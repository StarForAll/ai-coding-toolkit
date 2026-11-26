#!/usr/bin/env python3
"""方案 B：`run resume` 只解除**实例**暂停，不动任务、不动游标（机制稿 §2.2/§7.3）。

三条断言（这就是 B 的全部语义）：
1. 解除后 `paused=false`、`resumed.at` 有值、`lifted_paused_at` 记住被解除的那次暂停；
2. **当前任务仍是暂停态**（解除实例暂停不等于恢复任务——那是 `task-resume` 的另一个决定）；
3. 游标不变，且之后 `advance` 能重新推进（返回 `waiting`，因为任务还没归档）。

另核可选决定的状态绑定：`subject` 不含本次 `paused_reason.at` → `WF_SEMANTIC_DECISION`（拿上次的决定清这次的暂停被拒）。

注入形态 = `resume` 不清 `paused`（只回报成功）→ 目标断言 1 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-RESUME"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''        run = dict(run, paused=False, resumed=resumed,\n'''
TO = '''        run = dict(run, resumed=resumed,  # 注入：不清 paused\n'''

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


def _run(project, args, sid=SID):
    return H.cli(project, args + ["--json"], sid=sid,
                 inputs={"generation": H.generation(project)})


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
    rc, payload = _run(project, ["definition", "prepare", "--id", "one-step",
                                 "--authorization", prepare_auth])
    if rc != 0:
        raise H.Precondition(f"prepare 失败：{(payload or {}).get('code')}")
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    rc, payload = _run(project, ["run", "create", "--creation", creation_path,
                                 "--authorization", create_auth])
    if rc != 0:
        raise H.Precondition(f"create 失败：{(payload or {}).get('code')}")
    run_id = ((payload or {}).get("facts") or {})["run"]["id"]
    rc, payload = _run(project, ["run", "advance", "--run", run_id])
    task_id = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')}")

    run_path = os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")
    rc, _payload = _run(project, ["run", "pause", "--run", run_id, "--reason", "先处理别的事"])
    if rc != 0:
        raise H.Failure if False else H.Precondition("pause 失败")
    paused = json.load(open(run_path, encoding="utf-8"))
    cursor_before = paused.get("cursor")
    paused_at = (paused.get("paused_reason") or {}).get("at")

    # ① 解除（不带决定）
    rc, payload = _run(project, ["run", "resume", "--run", run_id])
    problems = []
    if rc != 0:
        raise H.TargetFailure(f"resume 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    run_record = json.load(open(run_path, encoding="utf-8"))
    if run_record.get("paused") is not False:
        problems.append("实例仍是 paused（目标断言 1）")
    resumed = run_record.get("resumed") or {}
    if not resumed.get("at"):
        problems.append("未记录解除时间")
    if resumed.get("lifted_paused_at") != paused_at:
        problems.append(f"未记录被解除的暂停时点：{resumed}")
    if run_record.get("paused_reason", {}).get("reason") != "先处理别的事":
        problems.append("历史暂停原因被抹掉了")

    # ② 任务仍是暂停态（解除实例暂停 ≠ 恢复任务）
    task_dir = [n for n in os.listdir(os.path.join(project, ".wf/tasks")) if n.startswith(task_id)][0]
    task = json.load(open(os.path.join(project, ".wf/tasks", task_dir, "task.json"), encoding="utf-8"))
    if task.get("paused") is not True:
        problems.append("resume 顺手恢复了任务（越权：那是 task-resume 的决定）")

    # ③ 游标不变，且 advance 能重新推进
    if run_record.get("cursor") != cursor_before:
        problems.append("resume 动了游标")
    rc, payload = _run(project, ["run", "advance", "--run", run_id])
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or not facts.get("waiting"):
        problems.append(f"解除后 advance 未能恢复推进：{(payload or {}).get('code')} {facts}")

    # ④ 可选决定的状态绑定：拿本次暂停之前的决定（不含 paused_at）来清下一次暂停 → 拒
    rc, _payload = _run(project, ["run", "pause", "--run", run_id, "--reason", "再停一次"])
    if rc != 0:
        raise H.Precondition("第二次 pause 失败")
    # Decision 的六个必需键见机制稿 §1.1；这里只关心 subject 的状态绑定
    def _decision(subject, choice="resume", reason="人决定恢复"):
        return {"source": "human", "at": "2026-11-12T00:00:00.000000Z", "subject": subject,
                "object_digest": digest, "choice": choice, "reason": reason}

    second_paused = json.load(open(run_path, encoding="utf-8"))
    second_paused_at = (second_paused.get("paused_reason") or {}).get("at")
    stale = os.path.join(root, "stale.json")
    json.dump([_decision([run_id], reason="上次的决定")], open(stale, "w"), ensure_ascii=False)
    rc, payload = _run(project, ["run", "resume", "--run", run_id, "--decision", stale])
    if rc == 0 or (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"旧决定清了新暂停：rc={rc} code={(payload or {}).get('code')}")

    # ⑤ 针对本次暂停的决定（subject 含 paused_at）应被接受，并留下决定引用
    good = os.path.join(root, "good.json")
    json.dump([_decision([run_id, "暂停于", second_paused_at])], open(good, "w"), ensure_ascii=False)
    rc, payload = _run(project, ["run", "resume", "--run", run_id, "--decision", good])
    if rc != 0:
        problems.append(f"针对本次暂停的决定被拒：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    else:
        record = json.load(open(run_path, encoding="utf-8"))
        if not (record.get("resumed") or {}).get("decision"):
            problems.append("resumed 未留下决定引用")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
