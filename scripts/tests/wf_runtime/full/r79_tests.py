#!/usr/bin/env python3
"""第四十四轮 R79：E 复审缺陷的定点用例（哈希公式、Check 结构、处置事实、裁定精确匹配、脱敏）。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, records, check as wf_check, writer as wf_writer, tasks as wf_tasks

F = wfdrive.FIX
results = []
AT = "2026-11-04T11:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


# ---- D01：内容类锚点 = H(domain, C(P)) ----
P = {"plan_version": "sha256:" + "a" * 64, "content_digest": "sha256:" + "b" * 64}
content = wf_gates.step_anchor(None, P, False)
rec("D01 内容类锚点不额外包一层", records.H("wf-step-anchor-v1", P), content,
    content == records.H("wf-step-anchor-v1", P))
rec("D01b 与旧形状不同", "different", content == records.H("wf-step-anchor-v1", {"P": P}),
    content != records.H("wf-step-anchor-v1", {"P": P}))
rule = wf_gates.step_anchor("sha256:" + "c" * 64, P, True)
rec("D01c 规则类仍含 rule_version", records.H("wf-step-anchor-v1",
                                              {"rule_version": "sha256:" + "c" * 64, "P": P}), rule,
    rule == records.H("wf-step-anchor-v1", {"rule_version": "sha256:" + "c" * 64, "P": P}))

# ---- D02：Check 门禁结构复核 ----
healthy = {"check": {"result": "pass", "anchor": {"rule_version": "sha256:" + "d" * 64},
                     "commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0,
                                   "ended_at": AT,
                                   "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]}}],
                     "acceptance_results": [{"acceptance_id": "a1", "conclusion": "passed"}],
                     "internal_review": {"standard": {"conclusion": "pass", "basis": "b"},
                                         "requirement": {"conclusion": "pass", "basis": "b"}}},
           "plan": {"verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]}}],
                    "acceptance": [{"id": "a1"}]}}
rec("D02 结构齐全时无问题", "[]", wf_gates.check_result_problems(healthy),
    wf_gates.check_result_problems(healthy) == [])


def broken(**over):
    task = json.loads(json.dumps(healthy))
    task["check"].update(over)
    return wf_gates.check_result_problems(task)


for label, over in (
    ("缺 rule_version", {"anchor": {}}),
    ("缺 commands", {"commands": []}),
    ("命令未通过", {"commands": [{"verification_id": "v1", "status": "failed", "exit_code": 0,
                                 "ended_at": AT,
                                 "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]}}]}),
    ("缺验收结果", {"acceptance_results": []}),
    ("内部双轴缺一", {"internal_review": {"standard": {"conclusion": "pass", "basis": "b"}}}),
):
    problems = broken(**over)
    rec(f"D02 {label} → 阻断", "问题非空", [item["field"] for item in problems][:2], bool(problems))

task_missing_command = json.loads(json.dumps(healthy))
task_missing_command["plan"]["verifications"] = [{"id": "v1"}, {"id": "v2"}]
rec("D02 声明验证未执行 → 阻断", "commands",
    [item.get("field") for item in wf_gates.check_result_problems(task_missing_command)][:1],
    any(item.get("field") == "commands" for item in wf_gates.check_result_problems(task_missing_command)))

# ---- D03：处置结案需事实可核 ----
receipt = {"operation": "op-x", "head_before": None,
           "changes": [{"path": "pkg/a.py", "before": None, "after": None}],
           "result": "applied_pending_commit",
           "disposition": {"decision": {"choice": "commit", "subject": "x"},
                           "kind": "commit", "evidence": {"commit": "0" * 40},
                           "target_task": None}}
record = {"maintenance_results": [dict(receipt)]}
no_probe = wf_writer.receipt_state(record)
rec("D03 无探测时不得结案", "pending_check", no_probe[0]["state"], no_probe[0]["state"] == "pending_check")
bad_fact = wf_writer.receipt_state(record, disposition_probe=lambda entry: False)
rec("D03 事实不成立不得结案", "pending_check", bad_fact[0]["state"], bad_fact[0]["state"] == "pending_check")
good_fact = wf_writer.receipt_state(record, disposition_probe=lambda entry: True)
rec("D03 事实成立才结案", "disposed", good_fact[0]["state"], good_fact[0]["state"] == "disposed")

probe = wf_tasks.maintenance_disposition_probe(F)
fake_transfer = {"changes": [{"path": "pkg/a.py"}],
                 "disposition": {"kind": "transfer", "target_task": "2026-" + "f" * 32, "evidence": {"x": 1}}}
rec("D03 承接任务不存在 → 不结案", "False", probe(fake_transfer), probe(fake_transfer) is False)

# ---- D04：裁定精确匹配 ----
def rulings_task(count, multiples):
    # 每条 check_history 需带 result=fail 才计入「双源合并」的基数
    history = [{"id": f"c{index}", "result": "fail",
                "commands": [{"verification_id": "v-1", "status": "failed"}]}
               for index in range(count)]
    decisions = [{"subject": f"debug-ruling-v-1-{m}", "choice": "同一问题"} for m in multiples]
    return {"check_history": history, "execution": {"human_decisions": decisions}}


info = wf_gates.debug_pending(rulings_task(30, [10]), 3)
pendings = [item["multiple"] for item in info["pending"]]
rec("D04 第 1 倍不被第 10 倍覆盖", "1 在待裁定列表", pendings[:3], 1 in pendings)
rec("D04b 已裁定的第 10 倍不重复", "10 不在待裁定列表", 10 in pendings, 10 not in pendings)

# ---- D07：脱敏覆盖 Bearer 与分离参数 ----
secret = "sentinel-value-12345"
masked = wf_check.redact_secrets(f"Authorization: Bearer {secret}")
rec("D07 标准 Bearer 被遮罩", "不含明文", masked, secret not in masked)
argv = wf_check.redact_argv(["/usr/bin/python3", "tool", "--token", secret, "plain"])
rec("D07b 分离参数被遮罩", "不含明文", argv, secret not in json.dumps(argv))

json.dump(results, open("/tmp/r79_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
