"""sampling.py — 试点期判断抽样的确定性选样与统计（v42 §0.2，按原文实现）。

定位（§0.2）：抽样只回答"这类判断最近有没有明显出错"，**不证明整体判断质量**；
它是试点期手段，试点结束由人决定保留/降频/取消。

三条不可让 AI 影响的性质：
1. **候选来自事实骨架**（不是 AI 的 judgments）：AI 增减 judgments 不改变事件池；
2. **选样可复算**：`sha256(seed + 类名 + 序号) % 事件数`，种子在进入收工流程时冻结；
3. **冻结的是事件集**：补写可以继续新增 judgment，但骨架事件与种子已固定，选样结果不变。

实现取舍（§0.2 的"实现降级路径"**未启用**）：一次性强制占位按原文实现——强化类在
进入强化期后的下一个"该类有事件"的任务强制占第 1 条（仅一次）；若该任务收尾有 open
blocking，则"关闭"类仍占第 1 条，该强化类由第 2 条承接。若后续发现事件池与强化期状态
耦合出歧义，允许按原文删去占位、只保留「每任务固定 2 条 + 风险优先级 + 人评」。
"""

from __future__ import annotations

import hashlib

from . import records

# §0.2：候选来源（类 → 骨架字段）
EVENT_SOURCES = {
    "归属": "changed_paths",
    "关闭": "closures",
    "沿用": "drift_diffs",
    "扩面": "fix_scope",
    "标准变更": "standard_changes",
    "缺口": "requirement_gap_findings",
    "未核实": "unverified",
    "规模": "cumulative",
}

# §0.2：第 1 条的默认风险序（同级按该类历史失败记录排序，见 `priority`）
DEFAULT_PRIORITY = ("标准变更", "扩面", "关闭")
BUDGET_PER_TASK = 2


def _digest(seed, name, index):
    return hashlib.sha256(f"{seed}{name}{index}".encode("utf-8")).hexdigest()


def _pick(seed, name, index, events):
    if not events:
        return None
    return events[int(_digest(seed, name, index), 16) % len(events)]


def events_of(skeleton):
    """从事实骨架取事件池（AI 不能决定事件是否进池）。"""
    pool = {}
    for name, source in EVENT_SOURCES.items():
        value = skeleton.get(source)
        if source == "cumulative":
            pool[name] = [] if value is None else [f"cumulative:{value}"]
        elif isinstance(value, list):
            entries = []
            for item in value:
                if isinstance(item, dict):
                    identifier = (item.get("finding_id") or item.get("id") or item.get("where")
                                  or item.get("path") or item.get("id"))
                    entries.append(str(identifier if identifier is not None else item))
                else:
                    entries.append(str(item))
            pool[name] = entries
        else:
            pool[name] = []
    return pool


def priority(classes, history, open_blocking):
    """第 1 条的类别序：open blocking → 关闭优先；其余按默认序 + 历史失败 + 强化期。"""
    history = history or {}

    def rank(name):
        strengthened = 0 if (history.get(name) or {}).get("strengthened") else 1
        failures = (history.get(name) or {}).get("failures") or 0
        if open_blocking and name == "关闭":
            tier = 0
        elif name in DEFAULT_PRIORITY:
            tier = 1 + DEFAULT_PRIORITY.index(name)
        else:
            tier = 10
        return (strengthened, tier, -failures, name)

    return sorted(classes, key=rank)


def select(seed, pool, history=None, *, first_task=False, open_blocking=False):
    """返回本次抽样的两类（或首任务 1 条），并给出"为什么"（§0.2 预览先声明）。"""
    history = history or {}
    classes = [name for name in EVENT_SOURCES if pool.get(name)]
    budget = 1 if first_task else BUDGET_PER_TASK
    picks = []
    uncovered = [name for name in EVENT_SOURCES if not pool.get(name)]

    if first_task:
        name = "关闭" if pool.get("关闭") else "归属"
        event = _pick(seed, name, 0, pool.get(name) or [])
        if event is not None:
            picks.append({"class": name, "event": event,
                          "rule": "首任务只抽 1 条：优先关闭类，无关闭事件改抽归属类"})
        return {"seed": seed, "budget": budget, "picks": picks, "uncovered": uncovered,
                "classes_with_events": classes}

    ordered = priority(classes, history, open_blocking)
    if ordered:
        name = ordered[0]
        event = _pick(seed, name, 0, pool[name])
        reason = ("收尾存在 open blocking：关闭类优先" if (open_blocking and name == "关闭")
                  else "最高危类优先（强化期 > 标准变更 > 扩面 > 关闭 > 其余，同级按历史失败）")
        picks.append({"class": name, "event": event, "rule": reason})

    if budget >= 2 and classes:
        obligation = [name for name in ordered if (history.get(name) or {}).get("strengthened") and pool.get(name)]
        if obligation:
            name = obligation[0]
            taken = picks[0]["event"] if picks and picks[0]["class"] == name else None
            candidate, shift = _pick(seed, name, 1, pool[name]), 2
            while candidate is not None and candidate == taken and shift < 6:
                candidate = _pick(seed, name, shift, pool[name])
                shift += 1
            if candidate is None or candidate == taken:
                picks.append({"class": name, "event": None,
                              "rule": "强化义务无可履行事件（该类只有一个事件且已被抽走）："
                                      "顺延到下一个任务，不重复抽、不阻塞归档"})
            else:
                picks.append({"class": name, "event": candidate,
                              "rule": "第 2 条履行尚未完成的强化义务（取该类的另一个事件）"})
        else:
            index = int(_digest(seed, "class-2", 0), 16) % len(classes)
            name = classes[index]
            candidate = _pick(seed, name, 1, pool[name])
            shift = 2
            while picks and candidate is not None and candidate == picks[0]["event"] and shift < 5:
                candidate = _pick(seed, name, shift, pool[name])
                shift += 1
            picks.append({"class": name, "event": candidate,
                          "rule": "第 2 条按 sha256(seed+\"class-2\") 选类，再按序号 1 取事件（与第 1 条只要求事件不同）"})
    return {"seed": seed, "budget": budget, "picks": picks, "uncovered": uncovered,
            "classes_with_events": classes}


def freeze(task, skeleton, seed=None):
    """进入收工流程时冻结事件集与种子（写进**任务记录**，committed，可复算）。"""
    records_seed = seed or records.H("wf-sampling-seed-v1",
                                     {"task": task.get("id"), "at": records.now_str()})
    pool = events_of(skeleton)
    frozen = {"seed": records_seed, "events": pool, "frozen_at": records.now_str()}
    task["sampling"] = dict(task.get("sampling") or {}, **frozen)
    return frozen


def frozen(task):
    return (task.get("sampling") or {}) if isinstance(task.get("sampling"), dict) else {}


def select_for(task, history=None, *, first_task=False, open_blocking=False):
    """用已冻结的种子与事件集选样（冻结后 AI 再改 judgments 也不影响结果）。"""
    state = frozen(task)
    if not state.get("seed") or not isinstance(state.get("events"), dict):
        return None
    return select(state["seed"], state["events"], history,
                  first_task=first_task, open_blocking=open_blocking)


def report(history):
    """`wf sampling report` 的一屏：按类的样本/失败/连续无失败/层级，样本不足显式提示。"""
    lines = ["[判断抽样] 试点期统计（样本不足时门槛不激活，未命中不等于没问题）", ""]
    lines.append(f"{'类':<6}{'样本':>5}{'失败':>5}{'连续无失败':>8}  层级")
    for name in EVENT_SOURCES:
        item = history.get(name) or {}
        samples = item.get("samples") or 0
        failures = item.get("failures") or 0
        streak = item.get("consecutive_ok") or 0
        level = item.get("level") or "指引"
        note = "" if samples >= 10 else f"  （样本 {samples}<10，门槛未激活）"
        if item.get("strengthened_ended"):
            note += "  该类强化抽样期已结束"
        lines.append(f"{name:<6}{samples:>5}{failures:>5}{streak:>8}  {level}{note}")
    return "\n".join(lines) + "\n"


def record_result(task, picks, evaluations=None):
    """把本次抽样结果写进任务记录（committed）：结果与"抽到无判断=漏报失败"都留痕。"""
    state = dict(frozen(task))
    results = list(state.get("results") or [])
    evaluations = evaluations or {}
    for pick in picks:
        if not pick.get("event"):
            continue
        verdict = evaluations.get(f"{pick['class']}:{pick['event']}")
        entry = {"class": pick["class"], "event": pick["event"], "at": records.now_str()}
        if verdict == "missing":
            entry["failed"] = True
            entry["reason"] = "抽到无对应判断（漏报）"
        elif verdict == "wrong":
            entry["failed"] = True
            entry["reason"] = "结论或依据不成立"
        elif verdict == "ok":
            entry["failed"] = False
        results.append(entry)
    state["results"] = results
    task["sampling"] = state
    return state


def history_from_tasks(tasks):
    """按类累计样本/失败/连续无失败（只从记录重建，不设运行态标记）。"""
    history = {name: {"samples": 0, "failures": 0, "consecutive_ok": 0,
                      "strengthened": False, "level": "指引"} for name in EVENT_SOURCES}
    for task in tasks or []:
        state = frozen(task)
        for entry in state.get("results") or []:
            name = entry.get("class")
            if name not in history:
                continue
            item = history[name]
            item["samples"] += 1
            if entry.get("failed"):
                item["failures"] += 1
                item["consecutive_ok"] = 0
                item["strengthened"] = True          # 首次失败 → 该类进入强化抽样期
            else:
                item["consecutive_ok"] += 1
                if item["consecutive_ok"] >= 5 and item["samples"] >= 10:
                    item["level"] = "可选"
        # 期满前置（§0.2）：人以"已看过预览"声明后，已进入强化期的类恢复常规抽样；
        # 框架不检测人是否真看了（不追踪停留/翻页/点击）——这是明确交给人的取舍。
        if state.get("reviewed_by_human"):
            for name, item in history.items():
                if item.get("strengthened"):
                    item["strengthened"] = False
                    item["strengthened_ended"] = True
    return history


# --------------------------------------------------------------------------
# 漏报补写（§0.2「抽到无判断＝漏报失败」）与期满前置
# --------------------------------------------------------------------------


def judgment_for(pick, judgments):
    """该事件下是否存在对应判断（按 kind 匹配 + evidence_refs 指向该事件）。"""
    if not pick.get("event"):
        return None
    for item in judgments or []:
        if not isinstance(item, dict) or item.get("kind") != pick.get("class"):
            continue
        refs = [str(ref).split("@", 1)[0] for ref in item.get("evidence_refs") or []]
        if str(pick["event"]) in refs or f"f:{pick['event']}" in refs or f"p:{pick['event']}" in refs:
            return item
    return None


def backfill_status(picks, judgments, backfill_limit=2):
    """漏报补写的状态：缺哪些、补了哪些、（超额时）是否已到二次失败口径。

    恢复路径（§0.2）：AI 补写**两条**——`kind=漏报说明` 引被漏事件 + `kind=<该类>` 的新判断，
    两条带 `backfill: true`、**不用 `supersedes`**；原失败记录保留；每任务补写复核 ≤2 条。
    """
    missing, backfilled = [], []
    for pick in picks or []:
        if not pick.get("event"):
            continue
        found = judgment_for(pick, judgments)
        if found is not None:
            continue
        missing.append({"class": pick["class"], "event": pick["event"]})
        notes = [item for item in judgments or []
                 if isinstance(item, dict) and item.get("backfill") and item.get("kind") == "漏报说明"]
        fixes = [item for item in judgments or []
                 if isinstance(item, dict) and item.get("backfill") and item.get("kind") == pick["class"]]
        if notes and fixes:
            backfilled.append({"class": pick["class"], "event": pick["event"], "ok": True})
    over_limit = len(missing) > backfill_limit
    return {"missing": missing, "backfilled": backfilled, "count": len(missing),
            "limit": backfill_limit, "over_limit": over_limit,
            "note": ("每任务补写复核 ≤2 条；超出按「二次失败」处理：记失败 + 写根因 + 由人裁，不自动升内核"
                     if over_limit else "")}


def mark_reviewed(task, *, by="human", quote=None):
    """人的声明"已看过预览"——强化抽样期的**结束前置**（框架不机械检测）。"""
    state = dict(frozen(task))
    state["reviewed_by_human"] = {"at": records.now_str(), "by": by, "quote": quote}
    task["sampling"] = state
    return state["reviewed_by_human"]
