#!/usr/bin/env python3
"""第十二轮 R47–R48：spec 读取/写入的真实落点与嵌套仓库边界。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-04T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-T1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R47/R48 用例"}


def dfile(path, items):
    json.dump(items, open(path, "w"), ensure_ascii=False, indent=2)
    return path



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "test cleanup", "--allow-empty"], cwd=F, capture_output=True)


def write_gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


RULE = '''---
schema_version: 1
paths: ["pkg/**"]
status: "active"
verified_at: "2026-11-04"
author: "ai"
counterexample: "未覆盖"
---

# 规则

正文。
'''


def make_task(title, touch, sid="sess-T1"):
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


# ---------------- R47：读取侧不跟随越界链接 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task1, gen1, dir1, d1 = make_task("R47 读取边界", ["pkg/**", ".wf/spec/**"], "sess-T1")
json.dump([dec("approve", "approve", d1)], open("/tmp/r47_a.json", "w"))
wf(["task-approve", "--task", task1, "--decision", "/tmp/r47_a.json", "--json"],
   {"generation": gen1, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-T1")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc_s, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-T1")
rec("R47 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)
outside = "/tmp/wf-outside-spec.md"
open(outside, "w").write("# 项目外内容\n")
os.makedirs(os.path.join(F, ".wf/spec"), exist_ok=True)
link = os.path.join(F, ".wf/spec/link.md")
if os.path.islink(link) or os.path.exists(link):
    os.remove(link)
os.symlink(outside, link)
rc, payload, _ = wf(["spec", "--file", ".wf/spec/link.md", "--json"], {"generation": write_gen()}, "sess-T1")
rec("R47 越界链接被拒绝", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
sidecar_dir = os.path.join(F, ".wf/.runtime/spec-reads")
sidecar_hit = []
if os.path.isdir(sidecar_dir):
    for name in os.listdir(sidecar_dir):
        try:
            data = json.load(open(os.path.join(sidecar_dir, name), encoding="utf-8"))
        except Exception:
            continue
        if any(".wf/spec/link.md" == entry.get("path") for entry in data.get("specs") or []):
            sidecar_hit.append(name)
rec("R47 未写入完整读取侧车", "侧车无该路径记录", sidecar_hit, not sidecar_hit)
rec("R47 外部正文未进入结果", "正文缺失", (payload or {}).get("facts", {}).get("content") is None,
    (payload or {}).get("facts", {}).get("content") is None)
os.remove(link)
wf(["task-pause", "--task", task1, "--reason", "R47 收尾", "--json"], {"generation": write_gen()}, "sess-T1")
wf(["writer", "release", "--json"], {"generation": write_gen()}, "sess-T1")

# ---------------- R48：写入侧拒绝嵌套仓库 ----------------
clean()
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
task2, gen2, dir2, d2 = make_task("R48 嵌套仓库", ["pkg/**", ".wf/spec/**"], "sess-T2")
json.dump([dec("approve", "approve", d2)], open("/tmp/r48_a.json", "w"))
wf(["task-approve", "--task", task2, "--decision", "/tmp/r48_a.json", "--json"],
   {"generation": gen2, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-T2")
open(os.path.join(F, "pkg/b.py"), "w").write("b = 1\n")
rc_s2, start2, _ = wf(["task-start", "--task", task2, "--json"], {"generation": write_gen()}, "sess-T2")
rec("R48 准备：开工", "WF_OK", (start2 or {}).get("code"), rc_s2 == 0)
nested = os.path.join(F, ".wf/spec/child")
os.makedirs(os.path.join(nested, ".git"), exist_ok=True)
change = dfile("/tmp/r48_change.json",
               [{"operation": "add", "new_paths": [".wf/spec/child/new.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task2, "--changes", change, "--json"],
                    {"generation": write_gen()}, "sess-T2")
rec("R48 嵌套仓库目标被拒", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R48 拒绝时零写入", "new.md 未生成",
    os.path.exists(os.path.join(nested, "new.md")),
    not os.path.exists(os.path.join(nested, "new.md")))
rec("R48 报告嵌套根位置", "facts 含 nested repository root",
    json.dumps((payload or {}).get("facts"), ensure_ascii=False)[:140],
    "nested repository root" in json.dumps((payload or {}).get("facts"), ensure_ascii=False))
shutil.rmtree(nested)

json.dump(results, open("/tmp/r47r48_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
