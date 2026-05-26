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
    REQUIRED_POST_INSTALL_PATHS,
    STEP_TIMEOUT,
)
from runtime_bundle_manager import SOURCE_REPO_ROOT_ENV


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


def run_post_install_integrity(
    temp_dir: Path,
    scenario_name: str,
    profile: str,
    cli: str,
) -> ValidationResult:
    """Verify installed files and workflow-installed.json semantics."""
    findings: list[dict[str, Any]] = []

    for rel_path in REQUIRED_POST_INSTALL_PATHS:
        if not (temp_dir / rel_path).exists():
            findings.append(
                make_finding(
                    title=f"Missing installed artifact: {rel_path}",
                    step="post-install-integrity",
                    scenario_name=scenario_name,
                    temp_dir=temp_dir,
                    severity="P0",
                    repair_classification="confirmed-defect",
                    evidence=[f"Missing path: {rel_path}"],
                    description="install-workflow.py completed, but a required installed artifact is absent.",
                    investigation=f"Check why install-workflow.py did not create {rel_path}.",
                    category="post-install-artifact",
                    evidence_layer="generated-target-installed",
                    location=rel_path,
                )
            )

    record_path = temp_dir / ".trellis" / "workflow-installed.json"
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

    if scenario.get("run_post_checks", True):
        results.append(run_post_install_integrity(temp_dir, scenario_name, profile, cli))
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
        results.append(run_workflow_state(temp_dir, scenario_name))

    if scenario.get("run_upgrade_compat", False):
        results.append(run_upgrade_compat(temp_dir, workflow_root, repo_root, scenario_name, cli))

    return results
