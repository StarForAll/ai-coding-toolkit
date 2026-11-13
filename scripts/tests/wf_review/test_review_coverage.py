"""D2：`uncovered` 不推导审查通过（覆盖判定与缺口接受）。

防的失败（dogfood）：两份报告五轴全 `uncovered`，判定仍写 `pass`——"没有发现缺陷"被当成
"完成了必要审查"；同时 `derive_verdict` 的注释引用的 §4.8/§4.9 根本不存在。

断言：
1. 全部轴未覆盖 → 输入不成立（`WF_REVIEW_INVALID`），不产生 verdict；
2. 部分未覆盖且无人接受 → 需人裁决档（`WF_SEMANTIC_DECISION`），facts 列未覆盖轴；
3. 人接受缺口（`by/at/quote/source + round + axes`）→ 可产生判定，接受记录入库、facts 带缺口；
4. 接受文件的轴集合或轮次不符 → 拒绝；
5. 有 blocking finding + 已接受缺口 → 仍 `fail`。
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

    def require_held(self, task=None):
        return {"id": "sess-test"}, {"id": "human:test"}


def report_text(axes, findings=()):
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-12T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
            "scope-exceptions": [], "axes": dict(axes), "findings": list(findings),
            "verdict": "fail" if findings else "pass"}
    return ("<!-- wf-review-agent:v1 status=done -->\n" + MARKER
            + "\n\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```\n")


class DecideHarness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.ctx = Ctx(self.root)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def stage(self, axes, findings=()):
        imported, seen = [], []
        for slot, agent in (("s1", "pi"), ("s2", "zcode")):
            relative = f".wf/tasks/t1/review/round-1/review-{agent}.md"
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report_text(axes, findings), encoding="utf-8")
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

    def decide(self, acceptance=None):
        captured = {}
        file_path = None
        if acceptance is not None:
            file_path = str(self.root / "gap.json")
            Path(file_path).write_text(json.dumps(acceptance, ensure_ascii=False), encoding="utf-8")

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
            result = review.decide(self.ctx, {"id": "t1"}, 1, gap_acceptance_path=file_path)
        return result, captured.get("task") or {}


class CoverageStateTest(unittest.TestCase):
    def test_union_of_reports_is_the_round_coverage(self):
        state = review.coverage_state([{"range": "pass", "acceptance": "uncovered"},
                                       {"range": "uncovered", "acceptance": "fail"}])
        self.assertEqual(state["covered"], ["acceptance", "range"])
        self.assertEqual(state["uncovered"], ["contract", "regression", "testability"])
        self.assertFalse(state["all_uncovered"])

    def test_all_uncovered_is_input_not_established(self):
        state = review.coverage_state([{axis: "uncovered" for axis in review.REVIEW_AXES}])
        self.assertTrue(state["all_uncovered"])
        self.assertEqual(state["covered"], [])


    def test_projection_tolerates_malformed_axes(self):
        state = review.coverage_state([["range"], "x", None, {"range": "pass"}])
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


class DecideCoverageTest(DecideHarness):
    def test_all_uncovered_produces_no_verdict(self):
        self.stage({axis: "uncovered" for axis in review.REVIEW_AXES})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")
        self.assertEqual(caught.exception.facts["covered"], [])

    def test_partial_coverage_needs_a_human_decision(self):
        self.stage({**AXES, "contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide()
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertEqual(caught.exception.facts["uncovered"], ["contract"])

    def test_accepted_gap_allows_a_verdict_and_is_recorded(self):
        self.stage({**AXES, "contract": "uncovered"})
        result, task = self.decide(GapAcceptanceTest()._decision())
        self.assertEqual(result["code"], "WF_OK")
        self.assertEqual(result["facts"]["result"]["verdict"], "pass")
        coverage = result["facts"]["result"]["facts"]["coverage"]
        self.assertEqual(coverage["uncovered"], ["contract"])
        recorded = task["reviews"]["coverage_acceptances"]
        self.assertEqual(recorded[-1]["axes"], ["contract"])

    def test_mismatched_acceptance_is_rejected(self):
        self.stage({**AXES, "contract": "uncovered"})
        with self.assertRaises(review.ReviewError) as caught:
            self.decide(GapAcceptanceTest()._decision(axes=["range"]))
        self.assertEqual(caught.exception.code, "WF_REVIEW_INVALID")

    def test_blocking_findings_still_fail(self):
        self.stage({**AXES, "contract": "uncovered"}, findings=[
            {"id": "f1", "severity": "blocking", "class": "defect", "statement": "坏了",
             "location": "pkg/a.py:1", "assertion_ref": "a:1"}])
        result, _task = self.decide(GapAcceptanceTest()._decision())
        self.assertEqual(result["facts"]["result"]["verdict"], "fail")

    def test_gap_acceptance_cannot_ride_on_register_only_or_unavailable(self):
        for kwargs in ({"register_only": True, "plan_path": "plan.json"},
                       {"unavailable_path": "unavailable.json"}):
            with self.subTest(**kwargs), self.assertRaises(review.ReviewError) as caught:
                review.decide(SimpleNamespace(root=self.root), {"id": "t1"}, 1,
                              gap_acceptance_path="gap.json", **kwargs)
            self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")

    def test_cli_flag_reaches_the_decide_entry(self):
        """`--gap-acceptance` 必须真的接线到 decide（帮助里有字、入口没接线是最常见的漏项）。"""
        from wflib import cli

        args = cli.Args(["--task", "t1", "--gap-acceptance", "gap.json"])
        with mock.patch.object(tasks_mod, "load_task", return_value={"id": "t1", "title": "t"}), \
                mock.patch.object(review, "decide", return_value={"ok": True}) as decided:
            cli._review_command("decide")(SimpleNamespace(root=self.root), args)
        self.assertEqual(decided.call_args.kwargs["gap_acceptance_path"], "gap.json")

    def test_help_lists_the_gap_acceptance_flag(self):
        import json

        from wflib import cli

        text = json.dumps(cli.COMMAND_HELP["review-decide"], ensure_ascii=False)
        self.assertIn("--gap-acceptance", text)
        self.assertIn("round", text)
        self.assertIn("axes", text)

    def test_status_projects_coverage_and_acceptance(self):
        self.stage({**AXES, "contract": "uncovered"})
        task = records.load_json(self.task_dir / "task.json")
        facts = review.status_of_round(SimpleNamespace(root=self.root), task, 1)
        self.assertEqual(facts["coverage"]["uncovered"], ["contract"])
        self.assertEqual(facts["coverage"]["accepted"], [])
        self.decide(GapAcceptanceTest()._decision())
        task = records.load_json(self.task_dir / "task.json")
        facts = review.status_of_round(SimpleNamespace(root=self.root), task, 1)
        self.assertEqual(facts["coverage"]["accepted"], ["contract"])


if __name__ == "__main__":
    unittest.main()
