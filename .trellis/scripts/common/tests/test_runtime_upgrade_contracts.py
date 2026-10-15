from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]

# Platform deployment directories that this repository owned but retired in the
# 0.7.0 upgrade (.opencode / .qoder / .kiro). Their directories no longer exist
# on disk, so pinning assertions on them can only produce FileNotFoundError.
RETIRED_PLATFORM_DIRS = (".opencode/", ".qoder/", ".kiro/")


class RuntimeUpgradeContractsTest(unittest.TestCase):
    def test_hook_capable_research_carrier_keeps_skill_and_mcp_access(self) -> None:
        """0.7.0: the research agent's tool surface is ``Skill`` + ``mcp__*``.

        Upstream dropped the per-server allow-list (``mcp__ace__search_context``,
        ``mcp__Context7__*``, ``mcp__grok-search__*`` …) that the 0.5.17 template
        carried, so pinning concrete server names here only re-breaks on every
        upstream template refresh. Assert the invariants that must survive a
        refresh instead: the agent keeps Skill access and keeps MCP access.
        """
        carrier = REPO_ROOT / ".claude/agents/trellis-research.md"
        self.assertTrue(carrier.is_file(), f"missing research carrier: {carrier}")
        content = carrier.read_text(encoding="utf-8")

        tools_lines = [ln for ln in content.splitlines() if ln.startswith("tools:")]
        with self.subTest(check="single tools: line"):
            self.assertEqual(len(tools_lines), 1, tools_lines)
        tools_line = tools_lines[0] if tools_lines else ""

        for snippet in ("Skill", "mcp__"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, tools_line)

        for snippet in ("# Research Agent", "## Core Responsibilities", "Persist"):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, content)

    def test_codex_research_contract_keeps_dispatch_fallback_and_routing(self) -> None:
        """The Codex research carrier keeps its project-local guarantee plus the
        0.7.0 context-loading protocol.

        ``explicit delegated/non-inline Codex`` is this repository's inline-mode
        guard (re-applied by hand after the 0.7.0 template refresh). ``Trellis
        Context Loading Protocol`` is the 0.7.0 replacement for the old manual
        ``Active task: <path>`` prelude. Assert both; do not assert the retired
        provider-specific search table.
        """
        content = (
            REPO_ROOT / ".codex/agents/trellis-research.toml"
        ).read_text(encoding="utf-8")
        for snippet in (
            "Active task: <path>",
            "Trellis Context Loading Protocol",
            "explicit delegated/non-inline Codex",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, content)

    def test_change_workflow_keeps_current_finish_route_wording(self) -> None:
        """0.7.0 renumbered the finish route.

        0.5.17 said ``Phase 3.1 (verify quality + spec update)``; 0.7.0 anchors
        the same wrap-up contract on ``[workflow-state:completed]`` plus
        ``Phase 3.5`` (``/trellis:finish-work``). The route still exists and is
        still documented — the wording moved.
        """
        for rel_path in (
            ".agents/skills/trellis-meta/references/customize-local/change-workflow.md",
            ".claude/skills/trellis-meta/references/customize-local/change-workflow.md",
        ):
            content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for snippet in ("[workflow-state:completed]", "Phase 3.5"):
                with self.subTest(path=rel_path, snippet=snippet):
                    self.assertIn(snippet, content)

    def test_codex_hook_command_uses_utf8_flag(self) -> None:
        hooks = json.loads(
            (REPO_ROOT / ".codex/hooks.json").read_text(encoding="utf-8")
        )
        command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        self.assertIn("python3 -X utf8 .codex/hooks/inject-workflow-state.py", command)

    def test_no_retired_platform_paths_are_asserted(self) -> None:
        """Guard the guard: this file must not pin deleted platform dirs.

        Re-introducing ``.opencode/`` / ``.qoder/`` / ``.kiro/`` paths as
        assertion targets would turn the cases above back into
        ``FileNotFoundError`` the moment those directories stay retired.

        Inspects the parsed string literals rather than the raw source, so the
        module-level constant and the docstrings that explain this trap are not
        mistaken for committed assertions.
        """
        import ast

        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        # The module-level tuple and every docstring legitimately *name* these
        # directories while explaining the trap; only real assertion targets
        # (other string literals) are a defect.
        exempt: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "RETIRED_PLATFORM_DIRS":
                        if isinstance(node.value, ast.Tuple):
                            exempt |= {
                                elt.value
                                for elt in node.value.elts
                                if isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            }
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    exempt.add(doc)
        offending = sorted(
            {
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value not in exempt
                and any(
                    needle in node.value
                    for needle in RETIRED_PLATFORM_DIRS
                )
            }
        )
        with self.subTest(offending=offending):
            self.assertEqual(offending, [])


if __name__ == "__main__":
    unittest.main()
