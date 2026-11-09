#!/usr/bin/env python3
"""630 共存与重装：活动写者期间重装必须被拒；空闲后重装幂等且保留项目数据。

obligation（设计稿 §7.2「升级前置」、§7.3「保留数据重装」）：
- 写权被会话持有时，重装/追加平台必须被拒（不得在有人写的时候改资产）；
- 写权空闲后重装是幂等的：无变化时不取写权、不产生回执，任务数据原样保留。

注入形态：写者持有时也允许重装。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _release as R
import _review_flow as F
import _snapshot as S

SID = "sess-R630"
FROM = '    if state != "idle":\n        return f"writer state is {state!r}; 追加平台需在空闲时进行"\n'
TO = '    if False:  # 注入：写者持有时也允许重装\n        return f"writer state is {state!r}; 追加平台需在空闲时进行"\n'


def check():
    root, _lib, _payload = H.stage()
    source = R.source_repo(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        R.patch_asset(source, "install.py", FROM, TO)
    project = os.path.join(root, "proj")
    os.makedirs(project, exist_ok=True)
    first = R.installer(source, project)
    if first.returncode != 0:
        raise H.Precondition(f"首次安装失败：{(first.stdout or first.stderr)[-200:]}")
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "r@example.com"],
                ["git", "config", "user.name", "r"], ["git", "add", "-A"],
                ["git", "commit", "-qm", "init", "--allow-empty"]):
        import subprocess
        subprocess.run(cmd, cwd=project, check=True, capture_output=True)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    task_id, task_dir = S.started_task(project, root, sid=SID)     # 写权被本会话持有
    problems = []

    held = R.installer(source, project)
    if held.returncode == 0:
        problems.append("写权持有时重装未被拒")
    before_stop = open(os.path.join(task_dir, "task.json"), "rb").read()

    stop = os.path.join(root, "stop-630.json")
    json.dump([F.decision(["pkg/a.py"], "keep")], open(stop, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["stop", "--decision", stop, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"收工失败：{payload}")
    after_stop = open(os.path.join(task_dir, "task.json"), "rb").read()
    if after_stop == before_stop:
        raise H.Precondition("收工没有改动任务记录，夹具判据不成立")
    if problems:
        raise H.TargetFailure("；".join(problems))

    again = R.installer(source, project)
    if again.returncode != 0:
        problems.append(f"空闲后重装失败：{(again.stdout or again.stderr)[-160:]}")
    else:
        if "无任何变化" not in (again.stdout or ""):
            problems.append("空闲重装不是幂等（未声明「无任何变化」）")
        if open(os.path.join(task_dir, "task.json"), "rb").read() != after_stop:
            problems.append("重装改动了任务记录（应保留项目数据）")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
