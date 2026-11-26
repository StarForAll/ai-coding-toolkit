#!/usr/bin/env python3
"""六轮-3：实例定义快照缺失时，finish/terminate/preview 必须在**业务写入之前**报 `WF_HISTORY_UNRESOLVED`。

obligation（设计稿 §5.9、§7.4）：快照是实例的唯一执行依据；缺失属可识别的历史不明，
不是内部错误。更关键的是读取**时点**：`run terminate` 曾在逐任务处置之后才读快照，
缺失即留下半写状态——本次要求零写入退出。

红模：去掉 `fixed_snapshot` 的存在性判定（退回修复前直接 `open(...)`）→ 抛裸异常，
退出码不是 `WF_HISTORY_UNRESOLVED`，目标断言变红。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-SNAP"
MARKER = "<!-- wf-definition:v1 -->"

FROM = '''    if not snapshot_rel or not os.path.isfile(snapshot_abs):
'''
TO = '''    if not snapshot_rel:
'''


def _definition():
    task_step = {
        "id": "build", "type": "task", "title": "实现", "task_kind": "ordinary",
        "inputs": [], "outputs": [], "required": True, "skip": None,
        "human_points": [], "goal": "实现", "acceptance": ["验收通过"],
        "actions": [{"id": "work", "text": "实现", "inputs": [], "outputs": [],
                     "required": True, "skip": None, "human_points": []}],
        "verifications": [{"id": "v1", "source": "current_plan",
                           "established_by": {"kind": "current_task"},
                           "stored_in": {"kind": "task_plan", "verification_id": "v1"},
                           "consume_at": "check"}]}
    doc = {"format_version": 1, "workflow_id": "snap", "content_version": 1,
           "purpose": "快照缺失场景", "applicability": "已有基线",
           "inputs": {}, "steps": [task_step], "completion": ["正常归档"]}
    body = json.dumps(doc, ensure_ascii=False, indent=2)
    return f"{MARKER}\n```json\n{body}\n```\n\n# 说明\n"


def _raw(project, args, sid):
    """直接跑 CLI 并保留"没返回 JSON"这一事实：快照缺失导致崩溃本身就是缺陷签名。"""
    import subprocess

    envelope = {"session": {"provider": "host",
                            "identity": {"host_id": "dsh", "session_id": sid},
                            "activation": {"enabled": True, "start_source": "human:repro",
                                           "enabled_at": "2026-11-05T00:00:00.000000Z"}},
                "inputs": {"generation": H.generation(project)}}
    proc = subprocess.run([H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py")] + list(args),
                          input=json.dumps(envelope), capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    try:
        payload = json.loads(out) if out.startswith("{") else None
    except ValueError:
        payload = None
    return proc.returncode, payload, (proc.stderr or "").strip()


def _expect_history(project, sid, args, label, problems):
    rc, payload, stderr = _raw(project, args, sid)
    if payload is None:
        problems.append(f"{label} 崩溃而未返回原因码：rc={rc} stderr={stderr[-160:]!r}")
        return
    if _code(payload) != "WF_HISTORY_UNRESOLVED":
        problems.append(f"{label} 未报历史不明：code={_code(payload)}")


def _code(payload):
    return (payload or {}).get("code")


def check():
    import hashlib
    import subprocess

    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/runs.py"), FROM, TO)

    text = _definition()
    os.makedirs(os.path.join(project, ".wf/user-workflows"), exist_ok=True)
    with open(os.path.join(project, ".wf/user-workflows/snap.md"), "w", encoding="utf-8") as handle:
        handle.write(text)
    digest = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    prepare_auth = H.prepare_authorization(project, root, "snap", sid=SID)
    rc, payload = H.cli(project, ["definition", "prepare", "--id", "snap",
                                  "--authorization", prepare_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"prepare 失败：{_code(payload)}")
    creation = {"definition_id": "snap", "definition_digest": digest,
                "inputs": {}, "steps": {"build": "applicable"}}
    creation_path = os.path.join(root, "creation.json")
    json.dump(creation, open(creation_path, "w"), ensure_ascii=False)
    create_auth = H.creation_authorization(project, root, creation_path, sid=SID)
    rc, payload = H.cli(project, ["run", "create", "--creation", creation_path,
                                  "--authorization", create_auth, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"run create 失败：{_code(payload)}")
    run_id = (payload.get("facts") or {})["run"]["id"]
    subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "definition snap"], cwd=project,
                   check=True, capture_output=True)
    rc, payload = H.cli(project, ["run", "advance", "--run", run_id, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    task_id = ((payload or {}).get("facts") or {}).get("task")
    if rc != 0 or not task_id:
        raise H.Precondition(f"advance 未建任务：{_code(payload)}")
    task_dir = ((payload or {}).get("facts") or {}).get("directory")
    task_record = os.path.join(project, task_dir, "task.json")

    snapshot = os.path.join(project, ".wf/workflow-runs", run_id, "definition.md")
    if not os.path.isfile(snapshot):
        raise H.Precondition("快照不在预期路径")
    os.remove(snapshot)

    problems = []
    before = open(task_record, "rb").read()

    _expect_history(project, SID, ["run", "finish", "--run", run_id, "--json"], "run finish", problems)
    _expect_history(project, SID, ["run", "terminate", "--run", run_id, "--preview", "--json"],
                    "terminate --preview", problems)

    plan = os.path.join(root, "plan.json")
    json.dump([{"object": task_id,
                "decision_ref": {"source": "human", "at": "2026-11-26T02:00:00.000000Z",
                                 "subject": [task_id], "object_digest": "sha256:" + "0" * 64,
                                 "choice": "abandon", "reason": "终止实例"},
                "reason": "终止实例", "disposition": {"changes": []}}],
              open(plan, "w"), ensure_ascii=False)
    _expect_history(project, SID, ["run", "terminate", "--run", run_id, "--plan", plan, "--json"],
                    "run terminate", problems)
    after = open(task_record, "rb").read()
    if after != before:
        problems.append("快照缺失时 terminate 仍改写了任务记录（半写状态）")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))