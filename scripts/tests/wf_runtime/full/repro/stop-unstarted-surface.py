#!/usr/bin/env python3
"""629.s1.c1：「已批准但未开工」任务收工时，keep 的归属边界来自 plan.touch_paths。

obligation（§96 ① s1 × c1）：未开工任务的批准触碰面由 `approved_touch_paths` 回退到
`plan.touch_paths`；收工 keep 必须**按这个面**判定「保留 WIP」是否越界，且越界项要列在
`facts.out_of_scope`，不能只给一个笼统拒绝。

注入形态：未开工时不再回退 plan（批准面变空）——于是本任务自己的合法保留被误判越界。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-S1"
BLOCK = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def approved_not_started(project, root, title="s1 源任务"):
    """建任务 → 写 PRD → 批准；**不开工**（正是 s1 状态）。"""
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(BLOCK, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, "approve-s1.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest()), artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    return task_id


def stop(project, root, subject, tag):
    path = os.path.join(root, f"stop-s1-{tag}.json")
    json.dump([F.decision(subject, "keep")], open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return H.cli(project, ["stop", "--decision", path, "--json"], sid=SID,
                 inputs={"generation": H.generation(project)})


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")      # 批准面内
    open(os.path.join(project, "notes.txt"), "w").write("n\n")     # 批准面外
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                '    if snapshot is None and not started:\n'
                '        # 未开工：记录默认就带 `entry_snapshot: null`，此时才允许回退 plan\n'
                '        return list((task.get("plan") or {}).get("touch_paths") or [])\n',
                '    if snapshot is None and not started:\n'
                '        return []  # 注入：未开工不回退 plan（批准面变空）\n')
    approved_not_started(project, root)
    problems = []

    # ① 声明漏项：待保留路径没写全 → 拒绝（不得静默放行）
    rc, payload = stop(project, root, ["notes.txt"], "unlisted")
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_WORKSPACE_UNRESOLVED", "s1.c1 漏列")
    if rc == 0:
        problems.append("漏列时仍放行")

    # ② 越界项：两条都声明后，越界判定必须只点名 notes.txt（边界来自 plan.touch_paths）
    rc, payload = stop(project, root, ["pkg/b.py", "notes.txt"], "out-of-scope")
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_WORKSPACE_UNRESOLVED", "s1.c1 越界")
    facts = (payload or {}).get("facts") or {}
    if rc == 0:
        problems.append("越界路径未被拒绝")
    elif facts.get("out_of_scope") != ["notes.txt"]:
        problems.append(f"越界项不是 ['notes.txt']：{facts.get('out_of_scope')}")

    # ③ 正例：只有批准面内的路径 → keep 成立
    rc, payload = stop(project, root, ["pkg/b.py"], "in-range")
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"批准面内保留被拒：{(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
