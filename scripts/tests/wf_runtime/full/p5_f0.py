#!/usr/bin/env python3
"""F0（全新项目：无 Git/无基线）：自举 + Git 就绪。夹具由 install.py 从发行树安装。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
SID = "sess-F"
results = []


def rec(case, expected, actual, passed, note=""):
    results.append({"case": case, "expected": expected, "actual": actual, "pass": passed, "note": note})
    print(f"[F0] {case}: {'PASS' if passed else 'FAIL'} — {actual}")


def wf(args, inputs=None):
    return wfdrive.run(args, inputs=inputs, sid=SID, show=False)


rc, payload, _ = wf(["enable", "--json"])
rec("安装后启用（无 Git/无基线）", "pass", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["task-new", "--kind", "initialize", "--title", "初始化项目基线",
                     "--template", f"{F}/.wf/templates/task", "--json"])
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
if not task_id:
    print("task-new failed", payload); raise SystemExit(1)
directory = os.path.join(F, facts.get("directory", ""))
rec("无 Git 时仍可创建规划", "pass（创建任务/起草规划不被阻断）", "task-new ok", True)

prd = '''# 初始化项目基线

## 机读块

<!-- wf-plan:v1 -->
```json
{"schema_version": 1,
 "touch_paths": [".wf/baseline.md", ".wf/project-config.json", ".wf/spec/index.md"],
 "acceptance": [{"id": "a1", "statement": "骨架文件生成且可解析", "verification_ids": ["v1"]}],
 "verifications": [{"id": "v1", "invocation": {"kind": "argv",
   "argv": ["/usr/bin/python3", "-c", "import json,os; json.load(open('.wf/project-config.json')); os.stat('.wf/baseline.md'); print('ok')"]},
   "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}]}
```
'''
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
at = "2026-11-03T07:00:00.000000Z"
json.dump([{"source": "human (sess-F)", "at": at, "subject": "approve init plan",
            "object_digest": digest, "choice": "approve", "reason": "F0 自举"}],
          open("/tmp/f0_approve.json", "w"), ensure_ascii=False)
inputs = {"generation": gen, "complexity": "light",
          "downgrade": {"reason": "初始化任务只生成骨架，项目无既有治理面与外部契约",
                        "evidence": "全新项目；治理面块随本任务首次生成且 paths 为空"}}
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision", "/tmp/f0_approve.json", "--json"], inputs)
rec("批准初始化规划", "pass", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
rec("无 HEAD 时开工", "blocked WF_CAPABILITY_UNAVAILABLE",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_CAPABILITY_UNAVAILABLE" and rc == 1)

# 人授权建立 Git 就绪：只暂存骨架并产生首个 HEAD
subprocess.run(["git", "init", "-q"], cwd=F, check=False)
subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=F, check=False)
subprocess.run(["git", "config", "user.name", "tester"], cwd=F, check=False)
subprocess.run(["git", "add", ".wf", ".gitignore"], cwd=F, check=False)
subprocess.run(["git", "commit", "-qm", "wf: initial skeleton"], cwd=F, check=False)
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=F, capture_output=True, text=True).stdout.strip()
rec("人授权建立首个 HEAD", "HEAD 存在且只含骨架", head[:8], bool(head))

rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
rec("Git 就绪后开工", "pass", (payload or {}).get("code"), rc == 0)

skeleton = json.load(open(f"{F}/.wf/templates/project-config.skeleton.json"))
skeleton["project_id"] = os.urandom(16).hex()
baseline = open(f"{F}/.wf/templates/baseline.md", encoding="utf-8").read()
for key, value in (("scope", "全新示例项目"), ("non-goals", "不引入依赖"), ("acceptance", "骨架可解析"),
                   ("architecture", "单包"), ("risks", "无"), ("verification-commands", "/usr/bin/python3 -c \"print(1)\""),
                   ('"__WF_REQUIRED__"', '"本项目暂无特别约束路径"'),
                   ('"__WF_REQUIRED__"', '"dsh session F"'),
                   ('"__WF_REQUIRED__"', '"2026-11-03"')):
    baseline = baseline.replace("{{WF_REQUIRED:%s}}" % key if not key.startswith('"') else key, value, 1)
proposal = {"files": [
    {"path": ".wf/project-config.json", "content": json.dumps(skeleton, indent=2, ensure_ascii=False) + "\n", "before": None},
    {"path": ".wf/baseline.md", "content": baseline, "before": None},
    {"path": ".wf/spec/index.md", "content": open(f"{F}/.wf/templates/spec/index.md", encoding="utf-8").read(), "before": None},
]}
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import records as _wf_records

proposal["approval"] = {"source": "human terminal", "at": "2026-11-07T00:00:00.000000Z",
                        "subject": "F0 baseline proposal", "choice": "approve",
                        "object_digest": _wf_records.plain_digest({"files": proposal["files"]}),
                        "reason": "F0 初始化基线"}
json.dump(proposal, open("/tmp/f0_proposal.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", "/tmp/f0_proposal.json", "--json"], inputs)
rec("初始化落盘骨架", "pass", (payload or {}).get("code"), rc == 0)

json.dump({"standard": {"conclusion": "pass", "basis": "骨架文件核对"},
           "requirement": {"conclusion": "pass", "basis": "a1 由 v1 覆盖"}},
          open("/tmp/f0_notes.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/f0_notes.json", "--json"], inputs)
rec("Check pass", "pass", (payload or {}).get("code"), rc == 0)
wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], inputs)
json.dump([{"source": "human (sess-F)", "at": at, "subject": f"finish {task_id}", "object_digest": digest,
            "choice": "finish", "reason": "F0 初始化"},
           {"source": "human (sess-F)", "at": at, "subject": ".wf/project-config.json,.wf/baseline.md,.wf/spec/index.md",
            "object_digest": digest, "choice": "commit", "reason": "授权提交初始化产物"}],
          open("/tmp/f0_archive.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/f0_archive.json", "--json"], inputs)
rec("归档", "pass", (payload or {}).get("code"), rc == 0)
json.dump(results, open("/tmp/p5_f0_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results))
