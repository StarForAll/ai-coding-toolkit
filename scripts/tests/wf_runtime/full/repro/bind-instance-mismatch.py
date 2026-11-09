#!/usr/bin/env python3
"""F5-6／R50-04：实例标识不符必须拒绝，且拒绝路径不改写写权记录。

缺陷形态：绑定校验只看 session-id，实例标识（多 clone/多窗口）被忽略，
同会话标识的不同实例可以互相接管。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"),
                "def _require_instance_match(ctx, binding):",
                "def _require_instance_match(ctx, binding):\n    return  # 注入：不核实例标识")
    task_id, _task_dir = F.build_task(project, root)
    before = H.generation(project)
    rc, payload = H.cli(project, ["task-resume", "--task", task_id, "--json"],
                        sid="sess-R", inputs={"generation": before},
                        instance_id="f" * 32)
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_BINDING_MISMATCH", "bind-instance-mismatch")
    after = H.generation(project)

    problems = []
    if rc == 0:
        problems.append("实例标识不符仍放行")
    if (payload or {}).get("code") != "WF_BINDING_MISMATCH":
        problems.append(f"原因码不是 WF_BINDING_MISMATCH：{(payload or {}).get('code')}")
    if after != before:
        problems.append(f"拒绝路径改写了写权代次：{before} -> {after}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
