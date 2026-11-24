#!/usr/bin/env python3
"""639/644 spec 三段索引：索引表与两份 checklist 同批同步。

obligation（设计稿 §6.1）：spec 的索引表、开发前 checklist、质量检查三段都要能定位规则；
实现此前只同步 `index.md`，两份 checklist 连承载结构都没有（静态通用条目）。

注入形态：只同步 index.md，跳过两份 checklist。
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib

import _harness as H
import _review_flow as F

SID = "sess-639"
ADD_PATH = ".wf/spec/rules/rule-a.md"
RENAMED_PATH = ".wf/spec/rules/rule-b.md"
CONTENT = "---\ntitle: \"规则 %s\"\nstatus: \"active\"\npaths: [\"pkg/**\"]\n---\n\n# 规则 %s\n\n正文。\n"
FROM = 'def _sync_checklists(root, *, add=None, remove=None, rename=None):\n'
TO = 'def _sync_checklists(root, *, add=None, remove=None, rename=None):\n    return  # 注入：只同步索引表\n'
THREE = (".wf/spec/index.md", ".wf/spec/pre-dev-checklist.md", ".wf/spec/quality-checklist.md")


def seed_spec(project, payload):
    """把 spec 骨架放进项目（普通任务开工不生成 spec，这里按模板落盘）。"""
    spec_dir = os.path.join(project, ".wf/spec")
    os.makedirs(spec_dir, exist_ok=True)
    for name in ("index.md", "pre-dev-checklist.md", "quality-checklist.md"):
        source = os.path.join(payload, "templates", "spec", name)
        shutil.copy2(source, os.path.join(spec_dir, name))



def start_task(project, root, sid, touch_paths=(".wf/spec/**",)):
    """建任务（触碰面覆盖 spec 目录）→ 批准 → 开工。"""
    block = {"schema_version": 1, "touch_paths": list(touch_paths),
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1",
                                "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "spec 三段",
                                  "--template", os.path.join(project, ".wf/templates/task"), "--json"],
                        sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# spec 三段\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n\n内容。\n")
    decision = os.path.join(root, "approve-639.json")
    json.dump([dict(F.decision(f"approve {task_id}", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest()), artifacts=H.plan_artifacts(project, f"approve {task_id}"))],
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


def missing(project, needle):
    # 返回 tuple，便于与 THREE 直接比较（list != tuple 恒真，曾因此误报）
    """三段里哪几段没出现该指针。"""
    absent = []
    for rel in THREE:
        text = open(os.path.join(project, rel), encoding="utf-8").read()
        if needle not in text:
            absent.append(rel)
    return tuple(absent)


def check():
    root, _lib, payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    seed_spec(project, payload)
    # 控制记录先提交，避免被当成「他人未提交改动」挡住开工
    subprocess.run(["git", "add", ".wf"], cwd=project, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "spec skeleton", "--allow-empty"], cwd=project, capture_output=True)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/spec.py"), FROM, TO)
    task_id = start_task(project, root, SID)
    problems = []

    def spec_update(changes):
        path = os.path.join(root, "changes-639.json")
        json.dump(changes, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        return H.cli(project, ["spec-update", "--task", task_id, "--changes", path, "--json"],
                     sid=SID, inputs={"generation": H.generation(project)})

    rc, result = spec_update([{"operation": "add", "new_paths": [ADD_PATH], "content": CONTENT % ("A", "A")}])
    if rc != 0:
        raise H.Precondition(f"add 失败：{(result or {}).get('code')}")
    absent = missing(project, ADD_PATH)
    if absent:
        problems.append(f"新增后未同步：{absent}")

    rc, result = spec_update([{"operation": "rename", "old_paths": [ADD_PATH],
                               "new_paths": [RENAMED_PATH]}])
    if rc != 0:
        raise H.Precondition(f"rename 失败：{(result or {}).get('code')}")
    if missing(project, RENAMED_PATH):
        problems.append(f"改名后未同步：{missing(project, RENAMED_PATH)}")
    if missing(project, ADD_PATH) != THREE:
        problems.append("改名后旧条目仍在")

    rc, result = spec_update([{"operation": "delete", "old_paths": [RENAMED_PATH]}])
    if rc != 0:
        raise H.Precondition(f"delete 失败：{(result or {}).get('code')}")
    if missing(project, RENAMED_PATH) != THREE:
        problems.append("删除后条目仍在")
    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
