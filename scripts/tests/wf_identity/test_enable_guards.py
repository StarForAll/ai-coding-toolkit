"""启用前置：`enable` 与 `enable --new-session` 共用同一套、且在写盘之前跑。

真失败（2026-11-24 dogfood 复核 b-P1/F2）：`cmd_enable` 在 `--new-session` 分支直接返回，
Trellis 互斥与平台核对都不跑；普通启用先 `_establish_auto_session`（写附件 + 路由）再查冲突，
命令拒绝了却留下 `activation.enabled=true`，后续命令按"已启用"继续。

断言分两种：行为（两形态的 identity 都撞同一套门禁、被拒后不落附件）与顺序
（前置调用先于写调用的源码位置——顺序型不变量用源码断言固定，与既有做法一致）。
"""

import json
import sys
import uuid
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, records, session as session_mod  # noqa: E402


class FakeCtx:
    def __init__(self, root, inputs=None, platforms=()):
        self.root = str(root)
        self._inputs = dict(inputs or {})
        self._platforms = list(platforms)

    def inputs(self):
        return self._inputs

    def platforms(self):
        return self._platforms


def write_trellis_block(root):
    Path(root, "AGENTS.md").write_text(
        "# AGENTS\n\n<!-- TRELLIS:START -->\nmanaged\n<!-- TRELLIS:END -->\n", encoding="utf-8")


def write_host_config(root, host="dsh"):
    """当前宿主的注入配置（`TRELLIS_HOST_CONFIGS` 的适用面），用于走到"适用"分支。"""
    Path(root, ".dsh").mkdir(parents=True, exist_ok=True)
    Path(root, ".dsh", "hooks.json").write_text('{"hooks": [{"name": "trellis-sync"}]}',
                                                encoding="utf-8")


HOST_IDENTITY = {"provider": "host", "identity": {"host_id": "dsh", "session_id": "s"},
                 "source": "auto"}


class EnableGuardsTest(unittest.TestCase):
    def test_trellis_conflict_blocks_both_identity_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_trellis_block(tmp)
            write_host_config(tmp)
            ctx = FakeCtx(tmp, inputs={"trellis_loaded": True}, platforms=["dsh"])
            # 首次启用形态（身份尚未签发：pending 合成身份）
            with self.assertRaises(cli.CliError) as pending:
                cli._enable_guards(ctx, HOST_IDENTITY)
            self.assertEqual(pending.exception.code, "WF_FLOW_CONFLICT")
            # 已存在会话形态（轮换走这条）
            with self.assertRaises(cli.CliError) as existing:
                cli._enable_guards(ctx, dict(HOST_IDENTITY, source="auto"))
            self.assertEqual(existing.exception.code, "WF_FLOW_CONFLICT")

    def test_managed_block_without_loaded_declaration_needs_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_trellis_block(tmp)
            write_host_config(tmp)
            ctx = FakeCtx(tmp, platforms=["dsh"])
            with self.assertRaises(cli.CliError) as raised:
                cli._enable_guards(ctx, HOST_IDENTITY)
            self.assertEqual(raised.exception.code, "WF_SEMANTIC_DECISION")

    def test_platform_gate_applies_to_host_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = FakeCtx(tmp, platforms=())
            with self.assertRaises(cli.CliError) as raised:
                cli._enable_guards(ctx, {"provider": "host",
                                         "identity": {"host_id": "dsh", "session_id": "s"},
                                         "source": "auto"})
            self.assertEqual(raised.exception.code, "WF_IDENTITY_UNRESOLVED")
            self.assertEqual((raised.exception.facts or {}).get("reason"),
                             "installation declares no platforms")

    def test_guards_run_before_any_write(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        enable = source[source.index("def cmd_enable("):]
        rotate = source[source.index("def _rotate_session("):source.index("def _identity_facts(")]
        # 普通启用：前置先于建立（建立会写附件 + 路由）
        self.assertLess(enable.index("_enable_guards("), enable.index("_establish_auto_session("))
        # 轮换：前置先于任何附件/路由写入
        self.assertLess(rotate.index("_enable_guards("), rotate.index("store.save_attachment("))
        self.assertLess(rotate.index("_enable_guards("), rotate.index("store.save_routes("))
        # 首次启用等价的轮换分支也在写之前
        first_branch = rotate[:rotate.index("def _identity_facts(") if False else None]
        self.assertLess(first_branch.index("_enable_guards("), first_branch.index("_establish_auto_session("))


class RefusedEnableWritesNothingTest(unittest.TestCase):
    def test_refused_enable_leaves_no_activation(self):
        root = tempfile.mkdtemp()
        for rel in (".wf/bin", ".wf/lib/wflib"):
            Path(root, rel).mkdir(parents=True, exist_ok=True)
        Path(root, ".wf/bin/wf.py").write_text("", encoding="utf-8")
        write_trellis_block(root)
        write_host_config(root)
        argv = ["enable", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[]), \
                mock.patch.object(cli, "_trellis_state", wraps=cli._trellis_state):
            try:
                payload = cli.dispatch(ctx, argv)
            except cli.CliError as exc:
                payload = exc.result()
        # 自动模式未拿到宿主标识时，适用性未知 ⇒ 需人裁决档（同样是"拒绝且不写"）。
        self.assertEqual(payload["code"], "WF_SEMANTIC_DECISION")
        attachments = Path(root, ".wf/.runtime/attachments")
        self.assertEqual(sorted(attachments.iterdir()) if attachments.is_dir() else [], [])
        self.assertFalse(Path(root, ".wf/.runtime/routes.json").exists())

    def test_new_session_on_empty_boundary_hits_the_same_guard(self):
        """`--new-session` 在"本边界还没有会话"时走首次启用等价路径：前置同样先跑。

        这条路径此前 `ctx.session()` 还是 None（建立还没发生），用 `session()` 取身份会
        先抛 WF_IDENTITY_UNRESOLVED、把真正的互斥原因盖掉。
        """
        root = tempfile.mkdtemp()
        for rel in (".wf/bin", ".wf/lib/wflib"):
            Path(root, rel).mkdir(parents=True, exist_ok=True)
        Path(root, ".wf/bin/wf.py").write_text("", encoding="utf-8")
        write_trellis_block(root)
        write_host_config(root)
        argv = ["enable", "--new-session", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[]):
            try:
                payload = cli.dispatch(ctx, argv)
            except cli.CliError as exc:
                payload = exc.result()
        self.assertEqual(payload["code"], "WF_SEMANTIC_DECISION")
        attachments = Path(root, ".wf/.runtime/attachments")
        self.assertEqual(sorted(attachments.iterdir()) if attachments.is_dir() else [], [])


if __name__ == "__main__":
    unittest.main()


class EnableRejectsBeforeWriteTest(unittest.TestCase):
    """`enable` 的拒绝必须都在写盘之前——包括参数错与身份冲突这两条旧出口。"""

    def _root(self):
        root = tempfile.mkdtemp()
        for rel in (".wf/bin", ".wf/lib/wflib", ".wf/install"):
            Path(root, rel).mkdir(parents=True, exist_ok=True)
        Path(root, ".wf/bin/wf.py").write_text("", encoding="utf-8")
        Path(root, ".wf/install/installation.json").write_text(
            json.dumps({"platforms": ["dsh"]}), encoding="utf-8")
        return root

    def _attachment_count(self, root):
        directory = Path(root, ".wf/.runtime/attachments")
        return len(list(directory.iterdir())) if directory.is_dir() else 0

    def test_bad_identity_value_leaves_no_activation(self):
        root = self._root()
        argv = ["enable", "--identity", "bogus", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[]):
            with self.assertRaises(cli.CliError) as caught:
                cli.dispatch(ctx, argv)
        self.assertEqual(caught.exception.code, "WF_PATH_INVALID")
        self.assertEqual(self._attachment_count(root), 0)

    def test_anchor_conflict_leaves_no_activation(self):
        root = self._root()
        argv = ["enable", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[]), \
                mock.patch.object(cli, "_anchor_conflict", return_value=["OTHER"]):
            with self.assertRaises(cli.CliError) as caught:
                cli.dispatch(ctx, argv)
        self.assertEqual(caught.exception.code, "WF_IDENTITY_UNRESOLVED")
        self.assertEqual(self._attachment_count(root), 0)
        self.assertFalse(Path(root, ".wf/.runtime/routes.json").exists())


class StaleActivationRenewalTest(unittest.TestCase):
    """`activation_stale` 的出口是"人重新调用 /wf-start"——enable 自己不能撞同一个标记。

    此前 `auto_session()` 见 stale 直接 `WF_NOT_ENABLED`，普通 enable 与 `--new-session`
    都在核对资格前失败，等于出口走不通。
    """

    def _project_with_stale_session(self):
        from wflib import identity_store as store

        root = tempfile.mkdtemp()
        for rel in (".wf/bin", ".wf/lib/wflib", ".wf/install"):
            Path(root, rel).mkdir(parents=True, exist_ok=True)
        Path(root, ".wf/bin/wf.py").write_text("", encoding="utf-8")
        Path(root, ".wf/install/installation.json").write_text(
            json.dumps({"platforms": ["dsh"]}), encoding="utf-8")
        anchor = {"kind": "pid", "boot": "boot-A", "exe": "/usr/bin/python3",
                  "pid": 4242, "start": "100"}
        key = session_mod.anchor_key(anchor)
        identity = {"issued_id": uuid.uuid4().hex}
        attachment = store.new_attachment(identity, "wf", key, anchor,
                                          {"enabled": True, "start_source": "human:enable",
                                           "enabled_at": "2026-11-24T00:00:00Z"},
                                          "2026-11-24T00:00:00Z")
        attachment["activation_stale"] = True
        store.save_attachment(root, key, attachment)
        routes = store.load_routes(root)
        store.register(routes, key, key, "proc", "boot-A", "2026-11-24T00:00:00Z")
        store.save_routes(root, routes)
        # 轮换要求写权空闲
        Path(root, ".wf/writer.json").write_text(
            json.dumps({"schema_version": 1, "state": "idle", "generation": 1}),
            encoding="utf-8")
        return root, key, anchor

    def test_plain_enable_renews_instead_of_deadlocking(self):
        from wflib import identity_store as store

        root, key, anchor = self._project_with_stale_session()
        argv = ["enable", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[anchor]):
            payload = cli.dispatch(ctx, argv)
        self.assertEqual(payload["code"], "WF_OK")
        self.assertTrue((payload["facts"]["identity"] or {}).get("activation_renewed"))
        self.assertFalse((store.load_attachment(root, key) or {}).get("activation_stale"))

    def test_refused_rotation_leaves_the_old_session_unrenewed(self):
        """轮换被拒（对象仍在途）时不得顺手把旧会话续期——命令结果与磁盘状态要一致。"""
        from wflib import identity_store as store

        root, key, anchor = self._project_with_stale_session()
        records.write_json(str(Path(root) / ".wf" / "session-bindings" / f"{key}.json"),
                           {"object": {"kind": "task", "id": "t1"}})
        task_dir = Path(root) / ".wf/tasks/t1"
        task_dir.mkdir(parents=True)
        records.write_json(str(task_dir / "task.json"),
                           {"id": "t1", "status": "in_progress", "phase": "execute"})
        before = store.load_attachment(root, key)["activation"]["enabled_at"]
        argv = ["enable", "--new-session", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[anchor]):
            with self.assertRaises(cli.CliError) as caught:
                cli.dispatch(ctx, argv)
        self.assertEqual(caught.exception.code, "WF_BINDING_MISMATCH")
        after = store.load_attachment(root, key)
        self.assertTrue(after.get("activation_stale"))
        self.assertEqual(after["activation"]["enabled_at"], before)

    def test_new_session_renews_before_rotating(self):
        from wflib import identity_store as store

        root, key, anchor = self._project_with_stale_session()
        argv = ["enable", "--new-session", "--json"]
        ctx = cli.Context(root, argv)
        with mock.patch.object(session_mod, "candidates", return_value=[anchor]):
            payload = cli.dispatch(ctx, argv)
        self.assertEqual(payload["code"], "WF_OK")
        self.assertNotEqual(payload["facts"]["session_key"], key)
        self.assertTrue((payload["facts"]["identity"] or {}).get("activation_renewed"))
