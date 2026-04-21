#!/usr/bin/env python3
"""Analyze drift and repair low-risk workflow upgrades after Trellis updates.

用法:
  python3 upgrade-compat.py --check              # 检测冲突（默认）
  python3 upgrade-compat.py --merge              # 低风险重部署/补丁恢复
  python3 upgrade-compat.py --force              # 依赖原始备份的强制恢复
  python3 upgrade-compat.py --project-root /path # 指定项目根目录
  python3 upgrade-compat.py --cli claude,opencode,codex  # 指定 CLI 类型

重要边界：
- 目标项目应已先执行 `trellis init`
- 目标项目必须已完成当前最新 Trellis 官方升级；否则连只读分析和本脚本都不允许执行
- 建议先完成三态分析（A 纯净基线 / B 最新 workflow 期望状态 / C 目标项目真实状态）
- 当前 workflow 会重新部署合并型 + 纯新增型阶段命令资产
- `start.md` / `finish-work.md` / `record-session.md` 属于 Trellis 基线命令，升级脚本负责恢复并重新注入 workflow 补丁
- 若 Trellis 或 workflow 自身发生结构性 breaking change，本脚本不替代人工迁移判断
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from workflow_assets import (
    ADDED_COMMANDS,
    AGENT_SUFFIXES,
    ALL_CLI_TYPES,
    CODEX_PATCH_BASELINE_SKILLS,
    CODEX_SHARED_SKILL_NAMES,
    CLI_ALT_DIRS,
    CLI_DIRS,
    codex_secondary_skills_dir,
    codex_shared_skills_dir,
    DISTRIBUTED_COMMANDS,
    detect_cli_types as detect_cli_types_shared,
    HELPER_SCRIPTS,
    list_all_codex_skills_dirs,
    MANAGED_IMPLEMENTATION_AGENTS,
    OPTIONAL_DISABLED_BASELINE_COMMANDS,
    OVERLAY_BASELINE_COMMANDS,
    PATCH_BASELINE_COMMANDS,
    PATCH_BASELINE_SHARED_DOCS,
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_VERSION,
    check_latest_trellis_prerequisite,
    prepare_command_content,
    render_workflow_managed_agent,
    read_project_trellis_version,
    resolve_codex_skills_dir,
    workflow_managed_agent_target_path,
)


def _load_install_workflow_module():
    module_path = Path(__file__).resolve().with_name("install-workflow.py")
    spec = importlib.util.spec_from_file_location("workflow_install_workflow", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 install-workflow.py: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_INSTALL_WORKFLOW = _load_install_workflow_module()
_AGENTS_NL_ROUTING_END = _INSTALL_WORKFLOW._AGENTS_NL_ROUTING_END
_AGENTS_NL_ROUTING_MARKER = _INSTALL_WORKFLOW._AGENTS_NL_ROUTING_MARKER
_NL_ROUTING_SECTION = _INSTALL_WORKFLOW._NL_ROUTING_SECTION
_EMBED_ATTEMPT_FILE_NAME = _INSTALL_WORKFLOW._EMBED_ATTEMPT_FILE_NAME
deploy_agents_md_routing = _INSTALL_WORKFLOW.deploy_agents_md_routing


G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"


def ok(message: str) -> None:
    print(f"{G}✅ {message}{N}")


def warn(message: str) -> None:
    print(f"{Y}⚠️  {message}{N}")


def err(message: str) -> None:
    print(f"{R}❌ {message}{N}")


def info(message: str) -> None:
    print(f"{C}ℹ️  {message}{N}")


# ── 常量 ──
_PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
_INJECTION_MARKER = "## Operation Types"
_FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
_CODEX_START_SKILL_MARKER = "## Workflow Phase Router Patch `[AI]`"
_FINISH_WORK_START_HEADING = "### 1. Code Quality"
_FINISH_WORK_END_HEADING = "### 1.5. Test Coverage"
_RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
_RECORD_SESSION_INJECTION_MARKER = "### Step 2: One-Click Add Session"
_PARALLEL_DISABLED_MARKER = "<!-- workflow-parallel-disabled -->"
_WORKFLOW_PATCH_MARKER = "<!-- workflow-projectization-patch -->"
_WORKFLOW_START_HEADING = "## Development Process"
_WORKFLOW_END_HEADING = "## File Descriptions"
_IGNORE_EMBED_ATTEMPT_ENV = "WORKFLOW_IGNORE_EMBED_ATTEMPT"
# 当前 workflow 分发的阶段命令。
# `brainstorm` / `check` 与 Trellis 基线同名，但当前 workflow 采用合并后的阶段语义；
# `start` / `finish-work` / `record-session` 仍来自 Trellis 基线，并由当前 workflow 注入补丁。
_CLI_DIRS = CLI_DIRS
_CLI_ALT_DIRS = CLI_ALT_DIRS
_ALL_CLI_TYPES = ALL_CLI_TYPES
_REQUIRED_INSTALL_RECORD_KEYS = {
    "trellis_version",
    "cli_types",
    "commands",
    "overlay_commands",
    "added_commands",
    "disabled_commands",
    "patched_baseline_commands",
    "patched_shared_docs",
    "scripts",
    "initial_pack",
    "bootstrap_task_removed",
}
_LEGACY_OPTIONAL_VERSION_KEYS = {
    "workflow_version",
    "workflow_schema_version",
    "patched_codex_skills",
    "bootstrap_cleanup_status",
}


def find_root() -> Path:
    """向上查找包含任一 CLI 目录的项目根目录。"""
    all_dirs = list(_CLI_DIRS.values()) + list(_CLI_ALT_DIRS.values())
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        for d in all_dirs:
            if (cur / d).is_dir():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    dirs_str = "、".join(f"{d}/" for d in all_dirs)
    sys.exit(f"{R}未找到任何 CLI 目录（{dirs_str}）{N}")


def detect_cli_types(root: Path, requested: list[str] | None = None) -> list[str]:
    """检测项目中存在的 CLI 类型。"""
    found = detect_cli_types_shared(root)
    if requested:
        found = [cli_type for cli_type in found if cli_type in requested]
    return found


def has_phase_router(start_md: Path) -> bool:
    if not start_md.exists():
        return False
    return _PHASE_ROUTER_MARKER in start_md.read_text(encoding="utf-8")


def has_record_session_patch(record_session_md: Path) -> bool:
    if not record_session_md.exists():
        return False
    return _RECORD_SESSION_MARKER in record_session_md.read_text(encoding="utf-8")


def has_finish_work_patch(finish_work_path: Path) -> bool:
    if not finish_work_path.exists():
        return False
    return _FINISH_WORK_MARKER in finish_work_path.read_text(encoding="utf-8")


def has_codex_start_skill_patch(start_skill_path: Path) -> bool:
    if not start_skill_path.exists():
        return False
    return _CODEX_START_SKILL_MARKER in start_skill_path.read_text(encoding="utf-8")


def has_workflow_patch(workflow_md: Path) -> bool:
    if not workflow_md.exists():
        return False
    return _WORKFLOW_PATCH_MARKER in workflow_md.read_text(encoding="utf-8")


def has_agents_md_routing(agents_md: Path) -> bool:
    if not agents_md.exists():
        return False
    content = agents_md.read_text(encoding="utf-8")
    return _AGENTS_NL_ROUTING_MARKER in content and _AGENTS_NL_ROUTING_END in content


def agents_md_routing_matches_source(agents_md: Path) -> bool:
    if not agents_md.exists():
        return False
    content = agents_md.read_text(encoding="utf-8")
    if _AGENTS_NL_ROUTING_MARKER not in content or _AGENTS_NL_ROUTING_END not in content:
        return False
    start_idx = content.index(_AGENTS_NL_ROUTING_MARKER)
    end_idx = content.index(_AGENTS_NL_ROUTING_END) + len(_AGENTS_NL_ROUTING_END)
    actual_section = content[start_idx:end_idx].strip()
    expected_section = _NL_ROUTING_SECTION.rstrip().strip()
    return actual_section == expected_section


def workflow_patch_matches_source(src: Path, workflow_md: Path) -> bool:
    if not workflow_md.exists():
        return False
    patch = src / "workflow-patch-projectization.md"
    if not patch.exists():
        return False
    content = workflow_md.read_text(encoding="utf-8")
    return _WORKFLOW_PATCH_MARKER in content and patch.read_text(encoding="utf-8") in content


def build_finish_work_content(content: str, patch_text: str) -> str | None:
    if _FINISH_WORK_MARKER in content:
        return content

    start_idx = content.find(_FINISH_WORK_START_HEADING)
    end_idx = content.find(_FINISH_WORK_END_HEADING)
    if start_idx == -1:
        return None
    if end_idx == -1 or end_idx <= start_idx:
        next_heading_idx = content.find("\n### ", start_idx + len(_FINISH_WORK_START_HEADING))
        if next_heading_idx == -1:
            return None
        end_idx = next_heading_idx + 1

    prefix = content[:start_idx]
    suffix = content[end_idx:].lstrip("\n")
    return prefix + patch_text.rstrip() + "\n\n" + suffix


def build_workflow_content(content: str, patch_text: str) -> str | None:
    if _WORKFLOW_PATCH_MARKER in content:
        return content

    start_idx = content.find(_WORKFLOW_START_HEADING)
    end_idx = content.find(_WORKFLOW_END_HEADING)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return None

    prefix = content[:start_idx]
    suffix = content[end_idx:].lstrip("\n")
    return prefix + patch_text.rstrip() + "\n\n" + suffix


def load_install_record(rec_file: Path) -> dict:
    if not rec_file.exists():
        return {}
    try:
        return json.loads(rec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        warn(f"workflow-installed.json 损坏: {exc}")
        return {}


def detect_install_record_schema_conflicts(record: dict) -> int:
    if not record:
        warn("workflow-installed.json 缺失或不可读，跳过 schema 完整性校验")
        return 0

    missing_required = sorted(key for key in _REQUIRED_INSTALL_RECORD_KEYS if key not in record)
    missing_legacy_versions = sorted(key for key in _LEGACY_OPTIONAL_VERSION_KEYS if key not in record)

    if missing_required:
        err(f"workflow-installed.json 缺少字段: {', '.join(missing_required)}")
        return len(missing_required)

    if missing_legacy_versions:
        warn(
            "workflow-installed.json 缺少 legacy 可接受版本字段: "
            + ", ".join(missing_legacy_versions)
            + "；按 legacy/unknown 继续"
        )
        return 0

    ok("workflow-installed.json schema 完整")
    return 0


def detect_install_record_state_warnings(record: dict, root: Path) -> int:
    if not record:
        return 0

    bootstrap_task_dir = root / ".trellis" / "tasks" / "00-bootstrap-guidelines"
    bootstrap_removed = bool(record.get("bootstrap_task_removed"))
    bootstrap_status = record.get("bootstrap_cleanup_status")

    if bootstrap_removed and bootstrap_task_dir.exists():
        warn("workflow-installed.json: bootstrap_task_removed=true，但 00-bootstrap-guidelines 仍存在；需人工核对")
    if bootstrap_status == "removed" and bootstrap_task_dir.exists():
        warn("workflow-installed.json: bootstrap_cleanup_status=removed，但 00-bootstrap-guidelines 仍存在；需人工核对")
    if bootstrap_status == "absent" and bootstrap_task_dir.exists():
        warn("workflow-installed.json: bootstrap_cleanup_status=absent，但 00-bootstrap-guidelines 仍存在；需人工核对")

    return 0


def detect_embed_attempt_conflict(root: Path) -> int:
    if os.environ.get(_IGNORE_EMBED_ATTEMPT_ENV) == "1":
        return 0
    attempt_path = root / ".trellis" / _EMBED_ATTEMPT_FILE_NAME
    if not attempt_path.exists():
        return 0
    details = {}
    try:
        details = json.loads(attempt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        details = {"status": "unknown", "error": "attempt record unreadable"}
    err(
        f"检测到残留的 {_EMBED_ATTEMPT_FILE_NAME}；目标项目存在未完成或失败的历史嵌入尝试，"
        "当前状态不能视为完整有效嵌入。"
    )
    if details.get("status"):
        warn(f"{_EMBED_ATTEMPT_FILE_NAME}: status={details['status']}")
    if details.get("last_step"):
        warn(f"{_EMBED_ATTEMPT_FILE_NAME}: last_step={details['last_step']}")
    if details.get("error"):
        warn(f"{_EMBED_ATTEMPT_FILE_NAME}: error={details['error']}")
    return 1


def read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        warn(f"无法按 UTF-8 读取文件，跳过内容比对: {path}")
        return None


def expected_command_content(src: Path, name: str) -> str | None:
    source_path = src / f"{name}.md"
    if not source_path.exists():
        err(f"源命令缺失，无法校验: {source_path.name}")
        return None
    return prepare_command_content(source_path)


def expected_helper_script_content(src: Path, name: str) -> str | None:
    source_path = src / "shell" / name
    if not source_path.exists():
        err(f"源辅助脚本缺失，无法校验: {source_path.name}")
        return None
    return read_text(source_path)


def expected_agent_content(src: Path, cli_type: str, name: str) -> str | None:
    try:
        return render_workflow_managed_agent(src, cli_type, name)
    except FileNotFoundError as exc:
        err(f"源 agent 缺失，无法校验: {exc.filename}")
        return None


def expected_parallel_disabled_content(src: Path) -> str | None:
    source_path = src / "parallel-disabled.md"
    if not source_path.exists():
        err("parallel-disabled.md 缺失，无法校验 parallel 禁用覆盖")
        return None
    return prepare_command_content(source_path)


def is_parallel_disabled(path: Path) -> bool:
    text = read_text(path)
    if text is None:
        return False
    return _PARALLEL_DISABLED_MARKER in text


# ── Claude Code 冲突检测 ──
def detect_conflicts_claude(src: Path, dst_cmds: Path) -> int:
    conflicts = 0
    start = dst_cmds / "start.md"
    finish_work = dst_cmds / "finish-work.md"
    record_session = dst_cmds / "record-session.md"
    parallel = dst_cmds / "parallel.md"

    if not has_phase_router(start):
        err("[Claude] start.md: Phase Router 丢失")
        conflicts += 1
    else:
        ok("[Claude] start.md: Phase Router 正常")

    command_conflicts = 0
    for name in DISTRIBUTED_COMMANDS:
        target_path = dst_cmds / f"{name}.md"
        if not target_path.exists():
            warn(f"[Claude] 命令缺失: /trellis:{name}")
            command_conflicts += 1
            continue
        expected = expected_command_content(src, name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            command_conflicts += 1
            continue
        if actual != expected:
            err(f"[Claude] 命令内容漂移: /trellis:{name}")
            command_conflicts += 1
    if command_conflicts:
        conflicts += command_conflicts
    else:
        ok("[Claude] 所有分发命令内容一致")

    if not finish_work.exists():
        err("[Claude] finish-work.md: 文件缺失")
        conflicts += 1
    elif not has_finish_work_patch(finish_work):
        err("[Claude] finish-work.md: 项目化补丁缺失")
        conflicts += 1
    else:
        ok("[Claude] finish-work.md: 项目化补丁正常")

    if not record_session.exists():
        err("[Claude] record-session.md: 文件缺失")
        conflicts += 1
    elif not has_record_session_patch(record_session):
        err("[Claude] record-session.md: 元数据闭环说明缺失")
        conflicts += 1
    else:
        ok("[Claude] record-session.md: 元数据闭环说明正常")

    parallel_backup = dst_cmds / ".backup-original" / "parallel.md"
    if parallel.exists():
        err("[Claude] parallel.md: 应已从嵌入面移除")
        conflicts += 1
    elif parallel_backup.exists():
        ok("[Claude] parallel.md: 已移除且备份正常")

    return conflicts


# ── OpenCode 冲突检测 ──
def detect_conflicts_opencode(src: Path, dst_cmds: Path) -> int:
    conflicts = 0
    start = dst_cmds / "start.md"
    finish_work = dst_cmds / "finish-work.md"
    record_session = dst_cmds / "record-session.md"
    parallel = dst_cmds / "parallel.md"

    if not has_phase_router(start):
        err("[OpenCode] start.md: Phase Router 丢失")
        conflicts += 1
    else:
        ok("[OpenCode] start.md: Phase Router 正常")

    command_conflicts = 0
    for name in DISTRIBUTED_COMMANDS:
        target_path = dst_cmds / f"{name}.md"
        if not target_path.exists():
            warn(f"[OpenCode] 命令缺失: {name}")
            command_conflicts += 1
            continue
        expected = expected_command_content(src, name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            command_conflicts += 1
            continue
        if actual != expected:
            err(f"[OpenCode] 命令内容漂移: {name}")
            command_conflicts += 1
    if command_conflicts:
        conflicts += command_conflicts
    else:
        ok("[OpenCode] 所有分发命令内容一致")

    if not finish_work.exists():
        err("[OpenCode] finish-work.md: 文件缺失")
        conflicts += 1
    elif not has_finish_work_patch(finish_work):
        err("[OpenCode] finish-work.md: 项目化补丁缺失")
        conflicts += 1
    else:
        ok("[OpenCode] finish-work.md: 项目化补丁正常")

    if not record_session.exists():
        err("[OpenCode] record-session.md: 文件缺失")
        conflicts += 1
    elif not has_record_session_patch(record_session):
        err("[OpenCode] record-session.md: 元数据闭环说明缺失")
        conflicts += 1
    else:
        ok("[OpenCode] record-session.md: 元数据闭环说明正常")

    parallel_backup = dst_cmds / ".backup-original" / "parallel.md"
    if parallel.exists():
        err("[OpenCode] parallel.md: 应已从嵌入面移除")
        conflicts += 1
    elif parallel_backup.exists():
        ok("[OpenCode] parallel.md: 已移除且备份正常")

    return conflicts


def detect_conflicts_workflow_doc(src: Path, root: Path) -> int:
    workflow_md = root / ".trellis" / "workflow.md"
    if not workflow_md.exists():
        err("[Shared] .trellis/workflow.md: 文件缺失")
        return 1
    if not has_workflow_patch(workflow_md):
        err("[Shared] .trellis/workflow.md: 项目化补丁缺失")
        return 1
    if not workflow_patch_matches_source(src, workflow_md):
        err("[Shared] .trellis/workflow.md: 项目化补丁内容漂移")
        return 1
    ok("[Shared] .trellis/workflow.md: 项目化补丁正常")
    return 0


def detect_conflicts_agents_md(root: Path) -> int:
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        warn("[Shared] AGENTS.md: 文件缺失，跳过 NL 路由表检查")
        return 0
    if not has_agents_md_routing(agents_md):
        err("[Shared] AGENTS.md: NL 路由表缺失")
        return 1
    if not agents_md_routing_matches_source(agents_md):
        err("[Shared] AGENTS.md: NL 路由表内容漂移")
        return 1
    ok("[Shared] AGENTS.md: NL 路由表正常")
    return 0


def detect_conflicts_managed_agents(src: Path, root: Path, cli_type: str, cli_label: str) -> int:
    target_dir = root / CLI_DIRS[cli_type] / "agents"
    if not target_dir.is_dir():
        warn(f"[{cli_label}] {target_dir.relative_to(root)}/ 不存在，跳过 managed agents 检查")
        return 0

    conflicts = 0
    for agent_name in MANAGED_IMPLEMENTATION_AGENTS:
        target_path = workflow_managed_agent_target_path(root, cli_type, agent_name)
        if not target_path.exists():
            err(f"[{cli_label}] agent 缺失: {target_path.relative_to(root)}")
            conflicts += 1
            continue
        expected = expected_agent_content(src, cli_type, agent_name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            conflicts += 1
            continue
        if actual != expected:
            err(f"[{cli_label}] agent 内容漂移: {agent_name}")
            conflicts += 1
        else:
            ok(f"[{cli_label}] agent 正常: {agent_name}")
    return conflicts


# ── Codex 冲突检测 ──
def detect_conflicts_codex(src: Path, root: Path) -> int:
    conflicts = 0
    skills_dirs = list_all_codex_skills_dirs(root)
    if not skills_dirs:
        warn("[Codex] 未找到 skills 目录")
        return 0
    shared_skills_dir = codex_shared_skills_dir(root)
    secondary_skills_dir = codex_secondary_skills_dir(root)
    primary_skills_dir = resolve_codex_skills_dir(root)
    if primary_skills_dir is None:
        warn("[Codex] 未找到活动 skills 目录")
        return 0

    # shared skills 只允许存在于 .agents/skills
    skill_conflicts = 0
    for name in DISTRIBUTED_COMMANDS:
        target_path = shared_skills_dir / name / "SKILL.md"
        if not target_path.exists():
            warn(f"[Codex] shared skill 缺失: {name} ({shared_skills_dir.relative_to(root)})")
            skill_conflicts += 1
            continue
        expected = expected_command_content(src, name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            skill_conflicts += 1
            continue
        if actual != expected:
            err(f"[Codex] shared skill 内容漂移: {name} ({shared_skills_dir.relative_to(root)})")
            skill_conflicts += 1
    if skill_conflicts:
        conflicts += skill_conflicts
    else:
        ok(f"[Codex] {shared_skills_dir.relative_to(root)} 分发 skills 内容一致")

    if secondary_skills_dir.is_dir():
        duplicate_conflicts = 0
        for name in CODEX_SHARED_SKILL_NAMES:
            duplicate_path = secondary_skills_dir / name / "SKILL.md"
            if duplicate_path.exists():
                err(f"[Codex] duplicate shared skill 应已移除: {duplicate_path.relative_to(root)}")
                duplicate_conflicts += 1
        if duplicate_conflicts:
            conflicts += duplicate_conflicts

    # baseline patch 型 skills 只检查活动 skills 目录
    finish_work_skill = primary_skills_dir / "finish-work" / "SKILL.md"
    if not finish_work_skill.exists():
        err(f"[Codex] finish-work skill ({primary_skills_dir.relative_to(root)}): 基线缺失")
        conflicts += 1
    elif has_finish_work_patch(finish_work_skill):
        ok(f"[Codex] finish-work skill ({primary_skills_dir.relative_to(root)}): 项目化补丁正常")
    else:
        err(f"[Codex] finish-work skill ({primary_skills_dir.relative_to(root)}): 项目化补丁缺失")
        conflicts += 1

    start_skill = primary_skills_dir / "start" / "SKILL.md"
    if not start_skill.exists():
        err(f"[Codex] start skill ({primary_skills_dir.relative_to(root)}): 基线缺失")
        conflicts += 1
    elif has_codex_start_skill_patch(start_skill):
        ok(f"[Codex] start skill ({primary_skills_dir.relative_to(root)}): Phase Router 补丁正常")
    else:
        err(f"[Codex] start skill ({primary_skills_dir.relative_to(root)}): Phase Router 补丁缺失")
        conflicts += 1

    # hooks 是全局的，只检查一次
    hooks_json = root / ".codex" / "hooks.json"
    if hooks_json.exists():
        ok("[Codex] hooks.json 存在")
    else:
        warn("[Codex] hooks.json 缺失")
        conflicts += 1

    session_start = root / ".codex" / "hooks" / "session-start.py"
    if session_start.exists():
        ok("[Codex] session-start.py 存在")
    else:
        warn("[Codex] session-start.py 缺失")
        conflicts += 1

    # 对每个 skills 目录分别检查 parallel：当前 Codex 合同是“移除嵌入面，但保留备份”
    parallel_conflicts = 0
    for skills_dir in skills_dirs:
        parallel_skill = skills_dir / "parallel" / "SKILL.md"
        parallel_backup = skills_dir / ".backup-original" / "parallel" / "SKILL.md"
        if parallel_skill.exists():
            err(f"[Codex] parallel skill ({skills_dir.relative_to(root)}): 应已从嵌入面移除")
            parallel_conflicts += 1
        elif parallel_backup.exists():
            ok(f"[Codex] parallel skill ({skills_dir.relative_to(root)}): 已移除且备份正常")
    if parallel_conflicts:
        conflicts += parallel_conflicts

    return conflicts


def detect_shared_script_conflicts(src: Path, dst_scripts: Path) -> int:
    conflicts = 0
    for name in HELPER_SCRIPTS:
        target_path = dst_scripts / name
        if not target_path.exists():
            warn(f"[Shared] 辅助脚本缺失: {name}")
            conflicts += 1
            continue
        expected = expected_helper_script_content(src, name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            conflicts += 1
            continue
        if actual != expected:
            err(f"[Shared] 辅助脚本内容漂移: {name}")
            conflicts += 1
    if conflicts == 0:
        ok("[Shared] 所有辅助脚本内容一致")
    return conflicts


# ── 备份 ──
def backup_deployed_state(dst_cmds: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = dst_cmds / f".backup-upgrade-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    start = dst_cmds / "start.md"
    if start.exists():
        shutil.copy2(start, backup_dir / "start.md")
    finish_work = dst_cmds / "finish-work.md"
    if finish_work.exists():
        shutil.copy2(finish_work, backup_dir / "finish-work.md")
    record_session = dst_cmds / "record-session.md"
    if record_session.exists():
        shutil.copy2(record_session, backup_dir / "record-session.md")
    parallel = dst_cmds / "parallel.md"
    if parallel.exists():
        shutil.copy2(parallel, backup_dir / "parallel.md")
    for name in DISTRIBUTED_COMMANDS:
        candidate = dst_cmds / f"{name}.md"
        if candidate.exists():
            shutil.copy2(candidate, backup_dir / f"{name}.md")
    ok(f"备份 → {backup_dir.name}")


def backup_shared_workflow_state(root: Path) -> None:
    workflow_md = root / ".trellis" / "workflow.md"
    if not workflow_md.exists():
        return
    trellis_dir = root / ".trellis"
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = trellis_dir / f".backup-upgrade-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workflow_md, backup_dir / "workflow.md")
    ok(f".trellis/workflow.md 备份 → {backup_dir.name}")


# ── 命令部署 ──
def deploy_commands(src: Path, dst_cmds: Path) -> None:
    for name in DISTRIBUTED_COMMANDS:
        source_path = src / f"{name}.md"
        target_path = dst_cmds / f"{name}.md"
        if source_path.exists():
            content = prepare_command_content(source_path)
            target_path.write_text(content, encoding="utf-8")
            ok(f"/trellis:{name}")


def deploy_parallel_disabled(src: Path, target_path: Path, label: str) -> bool:
    expected = expected_parallel_disabled_content(src)
    if expected is None or not target_path.exists():
        return False
    target_path.write_text(expected, encoding="utf-8")
    ok(f"{label} 已更新为禁用版本")
    return True


def deploy_scripts(src: Path, dst_scripts: Path) -> None:
    dst_scripts.mkdir(parents=True, exist_ok=True)
    for name in HELPER_SCRIPTS:
        source_path = src / "shell" / name
        if source_path.exists():
            shutil.copy2(source_path, dst_scripts / name)
            (dst_scripts / name).chmod(0o755)
    ok("辅助脚本已更新")


def deploy_managed_agents(src: Path, root: Path, cli_type: str, cli_label: str) -> None:
    target_dir = root / CLI_DIRS[cli_type] / "agents"
    if not target_dir.is_dir():
        warn(f"[{cli_label}] {target_dir.relative_to(root)}/ 不存在，跳过 managed agents 重部署")
        return

    for agent_name in MANAGED_IMPLEMENTATION_AGENTS:
        target_path = workflow_managed_agent_target_path(root, cli_type, agent_name)
        try:
            rendered = render_workflow_managed_agent(src, cli_type, agent_name)
        except FileNotFoundError as exc:
            err(f"[{cli_label}] 源 agent 缺失，无法重部署: {exc.filename}")
            continue
        target_path.write_text(rendered, encoding="utf-8")
        ok(f"[{cli_label}] agent 已重部署: {agent_name}")


def deploy_codex_skills(src: Path, root: Path) -> None:
    skills_dirs = list_all_codex_skills_dirs(root)
    if not skills_dirs:
        warn("[Codex] 未找到 skills 目录，跳过")
        return
    shared_skills_dir = codex_shared_skills_dir(root)
    secondary_skills_dir = codex_secondary_skills_dir(root)

    for name in DISTRIBUTED_COMMANDS:
        source_path = src / f"{name}.md"
        if source_path.exists():
            content = prepare_command_content(source_path)
            target_path = shared_skills_dir / name / "SKILL.md"
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            ok(f"[Codex] shared skill: {name} → {target_path.relative_to(root)}")

    for skills_dir in skills_dirs:
        parallel_skill = skills_dir / "parallel" / "SKILL.md"
        if parallel_skill.exists():
            shutil.rmtree(parallel_skill.parent)
            ok(f"[Codex] parallel skill 已从嵌入面移除 → {parallel_skill.relative_to(root)}")
    if secondary_skills_dir.is_dir():
        for name in CODEX_SHARED_SKILL_NAMES:
            duplicate_dir = secondary_skills_dir / name
            if duplicate_dir.exists():
                shutil.rmtree(duplicate_dir)
                ok(f"[Codex] duplicate shared skill 已移除 → {duplicate_dir.relative_to(root)}")


# ── 恢复 ──
def restore_command_from_original_backup(dst_cmds: Path, command_name: str) -> bool:
    backup_path = dst_cmds / ".backup-original" / f"{command_name}.md"
    target_path = dst_cmds / f"{command_name}.md"
    if not backup_path.exists():
        err(f"缺少 .backup-original/{command_name}.md，无法执行强制恢复")
        return False
    shutil.copy2(backup_path, target_path)
    ok(f"{command_name}.md 已从 .backup-original 恢复")
    return True


def restore_optional_command_from_original_backup(dst_cmds: Path, command_name: str) -> bool:
    backup_path = dst_cmds / ".backup-original" / f"{command_name}.md"
    target_path = dst_cmds / f"{command_name}.md"
    if not backup_path.exists():
        return False
    shutil.copy2(backup_path, target_path)
    ok(f"{command_name}.md 已从 .backup-original 恢复")
    return True


def restore_start_from_original_backup(dst_cmds: Path, start: Path) -> bool:
    backup_start = dst_cmds / ".backup-original" / "start.md"
    if not backup_start.exists():
        err("缺少 .backup-original/start.md，无法执行强制恢复")
        return False
    shutil.copy2(backup_start, start)
    ok("start.md 已从 .backup-original 恢复")
    return True


def restore_workflow_from_original_backup(root: Path) -> bool:
    backup_path = root / ".trellis" / ".backup-original" / "workflow.md"
    target_path = root / ".trellis" / "workflow.md"
    if not backup_path.exists():
        err("缺少 .trellis/.backup-original/workflow.md，无法执行强制恢复")
        return False
    shutil.copy2(backup_path, target_path)
    ok(".trellis/workflow.md 已从 .backup-original 恢复")
    return True


def restore_codex_finish_work(skills_dir: Path) -> bool:
    backup_path = skills_dir / ".backup-original" / "finish-work" / "SKILL.md"
    target_path = skills_dir / "finish-work" / "SKILL.md"
    if not backup_path.exists():
        err("缺少 .backup-original/finish-work/SKILL.md，无法执行强制恢复")
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)
    ok("[Codex] finish-work skill 已从 .backup-original 恢复")
    return True


def restore_codex_start_skill(skills_dir: Path) -> bool:
    backup_path = skills_dir / ".backup-original" / "start" / "SKILL.md"
    target_path = skills_dir / "start" / "SKILL.md"
    if not backup_path.exists():
        err("缺少 .backup-original/start/SKILL.md，无法执行强制恢复")
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)
    ok("[Codex] start skill 已从 .backup-original 恢复")
    return True


def restore_optional_codex_skill(skills_dir: Path, skill_name: str) -> bool:
    backup_path = skills_dir / ".backup-original" / skill_name / "SKILL.md"
    target_path = skills_dir / skill_name / "SKILL.md"
    if not backup_path.exists():
        return False
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target_path)
    ok(f"[Codex] {skill_name} skill 已从 .backup-original 恢复")
    return True


def inject_phase_router(src: Path, start: Path) -> bool:
    patch = src / "start-patch-phase-router.md"
    if not patch.exists():
        err("start-patch-phase-router.md 缺失，Phase Router 无法恢复，请手动检查源目录")
        return False
    if not start.exists():
        err("start.md 不存在，Phase Router 无法恢复")
        return False

    content = start.read_text(encoding="utf-8")
    if _INJECTION_MARKER not in content:
        warn("start.md 中未找到 '## Operation Types'，无法自动注入 Phase Router")
        return False

    before, after = content.split(_INJECTION_MARKER, 1)
    start.write_text(before + prepare_command_content(patch) + "\n" + _INJECTION_MARKER + after, encoding="utf-8")
    ok("Phase Router 已注入")
    return True


def build_codex_start_skill_content(content: str, patch_text: str) -> str:
    if _CODEX_START_SKILL_MARKER in content:
        return content
    return content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"


def inject_codex_start_skill_patch(src: Path, start_skill_path: Path, target_label: str) -> bool:
    patch = src / "start-skill-patch-phase-router.md"
    if not patch.exists():
        err("start-skill-patch-phase-router.md 缺失，无法恢复 Codex start Phase Router 补丁")
        return False
    if not start_skill_path.exists():
        err(f"{target_label} 不存在，无法恢复 Phase Router 补丁")
        return False

    content = start_skill_path.read_text(encoding="utf-8")
    if _CODEX_START_SKILL_MARKER in content:
        ok(f"{target_label} Phase Router 补丁已存在")
        return True

    start_skill_path.write_text(
        build_codex_start_skill_content(content, prepare_command_content(patch)),
        encoding="utf-8",
    )
    ok(f"{target_label} Phase Router 补丁已注入")
    return True


def inject_finish_work_patch(src: Path, finish_work_path: Path, target_label: str) -> bool:
    patch = src / "finish-work-patch-projectization.md"
    if not patch.exists():
        err("finish-work-patch-projectization.md 缺失，无法恢复 finish-work 项目化补丁")
        return False
    if not finish_work_path.exists():
        err(f"{target_label} 不存在，无法恢复项目化补丁")
        return False

    content = finish_work_path.read_text(encoding="utf-8")
    if _FINISH_WORK_MARKER in content:
        ok(f"{target_label} 项目化补丁已存在")
        return True

    new_content = build_finish_work_content(content, patch.read_text(encoding="utf-8"))
    if new_content is None:
        warn(f"{target_label} 中未找到可替换的 Code Quality 区块，无法自动恢复项目化补丁")
        return False

    finish_work_path.write_text(new_content, encoding="utf-8")
    ok(f"{target_label} 项目化补丁已注入")
    return True


def inject_record_session_patch(src: Path, record_session_md: Path) -> bool:
    patch = src / "record-session-patch-metadata-closure.md"
    if not patch.exists():
        err("record-session-patch-metadata-closure.md 缺失，无法恢复 record-session 注入")
        return False
    if not record_session_md.exists():
        err("record-session.md 不存在，无法恢复元数据闭环说明")
        return False

    content = record_session_md.read_text(encoding="utf-8")
    if _RECORD_SESSION_MARKER in content:
        ok("record-session 元数据闭环说明已存在")
        return True
    if _RECORD_SESSION_INJECTION_MARKER not in content:
        warn("record-session.md 中未找到 Step 2 注入点，无法自动注入元数据闭环说明")
        return False

    before, after = content.split(_RECORD_SESSION_INJECTION_MARKER, 1)
    record_session_md.write_text(
        before + patch.read_text(encoding="utf-8") + "\n" + _RECORD_SESSION_INJECTION_MARKER + after,
        encoding="utf-8",
    )
    ok("record-session 元数据闭环说明已注入")
    return True


def inject_workflow_patch(src: Path, root: Path) -> bool:
    patch = src / "workflow-patch-projectization.md"
    workflow_md = root / ".trellis" / "workflow.md"
    if not patch.exists():
        err("workflow-patch-projectization.md 缺失，无法恢复 .trellis/workflow.md 项目化补丁")
        return False
    if not workflow_md.exists():
        err(".trellis/workflow.md 不存在，无法恢复项目化补丁")
        return False

    patch_text = patch.read_text(encoding="utf-8")
    content = workflow_md.read_text(encoding="utf-8")
    if _WORKFLOW_PATCH_MARKER in content and patch_text in content:
        ok("workflow.md 项目化补丁已存在")
        return True

    baseline_content = content
    if _WORKFLOW_PATCH_MARKER in content and patch_text not in content:
        backup_path = root / ".trellis" / ".backup-original" / "workflow.md"
        if backup_path.exists():
            baseline_content = backup_path.read_text(encoding="utf-8")
        else:
            warn("workflow.md 已存在旧补丁，但缺少 .backup-original/workflow.md，无法自动刷新")
            return False

    new_content = build_workflow_content(baseline_content, patch_text)
    if new_content is None:
        warn("workflow.md 中未找到 Development Process / File Descriptions 注入边界，无法自动恢复项目化补丁")
        return False

    workflow_md.write_text(new_content, encoding="utf-8")
    ok("workflow.md 项目化补丁已注入")
    return True


def write_install_record(
    rec_file: Path,
    current_version: str,
    previous_version: str,
    cli_types: list[str],
    prior_record: dict,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    installed = prior_record.get("installed", now)
    initial_pack = prior_record.get("initial_pack", "pack.requirements-discovery-foundation")
    bootstrap_task_removed = prior_record.get("bootstrap_task_removed", True)
    bootstrap_cleanup_status = prior_record.get("bootstrap_cleanup_status", "unknown")
    rec_file.write_text(
        json.dumps(
            {
                "trellis_version": current_version,
                "installed": installed,
                "previous_version": previous_version,
                "cli_types": cli_types,
                "updated": now,
                "commands": DISTRIBUTED_COMMANDS,
                "overlay_commands": OVERLAY_BASELINE_COMMANDS,
                "added_commands": ADDED_COMMANDS,
                "disabled_commands": OPTIONAL_DISABLED_BASELINE_COMMANDS,
                "patched_baseline_commands": PATCH_BASELINE_COMMANDS,
                "patched_codex_skills": CODEX_PATCH_BASELINE_SKILLS,
                "patched_shared_docs": PATCH_BASELINE_SHARED_DOCS,
                "scripts": HELPER_SCRIPTS,
                "workflow_version": WORKFLOW_VERSION,
                "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
                "initial_pack": initial_pack,
                "bootstrap_task_removed": bootstrap_task_removed,
                "bootstrap_cleanup_status": bootstrap_cleanup_status,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    ok(f"版本标记已更新: {current_version}")


def cleanup_old_backups(dst_cmds: Path) -> None:
    old_backups = sorted(
        [d for d in dst_cmds.iterdir() if d.is_dir() and d.name.startswith(".backup-upgrade-")],
        key=lambda d: d.name,
    )
    if len(old_backups) > 2:
        for directory in old_backups[:-2]:
            shutil.rmtree(directory)
            warn(f"清理旧备份: {directory.name}")


def cleanup_old_workflow_backups(root: Path) -> None:
    trellis_dir = root / ".trellis"
    if not trellis_dir.is_dir():
        return
    old_backups = sorted(
        [d for d in trellis_dir.iterdir() if d.is_dir() and d.name.startswith(".backup-upgrade-")],
        key=lambda d: d.name,
    )
    if len(old_backups) > 2:
        for directory in old_backups[:-2]:
            shutil.rmtree(directory)
            warn(f"清理旧 .trellis 备份: {directory.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_const", const="check", dest="mode", default="check")
    parser.add_argument("--merge", action="store_const", const="merge", dest="mode")
    parser.add_argument("--force", action="store_const", const="force", dest="mode")
    parser.add_argument("--project-root", type=Path, default=None, help="项目根目录（默认自动检测）")
    parser.add_argument("--cli", type=str, default=None,
                        help="指定 CLI 类型，逗号分隔: claude,opencode,codex（默认全部自动检测）")
    args = parser.parse_args()

    src = Path(__file__).resolve().parent
    if args.project_root:
        root = args.project_root.resolve()
        all_dirs = list(_CLI_DIRS.values()) + list(_CLI_ALT_DIRS.values())
        if not any((root / d).is_dir() for d in all_dirs):
            dirs_str = "、".join(f"{d}/" for d in all_dirs)
            sys.exit(f"{R}指定的项目根目录不含任何 CLI 目录（{dirs_str}）{N}")
    else:
        root = find_root()

    # 检测 CLI 类型
    requested = [x.strip() for x in args.cli.split(",")] if args.cli else None
    cli_types = detect_cli_types(root, requested)

    rec_file = root / ".trellis" / "workflow-installed.json"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"

    prerequisite_ok, prerequisite_message = check_latest_trellis_prerequisite(root)
    if not prerequisite_ok:
        err(prerequisite_message)
        return 1

    current_version = read_project_trellis_version(root) or "unknown"
    record = load_install_record(rec_file)
    installed_version = record.get("trellis_version", "unknown")
    version_changed = current_version != installed_version

    print()
    print("╔══════════════════════════════════════════╗")
    print("║   Trellis 工作流低风险修复（多CLI）        ║")
    print("╚══════════════════════════════════════════╝")
    print()

    info(f"当前版本: {current_version}  |  安装时版本: {installed_version}")
    info(f"目标 CLI: {', '.join(cli_types)}")
    if version_changed:
        warn(f"版本变化: {installed_version} → {current_version}")
    else:
        info("版本一致，继续检查部署完整性")
    if args.mode in ("merge", "force"):
        warn("建议先完成 A/B/C 三态分析；当前命令主要用于低风险漂移修复，不替代结构性升级迁移。")
    print()

    # 冲突检测
    total_conflicts = 0
    total_conflicts += detect_embed_attempt_conflict(root)
    total_conflicts += detect_install_record_schema_conflicts(record)
    detect_install_record_state_warnings(record, root)
    for cli_type in cli_types:
        if cli_type == "claude":
            dst_cmds = root / ".claude" / "commands" / "trellis"
            total_conflicts += detect_conflicts_claude(src, dst_cmds)
            total_conflicts += detect_conflicts_managed_agents(src, root, "claude", "Claude")
        elif cli_type == "opencode":
            dst_cmds = root / ".opencode" / "commands" / "trellis"
            total_conflicts += detect_conflicts_opencode(src, dst_cmds)
            total_conflicts += detect_conflicts_managed_agents(src, root, "opencode", "OpenCode")
        elif cli_type == "codex":
            total_conflicts += detect_conflicts_codex(src, root)
            total_conflicts += detect_conflicts_managed_agents(src, root, "codex", "Codex")
    total_conflicts += detect_shared_script_conflicts(src, dst_scripts)
    total_conflicts += detect_conflicts_workflow_doc(src, root)
    total_conflicts += detect_conflicts_agents_md(root)
    print(f"   总冲突: {total_conflicts}")
    print()

    if args.mode == "check":
        if total_conflicts:
            err(f"发现 {total_conflicts} 个冲突，运行 --merge 修复")
            return 1
        if version_changed:
            warn("检测通过，但版本记录已落后；如需重新部署并刷新版本标记，请运行 --merge")
        else:
            ok("版本一致，部署完整")
        return 0

    if not version_changed and total_conflicts == 0:
        ok("版本一致且部署完整，无需重新部署")
        return 0

    backup_shared_workflow_state(root)
    if args.mode == "force":
        if not restore_workflow_from_original_backup(root):
            return 1
    if not has_workflow_patch(root / ".trellis" / "workflow.md") and not inject_workflow_patch(src, root):
        err("[Shared] workflow.md 项目化补丁恢复失败")
        return 1
    agents_md = root / "AGENTS.md"
    if agents_md.exists() and (
        not has_agents_md_routing(agents_md) or not agents_md_routing_matches_source(agents_md)
    ):
        if not deploy_agents_md_routing(root, False):
            err("[Shared] AGENTS.md NL 路由表恢复失败")
            return 1

    # 合并/修复
    for cli_type in cli_types:
        if cli_type == "claude":
            dst_cmds = root / ".claude" / "commands" / "trellis"
            start = dst_cmds / "start.md"
            finish_work = dst_cmds / "finish-work.md"
            record_session = dst_cmds / "record-session.md"
            parallel = dst_cmds / "parallel.md"
            backup_deployed_state(dst_cmds)
            deploy_commands(src, dst_cmds)
            if args.mode == "force":
                if not restore_start_from_original_backup(dst_cmds, start):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "finish-work"):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "record-session"):
                    return 1
                restore_optional_command_from_original_backup(dst_cmds, "parallel")
            if not has_phase_router(start) and not inject_phase_router(src, start):
                err("[Claude] Phase Router 恢复失败")
                return 1
            if not has_finish_work_patch(finish_work) and not inject_finish_work_patch(src, finish_work, "finish-work.md"):
                err("[Claude] finish-work 项目化补丁恢复失败")
                return 1
            if not has_record_session_patch(record_session) and not inject_record_session_patch(src, record_session):
                err("[Claude] record-session 元数据闭环恢复失败")
                return 1
            if parallel.exists():
                parallel.unlink()
                ok("[Claude] parallel.md 已从嵌入面移除")
            deploy_managed_agents(src, root, "claude", "Claude")
        elif cli_type == "opencode":
            dst_cmds = root / ".opencode" / "commands" / "trellis"
            start = dst_cmds / "start.md"
            finish_work = dst_cmds / "finish-work.md"
            record_session = dst_cmds / "record-session.md"
            parallel = dst_cmds / "parallel.md"
            backup_deployed_state(dst_cmds)
            deploy_commands(src, dst_cmds)
            if args.mode == "force":
                if not restore_start_from_original_backup(dst_cmds, start):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "finish-work"):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "record-session"):
                    return 1
                restore_optional_command_from_original_backup(dst_cmds, "parallel")
            if not has_phase_router(start) and not inject_phase_router(src, start):
                err("[OpenCode] Phase Router 恢复失败")
                return 1
            if not has_finish_work_patch(finish_work) and not inject_finish_work_patch(src, finish_work, "finish-work.md"):
                err("[OpenCode] finish-work 项目化补丁恢复失败")
                return 1
            if not has_record_session_patch(record_session) and not inject_record_session_patch(src, record_session):
                err("[OpenCode] record-session 元数据闭环恢复失败")
                return 1
            if parallel.exists():
                parallel.unlink()
                ok("[OpenCode] parallel.md 已从嵌入面移除")
            deploy_managed_agents(src, root, "opencode", "OpenCode")
        elif cli_type == "codex":
            deploy_codex_skills(src, root)
            skills_dirs = list_all_codex_skills_dirs(root)
            if not skills_dirs:
                continue
            primary_skills_dir = resolve_codex_skills_dir(root)
            if primary_skills_dir is None:
                err("[Codex] 未找到活动 skills 目录")
                return 1
            expected_parallel = expected_parallel_disabled_content(src)
            start_skill = primary_skills_dir / "start" / "SKILL.md"
            finish_work_skill = primary_skills_dir / "finish-work" / "SKILL.md"
            if args.mode == "force":
                start_backup = primary_skills_dir / ".backup-original" / "start" / "SKILL.md"
                finish_work_backup = primary_skills_dir / ".backup-original" / "finish-work" / "SKILL.md"
                if start_backup.exists() and not restore_codex_start_skill(primary_skills_dir):
                    return 1
                if finish_work_backup.exists() and not restore_codex_finish_work(primary_skills_dir):
                    return 1
            for skills_dir in skills_dirs:
                if args.mode == "force":
                    restore_optional_codex_skill(skills_dir, "parallel")
                parallel_skill = skills_dir / "parallel" / "SKILL.md"
                if parallel_skill.exists():
                    shutil.rmtree(parallel_skill.parent)
                    ok(f"[Codex] parallel skill 已从嵌入面移除 → {parallel_skill.relative_to(root)}")
            if not start_skill.exists():
                err(f"[Codex] 活动 skills 目录缺少 start 基线：{primary_skills_dir.relative_to(root)}")
                return 1
            if not finish_work_skill.exists():
                err(f"[Codex] 活动 skills 目录缺少 finish-work 基线：{primary_skills_dir.relative_to(root)}")
                return 1
            if not has_codex_start_skill_patch(start_skill):
                if not inject_codex_start_skill_patch(
                    src,
                    start_skill,
                    f"start skill ({primary_skills_dir.relative_to(root)})",
                ):
                    err("[Codex] start Phase Router 补丁恢复失败")
                    return 1
            if not has_finish_work_patch(finish_work_skill):
                if not inject_finish_work_patch(
                    src,
                    finish_work_skill,
                    f"finish-work skill ({primary_skills_dir.relative_to(root)})",
                ):
                    err("[Codex] finish-work 项目化补丁恢复失败")
                    return 1
            deploy_managed_agents(src, root, "codex", "Codex")

    cleanup_old_workflow_backups(root)

    # 辅助脚本
    deploy_scripts(src, dst_scripts)

    # 更新安装记录
    write_install_record(rec_file, current_version, installed_version, cli_types, record)

    # 清理旧备份
    for cli_type in cli_types:
        if cli_type in ("claude", "opencode"):
            dst_cmds = root / f".{cli_type}" / "commands" / "trellis"
            cleanup_old_backups(dst_cmds)

    print()
    print("✅ 升级兼容处理完成")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
