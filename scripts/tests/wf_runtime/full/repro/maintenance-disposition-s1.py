#!/usr/bin/env python3
"""629.s1.c7：未结维护回执在开工期阻断，且「处置字段齐」不等于「已结案」。

obligation（§96 ① s1 × c7 / 机制稿 §4.5）：与本次请求范围重叠的未结维护组必须阻断开工；
处置（commit / reverse / transfer）要做**事实核验**——只写了 disposition 而事实对不上，
只能落 `pending_check`（`WF_HISTORY_UNRESOLVED`），不能当已结案放行。

注入形态：`maintenance_disposition_probe` 一律返回 True（字段齐即结案）。
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _harness as H
import _review_flow as F

SID = "sess-S7"
BLOCK = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1",
                            "invocation": {"kind": "argv", "argv": [H.WF_PYTHON, "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True,
                          check=False).stdout.strip()


def approved_not_started(project, root, sid=SID):
    rc, payload = H.cli(project, ["task-new", "--kind", "ordinary", "--title", "s1 回执",
                                  "--template", os.path.join(project, ".wf/templates/task"),
                                  "--json"], sid=sid)
    if rc != 0:
        raise H.Precondition(f"task-new 失败：{payload}")
    task_id = payload["facts"]["task_id"]
    task_dir = os.path.join(project, payload["facts"]["directory"])
    prd = f"# s1 回执\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(BLOCK, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(task_dir, name), "w", encoding="utf-8").write(f"# {name}\n")
    path = os.path.join(root, "approve-c7.json")
    import hashlib
    json.dump([F.decision("approve", "approve",
                          "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open(path, "w", encoding="utf-8"), ensure_ascii=False)
    rc, payload = H.cli(project, ["task-approve", "--task", task_id, "--decision", path, "--json"],
                        sid=sid, inputs={"generation": H.generation(project)})
    if rc != 0:
        raise H.Precondition(f"task-approve 失败：{payload}")
    return task_id


def write_receipt(project, disposition=None):
    path = os.path.join(project, ".wf/writer.json")
    record = json.load(open(path, encoding="utf-8"))
    sys.path.insert(0, os.path.join(project, ".wf/lib"))
    from wflib import fingerprint  # noqa: PLC0415 — 用被审对象的指纹实现，避免自造格式

    fp_b1 = fingerprint.item(project, "pkg/b.py")
    entry = {
        "operation": "op-c7", "preview_digest": "sha256:" + "1" * 64,
        "head_before": git(project, "rev-parse", "HEAD"),
        "changes": [{"path": "pkg/b.py", "before": None, "after": fp_b1}],
        "receipt_git_state": {"head": git(project, "rev-parse", "HEAD"), "tracked_paths": 1},
        "result": "applied_pending_commit", "disposition": disposition,
    }
    record["maintenance_results"] = [entry]
    json.dump(record, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def check():
    root, _lib, _payload = H.stage()
    project = H.deploy(root)
    H.ensure_project_config(project)
    os.makedirs(os.path.join(project, "pkg"), exist_ok=True)
    open(os.path.join(project, "pkg/b.py"), "w").write("b0\n")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "基线")
    if os.environ.get("WF_REPRO_INJECT") == "1":
        H.patch(os.path.join(project, ".wf/lib/wflib/tasks.py"),
                '    def probe(entry):\n        disposition = entry.get("disposition") or {}',
                '    def probe(entry):\n        return True  # 注入：处置字段齐即结案，不核事实\n'
                '        disposition = entry.get("disposition") or {}')
    task_id = approved_not_started(project, root)
    open(os.path.join(project, "pkg/b.py"), "w").write("b1\n")   # 维护组「已应用未提交」
    problems = []

    # ① 没有处置 → 未结维护组阻断开工，且点名该路径
    write_receipt(project)
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_WIP_UNRESOLVED", "s1.c7 未结")
    facts = (payload or {}).get("facts") or {}
    named = [item.get("path") for item in (facts.get("overlapping_receipts") or [])]
    if rc == 0:
        problems.append("未结维护组未阻断开工")
    elif named != ["pkg/b.py"]:
        problems.append(f"阻断项未点名 pkg/b.py：{named}")

    # ② 写了处置但事实对不上（claim 提交、实际未提交）→ 只能 pending_check
    write_receipt(project, disposition={"kind": "commit",
                                       "decision": {"choice": "commit", "source": "human",
                                                    "at": "2026-11-06T00:00:00.000000Z"},
                                       "evidence": {"commit": git(project, "rev-parse", "HEAD")}})
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    H.require_business_code(payload, rc)
    H.only_two_outcomes((payload or {}).get("code") if rc != 0 else "WF_OK",
                        "WF_HISTORY_UNRESOLVED", "s1.c7 处置不可核")
    if rc == 0:
        problems.append("处置事实不可核却放行（字段齐被当作已结案）")

    # ③ 真正提交后，回执派生 persisted → 开工成立
    git(project, "add", "-A")
    git(project, "commit", "-qm", "处置提交")
    rc, payload = H.cli(project, ["task-start", "--task", task_id, "--json"], sid=SID,
                        inputs={"generation": H.generation(project)})
    if rc != 0 or (payload or {}).get("code") != "WF_OK":
        problems.append(f"处置完成后开工仍被拒：{(payload or {}).get('code')}")

    if problems:
        raise H.TargetFailure("；".join(problems))
    return None


if __name__ == "__main__":
    sys.exit(H.main(check))
