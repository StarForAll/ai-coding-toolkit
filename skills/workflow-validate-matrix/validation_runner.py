"""Validation runner for workflow-validate-matrix."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from constants import (
    BLOCKING_ROUTE_ACTIONS,
    EMBED_STATE_VALID,
    PYTHON_BIN,
    STEP_TIMEOUT,
)
from runtime_bundle_manager import SOURCE_REPO_ROOT_ENV

_WORKFLOW_ASSETS_MODULE_CACHE: dict[Path, Any] = {}


@dataclass
class ValidationResult:
    """Result of a validation step."""

    step: str
    success: bool
    output: str = ""
    error: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)


def make_finding(
    *,
    title: str,
    step: str,
    scenario_name: str,
    temp_dir: Path,
    severity: str,
    repair_classification: str,
    evidence: list[str],
    description: str,
    investigation: str,
    category: str = "script-behavior",
    origin: str = "workflow-source",
    evidence_layer: str = "generated-target-runtime",
    location: str | None = None,
) -> dict[str, Any]:
    """Create a report finding with consistent fields."""
    return {
        "title": title,
        "step": step,
        "scenario": scenario_name,
        "category": category,
        "severity": severity,
        "repair_classification": repair_classification,
        "origin": origin,
        "evidence_layer": evidence_layer,
        "evidence": evidence,
        "location": location or ".",
        "temp_dir": str(temp_dir),
        "description": description,
        "investigation": investigation,
    }


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = STEP_TIMEOUT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()


def _json_payload(output: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _warning_findings(
    *,
    step: str,
    scenario_name: str,
    temp_dir: Path,
    output: str,
    location: str = ".",
) -> list[dict[str, Any]]:
    """Convert successful command warnings into evidence-gap findings."""
    payload = _json_payload(output)
    if payload and isinstance(payload.get("warnings"), list):
        warning_lines = [str(item).strip() for item in payload["warnings"] if str(item).strip()]
    else:
        warning_lines = [
            line.strip()
            for line in output.splitlines()
            if "⚠️" in line or line.strip().startswith("WARN") or line.lower().startswith("warning")
        ]
    if not warning_lines:
        return []
    return [
        make_finding(
            title=f"{step} emitted warnings",
            step=step,
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P2",
            repair_classification="evidence-gap",
            evidence=warning_lines[:10],
            description=(
                f"Validation step '{step}' exited successfully but emitted warnings. "
                "The matrix should surface these for repair-side triage instead of hiding them."
            ),
            investigation=f"Review the {step} output and decide whether the warning is actionable.",
            location=location,
        )
    ]


def run_detect_embed_state(
    temp_dir: Path,
    workflow_root: Path,
    repo_root: Path,
    scenario_name: str,
    expected_status: str,
    *,
    step: str,
    cli: str | None = None,
) -> ValidationResult:
    """Run detect-embed-state.py --json and match the exact status value."""
    script = workflow_root / "commands" / "detect-embed-state.py"
    command = [PYTHON_BIN, str(script), "--project-root", str(temp_dir), "--json"]
    if cli:
        command.extend(["--cli", cli])
    env = os.environ.copy()
    env[SOURCE_REPO_ROOT_ENV] = str(repo_root)

    try:
        result = _run_command(command, cwd=repo_root, env=env)
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title=f"{step} timed out",
            step=step,
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description=f"{step} did not complete within the validation timeout.",
            investigation="Check detect-embed-state.py for hangs or slow upgrade checks.",
        )
        return ValidationResult(step=step, success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title=f"{step} could not run",
            step=step,
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description=f"{step} failed before producing JSON output.",
            investigation="Verify the Python interpreter and detect-embed-state.py path.",
        )
        return ValidationResult(step=step, success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    payload = _json_payload(result.stdout)
    if result.returncode != 0 or payload is None:
        finding = make_finding(
            title=f"{step} returned invalid output",
            step=step,
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[
                f"returncode={result.returncode}",
                output or "No output",
            ],
            description=f"{step} must return parseable JSON so matrix validation can inspect exact status values.",
            investigation="Run detect-embed-state.py --json directly and fix the failing contract.",
        )
        return ValidationResult(step=step, success=False, output=output, error=finding["description"], findings=[finding])

    actual_status = str(payload.get("status", ""))
    if actual_status != expected_status:
        finding = make_finding(
            title=f"{step} status mismatch",
            step=step,
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[
                f"expected status: {expected_status}",
                f"actual status: {actual_status}",
                f"blockers: {payload.get('blockers', [])}",
            ],
            description=(
                f"{step} expected exact embed state '{expected_status}' but got '{actual_status}'. "
                "Substring matching is not reliable for embed-state validation."
            ),
            investigation="Inspect detect-embed-state.py output and the scenario setup traces.",
        )
        return ValidationResult(step=step, success=False, output=output, error=finding["description"], findings=[finding])

    findings = _warning_findings(step=step, scenario_name=scenario_name, temp_dir=temp_dir, output=output)
    return ValidationResult(step=step, success=True, output=output, findings=findings)


def run_install_workflow(
    temp_dir: Path,
    workflow_root: Path,
    repo_root: Path,
    scenario_name: str,
    profile: str,
    cli: str,
) -> ValidationResult:
    """Run install-workflow.py."""
    script = workflow_root / "commands" / "install-workflow.py"
    env = os.environ.copy()
    env["WORKFLOW_EMBED_EXECUTOR_CONFIRMED"] = "1"
    env[SOURCE_REPO_ROOT_ENV] = str(repo_root)

    try:
        result = _run_command(
            [
                PYTHON_BIN,
                str(script),
                "--project-root",
                str(temp_dir),
                "--profile",
                profile,
                "--cli",
                cli,
            ],
            cwd=repo_root,
            env=env,
        )
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title="install-workflow timed out",
            step="install-workflow",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description="install-workflow.py did not complete within the validation timeout.",
            investigation="Run install-workflow.py directly with the same profile and CLI combination.",
        )
        return ValidationResult(step="install-workflow", success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title="install-workflow could not run",
            step="install-workflow",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description="install-workflow.py failed before producing output.",
            investigation="Verify the Python interpreter and install-workflow.py path.",
        )
        return ValidationResult(step="install-workflow", success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    if result.returncode != 0:
        finding = make_finding(
            title="install-workflow failed",
            step="install-workflow",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[
                f"profile={profile}",
                f"cli={cli}",
                output or "No output",
            ],
            description="Workflow installation failed for this scenario.",
            investigation="Review install-workflow.py output and fix the source installation path.",
        )
        return ValidationResult(step="install-workflow", success=False, output=output, error=output, findings=[finding])

    findings = _warning_findings(step="install-workflow", scenario_name=scenario_name, temp_dir=temp_dir, output=output)
    return ValidationResult(step="install-workflow", success=True, output=output, findings=findings)


def run_install_block_check(
    temp_dir: Path,
    workflow_root: Path,
    repo_root: Path,
    scenario_name: str,
    profile: str,
    cli: str,
    expected_substrings: list[str],
) -> ValidationResult:
    """Run install-workflow.py and verify it is rejected for blocked/already-installed scenarios."""
    script = workflow_root / "commands" / "install-workflow.py"
    env = os.environ.copy()
    env["WORKFLOW_EMBED_EXECUTOR_CONFIRMED"] = "1"
    env[SOURCE_REPO_ROOT_ENV] = str(repo_root)

    try:
        result = _run_command(
            [
                PYTHON_BIN,
                str(script),
                "--project-root",
                str(temp_dir),
                "--profile",
                profile,
                "--cli",
                cli,
            ],
            cwd=repo_root,
            env=env,
        )
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title="install-workflow block check timed out",
            step="install-workflow-blocked",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description="install-workflow.py block check did not complete within the validation timeout.",
            investigation="Run install-workflow.py directly on the blocked scenario fixture.",
        )
        return ValidationResult(step="install-workflow-blocked", success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title="install-workflow block check could not run",
            step="install-workflow-blocked",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description="install-workflow.py block check failed before producing output.",
            investigation="Verify the Python interpreter and install-workflow.py path.",
        )
        return ValidationResult(step="install-workflow-blocked", success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    if result.returncode == 0:
        finding = make_finding(
            title="install-workflow unexpectedly allowed blocked reinstall",
            step="install-workflow-blocked",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[output or "install-workflow.py exited 0"],
            description="install-workflow.py should reject this scenario but returned success.",
            investigation="Check install-workflow.py embed-state gate before writing any install artifacts.",
        )
        return ValidationResult(step="install-workflow-blocked", success=False, output=output, error=finding["description"], findings=[finding])

    missing_substrings = [token for token in expected_substrings if token not in output]
    if missing_substrings:
        finding = make_finding(
            title="install-workflow block output missing expected evidence",
            step="install-workflow-blocked",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P1",
            repair_classification="confirmed-defect",
            evidence=[
                f"missing expected substrings: {missing_substrings}",
                output or "No output",
            ],
            description="install-workflow.py rejected the scenario, but the blocking evidence/output is incomplete.",
            investigation="Keep the rejection reason explicit so matrix validation and users can tell why install was blocked.",
        )
        return ValidationResult(step="install-workflow-blocked", success=False, output=output, error=finding["description"], findings=[finding])

    findings = _warning_findings(
        step="install-workflow-blocked",
        scenario_name=scenario_name,
        temp_dir=temp_dir,
        output=output,
    )
    return ValidationResult(step="install-workflow-blocked", success=True, output=output, findings=findings)


def _load_workflow_assets_module(workflow_root: Path):
    assets_path = (workflow_root / "commands" / "workflow_assets.py").resolve()
    cached = _WORKFLOW_ASSETS_MODULE_CACHE.get(assets_path)
    if cached is not None:
        return cached

    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("workflow_validate_matrix_bundle_assets", assets_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load bundled workflow_assets.py: {assets_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _WORKFLOW_ASSETS_MODULE_CACHE[assets_path] = module
    return module


def _expected_helper_scripts_for_profile(workflow_assets: Any, profile: str) -> set[str]:
    default_profile = str(getattr(workflow_assets, "DEFAULT_PROFILE", "outsourcing"))
    default_scripts = [str(item) for item in getattr(workflow_assets, "HELPER_SCRIPTS", [])]
    core_scripts = [str(item) for item in getattr(workflow_assets, "CORE_HELPER_SCRIPTS", default_scripts)]
    return set(default_scripts if profile == default_profile else core_scripts)


def _required_substrings_findings(
    *,
    scenario_name: str,
    temp_dir: Path,
    rel_path: str,
    content: str,
    required_substrings: tuple[str, ...],
    title_prefix: str,
    investigation: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for needle in required_substrings:
        if needle in content:
            continue
        findings.append(
            make_finding(
                title=f"{title_prefix} missing expected content",
                step="post-install-integrity",
                scenario_name=scenario_name,
                temp_dir=temp_dir,
                severity="P1",
                repair_classification="confirmed-defect",
                evidence=[f"path={rel_path}", f"missing substring={needle}"],
                description=f"{rel_path} exists but does not contain expected workflow-managed content.",
                investigation=investigation,
                category="post-install-artifact",
                evidence_layer="generated-target-installed",
                location=rel_path,
            )
        )
    return findings


def _candidate_paths_for_spec(spec: Any, root: Path, workflow_assets: Any) -> list[Path]:
    path = spec.locate(root)
    if path is None:
        return []
    if getattr(spec, "kind", "") != "skill" or getattr(spec, "cli_type", "") != "codex":
        return [path]

    candidates: list[Path] = []
    primary = path
    candidates.append(primary)
    try:
        secondary_dir = workflow_assets.codex_secondary_skills_dir(root)
    except Exception:
        secondary_dir = None
    if secondary_dir is not None:
        candidates.append(secondary_dir / getattr(spec, "name") / "SKILL.md")
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate)
    return deduped


def _candidate_paths_from_relative(rel_path: str, root: Path, workflow_assets: Any) -> list[Path]:
    path = root / rel_path
    if not rel_path.startswith(".codex/skills/.backup-original"):
        return [path]
    try:
        shared_dir = workflow_assets.codex_shared_skills_dir(root)
    except Exception:
        shared_dir = None
    shared_backup = shared_dir / ".backup-original" if shared_dir is not None else None
    candidates = [candidate for candidate in [path, shared_backup] if candidate is not None]
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        deduped.append(candidate)
        seen.add(candidate)
    return deduped


def run_post_install_integrity(
    temp_dir: Path,
    workflow_root: Path,
    scenario_name: str,
    profile: str,
    cli: str,
) -> ValidationResult:
    """Verify installed files and workflow-installed.json semantics."""
    findings: list[dict[str, Any]] = []
    workflow_assets = None
    cli_types = [item.strip() for item in cli.split(",") if item.strip()]
    expected_scripts_from_record: set[str] | None = None
    try:
        workflow_assets = _load_workflow_assets_module(workflow_root)
        asset_specs = workflow_assets.build_managed_asset_specs(cli_types)
        extra_specs = workflow_assets.build_managed_audit_extra_specs(cli_types)
    except Exception as exc:
        findings.append(
            make_finding(
                title="Unable to load workflow asset contract",
                step="post-install-integrity",
                scenario_name=scenario_name,
                temp_dir=temp_dir,
                severity="P0",
                repair_classification="confirmed-defect",
                evidence=[str(exc)],
                description="Matrix validation could not load the bundled workflow asset contract.",
                investigation="Check that runtime_bundle/workflow/commands/workflow_assets.py exists and remains importable.",
                category="post-install-artifact",
                evidence_layer="generated-target-runtime",
                location="runtime_bundle/workflow/commands/workflow_assets.py",
            )
        )
        asset_specs = []
        extra_specs = []

    record_path = temp_dir / ".trellis" / "workflow-installed.json"
    record: dict[str, Any] | None = None
    if record_path.exists():
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            record = None
    if isinstance(record, dict) and isinstance(record.get("scripts"), list):
        expected_scripts_from_record = {str(item) for item in record["scripts"]}

    for spec in asset_specs:
        candidate_paths = _candidate_paths_for_spec(spec, temp_dir, workflow_assets)
        if not candidate_paths:
            continue
        relative_path = candidate_paths[0].relative_to(temp_dir).as_posix()
        if spec.category == "disabled-baseline":
            if any(path.exists() for path in candidate_paths):
                findings.append(
                    make_finding(
                        title=f"Disabled baseline asset should be absent: {spec.asset_id}",
                        step="post-install-integrity",
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        severity="P0",
                        repair_classification="confirmed-defect",
                        evidence=[f"Unexpected path present: {relative_path}"],
                        description="A disabled baseline asset still exists after installation.",
                        investigation=f"Check why install-workflow.py did not remove disabled asset {spec.asset_id}.",
                        category="post-install-artifact",
                        evidence_layer="generated-target-installed",
                        location=relative_path,
                    )
                )
            continue
        if getattr(spec, "kind", "") == "script" and expected_scripts_from_record is not None:
            if getattr(spec, "name", "") not in expected_scripts_from_record:
                continue
        if not any(path.exists() for path in candidate_paths):
            findings.append(
                make_finding(
                    title=f"Missing installed asset: {spec.asset_id}",
                    step="post-install-integrity",
                    scenario_name=scenario_name,
                    temp_dir=temp_dir,
                    severity="P0",
                    repair_classification="confirmed-defect",
                    evidence=[f"Missing path: {relative_path}"],
                    description="install-workflow.py completed, but a managed installed asset is absent.",
                    investigation=f"Check why install-workflow.py did not deploy {spec.asset_id}.",
                    category="post-install-artifact",
                    evidence_layer="generated-target-installed",
                    location=relative_path,
                )
            )

    checked_extra_targets: set[tuple[str, str]] = set()
    for extra in extra_specs:
        cli_path_map = {
            "claude": getattr(extra, "claude_paths", ()),
            "opencode": getattr(extra, "opencode_paths", ()),
            "codex": getattr(extra, "codex_paths", ()),
        }
        for cli_type, rel_paths in cli_path_map.items():
            if cli_type not in set(cli_types):
                continue
            for rel_path in rel_paths:
                dedupe_key = (extra.capability, rel_path)
                if dedupe_key in checked_extra_targets:
                    continue
                checked_extra_targets.add(dedupe_key)
                targets = _candidate_paths_from_relative(rel_path, temp_dir, workflow_assets)
                if not any(target.exists() for target in targets):
                    findings.append(
                        make_finding(
                            title=f"Missing audit surface: {extra.capability}",
                            step="post-install-integrity",
                            scenario_name=scenario_name,
                            temp_dir=temp_dir,
                            severity="P0",
                            repair_classification="confirmed-defect",
                            evidence=[f"capability={extra.capability}", f"missing path={rel_path}"],
                            description="A documented workflow-managed audit surface is missing after installation.",
                            investigation=f"Reconcile install-workflow.py deployment with workflow_assets.py contract for {extra.capability}.",
                            category="post-install-artifact",
                            evidence_layer="generated-target-installed",
                            location=rel_path,
                        )
                    )
                    continue
                readable_target = next((target for target in targets if target.exists() and target.is_file()), None)
                if not extra.required_substrings or readable_target is None:
                    continue
                try:
                    content = readable_target.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    findings.append(
                        make_finding(
                            title=f"Unreadable audit surface: {extra.capability}",
                            step="post-install-integrity",
                            scenario_name=scenario_name,
                            temp_dir=temp_dir,
                            severity="P0",
                            repair_classification="confirmed-defect",
                            evidence=[f"path={rel_path}", str(exc)],
                            description="A workflow-managed audit surface exists but cannot be read for validation.",
                            investigation="Check file encoding and deployment integrity.",
                            category="post-install-artifact",
                            evidence_layer="generated-target-installed",
                            location=rel_path,
                        )
                    )
                    continue
                findings.extend(
                    _required_substrings_findings(
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        rel_path=rel_path,
                        content=content,
                        required_substrings=tuple(extra.required_substrings),
                        title_prefix=extra.capability,
                        investigation=f"Reconcile {rel_path} with workflow_assets.py content contract for {extra.capability}.",
                    )
                )

    if record_path.exists():
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            findings.append(
                make_finding(
                    title="workflow-installed.json is not valid JSON",
                    step="post-install-integrity",
                    scenario_name=scenario_name,
                    temp_dir=temp_dir,
                    severity="P0",
                    repair_classification="confirmed-defect",
                    evidence=[str(exc)],
                    description="The install record exists but cannot be parsed.",
                    investigation="Fix install record writing in install-workflow.py.",
                    category="post-install-artifact",
                    evidence_layer="generated-target-installed",
                    location=".trellis/workflow-installed.json",
                )
            )
        else:
            required_keys = {
                "workflow_version",
                "workflow_schema_version",
                "profile",
                "cli_types",
            }
            expected_scripts_from_record = (
                set(record.get("scripts", [])) if isinstance(record.get("scripts"), list) else set()
            )
            missing = sorted(key for key in required_keys if key not in record)
            if missing:
                findings.append(
                    make_finding(
                        title="workflow-installed.json missing required keys",
                        step="post-install-integrity",
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        severity="P0",
                        repair_classification="confirmed-defect",
                        evidence=[f"missing keys: {', '.join(missing)}"],
                        description="The install record is incomplete for repair-side verification.",
                        investigation="Update install-workflow.py record writing and upgrade compatibility checks.",
                        category="post-install-artifact",
                        evidence_layer="generated-target-installed",
                        location=".trellis/workflow-installed.json",
                    )
                )
            if record.get("profile") != profile:
                findings.append(
                    make_finding(
                        title="workflow-installed.json profile mismatch",
                        step="post-install-integrity",
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        severity="P1",
                        repair_classification="confirmed-defect",
                        evidence=[f"expected profile={profile}", f"actual profile={record.get('profile')}"],
                        description="The install record does not match the scenario profile.",
                        investigation="Check profile propagation in install-workflow.py.",
                        category="post-install-artifact",
                        evidence_layer="generated-target-installed",
                        location=".trellis/workflow-installed.json",
                    )
                )
            expected_cli = {item.strip() for item in cli.split(",") if item.strip()}
            actual_cli = set(record.get("cli_types", [])) if isinstance(record.get("cli_types"), list) else set()
            if not expected_cli.issubset(actual_cli):
                findings.append(
                    make_finding(
                        title="workflow-installed.json CLI types mismatch",
                        step="post-install-integrity",
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        severity="P1",
                        repair_classification="confirmed-defect",
                        evidence=[
                            f"expected CLI subset={sorted(expected_cli)}",
                            f"actual CLI types={sorted(actual_cli)}",
                        ],
                        description="The install record does not include all CLI adapters requested by the scenario.",
                        investigation="Check CLI detection/filtering in install-workflow.py.",
                        category="post-install-artifact",
                        evidence_layer="generated-target-installed",
                        location=".trellis/workflow-installed.json",
                    )
                )
            expected_scripts = (
                _expected_helper_scripts_for_profile(workflow_assets, profile)
                if workflow_assets is not None
                else set()
            )
            actual_scripts = expected_scripts_from_record
            if expected_scripts and expected_scripts != actual_scripts:
                findings.append(
                    make_finding(
                        title="workflow-installed.json scripts list mismatch",
                        step="post-install-integrity",
                        scenario_name=scenario_name,
                        temp_dir=temp_dir,
                        severity="P1",
                        repair_classification="confirmed-defect",
                        evidence=[
                            f"expected scripts={sorted(expected_scripts)}",
                            f"actual scripts={sorted(actual_scripts)}",
                        ],
                        description="The install record does not describe the helper script set that the profile should deploy.",
                        investigation="Check install record writing and profile-specific helper script selection.",
                        category="post-install-artifact",
                        evidence_layer="generated-target-installed",
                        location=".trellis/workflow-installed.json",
                    )
                )

    success = not findings
    error = "; ".join(f["title"] for f in findings)
    return ValidationResult(
        step="post-install-integrity",
        success=success,
        output="Post-install integrity check complete",
        error=error,
        findings=findings,
    )


def run_upgrade_compat(
    temp_dir: Path,
    workflow_root: Path,
    repo_root: Path,
    scenario_name: str,
    cli: str,
) -> ValidationResult:
    """Run upgrade-compat.py --check only for installed/upgrade scenarios."""
    script = workflow_root / "commands" / "upgrade-compat.py"
    env = os.environ.copy()
    env[SOURCE_REPO_ROOT_ENV] = str(repo_root)

    try:
        result = _run_command(
            [
                PYTHON_BIN,
                str(script),
                "--project-root",
                str(temp_dir),
                "--check",
                "--cli",
                cli,
            ],
            cwd=repo_root,
            env=env,
        )
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title="upgrade-compat timed out",
            step="upgrade-compat",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description="upgrade-compat.py did not complete within the validation timeout.",
            investigation="Run upgrade-compat.py directly on the scenario fixture.",
        )
        return ValidationResult(step="upgrade-compat", success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title="upgrade-compat could not run",
            step="upgrade-compat",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description="upgrade-compat.py failed before producing output.",
            investigation="Verify the Python interpreter and upgrade-compat.py path.",
        )
        return ValidationResult(step="upgrade-compat", success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    if result.returncode != 0:
        finding = make_finding(
            title="upgrade-compat reported conflicts",
            step="upgrade-compat",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P1",
            repair_classification="confirmed-defect",
            evidence=[output or "No output"],
            description="upgrade-compat.py found conflicts in an installed workflow scenario.",
            investigation="Review upgrade-compat.py output and fix the source upgrade path.",
        )
        return ValidationResult(step="upgrade-compat", success=False, output=output, error=output, findings=[finding])

    findings = _warning_findings(step="upgrade-compat", scenario_name=scenario_name, temp_dir=temp_dir, output=output)
    return ValidationResult(step="upgrade-compat", success=True, output=output, findings=findings)


def run_embed_integrity(temp_dir: Path, scenario_name: str) -> ValidationResult:
    """Run embed_integrity.py on the installed project."""
    script = temp_dir / ".trellis" / "scripts" / "workflow" / "embed_integrity.py"
    if not script.exists():
        finding = make_finding(
            title="embed_integrity.py missing after install",
            step="embed-integrity",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Missing .trellis/scripts/workflow/embed_integrity.py"],
            description="The installed workflow cannot run embed_integrity because the helper script is missing.",
            investigation="Check helper script deployment in install-workflow.py.",
            category="post-install-artifact",
            evidence_layer="generated-target-installed",
            location=".trellis/scripts/workflow/embed_integrity.py",
        )
        return ValidationResult(step="embed-integrity", success=False, error=finding["description"], findings=[finding])

    try:
        result = _run_command([PYTHON_BIN, str(script), str(temp_dir)], cwd=temp_dir)
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title="embed_integrity.py timed out",
            step="embed-integrity",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description="embed_integrity.py did not complete within the validation timeout.",
            investigation="Run embed_integrity.py directly in the installed fixture.",
            location=".trellis/scripts/workflow/embed_integrity.py",
        )
        return ValidationResult(step="embed-integrity", success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title="embed_integrity.py could not run",
            step="embed-integrity",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description="embed_integrity.py failed before producing output.",
            investigation="Verify the Python interpreter and installed embed_integrity.py.",
            location=".trellis/scripts/workflow/embed_integrity.py",
        )
        return ValidationResult(step="embed-integrity", success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    if result.returncode != 0:
        finding = make_finding(
            title="embed_integrity.py reported invalid embed state",
            step="embed-integrity",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[output or "No output"],
            description="embed_integrity.py reported the installed workflow as invalid.",
            investigation="Inspect the installed embed artifacts and integrity advisories.",
            location=".trellis/scripts/workflow/embed_integrity.py",
        )
        return ValidationResult(step="embed-integrity", success=False, output=output, error=finding["description"], findings=[finding])

    findings = _warning_findings(step="embed-integrity", scenario_name=scenario_name, temp_dir=temp_dir, output=output)
    return ValidationResult(step="embed-integrity", success=True, output=output, findings=findings)


def run_workflow_state(temp_dir: Path, scenario_name: str) -> ValidationResult:
    """Run workflow-state.py route and reject blocking route actions even with rc=0."""
    script = temp_dir / ".trellis" / "scripts" / "workflow" / "workflow-state.py"

    if not script.exists():
        finding = make_finding(
            title="workflow-state.py missing after install",
            step="workflow-state",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Missing .trellis/scripts/workflow/workflow-state.py"],
            description="The installed workflow cannot route because workflow-state.py is missing.",
            investigation="Check helper script deployment in install-workflow.py.",
            category="post-install-artifact",
            evidence_layer="generated-target-installed",
            location=".trellis/scripts/workflow/workflow-state.py",
        )
        return ValidationResult(step="workflow-state", success=False, error=finding["description"], findings=[finding])

    try:
        result = _run_command(
            [PYTHON_BIN, str(script), "route", "--project-root", str(temp_dir)],
            cwd=temp_dir,
        )
    except subprocess.TimeoutExpired:
        finding = make_finding(
            title="workflow-state route timed out",
            step="workflow-state",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=["Timeout after 5 minutes"],
            description="workflow-state.py route did not complete within the validation timeout.",
            investigation="Run workflow-state.py route directly in the scenario fixture.",
        )
        return ValidationResult(step="workflow-state", success=False, error=finding["description"], findings=[finding])
    except Exception as exc:
        finding = make_finding(
            title="workflow-state route could not run",
            step="workflow-state",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[str(exc)],
            description="workflow-state.py route failed before producing output.",
            investigation="Verify the Python interpreter and installed workflow-state.py.",
        )
        return ValidationResult(step="workflow-state", success=False, error=str(exc), findings=[finding])

    output = _combined_output(result)
    payload = _json_payload(result.stdout)
    action = str(payload.get("action", "")) if payload else ""
    if result.returncode != 0 or payload is None or action in BLOCKING_ROUTE_ACTIONS:
        finding = make_finding(
            title="workflow-state route is blocked",
            step="workflow-state",
            scenario_name=scenario_name,
            temp_dir=temp_dir,
            severity="P0",
            repair_classification="confirmed-defect",
            evidence=[
                f"returncode={result.returncode}",
                f"action={action or 'unparseable'}",
                output or "No output",
            ],
            description="workflow-state.py route returned a blocking or invalid action after installation.",
            investigation="Inspect installed workflow integrity, especially library-lock.yaml and workflow-installed.json.",
            location=".trellis/scripts/workflow/workflow-state.py",
        )
        return ValidationResult(step="workflow-state", success=False, output=output, error=finding["description"], findings=[finding])

    findings = _warning_findings(step="workflow-state", scenario_name=scenario_name, temp_dir=temp_dir, output=output)
    return ValidationResult(step="workflow-state", success=True, output=output, findings=findings)


def run_validations(
    temp_dir: Path,
    workflow_root: Path,
    repo_root: Path,
    scenario: dict[str, Any],
) -> list[ValidationResult]:
    """Run validation steps for a scenario."""
    scenario_name = str(scenario["name"])
    profile = str(scenario["profile"])
    cli = str(scenario["cli"])
    results: list[ValidationResult] = []

    expected_pre_status = str(scenario["expected_pre_status"])
    results.append(
        run_detect_embed_state(
            temp_dir,
            workflow_root,
            repo_root,
            scenario_name,
            expected_pre_status,
            step="detect-embed-state-pre",
            cli=cli,
        )
    )
    if not results[-1].success:
        return results

    if scenario.get("run_install", True):
        install_result = run_install_workflow(temp_dir, workflow_root, repo_root, scenario_name, profile, cli)
        results.append(install_result)
        if not install_result.success:
            return results
    elif scenario.get("verify_install_blocked", False):
        block_result = run_install_block_check(
            temp_dir,
            workflow_root,
            repo_root,
            scenario_name,
            profile,
            cli,
            [str(item) for item in scenario.get("expected_install_block_substrings", [])],
        )
        results.append(block_result)
        if not block_result.success:
            return results

    if scenario.get("run_post_checks", True):
        results.append(run_post_install_integrity(temp_dir, workflow_root, scenario_name, profile, cli))
        results.append(
            run_detect_embed_state(
                temp_dir,
                workflow_root,
                repo_root,
                scenario_name,
                str(scenario.get("expected_post_status", EMBED_STATE_VALID)),
                step="detect-embed-state-post",
                cli=cli,
            )
        )
        results.append(run_embed_integrity(temp_dir, scenario_name))
        results.append(run_workflow_state(temp_dir, scenario_name))

    if scenario.get("run_upgrade_compat", False):
        results.append(run_upgrade_compat(temp_dir, workflow_root, repo_root, scenario_name, cli))

    return results
