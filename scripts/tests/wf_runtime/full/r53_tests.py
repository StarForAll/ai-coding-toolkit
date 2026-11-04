#!/usr/bin/env python3
"""第十六轮 R53：空产物与连字符标记。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, templates as wf_templates

F = wfdrive.FIX
results = []
AT = "2026-11-04T13:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-X1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R53 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    # cwd 必须指向夹具：缺省会落到调用者所在仓库，把空提交写进 authoring 仓库历史
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def make_task(title, touch, sid="sess-X1"):
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


def approve(task_id, digest, gen, sid="sess-X1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r53_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "complex"}, sid)


DESIGN_OK = "# 设计\n\n## 契约\n\n不改变对外签名。\n\n## 数据流\n\n入参直传。\n\n## 取舍\n\n不做缓存。\n"
IMPLEMENT_OK = "# 执行\n\n## 顺序\n\n先写测试再实现。\n"

# ---------------- 标记正则接受连字符 ----------------
fields = [field for field, _o in wf_templates.find_markers("{{WF_REQUIRED:data-flow}} {{WF_REQUIRED:non-goals}}")]
rec("R53 连字符字段可识别", ["data-flow", "non-goals"], fields, fields == ["data-flow", "non-goals"])
value_ok = not wf_templates.find_value_markers({"a": "nominal"}, "")
rec("R53 普通字符串不误判", "不报值占位", value_ok, value_ok)

# ---------------- 空产物被拒 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R53 空产物", ["pkg/**", ".wf/spec/**"], "sess-X1")
open(os.path.join(dir1, "design.md"), "w").write("")
open(os.path.join(dir1, "implement.md"), "w").write("")
rc, payload, _ = approve(task1, d1, gen1, "sess-X1")
rec("R53 两个空文件不得批准", "WF_TEMPLATE_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")
reasons = {item.get("reason") for item in (((payload or {}).get("facts") or {}).get("artifacts") or [])}
rec("R53 报告空产物", "reason=empty", sorted(reasons), "empty" in reasons)

# 只有标题行也算未填
open(os.path.join(dir1, "design.md"), "w").write("# 设计\n")
open(os.path.join(dir1, "implement.md"), "w").write("# 执行\n")
rc, payload, _ = approve(task1, d1, gen1, "sess-X1")
rec("R53 只有标题算空正文", "WF_TEMPLATE_INCOMPLETE 且 reason=empty body",
    f"{(payload or {}).get('code')} {sorted({i.get('reason') for i in (((payload or {}).get('facts') or {}).get('artifacts') or [])})}",
    (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE"
    and "empty body" in {i.get("reason") for i in (((payload or {}).get("facts") or {}).get("artifacts") or [])})

# 连字符占位被识别为未填
open(os.path.join(dir1, "design.md"), "w").write(
    "# 设计\n\n## 契约\n\n不变。\n\n## 数据流\n\n{{WF_REQUIRED:data-flow}}\n\n## 取舍\n\n无。\n")
open(os.path.join(dir1, "implement.md"), "w").write(IMPLEMENT_OK)
rc, payload, _ = approve(task1, d1, gen1, "sess-X1")
rec("R53 连字符占位不得批准", "WF_TEMPLATE_INCOMPLETE",
    f"{(payload or {}).get('code')}", (payload or {}).get("code") == "WF_TEMPLATE_INCOMPLETE")
fields_reported = [f for item in (((payload or {}).get("facts") or {}).get("artifacts") or [])
                   for f in (item.get("fields") or [])]
rec("R53 报告具体连字符字段", ["data-flow"], sorted(set(fields_reported)), "data-flow" in fields_reported)

# 补齐后通过（批准 + 开工）
open(os.path.join(dir1, "design.md"), "w").write(DESIGN_OK)
rc, payload, _ = approve(task1, d1, gen1, "sess-X1")
rec("R53 补齐后批准通过", "WF_OK", (payload or {}).get("code"), rc == 0)
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc, payload, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-X1")
rec("R53 补齐后开工通过", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-pause", "--task", task1, "--reason", "R53 收尾", "--json"], {"generation": write_gen()}, "sess-X1")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-X1")

json.dump(results, open("/tmp/r53_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
