"""stop 的归属门禁（§21）：keep/commit 的 subject 必须落在本任务 e 桶，d/c 档一律拒绝。

区分力：删掉 `stop_work` 的 e 桶检查，本用例不再抛 `WF_WORKSPACE_UNRESOLVED` 即红。
"""

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import cli, tasks  # noqa: E402

TASK = "2026-" + "a" * 32


class StopOwnershipTest(unittest.TestCase):
    def _task(self):
        return {"id": TASK, "status": "in_progress", "phase": "execute",
                "handoff": {}, "execution": {"actions": []}, "plan": {}}

    def _go(self, choice, subject, e_paths):
        root = tempfile.mkdtemp()
        (Path(root) / ".wf").mkdir(exist_ok=True)
        ctx = mock.Mock(root=root)
        ctx.key = lambda required=True: "s-k"
        decision = {"source": "human:x", "at": "t", "subject": subject,
                    "object_digest": "", "choice": choice, "reason": "r"}
        decisions = [decision]
        if choice == "commit":
            decisions.append({"source": "human:x", "at": "t", "subject": subject,
                              "object_digest": "", "choice": "commit", "reason": "grant"})
        classified = {"buckets": {"a": [], "b": [], "c": [], "d": [], "e": e_paths, "f": []},
                      "candidates": list(e_paths), "touch_paths": ["pkg/**"]}
        with mock.patch.object(tasks.session_mod, "load_binding",
                               return_value={"object": {"kind": "task", "id": TASK}}), \
                mock.patch("wflib.lock.acquire", return_value=contextlib.nullcontext()), \
                mock.patch.object(tasks, "require_held_for",
                                  return_value=({"holder": {}}, {"holder": {}})), \
                mock.patch.object(tasks, "task_dir", return_value=root), \
                mock.patch.object(tasks.records, "load_json", return_value=self._task()), \
                mock.patch.object(tasks, "approved_touch_paths", return_value=["pkg/**"]), \
                mock.patch.object(tasks.scope, "classify_candidates", return_value=classified), \
                mock.patch.object(tasks.scope, "uncommitted_paths", return_value=list(e_paths)), \
                mock.patch.object(tasks.scope, "git", return_value=(0, "", "")), \
                mock.patch.object(tasks.fingerprint, "item",
                                  side_effect=lambda root, path: {"path": path, "digest": "sha256:x",
                                                                  "exists": True, "kind": "file"}):
            try:
                tasks.stop_work(ctx, decisions, choice)
            except tasks.TaskError as exc:
                return exc.code, exc.facts
        return None, None

    def test_keep_rejects_foreign_path(self):
        code, facts = self._go("keep", ["pkg/own.py", "pkg/theirs.py"], ["pkg/own.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("pkg/theirs.py", facts.get("foreign") or [])

    def test_commit_rejects_foreign_path(self):
        code, facts = self._go("commit", ["pkg/own.py", "pkg/theirs.py"], ["pkg/own.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("pkg/theirs.py", facts.get("foreign") or [])


if __name__ == "__main__":
    unittest.main()
