from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
HASH_FILE = REPO_ROOT / ".trellis/.template-hashes.json"


def _recorded_hashes() -> dict[str, str]:
    return json.loads(HASH_FILE.read_text(encoding="utf-8"))["hashes"]


def _actual_hash(rel_path: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel_path).read_bytes()).hexdigest()


class TemplateHashSemanticsTest(unittest.TestCase):
    def test_clean_managed_files_do_not_keep_stale_hashes(self) -> None:
        clean_files = (
            ".agents/skills/trellis-finish-work/SKILL.md",
            ".opencode/plugins/inject-subagent-context.js",
            ".opencode/plugins/session-start.js",
            ".qoder/settings.json",
            ".trellis/scripts/common/session_context.py",
        )
        recorded = _recorded_hashes()
        for rel_path in clean_files:
            with self.subTest(path=rel_path):
                self.assertEqual(recorded[rel_path], _actual_hash(rel_path))

    def test_repo_local_overlays_remain_detectable_as_modified(self) -> None:
        overlays = (
            ".claude/agents/trellis-research.md",
            ".claude/settings.json",
            ".codex/agents/trellis-check.toml",
            ".codex/agents/trellis-implement.toml",
            ".codex/agents/trellis-research.toml",
            ".codex/config.toml",
            ".opencode/agents/trellis-research.md",
            ".opencode/lib/trellis-context.js",
            ".opencode/plugins/inject-workflow-state.js",
            ".qoder/agents/trellis-research.md",
            ".trellis/scripts/add_session.py",
            ".trellis/scripts/common/safe_commit.py",
            ".trellis/scripts/common/task_store.py",
            ".trellis/workflow.md",
            "AGENTS.md",
        )
        recorded = _recorded_hashes()
        for rel_path in overlays:
            with self.subTest(path=rel_path):
                self.assertNotEqual(recorded[rel_path], _actual_hash(rel_path))

    def test_removed_templates_are_no_longer_tracked(self) -> None:
        recorded = _recorded_hashes()

        for rel_path in (
            ".qoder/skills/trellis-finish-work/SKILL.md",
            ".trellis/scripts/common/registry.py",
            ".trellis/scripts/common/worktree.py",
        ):
            with self.subTest(path=rel_path):
                self.assertNotIn(rel_path, recorded)

        for rel_path in recorded:
            with self.subTest(path=rel_path):
                self.assertFalse(rel_path.startswith(".kiro/"))


if __name__ == "__main__":
    unittest.main()
