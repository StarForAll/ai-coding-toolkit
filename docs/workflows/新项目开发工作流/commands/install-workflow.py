#!/usr/bin/env python3
"""在 trellis init 之后将当前自定义工作流安装到目标项目（多 CLI 支持）。

默认行为：自动检测目标项目中已存在的 Claude Code / OpenCode / Codex 配置，
并在同一个项目中同时部署对应适配层；`--cli` 仅用于过滤本次安装目标。

重要边界：
- 目标项目必须是 Git 仓库，`origin` 至少有两个 push URL，且已经执行过 `trellis init`
- 当前 workflow 是“嵌入 + 增强”模型，不会重建 Trellis 原生命令全集
- `feasibility` 到 `delivery` 这类阶段资产由当前 workflow 分发
- `start` / `finish-work` / `record-session` 默认来自 Trellis 基线，允许由当前 workflow 追加补丁增强
- 安装器会自动导入 `pack.requirements-discovery-foundation`，并删除 `00-bootstrap-guidelines`

前提:
- 目标项目是 Git 仓库，`origin` 至少有两个 push URL，已执行 trellis init，且存在对应 CLI 目录
- Codex 至少存在 .agents/skills/ 或 .codex/skills/ 之一

用法: python3 install-workflow.py [--project-root /path/to/project] [--cli claude,opencode,codex] [--dry-run]
卸载: python3 uninstall-workflow.py
"""
import argparse
import json
import subprocess
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from workflow_assets import (
    ADDED_COMMANDS,
    ALL_CLI_TYPES,
    CLI_ALT_DIRS,
    CLI_DIRS,
    DISTRIBUTED_COMMANDS,
    HELPER_SCRIPTS,
    OVERLAY_BASELINE_COMMANDS,
    resolve_codex_skills_dir,
)


# ── ANSI ──
G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")
def err(m): print(f"{R}❌ {m}{N}")
def info(m): print(f"{C}ℹ️  {m}{N}")


# ── 常量 ──
_CLI_DIRS = CLI_DIRS
_CLI_ALT_DIRS = CLI_ALT_DIRS
_ALL_CLI_TYPES = ALL_CLI_TYPES

# 对 Trellis 原生命令做增强时使用的补丁标记。
# 当前 workflow 会增强 `start.md`、`finish-work.md` 与 `record-session.md`，
# 而不是重写它们的全部基线内容。
_PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
_FINISH_WORK_MARKER = "<!-- finish-work-projectization-patch -->"
_FINISH_WORK_START_HEADING = "### 1. Code Quality"
_FINISH_WORK_END_HEADING = "### 1.5. Test Coverage"
_RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
_RECORD_SESSION_INJECTION_MARKER = "### Step 2: One-Click Add Session"
_TODO_FILE_NAME = "todo.txt"
_TODO_DEFAULT_LINE = "文档内容需要和实际当前的代码同步\n"
_REQUIREMENTS_FOUNDATION_PACK = "pack.requirements-discovery-foundation"
_BOOTSTRAP_TASK_NAME = "00-bootstrap-guidelines"
_ORIGIN_REMOTE_NAME = "origin"
_MIN_ORIGIN_PUSH_URLS = 2

# AGENTS.md NL 路由表标记
_AGENTS_NL_ROUTING_MARKER = "<!-- workflow-nl-routing-start -->"
_AGENTS_NL_ROUTING_END = "<!-- workflow-nl-routing-end -->"

_NL_ROUTING_SECTION = """\
<!-- workflow-nl-routing-start -->

## 自然语言命令路由

> 由工作流安装器自动生成。当用户用自然语言描述意图时，本表提供阶段入口候选映射与推荐口径。
>
> 入口约束：
> - Claude Code / OpenCode：优先使用项目级 `/trellis:xxx` 命令；OpenCode CLI 可使用 `trellis/xxx`
> - Codex：通过 `AGENTS.md` 自然语言路由或显式触发对应 skill；不要期待项目级 `/trellis:xxx` 命令目录
> - 本表用于缩小候选范围，不表示所有 CLI 都存在确定性的自动命令路由；若命中歧义、缺少前置条件或上下文不足，仍应先确认再进入对应阶段

### 工作流阶段命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 评估、能做吗、报价、新项目、风险、可行性、看看这个项目、能不能接、估个价、接私活、外包项目、客户需求 | `/trellis:feasibility` | 描述可行性评估意图，或显式触发 `feasibility` skill | §1 可行性评估 |
| 需求、PRD、明确需求、需求文档、需求分析、梳理需求、讨论方案、判断要不要拆任务 | `/trellis:brainstorm` | 描述需求澄清意图，或显式触发 `brainstorm` skill | §2 需求发现 |
| 设计、架构、架构设计、选型、接口设计、技术方案、开始设计、画架构图、设计方案 | `/trellis:design` | 描述设计阶段意图，或显式触发 `design` skill | §3 设计阶段 |
| 拆任务、排期、计划、任务分解、做计划、工作分解、里程碑、工作计划 | `/trellis:plan` | 描述任务拆解意图，或显式触发 `plan` skill | §4 任务拆解 |
| 写测试、TDD、测试驱动、先写测试、测试用例、验收测试 | `/trellis:test-first` | 描述测试先行意图，或显式触发 `test-first` skill | §4.3 测试先行 |
| 检查一下、质量检查、对照 spec、对照规范、自检、有没有偏差 | `/trellis:check` | 描述质量检查意图，或显式触发 `check` skill | §5.1.x 质量检查 |
| 补充审查、多 CLI 审查、多人审查、让其他 CLI 看一下、review-gate、审查门禁 | `/trellis:review-gate` | 描述补充审查意图，或显式触发 `review-gate` skill | §5.1.y 补充审查 |
| 提交前检查、准备提交、commit 前、收尾 | `/trellis:finish-work` | 描述提交前检查意图，或显式触发 `finish-work` skill | §6 提交检查 |
| 交付、部署、上线、发布、准备交付、跑验收、整理交付物、项目收尾 | `/trellis:delivery` | 描述交付收尾意图，或显式触发 `delivery` skill | §6+§7 测试交付 |
| 记录、保存进度、收工 | `/trellis:record-session` | 描述会话收尾意图，或显式触发 `record-session` skill | §7 会话记录 |

### 框架通用命令

| 触发关键词 | Claude / OpenCode 入口 | Codex 入口 | 说明 |
|-----------|------------------------|------------|------|
| 开始、新会话、继续、下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | Phase Router 自动检测 |
| 卡住了、反复出错、死循环 | `/trellis:break-loop` | 描述排障意图，或显式触发 `break-loop` skill | 深度 bug 分析 |
| 并行、worktree、同时开发 | `/trellis:parallel` | 描述并行开发意图，或显式触发 `parallel` skill | 并行任务管理 |
| 更新规范、沉淀经验 | `/trellis:update-spec` | 描述规范更新意图，或显式触发 `update-spec` skill | 规范更新 |
| 跨层检查、跨模块影响 | `/trellis:check-cross-layer` | 描述跨层检查意图，或显式触发 `check-cross-layer` skill | 跨层检查 |
| 集成 skill、添加 skill | `/trellis:integrate-skill` | 描述 skill 集成意图，或显式触发 `integrate-skill` skill | Skill 集成 |
| 读规范、开发前准备 | `/trellis:before-dev` | 描述开发前准备意图，或显式触发 `before-dev` skill | 开发前读规范 |
| 新人入门、项目介绍 | `/trellis:onboard` | 描述 onboarding 意图，或显式触发 `onboard` skill | 项目 onboarding |
| 创建命令、新命令 | `/trellis:create-command` | 描述创建命令意图，或显式触发 `create-command` skill | 创建新命令 |

### 歧义消解

- 多个命令匹配时：当前阶段上下文 > 精确关键词 > 阶段顺序推断 > 模糊语义
- 无法确定时：路由到 `/trellis:start`（Phase Router 自动检测）
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
    found = []
    for cli_type, cli_dir in _CLI_DIRS.items():
        if requested and cli_type not in requested:
            continue
        if (root / cli_dir).is_dir():
            found.append(cli_type)
        elif cli_type in _CLI_ALT_DIRS and (root / _CLI_ALT_DIRS[cli_type]).is_dir():
            # Codex 可用 .agents/ 替代 .codex/
            found.append(cli_type)
    if not found:
        dirs_str = "、".join(f"{d}/" for d in _CLI_DIRS.values())
        sys.exit(f"{R}未找到任何 CLI 目录（{dirs_str}），请先初始化目标 CLI{N}")
    return found


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
            "请先为同一个 origin 配置多个 push 远端，例如：\n"
            "git remote set-url --add --push origin git@github.com:xxx/yyy.git\n"
            f"git remote set-url --add --push origin git@gitee.com:xxx/yyy.git{N}"
        )


# ── 命令文件预处理 ──
def prepare_command_content(src: Path) -> str:
    """读取命令文件并替换路径引用。"""
    c = src.read_text(encoding="utf-8")
    c = c.replace("<WORKFLOW_DIR>/commands/shell/", ".trellis/scripts/workflow/")
    return c


def build_finish_work_content(content: str, patch_text: str) -> str | None:
    """将 finish-work 的默认 Code Quality 区块替换为项目化补丁。"""
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


# ── Claude Code 部署 ──
def deploy_claude(src: Path, root: Path, dry_run: bool) -> dict:
    """部署到 .claude/commands/trellis/"""
    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"
    result = {"commands": 0, "scripts": 0, "patches": 0, "errors": []}

    if not dst_cmds.is_dir():
        result["errors"].append(".claude/commands/trellis/ 不存在，请先运行: trellis init")
        return result

    # 备份
    if not dry_run:
        backup.mkdir(parents=True, exist_ok=True)
        start = dst_cmds / "start.md"
        finish_work = dst_cmds / "finish-work.md"
        record_session = dst_cmds / "record-session.md"
        baseline_overlaps = [dst_cmds / f"{name}.md" for name in OVERLAY_BASELINE_COMMANDS]
        if start.exists() and not (backup / "start.md").exists():
            shutil.copy2(start, backup / "start.md")
            ok(f"[Claude] start.md → 备份")
        if finish_work.exists() and not (backup / "finish-work.md").exists():
            shutil.copy2(finish_work, backup / "finish-work.md")
            ok(f"[Claude] finish-work.md → 备份")
        if record_session.exists() and not (backup / "record-session.md").exists():
            shutil.copy2(record_session, backup / "record-session.md")
            ok(f"[Claude] record-session.md → 备份")
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
                c = prepare_command_content(s)
                d.write_text(c, encoding="utf-8")
                ok(f"[Claude] /trellis:{cmd}")
            result["commands"] += 1
        else:
            warn(f"[Claude] 源文件缺失: {cmd}.md")

    # 注入 Phase Router
    start = dst_cmds / "start.md"
    if start.exists():
        content = start.read_text(encoding="utf-8")
        if _PHASE_ROUTER_MARKER not in content:
            patch = src / "start-patch-phase-router.md"
            if patch.exists():
                marker = "## Operation Types"
                if marker in content:
                    before, after = content.split(marker, 1)
                    if not dry_run:
                        start.write_text(
                            before + patch.read_text(encoding="utf-8") + "\n" + marker + after,
                            encoding="utf-8",
                        )
                    if dry_run:
                        info("[Claude] 将注入 Phase Router 到 start.md")
                    else:
                        ok("[Claude] Phase Router 已注入 start.md")
                    result["patches"] += 1
                else:
                    warn("[Claude] start.md 中未找到注入点 '## Operation Types'")
            else:
                warn("[Claude] start-patch-phase-router.md 不存在")
        else:
            ok("[Claude] Phase Router 已存在")

    finish_work = dst_cmds / "finish-work.md"
    if inject_finish_work_patch(
        src,
        finish_work,
        dry_run=dry_run,
        cli_label="Claude",
        target_label="finish-work.md",
    ):
        result["patches"] += 1

    # 注入元数据闭环
    record_session = dst_cmds / "record-session.md"
    if record_session.exists():
        content = record_session.read_text(encoding="utf-8")
        if _RECORD_SESSION_MARKER not in content:
            patch = src / "record-session-patch-metadata-closure.md"
            if patch.exists() and _RECORD_SESSION_INJECTION_MARKER in content:
                if not dry_run:
                    before, after = content.split(_RECORD_SESSION_INJECTION_MARKER, 1)
                    record_session.write_text(
                        before + patch.read_text(encoding="utf-8") + "\n" + _RECORD_SESSION_INJECTION_MARKER + after,
                        encoding="utf-8",
                    )
                if dry_run:
                    info("[Claude] 将注入 record-session 元数据闭环")
                else:
                    ok("[Claude] record-session 元数据闭环已注入")
                result["patches"] += 1
            elif not patch.exists():
                warn("[Claude] record-session-patch-metadata-closure.md 不存在")
            else:
                warn("[Claude] record-session.md 中未找到注入点")
        else:
            ok("[Claude] record-session 元数据闭环已存在")
    else:
        warn("[Claude] record-session.md 不存在，跳过元数据闭环注入")

    # 部署辅助脚本（共享）
    dst_scripts.mkdir(parents=True, exist_ok=True)
    for f in HELPER_SCRIPTS:
        s = src / "shell" / f
        d = dst_scripts / f
        if s.exists():
            if not dry_run:
                shutil.copy2(s, d)
                d.chmod(0o755)
            result["scripts"] += 1

    return result


# ── OpenCode 部署 ──
def deploy_opencode(src: Path, root: Path, dry_run: bool) -> dict:
    """部署到 .opencode/commands/trellis/（命令文件格式与 Claude Code 完全兼容）"""
    dst_cmds = root / ".opencode" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"
    result = {"commands": 0, "scripts": 0, "patches": 0, "errors": []}

    if not dst_cmds.is_dir():
        result["errors"].append(".opencode/commands/trellis/ 不存在，请先初始化 OpenCode")
        return result

    # 备份
    if not dry_run:
        backup.mkdir(parents=True, exist_ok=True)
        start = dst_cmds / "start.md"
        finish_work = dst_cmds / "finish-work.md"
        record_session = dst_cmds / "record-session.md"
        baseline_overlaps = [dst_cmds / f"{name}.md" for name in OVERLAY_BASELINE_COMMANDS]
        if start.exists() and not (backup / "start.md").exists():
            shutil.copy2(start, backup / "start.md")
            ok(f"[OpenCode] start.md → 备份")
        if finish_work.exists() and not (backup / "finish-work.md").exists():
            shutil.copy2(finish_work, backup / "finish-work.md")
            ok(f"[OpenCode] finish-work.md → 备份")
        if record_session.exists() and not (backup / "record-session.md").exists():
            shutil.copy2(record_session, backup / "record-session.md")
            ok(f"[OpenCode] record-session.md → 备份")
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
                c = prepare_command_content(s)
                d.write_text(c, encoding="utf-8")
                ok(f"[OpenCode] {cmd}（TUI: /trellis:{cmd} / CLI: trellis/{cmd}）")
            result["commands"] += 1
        else:
            warn(f"[OpenCode] 源文件缺失: {cmd}.md")

    # 注入 Phase Router
    start = dst_cmds / "start.md"
    if start.exists():
        content = start.read_text(encoding="utf-8")
        if _PHASE_ROUTER_MARKER not in content:
            patch = src / "start-patch-phase-router.md"
            if patch.exists():
                marker = "## Operation Types"
                if marker in content:
                    before, after = content.split(marker, 1)
                    if not dry_run:
                        start.write_text(
                            before + patch.read_text(encoding="utf-8") + "\n" + marker + after,
                            encoding="utf-8",
                        )
                    if dry_run:
                        info("[OpenCode] 将注入 Phase Router 到 start.md")
                    else:
                        ok("[OpenCode] Phase Router 已注入 start.md")
                    result["patches"] += 1
                else:
                    warn("[OpenCode] start.md 中未找到注入点 '## Operation Types'")
            else:
                warn("[OpenCode] start-patch-phase-router.md 不存在")
        else:
            ok("[OpenCode] Phase Router 已存在")

    finish_work = dst_cmds / "finish-work.md"
    if inject_finish_work_patch(
        src,
        finish_work,
        dry_run=dry_run,
        cli_label="OpenCode",
        target_label="finish-work.md",
    ):
        result["patches"] += 1

    # 注入元数据闭环
    record_session = dst_cmds / "record-session.md"
    if record_session.exists():
        content = record_session.read_text(encoding="utf-8")
        if _RECORD_SESSION_MARKER not in content:
            patch = src / "record-session-patch-metadata-closure.md"
            if patch.exists() and _RECORD_SESSION_INJECTION_MARKER in content:
                if not dry_run:
                    before, after = content.split(_RECORD_SESSION_INJECTION_MARKER, 1)
                    record_session.write_text(
                        before + patch.read_text(encoding="utf-8") + "\n" + _RECORD_SESSION_INJECTION_MARKER + after,
                        encoding="utf-8",
                    )
                if dry_run:
                    info("[OpenCode] 将注入 record-session 元数据闭环")
                else:
                    ok("[OpenCode] record-session 元数据闭环已注入")
                result["patches"] += 1
            elif not patch.exists():
                warn("[OpenCode] record-session-patch-metadata-closure.md 不存在")
            else:
                warn("[OpenCode] record-session.md 中未找到注入点")
        else:
            ok("[OpenCode] record-session 元数据闭环已存在")
    else:
        warn("[OpenCode] record-session.md 不存在，跳过元数据闭环注入")

    # 辅助脚本已在 Claude Code 部署时处理，此处不重复计数
    return result


# ── Codex CLI 部署 ──
def deploy_codex(src: Path, root: Path, dry_run: bool) -> dict:
    """部署到 skills 目录（Codex 无项目自定义命令目录，workflow 入口采用 skills 模型）。"""
    skills_dir = resolve_codex_skills_dir(root)
    if skills_dir is None:
        return {"commands": 0, "scripts": 0, "patches": 0, "errors": ["未找到 .agents/skills/ 或 .codex/skills/ 目录"]}

    result = {"commands": 0, "scripts": 0, "patches": 0, "errors": []}

    if not dry_run:
        for name in [*OVERLAY_BASELINE_COMMANDS, "finish-work"]:
            skill_path = skills_dir / name / "SKILL.md"
            backup_path = skills_dir / ".backup-original" / name / "SKILL.md"
            if skill_path.exists() and not backup_path.exists():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_path, backup_path)
                ok(f"[Codex] {name} skill → 备份")

    # 部署 skills（从命令文件转换为 skills 格式）
    for cmd in DISTRIBUTED_COMMANDS:
        s = src / f"{cmd}.md"
        d = skills_dir / cmd / "SKILL.md"
        if s.exists():
            if dry_run:
                info(f"[Codex] 将部署 skill: {cmd}")
            else:
                c = prepare_command_content(s)
                d.parent.mkdir(parents=True, exist_ok=True)
                d.write_text(c, encoding="utf-8")
                ok(f"[Codex] skill: {cmd} → {d.relative_to(root)}")
            result["commands"] += 1
        else:
            warn(f"[Codex] 源文件缺失: {cmd}.md")

    finish_work_skill = skills_dir / "finish-work" / "SKILL.md"
    if inject_finish_work_patch(
        src,
        finish_work_skill,
        dry_run=dry_run,
        cli_label="Codex",
        target_label="finish-work skill",
    ):
        result["patches"] += 1

    # Codex 通过 session-start.py hook 注入上下文，不需要注入 start.md
    # 验证 hook 是否已就绪
    hooks_json = root / ".codex" / "hooks.json"
    if hooks_json.exists():
        ok("[Codex] hooks.json 已存在")
        result["patches"] += 1
    else:
        warn("[Codex] hooks.json 不存在，SessionStart hook 未配置")

    session_start = root / ".codex" / "hooks" / "session-start.py"
    if session_start.exists():
        ok("[Codex] session-start.py hook 已存在")
    else:
        warn("[Codex] session-start.py 不存在，会话上下文注入不可用")

    # 辅助脚本已在 Claude Code 部署时处理
    return result


# ── 辅助脚本部署（共享） ──
def deploy_helper_scripts(src: Path, root: Path, dry_run: bool) -> int:
    """部署平台无关的辅助脚本到 .trellis/scripts/workflow/"""
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    count = 0
    dst_scripts.mkdir(parents=True, exist_ok=True)
    for f in HELPER_SCRIPTS:
        s = src / "shell" / f
        d = dst_scripts / f
        if s.exists():
            if not dry_run:
                shutil.copy2(s, d)
                d.chmod(0o755)
            count += 1
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


# ── 安装记录 ──
def write_install_record(root: Path, cli_types: list[str], dry_run: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    ver = (root / ".trellis" / ".version").read_text(encoding="utf-8").strip() \
        if (root / ".trellis" / ".version").exists() else "unknown"
    rec = root / ".trellis" / "workflow-installed.json"
    if not dry_run:
        rec.write_text(json.dumps({
            "trellis_version": ver,
            "installed": now,
            "cli_types": cli_types,
            "commands": DISTRIBUTED_COMMANDS,
            "overlay_commands": OVERLAY_BASELINE_COMMANDS,
            "added_commands": ADDED_COMMANDS,
            "scripts": HELPER_SCRIPTS,
            "initial_pack": _REQUIREMENTS_FOUNDATION_PACK,
            "bootstrap_task_removed": True,
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


def remove_bootstrap_task(root: Path, dry_run: bool) -> None:
    """安装 workflow 后删除 Trellis init 创建的 bootstrap task。"""
    task_dir = root / ".trellis" / "tasks" / _BOOTSTRAP_TASK_NAME
    if not task_dir.exists():
        info(f"{_BOOTSTRAP_TASK_NAME} 不存在，跳过清理")
        return
    if dry_run:
        info(f"将删除 Trellis bootstrap 任务 → .trellis/tasks/{_BOOTSTRAP_TASK_NAME}")
        return
    if task_dir.is_dir():
        shutil.rmtree(task_dir)
    else:
        task_dir.unlink()
    ok(f"Trellis bootstrap 任务已删除 → {_BOOTSTRAP_TASK_NAME}")


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
    p.add_argument("--dry-run", action="store_true", help="预览安装结果，不实际写入")
    args = p.parse_args()

    src = Path(__file__).resolve().parent
    root = args.project_root or find_root(Path(__file__))
    ensure_project_prereqs(root)

    # 检测 CLI 类型
    requested = [x.strip() for x in args.cli.split(",")] if args.cli else None
    if requested:
        for r in requested:
            if r not in _ALL_CLI_TYPES:
                sys.exit(f"{R}未知 CLI 类型: {r}（支持: {', '.join(_ALL_CLI_TYPES)}）{N}")
    cli_types = detect_cli_types(root, requested)

    print()
    print("╔══════════════════════════════════════════╗")
    print("║   自定义工作流 → Trellis 嵌入安装（多CLI） ║")
    print("╚══════════════════════════════════════════╝")
    print()
    info(f"检测到 CLI: {', '.join(cli_types)}")
    if not args.cli:
        info("默认策略: 在同一目标项目中同时部署全部检测到的 CLI 适配层；如需过滤请使用 --cli")
    if args.dry_run:
        warn("DRY RUN 模式 — 不实际写入文件")
    print()

    # 汇总结果
    total = {"claude": None, "opencode": None, "codex": None}

    # 部署到每个 CLI
    for cli_type in cli_types:
        if cli_type == "claude":
            total["claude"] = deploy_claude(src, root, args.dry_run)
        elif cli_type == "opencode":
            total["opencode"] = deploy_opencode(src, root, args.dry_run)
        elif cli_type == "codex":
            total["codex"] = deploy_codex(src, root, args.dry_run)
        print()

    # 辅助脚本（共享）
    if not any(t and t["errors"] for t in total.values()):
        script_count = deploy_helper_scripts(src, root, args.dry_run)
        info(f"辅助脚本: {script_count}/{len(HELPER_SCRIPTS)} 个")
    print()

    if not any(t and t["errors"] for t in total.values()):
        print("📚 初始 spec 基线...")
        if not import_requirements_foundation(root, args.dry_run):
            return 1
        print()
        print("🧹 Trellis bootstrap 清理...")
        remove_bootstrap_task(root, args.dry_run)
        print()

    # 安装记录
    write_install_record(root, cli_types, args.dry_run)

    # NL 路由表注入 AGENTS.md（为无 hooks 的 CLI 提供路由支持）
    print()
    print("📋 NL 路由表...")
    deploy_agents_md_routing(root, args.dry_run)

    # todo.txt
    if not args.dry_run:
        print()
        print("📝 项目级协作提醒...")
        ensure_project_todo(root)

    # 汇总
    print()
    print("╔══════════════════════════════════════════╗")
    if args.dry_run:
        print("║   ✅ DRY RUN 完成（预览）               ║")
    else:
        print("║   ✅ 安装完成                           ║")
    print("╚══════════════════════════════════════════╝")
    print()

    for cli_type, result in total.items():
        if result is None:
            continue
        if result["errors"]:
            for e in result["errors"]:
                err(f"[{cli_type}] {e}")
        else:
            ok(f"[{cli_type}] 命令: {result['commands']}/{len(DISTRIBUTED_COMMANDS)}, "
               f"补丁: {result['patches']}, 脚本: {result['scripts']}")

    print()
    if not args.dry_run:
        print("  下一步（推荐）:")
        print(f"    1. 安装器已自动导入 {_REQUIREMENTS_FOUNDATION_PACK}，并清理 {_BOOTSTRAP_TASK_NAME}")
        print("       请先确认 .trellis/library-lock.yaml 已包含需求发现基础资产")
        print("    2. 技术架构确认后，再使用 trellis-library/cli.py assemble 为当前项目补充真实 spec 集合")
        print("    3. 在目标项目根 README.md 中说明 todo.txt 的存在与用途")
        print("    4. 同一目标项目中各 CLI 的入口协议不同，请分别按各自原生入口使用")
        for cli_type in cli_types:
            if cli_type == "claude":
                print("       - Claude Code → /trellis:start")
            elif cli_type == "opencode":
                print("       - OpenCode → /trellis:start（TUI）或 trellis/start（CLI）")
            elif cli_type == "codex":
                print("       - Codex → 描述需求或显式触发对应 skill；不要期待项目级 /trellis:start")
        print(f"  卸载: python3 {src}/uninstall-workflow.py")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
