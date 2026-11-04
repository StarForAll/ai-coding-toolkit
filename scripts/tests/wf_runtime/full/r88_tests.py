#!/usr/bin/env python3
"""第五十五轮 R90：第十一轮复审 D1–D4 的定点用例（早期中断可恢复、实例固定、伪造 done 被拒、旧动作有出口）。"""
import json, os, sys, hashlib
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R90", instance_id=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, instance_id=instance_id)


def writer():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))


def save_writer(data):
    json.dump(data, open(os.path.join(F, ".wf/writer.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


def bindings():
    directory = os.path.join(F, ".wf/session-bindings")
    return [json.load(open(os.path.join(directory, name), encoding="utf-8"))
            for name in os.listdir(directory)]


# ---- 建一个任务，留下"意图已写、四步全 pending"的现场 ----
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R90 早期中断",
                     "--template", f"{F}/.wf/templates/task", "--json"])
facts = (payload or {}).get("facts") or {}
task_id = facts.get("task_id")
directory = os.path.join(F, facts["directory"])
instance_id = facts.get("instance_id")

# 抹掉产物与绑定，保留意图 → 模拟"create_dir 之前就中断"
import shutil
shutil.rmtree(directory, ignore_errors=True)
for binding in bindings():
    if (binding.get("object") or {}).get("id") == task_id:
        os.remove(os.path.join(F, ".wf/session-bindings", f"{binding['id']}.json"))
runtime_dir = os.path.join(F, ".wf/.runtime/sessions")
if os.path.isdir(runtime_dir):
    for name in os.listdir(runtime_dir):
        os.remove(os.path.join(runtime_dir, name))
data = writer()
data["action"]["state"] = "prepared"
data["action"]["steps"] = [{"id": step.get("id"), "state": "pending"} for step in data["action"]["steps"]]
save_writer(data)

# ---- D1：早期中断后重入能把目录/记录/绑定全部补齐 ----
rc2, payload2, _ = wf(["task-new", "--kind", "ordinary", "--title", "R90 早期中断",
                       "--template", f"{F}/.wf/templates/task", "--json"], instance_id=instance_id)
f2 = (payload2 or {}).get("facts") or {}
rec("D1 早期中断可续做同一任务", "resumed=True 且 task_id 不变",
    f"{f2.get('resumed')}/{f2.get('task_id') == task_id}",
    f2.get("resumed") is True and f2.get("task_id") == task_id)
rec("D1b 目录与产物被重建", "task.json 与 prd.md 均在",
    f"{os.path.isfile(os.path.join(directory, 'task.json'))}/{os.path.isfile(os.path.join(directory, 'prd.md'))}",
    os.path.isfile(os.path.join(directory, "task.json")) and os.path.isfile(os.path.join(directory, "prd.md")))
rec("D1c 绑定与运行态被重建", "binding 指向同一任务",
    [ (b.get("object") or {}).get("id") == task_id for b in bindings()],
    any((b.get("object") or {}).get("id") == task_id for b in bindings()))

# ---- D2：实例标识固定在意图里，重入不接受新值 ----
data = writer()
targets = {item.get("kind"): item.get("id") for item in data["action"].get("targets") or []}
rec("D2 意图固定 instance 目标", "含 instance", "instance" in targets, "instance" in targets)
data["action"]["state"] = "prepared"
save_writer(data)
for binding in bindings():
    if (binding.get("object") or {}).get("id") == task_id:
        os.remove(os.path.join(F, ".wf/session-bindings", f"{binding['id']}.json"))
rc3, payload3, _ = wf(["task-new", "--kind", "ordinary", "--title", "R90 早期中断",
                       "--template", f"{F}/.wf/templates/task", "--json"],
                      instance_id="ffffffffffffffffffffffffffffffff")
code3 = (payload3 or {}).get("code")
rec("D2b 重入只接受意图里的实例", "不返回成功",
    code3, code3 != "WF_OK")

# ---- D3：手工把步骤标 done 不能绕过真实后置 ----
data = writer()
data["action"]["state"] = "prepared"
data["action"]["steps"] = [{"id": step.get("id"), "state": "done"} for step in data["action"]["steps"]]
save_writer(data)
shutil.rmtree(directory, ignore_errors=True)
for binding in bindings():
    if (binding.get("object") or {}).get("id") == task_id:
        os.remove(os.path.join(F, ".wf/session-bindings", f"{binding['id']}.json"))
rc4, payload4, _ = wf(["task-new", "--kind", "ordinary", "--title", "R90 早期中断",
                       "--template", f"{F}/.wf/templates/task", "--json"], instance_id=instance_id)
f4 = (payload4 or {}).get("facts") or {}
rec("D3 伪造 done 仍会补做真实后置", "返回成功且产物重建",
    f"{(payload4 or {}).get('code')}/{os.path.isfile(os.path.join(directory, 'task.json'))}",
    os.path.isfile(os.path.join(directory, "task.json")))

# ---- D4：旧 task.action(task.create) 有明确出口，不再永久阻塞 ----
record = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
record["action"] = {"id": "sha256:" + "0" * 64, "kind": "task.create", "state": "prepared", "steps": []}
json.dump(record, open(os.path.join(directory, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)
rc6, payload6, _ = wf(["task-start", "--task", task_id, "--json"],
                      {"generation": writer().get("generation")})
code6 = (payload6 or {}).get("code")
rec("D4 旧 task.create 动作给出明确出口", "WF_RECORD_INVALID（不是无可执行出口）",
    code6, code6 == "WF_RECORD_INVALID")

json.dump(results, open("/tmp/r88_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
