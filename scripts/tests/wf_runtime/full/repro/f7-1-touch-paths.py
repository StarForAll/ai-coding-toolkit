#!/usr/bin/env python3
"""F7-1：批准触碰面三态（未开工回退 plan / 已开工空数组合法 / 已开工缺快照必拒）。

缺陷形态（注入点）：把"是否已开工"的判定退化为"快照是否为 dict"，
于是已开工但快照丢失的任务会静默拿到可变的 plan.touch_paths。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, lib, _payload = H.stage()
    H.load(lib)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(lib, "wflib", "tasks.py"),
                'started = task.get("phase") in PHASES_STARTED or bool(task.get("baseline_head"))',
                'started = False  # 注入：已开工也当未开工')
    from wflib import tasks as wf_tasks

    problems = []
    started_lost = {"id": "t1", "phase": "execute", "entry_snapshot": None,
                    "plan": {"touch_paths": ["src/**"]}}
    try:
        got = wf_tasks.approved_touch_paths(started_lost)
        problems.append(f"已开工缺快照未拒，返回 {got}")
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        # 期望码即正确行为；其它码由 only_two_outcomes 归为前置失败
        H.only_two_outcomes(code, "WF_RECORD_INVALID", "approved_touch_paths")

    empty_ok = {"id": "t2", "phase": "execute", "entry_snapshot": {"touch_paths": []},
                "plan": {"touch_paths": ["src/**"]}}
    got = wf_tasks.approved_touch_paths(empty_ok)
    if got != []:
        problems.append(f"空批准面被回退为 plan：{got}")

    unstarted = {"id": "t3", "phase": "plan", "entry_snapshot": None,
                 "plan": {"touch_paths": ["src/**"]}}
    got = wf_tasks.approved_touch_paths(unstarted)
    if got != ["src/**"]:
        problems.append(f"未开工未回退 plan：{got}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
