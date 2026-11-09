#!/usr/bin/env python3
"""673 执行器首次写入：project 作用域的确认必须有 Git 侧批准证据。

obligation（设计稿 §8.2「执行器首次写入」行 / §1.1）：项目键的首次写入不是
「谁先跑谁说了算」——`project_key_approved` 必须在基线或**已批准** PRD 里查到
同一个键名与配置值，否则拒绝，且**拒绝路径不写确认记录**。

注入形态：跳过批准链检查（`approved = True`）。
"""
import contextlib
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E


def set_config_only(project, value):
    path = os.path.join(project, ".wf/project-config.json")
    config = json.load(open(path, encoding="utf-8"))
    config["python_executable"] = value
    json.dump(config, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def approve_key(project, value):
    with open(os.path.join(project, ".wf/baseline.md"), "a", encoding="utf-8") as handle:
        handle.write(f"\npython_executable = {value}\n")


def confirm_raw(module, project, scope="project"):
    old = sys.stdin
    sys.stdin = E._Terminal("yes\n")
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            rc = module.cmd_confirm_executor(project, ["--scope", scope])
    finally:
        sys.stdin = old
    return rc, buffer.getvalue()


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.make_venv_python(project)
        set_config_only(project, ".venv/bin/python")      # 键未进基线/已批准 PRD
        if os.environ.get("WF_REPRO_INJECT") == "1":
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    "        approved = project_key_approved(root, config_value)\n",
                    "        approved = True  # 注入：不核批准链\n")
        module = E.launcher(project)
        rc, out = confirm_raw(module, project)
        problems = []
        if rc == 0:
            problems.append("未批准的键被接受（首次写入没有批准链）")
        elif "WF_APPROVAL_MISSING" not in out:
            raise H.Precondition(f"拒绝原因不是 WF_APPROVAL_MISSING：{out.strip()[-200:]}")
        if module.load_confirmations():
            problems.append(f"拒绝路径写了确认记录：{len(module.load_confirmations())} 条")
        # 正例：把键与值写进被批准的基线后，同一确认必须成立
        approve_key(project, ".venv/bin/python")
        rc2, out2 = confirm_raw(module, project)
        if rc2 != 0:
            raise H.Precondition(f"批准链补上后确认仍失败：{out2.strip()[-200:]}")
        if not E.ready(module, project):
            problems.append("批准后确认未生效（ready=False）")
        if problems:
            raise H.TargetFailure("；".join(problems))
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
