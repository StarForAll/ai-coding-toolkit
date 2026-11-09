#!/usr/bin/env python3
"""B6：任务目录只有规范文件；非规范文件被只读盘点出来。

obligation（dogfood 2026-11-07：单任务 52 个文件，~40 个是自建"证据/协议"文件）：
入口该生成的结构不该由人/模型手写成文件；同时要能被**看见**——
`status` 在绑定时报告任务目录的规范外文件，而不是等归档后翻目录。

注入形态：盘点恒返回空。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-b6"
FROM = "def summary(root, task_id):\n"
TO = "def summary(root, task_id):\n    return {\"count\": 0, \"unexpected\": []}  # 注入\n"


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/taskfiles.py"), FROM, TO)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    problems = []

    rc, payload = H.cli(project, ["status", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    facts = ((payload or {}).get("facts") or {}).get("task") or {}
    files = facts.get("files") or {}
    if files.get("count") != 0 or files.get("unexpected"):
        problems.append(f"新建任务目录不该有规范外文件：{files}")

    # 自建一个"证据文件" → status 必须把它点名
    open(os.path.join(task_dir, "finish-commit-manifest.json"), "w", encoding="utf-8").write("{}\n")
    rc, payload = H.cli(project, ["status", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    files = (((payload or {}).get("facts") or {}).get("task") or {}).get("files") or {}
    if "finish-commit-manifest.json" not in (files.get("unexpected") or []):
        problems.append(f"自建证据文件未被点名：{files}")

    # 规范文件与 review 目录不该被误报
    rc, payload = H.cli(project, ["status", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    names = (((payload or {}).get("facts") or {}).get("task") or {}).get("files") or {}
    for canonical in ("prd.md", "task.json"):
        if canonical in (names.get("unexpected") or []):
            problems.append(f"规范文件被误报：{canonical}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
