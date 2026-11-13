"""authorize.py — K6 五类不可逆动作的确认与"授权原件脱敏入库"（v42 K6 / S7）。

五类动作（一次确认绑定变化摘要）：① 提交/推送；② 删除数据；③ 外发内容；
④ 越出批准面的修改（先确认后改）；⑤ 仓库级规则文件（集合由 `protocol/repo_rules.json` 声明）。

两条性质：
- **授权是可审计凭证**：脱敏后的确认原件进 **committed**（任务目录），敏感原文留 runtime；
- **脱敏是单向不变量**：口径唯一来自 `protocol/redaction.json`，只可加严（`redaction.baseline.json`
  由不变量⑥守护），本模块不另立一份规则表。
"""

from __future__ import annotations

import os

from . import paths as paths_mod
from . import protocol as protocol_mod
from . import records

ACTIONS = {
    "commit": "提交 / 推送",
    "delete": "删除数据",
    "export": "外发内容",
    "expand": "越出批准面的修改（先确认后改）",
    "repo_rules": "仓库级规则文件",
}

# 入库保留项 = `protocol/redaction.json` 中 `effect=keep` 的语义标签在代码里的字段映射。
# 其余字段（含未知字段、嵌套字典、明细清单）一律丢弃并留下 `dropped_keys`——黑名单做不到
# "未知字段不泄漏"，dogfood 里 `quote` 与嵌套字典的敏感原文就是这样进 committed 的。
KEEP_SCALAR_KEYS = (
    # 动作类型 / 决策取值
    "action", "choice", "decision", "verdict",
    # 路径清单或变化摘要（含人写的变化理由：属"可审计凭证"的一部分，入库前同样过遮罩）
    "paths", "path", "subject", "changes", "target", "target_task", "reason",
    # 时间 / 人
    "at", "time", "by", "source",
    # 摘要类（协议明确允许：记录内保留 digest 与要点）
    "object_digest", "original_digest", "scope_digest",
)
QUOTE_KEYS = ("quote",)
QUOTE_MAX_CHARS = 500

# 外发授权绑定的材料类集合（机制稿 §9.1：diff / 需求 / 测试结果三类）
EXPORT_MATERIALS = ("diff", "requirement", "test_results")


def is_repo_rule(ctx, path):
    """是否命中仓库级规则文件集合（集合只来自 protocol，不在代码里另写一份）。"""
    for pattern in protocol_mod.repo_rules()["patterns"]:
        if str(path) == pattern or paths_mod.match_path(pattern, str(path)):
            return True
    return False


def repo_rule_paths(ctx, paths):
    return sorted(path for path in paths or [] if is_repo_rule(ctx, path))


def _kept_value(key, value):
    """单字段的保留形态：标量/路径清单原样（过遮罩），quote 只留摘要，其余 None（丢弃）。"""
    from . import check as check_mod

    if key in QUOTE_KEYS:
        text = check_mod.redact_text(str(value or ""))
        if len(text) > QUOTE_MAX_CHARS:
            return text[:QUOTE_MAX_CHARS] + "…<truncated>"
        return text
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return check_mod.redact_text(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [check_mod.redact_text(item) for item in value]
    return None


def redact(decision):
    """按 `protocol/redaction.json` 的 `keep` 口径产出可入库副本，并给出原文摘要。

    采用**保留白名单**：只有 `KEEP_SCALAR_KEYS` 与 `QUOTE_KEYS` 里的字段可能入库，
    其余（含未知字段、嵌套结构、明细清单）一律丢弃并在 `redaction.dropped_keys` 留痕。
    所有保留字符串都过遮罩；`quote` 只留摘要（截断 + 遮罩）。
    """
    decision = decision if isinstance(decision, dict) else {}
    kept = {}
    dropped = []
    for key, value in decision.items():
        if key not in KEEP_SCALAR_KEYS and key not in QUOTE_KEYS:
            dropped.append(key)
            continue
        transformed = _kept_value(key, value)
        if transformed is None:
            dropped.append(key)
            continue
        kept[key] = transformed
    original_digest = records.H("wf-authorization-original-v1", decision)
    kept["original_digest"] = original_digest
    kept["redaction"] = {"source": "protocol/redaction.json",
                         "mode": "keep-allowlist",
                         "dropped_keys": sorted(set(dropped)),
                         "when": records.now_str()}
    return kept, original_digest


def export_scope(task_id, materials):
    """外发授权的范围身份：任务 + 材料类集合（目的地由任务与暂存根派生，不单列）。

    授权入库只保存这个 digest（协议允许保留摘要），比较时用当前意图重算：
    旧授权给另一个任务、或材料类集合变了（新增一类材料），都不再匹配。
    """
    return records.H("wf-export-scope-v1", {"task": str(task_id),
                                            "materials": sorted(str(item) for item in materials or [])})


def export_scope_problems(task_dir, task_id, materials):
    """`review-launch` 的前置：已入库的外发授权必须覆盖**本次**任务与材料类集合。"""
    payload = require(task_dir, "export")
    if payload is None:
        return [{"reason": "本次审查要把材料外发，但缺外发动作的确认（K6 第 3 类）",
                 "missing_action": "export",
                 "exits": ["人执行 `wf authorize record --task <id> --file <决定.json>`，"
                           "文件里写一条 choice=export 的确认（task + materials + 人 + quote）后重跑",
                           "改用不外发的审阅方式（例如同机只读审阅）"]}]
    declared = payload.get("scope_digest")
    if not declared:
        return [{"reason": "外发确认没有绑定范围（缺 scope_digest）：不能用于本次外发",
                 "recorded": sorted(payload),
                 "exits": ["重新记录一条带 task + materials 的 export 确认（旧确认只覆盖当时未细分的类别）"]}]
    expected = export_scope(task_id, materials)
    if declared != expected:
        return [{"reason": "外发确认的范围与本次不一致（任务或材料类集合不同）",
                 "recorded_scope": declared, "current_scope": expected,
                 "current_task": str(task_id), "current_materials": sorted(materials or []),
                 "exits": ["为本任务/本次材料类集合重新记录一条 export 确认",
                           "缩小本次材料范围到已授权集合内"]}]
    return []


def authorization_path(task_dir, action):
    return os.path.join(str(task_dir), f"authorization-{action}.json")


def export_decision_problems(decision):
    """外发确认的形状：必须写明本任务与材料类集合（这是"本次范围"的可核对事实）。"""
    problems = []
    if not str((decision or {}).get("task") or "").strip():
        problems.append({"reason": "export authorization must name the task",
                         "field": "task"})
    materials = (decision or {}).get("materials")
    if not isinstance(materials, list) or not materials:
        problems.append({"reason": "export authorization must list the material classes",
                         "field": "materials", "known": list(EXPORT_MATERIALS)})
    else:
        unknown = sorted({str(item) for item in materials} - set(EXPORT_MATERIALS))
        if unknown:
            problems.append({"reason": "unknown material class in export authorization",
                             "unknown": unknown, "known": list(EXPORT_MATERIALS)})
    return problems


def record_authorization(task_dir, action, decision, *, raw_copy_dir=None):
    """写脱敏原件到**任务目录（committed）**；敏感原文只留在 runtime（若调用方给了目录）。"""
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")
    redacted, digest = redact(decision)
    redacted["action"] = action
    redacted["action_zh"] = ACTIONS[action]
    if action == "export":
        problems = export_decision_problems(decision)
        if problems:
            raise ValueError(f"export authorization is incomplete: {problems}")
        redacted["scope_digest"] = export_scope(decision.get("task"), decision.get("materials") or [])
    path = authorization_path(task_dir, action)
    records.write_json(path, redacted)
    if raw_copy_dir:
        os.makedirs(raw_copy_dir, exist_ok=True)
        records.write_json(os.path.join(str(raw_copy_dir), f"authorization-{action}.raw.json"), decision)
    return {"path": path, "digest": digest, "redacted": redacted}


def require(task_dir, action):
    """读取已入库的授权（脱敏副本）；缺失即阻断，并给出"要补哪一类确认"的出口。"""
    path = authorization_path(task_dir, action)
    payload = records.load_json(path)
    if payload is None:
        return None
    if payload.get("action") != action:
        return None
    return payload


def _pattern_hits(pattern, root):
    """该模式在仓库里能不能落到任何实际文件（glob 展开是否为空）。"""
    if root is None:
        return True                       # 没给仓库根就不判空，保持旧行为
    from . import scope as scope_mod

    listed = None
    try:
        # 已跟踪 + 未跟踪（`.wf/out-of-scope` 语义：新文件也是真实存在的区域）。
        # 只查已跟踪时，对"本任务即将新增的文件"登记的扩面永远匹配不到，等于不可用。
        _code, listed = scope_mod.git(root, "-c", "core.quotePath=false",
                                      "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        files = [item for item in (listed or "").split("\x00") if item] if listed else []
    except Exception:
        files = []
    if not files:
        for base, _dirs, names in os.walk(str(root)):
            for name in names:
                files.append(os.path.relpath(os.path.join(base, name), str(root)).replace(os.sep, "/"))
    from . import paths as paths_mod

    return any(paths_mod.match_path(str(pattern), item) for item in files)


def covers(task_dir, action, paths, *, root=None):
    """已入库的确认是否覆盖这些路径（K6 第 2/4 类：删除数据、越出批准面的修改）。

    返回 `(covered: bool, uncovered: list)`：路径按 glob 匹配确认里登记的路径；
    没有确认文件时整批未覆盖（不猜"大概是这个意思"）。
    """
    payload = require(task_dir, action)
    if payload is None:
        return False, sorted(paths or [])
    declared = []
    for key in ("paths", "path", "subject", "changes"):
        value = payload.get(key)
        if isinstance(value, str):
            declared.append(value)
        elif isinstance(value, list):
            declared.extend(str(item) for item in value
                            if isinstance(item, (str, dict)))
    declared = [item.get("path") if isinstance(item, dict) else item for item in declared]
    declared = [str(item) for item in declared if item]
    # 展开为空的模式视为**确认不可用**：人确认了一片不存在的区域，不能算覆盖
    broken = [pattern for pattern in declared if not _pattern_hits(pattern, root)]
    usable = [pattern for pattern in declared if pattern not in broken]
    uncovered = [path for path in paths or []
                 if not any(path == pattern or paths_mod.match_path(pattern, path)
                            for pattern in usable)]
    return (not uncovered and not broken), sorted(uncovered)
