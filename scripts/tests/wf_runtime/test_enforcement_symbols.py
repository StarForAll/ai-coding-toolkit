"""enforcement 行的符号核对。

`§1.1 固定流转程序化` 承诺"清单内步骤缺脚本实现按缺口处理"，但登记行曾指向
`check.py::run_check`（已拆三段）、`cli.py::dep/task-rework/task-replace`（已在 tasks.py）
这类不存在符号，而构建只校"非空"。此用例把"符号存在"变成构建门禁的回归断言。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))

import wf_release_common as common  # noqa: E402


class EnforcementSymbolTest(unittest.TestCase):
    def test_current_workflow_docs_resolve(self):
        parsed = common.parse_workflow_steps()
        self.assertTrue(parsed)
        self.assertEqual(common.enforcement_symbol_problems(parsed), [])

    def test_missing_symbol_is_reported(self):
        parsed = [{"id": "task.x", "enforcement": "`wflib/check.py::run_check`（执行）"}]
        problems = common.enforcement_symbol_problems(parsed)
        self.assertEqual(len(problems), 1)
        self.assertIn("run_check", problems[0])

    def test_external_layer_lines_are_skipped(self):
        parsed = [{"id": "control.repair.apply",
                   "enforcement": "系统级 `wf repair` 或直接运行 `.wf/bin/repair.py`"}]
        self.assertEqual(common.enforcement_symbol_problems(parsed), [])

    def test_install_symbol_resolves_with_release_prefix(self):
        parsed = [{"id": "control.asset.apply",
                   "enforcement": "系统级 `wf upgrade` → `<发行根>/install.py::run_upgrade`"}]
        self.assertEqual(common.enforcement_symbol_problems(parsed), [])


if __name__ == "__main__":
    unittest.main()
