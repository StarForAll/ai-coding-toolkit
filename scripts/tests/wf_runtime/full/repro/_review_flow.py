"""CLI 级 review 流程的公共步骤（review-decide 相关 repro 共用）。"""
import json
import os
import subprocess

import _harness as H

NOTE = {"standard": {"conclusion": "pass", "basis": "b"},
        "requirement": {"conclusion": "pass", "basis": "b"}}
AXES = ("range", "acceptance", "contract", "regression", "testability")
AT = "2026-11-05T00:00:00.000000Z"
REPORT = """<!-- wf-review-report:v1 -->
```json
{body}
```
"""


def decision(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "repro"}


def build_task(project, root, title="repro 任务", sid="sess-R"):
    """建任务 → 写 PRD 计划块 → 批准 → 开工。返回 (task_id, task_dir)。"""
    H.ensure_project_config(project)
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new failed: {payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    import hashlib

    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w").write(f"# {name}\n\n内容。\n")
    path = os.path.join(root, "approve.json")
    json.dump([decision("approve", "approve",
                        "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open(path, "w"), ensure_ascii=False)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve failed: {payload}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start failed: {payload}")
    return task_id, task_dir


def run_review(project, root, task_id, task_dir, slot_clis, sid="sess-R", axes=None):
    """check → launch → import 两份报告 → decide。返回 (decide_rc, 载荷, 记录)。"""
    axes = axes or {axis: {"conclusion": "pass", "basis": "b"} for axis in AXES}
    # 任务记录/绑定/写权属于本次任务的既有改动，先提交，Check 才不会把它们当冲突候选
    # 只提交治理面：业务文件 pkg/a.py 保持未提交，属本任务自己的改动（e 桶）
    subprocess.run(["git", "add", ".wf"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "task state", "--allow-empty"],
                   cwd=project, check=True, capture_output=True)
    notes = os.path.join(root, "notes.json")
    json.dump(NOTE, open(notes, "w"), ensure_ascii=False)
    ack = os.path.join(root, "ack.json")
    json.dump([decision("external-checked", "external-checked")], open(ack, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                                  "--decision", ack, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-check failed: {payload}")
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    check = record.get("check") or {}
    anchor = (check.get("anchor") or {}).get("check_anchor")
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": f"slot-{i}", "reviewer_cli": cli} for i, cli in enumerate(slot_clis)],
               "export_decision": decision("export", "approve"),
               "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    launch_path = os.path.join(root, "launch.json")
    json.dump(request, open(launch_path, "w"), ensure_ascii=False)
    # K6 第 3 类：材料外发必须有对应确认入库（请求里的 export_decision 只是声明）
    auth = os.path.join(root, "export.json")
    json.dump([{"choice": "export", "paths": ["pkg/**"], "quote": "人同意把材料外发给审查 CLI"}],
              open(auth, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["authorize", "record", "--task", task_id, "--file", auth, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"authorize record(export) failed: {payload}")
    rc, payload = H.cli(project, ["review-launch", "--task", task_id,
                                  "--launch-request", launch_path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"review-launch failed: {payload}")
    facts = (payload or {}).get("facts") or {}
    temp_paths = facts.get("temp_paths") or []
    if len(temp_paths) != len(slot_clis):
        raise H.Precondition(f"review-launch 未给出逐槽位暂存目录：{list(facts)}")
    for i, cli_name in enumerate(slot_clis):
        body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1,
                "reviewer-id": f"slot-{i}", "source-cli": cli_name, "review-time": AT,
                "review-focus": "x",
                "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
                "read-scope": ["pkg/**"],
                "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"],
                "scope-exceptions": [], "axes": axes, "findings": [], "verdict": "pass"}
        slot_dir = temp_paths[i]
        os.makedirs(slot_dir, exist_ok=True)
        report = os.path.join(slot_dir, "report.md")
        open(report, "w", encoding="utf-8").write(REPORT.format(slot=f"slot-{i}",
                                                                body=json.dumps(body, ensure_ascii=False, indent=2)))
        rc, payload = H.cli(project, ["review-import", "--task", task_id, "--round", "1",
                                      "--slot", f"slot-{i}", "--report", report, "--json"],
                            sid=sid, inputs={"generation": H.generation(project)})
        if rc != 0:
            raise H.Precondition(f"review-import failed: {payload}")
    rc, payload = H.cli(project, ["review-decide", "--task", task_id, "--round", "1", "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    return rc, payload, record
