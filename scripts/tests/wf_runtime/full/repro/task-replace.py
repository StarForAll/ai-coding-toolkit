#!/usr/bin/env python3
"""P1-5（替换）：`task-replace` 建继任者 S、登记继承、异常归档 T（机制稿 §6.3）。

断言链：
1. S 的 `attribution.inherited` 记下来源任务 T 与继承路径（它是 §3.3「最终触碰集合」的一部分）；
2. T 的 `successor_id` 指向 S；T 已异常归档（`terminal=abnormal`）；
3. S 只是**规划记录**（未批准、未开工、`run_id` 为空）——继承的触碰面不是开工许可；
4. 决定里 `touch_paths` 不覆盖继承路径 → 拒且零写入（§6.3「保留原态并回规划」）。

注入形态 = 不登记继承（模拟"只建 S、不带历史触碰面"）→ 目标断言 1 变红。
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-RPL"

FROM = '''        successor["attribution"] = {"decisions": [],\n'''
TO = '''        successor["attribution"] = {"decisions": [], "inherited": []}  # 注入：不登记继承
        successor["attribution_unused"] = {"decisions": [],\n'''


def _decision(path, choice, touch_paths, reason, disposition=None):
    payload = {"source": "human", "at": "2026-11-12T00:00:00.000000Z",
               "subject": ["替换"], "object_digest": "sha256:" + "a" * 64,
               "choice": choice, "reason": reason, "touch_paths": touch_paths}
    if disposition is not None:
        payload["disposition"] = disposition
    json.dump([payload], open(path, "w"), ensure_ascii=False)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    task_id, task_dir = F.build_task(project, root, title="被替换的任务", sid=SID)
    # 让 T 有归属路径：提交一次带 trailer 的业务提交
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", f"wf: deliver\n\nwf-task: {task_id}"],
                   cwd=project, check=True, capture_output=True)

    problems = []
    # ① 不覆盖继承路径 → 拒且零写入
    narrow = os.path.join(root, "narrow.json")
    _decision(narrow, "替换", ["other/**"], "换人重做")
    rc, payload = H.cli(project, ["task-replace", "--task", task_id, "--decision", narrow,
                                  "--json"], sid=SID, inputs={"generation": H.generation(project)})
    if rc == 0 or (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"不覆盖继承路径仍替换：rc={rc} code={(payload or {}).get('code')}")
    else:
        facts = (payload or {}).get("facts") or {}
        if not facts.get("uncovered"):
            problems.append(f"未列出未覆盖的继承路径：{facts}")

    # ② 覆盖后替换成功
    wide = os.path.join(root, "wide.json")
    _decision(wide, "替换", ["pkg/**"], "换人重做", disposition={"changes": [
        {"path": "pkg/a.py", "action": "carried_by_successor"}]})
    rc, payload = H.cli(project, ["task-replace", "--task", task_id, "--decision", wide,
                                  "--json"], sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.TargetFailure(f"replace 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    facts = (payload or {}).get("facts") or {}
    successor_id = facts.get("successor")
    if not successor_id:
        raise H.TargetFailure("未返回继任者 id")
    successor = json.load(open(os.path.join(project, facts["directory"], "task.json"),
                               encoding="utf-8"))
    inherited = (successor.get("attribution") or {}).get("inherited") or []
    if not inherited or inherited[0].get("source_task") != task_id:
        problems.append(f"目标断言：S 未登记继承：{inherited}")
    elif not inherited[0].get("paths"):
        problems.append("继承路径为空")
    if successor.get("status") != "not_started" or successor.get("plan", {}).get("approval"):
        problems.append(f"S 不应已批准/已开工：{successor.get('status')}")
    if successor.get("run_id"):
        problems.append("普通任务替换时 S 不应加入实例")
    archived = [n for n in os.listdir(os.path.join(project, ".wf/tasks/archive/2026-11"))
                if n.startswith(task_id)]
    if not archived:
        problems.append("T 未移入归档")
    else:
        record = json.load(open(os.path.join(project, ".wf/tasks/archive/2026-11", archived[0],
                                            "task.json"), encoding="utf-8"))
        if record.get("terminal") != "abnormal":
            problems.append(f"T 终态不是 abnormal：{record.get('terminal')}")
        if record.get("successor_id") != successor_id:
            problems.append(f"T 未登记 successor_id：{record.get('successor_id')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
