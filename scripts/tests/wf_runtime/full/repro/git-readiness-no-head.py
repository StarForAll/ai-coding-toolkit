#!/usr/bin/env python3
"""627 Git 就绪：无 HEAD 时不得开工（正例已由 p5_f0 覆盖，这里补负例）。

obligation（设计稿 §8.2「Git 就绪」、验收夹具 F0）：无提交的仓库只能落盘并报告待就绪，
**不允许业务任务开工**；出口是 `WF_CAPABILITY_UNAVAILABLE`（人授权后建首个 HEAD 再重试）。

注入形态：无 HEAD 也放行开工。
"""
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-627"
FROM = ('        if not head:\n'
        '            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "no HEAD commit"})\n')
TO = ('        if False:  # 注入：无 HEAD 也放行\n'
      '            raise TaskError("WF_CAPABILITY_UNAVAILABLE", {"reason": "no HEAD commit"})\n')


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    subprocess.run(["git", "add", "-A"], cwd=project, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=project, capture_output=True)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "无 HEAD",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# 无 HEAD\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n内容。\n")
    decision = os.path.join(root, "approve-627.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest()), artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")

    subprocess.run(["git", "update-ref", "-d", "HEAD"], cwd=project, capture_output=True)
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.code_problem(payload, {"WF_CAPABILITY_UNAVAILABLE"})
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
