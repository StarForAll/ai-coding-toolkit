"""runs.py — 用户工作流实例（第二轮交付；首轮命令存在且可调用）。

见机制稿 §7。首轮只提供只读记录读取，其余动作统一报告能力不可用。
"""

from __future__ import annotations

from . import assets, records
from .paths import join

ROUND = 2


RUNS_REL = ".wf/workflow-runs"


def run_path(root, run_id):
    return join(root, f".wf/workflow-runs/{run_id}.json")


def load_run(root, run_id):
    if not run_id:
        return None
    return records.load_json(run_path(root, run_id))


def iter_runs(root):
    """枚举实例记录（只读）。

    读不出的记录**不当作不存在**：调用方拿到 `(None, path)` 时必须报 unknown，
    否则「悬空 run_id」会被当成「不是实例任务」而错误放行（机制稿 §6.1 独立接续资格）。
    """
    import os

    directory = join(root, RUNS_REL)
    if not os.path.isdir(directory):
        return []
    found = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        found.append((records.load_json(path), path))
    return found


# 独立接续资格（机制稿 §6.1）的绑定面判定结果。**唯一实现**：
# `cli._eligible_task_bind` 用它决定放行/拒绝，`cli.cmd_ready` 用它归组与给阻断项。
BINDING_NONE = "no_run"
BINDING_IN_FLIGHT = "in_flight"
BINDING_NORMAL = "run_ended_normal"
BINDING_ABNORMAL_LICENSED = "run_abnormal_licensed"
BINDING_ABNORMAL_UNLICENSED = "run_abnormal_unlicensed"
BINDING_MISSING = "run_record_missing"


def binding_state(root, task):
    """任务在实例轴上的可接续状态：`{state, run_id, run, permission}`。"""
    run_id = (task or {}).get("run_id")
    if not run_id:
        return {"state": BINDING_NONE, "run_id": None, "run": None, "permission": None}
    run = load_run(root, run_id)
    if run is None:
        return {"state": BINDING_MISSING, "run_id": run_id, "run": None, "permission": None}
    terminal = run.get("terminal")
    if terminal == "normal":
        return {"state": BINDING_NORMAL, "run_id": run_id, "run": run, "permission": None}
    if terminal == "abnormal":
        permission = task.get("independent_resume") or {}
        licensed = bool(permission.get("decision") and permission.get("termination_action"))
        return {"state": BINDING_ABNORMAL_LICENSED if licensed else BINDING_ABNORMAL_UNLICENSED,
                "run_id": run_id, "run": run, "permission": permission or None}
    return {"state": BINDING_IN_FLIGHT, "run_id": run_id, "run": run, "permission": None}


def prepare(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("definition preparation (D03/D11)", ROUND)


def validate(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("definition static validation (D03/D11)", ROUND)


def create(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run creation (D03/D11)", ROUND)


def advance(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run advance (D12)", ROUND)


def pause(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run pause (D13)", ROUND)


def locate(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run locate (D13)", ROUND)


def terminate(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run terminate (D13)", ROUND)


def load_definition(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("workflow definition loading (D11)", ROUND)


def finish(*_args, **_kwargs):
    raise assets.CapabilityUnavailable("run finish (D13)", ROUND)
