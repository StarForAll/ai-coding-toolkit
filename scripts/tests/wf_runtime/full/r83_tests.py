#!/usr/bin/env python3
"""第四十八轮 R83：第五轮独立复审（A1/A2/A3/A5、B1/B2/B3）+ 其他 agent（1/2/3）的定点用例。"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload")
import wfdrive
from wflib import session as wf_session, spec as wf_spec, tasks as wf_tasks
import install as wf_install

F = wfdrive.FIX
results = []
AT = "2026-11-04T15:30:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def digest(text):
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- A1：不自造 choice 词表 ----
decision = {"source": "human", "at": AT, "subject": "x", "choice": "已解除", "reason": "合并规范"}
rec("A1 任意非空 choice 只做结构核验", "放行",
    wf_spec._require_release_decision({"decision": decision}, "t", "p"),
    wf_spec._require_release_decision({"decision": decision}, "t", "p") is None)
try:
    wf_spec._require_release_decision({"decision": {"choice": "解除", "reason": ""}}, "t", "p")
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("A1b 无理由仍被拒", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")

# ---- A2：身份判定只看平台在册（transport/能力证据已随 §1.4 修订取消） ----
sess = {"provider": "host", "identity": {"host_id": "dsh"}}
rec("A2 平台在册放行", "None", wf_session.check_platforms(["dsh"], sess)[0],
    wf_session.check_platforms(["dsh"], sess)[0] is None)
code, facts = wf_session.check_platforms(["codex"], sess)
rec("A2b 宿主未安装被拒并给出出口", "WF_IDENTITY_UNRESOLVED + next",
    f"{code}/{facts.get('next')}", code == "WF_IDENTITY_UNRESOLVED" and bool(facts.get("next")))
code, facts = wf_session.check_platforms([], sess)
rec("A2c 空平台清单被拒", "WF_IDENTITY_UNRESOLVED", code, code == "WF_IDENTITY_UNRESOLVED")
rec("A2d 能力证据常量已删除", "无 SUPPORTED_TRANSPORTS/OBSERVATION_KINDS",
    hasattr(wf_session, "SUPPORTED_TRANSPORTS"),
    not hasattr(wf_session, "SUPPORTED_TRANSPORTS") and not hasattr(wf_session, "OBSERVATION_KINDS"))
rec("A2e 安装器不再写 session_profile", "无 session_profile",
    "session_profile" in open(wf_install.__file__, encoding="utf-8").read(),
    "session_profile" not in open(wf_install.__file__, encoding="utf-8").read())

# ---- A5：delete / disable / rename 的续做三态 ----
root = tempfile.mkdtemp()
os.makedirs(os.path.join(root, ".wf/spec"), exist_ok=True)
target_rel = ".wf/spec/x.md"


def write(text):
    open(os.path.join(root, target_rel), "w").write(text)


def read():
    return open(os.path.join(root, target_rel)).read()


# delete：外部恢复成新内容 → 冲突
write("original\n")
before = digest("original\n")
change_delete = {"operation": "delete", "old_paths": [target_rel], "new_paths": [],
                 "before_digests": [before], "reference_dispositions": []}
write("restored by someone\n")
try:
    wf_spec._apply_change(root, change_delete, {"id": "t"}, [], resume=True)
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("A5 delete 续做遇外部改动被拒", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")
rec("A5b 冲突时保留现场", "内容仍在", read(), read() == "restored by someone\n")
write("original\n")
wf_spec._apply_change(root, change_delete, {"id": "t"}, [], resume=True)
rec("A5c 符合前像才删除", "文件不存在", os.path.exists(os.path.join(root, target_rel)),
    not os.path.exists(os.path.join(root, target_rel)))
wf_spec._apply_change(root, change_delete, {"id": "t"}, [], resume=True)
rec("A5d 已删除再次续做跳过", "不抛异常", True, True)

# disable：外部改动 frontmatter → 冲突
write("---\nschema_version: 1\nstatus: active\nauthor: ai\n---\n\n# x\n")
before_disable = digest(read())
change_disable = {"operation": "disable", "old_paths": [target_rel], "new_paths": [],
                  "before_digests": [before_disable], "reference_dispositions": []}
write("---\nschema_version: 1\nstatus: active\nauthor: someone-else\n---\n\n# x\n")
try:
    wf_spec._apply_change(root, change_disable, {"id": "t"}, [], resume=True)
    raised2 = None
except Exception as exc:  # noqa: BLE001
    raised2 = getattr(exc, "code", None)
rec("A5e disable 续做遇外部改动被拒", "WF_SEMANTIC_DECISION", raised2, raised2 == "WF_SEMANTIC_DECISION")

# rename：源被改 → 冲突
write("source content\n")
before_rename = digest("source content\n")
change_rename = {"operation": "rename", "old_paths": [target_rel], "new_paths": [".wf/spec/y.md"],
                 "before_digests": [before_rename], "reference_dispositions": []}
write("changed by someone\n")
try:
    wf_spec._apply_change(root, change_rename, {"id": "t"}, [], resume=True)
    raised3 = None
except Exception as exc:  # noqa: BLE001
    raised3 = getattr(exc, "code", None)
rec("A5f rename 续做遇外部改动被拒", "WF_SEMANTIC_DECISION", raised3, raised3 == "WF_SEMANTIC_DECISION")

# ---- 其他 agent 3：正文已是后像时仍要补索引 ----
write("original\n")
change_modify = {"operation": "modify", "old_paths": [target_rel], "new_paths": [target_rel],
                 "content": "mine\n", "before_digests": [before]}
write("mine\n")  # 模拟"正文写入成功、索引同步失败"后的中断态
index_path = os.path.join(root, ".wf/spec/index.md")
open(index_path, "w").write("# spec 索引\n\n## 规则\n")
applied = []
wf_spec._apply_change(root, change_modify, {"id": "t"}, applied, resume=True)
index_text = open(index_path).read()
rec("A3-agent 跳过正文时补索引", "索引含该文件", "x.md" in index_text, "x.md" in index_text)

# ---- B1：外层 decision 不静默跳过 ----
try:
    wf_spec._release_dependencies(root, [{"task_id": "t", "path": target_rel, "decision": decision}])
    raised4 = None
except Exception as exc:  # noqa: BLE001
    raised4 = getattr(exc, "code", None)
rec("B1 外层 decision 被可见拒绝", "WF_SEMANTIC_DECISION", raised4, raised4 == "WF_SEMANTIC_DECISION")

# ---- B2：task-new 中断恢复（意图在 writer 上，按原意图续做） ----
# 真实夹具：构造「动作已建、写权未取、绑定未写」→ 同会话重入续做
rc, payload, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R83 恢复",
                              "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R83A")
facts = (payload or {}).get("facts") or {}
task_id = facts.get("task_id")
directory = os.path.join(F, facts.get("directory") or "")
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
# 还原成中断态：动作未结案、绑定删除、写者回 idle
# 意图在 writer 主记录上：把父动作退回 prepared 以模拟中断
writer_path0 = os.path.join(F, ".wf/writer.json")
writer0 = json.load(open(writer_path0, encoding="utf-8"))
writer0["action"]["state"] = "prepared"
writer0["action"]["steps"] = [{"id": step.get("id"), "state": "pending"}
                              for step in writer0["action"].get("steps") or []]
json.dump(writer0, open(writer_path0, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for path in [os.path.join(F, ".wf/session-bindings", name)
             for name in os.listdir(os.path.join(F, ".wf/session-bindings"))]:
    binding = json.load(open(path, encoding="utf-8"))
    if (binding.get("object") or {}).get("id") == task_id:
        os.remove(path)
writer_path = os.path.join(F, ".wf/writer.json")
rc2, payload2, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R83 恢复",
                                "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R83A")
facts2 = (payload2 or {}).get("facts") or {}
if facts2.get("resumed") is not True:
    print("   reentry code:", (payload2 or {}).get("code"),
          (payload2 or {}).get("facts"))
rec("B2c 同会话重入续做同一任务", "resumed=True 且 task_id 不变",
    f"{facts2.get('resumed')}/{facts2.get('task_id') == task_id}",
    facts2.get("resumed") is True and facts2.get("task_id") == task_id)
rec("B2d 不再新建第二个任务", "目录唯一",
    len([name for name in os.listdir(os.path.join(F, ".wf/tasks")) if name.startswith(task_id[:8])]),
    len([name for name in os.listdir(os.path.join(F, ".wf/tasks")) if name.startswith(task_id[:8])]) == 1)

# ---- B3：报告缺失/不可读给结构化拒绝 ----
src = open(__import__("wflib.review", fromlist=["x"]).__file__, encoding="utf-8").read()
rec("B3 decide 对缺失 report_path 有出口", "含 imported entry lacks report_path",
    "imported entry lacks report_path" in src, "imported entry lacks report_path" in src)
rec("B3b decide 对不可读报告有出口", "含 report file unreadable",
    "report file unreadable" in src, "report file unreadable" in src)

json.dump(results, open("/tmp/r83_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
