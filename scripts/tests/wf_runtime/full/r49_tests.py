#!/usr/bin/env python3
"""第十三轮 R49：链接把目标带进嵌套仓库时，读写两侧都要拒绝。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive

F = wfdrive.FIX
results = []
AT = "2026-11-04T10:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-U1"):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human (test)", "at": AT, "subject": subject, "object_digest": digest,
            "choice": choice, "reason": "R49 用例"}


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


def make_task(title, touch, sid="sess-U1"):
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


# 夹具：项目内的嵌套仓库 vendor/subrepo（用 gitfile 形式，便于提交）
os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
os.makedirs(os.path.join(F, "vendor/subrepo/data"), exist_ok=True)
open(os.path.join(F, "vendor/subrepo/.git"), "w").write("gitdir: /tmp/nowhere\n")
open(os.path.join(F, "vendor/subrepo/data/rule.md"), "w").write(RULE)
clean()
task1, gen1, dir1, d1 = make_task("R49 链接进嵌套仓库", ["pkg/**", ".wf/spec/**"], "sess-U1")
json.dump([dec("approve", "approve", d1)], open("/tmp/r49_a.json", "w"))
wf(["task-approve", "--task", task1, "--decision", "/tmp/r49_a.json", "--json"],
   {"generation": gen1, "complexity": "light", "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, "sess-U1")
open(os.path.join(F, "pkg/a.py"), "w").write("a = 1\n")
rc_s, start1, _ = wf(["task-start", "--task", task1, "--json"], {"generation": write_gen()}, "sess-U1")
rec("R49 准备：开工", "WF_OK", (start1 or {}).get("code"), rc_s == 0)

# 读取：文件链接指向嵌套仓库
link_file = os.path.join(F, ".wf/spec/nested-file.md")
if os.path.lexists(link_file):
    os.remove(link_file)
os.symlink(os.path.join(F, "vendor/subrepo/data/rule.md"), link_file)
rc, payload, _ = wf(["spec", "--file", ".wf/spec/nested-file.md", "--json"], {"generation": write_gen()}, "sess-U1")
rec("R49 文件链接进嵌套仓库被拒", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R49 未返回正文字段", "facts.content 缺失", (payload or {}).get("facts", {}).get("content") is None,
    (payload or {}).get("facts", {}).get("content") is None)
sidecar_dir = os.path.join(F, ".wf/.runtime/spec-reads")
hits = []
if os.path.isdir(sidecar_dir):
    for name in os.listdir(sidecar_dir):
        try:
            data = json.load(open(os.path.join(sidecar_dir, name), encoding="utf-8"))
        except Exception:
            continue
        if any(entry.get("path") == ".wf/spec/nested-file.md" for entry in data.get("specs") or []):
            hits.append(name)
rec("R49 未写完整读取侧车", "侧车无记录", hits, not hits)

# 写入：目录链接指向嵌套仓库
link_dir = os.path.join(F, ".wf/spec/nested-dir")
if os.path.lexists(link_dir):
    os.remove(link_dir)
os.symlink(os.path.join(F, "vendor/subrepo/data"), link_dir)
change = dfile("/tmp/r49_change.json",
               [{"operation": "add", "new_paths": [".wf/spec/nested-dir/new.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task1, "--changes", change, "--json"],
                    {"generation": write_gen()}, "sess-U1")
rec("R49 目录链接进嵌套仓库被拒", "WF_PATH_INVALID", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_PATH_INVALID")
rec("R49 拒绝时零写入", "嵌套仓库内 new.md 未生成",
    os.path.exists(os.path.join(F, "vendor/subrepo/data/new.md")),
    not os.path.exists(os.path.join(F, "vendor/subrepo/data/new.md")))

# 正例：普通 spec 仍可写
ok_change = dfile("/tmp/r49_ok.json",
                  [{"operation": "add", "new_paths": [".wf/spec/normal.md"], "content": RULE}])
rc, payload, _ = wf(["spec-update", "--task", task1, "--changes", ok_change, "--json"],
                    {"generation": write_gen()}, "sess-U1")
rec("R49 正例：普通 spec 可写", "WF_OK", (payload or {}).get("code"), rc == 0)
os.remove(link_file)
os.remove(link_dir)
shutil.rmtree(os.path.join(F, "vendor"))

json.dump(results, open("/tmp/r49_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
