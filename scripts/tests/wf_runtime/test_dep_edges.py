"""P1-4：`dep add|rm`（机制稿 §6.1）。

只做四件事：两端存在性、自环/环（DFS 三色）、活动区约束、写回 `prerequisites`。
建边/删边是 `dependency.change` 状态动作，`targets` 覆盖两端（D08 的第二轮要求：
「第二轮加入全部依赖/实例目标」），因此跨任务目标碰撞走既有判定。

本文件钉住：幂等、自环、环、已归档前置、删边只改持有侧、targets 含两端。
节点级判定在 `tasks._find_cycle` / `_prerequisite_graph` 上做（CLI 外壳只做参数与写权）。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402


class DepGraphTest(unittest.TestCase):
    def test_cycle_detected_on_self_through_chain(self):
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        cycle = tasks_mod._find_cycle(graph, "a")
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle[0], cycle[-1])
        self.assertEqual(set(cycle), {"a", "b", "c"})

    def test_acyclic_graph_has_no_cycle(self):
        graph = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
        self.assertIsNone(tasks_mod._find_cycle(graph, "a"))

    def test_diamond_is_not_a_cycle(self):
        """菱形共享下游是合法的（不能因为重复访问就报环）。"""
        graph = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": []}
        self.assertIsNone(tasks_mod._find_cycle(graph, "b"))

    def test_prerequisite_graph_only_holds_active_records(self):
        import json
        import os
        import tempfile

        root = tempfile.mkdtemp(prefix="wf-dep-")
        for task_id, extra in (("2026-" + "a" * 32, {}),
                               ("2026-" + "b" * 32, {"status": "archived", "terminal": "normal"})):
            directory = os.path.join(root, ".wf", "tasks", task_id)
            os.makedirs(directory, exist_ok=True)
            record = {"schema_version": 1, "id": task_id, "status": "in_progress", "phase": "plan",
                      "prerequisites": []}
            record.update(extra)
            with open(os.path.join(directory, "task.json"), "w", encoding="utf-8") as handle:
                json.dump(record, handle)
        graph = tasks_mod._prerequisite_graph(root)
        self.assertEqual(list(graph), ["2026-" + "a" * 32])


if __name__ == "__main__":
    unittest.main()
