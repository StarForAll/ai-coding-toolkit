#!/usr/bin/env python3
"""第三十八轮 R74：写入目标白名单统一、activation 覆盖 start 路由、工作树枚举同源。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import paths as wf_paths, scope as wf_scope

F = wfdrive.FIX
results = []
AT = "2026-11-13T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Z1", **kw):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, **kw)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R74"}


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()

# ---- 1. 写入目标白名单是单一实现 ----
rec("1 基线/配置在允许集合", "允许", wf_paths.write_target_allowed(".wf/baseline.md"),
    wf_paths.write_target_allowed(".wf/baseline.md"))
rec("1b spec 目录在允许集合", "允许", wf_paths.write_target_allowed(".wf/spec/x.md"),
    wf_paths.write_target_allowed(".wf/spec/x.md"))
rec("1c 控制记录被拒", "拒绝", not wf_paths.write_target_allowed(".wf/writer.json"),
    not wf_paths.write_target_allowed(".wf/writer.json"))

# 走真实入口：spec-update 试图写控制记录
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R74 白名单",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-Z1")
facts = (payload or {}).get("facts", {})
task_id, genv = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R74\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
          open("/tmp/r74_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r74_a.json", "--json"],
   {"generation": genv, "complexity": "light",
    "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-Z1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
rc_s, payload_s, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, "sess-Z1")
if rc_s != 0:
    print("   start failed:", (payload_s or {}).get("code"),
          json.dumps((payload_s or {}).get("facts"), ensure_ascii=False)[:200])
changes = "/tmp/r74_changes.json"
json.dump([{"operation": "add", "new_paths": [".wf/writer.json"], "content": "{}"}],
          open(changes, "w"), ensure_ascii=False)
rc, payload, _ = wf(["spec-update", "--task", task_id, "--changes", changes, "--json"],
                    {"generation": gen()}, "sess-Z1")
rec("1d spec-update 拒绝控制记录目标", "WF_SCOPE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SCOPE_UNRESOLVED")

# ---- 2. activation 覆盖 start 路由 ----
for command, args in (("bind", ["bind", "--task", task_id, "--json"]),
                      ("task-new", ["task-new", "--kind", "ordinary", "--title", "R74 未启用",
                                    "--template", f"{F}/.wf/templates/task", "--json"])):
    rc, payload, _ = wf(args, {"generation": gen()}, "sess-Z2", activation=False)
    rec(f"2 {command} 未启用被拒", "WF_NOT_ENABLED", (payload or {}).get("code"),
        (payload or {}).get("code") == "WF_NOT_ENABLED")
rc, payload, _ = wfdrive.run(["writer", "acquire", "--json"], {"generation": gen()}, "sess-Z3",
                             activation=False, show=False)
rec("2c writer acquire 未启用被拒", "WF_NOT_ENABLED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_NOT_ENABLED")

# ---- 3. 工作树枚举与 Git 同源 ----
walked = set(wf_scope._enumerate_tree(F))
_listed = subprocess.run(["git", "-c", "core.quotePath=false", "ls-files"],
                         cwd=F, capture_output=True, text=True).stdout.split("\n")
git_paths = {p for p in _listed if p
             and not any(part in (".git", ".wf", "__pycache__", "node_modules") for part in p.split("/"))}
tracked_missing = {p for p in git_paths if p not in walked}
rec("3 枚举包含全部 Git 跟踪文件", "无遗漏", sorted(tracked_missing)[:3],
    not tracked_missing)
rec("3b 枚举不含控制目录", "无 .wf/ 前缀", [p for p in walked if p.startswith(".wf/")][:2],
    not [p for p in walked if p.startswith(".wf/")])

json.dump(results, open("/tmp/r74_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
