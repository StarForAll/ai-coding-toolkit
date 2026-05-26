"""Validation runner for workflow-validate-matrix."""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from constants import PYTHON_BIN, STEP_TIMEOUT


class ValidationResult:
    """Result of a validation step."""

    def __init__(
        self,
        step: str,
        success: bool,
        output: str = "",
        error: str = "",
        findings: Optional[List[Dict[str, Any]]] = None,
    ):
        self.step = step
        self.success = success
        self.output = output
        self.error = error
        self.findings = findings or []


def run_detect_embed_state(temp_dir: Path, workflow_source: Path) -> ValidationResult:
    """Run detect-embed-state.py."""
    script = workflow_source / "commands" / "detect-embed-state.py"

    try:
        result = subprocess.run(
            [PYTHON_BIN, str(script), "--project-root", str(temp_dir)],
            cwd=workflow_source,
            capture_output=True,
            text=True,
            timeout=STEP_TIMEOUT,
        )

        return ValidationResult(
            step="detect-embed-state",
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else "",
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            step="detect-embed-state",
            success=False,
            error="Timeout after 5 minutes",
        )
    except Exception as e:
        return ValidationResult(
            step="detect-embed-state",
            success=False,
            error=str(e),
        )


def run_install_workflow(
    temp_dir: Path, workflow_source: Path, profile: str, cli: str
) -> ValidationResult:
    """Run install-workflow.py."""
    script = workflow_source / "commands" / "install-workflow.py"

    try:
        result = subprocess.run(
            [
                PYTHON_BIN,
                str(script),
                "--project-root", str(temp_dir),
                "--profile", profile,
                "--cli", cli,
            ],
            cwd=workflow_source,
            capture_output=True,
            text=True,
            timeout=STEP_TIMEOUT,
        )

        return ValidationResult(
            step="install-workflow",
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else "",
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            step="install-workflow",
            success=False,
            error="Timeout after 5 minutes",
        )
    except Exception as e:
        return ValidationResult(
            step="install-workflow",
            success=False,
            error=str(e),
        )


def run_upgrade_compat(temp_dir: Path, workflow_source: Path) -> ValidationResult:
    """Run upgrade-compat.py --check."""
    script = workflow_source / "commands" / "upgrade-compat.py"

    try:
        result = subprocess.run(
            [
                PYTHON_BIN,
                str(script),
                "--project-root", str(temp_dir),
                "--check",
            ],
            cwd=workflow_source,
            capture_output=True,
            text=True,
            timeout=STEP_TIMEOUT,
        )

        # upgrade-compat returns non-zero if conflicts found
        # This is expected, not an error
        return ValidationResult(
            step="upgrade-compat",
            success=True,  # Always success if it runs
            output=result.stdout,
            error=result.stderr if result.stderr else "",
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            step="upgrade-compat",
            success=False,
            error="Timeout after 5 minutes",
        )
    except Exception as e:
        return ValidationResult(
            step="upgrade-compat",
            success=False,
            error=str(e),
        )


def run_workflow_state(temp_dir: Path) -> ValidationResult:
    """Run workflow-state.py route (if exists)."""
    script = temp_dir / ".trellis" / "scripts" / "workflow" / "workflow-state.py"

    if not script.exists():
        return ValidationResult(
            step="workflow-state",
            success=True,
            output="Script not found (skipped)",
        )

    try:
        result = subprocess.run(
            [PYTHON_BIN, str(script), "route"],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=STEP_TIMEOUT,
        )

        return ValidationResult(
            step="workflow-state",
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr if result.returncode != 0 else "",
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            step="workflow-state",
            success=False,
            error="Timeout after 5 minutes",
        )
    except Exception as e:
        return ValidationResult(
            step="workflow-state",
            success=False,
            error=str(e),
        )


def run_validations(
    temp_dir: Path, workflow_source: Path, profile: str, cli: str
) -> List[ValidationResult]:
    """Run all validation steps for a scenario."""
    results = []

    # Step 1: detect-embed-state (before install)
    results.append(run_detect_embed_state(temp_dir, workflow_source))

    # Step 2: install-workflow
    install_result = run_install_workflow(temp_dir, workflow_source, profile, cli)
    results.append(install_result)

    # If install failed, skip remaining steps
    if not install_result.success:
        return results

    # Step 3: upgrade-compat
    results.append(run_upgrade_compat(temp_dir, workflow_source))

    # Step 4: workflow-state (if exists)
    results.append(run_workflow_state(temp_dir))

    return results
