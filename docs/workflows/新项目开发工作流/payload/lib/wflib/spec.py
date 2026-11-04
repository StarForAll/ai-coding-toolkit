"""spec.py — 本地 spec 元数据、匹配排序、预算与变更（机制稿 §8.3、§8.4）。"""

from __future__ import annotations

import datetime
import hashlib
import json
import os

from . import paths as paths_mod
from . import records
from .paths import join

VALID_STATUS = ("template", "active", "disabled")
VALID_AUTHOR = ("human", "ai")


class SpecError(Exception):
    def __init__(self, code, facts=None):
        super().__init__(code)
        self.code = code
        self.facts = facts or {}


def parse_frontmatter(path):
    """受限 frontmatter：每行 `key: <JSON值>`；返回 (metadata, problems)。"""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        return {}, [f"unreadable: {exc}"]
    if not lines or lines[0].strip() != "---":
        return {}, ["frontmatter missing"]
    metadata = {}
    problems = []
    for line in lines[1:]:
        if line.strip() == "---":
            return metadata, problems
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            problems.append(f"invalid frontmatter line: {line!r}")
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        if key in metadata:
            problems.append(f"duplicate key: {key}")
            continue
        try:
            metadata[key] = json.loads(raw.strip())
        except ValueError:
            problems.append(f"value is not JSON: {key}")
    problems.append("frontmatter not closed")
    return metadata, problems


def validate_metadata(metadata):
    problems = []
    if metadata.get("schema_version") != 1:
        problems.append("schema_version must be 1")
    status = metadata.get("status")
    if status not in VALID_STATUS:
        problems.append(f"status must be in {VALID_STATUS}")
    author = metadata.get("author")
    if author not in VALID_AUTHOR:
        problems.append(f"author must be in {VALID_AUTHOR}")
    verified = metadata.get("verified_at")
    if verified not in (None, "extracted"):
        if not isinstance(verified, str):
            problems.append("verified_at must be a date string, 'extracted' or null")
        else:
            try:
                datetime.date.fromisoformat(verified)
            except ValueError:
                problems.append("verified_at must be a valid ISO date")
    if status == "active":
        if verified is None:
            problems.append("active spec requires verified_at (date or extracted)")
        if not metadata.get("counterexample"):
            problems.append("active spec requires counterexample")
    raw_paths = metadata.get("paths")
    valid_paths = []
    path_problems = []
    if raw_paths is not None:
        if not isinstance(raw_paths, list) or any(not isinstance(item, str) for item in raw_paths):
            problems.append("paths must be a string array")
        else:
            for item in raw_paths:
                try:
                    valid_paths.append(paths_mod.validate_glob(item))
                except paths_mod.InvalidPath as exc:
                    # 单条非法：只失效该条，其余条目继续可用（设计稿 §6.1）
                    path_problems.append(f"invalid path entry {item!r}: {exc}")
    return problems, valid_paths, path_problems


def path_violation(root, relative):
    """统一边界判定（项目包含性 + 字面/真实祖先的嵌套仓库）：读写入口共用。"""
    return paths_mod.boundary_violation(root, relative)


def load_spec(root, relative):
    absolute = join(root, relative)
    violation = path_violation(root, relative)
    if violation:
        return {"path": relative, "metadata": {}, "paths": [], "problems": [f"unroutable: {violation}"],
                "path_problems": [], "routable": False, "violation": violation, "digest": None}
    metadata, problems = parse_frontmatter(absolute)
    errors, valid_paths, path_problems = validate_metadata(metadata)
    # 整段解析/元数据不可靠 → 整文件不可路由；单条路径非法只失效该条
    routable = not problems and not errors
    return {"path": relative, "metadata": metadata, "paths": valid_paths,
            "problems": problems + errors, "path_problems": path_problems,
            "routable": routable, "digest": records.file_digest(absolute)}


def all_specs(root):
    directory = join(root, ".wf/spec")
    found = []
    if not os.path.isdir(directory):
        return found
    for base, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            absolute = os.path.join(base, name)
            relative = os.path.relpath(absolute, str(root)).replace(os.sep, "/")
            found.append(load_spec(root, relative))
    return found


def sort_key(entry, matched_path):
    metadata = entry["metadata"]
    best = None
    for pattern in entry["paths"]:
        if not paths_mod.match_path(pattern, matched_path):
            continue
        literal = len(paths_mod.literal_prefix(pattern))
        wildcards = sum(segment.count("*") + segment.count("?") for segment in pattern.split("/"))
        exact = 0 if pattern == matched_path else 1
        candidate = (exact, -literal, wildcards, -len(pattern), entry["path"])
        if best is None or candidate < best:
            best = candidate
    return best


def match(root, candidate_paths):
    """按 paths 匹配并按固定排序键排序。"""
    hits = {}
    unparsed = []
    for entry in all_specs(root):
        if entry.get("path_problems"):
            # 单条非法路径可见报告，但合法条目仍参与匹配
            unparsed.append({"path": entry["path"], "problems": entry["path_problems"],
                             "kind": "path", "routable": bool(entry.get("routable"))})
        if not entry.get("routable", not entry["problems"]):
            unparsed.append({"path": entry["path"], "problems": entry["problems"], "kind": "metadata"})
            continue
        if entry["metadata"].get("status") != "active":
            continue
        for candidate in candidate_paths:
            key = sort_key(entry, candidate)
            if key is None:
                continue
            hits.setdefault(entry["path"], (key, entry))
    ordered = sorted(hits.values(), key=lambda item: item[0])
    return [entry for _key, entry in ordered], unparsed


def sidecar_path(root, key):
    return join(root, f".wf/.runtime/spec-reads/{key}.json")


def record_read(root, key, relative, *, complete, deliver_codepoints, budget):
    path = sidecar_path(root, key)
    current = records.load_json(path, None) or {"specs": []}
    specs = [entry for entry in current.get("specs") or [] if entry.get("path") != relative]
    specs.append(
        {
            "path": relative,
            "digest": records.file_digest(join(root, relative)),
            "read_at": records.now_str(),
            "complete": bool(complete),
            "codepoints": deliver_codepoints,
            "budget": budget,
        }
    )
    payload = {"specs": specs}
    try:
        records.write_json(path, payload)
    except OSError as exc:
        return {"written": False, "reason": str(exc)}
    return {"written": True, "specs": specs}


def load_one_with_budget(root, relative, budget):
    """单文件：超预算也完整输出并明示（机制稿 §8.4）。"""
    absolute = join(root, relative)
    with open(absolute, "r", encoding="utf-8") as handle:
        text = handle.read()
    codepoints = len(text)
    return {
        "path": relative,
        "text": text,
        "codepoints": codepoints,
        "complete": True,
        "over_budget": codepoints > budget,
    }


def curation_stats(root):
    counts = {}
    for _path, task in _iter_all_tasks(root):
        known = set()
        for entry in task.get("curation") or []:
            known.add(entry.get("path"))
        for path in known:
            if not path:
                continue
            counts[path] = counts.get(path, 0) + 1
    return dict(sorted(counts.items()))


def _iter_all_tasks(root):
    from . import tasks as tasks_mod

    return list(tasks_mod.iter_tasks(root))




def _sync_curation_paths(root, old_path, new_path, current_task_id=None):
    """改名同步活动任务的策展引用（只改路径与哈希，机制稿 §8.4）。"""
    from . import tasks as tasks_mod
    import os

    from . import actions as actions_mod

    digest = records.file_digest(join(root, new_path))
    for directory, task in tasks_mod.iter_tasks(root):
        # 已归档任务的旧路径是历史证据，不强改（设计稿 §6.3）
        if task.get("status") == "archived" or task.get("terminal"):
            continue
        # 冲突已在 validate_changes 前置判定；此处只同步，不再中断

        changed = False
        for entry in task.get("curation") or []:
            if entry.get("path") == old_path:
                entry["path"] = new_path
                entry["digest"] = digest
                changed = True
        if changed:
            # 包络字段与常规写入一致（机制稿 §1.2）：窄写入也 bump 版本与时间
            task["revision"] = int(task.get("revision") or 0) + 1
            task["updated_at"] = records.now_str()
            records.write_json(os.path.join(directory, "task.json"), task)


def _index_path(root):
    return join(root, ".wf/spec/index.md")


def _sync_index(root, *, add=None, remove=None, rename=None):
    path = _index_path(root)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        lines = text.splitlines()
    except FileNotFoundError:
        text = "# spec 索引\n\n## 规则\n"
        lines = ["# spec 索引", "", "## 规则", ""]
    if text.count("```") % 2 == 1:
        # 结构损坏（未闭合围栏）时追加进去只会跑到代码块里：明确要求先修索引
        raise SpecError("WF_SEMANTIC_DECISION",
                        {"reason": "spec index has an unclosed code fence", "path": _index_path_rel(root),
                         "exits": ["先修好索引结构再重跑", "由人确认索引重建"]})
    lines = [line for line in lines if not (remove and f"]({remove})" in line)]
    replaced = False
    for index, line in enumerate(lines):
        if rename and f"]({rename[0]})" in line:
            lines[index] = line.replace(f"]({rename[0]})", f"]({rename[1]})")
            replaced = True
    if rename and not replaced:
        # 索引里本来就没有旧条目（初始化骨架/被手工改乱/上次同步失败）：
        # 只做替换等于什么也没补，改为把新路径追加进去（设计稿 §6.1 索引必须能定位）
        add = rename[1]
    if add:
        entry = f"- [{os.path.basename(add)}]({add})"
        seen = False
        deduped = []
        for line in lines:
            if f"]({add})" in line:
                if seen:
                    continue      # 同一目标只留一条
                seen = True
            deduped.append(line)
        lines = deduped
        if not seen:
            lines.append(entry)
    records.atomic_write(path, "\n".join(lines) + "\n")
    return os.path.relpath(path, str(root)).replace(os.sep, "/")


def _index_path_rel(root):
    return os.path.relpath(_index_path(root), str(root)).replace(os.sep, "/")


def _active_dependencies(root, path):
    dependents = []
    for task_path, task in _iter_all_tasks(root):
        if task.get("status") == "archived" and task.get("terminal") == "normal":
            continue
        for entry in task.get("curation") or []:
            if entry.get("path") == path and not entry.get("released"):
                dependents.append({"task": task.get("id"), "status": task.get("status")})
    return dependents




def _release_dependencies(root, dispositions):
    """人已解除活动依赖的写入（只改策展条目的 released 字段，机制稿 §8.4）。"""
    from . import tasks as tasks_mod

    for entry in dispositions:
        if not isinstance(entry, dict):
            continue
        if not entry.get("released"):
            # 只有外层 decision/replacement 的旧形态：人已给决定却没落盘，必须可见而不是静默跳过
            if entry.get("decision") or entry.get("replacement"):
                raise SpecError("WF_SEMANTIC_DECISION",
                                {"reason": "release must be declared under released.{decision,replacement}",
                                 "task": entry.get("task_id"), "path": entry.get("path")})
            continue
        task_id = entry.get("task_id")
        path = entry.get("path")
        if not task_id or not path:
            raise SpecError("WF_SEMANTIC_DECISION", {"reason": "release requires task_id and path", "entry": entry})
        # 「人在该任务策展清单记下已解除依赖」：决定本身要有内容，空值不能算人已同意
        _require_release_decision(entry.get("released"), task_id, path)
        directory = tasks_mod.task_dir(root, task_id)
        if not directory:
            raise SpecError("WF_HISTORY_UNRESOLVED", {"reason": "task not found", "task": task_id})
        import os

        task = records.load_json(os.path.join(directory, "task.json"))
        if not isinstance(task, dict):
            raise SpecError("WF_RECORD_INVALID", {"task": task_id})
        found = False
        released = entry.get("released") if isinstance(entry.get("released"), dict) else {}
        for item in task.get("curation") or []:
            if item.get("path") == path:
                item["released"] = {
                    # 决定与替代路径都在 released 里（机制稿 §1.3 curation.released 定义）；
                    # 外层的同名字段只是兼容写法，不能盖掉校验过的那一份
                    "decision": released.get("decision"),
                    "old_path": path,
                    "old_digest": item.get("digest"),
                    "replacement": released.get("replacement", entry.get("replacement")),
                }
                found = True
        if not found:
            raise SpecError("WF_SEMANTIC_DECISION", {"reason": "curation entry not found", "task": task_id,
                                                     "path": path})
        # 与常规写入一致地 bump 包络（机制稿 §1.2）
        task["revision"] = int(task.get("revision") or 0) + 1
        task["updated_at"] = records.now_str()
        records.write_json(os.path.join(directory, "task.json"), task)




def _require_release_decision(released, task_id, path):
    """解除依赖的人判必须是有效决定：对象、结论非空、带理由（设计稿 §6.3、机制稿 §8.4）。"""
    decision = released.get("decision") if isinstance(released, dict) else None
    if not isinstance(decision, dict) or not decision:
        raise SpecError("WF_SEMANTIC_DECISION",
                        {"reason": "release decision is missing or empty",
                         "task": task_id, "path": path})
    if not str(decision.get("choice") or "").strip():
        raise SpecError("WF_SEMANTIC_DECISION",
                        {"reason": "release decision lacks a choice", "task": task_id, "path": path})
    # 只核结构：choice 表达什么由人决定（机制稿 §1.5 语义面）。脚本不自造取值白名单。
    if not str(decision.get("reason") or "").strip():
        raise SpecError("WF_SEMANTIC_DECISION",
                        {"reason": "release decision lacks a reason", "task": task_id, "path": path})


def _check_reference_conflicts(root, old_paths, current_task_id=None):
    """写入前检查真正引用这些路径的活动任务是否带未完成动作（机制稿 §8.4）。"""
    from . import actions as actions_mod
    from . import tasks as tasks_mod

    pending = []
    for directory, task in tasks_mod.iter_tasks(root):
        if task.get("status") == "archived" or task.get("terminal"):
            continue
        if current_task_id and task.get("id") == current_task_id:
            continue  # 本次变更自身的在途动作不算冲突
        action = actions_mod.pending(task)
        if action is None:
            continue
        for entry in task.get("curation") or []:
            if entry.get("path") in old_paths and not entry.get("released"):
                pending.append({"task": task.get("id"), "action": action.get("id"),
                                "state": action.get("state"), "path": entry.get("path")})
    if pending:
        raise SpecError("WF_ACTION_INCOMPLETE", {"reason": "关联任务存在未完成动作，先恢复再改名",
                                                 "pending": pending})


def validate_changes(root, changes, resume=False, current_task_id=None):
    """整批预校验：结构、路径、重命名源目标、删除前的依赖解除目标；不写任何文件。

    resume=True 时按「已落盘事实」识别已完成步骤：改名源已不存在但目标存在、删除目标已不存在，
    均视为该步已完成而跳过前置校验（其余检查不放松）。
    """
    from . import tasks as tasks_mod

    if not isinstance(changes, list):
        raise SpecError("WF_RECORD_INVALID", {"reason": "changes must be an array"})
    for change in changes:
        if not isinstance(change, dict):
            raise SpecError("WF_RECORD_INVALID", {"reason": "change entry must be an object"})
        operation = change.get("operation")
        if operation not in ("add", "update", "merge", "rename", "delete", "disable"):
            raise SpecError("WF_DEFINITION_INVALID", {"reason": f"unknown spec operation: {operation}"})
        old_paths = change.get("old_paths") or []
        new_paths = change.get("new_paths") or []
        root_real = os.path.realpath(str(root))
        for relative in old_paths + new_paths:
            try:
                normalized = paths_mod.normalize(relative)
            except paths_mod.InvalidPath as exc:
                raise SpecError("WF_PATH_INVALID", {"path": relative, "reason": str(exc)})
            if not paths_mod.write_target_allowed(normalized):
                # 与 baseline-apply 共用同一白名单：控制记录一律拒绝（设计稿 §7.3）
                raise SpecError("WF_SCOPE_UNRESOLVED",
                                {"reason": "spec change target not in the writable class",
                                 "path": normalized, "allowed": paths_mod.write_target_allowed_list()})
            violation = paths_mod.boundary_violation(root, normalized)
            if violation:
                raise SpecError("WF_PATH_INVALID", {"reason": violation, "path": normalized})
        if operation in ("delete", "disable", "rename"):
            _check_reference_conflicts(root, old_paths, current_task_id)
        if operation in ("delete", "disable"):
            for entry in change.get("reference_dispositions") or []:
                if not isinstance(entry, dict) or not entry.get("released"):
                    continue
                task_id = entry.get("task_id")
                path = entry.get("path")
                if not task_id or not path:
                    raise SpecError("WF_SEMANTIC_DECISION",
                                    {"reason": "release requires task_id and path", "entry": entry})
                _require_release_decision(entry.get("released"), task_id, path)
                directory = tasks_mod.task_dir(root, task_id)
                if not directory:
                    raise SpecError("WF_HISTORY_UNRESOLVED", {"reason": "task not found", "task": task_id})
                task = records.load_json(os.path.join(directory, "task.json"))
                if not isinstance(task, dict):
                    raise SpecError("WF_RECORD_INVALID", {"task": task_id})
                if not any(item.get("path") == path for item in task.get("curation") or []):
                    raise SpecError("WF_SEMANTIC_DECISION",
                                    {"reason": "curation entry not found", "task": task_id, "path": path})
            for relative in old_paths:
                if not os.path.exists(join(root, relative)):
                    if resume:
                        continue
                    raise SpecError("WF_PATH_INVALID", {"path": relative, "reason": "target missing"})
            pending_old = [relative for relative in old_paths if os.path.exists(join(root, relative))]
            released = {(item.get("task_id"), item.get("path"))
                        for item in change.get("reference_dispositions") or []
                        if isinstance(item, dict) and item.get("released")}
            for relative in pending_old:
                dependents = [item for item in _active_dependencies(root, relative)
                              if (item.get("task"), relative) not in released]
                if dependents:
                    raise SpecError(
                        "WF_SEMANTIC_DECISION",
                        {"reason": "active dependencies block deletion/disable", "path": relative,
                         "dependents": dependents,
                         "exits": ["先在该任务解除依赖", "推迟删除", "指定替代文件"]},
                    )
            continue
        if operation == "rename":
            if len(old_paths) != 1 or len(new_paths) != 1:
                raise SpecError("WF_SEMANTIC_DECISION", {"reason": "rename requires one old and one new path"})
            source_exists = os.path.exists(join(root, old_paths[0]))
            target_exists = os.path.exists(join(root, new_paths[0]))
            if resume and not source_exists and target_exists:
                continue
            if not source_exists:
                raise SpecError("WF_PATH_INVALID", {"path": old_paths[0], "reason": "source missing"})
            if target_exists:
                raise SpecError("WF_TARGET_COLLISION", {"path": new_paths[0]})
            continue
        if not new_paths or not isinstance(change.get("content"), str):
            raise SpecError("WF_SEMANTIC_DECISION", {"reason": f"{operation} requires new_paths and content"})

    # R19：整批候选冲突（源唯一、目标唯一、目标不得是另一变更的源）
    sources, targets = [], []
    for index, change in enumerate(changes):
        for path in change.get("old_paths") or []:
            sources.append((index, paths_mod.normalize(path)))
        for path in change.get("new_paths") or []:
            targets.append((index, paths_mod.normalize(path)))
    seen_sources, seen_targets = {}, {}
    for index, path in sources:
        if path in seen_sources:
            raise SpecError("WF_TARGET_COLLISION",
                            {"reason": "同一个源在多条变更中被引用", "path": path,
                             "changes": [seen_sources[path], index]})
        seen_sources[path] = index
    for index, path in targets:
        if path in seen_targets:
            raise SpecError("WF_TARGET_COLLISION",
                            {"reason": "多条变更写同一个目标", "path": path,
                             "changes": [seen_targets[path], index]})
        seen_targets[path] = index
    for index, path in targets:
        owner = seen_sources.get(path)
        if owner is not None and owner != index:
            raise SpecError("WF_TARGET_COLLISION",
                            {"reason": "一条变更的目标是另一条变更的源（隐含链式依赖）", "path": path,
                             "changes": [owner, index]})
    return True


def apply_changes(root, changes, task, resume=False, current_task_id=None):
    """按变更集应用；先整批校验（零写入），再逐条应用，写失败映射为结构化退出码。"""
    validate_changes(root, changes, resume=resume, current_task_id=current_task_id)
    applied = []
    for change in changes:
        try:
            _apply_change(root, change, task, applied, resume=resume)
        except OSError as exc:
            raise SpecError("WF_PERSISTENCE_FAILED",
                            {"reason": f"写入失败：{exc}", "operation": change.get("operation"),
                             "applied": applied}) from exc
    return applied


def _apply_change(root, change, task, applied, resume=False):
    operation = change.get("operation")
    old_paths = change.get("old_paths") or []
    new_paths = change.get("new_paths") or []
    if operation in ("delete", "disable"):
        _release_dependencies(root, change.get("reference_dispositions") or [])
        for relative in old_paths:
            dependents = _active_dependencies(root, relative)
            if dependents:
                raise SpecError(
                    "WF_SEMANTIC_DECISION",
                    {"reason": "active dependencies block deletion/disable", "path": relative,
                     "dependents": dependents,
                     "exits": ["先在该任务解除依赖", "推迟删除", "指定替代文件"]},
                )
        for index, relative in enumerate(old_paths):
            absolute = join(root, relative)
            if resume:
                action = _resume_decision_removal(root, change, relative, index, operation)
                if action == "skip":
                    _sync_index(root, remove=relative)
                    continue
            if operation == "delete" and os.path.exists(absolute):
                os.unlink(absolute)
            elif operation == "disable" and os.path.exists(absolute):
                metadata, _problems = parse_frontmatter(absolute)
                metadata["status"] = "disabled"
                records.atomic_write(absolute, _rewrite_frontmatter(absolute, metadata))
                metadata_after, problems_after = parse_frontmatter(absolute)
                if problems_after or metadata_after.get("status") != "disabled":
                    raise SpecError("WF_RECORD_INVALID",
                                    {"reason": "disabled spec is not parseable after rewrite",
                                     "path": relative, "problems": problems_after})
            _sync_index(root, remove=relative)
        applied.append({"operation": operation, "old_paths": old_paths, "new_paths": [],
                        "before_digests": change.get("before_digests") or [],
                        "after_digests": [], "reference_dispositions": []})
        return
    if operation == "rename":
        source, target = old_paths[0], new_paths[0]
        if resume:
            action = _resume_decision_rename(root, change, source, target)
            if action == "skip":
                _sync_index(root, rename=(source, target))
                _sync_curation_paths(root, source, target, (task or {}).get("id"))
                applied.append({"operation": operation, "old_paths": old_paths, "new_paths": new_paths,
                                "before_digests": [records.file_digest(join(root, target))],
                                "after_digests": [records.file_digest(join(root, target))],
                                "reference_dispositions": []})
                return
        if os.path.exists(join(root, source)):
            os.makedirs(os.path.dirname(join(root, target)), exist_ok=True)
            os.rename(join(root, source), join(root, target))
        _sync_index(root, rename=(source, target))
        _sync_curation_paths(root, source, target, (task or {}).get("id"))
        applied.append({"operation": operation, "old_paths": old_paths, "new_paths": new_paths,
                        "before_digests": [records.file_digest(join(root, target))],
                        "after_digests": [records.file_digest(join(root, target))],
                        "reference_dispositions": []})
        return
    content = change.get("content")
    for index, relative in enumerate(new_paths):
        if resume:
            action = _resume_decision(root, change, relative, content, index)
            if action == "skip":
                # 正文已是本动作后像，但索引可能还没补：后置条件要分别核实，不能一起跳过
                _sync_index(root, add=relative)
                continue
        records.atomic_write(join(root, relative), content)
        _sync_index(root, add=relative)
    applied.append({"operation": operation, "old_paths": old_paths, "new_paths": new_paths,
                    "before_digests": change.get("before_digests") or [],
                    "after_digests": [records.file_digest(join(root, relative)) for relative in new_paths],
                    "reference_dispositions": change.get("reference_dispositions") or []})


def _resume_decision(root, change, relative, content, index):
    """续做时的三态判定（机制稿 §5.2）：符合前像→应用；已是本动作后像→跳过；都不符合→冲突。

    中断后文件可能被别的动作改过；此时按原变更集续做会覆盖新内容，必须停下来报冲突。
    """
    absolute = join(root, relative)
    expected_after = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    before = change.get("before_digests") or []
    expected_before = before[index] if index < len(before) else None
    current = records.file_digest(absolute) if os.path.exists(absolute) else None
    if current == expected_after:
        return "skip"  # 本动作已经写下预期后像
    if expected_before is None:
        if current is None:
            return "apply"
    elif current == expected_before:
        return "apply"
    raise SpecError("WF_SEMANTIC_DECISION",
                    {"reason": "resume target changed after the interruption",
                     "path": relative, "expected_before": expected_before,
                     "current": current, "expected_after": expected_after,
                     "exits": ["放弃续做并重新取前像", "先处置中断后的新内容再续做"]})


def _resume_decision_removal(root, change, relative, index, operation):
    """删除/停用的续做三态：仍符合前像→执行；本动作后像（已删除）→跳过；都不符→冲突。"""
    absolute = join(root, relative)
    before = change.get("before_digests") or []
    expected_before = before[index] if index < len(before) else None
    current = records.file_digest(absolute) if os.path.exists(absolute) else None
    if operation == "delete":
        if current is None:
            return "skip"           # 已经删掉了：本动作后像
        if current == expected_before:
            return "apply"
    else:  # disable：前像未变→执行；已是本动作后像（status=disabled）→跳过
        if current is not None and current == expected_before:
            return "apply"
        if current is not None:
            metadata, problems = parse_frontmatter(absolute)
            if not problems and metadata.get("status") == "disabled":
                # 后像是"改写后的新内容"，无法从前后像推定；只能给人核对出口，不能静默认作本动作成果
                raise SpecError("WF_SEMANTIC_DECISION",
                                {"reason": "target already disabled but cannot be proven to be this action's result",
                                 "path": relative, "looks_already_disabled": True,
                                 "exits": ["确认该停用确由本动作完成，再补齐索引", "按外部改动处置后重跑"]})
    raise SpecError("WF_SEMANTIC_DECISION",
                    {"reason": "resume target changed after the interruption",
                     "path": relative, "operation": operation,
                     "expected_before": expected_before, "current": current,
                     "exits": ["放弃续做并重新取前像", "先处置中断后的新内容再续做"]})


def _resume_decision_rename(root, change, source, target):
    """改名的续做三态：源仍是前像→执行；源已不在且目标在→已完成后像；其余→冲突。"""
    before = (change.get("before_digests") or [None])[0]
    source_abs, target_abs = join(root, source), join(root, target)
    source_now = records.file_digest(source_abs) if os.path.exists(source_abs) else None
    target_now = records.file_digest(target_abs) if os.path.exists(target_abs) else None
    if source_now is not None and source_now == before:
        return "apply"
    if source_now is None and target_now is not None:
        # 有前像就必须核内容仍是同一份；没有前像（旧登记/未给摘要）只能按"已完成"处理
        if before is None or target_now == before:
            return "skip"

    raise SpecError("WF_SEMANTIC_DECISION",
                    {"reason": "resume target changed after the interruption",
                     "source": source, "target": target,
                     "expected_before": before, "source_now": source_now, "target_now": target_now,
                     "exits": ["放弃续做并重新取前像", "先处置中断后的新内容再续做"]})


def _frontmatter_meta(path):
    """parse_frontmatter 返回 (metadata, problems)；这里只要元数据与问题。"""
    return parse_frontmatter(path)


def _rewrite_frontmatter(path, metadata):
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SpecError("WF_RECORD_INVALID", {"reason": "frontmatter missing"})
    output = ["---"]
    for key, value in metadata.items():
        output.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    output.append("---")  # 结束分隔符必须补回，否则正文被当成 frontmatter（frontmatter not closed）
    index = 1
    while index < len(lines) and lines[index].strip() != "---":
        index += 1
    output.extend(lines[index + 1:])
    return "\n".join(output) + "\n"
