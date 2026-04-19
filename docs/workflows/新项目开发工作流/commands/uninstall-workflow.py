#!/usr/bin/env python3
"""卸载工作流，恢复 Trellis 原始状态（多 CLI 支持）。

用法: python3 uninstall-workflow.py [--project-root /path/to/project] [--cli claude,opencode,codex]
"""

import json
import shutil
import sys
from pathlib import Path

from workflow_assets import (
    AGENT_SUFFIXES,
    ALL_CLI_TYPES,
    CODEX_PATCH_BASELINE_SKILLS,
    CLI_ALT_DIRS,
    CLI_DIRS,
    detect_cli_types as detect_cli_types_shared,
    DISTRIBUTED_COMMANDS,
    MANAGED_IMPLEMENTATION_AGENTS,
    OPTIONAL_DISABLED_BASELINE_COMMANDS,
    OVERLAY_BASELINE_COMMANDS,
    resolve_codex_skills_dir,
    workflow_managed_agent_target_path,
)


G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"
DEFAULT_COMMANDS = DISTRIBUTED_COMMANDS

_CLI_DIRS = CLI_DIRS
_CLI_ALT_DIRS = CLI_ALT_DIRS
_ALL_CLI_TYPES = ALL_CLI_TYPES
_AGENTS_NL_ROUTING_MARKER = "<!-- workflow-nl-routing-start -->"
_AGENTS_NL_ROUTING_END = "<!-- workflow-nl-routing-end -->"
_TODO_FILE_NAME = "todo.txt"
_TODO_DEFAULT_LINE = "文档内容需要和实际当前的代码同步\n"


def ok(message: str) -> None:
    print(f"{G}✅ {message}{N}")


def warn(message: str) -> None:
    print(f"{Y}⚠️  {message}{N}")


def err(message: str) -> None:
    print(f"{R}❌ {message}{N}")


def info(message: str) -> None:
    print(f"{C}ℹ️  {message}{N}")


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
    sys.exit(f"{R}未找到任何 CLI 目录（{dirs_str}）{N}")


def detect_cli_types(root: Path, requested: list[str] | None = None) -> list[str]:
    """检测项目中存在的 CLI 类型，可按 requested 过滤。"""
    found = detect_cli_types_shared(root)
    if requested:
        found = [cli_type for cli_type in found if cli_type in requested]
    return found


def load_install_record(rec_file: Path) -> dict:
    if not rec_file.exists():
        return {}
    try:
        return json.loads(rec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        warn(f"workflow-installed.json 损坏，将使用默认卸载列表: {exc}")
        return {}


def split_commands(commands: list[str], overlay_commands: list[str] | None, added_commands: list[str] | None) -> tuple[list[str], list[str]]:
    if overlay_commands:
        resolved_overlay = overlay_commands
    else:
        resolved_overlay = [name for name in commands if name in OVERLAY_BASELINE_COMMANDS]
    if added_commands:
        resolved_added = added_commands
    else:
        resolved_added = [name for name in commands if name not in resolved_overlay]
    return resolved_overlay, resolved_added


def restore_backed_up_command(backup: Path, target_dir: Path, command: str, cli_label: str) -> bool:
    backup_path = backup / f"{command}.md"
    target_path = target_dir / f"{command}.md"
    if not backup_path.exists():
        warn(f"[{cli_label}] 无 {command}.md 备份，保留当前文件")
        return False
    shutil.copy2(backup_path, target_path)
    ok(f"[{cli_label}] {command}.md 已恢复")
    return True


def restore_optional_disabled_command(backup: Path, target_dir: Path, command: str, cli_label: str) -> None:
    backup_path = backup / f"{command}.md"
    target_path = target_dir / f"{command}.md"
    if not backup_path.exists():
        return
    shutil.copy2(backup_path, target_path)
    ok(f"[{cli_label}] {command}.md 已恢复")


def uninstall_managed_agents(root: Path, cli_type: str, cli_label: str) -> None:
    target_dir = root / CLI_DIRS[cli_type] / "agents"
    backup_dir = target_dir / ".backup-original"
    suffix = AGENT_SUFFIXES[cli_type]

    if not target_dir.is_dir():
        warn(f"[{cli_label}] {target_dir.relative_to(root)}/ 不存在，跳过 managed agents 卸载")
        return

    restored = 0
    for agent_name in MANAGED_IMPLEMENTATION_AGENTS:
        backup_agent = backup_dir / f"{agent_name}{suffix}"
        target_agent = workflow_managed_agent_target_path(root, cli_type, agent_name)
        if backup_agent.exists():
            shutil.copy2(backup_agent, target_agent)
            ok(f"[{cli_label}] 恢复 agent: {agent_name}")
            restored += 1
        elif target_agent.exists():
            target_agent.unlink()
            ok(f"[{cli_label}] 删除 install 新建的 agent: {agent_name}")
        else:
            warn(f"[{cli_label}] 无 {agent_name}{suffix} 备份，保留当前文件")

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
        ok(f"[{cli_label}] agent 备份目录已删除")

    info(f"[{cli_label}] 已恢复 {restored}/{len(MANAGED_IMPLEMENTATION_AGENTS)} 个 managed agents")


def uninstall_claude(root: Path, added_commands: list[str], overlay_commands: list[str]) -> None:
    """卸载 Claude Code 部署的工作流。"""
    dst_cmds = root / ".claude" / "commands" / "trellis"
    backup = dst_cmds / ".backup-original"

    if not dst_cmds.is_dir():
        warn("[Claude] .claude/commands/trellis/ 不存在，跳过")
        return

    # 删除 workflow 新增命令
    removed = 0
    for command in added_commands:
        candidate = dst_cmds / f"{command}.md"
        if candidate.exists():
            candidate.unlink()
            ok(f"[Claude] 删除 {command}.md")
            removed += 1
    info(f"[Claude] 已删除 {removed} 个新增命令")

    restored = 0
    for command in overlay_commands:
        if restore_backed_up_command(backup, dst_cmds, command, "Claude"):
            restored += 1
    if overlay_commands:
        info(f"[Claude] 已恢复 {restored}/{len(overlay_commands)} 个同名基线命令")

    for command in OPTIONAL_DISABLED_BASELINE_COMMANDS:
        restore_optional_disabled_command(backup, dst_cmds, command, "Claude")

    # 恢复 start.md
    backup_start = backup / "start.md"
    if backup_start.exists():
        shutil.copy2(backup_start, dst_cmds / "start.md")
        ok("[Claude] start.md 已恢复")
    else:
        warn("[Claude] 无 start.md 备份，未恢复")

    # 恢复 finish-work.md
    backup_finish_work = backup / "finish-work.md"
    if backup_finish_work.exists():
        shutil.copy2(backup_finish_work, dst_cmds / "finish-work.md")
        ok("[Claude] finish-work.md 已恢复")
    else:
        warn("[Claude] 无 finish-work.md 备份，未恢复")

    # 恢复 record-session.md
    backup_record_session = backup / "record-session.md"
    if backup_record_session.exists():
        shutil.copy2(backup_record_session, dst_cmds / "record-session.md")
        ok("[Claude] record-session.md 已恢复")
    else:
        warn("[Claude] 无 record-session.md 备份，未恢复")

    # 清理备份目录
    if backup.exists():
        shutil.rmtree(backup)
        ok("[Claude] 备份目录已删除")

    # 清理升级备份
    for directory in dst_cmds.iterdir():
        if directory.is_dir() and directory.name.startswith(".backup-upgrade-"):
            shutil.rmtree(directory)
            ok(f"[Claude] 升级备份已删除: {directory.name}")

    uninstall_managed_agents(root, "claude", "Claude")


def uninstall_opencode(root: Path, added_commands: list[str], overlay_commands: list[str]) -> None:
    """卸载 OpenCode 部署的工作流。"""
    dst_cmds = root / ".opencode" / "commands" / "trellis"
    backup = dst_cmds / ".backup-original"

    if not dst_cmds.is_dir():
        warn("[OpenCode] .opencode/commands/trellis/ 不存在，跳过")
        return

    # 删除 workflow 新增命令
    removed = 0
    for command in added_commands:
        candidate = dst_cmds / f"{command}.md"
        if candidate.exists():
            candidate.unlink()
            ok(f"[OpenCode] 删除 {command}.md")
            removed += 1
    info(f"[OpenCode] 已删除 {removed} 个新增命令")

    restored = 0
    for command in overlay_commands:
        if restore_backed_up_command(backup, dst_cmds, command, "OpenCode"):
            restored += 1
    if overlay_commands:
        info(f"[OpenCode] 已恢复 {restored}/{len(overlay_commands)} 个同名基线命令")

    for command in OPTIONAL_DISABLED_BASELINE_COMMANDS:
        restore_optional_disabled_command(backup, dst_cmds, command, "OpenCode")

    # 恢复 start.md
    backup_start = backup / "start.md"
    if backup_start.exists():
        shutil.copy2(backup_start, dst_cmds / "start.md")
        ok("[OpenCode] start.md 已恢复")
    else:
        warn("[OpenCode] 无 start.md 备份，未恢复")

    # 恢复 finish-work.md
    backup_finish_work = backup / "finish-work.md"
    if backup_finish_work.exists():
        shutil.copy2(backup_finish_work, dst_cmds / "finish-work.md")
        ok("[OpenCode] finish-work.md 已恢复")
    else:
        warn("[OpenCode] 无 finish-work.md 备份，未恢复")

    # 恢复 record-session.md
    backup_record_session = backup / "record-session.md"
    if backup_record_session.exists():
        shutil.copy2(backup_record_session, dst_cmds / "record-session.md")
        ok("[OpenCode] record-session.md 已恢复")
    else:
        warn("[OpenCode] 无 record-session.md 备份，未恢复")

    # 清理备份目录
    if backup.exists():
        shutil.rmtree(backup)
        ok("[OpenCode] 备份目录已删除")

    # 清理升级备份
    for directory in dst_cmds.iterdir():
        if directory.is_dir() and directory.name.startswith(".backup-upgrade-"):
            shutil.rmtree(directory)
            ok(f"[OpenCode] 升级备份已删除: {directory.name}")

    uninstall_managed_agents(root, "opencode", "OpenCode")


def uninstall_codex(
    root: Path,
    added_commands: list[str],
    overlay_commands: list[str],
    patched_codex_skills: list[str],
) -> None:
    """卸载 Codex CLI 部署的工作流 skills。"""
    # 优先检查 .agents/skills/，其次 .codex/skills/
    skills_dirs = [root / ".agents" / "skills", root / ".codex" / "skills"]
    primary_skills_dir = resolve_codex_skills_dir(root)
    found_any = False

    for skills_dir in skills_dirs:
        if not skills_dir.is_dir():
            continue
        found_any = True
        removed = 0
        for command in added_commands:
            skill_dir = skills_dir / command
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)
                ok(f"[Codex] 删除 skill: {command}")
                removed += 1
        info(f"[Codex] {skills_dir} 已删除 {removed} 个新增 skills")

        restored = 0
        for command in overlay_commands:
            backup_skill = skills_dir / ".backup-original" / command / "SKILL.md"
            target_skill = skills_dir / command / "SKILL.md"
            if backup_skill.exists():
                target_skill.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_skill, target_skill)
                ok(f"[Codex] 恢复 {command} skill")
                restored += 1
            else:
                warn(f"[Codex] {skills_dir} 无 {command} skill 备份，保留当前文件")
        if overlay_commands:
            info(f"[Codex] 已恢复 {restored}/{len(overlay_commands)} 个同名基线 skills")

        for command in OPTIONAL_DISABLED_BASELINE_COMMANDS:
            backup_skill = skills_dir / ".backup-original" / command / "SKILL.md"
            target_skill = skills_dir / command / "SKILL.md"
            if backup_skill.exists():
                target_skill.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_skill, target_skill)
                ok(f"[Codex] 恢复 {command} skill")

        if primary_skills_dir is not None and skills_dir == primary_skills_dir:
            for baseline_skill in patched_codex_skills:
                backup_skill = skills_dir / ".backup-original" / baseline_skill / "SKILL.md"
                if backup_skill.exists():
                    target_skill = skills_dir / baseline_skill / "SKILL.md"
                    target_skill.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_skill, target_skill)
                    ok(f"[Codex] 恢复 {baseline_skill} skill")

        backup_dir = skills_dir / ".backup-original"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            ok(f"[Codex] 删除备份目录: {backup_dir}")

        for directory in skills_dir.iterdir():
            if directory.is_dir() and directory.name.startswith(".backup-upgrade-"):
                shutil.rmtree(directory)
                ok(f"[Codex] 升级备份已删除: {directory.name}")

    if not found_any:
        warn("[Codex] 未找到 skills 目录，跳过")

    uninstall_managed_agents(root, "codex", "Codex")


def remove_agents_md_routing(root: Path) -> None:
    """移除安装器注入的 AGENTS.md 自然语言路由表。"""
    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        return

    content = agents_md.read_text(encoding="utf-8")
    if _AGENTS_NL_ROUTING_MARKER not in content:
        return

    start_idx = content.index(_AGENTS_NL_ROUTING_MARKER)
    end_idx = content.index(_AGENTS_NL_ROUTING_END) + len(_AGENTS_NL_ROUTING_END)
    prefix = content[:start_idx].rstrip()
    suffix = content[end_idx:].lstrip()
    new_content = prefix + ("\n\n" if prefix and suffix else "") + suffix
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    agents_md.write_text(new_content, encoding="utf-8")
    ok("AGENTS.md NL 路由表已删除")


def remove_project_todo(root: Path) -> None:
    """删除安装器默认创建且未被修改的 todo.txt。"""
    todo_path = root / _TODO_FILE_NAME
    if not todo_path.exists():
        return

    content = todo_path.read_text(encoding="utf-8")
    if content == _TODO_DEFAULT_LINE:
        todo_path.unlink()
        ok("todo.txt 已删除")
    else:
        warn("todo.txt 已被修改，保留现有内容")


def restore_shared_workflow_doc(root: Path) -> None:
    """恢复 .trellis/workflow.md 基线，并清理其备份目录。"""
    trellis_dir = root / ".trellis"
    workflow_md = trellis_dir / "workflow.md"
    backup_dir = trellis_dir / ".backup-original"
    backup_workflow = backup_dir / "workflow.md"

    if backup_workflow.exists():
        shutil.copy2(backup_workflow, workflow_md)
        ok("workflow.md 已恢复")
    else:
        warn("无 workflow.md 备份，未恢复")

    if backup_dir.exists():
        shutil.rmtree(backup_dir)
        ok(".trellis/.backup-original 已删除")

    if trellis_dir.is_dir():
        for directory in trellis_dir.iterdir():
            if directory.is_dir() and directory.name.startswith(".backup-upgrade-"):
                shutil.rmtree(directory)
                ok(f".trellis 升级备份已删除: {directory.name}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="卸载自定义工作流（支持 Claude Code / OpenCode / Codex CLI）"
    )
    parser.add_argument("--project-root", type=Path, default=None, help="项目根目录（默认自动检测）")
    parser.add_argument("--cli", type=str, default=None,
                        help="指定 CLI 类型，逗号分隔: claude,opencode,codex（默认全部自动检测）")
    args = parser.parse_args()

    root = args.project_root or find_root(Path(__file__))

    # 检测 CLI 类型
    requested = [x.strip() for x in args.cli.split(",")] if args.cli else None
    cli_types = detect_cli_types(root, requested)

    rec_file = root / ".trellis" / "workflow-installed.json"
    record = load_install_record(rec_file)
    commands = record.get("commands") or DEFAULT_COMMANDS
    overlay_commands, added_commands = split_commands(
        commands,
        record.get("overlay_commands"),
        record.get("added_commands"),
    )
    installed_cli_types = record.get("cli_types") or cli_types

    # 优先使用安装记录中的 CLI 类型
    target_cli_types = installed_cli_types if installed_cli_types else cli_types
    if requested:
        target_cli_types = [t for t in target_cli_types if t in requested]

    print()
    print("╔══════════════════════════════════════════╗")
    print("║   自定义工作流 → 卸载（多CLI）             ║")
    print("╚══════════════════════════════════════════╝")
    print()
    info(f"目标 CLI: {', '.join(target_cli_types)}")
    info(f"待卸载命令: {', '.join(commands)}")
    info(f"同名基线命令: {', '.join(overlay_commands) or '无'}")
    info(f"纯新增命令: {', '.join(added_commands) or '无'}")
    print()

    for cli_type in target_cli_types:
        if cli_type == "claude":
            uninstall_claude(root, added_commands, overlay_commands)
        elif cli_type == "opencode":
            uninstall_opencode(root, added_commands, overlay_commands)
        elif cli_type == "codex":
            patched_codex_skills = record.get("patched_codex_skills") or CODEX_PATCH_BASELINE_SKILLS
            uninstall_codex(root, added_commands, overlay_commands, patched_codex_skills)
        print()

    # 删除辅助脚本
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    if dst_scripts.is_dir():
        shutil.rmtree(dst_scripts)
        ok(".trellis/scripts/workflow/ 已删除")

    # 删除安装记录
    if rec_file.exists():
        rec_file.unlink()
        ok("workflow-installed.json 已删除")

    # 删除 AGENTS.md 路由表注入
    remove_agents_md_routing(root)

    # 删除安装器默认创建的 todo.txt
    remove_project_todo(root)

    # 恢复 .trellis/workflow.md 基线
    restore_shared_workflow_doc(root)

    print()
    print("✅ 卸载完成 — Trellis 已恢复原始状态")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
