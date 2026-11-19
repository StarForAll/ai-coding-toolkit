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
        # 行级失败不是证据缺口：聚合 bad 只表示“未通过”，归因来自单元 typed outcome。
        gate_bad = {"ok": False, "gate": {"malformed": 0, "bad": ["x"]}, "counts": {},
                    "repro": {}}
        report = cleanup.assess_run(self.root, "run-1", {"units": []}, result(), gate_bad)
        self.assertEqual((report["cleanup_state"], report["evidence_state"]),
                         ("cleaned", "complete"),
                         "没有跑完不等于没有清理；行级失败也不等于证据缺失")
        # 结果行结构坏损才是证据缺口。
        gate_broken = {"ok": False, "gate": {"malformed": 1, "bad": []}, "counts": {},
                       "repro": {}}
        report = cleanup.assess_run(self.root, "run-1", {"units": []}, result(), gate_broken)
        self.assertEqual(report["evidence_state"], "incomplete")
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

    def test_missing_unit_still_gets_an_unverified_outcome(self):
        """结果结构缺失：每个计划单元都有 outcome 占位，evidence 不完整。"""
        (self.root / "lines").write_text("u\t1\t1\tbad\tmissing\n")
        gate = {"ok": False, "gate": {"malformed": 0, "missing": ["u"], "duplicate": [],
                                      "unexpected": [], "bad": ["u"]}, "counts": {}, "repro": {}}
        report = cleanup.assess_run(self.root, "run-1", {"units": [{"name": "u"}]},
                                    result(state="cleaned"), gate)
        self.assertEqual(report["unit_outcomes"], [{"unit": "u", "outcome": "unverified"}])
        self.assertEqual(report["outcome_counts"]["unverified"], 1)
        self.assertEqual(report["evidence_state"], "incomplete")

    def test_typed_outcomes_come_from_same_generation_unit_evidence(self):
        """真实文件接线：receipt 终态 + row/result 一致才给出 assertion_failed。"""
        results = self.root
        commands = results / "commands"
        commands.mkdir()
        (results / "lines").write_text("u\t1\t1\tbad\tsaved 0 / 1\n")
        receipt_path = commands / "c1.json"
        lifecycle.write_receipt(receipt_path, {
            "schema_version": 1, "command_id": "c1", "run_id": "run-1",
            "evidence_scope": "managed-child", "state": "finished",
            "local_cleanup": "none", "log_path": str(results / "u.log"),
            "argv": ["bash", "suite.sh"],
            "result": {"status": "failed", "rc": 1},
            "supervision": {"cleanup_state": "cleaned", "infrastructure_error": False,
                            "target_rc": 0}})
        unit_path = results / "u.test.log.json"
        unit_path.write_text(json.dumps({
            "schema_version": 2, "name": "u", "status": "failed", "rc": 1,
            "assertion_result": {"ok": False, "failures": 1, "counts_complete": True,
                                 "expected": 1, "observed": 0},
            "supervision": {"cleanup_state": "cleaned", "infrastructure_error": False,
                            "target_rc": 0},
            "unit_execution": {"schema_version": 1, "unit": "u", "run_id": "run-1",
                               "invocation_id": "inv", "state": "passed",
                               "result_row": ["u", "1", "1", "bad", "saved 0 / 1"],
                               "command_evidence": [{"phase": "test", "command_id": "c1",
                                                     "evidence_path": str(receipt_path),
                                                     "result_path": str(unit_path)}]}}))
        gate = {"ok": False, "gate": {"malformed": 0, "missing": [], "duplicate": [],
                                      "unexpected": [], "bad": ["u"]},
                "counts": {}, "repro": {}}
        report = cleanup.assess_run(results, "run-1", {"units": [{"name": "u"}]},
                                    result(), gate)
        self.assertEqual(report["evidence_state"], "complete")
        self.assertEqual(report["unit_outcomes"], [{"unit": "u", "outcome": "assertion_failed"}])
        self.assertEqual(report["outcome_counts"]["assertion_failed"], 1)
        # 错代 receipt → unverified，证据不完整。
        record = json.loads(unit_path.read_text())
        record["unit_execution"]["command_evidence"][0]["evidence_path"] = str(
            commands / "missing.json")
        unit_path.write_text(json.dumps(record))
        report = cleanup.assess_run(results, "run-1", {"units": [{"name": "u"}]},
                                    result(), gate)
        self.assertEqual(report["evidence_state"], "incomplete")
        self.assertEqual(report["outcome_counts"]["unverified"], 1)


class ClassifyUnitTest(unittest.TestCase):
    """单元分类器的唯一判据：row × unit_execution × test result × receipts。"""

    RESULT_PATH = "/results/unit.test.log.json"

    def unit_execution(self, state="passed", **overrides):
        record = {"schema_version": 1, "unit": "unit", "run_id": "run-1",
                  "invocation_id": "inv", "state": state,
                  "result_row": ["unit", "1", "2", "bad", "saved 0 / 1"],
                  "command_evidence": [{"phase": "test"}]}
        record.update(overrides)
        return record

    def result(self, *, rc=1, status="failed", target_rc=0, failures=1,
               counts_complete=True, assertion_ok=False):
        return {"rc": rc, "status": status,
                "assertion_result": {"ok": assertion_ok, "failures": failures,
                                     "counts_complete": counts_complete,
                                     "expected": 1, "observed": 0},
                "supervision": {"cleanup_state": "cleaned", "target_rc": target_rc}}

    def test_receipt(self, phase="test", status="failed", path=None, rc=None):
        codes = {"passed": 0, "failed": 1, "cancelled": 143, "timeout": 124}
        return {"phase": phase, "command_id": "c1",
                "result": {"status": status, "rc": codes[status] if rc is None else rc},
                "result_path": path or self.RESULT_PATH}

    def classify(self, result, receipts=None, problems=None, unit_execution=None, row=None):
        if row is None:
            rc = result.get("rc") if isinstance(result, dict) else 1
            row = ["unit", str(rc), "2", "ok" if rc == 0 else "bad", "x"]
        return cleanup.classify_unit(unit_execution or self.unit_execution(), result, row,
                                     receipts if receipts is not None
                                     else [self.test_receipt()],
                                     problems or [], self.RESULT_PATH)

    def test_assertion_failure_requires_zero_target_rc_and_complete_counts(self):
        outcome, _ = self.classify(self.result())
        self.assertEqual(outcome, "assertion_failed")
        for result in (self.result(target_rc=0, counts_complete=False),
                       self.result(target_rc=0, failures=0, assertion_ok=False),
                       self.result(target_rc=0, failures=0, assertion_ok=True,
                                   counts_complete=False)):
            with self.subTest(result=result):
                self.assertEqual(self.classify(result)[0], "unverified",
                                 "计数不完整或没有显式 FAIL 时不得归为断言失败")

    def test_nonzero_target_is_execution_failure_not_assertion(self):
        outcome, reason = self.classify(
            self.result(rc=2, target_rc=2, failures=0, counts_complete=False),
            receipts=[self.test_receipt(status="failed", rc=2)])
        self.assertEqual(outcome, "execution_failed")
        self.assertIn("target rc=2", reason)
        # 目标失败但断言自称通过：矛盾。
        contradiction = self.result(rc=2, target_rc=2, assertion_ok=True)
        self.assertEqual(self.classify(contradiction, receipts=[
            self.test_receipt(status="failed", rc=2)])[0], "unverified")

    def test_receipt_result_must_match_the_unit_result(self):
        outcome, reason = self.classify(
            self.result(rc=2, target_rc=2, failures=0, counts_complete=False),
            receipts=[self.test_receipt(status="failed", rc=1)])
        self.assertEqual(outcome, "unverified")
        self.assertIn("receipt result differs", reason)

    def test_passed_requires_complete_and_consistent_facts(self):
        passed = self.result(rc=0, status="passed", target_rc=0, failures=0,
                             assertion_ok=True)
        self.assertEqual(self.classify(passed, receipts=[
            self.test_receipt(status="passed")])[0], "passed")
        row_mismatch = passed
        outcome, _ = cleanup.classify_unit(
            self.unit_execution(), row_mismatch, ["unit", "2", "2", "bad", "x"],
            [self.test_receipt()], [], self.RESULT_PATH)
        self.assertEqual(outcome, "unverified")

    def test_missing_or_mismatched_receipt_is_unverified(self):
        self.assertEqual(self.classify(self.result(), receipts=[], )[0], "unverified")
        wrong_path = self.test_receipt(path="/results/other.json")
        self.assertEqual(self.classify(self.result(), receipts=[wrong_path])[0],
                         "unverified")
        self.assertEqual(self.classify(self.result(), problems=["receipt unreadable"])[0],
                         "unverified")
        execution_without_test = self.unit_execution(
            command_evidence=[{"phase": "fixture"}])
        self.assertEqual(self.classify(self.result(), receipts=[],
                                       unit_execution=execution_without_test)[0],
                         "unverified")

    def test_cancelled_requires_agreeing_receipt(self):
        cancelled = self.result(rc=143, status="cancelled", target_rc=0, failures=0,
                                counts_complete=False)
        receipt = self.test_receipt(status="cancelled")
        self.assertEqual(self.classify(cancelled, receipts=[receipt])[0], "cancelled")
        disagreeing = self.test_receipt(status="failed")
        self.assertEqual(self.classify(cancelled, receipts=[disagreeing])[0], "unverified")

    def test_cleanup_facts_do_not_change_the_typed_outcome(self):
        """清理成功/未知/失败只影响 cleanup_state，不改变单元分类。"""
        for state in ("cleaned", "unknown", "failed"):
            result = self.result(target_rc=0)
            result["supervision"]["cleanup_state"] = state
            self.assertEqual(self.classify(result)[0], "assertion_failed", state)
            execfail = self.result(rc=2, target_rc=2, failures=0, counts_complete=False)
            execfail["supervision"]["cleanup_state"] = state
            self.assertEqual(self.classify(execfail, receipts=[
                self.test_receipt(status="failed", rc=2)])[0],
                "execution_failed", state)
            cancelled = self.result(rc=143, status="cancelled", target_rc=0, failures=0,
                                    counts_complete=False)
            cancelled["supervision"]["cleanup_state"] = state
            self.assertEqual(self.classify(cancelled, receipts=[
                self.test_receipt(status="cancelled")])[0], "cancelled", state)
            prepared = self.unit_execution(state="prep-failed", failure_reason="INSTALL-FAILED")
            self.assertEqual(cleanup.classify_unit(
                prepared, {"status": "failed", "rc": 1},
                ["unit", "1", "0", "bad", "INSTALL-FAILED"],
                [self.test_receipt(phase="install")], [], self.RESULT_PATH)[0],
                "preparation_failed", state)

    def test_preparation_failure_is_never_an_assertion_failure(self):
        execution = self.unit_execution(state="prep-failed", failure_reason="INSTALL-FAILED",
                                        command_evidence=[])
        result = {"status": "failed", "rc": 1, "reason": "INSTALL-FAILED"}
        outcome, _ = cleanup.classify_unit(execution, result, ["unit", "1", "0", "bad", "x"],
                                           [], [], self.RESULT_PATH)
        self.assertEqual(outcome, "unverified",
                         "已启动准备阶段但缺 receipt：证据不足，不是可下结论的准备失败")
        receipt = self.test_receipt(phase="install", status="failed")
        outcome, _ = cleanup.classify_unit(execution, result, ["unit", "1", "0", "bad", "x"],
                                           [receipt], [], self.RESULT_PATH)
        self.assertEqual(outcome, "preparation_failed")
        preflight = self.unit_execution(state="prep-failed", failure_reason="FIXTURE-FAILED",
                                        command_evidence=[], preflight_failed=True)
        outcome, _ = cleanup.classify_unit(preflight, result, ["unit", "1", "0", "bad", "x"],
                                           [], [], self.RESULT_PATH)
        self.assertEqual(outcome, "preparation_failed")
        unlabeled = self.unit_execution(state="prep-failed", failure_reason="",
                                        command_evidence=[], preflight_failed=True)
        outcome, _ = cleanup.classify_unit(unlabeled, result, ["unit", "1", "0", "bad", "x"],
                                           [], [], self.RESULT_PATH)
        self.assertEqual(outcome, "unverified",
                         "preflight failure without a recorded reason is not classifiable")
        contradictory = self.test_receipt(phase="install", status="passed")
        outcome, _ = cleanup.classify_unit(execution, result, ["unit", "1", "0", "bad", "x"],
                                           [contradictory], [], self.RESULT_PATH)
        self.assertEqual(outcome, "unverified")


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