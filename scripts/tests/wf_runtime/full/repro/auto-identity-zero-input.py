#!/usr/bin/env python3
"""R4-1：自动身份模式零输入 —— `enable` 不带任何信封即可建立执行会话。

obligation（identity-redesign §2.2a/§3.1/§4.1；R0 结论 A1）：
同一执行边界内，身份由锚点派生（L1 单主 + L2 追加），调用方**不提供** session 对象；
重复调用必须复用同一会话，且只保留一份附件。

注入形态：不签发新身份而每次重建（模拟“找不到既有路由就新建”）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

FROM = "        if key is None:\n            _establish_auto_session(ctx)"
TO = "        _establish_auto_session(ctx)  # 注入：总是重建"


def run(project, args, inputs=None):
    """不带信封、只带业务输入的调用（自动模式的最小请求）。"""
    import subprocess
    payload = json.dumps({"inputs": inputs or {}}, ensure_ascii=False) if inputs is not None else ""
    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py")] + list(args),
                          input=payload, capture_output=True, text=True,
                          cwd=project)   # 真实使用里 agent 就在项目内跑
    text = (proc.stdout or "").strip()
    return proc.returncode, (json.loads(text) if text.startswith("{") else None)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)

    problems = []
    first = run(project, ["enable", "--json"])
    if first[0] != 0 or (first[1] or {}).get("code") != "WF_OK":
        raise H.Precondition(f"自动模式 enable 失败：{first}")
    facts = first[1]["facts"]
    key1 = facts.get("session_key") or ""
    if facts.get("identity_mode") != "auto":
        problems.append(f"identity_mode 不是 auto：{facts.get('identity_mode')}")
    if not key1:
        problems.append("没有返回 session_key")

    attachments = os.path.join(project, ".wf/.runtime/attachments")
    routes = os.path.join(project, ".wf/.runtime/anchors.json")
    if not os.path.isdir(attachments) or len(os.listdir(attachments)) != 1:
        problems.append(f"附件数不是 1：{os.listdir(attachments) if os.path.isdir(attachments) else 'missing'}")
    if not os.path.isfile(routes):
        problems.append("没有写 anchors.json")

    second = run(project, ["enable", "--json"])
    key2 = (((second[1] or {}).get("facts") or {}).get("session_key")) or ""
    if key2 != key1:
        problems.append(f"重复 enable 换了会话：{key1[:10]} → {key2[:10]}")
    if len(os.listdir(attachments)) != 1:
        problems.append(f"重复 enable 后附件数不是 1：{len(os.listdir(attachments))}")

    # 业务命令同样零身份输入（generation 仍必填）
    rc, payload = run(project, ["task-new", "--kind", "ordinary", "--title", "自动模式任务",
                                "--template", ".wf/templates/task", "--json"],
                      inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"自动模式下 task-new 失败：{(payload or {}).get('code')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
