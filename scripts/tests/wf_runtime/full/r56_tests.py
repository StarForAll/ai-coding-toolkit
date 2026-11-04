#!/usr/bin/env python3
"""第十九轮 R56：spec_verify_days 非法时阻断依赖它的判断。"""
import datetime, hashlib, json, os, subprocess, sys
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

import sys as _sys
_sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import records as _wf_records


def utc_today():
    """与实现同一时钟：核实周期按 UTC 计日。"""
    return _wf_records.utc_now().date()

AT = "2026-11-04T16:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-A1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R56 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


NOTES = "/tmp/r56_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

old_date = (utc_today() - datetime.timedelta(days=2)).isoformat()
RULE = f'''---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "{old_date}"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''

os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/r56.md"), "w").write(RULE)
index_path = os.path.join(F, ".wf/spec/index.md")
text = open(index_path, encoding="utf-8").read()
if "r56.md" not in text:
    open(index_path, "w", encoding="utf-8").write(text + "- [r56.md](.wf/spec/rules/r56.md)\n")
clean()

config_path = os.path.join(F, ".wf/project-config.json")
backup = open(config_path, encoding="utf-8").read()

rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R56 周期", "--template",
                     f"{F}/.wf/templates/task", "--json"], None, "sess-A1")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R56 周期\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r56_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r56_a.json", "--json"],
   {"generation": gen, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-A1")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc_s, start1, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": write_gen()}, "sess-A1")
rec("R56 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)
wf(["task-curate", "--task", task_id, "--spec", ".wf/spec/rules/r56.md", "--purpose", "周期用例", "--json"],
   {"generation": write_gen()}, "sess-A1")
wf(["spec", "--file", ".wf/spec/rules/r56.md", "--json"], {"generation": write_gen()}, "sess-A1")


def set_period(value_json):
    config = json.loads(backup)
    if value_json is not None:
        config["spec_verify_days"] = json.loads(value_json)
    else:
        config.pop("spec_verify_days", None)
    json.dump(config, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


# ① 合法值 1 天 → 两天前算到期
set_period("1")
clean()
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-A1")
spec_facts = (((payload or {}).get("facts") or {}).get("spec") or {})
rec("R56 合法周期 1 天 → 到期阻断", "WF_SPEC_INCOMPLETE",
    f"{(payload or {}).get('code')} period={spec_facts.get('period_days')}",
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE" and spec_facts.get("period_days") == 1)

# ② 非法值 → 同样阻断（不再静默按 90 天）
set_period('"invalid-period"')
clean()
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-A1")
spec_facts = (((payload or {}).get("facts") or {}).get("spec") or {})
rec("R56 非法值阻断（不按 90 天放行）", "WF_SPEC_INCOMPLETE 且 period_problems 非空",
    f"{(payload or {}).get('code')} problems={spec_facts.get('period_problems')}",
    (payload or {}).get("code") == "WF_SPEC_INCOMPLETE" and spec_facts.get("period_problems"))

# ③ 键缺失 → 用发行缺省（90 天），两天前不算到期
set_period(None)
clean()
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-A1")
saved_check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
saved_spec = saved_check.get("spec_review") or {}
rec("R56 键缺失按缺省且不阻断周期", "WF_OK 且记录 period_days=90、无 period_problems",
    f"{(payload or {}).get('code')} period={saved_spec.get('period_days')} problems={saved_spec.get('period_problems')}",
    saved_spec.get("period_days") == 90 and not saved_spec.get("period_problems"))

open(config_path, "w", encoding="utf-8").write(backup)
json.dump(results, open("/tmp/r56_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
