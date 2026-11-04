#!/usr/bin/env python3
"""第十轮 R43–R45 用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, cli as wf_cli, gates as wf_gates

F = wfdrive.FIX
results = []
AT = "2026-11-04T06:30:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual if False else expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R43-R45 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


RULE = '''---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "2026-11-04"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''


def make_task(title, touch, sid):
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


def approve(task_id, digest, gen, sid):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r43_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/r43_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- R43：Check 后新增命中规则使旧 Check 失效 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R43 新增规则", ["pkg/**"], "sess-R1")
approve(task1, d1, gen1, "sess-R1")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc_s, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-R1")
rec("R43 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)
rc, payload, _ = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"], {"generation": write_gen()}, "sess-R1")
rec("R43 准备：Check 通过", "WF_OK", (payload or {}).get("code"), rc == 0)
anchor_before = ((payload or {}).get("facts") or {}).get("anchor") or {}
# 另一提交新增命中 pkg/** 的规则（不触碰交付文件）
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/new.md"), "w").write(RULE)
records = os.path.join(F, ".wf/spec/index.md")
text = open(records, encoding="utf-8").read()
if "new.md" not in text:
    open(records, "w", encoding="utf-8").write(text + "- [new.md](.wf/spec/rules/new.md)\n")
clean()
task_like = wf_tasks.load_task(F, task1)
saved_rule = (task_like.get("check") or {}).get("anchor", {}).get("rule_version")
satisfied, code, facts = wf_gates.verify_step(
    type("C", (), {"root": F, "rule_version": lambda self: saved_rule})(), task_like, "task.check-passed")
rec("R43 新增命中规则后旧 Check 失效", "WF_CHECK_STALE",
    f"ok={satisfied} code={code}", satisfied is False and code == "WF_CHECK_STALE")
rec("R43 报告新旧锚点差异", "facts 含 saved/current",
    json.dumps(facts, ensure_ascii=False)[:120], "saved" in facts and "current" in facts)

# ---------------- R44：归属优先于 glob 重叠 ----------------
wf(["task-pause", "--task", task1, "--reason", "R43 收尾", "--json"], {"generation": write_gen()}, "sess-R1")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-R1")
clean()
os.makedirs(os.path.join(F, "src"), exist_ok=True)
# 先建重叠任务 B（无自身 WIP），再让 A 产生并保存 WIP
task_b, gen_b, dir_b, d_b = make_task("R44 B 重叠", ["src/**"], "sess-RB")
rec("R44 准备：B 创建", "创建成功", (task_b or "")[:14], bool(task_b))
wf(["task-pause", "--task", task_b, "--reason", "让位", "--json"], {"generation": write_gen()}, "sess-RB")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-RB")
clean()
task_a, gen_a, dir_a, d_a = make_task("R44 A 保留", ["src/**"], "sess-RA")
approve(task_a, d_a, gen_a, "sess-RA")
open(os.path.join(F, "src/a.py"), "w").write("a\n")
rc_sa, start_a, _ = wf(["task-start", "--task", task_a, "--json"], {"generation": write_gen()}, "sess-RA")
rec("R44 准备：A 开工", "WF_OK",
    f"{(start_a or {}).get('code')} facts={json.dumps((start_a or {}).get('facts'), ensure_ascii=False)[:220]}", rc_sa == 0)
keep_a = dfile("/tmp/r44_keep.json", [dec("src/a.py", "keep", d_a)])
rc, payload, _ = wf(["stop", "--decision", keep_a, "--json"], {"generation": write_gen()}, "sess-RA")
rec("R44 准备：A 保存 WIP 归属", "WF_OK", (payload or {}).get("code"), rc == 0)
blockers = wf_cli.wip_blockers(F, exclude_id=task_a)
rec("R44 A 的接续条件不把文件算给 B", "B 不在列或 B 无该路径",
    json.dumps(blockers, ensure_ascii=False)[:180],
    all(item.get("task") != task_b or "src/a.py" not in (item.get("paths") or [])
        for item in blockers))
blockers_a = [item for item in wf_cli.wip_blockers(F) if item.get("task") == task_a]
rec("R44 显式归属仍计入 A", "A 被列为 WIP 持有者",
    json.dumps(blockers_a, ensure_ascii=False)[:120],
    bool(blockers_a) and "src/a.py" in (blockers_a[0].get("paths") or []))
clean()

# ---------------- R45：已提交的删除视为已处置 ----------------
clean()
task_d, gen_d, dir_d, d_d = make_task("R45 删除", ["del/**"], "sess-RD")
approve(task_d, d_d, gen_d, "sess-RD")
os.makedirs(os.path.join(F, "del"), exist_ok=True)
open(os.path.join(F, "del/gone.txt"), "w").write("gone\n")
clean()
rc_sd, start_d, _ = wf(["task-start", "--task", task_d, "--json"], {"generation": write_gen()}, "sess-RD")
rec("R45 准备：开工", "WF_OK", (start_d or {}).get("code"), rc_sd == 0)
os.remove(os.path.join(F, "del/gone.txt"))
keep_d = dfile("/tmp/r45_keep.json", [dec("del/gone.txt", "keep", d_d)])
rc, payload, _ = wf(["stop", "--decision", keep_d, "--json"], {"generation": write_gen()}, "sess-RD")
rec("R45 准备：删除态保留 WIP", "WF_OK", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["bind", "--task", task_d, "--json"], {"generation": write_gen()}, "sess-RD2")
rec("R45 准备：接续取得写权", "WF_OK", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-resume", "--task", task_d, "--json"], {"generation": write_gen()}, "sess-RD2")
rec("R45 未提交删除可恢复", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-pause", "--task", task_d, "--reason", "R45", "--json"], {"generation": write_gen()}, "sess-RD2")
clean()
rec("R45 准备：写权仍在接续会话", "held", json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("state"),
    json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("state") == "held")
rc, payload, _ = wf(["task-resume", "--task", task_d, "--json"], {"generation": write_gen()}, "sess-RD2")
rec("R45 删除已提交后仍可恢复", "WF_OK", (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(dir_d, "task.json")))
resolved = (record.get("handoff") or {}).get("wip", {}).get("resolved")
rec("R45 写回解除结论", "resolved.choice=resume-after-disposal",
    json.dumps(resolved, ensure_ascii=False)[:100] if resolved else None,
    bool(resolved) and resolved.get("choice") == "resume-after-disposal")

json.dump(results, open("/tmp/r43r45_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
