"""Scenario setup for workflow-validate-matrix."""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any

from constants import PYTHON_BIN


def setup_clean(temp_dir: Path, workflow_source: Path) -> None:
    """Setup clean scenario: empty directory with git init only."""
    # Git init
    subprocess.run(
        ["git", "init"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
        timeout=30,
    )

    # Add dummy remote (required by install-workflow.py)
    subprocess.run(
        ["git", "remote", "add", "origin", "git@github.com:test/test.git"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
        timeout=10,
    )

    # Add second push URL (required by install-workflow.py)
    subprocess.run(
        ["git", "remote", "set-url", "--add", "--push", "origin", "git@github.com:test/test.git"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
        timeout=10,
    )

    subprocess.run(
        ["git", "remote", "set-url", "--add", "--push", "origin", "git@gitee.com:test/test.git"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
        timeout=10,
    )

    # Trellis init
    subprocess.run(
        ["trellis", "init", "--claude", "--opencode", "--codex", "-y", "-u", "xzc"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
        timeout=120,
    )


def setup_existing_trellis(temp_dir: Path, workflow_source: Path) -> None:
    """Setup existing-trellis scenario: after trellis init."""
    # Same as clean - trellis init already done
    setup_clean(temp_dir, workflow_source)


def setup_existing_workflow(temp_dir: Path, workflow_source: Path) -> None:
    """Setup existing-workflow scenario: with old workflow installed."""
    # First do trellis init
    setup_clean(temp_dir, workflow_source)

    # Install current workflow (simulating "old" version)
    # In real scenario, this would install an older version
    # For MVP, we just install current version to test upgrade-compat
    install_script = workflow_source / "commands" / "install-workflow.py"

    subprocess.run(
        [
            PYTHON_BIN,
            str(install_script),
            "--project-root", str(temp_dir),
            "--profile", "outsourcing",
            "--cli", "claude,opencode,codex",
        ],
        cwd=workflow_source,
        check=True,
        capture_output=True,
        timeout=180,
    )


SCENARIO_SETUP_MAP = {
    "clean": setup_clean,
    "existing-trellis": setup_existing_trellis,
    "existing-workflow": setup_existing_workflow,
}


def setup_scenario(scenario_name: str, temp_dir: Path, workflow_source: Path) -> None:
    """Setup a scenario in the given temp directory."""
    if scenario_name not in SCENARIO_SETUP_MAP:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    setup_func = SCENARIO_SETUP_MAP[scenario_name]
    setup_func(temp_dir, workflow_source)
