"""judgments.py — 判断骨架、`judgments[]` 与收工预览（v42 §5，K8 投影）。

分工（v42 §5.1）：**骨架是事实**，由框架从记录派生、删了能重建，AI 不得编造；
**judgments 是 AI 的语义**，append-only，只增不撤，引用只能选骨架里的 id。
预览是"人只看这一屏"，必须显式列出计数（含"不确定 0"这类断言）。

本模块只做派生、校验与渲染，不判断 decision 对不对（§5.4：框架不判决内容）。
"""

from __future__ import annotations

import os

from os.path import join

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
        "fix_scope": [{"judgment_id": item.get("id"), "paths": item.get("paths") or [],
                       "decision": item.get("decision"), "basis": item.get("basis")}
                      for item in (task.get("judgments") or [])
                      if isinstance(item, dict) and item.get("kind") == "扩面"],
        "standard_changes": [{"judgment_id": item.get("id"), "decision": item.get("decision"),
                              "basis": item.get("basis")}
                             for item in (task.get("judgments") or [])
                             if isinstance(item, dict) and item.get("kind") == "标准变更"],
        # [扩面]：本次新增的文件（相对归档/基线不存在者），来源取触发它的判断或 finding
        "new_paths": [{"path": path, "from": source}
                      for path, source in _new_paths(ctx, task, classified)],
        "new_in_scope": _new_in_scope(task, classified),
        "deleted_paths": _deleted_paths(ctx, task),
        # [未核实]：required 但这次没跑到、或被标成 supporting 的验收项，必须带原因与补偿
        "unverified": _unverified(ctx, task),
        # [缺口]/缺口事件源：取**判定结果**里的 gaps（此前读 imported[].gaps，导入流程从不写）
        "requirement_gap_findings": _review_gaps(task),
        "drift_diffs": _drift_diffs(ctx, task),   # 漂移位置：保存时的 parts vs 当前 parts（K8 可重建）
        "anchor_parts": _anchor_part_names(ctx, task),
        "prefs": load_prefs(ctx.root),   # 偏好只在本机；预览照实显示，缺失不提示（除非历史有过）   # 实质字段清单；None = 不可得（预览要照实说）
        "verifications": verifications,
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
    """锚点的实质字段名清单：直接取 `check.anchor_parts` 的键，不另写一份。

    算不出来时返回 `None`（不是 `[]`）：`[]` 会让预览看起来"没有不变项"，
    把"清单不可得"静默成"没有变化"——这正是本次审查点出的 P2。
    """
    from . import check as check_mod

    try:
        return sorted(check_mod.anchor_parts(ctx, task))
    except Exception:
        return None


def required_unverified_items(ctx, task):
    """required 且未结案的验收项（S5b/4.9）。

    **单向依赖**：judgments → projection，projection **不得**回头 import skeleton，
    否则会形成 `skeleton → required_unverified → open_items → skeleton` 的环
    （此前靠 `except Exception` 兜底，结果是算 199 层、3.67 秒、返回空列表）。
    """
    from . import projection as projection_mod

    return projection_mod.required_unverified(ctx, task)


def _iter_all_tasks(ctx):
    from . import tasks as tasks_mod

    return tasks_mod.iter_tasks(ctx.root)




def pending_escalations(task):
    """仍未被回答的 escalated 判断（v42 §5.3：只按当前有效判断算待决）。

    `judgments[]` 是 append-only：人回答后用新条目 `supersedes` 指向被挂起那条。
    历史必须保留，但**已被替代的条目不再算"还没回答"**——否则诚实求助会变成死路。
    门禁与预览必须共用这一处实现，否则"预览说 2 条待复核、门禁说 0 条"各说各话。
    """
    items = [item for item in (task.get("judgments") or []) if isinstance(item, dict)]
    superseded = {str(item.get("supersedes")) for item in items if item.get("supersedes")}
    return [item for item in items
            if item.get("outcome") == "escalated" and str(item.get("id")) not in superseded]



def ref_ids(facts):
    """骨架里可被引用的 id 集合（v42 §5.1「引用从事实派生」）。

    **单一 id 空间**：`v:`验收 `f:`finding `p:`路径 `d:`漂移位置，
    以及抽样事件的 `j:`判断 `a:`验收项 `s:`规模 `g:`缺口 `h:`内容摘要。
    抽样与 validate 必须共用这一处，否则"抽中了却无法补写"（历史缺陷）。
    """
    from . import sampling as sampling_mod

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
    for pool in (sampling_mod.events_of(facts) or {}).values():
        ids.update(str(item) for item in pool)
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
    # ask_always 约束的是"AI 不得自己定"，**不是"不许人回答"**：
    # 人给出的答复（by=human）本身就是该偏好的目的，拦住它会让求助再次变成死路。
    by_human = str(entry.get("by") or "") == "human"
    if prefs.get(kind) == "ask_always" and outcome != "escalated" and not by_human:
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






def _review_gaps(task):
    """审查缺口（uncovered 轴 / 未覆盖项）：不是失败，但必须可见、可被抽样到。"""
    gaps = (((task.get("reviews") or {}).get("result") or {}).get("facts") or {}).get("gaps") or []
    result = []
    for index, item in enumerate(gaps if isinstance(gaps, list) else []):
        if not isinstance(item, dict):
            continue
        label = item.get("axis") or item.get("reason") or f"gap-{index + 1}"
        result.append({"gap_id": str(label), "axis": item.get("axis"), "reason": item.get("reason"),
                       "slot": item.get("slot")})
    return result



def _new_paths(ctx, task, classified=None):
    """本次新增的**面外**文件 + 来源。

    语义（v42 §4.4/§5.3）：`[扩面]` 只表示"修下去要碰批准面之外的文件——需你复核"。
    所以这里必须按分类过滤：
      - 框架自有资产 / 控制记录（`.wf/tasks/**`、安装收据…）→ 完全不计（不是本任务交付）；
      - 批准面**之内**的新增 → 归 `[规模]`，不算扩面（把面内新增写进扩面会让"9 个新文件"
        这种噪声淹没真正的越界）；
      - 批准面**之外**的新增 → 进 `[扩面]`，保留来源标注。
    """
    from . import scope as scope_mod
    from . import tasks as tasks_mod

    if classified is None:
        try:
            classified = scope_mod.classify_candidates(ctx.root, task,
                                                       receipts=tasks_mod.task_receipts(ctx.root))
        except Exception:
            classified = {}
    buckets = (classified or {}).get("buckets") or {}
    # f：已提交但不在批准面；c：未提交且未归属。两者都只取"新增文件"
    candidates = set(buckets.get("f") or []) | set(buckets.get("c") or [])
    in_scope = list(buckets.get("e") or [])
    paths = []
    base = task.get("baseline_head")
    if base:
        out = _git(ctx.root, ["diff", "--name-status", str(base)])
        for line in (out or "").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].startswith("A"):
                paths.append(parts[-1])
    untracked = _git(ctx.root, ["ls-files", "--others", "--exclude-standard"]) or ""
    paths.extend(line.strip() for line in untracked.splitlines() if line.strip())
    sources = {}
    for item in task.get("judgments") or []:
        if not isinstance(item, dict):
            continue
        for path in item.get("paths") or []:
            sources.setdefault(str(path), item.get("kind") or "判断")
    for entry in ((task.get("reviews") or {}).get("imported") or []):
        for finding in entry.get("findings") or []:
            if isinstance(finding, dict) and finding.get("path"):
                sources.setdefault(str(finding["path"]), finding.get("id") or "finding")
    seen, result = set(), []
    for path in paths:
        if path in seen or path not in candidates:
            continue
        seen.add(path)
        result.append((path, sources.get(path)))
    return result


def _new_in_scope(task, classified):
    """批准面之内的新增数量（归 `[规模]`，不进 `[扩面]`）。"""
    return len(list(((classified or {}).get("buckets") or {}).get("e") or []))


def _deleted_paths(ctx, task):
    base = task.get("baseline_head")
    if not base:
        return []
    out = _git(ctx.root, ["diff", "--name-status", str(base)])
    return [line.split("\t")[-1] for line in (out or "").splitlines()
            if line.split("\t")[0].startswith("D")]


def _git(root, args):
    from .projection import _git as _projection_git

    return _projection_git(root, args)


def _unverified(ctx, task):
    """未结案的验收项：**从真实验收结果与处置记录派生**，不猜。

    此前的实现只读 plan 里的 required=False 项，导致"必需验证真失败"这种最该给人看的事实
    在预览里消失（门禁仍拦得住，但人审的那一屏漏了关键信息）。
    """
    from . import tasks as tasks_mod

    resolutions = task.get("unverified_resolutions") or {}
    entries = []
    for item in ((task.get("check") or {}).get("acceptance_results") or []):
        if not isinstance(item, dict):
            continue
        if item.get("conclusion") == "passed":
            continue
        acceptance_id = item.get("acceptance_id")
        resolution = resolutions.get(str(acceptance_id)) or {}
        if resolution:
            continue      # 已由人处置（verify resolve）的不再列为"未核实"
        try:
            required = tasks_mod.is_required(task, acceptance_id) if hasattr(tasks_mod, "is_required") else True
        except Exception:
            required = True
        entries.append({"id": acceptance_id,
                        "reason": f"验收结论={item.get('conclusion') or '未通过'}",
                        "compensation": ("必需项：只能收窄口径或异常归档"
                                         if required else "非必需：可记录为 supporting"),
                        "required": required})
    for item in task.get("unverified") or []:
        if isinstance(item, dict) and not resolutions.get(str(item.get("id"))):
            entries.append({"id": item.get("id"), "reason": item.get("reason") or "未说明",
                            "compensation": item.get("compensation") or "未给"})
    return entries



def skeleton_ids(task):
    """无 ctx 的轻量骨架（只用于引用校验）；完整骨架见 `skeleton(ctx, task)`。"""
    findings = [finding for entry in ((task.get("reviews") or {}).get("imported") or [])
                for finding in (entry.get("findings") or []) if isinstance(finding, dict)]
    verifications = [entry for entry in ((task.get("check") or {}).get("commands") or [])
                     if isinstance(entry, dict)]
    return {"findings": findings, "verifications": verifications, "changed_paths": []}




# ---- v42 §5.3：判断质量对照 / 依据对照 -------------------------------------
# 前提是「只增不撤」：judgments[] 是 append-only，所以"这类判断有没有少报"才可比。
# 设计上**不算分、不设阈值、不据此判退步**——只把差异与新旧依据摆出来，是否退步由人看。
HUNK_ONLY_MARKERS = ("hunk", "只引 hunk", "仅 hunk", "diff-hunk")


def _archive_records(root):
    """读归档任务记录（.wf/tasks/archive/<月>/<dir>/task.json）。读不到就返回空。"""
    base = join(root, ".wf/tasks/archive")
    found = []
    if not os.path.isdir(base):
        return found
    for month in sorted(os.listdir(base)):
        month_dir = join(base, month)
        if not os.path.isdir(month_dir):
            continue
        for name in sorted(os.listdir(month_dir)):
            record = records.load_json(join(month_dir, name, "task.json"), None)
            if isinstance(record, dict) and record.get("id"):
                record["_archived_dir"] = name
                found.append(record)
    return found


def _top_dirs(task):
    """顶层目录集合：§5.3 的"同类任务"按目录重叠判断。

    取**归档记录里真实存在**的批准触碰面（`entry_snapshot.touch_paths`，未开工回退 plan）——
    此前读 `task.changed_paths`，而正常流程从不写这个字段，导致对照永远"无同类任务可比"。
    """
    paths = ((task.get("entry_snapshot") or {}).get("touch_paths")
             or (task.get("plan") or {}).get("touch_paths") or [])
    dirs = set()
    for path in paths:
        text = str(path)
        parts = text.split("/")
        if len(parts) > 1:
            dirs.add(parts[0])
        elif "*" in text:
            dirs.add(".")
    return dirs


def _overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _shared_kind_items(task, kind):
    return [item for item in task.get("judgments") or []
            if isinstance(item, dict) and item.get("kind") == kind]


def _counts(task):
    """对照用三类计数（§5.3）：waived / escalated / 结构化差异只引 hunk。"""
    items = [item for item in task.get("judgments") or [] if isinstance(item, dict)]
    waived = [item for item in items if item.get("waived_by")]
    escalated = [item for item in items if item.get("outcome") == "escalated"]
    hunk_only = []
    for item in items:
        basis = str(item.get("basis") or "").lower()
        if any(marker in basis for marker in HUNK_ONLY_MARKERS):
            hunk_only.append(item)
    return {"waived": len(waived), "escalated": len(escalated), "hunk_only": len(hunk_only)}


def quality_comparison(root, task):
    """返回 §5.3 的两段行：`[判断质量]` 与 `[依据对照]`。

    找不到"上次同类任务"时**显式说明**（而不是假装没有退化）：全新项目首次收工就是这种情况。
    """
    current_dirs = _top_dirs(task)
    candidates = []
    for record in _archive_records(root):
        if record.get("id") == task.get("id"):
            continue
        candidates.append((_overlap(current_dirs, _top_dirs(record)), record))
    candidates.sort(key=lambda item: (-item[0], str(item[1].get("id"))))
    if not candidates or candidates[0][0] <= 0:
        return ["[判断质量] 无同类任务可比（首次收工或没有重叠目录的归档任务）；本项不产生对照",
                "[依据对照] 同上：无历史依据可并列"]

    overlap, previous = candidates[0]
    now_kinds = {item.get("kind") for item in task.get("judgments") or [] if isinstance(item, dict)}
    then_kinds = {item.get("kind") for item in previous.get("judgments") or [] if isinstance(item, dict)}
    added = sorted(k for k in now_kinds - then_kinds if k)
    gone = sorted(k for k in then_kinds - now_kinds if k)

    now_counts, then_counts = _counts(task), _counts(previous)
    weaker = []
    for kind in sorted(now_kinds & then_kinds):
        # 「依据变弱」只认**可核事实**：上次有引用、这次没有（引用在不在是事实，字数不是）。
        # 比字数会鼓励堆字——正好与"提高判断质量"相反。
        then_refs = sum(len(item.get("evidence_refs") or []) for item in _shared_kind_items(previous, kind))
        now_refs = sum(len(item.get("evidence_refs") or []) for item in _shared_kind_items(task, kind))
        if then_refs and not now_refs:
            weaker.append(kind)

    lines = [
        f"[判断质量] 与上次同类任务（{previous.get('id')}，目录重叠 {overlap * 100:.0f}%）相比："
        f"新增 {len(added)} 类{'（' + '、'.join(added) + '）' if added else ''} / "
        f"消失 {len(gone)} 类{'（' + '、'.join(gone) + '）' if gone else ''} / "
        f"依据变弱 {len(weaker)} 条{'（' + '、'.join(weaker) + '）' if weaker else ''}",
        f"          waived {now_counts['waived']}（上次 {then_counts['waived']}）/ "
        f"escalated {now_counts['escalated']}（上次 {then_counts['escalated']}）/ "
        f"结构化差异只引 hunk {now_counts['hunk_only']} 次（上次 {then_counts['hunk_only']}）",
        "          ↑ 以上只是提示，不算分、不设阈值；是否退步由你看下面的新旧依据对照",
    ]
    # 依据对照：basis **全文**并列，不摘要化（§5.3 明确要求）
    lines.append("[依据对照] 同类判断的依据全文（直接读归档记录，不摘要化）：")
    shared = sorted(now_kinds & then_kinds)
    if not shared:
        lines.append("          无同类判断可比")
    for kind in shared:
        now_items = _shared_kind_items(task, kind)
        then_items = _shared_kind_items(previous, kind)
        now_item = now_items[-1] if now_items else {}
        then_item = then_items[-1] if then_items else {}
        lines.append(f"          · {kind}")
        lines.append(f"            上次 basis：{then_item.get('basis')}")
        lines.append(f"            本次 basis：{now_item.get('basis')}")
        lines.append(f"            evidence_refs：上次 {then_item.get('evidence_refs') or []}"
                     f" → 本次 {now_item.get('evidence_refs') or []}")
    return lines



def render_preview(task, facts=None, sampling_line=None, root=None):
    """收工预览（一屏）：计数必须显式（含"不确定 0"），AI 的说法不替代计数。"""
    facts = facts or skeleton_ids(task)
    judgments = [item for item in task.get("judgments") or [] if isinstance(item, dict)]
    by_kind = {}
    for item in judgments:
        by_kind.setdefault(item.get("kind"), []).append(item)
    unsure = [item for item in judgments
              if item.get("kind") == "归属" and str(item.get("decision") or "").lower().startswith("不确定")]
    rejected = facts.get("rejected_unresolved") or []
    escalated = pending_escalations(task)
    rule_files_approved = any(
        str(item.get("decision") or "").startswith("人确认") for item in judgments
        if isinstance(item, dict) and item.get("kind") == "规则文件")
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
    listed = facts.get("anchor_parts")
    if listed is None:
        # 不是"没有不变项"，是"清单不可得"——两种状态不能长得一样
        lines.append("[不变]    字段清单不可得（锚点计算失败）；不代表没有变化")
        parts = []
    else:
        parts = [name for name in listed if name not in drift_where]
    if parts:
        lines.append(f"[不变]    {len(parts)} 项实质字段未变：{'、'.join(sorted(parts)[:6])}"
                     + ("…" if len(parts) > 6 else ""))
    prefs = facts.get("prefs") or {}
    if prefs:
        shown = "、".join(f"{kind}={value}" for kind, value in sorted(prefs.items()))
        lines.append(f"[偏好]    {shown}（仅本机）")
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
    # ---- §5.3 预览余下五段（数据都来自任务记录，属展示层）----------------------
    # [扩面]：本次新增的文件，标注来源（哪条判断/哪个 finding 带出来的）
    added_paths = [item for item in (facts.get("new_paths") or []) if item]
    if added_paths:
        lines.append(f"[扩面]    {len(added_paths)} 个新文件："
                     + "、".join(str(item.get("path")) + (f"←{item['from']}" if item.get("from") else "")
                                 for item in added_paths[:6])
                     + ("…" if len(added_paths) > 6 else ""))
    else:
        in_scope = facts.get("new_in_scope") or 0
        lines.append("[扩面]    0 个面外新文件"
                     + (f"（面内新增 {in_scope} 个，见 [规模]）" if in_scope else ""))
    # [规则文件]：仓库级规则文件一旦改动会影响后续所有任务，必须单列（集合来自 protocol）
    rule_files = [item for item in (facts.get("repo_rule_files") or []) if item]
    if rule_files:
        lines.append(f"[规则文件] {len(rule_files)} 项：{'、'.join(rule_files[:6])}"
                     "——改变后续所有任务的环境" + ("  ← 需你复核" if not rule_files_approved else ""))
    # [缺口]：审查缺口（uncovered 轴 / 未覆盖项）不是失败，但必须可见
    gaps = [item for item in (facts.get("requirement_gap_findings") or []) if item]
    if gaps:
        lines.append(f"[缺口]    {len(gaps)} 条："
                     + "、".join(str(item.get("axis") or item.get("reason")) for item in gaps[:4]))
    else:
        lines.append("[缺口]    无")
    # [未核实]：标注为 supporting / 未跑到的验收项必须写原因与补偿
    unverified = [item for item in (facts.get("unverified") or []) if item]
    if unverified:
        lines.append(f"[未核实]  {len(unverified)} 项：" + "；".join(
            f"{item.get('id')}（原因={item.get('reason')}；补偿={item.get('compensation')}）"
            for item in unverified[:3]) + "  ← 需你复核")
    # [有效性]：本轮报告是否仍有效（内容变了/锚点失效 → 作废）
    rounds = [entry for entry in ((task.get("reviews") or {}).get("launches") or []) if isinstance(entry, dict)]
    invalid = [entry for entry in rounds if entry.get("invalidated") or entry.get("stale")]
    if rounds:
        lines.append(f"[有效性]  {len(rounds)} 轮报告；作废 {len(invalid)} 轮"
                     + (f"（轮次 {'、'.join(str(item.get('round')) for item in invalid)}）" if invalid else ""))
    for kind in KINDS:
        entries = by_kind.get(kind)
        if not entries:
            continue
        lines.append(f"[{kind}]    {len(entries)} 条")
        for item in entries:
            flag = " [补]" if item.get("backfill") else ""
            lines.append(f"          · {item.get('decision')}{flag} ← {item.get('basis')}")
    if root:
        lines.extend(quality_comparison(root, task))
    return "\n".join(lines) + "\n"
