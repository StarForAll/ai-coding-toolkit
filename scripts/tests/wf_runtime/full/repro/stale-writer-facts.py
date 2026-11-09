#!/usr/bin/env python3
"""688 旧写者事实待核对：持有者死活未知时阻断，不得「PID 消失即当空闲」。

obligation（设计稿 §4.4、§8.2「互斥与锁生命周期」）：写权记录仍显示 `held`、但锁里的
持锁者进程已不存在时，运行期只能**阻断**并给交接/恢复出口；自动接管（把 PID 消失当空闲）
正是设计稿明列的禁止行为。判定「旧持有者是否还活着」是 repair/uninstall 的职责。

注入形态：把持锁者事实当空闲——`.wf-lock` 里的 pid 查不到就直接放行。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-W688"
FROM = ('        if holder.get("id") != key:\n'
        '            raise CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "held by another session"})\n')
TO = ('        if False:  # 注入：不再核他人持有（PID 消失即当空闲的等价形态）\n'
      '            raise CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "held by another session"})\n')


def stale_writer(project, task_id):
    path = os.path.join(project, ".wf/writer.json")
    record = json.load(open(path, encoding="utf-8"))
    record["state"] = "held"
    record["holder"] = {"kind": "session", "id": "sess-dead", "generation": record["generation"],
                        "scope": {"object": {"kind": "task", "id": task_id}}}
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    with open(os.path.join(project, ".wf-lock"), "w", encoding="utf-8") as handle:
        handle.write("wf-lock-v1\nholder pid=999999 start=0\n")   # pid 必定不存在


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    task_id, _task_dir = S.started_task(project, root, sid=SID)
    stale_writer(project, task_id)
    problems = []

    stop = os.path.join(root, "stop-688.json")
    json.dump([F.decision(["pkg/b.py"], "keep")], open(stop, "w", encoding="utf-8"), ensure_ascii=False)
    for label, argv in (("收工", ["stop", "--decision", stop, "--json"]),
                        ("写入口", ["spec-update", "--task", task_id, "--changes", stop, "--json"])):
        rc, payload = H.cli(project, argv, sid=SID, inputs={"generation": H.generation(project)})
        H.require_business_code(payload, rc)
        try:
            H.code_problem(payload, {"WF_WRITER_BUSY"})
        except H.TargetFailure as exc:
            problems.append(f"{label}：{exc}")
            break
        facts = (payload or {}).get("facts") or {}
        if facts.get("reason") != "held by another session":
            problems.append(f"{label}：阻断理由不是「他人持有」（{facts.get('reason')}）")
        hint = f"{payload.get('exit') or ''}{payload.get('next') or ''}"
        if not any(word in hint for word in ("交接", "恢复")):
            problems.append(f"{label}：出口未指向交接/恢复（{hint[:60]}）")
        if problems:
            break
    if problems:
        raise H.TargetFailure("；".join(problems))

    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
