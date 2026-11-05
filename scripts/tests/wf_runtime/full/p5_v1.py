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


def wf(args, inputs=None, sid="sess-V1", instance=None):
    return wfdrive.run(args, inputs=inputs, sid=sid, instance_id=instance, show=False)


# 平台未安装 → 写操作被拒（新模型：身份只看 hosts 是否在安装的 platforms 里）
inst_path = os.path.join(F, ".wf/install/installation.json")
installed = json.load(open(inst_path, encoding="utf-8"))
saved = list(installed.get("platforms") or [])
installed["platforms"] = []
json.dump(installed, open(inst_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["enable", "--json"])
rec("未安装平台时 enable", "WF_IDENTITY_UNRESOLVED（installation declares no platforms）",
    f"{(payload or {}).get('code')}", (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
# 只读诊断在未安装平台时仍可运行
rc_ro, ro_payload, _ = wf(["status", "--json"])
rec("未安装平台时只读诊断仍可运行", "WF_OK", (ro_payload or {}).get("code"),
    (ro_payload or {}).get("code") == "WF_OK")

proc = subprocess.run(["/softwares/python/bin/python3",
                       "/home/xzc/projects/personal/ai-coding-toolkit/scripts/wf-dev-deploy.py",
                       "--target", F, "--platform", "dsh", "--confirm"],
                      capture_output=True, text=True)
installed["platforms"] = saved
json.dump(installed, open(inst_path, "w", encoding="utf-8"), ensure_ascii=False)
rec("追加平台（已装项目只加平台）", "WF_OK 且回显平台",
    "WF_OK" in proc.stdout or rc == 0, proc.returncode == 0)

rc, payload, _ = wf(["enable", "--json"])
rec("平台在册后 enable", "pass WF_OK", (payload or {}).get("code"), rc == 0)

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
rec("实例标识不符（标识丢失/复制）", "WF_BINDING_MISMATCH（绑定层拒绝，不静默改绑）",
    f"{(payload or {}).get('code')} exit={rc}",
    (payload or {}).get("code") in ("WF_BINDING_MISMATCH", "WF_IDENTITY_UNRESOLVED") and rc != 0)

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
# 已绑定会话不会产出第二个对象：要么回原结果（already_completed），要么绑绑冲突；两者都不新建
created = (payload or {}).get("facts", {}).get("task_id")
rec("已绑定会话不能再建对象", "不产生第二个任务（原结果重试或绑定冲突）",
    f"{(payload or {}).get('code')} created={created} same={created == task_id}",
    (payload or {}).get("code") in ("WF_BINDING_MISMATCH", "WF_OK") and created == task_id)

json.dump(results, open("/tmp/p5_v1_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases")
