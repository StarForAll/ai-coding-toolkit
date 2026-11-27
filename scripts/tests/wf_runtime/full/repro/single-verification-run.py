#!/usr/bin/env python3
"""十轮收敛项：`task-check --run-verification` 只跑一条验证、只记一次运行。

obligation（设计稿 §3.5、机制稿 §3.5）：TDD 的红证据要能来自**一次针对性运行**，不是整轮 Check；
该入口不重算锚点、不写 `check`，并与 `--decision/--review-notes` 互斥。

红模：把该分支写成也走 Check（`if False` 关掉独立分支）→ 会写 check/要求双轴结论，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-SINGLE"

FROM = '''    run_verification = args.value("--run-verification")
    if run_verification:
        return _single_verification(ctx, task_id, run_verification)
'''
TO = '''    run_verification = args.value("--run-verification")
    if False:  # 注入：不提供单次运行入口（迫使走整轮 Check）
        return _single_verification(ctx, task_id, run_verification)
'''


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    task_id, task_dir = F.build_task(project, root, "单次验证", sid=SID)
    record_path = os.path.join(task_dir, "task.json")
    before = json.load(open(record_path, encoding="utf-8"))

    problems = []
    rc, payload = H.cli(project, ["task-check", "--task", task_id,
                                  "--run-verification", "v1", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    run = facts.get("run") or {}
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"单次运行入口不可用：{(payload or {}).get('code')} {str(facts)[:300]}")
    else:
        if run.get("verification_id") != "v1":
            problems.append(f"运行身份不是 v1：{run.get('verification_id')}")
        if not run.get("verification_digest"):
            problems.append("运行未记验证定义摘要")
        if run.get("status") not in ("passed", "failed"):
            problems.append(f"运行状态不对：{run.get('status')}")
        after = json.load(open(record_path, encoding="utf-8"))
        if after.get("check") is not None:
            problems.append("单次运行写了 check（不应产生 Check 结论）")
        runs = ((after.get("execution") or {}).get("verification_runs") or [])
        if len(runs) != 1:
            problems.append(f"运行记录数不对：{len(runs)}")
        if (after.get("check_history") or []) != (before.get("check_history") or []):
            problems.append("单次运行改了 check_history")

    # 与真实输入互斥（同一处登记）
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--run-verification", "v1",
                                  "--decision", os.path.join(root, "approve.json"), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc == 0:
        problems.append("--run-verification 与 --decision 同给未被拒")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
