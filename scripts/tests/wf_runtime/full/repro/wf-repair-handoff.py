#!/usr/bin/env python3
"""外部 N-1：`wf.py repair|uninstall` 的转交必须把已解析的项目根交给目标脚本。

缺陷形态：execv 只传脚本路径，目标脚本拿不到 root。`--project` 可选之后目标脚本退到
"当前目录"，因此从**项目外 cwd** 调用时会落到那个目录（缺 `.wf/`）而不是项目根——
设计稿承诺的「坏配置仍可达」恢复链路在异 cwd 下不可用。
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/bin/wf.py"),
                'env["WF_PROJECT_ROOT"] = root\n        os.execve(sys.executable, [sys.executable, script] + rest[1:], env)',
                'os.execv(sys.executable, [sys.executable, script] + rest[1:])  # 注入：不传 root')
    import json

    def run_repair(cwd):
        proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py"), "repair", "--json"],
                              cwd=cwd, capture_output=True, text=True)
        payload = None
        for line in reversed((proc.stdout or "").splitlines()):
            line = line.strip()
            if line.startswith("{"):
                try:
                    payload = json.loads(line)
                except ValueError:
                    payload = None
                break
        return proc, payload

    problems = []
    for label, cwd in (("项目根", project), ("外部 cwd", root)):
        proc, payload = run_repair(cwd)
        code = (payload or {}).get("code")
        if code == "WF_OK":
            root_seen = (((payload or {}).get("facts") or {}).get("preview") or {}).get("target_root")
            if root_seen != project:
                # 预览到了别的根（例如父目录）同样算缺陷：只断 WF_OK 不足以证明转交正确
                problems.append(f"{label}调用预览到了错误目标：{root_seen}")
            continue
        if code == "WF_CAPABILITY_UNAVAILABLE" and label == "外部 cwd":
            # 缺陷复现：转交没把已解析 root 交过去，目标脚本按缺省（当前目录）落到项目外
            problems.append(f"{label}调用落到当前目录而不是已解析的项目根：{payload}")
            continue
        if code == "WF_CAPABILITY_UNAVAILABLE":
            raise H.Precondition(f"{label}调用返回能力不可用：{payload}")
        if code == "WF_PATH_INVALID" and not ((payload or {}).get("facts") or {}).get("project"):
            # 缺陷复现：转交没把 root 交过去
            problems.append(f"{label}调用退化成分不清项目根")
            continue
        # 内部错误、未知码、其它业务失败都不算目标失败
        raise H.Precondition(f"{label}调用出现第三种结果：rc={proc.returncode} code={code}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
