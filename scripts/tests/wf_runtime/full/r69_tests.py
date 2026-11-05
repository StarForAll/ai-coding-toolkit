#!/usr/bin/env python3
"""第三十三轮 R69：前像结构与整批预检、审查导入冲突、卸载内容重核。"""
import hashlib, json, os, re, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-09T09:00:00.000000Z"
REPORT = "<!-- wf-review-report:v1 -->\n```json\n{body}\n```\n"
NOTES = "/tmp/r69_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-V1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R69"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def proposal_digest(files):
    from wflib import records as _r

    return _r.plain_digest({"files": files})


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R69 前像",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-V1")
facts = (payload or {}).get("facts", {})
task_id, genv = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R69\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
for name in ("design.md", "implement.md"):
    open(os.path.join(directory, name), "w").write(f"# {name}\n\n内容。\n")
json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
          open("/tmp/r69_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r69_a.json", "--json"],
   {"generation": genv, "complexity": "complex"}, "sess-V1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, "sess-V1")
clean()
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)


def apply(name, files):
    body = {"files": files,
            "approval": {"source": "human", "at": AT, "subject": f"r69 {name}", "choice": "approve",
                         "object_digest": proposal_digest(files)}}
    path = f"/tmp/r69_{name}.json"
    json.dump(body, open(path, "w"), ensure_ascii=False)
    return wf(["baseline-apply", "--task", task_id, "--proposal", path, "--json"], {"generation": gen()}, "sess-V1")


# ---- 1. before: {} 不构成约束 ----
rc, payload, _ = apply("emptybefore", [{"path": ".wf/spec/rules/a.md", "content": "# a\n", "before": {}}])
rec("1 空对象前像被拒", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
rc, payload, _ = apply("existsfalse", [{"path": ".wf/spec/rules/b.md", "content": "# b\n",
                                        "before": {"exists": False}}])
rec("1b exists=false 前像可用", "WF_OK", (payload or {}).get("code"), rc == 0)

# ---- 2. 整批预检：后一件冲突时前一件不得已写 ----
open(os.path.join(F, ".wf/spec/rules/c.md"), "w").write("# 外来改动\n")
files = [{"path": ".wf/spec/rules/d.md", "content": "# d\n", "before": None},
         {"path": ".wf/spec/rules/c.md", "content": "# c\n", "before": "sha256:" + "9" * 64}]
rc, payload, _ = apply("batchconflict", files)
conflicts = ((payload or {}).get("facts") or {}).get("conflicts")
rec("2 整批冲突在写入前拦下", "WF_WORKSPACE_UNRESOLVED 且列冲突",
    f"{(payload or {}).get('code')} conflicts={bool(conflicts)}",
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED" and conflicts)
rec("2b 前一件未产生写入", "d.md 不存在", os.path.exists(os.path.join(F, ".wf/spec/rules/d.md")),
    not os.path.exists(os.path.join(F, ".wf/spec/rules/d.md")))

# ---- 3. 审查导入冲突与门禁引用 ----
rc, payload, _ = wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"],
                    {"generation": gen()}, "sess-V1")
check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
anchor = (check.get("anchor") or {}).get("check_anchor")


def launch():
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": "slot-a", "reviewer_cli": "codex"},
                         {"slot": "slot-b", "reviewer_cli": "pi"}],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    json.dump(request, open("/tmp/r69_launch.json", "w"), ensure_ascii=False)
    return wf(["review-launch", "--task", task_id, "--launch-request", "/tmp/r69_launch.json", "--json"],
              {"generation": gen()}, "sess-V1")


def report_body(slot, **over):
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": 1, "reviewer-id": slot,
            "source-cli": {"slot-a": "codex", "slot-b": "pi"}[slot], "review-time": AT, "review-focus": "x",
            "check-anchor": {"check_id": check.get("id"), "check_anchor": anchor},
            "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**"], "scope-exceptions": [],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in ("range", "acceptance", "contract", "regression", "testability")},
            "findings": [], "verdict": "pass"}
    body.update(over)
    return REPORT.format(body=json.dumps(body, ensure_ascii=False, indent=2))


rc, payload, _ = launch()
import glob

found = re.search(r'"(/tmp/wf-review/[^"]*/' + re.escape(task_id) + r'/round-1)"', json.dumps(payload or {}))
staging = found.group(1) if found else glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")[0]
for slot in ("slot-a", "slot-b"):
    os.makedirs(os.path.join(staging, slot), exist_ok=True)
    open(os.path.join(staging, slot, "report.md"), "w", encoding="utf-8").write(report_body(slot))
    wf(["review-import", "--task", task_id, "--round", "1", "--slot", slot,
        "--report", os.path.join(staging, slot, "report.md"), "--json"], {"generation": gen()}, "sess-V1")
rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                    {"generation": gen()}, "sess-V1")
rec("3 准备：审查 pass", "WF_OK", (payload or {}).get("code"), rc == 0)

open(os.path.join(staging, "slot-a", "report.md"), "w", encoding="utf-8").write(
    report_body("slot-a", findings=[{"id": "F9", "severity": "blocker", "summary": "新问题"}]))
rc, payload, _ = wf(["review-import", "--task", task_id, "--round", "1", "--slot", "slot-a",
                     "--report", os.path.join(staging, "slot-a", "report.md"), "--json"],
                    {"generation": gen()}, "sess-V1")
rec("3b 同槽位不同摘要 → 导入冲突", "WF_REVIEW_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_REVIEW_INVALID")
from wflib import gates as wf_gates, cli as wf_cli
json.dump(wfdrive.envelope({"generation": gen()}, "sess-V1"), open("/tmp/r69_env.json", "w"), ensure_ascii=False)
ctx = wf_cli.Context(F, ["--envelope", "/tmp/r69_env.json"])
record_now = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
satisfied, code, facts = wf_gates.verify_step(ctx, record_now, "task.review-passed")
rec("3c 旧 pass 引用的就是当前导入 → 门禁通过", "满足", f"{satisfied} {code}", satisfied is True)

# 让旧结论引用的摘要与当前导入不一致（模拟被替换）
record_path = os.path.join(directory, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
record["reviews"]["result"]["imported"][0]["report_digest"] = "sha256:" + "0" * 64
json.dump(record, open(record_path, "w", encoding="utf-8"), ensure_ascii=False)
record_now = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
satisfied, code, facts = wf_gates.verify_step(ctx, record_now, "task.review-passed")
rec("3d 结论引用的报告已变 → 门禁不通过", "WF_REVIEW_INVALID",
    f"{satisfied} {code}", satisfied is False and code == "WF_REVIEW_INVALID")

json.dump(results, open("/tmp/r69_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))

# ---- 4. 卸载：确认期间内容变化必须使预览失效 ----
import shutil

UN = "/tmp/wf-fixtures/r69-uninstall"
shutil.rmtree(UN, ignore_errors=True)
os.makedirs(UN)
subprocess.run(["git", "init", "-q"], cwd=UN, capture_output=True)
subprocess.run(["/softwares/python/bin/python3",
                "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/install.py",
                "--target", UN, "--release-ref", "refs/tags/wf-v0.1.0",
                "--source", "/tmp/wf-fixtures/release-repo",
                "--platform", "dsh",
                "--confirm", ],
               capture_output=True, text=True)


def run_uninstall(mutator=None):
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(UN, ".wf/bin/uninstall.py"),
                             "--project", UN, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入令牌确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"令牌：([0-9a-f]{32})", buffer)
    if mutator:
        mutator()
    proc.stdin.write((token.group(1) if token else "0" * 32) + "\n")
    proc.stdin.flush()
    rest = proc.stdout.read()
    proc.wait(timeout=120)
    return token, proc.returncode, buffer + rest


target = os.path.join(UN, ".wf/templates/spec/index.md")
if not os.path.exists(target):
    target = None
    for base, _dirs, files in os.walk(os.path.join(UN, ".wf")):
        for name in files:
            if name == "index.md":
                target = os.path.join(base, name)
                break
        if target:
            break


def edit_asset():
    with open(target, "a", encoding="utf-8") as handle:
        handle.write("\n本地新增一行\n")


token, rc_u, out_u = run_uninstall(edit_asset)
survived = os.path.exists(target)
rec("4 确认期间资产被改 → 预览失效且不删除", "WF_PREVIEW_STALE 且文件仍在",
    f"rc={rc_u} survived={survived}",
    "WF_PREVIEW_STALE" in out_u and survived)

json.dump(results, open("/tmp/r69_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
