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
        # 0.5.17: several files were overwritten with .new template versions
        # and now match their template hash. Only truly locally-customized
        # files remain as overlays (recorded hash != actual hash).
        overlays = (
            ".claude/agents/trellis-research.md",
            ".claude/hooks/inject-workflow-state.py",
            ".claude/settings.json",
            ".codex/agents/trellis-check.toml",
            ".codex/agents/trellis-implement.toml",
            ".codex/agents/trellis-research.toml",
            ".codex/hooks/inject-workflow-state.py",
            ".codex/config.toml",
            ".qoder/hooks/inject-workflow-state.py",
            ".opencode/agents/trellis-research.md",
            ".opencode/plugins/inject-workflow-state.js",
            ".qoder/agents/trellis-research.md",
            ".agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
            ".claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
            ".opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
            ".qoder/skills/trellis-meta/references/customize-local/change-task-lifecycle.md",
            ".trellis/workflow.md",
            "AGENTS.md",
        )
        recorded = _recorded_hashes()
        for rel_path in overlays:
            with self.subTest(path=rel_path):
                self.assertNotEqual(recorded[rel_path], _actual_hash(rel_path))

    def test_overwritten_files_now_match_template_hash(self) -> None:
        # 0.5.17: these files were overwritten with .new template versions,
        # so their actual hash now matches the recorded template hash.
        overwritten = (
            ".trellis/scripts/add_session.py",
            ".trellis/scripts/common/safe_commit.py",
            ".trellis/scripts/common/task_store.py",
        )
        recorded = _recorded_hashes()
        for rel_path in overwritten:
            with self.subTest(path=rel_path):
                self.assertEqual(recorded[rel_path], _actual_hash(rel_path))

    def test_removed_templates_are_no_longer_tracked(self) -> None:
        recorded = _recorded_hashes()

        for rel_path in (
            ".qoder/skills/trellis-finish-work/SKILL.md",
            ".trellis/scripts/common/registry.py",
            ".trellis/scripts/common/worktree.py",
        ):
            with self.subTest(path=rel_path):
                self.assertNotIn(rel_path, recorded)

        # 0.5.17: .kiro/ platform is now a supported platform with template
        # files tracked in template-hashes.json. Remove the old assertion
        # that disallowed any .kiro/ entries.


if __name__ == "__main__":
    unittest.main()
