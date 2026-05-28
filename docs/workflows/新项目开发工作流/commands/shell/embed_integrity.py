#!/usr/bin/env python3
"""Embedded-workflow integrity checks for workflow-state routing.

The strong-gate router must refuse to continue when runtime-critical carrier
patches or helper semantics are actually broken. However, target projects may
legitimately accumulate low-risk textual drift in distributed command copies or
patch marker placement. This module therefore distinguishes:

- fatal integrity failures: runtime behavior is no longer trustworthy
- advisory drift warnings: embed still works, but source/target copies drifted
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from state_utils import INSTALL_RECORD, read_json  # noqa: E402


LIBRARY_LOCK = ".trellis/library-lock.yaml"
REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"
CRITICAL_RUNTIME_PATCH_NAMES = (
    "inject-workflow-state",
    "claude-inject-subagent-context",
    "opencode-inject-subagent-context",
    "session-start-strong-gate",
    "task-start-strong-gate",
    "task-create-preserve-active",
    "task-status-view-strong-gate",
    "workflow-phase-strong-gate",
)
INJECT_WORKFLOW_STATE_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-state-json]"
OPENCODE_INJECT_WORKFLOW_STATE_PATCH_MARKER = "// [workflow-embed-patch:prefer-workflow-state-json]"
OPENCODE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER = "// [workflow-embed-patch:opencode-subagent-gates]"
CLAUDE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER = "# [workflow-embed-patch:claude-subagent-gates]"
SESSION_START_STRONG_GATE_PATCH_MARKER = "# strong-gate-session-start-patch-applied"
OPENCODE_SESSION_UTILS_PATCH_MARKER = "// [workflow-embed-patch:strong-gate-session-utils]"
TASK_START_STRONG_GATE_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-no-status-flip]"
TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER = "# [workflow-embed-patch:preserve-parent-active-task]"
TASK_STATUS_VIEW_PATCH_MARKER = "# [workflow-embed-patch:strong-gate-task-status-view]"
WORKFLOW_PHASE_STRONG_GATE_PATCH_MARKER = "# strong-gate-phase-patch-applied"
DISTRIBUTED_COMMAND_NAMES = (
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "project-audit",
    "check",
    "review-gate",
    "delivery",
)
CODEX_PHASE_ROUTER_SKILL_MARKER = "## Workflow Phase Router Patch `[AI]`"
CODEX_FINISH_WORK_SKILL_MARKER = "<!-- finish-work-projectization-patch -->"
PATCHED_CODEX_SKILL_REQUIREMENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "trellis-continue": {
        "must_contain": (
            CODEX_PHASE_ROUTER_SKILL_MARKER,
            "workflow router",
            "workflow-state.py route",
            "Do not use `status=planning` / `status=in_progress`",
            "stay in the current phase-router entry",
            "Do not assume a public `implementation` skill exists.",
        ),
        "must_not_contain": (
            "figures out which phase/step to pick up at",
            "task state shows planning",
            "task state shows in progress",
            "implementation done, not yet checked",
            "check passed",
            "Load the Specific Step",
        ),
    },
    "trellis-finish-work": {
        "must_contain": (
            CODEX_FINISH_WORK_SKILL_MARKER,
            "complete native Trellis close-out after delivery",
            "archive + session-record steps after delivery",
            "Code commits are NOT done here",
        ),
        "must_not_contain": (
            "archive completed tasks, and record session progress to the developer journal",
        ),
    },
    "trellis-start": {
        "must_contain": (
            CODEX_PHASE_ROUTER_SKILL_MARKER,
            "workflow router",
            "workflow-state.py route",
            "Do not use `status=planning` / `status=in_progress`",
            "stay in the current phase-router entry",
            "Do not assume a public `implementation` skill exists.",
            "| New feature / unclear requirements | `brainstorm` |",
            "| About to write code | `trellis-continue` |",
            "| Done coding / quality check | `check` |",
        ),
        "must_not_contain": (
            "routes to brainstorm, direct edit, or task workflow",
            "task state shows planning",
            "task state shows in progress",
            "implementation done, not yet checked",
            "check passed",
            "Load the Specific Step",
            "| New feature / unclear requirements | `trellis-brainstorm` |",
            "| About to write code | `trellis-before-dev` |",
            "| Done coding / quality check | `trellis-check` |",
        ),
    },
    "trellis-brainstorm": {
        "must_contain": (
            "Workflow note: in projects that installed `docs/workflows/新项目开发工作流`",
            "All new implementation work must still pass `/trellis:feasibility` first.",
            "assessment.md",
        ),
        "must_not_contain": (
            "Triggered from `start` (Trellis command)",
            "| ``start` (Trellis command)` | Entry point that triggers brainstorm |",
            "[`research/<topic-a>.md`](research/<topic-a>.md)",
            "[`research/<topic-b>.md`](research/<topic-b>.md)",
        ),
    },
}


def _load_install_record_data(install_record: Path) -> dict[str, Any]:
    data = read_json(install_record)
    return data if isinstance(data, dict) else {}


def _install_record_cli_types(record: dict[str, Any]) -> set[str]:
    cli_types = record.get("cli_types")
    if not isinstance(cli_types, list):
        return set()
    return {str(item) for item in cli_types if isinstance(item, str)}


def _codex_session_start_is_wired(repo_root: Path) -> bool:
    hooks_json = repo_root / ".codex" / "hooks.json"
    if not hooks_json.is_file():
        return False
    try:
        payload = json.loads(hooks_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    return "session-start.py" in json.dumps(payload, ensure_ascii=False)


def _expected_critical_runtime_patches(repo_root: Path, record: dict[str, Any]) -> set[str]:
    cli_types = _install_record_cli_types(record)
    if cli_types:
        expected = {
            "inject-workflow-state",
            "task-start-strong-gate",
            "task-create-preserve-active",
            "task-status-view-strong-gate",
            "workflow-phase-strong-gate",
        }
        if cli_types & {"claude", "opencode"}:
            expected.add("session-start-strong-gate")
        if "claude" in cli_types:
            expected.add("claude-inject-subagent-context")
        if "opencode" in cli_types:
            expected.add("opencode-inject-subagent-context")
        if "codex" in cli_types and _codex_session_start_is_wired(repo_root):
            expected.add("session-start-strong-gate")
        return expected

    configured = record.get("critical_runtime_patches")
    if isinstance(configured, list):
        return {
            str(item)
            for item in configured
            if isinstance(item, str) and item in CRITICAL_RUNTIME_PATCH_NAMES
        }
    return set(CRITICAL_RUNTIME_PATCH_NAMES)


def _critical_patch_paths(repo_root: Path, cli_types: set[str]) -> list[tuple[str, Path, str]]:
    codex_session_start_wired = "codex" in cli_types and _codex_session_start_is_wired(repo_root)
    checks = [
        ("task-start-strong-gate", repo_root / ".trellis" / "scripts" / "task.py", TASK_START_STRONG_GATE_PATCH_MARKER),
        (
            "task-create-preserve-active",
            repo_root / ".trellis" / "scripts" / "common" / "task_store.py",
            TASK_CREATE_PRESERVE_ACTIVE_PATCH_MARKER,
        ),
        (
            "task-status-view-strong-gate",
            repo_root / ".trellis" / "scripts" / "common" / "tasks.py",
            TASK_STATUS_VIEW_PATCH_MARKER,
        ),
        (
            "task-status-view-strong-gate",
            repo_root / ".trellis" / "scripts" / "common" / "task_queue.py",
            TASK_STATUS_VIEW_PATCH_MARKER,
        ),
        (
            "workflow-phase-strong-gate",
            repo_root / ".trellis" / "scripts" / "common" / "workflow_phase.py",
            WORKFLOW_PHASE_STRONG_GATE_PATCH_MARKER,
        ),
    ]
    if "claude" in cli_types:
        checks.extend(
            [
                (
                    "inject-workflow-state",
                    repo_root / ".claude" / "hooks" / "inject-workflow-state.py",
                    INJECT_WORKFLOW_STATE_PATCH_MARKER,
                ),
                (
                    "claude-inject-subagent-context",
                    repo_root / ".claude" / "hooks" / "inject-subagent-context.py",
                    CLAUDE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER,
                ),
                (
                    "session-start-strong-gate",
                    repo_root / ".claude" / "hooks" / "session-start.py",
                    SESSION_START_STRONG_GATE_PATCH_MARKER,
                ),
            ]
        )
    if "codex" in cli_types:
        checks.append(
            (
                "inject-workflow-state",
                repo_root / ".codex" / "hooks" / "inject-workflow-state.py",
                INJECT_WORKFLOW_STATE_PATCH_MARKER,
            )
        )
        if codex_session_start_wired:
            checks.append(
                (
                    "session-start-strong-gate",
                    repo_root / ".codex" / "hooks" / "session-start.py",
                    SESSION_START_STRONG_GATE_PATCH_MARKER,
                )
            )
    if "opencode" in cli_types:
        checks.extend(
            [
                (
                    "inject-workflow-state",
                    repo_root / ".opencode" / "plugins" / "inject-workflow-state.js",
                    OPENCODE_INJECT_WORKFLOW_STATE_PATCH_MARKER,
                ),
                (
                    "session-start-strong-gate",
                    repo_root / ".opencode" / "lib" / "session-utils.js",
                    OPENCODE_SESSION_UTILS_PATCH_MARKER,
                ),
                (
                    "opencode-inject-subagent-context",
                    repo_root / ".opencode" / "plugins" / "inject-subagent-context.js",
                    OPENCODE_INJECT_SUBAGENT_CONTEXT_PATCH_MARKER,
                ),
            ]
        )
    return checks


def _python_compile_error(
    repo_root: Path,
    path: Path,
    patch_name: str,
    content: str,
) -> str | None:
    if path.suffix != ".py":
        return None
    try:
        compile(content, str(path), "exec")
    except SyntaxError as exc:
        detail = exc.msg
        if exc.lineno is not None:
            detail = f"{detail} @ line {exc.lineno}"
        return (
            f"{path.relative_to(repo_root)} 无法编译"
            f"（critical runtime patch: {patch_name}; {exc.__class__.__name__}: {detail}）"
        )
    return None


def _js_runtime_contract_errors(
    repo_root: Path,
    path: Path,
    patch_name: str,
    content: str,
) -> list[str]:
    if path.suffix != ".js":
        return []

    problems: list[str] = []
    if patch_name == "inject-workflow-state":
        if 'import { execFileSync } from "child_process"' not in content:
            problems.append(
                f"{path.relative_to(repo_root)} 缺少 execFileSync 导入"
                f"（critical runtime patch: {patch_name}）"
            )
        if 'const PYTHON_CMD = process.env.TRELLIS_PYTHON || "python3"' not in content:
            problems.append(
                f"{path.relative_to(repo_root)} 缺少 PYTHON_CMD 定义"
                f"（critical runtime patch: {patch_name}）"
            )
        if "function buildBreadcrumb(id, status, templates, source = null" in content and "task.extraLines" not in content:
            problems.append(
                f"{path.relative_to(repo_root)} 缺少 task.extraLines 透传"
                f"（critical runtime patch: {patch_name}）"
            )
    elif patch_name == "opencode-inject-subagent-context":
        required_fragments = (
            'const STRONG_GATE_BLOCKED_ERROR_NAME = "TrellisStrongGateBlockedError"',
            "function shouldAllowTaskInjection(routeData, subagentType)",
            "Embedded workflow keeps all Task-based subagent execution disabled.",
            "function loadRouteData(ctx, taskDir)",
            "function buildBlockedSubagentPrompt(routeData, subagentType, originalPrompt)",
            "function buildBlockedSubagentError(routeData, subagentType, originalPrompt)",
            "loadRouteData(ctx, ctx.resolveTaskDir(taskDir))",
            "Strong-gate blocked this subagent dispatch.",
            "strong-gate route does not allow subagent injection",
            "blockedError.name = STRONG_GATE_BLOCKED_ERROR_NAME",
            "throw blockedError",
            "error.name === STRONG_GATE_BLOCKED_ERROR_NAME",
            "throw error",
        )
        for fragment in required_fragments:
            if fragment in content:
                continue
            problems.append(
                f"{path.relative_to(repo_root)} 缺少补丁语义片段 `{fragment}`"
                f"（critical runtime patch: {patch_name}）"
            )
    return problems


def _task_runtime_contract_errors(
    repo_root: Path,
    path: Path,
    patch_name: str,
    content: str,
) -> list[str]:
    problems: list[str] = []
    if patch_name == "claude-inject-subagent-context":
        required_fragments = (
            "def _emit_blocked_subagent_output(",
            "Strong-gate blocked this subagent dispatch.",
            "current embedded workflow disables agent/subagent execution paths",
            "_emit_blocked_subagent_output(subagent_type, original_prompt, tool_input)",
            '"permissionDecision": "deny"',
            '"permission": "deny"',
        )
        for fragment in required_fragments:
            if fragment in content:
                continue
            problems.append(
                f"{path.relative_to(repo_root)} 缺少补丁语义片段 `{fragment}`"
                f"（critical runtime patch: {patch_name}）"
            )
    return problems


def _python_runtime_contract_errors(
    repo_root: Path,
    path: Path,
    patch_name: str,
    content: str,
) -> list[str]:
    if path.suffix != ".py":
        return []

    path_text = path.as_posix()
    fragment_requirements: tuple[str, ...] = ()
    if patch_name == "task-start-strong-gate":
        fragment_requirements = (
            "stage changes still go through workflow-state.py",
            "workflow-state.py route is authoritative",
        )
    elif patch_name == "task-create-preserve-active":
        fragment_requirements = (
            "TRELLIS_PRESERVE_ACTIVE_TASK",
            "Preserving current active task while creating child task",
        )
    elif patch_name == "task-status-view-strong-gate":
        if path_text.endswith("/common/tasks.py"):
            fragment_requirements = (
                "_workflow_state_summary",
                "_display_status",
                "workflow-state.json missing",
            )
        elif path_text.endswith("/common/task_queue.py"):
            fragment_requirements = (
                "list_tasks_by_status(None, repo_root)",
            )
    elif patch_name == "workflow-phase-strong-gate":
        fragment_requirements = (
            "_STRONG_GATE_STAGES",
        )

    problems: list[str] = []
    for fragment in fragment_requirements:
        if fragment in content:
            continue
        problems.append(
            f"{path.relative_to(repo_root)} 缺少补丁语义片段 `{fragment}`"
            f"（critical runtime patch: {patch_name}）"
        )
    return problems


def _detect_missing_critical_runtime_patches(repo_root: Path, record: dict[str, Any]) -> list[str]:
    expected = _expected_critical_runtime_patches(repo_root, record)
    if not expected:
        return []
    cli_types = _install_record_cli_types(record)
    missing: list[str] = []
    for patch_name, path, marker in _critical_patch_paths(repo_root, cli_types):
        if patch_name not in expected:
            continue
        if not path.is_file():
            missing.append(f"{path.relative_to(repo_root)} 缺失（critical runtime patch: {patch_name}）")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            missing.append(f"{path.relative_to(repo_root)} 不可读（critical runtime patch: {patch_name}）")
            continue
        compile_error = _python_compile_error(repo_root, path, patch_name, content)
        if compile_error is not None:
            missing.append(compile_error)
            continue
        marker_present = marker in content
        runtime_errors: list[str] = []
        runtime_errors.extend(_python_runtime_contract_errors(repo_root, path, patch_name, content))
        runtime_errors.extend(_js_runtime_contract_errors(repo_root, path, patch_name, content))
        runtime_errors.extend(_task_runtime_contract_errors(repo_root, path, patch_name, content))
        if runtime_errors:
            missing.extend(runtime_errors)
            continue
        if not marker_present:
            missing.append(
                f"{path.relative_to(repo_root)} 缺少补丁标记且无法确认已按当前合同保留 embed patch provenance"
                f"（critical runtime patch: {patch_name}）"
            )
    return missing


def _detect_missing_patched_codex_skills(repo_root: Path, record: dict[str, Any]) -> list[str]:
    if "codex" not in _install_record_cli_types(record):
        return []

    configured = record.get("patched_codex_skills")
    if not isinstance(configured, list):
        configured = []

    problems: list[str] = []
    shared_skills_dir = repo_root / ".agents" / "skills"
    skills_to_check: list[str] = [skill_name for skill_name in configured if isinstance(skill_name, str)]
    for optional_name in PATCHED_CODEX_SKILL_REQUIREMENTS:
        if optional_name in skills_to_check:
            continue
        if (shared_skills_dir / optional_name / "SKILL.md").is_file():
            skills_to_check.append(optional_name)

    for skill_name in skills_to_check:
        if not isinstance(skill_name, str):
            continue
        target = shared_skills_dir / skill_name / "SKILL.md"
        if not target.is_file():
            problems.append(f"{target.relative_to(repo_root)} 缺失（patched codex skill: {skill_name}）")
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"{target.relative_to(repo_root)} 不可读（patched codex skill: {skill_name}）")
            continue
        requirements = PATCHED_CODEX_SKILL_REQUIREMENTS.get(skill_name)
        if requirements is None:
            continue
        missing_fragments = [
            fragment
            for fragment in requirements.get("must_contain", ())
            if fragment not in content
        ]
        stale_fragments = [
            fragment
            for fragment in requirements.get("must_not_contain", ())
            if fragment in content
        ]
        if missing_fragments or stale_fragments:
            reasons: list[str] = []
            if missing_fragments:
                reasons.append("缺少补丁语义片段: " + " / ".join(missing_fragments))
            if stale_fragments:
                reasons.append("仍残留旧语义片段: " + " / ".join(stale_fragments))
            problems.append(
                f"{target.relative_to(repo_root)} 语义漂移（patched codex skill: {skill_name}）: "
                + "；".join(reasons)
            )
    return problems


def _managed_distributed_command_names(record: dict[str, Any]) -> list[str]:
    commands = record.get("commands")
    if isinstance(commands, list):
        names = [str(item) for item in commands if isinstance(item, str)]
        return [name for name in names if name in DISTRIBUTED_COMMAND_NAMES]
    return []


def _distributed_command_path_variants(
    repo_root: Path,
    cli_types: set[str],
    command_name: str,
) -> list[Path]:
    paths: list[Path] = []
    if "claude" in cli_types:
        paths.append(repo_root / ".claude" / "commands" / "trellis" / f"{command_name}.md")
    if "opencode" in cli_types:
        paths.append(repo_root / ".opencode" / "commands" / "trellis" / f"{command_name}.md")
    if "codex" in cli_types:
        paths.append(repo_root / ".agents" / "skills" / command_name / "SKILL.md")
    return paths


def _normalized_hash(content: str) -> str:
    normalized = content.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _detect_distributed_command_drift(repo_root: Path, record: dict[str, Any]) -> list[str]:
    cli_types = _install_record_cli_types(record)
    problems: list[str] = []
    for command_name in _managed_distributed_command_names(record):
        variants: list[tuple[Path, str]] = []
        missing_paths: list[Path] = []
        for path in _distributed_command_path_variants(repo_root, cli_types, command_name):
            if not path.is_file():
                missing_paths.append(path)
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                problems.append(f"{path.relative_to(repo_root)} 不可读（distributed command: {command_name}）")
                continue
            variants.append((path, _normalized_hash(content)))

        if missing_paths:
            missing_desc = ", ".join(path.relative_to(repo_root).as_posix() for path in missing_paths)
            problems.append(f"{command_name} 缺少受管副本: {missing_desc}")
            continue

        if len(variants) < 2:
            continue

        hashes = {digest for _path, digest in variants}
        if len(hashes) > 1:
            variant_desc = ", ".join(path.relative_to(repo_root).as_posix() for path, _digest in variants)
            problems.append(f"{command_name} 内容漂移: {variant_desc}")

    return problems


def _workflow_doc_contract_advisories(repo_root: Path) -> list[str]:
    workflow_md = repo_root / ".trellis" / "workflow.md"
    if not workflow_md.is_file():
        return []
    content = workflow_md.read_text(encoding="utf-8")
    issues: list[str] = []
    if "workflow-state.py init <leaf-dir> --stage plan" in content:
        issues.append(".trellis/workflow.md 仍使用 `init <leaf-dir> --stage plan` 作为 leaf 执行态补建指引")
    if "workflow-state.py init <leaf-dir> --stage project-audit" in content:
        issues.append(".trellis/workflow.md 仍使用 `init <leaf-dir> --stage project-audit` 作为任务级 owner handoff 指引")
    return issues


def _distributed_command_contract_advisories(repo_root: Path, record: dict[str, Any]) -> list[str]:
    cli_types = _install_record_cli_types(record)
    problems: list[str] = []
    delivery_paths = _distributed_command_path_variants(repo_root, cli_types, "delivery")
    for path in delivery_paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if "| 全部通过，且当前活动任务也准备关闭 | `/finish-work` |" in content:
            problems.append(f"{path.relative_to(repo_root)} 默认 finish-work 入口仍写成 `/finish-work`")
    plan_paths = _distributed_command_path_variants(repo_root, cli_types, "plan")
    for path in plan_paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        if "workflow-state.py init <leaf-task-dir> --stage plan" in content:
            problems.append(f"{path.relative_to(repo_root)} 仍要求 `init --stage plan` 作为 leaf 执行态补建")
    return problems


def _shared_script_contract_advisories(repo_root: Path) -> list[str]:
    plan_validate = repo_root / ".trellis" / "scripts" / "workflow" / "plan-validate.py"
    if not plan_validate.is_file():
        return []
    content = plan_validate.read_text(encoding="utf-8")
    if "缺少唯一的 project-audit task 行" in content:
        return []
    return [".trellis/scripts/workflow/plan-validate.py 未提前拦截“声明了 PROJECT-AUDIT 但缺少结构化 project-audit task 行”"]


def _extract_toml_table_body(content: str, heading: str) -> str | None:
    marker = f"{heading}\n"
    start = content.find(marker)
    if start == -1:
        return None
    body_start = start + len(marker)
    next_table = content.find("\n[", body_start)
    if next_table == -1:
        return content[body_start:]
    return content[body_start:next_table]


def _codex_config_advisories(repo_root: Path) -> list[str]:
    config_path = repo_root / ".codex" / "config.toml"
    if not config_path.is_file():
        return []
    content = config_path.read_text(encoding="utf-8")
    body = _extract_toml_table_body(content, "[features.multi_agent_v2]")
    if body is None:
        return []
    effective_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if any(line == "enabled = true" for line in effective_lines):
        return [".codex/config.toml 仍启用 multi_agent_v2，未落 main-session-only 配置补丁"]
    return []


def collect_embed_advisories(repo_root: Path) -> list[str]:
    """Collect non-fatal embed drift warnings.

    These items do not block `workflow-state.py route`, but they should be
    surfaced so maintainers can repair drift before it turns into a real
    compatibility failure.
    """

    install_record = repo_root / INSTALL_RECORD
    if not install_record.is_file():
        return []

    record = _load_install_record_data(install_record)
    advisories: list[str] = []

    missing_codex_skills = _detect_missing_patched_codex_skills(repo_root, record)
    if missing_codex_skills:
        advisories.append("patched codex skill 漂移: " + "; ".join(missing_codex_skills))

    distributed_drift = _detect_distributed_command_drift(repo_root, record)
    if distributed_drift:
        advisories.append("distributed command 内容漂移: " + "; ".join(distributed_drift))

    workflow_contract = _workflow_doc_contract_advisories(repo_root)
    if workflow_contract:
        advisories.append("workflow contract 漂移: " + "; ".join(workflow_contract))

    distributed_contract = _distributed_command_contract_advisories(repo_root, record)
    if distributed_contract:
        advisories.append("distributed command 合同漂移: " + "; ".join(distributed_contract))

    script_contract = _shared_script_contract_advisories(repo_root)
    if script_contract:
        advisories.append("shared script 合同漂移: " + "; ".join(script_contract))

    if "codex" in _install_record_cli_types(record):
        codex_config = _codex_config_advisories(repo_root)
        if codex_config:
            advisories.append("codex config 漂移: " + "; ".join(codex_config))

    return advisories


def detect_embed_invalid(repo_root: Path) -> str | None:
    install_record = repo_root / INSTALL_RECORD
    if not install_record.is_file():
        return None
    record = _load_install_record_data(install_record)

    library_lock = repo_root / LIBRARY_LOCK
    if not library_lock.is_file():
        return f"检测到 {INSTALL_RECORD}，但缺少 {LIBRARY_LOCK}"

    try:
        lock_text = library_lock.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"{LIBRARY_LOCK} 不可读，无法确认最低资产集"

    if REQUIREMENTS_FOUNDATION_PACK not in lock_text:
        return f"{LIBRARY_LOCK} 缺少最低资产集 {REQUIREMENTS_FOUNDATION_PACK}"

    missing_patches = _detect_missing_critical_runtime_patches(repo_root, record)
    if missing_patches:
        return "critical runtime patch 未完整落地: " + "; ".join(missing_patches)

    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Embedded workflow integrity helper")
    parser.add_argument("project_root", nargs="?", default=".", help="Target project root")
    parser.add_argument(
        "--force-ignore-embed-check",
        action="store_true",
        help="Bypass non-fatal embed drift checks and emit advisories instead",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.project_root).resolve()
    invalid = detect_embed_invalid(repo_root)
    advisories = collect_embed_advisories(repo_root)
    if invalid is not None and not args.force_ignore_embed_check:
        print(invalid)
        return 1
    if invalid is not None and args.force_ignore_embed_check:
        print(f"⚠️  {invalid}")
    for advisory in advisories:
        print(f"⚠️  {advisory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
