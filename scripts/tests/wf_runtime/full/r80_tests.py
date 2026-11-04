#!/usr/bin/env python3
"""第四十五轮 R80：第二轮独立复审（D02/D03/D04/D05/D07）的定点反例。"""
import json, os, re, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import check as wf_check, gates as wf_gates, tasks as wf_tasks, writer as wf_writer

F = wfdrive.FIX
results = []
AT = "2026-11-04T12:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


ARGV = {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]}


def task(verifications=None, acceptance=None):
    return {"plan": {"verifications": verifications if verifications is not None else
                     [{"id": "v1", "required": True, "invocation": ARGV}],
                     "acceptance": acceptance if acceptance is not None else [{"id": "a1"}]}}


def check(**over):
    base = {"result": "pass", "anchor": {"rule_version": "sha256:" + "d" * 64},
            "commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0, "ended_at": AT,
                          "invocation": ARGV}],
            "acceptance_results": [{"acceptance_id": "a1", "conclusion": "passed"}],
            "internal_review": {"standard": {"conclusion": "pass", "basis": "b"},
                                "requirement": {"conclusion": "pass", "basis": "b"}}}
    base.update(over)
    return base


def validate(over, task_over=None):
    t = task(**(task_over or {}))
    return wf_check.validate_check_result(t, check(**over))


# ---- D02：结构复核 ----
rec("D02 齐全时通过", "[]", validate({}), validate({}) == [])

failed_acceptance = validate({"acceptance_results": [{"acceptance_id": "a1", "conclusion": "failed"}]})
rec("D02 验收未通过被拒", "非空", [p.get("field") for p in failed_acceptance][:2], bool(failed_acceptance))

wrong_argv = dict(ARGV, argv=["/usr/bin/python3", "-c", "print(2)"])
wrong_command = validate({"commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0,
                                        "ended_at": AT, "invocation": wrong_argv}]})
rec("D02 调用被替换被拒", "invocation", [p.get("field") for p in wrong_command][:1],
    any("invocation" in (p.get("field") or "") for p in wrong_command))

bad_exit = validate({"commands": [{"verification_id": "v1", "status": "passed", "exit_code": 7,
                                   "ended_at": AT, "invocation": ARGV}]})
rec("D02 非零退出被拒", "exit_code", [p.get("field") for p in bad_exit][:1],
    any("exit_code" in (p.get("field") or "") for p in bad_exit))

no_end = validate({"commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0,
                                 "ended_at": None, "invocation": ARGV}]})
rec("D02 缺结束时间被拒", "ended_at", [p.get("field") for p in no_end][:1],
    any("ended_at" in (p.get("field") or "") for p in no_end))

duplicate = validate({"commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0,
                                    "ended_at": AT, "invocation": ARGV}] * 2})
rec("D02 重复结果被拒", "duplicate", [p.get("reason") for p in duplicate][:2],
    any("duplicate" in (p.get("reason") or "") for p in duplicate))

unknown_id = validate({"commands": [{"verification_id": "ghost", "status": "passed", "exit_code": 0,
                                     "ended_at": AT, "invocation": ARGV}]})
rec("D02 未知 verification 被拒", "unknown",
    [p.get("reason") for p in unknown_id][:1],
    any("unknown verification_id" in (p.get("reason") or "") for p in unknown_id))

optional = validate({"commands": [{"verification_id": "v1", "status": "passed", "exit_code": 0,
                                   "ended_at": AT, "invocation": ARGV}]},
                    {"verifications": [{"id": "v1", "required": True, "invocation": ARGV},
                                       {"id": "v2", "required": False, "invocation": ARGV}]})
rec("D02 可选验证未执行不阻断", "[]", optional, optional == [])

missing_required = validate({"commands": []}, {"verifications": [{"id": "v1", "required": True, "invocation": ARGV}]})
rec("D02 必要验证未执行被拒", "required verification",
    [p.get("reason") for p in missing_required][:2],
    any("required verification" in (p.get("reason") or "") for p in missing_required))

unknown_acceptance = validate({"acceptance_results": [{"acceptance_id": "a9", "conclusion": "passed"}]})
rec("D02 未知验收 id 被拒", "unknown acceptance",
    [p.get("reason") for p in unknown_acceptance][:2],
    any("unknown acceptance_id" in (p.get("reason") or "") for p in unknown_acceptance))

# ---- D03：处置事实核验 ----
def fp(digest, exists=True):
    return {"kind": "file", "exists": exists, "executable": False, "digest": digest}


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
open(os.path.join(F, "pkg/d03.txt"), "w").write("d03\n")
subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
subprocess.run(["git", "commit", "-qm", "d03", "--allow-empty"], cwd=F, capture_output=True)
probe = wf_tasks.maintenance_disposition_probe(F)

reverse_missing_before = {"changes": [{"path": "pkg/d03.txt"}],
                          "disposition": {"kind": "reverse", "decision": {"choice": "reverse"},
                                          "evidence": {"x": 1}}}
rec("D03 reverse 缺 before → 不结案", "False", probe(reverse_missing_before),
    probe(reverse_missing_before) is False)

empty_fp = {"changes": [{"path": "pkg/d03.txt", "before": {}}],
            "disposition": {"kind": "reverse", "decision": {"choice": "reverse"}, "evidence": {"x": 1}}}
rec("D03 before 为空对象 → 不结案", "False", probe(empty_fp), probe(empty_fp) is False)

transfer_empty_approval = {"changes": [{"path": "pkg/d03.txt"}],
                           "disposition": {"kind": "transfer", "decision": {"choice": "transfer"},
                                           "target_task": "2026-" + "0" * 32, "evidence": {"x": 1}}}
rec("D03 承接任务不存在 → 不结案", "False", probe(transfer_empty_approval),
    probe(transfer_empty_approval) is False)

# 真实承接任务：已批准但路径不覆盖 / 覆盖
target_id = "2026-" + "b" * 32
target_dir = os.path.join(F, ".wf/tasks", f"{target_id}-承接")
os.makedirs(target_dir, exist_ok=True)


def write_target(touch_paths, approval):
    json.dump({"schema_version": 1, "id": target_id, "title": "承接", "status": "in_progress",
               "plan": {"version": "sha256:" + "e" * 64, "touch_paths": touch_paths,
                        "approval": approval}},
              open(os.path.join(target_dir, "task.json"), "w", encoding="utf-8"), ensure_ascii=False)


approved = {"decision": {"choice": "approve"}, "at": AT}
write_target(["other/**"], approved)
not_covered = {"changes": [{"path": "pkg/d03.txt"}],
               "disposition": {"kind": "transfer", "decision": {"choice": "transfer"},
                               "target_task": target_id, "evidence": {"x": 1}}}
rec("D03 承接路径不覆盖 → 不结案", "False", probe(not_covered), probe(not_covered) is False)

write_target(["pkg/**"], approved)
covered = {"changes": [{"path": "pkg/d03.txt"}],
           "disposition": {"kind": "transfer", "decision": {"choice": "transfer"},
                           "target_task": target_id, "evidence": {"x": 1}}}
rec("D03 承接已批准且覆盖 → 结案", "True", probe(covered), probe(covered) is True)

write_target(["pkg/**"], {})
empty_approval = dict(covered)
rec("D03 承接批准为空对象 → 不结案", "False", probe(empty_approval), probe(empty_approval) is False)

# writer：处置决定必须授权 kind
receipt = {"operation": "op", "changes": [], "result": "applied_pending_commit",
           "disposition": {"decision": {"choice": "reject"}, "kind": "commit",
                           "evidence": {"x": 1}}}
state = wf_writer.receipt_state({"maintenance_results": [receipt]},
                                disposition_probe=lambda entry: True)
rec("D03 reject 不能当 commit 结案", "不得为 disposed", state[0]["state"],
    state[0]["state"] != "disposed")

# ---- D04：非法倍数标识 ----
rec("D04 上标数字不被当倍数", "None", wf_gates.parse_debug_ruling("debug-ruling-v-1-²"),
    wf_gates.parse_debug_ruling("debug-ruling-v-1-²") is None)
try:
    wf_tasks._apply_debug_inputs({}, [{"subject": "debug-ruling-v-1-²", "choice": "同一问题"}])
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = type(exc).__name__, getattr(exc, "code", None)
rec("D04 写入路径不给内部异常", "TaskError/WF_RECORD_INVALID", raised,
    raised is not None and raised[1] == "WF_RECORD_INVALID")

# ---- D07：脱敏覆盖 ----
sentinels = {
    "Bearer 短值": "Authorization: Bearer xyz",
    "分离 token": "run --token SENTINEL1 now",
    "下划线 api_key": "--api_key SENTINEL2",
    "access-token": "--access-token SENTINEL3",
}
leaks = {name: text for name, text in sentinels.items() if "SENTINEL" in wf_check.redact_text(text)}
rec("D07 文本级脱敏全覆盖", "无泄漏", list(leaks), not leaks)

# facts 与日志：真实失败命令，输出里带哨兵
verification = {"id": "vd7", "required": True,
                "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c",
                                                        "print('--token SENTINEL9');raise SystemExit(3)"]}}
class Ctx:
    root = F
    def rule_version(self):
        return "sha256:" + "f" * 64
record = wf_check._run_argv(Ctx(), {}, verification, os.path.join(F, ".wf/check-logs"))
log_text = open(os.path.join(F, record["evidence_ref"]), encoding="utf-8").read() if record.get("evidence_ref") else ""
rec("D07 facts 摘要不泄漏", "无哨兵", record.get("summary"), "SENTINEL9" not in json.dumps(record, ensure_ascii=False))
rec("D07b 日志不泄漏", "无哨兵", bool(log_text), "SENTINEL9" not in log_text)

json.dump(results, open("/tmp/r80_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
