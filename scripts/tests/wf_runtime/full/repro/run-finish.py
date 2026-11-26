#!/usr/bin/env python3
"""P1-3：`run finish` 正常结束——前置全是事实核对，不代调任务 finish（机制稿 §7.4）。

断言链：
1. 只剩一个必需步骤未满足 → `WF_SEMANTIC_DECISION` 并列出缺哪步（不硬结束）；
2. 人判步骤答复后（single human step）→ `terminal=normal`、`closing.mode=normal`、`ended_at` 有值；
3. 无提交授权时停在 `persist_pending` 并如实说明"记录组尚未提交"；
4. 终态后 `advance` 被拒。

注入形态 = 结束时不写 `terminal` → 目标断言 2 变红。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-FIN"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''        run = dict(run, terminal="normal", ended_at=records.now_str(),\n'''
TO = '''        run = dict(run, ended_at=records.now_str(),  # 注入：不写终态\n'''


def _definition():
    doc = {"format_version": 1, "workflow_id": "gate-step", "content_version": 1,
           "purpose": "只有一个确认步骤", "applicability": "已有基线", "inputs": {},
           "steps": [{"id": "confirm", "type": "human", "title": "确认交付",
                      "question": "本次交付是否完成？", "choices": ["完成", "未完成"],
                      "inputs": [], "outputs": [], "required": True, "skip": None,
                      "human_points": [{"id": "ask-confirm", "question": "确认？"}]}],
           "completion": ["确认步骤有答复"]}
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
    with open(os.path.join(project, ".wf/user-workflows/gate-step.md"), "w", encoding="utf-8") as h:
        h.write(text)
    creation = {"definition_id": "gate-step",
                "definition_digest": "sha256:" + __import__("hashlib").sha256(text.encode()).hexdigest(),
                "inputs": {}, "steps": {"confirm": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)

    def run(args):
        return H.cli(project, args + ["--json"], sid=SID,
                     inputs={"generation": H.generation(project)})

    prepare_auth = H.prepare_authorization(project, root, "gate-step", sid=SID)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    for args in (["definition", "prepare", "--id", "gate-step", "--authorization", prepare_auth],
                 ["run", "create", "--creation", creation_path,
                  "--authorization", create_auth]):
        rc, payload = run(args)
        if rc != 0:
            raise H.Precondition(f"{args[0]} 失败：{(payload or {}).get('code')}")
        if args[0] == "run":
            run_id = ((payload or {}).get("facts") or {})["run"]["id"]
    problems = []
    # ① 未满足必需步骤 → 拒
    rc, payload = run(["run", "finish", "--run", run_id])
    if rc == 0 or (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"未满足步骤仍结束：rc={rc} code={(payload or {}).get('code')}")
    else:
        unsat = ((payload or {}).get("facts") or {}).get("unsatisfied_steps") or []
        if [item.get("step") for item in unsat] != ["confirm"]:
            problems.append(f"未列出缺哪步：{unsat}")

    # ② 答复后正常结束
    answer = os.path.join(root, "answer.json")
    json.dump([{"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                "subject": ["confirm"], "object_digest": creation["definition_digest"],
                "choice": "完成", "reason": "人确认交付完成"}],
              open(answer, "w"), ensure_ascii=False)
    rc, payload = run(["run", "advance", "--run", run_id, "--decision", answer])
    if rc != 0:
        raise H.Precondition(f"advance 记录答复失败：{(payload or {}).get('code')}")
    rc, payload = run(["run", "finish", "--run", run_id])
    if rc != 0:
        raise H.TargetFailure(f"finish 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    record = json.load(open(os.path.join(project, ".wf/workflow-runs", f"{run_id}.json"),
                            encoding="utf-8"))
    if record.get("terminal") != "normal":
        problems.append("实例未写 terminal=normal（目标断言）")
    if (record.get("closing") or {}).get("mode") != "normal":
        problems.append(f"closing.mode 不是 normal：{record.get('closing')}")
    if not record.get("ended_at"):
        problems.append("未写 ended_at")
    # ③ 无授权 → persist_pending 且如实说明
    if (record.get("action") or {}).get("state") != "persist_pending":
        problems.append(f"无授权时动作状态：{(record.get('action') or {}).get('state')}")
    facts = (payload or {}).get("facts") or {}
    if facts.get("persisted") is not False:
        problems.append(f"无授权却报已持久化：{facts.get('persisted')}")
    if "尚未提交" not in str((payload or {}).get("next") or ""):
        problems.append(f"未如实说明记录组未提交：{(payload or {}).get('next')}")
    # ④ 终态后 advance 被拒
    rc, payload = run(["run", "advance", "--run", run_id])
    if rc == 0:
        problems.append("终态实例仍可推进")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
