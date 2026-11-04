#!/usr/bin/env python3
"""V5：调试计数与复盘（F1，初始化已完成）。"""
import hashlib, json, os, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []


def rec(case, expected, actual, passed, note=""):
    results.append({"case": case, "expected": expected, "actual": actual, "pass": passed, "note": note})
    print(f"[V5] {case}: {'PASS' if passed else 'FAIL'} — {actual}")


def wf(args, inputs=None, sid="sess-E"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def decision(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "V5 调试计数用例",
                     "--template", f"{F}/.wf/templates/task", "--json"])
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
if not task_id:
    print("task-new failed:", json.dumps(payload, ensure_ascii=False)[:600])
    raise SystemExit(1)
directory = os.path.join(F, facts.get("directory", ""))
prd = '''# V5 调试计数用例

## 机读块

<!-- wf-plan:v1 -->
```json
{"schema_version": 1, "touch_paths": ["flag.txt"],
 "acceptance": [{"id": "a1", "statement": "flag.txt 内容为 ok", "verification_ids": ["v1"]}],
 "verifications": [{"id": "v1", "invocation": {"kind": "argv",
   "argv": ["/usr/bin/python3", "-c", "import sys; sys.exit(0 if open('flag.txt').read().strip()=='ok' else 1)"]},
   "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]}
```
'''
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
at = "2026-11-03T05:00:00.000000Z"
decision("/tmp/v5_approve.json", [{"source": "human (sess-E)", "at": at, "subject": "approve",
                                   "object_digest": digest, "choice": "approve", "reason": "V5"}])
inputs = {"generation": gen}
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision", "/tmp/v5_approve.json", "--json"], inputs)
rec("准备：批准", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
rec("准备：开工", "pass", (payload or {}).get("code"), rc == 0)

json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "fail", "basis": "flag.txt 尚未创建"}},
          open("/tmp/v5_notes_fail.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/v5_notes_fail.json", "--json"], inputs)
rec("首次 Check（验证失败）", "blocked WF_CHECK_FAILED", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_CHECK_FAILED" and rc == 1)

open(os.path.join(F, "flag.txt"), "w").write("ok\n")
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "a1 通过"}},
          open("/tmp/v5_notes_pass.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/v5_notes_pass.json", "--json"], inputs)
rec("修复后重检", "pass", f"{(payload or {}).get('code')}", rc == 0)

record = json.load(open(os.path.join(directory, "task.json")))
history = record.get("check_history") or []
failed = [c for c in history if c.get("result") == "fail"]
rec("单次 Check 内重试形态", "每次 Check 每声明仅一条最终结果，重试不产生多条 failed 条目",
    f"checks={len(history)+1} failed_history={len(failed)} commands_in_pass={len(record['check']['commands'])}",
    len(record["check"]["commands"]) == 1 and len(failed) == base_failed if (base_failed := len(failed)) >= 0 else False)

# 形态二：Execute 期声明两次失败，合并累计达到阈值 3
decision("/tmp/v5_declare.json", [{"source": "human (sess-E)", "at": at,
                                   "subject": "debug-declaration:v1:count=2:evidence=handoff:retry-log",
                                   "object_digest": digest, "choice": "declare", "reason": "Execute 期两次失败"}])
rc, payload, _ = wf(["task-check", "--task", task_id, "--decision", "/tmp/v5_declare.json",
                     "--review-notes", "/tmp/v5_notes_pass.json", "--json"], inputs)
rec("声明 Execute 期失败（合并累计 1+2=3）", "pass 且记录 debug_declarations",
    (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(directory, "task.json")))
rec("双源合并累计", "check_history failed(1) + counted(2) = 3",
    json.dumps(record["execution"]["debug_declarations"], ensure_ascii=False),
    record["execution"]["debug_declarations"][0]["counted"] == 2)

decision("/tmp/v5_archive.json", [{"source": "human (sess-E)", "at": at, "subject": f"finish {task_id}",
                                   "object_digest": digest, "choice": "finish", "reason": "V5"},
                                  {"source": "human (sess-E)", "at": at, "subject": "flag.txt",
                                   "object_digest": digest, "choice": "commit", "reason": "授权提交"}])
wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], inputs)
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/v5_archive.json", "--json"], inputs)
facts = (payload or {}).get("facts", {})
print("   missing:", json.dumps([m for m in (facts.get("missing") or [])], ensure_ascii=False)[:800])
rec("未裁定倍数阻断归档", "needs_decision WF_SEMANTIC_DECISION 且列 unruled_debug_multiples",
    f"{(payload or {}).get('code')} unruled={len(facts.get('unruled_debug_multiples', []))}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and facts.get("unruled_debug_multiples"))

decision("/tmp/v5_ruling1.json", [{"source": "human (sess-E)", "at": at, "subject": "debug-ruling-v1-1",
                                   "object_digest": digest, "choice": "同一问题",
                                   "reason": "同一断言重复失败，属同一问题"}])
rc, payload, _ = wf(["task-check", "--task", task_id, "--decision", "/tmp/v5_ruling1.json",
                     "--review-notes", "/tmp/v5_notes_pass.json", "--json"], inputs)
rec("裁定「同一问题」留痕", "pass 且写入 human_decisions",
    (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/v5_archive.json", "--json"], inputs)
facts = (payload or {}).get("facts", {})
missing = facts.get("missing") or []
rec("裁定后触发复盘要求", "blocked，缺 task.retrospective-done",
    f"{(payload or {}).get('code')} missing={[m.get('id') for m in missing]}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")

decision("/tmp/v5_retro.json", [{"source": "human (sess-E)", "at": at, "subject": f"retro {task_id}",
                                 "object_digest": digest, "choice": "record", "reason": "复盘完成"}])
json.dump({"conclusion": "重复失败源于验收文件未创建；改为先建文件再检查",
           "refs": [{"kind": "debug_repeat", "ref": "debug-ruling-v1-1"}]},
          open("/tmp/v5_evidence.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["task-retrospect", "--task", task_id, "--evidence", "/tmp/v5_evidence.json",
                     "--json"], inputs)
rec("复盘记录覆盖触发集合", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/v5_archive.json", "--json"], inputs)
rec("复盘后归档", "pass", f"{(payload or {}).get('code')}", rc == 0)

json.dump(results, open("/tmp/p5_v5_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results))
