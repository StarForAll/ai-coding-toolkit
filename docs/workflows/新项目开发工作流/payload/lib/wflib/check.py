"""check.py — Check 固定五步与检查锚点（机制稿 §3.2、§3.5）。"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import uuid

from . import config as config_mod, fingerprint, records, scope
from .paths import join


class CheckError(Exception):
    def __init__(self, code, facts=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}


# --------------------------------------------------------------------------
# 检查对象与锚点
# --------------------------------------------------------------------------


def object_paths(ctx, task):
    """本次 Check 对象的实际触碰路径集合（e 类）∪ 规则输入。"""
    from . import tasks as tasks_mod

    receipts = tasks_mod.task_receipts(ctx.root)
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    paths = set(classified["buckets"]["e"])
    for entry in task.get("curation") or []:
        if entry.get("released"):
            continue
        if entry.get("path"):
            paths.add(entry["path"])
    for fixed in (".wf/baseline.md", ".wf/project-config.json"):
        if os.path.exists(join(ctx.root, fixed)):
            paths.add(fixed)
    return sorted(paths)


def spec_versions(ctx, task):
    """当前命中或策展的 spec（机制稿 §3.5）：新增的命中规则必须进入锚点输入。"""
    from . import spec as spec_mod
    from . import tasks as tasks_mod

    paths = set()
    for entry in task.get("curation") or []:
        if entry.get("released") or not entry.get("path"):
            continue
        paths.add(entry["path"])
    classified = scope.classify_candidates(ctx.root, task, receipts=tasks_mod.task_receipts(ctx.root))
    candidates = sorted(set(classified["buckets"]["e"]) |
                        {item for item in (".wf/baseline.md", ".wf/project-config.json")
                         if os.path.exists(join(ctx.root, item))})
    matched, _unparsed = spec_mod.match(ctx.root, candidates)
    for entry in matched:
        paths.add(entry["path"])
    versions = [{"path": path, "digest": records.file_digest(join(ctx.root, path))}
                for path in sorted(paths)]
    return sorted(versions, key=lambda item: str(item["path"]).encode("utf-8"))


def object_content_digest(ctx, task):
    return fingerprint.content_digest(fingerprint.items(ctx.root, object_paths(ctx, task)))


def anchor_parts(ctx, task, *, check=None):
    from . import tasks as tasks_mod

    plan = task.get("plan") or {}
    entry = task.get("entry_snapshot") or {}
    paths = object_paths(ctx, task)
    return {
        "plan_version": tasks_mod.normalized_plan_version(task),
        "entry_snapshot_digest": fingerprint.snapshot_digest(entry) if entry else None,
        "touch_paths_digest": fingerprint.touch_paths_digest(entry.get("touch_paths") or []),
        "paths_digest": fingerprint.paths_digest(paths),
        "content_digest": fingerprint.content_digest(fingerprint.items(ctx.root, paths)),
        "acceptance_digest": plan.get("acceptance_digest"),
        "spec_versions": spec_versions(ctx, task),
        "baseline_digest": records.file_digest(join(ctx.root, ".wf/baseline.md")),
        "config_digest": records.file_digest(join(ctx.root, ".wf/project-config.json")),
        "workflow_snapshot_digest": None,
    }


def current_anchor(ctx, task):
    parts = anchor_parts(ctx, task)
    missing = [key for key, value in parts.items() if value is None and key not in ("entry_snapshot_digest",
                                                                                   "workflow_snapshot_digest")]
    if missing:
        raise CheckError("WF_APPROVAL_MISSING", {"missing_anchor_inputs": missing})
    return fingerprint.check_anchor(parts), parts


# --------------------------------------------------------------------------
# 步骤 ②：verification.resolve(check)
# --------------------------------------------------------------------------


def _argv_ready(root, invocation):
    argv = invocation.get("argv") or []
    if not argv:
        return False, "empty argv"
    program = argv[0]
    if os.sep in program:
        target = program if os.path.isabs(program) else join(root, program)
        if not os.path.exists(target):
            return False, f"program missing: {program}"
        return True, None
    if shutil.which(program) is None and not os.path.exists(join(root, program)):
        return False, f"program not found on PATH: {program}"
    return True, None


def resolve_verifications(ctx, task, point):
    """返回 [{id, ready, facts}]；只读，不执行。"""
    problems = []
    declared = (task.get("plan") or {}).get("verifications") or []
    for verification in declared:
        if verification.get("consume_at") != point:
            continue
        invocation = verification.get("invocation") or {}
        if invocation.get("kind") == "manual":
            continue
        ready, reason = _argv_ready(ctx.root, invocation)
        cwd = verification.get("cwd") or "."
        if cwd != ".":
            try:
                target = join(ctx.root, cwd)
            except Exception:
                target = None
            if not os.path.isdir(target):
                ready = False
                reason = f"cwd missing: {cwd}"
        if not ready:
            problems.append({"verification_id": verification.get("id"), "reason": reason})
    return problems


# --------------------------------------------------------------------------
# 步骤 ③：执行验证并写 commands/acceptance_results
# --------------------------------------------------------------------------


SECRET_PATTERNS = (
    # Authorization: Bearer <值>（不设长度门槛，任意取值都遮罩）
    re.compile(r"(?i)\bBearer\s+[^\s\"',;]+"),
    # --token/--api-key/--access-token/--client-secret 等分离或等号/冒号写法（文本形态）
    re.compile(r"(?i)(--?[a-z0-9_.-]*(?:token|secret|password|passwd|api[_-]?key)[a-z0-9_.-]*)"
               r"(\s*[=:]\s*|\s+)\S+"),
    # key: value / key=value
    re.compile(r"(?i)\b([a-z0-9_.-]*(?:api[_-]?key|token|secret|password|passwd)[a-z0-9_.-]*)\b\s*[:=]\s*\S+"),
    # JSON/字典内嵌：键名可能带引号、值也可能带引号（{"token":"x"}、{'access_token': "y"}）
    re.compile(r"(?i)([\"']?[a-z0-9_.-]*(?:api[_-]?key|token|secret|password|passwd)[a-z0-9_.-]*[\"']?"
               r"\s*:\s*)([\"'])[^\"']*\2"),           # 带引号的值允许含空格/逗号
    re.compile(r"(?i)([\"']?[a-z0-9_.-]*(?:api[_-]?key|token|secret|password|passwd)[a-z0-9_.-]*[\"']?"
               r"\s*:\s*)(?![\"'])[^\s,}]+"),           # 不带引号的单词值
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
)

SECRET_HEAD = re.compile(r"(?i)^(--?[a-z0-9_.-]*(?:token|secret|password|passwd|api[_-]?key)[a-z0-9_.-]*)"
                         r"(\s*[=:]\s*|\s+)")


NON_SECRET_KEYS = frozenset({
    "tokenizer", "tokenizers", "token_type", "token_types", "tokens",
    "token_count", "token_limit", "token_budget", "token_size",
    "token_type_ids", "token_type_id", "token_ids", "input_ids",
    "max_tokens", "min_tokens", "max_token", "min_token",
})

KEY_PREFIX = re.compile(r"""(?i)^[\s{\[,"'`]*([A-Za-z0-9_.\-]+)["']?\s*[:=]\s*""")


def _non_secret_key(raw):
    """键名含 token/secret 子串但确实是计数/分词器的，不遮（避免 tokenizer → ***）。"""
    match = KEY_PREFIX.match(raw)
    if not match:
        return False
    key = match.group(1).lower()
    if key in NON_SECRET_KEYS:
        return True
    return key.endswith(("_count", "_limit", "_budget", "_size", "_type"))


def redact_text(text):
    """文本级遮罩：日志、facts 摘要、命令回显都走这一处，避免两套规则不一致。"""
    def mask(match):
        raw = match.group(0)
        if _non_secret_key(raw):
            return raw
        head = SECRET_HEAD.match(raw)
        if head:
            return head.group(0) + "***"
        head = re.match(r"""(?i)[\w\- "'{}\[\],:]*?[:=]\s*""", raw)
        if head:
            return head.group(0) + "***"
        return "***"

    out = text
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(mask, out)
    return out


# 兼容旧名：所有调用点都走同一实现
redact_secrets = redact_text


SEPARATED_FLAGS = ("--token", "--secret", "--password", "--api-key", "--apikey",
                   "--access-token", "--client-secret", "--auth-token")


def redact_argv(argv):
    """命令参数脱敏：分离写法按位置判定，其余交给同一份文本规则。"""
    masked = []
    skip_next = False
    for index, item in enumerate(argv):
        text = str(item)
        if skip_next:
            masked.append("***")
            skip_next = False
            continue
        if text in SEPARATED_FLAGS and index + 1 < len(argv):
            masked.append(text)
            skip_next = True
            continue
        masked.append(redact_text(text))
    return masked


# --------------------------------------------------------------------------
# Check 结果的结构复核：生成端与门禁端共用同一实现（机制稿 §3.5、§11.2）
# --------------------------------------------------------------------------

def validate_check_result(task, check):
    """核 Check 记录是否构成「真正做过的检查」。返回问题列表（空 = 通过）。

    只核结构事实：必要集合、唯一性、调用匹配、结束状态、验收覆盖、内部双轴。
    """
    plan = task.get("plan") or {}
    declared = {}
    for entry in plan.get("verifications") or []:
        if isinstance(entry, dict) and entry.get("id"):
            declared[entry["id"]] = entry
    required = {vid for vid, entry in declared.items() if entry.get("required", True) is not False}

    problems = []
    if check.get("result") != "pass":
        problems.append({"field": "result", "reason": "not pass", "value": check.get("result")})
    if not (check.get("anchor") or {}).get("rule_version"):
        problems.append({"field": "anchor.rule_version", "reason": "missing"})

    commands = check.get("commands")
    if not isinstance(commands, list) or not commands:
        problems.append({"field": "commands", "reason": "missing or empty"})
        commands = []

    seen = {}
    for entry in commands:
        if not isinstance(entry, dict):
            problems.append({"field": "commands", "reason": "entry is not an object"})
            continue
        vid = entry.get("verification_id")
        if vid not in declared:
            problems.append({"field": "commands", "reason": "unknown verification_id", "verification_id": vid})
            continue
        if vid in seen:
            problems.append({"field": "commands", "reason": "duplicate verification_id", "verification_id": vid})
        seen[vid] = entry

        definition = declared[vid]
        invocation = definition.get("invocation") or {}
        recorded = entry.get("invocation") or {}
        if invocation.get("kind") != recorded.get("kind"):
            problems.append({"field": f"commands[{vid}].invocation",
                             "reason": "invocation kind does not match the approved verification",
                             "approved": invocation.get("kind"), "recorded": recorded.get("kind")})
        elif invocation.get("kind") == "argv":
            approved_argv = redact_argv(list(invocation.get("argv") or []))
            recorded_argv = redact_argv(list(recorded.get("argv") or []))
            if approved_argv != recorded_argv:
                # 调用被替换即证明本次没有按批准的验证执行
                problems.append({"field": f"commands[{vid}].invocation",
                                 "reason": "recorded argv differs from the approved invocation",
                                 "approved": approved_argv, "recorded": recorded_argv})
        if entry.get("status") != "passed":
            problems.append({"field": f"commands[{vid}].status", "reason": "not passed",
                             "status": entry.get("status")})
        if invocation.get("kind") == "argv":
            if entry.get("exit_code") != 0:
                problems.append({"field": f"commands[{vid}].exit_code", "reason": "non-zero or missing",
                                 "exit_code": entry.get("exit_code")})
            if not entry.get("ended_at"):
                problems.append({"field": f"commands[{vid}].ended_at", "reason": "missing"})
        elif invocation.get("kind") == "manual":
            # manual 项没有执行痕迹，唯一的证据是人判 Decision：必须存在、覆盖本项、结论为 passed
            decision = entry.get("decision")
            if not isinstance(decision, dict) or not decision:
                problems.append({"field": f"commands[{vid}].decision",
                                 "reason": "manual verification without a decision"})
            else:
                if decision.get("choice") != "passed":
                    problems.append({"field": f"commands[{vid}].decision",
                                     "reason": "manual decision is not 'passed'",
                                     "choice": decision.get("choice")})
                if not _decision_covers(decision, str(vid), plan, plan.get("version")):
                    problems.append({"field": f"commands[{vid}].decision",
                                     "reason": "manual decision does not cover this verification",
                                     "subject": decision.get("subject"),
                                     "plan_version": decision.get("plan_version")})

    missing_required = sorted(required - set(seen))
    if missing_required:
        problems.append({"field": "commands", "reason": "required verification not executed",
                         "missing": missing_required})

    acceptance = plan.get("acceptance") or []
    results = check.get("acceptance_results")
    if not isinstance(results, list) or not results:
        problems.append({"field": "acceptance_results", "reason": "missing or empty"})
        results = []
    by_id = {}
    for item in results:
        if not isinstance(item, dict):
            problems.append({"field": "acceptance_results", "reason": "entry is not an object"})
            continue
        acceptance_id = item.get("acceptance_id") or item.get("id")
        if acceptance_id in by_id:
            problems.append({"field": "acceptance_results", "reason": "duplicate acceptance result",
                             "acceptance_id": acceptance_id})
        by_id[acceptance_id] = item
    for item in acceptance:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        result = by_id.get(item["id"])
        if result is None:
            problems.append({"field": "acceptance_results", "reason": "acceptance item has no result",
                             "acceptance_id": item["id"]})
        elif result.get("conclusion") != "passed":
            problems.append({"field": f"acceptance_results[{item['id']}]", "reason": "not passed",
                             "conclusion": result.get("conclusion")})
    known_acceptance = {item.get("id") for item in acceptance if isinstance(item, dict)}
    unknown = sorted(str(key) for key in by_id if key not in known_acceptance)
    if unknown:
        problems.append({"field": "acceptance_results", "reason": "unknown acceptance_id", "ids": unknown})

    review = check.get("internal_review") or {}
    for axis in ("standard", "requirement"):
        entry = review.get(axis) if isinstance(review, dict) else None
        if not isinstance(entry, dict) or entry.get("conclusion") != "pass" or not entry.get("basis"):
            problems.append({"field": f"internal_review.{axis}", "reason": "missing, not pass, or lacks basis"})
    return problems


def _run_argv(ctx, task, verification, log_dir):
    invocation = verification.get("invocation") or {}
    argv = list(invocation.get("argv") or [])
    cwd = verification.get("cwd") or "."
    workdir = ctx.root if cwd == "." else join(ctx.root, cwd)
    started = records.now_str()
    try:
        result = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, check=False)
        exit_code = result.returncode
        output = (result.stdout or "") + (result.stderr or "")
        summary = output.strip().splitlines()[-1] if output.strip() else ""
    except OSError as exc:
        exit_code = None
        summary = f"spawn failed: {exc}"
    ended = records.now_str()
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{verification.get('id')}.log")
    # 日志与 facts 都按秘密边界遮罩；命令参数一并过一遍（argv 可能带内联值）
    masked_argv = redact_argv(argv)
    summary = redact_text(summary)
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(f"argv: {records.canonical(masked_argv)}\ncwd: {cwd}\nexit_code: {exit_code}\n\n")
        handle.write(summary + "\n")
    status = "passed" if exit_code == 0 else ("not_run" if exit_code is None else "failed")
    return {
        "verification_id": verification.get("id"),
        "invocation": dict(invocation, argv=masked_argv) if invocation.get("argv") else invocation,
        "cwd": cwd,
        "input_refs": verification.get("input_refs") or [],
        "required": bool(verification.get("required", True)),
        "started_at": started,
        "ended_at": ended,
        "exit_code": exit_code,
        "status": status,
        "summary": summary,
        "evidence_ref": os.path.relpath(log_path, str(ctx.root)).replace(os.sep, "/"),
    }


def _manual_command(verification, decisions, anchor, plan, plan_version):
    """manual 验证：只接受明确 choice=passed 的人判 Decision，并把本次锚点核绑到记录。"""
    verification_id = verification.get("id")
    matches = [decision for decision in decisions or []
               if _decision_covers(decision, verification_id, plan, plan_version)]
    entry = {
        "verification_id": verification_id,
        "invocation": verification.get("invocation"),
        "cwd": verification.get("cwd") or ".",
        "input_refs": verification.get("input_refs") or [],
        "required": bool(verification.get("required", True)),
        "started_at": records.now_str(),
        "ended_at": records.now_str(),
        "exit_code": None,
        "status": "not_run",
        "summary": "manual verification without a passed human decision",
        "evidence_ref": None,
        "anchor": {"check_anchor": anchor, "plan_version": plan_version},
    }
    if not matches:
        return entry
    decision = matches[-1]
    choice = decision.get("choice")
    entry["decision"] = decision
    entry["evidence_ref"] = decision.get("source")
    entry["summary"] = f"manual decision: {choice}"
    if choice == "passed":
        entry["status"] = "passed"
    elif choice == "failed":
        entry["status"] = "failed"
    else:
        entry["status"] = "not_run"
        entry["summary"] = f"manual decision choice is {choice!r}; only 'passed' can satisfy a manual verification"
    return entry


EXTERNAL_CHECKED_CHOICES = ("已核对无影响", "核对无影响", "checked", "no-impact")


def _external_touches_task(item, task):
    """该外部提交是否触及本任务批准触碰面（未触及的不构成待决项）。"""
    from . import paths as paths_mod

    touch = (task.get("plan") or {}).get("touch_paths") or []
    for path in (item or {}).get("paths") or []:
        for pattern in touch:
            if paths_mod.match_path(pattern, path):
                return True
    return False


def _external_checked(item, decisions, task):
    """是否已有"已核对无影响"的人判：按提交 OID 精确匹配，或用 external-changes 整体声明。"""
    commit = (item or {}).get("commit")
    for decision in decisions or []:
        if decision.get("choice") not in EXTERNAL_CHECKED_CHOICES:
            continue
        subject = str(decision.get("subject") or "")
        if "external-changes" in subject:
            return True
        if commit and commit in subject:
            return True
    return False


def _acceptance_results(ctx, task, commands, decisions, anchor):
    plan = task.get("plan") or {}
    plan_version = plan.get("version")
    acceptance = plan.get("acceptance") or []
    results = []
    for item in acceptance:
        verification_ids = item.get("verification_ids") or []
        if verification_ids:
            relevant = [command for command in commands if command["verification_id"] in verification_ids]
            statuses = [command["status"] for command in relevant]
            if not relevant:
                conclusion = "pending"
            elif any(status in ("failed", "not_run") for status in statuses):
                conclusion = "failed" if "failed" in statuses else "pending"
            else:
                conclusion = "passed"
            results.append(
                {
                    "acceptance_id": item.get("id"),
                    "verification_ids": verification_ids,
                    "decision": None,
                    "conclusion": conclusion,
                    "evidence_refs": [command.get("evidence_ref") for command in relevant if command.get("evidence_ref")],
                }
            )
            continue
        matches = [
            decision
            for decision in decisions or []
            if _decision_covers(decision, str(item.get("id")), plan, plan_version)
            and decision.get("choice") in ("passed", "failed", "pending")
        ]
        if matches:
            decision = matches[-1]
            results.append(
                {
                    "acceptance_id": item.get("id"),
                    "verification_ids": [],
                    "decision": decision,
                    "conclusion": decision.get("choice"),
                    "evidence_refs": [decision.get("source")],
                    "anchor": {"check_anchor": anchor, "plan_version": plan_version},
                }
            )
        else:
            results.append(
                {
                    "acceptance_id": item.get("id"),
                    "verification_ids": [],
                    "decision": None,
                    "conclusion": "pending",
                    "evidence_refs": [],
                }
            )
    return results


def _parse_review_notes(path):
    if not path:
        return None, {"reason": "internal review notes missing"}
    try:
        data = records.load_json(path)
    except records.RecordInvalid as exc:
        return None, {"reason": f"review notes invalid: {exc}"}
    if not isinstance(data, dict):
        return None, {"reason": "review notes must be a JSON object"}
    standard = data.get("standard")
    requirement = data.get("requirement")
    allowed = ("pass", "fail", "undecided")
    if not isinstance(standard, dict) or standard.get("conclusion") not in allowed:
        return None, {"reason": "standard axis conclusion missing or invalid", "conclusion": (standard or {}).get("conclusion")}
    if not isinstance(requirement, dict) or requirement.get("conclusion") not in allowed:
        return None, {"reason": "requirement axis conclusion missing or invalid",
                      "conclusion": (requirement or {}).get("conclusion")}
    return {
        "standard": standard,
        "requirement": requirement,
        "tdd_evidence": data.get("tdd_evidence"),
    }, None


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------


def _decision_covers(decision, subject_id, plan, plan_version):
    """决定必须以「整词」覆盖目标 id，并绑定当前规划（显式版本或批准对象摘要）。"""
    tokens = [token for token in re.split(r"[\s,;、|]+", str(decision.get("subject") or "")) if token]
    if subject_id not in tokens:
        return False
    declared = decision.get("plan_version")
    if declared is not None:
        return str(declared) == str(plan_version)
    approval = (plan.get("approval") or {})
    digest = approval.get("object_digest")
    return bool(digest) and decision.get("object_digest") == digest


def _spec_coverage(ctx, task, decisions):
    """按「命中 ∪ 策展」逐条核实：未命中策展、到期、extracted/空都要人处置（设计稿 §6.2、§6.4）。"""
    from . import spec as spec_mod

    paths = object_paths(ctx, task)
    matched, unparsed = spec_mod.match(ctx.root, paths)
    matched_paths = [entry["path"] for entry in matched]
    curated = [entry.get("path") for entry in task.get("curation") or []
               if not entry.get("released") and entry.get("path")]
    missing = [path for path in matched_paths if path not in curated]

    metadata = {}
    for entry in matched:
        metadata[entry["path"]] = entry["metadata"]
    for path in curated:
        if path in metadata:
            continue
        loaded = spec_mod.load_spec(ctx.root, path)
        metadata[path] = (loaded or {}).get("metadata") or {}

    config_data, config_problems = config_mod.load_project_config(ctx.root, allow_missing=True)
    days, period_problem = config_mod.value_of(config_data, config_problems, "spec_verify_days")
    period_problems = [period_problem] if period_problem else []
    config_problems = [item.get("message") if isinstance(item, dict) else item for item in config_problems]
    if days is None:
        # 周期不可用时仍要能列出未核实/到期候选：按发行缺省计算，但结果标记为待核
        days = config_mod.DEFAULTS["spec_verify_days"]
    today = records.utc_now().date()
    needs = []
    for path in sorted(set(matched_paths) | set(curated)):
        verified = (metadata.get(path) or {}).get("verified_at")
        if verified in (None, "extracted"):
            needs.append({"path": path, "reason": "unverified" if verified is None else "extracted"})
            continue
        try:
            stamp = datetime.date.fromisoformat(str(verified))
        except ValueError:
            needs.append({"path": path, "reason": "unparsable-date", "verified_at": verified})
            continue
        if (stamp - today).days > 0:
            needs.append({"path": path, "reason": "future-date", "verified_at": str(verified)})
            continue
        if (today - stamp).days > days:
            needs.append({"path": path, "reason": "expired", "verified_at": str(verified), "days": days})

    plan = task.get("plan") or {}
    version = plan.get("version")
    unresolved = [item for item in needs
                  if not any(_decision_covers(decision, item["path"], plan, version)
                             and decision.get("choice") == "passed" for decision in decisions or [])]
    decisions_used = [decision for decision in decisions or []
                      if any(_decision_covers(decision, item["path"], plan, version)
                             and decision.get("choice") == "passed" for item in needs)]
    path_problems = [item for item in unparsed if item.get("kind") == "path"]
    return {"matched": matched_paths, "curated": sorted(set(curated)),
            "period_days": days, "period_problems": period_problems,
            "missing_curation": missing, "needs": needs, "unresolved": unresolved,
            "unparsed": [item for item in unparsed if item.get("kind") != "path"],
            "path_problems": path_problems, "config_problems": config_problems,
            "evidence": [{"subject": decision.get("subject"), "at": decision.get("at"),
                          "choice": decision.get("choice")} for decision in decisions_used]}


TDD_EVIDENCE_FIELDS = ("assertion", "red_command_ref", "red_reason", "green_command_ref", "properties")


def _command_index(commands):
    index = {}
    for command in commands or []:
        for key in (command.get("verification_id"), command.get("evidence_ref")):
            if key:
                index.setdefault(str(key), []).append(command)
    return index


def tdd_evidence_problem(evidence, commands, history_commands=None):
    """TDD 证据结构核对（机制稿 §3.5）：五段齐全；绿引用当前通过项，红引用历史失败项，两者不同。"""
    if not isinstance(evidence, dict):
        return {"reason": "tdd_evidence must be an object"}
    missing = [field for field in TDD_EVIDENCE_FIELDS if not str(evidence.get(field) or "").strip()]
    if missing:
        return {"missing": missing}
    red_ref = str(evidence.get("red_command_ref"))
    green_ref = str(evidence.get("green_command_ref"))
    if red_ref == green_ref:
        return {"reason": "red and green must reference different runs", "ref": red_ref}
    current = _command_index(commands)
    history = _command_index(history_commands)
    green = [item for item in current.get(green_ref) or [] if item.get("status") == "passed"]
    if not green:
        return {"reason": "green run not found among current passed commands", "green": green_ref}
    red = [item for item in history.get(red_ref) or [] if item.get("status") == "failed"]
    if not red:
        return {"reason": "red run not found among historical failed commands", "red": red_ref,
                "known_history_refs": sorted(history)}
    return None


def run_check(ctx, task, decisions, review_notes_path):
    """执行固定五步；返回 (check_record, code, facts)。"""
    task_dir = _task_dir(ctx, task)
    # ① 范围核对
    receipts = _receipts(ctx)
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    external, external_findings = scope.external_changes(ctx.root, task)
    buckets = classified["buckets"]
    scope_facts = {
        "candidates": len(classified["candidates"]),
        "buckets": {key: buckets[key] for key in ("a", "b", "c", "d", "e", "f")},
        "external_changes": external_findings,
        "external_pending": len(external_findings or []),
    }
    if buckets["f"]:
        raise CheckError("WF_SCOPE_VIOLATION", dict(scope_facts, out_of_scope=buckets["f"]))
    if buckets["c"]:
        raise CheckError("WF_WORKSPACE_UNRESOLVED", dict(scope_facts, other_tasks=buckets["c"]))
    pending_external = [item for item in (external_findings or [])
                        if _external_touches_task(item, task)
                        and not _external_checked(item, decisions, task)]
    if pending_external:
        raise CheckError("WF_SEMANTIC_DECISION",
                         dict(scope_facts, external_pending_unchecked=pending_external,
                              exits=["逐条核对影响并给出『已核对无影响』决定",
                                     "确认属本任务改动则用 task-attribute 裁决归属",
                                     "影响验收则回 Plan，影响检查则重检"]))
    if buckets.get("d"):
        # 归属语义存疑：交人裁决，不当通过（机制稿 §3.5）
        raise CheckError("WF_SCOPE_UNRESOLVED", dict(scope_facts, ambiguous_ownership=buckets["d"]))
    conflicts = scope.cross_task_conflicts(ctx.root, task)
    if conflicts:
        # 同一路径被另一个任务显式归属：双重认领，不能由脚本判定归谁
        raise CheckError("WF_SCOPE_UNRESOLVED", dict(scope_facts, cross_task_claims=conflicts))
    governance_violations, governance_state = scope.declaration_violations(
        buckets["e"], classified["touch_paths"], ctx.root
    )
    if governance_state.get("unavailable"):
        raise CheckError(
            "WF_SEMANTIC_DECISION",
            dict(scope_facts, governance_unavailable=governance_state.get("problems")),
        )
    if governance_violations:
        raise CheckError("WF_SCOPE_UNRESOLVED", dict(scope_facts, governance=governance_violations))

    # ①' 知识兜底：按真实触碰路径重匹配，漏策展/未核实一律阻断
    coverage = _spec_coverage(ctx, task, decisions)
    if coverage["missing_curation"] or coverage["unresolved"] or coverage["period_problems"]:
        raise CheckError("WF_SPEC_INCOMPLETE", dict(scope_facts, spec=coverage))

    scan_before = fingerprint.items(ctx.root, object_paths(ctx, task))
    anchor, parts = current_anchor(ctx, task)
    plan = task.get("plan") or {}

    # ② verification.resolve(check)
    unresolved = resolve_verifications(ctx, task, "check")
    if unresolved:
        raise CheckError("WF_VERIFICATION_UNREADY", {"unresolved": unresolved})

    # ③ 执行验证
    started = records.now_str()
    log_dir = os.path.join(task_dir, "check-logs", records.now_str().replace(":", "").replace(".", ""))
    commands = []
    declared = (task.get("plan") or {}).get("verifications") or []
    referenced = set()
    for item in (task.get("plan") or {}).get("acceptance") or []:
        referenced.update(item.get("verification_ids") or [])
    for verification in declared:
        if not (verification.get("required") or verification.get("id") in referenced):
            continue
        # consume_at 只决定「声明与就绪的核对时点」，不豁免必需业务验证在 Check 中执行（机制稿 §3.5）
        invocation = verification.get("invocation") or {}
        if invocation.get("kind") == "manual":
            commands.append(_manual_command(verification, decisions, anchor, plan, plan.get("version")))
        else:
            commands.append(_run_argv(ctx, task, verification, log_dir))

    # ④ 双轴内部审查
    internal_review, review_problem = _parse_review_notes(review_notes_path)
    tdd_evidence = (internal_review or {}).get("tdd_evidence")
    history_entries = list(task.get("check_history") or [])
    if task.get("check"):
        history_entries.append(task["check"])  # 本次即将被替换的旧检查同样是历史
    history_commands = [command for entry in history_entries for command in entry.get("commands") or []]
    tdd_problem = (tdd_evidence_problem(tdd_evidence, commands, history_commands)
                   if plan.get("tdd") else None)
    tdd_ok = tdd_problem is None

    # R21：结束前重算完整范围核对（分类/外部变更/治理面），变化即不判 pass
    reclassified = scope.classify_candidates(ctx.root, task, receipts=_receipts(ctx))
    external_after, external_after_findings = scope.external_changes(ctx.root, task)
    governance_after, governance_state_after = scope.declaration_violations(
        reclassified["buckets"]["e"], reclassified["touch_paths"], ctx.root
    )
    scope_after = {
        "buckets": {key: reclassified["buckets"][key] for key in ("a", "b", "c", "d", "e", "f")},
        "external_changes": external_after_findings,
        "governance": governance_after,
    }
    if scope_after != {"buckets": scope_facts["buckets"], "external_changes": scope_facts["external_changes"],
                       "governance": governance_violations}:
        raise CheckError("WF_CHECK_STALE",
                         {"reason": "检查期间范围核对结论发生变化",
                          "before": {"buckets": scope_facts["buckets"],
                                     "external_changes": scope_facts["external_changes"],
                                     "governance": governance_violations},
                          "after": scope_after})

    scan_after = fingerprint.items(ctx.root, object_paths(ctx, task))
    if scan_after != scan_before:
        before_map = {entry["path"]: entry for entry in scan_before}
        changed = [entry["path"] for entry in scan_after
                   if before_map.get(entry["path"]) != entry]
        raise CheckError("WF_CHECK_STALE",
                         {"reason": "检查期间对象发生变化（扫描前后不一致）", "changed": changed})

    # ⑤ 写结果与指纹（锚点在 ② 之前固定，扫描前后不一致即不判 pass）
    acceptance_results = _acceptance_results(ctx, task, commands, decisions, anchor)
    failed_commands = [command for command in commands if command["status"] in ("failed", "not_run")]
    acceptance_failed = [item for item in acceptance_results if item["conclusion"] != "passed"]
    axes = {axis: ((internal_review or {}).get(axis) or {}).get("conclusion")
            for axis in ("standard", "requirement")}
    axes_failed = [axis for axis, conclusion in axes.items() if conclusion != "pass"]
    passed = (not failed_commands and not acceptance_failed and internal_review is not None
              and not axes_failed and tdd_ok)
    check_id = f"{records.utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex}"
    check = {
        "id": check_id,
        "anchor": {"check_anchor": anchor, "rule_version": ctx.rule_version()},
        "paths_digest": parts["paths_digest"],
        "content_digest": parts["content_digest"],
        "started_at": started,
        "ended_at": records.now_str(),
        "result": "pass" if passed else "fail",
        "commands": commands,
        "acceptance_results": acceptance_results,
        "internal_review": internal_review,
        "tdd_evidence": tdd_evidence,
        "invalidation": None,
        "scope_check": scope_facts,
        "spec_review": coverage,
        "governance": {"violations": governance_violations},
    }
    facts = {
        "check": check_id,
        "failed_commands": failed_commands,
        "acceptance": acceptance_failed,
        "internal_review": review_problem,
        "internal_review_axes": axes_failed,
        "tdd": tdd_problem,
        "object_paths": object_paths(ctx, task),
    }
    if passed:
        return check, None, facts
    return check, "WF_CHECK_FAILED", facts


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    return tasks_mod.task_dir(ctx.root, task.get("id"))


def _receipts(ctx):
    from . import tasks as tasks_mod

    return tasks_mod.task_receipts(ctx.root)
