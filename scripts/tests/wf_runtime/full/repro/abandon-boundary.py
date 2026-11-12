#!/usr/bin/env python3
"""637 异常归档边界：放弃必须「先预览、再逐项给去向」，缺项即拒且零写入。

obligation（设计稿 §5.6、机制稿 §6.4）：task-abandon 是异常归档，不套正常完成条件，
但也不允许把人未处理的 WIP 一起带走——① 无 `--disposition` 时只回预览、不写记录；
② 去向未覆盖每个未提交路径 → `WF_WORKSPACE_UNRESOLVED` 并点名缺项；
③ 覆盖 + 提交授权后成立，终态是 **abnormal**（不得记为正常完成）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S
import _review_flow as F

SID = "sess-A637"
# 2026-11-12：放弃本体抽进 `_apply_abandon()` 供 `run terminate` 共用，缩进随之下调一级。
FROM = '    uncovered = _uncovered_paths(preview["uncommitted"], disposition)\n'
TO = '    uncovered = []  # 注入：不核去向覆盖\n'


def task_record(project, task_id):
    for base in (os.path.join(project, ".wf/tasks"),
                 os.path.join(project, ".wf/tasks/archive/2026-11")):
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            if name.endswith(task_id[-6:] + "-s3 任务") or task_id[-6:] in name:
                path = os.path.join(base, name, "task.json")
                if os.path.isfile(path):
                    return json.load(open(path, encoding="utf-8"))
    return None


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    task_id, task_dir = S.started_task(project, root, sid=SID, title="s3 任务")
    open(os.path.join(project, "pkg/a.py"), "w").write("a-wip\n")
    problems = []

    decision = os.path.join(root, "abandon.json")
    json.dump([F.decision(["pkg/a.py"], "abandon")], open(decision, "w", encoding="utf-8"),
              ensure_ascii=False)

    # ① 无 disposition：只回预览，记录不变
    before = open(os.path.join(task_dir, "task.json"), "rb").read()
    rc, payload = H.cli(project, ["task-abandon", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_SEMANTIC_DECISION", "637 无去向")
    after = open(os.path.join(task_dir, "task.json"), "rb").read()
    if rc == 0:
        problems.append("缺 disposition 仍放行")
    if after != before:
        problems.append("预览路径改写了任务记录（应零写入）")

    # ② 去向未覆盖未提交路径：点名缺项
    if not problems:
        partial = os.path.join(root, "abandon-partial.json")
        json.dump({"changes": [{"object": "pkg/other.py", "reason": "x"}]},
                  open(partial, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = H.cli(project, ["task-abandon", "--task", task_id, "--decision", decision,
                                      "--disposition", partial, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                            "WF_WORKSPACE_UNRESOLVED", "637 去向缺项")
        facts = (payload or {}).get("facts") or {}
        if facts.get("uncovered") != ["pkg/a.py"]:
            problems.append(f"缺项不是 ['pkg/a.py']：{facts.get('uncovered')}")

    # ③ 覆盖 + 提交授权 → 成立，终态 abnormal
    if not problems:
        full = os.path.join(root, "abandon-full.json")
        json.dump({"changes": [{"object": "pkg/a.py", "reason": "由人提交后放弃"}]},
                  open(full, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump([F.decision(["pkg/a.py"], "abandon"), F.decision(["pkg/a.py"], "commit")],
                  open(decision, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = H.cli(project, ["task-abandon", "--task", task_id, "--decision", decision,
                                      "--disposition", full, "--json"], sid=SID,
                            inputs={"generation": H.generation(project)})
        if rc != 0 or (payload or {}).get("code") != "WF_OK":
            problems.append(f"覆盖后仍未成立：{(payload or {}).get('code')}")
        else:
            record = task_record(project, task_id)
            if not record:
                problems.append("放弃后找不到任务记录")
            elif record.get("terminal") != "abnormal":
                problems.append(f"终态不是 abnormal：{record.get('terminal')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
