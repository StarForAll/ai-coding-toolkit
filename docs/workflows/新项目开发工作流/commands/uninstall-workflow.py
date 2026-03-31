#!/usr/bin/env python3
"""卸载工作流，恢复 Trellis 原始状态。

用法: python3 uninstall-workflow.py [--project-root /path/to/project]
"""

import json
import shutil
import sys
from pathlib import Path


G, Y, R, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0m"
DEFAULT_COMMANDS = ["feasibility", "brainstorm", "design", "plan", "test-first", "self-review", "check", "delivery"]


def ok(message: str) -> None:
    print(f"{G}✅ {message}{N}")


def warn(message: str) -> None:
    print(f"{Y}⚠️  {message}{N}")


def find_root(start: Path) -> Path:
    cur = start.resolve().parent
    for _ in range(10):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    sys.exit(f"{R}未找到 .claude/ 目录{N}")


def load_install_record(rec_file: Path) -> dict:
    if not rec_file.exists():
        return {}
    try:
        return json.loads(rec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        warn(f"workflow-installed.json 损坏，将使用默认卸载列表: {exc}")
        return {}


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=None)
    args = parser.parse_args()

    root = args.project_root or find_root(Path(__file__))
    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"
    rec_file = root / ".trellis" / "workflow-installed.json"

    record = load_install_record(rec_file)
    commands = record.get("commands") or DEFAULT_COMMANDS

    print()
    print("╔══════════════════════════════════════╗")
    print("║   自定义工作流 → 卸载                 ║")
    print("╚══════════════════════════════════════╝")
    print()

    removed = 0
    for command in commands:
        candidate = dst_cmds / f"{command}.md"
        if candidate.exists():
            candidate.unlink()
            ok(f"删除 {command}.md")
            removed += 1
    print(f"   {removed} 个命令\n")

    backup_start = backup / "start.md"
    if backup_start.exists():
        shutil.copy2(backup_start, dst_cmds / "start.md")
        ok("start.md 已恢复")
    else:
        warn("无备份，start.md 未修改")

    backup_record_session = backup / "record-session.md"
    if backup_record_session.exists():
        shutil.copy2(backup_record_session, dst_cmds / "record-session.md")
        ok("record-session.md 已恢复")
    else:
        warn("无 record-session 备份，record-session.md 未修改")

    if dst_scripts.is_dir():
        shutil.rmtree(dst_scripts)
        ok(".trellis/scripts/workflow/ 已删除")

    if rec_file.exists():
        rec_file.unlink()
        ok("workflow-installed.json 已删除")

    if backup.exists():
        shutil.rmtree(backup)
        ok("备份目录已删除")

    for directory in dst_cmds.iterdir():
        if directory.is_dir() and directory.name.startswith(".backup-upgrade-"):
            shutil.rmtree(directory)
            ok(f"升级备份已删除: {directory.name}")

    print()
    print("✅ 卸载完成 — Trellis 已恢复原始状态")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
