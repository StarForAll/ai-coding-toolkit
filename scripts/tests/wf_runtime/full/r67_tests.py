#!/usr/bin/env python3
"""第三十轮 R67：写权入口实例/能力核验、baseline 状态与提案、清单声明（产品侧断言）。

运行器假树断言已迁到运行器契约入口（test_run_all_contract + fake_runner_contract）。
"""
import hashlib, json, os, subprocess, sys
import wfdrive
sys.path.insert(0, wfdrive.LIB)
from wflib import gates as wf_gates, cli as wf_cli

F = wfdrive.FIX
results = []


def _proposal_digest(files):
    sys.path.insert(0, wfdrive.LIB)
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
    json.dump([dec("approve", "approve", digest)], open(wfdrive.temp(f"r67_{facts['task_id']}.json"), "w"))
    wf(["task-approve", "--task", facts["task_id"], "--decision", wfdrive.temp(f"r67_{facts['task_id']}.json"), "--json"],
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
install["platforms"] = []   # 等价场景：本项目没有为任何平台安装 → 日常入口拒绝
json.dump(install, open(install_path, "w", encoding="utf-8"), ensure_ascii=False)
rc, payload, _ = wf(["task-curate", "--task", task1, "--spec", ".wf/spec/rules/r67.md",
                     "--purpose", "x", "--json"], {"generation": gen()}, "sess-M1")
rec("1c 宿主未在册 → 日常入口拒绝", "WF_IDENTITY_UNRESOLVED", (payload or {}).get("code"),
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
    path = wfdrive.temp(f"r67_{name}.json")
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
                     wfdrive.temp("r67_noapproval.json") if os.path.exists(wfdrive.temp("r67_noapproval.json")) else
                     json.dump({"files": [{"path": ".wf/spec/rules/r67c.md", "content": "# 三\n", "before": None}]},
                               open(wfdrive.temp("r67_noapproval.json"), "w")) or wfdrive.temp("r67_noapproval.json"), "--json"],
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
env_path = wfdrive.temp("r67_env.json")
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
restored = wf_gates.declared_step_specs(wf_cli.Context(F, ["--envelope", env_path]))
restored_ids = [entry.get("id") for entry in restored]
rec("3d 恢复后可用", "含 task.plan-approved 且义务 id 唯一",
    f"count={len(restored_ids)} has={'task.plan-approved' in restored_ids}",
    "task.plan-approved" in restored_ids and len(restored_ids) == len(set(restored_ids)))

json.dump(results, open(wfdrive.temp("r67_results.json"), "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
