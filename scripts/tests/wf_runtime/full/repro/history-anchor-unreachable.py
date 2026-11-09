#!/usr/bin/env python3
"""F-67／设计稿 §4.2、§5.4：任务基线被重写（`git commit --amend`）后历史锚点不可达，
`task-check` 必须 `WF_HISTORY_UNRESOLVED`（只读核对、带三个出口），不得静默通过；
基线可达性恢复（`git reset --soft` 回到原基线提交，不动工作树）后同一检查通过。

注入形态：把 Check 的不可达判定改成恒假——重写历史后仍按普通路径放行，
即夹具未覆盖清单点名的缺陷形态「静默通过而非报锚点不可达」。
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
        H.patch(os.path.join(project, ".wf/lib/wflib/check.py"),
                "    if (external or {}).get(\"unreachable\"):",
                "    if False:  # 注入：基线不可达静默放行")
    task_id, task_dir = F.build_task(project, root, title="历史锚点不可达")
    record_path = os.path.join(task_dir, "task.json")
    baseline = json.load(open(record_path, encoding="utf-8"))["baseline_head"]
    notes = os.path.join(root, "notes.json")
    json.dump(F.NOTE, open(notes, "w"), ensure_ascii=False)
    ack = os.path.join(root, "ack.json")
    json.dump([F.decision("external-checked", "external-checked")], open(ack, "w"))

    def run_check():
        return H.cli(project, ["task-check", "--task", task_id, "--review-notes", notes,
                               "--decision", ack, "--json"],
                     inputs={"generation": H.generation(project)})

    # 负例：开工后重写基线提交 → 锚点不可达
    subprocess.run(["git", "commit", "--amend", "-qm", "rewritten fixture baseline", "--allow-empty"],
                   cwd=project, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project,
                          capture_output=True, text=True).stdout.strip()
    if head == baseline:
        raise H.Precondition("amend 未重写基线提交（夹具失效）")
    rc, payload = run_check()
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_HISTORY_UNRESOLVED", "history-anchor-unreachable")
    facts = (payload or {}).get("facts") or {}
    problems = []
    if rc == 0:
        problems.append("基线不可达仍放行（rc=0）")
    if (payload or {}).get("code") != "WF_HISTORY_UNRESOLVED":
        problems.append(f"原因码不是 WF_HISTORY_UNRESOLVED：{(payload or {}).get('code')}")
    if not facts.get("exits"):
        problems.append("未给恢复出口")
    if problems:
        raise H.TargetFailure("；".join(problems))

    # 正例：软重置回原基线提交（工作树不动、写权代次不变）→ 同一检查通过
    subprocess.run(["git", "reset", "--soft", baseline], cwd=project, check=True, capture_output=True)
    rc, payload = run_check()
    H.require_success(payload, rc, "可达性恢复后的重检")
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
