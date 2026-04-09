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
- 建议先完成三态分析（A 纯净基线 / B 最新 workflow 期望状态 / C 目标项目真实状态）
- 当前 workflow 会重新部署合并型 + 纯新增型阶段命令资产
- `start.md` / `finish-work.md` / `record-session.md` 属于 Trellis 基线命令，升级脚本负责恢复并重新注入 workflow 补丁
- 若 Trellis 或 workflow 自身发生结构性 breaking change，本脚本不替代人工迁移判断
"""

import argparse
import json
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
_FINISH_WORK_START_HEADING = "### 1. Code Quality"
_FINISH_WORK_END_HEADING = "### 1.5. Test Coverage"
_RECORD_SESSION_MARKER = "## Record-Session Metadata Closure `[AI]`"
_RECORD_SESSION_INJECTION_MARKER = "### Step 2: One-Click Add Session"
# 当前 workflow 分发的阶段命令。
# `brainstorm` / `check` 与 Trellis 基线同名，但当前 workflow 采用合并后的阶段语义；
# `start` / `finish-work` / `record-session` 仍来自 Trellis 基线，并由当前 workflow 注入补丁。
_CLI_DIRS = CLI_DIRS
_CLI_ALT_DIRS = CLI_ALT_DIRS
_ALL_CLI_TYPES = ALL_CLI_TYPES


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
    found = []
    for cli_type, cli_dir in _CLI_DIRS.items():
        if requested and cli_type not in requested:
            continue
        if (root / cli_dir).is_dir():
            found.append(cli_type)
        elif cli_type in _CLI_ALT_DIRS and (root / _CLI_ALT_DIRS[cli_type]).is_dir():
            found.append(cli_type)
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


def load_install_record(rec_file: Path) -> dict:
    if not rec_file.exists():
        return {}
    try:
        return json.loads(rec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        warn(f"workflow-installed.json 损坏: {exc}")
        return {}


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


# ── Claude Code 冲突检测 ──
def detect_conflicts_claude(src: Path, dst_cmds: Path) -> int:
    conflicts = 0
    start = dst_cmds / "start.md"
    finish_work = dst_cmds / "finish-work.md"
    record_session = dst_cmds / "record-session.md"

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

    return conflicts


# ── OpenCode 冲突检测 ──
def detect_conflicts_opencode(src: Path, dst_cmds: Path) -> int:
    conflicts = 0
    start = dst_cmds / "start.md"
    finish_work = dst_cmds / "finish-work.md"
    record_session = dst_cmds / "record-session.md"

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

    return conflicts


# ── Codex 冲突检测 ──
def detect_conflicts_codex(src: Path, root: Path) -> int:
    conflicts = 0
    skills_dir = resolve_codex_skills_dir(root)
    if skills_dir is None:
        warn("[Codex] 未找到 skills 目录")
        return 0

    skill_conflicts = 0
    for name in DISTRIBUTED_COMMANDS:
        target_path = skills_dir / name / "SKILL.md"
        if not target_path.exists():
            warn(f"[Codex] skill 缺失: {name}")
            skill_conflicts += 1
            continue
        expected = expected_command_content(src, name)
        actual = read_text(target_path)
        if expected is None or actual is None:
            skill_conflicts += 1
            continue
        if actual != expected:
            err(f"[Codex] skill 内容漂移: {name}")
            skill_conflicts += 1
    if skill_conflicts:
        conflicts += skill_conflicts
    else:
        ok("[Codex] 所有分发 skills 内容一致")

    finish_work_skill = skills_dir / "finish-work" / "SKILL.md"
    if finish_work_skill.exists():
        if has_finish_work_patch(finish_work_skill):
            ok("[Codex] finish-work skill: 项目化补丁正常")
        else:
            err("[Codex] finish-work skill: 项目化补丁缺失")
            conflicts += 1

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
    for name in DISTRIBUTED_COMMANDS:
        candidate = dst_cmds / f"{name}.md"
        if candidate.exists():
            shutil.copy2(candidate, backup_dir / f"{name}.md")
    ok(f"备份 → {backup_dir.name}")


# ── 命令部署 ──
def prepare_command_content(source_path: Path) -> str:
    content = source_path.read_text(encoding="utf-8")
    content = content.replace("<WORKFLOW_DIR>/commands/shell/", ".trellis/scripts/workflow/")
    return content


def deploy_commands(src: Path, dst_cmds: Path) -> None:
    for name in DISTRIBUTED_COMMANDS:
        source_path = src / f"{name}.md"
        target_path = dst_cmds / f"{name}.md"
        if source_path.exists():
            content = prepare_command_content(source_path)
            target_path.write_text(content, encoding="utf-8")
            ok(f"/trellis:{name}")


def deploy_scripts(src: Path, dst_scripts: Path) -> None:
    dst_scripts.mkdir(parents=True, exist_ok=True)
    for name in HELPER_SCRIPTS:
        source_path = src / "shell" / name
        if source_path.exists():
            shutil.copy2(source_path, dst_scripts / name)
            (dst_scripts / name).chmod(0o755)
    ok("辅助脚本已更新")


def deploy_codex_skills(src: Path, root: Path) -> None:
    skills_dir = resolve_codex_skills_dir(root)
    if skills_dir is None:
        warn("[Codex] 未找到 skills 目录，跳过")
        return

    for name in DISTRIBUTED_COMMANDS:
        source_path = src / f"{name}.md"
        target_path = skills_dir / name / "SKILL.md"
        if source_path.exists():
            content = prepare_command_content(source_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            ok(f"[Codex] skill: {name}")


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


def restore_start_from_original_backup(dst_cmds: Path, start: Path) -> bool:
    backup_start = dst_cmds / ".backup-original" / "start.md"
    if not backup_start.exists():
        err("缺少 .backup-original/start.md，无法执行强制恢复")
        return False
    shutil.copy2(backup_start, start)
    ok("start.md 已从 .backup-original 恢复")
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
    start.write_text(before + patch.read_text(encoding="utf-8") + "\n" + _INJECTION_MARKER + after, encoding="utf-8")
    ok("Phase Router 已注入")
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


def write_install_record(rec_file: Path, current_version: str, previous_version: str, cli_types: list[str]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    rec_file.write_text(
        json.dumps(
            {
                "trellis_version": current_version,
                "previous_version": previous_version,
                "cli_types": cli_types,
                "updated": now,
                "commands": DISTRIBUTED_COMMANDS,
                "overlay_commands": OVERLAY_BASELINE_COMMANDS,
                "added_commands": ADDED_COMMANDS,
                "scripts": HELPER_SCRIPTS,
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

    current_version = (
        (root / ".trellis" / ".version").read_text(encoding="utf-8").strip()
        if (root / ".trellis" / ".version").exists()
        else "unknown"
    )
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
    for cli_type in cli_types:
        if cli_type == "claude":
            dst_cmds = root / ".claude" / "commands" / "trellis"
            total_conflicts += detect_conflicts_claude(src, dst_cmds)
        elif cli_type == "opencode":
            dst_cmds = root / ".opencode" / "commands" / "trellis"
            total_conflicts += detect_conflicts_opencode(src, dst_cmds)
        elif cli_type == "codex":
            total_conflicts += detect_conflicts_codex(src, root)
    total_conflicts += detect_shared_script_conflicts(src, dst_scripts)
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

    # 合并/修复
    for cli_type in cli_types:
        if cli_type == "claude":
            dst_cmds = root / ".claude" / "commands" / "trellis"
            start = dst_cmds / "start.md"
            finish_work = dst_cmds / "finish-work.md"
            record_session = dst_cmds / "record-session.md"
            backup_deployed_state(dst_cmds)
            deploy_commands(src, dst_cmds)
            if args.mode == "force":
                if not restore_start_from_original_backup(dst_cmds, start):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "finish-work"):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "record-session"):
                    return 1
            if not has_phase_router(start) and not inject_phase_router(src, start):
                err("[Claude] Phase Router 恢复失败")
                return 1
            if not has_finish_work_patch(finish_work) and not inject_finish_work_patch(src, finish_work, "finish-work.md"):
                err("[Claude] finish-work 项目化补丁恢复失败")
                return 1
            if not has_record_session_patch(record_session) and not inject_record_session_patch(src, record_session):
                err("[Claude] record-session 元数据闭环恢复失败")
                return 1
        elif cli_type == "opencode":
            dst_cmds = root / ".opencode" / "commands" / "trellis"
            start = dst_cmds / "start.md"
            finish_work = dst_cmds / "finish-work.md"
            record_session = dst_cmds / "record-session.md"
            backup_deployed_state(dst_cmds)
            deploy_commands(src, dst_cmds)
            if args.mode == "force":
                if not restore_start_from_original_backup(dst_cmds, start):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "finish-work"):
                    return 1
                if not restore_command_from_original_backup(dst_cmds, "record-session"):
                    return 1
            if not has_phase_router(start) and not inject_phase_router(src, start):
                err("[OpenCode] Phase Router 恢复失败")
                return 1
            if not has_finish_work_patch(finish_work) and not inject_finish_work_patch(src, finish_work, "finish-work.md"):
                err("[OpenCode] finish-work 项目化补丁恢复失败")
                return 1
            if not has_record_session_patch(record_session) and not inject_record_session_patch(src, record_session):
                err("[OpenCode] record-session 元数据闭环恢复失败")
                return 1
        elif cli_type == "codex":
            deploy_codex_skills(src, root)
            skills_dir = resolve_codex_skills_dir(root)
            if skills_dir is None:
                continue
            finish_work_skill = skills_dir / "finish-work" / "SKILL.md"
            if args.mode == "force" and finish_work_skill.exists():
                if not restore_codex_finish_work(skills_dir):
                    return 1
            if finish_work_skill.exists() and not has_finish_work_patch(finish_work_skill):
                if not inject_finish_work_patch(src, finish_work_skill, "finish-work skill"):
                    err("[Codex] finish-work 项目化补丁恢复失败")
                    return 1

    # 辅助脚本
    deploy_scripts(src, dst_scripts)

    # 更新安装记录
    write_install_record(rec_file, current_version, installed_version, cli_types)

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
