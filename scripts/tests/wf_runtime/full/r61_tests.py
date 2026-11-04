#!/usr/bin/env python3
"""第二十四轮 R61：完整指纹核验 + 待核必进门禁。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, fingerprint as wf_fp, cli as wf_cli

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def git(*args):
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=F,
                          capture_output=True, text=True).stdout.strip()


def states():
    return {item["operation"]: item["state"] for item in wf_tasks.task_receipts(F)}


def set_receipt(changes, result="applied_pending_commit", head=None):
    writer_path = os.path.join(F, ".wf/writer.json")
    writer = json.load(open(writer_path, encoding="utf-8"))
    writer["maintenance_results"] = [{
        "operation": "op-61", "preview_digest": "sha256:" + "1" * 64,
        "head_before": head or subprocess.run(["git", "rev-parse", "HEAD"], cwd=F,
                                              capture_output=True, text=True).stdout.strip(),
        "changes": changes, "receipt_git_state": {}, "result": result, "disposition": None}]
    json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
open(os.path.join(F, "pkg/f.txt"), "w").write("x\n")
git("add", "-A"); git("commit", "-qm", "初始")

# ① 完整指纹：可执行位不符 → 不得 persisted
open(os.path.join(F, "pkg/f.txt"), "w").write("x\n")
os.chmod(os.path.join(F, "pkg/f.txt"), 0o755)
after = wf_fp.item(F, "pkg/f.txt")
set_receipt([{"path": "pkg/f.txt", "before": None, "after": after}], head=git("rev-parse", "HEAD"))
os.chmod(os.path.join(F, "pkg/f.txt"), 0o644)
git("add", "-A"); git("commit", "-qm", "去掉可执行位")
git("add", ".wf/writer.json"); git("commit", "-qm", "回执（可执行位不符）")
rec("R61 可执行位不符→仍待提交", "applied_pending_commit", states().get("op-61"),
    states().get("op-61") == "applied_pending_commit")

# ② 恢复可执行位 → 树状态与登记一致 → persisted
os.chmod(os.path.join(F, "pkg/f.txt"), 0o755)
git("add", "pkg/f.txt"); git("commit", "-qm", "恢复可执行位")
rec("R61 完整状态一致→persisted", "persisted", states().get("op-61"),
    states().get("op-61") == "persisted")

# ③ 删除登记：文件不存在时可 persisted，存在时不得
os.remove(os.path.join(F, "pkg/f.txt"))
deleted_fp = wf_fp.item(F, "pkg/f.txt")
set_receipt([{"path": "pkg/f.txt", "before": None, "after": deleted_fp}], head=git("rev-parse", "HEAD"))
git("add", "-A"); git("commit", "-qm", "删除文件")
git("add", ".wf/writer.json"); git("commit", "-qm", "回执（登记删除）")
rec("R61 登记删除且确实删除→persisted", "persisted", states().get("op-61"),
    states().get("op-61") == "persisted")

# ④ 历史纯摘要登记仍兼容
open(os.path.join(F, "pkg/g.txt"), "w").write("g\n")
git("add", "-A"); git("commit", "-qm", "g")
legacy = "sha256:" + hashlib.sha256(b"g\n").hexdigest()
set_receipt([{"path": "pkg/g.txt", "before": None, "after": legacy}], head=git("rev-parse", "HEAD"))
git("add", ".wf/writer.json"); git("commit", "-qm", "回执（历史摘要）")
rec("R61 历史摘要登记兼容", "persisted", states().get("op-61"), states().get("op-61") == "persisted")

# ⑤ probe 抛异常时仍可定位路径并被门禁阻断
writer_path = os.path.join(F, ".wf/writer.json")
writer = json.load(open(writer_path, encoding="utf-8"))
writer["maintenance_results"] = [{"operation": "op-61", "head_before": git("rev-parse", "HEAD"),
                                  "changes": [{"path": "pkg/g.txt", "after": legacy}], "result": "x"}]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
original = wf_tasks.maintenance_persisted_probe
wf_tasks.maintenance_persisted_probe = lambda root: (lambda entry: (_ for _ in ()).throw(AttributeError("boom")))
items = wf_tasks.task_receipts(F)
wf_tasks.maintenance_persisted_probe = original
entry = items[0]
rec("R61 探测异常→pending_check 且带路径", "pending_check 且 paths 非空",
    f"{entry['state']} paths={entry['facts'].get('paths')}",
    entry["state"] == "pending_check" and entry["facts"].get("paths"))
env = "/tmp/r61_env.json"
json.dump(wfdrive.envelope({}, "sess-F9"), open(env, "w"), ensure_ascii=False)
ctx = wf_cli.Context(F, ["--envelope", env])
wf_tasks.maintenance_persisted_probe = lambda root: (lambda entry: (_ for _ in ()).throw(AttributeError("boom")))
caught = None
try:
    wf_tasks._block_overlapping_maintenance(ctx, {"id": "2026-" + "e" * 32, "plan": {"touch_paths": ["pkg/**"]}})
except Exception as exc:
    caught = getattr(exc, "code", None)
wf_tasks.maintenance_persisted_probe = original
rec("R61 探测异常→门禁待核出口", "WF_HISTORY_UNRESOLVED", caught, caught == "WF_HISTORY_UNRESOLVED")

json.dump(results, open("/tmp/r61_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
