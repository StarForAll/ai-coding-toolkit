#!/usr/bin/env python3
"""F1 夹具：初始化任务闭环（task-new → approve → start → baseline-apply → check → knowledge → archive）。"""
import hashlib, json, os, subprocess, sys

sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
TASK_TEMPLATE = f"{F}/.wf/templates/task"


def wf(args, inputs=None):
    return wfdrive.run(args, inputs=inputs, show=False)


def step(label, rc, payload):
    code = (payload or {}).get("code")
    print(f"[{label}] exit={rc} code={code}")
    if rc != 0:
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:2000])
        raise SystemExit(f"stopped at {label}")
    return payload


rc, payload, out = wf(["task-new", "--kind", "initialize", "--title", "初始化项目基线",
                     "--template", TASK_TEMPLATE, "--json"])
payload = step("task-new", rc, payload)
task_id = payload["facts"]["task_id"]
task_dir = os.path.join(F, payload["facts"]["directory"])
generation = payload["facts"]["generation"]

prd = '''# 初始化项目基线

## 目标

为已有项目建立 wf 活基线、项目配置与 spec 骨架，使后续普通任务具备开工前置。

## 范围与触碰面

- `.wf/baseline.md`
- `.wf/project-config.json`
- `.wf/spec/{index.md,pre-dev-checklist.md,quality-checklist.md}`

## 方案说明

按发行模板成组生成；不导入外部知识、不建索引服务。治理面 paths 保持空数组并把原因记入块内。

## 不做项

不改业务代码、不改 README、不引入依赖、不配置 python_executable。

## 机读块

<!-- wf-plan:v1 -->
```json
{
  "schema_version": 1,
  "touch_paths": [
    ".wf/baseline.md",
    ".wf/project-config.json",
    ".wf/spec/index.md",
    ".wf/spec/pre-dev-checklist.md",
    ".wf/spec/quality-checklist.md"
  ],
  "acceptance": [
    {"id": "a1", "statement": "基线、项目配置与 spec 骨架均已生成且可被解析", "verification_ids": ["v1"]}
  ],
  "verifications": [
    {"id": "v0", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print('start ok')"]},
     "cwd": ".", "input_refs": [], "required": true, "consume_at": "start"},
    {"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "import json, os; json.load(open('.wf/project-config.json')); [os.stat(p) for p in ('.wf/baseline.md', '.wf/spec/index.md')]; print('config ok')"]},
     "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}
  ]
}
```

## 待决问题

plan-q-1：初始化任务是否按轻量处理（仅生成骨架文件、不触碰既有治理面与外部契约）？推荐答案：是。
'''
open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
prd_digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
at = "2026-11-03T01:00:00.000000Z"
approve = [
    {"source": "human terminal (session A)", "at": at, "subject": "approve plan for initialize task",
     "object_digest": prd_digest, "choice": "approve", "reason": "范围仅骨架文件，验收由 v1 机械核验；接受轻量分级"},
    {"source": "human terminal (session A)", "at": at, "subject": "plan-q-1：初始化任务是否按轻量处理",
     "object_digest": prd_digest, "choice": "是", "reason": "接受推荐项"},
]
json.dump(approve, open("/tmp/decision_approve_init.json", "w"), ensure_ascii=False, indent=2)

inputs = {"generation": generation, "complexity": "light",
          "downgrade": {"reason": "初始化任务只生成骨架文件，不触碰既有治理面与外部契约",
                        "evidence": "治理面块随本任务首次生成且 paths 为空；不修改业务代码与依赖"}}
rc, payload, _ = wf(["task-approve", "--task", task_id, "--decision", "/tmp/decision_approve_init.json", "--json"],
                    inputs)
payload = step("task-approve", rc, payload)
print("   plan_version:", payload["facts"]["plan_version"])

rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
payload = step("task-start", rc, payload)

# baseline-apply：生成基线、配置与 spec 骨架
skeleton = json.load(open(f"{F}/.wf/templates/project-config.skeleton.json"))
skeleton["project_id"] = os.urandom(16).hex()
baseline = open(f"{F}/.wf/templates/baseline.md", encoding="utf-8").read()
now = "2026-11-03T01:10:00Z"
baseline = (baseline
            .replace("{{WF_REQUIRED:scope}}", "为示例项目建立 wf 基线；范围为 src/ 与 tests/ 下的既有代码。")
            .replace("{{WF_REQUIRED:non-goals}}", "不新增业务功能，不改构建方式。")
            .replace("{{WF_REQUIRED:acceptance}}", "验证命令通过，spec 索引可读。")
            .replace("{{WF_REQUIRED:architecture}}", "单包 Python 项目：src/ 为代码，tests/ 为测试。")
            .replace("{{WF_REQUIRED:risks}}", "无外部依赖；回退方式为删除 .wf/ 后重装。")
            .replace("{{WF_REQUIRED:verification-commands}}", "/usr/bin/python3 -c \"from src.calc import add; assert add(1,2)==3\"")
            .replace('"__WF_REQUIRED__"', '"本项目暂无特别约束路径（初始化任务审定）"', 1)
            .replace('"__WF_REQUIRED__"', '"dsh session A"', 1)
            .replace('"__WF_REQUIRED__"', '"2026-11-03"', 1))
files = [
    {"path": ".wf/project-config.json", "content": json.dumps(skeleton, indent=2, ensure_ascii=False) + "\n"},
    {"path": ".wf/baseline.md", "content": baseline},
    {"path": ".wf/spec/index.md", "content": open(f"{F}/.wf/templates/spec/index.md", encoding="utf-8").read()},
    {"path": ".wf/spec/pre-dev-checklist.md",
     "content": open(f"{F}/.wf/templates/spec/pre-dev-checklist.md", encoding="utf-8").read()},
    {"path": ".wf/spec/quality-checklist.md",
     "content": open(f"{F}/.wf/templates/spec/quality-checklist.md", encoding="utf-8").read()},
]
for entry in files:
    entry["before"] = None  # 初始化：目标文件此前不存在
proposal = {"files": files,
            "decision": {"source": "human terminal", "at": at, "subject": "baseline proposal for initialize task",
                         "object_digest": None, "choice": "approve",
                         "reason": "初始化任务按已批准 PRD 生成骨架"}}
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import records as _records
proposal["decision"]["object_digest"] = _records.plain_digest({"files": files})
json.dump(proposal, open("/tmp/proposal_init.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["baseline-apply", "--task", task_id, "--proposal", "/tmp/proposal_init.json", "--json"], inputs)
payload = step("baseline-apply", rc, payload)
print("   written:", payload["facts"]["written"])

notes = {"standard": {"conclusion": "pass", "basis": "生成文件与模板一致，逐项人工核对"},
         "requirement": {"conclusion": "pass", "basis": "验收项 a1 由 v1 机械核验"}}
json.dump(notes, open("/tmp/review_notes_init.json", "w"), ensure_ascii=False, indent=2)

rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", "/tmp/review_notes_init.json", "--json"], inputs)
payload = step("task-check", rc, payload)
print("   check:", payload["facts"]["check"])

rc, payload, _ = wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], inputs)
payload = step("task-knowledge", rc, payload)

grant_paths = [item["path"] for item in files]
archive_decisions = [
    {"source": "human terminal (session A)", "at": "2026-11-03T01:20:00.000000Z",
     "subject": f"finish {task_id}: 人已了解结果与未核实项", "object_digest": prd_digest,
     "choice": "finish", "reason": "初始化产物已核验，验收 a1 通过"},
    {"source": "human terminal (session A)", "at": "2026-11-03T01:20:00.000000Z",
     "subject": ",".join(grant_paths), "object_digest": prd_digest,
     "choice": "commit", "reason": "授权提交本次初始化产物及其任务记录"},
]
json.dump(archive_decisions, open("/tmp/decision_archive_init.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["archive", "--task", task_id, "--decision", "/tmp/decision_archive_init.json", "--json"], inputs)
payload = step("archive", rc, payload)
print("   archive:", json.dumps(payload["facts"], ensure_ascii=False)[:600])
rc, payload, out = wf(["writer", "release", "--json"], inputs)
step("writer-release", rc, payload)
print("TASK_ID", task_id)
