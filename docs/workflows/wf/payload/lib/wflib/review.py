"""review.py — 审查发起、导入与判定（机制稿 §9.1、§9.2）。"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile

from . import check as check_mod, config, records, scope as scope_mod, writer as writer_mod
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

# 主会话复核（2026-11-13）：reviewer 报告是辅助证据；主会话必须给出自己的五轴结论。
MAIN_REVIEW_FIELDS = ("task", "round", "axes", "report_review", "finding_review")
MAIN_REVIEW_RELIANCE = ("primary", "partial", "none")
MAIN_REVIEW_CHECKS = ("verified", "disputed", "unable")

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


def report_skeleton(task_id, round_no, check, anchor, launch=None, materials_identity=None):
    """reviewer 手边的完整骨架：状态行 + 协议块 + 字段占位。

    骨架只铺路，不是门禁：未填的轴/verdict 仍会被 `wf lint report` 与导入端报出来。
    excluded-scope/read-scope 由入口预填（2026-11-21）：excluded-scope 取本轮
    mandatory_exclusions 的 launch 口径；read-scope 预填 materials（只读材料包的
    合法默认值）。reviewer 仍可自行申报，但受同一套导入校验约束——预填只让骨架
    默认可过，不放宽任何校验。

    `materials` 预填本轮材料身份（报告绑它读到的版本）：main 会话重物化材料后，
    旧值就对不上并被拒，而不是让旧报告去替新材料作证。
    """
    exclusions = []
    if launch is not None:
        # 与导入校验同一口径（mandatory_exclusions 是唯一合并实现），不另算第二份
        exclusions = sorted(mandatory_exclusions((launch or {}).get("exclusions")))
    payload = {
        "protocol": PROTOCOL,
        "task-id": task_id,
        "round": int(round_no),
        "review-time": records.now_str(),
        "review-focus": REVIEW_FOCUS,
        "check-anchor": {"check_id": (check or {}).get("id"), "check_anchor": anchor},
        "read-scope": ["materials"],
        "excluded-scope": exclusions,
        "axes": {axis: "" for axis in REVIEW_AXES},
        "findings": [],
        "verdict": "",
    }
    if materials_identity:
        payload["materials"] = {"identity": materials_identity}
    return chr(10).join([
        AGENT_HEADER.format(status="in-progress"),
        "<!-- 正文写在这里；保存前把首行 status=in-progress 改成 status=done，"
        "并先跑 `wf lint report --file <本文件>` 一次列全问题 -->",
        "",
        REPORT_MARKER,
        "<!-- axes/verdict/findings 是占位：按材料逐轴填；verdict 取 pass|fail|unavailable；"
        "materials.identity 是本轮材料身份，入口重物化材料后须按新骨架更新 -->",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=1),
        "```",
        "",
    ])


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
            head = handle.read(STATUS_HEAD_CHARS)
    except OSError:
        return None
    return report_status(head)


# --------------------------------------------------------------------------
# A1 槽位身份：`slot` 是**声明名**（记录里的身份键），`agent` 只作展示与文件名。
# 分配/推导只在 `slot_assignment` 里做一次；写入端（review-import）与读取端
# （status_of_round）都只消费它，不得各自实现一套"哪份报告算哪个槽位"。
# --------------------------------------------------------------------------


def declared_slots(launch):
    """本轮声明槽位（声明顺序）：`[(slot, reviewer_cli|None)]`。

    声明顺序即位置分配顺序；`reviewer_cli` 声明了就让槽位与 reviewer 绑定。
    """
    found = []
    for item in (launch or {}).get("slots") or []:
        if isinstance(item, dict) and item.get("slot"):
            found.append((str(item["slot"]), review_cli(item.get("reviewer_cli"))))
    return found


def staged_agents(ctx, task_id, round_no):
    """本轮暂存目录里已出现的报告身份（文件名 token），按名字排序。

    身份由文件名承载。这里数的文件与 `review-import` 扫描的是同一批，所以
    「status 说到位的槽位」与「导入会占用哪个槽位」不会分叉。
    """
    directory = round_dir(ctx, task_id, round_no)
    found = []
    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if os.path.isfile(path):
                agent = agent_from_path(path)
                if agent:
                    found.append(agent)
    return found


def slot_assignment(launch, imported, agents=()):
    """声明槽位 → 身份 的唯一分配点（`review-import` 与 `status_of_round` 共用）。

    规则固定三档，不随调用点变化：
    ① 已导入记录的 `slot` 本身就是声明槽位 → 直接绑定（粘性：重导入不换槽位）；
    ② 声明了 `reviewer_cli` 的槽位按该声明绑定（已导入记录与暂存报告同等对待）；
    ③ 其余身份按名字排序，依次占满剩余的声明槽位（位置分配顺序）。

    返回 `{slot: {"agent", "entry", "derived"}}`。`derived=True` 表示这条绑定是从
    「`slot` 记的是 reviewer 名」的旧记录推导出来的——**只用于展示，不回写记录，
    也不进放行匹配键**（放行键仍取 `imported[].slot` 原值）。没有声明槽位时
    （旧记录 / 未 launch）退化为「槽位 = 身份原值」。
    """
    declared = declared_slots(launch)
    names = [slot for slot, _cli in declared]
    identities = []
    for entry in imported:
        if isinstance(entry, dict):
            identities.append((normalize_agent(entry.get("agent") or entry.get("slot")), entry))
    seen = {name for name, _entry in identities}
    for agent in agents:
        name = normalize_agent(agent)
        if name and name not in seen:
            identities.append((name, None))
            seen.add(name)
    bound, consumed = {}, set()
    if not names:
        for index, (name, entry) in enumerate(identities):
            if name and name not in bound:
                bound[name] = {"agent": name, "entry": entry, "derived": False}
                consumed.add(index)
        return bound
    for index, (name, entry) in enumerate(identities):
        slot = entry.get("slot") if entry else None
        if slot in names and slot not in bound:
            bound[slot] = {"agent": normalize_agent(entry.get("agent") or name),
                           "entry": entry, "derived": False}
            consumed.add(index)
    for slot, cli in declared:
        if slot in bound or not cli:
            continue
        match = next((index for index, (name, _entry) in enumerate(identities)
                      if name == cli and index not in consumed), None)
        if match is None:
            continue
        bound[slot] = {"agent": identities[match][0], "entry": identities[match][1],
                       "derived": False}
        consumed.add(match)
    pending = sorted((index for index in range(len(identities)) if index not in consumed),
                     key=lambda index: identities[index][0])
    free = [slot for slot in names if slot not in bound]
    for index, slot in zip(pending, free):
        name, entry = identities[index]
        bound[slot] = {"agent": name, "entry": entry,
                       "derived": entry is not None and entry.get("slot") != slot}
    return bound


def read_report(text):
    """宽松解析：返回 `(payload, problems)`。结构坏了 payload 为 None。

    只管**结构**（协议标记、json 块、对象形状）；字段、状态头、范围与轴的一致性属于
    "输入面"，由 `report_input_problems` 一处判定——导入、判定、`lint report` 共用，
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
    return payload, []


def parse_report(text):
    """结构解析（不是输入判定）：结构不成立即 `WF_REVIEW_INVALID`。

    字段与范围是否成立由 `report_input_problems` 判定；调用方（导入、判定）按同一份
    问题清单拒绝，不在这里再写一套字段要求。
    """
    payload, problems = read_report(text)
    if problems:
        raise ReviewError("WF_REVIEW_INVALID", problems[0])
    return payload


# 头部状态行只在**前 400 字符**内找：导入的自动发现只扫这一段，lint 必须与它同源，
# 否则"状态行写在报告末尾"的报告会在 lint 处通过、在导入处静默跳过（dogfood 实录）。
STATUS_HEAD_CHARS = 400
STATUS_LINE = re.compile(r"<!-- wf-review-agent:v1 status=([a-z-]+) -->")


def report_status(text):
    """报告头部状态：`done` / `in-progress` / `None`（头部没有状态行）。"""
    if not isinstance(text, str):
        return None
    match = STATUS_LINE.search(text[:STATUS_HEAD_CHARS])
    return match.group(1) if match else None


def report_input_problems(payload, *, task=None, text=None, launch=None, require_done=True,
                          materials_identity=None, materials_required=False,
                          materials_restored=False):
    """报告**输入面**的唯一校验实现（`lint` / `import` / `decide` 共用）。

    此前三处各写一套：`lint` 只核字段存在，导入核字段存在，判定核非空与敏感面——
    结果是"lint 通过 → 导入成功 → 判定失败 → 另开一轮"（dogfood 的格式返工链）。
    共享函数只覆盖输入面；锚点新鲜度、人数/异种、报告摘要一致性仍在导入与判定各自的
    （也是唯一的）位置核。

    `materials_identity` 是本轮材料的**当前**身份（`materials_identity`，可为 None）：报告
    若携带 `materials` 就必须等于它——报告只对它读到的那批字节成立，别的版本要重审。
    `materials_required` 只在**导入**置真：入口能预填，漏填是新报告的信息缺口，不能与
    "旧版本根本没这个字段"混为一谈；判定侧仍按可选处理（在途轮的旧报告要能判完）。
    `materials_restored`：报告按 `--restore` 还原（身份取记录）。此时它自报的旧身份与当前
    不同是预期——不在这里报问题，交给调用方的跨条目判据（混合基线）处理。

    返回 `{checks: {check_name: [problems]}, verdict, gaps, blocking}`：
    - `checks` 供 lint 逐项展示；
    - `verdict`/`gaps`/`blocking` 是 `derive_verdict` 的同一次结果，调用方不重复推导。
    """
    checks = {}
    if not isinstance(payload, dict):
        payload = {}
        add_problem = [{"reason": "report payload must be an object"}]
    else:
        payload = dict(payload)
        add_problem = []

    notes = []

    def add(name, problems, note=None):
        # 通过项也登记：lint 要能回答"这次到底核了哪些面"，只列失败项会让"没核"和"核过"同形。
        checks[name] = list(problems)
        if note and not problems:
            notes.append({"check": name, "note": note})

    shape = list(add_problem)
    for field in ("read-scope", "excluded-scope", "findings"):
        if field in payload and not isinstance(payload.get(field), list):
            shape.append({"reason": f"{field} must be an array", "field": field,
                          "actual": type(payload.get(field)).__name__})
            payload[field] = []
    if "axes" in payload and not isinstance(payload.get("axes"), dict):
        shape.append({"reason": "axes must be an object", "field": "axes",
                      "actual": type(payload.get("axes")).__name__})
        payload["axes"] = {}
    if "round" in payload:
        raw_round = payload.get("round")
        try:
            round_value = int(raw_round)
        except (TypeError, ValueError):
            round_value = 0
        if isinstance(raw_round, bool):
            round_value = 0
        if round_value < 1:
            shape.append({"reason": "round must be a positive integer", "field": "round",
                          "actual": payload.get("round")})
    add("shape", shape)
    findings_shape = []
    seen_finding_ids = set()
    for index, item in enumerate(payload.get("findings") or []):
        if not isinstance(item, dict):
            findings_shape.append({"reason": "finding must be an object", "index": index})
        elif not item.get("id"):
            findings_shape.append({"reason": "finding requires id", "index": index,
                                   "severity": item.get("severity")})
        elif str(item["id"]) in seen_finding_ids:
            findings_shape.append({"reason": "finding id must be unique within one report",
                                   "index": index, "finding_id": item["id"]})
        else:
            seen_finding_ids.add(str(item["id"]))
            severity = item.get("severity")
            if severity not in BLOCKING_SEVERITIES + ("suggestion",):
                # 非法 severity 不能静默落成"非阻塞"：那是把拼写错误变成结论变化。
                findings_shape.append({"reason": "finding severity is not blocking|suggestion",
                                       "index": index, "finding_id": item["id"],
                                       "severity": severity,
                                       "known": list(BLOCKING_SEVERITIES) + ["suggestion"]})
    add("findings-shape", findings_shape)

    status = report_status(text) if text is not None else None
    if text is not None:
        if status is None:
            add("status-head", [{
                "reason": (f"report status header missing from the first "
                           f"{STATUS_HEAD_CHARS} characters"),
                "status": status,
                "exits": ["把 `<!-- wf-review-agent:v1 status=in-progress -->` 放在报告开头"
                             "（骨架写在第一行；判定只读开头前 "
                             f"{STATUS_HEAD_CHARS} 字符）"],
            }])
        elif status == "done":
            add("status-head", [])
        elif status == "in-progress" and not require_done:
            # 预检跑在草稿阶段：in-progress 是预期状态，不是格式错误；
            # 只有导入/判定要求 done。
            add("status-head", [], note="status=in-progress 属草稿；导入前须改为 status=done")
        else:
            add("status-head", [{
                "reason": "report status is not done",
                "status": status,
                "exits": ["把 `<!-- wf-review-agent:v1 status=done -->` 放在报告开头后重新导入"
                             "（骨架写在第一行；判定只读开头前 "
                             f"{STATUS_HEAD_CHARS} 字符）"],
            }])

    add("protocol", [] if payload.get("protocol") == PROTOCOL else [{
        "reason": "unsupported protocol", "protocol": payload.get("protocol"),
        "expected": PROTOCOL}])
    missing = [field for field in REPORT_FIELDS if field not in payload]
    add("required-fields", [{"reason": "missing field", "field": field} for field in missing])
    add("check-anchor", anchor_identity_problems(payload.get("check-anchor"), task))

    # 材料身份（可选字段：此前版本的报告没有它，按"未绑定"记事实，不因此失败）：
    # 报告只对它读到的那批字节成立。给了就必须等于当前身份，否则等于"结论对应的材料已换"。
    if "materials" in payload or materials_required:
        materials_problems = []
        declared_materials = payload.get("materials")
        if declared_materials is None:
            if materials_required and materials_identity:
                materials_problems.append({
                    "reason": "report omits materials.identity while the round has materials",
                    "exits": ["照 report_path 首部的骨架补回 materials 块后重新导入",
                              "入口重物化过材料的，先重跑 review-context 取新骨架"]})
        elif not isinstance(declared_materials, dict):
            materials_problems.append({"reason": "materials must be an object",
                                       "field": "materials",
                                       "actual": type(declared_materials).__name__})
        else:
            declared_identity = str(declared_materials.get("identity") or "")
            if not re.match(r"^sha256:[0-9a-f]{64}$", declared_identity):
                materials_problems.append({
                    "reason": "materials.identity must be 'sha256:' + 64 hex chars",
                    "actual": declared_identity[:80],
                    "exits": ["按骨架重抄 materials 块（骨架在 report_path 首部）"]})
            elif not materials_identity:
                materials_problems.append({
                    "reason": "report declares a material identity but the round has none",
                    "declared": declared_identity,
                    "exits": ["重跑 review-context 物化本轮材料后再导入",
                              "材料已不可还原时开新一轮审查"]})
            elif declared_identity != materials_identity and not materials_restored:
                materials_problems.append({
                    "reason": "report is bound to different round materials",
                    "declared": declared_identity, "current": materials_identity,
                    "exits": ["有备份时把原字节放回再重跑 review-context（原报告仍有效）",
                              "材料确实变了：按新材料重写报告，再开新一轮（同轮已登记摘要不可覆盖）"]})
        add("materials", materials_problems)

    if launch is None and task is not None:
        try:
            round_no = int(payload.get("round") or 0)
        except (TypeError, ValueError):
            round_no = 0
        for entry in (task.get("reviews") or {}).get("launches") or []:
            if isinstance(entry, dict) and int(entry.get("round") or 0) == round_no:
                launch = entry
                break
    if launch is not None and not isinstance(launch, dict):
        launch = None
    readable_for_empty = (launch.get("readable_scope")
                          if isinstance(launch, dict) else None)
    materials_only = (isinstance(readable_for_empty, dict)
                      and not any(readable_for_empty.get(key)
                                  for key in ("business_code", "spec", "paths", "prd")))
    if "read-scope" in payload:
        reads_declared = [str(item) for item in payload.get("read-scope") or [] if str(item).strip()]
        bad_paths = []
        for read in reads_declared:
            if read == "materials" or read.startswith("materials/"):
                continue
            normalized = read.replace("\\", "/")
            if (normalized.startswith(("/", "~"))
                    or (len(normalized) > 1 and normalized[1] == ":")
                    or ".." in normalized.split("/")):
                bad_paths.append(read)
        add("read-scope-path", [{
            "reason": "report read-scope must use project-relative paths",
            "paths": bad_paths,
            "exits": ["改成仓库相对路径", "项目外/绝对路径不在可读面内；停止并回报"],
        }] if bad_paths else [])
        add("read-scope", [] if (reads_declared or materials_only) else [{
            "reason": "report read-scope is empty",
            "exits": ["写清本次实际读取的路径/面；只读材料包时写 materials",
                      "本轮 readable_scope 显式为空时，空数组表示未做仓库补读"]}])
    if "excluded-scope" in payload:
        excluded = payload.get("excluded-scope")
        gaps = exclusion_gaps(payload)
        add("excluded-scope", ([] if excluded else [{"reason": "report excluded-scope is empty"}])
            + ([{"reason": "excluded-scope does not cover sensitive surfaces", "missing": gaps}]
               if excluded and gaps else []))
    if "read-scope" in payload and "excluded-scope" in payload:
        allowed_prd = str(((launch or {}).get("readable_scope") or {}).get("prd") or "").strip()
        add("read-scope-excluded", read_scope_problems(payload, allowed_prd=allowed_prd))
    if launch is not None:
        from . import paths as paths_mod

        reads = [normalize_scope_path(item) for item in payload.get("read-scope") or []
                 if str(item).strip()]
        exclusions = mandatory_exclusions(launch.get("exclusions"))
        overlaps = []
        prd_path = normalize_scope_path(
            ((launch or {}).get("readable_scope") or {}).get("prd") or "")
        for read in reads:
            if read == "materials" or read.startswith("materials/"):
                continue
            if prd_path and read == prd_path:
                continue
            for excluded in exclusions:
                reason = pattern_overlap(read, excluded)
                if reason:
                    overlaps.append({"read": read, "excluded": excluded, "overlap": reason})
                    break
        if overlaps:
            add("read-scope-launch", [{
                "reason": "report read-scope intersects the launch exclusions",
                "overlaps": overlaps,
                "exits": ["把该路径从 read-scope 移除（若确实未读）",
                          "或说明为何需要范围外材料并停止，不自行扩大读取面"],
            }])
        readable = (launch.get("readable_scope")
                    if isinstance(launch.get("readable_scope"), dict) else {})
        if "readable_scope" in launch:
            business = [normalize_scope_path(item) for item in
                        (readable.get("business_code") or readable.get("paths") or [])
                        if str(item).strip()]
            spec = [normalize_scope_path(item) for item in readable.get("spec") or []
                    if str(item).strip()]
            prd = normalize_scope_path(readable.get("prd") or "")
            outside = []
            for read in reads:
                if read == "materials" or read.startswith("materials/"):
                    continue
                if prd and read == prd:
                    continue
                if any(paths_mod.subsumes(read, pattern) for pattern in spec):
                    continue
                if read in (".wf", ".git") or read.startswith((".wf/", ".git/")):
                    # 运行态/控制面不是业务代码；spec 已在上一条显式放行。
                    outside.append(read)
                    continue
                if any(paths_mod.subsumes(read, pattern) for pattern in business):
                    continue
                outside.append(read)
            if outside:
                add("read-scope-readable", [{
                    "reason": "report read-scope is outside the launch readable_scope",
                    "paths": outside,
                    "readable_scope": {"business_code": business, "spec": spec, "prd": prd},
                    "exits": ["把读取面收回到 launch 声明的业务代码/spec/PRD",
                              "只读材料包时写 materials；需要范围外材料时停止并回报"],
                }])

    axes_value = payload.get("axes")
    if isinstance(axes_value, dict):
        verdict, axis_problems, gaps, blocking = derive_verdict(axes_value, payload.get("findings"))
        add("axes-and-verdict", axis_problems)
        if "verdict" in payload:
            add("declared-verdict", [] if payload.get("verdict") == verdict else [{
                "reason": "申报 verdict 与推导不一致",
                "declared": payload.get("verdict"), "derived": verdict}])
    else:
        # 形状不成立时不再推导 verdict：对非对象取 items 会抛异常，也会让"申报不一致"变成噪声
        verdict, gaps, blocking = None, [], []
        add("axes-and-verdict", [{"reason": "axes must be an object"}])
    if shape or findings_shape:
        # 任意集合/对象/枚举形状错误都不产生“通过”结论；逐项问题在各自检查里。
        verdict, gaps, blocking = None, [], []
    return {"checks": checks, "notes": notes, "verdict": verdict,
            "gaps": gaps, "blocking": blocking}


def flatten_checks(checks):
    """把 `report_input_problems` 的分组问题拉平，附上 `check` 名（导入/判定的事实面用）。"""
    flat = []
    for name, problems in checks.items():
        for problem in problems or []:
            item = dict(problem) if isinstance(problem, dict) else {"reason": str(problem)}
            item.setdefault("check", name)
            flat.append(item)
    return flat


# --------------------------------------------------------------------------
# ⑥ 共享事实：放行记录、逐轮决策、结论引用
# 匹配键/口径只在这里定义一次，其余地方只消费，不得各自实现。
# --------------------------------------------------------------------------


def release_key(entry):
    """放行匹配键：`(round, slot, report_digest)`。

    A1 裁定（B）：`slot` 取**记录原值**，不把 agent 名归一成 slot——否则重新引入
    "槽位名与 reviewer 名两种身份"的误配面。`unverifiable` 与放行记录两侧同源。
    """
    return (int(entry.get("round") or 0), entry.get("slot"), entry.get("report_digest"))


def review_required(task):
    """复杂任务才承担 C4（与 `review-passed` 的短路条件同源）。"""
    return (task.get("plan") or {}).get("complexity") == "complex"


def acceptance_records(task):
    """全部放行记录（含已撤销/已消费）：`unknown_acceptances` 的唯一读取点。"""
    return [item for item in ((task.get("reviews") or {}).get("unknown_acceptances") or [])
            if isinstance(item, dict)]


def active_acceptances(task):
    """`released` 的唯一判据：未撤销 **且** 未消费。"""
    return [item for item in acceptance_records(task)
            if not item.get("revoked") and not item.get("consumed")]


def cited_keys(reviews, result=None):
    """当前结论引用的 `(round, slot)` 集合。"""
    result = result if result is not None else (reviews.get("result") or {})
    return {(int(result.get("round") or 0), item.get("slot"))
            for item in result.get("imported") or [] if isinstance(item, dict)}


def release_allowed_for(entry, task, *, cited=None):
    """可放行条件：`!(cited && review_required)`；复杂度取**当前** plan（降级会翻转它）。"""
    if cited is None:
        cited = release_key(entry)[:2] in cited_keys(task.get("reviews") or {})
    return not (cited and review_required(task))


def undecided_rounds(task):
    """已发起、但还没有判定的轮次（升序）。

    导入缺省取最大发起轮，恢复较早一轮就会导错轮；错误里直接列出待处理轮次，
    比让调用方再翻记录猜一次便宜。
    """
    reviews = (task or {}).get("reviews") or {}
    decided = {int(item.get("round") or 0) for item in reviews.get("rounds") or []
               if isinstance(item, dict)}
    result = reviews.get("result") or {}
    if isinstance(result, dict) and result.get("round"):
        decided.add(int(result.get("round") or 0))
    launched = {int(item.get("round") or 0) for item in reviews.get("launches") or []
                if isinstance(item, dict)}
    return sorted(round_no for round_no in launched - decided if round_no > 0)


def inferred_rounds(reviews):
    """`rounds[]` 为空时按 `result` 推断一条（存量回退：`inferred: true`、`decided_at: null`）。"""
    rounds = [item for item in reviews.get("rounds") or [] if isinstance(item, dict)]
    if rounds:
        return rounds
    result = reviews.get("result") or {}
    if not result.get("verdict"):
        return []
    return [{"round": int(result.get("round") or 0), "verdict": result.get("verdict"),
             "check_id": result.get("check_id"), "decided_at": None, "inferred": True}]


def decision_rounds(task):
    return inferred_rounds(task.get("reviews") or {})


def latest_decision(task, round_no):
    """同轮取最新：`decided_at` 最大者，`null` 视为最早。所有消费方走这一个函数。"""
    entries = [item for item in decision_rounds(task)
               if int(item.get("round") or 0) == int(round_no)]
    if not entries:
        return None
    return max(entries, key=lambda item: str(item.get("decided_at") or ""))


def read_imported_report(ctx, entry):
    """重读一条已导入报告：返回 `(payload, cause, reason)`。

    唯一的重读/归因点（`open_findings` / `all_findings` / `proposers_from_history` 共用）：
    `cause` 三分——`None`（可读且摘要一致）/ `missing`（文件不在了）/ `changed`（摘要不符）/
    `unreadable`（权限或解析失败）；`payload` 只在 `cause is None` 时是报告对象。
    """
    rel = entry.get("report_path")
    path = join(ctx.root, rel)
    current_digest, cause, reason = records.file_digest_state(path)
    if cause:
        return None, cause, reason
    if current_digest != entry.get("report_digest"):
        cause = "missing" if current_digest is None else "changed"
        return None, cause, ("报告导入后被删除" if cause == "missing" else "报告导入后被改写")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload, _problems = read_report(handle.read())
    except OSError as exc:
        return None, "unreadable", str(exc)
    if payload is None:
        return None, "unreadable", "report unreadable after import"
    return payload, None, None


def finding_key(round_no, slot, finding_id):
    """finding 的精确身份：`(round, slot, finding_id)`。

    A9：`finding_id` 只在**同一份报告内**唯一；跨轮/跨槽位同名的「新问题」与旧问题
    是两个身份。关闭匹配与提出者索引都只认这个三元组。
    """
    return (int(round_no or 0), str(slot or ""), str(finding_id))


def disposition_keys(dispositions, known):
    """把 dispositions 归到 finding 精确身份：`(resolved, ambiguous, unknown)`。

    - 处置显式写了 `round` + `slot` → 按它定位（唯一无歧义的写法）；
    - 只写 `finding_id` 且只命中一个身份 → 就是它（兼容既有写法）；
    - 命中多个身份 → **歧义**：不关闭；由 AI 在 plan 里补 `round`+`slot` 后重交（机械消歧，不需要人裁）；
    - 命中零个 → 未知（不属任何已导入报告）。

    `known` 是身份集合；`resolved` 是 `{身份: decision}`（三值都收，关闭判定由调用方按
    `accepted` 过滤）。`finding_id` 为空的条目直接跳过（F2：历史形状，读取端容忍）。
    """
    resolved, ambiguous, unknown = {}, [], []
    for item in dispositions or []:
        if not isinstance(item, dict):
            continue
        decision = item.get("decision")
        finding_id = item.get("finding_id")
        if finding_id is None:
            continue
        slot = item.get("slot")
        try:
            round_no = int(item.get("round") or 0)
        except (TypeError, ValueError):
            round_no = 0
        if round_no and slot:
            key = finding_key(round_no, slot, finding_id)
            if key in known:
                resolved[key] = decision
            else:
                unknown.append({"finding_id": finding_id, "round": round_no, "slot": slot,
                                "decision": decision})
            continue
        matches = sorted(key for key in known if key[2] == str(finding_id))
        if len(matches) == 1:
            resolved[matches[0]] = decision
        elif matches:
            ambiguous.append({"finding_id": finding_id, "decision": decision,
                              "candidates": [{"round": key[0], "slot": key[1]} for key in matches],
                              "reason": "同一 finding_id 出现在多轮/多槽位，处置未声明 round+slot"})
        else:
            unknown.append({"finding_id": finding_id, "decision": decision})
    return resolved, ambiguous, unknown


def open_findings(ctx, task):
    """未处置 findings（K8 投影）：重解析已导入报告，按 dispositions 派生。

    报告有 digest、导入后不可改（K4a），所以"重解析"不会与当时的事实分叉；findings 因此
    不需要另存一份（同一事实两处存）。返回
    `{unaddressed, blocking, unavailable, closed, ambiguous}`（A9：`closed` 按
    `(round, slot, finding_id)` 精确身份；`ambiguous` 是归属不明的历史处置，待人裁）。

    ⑥：`blocking`/`unaddressed` 条目带 `round`；`unavailable` 条目带 `cause`（三分的唯一产出点）/
    `round`/`report_digest`，摘要读取的 OSError 归因也在这一处（`cause: "unreadable"`）。
    """
    reviews = task.get("reviews") or {}
    unaddressed, unavailable, found = [], [], []
    for entry in reviews.get("imported") or []:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("report_path")
        if not rel:
            continue
        round_no = int(entry.get("round") or 0)
        payload, cause, reason = read_imported_report(ctx, entry)
        if cause:
            unavailable.append({"slot": entry.get("slot"), "round": round_no,
                                "report_digest": entry.get("report_digest"), "path": rel,
                                "cause": cause, "reason": reason})
            continue
        for finding in payload.get("findings") or []:
            if not isinstance(finding, dict) or not finding.get("id"):
                continue
            item = {"finding_id": finding["id"], "severity": finding.get("severity"),
                    "slot": entry.get("slot"), "round": round_no,
                    "assertion_ref": finding.get("assertion_ref")}
            found.append((finding_key(round_no, entry.get("slot"), finding["id"]), item))
    # 主会话自己核实的 finding（`main_findings`）也是本轮 finding；只取每轮最新一份复核，
    # 旧 supersedes 记录不重复计入。它们与 reviewer finding 用同一个身份/处置空间。
    latest_main = {}
    for entry in reviews.get("main_reviews") or []:
        if isinstance(entry, dict):
            latest_main[int(entry.get("round") or 0)] = entry
    for round_no, entry in latest_main.items():
        for finding in entry.get("main_findings") or []:
            if not isinstance(finding, dict) or not finding.get("id"):
                continue
            item = {"finding_id": finding["id"], "severity": finding.get("severity"),
                    "slot": "main", "round": round_no,
                    "assertion_ref": finding.get("assertion_ref")}
            found.append((finding_key(round_no, "main", finding["id"]), item))
    known = {key for key, _item in found}
    # A9：关闭按精确身份，不按裸 finding_id；歧义条目不关闭、列入待裁
    resolved, ambiguous, _unknown = disposition_keys(reviews.get("dispositions") or [], known)
    checks = {}
    for round_no, entry in latest_main.items():
        for review_item in entry.get("finding_review") or []:
            if not isinstance(review_item, dict) or not review_item.get("finding_id"):
                continue
            slot = review_item.get("slot")
            if slot is None:
                continue
            checks[(int(round_no), str(slot), str(review_item["finding_id"]))] = review_item.get("check")
    accepted = {key for key, decision in resolved.items() if decision == "accepted"}
    # 关闭记录提交在哪个轮：用于判断"旧轮 unable 是否已被后续轮的核实取代"。
    submitted = {}
    for item in reviews.get("dispositions") or []:
        if isinstance(item, dict):
            keys, _ambiguous, _unknown = disposition_keys([item], known)
            if len(keys) == 1:
                submitted[next(iter(keys))] = int(item.get("submitted_round")
                                                  or item.get("round") or 0)
    # 旧记录没有主会话复核时维持既有“accepted 即关闭”；有复核时只认 verified/disputed。
    # unable 只能在**同一轮**阻断：后续轮提交的 accepted 表示核实已完成（证据由判定侧另核）。
    closed = {key for key in accepted
              if not checks or checks.get(key) in ("verified", "disputed")
              or (checks.get(key) == "unable" and submitted.get(key, 0) > int(key[0]))}
    # accepted 但主会话复核仍是 unable（或没有复核状态）不算关闭：unable 保持待核实，
    # 不能靠一条没有证据的 accepted 让 blocking 消失。
    unverified = accepted - closed
    # 已写 rejected/amended 但**不关闭**的处置：如实标注，供 status 显示"已驳回未关闭"（B5）
    unclosed = {key: decision for key, decision in resolved.items()
                if decision in ("rejected", "amended")}
    for key, item in found:
        if key in closed:
            continue
        if key in unclosed:
            item["disposition"] = unclosed[key]
        if key in unverified:
            item["disposition"] = "accepted"
            item["check"] = checks.get(key)
            item["unverified"] = True
        unaddressed.append(item)
    return {"unaddressed": unaddressed,
            "blocking": [item for item in unaddressed if item.get("severity") in BLOCKING_SEVERITIES],
            "unavailable": unavailable,
            "closed": [{"round": key[0], "slot": key[1], "finding_id": key[2]}
                       for key in sorted(closed)],
            "ambiguous": ambiguous}


def round_open_blocking(ctx, task, round_no, extra_dispositions=(), extra_main=None, *,
                        only_round=True):
    """本轮仍未关闭的 blocking（判定用）：复用 `open_findings`，只把本次 dispositions 临时并入。

    `open_findings` 消费的是已落盘 `reviews.dispositions`；判定要问的是"把本次 --plan 也
    算进去之后，本轮还剩哪些未关闭项"。这里不另写关闭匹配逻辑，只构造一个浅拷贝任务。
    `only_round=False` 返回**全部轮次**的未关闭 blocking（pass 判定的任务级校验用：
    pass 结论要求全部已知 blocking 已关闭，只拦本轮会让旧轮 fail 的未处置项被 pass 覆盖、
    再在归档门禁反弹成"可 finish 却被拦"的打架提示）。
    """
    reviews = dict(task.get("reviews") or {})
    reviews["dispositions"] = list(reviews.get("dispositions") or []) + list(extra_dispositions)
    if extra_main is not None:
        reviews["main_reviews"] = list(reviews.get("main_reviews") or []) + [extra_main]
    probe = dict(task, reviews=reviews)
    blocking = open_findings(ctx, probe)["blocking"]
    if only_round:
        return [item for item in blocking if int(item.get("round") or 0) == int(round_no)]
    return blocking


def lint_report(ctx, task, text):
    """报告的一次性全量预检（S3/C2，`wf lint report` 的唯一实现）。

    **不是门禁**：导入与判定仍是权威（锚点新鲜度、材料外发范围、人数/异种、报告正文摘要
    只在那两处核）。但**输入面**（状态头、必需字段、读取/排除范围、轴与 verdict 一致性）
    与导入/判定共用 `report_input_problems`——同一份报告在两处的输入结论必须一致，
    否则会重演"lint 通过 → 导入成功 → 判定失败 → 另开一轮"的协议返工。
    返回 `{ok, problems, checks, axes, verdict, gaps, deprecated_refs}`。
    """
    checks = []
    problems = []

    def done(name, result):
        checks.append({"check": name, "ok": not result, "problems": result})
        problems.extend(result)

    payload, structure_problems = read_report(text)
    if payload is None:
        return {"ok": False, "problems": structure_problems,
                "checks": [{"check": "protocol", "ok": False, "problems": structure_problems}],
                "axes": {}, "verdict": None, "gaps": [], "deprecated_refs": []}

    # 与导入同一份必填判据（`materials_required`）：预检说"过"、导入却因缺字段拒，
    # 是 lint/import 同源纪律要消掉的那类分歧。
    shared = report_input_problems(payload, task=task, text=text, require_done=False,
                                   materials_identity=round_materials_identity(
                                       ctx, task, payload.get("round")),
                                   materials_required=True)
    for name, items in shared["checks"].items():
        done(name, items)
    verdict, gaps = shared["verdict"], shared["gaps"]

    refs = []
    deprecated = []
    findings_for_refs = payload.get("findings") if isinstance(payload.get("findings"), list) else []
    if task is not None:
        index, changed = assertion_index(ctx, task)
        for finding in findings_for_refs:
            if not isinstance(finding, dict):
                continue
            ref = finding.get("assertion_ref")
            if not ref:
                if finding.get("severity") in BLOCKING_SEVERITIES:
                    refs.append({"reason": "blocking finding must cite an assertion_ref",
                                 "finding": finding.get("id")})
                continue
            problem = assertion_ref_problem(ref, index, changed, payload.get("check_fix_kind"), task=task,
                                            finding_location=finding.get("location"))
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

    axes_value = payload.get("axes") if isinstance(payload.get("axes"), dict) else {}
    return {"ok": not problems, "problems": problems, "checks": checks,
            "notes": shared.get("notes") or [],
            "axes": axes_value, "verdict": verdict, "gaps": gaps,
            "deprecated_refs": deprecated,
            "not_checked": ["锚点新鲜度", "材料外发范围", "审查人数与异种", "报告正文摘要（导入/判定处核对）"]}


def derive_verdict(axes, findings):
    """报告三态判定（S3 判定句，v42 B1）：`fail` 仅当存在 blocking finding。

    返回 `(conclusion, problems, gaps, blocking)`：
    - `conclusion` 取 `pass` / `fail` / `unavailable`，只对**已覆盖**的轴成立；
    - `problems` 为"输入不成立"的事实（轴缺失/非法、`fail` 轴没有对应 blocking finding）；
    - `gaps` 为 `uncovered` 轴——它**不是** fail，也不构成审查通过；缺口处置见
      `merged_coverage` / `gap_acceptance`（判定入口）与机制稿 §9.2；
    - 五轴全 `uncovered` 且没有 blocking finding 时，报告自身结论是 `unavailable`：
      "没有发现缺陷"不等于"完成了一次审查"。
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
    if blocking or fail_axes:
        return "fail", problems, gaps, blocking
    if not problems and len(gaps) == len(REVIEW_AXES):
        return "unavailable", problems, gaps, blocking
    return "pass", problems, gaps, blocking


def merged_coverage(main_review, axis_reports):
    """本轮覆盖：主会话复核 + **主会话采信的报告**，两者都未覆盖的轴才是缺口。

    `main_review` 是完整的主会话复核记录（`axes` + `report_review`），或 `None`
    （判定前的状态投影：没有主会话复核时报告原始结论只作展示，不产生 verdict）。

    报告覆盖不是无条件并集：主会话逐报告写 `reliance`，逐轴写 `sources`。
    - `reliance=none`：该报告不贡献覆盖（主会话明确不采信）；
    - `reliance=primary`：该报告的全部 `pass/fail` 轴贡献；
    - `reliance=partial`：只贡献主会话在该轴 `sources` 中明确列出的槽位；
    - 主会话自己的 `pass/fail` 轴始终直接覆盖。

    `pass`/`fail` 都算覆盖（`fail` 是"看过并判不通过"）；`uncovered` 不算。
    返回 `{covered, uncovered, all_uncovered, sources, adopted, report_reliance}`：
    - `sources[axis]` 列出实际覆盖该轴的来源（`main` 与/或槽位）；
    - `adopted` 表示本轮是否按主会话采信过滤（无主会话复核时为 False）；
    - `all_uncovered` 表示两个来源都没有真正覆盖任何轴——那是输入不成立，
      不是"没发现缺陷"。
    """
    main_axes = ((main_review or {}).get("axes") or {}) if isinstance(main_review, dict) else {}
    report_review = {}
    if isinstance(main_review, dict):
        for item in main_review.get("report_review") or []:
            if isinstance(item, dict) and item.get("slot"):
                report_review[str(item["slot"])] = item
    adopted = bool(main_review)
    covered = set()
    sources = {}
    report_reliance = {}
    for axis in REVIEW_AXES:
        found = []
        main_result = (main_axes or {}).get(axis)
        if _axis_conclusion(main_result) in ("pass", "fail"):
            declared = (main_result.get("sources")
                        if isinstance(main_result, dict) else None)
            if isinstance(declared, list) and declared:
                for source in declared:
                    src = str(source)
                    if src == "main":
                        found.append("main")
                    else:
                        found.append(src)
            else:
                found.append("main")
        for slot, axes in (axis_reports or {}).items():
            if not isinstance(axes, dict):
                # 形状不成立的报告由输入面校验拒绝；投影侧要能承受它，不能因 status/判定前置而抛栈
                continue
            conclusion = _axis_conclusion(axes.get(axis))
            if conclusion not in ("pass", "fail"):
                continue
            reliance = (report_review.get(str(slot)) or {}).get("reliance")
            if adopted:
                report_reliance[str(slot)] = reliance
                if reliance not in ("primary", "partial"):
                    continue
                if reliance == "partial":
                    axis_sources = (main_axes.get(axis) or {}).get("sources") \
                        if isinstance(main_axes.get(axis), dict) else None
                    if not isinstance(axis_sources, list) or str(slot) not in axis_sources:
                        continue
            found.append(str(slot))
        if found:
            covered.add(axis)
        sources[axis] = list(dict.fromkeys(found))
    uncovered = [axis for axis in REVIEW_AXES if axis not in covered]
    return {"covered": sorted(covered), "uncovered": uncovered,
            "all_uncovered": not covered, "sources": sources,
            "adopted": adopted, "report_reliance": report_reliance}


def _main_review_ref_key(ref, round_no, known_keys):
    """`finding_refs` 的一项 → 精确身份 `(round, slot, finding_id)`；无法唯一解析时返回 None。"""
    if isinstance(ref, dict):
        slot = ref.get("slot")
        finding_id = ref.get("finding_id")
        if slot is None or finding_id is None:
            return None
        return (int(round_no), str(slot), str(finding_id))
    matches = [key for key in known_keys if key[2] == str(ref)]
    return matches[0] if len(matches) == 1 else None


def coverage_conflicts(main_record, axis_reports, narrowed):
    """收窄材料时 `uncovered` 轴与 `primary` 报告覆盖的矛盾。

    这是覆盖声明之间的矛盾，不是"已知 blocking"本身。判定先让 blocking 形成 fail；
    只有本来要产 pass 时才拒绝，避免已核实缺陷被无关缺口/表单冲突挡住。
    """
    if not narrowed or not isinstance(main_record, dict):
        return []
    axes = main_record.get("axes") or {}
    reliance = {str(item.get("slot")): item.get("reliance")
                for item in main_record.get("report_review") or []
                if isinstance(item, dict) and item.get("slot")}
    conflicts = []
    for axis in REVIEW_AXES:
        entry = axes.get(axis)
        if not isinstance(entry, dict) or _axis_conclusion(entry) != "uncovered":
            continue
        for slot, value in reliance.items():
            if value != "primary":
                continue
            cited = _axis_conclusion(((axis_reports or {}).get(slot) or {}).get(axis))
            if cited in ("pass", "fail"):
                conflicts.append({"axis": axis, "slot": slot, "report_axis": cited})
    return conflicts


def main_review_revision_problems(previous, current_findings, accepted, round_no):
    """主会话复核「替换上一份」的合法边界（唯一定义：register-only 与正式判定共用）。

    两条：① 不能静默丢掉上一份复核里仍开着的 finding；② 不能只改 severity 把 blocking 降级。
    两者都允许"先由 dispositions（slot=main）记录关闭/重分类"——`accepted` 是已接受关闭的
    `(round, "main", finding_id)` 集合。此前 register-only 与正式判定各写一套、结论不一致
    （六轮复核 b.6）。
    """
    previous_ids = {str(item.get("id")) for item in (previous or {}).get("main_findings") or []
                    if isinstance(item, dict) and item.get("id")}
    current_ids = {str(item.get("id")) for item in current_findings
                   if isinstance(item, dict) and item.get("id")}
    still_open = [finding_id for finding_id in sorted(previous_ids - current_ids)
                  if (int(round_no), "main", finding_id) not in accepted]
    previous_severity = {str(item.get("id")): item.get("severity")
                         for item in (previous or {}).get("main_findings") or []
                         if isinstance(item, dict) and item.get("id")}
    current_severity = {str(item.get("id")): item.get("severity")
                        for item in current_findings
                        if isinstance(item, dict) and item.get("id")}
    downgraded = [finding_id for finding_id, severity in previous_severity.items()
                  if severity in BLOCKING_SEVERITIES
                  and current_severity.get(finding_id) not in BLOCKING_SEVERITIES
                  and finding_id in current_severity
                  and (int(round_no), "main", finding_id) not in accepted]
    problems = []
    if still_open:
        problems.append({"reason": "复核不能丢掉上一份里仍开着的 finding", "missing": still_open})
    if downgraded:
        problems.append({"reason": "blocking 降级必须先走 dispositions", "downgraded": downgraded})
    return problems


def merge_main_findings(payload, previous):
    """把本轮主会话 finding 与同轮已有复核**合并**（按 id 并集，机制侧算，不让 AI 重抄）。

    两件事必须分开：
    - `main_findings`：上轮已有、这次没写的按 id 补回（撤项只能走 dispositions）；
    - `finding_review`：这次没显式重写的条目，沿用**上一次的核实状态**——只补 finding
      不补状态，会让"缺省按 verified 记"把旧的 unable 自动改成 verified（机制替 AI 改判断）。
    两者独立判断：即使 finding 全部重写，核实状态也照样继承。
    """
    if not isinstance(payload, dict) or not isinstance(previous, dict):
        return payload
    merged = dict(payload)
    changed = False

    incoming = payload.get("main_findings")
    if isinstance(incoming, list):
        previous_items = [item for item in previous.get("main_findings") or []
                          if isinstance(item, dict) and str(item.get("id") or "").strip()]
        incoming_ids = {str(item.get("id") or "").strip()
                        for item in incoming if isinstance(item, dict)}
        carried = [item for item in previous_items
                   if str(item.get("id") or "").strip() not in incoming_ids]
        if carried:
            merged["main_findings"] = list(incoming) + carried
            changed = True

    previous_review = [item for item in previous.get("finding_review") or []
                       if isinstance(item, dict) and item.get("finding_id")]
    incoming_review = payload.get("finding_review")
    if previous_review and (incoming_review is None or isinstance(incoming_review, list)):
        incoming_review_ids = {(str(item.get("finding_id")), str(item.get("slot")))
                               for item in incoming_review or []
                               if isinstance(item, dict) and item.get("finding_id")}
        carried_review = [item for item in previous_review
                          if (str(item.get("finding_id")), str(item.get("slot")))
                          not in incoming_review_ids]
        if carried_review:
            merged["finding_review"] = list(incoming_review or []) + carried_review
            changed = True

    return merged if changed else payload


def validate_main_review(payload, *, task_id, round_no, imported, findings, open_blocking,
                         axis_reports, by, file_digest=None,
                         assertion_ids=None, changed_rules=None, discovery=False, task=None):
    """主会话复核的结构校验（不是语义判决）。

    返回 `(record, problems, semantic)`：
    - `problems` 是输入不成立（缺字段/轴/覆盖/引用不存在）→ `WF_REVIEW_INVALID`；
    - `semantic` 是"判 fail 但没有可指回的未关闭 finding"这类需要先修复/登记再判的事实 →
      `WF_SEMANTIC_DECISION`；
    - `record` 是入库形态（含 `coverage`），不保存复核文件正文。
    """
    problems, semantic = [], []
    if not isinstance(payload, dict):
        return None, [{"reason": "main review must be a JSON object"}], []
    missing = [field for field in MAIN_REVIEW_FIELDS if field not in payload]
    if missing:
        problems.append({"reason": "main review missing fields", "missing": missing})
    if str(payload.get("task") or "") != str(task_id):
        problems.append({"reason": "main review task does not match", "declared": payload.get("task"),
                         "expected": str(task_id)})
    try:
        declared_round = int(payload.get("round"))
    except (TypeError, ValueError):
        declared_round = None
    if declared_round != int(round_no):
        problems.append({"reason": "main review round does not match", "declared": payload.get("round"),
                         "expected": int(round_no)})

    slots = [str(entry.get("slot")) for entry in imported if entry.get("slot")]
    slot_set = set(slots)
    known_keys = {(int(item.get("round") or 0), str(item.get("slot")),
                   str(item.get("finding_id") or item.get("id")))
                  for item in findings if (item.get("finding_id") or item.get("id"))}
    known_severity = {(int(item.get("round") or 0), str(item.get("slot")),
                       str(item.get("finding_id") or item.get("id"))): item.get("severity")
                      for item in findings if (item.get("finding_id") or item.get("id"))}
    open_keys = {(int(item.get("round") or 0), str(item.get("slot")), str(item.get("finding_id")))
                 for item in open_blocking if item.get("finding_id")}
    main_findings = payload.get("main_findings") or []
    if not isinstance(main_findings, list):
        problems.append({"reason": "main_findings must be a list"})
        main_findings = []
    seen_main = set()
    normalized_main = []
    for item in main_findings:
        if not isinstance(item, dict):
            problems.append({"reason": "main finding must be an object"})
            continue
        finding_id = str(item.get("id") or "").strip()
        if not finding_id:
            problems.append({"reason": "main finding requires id"})
            continue
        if finding_id in seen_main:
            problems.append({"reason": "duplicate main finding id", "finding_id": finding_id})
            continue
        seen_main.add(finding_id)
        severity = str(item.get("severity") or "").strip()
        if not severity:
            problems.append({"reason": "main finding requires severity", "finding_id": finding_id})
        elif severity not in BLOCKING_SEVERITIES + ("suggestion",):
            problems.append({"reason": "main finding severity is not blocking|suggestion",
                             "finding_id": finding_id, "severity": severity,
                             "known": list(BLOCKING_SEVERITIES) + ["suggestion"]})
        if not str(item.get("statement") or "").strip():
            problems.append({"reason": "main finding requires statement", "finding_id": finding_id})
        if not str(item.get("basis") or "").strip():
            problems.append({"reason": "main finding requires basis", "finding_id": finding_id})
        if item.get("severity") in BLOCKING_SEVERITIES:
            ref = str(item.get("assertion_ref") or "").strip()
            if not ref:
                problems.append({"reason": "main blocking finding must cite an assertion_ref",
                                 "finding_id": finding_id})
            elif assertion_ids is not None:
                problem = assertion_ref_problem(ref, assertion_ids, changed_rules or {},
                                                item.get("check_fix_kind"), task=task,
                                                finding_location=item.get("location"))
                if problem:
                    problems.append(dict(problem, finding_id=finding_id))
        normalized_main.append(item)
        key = (int(round_no), "main", finding_id)
        known_keys.add(key)
        if item.get("severity") in BLOCKING_SEVERITIES:
            open_keys.add(key)

    axes = payload.get("axes")
    if not isinstance(axes, dict):
        problems.append({"reason": "main review axes must be an object"})
        axes = {}
    else:
        extra = sorted(set(axes) - set(REVIEW_AXES))
        missing_axes = [axis for axis in REVIEW_AXES if axis not in axes]
        if extra:
            problems.append({"reason": "main review has unknown axes", "axes": extra})
        if missing_axes:
            problems.append({"reason": "main review does not cover all axes", "missing": missing_axes})
        for axis in REVIEW_AXES:
            entry = axes.get(axis)
            if not isinstance(entry, dict):
                problems.append({"reason": "main review axis must be an object", "axis": axis})
                continue
            conclusion = entry.get("conclusion")
            basis = str(entry.get("basis") or "").strip()
            sources = entry.get("sources")
            refs = entry.get("finding_refs") or []
            if not isinstance(refs, list):
                problems.append({"reason": "main review finding_refs must be a list", "axis": axis})
                refs = []
            if conclusion not in AXIS_CONCLUSIONS:
                problems.append({"reason": "main review axis conclusion invalid", "axis": axis,
                                 "conclusion": conclusion, "known": list(AXIS_CONCLUSIONS)})
                continue
            # 粒度收敛（2026-11-21 批D，五轮审查 P1-5）：判 pass/fail 仍必须写 basis，
            # 但允许"一句指向采信来源"（如"与 r1 报告一致，见 sources"）——basis 质量属人/AI
            # 判断，机制只保证不空；复核的独立核实义务由 sources 与 finding_review 承载。
            if conclusion in ("pass", "fail") and not basis:
                problems.append({"reason": "main review pass/fail requires a basis", "axis": axis,
                                 "hint": "与采信报告一致的轴可写一句指向（如'与 r1 一致'），"
                                         "不必逐轴重述完整依据；分歧轴写清差异"})
            if not isinstance(sources, list):
                problems.append({"reason": "main review sources must be a list", "axis": axis})
                sources = []
            unknown = sorted(set(str(item) for item in sources) - (slot_set | {"main"}))
            if unknown:
                problems.append({"reason": "main review sources must be main or imported slots",
                                 "axis": axis, "unknown": unknown})
            if conclusion in ("pass", "fail") and not sources:
                problems.append({"reason": "main review pass/fail requires at least one source",
                                 "axis": axis})
            if conclusion == "uncovered" and refs:
                problems.append({"reason": "main review uncovered axis must not cite finding_refs",
                                 "axis": axis})
            if conclusion == "fail":
                if not refs:
                    semantic.append({"reason": "主会话判 fail 必须指回具体 finding；先修复重查或交人裁决",
                                     "axis": axis, "exits": [
                                         "修复后重跑 task-check，再 review-decide",
                                         "无法修复时登记 judgment（kind=缺口/未核实, outcome=escalated）交人，任务暂停或异常归档；不要伪造 reviewer finding",
                                         "无法覆盖就改判 uncovered，交人接受缺口"]})
                for ref in refs:
                    key = _main_review_ref_key(ref, round_no, known_keys)
                    if key is None:
                        problems.append({"reason": "main review finding_ref is ambiguous or unknown",
                                         "axis": axis, "ref": ref,
                                         "known": [{"round": k[0], "slot": k[1], "finding_id": k[2]}
                                                   for k in sorted(known_keys)][:12]})
                    elif key in open_keys:
                        continue
                    elif key in known_keys:
                        semantic.append({"reason": "主会话判 fail 引用的 finding 已关闭或不是 blocking",
                                         "axis": axis, "ref": ref,
                                         "exits": ["如仍有问题，开新一轮审查或登记新 finding",
                                                   "如已修复，把该轴改判 pass 并写依据"]})
                    else:
                        problems.append({"reason": "main review finding_ref is not from this round",
                                         "axis": axis, "ref": ref})

    report_review = payload.get("report_review")
    if not isinstance(report_review, list):
        problems.append({"reason": "main review report_review must be a list"})
        report_review = []
    seen_slots = set()
    for item in report_review:
        if not isinstance(item, dict):
            problems.append({"reason": "main review report_review entry must be an object"})
            continue
        slot = str(item.get("slot") or "")
        if slot not in slot_set:
            problems.append({"reason": "main review report_review slot was not imported", "slot": slot})
            continue
        if slot in seen_slots:
            problems.append({"reason": "main review report_review has duplicate slot", "slot": slot})
            continue
        seen_slots.add(slot)
        if item.get("reliance") not in MAIN_REVIEW_RELIANCE:
            problems.append({"reason": "main review reliance invalid", "slot": slot,
                             "reliance": item.get("reliance"), "known": list(MAIN_REVIEW_RELIANCE)})
        if not str(item.get("notes") or "").strip():
            problems.append({"reason": "main review report_review requires notes", "slot": slot})
    missing_slots = [slot for slot in slots if slot not in seen_slots]
    if missing_slots:
        problems.append({"reason": "main review does not assess every imported report",
                         "missing": missing_slots})
    reliance_by_slot = {str(item.get("slot")): item.get("reliance")
                        for item in report_review if isinstance(item, dict)}
    for axis, entry in (axes or {}).items():
        if axis not in REVIEW_AXES or not isinstance(entry, dict):
            continue
        if _axis_conclusion(entry) not in ("pass", "fail"):
            continue
        for source in entry.get("sources") or []:
            src = str(source)
            if src == "main":
                continue
            if reliance_by_slot.get(src) == "none":
                problems.append({"reason": "main review cites a report it does not rely on",
                                 "axis": axis, "slot": src,
                                 "exits": ["把该来源改成 main 并写你自己的依据",
                                           "或把 report_review.reliance 改为 primary/partial"]})
            else:
                cited = _axis_conclusion(((axis_reports or {}).get(src) or {}).get(axis))
                if cited not in ("pass", "fail"):
                    problems.append({"reason": "main review cites a report that did not cover this axis",
                                     "axis": axis, "slot": src})
                elif _axis_conclusion(entry) == "pass" and cited == "fail":
                    problems.append({"reason": "main review pass cites a report axis that failed",
                                     "axis": axis, "slot": src,
                                     "exits": ["把该轴改成 fail 并指回未关闭 finding",
                                               "把该报告的 reliance 改为 partial/none，并在具体 finding 的 "
                                  "finding_review.check 写 disputed（disputed 不是 reliance 取值）"]})

    finding_review = payload.get("finding_review")
    if not isinstance(finding_review, list):
        problems.append({"reason": "main review finding_review must be a list"})
        finding_review = []
    seen_keys = set()
    for item in finding_review:
        if not isinstance(item, dict):
            problems.append({"reason": "main review finding_review entry must be an object"})
            continue
        finding_id = item.get("finding_id")
        if not finding_id:
            problems.append({"reason": "main review finding_review requires finding_id"})
            continue
        slot = item.get("slot")
        if slot is None:
            matches = [key for key in known_keys if key[2] == str(finding_id)]
            if len(matches) != 1:
                problems.append({"reason": "main review finding_id is ambiguous; add slot",
                                 "finding_id": finding_id,
                                 "candidates": [{"slot": k[1]} for k in matches][:12]})
                continue
            key = matches[0]
        else:
            key = (int(round_no), str(slot), str(finding_id))
        if key not in known_keys:
            problems.append({"reason": "main review finding_review references an unknown finding",
                             "finding_id": finding_id, "slot": slot})
            continue
        # 唯一推断出的槽位要写回记录；否则后续关闭证据索引只读显式 slot，会漏核。
        item["slot"] = key[1]
        if key in seen_keys:
            problems.append({"reason": "main review finding_review has duplicate finding",
                             "finding_id": finding_id, "slot": slot})
            continue
        seen_keys.add(key)
        if item.get("check") not in MAIN_REVIEW_CHECKS:
            problems.append({"reason": "main review finding check invalid", "finding_id": finding_id,
                             "check": item.get("check"), "known": list(MAIN_REVIEW_CHECKS)})
        if not str(item.get("basis") or "").strip():
            problems.append({"reason": "main review finding_review requires basis",
                             "finding_id": finding_id})
    missing_findings = sorted(known_keys - seen_keys)
    # main_findings 已承载主会话自己的核实依据；finding_review 只作覆盖/override，
    # 缺省按 verified 记，避免让 AI 把自己的同一句依据再抄一遍。
    for key in list(missing_findings):
        if key[1] != "main":
            continue
        source = next((item for item in normalized_main
                       if str(item.get("id")) == key[2]), None)
        if source is None:
            continue
        finding_review.append({"finding_id": key[2], "slot": "main", "check": "verified",
                               "basis": str(source.get("basis") or "")})
        seen_keys.add(key)
    missing_findings = sorted(known_keys - seen_keys)
    # 只有 blocking 必须逐条核实（它决定本轮能不能 pass）。非阻塞建议是否值得本轮深挖
    # 属 AI 在授权内的取舍，未核实不阻断复核成立；已填的条目仍按同一规则校验。
    missing_blocking = [key for key in missing_findings
                        if known_severity.get(key) in BLOCKING_SEVERITIES]
    deferred_suggestions = [{"round": key[0], "slot": key[1], "finding_id": key[2]}
                            for key in missing_findings if key not in missing_blocking]
    if missing_blocking and not discovery:
        # discovery 只登记已核实的 main finding、不产生结论：本轮没有报告，就不能要求
        # 逐条核实 reviewer 的 blocking finding（那属于正式判定轮的义务）。
        problems.append({"reason": "main review does not assess every blocking finding",
                         "missing": [{"round": key[0], "slot": key[1], "finding_id": key[2]}
                                     for key in missing_blocking]})

    if problems or semantic:
        return None, problems, semantic
    record = {"round": int(round_no), "at": records.now_str(), "by": by,
              "file_digest": file_digest, "axes": axes,
              "main_findings": normalized_main,
              "deferred_suggestions": deferred_suggestions,
              "report_review": report_review, "finding_review": finding_review,
              "coverage": merged_coverage({"axes": axes, "report_review": report_review},
                                           axis_reports)}
    return record, [], []


def main_review_draft(ctx, task, round_no, path):
    """生成主会话复核的待填骨架：不产生结论，只铺路。"""
    task = records.load_json(os.path.join(_task_dir(ctx, task), "task.json")) or task
    reviews = task.get("reviews") or {}
    if round_no is None:
        launches = [entry for entry in reviews.get("launches") or [] if isinstance(entry, dict)]
        if not launches:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "no review round was launched"})
        round_no = max(int(entry.get("round") or 0) for entry in launches)
    imported = [entry for entry in reviews.get("imported") or []
                if isinstance(entry, dict) and int(entry.get("round") or 0) == int(round_no)]
    slots = [str(entry.get("slot")) for entry in imported if entry.get("slot")]
    findings = [item for item in all_findings(ctx, task)
                if int(item.get("round") or 0) == int(round_no)]
    slot_axes = {}
    for entry in imported:
        payload, cause, _reason = read_imported_report(ctx, entry)
        if cause is None:
            slot_axes[str(entry.get("slot"))] = (payload or {}).get("axes") or {}
    main_findings = []
    for entry in reviews.get("main_reviews") or []:
        if isinstance(entry, dict) and int(entry.get("round") or 0) == int(round_no):
            main_findings = list(entry.get("main_findings") or [])
    axes = {}
    for axis in REVIEW_AXES:
        axes[axis] = {"conclusion": "", "basis": "", "sources": [], "finding_refs": []}
    draft = {
        "task": task.get("id"),
        "round": int(round_no),
        "axes": axes,
        "main_findings": main_findings,
        "report_review": [{"slot": slot, "reliance": "", "notes": ""} for slot in slots],
        # 只有 blocking 必须逐条核实：给建议也塞空占位，等于逼 AI 为每条规定动作，
        # 或者必须知道"删掉占位"才算延后——那不是机制该要求的知识。
        "finding_review": [{"finding_id": item.get("id"), "slot": item.get("slot"),
                            "check": "", "basis": ""} for item in findings
                           if item.get("slot") != "main"
                           and item.get("severity") in BLOCKING_SEVERITIES],
    }
    target = str(path)
    records.atomic_write(target, json.dumps(draft, ensure_ascii=False, indent=2) + "\n")
    return {"path": target, "round": int(round_no), "slots": slots,
            "findings": len(findings)}


GAP_ACCEPTANCE_DOMAIN = "wf-gap-acceptance-v1"
SINGLE_REVIEWER_ACCEPTANCE_DOMAIN = "wf-single-reviewer-acceptance-v1"


def _masked_quote(value):
    """人确认原话的人读形态（遮罩+截断）：与 authorize/sampling/scale 同源。"""
    from . import authorize as authorize_mod

    return authorize_mod.mask_quote(value)


def single_reviewer_acceptance(decision, round_no, task_id=None):
    """W2-3（三轮裁决④）：人签残余风险接受的单校验点，gap_acceptance 同型。

    单 reviewer 判定的**留痕降级**（不默认）：形状与 attestation 同源
    （`by/at/quote/source`，AI 自述不被接受），另要求 `round` 精确等于本轮、
    `residual_risk` 声明（人对"只审一遍"残余风险的具体接受说明）。
    接受只降级"人数"：主会话复核、未关闭 blocking 等其余门槛照旧，不豁免。
    记录作者归属是声明边界（DSGN §1.5）：文件记录无法可靠辨别人写/模型代笔，
    沿用乙口径来源声明，不新增防伪声明。
    """
    from . import attestation as attestation_mod

    if decision is None:
        return None, []
    problems = list(attestation_mod.problems_of(decision, action="review.single-reviewer-acceptance"))
    if not str(decision.get("residual_risk") or "").strip():
        problems.append({"reason": "single reviewer acceptance requires a residual_risk statement",
                         "action": "review.single-reviewer-acceptance"})
    try:
        accepted_round = int(decision.get("round"))
    except (TypeError, ValueError):
        accepted_round = None
    if accepted_round != int(round_no):
        problems.append({"reason": "single reviewer acceptance round does not match this round",
                         "accepted_round": decision.get("round"), "round": int(round_no)})
    if task_id is not None:
        accepted_task = str(decision.get("task") or decision.get("task-id") or "")
        if accepted_task != str(task_id):
            problems.append({"reason": "single reviewer acceptance task does not match this task",
                             "accepted_task": accepted_task, "task": str(task_id)})
    if problems:
        return None, problems
    digest = records.H(SINGLE_REVIEWER_ACCEPTANCE_DOMAIN,
                       {"by": decision.get("by"), "at": decision.get("at"),
                        "quote": decision.get("quote"), "source": decision.get("source"),
                        "residual_risk": decision.get("residual_risk"),
                        "task": str(task_id) if task_id is not None else None,
                        "round": int(round_no)})
    return {"round": int(round_no), "residual_risk": decision.get("residual_risk"),
            "by": decision.get("by"), "at": decision.get("at"),
            "quote": _masked_quote(decision.get("quote")), "source": decision.get("source"),
            "attestation_digest": digest}, []


def gap_acceptance(decision, uncovered, round_no, task_id=None):
    """人接受覆盖缺口的唯一校验点：`(record, problems)`。

    形状与 `attestation` 同源（`by/at/quote/source`，AI 自述不被接受），另要求
    `round` 精确等于本轮、`axes` 精确等于未覆盖集合——接受"哪些轴没看"是事实，
    不能顺带把别的轴也算作已被接受。
    """
    from . import attestation as attestation_mod

    if decision is None:
        return None, []
    problems = list(attestation_mod.problems_of(decision, action="review.gap-acceptance"))
    axes = decision.get("axes")
    if not isinstance(axes, list) or not all(isinstance(item, str) for item in axes):
        problems.append({"reason": "gap acceptance requires an axes list",
                         "uncovered": list(uncovered)})
    elif sorted(set(axes)) != sorted(uncovered):
        problems.append({"reason": "accepted axes do not match the uncovered axes",
                         "accepted": sorted(set(axes)), "uncovered": sorted(uncovered)})
    try:
        accepted_round = int(decision.get("round"))
    except (TypeError, ValueError):
        accepted_round = None
    if accepted_round != int(round_no):
        problems.append({"reason": "gap acceptance round does not match this round",
                         "accepted_round": decision.get("round"), "round": int(round_no)})
    if task_id is not None:
        accepted_task = str(decision.get("task") or decision.get("task-id") or "")
        if accepted_task != str(task_id):
            problems.append({"reason": "gap acceptance task does not match this task",
                             "accepted_task": accepted_task, "task": str(task_id)})
    if problems:
        return None, problems
    digest = records.H(GAP_ACCEPTANCE_DOMAIN, {"by": decision.get("by"), "at": decision.get("at"),
                                               "quote": decision.get("quote"),
                                               "source": decision.get("source"),
                                               "task": str(task_id) if task_id is not None else None,
                                               "round": int(round_no),
                                               "axes": sorted(uncovered)})
    return {"round": int(round_no), "axes": sorted(uncovered),
            "by": decision.get("by"), "at": decision.get("at"),
            "quote": _masked_quote(decision.get("quote")), "source": decision.get("source"),
            "attestation_digest": digest}, []


def round_entry_gate(task):
    """审查入口的前置事实（唯一实现：`review-status` 投影与 `review-launch` 首报共用）。

    2026-11-25 第四轮复审 F2：已归档对象被 `review-status` 劝去 `review-launch`，
    而后者对归档对象报「规划批准已失效」（归档把 PRD 移走造成的副作用，不是真实原因）。
    这里只把两个可判事实算出来——对象是否终态、外部审查轮是否必需——由消费点决定文案：
    `external_review_required` 取"复杂任务且对象未终态"。轻量任务的完成条件是 Check 的内部
    双轴审查（设计稿 §6.5）；外部审查对它是**可选**工具——需要时可以直接发起，不改变分级与
    完成条件；但发起后报告里的未关闭 blocking 同样进入归档门禁（与复杂任务同口径），
    所以这里只报"是否必需"，不把可选动作写成禁止，也不隐藏它的后果。
    """
    status = task.get("status")
    complexity = (task.get("plan") or {}).get("complexity")
    terminal = status == "archived"
    return {"task_status": status,
            "complexity": complexity,
            "terminal": terminal,
            "external_review_required": (complexity == "complex") and not terminal}


def status_of_round(ctx, task, round_no=None):
    """审查到位状态（S9，`wf review-status` 的唯一实现；只读，不写任何记录）。

    人不必再当传声筒（dogfood D3）：一眼看到"本轮已到 n/2、缺哪份、那份文件现在是什么状态"。
    每槽位的 `state` 取 `missing`（没有文件）/`staged`（已产出未导入）/
    `imported`（已导入且摘要一致）/`stale`（导入后被改写或锚点已失效）。

    A1：槽位取**声明名**（分配只走 `slot_assignment`），`agent` 只作展示；旧记录
    （`slot` 记的是 reviewer 名）在读取时按位置推导并标 `slot_derived`，不回写。
    """
    reviews = task.get("reviews") or {}
    rounds = [entry for entry in reviews.get("launches") or [] if isinstance(entry, dict)]
    if round_no is None:
        round_no = max([int(entry.get("round") or 0) for entry in rounds] or [0])
    round_no = int(round_no)
    launch = next((entry for entry in rounds if int(entry.get("round") or 0) == round_no), None)
    imported = [entry for entry in reviews.get("imported") or []
                if int(entry.get("round") or 0) == round_no]
    task_id = task.get("id")
    assignment = slot_assignment(launch, imported, staged_agents(ctx, task_id, round_no))
    declared = [slot for slot, _cli in declared_slots(launch)] or sorted(assignment)
    try:
        anchor, _parts = _current_anchor(ctx, task)
    except Exception:
        anchor = None
    # 混合基线判据与 decide/check_next_hint 同一实现：逐槽位提示不得与轮级出口打架
    # （restored 槽说"可直接判定"、轮级 next_ 说"撞混合基线"就是同一页两句话）。
    current_materials_identity = round_materials_identity(ctx, task, round_no)
    materials_basis = round_materials_basis(imported, current_materials_identity)
    material_state = materials_identity_state(ctx, task_id, round_no)
    history_round = round_is_history(imported)
    slots = []
    for slot in declared:
        bound = assignment.get(slot) or {}
        entry = bound.get("entry")
        agent = bound.get("agent")
        record = {"slot": slot}
        if agent:
            record["agent"] = agent
        if bound.get("derived"):
            # 旧记录读时推导：`slot` 记的是 reviewer 名，这里只按位置映射到声明槽位
            record["slot_derived"] = True
            record["recorded_slot"] = (entry or {}).get("slot")
        if entry:
            path = join(ctx.root, entry.get("report_path") or "")
            current, cause, reason = (records.file_digest_state(path)
                                      if entry.get("report_path") else (None, None, None))
            record["imported"] = True
            record["report_path"] = entry.get("report_path")
            if cause == "unreadable":
                # C1：读不到不等于被改写，也不等于没有——如实单列，不假装新鲜、不抛栈
                record["state"] = "unreadable"
                record["cause"] = "unreadable"
                record["reason"] = f"报告无法读取：{reason}"
            elif entry.get("report_digest") != current:
                record["state"] = "stale"
                record["stale_cause"] = "report"
                record["reason"] = "报告导入后被改写"
            elif anchor is None:
                # 锚点算不出来（任务记录不完整）：到位但不核锚点，如实标注，不假装新鲜也不假装失效
                record["state"] = "imported"
                record["anchor_checked"] = False
            elif (entry.get("anchor") or {}).get("check_anchor") != anchor:
                # 与导入/判定同一判据（`anchor_identity_problems`）：同锚点换 check_id 是
                # **同内容重验**，报告仍有效——状态页若把它算 stale，恢复会话时 AI 会白等
                # 一份已经到齐的报告。
                record["state"] = "stale"
                record["anchor_checked"] = True
                record["stale_cause"] = "anchor"
                record["reason"] = "锚点已失效（对象/标准/内容变化）"
            elif ((entry.get("materials") or {}).get("identity")
                  and (entry.get("materials") or {}).get("identity")
                  != current_materials_identity):
                # 材料被重出/采纳后换了身份：报告读的那批字节已不可还原，和锚点失效同档
                record["state"] = "stale"
                record["anchor_checked"] = True
                # restore 故意保留旧身份：它与"材料真被换了"是两件事，提示与出口都不同
                if (entry.get("materials") or {}).get("restored"):
                    record["stale_cause"] = "restored-historical"
                    if material_state["state"] == "drift" and not history_round:
                        record["reason"] = ("本轮有 live 报告绑定现场材料，drift 会阻断整轮判定："
                                            "处置见轮级 next_（先放回原字节/重建材料）")
                    elif material_state["state"] in ("legacy", "legacy_adopted"):
                        record["reason"] = ("当前无材料身份（目录仍在、缺 manifest 或按现场字节采纳）："
                                            "重跑 review-context 采纳现场字节（现场字节未改过时身份会复现，"
                                            "原报告继续有效；改过才需重写/新轮）后仍可直接判定")
                    elif material_state["state"] == "unmaterialized" and material_state.get("present"):
                        record["reason"] = ("本轮材料包不完整（缺必需文件）：删除 materials/ 下全部内容后"
                                            "重跑 review-context 重建；不要按旧包采纳")
                    elif current_materials_identity is None:
                        record["reason"] = ("本轮材料目录已不在（当前无材料身份，记录里的旧身份属弱证据）："
                                            "重跑 review-context 重建材料（同 Check 身份会复现）后仍可直接判定；"
                                            "若还有槽位未到，等齐后再判定")
                    elif materials_basis["mixed"]:
                        record["reason"] = ("本轮基线混合（还原条目 + 对不上当前材料的正常条目）："
                                            "直接判定会撞混合基线，处置见轮级 next_")
                    else:
                        record["reason"] = ("现场材料已不是该记录的原证据（身份取记录，属弱身份）："
                                            "该记录可直接判定；若无其他槽位未到，可直接 review-decide，"
                                            "否则等齐后再判定；要恢复可核身份就放回原字节")
                else:
                    record["stale_cause"] = "materials"
                    if material_state["state"] in ("legacy", "legacy_adopted"):
                        record["reason"] = ("当前无材料身份（目录仍在、缺 manifest 或按现场字节采纳）："
                                            "重跑 review-context 采纳现场字节（现场字节未改过时身份会复现，"
                                            "原报告继续有效；改过才需重写/新轮）")
                    elif material_state["state"] == "unmaterialized" and material_state.get("present"):
                        record["reason"] = ("本轮材料包不完整（缺必需文件）：删除 materials/ 下全部内容后"
                                            "重跑 review-context 重建；不要按旧包采纳")
                    elif current_materials_identity is None:
                        record["reason"] = ("本轮材料目录已不在：重跑 review-context 重建（同 Check 身份会复现，"
                                            "现场字节未改过时原报告继续有效）后判定；字节改过才需重写报告/开新一轮")
                    else:
                        record["reason"] = "本轮材料身份已变：报告对应的不是当前材料"
            else:
                record["state"] = "imported"
                record["anchor_checked"] = True
        else:
            record["imported"] = False
            staged = (agent_report_path(ctx, task_id, round_no, agent) if agent else None)
            if staged and os.path.isfile(staged):
                record["state"] = "staged"
                record["staged_path"] = staged
                status = read_agent_status(staged)
                if status:
                    record["agent_status"] = status
            else:
                record["state"] = "missing"
        slots.append(record)
    # 报告在位 ≠ 已完成可导入：in-progress 占位只算“在写”，不能把 arrived/material_ready 说成已齐。
    arrived = [item for item in slots
               if item["state"] == "imported"
               or (item["state"] == "staged" and item.get("agent_status") == "done")]
    writing = [item["slot"] for item in slots
               if item["state"] == "staged" and item.get("agent_status") == "in-progress"]
    staged_unknown = [item["slot"] for item in slots
                      if item["state"] == "staged"
                      and item.get("agent_status") not in ("done", "in-progress")]
    missing = [item["slot"] for item in slots if item["state"] == "missing"]
    stale = [item["slot"] for item in slots if item["state"] == "stale"]
    unreadable = [item["slot"] for item in slots if item["state"] == "unreadable"]
    # B1：材料事实与判定资格**分列**。这里只说"材料齐不齐、能不能用"，
    # 不承诺"能不能判"——那由 `review_eligibility`（与 review-decide 同一个函数）给出提示。
    reviewers = sorted({normalize_agent(item.get("agent") or item.get("slot"))
                        for item in imported if item.get("slot")})
    implementation = {review_cli((launch or {}).get("implementation_cli"))} - {None}
    # 覆盖状态与缺口接受（与 review-decide 同一实现）：状态页要能回答"还差哪几轴/谁接受了缺口"
    axes_reports = {}
    for entry in imported:
        payload, cause, _reason = read_imported_report(ctx, entry)
        if cause is None:
            axes_reports[str(entry.get("slot"))] = (payload or {}).get("axes") or {}
    main_entries = [item for item in ((task.get("reviews") or {}).get("main_reviews") or [])
                    if isinstance(item, dict) and int(item.get("round") or 0) == round_no]
    main = main_entries[-1] if main_entries else None
    coverage = merged_coverage(main, axes_reports)
    coverage["main_review"] = {
        "present": bool(main),
        "file_digest": (main or {}).get("file_digest"),
        "axes": {axis: _axis_conclusion(((main or {}).get("axes") or {}).get(axis))
                 for axis in REVIEW_AXES} if main else {},
        "report_review": (main or {}).get("report_review") or [],
    }
    accepted_axes = sorted({axis
                            for item in ((task.get("reviews") or {}).get("coverage_acceptances") or [])
                            if isinstance(item, dict) and int(item.get("round") or 0) == round_no
                            for axis in item.get("axes") or []})
    coverage["accepted"] = accepted_axes
    # W2-3：单 reviewer 留痕降级可见——本轮有人签残余风险接受记录时如实投影
    single_accepted = [item for item in ((task.get("reviews") or {}).get("single_reviewer_acceptances") or [])
                       if isinstance(item, dict) and int(item.get("round") or 0) == round_no]
    single_reviewer = None
    if single_accepted:
        last = single_accepted[-1]
        single_reviewer = {"accepted": True,
                          "attestation_digest": last.get("attestation_digest"),
                          "by": last.get("by"), "round": round_no}
    elif reviewers and len(reviewers) < 2 and len(declared) < 2:
        single_reviewer = {"accepted": False,
                           "note": "单 reviewer：判定需人签残余风险接受记录（--single-reviewer-acceptance）"}
    return {"round": round_no, "required": len(declared), "arrived": len(arrived),
            "arrived_slots": [item["slot"] for item in arrived], "missing": missing,
            "stale": stale, "unreadable": unreadable,
            "writing": writing, "staged_unknown": staged_unknown,
            "ready_to_import": [item["slot"] for item in slots
                                if item["state"] == "staged"
                                and item.get("agent_status") == "done"],
            "material_ready": (bool(declared) and not missing and not stale and not unreadable
                               and not writing and not staged_unknown),
            "main_review_ready": bool(main) and not bool((main or {}).get("discovery")),
            "eligibility": review_eligibility(reviewers, implementation,
                                             imported_count=len(imported),
                                             declared_slots=len(declared)),
            "coverage": coverage,
            "single_reviewer": single_reviewer,
            "launch_scope": (launch or {}).get("scope"),
            # 材料身份强度与当前身份：`stale` 只说明某份报告对不上，这里给出根因与恢复方向。
            "materials": {"state": material_state["state"],
                          "identity": current_materials_identity,
                          "present": material_state.get("present") or []},
            "slots": slots, "anchor_current": anchor}


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
            file_digest, _file_cause, _file_reason = records.file_digest_state(
                join(ctx.root, spec_path))
            if curation_changed(before, entry["digest"], file_digest):
                changed[spec_path] = {"curation_digest": before, "current_digest": entry["digest"],
                                      "current_file_digest": file_digest}
    # 触碰面路径类引用（2026-11-21 批I，五轮审查 b#2）：`t:<批准触碰面内路径>`。
    # 指引（wf-review-action）要求"批准判据之外、仍在批准触碰面内的缺陷继续修、不降建议"，
    # 此前这类缺陷无法作为 blocking finding 进记录（K4c 只认验收/验证/spec）。登记形状：
    # 与 p:/f: 等证据引用同族——引用的事实是"该路径在本任务批准触碰面内"，可机械核验。
    from . import scope as _scope_mod
    from . import tasks as tasks_mod
    from . import paths as paths_mod

    # 九轮审查 b-3：t: 判据面 = 批准触碰面 ∪ 已生效 expand 单点确认——
    # 按指引"先授权再创建"的面外路径同样可作 blocking 判据。
    _patterns = list(tasks_mod.approved_touch_paths(task) or [])
    _patterns += _scope_mod._expand_authorization_patterns(ctx.root, task)
    for touch in _patterns:
        index[f"t:{touch}"] = "touch-path"
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


STANDARD_PARTS = ("spec_versions", "assertions_digest", "acceptance_digest")


def deprecated_clause_refs(ctx, task):
    """已停用子句的位置集合（`<规则路径>#<子句 id>`），供引用校验直接拒掉。

    与 `spec.rule_digest` 同口径：只看 active 判据的是摘要，deprecated 不再作依据。
    """
    from . import check as check_mod
    from . import spec as spec_mod

    refs = set()
    try:
        versions = check_mod.spec_versions(ctx, task)
    except Exception:
        return refs
    for entry in versions:
        info = spec_mod.load_spec(ctx.root, entry.get("path"))
        for clause in (info or {}).get("metadata", {}).get("clauses") or []:
            if isinstance(clause, dict) and clause.get("status") != "active" and clause.get("id"):
                refs.add(f"{entry.get('path')}#{clause['id']}")
    return refs


def standard_drift_gate(ctx, task):
    """标准面变了却没做判断 → 不能产出 pass（v42 §4.7：框架只标事实，后果是判断）。"""
    from . import check as check_mod

    saved = ((task.get("check") or {}).get("anchor") or {}).get("parts")
    if not isinstance(saved, dict):
        # 旧记录没有 parts：差异不可得。不可得**不是**"没有漂移"，按待决事实交人
        raise ReviewError("WF_SEMANTIC_DECISION",
                          {"reason": "Check 锚点没有 parts，标准面是否变化无法计算",
                           "exits": ["重跑 Check 生成带 parts 的锚点后重新发起审查",
                                     "由人确认按当前标准继续并记录该事实（kind=标准变更）"]})
    try:
        current = check_mod.anchor_parts(ctx, task)
    except Exception as exc:
        raise ReviewError("WF_SEMANTIC_DECISION",
                          {"reason": "锚点重算失败：标准面是否变化无法计算",
                           "error": str(exc)[:200],
                           "exits": ["修好 Check 可重算的前置（记录/spec 可读）后重试",
                                     "由人确认按当前标准继续并记录该事实（kind=标准变更）"]})
    positions = standard_drift_positions(anchor_drift(saved, current) or [])
    if not positions:
        return []
    kinds = {str(item.get("kind")) for item in (task.get("judgments") or []) if isinstance(item, dict)}
    if kinds & {"标准变更", "沿用"}:
        return positions
    raise ReviewError("WF_SEMANTIC_DECISION",
                      {"standard_drift": positions,
                       "reason": "标准面已变，但还没有「标准变更/沿用」判断",
                       "exits": ["补一条 kind=标准变更 的 judgment（写清改了哪条、为什么）",
                                 "判不了就用 outcome=escalated 交人"]})


def standard_drift_positions(diffs):
    """漂移里属于**标准面**的位置（v42 §4.7/§5.3）：标准集合与断言面的摘要变了才算。

    框架只标事实（`standard_drift`）；"还能不能沿用"是判断，由「标准变更/沿用」judgment 承载。
    """
    return [dict(item) for item in (diffs or [])
            if isinstance(item, dict) and item.get("where") in STANDARD_PARTS]


def assertion_ref_problem(ref, index, changed, fix_kind=None, deprecated=None, task=None,
                          finding_location=None):
    """单条引用的判定（K3b 引用属当前集合、K4c 规则不得自证）；返回问题字典或 None。

    `deprecated` 是已停用子句的位置集合（`<规则>#<子句>`）：引用停用判据等于用旧尺子量新活，
    直接拒（v42 §4.5「`d:` 引用 deprecated 条目被拒」同型）。
    """
    ref_text = str(ref)
    if ref_text.startswith("t:"):
        # 触碰面路径引用：只核存在性（glob 按可证包含匹配），不参与"规则不得自证"——
        # 它引用的不是规则，是"缺陷落在批准触碰面内的这一事实"。
        from . import paths as _paths_mod

        target = ref_text[2:]
        # 判据面唯一来源是 index 的 t: 条目（批准触碰面 ∪ 已生效 expand，见 assertion_index）
        patterns = sorted(key[2:] for key in index if key.startswith("t:"))
        if not any(target == pat or target.startswith(pat + "/")
                   or _paths_mod.match_path(pat, target) for pat in patterns):
            return {"reason": "t: 引用的路径不在本任务批准触碰面（含已生效的 expand 确认）内",
                    "assertion_ref": ref_text, "known_t_patterns": patterns,
                    "exits": ["确认缺陷在批准触碰面内，或先 authorize record 一条 choice=expand 后引用",
                              "面外且未扩面确认的缺陷回 Plan 扩面重批"]}
        # 六轮审查 a-1 + 七轮 b-1：t: 引用必须携带并覆盖 finding 的实际位置——
        # 缺 location 的 finding 不得用 t:（否则任意面内路径都能当判据绕过位置核验）。
        if finding_location is None:
            return {"reason": "t: 引用要求 finding 提供 location（缺陷实际位置）",
                    "assertion_ref": ref_text,
                    "exits": ["在 finding 里补 location 字段后重试",
                              "改用验收项/验证项/spec 判据引用"]}
        location = str(finding_location).strip()
        covered = (location == target or location.startswith(target + "/")
                   or _paths_mod.match_path(target, location))
        if not covered:
            return {"reason": "t: 引用与 finding 实际位置不符（引用必须是缺陷位置或其上级目录）",
                    "assertion_ref": ref_text, "finding_location": location,
                    "exits": ["把 t: 改为 finding 实际位置（或其上级目录/触碰面条目）",
                              "缺陷确在别处时：修正 location 或换引用"]}
        return None
    base = ref_text.split("#", 1)[0]
    if deprecated and ref_text in deprecated:
        return {"reason": "引用指向已停用的判据子句（只增不改：停用后不得再作依据）",
                "assertion_ref": ref,
                "exits": ["换用当前 active 的子句或验收项", "若确需恢复该条件，重新加一条新子句"]}
    if base in changed and fix_kind != "broken-reference":
        return {"reason": "assertion_ref 指向本任务内修改过的规则（规则不得自证）",
                "assertion_ref": ref, "changed_rule": changed[base],
                "exits": ["换一条未被本任务修改的判据（活动 spec 规则或验收项）",
                          "若确属 check 的机械纠错，先按 broken-reference 登记并单独复核"]}
    if "#" in str(ref) and index.get(base) == "spec-rule":
        # 具体子句引用必须精确存在（只有整条规则引用才允许只给路径），否则
        # `rule.md#不存在的子句` 会借基础路径放行，等于没核引用。
        if ref not in index and not (base in changed and fix_kind == "broken-reference"):
            return {"reason": "assertion_ref 引用的子句不存在或已停用",
                    "assertion_ref": ref, "known": sorted(index)[:40]}
        return None
    if ref not in index and base not in index:
        return {"reason": "assertion_ref 不属于当前批准集合",
                "assertion_ref": ref, "known": sorted(index)[:40]}
    return None


def broken_reference_problems(lifted, dispositions):
    """`check_fix_kind=broken-reference` 的豁免必须有人复核（2026-11-09 人裁 B）。

    `lifted` 为 import 记录里被声明的 finding（`{finding, assertion_ref, rule}`，调用方补
    `round`/`slot`）；每条都需要**同一条 finding** 的 disposition 且 `recheck_by` 以
    `human:` 开头——框架不验证声明真伪，只保证"声明过的事实一定经过人"。

    A9 的相邻面：匹配按 `(round, slot, finding_id)` 精确身份，不按裸 id——否则同一轮两个
    槽位报同名 finding 时，一次人复核会把另一条也"顺带豁免"。处置只写 `finding_id` 且
    命中多条身份时按歧义处理（不豁免），与关闭链同一套 `disposition_keys` 口径。
    """
    if not lifted:
        return []
    keys = [finding_key(item.get("round") or 0, item.get("slot"), item.get("finding"))
            for item in lifted if isinstance(item, dict)]
    human_dispositions = [item for item in dispositions or []
                          if isinstance(item, dict)
                          and isinstance(item.get("recheck_by"), str)
                          and item["recheck_by"].strip().lower().startswith("human:")]
    resolved, _ambiguous, _unknown = disposition_keys(human_dispositions, set(keys))
    human = set(resolved)
    problems = []
    for item, key in zip([entry for entry in lifted if isinstance(entry, dict)], keys):
        if key in human:
            continue
        problems.append({"finding": item.get("finding"), "assertion_ref": item.get("assertion_ref"),
                         "round": key[0], "slot": key[1],
                         "reason": "broken-reference 豁免需人复核：缺 recheck_by=human:<来源>",
                         "exits": ["为该 finding 补一条 dispositions（decision=accepted，recheck_by=human:<来源>）",
                                   "同一 finding_id 出现在多个槽位时，处置需同时写 round 与 slot",
                                   "或撤回豁免声明，改用未被本任务修改的判据"]})
    return problems




def proposers_from_history(ctx, task):
    """从**全部历史**已导入报告里取「finding 精确身份 → 提出者」（K4b 的独立事实，跨轮有效）。

    A7：导入记录**不保存 findings**（只存路径/摘要/锚点），所以提出者只能重解析报告；
    读取/归因走 `read_imported_report`，与 `open_findings` 同一处，不会与门禁的事实分叉。
    A9：键是 `(round, slot, finding_id)`——同名 id 在不同轮/槽位是不同问题，不能合并。
    """
    proposers = {}
    for entry in (task.get("reviews") or {}).get("imported") or []:
        if not isinstance(entry, dict) or not entry.get("report_path"):
            continue
        payload, cause, _reason = read_imported_report(ctx, entry)
        if cause:
            continue
        proposer = normalize_agent(entry.get("agent") or payload.get("source-cli")
                                   or entry.get("slot"))
        round_no = int(entry.get("round") or 0)
        for finding in payload.get("findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                proposers.setdefault(finding_key(round_no, entry.get("slot"), finding["id"]),
                                     proposer)
    latest_main = {}
    for entry in (task.get("reviews") or {}).get("main_reviews") or []:
        if isinstance(entry, dict):
            latest_main[int(entry.get("round") or 0)] = entry
    for round_no, entry in latest_main.items():
        for finding in entry.get("main_findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                proposers.setdefault(finding_key(round_no, "main", finding["id"]), "main")
    return proposers


def dispositions_problems(dispositions, proposers):
    """dispositions 的结构校验与"关闭不得自证"（机制稿 §9.2、K4b）。纯函数，便于单测。

    A9：提出者与关闭匹配都按 `(round, slot, finding_id)`。只写 `finding_id` 且同时命中
    多轮/多槽位时**不猜**：拒绝并给出候选，要求显式补 `round`+`slot` 后重跑。
    """
    known = set(proposers)
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
        keys, ambiguous, unknown = disposition_keys([item], known)
        if unknown:
            # 任意 id 都能被"关闭"等于关闭一个不存在的发现：必须拒绝并给出可选集合
            problems.append({"index": index, "finding_id": finding_id,
                             "reason": "finding_id 不属任何已导入报告",
                             "known": [{"round": key[0], "slot": key[1], "finding_id": key[2]}
                                       for key in sorted(known)][:12]})
            continue
        if ambiguous:
            problems.append({"index": index, "finding_id": finding_id,
                             "reason": "同一 finding_id 出现在多轮/多槽位，处置需声明 round+slot",
                             "candidates": ambiguous[0]["candidates"],
                             "exits": ["在处置里补 round（finding 提出时的轮次）与 slot（该轮的槽位）后重跑"]})
            continue
        key = next(iter(keys))
        proposer = proposers.get(key)
        recheck_by = normalize_agent(item.get("recheck_by")) if item.get("recheck_by") else None
        if recheck_by is None:
            problems.append({"index": index, "finding_id": finding_id,
                             "round": key[0], "slot": key[1],
                             "reason": "关闭需复核人：recheck_by 缺失",
                             "exits": ["补 recheck_by（不得由提出该 finding 的报告复核）"]})
        elif proposer and recheck_by == proposer:
            problems.append({"index": index, "finding_id": finding_id,
                             "round": key[0], "slot": key[1],
                             "reason": "关闭复核不得自证：复核人与提出者是同一份报告",
                             "proposer": proposer, "recheck_by": recheck_by})
    return problems


def evidence_ref_problems(ctx, task, refs, include_history=False, check_id=None):
    """关闭证据的可解析性：引用必须存在，verification 必须 passed。

    证据是否足以证明修复仍是 AI 判断；这里只核"引用能不能解析、验证是否通过"这两类
    可直接核对的事实，避免不存在的 `v:` 或未通过的验证被当成关闭证据。
    """
    plan = task.get("plan") or {}
    acceptance = {str(item.get("id")) for item in plan.get("acceptance") or []
                  if isinstance(item, dict) and item.get("id")}
    # 计划只提供验证项定义；是否通过以 Check 的实际执行记录为准。
    check_entries = [task.get("check")] + list(task.get("check_history") or [])
    target_check = None
    missing_bound = False
    if check_id:
        target_check = next((entry for entry in check_entries
                             if isinstance(entry, dict) and entry.get("id") == check_id), None)
        # 绑定的那次 Check 不存在时**不能**退回当前 Check 解析：那等于把"不可核实的
        # 历史证据"解释成"当前验证通过"，与"不跨同名验证项串用"自相矛盾。
        missing_bound = target_check is None
    verifications = {}
    if missing_bound:
        return [{"reason": "evidence bound to a Check that no longer exists",
                 "check_id": str(check_id)}]
    if target_check is not None:
        # 关闭记录绑定到哪次 Check，就用哪次 Check 的 commands；不跨同名验证项串用。
        for item in target_check.get("commands") or []:
            if isinstance(item, dict) and item.get("verification_id"):
                verifications[str(item["verification_id"])] = item.get("status")
    else:
        verifications = {str(item.get("id")): None
                         for item in plan.get("verifications") or []
                         if isinstance(item, dict) and item.get("id")}
        for item in (task.get("check") or {}).get("commands") or []:
            if isinstance(item, dict) and item.get("verification_id"):
                vid = str(item["verification_id"])
                if vid in verifications:
                    verifications[vid] = item.get("status")
        if include_history:
            # 旧关闭没有 check_id 时才按历史回退；有绑定就只认绑定那次。
            for entry in task.get("check_history") or []:
                if not isinstance(entry, dict):
                    continue
                for item in entry.get("commands") or []:
                    if isinstance(item, dict) and item.get("verification_id"):
                        vid = str(item["verification_id"])
                        verifications.setdefault(vid, None)
                        verifications[vid] = item.get("status")
    findings = {str(item.get("id")) for item in all_findings(ctx, task)
                if isinstance(item, dict) and item.get("id")}
    judgments = {str(item.get("id")) for item in task.get("judgments") or []
                 if isinstance(item, dict) and item.get("id")}
    paths = {str(item) for item in
             ((task.get("entry_snapshot") or {}).get("touch_paths") or []) +
             (plan.get("touch_paths") or []) if str(item).strip()}
    try:
        delivery = scope_mod.delivery_set(ctx.root, task)
        paths.update(str(item) for item in delivery.get("paths") or [])
    except Exception:
        pass
    problems = []
    for ref in refs:
        text = str(ref).strip().split("@", 1)[0]
        if not text:
            problems.append({"reason": "evidence_ref is empty", "ref": ref})
            continue
        if text.startswith("v:"):
            vid = text[2:]
            if vid not in verifications:
                problems.append({"reason": "evidence_ref verification does not exist",
                                 "ref": ref})
            elif verifications.get(vid) != "passed":
                problems.append({"reason": "evidence_ref verification did not pass",
                                 "ref": ref, "status": verifications.get(vid)})
        elif text.startswith("a:"):
            if text[2:] not in acceptance:
                problems.append({"reason": "evidence_ref acceptance does not exist", "ref": ref})
        elif text.startswith("f:"):
            if text[2:] not in findings:
                problems.append({"reason": "evidence_ref finding does not exist", "ref": ref})
        elif text.startswith("p:"):
            if text[2:] not in paths:
                problems.append({"reason": "evidence_ref path is not in delivery/touch paths",
                                 "ref": ref})
        elif text.startswith("j:"):
            if text[2:] not in judgments:
                problems.append({"reason": "evidence_ref judgment does not exist", "ref": ref})
        elif text.startswith("d:"):
            saved = ((task.get("check") or {}).get("anchor") or {}).get("parts")
            try:
                _anchor, current = check_mod.current_anchor(ctx, task)
                drift_ids = {str(item.get("id")) for item in
                             (anchor_drift(saved, current) or [])
                             if isinstance(item, dict) and item.get("id")}
            except Exception:
                drift_ids = set()
            if text not in drift_ids:
                problems.append({"reason": "evidence_ref drift position does not exist",
                                 "ref": ref, "known": sorted(drift_ids)[:20]})
        else:
            problems.append({"reason": "evidence_ref prefix is not a resolvable closure evidence",
                             "ref": ref,
                             "exits": ["用 v:/a:/f:/p:/j: 中可解析的引用",
                                       "改规则/基线用 p:<该路径>（须在交付面内），并重跑 Check",
                                       "d: 只有在当前锚点差异中确有该位置时才可用"]})
    return problems


def verified_closure_problems(dispositions, main_record, proposers, round_no, main_checks=None,
                              evidence_check=None, historical_evidence_check=None,
                              current_dispositions=None):
    """`verified` finding 的 accepted 关闭必须有 evidence_refs。

    同时检查**已落盘**与**本次** dispositions：`--register-only` 先写入的空证据关闭，
    不能靠下一次无 plan 的 decide 绕过。
    """
    checks = dict(main_checks or {})
    for item in (main_record or {}).get("finding_review") or []:
        if isinstance(item, dict) and item.get("slot") and item.get("finding_id"):
            checks[(int(round_no), str(item["slot"]), str(item["finding_id"]))] = item.get("check")
    # 同一 finding 的关闭是 append-only；判定按**最新一条**处置，旧空证据被后续有效处置
    # 或 amended 覆盖后不应继续阻断（否则“补齐证据/撤回关闭再重试”永远过不了）。
    latest = {}
    for item in dispositions:
        if not isinstance(item, dict):
            continue
        keys, _ambiguous, _unknown = disposition_keys([item], set(proposers))
        if len(keys) != 1:
            continue
        latest[next(iter(keys))] = item
    current_keys = set()
    for item in current_dispositions or []:
        if not isinstance(item, dict):
            continue
        keys, _ambiguous, _unknown = disposition_keys([item], set(proposers))
        current_keys.update(keys)
    problems = []
    for key, item in latest.items():
        if item.get("decision") != "accepted":
            continue
        status = checks.get(key)
        later_round = int(item.get("submitted_round") or 0) > int(key[0])
        if status == "unable" and later_round:
            # 旧轮 unable 被后续轮的 accepted 取代时，核实责任落在这条处置上：
            # 没有可解析证据就不算完成，不能"换一轮就自动关闭"。
            status = "verified"
        if status != "verified":
            continue
        refs = item.get("evidence_refs") or []
        if not refs:
            problems.append({"reason": "verified finding closure requires evidence_refs",
                             "finding_id": item.get("finding_id"), "slot": item.get("slot"),
                             "exits": ["补 evidence_refs 指向关闭所用的验证/证据",
                                       "或把 finding_review.check 改为 disputed（误报/重分类）"]})
            continue
        current_problems = (evidence_check(refs, item.get("check_id"))
                            if evidence_check is not None else [])
        # 有 check_id 的关闭已经绑定那次 Check；历史回退只给没有绑定的旧关闭。
        is_current = current_keys is not None and key in current_keys
        if (current_problems and not is_current and not item.get("check_id")
                and historical_evidence_check is not None):
            historical_problems = historical_evidence_check(refs)
            if not historical_problems:
                current_problems = []
        for problem in current_problems:
            problems.append(dict(problem, finding_id=item.get("finding_id"),
                                 slot=item.get("slot")))
    return problems


def _current_anchor(ctx, task):
    try:
        anchor, parts = check_mod.current_anchor(ctx, task)
    except check_mod.CheckError as exc:
        raise ReviewError(exc.code, exc.facts)
    return anchor, parts


DEFAULT_EXCLUSIONS = (".env", "**/.env", "id_rsa", "**/id_rsa", ".npmrc", "**/.npmrc",
                      ".netrc", "**/.netrc", "secrets.json", "**/secrets.json",
                      ".codex/config.toml", "**/.codex/config.toml",
                      "config.local.json", "**/config.local.json",
                      "../**", ".wf/tasks/**")


def mandatory_exclusions(extras=()):
    """必排面 + 本轮追加；请求只能加，不能整体替换掉敏感面。"""
    merged = list(DEFAULT_EXCLUSIONS)
    values = [extras] if isinstance(extras, str) else (
        extras if isinstance(extras, (list, tuple)) else [])
    for item in values:
        text = str(item).strip()
        if text and text not in merged:
            merged.append(text)
    return merged


def task_prd_path(ctx, task):
    """任务 PRD 的仓库相对路径（发起声明、材料校验与物化共用）。"""
    from . import tasks as tasks_mod

    directory = tasks_mod.task_dir(ctx.root, task.get("id")) or ""
    relative_dir = os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/") if directory else ""
    return f"{relative_dir}/prd.md" if relative_dir else "prd.md"


def scope_binding_problems(ctx, task, launch, delivery):
    """launch 的 `submitted_scope` 与可物化事实是否一致（声明即物化输入）。

    只核可机械比较的三项：diff 路径是交付集合的子集、需求材料是本任务 PRD、测试结果是
    当前 Check。路径扩大或指向别的对象即拒绝；缩小允许，由 `write_materials` 按声明物化。
    """
    submitted = (launch or {}).get("submitted_scope") or {}
    problems = []
    diff = submitted.get("diff")
    if isinstance(diff, dict):
        paths = diff.get("paths")
        if not isinstance(paths, list):
            problems.append({"reason": "submitted_scope.diff.paths must be an array",
                             "value": paths,
                             "exits": ["补 diff.paths（只能是当前交付集合的子集）；旧请求可去掉 --launch-request 让入口重建"]})
        else:
            unique = sorted({str(item) for item in paths})
            allowed = set(delivery.get("paths") or [])
            outside = sorted(item for item in unique if item not in allowed)
            if outside:
                problems.append({"reason": "submitted_scope.diff.paths outside delivery_set",
                                 "paths": outside,
                                 "exits": ["只声明交付集合内的路径；要扩大范围先回 Plan 扩面并重新 Check"]})
            exclusions = mandatory_exclusions((launch or {}).get("exclusions"))
            overlaps = []
            for path in unique:
                for excluded in exclusions:
                    reason = pattern_overlap(path, excluded)
                    if reason:
                        overlaps.append({"path": path, "excluded": excluded, "overlap": reason})
                        break
            if overlaps:
                problems.append({"reason": "submitted_scope.diff.paths intersects launch exclusions",
                                 "overlaps": overlaps,
                                 "exits": ["把这些路径从 diff.paths 移除；它们本轮已被排除",
                                           "若确需审查，先调整 exclusions 与授权后重新 launch"]})
        base = diff.get("diff_base")
        if base not in (None, "", task.get("baseline_head")):
            problems.append({"reason": "submitted_scope.diff.diff_base is not the task baseline",
                             "declared": base, "baseline": task.get("baseline_head")})
    # 旧请求把三类材料写成 bool；不把它当新形状，留给 context 回退交付集合。
    requirement = submitted.get("requirement")
    if isinstance(requirement, str) and requirement and requirement != task_prd_path(ctx, task):
        problems.append({"reason": "submitted_scope.requirement is not this task PRD",
                         "declared": requirement, "expected": task_prd_path(ctx, task)})
    tests = submitted.get("test_results")
    if isinstance(tests, dict):
        check_id = tests.get("check")
        current_check = task.get("check") or {}
        if check_id and check_id != current_check.get("id"):
            # 同锚点重跑 Check 只是同内容重验：材料范围不该因此被拒（十三轮 a-3）。
            declared_anchor = tests.get("check_anchor")
            current_anchor = (current_check.get("anchor") or {}).get("check_anchor")
            if not (declared_anchor and declared_anchor == current_anchor):
                problems.append({"reason": "submitted_scope.test_results.check is not the current Check",
                                 "declared": check_id, "current": current_check.get("id"),
                                 "declared_anchor": declared_anchor,
                                 "current_anchor": current_anchor})
    return problems


def review_scope_facts(ctx, task, launch):
    """判定要消费的材料范围事实：选中、未选、总数、是否收窄/旧形状。

    只记录事实，不判断"未选路径是否影响结论"——那是主会话复核的判断。判定结果带上
    `unselected`，只看 verdict 的调用方也能知道本轮证据支撑面。
    """
    launch = launch or {}
    scope = launch.get("scope") or {}
    submitted = launch.get("submitted_scope") or {}
    diff = submitted.get("diff") if isinstance(submitted, dict) else None
    legacy = not isinstance(diff, dict) or bool(scope.get("legacy"))
    selected = None
    if isinstance(diff, dict) and isinstance(diff.get("paths"), list):
        selected = sorted({str(item) for item in diff.get("paths") or []})
    total = scope.get("total")
    unselected = None
    recompute_failed = False
    if selected is None and legacy:
        # 旧布尔/缺省 launch 没有 paths：按当前交付集合减必排/本轮排除面重算，
        # 否则判定会把“实际已裁剪”的材料当成完整材料（narrowed=None）。
        try:
            delivery = scope_mod.delivery_set(ctx.root, task)
            all_paths = list(delivery.get("paths") or [])
            exclusions = mandatory_exclusions(launch.get("exclusions"))
            selected = [path for path in all_paths
                        if not any(pattern_overlap(path, excluded) for excluded in exclusions)]
            total = len(all_paths) if total is None else total
            chosen = set(selected)
            unselected = sorted(path for path in all_paths if path not in chosen)
        except Exception:
            selected = None
            recompute_failed = True
    if selected is not None and unselected is None:
        try:
            delivery = scope_mod.delivery_set(ctx.root, task)
            all_paths = list(delivery.get("paths") or [])
            total = len(all_paths) if total is None else total
            chosen = set(selected)
            unselected = sorted(path for path in all_paths if path not in chosen)
        except Exception:
            unselected = None
            recompute_failed = True
    narrowed = scope.get("narrowed")
    if narrowed is None:
        if selected is not None and total is not None:
            narrowed = len(selected) < total
        elif isinstance(scope.get("selected"), int) and total is not None:
            narrowed = scope["selected"] < total
    return {"selected": selected if selected is not None else scope.get("selected"),
            "unselected": unselected, "total": total, "narrowed": narrowed,
            "legacy": legacy, "scope_recompute_failed": recompute_failed}


def _deep_merge_launch_request(base, override):
    """四轮审查：launch 请求的**嵌套字段级**深合并（dict 逐键下沉；列表/标量整体替换）——
    只覆盖 submitted_scope.diff.paths 之类局部项时不再连带丢掉其余默认材料。
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_launch_request(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_launch_request(ctx, task, implementation_cli=None):
    """按当前对象生成发起请求（材料三类、只读范围、排除面都由入口算）。

    `submitted_scope` 是"要外发什么"的声明，内容仍由 `review-context` 物化到暂存目录；
    这里给的是三类材料的**来源与摘要**，不是第二份材料本体。
    """
    from . import scope as scope_mod
    from . import tasks as tasks_mod

    delivery = scope_mod.delivery_set(ctx.root, task)
    # 默认请求必须能被同一套范围校验接受：先把必排面从 diff.paths 去掉，
    # 不把“生成请求 → 被自己拒绝 → 让 AI 手写”的返工留给调用方。
    default_exclusions = mandatory_exclusions()
    diff_paths = [path for path in delivery["paths"]
                  if not any(pattern_overlap(path, excluded)
                             for excluded in default_exclusions)]
    touch_paths = tasks_mod.approved_touch_paths(task)
    business = sorted(path for path in touch_paths if not str(path).startswith(".wf/"))
    curation = [entry.get("path") for entry in task.get("curation") or []
                if isinstance(entry, dict) and entry.get("path") and not entry.get("released")]
    prd_path = task_prd_path(ctx, task)
    check = task.get("check") or {}
    commands = [{"verification_id": item.get("verification_id"), "status": item.get("status")}
                for item in check.get("commands") or [] if isinstance(item, dict)]
    return {
        "implementation_clis": [implementation_cli] if implementation_cli else [],
        "slots": [{"slot": "s1"}, {"slot": "s2"}],
        "submitted_scope": {
            "diff": {"source": "delivery_set", "diff_base": task.get("baseline_head"),
                     "paths": sorted(diff_paths)},
            "requirement": prd_path,
            # `check_anchor` 必须一起给：同内容重跑时范围校验按它复用（十四轮 a-2）
            "test_results": {"check": check.get("id"),
                             "check_anchor": (check.get("anchor") or {}).get("check_anchor"),
                             "commands": commands},
        },
        # 设计稿 §6.5：允许自主读取的是业务代码、spec 与 PRD；触碰面只是审查重点，不是读取上限。
        "readable_scope": {"business_code": ["**"], "focus_paths": business,
                           # 设计稿 §6.5：spec 是可读面，不止本任务策展过的条目；
                           # 默认放行运行时 spec 树与策展条目，避免“查相邻规则”变成越界。
                           "spec": sorted(set(curation) | {".wf/spec/**", ".wf/baseline.md"}),
                           "prd": prd_path},
        "exclusions": list(DEFAULT_EXCLUSIONS),
    }


def launch_preview(ctx, task, request_path=None, implementation_cli=None):
    """三轮三审 b8：`review-launch --preview` 的只读出口——按当前对象生成（并与
    `--launch-request` 覆盖/补充合并后的）请求内容并回显，**不落盘、不启动轮次、不取锁**。

    用途：人签 export 确认前先看到将被外发的路径清单、排除面与范围统计——
    签字的信息基础不弱于被保护的动作；授权口径（task + materials）不变。
    """
    from . import authorize as authorize_mod

    request = default_launch_request(ctx, task, implementation_cli)
    if request_path:
        supplied = records.load_json(request_path)
        if not isinstance(supplied, dict):
            raise ReviewError("WF_PATH_INVALID", {"reason": "launch request missing or not an object"})
        request = _deep_merge_launch_request(request, supplied)
    diff_paths = (((request.get("submitted_scope") or {}).get("diff") or {}).get("paths") or [])
    directory = _task_dir(ctx, task)
    recorded = authorize_mod.require(directory, "export") if directory else None
    delivery = scope_mod.delivery_set(ctx.root, task)
    # 四轮审查 a-P1：preview 展示 test_results 的实际内容身份——
    # 本轮 Check 的日志文件清单 + 逐文件摘要（与 write_materials 同源计算，不复制本体）。
    check = task.get("check") or {}
    logs_preview = []
    _logs_omitted = 0
    _started = (check.get("started_at") or "").replace(":", "").replace(".", "")
    if _started and directory:
        _log_root = os.path.join(directory, "check-logs", _started)
        if os.path.isdir(_log_root):
            _names_all = sorted(_name for _name in os.listdir(_log_root)
                                if os.path.isfile(os.path.join(_log_root, _name)))
            for _name in _names_all[:20]:
                _src = os.path.join(_log_root, _name)
                _fd, _cause, _why = records.file_digest_state(_src)
                logs_preview.append({"file": _name, "digest": _fd,
                                      "unavailable_cause": _cause})
            _logs_omitted = max(0, len(_names_all) - 20)   # 截断可见：预览不假装全量
    return {
        "request": request,
        "entry_gate": round_entry_gate(task),
        "export_authorization": {
            "recorded": recorded is not None,
            "scope_digest": (recorded or {}).get("scope_digest"),
            "note": ("已入库（同任务同材料类集合持续有效）" if recorded is not None else
                     "未入库：正式 launch 前先 authorize record choice=export"),
        },
        "scope_stats": {"diff_paths": len(diff_paths),
                        "delivery_total": len(delivery["paths"]),
                        "exclusions": list(request.get("exclusions") or [])},
        "test_results_preview": {"check_id": check.get("id"),
                                 "commands": len(check.get("commands") or []),
                                 "check_logs": logs_preview,
                                 "check_logs_omitted": _logs_omitted,
                                 "note": "确认覆盖材料类；每轮内容由批准范围与排除面约束"
                                         "（类集合不变不要求重签，也不等于逐轮内容核对）"},
    }


def launch(ctx, task, request_path=None, implementation_cli=None):
    from . import cli, lock

    # 终态对象没有审查轮次（2026-11-25 第四轮复审 F2）：必须在其它核验之前报真实原因。
    # 归档会把 PRD 移入 `.wf/tasks/archive/`，若先跑 `_is_approved_plan`，得到的是
    # 「规划批准已失效」——处置方向（回 Plan 重批）对已归档对象是错的。
    gate = round_entry_gate(task)
    if gate["terminal"]:
        raise ReviewError("WF_SEMANTIC_DECISION", {
            "reason": "task is archived; review rounds are closed",
            "status": gate["task_status"],
            "exits": ["对象已归档：审查结论看归档记录，不再发起新轮",
                      "确实需要再审：对新对象（新任务）重新发起审查"]})
    if request_path:
        # 三轮三审：`--launch-request` 只作**覆盖/补充**（机制稿 §9.1 登记口径）——
        # 三类材料/只读范围/排除面仍由入口按当前对象生成，请求里显式给的键覆盖对应项，
        # 不再要求模型为调一个局部选项重写整份材料范围。
        supplied = records.load_json(request_path)
        if not isinstance(supplied, dict):
            raise ReviewError("WF_PATH_INVALID", {"reason": "launch request missing or not an object"})
        default = default_launch_request(ctx, task, implementation_cli)
        # 四轮审查：**嵌套字段级**深合并（dict 逐键下沉；列表/标量整体替换）——
        # 只想覆盖 submitted_scope.diff.paths 时不再连带丢掉 requirement/test_results。
        # 实现与 launch_preview 共用 `_deep_merge_launch_request`（同一判定一处实现）。
        request = _deep_merge_launch_request(default, supplied)
    else:
        # 固定流转程序化（设计稿 §1.1）：材料三类、只读范围、排除面都是可机械得到的，
        # 不再要求模型手写 JSON；`--launch-request` 仍可用于覆盖/补充。
        request = default_launch_request(ctx, task, implementation_cli)
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
    # 三轮三审：显式 reviewers=1 是**声明的降级**（单 reviewer 轮）——按声明值生成，
    # 不再被 max(2, …) 吞掉；判定侧的人数门禁照旧（无接受记录仍拒）。
    slots = request.get("slots")
    if not slots:
        if "reviewers" in request:
            count = int(request.get("reviewers") or 0)
            if count < 1:
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "reviewers must be >= 1", "reviewers": count})
        else:
            count = 2
        slots = [{"slot": f"s{index + 1}"} for index in range(count)]
    if not isinstance(slots, list) or not slots:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "at least one slot required"})
    for slot in slots:
        if not isinstance(slot, dict) or not slot.get("slot"):
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "slot requires slot id"})
        declared_cli = slot.get("reviewer_cli")
        if declared_cli and declared_cli in implementation:
            raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer CLI must differ from implementation CLIs",
                                                    "slot": slot})
    from . import authorize as authorize_mod

    submitted = request.get("submitted_scope")
    if submitted is None:
        submitted = {}
    if not isinstance(submitted, dict):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "submitted_scope must be an object"})
    # 旧请求的形状（diff 字符串/布尔、requirement/test_results 字符串或列表）只作兼容读；
    # 新形状的 dict 字段由 scope_binding_problems 逐项核。这里只拒绝无法当对象用的 submitted_scope。
    raw_exclusions = request.get("exclusions")
    if raw_exclusions is not None and not isinstance(raw_exclusions, (list, str)):
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "exclusions must be an array or legacy string"})
    readable_scope = request.get("readable_scope")
    if readable_scope is not None and not isinstance(readable_scope, dict):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "readable_scope must be an object"})
    if isinstance(readable_scope, dict):
        for key in ("business_code", "spec", "paths"):
            value = readable_scope.get(key)
            if value is not None and not isinstance(value, list):
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": f"readable_scope.{key} must be an array"})
        if readable_scope.get("prd") is not None and not isinstance(readable_scope.get("prd"), str):
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "readable_scope.prd must be a string"})
    if readable_scope is None:
        # 未声明就按入口默认生成；显式空对象表示“不授权额外读取”，不能静默当成无限制。
        readable_scope = default_launch_request(ctx, task, implementation_cli=impl).get(
            "readable_scope") or {}
    readable_prd = str((readable_scope or {}).get("prd") or "").strip()
    expected_prd = task_prd_path(ctx, task)
    if readable_prd and readable_prd != expected_prd:
        raise ReviewError("WF_REVIEW_INVALID", {
            "reason": "readable_scope.prd must be this task's PRD",
            "declared": readable_prd, "expected": expected_prd,
            "exits": ["写本任务 PRD；其他任务的 PRD 不在本任务读取面内"],
        })
    # 权威来源是**入库的外发确认**（绑定任务 + 材料类）；请求里的 export_decision
    # 只是旧客户端的标签，不能覆盖入口实际核验的确认摘要。
    recorded = authorize_mod.require(_task_dir(ctx, task), "export") or {}
    export_decision = recorded.get("original_digest") or request.get("export_decision")
    exclusions = mandatory_exclusions(raw_exclusions)
    slots_material = (("diff",), ("requirement", "requirements"), ("test_results", "tests"))
    missing_material = [names[0] for names in slots_material
                        if not any(submitted.get(name) for name in names)]
    if missing_material:
        # 三类材料是审查输入的最小集，缺一即无法覆盖必要检查面（机制稿 §9.2）
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "submitted_scope lacks required material",
                           "missing": missing_material, "submitted": sorted(submitted)})
    # K6 第 3 类：材料离开本机属不可逆动作——**声明不等于确认**，且确认必须覆盖**本次范围**
    # （任务 + 材料类集合）；只核"曾经有过外发确认"会让旧授权复用到新增材料或另一个任务。
    materials = sorted({names[0] for names in slots_material
                        if any(submitted.get(name) for name in names)})
    export_problems = authorize_mod.export_scope_problems(_task_dir(ctx, task), task.get("id"),
                                                          materials)
    if export_problems:
        # 三轮二审 A6：外发缺确认与提交缺授权是两件不可逆动作——各自有码，
        # 不再让 AI 把外发拦截误读成提交权限问题（码表闭集只增）。
        raise ReviewError("WF_EXPORT_NOT_AUTHORIZED",
                          {"missing_action": "export",
                           "materials": materials,
                           "problems": export_problems,
                           "exits": [item for problem in export_problems
                                     for item in problem.get("exits") or []]})
    with lock.acquire(ctx.root, holder_hint="review-launch"):
        _record, holder = _require_held_for_task(ctx, task)
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        # Check 与锚点都按**锁内重读后的任务**取：等待锁期间 Check 可能被替换或失败，
        # 否则 request.json 会绑定到旧 Check（第十三/十四轮复审 P5、F14-3）。
        # 有效性只走 `gates.check_validity` 一处：`result == pass` 不等于锚点仍匹配
        # （内容/规格/基线变化后旧 Check 已失效，不能拿它发起新轮）。
        from . import gates as gates_mod
        from . import tasks as tasks_mod

        if not tasks_mod._is_approved_plan(task, ctx.root):
            raise ReviewError("WF_APPROVAL_MISSING", {
                "reason": "规划批准已失效；当前 PRD 不再对应批准版本",
                "exits": ["回 Plan 重新批准（或机械修订）后再 task-check",
                          "不要用旧 Check 发起审查"],
            })
        validity = gates_mod.check_validity(ctx, task)
        if not validity["valid"]:
            raise ReviewError(validity["code"], {
                "reason": "launch requires a valid Check",
                **validity["facts"],
                "blockers": validity["blockers"],
                "exits": ["在批准范围内修复后重跑 task-check，再 review-launch"],
            })
        check = task.get("check") or {}
        anchor, _parts = _current_anchor(ctx, task)
        delivery = scope_mod.delivery_set(ctx.root, task)
        diff_scope = submitted.get("diff") if isinstance(submitted, dict) else None
        if isinstance(diff_scope, dict) and not isinstance(diff_scope.get("paths"), list):
            # 新形状必须给出 paths；缺了/为 null 都无法在发起时核"要发什么"，不能留到
            # 取材料时再回落到完整交付集合（那会把范围判断藏到 reviewer 启动之后）。
            raise ReviewError("WF_REVIEW_INVALID", {
                "reason": "submitted_scope.diff.paths required (array)",
                "submitted": submitted,
                "exits": ["补 diff.paths（只能是当前交付集合的子集）后重新 review-launch",
                          "旧形状请求可去掉 --launch-request，让入口按当前对象重建请求"],
            })
        scope_problems = scope_binding_problems(
            ctx, task,
            {"submitted_scope": submitted, "exclusions": exclusions},
            delivery)
        if scope_problems:
            raise ReviewError("WF_REVIEW_INVALID", {
                "problems": scope_problems,
                "round": None,
                "exits": ["按 problems 修正 launch 请求后重试",
                          "要扩大范围先回 Plan 扩面并重新 Check，不把未声明路径塞进审查材料"],
            })
        declared_paths = (sorted({str(item) for item in diff_scope.get("paths") or []})
                          if isinstance(diff_scope, dict) and isinstance(diff_scope.get("paths"), list)
                          else None)
        if isinstance(declared_paths, list):
            selected_paths = declared_paths
        else:
            # 旧布尔/缺省形状：有效材料 = 交付集合 - 本轮 exclusions；仍标 legacy 供审计。
            selected_paths = [path for path in delivery["paths"]
                              if not any(pattern_overlap(path, excluded)
                                         for excluded in exclusions)]
        scope_fact = {
            "selected": len(selected_paths),
            "total": len(delivery["paths"]),
            "narrowed": len(selected_paths) < len(delivery["paths"]),
            "legacy": not isinstance(declared_paths, list),
        }
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
                "readable_scope": readable_scope,
                "exclusions": list(exclusions),
            }
            records.write_json(os.path.join(directory, "request.json"), request_payload)
            temp_paths.append(directory)
        entry = {
            "round": round_no,
            "attempt": attempt,
            "decision": export_decision,
            # 单值口径（C6）；`implementation_clis` 保留为兼容读字段
            "implementation_cli": impl,
            "declared_at": records.now_str(),
            "declared_by": holder,
            "implementation_clis": implementation,
            "slots": slots,
            "anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "scope": scope_fact,
            "submitted_scope": request.get("submitted_scope") or {},
            "readable_scope": readable_scope,
            "exclusions": list(exclusions),
            "export_decision": export_decision,
            "temp_paths": temp_paths,
        }
        if len(slots) < 2:
            entry["degraded"] = "single-provider"
        launches = list(reviews.get("launches") or [])
        launches.append(entry)
        reviews["launches"] = launches
        # v66：失效不再由 launch 改写 `result.verdict` 表达（那会让合法的 pass 被误杀）。
        # 失效判定统一落在 `gates.review_binding` 的 CLI 校验上；`rounds[]` 只记决策。
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
            "scope": scope_fact,
            "temp_paths": temp_paths,
            "degraded": entry.get("degraded"),
            "paste_text": commands,
            "control_assertion": assertion,
        },
    )


def _require_held_for_task(ctx, task):
    """任务写入口的写权核验（唯一实现转发，`tasks.require_held_for`）。

    review 的四个入口（launch/import/accept-unknown/decide）都作用在任务上，实例内任务
    的写权作用域是实例——转发而不是各自写一套 `require_held(task=…)`。
    """
    from . import tasks as tasks_mod

    return tasks_mod.require_held_for(ctx, task.get("id"))


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    directory = tasks_mod.task_dir(ctx.root, task.get("id"))
    if not directory:
        raise ReviewError("WF_RECORD_INVALID", {"missing_task": task.get("id")})
    return directory




MATERIAL_MISSING = "# [wf-material-missing]"
MATERIAL_EMPTY = "# 本任务交付面为空（无已归属路径）"


def _git_capture(root, args):
    """跑一次只读取片段：退出码 0/1 都算成功（`--no-index` 用 1 表示有差异）。"""
    import subprocess

    try:
        proc = subprocess.run(["git", "-c", "safe.directory=*", *args], cwd=str(root),
                              capture_output=True, text=True, check=False)
    except OSError as exc:
        return None, f"git unavailable: {exc}"
    if proc.returncode not in (0, 1):
        return None, f"git exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}"
    return proc.stdout or "", None


def _path_status(root, path):
    text, problem = _git_capture(root, ["status", "--porcelain=v1", "-z",
                                       "--untracked-files=all", "--", path])
    if problem:
        return None, problem
    for entry in text.split("\0"):
        if len(entry) > 3 and entry[3:] == path:
            return entry[:2], None
    return "  ", None


def materialize_delivery(root, paths, *, base=None):
    """按 git 状态逐路径生成材料片段（审查材料与人工复核共用的唯一实现）。

    - 未跟踪新文件：`git diff --no-index /dev/null <path>`（普通 `diff HEAD` 对未跟踪文件
      输出 0 字节——这是 dogfood 第 1–4 轮 reviewer「看不到新文件」的原题）；
    - 已跟踪（含已暂存 + 未暂存 + **任务中途已提交**）：`git diff <base> -- <path>`，
      `base` 取任务基线提交——只比 `HEAD` 会让"中途提交之后再接续"的任务材料退化成
      "no textual change"，审查者看不到本任务实际交付了什么；
    - 删除：同一个基线对比给出删除 hunk；随提交删除的路径同样出现在片段里；
    - 二进制：只给可见标记（路径 + 字节 + 摘要），不内联；
    - 取片段失败：进 `problems` 并在正文留下 `[wf-material-missing]`，绝不静默成"无差异"；
    - 基线不可用（缺失/不可达）：如实进 `status.json.diff_base_problem` 与入口 facts
      并退回 `HEAD`（不静默；载体是材料清单与 facts，不在 diff 正文插标注块）。
    """
    files, problems, chunks = [], [], []
    diff_base, base_problem = _resolve_diff_base(root, base)
    for path in list(paths or []):
        absolute = join(root, path)
        exists = os.path.exists(absolute)
        status, problem = _path_status(root, path)
        entry = {"path": path, "status": status, "generated": False}
        if problem:
            problems.append({"path": path, "reason": problem})
            chunks.append(f"{MATERIAL_MISSING} {path}: {problem}")
            files.append(entry)
            continue
        untracked = str(status or "").strip() == "??"
        if untracked and exists:
            kind = "new (untracked)"
            text, problem = _git_capture(root, ["diff", "--no-color", "--no-index", "--",
                                               "/dev/null", path])
        else:
            kind = "deleted" if not exists else "modified"
            text, problem = _git_capture(root, ["diff", "--no-color", diff_base, "--", path])
        if problem:
            problems.append({"path": path, "reason": problem})
            chunks.append(f"{MATERIAL_MISSING} {path}: {problem}")
            files.append(entry)
            continue
        body = (text or "").strip()
        note = None
        if body and any(line.startswith("Binary files") for line in body.splitlines()):
            digest, cause, _reason = records.file_digest_state(absolute) if exists else (None, None, None)
            size = os.path.getsize(absolute) if exists else None
            note = f"binary: bytes={size} digest={digest or ('unreadable:' + str(cause))}"
        elif not body:
            if untracked and exists:
                note = "new empty file (0 bytes of content)"
            elif not exists:
                note = f"deleted at or after the task baseline ({diff_base[:12]})"
            else:
                note = f"no change between the task baseline ({diff_base[:12]}) and the worktree"
        chunks.append(f"# ==== {kind} {path} ====")
        if body:
            chunks.append(body)
        if note:
            chunks.append(f"# ({note})")
        entry.update(generated=bool(body), kind=kind, bytes=len(body), note=note)
        files.append(entry)
    return {"text": "\n".join(chunks).strip(), "files": files,
            "problems": problems, "empty": not list(paths or []),
            "diff_base": diff_base, "diff_base_problem": base_problem}


def _resolve_diff_base(root, base):
    """材料差异源：任务基线优先；不可用时退回 `HEAD` 并**如实**给出原因。"""
    candidate = str(base or "").strip()
    if candidate:
        _text, problem = _git_capture(root, ["rev-parse", "--verify", f"{candidate}^{{commit}}"])
        if not problem:
            return candidate, None
        reason = f"task baseline is not a reachable commit ({candidate}): {problem}"
    else:
        reason = "task baseline commit is not recorded"
    head, problem = _git_capture(root, ["rev-parse", "--verify", "HEAD^{commit}"])
    if problem:
        return "HEAD", reason + "; HEAD also unavailable"
    return "HEAD", reason + "; falling back to HEAD"




_PATCH_HEADER = "diff --git "


def _patch_path(rest):
    """从 `diff --git a/<p> b/<p>` 里取出 b 侧路径；取不出返回 None（= 按配置类处理）。

    Git 对非 ASCII/含空格的路径写成 `"a/\\350\\256...""`（八进制转义）形态，只认裸 `a/`
    会让 `设置.yaml` 落到"代码文件"档，同一份凭据因文件名而泄漏（十六轮 b-1）。
    解析不确定时**fail-closed**：宁可用全量档让代码少可读，也不让凭据出去。
    """
    rest = rest.strip()
    for item in reversed(_split_quoted(rest)):
        body = item[1:-1] if item.startswith('"') and item.endswith('"') else item
        if body.startswith(("a/", "b/")):
            return _unquote_git(body[2:])
    parts = rest.split(" b/")
    if len(parts) == 2 and parts[0].startswith("a/"):
        return parts[1]
    return None


def _split_quoted(text):
    """切出带引号的分段（Git 的路径转义形态）。"""
    pieces, index = [], 0
    while index < len(text):
        if text[index] == '"':
            end = index + 1
            while end < len(text) and text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            pieces.append(text[index:end + 1])
            index = end + 1
        else:
            index += 1
    return pieces


def _unquote_git(path):
    """还原 Git 的八进制转义路径（`\\350\\256\\276` → 字节 → UTF-8）。"""
    body = path[1:-1] if path.startswith('"') and path.endswith('"') else path
    out = bytearray()
    index = 0
    while index < len(body):
        char = body[index]
        if char == "\\" and body[index + 1:index + 4].isdigit():
            out.append(int(body[index + 1:index + 4], 8))
            index += 4
            continue
        if char == "\\" and index + 1 < len(body):
            mapping = {"n": 10, "t": 9, "\\": 92, '"': 34}
            out.extend(bytes([mapping.get(body[index + 1], ord(body[index + 1]))]))
            index += 2
            continue
        out.extend(char.encode("utf-8"))
        index += 1
    return out.decode("utf-8", "replace")


def redact_patch(text):
    """按 `diff --git` 分片决定遮罩级别：配置类文件用全量、代码文件只遮字面量。

    整份 diff 用同一档时只能二选一：全量档会让 `password = read_from_store()` 不可审，
    材料档会让 `config.yaml` 的裸凭据外发。按文件分片是唯一同时满足两边的做法。
    """
    from . import check as check_mod

    if not isinstance(text, str) or not text:
        return text or ""
    pieces, current, current_path = [], [], None

    def flush():
        if current:
            body = "".join(current)
            pieces.append(check_mod.redact_for_path(current_path, body))

    for line in text.splitlines(keepends=True):
        if line.startswith(_PATCH_HEADER):
            flush()
            current, current_path = [line], _patch_path(line[len(_PATCH_HEADER):])
            continue
        current.append(line)
    flush()
    return "".join(pieces)


MATERIALS_PROTOCOL = "wf-materials-v1"
MANIFEST_NAME = "materials-manifest.json"
# 一次物化必然写出的顶层材料文件（`check-logs/` 是可选子目录）。旧版逐文件直写留下的
# 半包可能缺其中任意一个；缺件包不是"reviewer 读过的材料"，不能被 legacy 采纳。
MATERIAL_FILES = ("diff.patch", "prd.md", "check.json", "status.json", "tests.json")


def load_materials_manifest(materials_dir):
    """轮次材料身份（manifest）：物化即固定，供续写与判定还原 reviewer 读到的版本。

    manifest 缺失/损坏返回 None（按"身份丢失"处理：调用方按现场字节采纳，不重写
    reviewer 读过的材料）；文件存在但形状不符同样返回 None——不把损坏的 manifest 当有效身份。
    """
    path = os.path.join(materials_dir, MANIFEST_NAME)
    if not os.path.isfile(path):
        return None
    try:
        data = records.load_json(path)
    except Exception:
        return None
    if not isinstance(data, dict) or data.get("protocol") != MATERIALS_PROTOCOL:
        return None
    return data


def verify_materials_manifest(manifest, materials_dir):
    """按 manifest 逐文件核摘要；返回失配列表（空即一致）。含子目录相对路径。

    分隔符两种形态都试：manifest 可能在另一平台写出（键是 `\\`），而文件名本身也可能
    真的含反斜杠（Linux 上 `v\\1.log` 就是普通字符）。只按归一形式 join 会把这种真名
    解析成子目录，报出"missing + not in manifest"的假 drift，且采纳出口也修不好。
    已知静默面：真名键已存在时再加一个**同字节**的嵌套孪生文件不报 `not in manifest`
    （内容相同，语义无差别）；字节不同则照常报 digest mismatch。
    """
    drift = []
    recorded_forms = set()
    for rel, digest in (manifest.get("files") or {}).items():
        rel = str(rel)
        candidates = [rel]
        normalized = rel.replace("\\", "/")
        if normalized != rel:
            candidates.append(normalized)
        recorded_forms.update(candidates)
        actual, cause, reason = None, None, None
        for candidate in candidates:
            actual, cause, reason = records.file_digest_state(
                os.path.join(materials_dir, candidate))
            if actual:
                break
        if not actual:
            drift.append({"file": rel, "reason": "missing",
                          "unavailable_cause": cause, "detail": reason})
        elif actual != digest:
            drift.append({"file": rel, "reason": "digest mismatch",
                          "recorded": digest, "actual": actual})
    # 物化后**新增**的文件同样是"不是 reviewer 读到的那一版"：不列出来就只能在
    # 判定后靠人去目录里看（reviewer 当时没读过它，却会被后来的判定当成材料）。
    for base, _dirs, names in os.walk(materials_dir):
        for name in sorted(names):
            path = os.path.join(base, name)
            if os.path.abspath(path) == os.path.abspath(os.path.join(materials_dir, MANIFEST_NAME)):
                continue
            rel = os.path.relpath(path, materials_dir)
            if rel in recorded_forms or rel.replace(os.sep, "/") in recorded_forms:
                continue
            drift.append({"file": rel.replace(os.sep, "/"), "reason": "not in manifest"})
    return drift


MATERIALS_STAGING_PREFIX = "materials.staging-"


def materials_identity(manifest):
    """轮次材料的**内容身份**（唯一实现）：被审 check_id + 逐文件摘要。

    不含 `generated_at`/`facts`：时间戳每次物化都变，算进来会让"内容一字不差的重出材料"
    也判失配，出口就只剩开新一轮。`legacy_materials` 这类强弱信息由 `materials_identity_state`
    的 `state` 另报，不进身份。

    身份的两个消费者：导入登记（报告绑它读到的版本）与判定比对（结论只对它成立）。
    manifest 不存在时返回 None（弱身份，调用方如实标注）。
    """
    if not isinstance(manifest, dict):
        return None
    body = {"check_id": manifest.get("check_id"), "files": manifest.get("files") or {}}
    return "sha256:" + records.sha256_hex(records.canonical_bytes(body))


def _material_staging_dir(directory):
    """本轮材料先在 staging 组装，写全（含 manifest）后一次 rename 发布。

    逐文件直写会在中断时留下半包，而半包没有 manifest ⇒ 下次被当成 `legacy` 采纳
    （reviewer 读到缺件的"材料"）。`materials_identity_state` 不读 staging，残留由本函数
    起手清掉。
    """
    for name in sorted(os.listdir(directory)):
        if name.startswith(MATERIALS_STAGING_PREFIX):
            shutil.rmtree(os.path.join(directory, name), ignore_errors=True)
    return tempfile.mkdtemp(dir=directory, prefix=MATERIALS_STAGING_PREFIX)


def _publish_materials(staging, materials):
    """原子发布材料目录；并发下按**内容身份**归并，不把竞态报成路径冲突。

    两个 reviewer 同时取材料时都可能读到"未物化"，后到者在发布时看到非空目录。
    同轮同锚点重出的材料按定义是同一批字节（manifest 身份相同）⇒ 复用先到的，
    丢弃自己的 staging（幂等重入，不是错误）；身份不同才是真冲突。
    """
    if os.path.isdir(materials) and os.listdir(materials):
        published = records.load_json(os.path.join(materials, MANIFEST_NAME), None)
        incoming = records.load_json(os.path.join(staging, MANIFEST_NAME), None)
        if published is not None and incoming is not None \
                and materials_identity(published) == materials_identity(incoming):
            shutil.rmtree(staging, ignore_errors=True)
            return False
        raise ReviewError("WF_PATH_INVALID", {
            "reason": "materials directory already holds a different set for this round",
            "materials": materials,
            "published_identity": materials_identity(published),
            "incoming_identity": materials_identity(incoming),
            "exits": ["先 review-status 核对该轮材料身份；同轮不同内容说明对象在两次取材料之间变了",
                      "确实要按当前对象重出材料：删除 materials/ 全部内容后重跑 review-context"]})
    if os.path.isdir(materials):
        os.rmdir(materials)
    os.replace(staging, materials)
    return True


def materials_identity_state(ctx, task_id, round_no):
    """本轮材料身份状态（取材料与判定共用的唯一判据）：

    `fixed`（有 manifest 且逐文件一致，未采纳过）/ `legacy_adopted`（一致但那批字节是
    按现场采纳的，弱身份）/ `drift`（物化后被改、损坏或新增文件）/ `legacy`（有材料无
    manifest）/ `unmaterialized`（没有材料）。返回值总含 `present`（当前文件名）。
    

    判定入口此前只读 manifest 写摘要、逐文件校验只在取材料时做——材料被改动后
    `review-decide` 仍能返回 pass，等于 pass 声称的证据从未被核对过。判据收在这里，
    两个入口问同一个问题，输出各自的出口。

    `legacy`（有材料、无 manifest）不重写 reviewer 读过的字节，按现场采纳并记事实；
    要按当前内容重出材料，由调用方给出"连内容一起删"的出口。
    """
    materials = os.path.join(round_dir(ctx, task_id, round_no), "materials")
    present = []
    if os.path.isdir(materials):
        # `present` 的语义是"当前材料文件名"：子目录（如 `check-logs/`）不是材料文件。
        # 此前把目录名也算成"有材料"，会让"删内容文件+manifest 后重跑"这条出口
        # 落进 legacy 采纳，产出一个缺 diff/prd/check/tests 的半包却报成功。
        present = sorted(name for name in os.listdir(materials)
                         if name != MANIFEST_NAME and os.path.isfile(os.path.join(materials, name)))
    manifest = load_materials_manifest(materials)
    if manifest is not None:
        drift = verify_materials_manifest(manifest, materials)
        if drift:
            return {"state": "drift", "materials": materials, "manifest": manifest,
                    "drift": drift, "present": present}
        # 采纳过的这批字节从未被核对过（只是"自采纳以后再没动"）：不能因为写了
        # manifest 就升格成 fixed，否则"删 manifest 再重取"这条恢复出口会把弱身份洗掉。
        weak = bool((manifest.get("facts") or {}).get("legacy_materials"))
        return {"state": "legacy_adopted" if weak else "fixed", "materials": materials,
                "manifest": manifest, "drift": [], "present": present}
    if not present:
        return {"state": "unmaterialized", "materials": materials, "manifest": None,
                "drift": [], "present": present}
    incomplete = [name for name in MATERIAL_FILES if name not in present]
    if incomplete:
        # 旧版逐文件直写的半包（缺必需文件）不是可采纳的"现场字节"：它的内容不构成
        # 一套材料，采纳只会让 reviewer 读到缺件包。按未物化处理，由调用方重建或给出出口。
        return {"state": "unmaterialized", "materials": materials, "manifest": None,
                "drift": [], "present": present, "incomplete": incomplete}
    return {"state": "legacy", "materials": materials,
            "manifest": None, "drift": [], "present": present}


def round_is_history(entries):
    """本轮导入记录是否"没有现场身份可言"（decide 的 drift 豁免判据，唯一实现）。

    restore 记录的身份来自记录、纯旧记录压根没有身份；两者都不该被现场漂移挡住。
    只要有任一条带现场身份的 live 报告，drift 就必须拒——不能用"存在还原条目"代理。
    """
    items = [entry for entry in entries or [] if isinstance(entry, dict)]
    return bool(items) and all(
        (entry.get("materials") or {}).get("restored")
        or not (entry.get("materials") or {}).get("identity")
        for entry in items)


def round_materials_basis(entries, current_identity):
    """一轮报告的**材料基线**视图（唯一实现）：阻断与提示都读它，不各推一份。

    `restored` 条目的身份来自记录，天然可能≠当前；单条不阻断。
    同轮出现"还原 + 非还原"两份基线时，verdict 声称覆盖同一交付面却证据不同 —— 记为 mixed。
    """
    restored, live = [], []
    for entry in entries or []:
        materials = entry.get("materials") or {}
        identity = materials.get("identity")
        if not identity:
            continue
        # 当前没有材料身份（目录被清/丢失）时，**有绑定身份的报告**同样是对不上的现场：
        # 它等不来新材料，恢复只能重出材料或开新一轮。此前这里直接跳过，status 会回落成
        # "材料未齐，等 reviewer 产出"——一个永远等不到的出口。
        if current_identity is not None and identity == current_identity:
            continue
        (restored if materials.get("restored") else live).append(entry)
    return {"restored": restored, "live_mismatch": live,
            "mixed": bool(restored) and bool(live),
            "stale": bool(live)}


def round_materials_identity(ctx, task, round_no):
    """本轮材料的**当前**身份（报告校验与判定共用的唯一取值点）：无 manifest 即 None。"""
    try:
        round_no = int(round_no)
    except (TypeError, ValueError):
        return None
    if round_no < 1 or not task:
        return None
    state = materials_identity_state(ctx, task.get("id"), round_no)
    return materials_identity(state.get("manifest"))


def write_materials_manifest(materials_dir, check_id, check_anchor, material_facts):
    """物化完成后扫描材料目录写 manifest（先扫后写，manifest 自身不入 files）。"""
    files = {}
    for base, _dirs, names in os.walk(materials_dir):
        for name in sorted(names):
            path = os.path.join(base, name)
            if os.path.abspath(path) == os.path.abspath(os.path.join(materials_dir, MANIFEST_NAME)):
                continue
            rel = os.path.relpath(path, materials_dir).replace(os.sep, "/")
            digest, _cause, _reason = records.file_digest_state(path)
            if digest:
                files[rel] = digest
    payload = {"protocol": MATERIALS_PROTOCOL, "check_id": check_id,
               "check_anchor": check_anchor, "generated_at": records.now_str(),
               "files": files, "facts": material_facts}
    records.write_json(os.path.join(materials_dir, MANIFEST_NAME), payload)
    return payload


def write_materials(ctx, task, round_no, anchor, materials_dir, paths=None, delivery=None):
    """把本轮审查材料落盘（唯一实现）：diff.patch + status.json + prd/check/tests。

    交付面来自 `scope.delivery_set`；launch 声明缩小范围时由 `paths` 传入其子集，
    让"声明要发什么"与"实际物化什么"是同一份输入。未跟踪新文件必须出现在 diff.patch；
    生成失败写进 status.json 的 problems，正文留 `[wf-material-missing]`，不把失败伪装成
    "无差异"。返回可并入入口 facts 的材料事实；写完由调用方落 manifest（材料身份）。
    """
    from . import tasks as tasks_mod

    delivery = delivery or scope_mod.delivery_set(ctx.root, task)
    paths = list(delivery["paths"] if paths is None else paths)
    material = materialize_delivery(ctx.root, paths, base=task.get("baseline_head"))
    if material["empty"]:
        diff_text = MATERIAL_EMPTY
    elif material["text"]:
        diff_text = material["text"]
    else:
        diff_text = (f"# 交付面有 {len(paths)} 条路径，但未生成任何内容片段；"
                     "见同目录 status.json 的 problems")
    # 材料是**外发物**：随 `review-launch` 交给异种 reviewer CLI。脱敏协议 `secret-mask` 的
    # 范围是"所有入库内容"，这里此前直接写原始 diff/PRD——日志已脱敏不能推出材料已脱敏
    # （2026-11-23 九轮复审 b-2：虚构 api_key/password 原样进入 diff.patch 与 prd.md）。
    from . import check as check_mod

    diff_text = redact_patch(diff_text)
    records.atomic_write(os.path.join(materials_dir, "diff.patch"), diff_text + chr(10))
    selected = set(paths)
    prd_text = tasks_mod.read_prd(ctx.root, task) if hasattr(tasks_mod, "read_prd") else ""
    records.atomic_write(os.path.join(materials_dir, "prd.md"),
                         # PRD 是任务文档（散文 + 片段）：按全量规则处置，漏遮面更大
                         check_mod.redact_text(prd_text) or "# PRD 不可读" + chr(10))
    # 审查材料只放 Check 的公共身份/结论/锚点；`internal_review` 等实施侧自评不进材料。
    check = task.get("check") or {}
    check_public = {key: check.get(key) for key in ("id", "result", "anchor") if key in check}
    records.write_json(os.path.join(materials_dir, "check.json"),
                       {"check": check_public, "anchor": {"check_anchor": anchor}})
    commands = (task.get("check") or {}).get("commands") or []
    # 注意：**不要**在这里先写一份 `{"commands": commands}`——那是原文，材料是外发物，
    # 两次写之间审查会话能读到原文、中途失败也留下它。tests.json 只在末尾写一次（脱敏后）。
    # 十六轮 a-3：当前 Check 的完整脱敏验证日志物化进材料包——
    # 日志本体在任务目录 check-logs/ 下（reviewer 必排面），此前 reviewer 只能看到
    # commands 摘要、无法复核具体输出。按当前 Check 引用把已脱敏日志复制到
    # materials/check-logs/，tests.json 附带清单与摘要；不开放任务目录、不新增审查步骤。
    logs_manifest = []
    # a 组 a-3：Check 记录的真实字段是 started_at（与 check.py 日志目录命名同源）——
    # 此前读 check.started 恒为空，日志复制分支在真实数据上从不执行。
    _check_started = ((task.get("check") or {}).get("started_at") or "").replace(":", "").replace(".", "")
    # a-3（三轮外部审查 a4）：日志必须按命令记录的证据身份核对——
    # commands[].evidence_ref + log_digest 是执行时已保存的身份；复制时逐文件比对，
    # 字节不符或读不到的日志**不进材料包**（身份核对先于物化），改记入
    # status.json.problems（不静默省略，也不把新字节冒充该 Check 的原始证据）。
    _expected_logs = {os.path.basename(str(cmd.get("evidence_ref"))): cmd.get("log_digest")
                      for cmd in commands
                      if isinstance(cmd, dict) and cmd.get("evidence_ref") and cmd.get("log_digest")}
    _log_problems = []
    # 上一次物化的日志副本一律先清空：源目录这次不存在/不可达时也要清——否则旧字节
    # 留在包里而新清单不再列它，reviewer 会读到过期证据（十五轮 a-3）。
    _materials_logs = os.path.join(materials_dir, "check-logs")
    if os.path.isdir(_materials_logs):
        for _stale in sorted(os.listdir(_materials_logs)):
            _stale_path = os.path.join(_materials_logs, _stale)
            if os.path.isfile(_stale_path):
                os.remove(_stale_path)
    if _check_started:
        _log_root = os.path.join(_task_dir(ctx, task), "check-logs", _check_started)
        if os.path.isdir(_log_root):
            _dest = _materials_logs
            os.makedirs(_dest, exist_ok=True)
            for _name in sorted(os.listdir(_log_root)):
                _src = os.path.join(_log_root, _name)
                if not os.path.isfile(_src):
                    continue
                # **先核身份、再决定要不要进材料包**（2026-11-23 十轮复审 b-2）：材料是外发物，
                # 此前先 copyfile 再核摘要，被改写的日志和从未被任何命令引用的文件都进了包，
                # verified=false / null 只是事后标注——标注不能约束材料范围。
                _fd, _cause, _why = records.file_digest_state(_src)
                _recorded = _expected_logs.get(_name)
                if _recorded is None:
                    _log_problems.append({"reason": "check log not referenced by any command "
                                                    "(not materialized)",
                                          "file": _name})
                    continue
                if not _fd or _fd != _recorded:
                    _log_problems.append({"reason": "check log digest mismatch "
                                                    "(not materialized)",
                                          "file": _name, "recorded_digest": _recorded,
                                          "digest": _fd,
                                          "unavailable_cause": _cause if not _fd else None})
                    continue
                import shutil as _shutil

                _shutil.copyfile(_src, os.path.join(_dest, _name))
                logs_manifest.append({"file": f"check-logs/{_name}",
                                      "digest": _fd,
                                      "recorded_digest": _recorded,
                                      "verified": True})
    for _name in sorted(set(_expected_logs) - {os.path.basename(item["file"])
                                                for item in logs_manifest}):
        _log_problems.append({"reason": "check log referenced by a command was not materialized",
                              "file": _name})
    if _log_problems:
        # 日志短缺与脱敏范围是 reviewer 同时需要的事实：先汇总再**一次**写出 status.json，
        # 不做第二遍覆盖写（此前覆盖写丢掉 redacted/redaction，十四轮 b-3）。
        material["problems"] = list(material["problems"]) + _log_problems
    records.write_json(os.path.join(materials_dir, "status.json"),
                       {"paths": paths, "files": material["files"],
                        "problems": material["problems"], "empty": material["empty"],
                        # 材料是脱敏副本：reviewer 看到的是 `***`，不宣称与工作树逐字相同。
                        # `redaction` 写明**按文件类型的策略**，材料里不会再有"标了 redacted
                        # 却没说哪部分是原文"的盲区（十四轮 a-1）。
                        "redacted": True,
                        "redaction": {"diff": "per-file（配置类全量 / 代码类仅字面量）",
                                      "prd": "full", "commands": "field-aware"},
                        "diff_base": material.get("diff_base"),
                        "diff_base_problem": material.get("diff_base_problem"),
                        # 索引只列本轮实际物化的路径；整份交付集合是判定侧事实，不该从材料泄漏。
                        "buckets": {key: [path for path in delivery["buckets"][key]
                                          if path in selected]
                                    for key in ("e", "f", "covered_f", "uncovered_f")}})
    # 命令记录里含人工验证的原始 decision（理由/引文），材料是外发物 ⇒ 先脱敏再落盘，
    # **只写一次**：此前的"先写原文、最后覆写"一旦脱敏破坏结构就把原文留在材料目录里。
    tests_payload = {"commands": check_mod.redact_commands(commands)}
    if logs_manifest:
        tests_payload["logs"] = logs_manifest
    records.write_json(os.path.join(materials_dir, "tests.json"), tests_payload)
    return {"material_paths": len(paths),
            "material_problems": material["problems"][:5],
            "material_problem_count": len(material["problems"]),
            "diff_base": material.get("diff_base"),
            "diff_base_problem": material.get("diff_base_problem")}


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
    plan = record.get("plan") or {}
    if "approval" in plan:
        # 发起后 PRD/批准或 Check 失效（含 task-replan 把 approval 置空）：不能在
        # reviewer 已开始后才由判定端拦下。
        from . import gates as gates_mod
        if not tasks_mod._is_approved_plan(record, ctx.root):
            raise ReviewError("WF_APPROVAL_MISSING", {
                "reason": "规划批准已失效；当前 PRD 不再对应批准版本",
                "exits": ["回 Plan 重新批准（或机械修订）后重跑 Check、重新发起审查"],
            })
        validity = gates_mod.check_validity(ctx, record)
        if not validity.get("valid"):
            raise ReviewError(validity.get("code") or "WF_CHECK_STALE", {
                "reason": "审查材料必须基于仍有效的 Check",
                **(validity.get("facts") or {}),
                "blockers": validity.get("blockers"),
                "exits": ["重新 Check 后重新发起审查", "不要用旧 Check 取材料"],
            })
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
    launch = next((entry for entry in launches if int(entry.get("round") or 0) == round_no), {})
    if not isinstance(launch, dict):
        launch = {}
    anchor, _parts = _current_anchor(ctx, record)
    launch_anchor = (launch.get("anchor") or {}).get("check_anchor")
    identity = anchor_identity_problems(launch.get("anchor"), record)
    if identity or (launch_anchor and launch_anchor != anchor):
        # 发起后内容/规格/基线又变了，或 Check 重跑换了 id：旧轮只能作废，
        # 重跑 Check 后重新发起。`check_anchor` 相同不代表同一份 Check。
        saved = ((record.get("check") or {}).get("anchor") or {})
        facts = {"reason": "launch Check identity or anchor no longer matches the current Check",
                 "round": round_no,
                 "launch_anchor": launch_anchor,
                 "current_anchor": anchor,
                 "identity": identity,
                 "exits": ["重跑 task-check 生成有效 Check 后重新 review-launch"]}
        # 本轮已写的草稿在这里点名：换了 Check 后旧目录不可续写，但草稿本身还在，
        # 至少给出可读物路径与去向，不让 reviewer 无从下手。
        drafts = []
        for slot, _cli in declared_slots(launch):
            candidate = agent_report_path(ctx, task_id, round_no, slot)
            if os.path.isfile(candidate):
                drafts.append({"slot": slot, "path": candidate,
                               "status": read_agent_status(candidate)})
        if drafts:
            facts["stale_round_drafts"] = drafts
            facts["exits"].append("旧 Check 下已写的草稿保留在此：新轮沿用同一结论时，"
                                  "按新锚点重写报告；不要覆盖已 done 的报告")
        drift = anchor_drift(saved.get("parts"), _parts)
        if drift is None:
            facts["diff_unavailable"] = "旧 check 记录没有 anchor.parts；不按当前内容反推"
        else:
            facts["drift_diffs"] = drift
        raise ReviewError("WF_CHECK_STALE", facts)
    launch_readable = (launch or {}).get("readable_scope")
    if not isinstance(launch_readable, dict):
        launch_readable = {}
    launch_prd = str(launch_readable.get("prd") or "").strip()
    if launch_prd and launch_prd != task_prd_path(ctx, record):
        raise ReviewError("WF_REVIEW_INVALID", {
            "reason": "readable_scope.prd must be this task's PRD",
            "declared": launch_prd, "expected": task_prd_path(ctx, record),
            "round": round_no,
            "exits": ["按本任务 PRD 重新 review-launch；不把其他任务 PRD 当读取面"],
        })
    delivery = scope_mod.delivery_set(ctx.root, record)
    submitted = (launch or {}).get("submitted_scope")
    if not isinstance(submitted, dict):
        submitted = {}
    diff_scope = submitted.get("diff")
    legacy_scope = not isinstance(diff_scope, dict)
    if isinstance(diff_scope, dict):
        problems = scope_binding_problems(ctx, record, launch, delivery)
        if problems:
            raise ReviewError("WF_REVIEW_INVALID", {
                "problems": problems,
                "round": round_no,
                "exits": ["按 problems 修正 launch 请求后重新 review-launch",
                          "要扩大范围先回 Plan 扩面并重新 Check，不在此处补发未声明材料"],
            })
    declared_paths = diff_scope.get("paths") if isinstance(diff_scope, dict) else None
    paths = sorted({str(item) for item in declared_paths}) if isinstance(declared_paths, list) else None
    if paths is None:
        # 旧 launch 没有 submitted_scope 或仍是布尔形状：按交付集合物化，但先扣掉本轮排除面，
        # 并在 facts 里如实标注。兼容不等于绕过外发边界。
        legacy_scope = True
        exclusions = mandatory_exclusions((launch or {}).get("exclusions"))
        paths = [path for path in delivery["paths"]
                 if not any(pattern_overlap(path, excluded) for excluded in exclusions)]
    narrowed = len(paths) < len(delivery["paths"])
    directory = round_dir(ctx, task_id, round_no)
    materials = os.path.join(directory, "materials")
    os.makedirs(materials, exist_ok=True)
    # 轮次材料一经物化即固定（manifest 落盘）：同轮重入校验复用、不重写——reviewer
    # 当时读到的材料版本可由 manifest 还原。同锚点重跑 Check（新 check_id）后旧轮
    # 续写仍读首轮材料；当前 Check 与物化 check_id 不同时在 facts 标注，判定按本轮
    # 固定材料核对（同内容免重审与证据身份不冲突：锚点相同 ⇒ 被审的是同一份内容）。
    current_check_id = (record.get("check") or {}).get("id")
    # 五种状态各自的处置（判据在 materials_identity_state，与 review-decide 共用）：
    # fixed 复用；drift 阻断；legacy / legacy_adopted 按现场字节采纳（不重写 reviewer
    # 读过的东西，后者沿用原 check_id 与采纳时间）；unmaterialized 才是首次物化。
    material_state = materials_identity_state(ctx, task_id, round_no)
    if material_state["state"] == "drift":
        raise ReviewError("WF_REVIEW_INVALID", {
            "reason": "本轮材料与 manifest 不符（材料在物化后被改动或损坏）",
            "manifest_check_id": (material_state["manifest"] or {}).get("check_id"),
            "drift": material_state["drift"],
            "exits": ["材料改动可接受且有备份：把备份/暂存副本的原字节放回材料目录后重跑 review-context"
                      "（manifest 只记摘要、不放字节；原字节 ⇒ 原身份，已导入报告继续有效）",
                      "要按当前内容重出材料：删 materials/ 下的内容文件**和** materials-manifest.json"
                      "后重跑 review-context（只删内容会停在 drift）",
                      "采纳现场字节的弱身份：只删 manifest、留着改动后的内容重跑（facts 记 "
                      "legacy_materials，但已导入报告按新身份核对）"]})
    if material_state["state"] == "fixed":
        # 复用即不重写 manifest：其中记录的 check_id 是**被审 Check**的身份，不能被
        # 后来的同锚点 Check 覆盖（重写会让判定引用的身份随重跑漂移）。
        manifest = material_state["manifest"]
        material_facts = dict((manifest or {}).get("facts") or {}, materials_fixed=True)
    elif material_state["state"] in ("legacy", "legacy_adopted"):
        # 采纳：不重写 reviewer 读过的字节。已有 manifest（此前已采纳过）时沿用它的
        # check_id 与首次采纳时间，只用当前字节重算摘要——否则每重入一次就把
        # "这批材料由哪个 Check 物化"改写一次，且弱身份被洗成 fixed。
        prior = (material_state["manifest"] or {}).get("facts") or {}
        material_facts = {"legacy_materials": True,
                          "adopted_files": (material_state["present"]  # 顶层名，非路径
                                            or sorted(prior.get("adopted_files") or [])),
                          "adopted_at": prior.get("adopted_at") or records.now_str(),
                          "note": "材料无核对身份（按现场字节采纳，未证明未被改动）"}
        prior_check_id = (material_state["manifest"] or {}).get("check_id")
        if not prior_check_id:
            # 采纳旧包时优先沿用导入记录里的被审 check_id：材料字节没变、只是 manifest
            # 丢了时，同锚点重跑 Check（新 id）不应把旧报告的身份改掉。
            _imported_round = [entry for entry in (record.get("reviews") or {}).get("imported") or []
                               if isinstance(entry, dict)
                               and int(entry.get("round") or 0) == int(round_no)]
            _check_ids = {(entry.get("anchor") or {}).get("check_id") for entry in _imported_round
                          if (entry.get("anchor") or {}).get("check_id")}
            if len(_check_ids) == 1:
                prior_check_id = next(iter(_check_ids))
        manifest = write_materials_manifest(
            materials, prior_check_id or current_check_id, anchor, material_facts)
    else:
        # 未物化（含"删内容文件+manifest"后的恢复形态）：目录里可能只剩 `check-logs/`
        # 这类子目录，或一份缺必需文件的旧半包。子目录是残留、重建；缺件旧包不静默采纳、
        # 也不静默删除证据——给"删全部内容重建"与"放回完整备份"两个出口。
        if os.path.isdir(materials):
            if material_state.get("present"):
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "本轮材料包不完整（缺必需文件），不按旧包采纳",
                    "missing": material_state.get("incomplete") or [],
                    "present": material_state["present"],
                    "exits": ["删除 materials/ 下全部内容后重跑 review-context（按当前 Check 重建）",
                              "有完整备份时把原字节放回材料目录（原报告继续有效）"]})
            shutil.rmtree(materials, ignore_errors=True)
        staging = _material_staging_dir(directory)
        try:
            material_facts = write_materials(ctx, record, round_no, anchor, staging,
                                             paths=paths, delivery=delivery)
            manifest = write_materials_manifest(staging, current_check_id, anchor, material_facts)
            _publish_materials(staging, materials)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    # 首次物化后重算状态：`material_state` 是写入前的判定输入（决定走哪个分支），
    # 直接拿它回显会让本调用自己产出的材料在响应里仍显示 unmaterialized/fixed=false
    # （2026-11-25 复杂链路 dogfood 实测：reviewer 拿到"材料未物化"的错误事实）。
    material_state = materials_identity_state(ctx, task_id, round_no)
    # 授权边界事实与首次分支同源（launch 记录是唯一登记处）：续写（上下文丢失后重入）
    # 恰是最需要重读"本轮授权我读什么、排除什么"的场景。
    launch_facts = {"submitted_scope": (launch or {}).get("submitted_scope") or {},
                    "readable_scope": (launch or {}).get("readable_scope") or {},
                    "exclusions": list((launch or {}).get("exclusions") or []),
                    "anchor": (launch or {}).get("anchor") or {"check_anchor": anchor}}
    request_paths = {}
    request_path = None
    for _slot, _cli in declared_slots(launch):
        _path = os.path.join(slot_dir(ctx, task_id, round_no, _slot), "request.json")
        request_paths[_slot] = _path
        if _cli and _cli == agent:
            request_path = _path
    if request_path is None:
        # 未声明 reviewer_cli 绑定时槽位由位置分配推导；每槽位请求内容相同，任取一份
        # 都代表本轮授权事实（优先排序第一份，槽位缺失时按 agent 名回退）。
        request_path = (sorted(request_paths.values())[0]
                        if request_paths
                        else os.path.join(slot_dir(ctx, task_id, round_no, agent), "request.json"))
    materials_facts = {"diff": os.path.join(materials, "diff.patch"),
                       "prd": os.path.join(materials, "prd.md"),
                       "check": os.path.join(materials, "check.json"),
                       "tests": os.path.join(materials, "tests.json"),
                       "status": os.path.join(materials, "status.json"),
                       # P2-8（2026-11-21 六轮）：授权请求原件——reviewer 需要时可核对
                       # "本轮授权我读什么、排除什么"；路径指向发起写入的槽位目录。
                       "request": request_path,
                       "request_slots": request_paths}
    # 材料身份回显：state 与 fixed 都取真实判据（此前恒报 fixed=true，legacy/采纳态也说"已固定"，
    # reviewer 与主会话都看不出身份强弱）。identity 是报告要抄进 materials 块的值。
    materials_check = {"state": material_state["state"],
                       "fixed": material_state["state"] == "fixed",
                       "identity": materials_identity(manifest),
                       "check_id": manifest.get("check_id"),
                       "current_check_id": current_check_id}
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
    if status == "in-progress":
        # 上下文丢失后同一任务/轮次/身份重入：已有草稿不清、不覆盖，返回同一材料与路径。
        from . import codes as codes_mod
        return codes_mod.result(
            "WF_OK", object={"id": task_id, "name": record.get("title")},
            position_=codes_mod.position(scope="task", phase=record.get("phase"),
                                         task_id=task_id),
            next_="已有 in-progress 草稿：从 report_path 续写，保留已写内容；写完改 done 再导入",
            facts={"round": round_no, "agent": agent, "report_path": target,
                   "resumed": True,
                   "materials": materials_facts,
                   **material_facts, "legacy_scope": legacy_scope, "narrowed": narrowed,
                   "delivery_path_count": len(delivery["paths"]),
                   "submitted_paths": (sorted(str(item) for item in declared_paths)
                                       if isinstance(declared_paths, list) else None),
                   "skeleton_fields": list(REPORT_FIELDS),
                   "materials_check": materials_check,
                   **launch_facts})
    if status == "done":
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "this agent already has a report for the round",
                           "agent": agent, "round": round_no, "status": status, "path": target,
                           # done 报告改不了骨架，但缺身份时要知道往哪补：给出当前身份，别只说"去导入"
                           "materials_check": materials_check,
                           "exits": ["报告已完成，下一步 review-import",
                                     "报告缺 materials 块（此前版本写的）时，把 materials_check.identity "
                                     "按 `{'materials': {'identity': …}}` 补进协议块再导入",
                                     "换一个审查 agent（须与实施 CLI 及其它审查 CLI 不同）"]})
    records.atomic_write(target, report_skeleton(task_id, round_no, record.get("check") or {}, anchor,
                                                 launch=launch,
                                                 materials_identity=materials_check["identity"]))
    from . import codes

    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": record.get("title")},
        position_=codes.position(scope="task", phase=record.get("phase"), task_id=task_id),
        next_="按 materials 写报告到 report_path；导入前先跑 `wf lint report --file <report_path>`，"
              "保存时把头部 status 改为 done",
        facts={"round": round_no, "agent": agent, "report_path": target,
               "materials": materials_facts,
               **material_facts,
               "legacy_scope": legacy_scope,
               "narrowed": narrowed,
               "delivery_path_count": len(delivery["paths"]),
               "submitted_paths": (sorted(str(item) for item in declared_paths)
                                   if isinstance(declared_paths, list) else None),
               "skeleton_fields": list(REPORT_FIELDS),
               "materials_check": materials_check,
               **launch_facts},
    )


def evidence_identity_problem(previous, incoming_digest, file_digest, *, restore=False):
    """A4：导入端的证据身份判定（纯函数）。返回 None（放行）或问题 facts（拒绝）。

    判据只有一条主线：**已登记摘要就是这份证据的身份**。

    | 情形 | 已登记摘要 | 磁盘字节 | 结果 |
    |---|---|---|---|
    | 普通首次导入 | 无记录 | 任意 | 写入并登记（传 `--restore` 直接拒） |
    | 幂等重入 | = 来件 | = 来件 | 不重复写；字节被删则按原字节重建 |
    | 顶替（删档换报告） | ≠ 来件 | 任意 | **拒绝**，任何参数都不放行 |
    | 遗留补摘要 | 缺 | = 来件 | 放行，并把摘要补登记上 |
    | restore（遗留重导） | 缺 | ≠ 来件 | 显式放行；**保留原身份与原 anchor**（A5） |

    `--restore` 只对**已存在的记录**有意义：首次导入就传 ⇒ 拒绝。
    """
    if previous:
        registered = previous.get("report_digest")
        if registered:
            if registered != incoming_digest:
                return {"reason": "报告摘要在导入后不可替换",
                        "recorded": registered, "incoming": incoming_digest,
                        "exits": ["换一份报告必须换一轮：先 review-launch 重新发起审查",
                                  "只想恢复被删掉的原文件时，重新导入**同一份**报告即可"]}
            return None
        if file_digest == incoming_digest:
            return None        # 磁盘上就是这份字节：补登记摘要，不算替换
        if restore:
            return None
        return {"reason": "该记录缺登记摘要，且磁盘字节与来件不同：重导需显式 --restore",
                "file_digest": file_digest, "incoming": incoming_digest,
                "exits": ["确认来件就是当初导入的那份报告后，加 --restore 重跑",
                          "无法确认时换一轮：review-launch 重新发起审查"]}
    if restore:
        return {"reason": "首次导入不得使用 --restore（没有原身份可恢复）",
                "exits": ["去掉 --restore 直接导入"]}
    return None


def import_report(ctx, task, round_no=None, slot=None, report_path=None, _from_discovery=False,
                  as_value=None, agent=None, restore=False):
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
    # A1：`slot` 是声明槽位（记录身份键），`agent` 是 reviewer 名（只作展示与文件名）。
    # 这里只确定**身份 token**；槽位在锁内由 `slot_assignment` 的唯一分配点给出。
    identity = normalize_agent(agent) if agent else normalize_agent(slot)
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
                found = agent_from_path(candidate)
                if not found or (wanted and found != wanted):
                    continue
                if read_agent_status(candidate) != "done":
                    continue
                targets.append((found, candidate))
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
            undecided = undecided_rounds(record)
            raise ReviewError("WF_PATH_INVALID",
                              {"reason": "no finished report in this round", "round": round_no,
                               "agent": wanted, "directory": directory,
                               # 缺省取最大发起轮：恢复较早一轮时错轮是常见形态，把待处理轮次
                               # 直接列出来，调用方不必再去猜/翻记录。
                               "undecided_rounds": undecided,
                               "exits": ["先由 reviewer 会话运行 review-context 并写完报告（status=done）",
                                         "本轮不是要处理的那一轮时用 `--round <n>` 显式指定"
                                         + (f"（待处理轮次：{undecided}）" if undecided else "")]})
        # 发现式导入（2026-11-21 调整）：逐份导入，坏报告不中断其余槽位——
        # 导入是证据入库，能入的先入，失败槽位在 facts.import_errors 单列（含原因与出口）。
        imported, import_errors, results_by_agent = [], [], {}
        last = None
        for found, candidate in targets:
            try:
                result = import_report(ctx, task, round_no, None, candidate,
                                       _from_discovery=True, agent=found)
                imported.append(found)
                results_by_agent[found] = result
                last = result
            except ReviewError as exc:
                import_errors.append({"agent": found,
                                      "code": getattr(exc, "code", "WF_REVIEW_INVALID"),
                                      "reason": str((exc.facts or {}).get("reason", exc)),
                                      "exits": list((exc.facts or {}).get("exits") or [])})
        if not imported and import_errors:
            # 一份都没能入库：按原语义抛第一份的错误（不伪造部分成功）
            raise ReviewError(import_errors[0]["code"],
                              {"reason": import_errors[0]["reason"],
                               "agent": import_errors[0]["agent"],
                               "exits": import_errors[0]["exits"]})
        last = last or {}
        facts = dict(last.get("facts") or {})
        facts["imported_agents"] = imported
        # P2-9（2026-11-21 六轮）：部分导入时保留每个成功槽位的关键 facts——
        # 主会话判断"两份都入库且锚点一致"需要对称信息，不能只留最后一份。
        if len(imported) > 1 or (import_errors and imported):
            facts["imports"] = []
            for _idx, (found, _cand) in enumerate(targets):
                if found in imported:
                    slot_facts = (results_by_agent.get(found) or {}).get("facts") or {}
                    facts["imports"].append({"agent": found,
                                             "report_digest": slot_facts.get("report_digest"),
                                             "findings": slot_facts.get("findings_count",
                                                                        len(slot_facts.get("findings") or [])),
                                             "anchor_ok": slot_facts.get("anchor_ok")})
        if import_errors:
            facts["import_errors"] = import_errors
            facts["note"] = "部分报告未入库：按 import_errors 逐槽位处理，已入库的不受影响"
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
    # 输入面（字段、状态头、读取/排除范围、轴与 verdict 一致性）与 lint、判定同一实现；
    # **先**做形状检查再比身份字段：否则 `round: "bad-round"` 会在共享校验前抛裸 ValueError，
    # 报告格式问题又漏回给调用方自己猜。在取锁前完成，保证"报告不合格"不会被锁内更早的锚点问题遮住。
    try:
        current_record = records.load_json(os.path.join(_task_dir(ctx, task), "task.json")) or task
    except Exception:  # noqa: BLE001 — 记录读不到时仍按调用方给的 task 做输入面检查
        current_record = task
    input_problems = flatten_checks(report_input_problems(
        payload, task=current_record, text=text,
        materials_identity=round_materials_identity(ctx, current_record, round_no),
        materials_required=not restore, materials_restored=restore)["checks"])
    # restore 只放宽"身份相等"（校验器已按 `materials_restored` 处理），格式问题照报。
    if input_problems:
        raise ReviewError("WF_REVIEW_INVALID",
                          {"reason": "report input does not satisfy the protocol",
                           "problems": input_problems,
                           "exits": ["按问题清单修正报告后重新导入（lint report 与导入共用同一校验）",
                                     f"状态行必须在报告开头前 {STATUS_HEAD_CHARS} 字符内且为 status=done"]})
    if str(payload.get("task-id")) != str(task.get("id")):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "task-id mismatch", "report": payload.get("task-id")})
    try:
        declared_round = int(payload.get("round"))
    except (TypeError, ValueError):
        declared_round = None
    if declared_round != int(round_no):
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "round mismatch", "report": payload.get("round")})
    # 材料在物化后被改动（含量增加）时，报告与链上判定都不再对得上；导入端先拒一次，
    # 不把同一件事推到判定才炸（lint/import/decide 同源的既有纪律）。
    material_state = materials_identity_state(ctx, task.get("id"), round_no)
    if material_state["state"] == "drift" and not restore:
        # restore 还原的是历史证据，历史证据不必匹配当前现场；drift 留给判定侧如实报。
        raise ReviewError("WF_REVIEW_INVALID", {
            "reason": "本轮材料在物化后被改动，报告无法对上材料身份",
            "round": int(round_no), "drift": material_state["drift"],
            "exits": ["有备份时把原字节放回材料目录再重跑 review-context（原字节 ⇒ 原身份）",
                      "材料确实变了：删 materials/ 下内容文件**和** materials-manifest.json 后重跑 "
                      "review-context，再按新材料重写报告并开新一轮"]})
    # 身份优先看文件名；正文写了就要一致（2026-11-07：正文不再要求该字段）
    if payload.get("reviewer-id") and normalize_agent(payload.get("reviewer-id")) != identity:
        raise ReviewError("WF_REVIEW_INVALID", {"reason": "reviewer-id mismatch", "report": payload.get("reviewer-id")})
    from . import lock

    with lock.acquire(ctx.root, holder_hint="review-import"):
        _record, holder = _require_held_for_task(ctx, task)
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
        # ⑥ 消费写点①：导入命令观察到「放行记录对应的报告当前可核实」→ 该放行失效
        consume_recovered(ctx, task)
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
        record_slot = slot
        if discovered:
            # A1 写路径：槽位只从唯一分配点取（记录原值 → reviewer_cli 声明 → 位置顺序），
            # 不再把 reviewer 名当槽位写进记录。
            round_imported = [item for item in reviews.get("imported") or []
                              if int(item.get("round") or 0) == int(round_no)]
            assignment = slot_assignment(launch, round_imported,
                                         staged_agents(ctx, task.get("id"), round_no))
            record_slot = next((name for name, item in assignment.items()
                                if item.get("agent") == identity), None)
            if not record_slot:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "no declared slot left for this reviewer",
                    "agent": identity, "round": int(round_no),
                    "declared": [name for name, _cli in declared_slots(launch)],
                    "imported": [item.get("slot") for item in round_imported],
                    "exits": ["按已声明的槽位数减少本轮报告，或用 review-launch 重新发起足够槽位的轮次"]})
        # 身份由文件名承载（仅发现模式）：正文若仍写 source-cli / reviewer-id 必须与文件名一致
        for field in (("source-cli", "reviewer-id") if discovered else ()):
            if payload.get(field) and normalize_agent(payload.get(field)) != identity:
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": f"report {field} differs from its file name",
                                   "field": field, "report": payload.get(field),
                                   "file_agent": identity, "slot": record_slot})
        # 引用必须属于当前批准集合；本任务内改过的规则不得当判据（机制稿 §9.2、K3c）
        index, changed = assertion_index(ctx, task)
        deprecated_refs = deprecated_clause_refs(ctx, task)
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
                                       "finding": finding.get("id"), "slot": record_slot,
                                       "known": sorted(index)})
                continue
            problem = assertion_ref_problem(ref, index, changed, fix_kind, task=task,
                                            finding_location=finding.get("location"),
                                            deprecated=deprecated_refs)
            if problem:
                problem["finding"] = finding.get("id")
                problem["slot"] = record_slot
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
        anchor_problems = anchor_identity_problems(report_anchor, task)
        if anchor_problems:
            raise ReviewError("WF_REVIEW_INVALID",
                              {"problems": anchor_problems, "slot": record_slot,
                               "exits": ["用当前 Check 重新 review-launch 并发起报告",
                                         "旧报告不得绑定到新 Check，即使内容指纹相同"]})
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
        target = os.path.join(target_dir, f"review-{identity}.md")
        legacy = os.path.join(path, "review", f"review-round-{int(round_no)}", f"{identity}.md")
        if not os.path.exists(target) and os.path.exists(legacy):
            target = legacy
        existing_digest, existing_cause, existing_reason = records.file_digest_state(target)
        if existing_cause == "unreadable":
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "报告路径无法读取", "path": target,
                               "error": existing_reason, "slot": record_slot})
        incoming_digest = "sha256:" + records.sha256_hex(text.encode("utf-8"))
        # A4：登记摘要优先于文件字节——删掉文件再导另一份，不能顶掉已登记的证据
        previous = next((entry for entry in reviews.get("imported") or []
                         if isinstance(entry, dict)
                         and int(entry.get("round") or 0) == int(round_no)
                         and entry.get("slot") == record_slot), None)
        identity_problem = evidence_identity_problem(previous, incoming_digest, existing_digest,
                                                     restore=restore)
        if identity_problem:
            raise ReviewError("WF_REVIEW_INVALID",
                              dict(identity_problem, slot=record_slot, round=int(round_no),
                                   report_path=os.path.relpath(target, str(ctx.root)).replace(os.sep, "/")))
        if existing_digest and existing_digest != incoming_digest:
            # 同路径不同摘要即冲突：不覆盖、不留旧结论（机制稿 §9.2）
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "report digest differs from the imported one",
                               "slot": record_slot, "existing": existing_digest,
                               "incoming": incoming_digest,
                               "exits": ["同一轮不覆盖已导入报告：开新一轮 `review-launch` 重新发起审查",
                                         "只是文件被误动过字节：恢复为导入时的原内容（existing 摘要）后重试"]},
                              )
        if existing_digest:
            # 同摘要重入：幂等，不重复写
            pass
        else:
            records.atomic_write(target, text)
        digest, digest_cause, digest_reason = records.file_digest_state(target)
        if digest_cause:
            # 写后读不回来：宁可拒绝，也不留一条 `report_digest: null` 的"遗留记录"
            raise ReviewError("WF_REVIEW_INVALID",
                              {"reason": "报告写入后无法读取", "path": target,
                               "error": digest_reason, "slot": record_slot})
        imported = [entry for entry in reviews.get("imported") or []
                    if not (int(entry.get("round") or 0) == int(round_no) and entry.get("slot") == record_slot)]
        entry_anchor = {"check_id": (task.get("check") or {}).get("id"), "check_anchor": anchor}
        if restore and previous is not None:
            # A5：restore 只还原"这条记录原本的身份"，不把 anchor 换成当前 check——
            # 否则等于替人补一句"当时就是按这个标准审的"，而机制无法为那句话作证。
            entry_anchor = previous.get("anchor")
        entry_record = {"round": int(round_no), "slot": record_slot,
                        "report_path": os.path.relpath(target, str(ctx.root)).replace(os.sep, "/"),
                        "report_digest": digest, "anchor": entry_anchor}
        # 报告绑定它读到的那批材料（A1 裁定）：身份在导入时登记，判定按它核对。
        # restore 保留原身份——不拿当前材料替旧报告作证。没有声明过 `materials` 的旧报告
        # 照当前身份记但不宣称绑定（`unbound`），不阻断在途轮。
        if restore and previous is not None and previous.get("materials"):
            entry_record["materials"] = dict(previous.get("materials"), restored=True)
        elif restore:
            identity_now = materials_identity(material_state["manifest"])
            entry_record["materials"] = dict(
                {"identity": identity_now} if identity_now else {"state": material_state["state"]},
                restored=True, unbound=True)
        else:
            identity_now = materials_identity(material_state["manifest"])
            entry_record["materials"] = ({"identity": identity_now} if identity_now
                                         else {"state": material_state["state"]})
            if not payload.get("materials"):
                entry_record["materials"]["unbound"] = True
        # 标准漂移在**导入**这一侧也标成事实（判定侧才阻断）：让"这份报告提交时标准已变"可见，
        # 又不因为"判断还没写"把正常顺序（导入 → 判断 → 判定）卡住。
        standard_positions = standard_drift_positions(
            anchor_drift(((task.get("check") or {}).get("anchor") or {}).get("parts"), _parts) or [])
        if standard_positions:
            entry_record["standard_drift"] = standard_positions
        if lifted:
            entry_record["broken_reference"] = {"declared": True, "lifted": lifted}
        if discovered:
            entry_record["agent"] = identity
        imported.append(entry_record)
        reviews["imported"] = imported
        task["reviews"] = reviews
        inputs = {"task": task.get("id"), "round": int(round_no), "slot": record_slot}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.import", holder, inputs, ["verify_metadata", "verify_anchor", "publish"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.import", holder, inputs, action, evidence_refs=[digest]
        )
    from . import codes

    # A2（三轮二审）：导入是半完成态——next_ 给全收敛引线，不给"只差另一份报告"的错觉。
    # 全部在机制内可判：按 launch 声明槽位与已导入槽位求差集。
    launch_slots_now = [slot.get("slot") for slot in ((launch or {}).get("slots") or [])
                        if isinstance(slot, dict) and slot.get("slot")]
    imported_slots_now = sorted({str(entry.get("slot")) for entry in imported
                               if int(entry.get("round") or 0) == int(round_no)})
    missing_slots = [slot for slot in launch_slots_now if slot not in imported_slots_now]
    next_text = (f"第 {int(round_no)} 轮报告已齐：用 `review-decide --round {int(round_no)} "
                 "--main-review-draft` 生成复核骨架，"
                 "填完五轴/逐报告/逐 finding 后 `--main-review` 判定（处置与判定步骤见 wf-review-action）"
                 if not missing_slots else
                 f"还差槽位报告：{'、'.join(missing_slots)}——补齐后按 wf-review 产出并 "
                 f"`review-import --round {int(round_no)}`；"
                 f"本轮报告已齐后用 `review-decide --round {int(round_no)} --main-review-draft` "
                 "生成复核骨架再判定")
    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_=next_text,
        facts={"round": int(round_no), "slot": record_slot, "report_digest": digest,
               "verdict": payload.get("verdict"), "findings": payload.get("findings"),
               "missing_slots": missing_slots,
               **(dict(agent=identity) if discovered else {}),
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


def pattern_overlap(read, excluded):
    """读声明与排除面的可证交叠（三面）：返回说明或 None。"""
    from . import paths as paths_mod

    try:
        if paths_mod.match_path(excluded, read):
            return "excluded pattern matches the declared read path"
        if not any(char in read for char in "*?["):
            # 目录读声明（纯字面）包含排除子目录：`pkg` 包含 `pkg/secret/**`。
            if paths_mod.match_path(read.rstrip("/") + "/**", excluded):
                return "declared read path includes the excluded surface"
        if paths_mod.subsumes(read, excluded):
            return "declared read pattern is inside the excluded surface"
        if paths_mod.subsumes(excluded, read):
            return "declared read pattern includes the excluded surface"
    except Exception:  # noqa: BLE001 — 无法解释的模式不当作矛盾
        return None
    return None


def normalize_scope_path(text):
    """读/排除声明的比较用规范路径；非法形状保留原样，交给形状检查报错。"""
    from . import paths as paths_mod
    raw = str(text).replace("\\", "/")
    try:
        return paths_mod.normalize(raw)
    except Exception:  # noqa: BLE001
        return raw


def read_scope_problems(payload, allowed_prd=None):
    """报告不得同时声明「读取」与「排除」同一面。

    只核可比较的路径模式：排除模式命中读声明、读声明完全落在排除面内、或读声明
    包含排除面，三者任一成立即矛盾。自然语言归类留给主会话复核，不在这里猜。
    """
    reads = [normalize_scope_path(item) for item in payload.get("read-scope") or []
             if str(item).strip() and str(item) not in ("materials",)
             and not str(item).startswith("materials/")]
    if allowed_prd:
        # 本任务 PRD 是显式放行的需求材料；排除面里的 .wf/tasks/** 不把它算成冲突。
        prd_norm = normalize_scope_path(allowed_prd)
        reads = [read for read in reads if read != prd_norm]
    excludes = [normalize_scope_path(item) for item in payload.get("excluded-scope") or []
                if str(item).strip()]
    problems = []
    for read in reads:
        for excluded in excludes:
            overlap = pattern_overlap(read, excluded)
            if overlap:
                problems.append({"reason": "read-scope intersects excluded-scope",
                                 "read": read, "excluded": excluded, "overlap": overlap,
                                 "exits": ["把该路径从 read-scope 移除（若确实未读）",
                                           "或修正 excluded-scope/报告正文；越界读取按审查未通过处理"]})
                break
    return problems


def anchor_identity_problems(anchor, task=None):
    """`check-anchor` 的形状与 Check 身份（`check_id` + `check_anchor`）。

    `check_anchor` 相同不代表同一份 Check：重跑 Check 会生成新 id，旧报告必须失效。
    形状问题与身份问题分开列，调用方按入口语义选择 code。
    """
    if not isinstance(anchor, dict):
        return [{"reason": "check-anchor must be an object", "value": anchor}]
    problems = []
    if not str(anchor.get("check_id") or "").strip():
        problems.append({"reason": "check-anchor.check_id missing"})
    if not str(anchor.get("check_anchor") or "").strip():
        problems.append({"reason": "check-anchor.check_anchor missing"})
    if task is not None:
        check = task.get("check") or {}
        current = check.get("id")
        current_anchor = (check.get("anchor") or {}).get("check_anchor")
        declared = anchor.get("check_id")
        if declared and current and declared != current:
            # 同锚点重跑 Check 只是**同内容重验**：轮次身份继续有效，不必整轮重开
            # （十二轮 b-3）。锚点不同才是真变化，仍按身份不符拒绝。
            if not (current_anchor and anchor.get("check_anchor") == current_anchor):
                problems.append({"reason": "check-anchor.check_id is not the current Check",
                                 "declared": declared, "current": current,
                                 "declared_anchor": anchor.get("check_anchor"),
                                 "current_anchor": current_anchor})
    return problems


def review_report_problems(ctx, task, *, round_no, launch, imported, anchor):
    """报告与锚点问题（`problems` 通道）：逐份重核摘要、锚点、范围与轴。

    ⑥ 提取（原 `decide` 内的循环原样搬出）：`decide` 与 `repair_scope` 共用同一判据。
    返回 `{problems, failures, gaps_out, source_clis, blockers}`；`blockers` 是短原因 token
    （`report_invalid` / `anchor_stale`），供 `launches[].blocked` 直接呈现。
    """
    problems, failures, gaps_out, source_clis, blockers = [], [], [], [], []
    report_axes = {}
    declared_slots = {slot.get("slot"): slot.get("reviewer_cli")
                      for slot in (launch or {}).get("slots") or []
                      if isinstance(slot, dict) and slot.get("slot")}
    current_materials = round_materials_identity(ctx, task, round_no)
    for entry in imported:
        rel = entry.get("report_path")
        if not rel:
            problems.append({"slot": entry.get("slot"), "reason": "imported entry lacks report_path"})
            blockers.append("report_invalid")
            continue
        report_abs = join(ctx.root, rel)
        # 导入端防住"同路径换内容"，判定端必须同样重核摘要：否则报告文件可被事后改写
        current_digest, cause, reason = records.file_digest_state(report_abs)
        if cause == "unreadable":
            problems.append({"slot": entry.get("slot"), "reason": "report file unreadable",
                             "path": rel, "error": reason})
            blockers.append("report_invalid")
            continue
        if entry.get("report_digest") != current_digest:
            problems.append({"slot": entry.get("slot"), "reason": "report file changed after import",
                             "recorded": entry.get("report_digest"), "current": current_digest,
                             "path": rel})
            blockers.append("report_invalid")
            continue
        try:
            with open(report_abs, "r", encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            problems.append({"slot": entry.get("slot"), "reason": "report file unreadable",
                             "path": rel, "error": str(exc)})
            blockers.append("report_invalid")
            continue
        try:
            payload = parse_report(text)
        except ReviewError as exc:
            # 结构不成立也是一条"报告问题"，不是异常出口：status/预检不得因此抛栈
            problem = {"slot": entry.get("slot")}
            problem.update(exc.facts or {})
            problem.setdefault("reason", exc.code)
            problems.append(problem)
            blockers.append("report_invalid")
            continue
        proposer = normalize_agent(entry.get("agent") or payload.get("source-cli") or entry.get("slot"))
        source_clis.append(proposer)
        report_anchor = payload.get("check-anchor")
        if not isinstance(report_anchor, dict) or report_anchor.get("check_anchor") != anchor:
            # 失效锚点一律重审，不能因旧文件仍在而复用（机制稿 §9.2）
            problems.append({"slot": entry.get("slot"), "reason": "report anchor does not match current check",
                             "report_anchor": report_anchor, "current_anchor": anchor})
            blockers.append("anchor_stale")
        declared_cli = declared_slots.get(entry.get("slot"))
        if declared_cli and payload.get("source-cli") != declared_cli:
            problems.append({"slot": entry.get("slot"), "reason": "report source-cli not declared for slot",
                             "source_cli": payload.get("source-cli"), "declared": declared_cli})
            blockers.append("report_invalid")
        # 输入面走**共享实现**（与 lint / import 同源）：同一份报告在三处的输入结论一致。
        # 状态头不在判定处重核——它是"导入时是否已完成"的事实，已在导入那一刻定案，
        # 判定侧重读同一份已导入文件不会产生新信息。
        shared = report_input_problems(
            payload, task=task, launch=launch, materials_identity=current_materials,
            materials_restored=bool((entry.get("materials") or {}).get("restored")))
        for problem in flatten_checks(shared["checks"]):
            problems.append(dict(problem, slot=entry.get("slot")))
            blockers.append("report_invalid")
        # 登记过材料身份、但与本轮当前材料不同：判定读不到 reviewer 当时读的那批字节。
        bound = (entry.get("materials") or {}).get("identity")
        # 基线视图只算一次（同一实现供提示与 status 复用）
        basis = round_materials_basis(imported, current_materials)
        # restore 记录的身份来自记录本身（历史证据），与现场不同是常态：降为事实不阻断，
        # 否则"恢复入口允许导入、判定却永远过不去"。`unbound` 同档说明强度。
        if bound and current_materials and bound != current_materials:
            restored_entry = bool((entry.get("materials") or {}).get("restored"))
            mixed = basis["mixed"]
            if not restored_entry or mixed:
                problems.append({"slot": entry.get("slot"),
                                 "reason": ("round mixes restored and current material identities"
                                            if mixed else "imported report is bound to different round materials"),
                                 "bound": bound, "current": current_materials,
                                 "restored": restored_entry,
                                 "unbound": bool((entry.get("materials") or {}).get("unbound")),
                                 **({"exits": ["把这一份也按 `--restore` 重导（标成历史证据）",
                                               "或按新材料重写报告并开新一轮"]} if mixed else {})})
                blockers.append("materials_stale")
        report_axes[entry.get("slot")] = payload.get("axes") or {}
        # 缺口只由 `axes: uncovered` 承载。`scope-exceptions` / `material-gaps` 这类自由文本
        # 不再一义多用：主会话复核补足或人接受缺口，材料不足写进对应轴。
        gaps, blocking = shared["gaps"], shared["blocking"]
        for gap in gaps:
            gaps_out.append(dict(gap, slot=entry.get("slot")))
        if blocking:
            failures.append({"slot": entry.get("slot"), "reason": "report carries blocking findings",
                             "findings": blocking})
    return {"problems": problems, "failures": failures, "gaps_out": gaps_out,
            "source_clis": source_clis, "blockers": sorted(set(blockers)),
            "report_axes": report_axes}


def review_eligibility(distinct, implementation, *, imported_count, declared_slots):
    """输入是否合格（`input_problems` 通道）：人数与异种。**不与报告问题合并**（矩阵 #28）。

    返回 `{problems, blockers}`：`implementer_overlap` / `insufficient_reviewers` / `material_missing`
    只在这里产出——`blocked` 是"已成立的事实"，不做优先级合成。
    """
    problems, blockers = [], []
    if len(distinct) < 2:
        problems.append({"reason": "人数不合格：需要两个彼此不同的审查 CLI",
                         "reviewer_clis": distinct})
        # 材料是否还可能到：已导入数 < 声明槽位数即"还有槽位可能到"（发现式 2/3 已够判定）
        blockers.append("material_missing" if imported_count < declared_slots else "insufficient_reviewers")
    overlap = sorted(implementation & set(distinct))
    if overlap:
        problems.append({"reason": "审查 CLI 与实施 CLI 重叠",
                         "reviewer_clis": distinct, "implementation": sorted(implementation)})
        blockers.append("implementer_overlap")
    return {"problems": problems, "blockers": sorted(set(blockers))}


def consume_recovered(ctx, task):
    """⑥ 消费钩子（一次一事件）：报告重新可核实 → 该键的放行记录置 `consumed: true`。

    只在受控写点调用（`review-import` / `review-decide` / `wf archive` 的预检前）。
    **保证范围精确**：只保证「写点观察到恢复后该放行失效」；「恢复 → 期间无写命令 → 再次损坏」
    不在保证内（归档钩子只兜住「归档时报告仍可核实」那一支）。
    """
    entries = acceptance_records(task)
    if not entries:
        return []
    verified = {}
    for entry in (task.get("reviews") or {}).get("imported") or []:
        if not isinstance(entry, dict) or not entry.get("report_path"):
            continue
        digest, cause, _reason = records.file_digest_state(join(ctx.root, entry.get("report_path")))
        # 读不到 ⇒ 未观察到恢复（不放行失效）；与"文件被改"同处理，不把 IO 故障当成恢复
        verified[(int(entry.get("round") or 0), entry.get("slot"))] = (
            cause is None and digest == entry.get("report_digest"))
    consumed = []
    for item in entries:
        if item.get("revoked") or item.get("consumed"):
            continue
        key = release_key(item)
        if verified.get(key[:2]):
            item["consumed"] = True
            item["consumed_at"] = records.now_str()
            consumed.append({"round": key[0], "slot": key[1], "report_digest": key[2]})
    return consumed


def acceptance_echo(task):
    """当前生效的放行清单（status 与 archive 强制回显的同一形状）。"""
    return [{"round": item.get("round"), "slot": item.get("slot"),
             "report_digest": item.get("report_digest"), "by": item.get("by"),
             "at": item.get("at"), "quote": _masked_quote(item.get("quote")),
             "batch": item.get("batch")}
            for item in active_acceptances(task)]


def registered_digest(task, round_no, slot):
    """登记摘要（决定文件的 digest 权威来源，不是损坏文件的当前摘要）。"""
    for entry in (task.get("reviews") or {}).get("imported") or []:
        if not isinstance(entry, dict):
            continue
        if int(entry.get("round") or 0) == int(round_no or 0) and entry.get("slot") == slot:
            return entry.get("report_digest")
    return None


def _launch_form(imported):
    """`discovered`／`legacy`／`null`（无导入）——逐轮原始形态，不做三态合成。"""
    if not imported:
        return None
    return "discovered" if any("agent" in entry for entry in imported) else "legacy"


def launch_facts(ctx, task):
    """⑥ 逐轮 launch 原始事实（扁平）：`{round, form, imported, declared, decided, blocked}`。"""
    reviews = task.get("reviews") or {}
    try:
        anchor, _parts = _current_anchor(ctx, task)
    except ReviewError:
        anchor = None
    out = []
    for entry in reviews.get("launches") or []:
        if not isinstance(entry, dict):
            continue
        round_no = int(entry.get("round") or 0)
        imported = [item for item in reviews.get("imported") or []
                    if isinstance(item, dict) and int(item.get("round") or 0) == round_no]
        form = _launch_form(imported)
        declared_slots = len(entry.get("slots") or [])
        reviewers = sorted({normalize_agent(item.get("agent") or item.get("slot"))
                            for item in imported if item.get("slot")})
        implementer = review_cli(entry.get("implementation_cli"))
        blocked = []
        problems = []
        if imported and anchor is not None:
            report_facts = review_report_problems(ctx, task, round_no=round_no, launch=entry,
                                                 imported=imported, anchor=anchor)
            blocked.extend(report_facts["blockers"])
            problems = report_facts["problems"]
        eligibility = review_eligibility(reviewers, {implementer} if implementer else set(),
                                         imported_count=len(imported), declared_slots=declared_slots)
        blocked.extend(eligibility["blockers"])
        # B3：`blocked` 是组标签（report_invalid / anchor_stale / material_missing /
        # insufficient_reviewers / implementer_overlap）。标签命中时**并排**给出它概括的事实行，
        # 否则"哪一份、因为什么"就被 token 遮住了。
        out.append({"round": round_no, "form": form, "imported": len(imported),
                    "declared": declared_slots,
                    "decided": latest_decision(task, round_no) is not None,
                    "blocked": sorted(set(blocked)),
                    "problems": problems,
                    "scope": entry.get("scope"),
                    "eligibility": eligibility})
    return out


def unverifiable_evidence(ctx, task, *, findings=None):
    """⑥ `unverifiable` 的唯一产出：`open_findings` 的 unavailable + 引用/放行/消费事实。"""
    findings = findings if findings is not None else open_findings(ctx, task)
    reviews = task.get("reviews") or {}
    cited = cited_keys(reviews)
    active = {release_key(item) for item in active_acceptances(task)}
    consumed = {release_key(item) for item in acceptance_records(task) if item.get("consumed")}
    out = []
    for item in findings["unavailable"]:
        if item.get("report_digest") is None:
            # A6 裁定：缺登记摘要的遗留记录既不能核验也不能放行 → 单列 `legacy_unverifiable`，
            # 不进入 `unverifiable`（否则 exits 会给出做不到的 restore/human_release）
            continue
        entry = dict(item)
        key = release_key(item)
        entry["cited"] = key[:2] in cited
        entry["release_allowed"] = release_allowed_for(item, task, cited=entry["cited"])
        entry["released"] = key in active
        entry["consumed"] = key in consumed
        # 三态（§3a）：已豁免（未知）／已失效（一次一事件后再次损坏）／未知（未放行）
        entry["state"] = ("accepted-risk" if entry["released"]
                          else ("consumed" if entry["consumed"] else "unresolved"))
        out.append(entry)
    return out


def legacy_unverifiable(ctx, task):
    """A6 裁定：缺登记摘要的遗留记录——机制既不能核验也不能放行，`status` 单列。

    它们**不计入 C3 阻断**（否则旧任务永久卡死）。补摘要的唯一路径是用现有
    `review-import` 对同轮同槽位重导一次；重导合法性依赖"文件内容未被篡改"，
    机制无法证明——属遗留风险，如实登记在 `note` 里。

    每条都带**明确出口**（A6 需要的产出）：补摘要 / 另开新一轮 / 放弃任务。出口只写
    人可执行的文本，不复用门禁的 `{condition, action}` 词表——那些是 `exits_for` 的
    唯一产出，这里不是门禁条件。
    """
    out = []
    for item in open_findings(ctx, task)["unavailable"]:
        if item.get("report_digest") is not None:
            continue
        out.append(dict(item, note="缺登记摘要，机制既不能核验也不能放行", exits=[
            "补登记摘要：对同轮同槽位重导同一份报告（`wf review-import --task <id>`；"
            "磁盘字节已变时加 `--restore`）",
            "换一轮重新审查：`wf review-launch --task <id> ...`，由新轮结论覆盖这条遗留证据",
            "任务不再继续：`wf task-abandon --task <id>`",
        ]))
    return out


def exiting_evidence(ctx, task):
    """C3 的**阻断口径**（唯一实现）：只统计仍承载未完成义务、且未被放行的不可核实证据。

    ① 当前 `result` 引用的报告；② 所属轮最新 verdict ≠ pass（含未判定）；③ 属于当前
    `result` 那一轮的任何报告。仅「已 pass ∧ 不在 result 轮 ∧ 未被引用」的历史报告豁免。
    **A6 裁定**：登记摘要缺失（`report_digest` 为 null）的遗留记录**不计入阻断**——机制既
    不能核验也不能证明身份，阻断只会让旧任务永久卡死；它们在 `status` 的 `legacy_unverifiable`
    里单列。
    """
    reviews = task.get("reviews") or {}
    result = reviews.get("result") or {}
    result_round = int(result.get("round") or 0)
    cited = cited_keys(reviews)
    out = []
    for item in unverifiable_evidence(ctx, task):   # 缺登记摘要的记录已在此被排除
        key = release_key(item)
        if item.get("released"):
            continue
        carries = (key[:2] in cited) or (int(item.get("round") or 0) == result_round)
        if not carries:
            decision = latest_decision(task, int(item.get("round") or 0))
            verdict = (decision or {}).get("verdict")
            carries = verdict != "pass"
        if carries:
            out.append(item)
    return out


def exits_for(facts):
    """⑥ 唯一出口实现：返回 `[{condition, action, round}]`（无 `preferred`、无 `when`）。"""
    conclusion = facts["conclusion"]
    exits = []
    if not conclusion.get("check_valid"):
        exits.append({"condition": "C1", "action": "rerun_check", "round": None})
    if facts["open_blocking"]:
        exits.append({"condition": "C2", "action": "record_disposition", "round": None})
    unreleased = [item for item in facts["unverifiable"] if not item.get("released")]
    if unreleased:
        exits.append({"condition": "C3", "action": "restore_bytes", "round": None})
        if any(item.get("release_allowed") for item in unreleased):
            exits.append({"condition": "C3", "action": "human_release", "round": None})
    c4_met = (not facts["review_required"]
              or (conclusion.get("verdict") == "pass" and conclusion.get("binding")))
    if not c4_met:
        binding_round = conclusion.get("round") if conclusion.get("binding") else None
        for launch in facts["launches"]:
            blocked = set(launch.get("blocked") or [])
            if not blocked and not launch.get("decided"):
                exits.append({"condition": "C4", "action": "resume_inflight", "round": launch["round"]})
            elif not blocked and launch.get("decided") and launch["round"] != binding_round:
                exits.append({"condition": "C4", "action": "redecide_round", "round": launch["round"]})
            elif blocked and blocked <= {"material_missing"}:
                exits.append({"condition": "C4", "action": "await_material", "round": launch["round"]})
        # 常列（不设「check 换代」门槛）：重判的真正前提是报告锚点仍匹配
        exits.append({"condition": "C4", "action": "relaunch_review", "round": None})
    if not c4_met or unreleased:
        terminal = "C4" if facts["review_required"] else "C3"
        exits.append({"condition": terminal, "action": "pause_for_human", "round": None})
        exits.append({"condition": terminal, "action": "abandon_task", "round": None})
    return exits


def _stale_extra(reviews, result):
    """判定之后该轮新导入、未被结论引用的报告 slot（派生事实，非门禁条件）。"""
    round_no = int(result.get("round") or 0)
    if not result.get("verdict"):
        return []
    cited = {item.get("slot") for item in result.get("imported") or [] if isinstance(item, dict)}
    return [{"round": round_no, "slot": entry.get("slot"), "report_path": entry.get("report_path")}
            for entry in reviews.get("imported") or []
            if isinstance(entry, dict) and int(entry.get("round") or 0) == round_no
            and entry.get("slot") not in cited]


def repair_scope(ctx, task):
    """⑥ 修复态的事实集（纯派生、不落盘；无单一状态枚举）。

    `open_blocking` / `unverifiable` 与归档门禁**同源**（`open_findings`），`conclusion` 的两项
    子判定来自 `gates.check_validity` / `gates.review_binding`（不另写判据），`exits` 只由
    `exits_for` 产出。
    """
    from . import gates as gates_mod

    reviews = task.get("reviews") or {}
    result = reviews.get("result") or {}
    findings = open_findings(ctx, task)
    check_facts = gates_mod.check_validity(ctx, task)
    if result.get("verdict"):
        binding_facts = gates_mod.review_binding(ctx, task, result=result)
    else:
        binding_facts = {"binding": False, "blockers": []}
    conclusion = {
        "decided": bool(result.get("verdict")),
        "verdict": result.get("verdict"),
        "round": result.get("round") if result.get("verdict") else None,
        "check_id": result.get("check_id") if result.get("verdict") else None,
        "binding": binding_facts["binding"],
        "binding_blockers": binding_facts["blockers"],
        "check_valid": check_facts["valid"],
        "check_blockers": check_facts["blockers"],
        "stale_extra": _stale_extra(reviews, result),
    }
    # 便利派生（§2.1）：**仅作展示**，不是任何完成条件（条件用 C1/C4 各自的原始事实）
    conclusion["applicable"] = bool(conclusion["binding"] and conclusion["check_valid"])
    facts = {
        "review_required": review_required(task),
        "rounds": [dict(item) for item in decision_rounds(task)],
        "launches": launch_facts(ctx, task),
        "open_blocking": findings["blocking"],
        "unverifiable": unverifiable_evidence(ctx, task, findings=findings),
        "conclusion": conclusion,
    }
    return dict(facts, exits=exits_for(facts))


def acceptance_problems(task, payload, current):
    """决定文件校验（纯函数）：`(bad, accepted)`。任何项不合法 → 整批拒绝（零写入）。

    `current` 是 `{release_key: unverifiable 条目}`：**可放行条件在这里强制**，
    不只是展示——complex 的引用证据（`release_allowed == false`）必须拒绝放行。
    """
    batch_id = str(payload.get("batch") or "").strip()
    items = payload.get("acceptances")
    bad, accepted = [], []
    if not batch_id:
        bad.append({"reason": "batch 必填"})
    if not isinstance(items, list) or not items:
        bad.append({"reason": "acceptances 必须是非空数组"})
    for index, item in enumerate(items if isinstance(items, list) else []):
        if not isinstance(item, dict):
            bad.append({"index": index, "reason": "acceptance 必须是对象"})
            continue
        problems = []
        for field in ("quote", "by", "at", "source"):
            if not str(item.get(field) or "").strip():
                problems.append({"field": field, "reason": "必填"})
        if not str(item.get("by") or "").startswith("human:"):
            problems.append({"field": "by", "reason": "必须 human: 前缀"})
        if item.get("waive_unknown_findings") is not True:
            problems.append({"field": "waive_unknown_findings",
                             "reason": "必须显式承认该报告未知 findings 一并豁免"})
        registered = registered_digest(task, item.get("round"), item.get("slot"))
        if item.get("report_digest") is None or item.get("report_digest") != registered:
            # 防 typo 生成永不匹配的记录：不等即整批拒绝
            problems.append({"field": "report_digest",
                             "reason": "必须等于该 (round, slot) 的登记摘要",
                             "registered": registered, "given": item.get("report_digest")})
        entry = current.get(release_key(item))
        if entry is None:
            problems.append({"reason": "该 (round, slot, report_digest) 不在当前 unverifiable 中（不做预放行）"})
        elif not entry.get("release_allowed"):
            # B2 / §2.2：complex 的引用证据不可放行——放行只解除 C3，不能替代新审查
            problems.append({"reason": "该条不可放行：complex 的引用证据（release_allowed == false）",
                             "cited": entry.get("cited"), "review_required": task.get("plan", {}).get(
                                 "complexity") == "complex",
                             "exits": ["先完成一次新审查，使旧报告变成非引用证据后再放行",
                                       "或找回原字节（restore_bytes）"]})
        if problems:
            bad.append({"index": index, "round": item.get("round"), "slot": item.get("slot"),
                        "problems": problems})
        else:
            accepted.append(item)
    return bad, accepted


def merge_acceptances(kept, accepted, batch_id, now):
    """写入合并（纯函数）：幂等与 `released` 完全同口径；已撤销/已消费则新增一条。"""
    added, already = [], []
    for item in accepted:
        key = release_key(item)
        existing = next((entry for entry in kept
                         if isinstance(entry, dict) and not entry.get("revoked")
                         and not entry.get("consumed") and release_key(entry) == key), None)
        if existing is not None:
            already.append({"round": key[0], "slot": key[1], "report_digest": key[2],
                            "batch": existing.get("batch")})
            continue
        kept.append({"batch": batch_id, "round": key[0], "slot": key[1], "report_digest": key[2],
                     "quote": _masked_quote(item.get("quote")), "by": item.get("by"),
                     "at": item.get("at"),
                     "source": item.get("source"), "waive_unknown_findings": True,
                     "accepted_at": now, "revoked": False, "consumed": False})
        added.append({"round": key[0], "slot": key[1], "report_digest": key[2], "batch": batch_id})
    return added, already


def accept_unknown(ctx, task, decision_path=None, *, revoke=False, batch=None, round_no=None,
                   slot=None, digest=None):
    """人裁放行（乙通道）：批次**全有或全无**；撤销只标记不删除。

    - `digest` 的权威来源是**导入记录里的登记摘要**；决定文件与该值不等 → 整批拒绝。
    - 匹配键 `(round, slot, report_digest)` 三者全等，且该条必须在**当前** `unverifiable` 中。
    - 幂等与 `released` 同口径：只有「同键 ∧ 未撤销 ∧ 未消费」才回报 `already_accepted`。
    """
    from . import lock
    from . import tasks as tasks_mod

    if revoke:
        by_batch = batch is not None
        by_key = any(value not in (None, "") for value in (round_no, slot, digest))
        if by_batch == by_key:
            raise ReviewError("WF_PATH_INVALID", {
                "reason": "--revoke 需要 --batch 或 --round/--slot/--digest 之一（同时给出不猜优先级）"})
    elif not decision_path:
        raise ReviewError("WF_PATH_INVALID", {"reason": "需要 --file <决定.json>（或用 --revoke）"})
    payload = None
    if not revoke:
        payload = records.load_json(decision_path)
        if not isinstance(payload, dict):
            raise ReviewError("WF_PATH_INVALID", {"reason": "决定文件缺失或不是对象", "path": decision_path})
    with lock.acquire(ctx.root, holder_hint="review-accept-unknown"):
        _record, holder = _require_held_for_task(ctx, task)
        path = _task_dir(ctx, task)
        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.setdefault("reviews", {})
        kept = reviews.get("unknown_acceptances")
        if not isinstance(kept, list):
            kept = []
        inputs = {"task": task.get("id"), "revoke": bool(revoke), "batch": batch}
        if revoke:
            targets = []
            for item in kept:
                if not isinstance(item, dict):
                    continue
                if batch is not None and item.get("batch") == batch:
                    targets.append(item)
                elif batch is None and release_key(item) == (int(round_no or 0), slot, digest):
                    targets.append(item)
            if not targets:
                raise ReviewError("WF_TARGET_MISSING", {
                    "reason": "没有匹配的放行记录",
                    "selectors": {"batch": batch, "round": round_no, "slot": slot,
                                  "report_digest": digest}})
            changed = []
            for item in targets:
                if item.get("revoked"):
                    continue
                item["revoked"] = True
                item["revoked_at"] = records.now_str()
                changed.append({"round": item.get("round"), "slot": item.get("slot"),
                                "report_digest": item.get("report_digest"), "batch": item.get("batch")})
            reviews["unknown_acceptances"] = kept
            task["reviews"] = reviews
            task, action = tasks_mod._start_task_action(
                ctx, path, task, "review.decide", holder, inputs, ["record_unknown_acceptance"])
            task, assertion = tasks_mod._finish_task_action(
                ctx, path, task, "review.decide", holder, inputs, action)
            return _accept_result(task, {"revoked": changed}, kept, assertion)
        current = {release_key(entry): entry for entry in unverifiable_evidence(ctx, task)}
        batch_id = str(payload.get("batch") or "").strip()
        bad, accepted = acceptance_problems(task, payload, current)
        if bad:
            raise ReviewError("WF_REVIEW_INVALID", {
                "bad_items": bad,
                "reason": "决定文件不合规：整批拒绝，零写入",
                "exits": ["按 bad_items 修正决定文件后重跑（digest 必须抄登记摘要，不是损坏文件的当前摘要）"]})
        added, already = merge_acceptances(kept, accepted, batch_id, records.now_str())
        reviews["unknown_acceptances"] = kept
        task["reviews"] = reviews
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.decide", holder, inputs, ["record_unknown_acceptance"])
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.decide", holder, inputs, action)
    return _accept_result(task, {"added": added, "already_accepted": already}, kept, assertion)


def _accept_result(task, facts, kept, assertion):
    from . import codes

    active = acceptance_echo(task)
    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_="放行只解除 C3，不改变 C2；撤销用 --revoke",
        facts=dict(facts, unknown_acceptances=active, control_assertion=assertion))


def decide(ctx, task, round_no=None, plan_path=None, unavailable_path=None, register_only=False,
           gap_acceptance_path=None, main_review_path=None, single_reviewer_acceptance_path=None):
    """判定（2026-11-07）：round 缺省取最新已发起轮；审核者身份取导入记录里的文件名 token。

    `register_only=True`（A8）：**只登记复核关闭**，不产生结论——不推导 verdict、不写
    `result` / `rounds[]` / `attempts`，因此不需要凑齐人数/异种资格。关闭本身的硬条件照旧：
    结构、`recheck_by` 不得自证、finding 必须属已导入报告（A9 的精确身份）。

    `gap_acceptance_path`：人接受覆盖缺口的确认文件（`by/at/quote/source` + `round` + `axes`）。
    未覆盖的轴不构成审查通过，也不构成缺陷；没有这份确认时本命令输出需人裁决档。

    `main_review_path`（2026-11-13）：主会话复核文件。reviewer 报告是辅助证据；产生 verdict
    前必须提交本轮五轴复核。覆盖由主会话复核与**主会话采信的报告**合并，两者都未覆盖的轴才是缺口。
    """
    if main_review_path and unavailable_path:
        raise ReviewError("WF_SEMANTIC_DECISION", {
            "reason": "审查不可用声明不能同时提交主会话复核",
            "exits": ["先 review-decide --unavailable <声明> 留痕",
                      "或去掉 --unavailable，用 --main-review 做判定"]})
    if gap_acceptance_path and (register_only or unavailable_path):
        raise ReviewError("WF_SEMANTIC_DECISION", {
            "reason": "缺口接受文件只对产生判定的那次 review-decide 有效",
            "exits": ["去掉 --gap-acceptance 只做登记/不可用声明",
                      "需要判定时单独跑一次 review-decide（带 --gap-acceptance）"]})
    if register_only and unavailable_path:
        raise ReviewError("WF_SEMANTIC_DECISION",
                          {"reason": "--register-only 只登记关闭，不能同时声明审查不可用"})
    if single_reviewer_acceptance_path and (register_only or unavailable_path):
        raise ReviewError("WF_SEMANTIC_DECISION", {
            "reason": "单 reviewer 接受文件只对产生判定的那次 review-decide 有效",
            "exits": ["去掉 --single-reviewer-acceptance 只做登记/不可用声明",
                      "需要判定时单独跑一次 review-decide（带 --single-reviewer-acceptance）"]})
    if register_only and not (plan_path or main_review_path):
        raise ReviewError("WF_SEMANTIC_DECISION",
                          {"reason": "--register-only 需要 --plan 或 --main-review（没有可登记的内容）"})
    if unavailable_path and plan_path:
        # A14：审查做不成 ≠ 问题已关闭。同批登记等于用"不可用"顺手关掉 finding。
        raise ReviewError("WF_SEMANTIC_DECISION", {
            "reason": "审查不可用与登记关闭不能同批：这是两件不同的事实",
            "exits": ["先 `wf review-decide --register-only --plan <处置>` 登记复核关闭",
                      "再 `wf review-decide --unavailable <声明>` 声明本轮审查不可用"]})
    if round_no is None:
        _path = _task_dir(ctx, task)
        _record = records.load_json(os.path.join(_path, "task.json"))
        _launches = [entry for entry in (_record.get("reviews") or {}).get("launches") or []
                     if isinstance(entry, dict)]
        if not _launches:
            raise ReviewError("WF_SEMANTIC_DECISION", {"reason": "no review round was launched"})
        round_no = max(int(entry.get("round") or 0) for entry in _launches)
    round_no = int(round_no)
    if not register_only and not unavailable_path:
        # 标准漂移是“能否产正式结论”的前置，不是事实登记的前置：
        # unavailable/register-only 仍要能如实记录。
        standard_drift_gate(ctx, task)
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
    gap_decision = None
    if gap_acceptance_path:
        gap_decision = records.load_json(gap_acceptance_path)
        if not isinstance(gap_decision, dict):
            raise ReviewError("WF_PATH_INVALID",
                              {"reason": "gap acceptance file missing or not an object",
                               "path": gap_acceptance_path})
    single_decision = None
    if single_reviewer_acceptance_path:
        single_decision = records.load_json(single_reviewer_acceptance_path)
        if not isinstance(single_decision, dict):
            raise ReviewError("WF_PATH_INVALID",
                              {"reason": "single reviewer acceptance file missing or not an object",
                               "path": single_reviewer_acceptance_path})
    with lock.acquire(ctx.root, holder_hint="review-decide"):
        _record, holder = _require_held_for_task(ctx, task)
        path = _task_dir(ctx, task)
        from . import tasks as tasks_mod

        task = records.load_json(os.path.join(path, "task.json"))
        reviews = task.get("reviews") or {}
        current_check_id = (task.get("check") or {}).get("id")
        for item in dispositions:
            if isinstance(item, dict):
                # 提交轮随处置固化：旧轮 unable 是否被后续轮核实取代，只按这个事实判。
                item["submitted_round"] = int(round_no)
                if current_check_id:
                    # 本次提交的关闭只能绑定本次 Check；显式给的历史 check_id 不能借历史放行。
                    item["check_id"] = current_check_id
        # ⑥ 消费写点②：本命令观察到「放行记录对应的报告当前可核实」→ 该放行失效。
        # A8：只登记关闭也是写点，两条路径共用这一次调用（一个写点只消费一次）。
        consume_recovered(ctx, task)
        # 本轮材料身份：判定路径必须核（drift 即拒），结果一律按它记引用。
        material_state = materials_identity_state(ctx, task.get("id"), round_no)
        if not register_only and not unavailable_path:
            # 正式结论必须绑定有效的 Check；只发起/导入已核，判定不能拿已失效 Check 产 verdict。
            from . import gates as gates_mod
            from . import tasks as tasks_mod
            if not tasks_mod._is_approved_plan(task, ctx.root):
                raise ReviewError("WF_APPROVAL_MISSING", {
                    "reason": "规划批准已失效；当前 PRD 不再对应批准版本",
                    "exits": ["回 Plan 重新批准（或机械修订）后再 task-check",
                              "不要用旧 Check 产生审查结论"],
                })
            validity = gates_mod.check_validity(ctx, task)
            if not validity.get("valid"):
                raise ReviewError(validity.get("code") or "WF_CHECK_STALE",
                                  dict(validity.get("facts") or {},
                                       blockers=validity.get("blockers"),
                                       exits=["重新 Check 后再判定",
                                              "无法重查时交人/按暂停处置；Check 失效不属审查不可用声明"]))
            # 判定消费的是**本轮材料**：取材料时核过不等于此刻还成立。材料在物化后被改，
            # 报告与 verdict 就都失去被审对象（P1：此前判定只把 manifest 抄进结果）。
            # 本轮导入记录是否"没有现场身份可言"（此处 `imported` 还没组装，直接从记录取）：
            # restore 记录的身份来自记录、纯旧记录压根没有身份。两种都不该被现场漂移挡住。
            _round_entries = [entry for entry in reviews.get("imported") or []
                              if isinstance(entry, dict) and int(entry.get("round") or 0) == int(round_no)]
            history_round = round_is_history(_round_entries)
            if material_state["state"] == "drift" and not history_round:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "本轮材料在物化后被改动，不能据此产结论",
                    "round": round_no, "drift": material_state["drift"],
                    "manifest_check_id": (material_state["manifest"] or {}).get("check_id"),
                    "exits": ["有备份时把原字节放回材料目录，重跑 review-context（原字节 ⇒ 原身份）后再判定",
                              "材料确实变了：报告按新材料重写并开新一轮（同轮已登记摘要不可覆盖）",
                              "不手改材料目录；结果记的是报告绑定的材料身份"]})
        if register_only:
            # A8：只登记复核关闭或主会话已核实 finding。与判定共用同一把锁、同一套处置校验，
            # 但**不产生结论**：result / rounds[] / attempts 一律不动。
            # 但“用证据关闭”仍必须绑定一个当前有效的批准与 Check，不能借失效 Check 的旧 passed。
            if plan_path:
                from . import gates as gates_mod
                from . import tasks as tasks_mod
                if not tasks_mod._is_approved_plan(task, ctx.root):
                    raise ReviewError("WF_APPROVAL_MISSING", {
                        "reason": "登记关闭时规划批准已失效",
                        "exits": ["回 Plan 重新批准（或机械修订）后再登记关闭",
                                  "只登记 main finding 时去掉 --plan"],
                    })
                validity = gates_mod.check_validity(ctx, task)
                if not validity.get("valid"):
                    raise ReviewError(validity.get("code") or "WF_CHECK_STALE", {
                        "reason": "登记关闭必须基于仍有效的 Check",
                        **(validity.get("facts") or {}),
                        "blockers": validity.get("blockers"),
                        "exits": ["重新 Check 后再登记关闭",
                                  "只登记 main finding 时去掉 --plan；不要把失效 Check 当关闭证据"],
                    })
            proposers = proposers_from_history(ctx, task)
            registered_main = 0
            supersedes_digest = None
            if main_review_path:
                existing_main = [entry for entry in reviews.get("main_reviews") or []
                                 if isinstance(entry, dict)
                                 and int(entry.get("round") or 0) == int(round_no)]
                main_payload = records.load_json(main_review_path)
                if main_payload is None:
                    raise ReviewError("WF_PATH_INVALID",
                                      {"reason": "main review file missing", "path": main_review_path})
                if existing_main:
                    main_payload = merge_main_findings(main_payload, existing_main[-1])
                if not isinstance(main_payload, dict):
                    raise ReviewError("WF_REVIEW_INVALID",
                                      {"reason": "main review must be an object",
                                       "path": main_review_path})
                main_digest, main_cause, main_reason = records.file_digest_state(main_review_path)
                if main_cause:
                    raise ReviewError("WF_PATH_INVALID",
                                      {"reason": "main review unreadable", "path": main_review_path,
                                       "cause": main_cause, "detail": main_reason})
                if existing_main and existing_main[-1].get("file_digest") != main_digest:
                    decision = latest_decision(task, round_no) or {}
                    if decision.get("verdict") in ("pass", "unavailable"):
                        raise ReviewError("WF_REVIEW_INVALID", {
                            "reason": "本轮已判 pass/unavailable，登记入口不能改写主会话复核",
                            "round": int(round_no), "recorded": decision.get("verdict"),
                            "exits": ["要改结论请开新一轮 review-launch",
                                      "只登记 finding 时保持已有复核不变"],
                        })
                    previous = existing_main[-1]
                    resolved, _ambiguous, _unknown = disposition_keys(
                        list(reviews.get("dispositions") or []) + list(dispositions),
                        set(proposers))
                    accepted = {key for key, decision in resolved.items()
                                if decision == "accepted"}
                    revision_problems = main_review_revision_problems(
                        previous, main_payload.get("main_findings") or [], accepted, round_no)
                    if revision_problems:
                        raise ReviewError("WF_REVIEW_INVALID", dict(
                            {"round": int(round_no), "problems": revision_problems,
                             "exits": ["保留已有 main_findings 后再追加新 finding",
                                       "或用 dispositions 的 slot=main 记录重分类/关闭"]},
                            **revision_problems[0]))
                    supersedes_digest = previous.get("file_digest")
                discovery = not all(field in main_payload for field in
                                    ("axes", "report_review", "finding_review"))
                if discovery:
                    main_payload = dict(main_payload)
                    main_payload.setdefault("axes", {
                        axis: {"conclusion": "uncovered", "basis": "", "sources": [],
                               "finding_refs": []} for axis in REVIEW_AXES})
                    main_payload.setdefault("report_review", [])
                    main_payload.setdefault("finding_review", [])
                    imported_round = []
                    axis_reports = {}
                    # 已知 finding 集合仍取任务全量：否则机制刚继承回来的旧核实条目
                    # 会被判成 unknown finding，AI 只能重交整份复核才能绕过。
                    current_findings = [item for item in all_findings(ctx, task)]
                    open_items = []
                else:
                    imported_round = [entry for entry in reviews.get("imported") or []
                                      if isinstance(entry, dict)
                                      and int(entry.get("round") or 0) == int(round_no)]
                    axis_reports = {}
                    for entry in imported_round:
                        payload, cause, _reason = read_imported_report(ctx, entry)
                        if cause is None:
                            axis_reports[str(entry.get("slot"))] = (payload or {}).get("axes") or {}
                    current_findings = [item for item in all_findings(ctx, task)
                                        if int(item.get("round") or 0) == int(round_no)]
                    open_items = [item for item in open_findings(ctx, task)["blocking"]
                                  if int(item.get("round") or 0) == int(round_no)]
                assertion_ids, changed_rules = assertion_index(ctx, task)
                main_record, main_problems, main_semantic = validate_main_review(
                    main_payload, task_id=task.get("id"), round_no=round_no,
                    imported=imported_round, findings=current_findings,
                    open_blocking=open_items,
                    axis_reports=axis_reports, by=ctx.key(),
                    file_digest=main_digest, assertion_ids=assertion_ids,
                    changed_rules=changed_rules, discovery=discovery, task=task)
                if discovery and main_record is not None:
                    main_record["discovery"] = True
                if main_problems or main_semantic:
                    raise ReviewError("WF_REVIEW_INVALID", {
                        "problems": main_problems or main_semantic,
                        "round": int(round_no),
                        "exits": ["修正主会话复核后重跑 --register-only",
                                  "或改用全量 review-decide（需要完整报告输入）"],
                    })
                if existing_main and existing_main[-1].get("file_digest") == main_digest:
                    registered_main = 0
                else:
                    if supersedes_digest:
                        main_record["supersedes"] = supersedes_digest
                    reviews["main_reviews"] = list(reviews.get("main_reviews") or []) + [main_record]
                    task["reviews"] = reviews
                    registered_main = len(main_record.get("main_findings") or [])
                    for item in main_record.get("main_findings") or []:
                        if isinstance(item, dict) and item.get("id"):
                            proposers.setdefault((int(round_no), "main", str(item["id"])), "main")
            problems = dispositions_problems(dispositions, proposers)
            main_checks = {}
            for entry in reviews.get("main_reviews") or []:
                if not isinstance(entry, dict):
                    continue
                entry_round = int(entry.get("round") or 0)
                for item in entry.get("finding_review") or []:
                    if isinstance(item, dict) and item.get("slot") and item.get("finding_id"):
                        main_checks[(entry_round, str(item["slot"]),
                                     str(item["finding_id"]))] = item.get("check")
            problems = problems + verified_closure_problems(
                dispositions, None, proposers, round_no, main_checks=main_checks,
                evidence_check=lambda refs, check_id=None: evidence_ref_problems(
                    ctx, task, refs, check_id=check_id),
                historical_evidence_check=lambda refs: evidence_ref_problems(
                    ctx, task, refs, include_history=True),
                current_dispositions=dispositions)
            if problems:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": problems,
                    "proposers": [{"round": key[0], "slot": key[1], "finding_id": key[2]}
                                  for key in sorted(proposers)][:12],
                    "exits": ["按问题清单补 disposition 字段与复核人后重跑",
                              "若只想留下记录而不关闭，去掉 decision=accepted"]})
            reviews["dispositions"] = list(reviews.get("dispositions") or []) + dispositions
            task["reviews"] = reviews
            inputs = {"task": task.get("id"), "round": int(round_no), "register_only": True}
            task, action = tasks_mod._start_task_action(
                ctx, path, task, "review.close", holder, inputs,
                ["verify_dispositions", "record_dispositions"])
            closed = [item for item in dispositions if isinstance(item, dict)
                      and item.get("decision") == "accepted"]
            task, assertion = tasks_mod._finish_task_action(
                ctx, path, task, "review.close", holder, inputs, action)
            from . import codes as codes_mod

            return codes_mod.result(
                "WF_OK",
                object={"id": task.get("id"), "name": task.get("title")},
                position_=codes_mod.position(scope="task", phase=task.get("phase"),
                                             task_id=task.get("id"),
                                             action_id=task["action"]["id"],
                                             action_state=task["action"]["state"]),
                next_="关闭已登记（不产生审查结论）；需要结论时另行 review-decide",
                facts={"register_only": True,
                       "materials_state": material_state["state"],
                       "registered": len(dispositions),
                       "registered_main_findings": registered_main,
                       "closing": len(closed),
                       "not_closing": [{"finding_id": item.get("finding_id"),
                                        "decision": item.get("decision")}
                                       for item in dispositions
                                       if isinstance(item, dict) and item.get("decision") != "accepted"],
                       "control_assertion": assertion},
            )
        launch = None
        for entry in reviews.get("launches") or []:
            if int(entry.get("round") or 0) == int(round_no):
                launch = entry
                break
        scope_facts = review_scope_facts(ctx, task, launch)
        imported = [entry for entry in reviews.get("imported") or [] if int(entry.get("round") or 0) == int(round_no)]
        anchor, _parts = _current_anchor(ctx, task)
        distinct = []
        problems = []       # 输入不成立：报告/身份/锚点/材料不合规 → 拒绝，不写结论
        failures = []       # 有效审查给出的未通过结论 → 记 fail，成为复盘触发事实
        open_blocking_now = []  # 本轮写入 dispositions 后仍未关闭的 blocking（判定用）
        # 提出者要**跨轮累积**：只在"关闭所在轮"里找 proposer，会让第 1 轮提出的 finding
        # 在第 2 轮被同一份报告复核关闭而查不出来（隔一轮自证 = K4b 可绕过）。
        # A7：提出者从**全部历史报告重解析**取（导入记录不存 findings），跨轮有效
        proposers = proposers_from_history(ctx, task)   # (round, slot, finding_id) → 提出者
        main_record = None  # 只有产生 verdict 的路径才写主会话复核
        single_reviewer_facts = None   # W2-3：单 reviewer 留痕降级的事实（有接受记录时非 None）
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
            declared_slots_count = len((launch or {}).get("slots") or [])
            imported_slots = [normalize_agent(entry.get("slot")) for entry in imported]
            # 材料/报告是否到齐先于人数判定（六轮复核 B1）：两种导入形态共用这一处——
            # discovered 模式人数取自已导入报告，第二份只是没写完时会被误判成"单个 reviewer"，
            # 逼人签不可逆的残余风险接受；显式槽位模式原来落到更靠后的 missing_slots 分支。
            # 例外：人**已经**给出单 reviewer 残余风险接受时不再阻断——那说明缺的槽位是"确实不可用"
            # 而不是"还没写完"，此时该走人签降级（否则可用报告永远判定不了）。
            pending_acceptance, _pending_problems = single_reviewer_acceptance(
                single_decision, round_no, task_id=task.get("id"))
            if (declared_slots_count and len(imported) < declared_slots_count
                    and pending_acceptance is None):
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "本轮声明了更多审查槽位，报告还没导入齐（材料未到齐，不是人数不合格）",
                    "missing": [slot for slot in launch_slots if slot and slot not in imported_slots],
                    "declared_slots": declared_slots_count, "imported": len(imported),
                    "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                         for entry in imported],
                    "exits": ["等其余 reviewer 写完报告后**在同一轮** review-import 导入，再 review-decide",
                              "该槽位确实不可用（reviewer 失败/环境不足）：由人签单 reviewer 残余风险接受"
                              "（同 --single-reviewer-acceptance）后重判——此时不再等报告",
                              "要换 reviewer：用 review-launch 重新发起新一轮（同轮报告不跨轮复用）"],
                })
            # 人数不足，或"声明了更多槽位但人已签单 reviewer 残余风险接受且报告不会再来"：
            # 两种都进同一个降级分支（后者缺的槽位按确实不可用处理）。
            if (len(declared_slot_ids) < 2
                    or (pending_acceptance is not None and len(imported) < declared_slots_count)):
                # 单 reviewer（W2-3，三轮裁决④）：默认仍拒——复杂任务要求两位异种 reviewer。
                # 有人签残余风险接受记录（--single-reviewer-acceptance）时允许产出 verdict，
                # 留痕降级（degraded: single-provider + acceptance 引用）；接受只降级"人数"，
                # 主会话复核/未关闭 blocking 等其余门槛照旧。
                single_acceptance, single_problems = single_reviewer_acceptance(
                    single_decision, round_no, task_id=task.get("id"))
                if single_problems:
                    raise ReviewError("WF_REVIEW_INVALID", {
                        "reason": "single reviewer cannot produce a decision (degraded: single-provider)",
                        "declared": declared_slot_ids,
                        "degraded": "single-provider",
                        "problems": single_problems,
                        "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                             for entry in imported],
                        "exits": ["人接受残余风险：写接受文件（by/at/quote/source + round + residual_risk）"
                                  "后用 --single-reviewer-acceptance 重跑 review-decide",
                                  "补齐第二份报告（**同一轮**导入）后再判；确要换 reviewer 才重发新一轮"],
                    })
                if single_acceptance is None:
                    raise ReviewError("WF_REVIEW_INVALID", {
                        "reason": "single reviewer cannot produce a decision (degraded: single-provider)",
                        "declared": declared_slot_ids,
                        "degraded": "single-provider",
                        "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                             for entry in imported],
                        "exits": ["人接受残余风险：先 record single-reviewer-acceptance"
                                  "（by/at/quote/source + round + residual_risk）再判定",
                                  "补齐第二份报告（**同一轮**导入）后再判；确要换 reviewer 才重发新一轮",
                                  "按设计稿 §6.5 的不可用处置：review-decide --unavailable <声明文件> 留痕，"
                                  "复杂任务暂停或异常归档（不得据此判 pass）"],
                    })
                # 接受记录落任务记录（按轮绑定，判定后不可替换——main_reviews 幂等同型）
                existing_single = [entry for entry in reviews.get("single_reviewer_acceptances") or []
                                   if isinstance(entry, dict)
                                   and int(entry.get("round") or 0) == int(round_no)]
                if existing_single:
                    if existing_single[-1].get("attestation_digest") != single_acceptance["attestation_digest"]:
                        raise ReviewError("WF_REVIEW_INVALID", {
                            "reason": "本轮已有单 reviewer 接受记录，判定后不可替换",
                            "round": int(round_no),
                            "exits": ["保留既有接受记录直接判定",
                                      "确需撤回：按需人裁决处置（新轮重发）"],
                        })
                else:
                    reviews["single_reviewer_acceptances"] = list(
                        reviews.get("single_reviewer_acceptances") or []) + [single_acceptance]
                single_reviewer_facts = {
                    "degraded": "single-provider",
                    "single_reviewer_accepted": {
                        "attestation_digest": single_acceptance["attestation_digest"],
                        "quote_summary": _masked_quote(single_acceptance.get("quote"))[:80],
                        "by": single_acceptance.get("by"), "round": int(round_no)}}
            missing_slots = ([] if discovered_mode
                             else [slot for slot in declared_slot_ids if slot not in imported_slots])
            if missing_slots and pending_acceptance is None:
                # 声明的槽位都要有报告：缺一即输入不完整，不能按已导入的部分判 pass。
                # 人已签单 reviewer 残余风险接受时，缺的槽位按"确实不可用"处理（下面走降级判定）。
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"reason": "declared slots missing reports", "missing": missing_slots,
                                   "imported": imported_slots})
            # 报告/锚点问题与人数/异种问题**分列**（矩阵 #28）：两个共享函数不合并。
            report_facts = review_report_problems(ctx, task, round_no=round_no, launch=launch,
                                                 imported=imported, anchor=anchor)
            problems = report_facts["problems"]
            failures = report_facts["failures"]
            source_clis = report_facts["source_clis"]
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
            # 否则会把输入无效记成正式 fail 并触发复盘语义。判据在 `review_eligibility`（矩阵 #28）。
            eligibility = review_eligibility(distinct, implementation,
                                             imported_count=len(imported),
                                             declared_slots=len((launch or {}).get("slots") or []))
            if single_reviewer_facts is not None:
                # W2-3：人签接受已消费"人数不合格"——留痕降级只降人数；
                # 实施 CLI 重叠（异种门禁）不在降级范围，仍拒绝。
                eligibility_problems = [p for p in eligibility["problems"]
                                        if "人数不合格" not in str(p.get("reason"))]
            else:
                eligibility_problems = eligibility["problems"]
            if eligibility_problems:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": eligibility_problems,
                    "degraded": (launch or {}).get("degraded"),
                    "imported_reports": [{"slot": entry.get("slot"), "report_path": entry.get("report_path")}
                                         for entry in imported],
                    "exits": ["补足两个彼此不同、且均异于实施 CLI 的 reviewer 后**用 review-launch 重新发起新一轮**（已导入的坏报告留在原轮，不跨轮复用）",
                              "按设计稿 §6.5 的不可用处置：review-decide --unavailable <声明文件> 留痕，"
                              "复杂任务暂停或异常归档（不得据此判 pass）"],
                })
            verdict = "pass"
            facts = {"reviewer_clis": distinct}
            if single_reviewer_facts is not None:
                # W2-3：留痕降级进判定 facts（degraded + acceptance 引用）
                facts.update(single_reviewer_facts)
            # 主会话复核（2026-11-13）：报告是辅助证据；产生 verdict 前必须有本轮五轴复核。
            # 覆盖由「主会话复核 + 主会话采信的报告」合并：主会话能补足的轴不触发补轮，两者都未覆盖才交人。
            if not main_review_path:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "缺少主会话复核：reviewer 报告是辅助证据，不能只按报告判",
                    "round": int(round_no),
                    "exits": ["先 `review-decide --main-review-draft <file>` 生成待填骨架",
                              "填完五轴结论/依据/逐报告与逐 finding 复核后，用 --main-review <file> 重跑"],
                })
            main_payload = records.load_json(main_review_path)
            if main_payload is None:
                raise ReviewError("WF_PATH_INVALID",
                                  {"reason": "main review file missing", "path": main_review_path})
            previous_main = [entry for entry in reviews.get("main_reviews") or []
                             if isinstance(entry, dict)
                             and int(entry.get("round") or 0) == int(round_no)]
            if previous_main:
                # 修正复核只需提交新增/改动项：并集由入口算，漏写不会静默丢掉已核实 finding。
                main_payload = merge_main_findings(main_payload, previous_main[-1])
            main_findings = [item for item in all_findings(ctx, task)
                             if int(item.get("round") or 0) == int(round_no)]
            open_items = [item for item in open_findings(ctx, task)["blocking"]
                          if int(item.get("round") or 0) == int(round_no)]
            main_digest, main_cause, main_reason = records.file_digest_state(main_review_path)
            if main_cause:
                raise ReviewError("WF_PATH_INVALID",
                                  {"reason": "main review unreadable", "path": main_review_path,
                                   "cause": main_cause, "detail": main_reason})
            assertion_ids, changed_rules = assertion_index(ctx, task)
            main_record, main_problems, main_semantic = validate_main_review(
                main_payload, task_id=task.get("id"), round_no=round_no,
                imported=imported, findings=main_findings, open_blocking=open_items,
                axis_reports=report_facts.get("report_axes") or {},
                by=ctx.key(), file_digest=main_digest,
                assertion_ids=assertion_ids, changed_rules=changed_rules, task=task)
            if main_problems:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": main_problems,
                    "round": int(round_no),
                    "exits": ["按 problems 补齐五轴/逐报告/逐 finding 复核后重跑",
                              "用 --main-review-draft 重新生成骨架，避免手写字段"],
                })
            if main_semantic:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "problems": main_semantic,
                    "round": int(round_no),
                    "exits": ["修复后重跑 task-check，再 review-decide",
                              "无法修复时登记 judgment（kind=缺口/未核实, outcome=escalated）交人，任务暂停或异常归档；不要伪造 reviewer finding",
                              "无法覆盖就改判 uncovered，交人接受缺口"],
                })
            previous_main = [item for item in reviews.get("main_reviews") or []
                             if isinstance(item, dict) and int(item.get("round") or 0) == int(round_no)]
            same_digest = (bool(previous_main)
                           and previous_main[-1].get("file_digest") == main_record["file_digest"])
            if previous_main and not same_digest:
                previous_decision = latest_decision(task, round_no) or {}
                if previous_decision.get("verdict") in ("pass", "unavailable"):
                    raise ReviewError("WF_REVIEW_INVALID", {
                        "reason": "本轮已有 pass/unavailable 结论；复核不可替换",
                        "recorded": previous_main[-1].get("file_digest"),
                        "incoming": main_record["file_digest"],
                        "exits": ["要改结论请开新一轮（review-launch），不覆盖已判轮次的复核",
                                  "同一份复核重入会幂等，不会重复记录"],
                    })
                # 本轮此前是 fail（或尚未产生结论）：允许用修正后的复核重新判定，
                # 旧复核保留并标 supersedes。否则误报关闭后只能提交与事实矛盾的旧复核。
                resolved, _ambiguous, _unknown = disposition_keys(
                    list(reviews.get("dispositions") or []) + list(dispositions),
                    set(proposers))
                accepted = {key for key, decision in resolved.items()
                            if decision == "accepted"}
                revision_problems = main_review_revision_problems(
                    previous_main[-1], main_record.get("main_findings") or [], accepted, round_no)
                if revision_problems:
                    raise ReviewError("WF_REVIEW_INVALID", dict(
                        {"round": int(round_no), "problems": revision_problems,
                         "exits": ["在新复核里保留该 finding",
                                   "或先用 dispositions 的 slot=main 关闭/重分类"]},
                        **revision_problems[0]))
                main_record["supersedes"] = previous_main[-1].get("file_digest")
            if not same_digest:
                reviews["main_reviews"] = list(reviews.get("main_reviews") or []) + [main_record]
            # 本次复核刚产生的主会话 finding 也要成为可处置的提出者；proposers 在本轮
            # 复核读入前已从历史算出，不补这一步会让“同批登记关闭”误报未知 finding。
            for item in main_record.get("main_findings") or []:
                if isinstance(item, dict) and item.get("id"):
                    proposers.setdefault((int(round_no), "main", str(item["id"])), "main")
            # disposition 结构与其"关闭不得自证"（机制稿 §9.2、K4b）
            problems = dispositions_problems(dispositions, proposers)
            # A7/A9 相邻面：豁免匹配要带精确身份，读时把条目上的 round/slot 补进 lifted
            lifted = [dict(item, round=int(entry.get("round") or 0), slot=entry.get("slot"))
                      for entry in imported
                      for item in ((entry.get("broken_reference") or {}).get("lifted") or [])
                      if isinstance(item, dict)]
            # main_findings 的 broken-reference 声明也必须进人复核清单，不能借主会话自己的
            # assertion_ref 绕过 K4c。已登记的历史主会话复核也要覆盖（register-only 先记录、
            # 全量判定后核的场景）。
            main_broken = []
            for entry in reviews.get("main_reviews") or []:
                if not isinstance(entry, dict):
                    continue
                if entry.get("file_digest") == main_record.get("file_digest"):
                    continue
                entry_round = int(entry.get("round") or 0)
                for item in entry.get("main_findings") or []:
                    if (isinstance(item, dict)
                            and item.get("check_fix_kind") == "broken-reference"
                            and str(item.get("assertion_ref") or "").split("#", 1)[0] in changed_rules):
                        main_broken.append({"finding": item.get("id"),
                                            "assertion_ref": item.get("assertion_ref"),
                                            "rule": item.get("rule"), "round": entry_round,
                                            "slot": "main"})
            main_broken += [{"finding": item.get("id"), "assertion_ref": item.get("assertion_ref"),
                             "rule": item.get("rule"), "round": int(round_no), "slot": "main"}
                            for item in main_record.get("main_findings") or []
                            if isinstance(item, dict) and item.get("check_fix_kind") == "broken-reference"
                            and str(item.get("assertion_ref") or "").split("#", 1)[0] in changed_rules]
            lifted += main_broken
            problems = problems + broken_reference_problems(
                lifted, list(reviews.get("dispositions") or []) + list(dispositions))
            # 关闭证据：verified finding 的 accepted 必须带 evidence_refs；否则
            # "我核实了"与"误报关闭"会以自相矛盾的方式同时成立。已落盘与本次一并核。
            main_checks = {}
            for entry in reviews.get("main_reviews") or []:
                if not isinstance(entry, dict):
                    continue
                entry_round = int(entry.get("round") or 0)
                for item in entry.get("finding_review") or []:
                    if isinstance(item, dict) and item.get("slot") and item.get("finding_id"):
                        main_checks[(entry_round, str(item["slot"]),
                                     str(item["finding_id"]))] = item.get("check")
            # 同一 finding 取最新处置；当前证据先按当前 Check 解，历史关闭可回退历史 Check
            # （不按新 Check 重解旧证据）。缺证据的最新关闭仍会被下面拒绝。
            problems = problems + verified_closure_problems(
                list(reviews.get("dispositions") or []) + list(dispositions),
                main_record, proposers, round_no, main_checks=main_checks,
                evidence_check=lambda refs, check_id=None: evidence_ref_problems(
                    ctx, task, refs, check_id=check_id),
                historical_evidence_check=lambda refs: evidence_ref_problems(
                    ctx, task, refs, include_history=True),
                current_dispositions=dispositions)
            if problems:
                raise ReviewError("WF_REVIEW_INVALID",
                                  {"problems": problems,
                                   "proposers": [{"round": key[0], "slot": key[1],
                                                  "finding_id": key[2]}
                                                 for key in sorted(proposers)],
                                   "reported": [{"slot": entry.get("slot")} for entry in imported],
                                   "exits": ["按问题清单补 disposition 字段与复核人后重跑 review-decide",
                                             "把该 finding 标为不处置并在判断清单里写理由（不构成关闭）"]})
            # 本轮未关闭 blocking 先算出来：已确认的阻塞不能先被无关的覆盖缺口拦住。
            open_blocking_now = round_open_blocking(ctx, task, round_no, dispositions,
                                                    extra_main=main_record)
            if failures:
                facts = dict(facts, report_failures=failures)
            coverage_conflict = coverage_conflicts(main_record,
                                                   report_facts.get("report_axes") or {},
                                                   bool(scope_facts.get("narrowed")))
            if coverage_conflict and not open_blocking_now:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "narrowed materials: uncovered axis conflicts with a primary report's coverage",
                    "conflicts": coverage_conflict,
                    "round": int(round_no),
                    "exits": ["把该报告改为 partial/none，并在可采信的轴 sources 里列出槽位",
                              "或把该轴改成 pass/fail 并写清依据"],
                })
            if coverage_conflict and open_blocking_now:
                facts = dict(facts, coverage_conflicts=coverage_conflict)
            if open_blocking_now:
                facts = dict(facts, reason="审查未通过", open_blocking=open_blocking_now)
                if gap_decision is not None:
                    facts = dict(facts, gap_acceptance_ignored={
                        "round": int(round_no),
                        "axes": gap_decision.get("axes") if isinstance(gap_decision, dict) else None,
                        "reason": "本轮已有未关闭 blocking，直接记录 fail；缺口接受不影响本次判否",
                    })

            # 覆盖判定（2026-11-13，2026-11-20 采信修正）：主会话复核 + 采信的报告；两者都未覆盖才是缺口。
            coverage = merged_coverage(main_record,
                                       report_facts.get("report_axes") or {})
            coverage_facts = {"covered": coverage["covered"], "uncovered": coverage["uncovered"],
                              "all_uncovered": coverage["all_uncovered"],
                              "sources": coverage["sources"],
                              "adopted": coverage["adopted"],
                              "report_reliance": coverage["report_reliance"],
                              "main_review": {
                                  "file_digest": main_record["file_digest"],
                                  "axes": {axis: _axis_conclusion((main_record.get("axes") or {}).get(axis))
                                           for axis in REVIEW_AXES}}}
            report_axes = report_facts.get("report_axes") or {}
            no_coverage = [slot for slot, axes in report_axes.items()
                           if not any(_axis_conclusion(axis_entry) in ("pass", "fail")
                                      for axis_entry in (axes or {}).values())]
            if no_coverage and not coverage["all_uncovered"] and not open_blocking_now:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "有独立 reviewer 报告没有实际覆盖任何轴；两位独立审查不能由一位代偿",
                    "report_axes": report_axes, "slots_without_coverage": no_coverage,
                    "exits": ["让每份 reviewer 报告至少实际覆盖一个可核对轴并重新导入",
                              "审查环境确实不足时按不可用处置留痕，不得据此判 pass"],
                })
            if coverage["all_uncovered"] and not open_blocking_now:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "本轮主会话复核与 reviewer 报告都没有真正覆盖任何轴：这不构成审查结论",
                    "covered": coverage["covered"], "uncovered": coverage["uncovered"],
                    "report_axes": report_facts.get("report_axes") or {},
                    "exits": ["主会话补做五轴复核并写 pass/fail + 依据后重跑",
                              "审查环境确实不足时按设计稿 §6.5 的不可用处置留痕（不得据此判 pass）"],
                })
            if coverage["uncovered"] and not open_blocking_now:
                acceptance, gap_problems = gap_acceptance(gap_decision, coverage["uncovered"], round_no,
                                                          task_id=task.get("id"))
                if gap_problems:
                    raise ReviewError("WF_REVIEW_INVALID", {
                        "problems": gap_problems,
                        "uncovered": coverage["uncovered"],
                        "exits": ["把接受文件写成 {by, at, quote, source, round, axes}，"
                                  "axes 必须等于本轮未覆盖集合后重跑 review-decide"],
                    })
                if acceptance is None:
                    raise ReviewError("WF_SEMANTIC_DECISION", {
                        "reason": "本轮存在主会话复核与报告都未覆盖的轴：缺口不判 fail，但也不能当作审查通过",
                        "covered": coverage["covered"], "uncovered": coverage["uncovered"],
                        "sources": coverage["sources"],
                        "exits": ["主会话补做未覆盖轴的复核（推荐；能核实就写 pass/fail + 依据）",
                                  "人确认接受该覆盖缺口：写接受文件（by/at/quote/source + round + axes）"
                                  "后用 --gap-acceptance 重跑 review-decide"],
                    })
                reviews["coverage_acceptances"] = list(reviews.get("coverage_acceptances") or []) + [acceptance]
                coverage_facts["acceptance"] = acceptance
            elif gap_decision is not None and not open_blocking_now:
                raise ReviewError("WF_SEMANTIC_DECISION", {
                    "reason": "本轮没有未覆盖轴，但提供了缺口接受文件：不接受与本轮无关的确认",
                    "accepted_round": gap_decision.get("round"),
                    "accepted_axes": gap_decision.get("axes"),
                    "exits": ["去掉 --gap-acceptance 重跑", "确认该确认对应的是哪一轮后重新提交"],
                })
            facts["coverage"] = coverage_facts
            facts["main_review"] = {
                "file_digest": main_record["file_digest"],
                "report_review": main_record.get("report_review") or [],
                "finding_review": main_record.get("finding_review") or [],
            }

        if open_blocking_now:
            verdict = "fail"
        elif verdict == "pass":
            # ① 任务级一致性（2026-11-24）：pass 结论要求**全部**已知 blocking 已关闭——
            # 只拦本轮会让旧轮 fail 报告的未处置项被 pass 覆盖，再在归档门禁 C2 反弹，
            # 造出"提示可 finish、门禁必拦"的打架（dogfood 八轮审查的返工源）。
            # 本次 --plan 里一并给出的处置已计入（same probe），无需二次提交。
            _other_open = [item for item in round_open_blocking(ctx, task, round_no, dispositions,
                                                                extra_main=main_record,
                                                                only_round=False)
                           if int(item.get("round") or 0) != int(round_no)]
            if _other_open:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "pass 结论与已知事实矛盾：仍有他轮未关闭 blocking",
                    "open_blocking": _other_open,
                    "exits": ["在本次处置文件中补齐对这些 finding 的处置（round+slot 明确；"
                              "accepted 须 verified 证据，误报/重分类走 disputed 复核）后重跑 review-decide",
                              "仍有真实阻塞时保持 fail：修复 → 重查 → 再判",
                              "处置无法本地核实时登记 judgment（kind=缺口/未核实, outcome=escalated）交人"]})
            main_fail_axes = [axis for axis, value in ((main_record or {}).get("axes") or {}).items()
                              if _axis_conclusion(value) == "fail"]
            if main_fail_axes:
                raise ReviewError("WF_REVIEW_INVALID", {
                    "reason": "主会话复核仍把轴判 fail，不能据此产出 pass",
                    "fail_axes": main_fail_axes,
                    "round": int(round_no),
                    "exits": ["误报/重分类关闭后提交修正复核（同轮允许，旧复核保留并标 supersedes）",
                              "仍有真实阻塞时保持 fail，修复后重跑 Check 并发新轮"],
                })

        # A9：把本次登记的关闭**定到精确身份**上（round+slot）。此前只写 finding_id 的
        # 记录靠"唯一命中"解析；一旦他轮出现同名问题就会变成歧义，所以写入时就固化。
        resolved_keys, _ambiguous_keys, _unknown_keys = disposition_keys(
            dispositions, set(proposers))
        for item in dispositions:
            if item.get("decision") != "accepted" or (item.get("round") and item.get("slot")):
                continue
            matches = [key for key, decision in resolved_keys.items()
                       if decision == "accepted" and key[2] == str(item.get("finding_id"))]
            if len(matches) == 1:
                item["round"], item["slot"] = matches[0][0], matches[0][1]
        # ⑥：`facts.not_closing` 如实回报**未关闭**项（closed 集不改，仍只收 accepted；B5）
        not_closing = [{"finding_id": item.get("finding_id"), "decision": item.get("decision")}
                       for item in dispositions
                       if isinstance(item, dict) and item.get("decision") != "accepted"]
        if not_closing:
            facts = dict(facts, not_closing=not_closing)
        # ⑥ 逐轮决策事实（append-only）：`rounds[]` 为空时先把按 `result` 推断的一条**落盘**，再追加本轮
        rounds = inferred_rounds(reviews)
        rounds.append({"round": int(round_no), "verdict": verdict,
                       "check_id": (task.get("check") or {}).get("id"),
                       "decided_at": records.now_str()})
        reviews["rounds"] = rounds
        facts = dict(facts, scope=scope_facts)
        if material_state["state"] != "fixed":
            # 身份强度如实上报：判定通过时材料是否有可核身份，不能靠调用方自己翻目录。
            weak = material_state["state"] in ("legacy", "legacy_adopted")
            drift = material_state["state"] == "drift"
            facts = dict(
                facts, materials_state=material_state["state"],
                materials_note=("材料没有可核身份（按现场字节采纳，未证明未被改动；"
                                "身份只覆盖 manifest 列出的文件）；"
                                "要可核身份则删材料内容**和** manifest 后重跑 review-context" if weak else
                                "材料在物化后被改动；本轮的结论按**记录给出的身份**成立"
                                "（纯旧记录没有身份时见 unbound），现场字节只作参考"
                                "（要恢复可核身份就放回原字节）" if drift else
                                "本轮没有可用材料包（目录不在或不完整）：报告读到的材料已不可还原"))
        # 判定引用的材料身份：本轮 manifest（轮次材料一经物化即固定）的摘要——
        # "判定通过时 reviewer 读到的是哪份 check.json/日志"由此可还原，不靠时间推断。
        # `state` 同时如实暴露身份强度：legacy=无身份记录（按现场采纳）、unmaterialized=无材料。
        _manifest = material_state["manifest"]
        # 判定引用的材料身份取**报告绑定的那条**（结论对它成立），当前身份另列对账：
        # 旧实现在这里只记当前 manifest，重物化后结论会冒充"审的是新那份"。
        _bindings = sorted({(entry.get("materials") or {}).get("identity") for entry in imported
                            if (entry.get("materials") or {}).get("identity")})
        _current = materials_identity(_manifest)
        _materials_identity = {"state": material_state["state"],
                               # 老报告没绑身份（`unbound`）时只能记当前值，别留空数组
                               "identity": ((_bindings[0] if len(_bindings) == 1 else _bindings)
                                            or _current),
                               "unbound": any(not (entry.get("materials") or {}).get("identity")
                                              or (entry.get("materials") or {}).get("unbound")
                                              for entry in imported),
                               "check_id": (_manifest or {}).get("check_id")}
        if _current and _bindings and _current not in _bindings:
            _materials_identity["current"] = _current
        result = {
            "verdict": verdict,
            "round": int(round_no),
            "scope": scope_facts,
            "reviewer_clis": distinct,
            "check_id": (task.get("check") or {}).get("id"),
            "anchor": {"check_id": (task.get("check") or {}).get("id"), "check_anchor": anchor},
            "imported": [{"slot": entry.get("slot"), "report_digest": entry.get("report_digest")} for entry in imported],
            "facts": facts,
            # 降级事实取**实际发生的**来源：launch 声明（人一开始就只要一位）或本轮人签接受
            # （声明了多位但只到一份、其余确认不可用）。只认 launch 会让后者的 result 看不出降级
            # 而 facts 里有——同一事实两个投影不一致（六轮二轮审查 B1 收尾）。
            "degraded": ((single_reviewer_facts or {}).get("degraded")
                         or (launch or {}).get("degraded")),
            "materials": _materials_identity,
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
        inputs = {"task": task.get("id"), "round": int(round_no), "verdict": verdict,
                  "main_review_digest": (main_record or {}).get("file_digest")}
        task, action = tasks_mod._start_task_action(
            ctx, path, task, "review.decide", holder, inputs, ["derive_verdict", "record_dispositions"]
        )
        task, assertion = tasks_mod._finish_task_action(
            ctx, path, task, "review.decide", holder, inputs, action,
            evidence_refs=[entry.get("report_path") for entry in imported if entry.get("report_path")],
        )
    from . import codes

    # 三种结论各有码（六轮复核 B2）：pass / 输入成立但不通过（fail）/ 环境不足。
    # 此前 fail 与"输入不成立"共用 `WF_REVIEW_INVALID`，下游按码分流会把正当结论当坏输入。
    code = {"pass": "WF_OK", "fail": "WF_REVIEW_FAILED",
            "unavailable": "WF_REVIEW_UNAVAILABLE"}.get(verdict, "WF_REVIEW_INVALID")
    return codes.result(
        code,
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id")),
        next_=("verdict=pass（全部已知 blocking 已关闭）后由人调用 finish（wf-finish）" if verdict == "pass" else
               ("按异常退出处置：暂停，或经人重新分级后按轻量完成" if verdict == "unavailable" else
                "有未关闭 blocking：在批准范围内修复→重跑 task-check→重新发起；"
                "误报/重分类经复核登记 accepted 后可重判")),
        facts={"result": result, "reviewer_clis": result.get("reviewer_clis"),
               "control_assertion": assertion},
    )


def all_findings(ctx, task):
    """报告里的**全部** findings（含已处置），`unaddressed` 只是它的子集。

    骨架需要"全部"（v42 §5.1 的 `findings[]` + 单列 `closures[]`）；把只含未处置的集合
    当成全部，会让"已关闭"的缺陷从清单里消失，也让两个字段变成同一份东西。
    """
    reviews = task.get("reviews") or {}
    found = []
    for entry in reviews.get("imported") or []:
        if not isinstance(entry, dict):
            continue
        rel = entry.get("report_path")
        if not rel:
            continue
        payload, cause, _reason = read_imported_report(ctx, entry)
        if cause:
            continue
        round_no = int(entry.get("round") or 0)
        for finding in payload.get("findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                found.append({"id": finding.get("id"), "severity": finding.get("severity"),
                              "class": finding.get("class"), "slot": entry.get("slot"),
                              "round": round_no,
                              "assertion_ref": finding.get("assertion_ref"),
                              "_key": finding_key(round_no, entry.get("slot"), finding["id"])})
    latest_main = {}
    for entry in reviews.get("main_reviews") or []:
        if isinstance(entry, dict):
            latest_main[int(entry.get("round") or 0)] = entry
    for round_no, entry in latest_main.items():
        for finding in entry.get("main_findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                found.append({"id": finding.get("id"), "severity": finding.get("severity"),
                              "class": finding.get("class"), "slot": "main",
                              "round": round_no,
                              "assertion_ref": finding.get("assertion_ref"),
                              "_key": finding_key(round_no, "main", finding["id"])})
    # 关闭与 `open_findings` 同一判据：只把 accepted **且**已核实（或后续轮核实）的算关闭，
    # 不能只凭 accepted 就把 unable 项标成 closed。
    closers = {finding_key(item.get("round"), item.get("slot"), item.get("finding_id"))
               for item in open_findings(ctx, task)["closed"]}
    for item in found:
        item["closed"] = item.pop("_key") in closers
    return found
