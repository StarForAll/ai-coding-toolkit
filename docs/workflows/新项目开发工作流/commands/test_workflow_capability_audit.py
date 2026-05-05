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
DEVELOPER_FILE = REPO_ROOT / ".trellis" / ".developer"


def load_assets_module():
    spec = importlib.util.spec_from_file_location("workflow_capability_assets_test", WORKFLOW_ASSETS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_script_module():
    spec = importlib.util.spec_from_file_location("workflow_capability_audit_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(COMMANDS_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
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
        self._pre_workflow_assets = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self._pre_developer = DEVELOPER_FILE.read_text(encoding="utf-8") if DEVELOPER_FILE.is_file() else None
        self._fixture_dirs: list[Path] = []
        self._temp_dirs: list[Path] = []

    def tearDown(self) -> None:
        if TRELLIS_TASKS_DIR.is_dir():
            for d in TRELLIS_TASKS_DIR.iterdir():
                if d.name not in self._pre_task_dirs:
                    shutil.rmtree(d, ignore_errors=True)
        if self._pre_current_task is not None:
            CURRENT_TASK_FILE.write_text(self._pre_current_task, encoding="utf-8")
        elif CURRENT_TASK_FILE.is_file():
            CURRENT_TASK_FILE.unlink()
        WORKFLOW_ASSETS.write_text(self._pre_workflow_assets, encoding="utf-8")
        if self._pre_developer is not None:
            DEVELOPER_FILE.write_text(self._pre_developer, encoding="utf-8")
        elif DEVELOPER_FILE.is_file():
            DEVELOPER_FILE.unlink()
        for d in self._fixture_dirs:
            shutil.rmtree(d, ignore_errors=True)
        for d in self._temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _track_fixtures_from_payload(self, payload: dict) -> None:
        for key in ("a_root", "b_root"):
            path = Path(payload[key])
            if path.exists():
                self._fixture_dirs.append(path)

    def _set_repo_developer(self, name: str) -> None:
        DEVELOPER_FILE.write_text(f"name={name}\n", encoding="utf-8")

    def _remove_compatible_anchor(self) -> None:
        content = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "', content)
        content = content.replace('COMPATIBLE_TRELLIS_VERSION = "0.4.0"\n', "", 1)
        WORKFLOW_ASSETS.write_text(content, encoding="utf-8")

    def _make_fake_trellis_bin(self, version: str = "9.9.9", init_exit: int = 42) -> Path:
        bin_dir = Path(tempfile.mkdtemp(prefix="workflow-capability-audit-bin-"))
        self._temp_dirs.append(bin_dir)
        trellis_path = bin_dir / "trellis"
        trellis_path.write_text(
            "\n".join(
                [
                    "#!/bin/sh",
                    'if [ "$1" = "-v" ]; then',
                    f'  echo "{version}"',
                    "  exit 0",
                    "fi",
                    'echo "simulated trellis init failure" >&2',
                    f"exit {init_exit}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        trellis_path.chmod(0o755)
        return bin_dir

    def _create_task_dir(self, dir_name: str, title: str, *, children: list[str] | None = None) -> Path:
        task_dir = TRELLIS_TASKS_DIR / dir_name
        task_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "title": title,
            "children": children or [],
            "parent": None,
        }
        (task_dir / "task.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return task_dir

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

    def test_missing_anchor_rejects_invalid_supplied_version_without_writing_source(self) -> None:
        self._remove_compatible_anchor()
        result = self.run_script("--compatible-trellis-version", "not-a-version", "--json")
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "version-parse-error")
        current_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "not-a-version"', current_text)
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "', current_text)

    def test_update_compatible_anchor_replaces_existing_value(self) -> None:
        module = load_script_module()
        module.update_compatible_anchor("0.5.0")
        current_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "0.5.0"', current_text)
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "0.4.0"', current_text)

    def test_update_compatible_anchor_inserts_after_schema_line_when_missing(self) -> None:
        module = load_script_module()
        self._remove_compatible_anchor()
        module.update_compatible_anchor("0.5.0")
        lines = WORKFLOW_ASSETS.read_text(encoding="utf-8").splitlines()
        schema_index = lines.index('WORKFLOW_SCHEMA_VERSION = "2"  # 安装记录 JSON 的 schema 版本，安装记录结构变化时递增')
        self.assertEqual(lines[schema_index + 1], 'COMPATIBLE_TRELLIS_VERSION = "0.5.0"')

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

    def test_full_audit_uses_repo_developer_identity_for_fresh_fixtures(self) -> None:
        assets = load_assets_module()
        self._set_repo_developer("audit-dev")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        for key in ("a_root", "b_root"):
            developer_text = (Path(payload[key]) / ".trellis" / ".developer").read_text(encoding="utf-8")
            self.assertIn("name=audit-dev", developer_text)

    def test_full_audit_failure_cleans_up_created_task_and_temp_fixtures(self) -> None:
        fake_bin = self._make_fake_trellis_bin()
        controlled_tmp = Path(tempfile.mkdtemp(prefix="workflow-capability-audit-tmp-"))
        self._temp_dirs.append(controlled_tmp)
        env = {
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "TMPDIR": str(controlled_tmp),
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        current_task = CURRENT_TASK_FILE.read_text(encoding="utf-8") if CURRENT_TASK_FILE.is_file() else None
        self.assertEqual(current_task, self._pre_current_task)
        current_task_dirs = set(d.name for d in TRELLIS_TASKS_DIR.iterdir()) if TRELLIS_TASKS_DIR.is_dir() else set()
        self.assertEqual(current_task_dirs, self._pre_task_dirs)
        self.assertEqual(list(controlled_tmp.iterdir()), [])

    def test_full_audit_creates_child_task_when_current_task_is_workflow_audit(self) -> None:
        assets = load_assets_module()
        current_task_dir = self._create_task_dir(
            "05-03-existing-workflow-audit",
            "workflow-audit: 新项目开发工作流",
        )
        CURRENT_TASK_FILE.write_text(f".trellis/tasks/{current_task_dir.name}", encoding="utf-8")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        task_json = REPO_ROOT / payload["task_dir"] / "task.json"
        task_data = json.loads(task_json.read_text(encoding="utf-8"))
        self.assertEqual(task_data["parent"], current_task_dir.name)

    def test_full_audit_stops_when_current_task_is_workflow_capability_audit(self) -> None:
        assets = load_assets_module()
        current_task_dir = self._create_task_dir(
            "05-03-existing-workflow-capability-audit",
            "workflow-capability-audit: 新项目开发工作流",
        )
        CURRENT_TASK_FILE.write_text(f".trellis/tasks/{current_task_dir.name}", encoding="utf-8")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("existing workflow-capability-audit task", result.stderr)
        current_task_dirs = set(d.name for d in TRELLIS_TASKS_DIR.iterdir()) if TRELLIS_TASKS_DIR.is_dir() else set()
        self.assertEqual(current_task_dirs, self._pre_task_dirs | {current_task_dir.name})

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

    def test_fix_lifecycle_rejects_task_dir_outside_audit_tasks(self) -> None:
        outside_dir = Path(tempfile.mkdtemp(prefix="workflow-capability-audit-outside-"))
        self._temp_dirs.append(outside_dir)
        rel_path = os.path.relpath(outside_dir, REPO_ROOT)
        result = self.run_script("--task-dir", rel_path, "--finalize-fixture-destruction", "--json")
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn(".trellis/tasks", result.stderr)

    def test_fix_lifecycle_rejects_workflow_audit_task_dir(self) -> None:
        task_dir = self._create_task_dir(
            "05-03-existing-workflow-audit-task",
            "workflow-audit: 新项目开发工作流",
        )
        (task_dir / "capability-report.md").write_text(
            "\n".join(
                [
                    "## Confirmed Fix Scope",
                    "- none yet",
                    "",
                    "## Applied Corrections",
                    "- none yet",
                    "",
                    "## Post-Fix Revalidation",
                    "- none yet",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = self.run_script(
            "--task-dir",
            f".trellis/tasks/{task_dir.name}",
            "--confirm-fix-scope",
            "should-not-apply",
            "--json",
        )
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("workflow-capability-audit task", result.stderr)

    def test_fix_lifecycle_requires_completed_fix_evidence_before_fixture_destruction(self) -> None:
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
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertNotEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self.assertTrue(Path(payload["a_root"]).exists())
        self.assertTrue(Path(payload["b_root"]).exists())
        report_text = (REPO_ROOT / payload["capability_report"]).read_text(encoding="utf-8")
        self.assertIn("- Destroyed: no", report_text)
        self.assertIn("- Final destruction confirmed by user: no", report_text)

    def test_supplemental_validation_reports_missing_section_heading_cleanly(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        report_path = REPO_ROOT / payload["capability_report"]
        report_text = report_path.read_text(encoding="utf-8").replace("## Structural-Break Judgment", "## Removed Structural Break")
        report_path.write_text(report_text, encoding="utf-8")

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
        self.assertNotEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self.assertIn("Missing required section heading", second.stderr)

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

    def test_shared_skills_deployment_carrier_appears_in_dependent_surface(self) -> None:
        """shared-skills-deployment-carrier (TN-007) must appear in the dependent surface matrix."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)

        # Assert dependent_rows >= 7 (was 6 before the shared-skills carrier was added)
        self.assertGreaterEqual(payload["dependent_rows"], 7)

        # Read the generated capability-report.md
        report_path = REPO_ROOT / payload["capability_report"]
        report_text = report_path.read_text(encoding="utf-8")

        # Assert shared-skills-deployment-carrier appears in the report
        self.assertIn("shared-skills-deployment-carrier", report_text)

        # Extract the dependent surface matrix section
        dependent_section = _extract_section(report_text, "## Workflow-Dependent Trellis-Native Surface Matrix")
        self.assertIn("shared-skills-deployment-carrier", dependent_section)

        # Parse matrix rows to inspect classifications
        module = load_script_module()
        rows = module.parse_matrix_rows(dependent_section)
        shared_row = None
        for row in rows:
            if row["capability"] == "shared-skills-deployment-carrier":
                shared_row = row
                break
        self.assertIsNotNone(shared_row, "shared-skills-deployment-carrier row must exist in dependent surface matrix")

        # Claude has no paths, so classification must be not-applicable
        self.assertEqual(shared_row["claude_classification"], "not-applicable")
        # OpenCode and Codex both use .agents/skills/ as shared deployment carrier (created by trellis init with --opencode and/or --codex)
        self.assertEqual(shared_row["opencode_classification"], "adopted-compatible")
        self.assertEqual(shared_row["codex_classification"], "adopted-compatible")

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
