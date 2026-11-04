#!/usr/bin/env python3
"""第二十二轮 R59：维护回执已提交即派生 persisted。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, scope as wf_scope

F = wfdrive.FIX
results = []
AT = "2026-11-04T19:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-D1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R59"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2); return path


def git(*args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=F,
                          capture_output=True, text=True).stdout.strip()


# 构造：一条 applied_pending_commit 回执 + 独立登记文件，先不提交
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
open(os.path.join(F, "pkg/m.txt"), "w").write("m\n")
git("add", "-A"); git("commit", "-qm", "登记文件初始")
head_before = git("rev-parse", "HEAD")
open(os.path.join(F, "pkg/m.txt"), "w").write("m changed\n")
after = "sha256:" + hashlib.sha256(open(os.path.join(F, "pkg/m.txt"), "rb").read()).hexdigest()

writer_path = os.path.join(F, ".wf/writer.json")
writer = json.load(open(writer_path, encoding="utf-8"))
writer["maintenance_results"] = [{
    "operation": "probe-op-1", "preview_digest": "sha256:" + "1" * 64, "head_before": head_before,
    "changes": [{"path": "pkg/m.txt", "before": None, "after": after}],
    "receipt_git_state": {"head": head_before, "tracked_paths": 1},
    "result": "applied_pending_commit", "disposition": None,
}]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

states = {item["operation"]: item["state"] for item in wf_tasks.task_receipts(F)}
rec("R59 未提交时为待提交", "applied_pending_commit", states.get("probe-op-1"),
    states.get("probe-op-1") == "applied_pending_commit")
rec("R59 待提交计入重叠阻断", "非空",
    len(__import__("wflib.writer", fromlist=["writer"]).blocking_receipts(wf_tasks.task_receipts(F), ["pkg/m.txt"])),
    bool(__import__("wflib.writer", fromlist=["writer"]).blocking_receipts(wf_tasks.task_receipts(F), ["pkg/m.txt"])))

# 提交回执与全部登记文件终态 → 读取即派生 persisted
git("add", "-A"); git("commit", "-qm", "提交回执与登记终态")
states = {item["operation"]: item["state"] for item in wf_tasks.task_receipts(F)}
rec("R59 完整提交后派生 persisted", "persisted", states.get("probe-op-1"),
    states.get("probe-op-1") == "persisted")
rec("R59 不再计入门禁重叠", "空",
    len(__import__("wflib.writer", fromlist=["writer"]).blocking_receipts(wf_tasks.task_receipts(F), ["pkg/m.txt"])),
    not __import__("wflib.writer", fromlist=["writer"]).blocking_receipts(wf_tasks.task_receipts(F), ["pkg/m.txt"]))
rec("R59 工作区干净", "", git("status", "--porcelain"), git("status", "--porcelain") == "")
writer_now = json.load(open(writer_path, encoding="utf-8"))
rec("R59 回执本身未被改写（不写 writer）", "result 仍是 applied_pending_commit",
    (writer_now.get("maintenance_results") or [{}])[0].get("result"),
    (writer_now.get("maintenance_results") or [{}])[0].get("result") == "applied_pending_commit")

# 重叠任务可开工
clean_gen = json.load(open(writer_path, encoding="utf-8")).get("generation")
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R59 重叠任务",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-D2")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
rec("R59 重叠任务创建", "创建成功", (task_id or "")[:12], bool(task_id))
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R59 重叠任务\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r59_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r59_a.json", "--json"],
   {"generation": gen, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-D2")
open(os.path.join(F, "pkg/n.txt"), "w").write("n\n")
rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": gen}, "sess-D2")
rec("R59 重叠任务可开工（不再 WF_WIP_UNRESOLVED）", "WF_OK", (payload or {}).get("code"), rc == 0)

json.dump(results, open("/tmp/r59_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
