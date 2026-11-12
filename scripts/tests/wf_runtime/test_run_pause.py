"""P1-2：`run pause` 的参数契约（机制稿 §7.3、§1.5）。

端到端（写 `paused`/`paused_reason`、暂停当前任务、advance 被挡）走
`repro/run-pause-and-advance.py`；这里只钉住「缺参必须拒绝」这类纯契约。

机制稿 §7.3 的硬要求是「实例暂停须保存当前任务的暂停或等待原因及当前步骤，
**不能只移动游标绕过任务门禁**」——所以 pause 不动 `cursor`，只写 `paused`/`paused_reason`
并把当前任务标 `paused`（清执行候选）。

解除路径**不在这里**：机制稿 §2.2 只为任务定义「暂停/恢复」，实例的解除没有出处
（`run` 的子动作表也没有 resume）。当前 paused 实例的出口是 `run terminate`。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import runs  # noqa: E402


def _args(run_id, reason="人要先处理别的事"):
    def value(name, default=None):
        return {"--run": run_id, "--reason": reason}.get(name, default)
    return type("A", (), {"value": staticmethod(value)})()


class RunPauseContractTest(unittest.TestCase):
    def test_requires_reason(self):
        with self.assertRaises(runs.DefinitionError) as caught:
            runs.pause(object(), _args("r1", reason="  "))
        self.assertEqual(caught.exception.code, "WF_PATH_INVALID")

    def test_requires_run_id(self):
        with self.assertRaises(runs.DefinitionError) as caught:
            runs.pause(object(), _args(None))
        self.assertEqual(caught.exception.code, "WF_PATH_INVALID")

if __name__ == "__main__":
    unittest.main()
