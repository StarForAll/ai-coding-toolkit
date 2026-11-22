#!/usr/bin/env python3
"""CP3（A6 提交范围 / A7 审查 attempt / A9 执行器 / A16 处理器表 / A17 rules_digest）回归用例。"""
import hashlib, json, os, subprocess, sys
import wfdrive
sys.path.insert(0, wfdrive.LIB)
from wflib import assets as wf_assets, cli as wf_cli, gates as wf_gates

F = wfdrive.FIX
results = []
AT = "2026-11-03T11:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Q1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def dec(subject, choice, digest="sha256:" + "0" * 64, reason="CP3 用例"):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": reason}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def make_task(title, touch, sid, acceptance=None, verifications=None):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:300]); raise SystemExit(1)
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": acceptance or [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": verifications or [{"id": "v1", "invocation": {
                 "kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                 "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(wfdrive.temp(f"cp3_{task_id}_a.json"), [dec("approve plan", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = wfdrive.temp("cp3_notes.json")
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- T1 / A6：提交不捎带预暂存内容 ----------------
clean()
task1, gen1, dir1, d1 = make_task("CP3 A6 提交范围", ["src/c6.txt"], "sess-Q1")
approve(task1, d1, gen1, "sess-Q1")
open(os.path.join(F, "src/c6.txt"), "w").write("c6\n")
wf(["task-start", "--task", task1, "--json"], {"generation": gen1}, "sess-Q1")
check_rc, check_payload, _ = wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"],
                                {"generation": gen1}, "sess-Q1")
rec("A6 准备：Check 通过", "pass", (check_payload or {}).get("code"), check_rc == 0)
if check_rc != 0:
    raise RuntimeError(f"A6 Check precondition failed: {check_payload}")
wf(["task-knowledge", "--task", task1, "--decision", "no-update", "--json"], {"generation": gen1}, "sess-Q1")
open(os.path.join(F, "notes.txt"), "w").write("unrelated\n")
subprocess.run(["git", "add", "notes.txt"], cwd=F, capture_output=True)
wf(["sampling", "pick", "--task", task1, "--freeze", "--json"],
                       {"generation": gen1}, "sess-Q1")   # 归档前置：先冻结并落盘选样
rc, payload, out = wf(["archive", "--task", task1, "--decision",
                       dfile(wfdrive.temp("cp3_a6.json"), [dec(f"finish {task1}", "finish", d1),
                                                  dec(["src/c6.txt"], "commit", d1)]),
                       "--json"], {"generation": gen1}, "sess-Q1")
rec("A6 归档成功（subject 为数组）", "pass", (payload or {}).get("code"), rc == 0)
def show(rev):
    return subprocess.run(["git", "-c", "core.quotePath=false", "show", "--name-only", "--format=", rev],
                          cwd=F, capture_output=True, text=True).stdout.split()


business = show("HEAD~1")
record_commit = show("HEAD")
status = subprocess.run(["git", "status", "--porcelain"], cwd=F, capture_output=True, text=True).stdout
rec("A6 业务提交不含预暂存文件", "notes.txt 不在业务提交中", f"in_business={'notes.txt' in business}",
    "notes.txt" not in business)
rec("A6 归档提交不含预暂存文件", "notes.txt 不在归档提交中", f"in_archive={'notes.txt' in record_commit}",
    "notes.txt" not in record_commit)
rec("A6 预暂存内容保持原状", "notes.txt 仍处于暂存区", status.strip().split()[:1],
    "A  notes.txt" in status or "A notes.txt" in status)
subprocess.run(["git", "reset", "-q", "HEAD", "notes.txt"], cwd=F, capture_output=True)
os.remove(os.path.join(F, "notes.txt"))
wf(["writer", "release", "--json"], {"generation": gen1}, "sess-Q1")

# ---------------- T2 / A6b：glob 不得作为提交路径 ----------------
clean()
task2, gen2, dir2, d2 = make_task("CP3 A6 glob 拒绝", ["src/c6b.txt"], "sess-Q2")
approve(task2, d2, gen2, "sess-Q2")
open(os.path.join(F, "src/c6b.txt"), "w").write("c6b\n")
wf(["task-start", "--task", task2, "--json"], {"generation": gen2}, "sess-Q2")
wf(["task-check", "--task", task2, "--review-notes", NOTES, "--json"], {"generation": gen2}, "sess-Q2")
wf(["task-knowledge", "--task", task2, "--decision", "no-update", "--json"], {"generation": gen2}, "sess-Q2")
wf(["sampling", "pick", "--task", task2, "--freeze", "--json"],
                       {"generation": gen2}, "sess-Q2")   # 归档前置：先冻结并落盘选样（本任务会话）
rc, payload, out = wf(["archive", "--task", task2, "--decision",
                       dfile(wfdrive.temp("cp3_a6b.json"), [dec(f"finish {task2}", "finish", d2),
                                                  dec("src/*.py", "commit", d2)]), "--json"],
                      {"generation": gen2}, "sess-Q2")
rec("A6 未覆盖交付的授权被门禁挡住", "WF_WIP_UNRESOLVED 或 WF_COMMIT_NOT_AUTHORIZED",
    (payload or {}).get("code"),
    (payload or {}).get("code") in ("WF_WIP_UNRESOLVED", "WF_COMMIT_NOT_AUTHORIZED"))
wf(["task-pause", "--task", task2, "--reason", "CP3 收尾", "--json"], {"generation": gen2}, "sess-Q2")
wf(["writer", "release", "--json"], {"generation": gen2}, "sess-Q2")

# ---------------- T3 / A7：同一尝试两轮上限 ----------------
clean()
task3, gen3, dir3, d3 = make_task("CP3 A7 审查 attempt", ["src/c7.txt"], "sess-Q3")
approve(task3, d3, gen3, "sess-Q3")
open(os.path.join(F, "src/c7.txt"), "w").write("c7\n")
wf(["task-start", "--task", task3, "--json"], {"generation": gen3}, "sess-Q3")
wf(["task-check", "--task", task3, "--review-notes", NOTES, "--json"], {"generation": gen3}, "sess-Q3")
launch = {"implementation_clis": ["dsh"],
          "slots": [{"slot": "r1", "reviewer_cli": "claude"}, {"slot": "r2", "reviewer_cli": "codex"}],
          "submitted_scope": {"diff": "git diff", "requirements": ["prd"], "test_results": ["v1"]},
          "readable_scope": {"code": ["src/**"], "spec": [".wf/spec/**"], "prd": os.path.relpath(os.path.join(dir3, "prd.md"), F)},
          "exclusions": [".env"], "export_decision": "human (test)"}
json.dump(launch, open(wfdrive.temp("cp3_launch.json"), "w"), ensure_ascii=False)
# K6 第 3 类：外发以"确认入库"为准（请求里的 export_decision 只是声明）
json.dump([{"choice": "export", "task": task3, "materials": ["diff", "requirement", "test_results"], "paths": ["src/**"], "quote": "人同意把材料外发给审查 CLI",
                "by": "human:test", "at": "2026-11-10T00:00:00.000000Z",
                "source": "user-declared"}],
          open(wfdrive.temp("cp3_export.json"), "w"), ensure_ascii=False)
wf(["authorize", "record", "--task", task3, "--file", wfdrive.temp("cp3_export.json"), "--json"],
   {"generation": gen3}, "sess-Q3")
rc, payload, _ = wf(["review-launch", "--task", task3, "--launch-request", wfdrive.temp("cp3_launch.json"), "--json"],
                    {"generation": gen3}, "sess-Q3")
rec("A7 round 1 发起", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["review-launch", "--task", task3, "--launch-request", wfdrive.temp("cp3_launch.json"), "--json"],
                    {"generation": gen3}, "sess-Q3")
rec("A7 round 2 发起", "pass", (payload or {}).get("code"), rc == 0)
record = json.load(open(os.path.join(dir3, "task.json")))
attempts = record["reviews"]["attempts"]
rec("A7 两轮落在同一 attempt", "attempts=[{number:1,round_ids:[1,2]}]",
    json.dumps(attempts, ensure_ascii=False), len(attempts) == 1 and attempts[0]["round_ids"] == [1, 2])
rc, payload, _ = wf(["review-launch", "--task", task3, "--launch-request", wfdrive.temp("cp3_launch.json"), "--json"],
                    {"generation": gen3}, "sess-Q3")
# round_ids 现在只作观察与历史重建，不再作为拒绝依据（见 review.py 对应注释）：
# 轮次上限不是机械门禁，是否再开一轮由人/判定决定。故第三轮应放行并继续记在同一 attempt。
rec("A7 第三轮放行且继续记在同一 attempt", "WF_OK 且 round_ids 含 3", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_OK"
    and 3 in ((json.load(open(os.path.join(dir3, "task.json")))["reviews"]["attempts"][0].get("round_ids")) or []))
wf(["task-pause", "--task", task3, "--reason", "CP3 收尾", "--json"], {"generation": gen3}, "sess-Q3")
wf(["writer", "release", "--json"], {"generation": gen3}, "sess-Q3")

# ---------------- T4 / A9：执行器解析 ----------------
WF = os.path.join(F, ".wf/bin/wf.py")


def status():
    proc = subprocess.run([wfdrive.PYTHON, WF, "status", "--json"], capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        payload = {}
    return proc.returncode, payload


home_config = os.path.expanduser("~/.wf/config.json")
project_config = os.path.join(F, ".wf/project-config.json")
backup = open(project_config, encoding="utf-8").read()

open(home_config, "w").write(json.dumps({"schema_version": 1, "python_executable": "python3"}))
rc, payload = status()
rec("A9 全局键须为绝对路径", "WF_EXECUTOR_UNCONFIRMED",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_EXECUTOR_UNCONFIRMED" and rc == 1)
os.remove(home_config)

config = json.loads(backup)
config["python_executable"] = "../outside-python3"
json.dump(config, open(project_config, "w"), ensure_ascii=False, indent=2)
rc, payload = status()
rec("A9 项目键不得越出项目根", "WF_PATH_INVALID", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_PATH_INVALID")

open(project_config, "w").write("{ broken json")
rc, payload = status()
rec("A9 项目配置损坏不静默回退", "WF_EXECUTOR_UNCONFIRMED", f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_EXECUTOR_UNCONFIRMED" and rc == 1)
open(project_config, "w").write(backup)

# ---------------- T5 / A16：固定分派表 ----------------
# 交付轮次（2026-11-05 人裁 B）：清单必须声明 delivery_round，安装自检据此判可达
_specs = wf_gates.required_step_specs()
manifest = {"delivery_round": wf_gates.CURRENT_DELIVERY_ROUND,
            "required_steps": [{"id": step, "delivery_round": _specs[step]["delivery_round"]}
                               for step in sorted(wf_gates.supported_keys())]}
problems = wf_gates.support_report(manifest, wf_cli.COMMANDS,
                                   [name for name in wf_gates.BOOTSTRAP_ENTRIES
                                    if os.path.isfile(os.path.join(F, ".wf/bin", f"{name}.py"))])
rec("A16 分派表与命令面一致", "无问题", f"{len(problems)} problems", not problems)
# 桩不再是固定的某个子命令（2026-11-12：`run` 已部分交付，命令本身不再是桩，
# 但它的 `advance/pause/terminate` 子动作仍报能力不可用）。这里**按当前命令面动态找**
# 一个仍是桩的承接命令，再挑一个声明为它的 control 步骤——断言核的是检查器本身，
# 不应绑死在某一个命令名上（绑死的话每次解封一处就要改这条用例）。
# 2026-11-22 三轮 W4：upgrade 已从能力桩改为引导层转交报错——真实命令面不再有桩。
# 这条断言核的是**检查器本身**（support_report 必须抓到"声明已交付但承接命令是桩"），
# 改用合成桩探针：给 upgrade 处理器临时装回 wf_delivery_round 标记，验证检测逻辑后还原。
_probe_commands = dict(wf_cli.COMMANDS)
_original_upgrade = _probe_commands.get("upgrade")
_probe_step = "control.asset.apply"


def _probe_stub(ctx, args):
    raise wf_cli.CliError("WF_CAPABILITY_UNAVAILABLE", {"probe": True})


_probe_stub.wf_delivery_round = 3
_probe_commands["upgrade"] = _probe_stub
overclaimed = {"delivery_round": wf_gates.CURRENT_DELIVERY_ROUND,
               "required_steps": [dict(step, delivery_round=(wf_gates.CURRENT_DELIVERY_ROUND
                                                             if step["id"] == _probe_step
                                                             else step["delivery_round"]))
                                  for step in manifest["required_steps"]]}
claimed_problems = wf_gates.support_report(overclaimed, _probe_commands)
rec("A16 已交付步骤不得是能力桩（合成桩探针）", f"报 capability stub（{_probe_step}）",
    claimed_problems[:1],
    any(p.get("required_step") == _probe_step and "capability stub" in p.get("reason", "")
        for p in claimed_problems))
# 还原真实命令面（upgrade 是转交报错，不是桩）
if _original_upgrade is not None:
    _probe_commands["upgrade"] = _original_upgrade
missing_round = {"required_steps": [{"id": "task.archived"}]}
rec("A16 缺交付轮次被拒", "报 delivery_round missing",
    wf_gates.support_report(missing_round, wf_cli.COMMANDS)[:1],
    any("delivery_round" in p.get("reason", "") for p in wf_gates.support_report(missing_round, wf_cli.COMMANDS)))
bad = {"delivery_round": wf_gates.CURRENT_DELIVERY_ROUND,
       "required_steps": manifest["required_steps"] + [{"id": "task.unknown-step", "delivery_round": 1}]}
rec("A16 未登记步骤被拒", "报 no fixed handler",
    wf_gates.support_report(bad, wf_cli.COMMANDS),
    any(p.get("required_step") == "task.unknown-step" for p in wf_gates.support_report(bad, wf_cli.COMMANDS)))
fewer = {"delivery_round": wf_gates.CURRENT_DELIVERY_ROUND,
         "required_steps": [item for item in manifest["required_steps"] if item["id"] != "control.task.archive"]}
rec("A16 未声明处理器被拒", "报 handler not declared",
    len(wf_gates.support_report(fewer, wf_cli.COMMANDS)),
    any(p.get("required_step") == "control.task.archive"
        for p in wf_gates.support_report(fewer, wf_cli.COMMANDS)))

# ---------------- T6 / A17：rules_digest 两实现一致（含非 ASCII） ----------------
sample = {"schema_version": 1,
          "compatibility": {"python_min": {"major": 3, "minor": 11}, "rules_digest": "x"},
          "assets": [{"source_path": "技能/b.py", "target_class": "project_wf", "target_relative": ".wf/b"},
                     {"source_path": "a.py", "target_class": "project_wf", "target_relative": ".wf/a"}],
          "required_steps": [{"id": "task.b"}, {"id": "task.a"}],
          "template_markers": {"formats": [], "uses": []},
          "gitignore_managed": {"begin_marker": "# wf-managed-v1", "end_marker": "# wf-managed-end",
                                "lines": ["/.wf-lock"]}}
import importlib.util
spec = importlib.util.spec_from_file_location("wf_install", wfdrive.install_source_path())
install_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install_mod)
rec("A17 两处 rules_digest 一致（含非 ASCII 路径）", "相同摘要",
    f"same={install_mod.compute_rules_digest(sample) == wf_assets.compute_rules_digest(sample)}",
    install_mod.compute_rules_digest(sample) == wf_assets.compute_rules_digest(sample))

json.dump(results, open(wfdrive.temp("cp3_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
