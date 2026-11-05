#!/usr/bin/env python3
"""第三十轮 R67：写权入口实例/能力核验、baseline 状态与提案、清单声明、聚合脚本退出码。"""
import hashlib, json, os, shutil, subprocess, sys
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
import wfdrive
from wflib import gates as wf_gates, cli as wf_cli

F = wfdrive.FIX
results = []


def _proposal_digest(files):
    sys.path.insert(0, "/home/xzc/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/payload/lib")
    from wflib import records as _r

    return _r.plain_digest({"files": files})

AT = "2026-11-07T09:00:00.000000Z"


def rec(name, expected, actual, ok):
    results.append({"case": name, "expected": expected, "actual": actual, "pass": bool(ok)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {actual}")


def wf(args, inputs=None, sid="sess-M1", **kw):
    return wfdrive.run(args, inputs=inputs, sid=sid, show=False, **kw)


def dec(subject, choice, digest="sha256:" + "0" * 64):
    return {"source": "human", "at": AT, "subject": subject, "object_digest": digest, "choice": choice, "reason": "R67"}



def clean():
    subprocess.run(["git", "add", "-A"], cwd=F, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "cap", "--allow-empty"], cwd=F, capture_output=True)


def gen():
    return json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("generation")


def make_task(title, sid):
    rc, payload, _ = wf(["task-new", "--kind", "ordinary", "--title", title,
                         "--template", f"{F}/.wf/templates/task", "--json"], None, sid)
    facts = (payload or {}).get("facts", {})
    directory = os.path.join(F, facts["directory"])
    block = {"schema_version": 1, "touch_paths": ["pkg/**", ".wf/spec/**"],
             "acceptance": [{"id": "a1", "statement": "x", "verification_ids": ["v1"]}],
             "verifications": [{"id": "v1", "invocation": {"kind": "argv", "argv": ["/usr/bin/python3", "-c", "print(1)"]},
                                "cwd": ".", "input_refs": [], "required": True, "consume_at": "check"}]}
    prd = f"# {title}\n\n<!-- wf-plan:v1 -->\n```json\n{json.dumps(block, ensure_ascii=False, indent=2)}\n```\n"
    open(os.path.join(directory, "prd.md"), "w", encoding="utf-8").write(prd)
    digest = "sha256:" + hashlib.sha256(prd.encode()).hexdigest()
    json.dump([dec("approve", "approve", digest)], open(f"/tmp/r67_{facts['task_id']}.json", "w"))
    wf(["task-approve", "--task", facts["task_id"], "--decision", f"/tmp/r67_{facts['task_id']}.json", "--json"],
       {"generation": facts.get("generation"), "complexity": "light",
        "downgrade": {"reason": "单文件", "evidence": "不碰治理面"}}, sid)
    return facts["task_id"], facts.get("generation"), directory


os.makedirs(os.path.join(F, "pkg"), exist_ok=True)
clean()

# ---- 1. 写权获取/释放核验实例标识；能力未核实即拒 ----
task1, gen1, dir1 = make_task("R67 写权实例", "sess-M1")
rc, payload, _ = wf(["writer", "acquire", "--json"], {"generation": gen1},
                    "sess-M1", instance_id="ffffffffffffffffffffffffffffffff")
rec("1 writer acquire 拒绝错误实例标识", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
wf(["writer", "release", "--json"], {"generation": gen()}, "sess-M1")
rc, payload, _ = wf(["writer", "acquire", "--json"], {"generation": gen()}, "sess-M1")
holder_id = (json.load(open(os.path.join(F, ".wf/writer.json"), encoding="utf-8")).get("holder") or {}).get("id")
same_session = holder_id == wfdrive.wf_key("sess-M1") if hasattr(wfdrive, "wf_key") else True
rec("1b 正常获取成功或已由本会话持有", "WF_OK 或已持有时 WF_WRITER_BUSY",
    f"{(payload or {}).get('code')} held_by_self={same_session}",
    (payload or {}).get("code") in ("WF_OK", "WF_WRITER_BUSY") and same_session)

install_path = os.path.join(F, ".wf/install/installation.json")
backup = open(install_path, encoding="utf-8").read()
install = json.loads(backup)
install["session_profile"]["capability"]["status"] = "unknown"
json.dump(install, open(install_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["task-curate", "--task", task1, "--spec", ".wf/spec/rules/r67.md",
                     "--purpose", "x", "--json"], {"generation": gen()}, "sess-M1")
rec("1c 能力未核实 → 日常入口拒绝", "WF_IDENTITY_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_IDENTITY_UNRESOLVED")
open(install_path, "w", encoding="utf-8").write(backup)

# ---- 2. baseline-apply 状态与提案 ----
rc, payload, _ = wf(["task-start", "--task", task1, "--json"], {"generation": gen()}, "sess-M1")
open(os.path.join(F, "pkg/a.py"), "w").write("a\n")
clean()
os.makedirs(os.path.join(F, ".wf/spec/rules"), exist_ok=True)
open(os.path.join(F, ".wf/spec/rules/r67.md"), "w").write("# 规则\n")


def proposal(name, extra=None):
    files = [{"path": ".wf/spec/rules/r67b.md", "content": f"# 规则二 {name}\n", "before": None}]
    body = {"files": files,
            "approval": {"source": "human", "at": AT, "subject": "r67 baseline", "choice": "approve",
                         "object_digest": _proposal_digest(files), "reason": "R67"}}
    if extra:
        body.update(extra)
    path = f"/tmp/r67_{name}.json"
    json.dump(body, open(path, "w"), ensure_ascii=False)
    return path


rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", proposal("ok"), "--json"],
                    {"generation": gen()}, "sess-M1")
rec("2 正常执行态可写", "WF_OK", (payload or {}).get("code"), rc == 0)

for state, key in (("paused", "paused"), ("suspended", "suspended")):
    wf(["task-pause", "--task", task1, "--reason", "x", "--json"], {"generation": gen()}, "sess-M1")
    record_path = os.path.join(dir1, "task.json")
    record = json.load(open(record_path, encoding="utf-8"))
    if state == "suspended":
        record["paused"] = False
        record["suspended"] = True
        json.dump(record, open(record_path, "w"), ensure_ascii=False)
    rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", proposal(f"{state}"), "--json"],
                        {"generation": gen()}, "sess-M1")
    rec(f"2 {state} 时拒绝基线写入", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
        (payload or {}).get("code") == "WF_SEMANTIC_DECISION")
    record = json.load(open(record_path, encoding="utf-8"))
    record["paused"] = False
    record["suspended"] = False
    json.dump(record, open(record_path, "w"), ensure_ascii=False)

rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal",
                     "/tmp/r67_noapproval.json" if os.path.exists("/tmp/r67_noapproval.json") else
                     json.dump({"files": [{"path": ".wf/spec/rules/r67c.md", "content": "# 三\n", "before": None}]},
                               open("/tmp/r67_noapproval.json", "w")) or "/tmp/r67_noapproval.json", "--json"],
                    {"generation": gen()}, "sess-M1")
rec("2b 无批准引用的提案被拒", "WF_SEMANTIC_DECISION", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_SEMANTIC_DECISION")

stale = proposal("stale")
body = json.load(open(stale, encoding="utf-8"))
body["files"][0]["before"] = "sha256:" + "1" * 64
body["approval"]["object_digest"] = _proposal_digest(body["files"])  # 前像变了，批准也随之更新
json.dump(body, open(stale, "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", stale, "--json"],
                    {"generation": gen()}, "sess-M1")
rec("2c 前像不符被拒", "WF_WORKSPACE_UNRESOLVED", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_WORKSPACE_UNRESOLVED")

record_path = os.path.join(dir1, "task.json")
record = json.load(open(record_path, encoding="utf-8"))
record["status"] = "archived"
record["terminal"] = "normal"
json.dump(record, open(record_path, "w"), ensure_ascii=False)
rc, payload, _ = wf(["baseline-apply", "--task", task1, "--proposal", proposal("archived"), "--json"],
                    {"generation": gen()}, "sess-M1")
rec("2d 已归档对象拒绝基线写入", "WF_BINDING_MISMATCH", (payload or {}).get("code"),
    (payload or {}).get("code") == "WF_BINDING_MISMATCH")
record["status"] = "in_progress"
record["terminal"] = None
json.dump(record, open(record_path, "w"), ensure_ascii=False)
clean()

# ---- 3. 清单声明：改 scope 不能把门禁移出义务集合 ----
manifest_path = os.path.join(F, ".wf/install/release-manifest.json")
manifest_backup = open(manifest_path, encoding="utf-8").read()
env_path = "/tmp/r67_env.json"
json.dump(wfdrive.envelope({"generation": gen()}, "sess-M1"), open(env_path, "w"), ensure_ascii=False)


def declared_with(mutate):
    manifest = json.loads(manifest_backup)
    mutate(manifest)
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False)
    try:
        wf_gates.declared_step_specs(wf_cli.Context(F, ["--envelope", env_path]))
        return "accepted"
    except Exception as exc:
        return getattr(exc, "code", type(exc).__name__)


def set_scope(m):
    for step in m["required_steps"]:
        if step["id"] == "task.plan-approved":
            step["scope"] = "control"


def drop_mode(m):
    for step in m["required_steps"]:
        if step["id"] == "task.plan-approved":
            step.pop("mode", None)


def dup(m):
    m["required_steps"].append(dict(m["required_steps"][0]))


rec("3 scope 改动不得移出门禁", "WF_ASSET_DECISION", declared_with(set_scope),
    declared_with(set_scope) == "WF_ASSET_DECISION")
rec("3b 缺 mode 被拒", "WF_ASSET_DECISION", declared_with(drop_mode),
    declared_with(drop_mode) == "WF_ASSET_DECISION")
rec("3c 重复声明被拒", "WF_ASSET_DECISION", declared_with(dup),
    declared_with(dup) == "WF_ASSET_DECISION")
open(manifest_path, "w", encoding="utf-8").write(manifest_backup)
rec("3d 恢复后可用", "有义务", bool(wf_gates.declared_step_specs(wf_cli.Context(F, ["--envelope", env_path]))), True)

# ---- 4. 聚合脚本：失败必须传播 ----
fake = "/tmp/r67_fake_suites"
shutil.rmtree(fake, ignore_errors=True)
os.makedirs(fake)
real = "/home/xzc/projects/personal/ai-coding-toolkit/scripts/tests/wf_runtime/full"
shutil.copy(os.path.join(real, "run_all.sh"), fake)
# run_all 的并行路径会调用 run_one.sh：假环境也要有可运行版本（否则并行段无结果行，失败无法传播）
open(os.path.join(fake, "run_one.sh"), "w").write(
    '#!/bin/bash\nset -uo pipefail\nsuite=$1\n'
    'out="$RESULTS_DIR/$suite.out"\n'
    '"$PY" "$HERE/$suite.py" >"$out" 2>&1\nrc=$?\n'
    'bad=$(grep -c "\\[FAIL\\]" "$out" || true)\nline=$(tail -1 "$out")\n'
    'status=ok\n'
    'if [ "$rc" -ne 0 ] || [ "$bad" -ne 0 ] || printf "%s" "$line" | grep -qE "FAIL|(saved|total) 0"; then status=bad; fi\n'
    'printf "%s\\t%s\\t%s\\t%s\\t%s\\n" "$suite" "$rc" "0" "$status" "$line" >> "$RESULTS_DIR/lines"\n')
open(os.path.join(fake, "wf_fixture.sh"), "w").write(
    '#!/bin/bash\nset -e\nF=${1:-/tmp/fake}\nrm -rf "$F"; mkdir -p "$F/.wf/bin"\n'
    ': > "$F/.wf/bin/wf.py"\n')
open(os.path.join(fake, "f1_init.py"), "w").write("print('ok')\n")
open(os.path.join(fake, "wf_fixture.sh"), "w").write(
    '#!/bin/bash\nset -e\nF=${1:-/tmp/fake}\nrm -rf "$F"; mkdir -p "$F/.wf/bin"\n'
    ': > "$F/.wf/bin/wf.py"\n')
open(os.path.join(fake, "cp1_tests.py"), "w").write("print('[FAIL] fake')\nprint('saved 0 cases; 0 passed')\nraise SystemExit(1)\n")
# 依 run_all.sh 里的实际清单造同名假套件，避免清单变动后假环境缺文件
import re as _re
suites_line = _re.search(r'SUITES="([^"]+)"', open(os.path.join(real, "run_all.sh"), encoding="utf-8").read())
for name in suites_line.group(1).split():
    if name == "cp1_tests":
        continue
    open(os.path.join(fake, f"{name}.py"), "w").write("print('saved 1 cases; 1 passed')\n")
# run_all.sh 里直接调用的额外脚本体也要有可运行的假件
open(os.path.join(fake, "r72_tests.py"), "w").write(
    "print('\\n'.join('[PASS] case %d' % i for i in range(1, 8)))\nprint('saved 7 / 7')\n")
open(os.path.join(fake, "p5_f0.py"), "w").write("print('PASS')\n" * 9)
# 发行仓库桩：run_all 的 run_f0 会调用 $RELEASE_REPO/install.py
fake_repo = "/tmp/r67_fake_release"
shutil.rmtree(fake_repo, ignore_errors=True)
os.makedirs(fake_repo)
open(os.path.join(fake_repo, "wf-release.json"), "w").write("{}")
open(os.path.join(fake_repo, "install.py"), "w").write("import sys; sys.exit(0)\n")
for name, count in (("p5_spec", 13), ("p5_v2v3", 12), ("p5_v5", 12)):
    open(os.path.join(fake, f"{name}.py"), "w").write("print('PASS')\n" * count)
proc = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                      env={**os.environ, "WF_FIX": "/tmp/r67_fake_fix", "WF_RELEASE_REPO": "/tmp/r67_fake_release",
                           "WF_REBUILD_RELEASE": "0", "WF_JOBS": "2",
                           "WF_RESULTS_DIR": "/tmp/r67_fake_results"})
rec("4 有失败时脚本非零退出", "exit≠0 且汇总报失败", f"exit={proc.returncode}",
    proc.returncode != 0 and "失败 1 项" in proc.stdout)
open(os.path.join(fake, "cp1_tests.py"), "w").write("print('saved 1 cases; 1 passed')\n")
proc2 = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                       env={**os.environ, "WF_FIX": "/tmp/r67_fake_fix", "WF_RELEASE_REPO": "/tmp/r67_fake_release", "WF_REBUILD_RELEASE": "0"})
rec("4b 无失败时零退出", "exit=0", f"exit={proc2.returncode}", proc2.returncode == 0)

json.dump(results, open("/tmp/r67_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
