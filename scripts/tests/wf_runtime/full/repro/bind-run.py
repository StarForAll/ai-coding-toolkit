#!/usr/bin/env python3
"""P1-2 收口：`bind --run` 让新会话接续在途实例（机制稿 §2.1、§6.1 的绑定面）。

断言链：
1. 首个会话创建实例并推进（游标指向任务）；释放写权后，**新会话**能 `bind --run`；
2. 绑定后的运行态 `current_task` 取实例游标所指的任务（不是 null）；
3. 绑定后同一新会话可直接 `run advance`（绑定与写权 scope 都指向该实例）；
4. 正常结束的实例不给绑定（`WF_BINDING_MISMATCH`）——正常结束只回报结果。

注入形态 = 绑定后运行态写 `current_task: null`（模拟"实例绑定没把当前任务带过来"）→ 目标断言 2 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

FIRST = "sess-BR1"
SECOND = "sess-BR2"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''    run = runs_mod.load_run(ctx.root, target) or {}
    return (run.get("cursor") or {}).get("task_id")'''
TO = '''    return None  # 注入：实例绑定不带当前任务'''

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


def session_key(sid):
    """会话侧车 key：与 wflib.session.session_key 同算法（provider + identity）。"""
    payload = {"provider": "host", "identity": {"host_id": "dsh", "session_id": sid}}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")).hexdigest()


def runtime_record(project, sid):
    """按会话 key 精确读取运行态侧车；目录里存在旧会话文件时也不得按 readdir 顺序取。"""
    path = os.path.join(project, ".wf/.runtime/sessions", session_key(sid) + ".json")
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


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
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/one-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "one-step", "definition_digest": digest, "inputs": {},
                "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args, sid):
        return H.cli(project, args + ["--json"], sid=sid,
                     inputs={"generation": H.generation(project)})

    prepare_auth = H.prepare_authorization(project, root, "one-step", sid=FIRST)
    create_auth = H.creation_authorization(project, root, creation_path, sid=FIRST)
    for args in (["definition", "prepare", "--id", "one-step", "--authorization", prepare_auth],
                 ["run", "create", "--creation", creation_path,
                  "--authorization", create_auth]):
        rc, payload = run(args, FIRST)
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        if args[0] == "run":
            run_id = ((payload or {}).get("facts") or {})["run"]["id"]
    rc, payload = run(["run", "advance", "--run", run_id], FIRST)
    task_id = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{(payload or {}).get('code')}")

    problems = []
    # §4.4：释放写权要求对象已暂停或已终态——先暂停实例，再释放，新会话才能接
    rc, payload = run(["run", "pause", "--run", run_id, "--reason", "换会话"], FIRST)
    if rc != 0:
        raise H.Precondition(f"run pause 失败：{(payload or {}).get('code')}")
    rc, payload = run(["writer", "release"], FIRST)
    if rc != 0:
        raise H.Precondition(f"writer release 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    # ① 新会话 bind --run
    rc, payload = run(["bind", "--run", run_id], SECOND)
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.TargetFailure(f"bind --run 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    facts = (payload or {}).get("facts") or {}
    if ((facts.get("binding") or {}).get("object") or {}).get("kind") != "run":
        problems.append(f"绑定对象不是实例：{facts.get('binding')}")

    # ② 运行态 current_task 取游标所指任务。必须按**本会话 key** 精确读取侧车：
    # 目录里可能同时存在旧会话（sess-BR1）与新会话（sess-BR2）文件，readdir 顺序不是语义，
    # 取任意 object.id 匹配的文件会把旧会话的正确 current_task 误当成本会话证据。
    runtime = runtime_record(project, SECOND)
    if runtime is None:
        problems.append(f"未写本会话的运行态：{session_key(SECOND)}")
    else:
        if (runtime.get("object") or {}).get("id") != run_id:
            problems.append(f"运行态对象不是本次实例：{runtime.get('object')}")
        if runtime.get("current_task") != task_id:
            problems.append(f"运行态 current_task 不是游标任务：{runtime.get('current_task')}")

    # ③ 新会话解除暂停后可直接推进（等待当前任务，而不是被绑定挡下）
    rc, payload = run(["run", "resume", "--run", run_id], SECOND)
    if rc != 0:
        problems.append(f"新会话无法解除暂停：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    rc, payload = run(["run", "advance", "--run", run_id], SECOND)
    if rc != 0 or ((payload or {}).get("facts") or {}).get("waiting") is not True:
        problems.append(f"新会话无法推进：rc={rc} {(payload or {}).get('code')} "
                        f"{(payload or {}).get('facts')}")

    # ④ 正常结束的实例不给绑定
    plan_path = os.path.join(root, "plan.json")
    entry = {"object": task_id,
             "decision_ref": {"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                              "subject": [task_id], "object_digest": digest,
                              "choice": "保留", "reason": "保留任务独立接续"},
             "reason": "实例异常终止"}
    json.dump([entry], open(plan_path, "w"), ensure_ascii=False)
    rc, payload = run(["run", "terminate", "--run", run_id, "--plan", plan_path], SECOND)
    if rc != 0:
        raise H.Precondition(f"terminate 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    run(["writer", "release"], SECOND)
    rc, payload = run(["bind", "--run", run_id], "sess-BR3")
    if rc == 0 or (payload or {}).get("code") != "WF_BINDING_MISMATCH":
        problems.append(f"已结束实例仍可绑定：rc={rc} code={(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
