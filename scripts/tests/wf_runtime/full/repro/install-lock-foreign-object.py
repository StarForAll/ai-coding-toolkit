#!/usr/bin/env python3
"""F5-5：锁对象判据必须与运行期同源——空文件 / 未知标记 / 指向项目外的符号链接一律拒绝。

缺陷形态：只判断"路径存在"就当自己的锁复用，于是别人的文件、空文件、
甚至指向项目外的符号链接都会被认领，互斥失效。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, _lib, payload = H.stage()
    sys.path.insert(0, payload)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 只保留一个注入点：标记前缀。真实落点的独立用例见 install-lock-realpath.py
        H.patch(os.path.join(payload, "install.py"),
                "elif not content.startswith(LOCK_MARK):",
                "elif False:  # 注入：不核标记前缀")
    import install as wf_install

    project = os.path.join(root, "proj")
    os.makedirs(project, exist_ok=True)
    lock_path = os.path.join(project, ".wf-lock")
    outside = os.path.join(root, "outside")

    problems = []

    def claim():
        with wf_install.Lock(lock_path, root=project):
            return True

    open(lock_path, "w").close()                      # 空文件
    try:
        claim()
        problems.append("空文件被当成可用锁")
    except (wf_install.LockRejected, wf_install.LockBusy):
        pass

    open(lock_path, "w").write("someone-else\n")      # 未知标记
    try:
        claim()
        problems.append("未知标记被认领")
    except (wf_install.LockRejected, wf_install.LockBusy):
        pass

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
