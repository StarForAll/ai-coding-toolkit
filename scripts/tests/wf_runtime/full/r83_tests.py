#!/usr/bin/env python3
"""第四十八轮 R83：第五轮独立复审（A1/A2/A3/A5、B1/B2/B3）+ 其他 agent（1/2/3）的定点用例。"""
import contextlib, hashlib, io, json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wfdrive
sys.path.insert(0, wfdrive.LIB)
# 候选模式断言已安装发行器的行为；dev 模式保留作者 payload（作者侧覆盖）。
if wfdrive.deploy_mode() == "candidate":
    sys.path.insert(0, wfdrive.release_root())
else:
    sys.path.insert(0, wfdrive.REPO + "/docs/workflows/wf/payload")
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
_absent_before = os.path.exists(os.path.join(root, target_rel))
wf_spec._apply_change(root, change_delete, {"id": "t"}, [], resume=True)
# 幂等必须核后置状态：文件仍不存在（不是"没抛异常"就算过，第二十三轮复审 N23-3）
rec("A5d 已删除再次续做保持删除态", "文件仍不存在",
    f"before={_absent_before} after={os.path.exists(os.path.join(root, target_rel))}",
    not _absent_before and not os.path.exists(os.path.join(root, target_rel)))

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

# ---- B2（2026-11-05）：安装期分支来源核对（当前分支缺失、其他分支存在） ----
branch_repo = tempfile.mkdtemp(prefix="r83-branch-")
subprocess.run(["git", "init", "-q"], cwd=branch_repo, check=False)
subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=branch_repo, check=False)
subprocess.run(["git", "config", "user.name", "t"], cwd=branch_repo, check=False)
open(os.path.join(branch_repo, "README.md"), "w").write("base\n")
subprocess.run(["git", "add", "README.md"], cwd=branch_repo, check=False)
subprocess.run(["git", "commit", "-qm", "base"], cwd=branch_repo, check=False)
default_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=branch_repo,
                                capture_output=True, text=True).stdout.strip()
subprocess.run(["git", "checkout", "-qb", "side"], cwd=branch_repo, check=False)
os.makedirs(os.path.join(branch_repo, ".agents/skills/wf-start"), exist_ok=True)
open(os.path.join(branch_repo, ".agents/skills/wf-start/SKILL.md"), "w").write("side\n")
subprocess.run(["git", "add", "."], cwd=branch_repo, check=False)
subprocess.run(["git", "commit", "-qm", "side"], cwd=branch_repo, check=False)
subprocess.run(["git", "checkout", "-q", default_branch], cwd=branch_repo, check=False)
current_branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=branch_repo,
                                capture_output=True, text=True).stdout.strip()
rec("B2 前置：回到默认分支且该文件不在工作树", f"HEAD={default_branch} 且文件缺失",
    f"HEAD={current_branch} exists={os.path.exists(os.path.join(branch_repo, '.agents/skills/wf-start/SKILL.md'))}",
    current_branch == default_branch
    and not os.path.exists(os.path.join(branch_repo, ".agents/skills/wf-start/SKILL.md")))

findings = wf_install.branch_source_findings(branch_repo, [".agents/skills/wf-start/SKILL.md"])
rec("B2 其他分支存在而同分支缺失 → 报分支来源",
    "发现 1 条并给出分支名",
    json.dumps(findings, ensure_ascii=False),
    len(findings) == 1 and findings[0].get("branch") == "side")

rec("B2 工作树已存在 → 不算发现", "空列表",
    wf_install.branch_source_findings(branch_repo, ["README.md"]),
    wf_install.branch_source_findings(branch_repo, ["README.md"]) == [])
rec("B2 任何分支都没有 → 不算发现", "空列表",
    wf_install.branch_source_findings(branch_repo, [".agents/skills/absent/SKILL.md"]),
    wf_install.branch_source_findings(branch_repo, [".agents/skills/absent/SKILL.md"]) == [])
shutil.rmtree(branch_repo, ignore_errors=True)

# ---- A1/A2（2026-11-05 第二轮复审）：install.py::add_platforms 的行为 ----

def _run_add_platforms(args, writes, roots):
    """调用 add_platforms 并返回 (rc, 最后一行 JSON 载荷或 None)。"""
    import install as _install
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = _install.add_platforms(args, "c0", _MANIFEST, writes, roots)
    payload = None
    for line in reversed(buffer.getvalue().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                payload = json.loads(line)
            except ValueError:
                payload = None
            break
    return rc, payload


import argparse as _argparse


_RULES_DIGEST = "sha256:" + "a" * 64
# add_platforms 在锁内按 manifest 重算完整计划（不信任调用方传入的 writes），
# 因此合成 manifest 必须像真实发行清单一样登记该技能资产。
_MANIFEST = {"compatibility": {"rules_digest": _RULES_DIGEST},
             "assets": [{"target_class": "skill_root",
                         "target_relative": "wf-start/SKILL.md",
                         "source_path": "skills/wf-start/SKILL.md",
                         "digest": "sha256:y", "executable": False}]}


def _mk_platform_env(name):
    base = tempfile.mkdtemp(prefix=f"r83-{name}-")
    target = os.path.join(base, "proj")
    source = os.path.join(base, "rel")
    # 新平台根故意与已装的 .agents/skills 不同：追加平台只处理新根
    root = os.path.join(target, ".cursor/skills")
    os.makedirs(os.path.join(source, "skills/wf-start"), exist_ok=True)
    os.makedirs(os.path.join(target, ".wf/install"), exist_ok=True)
    open(os.path.join(source, "skills/wf-start/SKILL.md"), "w").write("v1\n")
    installation = {"schema_version": 1, "release_ref": "refs/tags/wf-v0.1.0", "source_commit": "c0",
                    "version": "0.1.0", "rules_digest": _RULES_DIGEST,
                    "platforms": ["dsh"], "roots": [".agents/skills"],
                    "assets": [{"target": ".wf/bin/wf.py", "root_ref": "project", "digest": "sha256:x",
                                "source_path": "bin/wf.py"}],
                    "decisions": [], "installed_at": "2026-11-05T00:00:00.000000Z", "tool": "install.py"}
    json.dump(installation, open(os.path.join(target, ".wf/install/installation.json"), "w"),
              ensure_ascii=False, indent=2)
    writer = {"schema_version": 1, "id": "writer", "revision": 0, "created_at": "2026-11-05T00:00:00.000000Z",
              "updated_at": "2026-11-05T00:00:00.000000Z", "write_mark": None, "action": None,
              "state": "idle", "generation": 2, "holder": None, "handover": None,
              "checkpoint": None, "maintenance_results": []}
    json.dump(writer, open(os.path.join(target, ".wf/writer.json"), "w"), ensure_ascii=False, indent=2)
    args = _argparse.Namespace(target=target, source=source, platform=["cursor"], confirm=True, json=True)
    writes = [(root, {"target_class": "skill_root", "source_path": "skills/wf-start/SKILL.md",
                      "digest": "sha256:y", "executable": False}, "wf-start/SKILL.md")]
    return base, target, root, args, writes


base, target, root, args, writes = _mk_platform_env("add")
wf_install.add_platforms(args, "c0", _MANIFEST, writes, [root])
inst = json.load(open(os.path.join(target, ".wf/install/installation.json"), encoding="utf-8"))
wr = json.load(open(os.path.join(target, ".wf/writer.json"), encoding="utf-8"))
receipt = (wr.get("maintenance_results") or [{}])[-1]
paths = [item.get("path") for item in receipt.get("changes") or []]
rec("A1 追加平台登记新根资产", "assets 增加且含新根技能",
    json.dumps(inst.get("assets"), ensure_ascii=False)[:160],
    len(inst.get("assets") or []) == 2
    and any(a.get("root_ref") == root and a.get("target") == "wf-start/SKILL.md"
            for a in inst.get("assets") or []))
rec("A1 回执路径为项目相对且含安装记录",
    "changes 含 .cursor/skills/wf-start/SKILL.md 与 .wf/install/installation.json",
    paths, ".cursor/skills/wf-start/SKILL.md" in paths
    and ".wf/install/installation.json" in paths)
rec("A1 授予与撤销各递增代次", "generation 2 → 4", wr.get("generation"), wr.get("generation") == 4)
rec("A1 释放后空闲且无 holder", "state=idle holder=None",
    f"{wr.get('state')}/{wr.get('holder')}", wr.get("state") == "idle" and wr.get("holder") is None)
before = json.load(open(os.path.join(target, ".wf/writer.json"), encoding="utf-8"))
idem_rc, idem_payload = _run_add_platforms(args, writes, [root])
after_idem = json.load(open(os.path.join(target, ".wf/writer.json"), encoding="utf-8"))
rec("A1 重复同平台幂等（不取写权、不产生空回执）", "writer 记录逐字段不变且回显 noop",
    f"rc={idem_rc} same={before == after_idem} noop={(idem_payload or {}).get('facts', {}).get('noop')}",
    idem_rc == 0 and before == after_idem
    and (idem_payload or {}).get("facts", {}).get("noop") is True)
shutil.rmtree(base, ignore_errors=True)

base, target, root, args, writes = _mk_platform_env("conflict")
# 两个目标：一个异内容、一个不存在；冲突时必须**整批**不写，连不存在的那份也不能落地
os.makedirs(os.path.join(root, "wf-start"), exist_ok=True)
open(os.path.join(root, "wf-start/SKILL.md"), "w").write("local-edit\n")
writes.append((root, {"target_class": "skill_root", "source_path": "skills/wf-start/SKILL.md",
                      "digest": "sha256:z", "executable": False}, "wf-init/SKILL.md"))
before_writer = json.load(open(os.path.join(target, ".wf/writer.json"), encoding="utf-8"))
inst_path = os.path.join(target, ".wf/install/installation.json")
before_inst = open(inst_path, encoding="utf-8").read()
code, payload_c = _run_add_platforms(args, writes, [root])
after_writer = json.load(open(os.path.join(target, ".wf/writer.json"), encoding="utf-8"))
rec("A1 内容冲突整批不写", "WF_ASSET_DECISION 且 writer/安装记录/两份目标都未变",
    f"rc={code} code={(payload_c or {}).get('code')} batch_written="
    f"{os.path.exists(os.path.join(root, 'wf-init/SKILL.md'))}",
    code == 1 and (payload_c or {}).get("code") == "WF_ASSET_DECISION"
    and before_writer == after_writer and open(inst_path, encoding="utf-8").read() == before_inst
    and open(os.path.join(root, "wf-start/SKILL.md")).read().strip() == "local-edit"
    and not os.path.exists(os.path.join(root, "wf-init/SKILL.md")))
shutil.rmtree(base, ignore_errors=True)

base, target, root, args, writes = _mk_platform_env("badwriter")
wp = os.path.join(target, ".wf/writer.json")
bad = json.load(open(wp, encoding="utf-8"))
bad["schema_version"] = 99
json.dump(bad, open(wp, "w"), ensure_ascii=False, indent=2)
wr_before = open(wp, encoding="utf-8").read()
inst_before = open(os.path.join(target, ".wf/install/installation.json"), encoding="utf-8").read()
code, payload_s = _run_add_platforms(args, writes, [root])
rec("A2 writer schema 非法即拒且零写入", "WF_RECORD_INVALID，记录与目标均未变",
    f"rc={code} code={(payload_s or {}).get('code')} "
    f"file_exists={os.path.exists(os.path.join(root, 'wf-start/SKILL.md'))}",
    code == 1 and (payload_s or {}).get("code") == "WF_RECORD_INVALID"
    and open(wp, encoding="utf-8").read() == wr_before
    and open(os.path.join(target, ".wf/install/installation.json"), encoding="utf-8").read() == inst_before
    and not os.path.exists(os.path.join(root, "wf-start/SKILL.md")))
shutil.rmtree(base, ignore_errors=True)

json.dump(results, open(wfdrive.temp("r83_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
