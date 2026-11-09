#!/usr/bin/env python3
"""668 残余缺口：确认元组必须比对解释器版本。

obligation（§2.3.11 ③）：`confirm-executor` 记录的 `python_version` 是确认事实的一部分；
解释器升级/被替换成另一版本而 size/mtime 未变（打包镜像、保留元数据）时，
旧确认不得继续生效——否则「确认过某个解释器」会退化成「确认过某个路径」。

注入形态：元组比对忽略 `python_version`。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

FROM = '        ) and entry.get("python_version") == version_text:\n'
TO = '        ):\n'


def status_code(project):
    import subprocess

    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py"), "status", "--json"],
                          cwd=project, capture_output=True, text=True, input="{}")
    try:
        return (json.loads(proc.stdout.strip().splitlines()[-1] or "{}") or {}).get("code")
    except Exception:  # noqa: BLE001
        return None


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.make_venv_python(project)
        E.set_executor(project, ".venv/bin/python")
        if os.environ.get("WF_REPRO_INJECT") == "1":
            H.patch(os.path.join(project, ".wf/bin/wf.py"), FROM, TO)
        module = E.launcher(project)
        E.confirm(module, project)
        if not E.ready(module, project):
            raise H.TargetFailure("确认后并不 ready")
        # 保留 size/mtime，只改登记版本 → 等价于「同为元数据、版本已不同」
        path = module.confirm_path()
        data = json.load(open(path, encoding="utf-8"))
        for entry in data.get("interpreters") or []:
            entry["python_version"] = "Python 3.9.0"
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        problems = []
        if E.ready(module, project):
            problems.append("版本不符仍判 ready")
        if status_code(project) != "WF_EXECUTOR_UNCONFIRMED":
            problems.append("CLI 未以 WF_EXECUTOR_UNCONFIRMED 拒绝")
        if problems:
            raise H.TargetFailure("；".join(problems))
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
