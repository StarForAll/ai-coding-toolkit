#!/usr/bin/env python3
"""第七轮 R35–R37 用例。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, cli as wf_cli

F = wfdrive.FIX
results = []
AT = "2026-11-04T02:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Y1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R35-R37 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-Y1"):
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


def approve(task_id, digest, gen, sid="sess-Y1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r35_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/r35_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- R35：异常归档「终态已写、目录未移动」的续做 ----------------
clean()
os.makedirs(os.path.join(F, "a35"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R35 放弃续做", ["a35/**"], "sess-Y1")
approve(task1, d1, gen1, "sess-Y1")
open(os.path.join(F, "a35/w.txt"), "w").write("w\n")
wf(["task-start", "--task", task1, "--json"], {"generation": gen1}, "sess-Y1")
disp = {"changes": [{"object": "a35/w.txt", "decision_ref": AT, "reason": "提交保留"}], "targets": [], "pending": []}
json.dump(disp, open("/tmp/r35_disp.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["task-abandon", "--task", task1, "--decision",
                     dfile("/tmp/r35_stop.json", [dec(f"stop {task1}", "abandon", d1),
                                                  dec("a35/**", "commit", d1)]),
                     "--disposition", "/tmp/r35_disp.json", "--json"], {"generation": gen1}, "sess-Y1")
rec("R35 准备：放弃结案", "WF_OK", (payload or {}).get("code"), rc == 0)
archived_dir = wf_tasks.task_dir(F, task1)
active_dir = os.path.join(F, ".wf/tasks", os.path.basename(archived_dir))
subprocess.run(["git", "reset", "-q", "--mixed", "HEAD~1"], cwd=F, capture_output=True)
shutil.move(archived_dir, active_dir)
rec("R35 准备：目录回到活动位置", "活动在、归档不在",
    f"active={os.path.exists(active_dir)} archived={os.path.exists(archived_dir)}",
    os.path.exists(active_dir) and not os.path.exists(archived_dir))
rc, payload, _ = wf(["task-abandon", "--task", task1, "--decision",
                     dfile("/tmp/r35_stop2.json", [dec(f"stop {task1}", "abandon", d1),
                                                   dec("a35/**", "commit", d1)]),
                     "--disposition", "/tmp/r35_disp.json", "--json"], {"generation": gen1}, "sess-Y1")
moved = wf_tasks.task_dir(F, task1)
facts = (payload or {}).get("facts", {})
rec("R35 重入先完成移动", "记录回到归档根",
    f"dir={os.path.relpath(moved, F) if moved else None}",
    moved is not None and ".wf/tasks/archive/" in moved.replace(os.sep, "/"))
rec("R35 重入报告已持久化", "WF_OK 且 record_persisted",
    f"{(payload or {}).get('code')} persisted={facts.get('record_persisted')}",
    (payload or {}).get("code") == "WF_OK" and facts.get("record_persisted") is True)
wf(["writer", "release", "--json"], {"generation": gen1}, "sess-Y1")

# ---------------- R36：同一会话新代次不得被旧调用释放 ----------------
clean()
task2, gen2, dir2, d2 = make_task("R36 代次", ["a36/**"], "sess-Y2")
approve(task2, d2, gen2, "sess-Y2")
rc_s, start2, _ = wf(["task-start", "--task", task2, "--json"], {"generation": gen2}, "sess-Y2")
rec("R36 准备：开工", "WF_OK", (start2 or {}).get("code"), rc_s == 0)
wf(["task-pause", "--task", task2, "--reason", "R36", "--json"], {"generation": gen2}, "sess-Y2")
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen2}, "sess-Y2")
rec("R36 准备：释放第 1 代", "WF_OK", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["writer", "acquire", "--task", task2, "--json"], {"generation": gen2}, "sess-Y2")
gen3 = ((payload or {}).get("facts") or {}).get("generation")
rec("R36 准备：重新取得新代次", "WF_OK 且代次前进",
    f"{(payload or {}).get('code')} gen={gen3}", rc == 0 and gen3 and int(gen3) > int(gen2))
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen2}, "sess-Y2")
rec("R36 旧代次不得释放新写权", "WF_GENERATION_STALE", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_GENERATION_STALE")
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen3}, "sess-Y2")
rec("R36 当前代次可释放", "WF_OK", (payload or {}).get("code"), rc == 0)

# ---------------- R37：真实 stop --choice keep 的 WIP 被消费 ----------------
clean()
os.makedirs(os.path.join(F, "a37"), exist_ok=True)
task3, gen3b, dir3, d3 = make_task("R37 保留 WIP", ["a37/**"], "sess-Y3")
approve(task3, d3, gen3b, "sess-Y3")
open(os.path.join(F, "a37/k.txt"), "w").write("k\n")
rc_s, start3, _ = wf(["task-start", "--task", task3, "--json"], {"generation": gen3b}, "sess-Y3")
rec("R37 准备：开工", "WF_OK", (start3 or {}).get("code"), rc_s == 0)
keep = dfile("/tmp/r37_keep.json", [dec("a37/k.txt", "keep", d3)])
rc, payload, _ = wf(["stop", "--decision", keep, "--json"], {"generation": gen3b}, "sess-Y3")
rec("R37 准备：收工保留 WIP", "WF_OK 且记录 handoff.wip",
    f"{(payload or {}).get('code')} paths={((payload or {}).get('facts') or {}).get('wip', {}).get('paths')}",
    rc == 0 and ((payload or {}).get("facts") or {}).get("wip", {}).get("paths"))
blockers = wf_cli.wip_blockers(F, exclude_id="2026-" + "0" * 32)
rec("R37 真实 WIP 被识别", "列出该任务与路径",
    f"blocked={json.dumps(blockers, ensure_ascii=False)[:140]}",
    bool(blockers) and blockers[0].get("task") == task3 and "a37/k.txt" in (blockers[0].get("paths") or []))
record_path = os.path.join(dir3, "task.json")
record = json.load(open(record_path))
caught = None
try:
    wf_tasks.ensure_releasable(record, F)
except Exception as exc:
    caught = getattr(exc, "code", None)
rec("R37 保留 WIP 阻断空闲释放", "WF_WORKSPACE_UNRESOLVED", caught, caught == "WF_WORKSPACE_UNRESOLVED")
# 保留路径消失后再恢复 → 阻断
rc, payload, _ = wf(["writer", "acquire", "--task", task3, "--json"], {"generation": gen3b}, "sess-Y3")
gen_after = ((payload or {}).get("facts") or {}).get("generation") or gen3b
rec("R37 准备：恢复前取得写权", "WF_OK", (payload or {}).get("code"), rc == 0)
os.remove(os.path.join(F, "a37/k.txt"))
rc, payload, _ = wf(["task-resume", "--task", task3, "--json"], {"generation": gen_after}, "sess-Y3")
rec("R37 保留路径变化时恢复被拒", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")

json.dump(results, open("/tmp/r35r37_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
