#!/usr/bin/env python3
"""668 执行器配置可信：确认元组必须绑定解释器的实际指纹。

obligation（设计稿 §8.2「执行器配置可信」行）：确认记录是**当前解释器**的事实，
同路径替换（大小/修改时间变化）后不得沿用旧确认——否则「确认」退化为一次性的路径登记。

注入形态：`matches()` 不核 size/mtime（退回「只看路径」的年代）。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _executor_set as E


def status_code(project):
    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py"), "status", "--json"],
                          cwd=project, capture_output=True, text=True, input="{}")
    try:
        return (json.loads(proc.stdout.strip().splitlines()[-1] or "{}") or {}).get("code")
    except Exception:  # noqa: BLE001 — 解析失败按"未返回业务码"处理
        return None


def check():
    root, _lib, _payload = H.stage()
    with E.isolated_home(root):
        project = H.deploy(root)
        H.ensure_project_config(project)
        python = E.make_venv_python(project)
        E.set_executor(project, ".venv/bin/python")
        if os.environ.get("WF_REPRO_INJECT") == "1":
            H.patch(os.path.join(project, ".wf/bin/wf.py"),
                    '    if entry.get("size") != size or entry.get("mtime_ns") != mtime_ns:\n        return False\n',
                    '    if False and (entry.get("size") != size or entry.get("mtime_ns") != mtime_ns):\n        return False\n')
        module = E.launcher(project)
        E.confirm(module, project)
        if not E.ready(module, project):
            raise H.TargetFailure("确认后并不 ready（确认本身没有落到元组上）")
        if status_code(project) == "WF_EXECUTOR_UNCONFIRMED":
            raise H.TargetFailure("刚确认完就被判未确认")
        # 同路径替换解释器：只改指纹，不改路径/配置
        stat = os.stat(python)
        os.utime(python, (stat.st_atime, stat.st_mtime + 100))
        problems = []
        if E.ready(module, project):
            problems.append("解释器指纹变化后仍判 ready（沿用旧确认）")
        if status_code(project) != "WF_EXECUTOR_UNCONFIRMED":
            problems.append("CLI 未以 WF_EXECUTOR_UNCONFIRMED 拒绝")
        if problems:
            raise H.TargetFailure("；".join(problems))
        return None


if __name__ == "__main__":
    sys.exit(H.main(check))
