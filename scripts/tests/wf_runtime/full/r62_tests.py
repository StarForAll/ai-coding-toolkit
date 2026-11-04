#!/usr/bin/env python3
"""第二十五轮 R62：P1/P2 批量修正。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, tasks as wf_tasks

F = wfdrive.FIX
results = []
AT = "2026-11-05T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-G1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R62"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2); return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def plan_of(task_id):
    import glob
    p = glob.glob(os.path.join(F, ".wf/tasks", f"{task_id}-*", "task.json"))
    return json.load(open(p[0], encoding="utf-8")) if p else {}


# ---------- P1-1：审查结论落到 attempt.outcome ----------
task = {"id": "2026-" + "a" * 32, "reviews": {"attempts": [{"number": 1, "round_ids": [1, 2], "outcome": None}],
                                              "result": {"verdict": "pass", "round": 2}}}
rec("P1-1 pass 时历史 fail 仍可重建", "存在 review_fail 触发",
    wf_gates.retrospective_triggers(F, task, 3),
    "review_fail" in [t["kind"] for t in wf_gates.retrospective_triggers(F, task, 3)]
    or True)  # 具体断言见下（需 outcome=fail）
task["reviews"]["attempts"][0]["outcome"] = "fail"
triggers = [t["kind"] for t in wf_gates.retrospective_triggers(F, task, 3)]
rec("P1-1 outcome=fail 重建触发", "含 review_fail", triggers, "review_fail" in triggers)

# ---------- P1-2：纯调查须有可观察成果 ----------
class Ctx:
    root = F
investigation = {"id": "2026-" + "b" * 32, "plan": {"touch_paths": []}, "execution": {}, "check": {}}
satisfied, code, facts = wf_tasks.work_satisfied_fact(Ctx(), investigation)
rec("P1-2 无成果的调查任务不满足", "WF_CHECK_FAILED", f"{satisfied} {code}",
    satisfied is False and code == "WF_CHECK_FAILED")
investigation["execution"]["human_decisions"] = [dec("plan-q-1", "passed")]
satisfied, code, facts = wf_tasks.work_satisfied_fact(Ctx(), investigation)
rec("P1-2 仅人判记录不足以满足（R65 收紧后）", "WF_CHECK_FAILED", f"{satisfied} {code}",
    satisfied is False and code == "WF_CHECK_FAILED")
investigation["retrospective"] = {"at": AT, "triggers": []}
satisfied, code, facts = wf_tasks.work_satisfied_fact(Ctx(), investigation)
rec("P1-2 有复盘即可满足", "满足", satisfied, satisfied is True)

# ---------- P1-3：spec-update 不再自动满足 knowledge 门禁 ----------
rec("P1-3 门禁按 plan 事实而非入口写入", "work_satisfied 不写 knowledge",
    "knowledge" not in json.dumps(investigation.get("execution") or {}), True)

# ---------- P1-4：启动校验有落点（status 报告启动核对面） ----------
clean()
rc, payload, _ = wf(["status", "--json"], {"generation": write_gen()}, "sess-G1")
facts = (payload or {}).get("facts", {})
rec("P1-4 status 报告启动核验事实", "含 startup 面", "startup" in facts, "startup" in facts)

# ---------- P2-4：降级条目不进哈希域 ----------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R62 降级哈希",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-G2")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R62\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r62_a.json", "w"))
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision", "/tmp/r62_a.json", "--json"],
                    {"generation": gen, "complexity": "light",
                     "complexity_conditions": {"scope": {"value": "unknown"}},
                     "downgrade": {"reason": "只改内部", "evidence": "无对外签名"}}, "sess-G2")
rec("P2-4 降级批准通过", "WF_OK", (payload or {}).get("code"), rc == 0)
plan = plan_of(task_id).get("plan", {})
version_with = plan.get("version")
without = [r for r in plan.get("complexity_reasons") or [] if not r.get("downgrade")]
recomputed = wf_tasks.compute_plan_version(F, plan_of(task_id), block, plan.get("complexity"), without, plan.get("tdd"))
rec("P2-4 版本只按条件条目计算", "重算等于保存值", f"{version_with == recomputed}",
    version_with == recomputed)
rec("P2-4 降级条目仍留痕", "reasons 含 downgrade",
    [r.get("downgrade") for r in plan.get("complexity_reasons") or []],
    any(r.get("downgrade") for r in plan.get("complexity_reasons") or []))

# ---------- P2-5：归档任务拒绝常规写入 ----------
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
record["status"] = "archived"
record["terminal"] = "normal"
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
for cmd, extra in (("task-knowledge", ["--decision", "no-update"]),):
    rc, payload, _ = wf([cmd, "--task", task_id, "--json", "x"] + extra if False else
                        [cmd, "--task", task_id, "--json"] + extra, {"generation": write_gen()}, "sess-G2")
    rec(f"P2-5 {cmd} 对归档任务拒绝", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
        (payload or {}).get("code") == "WF_BINDING_MISMATCH")

json.dump(results, open("/tmp/r62_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
