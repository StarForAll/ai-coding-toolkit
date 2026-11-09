"""judgments.py — 判断骨架、`judgments[]` 与收工预览（v42 §5，K8 投影）。

分工（v42 §5.1）：**骨架是事实**，由框架从记录派生、删了能重建，AI 不得编造；
**judgments 是 AI 的语义**，append-only，只增不撤，引用只能选骨架里的 id。
预览是"人只看这一屏"，必须显式列出计数（含"不确定 0"这类断言）。

本模块只做派生、校验与渲染，不判断 decision 对不对（§5.4：框架不判决内容）。
"""

from __future__ import annotations

import os

from . import codes, records

# v42 §5.2：只记三类，种类取既有判断类（`by=human` 只是字段，不新增第十类）
KINDS = ("归属", "关闭", "沿用", "扩面", "标准变更", "缺口", "未核实", "规模")
DECISIONS = ("applied", "escalated")
OUTCOMES = ("applied", "escalated")
BY = ("ai", "human")


def skeleton(ctx, task):
    """事实骨架：全部由记录派生（K8 可重建）。删掉再算必须等值。"""
    from . import scope as scope_mod
    from . import tasks as tasks_mod

    reviews = task.get("reviews") or {}
    check = task.get("check") or {}
    try:
        classified = scope_mod.classify_candidates(
            ctx.root, task, receipts=tasks_mod.task_receipts(ctx.root))
        owned = list(classified["buckets"]["e"])
        excluded = list(classified["buckets"]["c"]) + list(classified["buckets"]["d"])
    except Exception:  # 分类失败不放大为阻断：骨架如实标"不可用"，不猜
        owned, excluded = [], []
        classified = {"unavailable": True}
    from . import review as review_mod

    disposals = [item for item in reviews.get("dispositions") or [] if isinstance(item, dict)]
    # 全部 findings（含已处置）进骨架；未处置的是它的子集，不是同一份东西
    findings = [{"id": item["id"], "severity": item.get("severity"), "class": item.get("class"),
                 "closed": item.get("closed")}
                for item in review_mod.all_findings(ctx, task)]
    closures = [{"finding_id": item.get("finding_id"), "cited_verification": item.get("evidence_refs"),
                 "recheck_by": item.get("recheck_by")}
                for item in disposals if item.get("decision") == "accepted"]
    # 未处置 findings 直接取 K8 投影（重解析报告），与归档门禁同源
    from . import review as review_mod

    unaddressed = [{"finding_id": item["finding_id"], "severity": item.get("severity")}
                   for item in review_mod.open_findings(ctx, task)["unaddressed"]]
    verifications = [{"id": entry.get("verification_id"), "result": entry.get("status")}
                     for entry in check.get("commands") or [] if isinstance(entry, dict)]
    judgments = [item for item in task.get("judgments") or [] if isinstance(item, dict)]
    rejected = [{"at": item.get("at"), "kind": item.get("kind"), "decision": item.get("decision")}
                for item in judgments
                if (item.get("challenged") or {}).get("conclusion") == "rejected"
                and not item.get("resolved_by") and not item.get("waived_by")]
    waived = [item for item in judgments if item.get("waived_by")]
    return {
        "changed_paths": sorted(owned),
        "excluded_paths": sorted(excluded),
        "repo_rule_files": _repo_rule_files(ctx, task),
        "vendor_dirty": list(classified.get("vendor_dirty") or []),
        "findings": findings,
        "closures": closures,
        # 扩面/标准变更两类事件池由**判断记录**派生，不再恒空（否则抽样永远抽不到它们）
        "fix_scope": [{"paths": item.get("paths") or [], "decision": item.get("decision"),
                       "basis": item.get("basis")}
                      for item in (task.get("judgments") or [])
                      if isinstance(item, dict) and item.get("kind") == "扩面"],
        "standard_changes": [{"decision": item.get("decision"), "basis": item.get("basis")}
                             for item in (task.get("judgments") or [])
                             if isinstance(item, dict) and item.get("kind") == "标准变更"],
        "drift_diffs": _drift_diffs(ctx, task),   # 漂移位置：保存时的 parts vs 当前 parts（K8 可重建）
        "anchor_parts": _anchor_part_names(ctx, task),   # 实质字段清单（预览「不变」行用）
        "verifications": verifications,
        # §0.2 的「未核实」事件源：未结案的验收项（S5b 的 unverified[]）
        "unverified": [str(item.get("acceptance_id"))
                       for item in (_required_unverified(ctx, task))],
        "cumulative": cumulative_facts(ctx, task),
        "rejected": [dict(item) for item in disposals if item.get("decision") == "rejected"],
        "rejected_unresolved": rejected,
        "unaddressed_findings": unaddressed,
        "waived_count": len(waived),
        "scope_available": not classified.get("unavailable", False),
    }


def cumulative_facts(ctx, task):
    """4.6 的事实托底：自基线以来的累计量 vs 本项目历史最大值（只给事实，不给阈值）。"""
    from . import scale as scale_mod

    current = scale_mod.changes_since(ctx, task)
    historical = scale_mod.history_max([item for _directory, item in _iter_all_tasks(ctx)])
    described = scale_mod.describe(current, historical)
    return {"since_last_authorized": current.get("net") if current.get("available") else None,
            "files": current.get("files"), "new_files": current.get("new_files"),
            "historical_max": historical, "exceeds_history": described["exceeds_history"],
            "line": described["line"], "available": current.get("available", False),
            "reason": current.get("reason")}


def _drift_diffs(ctx, task):
    """漂移差异（位置级）：拿 check 锚点里保存的 parts 与当前 parts 比，产出 `d:<字段>` 列表。

    这是 K8 的可重建投影——不落盘、不依赖导入时算的那份。
    """
    from . import check as check_mod
    from . import review as review_mod

    saved = ((task.get("check") or {}).get("anchor") or {}).get("parts")
    try:
        current = check_mod.anchor_parts(ctx, task)
    except Exception:            # 记录不完整时不给差异（调用方按"差异不可得"处理）
        return []
    diffs = review_mod.anchor_drift(saved, current)
    return diffs or []


def _repo_rule_files(ctx, task):
    """命中的仓库级规则文件（集合只来自 protocol，不在代码里另写一份）。"""
    from . import authorize as authorize_mod
    from . import check as check_mod

    try:
        return authorize_mod.repo_rule_paths(ctx, check_mod.object_paths(ctx, task))
    except Exception:
        return []


def _anchor_part_names(ctx, task):
    """锚点的实质字段名清单：直接取 `check.anchor_parts` 的键，不另写一份。"""
    from . import check as check_mod

    try:
        return sorted(check_mod.anchor_parts(ctx, task))
    except Exception:
        return []


def _required_unverified(ctx, task):
    from . import projection as projection_mod

    try:
        return projection_mod.required_unverified(ctx, task)
    except Exception:
        return []


def _iter_all_tasks(ctx):
    from . import tasks as tasks_mod

    return tasks_mod.iter_tasks(ctx.root)


def ref_ids(facts):
    """骨架里可被引用的 id 集合：`v:`/`f:`/`p:`/`d:`（v42 §5.1「引用从事实派生」）。"""
    ids = set()
    for verification in facts.get("verifications") or []:
        identifier = verification.get("id") or verification.get("verification_id")
        if identifier:
            ids.add(f"v:{identifier}")
    for finding in facts.get("findings") or []:
        if finding.get("id"):
            ids.add(f"f:{finding['id']}")
    for path in facts.get("changed_paths") or []:
        ids.add(f"p:{path}")
    # 漂移位置也是可引用的骨架事实（v42：`d:` 指漂移差异中的一个具体位置）
    for item in facts.get("drift_diffs") or []:
        if isinstance(item, dict) and item.get("id"):
            ids.add(str(item["id"]))
    return ids


PREFS = ("ask_always", "ai_decides")


def prefs_path(root):
    """偏好只在本机（v42 §5.3）：`.wf/.runtime/prefs.json`，不入库、不登记 protocol。"""
    return os.path.join(str(root), ".wf", ".runtime", "prefs.json")


def load_prefs(root):
    payload = records.load_json(prefs_path(root))
    if not isinstance(payload, dict):
        return {}
    return {str(k): v for k, v in payload.items() if v in PREFS}


def set_pref(root, kind, value):
    """人设定某类判断的偏好：`ask_always`（每次都问）/ `ai_decides`（自己定）。"""
    if kind not in KINDS:
        raise ValueError(f"unknown judgment kind: {kind}")
    if value not in PREFS:
        raise ValueError(f"preference must be one of {PREFS}")
    payload = dict(load_prefs(root))
    payload[str(kind)] = value
    records.write_json(prefs_path(root), payload)
    return payload


def validate(entry, facts):
    """单条 judgment 的机械校验（§5.4：只核引用是否属骨架派生集合、字段是否成立）。"""
    problems = []
    if not isinstance(entry, dict):
        return [{"reason": "judgment must be an object"}]
    if entry.get("kind") not in KINDS:
        problems.append({"reason": "kind 非法", "kind": entry.get("kind"), "known": list(KINDS)})
    if not str(entry.get("basis") or "").strip():
        problems.append({"reason": "basis 必填（留下依据，不规定结论）"})
    outcome = entry.get("outcome")
    if outcome not in OUTCOMES:
        problems.append({"reason": "outcome 取 applied|escalated", "outcome": outcome})
    if outcome == "escalated" and not str(entry.get("escalated_question") or "").strip():
        problems.append({"reason": "escalated 必须写清你判断不了的那个问题"})
    kind = entry.get("kind")
    prefs = facts.get("prefs") or {}
    if prefs.get(kind) == "ask_always" and outcome != "escalated":
        problems.append({"reason": "该类判断设为 ask_always：必须 escalated 交人，不得自己定",
                         "kind": kind})
    if outcome == "escalated" and prefs.get(kind) == "ai_decides" and not str(entry.get("why") or "").strip():
        problems.append({"reason": "ai_decides 下的越界升级必须写 why（为什么判断不了）",
                         "kind": kind})
    if entry.get("by") is not None and entry.get("by") not in BY:
        problems.append({"reason": "by 取 ai|human", "by": entry.get("by")})
    # 豁免只能由人给出（v42 §6）：`waived_by` 必须带 human 前缀，AI 不得自行免检
    waived_by = str(entry.get("waived_by") or "")
    if waived_by and not waived_by.startswith("human:"):
        problems.append({"reason": "豁免只能由人给出（waived_by 须为 human:<来源>）",
                         "waived_by": waived_by})
    # 判「沿用」必须引用一个**存在**的漂移位置（`d:`）：位置存不存在是事实，相关性是判断
    drift_ids = {str(item.get("id")) for item in (facts.get("drift_diffs") or [])
                 if isinstance(item, dict) and item.get("id")}
    refs = [str(item) for item in entry.get("evidence_refs") or []]
    if entry.get("kind") == "沿用" and not any(r.startswith("d:") for r in refs):
        problems.append({"reason": "判「沿用」必须引用漂移差异中的一个位置（d:<字段>）",
                         "known_positions": sorted(drift_ids)[:20]})
    for ref in refs:
        if ref.startswith("d:") and ref not in drift_ids:
            problems.append({"reason": "漂移位置不在 drift_diffs 里（位置存不存在是事实）",
                             "ref": ref, "known_positions": sorted(drift_ids)[:20]})
    rejected = {str(item.get("finding_id")) for item in (facts.get("rejected") or [])
                if isinstance(item, dict)}
    if str(entry.get("finding") or "") in rejected and not str(entry.get("resolved_by") or "").strip():
        problems.append({"reason": "被驳回的 finding 只能以 resolved 收口（须写 resolved_by）",
                         "finding": entry.get("finding")})
    known = ref_ids(facts)
    for ref in entry.get("evidence_refs") or []:
        if str(ref) not in known and str(ref).split("@", 1)[0] not in known:
            problems.append({"reason": "evidence_ref 不属骨架派生集合（不接受自由路径）",
                             "ref": ref, "known_sample": sorted(known)[:20]})
    return problems


def append(task, entry, facts=None):
    """append-only 追加：不得删除或改动既有条目；更正只能新增并用 `supersedes` 指向旧条目。"""
    facts = facts or skeleton_ids(task)
    judgments = list(task.get("judgments") or [])
    problems = validate(entry, facts)
    supersedes = entry.get("supersedes")
    if supersedes is not None:
        if not any(item.get("id") == supersedes for item in judgments if isinstance(item, dict)):
            problems.append({"reason": "supersedes 指向的条目不存在", "supersedes": supersedes})
    if problems:
        return None, problems
    record = dict(entry)
    record.setdefault("by", "ai")
    record.setdefault("at", records.now_str())
    record.setdefault("id", f"j{len(judgments) + 1}")
    judgments.append(record)          # 只追加，不重排、不删除
    task["judgments"] = judgments
    return record, []


def skeleton_ids(task):
    """无 ctx 的轻量骨架（只用于引用校验）；完整骨架见 `skeleton(ctx, task)`。"""
    findings = [finding for entry in ((task.get("reviews") or {}).get("imported") or [])
                for finding in (entry.get("findings") or []) if isinstance(finding, dict)]
    verifications = [entry for entry in ((task.get("check") or {}).get("commands") or [])
                     if isinstance(entry, dict)]
    return {"findings": findings, "verifications": verifications, "changed_paths": []}


def render_preview(task, facts=None, sampling_line=None):
    """收工预览（一屏）：计数必须显式（含"不确定 0"），AI 的说法不替代计数。"""
    facts = facts or skeleton_ids(task)
    judgments = [item for item in task.get("judgments") or [] if isinstance(item, dict)]
    by_kind = {}
    for item in judgments:
        by_kind.setdefault(item.get("kind"), []).append(item)
    unsure = [item for item in judgments
              if item.get("kind") == "归属" and str(item.get("decision") or "").lower().startswith("不确定")]
    rejected = facts.get("rejected_unresolved") or []
    escalated = [item for item in judgments if item.get("outcome") == "escalated"]
    lines = [
        f"本次任务判断清单（{len(judgments)} 条；需你复核 {len(escalated)} 条；被驳回未处置 {len(rejected)} 条）",
        "",
        f"[归属]    {len(facts.get('changed_paths') or [])} 个路径归本任务；不确定 {len(unsure)}",
        f"[关闭]    已处置 {len(facts.get('closures') or [])} 条；未处置 {len(facts.get('unaddressed_findings') or [])} 条",
        f"[验证]    本次实际跑过 {len(facts.get('verifications') or [])} 项",
        f"[豁免]    waived {facts.get('waived_count', 0)} 条（只能由人给出）",
    ]
    # 「不影响的不变」：没漂移的实质字段也要照列，否则人只看见变化、以为其余都动过（v42 §5.3）
    drift_where = {str(item.get("where")) for item in (facts.get("drift_diffs") or [])
                   if isinstance(item, dict)}
    parts = []
    for name in (facts.get("anchor_parts") or []):
        if name not in drift_where:
            parts.append(name)
    if parts:
        lines.append(f"[不变]    {len(parts)} 项实质字段未变：{'、'.join(sorted(parts)[:6])}"
                     + ("…" if len(parts) > 6 else ""))
    vendor = facts.get("vendor_dirty") or []
    if vendor:
        lines.append(f"[vendor]  {len(vendor)} 项框架自有改动（不计入交付、不进审查、不进业务提交）")
    cumulative = facts.get("cumulative") or {}
    if cumulative.get("line"):
        lines.append(cumulative["line"])
    if sampling_line:
        lines.append(sampling_line)
    if rejected:
        lines.append(f"[待处置]  被驳回且未处置：{len(rejected)} 条（AI 只能 resolved，waive 需你确认）")
    if escalated:
        lines.append(f"[升级]    {len(escalated)} 条判断判断不了：")
        for item in escalated:
            lines.append(f"          - {item.get('kind')}：{item.get('escalated_question')}")
    for kind in KINDS:
        entries = by_kind.get(kind)
        if not entries:
            continue
        lines.append(f"[{kind}]    {len(entries)} 条")
        for item in entries:
            flag = " [补]" if item.get("backfill") else ""
            lines.append(f"          · {item.get('decision')}{flag} ← {item.get('basis')}")
    return "\n".join(lines) + "\n"
