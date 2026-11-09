"""runs.py — 用户工作流实例（第二轮交付；首轮命令存在且可调用）。

见机制稿 §7。首轮只提供只读记录读取，其余动作统一报告能力不可用。
"""

from __future__ import annotations

from . import assets, records
from .paths import join

ROUND = 2


def run_path(root, run_id):
    return join(root, f".wf/workflow-runs/{run_id}.json")


def load_run(root, run_id):
    if not run_id:
        return None
    return records.load_json(run_path(root, run_id))


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
