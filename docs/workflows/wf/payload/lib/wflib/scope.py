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
    # `-z`：普通按行读取会把带引号/制表符/换行的路径转义，归属与外部变更都会漏核（第十八轮复审 N18-4）
    code, out = git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", "--no-renames", sha)
    if code != 0:
        return None
    return [item for item in out.split("\0") if item]


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
    # 两种写法（字面/通配）走同一枚举：判据是"治理 pattern 命中的真实文件也被触碰面命中"，
    # 分支差异不改变行为，故合并为一条路径（2026-11-05 第九轮复审：去掉冗余分支）。
    for pattern in block["paths"]:
        for actual in tree:
            if not paths_mod.match_path(pattern, actual):
                continue
            for touch in touch_paths or []:
                if paths_mod.match_path(touch, actual):
                    return "true", {"fact": "witnessed", "path": actual, "governance": pattern}
    for governance_pattern in block["paths"]:
        for touch in touch_paths or []:
            if not paths_mod.provably_disjoint(governance_pattern, touch):
                return "true", {"fact": "prefix-unexcluded", "governance": governance_pattern, "touch": touch}
    return "false", {"fact": "disjoint"}


# 契约面（复杂度条件②）：改这些文件就改变框架对外行为（设计稿 §4.3 ②）
CONTRACT_SURFACE = (".wf/bin/**", ".wf/lib/**", ".wf/templates/**", ".wf/workflows/**")
# 验收口径来源（复杂度条件③）：这些是"验收口径/回退方案/审查面"的载体
# 只收「验收口径的载体」：改 spec 正文属知识更新，不等于验收口径变化（设计稿 §4.3 ③说的是"变化"）；
# 验收 id 集合变化另由调用方作为事实传入（tasks._complexity_proposal）。
ACCEPTANCE_SURFACE = (".wf/baseline.md", ".wf/project-config.json")
# AGENTS.md 的托管块属于②（安装器写入的流程路由块，改它就改变 AI 路由行为）
AGENTS_BLOCK_MARKER = "TRELLIS:START"


def _overlaps(pattern, touch):
    return not paths_mod.provably_disjoint(pattern, touch)


def contract_surface_condition(root, touch_paths, declared=None):
    """条件②：触碰面命中契约面，或 Plan 显式声明 contract_changes。"""
    if declared:
        return "true", {"fact": "declared", "contract_changes": list(declared)}
    for touch in touch_paths or []:
        for pattern in CONTRACT_SURFACE:
            if _overlaps(pattern, touch):
                return "true", {"fact": "contract-surface", "pattern": pattern, "touch": touch}
        if _overlaps("AGENTS.md", touch):
            path = os.path.join(root, "AGENTS.md")
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError:
                text = ""
            if AGENTS_BLOCK_MARKER in text:
                return "true", {"fact": "agents-managed-block", "touch": touch}
    return "false", {"fact": "no-contract-surface"}


def acceptance_surface_condition(root, touch_paths, acceptance_changed=None):
    """条件③：触碰验收口径来源，或（再次批准时）验收 id 集合发生变化。"""
    if acceptance_changed:
        return "true", {"fact": "acceptance-changed", "detail": acceptance_changed}
    for touch in touch_paths or []:
        for pattern in ACCEPTANCE_SURFACE:
            if _overlaps(pattern, touch):
                return "true", {"fact": "acceptance-surface", "pattern": pattern, "touch": touch}
    return "false", {"fact": "no-acceptance-surface"}


def expansion_condition(previous_touch_paths, touch_paths):
    """条件④：再次批准时触碰面覆盖上一版批准面之外的路径。"""
    previous = list(previous_touch_paths or [])
    if not previous:
        return "false", {"fact": "no-previous-approval"}
    for touch in touch_paths or []:
        if not any(not paths_mod.provably_disjoint(old, touch) for old in previous):
            return "true", {"fact": "scope-expanded", "touch": touch, "previous": previous}
    # 新面覆盖了旧面没覆盖到的具体路径也视为扩张（用旧面里已批准的路径反查不含 touch 时的情形略过：
    # 这里只判"新增条目未被旧面包含"，宁高不低）
    return "false", {"fact": "within-previous"}


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


GITIGNORE_BEGIN = "# wf-managed-v1"
GITIGNORE_END = "# wf-managed-end"


def _gitignore_is_framework_only(root):
    """`.gitignore` 若只含安装器托管段（未被人改动），属框架控制面。

    背景（2026-11-08 R1 回归）：全新安装会新建 `.gitignore`，它是未跟踪文件；
    若按普通业务文件归类，第一次 Check 就会把它报成"未归属改动"。
    唯一判据是**内容**：去掉托管段后必须没有其它行——用户自行加过内容时不隐藏。
    """
    if not root:
        return False
    try:
        with open(os.path.join(str(root), ".gitignore"), "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return False
    if GITIGNORE_BEGIN not in text or GITIGNORE_END not in text:
        return False
    rest = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == GITIGNORE_BEGIN:
            inside = True
            continue
        if stripped == GITIGNORE_END:
            inside = False
            continue
        if not inside and stripped:
            rest.append(stripped)
    return not rest


def _is_control_record(path, task_id, installed=None, root=None):
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
    if path == ".gitignore" and _gitignore_is_framework_only(root):
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


# K5：框架自有资产（`vendor`）。它不进交付面、不进审查材料、不进业务提交；
# 它的改动只作为 `vendor_dirty` 事实记录，不参与归属/范围/检查结论。
VENDOR_PREFIX = ".wf/"


def is_vendor(path):
    return str(path).startswith(VENDOR_PREFIX)


def is_vendor_asset(path, root=None):
    """框架自有资产：`.wf/**` 里**不属项目数据**的部分。

    只按 `.wf/` 前缀判会把 `.wf/spec/**`、`.wf/tasks/**`、`.wf/baseline.md` 等项目数据
    一起打成 vendor；分类器与交付集合必须用同一个口径，否则"归属正确但交付集合为空"。
    """
    return is_vendor(path) and not is_project_data(path, root)


def vendor_paths(paths):
    return sorted(path for path in paths or [] if is_vendor(path))


def _exclusion_records(task):
    """任务记录里的外来改动排除（`execution.workspace_exclusions`，append-only）。"""
    entries = ((task.get("execution") or {}).get("workspace_exclusions") or [])
    return [item for item in entries if isinstance(item, dict) and item.get("path")]


def _fingerprint_item(root, path):
    from . import fingerprint

    try:
        item = fingerprint.item(root, path)
    except OSError:
        return None
    return item


def load_exclusion_declarations(path):
    """读排除声明文件（对象或数组）并校验：`(entries, problems)`。"""
    if not path:
        return [], []
    try:
        payload = records.load_json(path)
    except (OSError, records.RecordInvalid) as exc:
        return [], [{"reason": f"workspace exclusion file unreadable: {exc}", "path": str(path)}]
    if payload is None:
        return [], [{"reason": "workspace exclusion file missing", "path": str(path)}]
    items = payload if isinstance(payload, list) else [payload]
    return exclusion_entries(items)


def exclusion_entries(decisions):
    """从决定文件里取外来改动排除声明：`(entries, problems)`。

    形状：`{choice: <workspace_exclusion 域>, paths: [路径…], reason, by, at, quote, source}`。
    路径必须是**具体路径**（不接受 glob）：摘要在记录时按当时内容固定，glob 无法绑定内容。
    人的确认按乙口径校验（`by=human:<来源>` + `source=user-declared`）：AI 自述不被接受。
    """
    from . import attestation as attestation_mod
    from . import decisions as decisions_mod

    entries, problems = [], []
    for index, decision in enumerate(decisions or []):
        if not isinstance(decision, dict):
            problems.append({"reason": "排除声明必须是对象（数组元素逐个校验）", "index": index})
            continue
        if not decisions_mod.accepts("workspace_exclusion", decision.get("choice")):
            # 文件是以 `--workspace-exclusion` 显式传入的：不能把"认不出的 choice"当成"没有声明"，
            # 否则排除被静默忽略、阻断却仍复现，人只能猜哪里写错了。
            problems.append({"reason": "排除声明的 choice 不在登记域内",
                             "choice": decision.get("choice"),
                             "known": list(decisions_mod.domain("workspace_exclusion"))})
            continue
        paths = decision.get("paths")
        if not isinstance(paths, list) or not paths:
            problems.append({"reason": "排除声明需要 paths 列表", "choice": decision.get("choice")})
            continue
        for path in paths:
            if not isinstance(path, str) or not path.strip():
                problems.append({"reason": "排除声明的 paths 只接受非空字符串"})
                continue
            if any(mark in path for mark in ("*", "?", "[")):
                problems.append({"reason": "排除声明只接受具体路径（不接受 glob）", "path": path})
                continue
            entries.append({"path": path.strip(), "reason": decision.get("reason"),
                            "by": decision.get("by"), "at": decision.get("at"),
                            "quote": decision.get("quote"), "source": decision.get("source")})
        for problem in attestation_mod.problems_of(
                {key: decision.get(key) for key in ("by", "at", "quote", "source")},
                action="workspace.exclude"):
            problems.append(problem)
    return entries, problems


def exclusion_records(root, classified, entries, *, now=None):
    """把排除声明落成**摘要绑定**的记录：路径必须当前在 c 桶（未归属未提交）。

    幂等：同一路径已按**相同摘要**排除时不再重复写入（重跑同一声明照常成功）。
    """
    c_paths = set(classified["buckets"].get("c") or [])
    already = {item["path"]: item
               for item in (classified.get("exclusions") or {}).get("applied") or []}
    # 同一路径在声明里出现多次：后者覆盖前者（按路径收敛），不写重复记录
    from . import check as check_mod

    deduped = {}
    for entry in entries:
        deduped[entry["path"]] = entry
    records_out, problems = [], []
    entries = list(deduped.values())
    for entry in entries:
        path = entry["path"]
        item = _fingerprint_item(root, path)
        if not item:
            problems.append({"reason": "无法读取该路径的当前内容摘要", "path": path})
            continue
        current = {"exists": item.get("exists"), "digest": item.get("digest")}
        if path not in c_paths:
            existing = already.get(path)
            if existing and existing.get("saved") == current:
                continue
            problems.append({
                "reason": "排除只适用于未归属的未提交路径；该路径不在 c 桶",
                "path": path,
                "exits": ["核对路径拼写与真实状态",
                          "该路径若属本任务：未提交的按批准触碰面归属；已提交的用 task-attribute --commit <sha> 裁决",
                          "若属其他任务：先按其他任务收工/交接处置"]})
            continue
        # 人的确认原话按脱敏协议只留**摘要**：入库的是遮罩+截断后的文本，
        # `attestation_digest` 固定原文，事后可核对但不把潜在敏感值带进 committed。
        raw_quote = str(entry.get("quote") or "")
        records_out.append({
            "path": path,
            "exists": current["exists"],
            "digest": current["digest"],
            "reason": entry.get("reason"),
            "by": entry.get("by"),
            "at": entry.get("at"),
            "source": entry.get("source"),
            "quote": check_mod.redact_text(raw_quote)[:300],
            "attestation_digest": records.H("wf-exclusion-attestation-v1",
                                            {"by": entry.get("by"), "at": entry.get("at"),
                                             "quote": raw_quote, "source": entry.get("source")}),
            "recorded_at": now or records.now_str(),
        })
    return records_out, problems


def persist_exclusions(task, new_records):
    """写入任务记录（同路径以最新记录替换，其余保留；append-only 语义按路径收敛）。"""
    execution = task.setdefault("execution", {})
    existing = list(execution.get("workspace_exclusions") or [])
    replaced = {item["path"] for item in new_records}
    kept = [item for item in existing
            if isinstance(item, dict) and item.get("path") not in replaced]
    execution["workspace_exclusions"] = kept + list(new_records)
    return task


def exclusion_states(root, task):
    """逐条重算排除事实：`applied`（摘要仍匹配）/`lapsed`（内容已变，排除失效）。"""
    applied, lapsed = [], []
    for record in _exclusion_records(task):
        item = _fingerprint_item(root, record["path"])
        current = {"exists": item.get("exists"), "digest": item.get("digest")} if item else {}
        saved = {"exists": record.get("exists"), "digest": record.get("digest")}
        entry = {"path": record["path"], "saved": saved, "current": current,
                 "reason": record.get("reason")}
        if item and current == saved:
            applied.append(entry)
        else:
            lapsed.append(entry)
    return {"applied": applied, "lapsed": lapsed}


def classify_candidates(root, task, receipts=None):
    """返回 {a: [...], b: [...], c: [...], d: [...], e: [...], f: [...], facts...}。"""
    task_id = task.get("id")
    # 与写入口同一判定（2026-11-05 第七轮复审 F7-3）：未开工回退 plan，已开工一律以快照为准，
    # 快照缺失/类型不符抛 WF_RECORD_INVALID，不在本函数里另写一套回退口径。
    from . import tasks as tasks_mod
    touch_paths = tasks_mod.approved_touch_paths(task)
    entry = task.get("entry_snapshot") or {}
    uncommitted = uncommitted_paths(root)
    attributed = set(attributed_paths(root, task_id, task.get("baseline_head")))
    attributed |= set(attributed_by_decision(root, task))
    candidates = sorted(set(uncommitted) | attributed)
    installed = installed_asset_paths(root)
    # 归属语义存疑（机制稿 §3.5 d 档）：命中批准触碰面、却被**另一个任务**显式登记为未处置 WIP。
    # 判定只有一处实现（本函数调 `cross_task_conflicts`），不在这里另写一套争抢判定。
    conflicts = cross_task_conflicts(root, task, touch_paths)
    claimed_by = {}
    for item in conflicts:
        claimed_by.setdefault(item["path"], []).append(item.get("claimed_by"))
    buckets = {"a": [], "b": [], "c": [], "d": [], "e": [], "f": [], "v": [], "x": []}
    receipt_paths = set()
    for receipt in receipts or []:
        if receipt["state"] in ("applied_pending_commit", "pending_check"):
            receipt_paths.update(receipt["facts"].get("paths") or [])
    for path in candidates:
        # 顺序要紧：记录/维护组（a/b）先判——`.wf/tasks/**`、`.wf/baseline.md` 是项目数据，
        # 不是框架自有资产；先判 vendor 会把记录一起打成 vendor（演练实测：归档提交被自己挡住）。
        if path in receipt_paths:
            buckets["a"].append(path)
            continue
        if _is_control_record(path, task_id, installed, root):
            buckets["b"].append(path)
            continue
        if is_vendor(path) and not is_project_data(path):
            # K5：框架自有资产不进交付面/审查/业务提交；**项目数据**（`.wf/spec/**` 等）照常参与分类
            buckets["v"].append(path)
            continue
        if path in claimed_by:
            # 先判存疑再判归属：宽 glob 命中不能覆盖他任务已显式登记的归属（机制稿 §3.3）
            buckets["d"].append(path)
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
    # 人确认「这些外来改动不属于本任务、保持原样」的记录：只把**摘要仍匹配**的路径从 c 移到 x。
    # 内容一变即失配 → 路径回到 c（排除不是永久豁免），x 不进交付/指纹/材料/提交面。
    exclusions = exclusion_states(root, task)
    applied_paths = {item["path"] for item in exclusions["applied"]}
    if applied_paths:
        buckets["x"] = sorted(path for path in buckets["c"] if path in applied_paths)
        buckets["c"] = [path for path in buckets["c"] if path not in applied_paths]
    return {
        "buckets": buckets,
        "candidates": candidates,
        "touch_paths": touch_paths,
        "entry_snapshot": entry,
        "vendor_dirty": buckets["v"],
        "exclusions": exclusions,
        # d 档的展开事实（谁在争抢）：交人裁决时要看到双方，不能只给一个裸路径
        "conflicts": conflicts,
    }


def delivery_set(root, task, receipts=None, classified=None):
    """本任务**交付集合**的唯一实现：内容域（指纹、审查材料、待提交面共用）。

    构成（机制稿 §3.5 的真实触碰路径口径）：
    - `e` 桶：归属本任务且命中批准触碰面；
    - 已由 `expand` 确认覆盖的 `f` 桶路径（先确认后改，K6 第 4 类）；
    - 未释放的策展路径（任务声明要读/改的 spec）；
    - `.wf/baseline.md` / `.wf/project-config.json`（存在即入锚点输入）。

    `uncovered_f` 原样返回，由 Check 继续按 `WF_SCOPE_VIOLATION` 阻断；本函数不改判定，
    只保证"哪些路径算本任务交付"只有一处口径（此前 object_paths 取 e、材料取 e∪f，
    扩面路径因此可能进材料却不进内容指纹）。
    """
    from . import authorize as authorize_mod
    from . import tasks as tasks_mod

    if classified is None:
        if receipts is None:
            receipts = tasks_mod.task_receipts(root)
        classified = classify_candidates(root, task, receipts=receipts)
    buckets = classified["buckets"]
    in_scope = sorted(path for path in (buckets.get("e") or []) if not is_vendor_asset(path, root))
    out_of_scope = sorted(path for path in (buckets.get("f") or []) if not is_vendor_asset(path, root))
    covered, uncovered = [], list(out_of_scope)
    if out_of_scope:
        directory = tasks_mod.task_dir(root, task.get("id"))
        if directory:
            _ok, uncovered = authorize_mod.covers(directory, "expand", out_of_scope, root=root)
            covered = sorted(set(out_of_scope) - set(uncovered))
    paths = set(in_scope) | set(covered)
    for entry in task.get("curation") or []:
        if entry.get("released") or not entry.get("path"):
            continue
        if not is_vendor_asset(entry["path"], root):
            paths.add(entry["path"])
    for fixed in (".wf/baseline.md", ".wf/project-config.json"):
        if os.path.exists(join(root, fixed)):
            paths.add(fixed)
    return {
        "paths": sorted(paths),
        "buckets": {
            "e": in_scope,
            "f": out_of_scope,
            "covered_f": covered,
            "uncovered_f": sorted(uncovered),
            "v": list(buckets.get("v") or []),
        },
        "candidates": classified.get("candidates") or [],
    }


def _wip_path_strings(items):
    """把 `handoff.wip.paths` 的指纹对象/字符串统一成路径字符串。"""
    paths = []
    for item in items:
        if isinstance(item, str):
            paths.append(item)
        elif isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]))
    return paths


def cross_task_conflicts(root, task, touch_paths=None):
    """活冲突：当前未提交的路径被**另一个任务显式记为 WIP**（停/交接时保存的指纹）。

    历史提交曾改过同一文件不等于永久拥有它（机制稿 §3.3）：只有另一任务明确留下
    `handoff.wip.paths` 声明"这些改动我还没处置"时，才算当前争抢。

    `touch_paths` 由调用方传入时**直接使用**，不再自行重算：批准触碰面只推导一次，
    否则同一判定在两处各算一遍，注入点也会被第二处掩盖（`f7-3` 的双模探针因此失效）。
    """
    task_id = task.get("id")
    from . import tasks as tasks_mod

    if touch_paths is None:
        touch_paths = tasks_mod.approved_touch_paths(task)
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
        # `handoff.wip.paths` 存的是 fingerprint.item() 的对象（stop 写入），也可能是字符串；
        # 直接拿对象做集合判断会抛 unhashable type: 'dict'（第十三轮复审 F13-1）。
        for path in _wip_path_strings(wip.get("paths") or []):
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
    from . import tasks as tasks_mod

    touch_paths = tasks_mod.approved_touch_paths(task)
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


def is_project_data(path, root=None):
    """该路径属**项目数据**（任务记录/项目自己的 spec/安装记录/基线/配置），不是框架自有资产。

    集合来自 `protocol.project_data()`，代码里不另写前缀清单——前缀清单一度漏了 `.wf/spec/`，
    那类洞只能靠"声明表"堵住。
    """
    from . import protocol as protocol_mod

    data = protocol_mod.project_data()      # protocol 目录由加载器自己定位，不传项目根
    text = str(path)
    return text.startswith(tuple(data["prefixes"])) or text in tuple(data["files"])


def vendor_assets(root, task, paths):
    """提交面里的**框架自有资产**：`.wf/**` 且不属于本任务控制记录/维护组。

    归档提交要带上 `.wf/tasks/**`、`.wf/baseline.md` 等项目数据，它们不是 vendor；
    只看前缀会把记录一起挡住。
    """
    task_id = (task or {}).get("id")
    installed = installed_asset_paths(root)
    # 项目数据（不是框架自有资产）：任务记录、基线、项目配置、安装记录
    # 项目数据（不是框架自有资产）：任务记录、**项目自己的 spec**、安装记录。
    # `.wf/spec/**` 由 spec.update 写入、不被升级覆盖（实现方案 §"项目数据落点表"），
    # 漏了它会让初始化任务与日常 spec 更新都归不了档。
    task_id = (task or {}).get("id")
    installed = installed_asset_paths(root)
    found = []
    for path in paths or []:
        if not is_vendor_asset(path, root):    # 项目数据不算框架自有资产
            continue
        if _is_control_record(path, task_id, installed, root):
            continue
        found.append(path)
    return sorted(found)
