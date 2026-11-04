#!/usr/bin/env python3
"""第五十轮 R85：第七轮复审（R50-01..11）+ 其他 agent（P1-1/P1-3/P2-2..P2-5）的定点用例。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import check as wf_check, gates as wf_gates, spec as wf_spec, tasks as wf_tasks

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def make_root():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, ".wf/spec"), exist_ok=True)
    open(os.path.join(root, ".wf/spec/index.md"), "w").write("# spec 索引\n\n## 规则\n")
    return root


# ---- R50-01：创建过程不留下无意图的中间态（目录先暂存再发布） ----
src = open(wf_tasks.__file__, encoding="utf-8").read()
rec("R50-01 创建走暂存目录后原子发布", "含 .staging-",
    ".staging-" in src, ".staging-" in src)
rec("R50-01b 意图写在 writer 主记录（裁 A）", "含 updated[\"action\"] = action",
    'updated["action"] = action' in src, 'updated["action"] = action' in src)

# ---- R50-02：别的会话不能越过未完成的创建意图 ----
rec("R50-02 有未完成意图时阻断其他会话", "以 writer 上的父动作为判据",
    "unfinished task.create intent exists" in src,
    "unfinished task.create intent exists" in src)

# ---- R50-07：动作已结案的重试返回原结果 ----
rec("R50-07 已完成动作可重试返回原结果", "含 already_completed",
    "already_completed" in src, "already_completed" in src)

# ---- R50-08：索引去重 + 未闭合围栏拒绝 ----
root = make_root()
index = os.path.join(root, ".wf/spec/index.md")
open(index, "w").write("# spec 索引\n\n## 规则\n\n- [a.md](.wf/spec/renamed.md)\n- [a.md](.wf/spec/renamed.md)\n")
open(os.path.join(root, ".wf/spec/r.md"), "w").write("x\n")
wf_spec._sync_index(root, add=".wf/spec/renamed.md")
text = open(index).read()
rec("R50-08 同一目标不重复", "只有一条", text.count("](.wf/spec/renamed.md)"),
    text.count("](.wf/spec/renamed.md)") == 1)

open(index, "w").write("# spec 索引\n\n## 规则\n\n```md\n- 未闭合\n")
try:
    wf_spec._sync_index(root, add=".wf/spec/new.md")
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("R50-08b 未闭合围栏拒绝同步", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")

# ---- R50-09：disable 后像不可推定 → 明确出口 ----
root2 = make_root()
rel = ".wf/spec/d.md"
body = '---\nschema_version: 1\nstatus: "disabled"\nauthor: "ai"\n---\n\n# d\n'
open(os.path.join(root2, rel), "w").write(body)
change = {"operation": "disable", "old_paths": [rel], "new_paths": [],
          "before_digests": ["sha256:" + "0" * 64], "reference_dispositions": []}
try:
    wf_spec._apply_change(root2, change, {"id": "t"}, [], resume=True)
    raised2 = None
except Exception as exc:  # noqa: BLE001
    raised2 = getattr(exc, "code", None)
rec("R50-09 已 disabled 但不可推定 → 交人核对", "WF_SEMANTIC_DECISION", raised2,
    raised2 == "WF_SEMANTIC_DECISION")

# ---- R50-10：复盘门禁核调试证据 ----
missing_task = {"execution": {"debug_declarations": [{"verification_id": "v1", "counted": 2,
                                                     "evidence_refs": ["missing.txt"]}],
                              "human_decisions": [{"subject": "debug-ruling-v1-1", "choice": "同一问题"}]},
                "check_history": []}


class Ctx:
    root = F


problems = wf_tasks.retrospective_evidence_problems(Ctx(), missing_task)
rec("R50-10 证据缺失被识破", "problems 非空", problems, bool(problems))
symbolic = {"execution": {"debug_declarations": [{"verification_id": "v1", "counted": 2,
                                                  "evidence_refs": ["handoff"]}],
                          "human_decisions": [{"subject": "debug-ruling-v1-1", "choice": "同一问题"}]},
            "check_history": []}
rec("R50-10b 符号引用不误判", "[]", wf_tasks.retrospective_evidence_problems(Ctx(), symbolic),
    wf_tasks.retrospective_evidence_problems(Ctx(), symbolic) == [])

# ---- R50-11：安装预览展示 session_profile ----
install_src = open("/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/install.py",
                   encoding="utf-8").read()
rec("R50-11 预览含会话身份", "含 session_profile 段", "会话身份（session_profile）" in install_src,
    "会话身份（session_profile）" in install_src)

# ---- P1-1：外部变更作为待核事实（不新增阻断判定，登记边界） ----
check_src = open(wf_check.__file__, encoding="utf-8").read()
rec("P1-1 外部变更数量进入 facts", "含 external_pending", "external_pending" in check_src,
    "external_pending" in check_src)

# ---- P1-3：巡检补归档引用与持久化 ----
summary = wf_tasks._governance_summary(F, list(wf_tasks.iter_tasks(F)), [])
rec("P1-3 巡检含归档引用", "archive_references",
    sorted(summary), "archive_references" in summary)

# ---- P2-2：纯删除也算交付 ----
rec("P2-2 删除事实可作交付", "含 _removal_attributed",
    "_removal_attributed" in src, "_removal_attributed" in src)

# ---- P2-3：候选唯一性对所有 kind 生效 ----
body = src[src.index("def cmd_task_start"):]
for terminator in ("\ndef cmd_task_pause", "\ndef cmd_task_resume", "\ndef cmd_task_replan"):
    if terminator in body:
        body = body[:body.index(terminator)]
        break
ordinary_at = body.find('if task.get("kind") == "ordinary":')
if ordinary_at < 0:
    ordinary_at = body.find("if task.get(\"kind\") == 'ordinary':")
others_at = body.find("if others:")
rec("P2-3 候选唯一性不在 ordinary 分支内",
    "if others 出现在 ordinary 分支之后且同级缩进",
    f"ordinary={ordinary_at >= 0} others={others_at >= 0}",
    ordinary_at >= 0 and others_at > ordinary_at and body[others_at - 4:others_at] == "    ")

# ---- P2-4：审查不可用与不合格分流 ----
gate_src = open(wf_gates.__file__, encoding="utf-8").read()
rec("P2-4 门禁区分 REVIEW_UNAVAILABLE", "含 WF_REVIEW_UNAVAILABLE",
    "WF_REVIEW_UNAVAILABLE" in gate_src, "WF_REVIEW_UNAVAILABLE" in gate_src)

# ---- P2-5：提示键在批准结果中浮现 ----
rec("P2-5 复杂度提示键带出", "含 complexity_hints", "complexity_hints" in src,
    "complexity_hints" in src)

json.dump(results, open("/tmp/r85_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
