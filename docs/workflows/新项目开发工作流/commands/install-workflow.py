#!/usr/bin/env python3
"""一键将自定义工作流嵌入 Trellis 框架（多 CLI 支持）。

默认行为：自动检测目标项目中已存在的 Claude Code / OpenCode / Codex 配置，
并在同一个项目中同时部署对应适配层；`--cli` 仅用于过滤本次安装目标。

前提:
- 目标项目已执行 trellis init，且存在对应 CLI 目录
- Codex 至少存在 .agents/skills/ 或 .codex/skills/ 之一

用法: python3 install-workflow.py [--project-root /path/to/project] [--cli claude,opencode,codex] [--dry-run]
卸载: python3 uninstall-workflow.py
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── ANSI ──
G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")
def err(m): print(f"{R}❌ {m}{N}")
def info(m): print(f"{C}ℹ️  {m}{N}")


# ── 常量 ──
_CLI_DIRS = {
    "claude": ".claude",
    "opencode": ".opencode",
    "codex": ".codex",
}
# Codex 也接受 .agents/ 作为 skills 目录
_CLI_ALT_DIRS = {
    "codex": ".agents",
}
_ALL_CLI_TYPES = ["claude", "opencode", "codex"]

NEW_COMMANDS = [
    "feasibility", "brainstorm", "design", "plan",
    "test-first", "self-review", "check", "delivery",
]
HELPER_SCRIPTS = [
    "feasibility-check.py", "design-export.py",
    "plan-validate.py", "self-review-check.py",
    "delivery-control-validate.py",
    "metadata-autocommit-guard.py",
    "record-session-helper.py",
]

# Phase Router 精确检测标记
_PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
_RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
_RECORD_SESSION_INJECTION_MARKER = "### Step 2: One-Click Add Session"
_TODO_FILE_NAME = "todo.txt"
_TODO_DEFAULT_LINE = "文档内容需要和实际当前的代码同步\n"


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


# ── 命令文件预处理 ──
def prepare_command_content(src: Path) -> str:
    """读取命令文件并替换路径引用。"""
    c = src.read_text(encoding="utf-8")
    c = c.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
    return c


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
        record_session = dst_cmds / "record-session.md"
        if start.exists() and not (backup / "start.md").exists():
            shutil.copy2(start, backup / "start.md")
            ok(f"[Claude] start.md → 备份")
        if record_session.exists() and not (backup / "record-session.md").exists():
            shutil.copy2(record_session, backup / "record-session.md")
            ok(f"[Claude] record-session.md → 备份")

    # 部署命令
    for cmd in NEW_COMMANDS:
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
                    ok("[Claude] Phase Router 已注入 start.md")
                    result["patches"] += 1
                else:
                    warn("[Claude] start.md 中未找到注入点 '## Operation Types'")
            else:
                warn("[Claude] start-patch-phase-router.md 不存在")
        else:
            ok("[Claude] Phase Router 已存在")

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
        record_session = dst_cmds / "record-session.md"
        if start.exists() and not (backup / "start.md").exists():
            shutil.copy2(start, backup / "start.md")
            ok(f"[OpenCode] start.md → 备份")
        if record_session.exists() and not (backup / "record-session.md").exists():
            shutil.copy2(record_session, backup / "record-session.md")
            ok(f"[OpenCode] record-session.md → 备份")

    # 部署命令（与 Claude Code 完全相同的文件格式）
    for cmd in NEW_COMMANDS:
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
                    ok("[OpenCode] Phase Router 已注入 start.md")
                    result["patches"] += 1
                else:
                    warn("[OpenCode] start.md 中未找到注入点 '## Operation Types'")
            else:
                warn("[OpenCode] start-patch-phase-router.md 不存在")
        else:
            ok("[OpenCode] Phase Router 已存在")

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
    # 优先使用 .agents/skills/，其次 .codex/skills/
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.is_dir():
        skills_dir = root / ".codex" / "skills"
    if not skills_dir.is_dir():
        return {"commands": 0, "scripts": 0, "patches": 0, "errors": ["未找到 .agents/skills/ 或 .codex/skills/ 目录"]}

    result = {"commands": 0, "scripts": 0, "patches": 0, "errors": []}

    # 部署 skills（从命令文件转换为 skills 格式）
    for cmd in NEW_COMMANDS:
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
            "commands": NEW_COMMANDS,
            "scripts": HELPER_SCRIPTS,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"安装记录 → {rec.name} (Trellis {ver}, CLI: {', '.join(cli_types)})")


# ── todo.txt ──
def ensure_project_todo(root: Path) -> None:
    todo_path = root / _TODO_FILE_NAME
    if todo_path.exists():
        warn(f"{_TODO_FILE_NAME} 已存在，保留现有内容")
        return
    todo_path.write_text(_TODO_DEFAULT_LINE, encoding="utf-8")
    ok(f"初始化提醒 → {_TODO_FILE_NAME}")


# ── 主流程 ──
def main():
    p = argparse.ArgumentParser(
        description="安装自定义工作流到 Trellis（默认同一项目同时部署已检测到的 Claude Code / OpenCode / Codex 适配层）"
    )
    p.add_argument("--project-root", type=Path, default=None, help="项目根目录（默认自动检测）")
    p.add_argument("--cli", type=str, default=None,
                   help="指定 CLI 类型，逗号分隔: claude,opencode,codex（默认安装全部检测到的 CLI；此参数仅用于过滤）")
    p.add_argument("--dry-run", action="store_true", help="预览安装结果，不实际写入")
    args = p.parse_args()

    src = Path(__file__).resolve().parent
    root = args.project_root or find_root(Path(__file__))

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

    # 安装记录
    write_install_record(root, cli_types, args.dry_run)

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
            ok(f"[{cli_type}] 命令: {result['commands']}/{len(NEW_COMMANDS)}, "
               f"补丁: {result['patches']}, 脚本: {result['scripts']}")

    print()
    if not args.dry_run:
        print("  下一步（推荐）:")
        print("    1. 若目标项目已接入 trellis-library 组装流程，先补 requirements-discovery-foundation")
        print("       python3 trellis-library/cli.py assemble --target <project-root> --pack pack.requirements-discovery-foundation --dry-run")
        print("       确认 dry-run 输出无误后，去掉 --dry-run 正式执行")
        print("    2. 最低要求：补齐 problem-definition / scope-boundary / requirement-clarification / acceptance-criteria")
        print("       再补 customer-facing / developer-facing PRD spec、template、checklist")
        print("    3. 若未接入 trellis-library CLI，则手动复制最低资产集到目标项目 .trellis/")
        print("    4. 在目标项目根 README.md 中说明 todo.txt 的存在与用途")
        print("    5. 同一目标项目中各 CLI 的入口协议不同，请分别按各自原生入口使用")
        for cli_type in cli_types:
            if cli_type == "claude":
                print("       - Claude Code → /trellis:start")
            elif cli_type == "opencode":
                print("       - OpenCode → /trellis:start（TUI）或 trellis/start（CLI）")
            elif cli_type == "codex":
                print("       - Codex → 描述需求或显式触发对应 skill；不要期待项目级 /trellis:start")
        print(f"  卸载: python3 {src}/uninstall-workflow.py")
    print()


if __name__ == "__main__":
    main()
