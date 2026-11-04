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
status: extracted
verified_at: "extracted"
author: ai
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

rule2 = rule.replace('status: extracted', 'status: active').replace('verified_at: "extracted"',
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
rec("删除未解除依赖", "needs_decision WF_SEMANTIC_DECISION（给三个出口）",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)

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
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/spec_archive.json", "--json"], inputs)
rec("归档", "pass", (payload or {}).get("code"), rc == 0)
wf(["writer", "release", "--json"], inputs)
json.dump(results, open("/tmp/p5_spec_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results))
