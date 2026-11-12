"""P1-2（下半）：`run locate` 只读定位（机制稿 §2.1 的绑定内定位）。

只读：不写任何字段；任务状态一律**查 task**（不抄进实例记录）；读不出就报
`WF_HISTORY_UNRESOLVED`，不把「读不出」当「没有」（未知不当零）。
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402


def _root():
    root = tempfile.mkdtemp(prefix="wf-locate-")
    os.makedirs(os.path.join(root, ".wf", "workflow-runs"), exist_ok=True)
    return root


def _args(run_id):
    return SimpleNamespace(value=lambda name, default=None: run_id if name == "--run" else default)


def _write(root, run_id, payload):
    path = os.path.join(root, ".wf", "workflow-runs", f"{run_id}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)


class RunLocateTest(unittest.TestCase):
    def test_missing_run_is_a_decision_not_absent(self):
        root = _root()
        with self.assertRaises(runs.DefinitionError) as caught:
            runs.locate(SimpleNamespace(root=root), _args("nope"))
        self.assertEqual(caught.exception.code, "WF_HISTORY_UNRESOLVED")

    def test_requires_run_id(self):
        with self.assertRaises(runs.DefinitionError) as caught:
            runs.locate(SimpleNamespace(root=_root()), _args(None))
        self.assertEqual(caught.exception.code, "WF_PATH_INVALID")

    def test_reads_cursor_and_maps_tasks(self):
        root = _root()
        task_id = "2026-" + "a" * 32
        _write(root, "run-1", {"schema_version": 1, "id": "run-1", "workflow_id": "w",
                               "definition": {"digest": "sha256:" + "b" * 64},
                               "cursor": {"step_id": "s1", "task_id": task_id},
                               "step_results": {"s1": {"kind": "satisfied"}},
                               "task_map": {"s1": {"task_id": task_id, "predecessors": [],
                                                   "superseded_ids": []}},
                               "sequence_changes": [], "terminal": None, "paused": False,
                               "ended_at": None})
        directory = os.path.join(root, ".wf", "tasks", task_id)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "task.json"), "w", encoding="utf-8") as handle:
            json.dump({"schema_version": 1, "id": task_id, "status": "archived",
                       "phase": "finish"}, handle)
        payload = runs.locate(SimpleNamespace(root=root), _args("run-1"))
        facts = payload["facts"]
        self.assertEqual(facts["cursor"], {"step_id": "s1", "task_id": task_id})
        self.assertEqual(facts["tasks"], [{"step_id": "s1", "task_id": task_id,
                                          "status": "archived", "phase": "finish",
                                          "unknown": False}])

    def test_task_status_is_read_from_the_task_not_the_run(self):
        root = _root()
        _write(root, "run-2", {"schema_version": 1, "id": "run-2", "workflow_id": "w",
                               "cursor": None, "step_results": {},
                               "task_map": {"s1": {"task_id": "2026-" + "c" * 32}},
                               "terminal": None, "paused": False})
        payload = runs.locate(SimpleNamespace(root=root), _args("run-2"))
        entry = payload["facts"]["tasks"][0]
        self.assertTrue(entry["unknown"], "任务记录不存在时必须标 unknown，而不是给空状态")
        self.assertIsNone(entry["status"])


if __name__ == "__main__":
    unittest.main()
