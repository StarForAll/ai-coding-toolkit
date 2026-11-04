#!/usr/bin/env python3
"""V1：宿主会话身份能力与固定绑定（F1v 夹具，capability 初值 unknown）。"""
import json, os, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []


def rec(case, expected, actual, passed, note=""):
    results.append({"case": case, "expected": expected, "actual": actual, "pass": passed, "note": note})
    print(f"[V1] {case}: {'PASS' if passed else 'FAIL'} — {actual}")


def wf(args, inputs=None, sid="sess-A", instance=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, instance_id=instance, show=False)


rc, payload, _ = wf(["enable", "--json"])
rec("capability=unknown 时 enable", "needs_decision WF_IDENTITY_UNRESOLVED",
    f"{(payload or {}).get('code')} exit={rc}", (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED" and rc == 2,
    "facts 列未核实的稳定性/传递事实")

proc = subprocess.run(["/softwares/python/bin/python3",
                       "/home/xzc/projects/personal/ai-coding-toolkit/scripts/wf-dev-deploy.py",
                       "--target", F, "--skill-root", "/tmp/wf-fixtures/skills",
                       "--confirm", "--host-id", "dsh", "--verify-capability",
                       "--capability-evidence", "kind=reentry;ref=夹具内同会话重入观察;by=test fixture"],
                      capture_output=True, text=True)
rec("维护预览更新 session_profile", "只更新安装记录（资产与数据未变）",
    "仅更新" in proc.stdout, "仅更新" in proc.stdout)

rc, payload, _ = wf(["enable", "--json"])
rec("verified 后 enable", "pass WF_OK", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "V1 绑定用例",
                     "--template", f"{F}/.wf/templates/task", "--json"])
task_id = (payload or {}).get("facts", {}).get("task_id")
gen = (payload or {}).get("facts", {}).get("generation")
inst = (payload or {}).get("facts", {}).get("instance_id")
rec("task-new 一次完成写权获取+首次绑定+创建", "pass 且回显 generation 与 instance_id",
    f"task={task_id} gen={gen} inst={inst}", rc == 0 and bool(gen) and bool(inst))

rc, payload, _ = wf(["enable", "--json"])
rec("重复调用 enable", "pass（不重复绑定、不新建绑定）", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["status", "--json"], instance=inst)
rec("同一身份+同一实例标识（压缩后恢复）", "position.task_id 指向原任务",
    f"task_id={(payload or {}).get('position', {}).get('task_id')}",
    (payload or {}).get("position", {}).get("task_id") == task_id)

rc, payload, _ = wf(["bind", "--task", task_id, "--json"], instance="0" * 32)
rec("实例标识不符（标识丢失/复制）", "needs_decision WF_IDENTITY_UNRESOLVED",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED" and rc == 2)

rc, payload, _ = wf(["task-pause", "--task", task_id, "--reason", "V1 交接", "--json"], {"generation": gen})
rec("暂停当前任务", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen})
rec("释放写权（合法终态/暂停后）", "pass", (payload or {}).get("code"), rc == 0)

rc, payload, _ = wf(["bind", "--task", task_id, "--json"], sid="sess-B")
rec("新会话按就绪对象 bind 接续", "pass 并回显新代次",
    f"{(payload or {}).get('code')} gen={(payload or {}).get('facts', {}).get('generation')}",
    rc == 0)

rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "不应成功", "--template",
                     f"{F}/.wf/templates/task", "--json"], sid="sess-B")
rec("已绑定会话不能再建对象", "blocked WF_BINDING_MISMATCH",
    (payload or {}).get("code"), (payload or {}).get("code") == "WF_BINDING_MISMATCH")

json.dump(results, open("/tmp/p5_v1_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases")
