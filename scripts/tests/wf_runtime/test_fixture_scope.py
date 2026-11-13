#!/usr/bin/env python3
"""Fixture cleanup must refuse unowned paths before changing their contents."""
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
