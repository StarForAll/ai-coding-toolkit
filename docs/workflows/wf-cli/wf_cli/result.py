"""Fixed output shape for the system-level wf command.

The command is an entry point in the same output family as the project bootstrap: every failure
names a stable code, decisive facts and an exit. It never invents a release identity or writes a
project record itself; maintenance is delegated to the release installer / installed independent
entries.
"""

from __future__ import annotations

import json
import sys

PROHIBITED_REPAIRS = "不猜发行版本或 tag；不改为本地 checkout 充当发行源；不绕过系统 wf 命令或改写安装记录"


def _payload(tier, code, facts, exit_hint, next_step, warnings=None):
    return {
        "tier": tier,
        "code": code,
        "object": None,
        "position": {
            "scope": "maintenance" if code.startswith("WF_") else None,
            "phase": None,
            "step_id": None,
            "task_id": None,
            "action_id": None,
            "action_state": None,
        },
        "next": next_step,
        "facts": facts or {},
        "exit": exit_hint,
        "prohibited_repairs": PROHIBITED_REPAIRS,
        "warnings": list(warnings or []),
    }


def _emit(payload, json_mode, human_lines):
    if json_mode:
        sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    else:
        for line in human_lines:
            sys.stdout.write(line + "\n")
    sys.stdout.flush()


def blocked(code, message, facts=None, exit_hint=None, json_mode=False, exit_code=1, tier="blocked",
            warnings=None):
    payload = _payload(tier, code, dict(facts or {}, message=message), exit_hint, exit_hint, warnings)
    lines = [f"BLOCKED  {code}", f"事实: {json.dumps(payload['facts'], ensure_ascii=False, sort_keys=True)}"]
    if exit_hint:
        lines.append(f"出口: {exit_hint}")
    if warnings:
        lines.extend(f"WARN  {item}" for item in warnings)
    _emit(payload, json_mode, lines)
    return exit_code


def passed(message, facts=None, next_step=None, json_mode=False, warnings=None):
    payload = _payload("pass", "WF_OK", dict(facts or {}, message=message), None, next_step, warnings)
    lines = ["OK  WF_OK", message]
    for key, value in sorted((facts or {}).items()):
        lines.append(f"{key}: {value}")
    if next_step:
        lines.append(f"下一步: {next_step}")
    if warnings:
        lines.extend(f"WARN  {item}" for item in warnings)
    _emit(payload, json_mode, lines)
    return 0