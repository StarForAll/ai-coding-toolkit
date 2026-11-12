"""P2-9：`_apply_debug_inputs` 必须幂等（实现稿 §2.3.11 ④）。

历史状态：同一决定文件重入会把声明/裁定**重复 append** 到 `execution.debug_declarations`，
`counted` 随之翻倍；只有带 `dedupe_refs` 的形态会被后面的全局唯一约束拦住（方向保守但不完整）。

现在以结构化字段作幂等键（`verification_id` + `counted` + `evidence_refs` + `dedupe_refs`，
裁定用 `subject` + `choice` + `evidence_refs`），重入即跳过——**不新增任何字段**。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402

DECL = {"choice": "count", "subject": "debug-declaration:test-run:count=2:evidence=check:C1"}


def _task():
    return {"id": "t1", "execution": {}, "check": {"id": "C1"}, "check_history": []}


class DebugDeclarationIdempotencyTest(unittest.TestCase):
    def test_same_decision_twice_does_not_double_count(self):
        task = _task()
        tasks_mod._apply_debug_inputs(task, [DECL])
        tasks_mod._apply_debug_inputs(task, [DECL])
        declarations = task["execution"]["debug_declarations"]
        self.assertEqual(len(declarations), 1)
        self.assertEqual(declarations[0]["counted"], 2)

    def test_distinct_declarations_are_both_kept(self):
        task = _task()
        tasks_mod._apply_debug_inputs(task, [DECL])
        second = {"choice": "count",
                  "subject": "debug-declaration:other-run:count=1:evidence=check:C1"}
        tasks_mod._apply_debug_inputs(task, [second])
        self.assertEqual(len(task["execution"]["debug_declarations"]), 2)

    def test_ruling_is_idempotent_too(self):
        task = _task()
        ruling = {"choice": "同一问题", "subject": "debug-ruling-test-run-2", "evidence_refs": ["check:C1"]}
        tasks_mod._apply_debug_inputs(task, [ruling])
        tasks_mod._apply_debug_inputs(task, [ruling])
        self.assertEqual(len(task["execution"]["human_decisions"]), 1)

    def test_removing_the_key_reproduces_duplication(self):
        """注入：让幂等键恒不相等（等于旧实现）→ 同一决定文件被累计两次。"""
        task = _task()
        calls = {"n": 0}

        def unique_key(entry):
            calls["n"] += 1
            return f"unique-{calls['n']}"

        with mock.patch.object(tasks_mod, "_debug_idempotency_key", side_effect=unique_key):
            tasks_mod._apply_debug_inputs(task, [DECL])
            tasks_mod._apply_debug_inputs(task, [DECL])
        self.assertEqual(len(task["execution"]["debug_declarations"]), 2)


if __name__ == "__main__":
    unittest.main()
