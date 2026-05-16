from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


class RuntimeUpgradeContractsTest(unittest.TestCase):
    def test_rich_research_contract_on_hook_capable_carriers(self) -> None:
        matrix = {
            ".claude/agents/trellis-research.md": (
                "mcp__ace__search_context",
                "mcp__Context7__resolve-library-id",
                "mcp__deepwiki__read_wiki_structure",
                "mcp__grok-search__web_search",
                "Active task: <path>",
                "ace.search_context",
                "Context7",
                "grok.web_search",
            ),
            ".opencode/agents/trellis-research.md": (
                "mcp__ace__search_context: allow",
                "mcp__Context7__*: allow",
                "mcp__deepwiki__*: allow",
                "mcp__grok-search__*: allow",
                "Active task: <path>",
                "ace.search_context",
                "Context7",
                "grok.web_search",
            ),
            ".qoder/agents/trellis-research.md": (
                "mcp__ace__search_context",
                "mcp__Context7__resolve-library-id",
                "mcp__deepwiki__read_wiki_structure",
                "mcp__grok-search__web_search",
                "Active task: <path>",
                "ace.search_context",
                "Context7",
                "grok.web_search",
            ),
        }

        for rel_path, expected_snippets in matrix.items():
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for snippet in expected_snippets:
                with self.subTest(path=rel_path, snippet=snippet):
                    self.assertIn(snippet, content)

    def test_codex_research_contract_keeps_dispatch_fallback_and_routing(self) -> None:
        content = (
            REPO_ROOT / ".codex/agents/trellis-research.toml"
        ).read_text(encoding="utf-8")
        for snippet in (
            "Active task: <path>",
            "ace.search_context",
            "Context7",
            "deepwiki",
            "grok-search",
            "explicit delegated/non-inline Codex",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, content)

    def test_kiro_research_prompt_keeps_active_task_fallback(self) -> None:
        data = json.loads(
            (REPO_ROOT / ".kiro/agents/trellis-research.json").read_text(
                encoding="utf-8"
            )
        )
        prompt = data["prompt"]
        self.assertIn("Active task: <path>", prompt)
        self.assertIn("semantic/context search", prompt)

    def test_change_workflow_keeps_current_finish_route_wording(self) -> None:
        expected = "Phase 3.1 (verify quality + spec update)"
        for rel_path in (
            ".agents/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".claude/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".kiro/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".opencode/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".qoder/skills/trellis-meta/references/customize-local/change-workflow.md",
        ):
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            with self.subTest(path=rel_path):
                self.assertIn(expected, content)

    def test_codex_hook_command_uses_utf8_flag(self) -> None:
        hooks = json.loads(
            (REPO_ROOT / ".codex/hooks.json").read_text(encoding="utf-8")
        )
        command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("python3 -X utf8 .codex/hooks/inject-workflow-state.py", command)


if __name__ == "__main__":
    unittest.main()
