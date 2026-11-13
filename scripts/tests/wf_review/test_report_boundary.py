"""D2：报告读取/排除边界、缺口通道与 reviewer 入口的授权范围。

防的失败（dogfood / 分析报告）：
- `read-scope: [".env"]` 与 `excluded-scope` 声明排除凭据可同时通过；
- `scope-exceptions` 自述越界只进 gaps、不阻断；`material-gaps` 被记成审查 fail；
- 五轴全 uncovered 的报告自报 pass；
- `review-context` 不把本次 `readable_scope`/`exclusions` 交给 reviewer。
"""

import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, review  # noqa: E402

ANCHOR = "sha256:" + "d" * 64
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]
AXES = {name: "pass" for name in review.REVIEW_AXES}


def payload(**overrides):
    body = {"protocol": "wf-review-v1", "task-id": "t1", "round": 1,
            "review-time": "2026-11-13T00:00:00.000000Z", "review-focus": "x",
            "check-anchor": {"check_id": "c1", "check_anchor": ANCHOR},
            "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
            "axes": dict(AXES), "findings": [], "verdict": "pass"}
    body.update(overrides)
    return body


class ReadScopeBoundaryTest(unittest.TestCase):
    def test_read_scope_must_not_intersect_excluded_scope(self):
        problems = review.read_scope_problems(payload(**{"read-scope": [".env"]}))
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["reason"], "read-scope intersects excluded-scope")

    def test_broad_read_scope_that_includes_exclusions_is_a_contradiction(self):
        problems = review.read_scope_problems(payload(**{"read-scope": ["**"],
                                                          "excluded-scope": [".env"]}))
        self.assertEqual(len(problems), 1)

    def test_legitimate_supplementary_read_passes(self):
        problems = review.read_scope_problems(payload(**{"read-scope": ["pkg/dependency.py",
                                                                        "spec/rules.md"]}))
        self.assertEqual(problems, [])

    def test_same_check_name_in_lint_and_input_face(self):
        text = ("<!-- wf-review-agent:v1 status=done -->\n" + review.REPORT_MARKER
                + "\n\n```json\n" + json.dumps(payload(**{"read-scope": [".env"]}),
                                               ensure_ascii=False) + "\n```\n")
        lint = review.lint_report(None, None, text)
        self.assertFalse(lint["ok"])
        self.assertIn("read-scope-excluded",
                      {item["check"] for item in lint["checks"] if not item["ok"]})


class VerdictShapeTest(unittest.TestCase):
    def test_all_uncovered_report_is_unavailable_not_pass(self):
        conclusion, problems, gaps, blocking = review.derive_verdict(
            {axis: "uncovered" for axis in review.REVIEW_AXES}, [])
        self.assertEqual(conclusion, "unavailable")
        self.assertEqual(problems, [])
        self.assertEqual(len(gaps), len(review.REVIEW_AXES))
        self.assertEqual(blocking, [])

    def test_all_uncovered_with_blocking_still_fails(self):
        conclusion, _problems, _gaps, _blocking = review.derive_verdict(
            {axis: "uncovered" for axis in review.REVIEW_AXES},
            [{"id": "f1", "severity": "blocking"}])
        self.assertEqual(conclusion, "fail")

    def test_partial_uncovered_stays_pass_for_covered_axes(self):
        conclusion, problems, gaps, _blocking = review.derive_verdict(
            {**AXES, "contract": "uncovered"}, [])
        self.assertEqual(conclusion, "pass")
        self.assertEqual(problems, [])
        self.assertEqual([item["axis"] for item in gaps], ["contract"])


class LegacyFieldsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_dir = self.root / ".wf" / "tasks" / "t1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _task(self, findings=()):
        return {"id": "t1", "title": "t", "status": "in_progress", "phase": "check",
                "revision": 1, "check": {"id": "c1", "result": "pass",
                                         "anchor": {"check_anchor": ANCHOR}},
                "plan": {"complexity": "complex", "acceptance": [], "verifications": []},
                "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                          "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                          "temp_paths": []}],
                            "imported": [
                                {"round": 1, "slot": "s1", "agent": "pi",
                                 "report_path": ".wf/tasks/t1/review/round-1/review-pi.md",
                                 "report_digest": "sha256:" + "a" * 64,
                                 "anchor": {"check_anchor": ANCHOR}},
                                {"round": 1, "slot": "s2", "agent": "zcode",
                                 "report_path": ".wf/tasks/t1/review/round-1/review-zcode.md",
                                 "report_digest": "sha256:" + "b" * 64,
                                 "anchor": {"check_anchor": ANCHOR}}]}}

    def _stage_reports(self, body_overrides=None):
        body = payload(**{"scope-exceptions": ["读取了排除面 .env，边界尚未处置"],
                          "material-gaps": ["验收用例缺失"]})
        body.update(body_overrides or {})
        text = ("<!-- wf-review-agent:v1 status=done -->\n" + review.REPORT_MARKER
                + "\n\n```json\n" + json.dumps(body, ensure_ascii=False) + "\n```\n")
        for name in ("review-pi.md", "review-zcode.md"):
            path = self.task_dir / "review" / "round-1" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def test_scope_exceptions_and_material_gaps_are_not_failures(self):
        self._stage_reports()
        task = self._task()
        for entry in task["reviews"]["imported"]:
            entry["report_digest"] = records.file_digest(self.root / entry["report_path"])
        facts = review.review_report_problems(SimpleNamespace(root=self.root), task, round_no=1,
                                              launch=task["reviews"]["launches"][0],
                                              imported=task["reviews"]["imported"], anchor=ANCHOR)
        self.assertEqual(facts["problems"], [])
        self.assertEqual(facts["failures"], [])
        self.assertEqual(facts["gaps_out"], [])


class ContextScopeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_id = "t1-" + uuid.uuid4().hex[:8]
        self.task_dir = self.root / ".wf" / "tasks" / self.task_id
        self.task_dir.mkdir(parents=True)
        self.task = {"id": self.task_id, "title": "t", "status": "in_progress", "phase": "check",
                     "revision": 1, "check": {"id": "c1", "result": "pass",
                                              "anchor": {"check_anchor": ANCHOR}},
                     "reviews": {"launches": [{"round": 1, "implementation_cli": "dsh",
                                               "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                               "submitted_scope": {"diff": {"paths": ["pkg/a.py"]}},
                                               "readable_scope": {"business_code": ["**"],
                                                                  "focus_paths": ["pkg/a.py"]},
                                               "exclusions": list(COVERED),
                                               "temp_paths": []}],
                                 "imported": []}}
        records.write_json(self.task_dir / "task.json", self.task)

    def tearDown(self):
        self._tmp.cleanup()

    def test_context_returns_the_launch_scope(self):
        with mock.patch.object(review, "_current_anchor", return_value=(ANCHOR, {})), \
                mock.patch.object(review, "write_materials", return_value={"problems": []}):
            result = review.context(SimpleNamespace(root=self.root), self.task, 1, as_value="pi")
        facts = result["facts"]
        self.assertEqual(facts["submitted_scope"]["diff"]["paths"], ["pkg/a.py"])
        self.assertEqual(facts["readable_scope"]["focus_paths"], ["pkg/a.py"])
        self.assertIn(".env", facts["exclusions"])


if __name__ == "__main__":
    unittest.main()
