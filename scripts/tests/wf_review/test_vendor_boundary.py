"""P4/K5：框架自有资产（vendor）不进交付面、不进检查对象、不进业务提交。

防的失败（dogfood E1/E2「框架既是交付物又是审查机制」）：`.wf/lib/wflib/*.py` 曾直接进任务
批准触碰面，于是"修框架"和"做需求"混在同一份交付里，检查与提交都无法分开。K5 的处置是
把 `.wf/**` 摘成 vendor：只记 `vendor_dirty`，不参与归属、范围与检查结论。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

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


class VendorVsControlRecordTest(unittest.TestCase):
    """`.wf/tasks/**`、`.wf/baseline.md` 是项目数据，不是 vendor——顺序错了会把归档提交挡住。"""

    def test_control_records_are_not_vendor_assets(self):
        from wflib import scope

        with tempfile_dir() as root:
            task = {"id": "2026-x"}
            found = scope.vendor_assets(str(root), task,
                                        [".wf/tasks/2026-x", ".wf/tasks/2026-x/task.json",
                                         ".wf/baseline.md", ".wf/lib/wflib/scope.py"])
        self.assertIn(".wf/lib/wflib/scope.py", found)
        self.assertNotIn(".wf/tasks/2026-x/task.json", found)

    def test_classifier_puts_records_before_vendor(self):
        import inspect

        source = inspect.getsource(scope.classify_candidates) if False else None
        import wflib.scope as scope_mod

        body = inspect.getsource(scope_mod.classify_candidates)
        self.assertLess(body.index("_is_control_record"), body.index("is_vendor(path)"),
                        "控制记录必须在 vendor 之前判定")


def tempfile_dir():
    import contextlib, tempfile

    @contextlib.contextmanager
    def _cm():
        with tempfile.TemporaryDirectory() as tmp:
            yield tmp

    return _cm()


class ProjectSpecIsNotVendorTest(unittest.TestCase):
    """`.wf/spec/**` 是项目数据（spec.update 写入、升级不覆盖），不是框架 vendor。

    审查实测：漏了它会让**初始化任务**与日常 spec 更新都无法归档（提交面被判 vendor）。
    """

    def test_project_spec_paths_are_project_data(self):
        from wflib import scope

        with tempfile_dir() as root:
            found = scope.vendor_assets(str(root), {"id": "2026-x"},
                                        [".wf/spec/index.md", ".wf/spec/core/a.md",
                                         ".wf/lib/wflib/scope.py"])
        self.assertNotIn(".wf/spec/index.md", found)
        self.assertNotIn(".wf/spec/core/a.md", found)
        self.assertIn(".wf/lib/wflib/scope.py", found)


class ProjectDataDeclarationTest(unittest.TestCase):
    """项目数据集合只来自 protocol（前缀清单漏过 `.wf/spec/`，那类洞只能靠声明表堵住）。"""

    def test_declaration_lists_the_project_data_paths(self):
        from wflib import protocol

        data = protocol.project_data()
        self.assertIn(".wf/tasks/", data["prefixes"])
        self.assertIn(".wf/spec/", data["prefixes"])
        self.assertIn(".wf/baseline.md", data["files"])

    def test_scope_reads_the_declaration_not_a_local_list(self):
        source = (REPO / "docs/workflows/wf/payload/lib/wflib/scope.py").read_text(encoding="utf-8")
        self.assertIn("protocol_mod.project_data()", source)
        self.assertNotIn('data_prefixes = (".wf/tasks/"', source)

    def test_spec_changes_reach_the_classifier_not_the_vendor_bucket(self):
        import subprocess
        import tempfile

        from wflib import scope

        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            task = {"id": "2026-x", "entry_snapshot": {"touch_paths": [".wf/spec/**"]},
                    "plan": {"touch_paths": [".wf/spec/**"]}}
            (Path(tmp) / ".wf/spec").mkdir(parents=True)
            (Path(tmp) / ".wf/spec/index.md").write_text("x", encoding="utf-8")
            classified = scope.classify_candidates(tmp, task, receipts=())
        self.assertEqual(classified["buckets"]["v"], [],
                         "项目自己的 spec 不能进 vendor 桶")
