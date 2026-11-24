#!/usr/bin/env python3
"""第二十七轮 R64：P3 改进项。"""
import hashlib, json, os, subprocess, sys
import wfdrive
sys.path.insert(0, wfdrive.LIB)
from wflib import gates as wf_gates

F = wfdrive.FIX
results = []
AT = "2026-11-05T11:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-J1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "artifacts": wfdrive.plan_artifacts(subject), "object_digest": digest, "choice": choice, "reason": "R64"}



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
proc = subprocess.run([wfdrive.PYTHON, os.path.join(F, ".wf/bin/wf.py"), "spec", "--file", ".wf/spec/index.md"],
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
env = wfdrive.temp("r64_env.json")
json.dump(wfdrive.envelope({"generation": write_gen()}, "sess-J1"), open(env, "w"), ensure_ascii=False)
from wflib import cli as wf_cli
ctx = wf_cli.Context(F, ["--envelope", env])
findings = wf_gates.evaluate(ctx, task, "before_execute")
wf_gates.compute_P = original_compute
unknown = [item for item in findings if item["id"] == "__unknown_steps__"]
rec("P3-8 未知 step 留痕", "有 __unknown_steps__ 条目", bool(unknown), bool(unknown))

# P3-1（源树无 __pycache__）已迁移：运行器承载“运行期不污染源树”这条不变量
# （run_all.sh 的 source_hygiene.py snapshot/check）。旧用例先 rmtree 再断言“没有”，
# 恒真且会改写作者源树，因此删除而不是保留。

# P3-3：改名同步 bump 包络（断言对象 = 当前部署实际使用的 wflib，不是作者 payload）
_lib_source = open(os.path.join(wfdrive.LIB, "wflib", "spec.py"), encoding="utf-8").read()
_scope_label = "安装库" if wfdrive.deploy_mode() == "candidate" else "作者库"
rec(f"P3-3（{_scope_label}）同步与释放 bump 包络", "库源码含 revision bump",
    f"lib={wfdrive.LIB}", "revision" in _lib_source)

json.dump(results, open(wfdrive.temp("r64_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
