"""decisions.py — `Decision.choice` 取值域的唯一登记处（实现稿 §2.3.11 ①）。

机制稿 §1.1 只规定 `Decision` 的**结构**（`{source, at, subject, object_digest, choice, reason}`），
`choice` 的**取值域按操作分别登记在实现稿 §2.3**。此前这些取值以字面量散落在
`tasks.py` / `check.py` 的七处判断里：既没有单一来源，也就无法回答「新加一个近义词算不算改语义」。

本模块只做两件事：

1. **登记**：`DOMAINS` 逐操作列出**当前已被接受**的写法（首项为规范值）。
   增减任何一项都是语义变更，须先回实现稿同批登记，不能在调用点就地加同义词
   （实现稿 §2.3.11 ①「不得据同义词新增语义分支」）。
2. **判定**：`accepts(operation, choice)` 与 `canonical(operation, choice)`，
   调用点不得再写自己的元组比较。

`plan-q` 的答复不在此表：它的身份由 `subject` 里的编号决定（`plan-q-<n>`），
`choice` 写什么都不改变语义，因此它不是取值域问题。
"""

from __future__ import annotations

import re

# 操作名 → 已登记的写法（首项为规范值）。只登记**当前实现已接受**的写法，不新增。
DOMAINS = {
    # 规划批准（`task-approve`、`baseline-apply` 的批准决定、最终门禁的批准复核）
    "plan_approval": ("approve", "批准"),
    # 机械修订（`task-approve` 的等价链路径——a 组 a-2：不经 task-replan）
    "mechanical_revision": ("机械修订",),
    # 实质规划变更（`task-replan --decision` 的必填取值）
    "replan": ("replan", "重新规划"),
    # 收工/归档选择（`stop` 的选择与 `archive` 的 finish 证据）
    "archive_finish": ("finish", "完成", "pass"),
    # 收工选择（机制稿 §4.3 的 `decision` 四值；机制侧 owns 该域，这里只做机读副本）
    "stop_choice": ("commit", "keep", "reverse", "transfer"),
    # 提交授权（`stop`/`archive`/`task-abandon` 的 `commit_grants`）
    "commit_grant": ("commit",),
    # 外部变更「已核对无影响」的人判（Check 的外部提交核对）
    "external_checked": ("已核对无影响", "核对无影响", "checked", "no-impact"),
    # 重复调试裁定（`debug-ruling-<verification_id>-<multiple>`）
    "debug_ruling": ("同一问题", "不同问题"),
    # 验收项结论（Check 的 `acceptance_results[].conclusion` 与人工接受决定）
    "acceptance_conclusion": ("passed", "failed", "pending"),
    # 外来未提交改动的排除（人确认"不属于本任务、保持原样"；路径 + 记录时内容摘要绑定）
    "workspace_exclusion": ("排除外来改动", "exclude-foreign"),
    # 工作流定义准备范围授权（`definition prepare --authorization`）：人授予"可写这些定义路径"的
    # 准备权限；内容本身仍由创建实例时的定义摘要单独确认（设计稿 §5.7）
    "prepare_definition": ("准备定义", "prepare-definition"),
    # 实例创建授权（`run create --authorization`）：人确认"用这个定义版本/输入/步骤适用性创建实例"；
    # 决定里的 `object_digest` 是创建输入的规范摘要（`runs.creation_digest`）
    "create_instance": ("创建实例", "create-instance"),
    # 步骤契约里的必做动作结果（`task-check --decision`，subject 整词含动作 id）：
    # `done` = 该项已做；`waived` = 经人/审查认定本次不适用（理由写在 reason）
    "action_result": ("done", "完成", "waived", "不适用"),
}


class UnknownDomain(Exception):
    """调用点写了未登记的域：宁可报错，也不静默退化成「任意值都接受」。"""


def domain(operation: str) -> tuple:
    try:
        return DOMAINS[operation]
    except KeyError as exc:
        raise UnknownDomain(operation) from exc


def accepts(operation: str, choice) -> bool:
    return choice in domain(operation)


# 同义写法 → 规范值。**只登记"同一含义的不同拼写"**：取值语义彼此不同的域（如
# `stop_choice` 的 commit/keep、`acceptance_conclusion` 的 passed/failed）不在此表，`canonical`
# 对它们返回取值本身。此前实现一律返回登记表首项，于是 `failed` → `passed`、`keep` → `commit`：
# 人工验收的失败结论会被当成通过，spec 核实的失败结论也不会进 unresolved（十轮自审查发现）。
ALIAS_GROUPS = {
    "plan_approval": {"批准": "approve"},
    "replan": {"重新规划": "replan"},
    "archive_finish": {"完成": "finish", "pass": "finish"},
    "commit_grant": {},
    "external_checked": {"核对无影响": "已核对无影响", "checked": "已核对无影响",
                         "no-impact": "已核对无影响"},
    "workspace_exclusion": {"exclude-foreign": "排除外来改动"},
    "prepare_definition": {"prepare-definition": "准备定义"},
    "create_instance": {"create-instance": "创建实例"},
    "action_result": {"完成": "done", "不适用": "waived"},
}


def canonical(operation: str, choice):
    """把已登记的写法归一成规范值；未登记返回 None（调用方据此拒绝并列出可接受值）。

    语义彼此不同的域返回取值本身：`canonical("acceptance_conclusion", "failed") == "failed"`。
    """
    values = domain(operation)
    if choice not in values:
        return None
    return ALIAS_GROUPS.get(operation, {}).get(choice, choice)


SUBJECT_SPLIT = re.compile(r"[\s,，;；、|]+")


def subject_tokens(subject):
    """决定 `subject` 的 token 列表（数组或分隔字符串两种形态，唯一实现）。

    判定"某 id 是否被这份决定覆盖"在四个入口出现过四份实现（正则整词、`re.split` 成员、
    路径切分）——同一判据多处维护必然漂移。这里给出**唯一**切分：空白与 `,，;；、|` 都是分隔符。
    """
    if isinstance(subject, list):
        items = [str(item) for item in subject]
    elif isinstance(subject, str):
        items = [subject]
    else:
        return []
    tokens = []
    for item in items:
        tokens.extend(token for token in SUBJECT_SPLIT.split(item) if token and token.strip())
    return tokens


def subject_mentions(subject, target):
    """`subject` 是否以**整词**覆盖 `target`（`api` 不覆盖 `api-docs`）。"""
    if not isinstance(target, str) or not target:
        return False
    return target in subject_tokens(subject)


def registered() -> dict:
    """只读快照，供 `wf help`/诊断输出与文档核对。"""
    return {key: list(value) for key, value in DOMAINS.items()}
