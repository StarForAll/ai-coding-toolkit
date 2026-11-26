#!/usr/bin/env python3
"""六轮-1：人判/略过步骤记录后，`run advance` 必须推进到下一步（不把合法中间态报成历史损坏）。

obligation（设计稿 §5.8、§7.3）：人判步骤与按 `creation.steps` 声明略过的步骤都**合法地没有任务映射**
（`cursor.task_id: null`，结果在 `step_results` 里）。重入 advance 时按「步骤类型 + 已落盘结果」结案推进；
只有「游标步骤既无任务映射又无结果」才是 `WF_HISTORY_UNRESOLVED`。

红模：把「已落盘结果即结案」的分支关掉（退回修复前：只要有 step_id 就要 task_map），
第二次 advance 必报 `WF_HISTORY_UNRESOLVED` → 目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-ADV6"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''            elif recorded.get("kind") in ("satisfied", "skipped"):
'''
TO = '''            elif recorded.get("kind") in ("satisfied", "skipped") and False:
'''


def _human(step_id, title, choices=("yes", "no")):
    return {"id": step_id, "type": "human", "title": title, "required": True, "skip": None,
            "inputs": [], "outputs": [],
            "question": f"{title}？", "choices": list(choices), "human_points": []}


def _task(step_id, title, skip=None):
    return {"id": step_id, "type": "task", "title": title, "task_kind": "ordinary",
            "inputs": [], "outputs": [], "required": not bool(skip), "skip": skip,
            "human_points": ([{"id": skip["decision_point"], "question": "是否略过？"}]
                             if skip else []),
            "goal": f"完成 {title}", "acceptance": ["验收通过"],
            "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                         "required": True, "skip": None, "human_points": []}],
            "verifications": [{"id": f"v-{step_id}", "source": "current_plan",
                               "established_by": {"kind": "current_task"},
                               "stored_in": {"kind": "task_plan", "verification_id": f"v-{step_id}"},
                               "consume_at": "check"}]}


def _definition(workflow_id, steps):
    doc = {"format_version": 1, "workflow_id": workflow_id, "content_version": 1,
           "purpose": "复核人判/略过后的推进", "applicability": "已有基线",
           "inputs": {}, "steps": steps, "completion": ["全部步骤记录结果"]}
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def _install(project, workflow_id, steps):
    text = _definition(workflow_id, steps)
    directory = os.path.join(project, ".wf/user-workflows")
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, f"{workflow_id}.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _advance_sid(project, run_id, sid, decision=None):
    args = ["run", "advance", "--run", run_id, "--json"]
    if decision:
        args += ["--decision", decision]
    return H.cli(project, args, sid=sid, inputs={"generation": H.generation(project)})


def _create_sid(project, root, workflow_id, digest, steps, sid):
    creation = {"definition_id": workflow_id, "definition_digest": digest,
                "inputs": {}, "steps": steps}
    path = os.path.join(root, f"creation-{workflow_id}.json")
    json.dump(creation, open(path, "w"), ensure_ascii=False)
    auth = H.creation_authorization(project, root, path, sid=sid)
    rc, payload = H.cli(project, ["run", "create", "--creation", path,
                                  "--authorization", auth, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"run create 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    return (payload.get("facts") or {})["run"]["id"]


def check():
    problems = []
    import subprocess
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    # ---- 场景 A：人判步骤 → 下一步任务步骤 ----
    text = _definition("human-first", [_human("confirm", "确认开工"), _task("build", "实现")])
    directory = os.path.join(project, ".wf/user-workflows")
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "human-first.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    prepare_auth = H.prepare_authorization(project, root, "human-first", sid=SID)
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "human-first",
                                  "--authorization", prepare_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"prepare 失败：{(payload or {}).get('code')}")
    run_id = _create_sid(project, root, "human-first", digest,
                         {"confirm": "applicable", "build": "applicable"}, SID)
    subprocess.run(["git", "add", "-A"], cwd=project, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-qm", "definition human-first"], cwd=project, check=True,
                   capture_output=True)

    rc, payload = _advance_sid(project, run_id, SID)
    if (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        raise H.Precondition(f"人判步骤未要求答复：rc={rc} code={(payload or {}).get('code')}")
    decision = os.path.join(root, "answer.json")
    json.dump([dict(F.decision(["confirm", "确认开工"], "yes"), reason="人确认开工")],
              open(decision, "w"), ensure_ascii=False)
    rc, payload = _advance_sid(project, run_id, SID, decision)
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"答复记录失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    rc, payload = _advance_sid(project, run_id, SID)
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    build_task = facts.get("task")
    if code != "WF_OK":
        raise H.TargetFailure(f"人判步骤之后的 advance 未推进：code={code} facts={facts}")
    if not build_task:
        problems.append(f"未在下一步（build）建任务：facts={facts}")
    if (facts.get("cursor") or {}).get("step_id") != "build":
        problems.append(f"游标未移到 build：{facts.get('cursor')}")

    # ---- 场景 B：略过步骤 → 下一步人判步骤 ----
    # 另一个项目 + 另一个会话：场景 A 的会话已绑定到在途实例，实例创建要求写权空闲（§5.8）。
    skip_root, _skip_lib, _skip_payload = H.stage()
    skip_project = H.deploy(skip_root)
    H.ensure_project_config(skip_project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(skip_project, ".wf/lib/wflib/runs.py"), FROM, TO)
    skip = {"decision_point": "skip-opt", "condition": "本次不需要该步骤", "downstream": []}
    _install(skip_project, "skip-flow", [_task("opt", "可选步骤", skip=skip), _human("final", "收尾确认")])
    subprocess.run(["git", "add", "-A"], cwd=skip_project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "definition skip-flow"], cwd=skip_project,
                   check=True, capture_output=True)
    text = open(os.path.join(skip_project, ".wf/user-workflows/skip-flow.md"), encoding="utf-8").read()
    skip_digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    skip_auth = H.prepare_authorization(skip_project, skip_root, "skip-flow", sid="sess-ADV7")
    rc, payload = H.cli(skip_project, ["definition", "prepare", "--id", "skip-flow",
                                       "--authorization", skip_auth, "--json"],
                        sid="sess-ADV7", inputs={"generation": H.generation(skip_project)})
    if rc != 0:
        raise H.Precondition(f"prepare(skip-flow) 失败：{(payload or {}).get('code')}")
    skip_run = _create_sid(skip_project, skip_root, "skip-flow", skip_digest,
                           {"opt": "skipped", "final": "applicable"}, "sess-ADV7")
    skip_decision = os.path.join(skip_root, "skip.json")
    json.dump([dict(F.decision(["opt", "可选步骤"], "skip"), reason="本次不需要")],
              open(skip_decision, "w"), ensure_ascii=False)
    rc, payload = _advance_sid(skip_project, skip_run, "sess-ADV7", skip_decision)
    if (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"略过记录失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    rc, payload = _advance_sid(skip_project, skip_run, "sess-ADV7")
    code = (payload or {}).get("code")
    facts = (payload or {}).get("facts") or {}
    if code == "WF_HISTORY_UNRESOLVED":
        raise H.TargetFailure(f"略过步骤之后的 advance 报历史损坏：{facts}")
    if code == "WF_OK" and facts.get("step") != "final":
        problems.append(f"略过之后没有走到 final：{facts}")

    # ---- 场景 C：任务已异常归档 → 出口必须是实例层可执行动作 ----
    if not problems and build_task:
        abandon = os.path.join(root, "abandon.json")
        json.dump([dict(F.decision([build_task], "abandon"), reason="放弃该步骤")],
                  open(abandon, "w"), ensure_ascii=False)
        disposition = os.path.join(root, "disposition.json")
        json.dump({"changes": []}, open(disposition, "w"), ensure_ascii=False)
        rc, payload = H.cli(project, ["task-abandon", "--task", build_task, "--decision", abandon,
                                      "--disposition", disposition, "--json"],
                            sid=SID, inputs={"generation": H.generation(project)})
        if rc != 0:
            raise H.Precondition(f"task-abandon 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
        rc, payload = _advance_sid(project, run_id, SID)
        code = (payload or {}).get("code")
        facts = (payload or {}).get("facts") or {}
        exits = facts.get("exits") or []
        if code != "WF_SEMANTIC_DECISION":
            problems.append(f"异常归档后 advance 未停在需人决策：code={code} facts={facts}")
        elif not any("run terminate" in str(item) for item in exits):
            problems.append(f"异常归档出口未给实例层动作：exits={exits}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None

if __name__ == "__main__":
    sys.exit(H.main(check))
