from __future__ import annotations

import json
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
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(ANALYZE_SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def make_root(self, prefix: str) -> Path:
        root = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(shutil.rmtree, root)
        return root

    def write_file(self, root: Path, rel_path: str, content: str) -> None:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

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

        self.write_file(expected, ".agents/skills/brainstorm/SKILL.md", "workflow brainstorm\n")
        self.write_file(expected, ".agents/skills/finish-work/SKILL.md", "workflow finish-work\n")

        self.write_file(target, ".agents/skills/brainstorm/SKILL.md", "baseline brainstorm\n")
        self.write_file(target, ".agents/skills/finish-work/SKILL.md", "baseline finish-work\n")

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
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["codex:brainstorm"], "replace")
        self.assertEqual(actions["codex:finish-work"], "replace")

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
        )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        actions = {item["asset_id"]: item["action"] for item in payload["findings"]}
        self.assertEqual(actions["claude:retired-command"], "delete")


if __name__ == "__main__":
    unittest.main()
