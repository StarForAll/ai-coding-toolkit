#!/usr/bin/env python3
"""第三十四轮 R70：卸载既有偏离与确认期变化之分、真实审查失败必须落盘。"""
import hashlib, json, os, re, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []

EXTERNAL_ACK = "/tmp/wf_external_ack.json"
if not os.path.exists(EXTERNAL_ACK):
    json.dump([{"source": "human (test)", "at": "2026-11-04T00:00:00.000000Z",
                "subject": "external-changes", "object_digest": "sha256:" + "0" * 64,
                "choice": "已核对无影响", "reason": "夹具提交均为本任务改动"}],
              open(EXTERNAL_ACK, "w"), ensure_ascii=False)
AT = "2026-11-10T09:00:00.000000Z"
REPORT = ("<!-- wf-review-agent:v1 status=done -->\n"
          "<!-- wf-review-report:v1 -->\n```json\n{body}\n```\n")
NOTES = "/tmp/r70_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "b"},
           "requirement": {"conclusion": "pass", "basis": "b"}}, open(NOTES, "w"))


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-W1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice,
            "reason": "R70"}


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


# ---------- 1. 卸载：既有偏离不被误判，确认期变化才失效 ----------
def _release_source():
    """发行目录：优先 WF_RELEASE_REPO（harness 提供），否则用仓库内已构建的发行树。

    两处都可能不存在（未构建/未挂载）——那就明确报出来，而不是让卸载步骤连锁失败。
    """
    candidates = [os.environ.get("WF_RELEASE_REPO"), "/tmp/wf-fixtures/release-repo",
                  "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf-release"]
    for path in candidates:
        # install.py 要求"已检出的发行目录"：既要有清单，也要有 wf-release/ 实体assets
        if (path and os.path.exists(os.path.join(path, "wf-release.json"))
                and os.path.isdir(os.path.join(path, "wf-release"))):
            return path
    raise SystemExit("r70: 需要有效的发行目录（WF_RELEASE_REPO，含 wf-release.json 与 wf-release/ 实体）；"
                     "单独运行请先 bash scripts/build-wf-release.py 并用 run_all.sh 提供该路径")


def make_project(name):
    target = f"/tmp/wf-fixtures/r70-{name}"
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)
    subprocess.run(["git", "init", "-q"], cwd=target, capture_output=True)
    proc = subprocess.run(["/softwares/python/bin/python3",
                           "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/wf/payload/install.py",
                           "--target", target, "--release-ref", "refs/tags/wf-v0.1.0",
                           "--source", _release_source(),
                           "--platform", "dsh",
                           "--confirm", ],
                          capture_output=True, text=True)
    if not os.path.exists(os.path.join(target, ".wf/bin/uninstall.py")):
        # 安装没落地时后面全是连锁失败：把安装输出带出来，别让它静默
        print(f"make_project({name}) 安装未落地 rc={proc.returncode}:",
              ((proc.stdout or "") + (proc.stderr or ""))[-300:].replace("\n", " | "))
    return target


def run_uninstall(target, mutator=None):
    proc = subprocess.Popen(["/usr/bin/python3", os.path.join(target, ".wf/bin/uninstall.py"),
                             "--project", target, "--apply"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    buffer = ""
    while "请输入预览指纹确认" not in buffer:
        char = proc.stdout.read(1)
        if not char:
            break
        buffer += char
    token = re.search(r"预览指纹：([0-9a-f]{8})", buffer)
    # 进程可能在提示前就退出（前置不成立/已无内容可卸）：此时写管道会 BrokenPipe 掩盖真实原因。
    # 直接把它已输出的内容带回去，由断言显示事实。
    if token is None and proc.poll() is not None:
        rest = proc.stdout.read()
        proc.wait(timeout=120)
        return proc.returncode, buffer + rest
    if mutator:
        mutator()
    try:
        proc.stdin.write((token.group(1) if token else "0" * 8) + "\n")
        proc.stdin.flush()
    except BrokenPipeError:
        pass
    rest = proc.stdout.read()
    proc.wait(timeout=120)
    return proc.returncode, buffer + rest


def first_asset(target):
    for base, _dirs, files in os.walk(os.path.join(target, ".wf")):
        for name in sorted(files):
            return os.path.join(base, name)
    return None


# ① 干净资产：卸载成功
clean_target = make_project("clean")
rc, out = run_uninstall(clean_target)
if rc != 0:
    print("① 卸载输出:", out[-400:].replace("\n", " | "))
rec("1 干净资产可卸载", "WF_OK", f"rc={rc}", rc == 0 and "WF_OK" in out)

# ② 预览前已有本地偏离、确认期间未变：应成功（保留偏离）
deviated = make_project("deviated")
asset = first_asset(deviated)
with open(asset, "a", encoding="utf-8") as handle:
    handle.write("\n本地偏离行\n")
rc, out = run_uninstall(deviated)
survived = os.path.exists(asset)
rec("1b 既有偏离不被误判为预览失效", "卸载成功且偏离文件保留",
    f"rc={rc} survived={survived}",
    rc == 0 and "WF_OK" in out and survived)

# ③ 确认期间才改动：应拒绝
drifted = make_project("drifted")
asset2 = first_asset(drifted)


def mutate():
    with open(asset2, "a", encoding="utf-8") as handle:
        handle.write("\n确认期新增\n")


rc, out = run_uninstall(drifted, mutate)
rec("1c 确认期间改动 → 预览失效且保留", "WF_PREVIEW_STALE 且文件仍在",
    f"rc={rc} survived={os.path.exists(asset2)}",
    "WF_PREVIEW_STALE" in out and os.path.exists(asset2))

# ---------- 2. 真实审查失败必须落盘 ----------
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", "R70 审查失败",
                     "--template", f"{F}/.wf/templates/task", "--json"], None, "sess-W1")
facts = (payload or {}).get("facts", {})
task_id, genv = facts.get("task_id"), facts.get("generation")
directory = os.path.join(F, facts["directory"])
block = {"schema_version": 1, "touch_paths": ["pkg/**"],
         "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
         "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                            "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
prd = f"# R70\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
for name in ("design.md", "implement.md"):
    open(os.path.join(directory, name), "w").write(f"# {name}\n\n内容。\n")
json.dump([dec("approve", "approve", "sha256:" + hashlib.sha256(prd.encode()).hexdigest())],
          open("/tmp/r70_a.json", "w"))
wf(["task-approve", "--task", task_id, "--decision", "/tmp/r70_a.json", "--json"],
   {"generation": genv, "complexity": "complex"}, "sess-W1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
wf(["task-start", "--task", task_id, "--json"], {"generation": gen()}, "sess-W1")


def launch(round_no):
    request = {"implementation_clis": ["dsh"],
               "slots": [{"slot": "slot-a", "reviewer_cli": "codex"},
                         {"slot": "slot-b", "reviewer_cli": "pi"}],
               "export_decision": dec("export", "approve"), "submitted_scope": {"diff": "git diff", "requirement": ["prd"], "test_results": ["v1"]},
               "readable_scope": {"paths": ["pkg/**"]}, "exclusions": []}
    path = f"/tmp/r70_launch_{round_no}.json"
    json.dump(request, open(path, "w"), ensure_ascii=False)
    # K6 第 3 类：外发以"确认入库"为准（请求里的 export_decision 只是声明）
    export_path = f"/tmp/r70_export_{round_no}.json"
    json.dump([{"choice": "export", "task": task_id, "materials": ["diff", "requirement", "test_results"], "paths": ["pkg/**"], "quote": "人同意把材料外发给审查 CLI",
                "by": "human:test", "at": "2026-11-10T00:00:00.000000Z",
                "source": "user-declared"}],
              open(export_path, "w"), ensure_ascii=False)
    wf(["authorize", "record", "--task", task_id, "--file", export_path, "--json"],
       {"generation": gen()}, "sess-W1")
    return wf(["review-launch", "--task", task_id, "--launch-request", path, "--json"],
              {"generation": gen()}, "sess-W1")


def import_report(staging, slot, round_no, check, anchor, **over):
    body = {"protocol": "wf-review-v1", "task-id": task_id, "round": round_no, "reviewer-id": slot,
            "source-cli": {"slot-a": "codex", "slot-b": "pi"}[slot], "review-time": AT, "review-focus": "x",
            "check-anchor": {"check_id": (check or {}).get("id"), "check_anchor": anchor},
            "read-scope": ["pkg/**"], "excluded-scope": ["node_modules/**", ".env", "*.pem", ".codex/**", "../**", ".wf/tasks/**"], "scope-exceptions": [],
            "axes": {axis: {"conclusion": "pass", "basis": "b"} for axis in ("range", "acceptance", "contract", "regression", "testability")},
            "findings": [], "verdict": "pass"}
    body.update(over)
    directory_slot = os.path.join(staging, slot)
    os.makedirs(directory_slot, exist_ok=True)
    path = os.path.join(directory_slot, "report.md")
    open(path, "w", encoding="utf-8").write(REPORT.format(body=json.dumps(body, ensure_ascii=False, indent=2)))
    rc, payload, _ = wf(["review-import", "--task", task_id, "--round", str(round_no), "--slot", slot,
                         "--report", path, "--json"], {"generation": gen()}, "sess-W1")
    if rc != 0:
        print("   import failed:", slot, (payload or {}).get("code"),
              json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:160])
    return rc, payload, None


def current_anchor():
    check = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8")).get("check") or {}
    return check, (check.get("anchor") or {}).get("check_anchor")


wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": gen()}, "sess-W1")
check, anchor = current_anchor()
rc, payload, _ = launch(1)
import glob as _glob

found = _glob.glob(f"/tmp/wf-review/*/{task_id}/round-1")
staging1 = found[0] if found else f"/tmp/wf-review/unknown/{task_id}/round-1"
for slot in ("slot-a", "slot-b"):
    import_report(staging1, slot, 1, check, anchor,
                  # v42 B1：blocking finding 必须落在具体轴上，否则"输入不成立"而非"判定 fail"
                  **({"findings": [{"id": "F1", "severity": "blocker", "axis": "acceptance",
                                    "assertion_ref": "a1", "summary": "真失败"}], "verdict": "fail"}
                     if slot == "slot-a" else {}))
rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "1", "--json"],
                    {"generation": gen()}, "sess-W1")
record = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
first = (record.get("reviews") or {}).get("result") or {}
outcome = ((record.get("reviews") or {}).get("attempts") or [{}])[0].get("outcome")
if (payload or {}).get("code") != "WF_OK":
    print("② decide 原文:", json.dumps(payload or {}, ensure_ascii=False)[:400])
rec("2 首轮真失败被记录", "result.verdict=fail 且 outcome=fail",
    f"code={(payload or {}).get('code')} verdict={first.get('verdict')} outcome={outcome}",
    first.get("verdict") == "fail" and outcome == "fail")

# 修复后次轮通过
open(os.path.join(F, "pkg/b.py"), "w").write("b\n")
wf(["task-check", "--task", task_id, "--review-notes", NOTES,
                    "--decision", EXTERNAL_ACK, "--json"], {"generation": gen()}, "sess-W1")
check, anchor = current_anchor()
rc, payload, _ = launch(2)
found = _glob.glob(f"/tmp/wf-review/*/{task_id}/round-2")
staging2 = found[0] if found else f"/tmp/wf-review/unknown/{task_id}/round-2"
for slot in ("slot-a", "slot-b"):
    import_report(staging2, slot, 2, check, anchor)
rc, payload, _ = wf(["review-decide", "--task", task_id, "--round", "2", "--json"],
                    {"generation": gen()}, "sess-W1")
record = json.load(open(os.path.join(directory, "task.json"), encoding="utf-8"))
reviews = record.get("reviews") or {}
outcome = (reviews.get("attempts") or [{}])[0].get("outcome")
from wflib import gates as wf_gates

triggers = [t["kind"] for t in wf_gates.retrospective_triggers(F, record, 3)]
rec("2b 次轮通过仍保留历史失败", "outcome=fail 且触发含 review_fail",
    f"verdict={(reviews.get('result') or {}).get('verdict')} outcome={outcome} triggers={triggers}",
    (reviews.get("result") or {}).get("verdict") == "pass" and outcome == "fail" and "review_fail" in triggers)

json.dump(results, open("/tmp/r70_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
