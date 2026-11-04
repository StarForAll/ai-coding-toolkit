#!/usr/bin/env python3
"""第十七轮 R54：四项条件汇总后统一提议复杂度。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-04T14:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Y1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R54 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-Y1"):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, inputs_extra, sid="sess-Y1"):
    inputs = {"generation": gen}
    inputs.update(inputs_extra)
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r54_{task_id}.json", [dec("approve", "approve", digest)]), "--json"], inputs, sid)


def plan_of(task_id):
    import glob
    p = glob.glob(os.path.join(F, ".wf/tasks", f"{task_id}-*", "task.json"))
    return json.load(open(p[0], encoding="utf-8")) if p else {}


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)

# ① 仅 contract=true，不显式指定 complexity → 提议 complex，缺产物被拒
clean()
task1, gen1, dir1, d1 = make_task("R54 contract", ["pkg/**", ".wf/spec/**"], "sess-Y1")
rc, payload, _ = approve(task1, d1, gen1, {"complexity_conditions": {"contract": {"value": "true", "fact": "changes public API contract"}}})
rec("R54 contract=true 未指定分级 → 要求复杂产物", "WF_TEMPLATE_INCOMPLETE",
    (payload or {}).get("code"), (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")
rec("R54 报告按 complex 要求", "facts.complexity=complex",
    ((payload or {}).get("facts") or {}).get("complexity"),
    ((payload or {}).get("facts") or {}).get("complexity") == "complex")

# ② 补齐产物 → 通过且分级为 complex
open(os.path.join(dir1, "design.md"), "w").write("# 设计\n\n## 契约\n\n签名不变。\n")
open(os.path.join(dir1, "implement.md"), "w").write("# 执行\n\n先测试后实现。\n")
rc, payload, _ = approve(task1, d1, gen1, {"complexity_conditions": {"contract": {"value": "true", "fact": "changes public API contract"}}})
rec("R54 补齐后通过", "WF_OK", (payload or {}).get("code"), rc == 0)
plan = plan_of(task1)
rec("R54 分级落为 complex", "plan.complexity=complex", plan.get("plan", {}).get("complexity"),
    plan.get("plan", {}).get("complexity") == "complex")
conds = [r.get("condition") for r in plan.get("plan", {}).get("complexity_reasons") or []]
rec("R54 条件事实入库", "reasons 含 contract", conds, "contract" in conds)

# ③ 仅 scope 条件也复现同一行为（不只 contract 一条路径）
clean()
wf(["task-pause", "--task", task1, "--reason", "R54 收尾", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y1")
wf(["writer", "release", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y1")
task2, gen2, dir2, d2 = make_task("R54 scope", ["pkg/**"], "sess-Y2")
rc2, payload2, _ = approve(task2, d2, gen2, {"complexity_conditions": {"scope": {"value": "unknown", "fact": "范围可能扩张"}}}, "sess-Y2")
rec("R54 scope=unknown 同样要求产物", "WF_TEMPLATE_INCOMPLETE", (payload2 or {}).get("code"),
    (payload2 or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")

# ④ 条件为 true 但人工显式 light 且给理由证据 → 允许降级
rc, payload, _ = approve(task2, d2, gen2, {"complexity": "light", "complexity_conditions": {"scope": {"value": "unknown"}},
                                           "downgrade": {"reason": "只改一个内部函数", "evidence": "无对外签名变化"}}, "sess-Y2")
rec("R54 有理由可降级为 light", "WF_OK", (payload or {}).get("code"), rc == 0)
plan2 = plan_of(task2)
downgraded = [r for r in plan2.get("plan", {}).get("complexity_reasons") or [] if r.get("downgrade")]
rec("R54 降级留痕", "reasons 含 downgrade", bool(downgraded), bool(downgraded))

# ⑤ 条件 true 但显式 light 且无降级信息 → 拒绝
clean()
wf(["task-pause", "--task", task2, "--reason", "R54 收尾", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y2")
wf(["writer", "release", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y2")
task3, gen3, dir3, d3 = make_task("R54 无理由降级", ["pkg/**"], "sess-Y3")
rc, payload, _ = approve(task3, d3, gen3, {"complexity": "light",
                                           "complexity_conditions": {"contract": {"value": "true"}}}, "sess-Y3")
rec("R54 无理由降级被拒", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")

# ⑥ 无任何条件 → light，不要求产物
clean()
wf(["task-pause", "--task", task3, "--reason", "R54 收尾", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y3")
wf(["writer", "release", "--json"],
   {"generation": json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")}, "sess-Y3")
task4, gen4, dir4, d4 = make_task("R54 无条件", ["pkg/**"], "sess-Y4")
rc, payload, _ = approve(task4, d4, gen4, {}, "sess-Y4")
rec("R54 无条件为 light 且通过", "WF_OK 且 complex=light",
    f"{(payload or {}).get('code')} {plan_of(task4).get('plan', {}).get('complexity')}", rc == 0)

json.dump(results, open("/tmp/r54_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
