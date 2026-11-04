#!/usr/bin/env python3
"""R1（整批预校验 + 未完成动作接续）与 R2（confirm-executor 交互闸门）用例。"""
import json, os, pty, shutil, subprocess, sys, time
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
WF = os.path.join(F, ".wf/bin/wf.py")
results = []

def _pd(files):
    import sys as _s
    _s.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
    from wflib import records as _r
    return _r.plain_digest({"files": files})

AT = "2026-11-03T19:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R12"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R1/R2 用例"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-R12"):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:300]); raise SystemExit(1)
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib_sha(prd)


def hashlib_sha(text):
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def approve(task_id, digest, gen, sid="sess-R12"):
    path = f"/tmp/r12_{task_id}_a.json"
    json.dump([dec("approve", "approve", digest)], open(path, "w"))
    return wf(["task-approve", "--task", task_id, "--decision", path, "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单步", "evidence": "治理面"}}, sid)


# ---------------- R1-a：baseline-apply 整批预校验 ----------------
clean()
task1, gen1, dir1, d1 = make_task("R1 基线整批", [".wf/spec/**"], "sess-R12")
approve(task1, d1, gen1)
wf(["task-start", "--task", task1, "--json"], {"generation": gen1})
files = [
    {"path": ".wf/spec/first.md", "content": "# first\n", "before": None},
    {"path": "../escape.md", "content": "# escape\n", "before": None}]
proposal = {"files": files,
            "approval": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                         "subject": "baseline proposal r1", "choice": "approve",
                         "object_digest": _pd(files), "reason": "R1 用例"}}
json.dump(proposal, open("/tmp/r12_proposal_bad.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", "/tmp/r12_proposal_bad.json", "--json"],
                    {"generation": gen1})
rec("R1 非法条目整批拒绝", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R1 拒绝时零写入", "first.md 不存在", os.path.exists(os.path.join(F, ".wf/spec/first.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/first.md")))

# 写入中途失败 → 动作留存 → 同提案重入续做
os.makedirs(os.path.join(F, ".wf/spec/blocked-dir"), exist_ok=True)
os.chmod(os.path.join(F, ".wf/spec/blocked-dir"), 0o555)
files2 = [
    {"path": ".wf/spec/first.md", "content": "# first\n", "before": None},
    {"path": ".wf/spec/blocked-dir/x.md", "content": "# blocked\n", "before": None}]
proposal2 = {"files": files2,
             "approval": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                          "subject": "baseline proposal r1", "choice": "approve",
                          "object_digest": _pd(files2), "reason": "R1 用例"}}
json.dump(proposal2, open("/tmp/r12_proposal_mid.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", "/tmp/r12_proposal_mid.json", "--json"],
                    {"generation": gen1})
rec("R1 中途写入失败映射为结构化退出码", "WF_PERSISTENCE_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PERSISTENCE_FAILED")
record = json.load(open(os.path.join(dir1, "task.json")))
pending = record.get("action") or {}
rec("R1 失败后动作留在未完成态", "kind=baseline.apply 且 state!=done",
    f"kind={pending.get('kind')} state={pending.get('state')}",
    pending.get("kind") == "baseline.apply" and pending.get("state") != "done")
first_action = pending.get("id")
files3 = [{"path": ".wf/spec/first.md", "content": "# different\n", "before": None},
          {"path": ".wf/spec/blocked-dir/x.md", "content": "# different\n", "before": None}]
json.dump({"files": files3,
           "approval": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                        "subject": "baseline proposal r1", "choice": "approve",
                        "object_digest": _pd(files3), "reason": "R1 用例"}},
          open("/tmp/r12_proposal_other.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", "/tmp/r12_proposal_other.json", "--json"],
                    {"generation": gen1})
rec("R1 不同提案不得覆盖未完成动作", "WF_ACTION_INCOMPLETE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_ACTION_INCOMPLETE")
os.chmod(os.path.join(F, ".wf/spec/blocked-dir"), 0o755)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", "/tmp/r12_proposal_mid.json", "--json"],
                    {"generation": gen1})
rec("R1 同提案重入续做成功", "WF_OK 且两份文件都在",
    f"{(payload or {}).get('code')} first={os.path.exists(os.path.join(F, '.wf/spec/first.md'))} second={os.path.exists(os.path.join(F, '.wf/spec/blocked-dir/x.md'))}",
    rc == 0 and os.path.exists(os.path.join(F, ".wf/spec/first.md")) and os.path.exists(os.path.join(F, ".wf/spec/blocked-dir/x.md")))
record = json.load(open(os.path.join(dir1, "task.json")))
finished = record.get("action") or {}
rec("R1 接续复用同一动作", "action.id 与失败时一致且 state=done",
    f"same={finished.get('id') == first_action} state={finished.get('state')}",
    finished.get("id") == first_action and finished.get("state") == "done")
wf(["task-pause", "--task", task1, "--reason", "R1 收尾", "--json"], {"generation": gen1})
wf(["writer", "release", "--json"], {"generation": gen1})

# ---------------- R1-b：spec-update 整批预校验 ----------------
clean()
task2, gen2, dir2, d2 = make_task("R1 spec 整批", [".wf/spec/**"], "sess-R13")
approve(task2, d2, gen2, "sess-R13")
wf(["task-start", "--task", task2, "--json"], {"generation": gen2}, "sess-R13")
rule = '''---
schema_version: 1
paths: ["src/x.py"]
status: "active"
verified_at: "2026-11-03"
author: "ai"
counterexample: "x 未校验入参"
---

# 校验约定

入参必须先校验。
'''
changes = [{"operation": "add", "new_paths": [".wf/spec/rules/new-one.md"], "content": rule},
           {"operation": "delete", "old_paths": [".wf/spec/rules/does-not-exist.md"],
            "reference_dispositions": []}]
json.dump(changes, open("/tmp/r12_spec_bad.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["spec-update", "--task", task2, "--changes", "/tmp/r12_spec_bad.json", "--json"],
                    {"generation": gen2}, "sess-R13")
rec("R1 spec 整批校验拦截", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R1 spec 拦截时零写入", "new-one.md 不存在",
    os.path.exists(os.path.join(F, ".wf/spec/rules/new-one.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/rules/new-one.md")))
index_text = open(os.path.join(F, ".wf/spec/index.md"), encoding="utf-8").read()
rec("R1 spec 拦截时索引不变", "index 不含 new-one.md", "new-one.md" in index_text, "new-one.md" not in index_text)
wf(["task-pause", "--task", task2, "--reason", "R1 收尾", "--json"], {"generation": gen2}, "sess-R13")
wf(["writer", "release", "--json"], {"generation": gen2}, "sess-R13")

# ---------------- R2：confirm-executor 交互闸门 ----------------
clean()
home = os.path.expanduser("~/.wf/interpreters.json")
backup = open(home, encoding="utf-8").read() if os.path.exists(home) else None
config_path = os.path.join(F, ".wf/project-config.json")
config = json.load(open(config_path))
config["python_executable"] = "/usr/bin/python3"
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
baseline = os.path.join(F, ".wf/baseline.md")
text = open(baseline, encoding="utf-8").read()
if "python_executable" not in text:
    text += "\npython_executable: /usr/bin/python3\n"
    open(baseline, "w", encoding="utf-8").write(text)
clean()


def run_confirm(stdin_kind, answer=None):
    args = ["/usr/bin/python3", WF, "confirm-executor", "--scope", "project"]
    if stdin_kind == "pipe":
        return subprocess.run(args, cwd=F, capture_output=True, text=True, input=(answer or "") + "\n")
    master, slave = pty.openpty()
    proc = subprocess.Popen(args, cwd=F, stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    os.close(slave)
    time.sleep(0.6)
    if answer:
        os.write(master, (answer + "\n").encode())
    out = proc.communicate(timeout=60)[0]
    os.close(master)
    return subprocess.CompletedProcess(args, proc.returncode, out, "")


def recorded_count():
    data = json.load(open(home)) if os.path.exists(home) else {"interpreters": []}
    return len(data.get("interpreters") or [])


before = recorded_count()
pipe = run_confirm("pipe", "yes")
rec("R2 非 TTY 拒绝写确认记录", "exit=2 且 WF_SEMANTIC_DECISION",
    f"rc={pipe.returncode} code={'WF_SEMANTIC_DECISION' in pipe.stdout}",
    pipe.returncode == 2 and "WF_SEMANTIC_DECISION" in pipe.stdout)
rec("R2 非 TTY 未写记录", f"记录条数仍为 {before}", recorded_count(), recorded_count() == before)
pty_no = run_confirm("pty", "no")
rec("R2 TTY 下拒绝确认词不写记录", "非零退出且未写",
    f"rc={pty_no.returncode} count={recorded_count()}",
    pty_no.returncode != 0 and recorded_count() == before)
pty_yes = run_confirm("pty", "yes")
rec("R2 TTY 下确认词写入记录", f"退出 0 且记录 +1",
    f"rc={pty_yes.returncode} count={recorded_count()}",
    pty_yes.returncode == 0 and recorded_count() == before + 1)

if backup is not None:
    open(home, "w").write(backup)
else:
    os.remove(home)

json.dump(results, open("/tmp/r1r2_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
