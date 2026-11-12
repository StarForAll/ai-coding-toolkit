"""P2-1：`d` 档（归属语义存疑）必须可达并被 Check 消费（机制稿 §3.5 d）。

历史状态：`classify_candidates` 的 `owned = 归属证据 ∪ 命中批准面`，而候选集＝未提交 ∪ 归属，
于是 `¬owned ∧ ¬uncommitted` 恒假——**d 档恒空**，「命中批准面但归属存疑」被静默归进 e 档放行。
机制稿 §3.5「首轮实现覆盖」把这一档留给第二轮：引入「已提交但归属不可解析」的判定。

现在的判据（只此一处）：路径命中批准触碰面、却被**另一个任务**显式登记为未处置 WIP →
`d`（`WF_SCOPE_UNRESOLVED` 交人裁决），不再按宽 glob 命中算成本任务范围。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import check as check_mod  # noqa: E402
from wflib import scope as scope_mod  # noqa: E402


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _repo_with_dirty_file(relative="pkg/a.py"):
    root = tempfile.mkdtemp(prefix="wf-scope-d-")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    os.makedirs(os.path.join(root, "pkg"), exist_ok=True)
    path = os.path.join(root, relative)
    open(path, "w", encoding="utf-8").write("base\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    open(path, "w", encoding="utf-8").write("changed\n")
    return root


def _task(task_id="2026-" + "a" * 32, touch=("pkg/**",)):
    return {
        "id": task_id,
        "status": "in_progress",
        "phase": "execute",
        "baseline_head": "deadbeef",
        "entry_snapshot": {"baseline_head": "deadbeef", "touch_paths": list(touch)},
        "plan": {"touch_paths": list(touch)},
    }


class ScopeDBucketTest(unittest.TestCase):
    def test_plain_dirty_path_in_scope_is_e(self):
        """没有他任务争抢时，未提交且命中批准面仍是 e（设计稿 §4.2 的既有语义）。"""
        root = _repo_with_dirty_file()
        classified = scope_mod.classify_candidates(root, _task())
        self.assertEqual(classified["buckets"]["d"], [])
        self.assertEqual(classified["buckets"]["e"], ["pkg/a.py"])
        self.assertEqual(classified["conflicts"], [])

    def test_path_claimed_by_another_task_lands_in_d(self):
        root = _repo_with_dirty_file()
        other = _task("2026-" + "b" * 32, touch=("other/**",))
        other["handoff"] = {"wip": {"paths": [{"path": "pkg/a.py"}], "resolved": None}}
        with mock.patch.object(scope_mod, "_iter_task_records", return_value=[(None, other)]):
            classified = scope_mod.classify_candidates(root, _task())
        self.assertEqual(classified["buckets"]["d"], ["pkg/a.py"])
        self.assertEqual(classified["buckets"]["e"], [])
        self.assertEqual(classified["conflicts"], [{"path": "pkg/a.py", "claimed_by": other["id"]}])

    def test_check_reports_scope_unresolved_for_d(self):
        """消费端：d 非空即 `WF_SCOPE_UNRESOLVED`，并同时给出争抢双方。"""
        classified = {"buckets": {"a": [], "b": [], "c": [], "d": ["pkg/a.py"], "e": [], "f": []},
                      "candidates": ["pkg/a.py"], "touch_paths": ["pkg/**"],
                      "entry_snapshot": {}, "vendor_dirty": [],
                      "conflicts": [{"path": "pkg/a.py", "claimed_by": "other"}]}
        with mock.patch.object(check_mod, "_task_dir", return_value="/tmp/x"), \
                mock.patch.object(check_mod, "_receipts", return_value=[]), \
                mock.patch.object(check_mod.scope, "classify_candidates", return_value=classified), \
                mock.patch.object(check_mod.scope, "external_changes", return_value=({}, [])):
            with self.assertRaises(check_mod.CheckError) as caught:
                check_mod.run_check(mock.Mock(root="/tmp/x"), _task(), [], None)
        self.assertEqual(caught.exception.code, "WF_SCOPE_UNRESOLVED")
        self.assertEqual(caught.exception.facts["ambiguous_ownership"], ["pkg/a.py"])
        self.assertEqual(caught.exception.facts["cross_task_claims"],
                         [{"path": "pkg/a.py", "claimed_by": "other"}])


if __name__ == "__main__":
    unittest.main()
