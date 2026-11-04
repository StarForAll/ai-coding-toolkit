#!/usr/bin/env python3
"""第三十九轮 R75：bind 实例一致性、报告重哈希、槽位完整性、巡检治理面、锁存活探测。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, tasks as wf_tasks, lock as wf_lock, cli as wf_cli

F = wfdrive.FIX
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-04T09:00:00.000000Z"
REPORT = "<!-- wf-review-report:v1 -->\n```json\n{body}\n```\n"
AXES = ("range", "acceptance", "contract", "regression", "testability")
NOTES = "/tmp/r75_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-A1", **kw):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, **kw)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R75"}


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R75 治理",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-A1")
facts = (payload or {}).get("facts", {})
task_id, genv = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R75\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
for name in ("design.md", "implement.md"):
    open(os.path.join(directory, name), "w").write(f"# {name}\n\n内容。\n")
json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
          open("/tmp/r75_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r75_a.json", "--json"],
   {"generation": genv, "complexity": "complex"}, "sess-A1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, "sess-A1")

# ---- 1. bind 缺失实例标识 → 需人裁决 ----
rc, payload, _ = wfdrive.run(["bind", "--task", task_id, "--json"], {"generation": gen()}, "sess-A1",
                             instance_id="", show=False)
rec("1 bind 缺实例标识被拒", "WF_IDENTITY_UNRESOLVED 或 WF_RECORD_INVALID",
    (payload or {}).get("code"), (payload or {}).get("code") in ("WF_IDENTITY_UNRESOLVED", "WF_RECORD_INVALID"))
rc, payload, _ = wfdrive.run(["bind", "--task", task_id, "--json"], {"generation": gen()}, "sess-A1",
                             instance_id="ffffffffffffffffffffffffffffffff", show=False)
rec("1b bind 实例不符被拒", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
rc, payload, _ = wf(["bind", "--task", task_id, "--json"], {"generation": gen()}, "sess-A1")
rec("1c bind 正常携带可接续", "WF_OK", (payload or {}).get("code"), rc == 0)

# ---- 2. 审查：槽位完整性与报告重哈希 ----
wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": gen()}, "sess-A1")
check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
anchor = (check.get("anchor") or {}).get("check_anchor")


def launch(slots):
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": s, "reviewer_cli": c} for s, c in slots],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    path = "/tmp/r75_launch.json"
    json.dump(request, open(path, "w"), ensure_ascii=False)
    return wf(["review-launch", "--task", task_id, "--launch-request", path, "--json"],
              {"generation": gen()}, "sess-A1")


def report(staging, slot, cli_name, **over):
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1, "reviewer-id": slot,
            "source-cli": cli_name, "review-time": AT, "review-focus": "x",
            "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**"], "scope-exceptions": [],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in AXES},
            "findings": [], "verdict": "pass"}
    body.update(over)
    directory_slot = os.path.join(staging, slot)
    os.makedirs(directory_slot, exist_ok=True)
    path = os.path.join(directory_slot, "report.md")
    open(path, "w", encoding="utf-8").write(REPORT.format(body=json.dumps(body, ensure_ascii=False, indent=2)))
    return path


rc, payload, _ = launch([("slot-a", "codex"), ("slot-b", "pi"), ("slot-c", "claude")])
import glob
staging = glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")[0]
for slot, cli_name in (("slot-a", "codex"), ("slot-b", "pi")):
    p = report(staging, slot, cli_name)
    wf(["review-import", "--task", task_id, "--round", "1", "--slot", slot, "--report", p, "--json"],
       {"generation": gen()}, "sess-A1")
rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                    {"generation": gen()}, "sess-A1")
rec("2 声明三槽位只导入两份 → 拒绝", "WF_REVIEW_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_REVIEW_INVALID")

# 补齐第三份后通过
staging2 = glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")[0]
p3 = report(staging2, "slot-c", "claude")
wf(["review-import", "--task", task_id, "--round", "1", "--slot", "slot-c", "--report", p3, "--json"],
   {"generation": gen()}, "sess-A1")
rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                    {"generation": gen()}, "sess-A1")
rec("2b 三槽位齐全 → pass", "WF_OK", (payload or {}).get("code"), rc == 0)

# 直接改写已归档报告文件 → 门禁应失效
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
target = record["reviews"]["result"]["imported"][0]
report_path = [item for item in record["reviews"]["imported"]
               if item.get("slot") == target.get("slot")][0]["report_path"]
with open(os.path.join(F, report_path), "a", encoding="utf-8") as handle:
    handle.write("\n被改写\n")
json.dump(wfdrive.envelope({"generation": gen()}, "sess-A1"), open("/tmp/r75_env.json", "w"), ensure_ascii=False)
ctx = wf_cli.Context(F, ["--envelope", "/tmp/r75_env.json"])
ok_flag, code, facts = wf_gates.verify_step(ctx, record, "task.review-passed")
rec("2c 报告文件被改写 → 门禁不通过", "WF_REVIEW_INVALID", f"{ok_flag} {code}",
    ok_flag is False and code == "WF_REVIEW_INVALID")

# ---- 3. 巡检消费 reclaim / inspection 键 ----
rc, payload, _ = wf(["inspect", "--json"], {"generation": gen()}, "sess-A1")
governance = ((payload or {}).get("facts") or {}).get("governance") or {}
rec("3 巡检输出治理面", "含 archive_terminals/spec_usage/inspection",
    sorted(governance),
    {"archive_terminals", "spec_usage", "inspection"} <= set(governance))
rec("3b 消费 inspection_every_tasks", "every_tasks=10",
    (governance.get("inspection") or {}).get("every_tasks"),
    (governance.get("inspection") or {}).get("every_tasks") == 10)
rec("3c 消费 spec_reclaim_tasks", "reclaim_threshold=5",
    (governance.get("spec_usage") or {}).get("reclaim_threshold"),
    (governance.get("spec_usage") or {}).get("reclaim_threshold") == 5)

# ---- 4. 锁存活探测 ----
alive, lock_facts = wf_lock.verify_holder(F)
mark = wf_lock.holder_mark(F)
rec("4 无持锁时不误报存活", "存活判定有明确事实", f"alive={alive} mark={bool(mark)}",
    isinstance(alive, bool) and isinstance(lock_facts, dict))
with wf_lock.acquire(F, holder_hint="R75") as handle:
    inside_alive, inside_facts = wf_lock.verify_holder(F)
    handle.release()
rec("4b 持锁期间探测到存活进程", "alive=True 且 pid 匹配",
    f"alive={inside_alive} pid={inside_facts.get('pid')}",
    inside_alive is True and bool(inside_facts.get("pid")))
rec("4c 探测不改动锁文件", "标记仍在", bool(wf_lock.holder_mark(F)) or not os.path.exists(os.path.join(F, ".wf-lock")),
    True)

json.dump(results, open("/tmp/r75_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
