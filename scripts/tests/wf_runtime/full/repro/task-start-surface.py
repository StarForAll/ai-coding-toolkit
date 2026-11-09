#!/usr/bin/env python3
"""629.s1.c4：开工期分类器用「未开工回退到的 plan.touch_paths」划分未提交路径。

obligation（§96 ① s1 × c4）：`task-start` 对普通任务要按批准触碰面分桶——
面内的未提交改动是 e（本任务自己的活，允许开工），面外的未归属改动是 c（别的活，必须阻断）。

注入形态：未开工不回退 plan（批准面变空）→ 面内改动被打成 c，合法开工被误拦。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-S4"
BLOCK = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def approved_not_started(project, root):
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "s1 分类器",
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# s1 分类器\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(BLOCK, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, "approve-c4.json")
    json.dump([F.decision("approve", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    return task_id


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")     # 批准面内
    open(os.path.join(project, "notes.txt"), "w").write("n\n")    # 批准面外
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                '    if snapshot is None and not started:\n'
                '        # 未开工：记录默认就带 `entry_snapshot: null`，此时才允许回退 plan\n'
                '        return list((task.get("plan") or {}).get("touch_paths") or [])\n',
                '    if snapshot is None and not started:\n'
                '        return []  # 注入：未开工不回退 plan（批准面变空）\n')
    task_id = approved_not_started(project, root)
    problems = []

    # ① 面外未归属改动存在 → 开工必须阻断，且只点名 notes.txt
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_WORKSPACE_UNRESOLVED", "s1.c4 面外改动")
    facts = (payload or {}).get("facts") or {}
    if rc == 0:
        problems.append("面外未归属改动存在时仍开工")
    elif facts.get("other_tasks") != ["notes.txt"]:
        problems.append(f"阻断项不是 ['notes.txt']：{facts.get('other_tasks')}")

    # ② 清掉面外改动后，面内未提交改动属本任务 → 开工成立
    os.remove(os.path.join(project, "notes.txt"))
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"面内未提交改动导致开工被拒：{(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
