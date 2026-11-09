#!/usr/bin/env python3
"""外部 P1 核对：`stop` 的写权核验与释放必须在同一把锁内。

判据：另一进程持 `.wf-lock` 时调 `stop` 必须失败（取锁拒绝），
且 writer/task 记录都不被改写——若"锁外核验 + 锁内写回"存在，会看到写入成功。
"""
import fcntl
import json
import os
import subprocess
import sys

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


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 注入：把 stop_work 的锁去掉（模拟"锁外核验 + 锁内写回"）
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                'with lock.acquire(ctx.root, holder_hint="stop"):',
                'with __import__("contextlib").nullcontext():  # 注入：stop 不取锁')
    sid = "sess-S1"
    task_id, task_dir = F.build_task(project, root, "stop 锁", sid=sid)
    keep = os.path.join(root, "keep.json")
    json.dump([F.decision(["pkg/a.py"], "keep")], open(keep, "w"), ensure_ascii=False)

    writer_path = os.path.join(project, ".wf/writer.json")
    before_writer = open(writer_path, encoding="utf-8").read()
    before_task = open(os.path.join(task_dir, "task.json"), encoding="utf-8").read()

    holder = subprocess.Popen([H.WF_PYTHON, "-c", HOLDER, os.path.join(project, ".wf-lock"), "6"],
                              stdout=subprocess.PIPE, text=True)
    try:
        if holder.stdout.readline().strip() != "locked":
            raise H.Precondition("锁持有者未就绪")
        rc, payload = H.cli(project, ["stop", "--decision", keep, "--json"], sid=sid,
                            inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK", "WF_WRITER_BUSY", "stop-under-lock")
    finally:
        holder.kill()
        holder.wait()

    problems = []
    if rc == 0:
        problems.append("锁被他人持有时 stop 仍然成功")
    if (payload or {}).get("code") not in ("WF_WRITER_BUSY",):
        problems.append(f"原因码不是 WF_WRITER_BUSY：{(payload or {}).get('code')}")
    if open(writer_path, encoding="utf-8").read() != before_writer:
        problems.append("拒绝路径改写了 writer")
    if open(os.path.join(task_dir, "task.json"), encoding="utf-8").read() != before_task:
        problems.append("拒绝路径改写了 task 记录")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
