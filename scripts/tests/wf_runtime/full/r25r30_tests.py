#!/usr/bin/env python3
"""第五轮 R25–R30 用例（R25/R27/R29 由第四轮用例覆盖，这里补 R28、R30 与 R29 的直接断言）。"""
import datetime, hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []

import sys as _sys
_sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import records as _wf_records


def utc_today():
    """与实现同一时钟：核实周期按 UTC 计日。"""
    return _wf_records.utc_now().date()

AT = "2026-11-03T23:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-W1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R25-R30 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-W1"):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid="sess-W1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r25_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/r25_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

RULE = '''---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "{date}"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''

# ---------------- R28：周期配置、未来日期、spec_review 落记录 ----------------
config_path = os.path.join(F, ".wf/project-config.json")
config = json.load(open(config_path))
config["spec_verify_days"] = 1
json.dump(config, open(config_path, "w"), ensure_ascii=False, indent=2)
clean()
today = utc_today()
old_date = (today - datetime.timedelta(days=2)).isoformat()
future_date = (today + datetime.timedelta(days=3)).isoformat()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task28, gen28, dir28, d28 = make_task("R28 核实周期", ["pkg/**", ".wf/spec/**"], "sess-W28")
approve(task28, d28, gen28, "sess-W28")
rc_s, start28, _ = wf(["task-start", "--task", task28, "--json"], {"generation": gen28}, "sess-W28")
rec("R28 准备：开工", "WF_OK", (start28 or {}).get("code"), rc_s == 0)
changes = dfile("/tmp/r28_add.json",
                [{"operation": "add", "new_paths": [".wf/spec/old.md"], "content": RULE.replace("{date}", old_date)},
                 {"operation": "add", "new_paths": [".wf/spec/future.md"], "content": RULE.replace("{date}", future_date)}])
wf(["spec-update", "--task", task28, "--changes", changes, "--json"], {"generation": gen28}, "sess-W28")
open(os.path.join(F, "pkg/r28.txt"), "w").write("r28\n")
for path in (".wf/spec/old.md", ".wf/spec/future.md"):
    wf(["task-curate", "--task", task28, "--spec", path, "--purpose", "核实用例", "--json"],
       {"generation": gen28}, "sess-W28")
    wf(["spec", "--file", path, "--json"], {"generation": gen28}, "sess-W28")
rc, payload, _ = wf(["task-check", "--task", task28, "--review-notes", NOTES, "--json"],
                    {"generation": gen28}, "sess-W28")
spec_facts = ((payload or {}).get("facts") or {}).get("spec") or {}
needs = [item.get("reason") for item in spec_facts.get("needs") or []]
rec("R28 配置周期生效（1 天）", "needs 含 expired 且 period_days=1",
    f"needs={needs} period={spec_facts.get('period_days')}",
    "expired" in needs and spec_facts.get("period_days") == 1)
rec("R28 未来日期进入待核对", "needs 含 future-date", needs, "future-date" in needs)
covered = dfile("/tmp/r28_decision.json", [dec(".wf/spec/old.md .wf/spec/future.md", "passed", d28)])
rc, payload, _ = wf(["task-check", "--task", task28, "--decision", covered, "--review-notes", NOTES, "--json"],
                    {"generation": gen28}, "sess-W28")
record = json.load(open(os.path.join(dir28, "task.json")))
saved = (record.get("check") or {}).get("spec_review") or {}
rec("R28 覆盖后可继续", "WF_OK", (payload or {}).get("code"), rc == 0)
rec("R28 spec_review 写入检查记录", "记录含 needs/period/evidence",
    f"needs={len(saved.get('needs') or [])} evidence={len(saved.get('evidence') or [])}",
    bool(saved.get("needs")) and saved.get("period_days") == 1 and bool(saved.get("evidence")))
wf(["task-pause", "--task", task28, "--reason", "R28 收尾", "--json"], {"generation": gen28}, "sess-W28")
wf(["writer", "release", "--json"], {"generation": gen28}, "sess-W28")

# ---------------- R30：冲突判定只看真正引用该路径的活动任务 ----------------
from wflib import spec as wf_spec  # noqa: E402

clean()
task30, gen30, dir30, d30 = make_task("R30 引用冲突", [".wf/spec/**"], "sess-W30")
approve(task30, d30, gen30, "sess-W30")
rc_s30, start30, _ = wf(["task-start", "--task", task30, "--json"], {"generation": gen30}, "sess-W30")
rec("R30 准备：开工", "WF_OK", f"{(start30 or {}).get('code')}", rc_s30 == 0)
add30 = dfile("/tmp/r30_add.json", [{"operation": "add", "new_paths": [".wf/spec/ref.md"],
                                     "content": RULE.replace("{date}", today.isoformat())}])
wf(["spec-update", "--task", task30, "--changes", add30, "--json"], {"generation": gen30}, "sess-W30")
wf(["task-curate", "--task", task30, "--spec", ".wf/spec/ref.md", "--purpose", "引用", "--json"],
   {"generation": gen30}, "sess-W30")
index_path = os.path.join(F, ".wf/spec/index.md")
backup = open(index_path, encoding="utf-8").read()
os.remove(index_path)
os.makedirs(index_path)
noise = dfile("/tmp/r30_noise.json", [{"operation": "add", "new_paths": [".wf/spec/noise.md"],
                                       "content": RULE.replace("{date}", today.isoformat())}])
rc, payload, _ = wf(["spec-update", "--task", task30, "--changes", noise, "--json"],
                    {"generation": gen30}, "sess-W30")
os.rmdir(index_path)
open(index_path, "w", encoding="utf-8").write(backup)
rec("R30 准备：留下未完成动作", "WF_PERSISTENCE_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PERSISTENCE_FAILED")
raised = None
try:
    wf_spec._check_reference_conflicts(F, [".wf/spec/ref.md"])
except wf_spec.SpecError as exc:
    raised = exc.code
rec("R30 被引用的路径在写入前阻断", "WF_ACTION_INCOMPLETE", raised, raised == "WF_ACTION_INCOMPLETE")
unrelated = None
try:
    wf_spec._check_reference_conflicts(F, [".wf/spec/other.md"])
except wf_spec.SpecError as exc:
    unrelated = exc.code
rec("R30 未被引用的路径不阻断", "不抛错", unrelated or "no-raise", unrelated is None)
rec("R30 判定只读不写文件", "ref.md 仍在",
    os.path.exists(os.path.join(F, ".wf/spec/ref.md")),
    os.path.exists(os.path.join(F, ".wf/spec/ref.md")))
wf(["writer", "release", "--json"], {"generation": gen30}, "sess-W30")

json.dump(results, open("/tmp/r25r30_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
