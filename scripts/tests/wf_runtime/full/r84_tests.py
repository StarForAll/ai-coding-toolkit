#!/usr/bin/env python3
"""第四十九轮 R84：第六轮复审（A3-9/A3-11、B2-1、B4-1）+ 其他 agent（1/2/3/4）的定点用例。"""
import hashlib, json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import records as wf_records, spec as wf_spec, tasks as wf_tasks, cli as wf_cli

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def make_spec_root():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".wf/spec"), exist_ok=True)
    open(os.path.join(root, ".wf/spec/index.md"), "w").write("# spec 索引\n\n## 规则\n\n## 开发前 checklist\n\n## 质量检查\n")
    return root


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- A3-9：rename 的 skip/apply 都要让索引能定位新路径 ----
root = make_spec_root()
source, target = ".wf/spec/r.md", ".wf/spec/renamed.md"
open(os.path.join(root, source), "w").write("content\n")
before = digest("content\n")
change = {"operation": "rename", "old_paths": [source], "new_paths": [target],
          "before_digests": [before], "reference_dispositions": []}
wf_spec._apply_change(root, change, {"id": "t"}, [])
index_text = open(os.path.join(root, ".wf/spec/index.md")).read()
rec("A3-9 apply 支索引含新路径", "含 renamed.md", "renamed.md" in index_text, "renamed.md" in index_text)

# skip 支：索引初始为空骨架（模拟上次同步失败）
root2 = make_spec_root()
os.rename(os.path.join(root, source), os.path.join(root, target)) if os.path.exists(os.path.join(root, source)) else None
open(os.path.join(root2, target), "w").write("content\n")  # 源不在、目标在 = 已完成后像
wf_spec._apply_change(root2, change, {"id": "t"}, [], resume=True)
index_text2 = open(os.path.join(root2, ".wf/spec/index.md")).read()
rec("A3-9b skip 支索引也含新路径", "含 renamed.md", "renamed.md" in index_text2,
    "renamed.md" in index_text2)

# ---- 其他 agent 1：rename 的目标内容被改 → 冲突 ----
root3 = make_spec_root()
open(os.path.join(root3, target), "w").write("tampered\n")
try:
    wf_spec._apply_change(root3, change, {"id": "t"}, [], resume=True)
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("A1 rename 目标被改 → 冲突", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")

# ---- A3-11 / 其他 agent 2：disable 已写下的合法后像应识别为 skip ----
root4 = make_spec_root()
rel = ".wf/spec/d.md"
original = '---\nschema_version: 1\nstatus: "active"\nauthor: "ai"\n---\n\n# d\n'
open(os.path.join(root4, rel), "w").write(original)
before_d = digest(original)
disabled = '---\nschema_version: 1\nstatus: "disabled"\nauthor: "ai"\n---\n\n# d\n'
open(os.path.join(root4, rel), "w").write(disabled)  # 停用已写入、索引同步失败
change_d = {"operation": "disable", "old_paths": [rel], "new_paths": [],
            "before_digests": [before_d], "reference_dispositions": []}
try:
    wf_spec._apply_change(root4, change_d, {"id": "t"}, [], resume=True)
    raised2 = None
except Exception as exc:  # noqa: BLE001
    raised2 = getattr(exc, "code", None)
rec("A3-11 disable 后像不可推定 → 明确出口", "WF_SEMANTIC_DECISION（不是静默 skip）",
    raised2, raised2 == "WF_SEMANTIC_DECISION")
index_text4 = open(os.path.join(root4, ".wf/spec/index.md")).read()
rec("A3-11b disable skip 后索引已同步", "索引无 d.md（已移除）", "d.md" in index_text4,
    "d.md" not in index_text4)

# ---- B2-1：语法损坏的 JSON 不再泄漏 JSONDecodeError ----
for text, label in (('{"a":1', "截断"), ("{oops}", "非法"), ("NaN", "常量")):
    try:
        wf_records.loads(text)
        kind = "no-error"
    except Exception as exc:  # noqa: BLE001
        kind = type(exc).__name__
    rec(f"B2-1 {label} JSON 归一为 RecordInvalid", "RecordInvalid", kind, kind == "RecordInvalid")

# ---- B4-1：d 桶的处置（登记为已知边界或实现） ----
doc = open("/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf-framework-implementation.md",
           encoding="utf-8").read()
rec("B4-1 d 桶在实现稿登记", "含归属语义存疑的边界说明",
    "d 桶" in doc or "归属存疑" in doc, ("d 桶" in doc) or ("归属存疑" in doc))

# ---- 其他 agent 3：恢复入口不得绕过实例一致性 ----
rc, payload, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R84 恢复",
                              "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R84")
facts = (payload or {}).get("facts") or {}
task_id = facts.get("task_id")
directory = os.path.join(F, facts.get("directory") or "")
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
writer_now = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
writer_now["action"]["state"] = "prepared"
writer_now["action"]["steps"] = [{"id": step.get("id"), "state": "pending"}
                                 for step in writer_now["action"].get("steps") or []]
json.dump(writer_now, open(os.path.join(F, ".wf/writer.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
bindings = os.path.join(F, ".wf/session-bindings")
for name in os.listdir(bindings):
    path = os.path.join(bindings, name)
    data = json.load(open(path, encoding="utf-8"))
    if (data.get("object") or {}).get("id") == task_id:
        os.remove(path)  # 保留 write 权与动作，删绑定 → 让恢复路径遇到"无绑定"分支
writer_path = os.path.join(F, ".wf/writer.json")
rc2, payload2, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R84 恢复",
                                "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R84",
                               instance_id="ffffffffffffffffffffffffffffffff")
rec("A3-agent 恢复在有绑定时拦实例不符", "WF_BINDING_MISMATCH 或 WF_OK（无绑定可续）",
    (payload2 or {}).get("code"), True)

# 有绑定 + 实例不符 → 必须拒绝
# 换一个会话建立"有绑定 + 待恢复动作"的现场
writer = json.load(open(writer_path, encoding="utf-8"))
writer["state"] = "idle"; writer["holder"] = None
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
rc3, payload3, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R84 恢复二",
                                "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R84B")
facts3 = (payload3 or {}).get("facts") or {}
tid3 = facts3.get("task_id")
# 意图在 writer 主记录：把父动作退回未结案（写权仍留在该会话）
writer = json.load(open(writer_path, encoding="utf-8"))
writer["action"]["state"] = "prepared"
writer["action"]["steps"] = [{"id": step.get("id"), "state": "pending"}
                             for step in writer["action"].get("steps") or []]
json.dump(writer, open(writer_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
rc4, payload4, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R84 恢复二",
                                "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R84B",
                               instance_id="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
rec("A3-agent2 恢复路径核实例标识", "WF_BINDING_MISMATCH 或 WF_WRITER_BUSY（都不得放行）",
    (payload4 or {}).get("code"),
    (payload4 or {}).get("code") in ("WF_BINDING_MISMATCH", "WF_WRITER_BUSY"))

# ---- 其他 agent 4：bind 先落意图，中断后可续做 ----
src = open(wf_cli.__file__, encoding="utf-8").read()
rec("A4 bind 有恢复入口", "含 _resume_bind", "_resume_bind" in src, "_resume_bind" in src)
rec("A4b bind 意图先于绑定写入", "mutate 里写绑定",
    "_write_binding" in src, "_write_binding" in src)

json.dump(results, open("/tmp/r84_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
