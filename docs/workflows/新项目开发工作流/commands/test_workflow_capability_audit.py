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


def load_assets_module():
    spec = importlib.util.spec_from_file_location("workflow_capability_assets_test", WORKFLOW_ASSETS)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WorkflowCapabilityAuditTests(unittest.TestCase):
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
        result = self.run_script("--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "newer-version-continue")
        self.assertIn("task_dir", payload)
        self.assertIn("capability_report", payload)
        self.assertGreaterEqual(payload["managed_rows"], 1)
        self.assertGreaterEqual(payload["dependent_rows"], 1)
        self.assertIn(payload["structural_break_judgment"], {"no", "possible"})

    def test_supplemental_capability_updates_same_report(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)

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

    def test_fix_lifecycle_updates_same_report(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script("--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)

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


if __name__ == "__main__":
    raise SystemExit(unittest.main())
