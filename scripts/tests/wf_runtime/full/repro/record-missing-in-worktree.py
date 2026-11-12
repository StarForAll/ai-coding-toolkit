#!/usr/bin/env python3
"""F-68／设计稿 §5.4：任务记录提交进历史后从工作树删除，
`task-check` 必须 `WF_RECORD_INVALID`（结构化 JSON、带恢复出口），
`inspect` 必须把该目录列入 `broken_task_dirs`；恢复文件后同一检查通过。

注入形态（2026-11-12 调整）：把「记录缺失」分支的原因码换掉（`WF_RECORD_INVALID` →
`WF_TARGET_MISSING`）。原先注的是「静默忽略」，但 `task-check` 拆两段锁后缺记录出口抽成
`_require_task_dir()`、下游两步都假设记录是 dict，静默跳过只会得到内部错误 70 而不是业务结论——
该缺陷形态在新结构下已不可达。换原因码的注入仍能证明：本用例核的是**具体码 + 恢复出口**。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    if os.environ.get("WF_REPRO_INJECT") == "1":
        # 2026-11-12：`task-check` 拆两段锁后，缺记录出口抽成 `_require_task_dir()` 供两段共用。
        # 「静默忽略」这个旧缺陷形态**已不可达**——下游两步都假设记录是 dict，跳过守卫只会
        # 得到内部错误 70（不是业务结论）。所以注入改为「守卫在，但报错的原因码不对」：
        # 这仍然证明本用例核的是**具体原因码 + 恢复出口**，而不是"随便报个错就算过"。
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                '    raise TaskError("WF_RECORD_INVALID", {\n'
                '        "reason": "task record is missing from the worktree",',
                '    raise TaskError("WF_TARGET_MISSING", {  # 注入：原因码不对\n'
                '        "reason": "task record is missing from the worktree",')
    task_id, task_dir = F.build_task(project, root, title="记录缺失负例")
    notes = os.path.join(root, "notes.json")
    json.dump(F.NOTE, open(notes, "w"), ensure_ascii=False)
    ack = os.path.join(root, "ack.json")
    json.dump([F.decision("external-checked", "external-checked")], open(ack, "w"))
    record_path = os.path.join(task_dir, "task.json")

    # 记录先进历史，再从工作树删除（历史里有、现场没有）
    subprocess.run(["git", "add", ".wf"], cwd=project, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "record exists"], cwd=project, check=True, capture_output=True)
    os.remove(record_path)

    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                                  "--decision", ack, "--json"],
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    facts = (payload or {}).get("facts") or {}
    problems = []
    if rc == 0:
        problems.append("工作树缺任务记录仍放行（rc=0）")
    if (payload or {}).get("code") != "WF_RECORD_INVALID":
        problems.append(f"原因码不是 WF_RECORD_INVALID：{(payload or {}).get('code')}")
    if not facts.get("exits"):
        problems.append("未给恢复出口")
    if not (payload or {}).get("exit"):
        problems.append("缺 exit 提示")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # 巡检面：缺记录目录必须被列入 broken_task_dirs（不静默当没有）
    rc, inspect = H.cli(project, ["inspect", "--json"])
    H.require_success(inspect, rc, "inspect")
    broken = ((inspect or {}).get("facts") or {}).get("broken_task_dirs") or []
    if not any(str(item.get("path", "")) == task_dir for item in broken):
        raise H.TargetFailure(
            f"inspect 未把缺记录目录列入 broken_task_dirs：{json.dumps(broken, ensure_ascii=False)[:200]}")

    # 正例：从 Git 恢复记录后同一检查通过
    subprocess.run(["git", "checkout", "--", record_path], cwd=project, check=True, capture_output=True)
    rc, payload = H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                                  "--decision", ack, "--json"],
                        inputs={"generation": H.generation(project)})
    H.require_success(payload, rc, "恢复记录后的重检")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
