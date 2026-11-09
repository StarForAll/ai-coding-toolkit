#!/usr/bin/env python3
"""629.s2.c1：空批准面是合法状态，收工只按空面判定，不回退 plan。

obligation（§96 ① s2 × c1）：`entry_snapshot.touch_paths == []` 表示"本任务批准面为空"，
keep 时任何路径都算越界（`WF_WORKSPACE_UNRESOLVED` + `out_of_scope`），
**不得**因为空就被当成缺失去回退可变的 `plan.touch_paths`。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-S2S"


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        S.inject_empty_fallback(project)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    S.empty_surface(task_dir)
    path = os.path.join(root, "stop-s2.json")
    json.dump([F.decision(["pkg/b.py"], "keep")], open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["stop", "--decision", path, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.code_problem(payload, {"WF_WORKSPACE_UNRESOLVED"})
    facts = (payload or {}).get("facts") or {}
    if facts.get("out_of_scope") != ["pkg/b.py"]:
        raise H.TargetFailure(f"越界项不是 ['pkg/b.py']：{facts.get('out_of_scope')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
