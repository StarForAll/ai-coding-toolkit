#!/usr/bin/env python3
"""第五十八轮 R93：平台清单即身份事实（无 --host-id）+ 多 agent 覆盖保护。"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, "/tmp")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wfdrive

F = wfdrive.FIX
results = []


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": actual, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R93", instance=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, instance_id=instance)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


inst_path = os.path.join(F, ".wf/install/installation.json")
installation = json.load(open(inst_path, encoding="utf-8"))
rec("R93 安装记录只有 platforms、没有 session_profile", "platforms 非空且无 session_profile",
    f"{installation.get('platforms')}/{('session_profile' in installation)}",
    bool(installation.get("platforms")) and "session_profile" not in installation)

# 1) 未安装的宿主：写操作被拒、只读放行
backup = open(inst_path, encoding="utf-8").read()
muted = json.loads(backup); muted["platforms"] = ["codex"]
json.dump(muted, open(inst_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["enable", "--json"], sid="sess-R93-dsh")
rec("R93 未安装的宿主写操作被拒", "WF_IDENTITY_UNRESOLVED",
    (payload or {}).get("code"), (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
rc_ro, ro_payload, _ = wf(["status", "--json"], sid="sess-R93-dsh")
rec("R93 未安装的宿主仍可只读诊断", "WF_OK", (ro_payload or {}).get("code"),
    (ro_payload or {}).get("code") == "WF_OK")
open(inst_path, "w", encoding="utf-8").write(backup)

# 2) 平台在册后同一宿主放行
rc, payload, _ = wf(["enable", "--json"], sid="sess-R93-dsh")
rec("R93 平台在册即放行（无登记、无证据）", "WF_OK", (payload or {}).get("code"), rc == 0)

# 3) 两个 agent 交替操作同一任务：串行 + 代次保护
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R93 多 agent",
                     "--template", f"{F}/.wf/templates/task", "--json"], sid="sess-R93-A")
facts = (payload or {}).get("facts") or {}
task_id, generation_a = facts.get("task_id"), facts.get("generation")
rec("R93 A 建任务并持写权", "WF_OK 且有代次", f"{task_id}/{generation_a}",
    rc == 0 and bool(generation_a))
rc_b, payload_b, _ = wf(["bind", "--task", task_id, "--json"], sid="sess-R93-B")
rec("R93 B 在 A 持写权时拿不到对象", "WF_WRITER_BUSY 或 WF_BINDING_MISMATCH（都不得放行）",
    (payload_b or {}).get("code"),
    (payload_b or {}).get("code") in ("WF_WRITER_BUSY", "WF_BINDING_MISMATCH"))
wf(["task-pause", "--task", task_id, "--reason", "交接", "--json"], {"generation": generation_a},
   sid="sess-R93-A")
wf(["writer", "release", "--json"], {"generation": generation_a}, sid="sess-R93-A")
rc_b2, payload_b2, _ = wf(["bind", "--task", task_id, "--json"], sid="sess-R93-B")
rec("R93 释放后 B 可接续同一任务", "WF_OK", (payload_b2 or {}).get("code"), rc_b2 == 0)
# A 拿旧代次再写 → 必须被代次闸拒绝
rc_a2, payload_a2, _ = wf(["task-resume", "--task", task_id, "--json"],
                          {"generation": generation_a}, sid="sess-R93-A")
rec("R93 A 用旧代次写被拒", "WF_GENERATION_STALE 或 WF_WRITER_BUSY",
    (payload_a2 or {}).get("code"),
    (payload_a2 or {}).get("code") in ("WF_GENERATION_STALE", "WF_WRITER_BUSY"))

# 4) 装完再追加 agent：只加平台，不动既有资产（要求写权空闲）
wf(["writer", "release", "--json"], {"generation": gen()}, sid="sess-R93-B")
install_py = "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/install.py"
before_assets = len(installation.get("assets") or [])
# 夹具是 dev 部署（release_ref=dev:...）：追加平台用开发态部署工具，正式发行用 install.py
dev_deploy = "/home/xzc/projects/personal/ai-coding-toolkit/scripts/wf-dev-deploy.py"
proc = subprocess.run(["/softwares/python/bin/python3", dev_deploy, "--target", F,
                       "--platform", "cursor", "--confirm"], capture_output=True, text=True)
after = json.load(open(inst_path, encoding="utf-8"))
if proc.returncode != 0:
    print("   add-platform stdout:", (proc.stdout or proc.stderr)[-300:])
rec("R93 追加平台只改 platforms", "platforms 增加且 assets 数量不变",
    f"{sorted(set(after.get('platforms') or []) - set(installation.get('platforms') or []))}/"
    f"{len(after.get('assets') or []) == before_assets}",
    "cursor" in (after.get("platforms") or []) and len(after.get("assets") or []) == before_assets)

json.dump(results, open("/tmp/r90_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
