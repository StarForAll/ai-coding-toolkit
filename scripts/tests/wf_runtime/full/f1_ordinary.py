#!/usr/bin/env python3
"""F1 夹具：普通任务闭环（新会话 B）。"""
import hashlib, json, os, sys

sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
SID = "sess-B"


def wf(args, inputs=None):
    return wfdrive.run(args, inputs=inputs, sid=SID, show=False)


def step(label, rc, payload):
    print(f"[{label}] exit={rc} code={(payload or {}).get('code')}")
    if rc != 0:
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:2500])
        raise SystemExit(f"stopped at {label}")
    return payload


rc, payload, _ = wf(["enable", "--json"])
step("enable", rc, payload)
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "新增 multiply 函数",
                     "--template", f"{F}/.wf/templates/task", "--json"])
payload = step("task-new", rc, payload)
task_id = payload["facts"]["task_id"]
task_dir = os.path.join(F, payload["facts"]["directory"])
generation = payload["facts"]["generation"]

prd = '''# 新增 multiply 函数

## 目标

在示例项目中新增 `multiply(a, b)` 并配一条单元测试。

## 范围与触碰面

- `src/calc.py`
- `tests/test_calc.py`

## 方案说明

沿用既有函数风格，新增纯函数并补断言；验证命令直接调用该函数。

## 不做项

不改 README，不改依赖，不动 `add`。

## 机读块

<!-- wf-plan:v1 -->
```json
{
  "schema_version": 1,
  "touch_paths": ["src/calc.py", "tests/test_calc.py"],
  "acceptance": [
    {"id": "a1", "statement": "multiply 在正数与负数用例上返回正确结果", "verification_ids": ["v1"]}
  ],
  "verifications": [
    {"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "from src.calc import multiply; assert multiply(3,4)==12 and multiply(-2,5)==-10; print('multiply ok')"]},
     "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}
  ]
}
```

## 待决问题

plan-q-1：是否按轻量处理（仅一个纯函数与一条测试，验收由本任务自行定义）？推荐答案：是。
'''
open(os.path.join(task_dir, "prd.md"), "w", encoding="utf-8").write(prd)
prd_digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
at = "2026-11-03T02:00:00.000000Z"
json.dump([
    {"source": "human terminal (session B)", "at": at, "subject": "approve plan for multiply task",
     "object_digest": prd_digest, "choice": "approve", "reason": "范围两个文件，验收机械可核"},
    {"source": "human terminal (session B)", "at": at, "subject": "plan-q-1：是否按轻量处理",
     "object_digest": prd_digest, "choice": "是", "reason": "接受推荐项"},
], open("/tmp/decision_approve_multiply.json", "w"), ensure_ascii=False, indent=2)

inputs = {"generation": generation}
rc, payload, _ = wf(["task-approve", "--task", task_id,
                     "--decision", "/tmp/decision_approve_multiply.json", "--json"], inputs)
step("task-approve", rc, payload)
rc, payload, _ = wf(["task-start", "--task", task_id, "--json"], inputs)
step("task-start", rc, payload)

# 实施（AI 在批准范围内起草）
calc = open(os.path.join(F, "src/calc.py"), encoding="utf-8").read()
if "multiply" not in calc:
    calc += "\n\ndef multiply(a, b):\n    return a * b\n"
open(os.path.join(F, "src/calc.py"), "w", encoding="utf-8").write(calc)
tests = open(os.path.join(F, "tests/test_calc.py"), encoding="utf-8").read()
if "multiply" not in tests:
    tests += "\n\ndef test_multiply():\n    from src.calc import multiply\n    assert multiply(3, 4) == 12\n    assert multiply(-2, 5) == -10\n"
open(os.path.join(F, "tests/test_calc.py"), "w", encoding="utf-8").write(tests)

notes = {"standard": {"conclusion": "pass", "basis": "新增纯函数，未改既有 add；命名与风格一致"},
         "requirement": {"conclusion": "pass", "basis": "验收 a1 由 v1 覆盖正负用例"}}
json.dump(notes, open("/tmp/review_notes_multiply.json", "w"), ensure_ascii=False, indent=2)

rc, payload, _ = wf(["task-check", "--task", task_id,
                     "--review-notes", "/tmp/review_notes_multiply.json", "--json"], inputs)
payload = step("task-check", rc, payload)
print("   anchor:", payload["facts"]["anchor"]["check_anchor"])

rc, payload, _ = wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], inputs)
step("task-knowledge", rc, payload)

json.dump([
    {"source": "human terminal (session B)", "at": "2026-11-03T02:10:00.000000Z",
     "subject": f"finish {task_id}: 人已了解检查结果与未核实项", "object_digest": prd_digest,
     "choice": "finish", "reason": "轻量任务，验收 a1 通过，双轴审查完成"},
    {"source": "human terminal (session B)", "at": "2026-11-03T02:10:00.000000Z",
     "subject": "src/calc.py,tests/test_calc.py", "object_digest": prd_digest,
     "choice": "commit", "reason": "授权提交本任务两个交付路径"},
], open("/tmp/decision_archive_multiply.json", "w"), ensure_ascii=False, indent=2)
rc, payload, _ = wf(["archive", "--task", task_id,
                     "--decision", "/tmp/decision_archive_multiply.json", "--json"], inputs)
payload = step("archive", rc, payload)
print("   archived:", payload["facts"]["terminal"], payload["facts"]["moved_to"])
rc, payload, _ = wf(["writer", "release", "--json"], inputs)
step("writer-release", rc, payload)
print("TASK_ID", task_id)
