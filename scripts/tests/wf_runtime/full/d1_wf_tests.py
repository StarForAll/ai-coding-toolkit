#!/usr/bin/env python3
"""C 段实跑：provider=wf 的签发路径端到端（携带/恢复/丢失/复制到新会话）。"""
import json, os, subprocess, uuid
F = os.environ.get("WF_FIX", "/tmp/wf-fixtures/d1")
WF = os.path.join(F, ".wf/bin/wf.py")
PYTHON = "/usr/bin/python3"
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def run(args, inputs=None, issued=None, activation=True, instance_id=None):
    env = {"session": {"provider": "wf", "identity": {"issued_id": issued}, "instance_id": instance_id,
                       "activation": ({"enabled": True, "start_source": "human:test",
                                       "enabled_at": "2026-11-05T00:00:00.000000Z"} if activation else None)},
           "inputs": inputs or {}}
    proc = subprocess.run([PYTHON, WF] + list(args), cwd=F, input=json.dumps(env), capture_output=True, text=True)
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else None
    except ValueError:
        payload = None
    return proc.returncode, payload, proc.stdout


ISSUED = uuid.uuid4().hex
print("wf 签发 id：", ISSUED[:12] + "…")

rc, payload, _ = run(["task-new", "--kind", "ordinary", "--title", "wf 签发路径",
                      "--template", f"{F}/.wf/templates/task", "--json"], None, ISSUED)
facts = (payload or {}).get("facts", {})
task_id, gen = facts.get("task_id"), facts.get("generation")
rec("C-1 wf 签发身份首次绑定", "WF_OK", (payload or {}).get("code"), rc == 0 and bool(task_id))

rc, payload, _ = run(["status", "--json"], {"generation": gen}, ISSUED)
obj = (((payload or {}).get("facts") or {}).get("binding") or {}).get("object") or {}
rec("C-2 同 issued_id 重入保持绑定", "object.id 一致", obj.get("id"), obj.get("id") == task_id)

rc, payload, _ = run(["task-start", "--task", task_id, "--json"], {"generation": gen}, ISSUED, activation=False)
rec("C-3 压缩未携带 activation → 业务动作被拒", "WF_NOT_ENABLED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_NOT_ENABLED")

rc, payload, _ = run(["enable", "--json"], {"generation": gen}, ISSUED)
rec("C-4 重新 enable 恢复原对象", "WF_OK", (payload or {}).get("code"), rc == 0)
rc, payload, _ = run(["status", "--json"], {"generation": gen}, ISSUED)
obj = (((payload or {}).get("facts") or {}).get("binding") or {}).get("object") or {}
rec("C-4b 未产生改绑", "object.id 不变", obj.get("id"), obj.get("id") == task_id)

OTHER = uuid.uuid4().hex
rc, payload, _ = run(["status", "--json"], {"generation": gen}, OTHER)
obj = (((payload or {}).get("facts") or {}).get("binding") or {}).get("object") or {}
rec("C-5 复制到新会话不可见原绑定", "无绑定", obj, not obj)
rc, payload, _ = run(["task-start", "--task", task_id, "--json"], {"generation": gen}, OTHER)
rec("C-5b 新会话推进被拒", "非 WF_OK", (payload or {}).get("code"), (payload or {}).get("code") != "WF_OK")

rc, payload, _ = run(["status", "--json"], {"generation": gen}, None)
rec("C-6 丢失 issued_id → 身份未决", "WF_IDENTITY_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")

json.dump(results, open("/tmp/d1_wf_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
