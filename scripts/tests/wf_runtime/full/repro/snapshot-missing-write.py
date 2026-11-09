#!/usr/bin/env python3
"""629.s3.c11：快照缺 touch_paths 时，写入口（spec-update / baseline-apply）必须 fail-closed。

obligation：写入口用批准面判定「目标是否在范围内」；s3 下该面不可得必须
`WF_RECORD_INVALID`，不得回退 plan——否则手改 plan 就能扩大可写范围。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-S3W"


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
    changes = os.path.join(root, "changes.json")
    json.dump([{"action": "add", "new_paths": ["pkg/r.md"], "content": "x\n"}],
              open(changes, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["spec-update", "--task", task_id,
                                  "--changes", changes, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.code_problem(payload, {"WF_RECORD_INVALID"})
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
