"""复杂任务审查链路脚手架：Check 通过 → launch（双伪槽位）→ 可用于 decide 类用例。

`review.launch` 的前置（2026-11-06 查证）：implementation_clis 非空、slots 每项含
slot+reviewer_cli 且与实施 CLI 不同、export_decision、submitted_scope 含三类材料，
并且**任务当前 Check 必须 pass**。本文件把这些一次性封装，供 692/666 复用。
"""
import json
import os
import subprocess
import sys

import _harness as H

IMPLEMENTATION = "codex"
SLOTS = ({"slot": "s1", "reviewer_cli": "pi"}, {"slot": "s2", "reviewer_cli": "claude"})
NOTES = {"standard": {"conclusion": "pass", "basis": "单函数"},
         "requirement": {"conclusion": "pass", "basis": "a1 覆盖"}}


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def prepare(project, root, sid, title="审查任务", complexity="complex"):
    """建任务（可按需复杂）→ 批准 → 开工 → 交付一个文件 → Check pass。返回 (task_id, task_dir)。"""
    import hashlib

    import _review_flow as F

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    # 复杂任务要求 design/implement 有实质正文（WF_TEMPLATE_INCOMPLETE 会拦空 body）
    for name, body in (("design.md", "设计：在 pkg/a.py 中实现 add 的多参数求和支持。\n"),
                       ("implement.md", "实现：修改 add 签名，接受可变参数并累加；用例覆盖 2 与 3 参数。\n")):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n{body}")
    decision = os.path.join(root, "approve-review.json")
    _entry = dict(F.decision(f"approve {task_id}", "approve",
                             "sha256:" + hashlib.sha256(prd.encode()).hexdigest()),
                  artifacts=H.plan_artifacts(project, f"approve {task_id}"))
    # 分级是人的决定内容（机制稿 §2.3：请求 inputs 只作提议）；0.0.2 起复杂分级缺决定即拒
    if complexity:
        _entry["plan"] = {"complexity": complexity}
    json.dump([_entry], open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    inputs = {"generation": H.generation(project)}
    if complexity:
        inputs["complexity"] = complexity
        if complexity == "complex":
            inputs["complexity_conditions"] = {"governance": False}
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=sid, inputs=inputs)
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=sid,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{payload}")
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    git(project, "add", ".wf")
    git(project, "commit", "-qm", "task state", "--allow-empty")
    notes = os.path.join(root, "notes-review.json")
    json.dump(NOTES, open(notes, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-check 未通过：{(payload or {}).get('code')}")
    return task_id, task_dir


def launch(project, root, sid, task_id):
    request = os.path.join(root, "launch-review.json")
    json.dump({
        "implementation_clis": [IMPLEMENTATION],
        "slots": list(SLOTS),
        "export_decision": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                            "subject": ["授权外发审查材料"], "choice": "export"},
        "submitted_scope": {"diff": True, "requirement": True, "test_results": True},
    }, open(request, "w", encoding="utf-8"), ensure_ascii=False)
    # K6 第 3 类：外发要以"确认入库"为准，请求里的 export_decision 只是声明
    auth = os.path.join(root, "export-auth.json")
    json.dump([{"choice": "export", "task": task_id, "materials": ["diff", "requirement", "test_results"], "paths": ["pkg/**"], "quote": "人同意把材料外发给审查 CLI",
                "by": "human:test", "at": "2026-11-10T00:00:00.000000Z",
                "source": "user-declared"}],
              open(auth, "w"), ensure_ascii=False)
    rc_auth, payload_auth = H.cli(project, ["authorize", "record", "--task", task_id, "--file", auth, "--json"],
                                  sid=sid, inputs={"generation": H.generation(project)})
    if rc_auth != 0:
        raise H.Precondition(f"authorize record(export) 失败：{payload_auth}")
    return H.cli(project, ["review-launch", "--task", task_id, "--launch-request", request, "--json"],
                 sid=sid, inputs={"generation": H.generation(project)})
