#!/usr/bin/env python3
"""第四轮 R17–R24 用例（隔离夹具）。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks

F = wfdrive.FIX
results = []
AT = "2026-11-03T22:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-U1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64, **extra):
    base = {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R17-R24 用例"}
    base.update(extra)
    return base


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-U1", prd_extra=None):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    if prd_extra:
        block.update(prd_extra)
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid="sess-U1", extra=None):
    inputs = {"generation": gen, "complexity": "light",
              "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}
    if extra:
        inputs.update(extra)
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r17_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"], inputs, sid)


NOTES = "/tmp/r17_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

RULE = '''---
schema_version: 1
paths: ["src/**"]
status: "active"
verified_at: "2026-11-03"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''

# ---------------- R19：同批改名碰撞 ----------------
clean()
task19, gen19, dir19, d19 = make_task("R19 改名碰撞", [".wf/spec/**"], "sess-U19")
approve(task19, d19, gen19, "sess-U19")
wf(["task-start", "--task", task19, "--json"], {"generation": gen19}, "sess-U19")
for name in ("a", "c"):
    change = dfile(f"/tmp/r19_{name}.json",
                   [{"operation": "add", "new_paths": [f".wf/spec/{name}.md"], "content": RULE}])
    wf(["spec-update", "--task", task19, "--changes", change, "--json"], {"generation": gen19}, "sess-U19")
batch = dfile("/tmp/r19_conflict.json",
              [{"operation": "rename", "old_paths": [".wf/spec/a.md"], "new_paths": [".wf/spec/b.md"]},
               {"operation": "rename", "old_paths": [".wf/spec/c.md"], "new_paths": [".wf/spec/b.md"]}])
rc, payload, _ = wf(["spec-update", "--task", task19, "--changes", batch, "--json"], {"generation": gen19}, "sess-U19")
rec("R19 同批同目标被拒", "WF_TARGET_COLLISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_TARGET_COLLISION")
rec("R19 拒绝时零写入", "a.md 与 c.md 都还在",
    f"a={os.path.exists(os.path.join(F, '.wf/spec/a.md'))} c={os.path.exists(os.path.join(F, '.wf/spec/c.md'))}",
    os.path.exists(os.path.join(F, ".wf/spec/a.md")) and os.path.exists(os.path.join(F, ".wf/spec/c.md")))
wf(["task-pause", "--task", task19, "--reason", "R19 收尾", "--json"], {"generation": gen19}, "sess-U19")
wf(["writer", "release", "--json"], {"generation": gen19}, "sess-U19")

# ---------------- R17：spec-update 动作授权 ----------------
clean()
task17, gen17, dir17, d17 = make_task("R17 spec 授权", ["src/**", ".wf/spec/**"], "sess-U17")
approve(task17, d17, gen17, "sess-U17")
early = dfile("/tmp/r17_early.json", [{"operation": "add", "new_paths": [".wf/spec/early.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task17, "--changes", early, "--json"], {"generation": gen17}, "sess-U17")
rec("R17 未开工不得写 spec", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
open(os.path.join(F, "src/r17.txt"), "w").write("r17\n")
wf(["task-start", "--task", task17, "--json"], {"generation": gen17}, "sess-U17")
wf(["task-pause", "--task", task17, "--reason", "R17 暂停", "--json"], {"generation": gen17}, "sess-U17")
rc, payload, _ = wf(["spec-update", "--task", task17, "--changes", early, "--json"], {"generation": gen17}, "sess-U17")
rec("R17 暂停任务不得写 spec", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
rec("R17 拒绝时零写入", "early.md 不存在", os.path.exists(os.path.join(F, ".wf/spec/early.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/early.md")))
wf(["task-resume", "--task", task17, "--json"], {"generation": gen17}, "sess-U17")
rc, payload, _ = wf(["spec-update", "--task", task17, "--changes", early, "--json"], {"generation": gen17}, "sess-U17")
rec("R17 恢复后可写", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-pause", "--task", task17, "--reason", "R17 收尾", "--json"], {"generation": gen17}, "sess-U17")
wf(["writer", "release", "--json"], {"generation": gen17}, "sess-U17")

# R26：spec 目标须在批准触碰面内
clean()
task17b, gen17b, dir17b, d17b = make_task("R17b spec 触碰面", ["src/**"], "sess-U17b")
approve(task17b, d17b, gen17b, "sess-U17b")
open(os.path.join(F, "src/r17b.txt"), "w").write("r17b\n")
rc_s, start_b, _ = wf(["task-start", "--task", task17b, "--json"], {"generation": gen17b}, "sess-U17b")
rec("R26 准备：开工", "WF_OK", (start_b or {}).get("code"), rc_s == 0)
out_of_face = dfile("/tmp/r17_out.json", [{"operation": "add", "new_paths": [".wf/spec/outside-face.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task17b, "--changes", out_of_face, "--json"],
                    {"generation": gen17b}, "sess-U17b")
rec("R26 spec 目标不在触碰面内", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
rec("R26 拒绝时零写入", "outside-face.md 不存在", os.path.exists(os.path.join(F, ".wf/spec/outside-face.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/outside-face.md")))
wf(["task-pause", "--task", task17b, "--reason", "R26 收尾", "--json"], {"generation": gen17b}, "sess-U17b")
wf(["writer", "release", "--json"], {"generation": gen17b}, "sess-U17b")

json.dump(results, open("/tmp/r17r24_results.json", "w"), ensure_ascii=False, indent=2)
print("part1", sum(1 for r in results if r["pass"]), "/", len(results))

# ---------------- R20：改名不改归档引用 ----------------
clean()
task20a, gen20a, dir20a, d20a = make_task("R20 归档引用", [".wf/spec/**"], "sess-U20a")
approve(task20a, d20a, gen20a, "sess-U20a")
wf(["task-start", "--task", task20a, "--json"], {"generation": gen20a}, "sess-U20a")
old_rule = RULE.replace("paths: [\"src/**\"]", "paths: [\"src/old/**\"]")
add20 = dfile("/tmp/r20_add.json", [{"operation": "add", "new_paths": [".wf/spec/old.md"], "content": old_rule}])
wf(["spec-update", "--task", task20a, "--changes", add20, "--json"], {"generation": gen20a}, "sess-U20a")
wf(["task-curate", "--task", task20a, "--spec", ".wf/spec/old.md", "--purpose", "旧规则", "--json"],
   {"generation": gen20a}, "sess-U20a")
wf(["spec", "--file", ".wf/spec/old.md", "--json"], {"generation": gen20a}, "sess-U20a")
rc, payload, _ = wf(["task-check", "--task", task20a, "--review-notes", NOTES, "--json"],
                    {"generation": gen20a}, "sess-U20a")
json.dump((payload or {}).get("facts"), open("/tmp/r20_facts.json", "w"), ensure_ascii=False)
rec("R20 准备：Check", "WF_OK", f"{(payload or {}).get('code')}", rc == 0)
wf(["task-knowledge", "--task", task20a, "--decision", "no-update", "--json"], {"generation": gen20a}, "sess-U20a")
rc, payload, _ = wf(["archive", "--task", task20a, "--decision",
                     dfile("/tmp/r20_arch.json", [dec(f"finish {task20a}", "finish", d20a),
                                                  dec(".wf/spec/**", "commit", d20a)]),
                     "--json"], {"generation": gen20a}, "sess-U20a")
rec("R20 准备：归档任务", "WF_OK", f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:300]}", rc == 0)
wf(["writer", "release", "--json"], {"generation": gen20a}, "sess-U20a")
archived_dir = wf_tasks.task_dir(F, task20a)
before = open(os.path.join(archived_dir, "task.json"), encoding="utf-8").read()

clean()
task20b, gen20b, dir20b, d20b = make_task("R20 改名", [".wf/spec/**"], "sess-U20b")
approve(task20b, d20b, gen20b, "sess-U20b")
wf(["task-start", "--task", task20b, "--json"], {"generation": gen20b}, "sess-U20b")
rename20 = dfile("/tmp/r20_rename.json", [{"operation": "rename", "old_paths": [".wf/spec/old.md"],
                                           "new_paths": [".wf/spec/new.md"]}])
rc, payload, _ = wf(["spec-update", "--task", task20b, "--changes", rename20, "--json"],
                    {"generation": gen20b}, "sess-U20b")
after = open(os.path.join(archived_dir, "task.json"), encoding="utf-8").read()
rec("R20 改名成功", "WF_OK", (payload or {}).get("code"), rc == 0)
rec("R20 归档任务记录未被改写", "task.json 内容不变", before == after, before == after)
rec("R20 归档仍引用旧路径", ".wf/spec/old.md 仍在归档策展里",
    ".wf/spec/old.md" in json.loads(after).get("curation", [{}])[0].get("path", ""),
    ".wf/spec/old.md" in after)
wf(["task-pause", "--task", task20b, "--reason", "R20 收尾", "--json"], {"generation": gen20b}, "sess-U20b")
wf(["writer", "release", "--json"], {"generation": gen20b}, "sess-U20b")

# ---------------- R18：到期与策展并集 ----------------
clean()
rule18 = RULE.replace("src/**", "lib/**")
expired = rule18.replace('verified_at: "2026-11-03"', 'verified_at: "2000-01-01"')
nomatch = rule18.replace('paths: ["lib/**"]', 'paths: ["nope/**"]').replace('verified_at: "2026-11-03"', 'verified_at: "2000-01-01"')
task18, gen18, dir18, d18 = make_task("R18 核实", ["lib/**", ".wf/spec/**"], "sess-U18")
approve(task18, d18, gen18, "sess-U18")
wf(["task-start", "--task", task18, "--json"], {"generation": gen18}, "sess-U18")
add18 = dfile("/tmp/r18_add.json",
              [{"operation": "add", "new_paths": [".wf/spec/expired.md"], "content": expired},
               {"operation": "add", "new_paths": [".wf/spec/nomatch.md"], "content": nomatch}])
wf(["spec-update", "--task", task18, "--changes", add18, "--json"], {"generation": gen18}, "sess-U18")
open(os.path.join(F, "lib/r18.txt"), "w") if os.path.isdir(os.path.join(F, "lib")) else None
wf(["task-curate", "--task", task18, "--spec", ".wf/spec/expired.md", "--purpose", "到期规则", "--json"],
   {"generation": gen18}, "sess-U18")
wf(["spec", "--file", ".wf/spec/expired.md", "--json"], {"generation": gen18}, "sess-U18")
rc, payload, _ = wf(["task-check", "--task", task18, "--review-notes", NOTES, "--json"],
                    {"generation": gen18}, "sess-U18")
needs = [item.get("reason") for item in (((payload or {}).get("facts") or {}).get("spec") or {}).get("needs") or []]
rec("R18 到期条目阻断", "WF_SPEC_INCOMPLETE 且 needs 含 expired",
    f"code={(payload or {}).get('code')} needs={needs}",
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE" and "expired" in needs)
wf(["task-curate", "--task", task18, "--spec", ".wf/spec/nomatch.md", "--purpose", "未被命中但已策展", "--json"],
   {"generation": gen18}, "sess-U18")
wf(["spec", "--file", ".wf/spec/nomatch.md", "--json"], {"generation": gen18}, "sess-U18")
rc, payload, _ = wf(["task-check", "--task", task18, "--decision",
                     dfile("/tmp/r18_dec.json", [dec(".wf/spec/expired.md", "passed", d18)]),
                     "--review-notes", NOTES, "--json"], {"generation": gen18}, "sess-U18")
spec_facts = ((payload or {}).get("facts") or {}).get("spec") or {}
rec("R18 策展未命中条目也参与判定", "curated 含 nomatch 且仍阻断",
    f"curated={spec_facts.get('curated')} code={(payload or {}).get('code')}",
    ".wf/spec/nomatch.md" in (spec_facts.get("curated") or [])
    and (payload or {}).get("code") == "WF_SPEC_INCOMPLETE")
rc, payload, _ = wf(["task-check", "--task", task18, "--decision",
                     dfile("/tmp/r18_dec2.json", [dec(".wf/spec/expired.md .wf/spec/nomatch.md", "passed", d18)]),
                     "--review-notes", NOTES, "--json"], {"generation": gen18}, "sess-U18")
rec("R18 人判覆盖后通过", "WF_OK", f"{(payload or {}).get('code')} spec={json.dumps(((payload or {}).get('facts') or {}).get('spec'), ensure_ascii=False)[:160]}", rc == 0)
wf(["task-pause", "--task", task18, "--reason", "R18 收尾", "--json"], {"generation": gen18}, "sess-U18")
wf(["writer", "release", "--json"], {"generation": gen18}, "sess-U18")

json.dump(results, open("/tmp/r17r24_results.json", "w"), ensure_ascii=False, indent=2)
print("part2", sum(1 for r in results if r["pass"]), "/", len(results))

# ---------------- R21：验证期间新增范围外文件 ----------------
clean()
ver21 = [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c",
          "open('rogue.txt','w').write('rogue')"]},
          "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]
os.makedirs(os.path.join(F, "area21"), exist_ok=True)
task21, gen21, dir21, d21 = make_task("R21 结束前重算", ["area21/**"], "sess-U21")
approve(task21, d21, gen21, "sess-U21")
open(os.path.join(F, "area21/r21.txt"), "w").write("r21\n")
wf(["task-start", "--task", task21, "--json"], {"generation": gen21}, "sess-U21")
probe = json.load(open(os.path.join(dir21, "task.json")))
probe_block = json.loads(open(os.path.join(dir21, "prd.md"), encoding="utf-8").read().split("```json")[1].split("```")[0])
probe_block["verifications"] = ver21
prd21 = f"# R21 结束前重算\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(probe_block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(dir21, "prd.md"), "w", encoding="utf-8").write(prd21)
d21b = "sha256:" + hashlib.sha256(prd21.encode()).hexdigest()
wf(["task-replan", "--task", task21, "--json"], {"generation": gen21}, "sess-U21")
approve(task21, d21b, gen21, "sess-U21")
rc, payload, _ = wf(["task-check", "--task", task21, "--review-notes", NOTES, "--json"],
                    {"generation": gen21}, "sess-U21")
rec("R21 验证期间新增范围外文件", "WF_CHECK_STALE 或 WF_WORKSPACE_UNRESOLVED",
    f"{(payload or {}).get('code')}",
    (payload or {}).get("code") in ("WF_CHECK_STALE", "WF_WORKSPACE_UNRESOLVED"))
if os.path.exists(os.path.join(F, "rogue.txt")):
    os.remove(os.path.join(F, "rogue.txt"))
wf(["task-pause", "--task", task21, "--reason", "R21 收尾", "--json"], {"generation": gen21}, "sess-U21")
wf(["writer", "release", "--json"], {"generation": gen21}, "sess-U21")

# ---------------- R22：TDD 证据结构 ----------------
clean()
tdd_block = {"tdd": True}
os.makedirs(os.path.join(F, "area22"), exist_ok=True)
task22, gen22, dir22, d22 = make_task("R22 TDD 结构", ["area22/**"], "sess-U22", prd_extra=tdd_block)
approve(task22, d22, gen22, "sess-U22", extra={"tdd": True})
open(os.path.join(F, "area22/r22.txt"), "w").write("r22\n")
rc_s22, start22, _ = wf(["task-start", "--task", task22, "--json"], {"generation": gen22}, "sess-U22")
rec("R22 准备：开工", "WF_OK", (start22 or {}).get("code"), rc_s22 == 0)
bad_notes = "/tmp/r22_notes_bad.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"},
           "tdd_evidence": {"note": "no red/green references"}}, open(bad_notes, "w"))
rc, payload, _ = wf(["task-check", "--task", task22, "--review-notes", bad_notes, "--json"],
                    {"generation": gen22}, "sess-U22")
rec("R22 非结构化证据不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
good = {"assertion": "add 支持变长加数", "red_reason": "旧实现不接受第三个加数",
        "red_command_ref": "v1", "green_command_ref": "v2",
        "properties": "可红、确定性、快速、可无人执行"}
good_notes = "/tmp/r22_notes_good.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"},
           "tdd_evidence": good}, open(good_notes, "w"))
block = json.loads(open(os.path.join(dir22, "prd.md"), encoding="utf-8").read().split("```json")[1].split("```")[0])
block["tdd"] = True
block["verifications"] = [
    {"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c",
      "import sys; sys.exit(0 if open('area22/r22.txt').read().strip()=='ok' else 1)"]},
     "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"},
    {"id": "v2", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(2)"]},
     "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]
prd22 = f"# R22 TDD 结构\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(dir22, "prd.md"), "w", encoding="utf-8").write(prd22)
d22b = "sha256:" + hashlib.sha256(prd22.encode()).hexdigest()
wf(["task-replan", "--task", task22, "--json"], {"generation": gen22}, "sess-U22")
approve(task22, d22b, gen22, "sess-U22", extra={"tdd": True})
# 制造历史红运行：文件内容不满足 v1 → Check fail
open(os.path.join(F, "area22/r22.txt"), "w").write("bad\n")
rc_fail, fail_payload, _ = wf(["task-check", "--task", task22, "--review-notes", good_notes, "--json"],
                              {"generation": gen22}, "sess-U22")
rec("R22 准备：历史红运行", "WF_CHECK_FAILED", (fail_payload or {}).get("code"),
    (fail_payload or {}).get("code") == "WF_CHECK_FAILED")
open(os.path.join(F, "area22/r22.txt"), "w").write("ok\n")
rc, payload, _ = wf(["task-check", "--task", task22, "--review-notes", good_notes, "--json"],
                    {"generation": gen22}, "sess-U22")
rec("R22 真实红→绿结构通过", "WF_OK", f"{(payload or {}).get('code')}", rc == 0)
same = {"assertion": "a", "red_reason": "r", "red_command_ref": "v2", "green_command_ref": "v2",
        "properties": "可红"}
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"},
           "tdd_evidence": same}, open("/tmp/r22_notes_same.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task22, "--review-notes", "/tmp/r22_notes_same.json", "--json"],
                    {"generation": gen22}, "sess-U22")
rec("R22 红绿同一条不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
wf(["task-pause", "--task", task22, "--reason", "R22 收尾", "--json"], {"generation": gen22}, "sess-U22")
wf(["writer", "release", "--json"], {"generation": gen22}, "sess-U22")

# ---------------- R23：归档提交失败后按既有授权续做 ----------------
clean()
os.makedirs(os.path.join(F, "area23"), exist_ok=True)
task23, gen23, dir23, d23 = make_task("R23 归档续做", ["area23/**"], "sess-U23")
approve(task23, d23, gen23, "sess-U23")
open(os.path.join(F, "area23/r23.txt"), "w").write("r23\n")
wf(["task-start", "--task", task23, "--json"], {"generation": gen23}, "sess-U23")
wf(["task-check", "--task", task23, "--review-notes", NOTES, "--json"], {"generation": gen23}, "sess-U23")
wf(["task-knowledge", "--task", task23, "--decision", "no-update", "--json"], {"generation": gen23}, "sess-U23")
rc, payload, _ = wf(["archive", "--task", task23, "--decision",
                     dfile("/tmp/r23_arch.json", [dec(f"finish {task23}", "finish", d23),
                                                  dec("area23/**", "commit", d23)]), "--json"],
                    {"generation": gen23}, "sess-U23")
rec("R23 准备：正常归档", "WF_OK", (payload or {}).get("code"), rc == 0)
# 回退记录组提交，制造「已移动、未持久化」状态
subprocess.run(["git", "reset", "-q", "--mixed", "HEAD~1"], cwd=F, capture_output=True)
subprocess.run(["git", "checkout", "-q", "--", "."], cwd=F, capture_output=True)
archived = wf_tasks.task_dir(F, task23)
persisted_before = wf_tasks.archive_persisted(F, json.load(open(os.path.join(archived, "task.json"))))
rc_norights, no_rights, _ = wf(["archive", "--task", task23, "--decision",
                                 dfile("/tmp/r23_arch2.json", [dec(f"finish {task23}", "finish", d23)]), "--json"],
                                {"generation": gen23}, "sess-U23")
wf(["writer", "release", "--json"], {"generation": gen23}, "sess-U23")
rc_busy, busy_payload, _ = wf(["archive", "--task", task23, "--decision",
                                dfile("/tmp/r23_arch2.json", [dec(f"finish {task23}", "finish", d23)]), "--json"],
                               {"generation": gen23}, "sess-U23")
rec("R23 无写权不得续做", "WF_WRITER_BUSY", (busy_payload or {}).get("code"),
    (busy_payload or {}).get("code") == "WF_WRITER_BUSY")
wf(["writer", "acquire", "--task", task23, "--json"], {"generation": gen23}, "sess-U23")
rc, payload, _ = wf(["archive", "--task", task23, "--decision",
                     dfile("/tmp/r23_arch2.json", [dec(f"finish {task23}", "finish", d23)]), "--json"],
                    {"generation": gen23}, "sess-U23")
facts = (payload or {}).get("facts", {})
rec("R23 未持久化状态已构造", "persisted=False", persisted_before.get("persisted"),
    persisted_before.get("persisted") is False)
rec("R23 重入按既有授权续做提交", "WF_OK 且 persisted=true 且标记续做",
    f"{(payload or {}).get('code')} persisted={(facts.get('archive_persisted') or {}).get('persisted')} resumed={(facts.get('archive_persisted') or {}).get('resumed_commit')}",
    (payload or {}).get("code") == "WF_OK"
    and (facts.get("archive_persisted") or {}).get("persisted") is True
    and (facts.get("archive_persisted") or {}).get("resumed_commit") is True)
wf(["writer", "release", "--json"], {"generation": gen23}, "sess-U23")

# ---------------- R24：放弃时的真实处置 ----------------
clean()
os.makedirs(os.path.join(F, "area24"), exist_ok=True)
task24, gen24, dir24, d24 = make_task("R24 放弃处置", ["area24/**"], "sess-U24")
approve(task24, d24, gen24, "sess-U24")
open(os.path.join(F, "area24/r24.txt"), "w").write("r24\n")
wf(["task-start", "--task", task24, "--json"], {"generation": gen24}, "sess-U24")
disp = {"changes": [{"object": "area24/r24.txt", "decision_ref": AT, "reason": "保留现状"}], "targets": [], "pending": []}
json.dump(disp, open("/tmp/r24_disp.json", "w"), ensure_ascii=False)
stop_only = dfile("/tmp/r24_stop.json", [dec(f"stop {task24}", "abandon", d24)])
rc, payload, _ = wf(["task-abandon", "--task", task24, "--decision", stop_only,
                     "--disposition", "/tmp/r24_disp.json", "--json"], {"generation": gen24}, "sess-U24")
rec("R24 无授权且未处置不得结案", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
record = json.load(open(os.path.join(dir24, "task.json")))
rec("R24 未结案时不写异常终态", "terminal 为空且仍未归档",
    f"terminal={record.get('terminal')} status={record.get('status')}",
    not record.get("terminal") and record.get("status") != "archived")
with_grant = dfile("/tmp/r24_grant.json", [dec(f"stop {task24}", "abandon", d24),
                                           dec("area24/**", "commit", d24)])
rc, payload, _ = wf(["task-abandon", "--task", task24, "--decision", with_grant,
                     "--disposition", "/tmp/r24_disp.json", "--json"], {"generation": gen24}, "sess-U24")
committed = subprocess.run(["git", "log", "-2", "--name-only", "--format="], cwd=F,
                           capture_output=True, text=True).stdout
rec("R24 有授权时实际提交并结案", "WF_OK 且改动已提交",
    f"{(payload or {}).get('code')} committed={'area24/r24.txt' in committed}",
    rc == 0 and "area24/r24.txt" in committed)

json.dump(results, open("/tmp/r17r24_results.json", "w"), ensure_ascii=False, indent=2)
print("total", sum(1 for r in results if r["pass"]), "/", len(results))
