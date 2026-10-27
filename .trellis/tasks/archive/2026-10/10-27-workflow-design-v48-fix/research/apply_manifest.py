#!/usr/bin/env python3
"""v48 fix round: apply manifest rows by exact replace(old, new, 1).

Usage: apply_manifest.py [--manifest <tsv>] ID [ID ...]
Per row: pre-execution count(old) must be exactly 1 in the target file;
post-execution count(new) must be exactly 1. Any mismatch aborts the whole
run before writing anything (all rows staged in memory first).
"""
import sys
from pathlib import Path

ROOT = Path("/home/xzc/projects/personal/ai-coding-toolkit")
REC = Path(__file__).resolve().parent
DOCS = {
    "主稿": ROOT / "docs/workflows/workflow-design.md",
    "配套": ROOT / "docs/workflows/依赖机制设计说明.md",
    "spec": ROOT / ".trellis/spec/docs/index.md",
    "guide": ROOT / ".trellis/spec/guides/design-review-thinking-guide.md",
    "residuals": REC / "residuals.md",
}

# 执行顺序（修复指令 §3 与复核修正轮 r2，均不可颠倒）
ORDER = {
    REC / "fix-manifest.tsv": [
        # 阶段 1 源
        "M2d", "M3b", "M3c", "M3a", "M4a", "M6", "M1",
        # 阶段 2 引用/镜像
        "M3d", "M3e", "M3f", "M3h", "M3g", "M4b", "M4c", "M4d", "M7a", "M7b", "M5", "M2a", "M2b", "M2c",
    ],
    REC / "fix-manifest-r2.tsv": [
        # 复核修正轮：先源（R1/R2），后正文位，再记录位
        "R1", "R2", "R3", "R4", "R5a", "R5b", "R5c", "R5d", "R5e", "R6c", "R6a", "R6b", "R7",
    ],
    REC / "fix-manifest-r3.tsv": [
        # r3 微修轮：源（R1/R2/R3/R4 正文）→ 记录/仪器（R5–R11）
        "R1a", "R1b", "R2a", "R2b", "R3a", "R3b", "R3c", "R3d", "R4a", "R4b", "R5", "R6", "R7", "R8a", "R8b", "R9", "R10a", "R10b", "R10c", "R10d", "R11",
    ],
}


def load_manifest(path):
    rows = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("ID\t"):
            continue
        cols = ln.split("\t")
        # 字段内换行以字面 \n 转义存储
        rows[cols[0]] = {
            "file": cols[1],
            "old": cols[3].replace("\\n", "\n"),
            "new": cols[4].replace("\\n", "\n"),
        }
    return rows


def main():
    args = sys.argv[1:]
    manifest = REC / "fix-manifest.tsv"
    if args and args[0] == "--manifest":
        manifest = REC / args[1]
        args = args[2:]
    order = ORDER[manifest]
    wanted = args or order
    for wid in wanted:
        if wid not in order:
            sys.exit(f"unknown or out-of-plan id: {wid}")
    rows = load_manifest(manifest)
    # 先全部读入并预检，任何一处计数不符即整体不落盘
    texts = {k: p.read_text(encoding="utf-8") for k, p in DOCS.items()}
    plan = []
    for wid in wanted:
        r = rows[wid]
        path = DOCS[r["file"]]
        text = texts[r["file"]]
        c_old = text.count(r["old"])
        if c_old != 1:
            sys.exit(f"{wid}: pre-execution count(old)={c_old}, expected 1 — abort")
        plan.append((wid, r, path))
    for wid, r, path in plan:
        text = path.read_text(encoding="utf-8")
        assert text.count(r["old"]) == 1, wid
        new_text = text.replace(r["old"], r["new"], 1)
        assert new_text.count(r["new"]) == 1, wid
        path.write_text(new_text, encoding="utf-8")
        line_no = new_text[: new_text.index(r["new"])].count("\n") + 1
        print(f"{wid}\t{path.name}\t{line_no}")
    print("all applied")


if __name__ == "__main__":
    main()
