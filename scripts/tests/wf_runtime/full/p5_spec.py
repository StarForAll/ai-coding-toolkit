#!/usr/bin/env python3
"""F1 专属：本地 spec 生命周期（新增/更新/合并/改名/删除 + 依赖解除 + 索引同步），全程无 MCP。"""
import hashlib, json, os, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
SID = "sess-G"
results = []


def rec(case, expected, actual, passed):
    results.append({"case": case, "expected": expected, "actual": actual, "pass": passed})
    print(f"[F1-spec] {case}: {'PASS' if passed else 'FAIL'} — {actual}")


def wf(args, inputs=None):
    return wfdrive.run(args, inputs=inputs, sid=SID, show=False)


rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "本地 spec 生命周期",
                     "--template", f"{F}/.wf/templates/task", "--json"])
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
if not task_id:
    print("task-new failed", payload); raise SystemExit(1)
directory = os.path.join(F, facts.get("directory", ""))
prd = '''# 本地 spec 生命周期

## 机读块

<!-- wf-plan:v1 -->
```json
{"schema_version": 1,
 "touch_paths": [".wf/spec/**", "src/**"],
 "acceptance": [{"id": "a1", "statement": "spec 增改并合改名删除与索引同步成立", "verification_ids": ["v1"]}],
 "verifications": [{"id": "v1", "invocation": {"kind": "argv",
   "argv": ["/usr/bin/python3", "-c", "import os; assert os.path.isfile('.wf/spec/index.md'); print('ok')"]},
   "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]}
```
'''
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
at = "2026-11-03T08:00:00.000000Z"
json.dump([{"source": "human (sess-G)", "at": at, "subject": "approve spec lifecycle",
            "object_digest": digest, "choice": "approve", "reason": "本地 spec 用例"}],
          open("/tmp/spec_approve.json", "w"), ensure_ascii=False)
inputs = {"generation": gen}
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision", "/tmp/spec_approve.json", "--json"], inputs)
rec("批准", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
rec("开工", "pass", (payload or {}).get("code"), rc == 0)

rule = '''---
schema_version: 1
paths: ["src/calc.py"]
status: "extracted"
verified_at: "extracted"
author: "ai"
counterexample: "未经人核实即当作已核实规则"
---

# calc 纯函数约定

## 约定

add 与 multiply 必须是纯函数，不读写全局状态。
'''
changes = [{"operation": "add", "new_paths": [".wf/spec/rules/calc.md"], "content": rule}]
json.dump(changes, open("/tmp/spec_add.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_add.json", "--json"], inputs)
rec("新增（extracted）", "pass", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["task-curate", "--task", task_id, "--spec", ".wf/spec/rules/calc.md",
                     "--purpose", "约束 calc 纯函数", "--json"], inputs)
rec("策展引用", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["spec", "--file", ".wf/spec/rules/calc.md", "--json"], inputs)
facts = (payload or {}).get("facts", {})
rec("读取正文并留痕", "complete=true 且写入本会话侧车",
    f"complete={facts.get('complete')} codepoints={facts.get('codepoints')}",
    facts.get("complete") is True and facts.get("sidecar", {}).get("written") is True)

rule2 = rule.replace('status: "extracted"', 'status: "active"').replace('verified_at: "extracted"',
                                                                   'verified_at: "2026-11-03"')
changes = [{"operation": "update", "new_paths": [".wf/spec/rules/calc.md"], "content": rule2,
            "before_digests": [facts.get("digest")]}]
json.dump(changes, open("/tmp/spec_update.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_update.json", "--json"], inputs)
rec("更新为 active（人核实日期）", "pass", (payload or {}).get("code"), rc == 0)

changes = [{"operation": "rename", "old_paths": [".wf/spec/rules/calc.md"],
            "new_paths": [".wf/spec/rules/pure.md"]}]
json.dump(changes, open("/tmp/spec_rename.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_rename.json", "--json"], inputs)
rec("改名（索引同步）", "pass 且 index 指向新路径",
    f"{(payload or {}).get('code')}",
    rc == 0 and "pure.md" in open(os.path.join(F, ".wf/spec/index.md"), encoding="utf-8").read())

changes = [{"operation": "delete", "old_paths": [".wf/spec/rules/pure.md"]}]
json.dump(changes, open("/tmp/spec_delete_bad.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_delete_bad.json", "--json"], inputs)
_exits = ((payload or {}).get("facts") or {}).get("exits") or []
rec("删除未解除依赖", "needs_decision WF_SEMANTIC_DECISION 且给出三个出口",
    f"{(payload or {}).get('code')} exit={rc} exits={len(_exits)}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2 and len(_exits) == 3)

release = [{"operation": "delete", "old_paths": [".wf/spec/rules/pure.md"],
           "reference_dispositions": [{"task_id": task_id, "path": ".wf/spec/rules/pure.md",
                                       "released": {"decision": {"source": "human (sess-G)",
                                                                 "at": "2026-11-04T00:00:00.000000Z",
                                                                 "subject": "release .wf/spec/rules/pure.md",
                                                                 "choice": "解除依赖",
                                                                 "reason": "本条规则将在本任务合并为通用约定"}},
                                       "replacement": ".wf/spec/rules/general.md"}]}]
json.dump(release, open("/tmp/spec_delete_ok.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_delete_ok.json", "--json"], inputs)
deleted = not os.path.exists(os.path.join(F, ".wf/spec/rules/pure.md"))
rec("解除依赖后删除", "pass 且文件移除、索引同步", f"{(payload or {}).get('code')} removed={deleted}",
    rc == 0 and deleted)

merged = rule2.replace("# calc 纯函数约定", "# calc 通用约定")
changes = [{"operation": "add", "new_paths": [".wf/spec/rules/general.md"], "content": merged}]
json.dump(changes, open("/tmp/spec_merge.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_merge.json", "--json"], inputs)
rec("合并写入目标文件", "pass", (payload or {}).get("code"), rc == 0)

# ---- 拆分：旧文件「停用并保留」分支（2026-11-05 补：B5 只覆盖过「原文件移除」） ----
def _split_part(title, body, base):
    head = base.split("## 约定")[0].replace("# calc 通用约定", f"# {title}")
    return head + "## 约定\n\n" + body + "\n"


combined = _split_part("calc 合并条目", "纯函数与副作用约定先合并登记，随后拆分。", merged)
changes = [{"operation": "add", "new_paths": [".wf/spec/rules/combined.md"], "content": combined}]
json.dump(changes, open("/tmp/spec_split_add.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_split_add.json", "--json"], inputs)
rec("拆分前置：建待拆分条目", "pass", (payload or {}).get("code"), rc == 0)

# 候选必须是规则 paths 的真实取值（规则 paths 是 src/calc.py，不是 src/**）；
# 先做 active 正对照，才能把「停用后不命中」与「本来就不匹配」区分开。
sys.path.insert(0, os.path.join(F, ".wf/lib"))
try:
    from wflib import spec as wf_spec
finally:
    sys.path.pop(0)
matched_before = [entry["path"] for entry in wf_spec.match(F, ["src/calc.py"])[0]]
rec("拆分前对照：active 条目可被 src/calc.py 命中", "命中 combined.md",
    f"matched={sorted(set(matched_before))}",
    any(path.endswith("combined.md") for path in matched_before))

split_pure = _split_part("calc 纯函数", "add 与 multiply 必须是纯函数，不读写全局状态。", merged)
split_side = _split_part("calc 副作用", "所有 I/O 必须显式注入，禁止隐式读环境变量。", merged)
changes = [
    {"operation": "add", "new_paths": [".wf/spec/rules/calc-pure.md"], "content": split_pure},
    {"operation": "add", "new_paths": [".wf/spec/rules/calc-side.md"], "content": split_side},
    {"operation": "disable", "old_paths": [".wf/spec/rules/combined.md"]},
]
json.dump(changes, open("/tmp/spec_split_disable.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", "/tmp/spec_split_disable.json", "--json"], inputs)
applied = len((payload or {}).get("facts", {}).get("applied") or [])
rec("拆分（停用旧文件并新建两条）", "pass 且 applied=3",
    f"{(payload or {}).get('code')} applied={applied}", rc == 0 and applied == 3)

combined_path = os.path.join(F, ".wf/spec/rules/combined.md")
combined_meta = wf_spec.parse_frontmatter(combined_path)[0] if os.path.exists(combined_path) else {}
rec("拆分后旧文件保留且 status=disabled", "文件存在且 frontmatter 的 status 为 disabled",
    f"exists={os.path.exists(combined_path)} status={combined_meta.get('status')!r}",
    os.path.exists(combined_path) and combined_meta.get("status") == "disabled")

index_text = open(os.path.join(F, ".wf/spec/index.md"), encoding="utf-8").read()
rec("拆分后索引同步（新条目入、旧条目出）", "含 calc-pure/calc-side，不含 combined",
    f"pure={'calc-pure.md' in index_text} side={'calc-side.md' in index_text} "
    f"combined={'combined.md' in index_text}",
    "calc-pure.md" in index_text and "calc-side.md" in index_text and "combined.md" not in index_text)

# 候选必须是规则 paths 的真实取值（规则 paths 是 src/calc.py，不是 src/**）；
# 同时给一个 active 正对照，否则「停用后不命中」无法与「本来就不匹配」区分。
matched_after = [entry["path"] for entry in wf_spec.match(F, ["src/calc.py"])[0]]
rec("停用条目不再作为规则被加载", "src/calc.py 命中 calc-pure/calc-side，不含 combined.md",
    f"matched={sorted(set(matched_after))}",
    any(path.endswith("calc-pure.md") for path in matched_after)
    and any(path.endswith("calc-side.md") for path in matched_after)
    and not any(path.endswith("combined.md") for path in matched_after))

json.dump({"standard": {"conclusion": "pass", "basis": "spec 变更逐项核对"},
           "requirement": {"conclusion": "pass", "basis": "a1 覆盖"}},
          open("/tmp/spec_notes.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/spec_notes.json", "--json"], inputs)
rec("Check pass（spec 变更已入检查对象）", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-knowledge", "--task", task_id, "--decision", "updated", "--json"], inputs)
rec("知识处置 updated", "pass", (payload or {}).get("code"), rc == 0)
json.dump([{"source": "human (sess-G)", "at": at, "subject": f"finish {task_id}", "object_digest": digest,
            "choice": "finish", "reason": "spec 生命周期用例完成"},
           {"source": "human (sess-G)", "at": at, "subject": ".wf/spec/**", "object_digest": digest,
            "choice": "commit", "reason": "授权提交 spec 变更"}],
          open("/tmp/spec_archive.json", "w"), ensure_ascii=False)
wf(["sampling", "pick", "--task", task_id, "--freeze", "--json"],
                       {"generation": gen})   # 归档前置：先冻结并落盘选样
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/spec_archive.json", "--json"], inputs)
rec("归档", "pass", (payload or {}).get("code"), rc == 0)
wf(["writer", "release", "--json"], inputs)
json.dump(results, open("/tmp/p5_spec_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results))
