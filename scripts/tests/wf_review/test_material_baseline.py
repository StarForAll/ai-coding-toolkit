"""D7：审查材料的差异源是**任务基线**，不只是 HEAD。

防的失败（dogfood）：任务中途提交后再接续，已跟踪文件只与 HEAD 比 → 材料里写
"no textual change (metadata-only?)"，reviewer 看不到本任务实际交付的变化；已提交删除
只剩一句标注。

断言：
1. 任务中途提交的修改与删除都出现在片段里（相对任务基线）；
2. 同一份改动在"只比 HEAD"时确实为空——证明差异源真的换了，而不是文案变化；
3. 未跟踪新增仍走 `--no-index`；
4. 基线不可用 → `diff_base_problem` 如实给出（不静默、不算生成失败）。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import review  # noqa: E402


def _run(root, *args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
                   cwd=root, check=True, capture_output=True)


def _head(root):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


def _repo():
    root = tempfile.mkdtemp(prefix="wf-material-base-")
    _run(root, "init", "-q")
    for name, text in (("modified.txt", "old\n"), ("removed.txt", "gone\n")):
        with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
            handle.write(text)
    _run(root, "add", ".")
    _run(root, "commit", "-qm", "base")
    return root


class MaterialBaselineTest(unittest.TestCase):
    def setUp(self):
        self.root = _repo()
        self.baseline = _head(self.root)
        # 任务中途提交：改一个、删一个
        with open(os.path.join(self.root, "modified.txt"), "w", encoding="utf-8") as handle:
            handle.write("new\n")
        _run(self.root, "rm", "-q", "removed.txt")
        _run(self.root, "add", "-A")
        _run(self.root, "commit", "-qm", "wf: task change")
        self.head = _head(self.root)

    def test_committed_changes_appear_against_the_task_baseline(self):
        material = review.materialize_delivery(
            self.root, ["modified.txt", "removed.txt"], base=self.baseline)
        self.assertEqual(material["problems"], [])
        self.assertIn("+new", material["text"])
        self.assertIn("-gone", material["text"])
        self.assertNotIn("no change between", material["text"])

    def test_head_only_comparison_would_be_empty(self):
        material = review.materialize_delivery(self.root, ["modified.txt"], base=self.head)
        self.assertIn("no change between", material["text"])

    def test_untracked_file_still_uses_no_index(self):
        with open(os.path.join(self.root, "added.txt"), "w", encoding="utf-8") as handle:
            handle.write("brand new\n")
        material = review.materialize_delivery(
            self.root, ["added.txt"], base=self.baseline)
        self.assertIn("brand new", material["text"])
        self.assertEqual(material["files"][0]["kind"], "new (untracked)")

    def test_unusable_baseline_is_reported_as_a_fact(self):
        material = review.materialize_delivery(
            self.root, ["modified.txt"], base="0" * 40)
        self.assertEqual(material["diff_base"], "HEAD")
        self.assertIn("task baseline", material["diff_base_problem"])
        self.assertIn("no change between", material["text"])


if __name__ == "__main__":
    unittest.main()
