"""Author-side path/scope owner (`scripts/wf_test_paths.py`) and its callers.

AC01/AC02: a managed path must be judged by path components *before* the first write.
A not-yet-existing `..` tail, a symlinked parent, a similar prefix or a broken link can
not borrow a string prefix; legal in-scope paths that do not exist yet stay usable.
Independent low-level CLIs (test-release/candidate/release-lock) consume the same rule.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FULL = Path(__file__).resolve().parent / "full"
sys.path.insert(0, str(REPO / "scripts"))

import wf_test_paths  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CanonicalPathTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-paths-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scope = wf_test_paths.create_test_scope(str(self.root))

    def test_nonexistent_dotdot_tail_is_refused(self):
        target = self.scope / "results" / ".." / ".." / "outside"
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.require_in_scope(target, scope=self.scope)
        self.assertFalse((self.root / "outside").exists(), "越界判断前不得创建任何路径")

    def test_parent_symlink_escape_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.scope / "linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.require_in_scope(self.scope / "linked" / "results", scope=self.scope)

    def test_similar_prefix_is_not_inside(self):
        sibling = Path(str(self.scope) + "-sibling")
        sibling.mkdir()
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.require_in_scope(sibling, scope=self.scope)
        self.assertEqual(wf_test_paths.canonical(sibling), sibling)

    def test_broken_link_component_is_refused(self):
        (self.scope / "broken").symlink_to(self.root / "missing-target")
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.canonical(self.scope / "broken" / "results")

    def test_uncreated_in_scope_paths_are_accepted(self):
        wf_test_paths.require_in_scope(self.scope / "results" / "run-1",
                                       self.scope / "cache" / "template",
                                       self.scope / "state" / "repro-state.json",
                                       scope=self.scope)
        self.assertFalse((self.scope / "results").exists())

    def test_marker_is_validated_by_the_owner(self):
        self.assertEqual(wf_test_paths.read_scope(self.scope), self.scope)
        marker = self.scope / wf_test_paths.SCOPE_MARKER
        record = json.loads(marker.read_text())
        record["uid"] = 0
        marker.write_text(json.dumps(record))
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.read_scope(self.scope)
        marker.unlink()
        with self.assertRaises(wf_test_paths.PathError):
            wf_test_paths.read_scope(self.scope)


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-layout-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scope = wf_test_paths.create_test_scope(str(self.root))
        self.addCleanup(lambda: os.environ.pop("WF_TEST_SCOPE_ROOT", None))

    def test_scope_layout_derives_every_managed_default(self):
        layout = wf_test_paths.resolve_layout(env={"WF_TEST_SCOPE_ROOT": str(self.scope)})
        for key in ("results_dir", "fixture", "legacy_fixture", "results_cache", "state",
                    "locks", "template", "test_release", "candidate", "pycache",
                    "pycache_bootstrap", "plan_log"):
            self.assertTrue(wf_test_paths.contains(self.scope, layout[key]),
                            f"{key}={layout[key]} 不在 scope 内")

    def test_explicit_out_of_scope_cache_or_pycache_is_refused(self):
        outside = self.root / "outside"
        outside.mkdir()
        for key, value in (("WF_RESULTS_CACHE", outside / "cache"),
                           ("WF_TEST_RELEASE_CACHE", outside / "release"),
                           ("WF_PYCACHE", outside / "pycache"),
                           ("WF_TEST_RUN_CACHE", outside / "state"),
                           ("WF_RESULTS_DIR", outside / "results"),
                           ("WF_FIX", outside / "fixture")):
            with self.subTest(key=key), self.assertRaises(wf_test_paths.PathError):
                wf_test_paths.resolve_layout(env={"WF_TEST_SCOPE_ROOT": str(self.scope), key: str(value)})
        self.assertEqual(sorted(os.listdir(outside)), [], "拒绝路径不得产生任何写入")

    def test_explicit_in_scope_values_are_kept(self):
        layout = wf_test_paths.resolve_layout(env={
            "WF_TEST_SCOPE_ROOT": str(self.scope),
            "WF_RESULTS_DIR": str(self.scope / "custom-results")})
        self.assertEqual(layout["results_dir"], self.scope / "custom-results")

    def test_production_layout_keeps_legacy_defaults(self):
        layout = wf_test_paths.resolve_layout(kind="run", pid=4242, env={})
        self.assertEqual(layout["results_dir"],
                         Path.home() / ".cache" / "wf-test-run" / "run-4242")
        self.assertEqual(layout["fixture"], Path("/tmp/wf-fixtures/run-4242"))


class CallerTest(unittest.TestCase):
    """独立低层入口也必须在首次写入前消费同一规则。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-path-callers-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scope = wf_test_paths.create_test_scope(str(self.root))
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def test_test_release_refuses_an_out_of_scope_root(self):
        release = _load("wf_test_release_scope", REPO / "scripts" / "tests" / "wf_test_release.py")
        saved = os.environ.get("WF_TEST_SCOPE_ROOT")
        os.environ["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        try:
            with self.assertRaises(release.TestReleaseError):
                release.check_output_root(str(self.outside / "release"))
            release.check_output_root(str(self.scope / "release"))
        finally:
            if saved is None:
                os.environ.pop("WF_TEST_SCOPE_ROOT", None)
            else:
                os.environ["WF_TEST_SCOPE_ROOT"] = saved
        self.assertFalse((self.outside / "release").exists())

    def test_candidate_repo_refuses_an_out_of_scope_root(self):
        candidate = _load("wf_candidate_scope", FULL / "prepare_candidate_repo.py")
        saved = os.environ.get("WF_TEST_SCOPE_ROOT")
        os.environ["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        try:
            with self.assertRaises(candidate.CandidateError):
                candidate.check_out_path(str(self.outside / "candidate"))
            candidate.check_out_path(str(self.scope / "candidate"))
        finally:
            if saved is None:
                os.environ.pop("WF_TEST_SCOPE_ROOT", None)
            else:
                os.environ["WF_TEST_SCOPE_ROOT"] = saved
        self.assertFalse((self.outside / "candidate").exists())

    def test_release_lock_refuses_an_out_of_scope_root(self):
        lock = _load("wf_release_lock_scope", REPO / "scripts" / "release_lock.py")
        saved = os.environ.get("WF_TEST_SCOPE_ROOT")
        os.environ["WF_TEST_SCOPE_ROOT"] = str(self.scope)
        try:
            with self.assertRaises(lock.LockError):
                lock.open_lock(str(self.outside / "release"))
        finally:
            if saved is None:
                os.environ.pop("WF_TEST_SCOPE_ROOT", None)
            else:
                os.environ["WF_TEST_SCOPE_ROOT"] = saved
        self.assertFalse((self.outside / "release.lock").exists())

    def _entries(self):
        return sorted(str(path.relative_to(self.scope)) for path in self.scope.rglob("*"))

    @staticmethod
    def _env(**extra):
        env = dict(os.environ)
        for key in ("WF_RESULTS_DIR", "WF_FIX", "WF_PYCACHE", "WF_RESULTS_CACHE",
                    "WF_TEST_RELEASE_CACHE", "WF_TEST_RUN_CACHE", "WF_CANCEL_FILE",
                    "PYTHONPYCACHEPREFIX"):
            env.pop(key, None)
        env.update(extra)
        return env

    def test_run_all_list_writes_nothing_in_the_scope(self):
        env = self._env(WF_TEST_SCOPE_ROOT=str(self.scope))
        before = self._entries()
        result = subprocess.run(["bash", str(FULL / "run_all.sh"), "--list"],
                                capture_output=True, text=True, env=env, cwd=str(REPO))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._entries(), before, "list 计划不得在 scope 内创建/删除任何文件")

    def test_run_all_dry_run_mirrors_only_plan_and_owner(self):
        results = self.scope / "mirror"
        env = self._env(WF_TEST_SCOPE_ROOT=str(self.scope), WF_RESULTS_DIR=str(results))
        result = subprocess.run(["bash", str(FULL / "run_all.sh"), "--dry-run"],
                                capture_output=True, text=True, env=env, cwd=str(REPO))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.name for path in results.iterdir()),
                         [".wf-results-owner.json", "plan.json"],
                         "显式 dry-run 只允许 plan 与 owner marker，不得生成 pycache")

    def test_out_of_scope_pycache_is_refused_before_any_write(self):
        outside = self.root / "outside-pycache"
        env = self._env(WF_TEST_SCOPE_ROOT=str(self.scope), WF_PYCACHE=str(outside))
        before = self._entries()
        result = subprocess.run(["bash", str(FULL / "run_all.sh"), "--list"],
                                capture_output=True, text=True, env=env, cwd=str(REPO))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PATH-REFUSED", result.stderr)
        self.assertEqual(self._entries(), before, "拒绝前不得在 scope 内产生写入")
        self.assertFalse(outside.exists(), "域外 pycache 在拒绝前不得被创建/写入")

    def test_plan_list_direct_call_writes_nothing(self):
        env = self._env(WF_TEST_SCOPE_ROOT=str(self.scope), WF_RESULTS_DIR="", WF_FIX="",
                        PYTHONDONTWRITEBYTECODE="1")
        before = self._entries()
        result = subprocess.run([sys.executable, str(FULL / "plan.py"), "--list", "--format", "sh"],
                                capture_output=True, text=True, env=env, cwd=str(REPO))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._entries(), before, "直接 list 计划不得写 scope")


if __name__ == "__main__":
    unittest.main()
