#!/usr/bin/env python3
"""Fixture cleanup must refuse unowned paths before changing their contents."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

FULL = Path(__file__).parent / "full"


class FixtureScopeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-fixture-scope-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def scope(self):
        path = FULL / "fixture_scope.py"
        self.assertTrue(path.exists(), "shared fixture ownership guard is missing")
        spec = importlib.util.spec_from_file_location("wf_fixture_scope_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_existing_unowned_directory_is_untouched(self):
        target = self.root / "valuable"
        target.mkdir()
        sentinel = target / "keep"
        sentinel.write_text("do not delete")
        scope = self.scope()
        with self.assertRaises(scope.FixtureError):
            scope.reset(target)
        self.assertEqual(sentinel.read_text(), "do not delete")

    def test_unowned_results_directory_is_rejected_without_cleanup(self):
        target = self.root / "results"
        target.mkdir()
        sentinel = target / "report.json"
        sentinel.write_text('{"user": true}')
        scope = self.scope()
        with self.assertRaises(scope.FixtureError):
            scope.prepare_results(target)
        self.assertEqual(sentinel.read_text(), '{"user": true}')

    def test_owned_results_cleanup_only_removes_runner_artifacts(self):
        scope = self.scope()
        target = self.root / "results"
        scope.claim_results(target)
        (target / "old.json").write_text("{}")
        (target / "notes.txt").write_text("keep")
        (target / "logs").mkdir()
        (target / "logs" / "old.log").write_text("log")
        scope.prepare_results(target)
        self.assertFalse((target / "old.json").exists())
        self.assertEqual((target / "notes.txt").read_text(), "keep")
        self.assertTrue((target / "logs").is_dir())
        self.assertTrue((target / ".wf-results-owner.json").is_file())

    def test_dangling_log_link_is_removed_without_creating_its_target(self):
        scope = self.scope()
        results = self.root / 'results'
        scope.claim_results(results)
        outside = self.root / 'outside.log'
        link = results / 'case.log'
        link.symlink_to(outside)
        scope.prepare_results(results)
        self.assertFalse(link.is_symlink())
        self.assertFalse(outside.exists())

    def test_fixture_lease_rejects_parallel_root_invocation(self):
        command = [sys.executable, str(FULL / "fixture_scope.py"), "lease", "--",
                   sys.executable, "-u", "-c",
                   "import time; print('ready',flush=True); time.sleep(3)"]
        first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(first.stdout.readline().strip(), "ready")
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertIn("another wf harness owns", second.stderr)
        finally:
            first.terminate()
            first.communicate(timeout=2)

    def test_forged_lease_environment_is_rejected(self):
        marker = Path(self.tmp.name) / "lease-owner.json"
        result = subprocess.run(
            [sys.executable, str(FULL / "fixture_scope.py"), "check-lease"],
            env={**os.environ, "WF_FIXTURE_LEASE_FD": "0",
                 "WF_FIXTURE_LEASE_PID": str(os.getpid()),
                 "WF_FIXTURE_LEASE_MARKER": str(marker)},
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_owned_directory_can_be_rebuilt_without_touching_siblings(self):
        scope = self.scope()
        target = self.root / "fixture"
        scope.reset(target)
        (target / "old").write_text("old")
        sibling = self.root / "keep"
        sibling.write_text("keep")
        scope.reset(target)
        self.assertFalse((target / "old").exists())
        self.assertEqual(sibling.read_text(), "keep")

    def test_symlink_and_forbidden_overlap_are_refused(self):
        scope = self.scope()
        target = self.root / "valuable"
        target.mkdir()
        sentinel = target / "keep"
        sentinel.write_text("keep")
        link = self.root / "link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(scope.FixtureError):
            scope.reset(link)
        with self.assertRaises(scope.FixtureError):
            scope.reset(target, forbidden=[target / "keep"])
        self.assertEqual(sentinel.read_text(), "keep")

    def test_repository_and_temp_root_are_refused(self):
        scope = self.scope()
        for target in (FULL.resolve().parents[3], Path(tempfile.gettempdir()),
                       Path(tempfile.gettempdir()) / 'wf-fixtures', Path.home(), Path('/')):
            with self.subTest(target=target), self.assertRaises(scope.FixtureError):
                scope.reset(target)


class PruneResultsTest(unittest.TestCase):
    """缓存轮转契约（design D5.2/D5.3）：marker 门控、scope 前缀隔离、keep-N、
    exclude 保护、bootstrap 白名单与"未知顶层内容跳过"。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-prune-test-")
        self.addCleanup(self.tmp.cleanup)
        self.cache = Path(self.tmp.name) / "wf-test-run"
        self.cache.mkdir()

    def scope(self):
        spec = importlib.util.spec_from_file_location(
            "wf_fixture_scope_prune_test", FULL / "fixture_scope.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _make_run(self, name, owned=True, mtime=0):
        import json as _json
        import os as _os
        directory = self.cache / name
        directory.mkdir()
        (directory / "lines").write_text("stub")
        if owned:
            marker = directory / ".wf-results-owner.json"
            marker.write_text(_json.dumps(
                {"owner": "wf-test-fixture-v1", "root": str(directory)}))
            _os.utime(marker, (mtime, mtime))
        return directory

    def test_prunes_oldest_owned_beyond_keep_and_prefix_isolated(self):
        scope = self.scope()
        for i in range(5):
            self._make_run(f"run-{100 + i}", mtime=i)
        repro_dir = self._make_run("repro-green-1", mtime=1)
        scope.prune_results(self.cache, "run", keep=2)
        # 保留最新 2 个（mtime 3/4），删除最旧 3 个；repro-* 不被 run scope 越界回收
        self.assertTrue((self.cache / "run-103").exists())
        self.assertTrue((self.cache / "run-104").exists())
        self.assertFalse((self.cache / "run-100").exists())
        self.assertFalse((self.cache / "run-102").exists())
        self.assertTrue(repro_dir.exists())

    def test_unowned_and_excluded_directories_survive(self):
        scope = self.scope()
        unowned = self._make_run("run-200", owned=False)
        excluded = self._make_run("run-201", mtime=1)
        scope.prune_results(self.cache, "run", keep=0, exclude=[excluded])
        # 无 marker：普通 prune 一律不删（bootstrap 才有资格，见下一个用例）
        self.assertTrue(unowned.exists())
        self.assertTrue(excluded.exists())

    def test_bootstrap_only_removes_known_product_shapes(self):
        scope = self.scope()
        eligible = self._make_run("run-300", owned=False)
        (eligible / "logs").mkdir()  # 已知子目录（无 marker）
        unknown = self._make_run("run-301", owned=False)
        (unknown / "flows").write_text("x")  # 顶层未知文件 → 跳过
        deep = self._make_run("run-302", owned=False)
        (deep / "home-suite").mkdir()  # 顶层未知目录 → 跳过
        keep_marker = self._make_run("run-303", mtime=5)
        scope.prune_results(self.cache, "run", keep=20, bootstrap=True)
        self.assertFalse(eligible.exists())
        self.assertTrue(unknown.exists())
        self.assertTrue(deep.exists())
        self.assertTrue(keep_marker.exists())

    def test_invalid_root_and_scope_are_refused(self):
        scope = self.scope()
        outside = Path(self.tmp.name) / "elsewhere" / "wf-test-run"
        outside.mkdir(parents=True)
        # 临时目录之下但名字不是标准根：允许（validate 的边界），真正拒绝的是
        # 非临时、非标准根路径与非法 scope。
        with self.assertRaises(scope.FixtureError):
            scope.prune_results(Path(self.tmp.name) / "wf-test-run", "both")
        home_like = Path("/definitely/not/a/tmp/path")
        with self.assertRaises(scope.FixtureError):
            scope.prune_results(home_like, "run")

    def test_repro_state_json_is_never_touched(self):
        scope = self.scope()
        state = self.cache / "repro-state.json"
        state.write_text("{}")
        scope.prune_results(self.cache, "repro", keep=0, bootstrap=True)
        self.assertEqual(state.read_text(), "{}")


class TestScopeTest(unittest.TestCase):
    """显式测试域（AC13）：owned scope、管理 locator 越界拒绝、结果锁域与继承。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-scope-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self._saved = {key: os.environ.get(key) for key in
                       ("WF_TEST_SCOPE_ROOT", "WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_PID",
                        "WF_RESULTS_LOCK_DOMAIN", "WF_RESULTS_LOCK_MNT",
                        "WF_FIXTURE_LEASE_FD", "WF_FIXTURE_LEASE_PID")}
        self.addCleanup(self._restore)

    def _restore(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def scope(self):
        spec = importlib.util.spec_from_file_location("wf_fixture_scope_scope_test",
                                                      FULL / "fixture_scope.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def make_scope(self):
        scope = self.scope()
        root = scope.create_test_scope(str(self.base))
        os.environ["WF_TEST_SCOPE_ROOT"] = str(root)
        return scope, root

    def test_scope_marker_is_fixed_and_validated(self):
        scope, root = self.make_scope()
        self.assertEqual(scope.read_scope(root), root)
        self.assertEqual(scope.results_domain(), "scope:" + str(root))
        self.assertEqual(scope.results_lock_path(), root / "locks" / f"results-{os.getuid()}.lock")
        marker = root / scope.SCOPE_MARKER
        record = json.loads(marker.read_text())
        record["uid"] = 0
        marker.write_text(json.dumps(record))
        with self.assertRaises(scope.FixtureError):
            scope.read_scope(root)
        marker.unlink()
        with self.assertRaises(scope.FixtureError):
            scope.read_scope(root)

    def test_production_domain_uses_fixed_uid_lock(self):
        scope = self.scope()
        os.environ.pop("WF_TEST_SCOPE_ROOT", None)
        self.assertEqual(scope.results_domain(), "production")
        self.assertEqual(str(scope.results_lock_path()), f"/tmp/wf-test-results-{os.getuid()}.lock")

    def test_runner_managed_paths_must_stay_inside_the_scope(self):
        scope, root = self.make_scope()
        scope.ensure_in_scope(str(root / "results"), str(root / "cache" / "x"))
        self.assertEqual(scope.ensure_in_scope(str(root)), None, "scope 自身合法")
        outside = self.base / "outside"
        outside.mkdir()
        with self.assertRaises(scope.FixtureError):
            scope.ensure_in_scope(str(outside))
        # 项目外但 scope 内的兄弟目录仍是合法 escape/probe 目标（scope 不等于 project）。
        (root / "outside").mkdir()
        self.assertEqual(scope.ensure_in_scope(str(root / "outside")), None)
        os.environ.pop("WF_TEST_SCOPE_ROOT", None)
        scope.ensure_in_scope(str(outside))

    def test_results_lock_is_exclusive_and_domain_bound(self):
        scope, _root = self.make_scope()
        scope.acquire_results_lock()
        with self.assertRaises(scope.FixtureError):
            scope.acquire_results_lock()
        self.assertTrue(scope.verify_results_lock())
        os.environ["WF_RESULTS_LOCK_DOMAIN"] = "scope:/elsewhere"
        with self.assertRaises(scope.FixtureError):
            scope.verify_results_lock()

    def test_scope_domain_requires_an_active_scope(self):
        """域标记只是定位：没有活动 scope 时，`scope:` 域不得被当成继承来的结果锁。"""
        scope, _root = self.make_scope()
        scope.acquire_results_lock()
        self.assertTrue(scope.verify_results_lock())
        os.environ.pop("WF_TEST_SCOPE_ROOT", None)
        with self.assertRaises(scope.FixtureError):
            scope.verify_results_lock()

    def test_scope_domain_must_match_the_active_scope(self):
        """另一个真实 scope 的域字符串也不能冒用当前 scope 的锁。"""
        scope, _root = self.make_scope()
        scope.acquire_results_lock()
        other = scope.create_test_scope(str(self.base))
        os.environ["WF_RESULTS_LOCK_DOMAIN"] = "scope:" + str(other)
        with self.assertRaises(scope.FixtureError):
            scope.verify_results_lock()

    def test_unit_domain_without_scope_or_inherited_lock_is_refused(self):
        scope, _root = self.make_scope()
        os.environ.pop("WF_TEST_SCOPE_ROOT", None)
        os.environ["WF_UNIT_DOMAIN"] = "unit"
        self.addCleanup(os.environ.pop, "WF_UNIT_DOMAIN", None)
        with self.assertRaises(scope.FixtureError):
            scope.lease_domain([sys.executable, "-c", "pass"])

    def test_forged_results_lease_is_rejected(self):
        scope, _root = self.make_scope()
        os.environ.update({"WF_RESULTS_LOCK_FD": "0", "WF_RESULTS_LOCK_PID": str(os.getpid()),
                           "WF_RESULTS_LOCK_DOMAIN": scope.results_domain(),
                           "WF_RESULTS_LOCK_MNT": os.readlink("/proc/self/ns/mnt")})
        with self.assertRaises(scope.FixtureError):
            scope.verify_results_lock()

    def test_lease_results_execs_with_verifiable_locks(self):
        scope, root = self.make_scope()
        result = subprocess.run(
            [sys.executable, str(FULL / "fixture_scope.py"), "lease-results", "--",
             sys.executable, "-c",
             "import os,subprocess,sys;"
             "subprocess.run([sys.executable, os.path.join(os.environ['FULL'], 'fixture_scope.py'),"
             " 'check-results-lease'], check=True);"
             "subprocess.run([sys.executable, os.path.join(os.environ['FULL'], 'fixture_scope.py'),"
             " 'check-lease'], check=True);print('OK')"],
            env={**os.environ, "FULL": str(FULL)}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)
        self.assertTrue((root / "locks" / f"results-{os.getuid()}.lock").is_file())


if __name__ == "__main__":
    unittest.main()
