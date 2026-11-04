#!/usr/bin/env python3
"""CP1（A5/A10/A11/A12/A15/A18/A21/A22/A23）回归用例。"""
import hashlib, json, os, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-03T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")



def clean():
    import subprocess
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def wf(args, inputs=None, sid="sess-M1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def decision_file(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def dec(subject, choice, digest="sha256:" + "0" * 64, source="human (test)"):
    return {"source": source, "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "CP1 用例"}


def new_task(title, touch, verifications, acceptance, sid, prd_extra=""):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], sid=sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:400]); raise SystemExit(1)
    directory = os.path.join(F, facts["directory"])
    prd = f"""# {title}

## 机读块

<!-- wf-plan:v1 -->
```json
{json.dumps({"schema_version": 1, "touch_paths": touch, "acceptance": acceptance,
             "verifications": verifications}, ensure_ascii=False, indent=2)}
```
{prd_extra}
"""
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid, complexity="light", downgrade=True):
    path = decision_file(f"/tmp/cp1_{task_id}_approve.json", [dec("approve plan", "approve", digest)])
    inputs = {"generation": gen, "complexity": complexity}
    if downgrade and complexity == "light":
        inputs["downgrade"] = {"reason": "仅新增一个纯函数", "evidence": "触碰面单文件、不碰治理面"}
    return wf(["task-approve", "--task", task_id, "--decision", path, "--json"], inputs, sid)


def start(task_id, gen, sid):
    return wf(["task-start", "--task", task_id, "--json"], {"generation": gen}, sid)


def check(task_id, gen, sid, notes=None, decision=None):
    args = ["task-check", "--task", task_id, "--json"]
    if notes:
        args += ["--review-notes", notes]
    if decision:
        args += ["--decision", decision]
    return wf(args, {"generation": gen}, sid)


def release(task_id, gen, sid):
    wf(["task-pause", "--task", task_id, "--reason", "CP1 收尾", "--json"], {"generation": gen}, sid)
    wf(["writer", "release", "--json"], {"generation": gen}, sid)


PASS_NOTES = "/tmp/cp1_notes_pass.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(PASS_NOTES, "w"))

clean()
# ---------------- T1 / A5：开工回执类型 ----------------
sid = "sess-M1"
task1, gen1, dir1, d1 = new_task("CP1 A5 回执类型", ["src/a5.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid)
approve(task1, d1, gen1, sid)
open(os.path.join(F, "src/a5.txt"), "w").write("a5\n")
rc, payload, out = start(task1, gen1, sid)
record = json.load(open(os.path.join(dir1, "task.json")))
steps = record["execution"]["required_steps"]
bad = [s for s in steps if s["result"] == "reused" and (s.get("skip_basis") or {}).get("completed_ref") is None]
loaded = [s for s in steps if s["id"] == "task.spec-loaded"]
rec("A5 开工回执不含非法 reused", "无 reused∧completed_ref=null", f"reused_null={len(bad)}", not bad)
rec("A5 spec-loaded 写 completed", "result=completed", f"{loaded[-1]['result'] if loaded else None}",
    bool(loaded) and loaded[-1]["result"] == "completed")
release(task1, gen1, sid)

clean()
# ---------------- T2 / A15：开工核 plan-q 覆盖 ----------------
sid = "sess-M2"
task2, gen2, dir2, d2 = new_task("CP1 A15 plan-q", ["src/a15.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid,
                                 prd_extra="\n## 待决问题\n\nplan-q-1：是否按轻量处理？推荐答案：是。\n")
# 批准时需先有答复
rc, payload, out = wf(["task-approve", "--task", task2, "--decision",
                       decision_file("/tmp/cp1_a15_q.json", [dec("approve plan", "approve", d2),
                                                             dec("plan-q-1：是否按轻量处理", "是", d2)]),
                       "--json"], {"generation": gen2, "complexity": "light",
                                   "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)
rec("A15 批准（含答复）", "pass", (payload or {}).get("code"), rc == 0)
# 构造：删掉 plan-q 答复
path2 = os.path.join(dir2, "task.json")
record = json.load(open(path2))
record["execution"]["human_decisions"] = [x for x in record["execution"]["human_decisions"]
                                         if "plan-q-1" not in str(x.get("subject", ""))]
json.dump(record, open(path2, "w"), ensure_ascii=False)
rc, payload, out = start(task2, gen2, sid)
rec("A15 开工核 plan-q 覆盖", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
release(task2, gen2, sid)

clean()
# ---------------- T3 / A10：manual 与空验收的锚点绑定 ----------------
sid = "sess-M3"
task3, gen3, dir3, d3 = new_task("CP1 A10 锚点绑定", ["src/a10.txt"],
                                 [{"id": "m1", "invocation": {"kind": "manual", "criterion": "人工确认文件存在"},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "人判确认", "verification_ids": []}], sid)
approve(task3, d3, gen3, sid)
open(os.path.join(F, "src/a10.txt"), "w").write("a10\n")
start(task3, gen3, sid)
rc, payload, out = check(task3, gen3, sid, PASS_NOTES)
rec("A10 无 Decision 的 manual", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
wrong = decision_file("/tmp/cp1_a10_wrong.json", [dec("m1", "approve", d3), dec("a1", "passed", d3)])
rc, payload, out = check(task3, gen3, sid, PASS_NOTES, wrong)
rec("A10 choice 非枚举不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
right = decision_file("/tmp/cp1_a10_right.json", [dec("m1", "passed", d3), dec("a1", "passed", d3)])
rc, payload, out = check(task3, gen3, sid, PASS_NOTES, right)
ok = rc == 0
record = json.load(open(os.path.join(dir3, "task.json")))
cmds = record["check"]["commands"] if record.get("check") else []
acc = record["check"]["acceptance_results"] if record.get("check") else []
bound = bool(cmds and cmds[0].get("anchor", {}).get("check_anchor")) and \
        bool(acc and acc[0].get("anchor", {}).get("plan_version"))
rec("A10 显式 passed 通过", "pass", (payload or {}).get("code"), ok)
rec("A10 记录绑定锚点与 plan.version", "command/acceptance 均带锚点", f"bound={bound}", bound)
release(task3, gen3, sid)

clean()
# ---------------- T4 / A11：检查期间对象变化 ----------------
sid = "sess-M4"
task4, gen4, dir4, d4 = new_task("CP1 A11 扫描前后", ["src/a11.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv",
                                   "argv": ["/usr/bin/python3", "-c", "open('src/a11.txt','a').write('x')"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件可写", "verification_ids": ["v1"]}], sid)
approve(task4, d4, gen4, sid)
open(os.path.join(F, "src/a11.txt"), "w").write("a11\n")
start(task4, gen4, sid)
rc, payload, out = check(task4, gen4, sid, PASS_NOTES)
rec("A11 检查期间对象变化", "WF_CHECK_STALE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_STALE")
release(task4, gen4, sid)

clean()
# ---------------- T5 / A12：finish 时点解析 ----------------
sid = "sess-M5"
task5, gen5, dir5, d5 = new_task("CP1 A12 finish 解析", ["src/a12.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"},
                                  {"id": "f1", "invocation": {"kind": "argv", "argv": ["/nonexistent/wf-tool"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "finish"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid)
approve(task5, d5, gen5, sid)
open(os.path.join(F, "src/a12.txt"), "w").write("a12\n")
start(task5, gen5, sid)
rc, payload, out = check(task5, gen5, sid, PASS_NOTES)
rec("A12 finish 必需项在 Check 即执行（R11）", "WF_CHECK_FAILED（命令不可执行）",
    (payload or {}).get("code"), (payload or {}).get("code") == "WF_CHECK_FAILED")
rec("A12 归档前不得以未执行项通过", "非 WF_OK",
    (payload or {}).get("code"), (payload or {}).get("code") != "WF_OK")
release(task5, gen5, sid)

clean()
# ---------------- T6 / A18：降级证据复核 ----------------
sid = "sess-M6"
task6, gen6, dir6, d6 = new_task("CP1 A18 降级复核", ["src/a18.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid)
rc, payload, out = approve(task6, d6, gen6, sid)
rec("A18 批准", "pass", (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(dir6, "task.json")))
record["plan"]["complexity_reasons"] = [{"downgrade": True, "reason": "缩范围"}]
json.dump(record, open(os.path.join(dir6, "task.json"), "w"), ensure_ascii=False)
open(os.path.join(F, "src/a18.txt"), "w").write("a18\n")
start(task6, gen6, sid)
check(task6, gen6, sid, PASS_NOTES)
wf(["task-knowledge", "--task", task6, "--decision", "no-update", "--json"], {"generation": gen6}, sid)
rc, payload, out = wf(["archive", "--task", task6, "--decision",
                       decision_file("/tmp/cp1_a18_archive.json", [dec(f"finish {task6}", "finish", d6),
                                                                   dec("src/a18.txt", "commit", d6)]),
                       "--json"], {"generation": gen6}, sid)
rec("A18 降级缺证据阻断", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
release(task6, gen6, sid)

clean()
# ---------------- T7 / A21：交接前置 ----------------
sid = "sess-M7"
task7, gen7, dir7, d7 = new_task("CP1 A21 交接前置", ["src/a21.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid)
approve(task7, d7, gen7, sid)
open(os.path.join(F, "src/a21.txt"), "w").write("a21\n")
start(task7, gen7, sid)
rc, payload, out = wf(["writer-handover", "begin", "--to", "deadbeef", "--decision",
                       decision_file("/tmp/cp1_a21_dec.json", [dec("handover", "accept", d7)]),
                       "--json"], {"generation": gen7}, sid)
rec("A21 未保存进度即交接", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")

# ---------------- T8 / A22：收工判定 ----------------
rc, payload, out = wf(["stop", "--decision",
                       decision_file("/tmp/cp1_a22_keep.json", [dec("src/a21.txt,docs/other.txt", "keep", d7)]),
                       "--json"], {"generation": gen7}, sid)
rec("A22 keep 含范围外路径", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
release(task7, gen7, sid)

clean()
task7b, gen7b, dir7b, d7b = new_task("CP1 A22 commit 覆盖", ["src/a22.txt"],
                                    [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                      "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                    [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], "sess-M7b")
approve(task7b, d7b, gen7b, "sess-M7b")
open(os.path.join(F, "src/a22.txt"), "w").write("a22\n")
start(task7b, gen7b, "sess-M7b")
rc, payload, out = wf(["stop", "--decision",
                       decision_file("/tmp/cp1_a22_commit.json", [dec("src/a22.txt,src/a22-extra.txt", "commit", d7b),
                                                                  dec("src/a22.txt", "commit", d7b)]),
                       "--json"], {"generation": gen7b}, "sess-M7b")
rec("A22 commit 授权未覆盖", "WF_COMMIT_NOT_AUTHORIZED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_COMMIT_NOT_AUTHORIZED")
release(task7b, gen7b, "sess-M7b")

clean()
task7c, gen7c, dir7c, d7c = new_task("CP1 A22 transfer", ["src/a22b.txt"],
                                    [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                      "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                    [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], "sess-M7c")
approve(task7c, d7c, gen7c, "sess-M7c")
open(os.path.join(F, "src/a22b.txt"), "w").write("a22b\n")
start(task7c, gen7c, "sess-M7c")
rc, payload, out = wf(["stop", "--decision",
                       decision_file("/tmp/cp1_a22_transfer.json", [dec("src/a22b.txt", "transfer", d7c)]),
                       "--json"], {"generation": gen7c}, "sess-M7c")
rec("A22 transfer 承接对象不存在", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
release(task7c, gen7c, "sess-M7c")

# ---------------- T9 / A23：放弃预览与去向覆盖 ----------------
clean()
sid = "sess-M8"
task9, gen9, dir9, d9 = new_task("CP1 A23 放弃预览", ["src/a23.txt", "tests/a23.txt"],
                                 [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                   "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                 [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], sid)
approve(task9, d9, gen9, sid)
open(os.path.join(F, "src/a23.txt"), "w").write("a23\n")
open(os.path.join(F, "tests/a23.txt"), "w").write("a23\n")
start(task9, gen9, sid)
stop_dec = decision_file("/tmp/cp1_a23_stop.json", [dec(f"stop {task9}", "abandon", d9)])
rc, payload, out = wf(["task-abandon", "--task", task9, "--decision", stop_dec, "--json"],
                      {"generation": gen9}, sid)
facts = (payload or {}).get("facts", {})
rec("A23 无 disposition 出预览", "WF_SEMANTIC_DECISION 且含 preview.uncommitted",
    f"{(payload or {}).get('code')} uncommitted={len((facts.get('preview') or {}).get('uncommitted', []))}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and (facts.get("preview") or {}).get("uncommitted"))
partial = {"changes": [{"object": "src/a23.txt", "decision_ref": AT, "reason": "保留现状"}], "targets": [], "pending": []}
json.dump(partial, open("/tmp/cp1_a23_partial.json", "w"), ensure_ascii=False)
rc, payload, out = wf(["task-abandon", "--task", task9, "--decision", stop_dec,
                       "--disposition", "/tmp/cp1_a23_partial.json", "--json"], {"generation": gen9}, sid)
rec("A23 去向未覆盖全部未提交路径", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
full = {"changes": [{"object": "src/a23.txt", "decision_ref": AT, "reason": "保留现状"},
                    {"object": "tests/a23.txt", "decision_ref": AT, "reason": "保留现状"}],
        "targets": [], "pending": []}
json.dump(full, open("/tmp/cp1_a23_full.json", "w"), ensure_ascii=False)
with_grant = decision_file("/tmp/cp1_a23_grant.json",
                           [dec(f"stop {task9}", "abandon", d9),
                            dec(["src/a23.txt", "tests/a23.txt"], "commit", d9)])
rc, payload, out = wf(["task-abandon", "--task", task9, "--decision", with_grant,
                       "--disposition", "/tmp/cp1_a23_full.json", "--json"], {"generation": gen9}, sid)
rec("A23 覆盖全部后异常归档", "pass", (payload or {}).get("code"), rc == 0)
wf(["writer", "release", "--json"], {"generation": gen9}, sid)

json.dump(results, open("/tmp/cp1_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
