"""Scenario setup for workflow-validate-matrix."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from constants import PYTHON_BIN, TRELLIS_USER
from runtime_bundle_manager import SOURCE_REPO_ROOT_ENV


def _run(command: list[str], cwd: Path, timeout: int = 30, env: dict[str, str] | None = None) -> None:
    """Run a scenario setup command with consistent error handling."""
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _init_git_repo(temp_dir: Path) -> None:
    """Create a non-empty git repo that satisfies install-workflow prerequisites."""
    _run(["git", "init"], cwd=temp_dir)
    _run(["git", "checkout", "-B", "main"], cwd=temp_dir)
    _run(["git", "config", "user.email", "matrix@example.invalid"], cwd=temp_dir)
    _run(["git", "config", "user.name", "Workflow Matrix"], cwd=temp_dir)
    (temp_dir / "README.md").write_text("# Matrix fixture\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=temp_dir)
    _run(["git", "commit", "-m", "chore: initial fixture"], cwd=temp_dir)

    _run(
        ["git", "remote", "add", "origin", "git@github.com:test/test.git"],
        cwd=temp_dir,
        timeout=10,
    )
    _run(
        ["git", "remote", "set-url", "--add", "--push", "origin", "git@github.com:test/test.git"],
        cwd=temp_dir,
        timeout=10,
    )
    _run(
        ["git", "remote", "set-url", "--add", "--push", "origin", "git@gitee.com:test/test.git"],
        cwd=temp_dir,
        timeout=10,
    )


def _trellis_init(temp_dir: Path) -> None:
    """Run trellis init for all platform carriers used by the matrix."""
    _run(
        ["trellis", "init", "--claude", "--opencode", "--codex", "-y", "-u", TRELLIS_USER],
        cwd=temp_dir,
        timeout=120,
    )


def setup_clean(temp_dir: Path, workflow_root: Path, scenario: dict[str, Any], repo_root: Path) -> None:
    """Setup clean scenario: git init + initial commit + trellis init."""
    _ = workflow_root, scenario, repo_root
    _init_git_repo(temp_dir)
    _trellis_init(temp_dir)


def _add_task_history(temp_dir: Path) -> None:
    """Create task/workspace artifacts that make the fixture non-empty."""
    tasks_dir = temp_dir / ".trellis" / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    dummy_task = tasks_dir / "test-task"
    dummy_task.mkdir(exist_ok=True)
    (dummy_task / "task.json").write_text(
        json.dumps({"name": "test-task", "status": "completed"}, indent=2),
        encoding="utf-8",
    )
    workspace_dir = temp_dir / ".trellis" / "workspace" / TRELLIS_USER
    workspace_dir.mkdir(parents=True, exist_ok=True)
    (workspace_dir / "journal-1.md").write_text("# Fixture journal\n", encoding="utf-8")


def setup_existing_customized(temp_dir: Path, workflow_root: Path, scenario: dict[str, Any], repo_root: Path) -> None:
    """Setup a Trellis project with task history and existing CLI customization."""
    setup_clean(temp_dir, workflow_root, scenario, repo_root)
    _add_task_history(temp_dir)

    claude_settings = temp_dir / ".claude" / "settings.json"
    claude_settings.parent.mkdir(parents=True, exist_ok=True)
    claude_settings.write_text(
        json.dumps({"permissions": {"allow": ["Bash(git status:*)"]}}, indent=2),
        encoding="utf-8",
    )

    opencode_config = temp_dir / ".opencode" / "opencode.json"
    opencode_config.parent.mkdir(parents=True, exist_ok=True)
    opencode_config.write_text(json.dumps({"model": "fixture"}, indent=2), encoding="utf-8")

    codex_config = temp_dir / ".codex" / "config.toml"
    codex_config.parent.mkdir(parents=True, exist_ok=True)
    existing = codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
    if "fixture_custom_setting" not in existing:
        codex_config.write_text(existing.rstrip() + "\nfixture_custom_setting = true\n", encoding="utf-8")


def setup_failed_attempt(temp_dir: Path, workflow_root: Path, scenario: dict[str, Any], repo_root: Path) -> None:
    """Setup a project that should be blocked by a failed embed-attempt record."""
    setup_clean(temp_dir, workflow_root, scenario, repo_root)
    attempt_record = temp_dir / ".trellis" / "workflow-embed-attempt.json"
    attempt_record.write_text(
        json.dumps(
            {
                "status": "failed",
                "workflow_version": "0.0.0",
                "workflow_root": str(workflow_root),
                "target_project_root": str(temp_dir),
                "last_step": "deploy-cli-assets",
                "error": "synthetic partial install marker for matrix validation",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _install_workflow(temp_dir: Path, workflow_root: Path, scenario: dict[str, Any], repo_root: Path) -> None:
    """Install the workflow during setup for upgrade-oriented scenarios."""
    env = os.environ.copy()
    env["WORKFLOW_EMBED_EXECUTOR_CONFIRMED"] = "1"
    env[SOURCE_REPO_ROOT_ENV] = str(repo_root)
    _run(
        [
            PYTHON_BIN,
            str(workflow_root / "commands" / "install-workflow.py"),
            "--project-root",
            str(temp_dir),
            "--profile",
            str(scenario["profile"]),
            "--cli",
            str(scenario["cli"]),
        ],
        cwd=repo_root,
        timeout=300,
        env=env,
    )


def setup_preinstalled_workflow(temp_dir: Path, workflow_root: Path, scenario: dict[str, Any], repo_root: Path) -> None:
    """Setup an already embedded workflow target for upgrade-compat validation."""
    setup_existing_customized(temp_dir, workflow_root, scenario, repo_root)
    _install_workflow(temp_dir, workflow_root, scenario, repo_root)

    record_path = temp_dir / ".trellis" / "workflow-installed.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["previous_workflow_version"] = record.get("workflow_version", "unknown")
    record["previous_workflow_schema_version"] = record.get("workflow_schema_version", "unknown")
    record["workflow_version"] = "0.0.0-matrix-legacy"
    record["workflow_schema_version"] = "2"
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def verify_trellis_baseline(temp_dir: Path) -> None:
    """Verify trellis init produced the baseline marker expected by all scenarios."""
    trellis_marker = temp_dir / ".trellis" / "scripts" / "task.py"
    if not trellis_marker.exists():
        raise RuntimeError("Trellis init failed - task.py not found")


SCENARIO_SETUP_MAP = {
    "clean": setup_clean,
    "existing-customized": setup_existing_customized,
    "failed-attempt": setup_failed_attempt,
    "preinstalled-workflow": setup_preinstalled_workflow,
}


def setup_scenario(scenario: dict[str, Any], temp_dir: Path, workflow_root: Path, repo_root: Path) -> None:
    """Setup a scenario in the given temp directory."""
    setup_name = str(scenario.get("setup", ""))
    if setup_name not in SCENARIO_SETUP_MAP:
        raise ValueError(f"Unknown scenario setup: {setup_name}")

    setup_func = SCENARIO_SETUP_MAP[setup_name]
    setup_func(temp_dir, workflow_root, scenario, repo_root)
    verify_trellis_baseline(temp_dir)
