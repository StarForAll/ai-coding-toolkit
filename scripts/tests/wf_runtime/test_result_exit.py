"""结果结构的 `exit` 只在失败/待决时给出口（2026-11-25 第四轮复审 F3）。

机制稿 §11.1：`next` 是具名下一操作，`exit` 是失败/待决时可走的出口。旧实现给每个 `WF_OK`
都塞了码表通用文案「继续当前绑定步骤；不推断其他对象已完成」，与只读命令（version/help/status）
自己的 `next` 直接矛盾；文本渲染器本来也只在非 pass 时显示它。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, codes  # noqa: E402


class ResultExitTest(unittest.TestCase):
    def test_pass_result_has_no_exit(self):
        payload = codes.result("WF_OK", next_="wf-center：下一步由 next 给")
        self.assertEqual(payload["tier"], "pass")
        self.assertIsNone(payload["exit"])

    def test_blocked_result_keeps_code_exit(self):
        payload = codes.result("WF_APPROVAL_MISSING")
        self.assertEqual(payload["tier"], "blocked")
        self.assertTrue(payload["exit"])
        self.assertEqual(payload["exit"], codes.exit_of("WF_APPROVAL_MISSING"))

    def test_needs_decision_result_keeps_code_exit(self):
        payload = codes.result("WF_SEMANTIC_DECISION")
        self.assertEqual(payload["tier"], "needs_decision")
        self.assertTrue(payload["exit"])

    def test_text_renderer_shows_exit_only_when_blocked(self):
        passed = cli.render(codes.result("WF_OK", next_="按 next 继续"))
        self.assertNotIn("出口:", passed)
        blocked = cli.render(codes.result("WF_APPROVAL_MISSING", next_="重新批准"))
        self.assertIn("出口:", blocked)


if __name__ == "__main__":
    unittest.main()
