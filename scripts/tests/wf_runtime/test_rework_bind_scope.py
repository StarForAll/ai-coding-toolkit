"""§48（2026-11-28 人裁）：在途实例的受控返工 R 不允许 task 绑定，只能绑实例。

区分力：删掉 `_eligible_task_bind` 里的谱系拦截分支，本用例即变红（binding_state 返回
BINDING_NONE 会直接放行）。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, runs  # noqa: E402

RUN = "2026-" + "f" * 32
REWORK = "2026-" + "a" * 32


class ReworkBindScopeTest(unittest.TestCase):
    def test_task_bind_of_rework_member_is_rejected(self):
        task = {"id": REWORK, "status": "in_progress"}
        run = {"id": RUN, "terminal": None,
               "sequence_changes": [{"task_id": REWORK, "resume_task": None}]}
        ctx = mock.Mock(root="/tmp/x")
        with mock.patch.object(runs, "binding_state",
                               return_value={"state": runs.BINDING_NONE}), \
                mock.patch.object(runs, "iter_runs", return_value=[(RUN, run)]):
            with self.assertRaises(cli.CliError) as caught:
                cli._eligible_task_bind(ctx, task)
        self.assertEqual(caught.exception.code, "WF_BINDING_MISMATCH")
        self.assertEqual(caught.exception.facts.get("run_id"), RUN)

    def test_ordinary_task_still_binds(self):
        task = {"id": REWORK, "status": "in_progress"}
        ctx = mock.Mock(root="/tmp/x")
        with mock.patch.object(runs, "binding_state",
                               return_value={"state": runs.BINDING_NONE}), \
                mock.patch.object(runs, "iter_runs", return_value=[]):
            self.assertIsNone(cli._eligible_task_bind(ctx, task))


if __name__ == "__main__":
    unittest.main()
