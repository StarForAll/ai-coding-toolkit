#!/usr/bin/env python3
"""Trellis 版本升级后重新嵌入工作流。

用法:
  python3 upgrade-compat.py --check    # 检测冲突（默认）
  python3 upgrade-compat.py --merge    # 自动合并
  python3 upgrade-compat.py --force    # 强制覆盖
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


G, Y, R, C, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0;36m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")
def err(m): print(f"{R}❌ {m}{N}")
def info(m): print(f"{C}ℹ️  {m}{N}")


def find_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    sys.exit(f"{R}未找到 .claude/ 目录{N}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_const", const="check", dest="mode", default="check")
    p.add_argument("--merge", action="store_const", const="merge", dest="mode")
    p.add_argument("--force", action="store_const", const="force", dest="mode")
    args = p.parse_args()

    src = Path(__file__).resolve().parent
    root = find_root()
    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    rec_file = root / ".trellis" / "workflow-installed.json"

    NEW_COMMANDS = ["feasibility", "design", "plan", "test-first", "self-review", "check", "delivery"]
    HELPER_SCRIPTS = ["feasibility-check.py", "design-export.py", "plan-validate.py", "self-review-check.py"]

    # 读取版本
    cur_ver = ((root / ".trellis" / ".version").read_text().strip()
               if (root / ".trellis" / ".version").exists() else "unknown")
    inst_ver = "unknown"
    if rec_file.exists():
        inst_ver = json.loads(rec_file.read_text()).get("trellis_version", "unknown")

    print()
    print("╔══════════════════════════════════════╗")
    print("║   Trellis 版本升级兼容处理            ║")
    print("╚══════════════════════════════════════╝")
    print()

    info(f"当前版本: {cur_ver}  |  安装时版本: {inst_ver}")
    if cur_ver == inst_ver:
        ok("版本一致，无需处理")
        return
    warn(f"版本变化: {inst_ver} → {cur_ver}")
    print()

    # 冲突检测
    conflicts = 0
    start = dst_cmds / "start.md"
    if not (start.exists() and "Phase Router" in start.read_text()):
        err("start.md: Phase Router 丢失")
        conflicts += 1
    else:
        ok("start.md: Phase Router 正常")

    missing = [c for c in NEW_COMMANDS if not (dst_cmds / f"{c}.md").exists()]
    if missing:
        for c in missing:
            warn(f"命令缺失: /trellis:{c}")
        conflicts += 1
    else:
        ok("所有命令存在")
    print(f"   冲突: {conflicts}")
    print()

    if args.mode == "check":
        if conflicts:
            err(f"发现 {conflicts} 个冲突，运行 --merge 修复")
            sys.exit(1)
        ok("无冲突")
        return

    # 备份
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    bk = dst_cmds / f".backup-upgrade-{ts}"
    bk.mkdir(parents=True, exist_ok=True)
    if start.exists():
        shutil.copy2(start, bk / "start.md")
    for c in NEW_COMMANDS:
        p = dst_cmds / f"{c}.md"
        if p.exists():
            shutil.copy2(p, bk / f"{c}.md")
    ok(f"备份 → {bk.name}")

    # 重新部署命令
    for cmd in NEW_COMMANDS:
        s, d = src / f"{cmd}.md", dst_cmds / f"{cmd}.md"
        if s.exists():
            c = s.read_text(encoding="utf-8")
            c = c.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
            d.write_text(c, encoding="utf-8")
            ok(f"/trellis:{cmd}")

    # 合并 start.md
    if not (start.exists() and "Phase Router" in start.read_text()):
        patch = src / "start-patch-phase-router.md"
        if patch.exists() and start.exists():
            content = start.read_text(encoding="utf-8")
            marker = "## Operation Types"
            if marker in content:
                before, after = content.split(marker, 1)
                start.write_text(before + patch.read_text(encoding="utf-8") + "\n" + marker + after, encoding="utf-8")
                ok("Phase Router 已注入")

    # 重新部署脚本
    dst_scripts.mkdir(parents=True, exist_ok=True)
    for f in HELPER_SCRIPTS:
        s = src / "shell" / f
        if s.exists():
            shutil.copy2(s, dst_scripts / f)
            (dst_scripts / f).chmod(0o755)
    ok("辅助脚本已更新")

    # 更新安装记录
    now = datetime.now(timezone.utc).isoformat()
    rec_file.write_text(json.dumps({
        "trellis_version": cur_ver,
        "previous_version": inst_ver,
        "updated": now,
        "commands": NEW_COMMANDS,
        "scripts": HELPER_SCRIPTS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"版本标记已更新: {cur_ver}")

    print()
    print("✅ 升级兼容处理完成")
    print()


if __name__ == "__main__":
    main()
