#!/usr/bin/env python3
"""六轮-A1：`task-check --workspace-exclusion` 的声明必须在三段全流程里成立并落盘。

obligation（设计稿 §4.2 的外来改动排除 + 机制稿 §3.5）：排除声明是**人给出的输入**，
Check 准备段登记后，定稿段重读盘上记录时必须把它重放（否则前后分类不一致 → 假 `WF_CHECK_STALE`，
且新声明永远不落盘）。六轮修「以盘上记录为准」时只重放了调试声明，漏了这一项。

红模：去掉定稿段的重放 → 检查必然 `WF_CHECK_STALE`，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-EXCL"

FROM = '''        if state.get("exclusion_records"):
            scope.persist_exclusions(fresh, state["exclusion_records"])
'''
TO = '''        pass  # 注入：不重放本次 Check 登记的排除声明
'''


def _block():
    return {"schema_version": 1, "touch_paths": ["pkg/a.txt"],
            "acceptance": [{"id": "a1", "statement": "a.txt 内容为 ok", "verification_ids": ["v1"]}],
            "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": [
                "/usr/bin/python3", "-c",
                "import sys;sys.exit(0 if open('pkg/a.txt').read().strip()=='ok' else 1)"]},
                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.txt"), "w").write("ok\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "排除声明",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = ("# 排除声明\n\n<!-- wf-plan:v1 -->\n```json\n"
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

    # 开工后出现的**外来未提交改动**（不属于本任务、不在触碰面内）
    with open(os.path.join(project, "foreign.txt"), "w", encoding="utf-8") as handle:
        handle.write("local tool state\n")
    declaration = os.path.join(root, "exclusion.json")
    json.dump({"choice": "排除外来改动", "paths": ["foreign.txt"],
               "reason": "本地工具临时数据，不属本任务", "by": "human:repro",
               "at": "2026-11-26T08:00:00Z", "quote": "保持原样", "source": "user-declared"},
              open(declaration, "w"), ensure_ascii=False)

    notes = os.path.join(root, "notes.json")
    json.dump({"standard": {"conclusion": "pass", "basis": "只动 pkg/a.txt"},
               "requirement": {"conclusion": "pass", "basis": "a1 由 v1 覆盖"}},
              open(notes, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                                  "--workspace-exclusion", declaration, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    code = (payload or {}).get("code")
    if rc != 0 or code != "WF_OK":
        raise H.TargetFailure(f"带排除声明的 Check 未通过：code={code} "
                              f"facts={json.dumps((payload or {}).get('facts') or {}, ensure_ascii=False)[:600]}")

    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    entries = ((record.get("execution") or {}).get("workspace_exclusions")) or []
    paths = [item.get("path") for item in entries if isinstance(item, dict)]
    if "foreign.txt" not in paths:
        raise H.TargetFailure(f"排除声明未落盘：workspace_exclusions={paths}")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))