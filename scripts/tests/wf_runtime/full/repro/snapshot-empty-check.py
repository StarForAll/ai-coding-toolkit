#!/usr/bin/env python3
"""629.s2.c4：空批准面下 Check 的范围分类必须按空面判定。

obligation（§96 ① s2 × c4）：批准面为空时，本任务名下没有任何 in-scope 路径，
未提交改动因此归 c 桶（"不是本任务的活"）并阻断 Check——不是回退 plan 把它们收进来。
本用例先把控制记录（`.wf/`）提交掉，使 c 桶只剩业务文件，再断言它被点名。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-S2C"


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        S.inject_empty_fallback(project)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    evidence = os.path.join(root, "ev-s2.json")
    json.dump({"conclusion": "调查完成", "items": [{"ref": "x", "note": "y"}]},
              open(evidence, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-retrospect", "--task", task_id,
                                  "--evidence", evidence, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-retrospect 失败：{payload}")
    S.empty_surface(task_dir)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.code_problem(payload, {"WF_WORKSPACE_UNRESOLVED"})
    buckets = ((payload or {}).get("facts") or {}).get("buckets") or {}
    if "pkg/b.py" not in (buckets.get("c") or []):
        raise H.TargetFailure(f"空面下本任务文件未归 c 桶：{buckets.get('c')}")
    if buckets.get("e"):
        raise H.TargetFailure(f"空面下仍出现 in-scope 路径（疑似回退 plan）：{buckets.get('e')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
