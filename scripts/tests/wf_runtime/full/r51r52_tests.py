#!/usr/bin/env python3
"""第十五轮 R51–R52 用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import spec as wf_spec

F = wfdrive.FIX
results = []
AT = "2026-11-04T12:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-W1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R51/R52 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def make_task(title, touch, sid="sess-W1"):
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


def approve(task_id, digest, gen, complexity="complex", sid="sess-W1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r51_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": complexity}, sid)


DESIGN = """# 设计

<!-- wf-plan:v1 -->

## 方案

选 A。
"""

IMPLEMENT = """# 执行

## 顺序

先 a 后 b。
"""

# ---------------- R51：复杂任务三件套 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R51 复杂产物", ["pkg/**", ".wf/spec/**"], "sess-W1")
rc, payload, _ = approve(task1, d1, gen1, "complex", "sess-W1")
rec("R51 缺 design/implement 不得批准", "WF_TEMPLATE_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")
artifacts = ((payload or {}).get("facts") or {}).get("artifacts") or []
rec("R51 报告缺失产物", "列出 design.md 与 implement.md",
    json.dumps(artifacts, ensure_ascii=False)[:120],
    sorted(item.get("artifact") for item in artifacts) == ["design.md", "implement.md"])
# 仅写模板占位
open(os.path.join(dir1, "design.md"), "w", encoding="utf-8").write(
    "# 设计\n\n{{WF_REQUIRED:approach}}\n\n<!-- wf-plan:v1 -->\n")
open(os.path.join(dir1, "implement.md"), "w", encoding="utf-8").write("# 执行\n\n{{WF_REQUIRED:order}}\n")
rc, payload, _ = approve(task1, d1, gen1, "complex", "sess-W1")
rec("R51 保留占位不得批准", "WF_TEMPLATE_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")
reasons = {item.get("reason") for item in (((payload or {}).get("facts") or {}).get("artifacts") or [])}
rec("R51 报告未填占位", "reason=unfilled placeholders", sorted(reasons), "unfilled placeholders" in reasons)
open(os.path.join(dir1, "design.md"), "w", encoding="utf-8").write(DESIGN)
open(os.path.join(dir1, "implement.md"), "w", encoding="utf-8").write(IMPLEMENT)
rc, payload, _ = approve(task1, d1, gen1, "complex", "sess-W1")
rec("R51 补齐后批准通过", "WF_OK", (payload or {}).get("code"), rc == 0)
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc, payload, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-W1")
rec("R51 开工复核通过", "WF_OK", (payload or {}).get("code"), rc == 0)
# 开工后把 implement 改回占位 → 回 Plan 再开工时被拒
open(os.path.join(dir1, "implement.md"), "w", encoding="utf-8").write("# 执行\n\n{{WF_REQUIRED:order}}\n")
clean()
wf(["task-pause", "--task", task1, "--reason", "R51", "--json"], {"generation": write_gen()}, "sess-W1")
wf(["task-resume", "--task", task1, "--json"], {"generation": write_gen()}, "sess-W1")
json.dump([dec("approve", "approve", d1)], open("/tmp/r51_re.json", "w"))
rc, payload, _ = wf(["task-approve", "--task", task1, "--decision", "/tmp/r51_re.json", "--json"],
                    {"generation": write_gen(), "complexity": "complex"}, "sess-W1")
wf(["task-pause", "--task", task1, "--reason", "R51 收尾", "--json"], {"generation": write_gen()}, "sess-W1")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-W1")

# ---------------- R52：disable 保留分隔符且可复验 ----------------
clean()
task2, gen2, dir2, d2 = make_task("R52 disable", ["pkg/**", ".wf/spec/**"], "sess-W2")
json.dump([dec("approve", "approve", d2)], open("/tmp/r52_a.json", "w"))
wf(["task-approve", "--task", task2, "--decision", "/tmp/r52_a.json", "--json"],
   {"generation": gen2, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-W2")
open(os.path.join(F, "pkg/b.py"), "w").write("b = 1\n")
wf(["task-start", "--task", task2, "--json"], {"generation": write_gen()}, "sess-W2")
rule = '''---
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
add = dfile("/tmp/r52_add.json", [{"operation": "add", "new_paths": [".wf/spec/rules/r52.md"], "content": rule}])
wf(["spec-update", "--task", task2, "--changes", add, "--json"], {"generation": write_gen()}, "sess-W2")
disable = dfile("/tmp/r52_dis.json", [{"operation": "disable", "old_paths": [".wf/spec/rules/r52.md"],
                                       "reference_dispositions": []}])
rc, payload, _ = wf(["spec-update", "--task", task2, "--changes", disable, "--json"],
                    {"generation": write_gen()}, "sess-W2")
rec("R52 disable 成功", "WF_OK", (payload or {}).get("code"), rc == 0)
text = open(os.path.join(F, ".wf/spec/rules/r52.md"), encoding="utf-8").read()
meta, problems = wf_spec.parse_frontmatter(os.path.join(F, ".wf/spec/rules/r52.md"))
rec("R52 结果仍可解析", "无 problems 且 status=disabled",
    f"problems={problems} status={meta.get('status')}",
    not problems and meta.get("status") == "disabled")
rec("R52 结束分隔符保留", "第二个 --- 存在", text.count("---") >= 2, text.count("---") >= 2)
wf(["task-pause", "--task", task2, "--reason", "R52 收尾", "--json"], {"generation": write_gen()}, "sess-W2")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-W2")

json.dump(results, open("/tmp/r51r52_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
