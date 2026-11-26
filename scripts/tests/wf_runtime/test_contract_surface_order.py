"""复杂度条件② 的 AGENTS.md 判定：与触碰面顺序无关，且不把"还没改"当已证事实。

六轮审查 b-5：`AGENTS.md` 排在契约路径之前时，旧实现用「托管块未变」直接把整条条件判成 false，
后面的 `.wf/lib/**` 根本没被检查——同一触碰面换个顺序就换了复杂度结论。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import scope  # noqa: E402

BLOCK = "<!-- TRELLIS:START -->\n托管块\n<!-- TRELLIS:END -->\n"


class ContractSurfaceOrderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wf-contract-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "AGENTS.md").write_text("# 项目\n\n" + BLOCK, encoding="utf-8")
        for command in (["init", "-q"], ["config", "user.email", "t@example.com"],
                        ["config", "user.name", "t"], ["add", "AGENTS.md"],
                        ["commit", "-qm", "base"]):
            subprocess.run(["git", *command], cwd=str(self.root), check=True, capture_output=True)

    def test_flagged_regardless_of_order(self):
        for touch_paths in (["AGENTS.md", ".wf/lib/**"], [".wf/lib/**", "AGENTS.md"]):
            verdict, facts = scope.contract_surface_condition(str(self.root), touch_paths)
            self.assertEqual(verdict, "true", (touch_paths, facts))

    def test_agents_only_with_unchanged_block_is_false_but_says_why(self):
        verdict, facts = scope.contract_surface_condition(str(self.root), ["AGENTS.md"])
        self.assertEqual(verdict, "false", facts)
        self.assertEqual(facts.get("basis"), "managed-block-unchanged-at-approval")
        self.assertIn("contract_changes", str(facts.get("note") or ""))

    def test_changed_managed_block_is_true(self):
        (self.root / "AGENTS.md").write_text(
            "# 项目\n\n<!-- TRELLIS:START -->\n改过的托管块\n<!-- TRELLIS:END -->\n", encoding="utf-8")
        verdict, facts = scope.contract_surface_condition(str(self.root), ["AGENTS.md"])
        self.assertEqual(verdict, "true", facts)
        self.assertEqual(facts.get("fact"), "agents-managed-block")

    def test_outside_block_edit_with_committed_state_stays_false(self):
        """块外文字改动（托管块与 HEAD 一致）不升复杂；语义由方案/person 判断。"""
        (self.root / "AGENTS.md").write_text("# 项目（改了说明）\n\n" + BLOCK, encoding="utf-8")
        verdict, facts = scope.contract_surface_condition(str(self.root), ["AGENTS.md"])
        self.assertEqual(verdict, "false", facts)
        self.assertEqual(facts.get("fact"), "agents-outside-block")


if __name__ == "__main__":
    unittest.main()
