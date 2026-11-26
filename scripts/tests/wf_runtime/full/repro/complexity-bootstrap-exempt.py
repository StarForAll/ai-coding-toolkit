#!/usr/bin/env python3
"""669a initialize/bootstrap 豁免机械条件①③④（2026-11-07 人裁）。

obligation（设计稿 §4.3「新任务首次定义自己的验收不算变化」+ 2026-11-07 人裁）：
`initialize`/`bootstrap` 要**创建**基线/配置/spec；拿"尚不存在的基线"去判①③④
会让每个新项目的第一步必然复杂。这三项对它不适用；②（契约面）仍参与。

注入形态：取消豁免（initialize 仍按普通任务判①③）。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H

SID = "sess-669a"
FROM = '    bootstrap = (task.get("kind") in ("initialize", "bootstrap"))\n'
TO = '    bootstrap = False  # 注入：取消 bootstrap 豁免\n'
BLOCK = {"schema_version": 1,
         "touch_paths": [".wf/baseline.md", ".wf/project-config.json", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def build(project, root, kind, title, block, plan=None):
    rc, payload = H.cli(project, ["task-new", "--kind", kind, "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=SID)
    if rc != 0:
        raise H.Precondition(f"task-new({kind}) 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    decision = os.path.join(root, f"dec-{task_id}.json")
    _entry = {"source": "human:tester", "at": "2026-11-07T00:00:00.000000Z",
              "subject": f"approve {task_id}",
              "object_digest": "sha256:" + hashlib.sha256(prd.encode()).hexdigest(),
              "artifacts": H.plan_artifacts(project, f"approve {task_id}"),
              "choice": "approve", "reason": "用例"}
    if plan is not None:
        _entry["plan"] = dict(plan)
    json.dump([_entry], open(decision, "w", encoding="utf-8"), ensure_ascii=False)
    return H.cli(project, ["task-approve", "--task", task_id, "--decision", decision, "--json"],
                 sid=SID, inputs={"generation": H.generation(project)})


def fresh(inject):
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    if inject:
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), FROM, TO)
    return root, project


def check():
    inject = os.environ.get("WF_REPRO_INJECT") == "1"
    problems = []

    # ① initialize：触碰基线/配置/spec（且无既有基线）→ 不应被机械条件判复杂
    root, project = fresh(inject)
    rc, payload = build(project, root, "initialize", "初始化基线", BLOCK)
    code = (payload or {}).get("code")
    # "被判复杂"在入口有两副面孔：要求补三件套（`WF_TEMPLATE_INCOMPLETE`）或要人裁分级
    # （`WF_SEMANTIC_DECISION`）。红模注入取消 bootstrap 豁免后出现的是后者——原用例只认前者，
    # 把目标失败当成了前置失败，red 面因此长期不可证伪（三轮自检修正）。
    if code in ("WF_TEMPLATE_INCOMPLETE", "WF_SEMANTIC_DECISION"):
        problems.append(f"initialize 被判成复杂：{code}")
    elif rc != 0:
        raise H.Precondition(f"initialize 批准失败：{code} {(payload or {}).get('facts')}")

    # ② 普通任务触碰同一批路径 → 仍应判复杂（豁免不得外溢）
    root2, project2 = fresh(inject)
    rc, payload = build(project2, root2, "ordinary", "改基线", BLOCK,
                        plan={"complexity": "complex"})
    if (payload or {}).get("code") != "WF_TEMPLATE_INCOMPLETE":
        problems.append(f"普通任务触碰基线未被判复杂：{(payload or {}).get('code')}")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
