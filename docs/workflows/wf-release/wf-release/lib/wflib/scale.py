"""scale.py — 变化规模的事实托底（v42 4.6，S6 第 5 项）。

4.6 的判据本身是判断（"这次改了多少、要不要人确认"），框架只提供两个**事实**：
1. **自上次人确认以来的累计量**（净增删行、文件数），
2. **本项目历史上确认过的最大规模**（从归档任务记录派生），并据此高亮"超出历史最大值"。

不设绝对阈值（200/800 等已在 v10 删除）：比较对象是项目自身的历史，不是拍出来的数字。
"""

from __future__ import annotations

import os
import subprocess

from . import records


def _git(root, args):
    try:
        proc = subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout




def _count_lines(path):
    """二进制或不可读按 0 行计（只影响规模提示，不阻断）；不猜内容。"""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return 0
    if b"\x00" in data[:8192]:
        return 0
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)



def changes_since(ctx, task):
    """自任务基线（首次开工的 baseline_head）到当前工作树的累计变化。

    读不到Git（非仓库/基线不可达）时返回 `available=False` 并给原因，不猜 0。
    """
    base = task.get("baseline_head")
    if not base:
        return {"available": False, "reason": "任务尚无 baseline_head（未开工）"}
    output = _git(ctx.root, ["diff", "--numstat", str(base)])
    if output is None:
        return {"available": False, "reason": "git diff 不可用（基线不可达或非仓库）", "base": base}
    added = deleted = files = 0
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        plus, minus = parts[0], parts[1]
        if plus.isdigit():
            added += int(plus)
        if minus.isdigit():
            deleted += int(minus)
        files += 1
    # 未跟踪的新文件不计入 numstat：补一次数量，避免"净增删行"把新交付算成 0
    untracked = _git(ctx.root, ["ls-files", "--others", "--exclude-standard"]) or ""
    new_files = [line for line in untracked.splitlines() if line.strip()]
    # 未跟踪文件的**内容**也要计入：只补数量会让"新增 1000 行"显示成净增 0，规模判断失真。
    for relative in new_files:
        added += _count_lines(os.path.join(ctx.root, relative))
    return {"available": True, "base": base, "files": files + len(new_files),
            "new_files": len(new_files), "added": added, "deleted": deleted,
            "net": added - deleted}


def history_max(tasks):
    """历史上确认过的最大规模（只从记录派生：归档任务的 `cumulative.confirmed_net`）。"""
    best = None
    for task in tasks or []:
        value = ((task.get("cumulative") or {}).get("confirmed_net"))
        if isinstance(value, int) and (best is None or value > best):
            best = value
    return best


def describe(current, historical_max):
    """预览用的一行事实 + 是否超历史（超了只高亮，不阻断：判断权在人）。"""
    if not current.get("available"):
        return {"line": f"[规模]    不可得：{current.get('reason')}", "exceeds_history": None}
    net = current.get("net", 0)
    if historical_max is None:
        line = (f"[规模]    净增删 {net} 行 / 新增 {current.get('new_files', 0)} 个文件；"
                "本项目尚无历史确认记录（首个任务收工须确认一次以建立锚）")
        return {"line": line, "exceeds_history": None}
    over = net > historical_max
    line = (f"[规模]    净增删 {net} 行 / 新增 {current.get('new_files', 0)} 个文件；"
            f"本项目历史最大 {historical_max} 行" + ("　← 超出历史最大值" if over else ""))
    return {"line": line, "exceeds_history": over}


def record(task, current, *, by="human", quote=None):
    """人确认规模时把累计量记进任务记录（committed），成为后续任务的"历史最大"输入。"""
    payload = dict(task.get("cumulative") or {})
    payload.update({"confirmed_net": current.get("net"), "confirmed_files": current.get("files"),
                    "added": current.get("added"), "deleted": current.get("deleted"),
                    "base": current.get("base"), "at": records.now_str(), "by": by, "quote": quote})
    task["cumulative"] = payload
    return payload
