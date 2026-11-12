"""P1-5/6：返工与挂起复评的判定（机制稿 §6.2）。

本文件核**可机械判定**的部分：
- 返工集合 = 所有 `rework_of=T` 的活动与归档记录；
- 复评四条条件的逐条事实（挂起 / 集合非空 / 集合无未归档成员 / 前置满足 / 无未完成动作）；
- 条件不满足是**正常等待**（返回 waiting），不是失败，也不造原因码。

端到端（建 R、T 挂起与前置、同实例 sequence_changes 与 cursor）走
`repro/task-rework.py`。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402

PARENT = "2026-" + "a" * 32
REWORK = "2026-" + "b" * 32


def _root(records):
    root = tempfile.mkdtemp(prefix="wf-rework-")
    for record in records:
        directory = os.path.join(root, ".wf", "tasks", record["id"])
        if record.get("status") == "archived":
            directory = os.path.join(root, ".wf", "tasks", "archive", "2026-11", record["id"])
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "task.json"), "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False)
    return root


def _task(task_id, **extra):
    record = {"schema_version": 1, "id": task_id, "status": "in_progress", "phase": "execute",
              "prerequisites": [], "rework_of": None, "action": None}
    record.update(extra)
    return record


class ReworkSetTest(unittest.TestCase):
    def test_set_collects_active_and_archived_members(self):
        root = _root([_task(PARENT, suspended=True),
                      _task(REWORK, rework_of=PARENT),
                      _task("2026-" + "c" * 32, rework_of=PARENT, status="archived",
                            terminal="normal")])
        members = tasks_mod.rework_set(root, PARENT)
        self.assertEqual(sorted(item["id"] for item in members),
                         [REWORK, "2026-" + "c" * 32])

    def test_conditions_report_each_fact(self):
        root = _root([_task(PARENT, suspended=True), _task(REWORK, rework_of=PARENT)])
        conditions = {item["condition"]: item["ok"]
                      for item in tasks_mod.reassess_problems(root, _task(PARENT, suspended=True))}
        self.assertTrue(conditions["task_suspended"])
        self.assertTrue(conditions["rework_set_non_empty"])
        self.assertFalse(conditions["rework_set_all_archived"], "返工还没归档就不能清挂起")
        self.assertTrue(conditions["prerequisites_satisfied"])

    def test_empty_set_keeps_task_suspended(self):
        root = _root([_task(PARENT, suspended=True)])
        conditions = {item["condition"]: item["ok"]
                      for item in tasks_mod.reassess_problems(root, _task(PARENT, suspended=True))}
        self.assertFalse(conditions["rework_set_non_empty"])

    def test_unmet_prerequisite_blocks_reassessment(self):
        blocker = "2026-" + "d" * 32
        root = _root([_task(PARENT, suspended=True, prerequisites=[blocker]),
                      _task(REWORK, rework_of=PARENT, status="archived", terminal="normal"),
                      _task(blocker, status="in_progress", terminal=None)])
        conditions = {item["condition"]: item["ok"]
                      for item in tasks_mod.reassess_problems(
                          root, _task(PARENT, suspended=True, prerequisites=[blocker]))}
        self.assertFalse(conditions["prerequisites_satisfied"])

    def test_pending_action_blocks_reassessment(self):
        root = _root([_task(PARENT, suspended=True),
                      _task(REWORK, rework_of=PARENT, status="archived", terminal="normal")])
        pending = {"kind": "task.check", "state": "applying"}
        conditions = {item["condition"]: item["ok"]
                      for item in tasks_mod.reassess_problems(
                          root, _task(PARENT, suspended=True, action=pending))}
        self.assertFalse(conditions["no_pending_action"])


if __name__ == "__main__":
    unittest.main()
