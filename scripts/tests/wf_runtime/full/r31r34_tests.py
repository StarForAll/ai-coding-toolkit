#!/usr/bin/env python3
"""第六轮 R31–R34 用例。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import tasks as wf_tasks, gates as wf_gates, cli as wf_cli

F = wfdrive.FIX
results = []
AT = "2026-11-04T00:30:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-X1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R31-R34 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def make_task(title, touch, sid="sess-X1"):
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


def approve(task_id, digest, gen, sid="sess-X1"):
    return wf(["task-approve", "--task", task_id, "--decision",
               dfile(f"/tmp/r31_{task_id}_a.json", [dec("approve", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/r31_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- R31b：归档「终态已写、目录未移动」的恢复 ----------------
clean()
os.makedirs(os.path.join(F, "a31"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R31 归档恢复", ["a31/**"], "sess-X1")
approve(task1, d1, gen1, "sess-X1")
open(os.path.join(F, "a31/x.txt"), "w").write("x\n")
wf(["task-start", "--task", task1, "--json"], {"generation": gen1}, "sess-X1")
wf(["task-check", "--task", task1, "--review-notes", NOTES, "--json"], {"generation": gen1}, "sess-X1")
wf(["task-knowledge", "--task", task1, "--decision", "no-update", "--json"], {"generation": gen1}, "sess-X1")
rc, payload, _ = wf(["archive", "--task", task1, "--decision",
                     dfile("/tmp/r31_arch.json", [dec(f"finish {task1}", "finish", d1),
                                                  dec("a31/**", "commit", d1)]), "--json"],
                    {"generation": gen1}, "sess-X1")
rec("R31 准备：正常归档", "WF_OK", (payload or {}).get("code"), rc == 0)
# 还原成「终态已写、目录在活动位置、记录未提交」
archived_dir = wf_tasks.task_dir(F, task1)
active_dir = os.path.join(F, ".wf/tasks", os.path.basename(archived_dir))
subprocess.run(["git", "reset", "-q", "--mixed", "HEAD~1"], cwd=F, capture_output=True)
shutil.move(archived_dir, active_dir)
rec("R31 准备：目录回到活动位置", "活动目录存在、归档目录不存在",
    f"active={os.path.exists(active_dir)} archived={os.path.exists(archived_dir)}",
    os.path.exists(active_dir) and not os.path.exists(archived_dir))
rc, payload, _ = wf(["archive", "--task", task1, "--decision",
                     dfile("/tmp/r31_arch2.json", [dec(f"finish {task1}", "finish", d1),
                                                   dec("a31/**", "commit", d1)]), "--json"],
                    {"generation": gen1}, "sess-X1")
facts = (payload or {}).get("facts", {})
moved_back = wf_tasks.task_dir(F, task1)
rec("R31 重入先完成移动", "记录回到归档根下",
    f"dir={os.path.relpath(moved_back, F) if moved_back else None}",
    moved_back is not None and ".wf/tasks/archive/" in moved_back.replace(os.sep, "/"))
rec("R31 重入报告已持久化", "WF_OK 且 persisted=true",
    f"{(payload or {}).get('code')} persisted={(facts.get('archive_persisted') or {}).get('persisted')}",
    (payload or {}).get("code") == "WF_OK" and (facts.get("archive_persisted") or {}).get("persisted") is True)
wf(["writer", "release", "--json"], {"generation": gen1}, "sess-X1")

# ---------------- R31a：放弃后记录未提交的续做 ----------------
clean()
os.makedirs(os.path.join(F, "a31b"), exist_ok=True)
task2, gen2, dir2, d2 = make_task("R31 放弃续做", ["a31b/**"], "sess-X2")
approve(task2, d2, gen2, "sess-X2")
open(os.path.join(F, "a31b/y.txt"), "w").write("y\n")
wf(["task-start", "--task", task2, "--json"], {"generation": gen2}, "sess-X2")
disp = {"changes": [{"object": "a31b/y.txt", "decision_ref": AT, "reason": "提交保留"}], "targets": [], "pending": []}
json.dump(disp, open("/tmp/r31_disp.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["task-abandon", "--task", task2, "--decision",
                     dfile("/tmp/r31_stop.json", [dec(f"stop {task2}", "abandon", d2),
                                                  dec("a31b/**", "commit", d2)]),
                     "--disposition", "/tmp/r31_disp.json", "--json"], {"generation": gen2}, "sess-X2")
rec("R31 准备：放弃结案", "WF_OK", (payload or {}).get("code"), rc == 0)
subprocess.run(["git", "reset", "-q", "--mixed", "HEAD~1"], cwd=F, capture_output=True)
closed_dir = wf_tasks.task_dir(F, task2)
record_rel = os.path.relpath(closed_dir, F).replace(os.sep, "/")
rec("R31 准备：记录未提交", "任务仍归档、记录未入库",
    f"tracked={subprocess.run(['git','ls-files','--error-unmatch',f'{record_rel}/task.json'], cwd=F, capture_output=True).returncode == 0}",
    subprocess.run(["git", "ls-files", "--error-unmatch", f"{record_rel}/task.json"],
                   cwd=F, capture_output=True).returncode != 0)
rc, payload, _ = wf(["task-abandon", "--task", task2, "--decision",
                     dfile("/tmp/r31_stop2.json", [dec(f"stop {task2}", "abandon", d2),
                                                   dec("a31b/**", "commit", d2)]),
                     "--disposition", "/tmp/r31_disp.json", "--json"], {"generation": gen2}, "sess-X2")
tracked_now = subprocess.run(["git", "ls-files", "--error-unmatch", f"{record_rel}/task.json"],
                             cwd=F, capture_output=True).returncode == 0
rec("R31 放弃重入续做记录提交", "WF_OK 且记录已入库",
    f"{(payload or {}).get('code')} tracked={tracked_now}",
    (payload or {}).get("code") == "WF_OK" and tracked_now)
wf(["writer", "release", "--json"], {"generation": gen2}, "sess-X2")

# ---------------- R32：锁外核验后写权已转移，锁内必须重核 ----------------
os.makedirs(os.path.join(F, ".wf/session-bindings"), exist_ok=True)
real_id = wf_tasks.task_dir(F, task2).split("/")[-1].split("-")[0] + "-" + wf_tasks.task_dir(F, task2).split("/")[-1].split("-")[1]
json.dump({"object": {"kind": "task", "id": real_id}, "instance_id": "r32instance0000000000000000000000"},
          open(os.path.join(F, ".wf/session-bindings", "sess-R32.json"), "w"), ensure_ascii=False)


class FakeCtx:
    def __init__(self, root, key, record):
        self.root = root
        self._key = key
        self._record = record
        self.writes = 0

    def key(self):
        return self._key

    def writer(self):
        return self._record

    def session(self, required=True):
        return {"provider": "host", "identity": {"host_id": "dsh", "session_id": self._key},
                "instance_id": "r32instance0000000000000000000000", "activation": None}

    def profile(self):
        return {"host_id": "dsh", "provider": "host", "transport": "request_json",
                "capability": {"status": "verified", "verified_version": None, "evidence_refs": []}}

    def inputs(self):
        return {}

    def require_held(self, task=None, run=None):
        self.checks = getattr(self, "checks", 0) + 1
        holder = self._record.get("holder") or {}
        if getattr(self, "raise_on_call", None) == self.checks:
            # 模拟「锁外核验通过、锁内已被交出/换期」
            raise wf_cli.CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "changed between checks"})
        if self._record.get("state") != "held" or holder.get("id") != self._key:
            raise wf_cli.CliError("WF_WRITER_BUSY", {"holder": holder, "reason": "held by another session"})
        return self._record, holder


def writer(case):
    results.append({"case": case["name"], "expected": case["expected"], "actual": case["actual"],
                    "pass": bool(case["pass"])})
    print(f"[{'PASS' if case['pass'] else 'FAIL'}] {case['name']}: {case['actual']}")


holder_other = {"kind": "session", "id": "session-B", "generation": 3,
                "scope": {"object": {"kind": "task", "id": "2026-" + "a" * 32}}}
fake = FakeCtx(F, "sess-R32", {"state": "held", "generation": 3,
                               "holder": {"kind": "session", "id": "sess-R32", "generation": 3,
                                          "scope": {"object": {"kind": "task", "id": "2026-" + "a" * 32}}}})
fake.raise_on_call = 2
caught = None
try:
    with wf_cli._lock(F, hint="test"):
        pass
except Exception:
    pass
try:
    # 直接走释放路径：锁外核验通过（伪造），锁内应发现持有者已变
    wf_cli._writer_release(fake)
except Exception as exc:
    caught = getattr(exc, "code", None)
writer({"name": "R32 锁内持有者变更时拒绝释放", "expected": "WF_WRITER_BUSY",
        "actual": f"{caught} checks={getattr(fake, 'checks', 0)}",
        "pass": caught == "WF_WRITER_BUSY" and getattr(fake, "checks", 0) >= 2})

# ---------------- R33：他任务未处置 WIP 阻断获取；自身 pending 阻断释放 ----------------
clean()
os.makedirs(os.path.join(F, "a33"), exist_ok=True)
task3, gen3, dir3, d3 = make_task("R33 WIP", ["a33/**"], "sess-X3")
approve(task3, d3, gen3, "sess-X3")
open(os.path.join(F, "a33/z.txt"), "w").write("z\n")
wf(["task-start", "--task", task3, "--json"], {"generation": gen3}, "sess-X3")
wf(["task-pause", "--task", task3, "--reason", "WIP", "--json"], {"generation": gen3}, "sess-X3")
wf(["writer", "release", "--json"], {"generation": gen3}, "sess-X3")
record_path = os.path.join(dir3, "task.json")
record = json.load(open(record_path))
record["disposition"] = {"kind": "stop", "changes": [], "targets": [],
                         "pending": [{"object": "a33/z.txt", "reason": "待处置"}]}
json.dump(record, open(record_path, "w"), ensure_ascii=False)
clean()
blockers = wf_cli.wip_blockers(F, exclude_id="2026-" + "f" * 32)
rec("R33 他任务未处置 WIP 被识别", "列出该任务与其 pending",
    f"blocked={json.dumps(blockers, ensure_ascii=False)[:120]}",
    bool(blockers) and blockers[0].get("task") == task3)
rec("R33 排除自身后不阻断", "空列表", wf_cli.wip_blockers(F, exclude_id=task3), not wf_cli.wip_blockers(F, exclude_id=task3))
rc, payload, _ = wf(["writer", "acquire", "--task", task3, "--json"], {"generation": gen3}, "sess-X3")
rec("R33 准备：重新获取写权", "WF_OK", (payload or {}).get("code"), rc == 0)
gen_after = ((payload or {}).get("facts") or {}).get("generation") or gen3
rc, payload, _ = wf(["writer", "release", "--json"], {"generation": gen_after}, "sess-X3")
rec("R33 自身 pending 阻断释放", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")

# ---------------- R34：规则版本参与门禁 ----------------
record = json.load(open(record_path))
record["disposition"] = {"kind": "stop", "changes": [], "targets": [], "pending": []}
json.dump(record, open(record_path, "w"), ensure_ascii=False)
clean()


class GateCtx:
    root = F
    def rule_version(self):
        return "sha256:" + "new" * 10
    def key(self):
        return "sess-X5"


task_like = {"id": task3, "status": "in_progress", "phase": "finish",
             "plan": {"approval": {"at": AT}, "version": "sha256:" + "1" * 64,
                      "touch_paths": ["a33/**"], "acceptance": [], "verifications": [],
                      "complexity": "light"},
             "check": {"id": "chk", "result": "pass",
                       "anchor": {"check_anchor": "sha256:" + "0" * 64,
                                  "rule_version": "sha256:" + "old" * 10},
                       "commands": [], "acceptance_results": [], "internal_review": {"standard": {"conclusion": "pass"},
                                                                                    "requirement": {"conclusion": "pass"}}}}
satisfied, code, facts = wf_gates.verify_step(GateCtx(), task_like, "task.check-passed")
rec("R34 旧规则 Check 不满足门禁", "WF_CHECK_STALE",
    f"ok={satisfied} code={code}", satisfied is False and code == "WF_CHECK_STALE")

json.dump(results, open("/tmp/r31r34_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
