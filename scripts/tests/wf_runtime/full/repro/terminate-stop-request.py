#!/usr/bin/env python3
"""B1：写权不可核时 `run terminate` **只读接收停止请求**（机制稿 §7.4 + §4.4 侧车窄例外）。

断言链：
1. 他人持有写权时 terminate 仍被阻断（`WF_WRITER_BUSY`），但 facts 里带回 `stop_request`；
2. 请求落在**本会话侧车**（`.wf/.runtime/sessions/<key>.json`），不写任何项目记录；
3. 写权恢复后 `run terminate --preview` 能把该请求带出来（`pending_stop_request`）；
4. 侧车里的请求**不是**终止事实：实例 `terminal` 仍为空。

注入形态 = 不记侧车（模拟"阻断就完事"）→ 目标断言 1/2 变红。
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

OWNER = "sess-OWNER"
OTHER = "sess-OTHER"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''    receipt = _record_stop_request(ctx, run_id, plan_path, holder)'''
TO = '''    receipt = None  # 注入：不记停止请求'''

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
    return f"{MARKER}\n```json\n{json.dumps(doc, ensure_ascii=False, indent=2)}\n```\n\n# 说明\n"


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/one-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    creation = {"definition_id": "one-step", "definition_digest": digest, "inputs": {},
                "steps": {"change": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args, sid=OWNER):
        return H.cli(project, args + ["--json"], sid=sid,
                     inputs={"generation": H.generation(project)})

    for args in (["definition", "prepare", "--id", "one-step"],
                 ["run", "create", "--creation", creation_path]):
        rc, payload = run(args)
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        if args[0] == "run":
            run_id = ((payload or {}).get("facts") or {})["run"]["id"]

    plan_path = os.path.join(root, "plan.json")
    json.dump([{"object": "2026-" + "0" * 32,
                "decision_ref": {"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                                 "subject": ["x"], "object_digest": digest,
                                 "choice": "放弃", "reason": "停止"},
                "reason": "实例终止"}], open(plan_path, "w"), ensure_ascii=False)

    problems = []
    # ① 保持写权在 OWNER 手里，由 OTHER 发起终止
    rc, payload = run(["run", "terminate", "--run", run_id, "--plan", plan_path], sid=OTHER)
    facts = (payload or {}).get("facts") or {}
    receipt = facts.get("stop_request")
    if rc == 0 or (payload or {}).get("code") != "WF_WRITER_BUSY":
        problems.append(f"他人持写权时未被阻断：rc={rc} code={(payload or {}).get('code')}")
    if not isinstance(receipt, dict) or receipt.get("run") != run_id:
        problems.append(f"未回执停止请求（目标断言）：{receipt}")
    # ② 侧车落盘、项目记录未动（侧车文件名是会话键的派生值，按内容找而不是按名字猜）
    sessions_dir = os.path.join(project, ".wf/.runtime/sessions")
    stored = {}
    if os.path.isdir(sessions_dir):
        for name in os.listdir(sessions_dir):
            try:
                candidate = json.load(open(os.path.join(sessions_dir, name), encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if (candidate.get("stop_request") or {}).get("run") == run_id:
                stored = candidate["stop_request"]
                break
    if not stored:
        problems.append("侧车未写停止请求")
    record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json"),
                            encoding="utf-8"))
    if record.get("terminal"):
        problems.append("侧车请求被写成了终止事实（terminal 不应有值）")
    if record.get("closing"):
        problems.append("侧车请求写了 closing（应零项目写入）")

    # ③ 写权恢复后预览带出该请求
    rc, payload = run(["run", "terminate", "--run", run_id, "--preview"], sid=OTHER)
    facts = (payload or {}).get("facts") or {}
    if (facts.get("pending_stop_request") or {}).get("run") != run_id:
        problems.append(f"预览没带出停止请求：{facts.get('pending_stop_request')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
