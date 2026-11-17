#!/usr/bin/env python3
"""The runner must bound commands and retain their actual failure output."""
import fcntl
import importlib.util
import json
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


class EvidenceTest(unittest.TestCase):
    """命令证据域（AC03）：standalone/ managed 先登记再启动，写失败不启动，坏上下文不降级。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-evidence-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.log = self.root / "logs" / "command.log"

    def module(self):
        path = FULL / "execution.py"
        spec = importlib.util.spec_from_file_location("wf_execution_evidence_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def lifecycle(self):
        path = FULL / "resource_lifecycle.py"
        spec = importlib.util.spec_from_file_location("wf_lifecycle_exec_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_standalone_receipt_is_a_hidden_sibling_and_returns_the_path(self):
        execution = self.module()
        marker = self.root / "started"
        result = execution.run([sys.executable, "-c",
                                "open(%r,'w').write('x')" % str(marker)],
                               self.log, timeout=10)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(marker.exists())
        evidence = Path(result["evidence_path"])
        self.assertEqual(evidence.parent, self.log.parent)
        self.assertTrue(evidence.name.startswith("." + self.log.name + ".execution-"))
        record = json.loads(evidence.read_text())
        self.assertEqual(record["evidence_scope"], "standalone-command")
        self.assertIsNone(record["run_id"])
        self.assertEqual(record["state"], "finished")
        self.assertEqual(record["command_id"], result["command_id"])
        self.assertEqual(record["local_cleanup"], "none")

    def test_missing_log_parents_are_created_and_relative_log_uses_caller_cwd(self):
        execution = self.module()
        target_cwd = self.root / "target"
        target_cwd.mkdir()
        relative = os.path.relpath(self.root / "relative.log", Path.cwd())
        result = execution.run([sys.executable, "-c", "print('ok')"],
                               Path(relative), timeout=10, cwd=target_cwd)
        self.assertEqual(result["status"], "passed")
        self.assertTrue((self.root / "relative.log").exists(),
                        "相对 log 必须相对调用者 cwd 固定，而不是目标 cwd")
        self.assertEqual(result["cwd"], str(target_cwd))
        self.assertEqual(Path(result["evidence_path"]).parent, self.root)

    def test_managed_context_is_verified_and_receipts_land_in_commands(self):
        execution = self.module()
        life = self.lifecycle()
        results = self.root / "results"
        run = life.begin_run(str(results), "execution", "full")
        old = dict(os.environ)
        try:
            os.environ.update({"WF_RUN_ID": run["run_id"], "WF_RESULTS_DIR": str(results),
                               "WF_COMMAND_EVIDENCE_ROOT": str(results / "commands")})
            result = execution.run([sys.executable, "-c", "print('ok')"],
                                   self.log, timeout=10)
        finally:
            os.environ.clear()
            os.environ.update(old)
        record = json.loads(Path(result["evidence_path"]).read_text())
        self.assertEqual(record["evidence_scope"], "managed-child")
        self.assertEqual(record["run_id"], run["run_id"])
        self.assertEqual(Path(result["evidence_path"]).parent, results / "commands")
        self.assertEqual(record["state"], "finished")

    def test_incomplete_managed_context_is_refused_without_starting_the_target(self):
        execution = self.module()
        marker = self.root / "started"
        old = dict(os.environ)
        try:
            os.environ["WF_RUN_ID"] = "run-without-root"
            with self.assertRaises(execution.EvidenceError):
                execution.run([sys.executable, "-c",
                               "open(%r,'w').write('x')" % str(marker)],
                              self.log, timeout=10)
        finally:
            os.environ.clear()
            os.environ.update(old)
        self.assertFalse(marker.exists(), "证据域拒绝必须在目标启动前")
        self.assertFalse(self.log.exists(), "被拒绝的调用不得留下成功日志")

    def test_scope_boundary_rejects_logs_outside_the_owned_scope(self):
        import fixture_scope
        execution = self.module()
        scope = fixture_scope.create_test_scope()
        self.addCleanup(lambda: __import__("shutil").rmtree(scope, ignore_errors=True))
        old = dict(os.environ)
        try:
            os.environ["WF_TEST_SCOPE_ROOT"] = str(scope)
            outside = self.root / "outside.log"
            with self.assertRaises(fixture_scope.FixtureError):
                execution.run([sys.executable, "-c", "print('ok')"], outside, timeout=10)
            inside = scope / "logs" / "inside.log"
            result = execution.run([sys.executable, "-c", "print('ok')"], inside, timeout=10)
            self.assertEqual(result["status"], "passed")
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_receipt_write_failure_prevents_the_target_from_starting(self):
        execution = self.module()
        marker = self.root / "started"
        self.log.parent.mkdir()
        self.log.parent.chmod(0o500)
        self.addCleanup(lambda: self.log.parent.chmod(0o700))
        with self.assertRaises(OSError):
            execution.run([sys.executable, "-c",
                           "open(%r,'w').write('x')" % str(marker)], self.log, timeout=10)
        self.assertFalse(marker.exists(), "写 started 失败时目标不得启动")

    def test_isolated_home_is_unique_removed_on_success_and_retained_on_unknown(self):
        execution = self.module()
        result = execution.run([sys.executable, "-c", "print('ok')"], self.log,
                               timeout=10, isolated_user=True)
        self.assertEqual(result["status"], "passed")
        record = json.loads(Path(result["evidence_path"]).read_text())
        self.assertEqual(record["local_cleanup"], "removed")
        self.assertFalse(Path(str(self.log) + ".home-" + result["command_id"]).exists(),
                         "cleaned 的隔离 HOME 必须回收")
        os.environ.update({"WF_TEST_FAULT_INJECTION": "1", "WF_GUARDIAN_FAULT": "kill",
                           "WF_GUARDIAN_FAULT_DELAY": "0.2"})
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_TEST_FAULT_INJECTION", "WF_GUARDIAN_FAULT",
                                  "WF_GUARDIAN_FAULT_DELAY")])
        failed = execution.run([sys.executable, "-c", "import time; time.sleep(2)"],
                               self.root / "logs" / "fail.log", timeout=10,
                               isolated_user=True)
        self.assertNotEqual(failed["status"], "passed")
        record = json.loads(Path(failed["evidence_path"]).read_text())
        self.assertIn(record["local_cleanup"], ("retained-unknown", "failed"))
        self.assertTrue(Path(str(self.root / "logs" / "fail.log") + ".home-"
                             + failed["command_id"]).exists(),
                        "监督 unknown 时隔离 HOME 必须保留")




    def test_declared_local_dirs_are_removed_only_after_clean_supervision(self):
        execution = self.module()
        self.log.parent.mkdir(parents=True, exist_ok=True)
        local = self.log.parent / "phase-tmp"
        local.mkdir()
        (local / "payload").write_text("x")
        result = execution.run([sys.executable, "-c", "print('ok')"], self.log,
                               timeout=10, local_dirs=[local])
        self.assertEqual(result["status"], "passed")
        self.assertFalse(local.exists(), "cleaned 的相位 TMPDIR 必须回收")
        record = json.loads(Path(result["evidence_path"]).read_text())
        self.assertEqual(record["local_cleanup"], "removed")
        retained = self.log.parent / "retained-tmp"
        retained.mkdir()
        os.environ.update({"WF_TEST_FAULT_INJECTION": "1", "WF_GUARDIAN_FAULT": "kill",
                           "WF_GUARDIAN_FAULT_DELAY": "0.2"})
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_TEST_FAULT_INJECTION", "WF_GUARDIAN_FAULT",
                                  "WF_GUARDIAN_FAULT_DELAY")])
        failed = execution.run([sys.executable, "-c", "import time; time.sleep(2)"],
                               self.root / "logs" / "phase.log", timeout=10,
                               local_dirs=[retained])
        self.assertNotEqual(failed["status"], "passed")
        record = json.loads(Path(failed["evidence_path"]).read_text())
        self.assertIn(record["local_cleanup"], ("retained-unknown", "failed"))
        self.assertIn(str(retained), record["retained_paths"])
        self.assertTrue(retained.exists())



class NamespaceScrubTest(unittest.TestCase):
    """namespace 单元不得携带宿主 state/cache locator（AC10）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-namespace-test-")
        self.addCleanup(self.tmp.cleanup)

    def module(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("wf_namespace_scrub", FULL / "namespace.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_state_and_cache_locators_are_scrubbed(self):
        module = self.module()
        environ = {
            "WF_TEST_RUN_CACHE": "/home/user/.cache/wf-test-run",
            "WF_RESULTS_CACHE": "/home/user/.cache/wf-test-run",
            "WF_PLAN_LOG": "/tmp/plan-calls-1",
            "WF_RESULTS_LOCK_FD": "9", "WF_RESULTS_LOCK_DOMAIN": "production",
            "WF_TEST_SCOPE_ROOT": "/tmp/wf-test-scope-x",
            "WF_RELEASE_CONTEXT": "/tmp/keep-context.json",
            "SOURCE_HOME": "/home/user",
        }
        removed = module.scrub_state_locators(environ)
        for key in ("WF_TEST_RUN_CACHE", "WF_RESULTS_CACHE", "WF_PLAN_LOG",
                    "WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_DOMAIN", "WF_TEST_SCOPE_ROOT"):
            self.assertIn(key, removed)
            self.assertNotIn(key, environ)
        self.assertEqual(environ["WF_RELEASE_CONTEXT"], "/tmp/keep-context.json",
                         "已核 release context 是只读输入，不属 state locator")
        self.assertEqual(environ["SOURCE_HOME"], "/home/user")

    def test_unit_domain_cannot_borrow_host_locks(self):
        probe = subprocess.run(
            ["unshare", "-Urm", "bash", "-c",
             "mount -t tmpfs tmpfs /proc/self/fd >/dev/null 2>&1 || mount -t tmpfs tmpfs /tmp"],
            capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("user namespaces with mount support are unavailable（能力缺失已记录）")
        sys.path.insert(0, str(FULL))
        import fixture_scope
        root = Path(self.tmp.name)
        results, release = root / "results", root / "release"
        results.mkdir(parents=True, exist_ok=True)
        release.mkdir(parents=True, exist_ok=True)
        saved = {key: os.environ.get(key) for key in
                 ("WF_TEST_SCOPE_ROOT", "WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_PID",
                  "WF_RESULTS_LOCK_DOMAIN", "WF_RESULTS_LOCK_MNT")}
        for key in saved:
            os.environ.pop(key, None)
        self.addCleanup(lambda: [os.environ.pop(key, None) if saved[key] is None
                                 else os.environ.__setitem__(key, saved[key]) for key in saved])
        fd = fixture_scope.acquire_results_lock()
        inode = os.fstat(fd).st_ino
        lock_path = Path(fixture_scope.PRODUCTION_RESULTS_LOCK)
        try:
            env = {**os.environ, "RESULTS_DIR": str(results), "SHARED_RELEASE": str(release),
                   "WF_TEMPLATE_READY": "0", "FIX": str(root / "fixture"),
                   "WF_TEST_RUN_CACHE": str(root / "host-state"),
                   "WF_RESULTS_CACHE": str(root / "host-cache")}
            code = (
                "import os, sys\n"
                "sys.path.insert(0, %r)\n" % str(FULL) +
                "import fixture_scope\n"
                "problems = []\n"
                "if os.environ.get('WF_UNIT_DOMAIN') != 'unit':\n"
                "    problems.append('unit domain marker missing')\n"
                "if 'WF_TEST_RUN_CACHE' in os.environ or 'WF_RESULTS_CACHE' in os.environ:\n"
                "    problems.append('host state/cache locator leaked into the unit')\n"
                "try:\n"
                "    fixture_scope.verify_results_lock()\n"
                "    problems.append('forged inherited host results lock was accepted')\n"
                "except fixture_scope.FixtureError:\n"
                "    pass\n"
                "try:\n"
                "    fixture_scope.lease_domain([sys.executable, '-c', 'pass'])\n"
                "    problems.append('unit domain created a private host-like lock')\n"
                "except fixture_scope.FixtureError:\n"
                "    pass\n"
                "print('problems:', problems)\n"
                "raise SystemExit(1 if problems else 0)\n")
            child = subprocess.run(["unshare", "-Urm", sys.executable, str(FULL / "namespace.py"),
                                    sys.executable, "-c", code],
                                   env=env, capture_output=True, text=True)
            self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
            self.assertIn("problems: []", child.stdout)
        finally:
            pass
        # 宿主锁：inode 不变、仍由本进程持有（子进程只关自己的 FD 副本）。
        self.assertEqual(os.stat(lock_path).st_ino, inode)
        self.assertTrue(fixture_scope.verify_results_lock())
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


if __name__ == "__main__":
    unittest.main()
