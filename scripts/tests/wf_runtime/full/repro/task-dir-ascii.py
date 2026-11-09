#!/usr/bin/env python3
"""B8：任务目录名只保留 ASCII（标题仍存记录）。

obligation（dogfood 2026-11-07）：`2026-…-初始化-wf-基线-项目配置与-spec-骨架` 这类中文目录
在转录里已出现乱码，跨工具链也有风险。标题是记录字段，不该进路径。

注入形态：slug 允许非 ASCII（旧行为）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-b8"
TITLE = "初始化 wf 基线、项目配置与 spec 骨架"
FROM = '    return cleaned[:48].strip("-") or "task"' + chr(10)
TO = '    return re.sub(r"[^\\w\\-]+", "-", title, flags=re.UNICODE).strip("-")[:48] or "task"  # 注入' + chr(10)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    rc, payload = H.cli(project, ["task-new", "--kind", "initialize", "--title", TITLE,
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    facts = (payload or {}).get("facts") or {}
    directory = facts.get("directory") or ""
    name = os.path.basename(directory)
    task_dir = os.path.join(project, directory)
    problems = []
    try:
        name.encode("ascii")
    except UnicodeEncodeError:
        problems.append(f"目录名含非 ASCII：{name}")
    if not name.startswith(facts.get("task_id", "")):
        problems.append(f"目录名未以任务 id 起首：{name}")
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    if record.get("title") != TITLE:
        problems.append(f"标题未原样保存：{record.get('title')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
