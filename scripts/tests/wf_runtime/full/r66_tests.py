#!/usr/bin/env python3
"""第二十九轮 R66：公共写入口统一核验（实例标识、写者结构、终态、清单义务、重复记录）。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, tasks as wf_tasks, writer as wf_writer, cli as wf_cli

F = wfdrive.FIX
results = []
AT = "2026-11-06T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-L1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice, "reason": "R66"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def make_task(title, sid):
    rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", title,
                         "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    json.dump([dec("approve", "approve", digest)], open(f"/tmp/r66_{facts['task_id']}.json", "w"))
    wf(["task-approve", "--task", facts["task_id"], "--decision", f"/tmp/r66_{facts['task_id']}.json", "--json"],
       {"generation": facts.get("generation"), "complexity": "light",
        "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)
    return facts["task_id"], facts.get("generation")


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()

# ---- 1. 日常入口核验实例标识 ----
task1, gen1 = make_task("R66 实例标识", "sess-L1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
wf(["task-start", "--task", task1, "--json"], {"generation": gen1}, "sess-L1")
rc, payload, _ = wfdrive.run(["task-pause", "--task", task1, "--reason", "x", "--json"],
                             {"generation": gen()}, "sess-L1",
                             instance_id="ffffffffffffffffffffffffffffffff", show=False)
rec("1 实例标识被篡改 → 拒绝", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
rc, payload, _ = wf(["task-pause", "--task", task1, "--reason", "x", "--json"],
                    {"generation": gen()}, "sess-L1")
rec("1b 正常携带实例标识 → 通过", "WF_OK", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wfdrive.run(["task-pause", "--task", task1, "--reason", "x", "--json"],
                             {"generation": gen()}, "sess-L1", instance_id="", show=False)
rec("1c 实例标识缺失 → 需人裁决", "WF_IDENTITY_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
clean()

# ---- 2. 写者结构与代次一致性 ----
record_path = os.path.join(F, ".wf/writer.json")
backup = open(record_path, encoding="utf-8").read()
writer = json.loads(backup)
writer["schema_version"] = 999
json.dump(writer, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["status", "--json"], {}, "sess-L1")
rec("2 未知 writer schema 被拒", "WF_RECORD_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_RECORD_INVALID")
writer = json.loads(backup)
writer["holder"]["generation"] = int(writer.get("generation") or 0) + 1
json.dump(writer, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["status", "--json"], {}, "sess-L1")
rec("2b 顶层与 holder 代次矛盾被拒", "WF_RECORD_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_RECORD_INVALID")
open(record_path, "w", encoding="utf-8").write(backup)

# ---- 3. 终态对象不再接受暂停 ----
clean()
rc, payload, _ = wf(["task-pause", "--task", task1, "--reason", "x", "--json"], {"generation": gen()}, "sess-L1")
rec("3 正常任务暂停通过（准备）", "WF_OK 或已暂停", (payload or {}).get("code"),
    (payload or {}).get("code") in ("WF_OK", "WF_SEMANTIC_DECISION"))
import glob
tpath = glob.glob(os.path.join(F, ".wf/tasks", f"{task1}-*", "task.json"))[0]
task_rec = json.load(open(tpath, encoding="utf-8"))
task_rec["status"] = "archived"
task_rec["terminal"] = "normal"
json.dump(task_rec, open(tpath, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["task-pause", "--task", task1, "--reason", "x", "--json"], {"generation": gen()}, "sess-L1")
rec("3b 已归档任务拒绝暂停", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
rc, payload, _ = wf(["task-resume", "--task", task1, "--json"], {"generation": gen()}, "sess-L1")
rec("3c 已归档任务拒绝恢复", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
clean()

# ---- 4. 义务集合来自已校验清单 ----
from wflib import assets as wf_assets
manifest_path = os.path.join(F, ".wf/install/release-manifest.json")
manifest_backup = open(manifest_path, encoding="utf-8").read()
manifest = json.loads(manifest_backup)
manifest["required_steps"] = [s for s in manifest.get("required_steps") or [] if s.get("id") != "task.spec-loaded"]
json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
env_path = "/tmp/r66_env.json"
json.dump(wfdrive.envelope({"generation": gen()}, "sess-L1"), open(env_path, "w"), ensure_ascii=False)
ctx = wf_cli.Context(F, ["--envelope", env_path])
blocked = None
try:
    wf_gates.declared_step_specs(ctx)
except Exception as exc:
    blocked = getattr(exc, "code", type(exc).__name__)
rec("4 清单缺声明 → 拒绝计算义务", "WF_ASSET_DECISION", blocked, blocked == "WF_ASSET_DECISION")
open(manifest_path, "w", encoding="utf-8").write(manifest_backup)
declared = [item["id"] for item in wf_gates.declared_step_specs(wf_cli.Context(F, ["--envelope", env_path]))]
rec("4b 正常时义务由清单给出", "含 task.plan-approved", "task.plan-approved" in declared,
    "task.plan-approved" in declared)

# ---- 5. 重复任务记录不得静默取一 ----
clean()
src_dir = os.path.dirname(tpath)
dup_dir = src_dir + "-copy"
shutil.copytree(src_dir, dup_dir)
caught = None
try:
    wf_tasks.task_dir(F, task1)
except Exception as exc:
    caught = type(exc).__name__

rec("5 重复记录被拒并给诊断", "RecordInvalid", caught, caught == "RecordInvalid")
shutil.rmtree(dup_dir, ignore_errors=True)
rec("5b 去重后可正常定位", "返回路径", bool(wf_tasks.task_dir(F, task1)), bool(wf_tasks.task_dir(F, task1)))

json.dump(results, open("/tmp/r66_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
