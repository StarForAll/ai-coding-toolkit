#!/usr/bin/env python3
"""第四十六轮 R81：第三轮独立复审 + 其他 agent 反例的定点用例。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload")
import wfdrive
from wflib import check as wf_check, session as wf_session, spec as wf_spec, assets as wf_assets
import install as wf_install

F = wfdrive.FIX
results = []
AT = "2026-11-04T13:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


# ---- D-B4-1：install 的写入计划必须整批核验 ----
manifest = {"assets": [
    {"target_class": "project_wf", "target_relative": "../escape.txt", "source_path": "x"},
    {"target_class": "project_wf", "target_relative": ".wf/bin/wf.py", "source_path": "x"},
]}
root = tempfile.mkdtemp()
writes, problems = wf_install.plan_writes(root, [root], manifest)
rec("D-B4-1 清单含 ../ 即整批拒绝", "problems 非空且写入为空",
    f"problems={len(problems)} writes={len(writes)}",
    bool(problems) and not writes)

unknown_class = {"assets": [{"target_class": "elsewhere", "target_relative": "a.py"}]}
writes2, problems2 = wf_install.plan_writes(root, [root], unknown_class)
rec("D-B4-1b 未知 target_class 被拒", "problems 非空", len(problems2), bool(problems2))

release_only = {"assets": [{"target_class": "release_only", "target_relative": "install.py"}]}
writes3, problems3 = wf_install.plan_writes(root, [root], release_only)
rec("D-B4-1c release_only 跳过且不报错", "无写入无问题",
    f"writes={len(writes3)} problems={len(problems3)}", not writes3 and not problems3)

# engine 侧 symlink 逃逸
outside = tempfile.mkdtemp()
link_root = tempfile.mkdtemp()
os.symlink(outside, os.path.join(link_root, "linked"))
escape = {"assets": [{"target_class": "project_wf", "target_relative": "linked/x.py"}]}
writes4, problems4 = wf_install.plan_writes(link_root, [link_root], escape)
rec("D-B4-1d 符号链接逃逸被拒", "problems 非空", len(problems4), bool(problems4))

# ---- D-A1-5：manual 验证必须有可核的人判 ----
def manual_task():
    digest = "sha256:" + "a" * 64
    return {"plan": {"version": digest, "approval": {"object_digest": digest},
                     "verifications": [{"id": "v1", "invocation": {"kind": "manual"}}],
                     "acceptance": [{"id": "a1"}]}}


def manual_check(decision):
    return {"result": "pass", "anchor": {"rule_version": "sha256:" + "d" * 64},
            "commands": [{"verification_id": "v1", "status": "passed", "exit_code": None,
                          "invocation": {"kind": "manual"}, "decision": decision}],
            "acceptance_results": [{"acceptance_id": "a1", "conclusion": "passed"}],
            "internal_review": {"standard": {"conclusion": "pass", "basis": "b"},
                                "requirement": {"conclusion": "pass", "basis": "b"}}}


good_decision = {"source": "human", "at": AT, "subject": "v1", "choice": "passed",
                 "object_digest": "sha256:" + "a" * 64, "reason": "人判通过"}  # 绑定批准对象摘要
rec("D-A1-5 有可核人判 → 通过", "[]",
    wf_check.validate_check_result(manual_task(), manual_check(good_decision)),
    wf_check.validate_check_result(manual_task(), manual_check(good_decision)) == [])
for label, decision in (("无 decision", None),
                        ("choice=reject", dict(good_decision, choice="reject")),
                        ("subject 不覆盖", dict(good_decision, subject="别的"))):
    problems = wf_check.validate_check_result(manual_task(), manual_check(decision))
    rec(f"D-A1-5 {label} → 阻断", "非空", [p["reason"] for p in problems][:2], bool(problems))

# ---- D-B1-1：解除依赖必须有有效决定 ----
release_root = tempfile.mkdtemp()
os.makedirs(os.path.join(release_root, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(release_root, ".wf/spec/rules/g.md"), "w").write("# g\n")
try:
    wf_spec._require_release_decision({"decision": None}, "t2", ".wf/spec/rules/g.md")
    raised = None
except Exception as exc:  # noqa: BLE001
    raised = getattr(exc, "code", None)
rec("D-B1-1 空决定被拒", "WF_SEMANTIC_DECISION", raised, raised == "WF_SEMANTIC_DECISION")
try:
    wf_spec._require_release_decision({"decision": {"choice": "解除依赖"}}, "t2", ".wf/spec/rules/g.md")
    raised2 = None
except Exception as exc:  # noqa: BLE001
    raised2 = getattr(exc, "code", None)
rec("D-B1-1b 缺理由被拒", "WF_SEMANTIC_DECISION", raised2, raised2 == "WF_SEMANTIC_DECISION")
ok_release = wf_spec._require_release_decision(
    {"decision": {"choice": "解除依赖", "reason": "合并为通用约定"}}, "t2", ".wf/spec/rules/g.md")
rec("D-B1-1c 有效决定放行", "None", ok_release, ok_release is None)

# ---- 其他 agent 1：json 模式必须交付正文 ----
env = wfdrive.envelope({"generation": 1}, "sess-A1")
rc, payload, _ = wfdrive.run(["spec", "--file", ".wf/spec/index.md", "--json"], {"generation": 1}, "sess-A1")
facts = (payload or {}).get("facts") or {}
rec("A1 json 模式带正文", "content 非空", (facts.get("content") or "")[:10], bool(facts.get("content")))
rec("A1b json 模式 complete 与正文一致", "complete=True 且 content 非空",
    f"{facts.get('complete')}/{bool(facts.get('content'))}",
    facts.get("complete") is True and bool(facts.get("content")))

# ---- 其他 agent 2：task-new 先落恢复意图 ----
rc, payload, _ = wfdrive.run(["task-new", "--kind", "ordinary", "--title", "R81 意图",
                              "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-R81")
facts = (payload or {}).get("facts") or {}
task_id = facts.get("task_id")
writer = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
action = writer.get("action") or {}
step_ids = [step.get("id") if isinstance(step, dict) else step for step in action.get("steps") or []]
rec("A2 task.create 在主记录上且步骤齐备", "writer.action.kind=task.create 且含 bind",
    f"{action.get('kind')}/{step_ids}",
    action.get("kind") == "task.create" and "bind" in step_ids)
rec("A2b 动作已结案", "state=done", action.get("state"), action.get("state") == "done")
rec("A2c 目标固定（writer/task/binding/runtime）", "四个 target",
    sorted({item.get("kind") for item in action.get("targets") or [] if isinstance(item, dict)}),
    {"writer", "task", "binding", "runtime"} <= {item.get("kind") for item in action.get("targets") or []
                                                 if isinstance(item, dict)})

# ---- 其他 agent 3：每个 skill 根各算一项规则指纹 ----
skills_a = tempfile.mkdtemp(); skills_b = tempfile.mkdtemp()
for base, text in ((skills_a, "A"), (skills_b, "B")):
    os.makedirs(os.path.join(base, "wf-x"), exist_ok=True)
    open(os.path.join(base, "wf-x/SKILL.md"), "w").write(text)
asset_manifest = {"assets": [{"target_class": "skill_root", "target_relative": "wf-x/SKILL.md",
                              "kind": "skill"}]}
entries = wf_assets.installed_asset_entries(asset_manifest, {"roots": [skills_a, skills_b]}, root)
rec("A3 两个 skill 根各一项", "2", len(entries), len(entries) == 2)
before = json.dumps(entries, sort_keys=True)
open(os.path.join(skills_b, "wf-x/SKILL.md"), "w").write("B2")
after = wf_assets.installed_asset_entries(asset_manifest, {"roots": [skills_a, skills_b]}, root)
rec("A3b 第二个根改动反映到指纹", "指纹变化", before != json.dumps(after, sort_keys=True),
    before != json.dumps(after, sort_keys=True))

# ---- 其他 agent 6：能力声明必须有结构 ----
profile_bare = {"host_id": "dsh", "provider": "host", "transport": "request_json",
                "capability": {"status": "verified"}}
code, facts = wf_session.check_profile(profile_bare, {"provider": "host", "identity": {"host_id": "dsh"}})
rec("A6 无证据的 verified 被拒", "WF_IDENTITY_UNRESOLVED",
    f"{code}/{facts.get('missing')}", code == "WF_IDENTITY_UNRESOLVED")
profile_full = dict(profile_bare)
profile_full["capability"] = {"status": "verified", "verified_version": "v",
                              "evidence_refs": [{"kind": "compaction", "ref": "x"}]}
code2, _ = wf_session.check_profile(profile_full, {"provider": "host", "identity": {"host_id": "dsh"}})
rec("A6b 结构齐全放行", "None", code2, code2 is None)
profile_notransport = dict(profile_bare); profile_notransport.pop("transport")
code3, _ = wf_session.check_profile(profile_notransport, {"provider": "host", "identity": {"host_id": "dsh"}})
rec("A6c 缺 transport 被拒", "WF_IDENTITY_UNRESOLVED", code3, code3 == "WF_IDENTITY_UNRESOLVED")

# ---- 其他 agent 5：项目键批准证据须对应已批准规划 ----
draft = tempfile.mkdtemp()
os.makedirs(os.path.join(draft, ".wf/tasks/2026-x-draft"), exist_ok=True)
open(os.path.join(draft, ".wf/baseline.md"), "w").write("# baseline\n")
open(os.path.join(draft, ".wf/tasks/2026-x-draft/prd.md"), "w").write("python_executable: /usr/bin/python3\n")
json.dump({"id": "2026-x", "status": "plan", "plan": {"version": None, "approval": None}},
          open(os.path.join(draft, ".wf/tasks/2026-x-draft/task.json"), "w"))
evidence = wf_install.__dict__.get("project_key_approved")
import importlib.util
spec_file = "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/bin/wf.py"
module_spec = importlib.util.spec_from_file_location("wf_boot", spec_file)
boot = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(boot)
rec("A5 草稿 PRD 不作批准证据", "None",
    boot.project_key_approved(draft, "/usr/bin/python3"),
    boot.project_key_approved(draft, "/usr/bin/python3") is None)
# 批准对象摘要必须等于当前 PRD 的摘要（回 Plan 改了 PRD 就失效）
import hashlib as _hl
prd_digest = "sha256:" + _hl.sha256(
    open(os.path.join(draft, ".wf/tasks/2026-x-draft/prd.md"), "rb").read()).hexdigest()
json.dump({"id": "2026-x", "status": "plan",
           "plan": {"version": prd_digest,
                    "approval": {"object_digest": prd_digest, "decision": {"choice": "approve"}}}},
          open(os.path.join(draft, ".wf/tasks/2026-x-draft/task.json"), "w"))
rec("A5b 已批准 PRD 作为证据", "非空",
    bool(boot.project_key_approved(draft, "/usr/bin/python3")),
    bool(boot.project_key_approved(draft, "/usr/bin/python3")))

open(os.path.join(draft, ".wf/tasks/2026-x-draft/prd.md"), "a").write("\n# 回 Plan 改了口径\n")
rec("A5b2 批准后改 PRD → 证据失效", "None",
    boot.project_key_approved(draft, "/usr/bin/python3"),
    boot.project_key_approved(draft, "/usr/bin/python3") is None)

# ---- 其他 agent 4：相对解释器身份按项目根解析 ----
project = tempfile.mkdtemp()
os.makedirs(os.path.join(project, "venv/bin"), exist_ok=True)
open(os.path.join(project, "venv/bin/python"), "w").write("#!/bin/sh\n")
identity = boot.path_identity("venv/bin/python", project)
rec("A4 相对候选按项目根解析", "项目内相对路径",
    identity, identity == os.path.join("venv", "bin", "python"))

# ---- 其他 agent 5b：损坏全局配置不否定有效项目配置 ----
os.makedirs(os.path.join(project, ".wf"), exist_ok=True)
json.dump({"python_executable": "venv/bin/python"},
          open(os.path.join(project, ".wf/project-config.json"), "w"))
scope, value, error = boot.resolve_candidate(project)
rec("A5c 有效项目配置优先于损坏全局配置", "project", f"{scope}/{error}",
    scope == "project" and error is None)
json.dump({"python_executable": 123}, open(os.path.join(project, ".wf/project-config.json"), "w"))
scope2, value2, error2 = boot.resolve_candidate(project)
rec("A5d 非字符串项目值给结构化出口", "WF_EXECUTOR_UNCONFIRMED",
    (error2 or (None, None))[1], (error2 or (None, None))[1] == "WF_EXECUTOR_UNCONFIRMED")

# ---- 其他 agent 7：wf-start 说明与运行时一致（activation/instance 重放） ----
skill = open("/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/skills/wf-start/SKILL.md",
             encoding="utf-8").read()
rec("A7 wf-start 写明 activation 与 instance_id 重放", "含两者",
    "activation" in skill and "instance_id" in skill,
    "activation" in skill and "instance_id" in skill)

json.dump(results, open("/tmp/r81_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
