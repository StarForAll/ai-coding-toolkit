#!/usr/bin/env python3
"""629.s2.c11：空批准面下写入口必须按「无路径在范围内」拒绝，且回显空面。

obligation（§96 ① s2 × c11）：`spec-update` 的目标必须在批准面内；面为空时
任何目标都越界 → `WF_SCOPE_UNRESOLVED`，且 `facts.touch_paths == []`
（回显空数组即证明它用的是快照，而不是回退后的 plan）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-S2W"


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
    changes = os.path.join(root, "changes-s2.json")
    json.dump([{"action": "add", "new_paths": ["pkg/r.md"], "content": "x\n"}],
              open(changes, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["spec-update", "--task", task_id, "--changes", changes, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.code_problem(payload, {"WF_SCOPE_UNRESOLVED"})
    facts = (payload or {}).get("facts") or {}
    if facts.get("touch_paths") != []:
        raise H.TargetFailure(f"未回显空批准面（疑似回退 plan）：{facts.get('touch_paths')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
