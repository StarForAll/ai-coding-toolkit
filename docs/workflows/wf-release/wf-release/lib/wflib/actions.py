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
        "targets": targets or [],
        "steps": list(steps or []),
        "next_step": (steps or [None])[0] if steps else None,
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
    steps = list(action.get("steps") or [])
    if step_id in steps:
        index = steps.index(step_id)
        action = dict(action)
        action["next_step"] = steps[index + 1] if index + 1 < len(steps) else None
        action["state"] = "applying"
        return action
    raise ValueError(f"unknown step: {step_id}")


def complete(action, summary=None, control_assertion=None):
    action = dict(action)
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
