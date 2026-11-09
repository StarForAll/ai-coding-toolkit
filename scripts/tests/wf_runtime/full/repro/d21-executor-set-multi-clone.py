#!/usr/bin/env python3
"""D21／设计稿 §1.1：确认记录按完整元组保存为集合——同一项目的不同 clone
用不同解释器时各自记录并存，写入不得覆盖其他元组的记录。

场景：项目 A 确认 `/usr/bin/python3`，其 clone B 改配置并确认
`/softwares/python/bin/python3`；两份 project 作用域确认携带同一
project_id 互不覆盖，两个 clone 的 `executor_ready` 都成立。
注入形态：写入时按 project_id 去重（后确认覆盖先确认）——
设计稿明文否定的「按『项目标识+键名』只留一条」。
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

PY_A = "/usr/bin/python3"
PY_B = "/softwares/python/bin/python3"


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            # 注入：写入按项目标识去重，后确认的 clone 覆盖先确认的（缺陷形态）
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    "        entries.append(entry)",
                    "        entries = [e for e in entries if e.get(\"project_id\") != entry[\"project_id\"]] + [entry]  # 注入：按项目标识只留一条")
        clone = os.path.join(root, "clone")
        shutil.copytree(project, clone)
        E.set_executor(project, PY_A)
        E.set_executor(clone, PY_B)
        module_a = E.launcher(project)
        module_b = E.launcher(clone)
        E.confirm(module_a, project)
        E.confirm(module_b, clone)
        project_id = json.load(open(os.path.join(project, ".wf/project-config.json"),
                                   encoding="utf-8"))["project_id"]
        entries = [item for item in module_a.load_confirmations()
                   if item.get("project_id") == project_id]
        ready_a = E.ready(module_a, project)
        ready_b = E.ready(module_b, clone)
        problems = []
        if len(entries) != 2:
            problems.append(f"同项目多 clone 的确认未并存（期望 2 条，实际 {len(entries)}）")
        if not ready_a:
            problems.append("clone B 确认后 A 不再 ready（记录被覆盖）")
        if not ready_b:
            problems.append("clone B 自身不 ready")
        if problems:
            raise H.TargetFailure("；".join(problems))
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
