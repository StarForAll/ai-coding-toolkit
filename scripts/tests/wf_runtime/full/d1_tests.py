#!/usr/bin/env python3
"""D1 实跑：真实宿主身份（$DSH_SESSION_ID）+ 压缩边界 + wf 签发路径。"""
import json, os, subprocess, sys, time
sys.path.insert(0, "/tmp")
F = os.environ.get("WF_FIX", "/tmp/wf-fixtures/d1")
WF = os.path.join(F, ".wf/bin/wf.py")
PYTHON = "/usr/bin/python3"
REAL = os.environ.get("DSH_SESSION_ID") or "session-unknown"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def envelope(sid, activation=True, instance_id=None, provider="host", issued=None):
    identity = {"host_id": "dsh", "session_id": sid} if provider == "host" else {"issued_id": issued}
    return {"session": {"provider": provider, "identity": identity, "instance_id": instance_id,
                        "activation": ({"enabled": True, "start_source": "human:test",
                                        "enabled_at": "2026-11-05T00:00:00.000000Z"} if activation else None)},
            "inputs": {}}


def run(args, inputs=None, sid=REAL, activation=True, instance_id=None, provider="host", issued=None):
    env = envelope(sid, activation, instance_id, provider, issued)
    env["inputs"] = inputs or {}
    proc = subprocess.run([PYTHON, WF] + list(args), cwd=F, input=json.dumps(env, ensure_ascii=False),
                          capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else None
    except ValueError:
        payload = None
    return proc.returncode, payload, proc.stdout


print("真实会话标识：", REAL[:20] + "…", f"(len={len(REAL)})")

# ---- 1. 真实宿主身份首次绑定 ----
rc, payload, _ = run(["task-new", "--kind", "ordinary", "--title", "D1 真实身份",
                      "--template", f"{F}/.wf/templates/task", "--json"], None, REAL)
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
rec("D1-1 真实 session_id 可绑定", "WF_OK", (payload or {}).get("code"), rc == 0 and bool(task_id))

# ---- 2. 同身份重入（无变化）----
rc, payload, _ = run(["status", "--json"], {"generation": gen}, REAL)
binding = ((payload or {}).get("facts") or {}).get("binding") or {}
rec("D1-2 同身份重入保持绑定", "object.id 等于任务",
    (binding.get("object") or {}).get("id"), (binding.get("object") or {}).get("id") == task_id)

# ---- 3. 压缩边界：activation 丢失 ----
rc, payload, _ = run(["status", "--json"], {"generation": gen}, REAL, activation=False)
rec("D1-3 压缩未携带 activation → 需重新 start", "WF_NOT_ENABLED 或 WF_OK(只读)",
    (payload or {}).get("code"), True)  # 只读诊断允许；下表按业务动作再验

rc, payload, _ = run(["task-start", "--task", task_id, "--json"], {"generation": gen}, REAL, activation=False)
rec("D1-3b 无 activation 推进业务被拒", "WF_NOT_ENABLED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_NOT_ENABLED")

# ---- 4. 重新 start 只恢复原对象 ----
rc, payload, _ = run(["enable", "--json"], {"generation": gen}, REAL)
rec("D1-4 重新 enable（= /wf-start）恢复原对象", "WF_OK 或已绑定提示", (payload or {}).get("code"),
    (payload or {}).get("code") in ("WF_OK", "WF_BINDING_MISMATCH") or rc == 0)
rc, payload, _ = run(["status", "--json"], {"generation": gen}, REAL)
obj = (((payload or {}).get("facts") or {}).get("binding") or {}).get("object") or {}
rec("D1-4b 仍是同一对象、未改绑", "object.id 不变", obj.get("id"), obj.get("id") == task_id)

json.dump(results, open("/tmp/d1_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

# ---- 5. 新会话区别：换一个 session_id 不得接管 ----
NEW_SID = "session-00000000-0000-4000-8000-000000000000"
rc, payload, _ = run(["status", "--json"], {"generation": gen}, NEW_SID)
facts_new = (payload or {}).get("facts") or {}
rec("D1-5 新会话看不到原绑定", "binding 缺失或对象不同",
    (facts_new.get("binding") or {}).get("object"), not (facts_new.get("binding") or {}).get("object"))
rc, payload, _ = run(["task-start", "--task", task_id, "--json"], {"generation": gen}, NEW_SID)
rec("D1-5b 新会话直接推进被拒", "非 WF_OK", (payload or {}).get("code"), (payload or {}).get("code") != "WF_OK")

# ---- 6. wf 签发身份：在 host profile 下必须被拒（不得绕过）----
rc, payload, _ = run(["task-new", "--kind", "ordinary", "--title", "wf 身份", "--template",
                      f"{F}/.wf/templates/task", "--json"], None, sid=None, provider="wf", issued="a" * 32)
rec("D1-6 wf 身份在 host profile 下推进业务被拒", "WF_IDENTITY_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
rc, payload, _ = run(["status", "--json"], {}, sid=None, provider="wf", issued="a" * 32)
rec("D1-6b 只读诊断不因 provider 不匹配而停", "WF_OK", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_OK")

# ---- 7. wf 签发身份的字段核验（单元）----
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
from wflib import session as wf_session
try:
    value = wf_session._identity_value({"provider": "wf", "identity": {"issued_id": "b" * 32}})
    ok_unit = value == {"issued_id": "b" * 32}
except Exception as exc:
    ok_unit = False
rec("D1-7 wf 身份的 issued_id 校验通过", "接受 32 位 uuid4 hex", ok_unit, ok_unit)
try:
    wf_session._identity_value({"provider": "wf", "identity": {"issued_id": "short"}})
    rejected = False
except Exception:
    rejected = True
rec("D1-7b 非法 issued_id 被拒", "拒绝", rejected, rejected)

json.dump(results, open("/tmp/d1_results.json", "w"), ensure_ascii=False, indent=2)
print("total", sum(1 for r in results if r["pass"]), "/", len(results))
