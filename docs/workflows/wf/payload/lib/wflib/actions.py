"""actions.py — 动作意图、幂等键与重入四态（机制稿 §5.1、§5.2）。"""

from __future__ import annotations

import os

from . import records

ACTION_FIELDS = (
    "id",
    "kind",
    "scope",
    "decision_refs",
    "base_revision",
    "head_before",
    "inputs_digest",
    "targets",
    "steps",
    "next_step",
    "state",
    "result",
)

STATES = ("prepared", "applying", "persist_pending", "done")


def normalize_inputs(inputs: dict) -> list:
    """[{name, value}]，按 name 的 UTF-8 字节序去重排序。"""
    pairs = [{"name": name, "value": value} for name, value in (inputs or {}).items()]
    return sorted(pairs, key=lambda entry: entry["name"].encode("utf-8"))


def inputs_digest(inputs: dict) -> str:
    return records.H("wf-action-inputs-v1", normalize_inputs(inputs))


def action_id(owner_ref, base_revision: int, kind: str, inputs: dict, approval_ref) -> str:
    payload = {
        "owner_ref": owner_ref,
        "base_revision": int(base_revision),
        "kind": kind,
        "normalized_inputs": normalize_inputs(inputs),
        "approval_ref": approval_ref,
    }
    return records.H("wf-action-v1", payload)


def targets_digest(targets) -> str:
    def strip(value):
        if isinstance(value, dict):
            return {
                key: strip(item)
                for key, item in value.items()
                if key not in ("action", "write_mark", "revision")
            }
        if isinstance(value, list):
            return [strip(item) for item in value]
        return value

    return records.plain_digest(strip(targets))


def control_projection(owner_ref, action_id_value, operation, inputs_digest_value, targets_digest_value) -> dict:
    return {
        "owner_ref": owner_ref,
        "action_id": action_id_value,
        "operation": operation,
        "inputs_digest": inputs_digest_value,
        "targets_digest": targets_digest_value,
    }


def control_occurrence(projection: dict) -> str:
    return records.H("wf-control-occurrence-v1", projection)


def control_anchor(rule_version, projection: dict) -> str:
    return records.H("wf-step-anchor-v1", {"rule_version": rule_version, "P": projection})


def head_of(root):
    """只读 HEAD；无 HEAD 或不可用返回 None。"""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def new_action(
    kind: str,
    owner_ref: dict,
    base_revision: int,
    inputs: dict,
    *,
    scope=None,
    decision_refs=None,
    targets=None,
    steps=None,
    head_before=None,
    approval_ref=None,
) -> dict:
    return {
        "id": action_id(owner_ref, base_revision, kind, inputs, approval_ref),
        "kind": kind,
        "scope": scope,
        "decision_refs": list(decision_refs or []),
        "base_revision": int(base_revision),
        "head_before": head_before,
        "inputs_digest": inputs_digest(inputs),
        # 意图本体也要留：恢复时（如 identity/project_id）需要取值而不只是校验摘要
        "inputs": dict(inputs or {}),
        "targets": targets or [],
        # `steps` 的唯一形状：`{"id","state"}` 列表（写入流程与入口都在这一步之后按 id 标状态）。
        # 早先这里存的是步骤名字，另有多处再改写成字典——同一字段两种形状，按名比较全部失效。
        "steps": [{"id": str(step), "state": "pending"} for step in (steps or [])],
        "next_step": (str(steps[0]) if steps else None),
        "state": "prepared",
        "result": None,
    }


def current(record):
    action = record.get("action") if isinstance(record, dict) else None
    return action if isinstance(action, dict) else None


def pending(record):
    """返回未完成动作（state != done）；无则 None。"""
    action = current(record)
    if action and action.get("state") != "done":
        return action
    return None


def is_done(action) -> bool:
    return bool(action) and action.get("state") == "done"


def step_done(action, step_id: str):
    """推进一步：把该步骤标 done，`next_step` 指向下一个步骤 id。"""
    steps = [dict(item) if isinstance(item, dict) else {"id": item, "state": "pending"}
             for item in action.get("steps") or []]
    ids = [str(item.get("id")) for item in steps]
    if step_id not in ids:
        raise ValueError(f"unknown step: {step_id}")
    index = ids.index(step_id)
    steps[index]["state"] = "done"
    action = dict(action)
    action["steps"] = steps
    action["next_step"] = ids[index + 1] if index + 1 < len(ids) else None
    action["state"] = "applying"
    return action


def complete(action, summary=None, control_assertion=None):
    action = dict(action)
    # 收尾即"全部步骤完成"：状态与步骤不再各说一套
    action["steps"] = [dict(item, state="done") if isinstance(item, dict)
                       else {"id": item, "state": "done"}
                       for item in action.get("steps") or []]
    action["state"] = "done"
    action["next_step"] = None
    action["result"] = {"summary": summary, "failure": None, "control_assertion": control_assertion}
    return action


def fail(action, failure: str):
    action = dict(action)
    action["state"] = "applying"
    action["result"] = {"summary": None, "failure": failure, "control_assertion": None}
    return action


def reentry_state(record) -> str:
    """整体重入观察（机制稿 §5.2 四态）。"""
    action = current(record)
    if not action:
        return "none"
    if action.get("state") == "done":
        return "done"
    if action.get("state") == "persist_pending":
        return "persist_pending"
    if action.get("state") in ("prepared", "applying"):
        return "resumable"
    return "recovering"
