#!/usr/bin/env python3
"""第三轮 R7–R15 用例（隔离夹具）。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []

def _pd(files):
    import sys as _s
    _s.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
    from wflib import records as _r
    return _r.plain_digest({"files": files})


def _pdict(files, approval):
    approval = dict(approval)
    approval["object_digest"] = _pd(files)
    return {"files": files, "approval": approval}

AT = "2026-11-03T21:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-T1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64, **extra):
    base = {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R7-R15 用例"}
    base.update(extra)
    return base


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-T1", verifications=None, acceptance=None):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:300]); raise SystemExit(1)
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": acceptance or [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": verifications or [{"id": "v1", "invocation": {
                 "kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                 "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid="sess-T1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r7_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/r7_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- R7：baseline-apply 边界 ----------------
clean()
task1, gen1, dir1, d1 = make_task("R7 基线边界", [".wf/spec/**"], "sess-T1")
approve(task1, d1, gen1)
proposal = dfile("/tmp/r7_prop_ok.json", _pdict([{"path": ".wf/spec/ok.md", "content": "# ok\n", "before": None}], {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": "r7 proposal", "choice": "approve",
                    "object_digest": None, "reason": "R7"}))
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", proposal, "--json"], {"generation": gen1})
rec("R7 未开工不得应用", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
rec("R7 未开工零写入", "未写 ok.md", os.path.exists(os.path.join(F, ".wf/spec/ok.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/ok.md")))
rc_start, start_payload, _ = wf(["task-start", "--task", task1, "--json"], {"generation": gen1})
rec("R7 准备：开工", "WF_OK", (start_payload or {}).get("code"), rc_start == 0)
bad = dfile("/tmp/r7_prop_writer.json", _pdict([{"path": ".wf/writer.json", "content": "{}", "before": None}], {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": "r7 proposal", "choice": "approve",
                    "object_digest": None, "reason": "R7"}))
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", bad, "--json"], {"generation": gen1})
rec("R7 控制记录不得作目标", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
outside = dfile("/tmp/r7_prop_src.json", _pdict([{"path": "src/r7.txt", "content": "x\n", "before": None}], {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": "r7 proposal", "choice": "approve",
                    "object_digest": None, "reason": "R7"}))
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", outside, "--json"], {"generation": gen1})
rec("R7 业务路径不得经基线写入", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", proposal, "--json"], {"generation": gen1})
rec("R7 合法提案可应用", "WF_OK", (payload or {}).get("code"), rc == 0)

# 符号链接逃逸
os.makedirs("/tmp/outside-target", exist_ok=True)
if not os.path.islink(os.path.join(F, ".wf/spec/link")):
    os.symlink("/tmp/outside-target", os.path.join(F, ".wf/spec/link"))
escape = dfile("/tmp/r7_prop_link.json", _pdict([{"path": ".wf/spec/link/x.md", "content": "# x\n", "before": None}], {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": "r7 proposal", "choice": "approve",
                    "object_digest": None, "reason": "R7"}))
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", escape, "--json"], {"generation": gen1})
rec("R7 符号链接逃逸被拒", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R7 逃逸时未写项目外文件", "outside 未生成 x.md", os.path.exists("/tmp/outside-target/x.md"),
    not os.path.exists("/tmp/outside-target/x.md"))
os.remove(os.path.join(F, ".wf/spec/link"))
wf(["task-pause", "--task", task1, "--reason", "R7 收尾", "--json"], {"generation": gen1})
wf(["writer", "release", "--json"], {"generation": gen1})
clean()

# 触碰面外目标（窄触碰面任务）
task1b, gen1b, dir1b, d1b = make_task("R7b 触碰面", [".wf/baseline.md"], "sess-T1b")
approve(task1b, d1b, gen1b, "sess-T1b")
rc_s, start_payload, _ = wf(["task-start", "--task", task1b, "--json"], {"generation": gen1b}, "sess-T1b")
rec("R7b 准备：开工", "WF_OK", (start_payload or {}).get("code"), rc_s == 0)
offscope = dfile("/tmp/r7_prop_spec.json", _pdict([{"path": ".wf/spec/other.md", "content": "# o\n", "before": None}], {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                    "subject": "r7 proposal", "choice": "approve",
                    "object_digest": None, "reason": "R7"}))
rc, payload, _ = wf(["baseline-apply", "--task", task1b, "--proposal", offscope, "--json"],
                    {"generation": gen1b}, "sess-T1b")
rec("R7 目标须在批准触碰面内", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
wf(["task-pause", "--task", task1b, "--reason", "R7 收尾", "--json"], {"generation": gen1b}, "sess-T1b")
wf(["writer", "release", "--json"], {"generation": gen1b}, "sess-T1b")

# ---------------- R8：spec-update 目标类别 ----------------
clean()
task8, gen8, dir8, d8 = make_task("R8 spec 目标类别", [".wf/spec/**"], "sess-T8")
approve(task8, d8, gen8, "sess-T8")
rc_s8, start8, _ = wf(["task-start", "--task", task8, "--json"], {"generation": gen8}, "sess-T8")
rec("R8 准备：开工", "WF_OK", (start8 or {}).get("code"), rc_s8 == 0)
wrong = dfile("/tmp/r7_spec_writer.json", [{"operation": "add", "new_paths": [".wf/writer.json"], "content": "{}"}])
rc, payload, _ = wf(["spec-update", "--task", task8, "--changes", wrong, "--json"], {"generation": gen8}, "sess-T8")
rec("R8 spec 不得写控制记录", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
wf(["task-pause", "--task", task8, "--reason", "R8 收尾", "--json"], {"generation": gen8}, "sess-T8")
wf(["writer", "release", "--json"], {"generation": gen8}, "sess-T8")

# ---------------- R10：双轴必须通过 ----------------
clean()
task10, gen10, dir10, d10 = make_task("R10 双轴", ["src/r10.txt"], "sess-T2")
approve(task10, d10, gen10, "sess-T2")
open(os.path.join(F, "src/r10.txt"), "w").write("r10\n")
rc_s10, start10, _ = wf(["task-start", "--task", task10, "--json"], {"generation": gen10}, "sess-T2")
rec("R10 准备：开工", "WF_OK", (start10 or {}).get("code"), rc_s10 == 0)
fail_notes = "/tmp/r7_notes_fail.json"
json.dump({"standard": {"conclusion": "fail", "basis": "契约不一致"},
           "requirement": {"conclusion": "fail", "basis": "验收未覆盖"}}, open(fail_notes, "w"))
rc, payload, _ = wf(["task-check", "--task", task10, "--review-notes", fail_notes, "--json"],
                    {"generation": gen10}, "sess-T2")
rec("R10 双轴 fail 不得 pass", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
rc, payload, _ = wf(["task-check", "--task", task10, "--review-notes", NOTES, "--json"],
                    {"generation": gen10}, "sess-T2")
rec("R10 双轴 pass 可继续", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-pause", "--task", task10, "--reason", "R10 收尾", "--json"], {"generation": gen10}, "sess-T2")
wf(["writer", "release", "--json"], {"generation": gen10}, "sess-T2")

# ---------------- R11：finish 验证必须执行 ----------------
clean()
verifications = [
    {"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
     "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"},
    {"id": "v2", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "raise SystemExit(3)"]},
     "cwd": ".", "input_refs": [], "required": True, "consume_at": "finish"}]
task11, gen11, dir11, d11 = make_task("R11 finish 验证", ["src/r11.txt"], "sess-T3", verifications=verifications)
approve(task11, d11, gen11, "sess-T3")
open(os.path.join(F, "src/r11.txt"), "w").write("r11\n")
rc_s11, start11, _ = wf(["task-start", "--task", task11, "--json"], {"generation": gen11}, "sess-T3")
rec("R11 准备：开工", "WF_OK", (start11 or {}).get("code"), rc_s11 == 0)
rc, payload, _ = wf(["task-check", "--task", task11, "--review-notes", NOTES, "--json"],
                    {"generation": gen11}, "sess-T3")
record = json.load(open(os.path.join(dir11, "task.json")))
ids = [c.get("verification_id") for c in (record.get("check") or {}).get("commands") or []]
rec("R11 finish 项在 Check 被执行", "commands 含 v2 且 Check 未 pass",
    f"ids={ids} code={(payload or {}).get('code')}",
    "v2" in ids and (payload or {}).get("code") in ("WF_CHECK_FAILED", "WF_VERIFICATION_UNREADY"))
wf(["task-pause", "--task", task11, "--reason", "R11 收尾", "--json"], {"generation": gen11}, "sess-T3")
wf(["writer", "release", "--json"], {"generation": gen11}, "sess-T3")

json.dump(results, open("/tmp/r7r15_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")

# ---------------- R9：改名/删除的续做 ----------------
clean()
task9, gen9, dir9, d9 = make_task("R9 改名续做", [".wf/spec/**"], "sess-T9")
approve(task9, d9, gen9, "sess-T9")
rc_s9, start9, _ = wf(["task-start", "--task", task9, "--json"], {"generation": gen9}, "sess-T9")
rec("R9 准备：开工", "WF_OK", (start9 or {}).get("code"), rc_s9 == 0)
rule = '''---
schema_version: 1
paths: ["src/r9.py"]
status: "active"
verified_at: "2026-11-03"
author: "ai"
counterexample: "r9 未校验"
---

# r9 约定

正文。
'''
add = dfile("/tmp/r9_add.json", [{"operation": "add", "new_paths": [".wf/spec/r9.md"], "content": rule}])
rc, payload, _ = wf(["spec-update", "--task", task9, "--changes", add, "--json"], {"generation": gen9}, "sess-T9")
rec("R9 准备：建条目", "WF_OK", (payload or {}).get("code"), rc == 0)
index_path = os.path.join(F, ".wf/spec/index.md")
backup = open(index_path, encoding="utf-8").read()
os.remove(index_path)
os.makedirs(index_path)
rename = dfile("/tmp/r9_rename.json", [{"operation": "rename", "old_paths": [".wf/spec/r9.md"],
                                        "new_paths": [".wf/spec/r9b.md"]}])
rc, payload, _ = wf(["spec-update", "--task", task9, "--changes", rename, "--json"], {"generation": gen9}, "sess-T9")
rec("R9 改名后索引写失败", "WF_PERSISTENCE_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PERSISTENCE_FAILED")
rec("R9 改名本身已落盘", "r9b.md 存在且 r9.md 不存在",
    f"new={os.path.exists(os.path.join(F, '.wf/spec/r9b.md'))} old={os.path.exists(os.path.join(F, '.wf/spec/r9.md'))}",
    os.path.exists(os.path.join(F, ".wf/spec/r9b.md")) and not os.path.exists(os.path.join(F, ".wf/spec/r9.md")))
os.rmdir(index_path)
open(index_path, "w", encoding="utf-8").write(backup)
rc, payload, _ = wf(["spec-update", "--task", task9, "--changes", rename, "--json"], {"generation": gen9}, "sess-T9")
index_text = open(index_path, encoding="utf-8").read()
rec("R9 同变更集重入完成剩余步骤", "WF_OK 且索引含 r9b.md",
    f"{(payload or {}).get('code')} index={'r9b.md' in index_text}",
    rc == 0 and "r9b.md" in index_text and index_text.count("r9b.md") == 1)
wf(["task-pause", "--task", task9, "--reason", "R9 收尾", "--json"], {"generation": gen9}, "sess-T9")
wf(["writer", "release", "--json"], {"generation": gen9}, "sess-T9")

# ---------------- R12：人判绑定对象与版本 ----------------
clean()
task12, gen12, dir12, d12 = make_task(
    "R12 人判绑定", ["src/r12.txt"], "sess-T12",
    verifications=[{"id": "v1", "invocation": {"kind": "manual", "criterion": "人工确认 r12"},
                    "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
    acceptance=[{"id": "a1", "statement": "人判验收", "verification_ids": ["v1"]}])
approve(task12, d12, gen12, "sess-T12")
open(os.path.join(F, "src/r12.txt"), "w").write("r12\n")
rc_s12, start12, _ = wf(["task-start", "--task", task12, "--json"], {"generation": gen12}, "sess-T12")
rec("R12 准备：开工", "WF_OK", (start12 or {}).get("code"), rc_s12 == 0)
old = dfile("/tmp/r12_old.json", [dec("v10 a1", "passed", d12)])
rc, payload, _ = wf(["task-check", "--task", task12, "--decision", old, "--review-notes", NOTES, "--json"],
                    {"generation": gen12}, "sess-T12")
rec("R12 旧 id/旧对象不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
zeros = dfile("/tmp/r12_zeros.json", [dec("v1 a1", "passed", "sha256:" + "0" * 64)])
rc, payload, _ = wf(["task-check", "--task", task12, "--decision", zeros, "--review-notes", NOTES, "--json"],
                    {"generation": gen12}, "sess-T12")
rec("R12 未绑定批准对象的决定不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
right = dfile("/tmp/r12_right.json", [dec("v1 a1", "passed", d12)])
rc, payload, _ = wf(["task-check", "--task", task12, "--decision", right, "--review-notes", NOTES, "--json"],
                    {"generation": gen12}, "sess-T12")
rec("R12 绑定对象与版本的决定通过", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-pause", "--task", task12, "--reason", "R12 收尾", "--json"], {"generation": gen12}, "sess-T12")
wf(["writer", "release", "--json"], {"generation": gen12}, "sess-T12")

# ---------------- R13：Check 期 spec 兜底 ----------------
clean()
pathed = '''---
schema_version: 1
paths: ["src/**"]
status: "active"
verified_at: "2026-11-03"
author: "ai"
counterexample: "未覆盖新增文件"
---

# src 规范

正文。
'''
extracted = '''---
schema_version: 1
paths: ["src/**"]
status: "active"
verified_at: "extracted"
author: "ai"
counterexample: "未核实"
---

# 提取条目

正文。
'''
json.dump([{"operation": "add", "new_paths": [".wf/spec/rules/src.md"], "content": pathed}],
          open("/tmp/r13_seed.json", "w"), ensure_ascii=False)
task13, gen13, dir13, d13 = make_task("R13 spec 兜底", ["src/**", ".wf/spec/**"], "sess-T13")
approve(task13, d13, gen13, "sess-T13")
rc_s13, start13, _ = wf(["task-start", "--task", task13, "--json"], {"generation": gen13}, "sess-T13")
rec("R13 准备：开工", "WF_OK", (start13 or {}).get("code"), rc_s13 == 0)
rc, payload, _ = wf(["spec-update", "--task", task13, "--changes", "/tmp/r13_seed.json", "--json"],
                    {"generation": gen13}, "sess-T13")
open(os.path.join(F, "src/r13.txt"), "w").write("r13\n")
rc, payload, _ = wf(["task-check", "--task", task13, "--review-notes", NOTES, "--json"],
                    {"generation": gen13}, "sess-T13")
rec("R13 漏策展的命中被阻断", "WF_SPEC_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE")
wf(["task-curate", "--task", task13, "--spec", ".wf/spec/rules/src.md", "--purpose", "src 规范", "--json"],
   {"generation": gen13}, "sess-T13")
wf(["spec", "--file", ".wf/spec/rules/src.md", "--json"], {"generation": gen13}, "sess-T13")
json.dump([{"operation": "add", "new_paths": [".wf/spec/rules/src-extracted.md"], "content": extracted}],
          open("/tmp/r13_extracted.json", "w"), ensure_ascii=False)
wf(["spec-update", "--task", task13, "--changes", "/tmp/r13_extracted.json", "--json"],
   {"generation": gen13}, "sess-T13")
wf(["task-curate", "--task", task13, "--spec", ".wf/spec/rules/src-extracted.md",
    "--purpose", "提取条目", "--json"], {"generation": gen13}, "sess-T13")
wf(["spec", "--file", ".wf/spec/rules/src-extracted.md", "--json"], {"generation": gen13}, "sess-T13")
rc, payload, _ = wf(["task-check", "--task", task13, "--review-notes", NOTES, "--json"],
                    {"generation": gen13}, "sess-T13")
rec("R13 未核实条目阻断", "WF_SPEC_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE")
decide = dfile("/tmp/r13_decision.json", [dec(".wf/spec/rules/src-extracted.md", "passed", d13)])
rc, payload, _ = wf(["task-check", "--task", task13, "--decision", decide, "--review-notes", NOTES, "--json"],
                    {"generation": gen13}, "sess-T13")
rec("R13 人判覆盖后可继续", "WF_OK",
    f"{(payload or {}).get('code')} spec={json.dumps(((payload or {}).get('facts') or {}).get('spec'), ensure_ascii=False)[:160]}",
    rc == 0)
wf(["task-pause", "--task", task13, "--reason", "R13 收尾", "--json"], {"generation": gen13}, "sess-T13")
wf(["writer", "release", "--json"], {"generation": gen13}, "sess-T13")

# ---------------- R14：归档持久化只认任务记录 ----------------
clean()
demo_id = "2026-" + "d" * 32
demo_rel = f".wf/tasks/archive/2026-11/{demo_id}-demo"
os.makedirs(os.path.join(F, demo_rel, "review"), exist_ok=True)
open(os.path.join(F, demo_rel, "review/notes.md"), "w").write("# notes\n")
subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
subprocess.run(["git", "commit", "-qm", "only notes"], cwd=F, capture_output=True)
lower = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=F, capture_output=True, text=True).stdout.strip()
synthetic = {"id": demo_id, "action": {"kind": "task.archive", "head_before": lower}}
result = wf_tasks.archive_persisted(F, synthetic)
rec("R14 只提交 review/notes.md 不算已持久化", "persisted=False", result.get("persisted"),
    result.get("persisted") is False)
open(os.path.join(F, demo_rel, "task.json"), "w").write(json.dumps({"id": demo_id, "terminal": "normal"}))
subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
subprocess.run(["git", "commit", "-qm", "record"], cwd=F, capture_output=True)
result = wf_tasks.archive_persisted(F, synthetic)
rec("R14 记录进入提交才算已持久化", "persisted=True", result.get("persisted"), result.get("persisted") is True)

# ---------------- R15：锁按 §4.1 ----------------
clean()
lock_path = os.path.join(F, ".wf-lock")
open(lock_path, "wb").write(b"")
proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "task-new", "--kind", "ordinary",
                       "--title", "R15-empty", "--template", os.path.join(F, ".wf/templates/task"), "--json"],
                      cwd=F, capture_output=True, text=True,
                      input=json.dumps({"session": {"provider": "host",
                                                    "identity": {"host_id": "dsh", "session_id": "sess-T15"},
                                                    "instance_id": None,
                                                    "activation": {"enabled": True, "start_source": "test",
                                                                   "enabled_at": AT}},
                                        "inputs": {"generation": 1}}))
rec("R15 空锁不被认领", "WF_CAPABILITY_UNAVAILABLE",
    f"rc={proc.returncode} has={'WF_CAPABILITY_UNAVAILABLE' in proc.stdout}",
    "WF_CAPABILITY_UNAVAILABLE" in proc.stdout)
rec("R15 空锁未被补写", "仍为空", open(lock_path, "rb").read().decode("latin-1") or "<empty>",
    open(lock_path, "rb").read() == b"")
open(lock_path, "wb").write(b"wf-lock")
proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "task-new", "--kind", "ordinary",
                       "--title", "R15", "--template", os.path.join(F, ".wf/templates/task"), "--json"],
                      cwd=F, capture_output=True, text=True,
                      input=json.dumps({"session": {"provider": "host",
                                                    "identity": {"host_id": "dsh", "session_id": "sess-T15"},
                                                    "instance_id": None,
                                                    "activation": {"enabled": True, "start_source": "test",
                                                                   "enabled_at": AT}},
                                        "inputs": {"generation": 1}}))
rec("R15 部分标记返回 WF_CAPABILITY_UNAVAILABLE", "WF_CAPABILITY_UNAVAILABLE",
    f"rc={proc.returncode} has={'WF_CAPABILITY_UNAVAILABLE' in proc.stdout}",
    "WF_CAPABILITY_UNAVAILABLE" in proc.stdout)
mark = open(lock_path, "rb").read()
rec("R15 不覆写未知内容", "标记仍为 wf-lock", mark.decode("latin-1"), mark == b"wf-lock")
open(lock_path, "wb").write(b"wf-lock-v1\n")
proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "status"], cwd=F,
                      capture_output=True, text=True)
rec("R15 合法标记恢复正常", "rc=0", proc.returncode, proc.returncode == 0)

json.dump(results, open("/tmp/r7r15_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
