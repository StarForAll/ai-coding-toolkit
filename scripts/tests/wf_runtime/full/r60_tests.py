#!/usr/bin/env python3
"""第二十三轮 R60：查证须核提交树终态、按路径排序、待核进入门禁。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
def sync_journal():
    """把 writer.json 里最后一条回执同步进**提交层账本**（`.wf/install/maintenance.jsonl`）。

    回执账本在提交层，探针从提交树读它；套件模拟维护动作时只写 writer.json 的话，
    探针永远判 pending。断言不变，只是让模拟与真实入口同构。
    """
    sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
    from wflib import maintenance as _m
    receipts = (json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
                .get("maintenance_results") or [])
    if receipts:
        _m.append(F, receipts[-1])


import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def git(*args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=F,
                          capture_output=True, text=True).stdout.strip()


def digest(path):
    return "sha256:" + hashlib.sha256(open(os.path.join(F, path), "rb").read()).hexdigest()


def states():
    return {item["operation"]: item["state"] for item in wf_tasks.task_receipts(F)}


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
open(os.path.join(F, "pkg/a.txt"), "w").write("a0\n")
open(os.path.join(F, "pkg/b.txt"), "w").write("b0\n")
git("add", "-A"); git("commit", "-qm", "初始")
head_before = git("rev-parse", "HEAD")

# 两文件回执（验证排序不再炸）
open(os.path.join(F, "pkg/a.txt"), "w").write("a1\n")
open(os.path.join(F, "pkg/b.txt"), "w").write("b1\n")
after_a, after_b = digest("pkg/a.txt"), digest("pkg/b.txt")
writer_path = os.path.join(F, ".wf/writer.json")
writer = json.load(open(writer_path, encoding="utf-8"))
writer["maintenance_results"] = [{
    "operation": "op-60", "preview_digest": "sha256:" + "1" * 64, "head_before": head_before,
    "changes": [{"path": "pkg/b.txt", "before": None, "after": after_b},
                {"path": "pkg/a.txt", "before": None, "after": after_a}],
    "receipt_git_state": {"head": head_before, "tracked_paths": 2},
    "result": "applied_pending_commit", "disposition": None,
}]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
sync_journal()
rec("R60 多文件回执不抛排序异常", "applied_pending_commit", states().get("op-60"),
    states().get("op-60") == "applied_pending_commit")

# ① 登记 A、实际提交 B（无回执提交）→ 不得误判 persisted
open(os.path.join(F, "pkg/a.txt"), "w").write("a1\n")
open(os.path.join(F, "pkg/b.txt"), "w").write("b1\n")
git("add", "pkg/a.txt", "pkg/b.txt"); git("commit", "-qm", "文件先提交")
rec("R60 仅提交文件、回执未提交时为待提交", "applied_pending_commit", states().get("op-60"),
    states().get("op-60") == "applied_pending_commit")

# ② 内容与登记不符（改内容后再提交回执）→ 不得 persisted
open(os.path.join(F, "pkg/a.txt"), "w").write("aX\n")
git("add", "pkg/a.txt"); git("commit", "-qm", "内容偏离登记")
# 账本在提交层：回执与账本必须一起进提交，否则探针读不到（方案 D）
git("add", ".wf/writer.json", ".wf/install/maintenance.jsonl"); git("commit", "-qm", "提交回执（树与登记不符）")
rec("R60 提交树内容与登记不符→仍待提交", "applied_pending_commit", states().get("op-60"),
    states().get("op-60") == "applied_pending_commit")

# ③ 恢复为登记内容并提交 → 后续提交树已含完整结果，应判 persisted
open(os.path.join(F, "pkg/a.txt"), "w").write("a1\n")
git("add", "pkg/a.txt"); git("commit", "-qm", "恢复为登记内容")
rec("R60 后续提交树已含完整结果→persisted", "persisted", states().get("op-60"),
    states().get("op-60") == "persisted")

# ④ pending_check 必须进门禁：把回执改成不可解析
writer = json.load(open(writer_path, encoding="utf-8"))
writer["maintenance_results"] = [{"operation": "op-60", "result": "unknown-state", "head_before": None,
                                  "changes": [{"path": "pkg/a.txt", "after": after_a}]}]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
sync_journal()
rec("R60 不可核回执为 pending_check", "pending_check", states().get("op-60"),
    states().get("op-60") == "pending_check")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
from wflib import cli as wf_cli
env = "/tmp/r60_env.json"
json.dump(wfdrive.envelope({}, "sess-E9"), open(env, "w"), ensure_ascii=False)
ctx = wf_cli.Context(F, ["--envelope", env])
task = {"id": "2026-" + "e" * 32, "plan": {"touch_paths": ["pkg/**"]}}
caught = None
try:
    wf_tasks._block_overlapping_maintenance(ctx, task)
except Exception as exc:
    caught = getattr(exc, "code", None)
rec("R60 待核回执进入门禁（不再被忽略）", "WF_HISTORY_UNRESOLVED", caught, caught == "WF_HISTORY_UNRESOLVED")

json.dump(results, open("/tmp/r60_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
