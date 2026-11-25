"""codes.py — 结果结构与原因码访问器（机制稿 §11.1）。

码表本身不在本模块：机器事实的唯一存放处是 `protocol/codes.json`，
码值语义权属在机制稿 §11.1（发布后只增不改义）。本模块只做访问器与
§11.1 单一结果结构的构造，不持有第二份枚举。
"""

from __future__ import annotations

from .protocol import codes as _protocol_codes

# code -> (tier, exit, prohibited_repairs)：规范化为元组，调用点与旧表同形。
CODES = _protocol_codes()


TIER_EXIT_CODES = {"pass": 0, "blocked": 1, "needs_decision": 2}
INTERNAL_ERROR_EXIT = 70


class CodeUnknown(Exception):
    pass


def tier_of(code: str) -> str:
    try:
        return CODES[code][0]
    except KeyError as exc:
        raise CodeUnknown(code) from exc


def exit_of(code: str) -> str:
    return CODES[code][1]


def prohibited_of(code: str) -> str | None:
    return CODES[code][2]


def process_exit(code: str) -> int:
    return TIER_EXIT_CODES[tier_of(code)]


def position(scope=None, phase=None, step_id=None, task_id=None, action_id=None, action_state=None):
    return {
        "scope": scope,
        "phase": phase,
        "step_id": step_id,
        "task_id": task_id,
        "action_id": action_id,
        "action_state": action_state,
    }


def result(
    code,
    *,
    object=None,
    position_=None,
    next_=None,
    facts=None,
    warnings=None,
    issues=None,
):
    """构造 §11.1 的单一结果结构。"""
    tier = tier_of(code)
    payload = {
        "tier": tier,
        "code": code,
        "object": object,
        "position": position_ or position(),
        "next": next_,
        "facts": facts or {},
        # `exit` 是失败/待决的出口（机制稿 §11.1）：pass 时下一步只由 `next` 承载。
        # 此前每个 pass 也带码表通用文案「继续当前绑定步骤」，与只读命令的 next 直接矛盾
        # （2026-11-25 第四轮复审 F3），文本渲染器本来也不显示 pass 的该字段。
        "exit": exit_of(code) if tier != "pass" else None,
        "prohibited_repairs": prohibited_of(code) if tier != "pass" else None,
        "warnings": warnings or [],
    }
    if issues:
        payload["issues"] = issues
    return payload
