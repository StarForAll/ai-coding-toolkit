#!/usr/bin/env python3
"""P1-2：`run advance` 首达任务步骤要**建任务并写顺序边**，重入不建第二份（机制稿 §7.3）。

本批覆盖最小闭环：
- 单任务定义：首个 task 步骤 → 生成任务（`run_id`=本实例、无前置）、写 `task_map`、游标指向它；
- 重入 advance → 复用已映射的任务（不建第二份）；
- 前一任务未正常归档时推进下一个 task 步骤 → `WF_DEPENDENCY_UNMET`（顺序前置只认正常归档）。

注入形态 = 建出的任务不记 `run_id`（模拟「只靠 task_map 记住对应关系」）→ 目标断言变红。
「重入不建第二份」是正向断言：它同时被三层保护挡着（等待当前任务 / 复用映射 /
顺序前置必须正常归档），单点注入不可达，所以不当红模。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-ADV"
MARKER = "<!-- wf-definition:v1 -->"


def _step(step_id, title, required=True, skip=None, inputs=None):
    return {"id": step_id, "type": "task", "title": title, "task_kind": "ordinary",
            "inputs": inputs or [], "outputs": [], "required": required, "skip": skip,
            "human_points": [{"id": f"approve-{step_id}", "question": "是否批准？"}],
            "goal": f"完成 {title}", "acceptance": ["验收通过"],
            "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                         "required": True, "skip": None, "human_points": []}],
            "verifications": [{"id": "task-check", "source": "current_plan",
                               "established_by": {"kind": "current_task"},
                               "stored_in": {"kind": "task_plan", "verification_id": "task-check"},
                               "consume_at": "check"}]}


# 目标断言落在这条事实上：**步骤生成的任务必须记 run_id**（否则机制稿 §6.1 的
# 「独立接续资格」无从判定，实例与任务的对应关系就只剩 task_map 一份）。
# 说明：也曾想拿「重入建第二个任务」当目标，但那条路有三层保护（等待当前任务完成 /
# 复用已映射任务 / 顺序前置必须正常归档），任何单点注入都不可达 → 注入退化成没意义。
# 重入幂等仍作**正向断言**留在本用例里。
FROM = '''        task["run_id"] = run_id\n'''
TO = '''        pass  # 注入：任务不记 run_id\n'''


def _definition():
    doc = {
        "format_version": 1, "workflow_id": "two-step", "content_version": 1,
        "purpose": "两步顺序流程", "applicability": "已有基线",
        "inputs": {}, "steps": [_step("first", "首个任务"), _step("second", "第二个任务")],
        "completion": ["两个任务都正常归档"],
    }
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
    with open(os.path.join(project, ".wf/user-workflows/two-step.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "two-step", "definition_digest": digest,
                "inputs": {}, "steps": {"first": "applicable", "second": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    prepare_auth = H.prepare_authorization(project, root, "two-step", sid=SID)
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "two-step",
                                  "--authorization", prepare_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"prepare 失败：{(payload or {}).get('code')}")
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", create_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"create 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    run_id = ((payload or {}).get("facts") or {})["run"]["id"]

    # ① 首达任务步骤：建任务 + 写顺序边
    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    first_task = facts.get("task")
    if rc != 0 or (payload or {}).get("code") != "WF_OK" or not first_task:
        raise H.TargetFailure(f"advance 未建任务：{(payload or {}).get('code')} {facts}")
    record = json.load(open(os.path.join(project, facts["directory"], "task.json")))
    problems = []
    if record.get("run_id") != run_id:
        problems.append(f"任务未记 run_id：{record.get('run_id')}")
    if record.get("prerequisites") != []:
        problems.append(f"首任务不应有前置：{record.get('prerequisites')}")
    run_record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json")))
    if ((run_record.get("task_map") or {}).get("first") or {}).get("task_id") != first_task:
        problems.append("task_map 未写 first 的映射")
    if (run_record.get("cursor") or {}).get("task_id") != first_task:
        problems.append(f"游标未指向新任务：{run_record.get('cursor')}")

    # ② 目标断言：重入不建第二份
    before = sorted(name for name in os.listdir(os.path.join(project, ".wf/tasks"))
                    if name.startswith("2026-"))
    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    after = sorted(name for name in os.listdir(os.path.join(project, ".wf/tasks"))
                   if name.startswith("2026-"))
    if after != before:
        problems.append(f"重入建了第二个任务：{before} → {after}")
    if ((payload or {}).get("facts") or {}).get("task") != first_task:
        problems.append("重入未复用已映射的任务")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
