#!/usr/bin/env python3
"""648 Python 执行器：项目键「已设但不可用」必须报错，不得静默降级到全局/系统。

obligation（设计稿 §8.1「按已设置选唯一候选」、机制稿 §8.2）：配置非法不回退——
项目键指向不存在的解释器时，解析结果仍是 **project 作用域 + 该键值**，
由入口报 `WF_EXECUTOR_UNCONFIRMED`；若在解析阶段就换成全局键，
「确认过哪个解释器」这件事会静默失去意义。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

MISSING = "/nonexistent/python3"
GLOBAL_PY = "/softwares/python/bin/python3"
FROM = ('    if scope in (None, "project") and project_value:\n'
        '        # 有效项目配置优先：不去读全局层，损坏的全局键也就不再阻断它\n'
        '        return "project", project_value, None\n')
TO = ('    if scope in (None, "project") and project_value:\n'
      '        if not os.path.isfile(project_value) and os.path.isfile("/softwares/python/bin/python3"):\n'
      '            return "global", "/softwares/python/bin/python3", None  # 注入：项目键不可用即降级\n'
      '        return "project", project_value, None\n')


def status_code(project):
    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py"), "status", "--json"],
                          cwd=project, capture_output=True, text=True, input="{}")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1] or "{}") or {}
    except Exception:  # noqa: BLE001
        return {}


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            H.patch(os.path.join(project, ".wf/bin/wf.py"), FROM, TO)
        module = E.launcher(project)
        global_path = module.global_config_path()
        os.makedirs(os.path.dirname(global_path), exist_ok=True)
        json.dump({"schema_version": 1, "python_executable": GLOBAL_PY},
                  open(global_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        path = os.path.join(project, ".wf/project-config.json")
        config = json.load(open(path, encoding="utf-8"))
        config["python_executable"] = MISSING
        json.dump(config, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        problems = []
        scope, value, error = module.resolve_candidate(project)
        if error:
            problems.append(f"解析直接报错：{error}")
        elif scope != "project" or value != MISSING:
            problems.append(f"解析降级到 {scope}：{value}")
        payload = status_code(project)
        if payload.get("code") != "WF_EXECUTOR_UNCONFIRMED":
            problems.append(f"CLI 未以 WF_EXECUTOR_UNCONFIRMED 拒绝：{payload.get('code')}")
        candidate = ((payload.get("facts") or {}).get("candidate"))
        if candidate and os.path.realpath(str(candidate)) != MISSING:
            problems.append(f"报错对象不是配置的项目键：{candidate}")
        if problems:
            raise H.TargetFailure("；".join(problems))
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
