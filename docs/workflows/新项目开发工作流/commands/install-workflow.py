#!/usr/bin/env python3
"""一键将自定义工作流嵌入 Trellis 框架。

前提: 已运行 trellis init
用法: python3 install-workflow.py [--project-root /path/to/project]
卸载: python3 uninstall-workflow.py
"""
import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── ANSI ──
G, Y, R, N = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[0m"
def ok(m): print(f"{G}✅ {m}{N}")
def warn(m): print(f"{Y}⚠️  {m}{N}")
def err(m): print(f"{R}❌ {m}{N}")


def find_root(start: Path) -> Path:
    """向上查找包含 .claude/ 的项目根目录。"""
    cur = start.resolve().parent
    for _ in range(10):
        if (cur / ".claude").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    sys.exit(f"{R}未找到 .claude/ 目录，请在 Trellis 项目内运行或用 --project-root 指定{N}")


def inject_phase_router(start_md: Path):
    """在 start.md 的 '## Operation Types' 前注入 Phase Router。"""
    block = (Path(__file__).parent / "start-patch-phase-router.md").read_text(encoding="utf-8")
    content = start_md.read_text(encoding="utf-8")
    marker = "## Operation Types"
    if marker in content:
        before, after = content.split(marker, 1)
        start_md.write_text(before + block + "\n" + marker + after, encoding="utf-8")
        ok("Phase Router 已注入 start.md")
    else:
        err("start.md 中未找到 '## Operation Types'，跳过注入")


def main():
    p = argparse.ArgumentParser(description="安装自定义工作流到 Trellis")
    p.add_argument("--project-root", type=Path, default=None)
    args = p.parse_args()

    src = Path(__file__).resolve().parent          # commands/ 源目录
    root = args.project_root or find_root(Path(__file__))
    dst_cmds = root / ".claude" / "commands" / "trellis"
    dst_scripts = root / ".trellis" / "scripts" / "workflow"
    backup = dst_cmds / ".backup-original"

    # ── 需部署的文件（根据你的工作流修改这里）──
    NEW_COMMANDS = [
        "feasibility", "design", "plan",
        "test-first", "self-review", "check", "delivery",
    ]
    HELPER_SCRIPTS = [
        "feasibility-check.py", "design-export.py",
        "plan-validate.py", "self-review-check.py",
    ]

    print()
    print("╔══════════════════════════════════════╗")
    print("║   自定义工作流 → Trellis 嵌入安装     ║")
    print("╚══════════════════════════════════════╝")
    print()

    # ── 前提检查 ──
    if not dst_cmds.is_dir():
        err(".claude/commands/trellis/ 不存在，请先运行: trellis init")
        sys.exit(1)
    ok("trellis 已初始化")

    # ── 备份 start.md ──
    print("📦 备份...")
    backup.mkdir(parents=True, exist_ok=True)
    start = dst_cmds / "start.md"
    bk = backup / "start.md"
    if start.exists() and not bk.exists():
        shutil.copy2(start, bk)
        ok(f"start.md → {bk}")
    else:
        warn("备份已存在，跳过")
    print()

    # ── 部署命令 ──
    print("📦 部署命令...")
    n = 0
    for cmd in NEW_COMMANDS:
        s, d = src / f"{cmd}.md", dst_cmds / f"{cmd}.md"
        if s.exists():
            c = s.read_text(encoding="utf-8")
            # 部署时将源路径替换为安装路径
            c = c.replace("docs/workflows/新项目开发工作流/commands/shell/", ".trellis/scripts/workflow/")
            d.write_text(c, encoding="utf-8")
            ok(f"/trellis:{cmd}")
            n += 1
    print(f"   {n}/{len(NEW_COMMANDS)} 个命令")
    print()

    # ── 注入 Phase Router ──
    print("🔄 start.md...")
    if start.exists() and "Phase Router" in start.read_text(encoding="utf-8"):
        ok("已有 Phase Router，跳过")
    elif (src / "start-patch-phase-router.md").exists():
        inject_phase_router(start)
    else:
        warn("start-patch-phase-router.md 不存在，跳过注入")
    print()

    # ── 部署辅助脚本 ──
    print("📦 辅助脚本...")
    dst_scripts.mkdir(parents=True, exist_ok=True)
    sn = 0
    for f in HELPER_SCRIPTS:
        s, d = src / "shell" / f, dst_scripts / f
        if s.exists():
            shutil.copy2(s, d)
            d.chmod(0o755)
            sn += 1
    print(f"   {sn}/{len(HELPER_SCRIPTS)} 个脚本")
    print()

    # ── 安装记录（存 .trellis/ 下，不依赖 trellis-local）──
    now = datetime.now(timezone.utc).isoformat()
    ver = (root / ".trellis" / ".version").read_text(encoding="utf-8").strip() if (root / ".trellis" / ".version").exists() else "unknown"
    rec = root / ".trellis" / "workflow-installed.json"
    import json
    rec.write_text(json.dumps({
        "trellis_version": ver,
        "installed": now,
        "commands": NEW_COMMANDS,
        "scripts": HELPER_SCRIPTS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    ok(f"安装记录 → {rec.name} (Trellis {ver})")

    print()
    print("╔══════════════════════════════════════╗")
    print("║   ✅ 安装完成                         ║")
    print("╚══════════════════════════════════════╝")
    print()
    print("  下一步（推荐）:")
    print("    1. 若目标项目已接入 trellis-library 组装流程，先补 requirements-discovery-foundation")
    print("       python3 trellis-library/cli.py assemble --target <project-root> --pack pack.requirements-discovery-foundation --dry-run")
    print("       确认 dry-run 输出无误后，去掉 --dry-run 正式执行")
    print("    2. 最低要求：补齐 problem-definition / scope-boundary / requirement-clarification / acceptance-criteria")
    print("       再补 customer-facing / developer-facing PRD spec、template、checklist")
    print("    3. 若未接入 trellis-library CLI，则手动复制最低资产集到目标项目 .trellis/")
    print("    4. 打开 Claude Code → /trellis:start")
    print(f"  卸载: python3 {src}/uninstall-workflow.py")
    print()


if __name__ == "__main__":
    main()
