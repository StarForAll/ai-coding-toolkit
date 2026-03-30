#!/usr/bin/env python3
"""Trellis 版本升级后重新嵌入工作流。

用法:
  python3 upgrade-compat.py --check              # 检测冲突（默认）
  python3 upgrade-compat.py --merge              # 自动合并
  python3 upgrade-compat.py --force              # 强制覆盖
  python3 upgrade-compat.py --project-root /path # 指定项目根目录
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"


def ok(message: str) -> None:
    print(f"{G}✅ {message}{N}")


def warn(message: str) -> None:
    print(f"{Y}⚠️  {message}{N}")


def err(message: str) -> None:
    print(f"{R}❌ {message}{N}")


def info(message: str) -> None:
    print(f"{C}ℹ️  {message}{N}")


_PHASE_ROUTER_MARKER = "## Phase Router `[AI]`"
_INJECTION_MARKER = "## Operation Types"
NEW_COMMANDS = ["feasibility", "design", "plan", "test-first", "self-review", "check", "delivery"]
HELPER_SCRIPTS = [
    "feasibility-check.py",
    "design-export.py",
    "plan-validate.py",
    "self-review-check.py",
    "delivery-control-validate.py",
    "metadata-autocommit-guard.py",
]


def find_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    sys.exit(f"{R}未找到 .claude/ 目录{N}")


def has_phase_router(start_md: Path) -> bool:
    if not start_md.exists():
        return False
    return _PHASE_ROUTER_MARKER in start_md.read_text(encoding="utf-8")


def load_install_record(rec_file: Path) -> dict:
    if not rec_file.exists():
        return {}
    try:
        return json.loads(rec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        warn(f"workflow-installed.json 损坏: {exc}")
        return {}


def detect_conflicts(dst_cmds: Path, dst_scripts: Path) -> int:
    conflicts = 0
    start = dst_cmds / "start.md"

    if not has_phase_router(start):
        err("start.md: Phase Router 丢失")
        conflicts += 1
    else:
        ok("start.md: Phase Router 正常")

    missing_commands = [name for name in NEW_COMMANDS if not (dst_cmds / f"{name}.md").exists()]
    if missing_commands:
        for name in missing_commands:
            warn(f"命令缺失: /trellis:{name}")
        conflicts += len(missing_commands)
    else:
        ok("所有命令存在")

    missing_scripts = [name for name in HELPER_SCRIPTS if not (dst_scripts / name).exists()]
    if missing_scripts:
        for name in missing_scripts:
            warn(f"辅助脚本缺失: {name}")
        conflicts += len(missing_scripts)
    else:
        ok("所有辅助脚本存在")

    return conflicts


def backup_deployed_state(dst_cmds: Path, start: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = dst_cmds / f".backup-upgrade-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if start.exists():
        shutil.copy2(start, backup_dir / "start.md")
    for name in NEW_COMMANDS:
        candidate = dst_cmds / f"{name}.md"
        if candidate.exists():
            shutil.copy2(candidate, backup_dir / f"{name}.md")
    ok(f"备份 → {backup_dir.name}")


def deploy_commands(src: Path, dst_cmds: Path) -> None:
    for name in NEW_COMMANDS:
        source_path = src / f"{name}.md"
        target_path = dst_cmds / f"{name}.md"
        if source_path.exists():
            content = source_path.read_text(encoding="utf-8")
            content = content.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
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


def restore_start_from_original_backup(dst_cmds: Path, start: Path) -> bool:
    backup_start = dst_cmds / ".backup-original" / "start.md"
    if not backup_start.exists():
        err("缺少 .backup-original/start.md，无法执行强制恢复")
        return False
    shutil.copy2(backup_start, start)
    ok("start.md 已从 .backup-original 恢复")
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


def write_install_record(rec_file: Path, current_version: str, previous_version: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    rec_file.write_text(
        json.dumps(
            {
                "trellis_version": current_version,
                "previous_version": previous_version,
                "updated": now,
                "commands": NEW_COMMANDS,
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
    args = parser.parse_args()

    src = Path(__file__).resolve().parent
    if args.project_root:
        root = args.project_root.resolve()
        if not (root / ".claude").is_dir():
            sys.exit(f"{R}指定的项目根目录不含 .claude/{N}")
    else:
        root = find_root()

    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    rec_file = root / ".trellis" / "workflow-installed.json"
    start = dst_cmds / "start.md"

    current_version = (
        (root / ".trellis" / ".version").read_text(encoding="utf-8").strip()
        if (root / ".trellis" / ".version").exists()
        else "unknown"
    )
    record = load_install_record(rec_file)
    installed_version = record.get("trellis_version", "unknown")
    version_changed = current_version != installed_version

    print()
    print("╔══════════════════════════════════════╗")
    print("║   Trellis 版本升级兼容处理            ║")
    print("╚══════════════════════════════════════╝")
    print()

    info(f"当前版本: {current_version}  |  安装时版本: {installed_version}")
    if version_changed:
        warn(f"版本变化: {installed_version} → {current_version}")
    else:
        info("版本一致，继续检查部署完整性")
    print()

    conflicts = detect_conflicts(dst_cmds, dst_scripts)
    print(f"   冲突: {conflicts}")
    print()

    if args.mode == "check":
        if conflicts:
            err(f"发现 {conflicts} 个冲突，运行 --merge 修复")
            return 1
        if version_changed:
            warn("检测通过，但版本记录已落后；如需重新部署并刷新版本标记，请运行 --merge")
        else:
            ok("版本一致，部署完整")
        return 0

    if not version_changed and conflicts == 0:
        ok("版本一致且部署完整，无需重新部署")
        return 0

    backup_deployed_state(dst_cmds, start)
    deploy_commands(src, dst_cmds)

    if args.mode == "force" and not restore_start_from_original_backup(dst_cmds, start):
        return 1
    if not has_phase_router(start) and not inject_phase_router(src, start):
        err("Phase Router 恢复失败，未更新版本标记")
        return 1

    deploy_scripts(src, dst_scripts)
    write_install_record(rec_file, current_version, installed_version)
    cleanup_old_backups(dst_cmds)

    print()
    print("✅ 升级兼容处理完成")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
