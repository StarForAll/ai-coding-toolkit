#!/usr/bin/env python3
"""第三十五轮 R71：交接实例核验、dispose 锁内重核、审查五轴齐全。"""
import hashlib, json, os, re, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-11T09:00:00.000000Z"
REPORT = "<!-- wf-review-report:v1 -->\n```json\n{body}\n```\n"
NOTES = "/tmp/r71_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))
AXES = ("range", "acceptance", "contract", "regression", "testability")


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-X1", **kw):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, **kw)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R71"}


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def build_task(title, sid, complexity="complex"):
    clean()
    rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", title,
                         "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, genv = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(directory, name), "w").write(f"# {name}\n\n内容。\n")
    json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open("/tmp/r71_a.json", "w"))
    inputs = {"generation": genv, "complexity": complexity}
    if complexity == "light":
        inputs["downgrade"] = {"reason": "单文件", "evidence": "不碰治理面"}
    wf(["task-approve", "--task", task_id, "--decision", "/tmp/r71_a.json", "--json"], inputs, sid)
    open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
    rc_s, payload_s, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, sid)
    if rc_s != 0:
        print("   start failed:", (payload_s or {}).get("code"),
              json.dumps((payload_s or {}).get("facts"), ensure_ascii=False)[:200])
    return task_id, directory, sid


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)

# ---------- 1. 交接两端都核实例标识 ----------
task_id, directory, sid = build_task("R71 交接", "sess-X1")
wf(["task-pause", "--task", task_id, "--reason", "交接准备", "--json"], {"generation": gen()}, sid)
json.dump([dec(f"handover {task_id}", "handover")], open("/tmp/r71_ho.json", "w"))
rc, payload, _ = wfdrive.run(["writer-handover", "begin", "--to", "sess-X2", "--decision", "/tmp/r71_ho.json",
                              "--json"], {"generation": gen()}, sid,
                             instance_id="ffffffffffffffffffffffffffffffff", show=False)
rec("1 交接发起拒绝错误实例标识", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
writer_state = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("state")
rec("1b 交接未进入 recovering", "held", writer_state, writer_state == "held")
rc, payload, _ = wf(["writer-handover", "begin", "--to", "sess-X2", "--decision", "/tmp/r71_ho.json",
                     "--json"], {"generation": gen()}, sid)
rec("1c 正常交接发起", "WF_OK", (payload or {}).get("code"), rc == 0)

# ---------- 2. dispose 锁内重核 ----------
def run_dispose(plan_path, mutator=None):
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"), "--project", F,
                             "--dispose", plan_path, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入令牌确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"令牌：([0-9a-f]{32})", buffer)
    if mutator:
        mutator()
    proc.stdin.write((token.group(1) if token else "0" * 32) + "\n")
    proc.stdin.flush()
    rest = proc.stdout.read()
    proc.wait(timeout=90)
    return proc.returncode, buffer + rest


writer_path = os.path.join(F, ".wf/writer.json")
writer = json.load(open(writer_path, encoding="utf-8"))
receipt = {
    "operation": "r71-op", "preview_digest": "sha256:" + "1" * 64, "head_before": None,
    "changes": [{"path": "pkg/a.py", "before": None, "after": None}],
    "receipt_git_state": {}, "result": "applied_pending_commit", "disposition": None,
}
writer["maintenance_results"] = [receipt]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def plan_for(reason):
    return {"operation": "r71-op",
            "disposition": {"decision": {"source": "human", "at": AT, "subject": "r71", "choice": "commit",
                                         "object_digest": "sha256:" + "0" * 64, "reason": reason},
                            "kind": "commit", "target_task": None,
                            "evidence": {"commit": "0" * 40, "verified_by": "human", "paths": "r71"}}}


base_plan = "/tmp/r71_dispose.json"
json.dump(plan_for("A"), open(base_plan, "w"), ensure_ascii=False)


def swap_plan():
    json.dump(plan_for("B"), open(base_plan, "w"), ensure_ascii=False)


rc, out = run_dispose(base_plan, swap_plan)
rec("2 计划被替换 → 预览失效", "WF_PREVIEW_STALE", f"rc={rc}",
    "WF_PREVIEW_STALE" in out)
writer_now = json.load(open(writer_path, encoding="utf-8"))
disposed = (writer_now.get("maintenance_results") or [{}])[0].get("disposition")
rec("2b 未按被替换的计划写回", "disposition 仍为空", disposed, disposed is None)

json.dump(results, open("/tmp/r71_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

# 清理第 2 段的维护回执，避免挡住后续任务的开工程序
writer_now = json.load(open(writer_path, encoding="utf-8"))
writer_now["maintenance_results"] = []
json.dump(writer_now, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- 3. 审查五轴必须齐全 ----------
os.makedirs(os.path.join(F, "pkg2"), exist_ok=True)


def reset_writer():
    record = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
    if record.get("state") == "idle":
        return
    if record.get("state") != "recovering":
        record["state"] = "recovering"
        record["holder"] = None
        json.dump(record, open(os.path.join(F, ".wf/writer.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"), "--project", F, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入令牌确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"令牌：([0-9a-f]{32})", buffer)
    proc.stdin.write((token.group(1) if token else "0" * 32) + "\n")
    proc.stdin.flush()
    proc.stdout.read()
    proc.wait(timeout=90)


def review_case(name, axes, expect_code, expect_verdict=None):
    reset_writer()
    task_id, directory, sid = build_task(f"R71 轴 {name}", f"sess-Y{abs(hash(name)) % 1000}")
    rc_c, payload_c, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                            {"generation": gen()}, sid)
    if rc_c != 0:
        print("   check failed:", (payload_c or {}).get("code"),
              json.dumps((payload_c or {}).get("facts"), ensure_ascii=False)[:200])
    check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
    anchor = (check.get("anchor") or {}).get("check_anchor")
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": "slot-a", "reviewer_cli": "codex"},
                         {"slot": "slot-b", "reviewer_cli": "pi"}],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    launch_path = f"/tmp/r71_launch_{name}.json"
    json.dump(request, open(launch_path, "w"), ensure_ascii=False)
    rc, payload, _ = wf(["review-launch", "--task", task_id, "--launch-request", launch_path, "--json"],
                        {"generation": gen()}, sid)
    if rc != 0:
        print("   launch failed:", (payload or {}).get("code"),
              json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:200])
    import glob as _glob

    found = _glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")
    staging = found[0] if found else f"/tmp/wf-review/unknown/{task_id}/round-1"
    for slot in ("slot-a", "slot-b"):
        body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1, "reviewer-id": slot,
                "source-cli": {"slot-a": "codex", "slot-b": "pi"}[slot], "review-time": AT,
                "review-focus": "x", "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
                "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**"], "scope-exceptions": [],
                "axes": axes, "findings": [], "verdict": "pass"}
        slot_dir = os.path.join(staging, slot)
        os.makedirs(slot_dir, exist_ok=True)
        path = os.path.join(slot_dir, "report.md")
        open(path, "w", encoding="utf-8").write(REPORT.format(body=json.dumps(body, ensure_ascii=False, indent=2)))
        rc_i, payload_i, _ = wf(["review-import", "--task", task_id, "--round", "1", "--slot", slot,
                                 "--report", path, "--json"], {"generation": gen()}, sid)
        if rc_i != 0:
            print("   import failed:", slot, (payload_i or {}).get("code"),
                  json.dumps((payload_i or {}).get("facts"), ensure_ascii=False)[:200])
    rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                        {"generation": gen()}, sid)
    if rc != 0:
        print("   decide facts:", (payload or {}).get("code"),
              json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:220])
    record = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
    verdict = ((record.get("reviews") or {}).get("result") or {}).get("verdict")
    wf(["task-pause", "--task", task_id, "--reason", "收尾", "--json"], {"generation": gen()}, sid)
    wf(["writer", "release", "--json"], {"generation": gen()}, sid)
    return (payload or {}).get("code"), verdict


all_pass = {axis: {"conclusion": "pass", "basis": "b"} for axis in AXES}
code, verdict = review_case("all", all_pass, "WF_OK", "pass")
rec("3 五轴齐全且通过 → pass", "WF_OK/pass", f"{code}/{verdict}", code == "WF_OK" and verdict == "pass")
code, verdict = review_case("empty", {}, "WF_REVIEW_INVALID")
rec("3b axes 为空被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code, verdict = review_case("only", {"range": {"conclusion": "pass", "basis": "b"}}, "WF_REVIEW_INVALID")
rec("3c 只报一轴被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
partial = dict(all_pass)
partial.pop("testability")
code, verdict = review_case("missing", partial, "WF_REVIEW_INVALID")
rec("3d 缺可测性轴被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
unknown_axis = dict(all_pass)
unknown_axis["extra"] = {"conclusion": "pass", "basis": "b"}
code, verdict = review_case("extra", unknown_axis, "WF_REVIEW_INVALID")
rec("3e 未知轴被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")

json.dump(results, open("/tmp/r71_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
