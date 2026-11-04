#!/usr/bin/env python3
"""CP5 / B3 崩溃点、B4 dedupe 双扣、B5 spec 拆分（F1）。"""
import hashlib, json, os, signal, subprocess, sys, time
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
WF = os.path.join(F, ".wf/bin/wf.py")
results = []
AT = "2026-11-03T14:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-G1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "CP5 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def make_task(title, touch, sid, verifications=None, acceptance=None):
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


def approve(task_id, digest, gen, sid):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/cp5_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/cp5_notes2.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- B4 / dedupe 双扣 ----------------
config_path = os.path.join(F, ".wf/project-config.json")
config = json.load(open(config_path))
config["debug_repeat_threshold"] = 2
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
clean()

task_b4, gen_b4, dir_b4, d_b4 = make_task(
    "CP5 dedupe 双扣", ["src/b4.txt"],
    "sess-G1",
    verifications=[{"id": "v1", "invocation": {"kind": "argv", "argv": [
        "/usr/bin/python3", "-c",
        "import sys; sys.exit(0 if open('src/b4.txt').read().strip()=='ok' else 1)"]},
        "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
    acceptance=[{"id": "a1", "statement": "内容为 ok", "verification_ids": ["v1"]}])
approve(task_b4, d_b4, gen_b4, "sess-G1")
open(os.path.join(F, "src/b4.txt"), "w").write("bad\n")
wf(["task-start", "--task", task_b4, "--json"], {"generation": gen_b4}, "sess-G1")
wf(["task-check", "--task", task_b4, "--review-notes", NOTES, "--json"], {"generation": gen_b4}, "sess-G1")
open(os.path.join(F, "src/b4.txt"), "w").write("ok\n")
rc, payload, _ = wf(["task-check", "--task", task_b4, "--review-notes", NOTES, "--json"],
                    {"generation": gen_b4}, "sess-G1")
rec("B4 重检通过（历史 1 次失败）", "pass", (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(dir_b4, "task.json")))
failed_check = [c["id"] for c in record["check_history"] if c["result"] == "fail"][0]
declare1 = dfile("/tmp/cp5_b4_decl1.json", [dec(
    f"debug-declaration:v1:count=2:dedupe={failed_check}/v1:evidence=handoff", "declare", d_b4)])
wf(["task-check", "--task", task_b4, "--decision", declare1, "--review-notes", NOTES, "--json"],
   {"generation": gen_b4}, "sess-G1")
declare2 = dfile("/tmp/cp5_b4_decl2.json", [dec(
    f"debug-declaration:v1:count=1:dedupe={failed_check}/v1", "declare", d_b4)])
rc, payload, _ = wf(["task-check", "--task", task_b4, "--decision", declare2, "--review-notes", NOTES, "--json"],
                    {"generation": gen_b4}, "sess-G1")
rec("B4 同一失败事件重复计入被拒", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
wf(["task-knowledge", "--task", task_b4, "--decision", "no-update", "--json"], {"generation": gen_b4}, "sess-G1")
rc, payload, _ = wf(["archive", "--task", task_b4, "--decision",
                     dfile("/tmp/cp5_b4_arch.json", [dec(f"finish {task_b4}", "finish", d_b4),
                                                     dec("src/b4.txt", "commit", d_b4)]), "--json"],
                    {"generation": gen_b4}, "sess-G1")
facts = (payload or {}).get("facts", {})
pending = facts.get("unruled_debug_multiples") or []
rec("B4 双扣后合并累计=2（1+2-1）", "WF_SEMANTIC_DECISION 且 merged=2",
    f"{(payload or {}).get('code')} merged={(pending[0].get('merged') if pending else None)}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and pending and pending[0].get("merged") == 2)
config.pop("debug_repeat_threshold", None)
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
wf(["task-pause", "--task", task_b4, "--reason", "CP5 收尾", "--json"], {"generation": gen_b4}, "sess-G1")
wf(["writer", "release", "--json"], {"generation": gen_b4}, "sess-G1")

# ---------------- B5 / spec 拆分（add + delete 组合） ----------------
clean()
task_b5, gen_b5, dir_b5, d_b5 = make_task("CP5 spec 拆分", [".wf/spec/**"], "sess-G2")
approve(task_b5, d_b5, gen_b5, "sess-G2")
wf(["task-start", "--task", task_b5, "--json"], {"generation": gen_b5}, "sess-G2")
rule = '''---
schema_version: 1
paths: ["src/calc.py"]
status: "active"
verified_at: "2026-11-03"
author: "ai"
counterexample: "未区分纯函数与有副作用的辅助函数"
---

# calc 约定

## 约定

add 必须保持纯函数。
'''
change1 = [{"operation": "add", "new_paths": [".wf/spec/rules/combined.md"], "content": rule}]
json.dump(change1, open("/tmp/cp5_b5_add.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_b5, "--changes", "/tmp/cp5_b5_add.json", "--json"],
                    {"generation": gen_b5}, "sess-G2")
rec("B5 建被拆分条目", "pass", (payload or {}).get("code"), rc == 0)
wf(["task-curate", "--task", task_b5, "--spec", ".wf/spec/rules/combined.md",
    "--purpose", "拆分前引用", "--json"], {"generation": gen_b5}, "sess-G2")
split = [{"operation": "add", "new_paths": [".wf/spec/rules/pure.md"], "content": rule.replace("# calc 约定", "# 纯函数约定")},
         {"operation": "add", "new_paths": [".wf/spec/rules/effects.md"], "content": rule.replace("# calc 约定", "# 副作用约定")},
         {"operation": "delete", "old_paths": [".wf/spec/rules/combined.md"],
          "reference_dispositions": [{"task_id": task_b5, "path": ".wf/spec/rules/combined.md",
                                      "released": {"decision": {"source": "human (test)", "at": AT,
                                                                "subject": "release .wf/spec/rules/combined.md",
                                                                "choice": "解除依赖",
                                                                "reason": "拆分为 pure/effects 两条"}},
                                      "replacement": ".wf/spec/rules/pure.md"}]}]
json.dump(split, open("/tmp/cp5_b5_split.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["spec-update", "--task", task_b5, "--changes", "/tmp/cp5_b5_split.json", "--json"],
                    {"generation": gen_b5}, "sess-G2")
applied = (payload or {}).get("facts", {}).get("applied") or []
index_text = open(os.path.join(F, ".wf/spec/index.md"), encoding="utf-8").read()
rec("B5 拆分应用", "3 条变更且原文件移除",
    f"{(payload or {}).get('code')} applied={len(applied)} old_gone={not os.path.exists(os.path.join(F, '.wf/spec/rules/combined.md'))} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:200]}",
    rc == 0 and len(applied) == 3 and not os.path.exists(os.path.join(F, ".wf/spec/rules/combined.md")))
rec("B5 索引同步新条目、移除旧条目", "index 含 pure/effects、不含 combined",
    f"pure={'pure.md' in index_text} effects={'effects.md' in index_text} combined={'combined.md' in index_text}",
    "pure.md" in index_text and "effects.md" in index_text and "combined.md" not in index_text)
wf(["task-pause", "--task", task_b5, "--reason", "CP5 收尾", "--json"], {"generation": gen_b5}, "sess-G2")
wf(["writer", "release", "--json"], {"generation": gen_b5}, "sess-G2")

# ---------------- B3 / 崩溃点：归档提交后进程被杀 ----------------
clean()
task_b3, gen_b3, dir_b3, d_b3 = make_task("CP5 崩溃点", ["src/b3.txt"], "sess-G3")
approve(task_b3, d_b3, gen_b3, "sess-G3")
open(os.path.join(F, "src/b3.txt"), "w").write("b3\n")
wf(["task-start", "--task", task_b3, "--json"], {"generation": gen_b3}, "sess-G3")
wf(["task-check", "--task", task_b3, "--review-notes", NOTES, "--json"], {"generation": gen_b3}, "sess-G3")
wf(["task-knowledge", "--task", task_b3, "--decision", "no-update", "--json"], {"generation": gen_b3}, "sess-G3")
archive_decision = dfile("/tmp/cp5_b3_arch.json", [dec(f"finish {task_b3}", "finish", d_b3),
                                                   dec("src/b3.txt", "commit", d_b3)])
envelope = json.dumps({"session": {"provider": "host",
                                   "identity": {"host_id": "dsh", "session_id": "sess-G3"},
                                   "instance_id": wfdrive._binding_instance("sess-G3"),
                                   "activation": {"enabled": True, "start_source": "test", "enabled_at": AT}},
                       "inputs": {"generation": gen_b3}})
proc = subprocess.Popen(["/usr/bin/python3", WF, "archive", "--task", task_b3,
                         "--decision", archive_decision, "--json"],
                        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
proc.stdin.write(envelope.encode()); proc.stdin.close()
killed = False
deadline = time.time() + 15
while time.time() < deadline and proc.poll() is None:
    subjects = subprocess.run(["git", "log", "-3", "--format=%s"], cwd=F,
                              capture_output=True, text=True).stdout
    if f"wf: archive {task_b3}" in subjects:
        try:
            os.kill(proc.pid, signal.SIGKILL)
            killed = True
        except ProcessLookupError:
            pass
        break
    time.sleep(0.002)
proc.wait()
rec("B3 归档提交后被强杀", "进程被 SIGKILL（提交已落地、结果未报告）",
    f"killed={killed} rc={proc.returncode}",
    killed and proc.returncode == -signal.SIGKILL)
rc, payload, _ = wf(["archive", "--task", task_b3, "--decision", archive_decision, "--json"],
                    {"generation": gen_b3}, "sess-G3")
facts = (payload or {}).get("facts", {})
persisted = (facts.get("archive_persisted") or {}).get("persisted")
commits = subprocess.run(["git", "log", "--format=%s"], cwd=F,
                         capture_output=True, text=True).stdout.count(f"wf: archive {task_b3}")
rec("B3 独立进程重入报告已持久化", "WF_OK 且 persisted=true、不重复归档",
    f"{(payload or {}).get('code')} persisted={persisted} commits={commits}",
    rc == 0 and persisted is True and commits == 1)
wf(["writer", "release", "--json"], {"generation": gen_b3}, "sess-G3")

json.dump(results, open("/tmp/cp5_b345_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
