#!/usr/bin/env python3
"""第五十四轮 R89：裁决 A 的落地——writer 单一父动作 + Finish 期受控回 check。"""
import json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []
NOTES = "/tmp/r87_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R89", instance_id=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, instance_id=instance_id)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


# ---- A：主记录是 writer 的单一父动作 ----
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R89",
                     "--template", f"{F}/.wf/templates/task", "--json"])
facts = (payload or {}).get("facts") or {}
task_id = facts.get("task_id")
writer = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
action = writer.get("action") or {}
steps = [step.get("id") if isinstance(step, dict) else step for step in action.get("steps") or []]
rec("A1 主记录为 writer 的 task.create", "writer.action.kind=task.create",
    action.get("kind"), action.get("kind") == "task.create")
rec("A2 四步全部结案", "steps done + state done",
    f"{steps}/{action.get('state')}",
    steps == ["create_dir", "write_record", "acquire_writer", "bind"] and action.get("state") == "done")
targets = {item.get("kind") for item in action.get("targets") or [] if isinstance(item, dict)}
rec("A3 目标固定（writer/task/binding/runtime）", "四类齐全", sorted(targets),
    {"writer", "task", "binding", "runtime"} <= targets)
task_record = json.load(open(os.path.join(F, facts["directory"], "task.json"), encoding="utf-8"))
rec("A4 任务记录不再承载创建动作", "task.action 为空",
    task_record.get("action"), not task_record.get("action"))
binding = json.load(open(os.path.join(F, ".wf/session-bindings",
                                      os.listdir(os.path.join(F, ".wf/session-bindings"))[0]),
                         encoding="utf-8"))
rec("A5 绑定与运行态齐备", "binding 有 instance_id 且运行态存在",
    bool(binding.get("instance_id")),
    bool(binding.get("instance_id")) and os.path.isfile(os.path.join(
        F, ".wf/.runtime/sessions", os.path.basename(
            os.path.join(F, ".wf/session-bindings")) and
        os.listdir(os.path.join(F, ".wf/session-bindings"))[0])))

# ---- 中断恢复：父动作退回未结案后重入续做同一任务 ----
writer = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
writer["bind_steps_backup"] = [step.get("id") for step in writer["action"]["steps"]]
writer["action"]["state"] = "prepared"
writer["action"]["steps"] = [{"id": step.get("id"), "state": "pending"} for step in writer["action"]["steps"]]
json.dump(writer, open(os.path.join(F, ".wf/writer.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
inst = binding.get("instance_id")
rc2, payload2, _ = wf(["task-new", "--kind", "ordinary", "--title", "R89",
                       "--template", f"{F}/.wf/templates/task", "--json"], instance_id=inst)
f2 = (payload2 or {}).get("facts") or {}
rec("A6 重入按原意图续做同一任务", "resumed=True 且 task_id 不变",
    f"{f2.get('resumed')}/{f2.get('task_id') == task_id}",
    f2.get("resumed") is True and f2.get("task_id") == task_id)
writer = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
rec("A7 续做后动作结案", "state=done", writer["action"].get("state"),
    writer["action"].get("state") == "done")

# ---- B：Finish 期变更受控回 check ----
# 复审指出：B 段缺项目配置会让 task-start 直接 WF_CAPABILITY_UNAVAILABLE
config_path = os.path.join(F, ".wf/project-config.json")
if not os.path.isfile(config_path):
    json.dump({"schema_version": 1}, open(config_path, "w"), ensure_ascii=False, indent=2)
prd = f"{F}/{facts['directory']}/prd.md"
block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
open(prd, "w").write("# R89\n\n<!-- wf-plan:v1 -->\n```json\n" + json.dumps(block, ensure_ascii=False, indent=2) + "\n```\n")
import hashlib
digest = "sha256:" + hashlib.sha256(open(prd, "rb").read()).hexdigest()
json.dump([{"source": "human", "at": "2026-11-04T00:00:00.000000Z", "subject": "approve",
            "object_digest": digest, "choice": "approve", "reason": "r89"}],
          open("/tmp/r89_approve.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r89_approve.json", "--json"],
   {"generation": gen(), "complexity": "light", "downgrade": {"reason": "x", "evidence": "y"}})
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
open(os.path.join(F, "pkg/r89.py"), "w").write("x=1\n")
wf(["task-start", "--task", task_id, "--json"], {"generation": gen()})
json.dump([{"source": "human", "at": "2026-11-04T00:00:00.000000Z", "subject": "external-changes",
            "object_digest": "sha256:" + "0" * 64, "choice": "已核对无影响", "reason": "夹具"}],
          open("/tmp/r89_ext.json", "w"))
wf(["task-check", "--task", task_id, "--review-notes", NOTES, "--decision", "/tmp/r89_ext.json", "--json"],
   {"generation": gen()})
wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], {"generation": gen()})
# 推进到 finish：需要 finish 决定（用 archive 的 finish 分支之前先看 phase）
record = json.load(open(os.path.join(F, facts["directory"], "task.json"), encoding="utf-8"))
rec("B0 检查已通过", "pass", (record.get("check") or {}).get("result"),
    (record.get("check") or {}).get("result") == "pass")


# ---- B：finish 期 spec 变更 → 受控回 check ----
# 先归档前把 phase 推到 finish：用 task-knowledge 后的 archive 前置手工推进不可行，
# 这里直接改记录模拟"进入 finish 后发现问题"的现场（仅测迁移语义）
record = json.load(open(os.path.join(F, facts["directory"], "task.json"), encoding="utf-8"))
record["phase"] = "finish"
json.dump(record, open(os.path.join(F, facts["directory"], "task.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/r89.md"), "w").write('# r89\n')
changes = "/tmp/r89_changes.json"
json.dump([{"operation": "add", "new_paths": [".wf/spec/rules/r89b.md"], "content": "# r89b\n"}],
          open(changes, "w"), ensure_ascii=False)
rc_b, payload_b, _ = wf(["spec-update", "--task", task_id, "--changes", changes, "--json"],
                        {"generation": gen()})
fb = (payload_b or {}).get("facts") or {}
rec("B1 finish 期变更回 check", "reentered_check=True 且 phase=check",
    f"{fb.get('reentered_check')}/{fb.get('phase')}",
    fb.get("reentered_check") is True and fb.get("phase") == "check")
record = json.load(open(os.path.join(F, facts["directory"], "task.json"), encoding="utf-8"))
invalidated = (record.get("check") or {}).get("invalidated") or {}
rec("B2 旧检查保留并登记失效", "invalidated 有 at/by",
    sorted(invalidated), {"at", "by"} <= set(invalidated))
valid, code, _f = __import__("wflib.gates", fromlist=["x"]).verify_step(
    type("C", (), {"root": F, "rule_version": lambda self: "sha256:" + "0" * 64})(), record, "task.check-passed")
rec("B3 失效的旧检查不再通过门禁", "WF_CHECK_STALE", code, code == "WF_CHECK_STALE")

json.dump(results, open("/tmp/r87_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

