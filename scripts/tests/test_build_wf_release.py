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
        # 版本唯一源 = README「目标版本」+ builder --version；断言不写死版本号，
        # 只要求"当前 README 版本通过、相邻版本被拒"（否则每次 bump 都要改测试）。
        current = MODULE.readme_target_version()
        MODULE.assert_readme_version(current)
        major, minor, patch = (int(part) for part in current.split("."))
        with self.assertRaises(MODULE.BuildError):
            MODULE.assert_readme_version(f"{major}.{minor}.{patch + 1}")

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
        cli_at = main_body.index("assert_cli_packaging(None)")
        tag_at = main_body.index("assert_version_not_tagged(args.version)")
        remove_at = main_body.index("shutil.rmtree(RELEASE_ROOT)")
        self.assertLess(readme_at, remove_at)
        self.assertLess(cli_at, remove_at)
        self.assertLess(tag_at, remove_at)

    def test_build_output_has_no_hash_dump(self):
        source = (REPO / "scripts" / "build-wf-release.py").read_text(encoding="utf-8")
        self.assertNotIn('print("hashes:")', source)
        self.assertNotIn('print(f"rules_digest:', source)

    def test_cli_package_resolves_current_release_version(self):
        # CLI 版本动态读取发行清单；打包时这个路径/正则必须仍能解析到同一版本。
        MODULE.assert_cli_packaging(MODULE.readme_target_version())


if __name__ == "__main__":
    unittest.main()


class VerifyIsReadOnlyTest(unittest.TestCase):
    """"同版不复用"只管重建；`--version X --verify` 必须能核对**已打 tag** 的发行。

    背景（2026-11-23）：`verify-wf-release.py` 的 release_tree_matches_source 调的就是这条
    命令；tag 存在时若被 guard 拒掉，发行核对永远 FAIL。
    """

    def test_verify_mode_skips_tag_guard_and_rebuild(self):
        source = (REPO / "scripts" / "build-wf-release.py").read_text(encoding="utf-8")
        marker = source.index("if args.verify:")
        # --verify 分支内：不重建、不跑 tag guard
        verify_block = source[marker:source.index("else:", marker)]
        self.assertNotIn("shutil.rmtree(RELEASE_ROOT)", verify_block)
        self.assertNotIn("assert_version_not_tagged(args.version)", verify_block)
        # 非 --verify 分支内：两者都在
        rebuild_block = source[source.index("else:", marker):]
        self.assertIn("shutil.rmtree(RELEASE_ROOT)", rebuild_block)
        self.assertIn("assert_version_not_tagged(args.version)", rebuild_block)
