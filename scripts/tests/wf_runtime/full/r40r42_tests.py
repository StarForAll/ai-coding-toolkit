#!/usr/bin/env python3
"""第九轮 R40–R42 用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import cli as wf_cli

F = wfdrive.FIX
results = []
AT = "2026-11-04T05:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Q1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R40-R42 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def make_task(title, touch, sid):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": touch,
             "acceptance": [{"id": "a1", "statement": "文件存在", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    return task_id, gen, directory, "sha256:" + hashlib.sha256(prd.encode()).hexdigest()


def approve(task_id, digest, gen, sid):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r40_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


# ---------------- R40：未登记的脏改动阻断其他对象 ----------------
clean()
os.makedirs(os.path.join(F, "a40"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R40 未登记 WIP", ["a40/**"], "sess-Q1")
approve(task1, d1, gen1, "sess-Q1")
open(os.path.join(F, "a40/x.txt"), "w").write("x\n")
rc_s, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Q1")
rec("R40 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)
wf(["task-pause", "--task", task1, "--reason", "未登记 WIP", "--json"], {"generation": write_gen()}, "sess-Q1")
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Q1")
rec("R40 释放写权（改动仍归属该任务）", "WF_OK", (payload or {}).get("code"), rc == 0)
blockers = wf_cli.wip_blockers(F)
rec("R40 未登记改动被识别", "列出 a40/x.txt",
    json.dumps(blockers, ensure_ascii=False)[:140],
    bool(blockers) and "a40/x.txt" in (blockers[0].get("paths") or []))
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R40 其他对象",
                     "--template", f"{F}/.wf/templates/task", "--json"], {"generation": write_gen()}, "sess-Q2")
rec("R40 其他对象 task-new 被拒", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")

# ---------------- R41：同一对象接续允许，且交回保留 WIP ----------------
rc, payload, _ = wf(["bind", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Q2")
facts = (payload or {}).get("facts", {})
rec("R41 同对象接续被允许", "WF_OK", (payload or {}).get("code"), rc == 0)
rec("R41 接续响应带出保留 WIP", "inherited_wip 含 a40/x.txt",
    json.dumps(facts.get("inherited_wip"), ensure_ascii=False)[:160],
    bool(facts.get("inherited_wip")) and "a40/x.txt" in (facts["inherited_wip"].get("paths") or []))
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-Q2")

# ---------------- R42：恢复时核对保存的指纹 ----------------
clean()
rec_path = os.path.join(dir1, "task.json")
record = json.load(open(rec_path))
record["handoff"] = {"wip": {"paths": [{"path": "a40/x.txt", "exists": True, "kind": "file",
                                        "executable": False,
                                        "digest": "sha256:" + hashlib.sha256(b"x\n").hexdigest()}],
                              "pending": [], "resolved": None}}
json.dump(record, open(rec_path, "w"), ensure_ascii=False)
clean()
rc, payload, _ = wf(["bind", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Q3")
rec("R42 准备：接续取得写权", "WF_OK", (payload or {}).get("code"), rc == 0)
open(os.path.join(F, "a40/x.txt"), "w").write("replaced\n")
rc, payload, _ = wf(["task-resume", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Q3")
facts = (payload or {}).get("facts", {})
rec("R42 内容变化时恢复被拒", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
rec("R42 报告变化路径与指纹", "changed 含 a40/x.txt",
    json.dumps(facts.get("changed"), ensure_ascii=False)[:160],
    bool(facts.get("changed")) and facts["changed"][0].get("path") == "a40/x.txt")
open(os.path.join(F, "a40/x.txt"), "w").write("x\n")
rc, payload, _ = wf(["task-resume", "--task", task1, "--json"], {"generation": write_gen()}, "sess-Q3")
rec("R42 指纹一致时恢复通过", "WF_OK", (payload or {}).get("code"), rc == 0)

json.dump(results, open("/tmp/r40r42_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
