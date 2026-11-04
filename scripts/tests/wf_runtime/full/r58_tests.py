#!/usr/bin/env python3
"""第二十一轮 R58：结构级/字段级分类 + 阈值消费者阻断。"""
import datetime, hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import config as wf_config

F = wfdrive.FIX
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-04T18:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-C1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R58"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2); return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


# ---------- 分类单元 ----------
field_problem = [{"level": "field", "key": "tdd_default", "message": "tdd_default must be a boolean"}]
struct_problem = [{"level": "structure", "key": "schema_version", "message": "unsupported schema_version: 999"}]
rec("R58 无关字段错误不扩散到缺失键", 90,
    wf_config.value_of({}, field_problem, "spec_verify_days")[0],
    wf_config.value_of({}, field_problem, "spec_verify_days") == (90, None))
rec("R58 结构级错误阻断缺失键", None,
    wf_config.value_of({}, struct_problem, "spec_verify_days")[0],
    wf_config.value_of({}, struct_problem, "spec_verify_days")[0] is None)
rec("R58 结构级错误阻断已给的合法键", None,
    wf_config.value_of({"spec_verify_days": 5}, struct_problem, "spec_verify_days")[0],
    wf_config.value_of({"spec_verify_days": 5}, struct_problem, "spec_verify_days")[0] is None)
rec("R58 无关字段错误不影响自身合法键", 5,
    wf_config.value_of({"spec_verify_days": 5}, field_problem, "spec_verify_days")[0],
    wf_config.value_of({"spec_verify_days": 5}, field_problem, "spec_verify_days") == (5, None))

# ---------- 入口：阈值非法必须阻断调试分支 ----------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
config_path = os.path.join(F, ".wf/project-config.json")
backup = open(config_path, encoding="utf-8").read()

rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R58 阈值", "--template",
                     f"{F}/.wf/templates/task", "--json"], None, "sess-C1")
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "总是失败", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c",
                                                                      "import sys; sys.exit(0 if open('pkg/a.py').read().strip()=='ok' else 1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R58 阈值\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
json.dump([dec("approve", "approve", digest)], open("/tmp/r58_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r58_a.json", "--json"],
   {"generation": gen, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-C1")
open(os.path.join(F, "pkg/a.py"), "w").write("bad\n")
rc_s, start1, _ = wf(["task-start", "--task", task_id, "--json"], {"generation": write_gen()}, "sess-C1")
rec("R58 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)

NOTES = "/tmp/r58_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"}, "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def run_final_gate():
    """直接取归档门禁（debug 待决分支在 final_gate 内）。"""
    import importlib
    sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
    from wflib import gates as gates_mod
    from wflib import cli as wf_cli
    env_path = "/tmp/r58_env.json"
    json.dump(wfdrive.envelope({"generation": write_gen()}, "sess-C1"), open(env_path, "w"), ensure_ascii=False)
    ctx = wf_cli.Context(F, ["--envelope", env_path])
    import glob
    task = json.load(open(glob.glob(os.path.join(F, ".wf/tasks", "*R58*", "task.json"))[0], encoding="utf-8"))
    ok, code, facts = gates_mod.final_gate(ctx, task)
    return ok, code, facts


cfg = json.loads(backup); cfg["debug_repeat_threshold"] = 1
json.dump(cfg, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
clean()
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-C1")
rec("R58 准备：一次失败留下", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-C1")
rec("R58 准备：第二次失败（历史留痕）", "WF_CHECK_FAILED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_CHECK_FAILED")

open(os.path.join(F, "pkg/a.py"), "w").write("ok\n")
subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
subprocess.run(["git", "commit", "-qm", "fix"], cwd=F, capture_output=True)
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": write_gen()}, "sess-C1")
rec("R58 准备：第三次通过", "WF_OK", (payload or {}).get("code"), rc == 0)
wf(["task-knowledge", "--task", task_id, "--decision", "no-update", "--json"], {"generation": write_gen()}, "sess-C1")
ok, code, facts = run_final_gate()
rec("R58 阈值=1 时要求裁定", "WF_SEMANTIC_DECISION 且 pending 非空",
    f"ok={ok} code={code} facts={json.dumps(facts, ensure_ascii=False)[:200]}",
    ok is False and code == "WF_SEMANTIC_DECISION" and facts.get("unruled_debug_multiples"))

cfg["debug_repeat_threshold"] = "bad"
json.dump(cfg, open(config_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
clean()
caught_code, caught_facts = None, {}
try:
    run_final_gate()
except Exception as exc:
    caught_code, caught_facts = getattr(exc, "code", None), getattr(exc, "facts", {}) or {}
rec("R58 阈值非法时同样阻断（不再按 3 放行）", "WF_CAPABILITY_UNAVAILABLE 且指出该键",
    f"code={caught_code} facts={json.dumps(caught_facts, ensure_ascii=False)[:90]}",
    caught_code == "WF_CAPABILITY_UNAVAILABLE"
    and "debug_repeat_threshold" in json.dumps(caught_facts, ensure_ascii=False))

open(config_path, "w", encoding="utf-8").write(backup)
json.dump(results, open("/tmp/r58_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
