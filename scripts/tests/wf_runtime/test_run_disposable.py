"""实例终止的处置集合与替代引用（八轮审查 b-1 / a-3）：

- R（受控返工）登记在 `sequence_changes`：只枚举 `task_map` 会漏列它，补进计划又被判"实例外任务"；
- `skip.downstream[].replacement` 的 `from: input` 静态允许，运行期必须真的解析（否则合法定义必死）。
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, runs  # noqa: E402


class _Ctx:
    def __init__(self, root):
        self.root = str(root)


class DisposableTasksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-disposable-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".wf" / "tasks").mkdir(parents=True)

    def _put(self, task_id, status="in_progress"):
        directory = self.root / ".wf" / "tasks" / task_id
        directory.mkdir(parents=True, exist_ok=True)
        records.write_json(str(directory / "task.json"), {"id": task_id, "status": status})

    def test_rework_task_is_part_of_disposal(self):
        self._put("T1")
        self._put("R1")
        run = {"id": "r1", "task_map": {"build": {"task_id": "T1"}},
               "sequence_changes": [{"kind": "rework", "step_id": "build",
                                     "task_id": "R1", "resume_task": "T1"}]}
        items = runs._run_disposable_tasks(_Ctx(self.root), run)
        self.assertEqual([item["task"] for item in items], ["T1", "R1"])
        self.assertEqual([item["source"] for item in items], ["step", "rework"])
        self.assertEqual(items[1]["resume_task"], "T1")

    def test_archived_rework_is_listed_but_not_required(self):
        self._put("T1")
        self._put("R1", "archived")
        run = {"id": "r1", "task_map": {"build": {"task_id": "T1"}},
               "sequence_changes": [{"kind": "rework", "task_id": "R1", "resume_task": "T1"}]}
        items = runs._run_disposable_tasks(_Ctx(self.root), run)
        self.assertEqual([item["archived"] for item in items], [False, True])


class ReplacementFromInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-replacement-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "out").mkdir()

    def test_input_path_is_resolved_at_runtime(self):
        (self.root / "out" / "sub.txt").write_text("x\n", encoding="utf-8")
        ready, detail = runs._replacement_ready(
            _Ctx(self.root), {}, {"from": "input", "name": "substitute"},
            {}, {"substitute": "out/sub.txt"})
        self.assertTrue(ready, detail)

    def test_missing_input_path_is_reported(self):
        ready, detail = runs._replacement_ready(
            _Ctx(self.root), {}, {"from": "input", "name": "substitute"},
            {}, {"substitute": "out/absent.txt"})
        self.assertFalse(ready)
        self.assertIn("absent.txt", detail)

    def test_missing_input_value_is_reported(self):
        ready, detail = runs._replacement_ready(
            _Ctx(self.root), {}, {"from": "input", "name": "substitute"}, {}, {})
        self.assertFalse(ready)
        self.assertIn("not a path value", detail)


if __name__ == "__main__":
    unittest.main()
