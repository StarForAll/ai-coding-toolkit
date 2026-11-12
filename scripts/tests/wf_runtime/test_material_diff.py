"""R2：审查材料物化的唯一实现（`review.materialize_delivery`）。

dogfood 的原题：`_material_diff` 只跑 `git diff [HEAD] -- path`，未跟踪文件两种调用都输出 0 字节，
异常又被吞成 `owned=[]`，最后写成"无工作树差异"。本用例锁四件事：

1. 未跟踪新文件的内容真的出现在片段里；
2. 已暂存与未暂存的改动都出现；
3. 删除给出删除 hunk，二进制给出可见标记；
4. 取片段失败时进 `problems` 并留下 missing 标记，**不再**伪装成"无差异"。

另含报告骨架断言：骨架必须能被 `read_report` 解析出全部 `REPORT_FIELDS`。
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


def _repo():
    root = tempfile.mkdtemp(prefix="wf-material-")
    _run(root, "init", "-q")
    for name, text in (("tracked.txt", "one\n"), ("staged.txt", "old\n"),
                       ("deleted.txt", "bye\n")):
        with open(os.path.join(root, name), "w", encoding="utf-8") as handle:
            handle.write(text)
    with open(os.path.join(root, "blob.bin"), "wb") as handle:
        handle.write(b"\x00\x01\x02binary\n")
    _run(root, "add", ".")
    _run(root, "commit", "-qm", "base")
    return root


class MaterialDiffTest(unittest.TestCase):
    def test_untracked_file_content_is_materialized(self):
        root = _repo()
        with open(os.path.join(root, "new_module.py"), "w", encoding="utf-8") as handle:
            handle.write("def hello():\n    return 'notify'\n")
        material = review.materialize_delivery(root, ["new_module.py"])
        self.assertEqual(material["problems"], [])
        self.assertIn("def hello", material["text"])
        self.assertIn("new_module.py", material["text"])
        self.assertTrue(material["files"][0]["generated"])

    def test_staged_and_unstaged_changes_both_appear(self):
        root = _repo()
        with open(os.path.join(root, "staged.txt"), "w", encoding="utf-8") as handle:
            handle.write("staged line\n")
        _run(root, "add", "staged.txt")
        with open(os.path.join(root, "tracked.txt"), "w", encoding="utf-8") as handle:
            handle.write("unstaged line\n")
        text = review.materialize_delivery(root, ["staged.txt", "tracked.txt"])["text"]
        self.assertIn("staged line", text)
        self.assertIn("unstaged line", text)

    def test_deletion_gives_a_deletion_hunk(self):
        root = _repo()
        os.remove(os.path.join(root, "deleted.txt"))
        material = review.materialize_delivery(root, ["deleted.txt"])
        self.assertEqual(material["problems"], [])
        self.assertIn("bye", material["text"])
        self.assertIn("# ==== deleted deleted.txt ====", material["text"])

    def test_binary_is_marked_not_silently_empty(self):
        root = _repo()
        with open(os.path.join(root, "blob.bin"), "wb") as handle:
            handle.write(b"\x00\x01\x02binary changed\n")
        material = review.materialize_delivery(root, ["blob.bin"])
        self.assertIn("binary:", material["text"])
        self.assertIn("# ==== modified blob.bin ====", material["text"])
        self.assertIn("bytes=", material["files"][0]["note"] or "")
        self.assertIn("digest=sha256:", material["files"][0]["note"] or "")

    def test_failure_is_reported_instead_of_faked_as_no_diff(self):
        root = _repo()
        original = review._git_capture

        def broken(*_args, **_kwargs):
            return None, "boom: git unavailable"

        review._git_capture = broken
        try:
            material = review.materialize_delivery(root, ["tracked.txt"])
        finally:
            review._git_capture = original
        self.assertEqual(len(material["problems"]), 1)
        self.assertIn(review.MATERIAL_MISSING, material["text"])
        self.assertNotIn("无工作树差异", material["text"])

    def test_empty_delivery_set_is_explicit(self):
        material = review.materialize_delivery(_repo(), [])
        self.assertTrue(material["empty"])
        self.assertEqual(material["text"], "")

    def test_report_skeleton_parses_with_all_fields(self):
        skeleton = review.report_skeleton("2026-01-01-abc", 2, {"id": "c1"}, "check-anchor:1")
        self.assertIn("status=in-progress", skeleton)
        payload, problems = review.read_report(skeleton)
        self.assertEqual(problems, [])
        for field in review.REPORT_FIELDS:
            self.assertIn(field, payload)
        self.assertEqual(payload["round"], 2)
        self.assertEqual(payload["check-anchor"], {"check_id": "c1", "check_anchor": "check-anchor:1"})


if __name__ == "__main__":
    unittest.main()


class WriteMaterialsTest(unittest.TestCase):
    """`review.write_materials` 是落盘接线（此前只有生成函数被断言，接线无断言）。"""

    def _ctx(self, root):
        from types import SimpleNamespace

        return SimpleNamespace(root=root)

    def test_writes_diff_and_status_with_untracked_content(self):
        import json

        root = _repo()
        os.makedirs(os.path.join(root, ".wf", "tasks"), exist_ok=True)
        with open(os.path.join(root, "notify.py"), "w", encoding="utf-8") as handle:
            handle.write("def notify():\n    return 'sent'\n")
        task = {"id": "2026-01-01-abc", "phase": "execute",
                "entry_snapshot": {"touch_paths": ["notify.py"]},
                "plan": {"touch_paths": ["notify.py"]}, "baseline_head": None}
        materials = tempfile.mkdtemp(prefix="wf-materials-")
        facts = review.write_materials(self._ctx(root), task, 1, "check-anchor:9", materials)
        with open(os.path.join(materials, "diff.patch"), encoding="utf-8") as handle:
            diff_text = handle.read()
        with open(os.path.join(materials, "status.json"), encoding="utf-8") as handle:
            status = json.load(handle)
        self.assertIn("def notify", diff_text)
        self.assertNotIn("无工作树差异", diff_text)
        self.assertEqual(status["problems"], [])
        self.assertFalse(status["empty"])
        self.assertEqual(status["paths"], ["notify.py"])
        self.assertEqual(facts["material_problem_count"], 0)

    def test_empty_delivery_set_writes_explicit_reason(self):
        root = _repo()
        os.makedirs(os.path.join(root, ".wf", "tasks"), exist_ok=True)
        task = {"id": "2026-01-01-abc", "phase": "execute",
                "entry_snapshot": {"touch_paths": []}, "plan": {"touch_paths": []},
                "baseline_head": None}
        materials = tempfile.mkdtemp(prefix="wf-materials-")
        review.write_materials(self._ctx(root), task, 1, "check-anchor:9", materials)
        with open(os.path.join(materials, "diff.patch"), encoding="utf-8") as handle:
            self.assertIn(review.MATERIAL_EMPTY, handle.read())
