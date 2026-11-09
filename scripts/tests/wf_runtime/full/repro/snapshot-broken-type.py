#!/usr/bin/env python3
"""629.s4：`touch_paths` 类型损坏时，各入口必须 fail-closed。

s4 = 快照存在但 `touch_paths` 不是列表（这里是字符串）。按机制稿 §2.3 的严格三态，
类型不符一律 `WF_RECORD_INVALID`，不得把字符串当成可迭代的路径集合蒙混过关。
三个入口（收工 / Check / 写入口）共用同一批准面判定，逐个断言。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-S4T"
BROKEN_FROM = ('    if not isinstance(paths, list):\n'
               '        raise TaskError("WF_RECORD_INVALID",\n'
               '                        {"reason": "entry_snapshot.touch_paths must be a list",\n'
               '                         "task": task.get("id"), "touch_paths": paths})\n')
BROKEN_TO = ('    if not isinstance(paths, list):\n'
             '        paths = [paths]  # 注入：类型不符就当单条路径收下\n')


def damage_type(task_dir):
    path = os.path.join(task_dir, "task.json")
    record = json.load(open(path, encoding="utf-8"))
    snapshot = record.get("entry_snapshot")
    if not isinstance(snapshot, dict) or "touch_paths" not in snapshot:
        raise H.Precondition("夹具不是 s4：快照缺 touch_paths")
    snapshot["touch_paths"] = "pkg/**"      # 字符串：类型损坏
    record["entry_snapshot"] = snapshot
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), BROKEN_FROM, BROKEN_TO)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    damage_type(task_dir)
    problems = []

    stop_path = os.path.join(root, "stop-s4.json")
    json.dump([F.decision(["pkg/b.py"], "keep")], open(stop_path, "w", encoding="utf-8"), ensure_ascii=False)
    for label, argv in (
            ("收工", ["stop", "--decision", stop_path, "--json"]),
            ("Check", ["task-check", "--task", task_id, "--json"])):
        rc, payload = H.cli(project, argv, sid=SID, inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        try:
            H.code_problem(payload, {"WF_RECORD_INVALID"})
        except H.TargetFailure as exc:
            problems.append(f"{label}：{exc}")
            break
    if not problems:
        changes = os.path.join(root, "changes-s4.json")
        json.dump([{"action": "add", "new_paths": ["pkg/r.md"], "content": "x\n"}],
                  open(changes, "w", encoding="utf-8"), ensure_ascii=False)
        rc, payload = H.cli(project, ["spec-update", "--task", task_id, "--changes", changes, "--json"],
                            sid=SID, inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        try:
            H.code_problem(payload, {"WF_RECORD_INVALID"})
        except H.TargetFailure as exc:
            problems.append(f"写入口：{exc}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
