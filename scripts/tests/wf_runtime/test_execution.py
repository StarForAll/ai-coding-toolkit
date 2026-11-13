#!/usr/bin/env python3
"""The runner must bound commands and retain their actual failure output."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

FULL = Path(__file__).parent / "full"


class ExecutionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-execution-test-")
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "command.log"

    def execution(self):
        path = FULL / "execution.py"
        self.assertTrue(path.exists(), "shared bounded command executor is missing")
        spec = importlib.util.spec_from_file_location("wf_execution_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_nonzero_exit_and_both_streams_are_preserved(self):
        result = self.execution().run(
            [sys.executable, "-c", "import sys; print('out'); print('err',file=sys.stderr); sys.exit(7)"],
            self.log, timeout=2)
        self.assertEqual(result["rc"], 7)
        self.assertEqual(result["status"], "failed")
        self.assertIn("out", self.log.read_text())
        self.assertIn("err", self.log.read_text())

    def test_log_symlink_never_overwrites_external_target(self):
        sentinel = Path(self.tmp.name) / 'valuable'
        sentinel.write_text('keep')
        self.log.symlink_to(sentinel)
        with self.assertRaises(OSError):
            self.execution().run([sys.executable, '-c', "print('bad')"], self.log, timeout=2)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_timeout_kills_child_group_including_blocked_reader(self):
        pidfile = Path(self.tmp.name) / "child.pid"
        code = ("import subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],stdout=subprocess.PIPE,start_new_session=True); "
                "open(sys.argv[1],'w').write(str(p.pid)); "
                "p.stdout.read()")
        started = time.monotonic()
        result = self.execution().run([sys.executable, "-c", code, str(pidfile)],
                                      self.log, timeout=0.2)
        self.assertEqual(result["status"], "timeout")
        self.assertLess(time.monotonic() - started, 3)
        if pidfile.exists():
            pid = int(pidfile.read_text())
            for _ in range(50):
                state = Path(f"/proc/{pid}/stat")
                try:
                    process_state = state.read_text().split()[2]
                except (FileNotFoundError, ProcessLookupError):
                    break
                if process_state == "Z":
                    break
                time.sleep(0.01)
            else:
                os.kill(pid, signal.SIGKILL)
                self.fail("descendant survived executor timeout")

    def test_cancellation_records_result_and_terminates_command(self):
        result_path = Path(self.tmp.name) / 'result.json'
        ready = Path(self.tmp.name) / 'ready'
        code = "from pathlib import Path; import sys,time; Path(sys.argv[1]).write_text('ready'); time.sleep(30)"
        proc = subprocess.Popen([sys.executable, str(FULL / 'execution.py'), '--log', str(self.log),
                                 '--result', str(result_path), '--timeout', '5', '--',
                                 sys.executable, '-c', code, str(ready)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 3
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(ready.exists(), 'executor did not start command')
            proc.terminate()
            proc.communicate(timeout=3)
            import json
            result = json.loads(result_path.read_text())
            self.assertEqual(result['status'], 'cancelled')
            self.assertEqual(result['rc'], 143)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=2)

    def test_successful_but_empty_suite_has_no_assertion_evidence(self):
        self.log.write_text("")
        self.assertFalse(self.execution().verdict(self.log, 0, "suite")["ok"])

    def test_pass_substring_is_not_an_assertion(self):
        self.log.write_text("BYPASS validation\n")
        self.assertFalse(self.execution().verdict(self.log, 0, "flow", expected=1)["ok"])

    def test_partial_suite_count_is_not_an_assertion(self):
        self.log.write_text("saved 12\n")
        self.assertFalse(self.execution().verdict(self.log, 0, "suite")["ok"])

    def test_legacy_count_requires_each_assertion_to_pass(self):
        self.log.write_text('[V1] first: PASS — ok\n[V1] second: FAIL — rejected\nsaved 2 cases\n')
        self.assertFalse(self.execution().verdict(self.log, 0, 'suite')['ok'])
        self.log.write_text('[V1] first: PASS — ok\n[V1] second: PASS — ok\nsaved 2 cases\n')
        self.assertTrue(self.execution().verdict(self.log, 0, 'suite')['ok'])

    def test_steps_require_successes_and_terminal_task_identity(self):
        self.log.write_text('[start] exit=0 code=WF_OK\nTASK_ID task-1\n')
        self.assertTrue(self.execution().verdict(self.log, 0, 'steps')['ok'])
        self.assertTrue(self.execution().verdict(self.log, 0, 'suite')['ok'])
        self.log.write_text('[start] exit=1 code=WF_CHECK_FAILED\nTASK_ID task-1\n')
        self.assertFalse(self.execution().verdict(self.log, 0, 'steps')['ok'])

    def test_unshare_mounts_return_results_and_protect_template_and_release(self):
        probe = subprocess.run(
            ["unshare", "-Urm", "bash", "-c",
             "mount -t tmpfs tmpfs /proc/self/fd >/dev/null 2>&1 || mount -t tmpfs tmpfs /tmp"],
            capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("user namespaces with mount support are unavailable")
        root = Path(self.tmp.name)
        results = root / "results"
        template = results / "template"
        release = root / "release"
        results.mkdir()
        template.mkdir()
        release.mkdir()
        env = {**os.environ, "RESULTS_DIR": str(results), "WF_TEMPLATE": str(template),
               "WF_TEMPLATE_READY": "1", "SHARED_RELEASE": str(release),
               "FIX": str(root / "fixture")}
        code = ("from pathlib import Path; import os\n"
                "Path(os.environ['RESULTS_DIR'],'returned').write_text('ok')\n"
                "for root in (os.environ['WF_TEMPLATE'], os.environ['SHARED_RELEASE'], "
                "'/tmp/wf-fixtures/release-repo'):\n"
                " try: Path(root,'write-probe').write_text('bad')\n"
                " except OSError: pass\n")
        result = subprocess.run(["unshare", "-Urm", sys.executable,
                                 str(FULL / "namespace.py"), sys.executable, "-c", code],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((results / "returned").read_text(), "ok")
        self.assertFalse((template / "write-probe").exists())
        self.assertFalse((release / "write-probe").exists())


if __name__ == "__main__":
    unittest.main()
