#!/usr/bin/env python3
"""629.s3.c4/c5/c9/c10：快照缺 touch_paths 时，Check 期消费点必须全部 fail-closed。

obligation：Check 的范围分类、外部变更核对、跨任务冲突、外部变更再判定都以
「批准触碰面」为输入；s3 下该面不可得，必须 `WF_RECORD_INVALID`，
不得回退 plan（回退等于让手改的 plan 成为检查依据）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-S3C"


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        S.inject(project)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    S.damage(task_dir)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    # 任何其它业务码都说明「缺键即拒」失效（包括回退 plan 后继续跑出别的拒绝）
    H.code_problem(payload, {"WF_RECORD_INVALID"})
    facts = (payload or {}).get("facts") or {}
    if "touch_paths" not in str(facts.get("reason") or ""):
        raise H.TargetFailure(f"拒绝原因未指向缺键：{facts.get('reason')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
