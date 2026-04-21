from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
COMMANDS_DIR = REPO_ROOT / "docs" / "workflows" / "新项目开发工作流" / "commands"
ANALYZE_SCRIPT = COMMANDS_DIR / "analyze-upgrade.py"


class UpgradeAnalysisTests(unittest.TestCase):
    def run_script(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [PYTHON, str(ANALYZE_SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

    def make_root(self, prefix: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(shutil.rmtree, root)
        return root

    def write_file(self, root: Path, rel_path: str, content: str) -> None:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def latest_env(self, version: str) -> dict[str, str]:
        return {"TRELLIS_LATEST_VERSION": version}

    def test_analyze_upgrade_classifies_add_replace_merge_and_keep(self) -> None:
        baseline = self.make_root("upgrade-baseline-")
        expected = self.make_root("upgrade-expected-")
        target = self.make_root("upgrade-target-")

        self.write_file(baseline, ".claude/commands/trellis/start.md", "baseline start\n")
        self.write_file(baseline, ".claude/commands/trellis/brainstorm.md", "baseline brainstorm\n")

        self.write_file(expected, ".claude/commands/trellis/start.md", "workflow patched start\n")
        self.write_file(expected, ".claude/commands/trellis/brainstorm.md", "workflow brainstorm\n")
        self.write_file(expected, ".claude/commands/trellis/design.md", "workflow design\n")
        self.write_file(expected, ".trellis/scripts/workflow/check-quality.py", "# helper\n")

        self.write_file(target, ".claude/commands/trellis/start.md", "baseline start\n")
        self.write_file(target, ".claude/commands/trellis/brainstorm.md", "target custom brainstorm\n")
        self.write_file(target, ".trellis/scripts/workflow/check-quality.py", "# helper\n")
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "claude",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["claude:start"], "replace")
        self.assertEqual(actions["claude:brainstorm"], "merge")
        self.assertEqual(actions["claude:design"], "add")
        self.assertEqual(actions["shared:check-quality.py"], "keep")

    def test_analyze_upgrade_supports_codex_agents_skills(self) -> None:
        baseline = self.make_root("upgrade-baseline-codex-")
        expected = self.make_root("upgrade-expected-codex-")
        target = self.make_root("upgrade-target-codex-")

        self.write_file(baseline, ".agents/skills/brainstorm/SKILL.md", "baseline brainstorm\n")
        self.write_file(baseline, ".agents/skills/finish-work/SKILL.md", "baseline finish-work\n")
        self.write_file(baseline, ".codex/agents/check.toml", 'name = "check"\nsandbox_mode = "read-only"\n')

        self.write_file(expected, ".agents/skills/brainstorm/SKILL.md", "workflow brainstorm\n")
        self.write_file(expected, ".agents/skills/finish-work/SKILL.md", "workflow finish-work\n")
        self.write_file(expected, ".codex/agents/check.toml", 'name = "check"\nsandbox_mode = "workspace-write"\n')

        self.write_file(target, ".agents/skills/brainstorm/SKILL.md", "baseline brainstorm\n")
        self.write_file(target, ".agents/skills/finish-work/SKILL.md", "baseline finish-work\n")
        self.write_file(target, ".codex/agents/check.toml", 'name = "check"\nsandbox_mode = "read-only"\n')
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "codex",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["codex:brainstorm"], "replace")
        self.assertEqual(actions["codex:finish-work"], "replace")
        self.assertEqual(actions["codex:agent:check"], "replace")

    def test_analyze_upgrade_supports_claude_agents(self) -> None:
        baseline = self.make_root("upgrade-baseline-claude-agent-")
        expected = self.make_root("upgrade-expected-claude-agent-")
        target = self.make_root("upgrade-target-claude-agent-")

        self.write_file(baseline, ".claude/agents/research.md", "baseline research\n")
        self.write_file(expected, ".claude/agents/research.md", "workflow research\n")
        self.write_file(target, ".claude/agents/research.md", "baseline research\n")
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "claude",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["claude:agent:research"], "replace")

    def test_analyze_upgrade_supports_opencode_agents(self) -> None:
        baseline = self.make_root("upgrade-baseline-opencode-agent-")
        expected = self.make_root("upgrade-expected-opencode-agent-")
        target = self.make_root("upgrade-target-opencode-agent-")

        self.write_file(baseline, ".opencode/agents/check.md", "baseline check\n")
        self.write_file(expected, ".opencode/agents/check.md", "workflow check\n")
        self.write_file(target, ".opencode/agents/check.md", "baseline check\n")
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "opencode",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["opencode:agent:check"], "replace")

    def test_analyze_upgrade_detects_codex_secondary_skills_dir_and_parallel_drift(self) -> None:
        baseline = self.make_root("upgrade-baseline-codex-multi-")
        expected = self.make_root("upgrade-expected-codex-multi-")
        target = self.make_root("upgrade-target-codex-multi-")

        self.write_file(baseline, ".codex/skills/parallel/SKILL.md", "baseline parallel\n")

        self.write_file(expected, ".agents/skills/delivery/SKILL.md", "workflow delivery\n")
        self.write_file(expected, ".codex/skills/.backup-original/parallel/SKILL.md", "baseline parallel\n")

        self.write_file(target, ".agents/skills/delivery/SKILL.md", "workflow delivery\n")
        self.write_file(target, ".codex/skills/delivery/SKILL.md", "drifted delivery\n")
        self.write_file(target, ".codex/skills/parallel/SKILL.md", "drifted parallel\n")
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "codex",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["codex[.codex/skills]:delivery"], "delete")
        self.assertEqual(actions["codex[.codex/skills]:parallel"], "delete")

    def test_analyze_upgrade_classifies_delete_from_target_install_record(self) -> None:
        baseline = self.make_root("upgrade-baseline-delete-")
        expected = self.make_root("upgrade-expected-delete-")
        target = self.make_root("upgrade-target-delete-")

        self.write_file(expected, ".claude/commands/trellis/start.md", "workflow patched start\n")
        self.write_file(target, ".claude/commands/trellis/start.md", "workflow patched start\n")
        self.write_file(target, ".claude/commands/trellis/retired-command.md", "retired workflow command\n")
        self.write_file(
            target,
            ".trellis/workflow-installed.json",
            json.dumps(
                {
                    "cli_types": ["claude"],
                    "commands": ["brainstorm", "retired-command"],
                    "overlay_commands": ["brainstorm"],
                    "added_commands": ["retired-command"],
                    "scripts": [],
                },
                ensure_ascii=False,
            ),
        )
        self.write_file(target, ".trellis/.version", "2.1.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "claude",
            "--json",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["claude:retired-command"], "delete")

    def test_analyze_upgrade_blocks_when_target_is_not_latest_trellis(self) -> None:
        baseline = self.make_root("upgrade-baseline-stale-")
        expected = self.make_root("upgrade-expected-stale-")
        target = self.make_root("upgrade-target-stale-")

        self.write_file(target, ".claude/commands/trellis/start.md", "baseline start\n")
        self.write_file(target, ".trellis/.version", "2.0.0\n")

        result = self.run_script(
            "--baseline-root",
            str(baseline),
            "--expected-root",
            str(expected),
            "--target-root",
            str(target),
            "--cli",
            "claude",
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
        self.assertIn("尚未升级到当前最新 Trellis", result.stderr)
        self.assertIn("禁止执行当前步骤", result.stderr)


if __name__ == "__main__":
    unittest.main()
