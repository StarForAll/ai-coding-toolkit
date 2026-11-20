"""打包工具的破坏性顺序：预检必须在删除发行树之前。

防的失败（2026-11-09 实测两次）：新增 lib 文件忘登记 → 旧实现先 rmtree 再检查 →
"校验失败"顺带删掉已提交的发行树，只能靠重建恢复。检查与破坏的顺序不能反。
"""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts" / "build-wf-release.py"
SPEC = importlib.util.spec_from_file_location("wf_build_release_under_test", BUILD)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BuildOrderingTest(unittest.TestCase):
    def setUp(self):
        self.source = BUILD.read_text(encoding="utf-8")

    def test_preflight_runs_before_removing_release_tree(self):
        main_body = self.source.split("def main(argv=None):", 1)[1]
        preflight_at = main_body.index("dev_manifest = preflight()")
        remove_at = main_body.index("shutil.rmtree(RELEASE_ROOT)")
        self.assertLess(preflight_at, remove_at,
                        "预检必须在删除发行树之前：否则校验失败会删掉已提交的发行树")

    def test_unlisted_file_check_lives_in_preflight_only(self):
        self.assertIn("def preflight():", self.source)
        preflight_body = self.source.split("def preflight():", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("unlisted", preflight_body)
        build_body = self.source.split("def build(", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("unlisted", build_body, "检查不该回到 build()：那会在删树之后才失败")

    def test_readme_version_must_match_the_release(self):
        self.assertEqual(MODULE.readme_target_version(), "0.1.3")
        MODULE.assert_readme_version("0.1.3")
        with self.assertRaises(MODULE.BuildError):
            MODULE.assert_readme_version("0.1.4")

    def test_existing_tag_refuses_rebuilding_the_same_version(self):
        tags = subprocess.run(["git", "tag", "--list", "wf-v*"], cwd=REPO,
                              capture_output=True, text=True, check=False).stdout.split()
        if not tags:
            self.skipTest("no wf-v* tag in this checkout")
        version = tags[0][len("wf-v"):]
        with self.assertRaises(MODULE.BuildError):
            MODULE.assert_version_not_tagged(version)
        MODULE.assert_version_not_tagged("9.9.9")

    def test_guards_run_before_the_release_tree_is_removed(self):
        main_body = self.source.split("def main(argv=None):", 1)[1]
        readme_at = main_body.index("assert_readme_version(args.version)")
        tag_at = main_body.index("assert_version_not_tagged(args.version)")
        remove_at = main_body.index("shutil.rmtree(RELEASE_ROOT)")
        self.assertLess(readme_at, remove_at)
        self.assertLess(tag_at, remove_at)


if __name__ == "__main__":
    unittest.main()
