#!/usr/bin/env python3
"""616 日常收工：先只读预览逐路径归属，再按处置执行。

obligation（设计稿 §4.4）：收工应先给出「逐路径归属/状态/待验证项」的预览，
人看过再选处置；预览不得写任何记录（写完再问人等于事后补救）。

注入形态：`--preview` 落到执行分支（预览也落盘）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F
import _snapshot as S

SID = "sess-616"
FROM = '    if args.flag("--preview"):\n'
TO = '    if False:  # 注入：预览落到执行分支\n'


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    task_id, task_dir = S.started_task(project, root, sid=SID)
    open(os.path.join(project, "pkg/a.py"), "w").write("a-wip\n")
    decision = os.path.join(root, "stop-616.json")
    json.dump([F.decision(["pkg/a.py"], "keep")], open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    before = open(os.path.join(task_dir, "task.json"), "rb").read()
    writer_before = open(os.path.join(project, ".wf/writer.json"), "rb").read()
    problems = []

    rc, payload = H.cli(project, ["stop", "--decision", decision, "--preview", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"预览失败：{(payload or {}).get('code')}")
    else:
        facts = (payload or {}).get("facts") or {}
        buckets = facts.get("buckets") or {}
        if "pkg/a.py" not in (buckets.get("e") or []) + (buckets.get("c") or []):
            problems.append(f"预览未列出待处置路径：{buckets}")
        if facts.get("note") != "预览只读；本次未写入任何记录":
            problems.append("预览未声明只读")
    if open(os.path.join(task_dir, "task.json"), "rb").read() != before:
        problems.append("预览改写了任务记录")
    if open(os.path.join(project, ".wf/writer.json"), "rb").read() != writer_before:
        problems.append("预览改写了写权记录")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # 预览之后，正式收工仍可执行
    rc, payload = H.cli(project, ["stop", "--decision", decision, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        raise H.TargetFailure(f"预览后正式收工失败：{(payload or {}).get('code')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
