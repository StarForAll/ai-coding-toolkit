#!/usr/bin/env python3
"""B5：基线提案由入口生成（--files + 人的批准），不再手写 JSON。

obligation（dogfood 2026-11-07：agent 手写 baseline-proposal.json 才能应用）：
"哪些文件、什么内容、前像是什么"是机械事实，该由入口从工作树读；
人只给批准（决定文件）。手写提案是把结构负担推给人/模型。

注入形态：取消 --files 路径（退回只认 --proposal）。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib

import _harness as H
import _review_flow as F

SID = "sess-b5"
FROM = '    files_arg = args.value("--files")\n'
TO = '    files_arg = None  # 注入：只认 --proposal\n'



def start_task(project, root, sid):
    """建一个触碰面覆盖基线/配置/spec 的任务并开工。"""
    touch = [".wf/baseline.md", ".wf/project-config.json", ".wf/spec/**"]
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "建基线",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# 建基线\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n内容。\n")
    decision = os.path.join(root, "approve-plan.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                              "sha256:" + hashlib.sha256(prd.encode()).hexdigest()),
                     artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=sid,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{payload}")
    return task_id

def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    task_id = start_task(project, root, SID)

    # 交付：基线 + 配置 + spec 骨架（真实文件写在工作树）
    os.makedirs(os.path.join(project, ".wf/spec"), exist_ok=True)
    open(os.path.join(project, ".wf/baseline.md"), "w", encoding="utf-8").write("# 基线\n\n## 目标与范围\n\n演示。\n")
    open(os.path.join(project, ".wf/project-config.json"), "w", encoding="utf-8").write(
        json.dumps({"schema_version": 1, "tdd_default": False}, ensure_ascii=False) + "\n")
    open(os.path.join(project, ".wf/spec/index.md"), "w", encoding="utf-8").write("# spec 索引\n")
    files = ".wf/baseline.md,.wf/project-config.json,.wf/spec/index.md"
    # ① 预览：入口算好提案内容摘要，人据此批准（不手写提案 JSON）
    rc, payload = H.cli(project, ["baseline-apply", "--task", task_id, "--files", files,
                                  "--preview", "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    facts = (payload or {}).get("facts") or {}
    digest = facts.get("proposal_digest")
    if rc != 0 or not digest:
        raise H.TargetFailure(f"未按 --files 生成提案摘要：{(payload or {}).get('code')}")
    decision = os.path.join(root, "approve-baseline.json")
    json.dump([{"source": "human:tester", "at": "2026-11-07T00:00:00.000000Z",
                "subject": f"批准基线 {task_id}", "object_digest": digest,
                "choice": "approve", "reason": "基线内容已看过"}],
              open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["baseline-apply", "--task", task_id,
                                  "--files", files,
                                  "--decision", decision, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    problems = []
    if rc != 0:
        problems.append(f"--files 生成提案失败：{(payload or {}).get('code')} "
                        f"{(payload or {}).get('facts')}")
    else:
        facts = (payload or {}).get("facts") or {}
        accepted = set(facts.get("written") or []) | set(facts.get("skipped") or [])
        for rel in (".wf/baseline.md", ".wf/project-config.json", ".wf/spec/index.md"):
            if rel not in accepted:
                problems.append(f"未被接受：{rel}（written={facts.get('written')} skipped={facts.get('skipped')}）")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
