#!/usr/bin/env python3
"""第三十五轮 R71：交接实例核验、dispose 锁内重核、审查五轴齐全。"""
import hashlib, json, os, re, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
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


def review_case(name, axes, expect_code, expect_verdict=None, single=False, slot_specs=None):
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
    if slot_specs is None:
        slot_specs = [("slot-a", "codex")] if single else [("slot-a", "codex"), ("slot-b", "pi")]
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": slot, "reviewer_cli": cli} for slot, cli in slot_specs],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    launch_path = f"/tmp/r71_launch_{name}.json"
    json.dump(request, open(launch_path, "w"), ensure_ascii=False)
    # K6 第 3 类：外发以"确认入库"为准，请求里的 export_decision 只是声明
    export_path = f"/tmp/r71_export_{name}.json"
    json.dump([{"choice": "export", "paths": ["pkg/**"], "quote": "人同意把材料外发给审查 CLI"}],
              open(export_path, "w"), ensure_ascii=False)
    wf(["authorize", "record", "--task", task_id, "--file", export_path, "--json"],
       {"generation": gen()}, sid)
    rc, payload, _ = wf(["review-launch", "--task", task_id, "--launch-request", launch_path, "--json"],
                        {"generation": gen()}, sid)
    if rc != 0:
        print("   launch failed:", (payload or {}).get("code"),
              json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:200])
    import glob as _glob

    found = _glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")
    staging = found[0] if found else f"/tmp/wf-review/unknown/{task_id}/round-1"
    # v42 B1：`fail` 轴必须配 blocking finding，申报 verdict 也要与推导一致——
    # 否则报告本身不成立（WF_REVIEW_INVALID），测的就不是判定链路了。
    _failing = [axis for axis, value in (axes or {}).items()
                if (value.get("conclusion") if isinstance(value, dict) else value) == "fail"]
    _findings = [{"id": f"f-{i}", "severity": "blocking", "axis": axis,
                  "assertion_ref": "a1", "summary": f"{axis} 未满足"}
                 for i, axis in enumerate(_failing, start=1)]
    _verdict = "fail" if _failing else "pass"
    for slot, cli in slot_specs:
        body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1, "reviewer-id": slot,
                "source-cli": cli, "review-time": AT,
                "review-focus": "x", "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
                "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"], "scope-exceptions": [],
                "axes": axes, "findings": list(_findings), "verdict": _verdict}
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
    return (payload or {}).get("code"), verdict, (payload or {}).get("facts") or {}, record


all_pass = {axis: {"conclusion": "pass", "basis": "b"} for axis in AXES}
code, verdict, facts, record = review_case("all", all_pass, "WF_OK", "pass")
rec("3 五轴齐全且通过 → pass", "WF_OK/pass", f"{code}/{verdict}", code == "WF_OK" and verdict == "pass")
code, verdict, facts, record = review_case("empty", {}, "WF_REVIEW_INVALID")
rec("3b axes 为空被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code, verdict, facts, record = review_case("only", {"range": {"conclusion": "pass", "basis": "b"}}, "WF_REVIEW_INVALID")
rec("3c 只报一轴被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
partial = dict(all_pass)
partial.pop("testability")
code, verdict, facts, record = review_case("missing", partial, "WF_REVIEW_INVALID")
rec("3d 缺可测性轴被拒", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
unknown_axis = dict(all_pass)
unknown_axis["extra"] = {"conclusion": "pass", "basis": "b"}
extra_code, extra_verdict, extra_facts, extra_record = review_case("extra", unknown_axis, "WF_REVIEW_INVALID")
rec("3e 未知轴被拒且不写判定", "WF_REVIEW_INVALID + result 为空 + 无 fail 历史",
    f"{extra_code} result={((extra_record.get('reviews') or {}).get('result'))}",
    extra_code == "WF_REVIEW_INVALID"
    and ((extra_record.get("reviews") or {}).get("result")) is None
    and not any((a.get("outcome") == "fail") for a in ((extra_record.get("reviews") or {}).get("attempts") or [])))

single_code, single_verdict, single_facts, single_record = review_case("single", all_pass, "WF_REVIEW_INVALID", None, single=True)
rec("3f 单 reviewer 不产生判定结论", "WF_REVIEW_INVALID + degraded + 两个出口",
    f"{single_code} degraded={single_facts.get('degraded')} exits={len(single_facts.get('exits') or [])}",
    single_code == "WF_REVIEW_INVALID" and single_verdict is None
    and single_facts.get("degraded") == "single-provider"
    and len(single_facts.get("exits") or []) == 2
    and single_facts.get("imported_reports")
    and ((single_record.get("reviews") or {}).get("result")) is None
    and not any((a.get("outcome") == "fail") for a in ((single_record.get("reviews") or {}).get("attempts") or [])))

# 有效输入但审查结论 fail：必须写 verdict=fail 并留可重建的历史（§91 曾错指 3b）
fail_axes = {axis: {"conclusion": "fail", "basis": "b"} for axis in AXES}
fail_code, fail_verdict, fail_facts, fail_record = review_case("real-fail", fail_axes, "WF_REVIEW_INVALID", "fail")
_fail_reviews = fail_record.get("reviews") or {}
if fail_verdict != "fail":
    print("3h facts:", json.dumps(fail_facts, ensure_ascii=False)[:500])
rec("3h 有效审查 fail 落判定且历史可重建", "WF_REVIEW_INVALID + verdict=fail + attempts.outcome=fail",
    f"{fail_code}/{fail_verdict}/"
    f"{[a.get('outcome') for a in (_fail_reviews.get('attempts') or [])]}",
    fail_code == "WF_REVIEW_INVALID" and fail_verdict == "fail"
    and ((_fail_reviews.get("result") or {}).get("verdict")) == "fail"
    and any(a.get("outcome") == "fail" for a in (_fail_reviews.get("attempts") or [])))

same_code, same_verdict, same_facts, same_record = review_case(
    "samecli", all_pass, "WF_REVIEW_INVALID", None,
    slot_specs=[("slot-a", "codex"), ("slot-b", "codex")])
rec("3g 同 CLI 双槽位不产生判定结论", "WF_REVIEW_INVALID + result 为空 + 无 fail 历史",
    f"{same_code} result={((same_record.get('reviews') or {}).get('result'))}",
    same_code == "WF_REVIEW_INVALID"
    and ((same_record.get("reviews") or {}).get("result")) is None
    and not any((a.get("outcome") == "fail")
                for a in ((same_record.get("reviews") or {}).get("attempts") or [])))


# ---------- 4. 两段显式交接 E2E（旧代次失效 → 接收者 accept → 新代次生效） ----------
ho_id, ho_dir, ho_sid = build_task("R71 交接 E2E", "sess-H1")
wf(["task-pause", "--task", ho_id, "--reason", "交接 E2E", "--json"], {"generation": gen()}, ho_sid)
json.dump([dec(f"handover {ho_id}", "handover")], open("/tmp/r71_ho2.json", "w"))
_old_gen = gen()
# receiver 按 session-key 核（不是裸会话名）：先按同一身份派生 H2 的 key
sys.path.insert(0, os.path.join(F, ".wf/lib"))
try:
    from wflib import session as _wf_session
    _h2_key = _wf_session.session_key({"provider": "host",
                                       "identity": {"host_id": "dsh", "session_id": "sess-H2"}})
finally:
    sys.path.pop(0)
rc, payload, _ = wf(["writer-handover", "begin", "--to", _h2_key, "--decision", "/tmp/r71_ho2.json",
                     "--json"], {"generation": _old_gen}, ho_sid)
rec("4 交接 begin 成功", "WF_OK", (payload or {}).get("code"), rc == 0)
_ho_state = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
rec("4b begin 后进入 recovering 且旧代次失效",
    "state=recovering，代次已递增",
    f"{_ho_state.get('state')}/{_ho_state.get('generation')}",
    _ho_state.get("state") == "recovering"
    and isinstance(_ho_state.get("generation"), int)
    and _ho_state.get("generation") > _old_gen)

rc, payload, _ = wf(["task-resume", "--task", ho_id, "--json"], {"generation": _old_gen}, ho_sid)
rec("4c 交接中间态旧会话不可写", "非 WF_OK（WF_GENERATION_STALE/WF_WRITER_BUSY/WF_IDENTITY_UNRESOLVED）",
    (payload or {}).get("code"),
    rc != 0 and (payload or {}).get("code") in
    ("WF_GENERATION_STALE", "WF_WRITER_BUSY", "WF_IDENTITY_UNRESOLVED", "WF_BINDING_MISMATCH"))

# 接收者 accept 之前也不能推进（中间态双方不可写）
rc_pre, payload_pre, _ = wfdrive.run(["task-resume", "--task", ho_id, "--json"],
                                     {"generation": _old_gen}, "sess-H2", show=False)
rec("4c2 accept 前接收者不可推进", "非 WF_OK",
    (payload_pre or {}).get("code"),
    rc_pre != 0 and (payload_pre or {}).get("code") in
    ("WF_BINDING_MISMATCH", "WF_WRITER_BUSY", "WF_GENERATION_STALE", "WF_IDENTITY_UNRESOLVED"))

rc, payload, _ = wfdrive.run(["writer-handover", "accept", "--json"], {}, "sess-H2", show=False)
_accept_gen = ((payload or {}).get("facts") or {}).get("generation")
rec("4d 接收者 accept 获得新代次", "WF_OK 且代次大于 begin 前",
    f"{(payload or {}).get('code')}/{_accept_gen}",
    rc == 0 and isinstance(_accept_gen, int) and _accept_gen > _old_gen)

rc, payload, _ = wf(["task-resume", "--task", ho_id, "--json"], {"generation": _accept_gen}, "sess-H2")
rec("4e 接收者持新代次可推进", "WF_OK", (payload or {}).get("code"), rc == 0)
# accept 之后旧会话（含旧代次）必须失效
rc_old, payload_old, _ = wf(["task-resume", "--task", ho_id, "--json"],
                            {"generation": _old_gen}, ho_sid)
rec("4f accept 后旧会话/旧代次失效", "非 WF_OK",
    (payload_old or {}).get("code"),
    rc_old != 0 and (payload_old or {}).get("code") in
    ("WF_WRITER_BUSY", "WF_GENERATION_STALE", "WF_BINDING_MISMATCH", "WF_IDENTITY_UNRESOLVED"))
wf(["writer", "release", "--json"], {"generation": _accept_gen}, "sess-H2")

json.dump(results, open("/tmp/r71_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
