#!/usr/bin/env python3
"""第十八轮 R55：批准决定的类型/对象/版本必须被消费。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-04T15:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Z1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R55 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)


def make_task(title, sid):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, choice="approve", sid="sess-Z1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r55_{task_id}_{choice}.json", [dec("approve", choice, digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


def plan_of(task_id):
    import glob
    p = glob.glob(os.path.join(F, ".wf/tasks", f"{task_id}-*", "task.json"))
    return json.load(open(p[0], encoding="utf-8")) if p else {}


# ① 正例：choice=approve 通过
clean()
task1, gen1, dir1, d1 = make_task("R55 approve", "sess-Z1")
rc, payload, _ = approve(task1, d1, gen1, "approve", "sess-Z1")
rec("R55 approve 决定被接受", "WF_OK", (payload or {}).get("code"), rc == 0)
rec("R55 approval.choice 落库为 approve", "approve", plan_of(task1).get("plan", {}).get("approval", {}).get("choice"),
    plan_of(task1).get("plan", {}).get("approval", {}).get("choice") == "approve")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc, payload, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Z1")
rec("R55 approve 后可开工", "WF_OK", (payload or {}).get("code"), rc == 0)
rec("R55 阶段进入 execute", "execute", plan_of(task1).get("phase"), plan_of(task1).get("phase") == "execute")
wf(["task-pause", "--task", task1, "--reason", "R55", "--json"], {"generation": write_gen()}, "sess-Z1")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Z1")

# ② 反例：只把 choice 换成 reject
clean()
task2, gen2, dir2, d2 = make_task("R55 reject", "sess-Z2")
rc, payload, _ = approve(task2, d2, gen2, "reject", "sess-Z2")
rec("R55 reject 决定不得批准", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
rc, payload, _ = wf(["task-start", "--task", task2, "--json"], {"generation": write_gen()}, "sess-Z2")
rec("R55 reject 后不得开工", "WF_APPROVAL_MISSING 或 WF_SEMANTIC_DECISION",
    (payload or {}).get("code"), (payload or {}).get("code") in ("WF_APPROVAL_MISSING", "WF_SEMANTIC_DECISION"))
wf(["task-pause", "--task", task2, "--reason", "R55", "--json"], {"generation": write_gen()}, "sess-Z2")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Z2")

# ③ 开工门禁复核：把已批准的 approval.choice 改成 reject
clean()
task3, gen3, dir3, d3 = make_task("R55 门禁复核", "sess-Z3")
approve(task3, d3, gen3, "approve", "sess-Z3")
rec_path = os.path.join(dir3, "task.json")
record = json.load(open(rec_path, encoding="utf-8"))
record["plan"]["approval"]["choice"] = "reject"
json.dump(record, open(rec_path, "w", encoding="utf-8"), ensure_ascii=False)
clean()
open(os.path.join(F, "pkg/c.py"), "w").write("c = 1\n")
rc, payload, _ = wf(["task-start", "--task", task3, "--json"], {"generation": write_gen()}, "sess-Z3")
rec("R55 门禁复核 approval.choice", "WF_APPROVAL_MISSING", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_APPROVAL_MISSING")
wf(["task-pause", "--task", task3, "--reason", "R55", "--json"], {"generation": write_gen()}, "sess-Z3")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Z3")

# ④ 对象不符：决定指向旧 PRD
clean()
task4, gen4, dir4, d4 = make_task("R55 对象", "sess-Z4")
rc, payload, _ = approve(task4, "sha256:" + "0" * 64, gen4, "approve", "sess-Z4")
rec("R55 对象摘要不符被拒", "WF_APPROVAL_MISSING", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_APPROVAL_MISSING")
wf(["task-pause", "--task", task4, "--reason", "R55", "--json"], {"generation": write_gen()}, "sess-Z4")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Z4")

json.dump(results, open("/tmp/r55_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
