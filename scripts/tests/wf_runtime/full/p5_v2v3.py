#!/usr/bin/env python3
"""V2（归档持久化派生）与 V3（维护组与后续任务共存），F1 夹具（已完成初始化任务）。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
import wfdrive

F = wfdrive.FIX
results = []


def rec(vid, case, expected, actual, passed, note=""):
    results.append({"V": vid, "case": case, "expected": expected, "actual": actual, "pass": passed, "note": note})
    print(f"[{vid}] {case}: {'PASS' if passed else 'FAIL'} — {actual}")


def wf(args, inputs=None, sid="sess-C"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def git(*args):
    return subprocess.run(["git", *args], cwd=F, capture_output=True, text=True, check=False).stdout.strip()


def new_task(title, touch_paths, sid="sess-C", argv=("print(1)",)):
    rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", title,
                         "--template", f"{F}/.wf/templates/task", "--json"], sid=sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    directory = os.path.join(F, facts.get("directory", ""))
    prd = f"""# {title}

## 机读块

<!-- wf-plan:v1 -->
```json
{{"schema_version": 1,
  "touch_paths": {json.dumps(touch_paths, ensure_ascii=False)},
  "acceptance": [{{"id": "a1", "statement": "用例成立", "verification_ids": ["v1"]}}],
  "verifications": [{{"id": "v1", "invocation": {{"kind": "argv", "argv": ["/usr/bin/python3", "-c", "{argv[0]}"]}},
                     "cwd": ".", "input_refs": [], "required": true, "consume_at": "check"}}]}}
```
"""
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    return task_id, gen, digest


def approve(task_id, digest, gen, sid="sess-C"):
    at = "2026-11-03T04:00:00.000000Z"
    path = f"/tmp/decision_{task_id}.json"
    json.dump([{"source": f"human ({sid})", "at": at, "subject": "approve", "object_digest": digest,
                "choice": "approve", "reason": "用例"}], open(path, "w"), ensure_ascii=False)
    return wf(["task-approve", "--task", task_id, "--decision", path, "--json"], {"generation": gen}, sid)


# ---------- V3(a)：维护组未提交期间完成一个不重叠任务 ----------
task_v2, gen_v2, digest_v2 = new_task("V2 归档恢复用例", ["docs/v2.txt"])
rc, payload, _ = approve(task_v2, digest_v2, gen_v2)
rec("V3", "维护组未提交时创建并批准不重叠任务", f"pass（reject: WF_ASSET_DECISION）",
    (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-start", "--task", task_v2, "--json"], {"generation": gen_v2})
rec("V3", "不重叠任务开工（不带入维护组）", "pass", (payload or {}).get("code"), rc == 0)
os.makedirs(os.path.join(F, "docs"), exist_ok=True)
open(os.path.join(F, "docs/v2.txt"), "w").write("v2\n")
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"}, "requirement": {"conclusion": "pass", "basis": "a1"}},
          open("/tmp/notes_v2.json", "w"))
rc, payload, _ = wf(["task-check", "--task", task_v2, "--review-notes", "/tmp/notes_v2.json", "--json"],
                    {"generation": gen_v2})
rec("V2", "Check pass（V2 准备）", "pass", (payload or {}).get("code"), rc == 0)
wf(["task-knowledge", "--task", task_v2, "--decision", "no-update", "--json"], {"generation": gen_v2})
at = "2026-11-03T04:10:00.000000Z"
json.dump([{"source": "human (sess-C)", "at": at, "subject": f"finish {task_v2}", "object_digest": digest_v2,
            "choice": "finish", "reason": "V2 用例"},
           {"source": "human (sess-C)", "at": at, "subject": "docs/v2.txt", "object_digest": digest_v2,
            "choice": "commit", "reason": "授权提交 docs/v2.txt"}],
          open("/tmp/decision_v2_archive.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["archive", "--task", task_v2, "--decision", "/tmp/decision_v2_archive.json", "--json"],
                    {"generation": gen_v2})
commit_ok = (payload or {}).get("facts", {}).get("commit", {}).get("committed") is True
rec("V3", "不重叠任务归档（维护组仍待提交）", "pass 且提交成功（reject: 捎带维护组）",
    f"{(payload or {}).get('code')} commit={commit_ok}", rc == 0 and commit_ok)

# ---------- V2：归档提交后的持久化派生 ----------
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen_v2})
rec("V2", "归档后释放写权（另一合法动作改写公共字段）", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["archive", "--task", task_v2, "--decision", "/tmp/decision_v2_archive.json", "--json"],
                    {"generation": gen_v2})
facts = (payload or {}).get("facts", {})
rec("V2", "独立进程重入 archive", "报告「归档已持久化」，不重复归档/提交",
    f"{(payload or {}).get('code')} persisted={facts.get('archive_persisted', {}).get('persisted')}",
    rc == 0 and facts.get("archive_persisted", {}).get("persisted") is True)
count = git("log", "--format=%s").count(f"wf: archive {task_v2}")
rec("V2", "归档提交不重复", "同一任务仅一条 archive 提交", f"count={count}", count == 1)

# ---------- V3(b)：重叠任务被维护组挡住 ----------
task_v3, gen_v3, digest_v3 = new_task("V3 重叠维护组用例", [".wf/workflows/task-flow.md", ".wf/v3.txt"],
                                      sid="sess-D")
rc, payload, _ = approve(task_v3, digest_v3, gen_v3, sid="sess-D")
rec("V3", "创建并批准重叠任务", "pass", (payload or {}).get("code"), rc == 0)
rc, payload, _ = wf(["task-start", "--task", task_v3, "--json"], {"generation": gen_v3}, sid="sess-D")
rec("V3", "重叠任务开工", "blocked WF_WIP_UNRESOLVED",
    f"{(payload or {}).get('code')} exit={rc}", (payload or {}).get("code") == "WF_WIP_UNRESOLVED" and rc == 1)

# ---------- V3(c)：人明确处置维护组 ----------
writer = json.load(open(os.path.join(F, ".wf/writer.json")))
operation = writer["maintenance_results"][0]["operation"]
git("add", ".wf", ".gitignore")
subprocess.run(["git", "commit", "-qm", "wf: maintenance install group"], cwd=F, capture_output=True)
sha = git("rev-parse", "HEAD")
decision = {"source": "human (terminal)", "at": "2026-11-03T04:20:00.000000Z",
            "subject": f"maintenance group {operation} commit", "object_digest": "sha256:" + "0" * 64,
            "choice": "commit", "reason": "维护组按登记终态原样提交"}
plan = {"operation": operation,
        "disposition": {"kind": "commit", "decision": decision,
                        "evidence": {"commit": sha, "verified_by": "human", "paths": "install group"}}}
json.dump(plan, open("/tmp/dispose_plan.json", "w"), ensure_ascii=False, indent=2)
import re as _re

preview = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"),
                          "--project", F, "--dispose", "/tmp/dispose_plan.json"],
                         capture_output=True, text=True)
token = _re.search(r"令牌：([0-9a-f]{32})", preview.stdout)
apply_run = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/repair.py"),
                            "--project", F, "--dispose", "/tmp/dispose_plan.json",
                            "--apply", "--nonce", token.group(1) if token else "0" * 32],
                           capture_output=True, text=True,
                           input=(token.group(1) + "\n") if token else "")
rec("V3", "人处置维护组并回写 disposition（预览+令牌）",
    "repair --dispose 预览给出令牌并写回回执",
    f"token={'yes' if token else 'no'} {apply_run.stdout.strip().splitlines()[-1] if apply_run.stdout.strip() else apply_run.stderr[-120:]}",
    bool(token) and apply_run.returncode == 0 and "WF_OK" in apply_run.stdout)

rc, payload, _ = wf(["task-start", "--task", task_v3, "--json"], {"generation": gen_v3}, sid="sess-D")
rec("V3", "处置后重叠任务恢复推进", "pass",
    f"{(payload or {}).get('code')} facts={json.dumps((payload or {}).get('facts', {}), ensure_ascii=False)[:120]}",
    rc == 0)

# ---------- V3(d)：writer 未被无授权提交 ----------
touched = git("log", "--name-only", "--format=").splitlines()
in_task_commits = []
for line in git("log", "--format=%H").splitlines():
    files = git("show", "--name-only", "--format=", line).splitlines()
    if any(f.startswith(".wf/tasks/") for f in files) and ".wf/writer.json" in files:
        in_task_commits.append(line)
rec("V3", "writer 整文件未被任务提交捎带", "任务提交中不出现 .wf/writer.json（维护组提交另计）",
    f"task_commits_with_writer={len(in_task_commits)}", len(in_task_commits) == 0)

json.dump(results, open("/tmp/p5_v2v3_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results))
