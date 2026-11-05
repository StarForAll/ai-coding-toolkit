"""scope.py — 治理面、候选路径分类与外部变更核对（机制稿 §3.3–§3.5、§4.4）。

只做结构判定与事实列举；范围语义存疑输出需人裁决。
"""

from __future__ import annotations

import json
import os
import subprocess

from . import paths as paths_mod
from . import records
from .paths import join

GOVERNANCE_MARKER = "<!-- wf-governance:v1 -->"


# --------------------------------------------------------------------------
# git（只读查询；不改变仓库状态）
# --------------------------------------------------------------------------


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args], cwd=str(root), capture_output=True, text=True,
            check=False
        )
    except OSError:
        return None, ""
    if result.returncode != 0:
        return result.returncode, result.stdout
    return 0, result.stdout


def has_git(root) -> bool:
    if not os.path.isdir(join(root, ".git")) and not os.path.isfile(join(root, ".git")):
        return False
    code, out = git(root, "rev-parse", "--show-toplevel")
    return code == 0


def head(root):
    code, out = git(root, "rev-parse", "HEAD")
    if code != 0:
        return None
    value = out.strip()
    return value or None


def is_ancestor(root, ancestor, descendant="HEAD"):
    """祖先判定**不缓存**：同进程调用方可能在进程内改 HEAD（多个套件直接 import 本模块后自行提交），
    缓存会给出陈旧事实。可缓存的只有按提交 sha 定位的不可变对象（见 tasks._tree_entries）。"""
    code, _ = git(root, "merge-base", "--is-ancestor", ancestor, descendant)
    return code == 0


def uncommitted_paths(root):
    """工作树与索引相对 HEAD 的并集（含未跟踪拟交付文件）。"""
    if not has_git(root):
        return []
    code, out = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if code != 0:
        raise records.RecordInvalid("git status failed; cannot enumerate workspace")
    entries = out.split("\0")
    found = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if path:
            found.append(path)
        if status[:1] in ("R", "C") or status[1:2] in ("R", "C"):
            if index < len(entries) and entries[index]:
                found.append(entries[index])
                index += 1
    return sorted(set(item for item in found if item))


def commit_message(root, sha):
    code, out = git(root, "log", "-1", "--format=%B", sha)
    return out if code == 0 else ""


def commit_trailer_task(message):
    for line in (message or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("wf-task:"):
            return stripped.split(":", 1)[1].strip()
    return None


def commit_paths(root, sha):
    code, out = git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "--no-renames", sha)
    if code != 0:
        return None
    return [line for line in out.splitlines() if line]


def commits_since(root, start):
    if not start:
        return []
    if not is_ancestor(root, start):
        return None
    code, out = git(root, "rev-list", "--reverse", f"{start}..HEAD")
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def attributed_paths(root, task_id, start):
    """标记提交 + 归属裁决所得路径（本任务）。"""
    found = set()
    for sha in commits_since(root, start) or []:
        message = commit_message(root, sha)
        if commit_trailer_task(message) == task_id:
            found.update(commit_paths(root, sha) or [])
    return sorted(found)


def attribution_commits(root, task):
    commits = []
    for entry in (task.get("attribution") or {}).get("decisions") or []:
        if entry.get("commit"):
            commits.append(entry["commit"])
    return commits


def attributed_by_decision(root, task):
    found = set()
    for sha in attribution_commits(root, task):
        found.update(commit_paths(root, sha) or [])
    for entry in (task.get("attribution") or {}).get("inherited") or []:
        for path in entry.get("paths") or []:
            found.add(path)
    return sorted(found)


# --------------------------------------------------------------------------
# 治理面
# --------------------------------------------------------------------------


def baseline_path(root):
    return join(root, ".wf/baseline.md")


def parse_governance(root):
    """返回 (block, problems)；块缺失/不可解析/全部条目失效即不可用。"""
    path = baseline_path(root)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        return None, ["baseline missing"]
    marker_index = text.find(GOVERNANCE_MARKER)
    if marker_index < 0:
        return None, ["governance block missing"]
    tail = text[marker_index + len(GOVERNANCE_MARKER):]
    fence_start = tail.find("```json")
    if fence_start < 0:
        return None, ["governance block has no json fence"]
    fence_start += len("```json")
    fence_end = tail.find("```", fence_start)
    if fence_end < 0:
        return None, ["governance json fence not closed"]
    try:
        block = json.loads(tail[fence_start:fence_end])
    except ValueError as exc:
        return None, [f"governance block invalid json: {exc}"]
    if not isinstance(block, dict) or not isinstance(block.get("paths"), list):
        return None, ["governance block shape invalid"]
    valid = []
    problems = []
    for pattern in block["paths"]:
        try:
            valid.append(paths_mod.validate_glob(pattern))
        except paths_mod.InvalidPath as exc:
            problems.append(f"invalid governance entry {pattern!r}: {exc}")
    if not valid and block.get("paths"):
        return None, problems or ["all governance entries invalid"]
    return {"paths": valid, "reason": block.get("reason"), "decided_by": block.get("decided_by"),
            "decided_at": block.get("decided_at")}, problems


TREE_EXCLUDES = (".git", ".wf", "__pycache__", "node_modules")


def _enumerate_tree(root):
    """只读枚举工作树路径：优先 `git ls-files`（与 Git 同源、快），不可用时退回 os.walk。"""
    tracked = _git_ls_files(root)
    if tracked is not None:
        return tracked
    found = []
    for base, dirs, files in os.walk(str(root)):
        dirs[:] = [name for name in dirs if name not in TREE_EXCLUDES]
        for name in files:
            absolute = os.path.join(base, name)
            found.append(os.path.relpath(absolute, str(root)).replace(os.sep, "/"))
    return found


def _git_ls_files(root):
    """仓库内用 `git ls-files -z --cached --others --exclude-standard`；非仓库返回 None。"""
    import subprocess

    try:
        inside = subprocess.run(["git", "-c", "core.quotePath=false", "rev-parse", "--is-inside-work-tree"],
                                cwd=str(root), capture_output=True, text=True, check=False)
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return None
        listing = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files", "-z",
                                  "--cached", "--others", "--exclude-standard"],
                                 cwd=str(root), capture_output=True, text=True, check=False)
        if listing.returncode != 0:
            return None
    except OSError:
        return None
    paths = [entry for entry in (listing.stdout or "").split("\0") if entry]
    return [path for path in paths if not any(part in TREE_EXCLUDES for part in path.split("/"))]


def governance_condition(root, touch_paths):
    """条件①：witnessed / disjoint / prefix-unexcluded / governance-unavailable。"""
    block, problems = parse_governance(root)
    if block is None:
        return "unknown", {"fact": "governance-unavailable", "problems": problems}
    tree = _enumerate_tree(root)
    for pattern in block["paths"]:
        if not paths_mod.has_wild(pattern) or any(segment == "**" for segment in pattern.split("/")):
            for actual in tree:
                if paths_mod.match_path(pattern, actual):
                    for touch in touch_paths or []:
                        if paths_mod.match_path(touch, actual):
                            return "true", {"fact": "witnessed", "path": actual, "governance": pattern}
            continue
        for actual in tree:
            if paths_mod.match_path(pattern, actual):
                for touch in touch_paths or []:
                    if paths_mod.match_path(touch, actual):
                        return "true", {"fact": "witnessed", "path": actual, "governance": pattern}
    for governance_pattern in block["paths"]:
        for touch in touch_paths or []:
            if not paths_mod.provably_disjoint(governance_pattern, touch):
                return "true", {"fact": "prefix-unexcluded", "governance": governance_pattern, "touch": touch}
    return "false", {"fact": "disjoint"}


def declaration_violations(actual_paths, touch_paths, root):
    """声明判定：每条实际落入治理面的路径须有可证包含的批准条目。"""
    block, problems = parse_governance(root)
    if block is None:
        return [], {"unavailable": True, "problems": problems}
    violations = []
    for actual in actual_paths:
        for governance_pattern in block["paths"]:
            if not paths_mod.match_path(governance_pattern, actual):
                continue
            declared = any(
                paths_mod.match_path(entry, actual) and paths_mod.subsumes(entry, governance_pattern)
                for entry in touch_paths or []
            )
            if not declared:
                violations.append(
                    {
                        "path": actual,
                        "governance": governance_pattern,
                        "declared": list(touch_paths or []),
                    }
                )
    return violations, {"unavailable": False}


# --------------------------------------------------------------------------
# 候选路径分类（§3.5）
# --------------------------------------------------------------------------


def _is_control_record(path, task_id, installed=None):
    """框架自身的控制面与**安装器投放的框架资产**不算任务交付物。

    技能副本现在装在目标项目内（如 `.agents/skills/wf-start/SKILL.md`），它们是安装产物、
    不是本任务改的业务文件；按 installation.json 登记的投放清单识别，不按目录名猜。
    """
    if path.startswith(".wf/tasks/"):
        return f"/{task_id}-" in path
    if path.startswith(
        (".wf/session-bindings/", ".wf/writer.json", ".wf/.runtime/", ".wf/workflow-runs/",
         ".wf/install/", ".wf/preparations/")
    ):
        return True
    return path in (installed or ())


def installed_asset_paths(root):
    """安装记录里登记的投放路径（项目内相对路径）——框架资产，不是任务交付物。"""
    from . import records as records_mod

    installation = records_mod.load_json(os.path.join(str(root), ".wf/install/installation.json"), None)
    if not isinstance(installation, dict):
        return set()
    found = set()
    base_root = os.path.realpath(str(root))
    for asset in installation.get("assets") or []:
        target = (asset or {}).get("target")
        if not isinstance(target, str) or not target:
            continue
        root_ref = (asset or {}).get("root_ref") or "project"
        if root_ref == "project":
            found.add(target.replace(os.sep, "/"))
            continue
        # 技能副本：root_ref 是投放根（可能在项目内），换算成项目内相对路径
        absolute = os.path.join(str(root_ref), *target.split("/"))
        relative = os.path.relpath(os.path.realpath(absolute), base_root).replace(os.sep, "/")
        if not relative.startswith(".."):
            found.add(relative)
    return found


def classify_candidates(root, task, receipts=None):
    """返回 {a: [...], b: [...], c: [...], d: [...], e: [...], f: [...], facts...}。"""
    task_id = task.get("id")
    entry = task.get("entry_snapshot") or {}
    touch_paths = entry.get("touch_paths") or (task.get("plan") or {}).get("touch_paths") or []
    uncommitted = uncommitted_paths(root)
    attributed = set(attributed_paths(root, task_id, task.get("baseline_head")))
    attributed |= set(attributed_by_decision(root, task))
    candidates = sorted(set(uncommitted) | attributed)
    installed = installed_asset_paths(root)
    buckets = {"a": [], "b": [], "c": [], "d": [], "e": [], "f": []}
    receipt_paths = set()
    for receipt in receipts or []:
        if receipt["state"] in ("applied_pending_commit", "pending_check"):
            receipt_paths.update(receipt["facts"].get("paths") or [])
    for path in candidates:
        if path in receipt_paths:
            buckets["a"].append(path)
            continue
        if _is_control_record(path, task_id, installed):
            buckets["b"].append(path)
            continue
        owned = path in attributed or any(paths_mod.match_path(entry_pattern, path) for entry_pattern in touch_paths)
        in_scope = any(paths_mod.match_path(entry_pattern, path) for entry_pattern in touch_paths)
        if owned and in_scope:
            buckets["e"].append(path)
            continue
        if owned and not in_scope:
            buckets["f"].append(path)
            continue
        if path in uncommitted:
            buckets["c"].append(path)
            continue
        buckets["d"].append(path)
    return {
        "buckets": buckets,
        "candidates": candidates,
        "touch_paths": touch_paths,
        "entry_snapshot": entry,
    }


def cross_task_conflicts(root, task):
    """活冲突：当前未提交的路径被**另一个任务显式记为 WIP**（停/交接时保存的指纹）。

    历史提交曾改过同一文件不等于永久拥有它（机制稿 §3.3）：只有另一任务明确留下
    `handoff.wip.paths` 声明"这些改动我还没处置"时，才算当前争抢。
    """
    task_id = task.get("id")
    touch_paths = (task.get("entry_snapshot") or {}).get("touch_paths") \
        or (task.get("plan") or {}).get("touch_paths") or []
    live = set(uncommitted_paths(root))
    conflicts = []
    for _path, other in _iter_task_records(root):
        other_id = other.get("id")
        if not other_id or other_id == task_id:
            continue
        if other.get("status") == "archived" or other.get("terminal"):
            continue
        wip = ((other.get("handoff") or {}).get("wip") or {})
        if wip.get("resolved"):
            continue
        for path in wip.get("paths") or []:
            if path not in live:
                continue
            if any(paths_mod.match_path(pattern, path) for pattern in touch_paths):
                conflicts.append({"path": path, "claimed_by": other_id})
    return conflicts


def attributed_by_other_tasks(root, task_id, start):
    """其它任务显式归属的路径（用于识别跨任务冲突认领）。"""
    found = set()
    for _path, task in _iter_task_records(root):
        other = task.get("id")
        if not other or other == task_id:
            continue
        found.update(attributed_paths(root, other, task.get("baseline_head")))
    return found


def _iter_task_records(root):
    from . import tasks as tasks_mod

    return tasks_mod.iter_tasks(root)


def external_changes(root, task):
    """从任务基线到 HEAD 中触及批准触碰面却无本任务归属的提交。"""
    baseline = task.get("baseline_head")
    if not baseline:
        return {"baseline": None, "commits": []}, []
    commits = commits_since(root, baseline)
    if commits is None:
        return {"baseline": baseline, "commits": [], "unreachable": True}, []
    touch_paths = (task.get("entry_snapshot") or {}).get("touch_paths") or []
    findings = []
    for sha in commits:
        message = commit_message(root, sha)
        if commit_trailer_task(message) == task.get("id"):
            continue
        changed = commit_paths(root, sha) or []
        relevant = [path for path in changed if any(paths_mod.match_path(pattern, path) for pattern in touch_paths)]
        if relevant:
            findings.append(
                {
                    "commit": sha,
                    "paths": relevant,
                    "task_trailer": commit_trailer_task(message),
                }
            )
    return {"baseline": baseline, "commits": findings}, findings


def workspace_groups(root, task):
    """工作区分类：用于开工/换对象/释放前的边界核对。"""
    return classify_candidates(root, task)
