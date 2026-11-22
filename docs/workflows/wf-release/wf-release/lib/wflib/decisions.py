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


def canonical(operation: str, choice):
    """返回登记表里的规范值；未登记返回 None（调用方据此拒绝并列出可接受值）。"""
    for item in domain(operation):
        if item == choice:
            return domain(operation)[0]
    return None


def registered() -> dict:
    """只读快照，供 `wf help`/诊断输出与文档核对。"""
    return {key: list(value) for key, value in DOMAINS.items()}
