from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = (
    "/ops/softwares/python/bin/python3"
    if Path("/ops/softwares/python/bin/python3").exists()
    else shutil.which("python3") or shutil.which("python")
)
CLI = REPO_ROOT / "trellis-library" / "cli.py"
ANALYZE_SCRIPT = REPO_ROOT / "trellis-library" / "scripts" / "assembly" / "analyze-library-pull.py"
GO_PACKAGE_ASSET = "spec.technologies.languages.go-package-structure"
GO_PACKAGE_OVERVIEW = (
    "specs/technologies/languages/go/package-structure/overview.md"
)
GO_PACKAGE_TARGET_OVERVIEW = (
    "spec/technologies/languages/go/package-structure/overview.md"
)
GO_PACKAGE_TARGET_DIR = "spec/technologies/languages/go/package-structure"


class TrellisLibraryCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(CLI), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def create_library_copy(self, root: str) -> Path:
        library_copy = Path(root) / "trellis-library-copy"
        shutil.copytree(REPO_ROOT / "trellis-library", library_copy)
        return library_copy

    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, str(script), *args],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def load_script_module(self, path: Path, module_name: str):
        spec = importlib.util.spec_from_file_location(module_name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_main_help_lists_supported_commands(self) -> None:
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("validate", result.stdout)
        self.assertIn("assemble", result.stdout)
        self.assertIn("sync", result.stdout)

    def test_sync_help_lists_modes(self) -> None:
        result = self.run_cli("sync", "--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("downstream", result.stdout)
        self.assertIn("diff", result.stdout)
        self.assertIn("propose", result.stdout)
        self.assertIn("apply", result.stdout)

    def test_sync_requires_mode(self) -> None:
        result = self.run_cli("sync")

        self.assertEqual(result.returncode, 1)
        self.assertIn("sync requires --mode", result.stderr)

    def test_sync_rejects_unknown_mode(self) -> None:
        result = self.run_cli("sync", "--mode", "unknown")

        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown sync mode", result.stderr)

    def test_validate_command_passes_through_to_validator(self) -> None:
        result = self.run_cli("validate", "--library-root", "trellis-library", "--strict-warnings")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        # returncode==0 is sufficient; output contains INFO/WARN when findings exist
        self.assertNotIn("ERROR", result.stdout)

    def test_validate_command_does_not_flag_nested_assets_under_registered_directory_assets(self) -> None:
        result = self.run_cli("validate", "--library-root", "trellis-library", "--strict-warnings")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotIn(
            "registered-asset-not-discoverable",
            result.stdout,
            msg=result.stdout + result.stderr,
        )

    def test_validate_command_does_not_fail_on_mtime_only_related_asset_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            library_root = self.create_library_copy(temp_root)
            source_path = library_root / "specs/universal-domains/contracts/api-contracts"
            target_path = library_root / "templates/universal-domains/contracts/api-contract-template.md"

            stale_target_time = source_path.stat().st_mtime - 120
            os.utime(target_path, (stale_target_time, stale_target_time))

            result = self.run_cli("validate", "--library-root", str(library_root), "--strict-warnings")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_assemble_command_runs_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            result = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
                "--dry-run",
            )

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("COPY", result.stdout)
        self.assertIn("DRY RUN", result.stdout)
        self.assertIn(".trellis/spec/", result.stdout)
        self.assertNotIn(".trellis/specs/", result.stdout)

    def test_assemble_command_writes_specs_into_dot_trellis_spec_and_records_lock_path(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            result = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            legacy_target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_OVERVIEW
            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            lock_data = json.loads(json.dumps({}))
            target_exists = target_file.exists()
            legacy_exists = legacy_target_file.exists()
            if lock_path.exists():
                import yaml

                lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertTrue(target_exists, msg=result.stdout + result.stderr)
        self.assertFalse(legacy_exists, msg=result.stdout + result.stderr)
        self.assertIn(
            ".trellis/" + GO_PACKAGE_TARGET_DIR,
            [item["target_path"] for item in lock_data["imports"]],
        )

    def test_assemble_command_does_not_auto_import_script_dependencies_for_specs(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            result = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                "spec.universal-domains.project-governance.library-sync-governance",
            )

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            script_asset_path = (
                Path(target_dir)
                / ".trellis"
                / "library-assets"
                / "scripts"
                / "validation"
                / "validate-library-sync.py"
            )
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertFalse(script_asset_path.exists(), msg=result.stdout + result.stderr)
        self.assertNotIn(
            "script.validation.validate-library-sync",
            lock_data["selection"]["assets"],
        )
        self.assertFalse(
            any(item["type"] == "script" for item in lock_data["imports"]),
            msg=lock_data,
        )

    def test_sync_downstream_mode_runs_against_assembled_target(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            sync = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--dry-run",
            )

        self.assertEqual(sync.returncode, 0, msg=sync.stdout + sync.stderr)
        self.assertIn("unchanged:", sync.stdout)

    def test_sync_diff_mode_reports_modified_eligible_spec(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            original = target_file.read_text(encoding="utf-8")
            target_file.write_text(
                original + "\nGeneralized testing note for upstream proposal coverage.\n",
                encoding="utf-8",
            )

            diff = self.run_cli(
                "sync",
                "--mode",
                "diff",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--json",
                "--update-lock",
            )

        self.assertEqual(diff.returncode, 2, msg=diff.stdout + diff.stderr)
        payload = json.loads(diff.stdout)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["asset_id"], GO_PACKAGE_ASSET)
        self.assertEqual(payload[0]["diff_status"], "modified")
        self.assertTrue(payload[0]["contribution_eligible"])

    def test_sync_propose_mode_generates_report_and_patch_for_modified_spec(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            target_file.write_text(
                target_file.read_text(encoding="utf-8")
                + "\nGeneralized testing note for upstream proposal coverage.\n",
                encoding="utf-8",
            )

            diff = self.run_cli(
                "sync",
                "--mode",
                "diff",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--update-lock",
            )
            self.assertEqual(diff.returncode, 2, msg=diff.stdout + diff.stderr)

            report_path = Path(target_dir) / "proposal-report.md"
            patch_path = Path(target_dir) / "proposal.patch"
            propose = self.run_cli(
                "sync",
                "--mode",
                "propose",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--scope",
                "file",
                "--file",
                "overview.md",
                "--report-out",
                str(report_path),
                "--patch-out",
                str(patch_path),
                "--json",
                "--update-lock",
            )

            report = report_path.read_text(encoding="utf-8")
            patch = patch_path.read_text(encoding="utf-8")

        self.assertEqual(propose.returncode, 0, msg=propose.stdout + propose.stderr)
        payload = json.loads(propose.stdout)
        self.assertEqual(payload["target_asset_id"], GO_PACKAGE_ASSET)
        self.assertEqual(payload["selected_scope"], "file")
        self.assertIn("overview.md", payload["selected_items"])
        self.assertIn("Generalized testing note", patch)
        self.assertIn("Selected Items", report)

    def test_sync_propose_mode_recomputes_eligibility_and_rejects_private_hint_spec_even_with_stale_lock_cache(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            target_file.write_text(
                target_file.read_text(encoding="utf-8")
                + "\nThis project-specific customer workflow should stay local.\n",
                encoding="utf-8",
            )

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_item = next(
                item for item in lock_data["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            import_item["local_state"] = "modified"
            import_item["contribution"]["eligible"] = True
            lock_path.write_text(
                yaml.safe_dump(lock_data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            propose = self.run_cli(
                "sync",
                "--mode",
                "propose",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--scope",
                "file",
                "--file",
                "overview.md",
            )

        self.assertNotEqual(propose.returncode, 0, msg=propose.stdout + propose.stderr)
        self.assertIn("not marked as contribution eligible", propose.stderr)

    def test_sync_propose_mode_recomputes_eligibility_and_ignores_stale_false_cache(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            target_file.write_text(
                target_file.read_text(encoding="utf-8")
                + "\nGeneralized testing note for proposal recomputation.\n",
                encoding="utf-8",
            )

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_item = next(
                item for item in lock_data["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            import_item["local_state"] = "modified"
            import_item["contribution"]["eligible"] = False
            lock_path.write_text(
                yaml.safe_dump(lock_data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            propose = self.run_cli(
                "sync",
                "--mode",
                "propose",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--scope",
                "file",
                "--file",
                "overview.md",
                "--json",
            )

        self.assertEqual(propose.returncode, 0, msg=propose.stdout + propose.stderr)
        payload = json.loads(propose.stdout)
        self.assertTrue(payload["contribution_eligible"])

    def test_sync_directory_file_set_drift_is_classified_as_diverged_consistently(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_dir_path = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_DIR
            (target_dir_path / "extra-local-file.md").write_text(
                "Extra local file\n",
                encoding="utf-8",
            )

            sync = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--dry-run",
                "--json",
            )
            diff = self.run_cli(
                "sync",
                "--mode",
                "diff",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--json",
            )

        self.assertEqual(sync.returncode, 2, msg=sync.stdout + sync.stderr)
        self.assertEqual(diff.returncode, 2, msg=diff.stdout + diff.stderr)
        sync_payload = json.loads(sync.stdout.split("\n\n", 1)[0])
        diff_payload = json.loads(diff.stdout)
        self.assertEqual(sync_payload[0]["result"], "blocked-diverged")
        self.assertEqual(diff_payload[0]["diff_status"], "diverged")

    def test_determine_local_state_marks_directory_file_set_drift_as_diverged(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_item = next(
                item for item in lock_data["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            target_path = Path(target_dir) / import_item["target_path"]
            (target_path / "extra-local-file.md").write_text("Extra local file\n", encoding="utf-8")

            module = self.load_script_module(
                REPO_ROOT / "trellis-library" / "scripts" / "sync" / "sync-library-assets.py",
                "sync_library_assets_test",
            )
            local_state = module.determine_local_state(import_item, target_path)

        self.assertEqual(local_state, "diverged")

    def test_sync_blocked_modified_persists_observed_checksum_and_block_metadata_without_overwriting_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_before = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_before = next(
                item for item in lock_before["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            baseline_checksum = import_before["last_local_checksum"]

            target_file = Path(target_dir) / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            target_file.write_text(
                target_file.read_text(encoding="utf-8")
                + "\nBlocked sync metadata coverage note.\n",
                encoding="utf-8",
            )

            sync1 = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(sync1.returncode, 2, msg=sync1.stdout + sync1.stderr)

            lock_after_first = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_after_first = next(
                item for item in lock_after_first["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )

            sync2 = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(sync2.returncode, 2, msg=sync2.stdout + sync2.stderr)

            lock_after_second = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_after_second = next(
                item for item in lock_after_second["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )

        self.assertEqual(import_after_first["local_state"], "modified")
        self.assertEqual(import_after_first["last_local_checksum"], baseline_checksum)
        self.assertNotEqual(import_after_first.get("last_observed_checksum", ""), baseline_checksum)
        self.assertTrue(import_after_first.get("last_blocked_at"))
        self.assertEqual(import_after_first.get("blocked_count"), 1)
        self.assertEqual(import_after_second["last_local_checksum"], baseline_checksum)
        self.assertEqual(import_after_second.get("blocked_count"), 2)

    def test_analyze_marks_unmanaged_lock_target_path_as_structural_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_item = next(
                item for item in lock_data["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            import_item["target_path"] = "custom/spec/technologies/languages/go/package-structure"
            lock_path.write_text(
                yaml.safe_dump(lock_data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            analyze = self.run_script(
                ANALYZE_SCRIPT,
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                "example.assembled-packs.go-service-foundation",
                "--json",
            )

        self.assertEqual(analyze.returncode, 0, msg=analyze.stdout + analyze.stderr)
        payload = json.loads(analyze.stdout)
        self.assertEqual(payload["needs_review"][0]["category"], "structural-conflict")
        self.assertIn("escapes managed .trellis/", payload["needs_review"][0]["message"])

    def test_analyze_merge_mode_scans_other_imports_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            baseline = self.run_script(
                ANALYZE_SCRIPT,
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--json",
            )
            self.assertEqual(baseline.returncode, 0, msg=baseline.stdout + baseline.stderr)
            selected_ids = set(json.loads(baseline.stdout)["assets_requested"])
            other_import = next(
                item
                for item in lock_data["imports"]
                if item["asset_id"] not in selected_ids
            )
            other_target = Path(target_dir) / other_import["target_path"]
            if other_target.is_dir():
                other_file = next(path for path in other_target.rglob("*.md"))
            else:
                other_file = other_target
            other_file.write_text(
                other_file.read_text(encoding="utf-8") + "\nOther drift coverage note.\n",
                encoding="utf-8",
            )

            analyze = self.run_script(
                ANALYZE_SCRIPT,
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--json",
            )

        self.assertEqual(analyze.returncode, 0, msg=analyze.stdout + analyze.stderr)
        payload = json.loads(analyze.stdout)
        drift_ids = {item["asset_id"] for item in payload["drift_items"]}
        self.assertIn(other_import["asset_id"], drift_ids)

    def test_sync_downstream_reports_other_import_drift_when_scoped_to_single_asset(self) -> None:
        with tempfile.TemporaryDirectory() as target_dir:
            assemble = self.run_cli(
                "assemble",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = Path(target_dir) / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            other_import = next(
                item for item in lock_data["imports"] if item["asset_id"] != GO_PACKAGE_ASSET
            )
            other_target = Path(target_dir) / other_import["target_path"]
            if other_target.is_dir():
                other_file = next(path for path in other_target.rglob("*.md"))
            else:
                other_file = other_target
            other_file.write_text(
                other_file.read_text(encoding="utf-8") + "\nScoped sync drift coverage note.\n",
                encoding="utf-8",
            )

            sync = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                "trellis-library",
                "--target",
                target_dir,
                "--asset",
                GO_PACKAGE_ASSET,
                "--dry-run",
            )

        self.assertEqual(sync.returncode, 0, msg=sync.stdout + sync.stderr)
        self.assertIn("已导入但本次未操作的资产存在漂移", sync.stdout)
        self.assertIn(other_import["asset_id"], sync.stdout)

    def test_sync_include_pinned_updates_pinned_asset_when_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            library_root = self.create_library_copy(temp_root)
            target_dir = Path(temp_root) / "target-project"
            target_dir.mkdir(parents=True, exist_ok=True)

            assemble = self.run_cli(
                "assemble",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            lock_path = target_dir / ".trellis" / "library-lock.yaml"
            import yaml

            lock_data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            import_item = next(
                item for item in lock_data["imports"] if item["asset_id"] == GO_PACKAGE_ASSET
            )
            import_item["upstream_sync"] = "pinned"
            lock_path.write_text(
                yaml.safe_dump(lock_data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            source_file = library_root / GO_PACKAGE_OVERVIEW
            pinned_line = "Pinned asset sync coverage line.\n"
            source_file.write_text(
                source_file.read_text(encoding="utf-8") + "\n" + pinned_line,
                encoding="utf-8",
            )

            target_file = target_dir / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            before_sync = target_file.read_text(encoding="utf-8")

            skipped = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--asset",
                GO_PACKAGE_ASSET,
            )
            self.assertEqual(skipped.returncode, 0, msg=skipped.stdout + skipped.stderr)
            self.assertIn("skipped-pinned", skipped.stdout)

            updated = self.run_cli(
                "sync",
                "--mode",
                "downstream",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--asset",
                GO_PACKAGE_ASSET,
                "--include-pinned",
                "--force",
            )

            after_sync = target_file.read_text(encoding="utf-8")

        self.assertEqual(updated.returncode, 0, msg=updated.stdout + updated.stderr)
        self.assertIn("updated", updated.stdout)
        self.assertNotEqual(before_sync, after_sync)
        self.assertIn(pinned_line.strip(), after_sync)

    def test_sync_apply_mode_applies_patch_to_library_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            library_root = self.create_library_copy(temp_root)
            target_dir = Path(temp_root) / "target-project"
            target_dir.mkdir(parents=True, exist_ok=True)

            assemble = self.run_cli(
                "assemble",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--pack",
                "pack.go-service-foundation",
            )
            self.assertEqual(assemble.returncode, 0, msg=assemble.stdout + assemble.stderr)

            target_file = target_dir / ".trellis" / GO_PACKAGE_TARGET_OVERVIEW
            appended_line = "Generalized apply-mode testing note.\n"
            target_file.write_text(
                target_file.read_text(encoding="utf-8") + "\n" + appended_line,
                encoding="utf-8",
            )

            diff = self.run_cli(
                "sync",
                "--mode",
                "diff",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--asset",
                GO_PACKAGE_ASSET,
                "--update-lock",
            )
            self.assertEqual(diff.returncode, 2, msg=diff.stdout + diff.stderr)

            proposal_path = Path(temp_root) / "proposal.json"
            patch_path = Path(temp_root) / "proposal.patch"
            propose = self.run_cli(
                "sync",
                "--mode",
                "propose",
                "--library-root",
                str(library_root),
                "--target",
                str(target_dir),
                "--asset",
                GO_PACKAGE_ASSET,
                "--scope",
                "file",
                "--file",
                "overview.md",
                "--patch-out",
                str(patch_path),
                "--json",
            )
            self.assertEqual(propose.returncode, 0, msg=propose.stdout + propose.stderr)

            proposal = json.loads(propose.stdout)
            proposal["approved"] = True
            proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")

            source_file = library_root / GO_PACKAGE_OVERVIEW
            before_apply = source_file.read_text(encoding="utf-8")

            apply_result = self.run_cli(
                "sync",
                "--mode",
                "apply",
                "--library-root",
                str(library_root),
                "--proposal",
                str(proposal_path),
                "--patch",
                str(patch_path),
                "--apply",
                "--json",
            )

            after_apply = source_file.read_text(encoding="utf-8")

        self.assertEqual(apply_result.returncode, 0, msg=apply_result.stdout + apply_result.stderr)
        payload = json.loads(apply_result.stdout)
        self.assertTrue(payload["applied"])
        self.assertTrue(payload["validated"])
        self.assertIn(appended_line.strip(), after_apply)
        self.assertNotEqual(before_apply, after_apply)


if __name__ == "__main__":
    unittest.main()
