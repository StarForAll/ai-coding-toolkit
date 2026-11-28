"""实例首个 task 步骤的自举校验（设计稿 §3.3）。

全新项目无活基线/配置时，定义的首个 task 步骤必须是 initialize/bootstrap；
否则实例会建出普通任务，而 task-start 的自举前置拒绝且出口在已绑定实例会话不可执行。
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


def _doc(kind):
    return {"format_version": 1, "workflow_id": "wf-a", "content_version": 1,
            "purpose": "x", "applicability": "x", "inputs": {},
            "steps": [{"id": "s1", "type": "task", "task_kind": kind, "title": "t"}],
            "completion": ["done"]}


class BootstrapFirstStepTest(unittest.TestCase):
    def _problems(self, kind, ready):
        with tempfile.TemporaryDirectory() as root:
            if ready:
                os.makedirs(os.path.join(root, ".wf"), exist_ok=True)
                with open(os.path.join(root, ".wf", "project-config.json"), "w", encoding="utf-8") as handle:
                    json.dump({"schema_version": 1}, handle)
                with open(os.path.join(root, ".wf", "baseline.md"), "w", encoding="utf-8") as handle:
                    handle.write("# 项目基线\n")
            return [item for item in runs.validate_definition(_doc(kind), root, workflow_id="wf-a")
                    if "first task step must be initialize" in str(item.get("reason"))]

    def test_new_project_ordinary_first_step_rejected(self):
        self.assertTrue(self._problems("ordinary", ready=False))

    def test_new_project_initialize_first_step_accepted(self):
        self.assertEqual(self._problems("initialize", ready=False), [])

    def test_existing_project_ordinary_first_step_allowed(self):
        self.assertEqual(self._problems("ordinary", ready=True), [])


if __name__ == "__main__":
    unittest.main()
