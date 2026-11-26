#!/usr/bin/env python3
"""六轮-7：再次批准时，「扩面」按包含关系判、「验收口径变化」按摘要判（设计稿 §4.3 条件③④）。

obligation：`src/a.py → src/**` 相交但确实扩大了面（旧判据用"是否相交"漏判）；沿用原验收 id
只改判据文字同样是新承诺（旧判据只比 id 集合漏判）。两者都必须由 `task-approve --draft`
的 `complexity_proposal` 如实提议为复杂。

红模：把扩面判据退回"是否相交" → 提议里缺 `scope` 条件，目标断言变红。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-EXP"

FROM = '''        covering = [old for old in previous if paths_mod.subsumes(touch, old)]
        if not covering:
'''
TO = '''        covering = [old for old in previous if not paths_mod.provably_disjoint(old, touch)]
        if not covering:
'''


def _block(touch, statement):
    return {"schema_version": 1, "touch_paths": list(touch),
            "acceptance": [{"id": "a1", "statement": statement, "verification_ids": ["v1"]}],
            "verifications": [{"id": "v1",
                               "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                               "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def _prd(block):
    return ("# 扩面判据\n\n<!-- wf-plan:v1 -->\n```json\n"
            + json.dumps(block, ensure_ascii=False, indent=2) + "\n```\n")


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/scope.py"), FROM, TO)

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "扩面判据",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])

    prd = _prd(_block(["pkg/a.py"], "旧判据"))
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    decision = os.path.join(root, "approve.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve", digest),
                    artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
              open(decision, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"首次批准失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    # 再次规划：触碰面从单文件扩到整目录，验收 id 不变但判据文字变了
    prd2 = _prd(_block(["pkg/**"], "新判据（覆盖目录内全部文件）"))
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd2)
    digest2 = "sha256:" + hashlib.sha256(prd2.encode()).hexdigest()
    replan = os.path.join(root, "replan.json")
    json.dump([dict(F.decision([task_id, "replan"], "replan", digest2))],
              open(replan, "w"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-replan", "--task", task_id, "--decision", replan, "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-replan 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")

    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--draft", "--json"],
                        sid=SID, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve --draft 失败：{(payload or {}).get('code')} {(payload or {}).get('facts')}")
    facts = (payload or {}).get("facts") or {}
    proposal = facts.get("complexity_proposal") or {}
    conditions = [item.get("condition") for item in proposal.get("reasons") or []
                  if isinstance(item, dict)]
    problems = []
    if proposal.get("value") != "complex":
        problems.append(f"提议不是复杂：{proposal}")
    if "scope" not in conditions:
        problems.append(f"扩面未按包含关系判出（缺 scope 条件）：{conditions}")
    if "acceptance" not in conditions:
        problems.append(f"验收口径变化未按摘要判出（缺 acceptance 条件）：{conditions}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))