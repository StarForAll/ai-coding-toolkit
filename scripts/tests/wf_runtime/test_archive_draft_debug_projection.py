"""十六轮后 d-1（盲审）：archive --draft 投影已裁「不同问题」的重复调试倍数。

防的失败：「不同问题」裁定不产生复盘触发事实（复盘只在「同一问题」方向转正），
若 finish 人签前没有它的可见投影，误裁方向对人是不可见的——§11.2 的
「人可在 finish 人签时复核」声明在该方向不成立。投影数据与归档门禁同源
（gates.debug_pending 的 rulings_raw），不落第二份账本。
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import tasks as tasks_mod  # noqa: E402


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=str(root),
                          capture_output=True, text=True, check=False)


class ArchiveDraftDebugProjectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "tests@example.com")
        _git(self.root, "config", "user.name", "tests")
        (self.root / "a.txt").write_text("v1\n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-qm", "init")
        task_dir = self.root / ".wf" / "tasks" / "t-draft"
        task_dir.mkdir(parents=True)
        self.task = {"id": "t-draft", "title": "草稿投影", "status": "in_progress",
                     "phase": "finish", "baseline_head": None,
                     "entry_snapshot": {"touch_paths": []},
                     "plan": {"version": "v1", "complexity": "light"},
                     "execution": {"required_steps": [], "actions": [],
                                   "human_decisions": [
                                       {"subject": "debug-ruling-v1-1", "choice": "不同问题",
                                        "reason": "根因不同", "evidence_refs": ["check:c1"]},
                                       {"subject": "debug-ruling-v2-1", "choice": "同一问题",
                                        "reason": "同根因", "evidence_refs": ["check:c2"]},
                                   ],
                                   "debug_declarations": []}}
        (task_dir / "task.json").write_text(json.dumps(self.task), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _ctx(self):
        import types

        return types.SimpleNamespace(root=str(self.root), debug_threshold=lambda: 3)

    def test_draft_projects_ruled_different_multiples(self):
        draft = tasks_mod._archive_draft(self._ctx(), "t-draft")
        ruled = draft.get("debug_ruled_different")
        self.assertEqual([item["subject"] for item in ruled], ["debug-ruling-v1-1"])
        self.assertEqual(ruled[0]["choice"], "不同问题")

    def test_draft_without_rulings_projects_empty_list(self):
        task_dir = self.root / ".wf" / "tasks" / "t-draft"
        task = dict(self.task)
        task["execution"] = {"required_steps": [], "actions": [],
                             "human_decisions": [], "debug_declarations": []}
        (task_dir / "task.json").write_text(json.dumps(task), encoding="utf-8")
        draft = tasks_mod._archive_draft(self._ctx(), "t-draft")
        self.assertEqual(draft.get("debug_ruled_different"), [])


if __name__ == "__main__":
    unittest.main()
