#!/usr/bin/env python3
"""F5-5（真实落点）：`.wf-lock` 是指向项目外的符号链接时不得被认领。

与"标记前缀"分开成独立用例，各自单点注入、各自可证伪（第九轮复审 N9-3）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, _lib, payload = H.stage()
    sys.path.insert(0, payload)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(payload, "install.py"),
                "if not (real == root_real or real.startswith(root_real + os.sep)):",
                "if False:  # 注入：不核真实落点")
    import install as wf_install

    project = os.path.join(root, "proj")
    outside = os.path.join(root, "outside")
    os.makedirs(project, exist_ok=True)
    os.makedirs(outside, exist_ok=True)
    target = os.path.join(outside, "elsewhere")
    open(target, "w").write("wf-lock-v1\nholder: x\n")
    lock_path = os.path.join(project, ".wf-lock")
    os.symlink(target, lock_path)

    problems = []
    try:
        with wf_install.Lock(lock_path, root=project):
            problems.append("指向项目外的符号链接被认领")
    except (wf_install.LockRejected, wf_install.LockBusy):
        pass
    # 对照：项目内的普通锁必须仍可用（避免"一律拒绝"也算通过）
    inner = os.path.join(project, "inner")
    os.makedirs(inner, exist_ok=True)
    inner_lock = os.path.join(inner, ".wf-lock")
    try:
        with wf_install.Lock(inner_lock, root=project):
            pass
    except Exception as exc:  # noqa: BLE001
        raise H.Precondition(f"项目内锁正对照不可用：{getattr(exc, 'code', exc)}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
