"""安装器托管段只来自发行清单（`gitignore_managed` 是忽略集合的唯一枚举）。

此前 `managed_segment()` 留了一份两行回退，与清单五条不同源；回退会静默写出半个托管段。
本用例断言：有登记 → 原样输出；缺登记 → 明确抛错（由主流程转 `WF_ASSET_DECISION`）。
"""

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INSTALL = REPO / "docs" / "workflows" / "wf" / "payload" / "install.py"


def _install_module():
    spec = importlib.util.spec_from_file_location("wf_install_under_test", INSTALL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManagedSegmentTest(unittest.TestCase):
    def test_segment_comes_from_manifest_only(self):
        module = _install_module()
        manifest = {"gitignore_managed": {"begin_marker": "# begin",
                                          "lines": ["/.wf/.runtime/", "/.wf/writer.json"],
                                          "end_marker": "# end"}}
        self.assertEqual(module.managed_segment(manifest),
                         "# begin\n/.wf/.runtime/\n/.wf/writer.json\n# end")

    def test_missing_registration_is_refused(self):
        module = _install_module()
        for manifest in ({}, {"gitignore_managed": {"lines": []}},
                         {"gitignore_managed": {"lines": ["/x"], "begin_marker": ""}}):
            with self.assertRaises(ValueError):
                module.managed_segment(manifest)


if __name__ == "__main__":
    unittest.main()
