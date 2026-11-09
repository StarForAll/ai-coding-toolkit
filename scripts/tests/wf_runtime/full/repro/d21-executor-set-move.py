#!/usr/bin/env python3
"""D21／设计稿 §1.1：项目键用相对路径时，目录整体移动不改变路径身份、确认不失效。

场景：项目内 `.venv/bin/python`（相对键）确认后，整个项目目录移动到新位置，
`executor_ready` 仍成立（路径身份按「相对项目根的位置」登记，随项目走）。
注入形态：相对键也按绝对真实路径登记身份——项目一移动身份即变、确认失效，
被迫对同一份已确认的解释器重复人确认。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

RELATIVE = ".venv/bin/python"


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.make_venv_python(project, RELATIVE)
        E.set_executor(project, RELATIVE)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            # 注入：相对键按绝对真实路径登记（移动即失效的缺陷形态）
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    "    absolute = os.path.join(os.path.abspath(root), candidate)",
                    "    return os.path.realpath(os.path.join(os.path.abspath(root), candidate))  # 注入：相对键也按绝对真实路径登记")
        module = E.launcher(project)
        E.confirm(module, project)
        if not E.ready(module, project):
            raise H.Precondition("移动前 ready 不成立（夹具未生效）")

        moved = os.path.join(root, "moved")
        os.rename(project, moved)
        module_moved = E.launcher(moved)
        if not E.ready(module_moved, moved):
            raise H.TargetFailure("目录移动后确认失效（相对路径身份被当成绝对路径）")
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
