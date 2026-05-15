#!/usr/bin/env python3
"""Tests for workflow-capability-audit execution helpers."""

from __future__ import annotations

import io
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch


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
RUNTIME_SESSIONS_DIR = REPO_ROOT / ".trellis" / ".runtime" / "sessions"
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
        self._pre_workflow_assets = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self._pre_developer = DEVELOPER_FILE.read_text(encoding="utf-8") if DEVELOPER_FILE.is_file() else None
        self._pre_runtime_sessions = {
            path.name: path.read_text(encoding="utf-8")
            for path in RUNTIME_SESSIONS_DIR.glob("*.json")
        } if RUNTIME_SESSIONS_DIR.is_dir() else {}
        self._fixture_dirs: list[Path] = []
        self._temp_dirs: list[Path] = []

    def tearDown(self) -> None:
        if TRELLIS_TASKS_DIR.is_dir():
            for d in TRELLIS_TASKS_DIR.iterdir():
                if d.name not in self._pre_task_dirs:
                    shutil.rmtree(d, ignore_errors=True)
        WORKFLOW_ASSETS.write_text(self._pre_workflow_assets, encoding="utf-8")
        if self._pre_developer is not None:
            DEVELOPER_FILE.write_text(self._pre_developer, encoding="utf-8")
        elif DEVELOPER_FILE.is_file():
            DEVELOPER_FILE.unlink()
        if RUNTIME_SESSIONS_DIR.is_dir():
            for path in RUNTIME_SESSIONS_DIR.glob("*.json"):
                if path.name not in self._pre_runtime_sessions:
                    path.unlink()
        else:
            RUNTIME_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in self._pre_runtime_sessions.items():
            (RUNTIME_SESSIONS_DIR / name).write_text(content, encoding="utf-8")
        for d in self._fixture_dirs:
            shutil.rmtree(d, ignore_errors=True)
        for d in self._temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _clear_active_test_audit_task(self) -> None:
        for session_path in RUNTIME_SESSIONS_DIR.glob("*.json"):
            try:
                payload = json.loads(session_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            current = payload.get("current_task")
            if isinstance(current, str) and "workflow-capability-audit" in current:
                session_path.unlink()

    def _release_fake_audit_task_for_followup(self) -> None:
        self._clear_active_test_audit_task()

    def _track_fixtures_from_payload(self, payload: dict) -> None:
        for key in ("a_root", "b_root"):
            path = Path(payload[key])
            if path.exists():
                self._fixture_dirs.append(path)

    def _set_repo_developer(self, name: str) -> None:
        DEVELOPER_FILE.write_text(f"name={name}\n", encoding="utf-8")

    def _session_file_for(self, context_id: str) -> Path:
        RUNTIME_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return RUNTIME_SESSIONS_DIR / f"{context_id}.json"

    def _write_session_current_task(self, context_id: str, task_ref: str) -> None:
        self._session_file_for(context_id).write_text(
            json.dumps({"current_task": task_ref}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_session_current_task(self, context_id: str) -> str | None:
        path = self._session_file_for(context_id)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload.get("current_task")
        return value if isinstance(value, str) else None

    def _remove_compatible_anchor(self) -> None:
        content = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "', content)
        content = re.sub(r'^COMPATIBLE_TRELLIS_VERSION = ".*"\n', "", content, count=1, flags=re.MULTILINE)
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
        merged_env["TRELLIS_CONTEXT_ID"] = "test-context"
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

    def _write_fake_audit_root(self, root: Path, developer_name: str, *, include_delivery: bool) -> None:
        (root / ".trellis" / "scripts").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / ".developer").write_text(f"name={developer_name}\n", encoding="utf-8")
        (root / ".trellis" / ".version").write_text("9.9.9\n", encoding="utf-8")
        (root / ".trellis" / "workflow.md").write_text("# fake workflow\n", encoding="utf-8")
        (root / ".trellis" / "scripts" / "task.py").write_text("# fake task helper\n", encoding="utf-8")
        (root / ".trellis" / "scripts" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".trellis" / "scripts" / "hooks" / "linear_sync.py").write_text("# hook script\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("# fake AGENTS\n", encoding="utf-8")

        (root / ".claude" / "commands" / "trellis").mkdir(parents=True, exist_ok=True)
        if include_delivery:
            (root / ".claude" / "commands" / "trellis" / "delivery.md").write_text(
                "# delivery\n",
                encoding="utf-8",
            )
        (root / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "agents" / "trellis-research.md").write_text("# research\n", encoding="utf-8")
        (root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "inject-workflow-state.py").write_text("# hook\n", encoding="utf-8")
        (root / ".claude" / "hooks" / "session-start.py").write_text("# hook\n", encoding="utf-8")
        (root / ".claude" / "hooks" / "inject-subagent-context.py").write_text("# hook\n", encoding="utf-8")
        (root / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

        (root / ".opencode" / "agents").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "agents" / "trellis-research.md").write_text("# research\n", encoding="utf-8")
        (root / ".opencode" / "plugins").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "package.json").write_text("{}", encoding="utf-8")
        (root / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "lib").mkdir(parents=True, exist_ok=True)

        (root / ".codex" / "agents").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "agents" / "trellis-research.toml").write_text('name = "trellis-research"\n', encoding="utf-8")
        (root / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")
        (root / ".codex" / "config.toml").write_text("[features.multi_agent_v2]\nenabled = true\n", encoding="utf-8")
        (root / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "hooks" / "inject-workflow-state.py").write_text("# hook\n", encoding="utf-8")

        (root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)

    def _make_fake_full_audit_roots(self, developer_name: str) -> tuple[Path, Path]:
        a_root = Path(tempfile.mkdtemp(prefix="workflow-capability-audit-a-"))
        b_root = Path(tempfile.mkdtemp(prefix="workflow-capability-audit-b-"))
        self._temp_dirs.extend([a_root, b_root])
        self._write_fake_audit_root(a_root, developer_name, include_delivery=False)
        self._write_fake_audit_root(b_root, developer_name, include_delivery=True)
        return a_root, b_root

    def _write_initial_managed_matrix_extras(self, root: Path) -> None:
        (root / ".trellis" / "workflow-installed.json").write_text("{}", encoding="utf-8")
        (root / ".trellis" / "library-lock.yaml").write_text(
            "packs:\n  - pack.requirements-discovery-foundation\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "spec" / "universal-domains" / "verification" / "evidence-requirements").mkdir(
            parents=True,
            exist_ok=True,
        )
        (root / ".trellis" / "spec" / "universal-domains" / "verification" / "evidence-requirements" / "overview.md").write_text(
            "# evidence requirements\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "spec" / "universal-domains" / "project-governance" / "readme-governance").mkdir(
            parents=True,
            exist_ok=True,
        )
        (root / ".trellis" / "spec" / "universal-domains" / "project-governance" / "readme-governance" / "overview.md").write_text(
            "# readme governance\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "checklists" / "universal-domains" / "product-and-requirements").mkdir(
            parents=True,
            exist_ok=True,
        )
        (root / ".trellis" / "checklists" / "universal-domains" / "product-and-requirements" / "developer-facing-prd-checklist.md").write_text(
            "# prd checklist\n",
            encoding="utf-8",
        )
        (root / ".trellis" / "workflow-docs").mkdir(parents=True, exist_ok=True)
        for card_name in ("需求变更管理执行卡.md", "源码水印与归属证据链执行卡.md"):
            (root / ".trellis" / "workflow-docs" / card_name).write_text(f"# {card_name}\n", encoding="utf-8")
        (root / "todo.txt").write_text("workflow todo\n", encoding="utf-8")
        (root / ".trellis" / ".backup-original").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "commands" / "trellis" / ".backup-original").mkdir(parents=True, exist_ok=True)
        (root / ".opencode" / "commands" / "trellis" / ".backup-original").mkdir(parents=True, exist_ok=True)
        (root / ".agents" / "skills" / ".backup-original").mkdir(parents=True, exist_ok=True)
        (root / ".codex" / "skills" / ".backup-original").mkdir(parents=True, exist_ok=True)

    def _create_fake_audit_task_dir(self, title: str, parent: str | None) -> str:
        existing = {
            d.name for d in TRELLIS_TASKS_DIR.iterdir() if d.is_dir()
        } if TRELLIS_TASKS_DIR.is_dir() else set()
        index = 1
        while True:
            dir_name = f"05-06-workflow-capability-audit-{index:02d}"
            if dir_name not in existing:
                break
            index += 1
        task_dir = TRELLIS_TASKS_DIR / dir_name
        task_dir.mkdir(parents=True, exist_ok=False)
        payload = {
            "title": title,
            "parent": Path(parent).name if parent else None,
            "children": [],
        }
        (task_dir / "task.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return f".trellis/tasks/{dir_name}"

    def _fake_managed_rows(self) -> list[dict[str, str]]:
        return [
            {
                "capability_id": "WM-001",
                "capability": "helper-script:workflow-state.py",
                "mechanism": "Workflow deploys shared helper scripts used across CLI carriers.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "B=.trellis/scripts/workflow/workflow-state.py",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "B=.trellis/scripts/workflow/workflow-state.py",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "B=.trellis/scripts/workflow/workflow-state.py",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            }
        ]

    def _fake_dependent_rows(self) -> list[dict[str, str]]:
        return [
            {
                "capability_id": "TN-001",
                "capability": "project-rules-and-routing-carrier",
                "mechanism": "Workflow depends on AGENTS-style project rules/routing as a shared long-lived carrier.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=AGENTS.md; B=AGENTS.md",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "A=AGENTS.md; B=AGENTS.md",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "A=AGENTS.md; B=AGENTS.md",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-002",
                "capability": "claude-hooks-and-settings-carrier",
                "mechanism": "Workflow may rely on Claude runtime hooks/settings that are Trellis-native or manually maintained rather than installer-managed.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=.claude/settings.json,.claude/hooks; B=.claude/settings.json,.claude/hooks",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "not-applicable",
                "opencode_classification": "not-applicable",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-003",
                "capability": "opencode-plugin-and-instructions-carrier",
                "mechanism": "Workflow may rely on OpenCode plugin/instruction carrier surfaces outside installer-managed workflow commands.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "A=.opencode/plugins,.opencode/package.json; B=.opencode/plugins,.opencode/package.json",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-004",
                "capability": "codex-hooks-and-config-carrier",
                "mechanism": "Workflow may rely on Codex hook/config surfaces outside installer-managed shared skills, and these surfaces can remain file-present while runtime activation is still gated by project trust plus higher-precedence hook/config decisions outside the embedded workflow files.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "not-applicable",
                "opencode_classification": "not-applicable",
                "codex_evidence": "A=.codex/hooks.json,.codex/config.toml,.codex/hooks/inject-workflow-state.py; B=.codex/hooks.json,.codex/config.toml,.codex/hooks/inject-workflow-state.py",
                "codex_classification": "present-but-gated-expected",
                "overall_summary": "present-but-gated-expected",
                "structural_signal": "carrier exists in A/B, but Codex runtime activation still depends on feature gates or user approval outside the embedded workflow files",
                "adaptation_decision": "Treat file presence and runtime activation as separate checks when judging Codex compatibility.",
            },
            {
                "capability_id": "TN-005",
                "capability": "implementation-agent-carrier",
                "mechanism": "Workflow depends on per-CLI implementation agent carrier directories even beyond installer ownership boundaries.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=.claude/agents/trellis-research.md,.claude/agents/trellis-implement.md,.claude/agents/trellis-check.md; B=.claude/agents/trellis-research.md,.claude/agents/trellis-implement.md,.claude/agents/trellis-check.md",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "A=.opencode/agents/trellis-research.md,.opencode/agents/trellis-implement.md,.opencode/agents/trellis-check.md; B=.opencode/agents/trellis-research.md,.opencode/agents/trellis-implement.md,.opencode/agents/trellis-check.md",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "A=.codex/agents/trellis-research.toml,.codex/agents/trellis-implement.toml,.codex/agents/trellis-check.toml; B=.codex/agents/trellis-research.toml,.codex/agents/trellis-implement.toml,.codex/agents/trellis-check.toml",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-006",
                "capability": "trellis-runtime-workflow-guide",
                "mechanism": "Workflow depends on Trellis runtime workflow guide and project runtime script surfaces.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "A=.trellis/workflow.md,.trellis/scripts/task.py; B=.trellis/workflow.md,.trellis/scripts/task.py",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-007",
                "capability": "shared-skills-deployment-carrier",
                "mechanism": "Workflow depends on .agents/skills/ as a shared deployment layer for OpenCode and Codex skills.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "A=.agents/skills; B=.agents/skills",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "A=.agents/skills; B=.agents/skills",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-008",
                "capability": "claude-native-skills-carrier",
                "mechanism": "Workflow depends on .claude/skills/ as the Claude-native skills carrier for repo-local maintainer skills.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=.claude/skills; B=.claude/skills",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "not-applicable",
                "opencode_classification": "not-applicable",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-009",
                "capability": "opencode-native-skills-carrier",
                "mechanism": "Workflow depends on .opencode/skills/ as the OpenCode-native skills carrier for repo-local skills.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "A=.opencode/skills; B=.opencode/skills",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-010",
                "capability": "opencode-lib-carrier",
                "mechanism": "Workflow depends on .opencode/lib/ as the OpenCode helper libraries carrier (e.g., trellis-context.js, session-utils.js).",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "A=.opencode/lib; B=.opencode/lib",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-011",
                "capability": "trellis-hooks-script-carrier",
                "mechanism": "Workflow depends on Trellis-side lifecycle hook scripts under .trellis/scripts/hooks/ rather than an older .trellis/hooks directory model.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "A=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py; B=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py",
                "claude_classification": "adopted-compatible",
                "opencode_evidence": "A=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py; B=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py",
                "opencode_classification": "adopted-compatible",
                "codex_evidence": "A=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py; B=.trellis/scripts/hooks,.trellis/scripts/hooks/linear_sync.py",
                "codex_classification": "adopted-compatible",
                "overall_summary": "adopted-compatible",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
            {
                "capability_id": "TN-012",
                "capability": "codex-secondary-skills-carrier",
                "mechanism": "Workflow must account for .codex/skills/ as a Codex-local/secondary skills carrier that may appear after trellis init, may hold Codex-only or project-local skills, and can affect duplicate shared-skill cleanup plus Codex-side runtime behavior.",
                "discovery_source": "ai-discovered",
                "claude_evidence": "not-applicable",
                "claude_classification": "not-applicable",
                "opencode_evidence": "not-applicable",
                "opencode_classification": "not-applicable",
                "codex_evidence": "not-applicable",
                "codex_classification": "not-applicable",
                "overall_summary": "not-applicable",
                "structural_signal": "none detected from A/B dependency surface shape",
                "adaptation_decision": "No action required in fresh B unless later compatibility analysis changes this.",
            },
        ]

    def run_script_with_fake_full_audit(
        self,
        *args: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        module = load_script_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged_env = os.environ.copy()
        merged_env["TRELLIS_CONTEXT_ID"] = "test-context"
        if env:
            merged_env.update(env)
        created_roots: list[Path] = []

        def fake_create_fixture_root(prefix: str, developer_name: str) -> Path:
            if not created_roots:
                created_roots.extend(self._make_fake_full_audit_roots(developer_name))
            if prefix.startswith("workflow-capability-audit-a-"):
                return created_roots[0]
            if prefix.startswith("workflow-capability-audit-b-"):
                return created_roots[1]
            raise AssertionError(f"Unexpected fixture prefix: {prefix}")

        def fake_run_task_create(title: str, parent: str | None) -> str:
            return self._create_fake_audit_task_dir(title, parent)

        def fake_run_task_start(task_dir: str) -> None:
            context_id = merged_env.get("TRELLIS_CONTEXT_ID", "test-context")
            self._write_session_current_task(context_id, task_dir)

        with (
            patch.dict(os.environ, merged_env, clear=False),
            patch.object(sys, "argv", [str(SCRIPT), *args]),
            patch.object(module, "run_task_create", side_effect=fake_run_task_create),
            patch.object(module, "run_task_start", side_effect=fake_run_task_start),
            patch.object(module, "create_fixture_root", side_effect=fake_create_fixture_root),
            patch.object(module, "install_workflow_into", return_value=None),
            patch.object(module, "detect_cli_types_from_roots", return_value=["claude", "opencode", "codex"]),
            patch.object(module, "build_workflow_managed_rows", return_value=self._fake_managed_rows()),
            patch.object(module, "build_workflow_dependent_rows", return_value=self._fake_dependent_rows()),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = module.main()
        return subprocess.CompletedProcess(
            args=[PYTHON, str(SCRIPT), *args],
            returncode=code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
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
        assets = load_assets_module()
        old_anchor = assets.COMPATIBLE_TRELLIS_VERSION
        module.update_compatible_anchor("0.5.0")
        current_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "0.5.0"', current_text)
        self.assertNotIn(f'COMPATIBLE_TRELLIS_VERSION = "{old_anchor}"', current_text)

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
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["gate_result"], "newer-version-continue")
        self.assertIn("task_dir", payload)
        self.assertIn("capability_report", payload)
        self.assertGreaterEqual(payload["managed_rows"], 1)
        self.assertGreaterEqual(payload["dependent_rows"], 1)
        self.assertIn(payload["structural_break_judgment"], {"no", "possible"})
        self._track_fixtures_from_payload(payload)

    def test_build_workflow_managed_rows_includes_confirmed_extra_managed_surfaces_in_initial_pass(self) -> None:
        assets = load_assets_module()
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("audit-dev")
        self._write_initial_managed_matrix_extras(b_root)
        agents_with_routing = "\n".join(
            [
                "# fake AGENTS",
                "<!-- workflow-nl-routing-start -->",
                "routing",
                "<!-- workflow-nl-routing-end -->",
            ]
        )
        (b_root / "AGENTS.md").write_text(agents_with_routing, encoding="utf-8")

        rows = module.build_workflow_managed_rows(a_root, b_root, ["claude", "opencode", "codex"])
        by_capability = {row["capability"]: row for row in rows}

        expected_capabilities = {
            "managed-enhanced-agent:trellis-research",
            "shared-artifact:todo-reminder-file",
            "shared-doc:execution-cards",
            "shared-artifact:workflow-installed-record",
            "shared-pack:requirements-discovery-foundation-import",
            "shared-doc:agents-nl-routing-block",
            "shared-state:backup-original-preservation",
        }
        self.assertTrue(expected_capabilities.issubset(by_capability))
        for capability in expected_capabilities:
            self.assertEqual(by_capability[capability]["discovery_source"], "ai-discovered")
            self.assertEqual(by_capability[capability]["overall_summary"], "adopted-compatible")
        self.assertIn("A=.claude/agents/trellis-research.md", by_capability["managed-enhanced-agent:trellis-research"]["claude_evidence"])
        self.assertIn("B=.codex/agents/trellis-research.toml", by_capability["managed-enhanced-agent:trellis-research"]["codex_evidence"])
        self.assertEqual(by_capability["shared-artifact:todo-reminder-file"]["codex_evidence"], "B=todo.txt")

    def test_build_workflow_managed_rows_requires_agents_routing_markers_for_routing_capability(self) -> None:
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("audit-dev")
        rows = module.build_workflow_managed_rows(a_root, b_root, ["claude", "opencode", "codex"])
        by_capability = {row["capability"]: row for row in rows}
        routing_row = by_capability["shared-doc:agents-nl-routing-block"]
        self.assertEqual(routing_row["overall_summary"], "not-applicable")

    def test_insert_matrix_row_keeps_supplemental_managed_rows_after_initial_ai_discovered_rows(self) -> None:
        module = load_script_module()
        report_text = "\n".join(
            [
                "## Workflow-Managed Surface Matrix",
                "",
                "| Capability ID | Capability | Latest Trellis Mechanism / Benefit | Discovery Source | Claude Evidence | Claude Classification | OpenCode Evidence | OpenCode Classification | Codex Evidence | Codex Classification | Overall Summary | Structural Signal | Adaptation Decision |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
                "| WM-001 | alpha | alpha mech | ai-discovered | B=alpha | adopted-compatible | B=alpha | adopted-compatible | B=alpha | adopted-compatible | adopted-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |",
                "| WM-002 | shared-doc:workflow.md | workflow mech | ai-discovered | B=.trellis/workflow.md | patched-compatible | B=.trellis/workflow.md | patched-compatible | B=.trellis/workflow.md | patched-compatible | patched-compatible | none detected from A/B surface shape | No action required in fresh B unless later compatibility analysis changes this. |",
                "",
                "## Workflow-Dependent Trellis-Native Surface Matrix",
                "",
            ]
        )
        inserted = module.insert_matrix_row(
            report_text,
            "## Workflow-Managed Surface Matrix",
            "| WM-099 | aaa-supplemental | supplemental mech | supplemental-confirmed | B=aaa | adopted-compatible | B=aaa | adopted-compatible | B=aaa | adopted-compatible | adopted-compatible | none detected from supplemental validation | No action required unless later confirmed compatibility analysis changes this. |",
            "aaa-supplemental",
        )
        managed_section = _extract_section(inserted, "## Workflow-Managed Surface Matrix")
        matrix_lines = [line for line in managed_section.splitlines() if line.startswith("| WM-")]
        self.assertEqual([line.split("|")[2].strip() for line in matrix_lines], ["alpha", "shared-doc:workflow.md", "aaa-supplemental"])

    def test_full_audit_uses_repo_developer_identity_for_fresh_fixtures(self) -> None:
        assets = load_assets_module()
        self._set_repo_developer("audit-dev")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
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
        context_id = "test-failure-cleanup"
        original_task = ".trellis/tasks/03-19-implement-agents-source"
        self._write_session_current_task(context_id, original_task)
        env = {
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "TMPDIR": str(controlled_tmp),
            "TRELLIS_CONTEXT_ID": context_id,
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        current_task = self._read_session_current_task(context_id)
        self.assertEqual(current_task, original_task)
        current_task_dirs = set(d.name for d in TRELLIS_TASKS_DIR.iterdir()) if TRELLIS_TASKS_DIR.is_dir() else set()
        self.assertEqual(current_task_dirs, self._pre_task_dirs)
        self.assertEqual(list(controlled_tmp.iterdir()), [])

    def test_full_audit_rejects_preexisting_top_level_audit_directory_without_deleting_it(self) -> None:
        assets = load_assets_module()
        today_prefix = date.today().strftime("%m-%d")
        existing_task_dir = self._create_task_dir(
            f"{today_prefix}-workflow-capability-audit",
            "workflow-capability-audit: 新项目开发工作流",
        )
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "claude", "--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("task directory already exists", result.stderr)
        self.assertTrue(existing_task_dir.is_dir())

    def test_codex_full_audit_python_probe_failure_reports_runtime_boundary_recheck(self) -> None:
        assets = load_assets_module()
        context_id = "test-codex-runtime-boundary"
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
            "TRELLIS_CONTEXT_ID": context_id,
        }
        module = load_script_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged_env = os.environ.copy()
        merged_env.update(env)

        task_dir_ref = self._create_fake_audit_task_dir(
            "workflow-capability-audit: 新项目开发工作流",
            None,
        )
        self._clear_active_test_audit_task()
        existing_names = {
            d.name for d in TRELLIS_TASKS_DIR.iterdir() if d.is_dir()
        }
        collision_name = Path(task_dir_ref).name
        self.assertIn(collision_name, existing_names)
        next_index = 1
        while True:
            candidate = f"05-06-workflow-capability-audit-{next_index:02d}"
            if candidate not in existing_names:
                break
            next_index += 1
        self.assertNotEqual(candidate, collision_name)

        def fake_run_task_create(title: str, parent: str | None) -> str:
            return f".trellis/tasks/{candidate}"

        def fake_run_task_start(task_dir: str) -> None:
            self._write_session_current_task(context_id, task_dir)

        failure = subprocess.CalledProcessError(
            returncode=1,
            cmd=["trellis", "init", "--claude", "--opencode", "--codex", "-u", "audit-dev", "-y"],
            stderr='Error: Python command "python3" not found. Trellis init requires Python ≥ 3.9.',
        )

        with (
            patch.dict(os.environ, merged_env, clear=False),
            patch.object(sys, "argv", [str(SCRIPT), "--current-cli", "codex", "--json"]),
            patch.object(module, "run_task_create", side_effect=fake_run_task_create),
            patch.object(module, "run_task_start", side_effect=fake_run_task_start),
            patch.object(module, "create_fixture_root", side_effect=failure),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = module.main()

        self.assertNotEqual(code, 0, msg=stdout.getvalue() + stderr.getvalue())
        self.assertIn("Codex runtime boundary", stderr.getvalue())
        self.assertIn("real shell, Claude Code, or OpenCode", stderr.getvalue())
        self.assertIn('Python command "python3" not found', stderr.getvalue())

    def test_full_audit_creates_child_task_when_current_task_is_workflow_audit(self) -> None:
        assets = load_assets_module()
        context_id = "test-child-audit-task"
        current_task_dir = self._create_task_dir(
            "05-03-existing-workflow-audit",
            "workflow-audit: 新项目开发工作流",
        )
        self._write_session_current_task(context_id, f".trellis/tasks/{current_task_dir.name}")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
            "TRELLIS_CONTEXT_ID": context_id,
        }
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        task_json = REPO_ROOT / payload["task_dir"] / "task.json"
        task_data = json.loads(task_json.read_text(encoding="utf-8"))
        self.assertEqual(task_data["parent"], current_task_dir.name)

    def test_full_audit_stops_when_current_task_is_workflow_capability_audit(self) -> None:
        assets = load_assets_module()
        context_id = "test-existing-capability-audit"
        current_task_dir = self._create_task_dir(
            "05-03-existing-workflow-capability-audit",
            "workflow-capability-audit: 新项目开发工作流",
        )
        self._write_session_current_task(context_id, f".trellis/tasks/{current_task_dir.name}")
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
            "TRELLIS_CONTEXT_ID": context_id,
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

    def test_full_audit_fails_when_current_cli_is_invalid(self) -> None:
        """Invalid --current-cli must fail before creating fixtures or a task."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script("--current-cli", "invalid-cli", "--json", env=env)
        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("--current-cli must be one of", result.stderr)

    def test_supplemental_capability_updates_same_report(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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
        self.assertEqual(second_payload["capability_report"], second_payload["report_path"])
        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("custom-supplemental-capability", report_text)
        self.assertIn("supplemental-confirmed", report_text)

    def test_supplemental_confirmed_preserves_structural_break_single_line_format(self) -> None:
        """After supplemental-confirmed, Structural-Break Judgment must stay single-line Why/Required next action."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9"}
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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
        self.assertEqual(second_payload["capability_report"], second_payload["report_path"])

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
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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
        self.assertEqual(second_payload["capability_report"], second_payload["report_path"])

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
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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
        self.assertEqual(second_payload["capability_report"], second_payload["report_path"])
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
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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
        self.assertEqual(second_payload["capability_report"], second_payload["report_path"])
        report_path = REPO_ROOT / second_payload["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("Confirm patch markers and capability matrix updates.", report_text)
        self.assertIn("Updated workflow source for Trellis version-upgrade compatibility.", report_text)
        self.assertIn("Revalidated capability report after confirmed correction.", report_text)
        self.assertIn("- Destroyed: yes", report_text)
        self.assertIn("- Final destruction confirmed by user: yes", report_text)
        self.assertIn("none pending; A/B fixture destruction already finalized for this audit round.", report_text)
        self.assertNotIn("whether to proceed from audit into confirmed compatibility-fix work", report_text)

    def test_fix_lifecycle_confirmed_scope_switches_stop_point_to_fixture_destruction_confirmation(self) -> None:
        """Confirming fix scope alone must NOT promote the anchor — only post-fix revalidation or finalization allows that."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', before_text)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirm patch markers and capability matrix updates.",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        report_path = REPO_ROOT / json.loads(second.stdout)["report_path"]
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("whether to finalize A/B fixture destruction after post-fix revalidation is complete", report_text)
        self.assertNotIn("whether to proceed from audit into confirmed compatibility-fix work", report_text)

        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertEqual(after_text, before_text, "Anchor must NOT be promoted when only confirm-fix-scope is recorded")

    def test_fix_lifecycle_promotes_anchor_when_no_fix_scope_but_lifecycle_entered(self) -> None:
        """Anchor must promote when post-fix revalidation + finalize are both present, even without --confirm-fix-scope."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', before_text)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--record-correction",
            "No source edits needed; workflow already compatible as-is.",
            "--record-revalidation",
            "Revalidated: workflow remains fully compatible after upgrade.",
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', after_text)

    def test_fix_lifecycle_promotes_anchor_when_compatible_as_is_with_revalidation_and_finalize(self) -> None:
        """No-fix compatible audits must still be able to promote the anchor after explicit revalidation + finalize."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', before_text)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirmed compatible as-is; no workflow source corrections required.",
            "--record-revalidation",
            "Revalidated compatible-as-is conclusion against final A/B evidence before fixture destruction.",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self._release_fake_audit_task_for_followup()

        third = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertEqual(third.returncode, 0, msg=third.stdout + third.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', after_text)

    def test_fix_lifecycle_does_not_promote_anchor_on_revalidation_without_finalize(self) -> None:
        """Post-fix revalidation alone must NOT promote anchor — finalization is also required."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', before_text)

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
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertEqual(after_text, before_text, "Anchor must NOT promote when revalidation is recorded but fixture destruction is not finalized")

    def test_fix_lifecycle_promotes_anchor_when_finalize_and_revalidation_recorded(self) -> None:
        """Anchor must promote when finalize is passed and revalidation was recorded in a prior call."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")

        # Record corrections + revalidation first
        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirm patch markers.",
            "--record-correction",
            "Updated workflow source.",
            "--record-revalidation",
            "Revalidated.",
            env=env,
        )
        self.assertEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self._release_fake_audit_task_for_followup()

        # Finalize — revalidation was recorded in a prior call, so the report has revalidation items
        # This MUST promote anchor because the report already has post-fix revalidation recorded
        third = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertEqual(third.returncode, 0, msg=third.stdout + third.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', after_text,
                       "Anchor must promote when finalizing and report already has revalidation recorded")

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
        current_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertEqual(current_text, self._pre_workflow_assets)

    def test_fix_lifecycle_requires_completed_fix_evidence_before_fixture_destruction(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

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

    def test_fix_lifecycle_does_not_promote_anchor_before_validation_succeeds(self) -> None:
        """confirm-fix-scope + finalize (without revalidation) must fail AND not promote anchor."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertNotIn('COMPATIBLE_TRELLIS_VERSION = "9.9.9"', before_text)

        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirm patch markers and capability matrix updates.",
            "--finalize-fixture-destruction",
            env=env,
        )
        self.assertNotEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertEqual(after_text, before_text)

    def test_fix_lifecycle_confirm_fix_scope_requires_parseable_current_version_for_anchor_promotion(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        before_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        bad_env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "not-a-version",
        }
        second = self.run_script(
            "--json",
            "--task-dir",
            payload["task_dir"],
            "--confirm-fix-scope",
            "Confirm patch markers and capability matrix updates.",
            env=bad_env,
        )
        self.assertNotEqual(second.returncode, 0, msg=second.stdout + second.stderr)
        self.assertIn("not parseable semver", second.stderr)
        after_text = WORKFLOW_ASSETS.read_text(encoding="utf-8")
        self.assertEqual(after_text, before_text)

    def test_supplemental_validation_reports_missing_section_heading_cleanly(self) -> None:
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()
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
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        report_path = REPO_ROOT / payload["capability_report"]
        report_text = report_path.read_text(encoding="utf-8")

        for section_heading in ["## Confirmed Fix Scope", "## Applied Corrections", "## Post-Fix Revalidation"]:
            section = _extract_section(report_text, section_heading)
            self.assertIn("- none yet", section, f"{section_heading} must contain '- none yet'")
            self.assertNotRegex(section, r"<.+>", f"{section_heading} must not contain angle-bracket placeholders")

    def test_initial_report_contains_native_cli_adaptation_evidence_section(self) -> None:
        """Initial report must include the Native CLI Adaptation Evidence section with Step B guidance."""
        assets = load_assets_module()
        env = {assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9"}
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)
        report_path = REPO_ROOT / payload["capability_report"]
        report_text = report_path.read_text(encoding="utf-8")

        section = _extract_section(report_text, "## Native CLI Adaptation Evidence")
        self.assertIn("## Native CLI Adaptation Evidence", section)
        self.assertIn("<!-- Fill this section during Step B AI review unless the execution engine already prefilled it. -->", section)
        self.assertIn("- Claude Code:", section)
        self.assertIn("- OpenCode:", section)
        self.assertIn("- Codex:", section)
        self.assertIn("- Discrepancy resolution:", section)
        self.assertIn("  - Official docs source:", section)
        self.assertIn("  - Repo-local evidence:", section)
        self.assertIn("  - Agreement / discrepancy:", section)

    def test_shared_skills_deployment_carrier_appears_in_dependent_surface(self) -> None:
        """shared-skills-deployment-carrier (TN-007) must appear in the dependent surface matrix."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        result = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self._track_fixtures_from_payload(payload)

        # Assert dependent_rows >= 12 (7 original + 4 new carriers + codex-secondary-skills-carrier)
        self.assertGreaterEqual(payload["dependent_rows"], 12)

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

    def test_build_workflow_dependent_rows_marks_codex_hook_carrier_as_present_but_gated(self) -> None:
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("audit-dev")
        rows = module.build_workflow_dependent_rows(a_root, b_root)
        by_capability = {row["capability"]: row for row in rows}
        codex_row = by_capability["codex-hooks-and-config-carrier"]
        self.assertEqual(codex_row["codex_classification"], "present-but-gated-expected")
        self.assertEqual(codex_row["overall_summary"], "present-but-gated-expected")
        self.assertNotIn("session-start.py", codex_row["codex_evidence"])

    def test_build_workflow_dependent_rows_uses_trellis_hooks_script_carrier(self) -> None:
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("audit-dev")
        rows = module.build_workflow_dependent_rows(a_root, b_root)
        by_capability = {row["capability"]: row for row in rows}
        hooks_row = by_capability["trellis-hooks-script-carrier"]
        self.assertEqual(hooks_row["overall_summary"], "adopted-compatible")
        self.assertIn(".trellis/scripts/hooks", hooks_row["claude_evidence"])
        self.assertNotIn(".trellis/hooks", hooks_row["claude_evidence"])

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

    def test_structural_break_human_output_matches_reference_template_headings(self) -> None:
        """Human-readable structural-break output must stay aligned with the maintained template headings."""
        template_path = REPO_ROOT / ".claude" / "skills" / "workflow-capability-audit" / "references" / "structural-break-possible-template.md"
        template_text = template_path.read_text(encoding="utf-8")
        expected_headings = [
            "## Structural-Break Judgment — Possible",
            "### Why Judgment Is Not Yet Definitive",
            "### Structural-Break Signals Observed",
            "### Why Normal Adaptation Cannot Be Safely Recommended Yet",
            "### What Additional Confirmation Or Analysis Is Needed",
            "### Decision Required",
        ]
        module = load_script_module()
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            module.print_structural_possible_human(["signal-1"])
        output = stdout.getvalue()
        for heading in expected_headings:
            self.assertIn(heading, template_text)
            self.assertIn(heading, output)

    def test_full_audit_non_json_structural_break_path_emits_template_and_payload(self) -> None:
        """Non-JSON full-audit output must emit the structural-break template before the payload JSON."""
        module = load_script_module()
        assets = load_assets_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        merged_env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
            "TRELLIS_CONTEXT_ID": "test-non-json-structural-break",
        }
        created_roots: list[Path] = []

        def fake_create_fixture_root(prefix: str, developer_name: str) -> Path:
            if not created_roots:
                created_roots.extend(self._make_fake_full_audit_roots(developer_name))
            if prefix.startswith("workflow-capability-audit-a-"):
                return created_roots[0]
            if prefix.startswith("workflow-capability-audit-b-"):
                return created_roots[1]
            raise AssertionError(f"Unexpected fixture prefix: {prefix}")

        def fake_run_task_create(title: str, parent: str | None) -> str:
            return self._create_fake_audit_task_dir(title, parent)

        def fake_run_task_start(task_dir: str) -> None:
            self._write_session_current_task(merged_env["TRELLIS_CONTEXT_ID"], task_dir)

        with (
            patch.dict(os.environ, merged_env, clear=False),
            patch.object(sys, "argv", [str(SCRIPT), "--current-cli", "claude"]),
            patch.object(module, "run_task_create", side_effect=fake_run_task_create),
            patch.object(module, "run_task_start", side_effect=fake_run_task_start),
            patch.object(module, "create_fixture_root", side_effect=fake_create_fixture_root),
            patch.object(module, "install_workflow_into", return_value=None),
            patch.object(module, "detect_cli_types_from_roots", return_value=["claude", "opencode", "codex"]),
            patch.object(module, "build_workflow_managed_rows", return_value=self._fake_managed_rows()),
            patch.object(module, "build_workflow_dependent_rows", return_value=self._fake_dependent_rows()),
            patch.object(module, "derive_structural_break", return_value=("possible", ["signal-1"], "needs confirmation")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = module.main()

        self.assertEqual(code, 0, msg=stdout.getvalue() + stderr.getvalue())
        output = stdout.getvalue()
        self.assertIn("## Structural-Break Judgment — Possible", output)
        self.assertIn("signal-1", output)
        self.assertIn('"structural_break_judgment": "possible"', output)
        self.assertEqual("", stderr.getvalue())

    def test_supplemental_capability_with_specific_gated_value_requests_followup(self) -> None:
        """Supplemental rows using present-but-gated-* values must still mark follow-up structural attention."""
        assets = load_assets_module()
        env = {
            assets.CURRENT_TRELLIS_VERSION_ENV: "9.9.9",
        }
        first = self.run_script_with_fake_full_audit("--current-cli", "claude", "--json", env=env)
        self.assertEqual(first.returncode, 0, msg=first.stdout + first.stderr)
        payload = json.loads(first.stdout)
        self._track_fixtures_from_payload(payload)
        self._release_fake_audit_task_for_followup()

        module = load_script_module()
        task_dir = REPO_ROOT / payload["task_dir"]
        with patch.object(
            module,
            "_evidence_and_classification",
            side_effect=[
                ("not-applicable", "not-applicable", False),
                ("not-applicable", "not-applicable", False),
                ("A=.codex/hooks.json; B=.codex/hooks.json", "present-but-gated-expected", True),
            ],
        ):
            result = module.validate_supplemental_capability(
                task_dir,
                "codex-gated-supplement",
                "workflow-dependent-native",
                "Supplemental Codex-gated capability.",
                [],
                [],
                [".codex/hooks.json"],
            )

        self.assertEqual(result["mode"], "supplemental-confirmed")
        report_text = (task_dir / "capability-report.md").read_text(encoding="utf-8")
        gated_row = next(
            line for line in report_text.splitlines()
            if "| codex-gated-supplement |" in line
        )
        self.assertIn("present-but-gated-expected", gated_row)
        self.assertIn(
            "supplemental capability indicates additional compatibility attention may be required",
            gated_row,
        )

    def test_new_carriers_discovered_by_real_directory_scan(self) -> None:
        """Integration test: TN-008~TN-011 carriers must appear when using real build_workflow_dependent_rows (not mocked)."""
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("carrier-dev")

        rows = module.build_workflow_dependent_rows(a_root, b_root)
        by_capability = {row["capability"]: row for row in rows}

        new_carriers = [
            ("claude-native-skills-carrier", "claude", "adopted-compatible"),
            ("opencode-native-skills-carrier", "opencode", "adopted-compatible"),
            ("opencode-lib-carrier", "opencode", "adopted-compatible"),
            ("trellis-hooks-script-carrier", "claude", "adopted-compatible"),
        ]
        for carrier_name, primary_cli, expected_classification in new_carriers:
            self.assertIn(carrier_name, by_capability, f"{carrier_name} must appear in dependent rows")
            row = by_capability[carrier_name]
            self.assertEqual(row[f"{primary_cli}_classification"], expected_classification,
                             f"{carrier_name} {primary_cli} classification must be {expected_classification}")

        # Verify codex-hooks-and-config-carrier now includes .codex/hooks/ scripts but no session-start requirement
        codex_carrier = by_capability.get("codex-hooks-and-config-carrier")
        self.assertIsNotNone(codex_carrier)
        self.assertIn(".codex/hooks/inject-workflow-state.py", codex_carrier["codex_evidence"])
        self.assertNotIn("session-start.py", codex_carrier["codex_evidence"])
        self.assertEqual(codex_carrier["codex_classification"], "present-but-gated-expected")

    def test_expected_gated_rows_do_not_trigger_structural_break(self) -> None:
        module = load_script_module()
        managed_rows = self._fake_managed_rows()
        dependent_rows = self._fake_dependent_rows()

        result, signals, why = module.derive_structural_break(managed_rows, dependent_rows)

        self.assertEqual(result, "no")
        self.assertEqual(signals, [])
        self.assertIn("does not show structural-break signals", why)

    def test_unexpected_gated_rows_still_trigger_structural_break(self) -> None:
        module = load_script_module()
        managed_rows = self._fake_managed_rows()
        dependent_rows = self._fake_dependent_rows()
        dependent_rows[3] = {
            **dependent_rows[3],
            "codex_classification": "present-but-gated-unexpected",
            "overall_summary": "present-but-gated-unexpected",
            "structural_signal": "runtime activation became gated unexpectedly in the current A/B audit",
        }

        result, signals, why = module.derive_structural_break(managed_rows, dependent_rows)

        self.assertEqual(result, "possible")
        self.assertEqual(len(signals), 1)
        self.assertIn("present-but-gated-unexpected", signals[0])
        self.assertIn("High-action compatibility findings", why)

    def test_codex_secondary_skills_carrier_is_adopted_compatible_when_present(self) -> None:
        """codex-secondary-skills-carrier must be adopted-compatible when .codex/skills/ exists in A/B."""
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("carrier-dev")

        # Create .codex/skills/ in both A and B
        (a_root / ".codex" / "skills").mkdir(parents=True, exist_ok=True)
        (b_root / ".codex" / "skills").mkdir(parents=True, exist_ok=True)

        rows = module.build_workflow_dependent_rows(a_root, b_root)
        by_capability = {row["capability"]: row for row in rows}

        codex_sec = by_capability.get("codex-secondary-skills-carrier")
        self.assertIsNotNone(codex_sec)
        self.assertEqual(codex_sec["codex_classification"], "adopted-compatible")
        self.assertIn(".codex/skills", codex_sec["codex_evidence"])

        # shared-skills-deployment-carrier must NOT include .codex/skills/
        shared_row = by_capability.get("shared-skills-deployment-carrier")
        self.assertIsNotNone(shared_row)
        self.assertNotIn(".codex/skills", shared_row["codex_evidence"])
        self.assertEqual(shared_row["codex_classification"], "adopted-compatible")

    def test_codex_secondary_skills_carrier_is_missing_but_valuable_when_only_in_A(self) -> None:
        """codex-secondary-skills-carrier must be missing-but-valuable for Codex when .codex/skills/ exists in A but not B."""
        module = load_script_module()
        a_root, b_root = self._make_fake_full_audit_roots("carrier-a-only")

        # Create .codex/skills/ in A only
        (a_root / ".codex" / "skills").mkdir(parents=True, exist_ok=True)

        rows = module.build_workflow_dependent_rows(a_root, b_root)
        by_capability = {row["capability"]: row for row in rows}

        codex_sec = by_capability.get("codex-secondary-skills-carrier")
        self.assertIsNotNone(codex_sec)
        self.assertEqual(codex_sec["codex_classification"], "missing-but-valuable",
                         "codex-secondary-skills-carrier must be missing-but-valuable when .codex/skills/ exists in A but not B")
        self.assertEqual(codex_sec["overall_summary"], "missing-but-valuable")

    def test_full_audit_failure_removes_child_link_from_parent_task(self) -> None:
        """If child audit setup fails after task creation, parent.children must not keep a stale child reference."""
        assets = load_assets_module()
        parent_task_dir = self._create_task_dir(
            "05-03-existing-workflow-audit",
            "workflow-audit: 新项目开发工作流",
        )
        self._write_session_current_task("test-parent-child-link", f".trellis/tasks/{parent_task_dir.name}")

        created_child_ref = self._create_fake_audit_task_dir(
            "workflow-capability-audit: 新项目开发工作流",
            f".trellis/tasks/{parent_task_dir.name}",
        )
        child_name = Path(created_child_ref).name
        parent_json_path = parent_task_dir / "task.json"
        parent_data = json.loads(parent_json_path.read_text(encoding="utf-8"))
        parent_data["children"] = [child_name]
        parent_json_path.write_text(json.dumps(parent_data, ensure_ascii=False, indent=2), encoding="utf-8")

        module = load_script_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        env = os.environ.copy()
        env[assets.CURRENT_TRELLIS_VERSION_ENV] = "9.9.9"
        env["TRELLIS_CONTEXT_ID"] = "test-parent-child-link"

        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(sys, "argv", [str(SCRIPT), "--current-cli", "claude", "--json"]),
            patch.object(module, "run_task_create", return_value=created_child_ref),
            patch.object(module, "run_task_start", side_effect=RuntimeError("simulated setup failure")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = module.main()

        self.assertNotEqual(code, 0, msg=stdout.getvalue() + stderr.getvalue())
        updated_parent = json.loads(parent_json_path.read_text(encoding="utf-8"))
        self.assertNotIn(child_name, updated_parent.get("children", []))

    def test_full_audit_failure_warns_when_active_task_cannot_be_restored_without_context(self) -> None:
        """Rollback cleanup must not fail just because the previous session-scoped task cannot be restored."""
        module = load_script_module()
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_active = module.ActiveTask(
            ".trellis/tasks/03-19-implement-commands-source",
            "session",
            "missing-context",
        )
        with (
            patch.dict(os.environ, {"TRELLIS_CURRENT_VERSION": "9.9.9", "TRELLIS_CONTEXT_ID": "test-missing-context"}, clear=False),
            patch.object(sys, "argv", [str(SCRIPT), "--current-cli", "claude", "--json"]),
            patch.object(module, "resolve_active_task", return_value=original_active),
            patch.object(module, "set_active_task", return_value=None),
            patch.object(module, "run_task_create", return_value=".trellis/tasks/05-08-workflow-capability-audit"),
            patch.object(module, "run_task_start", side_effect=RuntimeError("simulated start failure")),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            code = module.main()
        self.assertNotEqual(code, 0, msg=stdout.getvalue() + stderr.getvalue())
        self.assertIn("WARN: Could not restore the previous session-scoped active task", stderr.getvalue())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
