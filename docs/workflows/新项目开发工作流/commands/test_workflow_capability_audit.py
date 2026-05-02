#!/usr/bin/env python3
"""Tests for workflow-capability-audit execution helpers."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
SCRIPT = COMMANDS_DIR / "workflow-capability-audit.py"
WORKFLOW_ASSETS = COMMANDS_DIR / "workflow_assets.py"
TRELLIS_TASKS_DIR = REPO_ROOT / ".trellis" / "tasks"
CURRENT_TASK_FILE = REPO_ROOT / ".trellis" / ".current-task"


def load_assets_module():
    spec = importlib.util.spec_from_file_location("workflow_capability_assets_test", WORKFLOW_ASSETS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _extract_section(text: str, heading: str) -> str:
    """Extract a markdown section from heading to the next ## heading or EOF."""
    idx = text.find(heading)
    if idx == -1:
        return ""
    start = idx + len(heading)
    next_section = text.find("\n## ", start)
    if next_section == -1:
        next_section = len(text)
    return text[idx:next_section]


class WorkflowCapabilityAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self._pre_task_dirs = set(d.name for d in TRELLIS_TASKS_DIR.iterdir()) if TRELLIS_TASKS_DIR.is_dir() else set()
        self._pre_current_task = CURRENT_TASK_FILE.read_text(encoding="utf-8") if CURRENT_TASK_FILE.is_file() else None
        self._fixture_dirs: list[Path] = []

    def tearDown(self) -> None:
        if TRELLIS_TASKS_DIR.is_dir():
            for d in TRELLIS_TASKS_DIR.iterdir():
                if d.name not in self._pre_task_dirs:
                    shutil.rmtree(d, ignore_errors=True)
        if self._pre_current_task is not None:
            CURRENT_TASK_FILE.write_text(self._pre_current_task, encoding="utf-8")
        elif CURRENT_TASK_FILE.is_file():
            CURRENT_TASK_FILE.unlink()
        for d in self._fixture_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _track_fixtures_from_payload(self, payload: dict) -> None:
        for key in ("a_root", "b_root"):
            path = Path(payload[key])
            if path.exists():
                self._fixture_dirs.append(path)

    def run_script(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [PYTHON, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

    def test_compare_trellis_versions_orders_prerelease_before_stable(self) -> None:
        assets = load_assets_module()
        self.assertEqual(assets.compare_trellis_versions("0.4.0-beta.1", "0.4.0-rc.1"), -1)
        self.assertEqual(assets.compare_trellis_versions("0.4.0-rc.1", "0.4.0"), -1)
        self.assertEqual(assets.compare_trellis_versions("0.4.0", "0.4.0"), 0)
        self.assertEqual(assets.compare_trellis_versions("0.4.1", "0.4.0"), 1)

    def test_compare_trellis_versions_returns_none_for_unparseable_values(self) -> None:
        assets = load_assets_module()
        self.assertIsNone(assets.compare_trellis_versions("not-a-version", "0.4.0"))
        self.assertIsNone(assets.compare_trellis_versions("0.4.0", "unknown"))

    def test_script_stops_on_equal_version(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: assets.COMPATIBLE_TRELLIS_VERSION,
        }
        result = self.run_script("--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "equal-version-stop")
        self.assertFalse(payload["task_created"])

    def test_script_stops_on_older_version(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "0.3.9",
        }
        result = self.run_script("--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "older-version-block")

    def test_script_stops_on_version_parse_error(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "not-a-version",
        }
        result = self.run_script("--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "version-parse-error")

    def test_script_enters_upgrade_path_when_current_version_is_newer(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "newer-version-continue")
        self.assertIn("task_dir", payload)
        self.assertIn("capability_report", payload)
        self.assertGreaterEqual(payload["managed_rows"], 1)
        self.assertGreaterEqual(payload["dependent_rows"], 1)
        self.assertIn(payload["structural_break_judgment"], {"no", "possible"})
        self._track_fixtures_from_payload(payload)

    def test_full_audit_fails_when_current_cli_is_missing(self) -> None:
        """Omitting --current-cli must fail before creating fixtures or a task."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("--current-cli is required", result.stderr)

    def test_supplemental_capability_updates_same_report(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--supplemental-capability",
            "custom-supplemental-capability",
            "--surface",
            "workflow-dependent-native",
            "--mechanism",
            "Supplemental capability confirmed from current A/B evidence.",
            "--claude-path",
            "AGENTS.md",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["mode"], "supplemental-confirmed")
        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("custom-supplemental-capability", report_text)
        self.assertIn("supplemental-confirmed", report_text)

    def test_supplemental_confirmed_preserves_structural_break_single_line_format(self) -> None:
        """After supplemental-confirmed, Structural-Break Judgment must stay single-line Why/Required next action."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9"}
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--supplemental-capability",
            "fmt-check-capability",
            "--surface",
            "workflow-dependent-native",
            "--mechanism",
            "Format drift test: supplemental capability.",
            "--claude-path",
            "AGENTS.md",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["mode"], "supplemental-confirmed")

        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")

        sb_section = _extract_section(report_text, "## Structural-Break Judgment")
        self.assertIn(sb_section, report_text)
        self.assertRegex(sb_section, r"(?m)^- Why: .+", "Why must be single-line")
        self.assertRegex(sb_section, r"(?m)^- Required next action: .+", "Required next action must be single-line")
        self.assertNotRegex(sb_section, r"(?m)^- Why:\s*$", "Old two-line Why split must not appear")
        self.assertNotRegex(sb_section, r"(?m)^- Required next action:\s*$", "Old two-line Required next action split must not appear")

    def test_supplemental_unconfirmed_preserves_structural_break_single_line_format(self) -> None:
        """After supplemental-unconfirmed, Structural-Break Judgment must stay single-line Why/Required next action."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9"}
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--supplemental-capability",
            "no-evidence-capability",
            "--surface",
            "workflow-dependent-native",
            "--mechanism",
            "No evidence in either A or B.",
            "--claude-path",
            "nonexistent-file.xyz",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["mode"], "supplemental-unconfirmed")

        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")

        sb_section = _extract_section(report_text, "## Structural-Break Judgment")
        self.assertRegex(sb_section, r"(?m)^- Why: .+", "Why must be single-line")
        self.assertRegex(sb_section, r"(?m)^- Required next action: .+", "Required next action must be single-line")
        self.assertNotRegex(sb_section, r"(?m)^- Why:\s*$")
        self.assertNotRegex(sb_section, r"(?m)^- Required next action:\s*$")

    def test_supplemental_capability_not_in_A_but_in_B_confirmed_as_unclear(self) -> None:
        """workflow-dependent-native surface: path exists in B but not A → confirmed as unclear."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--supplemental-capability",
            "workflow-added-command-carrier",
            "--surface",
            "workflow-dependent-native",
            "--mechanism",
            "Workflow-added commands that the Trellis baseline does not ship.",
            "--claude-path",
            ".claude/commands/trellis/delivery.md",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["mode"], "supplemental-confirmed",
                         msg=f"Expected supplemental-confirmed, got {second_payload.get('mode')}")
        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("workflow-added-command-carrier", report_text)
        self.assertIn("supplemental-confirmed", report_text)
        self.assertIn("| unclear |", report_text)
        self.assertRegex(report_text, r"(?m)^- Why: .+", msg="Why must be single-line, not split across two lines")
        self.assertRegex(report_text, r"(?m)^- Required next action: .+", msg="Required next action must be single-line")
        self.assertNotRegex(report_text, r"(?m)^- Why:\s*$", msg="Old split Why format must not appear")
        self.assertNotRegex(report_text, r"(?m)^- Required next action:\s*$", msg="Old split Required next action format must not appear")

    def test_fix_lifecycle_updates_same_report(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirm patch markers and capability matrix updates.",
            "--record-correction",
            "Updated workflow source for Trellis version-upgrade compatibility.",
            "--record-revalidation",
            "Revalidated capability report after confirmed correction.",
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        second_payload = json.loads(second.stdout)
        self.assertEqual(second_payload["mode"], "fix-lifecycle-updated")
        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Confirm patch markers and capability matrix updates.", report_text)
        self.assertIn("Updated workflow source for Trellis version-upgrade compatibility.", report_text)
        self.assertIn("Revalidated capability report after confirmed correction.", report_text)
        self.assertIn("- Destroyed: yes", report_text)
        self.assertIn("- Final destruction confirmed by user: yes", report_text)

    def test_initial_report_avoids_angle_bracket_placeholders_in_lifecycle_sections(self) -> None:
        """Initial report must use 'none yet', not angle-bracket placeholders, for lifecycle sections."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9"}
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        report_path = REPO_ROOT / payload["capability_report"]
        report_text = report_path.read_text(encoding="utf-8")

        for section_heading in ["## Confirmed Fix Scope", "## Applied Corrections", "## Post-Fix Revalidation"]:
            section = _extract_section(report_text, section_heading)
            self.assertIn("- none yet", section, f"{section_heading} must contain '- none yet'")
            self.assertNotRegex(section, r"<.+>", f"{section_heading} must not contain angle-bracket placeholders")

    def test_print_stop_human_includes_next_action_section(self) -> None:
        """Human-readable version-gate stop output must include the ### Next Action section."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: assets.COMPATIBLE_TRELLIS_VERSION}
        result = self.run_script(env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        output = result.stdout
        self.assertIn("### Next Action", output)
        self.assertIn("Update COMPATIBLE_TRELLIS_VERSION", output)
        for section in ["## Version Gate Stop", "### Why Execution Stops Here", "### Task Creation", "### Next Action"]:
            self.assertIn(section, output)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
