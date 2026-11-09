#!/usr/bin/env python3
"""629.s3.c1/c2/c3/c7：快照缺 touch_paths 时，收工路径必须 fail-closed。

obligation（§96 ① s3 × 收工类消费点）：已开工任务的批准面只能取 `entry_snapshot`；
缺键即 `WF_RECORD_INVALID`，**不得**回退可变的 `plan.touch_paths`——否则手改 task.json
的 plan 就能反向扩大批准面，keep/transfer 的归属判定随之失效。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-S3S"


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
    problems = []
    for label, decision in (("keep", ["pkg/b.py"]),
                            ("transfer", ["pkg/b.py"])):
        payload_dec = dict(F.decision(decision, label))
        if label == "transfer":
            payload_dec["target_task"] = task_id
        path = os.path.join(root, f"stop-s3-{label}.json")
        json.dump([payload_dec], open(path, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = H.cli(project, ["stop", "--decision", path, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                            "WF_RECORD_INVALID", f"s3 收工/{label}")
        if rc == 0:
            problems.append(f"{label}：快照缺键仍放行")
            break  # 已放行会改状态（暂停 + 释放写权），后续分支不再可用
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
