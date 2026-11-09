#!/usr/bin/env python3
"""A3：transfer 的承接对象由 `Decision.target_task` 指定（subject 只列待承接路径）。

缺陷形态（修复前）：把 subject 首项当承接任务 id，于是 id 与路径混在一张清单里被逐项指纹化，
实际表达不出"承接任务 + 待承接路径"，承接核验永远走不到。
本用例证明：入口确实读取 `target_task`，并对"不存在"与"自承接"给出结构化拒绝。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 退回"subject 首项即 id"的旧实现
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                '            target = str(declared.get("target_task") or "").strip()',
                '            target = str((declared.get("subject") or [""])[0] or "").strip()  # 注入')
    sid = "sess-T1"
    task_id, _task_dir = F.build_task(project, root, "transfer 源任务", sid=sid)
    H.cli(project, ["task-start", "--task", task_id, "--json"], sid=sid,
          inputs={"generation": H.generation(project)})

    problems = []
    cases = {
        "nonexistent": "2026-" + "a" * 32,
        "self": task_id,
    }
    for label, target in cases.items():
        path = os.path.join(root, f"stop_{label}.json")
        decision = dict(F.decision(["pkg/a.py"], "transfer"), target_task=target)
        json.dump([decision], open(path, "w"), ensure_ascii=False)
        rc, payload = H.cli(project, ["stop", "--decision", path, "--json"], sid=sid,
                            inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK", "WF_SEMANTIC_DECISION", "transfer-target-task-field")
        facts = (payload or {}).get("facts") or {}
        if rc == 0:
            problems.append(f"{label}：未被拒绝")
            continue
        if (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
            problems.append(f"{label}：原因码 {(payload or {}).get('code')}")
        if facts.get("target") != target:
            problems.append(f"{label}：未回显 target_task（{facts.get('target')}）")
        if not facts.get("exits"):
            problems.append(f"{label}：未给出口")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
