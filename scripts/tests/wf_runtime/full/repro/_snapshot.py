"""s3（已开工 + 快照缺键）用例共用脚手架。

s3 = 任务已开工，但 `entry_snapshot` 是对象却缺 `touch_paths`。按机制稿 §2.3 与
实现稿「严格三态」，此时批准触碰面**不得回退可变 plan**，每个消费点都必须 fail-closed
（`WF_RECORD_INVALID`）。四类入口（收工 / Check / 写入口 / finish）共用本文件造夹具。
"""
import json
import os
import sys

import _harness as H
import _review_flow as F

INJECT_FROM = ('    if "touch_paths" not in snapshot:\n'
               '        raise TaskError("WF_RECORD_INVALID",\n'
               '                        {"reason": "entry_snapshot lacks touch_paths", "task": task.get("id")})\n')
INJECT_TO = ('    if "touch_paths" not in snapshot:\n'
             '        return list((task.get("plan") or {}).get("touch_paths") or [])  # 注入：缺键回退 plan\n')

BLOCK = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def inject(project):
    H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), INJECT_FROM, INJECT_TO)


def started_task(project, root, sid="sess-S3", title="s3 任务"):
    """建任务 → PRD → 批准 → 开工（不产生未提交改动，避免分类器先行拦截）。"""
    import hashlib

    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", title,
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(BLOCK, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, "approve-s3.json")
    json.dump([F.decision("approve", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=sid,
                        inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-start 失败：{payload}")
    return task_id, task_dir


def damage(task_dir):
    """把快照改成「对象但缺 touch_paths」——s3 状态。"""
    path = os.path.join(task_dir, "task.json")
    record = json.load(open(path, encoding="utf-8"))
    snapshot = record.get("entry_snapshot")
    if not isinstance(snapshot, dict) or "touch_paths" not in snapshot:
        raise H.Precondition(f"开工后快照不是对象或缺 touch_paths：{snapshot!r}")
    snapshot.pop("touch_paths")
    record["entry_snapshot"] = snapshot
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def empty_surface(task_dir):
    """s2 状态：快照存在、`touch_paths` 是**合法空数组**（不是损坏）。"""
    path = os.path.join(task_dir, "task.json")
    record = json.load(open(path, encoding="utf-8"))
    snapshot = record.get("entry_snapshot")
    if not isinstance(snapshot, dict):
        raise H.Precondition(f"开工后快照不是对象：{snapshot!r}")
    snapshot["touch_paths"] = []
    record["entry_snapshot"] = snapshot
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


EMPTY_FALLBACK_FROM = "    return list(paths)\n"
EMPTY_FALLBACK_TO = ("    return list(paths) or list((task.get('plan') or {}).get('touch_paths') or [])"
                     "  # 注入：空数组回退 plan\n")


def inject_empty_fallback(project):
    """注入缺陷：空数组被当成缺失，回退可变 plan。"""
    H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"), EMPTY_FALLBACK_FROM, EMPTY_FALLBACK_TO)
