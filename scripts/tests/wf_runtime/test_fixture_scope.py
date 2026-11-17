#!/usr/bin/env python3
"""Fixture cleanup must refuse unowned paths before changing their contents."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
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

    def lifecycle(self):
        spec = importlib.util.spec_from_file_location(
            "wf_resource_lifecycle_fixture_test", FULL / "resource_lifecycle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def finished_run(self, root, artifacts=()):
        life = self.lifecycle()
        out = life.begin_run(str(root), "execution", "full")
        for relative in artifacts:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative.endswith("/"):
                path.mkdir(exist_ok=True)
            else:
                path.write_text("x")
        life.finish_run(str(root), out["run_id"], "full", "cleaned", "ok", "complete")
        return out

    def test_finished_cleaned_generation_is_reset_through_begin_run(self):
        scope = self.scope()
        target = self.root / "results"
        self.finished_run(target, ["old.json", "lines", "logs/old.log", "commands/a.json"])
        scope.begin_run(str(target))
        self.assertFalse((target / "old.json").exists())
        self.assertFalse((target / "commands" / "a.json").exists())
        self.assertFalse((target / "logs" / "old.log").exists())
        self.assertTrue((target / "logs").is_dir())
        self.assertEqual(json.loads((target / ".wf-results-owner.json").read_text())["intent"],
                         "execution")

    def test_unknown_top_level_entry_blocks_reuse_without_deletion(self):
        scope = self.scope()
        target = self.root / "results"
        self.finished_run(target)
        (target / "notes.txt").write_text("keep")
        with self.assertRaises(scope.FixtureError):
            scope.begin_run(str(target))
        self.assertEqual((target / "notes.txt").read_text(), "keep")

    def test_reused_results_drop_stale_runner_control_record(self):
        scope = self.scope()
        results = self.root / 'results'
        self.finished_run(results, ['.runner.json'])
        scope.begin_run(str(results))
        self.assertFalse((results / '.runner.json').exists(),
                         "上一轮的 .runner.json 不得跨轮污染 cleanup 聚合")

    def test_dangling_log_link_is_refused_without_creating_its_target(self):
        scope = self.scope()
        results = self.root / 'results'
        self.finished_run(results)
        outside = self.root / 'outside.log'
        link = results / 'case.log'
        link.symlink_to(outside)
        with self.assertRaises(scope.FixtureError):
            scope.begin_run(str(results))
        self.assertTrue(link.is_symlink())
        self.assertFalse(outside.exists())

    def test_prepare_results_is_no_longer_a_standalone_entry(self):
        scope = self.scope()
        target = self.root / "results"
        self.finished_run(target)
        with self.assertRaises(scope.FixtureError):
            scope.prepare_results(target)

    def test_claim_results_writes_plan_only_owner(self):
        scope = self.scope()
        target = self.root / "results"
        scope.claim_results(target)
        owner = json.loads((target / ".wf-results-owner.json").read_text())
        self.assertEqual((owner["schema_version"], owner["intent"], owner["run_id"]),
                         (2, "plan-only", None))
        self.assertFalse((target / "run-state.json").exists())

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

    def test_empty_unowned_directory_is_reclaimable_but_data_is_not(self):
        scope = self.scope()
        empty = self.root / 'fixture'
        empty.mkdir()
        self.assertTrue(scope.remove(empty), "调用方预建的空目录可以回收")
        self.assertFalse(empty.exists())
        valuable = self.root / 'valuable'
        valuable.mkdir()
        (valuable / 'keep').write_text('keep')
        with self.assertRaises(scope.FixtureError):
            scope.remove(valuable)
        self.assertEqual((valuable / 'keep').read_text(), 'keep')

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

    def lifecycle(self):
        spec = importlib.util.spec_from_file_location(
            "wf_resource_lifecycle_prune_test", FULL / "resource_lifecycle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _make_run(self, name, owned=True, mtime=0, state="finished", cleanup="cleaned",
                  evidence="complete"):
        import os as _os
        directory = self.cache / name
        if owned:
            life = self.lifecycle()
            run = life.begin_run(str(directory), "execution", "full")
            (directory / "lines").write_text("stub")
            if state == "finished":
                life.finish_run(str(directory), run["run_id"], "full", cleanup, "ok", evidence)
            marker = directory / ".wf-results-owner.json"
            _os.utime(marker, (mtime, mtime))
        else:
            directory.mkdir()
            (directory / "lines").write_text("stub")
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

    def test_bootstrap_only_reports_unowned_entries_and_never_deletes_them(self):
        scope = self.scope()
        eligible = self._make_run("run-300", owned=False)
        (eligible / "logs").mkdir()  # 已知子目录（无 marker）
        unknown = self._make_run("run-301", owned=False)
        (unknown / "flows").write_text("x")
        active = self._make_run("run-302", state="active")
        retained = self._make_run("run-303", cleanup="unknown")
        keep_marker = self._make_run("run-304", mtime=5)
        rc = scope.prune_results(self.cache, "run", keep=20, bootstrap=True)
        self.assertEqual(rc, 1, "无主/非终态条目必须报告待退役复核并以非零退出")
        self.assertTrue(eligible.exists(), "已知形状不等于删除许可")
        self.assertTrue(unknown.exists())
        self.assertTrue(active.exists())
        self.assertTrue(retained.exists())
        self.assertTrue(keep_marker.exists())

    def test_legacy_owner_is_not_auto_pruned(self):
        scope = self.scope()
        legacy = self.cache / "run-400"
        legacy.mkdir()
        (legacy / "lines").write_text("x")
        (legacy / ".wf-results-owner.json").write_text(json.dumps(
            {"owner": "wf-test-fixture-v1", "root": str(legacy)}))
        rc = scope.prune_results(self.cache, "run", keep=0, bootstrap=True)
        self.assertEqual(rc, 1)
        self.assertTrue(legacy.exists(), "旧格式 owner 不能凭名字自动轮转")

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


# ---- C3：结果/夹具盘点与退役（父任务 design §4.2）-----------------------------

import pty  # noqa: E402
import select  # noqa: E402


def results_cli(scope, args, env_extra=None):
    import subprocess
    env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    env["WF_TEST_SCOPE_ROOT"] = str(scope)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(FULL / "fixture_scope.py"), *args],
                          capture_output=True, text=True, env=env, cwd=str(FULL.parents[2]),
                          timeout=120)


def retire_results_pty(scope, args, phrase):
    master, slave = pty.openpty()
    env = {key: value for key, value in os.environ.items() if not key.startswith("WF_")}
    env["WF_TEST_SCOPE_ROOT"] = str(scope)
    proc = subprocess.Popen([sys.executable, str(FULL / "fixture_scope.py"),
                             "retire-results", *args], stdin=slave, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env,
                            cwd=str(FULL.parents[2]))
    os.close(slave)
    try:
        time.sleep(0.5)
        try:
            os.write(master, (phrase + "\n").encode())
        except OSError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate(timeout=10)
            stderr += "\nPTY-CHILD-TIMEOUT"
    finally:
        try:
            os.close(master)
        except OSError:
            pass
    return proc.returncode, stdout, stderr


class ResultsInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import fixture_scope as scope_module
        cls.scope = scope_module.create_test_scope()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scope, ignore_errors=True)

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="results-", dir=self.scope))
        self.cache = self.root / "cache"
        self.cache.mkdir()

    def lifecycle(self):
        spec = importlib.util.spec_from_file_location(
            "wf_lifecycle_results_inventory", FULL / "resource_lifecycle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def new_run(self, name, finish=True):
        life = self.lifecycle()
        path = self.cache / name
        out = life.begin_run(str(path), "execution", "full")
        if finish:
            life.finish_run(str(path), out["run_id"], "full", "cleaned", "ok", "complete")
        return path

    def legacy_run(self, name):
        path = self.cache / name
        path.mkdir()
        (path / "lines").write_text("x")
        (path / ".wf-results-owner.json").write_text(json.dumps(
            {"owner": "wf-test-fixture-v1", "root": str(path)}))
        return path

    def inventory(self, *extra):
        proc = results_cli(self.scope, ["inventory-results", "--cache-root", str(self.cache),
                                        "--format", "json", *extra])
        return proc, json.loads(proc.stdout or "{}")

    def test_inventory_reports_identity_and_never_writes(self):
        cleaned = self.new_run("run-1")
        legacy = self.legacy_run("repro-2")
        unowned = self.cache / "run-3"
        unowned.mkdir()
        (unowned / "lines").write_text("x")
        active = self.new_run("run-4", finish=False)
        before = sorted(os.listdir(self.cache))
        proc, report = self.inventory()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(sorted(os.listdir(self.cache)), before, "inventory 必须零写")
        by_path = {item["path"]: item for item in report["entries"]}
        self.assertEqual(by_path[os.path.realpath(cleaned)]["class"], "finished-cleaned")
        self.assertEqual(by_path[os.path.realpath(legacy)]["provenance"], "legacy-owned")
        self.assertEqual(by_path[os.path.realpath(unowned)]["provenance"], "unowned")
        self.assertEqual(by_path[os.path.realpath(active)]["class"], "active")
        for path in (cleaned, legacy, active):
            item = by_path[os.path.realpath(path)]
            self.assertTrue(item.get("digest"), f"{path} 的身份快照必须存在")

    def test_safe_legacy_only_accepts_strict_old_results(self):
        legacy = self.legacy_run("repro-2")
        cleaned = self.new_run("run-1")
        proc, report = self.inventory()
        self.assertEqual(proc.returncode, 0)
        legacy_entry = next(i for i in report["entries"] if i["path"] == os.path.realpath(legacy))
        cleaned_entry = next(i for i in report["entries"] if i["path"] == os.path.realpath(cleaned))
        selection = self.root / "legacy.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "results",
                                         "root": report["root"], "entries": [legacy_entry]}))
        report_path = self.root / "legacy-retire.json"
        proc = results_cli(self.scope, ["retire-results", "--selection", str(selection),
                                        "--retirement-mode", "safe-legacy",
                                        "--confirm-retirement", "--report", str(report_path)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertFalse(legacy.exists())
        self.assertTrue(cleaned.exists())
        # 新协议结果不得走 safe-legacy。
        selection = self.root / "new.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "results",
                                         "root": report["root"], "entries": [cleaned_entry]}))
        proc = results_cli(self.scope, ["retire-results", "--selection", str(selection),
                                        "--retirement-mode", "safe-legacy",
                                        "--confirm-retirement",
                                        "--report", str(self.root / "new-retire.json")])
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(cleaned.exists())

    def test_manual_retained_requires_tty_and_exact_results_digest(self):
        cleaned = self.new_run("run-1")
        proc, report = self.inventory()
        entry = next(i for i in report["entries"] if i["path"] == os.path.realpath(cleaned))
        selection = self.root / "selection.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "results",
                                         "root": report["root"], "entries": [entry]}))
        plain = results_cli(self.scope, ["retire-results", "--selection", str(selection),
                                         "--retirement-mode", "manual-retained",
                                         "--confirm-retirement",
                                         "--report", str(self.root / "plain.json")])
        self.assertNotEqual(plain.returncode, 0)
        self.assertIn("TTY", plain.stderr)
        self.assertTrue(cleaned.exists())
        digest = self.lifecycle().selection_digest([entry])
        phrase = f"results {report['root']} {digest} abandon"
        rc, stdout, stderr = retire_results_pty(
            self.scope, ["--selection", str(selection), "--retirement-mode", "manual-retained",
                         "--confirm-retirement", "--report", str(self.root / "manual.json")],
            phrase)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertFalse(cleaned.exists())

    def test_unowned_results_and_unowned_fixtures_are_refused(self):
        unowned = self.cache / "run-9"
        unowned.mkdir()
        (unowned / "lines").write_text("x")
        fixture = self.root / "loose-fixture"
        fixture.mkdir()
        (fixture / "payload").write_text("x")
        proc, report = self.inventory()
        result_entry = next(i for i in report["entries"] if i["path"] == os.path.realpath(unowned))
        selection = self.root / "bad.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "results",
                                         "root": report["root"], "entries": [result_entry]}))
        proc = results_cli(self.scope, ["retire-results", "--selection", str(selection),
                                        "--retirement-mode", "manual-retained",
                                        "--confirm-retirement",
                                        "--report", str(self.root / "bad.json.out")])
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(unowned.exists())
        # 精确 fixture 模式：无 marker 的目录不能被当作 owned。
        proc = results_cli(self.scope, ["inventory-results", "--fixture", str(fixture),
                                        "--format", "json"])
        precise = json.loads(proc.stdout)
        self.assertEqual(precise["entries"][0]["provenance"], "unowned")

    def test_owned_fixture_is_precisely_retired(self):
        import fixture_scope as scope_module
        fixture = self.root / "owned-fixture"
        scope_module.reset(fixture)
        (fixture / "payload").write_text("x")
        proc = results_cli(self.scope, ["inventory-results", "--fixture", str(fixture),
                                        "--format", "json"])
        report = json.loads(proc.stdout)
        entry = report["entries"][0]
        self.assertEqual(entry["provenance"], "owned")
        selection = self.root / "fixture.json"
        selection.write_text(json.dumps({"schema_version": 1, "domain": "results",
                                         "root": "precise", "entries": [entry]}))
        digest = self.lifecycle().selection_digest([entry])
        phrase = f"results precise {digest} abandon"
        rc, stdout, stderr = retire_results_pty(
            self.scope, ["--selection", str(selection), "--retirement-mode", "manual-retained",
                         "--confirm-retirement", "--report", str(self.root / "fixture.json.out")],
            phrase)
        self.assertEqual(rc, 0, stdout + stderr)
        self.assertFalse(fixture.exists())

    def test_observe_excludes_current_results(self):
        cleaned = self.new_run("run-1")
        current = self.new_run("run-2")
        import fixture_scope as scope_module
        report = scope_module.observe_results(str(self.cache), exclude=[str(current)])
        self.assertIn("finished-cleaned", report["counts"])
        self.assertEqual(report["counts"].get("finished-cleaned"), 1)
        self.assertIn("inventory-results", report["inventory_hint"])
