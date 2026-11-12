#!/usr/bin/env python3
"""P1-5（替换预览）：`task-replace --preview` 只读给出将被固定的候选（机制稿 §6.3 首句）。

断言链：
1. 预览列出继承路径、`touch_paths` 未覆盖项、下游重连对象、未归档返工与实例映射；
2. 预览**零写入**：T 未改、没建 S、实例 `task_map` 未动；
3. `touch_paths` 覆盖时不报未覆盖项。

注入形态 = 预览里漏掉继承路径（模拟"预览只给空壳清单"）→ 目标断言 1 变红。
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-RPV"

FROM = '''               "inherited_paths": inherited, "uncovered_by_touch_paths": uncovered,'''
TO = '''               "inherited_paths": [], "uncovered_by_touch_paths": [],  # 注入：空壳预览'''


def _decision(path, choice, touch_paths):
    json.dump([{"source": "human", "at": "2026-11-12T00:00:00.000000Z",
                "subject": ["替换"], "object_digest": "sha256:" + "a" * 64,
                "choice": choice, "reason": "换人重做", "touch_paths": touch_paths}],
              open(path, "w"), ensure_ascii=False)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    task_id, _task_dir = F.build_task(project, root, title="被替换的任务", sid=SID)
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", f"wf: deliver\n\nwf-task: {task_id}"],
                   cwd=project, check=True, capture_output=True)

    def run(args):
        return H.cli(project, args + ["--json"], sid=SID,
                     inputs={"generation": H.generation(project)})

    problems = []
    narrow = os.path.join(root, "narrow.json")
    _decision(narrow, "替换", ["other/**"])
    rc, payload = run(["task-replace", "--task", task_id, "--decision", narrow, "--preview"])
    facts = (payload or {}).get("facts") or {}
    if rc != 0 or facts.get("preview") is not True:
        raise H.TargetFailure(f"预览失败：rc={rc} code={(payload or {}).get('code')}")
    if "pkg/a.py" not in (facts.get("inherited_paths") or []):
        problems.append(f"预览未列出继承路径（目标断言）：{facts.get('inherited_paths')}")
    if "pkg/a.py" not in (facts.get("uncovered_by_touch_paths") or []):
        problems.append(f"预览未标出未覆盖项：{facts.get('uncovered_by_touch_paths')}")
    # 零写入：T 仍在活动区、未暂停/挂起、无 successor_id
    active = [n for n in os.listdir(os.path.join(project, ".wf/tasks")) if n.startswith(task_id)]
    if not active:
        problems.append("预览把 T 移走了（应零写入）")
    else:
        record = json.load(open(os.path.join(project, ".wf/tasks", active[0], "task.json"),
                                encoding="utf-8"))
        if record.get("successor_id") or record.get("suspended"):
            problems.append("预览改了 T 的字段（应零写入）")
    if len([n for n in os.listdir(os.path.join(project, ".wf/tasks")) if n.startswith("2026-")]) != 1:
        problems.append("预览新建了任务目录（应零写入）")

    wide = os.path.join(root, "wide.json")
    _decision(wide, "替换", ["pkg/**"])
    rc, payload = run(["task-replace", "--task", task_id, "--decision", wide, "--preview"])
    facts = (payload or {}).get("facts") or {}
    if facts.get("uncovered_by_touch_paths"):
        problems.append(f"覆盖后仍报未覆盖：{facts.get('uncovered_by_touch_paths')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
