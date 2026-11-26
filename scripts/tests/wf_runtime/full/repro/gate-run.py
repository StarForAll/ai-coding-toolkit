#!/usr/bin/env python3
"""G05：`gate` 的实例分支——绑到实例后能只读查门禁（机制稿 §7.3、§11.2）。

断言链：
1. 绑到实例的新会话 `gate --due before_execute` 返回 `WF_OK`（不再是能力不可用）；
2. facts 列出每个步骤的 `result`/`applicability`/`current`，并说明当前在等什么（等任务完成）；
3. **零写入**：游标、`step_results`、实例 revision 都没变。

注入形态 = 实例分支不列步骤（模拟"只回一句空门禁"）→ 目标断言 2 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-GR"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''    return {"run": run.get("id"), "cursor": cursor, "steps": steps,'''
TO = '''    return {"run": run.get("id"), "cursor": cursor, "steps": [],  # 注入：不列步骤'''

STEP = {
    "id": "change", "type": "task", "title": "实施变更", "task_kind": "ordinary",
    "inputs": [], "outputs": [], "required": True, "skip": None,
    "human_points": [{"id": "approve-plan", "question": "是否批准？"}],
    "goal": "完成变更", "acceptance": ["验收通过"],
    "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                 "required": True, "skip": None, "human_points": []}],
    "verifications": [{"id": "task-check", "source": "current_plan",
                       "established_by": {"kind": "current_task"},
                       "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                       "consume_at": "check"}],
}


def _definition():
    doc = {"format_version": 1, "workflow_id": "one-step", "content_version": 1,
           "purpose": "一步流程", "applicability": "已有基线", "inputs": {},
           "steps": [STEP], "completion": ["change 正常归档"]}
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/gates.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/one-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "one-step", "definition_digest": digest, "inputs": {},
                "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args, sid=SID):
        return H.cli(project, args + ["--json"], sid=sid,
                     inputs={"generation": H.generation(project)})

    prepare_auth = H.prepare_authorization(project, root, "one-step", sid=SID)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    for args in (["definition", "prepare", "--id", "one-step", "--authorization", prepare_auth],
                 ["run", "create", "--creation", creation_path,
                  "--authorization", create_auth]):
        rc, payload = run(args)
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        if args[0] == "run":
            run_id = ((payload or {}).get("facts") or {})["run"]["id"]
    rc, payload = run(["run", "advance", "--run", run_id])
    task_id = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')}")

    run_path = os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")
    before = json.load(open(run_path, encoding="utf-8"))
    problems = []
    rc, payload = run(["gate", "--due", "before_execute"])
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"实例 gate 不可用：rc={rc} code={(payload or {}).get('code')}")
    else:
        steps = facts.get("steps") or []
        if [item.get("id") for item in steps] != ["change"]:
            problems.append(f"gate 未列步骤（目标断言）：{steps}")
        elif steps[0].get("task") != task_id or not steps[0].get("current"):
            problems.append(f"gate 未标出当前步骤与任务：{steps[0]}")
        if not any("等待任务" in str(item.get("reason")) for item in facts.get("blocking") or []):
            problems.append(f"未说明在等什么：{facts.get('blocking')}")
    after = json.load(open(run_path, encoding="utf-8"))
    if after.get("cursor") != before.get("cursor") or after.get("step_results") != before.get("step_results"):
        problems.append("gate 改了游标或 step_results（应只读）")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
