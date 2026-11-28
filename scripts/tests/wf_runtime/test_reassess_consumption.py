"""核销"全或不动"（§25）：返工集合归档后仍有残留差异 → 不核销并报告；无残留 → 核销。

区分力：删掉 `cmd_task_reassess` 的 `still_dirty` 判定（改成无条件核销），第一例即红。
"""

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks  # noqa: E402

TASK = "2026-" + "a" * 32
REWORK = "2026-" + "b" * 32


class ReassessConsumptionTest(unittest.TestCase):
    def _run(self, dirty):
        root = tempfile.mkdtemp()
        (Path(root) / ".wf").mkdir(exist_ok=True)
        task = {"id": TASK, "status": "in_progress", "phase": "execute", "suspended": True,
                "handoff": {"wip": {"paths": [{"path": "pkg/x.py", "digest": "sha256:x"}],
                                    "resolved": None}},
                "execution": {"actions": []}}
        holding = [task]

        def _start(ctx, path, t, kind, holder, inputs, steps):
            return t, {"id": "a1", "kind": kind, "state": "open"}

        def _finish(ctx, path, t, kind, holder, inputs, action, evidence_refs=None):
            return t, {"writer": "s-k"}

        args = mock.Mock()
        args.value = lambda name: {"--task": TASK}.get(name)
        ctx = mock.Mock(root=root)
        ctx.key = lambda required=True: "s-k"
        with mock.patch.object(tasks.session_mod, "load_binding",
                               return_value={"object": {"kind": "task", "id": TASK}}), \
                mock.patch.object(tasks, "reassess_write_right", return_value=(True, {})), \
                mock.patch.object(tasks, "bind_task_for_write", return_value=None), \
                mock.patch("wflib.lock.acquire", return_value=contextlib.nullcontext()), \
                mock.patch.object(tasks, "require_held_for", return_value=({"holder": {}}, {"holder": {}})), \
                mock.patch.object(tasks, "_require_task_dir", return_value=root), \
                mock.patch.object(tasks.records, "load_json", return_value=task), \
                mock.patch.object(tasks, "reassess_problems", return_value=[]), \
                mock.patch.object(tasks, "rework_set",
                                  return_value=[{"id": REWORK, "status": "archived"}]), \
                mock.patch.object(tasks.scope, "uncommitted_paths", return_value=list(dirty)), \
                mock.patch.object(tasks, "iter_tasks", return_value=[]), \
                mock.patch.object(tasks, "_start_task_action", side_effect=_start), \
                mock.patch.object(tasks, "_finish_task_action", side_effect=_finish):
            result = tasks.cmd_task_reassess(ctx, args)
        payload = getattr(result, "payload", None)
        if payload is None:
            payload = result if isinstance(result, dict) else {}
        facts = payload.get("facts") or {}
        return facts, task

    def test_residual_dirty_keeps_registration(self):
        facts, task = self._run(["pkg/x.py"])
        self.assertEqual(facts.get("unresolved_after_rework"), ["pkg/x.py"])
        self.assertIsNone(task["handoff"]["wip"]["resolved"], "残留未处置时不得核销")

    def test_clean_tree_consumes_registration(self):
        facts, task = self._run([])
        self.assertEqual(facts.get("unresolved_after_rework"), [])
        self.assertEqual(task["handoff"]["wip"]["resolved"].get("choice"), "rework-completed")


if __name__ == "__main__":
    unittest.main()
