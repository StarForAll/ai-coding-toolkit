#!/usr/bin/env python3
"""B7：`--envelope-last` 免重拼信封 + `status --short` 免全量 task.json。

obligation（dogfood 2026-11-07：51 次碰 `/tmp/wf-env.json`、13 次整份 `cat task.json`）：
会话内应能复用上一次生效的信封；状态的"下一步"视图不该要求模型读整份记录。

注入形态：不写信封缓存。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _snapshot as S

SID = "sess-b7"
FROM = "    if not isinstance(envelope, dict):\n        return\n"
TO = "    if True:  # 注入：不缓存信封\n        return\n"


def envelope(project):
    return {"session": {"provider": "host",
                        "identity": {"host_id": "dsh", "session_id": SID},
                        "instance_id": H.binding_instance(project, SID),
                        "activation": {"enabled": True, "start_source": "human:repro",
                                       "enabled_at": "2026-11-07T00:00:00.000000Z"}},
            "inputs": {}}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/cli.py"), FROM, TO)
    task_id, _task_dir = S.started_task(project, root, sid=SID)
    problems = []

    # ① 缓存存在：启动任务的命令成功后应当写下来
    cache = os.path.join(project, ".wf/.runtime/envelopes", f"{SID}.json")
    if not os.path.isfile(cache):
        problems.append("成功命令未写信封缓存")
    else:
        saved = json.load(open(cache, encoding="utf-8"))
        if (saved.get("session") or {}).get("identity", {}).get("session_id") != SID:
            problems.append(f"缓存里的会话身份不对：{saved.get('session')}")

    # ② --envelope-last 能在不给信封的情况下跑通
    rc, payload = H.cli(project, ["status", "--short", "--envelope-last", "--session", SID, "--json"], sid=SID,
                        use_envelope=False)
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"--envelope-last 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    task_facts = ((payload or {}).get("facts") or {}).get("task") or {}
    if not task_facts.get("id"):
        problems.append(f"status --short 未回任务摘要：{task_facts}")
    for heavy in ("plan", "reviews", "execution", "check_history"):
        if heavy in json.dumps(task_facts, ensure_ascii=False):
            problems.append(f"status --short 仍带重字段：{heavy}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
