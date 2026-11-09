#!/usr/bin/env python3
"""622 就绪视图：无绑定会话能列出候选并给出最早就绪建议，且不写任何判定字段。

obligation（设计稿 §5.6 / §5.1、机制稿 §6.1）：
- 无绑定会话按创建时间给出**最早就绪建议**，人可选另一个；
- 「就绪」不等于「存在」：已批准未开工才算可直接接续，
  进行中未暂停、或写权被别的会话持有时必须列为阻断项；
- 只读：不写判定字段（整体记录前后不变）。

注入形态：忽略全部阻断项（ready 恒为真）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-622"
FROM = '        entries.append({\n'
TO = '        blockers = []  # 注入：忽略全部阻断项\n        entries.append({\n'


def ready(project, sid=SID):
    return H.cli(project, ["ready", "--json"], sid=sid,
                 inputs={"generation": H.generation(project)})


def approved_not_started(project, root, title="待接续任务"):
    import hashlib

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n内容。\n")
    decision = os.path.join(root, "approve-ready.json")
    json.dump([F.decision("approve", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    return task_id, task_dir


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    task_id, task_dir = approved_not_started(project, root)
    before = open(os.path.join(task_dir, "task.json"), "rb").read()
    problems = []

    rc, payload = ready(project)
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"ready 失败：{payload}")
    facts = (payload or {}).get("facts") or {}
    entry = next((item for item in facts.get("tasks") or [] if item.get("id") == task_id), None)
    if not entry:
        problems.append("就绪视图未列出已批准未开工的任务")
    elif not entry.get("ready"):
        problems.append(f"已批准未开工的任务未判 ready：{entry.get('blockers')}")
    if facts.get("suggested") != task_id:
        problems.append(f"建议对象不是该任务：{facts.get('suggested')}")
    if open(os.path.join(task_dir, "task.json"), "rb").read() != before:
        problems.append("就绪视图改写了任务记录（只读子命令不得写判定字段）")

    # 开工后：进行中未暂停 → 不再 ready
    S.started_task(project, root, sid=SID) if False else None
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{payload}")
    rc, payload = ready(project)
    entry = next((item for item in ((payload or {}).get("facts") or {}).get("tasks") or []
                  if item.get("id") == task_id), None)
    if entry and entry.get("ready"):
        problems.append("进行中未暂停的任务仍被判 ready")
    if ((payload or {}).get("facts") or {}).get("suggested") == task_id:
        problems.append("进行中的任务仍被建议接续")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
