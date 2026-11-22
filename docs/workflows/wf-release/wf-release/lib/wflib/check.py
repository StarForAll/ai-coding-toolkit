"""check.py — Check 固定五步与检查锚点（机制稿 §3.2、§3.5）。"""

from __future__ import annotations

import datetime
import os
import re
import shutil
import subprocess
import uuid

from . import config as config_mod, decisions as decisions_mod, fingerprint, records, scope
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
    """本次 Check 对象的内容域：`scope.delivery_set()` 的路径集合（唯一口径）。"""
    return list(scope.delivery_set(ctx.root, task)["paths"])


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
    versions = []
    for path in sorted(paths):
        info = spec_mod.load_spec(ctx.root, path)
        # 实质摘要优先（机制稿 §8.3：check + active clauses）；没有实质字段的规则退回整文件摘要，
        # 这条 fallback 是显式的：无 check/clauses 的规则无法区分"改排版"与"改条件"。
        digest = spec_mod.rule_digest(info.get("metadata") or {}) or records.file_digest(join(ctx.root, path))
        versions.append({"path": path, "digest": digest})
    return sorted(versions, key=lambda item: str(item["path"]).encode("utf-8"))


def assertions_digest(ctx, task):
    """断言面摘要（K3b）：验收项实质字段 + 被引用的验证定义 + 参与规则的实质摘要。

    只算实质字段（排版不计）：验收项 `statement`/`severity`/`verification_ids` 与 v42 的
    `verify.*` 字段；被引用的验证定义的 `invocation`/`cwd`/`input_refs`（命令或参数变了，
    标准的含义就变了）；每条参与 spec 规则的 `check` 与 active `clauses`。
    """
    from . import spec as spec_mod

    plan = task.get("plan") or {}
    acceptance = []
    for item in plan.get("acceptance") or []:
        if not isinstance(item, dict):
            continue
        verify = {key: item[key] for key in ("kind", "refs", "covers", "judged_by", "env") if key in item}
        entry = {"id": item.get("id"), "statement": item.get("statement"),
                 "severity": item.get("severity"),
                 "verification_ids": list(item.get("verification_ids") or [])}
        if verify:
            entry["verify"] = verify
        acceptance.append(entry)
    wanted = {vid for item in acceptance for vid in item["verification_ids"]}
    verifications = []
    for verification in plan.get("verifications") or []:
        if not isinstance(verification, dict) or verification.get("id") not in wanted:
            continue
        verifications.append({"id": verification.get("id"),
                              "invocation": verification.get("invocation"),
                              "cwd": verification.get("cwd"),
                              "input_refs": verification.get("input_refs")})
    rules = []
    for entry in spec_versions(ctx, task):
        info = spec_mod.load_spec(ctx.root, entry["path"])
        rules.append({"path": entry["path"],
                      "rule_digest": spec_mod.rule_digest(info.get("metadata") or {})})
    return records.H("wf-assertions-v1",
                     {"acceptance": acceptance, "verifications": verifications, "rules": rules})


def object_content_digest(ctx, task):
    return fingerprint.content_digest(fingerprint.items(ctx.root, object_paths(ctx, task)))


def workflow_snapshot_digest(ctx, task):
    """属于实例的任务：定义快照是**本任务的规则输入**（设计稿 §4.2 内容指纹末句）。

    没有 `run_id` 的任务返回 None（该键对普通任务不适用，`current_anchor` 也不把它算缺项）。
    实例任务缺快照/记录不可读 → `WF_RECORD_INVALID`：仅有哈希而无可读快照不满足恢复
    （设计稿 §5.7），不能把它静默折成 None 让旧锚点继续有效。
    """
    run_id = task.get("run_id")
    if not run_id:
        return None
    from . import runs as runs_mod

    run = runs_mod.load_run(ctx.root, run_id)
    definition = (run or {}).get("definition") or {}
    definition_digest = definition.get("digest")
    snapshot_rel = (definition.get("snapshot_path")
                    or f".wf/workflow-runs/{run_id}/definition.md")
    snapshot_path = join(ctx.root, snapshot_rel)
    snapshot_digest, cause, reason = records.file_digest_state(snapshot_path)
    if not isinstance(run, dict) or not definition_digest or cause:
        raise CheckError("WF_RECORD_INVALID",
                         {"reason": "run-bound task requires a readable definition snapshot",
                          "run": run_id, "definition_digest": definition_digest,
                          "snapshot": snapshot_rel,
                          "cause": cause, "detail": reason,
                          "exits": ["由 repair 核对实例记录与快照后恢复",
                                    "确认实例已终止：按设计稿 §5.9 处置该任务的归属后再重跑 Check"]})
    return records.H("wf-workflow-snapshot-v1", {"run": run_id,
                                                 "definition_digest": definition_digest,
                                                 "snapshot_digest": snapshot_digest})


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
        "assertions_digest": assertions_digest(ctx, task),
        "baseline_digest": records.file_digest(join(ctx.root, ".wf/baseline.md")),
        "config_digest": records.file_digest(join(ctx.root, ".wf/project-config.json")),
        "workflow_snapshot_digest": workflow_snapshot_digest(ctx, task),
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


# 键名的扫描长度必须**有界**：`[a-z0-9_.-]*` 无限长时，正则会在每一位置尝试扩张，
# 对一整行无分隔字符（压缩后的 JSON、长 token 串）退化成 O(n²)——400KB 日志实测挂死。
# 键名超过 64 字符的写法不在遮罩范围内（正常键名远短于此），这个界只限制"找键名"的扫描，
# 不限制被遮罩的值（`\S+` 仍可长）。
_KEY = r"[a-z0-9_.-]{0,64}"

SECRET_PATTERNS = (
    # Authorization: Bearer <值>（不设长度门槛，任意取值都遮罩）
    re.compile(r"(?i)\bBearer\s+[^\s\"',;]+"),
    # --token/--api-key/--access-token/--client-secret 等分离或等号/冒号写法（文本形态）
    re.compile(r"(?i)(--?" + _KEY + r"(?:token|secret|password|passwd|api[_-]?key)" + _KEY + r")"
               r"(\s*[=:]\s*|\s+)\S+"),
    # key: value / key=value
    re.compile(r"(?i)\b(" + _KEY + r"(?:api[_-]?key|token|secret|password|passwd)" + _KEY
               + r")\b\s*[:=]\s*\S+"),
    # JSON/字典内嵌：键名可能带引号、值也可能带引号（{"token":"x"}、{'access_token': "y"}）
    re.compile(r"(?i)([\"']?" + _KEY + r"(?:api[_-]?key|token|secret|password|passwd)" + _KEY
               + r"[\"']?\s*:\s*)([\"'])[^\"']*\2"),     # 带引号的值允许含空格/逗号
    re.compile(r"(?i)([\"']?" + _KEY + r"(?:api[_-]?key|token|secret|password|passwd)" + _KEY
               + r"[\"']?\s*:\s*)(?![\"'])[^\s,}]+"),     # 不带引号的单词值
    # 中文键名：本框架文档与人写的 quote 以中文为主，`口令：xxx` / `口令 xxx` 同样是凭据
    re.compile(r"(?:密码|口令|密钥|令牌|私钥|凭据)\s*[:：=]\s*\S+"),
    re.compile(r"(?i)(?:密码|口令|密钥|令牌|私钥)\s+[A-Za-z0-9_.\-]{6,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
)

SECRET_HEAD = re.compile(r"(?i)^(--?" + _KEY + r"(?:token|secret|password|passwd|api[_-]?key)"
                         + _KEY + r")(\s*[=:]\s*|\s+)")


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


# 触发词：只有出现这些片段的位置才可能构成敏感键名。用它先定位**窗口**，再在窗口内跑完整规则——
# 全篇逐位置跑正则会在长行（压缩 JSON、长 token 串）上退化成二次方；400KB 日志实测挂死。
TRIGGER = re.compile(r"(?i)(bearer|token|secret|password|passwd|api[_-]?key|sk-|gh[pousr]_|akia"
                        r"|密码|口令|密钥|令牌|私钥|凭据)")
# 窗口半宽：覆盖常见的 `key: value`、`--token value` 与 YAML 换行写法；超出此距离的
# "键在这里、值在很远的地方"不属这些规则表达的形态。
MASK_WINDOW = 512


def _mask_match(match):
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


def _mask_window(window):
    out = window
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(_mask_match, out)
    return out


def redact_text(text):
    """文本级遮罩：日志、facts 摘要、命令回显都走这一处，避免两套规则不一致。

    先按触发词定位窗口（合并重叠窗口），只在窗口内跑完整规则：语义与"全篇逐位置匹配"一致
    到窗口边界，但对长行是线性开销。
    """
    if not isinstance(text, str) or not text:
        return text or ""
    spans = [(match.start(), match.end()) for match in TRIGGER.finditer(text)]
    if not spans:
        return text
    windows = []
    for start, end in spans:
        left, right = max(0, start - MASK_WINDOW), min(len(text), end + MASK_WINDOW)
        if windows and left <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], right))
        else:
            windows.append((left, right))
    out, cursor = [], 0
    for left, right in windows:
        out.append(text[cursor:left])
        out.append(_mask_window(text[left:right]))
        cursor = right
    out.append(text[cursor:])
    return "".join(out)


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
                if decisions_mod.canonical("acceptance_conclusion", decision.get("choice")) != "passed":
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


LOG_HEAD_BYTES = 64 * 1024
LOG_TAIL_BYTES = 192 * 1024


def _log_payload(argv, cwd, exit_code, output):
    """把一次验证的执行事实写成可复核的日志文本（完整输出 + 可见截断）。

    此前只落最后一行 summary，复核只能靠人保留终端（dogfood 第 3 轮 reviewer 的
    "原始日志仅摘要"）。截断上限是**机制常量**而不是项目配置：日志是可丢弃证据，
    重复输出同一结论不引入新的预算键。
    """
    import hashlib

    raw = str(output or "").encode("utf-8", "replace")
    truncated = False
    dropped = 0
    if len(raw) > LOG_HEAD_BYTES + LOG_TAIL_BYTES:
        truncated = True
        dropped = len(raw) - LOG_HEAD_BYTES - LOG_TAIL_BYTES
        body = (raw[:LOG_HEAD_BYTES]
                + f"\n[wf-log-truncated kept={LOG_HEAD_BYTES + LOG_TAIL_BYTES} "
                  f"dropped={dropped} total={len(raw)}]\n".encode("utf-8")
                + raw[-LOG_TAIL_BYTES:])
    else:
        body = raw
    head = (f"argv: {records.canonical(argv)}\ncwd: {cwd}\nexit_code: {exit_code}\n"
            f"output_bytes: {len(raw)}\ntruncated: {truncated}\n\n").encode("utf-8")
    payload = head + body
    return {"text": payload, "bytes": len(raw), "truncated": truncated,
            "digest": "sha256:" + hashlib.sha256(payload).hexdigest()}


def _run_argv(ctx, task, verification, log_dir):
    invocation = verification.get("invocation") or {}
    argv = list(invocation.get("argv") or [])
    cwd = verification.get("cwd") or "."
    workdir = ctx.root if cwd == "." else join(ctx.root, cwd)
    started = records.now_str()
    # 验证命令跑在 OS 锁内（机制稿 §4.1 的已知偏差，见实现稿 §2.3.11）：至少给出超时上界，
    # 避免挂起的命令无限期占锁（第二十三轮复审外部 P2-NEW 的部分缓解）。
    cfg, problems = config_mod.load_project_config(ctx.root, allow_missing=True)
    try:
        value, problem = config_mod.value_of(cfg, problems, "verification_timeout_seconds")
    except config_mod.ConfigError as exc:
        raise CheckError("WF_RECORD_INVALID", {"reason": "invalid verification timeout config", "detail": str(exc)})
    # `value_of` 对非法值返回 (None, problem)：**必须消费 problem**，否则非法配置会静默退成无界
    # （第二十五轮复审 N25-2）。
    if problem:
        raise CheckError("WF_RECORD_INVALID", {"reason": "invalid verification timeout config",
                                               "detail": problem})
    timeout = value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
    output = ""
    try:
        result = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, check=False,
                                timeout=timeout)
        exit_code = result.returncode
        output = (result.stdout or "") + (result.stderr or "")
        summary = output.strip().splitlines()[-1] if output.strip() else ""
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        partial = exc.stdout or exc.stderr or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        output = partial
        summary = f"timed out after {timeout}s"
    except OSError as exc:
        exit_code = None
        summary = f"spawn failed: {exc}"
    ended = records.now_str()
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{verification.get('id')}.log")
    # 日志与 facts 都按秘密边界遮罩；命令参数一并过一遍（argv 可能带内联值）
    masked_argv = redact_argv(argv)
    summary = redact_text(summary)
    log = _log_payload(masked_argv, cwd, exit_code, redact_text(output))
    with open(log_path, "wb") as handle:
        handle.write(log["text"])
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
        "log_digest": log["digest"],
        "log_bytes": log["bytes"],
        "log_truncated": log["truncated"],
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


# 取值域只在 `wflib/decisions.py` 登记（实现稿 §2.3.11 ①）
EXTERNAL_CHECKED_CHOICES = decisions_mod.domain("external_checked")


def _external_touches_task(item, task):
    """该外部提交是否触及本任务批准触碰面（未触及的不构成待决项）。"""
    from . import paths as paths_mod

    from . import tasks as tasks_module

    touch = tasks_module.approved_touch_paths(task)
    for path in (item or {}).get("paths") or []:
        for pattern in touch:
            if paths_mod.match_path(pattern, path):
                return True
    return False


def _external_checked(item, decisions, task):
    """是否已有"已核对无影响"的人判：按提交 OID 精确匹配，或用 external-changes 整体声明。"""
    commit = (item or {}).get("commit")
    # `task-attribute` 登记过的归属也算"已核对"：否则检查侧给出的出口 2 走不到终点
    # （审查实测：登记进 attribution 后 external_findings 原样重现，因为只看了 trailer）
    for entry in (task or {}).get("attribution", {}).get("decisions") or []:
        if not isinstance(entry, dict):
            continue
        if commit and str(entry.get("commit", "")).startswith(str(commit)[:7]):
            return True
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
            and decisions_mod.accepts("acceptance_conclusion", decision.get("choice"))
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
                             and decisions_mod.canonical("acceptance_conclusion", decision.get("choice")) == "passed"
                             for decision in decisions or [])]
    decisions_used = [decision for decision in decisions or []
                      if any(_decision_covers(decision, item["path"], plan, version)
                             and decisions_mod.canonical("acceptance_conclusion", decision.get("choice")) == "passed"
                             for item in needs)]
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


def run_check_scope(ctx, task, decisions, review_notes_path, exclusion_entries=None):
    """Check 的**锁内准备段**：范围核对、知识兜底、锚点固定（机制稿 §3.5 ①②）。

    这一段只读文件与记录，**不执行任何外部命令**——长操作留给 `run_check_execute()` 在锁外跑
    （机制稿 §4.1「长操作不长期持 OS 锁」）。返回的 state 是后面两段的唯一输入。
    """
    task_dir = _task_dir(ctx, task)
    # ① 范围核对
    receipts = _receipts(ctx)
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    # 人对外来改动的排除（本次声明给出时消费；记录进任务，摘要变化即失效）
    if exclusion_entries:
        new_records, problems = scope.exclusion_records(ctx.root, classified, exclusion_entries)
        if problems:
            raise CheckError("WF_SEMANTIC_DECISION",
                             {"problems": problems,
                              "exits": ["只排除未归属未提交的路径；属本任务的路径在批准触碰面内直接计入交付，"
                                        "已提交的历史改动才用 task-attribute --commit <sha> 裁决归属"]})
        scope.persist_exclusions(task, new_records)
        classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    external, external_findings = scope.external_changes(ctx.root, task)
    buckets = classified["buckets"]
    scope_facts = {
        "candidates": len(classified["candidates"]),
        "buckets": {key: buckets[key] for key in ("a", "b", "c", "d", "e", "f")},
        "excluded": classified.get("exclusions") or {},
        "external_changes": external_findings,
        "external_pending": len(external_findings or []),
    }
    # 任务基线不可达：设计稿 §4.2/§5.4 要求走记录锚点核对并由人裁决，不能静默通过
    if (external or {}).get("unreachable"):
        raise CheckError("WF_HISTORY_UNRESOLVED",
                         dict(scope_facts, baseline=(external or {}).get("baseline"),
                              reason="task baseline head is unreachable",
                              exits=["按设计稿 §5.4 只读核对记录锚点后由人裁决",
                                     "确认基线被重写后重做本任务的锚点/检查",
                                     "如属历史迁移，先 repair 核旧写者与记录来源"]))
    delivery = scope.delivery_set(ctx.root, task, receipts=receipts, classified=classified)
    covered_expansion = delivery["buckets"]["covered_f"]
    uncovered_expansion = delivery["buckets"]["uncovered_f"]
    if uncovered_expansion:
        # K6 第 4 类：越出批准面的修改必须**先确认后改**；`expand` 确认只覆盖它登记的路径。
        raise CheckError("WF_SCOPE_VIOLATION",
                         dict(scope_facts, out_of_scope=uncovered_expansion,
                              covered_by_authorization=covered_expansion,
                              exits=["回 Plan 扩范围并重新批准",
                                     "先取得未覆盖路径的扩面确认（K6 第 4 类）后再改"]))
    if covered_expansion:
        # 已批准扩面：仍留事实（供预览与判断清单使用），并并入 e 供展示/指纹使用。
        scope_facts = dict(scope_facts,
                           approved_expansion=covered_expansion,
                           buckets=dict(scope_facts["buckets"],
                                        e=sorted(set(scope_facts["buckets"]["e"]) | set(covered_expansion)),
                                        f=[]))
    if buckets["c"]:
        raise CheckError("WF_WORKSPACE_UNRESOLVED",
                         dict(scope_facts, other_tasks=buckets["c"],
                              vendor_dirty=buckets.get("v", []),
                              exits=["确认这些外来改动不属于本任务：写一条 choice=排除外来改动 的决定"
                                     "（paths + by/at/quote/source）后用 --workspace-exclusion 重跑 task-check",
                                     "由人实际处置这些路径（提交 / 移走 / 具名承接）后重跑"]))
    pending_external = [item for item in (external_findings or [])
                        if _external_touches_task(item, task)
                        and not _external_checked(item, decisions, task)]
    if pending_external:
        raise CheckError("WF_SEMANTIC_DECISION",
                         dict(scope_facts, external_pending_unchecked=pending_external,
                              exits=["逐条核对影响并给出『已核对无影响』决定",
                                     "确认属本任务且已提交的改动用 task-attribute --commit <sha> 裁决归属",
                                     "影响验收则回 Plan，影响检查则重检"]))
    if buckets.get("d"):
        # 归属语义存疑：交人裁决，不当通过（机制稿 §3.5 d 档）。
        # 争抢判定由 `scope.classify_candidates` 单次给出（它自己调 `cross_task_conflicts`），
        # 这里不再重复计算——两处各算一次就会漂移。
        raise CheckError("WF_SCOPE_UNRESOLVED",
                         dict(scope_facts, ambiguous_ownership=buckets["d"],
                              cross_task_claims=classified.get("conflicts") or []))
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
        # 出口要可执行，先得说清缺什么：把"缺哪几条"提到 facts 顶层（否则 AI 只看到一句
        # "分批读取全文后重试"，不知道读哪条——这是 K10 的落实，不是措辞偏好）。
        missing_paths = sorted({item.get("path") if isinstance(item, dict) else str(item)
                                for item in (coverage.get("missing_curation") or [])}
                               | {item.get("path") if isinstance(item, dict) else str(item)
                                  for item in (coverage.get("unresolved") or [])})
        exits = ["对缺策展的 spec 先 `task-curate --spec <路径>`",
                 "对未核实的 spec 用 `spec --file <路径>` 完成读取留痕，或按设计稿 §6.2 处置",
                 "到期/待核项按 `verify resolve` 或重新核实后重入 Check"]
        raise CheckError("WF_SPEC_INCOMPLETE",
                         dict(scope_facts, spec=coverage, missing=missing_paths,
                              missing_curation=coverage.get("missing_curation"),
                              unresolved=coverage.get("unresolved"),
                              period_problems=coverage.get("period_problems"), exits=exits))

    scan_before = fingerprint.items(ctx.root, object_paths(ctx, task))
    anchor, parts = current_anchor(ctx, task)
    plan = task.get("plan") or {}
    started = records.now_str()      # 本次 Check 的起点（`check.started_at`），供两段共用

    # ② verification.resolve(check)
    unresolved = resolve_verifications(ctx, task, "check")
    if unresolved:
        raise CheckError("WF_VERIFICATION_UNREADY", {"unresolved": unresolved})

    return {
        "scope_facts": scope_facts,
        "coverage": coverage,
        "governance_violations": governance_violations,
        "anchor": anchor,
        "parts": parts,
        "plan": plan,
        "scan_before": scan_before,
        "started": started,
        "decisions": decisions,
        "review_notes_path": review_notes_path,
    }


def run_check_execute(ctx, task, state):
    """Check 的**锁外执行段**：逐条跑已批准的验证命令（机制稿 §4.1）。

    只做执行与取证；不判 pass、不写记录。何时回锁、回锁后如何重核由调用方负责。
    """
    anchor = state["anchor"]
    plan = state["plan"]
    decisions = state["decisions"]
    task_dir = _task_dir(ctx, task)
    log_dir = os.path.join(task_dir, "check-logs",
                           state["started"].replace(":", "").replace(".", ""))
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

    return commands


def run_check_finish(ctx, task, state, commands):
    """Check 的**锁内定稿段**：双轴审查、结束前重算范围与锚点、组装检查记录（机制稿 §3.5 ④⑤）。"""
    scope_facts = state["scope_facts"]
    coverage = state["coverage"]
    governance_violations = state["governance_violations"]
    anchor = state["anchor"]
    parts = state["parts"]
    plan = state["plan"]
    scan_before = state["scan_before"]
    started = state["started"]
    decisions = state["decisions"]
    review_notes_path = state["review_notes_path"]
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
        # parts 是"失配时列出差异"的第二端（机制稿 §3.5）：与 check_anchor 同源写入的快照。
        "anchor": {"check_anchor": anchor, "rule_version": ctx.rule_version(), "parts": dict(parts)},
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
        # vendor_dirty 消费点（2026-11-21 批C）：结束前重分类的 v 桶如实上抛——
        # task-check facts 与归档收尾都能看到，人据此确认归属（回源仓库立项），不阻断。
        "vendor_dirty": reclassified["buckets"]["v"],
        # b-1（九轮→十轮 b-1）：开工前已存在的交付路径经 Check facts 正常回传——
        # 否则 check→task-check facts 断链，AI 无法从正常 Check 结果获知需确认归属。
        "preexisting_in_scope": reclassified.get("preexisting_in_scope") or [],
    }
    if passed:
        return check, None, facts
    return check, "WF_CHECK_FAILED", facts


def run_check(ctx, task, decisions, review_notes_path, exclusion_entries=None):
    """固定五步的兼容入口：三段顺序执行（不需要拆锁的调用方用它）。

    `cmd_task_check` 不用它——它必须在执行段前后各取/放一次锁。
    """
    state = run_check_scope(ctx, task, decisions, review_notes_path,
                            exclusion_entries=exclusion_entries)
    commands = run_check_execute(ctx, task, state)
    return run_check_finish(ctx, task, state, commands)


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    return tasks_mod.task_dir(ctx.root, task.get("id"))


def _receipts(ctx):
    from . import tasks as tasks_mod

    return tasks_mod.task_receipts(ctx.root)
