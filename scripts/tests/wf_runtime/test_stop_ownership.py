"""stop 的归属门禁与空 subject 守卫（§21；2026-11-28 外审 A2-2）。

区分力：
- 空 subject + 只有自身控制记录（b 桶）时不再被"工作区有未提交差异"误拒；
- 空 subject + 本任务业务 WIP（e 桶）仍拒绝；
- keep/commit 接受本任务 a∪e（a 是 baseline-apply 等回执路径），仍拒绝他人路径。
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
CONTROL = f".wf/tasks/{TASK}/task.json"


class StopOwnershipTest(unittest.TestCase):
    def _task(self):
        return {"id": TASK, "status": "in_progress", "phase": "execute",
                "handoff": {}, "execution": {"actions": []}, "plan": {}}

    def _go(self, choice, subject, e_paths=None, *, a_paths=None, b_paths=None,
            uncommitted=None, touch=None, leftover_after_commit=None):
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
        classified = {"buckets": {"a": list(a_paths or []), "b": list(b_paths or []),
                                  "c": [], "d": [], "e": list(e_paths or []), "f": []},
                      "candidates": list(e_paths or []) + list(a_paths or []),
                      "touch_paths": list(touch or ["pkg/**"])}
        task = self._task()

        def start(ctx_, directory, current, kind, holder, inputs, steps):
            current["action"] = {"id": "a1", "state": "doing"}
            return current, {"id": "a1"}

        def finish(ctx_, directory, current, kind, holder, inputs, action, **kwargs):
            current["action"] = {"id": "a1", "state": "done"}
            return current, {"ok": True}

        dirty_calls = [list(uncommitted if uncommitted is not None else (e_paths or [])),
                       list(leftover_after_commit if leftover_after_commit is not None else [])]

        def dirty(_root):
            return dirty_calls.pop(0) if dirty_calls else []

        with mock.patch.object(tasks.session_mod, "load_binding",
                               return_value={"object": {"kind": "task", "id": TASK}}), \
                mock.patch("wflib.lock.acquire", return_value=contextlib.nullcontext()), \
                mock.patch.object(tasks, "require_held_for",
                                  return_value=({"holder": {}}, {"holder": {}})), \
                mock.patch.object(tasks, "task_dir", return_value=root), \
                mock.patch.object(tasks.records, "load_json", return_value=task), \
                mock.patch.object(tasks, "approved_touch_paths", return_value=list(touch or ["pkg/**"])), \
                mock.patch.object(tasks, "task_receipts", return_value=[]), \
                mock.patch.object(tasks.scope, "classify_candidates", return_value=classified), \
                mock.patch.object(tasks.scope, "uncommitted_paths", side_effect=dirty), \
                mock.patch.object(tasks.scope, "git", return_value=(0, "", "")), \
                mock.patch.object(tasks, "_commit_gate_problems", return_value=None), \
                mock.patch.object(tasks, "_commit_paths", return_value={"committed": True}), \
                mock.patch.object(tasks, "_start_task_action", side_effect=start), \
                mock.patch.object(tasks, "_finish_task_action", side_effect=finish), \
                mock.patch.object(tasks.writer_mod, "release", return_value={}), \
                mock.patch.object(tasks.writer_mod, "save", return_value=None), \
                mock.patch.object(tasks.fingerprint, "item",
                                  side_effect=lambda root_, path: {"path": path, "digest": "sha256:x",
                                                                  "exists": True, "kind": "file"}):
            try:
                tasks.stop_work(ctx, decisions, choice)
            except tasks.TaskError as exc:
                return exc.code, exc.facts
        return None, None

    def test_keep_rejects_foreign_path(self):
        code, facts = self._go("keep", "pkg/own.py,pkg/theirs.py", ["pkg/own.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("pkg/theirs.py", facts.get("foreign") or [])

    def test_commit_rejects_foreign_path(self):
        code, facts = self._go("commit", "pkg/own.py,pkg/theirs.py", ["pkg/own.py"])
        self.assertEqual(code, "WF_WORKSPACE_UNRESOLVED")
        self.assertIn("pkg/theirs.py", facts.get("foreign") or [])

    def test_empty_subject_with_only_control_records_is_allowed(self):
        code, facts = self._go("keep", "", [], b_paths=[CONTROL], uncommitted=[CONTROL])
        self.assertIsNone(code)

    def test_empty_subject_with_business_wip_is_rejected(self):
        code, facts = self._go("keep", "", ["pkg/a.py"], uncommitted=["pkg/a.py"])
        self.assertEqual(code, "WF_SEMANTIC_DECISION")
        self.assertIn("pkg/a.py", facts["unlisted"])

    def test_keep_accepts_receipt_bucket_path(self):
        code, facts = self._go("keep", ".wf/baseline.md", [], a_paths=[".wf/baseline.md"],
                               uncommitted=[".wf/baseline.md"],
                               touch=["pkg/**", ".wf/baseline.md"])
        self.assertIsNone(code)

    def test_commit_accepts_receipt_bucket_path(self):
        code, facts = self._go("commit", ".wf/baseline.md", [], a_paths=[".wf/baseline.md"],
                               uncommitted=[".wf/baseline.md"],
                               touch=["pkg/**", ".wf/baseline.md"],
                               leftover_after_commit=[])
        self.assertIsNone(code)


if __name__ == "__main__":
    unittest.main()
