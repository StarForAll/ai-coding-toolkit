"""review.py — 审查发起、导入与判定（机制稿 §9.1、§9.2）。"""

from __future__ import annotations

import json
import os
import re
import tempfile

from . import check as check_mod, config, records, writer as writer_mod
from .paths import join

REPORT_MARKER = "<!-- wf-review-report:v1 -->"
PROTOCOL = "wf-review-v1"
REVIEW_FOCUS = "范围、验收、契约/spec、跨层回归、可测性"

# 2026-11-07：身份由**文件名** `review-<agent>.md` 承载，正文不再要求 reviewer-id / source-cli。
# 若正文仍写了这两项且与文件名不一致，按「两个事实源冲突」拒绝。
REPORT_FIELDS = (
    "protocol",
    "task-id",
    "round",
    "review-time",
    "review-focus",
    "check-anchor",
    "read-scope",
    "excluded-scope",
    "axes",
    "findings",
    "verdict",
)


BLOCKING_SEVERITIES = ("blocker", "blocking", "critical", "high")

# 外部审查的固定五轴（机制稿 §9.2、skill wf-review）；内部两轴属 Check 自审，不在此列
REVIEW_AXES = ("range", "acceptance", "contract", "regression", "testability")
AXIS_CONCLUSIONS = ("pass", "fail", "uncovered")


def _axis_conclusion(value):
    """轴结果既可能是 {conclusion, basis} 也可能是裸结论字符串。"""
    if isinstance(value, dict):
        return value.get("conclusion")
    return value


class ReviewError(Exception):
    def __init__(self, code, facts=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}


def staging_root(ctx, task_id):
    project_config, _problems = config.load_project_config(ctx.root, allow_missing=True)
    project_id = (project_config or {}).get("project_id") or "unknown-project"
    return os.path.join(tempfile.gettempdir(), "wf-review", str(project_id), task_id)


def slot_dir(ctx, task_id, round_no, slot):
    return os.path.join(staging_root(ctx, task_id), f"round-{int(round_no)}", slot)


AGENT_ALIASES = {"claude": "claudecode", "gemini": "geminicli", "ghcopilot": "copilot"}
AGENT_REPORT = re.compile(r"^review-([a-z0-9._-]+)\.md$")
AGENT_HEADER = "<!-- wf-review-agent:v1 status={status} -->"


CLI_TOKEN_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def normalize_agent(value):
    token = str(value or "").strip().lower()
    return AGENT_ALIASES.get(token, token)


def review_cli(value):
    """把外部声明归一成 CLI token；空/非法一律 None（不猜、不兜底成别的值）。"""
    token = normalize_agent(value)
    return token if token and CLI_TOKEN_RE.match(token) else None


def participant_cli(ctx, as_value=None):
    """审查参与者 CLI（设计稿 §6.5 C6）：`--as` 优先，显式模式回退信封 host_id。

    自动身份模式不提供 host 身份（锚点只派生执行边界），因此那边**必须**显式 `--as`；
    这不是"适配某个 agent"，而是"参与者身份自报 + 三处交叉核对"。
    """
    token = review_cli(as_value)
    if token:
        return token
    session = ctx.session() or {}
    legacy = review_cli((session.get("identity") or {}).get("host_id"))
    if legacy:
        return legacy
    raise ReviewError("WF_IDENTITY_UNRESOLVED", {
        "reason": "reviewer CLI not declared",
        "identity_mode": session.get("source") or "explicit",
        "exits": ["用 --as <cli> 声明本次审查的 CLI（如 --as pi）",
                  "或在显式信封模式下由信封携带 session.identity.host_id"],
    })


def round_dir(ctx, task_id, round_no):
    return os.path.join(staging_root(ctx, task_id), f"round-{int(round_no)}")


def agent_report_path(ctx, task_id, round_no, agent):
    return os.path.join(round_dir(ctx, task_id, round_no), f"review-{normalize_agent(agent)}.md")


def agent_from_path(path):
    match = AGENT_REPORT.match(os.path.basename(path))
    return normalize_agent(match.group(1)) if match else None


def read_agent_status(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            head = handle.read(400)
    except OSError:
        return None
    match = re.search(r"status=([a-z-]+)", head)
    return match.group(1) if match else None


def read_report(text):
    """宽松解析：返回 `(payload, problems)`。结构坏了 payload 为 None；只是字段缺失则两者都有。

    门禁用 `parse_report`（遇到第一个问题就拒），`lint report` 用本函数——两者同一份解析，
    避免"容忍版"与"严格版"各写一遍（纪律 #4）。
    """
    if REPORT_MARKER not in text:
        return None, [{"reason": "report protocol marker missing"}]
    tail = text.split(REPORT_MARKER, 1)[1]
    fence = tail.find("```json")
    if fence < 0:
        return None, [{"reason": "report json block missing"}]
    start = fence + len("```json")
    end = tail.find("```", start)
    if end < 0:
        return None, [{"reason": "report json block not closed"}]
    try:
        payload = records.loads(tail[start:end])
    except records.RecordInvalid as exc:
        return None, [{"reason": f"report json invalid: {exc}"}]
    if not isinstance(payload, dict):
        return None, [{"reason": "report payload must be an object"}]
    problems = []
    missing = [field for field in REPORT_FIELDS if field not in payload]
    if missing:
        problems.append({"reason": "report missing required fields", "missing_fields": missing})
    if payload.get("protocol") != PROTOCOL:
        problems.append({"reason": "unsupported protocol", "protocol": payload.get("protocol")})
    return payload, problems


def parse_report(text):
    payload, problems = read_report(text)
    if problems:
        raise ReviewError("WF_REVIEW_INVALID", problems[0])
    return payload


def open_findings(ctx, task):
    """未处置 findings（K8 投影）：重解析已导入报告，按 dispositions 派生。

    报告有 digest、导入后不可改（K4a），所以"重解析"不会与当时的事实分叉；findings 因此
    不需要另存一份（同一事实两处存）。返回 `{unaddressed, blocking, unavailable, closed}`。
    """
    reviews = task.get("reviews") or {}
    closed = {str(item.get("finding_id"))
              for item in reviews.get("dispositions") or []
              if isinstance(item, dict) and item.get("decision") == "accepted"}
    unaddressed, unavailable = [], []
    for entry in reviews.get("imported") or []:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("report_path")
        if not rel:
            continue
        path = join(ctx.root, rel)
        if records.file_digest(path) != entry.get("report_digest"):
            unavailable.append({"slot": entry.get("slot"), "path": rel,
                                "reason": "report changed after import"})
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload, _problems = read_report(handle.read())
        except OSError as exc:
            unavailable.append({"slot": entry.get("slot"), "path": rel, "reason": str(exc)})
            continue
        if payload is None:
            unavailable.append({"slot": entry.get("slot"), "path": rel,
                                "reason": "report unreadable after import"})
            continue
        for finding in payload.get("findings") or []:
            if not isinstance(finding, dict) or not finding.get("id"):
                continue
            if str(finding["id"]) in closed:
                continue
            unaddressed.append({"finding_id": finding["id"], "severity": finding.get("severity"),
                                "slot": entry.get("slot"), "assertion_ref": finding.get("assertion_ref")})
    return {"unaddressed": unaddressed,
            "blocking": [item for item in unaddressed if item.get("severity") in BLOCKING_SEVERITIES],
            "unavailable": unavailable, "closed": sorted(closed)}


def lint_report(ctx, task, text):
    """报告的一次性全量预检（S3/C2，`wf lint report` 的唯一实现）。

    **不是门禁**：导入与判定仍是权威（锚点新鲜度、材料外发范围、人数/异种、报告正文摘要
    只在那两处核）。这里只把"能一次查完的格式与引用问题"一次列全，避免 dogfood 里
    四轮才把格式改对的返工（C2/C3）。
    返回 `{ok, problems, checks, axes, verdict, gaps, deprecated_refs}`。
    """
    checks = []
    problems = []

    def done(name, result, detail=None):
        checks.append({"check": name, "ok": not result, "problems": result})
        problems.extend(result)

    payload, structure_problems = read_report(text)
    if payload is None:
        return {"ok": False, "problems": structure_problems,
                "checks": [{"check": "protocol", "ok": False, "problems": structure_problems}],
                "axes": {}, "verdict": None, "gaps": [], "deprecated_refs": []}
    done("protocol", structure_problems)
    required = [field for field in REPORT_FIELDS if field not in payload]
    done("required-fields", [{"reason": "missing field", "field": field} for field in required])

    verdict = None
    gaps = []
    axis_problems = []
    if isinstance(payload.get("axes"), dict):
        verdict, axis_problems, gaps, _blocking = derive_verdict(payload.get("axes"), payload.get("findings"))
        done("axes-and-verdict", axis_problems)
        declared = payload.get("verdict")
        done("declared-verdict", [] if declared == verdict else
             [{"reason": "申报 verdict 与推导不一致", "declared": declared, "derived": verdict}])
    else:
        done("axes-and-verdict", [{"reason": "axes must be an object"}])

    refs = []
    deprecated = []
    if task is not None:
        index, changed = assertion_index(ctx, task)
        for finding in payload.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            ref = finding.get("assertion_ref")
            if not ref:
                if finding.get("severity") in BLOCKING_SEVERITIES:
                    refs.append({"reason": "blocking finding must cite an assertion_ref",
                                 "finding": finding.get("id")})
                continue
            problem = assertion_ref_problem(ref, index, changed, payload.get("check_fix_kind"))
            if problem:
                refs.append(dict(problem, finding=finding.get("id")))
            base, _, clause_id = str(ref).partition("#")
            if clause_id:
                from . import spec as spec_mod
                info = spec_mod.load_spec(ctx.root, base)
                for clause in (info.get("metadata") or {}).get("clauses") or []:
                    if isinstance(clause, dict) and clause.get("id") == clause_id and clause.get("status") != "active":
                        deprecated.append({"finding": finding.get("id"), "assertion_ref": ref,
                                           "reason": "d: 只能引用 active 条目（引用 deprecated 视为位置不存在）"})
        done("finding-refs", refs)
        done("deprecated-refs", deprecated)
    else:
        checks.append({"check": "finding-refs", "ok": True, "skipped": "未给 --task：无法核对批准集合与规则状态"})

    recheck = payload.get("recheck")
    if recheck is not None:
        bad = []
        for index_, item in enumerate(recheck if isinstance(recheck, list) else [recheck]):
            if not isinstance(item, dict) or not item.get("finding_id"):
                bad.append({"reason": "recheck 每项需 finding_id", "index": index_})
        done("recheck", bad)

    return {"ok": not problems, "problems": problems, "checks": checks,
            "axes": payload.get("axes") or {}, "verdict": verdict, "gaps": gaps,
            "deprecated_refs": deprecated,
            "not_checked": ["锚点新鲜度", "材料外发范围", "审查人数与异种", "报告正文摘要（导入/判定处核对）"]}


def derive_verdict(axes, findings):
    """报告三态判定（S3 判定句，v42 B1）：`fail` 仅当存在 blocking finding。

    返回 `(conclusion, problems, gaps)`：
    - `conclusion` 取 `pass` / `fail`；
    - `problems` 为"输入不成立"的事实（轴缺失/非法、`fail` 轴没有对应 blocking finding、
      申报 verdict 与推导不一致）；
    - `gaps` 为 `uncovered` 轴——它**不是** fail，而是"没把握"的缺口（走 4.8/4.9）。
    """
    conclusions = {}
    problems = []
    gaps = []
    for axis, result in sorted((axes or {}).items()):
        if axis not in REVIEW_AXES:
            problems.append({"reason": "unknown review axis", "axis": axis})
            continue
        conclusion = _axis_conclusion(result)
        if conclusion not in AXIS_CONCLUSIONS:
            problems.append({"reason": "review axis conclusion invalid", "axis": axis,
                             "conclusion": conclusion, "known": list(AXIS_CONCLUSIONS)})
            continue
        conclusions[axis] = conclusion
        if conclusion == "uncovered":
            gaps.append({"axis": axis, "reason": "该轴未覆盖；按缺口处置，不当作缺陷"})
    missing = [axis for axis in REVIEW_AXES if axis not in (axes or {})]
    if missing:
        problems.append({"reason": "report does not cover all review axes",
                         "missing": missing, "expected": list(REVIEW_AXES)})
    blocking = [item for item in (findings or [])
                if isinstance(item, dict) and item.get("severity") in BLOCKING_SEVERITIES]
    fail_axes = [axis for axis, conclusion in conclusions.items() if conclusion == "fail"]
    if fail_axes and not blocking:
        problems.append({"reason": "轴判 fail 但没有对应 blocking finding（例外字段不得一义三用）",
                         "axes": fail_axes,
                         "exits": ["把该轴的问题写成 severity=blocking 的 finding（附 assertion_ref）",
                                   "或把该轴改成 uncovered 并按缺口处置"]})
    return ("fail" if (blocking or fail_axes) else "pass"), problems, gaps, blocking


def status_of_round(ctx, task, round_no=None):
    """审查到位状态（S9，`wf review-status` 的唯一实现；只读，不写任何记录）。

    人不必再当传声筒（dogfood D3）：一眼看到"本轮已到 n/2、缺哪份、那份文件现在是什么状态"。
    每槽位的 `state` 取 `missing`（没有文件）/`staged`（已产出未导入）/
    `imported`（已导入且摘要一致）/`stale`（导入后被改写或锚点已失效）。
    """
    reviews = task.get("reviews") or {}
    rounds = [entry for entry in reviews.get("launches") or [] if isinstance(entry, dict)]
    if round_no is None:
        round_no = max([int(entry.get("round") or 0) for entry in rounds] or [0])
    round_no = int(round_no)
    launch = next((entry for entry in rounds if int(entry.get("round") or 0) == round_no), None)
    imported = [entry for entry in reviews.get("imported") or []
                if int(entry.get("round") or 0) == round_no]
    imported_by_slot = {normalize_agent(entry.get("agent") or entry.get("slot")): entry
                        for entry in imported}
    declared = [normalize_agent(slot.get("slot")) for slot in (launch or {}).get("slots") or []
                if isinstance(slot, dict) and slot.get("slot")]
    if not declared and imported_by_slot:
        declared = sorted(imported_by_slot)
    try:
        anchor, _parts = _current_anchor(ctx, task)
    except Exception:
        anchor = None
    task_id = task.get("id")
    slots = []
    for slot in declared:
        entry = imported_by_slot.get(slot)
        record = {"slot": slot}
        if entry:
            path = join(ctx.root, entry.get("report_path") or "")
            current = records.file_digest(path) if entry.get("report_path") else None
            record["imported"] = True
            record["report_path"] = entry.get("report_path")
            if entry.get("report_digest") != current:
                record["state"] = "stale"
                record["reason"] = "报告导入后被改写"
            elif anchor is None:
                # 锚点算不出来（任务记录不完整）：到位但不核锚点，如实标注，不假装新鲜也不假装失效
                record["state"] = "imported"
                record["anchor_checked"] = False
            elif (entry.get("anchor") or {}).get("check_anchor") != anchor:
                record["state"] = "stale"
                record["anchor_checked"] = True
                record["reason"] = "锚点已失效（对象或标准已变化）"
            else:
                record["state"] = "imported"
                record["anchor_checked"] = True
        else:
            staged = agent_report_path(ctx, task_id, round_no, slot)
            record["imported"] = False
            if os.path.isfile(staged):
                record["state"] = "staged"
                record["staged_path"] = staged
                status = read_agent_status(staged)
                if status:
                    record["agent_status"] = status
            else:
                record["state"] = "missing"
        slots.append(record)
    arrived = [item for item in slots if item["state"] in ("imported", "staged")]
    missing = [item["slot"] for item in slots if item["state"] == "missing"]
    return {"round": round_no, "required": len(declared), "arrived": len(arrived),
            "arrived_slots": [item["slot"] for item in arrived], "missing": missing,
            "slots": slots, "anchor_current": anchor,
            "ready_to_decide": bool(declared) and not missing}


def curation_changed(before, current_rule_digest, current_file_digest):
    """策划摘要（选用时）与当前是否不同。

    策展记录里的摘要可能是**整文件摘要**（旧记录）或**规则实质摘要**（现行 `spec_versions`）——
    与当前任一形态相等即"没改过"。只看单一形态会把所有策划规则误判为"本任务改过"，
    让 K4c 变成一律阻断。
    """
    if not before:
        return False
    return before not in (current_rule_digest, current_file_digest)


def assertion_index(ctx, task):
    """当前批准集合 + 本任务内被改过的规则（K3b 引用校验、K4c 规则不得自证）。

    返回 `(index, changed)`：index 为 `{id: kind}`（验收项 id、验证 id、参与 spec 的路径与
    `path#clause-id`）；changed 为 `{path: {curation_digest, current_digest}}`——策展记录里的
    摘要是"选用时"的快照，与当前实质摘要不同即"本任务内改过这条规则"。
    """
    from . import check as check_mod
    from . import spec as spec_mod

    plan = task.get("plan") or {}
    index = {}
    for entry in plan.get("acceptance") or []:
        if isinstance(entry, dict) and entry.get("id"):
            index[str(entry["id"])] = "acceptance"
    for entry in plan.get("verifications") or []:
        if isinstance(entry, dict) and entry.get("id"):
            index[str(entry["id"])] = "verification"
    curated = {entry.get("path"): entry.get("digest")
               for entry in task.get("curation") or [] if isinstance(entry, dict) and entry.get("path")}
    changed = {}
    for entry in check_mod.spec_versions(ctx, task):
        spec_path = entry["path"]
        index[spec_path] = "spec-rule"
        info = spec_mod.load_spec(ctx.root, spec_path)
        for clause in (info.get("metadata") or {}).get("clauses") or []:
            if isinstance(clause, dict) and clause.get("status") == "active" and clause.get("id"):
                index[f"{spec_path}#{clause['id']}"] = "spec-clause"
        before = curated.get(spec_path)
        if before:
            file_digest = records.file_digest(join(ctx.root, spec_path))
            if curation_changed(before, entry["digest"], file_digest):
                changed[spec_path] = {"curation_digest": before, "current_digest": entry["digest"],
                                      "current_file_digest": file_digest}
    return index, changed


def anchor_drift(saved_parts, current_parts):
    """锚点差异（K3b）：只比实质字段；旧记录没有 parts 时返回 None（差异不可得）。"""
    if not isinstance(saved_parts, dict):
        return None
    diffs = []
    for key in sorted(set(saved_parts) | set(current_parts)):
        before, after = saved_parts.get(key), current_parts.get(key)
        if before != after:
            diffs.append({"id": f"d:{key}", "where": key, "before": before, "after": after})
    return diffs


def assertion_ref_problem(ref, index, changed, fix_kind=None):
    """单条引用的判定（K3b 引用属当前集合、K4c 规则不得自证）；返回问题字典或 None。"""
    base = str(ref).split("#", 1)[0]
    if base in changed and fix_kind != "broken-reference":
        return {"reason": "assertion_ref 指向本任务内修改过的规则（规则不得自证）",
                "assertion_ref": ref, "changed_rule": changed[base],
                "exits": ["换一条未被本任务修改的判据（活动 spec 规则或验收项）",
                          "若确属 check 的机械纠错，先按 broken-reference 登记并单独复核"]}
    if ref not in index and base not in index:
        return {"reason": "assertion_ref 不属于当前批准集合",
                "assertion_ref": ref, "known": sorted(index)[:40]}
    return None


def broken_reference_problems(lifted, dispositions):
    """`check_fix_kind=broken-reference` 的豁免必须有人复核（2026-11-09 人裁 B）。

    `lifted` 为 import 记录里被声明的 finding（`{finding, assertion_ref, rule}`）；
    每条都需要同名 disposition 且 `recheck_by` 以 `human:` 开头——框架不验证声明真伪，
    只保证"声明过的事实一定经过人"。纯函数，便于单测。
    """
    if not lifted:
        return []
    human = set()
    for item in dispositions or []:
        if not isinstance(item, dict):
            continue
        recheck = item.get("recheck_by")
        if isinstance(recheck, str) and recheck.strip().lower().startswith("human:"):
            human.add(str(item.get("finding_id")))
    problems = []
    for item in lifted:
        if str(item.get("finding")) not in human:
            problems.append({"finding": item.get("finding"), "assertion_ref": item.get("assertion_ref"),
                             "reason": "broken-reference 豁免需人复核：缺 recheck_by=human:<来源>",
                             "exits": ["为该 finding 补一条 dispositions（decision=accepted，recheck_by=human:<来源>）",
                                       "或撤回豁免声明，改用未被本任务修改的判据"]})
    return problems


def dispositions_problems(dispositions, proposers):
    """dispositions 的结构校验与"关闭不得自证"（机制稿 §9.2、K4b）。纯函数，便于单测。"""
    problems = []
    for index, item in enumerate(dispositions):
        if not isinstance(item, dict):
            problems.append({"index": index, "reason": "disposition must be an object"})
            continue
        decision = item.get("decision")
        if decision not in ("accepted", "rejected", "amended"):
            problems.append({"index": index, "reason": "decision must be accepted|rejected|amended",
                             "decision": decision})
        if not str(item.get("reason") or "").strip():
            problems.append({"index": index, "reason": "disposition requires a non-empty reason"})
        finding_id = item.get("finding_id")
        if finding_id is None:
            continue
        proposer = proposers.get(str(finding_id))
        recheck_by = normalize_agent(item.get("recheck_by")) if item.get("recheck_by") else None
        if recheck_by is None:
            problems.append({"index": index, "finding_id": finding_id,
                             "reason": "关闭需复核人：recheck_by 缺失",
                             "exits": ["补 recheck_by（不得由提出该 finding 的报告复核）"]})
        elif proposer and recheck_by == proposer:
            problems.append({"index": index, "finding_id": finding_id,
                             "reason": "关闭复核不得自证：复核人与提出者是同一份报告",
                             "proposer": proposer, "recheck_by": recheck_by})
    return problems


def _current_anchor(ctx, task):
    try:
        anchor, parts = check_mod.current_anchor(ctx, task)
    except check_mod.CheckError as exc:
        raise ReviewError(exc.code, exc.facts)
    return anchor, parts


def launch(ctx, task, request_path, implementation_cli=None):
    from . import cli, lock

    request = records.load_json(request_path)
    if not isinstance(request, dict):
        raise ReviewError("WF_PATH_INVALID", {"reason": "launch request missing or not an object"})
    # Check 的读取与核验移入锁内（见下）：锁外读到的 check 可能在排队期间被替换
    # （第十四轮复审 F14-3）。这里只做一次粗检，锁内会以重读记录为准。
    from_request = request.get("implementation_clis") or []
    if from_request and not isinstance(from_request, list):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "implementation_clis must be an array"})
    # 设计稿 §6.5（C6）：实施 CLI 是"异种审查是否成立"的**判定输入**，必须在发起轮次时声明，
    # 不能等判定时从会话猜。单值口径；旧请求里的数组仅供兼容读取，与该单值冲突即阻断。
    declared = review_cli(implementation_cli)
    legacy = sorted({item for item in (review_cli(entry) for entry in from_request) if item})
    if declared and legacy and legacy != [declared]:
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "implementation CLI conflicts with launch request",
                           "declared": declared, "request": legacy})
    impl = declared or (legacy[0] if len(legacy) == 1 else None)
    if not impl:
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "implementation CLI must be declared",
                           "requested": legacy,
                           "exits": ["用 --implementation-cli <cli> 声明本次实施所用 CLI 后重发 launch"]})
    implementation = [impl]
    # 2026-11-07：身份由报告文件名承载，launch 不再要求预先声明审查 CLI；
    # `slots` 缺省即"要两份审查"，只作计数用（可显式给 --reviewers N）。
    slots = request.get("slots")
    if not slots:
        count = int(request.get("reviewers") or 2)
        slots = [{"slot": f"s{index + 1}"} for index in range(max(2, count))]
    if not isinstance(slots, list) or not slots:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "at least one slot required"})
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("slot"):
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "slot requires slot id"})
        declared_cli = slot.get("reviewer_cli")
        if declared_cli and declared_cli in implementation:
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer CLI must differ from implementation CLIs",
                                                    "slot": slot})
    export_decision = request.get("export_decision")
    if not export_decision:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "export authorization decision required"})
    # K6 第 3 类：材料离开本机属不可逆动作——**声明不等于确认**，要有对应动作的确认入库
    from . import authorize as authorize_mod

    if authorize_mod.require(_task_dir(ctx, task), "export") is None:
        raise ReviewError("WF_COMMIT_NOT_AUTHORIZED",
                          {"missing_action": "export",
                           "reason": "本次审查要把材料外发，但缺外发动作的确认（K6 第 3 类）",
                           "exits": ["人执行 `wf authorize record --task <id> --file <决定.json>`，"
                                     "文件里写一条 choice=export 的确认（范围 + 人 + quote）后重跑",
                                     "改用不外发的审阅方式（例如同机只读审阅）"]})
    submitted = request.get("submitted_scope") or {}
    slots_material = (("diff",), ("requirement", "requirements"), ("test_results", "tests"))
    missing_material = [names[0] for names in slots_material
                        if not any(submitted.get(name) for name in names)]
    if missing_material:
        # 三类材料是审查输入的最小集，缺一即无法覆盖必要检查面（机制稿 §9.2）
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "submitted_scope lacks required material",
                           "missing": missing_material, "submitted": sorted(submitted)})
    with lock.acquire(ctx.root, holder_hint="review-launch"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        # Check 与锚点都按**锁内重读后的任务**取：等待锁期间 Check 可能被替换或失败，
        # 否则 request.json 会绑定到旧 Check（第十三/十四轮复审 P5、F14-3）。
        check = task.get("check") or {}
        if check.get("result") != "pass":
            raise ReviewError("WF_CHECK_FAILED", {"reason": "launch requires a valid Check pass",
                                                  "check": check.get("id"),
                                                  "result": check.get("result")})
        anchor, _parts = _current_anchor(ctx, task)
        reviews = task.setdefault("reviews", {})
        round_no = int(reviews.get("last_round") or 0) + 1
        attempts = list(reviews.get("attempts") or [])
        if not attempts:
            attempts = [{"number": 1, "rework_ref": None, "round_ids": [], "outcome": None}]
        current_attempt = attempts[-1]
        used = list(current_attempt.get("round_ids") or [])
        # 轮次不设上限（2026-11-09 人裁，机制稿 §9.1/§9.2）：是否继续由完成条件与未关闭项决定，
        # `round_ids` 只作观察与历史重建，不再作为拒绝依据。
        attempt = current_attempt.get("number") or 1
        temp_paths = []
        for slot in slots:
            directory = slot_dir(ctx, task.get("id"), round_no, slot["slot"])
            os.makedirs(directory, exist_ok=True)
            request_payload = {
                "task-id": task.get("id"),
                "round": round_no,
                "review-focus": REVIEW_FOCUS,
                "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
                "submitted_scope": request.get("submitted_scope") or {},
                "readable_scope": request.get("readable_scope") or {},
                "exclusions": request.get("exclusions") or [],
            }
            records.write_json(os.path.join(directory, "request.json"), request_payload)
            temp_paths.append(directory)
        entry = {
            "round": round_no,
            "attempt": attempt,
            "decision": request.get("export_decision"),
            # 单值口径（C6）；`implementation_clis` 保留为兼容读字段
            "implementation_cli": impl,
            "declared_at": records.now_str(),
            "declared_by": holder,
            "implementation_clis": implementation,
            "slots": slots,
            "anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "submitted_scope": request.get("submitted_scope") or {},
            "readable_scope": request.get("readable_scope") or {},
            "exclusions": request.get("exclusions") or [],
            "export_decision": request.get("export_decision"),
            "temp_paths": temp_paths,
        }
        if len(slots) < 2:
            entry["degraded"] = "single-provider"
        launches = list(reviews.get("launches") or [])
        previous = [item for item in launches
                    if isinstance(item, dict) and review_cli(item.get("implementation_cli"))]
        launches.append(entry)
        reviews["launches"] = launches
        # 实施 CLI 实质变化 ⇒ 既有审查结论失去依据（最终门禁不重核该字段）
        prior_clis = {review_cli(item.get("implementation_cli")) for item in previous}
        result_now = reviews.get("result") or {}
        if prior_clis and result_now and prior_clis != {impl} and result_now.get("verdict") in ("pass", "fail"):
            result_now["verdict"] = "invalidated"
            result_now["invalidated_reason"] = "implementation CLI changed"
            result_now["invalidated_at"] = records.now_str()
            reviews["result"] = result_now
        reviews["last_round"] = round_no
        current_attempt["round_ids"] = sorted(set(used) | {round_no})
        reviews["attempts"] = attempts
        inputs = {"task": task.get("id"), "round": round_no}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.launch", holder, inputs, ["declare", "stage_requests"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.launch", holder, inputs, action, evidence_refs=temp_paths
        )
    # 2026-11-07：不再输出长命令串；reviewer 侧只需声明任务与轮次（技能自己取其余事实）
    commands = [f"/wf-review（任务 {task.get('id')}，第 {round_no} 轮）" for _slot in slots]
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id"),
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="由人在 reviewer CLI 会话中调用上述 skill 文本；报告写入各自暂存目录",
        facts={
            "round": round_no,
            "attempt": attempt,
            "anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "temp_paths": temp_paths,
            "degraded": entry.get("degraded"),
            "paste_text": commands,
            "control_assertion": assertion,
        },
    )


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    directory = tasks_mod.task_dir(ctx.root, task.get("id"))
    if not directory:
        raise ReviewError("WF_RECORD_INVALID", {"missing_task": task.get("id")})
    return directory


def context(ctx, task, round_no=None, reset=False, as_value=None):
    """reviewer 侧入口（2026-11-07）：只给 task id（+ 轮次），其余由本命令提供。

    - 身份：取本会话信封的 `host_id` 归一化（`pi`/`zcode`/`codex`…），**不做平台校验**——
      审查 CLU 不必是项目的已安装平台，它只是报告署名人；写权限仍在主会话。
    - 占位：同一 agent 同一轮只允许一次审查调用；已有占位/已完成即拒绝（人可 `--reset` 清）。
    - 材料：把 diff/PRD/Check 记录物化到 `round-N/materials/`，reviewer 不再自己算。
    """
    from . import tasks as tasks_mod

    agent = participant_cli(ctx, as_value)
    task_id = task.get("id")
    path = _task_dir(ctx, task)
    record = records.load_json(os.path.join(path, "task.json"))
    reviews = record.get("reviews") or {}
    launches = [entry for entry in reviews.get("launches") or [] if isinstance(entry, dict)]
    if round_no is None:
        if not launches:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "no review round was launched"})
        round_no = max(int(entry.get("round") or 0) for entry in launches)
    round_no = int(round_no)
    if not any(int(entry.get("round") or 0) == round_no for entry in launches):
        raise ReviewError("WF_SEMANTIC_DECISION",
                          {"reason": "round was not launched", "round": round_no,
                           "launched": sorted(int(e.get("round") or 0) for e in launches)})
    anchor, _parts = _current_anchor(ctx, record)
    directory = round_dir(ctx, task_id, round_no)
    materials = os.path.join(directory, "materials")
    os.makedirs(materials, exist_ok=True)
    # 材料物化：diff 相对 HEAD；PRD 与 Check 记录直接复制；测试输出取 Check 的命令记录
    try:
        import subprocess

        diff = subprocess.run(["git", "-c", "safe.directory=*", "diff", "HEAD"], cwd=ctx.root,
                              capture_output=True, text=True, check=False).stdout
    except OSError:
        diff = ""
    records.atomic_write(os.path.join(materials, "diff.patch"), diff or "# 无工作树差异" + chr(10))
    prd_text = tasks_mod.read_prd(ctx.root, record) if hasattr(tasks_mod, "read_prd") else ""
    records.atomic_write(os.path.join(materials, "prd.md"), prd_text or "# PRD 不可读" + chr(10))
    records.write_json(os.path.join(materials, "check.json"),
                       {"check": record.get("check") or {}, "anchor": {"check_anchor": anchor}})
    commands = (record.get("check") or {}).get("commands") or []
    records.write_json(os.path.join(materials, "tests.json"), {"commands": commands})
    target = agent_report_path(ctx, task_id, round_no, agent)
    status = read_agent_status(target)
    if reset:
        if status is None:
            raise ReviewError("WF_PATH_INVALID", {"reason": "no report to reset", "path": target})
        os.remove(target)
        from . import codes as codes_mod

        return codes_mod.result("WF_OK", object={"id": task_id, "name": record.get("title")},
                                position_=codes_mod.position(scope="task", phase=record.get("phase"),
                                                             task_id=task_id),
                                next_="该 agent 本轮记录已清除，可重新运行 review-context 开始审查",
                                facts={"round": round_no, "agent": agent, "cleared": True,
                                       "path": target})
    if status in ("in-progress", "done"):
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "this agent already has a report for the round",
                           "agent": agent, "round": round_no, "status": status, "path": target,
                           "exits": ["换一个审查 agent（须与实施 CLI 及其它审查 CLI 不同）",
                                     "由人清除本轮该 agent 的记录后重试（review-context --reset）"]})
    records.atomic_write(target, (AGENT_HEADER.format(status="in-progress") + chr(10)
                                  + "<!-- 写完正文后把 status=in-progress 改成 status=done -->" + chr(10)))
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": record.get("title")},
        position_=codes.position(scope="task", phase=record.get("phase"), task_id=task_id),
        next_="按 materials 写报告到 report_path，保存时把头部 status 改为 done",
        facts={"round": round_no, "agent": agent, "report_path": target,
               "materials": {"diff": os.path.join(materials, "diff.patch"),
                             "prd": os.path.join(materials, "prd.md"),
                             "check": os.path.join(materials, "check.json"),
                             "tests": os.path.join(materials, "tests.json")},
               "anchor": {"check_anchor": anchor}},
    )


def import_report(ctx, task, round_no=None, slot=None, report_path=None, _from_discovery=False,
                  as_value=None):
    """导入报告（2026-11-07）：可只给 task id——轮次取当前打开的轮，身份取文件名/本会话。

    `report_path` 显式给出时保持旧语义（槽位制），供既有夹具与迁移期使用。
    """
    scan = report_path is None
    discovered = scan or _from_discovery
    declared = review_cli(as_value)
    if declared:
        # `--as X` 的三点一致性（review-identity-protocol §2）：X 必须等于本轮报告文件名 token，
        # 且该轮的 `<task>-<round>/` 目录里必须存在 `review-<X>.md`（占位由 context 创建）。
        # 只给 X 时把它当作筛选条件；同时给了 --slot 则两者必须一致。
        if slot and normalize_agent(slot) != declared:
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "--as conflicts with --slot", "as": declared, "slot": slot})
        slot = declared
    if scan:
        # 扫描本轮暂存目录里所有**已完成**的 `review-<agent>.md`（导入由持写权的主会话执行，
        # 因此不能用调用方身份定位报告——那是 reviewer 侧的事）。
        path = _task_dir(ctx, task)
        record = records.load_json(os.path.join(path, "task.json"))
        launches = [entry for entry in (record.get("reviews") or {}).get("launches") or []
                    if isinstance(entry, dict)]
        if round_no is None:
            if not launches:
                raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "no review round was launched"})
            round_no = max(int(entry.get("round") or 0) for entry in launches)
        round_no = int(round_no)
        directory = round_dir(ctx, task.get("id"), round_no)
        wanted = normalize_agent(slot) if slot else None
        targets = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                candidate = os.path.join(directory, name)
                if not os.path.isfile(candidate):
                    continue
                agent = agent_from_path(candidate)
                if not agent or (wanted and agent != wanted):
                    continue
                if read_agent_status(candidate) != "done":
                    continue
                targets.append((agent, candidate))
        if declared:
            # 占位 = context 写下的 `review-<X>.md` 骨架（身份在文件名）。两因判别（协议 §2）：
            #   目录整体消失，或该文件不存在 ⇒ no_claim（与"从未调用 context"不可区分）；
            #   文件在但未完成 ⇒ staging_evicted（暂存被清理/未写完）。
            claim = os.path.join(directory, f"review-{declared}.md")
            if not os.path.isdir(directory) or not os.path.isfile(claim):
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "no_claim", "as": declared, "round": round_no,
                                   "directory": directory,
                                   "exits": ["由该 reviewer 会话重跑 review-context --as "
                                             + declared + " 生成占位与材料"]})
            if not targets:
                raise ReviewError("WF_PATH_INVALID",
                                  {"reason": "staging_evicted", "as": declared, "round": round_no,
                                   "report": claim,
                                   "exits": ["确认报告已把头部 status 改成 done 后重试导入"]})
        if not targets:
            raise ReviewError("WF_PATH_INVALID",
                              {"reason": "no finished report in this round", "round": round_no,
                               "agent": wanted, "directory": directory,
                               "exits": ["先由 reviewer 会话运行 review-context 并写完报告（status=done）"]})
        results = [import_report(ctx, task, round_no, agent, candidate, _from_discovery=True)
                   for agent, candidate in targets]
        last = results[-1]
        facts = dict((last or {}).get("facts") or {})
        facts["imported_agents"] = [agent for agent, _p in targets]
        last["facts"] = facts
        return last
    if not os.path.isabs(report_path):
        raise ReviewError("WF_PATH_INVALID", {"reason": "report path must be absolute", "path": report_path})
    try:
        with open(report_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise ReviewError("WF_PATH_INVALID", {"reason": f"report unreadable: {exc}", "path": report_path})
    payload = parse_report(text)
    if str(payload.get("task-id")) != str(task.get("id")):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "task-id mismatch", "report": payload.get("task-id")})
    if int(payload.get("round") or 0) != int(round_no):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "round mismatch", "report": payload.get("round")})
    # 身份优先看文件名；正文写了就要一致（2026-11-07：正文不再要求该字段）
    if payload.get("reviewer-id") and normalize_agent(payload.get("reviewer-id")) != normalize_agent(slot):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer-id mismatch", "report": payload.get("reviewer-id")})
    from . import lock

    with lock.acquire(ctx.root, holder_hint="review-import"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.get("reviews") or {}
        launch = None
        for entry in reviews.get("launches") or []:
            if int(entry.get("round") or 0) == int(round_no):
                launch = entry
                break
        if not launch:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "round was not launched", "round": round_no})
        if not _from_discovery:
            slot_paths = [directory for directory in launch.get("temp_paths") or []
                          if os.path.basename(directory.rstrip(os.sep)) == slot]
            if not slot_paths:
                raise ReviewError("WF_REVIEW_INVALID", {"reason": "slot not declared in launch", "slot": slot})
            staging = os.path.realpath(slot_paths[0])
            real_report = os.path.realpath(report_path)
            if not real_report.startswith(staging + os.sep):
                raise ReviewError("WF_PATH_INVALID", {"reason": "report must come from its staging directory",
                                                      "expected": staging, "actual": real_report})
        anchor, _parts = _current_anchor(ctx, task)
        # 导入端先做字段完备性核验（机制稿 §9.2「先读完整报告并核元数据，再导入」）：
        # 缺 excluded-scope 之类的报告不再"导入成功、判定才拒"（第十一轮复审外部项）。
        _missing = [key for key in ("protocol", "task-id", "round",
                                    "review-time", "check-anchor", "read-scope",
                                    "excluded-scope", "axes", "verdict")
                    if key not in payload]
        # 身份由文件名承载（仅发现模式）：正文若仍写 source-cli / reviewer-id 必须与文件名一致
        for field, expected in ((("source-cli", slot), ("reviewer-id", slot)) if discovered else ()):
            if payload.get(field) and normalize_agent(payload.get(field)) != normalize_agent(expected):
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": f"report {field} differs from its file name",
                                   "field": field, "report": payload.get(field),
                                   "file_agent": normalize_agent(expected), "slot": slot})
        if _missing:
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "report missing required fields", "missing": _missing,
                               "slot": slot})
        # 引用必须属于当前批准集合；本任务内改过的规则不得当判据（机制稿 §9.2、K3c）
        index, changed = assertion_index(ctx, task)
        fix_kind = payload.get("check_fix_kind")
        lifted = []
        for finding in payload.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            ref = finding.get("assertion_ref")
            severity = finding.get("severity")
            if not ref:
                if severity in BLOCKING_SEVERITIES:
                    raise ReviewError("WF_REVIEW_INVALID",
                                      {"reason": "blocking finding must cite an assertion_ref",
                                       "finding": finding.get("id"), "slot": slot,
                                       "known": sorted(index)})
                continue
            problem = assertion_ref_problem(ref, index, changed, fix_kind)
            if problem:
                problem["finding"] = finding.get("id")
                problem["slot"] = slot
                raise ReviewError("WF_REVIEW_INVALID", problem)
            if str(ref).split("#", 1)[0] in changed and fix_kind == "broken-reference":
                # 豁免 = 声明 + 人复核（2026-11-09 人裁 B）：旧 check 原文没有落盘，
                # 框架不假装能验证声明为真，改为把它变成"判定时必须有人复核过"的机械前置。
                lifted.append({"finding": finding.get("id"), "assertion_ref": ref,
                               "rule": str(ref).split("#", 1)[0]})
        report_anchor = payload.get("check-anchor")
        if not isinstance(report_anchor, dict):
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "report check-anchor must be an object",
                               "report": report_anchor})
        if report_anchor.get("check_anchor") != anchor:
            saved = ((task.get("check") or {}).get("anchor") or {})
            drift = anchor_drift(saved.get("parts"), _parts)
            facts = {"reason": "check-anchor mismatch", "report": payload.get("check-anchor"),
                     "current_anchor": anchor}
            if drift is None:
                facts["diff_unavailable"] = "旧 check 记录没有 anchor.parts；不按当前内容反推"
            else:
                facts["drift_diffs"] = drift
            raise ReviewError("WF_REVIEW_INVALID", facts)
        # 2026-11-07：目录与文件名统一为 `review/round-N/review-<agent>.md`
        # （与暂存目录同名同构，少一层"哪份是哪份"的解释）。旧名仍可读。
        target_dir = os.path.join(path, "review", f"round-{int(round_no)}")
        os.makedirs(target_dir, exist_ok=True)
        target = os.path.join(target_dir, f"review-{normalize_agent(slot)}.md")
        legacy = os.path.join(path, "review", f"review-round-{int(round_no)}", f"{slot}.md")
        if not os.path.exists(target) and os.path.exists(legacy):
            target = legacy
        existing_digest = records.file_digest(target)
        incoming_digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        if existing_digest and existing_digest != incoming_digest:
            # 同路径不同摘要即冲突：不覆盖、不留旧结论（机制稿 §9.2）
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "report digest differs from the imported one",
                               "slot": slot, "existing": existing_digest, "incoming": incoming_digest},
                              )
        if existing_digest:
            # 同摘要重入：幂等，不重复写
            pass
        else:
            records.atomic_write(target, text)
        digest = records.file_digest(target)
        imported = [entry for entry in reviews.get("imported") or []
                    if not (int(entry.get("round") or 0) == int(round_no) and entry.get("slot") == slot)]
        entry_record = {"round": int(round_no), "slot": slot,
                        "report_path": os.path.relpath(target, str(ctx.root)).replace(os.sep, "/"),
                        "report_digest": digest, "anchor": {"check_id": (task.get("check") or {}).get("id"),
                                                            "check_anchor": anchor}}
        if lifted:
            entry_record["broken_reference"] = {"declared": True, "lifted": lifted}
        if discovered:
            entry_record["agent"] = normalize_agent(slot)
        imported.append(entry_record)
        reviews["imported"] = imported
        task["reviews"] = reviews
        inputs = {"task": task.get("id"), "round": int(round_no), "slot": slot}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.import", holder, inputs, ["verify_metadata", "verify_anchor", "publish"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.import", holder, inputs, action, evidence_refs=[digest]
        )
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_="导入另一槽位报告后 review-decide",
        facts={"round": int(round_no), "slot": slot, "report_digest": digest,
               "verdict": payload.get("verdict"), "findings": payload.get("findings"),
               "control_assertion": assertion},
    )


SENSITIVE_SURFACES = {
    "credentials": (".env", "id_rsa", ".npmrc", ".netrc", "secrets.json"),
    "private-config": (".codex/config.toml", "config.local.json"),
}


def exclusion_gaps(payload):
    """665：`excluded-scope` 不能只「非空」，必须覆盖四类敏感面（2026-11-07 审计结论）。"""
    from . import paths as paths_mod

    patterns = [str(item) for item in payload.get("excluded-scope") or [] if str(item).strip()]

    def covered(samples):
        for pattern in patterns:
            for sample in samples:
                try:
                    if paths_mod.match_path(pattern, sample):
                        return True
                except Exception:  # noqa: BLE001 — 无法解释的模式不算覆盖
                    continue
        return False

    gaps = []
    for name, samples in SENSITIVE_SURFACES.items():
        if not covered(samples):
            gaps.append(name)
    if not any(item.startswith("..") or item.startswith("/") for item in patterns):
        gaps.append("outside-project")
    if not covered([".wf/tasks/other/task.json"]):
        gaps.append("other-task-dirs")
    return gaps


def decide(ctx, task, round_no=None, plan_path=None, unavailable_path=None):
    """判定（2026-11-07）：round 缺省取最新已发起轮；审核者身份取导入记录里的文件名 token。"""
    if round_no is None:
        _path = _task_dir(ctx, task)
        _record = records.load_json(os.path.join(_path, "task.json"))
        _launches = [entry for entry in (_record.get("reviews") or {}).get("launches") or []
                     if isinstance(entry, dict)]
        if not _launches:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "no review round was launched"})
        round_no = max(int(entry.get("round") or 0) for entry in _launches)
    round_no = int(round_no)
    from . import cli, lock

    dispositions = []
    if plan_path:
        loaded = records.load_json(plan_path)
        if loaded is None:
            raise ReviewError("WF_PATH_INVALID", {"reason": "plan file missing", "path": plan_path})
        dispositions = loaded if isinstance(loaded, list) else [loaded]
    unavailable = None
    if unavailable_path:
        unavailable = records.load_json(unavailable_path)
        if not isinstance(unavailable, dict) or not unavailable.get("evidence"):
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "unavailable declaration requires evidence"})
    with lock.acquire(ctx.root, holder_hint="review-decide"):
        _record, holder = ctx.require_held(task=task.get("id"))
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.get("reviews") or {}
        launch = None
        for entry in reviews.get("launches") or []:
            if int(entry.get("round") or 0) == int(round_no):
                launch = entry
                break
        imported = [entry for entry in reviews.get("imported") or [] if int(entry.get("round") or 0) == int(round_no)]
        anchor, _parts = _current_anchor(ctx, task)
        distinct = []
        if unavailable:
            verdict = "unavailable"
            facts = {"unavailable": unavailable}
        else:
            if not imported:
                raise ReviewError("WF_REVIEW_INVALID", {"reason": "no imported report for this round"})
            # 人数与异种按**报告文件名**判定（身份由文件名承载）；
            # 实施 CLI 只读**本轮 launch 记录**（C6）：判定时不从会话猜，避免声明漂移绕过异种门禁。
            implementer = review_cli((launch or {}).get("implementation_cli"))
            if not implementer:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "implementation CLI not declared for this round",
                    "round": round_no,
                    "exits": ["用 review-launch --implementation-cli <cli> 重新发起本轮（报告可复用）"],
                })
            # 新形态（文件名承载身份）：人数按已导入报告的文件名 token 判；
            # 旧形态（槽位制，显式 --report）：仍按 launch 声明的槽位判，并核「声明了却没导入」。
            discovered_mode = any("agent" in entry for entry in imported)
            launch_slots = [normalize_agent(slot.get("slot")) for slot in (launch or {}).get("slots") or []
                            if isinstance(slot, dict) and slot.get("slot")]
            if discovered_mode:
                declared_slot_ids = sorted({normalize_agent(entry.get("agent") or entry.get("slot"))
                                            for entry in imported if entry.get("slot")})
            else:
                declared_slot_ids = sorted(set(launch_slots))
            if len(declared_slot_ids) < 2:
                # 单 reviewer：报告可留档参考，但不产生判定结论（设计稿 §6.5）。
                # 拒绝时把已导入报告与两个合法出口一并给出，避免人误以为"再跑一次就能判"。
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "single reviewer cannot produce a decision (degraded: single-provider)",
                    "declared": declared_slot_ids,
                    "degraded": "single-provider",
                    "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                         for entry in imported],
                    "exits": ["补第二个与实施 CLI 不同、且与它彼此不同的 reviewer CLI 后重发一轮",
                              "按设计稿 §6.5 的不可用处置：review-decide --unavailable <声明文件> 留痕，"
                              "复杂任务暂停或异常归档（不得据此判 pass）"],
                })
            imported_slots = [normalize_agent(entry.get("slot")) for entry in imported]
            missing_slots = ([] if discovered_mode
                             else [slot for slot in declared_slot_ids if slot not in imported_slots])
            if missing_slots:
                # 声明的槽位都要有报告：缺一即输入不完整，不能按已导入的部分判 pass
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "declared slots missing reports", "missing": missing_slots,
                                   "imported": imported_slots})
            source_clis = []
            declared_slots = {slot.get("slot"): slot.get("reviewer_cli")
                              for slot in (launch or {}).get("slots") or []
                              if isinstance(slot, dict) and slot.get("slot")}
            problems = []       # 输入不成立：报告/身份/锚点/材料不合规 → 拒绝，不写结论
            failures = []       # 有效审查给出的未通过结论 → 记 fail，成为复盘触发事实
            proposers = {}      # finding id → 提出它的报告（K4b：关闭不得自证）
            gaps_out = []       # uncovered 轴形成的缺口（走 4.8/4.9，不进 failures）
            for entry in imported:
                rel = entry.get("report_path")
                if not rel:
                    problems.append({"slot": entry.get("slot"), "reason": "imported entry lacks report_path"})
                    continue
                report_abs = join(ctx.root, rel)
                # 导入端防住"同路径换内容"，判定端必须同样重核摘要：否则报告文件可被事后改写
                current_digest = records.file_digest(report_abs)
                if entry.get("report_digest") != current_digest:
                    problems.append({"slot": entry.get("slot"), "reason": "report file changed after import",
                                     "recorded": entry.get("report_digest"), "current": current_digest,
                                     "path": rel})
                    continue
                try:
                    with open(report_abs, "r", encoding="utf-8") as handle:
                        payload = parse_report(handle.read())
                except OSError as exc:
                    problems.append({"slot": entry.get("slot"), "reason": "report file unreadable",
                                     "path": rel, "error": str(exc)})
                    continue
                proposer = normalize_agent(entry.get("agent") or payload.get("source-cli") or entry.get("slot"))
                source_clis.append(proposer)
                for finding in payload.get("findings") or []:
                    if isinstance(finding, dict) and finding.get("id"):
                        proposers.setdefault(str(finding["id"]), proposer)
                report_anchor = payload.get("check-anchor")
                if not isinstance(report_anchor, dict) or report_anchor.get("check_anchor") != anchor:
                    # 失效锚点一律重审，不能因旧文件仍在而复用（机制稿 §9.2）
                    problems.append({"slot": entry.get("slot"), "reason": "report anchor does not match current check",
                                     "report_anchor": report_anchor, "current_anchor": anchor})
                declared_cli = declared_slots.get(entry.get("slot"))
                if declared_cli and payload.get("source-cli") != declared_cli:
                    problems.append({"slot": entry.get("slot"), "reason": "report source-cli not declared for slot",
                                     "source_cli": payload.get("source-cli"), "declared": declared_cli})
                for field in ("read-scope", "excluded-scope"):
                    if not payload.get(field):
                        problems.append({"slot": entry.get("slot"), "reason": f"report lacks {field}"})
                gaps = exclusion_gaps(payload)
                if gaps:
                    problems.append({"slot": entry.get("slot"),
                                     "reason": "excluded-scope does not cover sensitive surfaces",
                                     "missing": gaps})
                # v42 B1：报告声明过的"未覆盖项"不再一义三用（既不判 fail 也不再是必填字段），
                # 统一按**缺口**呈现；三态结论由 axes 的 uncovered 承载。
                for item in payload.get("scope-exceptions") or []:
                    gaps_out.append({"slot": entry.get("slot"),
                                     "reason": "报告声明的未覆盖项（按缺口处置，不判 fail）",
                                     "exception": item})
                axes = payload.get("axes") or {}
                if not isinstance(axes, dict):
                    problems.append({"slot": entry.get("slot"), "reason": "report axes must be an object"})
                    axes = {}
                # S3 判定句（v42 B1）：fail 仅当存在 blocking finding；uncovered 产缺口不产缺陷；
                # 申报的 verdict 必须与推导一致，否则属输入不成立（不写结论、不改阶段）。
                derived, axis_problems, gaps, blocking = derive_verdict(axes, payload.get("findings"))
                for problem in axis_problems:
                    problems.append(dict(problem, slot=entry.get("slot")))
                for gap in gaps:
                    gaps_out.append(dict(gap, slot=entry.get("slot")))
                need = payload.get("material-gaps") or payload.get("missing-materials")
                if need:
                    failures.append({"slot": entry.get("slot"), "reason": "report declares required material gaps",
                                     "gaps": need})
                declared = payload.get("verdict")
                if declared != derived:
                    problems.append({"slot": entry.get("slot"), "reason": "申报 verdict 与推导不一致",
                                     "declared": declared, "derived": derived,
                                     "blocking_findings": [item.get("id") for item in blocking]})
                if blocking:
                    failures.append({"slot": entry.get("slot"), "reason": "report carries blocking findings",
                                     "findings": blocking})
            if problems:
                # 拒绝必须同时给出口（机制稿 §11.1 三档：拒绝不是死路）
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": problems,
                    "exits": ["按问题清单补齐报告（读/排除范围、轴覆盖、锚点、source-cli）后重新导入并判定",
                              "本轮改为不审查：`review-decide --unavailable <声明>` 留痕，任务按复杂或降级处置",
                              "确认无法审查时按异常退出处置，不伪造 pass"],
                })
            distinct = sorted(set(source_clis))
            implementation = {implementer}   # 单值口径：只认本轮声明
            # 输入不成立先拒绝（设计稿 §6.5、机制稿 §9.2，2026-11-05 第二轮复审 N2）：
            # 人数不足或与实施 CLI 重叠属「审查人数不合格」，不产生 verdict，也不进入审查失败历史，
            # 否则会把输入无效记成正式 fail 并触发复盘语义。
            input_problems = []
            if len(distinct) < 2:
                input_problems.append({"reason": "人数不合格：需要两个彼此不同的审查 CLI",
                                       "reviewer_clis": distinct})
            overlap = sorted(implementation & set(distinct))
            if overlap:
                input_problems.append({"reason": "审查 CLI 与实施 CLI 重叠",
                                       "reviewer_clis": distinct, "implementation": sorted(implementation)})
            if input_problems:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": input_problems,
                    "degraded": (launch or {}).get("degraded"),
                    "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                         for entry in imported],
                    "exits": ["补足两个彼此不同、且均异于实施 CLI 的 reviewer 后**用 review-launch 重新发起新一轮**（已导入的坏报告留在原轮，不跨轮复用）",
                              "按设计稿 §6.5 的不可用处置：review-decide --unavailable <声明文件> 留痕，"
                              "复杂任务暂停或异常归档（不得据此判 pass）"],
                })
            verdict = "pass"
            facts = {"reviewer_clis": distinct}
            if gaps_out:
                facts["gaps"] = gaps_out
            reasons = []
            if failures:
                reasons.append({"reason": "审查未通过", "failures": failures})
            if reasons:
                verdict = "fail"
                facts = dict(facts, reasons=reasons)
                if len(reasons) == 1:
                    facts.update({key: value for key, value in reasons[0].items() if key != "reason"})
                    facts["reason"] = reasons[0]["reason"]
        # disposition 结构与其"关闭不得自证"（机制稿 §9.2、K4b）
        problems = dispositions_problems(dispositions, proposers)
        lifted = [item for entry in imported
                  for item in ((entry.get("broken_reference") or {}).get("lifted") or [])]
        problems = problems + broken_reference_problems(lifted, dispositions)
        if problems:
            raise ReviewError("WF_REVIEW_INVALID",
                              {"problems": problems,
                               "proposers": proposers,
                               "reported": [{"slot": entry.get("slot")} for entry in imported],
                               "exits": ["按问题清单补 disposition 字段与复核人后重跑 review-decide",
                                         "把该 finding 标为不处置并在判断清单里写理由（不构成关闭）"]})

        result = {
            "verdict": verdict,
            "round": int(round_no),
            "reviewer_clis": distinct,
            "check_id": (task.get("check") or {}).get("id"),
            "anchor": {"check_id": (task.get("check") or {}).get("id"), "check_anchor": anchor},
            "imported": [{"slot": entry.get("slot"), "report_digest": entry.get("report_digest")} for entry in imported],
            "facts": facts,
            "degraded": (launch or {}).get("degraded"),
        }
        reviews["result"] = result
        # 历史 fail 事实须能重建：把本轮结论落到所在尝试的 outcome（机制稿 §9.2、§11.2）
        attempts = list(reviews.get("attempts") or [])
        for entry in attempts:
            if int(round_no) in (entry.get("round_ids") or []):
                # 尝试级 outcome 单调保留历史失败：同一尝试内前轮 fail 不被后轮 pass 覆盖，
                # 否则 retrospective_triggers 重建不出 review_fail（机制稿 §11.2 的「历史 result=fail」）
                if entry.get("outcome") != "fail":
                    entry["outcome"] = verdict
                break
        if attempts:
            reviews["attempts"] = attempts
        reviews["dispositions"] = list(reviews.get("dispositions") or []) + dispositions
        task["reviews"] = reviews
        inputs = {"task": task.get("id"), "round": int(round_no), "verdict": verdict}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.decide", holder, inputs, ["derive_verdict", "record_dispositions"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.decide", holder, inputs, action,
            evidence_refs=[entry.get("report_path") for entry in imported if entry.get("report_path")],
        )
    from . import codes

    code = "WF_OK" if verdict == "pass" else ("WF_REVIEW_UNAVAILABLE" if verdict == "unavailable" else "WF_REVIEW_INVALID")
    return codes.result(
        code,
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_="verdict=pass 后由人调用 finish" if verdict == "pass" else "补真实审查或按异常退出处置",
        facts={"result": result, "reviewer_clis": result.get("reviewer_clis"),
               "control_assertion": assertion},
    )


def all_findings(ctx, task):
    """报告里的**全部** findings（含已处置），`unaddressed` 只是它的子集。

    骨架需要"全部"（v42 §5.1 的 `findings[]` + 单列 `closures[]`）；把只含未处置的集合
    当成全部，会让"已关闭"的缺陷从清单里消失，也让两个字段变成同一份东西。
    """
    reviews = task.get("reviews") or {}
    closers = {str(item.get("finding_id")) for item in reviews.get("dispositions") or []
               if isinstance(item, dict) and item.get("decision") == "accepted"}
    found = []
    for entry in reviews.get("imported") or []:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("report_path")
        if not rel:
            continue
        path_abs = join(ctx.root, rel)
        if records.file_digest(path_abs) != entry.get("report_digest"):
            continue
        try:
            with open(path_abs, "r", encoding="utf-8") as handle:
                payload, _problems = read_report(handle.read())
        except OSError:
            continue
        if payload is None:
            continue
        for finding in payload.get("findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                found.append({"id": finding.get("id"), "severity": finding.get("severity"),
                              "class": finding.get("class"), "slot": entry.get("slot"),
                              "closed": str(finding["id"]) in closers,
                              "assertion_ref": finding.get("assertion_ref")})
    return found
