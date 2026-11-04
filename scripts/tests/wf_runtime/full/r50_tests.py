#!/usr/bin/env python3
"""第十四轮 R50：baseline-apply 与 spec 写入对同一目标作出一致边界判定。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []

def _pd(files):
    import sys as _s
    _s.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
    from wflib import records as _r
    return _r.plain_digest({"files": files})

AT = "2026-11-04T11:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-V1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R50 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


RULE = '''---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "2026-11-04"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''

os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
os.makedirs(os.path.join(F, "vendor/subrepo/data"), exist_ok=True)
open(os.path.join(F, "vendor/subrepo/.git"), "w").write("gitdir: /tmp/nowhere\n")
open(os.path.join(F, "vendor/subrepo/data/rule.md"), "w").write(RULE)
clean()

rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", "R50 基线边界",
                       "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-V1")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R50 基线边界\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r50_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r50_a.json", "--json"],
   {"generation": gen, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-V1")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc_s, start1, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": write_gen()}, "sess-V1")
rec("R50 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)

# 目录链接指向嵌套仓库
alias = os.path.join(F, ".wf/spec/alias")
if os.path.lexists(alias):
    os.remove(alias)
os.symlink(os.path.join(F, "vendor/subrepo/data"), alias)

# ① baseline-apply 写入该别名
proposal = dfile("/tmp/r50_baseline.json",
                 {"files": [{"path": ".wf/spec/alias/baseline-created.md", "content": RULE, "before": None}],
    "approval": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                 "subject": "r50 proposal", "choice": "approve",
                 "object_digest": _pd([{"path": ".wf/spec/alias/baseline-created.md", "content": RULE, "before": None}]), "reason": "R50"}})
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", proposal, "--json"],
                    {"generation": write_gen()}, "sess-V1")
rec("R50 baseline-apply 拒绝嵌套仓库目标", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R50 baseline-apply 零写入", "嵌套仓库内未生成",
    os.path.exists(os.path.join(F, "vendor/subrepo/data/baseline-created.md")),
    not os.path.exists(os.path.join(F, "vendor/subrepo/data/baseline-created.md")))
rec("R50 报告嵌套根原因", "facts 含 nested repository root",
    json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:120],
    "nested repository root" in json.dumps((payload or {}).get("facts"), ensure_ascii=False))

# ② spec-update 对同一目标：一致拒绝
change = dfile("/tmp/r50_spec.json",
               [{"operation": "add", "new_paths": [".wf/spec/alias/spec-created.md"], "content": RULE}])
rc, payload2, _ = wf(["spec-update", "--task", task_id, "--changes", change, "--json"],
                     {"generation": write_gen()}, "sess-V1")
rec("R50 spec 写入对同一目标一致拒绝", "WF_PATH_INVALID", (payload2 or {}).get("code"),
    (payload2 or {}).get("code") == "WF_PATH_INVALID")
rec("R50 两入口原因一致", "同为 nested repository root",
    f"baseline={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:80]} spec={json.dumps((payload2 or {}).get('facts'), ensure_ascii=False)[:80]}",
    "nested repository root" in json.dumps((payload or {}).get("facts"), ensure_ascii=False)
    and "nested repository root" in json.dumps((payload2 or {}).get("facts"), ensure_ascii=False))

# ③ 正例：普通 spec 骨架仍可经 baseline-apply 写入
ok_proposal = dfile("/tmp/r50_ok.json",
                    {"files": [{"path": ".wf/spec/plain.md", "content": RULE, "before": None}],
                     "approval": {"source": "human", "at": "2026-11-06T00:00:00.000000Z",
                                  "subject": "r50 proposal", "choice": "approve",
                                  "object_digest": _pd([{"path": ".wf/spec/plain.md", "content": RULE, "before": None}]), "reason": "R50"}})
rc, payload3, _ = wf(["baseline-apply", "--task", task_id, "--proposal", ok_proposal, "--json"],
                     {"generation": write_gen()}, "sess-V1")
rec("R50 正例：普通骨架可写", "WF_OK", (payload3 or {}).get("code"), rc == 0)
os.remove(alias)
shutil.rmtree(os.path.join(F, "vendor"))

json.dump(results, open("/tmp/r50_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
