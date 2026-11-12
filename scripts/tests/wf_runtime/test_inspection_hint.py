"""P2-5：归档后的巡检提示必须走项目配置、只数**正常归档**（实现稿 §2.3.11 未做项）。

历史状态：`_inspection_hint` 硬编码 `every = 10`，并且数的是 `.wf/tasks/archive/**` 下的
**全部** `task.json`（含异常归档与不可解析记录）；而同一发行里 `inspect` 的 `inspection.due`
已按机制稿 §8.5 算对了（正常归档、`archived_at` 可排序、配置键 `inspection_every_tasks`）。
两处算法不同 → 「提示说到点了、巡检说没到」这种自相矛盾。

现在到点判定只有一处实现（`_governance_summary` 的 `inspection`），本文件钉住三条事实：
配置生效、异常归档不计、记录不完整时只报 unknown（不谎报 due）。
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

from wflib import tasks as tasks_mod  # noqa: E402


def _archived(root, task_id, terminal, archived_at="2026-11-01T00:00:00.000000Z"):
    directory = os.path.join(root, ".wf", "tasks", "archive", "2026-11", f"{task_id}-t")
    os.makedirs(directory, exist_ok=True)
    record = {"schema_version": 1, "id": task_id, "status": "archived", "phase": "finish",
              "title": "t", "terminal": terminal, "archived_at": archived_at, "curation": []}
    with open(os.path.join(directory, "task.json"), "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False)


def _project(root, every=2):
    os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
    config = {"schema_version": 1, "inspection_every_tasks": every, "spec_reclaim_tasks": 5,
              "python_executable": "/usr/bin/python3"}
    with open(os.path.join(root, ".wf", "project-config.json"), "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False)


class InspectionHintTest(unittest.TestCase):
    def test_config_value_and_normal_archives_decide_due(self):
        """2 个正常 + 3 个异常，`inspection_every_tasks=2` → 到点（硬编码 10 会给出 False）。"""
        root = tempfile.mkdtemp(prefix="wf-hint-")
        _project(root, every=2)
        for index in range(2):
            _archived(root, "2026-" + "a" * 31 + str(index), "normal")
        for index in range(3):
            _archived(root, "2026-" + "b" * 31 + str(index), "abnormal")
        facts = tasks_mod._inspection_hint(SimpleNamespace(root=root))
        self.assertTrue(facts["due"])
        self.assertEqual(facts["archived"], 2)
        self.assertEqual(facts["abnormal"], 3)
        self.assertEqual(facts["every"], 2)

    def test_abnormal_only_does_not_trigger(self):
        root = tempfile.mkdtemp(prefix="wf-hint-")
        _project(root, every=2)
        for index in range(4):
            _archived(root, "2026-" + "c" * 31 + str(index), "abnormal")
        facts = tasks_mod._inspection_hint(SimpleNamespace(root=root))
        self.assertFalse(facts["due"])
        self.assertEqual(facts["archived"], 0)

    def test_invalid_config_is_unknown_not_false(self):
        root = tempfile.mkdtemp(prefix="wf-hint-")
        _project(root, every="ten")
        _archived(root, "2026-" + "d" * 31 + "0", "normal")
        facts = tasks_mod._inspection_hint(SimpleNamespace(root=root))
        self.assertIsNone(facts["due"])
        self.assertIn("unknown", facts["reason"])


if __name__ == "__main__":
    unittest.main()
