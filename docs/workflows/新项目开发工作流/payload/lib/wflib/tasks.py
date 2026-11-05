"""tasks.py — 任务记录、状态迁移与人判输入落点（机制稿 §1.3、§2.2、§2.3、§5.3、§6.4）。"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid

from . import actions, codes, config, fingerprint, records, scope, session as session_mod, writer as writer_mod
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
    cleaned = re.sub(r"[^\w\-]+", "-", title.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned[:48] or "task"


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


def locate_task_dirs(root, task_id):
    """完整 id 的全部匹配位置（活动区 + 归档区），供冲突诊断与定位使用。"""
    active, archived = _task_dirs(root)
    matches = []
    for path in active + archived:
        name = os.path.basename(path)
        if name == task_id or name.startswith(task_id + "-"):
            matches.append(path)
            continue
        if name.startswith(task_id):
            record = records.load_json(os.path.join(path, "task.json"))
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
        raise records.RecordInvalid(
            f"task record {os.path.basename(path)} carries id {task.get('id')!r}, expected {task_id!r}"
        )
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
        "execution": {"required_steps": [], "actions": [], "human_decisions": [], "debug_declarations": []},
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


def read_prd(root, task):
    path = task_dir(root, task.get("id"))
    if not path:
        return None
    try:
        with open(os.path.join(path, "prd.md"), "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


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
    subjects = [str(decision.get("subject", "")) for decision in decisions]
    return [question for question in plan_questions(root, task)
            if not any(question in subject for subject in subjects)]




MECHANICAL_REVISION = "机械修订"
APPROVE_CHOICES = ("approve", "批准")
# 设计稿 §4.3 的四个分级条件；机制稿 §2.3 要求逐项保存 true/false/unknown
# 键名与批准入口的 complexity_conditions 一致（设计稿 §4.3 四项）
COMPLEXITY_CONDITIONS = ("governance", "contract", "acceptance", "scope")


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


def artifact_digests(root, task):
    path = task_dir(root, task.get("id"))
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
        if not lower or not wanted or not operation:
            return False
        if not scope.is_ancestor(root, lower):
            return False
        for sha in scope.commits_since(root, lower) or []:
            # 回执本身须在该提交里（不要求与其他路径同一次 diff）
            blob = _committed_text(root, sha, ".wf/writer.json")
            if blob is None:
                continue
            try:
                committed = json.loads(blob)
            except ValueError:
                continue
            matched = None
            for saved in committed.get("maintenance_results") or []:
                if isinstance(saved, dict) and saved.get("operation") == operation:
                    matched = saved
                    break
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
        if kind == "transfer":
            target = disposition.get("target_task")
            task = load_task(root, target) if target else None
            if not isinstance(task, dict):
                return False
            approval = (task.get("plan") or {}).get("approval")
            # 已批准须是**有效批准对象**：非空对象 + 决策 + 规划版本，不能用"非 null"代替
            if not isinstance(approval, dict) or not approval:
                return False
            if not approval.get("decision") or not (task.get("plan") or {}).get("version"):
                return False
            touch = (task.get("plan") or {}).get("touch_paths") or []
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
    ("graph", "对象与依赖"),
    ("workspace", "工作区边界"),
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
    if task is not None:
        blockers = dependency_blockers(ctx.root, task)
        findings.append({"step": "graph", "status": "blocked" if blockers else "ok", "unmet": blockers})
        # 机制稿 §5.3 还要求「启动校验通过后」触发空集合复评；首轮只在 archive 侧调用，
        # 这里先留可核事实，第二轮补返工时连启动侧触发一起接上（登记见综合记录）。
        reassessment = _reassess_empty_set(ctx, task.get("id"))
        if reassessment.get("empty"):
            findings.append({"step": "graph", "status": "unknown", "reason": "empty retrospective set pending reassessment",
                             "reassessment": reassessment})
        from . import cli as cli_mod

        foreign = cli_mod.wip_blockers(ctx.root, exclude_id=task.get("id"))
        findings.append({"step": "workspace", "status": "blocked" if foreign else "ok", "blocking": foreign})
    else:
        findings.append({"step": "graph", "status": "unknown", "reason": "no bound object"})
        findings.append({"step": "workspace", "status": "unknown", "reason": "no bound object"})
    order = {name: index for index, (name, _label) in enumerate(STARTUP_STEPS)}
    return sorted(findings, key=lambda item: order.get(item["step"], 99))


def work_satisfied_fact(ctx, task):
    entry = task.get("entry_snapshot") or {}
    touch_paths = entry.get("touch_paths") or []
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


def changes_persisted_fact(ctx, task):
    receipts = task_receipts(ctx.root)
    classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
    pending = sorted(set(classified["buckets"]["e"]) & set(scope.uncommitted_paths(ctx.root)))
    if not pending:
        return True, None, {"paths": []}
    grants = task.get("commit_grants") or []
    if not grants:
        return False, "WF_COMMIT_NOT_AUTHORIZED", {"pending_paths": pending}
    return False, "WF_WIP_UNRESOLVED", {"pending_paths": pending, "grants": len(grants)}


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


def _resume_task_create(ctx, key, session, pending):
    """按原意图补完 task.create：索取写权 → 补绑定/运行态 → 结案，返回同一任务。"""
    from . import cli, session as session_mod, writer as writer_mod

    directory, task = pending
    task_id = task.get("id")
    record = ctx.writer()
    holder = record.get("holder") or {}
    if record.get("state") != "held" or holder.get("id") != key:
        owner_scope = {"object": {"kind": "task", "id": task_id}, "preparation": None}
        record = writer_mod.acquire(record, kind="session", ident=key, scope=owner_scope,
                                    checkpoint={"step": "task-new:resume", "at": records.now_str()})
        writer_mod.save(ctx.root, record)
    # R50-06：恢复不是"把 state 改成 done"，逐项核后置
    if not os.path.isdir(directory):
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"reason": "task directory missing during resume", "directory": directory},
                        next_="按原意图重建目录与产物，或走受控恢复")
    prd_path = os.path.join(directory, "prd.md")
    if not os.path.isfile(prd_path):
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"reason": "template artifact missing during resume", "path": prd_path},
                        next_="补齐模板产物后再续做")
    existing = session_mod.load_binding(ctx.root, key)
    if existing:
        # 恢复不是特权通道：已有绑定就要过同一套实例核验（缺失/不符一律拒绝）
        _require_instance_match(ctx, existing)
        if (existing.get("object") or {}).get("id") != task_id:
            raise TaskError("WF_BINDING_MISMATCH",
                            {"bound": existing.get("object"), "intended": task_id},
                            next_="按原意图续做同一对象；不改绑")
        instance_id = existing.get("instance_id")
        runtime = records.load_json(session_mod.runtime_path(ctx.root, key), None)
        if runtime is None:
            # 缓存缺失属可重建项：重建并留痕，不静默跳过（机制稿 §1.4）
            session_mod.write_runtime(ctx.root, key, {
                "binding_digest": records.plain_digest(existing),
                "instance_id": instance_id,
                "object": {"kind": "task", "id": task_id},
                "current_task": task_id,
                "cursor": None,
            })
    else:
        instance_id = session.get("instance_id") or session_mod.new_instance_id()
        binding = {
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
        session_mod.save_binding(ctx.root, key, binding)
        session_mod.write_runtime(ctx.root, key, {
            "binding_digest": records.plain_digest(binding),
            "instance_id": instance_id,
            "object": {"kind": "task", "id": task_id},
            "current_task": task_id,
            "cursor": None,
        })
    holder = record.get("holder") or {}
    task, assertion = _finish_task_action(
        ctx, directory, task, "task.create", holder,
        {"task": task_id, "kind": task.get("kind"), "title": task.get("title")}, task.get("action") or {},
        evidence_refs=[os.path.relpath(directory, str(ctx.root))],
    )
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_="起草 PRD 机读块，然后由人批准规划（task-approve）",
        facts={"task_id": task_id, "directory": os.path.relpath(directory, str(ctx.root)).replace(os.sep, "/"),
               "kind": task.get("kind"), "generation": record.get("generation"),
               "instance_id": instance_id, "resumed": True,
               "control_assertion": assertion},
    )


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
        raise TaskError("WF_PATH_INVALID", {"reason": "task-new requires --title"})
    if not template:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-new requires --template <tasks template dir>"})
    session = ctx.session()
    key = ctx.key()
    code, profile_facts = session_mod.check_platforms(ctx.platforms(), session)
    if code:
        raise cli.CliError(code, profile_facts, next_="install --platform <当前宿主> 后重试")
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
            bound_object = (bound.get("object") or {}).get("id")
            bound_task = load_task(ctx.root, bound_object) if bound_object else None
            if isinstance(bound_task, dict):
                # 响应丢失的重试：已完成则返回原结果，不产生第二个任务
                return codes.result(
                    "WF_OK",
                    object={"id": bound_object, "name": bound_task.get("title")},
                    position_=codes.position(scope="task", phase=bound_task.get("phase"),
                                             task_id=bound_object),
                    next_="继续当前对象（本条为重试返回的原结果）",
                    facts={"task_id": bound_object,
                           "directory": os.path.relpath(task_dir(ctx.root, bound_object), str(ctx.root)).replace(os.sep, "/")
                           if task_dir(ctx.root, bound_object) else None,
                           "kind": bound_task.get("kind"),
                           "already_completed": True,
                           "instance_id": bound.get("instance_id")},
                )
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "session already bound"},
                            next_="原对象结束后由新会话选择下一对象")
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
        elif (binding.get("object") or {}).get("id") != task_id:
            raise TaskError("WF_BINDING_MISMATCH",
                            {"bound": binding.get("object"), "intended": task_id},
                            next_="按原意图续做同一对象；不改绑")
        if not session_mod.write_runtime(ctx.root, key, {
            "binding_digest": records.plain_digest(binding),
            "instance_id": binding.get("instance_id"),
            "object": {"kind": "task", "id": task_id},
            "current_task": task_id,
            "cursor": None,
        }):
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
    """汇总四项条件后再给提议：任一 true/unknown 即提出 complex（机制稿 §1.3、设计稿 §4.3）。"""
    reasons = []
    value, fact = scope.governance_condition(ctx.root, block.get("touch_paths") or [])
    if value in ("true", "unknown"):
        reason = dict(fact)
        reason["condition"] = "governance"
        reason["value"] = value
        reason["fact"] = fact.get("fact")
        reasons.append(reason)
    extra = extra_conditions or {}
    for condition in COMPLEXITY_CONDITIONS:
        if condition == "governance":
            continue
        entry = extra.get(condition)
        if isinstance(entry, dict) and entry.get("value") in ("true", "unknown"):
            reasons.append({"condition": condition, "value": entry["value"], "fact": entry.get("fact", "")})
    proposed = "complex" if reasons else "light"
    return proposed, reasons


def cmd_task_approve(ctx, args):
    from . import cli, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id or not decision_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-approve requires --task <id> --decision <path>"})
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
        prd_text = _prd_text(ctx.root, task)
        approvals = [item for item in decisions if item.get("choice") in APPROVE_CHOICES]
        if not approvals:
            raise TaskError("WF_SEMANTIC_DECISION",
                            {"reason": "no approval decision", "choices": [item.get("choice") for item in decisions],
                             "accepted": list(APPROVE_CHOICES)},
                            next_="用 choice=approve 的决定重新批准")
        approval = approvals[0]
        prd_digest = "sha256:" + records.sha256_hex(prd_text.encode("utf-8"))
        if approval.get("object_digest") and approval.get("object_digest") != prd_digest:
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision does not cover the current PRD",
                             "decision_digest": approval.get("object_digest"), "current_digest": prd_digest},
                            next_="针对当前 PRD 重新出批准决定")
        subject = str(approval.get("subject") or "")
        if subject and task_id not in subject and approval.get("object_digest") != prd_digest:
            raise TaskError("WF_APPROVAL_MISSING",
                            {"reason": "approval decision subject does not name the task", "subject": subject},
                            next_="在 subject 记任务 id 或当前 PRD 摘要")
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
        complexity = inputs.get("complexity") or proposed
        if complexity not in ("light", "complex"):
            raise TaskError("WF_PATH_INVALID", {"reason": "inputs.complexity must be light|complex"})
        downgrade_entry = None
        if complexity == "light" and proposed == "complex":
            downgrade = inputs.get("downgrade") or {}
            if not downgrade.get("reason") or not downgrade.get("evidence"):
                raise TaskError(
                    "WF_SEMANTIC_DECISION",
                    {"reason": "complexity condition requires complex", "condition": reasons,
                     "downgrade_required": ["reason", "evidence"]},
                )
            # 降级条目属批准后追加事实，不进 plan 版本哈希域（机制稿 §1.1）
            downgrade_entry = {"downgrade": True, "reason": downgrade["reason"], "evidence": downgrade["evidence"]}
        artifact_problems = complex_artifact_problems(ctx.root, task, complexity)
        if artifact_problems:
            raise TaskError("WF_TEMPLATE_INCOMPLETE",
                            {"reason": "complex task requires complete design/implement",
                             "complexity": complexity, "artifacts": artifact_problems},
                            next_="补齐 design.md / implement.md 并填写必填占位后重新批准")
        tdd = inputs.get("tdd")
        if tdd is None:
            project_config, config_problems = config.load_project_config(ctx.root, allow_missing=True)
            tdd, tdd_problem = config.value_of(project_config, config_problems, "tdd_default")
            if tdd_problem:
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": tdd_problem, "key": "tdd_default"},
                                next_="修正 project-config.json 的该键，或显式传 inputs.tdd")
            if tdd is None:
                tdd = config.DEFAULTS["tdd_default"]
        if not isinstance(tdd, bool):
            raise TaskError("WF_PATH_INVALID", {"reason": "inputs.tdd must be boolean"})
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
        })
        task["plan"] = plan
        execution = task.setdefault("execution", {})
        human = execution.setdefault("human_decisions", [])
        for decision in decisions:
            if decision is not approval:
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
            "tdd": tdd,
            "touch_paths": block["touch_paths"],
            "acceptance_digest": plan["acceptance_digest"],
            "verifications": [item.get("id") for item in block["verifications"]],
            "control_assertion": assertion,
            # P2-5：配置了复评提示键就让它们真的出现（提醒复评复杂度，不自动分类）
            "complexity_hints": _complexity_hints(ctx.root),
        },
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
    from . import check as check_mod

    results = []
    for verification in (task.get("plan") or {}).get("verifications") or []:
        if verification.get("consume_at") != "start":
            continue
        invocation = verification.get("invocation") or {}
        ready, reason = check_mod._argv_ready(ctx.root, invocation)
        if not ready:
            raise TaskError("WF_VERIFICATION_UNREADY", {"verification_id": verification.get("id"), "reason": reason})
        cwd = verification.get("cwd") or "."
        workdir = ctx.root if cwd == "." else join(ctx.root, cwd)
        argv = list(invocation.get("argv") or [])
        result = subprocess.run(argv, cwd=workdir, capture_output=True, text=True, check=False)
        results.append({"verification_id": verification.get("id"), "exit_code": result.returncode})
        if result.returncode != 0:
            raise TaskError(
                "WF_CHECK_FAILED",
                {"verification_id": verification.get("id"), "exit_code": result.returncode,
                 "output": (result.stdout or "")[-800:] + (result.stderr or "")[-800:]},
            )
    return results




def _block_overlapping_maintenance(ctx, task):
    """与本次请求范围重叠的未结维护组阻断开工（机制稿 §4.5、§5.2 第⑩项）。"""
    from . import paths as paths_mod

    # 走统一读取：含可达提交查证，已提交的维护组自动派生 persisted（机制稿 §4.5）
    receipts = task_receipts(ctx.root)
    requested = (task.get("entry_snapshot") or {}).get("touch_paths") or (task.get("plan") or {}).get("touch_paths") or []
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
    prd_text = _prd_text(ctx.root, task)
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
    if sorted(touch_paths) != sorted(plan.get("touch_paths") or []) or acceptance != plan.get("acceptance_digest"):
        raise TaskError("WF_SEMANTIC_DECISION",
                        {"reason": "触碰面或验收发生变化，不属机械修订；回 Plan 重新批准",
                         "approved_touch_paths": plan.get("touch_paths"),
                         "current_touch_paths": touch_paths,
                         "approved_acceptance_digest": plan.get("acceptance_digest"),
                         "current_acceptance_digest": acceptance})
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


def cmd_task_start(ctx, args):
    from . import cli, gates, lock

    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-start requires --task <id>"})
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
            raise TaskError("WF_APPROVAL_MISSING", {"approved": (task.get("plan") or {}).get("version"),
                                                   "current": current.get("version")})
        if task.get("kind") == "ordinary":
            config_record, problems = config.load_project_config(ctx.root, allow_missing=True)
            if config_record is None:
                raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"missing": ".wf/project-config.json",
                                                             "reason": "ordinary task requires project config"})
            if not os.path.exists(join(ctx.root, ".wf/baseline.md")):
                raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"missing": ".wf/baseline.md"})
        if not scope.has_git(ctx.root):
            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "Git HEAD required", "missing": "git HEAD"})
        head = scope.head(ctx.root)
        if not head:
            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "no HEAD commit"})
        _block_overlapping_maintenance(ctx, task)
        start_results = _run_start_verifications(ctx, task)
        findings = gates.evaluate(ctx, task, "before_execute")
        blocking = [item for item in findings if item["status"] == "missing"]
        if blocking:
            raise TaskError(blocking[0]["code"] or "WF_SEMANTIC_DECISION", {"missing": blocking})
        if task.get("kind") == "ordinary":
            receipts = task_receipts(ctx.root)
            classified = scope.classify_candidates(ctx.root, task, receipts=receipts)
            if classified["buckets"]["c"]:
                raise TaskError("WF_WORKSPACE_UNRESOLVED", {"other_tasks": classified["buckets"]["c"]})
            if classified["buckets"]["f"]:
                raise TaskError("WF_SCOPE_VIOLATION", {"out_of_scope": classified["buckets"]["f"]})
        # P2-3：执行候选唯一性对全部 kind 生效（initialize/bootstrap 也不能与别的执行同时存在）
        others = [
            other for _path, other in iter_tasks(ctx.root)
            if other.get("id") != task_id
            and other.get("status") == "in_progress"
            and not other.get("paused") and not other.get("suspended")
        ]
        if others:
            raise TaskError("WF_RECORD_INVALID", {"other_candidates": [item.get("id") for item in others]})
        entry = {
            "plan_version": (task.get("plan") or {}).get("version"),
            "approval_ref": records.plain_digest((task.get("plan") or {}).get("approval")),
            "prd_digest": records.file_digest(join(path, "prd.md")),
            "touch_paths": (task.get("plan") or {}).get("touch_paths") or [],
            "head_at_entry": head,
            "entered_at": records.now_str(),
        }
        task["entry_snapshot"] = entry
        if task.get("status") == "not_started":
            task["baseline_head"] = head
        task["status"] = "in_progress"
        task["phase"] = "execute"
        task, action = _start_task_action(
            ctx, path, task, "task.transition", holder,
            {"task": task_id, "to": "execute", "plan_version": entry["plan_version"]},
            ["verify_approval", "resolve_start_verifications", "write_entry_snapshot", "transition"],
        )
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
        task, assertion = _finish_task_action(
            ctx, path, task, "task.transition", holder,
            {"task": task_id, "to": "execute", "plan_version": entry["plan_version"]}, action,
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


def cmd_task_replan(ctx, args):
    from . import lock

    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-replan requires --task <id>"})
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-replan"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") == "archived":
            raise TaskError("WF_BINDING_MISMATCH", {"reason": "task archived"})
        task["phase"] = "plan"
        task, action = _start_task_action(ctx, path, task, "task.transition", holder,
                                          {"task": task_id, "to": "plan"}, ["invalidate", "transition"])
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
        raise TaskError("WF_PATH_INVALID", {"reason": "task-pause requires --task <id>"})
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
        raise TaskError("WF_PATH_INVALID", {"reason": "task-resume requires --task <id>"})
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


def _apply_debug_inputs(task, decisions, root=None):
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
            declarations.append({"verification_id": verification_id, "counted": counted,
                                 "evidence_refs": evidence, "dedupe_refs": dedupe})
            continue
        if subject.startswith("debug-ruling-"):
            from . import gates as gates_mod

            if gates_mod.parse_debug_ruling(subject) is None:
                raise TaskError("WF_RECORD_INVALID",
                                {"subject": subject,
                                 "reason": "debug-ruling subject must be debug-ruling-<verification_id>-<multiple>"})
            if decision.get("choice") not in ("同一问题", "不同问题"):
                raise TaskError("WF_SEMANTIC_DECISION", {"subject": subject,
                                                         "reason": "ruling choice must be 同一问题/不同问题"})
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
        raise TaskError("WF_PATH_INVALID", {"reason": "task-curate requires --task --spec --purpose"})
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


def cmd_task_check(ctx, args):
    from . import check as check_mod, cli, gates, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    review_notes = args.value("--review-notes")
    if not task_id:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-check requires --task <id>"})
    decisions = cli._load_decision(decision_path) if decision_path else []
    _require_binding(ctx, task_id)
    with lock.acquire(ctx.root, holder_hint="task-check"):
        _record, holder = ctx.require_held(task=task_id)
        path = task_dir(ctx.root, task_id)
        task = records.load_json(os.path.join(path, "task.json"))
        if task.get("status") != "in_progress":
            raise TaskError("WF_SEMANTIC_DECISION", {"reason": "check requires in_progress", "status": task.get("status")})
        if task.get("paused") or task.get("suspended"):
            raise TaskError("WF_SEMANTIC_DECISION", {"paused": task.get("paused"), "suspended": task.get("suspended")})
        _apply_debug_inputs(task, decisions, ctx.root)
        findings = gates.evaluate(ctx, task, "before_check")
        blocking = [item for item in findings if item["status"] == "missing"]
        if blocking:
            raise TaskError(blocking[0]["code"] or "WF_SEMANTIC_DECISION", {"missing": blocking})
        try:
            check, code, facts = check_mod.run_check(ctx, task, decisions, review_notes)
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
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="人了解结果后调用 finish（wf-finish）",
        facts={"check": check["id"], "anchor": check["anchor"], "object_paths": facts.get("object_paths"),
               "acceptance_results": check["acceptance_results"], "commands": check["commands"],
               "control_assertion": assertion},
    )


def cmd_task_knowledge(ctx, args):
    from . import lock

    task_id = args.value("--task")
    decision = args.value("--decision")
    changes_path = args.value("--changes")
    if not task_id or decision not in ("no-update", "updated"):
        raise TaskError("WF_PATH_INVALID", {"reason": "task-knowledge requires --task <id> --decision no-update|updated"})
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
    decision_path = args.value("--decision")
    if not task_id or not evidence_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-retrospect requires --task <id> --evidence <path>"})
    evidence = records.load_json(evidence_path)
    if evidence is None:
        raise TaskError("WF_PATH_INVALID", {"reason": "evidence file missing", "path": evidence_path})
    decision = None
    if decision_path:
        from . import cli

        decisions = cli._load_decision(decision_path)
        decision = decisions[0]
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
        raise TaskError("WF_PATH_INVALID", {"reason": "task-attribute requires --task <id> --commit <oid>"})
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
    if not record_rel.startswith(".wf/tasks/archive/"):
        # 终态已写但目录未移动：先完成移动
        destination = _archive_destination(ctx.root, task)
        if os.path.exists(destination):
            raise TaskError("WF_TARGET_COLLISION",
                            {"destination": os.path.relpath(destination, str(ctx.root))})
        moved = _move_task(ctx.root, directory, destination)
        task = records.load_json(os.path.join(moved, "task.json"))
        record_rel = os.path.relpath(moved, str(ctx.root)).replace(os.sep, "/")
    if _record_committed(ctx.root, record_rel):
        return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                            facts={"terminal": "abnormal", "record_persisted": True,
                                   "note": "放弃已结案，无需重复"})
    _commit_paths(ctx.root, [record_rel], f"wf: abandon {task_id}\n\nwf-task: {task_id}")
    if not _record_committed(ctx.root, record_rel):
        raise TaskError("WF_PERSISTENCE_FAILED",
                        {"record": record_rel, "reason": "归档记录尚未进入提交"},
                        next_="持写权重入以续做记录提交")
    return codes.result("WF_OK", object={"id": task_id, "name": task.get("title")},
                        facts={"terminal": "abnormal", "record_persisted": True, "resumed_commit": True,
                               "note": "只报告退出完成与保留风险，不报告业务验收通过"})


def cmd_task_abandon(ctx, args):
    from . import cli, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    disposition_path = args.value("--disposition")
    if not task_id or not decision_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-abandon requires --task <id> --decision <path>"})
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
        preview = _abandon_preview(ctx, task)
        if not disposition:
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

        grants = [item for item in decisions[1:] if item.get("choice") == "commit"]
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
        task["commit_grants"] = [item for item in decisions[1:] if item.get("choice") == "commit"]
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
        _move_task(ctx.root, path, destination)
        record_rel = os.path.relpath(destination, str(ctx.root)).replace(os.sep, "/")
        _commit_paths(ctx.root, [record_rel], f"wf: abandon {task_id}\n\nwf-task: {task_id}")
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


def _move_task(root, source, destination):
    if os.path.exists(destination):
        raise TaskError("WF_TARGET_COLLISION", {"destination": os.path.relpath(destination, str(root))})
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.move(source, destination)
    return destination


def _commit_paths(root, paths, message):
    """按精确路径暂存并提交：不捎带索引中的其他内容，提交后回读核对（机制稿 §5.3）。"""
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

    add = git("add", "--", *authorized)
    if add.returncode != 0:
        raise TaskError("WF_PERSISTENCE_FAILED", {"command": "git add", "stderr": add.stderr[-500:]})
    staged = git("status", "--porcelain", "--", *authorized)
    if staged.returncode == 0 and not staged.stdout.strip():
        return {"committed": True, "already_clean": True, "paths": authorized, "head": scope.head(root)}
    commit = git("commit", "-m", message, "--", *authorized)
    if commit.returncode != 0:
        raise TaskError("WF_PERSISTENCE_FAILED", {"command": "git commit", "stderr": commit.stderr[-500:],
                                                  "stdout": commit.stdout[-500:]})
    shown = git("show", "--name-only", "--format=", "HEAD")
    committed = [line.strip() for line in shown.stdout.splitlines() if line.strip()]
    extra = [path for path in committed
             if not any(path == item or path.startswith(item + "/") or paths_mod.match_path(item, path)
                        for item in authorized)]
    if extra:
        raise TaskError("WF_COMMIT_NOT_AUTHORIZED",
                        {"reason": "提交包含授权路径之外的内容", "extra": extra, "authorized": authorized})
    return {"committed": True, "paths": committed, "head": scope.head(root)}






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


def cmd_archive(ctx, args):
    from . import cli, gates, lock

    task_id = args.value("--task")
    decision_path = args.value("--decision")
    if not task_id or not decision_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "archive requires --task <id> --decision <path>"})
    decisions = cli._load_decision(decision_path)
    finish = [item for item in decisions if item.get("choice") in ("finish", "完成", "pass")]
    grants = [item for item in decisions if item.get("choice") == "commit"]
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
            if current_dir and not rel_now.startswith(".wf/tasks/archive/"):
                _record, _holder = ctx.require_held(task=task_id)
                destination = _archive_destination(ctx.root, task)
                if os.path.exists(destination):
                    raise TaskError("WF_TARGET_COLLISION",
                                    {"destination": os.path.relpath(destination, str(ctx.root))})
                moved = _move_task(ctx.root, current_dir, destination)
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
                                                  f"wf: archive {task_id}\n\nwf-task: {task_id}")
                    # 记录组提交本身即下界：不再依赖 action.kind，避免"已提交却报失败"
                    bound = _parent_of(ctx.root, commit_result.get("head"))
                    persisted = archive_persisted(ctx.root, task, lower_override=bound)
                    persisted["resumed_commit"] = True
                    persisted["business_commit"] = business
                    task = records.load_json(os.path.join(task_dir(ctx.root, task_id), "task.json")) \
                        if task_dir(ctx.root, task_id) else task
            code = "WF_OK" if persisted.get("persisted") else "WF_PERSISTENCE_FAILED"
            return codes.result(
                code,
                object={"id": task_id, "name": task.get("title")},
                position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id,
                                         action_id=(task.get("action") or {}).get("id"),
                                         action_state=(task.get("action") or {}).get("state")),
                next_="归档已持久化：无需重复归档或重复提交" if persisted.get("persisted")
                else "按可达提交查证结果交人核对（不重复归档）",
                facts={"archive_persisted": persisted, "terminal": task.get("terminal")},
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
        business_commit = _commit_paths(ctx.root, sorted(set(grant_paths)),
                                        f"wf: complete {task_id}\n\nwf-task: {task_id}") if grant_paths else {
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
        moved = _move_task(ctx.root, path, destination)
        save_task(ctx.root, moved, task)
        record_rel = os.path.relpath(moved, str(ctx.root)).replace(os.sep, "/")
        commit_paths = [record_rel]
        commit_result = _commit_paths(ctx.root, commit_paths, f"wf: archive {task_id}\n\nwf-task: {task_id}")
        commit_result["business_commit"] = business_commit
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
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase="finish", task_id=task_id,
                                 action_id=task["action"]["id"], action_state=task["action"]["state"]),
        next_="按 §4.4 处理写权释放；下一对象需在新会话选择",
        facts={"terminal": "normal", "archived_at": task["archived_at"], "moved_to": record_rel,
               "commit": commit_result, "control_assertion": assertion, "reassessment": reassessment},
    )


def _reassess_empty_set(ctx, task_id):
    """首轮不存在挂起任务：按空集合通过，不写记录、不返回不可用。"""
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


def cmd_baseline_apply(ctx, args):
    from . import lock

    task_id = args.value("--task")
    proposal_path = args.value("--proposal")
    if not task_id or not proposal_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "baseline-apply requires --task <id> --proposal <path>"})
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
        touch_paths = list((task.get("plan") or {}).get("touch_paths") or [])
        root_real = os.path.realpath(str(ctx.root))
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
            planned.append((normalized, content))
        inputs = {"task": task_id, "files": [item[0] for item in planned],
                  "content_digests": [records.plain_digest(item[1]) for item in planned]}
        pending = actions.pending(task)
        if pending is not None and pending.get("kind") != "baseline.apply":
            raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"), "state": pending.get("state"),
                                                     "kind": pending.get("kind")},
                            next_="先按原动作意图恢复，再发起基线应用")
        if pending is not None:
            if pending.get("inputs_digest") != actions.inputs_digest(inputs):
                raise TaskError("WF_ACTION_INCOMPLETE", {"action": pending.get("id"),
                                                         "reason": "proposal differs from the pending action"},
                                next_="用同一提案重入以续做，或先核对未完成动作")
            action = pending
            task["action"] = action
            save_task(ctx.root, path, task)
        else:
            task, action = _start_task_action(ctx, path, task, "baseline.apply", holder, inputs,
                                              ["verify_proposal", "apply", "verify_result"])
        # 整批预检：先对全部条目分类，确认没有冲突后才写入任何文件
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
    changes_path = args.value("--changes")
    if not task_id or not changes_path:
        raise TaskError("WF_PATH_INVALID", {"reason": "spec-update requires --task <id> --changes <path>"})
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

        touch_paths = list((task.get("plan") or {}).get("touch_paths") or [])
        for change in changes:
            for raw in (change.get("old_paths") or []) + (change.get("new_paths") or []):
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


def cmd_task_reassess(ctx, args):
    """首轮：挂起集合为空，直接通过；第二轮交付完整复评路径。"""
    task_id = args.value("--task")
    if not task_id:
        raise TaskError("WF_PATH_INVALID", {"reason": "task-reassess requires --task <id>"})
    task = _load_or_fail(ctx, task_id)
    return codes.result(
        "WF_OK",
        object={"id": task_id, "name": task.get("title")},
        position_=codes.position(scope="task", phase=task.get("phase"), task_id=task_id),
        next_="无挂起任务；继续当前步骤",
        facts=_reassess_empty_set(ctx, task_id),
    )


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
        touch = (task.get("entry_snapshot") or {}).get("touch_paths") or []
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
            grants = [item for item in decisions[1:] if item.get("choice") == "commit"]
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
            target = paths[0] if paths else str(decisions[0].get("object_digest") or "")
            if not TASK_ID_RE.match(target):
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "transfer 的 subject 首项须是承接任务 id", "target": target})
            target_task = load_task(ctx.root, target)
            if target_task is None or target == task_id:
                raise TaskError("WF_SEMANTIC_DECISION",
                                {"reason": "transfer 须给出存在的具名承接任务 id", "target": target})
            commit_result = {"transferred_to": target}
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

    return [token.strip() for token in re.split(r"[,;\n]", subject) if token.strip()]


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
    writer = writer_mod.load(ctx.root) or {}
    receipts = task_receipts(ctx.root)  # 巡检同样消费可达提交查证（机制稿 §4.5）
    bindings_dir = join(ctx.root, ".wf/session-bindings")
    bindings = len(os.listdir(bindings_dir)) if os.path.isdir(bindings_dir) else 0
    facts = {
        "tasks": {"active": len(active), "archived": len(archived), "total": len(tasks)},
        "duplicate_ids": duplicates,
        "writer": {"state": writer.get("state"), "generation": writer.get("generation"),
                   "receipts": receipts},
        "bindings": bindings,
        "spec": _spec_summary(ctx.root),
        "governance": _governance_summary(ctx.root, tasks, archived),
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
    if not every_problem and every and not unknown:
        # 记录不完整时正常归档计数不可信：不给触发结论（未知不当零）
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
        "inspection": {
            "every_tasks": every,
            "normal_archived": len(normal),
            "abnormal_archived": len(abnormal),
            "due": due,
            "problem": every_problem,
        },
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
        if task.get("terminal") not in ("normal", "abnormal"):
            problems.append({"path": rel, "terminal": task.get("terminal")})
        elif not name.startswith(str(task.get("id"))):
            problems.append({"path": rel, "reason": "record id does not match directory name"})
        elif task.get("terminal") == "abnormal":
            # 异常归档用 _record_committed（记录已入提交且无未提交差异），与 archive_persisted 判据不同
            if not _record_committed(root, rel):
                problems.append({"path": rel, "reason": "abnormal archive record is not committed"})
        else:
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
