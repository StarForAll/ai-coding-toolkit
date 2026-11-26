#!/usr/bin/env python3
"""P1-2：`run pause` 写暂停原因与当前步骤、暂停当前任务，且暂停后 advance 必须停住。

机制稿 §7.3：「实例暂停须保存当前任务的暂停或等待原因及当前步骤，**不能只移动游标绕过
任务门禁**」——所以 pause 不动 `cursor`，只写 `paused`/`paused_reason` 并把当前任务标 paused。

注入形态 = `pause` 不写 `paused`（模拟「只回报不落盘」）→ 目标断言（实例记录必须为暂停态）变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-PAUSE"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''        run = dict(run, paused=True,\n'''
TO = '''        run = dict(run,  # 注入：不写 paused\n'''

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
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/one-step.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "one-step", "definition_digest": digest, "inputs": {},
                "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    prepare_auth = H.prepare_authorization(project, root, "one-step", sid=SID)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    for args in (["definition", "prepare", "--id", "one-step", "--authorization", prepare_auth],
                 ["run", "create", "--creation", creation_path,
                  "--authorization", create_auth]):
        rc, payload = H.cli(project, args + ["--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        run_id = ((payload or {}).get("facts") or {}).get("run", {}).get("id", run_id) \
            if args[0] == "run" else None
    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    task_id = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')}")
    cursor_before = (json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")))
                     .get("cursor"))

    rc, payload = H.cli(project, ["run", "pause", "--run", run_id, "--reason", "人要先处理别的事",
                                  "--json"], sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.TargetFailure(f"pause 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    run_record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")))
    problems = []
    # 目标断言：实例必须落成暂停态，并保存原因与当前步骤
    if run_record.get("paused") is not True:
        problems.append("实例记录没有 paused=true")
    reason = run_record.get("paused_reason") or {}
    if reason.get("reason") != "人要先处理别的事":
        problems.append(f"未保存暂停原因：{reason}")
    if reason.get("step") != "change":
        problems.append(f"未保存当前步骤：{reason}")
    if run_record.get("cursor") != cursor_before:
        problems.append("pause 移动了游标（机制稿 §7.3 禁止）")
    task = json.load(open(os.path.join(project, ".wf/tasks",
                                       [n for n in os.listdir(os.path.join(project, ".wf/tasks"))
                                        if n.startswith(task_id)][0], "task.json")))
    if task.get("paused") is not True:
        problems.append("当前任务未被暂停（执行候选没清掉）")

    # 暂停后 advance 必须停住
    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc == 0:
        problems.append("暂停后 advance 仍然推进了")
    elif (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"暂停后 advance 的原因码：{(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
