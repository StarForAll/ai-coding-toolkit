"""六轮-6：复杂度四项条件只报**可证事实**（设计稿 §4.3）。

三个已知偏差各有唯一判据：
① 扩面判包含关系（`paths.subsumes`），不判"是否相交"——`src/a.py → src/**` 相交却扩大了面；
② 验收口径变化判**摘要**，不只比 id 集合——沿用原 id 只改判据文字同样是新承诺；
③ `AGENTS.md` 只把安装器托管块（`TRELLIS:START`…`TRELLIS:END`）算契约面，
   块外项目文字改动不因此升为复杂（无法证明时保守判变）。
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "docs" / "workflows" / "wf" / "payload" / "lib"))

from wflib import fingerprint, scope, tasks  # noqa: E402


def _acceptance(statement="文件内容为 ok"):
    return [{"id": "a1", "statement": statement, "verification_ids": []}]


class ExpansionConditionTest(unittest.TestCase):
    def test_widening_a_glob_is_an_expansion(self):
        value, fact = scope.expansion_condition(["src/a.py"], ["src/**"])
        self.assertEqual(value, "true", fact)

    def test_narrowing_to_an_approved_file_is_within_previous(self):
        value, fact = scope.expansion_condition(["src/**"], ["src/a.py"])
        self.assertEqual(value, "false", fact)

    def test_new_covering_entry_is_within_previous(self):
        value, fact = scope.expansion_condition(["src/**"], ["src/a.py", "src/b.py"])
        self.assertEqual(value, "false", fact)

    def test_unrelated_path_is_an_expansion(self):
        value, fact = scope.expansion_condition(["src/**"], ["docs/x.md"])
        self.assertEqual(value, "true", fact)

    def test_first_approval_has_no_previous(self):
        value, fact = scope.expansion_condition([], ["src/**"])
        self.assertEqual(value, "false", fact)
        self.assertEqual(fact.get("fact"), "no-previous-approval")


class AcceptanceChangeTest(unittest.TestCase):
    def test_same_ids_with_new_criteria_is_a_change(self):
        previous = {"acceptance_ids": ["a1"],
                    "acceptance_digest": fingerprint.acceptance_digest(_acceptance("旧判据"))}
        change = tasks.acceptance_change(previous, {"acceptance": _acceptance("新判据")})
        self.assertIsNotNone(change, "同 id 改判据文本必须判为验收口径变化")
        self.assertEqual(change["current_ids"], ["a1"])

    def test_identical_acceptance_is_not_a_change(self):
        digest = fingerprint.acceptance_digest(_acceptance())
        previous = {"acceptance_ids": ["a1"], "acceptance_digest": digest}
        self.assertIsNone(tasks.acceptance_change(previous, {"acceptance": _acceptance()}))

    def test_first_approval_has_no_previous(self):
        self.assertIsNone(tasks.acceptance_change({}, {"acceptance": _acceptance()}))


class AgentsManagedBlockTest(unittest.TestCase):
    BLOCK = "<!-- TRELLIS:START -->\nmanaged v1\n<!-- TRELLIS:END -->\n"

    def _repo(self, committed_text, current_text=None):
        root = tempfile.mkdtemp(prefix="wf-agents-")
        path = os.path.join(root, "AGENTS.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(committed_text)
        for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "t@example.com"],
                    ["git", "config", "user.name", "t"], ["git", "add", "-A"],
                    ["git", "commit", "-qm", "init"]):
            subprocess.run(cmd, cwd=root, check=True, capture_output=True)
        if current_text is not None:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(current_text)
        return root

    def test_outside_block_edit_is_not_a_contract_change(self):
        repo = self._repo("# 项目说明\n\n" + self.BLOCK + "\n项目文字。\n",
                          "# 项目说明（改过）\n\n" + self.BLOCK + "\n项目文字。\n")
        value, fact = scope.contract_surface_condition(repo, ["AGENTS.md"])
        self.assertEqual(value, "false", fact)
        self.assertEqual(fact.get("fact"), "agents-outside-block")

    def test_inside_block_edit_is_a_contract_change(self):
        repo = self._repo(self.BLOCK,
                          "<!-- TRELLIS:START -->\nmanaged v2\n<!-- TRELLIS:END -->\n")
        value, fact = scope.contract_surface_condition(repo, ["AGENTS.md"])
        self.assertEqual(value, "true", fact)
        self.assertEqual(fact.get("fact"), "agents-managed-block")

    def test_untracked_agents_file_is_conservative(self):
        root = tempfile.mkdtemp(prefix="wf-agents-untracked-")
        with open(os.path.join(root, "AGENTS.md"), "w", encoding="utf-8") as handle:
            handle.write(self.BLOCK)
        value, fact = scope.contract_surface_condition(root, ["AGENTS.md"])
        self.assertEqual(value, "true", fact)

    def test_contract_surface_patterns_still_escalate(self):
        repo = self._repo(self.BLOCK)
        value, fact = scope.contract_surface_condition(repo, [".wf/templates/**"])
        self.assertEqual(value, "true", fact)
        self.assertEqual(fact.get("fact"), "contract-surface")


if __name__ == "__main__":
    unittest.main()