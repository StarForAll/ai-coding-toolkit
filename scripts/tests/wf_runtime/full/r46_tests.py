#!/usr/bin/env python3
"""第十一轮 R46：单条非法路径只失效该条，整份规则仍参与门禁。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import spec as wf_spec

F = wfdrive.FIX
results = []
AT = "2026-11-04T08:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-S1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R46 用例"}


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
paths: {paths}
status: "active"
verified_at: "extracted"
author: "ai"
counterexample: "未核实用例"
---

# 规则

正文。
'''

NOTES = "/tmp/r46_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))


def make_task(title, touch, sid="sess-S1"):
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


# ---------------- 对照：只改一个路径项 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R46 对照", ["pkg/**", ".wf/spec/**"], "sess-S1")
json.dump([dec("approve", "approve", d1)], open("/tmp/r46_a.json", "w"))
wf(["task-approve", "--task", task1, "--decision", "/tmp/r46_a.json", "--json"],
   {"generation": gen1, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}},
   "sess-S1")
rc_s, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-S1")
rec("R46 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")

valid_rule = RULE.replace("{paths}", '["pkg/**"]')
rule_with_bad_entry = RULE.replace("{paths}", '["pkg/**", "../invalid/**"]')
# 先用「只有合法条目」建立对照：应阻断
open(os.path.join(F, ".wf/spec/rules/only-valid.md"), "w").write(valid_rule)
index_path = os.path.join(F, ".wf/spec/index.md")
text = open(index_path, encoding="utf-8").read()
if "only-valid.md" not in text:
    open(index_path, "w", encoding="utf-8").write(text + "- [only-valid.md](.wf/spec/rules/only-valid.md)\n")
rc, payload, _ = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"],
                    {"generation": write_gen()}, "sess-S1")
rec("R46 对照：合法条目命中即阻断", "WF_SPEC_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE")

# 只改一个路径项：加一条非法条目，仍应阻断（不能因为非法条目让整份规则逃出门禁）
os.remove(os.path.join(F, ".wf/spec/rules/only-valid.md"))
open(os.path.join(F, ".wf/spec/rules/with-bad-entry.md"), "w").write(rule_with_bad_entry)
text = open(index_path, encoding="utf-8").read().replace(
    "- [only-valid.md](.wf/spec/rules/only-valid.md)\n", "- [with-bad-entry.md](.wf/spec/rules/with-bad-entry.md)\n")
open(index_path, "w", encoding="utf-8").write(text)
rc, payload, _ = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"],
                    {"generation": write_gen()}, "sess-S1")
spec_facts = (((payload or {}).get("facts") or {}).get("spec") or {})
rec("R46 单条非法不放过合法条目", "WF_SPEC_INCOMPLETE 且 matched 含该规则",
    f"{(payload or {}).get('code')} matched={spec_facts.get('matched')}",
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE"
    and ".wf/spec/rules/with-bad-entry.md" in (spec_facts.get("matched") or []))
rec("R46 非法条目作为可见报告", "path_problems 列出该条",
    json.dumps(spec_facts.get("path_problems"), ensure_ascii=False)[:140],
    bool(spec_facts.get("path_problems"))
    and "invalid path entry" in (spec_facts["path_problems"][0].get("problems") or [""])[0])

# 元数据整体不可解析 → 整文件不可路由
broken = open(os.path.join(F, ".wf/spec/rules/with-bad-entry.md"), encoding="utf-8").read()
open(os.path.join(F, ".wf/spec/rules/with-bad-entry.md"), "w").write(broken.replace('status: "active"', 'status: "bogus"'))
matched, unparsed = wf_spec.match(F, ["pkg/a.py"])
rec("R46 元数据不可靠时整文件不可路由", "不进入 matched、列入 unparsed",
    f"matched={[item['path'] for item in matched]} unparsed={[item['path'] for item in unparsed]}",
    ".wf/spec/rules/with-bad-entry.md" not in [item["path"] for item in matched]
    and ".wf/spec/rules/with-bad-entry.md" in [item["path"] for item in unparsed])

json.dump(results, open("/tmp/r46_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
