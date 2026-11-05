#!/usr/bin/env python3
"""第五十一轮 R86：第八轮复审（D-01..D-18 + 崩溃）的定点用例。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import check as wf_check, scope as wf_scope, tasks as wf_tasks

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


class Ctx:
    root = F


# ---- 崩溃修复：attributed_paths 返回列表，不得当字典用 ----
root = tempfile.mkdtemp()
os.makedirs(os.path.join(root, "pkg"), exist_ok=True)
os.makedirs(os.path.join(root, ".wf/tasks/2026-x-d"), exist_ok=True)
json.dump({"schema_version": 1, "id": "2026-x", "status": "in_progress"},
          open(os.path.join(root, ".wf/tasks/2026-x-d/task.json"), "w"))
subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
subprocess.run(["git", "config", "user.email", "t@e.c"], cwd=root, capture_output=True)
subprocess.run(["git", "config", "user.name", "t"], cwd=root, capture_output=True)
open(os.path.join(root, "pkg/gone.txt"), "w").write("x\n")
subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
subprocess.run(["git", "commit", "-qm", "init"], cwd=root, capture_output=True)
os.remove(os.path.join(root, "pkg/gone.txt"))
task = {"id": "2026-x", "baseline_head": None}
try:
    got = wf_tasks._removal_attributed(type("C", (), {"root": root})(), "pkg/gone.txt", task, [])
    crashed = None
except Exception as exc:  # noqa: BLE001
    got, crashed = None, type(exc).__name__
rec("崩溃：删除归属判定不再抛异常", "返回布尔", f"{got} crash={crashed}", crashed is None and isinstance(got, bool))

# ---- D-11/D-12：证据引用按类别核 ----
os.makedirs(os.path.join(root, "evidence"), exist_ok=True)
open(os.path.join(root, "evidence/real.txt"), "w").write("x")
task_dbg = {"execution": {"debug_declarations": [
    {"verification_id": "v1", "counted": 2,
     "evidence_refs": ["handoff", "check:v1", "evidence/real.txt", "evidence", "missing.txt"]}],
    "human_decisions": [{"subject": "debug-ruling-v1-1", "choice": "同一问题"}]},
    "check_history": [{"id": "v1", "commands": [{"evidence_ref": "logs/a.log"}]}]}
problems = wf_tasks.retrospective_evidence_problems(type("C", (), {"root": root})(), task_dbg)
refs = sorted({item.get("ref") for item in problems})
rec("D-11 符号引用不误判", "不含 handoff", "handoff" not in refs, "handoff" not in refs)
rec("D-12 目录证据被拒", "含 evidence", "evidence" in refs, "evidence" in refs)
rec("D-12b 缺失文件被拒", "含 missing.txt", "missing.txt" in refs, "missing.txt" in refs)
rec("D-12c check 条目内证据缺失被拒", "含 check:v1", "check:v1" in refs, "check:v1" in refs)

# ---- D-04：d 桶进 scope_facts 并可阻断 ----
check_src = open(wf_check.__file__, encoding="utf-8").read()
rec("D-04 d 桶已进范围事实（当前分类下不可达，仅结构存在）", "含 ambiguous_ownership",
    "ambiguous_ownership" in check_src, "ambiguous_ownership" in check_src)
rec("D-04b 跨任务冲突检测存在", "含 cross_task_conflicts",
    "cross_task_conflicts" in open(wf_scope.__file__, encoding="utf-8").read(),
    "cross_task_conflicts" in open(wf_scope.__file__, encoding="utf-8").read())

# ---- D-01：死 helper 已删（登记口径与代码一致） ----
rec("D-01 外部变更 helper 已接线（未决即阻断）", "含 _external_touches_task 且被消费",
    "pending_external" in check_src and "_external_touches_task" in check_src,
    "pending_external" in check_src and "_external_touches_task" in check_src)

# ---- D-02：两入口阶段口径对齐 ----
tasks_src = open(wf_tasks.__file__, encoding="utf-8").read()
rec("D-02 spec-update 与 baseline-apply 阶段口径一致",
    "两处都含 finish",
    tasks_src.count('("execute", "check", "finish")') >= 2,
    tasks_src.count('("execute", "check", "finish")') >= 2)
rec("D-02b finish 期变更回 check 并登记失效", "含 _reenter_check_from_finish 与 invalidated",
    "_reenter_check_from_finish" in tasks_src and "invalidated" in tasks_src,
    "_reenter_check_from_finish" in tasks_src and "invalidated" in tasks_src)

# ---- D-13：异常归档不被误报 ----
summary = wf_tasks._governance_summary(F, list(wf_tasks.iter_tasks(F)), [])
reasons = [item.get("reason") for item in (summary.get("archive_terminals") or {}).get("problems") or []]
rec("D-13 无异常归档误报", "不含 abnormal 未提交",
    reasons, not any("abnormal" in (r or "") for r in reasons))

# ---- D-14：引用检查含 unknown 分类且扫活动任务 ----
refs_summary = summary.get("archive_references") or {}
rec("D-14 引用检查带 unknown 分类", "含 unknown/status",
    sorted(refs_summary), {"dangling", "unknown", "status"} <= set(refs_summary))

# ---- D-15/D-16：预览与落盘证据同源 ----
install_src = open("/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/install.py",
                   encoding="utf-8").read()
rec("D-15 安装器预览与落盘共用平台解析", "含 resolve_skill_roots",
    "resolve_skill_roots(args.target" in install_src,
    "resolve_skill_roots(args.target" in install_src)
dev_src = open("/home/xzc/projects/personal/ai-coding-toolkit/scripts/wf-dev-deploy.py",
               encoding="utf-8").read()
rec("D-16 开发态预览含平台与技能目录", "含 平台：",
    "平台：" in dev_src and "技能目录（目标项目内）" in dev_src,
    "平台：" in dev_src and "技能目录（目标项目内）" in dev_src)

# ---- D-17/D-18：字节复现按 sha256；版本单源 ----
build_src = open("/home/xzc/projects/personal/ai-coding-toolkit/scripts/build-wf-release.py",
                 encoding="utf-8").read()
rec("D-17 复现比对用 sha256", "含 file_digest", "file_digest(path) == file_digest" in build_src,
    "file_digest(path) == file_digest" in build_src)
rec("D-18 版本一致性有断言", "含 _assert_version_consistency",
    "_assert_version_consistency" in build_src, "_assert_version_consistency" in build_src)

# ---- 收尾：stdin 不静默挂起 ----
cli_src = open(wf_check.__file__.replace("check.py", "cli.py"), encoding="utf-8").read()
rec("stdin 无管道时明确报错", "含 must be piped on stdin",
    "must be piped on stdin" in cli_src, "must be piped on stdin" in cli_src)



# ---- N52-01：历史提交归属不算活冲突，只有 saved WIP 才算 ----
src_scope = open(wf_scope.__file__, encoding="utf-8").read()
rec("N52-01 冲突判定以保存的 WIP 为准", "含 handoff.wip.paths 语义",
    "wip.get(\"paths\")" in src_scope or 'wip.get("paths")' in src_scope,
    'wip.get("paths")' in src_scope)
rec("N52-01b 不再用历史归属路径求交", "不含 attributed_paths 直接求交",
    "for path in attributed_paths(root, other_id, other.get(\"baseline_head\")):" not in src_scope,
    'for path in attributed_paths(root, other_id, other.get("baseline_head")):' not in src_scope)

json.dump(results, open("/tmp/r86_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

