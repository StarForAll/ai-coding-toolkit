"""gates.py — required 步骤投影、回执与最终门禁（机制稿 §11.2、§11.3、§9.3）。

所有判定只读已有记录与工作树事实；不新增状态值或原因码。
"""

from __future__ import annotations

import os

from . import actions, codes, fingerprint, records, scope
from .paths import join

TASK_KINDS = ("ordinary", "initialize", "bootstrap")

# (id, mode, condition, due) — 机制稿 §11.2 首版固定行
TASK_STEP_SPECS = (
    ("task.plan-approved", "once", "all", "before_execute"),
    ("task.spec-loaded", "repeatable", "all", "before_execute"),
    ("task.work-satisfied", "once", "all", "before_check"),
    ("task.check-passed", "repeatable", "all", "before_archive"),
    ("task.tdd-verified", "repeatable", "tdd", "before_archive"),
    ("task.review-passed", "repeatable", "complex", "before_archive"),
    ("task.knowledge-disposed", "once", "all", "before_archive"),
    ("task.retrospective-done", "once", "retrospective", "before_archive"),
    ("task.changes-persisted", "repeatable", "all", "before_archive"),
    # §0.2 抽样是试点期自验证手段而非交付承诺（2026-11-21 降档）：
    # 不再作为归档硬门禁；未跑抽样只降为提示（check_next_hint 与收工预览 facts），
    # 试点结束由人决定，届时一次代码改动删除提示并发版。
    ("task.archived", "once", "all", "after_archive"),
)

RULE_CLASS_STEPS = (
    "task.check-passed",
    "task.tdd-verified",
    "task.review-passed",
    "task.changes-persisted",
)

# 机制稿 §11.3 状态动作的固定名称（scope=control）
CONTROL_OPERATIONS = (
    "task.create",
    "task.transition",
    "task.attribute",
    "baseline.apply",
    "spec.update",
    "task.curate",
    "task.knowledge-dispose",
    "task.retrospect",
    "task.check",
    "review.launch",
    "review.import",
    "review.decide",
    "task.reassess",
    "session.bind",
    "task.pause",
    "session.stop",
    "writer.acquire",
    "writer.release",
    "writer.handover.begin",
    "writer.handover.accept",
    "definition.prepare",
    "run.advance",
    "run.terminate",
    "task.archive",
    "dependency.change",
    "task.rework",
    "task.replace",
    "task.abandon",
    "asset.apply",
    "repair.apply",
    "uninstall.apply",
)

DUE_ORDER = {"before_execute": 0, "before_check": 1, "before_archive": 2, "after_archive": 3, "operation_end": 4}

# control 步骤 → 承接它的公开子命令；repair/uninstall 由引导层转交（见 BOOTSTRAP_ENTRIES）
CONTROL_STEP_COMMANDS = {
    "task.create": "task-new",
    "task.transition": "task-start",
    "task.attribute": "task-attribute",
    "baseline.apply": "baseline-apply",
    "spec.update": "spec-update",
    "task.curate": "task-curate",
    "task.knowledge-dispose": "task-knowledge",
    "task.retrospect": "task-retrospect",
    "task.check": "task-check",
    "review.launch": "review-launch",
    "review.import": "review-import",
    "review.decide": "review-decide",
    "task.reassess": "task-reassess",
    "session.bind": "bind",
    "task.pause": "task-pause",
    "session.stop": "stop",
    "writer.acquire": "writer",
    "writer.release": "writer",
    "writer.handover.begin": "writer-handover",
    "writer.handover.accept": "writer-handover",
    "definition.prepare": "definition",
    "run.advance": "run",
    "run.terminate": "run",
    "task.archive": "archive",
    "dependency.change": "dep",
    "task.rework": "task-rework",
    "task.replace": "task-replace",
    "task.abandon": "task-abandon",
    "asset.apply": "upgrade",
    "repair.apply": "repair",
    "uninstall.apply": "uninstall",
}

# 由引导层转交、不在语义层 COMMANDS 表中的独立入口
BOOTSTRAP_ENTRIES = ("repair", "uninstall")

# 交付轮次（2026-11-05 人裁 B）：步骤 → 交付轮次；未列出的即首轮交付。
# 判据：清单声明"本轮已交付"的步骤，其承接命令不得是能力不可用桩；
# 声明为后续轮次的步骤只报告、不阻断启用（"未交付轮次的可预期不可达"）。
STEP_DELIVERY_ROUND = {
    "control.definition.prepare": 2,
    "control.run.advance": 2,
    "control.run.terminate": 2,
    "control.dependency.change": 2,
    "control.task.rework": 2,
    "control.task.replace": 2,
    "control.asset.apply": 3,
}
CURRENT_DELIVERY_ROUND = 1

# 固定分派表：required step id → 处理器（task 走 verify_step；control 走对应子命令）
HANDLERS = {step_id: "verify_step" for step_id, _mode, _condition, _due in TASK_STEP_SPECS}
for _operation, _command in CONTROL_STEP_COMMANDS.items():
    HANDLERS[f"control.{_operation}"] = _command




# --------------------------------------------------------------------------
# 重复调试计数（机制稿 §1.3 双源合并、§8.1 阈值、§11.2 倍数与裁定）
# --------------------------------------------------------------------------


DEBUG_THRESHOLD_DEFAULT = 3


def _failed_checks_for(task, verification_id):
    """check_history 中该 verification_id 的 failed 最终结果条目（每 check 一次）。"""
    entries = []
    for check in task.get("check_history") or []:
        if check.get("result") != "fail":
            continue
        for command in check.get("commands") or []:
            if command.get("verification_id") == verification_id and command.get("status") == "failed":
                entries.append({"check_id": check.get("id"), "verification_id": verification_id})
                break
    return entries


def merged_failures(task, verification_id):
    """双源合并：check_history failed 条目数 + 声明 counted 之和 − dedupe_refs 条目数。"""
    base = len(_failed_checks_for(task, verification_id))
    declarations = [entry for entry in (task.get("execution") or {}).get("debug_declarations") or []
                    if entry.get("verification_id") == verification_id]
    counted = sum(int(entry.get("counted") or 0) for entry in declarations)
    deduped = sum(len(entry.get("dedupe_refs") or []) for entry in declarations)
    return base + counted - deduped


def debug_pending(task, threshold=None):
    """返回未裁定倍数清单（阻断归档的事实面）与每个 verification_id 的合并累计。"""
    if threshold is None:
        threshold = DEBUG_THRESHOLD_DEFAULT
    verification_ids = set()
    for entry in (task.get("execution") or {}).get("debug_declarations") or []:
        if entry.get("verification_id"):
            verification_ids.add(entry["verification_id"])
    for check in task.get("check_history") or []:
        for command in check.get("commands") or []:
            if command.get("status") == "failed" and command.get("verification_id"):
                verification_ids.add(command["verification_id"])
    rulings = {}          # (verification_id, multiple) -> choice；解析失败的不计入
    rulings_raw = {}      # 原始 subject -> choice，供触发事实引用
    for decision in (task.get("execution") or {}).get("human_decisions") or []:
        subject = str(decision.get("subject", ""))
        if not subject.startswith("debug-ruling-"):
            continue
        rulings_raw[subject] = decision.get("choice")
        key = parse_debug_ruling(subject)
        if key is not None:
            rulings[key] = decision.get("choice")
    pending = []
    totals = {}
    for verification_id in sorted(verification_ids):
        merged = merged_failures(task, verification_id)
        totals[verification_id] = merged
        multiples = merged // threshold if threshold else 0
        for multiple in range(1, multiples + 1):
            # 精确比较 (verification_id, multiple)：前缀匹配会让「第 1 倍」被「第 10 倍」覆盖
            if (verification_id, multiple) not in rulings:
                pending.append({"verification_id": verification_id, "multiple": multiple,
                                "merged": merged, "threshold": threshold})
    return {"pending": pending, "merged": totals, "rulings": rulings, "rulings_raw": rulings_raw}


def parse_debug_ruling(subject):
    """`debug-ruling-<verification_id>-<multiple>` → (verification_id, multiple)；非法返回 None。

    verification_id 自身可能含连字符，因此按"最后一个 `-` 后是正整数"切分。
    """
    if not subject.startswith("debug-ruling-"):
        return None
    body = subject[len("debug-ruling-"):]
    head, sep, tail = body.rpartition("-")
    # 只认 ASCII 十进制数字：`²` 之类 isdigit() 为真但 int() 会抛，不能当倍数
    if not sep or not head or not tail or not (tail.isascii() and tail.isdigit()):
        return None
    multiple = int(tail)
    if multiple <= 0:
        return None
    return (head, multiple)


def debug_repeat_triggers(task, threshold=None):
    """已裁定为「同一问题」的倍数构成 debug_repeat 触发事实。"""
    info = debug_pending(task, threshold)
    triggers = []
    for subject, choice in (info.get("rulings_raw") or {}).items():
        if choice == "同一问题":
            triggers.append({"kind": "debug_repeat", "ref": subject})
    return triggers


def required_step_specs():
    specs = {}
    for step_id, mode, condition, due in TASK_STEP_SPECS:
        specs[step_id] = {
            "scope": "task",
            "applies": {"task_kinds": list(TASK_KINDS), "condition": condition},
            "due": due,
            "mode": mode,
            "delivery_round": STEP_DELIVERY_ROUND.get(step_id, CURRENT_DELIVERY_ROUND),
        }
    for operation in CONTROL_OPERATIONS:
        specs[f"control.{operation}"] = {
            "scope": "control",
            "applies": {"operation": operation},
            "due": "operation_end",
            "mode": "repeatable",
            "delivery_round": STEP_DELIVERY_ROUND.get(f"control.{operation}", CURRENT_DELIVERY_ROUND),
        }
    return specs


def supported_keys():
    return set(HANDLERS)


def _stub_rounds(commands):
    """从命令面取"能力不可用桩"的交付轮次（命令名 → 轮次）。"""
    rounds = {}
    if isinstance(commands, dict):
        for name, handler in commands.items():
            round_no = getattr(handler, "wf_delivery_round", None)
            if isinstance(round_no, int):
                rounds[name] = round_no
    return rounds


def support_report(manifest, commands, bootstrap_entries=()):
    """核对发行声明的 required_steps 与固定分派表、命令面是否一一对应。

    2026-11-05（人裁 B）：除"处理面存在"外，还核对**交付轮次可达**——
    清单声明 `delivery_round <= manifest.delivery_round` 的步骤，其承接命令不得是
    "能力不可用"桩；声明为后续轮次的步骤只报告覆盖情况，不阻断启用。
    """
    available = set(commands) | set(bootstrap_entries)
    stub_rounds = _stub_rounds(commands)
    problems = []
    current_round = manifest.get("delivery_round")
    if (not isinstance(current_round, int) or isinstance(current_round, bool)
            or current_round <= 0):
        problems.append({"required_step": "manifest.delivery_round",
                         "reason": "missing or invalid; cannot decide delivery reachability"})
        current_round = None
    declared = [step.get("id") for step in manifest.get("required_steps") or [] if step.get("id")]
    for step in manifest.get("required_steps") or []:
        step_id = step.get("id")
        if not step_id:
            continue
        handler = HANDLERS.get(step_id)
        if handler is None:
            problems.append({"required_step": step_id, "reason": "no fixed handler"})
            continue
        declared_round = step.get("delivery_round")
        if (not isinstance(declared_round, int) or isinstance(declared_round, bool)
                or declared_round <= 0):
            problems.append({"required_step": step_id, "reason": "delivery_round missing or invalid"})
        if step_id.startswith("control."):
            if handler not in available:
                if handler in BOOTSTRAP_ENTRIES:
                    # 引导层独立入口（repair/uninstall）：不在语义层命令表里，属预期形状，
                    # 报告时显式标注，避免被复审读成真缺口（2026-11-05 第七轮复审）。
                    problems.append({"required_step": step_id, "reason": "bootstrap-layer entry (expected)",
                                     "handler": handler})
                else:
                    problems.append({"required_step": step_id,
                                     "reason": f"handler entry missing: {handler}"})
            stub_round = stub_rounds.get(handler)
            if (stub_round is not None and isinstance(declared_round, int) and current_round is not None
                    and declared_round <= current_round):
                problems.append({
                    "required_step": step_id,
                    "reason": (f"declared delivered in round {declared_round} but its command "
                               f"`{handler}` is a capability stub (round {stub_round})"),
                })
        elif not callable(globals().get(handler)):
            problems.append({"required_step": step_id, "reason": f"handler callable missing: {handler}"})
    for step_id in sorted(set(HANDLERS) - set(declared)):
        problems.append({"required_step": step_id, "reason": "handler not declared by release"})
    return problems


# --------------------------------------------------------------------------
# 适用集合与投影 P
# --------------------------------------------------------------------------


def retrospective_triggers(root, task, threshold=None):
    """从既有判定记录重建触发事实集合（不落第二持久清单）。"""
    from . import tasks as tasks_mod

    triggers = []
    task_id = task.get("id")
    for path, other in tasks_mod.iter_tasks(root):
        if other.get("rework_of") == task_id:
            triggers.append({"kind": "rework", "ref": other.get("id")})
    reviews = task.get("reviews") or {}
    for attempt in reviews.get("attempts") or []:
        if attempt.get("outcome") == "fail":
            triggers.append({"kind": "review_fail", "ref": f"attempt-{attempt.get('number')}"})
    result = reviews.get("result") or {}
    if result.get("verdict") == "fail":
        triggers.append({"kind": "review_fail", "ref": f"round-{result.get('round')}"})
    for trigger in debug_repeat_triggers(task, threshold):
        triggers.append(trigger)
    unique = {}
    for trigger in triggers:
        unique[(trigger["kind"], trigger["ref"])] = trigger
    return sorted(unique.values(), key=lambda item: (item["kind"], str(item["ref"])))


def declared_step_specs(ctx):
    """从已校验发行清单取「有哪些义务」；缺失/不支持/矛盾一律拒绝，不退回代码常量。

    处理器表（HANDLERS）只说明「谁来算」，义务集合以清单为唯一机读来源（机制稿 §11.2）。
    """
    from . import assets as assets_mod
    from . import cli as cli_mod

    def _reject(reason, **facts):
        raise cli_mod.CliError("WF_ASSET_DECISION", dict(facts, reason=reason),
                               next_="核对发行清单与运行时处理器后重试；不按旧集合放行")

    try:
        manifest = assets_mod.load_installed_manifest(ctx.root)
    except assets_mod.AssetError as exc:
        _reject("installed manifest unusable", detail=str(exc))
    declared = assets_mod.required_steps(manifest)
    by_id = {}
    for entry in declared:
        # 声明本身先完整校验：结构不全、未知步骤、重复 id 都不能靠跳过或覆盖被接受
        if not isinstance(entry, dict):
            _reject("release declares a non-object required step", entry=entry)
        step_id = entry.get("id")
        if not step_id:
            _reject("release declares a required step without id", entry=entry)
        if step_id not in HANDLERS:
            _reject("release declares unknown required step", step_id=step_id)
        if step_id in by_id:
            _reject("release declares the same required step twice", step_id=step_id)
        if not entry.get("mode"):
            _reject("required step declaration lacks mode", step_id=step_id)
        if not entry.get("due"):
            _reject("required step declaration lacks due", step_id=step_id)
        by_id[step_id] = entry
    missing = sorted(set(HANDLERS) - set(by_id))
    if missing:
        _reject("release does not declare steps that handlers implement", missing=missing)
    ordered = []
    for step_id, mode, condition, due in TASK_STEP_SPECS:
        entry = by_id[step_id]
        scope = entry.get("scope", "task")
        if scope != "task":
            # 任务步骤被声明成别的 scope 等于把门禁移出义务集合，必须判矛盾而不是跳过
            _reject("release contradicts handler", step_id=step_id,
                    declared_scope=scope, handler_scope="task")
        applies = entry.get("applies") or {}
        declared_condition = applies.get("condition", condition)
        if declared_condition != condition:
            _reject("release contradicts handler", step_id=step_id,
                    declared_condition=declared_condition, handler_condition=condition)
        if entry.get("mode", mode) != mode or entry.get("due", due) != due:
            _reject("release contradicts handler", step_id=step_id,
                    declared_mode=entry.get("mode"), declared_due=entry.get("due"),
                    handler_mode=mode, handler_due=due)
        ordered.append({"id": step_id, "mode": mode, "due": due, "condition": condition})
    return ordered


def applicable(ctx, task, rule_version=None):
    plan = task.get("plan") or {}
    complexity = plan.get("complexity")
    tdd = plan.get("tdd")
    triggers = retrospective_triggers(ctx.root, task, ctx.debug_threshold())
    selected = []
    for step in declared_step_specs(ctx):
        condition = step["condition"]
        if condition == "complex" and complexity != "complex":
            continue
        if condition == "tdd" and not tdd:
            continue
        if condition == "retrospective" and not triggers:
            continue
        selected.append(step)
    return selected


def _normalized_plan_version(task):
    from . import tasks as tasks_mod

    return tasks_mod.normalized_plan_version(task)


def compute_P(ctx, task, step_id, *, check=None, rule_version=None):
    """按 §11.2 的唯一公式给出 P（内容键）；缺失值不补。"""
    from . import check as check_mod

    plan = task.get("plan") or {}
    plan_version = _normalized_plan_version(task)
    if step_id == "task.plan-approved":
        return {"plan_version": plan_version}
    if step_id == "task.spec-loaded":
        specs = sorted(
            [{"path": entry.get("path"), "digest": entry.get("digest")} for entry in (task.get("curation") or [])
             if not entry.get("released")],
            key=lambda item: str(item["path"]).encode("utf-8"),
        )
        return {"session_key": ctx.key(required=False), "instance_id": (ctx.session(required=False) or {}).get("instance_id"),
                "specs": specs}
    if step_id == "task.work-satisfied":
        return {"plan_version": plan_version, "content_digest": check_mod.object_content_digest(ctx, task)}
    if step_id in ("task.check-passed", "task.tdd-verified", "task.review-passed"):
        current = check or task.get("check") or {}
        anchor = (current.get("anchor") or {}).get("check_anchor")
        return {"check_id": current.get("id"), "check_anchor": anchor}
    if step_id == "task.knowledge-disposed":
        specs = sorted(
            [{"path": entry.get("path"), "digest": entry.get("digest")} for entry in (task.get("curation") or [])
             if not entry.get("released")],
            key=lambda item: str(item["path"]).encode("utf-8"),
        )
        knowledge = task.get("knowledge")
        return {
            "plan_version": plan_version,
            "knowledge_digest": records.plain_digest(knowledge) if knowledge is not None else None,
            "specs": specs,
        }
    if step_id == "task.retrospective-done":
        trig = retrospective_triggers(ctx.root, task, ctx.debug_threshold())
        return {"triggers": sorted(trig, key=lambda item: (item["kind"], str(item["ref"])))}
    if step_id == "task.changes-persisted":
        return {
            "content_digest": check_mod.object_content_digest(ctx, task),
            "paths": sorted(check_mod.object_paths(ctx, task), key=lambda value: value.encode("utf-8")),
        }
    if step_id == "task.sampled":
        # 2026-11-21 降档：不再是归档门禁；保留投影给提示消费（check_next_hint/
        # 收工预览 facts 的 pilot_sampling_pending 以 selection.picks 为准）。
        from . import sampling as sampling_mod

        selection = sampling_mod.selection(task)
        return {"seed": selection["seed"], "picks": selection["picks"]}
    if step_id == "task.archived":
        return {"archive_action_id": (task.get("action") or {}).get("id")}
    raise KeyError(step_id)


def step_occurrence(task_id, step_id, projection):
    return records.H("wf-step-occurrence-v1", {"task_id": task_id, "step_id": step_id, "P": projection})


def check_result_problems(task):
    """门禁端的 Check 结构复核：与生成端共用 `check.validate_check_result()`，不另写判据。"""
    from . import check as check_mod

    return check_mod.validate_check_result(task, task.get("check") or {})


def step_anchor(rule_version, projection, rule_class):
    """机制稿 §11.2 的唯一公式：规则类 C({rule_version, P})，内容类 C(P)。"""
    if rule_class:
        return records.H("wf-step-anchor-v1", {"rule_version": rule_version, "P": projection})
    return records.H("wf-step-anchor-v1", projection)


def _receipts(task, step_id):
    return [entry for entry in (task.get("execution") or {}).get("required_steps") or [] if entry.get("id") == step_id]


def receipt_state(task, step_id, projection, rule_version):
    rule_class = step_id in RULE_CLASS_STEPS
    occurrence = step_occurrence(task.get("id"), step_id, projection)
    candidates = []
    for entry in _receipts(task, step_id):
        if entry.get("occurrence") != occurrence:
            continue
        if entry.get("result") not in ("completed", "reused"):
            continue
        if rule_class and entry.get("rule_version") != rule_version:
            continue
        candidates.append(entry)
    for entry in candidates:
        if entry.get("result") == "completed":
            return "completed", entry
    if candidates:
        return "reused", candidates[-1]
    return None, None


def _has_stale_rule_receipt(task, step_id, projection, rule_version):
    occurrence = step_occurrence(task.get("id"), step_id, projection)
    for entry in _receipts(task, step_id):
        if entry.get("occurrence") != occurrence:
            continue
        if entry.get("result") in ("completed", "reused") and entry.get("rule_version") != rule_version:
            return True
    return False


def write_receipt(task, step_id, *, mode, projection, rule_version, evidence_refs=None, skip_basis=None,
                  reused_from=None):
    execution = task.setdefault("execution", {})
    steps = execution.setdefault("required_steps", [])
    rule_class = step_id in RULE_CLASS_STEPS
    now = records.now_str()
    occurrence = step_occurrence(task.get("id"), step_id, projection)
    if reused_from is not None:
        entry = {
            "id": step_id,
            "rule_version": rule_version if rule_class else None,
            "mode": mode,
            "occurrence": occurrence,
            "result": "reused",
            "anchor": step_anchor(rule_version, projection, rule_class),
            "completed_at": reused_from.get("completed_at"),
            "checked_at": now,
            "evidence_refs": evidence_refs or [],
            "skip_basis": skip_basis,
        }
    else:
        entry = {
            "id": step_id,
            "rule_version": rule_version if rule_class else None,
            "mode": mode,
            "occurrence": occurrence,
            "result": "completed",
            "anchor": step_anchor(rule_version, projection, rule_class),
            "completed_at": now,
            "checked_at": now,
            "evidence_refs": evidence_refs or [],
            "skip_basis": None,
        }
    steps.append(entry)
    return entry


# --------------------------------------------------------------------------
# 共享子判定（⑥）：步骤面与 repair_scope 共用，判据只在这里实现一次
# --------------------------------------------------------------------------


def _judgment(valid, code, facts, blocker, **extra):
    return dict({"valid": valid, "code": code, "facts": facts,
                 "blockers": [blocker] if blocker else []}, **extra)


def check_validity(ctx, task, *, rule_version=None):
    """Check 是否仍然有效（自 check-passed 原样提取，逐分支对齐 `gates.py:631-660`）。

    返回 `{valid, code, facts, blockers}`：`blockers` 是短原因 token，供
    `repair_scope.conclusion.check_blockers` 直接呈现——不另设第二套判据。
    """
    from . import tasks as tasks_mod

    current_check = task.get("check") or {}
    saved_rule = (current_check.get("anchor") or {}).get("rule_version")
    current_rule = rule_version or ctx.rule_version()
    if saved_rule and saved_rule != current_rule:
        return _judgment(False, "WF_CHECK_STALE", {
            "reason": "check was produced under different framework rules",
            "saved_rule_version": saved_rule,
            "current_rule_version": current_rule}, "rule_version")
    anchor = (current_check.get("anchor") or {}).get("check_anchor")
    now_anchor = tasks_mod.current_check_anchor(ctx, task)
    if now_anchor.get("error"):
        code, facts = now_anchor["error"]
        return _judgment(False, code, facts, "anchor_unavailable")
    if (current_check.get("invalidated") or {}).get("at"):
        # 受控回 check 时登记的失效事实：旧 pass 不再有效，必须重新 Check
        return _judgment(False, "WF_CHECK_STALE", {
            "reason": "check was invalidated by a later change",
            "invalidated": current_check.get("invalidated")}, "invalidated")
    if current_check.get("result") != "pass" or not anchor:
        return _judgment(False, "WF_CHECK_FAILED",
                         {"check": current_check.get("id"), "result": current_check.get("result")},
                         "result_not_pass" if current_check.get("result") != "pass" else "anchor_missing")
    if anchor != now_anchor.get("anchor"):
        return _judgment(False, "WF_CHECK_STALE",
                         {"saved": anchor, "current": now_anchor.get("anchor")}, "anchor_drift")
    # 结构复核：pass + 锚点一致不等于"检查真的做过"（机制稿 §3.5、§11.2 证据列）
    problems = check_result_problems(task)
    if problems:
        return _judgment(False, "WF_CHECK_FAILED", {"reason": "check result lacks required evidence",
                                                    "problems": problems}, "structure_problems")
    return _judgment(True, None, {}, None)


def review_binding(ctx, task, *, result=None):
    """审查结论是否仍绑定当前 Check（自 review-passed 原样提取 + ⑥ 新增 CLI 校验）。

    `binding` = `result.check_id == check.id`
                 ∧ 结论至少引用一份已导入报告
                 ∧ 引用报告 `result_digest == recorded == 文件当前摘要`
                 ∧ 结论所在轮的 `implementation_cli` == 最新 launch 的 `implementation_cli`

    不含 `verdict == "pass"`：verdict 是独立事实（判 fail 的结论也可能仍绑定当前 Check）。
    """
    from . import review as review_mod

    reviews = task.get("reviews") or {}
    result = result if result is not None else (reviews.get("result") or {})
    check = task.get("check") or {}
    if result.get("check_id") != check.get("id"):
        return _judgment(False, "WF_REVIEW_INVALID",
                         {"reason": "review result is not bound to current check"}, "check_id_changed",
                         binding=False)
    # 结论引用的报告必须仍是该轮/该槽位的有效导入：换了报告，旧 pass 不再有效（机制稿 §9.2）
    imported = {(int(entry.get("round") or 0), entry.get("slot")): entry.get("report_digest")
                for entry in reviews.get("imported") or []}
    cited = result.get("imported") or []
    if not cited:
        # 门禁对空引用是独立拒绝；漏掉它会让空引用的结论算出 binding == true
        return _judgment(False, "WF_REVIEW_INVALID",
                         {"reason": "review result cites no imported reports"}, "no_cited_reports",
                         binding=False)
    # 三重核对：结论引用的摘要 == 记录里的导入摘要 == **报告文件当前实际摘要**
    paths = {(int(item.get("round") or 0), item.get("slot")): item.get("report_path")
             for item in reviews.get("imported") or []}
    stale, unreadable = [], []
    for entry in cited:
        key = (int(result.get("round") or 0), entry.get("slot"))
        recorded = imported.get(key)
        actual = None
        rel = paths.get(key)
        if rel:
            actual, read_cause, read_reason = records.file_digest_state(join(ctx.root, rel))
            if read_cause == "unreadable":
                # ⑥ C1：摘要读取的权限/IO 故障按「读不到」归因，不抛出
                unreadable.append({"slot": entry.get("slot"), "round": key[0], "path": rel,
                                   "reason": read_reason})
                continue
        if recorded != entry.get("report_digest") or actual != entry.get("report_digest"):
            stale.append({"slot": entry.get("slot"), "round": key[0],
                          "result_digest": entry.get("report_digest"),
                          "recorded_digest": recorded, "file_digest": actual})
    if stale:
        return _judgment(False, "WF_REVIEW_INVALID", {
            "reason": "review result cites reports that are no longer the imported ones",
            "stale": stale}, "digest_mismatch", binding=False, stale=stale)
    if unreadable:
        return _judgment(False, "WF_REVIEW_INVALID", {
            "reason": "review result cites reports that cannot be read",
            "unreadable": unreadable}, "unreadable", binding=False, unreadable=unreadable)
    # ⑥ 新增：结论所在轮的实施 CLI 必须等于**最新** launch 的实施 CLI。
    # 把「已发起过新 launch 时旧 pass 仍可归档」堵在门禁上；换宿主但未 launch 看不到（§5 已披露）。
    launches = [item for item in reviews.get("launches") or [] if isinstance(item, dict)]
    conclusion_round = int(result.get("round") or 0)
    conclusion_launch = next((item for item in launches if int(item.get("round") or 0) == conclusion_round), None)
    latest_launch = max(launches, key=lambda item: int(item.get("round") or 0), default=None)
    conclusion_cli = review_mod.review_cli((conclusion_launch or {}).get("implementation_cli"))
    latest_cli = review_mod.review_cli((latest_launch or {}).get("implementation_cli"))
    if conclusion_cli and latest_cli and conclusion_cli != latest_cli:
        return _judgment(False, "WF_REVIEW_INVALID", {
            "reason": "review result was produced under a different implementation CLI",
            "round": conclusion_round, "implementation_cli": conclusion_cli,
            "latest_round": int((latest_launch or {}).get("round") or 0),
            "latest_implementation_cli": latest_cli}, "implementation_cli_changed", binding=False)
    return _judgment(True, None, {}, None, binding=True)


# --------------------------------------------------------------------------
# 逐步骤核验
# --------------------------------------------------------------------------


def verify_step(ctx, task, step_id, *, rule_version=None):
    """返回 (satisfied, code, facts)。"""
    from . import tasks as tasks_mod

    plan = task.get("plan") or {}
    if step_id == "task.plan-approved":
        approval = plan.get("approval")
        if not approval:
            return False, "WF_APPROVAL_MISSING", {"reason": "plan not approved"}
        if approval.get("choice") not in tasks_mod.APPROVE_CHOICES:
            return False, "WF_APPROVAL_MISSING", {"reason": "approval decision is not an approval",
                                                  "choice": approval.get("choice"),
                                                  "accepted": list(tasks_mod.APPROVE_CHOICES)}
        current = tasks_mod.current_plan_version(ctx.root, task)
        if current.get("error"):
            return False, current["error"][0], current["error"][1]
        if current.get("version") != plan.get("version"):
            return False, "WF_APPROVAL_MISSING", {
                "reason": "approved version does not match current planning inputs",
                "approved": plan.get("version"),
                "current": current.get("version"),
            }
        approved = plan.get("approved_version") or plan.get("version")
        normalized = tasks_mod.normalized_plan_version(task)
        if normalized != approved:
            return False, "WF_APPROVAL_MISSING", {
                "reason": "equivalence chain is broken or missing a Decision",
                "normalized": normalized,
                "approved": approved,
            }
        if plan.get("version") != approved:
            from . import fingerprint as fp

            block = current.get("block") or {}
            same_paths = sorted(block.get("touch_paths") or []) == sorted(plan.get("touch_paths") or [])
            same_acceptance = fp.acceptance_digest(block.get("acceptance") or []) == plan.get("acceptance_digest")
            if not (same_paths and same_acceptance):
                return False, "WF_APPROVAL_MISSING", {
                    "reason": "mechanical revision endpoints are not equivalent",
                    "same_touch_paths": same_paths,
                    "same_acceptance": same_acceptance,
                }
        questions = tasks_mod.plan_questions(ctx.root, task)
        errors = tasks_mod.question_errors(questions)
        if errors:
            return False, "WF_SEMANTIC_DECISION", {"problems": errors}
        missing = tasks_mod.unanswered_plan_questions(ctx.root, task)
        if missing:
            return False, "WF_SEMANTIC_DECISION", {"unanswered": missing}
        return True, None, {}
    if step_id == "task.spec-loaded":
        return tasks_mod.spec_loaded_fact(ctx, task)
    if step_id == "task.work-satisfied":
        return tasks_mod.work_satisfied_fact(ctx, task)
    if step_id == "task.check-passed":
        # 判据与 repair_scope 共用 `check_validity`（⑥）：这里只做投影，不另写条件
        verdict = check_validity(ctx, task, rule_version=rule_version)
        return verdict["valid"], verdict["code"], verdict["facts"]
    if step_id == "task.tdd-verified":
        check = task.get("check") or {}
        evidence = check.get("tdd_evidence")
        if plan.get("tdd"):
            from . import check as check_mod

            history_commands = [command for entry in task.get("check_history") or []
                                for command in entry.get("commands") or []]
            problem = check_mod.tdd_evidence_problem(evidence, check.get("commands") or [], history_commands)
            if problem:
                return False, "WF_CHECK_FAILED", dict({"reason": "tdd evidence incomplete"}, **problem)
            return True, None, {}
        return True, None, {}
    if step_id == "task.review-passed":
        if plan.get("complexity") != "complex":
            downgrades = [item for item in plan.get("complexity_reasons") or [] if item.get("downgrade")]
            incomplete = [item for item in downgrades
                          if not item.get("reason") or not item.get("evidence")]
            if incomplete:
                return False, "WF_SEMANTIC_DECISION", {
                    "incomplete_downgrade": incomplete,
                    "reason": "complex 降级为 light 须有理由与证据（机制稿 §9.3 门禁 3）",
                }
            return True, None, {}
        reviews = task.get("reviews") or {}
        result = reviews.get("result") or {}
        if result.get("verdict") != "pass":
            # P2-4：环境不足（无可用审查者）与审查不合格是两个出口（机制稿 §11.1）
            if result.get("unavailable") or result.get("verdict") == "unavailable":
                return False, "WF_REVIEW_UNAVAILABLE", {"result": result}
            return False, "WF_REVIEW_INVALID", {"result": result}
        # 绑定判据（含引用非空、三重摘要、结论轮 vs 最新 launch 的 CLI 校验）与
        # repair_scope 共用 `review_binding`（⑥）
        binding = review_binding(ctx, task, result=result)
        return binding["binding"], binding["code"], binding["facts"]
    if step_id == "task.knowledge-disposed":
        knowledge = task.get("knowledge")
        if not isinstance(knowledge, dict) or not knowledge.get("decision"):
            return False, "WF_SEMANTIC_DECISION", {"reason": "knowledge disposition missing"}
        if not isinstance(task.get("curation"), list):
            return False, "WF_RECORD_INVALID", {"reason": "curation field missing"}
        return True, None, {}
    if step_id == "task.retrospective-done":
        # 裁定引用的调试证据必须仍可核对（机制稿 §11.2"核对所引证据仍真实存在"）
        evidence_problems = tasks_mod.retrospective_evidence_problems(ctx, task)
        if evidence_problems:
            return False, "WF_SEMANTIC_DECISION", {"unverifiable_debug_evidence": evidence_problems}
        triggers = retrospective_triggers(ctx.root, task, ctx.debug_threshold())
        if not triggers:
            return True, None, {}
        retrospective = task.get("retrospective") or {}
        evidence = retrospective.get("evidence") or {}
        covered = set()
        for item in evidence.get("refs") or []:
            if isinstance(item, dict):
                covered.add((item.get("kind"), str(item.get("ref"))))
        missing = [item for item in triggers if (item["kind"], str(item["ref"])) not in covered]
        if missing:
            return False, "WF_SEMANTIC_DECISION", {"uncovered_triggers": missing}
        if not retrospective.get("conclusion"):
            return False, "WF_SEMANTIC_DECISION", {"reason": "retrospective conclusion missing"}
        return True, None, {}
    if step_id == "task.sampled":
        # 2026-11-21 降档：verify_step 不再核 task.sampled（已从 TASK_STEP_SPECS 移除）。
        # 该分支保留为防御性拒绝（未知步骤不该被当满足），触发即测试迁移有遗漏。
        return False, "WF_RECORD_INVALID", {
            "reason": "task.sampled is no longer a required step (pilot-only, 2026-11-21)",
        }
    if step_id == "task.changes-persisted":
        return tasks_mod.changes_persisted_fact(ctx, task)
    if step_id == "task.archived":
        if task.get("terminal") != "normal":
            return False, "WF_PERSISTENCE_FAILED", {"terminal": task.get("terminal")}
        return True, None, {}
    return True, None, {}


def evaluate(ctx, task, due, *, rule_version=None):
    """按门禁点收集缺项；只读，不写回执。"""
    rule_version = rule_version or ctx.rule_version()
    limit = DUE_ORDER[due]
    findings = []
    unknown = []
    for step in applicable(ctx, task, rule_version):
        if DUE_ORDER[step["due"]] > limit:
            continue
        try:
            projection = compute_P(ctx, task, step["id"], rule_version=rule_version)
        except KeyError:
            # 运行期未知 step id 被略过时留痕，不静默（P3）
            unknown.append(step["id"])
            continue
        state, receipt = receipt_state(task, step["id"], projection, rule_version)
        base = {"id": step["id"], "mode": step["mode"], "due": step["due"]}
        if state is None and step["id"] in RULE_CLASS_STEPS and _has_stale_rule_receipt(
                task, step["id"], projection, rule_version):
            findings.append(dict(base, status="missing", code="WF_CHECK_STALE",
                                 facts={"reason": "receipt produced under different framework rules"}))
            continue
        # 门禁重核完成判据：回执只是证据，不能替代对当前事实的核验（机制稿 §11.2）
        satisfied, code, facts = verify_step(ctx, task, step["id"], rule_version=rule_version)
        if not satisfied:
            findings.append(dict(base, status="missing", code=code, facts=facts))
        elif state == "completed":
            findings.append(dict(base, status="completed", receipt=receipt.get("anchor")))
        elif state == "reused":
            findings.append(dict(base, status="reused", code=None, facts=facts))
        else:
            findings.append(dict(base, status="satisfied", code=None, facts=facts))
    if unknown:
        findings.append({"id": "__unknown_steps__", "mode": "once", "due": "before_execute",
                         "status": "unknown", "code": None, "facts": {"steps": sorted(set(unknown))}})
    return findings


def evaluate_instance(ctx, run):
    """实例门禁（只读）：当前步骤、各步骤结果，以及 `run advance` 会等什么（机制稿 §7.3、§11.2）。

    只读断言：不写游标、不写 `step_results`、不建任务。判定的每一条都来自记录事实；
    「这一步该不该算完成」仍按任务侧 Check/finish 与人的判断。
    """
    from . import runs as runs_mod

    text = None
    snapshot = (run.get("definition") or {}).get("snapshot_path")
    path = join(ctx.root, snapshot) if snapshot else None
    if path is not None and os.path.exists(path):
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8")
    doc, problems = runs_mod.parse_definition(text) if text else (None, [])
    cursor = run.get("cursor") or {}
    step_results = run.get("step_results") or {}
    task_map = run.get("task_map") or {}
    applicability = runs_mod._applicability(run.get("creation_decision") or {}, doc or {})
    steps = []
    for step in runs_mod._ordered_steps(doc or {}):
        step_id = step["id"]
        result = step_results.get(step_id) or {}
        mapping = task_map.get(step_id) or {}
        steps.append({"id": step_id, "type": step.get("type"), "required": step.get("required"),
                      "applicability": applicability.get(step_id, "applicable"),
                      "result": result.get("kind"),
                      "task": mapping.get("task_id"),
                      "current": step_id == cursor.get("step_id")})
    blocking = []
    if run.get("terminal"):
        blocking.append({"code": None, "reason": "实例已结束", "terminal": run.get("terminal")})
    elif run.get("paused"):
        blocking.append({"code": None, "reason": "实例已暂停",
                         "exit": "run resume 后继续"})
    action = run.get("action") or {}
    if action.get("state") not in (None, "done"):
        blocking.append({"code": "WF_ACTION_INCOMPLETE",
                         "reason": "实例上有未完成动作",
                         "action": {"id": action.get("id"), "kind": action.get("kind"),
                                    "state": action.get("state"),
                                    "next_step": action.get("next_step")}})
    if problems:
        blocking.append({"code": "WF_HISTORY_UNRESOLVED",
                         "reason": "固定快照不可静态解析", "problems": problems})
    current_id = cursor.get("step_id")
    if current_id:
        current = step_results.get(current_id) or {}
        mapping = task_map.get(current_id) or {}
        if current.get("kind") in ("satisfied", "skipped"):
            blocking.append({"code": None, "reason": "当前步骤已结算，下一步待 advance 推进",
                             "step": current_id, "result": current.get("kind")})
        elif mapping.get("task_id"):
            from . import tasks as tasks_mod

            task = tasks_mod.load_task(ctx.root, mapping["task_id"]) or {}
            blocking.append({"code": None, "reason": "等待任务完成（advance 只认正常归档+持久化）",
                             "step": current_id, "task": mapping["task_id"],
                             "task_status": task.get("status"), "task_phase": task.get("phase"),
                             "task_terminal": task.get("terminal")})
        else:
            step = next((item for item in steps if item["id"] == current_id), None)
            blocking.append({"code": "WF_SEMANTIC_DECISION" if (step or {}).get("type") == "human" else None,
                             "reason": ("人判步骤待答" if (step or {}).get("type") == "human"
                                        else "步骤尚无结果"),
                             "step": current_id})
    return {"run": run.get("id"), "cursor": cursor, "steps": steps,
            "blocking": blocking, "closure": run.get("closing"),
            "terminal": run.get("terminal")}


def evaluate_instance_cli(ctx, run_id, due):
    """`gate` 的实例分支：只读断言 + 三档输出（与任务分支同一套输出形状）。"""
    from . import runs as runs_mod

    run = runs_mod.load_run(ctx.root, run_id)
    if not isinstance(run, dict):
        raise _cli_error("WF_HISTORY_UNRESOLVED", {"reason": "run record missing", "run": run_id})
    report = evaluate_instance(ctx, run)
    position = codes.position(scope="run", step_id=(run.get("cursor") or {}).get("step_id"),
                              action_id=(run.get("action") or {}).get("id"),
                              action_state=(run.get("action") or {}).get("state"))
    blocking = [item for item in report["blocking"] if item.get("code")]
    if blocking:
        first = blocking[0]
        return codes.result(
            first["code"],
            object={"id": run_id},
            position_=position,
            next_="按 blocking 的第一条处理后重试（只读断言：本次未写入任何记录）",
            facts={"due": due, "blocking": report["blocking"], "steps": report["steps"],
                   "cursor": report["cursor"], "note": "只读断言，不写游标与 step_results"},
        )
    return codes.result(
        "WF_OK",
        object={"id": run_id},
        position_=position,
        next_=("实例已结束，无可推进项" if report["terminal"] else "按 advance 推进当前步骤"),
        facts={"due": due, "blocking": report["blocking"], "steps": report["steps"],
               "cursor": report["cursor"], "terminal": report["terminal"],
               "note": "只读断言，不写游标与 step_results"},
    )


def evaluate_cli(ctx, due):
    """gate 命令：只读断言，取当前绑定任务。"""
    from . import session as session_mod
    from . import tasks as tasks_mod

    key = ctx.key(required=False)
    if not key:
        return codes.result(
            "WF_OK",
            facts={"bound": False, "due": due},
            next_="wf-start 选择对象后可查询门禁",
        )
    binding = session_mod.load_binding(ctx.root, key)
    if not binding:
        return codes.result("WF_OK", facts={"bound": False, "due": due}, next_="wf-start 选择对象")
    object_ref = binding.get("object") or {}
    if object_ref.get("kind") == "run":
        return evaluate_instance_cli(ctx, object_ref.get("id"), due)
    if object_ref.get("kind") != "task":
        raise _cli_error("WF_BINDING_MISMATCH",
                         {"reason": "bound object is neither task nor run", "object": object_ref})
    task = tasks_mod.load_task(ctx.root, object_ref.get("id"))
    if task is None:
        raise _cli_error("WF_RECORD_INVALID", {"missing_task": object_ref.get("id")})
    findings = evaluate(ctx, task, due)
    blocking = [item for item in findings if item["status"] == "missing"]
    position = codes.position(
        scope="task", phase=task.get("phase"), task_id=task.get("id"),
        action_id=(task.get("action") or {}).get("id"),
        action_state=(task.get("action") or {}).get("state"),
    )
    if blocking:
        first = blocking[0]
        return codes.result(
            first["code"] or "WF_CHECK_FAILED",
            object={"id": task.get("id"), "name": task.get("title")},
            position_=position,
            next_="按 missing 清单补齐对应步骤后重试",
            facts={"due": due, "missing": blocking, "all": findings},
        )
    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=position,
        next_="继续当前步骤",
        facts={"due": due, "steps": findings},
    )


def _cli_error(code, facts):
    from . import cli

    return cli.CliError(code, facts)


# --------------------------------------------------------------------------
# 最终门禁（§9.3 八项）
# --------------------------------------------------------------------------




def final_gate(ctx, task, ignore_action_id=None):
    """返回 (ok, code, facts)；第 8 项的人调用与归档提交由 archive 动作核。"""
    rule_version = ctx.rule_version()
    findings = evaluate(ctx, task, "before_archive", rule_version=rule_version)
    blocking = [item for item in findings if item["status"] == "missing"]
    if blocking:
        return False, blocking[0]["code"] or "WF_CHECK_FAILED", {"missing": blocking, "all": findings}
    ok, code, facts = final_gate_nonstep(ctx, task, ignore_action_id=ignore_action_id)
    if not ok:
        return ok, code, facts
    return True, None, {"steps": findings}


def final_gate_nonstep(ctx, task, ignore_action_id=None):
    """最终门禁的 nonstep 段（⑥ 提取：原 `final_gate` 的第 1–10 项原样搬出）。

    步骤面由 `final_gate` 先跑（顺序短路，见 `gates.py:865-871`）；这里是**步骤面之外**
    的全部阻断。归档命令与归档提交前的只读预检（D4）调同一个函数——不是第二套实现。
    """
    check = task.get("check") or {}
    if check.get("result") != "pass":
        return False, "WF_CHECK_FAILED", {"reason": "current check is not pass", "check": check.get("id")}
    # 「判断不了」只挂起最终结论，不冻结中途动作（v42 §5.3）：在归档口拦下即可
    # 只按**当前有效**判断算待决：被人回答/更正过的条目由新条目 supersedes 承接，
    # 历史照留（append-only），但不再算"还没回答"。否则诚实求助会变成流程死路。
    from . import judgments as judgments_mod

    escalated = judgments_mod.pending_escalations(task)
    if escalated:
        return False, "WF_SEMANTIC_DECISION", {
            "escalated": [{"kind": item.get("kind"), "question": item.get("escalated_question")}
                          for item in escalated],
            "reason": "有判断被 escalated 交人：最终结论挂起，等人回答",
            "exits": ["人回答后用 kind 相同的新 judgment 收口（supersedes 指向被挂起那条）",
                      "人直接裁定本轮不继续，按设计稿 §5.6 异常归档"],
        }
    # S5b/4.9：required 验收项未核实 → 阻断收工（只能收窄四项或异常归档，不接受"接受风险"）
    from . import projection as projection_mod

    pending_required = projection_mod.required_unverified(ctx, task)
    if pending_required:
        return False, "WF_SEMANTIC_DECISION", {
            "pending_required_unverified": pending_required,
            "reason": "required 验收项未核实：只能收窄（四项依据齐全）或异常归档",
            "exits": ["`wf verify resolve --kind narrow` 给齐 id/原因/影响/补偿 后重入",
                      "`wf verify resolve --kind inspection` 记录人工核验证据",
                      "按设计稿 §5.6 异常归档"],
        }
    # S6 的第 3/4 项：blocking 必须已被处置（"不处置"不是关闭，K10/K4b）
    from . import review as review_mod

    open_items = review_mod.open_findings(ctx, task)
    if open_items["blocking"]:
        return False, "WF_UNRESOLVED_BLOCKING", {
            "unaddressed_blocking": open_items["blocking"],
            "unavailable_reports": open_items["unavailable"],
            "exits": ["按 K4b 由非提出者复核后以 dispositions 关闭（决策 + 证据 + recheck_by）",
                      "由人确认重分类（改变 severity/类别的判断）",
                      "按 §5.6 异常归档"],
        }
    # 降级条目的齐全性在归档门禁核（不分轻量/复杂），不受 review-passed 的 complex 条件裁剪
    plan_now = task.get("plan") or {}
    # 人工载体：复杂分级必须是**人确认**的（决定文件 plan 块），不能由请求自报（设计稿 §4.3/§4.4）
    if plan_now.get("complexity") == "complex" and plan_now.get("confirmed_source") != "decision":
        return False, "WF_SEMANTIC_DECISION", {
            "reason": "complex 分级须由人在批准决定中确认（decision.plan.complexity）",
            "confirmed_source": plan_now.get("confirmed_source"),
            "human_inputs": plan_now.get("human_inputs"),
        }
    if plan_now.get("complexity") != "complex":
        downgrades = [item for item in plan_now.get("complexity_reasons") or [] if item.get("downgrade")]
        incomplete = [item for item in downgrades if not item.get("reason") or not item.get("evidence")]
        if incomplete:
            return False, "WF_SEMANTIC_DECISION", {
                "incomplete_downgrade": incomplete,
                "reason": "complex 降级为 light 须有理由与证据（机制稿 §9.3 门禁 3）",
            }
    from . import tasks as tasks_mod

    blockers = tasks_mod.dependency_blockers(ctx.root, task)
    if blockers:
        return False, "WF_DEPENDENCY_UNMET", {"unmet": blockers}
    debug = debug_pending(task, ctx.debug_threshold())
    if debug["pending"]:
        # 把判定所用的阈值一并给出：AI 才知道"到第几次算重复"，否则只看到 pending 列表
        return False, "WF_SEMANTIC_DECISION", {"unruled_debug_multiples": debug["pending"],
                                               "merged": debug["merged"],
                                               "threshold": ctx.debug_threshold(),
                                               "next": "对每个倍数裁定「同一问题/不同问题」"}
    pending = actions.pending(task)
    if pending and pending.get("id") == ignore_action_id:
        pending = None
    if task.get("suspended") or task.get("paused"):
        if pending:
            return False, "WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state")}
        return False, "WF_SEMANTIC_DECISION", {"reason": "task still paused or suspended",
                                               "paused": task.get("paused"), "suspended": task.get("suspended")}
    if pending:
        return False, "WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state")}
    # C3（⑥）：仍承载未完成义务、且未被放行的不可核实证据 → 阻断。
    # **必须在这里**（nonstep 段内）：归档前的只读预检才能在业务提交之前看到它，
    # 否则"业务已提交、归档因 C3 被拒"无法避免。
    unreleased = review_mod.exiting_evidence(ctx, task)
    if unreleased:
        releasable = any(item.get("release_allowed") for item in unreleased)
        return False, "WF_REVIEW_INVALID", {
            "reason": "unverifiable_evidence",
            "unverifiable": unreleased,
            "exits": ["找回原字节（restore_bytes）：报告重新可核实后该条离开 unverifiable",
                      "由人裁放行（human_release）：决定文件写 quote 与 waive_unknown_findings: true"
                      if releasable else
                      "本条的引用证据不可放行（complex）：完成一次新审查，使旧报告变成非引用证据后再人裁放行",
                      "按设计稿 §5.6 异常归档（不把放弃当成满足条件的手段）"],
        }
    return True, None, {}
