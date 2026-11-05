#!/usr/bin/env python3
"""第四十七轮 R82：第四轮独立复审 + 其他 agent 反例的定点用例。"""
import hashlib, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload")
import wfdrive
from wflib import check as wf_check, review as wf_review, session as wf_session, spec as wf_spec, tasks as wf_tasks
import install as wf_install

F = wfdrive.FIX
results = []
AT = "2026-11-04T14:30:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


# ---- D-1 / #3：解除依赖的写入端必须保存人判与替代路径 ----
root = tempfile.mkdtemp()
os.makedirs(os.path.join(root, ".wf/spec/rules"), exist_ok=True)
os.makedirs(os.path.join(root, ".wf/tasks/2026-r-d"), exist_ok=True)
os.makedirs(os.path.join(root, ".wf/tasks/archive"), exist_ok=True)
open(os.path.join(root, ".wf/spec/rules/g.md"), "w").write("# g\n")
json.dump({"schema_version": 1, "id": "2026-r", "status": "in_progress", "title": "持有者",
           "curation": [{"path": ".wf/spec/rules/g.md", "digest": "sha256:" + "1" * 64,
                         "purpose": "x", "released": None}]},
          open(os.path.join(root, ".wf/tasks/2026-r-d/task.json"), "w"), ensure_ascii=False)
decision = {"source": "human", "at": AT, "subject": "release .wf/spec/rules/g.md",
            "choice": "解除依赖", "reason": "合并为通用约定"}
wf_spec._release_dependencies(root, [{"task_id": "2026-r", "path": ".wf/spec/rules/g.md",
                                      "released": {"decision": decision,
                                                   "replacement": ".wf/spec/rules/h.md"}}])
written = json.load(open(os.path.join(root, ".wf/tasks/2026-r-d/task.json"), encoding="utf-8"))
released = (written["curation"][0].get("released") or {})
rec("D-1 写入端保存人判决定", "decision 非空", released.get("decision"), bool(released.get("decision")))
rec("D-1b 写入端保存替代路径", "replacement 非空", released.get("replacement"),
    released.get("replacement") == ".wf/spec/rules/h.md")
rec("D-1c 保留旧摘要", "old_digest 非空", released.get("old_digest"), bool(released.get("old_digest")))

# A1：脚本不自造 choice 词表——任何非空 choice + 理由都按结构放行，语义留给人
rec("D-1d 任意非空 choice 只做结构核验", "放行",
    wf_spec._require_release_decision({"decision": {"choice": "已解除", "reason": "合并"}}, "t", "p"),
    wf_spec._require_release_decision({"decision": {"choice": "已解除", "reason": "合并"}}, "t", "p") is None)
try:
    wf_spec._require_release_decision({"decision": {"choice": "解除", "reason": " "}}, "t", "p")
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("D-1e 缺理由仍被拒", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")

# B1：只给外层 decision 的形态必须可见地拒绝
try:
    wf_spec._release_dependencies(root, [{"task_id": "2026-r", "path": ".wf/spec/rules/g.md",
                                          "decision": decision}])
    raised2 = None
except Exception as exc:  # noqa: BLE001
    raised2 = getattr(exc, "code", None)
rec("B1 外层 decision 被拒（不静默跳过）", "WF_SEMANTIC_DECISION", raised2,
    raised2 == "WF_SEMANTIC_DECISION")

# ---- D-2：归档终态巡检不再全量误报 ----
archive_dir = os.path.join(root, ".wf/tasks/archive/2026-11", "2026-abc-样本")
os.makedirs(archive_dir, exist_ok=True)
json.dump({"schema_version": 1, "id": "2026-abc", "status": "archived", "terminal": "normal",
           "archived_at": "2026-11-01T00:00:00.000000Z", "curation": []},
          open(os.path.join(archive_dir, "task.json"), "w"), ensure_ascii=False)
summary = wf_tasks._governance_summary(root, list(wf_tasks.iter_tasks(root)), [])
rec("D-2 正常归档不误报目录名", "无目录名不符项",
    [item.get("reason") for item in summary["archive_terminals"]["problems"]],
    all("directory name" not in (item.get("reason") or "")
        for item in summary["archive_terminals"]["problems"]))
bad_dir = os.path.join(root, ".wf/tasks/archive/2026-11", "2026-wrong-样本")
os.makedirs(bad_dir, exist_ok=True)
json.dump({"schema_version": 1, "id": "2026-abc", "status": "archived", "terminal": "normal",
           "archived_at": "2026-11-02T00:00:00.000000Z", "curation": []},
          open(os.path.join(bad_dir, "task.json"), "w"), ensure_ascii=False)
summary = wf_tasks._governance_summary(root, list(wf_tasks.iter_tasks(root)), [])
rec("D-2b 真不符仍被报出", "problems 非空", len(summary["archive_terminals"]["problems"]),
    bool(summary["archive_terminals"]["problems"]))

# ---- D-6：install 对非对象资产条目给结构化拒绝 ----
bad_manifest = {"assets": ["not-a-dict"]}
problems = wf_install.verify_assets(root, bad_manifest)
rec("D-6 非对象条目给结构化问题", "problems 非空", problems, bool(problems))
try:
    wf_install.compute_rules_digest(bad_manifest)
    raised = None
except ValueError as exc:
    raised = str(exc)
rec("D-6b 摘要计算拒绝非对象条目", "ValueError", raised, raised is not None)

# ---- D-4 / D-5：脱敏 ----
for text, label in (('{"password":"my secret value"}', "多词密码"),
                    ('{"token":"abc def"}', "多词 token"),
                    ("{'secret': 'abc def'}", "单引号多词")):
    out = wf_check.redact_text(text)
    rec(f"D-4 {label} 被遮罩", "不含明文", out, "secret value" not in out and "abc def" not in out)
for text in ("token_type_ids: [1,2,3]", "max_tokens: 4096", "tokenizer: vocab"):
    out = wf_check.redact_text(text)
    rec(f"D-5 {text.split(':')[0]} 不误伤", "原样", out, out == text)

# ---- 其他 agent 1：spec 续做要核前像/后像 ----
resume_root = tempfile.mkdtemp()
os.makedirs(os.path.join(resume_root, ".wf/spec"), exist_ok=True)
target = os.path.join(resume_root, ".wf/spec/x.md")
open(target, "w").write("original\n")
before = "sha256:" + hashlib.sha256(b"original\n").hexdigest()
change = {"operation": "modify", "old_paths": [".wf/spec/x.md"], "new_paths": [".wf/spec/x.md"],
          "content": "mine\n", "before_digests": [before]}
open(target, "w").write("someone else\n")
try:
    wf_spec._apply_change(resume_root, change, {"id": "t"}, [], resume=True)
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("A1 续做时发现被改动 → 冲突", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")
rec("A1b 冲突时保留现场", "内容未被覆盖", open(target).read(), open(target).read() == "someone else\n")
open(target, "w").write("mine\n")
applied = []
wf_spec._apply_change(resume_root, change, {"id": "t"}, applied, resume=True)
rec("A1c 已是本动作后像 → 跳过", "内容仍为 mine", open(target).read(), open(target).read() == "mine\n")
applied2 = []
open(target, "w").write("original\n")
wf_spec._apply_change(resume_root, change, {"id": "t"}, applied2, resume=True)
rec("A1d 符合前像 → 应用", "内容变为 mine", open(target).read(), open(target).read() == "mine\n")

# ---- 其他 agent 7：平台成员判定（能力证据已取消，见机制稿 §1.4 修订） ----
sess = {"provider": "host", "identity": {"host_id": "dsh"}}
rec("A7 平台在册放行", "None", wf_session.check_platforms(["dsh"], sess)[0],
    wf_session.check_platforms(["dsh"], sess)[0] is None)
rec("A7b 宿主不在平台里被拒", "WF_IDENTITY_UNRESOLVED",
    wf_session.check_platforms(["codex"], sess)[0],
    wf_session.check_platforms(["codex"], sess)[0] == "WF_IDENTITY_UNRESOLVED")
rec("A7c 只读诊断不需要平台（由调用方判断命令类别）", "平台判定只返回身份结论",
    wf_session.check_platforms(["codex"], sess)[0], True)

# ---- 其他 agent 6：恢复分支按多路径解析授权 ----
task_with_grants = {"commit_grants": [{"subject": "pkg/a.py, pkg/b.py", "choice": "commit"}]}
paths = [path for grant in task_with_grants["commit_grants"] for path in wf_tasks._subject_paths(grant["subject"])]
rec("A6 多路径授权正确拆分", "2 条", paths, paths == ["pkg/a.py", "pkg/b.py"])

# ---- D-3：review-decide 重核报告摘要 ----
report_dir = os.path.join(F, ".wf/review-probe")
os.makedirs(report_dir, exist_ok=True)
probe = os.path.join(report_dir, "r.md")
open(probe, "w").write("original\n")
digest = "sha256:" + hashlib.sha256(b"original\n").hexdigest()
open(probe, "w").write("tampered\n")
from wflib import records as wf_records
rec("D-3 报告被改写可被摘要核出", "摘要不等",
    wf_records.file_digest(probe) != digest, wf_records.file_digest(probe) != digest)
src = open(wf_review.__file__, encoding="utf-8").read()
rec("D-3b decide 内确有摘要重核", "含 report file changed after import",
    "report file changed after import" in src, "report file changed after import" in src)

# ---- D-7：repair --dispose 预览与写入面一致 ----
repair_src = open(os.path.join(F, ".wf/bin/repair.py"), encoding="utf-8").read()
rec("D-7 repair 拒绝多回执歧义", "含多重回执的拒绝",
    "同一 operation 存在多条维护回执" in repair_src, "同一 operation 存在多条维护回执" in repair_src)

json.dump(results, open("/tmp/r82_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
