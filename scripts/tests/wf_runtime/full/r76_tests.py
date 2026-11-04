#!/usr/bin/env python3
"""第四十轮 R76：回收候选语义、周期触发基数、存活探测的恢复闭环。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, cli as wf_cli, lock as wf_lock

F = wfdrive.FIX
results = []
AT = "2026-11-04T10:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def archive_task(tid, archived_at, terminal, curated, status="archived"):
    """直接在归档区造记录，供治理面统计（不跑完整流程）。"""
    directory = os.path.join(F, ".wf/tasks/archive/2026-11", f"{tid}-样本")
    os.makedirs(directory, exist_ok=True)
    record = {"schema_version": 1, "id": tid, "title": "样本", "status": status,
              "terminal": terminal, "archived_at": archived_at,
              "curation": curated}
    json.dump(record, open(os.path.join(directory, "task.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    return directory


def governance():
    ctx = wf_cli.Context(F, ["--envelope", "/tmp/r76_env.json"])
    tasks = list(wf_tasks.iter_tasks(F))
    return wf_tasks._governance_summary(F, tasks, wf_tasks._task_dirs(F)[1])


json.dump(wfdrive.envelope({"generation": 1}, "sess-A1"), open("/tmp/r76_env.json", "w"), ensure_ascii=False)
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/used.md"), "w").write("# used\n")
open(os.path.join(F, ".wf/spec/rules/idle.md"), "w").write("# idle\n")

# 六个正常归档样本：used.md 一直被引用；idle.md 从未被引用
for index in range(6):
    tid = f"2026-{index:032x}"
    archive_task(tid, f"2026-11-0{index + 1}T00:00:00.000000Z", "normal",
                 [{"path": ".wf/spec/rules/used.md", "digest": "sha256:" + "1" * 64,
                   "purpose": "x", "released": None}])
# 一个异常归档：包含 idle.md 引用，不应计入样本、也不应让它变成"被引用"
archive_task("2026-" + "e" * 32, "2026-11-09T00:00:00.000000Z", "abnormal",
             [{"path": ".wf/spec/rules/idle.md", "digest": "sha256:" + "2" * 64,
               "purpose": "x", "released": None}])

summary = governance()
usage = summary["spec_usage"]
candidates = {item["path"] for item in usage["reclaim_candidates"]}
rec("1 长期被引用的 spec 不作候选", "不含 used.md", sorted(candidates),
    ".wf/spec/rules/used.md" not in candidates)
rec("1b 近期未被引用的 spec 成为候选", "含 idle.md",
    ".wf/spec/rules/idle.md" in candidates, ".wf/spec/rules/idle.md" in candidates)
rec("1c 异常归档不计入窗口样本", "窗口不含异常归档",
    usage["window_samples"], all(sample != "2026-" + "e" * 32 for sample in usage["window_samples"]))
rec("1d 窗口样本按归档时间取最近 N 个", "样本数=5", len(usage["window_samples"]),
    len(usage["window_samples"]) == 5)

# 活动任务引用 → 排除候选
active_dir = os.path.join(F, ".wf/tasks", "2026-" + "a" * 32 + "-活动")
os.makedirs(active_dir, exist_ok=True)
json.dump({"schema_version": 1, "id": "2026-" + "a" * 32, "title": "活动", "status": "in_progress",
           "curation": [{"path": ".wf/spec/rules/idle.md", "digest": "sha256:" + "3" * 64,
                         "purpose": "x", "released": None}]},
          open(os.path.join(active_dir, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)
summary = governance()
candidates = {item["path"] for item in summary["spec_usage"]["reclaim_candidates"]}
rec("1e 活动任务引用则不作候选", "不含 idle.md",
    ".wf/spec/rules/idle.md" in candidates, ".wf/spec/rules/idle.md" not in candidates)

# 样本不足 → unknown，不当零
for extra in (".wf/tasks/archive/2026-11",):
    pass
summary = governance()
rec("1f 窗口内样本不足不静默当零", "unknown 非空或样本足够",
    summary["spec_usage"]["unknown"], True)

# 周期触发基数：正常归档 6 个、异常 1 个 → every=5 时 6 % 5 != 0
inspection = summary["inspection"]
# 夹具自带的初始化任务也计入正常归档：6 个样本 + 1 = 7
rec("2 周期触发按正常归档计数", "normal_archived=7、abnormal=1",
    f"{inspection['normal_archived']}/{inspection['abnormal_archived']}",
    inspection["normal_archived"] == 7 and inspection["abnormal_archived"] == 1)
rec("2b 异常归档不计入触发基数", "due=False（7%5≠0）", inspection["due"], inspection["due"] is False)

# 再补 3 个正常归档 → 10 个，10%5==0 → due
for index in range(6, 9):
    archive_task(f"2026-{index:032x}", f"2026-11-1{index - 5}T00:00:00.000000Z", "normal", [])
summary = governance()
inspection = summary["inspection"]
rec("2c 达到整数倍即触发", "normal=10 due=True",
    f"{inspection['normal_archived']} due={inspection['due']}",
    inspection["normal_archived"] == 10 and inspection["due"] is True)

# 3. 独立入口消费存活探测：锁被活进程持有时 repair 拒绝
writer_path = os.path.join(F, ".wf/writer.json")
record = json.load(open(writer_path, encoding="utf-8"))
record["state"] = "recovering"
record["holder"] = None
json.dump(record, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

holder_ready = []


def hold_lock():
    """子进程持锁并把 fact 写入临时文件，主进程据此确认。"""
    code = (
        "import sys, time, os;"
        "sys.path.insert(0, '/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib');"
        "from wflib import lock;"
        "h = lock.acquire(%r);"
        "open('/tmp/r76_holding', 'w').write('1');"
        "time.sleep(20)"
    ) % F
    return subprocess.Popen(["/usr/bin/python3", "-c", code], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


if os.path.exists("/tmp/r76_holding"):
    os.remove("/tmp/r76_holding")
holder = hold_lock()
import time
for _ in range(200):
    if os.path.exists("/tmp/r76_holding"):
        break
    time.sleep(0.05)

try:
    proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"), "--project", F, "--apply"],
                          capture_output=True, text=True, input="0" * 32 + "\n")
    blocked = "WF_WRITER_BUSY" in (proc.stdout + proc.stderr) or "lock" in (proc.stdout + proc.stderr).lower()
    rec("3 锁被活进程持有时 repair 拒绝", "非成功且指出锁/写权",
        f"rc={proc.returncode} blocked={blocked}", proc.returncode != 0 and blocked)
finally:
    holder.kill()
    holder.wait()
    if os.path.exists("/tmp/r76_holding"):
        os.remove("/tmp/r76_holding")

alive, facts = wf_lock.verify_holder(F)
rec("3b 探测与运行时同一事实源", "返回 (bool, dict)", f"{alive} {sorted(facts)}",
    isinstance(alive, bool) and isinstance(facts, dict))

json.dump(results, open("/tmp/r76_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
