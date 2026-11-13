"""P3/S3：`lint report` 一次列全（C2/C3）与 `d:` 只认 active 条目。

防的失败：dogfood 里 4 次报告格式返工、8 轮审查——每次只报一个错，改一个再撞下一个。
这里断言"一次把能查的都列出来"，并且 lint 明确声明自己不是门禁（不冒充 pass）。
"""

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402

MARKER = review.REPORT_MARKER
COVERED = ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"]


def render(payload, status="done"):
    head = f"<!-- wf-review-agent:v1 status={status} -->\n" if status is not None else ""
    return f"{head}{MARKER}\n\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```\n"


AXES = {"range": "pass", "acceptance": "pass", "contract": "pass",
        "regression": "pass", "testability": "pass"}


def report(**overrides):
    payload = {"protocol": review.PROTOCOL, "task-id": "t1", "round": 1,
               "review-time": "2026-11-09T00:00:00Z",
               "review-focus": "范围、验收、契约、回归、可测性",
               "check-anchor": {"check_id": "c1", "check_anchor": "sha256:x"},
               "read-scope": ["pkg/**"], "excluded-scope": list(COVERED),
               "scope-exceptions": [], "axes": dict(AXES),
               "findings": [], "verdict": "pass"}
    payload.update(overrides)
    return payload


class LintReportTest(unittest.TestCase):
    def test_clean_report_passes_and_declares_not_a_gate(self):
        facts = review.lint_report(None, None, render(report()))
        self.assertTrue(facts["ok"], facts["problems"])
        self.assertEqual(facts["verdict"], "pass")
        self.assertTrue(facts["not_checked"], "lint 必须声明哪些事它没核，不能冒充门禁")

    def test_all_problems_are_listed_in_one_pass(self):
        payload = report(verdict="fail", findings=[
            {"id": "f1", "severity": "suggestion"}])
        payload["axes"]["contract"] = "fail"          # 轴 fail 却没有 blocking 依据
        payload.pop("review-focus")                  # 必填字段缺失
        facts = review.lint_report(None, None, render(payload))
        self.assertFalse(facts["ok"])
        reasons = json.dumps(facts["problems"], ensure_ascii=False)
        self.assertIn("review-focus", reasons)        # 字段缺失
        self.assertIn("一义三用", reasons)             # 轴 fail 无 blocking
        checks = {item["check"] for item in facts["checks"]}
        self.assertTrue({"protocol", "required-fields", "axes-and-verdict"} <= checks)

    def test_entity_checks_need_task_and_say_so(self):
        """不给 --task 时引用与规则状态核不了：必须显式标明跳过，不能静默当通过。"""
        facts = review.lint_report(None, None, render(report()))
        skipped = [item for item in facts["checks"] if item.get("skipped")]
        self.assertEqual(len(skipped), 1)
        self.assertIn("--task", skipped[0]["skipped"])

    def test_missing_protocol_marker_is_reported_as_single_problem(self):
        facts = review.lint_report(None, None, "没有标记的正文")
        self.assertFalse(facts["ok"])
        self.assertEqual(len(facts["problems"]), 1)
        self.assertIn("marker", facts["problems"][0]["reason"])

    def test_uncovered_axis_is_a_gap_not_a_failure(self):
        payload = report()
        payload["axes"]["acceptance"] = "uncovered"
        facts = review.lint_report(None, None, render(payload))
        self.assertTrue(facts["ok"], facts["problems"])
        self.assertEqual([item["axis"] for item in facts["gaps"]], ["acceptance"])

    def test_input_surface_matches_the_importer(self):
        """lint 与导入/判定同一套输入校验：空读范围/窄排除面/状态行位置都由共享实现报出。"""
        cases = {
            "read-scope": report(**{"read-scope": []}),
            "excluded-scope": report(**{"excluded-scope": ["node_modules/**"]}),
        }
        for check, payload in cases.items():
            facts = review.lint_report(None, None, render(payload))
            self.assertFalse(facts["ok"], check)
            names = {item["check"] for item in facts["checks"] if not item["ok"]}
            self.assertIn(check, names)

    def test_status_head_is_checked_where_the_importer_looks(self):
        missing = review.lint_report(None, None, render(report(), status=None))
        self.assertFalse(missing["ok"])
        self.assertIn("status-head", {item["check"] for item in missing["checks"] if not item["ok"]})
        tail = (f"{review.REPORT_MARKER}\n\n```json\n{json.dumps(report(), ensure_ascii=False)}\n```\n"
                "<!-- wf-review-agent:v1 status=done -->\n")
        facts = review.lint_report(None, None, tail)
        self.assertFalse(facts["ok"], "状态行在末尾时导入扫不到，lint 不能放行")
        not_done = review.lint_report(None, None, render(report(), status="in-progress"))
        self.assertFalse(not_done["ok"])
        reasons = json.dumps(not_done["problems"], ensure_ascii=False)
        self.assertIn("not done", reasons)


if __name__ == "__main__":
    unittest.main()
