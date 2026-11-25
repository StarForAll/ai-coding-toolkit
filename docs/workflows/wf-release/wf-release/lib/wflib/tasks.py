"""tasks.py — 任务记录、状态迁移与人判输入落点（机制稿 §1.3、§2.2、§2.3、§5.3、§6.4）。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid

from . import actions, codes, config, decisions as decisions_mod, fingerprint, records, scope, session as session_mod, writer as writer_mod
from .paths import join

TASKS_REL = ".wf/tasks"
ARCHIVE_REL = ".wf/tasks/archive"
PLAN_MARKER = "<!-- wf-plan:v1 -->"
PLAN_Q_RE = re.compile(r"^\s*plan-q-(\d+)\s*[：:]")
TASK_ID_RE = re.compile(r"^(\d{4}-[0-9a-f]{32})(?:-(.+))?$")

TASK_OWNED_FIELDS = (
    "schema_version", "id", "revision", "created_at", "updated_at", "write_mark", "action",
    "title", "kind", "status", "phase", "paused", "suspended", "terminal", "archived_at",
    "prerequisites", "rework_of", "successor_id", "run_id", "independent_resume", "plan",
    "entry_snapshot", "baseline_head", "attribution", "check", "check_history", "execution",
    "reviews", "curation", "knowledge", "retrospective", "handoff", "disposition",
    "commit_grants", "finish_decision",
)


class TaskError(Exception):
    def __init__(self, code, facts=None, next_=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}
        self.next = next_


# --------------------------------------------------------------------------
# 目录与记录
# --------------------------------------------------------------------------


def new_task_id():
    return f"{records.utc_now().strftime('%Y')}-{uuid.uuid4().hex}"


def slugify(title: str) -> str:
    """目录名 slug：**只保留 ASCII**（2026-11-07）。

    真实 dogfood 里出现过 `2026-3ef38…-初始化-wf-基线-项目配置与-spec-骨架` 这种中文目录，
    在转录里已经出现乱码、跨工具链也有风险。标题照旧存记录（`task.title`），只是不进路径。
    """
    ascii_only = title.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_only).strip("-")
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return cleaned[:48].strip("-") or "task"


def dir_name(task_id, title):
    return f"{task_id}-{slugify(title)}"


def _task_dirs(root):
    base = join(root, TASKS_REL)
    active = []
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if os.path.isdir(path) and name != "archive":
                active.append(path)
    archived = []
    archive_root = join(root, ARCHIVE_REL)
    if os.path.isdir(archive_root):
        for month in sorted(os.listdir(archive_root)):
            month_dir = os.path.join(archive_root, month)
            if not os.path.isdir(month_dir):
                continue
            for name in sorted(os.listdir(month_dir)):
                path = os.path.join(month_dir, name)
                if os.path.isdir(path):
                    archived.append(path)
    return active, archived


def broken_task_dirs(root):
    """现扫任务目录层级：非空但缺 task.json 的任务目录（不含容器与任务内部子目录）。"""
    found = []
    active = join(root, ".wf/tasks")
    archive = join(active, "archive")
    candidates = []
    if os.path.isdir(active):
        candidates.extend(os.path.join(active, name) for name in os.listdir(active)
                          if name != "archive" and os.path.isdir(os.path.join(active, name)))
    if os.path.isdir(archive):
        # 归档区固定两层：archive/<YYYY-MM>/<task-dir>
        for month in os.listdir(archive):
            month_path = os.path.join(archive, month)
            if not os.path.isdir(month_path):
                continue
            candidates.extend(os.path.join(month_path, name) for name in os.listdir(month_path)
                              if os.path.isdir(os.path.join(month_path, name)))
    for path in candidates:
        if os.path.isfile(os.path.join(path, "task.json")):
            continue
        try:
            entries = os.listdir(path)
        except OSError:
            entries = []
        if entries:
            found.append({"path": path, "entries": sorted(entries)[:5]})
    return found


def locate_task_dirs(root, task_id):
    """完整 id 的全部匹配位置（活动区 + 归档区），供冲突诊断与定位使用。"""
    active, archived = _task_dirs(root)
    matches = []
    for path in active + archived:
        name = os.path.basename(path)
        record_path = os.path.join(path, "task.json")
        # 缺 task.json：**空壳**可忽略（移动中断留下的目录），非空目录则必须报出，
        # 不能静默当成"没有这份记录"（第十六轮复审 F16-6）。
        if not os.path.isfile(record_path):
            # 缺记录：空壳跳过；非空由 `broken_task_dirs(root)` 现扫报告，不在此处抛错
            continue
        if name == task_id or name.startswith(task_id + "-"):
            matches.append(path)
            continue
        if name.startswith(task_id):
            record = records.load_json(record_path)
            if isinstance(record, dict) and record.get("id") == task_id:
                matches.append(path)
    return matches


def task_dir(root, task_id):
    matches = locate_task_dirs(root, task_id)
    if not matches:
        return None
    if len(matches) > 1:
        # 重复记录不得静默取一个：保留双方位置并给诊断出口（设计稿 §5.4）
        raise records.RecordInvalid(
            f"duplicate task records for {task_id}: {[os.path.basename(item) for item in matches]}"
        )
    return matches[0]


def iter_tasks(root):
    active, archived = _task_dirs(root)
    for path in active + archived:
        record = records.load_json(os.path.join(path, "task.json"))
        if isinstance(record, dict):
            yield path, record


def load_task(root, task_id):
    path = task_dir(root, task_id)
    if not path:
        return None
    task = records.load_json(os.path.join(path, "task.json"))
    if isinstance(task, dict) and task.get("id") not in (None, task_id):
        # carries_id：目录名被当 task id 传入时的结构化出口（2026-11-21）——cli 兜底
        # 分支据此给 "改用记录 id <X>" 提示；其余 RecordInvalid 原因不携带该属性。
        error = records.RecordInvalid(
            f"task record {os.path.basename(path)} carries id {task.get('id')!r}, expected {task_id!r}"
        )
        error.carries_id = task.get("id")
        raise error
    return task


def save_task(root, path, task):
    task = dict(task)
    task["updated_at"] = records.now_str()
    task["revision"] = int(task.get("revision", 0)) + 1
    records.write_json(os.path.join(path, "task.json"), task)
    return task


def new_task_record(kind, title):
    timestamp = records.now_str()
    return {
        "schema_version": 1,
        "id": new_task_id(),
        "revision": 0,
        "created_at": timestamp,
        "updated_at": timestamp,
        "write_mark": None,
        "action": None,
        "title": title,
        "kind": kind,
        "status": "not_started",
        "phase": "plan",
        "paused": False,
        "suspended": False,
        "terminal": None,
        "archived_at": None,
        "prerequisites": [],
        "rework_of": None,
        "successor_id": None,
        "run_id": None,
        "independent_resume": None,
        "plan": {
            "version": None,
            "artifacts": [],
            "touch_paths": [],
            "acceptance_digest": None,
            "verifications": [],
            "complexity": None,
            "complexity_reasons": [],
            "tdd": None,
            "approval": None,
            "equivalences": [],
        },
        "entry_snapshot": None,
        "baseline_head": None,
        "attribution": {"decisions": [], "inherited": []},
        "check": None,
        "check_history": [],
        "execution": {"required_steps": [], "actions": [], "human_decisions": [],
                      "debug_declarations": [], "workspace_exclusions": []},
        "reviews": {"last_round": 0, "attempts": [], "launches": [], "imported": [], "dispositions": [], "result": None},
        "curation": [],
        "knowledge": None,
        "retrospective": None,
        "handoff": {
            "goal": "",
            "decisions": [],
            "progress": "",
            "next": "",
            "pending": [],
            "ruled_out": [],
            "verification_refs": [],
            "wip": None,
        },
        "disposition": None,
        "commit_grants": [],
        "finish_decision": None,
    }


# --------------------------------------------------------------------------
# PRD 机读块
# --------------------------------------------------------------------------


def read_prd_bytes(root, task):
    """PRD 一次读取：返回 `(text, digest)`，两者出自同一次读（唯一实现）。

    `text` 保留文本模式的换行归一（`\\r\\n`/`\\r` → `\\n`），解析侧行为不变；`digest` 按
    **磁盘原始字节**计。`task-approve --draft` 预填的 `object_digest`、正式批准、机械修订、
    replan 都取这一个值——此前草稿/机械修订按原始字节、正式批准按文本重编码，CRLF 的 PRD
    会得到两个摘要，人批准完才发现绑定失败（首轮 dogfood 的直接复发路径）。
    单次读还有一层：解析与摘要不再各读一遍，同一份内容不会在两次读之间被拆开。
    """
    path = task_dir(root, task.get("id"))
    if not path:
        return None, None
    try:
        with open(os.path.join(path, "prd.md"), "rb") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return None, None
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return text, "sha256:" + records.sha256_hex(raw)


def read_prd(root, task):
    return read_prd_bytes(root, task)[0]


def prd_digest(root, task):
    """当前 PRD 的内容摘要（与 `read_prd` 同一读数）。"""
    return read_prd_bytes(root, task)[1]


def parse_plan_block(text):
    if text is None:
        return None, ["PRD missing"]
    occurrences = text.count(PLAN_MARKER)
    if occurrences == 0:
        return None, ["wf-plan block missing"]
    if occurrences > 1:
        return None, ["wf-plan block duplicated"]
    tail = text.split(PLAN_MARKER, 1)[1]
    fence = tail.find("```json")
    if fence < 0:
        return None, ["wf-plan block has no json fence"]
    start = fence + len("```json")
    end = tail.find("```", start)
    if end < 0:
        return None, ["wf-plan json fence not closed"]
    try:
        block = records.loads(tail[start:end])
    except records.RecordInvalid as exc:
        return None, [f"wf-plan block invalid: {exc}"]
    if not isinstance(block, dict):
        return None, ["wf-plan block must be a JSON object"]
    errors = validate_plan_block(block)
    return (None, errors) if errors else (block, [])


def validate_plan_block(block):
    errors = []
    if block.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    touch_paths = block.get("touch_paths")
    if not isinstance(touch_paths, list) or any(not isinstance(item, str) for item in touch_paths):
        errors.append("touch_paths must be a string array")
    acceptance = block.get("acceptance")
    verifications = block.get("verifications")
    if not isinstance(acceptance, list) or not acceptance:
        errors.append("acceptance must be a non-empty array")
    if not isinstance(verifications, list):
        errors.append("verifications must be an array")
        return errors
    seen_verifications = set()
    for item in verifications:
        if not isinstance(item, dict):
            errors.append("verification entry must be an object")
            continue
        vid = item.get("id")
        if not isinstance(vid, str) or not vid:
            errors.append("verification id missing")
            continue
        if vid in seen_verifications:
            errors.append(f"duplicate verification id: {vid}")
        seen_verifications.add(vid)
        invocation = item.get("invocation")
        if not isinstance(invocation, dict) or invocation.get("kind") not in ("argv", "manual"):
            errors.append(f"verification {vid}: invocation kind must be argv|manual")
        elif invocation.get("kind") == "argv":
            argv = invocation.get("argv")
            if not isinstance(argv, list) or not argv or any(not isinstance(token, str) for token in argv):
                errors.append(f"verification {vid}: argv must be a non-empty string array")
        else:
            if not invocation.get("criterion"):
                errors.append(f"verification {vid}: manual criterion missing")
        cwd = item.get("cwd", ".")
        if cwd != ".":
            try:
                from . import paths as paths_mod

                paths_mod.normalize(cwd)
            except Exception:
                errors.append(f"verification {vid}: cwd is not a safe project-relative path")
        if item.get("consume_at") not in ("start", "check", "finish"):
            errors.append(f"verification {vid}: consume_at must be start/check/finish")
        if not isinstance(item.get("required", True), bool):
            errors.append(f"verification {vid}: required must be boolean")
    seen_acceptance = set()
    for item in acceptance or []:
        if not isinstance(item, dict):
            errors.append("acceptance entry must be an object")
            continue
        aid = item.get("id")
        if not isinstance(aid, str) or not aid:
            errors.append("acceptance id missing")
            continue
        if aid in seen_acceptance:
            errors.append(f"duplicate acceptance id: {aid}")
        seen_acceptance.add(aid)
        if not item.get("statement"):
            errors.append(f"acceptance {aid}: statement missing")
        refs = item.get("verification_ids")
        if not isinstance(refs, list):
            errors.append(f"acceptance {aid}: verification_ids must be an array")
            continue
        for ref in refs:
            if ref not in seen_verifications:
                errors.append(f"acceptance {aid}: unknown verification id {ref}")
    return errors


def extract_plan_questions(text):
    """PRD 正文的 `plan-q-<n>：` 起始行（排除代码围栏与引用块）。"""
    found = []
    if not text:
        return found
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.lstrip().startswith(">"):
            continue
        match = PLAN_Q_RE.match(line)
        if match:
            found.append(f"plan-q-{int(match.group(1))}")
    return found


PHASES_STARTED = ("execute", "check", "finish")


def _is_approved_plan(task, root=None):
    """批准是否成立：批准语义 + 规划版本 + **当前 PRD 仍对应批准版本**（含等价链）。

    只查"非空 choice"会把失效批准、断裂等价链都当成已批准（第九轮 N9-2、第十轮 N10-1）。
    给了 root 时按门禁同一判据复核：当前 PRD 重算版本必须命中批准版本或等价链。
    """
    plan = task.get("plan") or {}
    approval = plan.get("approval")
    if not isinstance(approval, dict) or not approval:
        return False
    approved = plan.get("approved_version") or plan.get("version")
    if not approved:
        return False
    choice = approval.get("choice")
    inner = approval.get("decision")
    if choice not in APPROVE_CHOICES and not (isinstance(inner, dict)
                                              and inner.get("choice") in APPROVE_CHOICES):
        return False
    if root is None:
        return True
    # 读不到 PRD 就是无法证明"当前 PRD 仍对应批准版本"：按未批准处理（第十一轮复审 N11-2）。
    # 记录完整性另由 check/inspect 报，不在这里放行。
    directory = task_dir(root, task.get("id")) if task.get("id") else None
    if not directory or not os.path.isfile(os.path.join(directory, "prd.md")):
        return False
    current = current_plan_version(root, task)
    if isinstance(current, dict) and "error" in current:
        return False
    version = (current or {}).get("version")
    if version == approved:
        return True
    # 机械修订等价链：沿 `equivalences`（old_version → new_version）多跳归一到批准版本
    probe = dict(task)
    probe["plan"] = dict(plan, version=version)
    return normalized_plan_version(probe) == approved


def _normalized_paths(items):
    """按批准侧的同一规则规范化（`pkg//**` → `pkg/**`），再做去重。"""
    from . import paths as paths_mod

    normalized = []
    for item in items:
        try:
            normalized.append(paths_mod.validate_glob(item))
        except Exception:  # noqa: BLE001 — 非法写法保留原样，由校验侧报原因码
            normalized.append(item)
    return normalized


def _dedupe_paths(items):
    """按原顺序去重（机制稿 §2.3：快照保存规范化后的触碰面）。"""
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def approved_touch_paths(task):
    """当前批准触碰面（机制稿 §2.3）：以 entry_snapshot 为准，未开工才回退 plan。

    三态判定按**是否已开工**分流，而不是按"快照是否为 dict"：
    - 未开工（phase 仍在 plan 且没有 baseline_head / entry_snapshot 键）：回退 `plan.touch_paths`；
    - 已开工（进入 execute/check/finish，或已固定 baseline_head，或已有 entry_snapshot 键）：
      快照必须是对象且带 `touch_paths`；**空数组合法**，缺失/类型不符一律 `WF_RECORD_INVALID`，
      不回退可变 plan（2026-11-05 第七轮复审 F7-1）。
    """
    snapshot = task.get("entry_snapshot")
    started = task.get("phase") in PHASES_STARTED or bool(task.get("baseline_head"))
    if snapshot is None and not started:
        # 未开工：记录默认就带 `entry_snapshot: null`，此时才允许回退 plan
        return list((task.get("plan") or {}).get("touch_paths") or [])
    if not isinstance(snapshot, dict):
        raise TaskError("WF_RECORD_INVALID",
                        {"reason": "started task requires an entry_snapshot object",
                         "task": task.get("id"), "entry_snapshot": snapshot})
    if "touch_paths" not in snapshot:
        raise TaskError("WF_RECORD_INVALID",
                        {"reason": "entry_snapshot lacks touch_paths", "task": task.get("id")})
    paths = snapshot.get("touch_paths")
    if not isinstance(paths, list):
        raise TaskError("WF_RECORD_INVALID",
                        {"reason": "entry_snapshot.touch_paths must be a list",
                         "task": task.get("id"), "touch_paths": paths})
    return list(paths)


def question_errors(questions):
    errors = []
    seen = set()
    for item in questions:
        if item in seen:
            errors.append(f"duplicate question id: {item}")
        seen.add(item)
    numbers = sorted(int(item.split("-")[-1]) for item in questions)
    for index, number in enumerate(numbers, start=1):
        if number != index:
            errors.append("plan-q numbering must start at 1 and be contiguous")
            break
    return errors


def plan_questions(root, task):
    """从 PRD 正文提取 `plan-q-<n>` 全集（排除围栏与引用块）。"""
    return extract_plan_questions(_prd_text(root, task))


def unanswered_plan_questions(root, task, decisions=None):
    if decisions is None:
        decisions = (task.get("execution") or {}).get("human_decisions") or []
    # 整词匹配（与 `check._decision_covers` 同款）：`plan-q-1` 不得被 `plan-q-10` 的答复覆盖
    import re as _re

    # 整词匹配：`plan-q-1` 不得被 `plan-q-10` 覆盖，但允许 `plan-q-1：说明` 这种带后缀写法
    answered = set()
    for decision in decisions:
        subject = decision.get("subject", "")
        text = " ".join(str(item) for item in subject) if isinstance(subject, list) else str(subject or "")
        answered.update(f"plan-q-{number}" for number in _re.findall(r"(?<!\d)plan-q-(\d+)(?!\d)", text))
    return [question for question in plan_questions(root, task)
            if question.split("-")[-1] not in {item.split("-")[-1] for item in answered}]




# 取值域只在 `wflib/decisions.py` 登记（实现稿 §2.3.11 ①）；这里只做别名，不另写元组。
MECHANICAL_REVISION = decisions_mod.domain("mechanical_revision")[0]
APPROVE_CHOICES = decisions_mod.domain("plan_approval")
# 设计稿 §4.3 的四个分级条件；机制稿 §2.3 要求逐项保存 true/false/unknown
# 键名与批准入口的 complexity_conditions 一致（设计稿 §4.3 四项）
COMPLEXITY_CONDITIONS = ("governance", "contract", "acceptance", "scope")

# 决定文件里的「人已确认项」注册表（设计稿 §4.3/§4.4：复杂度与 TDD 由人确认并写入批准记录）。
# 扩展方式：新增一项只需在此登记 {键: 校验函数}，消费点用 plan_decision.get(键) 取值；
# **未登记的键不会被丢弃**——原样记入 plan.human_inputs 并产生 unconfirmed_keys 警告，
# 这样"新的人判项"不会因为代码没跟上而静默消失（可扩展性的关键约束）。
HUMAN_PLAN_KEYS = {
    "complexity": lambda value: value in ("light", "complex"),
    "tdd": lambda value: isinstance(value, bool),
    "downgrade": lambda value: isinstance(value, dict) and bool(value.get("reason")) and bool(value.get("evidence")),
}


def normalized_plan_version(task):
    """沿 equivalences 等价链把当前 plan.version 归一到既有批准版本（机制稿 §1.3）。"""
    plan = task.get("plan") or {}
    version = plan.get("version")
    approved = plan.get("approved_version")
    if not version or not approved or version == approved:
        return version
    links = {}
    for item in plan.get("equivalences") or []:
        if isinstance(item, dict) and item.get("new_version"):
            links[item["new_version"]] = item
    current = version
    seen = set()
    while current != approved:
        if current in seen:
            return version
        seen.add(current)
        link = links.get(current)
        if not link:
            return version
        decision = link.get("decision")
        if not isinstance(decision, dict) or decision.get("choice") != MECHANICAL_REVISION:
            return version
        current = link.get("old_version")
    return approved


COMPLEX_ARTIFACTS = ("design.md", "implement.md")


def complex_artifact_problems(root, task, complexity):
    """复杂任务须有 design/implement 且无未填占位（设计稿 §4.2、§4.3；机制稿 §2.3）。"""
    if complexity != "complex":
        return []
    from . import templates as templates_mod

    directory = task_dir(root, task.get("id"))
    problems = []
    for name in COMPLEX_ARTIFACTS:
        absolute = os.path.join(directory, name)
        if not os.path.isfile(absolute):
            problems.append({"artifact": name, "reason": "missing"})
            continue
        with open(absolute, "r", encoding="utf-8") as handle:
            text = handle.read()
        if not text.strip():
            problems.append({"artifact": name, "reason": "empty"})
            continue
        # 只有标题行的产物同样算未填（标题也是占位项）
        body = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if not body:
            problems.append({"artifact": name, "reason": "empty body"})
            continue
        markers = templates_mod.find_markers(text)
        if markers:
            problems.append({"artifact": name, "reason": "unfilled placeholders",
                             "fields": sorted({field for field, _offset in markers})})
        values = templates_mod.find_value_markers(text)
        if values:
            problems.append({"artifact": name, "reason": "unfilled values", "count": len(values)})
    return problems


def artifact_drift(root, task, declared):
    """决定绑定的规划产物与当前是否不同（未携带 `artifacts` 的旧决定返回空）。

    两侧都核：声明过的路径变了/没了算漂移；**当前存在却没被声明**的也算——规划集在草稿与
    批准之间从 {prd} 长成 {prd,design,implement} 时，新产物同样是人没看过的。
    """
    if not isinstance(declared, dict) or not declared:
        return []
    current = {item["path"]: item["digest"] for item in artifact_digests(root, task)}
    drift = [{"path": path, "declared": digest, "current": current.get(path)}
             for path, digest in sorted(declared.items()) if current.get(path) != digest]
    drift += [{"path": path, "declared": None, "current": digest}
              for path, digest in sorted(current.items()) if path not in declared]
    return drift


def artifact_digests(root, task):
    path = task_dir(root, task.get("id"))
    if not path:
        # 记录尚未落盘（构造中的迁移/夹具）时没有可核工件，返回空集而不是崩在 join(None)
        return []
    entries = []
    for name in ("prd.md", "design.md", "implement.md"):
        absolute = os.path.join(path, name)
        if os.path.isfile(absolute):
            relative = os.path.relpath(absolute, str(root)).replace(os.sep, "/")
            entries.append({"path": relative, "digest": records.file_digest(absolute)})
    return sorted(entries, key=lambda item: item["path"].encode("utf-8"))


def compute_plan_version(root, task, plan_block, complexity, complexity_reasons, tdd):
    payload = {
        "artifact_digests": artifact_digests(root, task),
        "plan_block": plan_block,
        "complexity": complexity,
        "complexity_reasons": complexity_reasons,
        "tdd": tdd,
    }
    return records.H("wf-plan-v1", payload)


def current_plan_version(root, task):
    text = read_prd(root, task)
    block, errors = parse_plan_block(text)
    if errors:
        return {"error": ("WF_TEMPLATE_INCOMPLETE", {"problems": errors})}
    # 与批准侧同一规范化：`pkg//**` 之类的合法写法在批准时被规范化，
    # 重算若用原始块就会与 plan.version 永久失配（2026-11-05 第十轮复审 N10-3）。
    from . import paths as paths_mod

    try:
        block = dict(block)
        block["touch_paths"] = [paths_mod.validate_glob(item) for item in block.get("touch_paths") or []]
    except Exception:  # noqa: BLE001 — 规范化失败按原样参与哈希，由校验侧给出原因码
        pass
    plan = task.get("plan") or {}
    # 哈希域只含条件条目：降级条目是批准后追加事实，重算时必须剔除（机制稿 §1.1）
    conditions = [item for item in plan.get("complexity_reasons") or [] if not item.get("downgrade")]
    version = compute_plan_version(root, task, block, plan.get("complexity"), conditions, plan.get("tdd"))
    return {"version": version, "block": block}


# --------------------------------------------------------------------------
# 门禁事实（供 gates.py 调用）
# --------------------------------------------------------------------------


# 提交对象不可变：按 (root, sha) 缓存整棵树，按 (root, sha, path) 缓存内容摘要。
# 之前是"每路径 2 次 git"，一次 Check 能起 500+ 子进程；批量化后降到每提交 1–2 次。
_TREE_CACHE = {}
_BLOB_CACHE = {}


def _tree_entries(root, sha):
    key = (str(root), sha)
    if key in _TREE_CACHE:
        return _TREE_CACHE[key]
    proc = subprocess.run(["git", "-c", "core.quotePath=false", "ls-tree", "-r", "-z", "--full-tree", sha],
                          cwd=str(root), capture_output=True, check=False)
    entries = {}
    if proc.returncode == 0:
        for record in proc.stdout.split(b"\0"):
            if not record:
                continue
            meta, _, raw_path = record.partition(b"\t")
            parts = meta.split(b" ")
            if len(parts) < 3:
                continue
            entries[raw_path.decode("utf-8", "surrogateescape")] = (parts[0].decode(), parts[2].decode())
    _TREE_CACHE[key] = entries
    return entries


def _blob_digest(root, sha, blob):
    key = (str(root), sha, blob)
    if key in _BLOB_CACHE:
        return _BLOB_CACHE[key]
    proc = subprocess.run(["git", "-c", "core.quotePath=false", "cat-file", "blob", blob],
                          cwd=str(root), capture_output=True, check=False)
    digest = "sha256:" + hashlib.sha256(proc.stdout).hexdigest() if proc.returncode == 0 else None
    _BLOB_CACHE[key] = digest
    return digest


def _committed_fingerprint(root, sha, path):
    """按候选提交树重建该路径的完整指纹：存在/删除、类型、可执行位、内容摘要（机制稿 §1.4）。"""
    entry = _tree_entries(root, sha).get(path)
    if entry is None:
        return {"path": path, "exists": False, "kind": "deleted", "executable": False, "digest": None}
    mode, blob = entry
    digest = _blob_digest(root, sha, blob)
    if digest is None:
        return {"path": path, "exists": False, "kind": "deleted", "executable": False, "digest": None}
    if mode == "120000":
        kind, executable = "symlink", False
    else:
        kind, executable = "file", bool(int(mode, 8) & 0o111)
    return {"path": path, "exists": True, "kind": kind, "executable": executable, "digest": digest}


def _fp_matches(expected, actual):
    """登记项与实际状态比较：完整指纹按字段比；纯摘要只比 digest；空对象一律不成立。"""
    if expected is None:
        return actual.get("exists") is False
    if isinstance(expected, str):
        return bool(expected) and actual.get("digest") == expected
    if not isinstance(expected, dict) or not expected:
        return False  # 空对象没有任何可比对事实，不能无条件匹配
    if not any(field in expected for field in ("exists", "kind", "executable", "digest")):
        return False
    for field in ("exists", "kind", "executable", "digest"):
        if field in expected and expected.get(field) != actual.get(field):
            return False
    return True


def _head_matches_changes(root, wanted):
    """HEAD 树里这些路径的内容摘要是否等于登记的终态（无下界提交时的"已提交"判据）。"""
    head = scope.head(root)
    if not head:
        return False
    for path, after in wanted:
        digest = after.get("digest") if isinstance(after, dict) else after
        if not isinstance(digest, str) or not digest:
            return False
        proc = subprocess.run(["git", "-c", "safe.directory=*", "show", f"{head}:{path}"],
                              cwd=root, capture_output=True)
        if proc.returncode != 0:
            return False
        if "sha256:" + records.sha256_hex(proc.stdout) != digest:
            return False
    return True


def _changes_by_path(changes):
    """按路径稳定排序的 [(path, after)]：字典列表不能直接比较（机制稿 §4.5）。"""
    pairs = []
    for change in changes or []:
        if isinstance(change, dict) and change.get("path"):
            pairs.append((change["path"], change.get("after")))
    return sorted(pairs, key=lambda item: item[0])


def maintenance_persisted_probe(root):
    """可达提交查证：下界之后存在一条提交，其树含该回执且各登记路径的树状态等于登记终态（机制稿 §4.5）。"""
    def probe(entry):
        lower = entry.get("head_before")
        operation = entry.get("operation")
        wanted = _changes_by_path(entry.get("changes"))
        if not wanted or not operation:
            return False
        if not lower:
            # 部署发生在首个提交之前（新仓库）时没有"下界提交"可查：按 **HEAD 树内容**
            # 逐路径核对登记终态——路径未被跟踪或内容不符即未持久化，仍不放行。
            # 只在回执本身声明为 `applied_pending_commit` 时才这样核：状态不明的坏回执
            # 一律留在 pending_check 交人（R60 的"不可核回执"判据）。
            if entry.get("result") != "applied_pending_commit":
                return False
            return _head_matches_changes(root, wanted)
        if not scope.is_ancestor(root, lower):
            return False
        for sha in scope.commits_since(root, lower) or []:
            # 回执账本在**提交层**（`.wf/install/maintenance.jsonl`，项目数据），
            # 不是运行态的 writer.json——后者被忽略后读不到，探针会永远 pending（实测 r59–r61）。
            from . import maintenance as maintenance_mod

            blob = _committed_text(root, sha, maintenance_mod.JOURNAL_REL)
            if blob is None:
                continue
            entries, _problems = maintenance_mod.parse(blob)
            matched = maintenance_mod.find(entries, operation)
            if matched is None:
                continue
            if [path for path, _after in _changes_by_path(matched.get("changes"))] != \
                    [path for path, _after in wanted]:
                continue
            # 逐项按提交树重建完整状态后比较，不看 diff、不只看摘要
            if all(_fp_matches(after, _committed_fingerprint(root, sha, path)) for path, after in wanted):
                return True
        return False

    return probe


def maintenance_disposition_probe(root):
    """处置结案的事实核验（机制稿 §4.5）：提交可达 / 反向修正到位 / 承接任务已批准且覆盖路径。"""

    def probe(entry):
        disposition = entry.get("disposition") or {}
        kind = disposition.get("kind")
        evidence = disposition.get("evidence") or {}
        changes = [change for change in entry.get("changes") or [] if isinstance(change, dict)]
        paths = [change.get("path") for change in changes if change.get("path")]
        if kind == "commit":
            commit = evidence.get("commit") if isinstance(evidence, dict) else None
            usable_commit = isinstance(commit, str) and bool(commit) and scope.is_ancestor(root, commit)
            if not paths:
                return usable_commit or bool(maintenance_persisted_probe(root)(entry))
            # 与"已持久化"用**同一份证据**：账本已入提交且各路径终态一致时，处置同样是事实可核的。
            # 否则两种判据会打架（一个说已入账、另一个说没见过提交），实测 r61 就是卡在这里。
            if bool(maintenance_persisted_probe(root)(entry)):
                return True
            for change in entry.get("changes") or []:
                if not isinstance(change, dict) or not change.get("path"):
                    continue
                path = change["path"]
                if usable_commit and _fp_matches(change.get("after"),
                                                 _committed_fingerprint(root, commit, path)):
                    continue
                # 提交可能被拆到多个提交：该路径当前已到登记终态且无未提交差异，同样成立
                if _fp_matches(change.get("after"), fingerprint.item(root, path)) \
                        and not scope.git(root, "status", "--porcelain", "--", path)[1].strip():
                    continue
                return False
            return True
        if kind == "reverse":
            for change in changes:
                if not change.get("path"):
                    continue
                # 键缺失 ≠ 显式 null：没有登记前像就无法证明"已反向修正"
                if "before" not in change:
                    return False
                if not _fp_matches(change["before"], fingerprint.item(root, change["path"])):
                    return False
            return True
        if kind == "uninstall":
            # 卸载的可核事实：登记要移除的资产当前都不存在（不依赖 Git 提交，2026-11-06 人裁）
            if not paths:
                return False
            for path in paths:
                if fingerprint.item(root, path).get("exists"):
                    return False
            return True
        if kind == "transfer":
            target = disposition.get("target_task")
            task = load_task(root, target) if target else None
            if not isinstance(task, dict):
                return False
            # 与 stop 的承接核验同判据（2026-11-05 第八轮复审 F8-3）：
            # 1) 有效批准对象——真实批准存的是 Decision 本身（有 choice，没有 `decision` 字段），
            #    旧探针要求 `approval.decision` 会把合法承接判成未结案；
            # 2) 批准面取 entry_snapshot（已开工），不读可变的 plan.touch_paths；
            # 3) 已归档/终止的承接任务不具承接资格。
            if task.get("status") == "archived" or task.get("terminal"):
                return False
            if not _is_approved_plan(task, root):
                return False
            try:
                touch = approved_touch_paths(task)
            except TaskError:
                return False
            from . import paths as paths_mod

            return all(any(paths_mod.match_path(pattern, path) for pattern in touch)
                       for path in paths if path)
        return False

    return probe


def task_receipts(root):
    record = writer_mod.load(root)
    if not record:
        return []
    return writer_mod.receipt_state(record, probe=maintenance_persisted_probe(root),
                                    disposition_probe=maintenance_disposition_probe(root))


def spec_read_state(ctx, task):
    key = ctx.key(required=False)
    if not key:
        return {"complete": False, "reason": "no session envelope", "specs": []}
    sidecar = records.load_json(join(ctx.root, f".wf/.runtime/spec-reads/{key}.json"), None) or {}
    read = {}
    for entry in sidecar.get("specs") or []:
        if isinstance(entry, dict) and entry.get("path"):
            read[entry["path"]] = entry
    required = [entry for entry in (task.get("curation") or []) if not entry.get("released") and entry.get("path")]
    missing = []
    for entry in required:
        record = read.get(entry["path"])
        if not record:
            missing.append({"path": entry["path"], "reason": "not read in this session"})
            continue
        if not record.get("complete"):
            missing.append({"path": entry["path"], "reason": "incomplete read"})
            continue
        digest = records.file_digest(join(ctx.root, entry["path"]))
        if digest != record.get("digest"):
            missing.append({"path": entry["path"], "reason": "content changed since read"})
    return {"complete": not missing, "missing": missing, "specs": sorted(read.keys())}


def spec_loaded_fact(ctx, task):
    state = spec_read_state(ctx, task)
    if state["complete"]:
        return True, None, {"specs": state["specs"]}
    return False, "WF_SPEC_INCOMPLETE", {"missing": state["missing"], "reason": state.get("reason")}


STARTUP_STEPS = (
    ("binding", "绑定与写者"),
    ("record", "记录可解释性"),
    ("candidates", "执行候选唯一性"),
    ("graph", "对象与依赖"),
    ("marker", "写者标记锚点"),
    ("assets", "框架资产可用性"),
    ("workspace", "工作区边界"),
)

# 机制稿 §5.2 的启动固定顺序里，首轮不进入 startup_check 的项：
# ④ 维护写者与本次预览范围的对应（只有维护入口有预览上下文，由维护入口自核）；
# ⑥ 未结束实例的快照/游标/任务归属（实例属第二轮）。
STARTUP_OUT_OF_SCOPE = (
    ("maintenance", "维护写者与预览范围对应：仅维护入口有预览上下文，由该入口自核"),
    ("instances", "未结束实例的快照/游标/任务归属：实例属于第二轮"),
)


def startup_check(ctx, task=None):
    """γ 启动校验的固定序列（机制稿 §5.2 ①–⑩ 的可实现子集）：未知优先于判定。

    只读；返回按序的 findings，每项 status 取 ok/unknown/blocked。
    """
    findings = []
    key = ctx.key(required=False)
    record = ctx.writer()
    if not key:
        findings.append({"step": "binding", "status": "unknown", "reason": "no session envelope"})
    else:
        binding = session_mod.load_binding(ctx.root, key)
        if not binding:
            findings.append({"step": "binding", "status": "unknown", "reason": "no persistent binding"})
        else:
            holder = record.get("holder") or {}
            state = record.get("state")
            if state != "held" or holder.get("id") != key:
                findings.append({"step": "binding", "status": "unknown", "reason": "write rights not held by this session",
                                 "writer_state": state})
            else:
                findings.append({"step": "binding", "status": "ok", "generation": holder.get("generation")})
    if not isinstance(record, dict) or not isinstance(record.get("generation"), int):
        findings.append({"step": "record", "status": "blocked", "reason": "writer record unreadable"})
    else:
        findings.append({"step": "record", "status": "ok"})
    # ③ 执行候选唯一性（机制稿 §5.2 ③）：多候选是记录集不变量破坏，不是写权占用
    try:
        active = [item.get("id") for _path, item in iter_tasks(ctx.root)
                  if item.get("status") == "in_progress"
                  and not item.get("paused") and not item.get("suspended")
                  and (task is None or item.get("id") != task.get("id"))]
    except Exception as exc:  # noqa: BLE001 — 活动记录不可读时以「候选未知」上报
        findings.append({"step": "candidates", "status": "unknown",
                         "code": "WF_HISTORY_UNRESOLVED", "reason": f"active records unreadable: {exc}"})
    else:
        if active:
            findings.append({"step": "candidates", "status": "blocked",
                             "code": "WF_RECORD_INVALID", "others": active})
        else:
            findings.append({"step": "candidates", "status": "ok"})
    if task is not None:
        blockers = dependency_blockers(ctx.root, task)
        findings.append({"step": "graph", "status": "blocked" if blockers else "ok", "unmet": blockers})
        # 机制稿 §5.3 还要求「启动校验通过后」触发空集合复评；首轮只在 archive 侧调用，
        # 这里先留可核事实，第二轮补返工时连启动侧触发一起接上（登记见综合记录）。
        reassessment = _reassess_empty_set(ctx, task.get("id"))
        if reassessment.get("empty"):
            findings.append({"step": "graph", "status": "unknown", "reason": "empty retrospective set pending reassessment",
                             "reassessment": reassessment})
        # ⑧ 写者标记按记录锚点核对（机制稿 §5.2 ⑧）：持有/恢复态必须有可识别的锁标记
        state = record.get("state")
        if state in ("held", "recovering"):
            from . import lock as lock_mod

            mark = None
            try:
                with open(lock_mod.lock_path(ctx.root), "r", encoding="utf-8") as handle:
                    mark = (handle.readline() or "").strip()
            except OSError:
                mark = None
            if mark != "wf-lock-v1":
                findings.append({"step": "marker", "status": "blocked",
                                 "code": "WF_HISTORY_UNRESOLVED",
                                 "reason": "lock marker missing or unknown", "marker": mark})
            else:
                findings.append({"step": "marker", "status": "ok"})
        else:
            findings.append({"step": "marker", "status": "ok", "note": "writer idle"})
        # ⑨ 框架资产可用性（机制稿 §5.2 ⑨）：必需资产缺失即报对应入口不可用
        required = (".wf/bin/wf.py", ".wf/bin/repair.py", ".wf/bin/uninstall.py",
                    ".wf/lib/wflib/module_main.py")
        missing = [rel for rel in required if not os.path.isfile(join(ctx.root, rel))]
        if missing:
            findings.append({"step": "assets", "status": "blocked",
                             "code": "WF_CAPABILITY_UNAVAILABLE", "missing": missing})
        else:
            findings.append({"step": "assets", "status": "ok"})
        from . import cli as cli_mod

        foreign = cli_mod.wip_blockers(ctx.root, exclude_id=task.get("id"))
        findings.append({"step": "workspace", "status": "blocked" if foreign else "ok", "blocking": foreign})
    else:
        findings.append({"step": "graph", "status": "unknown", "reason": "no bound object"})
        findings.append({"step": "workspace", "status": "unknown", "reason": "no bound object"})
    order = {name: index for index, (name, _label) in enumerate(STARTUP_STEPS)}
    return sorted(findings, key=lambda item: order.get(item["step"], 99))


def work_satisfied_fact(ctx, task):
    # 统一走批准面判定：快照缺失/损坏即 WF_RECORD_INVALID，不把损坏记录折叠成空批准面（第十二轮复审 M-1）
    try:
        touch_paths = approved_touch_paths(task)
    except TaskError as exc:
        return False, exc.code, exc.facts
    actions_declared = (task.get("execution") or {}).get("actions") or []
    pending = [item for item in actions_declared if item.get("result") in ("pending", None) and item.get("required", True)]
    if pending:
        return False, "WF_SEMANTIC_DECISION", {"pending_actions": pending}
    if not touch_paths:
        # 纯调查也须有可观察成果（机制稿 §11.2）：决策、复盘、curation 或使其 Check 成立
        investigation = bool(task.get("retrospective")) or bool(task.get("curation")) \
            or (task.get("check") or {}).get("result") == "pass"
        if not investigation:
            return False, "WF_CHECK_FAILED", {"reason": "investigation task needs an observable outcome",
                    "exits": ["记录复盘", "策展调查依据的 spec", "先通过 Check"]}
        return True, None, {"mode": "investigation"}
    from . import check as check_mod

    paths = check_mod.object_paths(ctx, task)
    existing = [path for path in paths if os.path.exists(join(ctx.root, path))]
    if not existing:
        # P2-2：纯删除/改名的交付同样成立——触碰路径上有归属本任务的删除/改名事实即可
        receipts = task_receipts(ctx.root)
        removed = [path for path in paths
                   if not os.path.exists(join(ctx.root, path))
                   and _removal_attributed(ctx, path, task, receipts)]
        if removed:
            return True, None, {"mode": "removal", "paths": sorted(removed)}
        return False, "WF_CHECK_FAILED", {"reason": "no delivered artifact found in workspace"}
    return True, None, {"objects": existing}


def pending_delivery_paths(ctx, task):
    """本任务交付面里**未提交**的路径（`delivery_set` ∩ 未提交）。

    `changes-persisted` 与归档预检消费的是同一个集合——只在这里算一次，避免两处各算一套。
    交付集合含已获 `expand` 确认的路径，因此获批的越界改动同样进入待提交面（否则它会被
    归档留在工作区，下一次 Check 变成 c 桶阻断）。
    """
    delivery = scope.delivery_set(ctx.root, task, receipts=task_receipts(ctx.root))
    return sorted(set(delivery["paths"]) & set(scope.uncommitted_paths(ctx.root)))


def commit_grant_paths(task):
    """本任务提交授权（`commit_grants[].subject`）覆盖的路径集合。"""
    granted = []
    for grant in task.get("commit_grants") or []:
        if isinstance(grant, dict):
            granted.extend(_subject_paths(grant.get("subject")))
    return sorted({item for item in granted if item})


def uncovered_commit_paths(pending, granted):
    """待提交路径里没被授权覆盖的那些（唯一口径：完全相等 / 目录前缀 / glob）。"""
    from . import paths as paths_mod

    def covered(item):
        return any(item == grant or item.startswith(grant + "/") or paths_mod.match_path(grant, item)
                   for grant in granted)

    return [item for item in pending if not covered(item)]


def changes_persisted_fact(ctx, task):
    pending = pending_delivery_paths(ctx, task)
    if not pending:
        return True, None, {"paths": []}
    granted = commit_grant_paths(task)
    if not granted:
        return False, "WF_COMMIT_NOT_AUTHORIZED", {"pending_paths": pending}
    uncovered = uncovered_commit_paths(pending, granted)
    if uncovered:
        return False, "WF_WIP_UNRESOLVED", {
            "pending_paths": pending, "uncovered_paths": uncovered, "grants": len(granted)}
    # D1：授权已覆盖全部待提交路径 ⇒ 这一步**由归档动作完成**（业务提交在 archive 内发生）。
    # 报 WIP_UNRESOLVED 会把 AI 推向"先手工提交再归档"，而归档自己就会提交同一批路径。
    return False, "WF_ACTION_INCOMPLETE", {
        "pending_paths": pending, "granted": granted,
        "fulfilled_by": "archive_commit", "resumable": True,
        "exits": ["直接 `wf archive --task <id> --file <提交授权决定>`：归档会提交这些路径并完成本步骤",
                  "不要先手工提交再归档——归档的提交授权已覆盖同一批路径"]}


def archive_precheck(ctx, task):
    """D4 预检（只读）：归档**业务提交之前**就能看到全部确定阻断。

    组成（矩阵 #37）：
    ① `final_gate_nonstep(ctx, task, ignore_action_id=<当前动作>)`（含 ⑥ 的 C3）；
    ② `evaluate(ctx, task, "before_archive", rule_version=…)` 先按 `id` 排除
       `task.changes-persisted`，再取 `status == "missing"` 的条目必须为空
       （`evaluate` 对每个适用步骤都返回条目、`status ∈ {missing, completed, reused, satisfied}`，
       "列表为空"是错的判据）；
    ③ 授权覆盖：本任务的未提交工作 `pending ⊄ 本次提交路径集` → `WF_WIP_UNRESOLVED`。

    **不得只调一次 `final_gate`**：它是顺序短路结构（先跑步骤面，任一步 missing 即返回），
    而预检发生在提交之前 → `changes-persisted` 必 missing → nonstep 十项一次都不会跑。
    返回 `{ok, code, facts, blocking}`；`blocking` 供 `--short` 原样列出"还有哪些确定阻断"。
    """
    from . import gates as gates_mod

    ok, code, facts = gates_mod.final_gate_nonstep(
        ctx, task, ignore_action_id=(task.get("action") or {}).get("id"))
    if not ok:
        return {"ok": False, "code": code, "facts": facts,
                "blocking": [{"stage": "final_gate_nonstep", "code": code, "facts": facts}]}
    findings = gates_mod.evaluate(ctx, task, "before_archive", rule_version=ctx.rule_version())
    missing = [item for item in findings
               if item.get("id") != "task.changes-persisted" and item.get("status") == "missing"]
    if missing:
        return {"ok": False, "code": missing[0].get("code") or "WF_CHECK_FAILED",
                "facts": {"missing": missing, "all": findings},
                "blocking": [{"stage": "steps", "id": item.get("id"), "code": item.get("code"),
                              "facts": item.get("facts")} for item in missing]}
    # 与 `changes_persisted_fact` 同一桶与同一覆盖口径（D1 提取为共享函数）：
    # 提交前存在待提交路径是正常的，只有"授权没覆盖到"才是阻断。
    granted = commit_grant_paths(task)
    pending = pending_delivery_paths(ctx, task)
    uncovered = uncovered_commit_paths(pending, granted)
    if uncovered:
        return {"ok": False, "code": "WF_WIP_UNRESOLVED",
                "facts": {"pending_paths": uncovered, "granted": sorted(set(granted)),
                          "reason": ("尚未提供提交授权：决定文件里需要 choice=commit"
                                     if not granted else "授权未覆盖全部待提交路径")},
                "blocking": [{"stage": "authorization", "code": "WF_WIP_UNRESOLVED",
                              "facts": {"pending_paths": uncovered}}]}
    return {"ok": True, "code": None, "facts": {"steps": findings, "pending": pending}, "blocking": []}


def current_check_anchor(ctx, task):
    from . import check as check_mod

    try:
        anchor, parts = check_mod.current_anchor(ctx, task)
    except check_mod.CheckError as exc:
        return {"error": (exc.code, exc.facts)}
    return {"anchor": anchor, "parts": parts}


# --------------------------------------------------------------------------
# 动作封装
# --------------------------------------------------------------------------


def _owner(holder):
    return writer_mod.owner_ref(holder.get("kind"), holder.get("id"), holder.get("scope"))


def _assertion(ctx, operation, holder, action, evidence_refs=None):
    from . import cli

    return cli._control_assertion(ctx, operation, _owner(holder), action, evidence_refs)


def _start_task_action(ctx, path, task, operation, holder, inputs, steps, targets=None):
    action = actions.new_action(
        operation,
        _owner(holder),
        int(task.get("revision", 0)),
        inputs,
        steps=steps,
        head_before=actions.head_of(ctx.root),
        targets=targets or [{"kind": "task", "id": task.get("id")}],
    )
    task = dict(task)
    task["action"] = action
    save_task(ctx.root, path, task)
    return task, action


def _finish_task_action(ctx, path, task, operation, holder, inputs, action, evidence_refs=None):
    from . import cli

    assertion = _assertion(ctx, operation, holder, action, evidence_refs)
    action = actions.complete(action, summary=operation, control_assertion=assertion)
    task = dict(task)
    task["action"] = action
    task["write_mark"] = {
        "operation": operation,
        "owner": _owner(holder),
        "generation": holder.get("generation"),
        "before_head": action.get("head_before"),
        "changed_fields": sorted(inputs.keys()),
        "action_id": action.get("id"),
        "invocation": {"entry": operation.split(".")[1] if "." in operation else operation,
                       "scope_digest": action.get("inputs_digest")},
    }
    save_task(ctx.root, path, task)
    return task, assertion


def _require_binding(ctx, task_id):
    """日常写入口的绑定核验：对象 + 实例标识（机制稿 §1.4，不只在 start 核一次）。"""
    key = ctx.key()
    binding = session_mod.load_binding(ctx.root, key)
    if not binding:
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "no binding", "session_key": key},
                        next_="由人先用 wf-start 选择对象")
    object_ref = binding.get("object") or {}
    if object_ref.get("id") != task_id:
        raise TaskError("WF_BINDING_MISMATCH", {"bound": object_ref, "requested": task_id})
    _require_instance_match(ctx, binding)
    return binding


def _require_instance_match(ctx, binding):
    """复用 cli 的统一实现：实例标识 + 身份能力状态（机制稿 §1.4）。"""
    from . import cli as cli_mod

    return cli_mod._require_instance_match(ctx, binding)


def _load_or_fail(ctx, task_id):
    task = load_task(ctx.root, task_id)
    if task is None:
        raise TaskError("WF_TARGET_COLLISION", {"reason": "task not found", "task": task_id})
    return task


def _prd_text(root, task):
    return read_prd(root, task) or ""




# --------------------------------------------------------------------------
# 命令：task-new
# --------------------------------------------------------------------------


def cmd_task_new(ctx, args):
    """首次创建：writer 上的**单一 task.create 父动作**（机制稿 §5.1）。

    主记录是 writer 的动作；目标一次固定（writer / task / binding / runtime），
    步骤逐个推进并回写，中断后按原意图续做，不按当前参数重建。
    """
    from . import cli, lock

    kind = args.value("--kind") or "ordinary"
    title = args.value("--title")
    template = args.value("--template")
    if kind not in ("ordinary", "initialize", "bootstrap"):
        raise TaskError("WF_PATH_INVALID", {"reason": "--kind must be ordinary|initialize|bootstrap"})
    if not title:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-new requires --title"})
    if not template:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-new requires --template <tasks template dir>"})
    session = ctx.session()
    key = ctx.key()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise cli.CliError(code, profile_facts, next_="install（已装齐全部平台）后重试")
    with lock.acquire(ctx.root, holder_hint="task-new"):
        record = ctx.writer()
        # 中断恢复优先：writer 上的父动作未结案就按原意图续做，不看当前参数
        pending = _writer_create_intent(record, key)
        if pending is not None:
            return _resume_task_create(ctx, key, session, record, pending)
        bound = session_mod.load_binding(ctx.root, key)
        if bound and (record.get("action") or {}).get("state") != "done":
            # 有绑定但父动作未结案：先续做结案，再给可见成功（R50-04）
            unfinished = _writer_create_intent(record, key)
            if unfinished is not None:
                return _resume_task_create(ctx, key, session, record, unfinished)
        if bound:
            # v42 §4 / dogfood A3：`task-new` 不得把"已绑定的旧任务"当成功返回。
            # 中断后的续做由 writer 上的 `task.create` 父动作承载（上面 `_writer_create_intent`），
            # 不靠一个 `already_completed` 标记；绑定终身，第二对象只能由新会话选择。
            # W2-6：绑定对象已终态时 next_ 与 enable 终态出口同口径（开新对象需新执行边界/
            # 新会话/换新会话标识）——archived 对象没有"continue/bind"可继续。
            _bound_obj = bound.get("object") or {}
            _bound_terminal = False
            if _bound_obj.get("kind") == "task":
                _record_bound = load_task(ctx.root, str(_bound_obj.get("id")))
                _bound_terminal = bool(_record_bound) and _record_bound.get("status") == "archived"
            elif _bound_obj.get("kind") == "run":
                from . import runs as _runs_mod

                _run_bound = _runs_mod.load_run(ctx.root, str(_bound_obj.get("id")))
                _bound_terminal = bool(_run_bound) and _run_bound.get("terminal") is not None
            if _bound_terminal:
                raise TaskError("WF_BINDING_MISMATCH",
                                {"reason": "session already bound (object terminal)",
                                 "object": bound.get("object")},
                                next_="旧对象已终态：开新对象需新执行边界或换新会话"
                                      "（或 `wf enable --new-session` 换新会话标识）")
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "session already bound",
                             "object": bound.get("object")},
                            next_="继续当前对象用 continue/bind；要开新任务请在新会话里选")
        cli.assert_no_foreign_wip(ctx, exclude_id=None)
        # 未完成的父动作不能被任何会话越过（写权空闲不等于没有遗留动作）
        leftover = (record.get("action") or {})
        if leftover.get("kind") == "task.create" and leftover.get("state") != "done":
            raise cli.CliError("WF_WRITER_BUSY",
                               {"reason": "unfinished task.create intent exists",
                                "intent_owner": (record.get("holder") or {}).get("id"),
                                "resume": "由原会话重入 task-new 续做，或走受控恢复"},
                               next_="原会话续做该意图；其他会话不得越过未完成动作")
        if record.get("state") != "idle":
            raise cli.CliError("WF_WRITER_BUSY", {"holder": record.get("holder")})

        task = new_task_record(kind, title)
        task_id = task["id"]
        directory = join(ctx.root, f"{TASKS_REL}/{dir_name(task_id, title)}")
        staging = join(ctx.root, f"{TASKS_REL}/.staging-{task_id}")
        if os.path.exists(directory) or os.path.exists(staging):
            raise cli.CliError("WF_TARGET_COLLISION",
                               {"path": directory if os.path.exists(directory) else staging})
        instance_id = session.get("instance_id") or session_mod.new_instance_id()
        inputs = {"task": task_id, "kind": kind, "title": title, "template": template}
        steps = ["create_dir", "write_record", "acquire_writer", "bind"]
        owner_scope = {"object": {"kind": "task", "id": task_id}, "preparation": None}
        # ① 意图与写权授予**同一次写入**：从此任何中断都能按原意图续做
        updated = writer_mod.acquire(record, kind="session", ident=key, scope=owner_scope,
                                     checkpoint={"step": "task-new", "at": records.now_str()})
        action = actions.new_action("task.create", _owner(updated.get("holder") or {}),
                                    int(updated.get("revision", 0)), inputs,
                                    steps=steps, head_before=actions.head_of(ctx.root),
                                    targets=[{"kind": "writer", "id": "writer"},
                                             {"kind": "task", "id": task_id},
                                             {"kind": "binding", "id": key},
                                             {"kind": "runtime", "id": key},
                                             # 实例标识/模板/标题作为不可变目标固定：重入只按这些值重建
                                             {"kind": "instance", "id": instance_id},
                                             {"kind": "template", "id": template},
                                             {"kind": "title", "id": title},
                                             {"kind": "task-kind", "id": kind}])
        action["steps"] = [{"id": step, "state": "pending"} for step in steps]
        updated = dict(updated)
        updated["action"] = action
        writer_mod.save(ctx.root, updated)

        # ② 逐步推进：每一步都做真实后置断言，缺什么补什么（幂等重放，不整段跳过）
        updated = _run_creation_steps(ctx, key, session, updated, action)

        # ③ 结案：步骤后置 + 目标完整性全部核过才允许 done
        assertion = _finish_writer_action(ctx, updated, "task.create",
                                          [os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
                                           f".wf/session-bindings/{key}.json"])
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": title},
        position_=codes.position(scope="task", phase="plan", task_id=task_id),
        next_="起草 PRD 机读块，然后由人批准规划（task-approve）",
        facts={
            "task_id": task_id,
            "directory": os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
            "kind": kind,
            "generation": updated.get("generation"),
            "instance_id": instance_id,
            "template_files": sorted(os.listdir(directory)) if os.path.isdir(directory) else [],
            "control_assertion": assertion,
        },
    )


def _writer_create_intent(record, key):
    """writer 上未结案的 task.create 意图（本会话）→ 返回动作，否则 None。"""
    action = record.get("action") or {}
    if action.get("kind") != "task.create" or action.get("state") == "done":
        return None
    holder = record.get("holder") or {}
    if holder.get("id") != key:
        return None
    return action


def _publish_task_tree(ctx, directory, staging, template, task):
    """把模板产物与记录一次发布到位：先写临时目录，再 rename。"""
    files = sorted(os.listdir(template)) if os.path.isdir(template) else []
    copied = []
    os.makedirs(staging, exist_ok=False)
    try:
        for name in files:
            if not name.endswith(".md"):
                continue
            with open(os.path.join(template, name), "r", encoding="utf-8") as handle:
                text = handle.read()
            with open(os.path.join(staging, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            copied.append(name)
        if "prd.md" not in copied:
            raise TaskError("WF_TEMPLATE_INCOMPLETE",
                            {"template": template, "reason": "prd.md template missing"})
        save_task(ctx.root, staging, task)
        os.rename(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _new_binding(key, session, instance_id, task_id):
    return {
        "schema_version": 1,
        "id": key,
        "revision": 0,
        "created_at": records.now_str(),
        "updated_at": records.now_str(),
        "write_mark": None,
        "action": None,
        "identity": {"provider": session["provider"], "value": session["identity"]},
        "instance_id": instance_id,
        "object": {"kind": "task", "id": task_id},
        "bound_at": records.now_str(),
    }


def _advance_writer_steps(ctx, record, step_ids):
    """把已完成的步骤标 done 并回写 writer（每步都落盘，中断可续）。"""
    record = dict(record)
    action = dict(record.get("action") or {})
    steps = [dict(item) if isinstance(item, dict) else {"id": item, "state": "pending"}
             for item in action.get("steps") or []]
    for step in steps:
        if step.get("id") in step_ids:
            step["state"] = "done"
    action["steps"] = steps
    record["action"] = action
    writer_mod.save(ctx.root, record)
    return record


def _finish_writer_action(ctx, record, operation, evidence_refs):
    """父动作结案：核后置、生成 control_assertion、写 write_mark。"""
    record = dict(record)
    action = record.get("action") or {}
    pending = [step.get("id") for step in action.get("steps") or []
               if isinstance(step, dict) and step.get("state") != "done"]
    if pending:
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"reason": "action steps unfinished", "pending": pending},
                        next_="重入以续做未完步骤")
    if operation == "task.create":
        # 步骤字段只是游标：结案前必须回到真实后置（手工标 done 不能代替产物）
        targets = _intent_targets(action)
        task_id = targets.get("task")
        key = targets.get("binding")
        stale = [step for step in [item.get("id") for item in action.get("steps") or []]
                 if not _step_postcondition(ctx, key, task_id, step, action)]
        if stale:
            raise TaskError("WF_PERSISTENCE_FAILED",
                            {"reason": "step postcondition missing at completion", "steps": stale,
                             "task": task_id},
                            next_="重入以重建缺失后置；不据步骤字段判完成")
    assertion = _assertion(ctx, operation, record.get("holder") or {}, action, evidence_refs)
    done = actions.complete(action, summary=operation, control_assertion=assertion)
    record["action"] = done
    from . import cli

    record["write_mark"] = cli._write_mark(
        ctx, operation, _owner(record.get("holder") or {}),
        (record.get("holder") or {}).get("generation"),
        done.get("head_before"), ["task"], done,
    )
    writer_mod.save(ctx.root, record)
    return assertion


def _intent_targets(action):
    """意图里固定的目标（task / instance 等）。"""
    return {item.get("kind"): item.get("id") for item in action.get("targets") or []
            if isinstance(item, dict) and item.get("kind")}


def _step_postcondition(ctx, key, task_id, step, action):
    """某一步的真实后置是否成立（不看步骤字段，看文件/记录）。"""
    from . import session as session_mod

    directory = task_dir(ctx.root, task_id)
    if step == "create_dir":
        return bool(directory and os.path.isdir(directory))
    if step == "write_record":
        return bool(directory and os.path.isfile(os.path.join(directory, "task.json")))
    if step == "acquire_writer":
        record = ctx.writer()
        holder = record.get("holder") or {}
        scope = (holder.get("scope") or {}).get("object") or {}
        return record.get("state") == "held" and holder.get("id") == key \
            and scope.get("kind") == "task" and scope.get("id") == task_id
    if step == "bind":
        binding = session_mod.load_binding(ctx.root, key)
        runtime = records.load_json(session_mod.runtime_path(ctx.root, key), None)
        return bool(binding and (binding.get("object") or {}).get("id") == task_id
                    and (runtime or {}).get("current_task") == task_id)
    return False


def _ensure_creation_step(ctx, key, session, record, action, step, task_id):
    """把某一步做到位（幂等）：已成立就跳过，否则执行该步的真实写入。"""
    from . import session as session_mod

    if _step_postcondition(ctx, key, task_id, step, action):
        return record
    directory = task_dir(ctx.root, task_id)
    if step in ("create_dir", "write_record"):
        fixed = _intent_targets(action)
        task = load_task(ctx.root, task_id) or new_task_record(
            fixed.get("task-kind") or "ordinary", fixed.get("title") or task_id)
        task["id"] = task_id
        template = fixed.get("template")
        final = directory or join(ctx.root, f"{TASKS_REL}/{dir_name(task_id, task.get('title') or '')}")
        staging = join(ctx.root, f"{TASKS_REL}/.staging-{task_id}")
        if not os.path.isdir(final):
            if not template or not os.path.isdir(template):
                raise TaskError("WF_PERSISTENCE_FAILED",
                                {"reason": "template missing during resume", "template": template},
                                next_="按原意图补齐模板路径后重入")
            shutil.rmtree(staging, ignore_errors=True)
            _publish_task_tree(ctx, final, staging, template, task)
        elif not os.path.isfile(os.path.join(final, "task.json")):
            save_task(ctx.root, final, task)
    elif step == "acquire_writer":
        owner_scope = {"object": {"kind": "task", "id": task_id}, "preparation": None}
        record = writer_mod.acquire(record, kind="session", ident=key, scope=owner_scope,
                                    checkpoint={"step": "task-new:resume", "at": records.now_str()})
        record["action"] = action
        writer_mod.save(ctx.root, record)
    elif step == "bind":
        instance_id = _intent_targets(action).get("instance")
        if not instance_id:
            raise TaskError("WF_RECORD_INVALID",
                            {"reason": "task.create intent lacks a fixed instance target"},
                            next_="按受控恢复重建意图；不猜测实例标识")
        binding = session_mod.load_binding(ctx.root, key)
        if binding is None:
            binding = _new_binding(key, session, instance_id, task_id)
            session_mod.save_binding(ctx.root, key, binding)
            from . import identity_store as _identity_store
            _identity_store.sync_attachment_instance(ctx.root, key, instance_id)   # §3.6
        elif (binding.get("object") or {}).get("id") != task_id:
            raise TaskError("WF_BINDING_MISMATCH",
                            {"bound": binding.get("object"), "intended": task_id},
                            next_="按原意图续做同一对象；不改绑")
        if not session_mod.update_runtime(
            ctx.root, key,
            binding_digest=records.plain_digest(binding),
            instance_id=binding.get("instance_id"),
            object={"kind": "task", "id": task_id},
            current_task=task_id,
            cursor=None,
        ):
            raise TaskError("WF_PERSISTENCE_FAILED",
                            {"reason": "session runtime cache write failed", "session_key": key})
    return record


def _run_creation_steps(ctx, key, session, record, action):
    """按固定顺序逐个推进 task.create 的四个步骤；每步以真实后置为准。"""
    task_id = _intent_targets(action).get("task")
    if not task_id:
        raise TaskError("WF_RECORD_INVALID", {"reason": "task.create intent lacks a task target"})
    for step in ("create_dir", "write_record", "acquire_writer", "bind"):
        record = _ensure_creation_step(ctx, key, session, record, action, step, task_id)
        if not _step_postcondition(ctx, key, task_id, step, action):
            raise TaskError("WF_PERSISTENCE_FAILED",
                            {"reason": "step postcondition not satisfied", "step": step,
                             "task": task_id},
                            next_="修复可写性/产物后重入续做该步骤")
        record = _advance_writer_steps(ctx, record, [step])
    return record


def _resume_task_create(ctx, key, session, record, action):
    """按原意图续做 task.create：目标与实例一律取自意图，不按当前参数重建。"""
    from . import session as session_mod

    targets = _intent_targets(action)
    task_id = targets.get("task")
    instance_id = targets.get("instance")
    if not task_id or not instance_id:
        raise TaskError("WF_RECORD_INVALID",
                        {"reason": "task.create intent lacks task/instance targets", "targets": targets},
                        next_="按受控恢复重建意图；不猜测任务或实例标识")
    carried = (ctx.session(required=False) or {}).get("instance_id")
    if carried and carried != instance_id:
        # 意图里已固定的实例标识是恢复的唯一依据：请求带来的不同值不能接管
        raise TaskError("WF_BINDING_MISMATCH",
                        {"carried": carried, "intended_instance": instance_id, "task": task_id},
                        next_="按原意图的实例标识重入；或走受控恢复/交接")
    binding = session_mod.load_binding(ctx.root, key)
    if binding is not None:
        _require_instance_match(ctx, binding)
        if (binding.get("object") or {}).get("id") != task_id:
            raise TaskError("WF_BINDING_MISMATCH",
                            {"bound": binding.get("object"), "intended": task_id},
                            next_="按原意图续做同一对象；不改绑")
    record = _run_creation_steps(ctx, key, session, record, action)
    directory = task_dir(ctx.root, task_id)
    task = load_task(ctx.root, task_id) or {}
    assertion = _finish_writer_action(ctx, record, "task.create",
                                      [os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
                                       f".wf/session-bindings/{key}.json"])
    binding = session_mod.load_binding(ctx.root, key) or {}
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_="起草 PRD 机读块，然后由人批准规划（task-approve）",
        facts={"task_id": task_id,
               "directory": os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/")
               if directory else None,
               "kind": task.get("kind"),
               "instance_id": binding.get("instance_id"),
               "resumed": True,
               "control_assertion": assertion},
    )

def _complexity_proposal(ctx, task, block, extra_conditions=None):
    """汇总四项条件后再给提议：任一 true/unknown 即提出 complex（机制稿 §1.3、设计稿 §4.3）。

    2026-11-07：②③④ 从"调用方自报"改为**事实核对**——只有证据不可读时才落到 unknown，
    且 unknown 同样按复杂处理（宁高不低）。调用方仍可补声明（`contract_changes`、
    `acceptance_changed`），但不能用"不传"来关掉检查。
    """
    reasons = []
    touch_paths = block.get("touch_paths") or []

    def record(condition, value, fact):
        if value not in ("true", "unknown"):
            return
        entry = dict(fact) if isinstance(fact, dict) else {}
        entry["condition"] = condition
        entry["value"] = value
        reasons.append(entry)

    # 2026-11-07 人裁：initialize/bootstrap 豁免机械条件——它要**创建**基线/配置/spec，
    # 拿"还不存在的基线"去判①③④ 只会让每个新项目的第一步必然复杂。
    # ①在基线缺失导致的 unknown 不算事实（bootstrap 场景不适用），③整条不参与；
    # ②（契约面）仍参与：它不依赖基线。
    bootstrap = (task.get("kind") in ("initialize", "bootstrap"))
    value, fact = scope.governance_condition(ctx.root, touch_paths)
    if bootstrap and value == "unknown" and fact.get("fact") == "governance-unavailable":
        value, fact = "false", {"fact": "bootstrap-not-applicable", "detail": fact.get("problems")}
    record("governance", value, fact)

    extra = extra_conditions or {}
    declared = (extra.get("contract") or {}).get("contract_changes") if isinstance(extra.get("contract"), dict) else None
    try:
        value, fact = scope.contract_surface_condition(ctx.root, touch_paths, declared)
    except Exception as exc:  # noqa: BLE001 — 证据不可读按 unknown（不静默放行）
        value, fact = "unknown", {"fact": f"contract-surface-unavailable: {exc}"}
    record("contract", value, fact)

    acceptance_changed = None
    previous_plan = task.get("plan") or {}
    previous_acceptance = previous_plan.get("acceptance_ids")
    current_acceptance = [item.get("id") for item in block.get("acceptance") or []
                          if isinstance(item, dict) and item.get("id")]
    if previous_acceptance is not None and sorted(previous_acceptance) != sorted(current_acceptance):
        acceptance_changed = {"previous": previous_acceptance, "current": current_acceptance}
    if bootstrap:
        record("acceptance", "false", {"fact": "bootstrap-not-applicable"})
    else:
        try:
            value, fact = scope.acceptance_surface_condition(ctx.root, touch_paths, acceptance_changed)
        except Exception as exc:  # noqa: BLE001
            value, fact = "unknown", {"fact": f"acceptance-surface-unavailable: {exc}"}
        record("acceptance", value, fact)

    if bootstrap:
        record("scope", "false", {"fact": "bootstrap-not-applicable"})
    else:
        try:
            value, fact = scope.expansion_condition(previous_plan.get("touch_paths"), touch_paths)
        except Exception as exc:  # noqa: BLE001
            value, fact = "unknown", {"fact": f"scope-expansion-unavailable: {exc}"}
        record("scope", value, fact)

    for condition in COMPLEXITY_CONDITIONS:
        if condition in ("governance", "contract", "acceptance", "scope"):
            continue
        entry = extra.get(condition)
        if isinstance(entry, dict) and entry.get("value") in ("true", "unknown"):
            record(condition, entry["value"], {"fact": entry.get("fact", "")})
    proposed = "complex" if reasons else "light"
    return proposed, reasons


def _resolve_tdd(ctx, plan_decision):
    """TDD 生效值与来源（唯一实现：草稿与正式批准共用；机制稿 §2.3、设计稿 §4.3）。

    顺序：决定 `plan.tdd` → 项目配置 `tdd_default` → 发行缺省。请求 `inputs.tdd` 只是提议，
    **不生效**——否则模型可以自行开启 TDD（多出 red→绿证据义务）而不经人确认。
    返回 `(value, source)`，source 取 `decision|project-default|built-in-default`。
    """
    value, source = None, None
    if isinstance(plan_decision, dict) and plan_decision.get("tdd") is not None:
        value, source = plan_decision.get("tdd"), "decision"
    else:
        project_config, config_problems = config.load_project_config(ctx.root, allow_missing=True)
        value, tdd_problem = config.value_of(project_config, config_problems, "tdd_default")
        if tdd_problem:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": tdd_problem, "key": "tdd_default"},
                            next_="修正 project-config.json 的该键，或在决定的 plan.tdd 写明取值")
        if value is None:
            value, source = config.DEFAULTS["tdd_default"], "built-in-default"
        else:
            source = "project-default"
    if not isinstance(value, bool):
        raise TaskError("WF_PATH_INVALID", {"reason": "tdd must be boolean", "value": value})
    return value, source


# 复杂分级的人签判据与文案（唯一实现；批准入口与归档门禁共用，纵深防御不另写一套措辞）。
COMPLEX_DECISION_REASON = "complex 分级须由人在批准决定中确认（decision.plan.complexity）"


def complex_needs_human_decision(plan):
    """True 表示复杂分级没有人的批准决定承载（决定 plan 或旧记录都可能触发）。"""
    plan = plan or {}
    return plan.get("complexity") == "complex" and plan.get("confirmed_source") != "decision"


def _approval_warnings(complexity, confirmed_source, tdd, tdd_source):
    """批准结果的可见提示（唯一实现）：把"没有人确认过"的地方说在前面。

    - 轻量分级：四项条件全为 false 时机器可证，批准照常通过；但来源记 `proposed`，
      提示人可用决定 plan 把分级记成他的选择。
    - TDD：设计稿 §4.4 要求 Plan 末与复杂度一并由人确认；决定没写时按项目默认/发行缺省执行
      （这是设计允许的缺省），但记录与提示要让"这个值不是人的明确选择"可见。
    复杂分级没有 decision 承载时，批准入口直接拒绝，不会走到这里。
    """
    warnings = []
    if confirmed_source == "proposed":
        warnings.append(f"分级未由人确认：本次记录来源为 proposed（机器提议，值 {complexity}）；"
                        "要按人确认的分级记账，请在决定的 `plan.complexity` 写明")
    if tdd_source in ("project-default", "built-in-default"):
        # TDD 只由决定 plan.tdd 或项目/发行缺省取值；缺省是设计允许的，但不是人的明确选择
        origin = {"project-default": "项目配置", "built-in-default": "发行缺省"}[tdd_source]
        warnings.append(f"TDD 未由人确认：按{origin}取 {str(tdd).lower()}；"
                        "要定这个值请在决定的 plan.tdd 写明")
    return warnings or None


def cmd_task_approve(ctx, args):
    import json as _json

    if args.flag("--draft"):
        # 十六轮批V：批准决定草稿——object_digest 由入口按当前 PRD 算好，
        # 人只填 source/quote/reason（TODO 占位，照抄会被预检拒）。
        # a 组 a-2：机械修订骨架移到这里（真实入口是 task-approve 的等价链）；
        # 前置占位必须写明"仅本任务已有批准后使用"——机械修订需先有已批准版本
        # （_mechanical_revision 的 WF_APPROVAL_MISSING），plan 阶段照抄必被拒。
        task_id = args.value("--task")
        if not task_id:
            raise TaskError("WF_USAGE_INVALID", {"reason": "task-approve requires --task <id>"})
        task = _load_or_fail(ctx, task_id)
        # 批准前预检（2026-11-24，P1-4）：正式入口对 PRD 的结构性校验里，只依赖
        # PRD/项目根的部分前移到草稿——人答复之前就把模板问题修完，不再出现
        # "人批准完才第一次暴露 JSON/占位错误"的返工（dogfood 会话1 的原始失败）。
        # 依赖决定文件的校验（未知 choice、摘要比对、subject 绑定、plan-q 答复）不前移；
        # 正式入口保留全套重核（草稿与正式之间 PRD 可变，digest 失配仍会拦截）。
        # 一次读数同时拿文本与摘要：预检对象与预填的 object_digest 因此出自同一份内容，
        # 不再出现"预检过的是这版、摘要指的是那版"。
        prd_text, digest = read_prd_bytes(ctx.root, task)
        if prd_text is None:
            # PRD 文件缺失与「有 PRD 但没写 plan 块」是两个失败：前者连预检对象都没有，
            # 给专门出口，不冒充模板问题（2026-11-24 R6）。
            raise TaskError("WF_TEMPLATE_INCOMPLETE", {
                "problems": [{"reason": "PRD missing"}],
                "next_": "先写 PRD（含 wf-plan 块）再生成批准草稿；正式批准会按同一判据拒绝",
            })
        _block, _block_errors = parse_plan_block(prd_text)
        problems = list(_block_errors)
        pending_qs = extract_plan_questions(prd_text)
        if not problems:
            from . import templates as templates_mod
            from . import paths as paths_mod

            _markers = [{"kind": "required-field", "field": field} for field, _offset in
                        templates_mod.find_markers(prd_text)]
            _markers += [{"kind": "required-value", "pointer": pointer}
                         for pointer in templates_mod.find_value_markers(_block)]
            if _markers:
                problems.append({"unfilled": _markers, "template": "prd.md"})
            problems.extend(question_errors(pending_qs))
            _touch = paths_mod.touch_path_errors(_block.get("touch_paths") or [], ctx.root)
            if _touch:
                problems.append({"invalid_touch_paths": [{"entry": entry, "reason": reason}
                                                         for entry, reason in _touch]})
        if problems:
            raise TaskError("WF_TEMPLATE_INCOMPLETE", {
                "problems": problems,
                "next_": "先修 PRD（模板标记/plan 块/占位值/touch_paths）再生成批准草稿；"
                         "正式批准会按同一判据拒绝",
            })
        # 复杂度提议与生效 TDD 是入口按事实算出的（机制稿 §2.3「先提出复杂度/TDD 交人同批确认」）：
        # 草稿把它们连同四项条件的理由一起给出，并把两值写进 approve 条目的 plan 骨架——
        # 否则 wf-continue「呈现复杂度与 TDD」没有事实可呈现，人批准的分级也从未被看见
        # （2026-11-25 第四轮复审 F1：此前草稿只给 TODO，正式批准把来源记成 inputs）。
        _request_inputs = ctx.inputs() or {}
        proposed, reasons = _complexity_proposal(ctx, task, _block,
                                                 _request_inputs.get("complexity_conditions") or {})
        # 草稿是只读骨架：项目配置/请求里的 TDD 取值坏掉时，不能连骨架都拿不到。
        # 问题进 facts（与 pending_plan_questions 同性质），由人先修配置/输入再批准；
        # 正式批准仍按严格解析 raise（那里坏值就是拒绝理由）。
        try:
            tdd_value, tdd_source = _resolve_tdd(ctx, None)
            tdd_problem = None
        except TaskError as exc:
            if exc.code not in ("WF_SEMANTIC_DECISION", "WF_PATH_INVALID"):
                raise
            tdd_value, tdd_source, tdd_problem = None, "unavailable", dict(exc.facts, code=exc.code)
        entry = {"source": "TODO human:<来源>",
                "at": records.now_str(),
                "subject": f"approve {task_id}",
                "object_digest": digest,
                # 人看的是整套规划，不只是 PRD 字节：把 design/implement 的当时摘要一并绑上，
                # 答复之后任一产物再变即拒（否则"批的是旧方案、记的是新方案"）。
                "artifacts": {item["path"]: item["digest"]
                              for item in artifact_digests(ctx.root, task)},
                "choice": "approve",
                # 人的答复可以改这两个值；原样保留即"确认入口的提议"（来源记 decision）。
                # TDD 不可解析时不预填该键，让正式批准按同一问题报出（facts.tdd.problem 已先给）。
                "plan": ({"complexity": proposed} if tdd_problem else
                         {"complexity": proposed, "tdd": tdd_value}),
                "reason": "TODO（人填写：为什么批准本规划）"}
        mechanical = {"source": "TODO human:<来源>",
                      "at": records.now_str(),
                      "subject": f"机械修订 {task_id}",
                      "object_digest": digest,
                      # 与 approve 条目同源：机械修订也核整套产物，草稿不带就会自我锁死
                      "artifacts": dict(entry["artifacts"]),
                      "choice": "机械修订",
                      "reason": "TODO（人填写：排版/转义等不改验收与触碰面的修订说明）"
                      "——仅本任务已有批准、且只改排版/转义时保留本条，否则删除"}
        # 复杂提议下 design/implement 是否齐备也是入口能算的：草稿先报，别让"人批准完才第一次暴露"。
        complex_artifacts = (complex_artifact_problems(ctx.root, task, proposed)
                             if proposed == "complex" else [])
        return _decision_draft_result(ctx, task_id, [entry, mechanical], command="task-approve",
                                      extra_facts={"pending_plan_questions": pending_qs,
                                                   "complexity_proposal": {"value": proposed,
                                                                           "reasons": reasons},
                                                   "complex_artifacts": complex_artifacts,
                                                   "tdd": ({"value": tdd_value, "source": tdd_source}
                                                           if tdd_problem is None else
                                                           {"value": None, "source": tdd_source,
                                                            "problem": tdd_problem})})
    from . import cli, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id or not decision_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-approve requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    task = _load_or_fail(ctx, task_id)
    _require_binding(ctx, task_id)
    inputs = ctx.inputs()
    with lock.acquire(ctx.root, holder_hint="task-approve"):
        record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        mechanical = [item for item in decisions if item.get("choice") == MECHANICAL_REVISION]
        if mechanical:
            # 机械修订不改阶段、不重复批准；在 execute/check/finish 均可接链（机制稿 §1.3）
            return _mechanical_revision(ctx, path, task, holder, mechanical[0], decisions)
        if task.get("status") not in ("not_started", "in_progress") or task.get("phase") != "plan":
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "approval only in plan phase",
                                                     "status": task.get("status"), "phase": task.get("phase")})
        prd_text, prd_digest = read_prd_bytes(ctx.root, task)
        # 未知 choice 不得静默忽略：否则人以为"我说了"，记录里却什么都没有
        # （演练实测：{"choice":"complexity","value":"complex"} 被无声丢弃，直到归档门禁才炸）。
        _known_choices = set(APPROVE_CHOICES) | {MECHANICAL_REVISION, "plan-q", "risk-accept"}

        def _answers_plan_q(item):
            """plan-q 的答复靠 **subject 里的编号**识别，choice 写什么都成立（"是"/"是，按推荐"/"plan-q"）。

            审查询问过：旧夹具写 `choice="是"` 被新守卫拒了。守卫的本意是"别静默丢掉我的意图"，
            而 plan-q 答复的意图已经在 subject 里，不该再要求一个特定词。
            """
            subject = item.get("subject")
            text = " ".join(str(x) for x in subject) if isinstance(subject, list) else str(subject or "")
            import re as _re
            return bool(_re.search(r"(?<!\d)plan-q-(\d+)(?!\d)", text))

        _unknown = [item.get("choice") for item in decisions
                    if isinstance(item, dict) and item.get("choice") not in _known_choices
                    and not _answers_plan_q(item)]
        if _unknown:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "unknown decision choice in approval file",
                             "unknown": _unknown, "known": sorted(_known_choices),
                             "hint": "分级写在批准决定的 plan 里：{choice=approve, plan:{complexity:...}}"},
                            next_="改决定文件后重新批准（未知 choice 一律拒绝，不猜意图）")
        approvals = [item for item in decisions if item.get("choice") in APPROVE_CHOICES]
        if not approvals:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "no approval decision", "choices": [item.get("choice") for item in decisions],
                             "accepted": list(APPROVE_CHOICES)},
                            next_="用 choice=approve 的决定重新批准")
        approval = approvals[0]
        # 摘要取自上面那次读（同一读数）：草稿/机械修订/replan 也用它，口径唯一。
        # 必填而不是"有才比"：留空的旧摘要能靠 subject 里的任务 id 混过，人答复之后 PRD
        # 再变也算批准（2026-11-24 复核 b-P1）。subject 含任务 id 退回**次级**绑定。
        declared_digest = approval.get("object_digest")
        if not declared_digest:
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision lacks object_digest (PRD digest)",
                             "expected_prd_digest": prd_digest},
                            next_="按当前 PRD 重新出批准决定：`task-approve --draft` 会预填摘要；"
                                  "入口不代填——人对 PRD 的批准留痕不可替代")
        if declared_digest != prd_digest:
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision does not cover the current PRD",
                             "decision_digest": declared_digest, "current_digest": prd_digest,
                             "expected_prd_digest": prd_digest},
                            next_="针对当前 PRD 重新出批准决定（object_digest 应为 expected_prd_digest；"
                                  "入口不代填——人对 PRD 的批准留痕不可替代）")
        declared_artifacts = approval.get("artifacts")
        if not isinstance(declared_artifacts, dict) or not declared_artifacts:
            # 只认 PRD 字节的决定会给"后来又补了方案"留门：产物一律要求现报（草稿已预填）。
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision lacks plan artifacts",
                             "expected_artifacts": {item["path"]: item["digest"]
                                                    for item in artifact_digests(ctx.root, task)},
                             "expected_prd_digest": prd_digest},
                            next_="重新生成草稿（task-approve --draft）后请人确认；"
                                  "手写决定时按 expected_artifacts 补 `artifacts`")
        changed_artifacts = artifact_drift(ctx.root, task, declared_artifacts)
        if changed_artifacts:
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "plan artifacts changed after the decision was drafted",
                             "changed": changed_artifacts,
                             "expected_artifacts": {item["path"]: item["digest"]
                                                    for item in artifact_digests(ctx.root, task)}},
                            next_="重新生成草稿（task-approve --draft）并按当前规划请人确认；"
                                  "答复之后新增或改写 design/implement 同样算没看过")
        # 摘要只绑内容：两份任务 PRD 字节相同时，光凭摘要无法说是哪一项。subject 是
        # **次级绑定**，所以仍核任务 id——它不是展示字段，help 的措辞与之对应。
        if task_id not in str(approval.get("subject") or ""):
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision subject does not name this task",
                             "subject": approval.get("subject"), "task": task_id,
                             "expected_prd_digest": prd_digest},
                            next_="在 subject 写明任务 id（摘要相同不等于同一项任务）；"
                                  "`task-approve --draft` 已按此形态生成")
        questions = extract_plan_questions(prd_text)
        q_errors = question_errors(questions)
        if q_errors:
            raise TaskError("WF_SEMANTIC_DECISION", {"problems": q_errors})
        unanswered = unanswered_plan_questions(ctx.root, task, decisions)
        if unanswered:
            raise TaskError("WF_SEMANTIC_DECISION", {"unanswered": unanswered},
                            next_="在决定文件中逐条给出 plan-q 答复")
        block, errors = parse_plan_block(prd_text)
        if errors:
            raise TaskError("WF_TEMPLATE_INCOMPLETE", {"problems": errors})
        from . import templates as templates_mod

        markers = [{"kind": "required-field", "field": field} for field, _offset in
                   templates_mod.find_markers(prd_text)]
        markers += [{"kind": "required-value", "pointer": pointer}
                    for pointer in templates_mod.find_value_markers(block)]
        if markers:
            raise TaskError("WF_TEMPLATE_INCOMPLETE", {"unfilled": markers, "template": "prd.md"})
        from . import paths as paths_mod

        touch_errors = paths_mod.touch_path_errors(block.get("touch_paths") or [], ctx.root)
        if touch_errors:
            raise TaskError("WF_PATH_INVALID", {"invalid_touch_paths": [{"entry": entry, "reason": reason}
                                                                       for entry, reason in touch_errors]})
        block["touch_paths"] = [paths_mod.validate_glob(item) for item in block.get("touch_paths") or []]
        # 四项条件先汇总，再定分级；人工指定只能降级且须给理由与证据
        extra = inputs.get("complexity_conditions") or {}
        proposed, reasons = _complexity_proposal(ctx, task, block, extra)
        # 人已确认项：优先取决定文件里的 plan 块（人写的），请求 inputs 只作提议；
        # 未登记的键不丢弃，原样留痕并给出 unconfirmed_keys（新增人判项不必改结构）。
        plan_decision = approval.get("plan")
        if plan_decision is None:
            plan_decision = {}
        if not isinstance(plan_decision, dict):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "decision.plan must be an object", "plan": plan_decision})
        unconfirmed = []
        for key, value in plan_decision.items():
            check = HUMAN_PLAN_KEYS.get(key)
            if check is None:
                unconfirmed.append(key)
                continue
            if not check(value):
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "invalid human-confirmed value", "key": key, "value": value})
        complexity = plan_decision.get("complexity") or inputs.get("complexity") or proposed
        if complexity not in ("light", "complex"):
            raise TaskError("WF_PATH_INVALID", {"reason": "complexity must be light|complex"})
        # 来源如实声明（2026-11-25 第四轮复审 F1）：决定与 inputs 都没有该值时，取值来自机器提议，
        # 旧实现记 "inputs" 会把"没有人确认过"写成"请求输入确认过"。
        if "complexity" in plan_decision:
            confirmed_source = "decision"
        elif inputs.get("complexity") is not None:
            confirmed_source = "inputs"
        else:
            confirmed_source = "proposed"
        # 复杂分级的载体只能是人的批准决定（设计稿 §4.3、机制稿 §2.3）：请求 inputs 是提议，
        # 机器提议更不是确认。只提示"归档会被拒"会让 AI 干完活才撞墙，这里在批准时即拒。
        if complexity == "complex" and confirmed_source != "decision":
            raise TaskError("WF_SEMANTIC_DECISION", {
                "reason": COMPLEX_DECISION_REASON,
                "complexity": complexity, "confirmed_source": confirmed_source,
                "complexity_reasons": reasons,
                "expected": {"plan": {"complexity": "complex"}},
                "exits": ["用 `task-approve --draft` 生成骨架（已预填 `plan.complexity`），请人确认后按骨架写决定",
                          "手写决定时在 `plan.complexity` 写明分级；请求 inputs 只作提议，不构成人确认"],
            }, next_="补齐人的分级决定后重新批准")
        downgrade_entry = None
        if complexity == "light" and proposed == "complex":
            downgrade = plan_decision.get("downgrade") or inputs.get("downgrade") or {}
            if not downgrade.get("reason") or not downgrade.get("evidence"):
                raise TaskError(
                    "WF_SEMANTIC_DECISION",
                    {"reason": "complexity condition requires complex", "condition": reasons,
                     "downgrade_required": ["reason", "evidence"],
                     "hint": "存量项目请先建 bootstrap 任务（建基线+项目配置）再开普通任务"},
                )
            # 降级条目属批准后追加事实，不进 plan 版本哈希域（机制稿 §1.1）
            downgrade_entry = {"downgrade": True, "reason": downgrade["reason"], "evidence": downgrade["evidence"]}
        artifact_problems = complex_artifact_problems(ctx.root, task, complexity)
        if artifact_problems:
            raise TaskError("WF_TEMPLATE_INCOMPLETE",
                            {"reason": "complex task requires complete design/implement",
                             "complexity": complexity, "artifacts": artifact_problems},
                            next_="补齐 design.md / implement.md 并填写必填占位后重新批准")
        # TDD 生效值：决定 → 请求 inputs → 项目配置 → 发行缺省（唯一实现在 _resolve_tdd，
        # 草稿与正式批准共用，避免"草稿显示一个值、正式记另一个值"）。
        tdd, tdd_source = _resolve_tdd(ctx, plan_decision)
        version = compute_plan_version(ctx.root, task, block, complexity, reasons, tdd)
        if downgrade_entry is not None:
            reasons = reasons + [downgrade_entry]
        artifacts = artifact_digests(ctx.root, task)
        snapshot = {"block": block, "artifacts": []}
        for entry in artifacts:
            try:
                with open(join(ctx.root, entry["path"]), "r", encoding="utf-8") as handle:
                    snapshot["artifacts"].append({"path": entry["path"], "digest": entry["digest"],
                                                  "content": handle.read()})
            except OSError:
                continue
        plan = dict(task.get("plan") or {})
        plan.update({
            "version": version,
            "approved_version": version,
            "artifacts": artifacts + [{"snapshot": snapshot}],
            "touch_paths": block["touch_paths"],
            "acceptance_digest": fingerprint.acceptance_digest(block["acceptance"]),
            "verifications": block["verifications"],
            "acceptance": block["acceptance"],
            "complexity": complexity,
            "complexity_reasons": reasons,
            "tdd": tdd,
            "approval": approval,
            # 人工载体：谁的值、有哪些未登记的人判项（新增项不会静默消失）
            "confirmed_source": confirmed_source,
            "human_inputs": plan_decision,
            "unconfirmed_keys": unconfirmed,
            "acceptance_ids": [item.get("id") for item in block["acceptance"] if isinstance(item, dict)],
        })
        task["plan"] = plan
        execution = task.setdefault("execution", {})
        human = execution.setdefault("human_decisions", [])
        for decision in decisions:
            if decision is not approval:
                # 保留 subject 只经专用通道入账：`task-check --decision` 会核倍数已到场与
                # choice 域；通用批准路径原样 append 会把任意 subject 变成裁定/声明，
                # 例如一条 plan-q 答复写成 `debug-ruling-<vid>-99` 即可静音归档阻断。
                subject = str(decision.get("subject") or "")
                if subject.startswith(("debug-ruling-", "debug-declaration:")):
                    raise TaskError("WF_SEMANTIC_DECISION", {
                        "reason": "debug ruling/declaration decisions must go through task-check --decision",
                        "subject": subject,
                        "exits": ["改用 task-check --decision 提交裁定/声明（入口核倍数与 choice 域）",
                                  "若是普通答复，把 subject 改回 plan-q-<n> / 任务主题"]})
                human.append(decision)
        task, action = _start_task_action(
            ctx, path, task, "task.transition", holder,
            {"task": task_id, "phase": "plan", "action": "approve", "plan_version": version},
            ["verify_block", "verify_touch_paths", "record_approval"],
        )
        projection = {"plan_version": version}
        from . import gates

        gates.write_receipt(task, "task.plan-approved", mode="once", projection=projection,
                            rule_version=ctx.rule_version(), evidence_refs=[records.plain_digest(approval)])
        task, assertion = _finish_task_action(
            ctx, path, task, "task.transition", holder,
            {"task": task_id, "phase": "plan", "action": "approve", "plan_version": version}, action,
        )
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="plan", task_id=task_id, action_id=task["action"]["id"],
                                 action_state=task["action"]["state"]),
        next_="人确认后开工：task-start",
        facts={
            "plan_version": version,
            "complexity": complexity,
            "complexity_reasons": reasons,
            "confirmed_source": confirmed_source,
            "tdd": tdd,
            "tdd_source": tdd_source,
            "touch_paths": block["touch_paths"],
            "acceptance_digest": plan["acceptance_digest"],
            "verifications": [item.get("id") for item in block["verifications"]],
            "control_assertion": assertion,
            # P2-5：配置了复评提示键就让它们真的出现（提醒复评复杂度，不自动分类）
            "complexity_hints": _complexity_hints(ctx.root),
        },
        warnings=_approval_warnings(complexity, confirmed_source, tdd, tdd_source),
    )


COMPLEXITY_HINT_KEYS = ("split_file_hint", "split_line_hint", "merge_line_hint",
                        "review_file_hint", "review_line_hint")


def _complexity_hints(root):
    """把配置里的复评提示键原样带出（机制稿 §8.1：提醒复评，不自动分类）。"""
    from . import config as config_mod

    config_data, problems = config_mod.load_project_config(root, allow_missing=True)
    hints = {}
    for key in COMPLEXITY_HINT_KEYS:
        value, problem = config_mod.value_of(config_data, problems, key)
        if value is not None and not problem:
            hints[key] = value
    return hints


# --------------------------------------------------------------------------
# 命令：task-start
# --------------------------------------------------------------------------


def _run_start_verifications(ctx, task):
    """开工时点的验证：`argv` 直接执行；`manual` 不执行，只登记"待人判"。

    **此前 manual 也走命令通道**（`_argv_ready` 拿不到 argv → `WF_VERIFICATION_UNREADY`），
    于是"规划校验接受 kind=manual + consume_at=start、开工必然报错"，AI 只能回 Plan 改
    已批准的验证声明——把一个合法声明变成规划缺陷（2026-11-23 五轮复审 b-3）。
    manual 的语义本来就是"人给结论"：开工只记一条 `human_required` 事实，真正的
    人判证据在 Check 阶段按既有规则（`check.py` 的 manual 分支要求 decision）强制。
    """
    from . import check as check_mod

    results = []
    for verification in (task.get("plan") or {}).get("verifications") or []:
        if verification.get("consume_at") != "start":
            continue
        invocation = verification.get("invocation") or {}
        if invocation.get("kind") == "manual":
            results.append({"verification_id": verification.get("id"), "kind": "manual",
                            "status": "human_required",
                            "criterion": invocation.get("criterion")})
            continue
        ready, reason = check_mod._argv_ready(ctx.root, invocation)
        if not ready:
            raise TaskError("WF_VERIFICATION_UNREADY", {"verification_id": verification.get("id"), "reason": reason})
        cwd = verification.get("cwd") or "."
        workdir = ctx.root if cwd == "." else join(ctx.root, cwd)
        argv = list(invocation.get("argv") or [])
        # 开工验证在项目锁内执行：没有超时界的话，一条挂起的命令会把所有依赖同一把锁的
        # 操作一起卡住（十四轮 a-3）。这里与 Check 用同一个配置键与同一套归因。
        # 配置非法时**必须报错**：静默退成"无超时"等于把配置契约变成建议，而这条命令
        # 就跑在项目锁内（十五轮 a-1）。只有"未配置"才是合法地无界。
        from . import check as _check_timeout_mod

        _timeout = _check_timeout_mod.verification_timeout(ctx.root)
        try:
            result = subprocess.run(argv, cwd=workdir, capture_output=True, text=True,
                                    check=False, timeout=_timeout)
        except subprocess.TimeoutExpired:
            raise TaskError("WF_CHECK_FAILED",
                            {"verification_id": verification.get("id"),
                             "reason": f"timed out after {_timeout}s",
                             "output": ""})
        results.append({"verification_id": verification.get("id"), "kind": "argv",
                        "exit_code": result.returncode})
        if result.returncode != 0:
            # 与 Check 阶段同一份遮罩（`check.redact_text` 是唯一实现在 check.py）：
            # 开工验证失败会把命令输出带进错误事实并原样回显给调用方/会话日志，
            # 不遮罩就等于**同一命令在 Check 有保护、在开工没有**（2026-11-23 六轮复审 a-2）。
            from . import check as _check_mod

            # 顺序必须是**先遮罩、后截断**：先截断会把长凭据的前缀（`Bearer `、键名）切掉，
            # 遮罩就找不到触发词，整段明文随错误回显（2026-11-23 七轮复审 a-1：
            # 1100 字符的虚构凭据在开工错误里残留 799 字符）。
            masked = _check_mod.redact_text((result.stdout or "") + (result.stderr or ""))
            raise TaskError(
                "WF_CHECK_FAILED",
                {"verification_id": verification.get("id"), "exit_code": result.returncode,
                 "output": masked[-800:]},
            )
    return results




def _start_verification_ids(task):
    """`consume_at=start` 的验证 id 列表（机制稿 §7.1 验证声明的首个消费时点）。"""
    return [item.get("id") for item in (task.get("plan") or {}).get("verifications") or []
            if isinstance(item, dict) and item.get("consume_at") == "start"]


def _start_verification_evidence(task, action):
    """动作内已固定下来的 start 期验证证据（`{verification_id: entry}`）。"""
    entries = (action or {}).get("inputs") or {}
    fixed = entries.get("start_verifications")
    if not isinstance(fixed, list):
        return {}
    return {item.get("verification_id"): item for item in fixed if isinstance(item, dict)}


def _missing_start_verification_evidence(task, action):
    """真实后置：每个 `consume_at=start` 验证都必须在动作内留下结果，缺即未完成。

    此前证据只进命令 facts（打印一次就没了），归档/复盘时无从核对「开工时那条验证真的跑过」；
    机制稿 §5.1 要求把跨记录写入固定在动作意图与后置里。
    """
    fixed = _start_verification_evidence(task, action)
    return [vid for vid in _start_verification_ids(task) if vid not in fixed]


def _block_overlapping_maintenance(ctx, task):
    """与本次请求范围重叠的未结维护组阻断开工（机制稿 §4.5、§5.2 第⑩项）。"""
    from . import paths as paths_mod

    # 走统一读取：含可达提交查证，已提交的维护组自动派生 persisted（机制稿 §4.5）
    receipts = task_receipts(ctx.root)
    # 统一走批准面判定（严格三态）：损坏快照不得静默回退 plan（第十三轮复审外部 P2）
    requested = approved_touch_paths(task)
    overlapping = []
    unverified = []
    for receipt in receipts:
        state = receipt["state"]
        if state not in ("applied_pending_commit", "pending_check"):
            continue
        for relative in receipt["facts"].get("paths") or []:
            if any(paths_mod.match_path(pattern, relative) for pattern in requested):
                item = {"operation": receipt["operation"], "path": relative, "state": state}
                if state == "pending_check":
                    item["reason"] = receipt["facts"].get("reason")
                    unverified.append(item)
                else:
                    overlapping.append(item)
                break
    if unverified:
        raise TaskError("WF_HISTORY_UNRESOLVED",
                        {"unverified_receipts": unverified,
                         "next": "只读核对维护回执与可达提交后重试"})
    if overlapping:
        raise TaskError("WF_WIP_UNRESOLVED",
                        {"overlapping_receipts": overlapping,
                         "next": "人处置维护组（提交 / 反向修正 / 具名承接）后回写处置，再恢复推进"})




def _mechanical_revision(ctx, path, task, holder, decision, decisions):
    """机械修订：校验两端同义后接一条等价链，不重复人批准（机制稿 §1.3）。"""
    from . import paths as paths_mod

    plan = dict(task.get("plan") or {})
    if task.get("status") == "archived":
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "已归档任务不接受机械修订"})
    if not plan.get("approval") or not plan.get("approved_version"):
        raise TaskError("WF_APPROVAL_MISSING", {"reason": "机械修订需先有已批准版本"})
    # 人签必须绑定**人看过的那份 PRD**：`task-approve --draft` 会预填 object_digest，
    # 入口此前不核对——拿旧摘要（草稿生成之后 PRD 又改过）调用仍返回 WF_OK，
    # 等于把旧确认沿用到未确认的内容（2026-11-23 十轮复审 b-1）。
    declared_digest = decision.get("object_digest")
    prd_text, current_digest = read_prd_bytes(ctx.root, task)
    if not declared_digest:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "机械修订的决定缺少 object_digest（需绑定人看过的 PRD 摘要）",
                         "current_object_digest": current_digest,
                         "exits": ["重新生成草稿（task-approve --draft）后请人确认并重跑"]})
    if current_digest is None:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "无法核对 PRD 摘要（任务目录或 prd.md 不可读）",
                         "exits": ["核对任务目录与 prd.md 后重跑；必要时回 Plan 重新批准"]})
    if declared_digest != current_digest:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "决定的 object_digest 与当前 PRD 摘要不一致：人确认的不是这份内容",
                         "declared_object_digest": declared_digest,
                         "current_object_digest": current_digest,
                         "exits": ["重新生成草稿、请人按当前内容确认后重跑",
                                   "若内容实质变化，回 Plan 重新批准"]})
    declared_artifacts = decision.get("artifacts")
    if not isinstance(declared_artifacts, dict) or not declared_artifacts:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "机械修订的决定缺少 artifacts（签认要覆盖整套产物）",
                         "expected_artifacts": {item["path"]: item["digest"]
                                                for item in artifact_digests(ctx.root, task)},
                         "exits": ["重新生成草稿（task-approve --draft）后请人确认并重跑"]})
    changed_artifacts = artifact_drift(ctx.root, task, declared_artifacts)
    if changed_artifacts:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "规划产物在签认之后变过：等价链会把新方案并进旧签认",
                         "changed": changed_artifacts,
                         "exits": ["重新生成草稿、请人确认后再跑",
                                   "产物实质变化时回 Plan 重新批准"]})
    block, errors = parse_plan_block(prd_text)
    if errors:
        raise TaskError("WF_TEMPLATE_INCOMPLETE", {"problems": errors})
    from . import templates as templates_mod

    markers = [{"kind": "required-field", "field": field} for field, _offset in
               templates_mod.find_markers(prd_text)]
    markers += [{"kind": "required-value", "pointer": pointer}
                for pointer in templates_mod.find_value_markers(block)]
    if markers:
        raise TaskError("WF_TEMPLATE_INCOMPLETE", {"unfilled": markers, "template": "prd.md"})
    touch_errors = paths_mod.touch_path_errors(block.get("touch_paths") or [], ctx.root)
    if touch_errors:
        raise TaskError("WF_PATH_INVALID", {"invalid_touch_paths": [
            {"entry": entry, "reason": reason} for entry, reason in touch_errors]})
    touch_paths = [paths_mod.validate_glob(item) for item in block.get("touch_paths") or []]
    acceptance = fingerprint.acceptance_digest(block.get("acceptance") or [])
    current_verifications = block.get("verifications") or []
    approved_verifications = plan.get("verifications") or []
    if (sorted(touch_paths) != sorted(plan.get("touch_paths") or [])
            or acceptance != plan.get("acceptance_digest")
            or records.H("wf-plan-verifications-v1", current_verifications)
            != records.H("wf-plan-verifications-v1", approved_verifications)):
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "触碰面、验收或验证项定义发生变化，不属机械修订；回 Plan 重新批准",
                         "approved_touch_paths": plan.get("touch_paths"),
                         "current_touch_paths": touch_paths,
                         "approved_acceptance_digest": plan.get("acceptance_digest"),
                         "current_acceptance_digest": acceptance,
                         "approved_verifications": approved_verifications,
                         "current_verifications": current_verifications})
    conditions = [item for item in plan.get("complexity_reasons") or [] if not item.get("downgrade")]
    current_version = compute_plan_version(ctx.root, task, block, plan.get("complexity"),
                                           conditions, plan.get("tdd"))
    if current_version == plan.get("version"):
        return codes.result(
            "WF_OK",
            object={"id": task.get("id"), "name": task.get("title")},
            position_=codes.position(scope="task", phase="plan", task_id=task.get("id")),
            next_="无需衔接：当前规划版本未变化",
            facts={"mechanical": True, "plan_version": current_version},
        )
    plan["equivalences"] = list(plan.get("equivalences") or []) + [{
        "old_version": plan.get("version"),
        "new_version": current_version,
        "reason": decision.get("reason"),
        "source": decision.get("source"),
        "decision": decision,
    }]
    plan["version"] = current_version
    plan["artifacts"] = artifact_digests(ctx.root, task)
    task["plan"] = plan
    execution = task.setdefault("execution", {})
    execution.setdefault("human_decisions", []).append(decision)
    inputs = {"task": task.get("id"), "action": "mechanical-revision",
              "old_version": plan["equivalences"][-1]["old_version"], "new_version": current_version}
    task, action = _start_task_action(ctx, path, task, "task.transition", holder, inputs,
                                      ["verify_synonymy", "record_equivalence"])
    task, assertion = _finish_task_action(ctx, path, task, "task.transition", holder, inputs, action,
                                          evidence_refs=[records.plain_digest(decision)])
    normalized = normalized_plan_version(task)
    return codes.result(
        "WF_OK",
        object={"id": task.get("id"), "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task.get("id"),
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="继续当前步骤；锚点与回执期次按归一版本保持不变",
        facts={"mechanical": True, "old_version": plan["equivalences"][-1]["old_version"],
               "new_version": current_version, "normalized_version": normalized,
               "approved_version": plan.get("approved_version"),
               "control_assertion": assertion},
    )


def _apply_exclusion_entries(ctx, task, classified, entries, *, receipts=None):
    """把本次声明里的外来改动排除落进记录，并返回**重新分类**的结果。

    路径必须当前在 c 桶（未归属未提交），摘要按记录时的真实内容固定。
    校验不通过整批拒绝（零写入）。
    """
    from . import scope as scope_mod

    if not entries:
        return classified
    new_records, problems = scope_mod.exclusion_records(ctx.root, classified, entries)
    if problems:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"problems": problems,
                         "exits": ["只排除未归属未提交的路径；属本任务的路径在批准触碰面内直接计入交付，"
                                   "已提交的历史改动才用 task-attribute --commit <sha> 裁决归属"]})
    scope_mod.persist_exclusions(task, new_records)
    return scope_mod.classify_candidates(ctx.root, task, receipts=receipts)


def cmd_task_start(ctx, args):
    from . import gates, lock

    task_id = args.value("--task")
    exclusion_file = args.value("--workspace-exclusion")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-start requires --task <id>"})
    exclusion_entries, exclusion_problems = scope.load_exclusion_declarations(exclusion_file)
    if exclusion_problems:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"problems": exclusion_problems,
                         "exits": ["按问题清单修正声明文件（paths 只写具体路径，确认要带 by/at/quote/source）"]})
    task = _load_or_fail(ctx, task_id)
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-start"):
        record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        pending = actions.pending(task)
        if pending:
            # 旧版本把首次创建的意图写在 task.action：迁移到 writer 意图前不能把它当"可按原意图恢复"
            if pending.get("kind") == "task.create":
                raise TaskError("WF_RECORD_INVALID",
                                {"reason": "legacy task.create intent lives on the task record",
                                 "action": pending.get("id"),
                                 "remedy": "task-new 已把创建意图迁到 writer；该遗留动作需人工确认后清除（repair）"},
                                next_="核对创建确实完成或用 repair 清理遗留动作；不要在此重放")
            raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state")},
                            next_="按原意图恢复该动作")
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived"})
        if task.get("phase") != "plan" or task.get("status") not in ("not_started", "in_progress"):
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "start requires plan phase",
                                                     "status": task.get("status"), "phase": task.get("phase")})
        if task.get("paused") or task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION", {"paused": task.get("paused"), "suspended": task.get("suspended")})
        blockers = dependency_blockers(ctx.root, task)
        if blockers:
            raise TaskError("WF_DEPENDENCY_UNMET", {"unmet": blockers})
        if not (task.get("plan") or {}).get("approval"):
            raise TaskError("WF_APPROVAL_MISSING", {"reason": "plan not approved"})
        current = current_plan_version(ctx.root, task)
        if current.get("error"):
            raise TaskError(current["error"][0], current["error"][1])
        if current.get("version") != (task.get("plan") or {}).get("version"):
            raise TaskError("WF_APPROVAL_MISSING",
                            {"approved": (task.get("plan") or {}).get("version"),
                             "current": current.get("version"),
                             "exits": ["规划有实质变化：回 Plan 重新批准（task-replan --decision 后 task-approve）",
                                       "只是排版/进度/说明改动：写 choice=机械修订 的决定文件后"
                                       "重跑 task-approve（接等价链，不重复人批准）"]})
        if task.get("kind") == "ordinary":
            config_record, problems = config.load_project_config(ctx.root, allow_missing=True)
            if config_record is None or not os.path.exists(join(ctx.root, ".wf/baseline.md")):
                # 与 task-approve 同口径：新项目冷启动要给可执行出口，不能只报"缺文件"让人猜
                missing = (".wf/project-config.json" if config_record is None else ".wf/baseline.md")
                raise TaskError("WF_CAPABILITY_UNAVAILABLE",
                                {"missing": missing, "reason": "ordinary task requires project config and baseline",
                                 "exits": ["先建一个 bootstrap 任务，用维护入口生成 .wf/project-config.json 与 .wf/baseline.md",
                                           "存量项目：按项目既有配置补齐这两个文件后重试"]},
                                next_="建 bootstrap 任务生成基线与配置（与 task-approve 的提示一致）")
        if not scope.has_git(ctx.root):
            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "Git HEAD required", "missing": "git HEAD"})
        head = scope.head(ctx.root)
        if not head:
            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "no HEAD commit"})
        _block_overlapping_maintenance(ctx, task)
        # 先核前置条件再跑验证命令：缺 spec 读取记录或工作区有外来改动时，命令跑过也白跑，
        # AI 处理完前置还得再跑一次（十六轮 b-4）。
        findings = gates.evaluate(ctx, task, "before_execute")
        blocking = [item for item in findings if item["status"] == "missing"]
        if blocking:
            raise TaskError(blocking[0]["code"] or "WF_SEMANTIC_DECISION", {"missing": blocking})
        if task.get("kind") == "ordinary":
            receipts = task_receipts(ctx.root)
            classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
            classified = _apply_exclusion_entries(ctx, task, classified, exclusion_entries,
                                                  receipts=receipts)
            if classified["buckets"]["c"]:
                raise TaskError("WF_WORKSPACE_UNRESOLVED",
                                {"other_tasks": classified["buckets"]["c"],
                                 "exclusions": classified.get("exclusions"),
                                 "exits": ["确认这些外来改动不属于本任务：写一份声明"
                                           "（choice=排除外来改动 + paths + by/at/quote/source）"
                                           "后用 --workspace-exclusion 重跑 task-start",
                                           "由人实际处置这些路径（提交 / 移走 / 具名承接）后重跑"]})
            if classified["buckets"]["f"]:
                raise TaskError("WF_SCOPE_VIOLATION", {"out_of_scope": classified["buckets"]["f"]})
        elif exclusion_entries:
            # 初始化/接入任务不走 c 档门禁，排除声明在这里没有消费点：显式拒绝，不静默丢弃
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "工作区排除只适用于普通任务；该任务类型不使用 c 档门禁",
                             "kind": task.get("kind"),
                             "exits": ["去掉 --workspace-exclusion 后重跑",
                                       "该路径若确属本任务且已提交：用 task-attribute --commit <sha> 裁决归属；"
                                       "未提交的按批准触碰面归属"]})
        # P2-3：执行候选唯一性对全部 kind 生效（initialize/bootstrap 也不能与别的执行同时存在）
        others = [
            other for _path, other in iter_tasks(ctx.root)
            if other.get("id") != task_id
            and other.get("status") == "in_progress"
            and not other.get("paused") and not other.get("suspended")
        ]
        if others:
            raise TaskError("WF_RECORD_INVALID", {"other_candidates": [item.get("id") for item in others]})
        # 触碰面按机制稿 §2.3「从该批准版本的 PRD 重提取并规范化」：
        # 直接抄 plan.touch_paths 会让手改 task.json 的 plan 反向影响快照（PRD 未变、版本比对仍通过）。
        _prd_source, _prd_at_entry = read_prd_bytes(ctx.root, task)
        _plan_block, _block_errors = parse_plan_block(_prd_source)
        if _block_errors or not isinstance(_plan_block, dict):
            raise TaskError("WF_TEMPLATE_INCOMPLETE",
                            {"problems": _block_errors or ["plan block missing"]})
        entry = {
            "plan_version": (task.get("plan") or {}).get("version"),
            "approval_ref": records.plain_digest((task.get("plan") or {}).get("approval")),
            "prd_digest": _prd_at_entry,
            "touch_paths": _dedupe_paths(_normalized_paths(_plan_block.get("touch_paths") or [])),
            "head_at_entry": head,
            "entered_at": records.now_str(),
            # 预存脏文件清单（九轮审查 b-1）：触碰面说明"允许改哪里"，不证明"是谁改的"。
            # 开工前已存在的未提交路径后续即使命中触碰面，也先按"待归属"处理（c 桶），
            # 不从 glob 命中直接推出归属。
            "preexisting_uncommitted": sorted(scope.uncommitted_paths(ctx.root)),
        }
        # 前置条件全部成立后才执行开工验证命令：失败/缺前置时命令没有白跑一次的机会
        # （十六轮 b-4）。结果仍写进 action 输入与回执。
        start_results = _run_start_verifications(ctx, task)
        task["entry_snapshot"] = entry
        if task.get("status") == "not_started":
            task["baseline_head"] = head
        task["status"] = "in_progress"
        task["phase"] = "execute"
        start_inputs = {"task": task_id, "to": "execute", "plan_version": entry["plan_version"],
                        "start_verifications": start_results}
        task, action = _start_task_action(
            ctx, path, task, "task.transition", holder, start_inputs,
            ["verify_approval", "resolve_start_verifications", "write_entry_snapshot", "transition"],
        )
        missing_evidence = _missing_start_verification_evidence(task, action)
        if missing_evidence:
            raise TaskError("WF_ACTION_INCOMPLETE",
                            {"reason": "start verifications not fixed in the action",
                             "missing": missing_evidence})
        rule_version = ctx.rule_version()
        for item in findings:
            if item["status"] != "satisfied":
                continue
            projection = gates.compute_P(ctx, task, item["id"], rule_version=rule_version)
            gates.write_receipt(
                task, item["id"], mode=item["mode"], projection=projection,
                rule_version=rule_version,
                evidence_refs=[f"task-start:{task_id}"],
            )
        missing_evidence = _missing_start_verification_evidence(task, action)
        if missing_evidence:
            # 结案前按真实后置重核：手工把步骤标 done 不能代替证据
            raise TaskError("WF_ACTION_INCOMPLETE",
                            {"reason": "start verifications missing before closing the action",
                             "missing": missing_evidence, "action": action.get("id")})
        task, assertion = _finish_task_action(
            ctx, path, task, "task.transition", holder, start_inputs, action,
        )
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="execute", task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="在批准触碰面内实施，然后 task-check",
        facts={"baseline_head": task.get("baseline_head"), "entry_snapshot": entry,
               "start_verifications": start_results, "control_assertion": assertion},
    )


# --------------------------------------------------------------------------
# 命令：task-replan / task-pause / task-resume
# --------------------------------------------------------------------------


def _load_decision_list(path):
    """读 Decision 文件（对象或数组），核必需字段。"""
    payload = records.load_json(path)
    if payload is None:
        raise TaskError("WF_PATH_INVALID", {"reason": "decision file missing", "path": path})
    items = payload if isinstance(payload, list) else [payload]
    required = ("source", "at", "subject", "object_digest", "choice", "reason")
    for item in items:
        if not isinstance(item, dict):
            raise TaskError("WF_RECORD_INVALID", {"reason": "decision must be an object"})
        missing = [key for key in required if key not in item]
        if missing:
            raise TaskError("WF_RECORD_INVALID", {"reason": "decision missing fields", "missing": missing,
                                                  "hint": "object_digest 填当前 PRD 摘要或 plan.version"})
    return items


def cmd_task_replan(ctx, args):
    if args.flag("--draft"):
        # 十六轮批V：规划变更决定草稿（object_digest 预填 PRD 摘要）。
        # 机械修订骨架已移到 task-approve --draft（a 组 a-2）：本命令正式执行只认
        # choice=replan——机械修订走 task-approve 的等价链，不重复人批。
        task_id = args.value("--task")
        if not task_id:
            raise TaskError("WF_USAGE_INVALID", {"reason": "task-replan requires --task <id>"})
        digest = _prd_digest_for_task(ctx, task_id)
        entries = [
            {"source": "TODO human:<来源>", "at": records.now_str(),
             "subject": f"replan {task_id}", "object_digest": digest, "choice": "replan",
             "reason": "TODO（人填写：实质规划变化是什么）"},
        ]
        return _decision_draft_result(ctx, task_id, entries, command="task-replan")
    from . import lock

    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-replan requires --task <id>"})
    # 打回 Plan 会让既有批准与 Check 失效，属"实质规划变更"：必须有人判证据
    # （机制稿 §2.2 的出口是"人澄清并重批"，第十五轮复审外部 P1）。
    decision_path = args.value("--decision")
    if not decision_path:
        raise TaskError("WF_SEMANTIC_DECISION", {
            "reason": "task-replan 需要人判证据：--decision <文件>（choice=replan）",
            "exits": ["由人出具 choice=replan 的 Decision 后重试",
                      "继续沿用现有规划，不改回 Plan",
                      "如需放弃任务，用 task-abandon（同样需要 Decision）"],
        })
    decisions = _load_decision_list(decision_path)
    # a 组 a-2：机械修订的真实入口是 task-approve（等价链）；本命令只认 replan。
    # 拒绝时给出指向真实入口的出口，不再让人在不成立的动作上空转。
    _mechanical_misrouted = [item for item in decisions
                             if isinstance(item, dict) and item.get("choice") == MECHANICAL_REVISION
                             and not any(decisions_mod.accepts("replan", other.get("choice"))
                                         for other in decisions if isinstance(other, dict))]
    if _mechanical_misrouted:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "机械修订不经 task-replan（本命令只认 choice=replan）",
                         "choices": [d.get("choice") for d in decisions]},
                        next_="用 task-approve --task <id> --decision <文件> 提交 choice=机械修订 的决定"
                              "（等价链核验后不重复人批）")
    if not any(decisions_mod.accepts("replan", item.get("choice")) for item in decisions):
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "决定文件里没有 choice=replan", "choices": [d.get("choice") for d in decisions]})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-replan"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived"})
        decision = next(item for item in decisions if decisions_mod.accepts("replan", item.get("choice")))
        # 决定必须指向本任务：subject 里要出现任务 id，或 object_digest 命中当前规划版本
        subject = decision.get("subject")
        subject_text = ",".join(subject) if isinstance(subject, list) else str(subject or "")
        current = current_plan_version(ctx.root, task)
        if isinstance(current, dict) and "error" in current:
            code, facts = current["error"]
            raise TaskError(code, dict(facts, reason="PRD 机读块不可解析，replan 无法核验当前规划",
                                       task=task_id))
        current_version = (current or {}).get("version")
        if task_id not in subject_text:
            raise TaskError("WF_SEMANTIC_DECISION", {
                "reason": "replan 决定的 subject 未指向本任务", "task": task_id, "subject": subject,
                "exits": ["重出决定，subject 写明任务 id",
                          "继续沿用现有规划，不改回 Plan"],
            })
        prd_digest_value = prd_digest(ctx.root, task)
        candidates = [item for item in (current_version, prd_digest_value) if item]
        if not candidates:
            raise TaskError("WF_TEMPLATE_INCOMPLETE", {
                "reason": "无法从 PRD 重算规划版本，replan 不能以空摘要放行",
                "task": task_id,
                "exits": ["先修正 PRD 的机读块（wf-plan:v1）后重试", "继续沿用现有规划，不改回 Plan"],
            })
        if decision.get("object_digest") not in candidates:
            raise TaskError("WF_SEMANTIC_DECISION", {
                "reason": "replan 决定的 object_digest 不等于当前规划版本或 PRD 摘要",
                "task": task_id, "object_digest": decision.get("object_digest"),
                "current_plan_version": current_version, "current_prd_digest": prd_digest_value,
                "exits": [f"用当前 PRD 摘要（{prd_digest_value}）或 plan.version（{current_version}）重出决定",
                          "继续沿用现有规划，不改回 Plan"],
            })
        # 实质规划变更：旧批准必须失效（机制稿 §2.2），但历史保留可追
        plan = dict(task.get("plan") or {})
        history = list(plan.get("approval_history") or [])
        if plan.get("approval") or plan.get("approved_version"):
            history.append({"approval": plan.get("approval"),
                            "approved_version": plan.get("approved_version") or plan.get("version"),
                            "invalidated_at": records.now_str(),
                            "reason": "task-replan"})
        plan["approval_history"] = history
        plan["approval"] = None
        plan["approved_version"] = None
        task["plan"] = plan
        task["phase"] = "plan"
        task, action = _start_task_action(ctx, path, task, "task.transition", holder,
                                          {"task": task_id, "to": "plan"},
                                          ["invalidate", "transition"])
        # 消费证据：人判决定入执行记录，动作上留引用（机制稿 §1.1、§11.2）
        execution = task.setdefault("execution", {})
        execution.setdefault("human_decisions", []).append(decision)
        action = dict(action or {})
        refs = list(action.get("decision_refs") or [])
        refs.append(records.plain_digest(decision))
        action["decision_refs"] = refs
        task["action"] = action
        task, assertion = _finish_task_action(ctx, path, task, "task.transition", holder,
                                              {"task": task_id, "to": "plan"}, action)
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="plan", task_id=task_id),
        next_="重新批准规划（task-approve）后 task-start 再入 Execute",
        facts={"note": "原有批准与检查留历史但当前无效；baseline_head 不变", "control_assertion": assertion},
    )


def cmd_task_pause(ctx, args):
    from . import lock

    task_id = args.value("--task")
    reason = args.value("--reason")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-pause requires --task <id>"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-pause"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "object already ended", "status": task.get("status"),
                             "terminal": task.get("terminal")},
                            next_="对象结束后只报告结果；恢复未完成的归档动作走专用恢复分支")
        task["paused"] = True
        handoff = task.setdefault("handoff", {})
        handoff["pending"] = list(handoff.get("pending") or []) + ([{"reason": reason}] if reason else [])
        task, action = _start_task_action(ctx, path, task, "task.pause", holder,
                                          {"task": task_id, "reason": reason}, ["pause"])
        task, assertion = _finish_task_action(ctx, path, task, "task.pause", holder,
                                              {"task": task_id, "reason": reason}, action)
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="人确认后 task-resume", facts={"control_assertion": assertion})


def cmd_task_resume(ctx, args):
    from . import lock

    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-resume requires --task <id>"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-resume"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "object already ended", "status": task.get("status"),
                             "terminal": task.get("terminal")},
                            next_="对象结束后只报告结果；恢复未完成的归档动作走专用恢复分支")
        # 恢复前重核保留 WIP：保留路径必须仍在工作树或仍是本任务可见的未提交改动
        retained = wip_paths(task)
        if retained:
            dirty = set(scope.uncommitted_paths(ctx.root))
            # R42：按记录里的指纹（内容/类型/可执行位）核对是否发生变化，不只判存在
            changed = []
            for entry in (task.get("handoff") or {}).get("wip", {}).get("paths") or []:
                if not isinstance(entry, dict) or not entry.get("path"):
                    continue
                now = fingerprint.item(ctx.root, entry["path"])
                saved = {key: entry.get(key) for key in ("path", "exists", "kind", "executable", "digest")}
                if now != saved:
                    changed.append({"path": entry["path"], "saved": saved, "current": now})
            if changed:
                raise TaskError("WF_WORKSPACE_UNRESOLVED",
                                {"reason": "retained WIP changed since it was recorded",
                                 "changed": changed},
                                next_="按变化后的实际内容重新核对归属与范围，必要时重新收工记录 WIP")
            deleted_on_record = {entry.get("path") for entry in
                                 (task.get("handoff") or {}).get("wip", {}).get("paths") or []
                                 if isinstance(entry, dict) and entry.get("exists") is False}
            # 记录即删除且当前仍不存在：属「合法删除」，只要已提交即视为已处置
            vanished = [item for item in retained
                        if item not in dirty and not os.path.exists(join(ctx.root, item))
                        and item not in deleted_on_record]
            if vanished:
                raise TaskError("WF_WORKSPACE_UNRESOLVED",
                                {"reason": "retained WIP changed under the task", "paths": vanished},
                                next_="先核实保留路径的实际去向（提交/反向修正/承接）再恢复")
            still = [item for item in retained if item in dirty]
            if not still:
                # 保留 WIP 已实际处置（提交/反向修正/删除已持久化）：补写解除结论（不新增命令）
                wip = task.setdefault("handoff", {}).setdefault("wip", {})
                wip["resolved"] = {"choice": "resume-after-disposal",
                                   "evidence": {"paths": retained, "dirty": [],
                                                "deleted": sorted(deleted_on_record)},
                                   "at": records.now_str()}
        task["paused"] = False
        task, action = _start_task_action(ctx, path, task, "task.transition", holder,
                                          {"task": task_id, "action": "resume"}, ["resume"])
        task, assertion = _finish_task_action(ctx, path, task, "task.transition", holder,
                                              {"task": task_id, "action": "resume"}, action)
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="继续当前阶段", facts={"control_assertion": assertion})


# --------------------------------------------------------------------------
# 命令：task-curate / task-check / task-knowledge / task-retrospect / task-attribute
# --------------------------------------------------------------------------




def _evidence_exists(root, task, ref):
    """证据引用是否可定位：任务目录内文件、check 记录 id、或 `handoff:`/`check:` 具名引用。"""
    if not isinstance(ref, str) or not ref:
        return False
    directory = task_dir(root, task.get("id"))
    if directory and os.path.exists(os.path.join(directory, ref)):
        return True
    known = {entry.get("id") for entry in task.get("check_history") or []} | {(task.get("check") or {}).get("id")}
    head, _, tail = ref.partition(":")
    if head == "check":
        return not tail or tail in known
    if head == "handoff":
        return bool(tail or (task.get("handoff") or {}))
    return ref in known


def _debug_idempotency_key(entry):
    """声明/裁定的幂等键（实现稿 §2.3.11 ④）。

    同一决定文件重入不得重复累计：键取**结构化字段**，不比原文措辞，
    因此"把同一事实写成另一句话"仍是两条（那是第二次声明，须由主会话授权内的 dedupe/裁定处置）。
    """
    import json as _json

    def freeze(value):
        return _json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)

    if "verification_id" in entry:
        return freeze({
            "kind": "declaration",
            "verification_id": entry.get("verification_id"),
            "counted": entry.get("counted"),
            "evidence_refs": sorted(entry.get("evidence_refs") or []),
            "dedupe_refs": sorted(freeze(pair) for pair in (entry.get("dedupe_refs") or [])),
        })
    return freeze({"kind": "ruling", "subject": entry.get("subject"),
                   "choice": entry.get("choice"),
                   "evidence_refs": sorted(entry.get("evidence_refs") or [])})


def _apply_debug_inputs(task, decisions, root=None, threshold=None):
    """把 Execute 期重复调试声明与 debug-ruling 裁定落到 execution（机制稿 §1.3）。"""
    execution = task.setdefault("execution", {})
    declarations = list(execution.get("debug_declarations") or [])
    rulings = list(execution.get("human_decisions") or [])
    for decision in decisions or []:
        subject = str(decision.get("subject", ""))
        if subject.startswith("debug-declaration:"):
            parts = subject.split(":")
            if len(parts) < 3:
                raise TaskError("WF_RECORD_INVALID", {"subject": subject, "reason": "declaration needs verification id and count"})
            verification_id = parts[1]
            counted = None
            dedupe = []
            evidence = []
            for token in parts[2:]:
                if token.startswith("count="):
                    try:
                        counted = int(token.split("=", 1)[1])
                    except ValueError:
                        raise TaskError("WF_RECORD_INVALID", {"subject": subject, "reason": "count must be an integer"})
                elif token.startswith("dedupe=") and token.split("=", 1)[1]:
                    for pair in token.split("=", 1)[1].split(","):
                        if not pair:
                            continue
                        if "/" not in pair:
                            raise TaskError("WF_RECORD_INVALID", {"subject": subject, "reason": "dedupe must be <check_id>/<verification_id>"})
                        check_id, vid = pair.split("/", 1)
                        dedupe.append({"check_id": check_id, "verification_id": vid})
                elif token.startswith("evidence=") and token.split("=", 1)[1]:
                    evidence.extend(token.split("=", 1)[1].split(","))
            if counted is None or counted <= 0:
                raise TaskError("WF_RECORD_INVALID", {"subject": subject, "reason": "counted must be a positive integer"})
            if len(dedupe) > counted:
                raise TaskError("WF_SEMANTIC_DECISION", {"subject": subject, "reason": "dedupe_refs exceed counted"})
            if root is not None:
                missing = [ref for ref in evidence if not _evidence_exists(root, task, ref)]
                if missing:
                    raise TaskError("WF_HISTORY_UNRESOLVED",
                                    {"subject": subject, "reason": "evidence_refs not found", "missing": missing})
            entry = {"verification_id": verification_id, "counted": counted,
                     "evidence_refs": evidence, "dedupe_refs": dedupe}
            # 幂等：同一决定文件重入不得重复累计（实现稿 §2.3.11 ④）
            if _debug_idempotency_key(entry) in {_debug_idempotency_key(item) for item in declarations}:
                continue
            declarations.append(entry)
            continue
        if subject.startswith("debug-ruling-"):
            from . import gates as gates_mod

            parsed = gates_mod.parse_debug_ruling(subject)
            if parsed is None:
                raise TaskError("WF_RECORD_INVALID",
                                {"subject": subject,
                                 "reason": "debug-ruling subject must be debug-ruling-<verification_id>-<multiple>"})
            # 未来倍数不能提前裁：裁定按最大倍数覆盖之前的全部倍数，写一个还没到的倍数
            # 会把尚未发生的倍数一并"覆盖"掉，之后的失败不再追问（a-P1）。
            # 同一决定文件里的声明还没落盘，先把它计入，否则"补记 + 裁新倍数"会被误拒。
            limit = threshold or gates_mod.DEBUG_THRESHOLD_DEFAULT
            pending = sum(item["counted"] for item in declarations
                          if item.get("verification_id") == parsed[0])
            merged = gates_mod.merged_failures(task, parsed[0]) + pending
            reached = merged // limit if limit else 0
            if parsed[1] > reached:
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"subject": subject, "multiple": parsed[1],
                                 "verification_id": parsed[0], "merged": merged,
                                 "threshold": limit, "reached": reached,
                                 "exits": [f"把倍数改成当前已达的 {reached}（或更小）后重跑",
                                           "确实要提前裁时，先让失败累计到该倍数再重跑"]})
            if not decisions_mod.accepts("debug_ruling", decision.get("choice")):
                raise TaskError("WF_SEMANTIC_DECISION", {"subject": subject,
                                                         "reason": "ruling choice must be 同一问题/不同问题"})
            if _debug_idempotency_key(decision) not in {_debug_idempotency_key(item) for item in rulings}:
                rulings.append(decision)
    # 证据必须真实存在，且 counted 不得少于去重后仍成立的证据条目（机制稿 §1.3、§11.2）
    known_checks = {entry.get("id") for entry in task.get("check_history") or []} | {(task.get("check") or {}).get("id")}
    for entry in declarations:
        refs = entry.get("evidence_refs") or []
        if not refs:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "declaration requires evidence_refs", "verification_id": entry.get("verification_id")})
        for pair in entry.get("dedupe_refs") or []:
            if pair.get("check_id") not in known_checks:
                raise TaskError("WF_HISTORY_UNRESOLVED",
                                {"reason": "dedupe_refs points to an unknown check", "dedupe": pair})
    # 同一 (check_id, verification_id) 对在全任务各声明中全局唯一
    seen = set()
    for entry in declarations:
        for pair in entry.get("dedupe_refs") or []:
            key = (pair.get("check_id"), pair.get("verification_id"))
            if key in seen:
                raise TaskError("WF_SEMANTIC_DECISION", {"duplicate_dedupe": list(key),
                                                         "reason": "same failed event counted twice"})
            seen.add(key)
    execution["debug_declarations"] = declarations
    execution["human_decisions"] = rulings


def cmd_task_curate(ctx, args):
    from . import lock

    task_id = args.value("--task")
    spec_path = args.value("--spec")
    purpose = args.value("--purpose")
    if not task_id or not spec_path or not purpose:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-curate requires --task --spec --purpose"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-curate"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task_id},
                            next_="归档后只经人确认的 repair 修记录")
        from . import paths as paths_mod

        try:
            normalized = paths_mod.normalize(spec_path)
        except paths_mod.InvalidPath as exc:
            raise TaskError("WF_PATH_INVALID", {"reason": str(exc), "spec": spec_path})
        digest = records.file_digest(join(ctx.root, normalized))
        if digest is None:
            raise TaskError("WF_PATH_INVALID", {"reason": "spec file missing", "spec": normalized})
        curation = [entry for entry in task.get("curation") or [] if entry.get("path") != normalized]
        curation.append({"path": normalized, "digest": digest, "purpose": purpose,
                         "selected_at": records.now_str(), "released": None})
        task["curation"] = curation
        inputs = {"task": task_id, "spec": normalized, "purpose": purpose}
        task, action = _start_task_action(ctx, path, task, "task.curate", holder, inputs, ["record"])
        task, assertion = _finish_task_action(ctx, path, task, "task.curate", holder, inputs, action,
                                              evidence_refs=[normalized])
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="读取正文：wf.py spec --file <path>",
                        facts={"curation": curation, "control_assertion": assertion})


def check_next_hint(task, check, ctx=None):
    """Check 成功后的下一跳（唯一实现）：复杂任务先审查，light 直接收工。

    此前固定写 "finish"，模型要么读文档、要么撞一次 `WF_REVIEW_INVALID` 才知道要先
    `review-launch`（dogfood 的"首次学费"）。
    """
    if (check or {}).get("result") != "pass":
        return "Check 未通过：按 facts 与 wf-repair-loop 处置后重查"
    hint = None
    # A3（三轮二审）：审查轮里仍有未关闭 blocking 时，下一跳不静默换到收工——
    # 可稳定计算（open_findings 唯一实现），让"修复→重查→再判"三步出现在 AI 必读的 next_。
    # 列表同时供 _binding 分支条件化：有未关闭 blocking 时不再说"可请人 finish"
    # （归档门禁会拦，同一条提示不能自相矛盾——2026-11-24）。
    open_blocking = []
    if ctx is not None:
        try:
            from . import review as _review_mod

            open_blocking = _review_mod.open_findings(ctx, task)["blocking"]
        except Exception:   # 投影失败不阻断下一跳本身
            open_blocking = []
    # 未关闭 blocking 的收敛动作只写一份：分支说"可以 finish"之前必须先满足它，
    # 否则同一条 next_ 会先叫人收工、再说 blocking 没关（归档门禁必拦）。
    blocking_fix = ""
    if open_blocking:
        rounds = sorted({int(item.get("round") or 0) for item in open_blocking})
        blocking_fix = (f"按处置规则关闭未关闭 blocking（轮次 {rounds}：在批准范围内修复 → "
                        "重跑 task-check → 重新发起判定；误报/重分类经复核登记 accepted 可同轮重判，"
                        "见 wf-review-action）")
    mentions_blocking = False
    if (task.get("plan") or {}).get("complexity") == "complex":
        export_note = ""
        if ctx is not None:
            # 三轮三审 b2／四轮 b3：外发确认是 launch 的前置门禁——与门禁**同一判据**
            # （export_scope_problems：任务 + 材料类集合都要匹配），不是"有没有文件"。
            # 已有确认但范围不符（如早期只确认了部分材料类）同样前置提示，
            # 不让 AI 按 next_ 撞 WF_EXPORT_NOT_AUTHORIZED。
            try:
                from . import authorize as _authorize_mod
                from . import tasks as _tasks_mod_self

                _dir = _tasks_mod_self.task_dir(ctx.root, task.get("id"))
                if _dir:
                    _problems = _authorize_mod.export_scope_problems(
                        _dir, task.get("id"), ["diff", "requirement", "test_results"])
                    if _problems:
                        export_note = ("；发起前先取人外发范围确认：`authorize record` 一条 choice=export"
                                       "（task + materials 三类，同任务同材料类集合持续有效）")
            except Exception:   # 投影失败不阻断下一跳本身
                pass
        # 同锚点重跑 Check 时不该再要一轮审查（十二轮 b-3）：归档判据已按锚点复用，
        # next 文案必须同口径，否则 AI 会照提示白开一轮。
        _result = ((task.get("reviews") or {}).get("result") or {})
        _bound = (_result.get("anchor") or {}).get("check_anchor")
        _current = ((task.get("check") or {}).get("anchor") or {}).get("check_anchor")
        # 只有**门禁也认为绑定**时才敢请人收工：报告摘要失配时 gates.review_binding 会拒，
        # next_ 若仍说"直接 finish"就是把 AI 送进一次必然失败的归档（十三轮 a-3）。
        # 原轮尚未判定、且锚点仍是当前锚点：继续那一轮（取材料/导入/判定），不要重新发起
        # 在途轮是否已判定：判据与 review 侧统一（2026-11-24）——走 latest_decision
        # （rounds[] 为空时从存量 result 回退），不再直读 rounds[]。两处判据分裂时
        # 同一轮会同时得到"仍在进行"（本函数）与"已判定"（review-status/repair_scope）。
        _review_mod_decided = None
        try:
            from . import review as _review_mod_hint

            _review_mod_decided = _review_mod_hint.latest_decision
        except Exception:      # 投影失败退回旧判据，不阻断下一跳本身
            _review_mod_decided = None
        _open_round = None
        for _launch in ((task.get("reviews") or {}).get("launches") or []):
            if not isinstance(_launch, dict):
                continue
            _round = int(_launch.get("round") or 0)
            if _review_mod_decided is not None:
                _decided = _review_mod_decided(task, _round) is not None
            else:
                _decided = any(int(item.get("round") or 0) == _round
                               for item in ((task.get("reviews") or {}).get("rounds") or [])
                               if isinstance(item, dict))
            _anchor = (_launch.get("anchor") or {}).get("check_anchor")
            if not _decided and _anchor and _anchor == _current:
                _open_round = _round
        _binding = False
        if _result.get("verdict") == "pass" and _bound and _bound == _current:
            try:
                from . import gates as _gates_mod

                _binding = bool(_gates_mod.review_binding(ctx, task).get("binding"))
            except Exception:      # noqa: BLE001 — 只读判定失败就退回保守提示
                _binding = False
        # 在途轮是否可继续由「轮次 + 锚点」决定（十四轮 b-1）：launch 不改写 result.verdict
        # （v66），旧轮的 fail/pass 只是历史，不得把在途轮挤成"重新发起"——那会沿 dogfood
        # 的失败路径再造人工提醒与重复轮次。
        # 在途轮的材料是否已被换掉（导入记录与当前身份不符，或按记录还原的旧身份）：
        # 这决定了"继续这一轮"能不能等来报告——同轮摘要锁下旧报告导不回来。
        _materials_stale = False
        _materials_unknown = False
        _materials_drift = False
        _materials_mixed = False
        _materials_current_missing = False
        _materials_history = False
        _materials_legacy = False
        _materials_present = False
        _materials_waiting = False
        _open_launch = (next((item for item in ((task.get("reviews") or {}).get("launches") or [])
                              if isinstance(item, dict)
                              and int(item.get("round") or 0) == _open_round), None)
                        if _open_round is not None else None)
        if _open_round is not None:
            try:
                from . import review as _review_mod_materials

                _imported = [item for item in ((task.get("reviews") or {}).get("imported") or [])
                             if isinstance(item, dict) and int(item.get("round") or 0) == _open_round]
                _now = _review_mod_materials.round_materials_identity(ctx, task, _open_round)
                _materials_current_missing = _now is None
                # 判据取自 `materials_identity_state`（与 review-context/decide 同源）：
                # drift 态下 `review-context` 会拒，不能指引"先取材料"；还原记录的身份来自
                # 记录本身，不算"材料被换过"。
                _state = _review_mod_materials.materials_identity_state(ctx, task.get("id"), _open_round)
                _materials_drift = _state["state"] == "drift"
                # 基线口径取 review 侧的唯一实现（不在这里重推一份，避免与阻断侧分叉）
                _basis = _review_mod_materials.round_materials_basis(_imported, _now)
                _materials_stale = _materials_drift or _basis["stale"]
                _materials_mixed = _basis["mixed"]
                _materials_history = _review_mod_materials.round_is_history(_imported)
                _materials_legacy = _state["state"] in ("legacy", "legacy_adopted")
                _materials_present = bool(_state.get("present"))
                _materials_waiting = bool(_open_launch is not None and
                                          len(_imported) < len(_open_launch.get("slots") or []))
            except Exception:      # noqa: BLE001 — 只读投影失败：不明说失配，但让下一跳先看状态
                _materials_stale = False
                _materials_unknown = True
        if _open_round is not None and _materials_current_missing and (_materials_stale or _materials_mixed):
            # `write_materials` 是确定性的：同 Check 重建会逐字节复现身份，原报告继续有效；
            # 只有 Check 已换 id 或交付面/规格已变才需要重写/开新一轮。
            if _materials_legacy:
                hint = (f"第 {_open_round} 轮审查在途，当前无材料身份（目录仍在、缺 manifest 或按现场字节采纳）："
                        "重跑 review-context 采纳现场字节（现场字节未改过时身份会复现，原报告继续有效；"
                        "采纳沿用导入记录的被审 check_id；字节改过才需重写/新轮）后 review-decide")
            elif _materials_present:
                hint = (f"第 {_open_round} 轮审查在途，但本轮材料包不完整（缺必需文件）："
                        "删 materials/ 下全部内容后重跑 review-context 重建（同 Check 身份会复现），"
                        "再 review-decide；不要按旧包采纳")
            else:
                hint = (f"第 {_open_round} 轮审查在途，但本轮材料目录已不在（当前无材料身份）："
                        "重跑 review-context 重建材料（同 Check 身份会逐字节复现，原报告继续有效），"
                        "再 review-decide；只有 Check 已重跑换 id 或交付面/规格已变才需重写/开新一轮")
            if _materials_waiting:
                hint += "；还有槽位未到，等齐后再判定"
        elif _open_round is not None and _materials_current_missing and _materials_history:
            hint = (f"第 {_open_round} 轮审查在途，材料目录已不在，但报告都是还原记录/无现场身份的历史证据："
                    "重跑 review-context 重建材料（同 Check 身份会复现），再 review-decide；"
                    "有槽位未到先等齐、有报告待导入先 review-import")
        elif _open_round is not None and _materials_drift and not _materials_history:
            if not _imported:
                hint = (f"第 {_open_round} 轮审查在途，材料已被改动（drift），但本轮还没有导入报告："
                        "有备份就把原字节放回材料目录并重跑 review-context；没有备份则删材料内容与 "
                        "manifest 后重建（同 Check 身份会复现），再让 reviewer 继续/写报告；"
                        "直接 review-decide 会被拒")
            else:
                hint = (f"第 {_open_round} 轮审查在途，材料已被改动（drift）且有 live 报告："
                        "有备份就把原字节放回材料目录并重跑 review-context；没有备份则删材料内容与 "
                        "manifest 后重建（同 Check 身份会复现，原报告继续有效），再 review-decide；"
                        "只有 Check 已重跑换 id 或交付面/规格已变才需重写/开新一轮")
        elif _open_round is not None and _materials_drift:
            if _materials_waiting:
                hint = (f"第 {_open_round} 轮审查在途，材料已被改动（drift），报告都是还原/无身份的历史证据，"
                        "但还有槽位未到：等齐后再 review-decide；若还有报告待导入，先恢复材料再导入")
            else:
                hint = (f"第 {_open_round} 轮审查在途，材料已被改动（drift），但报告都是还原/无身份的历史证据："
                        "可直接 review-decide；若还有报告待导入，先把原字节放回材料目录并重跑 "
                        "review-context 再导入")
            hint += ("；要恢复可核身份也走同一恢复动作——此时先取材料会撞 drift 校验")
        elif _open_round is not None and _materials_mixed:
            hint = (f"第 {_open_round} 轮审查在途，且还原记录与现场材料混在一轮："
                    "把正常条目也按 `--restore` 重导（标成历史证据），或按新材料重写并开新一轮；"
                    "直接判定会撞混合基线")
        elif _open_round is not None and _materials_stale:
            hint = (f"第 {_open_round} 轮审查在途，但材料已被换过（导入记录与当前材料身份不符）："
                    "同轮不能重导——有备份就把原字节放回材料目录并重跑 review-context，"
                    "没有备份则按新材料重写并开新一轮；等 reviewer 重交解决不了")
        elif _open_round is not None:
            hint = (f"第 {_open_round} 轮审查仍在进行且锚点未变（同内容重验）："
                    "继续这一轮——review-context 取材料（本轮材料按首轮物化固定，"
                    "不随 Check 重跑改写）→ 人跑 reviewer → 导入 → 判定；"
                    "不要重新 review-launch")
            _impl = {_review_mod_materials.review_cli((_open_launch or {}).get("implementation_cli"))}
            _impl.discard(None)
            _reviewers = {_review_mod_materials.normalize_agent(item.get("agent") or item.get("slot"))
                          for item in _imported}
            if _impl & _reviewers:
                hint = (f"第 {_open_round} 轮材料已到齐，但审查 CLI 与实施 CLI 重叠："
                        "先换异种 reviewer/补报告，再判定；资格事实见 review-status")
            if _materials_unknown:
                hint += "（材料身份没核成：先看 `review-status` 再决定是否继续）"
            if _binding and open_blocking:
                hint += ("；已有绑定当前锚点的 pass 结论，但 blocking 仍未关闭——"
                         "该轮判定后还需" + blocking_fix + "，才能请人 finish")
                mentions_blocking = True
            elif _binding:
                hint += "；已有绑定当前锚点的 pass 结论，该轮判定后即可请人 finish"
        elif _binding:
            if open_blocking:
                hint = ("已有审查结论绑定当前内容锚点，但 blocking 仍未关闭：先"
                        + blocking_fix + "，再请人 finish——直接 finish 会被归档门禁拦下")
                mentions_blocking = True
            else:
                hint = ("已有审查结论绑定当前内容锚点（同内容重跑）：可请人直接 finish；"
                        "内容或规划再变才需要重新 review-launch")
        elif _result.get("verdict") == "pass" and _bound and _bound == _current:
            hint = ("已有审查结论，但引用报告已失效或不再绑定（摘要失配/文件被改）："
                    "重新导入同一份报告，或 review-launch 换一轮后再 finish")
        else:
            hint = ("复杂任务：先 review-launch 发起一轮审查（wf-review），"
                    "导入/判定通过后再请人调用 finish" + export_note)
            if open_blocking:
                hint += "；发起前" + blocking_fix
                mentions_blocking = True
    else:
        # 轻量任务本可直收工，但已有 blocking（返工/复核遗留）时先收口再 finish：
        # 否则 finish 必然撞归档门禁 C2。
        hint = ("人了解结果后调用 finish（wf-finish）" if not open_blocking
                else "先" + blocking_fix + "，再请人调用 finish（wf-finish）")
        mentions_blocking = bool(open_blocking)
    if blocking_fix and not mentions_blocking:
        hint += "；注意：" + blocking_fix
    # §0.2 试点期抽样提示（2026-11-21 降档为建议，不阻断；无 picks 时附注）
    try:
        from . import sampling as sampling_mod

        if not sampling_mod.selection(task)["picks"]:
            hint += "；" + sampling_mod.PILOT_HINT
    except Exception:  # 提示失败不影响下一跳本身
        pass
    return hint


def cmd_task_check(ctx, args):
    """Check 的固定五步（机制稿 §3.5），**验证命令在锁外执行**（机制稿 §4.1）。

    三段：
    ① 锁内准备——绑定/写权/状态核验、调试声明落点、开工门禁、范围核对与锚点固定；
    ② **锁外执行**——逐条跑已批准的验证命令（长操作不长期持 OS 锁）；
    ③ 锁内定稿——重取锁后重核 holder 与代次、重算锚点（变了即 `WF_CHECK_STALE`）、
       结束前重算范围核对，然后组装记录、写 check_history 与回执、结案动作。

    「锁外窗口期间对象被改」不靠新判据兜底：锚点重算与 `run_check_finish` 里既有的
    扫描前后比对（`scan_after != scan_before` → `WF_CHECK_STALE`）本就是同一件事。
    """
    from . import check as check_mod, cli, gates, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    review_notes = args.value("--review-notes")
    exclusion_file = args.value("--workspace-exclusion")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-check requires --task <id>"})
    if args.flag("--review-notes-draft"):
        # 2026-11-23：双轴内部审查结论是 AI 必须手写的结构化文件，补只读骨架入口
        # （与 archive/stop/review-decide 的 --draft 同型：只打印不落盘，TODO 照抄会被
        # _parse_review_notes 判为非法 conclusion）。
        path = _require_task_dir(ctx, task_id)
        task_record = records.load_json(os.path.join(path, "task.json")) or {}
        skeleton = {
            "standard": {
                "conclusion": "TODO（pass|fail|undecided）",
                "basis": "TODO（依据：规范/契约条款与核对结果）",
            },
            "requirement": {
                "conclusion": "TODO（pass|fail|undecided）",
                "basis": "TODO（依据：PRD/验收项与实际结果）",
            },
        }
        return codes.result(
            "WF_OK",
            object={"id": task_id, "name": task_record.get("title")},
            position_=codes.position(scope="task", phase=task_record.get("phase"), task_id=task_id),
            next_="把两个轴的 TODO 换成结论与依据，写到 facts.path 后再去掉 --review-notes-draft 重跑 task-check",
            facts={"draft": skeleton, "path": os.path.join(path, "review-notes.json"),
                   "note": "草稿只读；TODO 原样提交会被判为非法 conclusion"},
        )
    decisions = cli._load_decision(decision_path) if decision_path else []
    exclusion_entries, exclusion_problems = scope.load_exclusion_declarations(exclusion_file)
    if exclusion_problems:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"problems": exclusion_problems,
                         "exits": ["按问题清单修正声明文件（paths 只写具体路径，确认要带 by/at/quote/source）"]})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-check"):
        _record, holder = ctx.require_held(task=task_id)
        path = _require_task_dir(ctx, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") != "in_progress":
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "check requires in_progress", "status": task.get("status")})
        if task.get("paused") or task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION", {"paused": task.get("paused"), "suspended": task.get("suspended")})
        _apply_debug_inputs(task, decisions, ctx.root, ctx.debug_threshold())
        findings = gates.evaluate(ctx, task, "before_check")
        blocking = [item for item in findings if item["status"] == "missing"]
        if blocking:
            raise TaskError(blocking[0]["code"] or "WF_SEMANTIC_DECISION", {"missing": blocking})
        try:
            state = check_mod.run_check_scope(ctx, task, decisions, review_notes,
                                              exclusion_entries=exclusion_entries)
        except check_mod.CheckError as exc:
            raise TaskError(exc.code, exc.facts)

    # ② 锁外执行：这一段可能跑几分钟，不能占着 OS 锁
    try:
        commands = check_mod.run_check_execute(ctx, task, state)
    except check_mod.CheckError as exc:
        raise TaskError(exc.code, exc.facts)

    # ③ 锁内定稿：重核写权与代次，重算锚点（期间对象被改 → 本次不判 pass）
    with lock.acquire(ctx.root, holder_hint="task-check"):
        _record, holder = ctx.require_held(task=task_id)
        path = _require_task_dir(ctx, task_id)
        # **不重读记录**：写权全程未释放（holder 仍是本会话），别的会话无法改这条记录；
        # 而准备段已经把调试声明等输入写进了内存态，重读会把它们丢掉（cp2-A13 / cp5-B4 实测）。
        # 锁外期间真正会变的是**工作树内容**，那由下面的锚点重算与 finish 的扫描比对判。
        anchor_now, _parts_now = check_mod.current_anchor(ctx, task)
        if anchor_now != state["anchor"]:
            raise TaskError("WF_CHECK_STALE",
                            {"reason": "锚点在锁外执行期间发生变化",
                             "before": state["anchor"], "after": anchor_now,
                             "exits": ["按当前内容重新 Check", "确认变化不影响结论后重新批准并重检"]})
        try:
            check, code, facts = check_mod.run_check_finish(ctx, task, state, commands)
        except check_mod.CheckError as exc:
            raise TaskError(exc.code, exc.facts)
        history = list(task.get("check_history") or [])
        if task.get("check"):
            history.append(task["check"])
        task["check_history"] = history
        task["check"] = check
        inputs = {"task": task_id, "check": check["id"]}
        task, action = _start_task_action(ctx, path, task, "task.check", holder, inputs,
                                          ["scope_check", "resolve_verifications", "run_verifications",
                                           "internal_review", "write_check"])
        rule_version = ctx.rule_version()
        gates.write_receipt(task, "task.work-satisfied", mode="once",
                            projection=gates.compute_P(ctx, task, "task.work-satisfied", rule_version=rule_version),
                            rule_version=rule_version, evidence_refs=[check["id"]])
        if check["result"] == "pass":
            gates.write_receipt(task, "task.check-passed", mode="repeatable",
                                projection=gates.compute_P(ctx, task, "task.check-passed", check=check,
                                                           rule_version=rule_version),
                                rule_version=rule_version, evidence_refs=[check["id"]])
            task["phase"] = "finish"
        task, assertion = _finish_task_action(ctx, path, task, "task.check", holder, inputs, action,
                                              evidence_refs=[check["id"]])
    if code:
        raise TaskError(code, dict(facts, check=check["id"]))
    next_hint = check_next_hint(task, check, ctx=ctx)
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_=next_hint,
        facts={"check": check["id"], "anchor": check["anchor"], "object_paths": facts.get("object_paths"),
               "acceptance_results": check["acceptance_results"], "commands": check["commands"],
               "control_assertion": assertion,
               # vendor_dirty 消费点（2026-11-21 批C）：框架自有改动不入交付/审查，但必须可见——
               # 非阻断；出现时由人确认归属（回源仓库立项），不能悄悄并入业务任务。
               "vendor_dirty": facts.get("vendor_dirty") or [],
               # W2-7：vendor 归属确认的可审计记录投影（kind=框架改动 的判断条目）——
               # 不阻断、不参与判定，纯事实：出现 vendor_dirty 时人已确认过归属与否一目了然。
               "vendor_judgments": [entry for entry in (task.get("judgments") or [])
                                    if isinstance(entry, dict) and entry.get("kind") == "框架改动"],
               # b-1（九轮，事实不阻断）：开工前已存在的交付路径，Check facts 同步可见
               "preexisting_in_scope": facts.get("preexisting_in_scope") or []},
    )


def _require_task_dir(ctx, task_id):
    """任务记录目录；记录从工作树消失时给结构化原因与恢复出口，不拼 None 路径（N21-3）。"""
    path = task_dir(ctx.root, task_id)
    if path:
        return path
    raise TaskError("WF_RECORD_INVALID", {
        "reason": "task record is missing from the worktree",
        "task": task_id,
        "exits": ["从 Git 恢复该任务目录（git checkout -- <path>）后重试",
                  "确认记录确实作废后按 repair --dispose / task-abandon 处置",
                  "不新建同 id 任务覆盖历史"],
    })


def cmd_task_knowledge(ctx, args):
    from . import lock

    task_id = args.value("--task")
    if args.flag("--changes-draft"):
        if not task_id:
            raise TaskError("WF_USAGE_INVALID", {"reason": "--changes-draft requires --task <id>"})
        path = task_dir(ctx.root, task_id)
        if not path:
            raise TaskError("WF_RECORD_INVALID", {"reason": "task record is missing", "task": task_id})
        task_record = records.load_json(os.path.join(path, "task.json")) or {}
        skeleton = [{"action": "TODO（add|update|merge|rename|delete）",
                     "path": "TODO（spec 相对路径）",
                     "reason": "TODO（变更理由）",
                     "summary": "TODO（≤80 字摘要）"}]
        return codes.result(
            "WF_OK",
            object={"id": task_id, "name": task_record.get("title")},
            position_=codes.position(scope="task", phase=task_record.get("phase"), task_id=task_id),
            next_="填好 changes 数组写到 facts.path，去掉 --changes-draft 后按 --decision updated 重跑",
            facts={"draft": skeleton, "path": os.path.join(path, "knowledge-changes.json")},
        )
    decision = "no-update" if args.flag("--no-update") else args.value("--decision")
    changes_path = args.value("--changes")
    if not task_id or decision not in ("no-update", "updated"):
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-knowledge requires --task <id> --decision no-update|updated"})
    changes = []
    if changes_path:
        loaded = records.load_json(changes_path)
        if loaded is None:
            raise TaskError("WF_PATH_INVALID", {"reason": "changes file missing", "path": changes_path})
        changes = loaded if isinstance(loaded, list) else [loaded]
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-knowledge"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task_id},
                            next_="归档后只经人确认的 repair 修记录")
        task["knowledge"] = {"decision": decision, "changes": changes, "evidence": []}
        inputs = {"task": task_id, "decision": decision}
        task, action = _start_task_action(ctx, path, task, "task.knowledge-dispose", holder, inputs, ["record"])
        from . import gates

        gates.write_receipt(task, "task.knowledge-disposed", mode="once",
                            projection=gates.compute_P(ctx, task, "task.knowledge-disposed",
                                                       rule_version=ctx.rule_version()),
                            rule_version=ctx.rule_version())
        task, assertion = _finish_task_action(ctx, path, task, "task.knowledge-dispose", holder, inputs, action)
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="finish 前核对",
                        facts={"knowledge": task["knowledge"], "control_assertion": assertion})


def cmd_task_retrospect(ctx, args):
    from . import gates, lock

    task_id = args.value("--task")
    evidence_path = args.value("--evidence")
    if not task_id or not evidence_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-retrospect requires --task <id> --evidence <path>"})
    # 复盘只收一份证据：结论在 `evidence.conclusion`，触发集合由入口重算。
    # 此前还接受 `--decision`（决定文件）却从不消费——读入即丢弃，比拒绝更贵
    # （AI 会以为"已经并进记录"）。2026-11-23 五轮复审 a-1 删除该旗标。
    evidence = records.load_json(evidence_path)
    if evidence is None:
        raise TaskError("WF_PATH_INVALID", {"reason": "evidence file missing", "path": evidence_path})
    _require_binding(ctx, task_id)
    required = bool(gates.retrospective_triggers(ctx.root, _load_or_fail(ctx, task_id), ctx.debug_threshold()))
    with lock.acquire(ctx.root, holder_hint="task-retrospect"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task_id},
                            next_="归档后只经人确认的 repair 修记录")
        conclusion = evidence.get("conclusion") if isinstance(evidence, dict) else None
        if not conclusion:
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "retrospective conclusion missing"})
        task["retrospective"] = {"required": required, "evidence": evidence, "conclusion": conclusion}
        inputs = {"task": task_id, "required": required}
        task, action = _start_task_action(ctx, path, task, "task.retrospect", holder, inputs, ["record"])
        gates.write_receipt(task, "task.retrospective-done", mode="once",
                            projection=gates.compute_P(ctx, task, "task.retrospective-done",
                                                       rule_version=ctx.rule_version()),
                            rule_version=ctx.rule_version(), evidence_refs=[evidence_path])
        task, assertion = _finish_task_action(ctx, path, task, "task.retrospect", holder, inputs, action,
                                              evidence_refs=[evidence_path])
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="继续 Finish", facts={"retrospective": task["retrospective"],
                                                    "control_assertion": assertion})


def cmd_task_attribute(ctx, args):
    from . import lock, scope as scope_mod

    task_id = args.value("--task")
    commit = args.value("--commit")
    if not task_id or not commit:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-attribute requires --task <id> --commit <oid>"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-attribute"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "attribution only for active tasks"})
        code, _ = scope_mod.git(ctx.root, "cat-file", "-e", f"{commit}^{{commit}}")
        if code != 0:
            raise TaskError("WF_HISTORY_UNRESOLVED", {"commit": commit, "reason": "commit not found"})
        message = scope_mod.commit_message(ctx.root, commit)
        trailer = scope_mod.commit_trailer_task(message)
        if trailer and trailer != task_id:
            raise TaskError("WF_SEMANTIC_DECISION", {"conflict": {"trailer": trailer, "requested": task_id}})
        attribution = task.setdefault("attribution", {"decisions": [], "inherited": []})
        attribution.setdefault("decisions", []).append({"commit": commit, "decision": "attributed"})
        inputs = {"task": task_id, "commit": commit}
        task, action = _start_task_action(ctx, path, task, "task.attribute", holder, inputs, ["record"])
        task, assertion = _finish_task_action(ctx, path, task, "task.attribute", holder, inputs, action,
                                              evidence_refs=[commit])
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_="重新 Check 后继续",
                        facts={"commit": commit, "paths": scope.commit_paths(ctx.root, commit),
                               "control_assertion": assertion})


# --------------------------------------------------------------------------
# 命令：task-abandon / archive
# --------------------------------------------------------------------------


def _abandon_resume(ctx, task_id):
    """放弃的续做：按目录位置与提交事实逐步恢复（调用方必须已持有互斥与写权）。"""
    task = load_task(ctx.root, task_id)
    if task is None or task.get("status") != "archived" or task.get("terminal") != "abnormal":
        return None
    directory = task_dir(ctx.root, task_id)
    if not directory:
        return None
    record_rel = os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/")
    old_rel = None
    if not record_rel.startswith(".wf/tasks/archive/"):
        # 终态已写但目录未移动：先完成移动
        destination = _archive_destination(ctx.root, task)
        if os.path.exists(destination):
            raise TaskError("WF_TARGET_COLLISION",
                            {"destination": os.path.relpath(destination, str(ctx.root))})
        old_rel = os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/")
        moved = _move_task(ctx.root, directory, destination, task)
        task = records.load_json(os.path.join(moved, "task.json"))
        record_rel = os.path.relpath(moved, str(ctx.root)).replace(os.sep, "/")
    if _record_committed(ctx.root, record_rel):
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            facts={"terminal": "abnormal", "record_persisted": True,
                                   "note": "放弃已结案，无需重复"})
    _commit_paths(ctx.root, [record_rel], f"wf: abandon {task_id}\n\nwf-task: {task_id}",
                  moved_from=(_moved_from(ctx.root, old_rel) or task.get("moved_from")))
    if not _record_committed(ctx.root, record_rel):
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"record": record_rel, "reason": "归档记录尚未进入提交"},
                        next_="持写权重入以续做记录提交")
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        facts={"terminal": "abnormal", "record_persisted": True, "resumed_commit": True,
                               "note": "只报告退出完成与保留风险，不报告业务验收通过"})


def cmd_task_abandon(ctx, args):
    """单任务放弃（机制稿 §6.4）。

    绑定、写权与「已异常归档但记录组未提交」的续做入口留在这里；
    放弃本体（预览 → 逐项去向 → 提交授权 → 异常终态 → 目录移动 → 记录组提交）
    在 `_apply_abandon()`，供本入口与 `run terminate` 共用（两个入口的绑定对象不同：
    任务 vs 实例，但「放弃一个任务」的判定只有一处）。
    """
    from . import cli, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    disposition_path = args.value("--disposition")
    if not task_id or not decision_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-abandon requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    disposition = None
    if disposition_path:
        loaded = records.load_json(disposition_path)
        if loaded is None:
            raise TaskError("WF_PATH_INVALID", {"reason": "disposition file missing"})
        disposition = loaded
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-abandon"):
        pending_resume = load_task(ctx.root, task_id)
        if pending_resume is not None and pending_resume.get("status") == "archived" \
                and pending_resume.get("terminal") == "abnormal":
            ctx.require_held(task=task_id)
            return _abandon_resume(ctx, task_id)
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived"})
        return _apply_abandon(ctx, task_id, task, path, decisions, disposition, holder)


def _apply_abandon(ctx, task_id, task, path, decisions, disposition, holder):
    """放弃本体（机制稿 §6.4）：调用方负责绑定/写权/锁与「任务未归档」的前置。"""
    from . import cli  # noqa: F401  （保留入口层引用，便于调试时同源调用）

    preview = _abandon_preview(ctx, task)
    # 输入形态归一：`--disposition` 传 JSON 数组（AI 首用的高概率写法）按 {"changes": [...]} 解释；
    # 否则 `(disposition or {}).get(...)` 会在 list 上抛裸 AttributeError（K10：不得裸异常）。
    if isinstance(disposition, list):
        disposition = {"changes": disposition}
    elif disposition is not None and not isinstance(disposition, dict):
        raise TaskError("WF_PATH_INVALID",
                        {"reason": '--disposition 须为对象 {"changes": [...]} 或数组 [...]',
                         "got": type(disposition).__name__,
                         "example": {"changes": [{"object": "<路径或 glob>", "reason": "去向理由"}]}})
    # 空处置（工作树干净 / 无必须处置项）应放行，而不是卡在预览态：
    # 「没给处置」与「处置为空」是两回事，前者要预览、后者是有效结论。
    needs_disposition = bool(preview.get("uncommitted")) or bool(preview.get("required_disposition_for"))
    if disposition is None and needs_disposition:
        return codes.result(
            "WF_SEMANTIC_DECISION",
            object={"id": task_id, "name": task.get("title")},
            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
            next_="人逐项给出 --disposition（object/decision_ref/reason）后重入",
            facts={"preview": preview,
                   "need": ["--disposition 覆盖 preview.uncommitted 的每一项"],
                   "note": "预览只读；本次未写入任何记录"},
        )
    uncovered = _uncovered_paths(preview["uncommitted"], disposition)
    if uncovered:
        return codes.result(
            "WF_WORKSPACE_UNRESOLVED",
            object={"id": task_id, "name": task.get("title")},
            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
            next_="在 disposition.changes 中为每个未提交路径给出实际去向后重入",
            facts={"preview": preview, "uncovered": uncovered},
        )
    # R24：未提交改动须「已授权提交」或「由人实际处置」，不遗留无主 WIP（机制稿 §6.4）
    from . import paths as paths_mod

    grants = [item for item in decisions[1:]
              if decisions_mod.accepts("commit_grant", item.get("choice"))]
    grant_paths = [path for grant in grants for path in _subject_paths(grant.get("subject"))]
    preview_uncommitted = list(preview["uncommitted"])
    to_commit = [path for path in preview_uncommitted
                 if any(path == grant_path or paths_mod.match_path(grant_path, path)
                        for grant_path in grant_paths)]
    if to_commit:
        _commit_paths(ctx.root, sorted(to_commit), f"wf: abandon {task_id}\n\nwf-task: {task_id}")
    leftover = [path for path in scope.uncommitted_paths(ctx.root) if path in set(preview_uncommitted)]
    if leftover:
        return codes.result(
            "WF_WORKSPACE_UNRESOLVED",
            object={"id": task_id, "name": task.get("title")},
            position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
            next_="为残留路径补提交授权，或由人实际处置（提交/反向修正/承接）后重入",
            facts={"leftover": leftover, "granted": sorted(to_commit), "preview": preview},
        )
    changes = (disposition or {}).get("changes") or []
    pending = (disposition or {}).get("pending") or []
    task["disposition"] = {
        "kind": "abandon",
        "decision": decisions[0],
        "changes": changes,
        "targets": (disposition or {}).get("targets") or [],
        "pending": pending,
    }
    task["commit_grants"] = [item for item in decisions[1:]
                             if decisions_mod.accepts("commit_grant", item.get("choice"))]
    inputs = {"task": task_id, "kind": "abandon"}
    task, action = _start_task_action(ctx, path, task, "task.abandon", holder, inputs,
                                      ["record_decision", "apply_disposition"])
    if task["disposition"]["pending"]:
        task, assertion = _finish_task_action(ctx, path, task, "task.abandon", holder, inputs, action)
        raise TaskError("WF_WORKSPACE_UNRESOLVED",
                        {"pending": task["disposition"]["pending"], "reason": "改动去向未落实"})
    task["paused"] = False
    task["suspended"] = False
    task["terminal"] = "abnormal"
    task["status"] = "archived"
    task["archived_at"] = records.now_str()
    task, assertion = _finish_task_action(ctx, path, task, "task.abandon", holder, inputs, action)
    destination = _archive_destination(ctx.root, task)
    old_rel = os.path.relpath(path, str(ctx.root)).replace(os.sep, "/")
    _move_task(ctx.root, path, destination, task)
    record_rel = os.path.relpath(destination, str(ctx.root)).replace(os.sep, "/")
    _commit_paths(ctx.root, [record_rel], f"wf: abandon {task_id}\n\nwf-task: {task_id}",
                  moved_from=_moved_from(ctx.root, old_rel))
    if not _record_committed(ctx.root, record_rel):
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"record": record_rel, "reason": "归档记录尚未进入提交",
                         "resume": "持有写权重入 task-abandon 可续做记录提交"},
                        next_="持写权重入以续做记录提交")
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                    position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                    next_="写权释放后可结束会话",
                    facts={"terminal": "abnormal", "archived_at": task["archived_at"],
                           "record_persisted": True,
                           "control_assertion": assertion,
                           "note": "只报告退出完成与保留风险，不报告业务验收通过"})




def _abandon_preview(ctx, task):
    """放弃前的只读预览：未提交改动、已有提交、下游与未完返工。"""
    receipts = task_receipts(ctx.root)
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    uncommitted = sorted(set(classified["buckets"]["e"]) & set(scope.uncommitted_paths(ctx.root)))
    attributed = scope.attributed_paths(ctx.root, task.get("id"), task.get("baseline_head"))
    downstream = []
    unfinished_rework = []
    for _path, other in iter_tasks(ctx.root):
        if other.get("id") == task.get("id"):
            continue
        if task.get("id") in (other.get("prerequisites") or []):
            downstream.append(other.get("id"))
        if other.get("rework_of") == task.get("id") and other.get("status") != "archived":
            unfinished_rework.append(other.get("id"))
    return {
        "task": {"id": task.get("id"), "status": task.get("status"), "phase": task.get("phase"),
                 "terminal": task.get("terminal")},
        "uncommitted": uncommitted,
        "attributed_paths": attributed,
        "downstream": sorted(downstream),
        "unfinished_rework": sorted(unfinished_rework),
        "required_disposition_for": uncommitted,
    }


def _uncovered_paths(paths, disposition):
    from . import paths as paths_mod

    objects = [item.get("object") for item in (disposition or {}).get("changes") or []
               if isinstance(item, dict)]
    uncovered = []
    for path in paths:
        if any(obj == path or (isinstance(obj, str) and paths_mod.match_path(obj, path)) for obj in objects):
            continue
        uncovered.append(path)
    return uncovered


def _archive_destination(root, task):
    archived_at = task.get("archived_at") or records.now_str()
    month = archived_at[:7]
    name = os.path.basename(task_dir(root, task["id"]) or dir_name(task["id"], task.get("title", "task")))
    return join(root, f"{ARCHIVE_REL}/{month}/{name}")


def _move_task(root, source, destination, task=None):
    if os.path.exists(destination):
        raise TaskError("WF_TARGET_COLLISION", {"destination": os.path.relpath(destination, str(root))})
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.move(source, destination)
    if isinstance(task, dict):
        # 记录移动来源：续做时用它定位"该提交的删除"，不靠目录名/文件名猜测（F15-1）
        task["moved_from"] = os.path.relpath(source, str(root)).replace(os.sep, "/")
        save_task(root, destination, task)
    return destination


def _deleted_paths(root, rel):
    """返回 `rel` 目录下**仍处于未提交删除**的精确文件路径（不含新增/修改）。"""
    from . import scope as scope_mod

    if not rel:
        return []
    _code, text = scope_mod.git(root, "status", "--porcelain", "-z", "--", rel)
    fields = [item for item in (text or "").split("\0")]
    deleted = []
    index = 0
    while index < len(fields):
        item = fields[index]
        if not item:
            index += 1
            continue
        status, path = item[:2], item[3:]
        # 改名/复制（R/C）在 -z 下把"源路径"放在紧随其后的独立字段里
        if status[:1] in ("R", "C") or status[1:2] in ("R", "C"):
            index += 2
            if status[1:2] == "D" and path:
                deleted.append(path)
            continue
        index += 1
        if "D" in status and path:
            deleted.append(path)
    return deleted


def _moved_from(root, rel):
    """目录移动的源路径：只要 Git 侧仍有未提交删除就纳入提交。

    "目录是否存在"不能代表"旧文件已恢复"——空目录或部分恢复都会让 exists() 骗过判定
    （第十四轮复审 F14-1）。判据改为 `git status --porcelain` 是否报出删除。
    """
    if not rel:
        return None
    from . import scope as scope_mod

    _code, text = scope_mod.git(root, "status", "--porcelain", "--", rel)
    if any(line.strip().startswith(("D ", "D	", " D")) or " D " in line for line in text.splitlines()):
        return rel
    return None


def _chain_trailer(task):
    """K9：把记录写链的链头写进提交 trailer（只承诺可检出，不承诺防伪造）。"""
    head = ((task.get("write_mark") or {}).get("action_id")) or (task.get("action") or {}).get("id")
    return f"\nwf-chain-head: {head}" if head else ""


def _tracked_under(root, relative):
    """HEAD 里该目录下的**已跟踪**路径（未跟踪目录返回空：没有删除可提交）。"""
    if not relative:
        return []
    code, out = scope.git(root, "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only",
                          "HEAD", "--", relative)
    if code != 0:
        return []
    return [line for line in (out or "").splitlines() if line.strip()]


def _deleted_paths(root, paths):
    """本次提交范围内**真正的删除**：HEAD 里有、工作树里没有。

    只按"工作树不存在"判会把从未存在过的路径（glob 展开结果、拼错的路径）也算成删除，
    于是每次归档都被要求补一条 delete 确认——那是假阻断。
    """
    if not paths:
        return []
    code, _out = scope.git(root, "rev-parse", "--verify", "HEAD")
    if code != 0:
        return []
    deleted = []
    for path in sorted(set(paths)):
        if os.path.exists(os.path.join(str(root), path)):
            continue
        code, _out = scope.git(root, "cat-file", "-e", f"HEAD:{path}")
        if code == 0:                      # HEAD 里有、工作树里没有 = 真删除
            deleted.append(path)
    return deleted


def _commit_paths(root, paths, message, moved_from=None):
    """按精确路径暂存并提交：不捎带索引中的其他内容，提交后回读核对（机制稿 §5.3）。

    **幂等判据（D3，归档失败后重入靠它）**：同一批路径第二次提交时，暂存区为空 →
    返回 `{"committed": True, "already_clean": True}` 且 **HEAD 不变**；也就是说重入
    不会重复提交。提交只用**精确路径**（授权里的 glob 先展开），所以重入也不会顺手
    带走别人的改动。

    `moved_from`：目录移动的**源路径**。移动会让旧路径变成未提交删除，只 add 新路径
    会把它留给项目（下一任务的 c 桶），所以删除必须进同一提交（第十三轮复审外部 P1）。
    """
    from . import paths as paths_mod

    authorized = []
    pending = None
    for raw in paths or []:
        token = str(raw).strip()
        if not token:
            continue
        if any(char in token for char in "*?["):
            # 授权可以写 glob，但提交按展开后的精确路径执行；无匹配即视为无效授权
            if pending is None:
                pending = scope.uncommitted_paths(root)
            matches = [item for item in pending if paths_mod.match_path(token, item)]
            authorized.extend(matches)
            continue
        try:
            authorized.append(paths_mod.normalize(token))
        except paths_mod.InvalidPath as exc:
            raise TaskError("WF_PATH_INVALID", {"reason": str(exc), "path": token})
    authorized = sorted(set(authorized))
    if not authorized:
        return {"committed": False, "reason": "no paths"}
    def git(*args):
        return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=str(root),
                              capture_output=True, text=True, check=False)

    # 目录移动的源路径：用 -A 把"旧路径删除"和新路径一起暂存，避免给项目留下无主删除
    staging = list(authorized)
    if moved_from:
        # 只并入"确切的删除文件"，不并入目录：目录级 `git add -A` 会把同目录下
        # 别的任务的未授权改动一起提交（第十五轮复审 F15-2）。
        for token in ([moved_from] if isinstance(moved_from, str) else list(moved_from)):
            for path in _deleted_paths(root, str(token or "").strip()):
                try:
                    staging.append(paths_mod.normalize(path))
                except paths_mod.InvalidPath as exc:
                    # 无法表示就整批拒绝：静默跳过会让"旧文件仍在 HEAD"却报成功（第二十三轮复审 N23-2）
                    raise TaskError("WF_PATH_INVALID", {
                        "reason": "移动源里的删除路径无法规范化，拒绝提交以免遗留旧文件",
                        "path": path, "detail": str(exc),
                        "exits": ["手工清理该路径后用同一命令重入",
                                  "如属历史遗留，走 repair 处置"],
                    })
        staging = sorted(set(staging))
    # 分类：已暂存的删除（索引里就是 D，工作树没有文件）不能再 add；未跟踪但已消失的路径也不能 add。
    def _staged_deleted(path):
        status = git("status", "--porcelain", "--", path)
        line = (status.stdout or "").strip()
        return bool(line) and line[0] == "D"

    to_add = [path for path in staging if not _staged_deleted(path)]
    add = git("add", "-A", "--", *to_add) if to_add else git("status", "--porcelain")
    if add.returncode != 0:
        # 逐路径剔除"git 认为不匹配"的项后重试一次（未跟踪且已消失的旧路径）
        keep = []
        for path in to_add:
            status = git("status", "--porcelain", "--", path)
            if status.returncode == 0 and status.stdout.strip():
                keep.append(path)
        if keep != to_add and keep:
            add = git("add", "-A", "--", *keep)
            to_add = keep
        if add.returncode != 0:
            raise TaskError("WF_PERSISTENCE_FAILED", {"command": "git add", "stderr": add.stderr[-500:]})
    staged = git("status", "--porcelain", "--", *staging)
    if staged.returncode == 0 and not staged.stdout.strip():
        return {"committed": True, "already_clean": True, "paths": staging, "head": scope.head(root)}
    commit = git("commit", "-m", message, "--", *staging)
    if commit.returncode != 0:
        raise TaskError("WF_PERSISTENCE_FAILED", {"command": "git commit", "stderr": commit.stderr[-500:],
                                                  "stdout": commit.stdout[-500:]})
    shown = git("show", "--name-only", "-z", "--format=", "HEAD")
    committed = [item for item in (shown.stdout or "").split("\0") if item.strip()]
    extra = [path for path in committed
             if not any(path == item or path.startswith(item + "/") or paths_mod.match_path(item, path)
                        for item in staging)]
    if extra:
        raise TaskError("WF_COMMIT_NOT_AUTHORIZED",
                        {"reason": "提交包含授权路径之外的内容", "extra": extra, "authorized": authorized})
    return {"committed": True, "paths": committed, "head": scope.head(root)}






def _prerequisite_graph(root):
    """活动任务的 `{task_id: [prereq]}`（环检测只看活动记录；归档成员按 §6.1 只作就绪判定）。"""
    graph = {}
    for _path, task in iter_tasks(root):
        if task.get("status") == "archived" or task.get("terminal"):
            continue
        task_id = task.get("id")
        if task_id:
            graph[task_id] = [item for item in task.get("prerequisites") or [] if item]
    return graph


def _find_cycle(graph, start):
    """从 `start` 出发的 DFS 三色；返回参与环的 id 序列，无环返回 None。"""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {}
    stack = []

    def walk(node):
        colour[node] = GREY
        stack.append(node)
        for child in graph.get(node) or []:
            state = colour.get(child, WHITE)
            if state == GREY:
                index = stack.index(child)
                return stack[index:] + [child]
            if state == WHITE:
                found = walk(child)
                if found:
                    return found
        stack.pop()
        colour[node] = BLACK
        return None

    return walk(start)


def cmd_dep(ctx, args):
    """`dep add|rm --task <id> --prereq <id>`（机制稿 §6.1：唯一 prerequisites 集合）。

    只做四件事：两端存在性、自环/环（DFS 三色）、活动区约束、写回 `prerequisites`。
    建边/删边都是 `dependency.change` 状态动作，targets 同时覆盖两端——
    跨任务目标碰撞因此走既有判定，而不是各入口另写一份。
    """
    from . import lock

    task_id = args.value("--task")
    prereq = args.value("--prereq")
    sub = args.value("--op") or (args.positional() or [None])[0]
    if sub not in ("add", "rm") or not task_id or not prereq:
        raise TaskError("WF_PATH_INVALID",
                        {"reason": "dep requires add|rm --task <id> --prereq <id>",
                         "got": {"op": sub, "task": task_id, "prereq": prereq}})
    if task_id == prereq:
        raise TaskError("WF_DEPENDENCY_UNMET", {"reason": "self edge", "task": task_id})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint=f"dep {sub}"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        if not path:
            raise TaskError("WF_TARGET_MISSING", {"reason": "task record missing", "task": task_id})
        task = records.load_json(os.path.join(path, "task.json"))
        if not isinstance(task, dict):
            raise TaskError("WF_RECORD_INVALID", {"task": task_id})
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "archived object does not accept dependency writes",
                             "task": task_id})
        current = [item for item in task.get("prerequisites") or [] if item]
        if sub == "add":
            other = load_task(ctx.root, prereq)
            if other is None:
                raise TaskError("WF_TARGET_MISSING",
                                {"reason": "prerequisite task not found", "prereq": prereq},
                                next_="核对 id 与目录后重试；不猜 id、不自动建对象")
            if other.get("status") == "archived" or other.get("terminal"):
                # §6.1：独立建边要求两端都在活动区且前置未归档；已归档历史前置只可由定义引用
                raise TaskError("WF_DEPENDENCY_UNMET",
                                {"reason": "prerequisite already archived", "prereq": prereq,
                                 "terminal": other.get("terminal")})
            if prereq in current:
                return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                                    position_=codes.position(scope="task", phase=task.get("phase"),
                                                             task_id=task_id),
                                    next_="边已存在（幂等，不重复写入）",
                                    facts={"edge": {"task": task_id, "prereq": prereq},
                                           "prerequisites": current})
            candidate = current + [prereq]
            graph = _prerequisite_graph(ctx.root)
            graph[task_id] = candidate
            cycle = _find_cycle(graph, task_id)
            if cycle:
                raise TaskError("WF_DEPENDENCY_UNMET",
                                {"reason": "candidate graph has a cycle", "cycle": cycle,
                                 "exits": ["换一个前置", "先删掉环上的边", "由人确认返工/重连"]})
            task["prerequisites"] = candidate
        else:
            if prereq not in current:
                return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                                    position_=codes.position(scope="task", phase=task.get("phase"),
                                                             task_id=task_id),
                                    next_="边不存在（幂等）",
                                    facts={"edge": {"task": task_id, "prereq": prereq},
                                           "prerequisites": current})
            # 删边只改未归档持有侧；目标可在归档区（死引用由 repair 处置，不在这里追认）
            task["prerequisites"] = [item for item in current if item != prereq]
        inputs = {"task": task_id, "prereq": prereq, "operation": sub}
        targets = [{"kind": "task", "id": task_id}, {"kind": "task", "id": prereq}]
        task, action = _start_task_action(
            ctx, path, task, "dependency.change", holder, inputs,
            ["validate_graph", "write_prerequisites"], targets=targets,
        )
        task, assertion = _finish_task_action(
            ctx, path, task, "dependency.change", holder, inputs, action,
            evidence_refs=[f"dep:{task_id}:{prereq}"],
        )
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="前置变化只挡收尾；首次开工/恢复/重入 Execute 仍各自核前置",
        facts={"edge": {"task": task_id, "prereq": prereq},
               "prerequisites": task.get("prerequisites") or [],
               "control_assertion": assertion},
    )


def dependency_blockers(root, task):
    """前置任务必须正常归档且归档持久化可核（机制稿 §6.1、§9.3 门禁 6）。"""
    blockers = []
    for prereq in task.get("prerequisites") or []:
        other = load_task(root, prereq)
        if other is None:
            blockers.append({"task": prereq, "reason": "missing"})
            continue
        if other.get("terminal") != "normal":
            blockers.append({"task": prereq, "reason": f"terminal={other.get('terminal')}"})
            continue
        persisted = archive_persisted(root, other)
        if not persisted.get("persisted"):
            blockers.append({"task": prereq, "reason": persisted.get("reason") or "archive not persisted"})
    return blockers


def archive_persisted(root, task, lower_override=None):
    """可达提交查证：核归档记录是否进入历史（机制稿 §5.3）。

    下界取归档动作的 `head_before`；恢复分支在动作尚未推进到 `task.archive` 时，用刚做的
    记录组提交作**下界替代**（提交内容事实），避免"提交已成功却报 no archive action"的假阴性。
    """
    action = task.get("action") or {}
    if action.get("kind") == "task.archive":
        lower = action.get("head_before")
        lower_source = "action.head_before"
    else:
        lower = lower_override
        lower_source = "record_commit"
    directory = task_dir(root, task.get("id"))
    if not directory:
        return {"persisted": False, "reason": "task directory not found"}
    record_rel = os.path.relpath(directory, str(root)).replace(os.sep, "/")
    if not record_rel.startswith(".wf/tasks/archive/"):
        return {"persisted": False, "reason": "record is not under the archive root", "record": record_rel}
    if not lower:
        reason = ("no archive action" if action.get("kind") != "task.archive"
                  else "no head_before (lower bound unknown)")
        return {"persisted": False, "reason": reason, "record": record_rel}
    if not scope.is_ancestor(root, lower):
        return {"persisted": False, "reason": "lower bound unreachable", "record": record_rel}
    lower_bound_source = lower_source
    record_file = f"{record_rel}/task.json"
    for sha in scope.commits_since(root, lower) or []:
        changed = scope.commit_paths(root, sha) or []
        if record_file not in changed:
            continue
        blob = _committed_text(root, sha, record_file)
        if blob is None:
            continue
        try:
            committed = json.loads(blob)
        except ValueError:
            continue
        if not isinstance(committed, dict):
            continue
        if committed.get("id") != task.get("id") or committed.get("terminal") != "normal":
            continue
        return {"persisted": True, "commit": sha, "record": record_file,
                "lower_bound": lower, "lower_bound_source": lower_bound_source}
    return {"persisted": False,
            "reason": "no reachable commit contains the archived task record with a normal terminal",
            "record": record_file}


def _parent_of(root, commit):
    """提交的父提交；无父（首个提交）返回 None，由 archive_persisted 走全量可达查证。"""
    if not commit:
        return None
    code, out = scope.git(root, "rev-list", "--parents", "-n", "1", commit)
    if code != 0:
        return None
    parts = out.split()
    return parts[1] if len(parts) > 1 else None


def _record_committed(root, record_rel):
    """记录目录已进入提交且无未提交差异。"""
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", f"{record_rel}/task.json"],
                             cwd=str(root), capture_output=True, text=True, check=False)
    if tracked.returncode != 0:
        return False
    status = subprocess.run(["git", "status", "--porcelain", "--", record_rel],
                            cwd=str(root), capture_output=True, text=True, check=False).stdout.strip()
    return status == ""


def _committed_text(root, sha, path):
    """读取某次提交中指定路径的内容；不存在或读取失败返回 None。"""
    proc = subprocess.run(["git", "-c", "core.quotePath=false", "show", f"{sha}:{path}"],
                          cwd=str(root), capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else None


def review_acceptance_echo(task):
    """当前生效的放行清单（归档回显）：机制自身的读取点，不复制 `review` 的判据。"""
    from . import review as review_mod

    return review_mod.acceptance_echo(task)


def _release_after_archive(ctx, task_id, holder=None):
    """正常归档持久化成功后释放写权：对象已终态，释放没有业务语义选择。

    释放失败不把归档报成失败：返回事实并给 `writer release` 恢复出口。
    """
    from . import cli

    try:
        record = ctx.writer()
        if record.get("state") == "idle":
            return {"released": True, "already": True}
        if holder is None:
            _record, holder = ctx.require_held(task=task_id)
        updated, assertion = cli._release_writer_locked(ctx, holder)
        return {"released": True, "generation": updated.get("generation"),
                "control_assertion": assertion}
    except Exception as exc:  # noqa: BLE001 — 归档已持久化，释放失败只报告，不反转结果
        return {"released": False, "code": getattr(exc, "code", type(exc).__name__),
                "facts": getattr(exc, "facts", {}),
                "next": "按 status 核对写权后重跑 `wf writer release`"}


def _archive_draft(ctx, task_id):
    """archive --draft 的草稿生成（2026-11-21）：只读、不要求写权与绑定。

    条目为 archive 决定域形状（archive_finish + commit_grant 骨架），每条含
    DECISION_FIELDS 六键占位；只有 commit 条目预填 subject 路径（finish 条目
    的 subject/quote 留占位——框架不替人写"已了解结果与未核实项"）。
    """
    from . import cli

    task = load_task(ctx.root, task_id)
    if task is None:
        raise TaskError("WF_RECORD_INVALID", {"missing_task": task_id})
    pending = pending_delivery_paths(ctx, task) or []
    granted = [str(item) for item in (commit_grant_paths(task) or [])]

    def _entry(choice, subject):
        # 六键占位从 DECISION_FIELDS 生成，不手抄（唯一事实源）。
        # 十轮审查 P2-3：占位统一带 TODO 前缀——_load_decision 拒绝任何 TODO 占位值，
        # "照抄草稿"在六个字段上同等被拒（不出现"半可过"）。
        return {
            "source": "TODO human:<来源>（人复核草稿后填）",
            "at": records.now_str(),
            "subject": subject,
            "object_digest": "",
            "choice": choice,
            "reason": "TODO（人填写：为什么这样处置）",
        }

    entries = [
        _entry("finish", "TODO（人写：已了解结果与未核实项）"),
    ]
    for path in sorted(set(pending) - set(granted)):
        entries.append(_entry("commit", [path]))
    for path in sorted(set(granted) & set(pending)):
        entries.append(_entry("commit", [path]))
    from . import sampling as sampling_mod

    # 十六轮后 d-1（盲审）：「不同问题」裁定不产生触发事实（复盘只在「同一问题」方向
    # 转正），finish 人签前必须有它的可见投影——否则误裁方向无人可见。数据源是
    # debug_pending 的 rulings_raw（与门禁同一重建口径，不落第二份账本）。
    from . import gates as gates_mod

    _debug_rulings = (gates_mod.debug_pending(task, ctx.debug_threshold()).get("rulings_raw") or {})
    ruled_different = [{"subject": subject, "choice": choice}
                       for subject, choice in sorted(_debug_rulings.items())
                       if choice == "不同问题"]
    return {
        "title": task.get("title"),
        "entries": entries,
        "pilot_sampling_pending": not sampling_mod.selection(task)["picks"],
        "debug_ruled_different": ruled_different,
    }


def cmd_archive(ctx, args):
    persisted = None      # 首归档路径没有续做分支，必须先初始化（否则引用未定义变量）
    from . import cli, gates, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "archive requires --task <id> --decision <path>"})
    if args.flag("--draft"):
        # 草稿模式（2026-11-21）：只读、免决定；在 _load_decision/action 启动/取锁之前返回，
        # 不要求写权与绑定。由 pending_delivery_paths/commit_grant_paths 生成决定文件草稿
        # （archive_finish + commit_grant 骨架，每条含 DECISION_FIELDS 六键占位；
        # 只有 commit 条目预填 subject 路径；finish 条目 subject/quote 留占位——
        # 框架不替人写"已了解结果与未核实项"）。人把草稿写成决定文件即授权。
        if decision_path:
            raise TaskError("WF_PATH_INVALID", {"reason": "--draft 与 --decision 互斥：草稿模式不消费决定文件"})
        draft = _archive_draft(ctx, task_id)
        from . import scope as _scope_mod

        _draft_task = load_task(ctx.root, task_id) or {"id": task_id}
        _classified = _scope_mod.classify_candidates(ctx.root, _draft_task)
        from . import cli as _cli_mod

        facts_payload = {"draft": draft["entries"], "pilot_sampling_pending": draft["pilot_sampling_pending"],
                         "debug_ruled_different": draft.get("debug_ruled_different") or [],
                         "note": "草稿只读；本次未写入任何记录",
                         # P1-1（九轮）：草稿同样给不可逆确认投影——缺 record 的在写决定前就要看到
                         "irreversible": _cli_mod._irreversible_projection(ctx.root, _draft_task)}
        if facts_payload["debug_ruled_different"]:
            facts_payload["note"] += ("；已裁「不同问题」的重复调试倍数见 debug_ruled_different"
                                      "（该方向不产生复盘触发事实，收工前可复核）")
        missing = facts_payload["irreversible"]["missing_authorizations"]
        next_ = "草稿只打印不落盘；人确认后把内容写成决定文件，再以 --decision 正式归档"
        if missing:
            next_ += "；注意：" + "；".join(item["action"] + " 缺确认（" +
                    ",".join(item["paths"][:5]) + "）——" + item["exits"][0] for item in missing)
        return codes.result(
            "WF_OK",
            object={"id": task_id, "name": draft["title"]},
            position_=codes.position(scope="task", task_id=task_id),
            next_=next_,
            facts=facts_payload)
    if not decision_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "archive requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    finish = [item for item in decisions if decisions_mod.accepts("archive_finish", item.get("choice"))]
    grants = [item for item in decisions if decisions_mod.accepts("commit_grant", item.get("choice"))]
    if not finish:
        raise TaskError("WF_SEMANTIC_DECISION", {"reason": "finish decision required",
                                                 "choices": [item.get("choice") for item in decisions]})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="archive"):
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json")) if path else None
        if task is None:
            raise TaskError("WF_TARGET_COLLISION", {"reason": "task not found", "task": task_id})
        if task.get("status") == "archived":
            # 终态已写但目录未移动：先完成移动，再按提交事实判定
            current_dir = task_dir(ctx.root, task_id)
            rel_now = os.path.relpath(current_dir, str(ctx.root)).replace(os.sep, "/") if current_dir else ""
            old_rel = None   # 续做分支：目录可能早已移动过，源路径只在本轮移动时才存在
            write_holder = None
            if current_dir and not rel_now.startswith(".wf/tasks/archive/"):
                _record, write_holder = ctx.require_held(task=task_id)
                destination = _archive_destination(ctx.root, task)
                if os.path.exists(destination):
                    raise TaskError("WF_TARGET_COLLISION",
                                    {"destination": os.path.relpath(destination, str(ctx.root))})
                old_rel = os.path.relpath(current_dir, str(ctx.root)).replace(os.sep, "/")
                moved = _move_task(ctx.root, current_dir, destination, task)
                task = records.load_json(os.path.join(moved, "task.json"))
            persisted = archive_persisted(ctx.root, task)
            if not persisted.get("persisted"):
                # R23：有既有提交授权时续做记录组提交（幂等）
                record_dir = task_dir(ctx.root, task_id)
                record_rel = (os.path.relpath(record_dir, str(ctx.root)).replace(os.sep, "/")
                              if record_dir else None)
                # 归档已由人授权（finish 决定在记录里）时，记录组提交是框架固定职责，可续做；
                # 但历史授权不能替代当前写权与代次（设计稿 §4.4）
                authorized = bool(task.get("finish_decision"))
                if record_rel and authorized:
                    try:
                        ctx.require_held(task=task_id)
                    except Exception as exc:  # 写权/代次不满足即停，不提交
                        return codes.result(
                            getattr(exc, "code", None) or "WF_WRITER_BUSY",
                            facts=getattr(exc, "facts", {}) or {},
                            next_="按写权现状交接或恢复后再续做归档提交",
                        )
                    # commit_grants 是 Decision 数组：把每个决定授权的路径摊平后按需提交
                    granted = []
                    for grant in task.get("commit_grants") or []:
                        if isinstance(grant, dict):
                            granted.extend(_subject_paths(grant.get("subject")))
                    granted = sorted(set(granted))
                    business = _commit_paths(ctx.root, granted, f"wf: archive {task_id} (business)")
                    commit_result = _commit_paths(ctx.root, [record_rel],
                                                  f"wf: archive {task_id}\n\nwf-task: {task_id}",
                                                  moved_from=(_moved_from(ctx.root, old_rel)
                                                  or task.get("moved_from")))
                    # 记录组提交本身即下界：不再依赖 action.kind，避免"已提交却报失败"
                    bound = _parent_of(ctx.root, commit_result.get("head"))
                    persisted = archive_persisted(ctx.root, task, lower_override=bound)
                    persisted["resumed_commit"] = True
                    persisted["business_commit"] = business
                    task = records.load_json(os.path.join(task_dir(ctx.root, task_id), "task.json")) \
                        if task_dir(ctx.root, task_id) else task
            code = "WF_OK" if persisted.get("persisted") else "WF_PERSISTENCE_FAILED"
            write_release = (_release_after_archive(ctx, task_id, holder=write_holder)
                             if persisted.get("persisted") else {"released": False,
                                                                 "reason": "归档尚未持久化"})
            return codes.result(
                code,
                object={"id": task_id, "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                         action_id=(task.get("action") or {}).get("id"),
                                         action_state=(task.get("action") or {}).get("state")),
                next_=("归档已持久化，写权已释放；下一对象需在新会话选择"
                       if persisted.get("persisted") and write_release.get("released")
                       else "归档已持久化：无需重复归档或重复提交" if persisted.get("persisted")
                       else "按可达提交查证结果交人核对（不重复归档）"),
                facts={"archive_persisted": persisted, "terminal": task.get("terminal"),
                       "write_release": write_release,
                       # vendor_dirty 消费点（2026-11-21 批C）：归档收尾同样可见，人确认归属后不阻断
                       "vendor_dirty": (scope.classify_candidates(ctx.root, task, receipts=task_receipts(ctx.root))
                                        .get("buckets", {}).get("v", [])),
                       # W2-7：vendor 归属确认记录（kind=框架改动）随终态可见，纯事实投影
                       "vendor_judgments": [entry for entry in (task.get("judgments") or [])
                                            if isinstance(entry, dict) and entry.get("kind") == "框架改动"],
                       # ⑥：归档强制回显当前生效的放行清单（人裁接受的风险必须跟着终态可见）
                       "unknown_acceptances": review_acceptance_echo(task)},
            )
        _record, holder = ctx.require_held(task=task_id)
        if task.get("status") != "in_progress" or task.get("phase") != "finish":
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "normal archive requires finish phase",
                                                     "status": task.get("status"), "phase": task.get("phase")})
        task["commit_grants"] = grants
        task["finish_decision"] = finish[0]
        destination = _archive_destination(ctx.root, task)
        if os.path.exists(destination):
            raise TaskError("WF_TARGET_COLLISION", {"destination": os.path.relpath(destination, str(ctx.root))})
        from . import check as check_mod

        unresolved = check_mod.resolve_verifications(ctx, task, "finish")
        if unresolved:
            raise TaskError("WF_VERIFICATION_UNREADY",
                            {"consume_at": "finish", "unresolved": unresolved,
                             "next": "补真实来源/设施后回到 Check 或重新归档"})
        inputs = {"task": task_id, "archive": os.path.relpath(destination, str(ctx.root)).replace(os.sep, "/")}
        pending_action = actions.pending(task)
        if pending_action and pending_action.get("kind") == "task.archive":
            action = pending_action
            action["state"] = "applying"
            task["action"] = action
            save_task(ctx.root, path, task)
        else:
            task, action = _start_task_action(ctx, path, task, "task.archive", holder, inputs,
                                              ["preflight", "commit_business", "final_gate", "write_terminal",
                                               "move", "persist", "verify"])
        grant_paths = [path for grant in grants for path in _subject_paths(grant.get("subject"))]
        # K5：含 vendor 的提交一律拒绝（框架自有资产不进业务提交）
        vendor_hits = scope.vendor_assets(ctx.root, task, grant_paths)
        if vendor_hits:
            action = actions.fail(dict(task["action"]), "vendor in commit grant")
            task["action"] = action
            save_task(ctx.root, path, task)
            raise TaskError("WF_SCOPE_VIOLATION",
                            {"reason": "提交范围包含框架自有资产（vendor）",
                             "vendor_paths": vendor_hits,
                             "exits": ["从 --subject 里去掉 .wf/** 后重试",
                                       "框架改动单独作为维护变更（install/upgrade/repair）处理"]})
        # K6 第 5 类：仓库级规则文件要有该类动作的确认（脱敏原件入库后才算数）
        from . import authorize as authorize_mod

        rule_hits = authorize_mod.repo_rule_paths(ctx, grant_paths)
        if rule_hits:
            # 与 `delete` 同口径：确认必须**覆盖这些路径**，只核"有过该类确认"会让旧确认
            # 复用到另一组规则文件（dogfood：授权类别存在即放行）。
            covered, uncovered = authorize_mod.covers(path, "repo_rules", rule_hits, root=ctx.root)
            if not covered:
                action = actions.fail(dict(task["action"]), "repo-level rule files without authorization")
                task["action"] = action
                save_task(ctx.root, path, task)
                raise TaskError("WF_REPO_RULES_NOT_AUTHORIZED",
                                {"missing_action": "repo_rules",
                                 "repo_rule_paths": rule_hits,
                                 "uncovered": uncovered,
                                 "reason": "提交范围含环境级规则文件（K6 第 5 类：环境级规则变更确认），但确认未覆盖这些路径",
                                 "exits": ["把人的确认写成文件（choice=repo_rules + paths 覆盖上面未覆盖的路径 + quote/by/source），经 `wf authorize record --task <id> --file <文件>` 登记后重入——门禁消费的是 authorization-repo_rules.json，写进 archive 决定文件不会生效",
                                           "把这些路径移出本次提交范围"]})
        # K6 第 2 类：本次提交范围里的**删除**要有一次确认（删除是不可逆动作）
        deleted_in_grant = _deleted_paths(ctx.root, grant_paths)
        if deleted_in_grant:
            covered, uncovered = authorize_mod.covers(path, "delete", deleted_in_grant, root=ctx.root)
            if not covered:
                action = actions.fail(dict(task["action"]), "delete without authorization")
                task["action"] = action
                save_task(ctx.root, path, task)
                raise TaskError("WF_DELETE_NOT_AUTHORIZED",
                                {"missing_action": "delete", "deleted_paths": uncovered,
                                 "reason": "提交范围含删除，但缺删除动作的确认（K6 第 2 类）",
                                 "exits": ["把人的确认写成文件（choice=delete + paths 覆盖这些路径 + quote/by/source），经 `wf authorize record --task <id> --file <文件>` 登记后重入——门禁消费的是 authorization-delete.json，写进 archive 决定文件不会生效",
                                           "把删除移出本次提交范围"]})
        # ⑥ D4：业务提交**之前**跑只读预检（否则"业务已提交、归档因 C3 被拒"无法避免）。
        # 消费钩子先跑：受控写点观察到"放行记录对应的报告已恢复可核实"即让该放行失效。
        from . import review as review_mod

        if review_mod.consume_recovered(ctx, task):
            save_task(ctx.root, path, task)
        precheck = archive_precheck(ctx, task)
        if not precheck["ok"]:
            action = actions.fail(dict(task["action"]), f"archive precheck: {precheck['code']}")
            task["action"] = action
            save_task(ctx.root, path, task)
            raise TaskError(precheck["code"], precheck["facts"])
        chain_head = _chain_trailer(task)
        business_commit = _commit_paths(ctx.root, sorted(set(grant_paths)),
                                        f"wf: complete {task_id}\n\nwf-task: {task_id}{chain_head}") if grant_paths else {
            "committed": False, "reason": "no grant paths"}
        task = records.load_json(os.path.join(path, "task.json"))
        task["commit_grants"] = grants
        task["finish_decision"] = finish[0]
        ok, code, facts = gates.final_gate(ctx, task, ignore_action_id=(task.get("action") or {}).get("id"))
        if not ok:
            action = actions.fail(dict(task["action"]), f"final gate: {code}")
            task["action"] = action
            save_task(ctx.root, path, task)
            raise TaskError(code, facts)
        task = records.load_json(os.path.join(path, "task.json"))
        action = dict(task["action"])
        action["state"] = "persist_pending"
        task["action"] = action
        task["write_mark"] = {
            "operation": "task.archive",
            "owner": writer_mod.owner_ref(holder.get("kind"), holder.get("id"), holder.get("scope")),
            "generation": holder.get("generation"),
            "before_head": action.get("head_before"),
            "changed_fields": sorted(inputs.keys()),
            "action_id": action.get("id"),
            "invocation": {"entry": "finish", "scope_digest": action.get("inputs_digest")},
        }
        task["terminal"] = "normal"
        task["status"] = "archived"
        task["archived_at"] = records.now_str()
        task["paused"] = False
        task["suspended"] = False
        save_task(ctx.root, path, task)
        old_rel = os.path.relpath(path, str(ctx.root)).replace(os.sep, "/")
        moved = _move_task(ctx.root, path, destination, task)
        save_task(ctx.root, moved, task)
        record_rel = os.path.relpath(moved, str(ctx.root)).replace(os.sep, "/")
        # 记录段要连**旧位置的删除**一起提交（否则 `D .wf/tasks/<旧任务目录>/*` 留在工作树里），
        # 但只能提交 HEAD 里**确实存在**的旧路径：首次归档的任务目录从未入库，
        # 把它当 pathspec 会让 `git add` 直接失败（"did not match any file(s) known to git"）。
        commit_paths = [record_rel] + _tracked_under(ctx.root, old_rel)
        commit_result = _commit_paths(ctx.root, commit_paths,
                                      f"wf: archive {task_id}\n\nwf-task: {task_id}{chain_head}",
                                      moved_from=(_moved_from(ctx.root, old_rel)
                                                  or task.get("moved_from")))
        commit_result["business_commit"] = business_commit
        # 首归档路径同样要能回答"是否已持久化"：以记录组提交本身为下界做可达提交查证
        persisted = archive_persisted(ctx.root, task,
                                      lower_override=_parent_of(ctx.root, commit_result.get("head")))
        from . import paths as paths_mod

        dirty = scope.uncommitted_paths(ctx.root)
        requested = list(grant_paths) + [record_rel]

        def covered_by_request(path):
            return any(path == item or path.startswith(item + "/") or paths_mod.match_path(item, path)
                       for item in requested)

        missing = [item for item in dirty if covered_by_request(item)]
        if missing:
            raise TaskError("WF_PERSISTENCE_FAILED", {"uncommitted_after_commit": missing,
                                                      "recovery": "归档记录保持 persist_pending，按可达提交查证后重入"})
        from . import cli as cli_mod

        assertion = cli_mod._control_assertion(
            ctx, "task.archive",
            writer_mod.owner_ref(holder.get("kind"), holder.get("id"), holder.get("scope")),
            task["action"], [record_rel],
        )
        reassessment = _reassess_empty_set(ctx, task_id)
        # 归档持久化已在锁内完成；写权释放在同一把锁内做，避免与另一个会话的 acquire 竞态。
        write_release = _release_after_archive(ctx, task_id, holder=holder)
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="finish", task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_=("归档已完成，写权已释放；下一对象需在新会话选择"
               if write_release.get("released")
               else "归档已完成；写权释放未完成，按 write_release 事实重跑 `wf writer release`"),
        facts={"terminal": "normal", "archived_at": task["archived_at"], "moved_to": record_rel,
               "write_release": write_release,
               "commit": commit_result, "control_assertion": assertion, "reassessment": reassessment,
               # 归档后"是否已持久化"要能被外部核对（续做路径会带 resumed_commit）：
               # 只给 stages 不够，调用方（含独立进程重入）无法判断终态是否落库。
               "archive_persisted": dict(persisted or {"available": False},
                                          resumed_commit=bool((persisted or {}).get("resumed_commit"))),
               # K7：三段逐段回报（运行态按设计不入库，只报告它被排除）
               "stages": [
                   {"stage": "business", "paths": sorted(set(grant_paths)),
                    "result": business_commit,
                    "recovery": "业务段失败：按可达提交查证后重入；不改终态、不重复提交"},
                   {"stage": "record", "paths": [record_rel], "result": commit_result,
                    "recovery": "记录段失败：归档记录保持 persist_pending，按可达提交查证后重入"},
                   {"stage": "runtime", "paths": [],
                    "result": {"committed": False, "reason": "运行态按 S10 不入库（gitignore 托管段）"},
                    "recovery": "无需恢复：运行态可丢弃重建"},
               ],
               # 巡检到点提示（设计稿 §5.4）：归档是"正常归档累计"的计数点，到点就在回显里提示
               "inspection_hint": _inspection_hint(ctx),
               # ⑥：归档强制回显当前生效的放行清单
               "unknown_acceptances": review_acceptance_echo(task)},
    )


def _inspection_hint(ctx):
    """归档后按整数倍口径给巡检提示；不阻断、只提示（外部 7）。

    到点判定只有**一处实现**：`_governance_summary` 的 `inspection`。此前本函数硬编码
    `every = 10` 并数**全部**归档（含异常归档与不可解析记录），与机制稿 §8.5 的
    「按正常归档累计、异常归档不计也不重置、键取自项目配置 `inspection_every_tasks`」
    不一致（实现稿 §2.3.11 未做项）。这里复用同一判定，另写一份就会两处漂移。
    """
    try:
        _active, archived = _task_dirs(ctx.root)
        inspection = _governance_summary(ctx.root, list(iter_tasks(ctx.root)), archived)["inspection"]
    except OSError:
        return {"due": None, "reason": "archive scan failed"}
    facts = {"archived": inspection.get("normal_archived"),
             "abnormal": inspection.get("abnormal_archived"),
             "every": inspection.get("every_tasks")}
    if inspection.get("problem"):
        facts["problem"] = inspection.get("problem")
    if inspection.get("due") is None:
        facts["due"] = None
        facts["reason"] = "normal-archive count or inspection_every_tasks is unknown; no conclusion"
        return facts
    facts["due"] = bool(inspection.get("due"))
    if facts["due"]:
        facts["next"] = "按设计稿 §5.4 运行 inspect 完成本轮巡检"
    return facts

def _reassess_empty_set(ctx, task_id):
    """首轮无返工集合时，复评只能是"无挂起任务"。

    但若记录里残留 `suspended`（手工编辑/迁移/repair 重建都可能留下），必须先报未知事实，
    不能谎报"没有"——"读不出 ≠ 没有"（第二十一轮复审外部 P1-2）。
    """
    found = []
    for _path, task in iter_tasks(ctx.root):
        if task.get("suspended") or task.get("paused") and task.get("suspended"):
            found.append({"id": task.get("id"), "phase": task.get("phase"),
                          "suspended": bool(task.get("suspended"))})
    if found:
        raise TaskError("WF_HISTORY_UNRESOLVED", {
            "reason": "记录里存在挂起/暂停残留，首轮无法判定返工集合",
            "pending": found,
            "exits": ["由人核对并清理这些记录的 suspended 标记后重试",
                      "确认属于历史迁移残留时走 repair 处置"],
        })
    return {"suspended_tasks": [], "reassessed": [], "note": "首轮无返工能力，挂起集合为空"}


def _reenter_check_from_finish(ctx, path, task, action, operation):
    """Finish→Check 受控迁移（机制稿 §2.2「Finish 中变更 → 回 check」）。

    作为父动作内部的一步：保留旧检查结果并登记失效事实，不伪造新的 Check 成功回执。
    """
    if task.get("phase") != "finish":
        return task, False
    check = task.get("check")
    if isinstance(check, dict) and check.get("id"):
        check = dict(check)
        check["invalidated"] = {"at": records.now_str(),
                                "by": operation,
                                "action_id": (action or {}).get("id"),
                                "reason": "对象/规范变化使旧结果失效（回 check）"}
        task["check"] = check
    task["phase"] = "check"
    task["updated_at"] = records.now_str()
    save_task(ctx.root, path, task)
    return task, True


# --------------------------------------------------------------------------
# 命令：baseline-apply / spec-update
# --------------------------------------------------------------------------


def _finalize_project_config(root, content, generated=None):
    """把 project_id 在**提案内容**阶段定稿：缺则生成一次，已存在则保留。

    这样"写入后重入"能判为已完成（内容一致），也不会由入口静默重建已有标识
    （第十六/十七轮复审 N17-2、N17-3）。
    """
    try:
        payload = json.loads(content)
    except ValueError:
        return content
    if not isinstance(payload, dict):
        return content
    existing = records.load_json(join(root, ".wf/project-config.json")) or {}
    site_id = existing.get("project_id") if isinstance(existing, dict) else None
    if payload.get("project_id"):
        return content            # 提案自带标识：尊重提案
    # 身份优先级：**意图值**（记录/未结案动作）> 现场配置 > 新生成。
    # 现场被外部改成别的 id 时，不得用它替换意图值——否则同一提案会被算成"不同提案"
    # （第二十二轮复审 N22-2）；真正的差异留给前像冲突去报。
    identity = generated or site_id
    if not identity:
        identity = uuid.uuid4().hex   # 初始化随机生成（机制稿 §8.1）
    payload["project_id"] = identity
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def cmd_baseline_apply(ctx, args):
    from . import lock

    task_id = args.value("--task")
    proposal_path = args.value("--proposal")
    files_arg = args.value("--files")
    decision_path = args.value("--decision")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "baseline-apply requires --task <id>"})
    if not proposal_path:
        # 2026-11-07：提案是机械结构（哪些文件、什么内容、前像是什么），不该由人/模型手写。
        # 给出 `--files <a,b,c> --decision <人的批准文件>` 即可，由入口读工作树生成提案。
        preview_only = args.flag("--preview")
        if not files_arg or (not decision_path and not preview_only):
            raise TaskError("WF_PATH_INVALID",
                            {"reason": "baseline-apply needs --proposal <json>, or --files <a,b,c> --decision <approve.json>",
                             "hint": "wf.py help baseline-apply 看结构"},
                            next_="用 --files + --decision 让入口生成提案（推荐），或提供既有格式的 --proposal")
        approval = None
        if decision_path:
            from . import cli as cli_mod

            decisions = cli_mod._load_decision(decision_path)
            approvals = [item for item in decisions if item.get("choice") in APPROVE_CHOICES]
            if not approvals:
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "decision file has no approval entry",
                                 "choices": [item.get("choice") for item in decisions]})
            approval = approvals[0]
        wanted = [item.strip() for item in str(files_arg).split(",") if item.strip()]
        if not wanted:
            raise TaskError("WF_PATH_INVALID", {"reason": "--files is empty"})
        entries = []
        for relative in wanted:
            absolute = join(ctx.root, relative)
            if not os.path.isfile(absolute):
                raise TaskError("WF_PATH_INVALID", {"reason": "file missing in worktree", "path": relative})
            with open(absolute, "r", encoding="utf-8") as handle:
                content = handle.read()
            # 前像＝当前工作树内容（应用前的真实状态），用来发现"生成后文件又被改过"
            before = "sha256:" + records.sha256_hex(content.encode("utf-8"))
            entries.append({"path": relative, "before": before, "content": content})
        proposal = {"files": entries}
        if approval is not None:
            proposal["approval"] = {"choice": approval.get("choice"),
                                    "subject": approval.get("subject"),
                                    "at": approval.get("at"), "source": approval.get("source"),
                                    "object_digest": approval.get("object_digest")}
        # 批准必须绑定到**提案内容**：人先看 --preview 给的结构摘要并据此写下 object_digest，
        # 避免"先批准再生成内容"（机制稿 §3.4）。这里把摘要算好回显，供人确认。
        proposal_digest = records.plain_digest({"files": entries})
        if args.flag("--preview"):
            from . import codes as codes_mod

            return codes_mod.result(
                "WF_OK",
                object={"id": task_id},
                position_=codes_mod.position(scope="task", task_id=task_id),
                next_="把 proposal_digest 写进人的批准决定（object_digest）后重跑（去掉 --preview）",
                facts={"preview": True, "proposal_digest": proposal_digest,
                       "files": [{"path": item["path"], "before": item["before"],
                                  "digest": "sha256:" + records.sha256_hex(item["content"].encode("utf-8"))}
                                 for item in entries]},
            )
    else:
        proposal = records.load_json(proposal_path)
    if not isinstance(proposal, dict):
        raise TaskError("WF_PATH_INVALID", {"reason": "proposal file missing or not an object"})
    files = proposal.get("files")
    if not isinstance(files, list) or not files:
        raise TaskError("WF_SEMANTIC_DECISION", {"reason": "proposal has no files"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="baseline-apply"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        from . import gates as gates_mod
        from . import paths as paths_mod

        # 阶段、状态与批准：只在执行中的已批准任务上应用基线/配置变更（机制稿 §3.4）
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "object already ended", "status": task.get("status"),
                             "terminal": task.get("terminal")},
                            next_="对象结束后只报告结果；恢复未完成的归档动作走专用恢复分支")
        if task.get("paused") or task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "task is paused or suspended", "paused": task.get("paused"),
                             "suspended": task.get("suspended")},
                            next_="先恢复任务再应用基线变更")
        if task.get("phase") not in ("execute", "check", "finish"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "baseline apply requires an executing task", "phase": task.get("phase")})
        approved_ok, approved_code, approved_facts = gates_mod.verify_step(ctx, task, "task.plan-approved")
        if not approved_ok:
            raise TaskError(approved_code, approved_facts)
        touch_paths = approved_touch_paths(task)
        # 提案须带针对本次变更的批准引用（机制稿 §3.4）：规划获批不足以证明任意版本提案已获批
        approval = proposal.get("approval") or proposal.get("decision")
        if not isinstance(approval, dict) or not approval.get("choice") or not approval.get("subject"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "proposal requires an approval reference {choice, subject}",
                             "approval": approval},
                            next_="把人对本次基线提案的批准写入 proposal.approval 后重新提交")
        if approval.get("choice") not in APPROVE_CHOICES:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "approval reference is not an approval", "choice": approval.get("choice"),
                             "accepted": list(APPROVE_CHOICES)},
                            next_="拒绝或无关决定不能作为基线变更的批准引用")
        proposal_digest = records.plain_digest({"files": files})
        if approval.get("object_digest") != proposal_digest:
            # 批准必须绑定到本次提案内容，不能用无关旧提案的批准（机制稿 §3.4）
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval does not cover this proposal",
                             "expected_digest": proposal_digest,
                             "decision_digest": approval.get("object_digest")},
                            next_="针对本次提案内容重新请人批准")


        # 整批预校验：任一非法条目都不产生写入
        planned = []
        generated = None
        for entry in files:
            if not isinstance(entry, dict):
                raise TaskError("WF_SEMANTIC_DECISION", {"reason": "file entry must be an object"})
            target = entry.get("path")
            content = entry.get("content")
            if not target or not isinstance(content, str):
                raise TaskError("WF_SEMANTIC_DECISION", {"reason": "file entry requires path and content",
                                                         "path": target})
            if "before" not in entry:
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "proposal entry requires before fingerprint (null = must not exist)",
                                 "path": target},
                                next_="补上旧指纹后重新请人批准")
            declared_before = entry["before"]
            if not isinstance(declared_before, (str, dict, type(None))):
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "before fingerprint must be a digest, fingerprint object or null",
                                 "path": target})
            if isinstance(declared_before, dict):
                # 空对象等于没有前像约束：必须给出摘要或显式「不存在」
                if not declared_before.get("digest") and declared_before.get("exists") is not False:
                    raise TaskError("WF_SEMANTIC_DECISION",
                                    {"reason": "before fingerprint needs digest or exists=false",
                                     "path": target, "before": declared_before})
            try:
                normalized = paths_mod.normalize(target)
            except paths_mod.InvalidPath as exc:
                raise TaskError("WF_PATH_INVALID", {"reason": str(exc), "path": target})
            # 目标类别：只允许基线文件、项目配置与 spec 骨架；控制记录一律拒绝
            if not paths_mod.write_target_allowed(normalized):
                raise TaskError("WF_SCOPE_UNRESOLVED",
                                {"reason": "baseline apply target class not allowed", "path": normalized,
                                 "allowed": paths_mod.write_target_allowed_list()})
            if not any(paths_mod.match_path(pattern, normalized) for pattern in touch_paths):
                raise TaskError("WF_SCOPE_UNRESOLVED",
                                {"reason": "target not covered by approved touch_paths", "path": normalized,
                                 "touch_paths": touch_paths})
            # 与 spec 写入共用同一套边界判定（项目包含性 + 字面/真实祖先的嵌套仓库）
            violation = paths_mod.boundary_violation(ctx.root, normalized)
            if violation:
                raise TaskError("WF_PATH_INVALID", {"reason": violation, "path": normalized})
            if normalized == ".wf/project-config.json":
                existing_cfg = records.load_json(join(ctx.root, ".wf/project-config.json")) or {}
                # ① 先解析**本任务**可恢复身份（memo → 未结案动作 → 现场）：
                #    解析必须在跨任务历史检查之前，否则"只有 pending 身份"的任务会
                #    被自己的历史挡住（第二十五轮复审 N25-1）。
                generated = task.get("project_config_project_id")
                if not generated:
                    _pending = actions.pending(task) or {}
                    generated = (_pending.get("inputs") or {}).get("project_id")
                if not generated and (existing_cfg or {}).get("project_id"):
                    generated = existing_cfg.get("project_id")
                # ② 本任务没有可恢复身份，且现场也缺失时才查历史痕迹：命中即要求 repair
                if not generated and not (existing_cfg or {}).get("project_id"):
                    traces = []
                    for _p, item in iter_tasks(ctx.root):
                        if item.get("id") == task_id:
                            continue
                        if item.get("project_config_project_id"):
                            traces.append(item.get("id"))
                            continue
                        _pending_other = actions.pending(item) or {}
                        if (_pending_other.get("inputs") or {}).get("project_id"):
                            traces.append(item.get("id"))
                    if traces:
                        raise TaskError("WF_HISTORY_UNRESOLVED", {
                            "reason": "项目曾有身份记录但现场与本任务都没有：重建须走 repair，入口不静默生成",
                            "traces": traces[:5],
                            "exits": ["从 Git 恢复 .wf/project-config.json（旧值仍在历史里时）后重试",
                                      "等 repair 重建能力交付（第三轮，见机制稿 D09）；在此之前不得静默生成新 id"],
                        })
                # 提案自带 id：也纳入身份（与 memo 同值），避免"现场 A / memo B"分叉
                try:
                    _proposed = json.loads(content)
                except ValueError:
                    _proposed = None
                if isinstance(_proposed, dict) and _proposed.get("project_id"):
                    if generated and generated != _proposed["project_id"]:
                        raise TaskError("WF_SEMANTIC_DECISION", {
                            "reason": "提案标识与已生成身份不一致",
                            "proposed": _proposed["project_id"], "known": generated,
                            "exits": ["用与既有身份一致的标识重出提案",
                                      "需要重建身份时走 repair（不由入口静默改）"],
                        })
                    generated = _proposed["project_id"]
                if not (existing_cfg or {}).get("project_id") and not generated:
                    # 只算不写：整批校验通过、动作登记之后才持久化（N20-1）
                    generated = uuid.uuid4().hex
                content = _finalize_project_config(ctx.root, content, generated)
            planned.append((normalized, content))
        # 1) 先在内存里算好计划与生成值（不写任何记录、不登记意图）
        inputs = {"task": task_id, "files": [item[0] for item in planned],
                  "content_digests": [records.plain_digest(item[1]) for item in planned]}
        if generated:
            inputs["project_id"] = generated
        pending = actions.pending(task)
        if pending is not None and pending.get("kind") != "baseline.apply":
            raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state"),
                                                     "kind": pending.get("kind")},
                            next_="先按原动作意图恢复，再发起基线应用")
        # 2) 与未结案意图比对：不同提案不得覆盖（这条要早于前像冲突，语义更具体）
        if pending is not None:
            if pending.get("inputs_digest") != actions.inputs_digest(inputs):
                raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"),
                                                         "reason": "proposal differs from the pending action"},
                                next_="用同一提案重入以续做，或先核对未完成动作")
        # 3) 整批前像预检：任何冲突都在登记意图之前判定（N20-1/N21-1）
        before_of = {}
        for entry in files:
            if isinstance(entry, dict) and entry.get("path"):
                before_of[entry["path"]] = entry.get("before")
        classification = []
        conflicts = []
        for normalized, content in planned:
            current = fingerprint.item(ctx.root, normalized)
            target_digest = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            before = before_of.get(normalized)
            already_applied = bool(current.get("exists")) and current.get("digest") == target_digest \
                and current.get("kind") == "file"
            if already_applied:
                classification.append(("skipped", normalized, content, current, before))
            elif _fp_matches(before, current):
                classification.append(("write", normalized, content, current, before))
            else:
                conflicts.append({"path": normalized, "declared_before": before, "current": current})
        if conflicts:
            raise TaskError("WF_WORKSPACE_UNRESOLVED",
                            {"reason": "proposal before-state does not match current files",
                             "conflicts": conflicts},
                            next_="按当前内容重新生成提案后再次请人批准")
        # 4) 校验通过后才登记/续做动作；生成值随意图同次持久化
        if pending is not None:
            action = pending
            task["action"] = action
            if not task.get("project_config_project_id"):
                carried = (pending.get("inputs") or {}).get("project_id")
                if carried:
                    task["project_config_project_id"] = carried
            save_task(ctx.root, path, task)
        else:
            if generated:
                # 记录字段与动作输入同时落：重入先取记录、再取意图（N21-1/N22-1）
                task["project_config_project_id"] = generated
            task, action = _start_task_action(ctx, path, task, "baseline.apply", holder, inputs,
                                              ["verify_proposal", "apply", "verify_result"])
        written = []
        skipped = []
        for kind, normalized, content, current, before in classification:
            if kind == "skipped":
                skipped.append(normalized)
                continue
            try:
                records.atomic_write(join(ctx.root, normalized), content)
            except OSError as exc:
                raise TaskError("WF_PERSISTENCE_FAILED",
                                {"reason": f"写入失败：{exc}", "path": normalized, "written": written},
                                next_="修正可写性后用同一提案重入以续做（已完成路径不重复写入）")
            written.append(normalized)
        task, _moved = _reenter_check_from_finish(ctx, path, task, action, "baseline.apply")
        task, assertion = _finish_task_action(ctx, path, task, "baseline.apply", holder, inputs, action,
                                              evidence_refs=written)
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_=("已回 check（Finish 期变更使旧检查失效，旧结果保留并登记 invalidation）；重新 Check"
                               if _moved else "重新 Check（基线与配置变化会使旧检查失效）"),
                        facts={"written": written, "skipped": skipped, "control_assertion": assertion,
                               "phase": task.get("phase"), "reentered_check": _moved})


def cmd_spec_update(ctx, args):
    from . import lock, spec as spec_mod

    task_id = args.value("--task")
    if args.flag("--changes-draft"):
        if not task_id:
            raise TaskError("WF_USAGE_INVALID", {"reason": "--changes-draft requires --task <id>"})
        path = task_dir(ctx.root, task_id)
        if not path:
            raise TaskError("WF_RECORD_INVALID", {"reason": "task record is missing", "task": task_id})
        task_record = records.load_json(os.path.join(path, "task.json")) or {}
        skeleton = [{"operation": "TODO（add|update|merge|rename|delete|disable）",
                     "new_paths": [], "old_paths": [],
                     "content": "TODO（add/update 的完整正文，含 frontmatter）"}]
        return codes.result(
            "WF_OK",
            object={"id": task_id, "name": task_record.get("title")},
            position_=codes.position(scope="task", phase=task_record.get("phase"), task_id=task_id),
            next_="填好 changes 数组写到 facts.path；after_digests/reference_dispositions 由入口补算，before_digests 可选（提供则按前像核），去掉 --changes-draft 后重跑 spec-update",
            facts={"draft": skeleton, "path": os.path.join(path, "spec-changes.json")},
        )
    changes_path = args.value("--changes")
    if not task_id or not changes_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "spec-update requires --task <id> --changes <path>"})
    changes = records.load_json(changes_path)
    if not isinstance(changes, list):
        raise TaskError("WF_PATH_INVALID", {"reason": "changes file must be a JSON array"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="spec-update"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        # R17：与基线入口同口径的动作授权（阶段 + 批准 + 未暂停/挂起）
        from . import gates as gates_mod

        if task.get("phase") not in ("execute", "check", "finish"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "spec update requires an executing task", "phase": task.get("phase"),
                             "allowed": ["execute", "check", "finish"]})
        if task.get("paused") or task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "spec update requires a non-paused task",
                             "paused": bool(task.get("paused")), "suspended": bool(task.get("suspended"))})
        approved_ok, approved_code, approved_facts = gates_mod.verify_step(ctx, task, "task.plan-approved")
        if not approved_ok:
            raise TaskError(approved_code, approved_facts)
        from . import paths as paths_mod

        touch_paths = approved_touch_paths(task)
        for change in changes:
            # 路径清单统一走 paths.path_list：字符串形态在这里也不能炸（此前这处裸拼接抛 internal error）
            declared = []
            for key in ("old_paths", "new_paths"):
                try:
                    declared.extend(paths_mod.path_list(change, key))
                except paths_mod.InvalidPath as exc:
                    raise TaskError("WF_PATH_INVALID", {"reason": str(exc), "key": key,
                                                        "change": change.get("operation")})
            for raw in declared:
                try:
                    normalized = paths_mod.normalize(raw)
                except paths_mod.InvalidPath as exc:
                    raise TaskError("WF_PATH_INVALID", {"path": raw, "reason": str(exc)})
                if not any(paths_mod.match_path(pattern, normalized) for pattern in touch_paths):
                    raise TaskError("WF_SCOPE_UNRESOLVED",
                                    {"reason": "spec target not covered by approved touch_paths",
                                     "path": normalized, "touch_paths": touch_paths})
        inputs = {"task": task_id, "changes": len(changes),
                  "digests": [records.plain_digest(item) for item in changes]}
        pending = actions.pending(task)
        resume = False
        if pending is not None and pending.get("kind") != "spec.update":
            raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state"),
                                                     "kind": pending.get("kind")},
                            next_="先按原动作意图恢复，再发起 spec 变更")
        if pending is not None:
            if pending.get("inputs_digest") != actions.inputs_digest(inputs):
                raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"),
                                                         "reason": "changes differ from the pending action"},
                                next_="用同一变更集重入以续做")
            resume = True
        # 语义先行：校验不过不留动作、零写入；续做时按已落盘事实识别已完成步骤
        spec_mod.validate_changes(ctx.root, changes, resume=resume, current_task_id=task_id)
        if resume:
            action = pending
            task["action"] = action
            save_task(ctx.root, path, task)
        else:
            task, action = _start_task_action(ctx, path, task, "spec.update", holder, inputs,
                                              ["apply_changes", "sync_index"])
        applied = spec_mod.apply_changes(ctx.root, changes, task, resume=resume, current_task_id=task_id)
        # 变更动作可能同步了其他任务的策展引用；重读本任务记录，避免用旧副本覆盖关联写入
        task = records.load_json(os.path.join(path, "task.json"))
        # knowledge 是人判字段，写者只应是 task-knowledge；变更事实由动作证据承载
        # （沿用 execution.actions 的既有载体，不新增未登记字段）
        task, _moved = _reenter_check_from_finish(ctx, path, task, action, "spec.update")
        task, assertion = _finish_task_action(ctx, path, task, "spec.update", holder, inputs, action,
                                              evidence_refs=[item.get("new_paths") for item in applied][:8])
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                        next_=("已回 check（Finish 期变更使旧检查失效，旧结果保留并登记 invalidation）；重新 Check"
                               if _moved else "知识变更已入记录；重新 Check 后方可 Finish"),
                        facts={"applied": applied, "control_assertion": assertion,
                               "phase": task.get("phase"), "reentered_check": _moved})


# --------------------------------------------------------------------------
# 收工、释放与巡检
# --------------------------------------------------------------------------


def bind_task_for_write(ctx, task_id):
    """任务的写入口绑定核验：普通任务绑任务本身；**实例内的任务**绑实例且 `cursor.task_id` 指向它。

    机制稿 §6.1：在途实例的任务只可由绑定该实例且游标正确的会话推进，不得直接以 task 绑定选取。
    返回 `("task"|"run", run_or_None, holder)`，供决策类入口（返工/复评）共用。
    """
    from . import session as session_mod

    key = ctx.key()
    binding = session_mod.load_binding(ctx.root, key)
    if not binding:
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "no binding", "session_key": key},
                        next_="由人先用 wf-start 选择对象")
    object_ref = binding.get("object") or {}
    if object_ref.get("id") == task_id and object_ref.get("kind") == "task":
        _require_instance_match(ctx, binding)
        return "task", None, ctx.require_held(task=task_id)
    task = load_task(ctx.root, task_id) or {}
    run_id = task.get("run_id")
    if run_id and object_ref.get("kind") == "run" and object_ref.get("id") == run_id:
        from . import runs as runs_mod

        run = runs_mod.load_run(ctx.root, run_id)
        if not isinstance(run, dict):
            raise TaskError("WF_HISTORY_UNRESOLVED", {"reason": "run record missing", "run": run_id})
        if run.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "run already ended", "terminal": run.get("terminal")})
        cursor = run.get("cursor") or {}
        if cursor.get("task_id") != task_id:
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "instance cursor is not on this task",
                             "cursor": cursor, "task": task_id},
                            next_="只推进游标所指的任务；换任务先 run advance")
        _require_instance_match(ctx, binding)
        return "run", run, ctx.require_held(run=run_id)
    raise TaskError("WF_BINDING_MISMATCH", {"bound": object_ref, "requested": task_id})


def rework_set(root, task_id):
    """返工集合：所有 `rework_of=T` 的活动与归档记录（机制稿 §6.2）。"""
    members = []
    for _path, other in iter_tasks(root):
        if other.get("rework_of") == task_id:
            members.append(other)
    return members


def reassess_write_right(ctx):
    """复评的写权事实：`(是否本会话持有, facts)`（机制稿 §6.2「未持权只报告待复评」）。"""
    record = ctx.writer() or {}
    holder = record.get("holder") or {}
    mine = record.get("state") == "held" and holder.get("id") == ctx.key()
    return mine, {"writer_state": record.get("state"), "writer_holder": holder.get("id")}


def reassess_problems(root, task):
    """挂起复评的四条条件（机制稿 §6.2，逐条给事实，不做优先级遮蔽）。"""
    task_id = task.get("id")
    members = rework_set(root, task_id)
    conditions = [
        {"condition": "task_suspended", "ok": bool(task.get("suspended")),
         "fact": {"suspended": bool(task.get("suspended"))}},
        {"condition": "rework_set_non_empty", "ok": bool(members),
         "fact": {"members": sorted(item.get("id") for item in members)}},
        {"condition": "rework_set_all_archived", "ok": bool(members) and all(
            item.get("status") == "archived" for item in members),
         "fact": {"unarchived": sorted(item.get("id") for item in members
                                       if item.get("status") != "archived")}},
        {"condition": "prerequisites_satisfied", "ok": not dependency_blockers(root, task),
         "fact": {"unmet": dependency_blockers(root, task)}},
        {"condition": "no_pending_action", "ok": actions.pending(task) is None,
         "fact": {"action": (task.get("action") or {}).get("kind"),
                  "state": (task.get("action") or {}).get("state")}},
    ]
    return conditions


def cmd_task_reassess(ctx, args):
    """挂起复评（机制稿 §6.2）：条件逐条核，满足则清 `suspended`（保留 `paused`）。

    未持写权只报「待复评」，不夺权；条件不满足不是失败——那正是"还在等返工"的正常状态，
    所以返回 `waiting` 与逐条事实，而不是造一个原因码。
    """
    from . import lock

    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-reassess requires --task <id>"})
    # 十六轮审查 a-4：先核绑定身份（绑定错仍拒绝），但**写权要求后移**——
    # bind_task_for_write 内含 require_held，未持权调用者会在"待复评"分支之前被拒，
    # 使机制稿 §6.2 承诺的只读报告不可达。未持权时按只读路径报告待复评；
    # 实际写入前（锁内）才 require_held。
    from . import session as session_mod

    binding = session_mod.load_binding(ctx.root, ctx.key())
    if not binding:
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "no binding", "session_key": ctx.key()},
                        next_="由人先用 wf-start 选择对象")
    _mine_early, writer_facts = reassess_write_right(ctx)
    mine, holder = False, None
    if _mine_early:
        _scope_kind, _run, holder = bind_task_for_write(ctx, task_id)
        mine = True
    if not mine:
        current = records.load_json(os.path.join(_require_task_dir(ctx, task_id), "task.json"))
        return codes.result(
            "WF_OK",
            object={"id": task_id, "name": current.get("title")},
            position_=codes.position(scope="task", phase=current.get("phase"), task_id=task_id),
            next_="写权不在本会话：只报告待复评，由持有写权的会话补做（不影响已成立的归档）",
            facts={"reassessed": False, "waiting": True, "pending_reassessment": True,
                   **writer_facts,
                   "conditions": reassess_problems(ctx.root, current)})
    with lock.acquire(ctx.root, holder_hint="task-reassess"):
        holder = ctx.require_held(**({"task": task_id} if _scope_kind == "task"
                                    else {"run": (_run or {}).get("id")}))[1]
        path = _require_task_dir(ctx, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived", "task": task_id})
        if not task.get("suspended"):
            return codes.result(
                "WF_OK", object={"id": task_id, "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                next_="该任务未挂起，无需复评（幂等）",
                facts={"reassessed": False, "suspended": False,
                       "conditions": reassess_problems(ctx.root, task)})
        conditions = reassess_problems(ctx.root, task)
        unmet = [item["condition"] for item in conditions if not item["ok"]]
        if unmet:
            return codes.result(
                "WF_OK", object={"id": task_id, "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
                next_="返工尚未全部归档或前置未满足：保持挂起，待复评（清挂起只在这些条件成立时发生）",
                facts={"reassessed": False, "waiting": True, "unmet": unmet,
                       "conditions": conditions})
        task["suspended"] = False
        # 清挂起保留 paused；若因此会出现第二个执行候选，同时记 paused + 等待人恢复（机制稿 §6.2）
        others = [other for _p, other in iter_tasks(ctx.root)
                  if other.get("id") != task_id and other.get("status") == "in_progress"
                  and not other.get("paused") and not other.get("suspended")]
        waiting_for_human = bool(others) and not task.get("paused")
        if waiting_for_human:
            task["paused"] = True
            task["pause_reason"] = {"reason": "reassessment done; another candidate is running",
                                    "at": records.now_str(), "by": "task.reassess"}
        inputs = {"task": task_id, "cleared": True}
        task, action = _start_task_action(ctx, path, task, "task.transition", holder, inputs,
                                          ["recheck_conditions", "clear_suspended"])
        task, assertion = _finish_task_action(ctx, path, task, "task.transition", holder, inputs,
                                              action, evidence_refs=[f"reassess:{task_id}"])
    return codes.result(
        "WF_OK", object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_=("已清挂起；因另有执行候选，本任务同时置暂停，等待人恢复"
               if waiting_for_human else "已清挂起；按就绪选择恢复"),
        facts={"reassessed": True, "suspended": False, "paused": bool(task.get("paused")),
               "waiting_for_human": waiting_for_human, "conditions": conditions,
               "control_assertion": assertion})


def _replace_preview(ctx, task, decision, successor_paths, decision_path):
    """替换的只读预览（机制稿 §6.3：预览固定 S id、原前置、来源提交/路径、返工来源、下游重连、实例映射）。

    只读：不建 S、不改 T、不写任何记录。人据此确认 `touch_paths` 是否覆盖继承路径。
    """
    from . import paths as paths_mod

    task_id = task.get("id")
    imported = scope.installed_asset_paths(ctx.root)
    inherited = sorted(
        path for path in (set(scope.attributed_paths(ctx.root, task_id, task.get("baseline_head")))
                          | set(scope.attributed_by_decision(ctx.root, task)))
        if not scope._is_control_record(path, task_id, imported, ctx.root))
    uncovered = [item for item in inherited
                 if not any(paths_mod.match_path(pattern, item) for pattern in successor_paths)]
    downstream = [other.get("id") for _path, other in iter_tasks(ctx.root)
                  if task_id in (other.get("prerequisites") or [])
                  and other.get("status") != "archived"]
    unfinished = [other.get("id") for _path, other in iter_tasks(ctx.root)
                  if other.get("rework_of") == task_id and other.get("status") != "archived"]
    run_map = None
    if task.get("run_id"):
        from . import runs as runs_mod

        run = runs_mod.load_run(ctx.root, task["run_id"]) or {}
        step_id = next((sid for sid, mapping in (run.get("task_map") or {}).items()
                        if (mapping or {}).get("task_id") == task_id), None)
        run_map = {"run": task.get("run_id"), "step_id": step_id,
                   "would_point_to_successor": bool(step_id),
                   "cursor": run.get("cursor"), "run_terminal": run.get("terminal")}
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_=("确认 touch_paths 覆盖 inherited 后带 --decision 重入（会被固定的 S id 届时生成）"
               if not uncovered else
               "当前 touch_paths 未覆盖 uncovered 中的继承路径：回 Plan 补齐后再替换"),
        facts={"preview": True, "task": task_id,
               "successor_id": "（届时生成：new_task_record 的 2026-<32hex>）",
               "predecessor_prerequisites": task.get("prerequisites") or [],
               "inherited_paths": inherited, "uncovered_by_touch_paths": uncovered,
               "touch_paths": successor_paths,
               "downstream_to_repoint": downstream,
               "unfinished_rework": unfinished,
               "run_mapping": run_map,
               "decision": decision_path, "paused": bool(task.get("paused")),
               "suspended": bool(task.get("suspended"))})


REPLACE_CHOICES = ("replace", "替换")


def cmd_task_replace(ctx, args):
    """替换（机制稿 §6.3）：建继任者 S、登记继承、重连下游与实例映射，最后异常归档 T。

    顺序与「先验证、后落盘」按 §6.3：① 预检 S 的目标/候选图与「S 的拟触碰面是否覆盖继承路径」；
    ② 建 S 的规划记录（**不代批准**：S 开工仍须自己当前版本批准）；③ 登记继承
    （写入 S 的 `attribution.inherited`，它是 §3.3「最终触碰集合」的一部分）；
    ④ 重连下游前置；⑤ 在途实例的 `task_map`/`cursor` 指向 S；⑥ 按异常归档处置 T（复用 `_apply_abandon`）。
    """
    from . import cli, lock, paths as paths_mod

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id or not decision_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-replace requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    decision = decisions[0]
    if str(decision.get("choice") or "") not in REPLACE_CHOICES:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "replace decision choice must be 替换/replace",
                         "got": decision.get("choice"), "accepted": list(REPLACE_CHOICES)})
    successor_paths = [path for path in (decision.get("touch_paths") or []) if isinstance(path, str)]
    if args.flag("--preview"):
        task = _load_or_fail(ctx, task_id)
        return _replace_preview(ctx, task, decision, successor_paths, decision_path)
    _scope_kind, _run, holder = bind_task_for_write(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-replace"):
        holder = ctx.require_held(**({"task": task_id} if _scope_kind == "task"
                                    else {"run": (_run or {}).get("id")}))[1]
        path = _require_task_dir(ctx, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "archived object does not accept replace", "task": task_id})
        if task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "suspended task must dispose its rework first", "task": task_id})
        if task.get("paused"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "paused task must be resumed before replacement",
                             "task": task_id},
                            next_="先 task-resume 把暂停处置掉（§6.3 的输入条件），再替换")
        if not successor_paths:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "replace decision must declare the successor's touch_paths",
                             "hint": "人确认 S 的拟触碰面；它必须覆盖继承路径"},
                            next_="在决定文件里给 touch_paths（S 的拟触碰面）后重入")
        # 继承路径 = T 的归属路径（机制稿 §3.3 的「替换继承路径」）
        # 继承的是**交付路径**，不含 T 自己的控制记录（任务目录/实例记录等固定职责记录
        # 不随业务继承；把它们算进来会让"覆盖继承路径"永远不成立——实测踩到过）
        installed = scope.installed_asset_paths(ctx.root)
        inherited = sorted(
            path for path in (set(scope.attributed_paths(ctx.root, task_id, task.get("baseline_head")))
                              | set(scope.attributed_by_decision(ctx.root, task)))
            if not scope._is_control_record(path, task_id, installed, ctx.root))
        uncovered = [item for item in inherited
                     if not any(paths_mod.match_path(pattern, item) for pattern in successor_paths)]
        if uncovered:
            # §6.3：不覆盖则保留原态并回规划
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "successor touch_paths do not cover the inherited paths",
                             "inherited": inherited, "uncovered": uncovered,
                             "successor_paths": successor_paths},
                            next_="回 Plan 把继承路径纳入 S 的触碰面后重新替换（本次未写入任何记录）")
        successor = new_task_record("ordinary", f"{task.get('title') or task_id}（接替）")
        successor_id = successor["id"]
        directory = join(ctx.root, f"{TASKS_REL}/{dir_name(successor_id, successor['title'])}")
        staging = join(ctx.root, f"{TASKS_REL}/.staging-{successor_id}")
        if os.path.exists(directory) or os.path.exists(staging):
            raise cli.CliError("WF_TARGET_COLLISION", {"path": directory})
        graph = _prerequisite_graph(ctx.root)
        graph[successor_id] = list(task.get("prerequisites") or [])
        cycle = _find_cycle(graph, successor_id)
        if cycle:
            raise TaskError("WF_DEPENDENCY_UNMET",
                            {"reason": "candidate graph has a cycle", "cycle": cycle})
        inputs = {"task": task_id, "successor": successor_id,
                  "inherited": inherited, "decision": decision}
        task, action = _start_task_action(
            ctx, path, task, "task.replace", holder, inputs,
            ["preflight", "create_successor", "register_inheritance",
             "reconnect_downstream", "update_run_map", "abandon_task"])
        successor["run_id"] = task.get("run_id") if _scope_kind == "run" else None
        successor["attribution"] = {"decisions": [],
                                    "inherited": [{"source_task": task_id,
                                                   "paths": inherited,
                                                   "decision": decision}]}
        _publish_task_tree(ctx, directory, staging, join(ctx.root, ".wf/templates/task"), successor)
        # ④ 下游重连：原本以 T 为前置的活动任务改挂 S（死引用不留）
        repointed = []
        for other_path, other in list(iter_tasks(ctx.root)):
            prerequisites = list(other.get("prerequisites") or [])
            if task_id not in prerequisites or other.get("id") == successor_id:
                continue
            if other.get("status") == "archived":
                continue
            other = dict(other, prerequisites=[successor_id if item == task_id else item
                                               for item in prerequisites])
            save_task(ctx.root, other_path, other)
            repointed.append(other.get("id"))
        # ⑤ 在途实例映射：该步骤的正式任务改为 S，游标跟着走
        if _scope_kind == "run" and _run and not _run.get("terminal"):
            from . import runs as runs_mod

            task_map = dict(_run.get("task_map") or {})
            step_id = next((sid for sid, mapping in task_map.items()
                            if (mapping or {}).get("task_id") == task_id), None)
            if step_id:
                task_map[step_id] = dict(task_map[step_id], task_id=successor_id,
                                        superseded_ids=list(
                                            (task_map[step_id] or {}).get("superseded_ids") or []
                                        ) + [task_id])
                runs_mod.save_run(ctx.root, dict(_run, task_map=task_map,
                                                 cursor={"step_id": step_id,
                                                         "task_id": successor_id}))
        task["successor_id"] = successor_id
        task, assertion = _finish_task_action(ctx, path, task, "task.replace", holder, inputs,
                                              action, evidence_refs=[f"successor:{successor_id}"])
        # ⑥ 按异常归档处置 T（复用放弃本体；未提交改动由决定文件的 disposition 承载）
        payload = _apply_abandon(ctx, task_id, task, path, [decision],
                                 decision.get("disposition"), holder)
        abandoned = (payload or {}).get("code") in (None, "WF_OK")
    next_ = ("T 已异常归档、S 已建立但**未批准**：S 须自己当前版本批准后开工（继承的触碰面不是开工许可）"
             if abandoned else
             "S 已建立并登记继承；T 的未提交改动尚未处置，按其出口处理后重入 task-abandon")
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="finish", task_id=task_id,
                                 action_id=task["action"]["id"],
                                 action_state=task["action"]["state"]),
        next_=next_,
        facts={"task": task_id, "successor": successor_id,
               "directory": os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
               "inherited": inherited, "repointed": repointed,
               "run_mapping_updated": bool(_scope_kind == "run" and _run),
               "abandoned": abandoned,
               "control_assertion": assertion})

REWORK_CHOICES = ("rework", "返工")


def _decision_draft_result(ctx, task_id, entries, *, command, extra_facts=None):
    """决定文件草稿（十六轮批V）：只打印不落盘、不要求写权——结构与摘要由入口算好。

    **作决定 vs 转录（设计稿 §1.2）**：决定内容必须是人已明确给出的选择；本骨架只消除
    "猜字段"的成本，模型可按人的明确答复填写并落盘，但不得推测、补造或替人选择。
    占位统一 TODO 前缀（`_load_decision` 会拒绝照抄）。
    """
    facts = {"draft": entries, "note": "草稿只读；本次未写入任何记录"}
    if extra_facts:
        facts.update(extra_facts)
    return codes.result(
        "WF_OK",
        object={"id": task_id},
        position_=codes.position(scope="task", task_id=task_id),
        next_=(f"草稿只打印不落盘；按人的明确答复填写（去掉 TODO；不得推测或替人选择）并写成决定文件后，"
               f"以 `{command} --task {task_id} --decision <文件>` 正式执行"),
        facts=facts)


def _prd_digest_for_task(ctx, task_id):
    """当前任务 PRD 的内容摘要（与正式批准同一读数；任务目录缺失仍按记录错误报）。"""
    _require_task_dir(ctx, task_id)
    return prd_digest(ctx.root, {"id": task_id})


def cmd_task_rework(ctx, args):
    """返工（机制稿 §6.2）：建 R 并让 T 挂起，R 独立批准/开工，不消费 T 的批准。

    在 T 的动作里**一次固定完整候选**（R 继承 T 的原前置与 `rework_of=T`、T 的 `prerequisites`
    增 R 且 `suspended=true`）；先预检目标碰撞与候选图，再落盘。同实例时在 `sequence_changes`
    登记并让 `cursor.task_id` 临时定位 R（T 不自动 paused）；普通任务绑定则 T 显式暂停并释放写权，
    由新会话绑定 R。
    """
    if args.flag("--draft"):
        # 十六轮批V：返工决定草稿——subject 指向本任务，reason 由人写返工原因。
        task_id = args.value("--task")
        if not task_id:
            raise TaskError("WF_USAGE_INVALID", {"reason": "task-rework requires --task <id>"})
        entry = {"source": "TODO human:<来源>", "at": records.now_str(),
                 "subject": f"rework {task_id}", "object_digest": "",
                 "choice": "rework",
                 "reason": "TODO（人填写：为什么返工、返工范围）"}
        return _decision_draft_result(ctx, task_id, [entry], command="task-rework")
    from . import cli, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id or not decision_path:
        raise TaskError("WF_USAGE_INVALID", {"reason": "task-rework requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    decision = decisions[0]
    if str(decision.get("choice") or "") not in REWORK_CHOICES:
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "rework decision choice must be 返工/rework",
                         "got": decision.get("choice"), "accepted": list(REWORK_CHOICES)})
    _scope_kind, _run, holder = bind_task_for_write(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-rework"):
        holder = ctx.require_held(**({"task": task_id} if _scope_kind == "task"
                                    else {"run": (_run or {}).get("id")}))[1]
        path = _require_task_dir(ctx, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived" or task.get("terminal"):
            raise TaskError("WF_BINDING_MISMATCH",
                            {"reason": "archived object does not accept rework", "task": task_id})
        if task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "task already suspended by another rework", "task": task_id})
        # 预检：R 的目标、候选图（T 的新前置集合 = 原前置 + R）
        rework = new_task_record("ordinary", f"{task.get('title') or task_id}（返工）")
        rework_id = rework["id"]
        rework["rework_of"] = task_id
        rework["prerequisites"] = list(task.get("prerequisites") or [])
        directory = join(ctx.root, f"{TASKS_REL}/{dir_name(rework_id, rework['title'])}")
        staging = join(ctx.root, f"{TASKS_REL}/.staging-{rework_id}")
        if os.path.exists(directory) or os.path.exists(staging):
            raise cli.CliError("WF_TARGET_COLLISION", {"path": directory})
        graph = _prerequisite_graph(ctx.root)
        graph[task_id] = list(task.get("prerequisites") or []) + [rework_id]
        graph[rework_id] = list(rework["prerequisites"])
        cycle = _find_cycle(graph, task_id)
        if cycle:
            raise TaskError("WF_DEPENDENCY_UNMET",
                            {"reason": "candidate graph has a cycle", "cycle": cycle})
        same_instance = bool(task.get("run_id"))
        inputs = {"task": task_id, "rework": rework_id, "same_instance": same_instance,
                  "decision": decision}
        task, action = _start_task_action(
            ctx, path, task, "task.rework", holder, inputs,
            ["preflight_graph", "create_rework", "suspend_task", "update_sequence"])
        tasks_mod_publish = _publish_task_tree
        tasks_mod_publish(ctx, directory, staging,
                          join(ctx.root, ".wf/templates/task"), rework)
        task["prerequisites"] = list(task.get("prerequisites") or []) + [rework_id]
        task["suspended"] = True
        sequence = []
        if same_instance:
            from . import runs as runs_mod

            run = runs_mod.load_run(ctx.root, task["run_id"])
            if isinstance(run, dict) and not run.get("terminal"):
                step_id = next((sid for sid, mapping in (run.get("task_map") or {}).items()
                                if (mapping or {}).get("task_id") == task_id), None)
                sequence = list(run.get("sequence_changes") or []) + [{
                    "kind": "rework", "step_id": step_id, "source_task": task_id,
                    "task_id": rework_id, "resume_task": task_id, "decision": decision}]
                run = dict(run, sequence_changes=sequence,
                           cursor={"step_id": step_id, "task_id": rework_id})
                runs_mod.save_run(ctx.root, run)
        task, assertion = _finish_task_action(
            ctx, path, task, "task.rework", holder, inputs, action,
            evidence_refs=[f"rework:{rework_id}"])
    paused_for_handover = not same_instance
    released = False
    assertion_tail = None
    if paused_for_handover:
        # 机制稿 §6.2：「T 显式暂停、**保存交接/工作区**并 release」——三件都要做。
        # 只暂停不存 WIP，会让新会话看不到"T 还留着哪些未提交改动"，也让 disposition 无处落地。
        preview = _abandon_preview(ctx, task)
        retained = sorted(preview.get("uncommitted") or [])
        task = dict(task, paused=True,
                    pause_reason={"reason": "rework handover", "at": records.now_str(),
                                  "by": "task.rework", "rework": rework_id},
                    handoff=dict(task.get("handoff") or {},
                                 wip={"decision": decision, "object": {"kind": "task", "id": task_id},
                                      "task_id": task_id, "step_id": task.get("phase"),
                                      "paths": retained, "risks": [], "pending": [],
                                      "resolved": None,
                                      "note": "rework handover：T 暂停并把工作区交给 R 会话处置"}))
        save_task(ctx.root, path, task)
        # 机制稿 §6.2：普通任务绑定分支由本入口完成 release（新会话才能绑定 R）。
        # 释放与「暂停已落盘」同一原子段：暂停没落盘就释放，等于把 T 的进度交给一个不知道要暂停的会话。
        with lock.acquire(ctx.root, holder_hint="task-rework release"):
            ctx.require_held(task=task_id)
            from . import writer as writer_mod

            updated = writer_mod.release(ctx.writer())
            writer_mod.save(ctx.root, updated)
            from . import cli as cli_mod

            assertion_tail = cli_mod._atomic_writer_action(
                ctx, updated, "writer.release",
                {"kind": "session", "id": ctx.key(),
                 "scope": {"object": {"kind": "task", "id": task_id}}},
                {"session_key": ctx.key(), "via": "task-rework"},
                ["verify_scope", "release"],
                lambda current: True,
            )
        released = True
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                 action_id=task["action"]["id"],
                                 action_state=task["action"]["state"]),
        next_=("同一实例：cursor 已临时定位到 R，完成 R 后 task-reassess 恢复 T"
               if same_instance else
               "T 已暂停且写权已释放：在新会话绑定 R（R 须独立批准与开工，不消费 T 的批准）"),
        facts={"task": task_id, "rework": rework_id,
               "directory": os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
               "prerequisites": task["prerequisites"], "suspended": True,
               "same_instance": same_instance, "sequence_changes": sequence,
               "paused_for_handover": paused_for_handover, "released": released,
               "release_assertion": assertion_tail,
               "control_assertion": assertion})


def wip_paths(task):
    """任务真实保留的 WIP 路径（handoff.wip.paths 为指纹条目或字符串）。"""
    wip = ((task.get("handoff") or {}).get("wip")) or {}
    if not wip or wip.get("resolved"):
        return []
    paths = []
    for item in wip.get("paths") or []:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]))
    return paths


def ensure_releasable(task, root=None):
    if task.get("status") == "archived":
        return True
    retained = wip_paths(task)
    if root is not None and retained:
        from . import scope as scope_mod

        dirty = set(scope_mod.uncommitted_paths(root))
        still = [path for path in retained if path in dirty]
        if still:
            raise TaskError("WF_WORKSPACE_UNRESOLVED",
                            {"reason": "retained WIP not disposed", "paths": still},
                            next_="先处置保留 WIP（提交/反向修正/承接）再释放写权")
    pending = (task.get("disposition") or {}).get("pending") or []
    if pending:
        raise TaskError("WF_WORKSPACE_UNRESOLVED",
                        {"reason": "task keeps un-disposed WIP", "pending": pending},
                        next_="先按 disposition 落实保留 WIP 再释放写权")
    if task.get("paused") or task.get("terminal"):
        return True
    if task.get("suspended"):
        raise TaskError("WF_SEMANTIC_DECISION", {"reason": "suspended task cannot be released as idle"})
    raise TaskError("WF_SEMANTIC_DECISION", {"reason": "release requires paused or terminal object",
                                             "status": task.get("status"), "phase": task.get("phase")})


def stop_work(ctx, decisions, choice):
    from . import cli, lock

    key = ctx.key()
    binding = session_mod.load_binding(ctx.root, key)
    if not binding:
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "no binding"})
    object_ref = binding.get("object") or {}
    if object_ref.get("kind") != "task":
        raise TaskError("WF_BINDING_MISMATCH", {"reason": "instance stop requires round 2"})
    task_id = object_ref.get("id")
    with lock.acquire(ctx.root, holder_hint="stop"):
        record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        from . import paths as paths_mod

        paths = _subject_paths(decisions[0].get("subject"))
        choice_now = decisions[0].get("choice")
        if not paths and choice_now != "transfer":
            # 无 WIP 时允许空路径：只显式记载没有任何覆盖路径（P3）
            if scope.uncommitted_paths(ctx.root):
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "工作区有未提交差异，收工决定须在 subject 列出覆盖路径"})
        items = []
        for relative in paths:
            try:
                items.append(fingerprint.item(ctx.root, relative))
            except records.RecordInvalid as exc:
                raise TaskError("WF_PATH_INVALID", {"reason": str(exc), "path": relative})
        # 损坏的快照必须显式拒绝：静默折叠成空批准面会放行越界 keep
        touch = approved_touch_paths(task)
        receipts = task_receipts(ctx.root)
        classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
        pending = sorted(set(classified["buckets"]["e"]) & set(scope.uncommitted_paths(ctx.root)))

        def covered(candidate, patterns):
            return any(candidate == pattern or paths_mod.match_path(pattern, candidate) for pattern in patterns)

        unlisted = [item for item in pending if not covered(item, paths)]
        if unlisted:
            raise TaskError("WF_WORKSPACE_UNRESOLVED",
                            {"reason": "收工选择未覆盖本任务全部未提交改动",
                             "unlisted": unlisted, "declared": paths})
        if choice == "keep":
            out_of_scope = [item for item in paths if not covered(item, touch)]
            if out_of_scope:
                raise TaskError("WF_WORKSPACE_UNRESOLVED",
                                {"reason": "保留 WIP 只适用于当前批准范围内且归属明确的路径",
                                 "out_of_scope": out_of_scope, "approved": touch})
            commit_result = None
        elif choice == "commit":
            # decisions[0] 是收工选择本身；授权必须是其后的独立 Decision（机制稿 §4.3）
            grants = [item for item in decisions[1:]
                  if decisions_mod.accepts("commit_grant", item.get("choice"))]
            grant_paths = [path for grant in grants for path in _subject_paths(grant.get("subject"))]
            uncovered = [item for item in paths if not covered(item, grant_paths)]
            if not grants or uncovered:
                raise TaskError("WF_COMMIT_NOT_AUTHORIZED",
                                {"reason": "提交授权须覆盖本次收工的每个路径",
                                 "uncovered": uncovered, "grant_paths": grant_paths})
            commit_result = _commit_paths(ctx.root, paths, f"wf: wip {task_id}\n\nwf-task: {task_id}")
            leftover = [item for item in scope.uncommitted_paths(ctx.root)
                        if any(item == path or paths_mod.match_path(path, item) for path in paths)]
            if leftover:
                raise TaskError("WF_PERSISTENCE_FAILED",
                                {"reason": "收工提交后仍有未提交差异", "leftover": leftover})
        elif choice == "reverse":
            dirty = [item for item in paths
                     if scope.git(ctx.root, "status", "--porcelain", "--", item)[1].strip()]
            if dirty:
                raise TaskError("WF_WORKSPACE_UNRESOLVED",
                                {"reason": "反向修正尚未实际完成（路径仍有差异）", "dirty": dirty})
            commit_result = {"reversed": True, "paths": paths}
        else:  # transfer
            # 承接对象用**专用字段** `target_task`（与 repair 的 disposition 同一约定，机制稿 §5.6）；
            # subject 只列待承接路径。早期实现把 subject 首项当 id，导致 id 与路径混在一张清单里
            # 被逐项指纹化，实际无法表达"承接任务 + 待承接路径"（2026-11-05 第七轮复审后续查证）。
            declared = decisions[0]
            target = str(declared.get("target_task") or "").strip()
            # 不做"subject 首项即 id"的兼容回退：真实 WIP 路径可能与任务 id 同形，
            # 回退会把它从核验面里静默移走（2026-11-05 第八轮复审 F8-1）。
            wip_paths = paths
            if not target or not TASK_ID_RE.match(target):
                raise TaskError("WF_SEMANTIC_DECISION", {
                    "reason": "transfer 须在 Decision.target_task 给出承接任务 id",
                    "target_task": declared.get("target_task"), "subject": declared.get("subject"),
                    "exits": ["补 Decision.target_task 后重试",
                              "改选 keep 保留 WIP（当前批准范围内）",
                              "由人实际处置这些改动后重试"],
                })
            target_task = load_task(ctx.root, target)
            if target_task is None or target == task_id:
                raise TaskError("WF_SEMANTIC_DECISION", {
                    "reason": "transfer 须给出存在且不同于本任务的具名承接任务 id",
                    "target": target, "is_self": target == task_id,
                    "exits": ["补一个存在且属于其他任务的 Decision.target_task 后重试",
                              "先新建并批准承接任务，再重试本次收工",
                              "改选 keep 保留 WIP（当前批准范围内）"],
                })
            # 「选择不等于已落实」（设计稿 §4.4）：承接必须可核——任务未归档、已批准，
            # 且批准触碰面覆盖待承接的全部路径；否则保留待决，不写 resolved。
            if target_task.get("status") == "archived" or target_task.get("terminal"):
                raise TaskError("WF_SEMANTIC_DECISION", {
                    "reason": "承接任务已归档/终止，不能承接 WIP",
                    "target": target, "status": target_task.get("status"),
                    "terminal": target_task.get("terminal"),
                    "exits": ["改选一个未归档、已批准且覆盖这些路径的任务承接",
                              "由人实际处置这些改动后重试",
                              "改选 keep 保留 WIP（当前批准范围内）"],
                })
            # 承接范围与写入口同一判定（F7-2）：已开工任务不回退可变 plan，空数组照用
            target_approved = approved_touch_paths(target_task)
            target_plan = target_task.get("plan") or {}
            target_approval = target_plan.get("approval")
            target_approval_valid = _is_approved_plan(target_task, ctx.root)
            uncovered_transfer = [item for item in wip_paths
                                  if not covered(item, target_approved)]
            if not target_approval_valid or uncovered_transfer:
                raise TaskError("WF_SEMANTIC_DECISION", {
                    "reason": "承接任务尚未有效批准，或批准触碰面未覆盖待承接路径",
                    "target": target, "approved": target_approved,
                    "approval_valid": target_approval_valid,
                    "uncovered": uncovered_transfer,
                    "exits": ["先让承接任务批准并覆盖这些路径后重试",
                              "改选另一个已批准且覆盖这些路径的承接任务",
                              "由人实际处置这些改动，或改选 keep 保留 WIP"],
                })
            commit_result = {"transferred_to": target,
                             "approved": target_approved,
                             "approval": target_approval}
        task.setdefault("handoff", {})["wip"] = {
            "decision": decisions[0],
            "object": object_ref,
            "task_id": task_id,
            "step_id": task.get("phase"),
            "paths": items,
            "risks": [item.get("reason") for item in decisions],
            "pending": [],
            # 只有 keep 才是「保留未处置」；其余选择按实际处置写解除结论与证据（机制稿 §6.4）
            "resolved": None if choice == "keep" else {
                "choice": choice,
                "evidence": commit_result,
                "at": records.now_str(),
            },
        }
        task["paused"] = True
        inputs = {"task": task_id, "choice": choice}
        task, action = _start_task_action(ctx, path, task, "session.stop", holder, inputs, ["record_wip", "pause"])
        task, assertion = _finish_task_action(ctx, path, task, "session.stop", holder, inputs, action)
        updated = writer_mod.release(record)
        writer_mod.save(ctx.root, updated)
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_="写权已释放；同对象恢复需核真实 WIP 与代次",
        facts={"wip": task["handoff"]["wip"], "commit": commit_result, "generation": updated.get("generation"),
               "control_assertion": assertion},
    )




def _subject_paths(subject):
    """Decision.subject 中的路径/对象列表：接受数组或 `,;/换行` 分隔的字符串。"""
    if isinstance(subject, list):
        return [str(item).strip() for item in subject if str(item).strip()]
    if not isinstance(subject, str):
        return []
    import re

    # 空格也算分隔：help 示例是单路径，AI 很容易写成空格分隔；拒收只会浪费一轮试错
    return [token.strip() for token in re.split(r"[,;\n\s]+", subject) if token.strip()]


def _removal_attributed(ctx, path, task, receipts):
    """该路径的"已不存在"是否有本任务的删除/改名事实支撑（机制稿 §4.2 触碰路径含删除与旧路径）。"""
    from . import scope as scope_mod

    # attributed_paths 返回的是路径列表（不是带 changes 的字典）：判定归属用成员关系
    attributed = scope_mod.attributed_paths(ctx.root, task.get("id"),
                                            task.get("baseline_head")) or []
    if path in set(attributed) and not os.path.exists(join(ctx.root, path)):
        return True
    for receipt in receipts or []:
        for change in receipt.get("changes") or []:
            if isinstance(change, dict) and change.get("path") == path:
                after = change.get("after")
                if isinstance(after, dict) and after.get("exists") is False:
                    return True
    return False


def retrospective_evidence_problems(ctx, task):
    """复盘触发事实所引的调试证据是否仍可核对（机制稿 §11.2「核对所引证据仍真实存在」）。

    三类引用分开处理：符号引用（handoff / check:<id> / check_history id）、提交、
    以及形如路径的文件引用（必须是文件，目录不算证据）。
    """
    from . import scope as scope_mod

    problems = []
    declarations = {entry.get("verification_id"): entry
                    for entry in (task.get("execution") or {}).get("debug_declarations") or []
                    if isinstance(entry, dict)}
    history = {entry.get("id"): entry for entry in task.get("check_history") or []
               if isinstance(entry, dict)}
    rulings = [entry for entry in (task.get("execution") or {}).get("human_decisions") or []
               if str(entry.get("subject", "")).startswith("debug-ruling-")]
    for ruling in rulings:
        subject = str(ruling.get("subject"))
        head, _sep, tail = subject.rpartition("-")
        if not head or not tail.isdigit():
            problems.append({"subject": subject, "reason": "malformed ruling subject"})
            continue
        verification_id = head[len("debug-ruling-"):] if head.startswith("debug-ruling-") else head
        declaration = declarations.get(verification_id) or {}
        for item in declaration.get("evidence_refs") or []:
            ref = str(item.get("path")) if isinstance(item, dict) else str(item)
            if not ref:
                continue
            problem = _evidence_ref_problem(ctx, ref, history, scope_mod)
            if problem:
                problems.append(dict(problem, subject=subject))
    return problems


def _evidence_ref_problem(ctx, ref, history, scope_mod):
    """单个证据引用的问题（None 表示可核对）。"""
    if ref in history:
        return _check_entry_evidence_problem(ctx, history[ref], ref)
    if ref.startswith("check:"):
        target = ref.split(":", 1)[1]
        if target in history:
            return _check_entry_evidence_problem(ctx, history[target], ref)
        return {"reason": "symbolic reference cannot be resolved", "ref": ref}
    if ref in SYMBOLIC_EVIDENCE_REFS:
        return None
    if _looks_like_commit(ref):
        return None if scope_mod.is_ancestor(ctx.root, ref) else \
            {"reason": "referenced commit unreachable", "ref": ref}
    absolute = join(ctx.root, ref)
    if os.path.exists(absolute) and not os.path.isfile(absolute):
        return {"reason": "referenced evidence is not a file", "ref": ref}
    if not _ref_is_path_like(ref):
        return None
    if not os.path.exists(absolute):
        return {"reason": "referenced evidence missing", "ref": ref}
    if not os.path.isfile(absolute):
        return {"reason": "referenced evidence is not a file", "ref": ref}
    return None


def _check_entry_evidence_problem(ctx, entry, ref):
    """check 条目内的证据文件仍须存在（机制稿允许引用 check_history，但所引事实要能核对）。"""
    for command in entry.get("commands") or []:
        evidence = command.get("evidence_ref") if isinstance(command, dict) else None
        if isinstance(evidence, str) and evidence and not os.path.isfile(join(ctx.root, evidence)):
            return {"reason": "check evidence file missing", "ref": ref, "file": evidence}
    return None


SYMBOLIC_EVIDENCE_REFS = frozenset({"handoff", "session", "handoff.progress", "check"})

def _ref_is_path_like(ref):
    """只有形如路径的引用才核文件存在（`handoff`、`check:<id>` 这类符号引用不判）。"""
    if ref.startswith("check:") or "/" in ref or "\\" in ref:
        return True
    return bool(os.path.splitext(ref)[1])


def _looks_like_commit(value):
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def inspect(ctx):
    active, archived = _task_dirs(ctx.root)
    tasks = list(iter_tasks(ctx.root))
    ids = {}
    for path, task in tasks:
        ids.setdefault(task.get("id"), []).append(os.path.relpath(path, str(ctx.root)))
    duplicates = {key: value for key, value in ids.items() if len(value) > 1}
    broken_dirs = broken_task_dirs(ctx.root)
    writer = writer_mod.load(ctx.root) or {}
    receipts = task_receipts(ctx.root)  # 巡检同样消费可达提交查证（机制稿 §4.5）
    bindings_dir = join(ctx.root, ".wf/session-bindings")
    bindings = len(os.listdir(bindings_dir)) if os.path.isdir(bindings_dir) else 0
    facts = {
        "tasks": {"active": len(active), "archived": len(archived), "total": len(tasks)},
        "duplicate_ids": duplicates,
        "broken_task_dirs": broken_dirs,
        "writer": {"state": writer.get("state"), "generation": writer.get("generation"),
                   "receipts": receipts},
        "bindings": bindings,
        "spec": _spec_summary(ctx.root),
        "governance": _governance_summary(ctx.root, tasks, archived),
        # 治理面声明本轮**未输出**的类别（A5 纪律）：交付后不得再有「未声明且未输出」的类。
        # 2026-11-12：`manual_compare`/`author_order`/`out_of_scope_duplicates` 均已交付，
        # 清单据此清空——空列表本身是断言（「没有隐瞒的类别」），不是省略。
        "governance_omitted": [],
    }
    warnings = []
    for receipt in receipts:
        if receipt["state"] in ("pending_check",):
            warnings.append({"receipt": receipt["operation"], "state": receipt["state"]})
    governance_facts = facts.get("governance") or {}
    for problem in (governance_facts.get("archive_terminals") or {}).get("problems") or []:
        warnings.append({"area": "archive_terminals", "problem": problem})
    for problem in (governance_facts.get("archive_references") or {}).get("dangling") or []:
        warnings.append({"area": "archive_references", "problem": problem})
    for item in (governance_facts.get("archive_references") or {}).get("unknown") or []:
        warnings.append({"area": "archive_references", "unknown": item})
    # D-10：目录数与可解析记录数不一致说明有孤儿目录
    if len(active) != len([1 for _p, t in tasks if t.get("status") != "archived"]):
        warnings.append({"area": "tasks", "problem": "active directory count differs from parsed records",
                         "active_dirs": len(active)})
    return codes.result("WF_OK", position_=codes.position(scope="maintenance" if writer.get("holder") else None),
                        next_="按报告逐项处置；修复另取授权", facts=facts, warnings=warnings)


def _scan_repo_paths(root):
    """本次巡检可读的合法仓库路径：已跟踪 + 未忽略的未跟踪（不含 `.git/`）。

    只看工作树，不做历史回扫（机制稿 §8.5 的比对范围就是「本次有效 active spec 的合法模式
    × 同一次巡检的项目路径范围」）。读不出就抛 OSError，由调用方记 unknown 而不是当零。
    """
    proc = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z",
                           "--cached", "--others", "--exclude-standard"],
                          cwd=str(root), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    paths = []
    for item in proc.stdout.split("\0"):
        if not item or item.startswith(".git/"):
            continue
        paths.append(item)
    return sorted(set(paths))


def _manual_compare(root):
    """「需人工比对」清单（机制稿 §8.5 三步算法；设计稿 §6.2）。

    分类只有两种：`witnessed`（有当前路径同时命中两份规则——证明适用范围相交，**不证明内容矛盾**）
    与 `potential`（前缀规则不能排除重叠、且无当前见证）。**不判定语义矛盾**：那要人对照正文。
    未知不当零：无合法 paths、条目非法、扫描不可用都进 `unverified`，且不据此给出候选结论。
    """
    from . import paths as paths_mod
    from . import spec as spec_mod

    unverified = []
    entries = []
    for entry in spec_mod.all_specs(root):
        problems = list(entry.get("problems") or []) + list(entry.get("path_problems") or [])
        if problems:
            unverified.append({"path": entry.get("path"), "reason": "spec unparsable or illegal",
                               "problems": problems})
            continue
        if (entry.get("metadata") or {}).get("status") != "active":
            continue
        patterns = [item for item in entry.get("paths") or [] if isinstance(item, str) and item]
        if not patterns:
            unverified.append({"path": entry.get("path"),
                               "reason": "active spec declares no legal paths"})
            continue
        entries.append({"path": entry.get("path"), "patterns": sorted(set(patterns))})

    repo_paths = _scan_repo_paths(root)
    if repo_paths is None:
        unverified.append({"reason": "repository path scan unavailable"})
        repo_paths = []

    hits = {}
    for item in entries:
        matched = {}
        for pattern in item["patterns"]:
            for path in repo_paths:
                if paths_mod.match_path(pattern, path):
                    matched.setdefault(path, set()).add(pattern)
        hits[item["path"]] = matched

    witnessed, potential = [], []
    for index, left in enumerate(entries):
        for right in entries[index + 1:]:
            pair = [left["path"], right["path"]]
            shared = sorted(set(hits[left["path"]]) & set(hits[right["path"]]))
            if shared:
                pairs = sorted({tuple(sorted((sorted(hits[left["path"]][path])[0],
                                              sorted(hits[right["path"]][path])[0])))
                                for path in shared})
                witnessed.append({
                    "pair": pair,
                    "patterns": [[a, b] for a, b in pairs],
                    "witnesses": shared,
                    "class": "witnessed",
                    "label": "已证实交集",
                })
                continue
            unexcluded = [[a, b] for a in left["patterns"] for b in right["patterns"]
                          if not paths_mod.provably_disjoint(a, b)]
            if not unexcluded:
                continue     # 全部模式组合可证不相交 → 不进比对候选
            potential.append({
                "pair": pair,
                "unexcluded": unexcluded,
                "basis": "前缀检查不能排除、无当前路径见证",
                "class": "potential",
                "label": "待核实的潜在交集",
            })

    return {
        "witnessed": witnessed,
        "potential": potential,
        "unverified": unverified,
        "counts": {"witnessed": len(witnessed), "potential": len(potential),
                   "candidates": len(witnessed) + len(potential),
                   "unexpanded": 0},
        "scan": {"spec_files": len(entries) + len(unverified), "repo_paths_scanned": len(repo_paths)},
    }


def _author_order(root):
    """`author` 复核顺序（机制稿 §8.5 知识治理清单）：`extracted` 前置、`author=ai` 优先。

    只给**顺序与依据**，不判「该不该复核」——那是人按正文与证据决定。
    """
    from . import spec as spec_mod

    queue = []
    for entry in spec_mod.all_specs(root):
        problems = list(entry.get("problems") or []) + list(entry.get("path_problems") or [])
        if problems or (entry.get("metadata") or {}).get("status") != "active":
            continue
        metadata = entry.get("metadata") or {}
        verified = metadata.get("verified_at")
        extracted = verified in (None, "extracted")
        author = metadata.get("author")
        reasons = []
        if extracted:
            reasons.append("extracted" if verified == "extracted" else "verified_at 缺失")
        if author == "ai":
            reasons.append("author=ai")
        queue.append((0 if extracted else 1, 0 if author == "ai" else 1,
                      entry.get("path") or "", {
                          "path": entry.get("path"),
                          "author": author,
                          "verified_at": verified,
                          "reason": " 且 ".join(reasons) if reasons else "已核实的 human 结论",
                      }))
    queue.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in queue]


def _out_of_scope_duplicates(root):
    """知识拒绝项的重复登记核对（机制稿 §8.4：同 concept 多文件由巡检报重复）。

    一概念一文件；重提只追加 `## 既往请求`，不新建文件。出现多份即**报重复登记**，
    由人合并或删除——不自动取舍（哪一份是权威是判断，不是事实）。
    读不出/无 concept 的文件单列 `unverified`：未知不当零。
    """
    from . import spec as spec_mod

    directory = join(root, ".wf/out-of-scope")
    if not os.path.isdir(directory):
        return {"duplicates": [], "unverified": [], "files": 0}
    by_concept = {}
    unverified = []
    files = 0
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        relative = f".wf/out-of-scope/{name}"
        try:
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                metadata, problems = spec_mod.parse_frontmatter_text(handle.read())
        except OSError as exc:
            unverified.append({"path": relative, "reason": f"unreadable: {exc}"})
            continue
        files += 1
        concept = metadata.get("concept")
        if problems or not isinstance(concept, str) or not concept:
            unverified.append({"path": relative,
                               "reason": "frontmatter unparsable or concept missing",
                               "problems": problems})
            continue
        by_concept.setdefault(concept, []).append(relative)
    duplicates = [{"concept": concept, "files": sorted(paths)}
                  for concept, paths in sorted(by_concept.items()) if len(paths) > 1]
    return {"duplicates": duplicates, "unverified": unverified, "files": files}


def _governance_summary(root, tasks, archived):
    """巡检治理面（设计稿 §6.2 回收、机制稿 §8.4 周期触发）。

    原则：**未知不当零**。样本不足、样本缺清单、条目不可解析、配置非法、改名/合并无法映射，
    一律只报 unknown 并**不再给出候选或触发结论**，避免"带着错误结论去人工回收"。
    """
    from . import config as config_mod

    project_config, problems = config_mod.load_project_config(root, allow_missing=True)
    window, window_problem = config_mod.value_of(project_config, problems, "spec_reclaim_tasks")
    every, every_problem = config_mod.value_of(project_config, problems, "inspection_every_tasks")

    # 归档事实的完整性前置：status=archived、terminal 合法、archived_at 可解析且可排序
    normal, abnormal = [], []
    incomplete = []
    for path, task in tasks:
        rel = os.path.relpath(path, str(root)).replace(os.sep, "/")
        if not rel.startswith(".wf/tasks/archive/"):
            continue
        task_id = str(task.get("id") or "")
        terminal = task.get("terminal")
        status = task.get("status")
        archived_at = task.get("archived_at")
        if status != "archived":
            incomplete.append({"task": task_id, "reason": "archived record is not status=archived",
                               "status": status})
            continue
        if terminal not in ("normal", "abnormal"):
            incomplete.append({"task": task_id, "reason": "archived record lacks a legal terminal",
                               "terminal": terminal})
            continue
        stamp = _parse_stamp(archived_at)
        if stamp is None:
            incomplete.append({"task": task_id, "reason": "archived_at missing or unparsable",
                               "archived_at": archived_at})
            continue
        record = (stamp, task_id, task)
        (normal if terminal == "normal" else abnormal).append(record)

    normal.sort(key=lambda item: (item[0], item[1]))
    recent = normal[-window:] if window else []
    active_tasks = [task for _path, task in tasks
                    if task.get("status") != "archived" and not task.get("terminal")]

    def curated(task):
        """完整策展清单：缺字段或非列表返回 None（不能当零）。"""
        entries = task.get("curation")
        return entries if isinstance(entries, list) else None

    def entry_path(entry):
        """只接受对象条目；非对象或不可解析返回 None（由调用方记 unknown）。"""
        if not isinstance(entry, dict):
            return None
        path = entry.get("path")
        return path if isinstance(path, str) and path else None

    unknown = []

    # 归档记录不完整：样本不可信，候选与触发都不成立
    for item in incomplete:
        unknown.append(dict(item, reason=f"archive record incomplete: {item['reason']}"))

    # 配置非法：不再计算依赖它的结论（设计稿 §3）
    if window_problem:
        unknown.append({"reason": "invalid spec_reclaim_tasks", "detail": window_problem})
    if every_problem:
        unknown.append({"reason": "invalid inspection_every_tasks", "detail": every_problem})

    # 活动任务同样纳入「未知压制候选」：依赖优先保护，不能把"读不出"当成"没依赖"
    active_refs = set()
    for task in active_tasks:
        entries = curated(task)
        task_label = task.get("id")
        if entries is None:
            unknown.append({"reason": "active task lacks curation list", "task": task_label})
            continue
        for entry in entries:
            path = entry_path(entry)
            if path is None:
                unknown.append({"reason": "active task curation entry unparsable", "task": task_label})
                continue
            if not (isinstance(entry, dict) and entry.get("released")):
                active_refs.add(path)

    if window and len(normal) < window:
        unknown.append({"reason": "not enough normal-archived samples",
                        "have": len(normal), "window": window})
    for _at, task_id, task in recent:
        entries = curated(task)
        if entries is None:
            unknown.append({"reason": "sample lacks curation list", "task": task_id})
            continue
        bad = [entry for entry in entries if entry_path(entry) is None and entry is not None]
        if bad:
            unknown.append({"reason": "sample curation entry unparsable", "task": task_id,
                            "entries": len(bad)})

    referenced_recently = set()
    for _at, _task_id, task in recent:
        for entry in curated(task) or []:
            path = entry_path(entry)
            if path:
                referenced_recently.add(path)

    existing = set(_spec_paths(root))
    # 改名/合并：样本或活动任务引用过、但现在已不存在的 spec 路径无法可靠映射 → unknown
    vanished = sorted({path for path in (referenced_recently | active_refs) if path not in existing})
    for path in vanished:
        unknown.append({"reason": "curation path no longer exists; rename/merge mapping unverifiable",
                        "path": path})

    # 有任何未知就不给候选：候选只在"窗口完整且可解释"时成立
    candidates = []
    if not unknown:
        for path in sorted(existing):
            if path in active_refs or path in referenced_recently:
                continue
            candidates.append({"path": path, "reason": "unreferenced in recent normal archives"})

    due = None
    # 到点判定只看**让「正常归档累计」变不可信**的因素：归档记录不完整、配置键非法。
    # 知识回收窗口的样本不足/路径失联属 `spec_usage` 的未知，不改变归档计数（机制稿 §8.5
    # 的触发只依赖正常归档累计；§2.3.11 的未知纪律针对「归档记录事实不完整」）。
    # 此前把整张 `unknown` 列表都算进来，会让一个年轻项目的巡检永远不到点——与机制稿相反。
    count_unreliable = bool(incomplete) or bool(every_problem)
    if not count_unreliable and every:
        due = bool(len(normal) and len(normal) % every == 0)

    return {
        "archive_terminals": {"problems": _archive_terminal_problems(root, tasks)},
        "archive_references": _archive_reference_summary(root, tasks),
        "spec_usage": {
            "reclaim_threshold": window,
            "window_samples": [task_id for _at, task_id, _task in recent],
            "reclaim_candidates": candidates,
            "unknown": unknown,
            "problem": window_problem,
            "statistic_complete": not unknown,
        },
        # 两级治理输出（机制稿 §8.5）：只给事实与分类，语义矛盾交人对照正文。
        "manual_compare": _manual_compare(root),
        "author_order": _author_order(root),
        "out_of_scope_duplicates": _out_of_scope_duplicates(root),
        "inspection": {
            "every_tasks": every,
            "normal_archived": len(normal),
            "abnormal_archived": len(abnormal),
            "due": due,
            "problem": every_problem,
        },
        # 机制稿 §8.5：**四类各自 passed/failed/unknown 及未覆盖对象**，不能只给知识统计就称巡检通过。
        # 三类结论的判定口径（脚本只核结构）：结构探针跑通且未发现处置项 = passed；
        # 发现需处置/待核对项 = failed；样本不足、条目不可解析、声明缺失 = unknown（不当作 0）。
        "four_class_verdicts": _four_class_verdicts(
            tasks,
            archive_terminals=_archive_terminal_problems(root, tasks),
            archive_references=_archive_reference_summary(root, tasks),
            spec_usage={"unknown": unknown, "problem": window_problem,
                        "statistic_complete": not unknown},
            incomplete=incomplete,
            every_problem=every_problem,
            manual_compare=_manual_compare(root),
            author_order=_author_order(root),
            out_of_scope_duplicates=_out_of_scope_duplicates(root),
        ),
    }


def _four_class_verdicts(tasks, *, archive_terminals, archive_references, spec_usage,
                         incomplete, every_problem, manual_compare, author_order,
                         out_of_scope_duplicates):
    """四类断言各自的三态结论（机制稿 §8.5）与「未覆盖对象」清单。

    四类＝归档引用 / 归档终态 / 归档 id / 知识（设计稿 §5.4）。每条结论**必须带事实**，
    `unknown` 不等于通过——只要有一类是 unknown，整体就不能称"巡检通过"。
    """
    def verdict(kind, failed, unknown_items):
        if unknown_items:
            status = "unknown"
        elif failed:
            status = "failed"
        else:
            status = "passed"
        return {"class": kind, "status": status, "failed": failed, "unknown": unknown_items}

    # `_archive_terminal_problems` 直接返回条目列表
    terminal_failed = list(archive_terminals or [])
    terminal_unknown = [item for item in incomplete
                        if item.get("reason", "").startswith("archived record lacks")]
    id_failed = [item for item in incomplete if item.get("reason") == "archived record is not status=archived"]
    stamp_unknown = [item for item in incomplete
                     if item in terminal_unknown or item.get("reason") == "archived_at missing or unparsable"]
    reference_failed = list(archive_references.get("dangling") or [])
    reference_unknown = list(archive_references.get("unknown") or [])
    # 三个治理输出直接以条目列表返回（`unverified`/重复项各在其内），这里只按事实分类：
    # 有「未核实/重复/非法」条目即 failed，不把它们降级成通过。
    knowledge_failed = ([] if spec_usage.get("statistic_complete")
                        else list(spec_usage.get("unknown") or []))
    knowledge_failed = knowledge_failed + list(manual_compare or []) \
        + list(author_order or []) + list(out_of_scope_duplicates or [])
    knowledge_unknown = []
    if spec_usage.get("problem") or every_problem:
        knowledge_unknown = [spec_usage.get("problem") or every_problem]
    verdicts = [
        verdict("archive_references", reference_failed, reference_unknown),
        verdict("archive_terminals", terminal_failed, stamp_unknown),
        verdict("archive_ids", id_failed, []),
        verdict("knowledge", knowledge_failed, knowledge_unknown),
    ]
    uncovered = [item for entry in verdicts for item in entry["failed"] + entry["unknown"]]
    return {
        "verdicts": verdicts,
        "uncovered": uncovered,
        "overall": ("failed" if any(entry["status"] == "failed" for entry in verdicts)
                    else "unknown" if any(entry["status"] == "unknown" for entry in verdicts)
                    else "passed"),
        "note": "unknown 不等于通过；本结论只核结构，语义矛盾交人对照正文",
    }


def _parse_stamp(value):
    """把 archived_at 解析成可排序的 datetime；缺失或不可解析返回 None。"""
    import datetime

    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    return stamp


TASK_REF_FIELDS = ("prerequisites", "rework_of", "successor_id")
SECOND_ROUND_REF_FIELDS = ("run_id", "instance_id", "independent_resume")


def _dangling_archive_refs(root, tasks):
    """引用悬空：活动与归档记录都扫（机制稿 §8.5 归档引用类）；第二轮字段给 unknown 不当通过。"""
    known_tasks = {task.get("id") for _path, task in tasks if task.get("id")}
    problems, unknown = [], []
    for path, task in tasks:
        rel = os.path.relpath(path, str(root)).replace(os.sep, "/")
        for field in TASK_REF_FIELDS:
            value = task.get(field)
            if not value:
                continue
            for ref in (value if isinstance(value, list) else [value]):
                if ref and ref not in known_tasks:
                    problems.append({"path": rel, "field": field, "ref": ref,
                                     "reason": "referenced task is not in the archive/active view"})
        for field in SECOND_ROUND_REF_FIELDS:
            if task.get(field):
                unknown.append({"path": rel, "field": field,
                                "reason": "instance/run tables land in round 2; cannot verify"})
    return problems, unknown


def _archive_reference_summary(root, tasks):
    dangling, unknown = _dangling_archive_refs(root, tasks)
    return {"dangling": dangling, "unknown": unknown,
            "status": "failed" if dangling else ("unknown" if unknown else "passed")}


def _spec_paths(root):
    from . import spec as spec_mod

    directory = os.path.join(str(root), ".wf", "spec")
    if not os.path.isdir(directory):
        return []
    found = []
    for base, _dirs, files in os.walk(directory):
        for name in files:
            if name.endswith(".md"):
                found.append(os.path.relpath(os.path.join(base, name), str(root)).replace(os.sep, "/"))
    return found


def _archive_terminal_problems(root, tasks):
    problems = []
    for path, task in tasks:
        rel = os.path.relpath(path, str(root)).replace(os.sep, "/")
        if not rel.startswith(".wf/tasks/archive/"):
            continue
        name = os.path.basename(str(path).rstrip("/"))  # iter_tasks 给的是任务目录本身
        # 三类问题各自独立报：写成 elif 链时，目录名不符会把"记录未提交/未持久化"
        # 一并掩掉，处置项在巡检里看不见。
        if task.get("terminal") not in ("normal", "abnormal"):
            problems.append({"path": rel, "kind": "terminal-missing",
                             "reason": "terminal not recorded",
                             "terminal": task.get("terminal")})
        # 两类失配要能分开消费：拿目录名当 id（`carries_id` 出口）与记录 id 无对应目录
        # （本节）。此前都只剩一句自由文本 reason，巡检输出无法按类筛选。
        if not name.startswith(str(task.get("id"))):
            problems.append({"path": rel, "kind": "dir-name-mismatch",
                             "reason": "record id does not match directory name",
                             "record_id": task.get("id"), "dir_name": name})
        if task.get("terminal") == "abnormal":
            # 异常归档用 _record_committed（记录已入提交且无未提交差异），与 archive_persisted 判据不同
            if not _record_committed(root, rel):
                problems.append({"path": rel, "reason": "abnormal archive record is not committed"})
        elif task.get("terminal") == "normal":
            # 终态未记录时不再跑持久化核对：判据依赖 terminal，缺了只会叠一条推断结果。
            persisted = archive_persisted(root, task)
            if not persisted.get("persisted"):
                problems.append({"path": rel, "reason": "archive record is not persisted",
                                 "detail": persisted.get("reason")})
    return problems


def _spec_summary(root):
    from . import spec as spec_mod

    directory = join(root, ".wf/spec")
    if not os.path.isdir(directory):
        return {"files": 0, "unparsed": []}
    entries, unparsed = [], []
    for base, _dirs, files in os.walk(directory):
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(base, name)
            metadata, problems = spec_mod.parse_frontmatter(path)
            if problems:
                unparsed.append(os.path.relpath(path, str(root)).replace(os.sep, "/"))
                continue
            entries.append({"path": os.path.relpath(path, str(root)).replace(os.sep, "/"),
                            "status": metadata.get("status")})
    return {"files": len(entries), "unparsed": unparsed,
            "active": len([item for item in entries if item.get("status") == "active"])}
