#!/usr/bin/env python3
"""CP4（A1 前置核验 / A4 spec 模板 / A8 卸载偏离 / A19 spec 输出）回归用例。"""
import hashlib, json, os, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import spec as wf_spec

F = wfdrive.FIX
results = []
AT = "2026-11-03T12:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-R1", fixture=None):
    if fixture:
        os.environ["WF_FIX"] = fixture
        import importlib
        importlib.reload(wfdrive)
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "CP4 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path


def make_task(title, touch, sid):
    rc, payload, out = wf(["task-new", "--kind", "ordinary", "--title", title,
                           "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    task_id, gen = facts.get("task_id"), facts.get("generation")
    if not task_id:
        print("task-new failed:", out[:300]); raise SystemExit(1)
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
               dfile(f"/tmp/cp4_{task_id}_a.json", [dec("approve plan", "approve", digest)]), "--json"],
              {"generation": gen, "complexity": "light",
               "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)


NOTES = "/tmp/cp4_notes.json"
json.dump({"standard": {"conclusion": "pass", "basis": "单文件"},
           "requirement": {"conclusion": "pass", "basis": "验收覆盖"}}, open(NOTES, "w"))

# ---------------- T1 / A1：前置依赖核验 ----------------
clean()
task_a, gen_a, dir_a, d_a = make_task("CP4 前置-被放弃", ["src/pa.txt"], "sess-R1")
approve(task_a, d_a, gen_a, "sess-R1")
open(os.path.join(F, "src/pa.txt"), "w").write("pa\n")
wf(["task-start", "--task", task_a, "--json"], {"generation": gen_a}, "sess-R1")
stop = dfile("/tmp/cp4_abandon.json", [dec(f"stop {task_a}", "abandon", d_a),
                                       dec("src/pa.txt", "commit", d_a)])
disp = {"changes": [{"object": "src/pa.txt", "decision_ref": AT, "reason": "保留现状"}], "targets": [], "pending": []}
json.dump(disp, open("/tmp/cp4_disp.json", "w"), ensure_ascii=False)
rc, payload, _ = wf(["task-abandon", "--task", task_a, "--decision", stop,
                     "--disposition", "/tmp/cp4_disp.json", "--json"], {"generation": gen_a}, "sess-R1")
rec("A1 准备：被放弃的前置任务", "pass", (payload or {}).get("code"), rc == 0)
wf(["writer", "release", "--json"], {"generation": gen_a}, "sess-R1")
clean()

task_b, gen_b, dir_b, d_b = make_task("CP4 前置-依赖方", ["src/pb.txt"], "sess-R2")
approve(task_b, d_b, gen_b, "sess-R2")
# 开工前就带上未满足的前置
record = json.load(open(os.path.join(dir_b, "task.json")))
record["prerequisites"] = [task_a]
json.dump(record, open(os.path.join(dir_b, "task.json"), "w"), ensure_ascii=False)
rc, payload, _ = wf(["task-start", "--task", task_b, "--json"], {"generation": gen_b}, "sess-R2")
rec("A1 开工核前置（异常归档）", "WF_DEPENDENCY_UNMET", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_DEPENDENCY_UNMET")
# 去掉前置后开工，再在归档门禁上构造未满足前置
record = json.load(open(os.path.join(dir_b, "task.json")))
record["prerequisites"] = []
json.dump(record, open(os.path.join(dir_b, "task.json"), "w"), ensure_ascii=False)
open(os.path.join(F, "src/pb.txt"), "w").write("pb\n")
wf(["task-start", "--task", task_b, "--json"], {"generation": gen_b}, "sess-R2")
wf(["task-check", "--task", task_b, "--review-notes", NOTES, "--json"], {"generation": gen_b}, "sess-R2")
wf(["task-knowledge", "--task", task_b, "--decision", "no-update", "--json"], {"generation": gen_b}, "sess-R2")
record = json.load(open(os.path.join(dir_b, "task.json")))
record["prerequisites"] = [task_a]
json.dump(record, open(os.path.join(dir_b, "task.json"), "w"), ensure_ascii=False)
rc, payload, _ = wf(["archive", "--task", task_b, "--decision",
                     dfile("/tmp/cp4_b.json", [dec(f"finish {task_b}", "finish", d_b),
                                               dec("src/pb.txt", "commit", d_b)]), "--json"],
                    {"generation": gen_b}, "sess-R2")
rec("A1 归档门禁核前置", "WF_DEPENDENCY_UNMET", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_DEPENDENCY_UNMET")
wf(["task-pause", "--task", task_b, "--reason", "CP4 收尾", "--json"], {"generation": gen_b}, "sess-R2")
wf(["writer", "release", "--json"], {"generation": gen_b}, "sess-R2")

# ---------------- T2 / A4：spec 模板可被解析 ----------------
meta, problems = wf_spec.parse_frontmatter(os.path.join(
    "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/templates/spec/rule.md"))
errors, paths, path_problems = wf_spec.validate_metadata(meta)
rec("A4 模板 frontmatter 可解析", "problems 为空且 metadata 含 status/author",
    f"problems={problems} errors={errors} path_problems={path_problems}",
    not problems and not errors and meta.get("status") == "template" and meta.get("author") == "ai")

# ---------------- T3 / A19：spec 输出单一 ----------------
clean()
task_c, gen_c, dir_c, d_c = make_task("CP4 spec 输出", ["src/pc.txt"], "sess-R3")
approve(task_c, d_c, gen_c, "sess-R3")
open(os.path.join(F, "src/pc.txt"), "w").write("pc\n")
wf(["task-start", "--task", task_c, "--json"], {"generation": gen_c}, "sess-R3")
proc = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "spec",
                       "--file", ".wf/spec/index.md"], input=json.dumps({
                           "session": {"provider": "host",
                                       "identity": {"host_id": "dsh", "session_id": "sess-R3"},
                                       "instance_id": None,
                                       "activation": {"enabled": True, "start_source": "test", "enabled_at": AT}},
                           "inputs": {"generation": gen_c}}), capture_output=True, text=True)
rec("A19 非 JSON 模式只输出正文", "stdout 为文件正文，无结果头",
    f"header={'PASS' in proc.stdout} stderr_lines={len(proc.stderr.strip().splitlines())}",
    "PASS" not in proc.stdout and "spec 索引" in proc.stdout and proc.stderr.strip())
proc_json = subprocess.run(["/usr/bin/python3", os.path.join(F, ".wf/bin/wf.py"), "spec",
                            "--file", ".wf/spec/index.md", "--json"], input=json.dumps({
                                "session": {"provider": "host",
                                            "identity": {"host_id": "dsh", "session_id": "sess-R3"},
                                            "instance_id": None,
                                            "activation": {"enabled": True, "start_source": "test", "enabled_at": AT}},
                                "inputs": {"generation": gen_c}}), capture_output=True, text=True)
parsed = json.loads(proc_json.stdout.strip())
rec("A19 --json 输出结构", "tier=pass 且 facts.content 存在",
    f"{parsed.get('tier')} has_content={'content' in parsed.get('facts', {})}",
    parsed.get("tier") == "pass" and "content" in parsed.get("facts", {}))
wf(["task-pause", "--task", task_c, "--reason", "CP4 收尾", "--json"], {"generation": gen_c}, "sess-R3")
wf(["writer", "release", "--json"], {"generation": gen_c}, "sess-R3")

json.dump(results, open("/tmp/cp4_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", len(results), "cases;", sum(1 for r in results if r["pass"]), "passed")
