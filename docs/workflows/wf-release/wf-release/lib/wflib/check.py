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


def object_paths(ctx, task, classified=None):
    """本次 Check 对象的内容域：`scope.delivery_set()` 的路径集合（唯一口径）。"""
    return list(scope.delivery_set(ctx.root, task, classified=classified)["paths"])


def spec_versions(ctx, task, classified=None):
    """当前命中或策展的 spec（机制稿 §3.5）：新增的命中规则必须进入锚点输入。"""
    from . import spec as spec_mod
    from . import tasks as tasks_mod

    paths = set()
    for entry in task.get("curation") or []:
        if entry.get("released") or not entry.get("path"):
            continue
        paths.add(entry["path"])
    if classified is None:
        # 三轮三审 b6：锚点计算路径统一由 anchor_parts 一次分类后透传；
        # 独立调用面缺省自行分类（口径不变，只是不再在锚点内重复扫描）。
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
        # 受控返工 R 不写 run_id，但同属在途实例：锚点必须含该实例的快照（2026-11-28 人裁 §48）。
        try:
            from . import runs as runs_mod0
            from . import tasks as tasks_mod0

            for _rid, run in runs_mod0.iter_runs(ctx.root):
                if not isinstance(run, dict) or run.get("terminal") is not None:
                    continue
                if tasks_mod0._task_in_run(task, task.get("id"), run.get("id"), run, ctx.root):
                    run_id = run.get("id")
                    break
        except Exception:
            run_id = None
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


def anchor_parts(ctx, task, *, check=None, classified=None):
    """锚点输入快照（check.parts 与 check_anchor 覆盖面同源）。

    W2-2（三轮裁决③）：新增常开键 control_plane_digest——vendor 脏路径集合的内容
    指纹（v 桶取 classify_candidates 单一来源）。Check 流程把已算分类传入
    （`classified`，与 delivery_set 同型）；只读调用面（judgments show /
    archive --draft / stop --preview 等锚点计算）缺省自行分类——只读面每次
    多一轮分类扫描的成本如实可见，不静默省略。
    """
    from . import tasks as tasks_mod

    plan = task.get("plan") or {}
    entry = task.get("entry_snapshot") or {}
    # 三轮三审 b6：锚点计算只做**一次**分类——classify 在此统一计算（缺省时），
    # object_paths/spec_versions 都透传复用；此前只读面一次锚点要扫 2–3 轮。
    if classified is None:
        from . import scope as scope_mod
        from . import tasks as _tasks_mod

        try:
            classified = scope_mod.classify_candidates(ctx.root, task,
                                                        receipts=_tasks_mod.task_receipts(ctx.root))
        except (CheckError, _tasks_mod.TaskError, records.RecordInvalid):
            # 契约错误原样传播：classify_candidates 对入口快照问题本就抛
            # WF_RECORD_INVALID（scope.py 既有口径）——不改写、不折 None，
            # 否则 current_anchor 折成 missing_anchor_inputs → WF_APPROVAL_MISSING 误归因。
            raise
        except Exception as exc:
            raise CheckError("WF_SCOPE_UNRESOLVED",
                             {"reason": "control-plane classification failed",
                              "detail": str(exc),
                              "exits": ["按 §5.4/repair 核对任务记录与入口快照后重试",
                                        "核对基线/记录归属后重跑 Check"]}) from exc
    try:
        paths = object_paths(ctx, task, classified=classified)
    except (CheckError, tasks_mod.TaskError, records.RecordInvalid):
        raise                    # 契约错误（WF_RECORD_INVALID 等）原样传播
    except Exception as exc:
        # delivery_set 消费同一份 classified，理论不再触发分类；保留同口径包装
        # 防御透传面之外的路径（不漏裸异常）。
        raise CheckError("WF_SCOPE_UNRESOLVED",
                         {"reason": "control-plane classification failed",
                          "detail": str(exc),
                          "exits": ["按 §5.4/repair 核对任务记录与入口快照后重试",
                                    "核对基线/记录归属后重跑 Check"]}) from exc
    return {
        "plan_version": tasks_mod.normalized_plan_version(task),
        "entry_snapshot_digest": fingerprint.snapshot_digest(entry) if entry else None,
        "touch_paths_digest": fingerprint.touch_paths_digest(entry.get("touch_paths") or []),
        "paths_digest": fingerprint.paths_digest(paths),
        "content_digest": fingerprint.content_digest(fingerprint.items(ctx.root, paths)),
        "acceptance_digest": plan.get("acceptance_digest"),
        "spec_versions": spec_versions(ctx, task, classified=classified),
        "assertions_digest": assertions_digest(ctx, task),
        "baseline_digest": records.file_digest(join(ctx.root, ".wf/baseline.md")),
        "config_digest": records.file_digest(join(ctx.root, ".wf/project-config.json")),
        "workflow_snapshot_digest": workflow_snapshot_digest(ctx, task),
        "control_plane_digest": fingerprint.control_plane_digest(
            (classified.get("buckets") or {}).get("v") or [], ctx.root),
        # 五轮审查 b2：呈现伴随键（不进 check_anchor 白名单、不参与哈希）——
        # control_plane_digest 失配时 drift 输出只有两串哈希，无法归因"改了哪个框架文件"；
        # v 桶路径集合并排保存，"变了什么"与"变了"同屏可见。空桶为 []（不进缺项判定）。
        "control_plane_paths": sorted((classified.get("buckets") or {}).get("v") or []),
    }


def current_anchor(ctx, task, *, classified=None):
    parts = anchor_parts(ctx, task, classified=classified)
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


# 键名的扫描长度必须**有界**：无界的 `[a-z0-9_.-]*` 会在每一位置尝试扩张，对长行退化成
# O(n²)（400KB 日志实测挂死）。这个界只限制"找键名"的扫描，不限制被遮罩的值长度。
_KEY = r"[a-z0-9_.-]{0,64}"
_KEYWORD = (r"(?:api[_-]?key|access[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key"
            r"|client[_-]?secret|secret|token|password|passwd|passphrase|credential)")
# 值的三种形态：
# - 单行引号值（允许内部空格与转义引号，`"FIRST SECOND THIRD"`、`"abc\\"def"`）；
# - 不透明凭据串（JWT / opaque token / hex / base64，≥8 字符且不含分隔符）；
# - 一般值（**不得以 `=`/`:` 起始**：那是分隔符，不是值——否则 `token = value` 会把 `=`
#   当成值掩掉、留下真值，2026-11-23 十轮复审 a-P0 的回归就是这样来的）。
# 注意必须整体分组：`head + _QUOTED` 拼接时，未分组的 `|` 会让右半支**脱离 head**，
# 变成"任意位置的裸引号串都被遮"（十轮复审的矩阵用例当场抓到）。
_QUOTED = r"(?:\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*')"
_OPAQUE = r"[A-Za-z0-9_\-.+/=]{8,}"
# 材料级的字面量值域：引号值，或"看起来是凭据"的不透明串——**排除调用/取值形态**
# （后面紧跟 `(`、`.`、`[` 的是表达式，如 `read_from_store()`、`os.environ[...]`）。
# 早前把非引号值整条标成 code_safe=False，结果 `.env` 里的 `API_KEY=abcdefgh123456`
# 在材料里明文外发（2026-11-23 十一轮复审 a-P0/b-3）。
# 判据是"这串东西本身像不像字面凭据"：不带 `.`/括号/下标的裸串按字面量处理
# （`hunter2`、`abcdefgh123456`、`.env` 里的值），带 `.` 或调用/下标语法的按表达式留给
# reviewer 看（`read_from_store()`、`os.environ['X']`、`self.secret`）。
# 裸值判据（字面量）：不含调用/下标语法 `(`/`[`、**含至少一个数字**、长度 ≥4。
# 含数字这一条把"常量引用/版本号"排除在材料遮罩外（`DEFAULT_PASSWORD`、`api_key_version = 2`），
# 让 reviewer 仍能看出取值变化；真凭据几乎总含数字（`hunter2`、`sk-…`、`.env` 里的值）。
_LITERAL = (r"(?:" + _QUOTED + r"|(?![^\s\"',;]*[(\[])(?=[^\s\"',;]*\d)"
            r"[^\s\"',;]{4,})")
_VALUE = r"(?:" + _QUOTED + r"|(?![=:])[^\s\"',;]+)"
_CRED_VALUE = r"(?:" + _QUOTED + r"|" + _OPAQUE + r")"


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


def _mask_head(match):
    """保留键/前缀，遮掉值。计数类键名原样返回。"""
    raw = match.group(0)
    if _non_secret_key(raw):
        return raw
    return (match.group("head") or "") + "***"


def _mask_whole(_match):
    return "***"


def _mask_url_password(match):
    """URL userinfo 只遮 password 段，保留 user 与 host。"""
    return match.group(1) + "***" + match.group(3)


# 关键词字面预筛：命中才跑对应正则（无关键词的大文本因此只付一次 `lower()` 的代价）。
_NEEDLES = ("token", "secret", "password", "passwd", "passphrase", "api_key", "api-key",
            "apikey", "access_key", "access_token", "auth_token", "client_secret",
            "private_key", "credential")

# **形态清单按协议承诺一次性规格化**（`redaction.json` 的 `secret-mask`：密钥/令牌/私钥/
# URL 内凭据/环境变量值）。每条规则：`(pattern, masker, needles, code_safe)`。
# - `needles` 是廉价字面预筛，命中才跑该正则；**只用关键词本身**，不掺空白形态
#   （此前 `"token "` 带一个空格，tab 形态靠巧合才被遮住）。
# - `code_safe` 标出"遮住它不会毁掉代码可读性"的规则：材料（diff/PRD）是给人/异种 reviewer
#   审代码的，`password = read_from_store()` 这种**调用**不是凭据，不该被掩成
#   `password = ***`（十轮复审 b-3）；日志与错误回显走全量规则。
# **顺序即语义**：具体形态（PEM/厂商令牌/URL/头/Bearer）先，键值与 flag 形态随后——
# 裸前缀规则若排在键值规则之前，`token = value` 会先被它吃掉分隔符（十轮复审 a-P0）。
RULES = (
    (re.compile(r"-----BEGIN[^-\n]{0,64}PRIVATE KEY-----(?s:.*?)-----END[^-\n]{0,64}PRIVATE KEY-----"),
     _mask_whole, ("private key",), True),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"), _mask_whole, ("sk-",), True),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}\b"), _mask_whole,
     ("ghp_", "gho_", "ghu_", "ghs_", "ghr_"), True),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}\b"), _mask_whole, ("akia",), True),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), _mask_whole, ("xox",), True),
    (re.compile(r"(://[^/\s:@]+:)([^/\s]+)(@)"), _mask_url_password, ("://",), True),
    (re.compile(r"(?i)(?P<head>\bauthorization\s*[:=]\s*(?:[A-Za-z]+\s+)?)" + _CRED_VALUE),
     _mask_head, ("authorization",), True),
    # `Bearer = <值>`/`token: <值>` 与键值规则同一语义类：材料级遮**字面量**值（调用/常量引用保留）。
    (re.compile(r"(?i)(?P<head>\b(?:bearer|basic|digest|token)\s*[:=]\s*)" + _LITERAL),
     _mask_head, ("bearer", "basic", "digest", "token"), True),
    (re.compile(r"(?i)(?P<head>\b(?:bearer|basic|digest|token)\s*[:=]\s*)" + _VALUE),
     _mask_head, ("bearer", "basic", "digest", "token"), False),
    (re.compile(r"(?i)(?P<head>\b(?:bearer|basic|digest|token)\s+)" + _CRED_VALUE),
     _mask_head, ("bearer", "basic", "digest", "token"), True),
    # 值**带引号**时是字面量（配置文件/JSON/env 里的真实凭据）⇒ 材料级也遮；
    # 值不带引号时可能是标识符或调用（`password = read_from_store()`）⇒ 只有全量级遮。
    (re.compile(r"(?i)(?P<head>--?[a-z0-9_.-]{0,64}" + _KEYWORD
                + r"[a-z0-9_.-]{0,64}(?:\s*[=:]\s*|\s+))" + _LITERAL), _mask_head, _NEEDLES, True),
    (re.compile(r"(?i)(?P<head>[\"']?[a-z0-9_.-]{0,64}" + _KEYWORD
                + r"[a-z0-9_.-]{0,64}[\"']?\s*[:=]\s*)" + _LITERAL), _mask_head, _NEEDLES, True),
    (re.compile(r"(?i)(?P<head>--?[a-z0-9_.-]{0,64}" + _KEYWORD
                + r"[a-z0-9_.-]{0,64}(?:\s*[=:]\s*|\s+))" + _VALUE), _mask_head, _NEEDLES, False),
    (re.compile(r"(?i)(?P<head>[\"']?[a-z0-9_.-]{0,64}" + _KEYWORD
                + r"[a-z0-9_.-]{0,64}[\"']?\s*[:=]\s*)" + _VALUE), _mask_head, _NEEDLES, False),
    # 中文键名出现在配置/文档里，从不构成"代码逻辑"——材料级同样遮字面量值。
    (re.compile(r"(?P<head>(?:密码|口令|密钥|令牌|私钥|凭据)\s*(?:[:：=]\s*|\s+))" + _LITERAL),
     _mask_head, ("密码", "口令", "密钥", "令牌", "私钥", "凭据"), True),
    (re.compile(r"(?P<head>(?:密码|口令|密钥|令牌|私钥|凭据)\s*(?:[:：=]\s*|\s+))" + _VALUE),
     _mask_head, ("密码", "口令", "密钥", "令牌", "私钥", "凭据"), False),
)



def redact_text(text):
    """文本级遮罩（全量）：日志、facts 摘要、命令回显。

    规则按协议承诺的形态一次性列出（`RULES`），对全文逐条应用；每条带廉价字面预筛，
    因此没有关键词的大文本只付一次 `lower()`。**没有窗口**：窗口曾经兼作"值的可见范围"，
    于是超过窗口的值只遮前半段、窗口内的触发词又被误当成"已覆盖"。
    """
    return _apply_rules(text, code_safe_only=False)


def redact_material(text):
    """材料级遮罩（code_safe 规则）：审查材料是**给人审代码的**，只遮明显的字面凭据。

    `password = read_from_store()` 这类调用不是凭据，不该被掩成 `password = ***`——那会让
    reviewer 无法判断被遮的是字面值还是调用逻辑（十轮复审 b-3）。日志/错误回显仍走
    `redact_text` 全量规则：那里宁过勿漏，且不是给人读逻辑的。
    """
    return _apply_rules(text, code_safe_only=True)


def _structured_secret_key(key):
    """结构化数据里的**字段名本身**就是信号：`{"password": "…"}` 的值不必自带引号/数字。"""
    text = str(key).lower()
    if text in NON_SECRET_KEYS:
        return False
    if text.endswith(("_count", "_limit", "_budget", "_size", "_type", "_version", "_name")):
        return False
    return any(word in text for word in ("token", "secret", "password", "passwd", "passphrase",
                                         "api_key", "apikey", "api-key", "access_key",
                                         "access_token", "auth_token", "client_secret",
                                         "private_key", "credential", "密码", "口令", "密钥",
                                         "令牌", "私钥", "凭据"))


# 配置文件类型：这些文件里"裸值"就是凭据本体的写法（`.env`/yaml/ini/tfvars…），
# 材料档对它们用**全量**规则；代码文件才用"只遮字面量"的判据保可读性
# （2026-11-23 十四轮复审 a-1：`config.yaml` 里纯字母 API key 曾随材料外发）。
CONFIG_SUFFIXES = (".env", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".properties", ".toml",
                   ".tfvars", ".json", ".jsonc", ".pem", ".key", ".crt", ".cer", ".p12", ".pfx")


def is_config_path(path):
    name = str(path or "").lower()
    if name.endswith(tuple(suffix for suffix in CONFIG_SUFFIXES if suffix != ".env")):
        return True
    base = name.rsplit("/", 1)[-1]
    return base == ".env" or base.startswith(".env.") or "/.env." in name


def verification_timeout(root):
    """项目配置里的验证超时（秒）；未配置或非法配置都返回 None（无界），非法值抛错。

    **两个执行点（Check 与开工验证）必须共用这一处**：开工验证在项目锁内跑，
    没有超时界时一条挂起的命令会卡住所有依赖同一把锁的操作（十四轮 a-3）。
    """
    cfg, problems = config_mod.load_project_config(root, allow_missing=True)
    try:
        value, problem = config_mod.value_of(cfg, problems, "verification_timeout_seconds")
    except config_mod.ConfigError as exc:
        raise CheckError("WF_RECORD_INVALID",
                         {"reason": "invalid verification timeout config", "detail": str(exc)})
    # `value_of` 对非法值返回 (None, problem)：**必须消费 problem**，否则非法配置会静默退成无界
    # （第二十五轮复审 N25-2）。
    if problem:
        raise CheckError("WF_RECORD_INVALID", {"reason": "invalid verification timeout config",
                                               "detail": problem})
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def redact_for_path(path, text):
    """材料里的**按文件类型**遮罩：配置类全量、代码类只遮字面量。

    `path` 为 None（路径解析不出，例如 Git 转义形态没认出来）时 **fail-closed**：按配置类
    全量遮——宁可用全量档让代码少可读，也不让凭据出去（十六轮 b-1）。
    """
    if not isinstance(text, str) or not text:
        return text or ""
    if path is None or is_config_path(path):
        return redact_text(text)
    return redact_material(text)


ARGV_KEYS = ("argv",)


def redact_commands(commands):
    """材料里的命令记录：**argv 用位置语义遮罩**（`--password <值>` 分离写法），其余字符串走全量档。

    命令记录是"真实执行过的 argv"——与配置类同性质：裸值就是凭据本体，而材料的"保代码可读"
    判据在这里只会漏（十五轮 b-P0：同一凭据在 Check 记录里被 `redact_argv` 遮成 `***`，
    在随材料外发的 tests.json 里却是明文，材料比入库记录暴露更宽）。
    """
    def walk(value, key=None):
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, (list, tuple)):
            if key in ARGV_KEYS:
                return redact_argv([str(item) for item in value])
            return [walk(item, key) for item in value]
        if isinstance(value, dict):
            redacted = {}
            for name, item in value.items():
                # 字段名本身是指标：`decision.password` 的值不必自带引号/数字（十六轮 b-2）
                if _structured_secret_key(name) and isinstance(item, str):
                    redacted[name] = "***"
                elif _structured_secret_key(name) and isinstance(item, (int, float)) \
                        and not isinstance(item, bool):
                    redacted[name] = "***"
                else:
                    redacted[name] = walk(item, name)
            return redacted
        return value

    return walk(commands)


def redact_object(value, *, code_safe=True):
    """结构化脱敏：递归处理 dict/list 里的字符串，**只走一次**、不经过 JSON 往返。

    两个要点：① 材料入口不能"先写原文、最后读回 JSON 覆写"（脱敏一旦破坏结构就抛
    JSONDecodeError，而原文已经落盘）；② 逐值脱敏会丢掉**字段名**提供的语义——
    `{"password": "purelettershere"}` 的值本身不含引号/数字，纯文本规则认不出它，
    所以这里按字段名直接判定（`_structured_secret_key`），值整体遮掉。
    """
    mask = redact_material if code_safe else redact_text
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if _structured_secret_key(key) and isinstance(item, str):
                redacted[key] = "***"
            elif _structured_secret_key(key) and isinstance(item, (int, float)) \
                    and not isinstance(item, bool):
                redacted[key] = "***"      # 数字型的口令同样不留在材料里
            else:
                redacted[key] = redact_object(item, code_safe=code_safe)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_object(item, code_safe=code_safe) for item in value]
    return value


def _apply_rules(text, *, code_safe_only):
    if not isinstance(text, str) or not text:
        return text or ""
    lowered = text.lower()
    for pattern, masker, needles, code_safe in RULES:
        if code_safe_only and not code_safe:
            continue
        if needles and not any(needle in lowered for needle in needles):
            continue
        text = pattern.sub(masker, text)
    return text


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
    # "必须有命令"的判据与执行段同源：**required 或被验收项引用**的验证项才算必须执行。
    # 只有可选、且未被引用的补充验证时，命令列表为空是合法形态（十二轮 b-4）；
    # 判据用 `declared`（上面按 id 建的表）本身，不要新起同名列表变量——那样
    # `vid not in declared` 会恒真，把每条命令判成 unknown（十一轮踩过）。
    try:
        referenced = set()
        for item in plan.get("acceptance") or []:
            referenced.update(item.get("verification_ids") or [])
        must_run = [vid for vid, entry in declared.items()
                    if entry.get("required") is not False or vid in referenced]
    except Exception:      # noqa: BLE001 — 结构异常由后面的字段校验报告
        must_run = list(declared)
    if not isinstance(commands, list) or (not commands and must_run):
        problems.append({"field": "commands", "reason": "missing or empty"})
        commands = []
    elif not commands:
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
                from . import tasks as _tasks_mod
                if not _decision_covers(decision, str(vid), plan,
                                        _tasks_mod.normalized_plan_version(task)):
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
    # 开工验证与 Check 共用这一处（`verification_timeout`）：同一个配置键、同一套非法值归因。
    timeout = verification_timeout(ctx.root)
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
        # 验证定义身份：同 id 但改了 argv/cwd/required 就不是"同一个验证"，红绿不能跨定义配对
        "verification_digest": fingerprint.verification_digest(verification),
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


def _manual_command(verification, decisions, anchor, plan, plan_version, content_digest=None):
    """manual 验证：只接受明确 choice=passed 的人判 Decision，并把本次锚点核绑到记录。

    决定还必须绑定**人当时看到的交付内容**（`content_digest` = `status` 的
    `delivery.content_digest`；不用 `object_digest`——那是"已批准的规划对象摘要"，两者不能混用）：
    只绑规划版本的话，代码改了、规划没变时旧的 `passed` 会被沿用到未确认的内容上，并被记进
    新 Check 的锚点（2026-11-23 十轮复审 b-1）。
    """
    verification_id = verification.get("id")
    matches = [decision for decision in decisions or []
               if _decision_covers(decision, verification_id, plan, plan_version)
               and (content_digest is None
                    or decision.get("content_digest") == content_digest)]
    entry = {
        "verification_id": verification_id,
        "verification_digest": fingerprint.verification_digest(verification),
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
        stale = [decision for decision in decisions or []
                 if _decision_covers(decision, verification_id, plan, plan_version)]
        if stale:
            entry["summary"] = ("manual decision exists but is not bound to current content "
                                "(content_digest mismatch)")
            entry["stale_decision"] = {
                "content_digest": (stale[-1] or {}).get("content_digest"),
                "current_content_digest": content_digest,
            }
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


def _acceptance_results(ctx, task, commands, decisions, anchor, content_digest=None):
    from . import tasks as tasks_mod

    plan = task.get("plan") or {}
    # 与锚点/回执同源：机械修订沿等价链归一到既有批准版本，不拿 raw plan.version 比。
    plan_version = tasks_mod.normalized_plan_version(task)
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
        # 直接人判（无 verification_ids 的验收项）同样要绑定交付内容：只比验收项 id + 规划版本
        # 时，代码变了、规划没变也会沿用旧结论（2026-11-23 十一轮复审 b-1）。
        matches = [
            decision
            for decision in decisions or []
            if _decision_covers(decision, str(item.get("id")), plan, plan_version)
            and decisions_mod.accepts("acceptance_conclusion", decision.get("choice"))
            and (content_digest is None or decision.get("content_digest") == content_digest)
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
            entry = {
                "acceptance_id": item.get("id"),
                "verification_ids": [],
                "decision": None,
                "conclusion": "pending",
                "evidence_refs": [],
            }
            # 与 manual 同型：已绑定规划但内容摘要不符时给出字段级事实，不把"决定写错"
            # 报成"人没给决定"。
            stale = [decision for decision in decisions or []
                     if _decision_covers(decision, str(item.get("id")), plan, plan_version)]
            if stale:
                entry["stale_decision"] = {
                    "content_digest": (stale[-1] or {}).get("content_digest"),
                    "current_content_digest": content_digest,
                }
            results.append(entry)
    return results


def _parse_review_notes(path):
    if not path:
        return None, {"reason": "internal review notes missing"}
    # 缺失与"内容不是对象"分开归因（2026-11-27 独立审查）：`load_json` 对不存在的文件返回
    # None，若只报"must be a JSON object"，AI 会去改文件内容而不是改路径——真实原因（相对
    # 进程 CWD 解析不到、文件根本没被读到）被掩盖成格式问题，白跑一轮。
    if not os.path.exists(path):
        return None, {"reason": f"review notes file not found: {path}",
                      "hint": "路径按进程 CWD（通常是项目根）解析；用 `wf.py status` 回显的 "
                              "directory 拼出任务目录内的路径，或先取 `--review-notes-draft` 骨架回显的确切路径"}
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
    from . import decisions as decisions_mod

    if not decisions_mod.subject_mentions(decision.get("subject"), subject_id):
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

    from . import tasks as _tasks_mod

    plan = task.get("plan") or {}
    version = _tasks_mod.normalized_plan_version(task)
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


def verification_run_commands(task):
    """把 `execution.verification_runs` 归一成 command 形状（供红证据消费）。"""
    execution = (task or {}).get("execution") or {}
    found = []
    for entry in execution.get("verification_runs") or []:
        if not isinstance(entry, dict):
            continue
        item = dict(entry)
        item.setdefault("evidence_ref", entry.get("verification_id"))
        found.append(item)
    return found


def tdd_evidence_problem(evidence, commands, history_commands=None):
    """TDD 证据结构核对（机制稿 §3.5）：五段齐全；红引用历史失败项、绿引用本次通过项，
    且两者覆盖**同一个验证项**（六轮复核 a.5：只核"一次失败 + 一次通过"能被两条无关命令拼凑）。"""
    if not isinstance(evidence, dict):
        return {"reason": "tdd_evidence must be an object"}
    missing = [field for field in TDD_EVIDENCE_FIELDS if not str(evidence.get(field) or "").strip()]
    if missing:
        return {"missing": missing}
    red_ref = str(evidence.get("red_command_ref"))
    green_ref = str(evidence.get("green_command_ref"))
    # 「不同运行」不是「引用串不同」：引用可以是 verification_id（同一验证项的两段运行
    # 本来就同名），红取自历史、绿取自本次，两个集合不相交即已保证是两段运行。
    current = _command_index(commands)
    history = _command_index(history_commands)
    green = [item for item in current.get(green_ref) or [] if item.get("status") == "passed"]
    if not green:
        return {"reason": "green run not found among current passed commands", "green": green_ref}
    red = [item for item in history.get(red_ref) or [] if item.get("status") == "failed"]
    if not red:
        return {"reason": "red run not found among historical failed commands", "red": red_ref,
                "known_history_refs": sorted(history)}
    # 红绿必须覆盖**同一个验证项**：只核"一次失败 + 一次通过"会被互不相关的两条命令拼凑成功
    # （六轮复核 a.5：R22 正例曾以文件内容检查为红、`print(2)` 为绿）。
    green_ids = {str(item.get("verification_id")) for item in green if item.get("verification_id")}
    red_ids = {str(item.get("verification_id")) for item in red if item.get("verification_id")}
    if not green_ids or not red_ids or not (green_ids & red_ids):
        return {"reason": "red and green must cover the same verification (同一验证项先红后绿)",
                "green": green_ref, "red": red_ref,
                "green_verification": sorted(green_ids), "red_verification": sorted(red_ids),
                "exits": ["用同一个 verification_id 先跑出失败、再跑出通过，并分别引用两次运行"]}
    # 同 id 还不够：验证定义（argv/cwd/required/consume_at）改过后，旧的红运行不能证明当前行为
    # （外部报告 b-P1：重规划可保留 id 换命令，旧失败记录会与新的通过记录配成一对）。
    green_digests = {str(item.get("verification_digest")) for item in green
                     if item.get("verification_digest")}
    red_digests = {str(item.get("verification_digest")) for item in red
                   if item.get("verification_digest")}
    if green_digests and not red_digests:
        # 升级前写入的历史运行没有验证定义摘要：**不能证明**它属于当前定义 ⇒ fail-closed。
        # 放行等于让"保留 id、换命令"的旧红测继续给新绿测背书（三轮审查 a-P1）。
        return {"reason": "red run predates verification identity (no verification_digest)"
                          "（无法证明旧失败运行属于当前验证定义，须按当前定义重跑红）",
                "green": green_ref, "red": red_ref,
                "green_digest": sorted(green_digests),
                "exits": ["按当前批准的验证定义重新制造一次失败运行，再用它和本次通过运行配对"]}
    if red_digests and not green_digests:
        return {"reason": "green run lacks verification identity（当前运行的验证定义摘要缺失，记录不完整）",
                "green": green_ref, "red": red_ref,
                "exits": ["重跑 task-check：当前运行必须带 verification_digest"]}
    if green_digests and red_digests and not (green_digests & red_digests):
        return {"reason": "red and green ran under different verification definitions"
                          "（同 id 但命令/工作目录/必需性已变，须按当前定义重新跑红）",
                "green": green_ref, "red": red_ref,
                "green_digest": sorted(green_digests), "red_digest": sorted(red_digests),
                "exits": ["按当前批准的验证定义重新制造一次失败运行，再用它和本次通过运行配对"]}
    return None


def run_check_scope(ctx, task, decisions, review_notes_path, exclusion_entries=None):
    """Check 的**锁内准备段**：范围核对、知识兜底、锚点固定（机制稿 §3.5 ①②）。

    这一段只读文件与记录，**不执行任何外部命令**——长操作留给 `run_check_execute()` 在锁外跑
    （机制稿 §4.1「长操作不长期持 OS 锁」）。返回的 state 是后面两段的唯一输入。
    """
    # ① 范围核对
    receipts = _receipts(ctx)
    exclusion_records = []
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    # 人对外来改动的排除（本次声明给出时消费；记录进任务，摘要变化即失效）
    if exclusion_entries:
        new_records, problems = scope.exclusion_records(ctx.root, classified, exclusion_entries)
        if problems:
            raise CheckError("WF_SEMANTIC_DECISION",
                             {"problems": problems,
                              "exits": ["只排除未归属未提交的路径；属本任务的路径在批准触碰面内直接计入交付，"
                                        "已提交的历史改动才用 task-attribute --commit <sha> 裁决归属"]})
        # 排除声明是**人的决定**：准备段先落到内存态、由 state 带到定稿段重放（六轮修复让定稿段
        # 以盘上记录为准，重放是唯一不漏的接法——只写内存态会在重读时丢掉，且前后分类不一致）。
        scope.persist_exclusions(task, new_records)
        exclusion_records = list(new_records)
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
                              exits=["只读核对记录锚点（wf inspect / status）后由人裁决",
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
        # 出口按对象形态条件化（2026-11-27 人裁：§7 条件式全序列）：
        # d 只报命中批准触碰面的路径（"回 Plan 纳触碰面"是空操作）；`handoff.wip` 只由普通任务的
        # stop 与 rework 普通分支写入，所以持有方必然是普通任务、按 stop 的 choice 处置；
        # 报告方若为实例步骤任务，`stop` 不可用，只能 `run pause`→`writer release`。
        # 形态按"在途实例"判：异常终止实例的保留任务按 task 绑定，出口用普通任务支
        # （run pause/resume 对已终态实例必拒；第十四轮复审 F5）。
        run_record = None
        try:
            from . import runs as runs_mod2

            run_record = runs_mod2.load_run(ctx.root, task.get("run_id")) if task.get("run_id") else None
        except Exception:
            run_record = None
        # 实例记录缺失：与 `cli.wip_blockers` 同口径报 history，而不是给一条必失败的 d 档出口
        # （2026-11-28 人裁 §46）。
        if task.get("run_id") and not isinstance(run_record, dict):
            raise CheckError("WF_HISTORY_UNRESOLVED",
                             {"reason": "run record missing for the task's instance",
                              "run_id": task.get("run_id"),
                              "exits": ["先恢复/补齐实例记录（`wf repair`）后重试",
                                        "或由人确认旧写者已停止后按 §5.5 核对工作区与记录"]})
        # 出口的可执行性由**会话绑定形态**决定（第二十四轮 F24-3）：run 绑定的会话只能用
        # `run pause`→`writer release`；task 绑定的会话只能用 `stop`/`task-pause`。任务形态
        # （run_id / sequence_changes）只作关联事实，不能替代绑定事实。
        bound_kind = None
        try:
            key = ctx.key(required=False) if hasattr(ctx, "key") else None
            if key:
                from . import session as session_mod3

                bound = session_mod3.load_binding(ctx.root, key)
                if isinstance(bound, dict):
                    bound_kind = (bound.get("object") or {}).get("kind")
        except Exception:
            bound_kind = None
        is_instance = bound_kind == "run"
        if bound_kind is None:
            is_instance = bool(task.get("run_id")) and (not isinstance(run_record, dict)
                                                        or run_record.get("terminal") is None)
        if bound_kind is None and not is_instance:
            # 受控返工 R 不写 run_id，但经 `sequence_changes` 属于在途实例（第二十三轮 F1）：
            # 形态必须按"是否属于在途实例"判，否则 run 绑定的会话会拿到 stop 出口（必报 BINDING_MISMATCH）。
            try:
                from . import runs as runs_mod3
                from . import tasks as tasks_mod3

                for _rid, run in runs_mod3.iter_runs(ctx.root):
                    if not isinstance(run, dict) or run.get("terminal") is not None:
                        continue
                    if tasks_mod3._task_in_run(task, task.get("id"), run.get("id"), run, ctx.root):
                        is_instance = True
                        break
            except Exception:
                pass
        report_side = ("本任务先 `run pause`→`writer release`（实例任务不支持 `stop`）；其自身未提交交付"
                       "由人在 Git 层处置（提交/反向修正）后用 `task-attribute` 裁决归属，或另立维护任务处理"
                       "（实例内提交入口登记为后续能力）"
                       if is_instance else
                       "本任务先处置自身未提交交付：`stop` 可用，但 subject 只列本任务 e 档路径、"
                       "choice 取 `commit`（需提交授权）/`reverse`/`transfer`，不得 `keep`、"
                       "不得把争抢路径写进 subject（它一并完成暂停与释放）；无自身交付要处置时用"
                       " `task-pause`→`writer release`")
        resume_side = ("`writer acquire` → `run resume` → `task-resume` → 重跑 task-check"
                       if is_instance else
                       "`writer acquire` → `task-resume` → 重跑 task-check")
        raise CheckError("WF_SCOPE_UNRESOLVED",
                         dict(scope_facts, ambiguous_ownership=buckets["d"],
                              cross_task_claims=classified.get("conflicts") or [],
                              reason="paths claimed by another active task as un-disposed WIP",
                              exits=[report_side,
                                     "持有该登记的任务会话处置该路径：`stop` 的 choice 从 `commit`（需人提交授权）/"
                                     "`transfer`（承接方须已批准且覆盖该路径）/`reverse` 中选——`keep` 会重新登记"
                                     "保留 WIP 并挡住承接方",
                                     resume_side,
                                     "由人裁决归属并留痕（`judgments add` kind=归属，`outcome=applied` 只留痕；"
                                     "`escalated` 会进待决并在归档口阻断）：裁决只决定由谁处置，"
                                     "仍走上一出口把该路径移出登记",
                                     "写权记录本身残留（旧写者已停止）时由人走 `wf repair` 核写者后再重试；"
                                     "WIP 登记残留仍须按上一出口处置"]))
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
                 "对未核实的 spec 用 `spec --file <路径>` 完成读取留痕，或用 verify resolve 处置",
                 "到期/待核项按 `verify resolve` 或重新核实后重入 Check"]
        raise CheckError("WF_SPEC_INCOMPLETE",
                         dict(scope_facts, spec=coverage, missing=missing_paths,
                              missing_curation=coverage.get("missing_curation"),
                              unresolved=coverage.get("unresolved"),
                              period_problems=coverage.get("period_problems"), exits=exits))

    scan_before = fingerprint.items(ctx.root, object_paths(ctx, task))
    # W2-2：Check 流程把已算分类传给锚点计算（与 delivery_set 同型），
    # 不在 anchor_parts 里再扫一轮；classified 变量沿用本函数 ① 段的结果。
    anchor, parts = current_anchor(ctx, task, classified=classified)
    plan = task.get("plan") or {}
    started = records.now_str()      # 本次 Check 的起点（`check.started_at`），供两段共用

    # ①''  实例步骤契约：定义里声明的必做动作/步骤内人判点/验证来源必须有兑现（十轮收敛项）
    contract = check_step_contract(ctx, task, plan, decisions)
    if contract["problems"]:
        raise CheckError("WF_SEMANTIC_DECISION", dict(contract))

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
        # 本次 Check 新登记的排除声明：定稿段重读任务记录后按它重放（见 `cmd_task_check` ③段）
        "exclusion_records": exclusion_records,
        # 动作结果由决定派生：定稿段重读记录后按同一份决定重放（与排除声明同型）
        "step_contract": contract,
    }


ACTION_RESULT_FIELD = "result"


def check_step_contract(ctx, task, plan, decisions):
    """实例步骤契约的兑现核对（唯一实现）：必做动作、步骤内人判点、声明验证。

    只核**声明是否被兑现**，不判业务内容：动作"做没做完"由 AI 给出结论（`--decision` 的
    `action_result` 域），人判点由人给结论，验证声明要求同 id 出现在**已批准 plan** 里。
    非实例任务（无 `execution.step`）直接通过——不给普通任务新增门禁。
    """
    from . import decisions as decisions_mod

    execution = task.get("execution") or {}
    step = execution.get("step") or {}
    if not step:
        return {"problems": [], "action_results": [], "human_points": [], "applied": []}
    approved_ids = {str(item.get("id")) for item in plan.get("verifications") or []
                    if isinstance(item, dict) and item.get("id")}
    action_results, pending_actions, applied = [], [], []
    for entry in execution.get("actions") or []:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            continue
        decision = _action_decision(decisions, entry["id"])
        result = None
        if decision is not None:
            normalized = decisions_mod.canonical("action_result", decision.get("choice"))
            if normalized is None:
                pending_actions.append({"id": entry["id"], "reason": "decision choice is not registered",
                                        "choice": decision.get("choice"),
                                        "accepted": list(decisions_mod.domain("action_result"))})
                continue
            result = normalized
            action_results.append({"id": entry["id"], "result": result,
                                   "decision": {"choice": decision.get("choice"),
                                                "why": decision.get("reason"),
                                                "by": decision.get("by") or decision.get("source"),
                                                "at": decision.get("at")}})
            applied.append({"id": entry["id"], "result": result})
            continue
        if entry.get("required") and entry.get("result") in ("pending", None):
            pending_actions.append({"id": entry["id"], "text": entry.get("text")})
    missing_points = []
    for point in execution.get("human_points") or []:
        if not isinstance(point, dict) or not isinstance(point.get("id"), str):
            continue
        if not any(_subject_mentions(decision.get("subject"), point["id"]) for decision in decisions or []):
            missing_points.append({"id": point["id"], "question": point.get("question"),
                                   "choices": point.get("choices")})
    missing_verifications = [item for item in execution.get("verifications") or []
                             if isinstance(item, dict) and str(item.get("id")) not in approved_ids]
    problems = []
    exits = []
    if pending_actions:
        problems.append({"kind": "pending_actions", "actions": pending_actions})
        exits.append("对每个必做动作下一条决定：subject 含动作 id、choice=done（已做）或 "
                     "waived（本次不适用，理由写 reason）后重跑 task-check")
    if missing_points:
        problems.append({"kind": "missing_human_points", "points": missing_points})
        exits.append("请人给出步骤内人判结论（subject 含该人判点 id）后带 --decision 重跑 task-check")
    if missing_verifications:
        problems.append({"kind": "declared_verification_not_in_plan",
                         "verifications": missing_verifications,
                         "approved_plan_verifications": sorted(approved_ids)})
        exits.append("回 Plan 把定义声明的验证 id 写进 plan.verifications 并重新批准（tag 同一 id）")
    return {"problems": problems, "exits": exits, "action_results": action_results,
            "human_points": [item.get("id") for item in execution.get("human_points") or []
                             if isinstance(item, dict)],
            "applied": applied, "step": step}


def apply_decisions_to_actions(ctx, task, decisions):
    """把 `action_result` 类决定写进任务记录的内存态（**早于门禁求值**，唯一应用点）。

    `task.work-satisfied` 门禁按 `execution.actions[].result` 判待办，而该结果本身由决定派生：
    若等到 Check 准备段才应用，门禁会先一步把"本次已用决定结掉的动作"报成待办（实测踩到）。
    这里返回契约事实（含 problems），供 Check 准备段与回显共用，不重复推导。
    """
    contract = check_step_contract(ctx, task, task.get("plan") or {}, decisions)
    apply_action_results(task, contract)
    return contract


def apply_action_results(task, contract):
    """把动作结果写回任务记录（定稿段重读后按同一份决定重放；幂等）。"""
    if not contract or not contract.get("action_results"):
        return task
    execution = dict(task.get("execution") or {})
    actions = [dict(item) if isinstance(item, dict) else item
               for item in execution.get("actions") or []]
    by_id = {item["id"]: item for item in contract["action_results"]
             if isinstance(item, dict) and isinstance(item.get("id"), str)}
    for index, entry in enumerate(actions):
        if not isinstance(entry, dict) or entry.get("id") not in by_id:
            continue
        record = by_id[entry["id"]]
        actions[index] = dict(entry, **{ACTION_RESULT_FIELD: record["result"],
                                        "result_decision": record["decision"]})
    execution["actions"] = actions
    task["execution"] = execution
    return task


def _action_decision(decisions, action_id):
    """按动作 id 找决定（`subject` 整词匹配，与 plan-q/步骤 id 同口径）。"""
    for decision in decisions or []:
        if isinstance(decision, dict) and _subject_mentions(decision.get("subject"), action_id):
            return decision
    return None


def _subject_mentions(subject, target):
    """整词覆盖判定（唯一实现在 `decisions.subject_mentions`）。"""
    from . import decisions as decisions_mod

    return decisions_mod.subject_mentions(subject, target)


def run_single_verification(ctx, task, verification_id):
    """单次验证运行（`task-check --run-verification <id>`）：只跑一条、只记一次运行。

    不产生 Check 结论、不动 `check`/锚点：它给的是**一次运行的运行身份**（验证 id + 定义摘要 +
    退出码 + 日志），供 TDD 的红证据消费（此前红证据只能来自整轮 Check，逼 AI 为取证改开发节奏）。
    """
    from . import tasks as tasks_mod

    plan = task.get("plan") or {}
    declared = [item for item in plan.get("verifications") or []
                if isinstance(item, dict) and str(item.get("id")) == str(verification_id)]
    if not declared:
        raise CheckError("WF_SEMANTIC_DECISION",
                         {"reason": "verification id is not in the approved plan",
                          "verification": verification_id,
                          "approved": [item.get("id") for item in plan.get("verifications") or []
                                       if isinstance(item, dict)],
                          "exits": ["用已批准 plan 里的验证 id", "要新增验证：回 Plan 补齐并重新批准"]})
    verification = declared[0]
    invocation = verification.get("invocation") or {}
    task_dir = _task_dir(ctx, task)
    run_at = records.now_str()
    log_dir = os.path.join(task_dir, "run-logs", run_at.replace(":", "").replace(".", ""))
    if invocation.get("kind") == "manual":
        raise CheckError("WF_SEMANTIC_DECISION",
                         {"reason": "manual verification has no command to run",
                          "verification": verification_id,
                          "exits": ["人工验收结论走 task-check --decision（choice=passed/failed）",
                                    "只有命令型验证可以用 --run-verification"]})
    command = _run_argv(ctx, task, verification, log_dir)
    execution = dict(task.get("execution") or {})
    runs = [item for item in execution.get("verification_runs") or [] if isinstance(item, dict)]
    entry = {key: command.get(key) for key in
             ("verification_id", "verification_digest", "invocation", "cwd", "exit_code",
              "status", "started_at", "ended_at", "log", "evidence_ref")}
    entry["at"] = run_at
    runs.append(entry)
    execution["verification_runs"] = runs
    task["execution"] = execution
    return task, entry


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
            from . import tasks as tasks_mod
            commands.append(_manual_command(verification, decisions, anchor, plan,
                                            tasks_mod.normalized_plan_version(task),
                                            (state.get("parts") or {}).get("content_digest")))
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
    # TDD 适用性由**已批准的规划声明**（`plan.tdd_applicability`，进 plan_version）：文档/调查类
    # 对象按独立可观察验证（验收项的命令通过或人判）承担验收，不再强迫造红绿（task-flow 已承诺）。
    tdd_applicability = plan.get("tdd_applicability") or "code"
    history_entries = list(task.get("check_history") or [])
    if task.get("check"):
        history_entries.append(task["check"])  # 本次即将被替换的旧检查同样是历史
    history_commands = [command for entry in history_entries for command in entry.get("commands") or []]
    # 单次验证运行（`task-check --run-verification`）也是历史运行：红证据不必来自整轮 Check
    history_commands.extend(verification_run_commands(task))
    tdd_problem = None
    if plan.get("tdd") and tdd_applicability == "code":
        tdd_problem = tdd_evidence_problem(tdd_evidence, commands, history_commands)
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
    acceptance_results = _acceptance_results(ctx, task, commands, decisions, anchor,
                                             (state.get("parts") or {}).get("content_digest"))
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
        "tdd_applicability": tdd_applicability,
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


def _task_dir(ctx, task):
    from . import tasks as tasks_mod

    return tasks_mod.task_dir(ctx.root, task.get("id"))


def _receipts(ctx):
    from . import tasks as tasks_mod

    return tasks_mod.task_receipts(ctx.root)
