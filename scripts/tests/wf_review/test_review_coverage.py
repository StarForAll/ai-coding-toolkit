"""D1/D2：主会话复核、两源覆盖与缺口接受。

防的失败（dogfood）：
- 覆盖按报告并集算：A 五轴 pass、B 五轴 uncovered 仍算全覆盖——"名义两位、实质一位"；
- 五轴全 uncovered 的报告自报 pass；`scope-exceptions` 自述越界仍 pass；
- 主会话没有自己的逐轴结论，报告成了唯一证据源。

断言：
1. 产生 verdict 必须带主会话复核；缺复核 → `WF_REVIEW_INVALID`；
2. 覆盖 = 主会话复核 ∪ 主会话采信的报告；两者都未覆盖才是缺口；
3. 全部轴未覆盖 → 输入不成立（`WF_REVIEW_INVALID`）；
4. 部分未覆盖且无人接受 → 需人裁决档（`WF_SEMANTIC_DECISION`）；
5. 人接受缺口（`by/at/quote/source + round + axes`）→ 可产生判定，接受记录入库；
6. 主会话 `fail` 必须指回未关闭 blocking；`pass` 不能覆盖未关闭 blocking；
7. 复核不可在判定后替换；`report_review`/`finding_review` 必须覆盖每份报告与每条 finding。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review, tasks as tasks_mod  # noqa: E402

ANCHOR = "sha256:" + "c" * 64
MARKER = review.REPORT_MARKER
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
AXES = {name: "pass" for name in review.REVIEW_AXES}


class Ctx:
    def __init__(self, root):
        self.root = str(root)

    def key(self):
        return "sess-test"

    def rule_version(self):
        return "test-rule"

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


def report_text(axes, findings=()):
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-12T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
            "axes": dict(axes), "findings": list(findings),
            "verdict": ("fail" if any(item.get("severity") in review.BLOCKING_SEVERITIES
                                      for item in findings if isinstance(item, dict))
                        else ("unavailable" if all(review._axis_conclusion(value) == "uncovered"
                                                   for value in axes.values()) else "pass"))}
    return ("<!-- wf-review-agent:v1 status=done -->\n" + MARKER
            + "\n\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```\n")


class DecideHarness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = Ctx(self.root)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)
        self.findings = []
        self.findings_by_slot = {}

    def tearDown(self):
        self._tmp.cleanup()

    def stage(self, axes, findings=(), per_slot=None):
        imported, seen = [], []
        self.findings = list(findings)
        self.findings_by_slot = {}
        for slot, agent in (("s1", "pi"), ("s2", "zcode")):
            slot_axes = dict(axes)
            slot_findings = list(findings)
            if per_slot and slot in per_slot:
                override = per_slot[slot]
                slot_axes = dict(override.get("axes", slot_axes))
                slot_findings = list(override.get("findings", slot_findings))
            relative = f".wf/tasks/t1/review/round-1/review-{agent}.md"
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report_text(slot_axes, slot_findings), encoding="utf-8")
            self.findings_by_slot[slot] = slot_findings
            imported.append({"round": 1, "slot": slot, "agent": agent, "report_path": relative,
                             "report_digest": records.file_digest(path),
                             "anchor": {"check_anchor": ANCHOR}})
            seen.append(relative)
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": "in_progress", "phase": "check", "revision": 1,
            "check": {"id": "c1", "result": "pass",
                      "anchor": {"check_anchor": ANCHOR, "parts": {}},
                      "commands": [{"verification_id": "v1", "status": "passed"}]},
            "entry_snapshot": {"touch_paths": []},
            "plan": {"complexity": "complex", "acceptance": [{"id": "a:1"}],
                     "verifications": [{"id": "v1"}]},
            "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                      "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                      "temp_paths": []}],
                        "imported": imported}})

    def main_review(self, axes=None, report_review=None, finding_review=None,
                    sources=None, **overrides):
        conclusions = dict(axes or {axis: "pass" for axis in review.REVIEW_AXES})
        source_map = sources or {}
        payload = {
            "task": "t1", "round": 1,
            "axes": {axis: {"conclusion": conclusions.get(axis, "pass"),
                            "basis": "主会话复核依据",
                            "sources": list(source_map.get(axis, ["main"])),
                            "finding_refs": []} for axis in review.REVIEW_AXES},
            "report_review": (report_review if report_review is not None else [
                {"slot": "s1", "reliance": "primary", "notes": "报告覆盖与依据可用"},
                {"slot": "s2", "reliance": "primary", "notes": "报告覆盖与依据可用"}]),
            "finding_review": finding_review if finding_review is not None else [
                {"finding_id": finding.get("id"), "slot": slot, "check": "verified",
                 "basis": "本地复核"}
                for slot, slot_findings in (self.findings_by_slot or {}).items()
                for finding in slot_findings],
        }
        for axis, refs in (overrides.pop("finding_refs", {}) or {}).items():
            payload["axes"][axis]["finding_refs"] = refs
        payload.update(overrides)
        path = self.root / "main-review.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def decide(self, acceptance=None, main_review=None, plan=None, register_only=False,
               check_valid=True, approved=True):
        captured = {}
        file_path = None
        plan_path = None
        if acceptance is not None:
            file_path = str(self.root / "gap.json")
            Path(file_path).write_text(json.dumps(acceptance, ensure_ascii=False), encoding="utf-8")
        if plan is not None:
            plan_path = str(self.root / "plan.json")
            Path(plan_path).write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        if register_only and main_review is None:
            main_path = None
        else:
            main_path = main_review if main_review is not None else self.main_review()

        def _start(_ctx, path, task, *_args, **_kwargs):
            captured["task"] = json.loads(json.dumps(task))
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        def _finish(_ctx, path, task, *_args, **_kwargs):
            records.write_json(os.path.join(path, "task.json"), task)
            return task, {"ok": True}

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "standard_drift_gate", return_value=[]), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action", _finish):
            validity = ({"valid": True, "code": None, "facts": {}, "blockers": []}
                        if check_valid else
                        {"valid": False, "code": "WF_CHECK_STALE",
                         "facts": {"reason": "invalidated"}, "blockers": ["invalidated"]})
            with mock.patch("wflib.gates.check_validity", return_value=validity), \
                    mock.patch("wflib.tasks._is_approved_plan", return_value=approved):
                result = review.decide(self.ctx, {"id": "t1"}, 1, gap_acceptance_path=file_path,
                                       plan_path=plan_path, main_review_path=main_path,
                                       register_only=register_only)
        return result, captured.get("task") or {}


class CoverageMergeTest(unittest.TestCase):
    def test_reports_and_main_review_are_merged(self):
        state = review.merged_coverage(
            {"axes": {"range": "uncovered", "acceptance": "pass"},
             "report_review": [{"slot": "s1", "reliance": "primary", "notes": "ok"},
                               {"slot": "s2", "reliance": "primary", "notes": "ok"}]},
            {"s1": {"range": "pass", "acceptance": "uncovered"},
             "s2": {"range": "uncovered", "acceptance": "fail"}})
        self.assertEqual(state["covered"], ["acceptance", "range"])
        self.assertEqual(state["uncovered"], ["contract", "regression", "testability"])
        self.assertEqual(state["sources"]["range"], ["s1"])
        self.assertEqual(state["sources"]["acceptance"], ["main", "s2"])
        self.assertFalse(state["all_uncovered"])

    def test_main_review_alone_can_cover_an_axis(self):
        state = review.merged_coverage(
            {"axes": {"range": "pass"},
             "report_review": [{"slot": "s1", "reliance": "primary", "notes": "ok"}]},
            {"s1": {"range": "uncovered"}})
        self.assertIn("range", state["covered"])
        self.assertEqual(state["sources"]["range"], ["main"])

    def test_both_sources_uncovered_is_a_gap(self):
        state = review.merged_coverage(
            {"axes": {"range": "uncovered", "contract": "pass"},
             "report_review": [{"slot": "s1", "reliance": "primary", "notes": "ok"}]},
            {"s1": {"range": "uncovered", "contract": "uncovered"}})
        self.assertFalse(state["all_uncovered"])
        self.assertIn("range", state["uncovered"])
        self.assertNotIn("contract", state["uncovered"])

    def test_no_source_covers_anything(self):
        state = review.merged_coverage(
            {"axes": {axis: "uncovered" for axis in review.REVIEW_AXES},
             "report_review": [{"slot": "s1", "reliance": "primary", "notes": "ok"}]},
            {"s1": {axis: "uncovered" for axis in review.REVIEW_AXES}})
        self.assertTrue(state["all_uncovered"])
        self.assertEqual(state["covered"], [])

    def test_projection_tolerates_malformed_axes(self):
        state = review.merged_coverage(None, {"s1": ["range"], "s2": None, "s3": {"range": "pass"}})
        self.assertEqual(state["covered"], ["range"])
        self.assertFalse(state["all_uncovered"])
        self.assertFalse(state["adopted"])

    def test_reliance_none_does_not_cover(self):
        main = {"axes": {axis: "uncovered" for axis in review.REVIEW_AXES},
                "report_review": [{"slot": "s1", "reliance": "none", "notes": "不采信"},
                                  {"slot": "s2", "reliance": "none", "notes": "不采信"}]}
        state = review.merged_coverage(
            main, {"s1": {axis: "pass" for axis in review.REVIEW_AXES},
                   "s2": {axis: "pass" for axis in review.REVIEW_AXES}})
        self.assertTrue(state["all_uncovered"])
        self.assertEqual(state["covered"], [])

    def test_partial_only_counts_axes_cited_by_the_main_review(self):
        main = {"axes": {
                    "range": {"conclusion": "uncovered", "basis": "交报告", "sources": ["s1"]},
                    "acceptance": {"conclusion": "uncovered", "basis": "只看主会话", "sources": ["main"]},
                    "contract": "uncovered", "regression": "uncovered", "testability": "uncovered"},
                "report_review": [{"slot": "s1", "reliance": "partial", "notes": "部分采信"}]}
        state = review.merged_coverage(
            main, {"s1": {"range": "pass", "acceptance": "pass",
                          "contract": "uncovered", "regression": "uncovered",
                          "testability": "uncovered"}})
        self.assertEqual(state["covered"], ["range"])
        self.assertEqual(state["sources"]["range"], ["s1"])
        self.assertIn("acceptance", state["uncovered"])


class CrossRoundClosureTest(unittest.TestCase):
    """旧轮 unable 被后续轮 accepted 取代时，证据要求照旧（不能"换一轮就免证据"）。"""

    KEY = (1, "main", "m1")

    def _disposition(self, **overrides):
        item = {"finding_id": "m1", "round": 1, "slot": "main", "decision": "accepted",
                "reason": "已修", "recheck_by": "human:xzc", "submitted_round": 2}
        item.update(overrides)
        return item

    def test_later_round_acceptance_without_evidence_is_rejected(self):
        problems = review.verified_closure_problems(
            [self._disposition()], None, {self.KEY: "main"}, 2,
            main_checks={self.KEY: "unable"}, current_dispositions=[self._disposition()])
        self.assertIn("verified finding closure requires evidence_refs",
                      json.dumps(problems, ensure_ascii=False))

    def test_later_round_acceptance_with_evidence_passes(self):
        problems = review.verified_closure_problems(
            [self._disposition(evidence_refs=["v:v1"])], None, {self.KEY: "main"}, 2,
            main_checks={self.KEY: "unable"},
            evidence_check=lambda refs, check_id=None: [],
            current_dispositions=[self._disposition(evidence_refs=["v:v1"])])
        self.assertEqual(problems, [])


class GapAcceptanceTest(unittest.TestCase):
    def _decision(self, **overrides):
        decision = {"by": "human:xzc", "at": "2026-11-12T00:00:00Z",
                    "quote": "我接受这些轴这次没看，理由：材料不足", "source": "user-declared",
                    "task": "t1", "round": 1, "axes": ["contract"]}
        decision.update(overrides)
        return decision

    def test_acceptance_must_match_task_when_task_id_is_given(self):
        record, problems = review.gap_acceptance(self._decision(), ["contract"], 1,
                                                 task_id="t1")
        self.assertEqual(problems, [])
        _record, problems = review.gap_acceptance(self._decision(task="other"),
                                                   ["contract"], 1, task_id="t1")
        self.assertTrue(problems)

    def test_acceptance_must_match_axes_and_round(self):
        record, problems = review.gap_acceptance(self._decision(), ["contract"], 1)
        self.assertEqual(problems, [])
        self.assertTrue(record["attestation_digest"].startswith("sha256:"))
        _record, problems = review.gap_acceptance(self._decision(axes=["range"]), ["contract"], 1)
        self.assertTrue(problems)
        _record, problems = review.gap_acceptance(self._decision(round=2), ["contract"], 1)
        self.assertTrue(problems)
        _record, problems = review.gap_acceptance(self._decision(by="ai"), ["contract"], 1)
        self.assertTrue(problems)


class ReviewScopeFactsTest(unittest.TestCase):
    def test_unselected_paths_are_recorded_for_the_verdict(self):
        from types import SimpleNamespace

        task = {"id": "t1", "entry_snapshot": {"touch_paths": ["pkg/a.py", "pkg/b.py"]}}
        launch = {"submitted_scope": {"diff": {"paths": ["pkg/a.py"]}},
                  "scope": {"selected": 1, "total": 2, "narrowed": True}}
        with mock.patch.object(review.scope_mod, "delivery_set",
                               return_value={"paths": ["pkg/a.py", "pkg/b.py"]}):
            facts = review.review_scope_facts(SimpleNamespace(root="."), task, launch)
        self.assertEqual(facts["selected"], ["pkg/a.py"])
        self.assertEqual(facts["unselected"], ["pkg/b.py"])
        self.assertTrue(facts["narrowed"])
        self.assertFalse(facts["legacy"])

    def test_legacy_recompute_failure_is_visible(self):
        from types import SimpleNamespace

        task = {"id": "t1", "entry_snapshot": {"touch_paths": []}}
        launch = {"submitted_scope": {"diff": True}, "scope": {},
                  "exclusions": []}
        with mock.patch.object(review.scope_mod, "delivery_set",
                               side_effect=RuntimeError("boom")):
            facts = review.review_scope_facts(SimpleNamespace(root="."), task, launch)
        self.assertTrue(facts["scope_recompute_failed"])
        self.assertIsNone(facts["selected"])


class VerifiedClosureTest(unittest.TestCase):
    def test_existing_disposition_without_evidence_is_rejected(self):
        main = {"finding_review": [{"finding_id": "f1", "slot": "s1", "check": "verified",
                                   "basis": "已核实"}]}
        dispositions = [{"finding_id": "f1", "slot": "s1", "round": 1,
                         "decision": "accepted", "reason": "已修复",
                         "recheck_by": "human:xzc"}]
        problems = review.verified_closure_problems(
            dispositions, main, {(1, "s1", "f1"): "pi"}, 1)
        self.assertTrue(problems)
        self.assertEqual(problems[0]["reason"],
                         "verified finding closure requires evidence_refs")

    def test_cross_round_main_closure_needs_evidence(self):
        dispositions = [{"finding_id": "mf1", "slot": "main", "round": 1,
                         "decision": "accepted", "reason": "已修复",
                         "recheck_by": "human:xzc"}]
        problems = review.verified_closure_problems(
            dispositions, {"round": 2, "finding_review": []},
            {(1, "main", "mf1"): "main"}, 2,
            main_checks={(1, "main", "mf1"): "verified"})
        self.assertTrue(problems)
        self.assertEqual(problems[0]["reason"],
                         "verified finding closure requires evidence_refs")


class DecideMainReviewTest(DecideHarness):
    def test_missing_main_review_is_an_input_error(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review="")
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")

    def test_main_review_can_cover_a_reviewer_gap(self):
        self.stage({**AXES, "contract": "uncovered"})
        result, task = self.decide()
        self.assertEqual(result["code"], "WF_OK")
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        coverage = result["facts"]["result"]["facts"]["coverage"]
        self.assertEqual(coverage["uncovered"], [])
        self.assertEqual(coverage["sources"]["contract"], ["main"])
        self.assertTrue(task["reviews"]["main_reviews"])

    def test_all_uncovered_from_both_sources_produces_no_verdict(self):
        self.stage({axis: "uncovered" for axis in review.REVIEW_AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(
                axes={axis: "uncovered" for axis in review.REVIEW_AXES}))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertEqual(caught.exception.facts["covered"], [])

    def test_partial_gap_needs_a_human_decision(self):
        self.stage({**AXES, "contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(axes={"contract": "uncovered"}))
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertEqual(caught.exception.facts["uncovered"], ["contract"])

    def test_accepted_gap_allows_a_verdict_and_is_recorded(self):
        self.stage({**AXES, "contract": "uncovered"})
        result, task = self.decide(
            acceptance=GapAcceptanceTest()._decision(),
            main_review=self.main_review(axes={"contract": "uncovered"}))
        self.assertEqual(result["code"], "WF_OK")
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        coverage = result["facts"]["result"]["facts"]["coverage"]
        self.assertEqual(coverage["uncovered"], ["contract"])
        recorded = task["reviews"]["coverage_acceptances"]
        self.assertEqual(recorded[-1]["axes"], ["contract"])

    def test_mismatched_acceptance_is_rejected(self):
        self.stage({**AXES, "contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(acceptance=GapAcceptanceTest()._decision(axes=["range"]),
                        main_review=self.main_review(axes={"contract": "uncovered"}))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")

    def test_blocking_findings_still_fail(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        result, _task = self.decide(
            main_review=self.main_review(axes={"regression": "fail"},
                                         finding_refs={"regression": [{"finding_id": "f1", "slot": "s1"}]}))
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_main_review_fail_without_finding_is_an_input_error(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(axes={"regression": "fail"}))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        text = json.dumps(caught.exception.facts, ensure_ascii=False)
        self.assertIn("finding", text)
        self.assertIn("judgment", text)
        self.assertIn("不要伪造 reviewer finding", text)

    def test_main_review_pass_cannot_override_open_blocking(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        result, _task = self.decide()
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_main_review_cannot_cite_an_unrelied_report(self):
        self.stage({**AXES})
        main = self.main_review(
            report_review=[{"slot": "s1", "reliance": "none", "notes": "不采信"},
                           {"slot": "s2", "reliance": "primary", "notes": "采信"}],
            sources={"range": ["s1"]})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("does not rely on", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_main_review_cannot_cite_a_report_that_did_not_cover_the_axis(self):
        self.stage({**AXES}, per_slot={"s1": {"axes": {**AXES, "range": "uncovered"}}})
        main = self.main_review(sources={"range": ["s1"]})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("did not cover", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_main_review_sources_are_not_relabelled_as_main(self):
        self.stage({**AXES}, per_slot={"s2": {"axes": {**AXES, "range": "uncovered"}}})
        result, _task = self.decide(main_review=self.main_review(sources={"range": ["s1"]}))
        coverage = result["facts"]["result"]["facts"]["coverage"]
        self.assertIn("s1", coverage["sources"]["range"])
        self.assertNotIn("main", coverage["sources"]["range"])

    def test_fail_round_allows_a_corrected_main_review(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        first, _task = self.decide()
        self.assertEqual(first["facts"]["result"]["verdict"], "fail")
        corrected = self.main_review(finding_review=[
            {"finding_id": "f1", "slot": "s1", "check": "disputed", "basis": "误报"},
            {"finding_id": "f1", "slot": "s2", "check": "disputed", "basis": "误报"}])
        plan = [{"finding_id": "f1", "round": 1, "slot": slot, "decision": "accepted",
                 "reason": "经复核认定误报", "recheck_by": "human:xzc"} for slot in ("s1", "s2")]
        second, task = self.decide(main_review=corrected, plan=plan)
        self.assertEqual(second["facts"]["result"]["verdict"], "pass")
        main_reviews = task["reviews"]["main_reviews"]
        self.assertEqual(len(main_reviews), 2)
        self.assertEqual(main_reviews[-1].get("supersedes"), main_reviews[0].get("file_digest"))

    def test_pass_cannot_keep_a_fail_axis_after_closing_the_finding(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        main = self.main_review(
            axes={"regression": "fail"},
            finding_refs={"regression": [{"finding_id": "f1", "slot": "s1"},
                                         {"finding_id": "f1", "slot": "s2"}]})
        first, _task = self.decide(main_review=main)
        self.assertEqual(first["facts"]["result"]["verdict"], "fail")
        plan = [{"finding_id": "f1", "round": 1, "slot": slot, "decision": "accepted",
                 "reason": "经复核认定误报", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:v1"]} for slot in ("s1", "s2")]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main, plan=plan)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertEqual(caught.exception.facts["fail_axes"], ["regression"])

    def test_report_bound_to_a_previous_check_id_is_rejected(self):
        self.stage({**AXES})
        record = records.load_json(self.task_dir / "task.json")
        record["check"]["id"] = "c2"
        records.write_json(self.task_dir / "task.json", record)
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("check_id", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_main_review_pass_cannot_cite_a_failed_report_axis(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES, "range": "fail"}, findings=[finding])
        main = self.main_review(sources={"range": ["s1"]})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("report axis that failed",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_verified_finding_closure_requires_evidence_refs(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        first, _task = self.decide()
        self.assertEqual(first["facts"]["result"]["verdict"], "fail")
        plan = [{"finding_id": "f1", "round": 1, "slot": slot, "decision": "accepted",
                 "reason": "已修复", "recheck_by": "human:xzc"} for slot in ("s1", "s2")]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(plan=plan)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("verified finding closure requires evidence_refs",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_narrowed_primary_report_needs_explicit_axis_source(self):
        self.stage({**AXES})
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["launches"][0]["scope"] = {"selected": 0, "total": 1, "narrowed": True}
        task["reviews"]["launches"][0]["submitted_scope"] = {"diff": {"paths": []}}
        records.write_json(self.task_dir / "task.json", task)
        main = self.main_review(axes={"contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("uncovered axis conflicts with a primary report",
                      json.dumps(caught.exception.facts, ensure_ascii=False))
        explicit = self.main_review(
            axes={"contract": "uncovered"},
            sources={"contract": ["s1"]},
            report_review=[{"slot": "s1", "reliance": "partial", "notes": "只采信 contract"},
                           {"slot": "s2", "reliance": "none", "notes": "不采信"}])
        result, _task = self.decide(main_review=explicit)
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        self.assertEqual(result["facts"]["result"]["facts"]["coverage"]["sources"]["contract"],
                         ["s1"])

    def test_known_blocking_fails_despite_uncovered_primary_conflict(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES, "contract": "fail"}, findings=[finding])
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["launches"][0]["scope"] = {"selected": 0, "total": 1, "narrowed": True}
        task["reviews"]["launches"][0]["submitted_scope"] = {"diff": {"paths": []}}
        records.write_json(self.task_dir / "task.json", task)
        main = self.main_review(
            axes={"range": "uncovered", "contract": "fail"},
            finding_refs={"contract": [{"finding_id": "f1", "slot": "s1"},
                                       {"finding_id": "f1", "slot": "s2"}]})
        result, _task = self.decide(main_review=main)
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        self.assertTrue(result["facts"]["result"]["facts"].get("coverage_conflicts"))

    def test_close_before_verify_still_needs_evidence_later(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc"},
                {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc"}]
        self.decide(plan=plan, register_only=True)
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("verified finding closure requires evidence_refs",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_decide_rejects_an_unapproved_plan(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(approved=False)
        self.assertEqual(caught.exception.code, "WF_APPROVAL_MISSING")

    def test_decide_rejects_an_invalid_check(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(check_valid=False)
        self.assertEqual(caught.exception.code, "WF_CHECK_STALE")

    def test_one_uncovered_reviewer_cannot_be_compensated_by_the_other(self):
        self.stage({**AXES}, per_slot={
            "s2": {"axes": {axis: "uncovered" for axis in review.REVIEW_AXES}}})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("slots_without_coverage", json.dumps(caught.exception.facts,
                                                            ensure_ascii=False))

    def test_main_coverage_cannot_replace_uncovered_reports(self):
        self.stage({axis: "uncovered" for axis in review.REVIEW_AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("独立 reviewer", json.dumps(caught.exception.facts,
                                                   ensure_ascii=False))

    def test_accepted_unable_cannot_close_blocking(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        main = self.main_review(
            finding_review=[{"finding_id": "f1", "slot": "s1", "check": "unable",
                             "basis": "尚未核实"}])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc"}]
        result, _task = self.decide(main_review=main, plan=plan)
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_explicit_historical_check_id_is_overridden(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        task = records.load_json(self.task_dir / "task.json")
        task["check"]["commands"] = [{"verification_id": "v1", "status": "failed"}]
        task["check_history"] = [{"id": "c-old",
                                  "commands": [{"verification_id": "v1", "status": "passed"}]}]
        records.write_json(self.task_dir / "task.json", task)
        main = self.main_review(
            finding_review=[{"finding_id": "f1", "slot": "s1", "check": "verified",
                             "basis": "本地复核"}])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc",
                 "check_id": "c-old", "evidence_refs": ["v:v1"]}]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main, plan=plan)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("did not pass", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_missing_bound_check_is_not_silently_rebound(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        task = records.load_json(self.task_dir / "task.json")
        # 已落盘的关闭绑定了一次不存在的 Check（旧记录）：不能退回当前 Check 解析同名验证项
        task["reviews"]["dispositions"] = [
            {"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
             "reason": "关闭", "recheck_by": "human:xzc", "check_id": "c-gone",
             "submitted_round": 1, "evidence_refs": ["v:v1"]}]
        records.write_json(self.task_dir / "task.json", task)
        main = self.main_review(
            finding_review=[{"finding_id": "f1", "slot": "s1", "check": "verified",
                             "basis": "本地复核"}])
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("no longer exists", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_current_closure_cannot_borrow_a_historical_pass(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        task = records.load_json(self.task_dir / "task.json")
        task["check"]["commands"] = [{"verification_id": "v1", "status": "failed"}]
        task["check_history"] = [{"id": "c0",
                                  "commands": [{"verification_id": "v1", "status": "passed"}]}]
        records.write_json(self.task_dir / "task.json", task)
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc", "evidence_refs": ["v:v1"]},
                {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc", "evidence_refs": ["v:v1"]}]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(plan=plan)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("did not pass", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_amended_latest_blocks_old_empty_evidence_check(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc"},
                {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc"}]
        self.decide(plan=plan, register_only=True)
        amended = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "amended",
                    "reason": "撤回关闭，问题仍开放", "recheck_by": "human:xzc"},
                   {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "amended",
                    "reason": "撤回关闭，问题仍开放", "recheck_by": "human:xzc"}]
        result, _task = self.decide(plan=amended)
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_valid_evidence_can_replace_an_empty_earlier_closure(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        empty = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                  "reason": "先关闭", "recheck_by": "human:xzc"},
                 {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                  "reason": "先关闭", "recheck_by": "human:xzc"}]
        self.decide(plan=empty, register_only=True)
        valid = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                  "reason": "补证据", "recheck_by": "human:xzc",
                  "evidence_refs": ["v:v1"]},
                 {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                  "reason": "补证据", "recheck_by": "human:xzc",
                  "evidence_refs": ["v:v1"]}]
        result, _task = self.decide(plan=valid)
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")

    def test_inferred_finding_slot_is_used_for_closure_evidence(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        main = self.main_review(
            finding_review=[{"finding_id": "f1", "check": "verified", "basis": "本地复核"}])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc"}]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main, plan=plan)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("verified finding closure requires evidence_refs",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_close_before_verify_with_bogus_evidence_is_rejected(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:missing"]},
                {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
                 "reason": "先关闭", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:missing"]}]
        self.decide(plan=plan, register_only=True)
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("verification does not exist",
                      json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_minimal_incremental_register_accepts_inherited_reviewer_entries(self):
        finding = {"id": "s1", "severity": "suggestion", "class": "style",
                   "statement": "可更简洁", "location": "pkg/a.py:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        self.decide(main_review=self.main_review(
            finding_review=[{"finding_id": "s1", "slot": "s1", "check": "verified",
                             "basis": "已核实"}]), register_only=True)
        minimal = self.root / "minimal.json"
        minimal.write_text(json.dumps({"task": "t1", "round": 1, "main_findings": [
            {"id": "m2", "severity": "blocking", "statement": "新问题",
             "location": "pkg/b.py:1", "assertion_ref": "a:1", "basis": "本地复现"}]},
            ensure_ascii=False), encoding="utf-8")
        result, task = self.decide(main_review=str(minimal), register_only=True)
        self.assertTrue(result["facts"]["register_only"])
        latest = task["reviews"]["main_reviews"][-1]
        checks = {(item["finding_id"], item["slot"]): item["check"]
                  for item in latest["finding_review"]}
        self.assertEqual(checks.get(("s1", "s1")), "verified")

    def test_redrafting_keeps_the_old_unable_state(self):
        self.stage({**AXES})
        first = {"id": "m1", "severity": "blocking", "statement": "第一条",
                 "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        self.decide(main_review=self.main_review(
            main_findings=[first],
            finding_review=[{"finding_id": "m1", "slot": "main", "check": "unable",
                             "basis": "尚未核实"}]), register_only=True)
        path = self.root / "draft.json"
        review.main_review_draft(self.ctx, {"id": "t1"}, 1, path)
        draft = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in draft["main_findings"]], ["m1"])
        # 按草稿原样提交（只补五轴与报告采信，不给 m1 写 finding_review）
        for axis in review.REVIEW_AXES:
            draft["axes"][axis].update({"conclusion": "pass", "basis": "复核", "sources": ["s1"]})
        for item in draft["report_review"]:
            item.update({"reliance": "primary", "notes": "可用"})
        draft_path = self.root / "filled-main.json"
        draft_path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        _result, task = self.decide(main_review=str(draft_path), register_only=True)
        latest = task["reviews"]["main_reviews"][-1]
        checks = {item["finding_id"]: item["check"] for item in latest["finding_review"]}
        self.assertEqual(checks.get("m1"), "unable")

    def test_appending_a_finding_keeps_the_old_unable_state(self):
        self.stage({**AXES})
        first = {"id": "m1", "severity": "blocking", "statement": "第一条",
                 "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        second = {"id": "m2", "severity": "blocking", "statement": "第二条",
                  "location": "pkg/b.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        self.decide(main_review=self.main_review(
            main_findings=[first],
            finding_review=[{"finding_id": "m1", "slot": "main", "check": "unable",
                             "basis": "尚未核实"}]), register_only=True)
        _result, task = self.decide(main_review=self.main_review(
            main_findings=[second], finding_review=[]), register_only=True)
        latest = task["reviews"]["main_reviews"][-1]
        checks = {item["finding_id"]: item["check"] for item in latest["finding_review"]}
        self.assertEqual(checks.get("m1"), "unable")

    def test_corrected_review_may_omit_previous_main_finding(self):
        self.stage({**AXES})
        first = {"id": "mf1", "severity": "blocking", "statement": "第一条",
                 "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        second = {"id": "mf2", "severity": "blocking", "statement": "第二条",
                  "location": "pkg/b.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        result, _task = self.decide(
            main_review=self.main_review(main_findings=[first]), plan=[
                {"finding_id": "mf1", "round": 1, "slot": "main", "decision": "amended",
                 "reason": "先记录", "recheck_by": "human:xzc"}])
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        # 修正复核只写新 finding：入口按 id 并集保留旧的，不需要 AI 重抄
        fixed, task = self.decide(main_review=self.main_review(main_findings=[second]))
        merged = task["reviews"]["main_reviews"][-1]
        self.assertEqual(sorted(item["id"] for item in merged["main_findings"]), ["mf1", "mf2"])

    def test_register_only_cannot_rewrite_a_judged_pass(self):
        self.stage({**AXES})
        self.decide()
        changed = self.main_review(axes={"contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=changed, register_only=True)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("pass/unavailable", json.dumps(caught.exception.facts,
                                                      ensure_ascii=False))

    def test_register_only_minimal_main_finding_needs_no_full_form(self):
        self.stage({**AXES})
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = []
        records.write_json(self.task_dir / "task.json", task)
        path = self.root / "minimal-main.json"
        path.write_text(json.dumps({
            "task": "t1", "round": 1,
            "main_findings": [{"id": "mf1", "severity": "blocking", "statement": "缺陷",
                               "location": "pkg/a.py:1", "assertion_ref": "a:1",
                               "basis": "本地复现"}],
        }, ensure_ascii=False), encoding="utf-8")
        result, task = self.decide(main_review=str(path), register_only=True)
        self.assertEqual(result["facts"]["registered_main_findings"], 1)
        self.assertTrue(task["reviews"]["main_reviews"][-1].get("discovery"))

    def test_register_only_can_record_main_finding_without_reports(self):
        self.stage({**AXES})
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = []
        records.write_json(self.task_dir / "task.json", task)
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(main_findings=[main_finding], report_review=[],
                                finding_review=[])
        result, task = self.decide(main_review=main, register_only=True)
        self.assertTrue(result["facts"]["register_only"])
        self.assertEqual(result["facts"]["registered_main_findings"], 1)
        self.assertEqual(task["reviews"]["main_reviews"][-1]["main_findings"][0]["id"], "mf1")
        self.assertEqual([item["finding_id"] for item in
                          review.open_findings(self.ctx, task)["blocking"]], ["mf1"])

    def test_register_only_close_rejects_an_invalid_check(self):
        self.stage({**AXES})
        plan = [{"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
                 "reason": "关闭", "recheck_by": "human:xzc"}]
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(plan=plan, register_only=True, check_valid=False)
        self.assertEqual(caught.exception.code, "WF_CHECK_STALE")

    def test_register_only_can_append_a_second_main_finding(self):
        self.stage({**AXES})
        task = records.load_json(self.task_dir / "task.json")
        task["reviews"]["imported"] = []
        records.write_json(self.task_dir / "task.json", task)
        first = {"id": "mf1", "severity": "blocking", "statement": "第一条",
                 "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        second = {"id": "mf2", "severity": "blocking", "statement": "第二条",
                  "location": "pkg/b.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        self.decide(main_review=self.main_review(main_findings=[first], report_review=[],
                                                finding_review=[]),
                    register_only=True)
        result, task = self.decide(
            main_review=self.main_review(main_findings=[first, second], report_review=[],
                                         finding_review=[]),
            register_only=True)
        self.assertEqual(result["facts"]["registered_main_findings"], 2)
        reviews = task["reviews"]["main_reviews"]
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[-1].get("supersedes"), reviews[0].get("file_digest"))
        self.assertEqual([item["finding_id"] for item in
                          review.open_findings(self.ctx, task)["blocking"]],
                         ["mf1", "mf2"])

    def test_main_finding_can_record_a_formal_fail(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实契约缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            axes={"contract": "fail"},
            main_findings=[main_finding],
            finding_refs={"contract": [{"finding_id": "mf1", "slot": "main"}]})
        result, _task = self.decide(main_review=main)
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        self.assertEqual(result["facts"]["result"]["facts"]["open_blocking"][0]["finding_id"],
                         "mf1")

    def test_main_blocking_finding_requires_assertion_ref(self):
        self.stage({**AXES})
        main = self.main_review(
            axes={"contract": "fail"},
            main_findings=[{"id": "mf1", "severity": "blocking", "statement": "缺陷",
                            "basis": "本地复现"}],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "本地复现"}],
            finding_refs={"contract": [{"finding_id": "mf1", "slot": "main"}]})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=main)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("assertion_ref", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_main_blocking_cannot_be_downgraded_by_rewriting_severity(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实契约缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            axes={"contract": "fail"},
            main_findings=[main_finding],
            finding_refs={"contract": [{"finding_id": "mf1", "slot": "main"}]})
        self.decide(main_review=main)
        downgraded = dict(main_finding, severity="suggestion")
        corrected = self.main_review(axes={"contract": "pass"},
                                     main_findings=[downgraded])
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=corrected)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("downgraded", caught.exception.facts)

    def test_closure_evidence_must_resolve_and_pass(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            main_findings=[main_finding],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "已修复"}])
        for ref in ("v:missing", "v:v1", "d:missing"):
            if ref == "v:v1":
                task = records.load_json(self.task_dir / "task.json")
                task["check"]["commands"] = [{"verification_id": "v1", "status": "failed"}]
                records.write_json(self.task_dir / "task.json", task)
            plan = [{"finding_id": "mf1", "round": 1, "slot": "main", "decision": "accepted",
                     "reason": "已修复", "recheck_by": "human:xzc",
                     "evidence_refs": [ref]}]
            with self.assertRaises(review.ReviewError) as caught:
                self.decide(main_review=main, plan=plan)
            self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
            self.assertIn("evidence_ref", json.dumps(caught.exception.facts,
                                                      ensure_ascii=False))

    def test_historical_closure_is_not_revalidated_against_new_check(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            main_findings=[main_finding],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "已修复"}])
        plan = [{"finding_id": "mf1", "round": 1, "slot": "main", "decision": "accepted",
                 "reason": "已修复", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:v1"]}]
        first, _task = self.decide(main_review=main, plan=plan)
        self.assertEqual(first["facts"]["result"]["verdict"], "pass")
        task = records.load_json(self.task_dir / "task.json")
        task["plan"]["verifications"] = [{"id": "v2"}]
        task["check"]["id"] = "c2"
        task["check"]["commands"] = [{"verification_id": "v2", "status": "passed"}]
        task["check_history"] = [{"id": "c1",
                                  "commands": [{"verification_id": "v1", "status": "passed"}]}]
        for entry in task["reviews"]["imported"]:
            report = self.root / entry["report_path"]
            text = report.read_text(encoding="utf-8").replace('"check_id": "c1"',
                                                              '"check_id": "c2"')
            report.write_text(text, encoding="utf-8")
            entry["report_digest"] = records.file_digest(report)
        records.write_json(self.task_dir / "task.json", task)
        second, _task = self.decide(main_review=main)
        self.assertEqual(second["facts"]["result"]["verdict"], "pass")

    def test_main_finding_can_be_closed_in_the_same_decision(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            main_findings=[main_finding],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "已修复"}])
        plan = [{"finding_id": "mf1", "round": 1, "slot": "main", "decision": "accepted",
                 "reason": "已修复", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:v1"]}]
        result, _task = self.decide(main_review=main, plan=plan)
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")

    def test_main_finding_appears_in_draft_and_all_findings(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            axes={"contract": "fail"},
            main_findings=[main_finding],
            finding_refs={"contract": [{"finding_id": "mf1", "slot": "main"}]})
        self.decide(main_review=main)
        task = records.load_json(self.task_dir / "task.json")
        found = review.all_findings(self.ctx, task)
        self.assertEqual([item["id"] for item in found if item["slot"] == "main"], ["mf1"])
        path = self.root / "draft.json"
        review.main_review_draft(self.ctx, {"id": "t1"}, 1, path)
        draft = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in draft["main_findings"]], ["mf1"])
        self.assertNotIn("mf1", [item["finding_id"] for item in draft["finding_review"]])

    def test_draft_only_asks_review_for_blocking_findings(self):
        blocking = {"id": "b1", "severity": "blocking", "class": "defect",
                    "statement": "坏了", "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        suggestion = {"id": "s1", "severity": "suggestion", "class": "style",
                      "statement": "可更简洁", "location": "pkg/a.py:2"}
        self.stage({**AXES}, findings=[blocking, suggestion],
                   per_slot={"s2": {"findings": []}})
        path = self.root / "draft.json"
        review.main_review_draft(self.ctx, {"id": "t1"}, 1, path)
        draft = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([item["finding_id"] for item in draft["finding_review"]], ["b1"])

    def test_main_finding_can_be_closed_with_evidence(self):
        self.stage({**AXES})
        main_finding = {"id": "mf1", "severity": "blocking", "statement": "主会话核实契约缺陷",
                        "location": "pkg/a.py:1", "assertion_ref": "a:1", "basis": "本地复现"}
        main = self.main_review(
            axes={"contract": "fail"},
            main_findings=[main_finding],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "本地复现"}],
            finding_refs={"contract": [{"finding_id": "mf1", "slot": "main"}]})
        first, _task = self.decide(main_review=main)
        self.assertEqual(first["facts"]["result"]["verdict"], "fail")
        corrected = self.main_review(
            axes={"contract": "pass"},
            main_findings=[main_finding],
            finding_review=[{"finding_id": "mf1", "slot": "main", "check": "verified",
                             "basis": "已修复"}])
        plan = [{"finding_id": "mf1", "round": 1, "slot": "main", "decision": "accepted",
                 "reason": "已修复", "recheck_by": "human:xzc",
                 "evidence_refs": ["v:v1"]}]
        second, _task = self.decide(main_review=corrected, plan=plan)
        self.assertEqual(second["facts"]["result"]["verdict"], "pass")

    def test_all_axes_uncovered_can_still_fail_on_a_reviewed_blocking(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({axis: "uncovered" for axis in review.REVIEW_AXES}, findings=[finding])
        result, _task = self.decide(main_review=self.main_review(
            axes={axis: "uncovered" for axis in review.REVIEW_AXES}))
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        self.assertTrue(result["facts"]["result"]["facts"]["coverage"]["all_uncovered"])

    def test_gap_acceptance_is_reported_as_ignored_when_blocking_fails(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        acceptance = {"by": "human:xzc", "at": "2026-11-20T00:00:00Z", "quote": "接受",
                      "source": "human", "round": 1, "axes": ["contract"]}
        result, _task = self.decide(acceptance=acceptance)
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        self.assertIn("gap_acceptance_ignored", result["facts"]["result"]["facts"])

    def test_confirmed_blocking_fails_before_an_unrelated_coverage_gap(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES, "contract": "uncovered"}, findings=[finding])
        result, _task = self.decide(main_review=self.main_review(
            axes={"contract": "uncovered"},
            finding_refs={"regression": [{"finding_id": "f1", "slot": "s1"},
                                         {"finding_id": "f1", "slot": "s2"}]}))
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")
        self.assertEqual(result["facts"]["result"]["facts"]["coverage"]["uncovered"],
                         ["contract"])

    def test_accepted_false_positive_can_pass_in_the_same_round(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        main = self.main_review(finding_review=[
            {"finding_id": "f1", "slot": "s1", "check": "disputed", "basis": "误报"},
            {"finding_id": "f1", "slot": "s2", "check": "disputed", "basis": "误报"}])
        plan = [
            {"finding_id": "f1", "round": 1, "slot": "s1", "decision": "accepted",
             "reason": "经复核认定误报", "recheck_by": "human:xzc"},
            {"finding_id": "f1", "round": 1, "slot": "s2", "decision": "accepted",
             "reason": "经复核认定误报", "recheck_by": "human:xzc"}]
        result, _task = self.decide(main_review=main, plan=plan)
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        self.assertEqual(result["facts"]["result"]["facts"].get("open_blocking", []), [])

    def test_report_review_must_cover_every_slot(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(report_review=[
                {"slot": "s1", "reliance": "primary", "notes": "只看了一份"}]))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("s2", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_finding_review_must_cover_every_blocking_finding(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(finding_review=[]))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("f1", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_deferred_suggestion_does_not_block_the_review(self):
        finding = {"id": "s1", "severity": "suggestion", "class": "style",
                   "statement": "可以更简洁", "location": "pkg/a.py:1"}
        self.stage({**AXES}, findings=[finding], per_slot={"s2": {"findings": []}})
        result, task = self.decide(main_review=self.main_review(finding_review=[]))
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        deferred = task["reviews"]["main_reviews"][-1].get("deferred_suggestions")
        self.assertEqual([item["finding_id"] for item in deferred], ["s1"])

    def test_main_review_cannot_be_replaced_after_a_verdict(self):
        self.stage({**AXES})
        self.decide()
        second = self.main_review(axes={"range": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=second)
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")

    def test_gap_acceptance_cannot_ride_on_register_only_or_unavailable(self):
        for kwargs in ({"register_only": True, "plan_path": "plan.json"},
                       {"unavailable_path": "unavailable.json"}):
            with self.subTest(**kwargs), self.assertRaises(review.ReviewError) as caught:
                review.decide(SimpleNamespace(root=self.root), {"id": "t1"}, 1,
                              gap_acceptance_path="gap.json", **kwargs)
            self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")

    def test_cli_flags_reach_the_decide_entry(self):
        """`--main-review` / `--gap-acceptance` 必须真的接线到 decide。"""
        from wflib import cli

        args = cli.Args(["--task", "t1", "--gap-acceptance", "gap.json",
                         "--main-review", "main-review.json"])
        with mock.patch.object(tasks_mod, "load_task", return_value={"id": "t1", "title": "t"}), \
                mock.patch.object(review, "decide", return_value={"ok": True}) as decided:
            cli._review_command("decide")(SimpleNamespace(root=self.root), args)
        self.assertEqual(decided.call_args.kwargs["gap_acceptance_path"], "gap.json")
        self.assertEqual(decided.call_args.kwargs["main_review_path"], "main-review.json")

    def test_draft_generates_a_fillable_skeleton(self):
        from wflib import cli

        self.stage({**AXES})
        path = str(self.root / "draft.json")
        args = cli.Args(["--task", "t1", "--main-review-draft", path])
        with mock.patch.object(tasks_mod, "load_task", return_value={"id": "t1", "title": "t"}):
            result = cli._review_command("decide")(SimpleNamespace(root=self.root), args)
        self.assertEqual(result["code"], "WF_OK")
        draft = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(set(draft["axes"]), set(review.REVIEW_AXES))
        self.assertEqual([item["slot"] for item in draft["report_review"]], ["s1", "s2"])
        self.assertEqual(draft["finding_review"], [])

    def test_help_lists_the_main_review_flags(self):
        from wflib import cli

        text = json.dumps(cli.COMMAND_HELP["review-decide"], ensure_ascii=False)
        self.assertIn("--main-review", text)
        self.assertIn("--main-review-draft", text)
        self.assertIn("--gap-acceptance", text)

    def test_status_projects_main_review_and_acceptance(self):
        self.stage({**AXES, "contract": "uncovered"})
        task = records.load_json(self.task_dir / "task.json")
        facts = review.status_of_round(SimpleNamespace(root=self.root), task, 1)
        self.assertFalse(facts["main_review_ready"])
        self.assertEqual(facts["coverage"]["uncovered"], ["contract"])
        self.decide(acceptance=GapAcceptanceTest()._decision(),
                    main_review=self.main_review(axes={"contract": "uncovered"}))
        task = records.load_json(self.task_dir / "task.json")
        facts = review.status_of_round(SimpleNamespace(root=self.root), task, 1)
        self.assertTrue(facts["main_review_ready"])
        self.assertEqual(facts["coverage"]["accepted"], ["contract"])


if __name__ == "__main__":
    unittest.main()
