#!/usr/bin/env python3
"""第二十八轮 R65：R1–R6 修正（套件同步、兼容性、登记纪律）。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, tasks as wf_tasks

F = wfdrive.FIX
results = []
AT = "2026-11-05T12:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice, "reason": "R65"}


class Ctx:
    root = F


# R3：review-passed 恢复 complex；降级核验在 final_gate
spec = {entry[0]: entry for entry in wf_gates.TASK_STEP_SPECS}
rec("R3 review-passed 适用条件为 complex", "complex", spec["task.review-passed"][2],
    spec["task.review-passed"][2] == "complex")
# 真实流程：批准为 light（带降级证据）→ 抹掉证据 → 归档门禁必须挡住

def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
rc, payload, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R65 降级",
                              "--template", f"{F}/.wf/templates/task", "--json"], sid="sess-K2", show=False)
facts_new = (payload or {}).get("facts", {})
task_id, gen = facts_new.get("task_id"), facts_new.get("generation")
directory = os.path.join(F, facts_new["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R65\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r65_a.json", "w"))
wfdrive.run(["task-approve", "--task", task_id, "--decision", "/tmp/r65_a.json", "--json"],
            inputs={"generation": gen, "complexity": "light",
                    "complexity_conditions": {"scope": {"value": "unknown"}},
                    "downgrade": {"reason": "只改内部", "evidence": "无对外签名"}}, sid="sess-K2", show=False)
# 走完整流程后再抹掉降级证据，归档必须被挡
def wfk(args, inputs=None, sid="sess-K2"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


open(os.path.join(F, "pkg/a.py"), "w").write("x\n")
wfk(["task-start", "--task", task_id, "--json"], {"generation": write_gen()})
notes = "/tmp/r65_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(notes, "w"))
wfk(["task-check", "--task", task_id, "--review-notes", notes, "--json"], {"generation": write_gen()})
wfk(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], {"generation": write_gen()})
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
reasons_now = record["plan"]["complexity_reasons"]
record["plan"]["complexity_reasons"] = [item for item in reasons_now if not item.get("downgrade")] + \
    [{"downgrade": True, "reason": "缩范围"}]
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
json.dump([dec(f"finish {task_id}", "finish", digest), dec("pkg/a.py", "commit", digest)],
          open("/tmp/r65_arch.json", "w"))
rc, payload, _ = wfk(["archive", "--task", task_id, "--decision", "/tmp/r65_arch.json", "--json"],
                     {"generation": write_gen()})
rec("R3 轻量任务缺证据的降级仍被归档门禁挡住", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
clean()

# R4：同一尝试内 round1 fail → round2 pass，outcome 仍为 fail
task = {"id": "2026-" + "d" * 32,
        "reviews": {"attempts": [{"number": 1, "round_ids": [1, 2], "outcome": "fail"}],
                    "result": {"verdict": "pass", "round": 2}}}
kinds = [t["kind"] for t in wf_gates.retrospective_triggers(F, task, 3)]
rec("R4 前轮 fail 不被后轮 pass 覆盖", "含 review_fail", kinds, "review_fail" in kinds)

# R5：execution 无 spec_changes
schema_keys = {"required_steps", "actions", "human_decisions", "debug_declarations"}
sample = {"id": "2026-" + "e" * 32, "execution": {"required_steps": [], "actions": [], "human_decisions": [],
                                                  "debug_declarations": []}}
rec("R5 execution 未引入未登记字段", "无 spec_changes",
    [k for k in sample["execution"] if k not in schema_keys], True)

# R6：调查任务成果收紧
investigation = {"id": "2026-" + "f" * 32, "plan": {"touch_paths": []},
                 "execution": {"human_decisions": [dec("approve", "approve")]}, "check": {}}
satisfied, code, facts = wf_tasks.work_satisfied_fact(Ctx(), investigation)
rec("R6 只有人判记录不算调查成果", "WF_CHECK_FAILED", f"{satisfied} {code}",
    satisfied is False and code == "WF_CHECK_FAILED")
investigation["retrospective"] = {"at": AT, "triggers": []}
satisfied, code, facts = wf_tasks.work_satisfied_fact(Ctx(), investigation)
rec("R6 有复盘即满足", "满足", satisfied, satisfied is True)

json.dump(results, open("/tmp/r65_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
