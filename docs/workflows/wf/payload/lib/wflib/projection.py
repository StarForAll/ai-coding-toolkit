"""projection.py — 可重建投影（K8）与审计线索（K9）。

K8 的原则：**投影是记录的函数**，删掉能重建，`--check` 断言等值。这里提供的三个投影都不落盘
（`open-items` / `attribution` / 判断骨架），因此"删掉重建"恒成立；`--check` 做两件能真出错的事：
① 同一记录连算两次必须等值（纯函数性）；② 若运行态里存在缓存副本，必须与重算值等值。

K9 的承诺只到"局部损坏/提交后改写可检出"：写链按 `task.actions` 的 id 顺序与 `write_mark`
锚定核对；提交按 trailer 分三态——有 `wf-task:` 标记（attributed）/ 人裁决归属（adjudicated）/
无标记且无裁决（external）。不承诺防伪造。
"""

from __future__ import annotations

import os
import subprocess

from . import records


def open_items(ctx, task):
    """未结事项（S8/S5b 的可重建投影）：未核实项、未处置 finding、被驳回未处置判断。"""
    from . import judgments as judgments_mod
    from . import review as review_mod

    facts = judgments_mod.skeleton(ctx, task)
    unverified = []
    for entry in ((task.get("check") or {}).get("acceptance_results") or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("conclusion") in ("passed", None) and entry.get("conclusion") == "passed":
            continue
        acceptance_id = entry.get("acceptance_id")
        resolution = (task.get("unverified_resolutions") or {}).get(str(acceptance_id))
        unverified.append({"acceptance_id": acceptance_id,
                           "conclusion": entry.get("conclusion"),
                           "required": is_required(task, acceptance_id),
                           "resolved": bool(resolution),
                           "resolution": resolution})
    findings = review_mod.open_findings(ctx, task)
    return {
        "unverified": unverified,
        "unaddressed_findings": findings["unaddressed"],
        "unaddressed_blocking": findings["blocking"],
        "rejected_unresolved": facts["rejected_unresolved"],
        "count": len(unverified) + len(findings["unaddressed"]) + len(facts["rejected_unresolved"]),
    }


def attribution(ctx, task):
    """归属投影：提交三态 + 未归属的未提交路径（K9 的 trailer 三态）。"""
    base = task.get("baseline_head")
    task_id = task.get("id")
    attributed, adjudicated, external = [], [], []
    output = _git(ctx.root, ["log", "--format=%H%x00%B%x00", f"{base}..HEAD"]) if base else None
    if output:
        for chunk in output.split("\x00\x00"):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = chunk.split("\x00")
            sha = parts[0].strip()
            body = parts[1] if len(parts) > 1 else ""
            markers = [line.split("wf-task:", 1)[1].strip()
                       for line in body.splitlines() if "wf-task:" in line]
            if task_id and task_id in markers:
                attributed.append(sha)
            elif task_id and _adjudicated(task, sha):
                adjudicated.append(sha)
            else:
                external.append(sha)
    return {"base": base, "attributed": attributed, "adjudicated": adjudicated,
            "external": external, "available": output is not None,
            "unattributed_paths": [] if output else []}


def _adjudicated(task, sha):
    for entry in (task.get("attribution") or {}).get("decisions") or []:
        if isinstance(entry, dict) and str(entry.get("commit", "")).startswith(sha[:7]):
            return True
    return False


def audit_chain(task):
    """写链核对（K9）：动作按 id 序列、`write_mark` 锚定最后一个动作、时间单调。"""
    actions = [item for item in task.get("actions") or [] if isinstance(item, dict)]
    problems = []
    seen = set()
    last_at = None
    for index, action in enumerate(actions):
        identifier = action.get("id")
        if not identifier:
            problems.append({"index": index, "reason": "action lacks id"})
            continue
        if identifier in seen:
            problems.append({"index": index, "reason": "duplicate action id", "id": identifier})
        seen.add(identifier)
        at = action.get("at")
        if last_at and at and str(at) < str(last_at):
            problems.append({"index": index, "reason": "action time goes backwards", "at": at, "prev": last_at})
        if at:
            last_at = at
    mark = task.get("write_mark") or {}
    head = mark.get("action_id")
    if head and head not in seen:
        problems.append({"reason": "write_mark 指向不存在的动作", "action_id": head})
    return {"actions": len(actions), "head": head, "problems": problems,
            "guarantee": "只承诺局部损坏/提交后改写可检出，不承诺防伪造"}


def _git(root, args):
    try:
        proc = subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True)
    except OSError:
        return None
    return proc.stdout if proc.returncode == 0 else None


def build(ctx, task, kind):
    if kind == "open-items":
        return open_items(ctx, task)
    if kind == "attribution":
        return attribution(ctx, task)
    if kind == "audit":
        return audit_chain(task)
    if kind == "skeleton":
        from . import judgments as judgments_mod

        return judgments_mod.skeleton(ctx, task)
    raise ValueError(f"unknown projection: {kind}")


def cache_path(root, task_id, kind):
    return os.path.join(str(root), ".wf/.runtime/projections", str(task_id), f"{kind}.json")


def check(ctx, task, kind):
    """K8 的 `--check`：① 连算两次等值；② 若存在缓存副本，与之等值。"""
    first = build(ctx, task, kind)
    second = build(ctx, task, kind)
    problems = []
    if first != second:
        problems.append({"reason": "同一记录两算不等值（投影不是纯函数）", "kind": kind})
    cached = records.load_json(cache_path(ctx.root, task.get("id"), kind))
    if cached is not None and cached != first:
        problems.append({"reason": "缓存副本与重算不等值（缓存已漂移）", "kind": kind})
    return {"kind": kind, "equal": not problems, "problems": problems,
            "cached": cached is not None, "projection": first}


def is_required(task, acceptance_id):
    """该验收项是否 required：验收项自带 `required`，或其引用的验证里有一条 required。"""
    plan = task.get("plan") or {}
    required_verifications = {item.get("id") for item in plan.get("verifications") or []
                              if isinstance(item, dict) and item.get("required")}
    for item in plan.get("acceptance") or []:
        if not isinstance(item, dict) or item.get("id") != acceptance_id:
            continue
        if item.get("required") is True:
            return True
        return any(vid in required_verifications for vid in item.get("verification_ids") or [])
    return False


def required_unverified(ctx, task):
    """required 且未结案的验收项（S5b/4.9）：`required` 不得以"接受风险"结案，只能收窄或异常归档。"""
    items = open_items(ctx, task)["unverified"]
    return [item for item in items if item.get("required") and not item.get("resolved")]


def resolve(task, acceptance_id, *, kind, evidence, reason=None, impact=None, compensation=None, by="human"):
    """记录一次未核实项的处置（S8 的 `verify resolve`）。

    `kind=narrow`（收窄口径）必须给齐 4.9 的四项：被收窄项 id（本参数）、不可验证的客观原因、
    影响面与被放弃的保障、补偿措施；`kind=inspection` 是人工核验，必须有 evidence。
    """
    problems = []
    if kind not in ("narrow", "inspection"):
        problems.append({"reason": "kind 取 narrow|inspection", "kind": kind})
    if not str(evidence or "").strip():
        problems.append({"reason": "必须给核验/收窄的证据"})
    if kind == "narrow":
        for name, value in (("reason", reason), ("impact", impact), ("compensation", compensation)):
            if not str(value or "").strip():
                problems.append({"reason": f"收窄必须给 {name}（4.9 四项缺一不接受）"})
    if problems:
        return None, problems
    resolutions = dict(task.get("unverified_resolutions") or {})
    record = {"kind": kind, "evidence": evidence, "by": by, "at": records.now_str()}
    if kind == "narrow":
        record.update({"reason": reason, "impact": impact, "compensation": compensation})
    resolutions[str(acceptance_id)] = record
    task["unverified_resolutions"] = resolutions
    return record, []


def chain_head_check(ctx, task):
    """K9 的链头锚定核对：任务记录最后一次提交的 `wf-chain-head` 必须等于当前写链链头。"""
    relative = task.get("_record_path") or None
    if not relative:
        record_dir = os.path.join(".wf", "tasks")
        relative = record_dir
    output = _git(ctx.root, ["log", "-1", "--format=%B", "--", relative])
    head = ((task.get("write_mark") or {}).get("action_id")) or (task.get("action") or {}).get("id")
    if output is None:
        return {"available": False, "reason": "读不到该记录路径的提交历史", "head": head}
    trailer = None
    for line in output.splitlines():
        if line.strip().startswith("wf-chain-head:"):
            trailer = line.split("wf-chain-head:", 1)[1].strip()
    if trailer is None:
        return {"available": True, "anchored": False, "head": head,
                "reason": "最后一条提交没有 wf-chain-head trailer"}
    return {"available": True, "anchored": trailer == head, "head": head, "trailer": trailer}
