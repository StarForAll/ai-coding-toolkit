#!/usr/bin/env python3
"""669/672 复杂度：条件②按事实核对 + 分级/TDD 由人在批准决定中确认。

obligation（设计稿 §4.3/§4.4）：
- 复杂度四项任一为是即按复杂；②③④不能由"调用方不传"关掉（669）；
- 复杂度与 TDD 由人确认并写入批准记录，模型不能自定（672）。

注入形态：不核契约面（②恒为 false）。
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-669"
FROM = 'def contract_surface_condition(root, touch_paths, declared=None):\n'
TO = 'def contract_surface_condition(root, touch_paths, declared=None):\n    return "false", {"fact": "injected"}\n'


_SEQ = {"n": 0}


def _next_sid():
    """每个任务用独立会话：v42 A3「一会话一对象」，同会话建第二个任务会被拒。"""
    _SEQ["n"] += 1
    return f"{SID}-{_SEQ['n']}"


def make_task(project, title, touch_paths):
    sid = _next_sid()
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    block = {"schema_version": 1, "touch_paths": touch_paths,
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, task_dir, "sha256:" + hashlib.sha256(prd.encode()).hexdigest(), sid


def approve(project, root, task_id, digest, plan=None, inputs=None, sid=None):
    path = os.path.join(root, f"decision-{task_id}.json")
    decision = {"source": "human:tester", "at": "2026-11-07T00:00:00.000000Z",
                "subject": f"approve {task_id}", "object_digest": digest,
                "artifacts": H.plan_artifacts(project, f"approve {task_id}"),
                "choice": "approve", "reason": "用例"}
    if plan is not None:
        decision["plan"] = plan
    json.dump([decision], open(path, "w", encoding="utf-8"), ensure_ascii=False)
    payload_inputs = {"generation": H.generation(project)}
    payload_inputs.update(inputs or {})
    return H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                 sid=sid or SID, inputs=payload_inputs)


def _setup():
    """每个用例一个干净项目：任务记录/未提交改动属各自的对象，不跨任务复用工作区。"""
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/a.py"), "w").write("a\n")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/scope.py"), FROM, TO)
    return root, project


def check():
    problems = []

    # ① ②按事实核对：命中 .wf/lib/** 即按复杂，不能靠"不传条件"关掉
    root, project = _setup()
    task_id, task_dir, digest, sid1 = make_task(project, "改门禁", ["pkg/**", ".wf/lib/wflib/gates.py"])
    rc, payload = approve(project, root, task_id, digest, plan={"complexity": "complex"}, sid=sid1)
    if (payload or {}).get("code") != "WF_TEMPLATE_INCOMPLETE":
        problems.append(f"②未按事实触发复杂：{(payload or {}).get('code')}")
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n内容。\n")
    rc, payload = approve(project, root, task_id, digest, plan={"complexity": "complex"}, sid=sid1)
    if rc != 0:
        problems.append(f"补齐产物后仍被拒：{(payload or {}).get('code')}")
    record = json.load(open(os.path.join(task_dir, "task.json"), encoding="utf-8"))
    conditions = [item.get("condition") for item in (record.get("plan") or {}).get("complexity_reasons") or []]
    if "contract" not in conditions:
        problems.append(f"条件事实未入库：{conditions}")
    if (record.get("plan") or {}).get("confirmed_source") != "decision":
        problems.append("复杂分级未记为人工确认（confirmed_source）")

    # ② 人确认的降级：决定文件带 plan.downgrade 才放行，且必须留痕
    root, project = _setup()
    task2, dir2, digest2, sid2 = make_task(project, "降级用例", ["pkg/**", ".wf/lib/wflib/check.py"])
    rc, payload = approve(project, root, task2, digest2, plan={"complexity": "light"}, sid=sid2)
    if (payload or {}).get("code") != "WF_SEMANTIC_DECISION":
        problems.append(f"无理由降级未被拒：{(payload or {}).get('code')}")
    rc, payload = approve(project, root, task2, digest2, sid=sid2,
                          plan={"complexity": "light",
                                "downgrade": {"reason": "只加日志一行", "evidence": "无门禁判定变化"}})
    if rc != 0:
        problems.append(f"有人确认降级仍被拒：{(payload or {}).get('code')}")
    record2 = json.load(open(os.path.join(dir2, "task.json"), encoding="utf-8"))
    if not [item for item in (record2.get("plan") or {}).get("complexity_reasons") or [] if item.get("downgrade")]:
        problems.append("降级条目未留痕")
    if (record2.get("plan") or {}).get("confirmed_source") != "decision":
        problems.append("降级未记为人工确认")

    # ③ 可扩展性：未登记的人判项不丢弃、不阻断，但必须留痕
    root, project = _setup()
    task3, dir3, digest3, sid3 = make_task(project, "新的人判项", ["pkg/**"])
    rc, payload = approve(project, root, task3, digest3, sid=sid3,
                          plan={"review_depth": "deep", "complexity": "light"})
    if rc != 0:
        problems.append(f"未登记人判项导致阻断：{(payload or {}).get('code')}")
    record3 = json.load(open(os.path.join(dir3, "task.json"), encoding="utf-8"))
    plan3 = record3.get("plan") or {}
    if "review_depth" not in (plan3.get("unconfirmed_keys") or []):
        problems.append(f"未登记项未留痕：{plan3.get('unconfirmed_keys')}")
    if (plan3.get("human_inputs") or {}).get("review_depth") != "deep":
        problems.append("未登记项原值未保存")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
