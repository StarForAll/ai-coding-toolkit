#!/usr/bin/env python3
"""Unit tests for workflow-validate-matrix validation runner."""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from constants import SCENARIOS
import validation_runner as vr


class _FakeAssetSpec:
    def __init__(self, asset_id: str, path: str, category: str = "added-command") -> None:
        self.asset_id = asset_id
        self._path = path
        self.category = category

    def locate(self, root: Path) -> Path:
        return root / self._path


class _FakeExtraSpec:
    def __init__(
        self,
        capability: str,
        *,
        claude_paths: tuple[str, ...] = (),
        opencode_paths: tuple[str, ...] = (),
        codex_paths: tuple[str, ...] = (),
        required_substrings: tuple[str, ...] = (),
    ) -> None:
        self.capability = capability
        self.claude_paths = claude_paths
        self.opencode_paths = opencode_paths
        self.codex_paths = codex_paths
        self.required_substrings = required_substrings


class ValidationRunnerTests(unittest.TestCase):
    def _base_assets_module(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            build_managed_asset_specs=lambda cli_types: [],
            build_managed_audit_extra_specs=lambda cli_types: [],
            HELPER_SCRIPTS=["embed_integrity.py", "workflow-state.py"],
            CORE_HELPER_SCRIPTS=["embed_integrity.py"],
            codex_shared_skills_dir=lambda root: root / ".agents" / "skills",
            codex_secondary_skills_dir=lambda root: root / ".codex" / "skills",
        )

    def test_run_install_block_check_requires_non_zero_with_expected_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-block-") as tmp:
            root = Path(tmp)
            process = vr.subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="目标项目不是可执行首次嵌入的初始态\nworkflow-embed-attempt.json",
            )
            with patch.object(vr, "_run_command", return_value=process):
                result = vr.run_install_block_check(
                    root,
                    root,
                    root,
                    "partial-failed-attempt",
                    "outsourcing",
                    "claude,opencode,codex",
                    ["目标项目不是可执行首次嵌入的初始态", "workflow-embed-attempt.json"],
                )

            self.assertTrue(result.success)
            self.assertEqual(result.findings, [])

    def test_run_install_block_check_fails_when_install_unexpectedly_succeeds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-block-") as tmp:
            root = Path(tmp)
            process = vr.subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
            with patch.object(vr, "_run_command", return_value=process):
                result = vr.run_install_block_check(
                    root,
                    root,
                    root,
                    "preinstalled-upgrade-check",
                    "outsourcing",
                    "claude,opencode,codex",
                    ["workflow-installed.json"],
                )

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["step"], "install-workflow-blocked")

    def test_run_post_install_integrity_reports_disabled_baseline_asset_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / ".codex" / "skills" / "parallel").mkdir(parents=True)
            (root / ".codex" / "skills" / "parallel" / "SKILL.md").write_text("parallel", encoding="utf-8")
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "outsourcing",
                        "cli_types": ["codex"],
                        "scripts": ["embed_integrity.py", "workflow-state.py"],
                    }
                ),
                encoding="utf-8",
            )

            fake_assets = self._base_assets_module()
            fake_assets.build_managed_asset_specs = lambda cli_types: [
                _FakeAssetSpec("codex:parallel", ".codex/skills/parallel/SKILL.md", category="disabled-baseline")
            ]
            with patch.object(vr, "_load_workflow_assets_module", return_value=fake_assets):
                result = vr.run_post_install_integrity(root, root, "scenario", "outsourcing", "codex")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["title"], "Disabled baseline asset should be absent: codex:parallel")

    def test_run_post_install_integrity_reports_required_substring_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("no routing markers here", encoding="utf-8")
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "outsourcing",
                        "cli_types": ["claude"],
                        "scripts": ["embed_integrity.py", "workflow-state.py"],
                    }
                ),
                encoding="utf-8",
            )

            fake_assets = self._base_assets_module()
            fake_assets.build_managed_audit_extra_specs = lambda cli_types: [
                _FakeExtraSpec(
                    "shared-doc:agents-nl-routing-block",
                    claude_paths=("AGENTS.md",),
                    required_substrings=("<!-- workflow-nl-routing-start -->",),
                )
            ]
            with patch.object(vr, "_load_workflow_assets_module", return_value=fake_assets):
                result = vr.run_post_install_integrity(root, root, "scenario", "outsourcing", "claude")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["location"], "AGENTS.md")
            self.assertIn("missing substring", result.findings[0]["evidence"][1])

    def test_run_post_install_integrity_uses_profile_specific_script_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "personal",
                        "cli_types": ["claude"],
                        "scripts": ["embed_integrity.py", "workflow-state.py"],
                    }
                ),
                encoding="utf-8",
            )

            fake_assets = self._base_assets_module()
            fake_assets.CORE_HELPER_SCRIPTS = ["embed_integrity.py"]
            with patch.object(vr, "_load_workflow_assets_module", return_value=fake_assets):
                result = vr.run_post_install_integrity(root, root, "scenario", "personal", "claude")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["title"], "workflow-installed.json scripts list mismatch")

    def test_run_post_install_integrity_accepts_codex_backup_in_shared_skills_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / ".agents" / "skills" / ".backup-original").mkdir(parents=True)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "outsourcing",
                        "cli_types": ["codex"],
                        "scripts": ["embed_integrity.py", "workflow-state.py"],
                    }
                ),
                encoding="utf-8",
            )

            fake_assets = self._base_assets_module()
            fake_assets.build_managed_audit_extra_specs = lambda cli_types: [
                _FakeExtraSpec(
                    "shared-state:backup-original-preservation",
                    codex_paths=(".codex/skills/.backup-original",),
                )
            ]
            with patch.object(vr, "_load_workflow_assets_module", return_value=fake_assets):
                result = vr.run_post_install_integrity(root, root, "scenario", "outsourcing", "codex")

            self.assertTrue(result.success, msg=result.findings)

    def test_run_post_install_integrity_uses_default_profile_not_literal_outsourcing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "team",
                        "cli_types": ["claude"],
                        "scripts": ["full-only.py"],
                    }
                ),
                encoding="utf-8",
            )

            fake_assets = self._base_assets_module()
            fake_assets.DEFAULT_PROFILE = "team"
            fake_assets.HELPER_SCRIPTS = ["full-only.py"]
            fake_assets.CORE_HELPER_SCRIPTS = ["core-only.py"]
            with patch.object(vr, "_load_workflow_assets_module", return_value=fake_assets):
                result = vr.run_post_install_integrity(root, root, "scenario", "team", "claude")

            self.assertTrue(result.success, msg=result.findings)

    def test_run_post_install_integrity_fails_closed_when_asset_contract_load_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-post-") as tmp:
            root = Path(tmp)
            (root / ".trellis").mkdir()
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.1.28",
                        "workflow_schema_version": "3",
                        "profile": "outsourcing",
                        "cli_types": ["claude"],
                        "scripts": ["embed_integrity.py", "workflow-state.py"],
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(vr, "_load_workflow_assets_module", side_effect=RuntimeError("boom")):
                result = vr.run_post_install_integrity(root, root, "scenario", "outsourcing", "claude")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["title"], "Unable to load workflow asset contract")

    def test_run_embed_integrity_reports_missing_script(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-embed-") as tmp:
            root = Path(tmp)

            result = vr.run_embed_integrity(root, "scenario")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["title"], "embed_integrity.py missing after install")

    def test_run_embed_integrity_reports_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-embed-") as tmp:
            root = Path(tmp)
            script = root / ".trellis" / "scripts" / "workflow" / "embed_integrity.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")

            with patch.object(vr, "_run_command", side_effect=vr.subprocess.TimeoutExpired(cmd=["x"], timeout=1)):
                result = vr.run_embed_integrity(root, "scenario")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["step"], "embed-integrity")

    def test_run_embed_integrity_reports_non_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-embed-") as tmp:
            root = Path(tmp)
            script = root / ".trellis" / "scripts" / "workflow" / "embed_integrity.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")

            process = vr.subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="broken")
            with patch.object(vr, "_run_command", return_value=process):
                result = vr.run_embed_integrity(root, "scenario")

            self.assertFalse(result.success)
            self.assertEqual(result.findings[0]["title"], "embed_integrity.py reported invalid embed state")

    def test_run_embed_integrity_succeeds_on_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-embed-") as tmp:
            root = Path(tmp)
            script = root / ".trellis" / "scripts" / "workflow" / "embed_integrity.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")

            process = vr.subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
            with patch.object(vr, "_run_command", return_value=process):
                result = vr.run_embed_integrity(root, "scenario")

            self.assertTrue(result.success)
            self.assertEqual(result.findings, [])

    def test_preinstalled_upgrade_check_legacy_schema_does_not_fail_embed_integrity_path(self) -> None:
        scenario = next(item for item in SCENARIOS if item["name"] == "preinstalled-upgrade-check")
        self.assertTrue(scenario["run_post_checks"])
        self.assertTrue(scenario["run_upgrade_compat"])
        self.assertEqual(scenario["expected_post_status"], "ALREADY_VALID_EMBEDDED")

        with tempfile.TemporaryDirectory(prefix="wvm-embed-legacy-") as tmp:
            root = Path(tmp)
            script = root / ".trellis" / "scripts" / "workflow" / "embed_integrity.py"
            script.parent.mkdir(parents=True)
            script.write_text("print('ok')\n", encoding="utf-8")
            (root / ".trellis" / "workflow-installed.json").write_text(
                json.dumps(
                    {
                        "workflow_version": "0.0.0-matrix-legacy",
                        "workflow_schema_version": "2",
                        "profile": "outsourcing",
                        "cli_types": ["claude", "opencode", "codex"],
                    }
                ),
                encoding="utf-8",
            )

            process = vr.subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
            with patch.object(vr, "_run_command", return_value=process):
                result = vr.run_embed_integrity(root, scenario["name"])

            self.assertTrue(result.success)
            self.assertEqual(result.findings, [])

    def test_load_workflow_assets_module_caches_by_resolved_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wvm-assets-") as tmp:
            root = Path(tmp)
            commands_dir = root / "commands"
            commands_dir.mkdir(parents=True)
            assets_path = commands_dir / "workflow_assets.py"
            assets_path.write_text(
                "DEFAULT_PROFILE = 'outsourcing'\nHELPER_SCRIPTS = []\nCORE_HELPER_SCRIPTS = []\n"
                "def build_managed_asset_specs(cli_types):\n    return []\n"
                "def build_managed_audit_extra_specs(cli_types):\n    return []\n",
                encoding="utf-8",
            )

            vr._WORKFLOW_ASSETS_MODULE_CACHE.clear()
            first = vr._load_workflow_assets_module(root)
            second = vr._load_workflow_assets_module(root)

            self.assertIs(first, second)

    def test_run_validations_collects_post_install_diagnostics_after_first_failure(self) -> None:
        scenario = {
            "name": "scenario",
            "profile": "outsourcing",
            "cli": "claude",
            "expected_pre_status": "INITIAL_BASELINE_READY",
            "expected_post_status": "ALREADY_VALID_EMBEDDED",
            "run_install": True,
            "run_post_checks": True,
            "run_upgrade_compat": True,
        }

        with tempfile.TemporaryDirectory(prefix="wvm-collect-") as tmp:
            root = Path(tmp)
            success = vr.ValidationResult(step="ok", success=True)
            fail_integrity = vr.ValidationResult(step="post-install-integrity", success=False, error="integrity")
            fail_post = vr.ValidationResult(step="detect-embed-state-post", success=False, error="post")
            fail_embed = vr.ValidationResult(step="embed-integrity", success=False, error="embed")
            fail_route = vr.ValidationResult(step="workflow-state", success=False, error="route")
            fail_upgrade = vr.ValidationResult(step="upgrade-compat", success=False, error="upgrade")

            with (
                patch.object(vr, "run_detect_embed_state", side_effect=[success, fail_post]),
                patch.object(vr, "run_install_workflow", return_value=success),
                patch.object(vr, "run_post_install_integrity", return_value=fail_integrity),
                patch.object(vr, "run_embed_integrity", return_value=fail_embed),
                patch.object(vr, "run_workflow_state", return_value=fail_route),
                patch.object(vr, "run_upgrade_compat", return_value=fail_upgrade),
            ):
                results = vr.run_validations(root, root, root, scenario)

            self.assertEqual(
                [result.step for result in results],
                [
                    "ok",
                    "ok",
                    "post-install-integrity",
                    "detect-embed-state-post",
                    "embed-integrity",
                    "workflow-state",
                    "upgrade-compat",
                ],
            )
            self.assertEqual(sum(1 for result in results if not result.success), 5)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
