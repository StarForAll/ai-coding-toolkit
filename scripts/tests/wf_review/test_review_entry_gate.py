"""审查入口的终态与必需性必须由事实决定（2026-11-25 第四轮复审 F2）。

两处真实错话：
- `review-status` 在「尚未发起任何轮」时无条件劝 `review-launch`：已归档任务与轻量任务都被劝去做
  一个不存在/非必需的轮次；
- 已归档任务跑 `review-launch` 得到「规划批准已失效」（归档把 PRD 移走造成的副作用），
  处置方向（回 Plan 重批）对终态对象是错的。

断言：`round_entry_gate` 的三态投影、`review-status` 按状态/复杂度的 next、`review-launch` 的终态首报。
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, records, review  # noqa: E402

ANCHOR = "sha256:" + "a" * 64


class RoundEntryGateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.task_dir = self.root / ".wf/tasks/t1"
        self.task_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write_task(self, status, complexity):
        records.write_json(self.task_dir / "task.json", {
            "id": "t1", "title": "t", "status": status, "phase": "check",
            "check": {"id": "c1", "result": "pass", "anchor": {"check_anchor": ANCHOR}},
            "plan": {"complexity": complexity},
            "reviews": {"launches": [], "imported": [], "dispositions": []}})
        return records.load_json(self.task_dir / "task.json")

    def status_next(self, task):
        ctx = mock.Mock()
        ctx.root = str(self.root)
        args = mock.Mock()
        args.value.side_effect = lambda name: {"--task": "t1"}.get(name)
        return cli.cmd_review_status(ctx, args)

    # -- 事实面 -----------------------------------------------------------
    def test_gate_facts(self):
        gate = review.round_entry_gate(self.write_task("in_progress", "complex"))
        self.assertEqual(gate["task_status"], "in_progress")
        self.assertFalse(gate["terminal"])
        self.assertTrue(gate["external_review_required"])
        self.assertFalse(review.round_entry_gate(self.write_task("in_progress", "light"))
                         ["external_review_required"])
        archived = review.round_entry_gate(self.write_task("archived", "complex"))
        self.assertTrue(archived["terminal"])
        self.assertFalse(archived["external_review_required"])

    # -- status 投影 ------------------------------------------------------
    def test_archived_task_is_not_told_to_launch(self):
        result = self.status_next(self.write_task("archived", "complex"))
        self.assertEqual(result["code"], "WF_OK")
        self.assertIn("已归档", result["next"])
        self.assertNotIn("先 review-launch", result["next"])
        self.assertTrue(result["facts"]["entry_gate"]["terminal"])

    def test_archived_decided_round_is_not_told_to_open_a_new_round(self):
        task = self.write_task("archived", "complex")
        task["reviews"] = {"launches": [{"round": 1, "implementation_cli": "dsh",
                                         "slots": [{"slot": "s1"}, {"slot": "s2"}],
                                         "anchor": {"check_anchor": ANCHOR}}],
                           "imported": [], "dispositions": [],
                           "result": {"round": 1, "verdict": "pass"}}
        records.write_json(self.task_dir / "task.json", task)
        result = self.status_next(task)
        self.assertIn("已归档", result["next"])
        self.assertNotIn("开新一轮", result["next"])

    def test_light_task_is_not_told_external_review_is_required(self):
        result = self.status_next(self.write_task("in_progress", "light"))
        self.assertIn("轻量任务没有必需的外部审查轮", result["next"])
        # 外部审查对轻量任务是可选工具，不写成禁止、也不写成必需
        self.assertIn("可直接 review-launch", result["next"])
        # 可选不等于无后果：自愿轮的未关闭 blocking 同样进归档门禁
        self.assertIn("未关闭 blocking", result["next"])

    def test_complex_task_still_gets_launch(self):
        result = self.status_next(self.write_task("in_progress", "complex"))
        self.assertIn("先 review-launch", result["next"])

    # -- launch 首报 ------------------------------------------------------
    def test_launch_on_archived_task_reports_terminal_state(self):
        task = self.write_task("archived", "complex")
        ctx = mock.Mock()
        ctx.root = str(self.root)
        with self.assertRaises(review.ReviewError) as caught:
            review.launch(ctx, task)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertEqual(caught.exception.facts["status"], "archived")
        self.assertIn("archived", caught.exception.facts["reason"])
        # 不再用"规划批准已失效"掩盖真实原因
        self.assertNotIn("WF_APPROVAL_MISSING", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
