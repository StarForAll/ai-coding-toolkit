#!/usr/bin/env python3
"""P1-4：`dep add|rm` 建边/删边必须可跑，并且只改未归档持有侧（机制稿 §6.1）。

此前 `dep` 是 `_unavailable(2, ...)` 桩。建边/删边是 `dependency.change` 状态动作，
targets 覆盖两端（D08：第二轮加入全部依赖/实例目标），环检测是 DFS 三色。

注入形态 = 去掉自环守卫 → 自环被接受，目标断言必须变红。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

# 自环有双重保护：显式守卫 + DFS 三色环检测。注入必须把**两层都**退回旧形态，
# 否则「自环被拒」仍可能由另一层满足，断言就测不到东西。
FROM = '    if task_id == prereq:\n'
TO = '    if False:  # 注入：不拦自环\n'
FROM_CYCLE = '            if cycle:\n'
TO_CYCLE = '            if False:  # 注入：不拦环\n'


def _pause_and_release(project, task_id, sid):
    # 前置任务的未提交改动必须先落成自己的提交，否则下一个新任务会被
    # 「他任务未处置 WIP」挡住（`assert_no_foreign_wip`，机制稿 §4.2）——那是正确行为
    import subprocess

    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", f"wf: deliver\n\nwf-task: {task_id}"],
                   cwd=project, check=True, capture_output=True)
    H.cli(project, ["task-pause", "--task", task_id, "--reason", "dep 用例", "--json"], sid=sid,
          inputs={"generation": H.generation(project)})
    H.cli(project, ["writer", "release", "--json"], sid=sid,
          inputs={"generation": H.generation(project)})


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        target = os.path.join(project, ".wf/lib/wflib/tasks.py")
        H.patch(target, FROM, TO)
        H.patch(target, FROM_CYCLE, TO_CYCLE)

    first_id, _dir = F.build_task(project, root, "dep 前置任务", sid="sess-DEP1")
    _pause_and_release(project, first_id, "sess-DEP1")

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "dep 后继任务",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid="sess-DEP2")
    if rc != 0:
        raise H.Precondition(f"task-new failed: {payload}")
    second_id = payload["facts"]["task_id"]

    problems = []
    rc, payload = H.cli(project, ["dep", "add", "--task", second_id, "--prereq", first_id, "--json"],
                        sid="sess-DEP2", inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"建边失败：{(payload or {}).get('code')} {facts}")
    elif facts.get("prerequisites") != [first_id]:
        problems.append(f"建边未写回前置：{facts.get('prerequisites')}")

    rc, payload = H.cli(project, ["dep", "add", "--task", second_id, "--prereq", first_id, "--json"],
                        sid="sess-DEP2", inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"重复建边未幂等：{(payload or {}).get('code')}")
    elif len(((payload or {}).get("facts") or {}).get("prerequisites") or []) != 1:
        problems.append("重复建边把前置写了两遍")

    # 目标断言：自环必须拒绝
    rc, payload = H.cli(project, ["dep", "add", "--task", second_id, "--prereq", second_id, "--json"],
                        sid="sess-DEP2", inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code") if rc != 0 else "WF_OK"
    if code != "WF_DEPENDENCY_UNMET":
        problems.append(f"自环未被拒：rc={rc} code={code}")

    rc, payload = H.cli(project, ["dep", "rm", "--task", second_id, "--prereq", first_id, "--json"],
                        sid="sess-DEP2", inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or facts.get("prerequisites") != []:
        problems.append(f"删边未生效：{(payload or {}).get('code')} {facts.get('prerequisites')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
