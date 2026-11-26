#!/usr/bin/env python3
"""P1-5：`task-rework` 建 R 并让 T 挂起；同实例时登记 sequence_changes 与 cursor（机制稿 §6.2）。

断言链（同实例分支）：
1. R 的 `rework_of=T`、`prerequisites` 继承 T 的原前置（此处为空）；
2. T 的 `prerequisites` 增 R、`suspended=true`、**不自动 paused**（同实例内 T 不暂停）；
3. 实例 `sequence_changes` 记 `{kind:rework, source_task:T, task_id:R, resume_task:T}`，
   `cursor.task_id` 临时定位 R；
4. `task-reassess` 在 R 未归档时返回 waiting（不清挂起、不造原因码）。

注入形态 = 不把 R 写进 T 的 prerequisites（模拟"只建返工、不建立依赖"）→ 目标断言 2 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-RWK"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''        task["prerequisites"] = list(task.get("prerequisites") or []) + [rework_id]\n'''
TO = '''        task["prerequisites"] = list(task.get("prerequisites") or [])  # 注入：不建立依赖\n'''

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
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/one-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "one-step", "definition_digest": digest, "inputs": {},
                "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args):
        return H.cli(project, args + ["--json"], sid=SID,
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
    parent = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not parent:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')}")

    decision_path = os.path.join(root, "rework.json")
    json.dump([{"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                "subject": [parent, "改动方案写错了"], "object_digest": digest,
                "choice": "返工", "reason": "实施方向错，需要重做"}],
              open(decision_path, "w"), ensure_ascii=False)
    rc, payload = run(["task-rework", "--task", parent, "--decision", decision_path])
    facts = (payload or {}).get("facts") or {}
    if rc != 0:
        raise H.TargetFailure(f"rework 失败：{(payload or {}).get('code')} {facts}")
    rework_id = facts.get("rework")
    problems = []
    if not rework_id:
        problems.append("未返回返工任务 id")
    else:
        rework_dir = os.path.join(project, facts["directory"], "task.json")
        rework = json.load(open(rework_dir, encoding="utf-8"))
        if rework.get("rework_of") != parent:
            problems.append(f"R 未记 rework_of：{rework.get('rework_of')}")
        if rework.get("run_id") is not None:
            problems.append("R 不应自动加入实例（须独立批准与开工）")
    parent_dir = [n for n in os.listdir(os.path.join(project, ".wf/tasks"))
                  if n.startswith(parent)][0]
    parent_record = json.load(open(os.path.join(project, ".wf/tasks", parent_dir, "task.json"),
                                   encoding="utf-8"))
    if rework_id and rework_id not in (parent_record.get("prerequisites") or []):
        problems.append("目标断言：T 的前置未增 R")
    if parent_record.get("suspended") is not True:
        problems.append("T 未挂起")
    if parent_record.get("paused"):
        problems.append("同实例内 T 不应自动暂停")
    run_record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json"),
                                encoding="utf-8"))
    sequence = run_record.get("sequence_changes") or []
    if not any(item.get("kind") == "rework" and item.get("source_task") == parent
               and item.get("task_id") == rework_id and item.get("resume_task") == parent
               for item in sequence):
        problems.append(f"sequence_changes 未登记返工：{sequence}")
    if (run_record.get("cursor") or {}).get("task_id") != rework_id:
        problems.append(f"cursor 未临时定位到 R：{run_record.get('cursor')}")

    # ④ R 未归档 → 游标在 R 上，advance 必须报等待且不把 R 当步骤完成
    rc, payload = run(["run", "locate", "--run", run_id])
    facts_locate = (payload or {}).get("facts") or {}
    if (facts_locate.get("cursor") or {}).get("task_id") != rework_id:
        problems.append(f"locate 未反映临时游标：{facts_locate.get('cursor')}")
    rc, payload = run(["run", "advance", "--run", run_id])
    facts_advance = (payload or {}).get("facts") or {}
    if facts_advance.get("controlled_rework") != rework_id:
        problems.append(f"advance 未识别受控返工：{facts_advance}")
    if (facts_advance.get("rework_status") or "") == "archived":
        problems.append("R 未归档却报已归档")
    run_path = os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")
    record = json.load(open(run_path, encoding="utf-8"))
    if (record.get("cursor") or {}).get("task_id") != rework_id:
        problems.append("advance 把游标从 R 上挪走了（应保持并报等待）")
    # 复评本身要针对 T：把游标按登记返回（R 未归档时 advance 只报等待，这里手工置回以测复评）
    record["cursor"] = {"step_id": (record.get("cursor") or {}).get("step_id"), "task_id": parent}
    json.dump(record, open(run_path, "w"), ensure_ascii=False, indent=2)
    rc, payload = run(["task-reassess", "--task", parent])
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or facts.get("waiting") is not True:
        problems.append(f"复评未报 waiting：rc={rc} {facts.get('unmet')}")
    if "rework_set_all_archived" not in (facts.get("unmet") or []):
        problems.append(f"未点名未归档的返工：{facts.get('unmet')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
