""".wf/spec 顶层的结构文件不是规则（2026-11-25 第四轮复审，b-7 类）。

出厂模板把 `index.md`、`pre-dev-checklist.md`、`quality-checklist.md` 放在 `.wf/spec/` 顶层，
而它们由 `spec-update` 的「三段同步」维护、不按 paths 匹配。旧 `all_specs` 把目录下所有 `.md`
都当规则加载，于是出厂模板自带 3 条「frontmatter missing」；dogfood 会话 1 在收工前才发现并
手工补 frontmatter（同一批准触碰面内返工）。

断言：结构文件不进规则集、不产生 unparsed；子目录里同名文件仍按规则校验；缺 frontmatter 的
真规则仍被报出（不静默放行）。
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import spec  # noqa: E402

VALID_RULE = """---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "2026-11-25"
author: "human"
counterexample: "不算违反：只读核对。"
---

# 规则
"""


class SpecStructureFilesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        base = self.root / ".wf/spec"
        (base / "rules").mkdir(parents=True)
        # 出厂模板的三个结构文件：没有 frontmatter，且本来就不是规则
        for name in spec.SPEC_STRUCTURE_FILES:
            (base / name).write_text(f"# {name}\n\n结构文件。\n", encoding="utf-8")
        (base / "rules/a.md").write_text(VALID_RULE, encoding="utf-8")
        (base / "rules/no-frontmatter.md").write_text("# 缺元数据的规则\n", encoding="utf-8")
        # 子目录里的同名文件不是结构文件
        (base / "rules/index.md").write_text("# 子目录索引\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_structural_files_are_not_rules(self):
        paths = {entry["path"] for entry in spec.all_specs(str(self.root))}
        for name in spec.SPEC_STRUCTURE_FILES:
            self.assertNotIn(f".wf/spec/{name}", paths)
        self.assertIn(".wf/spec/rules/a.md", paths)

    def test_subdirectory_namesakes_still_validated(self):
        entries = {entry["path"]: entry for entry in spec.all_specs(str(self.root))}
        self.assertIn(".wf/spec/rules/index.md", entries)
        self.assertTrue(entries[".wf/spec/rules/index.md"]["problems"])

    def test_missing_frontmatter_rule_is_still_reported(self):
        entries = {entry["path"]: entry for entry in spec.all_specs(str(self.root))}
        rule = entries[".wf/spec/rules/no-frontmatter.md"]
        self.assertFalse(rule["routable"])
        self.assertIn("frontmatter missing", rule["problems"])

    def test_match_has_no_unparsed_for_structural_files(self):
        entries, unparsed = spec.match(str(self.root), ["pkg/a.py"])
        self.assertEqual({item["path"] for item in unparsed},
                         {".wf/spec/rules/index.md", ".wf/spec/rules/no-frontmatter.md"})
        self.assertEqual([entry["path"] for entry in entries], [".wf/spec/rules/a.md"])


if __name__ == "__main__":
    unittest.main()
