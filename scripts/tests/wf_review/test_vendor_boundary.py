"""P4/K5：框架自有资产（vendor）不进交付面、不进检查对象、不进业务提交。

防的失败（dogfood E1/E2「框架既是交付物又是审查机制」）：`.wf/lib/wflib/*.py` 曾直接进任务
批准触碰面，于是"修框架"和"做需求"混在同一份交付里，检查与提交都无法分开。K5 的处置是
把 `.wf/**` 摘成 vendor：只记 `vendor_dirty`，不参与归属、范围与检查结论。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "新项目开发工作流" / "payload" / "lib"))

from wflib import scope  # noqa: E402


class VendorBoundaryTest(unittest.TestCase):
    def test_wf_prefix_is_vendor(self):
        self.assertTrue(scope.is_vendor(".wf/lib/wflib/scope.py"))
        self.assertTrue(scope.is_vendor(".wf/tasks/2026-x/task.json"))
        self.assertFalse(scope.is_vendor("src/app.py"))
        self.assertFalse(scope.is_vendor("docs/notify.md"))

    def test_vendor_paths_are_separated(self):
        paths = [".wf/bin/wf.py", "src/a.py", ".wf/protocol/codes.json"]
        self.assertEqual(scope.vendor_paths(paths),
                         [".wf/bin/wf.py", ".wf/protocol/codes.json"])

    def test_classifier_has_a_vendor_bucket(self):
        """分类结果必须有一档专收 vendor：它既不算 e（交付），也不算 f（越界）。"""
        import inspect

        source = inspect.getsource(scope.classify_candidates)
        self.assertIn('"v": []', source)
        self.assertIn("is_vendor(path)", source)
        self.assertIn("vendor_dirty", source)

    def test_check_objects_exclude_vendor(self):
        import inspect

        from wflib import check

        source = inspect.getsource(check.object_paths)
        self.assertIn("is_vendor", source,
                      "检查对象必须显式排除 vendor：否则改框架会污染业务交付的指纹")


if __name__ == "__main__":
    unittest.main()
