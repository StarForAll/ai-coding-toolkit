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

# 脱敏规则里"入库保留"与"留 runtime"的项（其余字段一律按 runtime_only 处理）
RUNTIME_ONLY_KEYS = ("content", "content_full", "items", "paths_detail", "secret", "credential",
                     "token", "password", "authorization_header")


def is_repo_rule(ctx, path):
    """是否命中仓库级规则文件集合（集合只来自 protocol，不在代码里另写一份）。"""
    for pattern in protocol_mod.repo_rules()["patterns"]:
        if str(path) == pattern or paths_mod.match_path(pattern, str(path)):
            return True
    return False


def repo_rule_paths(ctx, paths):
    return sorted(path for path in paths or [] if is_repo_rule(ctx, path))


def redact(decision):
    """按 `protocol/redaction.json` 的 `keep` 口径产出可入库副本，并给出原文摘要。

    保留：动作类型、路径清单或变化摘要、决策取值、时间、人、quote 摘要（以及它们的 digest）；
    丢弃：外发内容全文、删除清单明细、凭据类上下文——这些留在 runtime 原件里。
    """
    decision = decision if isinstance(decision, dict) else {}
    kept = {}
    for key, value in decision.items():
        if key in RUNTIME_ONLY_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            kept[key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            kept[key] = list(value)
        elif isinstance(value, dict):
            kept[key] = {k: v for k, v in value.items()
                         if isinstance(v, (str, int, float, bool)) or v is None}
        else:
            kept[key] = f"<omitted:{type(value).__name__}>"
    original_digest = records.H("wf-authorization-original-v1", decision)
    kept["original_digest"] = original_digest
    kept["redaction"] = {"source": "protocol/redaction.json",
                         "dropped_keys": sorted(set(decision) - set(kept)),
                         "when": records.now_str()}
    return kept, original_digest


def authorization_path(task_dir, action):
    return os.path.join(str(task_dir), f"authorization-{action}.json")


def record_authorization(task_dir, action, decision, *, raw_copy_dir=None):
    """写脱敏原件到**任务目录（committed）**；敏感原文只留在 runtime（若调用方给了目录）。"""
    if action not in ACTIONS:
        raise ValueError(f"unknown action: {action}")
    redacted, digest = redact(decision)
    redacted["action"] = action
    redacted["action_zh"] = ACTIONS[action]
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


def covers(task_dir, action, paths):
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
    uncovered = [path for path in paths or []
                 if not any(path == pattern or paths_mod.match_path(pattern, path)
                            for pattern in declared)]
    return (not uncovered), sorted(uncovered)
