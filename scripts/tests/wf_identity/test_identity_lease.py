"""P1：K1 会话标识（宿主优先、进程锚冲突判据）与 K2 租约（generation 接管）。

每条用例都回答「它防的失败实际发生过、或可具体推演吗」：
- `/clear` 新会话：dogfood A1 实际发生（`/clear` 命中旧绑定）。
- 冲突钉住：dogfood A4 实际发生（自动模式与写权矛盾，靠人转述解决）。
- 旧租约接管：`five_state/rotate/mark_superseded` 的现场发明即为此，v42 §4 已删，
  这里断言替代物（generation 比较）真的能区分新旧持有者。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, identity_store as store, records, session as S, writer  # noqa: E402


class TestClearProducesNewIdentity(unittest.TestCase):
    """`/clear` 后宿主给出新 session_id ⇒ 新 session_key ⇒ 新绑定（旧绑定不被复用）。"""

    def test_different_host_session_ids_yield_different_keys(self):
        def key(session_id):
            return S.session_key({"provider": "host",
                                  "identity": {"host_id": "dsh", "session_id": session_id}})

        before, after = key("dsh-run-1"), key("dsh-run-2")
        self.assertNotEqual(before, after)
        # 同一把钥匙重复计算必须一致（否则每次请求都会自造新会话）
        self.assertEqual(after, key("dsh-run-2"))

    def test_anchor_only_identity_declares_clear_blind(self):
        """只有进程锚时，`enable` 必须显式声明"看不见同一进程内的新会话"，不得静默复用旧绑定。"""
        import tempfile
        from unittest import mock

        class FakeCtx:
            def __init__(self, root):
                self.root = str(root)

            def explicit_session(self):
                return None

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(cli.session_mod, "candidates", return_value=[]):
            facts = cli._identity_facts(FakeCtx(Path(tmp)), "K")
        self.assertEqual(facts["source"], "anchor")
        self.assertTrue(facts["host_identity_absent"])
        self.assertTrue(facts["new_session_indistinguishable"])

    def test_host_identity_is_primary(self):
        """宿主给出会话标识时 source=host，且不再声称"看不见新会话"。"""
        import tempfile
        from unittest import mock

        class FakeCtx:
            def __init__(self, root):
                self.root = str(root)

            def explicit_session(self):
                return {"provider": "host", "identity": {"host_id": "dsh", "session_id": "s1"}}

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(cli.session_mod, "candidates", return_value=[]):
            facts = cli._identity_facts(FakeCtx(Path(tmp)), "K")
        self.assertEqual(facts["source"], "host")
        self.assertFalse(facts["host_identity_absent"])
        self.assertNotIn("new_session_indistinguishable", facts)


class TestConflictPinning(unittest.TestCase):
    """冲突不猜：锚点指向别的会话时，人用 `enable --identity host` 钉住，记录进 runtime 附件。"""

    def _ctx(self, root):
        class FakeCtx:
            pass

        ctx = FakeCtx()
        ctx.root = str(root)
        return ctx

    def test_pin_is_written_into_attachment(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attachment = store.new_attachment({"issued_id": "u-1"}, "wf", "K", {"kind": "pid"},
                                              {"enabled": True}, records.now_str())
            store.save_attachment(root, "K", attachment)
            cli._pin_identity(self._ctx(root), "K", {"anchor_conflict": ["OLD"]})
            saved = store.load_attachment(root, "K")
            self.assertEqual(saved["identity_pin"]["choice"], "host")
            self.assertEqual(saved["identity_pin"]["conflict_with"], ["OLD"])

    def test_pin_without_attachment_blocks(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cli.CliError) as caught:
                cli._pin_identity(self._ctx(Path(tmp)), "K", {"anchor_conflict": []})
            self.assertEqual(caught.exception.code, "WF_HISTORY_UNRESOLVED")


class TestLeaseTakeover(unittest.TestCase):
    """接管 bump generation：旧持有者下次写入即失效（写权门比较 generation）。"""

    def test_takeover_bumps_generation(self):
        record = writer.initial_record()
        record = writer.acquire(record, kind="session", ident="OLD", scope={"task": "A"})
        old_generation = record["generation"]
        record = writer.release(record)
        record = writer.acquire(record, kind="session", ident="NEW", scope={"task": "A"})
        self.assertGreater(record["generation"], old_generation)
        self.assertEqual(record["generation"], record["holder"]["generation"])
        self.assertEqual(record["holder"]["id"], "NEW")

    def test_old_holder_lease_is_superseded(self):
        record = writer.initial_record()
        record = writer.acquire(record, kind="session", ident="NEW", scope={"task": "A"})
        state = store.lease_state(record, "OLD")
        self.assertEqual(state, store.SUPERSEDED)

    def test_generation_mismatch_is_rejected_by_writer(self):
        record = writer.initial_record()
        record = writer.acquire(record, kind="session", ident="NEW", scope={"task": "A"})
        broken = dict(record, generation=record["generation"] + 1)
        with self.assertRaises(Exception) as caught:
            writer.require_supported(broken)
        self.assertIn("WF_RECORD_INVALID", str(caught.exception))


class TestAuthorizationBoundary(unittest.TestCase):
    """§2 授权边界：批准范围内的工作树改动不再逐次确认。

    防的失败：dogfood 里同一范围的工作被拆成"规划批准/摘要重批/基线提案批准/收工确认"
    多段，人被迫反复点头（4.6 反例）。机制上只允许**维护入口**消费确认令牌；
    普通任务写命令一旦出现令牌/确认等待，就必须显式讨论，而不是悄悄加回来。
    """

    def test_task_commands_do_not_consume_confirmation_tokens(self):
        """令牌/预览阻断只属维护入口；普通任务写命令一旦要求它，就是授权边界被收窄。

        判据取「确认令牌」的两个唯一标记（`preview_token` 与 `WF_PREVIEW_STALE`），
        不按单词猜（`--preview` 是收工预览的显示模式，`check.py` 的 `--token` 是密钥遮罩）。
        """
        import inspect

        from wflib import gates, tasks

        for module in (cli, tasks, gates):
            source = inspect.getsource(module)
            self.assertNotIn("preview_token", source,
                             f"{module.__name__} 要求确认令牌：批准范围内的工作树改动不得逐次确认")
            self.assertNotIn("WF_PREVIEW_STALE", source,
                             f"{module.__name__} 用预览失效阻断普通写：令牌只属维护入口")


if __name__ == "__main__":
    unittest.main()
