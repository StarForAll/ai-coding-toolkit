"""交接发现面与 TDD 谓词的唯一实现（2026-11-28 终审 F1/F3）。

缺陷形态：
1. recovering 的 `WF_WRITER_BUSY` 各入口各写一套，接收方看到的只是 "holder: null"，
   不点名唯一可执行入口 `writer-handover accept`；
2. `checkpoint` 只写不读（设计稿 §4.4 的"报告检查点"没有消费者）；
3. TDD 适用性谓词在 Check/门禁/draft 三处重复（`tdd_scope` 为唯一实现）。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check, cli  # noqa: E402


class WriterBusyProjectionTest(unittest.TestCase):
    def test_recovering_names_accept_and_projects_handover(self):
        record = {
            "state": "recovering",
            "holder": None,
            "checkpoint": None,
            "handover": {
                "from": "sess-a",
                "receiver_session_key": "sess-b",
                "object_or_preparation": {"kind": "task", "id": "t-1"},
                "invalidated_generation": 4,
                "decision": {"choice": "handover", "reason": "审计面"},
            },
        }
        error = cli.writer_busy_error(record, caller="sess-b")
        self.assertEqual(error.code, "WF_WRITER_BUSY")
        self.assertIn("writer-handover accept", error.next)
        self.assertIn("checkpoint", error.facts)
        self.assertEqual(error.facts["handover"]["receiver_session_key"], "sess-b")
        self.assertEqual(error.facts["handover"]["object"], {"kind": "task", "id": "t-1"})
        # 决定内容留在 writer.handover.decision（审计面），不扩大投影
        self.assertNotIn("decision", error.facts["handover"])
        self.assertEqual(error.facts["you_are"], "receiver")
        self.assertEqual(cli.writer_busy_error(record, caller="sess-a").facts["you_are"], "initiator")
        self.assertEqual(cli.writer_busy_error(record, caller="sess-x").facts["you_are"], "other")

    def test_held_points_to_repair_not_accept(self):
        record = {"state": "held",
                  "holder": {"kind": "session", "id": "other", "generation": 3},
                  "checkpoint": {"step": "acquired"}}
        error = cli.writer_busy_error(record)
        self.assertTrue(any("repair" in item for item in error.facts["exits"]))
        self.assertNotIn("writer-handover accept", error.next)
        self.assertEqual(error.facts["checkpoint"], {"step": "acquired"})

    def test_maintenance_holder_has_own_exit(self):
        record = {"state": "held",
                  "holder": {"kind": "maintenance", "id": "op-1", "generation": 3}}
        error = cli.writer_busy_error(record)
        self.assertIn("维护", error.next)

    def test_writer_handover_accept_needs_activation(self):
        self.assertTrue(cli._needs_activation("writer-handover", ["writer-handover", "accept"]))
        self.assertTrue(cli._needs_activation("writer-handover", ["writer-handover", "begin"]))


class HandoverScopeTest(unittest.TestCase):
    def test_unbound_session_only_hands_over_preparation(self):
        preparation = {"kind": "preparation", "id": "wf-a"}
        self.assertIsNone(cli.handover_begin_scope_problem(None, preparation))
        problem = cli.handover_begin_scope_problem(None, {"kind": "task", "id": "t-1"})
        self.assertEqual(problem["reason"], "未绑定会话只能交接准备范围（preparation）")
        self.assertIn("object", problem)
        # 已绑定会话不受该限制（任务/实例对象正常交接）
        self.assertIsNone(cli.handover_begin_scope_problem({"id": "k"}, {"kind": "task", "id": "t-1"}))

    def test_accept_creates_binding_only_for_task_or_run(self):
        self.assertTrue(cli.handover_accept_creates_binding({"kind": "task", "id": "t"}))
        self.assertTrue(cli.handover_accept_creates_binding({"kind": "run", "id": "r"}))
        self.assertFalse(cli.handover_accept_creates_binding({"kind": "preparation", "id": "wf"}))

class TddScopeTest(unittest.TestCase):
    def test_single_predicate_variants(self):
        self.assertEqual(check.tdd_scope({"tdd": True}), (True, "code"))
        self.assertEqual(check.tdd_scope({"tdd": True, "tdd_applicability": "docs"}), (False, "docs"))
        self.assertEqual(check.tdd_scope({"tdd": False}), (False, "code"))
        # 已批准规划优先于存量 check；两边冲突时按 plan（check 只作缺键回退）
        self.assertEqual(check.tdd_scope({"tdd": True, "tdd_applicability": "code"},
                                         {"tdd_applicability": "docs"}), (True, "code"))
        self.assertEqual(check.tdd_scope({"tdd": True, "tdd_applicability": "docs"},
                                         {"tdd_applicability": "code"}), (False, "docs"))
        self.assertEqual(check.tdd_scope({"tdd": True}, {"tdd_applicability": "investigation"}),
                         (False, "investigation"))


if __name__ == "__main__":
    unittest.main()


class AcceptBindingSyncTest(unittest.TestCase):
    """接收方 accept 后的身份载体（实测：只写绑定文件会让接收方无法写）。

    只写绑定文件时，自动身份模式的接收方附件仍缺 instance_id：下一条写命令被
    `_require_instance_match` 以 WF_IDENTITY_UNRESOLVED 拒绝，接收方持权却无法写/释放。
    """

    def test_accept_syncs_attachment_and_runtime(self):
        import tempfile
        from types import SimpleNamespace
        from unittest import mock

        from wflib import session as session_mod

        binding = {"instance_id": "inst-1", "object": {"kind": "task", "id": "t-1"}}
        with tempfile.TemporaryDirectory() as root:
            ctx = SimpleNamespace(root=root)
            with mock.patch.object(session_mod, "save_binding") as save_binding, \
                    mock.patch.object(cli, "_sync_attachment_instance") as sync, \
                    mock.patch.object(session_mod, "update_runtime") as runtime:
                cli._accept_binding_state(ctx, "key-1", {"kind": "task", "id": "t-1"}, binding)
        save_binding.assert_called_once()
        sync.assert_called_once_with(ctx, "key-1", "inst-1")
        kwargs = runtime.call_args.kwargs
        self.assertEqual(kwargs["instance_id"], "inst-1")
        self.assertEqual(kwargs["object"], {"kind": "task", "id": "t-1"})
        self.assertEqual(kwargs["current_task"], "t-1")
        self.assertIn("binding_digest", kwargs)
