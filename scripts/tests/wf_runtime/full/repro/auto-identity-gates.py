#!/usr/bin/env python3
"""R4-2：自动模式下两道身份闸门仍然生效。

1. `activation_stale` ⇒ 业务命令 `WF_NOT_ENABLED(activation_stale)`（§3.4/§4）；
2. 未登记的第二调用者（同会话另有存活根）⇒ `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)`
   （C2 分级，人裁 OD-8；§2.3d / §3.4 步骤 3）。

注入形态：让 `_auto_resolve` 忽略 stale 与 C2（直接放行）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

FROM = ('            if attachment and attachment.get("activation_stale") '
        'and getattr(self, "command", "") != "enable":')
TO = ('            if False and attachment and attachment.get("activation_stale") '
      'and getattr(self, "command", "") != "enable":  # 注入：忽略降级')


def run(project, args, inputs=None):
    import subprocess
    payload = json.dumps({"inputs": inputs or {}}) if inputs is not None else ""
    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py")] + list(args),
                          input=payload, capture_output=True, text=True, cwd=project)
    text = (proc.stdout or "").strip()
    return proc.returncode, (json.loads(text) if text.startswith("{") else None)


def load(project, rel):
    with open(os.path.join(project, rel), encoding="utf-8") as handle:
        return json.load(handle)


def save(project, rel, payload):
    with open(os.path.join(project, rel), "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)

    rc, payload = run(project, ["enable", "--json"])
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.Precondition(f"enable 失败：{payload}")
    key = payload["facts"]["session_key"]
    problems = []

    # ---- 闸门 1：activation_stale ----
    rel = f".wf/.runtime/attachments/{key}.json"
    attachment = load(project, rel)
    attachment["activation_stale"] = True
    save(project, rel, attachment)
    rc, payload = run(project, ["task-new", "--kind", "ordinary", "--title", "被拦",
                                "--template", ".wf/templates/task", "--json"],
                      inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    reason = ((payload or {}).get("facts") or {}).get("reason")
    if code != "WF_NOT_ENABLED" or reason != "activation_stale":
        problems.append(f"stale 未拦住：{code}/{reason}")

    # ---- 闸门 2：C2 未登记第二调用者 ----
    attachment["activation_stale"] = False
    # 造一个"另一个已登记的调用者"：同会话 roots 里放一个存活根（init 之下不可能），
    # 用当前进程的一个真实存活 pid（本测试进程自身）代替，并把当前 root 从 roots 里摘掉，
    # 使 `!known ∧ others_alive` 成立。
    save(project, rel, attachment)
    rc, payload = run(project, ["enable", "--json"])       # 记录当前 root
    roots = load(project, rel)["roots"]
    if not roots:
        raise H.Precondition("附件里没有根")
    current = roots[0]
    # 造一个**在用例期间存活、且不在 CLI 祖先进程链上**的进程作为"另一个存活根"；
    # 若用本测试进程，某些解释器下它恰好是 CLI 的 L2 锚 ⇒ known=True，C2 不会被触发。
    import subprocess as sp
    sleeper = sp.Popen(["sleep", "120"])
    pid = sleeper.pid
    stat = open(f"/proc/{pid}/stat").read()
    start = stat[stat.rindex(")") + 2:].split()[19]
    save(project, rel, {"session_key": key, "provider": "wf", "identity": attachment.get("identity"),
                        "activation": attachment.get("activation"), "activation_stale": False,
                        # 当前 root 不在 roots 里；roots 里放一个存活根
                        "roots": [{"kind": "pid", "boot": current["boot"], "pid": pid,
                                   "start": start, "exe": "python3"}],
                        "attached_l1": attachment.get("attached_l1"),
                        "instance_expected": None, "declared_implementation_cli": None})
    rc, payload = run(project, ["task-new", "--kind", "ordinary", "--title", "被 C2 拦",
                                "--template", ".wf/templates/task", "--json"],
                      inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    reason = ((payload or {}).get("facts") or {}).get("reason")
    if code != "WF_IDENTITY_UNRESOLVED" or reason != "concurrent_unregistered_caller":
        problems.append(f"C2 未拦住：{code}/{reason}")

    sleeper.kill()
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
