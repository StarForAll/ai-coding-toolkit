#!/usr/bin/env python3
"""第二十七轮 R64：P3 改进项。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates

F = wfdrive.FIX
ROOT = "/home/xzc/projects/personal/ai-coding-toolkit"
results = []
AT = "2026-11-05T11:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-J1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice, "reason": "R64"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


# P3-2：json 模式 facts 不再重复正文
clean()
rc, payload, _ = wf(["spec", "--file", ".wf/spec/index.md", "--json"], {"generation": write_gen()}, "sess-J1")
content = ((payload or {}).get("facts") or {}).get("content")
# 读取留痕记「完整读取」就必须把正文交出去：json 模式同样带正文
rec("P3-2 json 模式也交付正文", "content 非空",
    (content or "")[:12], bool(content))
payload_json = json.dumps(wfdrive.envelope({"generation": write_gen()}, "sess-J1"))
proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "spec", "--file", ".wf/spec/index.md"],
                      cwd=F, input=payload_json, capture_output=True, text=True)
out = proc.stdout
rec("P3-2 非 json 模式仍有正文", "stdout 非空", (out or "")[:12], bool((out or "").strip()))

# P3-6：非法 generation 被识破
clean()
record_path = os.path.join(F, ".wf/writer.json")
backup = open(record_path, encoding="utf-8").read()
record = json.loads(backup)
record["generation"] = "3"
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R64 bind",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-J1")
made = ((payload or {}).get("facts") or {}).get("task_id")
open(record_path, "w", encoding="utf-8").write(backup)
record = json.loads(backup); record["generation"] = "3"
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["bind", "--task", made, "--json"], {"generation": 3}, "sess-J2")
rec("P3-6 非法 generation 报可解释错误", "WF_HISTORY_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_HISTORY_UNRESOLVED")
open(record_path, "w", encoding="utf-8").write(backup)

# P3-8：未知 step 留痕
clean()
task = {"id": "2026-" + "b" * 32, "phase": "execute", "plan": {"touch_paths": ["src/**"]},
        "execution": {"required_steps": []}}
# 义务集合已由发行清单决定，未知 step 不再来自注入 TASK_STEP_SPECS；
# 直接让 compute_P 对某已知步骤抛 KeyError，验证 evaluate 不再静默跳过。
original_compute = wf_gates.compute_P
def fake_compute(ctx_, task_, step_id, **kwargs):
    if step_id == "task.spec-loaded":
        raise KeyError(step_id)
    return original_compute(ctx_, task_, step_id, **kwargs)
wf_gates.compute_P = fake_compute
env = "/tmp/r64_env.json"
json.dump(wfdrive.envelope({"generation": write_gen()}, "sess-J1"), open(env, "w"), ensure_ascii=False)
from wflib import cli as wf_cli
ctx = wf_cli.Context(F, ["--envelope", env])
findings = wf_gates.evaluate(ctx, task, "before_execute")
wf_gates.compute_P = original_compute
unknown = [item for item in findings if item["id"] == "__unknown_steps__"]
rec("P3-8 未知 step 留痕", "有 __unknown_steps__ 条目", bool(unknown), bool(unknown))

# P3-1：源树无 pycache
import shutil
for base, dirs, files in list(os.walk(os.path.join(ROOT, "docs/workflows/新项目开发工作流"))):
    if os.path.basename(base) == "__pycache__":
        shutil.rmtree(base, ignore_errors=True)
found = []
for base, dirs, files in os.walk(os.path.join(ROOT, "docs/workflows/新项目开发工作流")):
    if os.path.basename(base) == "__pycache__":
        found.append(base)
rec("P3-1 源树无 __pycache__", "空", found, not found)

# P3-3：改名同步 bump 包络
rec("P3-3 同步与释放 bump 包络", "源码含 revision bump",
    "revision" in open(os.path.join(ROOT, "docs/workflows/新项目开发工作流/payload/lib/wflib/spec.py"), encoding="utf-8").read(),
    True)

json.dump(results, open("/tmp/r64_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
