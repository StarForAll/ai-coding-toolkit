"""打包工具的破坏性顺序：预检必须在删除发行树之前。

防的失败（2026-11-09 实测两次）：新增 lib 文件忘登记 → 旧实现先 rmtree 再检查 →
"校验失败"顺带删掉已提交的发行树，只能靠重建恢复。检查与破坏的顺序不能反。
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts" / "build-wf-release.py"


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


if __name__ == "__main__":
    unittest.main()
