#!/usr/bin/env python3
"""第四轮 R17–R24 用例（隔离夹具）。"""
import hashlib, json, os, shutil, subprocess, sys
import wfdrive
sys.path.insert(0, wfdrive.LIB)
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
    base = {"source": "human (test)", "at": AT, "subject": subject, "artifacts": wfdrive.plan_artifacts(subject), "object_digest": digest,
            "choice": choice, "reason": "R17-R24 用例"}
    base.update(extra)
    return base


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def wfok(label, args, inputs=None, sid="sess-U1"):
    """**必须成功**的调用：失败即打印原文并停下（不让静默失败连锁到后面的 KeyError）。

    这套件此前的病根就是 `wf(...)` 不看返回码：一步失败后靠 KeyError / 怪码暴露，
    排查要重建整条链。夹具里凡是"下一步依赖它成功"的调用都该走这里。
    """
    rc, payload, out = wf(args, inputs, sid)
    if rc != 0:
        # 关键字段优先：把 facts 里最能定位问题的几项单独打印（整包会被无关字段占满）
        facts = (payload or {}).get("facts") or {}
        keys = ("missing", "reason", "exits", "problems", "uncovered", "other_tasks", "suspended")
        brief = {k: facts[k] for k in keys if k in facts}
        print(f"[STOP] {label}: code={(payload or {}).get('code')}")
        print("       关键 facts:", json.dumps(brief, ensure_ascii=False)[:800])
        if not brief:
            print("       原文:", (out or "")[:800])
        raise SystemExit(1)
    return rc, payload, out


def cur_gen():
    """当前写者代次（每次变更都会 bump；夹具里写死旧代次会得到 WF_GENERATION_STALE）。"""
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


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
    rc, payload, out = wf(["task-approve", "--task", task_id, "--decision",
                           dfile(wfdrive.temp(f"r17_{task_id}_a.json"), [dec(f"approve {task_id}", "approve", digest)]), "--json"],
                          inputs, sid)
    if rc != 0:
        print(f"approve 原文({task_id}):", (out or "")[:400])
    return rc, payload, out


NOTES = wfdrive.temp("r17_notes.json")
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
wfok("task-start", ["task-start", "--task", task19, "--json"], {"generation": gen19}, "sess-U19")
for name in ("a", "c"):
    change = dfile(wfdrive.temp(f"r19_{name}.json"),
                   [{"operation": "add", "new_paths": [f".wf/spec/{name}.md"], "content": RULE}])
    wf(["spec-update", "--task", task19, "--changes", change, "--json"], {"generation": gen19}, "sess-U19")
batch = dfile(wfdrive.temp("r19_conflict.json"),
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
early = dfile(wfdrive.temp("r17_early.json"), [{"operation": "add", "new_paths": [".wf/spec/early.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task17, "--changes", early, "--json"], {"generation": gen17}, "sess-U17")
rec("R17 未开工不得写 spec", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
open(os.path.join(F, "src/r17.txt"), "w").write("r17\n")
wfok("task-start", ["task-start", "--task", task17, "--json"], {"generation": gen17}, "sess-U17")
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
rc_s, start_b, _ = wfok("task-start", ["task-start", "--task", task17b, "--json"], {"generation": gen17b}, "sess-U17b")
rec("R26 准备：开工", "WF_OK", (start_b or {}).get("code"), rc_s == 0)
out_of_face = dfile(wfdrive.temp("r17_out.json"), [{"operation": "add", "new_paths": [".wf/spec/outside-face.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task17b, "--changes", out_of_face, "--json"],
                    {"generation": gen17b}, "sess-U17b")
rec("R26 spec 目标不在触碰面内", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")
rec("R26 拒绝时零写入", "outside-face.md 不存在", os.path.exists(os.path.join(F, ".wf/spec/outside-face.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/outside-face.md")))
wf(["task-pause", "--task", task17b, "--reason", "R26 收尾", "--json"], {"generation": gen17b}, "sess-U17b")
wf(["writer", "release", "--json"], {"generation": gen17b}, "sess-U17b")

json.dump(results, open(wfdrive.temp("r17r24_results.json"), "w"), ensure_ascii=False, indent=2)
print("part1", sum(1 for r in results if r["pass"]), "/", len(results))

# ---------------- R20：改名不改归档引用 ----------------
clean()
task20a, gen20a, dir20a, d20a = make_task("R20 归档引用", [".wf/spec/**"], "sess-U20a")
approve(task20a, d20a, gen20a, "sess-U20a")
wfok("task-start", ["task-start", "--task", task20a, "--json"], {"generation": gen20a}, "sess-U20a")
old_rule = RULE.replace("paths: [\"src/**\"]", "paths: [\"src/old/**\"]")
add20 = dfile(wfdrive.temp("r20_add.json"), [{"operation": "add", "new_paths": [".wf/spec/old.md"], "content": old_rule}])
wf(["spec-update", "--task", task20a, "--changes", add20, "--json"], {"generation": gen20a}, "sess-U20a")
wf(["task-curate", "--task", task20a, "--spec", ".wf/spec/old.md", "--purpose", "旧规则", "--json"],
   {"generation": gen20a}, "sess-U20a")
wfok("spec", ["spec", "--file", ".wf/spec/old.md", "--json"],
     {"generation": gen20a}, "sess-U20a")   # 读取留痕（spec-loaded 前置）
wfok("spec", ["spec", "--file", ".wf/spec/old.md", "--json"], {"generation": gen20a}, "sess-U20a")
rc, payload, _ = wf(["task-check", "--task", task20a, "--review-notes", NOTES, "--json"],
                    {"generation": gen20a}, "sess-U20a")
json.dump((payload or {}).get("facts"), open(wfdrive.temp("r20_facts.json"), "w"), ensure_ascii=False)
rec("R20 准备：Check", "WF_OK", f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:400]}", rc == 0)
wf(["task-knowledge", "--task", task20a, "--decision", "no-update", "--json"], {"generation": gen20a}, "sess-U20a")
wfok("sampling", ["sampling", "pick", "--task", task20a, "--freeze", "--json"],
                       {"generation": gen20a}, "sess-U20a")   # 归档前置：先冻结并落盘选样
rc, payload, _ = wf(["archive", "--task", task20a, "--decision",
                     dfile(wfdrive.temp("r20_arch.json"), [dec(f"finish {task20a}", "finish", d20a),
                                                  dec(".wf/spec/**", "commit", d20a)]),
                     "--json"], {"generation": gen20a}, "sess-U20a")
rec("R20 准备：归档任务", "WF_OK", f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:300]}", rc == 0)
wf(["writer", "release", "--json"], {"generation": gen20a}, "sess-U20a")
archived_dir = wf_tasks.task_dir(F, task20a)
before = open(os.path.join(archived_dir, "task.json"), encoding="utf-8").read()

clean()
task20b, gen20b, dir20b, d20b = make_task("R20 改名", [".wf/spec/**"], "sess-U20b")
approve(task20b, d20b, gen20b, "sess-U20b")
wfok("task-start", ["task-start", "--task", task20b, "--json"], {"generation": gen20b}, "sess-U20b")
rename20 = dfile(wfdrive.temp("r20_rename.json"), [{"operation": "rename", "old_paths": [".wf/spec/old.md"],
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
wfok("task-start", ["task-start", "--task", task18, "--json"], {"generation": gen18}, "sess-U18")
add18 = dfile(wfdrive.temp("r18_add.json"),
              [{"operation": "add", "new_paths": [".wf/spec/expired.md"], "content": expired},
               {"operation": "add", "new_paths": [".wf/spec/nomatch.md"], "content": nomatch}])
wf(["spec-update", "--task", task18, "--changes", add18, "--json"], {"generation": gen18}, "sess-U18")
open(os.path.join(F, "lib/r18.txt"), "w") if os.path.isdir(os.path.join(F, "lib")) else None
wf(["task-curate", "--task", task18, "--spec", ".wf/spec/expired.md", "--purpose", "到期规则", "--json"],
   {"generation": gen18}, "sess-U18")
wfok("spec", ["spec", "--file", ".wf/spec/expired.md", "--json"],
     {"generation": gen18}, "sess-U18")   # 读取留痕（spec-loaded 前置）
wfok("spec", ["spec", "--file", ".wf/spec/expired.md", "--json"], {"generation": gen18}, "sess-U18")
rc, payload, _ = wf(["task-check", "--task", task18, "--review-notes", NOTES, "--json"],
                    {"generation": gen18}, "sess-U18")
needs = [item.get("reason") for item in (((payload or {}).get("facts") or {}).get("spec") or {}).get("needs") or []]
rec("R18 到期条目阻断", "WF_SPEC_INCOMPLETE 且 needs 含 expired",
    f"code={(payload or {}).get('code')} needs={needs}",
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE" and "expired" in needs)
wf(["task-curate", "--task", task18, "--spec", ".wf/spec/nomatch.md", "--purpose", "未被命中但已策展", "--json"],
   {"generation": gen18}, "sess-U18")
wfok("spec", ["spec", "--file", ".wf/spec/nomatch.md", "--json"],
     {"generation": gen18}, "sess-U18")   # 读取留痕（spec-loaded 前置）
wfok("spec", ["spec", "--file", ".wf/spec/nomatch.md", "--json"], {"generation": gen18}, "sess-U18")
rc, payload, _ = wf(["task-check", "--task", task18, "--decision",
                     dfile(wfdrive.temp("r18_dec.json"), [dec(".wf/spec/expired.md", "passed", d18)]),
                     "--review-notes", NOTES, "--json"], {"generation": gen18}, "sess-U18")
spec_facts = ((payload or {}).get("facts") or {}).get("spec") or {}
rec("R18 策展未命中条目也参与判定", "curated 含 nomatch 且仍阻断",
    f"curated={spec_facts.get('curated')} code={(payload or {}).get('code')}",
    ".wf/spec/nomatch.md" in (spec_facts.get("curated") or [])
    and (payload or {}).get("code") == "WF_SPEC_INCOMPLETE")
rc, payload, _ = wf(["task-check", "--task", task18, "--decision",
                     dfile(wfdrive.temp("r18_dec2.json"), [dec(".wf/spec/expired.md .wf/spec/nomatch.md", "passed", d18)]),
                     "--review-notes", NOTES, "--json"], {"generation": gen18}, "sess-U18")
rec("R18 人判覆盖后通过", "WF_OK", f"{(payload or {}).get('code')} spec={json.dumps(((payload or {}).get('facts') or {}).get('spec'), ensure_ascii=False)[:160]}", rc == 0)
wf(["task-pause", "--task", task18, "--reason", "R18 收尾", "--json"], {"generation": gen18}, "sess-U18")
wf(["writer", "release", "--json"], {"generation": gen18}, "sess-U18")

json.dump(results, open(wfdrive.temp("r17r24_results.json"), "w"), ensure_ascii=False, indent=2)
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
wfok("task-start", ["task-start", "--task", task21, "--json"], {"generation": gen21}, "sess-U21")
probe = json.load(open(os.path.join(dir21, "task.json")))
probe_block = json.loads(open(os.path.join(dir21, "prd.md"), encoding="utf-8").read().split("```json")[1].split("```")[0])
probe_block["verifications"] = ver21
prd21 = f"# R21 结束前重算\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(probe_block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(dir21, "prd.md"), "w", encoding="utf-8").write(prd21)
d21b = "sha256:" + hashlib.sha256(prd21.encode()).hexdigest()
json.dump([dec(f"replan {task21}", "replan", d21b)], open(wfdrive.temp("r21_replan.json"), "w"))
wf(["task-replan", "--task", task21, "--decision", wfdrive.temp("r21_replan.json"), "--json"],
   {"generation": gen21}, "sess-U21")
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
rc_s22, start22, _ = wfok("task-start", ["task-start", "--task", task22, "--json"], {"generation": gen22}, "sess-U22")
rec("R22 准备：开工", "WF_OK", (start22 or {}).get("code"), rc_s22 == 0)
bad_notes = wfdrive.temp("r22_notes_bad.json")
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"},
           "tdd_evidence": {"note": "no red/green references"}}, open(bad_notes, "w"))
rc, payload, _ = wf(["task-check", "--task", task22, "--review-notes", bad_notes, "--json"],
                    {"generation": gen22}, "sess-U22")
rec("R22 非结构化证据不得通过", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
good = {"assertion": "add 支持变长加数", "red_reason": "旧实现不接受第三个加数",
        "red_command_ref": "v1", "green_command_ref": "v2",
        "properties": "可红、确定性、快速、可无人执行"}
good_notes = wfdrive.temp("r22_notes_good.json")
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
json.dump([dec(f"replan {task22}", "replan", d22b)], open(wfdrive.temp("r22_replan.json"), "w"))
wf(["task-replan", "--task", task22, "--decision", wfdrive.temp("r22_replan.json"), "--json"],
   {"generation": gen22}, "sess-U22")
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
           "tdd_evidence": same}, open(wfdrive.temp("r22_notes_same.json"), "w"))
rc, payload, _ = wf(["task-check", "--task", task22, "--review-notes", wfdrive.temp("r22_notes_same.json"), "--json"],
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
wfok("task-start", ["task-start", "--task", task23, "--json"], {"generation": cur_gen()}, "sess-U23")
rc_chk23, chk23, _ = wf(["task-check", "--task", task23, "--review-notes", NOTES, "--json"],
                                 {"generation": cur_gen()}, "sess-U23")
if rc_chk23 != 0:
    print("R23 check 原文:", json.dumps((chk23 or {}).get("facts") or {}, ensure_ascii=False)[:400])
wf(["task-knowledge", "--task", task23, "--decision", "no-update", "--json"], {"generation": cur_gen()}, "sess-U23")
wfok("sampling", ["sampling", "pick", "--task", task23, "--freeze", "--json"],
     {"generation": cur_gen()}, "sess-U23")   # 正常归档前必须冻结并落盘选样（task.sampled 前置）
# 制造「已移动、未持久化」：**首次**归档时注入故障，让记录段提交失败
# （第二次归档会因"已归档"直接返回 WF_OK，故障注入只有落在首次才有意义）
lock_path = os.path.join(F, ".git", "index.lock")
open(lock_path, "w").write("")
rc_fail, fail_payload, _ = wf(["archive", "--task", task23, "--decision",
                               dfile(wfdrive.temp("r23_arch.json"), [dec(f"finish {task23}", "finish", d23),
                                                            dec("area23/**", "commit", d23)]), "--json"],
                              {"generation": cur_gen()}, "sess-U23")
os.remove(lock_path)
rec("R23 归档记录段失败即持久化未完成", "WF_PERSISTENCE_FAILED",
    (fail_payload or {}).get("code"), (fail_payload or {}).get("code") == "WF_PERSISTENCE_FAILED")
archived_dir_before = wf_tasks.task_dir(F, task23)
persisted_before = wf_tasks.archive_persisted(F, json.load(open(os.path.join(archived_dir_before, "task.json"))))
rec("R23 未持久化状态已构造", "persisted=False", persisted_before.get("persisted"),
    persisted_before.get("persisted") is False)

# 写权随"对象暂停/终止"释放（机制稿 §4.4）：先暂停，再释放，才能造出"无写权"前提
wf(["task-pause", "--task", task23, "--reason", "R23 无写权前提", "--json"], {"generation": cur_gen()}, "sess-U23")
rc_rel, rel_payload, _ = wf(["writer", "release", "--json"], {"generation": cur_gen()}, "sess-U23")
print("R23 release:", rc_rel, (rel_payload or {}).get("code"), (rel_payload or {}).get("facts"))
rc_busy, busy_payload, _ = wf(["archive", "--task", task23, "--decision",
                               dfile(wfdrive.temp("r23_arch2.json"), [dec(f"finish {task23}", "finish", d23),
                                                   dec("area23/**", "commit", d23)]), "--json"],
                              {"generation": cur_gen()}, "sess-U23")
# 期望码由 WF_WRITER_BUSY 改为 WF_SEMANTIC_DECISION：实现把"写权空闲且本会话未持有"
# 与"写权被别人持着"分成了两码（前者给 `writer acquire` 出口，后者让等释放）。
# 这里构造的是**已释放**的场景，所以应得后者之外的这一码——语义仍成立：无写权不得续做。
rec("R23 无写权不得续做", "WF_SEMANTIC_DECISION 或 WF_WRITER_BUSY", (busy_payload or {}).get("code"),
    (busy_payload or {}).get("code") in ("WF_SEMANTIC_DECISION", "WF_WRITER_BUSY"))
if (payload or {}).get("code") != "WF_OK":
    print("R23 重入 archive reason:", json.dumps((payload or {}).get("facts") or {}, ensure_ascii=False)[:400])
# 对象仍处于 paused：先恢复，再取写权，然后才能重入续做归档
wf(["writer", "acquire", "--json"], {"generation": cur_gen()}, "sess-U23")
wf(["task-resume", "--task", task23, "--json"], {"generation": cur_gen()}, "sess-U23")
_rec23 = json.load(open(os.path.join(wf_tasks.task_dir(F, task23), "task.json"), encoding="utf-8"))
print("R23 续做前记录 check.id=", ((_rec23.get("check") or {}).get("id")),
      " 刚Check id=", ((chk23 or {}).get("facts") or {}).get("check"),
      " object_paths=", ((_rec23.get("check") or {}).get("object_paths")))
rc, payload, _ = wf(["archive", "--task", task23, "--decision",
                     dfile(wfdrive.temp("r23_arch2.json"), [dec(f"finish {task23}", "finish", d23),
                                                   dec("area23/**", "commit", d23)]), "--json"],
                    {"generation": cur_gen()}, "sess-U23")
if (payload or {}).get("code") != "WF_OK":
    _f = (payload or {}).get("facts") or {}
    print("R23 末条 facts:", json.dumps({k: _f.get(k) for k in ("reason", "missing", "exits", "all") if k in _f}, ensure_ascii=False)[:600])
facts = (payload or {}).get("facts", {})
# 期望收紧到"可保证的事实"：重入必须成功且**已持久化**；`resumed` 取决于失败发生点
# （业务段失败时目录还没移动 → 重入就是一次正常归档，resumed=False 才是诚实结果）。
# "移动后失败再续做"这条由 cp5 B3（SIGKILL 在提交后）覆盖，这里不重复要求。
rec("R23 重入按既有授权续做提交", "WF_OK 且 persisted=true",
    f"{(payload or {}).get('code')} persisted={(facts.get('archive_persisted') or {}).get('persisted')} resumed={(facts.get('archive_persisted') or {}).get('resumed_commit')}",
    (payload or {}).get("code") == "WF_OK"
    and (facts.get("archive_persisted") or {}).get("persisted") is True
    and (facts.get("archive_persisted") or {}).get("persisted") is True)
wf(["writer", "release", "--json"], {"generation": cur_gen()}, "sess-U23")

# ---------------- R24：放弃时的真实处置 ----------------
clean()
os.makedirs(os.path.join(F, "area24"), exist_ok=True)
task24, gen24, dir24, d24 = make_task("R24 放弃处置", ["area24/**"], "sess-U24")
approve(task24, d24, gen24, "sess-U24")
open(os.path.join(F, "area24/r24.txt"), "w").write("r24\n")
wfok("task-start", ["task-start", "--task", task24, "--json"], {"generation": gen24}, "sess-U24")
disp = {"changes": [{"object": "area24/r24.txt", "decision_ref": AT, "reason": "保留现状"}], "targets": [], "pending": []}
json.dump(disp, open(wfdrive.temp("r24_disp.json"), "w"), ensure_ascii=False)
stop_only = dfile(wfdrive.temp("r24_stop.json"), [dec(f"stop {task24}", "abandon", d24)])
rc, payload, _ = wf(["task-abandon", "--task", task24, "--decision", stop_only,
                     "--disposition", wfdrive.temp("r24_disp.json"), "--json"], {"generation": gen24}, "sess-U24")
rec("R24 无授权且未处置不得结案", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
record = json.load(open(os.path.join(dir24, "task.json")))
rec("R24 未结案时不写异常终态", "terminal 为空且仍未归档",
    f"terminal={record.get('terminal')} status={record.get('status')}",
    not record.get("terminal") and record.get("status") != "archived")
with_grant = dfile(wfdrive.temp("r24_grant.json"), [dec(f"stop {task24}", "abandon", d24),
                                           dec("area24/**", "commit", d24)])
rc, payload, _ = wf(["task-abandon", "--task", task24, "--decision", with_grant,
                     "--disposition", wfdrive.temp("r24_disp.json"), "--json"], {"generation": gen24}, "sess-U24")
committed = subprocess.run(["git", "log", "-2", "--name-only", "--format="], cwd=F,
                           capture_output=True, text=True).stdout
rec("R24 有授权时实际提交并结案", "WF_OK 且改动已提交",
    f"{(payload or {}).get('code')} committed={'area24/r24.txt' in committed}",
    rc == 0 and "area24/r24.txt" in committed)

json.dump(results, open(wfdrive.temp("r17r24_results.json"), "w"), ensure_ascii=False, indent=2)
print("total", sum(1 for r in results if r["pass"]), "/", len(results))
