#!/usr/bin/env python3
"""CP2（A2 等价链 / A3 activation / A13 阈值 / A14 Trellis 三档）回归用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-03T10:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-P1", activation=True):
    return wfdrive.run(args, inputs=inputs, sid=sid, activation=activation, show=False)



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def dec(subject, choice, digest="sha256:" + "0" * 64, reason="CP2 用例"):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": reason}


def decision_file(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def finish_task(task_id, gen, sid):
    wf(["task-pause", "--task", task_id, "--reason", "CP2 收尾", "--json"], {"generation": gen}, sid)
    wf(["writer", "release", "--json"], {"generation": gen}, sid)


def make_task(title, touch, verifications, acceptance, sid, body_note=""):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:400]); raise SystemExit(1)
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch, "acceptance": acceptance,
             "verifications": verifications}
    prd = f"# {title}\n\n## 说明\n\n{body_note or 'CP2 用例'}\n\n## 机读块\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid, extra=None):
    items = [dec("approve plan", "approve", digest)] + (extra or [])
    path = decision_file(f"/tmp/cp2_{task_id}_approve.json", items)
    return wf(["task-approve", "--task", task_id, "--decision", path, "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件纯函数", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/cp2_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))
V1 = {"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
      "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}

# ---------------- T1 / A3：activation 前置 ----------------
clean()
task1, gen1, dir1, d1 = make_task("CP2 A3 activation", ["src/p3.txt"], [V1],
                                  [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], "sess-P1")
approve(task1, d1, gen1, "sess-P1")
rc, payload, out = wf(["task-start", "--task", task1, "--json"], {"generation": gen1},
                      "sess-P1", activation=False)
rec("A3 缺 activation 的开工", "WF_NOT_ENABLED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_NOT_ENABLED" and rc == 1)
rc, payload, out = wf(["task-start", "--task", task1, "--json"], {"generation": gen1}, "sess-P1")
rec("A3 带 activation 的开工", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, out = wf(["status", "--json"], None, "sess-P1", activation=False)
rec("A3 只读查询无需 activation", "pass", (payload or {}).get("code"), rc == 0)
open(os.path.join(F, "src/p3.txt"), "w").write("p3\n")

# ---------------- T2 / A2：等价链归一 ----------------
check1 = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"], {"generation": gen1}, "sess-P1")
record1 = json.load(open(os.path.join(dir1, "task.json")))
anchor1 = record1["check"]["anchor"]["check_anchor"]
old_version = record1["plan"]["version"]
prd_path = os.path.join(dir1, "prd.md")
text = open(prd_path, encoding="utf-8").read()
open(prd_path, "w", encoding="utf-8").write(text.replace("CP2 用例", "CP2 用例（仅修错字）", 1))
rc, payload, out = approve(task1, d1, gen1, "sess-P1")
rec("A2 改错字后未接链即重批", "WF_APPROVAL_MISSING 或语义变化提示", (payload or {}).get("code"),
    (payload or {}).get("code") in ("WF_APPROVAL_MISSING", "WF_SEMANTIC_DECISION"))
# 用机械修订衔接
mech = decision_file("/tmp/cp2_mech.json", [dec(f"{old_version} -> 新版本（仅修错字）", "机械修订",
                                                d1, "只改正文错字，机读块未变")])
rc, payload, out = wf(["task-approve", "--task", task1, "--decision", mech, "--json"],
                      {"generation": gen1}, "sess-P1")
facts = (payload or {}).get("facts", {})
rec("A2 机械修订接链", "pass 且 normalized=approved",
    f"{(payload or {}).get('code')} norm={facts.get('normalized_version') == facts.get('approved_version')}",
    rc == 0 and facts.get("normalized_version") == facts.get("approved_version"))
record2 = json.load(open(os.path.join(dir1, "task.json")))
rec("A2 等价链已记录", "equivalences 长度 1", len(record2["plan"]["equivalences"]),
    len(record2["plan"]["equivalences"]) == 1)
check2 = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"], {"generation": gen1}, "sess-P1")
record3 = json.load(open(os.path.join(dir1, "task.json")))
anchor2 = record3["check"]["anchor"]["check_anchor"]
rec("A2 机械修订不改变锚点", "anchor 前后相同且重检通过",
    f"same={anchor1 == anchor2} rc={check2[0]}", anchor1 == anchor2 and check2[0] == 0)
finish_task(task1, gen1, "sess-P1")
# 语义变化必须被拒
clean()
task2, gen2, dir2, d2 = make_task("CP2 A2 语义变化", ["src/p2.txt"], [V1],
                                  [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}], "sess-P2")
approve(task2, d2, gen2, "sess-P2")
text2 = open(os.path.join(dir2, "prd.md"), encoding="utf-8").read()
open(os.path.join(dir2, "prd.md"), "w", encoding="utf-8").write(
    text2.replace('"statement": "文件存在"', '"statement": "文件存在且可读"'))
mech2 = decision_file("/tmp/cp2_mech2.json", [dec("旧 -> 新", "机械修订", d2, "改验收措辞")])
rc, payload, out = wf(["task-approve", "--task", task2, "--decision", mech2, "--json"],
                      {"generation": gen2}, "sess-P2")
rec("A2 语义变化拒绝机械修订", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
finish_task(task2, gen2, "sess-P2")

# ---------------- T3 / A13：项目阈值接线 ----------------
config_path = os.path.join(F, ".wf/project-config.json")
config = json.load(open(config_path))
config["debug_repeat_threshold"] = 2
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
clean()
task3, gen3, dir3, d3 = make_task("CP2 A13 阈值", ["src/p13.txt"],
                                  [{"id": "v1", "invocation": {"kind": "argv", "argv": [
                                      "/usr/bin/python3", "-c",
                                      "import sys; sys.exit(0 if open('src/p13.txt').read().strip()=='ok' else 1)"]},
                                    "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}],
                                  [{"id": "a1", "statement": "内容为 ok", "verification_ids": ["v1"]}], "sess-P3")
approve(task3, d3, gen3, "sess-P3")
open(os.path.join(F, "src/p13.txt"), "w").write("bad\n")
wf(["task-start", "--task", task3, "--json"], {"generation": gen3}, "sess-P3")
wf(["task-check", "--task", task3, "--review-notes", NOTES, "--json"], {"generation": gen3}, "sess-P3")
open(os.path.join(F, "src/p13.txt"), "w").write("ok\n")
rc, payload, out = wf(["task-check", "--task", task3, "--review-notes", NOTES, "--json"],
                      {"generation": gen3}, "sess-P3")
rec("A13 首次重检通过（历史 1 次失败）", "pass", (payload or {}).get("code"), rc == 0)
declare = decision_file("/tmp/cp2_declare.json", [dec("debug-declaration:v1:count=1:evidence=handoff", "declare", d3)])
wf(["task-check", "--task", task3, "--decision", declare, "--review-notes", NOTES, "--json"],
   {"generation": gen3}, "sess-P3")
wf(["task-knowledge", "--task", task3, "--decision", "no-update", "--json"], {"generation": gen3}, "sess-P3")
rc, payload, out = wf(["archive", "--task", task3, "--decision",
                       decision_file("/tmp/cp2_archive.json", [dec(f"finish {task3}", "finish", d3),
                                                               dec("src/p13.txt", "commit", d3)]),
                       "--json"], {"generation": gen3}, "sess-P3")
facts = (payload or {}).get("facts", {})
pending = facts.get("unruled_debug_multiples") or []
rec("A13 阈值 2 时合并累计 2 触发待决", "WF_SEMANTIC_DECISION 且 threshold=2",
    f"{(payload or {}).get('code')} threshold={pending[0].get('threshold') if pending else None}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and pending and pending[0].get("threshold") == 2)
config.pop("debug_repeat_threshold", None)
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
finish_task(task3, gen3, "sess-P3")

# ---------------- T4 / A14：Trellis 三档 ----------------
clean()
def enable():
    return wf(["enable", "--json"], None, "sess-P9")


os.makedirs(os.path.join(F, ".trellis"), exist_ok=True)
open(os.path.join(F, ".trellis", "README.md"), "w").write("residual\n")
rc, payload, out = enable()
rec("A14 仅数据线索", "pass（附警告）", f"{(payload or {}).get('code')} warnings={len((payload or {}).get('warnings') or [])}",
    rc == 0)

open(os.path.join(F, "AGENTS.md"), "w").write("# AGENTS\n\n<!-- TRELLIS:START -->\nmanaged\n<!-- TRELLIS:END -->\n")
rc, payload, out = enable()
rec("A14 托管块适用性未知", "needs_decision WF_SEMANTIC_DECISION", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)
os.remove(os.path.join(F, "AGENTS.md"))

os.makedirs(os.path.join(F, ".dsh"), exist_ok=True)
open(os.path.join(F, ".dsh", "hooks.json"), "w").write('{"hooks": [{"name": "trellis-sync"}]}')
rc, payload, out = enable()
rec("A14 当前宿主配置存在但未声明已加载 → 待核", "needs_decision WF_SEMANTIC_DECISION",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)
rc, payload, out = wf(["enable", "--json"], {"trellis_loaded": True}, "sess-P9")
rec("A14 声明本会话已加载 → 冲突阻断", "blocked WF_FLOW_CONFLICT", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_FLOW_CONFLICT" and rc == 1)
os.remove(os.path.join(F, ".dsh", "hooks.json"))

open(os.path.join(F, ".claude-settings"), "w").write("")
os.makedirs(os.path.join(F, ".claude"), exist_ok=True)
open(os.path.join(F, ".claude", "settings.json"), "w").write('{"hooks": [{"name": "trellis"}]}')
rc, payload, out = enable()
rec("A14 他宿主配置的适用性未知", "needs_decision WF_SEMANTIC_DECISION", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION" and rc == 2)
os.remove(os.path.join(F, ".claude", "settings.json"))
os.remove(os.path.join(F, ".claude-settings"))

json.dump(results, open("/tmp/cp2_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
