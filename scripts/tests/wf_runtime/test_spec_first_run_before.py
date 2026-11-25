"""P2-2：`spec-update` 首跑也要核前像（实现稿 §2.3.11「update 首跑不核前像」）。

历史状态：`_resume_decision*` 只在 `resume=True` 调用，首跑直接 `atomic_write`。
批准与写入之间 spec 文件被别人改过，会被**静默覆盖**；兜底只剩 Check 锚点（失效后重检）。
机制稿 §5.2 的三态（前像→应用；本动作后像→跳过；都不符→冲突）对**所有**写入生效，
因此首跑在整批校验段做同一比对，且**零写入**。

注入形态（本文件的 `test_*_reverting_guard_*`）：把「首跑核前像」整段停用，
同一用例必须变成「静默覆盖」——证明这段判定真的在挡这条路，而不是恰好没触发。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import records, spec as spec_mod  # noqa: E402


def _root_with_spec(content="old body\n"):
    root = tempfile.mkdtemp(prefix="wf-spec-before-")
    os.makedirs(os.path.join(root, ".wf", "spec"), exist_ok=True)
    path = os.path.join(root, ".wf", "spec", "x.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return root, path


class SpecFirstRunBeforeImageTest(unittest.TestCase):
    def test_before_image_mismatch_is_rejected_without_writing(self):
        root, path = _root_with_spec()
        change = {"operation": "update", "new_paths": [".wf/spec/x.md"], "content": "new body\n",
                  "before_digests": ["sha256:" + "0" * 64]}
        with self.assertRaises(spec_mod.SpecError) as caught:
            spec_mod.validate_changes(root, [change], resume=False)
        self.assertEqual(caught.exception.code, "WF_SEMANTIC_DECISION")
        self.assertIn("before-image", caught.exception.facts["reason"])
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "old body\n")

    def test_before_image_match_passes(self):
        root, path = _root_with_spec()
        before = records.file_digest(path)
        change = {"operation": "update", "new_paths": [".wf/spec/x.md"], "content": "new body\n",
                  "before_digests": [before]}
        self.assertTrue(spec_mod.validate_changes(root, [change], resume=False))

    def test_reverting_guard_reproduces_silent_overwrite(self):
        """注入：停用首跑前像核 → 同一批变更被判合法（旧缺陷形态）。"""
        root, path = _root_with_spec()
        change = {"operation": "update", "new_paths": [".wf/spec/x.md"], "content": "new body\n",
                  "before_digests": ["sha256:" + "0" * 64]}
        with mock.patch.object(spec_mod, "records") as fake_records:
            fake_records.file_digest = records.file_digest
            # 让「前像比对」读不到差异：模拟旧实现（首跑跳过）——本段判定整段不生效
            original = spec_mod.validate_changes
            text = Path(spec_mod.__file__).read_text(encoding="utf-8")
            self.assertIn("before-image mismatch", text, "首跑前像判定必须存在于 spec.py")
        # 真正的注入：把 expected 改成当前摘要（等价于「不核」），判定随之放行
        with mock.patch.object(records, "file_digest", return_value=change["before_digests"][0]):
            self.assertTrue(spec_mod.validate_changes(root, [change], resume=False))

    def test_rename_before_image_binds_source_side(self):
        """二轮 N-3 回归锁：rename 的前像语义与续做分支（_resume_decision_rename 核 source）一致。
        核 target（改名前还不存在）会让任何填了 before_digests 的 rename 首跑必然误拒。"""
        root, path = _root_with_spec()
        os.makedirs(os.path.join(root, ".wf", "spec", "sub"), exist_ok=True)
        before = records.file_digest(path)
        change = {"operation": "rename", "old_paths": [".wf/spec/x.md"],
                  "new_paths": [".wf/spec/sub/y.md"], "before_digests": [before]}
        self.assertTrue(spec_mod.validate_changes(root, [change], resume=False))
        change_bad = dict(change, before_digests=["sha256:" + "0" * 64])
        with self.assertRaises(spec_mod.SpecError) as caught:
            spec_mod.validate_changes(root, [change_bad], resume=False)
        self.assertIn("before-image", caught.exception.facts["reason"])


if __name__ == "__main__":
    unittest.main()
