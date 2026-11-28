"""实例暂停后释放写权：未登记的当前任务 WIP 不得因释放而丢失（2026-11-28 外审 A1-4）。

区分力：删掉 `_ensure_run_releasable` 的未登记 WIP 核对，本用例不再抛
`WF_WORKSPACE_UNRESOLVED` 即红。
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, runs, scope, tasks  # noqa: E402

RUN = {"paused": True, "terminal": None, "cursor": {"task_id": "T1"}}


def _task(terminal=None):
    return {"id": "T1", "status": "in_progress", "phase": "execute", "terminal": terminal,
            "handoff": {}, "plan": {"touch_paths": ["src/**"]}, "execution": {}}


def _classified(e=None, a=None):
    return {"buckets": {key: list(value or []) for key, value in
                        {"a": a, "b": [], "c": [], "d": [], "e": e, "f": []}.items()},
            "candidates": [], "touch_paths": ["src/**"]}


class RunReleaseWipTest(unittest.TestCase):
    def _call(self, *, task=None, dirty=None, e=None, a=None, retained=None):
        ctx = SimpleNamespace(root="/tmp/x")
        with mock.patch.object(runs, "load_run", return_value=RUN), \
                mock.patch.object(runs, "_run_persist_pending", return_value=False), \
                mock.patch.object(tasks, "load_task", return_value=task or _task()), \
                mock.patch.object(tasks, "wip_paths", return_value=list(retained or [])), \
                mock.patch.object(tasks, "task_receipts", return_value=[]), \
                mock.patch.object(scope, "classify_candidates",
                                  return_value=_classified(e=e, a=a)), \
                mock.patch.object(scope, "uncommitted_paths", return_value=list(dirty or [])):
            try:
                cli._ensure_run_releasable(ctx, "r1")
            except cli.CliError as exc:
                return exc.code, exc.facts
        return None, None

    def test_unregistered_work_path_blocks_release(self):
        code, facts = self._call(dirty=["src/a.py"], e=["src/a.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("src/a.py", facts["paths"])
        self.assertTrue(any("保持写权" in item for item in facts["exits"]))

    def test_unregistered_receipt_path_blocks_release(self):
        code, facts = self._call(dirty=[".wf/baseline.md"], a=[".wf/baseline.md"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn(".wf/baseline.md", facts["paths"])

    def test_clean_workspace_still_releases(self):
        code, facts = self._call(dirty=[], e=[])
        self.assertIsNone(code)
        self.assertIsNone(facts)

    def test_terminal_task_skips_unregistered_check(self):
        code, facts = self._call(task=_task("normal"), dirty=["src/a.py"], e=["src/a.py"])
        self.assertIsNone(code)

    def test_registered_wip_still_blocks_when_dirty(self):
        code, facts = self._call(dirty=["src/a.py"], retained=["src/a.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("undisposed WIP", facts["reason"])


if __name__ == "__main__":
    unittest.main()