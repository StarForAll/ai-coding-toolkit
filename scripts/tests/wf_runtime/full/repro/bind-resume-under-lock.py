#!/usr/bin/env python3
"""A2：bind 的"恢复"路径（绑定已写、`session.bind` 动作未结案）必须与写入口同在锁内。

缺陷形态：首次 bind 在锁内，恢复分支却在锁外重读并写 writer.json，
于是并发维护写入可与它交错（同款错误在 `_writer_release` 已修，这条漏了）。

判据：另一个进程持有 `.wf-lock` 时——
- 修复后：bind 取锁失败 → WF_WRITER_BUSY，且 writer 不被改写；
- 退化为锁外：bind 直接续做成功（WF_OK）→ 变红。
"""
import fcntl
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

HOLDER = """
import fcntl, sys, time
handle = open(sys.argv[1], "a+")
fcntl.flock(handle, fcntl.LOCK_EX)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
"""


def _pending_bind_state(project, task_id):
    """把 writer.action 伪造成"同一会话已发起、尚未结案"的 session.bind 意图。"""
    path = os.path.join(project, ".wf/writer.json")
    record = json.load(open(path, encoding="utf-8"))
    action = dict(record.get("action") or {})
    if not action.get("id"):
        return False
    # 复用一条同形状的动作记录，把 kind/state/targets 改成"session.bind 未结案"
    action["kind"] = "session.bind"
    action["state"] = "started"
    action["targets"] = [{"kind": "task", "id": task_id}]
    record["action"] = action
    json.dump(record, open(path, "w"), ensure_ascii=False, indent=2)
    return True


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"),
                'with _lock(ctx.root, hint="bind-resume"):',
                'with __import__("contextlib").nullcontext():  # 注入：恢复路径不取锁')
    sid = "sess-B1"
    task_id, task_dir = F.build_task(project, root, "bind 恢复", sid=sid)
    if not _pending_bind_state(project, task_id):
        raise H.Precondition("夹具前置失败：writer.action 不是 session.bind")

    before = open(os.path.join(project, ".wf/writer.json"), encoding="utf-8").read()
    holder = subprocess.Popen([H.WF_PYTHON, "-c", HOLDER,
                               os.path.join(project, ".wf-lock"), "6"],
                              stdout=subprocess.PIPE, text=True)
    try:
        line = holder.stdout.readline().strip()
        if line != "locked":
            raise H.Precondition(f"锁持有者未就绪：{line!r}")
        rc, payload = H.cli(project, ["bind", "--task", task_id, "--json"], sid=sid)
        H.require_business_code(payload, rc)
        H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK", "WF_WRITER_BUSY", "bind-resume-under-lock")
    finally:
        holder.kill()
        holder.wait()

    problems = []
    if rc == 0:
        problems.append("锁被他人持有时恢复路径仍然写成功（未取锁）")
    if (payload or {}).get("code") != "WF_WRITER_BUSY":
        problems.append(f"原因码不是 WF_WRITER_BUSY：{(payload or {}).get('code')}")
    after = open(os.path.join(project, ".wf/writer.json"), encoding="utf-8").read()
    if after != before:
        problems.append("拒绝路径仍改写了 writer 记录")

    # 锁释放后，同一恢复意图必须能正常结案（证明这条路径本身可用）
    time.sleep(0.4)
    rc_ok, payload_ok = H.cli(project, ["bind", "--task", task_id, "--json"], sid=sid)
    H.require_business_code(payload_ok, rc_ok)
    H.require_success(payload_ok, rc_ok, "锁释放后的恢复正对照")
    if rc_ok != 0:
        problems.append(f"锁空闲时恢复失败：{(payload_ok or {}).get('code')}")
    else:
        facts = (payload_ok or {}).get("facts") or {}
        if not facts.get("resumed"):
            problems.append("未走恢复分支（resumed 缺失）")
        state = json.load(open(os.path.join(project, ".wf/writer.json"), encoding="utf-8"))
        if (state.get("action") or {}).get("state") != "done":
            problems.append(f"动作未结案：{(state.get('action') or {}).get('state')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
