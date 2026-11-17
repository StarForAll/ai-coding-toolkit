"""清理证据的唯一解释点（AC01/02/10）：结构/矛盾一律 unknown，cleaned 才允许删除。

覆盖：
- `assess_execution` 对非对象/缺字段/非法状态/矛盾报告的反例；
- `read_children` 对 receipt 域/run_id/终态/local 清理的严格读取；
- `assess_run` 把“进程与本地资源事实”和“unit/gate 证据完整性”分开归因；
- `finalize` 只在 cleaned 时按固定角色序删除，首次失败即停并报告部分完成。
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

FULL = Path(__file__).resolve().parent / "full"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cleanup = _load("wf_runner_cleanup_test", FULL / "runner_cleanup.py")
lifecycle = _load("wf_lifecycle_for_cleanup_test", FULL / "resource_lifecycle.py")
import sys  # noqa: E402

sys.path.insert(0, str(FULL))
import fixture_scope  # noqa: E402


def result(status="passed", state="cleaned", infrastructure=False, rc=0):
    return {"status": status, "rc": rc,
            "supervision": {"cleanup_state": state, "infrastructure_error": infrastructure,
                            "target_rc": rc if status != "cancelled" else None}}


class AssessExecutionTest(unittest.TestCase):
    def test_cleaned_result_requires_terminal_evidence(self):
        self.assertEqual(cleanup.assess_execution(result())["cleanup_state"], "cleaned")
        cancelled = {"status": "cancelled", "rc": 130,
                     "supervision": {"cleanup_state": "cleaned", "infrastructure_error": False,
                                     "target_rc": None}}
        self.assertEqual(cleanup.assess_execution(cancelled)["cleanup_state"], "cleaned")

    def test_missing_or_malformed_evidence_is_unknown(self):
        for payload in (None, [], "x",
                        {"status": "passed"},
                        {"status": "bogus", "supervision": {"cleanup_state": "cleaned",
                                                             "infrastructure_error": False}},
                        {"status": "passed", "supervision": {"cleanup_state": "weird",
                                                              "infrastructure_error": False}},
                        {"status": "passed", "supervision": {"cleanup_state": "cleaned",
                                                              "target_rc": 0}},
                        {"status": "passed", "supervision": {"cleanup_state": "cleaned",
                                                              "infrastructure_error": False,
                                                              "target_rc": None}},
                        {"status": "passed", "supervision": {"cleanup_state": "cleaned",
                                                              "infrastructure_error": True,
                                                              "target_rc": 0}}):
            with self.subTest(payload=payload):
                self.assertEqual(cleanup.assess_execution(payload)["cleanup_state"], "unknown")

    def test_failed_state_is_preserved(self):
        self.assertEqual(cleanup.assess_execution(result(state="failed"))["cleanup_state"], "failed")


class ChildrenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-cleanup-children-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "commands").mkdir()

    def receipt(self, command_id, **overrides):
        record = {"schema_version": 1, "command_id": command_id, "run_id": "run-1",
                  "evidence_scope": "managed-child", "state": "finished",
                  "argv": ["true"], "cwd": str(self.root), "log_path": str(self.root / "a.log"),
                  "started_at": "t", "finished_at": "t", "result": result(), "supervision": result()["supervision"],
                  "local_cleanup": "none", "retained_paths": []}
        record.update(overrides)
        (self.root / "commands" / f"{command_id}.json").write_text(json.dumps(record))

    def test_finished_cleaned_children_pass(self):
        self.receipt("c1")
        report = cleanup.read_children(self.root, "run-1")
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(report["commands"]), 1)

    def test_wrong_run_domain_pending_and_local_states_are_problems(self):
        self.receipt("c1", run_id="other")
        self.receipt("c2", evidence_scope="standalone-command")
        self.receipt("c3", state="started")
        self.receipt("c4", local_cleanup="pending")
        self.receipt("c5", local_cleanup="failed")
        (self.root / "commands" / "notes.txt").write_text("x")
        kinds = {item["kind"] for item in cleanup.read_children(self.root, "run-1")["problems"]}
        self.assertTrue({"wrong-run", "wrong-domain", "pending", "local-pending",
                         "local-failed", "unexpected"} <= kinds, kinds)

    def test_unreadable_child_is_unknown(self):
        (self.root / "commands" / "bad.json").write_text("{broken")
        report = cleanup.read_children(self.root, "run-1")
        self.assertEqual(report["problems"][0]["kind"], "unreadable")


class AssessRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-cleanup-run-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_cleanup_and_evidence_are_separate_facts(self):
        gate_ok = {"ok": True, "gate": {}, "counts": {}, "repro": {}}
        report = cleanup.assess_run(self.root, "run-1", {"units": []}, result(), gate_ok)
        self.assertEqual((report["cleanup_state"], report["evidence_state"]),
                         ("cleaned", "complete"))
        gate_bad = {"ok": False, "gate": {}, "counts": {}, "repro": {}}
        report = cleanup.assess_run(self.root, "run-1", {"units": []}, result(), gate_bad)
        self.assertEqual((report["cleanup_state"], report["evidence_state"]),
                         ("cleaned", "incomplete"),
                         "没有跑完不等于没有清理，两个事实必须分开")
        broken = {"status": "passed", "rc": 0, "supervision": {"cleanup_state": "unknown"}}
        report = cleanup.assess_run(self.root, "run-1", {"units": []}, broken, gate_ok)
        self.assertEqual(report["cleanup_state"], "unknown")

    def test_validate_assessment_rejects_contradiction(self):
        assessment = {"cleanup_state": "cleaned", "problems": [{"kind": "pending"}],
                      "retained_paths": [], "target": {"cleanup_state": "cleaned"}}
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_assessment(assessment)
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_assessment(None)


class FinalizeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-cleanup-finalize-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.fix = self.root / "fixture"
        self.legacy = Path(str(self.fix) + ".legacy")

    def owned(self, path):
        fixture_scope.reset(path)
        (path / "payload").write_text("x")

    def assessment(self, state="cleaned", problems=None, retained=None):
        return {"cleanup_state": state, "problems": problems or [],
                "retained_paths": retained or [], "reasons": [],
                "target": {"cleanup_state": "cleaned", "status": "passed", "rc": 0},
                "evidence_state": "complete"}

    def test_cleaned_finalize_removes_owned_resources_in_role_order(self):
        self.owned(self.fix)
        self.owned(self.legacy)
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment())
        self.assertEqual(report["cleanup_state"], "cleaned")
        self.assertEqual(report["removed"], ["FIX", "LEGACY_FIXTURE_ROOT"])
        self.assertFalse(self.fix.exists())
        self.assertFalse(self.legacy.exists())

    def test_unknown_assessment_never_deletes(self):
        self.owned(self.fix)
        report = cleanup.finalize(self.results, {"fix": str(self.fix)},
                                  self.assessment("unknown"))
        self.assertEqual(report["removed"], [])
        self.assertTrue(self.fix.exists())
        self.assertIn("FIX", report["not_attempted"])

    def test_removal_failure_stops_and_reports_partial_completion(self):
        self.owned(self.fix)
        self.owned(self.legacy)
        # 先删 FIX，再让 LEGACY 的 marker 消失：第二次删除必须拒绝（未 owned），报告部分完成。
        original = fixture_scope.remove

        def failing(path, forbidden=()):
            if str(path) == str(self.legacy):
                raise fixture_scope.FixtureError("injected refusal")
            return original(path, forbidden)

        fixture_scope.remove = failing
        self.addCleanup(lambda: setattr(fixture_scope, "remove", original))
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment())
        self.assertEqual(report["cleanup_state"], "failed")
        self.assertEqual(report["removed"], ["FIX"])
        self.assertEqual(report["failed"], ["LEGACY_FIXTURE_ROOT"])
        self.assertFalse(self.fix.exists())
        self.assertTrue(self.legacy.exists())

    def test_unowned_fixture_path_is_reported_not_silently_skipped(self):
        self.fix.mkdir()
        (self.fix / "foreign").write_text("x")
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment())
        self.assertEqual(report["cleanup_state"], "failed")
        self.assertEqual(report["failed"], ["FIX"])
        self.assertTrue((self.fix / "foreign").exists())


    def test_single_root_partial_rmtree_failure_keeps_marker_and_remainder(self):
        self.owned(self.fix)
        (self.fix / "second").write_text("y")
        original = fixture_scope.shutil.rmtree

        def failing(path, *args, **kwargs):
            target = Path(path)
            first = sorted(target.iterdir())[0]
            if first.is_file():
                first.unlink()
            raise OSError("injected partial rmtree failure")

        fixture_scope.shutil.rmtree = failing
        self.addCleanup(lambda: setattr(fixture_scope.shutil, "rmtree", original))
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment())
        self.assertEqual(report["cleanup_state"], "failed")
        self.assertEqual(report["failed"], ["FIX"])
        self.assertTrue(fixture_scope.marker(self.fix).is_file(), "marker 必须保留")
        self.assertTrue(any(self.fix.iterdir()), "未删尽的字节必须保留供复核")
        self.assertIn(str(self.fix), report["retained_paths"])



class FaultSeamTest(unittest.TestCase):
    """受限故障点：只影响被点名的 finalize/删除，不伪造清理成功。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-cleanup-fault-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.fix = self.root / "fixture"
        self.legacy = Path(str(self.fix) + ".legacy")
        for path in (self.fix, self.legacy):
            fixture_scope.reset(path)
            (path / "payload").write_text("x")
        self.assessment = {"cleanup_state": "cleaned", "problems": [],
                           "retained_paths": [], "reasons": [],
                           "target": {"cleanup_state": "cleaned", "status": "passed", "rc": 0},
                           "evidence_state": "complete"}

    def with_fault(self, name):
        os.environ["WF_TEST_FAULT_INJECTION"] = "1"
        os.environ["WF_RUNNER_FINALIZE_FAULT"] = name
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_TEST_FAULT_INJECTION", "WF_RUNNER_FINALIZE_FAULT")])

    def test_unknown_selector_or_missing_scope_is_refused(self):
        os.environ["WF_TEST_FAULT_INJECTION"] = "1"
        os.environ["WF_RUNNER_FINALIZE_FAULT"] = "bogus"
        self.addCleanup(lambda: [os.environ.pop(key, None) for key in
                                 ("WF_TEST_FAULT_INJECTION", "WF_RUNNER_FINALIZE_FAULT")])
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_fault_selector()

    def test_delete_oserror_stops_before_the_first_removal(self):
        self.with_fault("delete-oserror")
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment)
        self.assertEqual(report["cleanup_state"], "failed")
        self.assertEqual(report["failed"], ["FIX"])
        self.assertEqual(report["removed"], [])
        self.assertIn("LEGACY_FIXTURE_ROOT", report["not_attempted"])
        self.assertTrue(self.fix.exists())
        self.assertTrue(self.legacy.exists())

    def test_delete_after_first_reports_exact_partial_completion(self):
        self.with_fault("delete-after-first")
        report = cleanup.finalize(self.results, {"fix": str(self.fix)}, self.assessment)
        self.assertEqual(report["cleanup_state"], "failed")
        self.assertEqual(report["removed"], ["FIX"])
        self.assertEqual(report["failed"], ["LEGACY_FIXTURE_ROOT"])
        self.assertFalse(self.fix.exists())
        self.assertTrue(self.legacy.exists())
        self.assertEqual(report["retained_paths"], [str(self.legacy)])




class CliTest(unittest.TestCase):
    def test_cli_requires_inputs_and_reports_state(self):
        import subprocess

        proc = subprocess.run([os.sys.executable, str(FULL / "runner_cleanup.py")],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()