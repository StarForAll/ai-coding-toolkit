"""受控返工 R 上的游标处置（机制稿 §6.2、§7.3）。

三条分支，逐条给事实：
- R 未归档 → 报等待，**游标不动**，且不把 R 当原定义步骤完成；
- R 已归档但 T 仍挂起 → 报等待复评；
- R 已归档且 T 已复评 → **按 `resume_task` 把游标返回 T**（并在 run.advance 动作里留痕）。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402

RUN = "2026-" + "1" * 32
PARENT = "2026-" + "2" * 32
REWORK = "2026-" + "3" * 32


class _Ctx:
    def __init__(self, root):
        self.root = Path(root)

    def key(self, **_kwargs):
        return "sess-cursor"

    def require_held(self, **_kwargs):
        return {"state": "held"}, {"scope": {"object": {"kind": "run", "id": RUN}}}

    def inputs(self):
        return {"generation": 1}

    def rule_version(self):
        return "sha256:" + "b" * 64


def _write(root, run=None, tasks=()):
    os.makedirs(os.path.join(root, ".wf/workflow-runs"), exist_ok=True)
    if run is not None:
        with open(os.path.join(root, ".wf/workflow-runs", f"{RUN}.json"), "w", encoding="utf-8") as handle:
            json.dump(run, handle, ensure_ascii=False)
    for task in tasks:
        directory = os.path.join(root, ".wf/tasks", task["id"])
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "task.json"), "w", encoding="utf-8") as handle:
            json.dump(task, handle, ensure_ascii=False)


def _task(task_id, **extra):
    record = {"schema_version": 1, "id": task_id, "status": "in_progress", "phase": "execute",
              "title": task_id, "prerequisites": [], "action": None}
    record.update(extra)
    return record


SEQUENCE = [{"kind": "rework", "step_id": "one", "source_task": PARENT,
             "task_id": REWORK, "resume_task": PARENT}]


class ReworkCursorTest(unittest.TestCase):
    def _base(self, rework_status, parent_suspended):
        root = tempfile.mkdtemp(prefix="wf-cursor-")
        run = {"id": RUN, "workflow_id": "demo", "revision": 2, "sequence_changes": SEQUENCE,
               "cursor": {"step_id": "one", "task_id": REWORK},
               "definition": {"digest": "sha256:" + "a" * 64, "snapshot_path": "x"}, "action": None}
        _write(root, run, [_task(REWORK, status=rework_status), _task(PARENT, suspended=parent_suspended)])
        return _Ctx(root), run

    def test_unarchived_rework_reports_waiting_and_keeps_cursor(self):
        ctx, run = self._base("in_progress", True)
        payload = runs._return_from_rework(ctx, run, SEQUENCE, run["cursor"], {})
        self.assertEqual(payload["facts"]["controlled_rework"], REWORK)
        self.assertEqual(payload["facts"]["rework_status"], "in_progress")
        self.assertNotIn("cursor", payload["facts"], "未归档时不应改动游标")
        with open(ctx.root / ".wf/workflow-runs" / f"{RUN}.json", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["cursor"]["task_id"], REWORK)

    def test_archived_but_suspended_reports_waiting_for_reassessment(self):
        ctx, run = self._base("archived", True)
        payload = runs._return_from_rework(ctx, run, SEQUENCE, run["cursor"], {})
        self.assertTrue(payload["facts"]["resume_suspended"])
        with open(ctx.root / ".wf/workflow-runs" / f"{RUN}.json", encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["cursor"]["task_id"], REWORK)

    def test_archived_and_reassessed_returns_cursor_to_parent(self):
        ctx, run = self._base("archived", False)
        payload = runs._return_from_rework(ctx, run, SEQUENCE, run["cursor"], {})
        self.assertEqual(payload["facts"]["resume_task"], PARENT)
        self.assertEqual(payload["facts"]["cursor"]["task_id"], PARENT)
        with open(ctx.root / ".wf/workflow-runs" / f"{RUN}.json", encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["cursor"]["task_id"], PARENT, "游标必须按登记返回 T")
        self.assertEqual(stored["action"]["kind"], "run.advance", "返回定位要在动作里留痕")

    def test_plain_task_cursor_is_untouched(self):
        ctx, run = self._base("in_progress", True)
        self.assertIsNone(runs._return_from_rework(ctx, run, [], run["cursor"], {}))


if __name__ == "__main__":
    unittest.main()
