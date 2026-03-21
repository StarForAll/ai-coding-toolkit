#!/usr/bin/env python3
"""卸载工作流，恢复 Trellis 原始状态。

用法: python3 uninstall-workflow.py [--project-root /path/to/project]
"""
import json
import shutil
import sys
from pathlib import Path


G, Y, R, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")


def find_root(start: Path) -> Path:
    cur = start.resolve().parent
    for _ in range(10):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    sys.exit(f"{R}未找到 .claude/ 目录{N}")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=None)
    args = p.parse_args()

    root = args.project_root or find_root(Path(__file__))
    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"
    rec_file = root / ".trellis" / "workflow-installed.json"

    # 从安装记录读取命令列表，若无则用默认
    if rec_file.exists():
        rec = json.loads(rec_file.read_text(encoding="utf-8"))
        cmds = rec.get("commands", [])
    else:
        cmds = ["feasibility", "design", "plan", "test-first", "self-review", "delivery"]

    print()
    print("╔══════════════════════════════════════╗")
    print("║   自定义工作流 → 卸载                 ║")
    print("╚══════════════════════════════════════╝")
    print()

    # 删除命令
    n = 0
    for c in cmds:
        p = dst_cmds / f"{c}.md"
        if p.exists():
            p.unlink()
            ok(f"删除 {c}.md")
            n += 1
    print(f"   {n} 个命令\n")

    # 恢复 start.md
    bk = backup / "start.md"
    if bk.exists():
        shutil.copy2(bk, dst_cmds / "start.md")
        ok("start.md 已恢复")
    else:
        warn("无备份，start.md 未修改")

    # 删除脚本
    if dst_scripts.is_dir():
        shutil.rmtree(dst_scripts)
        ok(".trellis/scripts/workflow/ 已删除")

    # 删除安装记录
    if rec_file.exists():
        rec_file.unlink()
        ok("workflow-installed.json 已删除")

    # 清理备份
    if backup.exists():
        shutil.rmtree(backup)
        ok("备份目录已删除")

    print()
    print("✅ 卸载完成 — Trellis 已恢复原始状态")
    print()


if __name__ == "__main__":
    main()
