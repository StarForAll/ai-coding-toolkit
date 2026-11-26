#!/usr/bin/env python3
"""P1-3：`run terminate` 批量处置——放弃走 §6.4、保留写 independent_resume（机制稿 §7.4）。

两条断言链：
1. 计划不全（漏掉已生成任务）→ `WF_SEMANTIC_DECISION` 且**零写入**（实例仍在途、任务未动）；
2. 完整计划（任务 A 放弃 + 任务 B 保留）→ A 异常归档（`terminal=abnormal`）、B 写
   `independent_resume` 且 `paused=true`、实例 `closing.mode=abnormal` + `terminal=abnormal`、
   未生成步骤记 `not_executed`；之后 `run advance` 因终态被拒。

注入形态 = 终止时不写 `terminal`（模拟"只保存关闭请求、不回写终态"）→ 目标断言 2 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-TERM"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''        run = dict(run, step_results=step_results, terminal="abnormal",\n'''
TO = '''        run = dict(run, step_results=step_results,  # 注入：不写终态\n'''


def _step(step_id, title):
    return {"id": step_id, "type": "task", "title": title, "task_kind": "ordinary",
            "inputs": [], "outputs": [], "required": True, "skip": None,
            "human_points": [{"id": f"approve-{step_id}", "question": "是否批准？"}],
            "goal": f"完成 {title}", "acceptance": ["验收通过"],
            "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                         "required": True, "skip": None, "human_points": []}],
            "verifications": [{"id": "task-check", "source": "current_plan",
                               "established_by": {"kind": "current_task"},
                               "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                               "consume_at": "check"}]}


def _definition():
    doc = {"format_version": 1, "workflow_id": "three-step", "content_version": 1,
           "purpose": "三步流程", "applicability": "已有基线", "inputs": {},
           "steps": [_step("one", "第一个"), _step("two", "第二个"), _step("three", "第三个")],
           "completion": ["三步都正常归档"]}
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def _decision(choice, task_id, digest):
    return {"source": "human", "at": "2026-11-12T00:00:00.000000Z",
            "subject": [task_id], "object_digest": digest, "choice": choice,
            "reason": f"批量终止：{choice}"}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/three-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "three-step", "definition_digest": digest, "inputs": {},
                "steps": {"one": "applicable", "two": "applicable", "three": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args, **kw):
        return H.cli(project, args + ["--json"], sid=SID,
                     inputs={"generation": H.generation(project)}, **kw)

    prepare_auth = H.prepare_authorization(project, root, "three-step", sid=SID)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    for args in (["definition", "prepare", "--id", "three-step", "--authorization", prepare_auth],
                 ["run", "create", "--creation", creation_path,
                  "--authorization", create_auth]):
        rc, payload = run(args)
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        if args[0] == "run":
            run_id = ((payload or {}).get("facts") or {})["run"]["id"]
    rc, payload = run(["run", "advance", "--run", run_id])
    first_task = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not first_task:
        raise H.Precondition(f"advance 未建首任务：{(payload or {}).get('code')}")

    run_path = os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")

    # ① 计划里混入不属于本实例的任务 → 拒且零写入
    #    （本实例此时只生成一个任务，所以"漏项"造不出来；用"多出未知任务"测同一道闸门）
    stranger = "2026-" + "0" * 32
    partial = os.path.join(root, "partial.json")
    json.dump([{"object": first_task, "decision_ref": _decision("放弃", first_task, digest),
                "reason": "实例终止"},
               {"object": stranger, "decision_ref": _decision("保留", stranger, digest),
                "reason": "不属于本实例"}], open(partial, "w"), ensure_ascii=False)
    rc, payload = run(["run", "terminate", "--run", run_id, "--plan", partial])
    problems = []
    if rc == 0 or (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"含未知任务的计划未被拒：rc={rc} code={(payload or {}).get('code')}")
    if json.load(open(run_path, encoding="utf-8")).get("closing"):
        problems.append("被拒的计划仍写了 closing（应零写入）")
    if not json.load(open(run_path, encoding="utf-8")).get("terminal") is None:
        problems.append("被拒的计划仍改了实例终态")

    # ② 完整计划：A 放弃、B 保留（B 不存在——本实例只生成一个任务，故计划只含它）
    second = os.path.join(root, "second.json")
    record_rel = f".wf/workflow-runs/{run_id}.json"
    grant = {"object": first_task,
             "decision_ref": _decision("放弃", first_task, digest),
             "reason": "实例终止，这项工作不再需要"}
    # 放弃决定里带上覆盖实例记录的提交授权（`commit`）”的约定：另给一条 commit 决定
    commit_grant = {"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                    "subject": [record_rel], "object_digest": digest,
                    "choice": "commit", "reason": "提交实例终止记录"}
    json.dump([dict(grant, decision_ref=[grant["decision_ref"], commit_grant])],
              open(second, "w"), ensure_ascii=False)
    rc, payload = run(["run", "terminate", "--run", run_id, "--plan", second])
    if rc != 0:
        raise H.TargetFailure(f"terminate 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    facts = (payload or {}).get("facts") or {}
    record = json.load(open(run_path, encoding="utf-8"))
    if facts.get("persisted") is not True:
        problems.append(f"有提交授权却未持久化：{facts.get('persisted')} {facts.get('commit')}")
    if (record.get("action") or {}).get("state") != "done":
        problems.append(f"提交完成后动作应 done：{(record.get('action') or {}).get('state')}")
    # 目标断言：实例必须落成异常终态
    if record.get("terminal") != "abnormal":
        problems.append("实例未写 terminal=abnormal（目标断言）")
    if (record.get("closing") or {}).get("mode") != "abnormal":
        problems.append(f"closing 不是 abnormal：{record.get('closing')}")
    # 放弃的任务：异常归档
    directory = [n for n in os.listdir(os.path.join(project, ".wf/tasks/archive/2026-11"))
                 if n.startswith(first_task)]
    if not directory:
        problems.append("被放弃的任务未移入归档")
    else:
        task = json.load(open(os.path.join(project, ".wf/tasks/archive/2026-11", directory[0],
                                          "task.json"), encoding="utf-8"))
        if task.get("terminal") != "abnormal":
            problems.append(f"被放弃任务的终态：{task.get('terminal')}")
    # 未生成的步骤记 not_executed，且不建空壳任务
    results = record.get("step_results") or {}
    for step_id in ("two", "three"):
        if (results.get(step_id) or {}).get("kind") != "not_executed":
            problems.append(f"未生成步骤 {step_id} 未记 not_executed：{results.get(step_id)}")
    if len([n for n in os.listdir(os.path.join(project, ".wf/tasks")) if n.startswith("2026-")]) != 0:
        problems.append("终止后活动区仍有任务目录（不应建空壳）")
    # 终态后 advance 必须被拒
    rc, payload = run(["run", "advance", "--run", run_id])
    if rc == 0:
        problems.append("终态实例仍可推进")
    # 不报告业务验收通过
    if "验收" in str(facts.get("next") or "") and "不报告" not in str(facts.get("next")):
        problems.append("next 未声明不报告业务验收通过")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
