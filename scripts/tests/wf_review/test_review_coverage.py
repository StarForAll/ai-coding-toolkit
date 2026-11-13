"""D1/D2：主会话复核、两源覆盖与缺口接受。

防的失败（dogfood）：
- 覆盖按报告并集算：A 五轴 pass、B 五轴 uncovered 仍算全覆盖——"名义两位、实质一位"；
- 五轴全 uncovered 的报告自报 pass；`scope-exceptions` 自述越界仍 pass；
- 主会话没有自己的逐轴结论，报告成了唯一证据源。

断言：
1. 产生 verdict 必须带主会话复核；缺复核 → `WF_SEMANTIC_DECISION`；
2. 覆盖 = 主会话复核 ∪ 报告；两者都未覆盖才是缺口；
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
                      "anchor": {"check_anchor": ANCHOR, "parts": {}}},
            "entry_snapshot": {"touch_paths": []},
            "plan": {"complexity": "complex", "acceptance": [], "verifications": []},
            "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                      "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                      "temp_paths": []}],
                        "imported": imported}})

    def main_review(self, axes=None, report_review=None, finding_review=None, **overrides):
        conclusions = dict(axes or {axis: "pass" for axis in review.REVIEW_AXES})
        payload = {
            "task": "t1", "round": 1,
            "axes": {axis: {"conclusion": conclusions.get(axis, "pass"),
                            "basis": "主会话复核依据",
                            "sources": ["main"],
                            "finding_refs": []} for axis in review.REVIEW_AXES},
            "report_review": report_review or [
                {"slot": "s1", "reliance": "primary", "notes": "报告覆盖与依据可用"},
                {"slot": "s2", "reliance": "primary", "notes": "报告覆盖与依据可用"}],
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

    def decide(self, acceptance=None, main_review=None):
        captured = {}
        file_path = None
        if acceptance is not None:
            file_path = str(self.root / "gap.json")
            Path(file_path).write_text(json.dumps(acceptance, ensure_ascii=False), encoding="utf-8")
        main_path = main_review if main_review is not None else self.main_review()

        def _start(_ctx, path, task, *_args, **_kwargs):
            captured["task"] = json.loads(json.dumps(task))
            task = dict(task)
            task["action"] = {"id": "a1", "state": "started"}
            records.write_json(os.path.join(path, "task.json"), task)
            return task, task["action"]

        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "standard_drift_gate", return_value=[]), \
                mock.patch.object(tasks_mod, "_start_task_action", _start), \
                mock.patch.object(tasks_mod, "_finish_task_action",
                                  lambda _ctx, _path, task, *_a, **_k: (task, {"ok": True})):
            result = review.decide(self.ctx, {"id": "t1"}, 1, gap_acceptance_path=file_path,
                                   main_review_path=main_path)
        return result, captured.get("task") or {}


class CoverageMergeTest(unittest.TestCase):
    def test_reports_and_main_review_are_merged(self):
        state = review.merged_coverage(
            {"range": "uncovered", "acceptance": "pass"},
            {"s1": {"range": "pass", "acceptance": "uncovered"},
             "s2": {"range": "uncovered", "acceptance": "fail"}})
        self.assertEqual(state["covered"], ["acceptance", "range"])
        self.assertEqual(state["uncovered"], ["contract", "regression", "testability"])
        self.assertEqual(state["sources"]["range"], ["s1"])
        self.assertEqual(state["sources"]["acceptance"], ["main", "s2"])
        self.assertFalse(state["all_uncovered"])

    def test_main_review_alone_can_cover_an_axis(self):
        state = review.merged_coverage({"range": "pass"}, {"s1": {"range": "uncovered"}})
        self.assertIn("range", state["covered"])
        self.assertEqual(state["sources"]["range"], ["main"])

    def test_both_sources_uncovered_is_a_gap(self):
        state = review.merged_coverage({"range": "uncovered", "contract": "pass"},
                                       {"s1": {"range": "uncovered", "contract": "uncovered"}})
        self.assertFalse(state["all_uncovered"])
        self.assertIn("range", state["uncovered"])
        self.assertNotIn("contract", state["uncovered"])

    def test_no_source_covers_anything(self):
        state = review.merged_coverage(
            {axis: "uncovered" for axis in review.REVIEW_AXES},
            {"s1": {axis: "uncovered" for axis in review.REVIEW_AXES}})
        self.assertTrue(state["all_uncovered"])
        self.assertEqual(state["covered"], [])

    def test_projection_tolerates_malformed_axes(self):
        state = review.merged_coverage({}, {"s1": ["range"], "s2": None, "s3": {"range": "pass"}})
        self.assertEqual(state["covered"], ["range"])
        self.assertFalse(state["all_uncovered"])


class GapAcceptanceTest(unittest.TestCase):
    def _decision(self, **overrides):
        decision = {"by": "human:xzc", "at": "2026-11-12T00:00:00Z",
                    "quote": "我接受这些轴这次没看，理由：材料不足", "source": "user-declared",
                    "round": 1, "axes": ["contract"]}
        decision.update(overrides)
        return decision

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


class DecideMainReviewTest(DecideHarness):
    def test_missing_main_review_is_not_a_verdict(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review="")
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")

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

    def test_main_review_fail_without_finding_is_a_human_decision(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(axes={"regression": "fail"}))
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("finding", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_main_review_pass_cannot_override_open_blocking(self):
        finding = {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
                   "location": "pkg/a.py:1", "assertion_ref": "a:1"}
        self.stage({**AXES}, findings=[finding])
        result, _task = self.decide()
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_report_review_must_cover_every_slot(self):
        self.stage({**AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(report_review=[
                {"slot": "s1", "reliance": "primary", "notes": "只看了一份"}]))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("s2", json.dumps(caught.exception.facts, ensure_ascii=False))

    def test_finding_review_must_cover_every_finding(self):
        finding = {"id": "f1", "severity": "suggestion", "class": "defect", "statement": "建议",
                   "location": "pkg/a.py:1"}
        self.stage({**AXES}, findings=[finding])
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(main_review=self.main_review(finding_review=[]))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertIn("f1", json.dumps(caught.exception.facts, ensure_ascii=False))

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
