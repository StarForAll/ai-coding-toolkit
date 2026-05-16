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

        self.write_file(baseline, ".claude/commands/trellis/continue.md", "baseline continue\n")
        self.write_file(baseline, ".claude/commands/trellis/brainstorm.md", "baseline brainstorm\n")

        self.write_file(expected, ".claude/commands/trellis/continue.md", "workflow patched continue\n")
        self.write_file(expected, ".claude/commands/trellis/brainstorm.md", "workflow brainstorm\n")
        self.write_file(expected, ".claude/commands/trellis/design.md", "workflow design\n")
        self.write_file(expected, ".trellis/scripts/workflow/check-quality.py", "# helper\n")

        self.write_file(target, ".claude/commands/trellis/continue.md", "baseline continue\n")
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
        self.assertEqual(actions["claude:continue"], "replace")
        self.assertEqual(actions["claude:brainstorm"], "merge")
        self.assertEqual(actions["claude:design"], "add")
        self.assertEqual(actions["shared:check-quality.py"], "keep")

    def test_analyze_upgrade_supports_codex_agents_skills(self) -> None:
        baseline = self.make_root("upgrade-baseline-codex-")
        expected = self.make_root("upgrade-expected-codex-")
        target = self.make_root("upgrade-target-codex-")

        self.write_file(baseline, ".agents/skills/trellis-finish-work/SKILL.md", "baseline finish-work\n")

        self.write_file(expected, ".agents/skills/brainstorm/SKILL.md", "workflow brainstorm\n")
        self.write_file(expected, ".agents/skills/trellis-finish-work/SKILL.md", "workflow finish-work\n")

        self.write_file(target, ".agents/skills/trellis-finish-work/SKILL.md", "baseline finish-work\n")
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
        self.assertEqual(actions["codex:brainstorm"], "add")
        self.assertEqual(actions["codex:trellis-finish-work"], "replace")

    def test_analyze_upgrade_does_not_manage_trellis_research_agent(self) -> None:
        # MANAGED_ENHANCED_AGENT_NAMES is empty — trellis-research is Trellis-native,
        # not a workflow-managed asset. It must not appear in upgrade findings,
        # even when baseline and expected differ (which would trigger a "replace"
        # if it were managed).
        baseline = self.make_root("upgrade-baseline-claude-agent-")
        expected = self.make_root("upgrade-expected-claude-agent-")
        target = self.make_root("upgrade-target-claude-agent-")

        self.write_file(baseline, ".claude/agents/trellis-research.md", "baseline research\n")
        self.write_file(expected, ".claude/agents/trellis-research.md", "expected research (different)\n")
        self.write_file(target, ".claude/agents/trellis-research.md", "baseline research\n")
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
        self.assertNotIn("claude:agent:research", actions)

    def test_analyze_upgrade_still_ignores_non_managed_opencode_check_agent(self) -> None:
        baseline = self.make_root("upgrade-baseline-opencode-agent-")
        expected = self.make_root("upgrade-expected-opencode-agent-")
        target = self.make_root("upgrade-target-opencode-agent-")

        self.write_file(baseline, ".opencode/agents/trellis-check.md", "baseline check\n")
        self.write_file(expected, ".opencode/agents/trellis-check.md", "baseline check\n")
        self.write_file(target, ".opencode/agents/trellis-check.md", "baseline check\n")
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
        asset_ids = {item["asset_id"] for item in payload["findings"]}
        self.assertNotIn("opencode:agent:check", asset_ids)

    def test_analyze_upgrade_includes_shared_extras_and_structural_risk_summary(self) -> None:
        baseline = self.make_root("upgrade-baseline-shared-extra-")
        expected = self.make_root("upgrade-expected-shared-extra-")
        target = self.make_root("upgrade-target-shared-extra-")

        self.write_file(baseline, "AGENTS.md", "# baseline\n")
        self.write_file(expected, "AGENTS.md", "# header\n<!-- workflow-nl-routing-start -->\nrouting\n<!-- workflow-nl-routing-end -->\n")
        self.write_file(target, "AGENTS.md", "# custom target agents\n")
        self.write_file(expected, ".trellis/workflow-installed.json", '{"ok": true}\n')
        self.write_file(expected, ".trellis/workflow-docs/需求变更管理执行卡.md", "card\n")
        self.write_file(expected, ".trellis/workflow-docs/源码水印与归属证据链执行卡.md", "card2\n")
        self.write_file(expected, "todo.txt", "workflow todo\n")
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
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        report = result.stdout
        self.assertIn("shared-artifact:workflow-installed-record", report)
        self.assertIn("shared-doc:agents-nl-routing-block", report)
        self.assertIn("shared-artifact:todo-reminder-file", report)
        self.assertIn("## 结构性风险提示", report)

    def test_analyze_upgrade_warns_when_merge_dominates(self) -> None:
        baseline = self.make_root("upgrade-baseline-merge-risk-")
        expected = self.make_root("upgrade-expected-merge-risk-")
        target = self.make_root("upgrade-target-merge-risk-")

        self.write_file(baseline, ".claude/commands/trellis/continue.md", "baseline continue\n")
        self.write_file(expected, ".claude/commands/trellis/continue.md", "workflow continue\n")
        self.write_file(target, ".claude/commands/trellis/continue.md", "custom continue\n")

        self.write_file(baseline, ".claude/commands/trellis/check.md", "baseline check\n")
        self.write_file(expected, ".claude/commands/trellis/check.md", "workflow check\n")
        self.write_file(target, ".claude/commands/trellis/check.md", "custom check\n")

        self.write_file(baseline, ".claude/commands/trellis/brainstorm.md", "baseline brainstorm\n")
        self.write_file(expected, ".claude/commands/trellis/brainstorm.md", "workflow brainstorm\n")
        self.write_file(target, ".claude/commands/trellis/brainstorm.md", "custom brainstorm\n")

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
            env=self.latest_env("2.1.0"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("merge 项占主导", result.stdout)

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

    def test_upgrade_check_detects_legacy_and_trellis_duplicate(self) -> None:
        """When both legacy bare-name and trellis-* agent files exist,
        upgrade-compat --check must report the duplicate definition as a conflict."""
        target = self.make_root("upgrade-dup-agent-")
        self.write_file(target, ".claude/commands/trellis/continue.md", "baseline\n")
        self.write_file(target, ".claude/agents/trellis-research.md", "---\nname: trellis-research\n")
        self.write_file(target, ".claude/agents/research.md", "---\nname: research\n")
        self.write_file(target, ".trellis/.version", "0.5.0-rc.3\n")
        self.write_file(target, ".trellis/workflow-installed.json",
                         '{"workflow_version":"0.1.28","cli_types":["claude"]}')

        upgrade_script = COMMANDS_DIR / "upgrade-compat.py"
        merged_env = os.environ.copy()
        merged_env.update(self.latest_env("0.5.0-rc.3"))

        result = subprocess.run(
            [PYTHON, str(upgrade_script), "--check", "--project-root", str(target), "--cli", "claude"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("重复定义", result.stdout)


if __name__ == "__main__":
    unittest.main()
