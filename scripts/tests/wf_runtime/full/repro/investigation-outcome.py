#!/usr/bin/env python3
"""六轮-9：零触碰面的纯调查任务不再被 `before_check` 自循环卡住。

obligation（设计稿 §4.2「纯调查须有可观察成果」+ task-flow 的 work-satisfied）：
零触碰面任务的成果由**已批准规划的验收项**承载，Check 逐条给结论；旧实现要求
「复盘 / curation / 历史 Check pass」，而 Check 又卡在这条前置上——自循环，
让"只交一份根因结论"的任务无路可走。

红模：把前置退回旧口径（要复盘/curation/历史 pass）→ 首次 Check 被
`WF_CHECK_FAILED` 挡住，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-INV"

FROM = '''        plan = task.get("plan") or {}
        acceptance = [item for item in plan.get("acceptance") or [] if isinstance(item, dict)]
        if not acceptance:
'''
TO = '''        plan = task.get("plan") or {}
        acceptance = [item for item in plan.get("acceptance") or [] if isinstance(item, dict)]
        if not (task.get("retrospective") or task.get("curation")
                or (task.get("check") or {}).get("result") == "pass"):  # 注入：旧前置
'''


def _block():
    return {"schema_version": 1, "touch_paths": [],
            "acceptance": [{"id": "a1", "statement": "给出根因结论（命令核对输出）",
                            "verification_ids": ["v1"]}],
            "verifications": [{"id": "v1", "invocation": {"kind": "argv",
                                                          "argv": [H.WF_PYTHON, "-c",
                                                                   "print('root cause: cache stale')"]},
                               "cwd": ".", "input_refs": [], "required": True,
                               "consume_at": "check"}]}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    root_lib = os.path.join(project, ".wf/lib")
    if root_lib not in sys.path:
        sys.path.insert(0, root_lib)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "只做根因分析",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = ("# 根因分析\n\n<!-- wf-plan:v1 -->\n```json\n"
           + json.dumps(_block(), ensure_ascii=False, indent=2) + "\n```\n")
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    decision = os.path.join(root, "approve.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve", digest),
                    artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(decision, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    notes = os.path.join(root, "notes.json")
    json.dump({"standard": {"conclusion": "pass", "basis": "只读分析，无代码改动"},
               "requirement": {"conclusion": "pass", "basis": "a1 由 v1 覆盖根因结论"}},
              open(notes, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    if rc != 0 or code != "WF_OK":
        raise H.TargetFailure(f"纯调查任务首轮 Check 被前置挡住：code={code} "
                              f"facts={(payload or {}).get('facts')}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))