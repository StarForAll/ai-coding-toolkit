"""Command supervision (AC15/AC16): C → G → S → W ownership and fault takeover.

All fault injection targets only processes created by these tests and explicitly owned
by them (recorded PIDs / test-created PTYs). The test outer boundary always reaps its
own children in a finally block, so a broken supervision path cannot leak into the host.
"""

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parent / "full"
FULL_STR = str(FULL)


def _load_execution():
    spec = importlib.util.spec_from_file_location("wf_supervision_execution",
                                                  FULL / "execution.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pid_alive(pid):
    try:
        state = Path(f"/proc/{pid}/stat").read_text().split()[2]
    except (OSError, IndexError):
        return False
    return state != "Z"


def wait_gone(pid, timeout=6.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.02)
    return False


class SupervisionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-supervision-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / "command.log"
        self.execution = _load_execution()
        os.environ.pop("WF_SUPERVISOR_FAULT", None)
        os.environ.pop("WF_GUARDIAN_FAULT", None)
        os.environ.pop("WF_CANCEL_FILE", None)
        os.environ["WF_TEST_FAULT_INJECTION"] = "1"
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_SUPERVISOR_FAULT", "WF_GUARDIAN_FAULT", "WF_CANCEL_FILE",
                                  "WF_TEST_FAULT_INJECTION")])

    def script(self, body):
        path = self.root / "target.py"
        path.write_text(body)
        return [sys.executable, str(path)]

    def test_normal_command_keeps_rc_and_both_streams(self):
        result = self.execution.run(
            [sys.executable, "-c",
             "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
            self.log, timeout=10)
        self.assertEqual((result["status"], result["rc"]), ("failed", 7))
        text = self.log.read_text()
        self.assertIn("out", text)
        self.assertIn("err", text)
        self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")

    def test_child_that_leaves_its_session_is_reaped(self):
        pidfile = self.root / "grandchild.pid"
        result = self.execution.run(self.script(
            "import os, subprocess, sys\n"
            "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],\n"
            "                     start_new_session=True)\n"
            f"open({str(pidfile)!r}, 'w').write(str(p.pid))\n"
            "raise SystemExit(0)\n"), self.log, timeout=20)
        self.assertEqual(result["rc"], 0, result["reason"])
        self.assertEqual(result["status"], "passed")
        self.assertTrue(pidfile.exists(), "target did not run")
        pid = int(pidfile.read_text())
        self.assertTrue(wait_gone(pid), "父先退出后，独立 session 的后代必须被回收")

    def cli(self, target, *, timeout=30, env=None, log=None, result=None):
        log = log or self.log
        result = result or (self.root / "result.json")
        env = {**os.environ, **(env or {})}
        proc = subprocess.Popen([sys.executable, str(FULL / "execution.py"),
                                 "--log", str(log), "--result", str(result),
                                 "--timeout", str(timeout), "--", *target],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        return proc, result

    def test_cancel_before_ready_never_starts_the_target(self):
        pidfile = self.root / "pre-ready.pid"
        cancel_file = self.root / "cancel-request"
        cancel_file.write_text("cancel\n")
        os.environ["WF_CANCEL_FILE"] = str(cancel_file)
        os.environ["WF_SUPERVISOR_READY_DELAY"] = "0.5"
        self.addCleanup(os.environ.pop, "WF_SUPERVISOR_READY_DELAY", None)
        result = self.execution.run(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), self.log, timeout=10)
        self.assertEqual(result["status"], "cancelled", result["reason"])
        self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")
        self.assertFalse(pidfile.exists(), "READY 前取消不得启动目标")

    def test_duplicate_cancel_is_idempotent(self):
        pidfile = self.root / "dup.pid"
        result_path = self.root / "dup-result.json"
        proc, _ = self.cli(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), result=result_path)
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline and proc.poll() is None:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists())
            proc.terminate()
            proc.terminate()
            proc.communicate(timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)
        outcome = json.loads(result_path.read_text())
        self.assertEqual(outcome["status"], "cancelled", outcome.get("reason"))
        self.assertTrue(wait_gone(int(pidfile.read_text())))

    def test_caller_disconnect_still_cleans_the_target(self):
        pidfile = self.root / "disconnect.pid"
        result_path = self.root / "disconnect-result.json"
        proc, _ = self.cli(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), result=result_path)
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline and proc.poll() is None:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists())
            proc.kill()  # 模拟调用方 C 不可接管地消失
            proc.wait(timeout=5)
            self.assertTrue(wait_gone(int(pidfile.read_text()), timeout=8),
                            "C 失联后 G 必须通过 EOF 取消并回收目标")
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)

    def test_cancel_file_cancels_and_signals_are_not_leaked_to_the_target(self):
        pidfile = self.root / "target.pid"
        cancel_file = self.root / "cancel-request"
        policy_file = self.root / "policy.txt"
        target = self.script(
            "import os, signal, sys, time\n"
            "blocked = signal.pthread_sigmask(signal.SIG_BLOCK, [])\n"
            f"open({str(policy_file)!r}, 'w').write(repr([\n"
            "    [int(s), repr(signal.getsignal(s))] for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)]\n"
            "    + [sorted(int(s) for s in blocked)]))\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n")
        proc, result_path = self.cli(target, env={"WF_CANCEL_FILE": str(cancel_file)})
        try:
            deadline = time.monotonic() + 5
            while not pidfile.exists() and time.monotonic() < deadline and proc.poll() is None:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists(), "target did not start")
            cancel_file.write_text("cancel\n")
            proc.communicate(timeout=30)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)
        outcome = json.loads(result_path.read_text())
        self.assertEqual(outcome.get("status"), "cancelled", outcome.get("reason"))
        self.assertEqual(outcome.get("rc"), 143)
        self.assertTrue(wait_gone(int(pidfile.read_text())))
        data = eval(policy_file.read_text())  # 测试自产文件
        dispositions, blocked = data[:3], data[3]
        self.assertEqual(blocked, [], "目标不得继承 S 的阻塞 mask")
        # SIGINT 在 exec 后由 Python 重新安装 default_int_handler（C 层仍是 SIG_DFL），
        # 关键是不得继承 S 的“忽略”设置；TERM/HUP 必须仍是 SIG_DFL。
        self.assertNotEqual(dispositions[0][1], repr(signal.SIG_IGN))
        self.assertEqual(dispositions[1], [int(signal.SIGTERM), repr(signal.SIG_DFL)])
        self.assertEqual(dispositions[2], [int(signal.SIGHUP), repr(signal.SIG_DFL)])

    def test_supervisor_faults_become_infrastructure_failures_without_leftovers(self):
        for fault in ("exception", "os_exit", "kill"):
            with self.subTest(fault=fault):
                pidfile = self.root / f"fault-{fault}.pid"
                log = self.root / f"fault-{fault}.log"
                os.environ["WF_SUPERVISOR_FAULT"] = fault
                result = self.execution.run(self.script(
                    "import os, sys, time\n"
                    f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
                    "time.sleep(30)\n"), log, timeout=20)
                self.assertEqual(result["status"], "failed", result["reason"])
                self.assertTrue(result["supervision"]["infrastructure_error"])
                self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")
                pid = int(pidfile.read_text())
                self.assertTrue(wait_gone(pid),
                                f"S 故障({fault})后目标未被 G 接管回收")

    def test_supervisor_death_before_started_still_leaves_no_descendants(self):
        """STARTED 尚未送达的崩溃窗口：G 仍必须接管并报告设施失败。"""
        os.environ["WF_SUPERVISOR_FAULT"] = "kill"
        os.environ["WF_SUPERVISOR_FAULT_DELAY"] = "0"
        self.addCleanup(os.environ.pop, "WF_SUPERVISOR_FAULT_DELAY", None)
        result = self.execution.run(self.script(
            "import time\ntime.sleep(30)\n"), self.log, timeout=20)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["supervision"]["infrastructure_error"])
        self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")

    def test_fault_environment_is_ignored_without_the_explicit_switch(self):
        self.addCleanup(os.environ.__setitem__, "WF_TEST_FAULT_INJECTION", "1")
        os.environ.pop("WF_TEST_FAULT_INJECTION", None)
        os.environ["WF_SUPERVISOR_FAULT"] = "kill"
        result = self.execution.run([sys.executable, "-c", "print('ok')"], self.log, timeout=10)
        self.assertEqual((result["status"], result["rc"]), ("passed", 0),
                         "普通环境变量不得注入生产故障")

    def test_hung_supervisor_is_taken_over_after_bounded_grace(self):
        pidfile = self.root / "hung.pid"
        os.environ["WF_SUPERVISOR_FAULT"] = "hang"
        os.environ["WF_GUARDIAN_CANCEL_GRACE"] = "1"
        os.environ["WF_SUPERVISION_GRACE"] = "4"
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_GUARDIAN_CANCEL_GRACE", "WF_SUPERVISION_GRACE")])
        result = self.execution.run(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), self.log, timeout=1)
        self.assertEqual(result["status"], "failed", result["reason"])
        self.assertTrue(result["supervision"]["infrastructure_error"])
        self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")
        self.assertTrue(wait_gone(int(pidfile.read_text())),
                        "卡住的 S 必须被 G 终止并接管其目标")

    def test_abrupt_guardian_loss_still_requires_supervisor_cleanup(self):
        pidfile = self.root / "orphan.pid"
        os.environ["WF_GUARDIAN_FAULT"] = "kill"
        result = self.execution.run(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), self.log, timeout=20)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["supervision"]["infrastructure_error"])
        self.assertEqual(result["supervision"]["cleanup_state"], "unknown",
                         "G 猝死后 C 不得仅凭“S 预期会清理”声称已清理")
        self.assertTrue(wait_gone(int(pidfile.read_text())),
                        "S 看到 G↔S EOF 后仍必须回收目标")

    def test_guardian_capturable_exception_is_cleaned_up(self):
        pidfile = self.root / "guardian-exc.pid"
        os.environ["WF_GUARDIAN_FAULT"] = "exception"
        result = self.execution.run(self.script(
            "import os, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), self.log, timeout=20)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["supervision"]["infrastructure_error"])
        self.assertEqual(result["supervision"]["cleanup_state"], "cleaned")
        self.assertTrue(wait_gone(int(pidfile.read_text())))

    def test_pass_fds_and_log_fidelity(self):
        target_file = self.root / "carried.txt"
        fd = os.open(target_file, os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            script = self.script(
                "import os, sys, time\n"
                f"os.write({fd}, b'carried')\n"
                "print('stdout-line')\n"
                "print('stderr-line', file=sys.stderr)\n")
            result = self.execution.run(script, self.log, timeout=10, pass_fds=[fd])
        finally:
            os.close(fd)
        self.assertEqual(result["rc"], 0, result["reason"])
        self.assertEqual(target_file.read_text(), "carried", "pass_fds 必须传到目标")
        text = self.log.read_text()
        self.assertIn("stdout-line", text)
        self.assertIn("stderr-line", text)
        target = self.root / "fds.txt"
        fd_dir = self.execution.run(self.script(
            "import os\n"
            "links = []\n"
            "for name in os.listdir('/proc/self/fd'):\n"
            "    try:\n"
            "        links.append(os.readlink('/proc/self/fd/' + name))\n"
            "    except OSError:\n"
            "        continue\n"
            f"open({str(target)!r}, 'w').write('\\n'.join(links))\n"),
            self.root / "fds.log", timeout=10)
        self.assertEqual(fd_dir["rc"], 0, fd_dir["reason"])
        self.assertNotIn("socket:", target.read_text(),
                         "目标不得继承任何监督控制 FD")

    def test_cancelling_one_command_does_not_kill_a_sibling(self):
        cancel_file = self.root / "cancel-request"
        first_pid = self.root / "first.pid"
        second_pid = self.root / "second.pid"
        proc, result_path = self.cli(self.script(
            "import os, time\n"
            f"open({str(first_pid)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n"), env={"WF_CANCEL_FILE": str(cancel_file)})
        try:
            deadline = time.monotonic() + 5
            while not first_pid.exists() and time.monotonic() < deadline and proc.poll() is None:
                time.sleep(0.02)
            self.assertTrue(first_pid.exists())
            sibling_proc, sibling_result = self.cli(
                self.script("import os, time\n"
                            f"open({str(second_pid)!r}, 'w').write(str(os.getpid()))\n"
                            "time.sleep(1.5)\n"),
                log=self.root / "sibling.log", result=self.root / "sibling.json", timeout=10)
            try:
                deadline = time.monotonic() + 5
                while not second_pid.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(second_pid.exists())
                sibling_pid = int(second_pid.read_text())
                cancel_file.write_text("cancel\n")
                proc.communicate(timeout=30)
                sibling_proc.communicate(timeout=30)
            finally:
                if sibling_proc.poll() is None:
                    sibling_proc.kill()
                sibling_proc.communicate(timeout=5)
            sibling = json.loads(sibling_result.read_text())
            self.assertEqual((sibling.get("status"), sibling.get("rc")), ("passed", 0),
                             "sibling 不应被另一条命令的取消误杀")
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=5)
        outcome = json.loads(result_path.read_text())
        self.assertEqual(outcome.get("status"), "cancelled")
        self.assertTrue(wait_gone(int(first_pid.read_text())))
        self.assertTrue(wait_gone(sibling_pid, timeout=2))

    def test_nested_command_cancellation_propagates_to_the_inner_target(self):
        inner_pid = self.root / "inner.pid"
        inner_script = self.script(
            "import os, time\n"
            f"open({str(inner_pid)!r}, 'w').write(str(os.getpid()))\n"
            "time.sleep(30)\n")
        outer = [sys.executable, str(FULL / "execution.py"), "--log",
                 str(self.root / "inner.log"), "--timeout", "30", "--", *inner_script]
        result = self.execution.run(outer, self.log, timeout=1.2)
        self.assertEqual(result["status"], "timeout", result["reason"])
        self.assertTrue(wait_gone(int(inner_pid.read_text())),
                        "外层取消必须传到内层 C/G 并在内层收口")

    def test_outer_cleanup_reaps_double_forked_children_and_releases_locks(self):
        """双 fork + 真实 flock：G 接管后锁必须可重取。"""
        import fcntl

        lock_path = self.root / "locked.bin"
        lock_path.write_text("x")
        pidfile = self.root / "double-fork.pid"
        script = (
            "import fcntl, os, sys, time\n"
            f"fd = os.open({str(lock_path)!r}, os.O_RDWR)\n"
            "fcntl.flock(fd, fcntl.LOCK_EX)\n"
            "pid = os.fork()\n"
            "if pid == 0:\n"
            "    os.setsid()\n"
            "    pid2 = os.fork()\n"
            "    if pid2 == 0:\n"
            f"        open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            "        time.sleep(30)\n"
            "        os._exit(0)\n"
            "    os._exit(0)\n"
            "os.waitpid(pid, 0)\n"
            "time.sleep(30)\n")
        os.environ["WF_SUPERVISOR_FAULT"] = "exception"
        result = self.execution.run([sys.executable, "-c", script], self.log, timeout=20)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(wait_gone(int(pidfile.read_text())),
                        "双 fork/独立 session 的后代必须被回收")
        probe = os.open(lock_path, os.O_RDWR)
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            fcntl.flock(probe, fcntl.LOCK_UN)
            os.close(probe)


if __name__ == "__main__":
    unittest.main()
