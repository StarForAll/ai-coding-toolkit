#!/usr/bin/env python3
"""在 trellis init 之后将当前自定义工作流安装到目标项目（多 CLI 支持）。

默认行为：自动检测目标项目中已存在的 Claude Code / OpenCode / Codex 配置，
并在同一个项目中同时部署对应适配层；`--cli` 仅用于过滤本次安装目标。

重要边界：
- 目标项目必须是 Git 仓库，`origin` 至少有两个 push URL，且已经执行过 `trellis init`
- 若是新建目标项目，本地主分支和初始分支必须为 `main`；已有本地提交历史的存量项目不强制切换
- 只有“纯净初始态”目标项目才允许执行首次嵌入；若检测到任何当前 workflow 的历史嵌入痕迹，必须阻止继续安装
- 当前 workflow 是“嵌入 + 增强”模型，不会重建 Trellis 原生命令全集
- `feasibility` 到 `delivery`（含 `project-audit`）这类阶段资产由当前 workflow 分发
- `continue` / `finish-work` / `record-session` 默认来自当前 Trellis 基线；当前 workflow 会在这些基线上追加补丁增强
- close-out 中的 `archive` 仍直接复用目标项目 Trellis 基线 `task.py`；若目标项目不是当前最新 Trellis 基线，可能不包含 archive auto-commit pathspec 修复
- 安装器会自动导入 `pack.requirements-discovery-foundation`；若目标项目存在 `00-bootstrap-guidelines` 则清理，不存在则跳过；若遗留的 repo-global `.current-task` 仍指向该 bootstrap task，则同步做兼容清理
- 一旦开始正式安装，安装器会先写入 `.trellis/workflow-embed-attempt.json`；若安装失败，该失败标记会保留，后续嵌入必须先由用户手动处理
- 首次嵌入执行应由可稳定执行项目安装脚本的入口（如 shell、Claude Code、OpenCode）完成；Codex 适合作为安装完成后的使用入口，不建议主导执行嵌入步骤

前提:
- 目标项目是 Git 仓库，`origin` 至少有两个 push URL，已执行 trellis init，且存在对应 CLI 目录
- 新建目标项目默认使用 `main` 作为本地主分支 / 初始分支；已有本地提交历史的项目可保留当前分支
- Codex 至少存在 .agents/skills/ 或 .codex/skills/ 之一

用法: python3 install-workflow.py [--project-root /path/to/project] [--cli claude,opencode,codex] [--dry-run]
卸载: python3 uninstall-workflow.py
"""
import argparse
import json
import os
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

TRELLIS_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / ".trellis" / "scripts"
if str(TRELLIS_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(TRELLIS_SCRIPTS_DIR))

from common.active_task import clear_task_from_sessions  # type: ignore[import-not-found]

from workflow_assets import (
    ADDED_COMMANDS,
    ALL_CLI_TYPES,
    CLI_ALT_DIRS,
    CLI_DIRS,
    CODEX_PATCH_BASELINE_SKILLS,
    CODEX_SHARED_SKILL_CLEANUP_NAMES,
    CORE_HELPER_SCRIPTS,
    DEFAULT_PROFILE,
    command_finish_work_candidates,
    command_phase_router_candidates,
    command_record_session_candidates,
    codex_finish_work_skill_candidates,
    codex_phase_router_skill_candidates,
    codex_secondary_skills_dir,
    codex_shared_skills_dir,
    DISTRIBUTED_COMMANDS,
    detect_cli_types as detect_cli_types_shared,
    EXECUTION_CARDS,
    find_first_existing_codex_skill_path,
    HELPER_SCRIPTS,
    legacy_agent_target_path,
    LEGACY_AGENT_NAMES,
    MANAGED_ENHANCED_AGENT_NAMES,
    list_all_codex_skills_dirs,
    OPTIONAL_DISABLED_BASELINE_COMMANDS,
    OUTSOURCING_EXECUTION_CARDS,
    OUTSOURCING_ONLY_SCRIPTS,
    OVERLAY_BASELINE_COMMANDS,
    PATCH_BASELINE_COMMANDS,
    PATCH_BASELINE_SHARED_DOCS,
    VALID_PROFILES,
    WORKFLOW_DOCS_DIR,
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_VERSION,
    AGENTS_NL_ROUTING_MARKERS,
    prepare_command_content,
    read_project_trellis_version,
    resolve_codex_skills_dir,
)


# ── ANSI ──
G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")
def err(m): print(f"{R}❌ {m}{N}")
def info(m): print(f"{C}ℹ️  {m}{N}")


def _remove_old_status_routing(content: str) -> str:
    """Remove old Step 3 (status=planning/in_progress routing) from baseline continue.md."""
    start_idx = content.find(_STATUS_ROUTING_MARKER)
    if start_idx == -1:
        return content
    end_idx = content.find(_STATUS_ROUTING_END_MARKER)
    if end_idx == -1 or end_idx <= start_idx:
        return content
    prefix = content[:start_idx]
    suffix = content[end_idx:]
    return prefix + suffix


# ── 常量 ──
_CLI_DIRS = CLI_DIRS
_CLI_ALT_DIRS = CLI_ALT_DIRS
_ALL_CLI_TYPES = ALL_CLI_TYPES
# 对 Trellis 原生命令做增强时使用的补丁标记。
# 当前 workflow 会增强 fresh baseline `continue.md` / `finish-work.md` / `record-session.md`；
# legacy `start.md` 仅在旧目标项目兼容路径中处理。
_PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
_STATUS_ROUTING_MARKER = "## Step 3: Decide Where You Are"
_STATUS_ROUTING_END_MARKER = "## Step 4: Load the Specific Step"
_FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
_FINISH_WORK_START_HEADING = "### 1. Code Quality"
_FINISH_WORK_END_HEADING = "### 2. close-out"
_FINISH_WORK_STEP1_HEADING = "## Step 1: Survey current state"
# For baseline finish-work.md (Trellis 0.5.16), Step 3/4 headings that
# the strong-gate patch must also replace.
_FINISH_WORK_STEP3_HEADING = "## Step 3: Archive task(s)"
_FINISH_WORK_STEP4_END_HEADING = "## Reference"
_CODEX_START_SKILL_MARKER = "## Workflow Phase Router Patch `[AI]`"
_WORKFLOW_PATCH_MARKER = "<!-- workflow-projectization-patch -->"
_WORKFLOW_START_HEADING = "## Development Process"
_WORKFLOW_END_HEADING = "## File Descriptions"
_WORKFLOW_PHASE_INDEX_MARKER = "<!-- workflow-projectization-phase-index-patch -->"
_WORKFLOW_BREADCRUMB_MARKER = "<!-- workflow-projectization-breadcrumb-patch -->"
_WORKFLOW_NO_TASK_MARKER = "<!-- workflow-projectization-no-task-patch -->"
_BASELINE_NO_TASK_START = "[workflow-state:no_task]"
_BASELINE_NO_TASK_END = "[/workflow-state:no_task]"
_BASELINE_PHASE_INDEX_START = "## Phase Index"
_BASELINE_PHASE_1_HEADING = "### Phase 1: Plan"
_BASELINE_CUSTOMIZING_HEADING = "## Customizing Trellis"
_TODO_FILE_NAME = "todo.txt"
_TODO_DEFAULT_LINE = "文档内容需要和实际当前的代码同步\n"
_EMBED_ATTEMPT_FILE_NAME = "workflow-embed-attempt.json"
_EMBED_ATTEMPT_STATUS_IN_PROGRESS = "in_progress"
_EMBED_ATTEMPT_STATUS_FAILED = "failed"
_EMBED_STATE_INITIAL = "INITIAL_BASELINE_READY"
_EMBED_STATE_VALID = "ALREADY_VALID_EMBEDDED"
_EMBED_STATE_BLOCKED = "BLOCKED_NON_INITIAL_STATE"
_REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"
_BOOTSTRAP_TASK_NAME = "00-bootstrap-guidelines"
_ORIGIN_REMOTE_NAME = "origin"
_MIN_ORIGIN_PUSH_URLS = 2
_PRIMARY_BRANCH_NAME = "main"
_HEAD_FILE_NAME = "HEAD"
_REFS_HEADS_PREFIX = "refs/heads/"
_PACKED_REFS_FILE = "packed-refs"
_PARALLEL_DISABLED_MARKER = "<!-- workflow-parallel-disabled -->"
_EMBED_EXECUTOR_CONFIRM_ENV = "WORKFLOW_EMBED_EXECUTOR_CONFIRMED"
_ENTRY_COMMAND_CANDIDATES = ("continue", "start")

# AGENTS.md NL 路由表标记
_AGENTS_NL_ROUTING_MARKER, _AGENTS_NL_ROUTING_END = AGENTS_NL_ROUTING_MARKERS

_NL_ROUTING_SECTION = """\
<!-- workflow-nl-routing-start -->

## 自然语言命令路由

> 由工作流安装器自动生成。当用户用自然语言描述意图时，本表提供阶段入口候选映射与推荐口径。
>
> 入口约束：
> - Claude Code / OpenCode：优先使用项目级 `/trellis:xxx` 命令；OpenCode CLI 可使用 `trellis/xxx`
> - Codex：通过 `AGENTS.md` 自然语言路由或显式触发对应 skill；不要期待项目级 `/trellis:xxx` 命令目录
> - 本表用于缩小候选范围，不表示所有 CLI 都存在确定性的自动命令路由；若命中歧义、缺少前置条件或上下文不足，仍应先确认再进入对应阶段
> - 当前 workflow 采用强门禁阶段状态机：阶段切换必须由用户明确确认；`/trellis:continue` 只重入当前已确认阶段，不自动跨阶段推进；legacy `/trellis:start` 仅用于旧目标项目兼容

### 工作流阶段命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 评估、能做吗、报价、新项目、风险、可行性、接不接、看看这个项目、能不能接、估个价、接私活、外包项目、客户需求 | `/trellis:feasibility` | 描述可行性评估意图，或显式触发 `feasibility` skill | §1 可行性评估。首次立项必经；若已有有效 assessment，可复用结果 |
| 需求、PRD、明确需求、需求文档、需求分析、想法、梳理需求、讨论方案、判断要不要拆任务 | `/trellis:brainstorm` | 描述需求澄清意图，或显式触发 `brainstorm` skill | §2 需求发现。前提：已存在有效 assessment |
| 设计、架构、架构设计、选型、接口设计、方案、技术方案、开始设计、画架构图、设计方案 | `/trellis:design` | 描述设计阶段意图，或显式触发 `design` skill | §3 设计阶段 |
| 拆任务、排期、计划、任务分解、里程碑、估时、做计划、工作分解、工作计划 | `/trellis:plan` | 描述任务拆解意图，或显式触发 `plan` skill | §4 任务拆解 |
| 写测试、TDD、测试驱动、先写测试、测试用例、验收测试 | `/trellis:test-first` | 描述测试先行意图，或显式触发 `test-first` skill | §4.3 测试先行 |
| 项目全局审查、全局代码审查、代码查缺补漏、项目审计、project-audit | `/trellis:project-audit` | 描述项目级审查意图，或显式触发 `project-audit` skill | §5.1 项目全局审查 |
| 检查一下、质量检查、对照 spec、对照规范、自检、有没有偏差 | `/trellis:check` | 描述质量检查意图，或显式触发 `check` skill | §5.1.x 质量检查 |
| 补充审查、多 CLI 审查、多人审查、让其他 CLI 看一下、review-gate、审查门禁 | `/trellis:review-gate` | 描述补充审查意图，或显式触发 `review-gate` skill | §5.1.y 补充审查 |
| 提交前检查、准备提交、完成检查、commit 前、收尾 | `/trellis:finish-work` | 描述提交前检查意图，或显式触发 `trellis-finish-work` skill | §6 提交检查 |
| 交付、部署、上线、发布、测试通过、准备交付、跑验收、整理交付物、项目收尾 | `/trellis:delivery` | 描述交付收尾意图，或显式触发 `delivery` skill | §6+§7 测试交付 |
| 记录、保存进度、收工、结束工作 | `/trellis:finish-work` | 描述会话收尾意图，或显式触发 `trellis-finish-work` skill | §7 会话记录 → delivery → record-session |

### 框架通用命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 调研、研究、查资料、查文档、看源码、搜代码、搜资料、技术调研、仓库分析 | 调用当前 CLI 的 `trellis-research` 子代理能力（若平台支持） | 描述研究意图，或显式触发 `trellis-research` agent | implementation 内部 research 链入口；用于代码/文档/仓库检索，不等于正式阶段命令 |
| 开始、新会话、继续、下一步 | `/trellis:continue` | 描述当前意图，或显式触发 `trellis-continue` skill | Phase Router 自动检测；legacy `/trellis:start` 仅兼容旧目标项目 |
| 卡住了、反复出错、死循环、调不通 | `/trellis:break-loop` | 描述排障意图，或显式触发 `trellis-break-loop` skill | 深度 bug 分析 |
| 更新规范、新发现、沉淀经验 | `/trellis:update-spec` | 描述规范更新意图，或显式触发 `trellis-update-spec` skill | 规范更新 |
| 跨层检查、跨模块、影响面 | `/trellis:check` + 手动指定跨层范围 | 描述跨层检查意图，或显式触发 `check` skill 并说明跨层范围 | 当前未提供专用 `check-cross-layer` skill；用 `/trellis:check` 替代 |
| 集成 skill、添加 skill | 手动完成 skill 集成 | 手动完成 skill 集成 | 当前未提供专用 `integrate-skill` skill；按 skill 文档手动集成 |
| 读规范、开发前准备、看看有什么规范 | `/trellis:before-dev` | 描述开发前准备意图，或显式触发 `trellis-before-dev` skill | 开发前读规范；默认主链里也会由 continue 自动执行 |
| 新人入门、项目介绍、怎么用 trellis | 阅读 AGENTS.md NL 路由表 | 阅读 AGENTS.md 路由表 | 当前未提供专用 `onboard` skill；按项目文档入门 |
| 创建命令、新命令、加个命令 | 按平台格式手动创建 | 按平台格式手动创建 | 当前未提供专用 `create-command` skill；按对应 CLI 格式手动创建 |

### 歧义消解

- 多个命令匹配时：当前阶段上下文 > 精确关键词 > 当前已确认阶段优先 > 模糊语义
- 无法确定时：路由到 `/trellis:continue`（Phase Router 自动检测）；legacy `/trellis:start` 仅用于旧目标项目兼容
- 当前 workflow 明确禁用基于 `parallel/worktree` 的后台 dispatch + PR 完成路径；如用户提到并行开发，应先回到 `/trellis:plan` 重新安排任务依赖，不再默认路由到 `parallel`
- top-2 优先级接近时：向用户确认意图，而不是假定已经完成自动精确路由

<!-- workflow-nl-routing-end -->
"""


# ── 项目根检测 ──
def find_root(start: Path) -> Path:
    """向上查找包含任一 CLI 目录的项目根目录。"""
    all_dirs = list(_CLI_DIRS.values()) + list(_CLI_ALT_DIRS.values())
    cur = start.resolve().parent
    for _ in range(10):
        for d in all_dirs:
            if (cur / d).is_dir():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    dirs_str = "、".join(f"{d}/" for d in all_dirs)
    sys.exit(f"{R}未找到任何 CLI 目录（{dirs_str}），请在 Trellis 项目内运行或用 --project-root 指定{N}")


def detect_cli_types(root: Path, requested: list[str] | None = None) -> list[str]:
    """检测项目中存在的 CLI 类型；默认返回全部检测到的 CLI，可按 requested 过滤。"""
    found = detect_cli_types_shared(root)
    if requested:
        found = [cli_type for cli_type in found if cli_type in requested]
    if not found:
        dirs_str = "、".join(f"{d}/" for d in _CLI_DIRS.values())
        sys.exit(f"{R}未找到任何 CLI 目录（{dirs_str}），请先初始化目标 CLI{N}")
    return found


def _read_text(path: Path | None) -> str | None:
    if path is None:
        return None
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _find_first_existing_command(dst_cmds: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        path = dst_cmds / f"{name}.md"
        if path.exists():
            return path
    return None


def _matches_expected_content(path: Path, expected: str) -> bool:
    actual = _read_text(path)
    if actual is None:
        return False
    return actual == expected


def _trace_display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _append_trace(traces: list[str], label: str, path: Path, root: Path) -> None:
    traces.append(f"{label}: {_trace_display(path, root)}")


def collect_workflow_embed_traces(src: Path, root: Path, cli_types: list[str]) -> list[str]:
    """Collect workflow-managed traces that prove the target project is not a clean initial baseline."""
    traces: list[str] = []

    attempt_record = root / ".trellis" / _EMBED_ATTEMPT_FILE_NAME
    if attempt_record.exists():
        _append_trace(traces, "embed-attempt-record", attempt_record, root)

    install_record = root / ".trellis" / "workflow-installed.json"
    if install_record.exists():
        _append_trace(traces, "install-record", install_record, root)

    workflow_md = root / ".trellis" / "workflow.md"
    workflow_text = _read_text(workflow_md)
    if workflow_text and _WORKFLOW_PATCH_MARKER in workflow_text:
        _append_trace(traces, "workflow-doc-patch", workflow_md, root)

    agents_md = root / "AGENTS.md"
    agents_text = _read_text(agents_md)
    if agents_text and _AGENTS_NL_ROUTING_MARKER in agents_text and _AGENTS_NL_ROUTING_END in agents_text:
        _append_trace(traces, "agents-routing-block", agents_md, root)

    helper_dir = root / ".trellis" / "scripts" / "workflow"
    for helper_name in HELPER_SCRIPTS:
        helper_path = helper_dir / helper_name
        if helper_path.exists():
            _append_trace(traces, "helper-script", helper_path, root)

    expected_overlay_content = {
        name: prepare_command_content(src / f"{name}.md")
        for name in OVERLAY_BASELINE_COMMANDS
        if (src / f"{name}.md").exists()
    }
    expected_added_content = {
        name: prepare_command_content(src / f"{name}.md")
        for name in ADDED_COMMANDS
        if (src / f"{name}.md").exists()
    }

    for cli_type in cli_types:
        if cli_type in ("claude", "opencode"):
            commands_dir = root / CLI_DIRS[cli_type] / "commands" / "trellis"
            if not commands_dir.is_dir():
                continue
            backup_dir = commands_dir / ".backup-original"
            if backup_dir.is_dir():
                _append_trace(traces, f"{cli_type}-backup-dir", backup_dir, root)

            for name, expected in expected_added_content.items():
                path = commands_dir / f"{name}.md"
                if _matches_expected_content(path, expected):
                    _append_trace(traces, f"{cli_type}-added-command", path, root)

            for name, expected in expected_overlay_content.items():
                path = commands_dir / f"{name}.md"
                if _matches_expected_content(path, expected):
                    _append_trace(traces, f"{cli_type}-overlay-command", path, root)

            marker_checks = [
                ("start-patch", commands_dir / "start.md", _PHASE_ROUTER_MARKER),
                ("finish-work-patch", commands_dir / "finish-work.md", _FINISH_WORK_MARKER),
                ("parallel-disabled", commands_dir / "parallel.md", _PARALLEL_DISABLED_MARKER),
            ]
            for label, path, marker in marker_checks:
                text = _read_text(path)
                if text and marker in text:
                    _append_trace(traces, f"{cli_type}-{label}", path, root)

            agents_dir = root / CLI_DIRS[cli_type] / "agents"
            if agents_dir.is_dir():
                backup_dir = agents_dir / ".backup-original"
                if backup_dir.is_dir():
                    _append_trace(traces, f"{cli_type}-agent-backup-dir", backup_dir, root)

        elif cli_type == "codex":
            skills_dirs = list_all_codex_skills_dirs(root)
            if not skills_dirs:
                continue
            expected_overlay_skills = expected_overlay_content
            for skills_dir in skills_dirs:
                backup_dir = skills_dir / ".backup-original"
                if backup_dir.is_dir():
                    _append_trace(traces, "codex-skill-backup-dir", backup_dir, root)

                for name, expected in expected_added_content.items():
                    path = skills_dir / name / "SKILL.md"
                    if _matches_expected_content(path, expected):
                        _append_trace(traces, "codex-added-skill", path, root)

                for name, expected in expected_overlay_skills.items():
                    path = skills_dir / name / "SKILL.md"
                    if _matches_expected_content(path, expected):
                        _append_trace(traces, "codex-overlay-skill", path, root)

                parallel_skill = skills_dir / "parallel" / "SKILL.md"
                parallel_text = _read_text(parallel_skill)
                if parallel_text and _PARALLEL_DISABLED_MARKER in parallel_text:
                    _append_trace(traces, "codex-parallel-disabled", parallel_skill, root)

            primary_skills_dir = resolve_codex_skills_dir(root)
            if primary_skills_dir is not None:
                router_skill = find_first_existing_codex_skill_path(
                    root,
                    codex_phase_router_skill_candidates(),
                    skills_dir=primary_skills_dir,
                )
                router_text = _read_text(router_skill)
                if router_text and _CODEX_START_SKILL_MARKER in router_text:
                    _append_trace(traces, "codex-start-patch", router_skill, root)

                finish_work_skill = find_first_existing_codex_skill_path(
                    root,
                    codex_finish_work_skill_candidates(),
                    skills_dir=primary_skills_dir,
                )
                finish_text = _read_text(finish_work_skill)
                if finish_text and _FINISH_WORK_MARKER in finish_text:
                    _append_trace(traces, "codex-finish-work-patch", finish_work_skill, root)

            agents_dir = root / ".codex" / "agents"
            if agents_dir.is_dir():
                backup_dir = agents_dir / ".backup-original"
                if backup_dir.is_dir():
                    _append_trace(traces, "codex-agent-backup-dir", backup_dir, root)

    return traces


def detect_embed_state(src: Path, root: Path, cli_types: list[str]) -> tuple[str, list[str]]:
    traces = collect_workflow_embed_traces(src, root, cli_types)
    if traces:
        return _EMBED_STATE_BLOCKED, traces
    return _EMBED_STATE_INITIAL, []


def embed_attempt_record_path(root: Path) -> Path:
    return root / ".trellis" / _EMBED_ATTEMPT_FILE_NAME


def write_embed_attempt_record(src: Path, root: Path, cli_types: list[str]) -> Path:
    now = datetime.now(timezone.utc).isoformat()
    workflow_root = src.parent
    workflow_spec = workflow_root / "工作流嵌入执行规范.md"
    attempt_path = embed_attempt_record_path(root)
    payload = {
        "status": _EMBED_ATTEMPT_STATUS_IN_PROGRESS,
        "workflow_version": WORKFLOW_VERSION,
        "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
        "workflow_spec_path": str(workflow_spec),
        "workflow_root": str(workflow_root),
        "target_project_root": str(root),
        "started_at": now,
        "updated_at": now,
        "cli_types": cli_types,
        "last_step": "preflight-passed",
    }
    attempt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return attempt_path


def update_embed_attempt_record(root: Path, **fields: object) -> None:
    attempt_path = embed_attempt_record_path(root)
    if not attempt_path.exists():
        return
    try:
        payload = json.loads(attempt_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}
    payload.update(fields)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    attempt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail_embed_attempt(root: Path, *, last_step: str, error: str) -> None:
    update_embed_attempt_record(
        root,
        status=_EMBED_ATTEMPT_STATUS_FAILED,
        last_step=last_step,
        error=error,
        failed_at=datetime.now(timezone.utc).isoformat(),
    )


def clear_embed_attempt_record(root: Path) -> None:
    attempt_path = embed_attempt_record_path(root)
    if attempt_path.exists():
        attempt_path.unlink()


def resolve_git_dir(root: Path) -> Path | None:
    """解析目标项目实际 Git 目录，兼容 .git 目录和 gitdir 文件。"""
    git_marker = root / ".git"
    if git_marker.is_dir():
        return git_marker
    if not git_marker.is_file():
        return None

    try:
        first_line = git_marker.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return None

    prefix = "gitdir:"
    if not first_line.lower().startswith(prefix):
        return None

    git_dir = first_line[len(prefix):].strip()
    if not git_dir:
        return None
    git_dir_path = Path(git_dir)
    if not git_dir_path.is_absolute():
        git_dir_path = (root / git_dir_path).resolve()
    return git_dir_path


def read_head_reference(git_dir: Path) -> tuple[str | None, bool]:
    """读取 HEAD 指向；返回 (ref_or_hash, is_symbolic_ref)。"""
    head_path = git_dir / _HEAD_FILE_NAME
    if not head_path.is_file():
        return None, False
    try:
        raw = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, False
    if not raw:
        return None, False
    prefix = "ref:"
    if raw.lower().startswith(prefix):
        return raw[len(prefix):].strip(), True
    return raw, False


def resolve_head_branch(root: Path) -> str | None:
    """解析当前本地分支名；detached HEAD 时返回 None。"""
    git_dir = resolve_git_dir(root)
    if git_dir is None:
        return None
    ref_or_hash, is_symbolic_ref = read_head_reference(git_dir)
    if not is_symbolic_ref or not ref_or_hash:
        return None
    if ref_or_hash.startswith(_REFS_HEADS_PREFIX):
        return ref_or_hash[len(_REFS_HEADS_PREFIX):]
    return ref_or_hash


def git_ref_exists(git_dir: Path, ref_name: str) -> bool:
    """检查 ref 是否已落地到本地 Git 元数据中。"""
    ref_path = git_dir / ref_name
    if ref_path.is_file():
        try:
            return bool(ref_path.read_text(encoding="utf-8").strip())
        except OSError:
            return False

    packed_refs = git_dir / _PACKED_REFS_FILE
    if not packed_refs.is_file():
        return False
    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("^"):
            continue
        parts = stripped.split(" ", 1)
        if len(parts) == 2 and parts[1].strip() == ref_name and parts[0].strip():
            return True
    return False


def has_local_commit_history(root: Path) -> bool:
    """判断当前仓库是否已有本地提交历史。"""
    git_dir = resolve_git_dir(root)
    if git_dir is None:
        return False
    ref_or_hash, is_symbolic_ref = read_head_reference(git_dir)
    if not ref_or_hash:
        return False
    if is_symbolic_ref:
        return git_ref_exists(git_dir, ref_or_hash)
    return True


def enforce_initial_main_branch_policy(root: Path) -> None:
    """对新建目标项目执行 main 分支门禁；已有历史项目仅提醒。"""
    branch_name = resolve_head_branch(root)
    has_history = has_local_commit_history(root)

    if branch_name == _PRIMARY_BRANCH_NAME:
        return

    if has_history:
        current = branch_name or "detached HEAD"
        warn(
            f"目标项目当前为 `{current}` 且已存在本地提交历史，workflow 不强制改为 `{_PRIMARY_BRANCH_NAME}`；"
            "若这仍是新建项目，请尽早统一默认分支。"
        )
        return

    if branch_name is None:
        sys.exit(
            f"{R}目标项目当前未处于可识别的本地分支；新建项目的主分支和初始分支必须使用 `{_PRIMARY_BRANCH_NAME}`。\n"
            f"请先执行：git checkout -b {_PRIMARY_BRANCH_NAME}{N}"
        )

    sys.exit(
        f"{R}目标项目当前本地分支为 `{branch_name}`；新建项目的主分支和初始分支必须使用 `{_PRIMARY_BRANCH_NAME}`。\n"
        f"请先执行：git branch -M {_PRIMARY_BRANCH_NAME}{N}"
    )


def count_origin_push_urls(root: Path) -> int:
    """统计 origin remote 下配置的 pushurl 数量。"""
    git_dir = resolve_git_dir(root)
    if git_dir is None:
        return 0

    config_path = git_dir / "config"
    if not config_path.is_file():
        return 0

    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0

    in_origin_block = False
    count = 0
    target_header = f'[remote "{_ORIGIN_REMOTE_NAME}"]'

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_origin_block = stripped == target_header
            continue
        if not in_origin_block or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip().lower() == "pushurl" and value.strip():
            count += 1

    return count


def normalize_task_ref(task_ref: str, root: Path) -> str:
    """规范化 `.current-task` 中的 task 引用，便于与 bootstrap task 比较。"""
    normalized = task_ref.strip()
    if not normalized:
        return ""

    path_obj = Path(normalized)
    if path_obj.is_absolute():
        try:
            normalized = path_obj.relative_to(root).as_posix()
        except ValueError:
            return normalized

    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("tasks/"):
        normalized = f".trellis/{normalized}"
    elif (
        "/" not in normalized
        and normalized
        and normalized not in {".", ".."}
        and not normalized.startswith(".trellis/")
    ):
        normalized = f".trellis/tasks/{normalized}"

    return normalized


def clear_bootstrap_current_task_if_needed(root: Path, dry_run: bool) -> bool:
    """若 `.current-task` 仍指向 bootstrap task，则同步清理该悬空引用。"""
    current_task_file = root / ".trellis" / ".current-task"
    if not current_task_file.is_file():
        return False

    current_task = normalize_task_ref(current_task_file.read_text(encoding="utf-8"), root)
    bootstrap_ref = f".trellis/tasks/{_BOOTSTRAP_TASK_NAME}"
    if current_task != bootstrap_ref:
        return False

    if dry_run:
        info(f"将清理 bootstrap current-task 引用 → {bootstrap_ref}")
        return True

    current_task_file.unlink()
    ok(f"已清理 bootstrap current-task 引用 → {bootstrap_ref}")
    return True


def _count_bootstrap_session_refs(root: Path) -> int:
    sessions_dir = root / ".trellis" / ".runtime" / "sessions"
    if not sessions_dir.is_dir():
        return 0

    bootstrap_ref = f".trellis/tasks/{_BOOTSTRAP_TASK_NAME}"
    count = 0
    for session_path in sessions_dir.glob("*.json"):
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        current_task = payload.get("current_task")
        if not isinstance(current_task, str):
            continue
        if normalize_task_ref(current_task, root) == bootstrap_ref:
            count += 1
    return count


def clear_bootstrap_session_runtime_if_needed(root: Path, dry_run: bool) -> int:
    """清理仍指向 bootstrap task 的 session runtime 文件。"""
    bootstrap_ref = f".trellis/tasks/{_BOOTSTRAP_TASK_NAME}"
    count = _count_bootstrap_session_refs(root)
    if count == 0:
        return 0

    if dry_run:
        info(f"将清理 bootstrap session active-task 引用 → {bootstrap_ref} ({count} 个 session)")
        return count

    cleared = clear_task_from_sessions(bootstrap_ref, root)
    ok(f"已清理 bootstrap session active-task 引用 → {bootstrap_ref} ({cleared} 个 session)")
    return cleared


def ensure_project_prereqs(root: Path) -> None:
    """校验目标项目满足 workflow 嵌入前提。"""
    git_marker = root / ".git"
    trellis_dir = root / ".trellis"
    trellis_version = trellis_dir / ".version"

    if not git_marker.exists():
        sys.exit(f"{R}目标项目不是 Git 仓库：缺少 .git，请先在项目根初始化 Git{N}")
    if not trellis_dir.is_dir():
        sys.exit(f"{R}目标项目未执行 trellis init：缺少 .trellis/ 目录{N}")
    if not trellis_version.is_file():
        sys.exit(f"{R}目标项目未检测到有效的 trellis init 产物：缺少 .trellis/.version{N}")
    push_url_count = count_origin_push_urls(root)
    if push_url_count < _MIN_ORIGIN_PUSH_URLS:
        sys.exit(
            f"{R}目标项目未满足 workflow 前置校验：`{_ORIGIN_REMOTE_NAME}` 至少需要 {_MIN_ORIGIN_PUSH_URLS} 个 push URL。\n"
            "请先为同一个 origin 配置多个 push 远端；若还没有 origin，先执行第一条：\n"
            "git remote add origin <你的第一个远程仓库URL>\n"
            "git remote set-url --add --push origin <第一个仓库URL>\n"
            f"git remote set-url --add --push origin <第二个仓库URL>{N}"
        )
    enforce_initial_main_branch_policy(root)


def ensure_embed_executor_confirmed(dry_run: bool) -> None:
    """Block until caller confirms this embed is not being executed from Codex.

    The workflow still supports Codex after install. This guard only protects the
    initial embed execution step.
    """
    if os.environ.get(_EMBED_EXECUTOR_CONFIRM_ENV) == "1":
        return
    if dry_run:
        return
    message = (
        "当前工作流嵌入步骤无法在 Codex 中嵌入成功，只能在 Claude Code / OpenCode（或直接 shell）中执行嵌入操作。\n"
        f"请确认当前执行这一步的不是 Codex；若确认无误，请重新执行并设置环境变量 {_EMBED_EXECUTOR_CONFIRM_ENV}=1。"
    )
    sys.exit(f"{R}{message}{N}")


# ── 命令文件预处理 ──
def prepare_parallel_disabled_content(src: Path) -> str | None:
    """读取禁用 parallel 的覆盖内容。"""
    source_path = src / "parallel-disabled.md"
    if not source_path.exists():
        return None
    return prepare_command_content(source_path)


def disable_parallel_command(src: Path, target_path: Path, *, dry_run: bool, cli_label: str) -> bool:
    """If a baseline parallel command exists, remove it from the embedded workflow surface.

    The workflow explicitly disables parallel/worktree execution, so we keep the
    backup but remove the command entry instead of leaving a disabled placeholder.
    """
    if not target_path.exists():
        return False

    if dry_run:
        info(f"[{cli_label}] 将移除 parallel 命令（已禁用，不嵌入到目标项目）")
    else:
        target_path.unlink()
        ok(f"[{cli_label}] parallel 命令已移除")
    return True


def disable_parallel_skill(src: Path, skills_dir: Path, *, dry_run: bool, cli_label: str) -> bool:
    """If a baseline Codex parallel skill exists, remove it from the embedded workflow surface.

    The workflow explicitly disables parallel/worktree execution. For Codex we should
    not leave an invalid placeholder SKILL.md behind because Codex expects valid YAML
    frontmatter. Instead, back up the baseline file and remove the skill from the
    project-local skills surface.
    """
    target_path = skills_dir / "parallel" / "SKILL.md"
    if not target_path.exists():
        return False

    if dry_run:
        info(f"[{cli_label}] 将移除 parallel skill（已禁用，不嵌入到目标项目）")
        return True

    skill_dir = target_path.parent
    shutil.rmtree(skill_dir)
    ok(f"[{cli_label}] parallel skill 已移除")
    return True


def build_finish_work_content(content: str, patch_text: str) -> str | None:
    """将 finish-work 的 Step 3/4 及 Code Quality 区块替换为项目化补丁。"""
    if _FINISH_WORK_MARKER in content:
        return content

    content = content.replace(
        'description: "Wrap up the current session: verify quality gate passed, remind user to commit, archive completed tasks, and record session progress to the developer journal. Use when done coding and ready to end the session."',
        'description: "Wrap up the current session: verify quality gate passed, collect close-out evidence, and hand off to delivery / record-session. Use when implementation is complete and ready for close-out."',
    )
    content = content.replace(
        "Wrap up the current session: archive the active task (and any other completed-but-unarchived tasks the user wants to clean up) and record the session journal. Code commits are NOT done here — those happen in workflow Phase 3.4 before you invoke this command.",
        "Wrap up the current session: verify close-out evidence, confirm the frozen quality matrix, and hand off to `delivery` / `record-session`. Code commits are NOT done here — those happen in workflow Phase 3.4 before you invoke this command.",
    )

    # Prefer replacing the full old Step 1-4 body when present so the
    # misleading archive/add_session guidance disappears from the top half too.
    start_idx = content.find(_FINISH_WORK_STEP1_HEADING)
    if start_idx == -1:
        # Fallback: from old archive/session steps through the end of Step 4.
        start_idx = content.find(_FINISH_WORK_STEP3_HEADING)
    if start_idx == -1:
        # Final fallback: try from "### 1. Code Quality" if no step headings exist.
        start_idx = content.find(_FINISH_WORK_START_HEADING)
    end_idx = content.find(_FINISH_WORK_STEP4_END_HEADING)
    if start_idx == -1:
        return content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"
    if end_idx != -1 and end_idx > start_idx:
        prefix = content[:start_idx]
        suffix = content[end_idx:]
        return prefix + patch_text.rstrip() + "\n\n" + suffix

    # Fallback: old narrow replacement (### 1. Code Quality to ### 1.5. Test Coverage)
    old_end_heading = "### 1.5. Test Coverage"
    end_idx = content.find(old_end_heading)
    if end_idx == -1 or end_idx <= start_idx:
        next_heading_idx = content.find("\n### ", start_idx + len(_FINISH_WORK_START_HEADING))
        if next_heading_idx == -1:
            return content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"
        end_idx = next_heading_idx + 1

    prefix = content[:start_idx]
    suffix = content[end_idx:].lstrip("\n")
    return prefix + patch_text.rstrip() + "\n\n" + suffix


def build_codex_phase_router_skill_content(content: str, patch_text: str) -> str:
    """Append workflow Phase Router guidance to the active Codex entry skill."""
    if _CODEX_START_SKILL_MARKER in content:
        return content
    return content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"


def inject_codex_phase_router_skill_patch(
    src: Path,
    target_path: Path,
    *,
    dry_run: bool,
    cli_label: str,
    target_label: str,
) -> bool:
    """为 Codex 当前入口 skill 注入 workflow Phase Router 补丁。"""
    if not target_path.exists():
        warn(f"[{cli_label}] {target_label} 不存在，跳过 Phase Router 补丁注入")
        return False

    content = target_path.read_text(encoding="utf-8")
    if _CODEX_START_SKILL_MARKER in content:
        ok(f"[{cli_label}] {target_label} Phase Router 补丁已存在")
        return False

    patch = src / "start-skill-patch-phase-router.md"
    if not patch.exists():
        warn(f"[{cli_label}] start-skill-patch-phase-router.md 不存在")
        return False

    new_content = build_codex_phase_router_skill_content(content, prepare_command_content(patch))
    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info(f"[{cli_label}] 将注入 {target_label} Phase Router 补丁")
    else:
        ok(f"[{cli_label}] {target_label} Phase Router 补丁已注入")
    return True


def build_codex_start_skill_content(content: str, patch_text: str) -> str:
    """Legacy wrapper preserved for tests and old helper call sites."""
    return build_codex_phase_router_skill_content(content, patch_text)


def inject_codex_start_skill_patch(
    src: Path,
    target_path: Path,
    *,
    dry_run: bool,
    cli_label: str,
) -> bool:
    """Legacy wrapper preserved for tests and old helper call sites."""
    return inject_codex_phase_router_skill_patch(
        src,
        target_path,
        dry_run=dry_run,
        cli_label=cli_label,
        target_label="entry skill",
    )


def build_workflow_content(content: str, patch_text: str) -> str | None:
    """用项目化补丁替换 workflow.md 中的 Development Process / Session End 区块。"""
    if _WORKFLOW_PATCH_MARKER in content:
        return content

    start_idx = content.find(_WORKFLOW_START_HEADING)
    end_idx = content.find(_WORKFLOW_END_HEADING)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return content.rstrip() + "\n\n" + patch_text.rstrip() + "\n"

    prefix = content[:start_idx]
    suffix = content[end_idx:].lstrip("\n")
    return prefix + patch_text.rstrip() + "\n\n" + suffix


def inject_finish_work_patch(
    src: Path,
    target_path: Path,
    *,
    dry_run: bool,
    cli_label: str,
    target_label: str,
) -> bool:
    """为 finish-work 基线注入项目化补丁。"""
    if not target_path.exists():
        warn(f"[{cli_label}] {target_label} 不存在，跳过项目化补丁注入")
        return False

    content = target_path.read_text(encoding="utf-8")
    if _FINISH_WORK_MARKER in content:
        ok(f"[{cli_label}] {target_label} 项目化补丁已存在")
        return False

    patch = src / "finish-work-patch-projectization.md"
    if not patch.exists():
        warn(f"[{cli_label}] finish-work-patch-projectization.md 不存在")
        return False

    new_content = build_finish_work_content(content, patch.read_text(encoding="utf-8"))
    if new_content is None:
        warn(f"[{cli_label}] {target_label} 中未找到可替换的 Code Quality 区块")
        return False

    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info(f"[{cli_label}] 将注入 {target_label} 项目化补丁")
    else:
        ok(f"[{cli_label}] {target_label} 项目化补丁已注入")
    return True


def inject_workflow_patch(src: Path, root: Path, *, dry_run: bool, profile: str = DEFAULT_PROFILE) -> bool:
    """为目标项目的 .trellis/workflow.md 注入项目化补丁。"""
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        warn("[Shared] .trellis/workflow.md 不存在，跳过项目化补丁注入")
        return False

    patch = src / "workflow-patch-projectization.md"
    if not patch.exists():
        warn("[Shared] workflow-patch-projectization.md 不存在")
        return False

    patch_text = prepare_command_content(patch, profile=profile)
    content = target_path.read_text(encoding="utf-8")
    if _WORKFLOW_PATCH_MARKER in content and patch_text in content:
        ok("[Shared] workflow.md 项目化补丁已存在")
        return False

    baseline_content = content
    if _WORKFLOW_PATCH_MARKER in content and patch_text not in content:
        backup_path = root / ".trellis" / ".backup-original" / "workflow.md"
        if backup_path.exists():
            baseline_content = backup_path.read_text(encoding="utf-8")
        else:
            warn("[Shared] workflow.md 已存在旧补丁，但缺少 .backup-original/workflow.md，无法自动刷新")
            return False

    new_content = build_workflow_content(baseline_content, patch_text)
    if new_content is None:
        warn("[Shared] workflow.md 中未找到可替换的 Development Process / Session End 区块")
        return False

    if not dry_run:
        backup_dir = root / ".trellis" / ".backup-original"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / "workflow.md"
        if not backup_path.exists():
            shutil.copy2(target_path, backup_path)
            ok("[Shared] workflow.md → 备份")
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将注入 workflow.md 项目化补丁")
    else:
        ok("[Shared] workflow.md 项目化补丁已注入")
    return True


def _extract_breadcrumb_block(content: str, start_tag: str, end_tag: str) -> tuple[str, int, int] | None:
    """Extract a breadcrumb block delimited by start_tag and end_tag from content.

    Returns (block_text, start_offset, end_offset) or None if not found.
    """
    start_idx = content.find(start_tag)
    if start_idx == -1:
        return None
    end_idx = content.find(end_tag, start_idx + len(start_tag))
    if end_idx == -1:
        return None
    end_idx += len(end_tag)
    return content[start_idx:end_idx], start_idx, end_idx


def inject_workflow_phase_index_patch(src: Path, root: Path, *, dry_run: bool, profile: str = DEFAULT_PROFILE) -> bool:
    """Replace the baseline Phase Index section with strong-gate version in workflow.md."""
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        warn("[Shared] workflow.md 不存在，跳过 Phase Index 补丁注入")
        return False

    patch = src / "workflow-patch-projectization.md"
    if not patch.exists():
        warn("[Shared] workflow-patch-projectization.md 不存在，跳过 Phase Index 补丁")
        return False

    patch_text = prepare_command_content(patch, profile=profile)

    # Extract Phase Index replacement section from patch
    phase_index_marker = _WORKFLOW_PHASE_INDEX_MARKER
    if phase_index_marker not in patch_text:
        warn("[Shared] workflow-patch-projectization.md 缺少 Phase Index 模板标记")
        return False

    phase_index_start = patch_text.find(phase_index_marker)
    # Find the second --- after the marker (first separates Phase Index from
    # Customizing Trellis; second separates from Strong-Gate Breadcrumb Blocks).
    # We need both sections to replace the old Phase Index + old Customizing Trellis.
    first_sep = patch_text.find("\n---\n", phase_index_start)
    if first_sep == -1:
        phase_index_section = patch_text[phase_index_start:]
    else:
        second_sep = patch_text.find("\n---\n", first_sep + 1)
        if second_sep == -1:
            phase_index_section = patch_text[phase_index_start:]
        else:
            phase_index_section = patch_text[phase_index_start:second_sep]

    content = target_path.read_text(encoding="utf-8")
    if phase_index_marker in content:
        ok("[Shared] workflow.md Phase Index 强门禁补丁已存在")
        return False

    # Find baseline Phase Index block: from "## Phase Index" to "## Strong-Gate Breadcrumb Blocks"
    # (removes old Phase 1/2/3 content and old Customizing Trellis section)
    phase_index_idx = content.find(_BASELINE_PHASE_INDEX_START)
    if phase_index_idx == -1:
        warn("[Shared] workflow.md 中未找到 ## Phase Index，跳过替换")
        return False

    breadcrumb_heading = "## Strong-Gate Breadcrumb Blocks"
    breadcrumb_idx = content.find(breadcrumb_heading, phase_index_idx)
    customizing_idx = content.find(_BASELINE_CUSTOMIZING_HEADING, phase_index_idx)

    if breadcrumb_idx != -1:
        # Replace from ## Phase Index to ## Strong-Gate Breadcrumb Blocks
        # (includes replacing old Customizing Trellis section)
        prefix = content[:phase_index_idx]
        suffix = content[breadcrumb_idx:]
        new_content = prefix + phase_index_section.rstrip() + "\n\n" + suffix
    elif customizing_idx != -1:
        # Replace from ## Phase Index to ## Customizing Trellis
        prefix = content[:phase_index_idx]
        suffix = content[customizing_idx:]
        new_content = prefix + phase_index_section.rstrip() + "\n\n" + suffix
    else:
        # Fallback: old behavior — only replace up to ### Phase 1: Plan
        phase1_idx = content.find(_BASELINE_PHASE_1_HEADING, phase_index_idx)
        if phase1_idx == -1:
            warn("[Shared] workflow.md 中未找到 ### Phase 1: Plan 且无 ## Customizing Trellis，跳过替换")
            return False
        prefix = content[:phase_index_idx]
        suffix = content[phase1_idx:]
        new_content = prefix + phase_index_section.rstrip() + "\n\n" + suffix

    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将注入 workflow.md Phase Index 强门禁补丁")
    else:
        ok("[Shared] workflow.md Phase Index 强门禁补丁已注入")
    return True


def inject_workflow_no_task_patch(src: Path, root: Path, *, dry_run: bool, profile: str = DEFAULT_PROFILE) -> bool:
    """Replace the baseline no_task breadcrumb block with strong-gate version in workflow.md."""
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        warn("[Shared] workflow.md 不存在，跳过 no_task 补丁注入")
        return False

    patch = src / "workflow-patch-projectization.md"
    if not patch.exists():
        warn("[Shared] workflow-patch-projectization.md 不存在，跳过 no_task 补丁")
        return False

    patch_text = prepare_command_content(patch, profile=profile)

    no_task_marker = _WORKFLOW_NO_TASK_MARKER
    if no_task_marker not in patch_text:
        warn("[Shared] workflow-patch-projectization.md 缺少 no_task 模板标记")
        return False

    no_task_start = patch_text.find(no_task_marker)
    # Find next --- or end of file as boundary
    next_section = patch_text.find("\n---\n", no_task_start)
    if next_section == -1:
        no_task_section = patch_text[no_task_start:]
    else:
        no_task_section = patch_text[no_task_start:next_section]

    content = target_path.read_text(encoding="utf-8")
    if no_task_marker in content:
        ok("[Shared] workflow.md no_task 强门禁补丁已存在")
        return False

    # Find and replace baseline no_task block
    block_info = _extract_breadcrumb_block(content, _BASELINE_NO_TASK_START, _BASELINE_NO_TASK_END)
    if block_info is None:
        warn("[Shared] workflow.md 中未找到 baseline [workflow-state:no_task] 块")
        return False

    _, block_start, block_end = block_info
    prefix = content[:block_start]
    suffix = content[block_end:]
    new_content = prefix + no_task_section.rstrip() + "\n" + suffix

    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将注入 workflow.md no_task 强门禁补丁")
    else:
        ok("[Shared] workflow.md no_task 强门禁补丁已注入")
    return True


def inject_workflow_breadcrumb_patch(src: Path, root: Path, *, dry_run: bool, profile: str = DEFAULT_PROFILE) -> bool:
    """Inject strong-gate breadcrumb blocks for all stages into workflow.md."""
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        warn("[Shared] workflow.md 不存在，跳过 breadcrumb 补丁注入")
        return False

    patch = src / "workflow-patch-projectization.md"
    if not patch.exists():
        warn("[Shared] workflow-patch-projectization.md 不存在，跳过 breadcrumb 补丁")
        return False

    patch_text = prepare_command_content(patch, profile=profile)

    breadcrumb_marker = _WORKFLOW_BREADCRUMB_MARKER
    if breadcrumb_marker not in patch_text:
        warn("[Shared] workflow-patch-projectization.md 缺少 breadcrumb 模板标记")
        return False

    breadcrumb_start = patch_text.find(breadcrumb_marker)
    # Find next --- or no_task section as boundary
    no_task_marker_idx = patch_text.find(_WORKFLOW_NO_TASK_MARKER, breadcrumb_start)
    if no_task_marker_idx != -1:
        breadcrumb_section = patch_text[breadcrumb_start:no_task_marker_idx]
    else:
        next_section = patch_text.find("\n---\n", breadcrumb_start)
        if next_section == -1:
            breadcrumb_section = patch_text[breadcrumb_start:]
        else:
            breadcrumb_section = patch_text[breadcrumb_start:next_section]

    content = target_path.read_text(encoding="utf-8")
    if breadcrumb_marker in content:
        ok("[Shared] workflow.md 强门禁 breadcrumb 补丁已存在")
        return False

    # Insert before the no_task block (or at end if no_task block not found)
    block_info = _extract_breadcrumb_block(content, _BASELINE_NO_TASK_START, _BASELINE_NO_TASK_END)
    if block_info is not None:
        _, block_start, _ = block_info
        prefix = content[:block_start]
        suffix = content[block_start:]
        new_content = prefix + breadcrumb_section.rstrip() + "\n\n" + suffix
    else:
        new_content = content.rstrip() + "\n\n" + breadcrumb_section.rstrip() + "\n"

    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将注入 workflow.md 强门禁 breadcrumb 补丁")
    else:
        ok("[Shared] workflow.md 强门禁 breadcrumb 补丁已注入")
    return True


def _apply_patch_workflow_phase(src: Path, root: Path, *, dry_run: bool) -> bool:
    """Apply patch-workflow-phase.py to the deployed workflow_phase.py helper."""
    import importlib.util

    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    target_wf_phase = dst_scripts / "workflow_phase.py"
    patch_script = src / "shell" / "patch-workflow-phase.py"

    if not target_wf_phase.exists():
        info("[Shared] workflow_phase.py 不存在，跳过强门禁补丁")
        return False

    if not patch_script.exists():
        warn("[Shared] patch-workflow-phase.py 不存在，跳过强门禁补丁")
        return False

    if dry_run:
        info(f"[Shared] 将对 workflow_phase.py 应用强门禁补丁 → {target_wf_phase}")
        return True

    spec = importlib.util.spec_from_file_location("patch_workflow_phase", patch_script)
    if spec is None or spec.loader is None:
        warn("[Shared] patch-workflow-phase.py 加载失败")
        return False
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "patch_workflow_phase"):
        result = module.patch_workflow_phase(target_wf_phase)
        if result:
            ok("[Shared] workflow_phase.py 强门禁补丁已应用")
        return result

    warn("[Shared] patch-workflow-phase.py 缺少 patch_workflow_phase 函数")
    return False


# ── Issue 1+7: patch deployed inject-workflow-state.py hook ──
_HOOK_PATCH_MARKER = "# [workflow-embed-patch:prefer-workflow-state-json]"


def patch_inject_workflow_state_hook(root: Path, *, dry_run: bool) -> bool:
    """Patch deployed inject-workflow-state.py to prefer workflow-state.json.stage (Issue 1)
    and strip fenced code blocks before breadcrumb parsing (Issue 7).

    Codex (.codex/) and Claude (.claude/) both receive Issue 1 and Issue 7 patches.
    """
    any_patched = False

    for hook_subpath, apply_issue1 in [
        (".codex/hooks/inject-workflow-state.py", True),
        (".claude/hooks/inject-workflow-state.py", True),
    ]:
        hook_path = root / hook_subpath
        if not hook_path.exists():
            continue

        content = hook_path.read_text(encoding="utf-8")

        issue1_already_applied = apply_issue1 and _HOOK_PATCH_MARKER in content
        if issue1_already_applied and "re.sub(r" in content:
            ok(f"[Shared] {hook_subpath} hook 补丁已存在")
            continue

        patched = content

        # ── Issue 7: strip fenced code blocks before _TAG_RE.finditer() ──
        # Insert a re.sub line after "content = workflow.read_text(encoding="utf-8")"
        # inside load_breadcrumbs().
        code_block_strip_line = '        content = re.sub(r"```.*?```", "", content, flags=re.DOTALL)\n'
        read_text_anchor = '        content = workflow.read_text(encoding="utf-8")\n'
        if read_text_anchor in patched and code_block_strip_line not in patched:
            insert_pos = patched.find(read_text_anchor) + len(read_text_anchor)
            patched = patched[:insert_pos] + code_block_strip_line + patched[insert_pos:]

        # ── Issue 1: prefer workflow-state.json.stage over task.json.status ──
        # (Applied to Codex and Claude hooks)
        if apply_issue1 and not issue1_already_applied:
            ws_override_block = """\
    # [workflow-embed-patch:prefer-workflow-state-json]
    # Prefer workflow-state.json.stage over task.json.status for strong-gate projects
    _ws_source = None
    _ws_path = task_dir / "workflow-state.json"
    if _ws_path.is_file():
        try:
            _ws_data = json.loads(_ws_path.read_text(encoding="utf-8"))
            _ws_stage = _ws_data.get("stage", "")
            if isinstance(_ws_stage, str) and _ws_stage:
                status = _ws_stage
                _ws_source = "workflow-state.json"
        except (json.JSONDecodeError, OSError):
            pass
"""
            return_anchor = "    return task_id, status, active.source\n"
            return_replacement = "    return task_id, status, _ws_source or active.source\n"
            if return_anchor in patched and _HOOK_PATCH_MARKER not in patched:
                func_def = "def get_active_task("
                func_start = patched.find(func_def)
                if func_start != -1:
                    return_pos = patched.find(return_anchor, func_start)
                    next_def = patched.find("\ndef ", func_start + len(func_def))
                    if next_def == -1 or return_pos < next_def:
                        patched = patched[:return_pos] + ws_override_block + return_replacement + patched[return_pos + len(return_anchor):]

        if patched == content:
            warn(f"[Shared] {hook_subpath} 补丁未命中目标代码，跳过")
            continue

        if not dry_run:
            hook_path.write_text(patched, encoding="utf-8")
        label = "优先 workflow-state.json.stage + 移除代码块示例" if apply_issue1 else "移除代码块示例"
        if dry_run:
            info(f"[Shared] 将补丁 {hook_subpath} hook（{label}）")
        else:
            ok(f"[Shared] {hook_subpath} hook 已补丁（{label}）")
        any_patched = True

    # ── Issue 2: patch OpenCode inject-workflow-state.js ──
    # Prefer workflow-state.json.stage over task.json.status for strong-gate projects
    opencode_js_subpath = ".opencode/plugins/inject-workflow-state.js"
    opencode_js_path = root / opencode_js_subpath
    if opencode_js_path.exists():
        js_content = opencode_js_path.read_text(encoding="utf-8")
        js_patch_marker = "// [workflow-embed-patch:prefer-workflow-state-json]"
        if js_patch_marker in js_content:
            ok(f"[Shared] {opencode_js_subpath} 补丁已存在")
        else:
            # Find the anchor: line right after "taskDir" stale check and before task.json read
            js_anchor = '  const taskJsonPath = join(taskDir, "task.json")\n'
            if js_anchor in js_content:
                js_override_block = """\
  // [workflow-embed-patch:prefer-workflow-state-json]
  // Prefer workflow-state.json.stage over task.json.status for strong-gate projects
  const wsPath = join(taskDir, "workflow-state.json")
  if (existsSync(wsPath)) {
    try {
      const wsData = JSON.parse(readFileSync(wsPath, "utf-8"))
      const wsStage = typeof wsData.stage === "string" && wsData.stage ? wsData.stage : ""
      if (wsStage) {
        const id = wsData.id || taskRef.split("/").pop()
        return { id, status: wsStage, source: "workflow-state.json" }
      }
    } catch {
      // fall through to task.json
    }
  }
"""
                insert_pos = js_content.find(js_anchor)
                patched_js = js_content[:insert_pos] + js_override_block + js_content[insert_pos:]
                if not dry_run:
                    opencode_js_path.write_text(patched_js, encoding="utf-8")
                if dry_run:
                    info(f"[Shared] 将补丁 {opencode_js_subpath}（优先 workflow-state.json.stage）")
                else:
                    ok(f"[Shared] {opencode_js_subpath} 已补丁（优先 workflow-state.json.stage）")
                any_patched = True
            else:
                warn(f"[Shared] {opencode_js_subpath} 补丁未命中目标代码，跳过")

    return any_patched


# ── C2: patch session-start no-task guidance to reference NL routing table ──
_SESSION_START_NO_TASK_MARKER = "# [workflow-embed-patch:session-start-nl-routing]"
_SESSION_START_NO_TASK_OLD = (
    '"Next-Action: After the user describes their intent, load skill `trellis-brainstorm` '
    'to clarify requirements and create a task via `python3 ./.trellis/scripts/task.py create`.\\n"'
)
_SESSION_START_NO_TASK_NEW = (
    '"Next-Action: Consult the AGENTS.md NL routing table for profile-specific entry routing. '
    'For outsourcing profile: run `python3 ./.trellis/scripts/workflow/workflow-state.py route` '
    'to detect first-entry and load `/trellis:feasibility`. '
    'For personal profile: load skill `trellis-brainstorm` to clarify requirements '
    'and create a task via `python3 ./.trellis/scripts/task.py create`.\\n"'
)


def patch_session_start_no_task_guidance(root: Path, *, dry_run: bool) -> bool:
    """Patch session-start hook no-task guidance to reference AGENTS.md NL routing table.

    The baseline session-start hook unconditionally directs to trellis-brainstorm +
    task.py create, which bypasses the feasibility gate for outsourcing profile.
    This patch updates the guidance to check the profile and route accordingly.
    """
    hook_path = root / ".claude" / "hooks" / "session-start.py"
    if not hook_path.exists():
        return False

    content = hook_path.read_text(encoding="utf-8")
    if _SESSION_START_NO_TASK_MARKER in content:
        ok("[Shared] session-start.py no-task guidance 补丁已存在")
        return False

    if _SESSION_START_NO_TASK_OLD not in content:
        warn("[Shared] session-start.py no-task 指导未命中目标代码，跳过")
        return False

    patched = content.replace(
        _SESSION_START_NO_TASK_OLD,
        _SESSION_START_NO_TASK_MARKER + "\n            " + _SESSION_START_NO_TASK_NEW,
    )

    if patched == content:
        warn("[Shared] session-start.py 补丁未生效，跳过")
        return False

    if not dry_run:
        hook_path.write_text(patched, encoding="utf-8")
        ok("[Shared] session-start.py no-task guidance 已补丁（引用 NL 路由表）")
    else:
        info("[Shared] 将补丁 session-start.py no-task guidance（引用 NL 路由表）")
    return True


# ── Issue 2: cleanup legacy three-phase breadcrumb blocks ──
_LEGACY_BREADCRUMB_TAGS = (
    "stale",
    "planning",
    "planning-inline",
    "in_progress",
    "in_progress-inline",
    "completed",
)
_LEGACY_WORKFLOW_SECTION_START = "## Phase Index"
_LEGACY_WORKFLOW_SECTION_END = "## Customizing Trellis (for forks)"


def cleanup_legacy_breadcrumb_blocks(root: Path, *, dry_run: bool) -> int:
    """Remove legacy three-phase breadcrumb blocks from embedded workflow.md (Issue 2).

    After strong-gate Phase Index + breadcrumb patches are applied, the old
    three-phase breadcrumb blocks (stale, planning, planning-inline, in_progress,
    in_progress-inline, completed) should be removed to avoid duplicate
    [workflow-state:STATUS] blocks that confuse the hook parser.
    """
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        return 0

    content = target_path.read_text(encoding="utf-8")
    removed = 0

    for tag in _LEGACY_BREADCRUMB_TAGS:
        start_tag = f"[workflow-state:{tag}]"
        end_tag = f"[/workflow-state:{tag}]"
        block_info = _extract_breadcrumb_block(content, start_tag, end_tag)
        if block_info is not None:
            block_text, block_start, block_end = block_info
            # Only remove legacy blocks when strong-gate breadcrumb patch
            # has been applied — without the marker, the file still follows
            # the baseline three-phase model and these blocks are valid.
            sg_marker_idx = content.find(_WORKFLOW_BREADCRUMB_MARKER)
            if sg_marker_idx == -1:
                continue
            # Legacy blocks are those that appear before the strong-gate marker
            if block_start < sg_marker_idx:
                # Remove the block and any surrounding blank lines
                before = content[:block_start].rstrip("\n")
                after = content[block_end:].lstrip("\n")
                content = before + "\n\n" + after
                removed += 1

    if removed > 0:
        if not dry_run:
            target_path.write_text(content, encoding="utf-8")
        if dry_run:
            info(f"[Shared] 将移除 {removed} 个旧三阶段 breadcrumb 块")
        else:
            ok(f"[Shared] 已移除 {removed} 个旧三阶段 breadcrumb 块")
    return removed


def cleanup_legacy_phase_router_sections(root: Path, *, dry_run: bool) -> bool:
    """Remove the legacy three-phase workflow contract from embedded workflow.md.

    The strong-gate workflow patch appends a new stage-machine contract after the
    baseline three-phase Phase Index section. Leaving the old section in place
    causes hooks and session-start carriers to read conflicting instructions.
    """
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        return False

    content = target_path.read_text(encoding="utf-8")
    marker_idx = content.find(_WORKFLOW_PHASE_INDEX_MARKER)
    if marker_idx == -1:
        return False

    start_idx = content.find(_LEGACY_WORKFLOW_SECTION_START)
    contract_idx = content.find("WORKFLOW-STATE BREADCRUMB CONTRACT")
    if contract_idx != -1:
        comment_start = content.rfind("<!--", 0, contract_idx)
        if comment_start != -1 and (start_idx == -1 or comment_start < start_idx):
            start_idx = comment_start
    end_idx = content.find(_LEGACY_WORKFLOW_SECTION_END)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return False
    if start_idx >= marker_idx:
        return False

    before = content[:start_idx].rstrip("\n")
    after = content[end_idx:].lstrip("\n")
    new_content = before + "\n\n" + after
    if new_content == content:
        return False

    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将移除 workflow.md 中旧三阶段 Phase Index / Plan-Execute-Finish 合同")
    else:
        ok("[Shared] 已移除 workflow.md 中旧三阶段 Phase Index / Plan-Execute-Finish 合同")
    return True


# ── Issue 6: cleanup stale workflow-state-contract.md references ──
_STALE_CONTRACT_PATTERN = ".trellis/spec/cli/backend/workflow-state-contract.md"
_STALE_CONTRACT_REPLACEMENT = "workflow-state.py --help"
_TASK_DEGRADED_PATCH_MARKER = "# [workflow-embed-patch:degraded-active-task]"
_OPENCODE_SESSION_UTILS_PATCH_MARKER = "// [workflow-embed-patch:strong-gate-session-utils]"


def cleanup_stale_contract_references(root: Path, *, dry_run: bool) -> bool:
    """Replace references to non-existent workflow-state-contract.md in embedded workflow.md (Issue 6)."""
    target_path = root / ".trellis" / "workflow.md"
    if not target_path.exists():
        return False

    content = target_path.read_text(encoding="utf-8")
    if _STALE_CONTRACT_PATTERN not in content:
        return False

    new_content = content.replace(_STALE_CONTRACT_PATTERN, _STALE_CONTRACT_REPLACEMENT)
    if not dry_run:
        target_path.write_text(new_content, encoding="utf-8")
    if dry_run:
        info("[Shared] 将替换 workflow-state-contract.md 引用 → workflow-state.py --help")
    else:
        ok("[Shared] 已替换 workflow-state-contract.md 引用 → workflow-state.py --help")
    return True


def patch_task_start_degraded_fallback(root: Path, *, dry_run: bool) -> bool:
    """Patch task.py so degraded start writes a fallback active-task file.

    The strong-gate router already knows how to recover from
    `.trellis/.runtime/degraded-active-task.json`, but the Trellis baseline
    `task.py start` degraded branch never writes it.
    """
    task_path = root / ".trellis" / "scripts" / "task.py"
    if not task_path.exists():
        return False

    content = task_path.read_text(encoding="utf-8")
    if _TASK_DEGRADED_PATCH_MARKER in content:
        ok("[Shared] task.py degraded fallback 补丁已存在")
        return False

    anchor = '        # Still flip task.json status: planning → in_progress so downstream phases proceed.\n'
    if anchor not in content:
        warn("[Shared] task.py degraded fallback 补丁未命中目标代码，跳过")
        return False

    patch_block = """\
        # [workflow-embed-patch:degraded-active-task]
        degraded_runtime = repo_root / ".trellis" / ".runtime"
        degraded_runtime.mkdir(parents=True, exist_ok=True)
        degraded_path = degraded_runtime / "degraded-active-task.json"
        degraded_payload = {
            "current_task": task_dir,
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "source": "task.py start (degraded)",
        }
        if write_json(degraded_path, degraded_payload):
            print(colored("✓ Wrote degraded active-task fallback", Colors.GREEN))

"""
    patched = content.replace(anchor, patch_block + anchor, 1)

    finish_anchor = '    if task_json_path.is_file():\n        run_task_hooks("after_finish", task_json_path, repo_root)\n    return 0\n'
    finish_patch = """\
    degraded_path = repo_root / ".trellis" / ".runtime" / "degraded-active-task.json"
    if degraded_path.exists():
        payload = read_json(degraded_path)
        if isinstance(payload, dict) and payload.get("current_task") == current:
            degraded_path.unlink()

"""
    if finish_anchor in patched:
        patched = patched.replace(finish_anchor, finish_patch + finish_anchor, 1)

    if not dry_run:
        task_path.write_text(patched, encoding="utf-8")
    if dry_run:
        info("[Shared] 将补丁 task.py degraded start fallback → .trellis/.runtime/degraded-active-task.json")
    else:
        ok("[Shared] task.py degraded start fallback 已补丁")
    return True


def patch_opencode_session_utils(root: Path, *, dry_run: bool) -> bool:
    """Patch OpenCode session-utils.js to route from workflow-state instead of READY semantics."""
    session_utils = root / ".opencode" / "lib" / "session-utils.js"
    if not session_utils.exists():
        return False

    content = session_utils.read_text(encoding="utf-8")
    if _OPENCODE_SESSION_UTILS_PATCH_MARKER in content:
        ok("[Shared] .opencode/lib/session-utils.js 强门禁补丁已存在")
        return False

    new_block = """\
// [workflow-embed-patch:strong-gate-session-utils]
function getTaskStatus(ctx, platformInput = null) {
  const active = ctx.getActiveTask(platformInput)
  const taskRef = active.taskPath
  const routeScript = join(ctx.directory, ".trellis", "scripts", "workflow", "workflow-state.py")

  if (!existsSync(routeScript)) {
    return `Status: ROUTER UNAVAILABLE\\nSource: ${active.source}\\nNext: Missing .trellis/scripts/workflow/workflow-state.py`
  }

  const args = [routeScript, "route", "--project-root", ctx.directory]
  if (taskRef) {
    args.splice(2, 0, taskRef)
  }

  try {
    const output = execFileSync(PYTHON_CMD, args, {
      cwd: ctx.directory,
      timeout: 5000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        ...(platformInput && typeof ctx.getContextKey === "function" && ctx.getContextKey(platformInput)
          ? { TRELLIS_CONTEXT_ID: ctx.getContextKey(platformInput) }
          : {}),
      },
    })
    const data = JSON.parse(output)
    const stage = typeof data.stage === "string" && data.stage ? data.stage : "(unknown)"
    const action = typeof data.action === "string" ? data.action : "unknown"
    const blockers = Array.isArray(data.blockers) ? data.blockers : []
    const blockerText = blockers.length > 0 ? `\\nBlockers: ${blockers.join(" | ")}` : ""
    return `Stage: ${stage}\\nAction: ${action}\\nReason: ${data.reason || ""}${blockerText}`
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    return `Status: ROUTER FAILED\\nSource: ${active.source}\\nNext: workflow-state.py route failed\\nError: ${message}`
  }
}
"""
    func_start = content.find("function getTaskStatus(ctx, platformInput = null) {")
    if func_start == -1:
        warn("[Shared] .opencode/lib/session-utils.js 强门禁补丁未命中目标代码，跳过")
        return False
    next_func = content.find("\nfunction loadTrellisConfig(", func_start)
    if next_func == -1:
        next_func = len(content)
    patched = content[:func_start] + new_block.rstrip() + "\n\n" + content[next_func:].lstrip("\n")
    if not dry_run:
        session_utils.write_text(patched, encoding="utf-8")
    if dry_run:
        info("[Shared] 将补丁 .opencode/lib/session-utils.js → 改用 workflow-state.py route")
    else:
        ok("[Shared] .opencode/lib/session-utils.js 已补丁 → 改用 workflow-state.py route")
    return True


def _migrate_legacy_agents(root: Path, cli_type: str, cli_label: str, *, dry_run: bool = False) -> dict:
    """Migrate legacy bare-name agent files to Trellis 0.5 naming convention.

    Before Trellis 0.5, agents were deployed as bare names (research.md).
    Trellis 0.5+ provides trellis-{name}.md / trellis-{name}.toml natively.
    This function renames any remaining legacy bare-name files.
    """
    result = {"agents": 0, "errors": []}
    agents_dir = root / CLI_DIRS[cli_type] / "agents"

    if not agents_dir.is_dir():
        return result

    for agent_name in LEGACY_AGENT_NAMES:
        legacy_path = legacy_agent_target_path(root, cli_type, agent_name)
        if cli_type == "codex":
            new_path = root / CLI_DIRS[cli_type] / "agents" / f"trellis-{agent_name}.toml"
        else:
            new_path = root / CLI_DIRS[cli_type] / "agents" / f"trellis-{agent_name}.md"

        if legacy_path.exists() and not new_path.exists():
            if dry_run:
                ok(f"[{cli_label}] agent 将重命名: {legacy_path.name} → {new_path.name}")
            else:
                import shutil
                shutil.copy2(legacy_path, new_path)
                legacy_path.unlink()
                ok(f"[{cli_label}] agent renamed: {legacy_path.name} → {new_path.name}")
            result["agents"] += 1
        elif legacy_path.exists() and new_path.exists():
            if dry_run:
                ok(f"[{cli_label}] 将删除 legacy 残留: {legacy_path.name}（trellis 版本已存在）")
            else:
                legacy_path.unlink()
                ok(f"[{cli_label}] legacy 残留已删除: {legacy_path.name}（trellis 版本已存在）")
            result["agents"] += 1

    return result


# ── Claude Code 部署 ──
def deploy_claude(src: Path, root: Path, dry_run: bool, *, profile: str = DEFAULT_PROFILE) -> dict:
    """部署到 .claude/commands/trellis/"""
    dst_cmds = root / ".claude" / "commands" / "trellis"
    backup = dst_cmds / ".backup-original"
    result = {"commands": 0, "scripts": 0, "patches": 0, "agents": 0, "errors": []}

    if not dst_cmds.is_dir():
        result["errors"].append(".claude/commands/trellis/ 不存在，请先运行: trellis init")
        return result

    # 备份
    if not dry_run:
        backup.mkdir(parents=True, exist_ok=True)
        entry_command = _find_first_existing_command(dst_cmds, _ENTRY_COMMAND_CANDIDATES)
        finish_work = dst_cmds / "finish-work.md"
        parallel = dst_cmds / "parallel.md"
        baseline_overlaps = [dst_cmds / f"{name}.md" for name in OVERLAY_BASELINE_COMMANDS]
        if entry_command is not None and not (backup / entry_command.name).exists():
            shutil.copy2(entry_command, backup / entry_command.name)
            ok(f"[Claude] {entry_command.name} → 备份")
        if finish_work.exists() and not (backup / "finish-work.md").exists():
            shutil.copy2(finish_work, backup / "finish-work.md")
            ok(f"[Claude] finish-work.md → 备份")
        if parallel.exists() and not (backup / "parallel.md").exists():
            shutil.copy2(parallel, backup / "parallel.md")
            ok("[Claude] parallel.md → 备份")
        for baseline_cmd in baseline_overlaps:
            backup_target = backup / baseline_cmd.name
            if baseline_cmd.exists() and not backup_target.exists():
                shutil.copy2(baseline_cmd, backup_target)
                ok(f"[Claude] {baseline_cmd.name} → 备份")

    # 部署命令
    for cmd in DISTRIBUTED_COMMANDS:
        s = src / f"{cmd}.md"
        d = dst_cmds / f"{cmd}.md"
        if s.exists():
            if dry_run:
                info(f"[Claude] 将部署 /trellis:{cmd}")
            else:
                c = prepare_command_content(s, profile=profile)
                d.write_text(c, encoding="utf-8")
                ok(f"[Claude] /trellis:{cmd}")
            result["commands"] += 1
        else:
            warn(f"[Claude] 源文件缺失: {cmd}.md")

    # 注入 Phase Router
    entry_command = _find_first_existing_command(dst_cmds, _ENTRY_COMMAND_CANDIDATES)
    if entry_command is not None:
        content = entry_command.read_text(encoding="utf-8")
        if _PHASE_ROUTER_MARKER not in content:
            # Remove old Step 3 (status-based routing) before injecting Phase Router
            content = _remove_old_status_routing(content)
            patch = src / "start-patch-phase-router.md"
            if patch.exists():
                patch_text = prepare_command_content(patch)
                marker = "## Operation Types"
                if marker in content:
                    before, after = content.split(marker, 1)
                    new_content = before + patch_text + "\n" + marker + after
                else:
                    new_content = content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"
                if not dry_run:
                    entry_command.write_text(new_content, encoding="utf-8")
                if dry_run:
                    info(f"[Claude] 将注入 Phase Router 到 {entry_command.name}")
                else:
                    ok(f"[Claude] Phase Router 已注入 {entry_command.name}")
                result["patches"] += 1
            else:
                warn("[Claude] start-patch-phase-router.md 不存在")
        else:
            ok(f"[Claude] Phase Router 已存在 → {entry_command.name}")
    else:
        warn("[Claude] continue.md / start.md 不存在，跳过 Phase Router 注入")

    finish_work = dst_cmds / "finish-work.md"
    if inject_finish_work_patch(
        src,
        finish_work,
        dry_run=dry_run,
        cli_label="Claude",
        target_label="finish-work.md",
    ):
        result["patches"] += 1

    if disable_parallel_command(src, dst_cmds / "parallel.md", dry_run=dry_run, cli_label="Claude"):
        result["patches"] += 1

    return result


# ── OpenCode 部署 ──
def deploy_opencode(src: Path, root: Path, dry_run: bool, *, profile: str = DEFAULT_PROFILE) -> dict:
    """部署到 .opencode/commands/trellis/（命令文件格式与 Claude Code 完全兼容）"""
    dst_cmds = root / ".opencode" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"
    result = {"commands": 0, "scripts": 0, "patches": 0, "agents": 0, "errors": []}

    if not dst_cmds.is_dir():
        result["errors"].append(".opencode/commands/trellis/ 不存在，请先初始化 OpenCode")
        return result

    # 备份
    if not dry_run:
        backup.mkdir(parents=True, exist_ok=True)
        entry_command = _find_first_existing_command(dst_cmds, _ENTRY_COMMAND_CANDIDATES)
        finish_work = dst_cmds / "finish-work.md"
        parallel = dst_cmds / "parallel.md"
        baseline_overlaps = [dst_cmds / f"{name}.md" for name in OVERLAY_BASELINE_COMMANDS]
        if entry_command is not None and not (backup / entry_command.name).exists():
            shutil.copy2(entry_command, backup / entry_command.name)
            ok(f"[OpenCode] {entry_command.name} → 备份")
        if finish_work.exists() and not (backup / "finish-work.md").exists():
            shutil.copy2(finish_work, backup / "finish-work.md")
            ok(f"[OpenCode] finish-work.md → 备份")
        if parallel.exists() and not (backup / "parallel.md").exists():
            shutil.copy2(parallel, backup / "parallel.md")
            ok("[OpenCode] parallel.md → 备份")
        for baseline_cmd in baseline_overlaps:
            backup_target = backup / baseline_cmd.name
            if baseline_cmd.exists() and not backup_target.exists():
                shutil.copy2(baseline_cmd, backup_target)
                ok(f"[OpenCode] {baseline_cmd.name} → 备份")

    # 部署命令（与 Claude Code 完全相同的文件格式）
    for cmd in DISTRIBUTED_COMMANDS:
        s = src / f"{cmd}.md"
        d = dst_cmds / f"{cmd}.md"
        if s.exists():
            if dry_run:
                info(f"[OpenCode] 将部署 {cmd}（TUI: /trellis:{cmd} / CLI: trellis/{cmd}）")
            else:
                c = prepare_command_content(s, profile=profile)
                d.write_text(c, encoding="utf-8")
                ok(f"[OpenCode] {cmd}（TUI: /trellis:{cmd} / CLI: trellis/{cmd}）")
            result["commands"] += 1
        else:
            warn(f"[OpenCode] 源文件缺失: {cmd}.md")

    # 注入 Phase Router
    entry_command = _find_first_existing_command(dst_cmds, _ENTRY_COMMAND_CANDIDATES)
    if entry_command is not None:
        content = entry_command.read_text(encoding="utf-8")
        if _PHASE_ROUTER_MARKER not in content:
            # Remove old Step 3 (status-based routing) before injecting Phase Router
            content = _remove_old_status_routing(content)
            patch = src / "start-patch-phase-router.md"
            if patch.exists():
                patch_text = prepare_command_content(patch)
                marker = "## Operation Types"
                if marker in content:
                    before, after = content.split(marker, 1)
                    new_content = before + patch_text + "\n" + marker + after
                else:
                    new_content = content.rstrip() + "\n\n---\n\n" + patch_text.rstrip() + "\n"
                if not dry_run:
                    entry_command.write_text(new_content, encoding="utf-8")
                if dry_run:
                    info(f"[OpenCode] 将注入 Phase Router 到 {entry_command.name}")
                else:
                    ok(f"[OpenCode] Phase Router 已注入 {entry_command.name}")
                result["patches"] += 1
            else:
                warn("[OpenCode] start-patch-phase-router.md 不存在")
        else:
            ok(f"[OpenCode] Phase Router 已存在 → {entry_command.name}")
    else:
        warn("[OpenCode] continue.md / start.md 不存在，跳过 Phase Router 注入")

    finish_work = dst_cmds / "finish-work.md"
    if inject_finish_work_patch(
        src,
        finish_work,
        dry_run=dry_run,
        cli_label="OpenCode",
        target_label="finish-work.md",
    ):
        result["patches"] += 1

    if disable_parallel_command(src, dst_cmds / "parallel.md", dry_run=dry_run, cli_label="OpenCode"):
        result["patches"] += 1

    # 辅助脚本已在 Claude Code 部署时处理，此处不重复计数
    return result


# ── Codex CLI 部署 ──
def deploy_codex(src: Path, root: Path, dry_run: bool, *, profile: str = DEFAULT_PROFILE) -> dict:
    """部署到 Codex skills 目录。

    共享 workflow skills 只写入 `.agents/skills/`。
    `.codex/skills/` 只保留 Codex 独有 skills；若存在重复 shared skills，应清理。
    baseline patch 型 skills（trellis-continue / trellis-finish-work）只增强活动目录；
    legacy start / finish-work 仅作为旧目标项目兼容输入。
    """
    skills_dirs = list_all_codex_skills_dirs(root)
    if not skills_dirs:
        return {
            "commands": 0,
            "scripts": 0,
            "patches": 0,
            "agents": 0,
            "manual_checks": 0,
            "errors": ["未找到 .agents/skills/ 或 .codex/skills/ 目录"],
        }
    primary_skills_dir = resolve_codex_skills_dir(root)
    if primary_skills_dir is None:
        return {
            "commands": 0,
            "scripts": 0,
            "patches": 0,
            "agents": 0,
            "manual_checks": 0,
            "errors": ["未找到 Codex 活动 skills 目录"],
        }

    result = {"commands": 0, "scripts": 0, "patches": 0, "agents": 0, "manual_checks": 0, "errors": []}
    shared_skills_dir = codex_shared_skills_dir(root)
    secondary_skills_dir = codex_secondary_skills_dir(root)

    # 备份禁用型 / baseline patch 型 skills
    if not dry_run:
        for skills_dir in skills_dirs:
            for name in OPTIONAL_DISABLED_BASELINE_COMMANDS:
                skill_path = skills_dir / name / "SKILL.md"
                backup_path = skills_dir / ".backup-original" / name / "SKILL.md"
                if skill_path.exists() and not backup_path.exists():
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(skill_path, backup_path)
                    ok(f"[Codex] {name} skill → {skills_dir.relative_to(root)}/.backup-original")
        for name in CODEX_PATCH_BASELINE_SKILLS:
            skill_path = primary_skills_dir / name / "SKILL.md"
            backup_path = primary_skills_dir / ".backup-original" / name / "SKILL.md"
            if skill_path.exists() and not backup_path.exists():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_path, backup_path)
                ok(f"[Codex] {name} skill → {primary_skills_dir.relative_to(root)}/.backup-original")
        if secondary_skills_dir.is_dir():
            for name in CODEX_SHARED_SKILL_CLEANUP_NAMES:
                duplicate_path = secondary_skills_dir / name / "SKILL.md"
                backup_path = secondary_skills_dir / ".backup-original" / name / "SKILL.md"
                if duplicate_path.exists() and not backup_path.exists():
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(duplicate_path, backup_path)
                    ok(f"[Codex] duplicate {name} skill → {secondary_skills_dir.relative_to(root)}/.backup-original")

    # 部署共享 skills（只写入 .agents/skills）
    for cmd in DISTRIBUTED_COMMANDS:
        s = src / f"{cmd}.md"
        if s.exists():
            d = shared_skills_dir / cmd / "SKILL.md"
            if dry_run:
                info(f"[Codex] 将部署 shared skill: {cmd} → {shared_skills_dir.relative_to(root)}")
            else:
                c = prepare_command_content(s, profile=profile)
                d.parent.mkdir(parents=True, exist_ok=True)
                d.write_text(c, encoding="utf-8")
                ok(f"[Codex] shared skill: {cmd} → {d.relative_to(root)}")
            result["commands"] += 1
        else:
            warn(f"[Codex] 源文件缺失: {cmd}.md")

    # 清理 .codex/skills/ 中重复的 shared skills
    if secondary_skills_dir.is_dir():
        for name in CODEX_SHARED_SKILL_CLEANUP_NAMES:
            duplicate_dir = secondary_skills_dir / name
            if not duplicate_dir.exists():
                continue
            if dry_run:
                info(f"[Codex] 将移除 duplicate shared skill: {name} → {secondary_skills_dir.relative_to(root)}")
            else:
                shutil.rmtree(duplicate_dir)
                ok(f"[Codex] duplicate shared skill 已移除: {duplicate_dir.relative_to(root)}")

    # 注入 finish-work 补丁（只增强活动 skills 目录）
    finish_work_skill = find_first_existing_codex_skill_path(
        root,
        codex_finish_work_skill_candidates(),
        skills_dir=primary_skills_dir,
    )
    if finish_work_skill is None:
        result["errors"].append(
            f"活动 skills 目录缺少 {CODEX_PATCH_BASELINE_SKILLS[1]} 基线，无法注入 workflow 项目化补丁：{primary_skills_dir.relative_to(root)}"
        )
    elif inject_finish_work_patch(
        src,
        finish_work_skill,
        dry_run=dry_run,
        cli_label="Codex",
        target_label=f"{finish_work_skill.parent.name} skill",
    ):
        result["patches"] += 1

    # 注入入口 skill Phase Router 补丁（优先 trellis-continue，兼容旧 start）
    router_skill = find_first_existing_codex_skill_path(
        root,
        codex_phase_router_skill_candidates(),
        skills_dir=primary_skills_dir,
    )
    if router_skill is None:
        result["errors"].append(
            f"活动 skills 目录缺少 {CODEX_PATCH_BASELINE_SKILLS[0]} 基线，无法注入 workflow Phase Router 补丁：{primary_skills_dir.relative_to(root)}"
        )
    else:
        if inject_codex_phase_router_skill_patch(
            src,
            router_skill,
            dry_run=dry_run,
            cli_label="Codex",
            target_label=f"{router_skill.parent.name} skill",
        ):
            result["patches"] += 1

    # Codex 当前通过 hooks.json 引用的 inject-workflow-state.py hook 注入上下文，
    # 不需要注入 start.md。
    # 验证 hook 是否已就绪（全局只检查一次）。
    # 这些属于 Trellis baseline / 项目手动维护面，不计入 workflow patch 数。
    hooks_json = root / ".codex" / "hooks.json"
    if hooks_json.exists():
        ok("[Codex] hooks.json 已存在")
        result["manual_checks"] += 1
    else:
        warn("[Codex] hooks.json 不存在，Codex hook 注入未配置")

    inject_workflow_state = root / ".codex" / "hooks" / "inject-workflow-state.py"
    if inject_workflow_state.exists():
        ok("[Codex] inject-workflow-state.py hook 已存在")
        result["manual_checks"] += 1
    else:
        warn("[Codex] inject-workflow-state.py 不存在，Codex workflow 上下文注入不可用")

    # 禁用 parallel（对所有目录，但 patches 只计一次）
    parallel_patched = False
    for skills_dir in skills_dirs:
        if disable_parallel_skill(src, skills_dir, dry_run=dry_run, cli_label="Codex"):
            if not parallel_patched:
                result["patches"] += 1
                parallel_patched = True

    # 辅助脚本已在 Claude Code 部署时处理
    return result


# ── 辅助脚本部署（共享） ──
def deploy_helper_scripts(src: Path, root: Path, dry_run: bool, *, profile: str = DEFAULT_PROFILE) -> int:
    """部署平台无关的辅助脚本到 .trellis/scripts/workflow/"""
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    count = 0
    dst_scripts.mkdir(parents=True, exist_ok=True)
    scripts = HELPER_SCRIPTS if profile == "outsourcing" else CORE_HELPER_SCRIPTS
    for f in scripts:
        s = src / "shell" / f
        d = dst_scripts / f
        if s.exists():
            if not dry_run:
                shutil.copy2(s, d)
                d.chmod(0o755)
            count += 1
    return count, len(scripts)


def deploy_execution_cards(src: Path, root: Path, dry_run: bool, *, profile: str = DEFAULT_PROFILE) -> int:
    """分发执行卡文档到 .trellis/workflow-docs/"""
    workflow_root = src.parent  # commands/ 的上一级即 workflow 根目录
    dst = root / WORKFLOW_DOCS_DIR
    cards = list(EXECUTION_CARDS)
    if profile == "outsourcing":
        cards.extend(OUTSOURCING_EXECUTION_CARDS)
    count = 0
    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
    for card_name in cards:
        card_src = workflow_root / card_name
        card_dst = dst / card_name
        if card_src.exists():
            if dry_run:
                info(f"将分发执行卡 → {WORKFLOW_DOCS_DIR}/{card_name}")
            else:
                shutil.copy2(card_src, card_dst)
                ok(f"执行卡 → {WORKFLOW_DOCS_DIR}/{card_name}")
            count += 1
        else:
            warn(f"执行卡源文件不存在: {card_src}")
    return count


def import_requirements_foundation(root: Path, dry_run: bool) -> bool:
    """安装后自动导入需求发现基础资产。"""
    repo_root = Path(__file__).resolve().parents[4]
    cli_path = repo_root / "trellis-library" / "cli.py"
    command = [
        sys.executable,
        str(cli_path),
        "assemble",
        "--target",
        str(root),
        "--pack",
        _REQUIREMENTS_FOUNDATION_PACK,
        "--auto",
    ]
    if dry_run:
        info(f"将导入初始 spec 基线 → {_REQUIREMENTS_FOUNDATION_PACK}")
        return True

    result = subprocess.run(
        command,
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        err(f"导入初始 spec 基线失败 → {_REQUIREMENTS_FOUNDATION_PACK}")
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        return False

    ok(f"初始 spec 基线已导入 → {_REQUIREMENTS_FOUNDATION_PACK}")
    return True


def run_post_install_check(src: Path, root: Path, cli_types: list[str], dry_run: bool) -> bool:
    """Run a final read-only self-check before declaring embed success."""
    if dry_run:
        info("将执行装后自检 → upgrade-compat.py --check")
        return True

    command = [sys.executable, str(src / "upgrade-compat.py"), "--check", "--project-root", str(root)]
    if cli_types:
        command.extend(["--cli", ",".join(cli_types)])
    current_version = read_project_trellis_version(root)
    env = dict(os.environ)
    if current_version:
        env["TRELLIS_LATEST_VERSION"] = current_version
    env["WORKFLOW_IGNORE_EMBED_ATTEMPT"] = "1"
    result = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        err("装后自检失败，当前项目已被标记为非初始态；请由用户手动处理后重新完整嵌入")
        return False
    ok("装后自检通过")
    return True


# ── 安装记录 ──
def write_install_record(
    root: Path,
    cli_types: list[str],
    dry_run: bool,
    *,
    profile: str = DEFAULT_PROFILE,
    bootstrap_cleanup: str = "unknown",
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    ver = (root / ".trellis" / ".version").read_text(encoding="utf-8").strip() \
        if (root / ".trellis" / ".version").exists() else "unknown"
    rec = root / ".trellis" / "workflow-installed.json"
    bootstrap_task_removed = bootstrap_cleanup in {"removed", "dry-run-removed"}
    scripts = HELPER_SCRIPTS if profile == "outsourcing" else CORE_HELPER_SCRIPTS
    cards = list(EXECUTION_CARDS)
    if profile == "outsourcing":
        cards.extend(OUTSOURCING_EXECUTION_CARDS)
    if not dry_run:
        rec.write_text(json.dumps({
            "trellis_version": ver,
            "installed": now,
            "cli_types": cli_types,
            "profile": profile,
            "commands": DISTRIBUTED_COMMANDS,
            "overlay_commands": OVERLAY_BASELINE_COMMANDS,
            "added_commands": ADDED_COMMANDS,
            "disabled_commands": OPTIONAL_DISABLED_BASELINE_COMMANDS,
            "patched_baseline_commands": [
                command_phase_router_candidates()[0],
                command_finish_work_candidates()[0],
            ],
            "patched_codex_skills": CODEX_PATCH_BASELINE_SKILLS,
            "patched_shared_docs": PATCH_BASELINE_SHARED_DOCS,
            # Legacy compatibility field: fresh installs no longer manage
            # enhanced agents, but older records/readers still understand it.
            "managed_enhanced_agents": MANAGED_ENHANCED_AGENT_NAMES,
            "scripts": list(scripts),
            "execution_cards": cards,
            "workflow_version": WORKFLOW_VERSION,
            "workflow_schema_version": WORKFLOW_SCHEMA_VERSION,
            "initial_pack": _REQUIREMENTS_FOUNDATION_PACK,
            "bootstrap_task_removed": bootstrap_task_removed,
            "bootstrap_cleanup_status": bootstrap_cleanup,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    if dry_run:
        info(f"将写入安装记录 → {rec.name} (Trellis {ver}, CLI: {', '.join(cli_types)})")
    else:
        ok(f"安装记录 → {rec.name} (Trellis {ver}, CLI: {', '.join(cli_types)})")


# ── todo.txt ──
def ensure_project_todo(root: Path) -> None:
    todo_path = root / _TODO_FILE_NAME
    if todo_path.exists():
        warn(f"{_TODO_FILE_NAME} 已存在，保留现有内容")
        return
    todo_path.write_text(_TODO_DEFAULT_LINE, encoding="utf-8")
    ok(f"初始化提醒 → {_TODO_FILE_NAME}")


def remove_bootstrap_task(root: Path, dry_run: bool) -> str:
    """安装 workflow 后删除 Trellis init 创建的 bootstrap task。

    返回值表示本次清理的实际状态：

    - ``"removed"``  : 目标项目存在 bootstrap task，且已实际删除
    - ``"absent"``   : 目标项目本就没有 bootstrap task（例如目标 Trellis 基线不再生成）
    - ``"dry-run-removed"`` : dry-run 模式下识别到了存在的 bootstrap task
    """
    task_dir = root / ".trellis" / "tasks" / _BOOTSTRAP_TASK_NAME
    current_task_cleared = clear_bootstrap_current_task_if_needed(root, dry_run)
    session_refs_cleared = clear_bootstrap_session_runtime_if_needed(root, dry_run)

    if not task_dir.exists():
        info(f"{_BOOTSTRAP_TASK_NAME} 不存在，跳过清理")
        return "absent"
    if dry_run:
        info(f"将删除 Trellis bootstrap 任务 → .trellis/tasks/{_BOOTSTRAP_TASK_NAME}")
        return "dry-run-removed"
    if task_dir.is_dir():
        shutil.rmtree(task_dir)
    else:
        task_dir.unlink()
    ok(f"Trellis bootstrap 任务已删除 → {_BOOTSTRAP_TASK_NAME}")
    if not current_task_cleared and session_refs_cleared == 0:
        info("bootstrap task 引用无需清理")
    return "removed"


# ── AGENTS.md NL 路由表注入 ──
def deploy_agents_md_routing(root: Path, dry_run: bool) -> bool:
    """将 NL 路由表注入到项目 AGENTS.md（为无 hooks 的 CLI 提供路由信息）。"""
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        warn("AGENTS.md 不存在，跳过 NL 路由表注入")
        return False

    content = agents_md.read_text(encoding="utf-8")

    # 已存在则替换
    if _AGENTS_NL_ROUTING_MARKER in content:
        start_idx = content.index(_AGENTS_NL_ROUTING_MARKER)
        end_idx = content.index(_AGENTS_NL_ROUTING_END) + len(_AGENTS_NL_ROUTING_END)
        new_content = content[:start_idx] + _NL_ROUTING_SECTION.rstrip() + content[end_idx:]
        if not dry_run:
            agents_md.write_text(new_content, encoding="utf-8")
        if dry_run:
            info("将更新 AGENTS.md NL 路由表")
        else:
            ok("AGENTS.md NL 路由表已更新")
        return True

    # 不存在则追加到末尾
    if not dry_run:
        with agents_md.open("a", encoding="utf-8") as f:
            f.write("\n\n" + _NL_ROUTING_SECTION)
    if dry_run:
        info("将注入 AGENTS.md NL 路由表")
    else:
        ok("AGENTS.md NL 路由表已注入")
    return True


# ── 主流程 ──
def main() -> int:
    p = argparse.ArgumentParser(
        description="安装自定义工作流到 Trellis Git 项目（默认同一项目同时部署已检测到的 Claude Code / OpenCode / Codex 适配层）"
    )
    p.add_argument("--project-root", type=Path, default=None, help="项目根目录（默认自动检测）")
    p.add_argument("--cli", type=str, default=None,
                   help="指定 CLI 类型，逗号分隔: claude,opencode,codex（默认安装全部检测到的 CLI；此参数仅用于过滤）")
    p.add_argument("--profile", choices=VALID_PROFILES, default=DEFAULT_PROFILE,
                   help=f"安装配置: personal（排除外包内容）/ outsourcing（完整内容，默认: {DEFAULT_PROFILE}）")
    p.add_argument("--dry-run", action="store_true", help="预览安装结果，不实际写入")
    args = p.parse_args()

    src = Path(__file__).resolve().parent
    root = args.project_root or find_root(Path(__file__))
    ensure_project_prereqs(root)
    ensure_embed_executor_confirmed(args.dry_run)

    # 检测 CLI 类型
    requested = [x.strip() for x in args.cli.split(",")] if args.cli else None
    if requested:
        for r in requested:
            if r not in _ALL_CLI_TYPES:
                sys.exit(f"{R}未知 CLI 类型: {r}（支持: {', '.join(_ALL_CLI_TYPES)}）{N}")
    cli_types = detect_cli_types(root, requested)
    state, traces = detect_embed_state(src, root, cli_types)
    if state != _EMBED_STATE_INITIAL:
        trace_lines = "\n".join(f"- {trace}" for trace in traces)
        sys.exit(
            f"{R}目标项目不是可执行首次嵌入的初始态，已阻止继续安装。\n"
            "当前协议只允许在纯净 Trellis 初始基线上执行首次嵌入；"
            "一旦出现当前 workflow 的历史嵌入痕迹（无论成功、失败、残缺或状态不明），"
            "都必须由用户手动处理后，再从初始态重新执行完整嵌入。\n"
            f"检测到的 workflow 痕迹:\n{trace_lines}{N}"
        )

    print()
    print("╔══════════════════════════════════════════╗")
    print("║   自定义工作流 → Trellis 嵌入安装（多CLI） ║")
    print("╚══════════════════════════════════════════╝")
    print()
    info(f"检测到 CLI: {', '.join(cli_types)}")
    if not args.cli:
        info("默认策略: 在同一目标项目中同时部署全部检测到的 CLI 适配层；如需过滤请使用 --cli")
    info(f"Profile: {args.profile}")
    if args.dry_run:
        warn("DRY RUN 模式 — 不实际写入文件")
    print()

    profile = args.profile
    attempt_record_created = False
    if not args.dry_run:
        write_embed_attempt_record(src, root, cli_types)
        attempt_record_created = True

    # 汇总结果
    total = {"claude": None, "opencode": None, "codex": None}

    try:
        # 部署到每个 CLI
        for cli_type in cli_types:
            update_embed_attempt_record(root, last_step=f"deploy-{cli_type}")
            if cli_type == "claude":
                total["claude"] = deploy_claude(src, root, args.dry_run, profile=profile)
                _migrate_legacy_agents(root, "claude", "Claude", dry_run=args.dry_run)
            elif cli_type == "opencode":
                total["opencode"] = deploy_opencode(src, root, args.dry_run, profile=profile)
                _migrate_legacy_agents(root, "opencode", "OpenCode", dry_run=args.dry_run)
            elif cli_type == "codex":
                total["codex"] = deploy_codex(src, root, args.dry_run, profile=profile)
                _migrate_legacy_agents(root, "codex", "Codex", dry_run=args.dry_run)
            print()

        if any(result and result["errors"] for result in total.values()):
            if attempt_record_created:
                fail_embed_attempt(
                    root,
                    last_step="deploy-cli-assets",
                    error="one or more CLI deployments reported errors",
                )
            print("╔══════════════════════════════════════════╗")
            print("║   ❌ 安装失败                           ║")
            print("╚══════════════════════════════════════════╝")
            print()
            for cli_type, result in total.items():
                if result is None:
                    continue
                if result["errors"]:
                    for e in result["errors"]:
                        err(f"[{cli_type}] {e}")
            print()
            return 1

        # 辅助脚本（共享）
        if not any(t and t["errors"] for t in total.values()):
            update_embed_attempt_record(root, last_step="deploy-helper-scripts")
            script_count, script_total = deploy_helper_scripts(src, root, args.dry_run, profile=profile)
            info(f"辅助脚本: {script_count}/{script_total} 个")

            # 执行卡文档
            update_embed_attempt_record(root, last_step="deploy-execution-cards")
            print()
            print("📄 执行卡文档...")
            card_count = deploy_execution_cards(src, root, args.dry_run, profile=profile)
            info(f"执行卡: {card_count} 个")

            update_embed_attempt_record(root, last_step="patch-workflow-doc")
            inject_workflow_patch(src, root, dry_run=args.dry_run, profile=profile)

            # Strong-gate Phase Index, no_task breadcrumb, and stage breadcrumb patches
            update_embed_attempt_record(root, last_step="patch-workflow-phase-index")
            inject_workflow_phase_index_patch(src, root, dry_run=args.dry_run, profile=profile)
            inject_workflow_no_task_patch(src, root, dry_run=args.dry_run, profile=profile)
            inject_workflow_breadcrumb_patch(src, root, dry_run=args.dry_run, profile=profile)

            # Issue 2: cleanup legacy three-phase breadcrumb blocks after strong-gate patches
            cleanup_legacy_phase_router_sections(root, dry_run=args.dry_run)
            cleanup_legacy_breadcrumb_blocks(root, dry_run=args.dry_run)

            # Issue 6: cleanup stale workflow-state-contract.md references
            cleanup_stale_contract_references(root, dry_run=args.dry_run)

            # Issue 1+7: patch deployed inject-workflow-state.py hook
            patch_inject_workflow_state_hook(root, dry_run=args.dry_run)
            patch_task_start_degraded_fallback(root, dry_run=args.dry_run)
            patch_opencode_session_utils(root, dry_run=args.dry_run)

            # C2: patch session-start no-task guidance to reference NL routing table
            patch_session_start_no_task_guidance(root, dry_run=args.dry_run)

            # Patch workflow_phase.py with strong-gate rejection
            _apply_patch_workflow_phase(src, root, dry_run=args.dry_run)
        print()

        if not any(t and t["errors"] for t in total.values()):
            print("📚 初始 spec 基线...")
            update_embed_attempt_record(root, last_step="import-initial-pack")
            if not import_requirements_foundation(root, args.dry_run):
                if attempt_record_created:
                    fail_embed_attempt(
                        root,
                        last_step="import-initial-pack",
                        error=f"failed to import {_REQUIREMENTS_FOUNDATION_PACK}",
                    )
                return 1
            print()
            print("🧹 Trellis bootstrap 清理...")
            update_embed_attempt_record(root, last_step="remove-bootstrap-task")
            bootstrap_cleanup = remove_bootstrap_task(root, args.dry_run)
        else:
            bootstrap_cleanup = "skipped"
            print()

        # 安装记录
        update_embed_attempt_record(root, last_step="write-install-record")
        write_install_record(root, cli_types, args.dry_run, profile=profile, bootstrap_cleanup=bootstrap_cleanup)

        # NL 路由表注入 AGENTS.md（为无 hooks 的 CLI 提供路由支持）
        print()
        print("📋 NL 路由表...")
        update_embed_attempt_record(root, last_step="inject-agents-routing")
        deploy_agents_md_routing(root, args.dry_run)

        # todo.txt
        if not args.dry_run:
            print()
            print("📝 项目级协作提醒...")
            update_embed_attempt_record(root, last_step="ensure-todo")
            ensure_project_todo(root)

        print()
        print("🧪 装后自检...")
        update_embed_attempt_record(root, last_step="post-install-check")
        if not run_post_install_check(src, root, cli_types, args.dry_run):
            if attempt_record_created:
                fail_embed_attempt(
                    root,
                    last_step="post-install-check",
                    error="upgrade-compat.py --check did not pass after installation",
                )
            return 1

        if not args.dry_run:
            clear_embed_attempt_record(root)
            attempt_record_created = False
    except Exception as exc:
        if attempt_record_created:
            fail_embed_attempt(root, last_step="unexpected-exception", error=str(exc))
        raise

    # 汇总
    print()
    print("╔══════════════════════════════════════════╗")
    if args.dry_run:
        print("║   ✅ DRY RUN 完成（预览）               ║")
    else:
        print("║   ✅ 安装完成                           ║")
    print("╚══════════════════════════════════════════╝")
    print()

    if not args.dry_run:
        info("后续 design 阶段请记得补齐项目根 README.md 与 README.en.md（块 C 英文补充版属于正式产物）")

    for cli_type, result in total.items():
        if result is None:
            continue
        if result["errors"]:
            for e in result["errors"]:
                err(f"[{cli_type}] {e}")
        else:
            summary = (
                f"[{cli_type}] 命令: {result['commands']}/{len(DISTRIBUTED_COMMANDS)}, "
                f"补丁: {result['patches']}, Agents: {result['agents']}, 脚本: {result['scripts']}"
            )
            if "manual_checks" in result:
                summary += f", 手动基线校验: {result['manual_checks']}"
            ok(summary)

    print()
    if not args.dry_run:
        print("  下一步（推荐）:")
        if bootstrap_cleanup == "removed":
            print(
                f"    1. 安装器已自动导入 {_REQUIREMENTS_FOUNDATION_PACK}，并清理 {_BOOTSTRAP_TASK_NAME}"
                "；若 `.current-task` 曾指向该 bootstrap task，也已同步清理"
            )
        elif bootstrap_cleanup == "absent":
            print(f"    1. 安装器已自动导入 {_REQUIREMENTS_FOUNDATION_PACK}；目标项目未创建 {_BOOTSTRAP_TASK_NAME}，清理已跳过")
        else:
            print(f"    1. 安装器已自动导入 {_REQUIREMENTS_FOUNDATION_PACK}；{_BOOTSTRAP_TASK_NAME} 清理状态: {bootstrap_cleanup}")
        print("       请先确认 trellis-library assemble 的导入结果已记录到 .trellis/library-lock.yaml")
        print("    2. 若目标项目不是当前最新 Trellis 基线，先升级 Trellis；当前 workflow 的 archive 收尾仍直接复用基线 task.py 行为")
        print("    3. 技术架构确认后，再使用 trellis-library/cli.py assemble 为当前项目补充真实 spec 集合")
        print("    4. 在目标项目根 README.md 中说明 todo.txt 的存在与用途")
        print("    5. 当前 workflow 默认启用源码水印与归属证明门禁（`ownership_proof_required` 常规默认值为 `yes`）；交付前使用 .trellis/scripts/workflow/ownership-proof-validate.py 做阶段校验，并在后续改动触碰受保护水印片段时使用 .trellis/scripts/workflow/source-watermark-guard.py 做保持/修复检查")
        print("    6. 同一目标项目中各 CLI 的入口协议不同，请分别按各自原生入口使用")
        for cli_type in cli_types:
            if cli_type == "claude":
                print("       - Claude Code → /trellis:continue（legacy /trellis:start 仅兼容旧目标项目）")
            elif cli_type == "opencode":
                print("       - OpenCode → /trellis:continue（TUI）或 trellis/continue（CLI）；legacy start 仅兼容旧目标项目")
            elif cli_type == "codex":
                print("       - Codex → 描述需求或显式触发对应 skill；不要期待项目级 /trellis:continue")
        print(f"  卸载: python3 {src}/uninstall-workflow.py")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
