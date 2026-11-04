#!/usr/bin/env python3
"""第八轮 R38–R39 用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import cli as wf_cli

F = wfdrive.FIX
results = []
AT = "2026-11-04T03:30:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-Z1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R38/R39 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def writer_generation():
    record = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8"))
    return record.get("generation")


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
               dfile(f"/tmp/r38_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


# ---------------- R38：新会话入口沿用同一前置 ----------------
clean()
os.makedirs(os.path.join(F, "a38"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R38 保留 WIP", ["a38/**"], "sess-Z1")
approve(task1, d1, gen1, "sess-Z1")
open(os.path.join(F, "a38/k.txt"), "w").write("k\n")
rc_s1, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": writer_generation()}, "sess-Z1")
rec("R38 准备：开工", "WF_OK",
    f"{(start1 or {}).get('code')} facts={json.dumps((start1 or {}).get('facts'), ensure_ascii=False)[:160]}", rc_s1 == 0)
keep = dfile("/tmp/r38_keep.json", [dec("a38/k.txt", "keep", d1)])
rc, payload, _ = wf(["stop", "--decision", keep, "--json"], {"generation": writer_generation()}, "sess-Z1")
rec("R38 准备：保留 WIP", "WF_OK",
    f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:160]}", rc == 0)
blockers = wf_cli.wip_blockers(F)
rec("R38 准备：WIP 已被识别", "列出该任务", blockers and blockers[0].get("task") == task1, bool(blockers))
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R38 新任务",
                     "--template", f"{F}/.wf/templates/task", "--json"], {"generation": 1}, "sess-Z3")
rec("R38 task-new 被同一前置拦住", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")
# 同对象接续由 R41 放行（响应带出来源 WIP），这里只核「换对象」被拒：任务只有一个时不可构造，
# 该分支由 R40–R42 套件用第二对象覆盖。
caught = None
try:
    wf_cli.assert_no_foreign_wip(type("C", (), {"root": F})(), exclude_id="2026-" + "0" * 32)
except Exception as exc:
    caught = getattr(exc, "code", None)
rec("R38 统一前置对 writer acquire 同判", "WF_WORKSPACE_UNRESOLVED", caught,
    caught == "WF_WORKSPACE_UNRESOLVED")

# ---------------- R39：实际处置后解除 ----------------
record_path = os.path.join(dir1, "task.json")
record = json.load(open(record_path))
rec("R39 keep 记录 resolved 为空", "resolved=None",
    (record.get("handoff") or {}).get("wip", {}).get("resolved"),
    (record.get("handoff") or {}).get("wip", {}).get("resolved") is None)
state_now = json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("state")
rc, payload, _ = wf(["writer", "acquire", "--task", task1, "--json"], {"generation": writer_generation()}, "sess-Z1")
rec("R39 准备：恢复前取得写权", "WF_OK",
    f"{(payload or {}).get('code')} writer_state={state_now} facts={json.dumps((payload or {}).get('facts'), ensure_ascii=False)[:120]}", rc == 0)
wf(["task-resume", "--task", task1, "--json"], {"generation": writer_generation()}, "sess-Z1")
record = json.load(open(record_path))
rec("R39 路径仍脏时 resume 不写解除", "resolved 仍为 None",
    (record.get("handoff") or {}).get("wip", {}).get("resolved"),
    (record.get("handoff") or {}).get("wip", {}).get("resolved") is None)
commit_stop = dfile("/tmp/r39_commit.json", [dec("a38/k.txt", "commit", d1),
                                             dec("a38/k.txt", "commit", d1)])
rc, payload, _ = wf(["stop", "--decision", commit_stop, "--json"], {"generation": writer_generation()}, "sess-Z1")
rec("R39 收工提交成功", "WF_OK", (payload or {}).get("code"), rc == 0)
record = json.load(open(record_path))
resolved = (record.get("handoff") or {}).get("wip", {}).get("resolved")
rec("R39 提交后写解除结论", "resolved.choice=commit",
    json.dumps(resolved, ensure_ascii=False)[:120] if resolved else None,
    bool(resolved) and resolved.get("choice") == "commit")
rec("R39 已提交不再阻断他对象", "空列表", wf_cli.wip_blockers(F), not wf_cli.wip_blockers(F))


json.dump(results, open("/tmp/r38r39_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
