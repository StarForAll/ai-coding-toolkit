#!/usr/bin/env python3
"""第三十一轮 R68：审查判定输入、repair 预览漂移与锁、基线批准与前像、续做分类。"""
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
AT = "2026-11-08T09:00:00.000000Z"
REPORT = "<!-- wf-review-report:v1 -->\n```json\n{body}\n```\n"
NOTES = "/tmp/r68_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-N1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R68"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def proposal_digest(files):
    from wflib import records as _r

    return _r.plain_digest({"files": files})


def run_repair(writer_mutator=None):
    """同进程起 repair --apply：读到令牌提示后改动写者，再输入令牌。"""
    writer_path = os.path.join(F, ".wf/writer.json")
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"), "--project", F, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入令牌确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"令牌：([0-9a-f]{32})", buffer)
    if writer_mutator:
        writer_mutator(writer_path)
    proc.stdin.write((token.group(1) if token else "0" * 32) + "\n")
    proc.stdin.flush()
    rest = proc.stdout.read()
    proc.wait(timeout=60)
    return token, proc.returncode, buffer + rest


def reset_writer():
    record = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
    if record.get("state") == "idle":
        return

    def to_recovering(path):
        data = json.load(open(path, encoding="utf-8"))
        data["state"] = "recovering"
        data["holder"] = None
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    to_recovering(os.path.join(F, ".wf/writer.json"))
    run_repair()


def build_task(title, sid):
    reset_writer()
    clean()
    rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", title,
                         "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    if "directory" not in facts:
        raise SystemExit(f"build_task failed: {(payload or {}).get('code')} {facts}")
    task_id, genv = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv",
                                                          "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    for name in ("design.md", "implement.md"):
        open(os.path.join(directory, name), "w").write(f"# {name}\n\n内容。\n")
    json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
              open("/tmp/r68_a.json", "w"))
    wf(["task-approve", "--task", task_id, "--decision", "/tmp/r68_a.json", "--json"],
       {"generation": genv, "complexity": "complex"}, sid)
    open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
    wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, sid)
    wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": gen()}, sid)
    return task_id, directory, sid


def finish(task_id, sid):
    wf(["task-pause", "--task", task_id, "--reason", "R68 收尾", "--json"], {"generation": gen()}, sid)
    wf(["writer", "release", "--json"], {"generation": gen()}, sid)


def write_report(staging, slot, task_id, check, anchor, **over):
    directory = os.path.join(staging, slot)
    os.makedirs(directory, exist_ok=True)
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1, "reviewer-id": slot,
            "source-cli": {"slot-a": "codex", "slot-b": "pi"}[slot],
            "review-time": AT, "review-focus": "x",
            "check-anchor": {"check_id": (check or {}).get("id"), "check_anchor": anchor},
            "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**"], "scope-exceptions": [],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in ("range", "acceptance", "contract", "regression", "testability")},
            "findings": [], "verdict": "pass"}
    body.update(over)
    path = os.path.join(directory, "report.md")
    open(path, "w", encoding="utf-8").write(REPORT.format(body=json.dumps(body, ensure_ascii=False, indent=2)))
    return path


def scenario(title, sid, mutate=None):
    task_id, directory, sid = build_task(title, sid)
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": "slot-a", "reviewer_cli": "codex"},
                         {"slot": "slot-b", "reviewer_cli": "pi"}],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    json.dump(request, open("/tmp/r68_launch.json", "w"), ensure_ascii=False)
    rc, payload, _ = wf(["review-launch", "--task", task_id, "--launch-request", "/tmp/r68_launch.json",
                         "--json"], {"generation": gen()}, sid)
    if rc != 0:
        return f"launch failed {(payload or {}).get('code')}"
    import glob as _glob

    text = json.dumps(payload or {})
    found = re.search(r'"(/tmp/wf-review/[^"]*/' + re.escape(task_id) + r'/round-1)"', text)
    if found:
        staging = found.group(1)
    else:
        candidates = _glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")
        staging = candidates[0] if candidates else f"/tmp/wf-review/unknown/{task_id}/round-1"
    check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
    anchor = (check.get("anchor") or {}).get("check_anchor")
    for slot in ("slot-a", "slot-b"):
        path = write_report(staging, slot, task_id, check, anchor, **((mutate or {}).get(slot, {})))
        rc_i, payload_i, _ = wf(["review-import", "--task", task_id, "--round", "1", "--slot", slot,
                                 "--report", path, "--json"], {"generation": gen()}, sid)
        if rc_i != 0:
            print("   import failed:", slot, (payload_i or {}).get("code"),
                  json.dumps((payload_i or {}).get("facts"), ensure_ascii=False)[:160])
    if mutate and mutate.get("__after__"):
        mutate["__after__"](task_id, sid)
    rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                        {"generation": gen()}, sid)
    if os.environ.get("R68_DEBUG"):
        print("   decide:", (payload or {}).get("code"),
              json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:300])
    finish(task_id, sid)
    return (payload or {}).get("code")


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()

# ---- 1. 审查判定输入 ----
rec("1 正常审查可 pass", "WF_OK", code := scenario("R68 审查正例", "sess-T1"), code == "WF_OK")


def rerun_check(task_id, sid):
    open(os.path.join(F, "pkg/b.py"), "w").write("b\n")
    wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": gen()}, sid)


code = scenario("R68 旧锚点", "sess-T2", {"__after__": rerun_check})
rec("2 导入后锚点失效 → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code = scenario("R68 阻塞发现", "sess-T3",
                {"slot-a": {"findings": [{"id": "F1", "severity": "blocker", "summary": "阻塞"}]}})
rec("3 带阻塞发现 → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code = scenario("R68 未声明 CLI", "sess-T4", {"slot-b": {"source-cli": "gemini"}})
rec("4 未声明的审查 CLI → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code = scenario("R68 缺材料", "sess-T5", {"slot-a": {"read-scope": []}})
rec("5 缺读取范围声明 → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code = scenario("R68 轴失败", "sess-T6",
                {"slot-a": {"axes": {**{axis: {"conclusion": "pass", "basis": "b"}
                                        for axis in ("range", "acceptance", "contract", "regression")},
                                     "testability": {"conclusion": "fail", "basis": "缺可测性"}}}})
rec("6 审查轴 fail → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")
code = scenario("R68 未覆盖例外", "sess-T7", {"slot-b": {"scope-exceptions": ["验收用例缺失"]}})
rec("7 声明未覆盖例外 → 判定拒绝", "WF_REVIEW_INVALID", code, code == "WF_REVIEW_INVALID")

# ---- 8. repair：确认等待窗口内写者变化 ----
def bump(path):
    data = json.load(open(path, encoding="utf-8"))
    data["state"] = "recovering"
    data["holder"] = None
    data["generation"] = int(data.get("generation") or 0) + 4
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


reset_writer()
token, rc_ok, out_ok = run_repair()
rec("8 预览后无变化时可应用", "WF_OK", f"rc={rc_ok} token={'yes' if token else 'no'}",
    rc_ok == 0 and "WF_OK" in out_ok)
token2, rc_stale, out_stale = run_repair(bump)
rec("8b 等待窗口内写者变化 → 预览失效", "WF_PREVIEW_STALE",
    f"rc={rc_stale} tail={out_stale.strip().splitlines()[-1][:50] if out_stale.strip() else ''}",
    "WF_PREVIEW_STALE" in out_stale)

# ---- 9. 空锁文件不被认领 ----
lock_path = os.path.join(F, ".wf-lock")
if os.path.exists(lock_path):
    os.remove(lock_path)
open(lock_path, "w").close()
reset_writer()
token3, rc_lock, out_lock = run_repair()
rec("9 空锁文件不被 repair 认领", "报锁问题",
    f"rc={rc_lock} tail={out_lock.strip().splitlines()[-1][:60] if out_lock.strip() else ''}",
    "lock" in out_lock.lower() or "wf-lock" in out_lock)
if os.path.exists(lock_path):
    os.remove(lock_path)

# ---- 10. 基线：批准语义与前像 ----
reset_writer()
task_id, directory, sid = build_task("R68 基线", "sess-U1")
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)


def baseline(name, choice="approve", bind=True, before="__omit__", content=None):
    files = [{"path": ".wf/spec/rules/r68b.md", "content": content or f"# {name}\n"}]
    if before != "__omit__":
        files[0]["before"] = before
    body = {"files": files,
            "approval": {"source": "human", "at": AT, "subject": f"r68 {name}", "choice": choice,
                         "object_digest": proposal_digest(files) if bind else "sha256:" + "0" * 64}}
    path = f"/tmp/r68_{name}.json"
    json.dump(body, open(path, "w"), ensure_ascii=False)
    return path


for label, kwargs, expect in (
    ("reject", {"choice": "reject"}, "WF_SEMANTIC_DECISION"),
    ("unbound", {"bind": False}, "WF_APPROVAL_MISSING"),
    ("nobefore", {}, "WF_SEMANTIC_DECISION"),
):
    rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", baseline(label, **kwargs),
                         "--json"], {"generation": gen()}, sid)
    code = (payload or {}).get("code")
    if label == "reject":
        rec("10 拒绝决定不得执行基线写入", expect, code, code == expect)
    elif label == "unbound":
        rec("10b 批准未绑定本提案 → 拒绝", expect, code, code == expect)
    else:
        rec("10c 缺前像指纹 → 拒绝", expect, code, code == expect)
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", baseline("ok", before=None),
                     "--json"], {"generation": gen()}, sid)
rec("10d 绑定批准 + 前像齐全 → 通过", "WF_OK", (payload or {}).get("code"), rc == 0)

# ---- 11. 部分成功后同提案重入续做 ----
locked = os.path.join(F, ".wf/spec/locked")
os.makedirs(locked, exist_ok=True)
blocked = os.path.join(locked, "r68d.md")
open(blocked, "w").write("# 占位\n")
os.chmod(locked, 0o555)
files = [{"path": ".wf/spec/rules/r68c.md", "content": "# c\n", "before": None},
         {"path": ".wf/spec/locked/r68d.md", "content": "# d\n",
          "before": "sha256:" + hashlib.sha256(open(blocked, "rb").read()).hexdigest()}]
body = {"files": files,
        "approval": {"source": "human", "at": AT, "subject": "r68 resume", "choice": "approve",
                     "object_digest": proposal_digest(files)}}
path = "/tmp/r68_resume.json"
json.dump(body, open(path, "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", path, "--json"],
                    {"generation": gen()}, sid)
rec("11 部分写入失败给结构化退出", "WF_PERSISTENCE_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PERSISTENCE_FAILED")
os.chmod(locked, 0o755)
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", path, "--json"],
                    {"generation": gen()}, sid)
facts = (payload or {}).get("facts") or {}
rec("11b 同提案重入续做（已写文件不挡）", "WF_OK 且 skipped 含已写文件",
    f"{(payload or {}).get('code')} skipped={facts.get('skipped')}",
    rc == 0 and facts.get("skipped") == [".wf/spec/rules/r68c.md"])
finish(task_id, sid)

json.dump(results, open("/tmp/r68_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
