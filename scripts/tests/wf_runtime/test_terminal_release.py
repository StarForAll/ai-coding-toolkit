"""对象终态后的写权释放与出口口径（机制稿 §5.3「归档成功后处理写权释放」、§7.4「最后释放」；§1.4 四态③轮换出口）。

防的失败（2026-11-27 主链路实测 + dogfood 会话 2/3/4）：
1. task.abandon / run.finish / run.terminate 持久化成功后写权仍 held——下一个对象被
   `WF_WRITER_BUSY` 挡住，出口"新会话接续"不可执行；
2. 终态收尾的出口仍写"下一对象需在新会话选择"，不指向 W3-1 的同边界轮换入口
   `enable --new-session`（AI/人被送回"另开终端"的旧路）；
3. status 的 facts.task 缺 directory——help 的 --review-notes 指引说"用 status 回显的
   directory"，回显却没有该字段（承诺位与事实位脱节）。
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, runs, session as session_mod, tasks  # noqa: E402

STOP_DECISION = {"subject": "stop t1", "choice": "放弃", "reason": "测试",
                 "at": "2026-11-27T00:00:00Z", "source": "human:test", "object_digest": None}


def _writer_ctx(state="held", scope=None, binding=None):
    """writer 上下文：holder 按传入 scope 构造（task/run 两态共用）。"""
    holder = {"kind": "session", "id": "sess-test", "generation": 3,
              "scope": {"object": scope or {"kind": "task", "id": "t1"}}}
    writer = {"state": state, "generation": 3, "holder": holder}
    ctx = SimpleNamespace(root="/tmp/not-used", writer=lambda: writer,
                          key=lambda: "sess-test", rule_version=lambda: "sha256:" + "0" * 64)
    ctx.require_held = lambda task=None: (None, holder)
    # `_require_instance_match` 读会话侧车的 instance_id；单元夹具两侧给同一假 id，
    # 与真实"绑定与请求实例标识一致"同形（缺失该链路的其余事实不经此测试面）。
    ctx.session = lambda required=False: {"instance_id": "inst-test"}
    ctx.platforms = lambda: ["dsh"]
    ctx._binding = binding
    ctx._binding_patch = mock.patch.object(session_mod, "load_binding",
                                           return_value=binding or {})
    return ctx, holder


class AbandonReleaseTest(unittest.TestCase):
    """task-abandon 成功路径：记录提交后释放写权，出口走 _archive_next。"""

    def test_apply_abandon_releases_after_commit(self):
        ctx, holder = _writer_ctx(scope={"kind": "task", "id": "t1"})
        task = {"id": "t1", "title": "T", "kind": "ordinary", "status": "archived",
                "phase": "finish", "terminal": "abnormal", "archived_at": "2026-11-27T00:00:00Z",
                "disposition": {"pending": [], "changes": [], "targets": []},
                "action": {"id": "a1", "state": "done"}}
        path = "/tmp/not-used/.wf/tasks/t1-x"
        with mock.patch.object(tasks, "_abandon_preview",
                               return_value={"uncommitted": [], "required_disposition_for": []}), \
             mock.patch.object(tasks, "_archive_destination",
                               return_value=path + "-arch"), \
             mock.patch.object(tasks, "_move_task", return_value=path), \
             mock.patch.object(tasks, "_commit_paths",
                               return_value={"committed": True, "head": "0" * 40}), \
             mock.patch.object(tasks, "_record_committed", return_value=True), \
             mock.patch.object(tasks, "_release_after_archive",
                               return_value={"released": True, "generation": 4}):
            result = tasks._apply_abandon(ctx, "t1", task, path, [STOP_DECISION], None, holder)
        self.assertEqual(result["code"], "WF_OK")
        self.assertTrue(result["facts"]["write_release"]["released"])
        self.assertIn("enable --new-session", result["next"])

    def test_apply_abandon_inside_run_terminate_keeps_writer(self):
        """run terminate 复用 _apply_abandon：holder scope 是在途 run，不得释放。"""
        ctx, holder = _writer_ctx(scope={"kind": "run", "id": "r1"})
        task = {"id": "t1", "title": "T", "kind": "ordinary", "status": "archived",
                "phase": "finish", "terminal": "abnormal", "archived_at": "2026-11-27T00:00:00Z",
                "disposition": {"pending": [], "changes": [], "targets": []},
                "action": {"id": "a1", "state": "done"}}
        path = "/tmp/not-used/.wf/tasks/t1-x"
        with mock.patch.object(tasks, "_abandon_preview",
                               return_value={"uncommitted": [], "required_disposition_for": []}), \
             mock.patch.object(tasks, "_archive_destination",
                               return_value=path + "-arch"), \
             mock.patch.object(tasks, "_move_task", return_value=path), \
             mock.patch.object(tasks, "_commit_paths",
                               return_value={"committed": True, "head": "0" * 40}), \
             mock.patch.object(tasks, "_record_committed", return_value=True), \
             mock.patch.object(tasks, "_release_after_archive",
                               return_value={"released": False, "kept": "run", "run": "r1"}):
            result = tasks._apply_abandon(ctx, "t1", task, path, [STOP_DECISION], None, holder)
        self.assertEqual(result["code"], "WF_OK")
        self.assertFalse(result["facts"]["write_release"]["released"])


class ReleaseAfterArchiveRunScopeTest(unittest.TestCase):
    """_release_after_archive 对 run scope 的两态：在途保留、终态释放。"""

    def test_inflight_run_is_kept(self):
        ctx, holder = _writer_ctx(scope={"kind": "run", "id": "r1"})
        with mock.patch.object(runs, "load_run", return_value={"id": "r1", "terminal": None}), \
             mock.patch.object(cli, "_release_writer_locked") as release:
            fact = tasks._release_after_archive(ctx, "t1", holder=holder)
        self.assertFalse(fact["released"])
        self.assertEqual(fact.get("kept"), "run")
        self.assertFalse(release.called)

    def test_terminal_run_is_released(self):
        ctx, holder = _writer_ctx(scope={"kind": "run", "id": "r1"})
        with mock.patch.object(runs, "load_run", return_value={"id": "r1", "terminal": "normal"}), \
             mock.patch.object(cli, "_release_writer_locked",
                               return_value=({"generation": 4}, {"ok": True})) as release:
            fact = tasks._release_after_archive(ctx, "r1", holder=holder)
        self.assertTrue(fact["released"])
        self.assertTrue(release.called)

    def test_missing_run_record_fails_closed(self):
        """记录读不到不得当作在途保留（unknown 不放行）：报事实并给 writer release 出口。"""
        ctx, holder = _writer_ctx(scope={"kind": "run", "id": "r1"})
        with mock.patch.object(runs, "load_run", return_value=None), \
             mock.patch.object(cli, "_release_writer_locked") as release:
            fact = tasks._release_after_archive(ctx, "r1", holder=holder)
        self.assertFalse(fact["released"])
        self.assertNotEqual(fact.get("kept"), "run")
        self.assertFalse(release.called)


class TerminalExitTextTest(unittest.TestCase):
    """终态收尾出口统一指向 enable --new-session（机制稿 §1.4 四态③）。"""

    def test_archive_next_released_points_to_rotation(self):
        text = tasks._archive_next({"released": True})
        self.assertIn("enable --new-session", text)
        self.assertNotIn("新会话选择", text)

    def test_archive_next_kept_run_still_points_to_advance(self):
        text = tasks._archive_next({"kept": "run"})
        self.assertIn("run advance", text)

    def test_old_idle_release_exit_is_gone(self):
        """writer release 幂等出口不再写"下一对象需在新会话选择"。"""
        ctx, _holder = _writer_ctx(state="idle")
        result = cli._writer_release(ctx)
        self.assertIn("enable --new-session", result["next"])


class PersistPendingReleaseGateTest(unittest.TestCase):
    """终态但记录组未持久化时，`writer release` 必须拒绝（2026-11-27 审查 F1）。

    机制稿 §5.3「归档成功后处理写权释放」：persist_pending 期间写权是续做提交的唯一
    在途权威，释放后重入只能撞 WF_WRITER_BUSY——那正是审查实测的死路。
    """

    def test_archived_uncommitted_task_refuses_release(self):
        task = {"id": "t1", "status": "archived", "terminal": "normal", "paused": False,
                "suspended": False, "disposition": {"pending": []}}
        with mock.patch.object(tasks, "task_dir", return_value="/tmp/not-used/.wf/tasks/t1-s"), \
             mock.patch.object(tasks, "_record_committed", return_value=False):
            with self.assertRaises(tasks.TaskError) as ctx:
                tasks.ensure_releasable(task, root="/tmp/not-used")
        self.assertEqual(ctx.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("not committed", (ctx.exception.facts or {}).get("reason", ""))

    def test_archived_committed_task_allows_release(self):
        task = {"id": "t1", "status": "archived", "terminal": "normal", "paused": False,
                "suspended": False, "disposition": {"pending": []}}
        with mock.patch.object(tasks, "task_dir", return_value="/tmp/not-used/.wf/tasks/t1-s"), \
             mock.patch.object(tasks, "_record_committed", return_value=True):
            self.assertTrue(tasks.ensure_releasable(task, root="/tmp/not-used"))

    def test_ended_unpersisted_run_refuses_release(self):
        from wflib import cli as cli_mod

        ctx, _holder = _writer_ctx(state="held", scope={"kind": "run", "id": "r1"})
        run = {"id": "r1", "terminal": "normal", "paused": False, "cursor": {}}
        with mock.patch.object(runs, "load_run", return_value=run), \
             mock.patch.object(runs, "_run_persist_pending", return_value=True):
            with self.assertRaises(cli_mod.CliError) as caught:
                cli_mod._ensure_run_releasable(ctx, "r1")
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")


class TerminateDecisionChannelTest(unittest.TestCase):
    """run terminate 的记录组提交授权通道（2026-11-27 审查 F2）。"""

    def test_terminate_accepts_decision_flag(self):
        from wflib import cli as cli_mod

        self.assertIn("--decision", cli_mod.COMMAND_SUB_FLAGS["run"]["terminate"])

    def test_terminate_decisions_merge_extra(self):
        grant = {"choice": "commit", "subject": [".wf/workflow-runs/r1.json"]}
        self.assertEqual(tasks is not None and
                         __import__("wflib.runs", fromlist=["_terminate_decisions"])
                         ._terminate_decisions({}, [grant]), [grant])


class ReleaseSuccessExitTest(unittest.TestCase):
    """释放成功出口按对象状态分档（2026-11-27 审查 F3）。"""

    def _ctx_held_task(self):
        return _writer_ctx(state="held", scope={"kind": "task", "id": "t1"},
                           binding={"object": {"kind": "task", "id": "t1"},
                                    "instance_id": "inst-test"})

    def test_released_ended_task_points_to_rotation(self):
        ctx, holder = self._ctx_held_task()
        task = {"id": "t1", "terminal": "normal", "paused": False, "suspended": False,
                "disposition": {"pending": []}}
        with ctx._binding_patch, \
             mock.patch.object(session_mod, "check_platforms", return_value=(None, {})), \
             mock.patch.object(tasks, "load_task", return_value=task), \
             mock.patch.object(tasks, "ensure_releasable", return_value=True), \
             mock.patch.object(tasks, "archive_persisted", return_value={"persisted": True}), \
             mock.patch.object(cli, "_release_writer_locked",
                               return_value=({"generation": 4}, {"ok": True})):
            result = cli._writer_release(ctx)
        self.assertIn("enable --new-session", result["next"])
        self.assertNotIn("下一对象需在新会话选择", result["next"])

    def test_released_paused_task_points_to_resume(self):
        ctx, holder = self._ctx_held_task()
        task = {"id": "t1", "terminal": None, "paused": True, "suspended": False,
                "disposition": {"pending": []}}
        with ctx._binding_patch, \
             mock.patch.object(session_mod, "check_platforms", return_value=(None, {})), \
             mock.patch.object(tasks, "load_task", return_value=task), \
             mock.patch.object(tasks, "ensure_releasable", return_value=True), \
             mock.patch.object(cli, "_release_writer_locked",
                               return_value=({"generation": 4}, {"ok": True})):
            result = cli._writer_release(ctx)
        self.assertIn("恢复并完成该对象", result["next"])
        self.assertIn("暂停不解除在途绑定", result["next"])


class TaskFactsDirectoryTest(unittest.TestCase):
    """status 的 facts.task 必须带 directory（help 指引的承诺位）。"""

    def test_task_facts_include_directory(self):
        root = Path("/tmp/not-used")
        ctx = SimpleNamespace(root=str(root))
        with mock.patch.object(tasks, "task_dir", return_value=root / ".wf/tasks/t1-slug"), \
             mock.patch("wflib.taskfiles.summary", return_value={"count": 0, "unexpected": []}):
            facts = cli._task_facts(ctx, {"id": "t1", "status": "in_progress", "phase": "plan"})
        self.assertEqual(facts["directory"], ".wf/tasks/t1-slug")


if __name__ == "__main__":
    unittest.main()
