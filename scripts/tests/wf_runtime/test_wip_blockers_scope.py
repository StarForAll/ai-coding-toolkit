"""`wip_blockers` 的排除面与 settled 处置面。

2026-11-27 第五/六轮独立审查：
- 排除面必须按**绑定对象**判：实例绑定会话重取写权时，实例步骤任务的自身 `e∩dirty`
  不能被当成别人的保留 WIP（否则永远回不到 Check）。
- 已 `resolved` 的登记路径（含 `transfer` 承接）既不再阻断任何人，也不回到原任务的 e 桶；
  此前 resolved 后路径被 `owned_dirty` 算回持有方，承接方拿不到写权。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli  # noqa: E402
from wflib import runs as runs_mod  # noqa: E402
from wflib import scope as scope_mod  # noqa: E402
from wflib import tasks as tasks_mod  # noqa: E402

RUN = "2026-" + "a" * 32
TASK = "2026-" + "b" * 32
OTHER = "2026-" + "c" * 32


def _task(task_id, *, run_id=None, wip=None, resolved=None):
    record = {"id": task_id, "status": "in_progress", "phase": "execute",
              "plan": {"touch_paths": ["pkg/**"]},
              "entry_snapshot": {"baseline_head": "deadbeef", "touch_paths": ["pkg/**"]}}
    if run_id:
        record["run_id"] = run_id
    if wip:
        record["handoff"] = {"wip": {"paths": [{"path": path} for path in wip], "resolved": resolved}}
    return record


def _classifier(_root, task, receipts=None):
    """按任务给出 e 桶：实例任务自己改脏的路径、其他任务改脏的路径。"""
    own = "pkg/own.py" if task.get("id") == TASK else "pkg/theirs.py"
    return {"buckets": {"a": [], "b": [], "c": [], "d": [], "e": [own], "f": [], "v": [], "x": []},
            "candidates": [own], "touch_paths": ["pkg/**"], "entry_snapshot": {},
            "vendor_dirty": [], "exclusions": {}, "conflicts": [], "preexisting_in_scope": []}


class WipBlockersScopeTest(unittest.TestCase):
    def _blocked(self, records, exclude_scope, dirty):
        run = {"id": RUN, "terminal": None, "cursor": {"task_id": TASK},
               "task_map": {"step-1": {"task_id": TASK}}, "sequence_changes": []}
        with mock.patch.object(tasks_mod, "iter_tasks",
                               return_value=[(None, item) for item in records]), \
                mock.patch.object(tasks_mod, "load_task", side_effect=lambda r, t: next(
                    (i for i in records if i.get("id") == t), None)), \
                mock.patch.object(scope_mod, "uncommitted_paths", return_value=list(dirty)), \
                mock.patch.object(runs_mod, "load_run", return_value=run), \
                mock.patch("wflib.fingerprint.item",
                           return_value={"path": "x", "digest": "sha256:x", "exists": True}), \
                mock.patch.object(scope_mod, "classify_candidates", side_effect=_classifier):
            return cli.wip_blockers("/nonexistent", exclude_scope=exclude_scope)

    def test_instance_scope_excludes_its_own_delivery(self):
        """实例步骤任务自己 e∩dirty 的路径不算外来（走 owned_dirty 通道，不靠 handoff.wip）。"""
        records = [_task(TASK, run_id=RUN), _task(OTHER, wip=["pkg/theirs.py"])]
        blocked = self._blocked(records, {"kind": "run", "id": RUN}, ["pkg/own.py", "pkg/theirs.py"])
        ids = {item.get("task") for item in blocked}
        self.assertNotIn(TASK, ids, "实例自己的交付不应被当成外来 WIP")
        self.assertIn(OTHER, ids, "其他任务的保留 WIP 仍须阻断")

    def test_task_scope_only_excludes_that_task(self):
        records = [_task(TASK, wip=["pkg/own.py"]), _task(OTHER, wip=["pkg/theirs.py"])]
        blocked = self._blocked(records, {"kind": "task", "id": TASK}, ["pkg/own.py", "pkg/theirs.py"])
        ids = {item.get("task") for item in blocked}
        self.assertNotIn(TASK, ids)
        self.assertIn(OTHER, ids)

    def test_no_scope_blocks_everything(self):
        records = [_task(TASK, run_id=RUN), _task(OTHER, wip=["pkg/theirs.py"])]
        blocked = self._blocked(records, None, ["pkg/own.py", "pkg/theirs.py"])
        ids = {item.get("task") for item in blocked}
        self.assertEqual(ids, {TASK, OTHER})

    def test_resolved_registration_blocks_nobody(self):
        """transfer/已处置：settled 路径（摘要仍匹配）不再阻断任何人（含原持有方与承接方）。"""
        record = _task(OTHER)
        record["handoff"] = {"wip": {"paths": [{"path": "pkg/theirs.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer", "at": "t"}}}
        blocked = self._blocked([record, _task(OTHER)], None, ["pkg/theirs.py"])
        self.assertEqual(blocked, [])

    def test_resolved_registration_does_not_hide_another_tasks_unresolved_wip(self):
        """A 已处置同一路径、B 之后又登记未处置 → 第三方仍被 B 阻断（第七轮复审回归面）。"""
        records = [_task(TASK, wip=["pkg/x.py"], resolved={"choice": "transfer", "at": "t"}),
                   _task(OTHER, wip=["pkg/x.py"])]
        blocked = self._blocked(records, None, ["pkg/x.py"])
        ids = {item.get("task") for item in blocked}
        self.assertEqual(ids, {OTHER}, "已处置的登记不能掩盖他任务的未处置登记")

    def test_settled_path_does_not_hide_third_party_unregistered_dirt(self):
        """A 已处置 P；C 把 P 改脏但无登记；第三方 B 取写权时仍必须被 C 挡（第八轮复审 F1）。"""
        records = [_task(TASK, wip=["pkg/x.py"], resolved={"choice": "transfer", "at": "t"}),
                   _task(OTHER)]  # OTHER 无 WIP 登记
        def classifier(_root, task, receipts=None):
            own = ["pkg/x.py"] if task.get("id") == OTHER else []
            return {"buckets": {"a": [], "b": [], "c": [], "d": [], "e": own, "f": [], "v": [], "x": []},
                    "candidates": own, "touch_paths": ["pkg/**"], "entry_snapshot": {},
                    "vendor_dirty": [], "exclusions": {}, "conflicts": [], "preexisting_in_scope": []}
        with mock.patch.object(tasks_mod, "iter_tasks",
                              return_value=[(None, item) for item in records]), \
                mock.patch.object(scope_mod, "uncommitted_paths", return_value=["pkg/x.py"]), \
                mock.patch.object(scope_mod, "classify_candidates", side_effect=classifier):
            blocked = cli.wip_blockers("/nonexistent",
                                       exclude_scope={"kind": "task", "id": "2026-" + "d" * 32})
        ids = {item.get("task") for item in blocked}
        self.assertIn(OTHER, ids, "已处置登记不得掩盖第三方的未登记未提交改动")

    def test_rework_lineage_source_does_not_block_binding_r(self):
        """绑定 R 时，其来源 T 的保留 WIP 由 R 承接（机制稿 §6.2，人裁方案①）。"""
        source = _task(TASK, wip=["pkg/x.py"])          # T：返工来源，保留 WIP
        rework = _task(OTHER)                            # R：rework_of=T
        rework["rework_of"] = TASK
        blocked = self._blocked_with([source, rework], None, ["pkg/x.py"],
                                     exclude_scope={"kind": "task", "id": OTHER})
        ids = {item.get("task") for item in blocked}
        self.assertNotIn(TASK, ids, "来源 T 的保留 WIP 不应挡住承接方 R")
        self.assertNotIn(OTHER, ids)

    def _blocked_with(self, records, exclude_id, dirty, exclude_scope=None):
        owner = self._blocked
        # 复用 _blocked 的 mock 组合，但允许自定义 exclude_scope/exclude_id
        def load(root, task_id):
            return next((item for item in records if item.get("id") == task_id), None)

        with mock.patch.object(tasks_mod, "iter_tasks",
                               return_value=[(None, item) for item in records]), \
                mock.patch.object(tasks_mod, "load_task", side_effect=load), \
                mock.patch.object(scope_mod, "uncommitted_paths", return_value=list(dirty)), \
                mock.patch.object(runs_mod, "load_run", return_value=None), \
                mock.patch.object(scope_mod, "classify_candidates", side_effect=_classifier):
            return cli.wip_blockers("/nonexistent", exclude_id=exclude_id,
                                    exclude_scope=exclude_scope)

    def test_transferred_path_belongs_to_receiver(self):
        """transfer 后归属承接方（人裁 §13）：承接方取写权不被挡，其他第三方被承接方挡。"""
        record = _task(OTHER)
        record["handoff"] = {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer",
                                                  "evidence": {"transferred_to": TASK},
                                                  "at": "t"}}}
        # 承接方 TASK 自己取写权：不被挡
        blocked = self._blocked_with([record, _task(TASK)], None, ["pkg/x.py"],
                                     exclude_scope={"kind": "task", "id": TASK})
        self.assertEqual({item.get("task") for item in blocked}, set(),
                         "承接方不应被它接手的路径挡住")
        # 第三方（未承接）取写权：被承接方挡
        blocked = self._blocked_with([record, _task(TASK)], None, ["pkg/x.py"],
                                     exclude_scope={"kind": "task", "id": "2026-" + "d" * 32})
        self.assertIn(TASK, {item.get("task") for item in blocked},
                      "第三方必须被承接方挡住")

    def test_two_keep_registrations_still_block(self):
        """存量双登记（A、B 对同一路径各有一条 keep）仍阻断第三方（人裁 §8 的存量核验）。"""
        records = [_task(TASK, wip=["pkg/x.py"]), _task(OTHER, wip=["pkg/x.py"])]
        blocked = self._blocked(records, None, ["pkg/x.py"])
        ids = {item.get("task") for item in blocked}
        # 存量双登记的先到先得是既有行为（backlog §8）；人裁只要求新判据不把它们一并放行。
        self.assertTrue(ids, "两份未处置登记中至少一方必须仍在阻断面")
        self.assertIn(TASK, ids, "先登记的一方（显式归属）仍须阻断")

    def test_requester_matches_run_scope_for_transferred_path(self):
        """实例绑定的承接任务（cursor）自取写权时不被自己承接的路径挡（R14 F1 / R15 F3）。"""
        run = {"id": RUN, "terminal": None, "cursor": {"task_id": TASK},
               "task_map": {"s1": {"task_id": TASK}}, "sequence_changes": []}
        record = _task(OTHER)
        record["handoff"] = {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer",
                                                  "evidence": {"transferred_to": TASK},
                                                  "at": "t"}}}
        with mock.patch.object(tasks_mod, "iter_tasks", return_value=[(None, record), (None, _task(TASK))]), \
                mock.patch.object(scope_mod, "uncommitted_paths", return_value=["pkg/x.py"]), \
                mock.patch.object(runs_mod, "load_run", return_value=run), \
                mock.patch("wflib.fingerprint.item",
                           return_value={"path": "pkg/x.py", "digest": "sha256:x", "exists": True}), \
                mock.patch.object(scope_mod, "classify_candidates", side_effect=_classifier):
            blocked = cli.wip_blockers("/nonexistent", exclude_scope={"kind": "run", "id": RUN})
        self.assertEqual(blocked, [], "实例内承接任务不应被自己承接的路径挡住")

    def test_transfer_survives_holder_archive(self):
        """转移方归档后，承接方仍挡住第三方（R19 F2：归属事实不能随归档消失）。"""
        holder = _task(OTHER)
        holder["status"] = "archived"
        holder["handoff"] = {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer",
                                                  "evidence": {"transferred_to": TASK},
                                                  "at": "t"}}}
        blocked = self._blocked([holder, _task(TASK)], None, ["pkg/x.py"])
        self.assertIn(TASK, {item.get("task") for item in blocked},
                      "第三方必须被承接方挡住，即使转移方已归档")

    def test_chained_transfer_owner_is_latest(self):
        """链式 transfer：归属收敛到最近一次（R20 F1），归档旧记录不覆盖较新承接方。"""
        holder = _task(OTHER)
        holder["status"] = "archived"
        holder["handoff"] = {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer",
                                                  "evidence": {"transferred_to": TASK},
                                                  "at": "2026-01-01T00:00:00Z"}}}
        middle = _task("2026-" + "a" * 32)
        middle["handoff"] = {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                     "resolved": {"choice": "transfer",
                                                  "evidence": {"transferred_to": "2026-" + "c" * 32},
                                                  "at": "2026-02-01T00:00:00Z"}}}
        blocked = self._blocked([middle, holder, _task("2026-" + "c" * 32)], None, ["pkg/x.py"])
        ids = {item.get("task") for item in blocked}
        self.assertIn("2026-" + "c" * 32, ids, "最近一次的承接方应成为归属方")
        self.assertNotIn(TASK, ids, "较早的承接方不应覆盖链尾")

    def test_focused_run_scope_still_blocks_other_step_tasks(self):
        """口径乙（聚焦＋谱系）：同实例但非 cursor、非谱系的步骤任务仍须阻断（F4）。"""
        run = {"id": RUN, "terminal": None, "cursor": {"task_id": TASK},
               "task_map": {"s1": {"task_id": TASK}, "s2": {"task_id": OTHER}},
               "sequence_changes": []}
        records = [_task(TASK, run_id=RUN, wip=["pkg/own.py"]),
                   _task(OTHER, run_id=RUN, wip=["pkg/theirs.py"])]

        def load(root, task_id):
            return next((item for item in records if item.get("id") == task_id), None)

        with mock.patch.object(tasks_mod, "iter_tasks",
                               return_value=[(None, item) for item in records]), \
                mock.patch.object(tasks_mod, "load_task", side_effect=load), \
                mock.patch.object(scope_mod, "uncommitted_paths",
                                  return_value=["pkg/own.py", "pkg/theirs.py"]), \
                mock.patch.object(runs_mod, "load_run", return_value=run), \
                mock.patch.object(scope_mod, "classify_candidates", side_effect=_classifier):
            blocked = cli.wip_blockers("/nonexistent", exclude_scope={"kind": "run", "id": RUN})
        ids = {item.get("task") for item in blocked}
        self.assertEqual(ids, {OTHER}, "非当前任务的同实例步骤任务必须仍阻断")

    def test_missing_run_record_is_history_problem(self):
        records = [_task(TASK, run_id=RUN)]
        with self.assertRaises(cli.CliError) as caught:
            with mock.patch.object(tasks_mod, "iter_tasks",
                                   return_value=[(None, item) for item in records]), \
                    mock.patch.object(scope_mod, "uncommitted_paths", return_value=[]), \
                    mock.patch.object(runs_mod, "load_run", return_value=None):
                cli.wip_blockers("/nonexistent", exclude_scope={"kind": "run", "id": RUN})
        self.assertEqual(caught.exception.code, "WF_HISTORY_UNRESOLVED")


if __name__ == "__main__":
    unittest.main()