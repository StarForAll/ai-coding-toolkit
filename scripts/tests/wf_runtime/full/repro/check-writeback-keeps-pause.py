#!/usr/bin/env python3
"""六轮-4：Check 锁外执行期间同会话写入的暂停，不得被定稿段用内存态覆盖。

obligation（设计稿 §4.2、§4.4）：`task-check` 的验证段在锁外跑（长操作不长期持锁），
回锁后必须**以盘上记录为准**：期间同一会话能成功 `task-pause`（写权没释放），
于是「本次检查结论仍成立」这一事实变了 → `WF_CHECK_STALE`；并且暂停必须留在记录里。

红模：去掉回锁后的身份比对（退回修复前：直接沿用准备段的内存态回写）→
Check 成功并把 `paused` 覆盖掉，目标断言变红。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

BLOCK = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv",
                                           "argv": ["/usr/bin/python3", "-c",
                                                    "import time;time.sleep(2)"]},
                            "cwd": ".", "input_refs": [], "required": True,
                            "consume_at": "check"}]}


def _started(project, root, title):
    import hashlib

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = ("# " + title + "\n\n<!-- wf-plan:v1 -->\n```json\n"
           + json.dumps(BLOCK, ensure_ascii=False, indent=2) + "\n```\n")
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, "approve-cw.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                               "sha256:" + hashlib.sha256(prd.encode()).hexdigest()),
                    artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{(payload or {}).get('code')}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{(payload or {}).get('code')}")
    return task_id, task_dir

SID = "sess-CW"

FROM = '''        if after_identity != before_identity:
'''
TO = '''        if after_identity != before_identity and False:
'''


def _envelope(project):
    return {"session": {"provider": "host",
                        "identity": {"host_id": "dsh", "session_id": SID},
                        "instance_id": H.binding_instance(project, SID),
                        "activation": {"enabled": True, "start_source": "human:repro",
                                       "enabled_at": "2026-11-05T00:00:00.000000Z"}},
            "inputs": {"generation": H.generation(project)}}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    task_id, task_dir = _started(project, root, "锁外暂停")
    notes = os.path.join(root, "notes.json")
    json.dump({"standard": {"conclusion": "pass", "basis": "无改动"},
               "requirement": {"conclusion": "pass", "basis": "验收 a1 由 v1 覆盖"}},
              open(notes, "w"), ensure_ascii=False)

    # 验证命令跑 2 秒：足够在锁外窗口里完成一次 task-pause
    proc = subprocess.Popen(
        [H.WF_PYTHON, os.path.join(project, ".wf/bin/wf.py"),
         "task-check", "--task", task_id, "--review-notes", notes, "--json"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc.stdin.write(json.dumps(_envelope(project), ensure_ascii=False))
    proc.stdin.close()

    import time
    time.sleep(0.6)
    rc_pause, payload_pause = H.cli(project, ["task-pause", "--task", task_id,
                                              "--reason", "锁外窗口里暂停", "--json"],
                                    sid=SID, inputs={"generation": H.generation(project)})
    if rc_pause != 0:
        proc.kill()
        raise H.Precondition(f"task-pause 在锁外窗口里失败：{(payload_pause or {}).get('code')}")

    out = (proc.stdout.read() or "").strip()
    proc.wait(timeout=120)
    try:
        payload = json.loads(out) if out.startswith("{") else None
    except ValueError:
        payload = None
    if payload is None:
        raise H.Precondition(f"task-check 未返回 JSON：rc={proc.returncode} out={out[:200]!r}")

    code = payload.get("code")
    record = json.load(open(os.path.join(task_dir, "task.json")))
    problems = []
    if code != "WF_CHECK_STALE":
        problems.append(f"检查结论未被判失效：code={code} facts={payload.get('facts')}")
    if not record.get("paused"):
        problems.append("暂停被 Check 定稿覆盖（记录里 paused 已丢失）")
    pending = (record.get("handoff") or {}).get("pending") or []
    if not any(item.get("reason") == "锁外窗口里暂停" for item in pending if isinstance(item, dict)):
        problems.append(f"暂停原因未保留：handoff.pending={pending}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))