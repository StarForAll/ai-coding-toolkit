"""重复调试的裁定按**覆盖**语义：一条裁定覆盖它之前的所有倍数。

真实摩擦（2026-11-24 复核 a-P2）：阈值为 3、同一个已查实的根因累计失败 9 次，会被要求
为第 1/2/3 个倍数各签一条裁定——计数是机制的事，而"这几次是不是同一根因"是一次判断。
覆盖不改变计数与留痕：裁定仍按 `debug-ruling-<验证项>-<倍数>` 精确落账，只是待决项一次
给出它覆盖的区间，判过的倍数不再追问。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import gates  # noqa: E402


def task_with(failures, rulings=()):
    return {"id": "t1",
            "check_history": [{"id": f"c{index}", "result": "fail",
                               "commands": [{"verification_id": "v1", "status": "failed"}]}
                              for index in range(failures)],
            "execution": {"debug_declarations": [],
                          "human_decisions": [
                              {"subject": f"debug-ruling-v1-{multiple}", "choice": choice,
                               "reason": "用例", "evidence_refs": ["check:c0"]}
                              for multiple, choice in rulings]}}


class DebugRulingCoverageTest(unittest.TestCase):
    def test_one_pending_covers_every_crossed_multiple(self):
        info = gates.debug_pending(task_with(9), 3)
        self.assertEqual(len(info["pending"]), 1)
        item = info["pending"][0]
        self.assertEqual(item["multiple"], 3)
        self.assertEqual(item["covers"], [1, 2, 3])

    def test_ruling_the_latest_multiple_clears_lower_ones(self):
        info = gates.debug_pending(task_with(9, [(3, "同一问题")]), 3)
        self.assertEqual(info["pending"], [])
        # 裁定仍按 subject 精确记录，没有被覆盖语义抹掉
        self.assertEqual(info["rulings"], {("v1", 3): "同一问题"})

    def test_next_crossing_asks_again(self):
        info = gates.debug_pending(task_with(12, [(3, "同一问题")]), 3)
        self.assertEqual([item["multiple"] for item in info["pending"]], [4])
        self.assertEqual(info["pending"][0]["covers"], [4])

    def test_below_threshold_asks_nothing(self):
        self.assertEqual(gates.debug_pending(task_with(2), 3)["pending"], [])


if __name__ == "__main__":
    unittest.main()


class FutureMultipleTest(unittest.TestCase):
    """未到达的倍数不能被提前裁（裁定按最大倍数覆盖之前全部倍数）。"""

    def test_future_multiple_is_rejected_at_write_time(self):
        import json
        import tempfile
        from unittest import mock
        from wflib import cli, decisions as decisions_mod, lock as lock_mod, records, tasks

        task = task_with(3)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = root / ".wf/tasks/t1"
            task_dir.mkdir(parents=True)
            task["status"] = "in_progress"
            task["phase"] = "check"
            records.write_json(task_dir / "task.json", task)
            decision = root / "d.json"
            decision.write_text(json.dumps([{
                "source": "human:test", "at": "2026-11-24T00:00:00Z", "subject": "debug-ruling-v1-99",
                "object_digest": "sha256:" + "0" * 64, "choice": "同一问题", "reason": "提前裁"}]), encoding="utf-8")
            ctx = mock.Mock()
            ctx.root = str(root)
            ctx.debug_threshold.return_value = 3
            ctx.inputs.return_value = {}
            args = mock.Mock()
            args.value.side_effect = lambda name: {"--task": "t1", "--decision": str(decision)}.get(name)
            args.flag.return_value = False
            lock_ctx = mock.MagicMock()
            lock_ctx.__enter__.return_value = None
            lock_ctx.__exit__.return_value = False
            with mock.patch.object(tasks, "_require_binding"), \
                    mock.patch.object(lock_mod, "acquire", return_value=lock_ctx):
                ctx.require_held.return_value = (records.load_json(task_dir / "task.json"),
                                                 {"id": "human:test"})
                with self.assertRaises(tasks.TaskError) as caught:
                    tasks.cmd_task_check(ctx, args)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertEqual(caught.exception.facts["reached"], 1)
