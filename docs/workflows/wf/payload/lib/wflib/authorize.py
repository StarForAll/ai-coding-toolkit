"""authorize.py — K6 五类不可逆动作的确认与"授权原件脱敏入库"（v42 K6 / S7）。

五类动作（一次确认绑定变化摘要）：① 提交/推送——确认通道是 finish 决定的
`commit_grants`（tasks.py 唯一口径），不经本模块；② 删除数据；③ 外发内容；
④ 越出批准面的修改（先确认后改）；⑤ 仓库级规则文件（集合由 `protocol/repo_rules.json` 声明；该类是环境级规则变更确认——确认的是对后续任务行为环境的影响，不等于动作本身不可逆）。
本模块只承载②③④⑤的确认文件（`authorization-<action>.json`）。

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
    "delete": "删除数据",
    "export": "外发内容",
    "expand": "越出批准面的修改（先确认后改）",
    "repo_rules": "环境级规则变更（仓库级规则文件）",
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


def mask_quote(value):
    """人的原话入库形态（遮罩 + 截断）：授权、抽样与规模确认共用一处。

    机制稿 §1.3 对"人的原话"的要求是遮罩+截断摘要；`authorize` 与 `sampling`
    都存人的 quote，不能只有一处做遮罩。
    """
    from . import check as check_mod

    text = check_mod.redact_text(str(value or ""))
    if len(text) > QUOTE_MAX_CHARS:
        return text[:QUOTE_MAX_CHARS] + "…<truncated>"
    return text

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
        return mask_quote(value)
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


def record_authorization(task_dir, action, decision, *, raw_copy_dir=None, root=None):
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
        redacted["materials"] = sorted(str(item) for item in decision.get("materials") or [])
        redacted["scope_digest"] = export_scope(decision.get("task"), decision.get("materials") or [])
    if action in ("repo_rules", "delete") and root is not None:
        # 确认时尝试内容绑定的模式清单（十六轮 a-1）：covers 用它区分
        # "缺摘要 = legacy 路径级"与"缺摘要 = 确认后新增的匹配文件"——
        # 后者承诺了内容绑定，须重新 record 才覆盖，不得按 legacy 放行。
        _bound_patterns = sorted({str(item)
                                  for key in ("paths", "path")
                                  for item in (_as_list_value(decision.get(key)))})
        if _bound_patterns:
            redacted["content_bound_patterns"] = _bound_patterns
        # 内容绑定（2026-11-21 六轮审查 a-2）：按确认时的具体文件内容摘要留档——
        # 归档守卫对比当前内容，同一路径后续改动不再被旧确认覆盖（环境级变更逐次确认）。
        digests = {}
        raw_paths = decision.get("paths")
        candidates = ([raw_paths] if isinstance(raw_paths, str) else
                      list(raw_paths) if isinstance(raw_paths, list) else [])
        for pattern in candidates:
            if not isinstance(pattern, str):
                continue
            for hit in _concrete_hits(pattern, root):
                from . import records as _records_mod

                rel = os.path.relpath(hit, str(root)).replace(os.sep, "/")
                # a 组 a-4 记录侧同批统一：内容留档的读取归因也走 file_digest_state
                # （C1 唯一实现）——missing/unreadable 均 None＝未绑内容，记录侧本就
                # 不区分两态，但不再在第二处内联解释 OSError。
                digest, _cause, _reason = _records_mod.file_digest_state(hit)
                digests[rel] = digest
        redacted["content_digests"] = digests
    path = authorization_path(task_dir, action)
    # 每次确认的范围—原话留痕（十二轮 P2-2）：顶层 quote/by/at 取最新，
    # record_log 按序保留每次的 {quote, by, at, source, paths, materials}——
    # 路径累积后仍能回答"谁为什么确认了哪条路径"。
    # 十三轮审查 P0-1：log 条目一律取 redact() 之后的值——quote 走同一遮罩+截断，
    # committed 授权文件里不再有第二条未脱敏的原话；by/at/source/paths 同为保留白名单口径。
    _log_entry = {"quote": redacted.get("quote"), "by": redacted.get("by"),
                  "at": redacted.get("at"), "source": redacted.get("source"),
                  "paths": redacted.get("paths") or redacted.get("path"),
                  "materials": redacted.get("materials")}
    _stored = records.load_json(path) or {}
    _existing_log = _stored.get("record_log") or []
    # 上限（十三→十四轮 P2-1/P2-2）：保留最近 20 条**真实条目**；更早的折叠数记顶层
    # `record_log_truncated`（累计、不占窗口、不重复累积）——标记塞列表会让计数错报、
    # 真实条目被挤掉；超限后逐条原话不再保留是**声明边界**（计数可见，见机制稿登记）。
    _truncated_before = int(_stored.get("record_log_truncated") or 0)
    _overflow = max(0, len(_existing_log) - 20)
    if _overflow:
        _existing_log = list(_existing_log[-20:])
    # 十一/十二轮审查：同动作重复授权按**累计**合并——覆盖会让先前的扩面路径
    # 重新变回未归属、delete 丢失已删文件的内容摘要，Check/归档随即阻断。
    existing = records.load_json(path)
    if isinstance(existing, dict) and existing.get("action") == action:
        merged = dict(existing)

        # 路径类键：归一为列表后并集去重（字符串/列表混用同判）
        for key in ("paths", "path", "subject"):
            combined = _as_list_value(existing.get(key)) + _as_list_value(redacted.get(key))
            seen, unique = set(), []
            for item in combined:
                marker = item if isinstance(item, (str, dict)) else str(item)
                if marker in seen:
                    continue
                seen.add(marker)
                unique.append(item)
            merged[key] = unique
        # 内容摘要：并入（新值覆盖同路径）；legacy 记录无该键时从新记录起档——
        # 否则 covers 回退路径级授权，新确认的路径可在确认后被替换内容（十四轮 P1）
        digests = dict(existing.get("content_digests") or {})
        digests.update(redacted.get("content_digests") or {})
        if digests:
            merged["content_digests"] = digests
        # 内容绑定模式（a 组 a-1）：与 digests 同型并集——先确认 `.gitignore` 再确认
        # `requirements-*.txt` 时，旧实现只合并 digests 不合并 patterns，追加确认的
        # 绑定模式丢失，covers 对新增的 `requirements-prod.txt` 按 legacy 路径级放行。
        bound_patterns = sorted(set(_as_list_value(existing.get("content_bound_patterns")))
                                | set(_as_list_value(redacted.get("content_bound_patterns"))))
        if bound_patterns:
            merged["content_bound_patterns"] = bound_patterns
        # export 的材料类并集后**重算范围身份**（十二轮 P1-1：合并不重算
        # scope_digest 会让"追加材料类后再确认"永远无效，出口指向已不成立的动作）
        if action == "export":
            # 十二轮 P1-1：材料类并集后**重算范围身份**；legacy 记录没有 materials
            # 键（无法还原旧集合）→ 新范围整体替换（与 content_digests 的兼容口径一致）
            old_materials = _as_list_value(existing.get("materials"))
            new_materials = _as_list_value(redacted.get("materials"))
            if old_materials:
                materials = sorted(set(old_materials) | set(new_materials))
                merged["materials"] = materials
                merged["scope_digest"] = export_scope(decision.get("task"), materials)
            elif new_materials:
                # legacy 记录没有 materials 键（无法还原旧集合）→ 新范围整体替换
                # （十三轮 P1-3：跳过会让"重新记录一条"永远无效，出口指向不成立的动作）
                merged["materials"] = sorted(new_materials)
                merged["scope_digest"] = export_scope(decision.get("task"), new_materials)
        # 每次确认的范围—原话留痕（十二轮 P2-2：路径累积但原话只留最新，
        # 事后无法回答"谁为什么确认了那条路径"）；顶层 quote/by/at 取最新
        # 顶层凭证字段取最新（十二轮 P2-2：原话留痕进 record_log，顶层 quote/by/at
        # 反映最近一次确认——路径累积后仍能回答"谁为什么确认了哪条路径"）
        merged.update({key: redacted[key] for key in ("quote", "by", "at", "source",
                                                         "original_digest", "redaction")
                       if key in redacted})
        redacted = merged
    # 合并可能整体替换了 redacted（= merged），log 统一在此追加——每次记录都在案；
    # 追加后立即裁窗：存档形态恒为 ≤20 条真实条目 + 顶层累计折叠数。
    _log = list(_existing_log) + [_log_entry]
    if len(_log) > 20:
        _overflow += len(_log) - 20
        _log = list(_log[-20:])
    redacted["record_log"] = _log
    if _truncated_before or _overflow:
        redacted["record_log_truncated"] = _truncated_before + _overflow
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


def _concrete_hits(pattern, root):
    """把确认里的路径模式展开成实际存在的具体文件（相对项目根的绝对路径）。

    通用 glob（2026-11-21 七轮审查 b-3）：`requirements-*.txt`、`docs/**` 等与
    repo_rules.json 同语法的模式都要能展开——只认精确路径或 /** 结尾会让按清单
    原样授权的模式永远拿不到内容摘要，形成"record 成功、归档永远未覆盖"的死循环。
    """
    if root is None:
        return []
    import glob as _glob

    full = os.path.join(str(root), pattern)
    hits = [item for item in _glob.glob(full, recursive=True) if os.path.isfile(item)]
    if not hits and os.path.isfile(full):
        hits = [full]
    return hits


def _as_list_value(value):
    """路径值的列表归一（record/covers 共用）：str→[str]，list→list，None→[]，dict→[dict]。"""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return list(value)
    return [value]


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
    # 展开为空的模式视为**确认不可用**：人确认了一片不存在的区域，不能算覆盖。
    # 例外（八轮审查 P0-1）：删除类 + 内容留档——确认时存在的文件（留了摘要）现在已删，
    # 模式匹配不到是**删除本身的效果**，不算"确认不可用"；否则删除确认永远过不了门禁。
    def _pattern_usable(pattern):
        if _pattern_hits(pattern, root):
            return True
        if action in ("delete", "repo_rules") and "content_digests" in payload:
            # 十六轮 a-2：规则文件"确认后按计划删除"——模式匹配不到是删除本身的效果，
            # 与删除类同型不算"确认不可用"；旧模式留在累计记录不再产生新前置。
            recorded_keys = payload.get("content_digests") or {}
            return any(key == pattern or key.startswith(pattern + "/")
                       or paths_mod.match_path(pattern, key)
                       for key in recorded_keys)
        return False

    broken = [pattern for pattern in declared if not _pattern_usable(pattern)]
    usable = [pattern for pattern in declared if pattern not in broken]
    uncovered = [path for path in paths or []
                 if not any(path == pattern or paths_mod.match_path(pattern, path)
                            for pattern in usable)]
    # 内容绑定（2026-11-21 六轮）：repo_rules/delete 的确认按确认时内容摘要核对——
    # 同一路径在确认之后又改动（或确认时留档缺失）即未覆盖，需按当前内容重新确认。
    # 内容绑定只对**带留档**的确认生效：旧确认（无 content_digests 键）保持原路径级语义，
    # 不追溯失效——新确认一律经 authorize record 落档后即受内容绑定。
    if (action in ("repo_rules", "delete") and not uncovered
            and "content_digests" in payload):
        recorded = payload.get("content_digests") or {}
        from . import records as _records_mod

        for path in sorted(paths or []):
            # a 组 a-4：当前内容的读取走 records.file_digest_state 三态归因（C1 唯一实现）——
            # missing 才是删除例外（确认时存在、当前已删 ⇒ 覆盖）；unreadable 按未覆盖
            # （无法核对即未覆盖），不再把权限/IO 错误折成 None 冒充"已删除"。
            current, cause, _reason = _records_mod.file_digest_state(
                os.path.join(str(root), path))
            if path not in recorded:
                # 缺摘要三档（十五轮 b-2 + 十六轮 a-1）：
                # ① 命中本次确认声明的模式（content_bound_patterns）→ 确认后才出现/才命中的
                #    文件——新确认承诺了内容绑定，须对它重新 record 才覆盖，不得冒充 legacy；
                # ② delete 且当前已删 → 未覆盖（legacy 无摘要的删除必须重新确认）；
                # ③ 其余 → legacy 路径级确认（合并前已授权、当时未绑摘要；不追溯失效）。
                bound_patterns = payload.get("content_bound_patterns") or []
                if any(path == pat or path.startswith(pat + "/")
                       or paths_mod.match_path(pat, path) for pat in bound_patterns):
                    uncovered.append(path)
                elif action == "delete" and current is None:
                    uncovered.append(path)
                continue
            if (current is None and cause == "missing"
                    and action in ("delete", "repo_rules") and recorded[path] is not None):
                # 删除类确认（八轮审查 P0-1）：record 在删除**之前**落档（绑定被删时的内容），
                # "确认时存在、当前已删除"正是被确认的效果——视为覆盖。
                # a-4 后仅 cause == "missing" 走这里；unreadable 落到下面按未覆盖处理。
                continue
            if recorded[path] is None or current is None:
                # 七轮审查 b-2：任何一端读不到即无法核对——按未覆盖处理（需人处置），
                # 不因"读不到"而静默放行；确认端读不到说明授权时就没绑上内容。
                uncovered.append(path)
            elif recorded[path] != current:
                uncovered.append(path)
    return (not uncovered and not broken), sorted(uncovered)
