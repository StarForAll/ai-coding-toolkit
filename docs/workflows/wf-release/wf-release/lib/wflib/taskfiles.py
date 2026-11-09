"""taskfiles.py — 任务目录的规范文件集与"非规范文件"只读盘点（2026-11-07）。

真实 dogfood 里单任务产出 52 个文件，其中约 40 个是"证据/协议"自述文件：
它们把入口该生成的结构外化成了人工负担。这里给出**规范集**并只读报告多出来的文件，
让人/模型第一次就能看到"是不是又自建了证据文件"，而不是等到归档后翻目录。
"""

from __future__ import annotations

import os

# 任务目录的规范文件（入口写、或人按入口格式写的）
CANONICAL = (
    "task.json",      # 记录
    "prd.md",         # 规划
    "design.md",      # 复杂任务三件套
    "implement.md",
)
# 入口自己写的目录：review（导入的报告）、check-logs（task-check 的验证输出）
CANONICAL_DIRS = ("review", "check-logs")


def summary(root, task_id):
    """返回 {"count": N, "unexpected": [...]}; 目录不存在时 count=0。"""
    base = None
    for name in os.listdir(os.path.join(root, ".wf/tasks")):
        if name.startswith(f"{task_id}-") or name == task_id:
            candidate = os.path.join(root, ".wf/tasks", name)
            if os.path.isdir(candidate):
                base = candidate
                break
    if base is None:
        return {"count": 0, "unexpected": []}
    files = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if os.path.isdir(path):
            if name in CANONICAL_DIRS:
                continue
            files.append(name + "/")
        elif name not in CANONICAL:
            files.append(name)
    return {"count": len(files), "unexpected": files}
