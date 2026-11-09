#!/usr/bin/env python3
"""D21／设计稿 §1.1：确认覆盖的是解释器二进制而非 venv 环境——
重建 venv 只在解析结果或文件元数据随之变化时才算变更、才触发失配。

场景（同一次重建的两个方向，对应设计稿原句的两半）：
- 元数据不变（同大小、同 mtime）的重建 → 确认沿用（ready 成立）；
- mtime 变化的重建 → 失配，须重新人确认（ready 不成立）。
注入形态：去掉轻量指纹（大小/mtime）比对——mtime 变化后仍沿用旧确认。
（「元数据不变 → 沿用」是同一句的另一半，不另设注入点，见 §95 表登记。）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E

RELATIVE = ".venv/bin/python"
T_SAME = 1700000000
T_NEW = 1700001000


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        E.make_venv_python(project, RELATIVE, mtime=T_SAME)
        E.set_executor(project, RELATIVE)
        if os.environ.get("WF_REPRO_INJECT") == "1":
            # 注入：不核解释器轻量指纹（大小/mtime）
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    "    if entry.get(\"size\") != size or entry.get(\"mtime_ns\") != mtime_ns:",
                    "    if False:  # 注入：不核轻量指纹")
        module = E.launcher(project)
        E.confirm(module, project)
        if not E.ready(module, project):
            raise H.Precondition("重建前 ready 不成立（夹具未生效）")

        # 重建①：同大小、同 mtime → 确认沿用（合规）
        E.make_venv_python(project, RELATIVE, mtime=T_SAME)
        if not E.ready(module, project):
            raise H.TargetFailure("元数据不变的 venv 重建后确认失配（不应触发变更）")

        # 重建②：mtime 变化 → 失配，须重新人确认
        E.make_venv_python(project, RELATIVE, mtime=T_NEW)
        if E.ready(module, project):
            raise H.TargetFailure("venv 重建（mtime 变化）后仍沿用旧确认")
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
