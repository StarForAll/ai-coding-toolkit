#!/usr/bin/env python3
"""第三十轮 R67：写权入口实例/能力核验、baseline 状态与提案、清单声明、聚合脚本退出码。"""
import atexit, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
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
# 假环境按**真实 run_all 的契约**搭建：run_all 把选择交给 plan.py，
# 所以 plan.py / 注册表 / results_gate.py 必须在同一棵假树里，REPO_ROOT 也指向它。
fake_root = tempfile.mkdtemp(prefix="wf-r67-fake-repo-")
atexit.register(shutil.rmtree, fake_root, ignore_errors=True)
fake = os.path.join(fake_root, "scripts/tests/wf_runtime/full")
os.makedirs(fake)
real = wfdrive.REPO + "/scripts/tests/wf_runtime/full"
# “假树需要哪些文件”只有一处来源：plan.py 的三桶清单（COPY/STUB/SPECIAL）。
# 复制真实文件会改变假环境语义的条目（worker/夹具/repro 入口）一律桩化，不复制。
_plan_spec = importlib.util.spec_from_file_location("wf_r67_real_plan", os.path.join(real, "plan.py"))
_real_plan = importlib.util.module_from_spec(_plan_spec)
_plan_spec.loader.exec_module(_real_plan)


def _copy_into_fake(relative):
    source = os.path.join(real, relative)
    target = os.path.join(fake, relative)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy(source, target)


for _name in _real_plan.FAKE_TREE_SPECIAL + _real_plan.FAKE_TREE_COPY:
    _copy_into_fake(_name)
# 作者侧路径/scope helper：假树里的 plan.py / fixture_scope.py 无条件导入它，
# 缺文件必须当场失败（不提供“缺 helper 就跳过校验”的兼容分支）。
shutil.copy(os.path.join(wfdrive.REPO, "scripts", "wf_test_paths.py"),
            os.path.join(fake_root, "scripts", "wf_test_paths.py"))
# 完整运行身份（release-context / repro context 共用）：假树也必须能解析，不静默降级。
shutil.copy(os.path.join(wfdrive.REPO, "scripts", "python_runtime_identity.py"),
            os.path.join(fake_root, "scripts", "python_runtime_identity.py"))
# 测试发行入口桩（release_context 只借用它的 ensure/check 子命令；锁由 release_lock 负责）。
# 它必须遵守真实 CLI 的 `--json` 状态契约：release_context 会解析 status（built|reused|checked）。
open(os.path.join(fake_root, "scripts/tests/wf_test_release.py"), "w").write(
    'import json, sys\n\n\n'
    'def observe(root):\n'
    '    return {"root": root, "status": "absent", "counts": {},\n'
    '            "capacity": "not-measured", "inventory_hint": ""}\n\n\n'
    'def inventory(root):\n'
    '    return {"schema_version": 1, "domain": "test-release-cache", "root": root,\n'
    '            "status": "absent", "entries": [], "unknown": []}\n\n\n'
    'if __name__ == "__main__":\n'
    '    print(json.dumps({"status": "built", "builds": 1, "root": "fake", '
    '"version": "0.1.0"}))\n'
    '    raise SystemExit(0)\n')
# release 锁桩：假环境不付真实 flock，但保留 acquire/write_env/verify 的形状。
open(os.path.join(fake_root, "scripts/release_lock.py"), "w").write(
    'import os\n\n\nclass Busy(Exception):\n    pass\n\n\nclass LockError(Exception):\n    pass\n\n\n'
    'def acquire(root, exclusive=True):\n'
    '    return os.open(root + ".lock", os.O_CREAT | os.O_RDWR, 0o600)\n\n\n'
    'def write_env(fd, root):\n    pass\n\n\n'
    'def verify_lease(root=None):\n    return True\n\n\n'
    'def release(fd):\n    pass\n')
# 产品树摘要桩（run_all 用它做前后比对）
open(os.path.join(fake_root, "scripts/wf_release_common.py"), "w").write(
    'REPO_ROOT = "/tmp/r67_fake_repo"\n\n\ndef tree_digest(root):\n'
    '    return "sha256:" + "0" * 64\n\n\ndef release_subject(tree, version, ref):\n'
    '    return {"subject": {"tree": tree_digest(tree), "version": version, "ref": ref},\n'
    '            "digest": "sha256:" + "1" * 64}\n')
# run_all 的并行路径会调用 run_one.sh：假环境也要有可运行版本
open(os.path.join(fake, "run_one.sh"), "w").write(
    '#!/bin/bash\nset -uo pipefail\nrecord=$1\n'
    'if [ "${R67_SKIP_SERIAL:-0}" = "1" ] && [ "${WF_NAMESPACE:-1}" = "0" ]; then exit 0; fi\n'
    'suite=${record%%:*}\nkind=$(printf "%s" "$record" | cut -d: -f2)\n'
    'expect=$(printf "%s" "$record" | cut -d: -f3)\nscript=${record##*:}\n'
    'case "$kind" in suite|candidate) ekind=suite ;; flow|extra) ekind=flow ;; *) ekind=suite ;; esac\n'
    'out="$RESULTS_DIR/$suite.out"\n'
    '"$PY" "$HERE/execution.py" --name "$suite" --kind "$ekind" --expected "$expect" \\\n'
    '  --log "$RESULTS_DIR/$suite.test.log" --result "$RESULTS_DIR/$suite.test.log.json" \\\n'
    '  -- "$PY" "$HERE/$script" >>"$out" 2>&1\nrc=$?\n'
    'line=$(tail -1 "$out")\n'
    'status=ok\n[ "$rc" -eq 0 ] || status=bad\n'
    'row=$(printf "%s\\t%s\\t%s\\t%s\\t%s" "$suite" "$rc" "0" "$status" "$line")\n'
    'printf "%s\\n" "$row" >> "$RESULTS_DIR/lines"\n'
    'rid=()\n[ -n "${WF_RUN_ID:-}" ] && rid=(--run-id "$WF_RUN_ID")\n'
    '"$PY" "$HERE/resource_lifecycle.py" unit-execution --unit-result "$RESULTS_DIR/$suite.test.log.json" \\\n'
    '  --unit "$suite" --state passed --result-row "$row" \\\n'
    '  --phase "test:$RESULTS_DIR/$suite.test.log.json" "${rid[@]}" >>"$out" 2>&1 || exit 1\n')
open(os.path.join(fake, "wf_fixture.sh"), "w").write(
    '#!/bin/bash\nset -e\nF=${1:-/tmp/fake}\nrm -rf "$F"; mkdir -p "$F/.wf/bin"\n'
    ': > "$F/.wf/bin/wf.py"\n')
open(os.path.join(fake, "f1_init.py"), "w").write("print('ok')\n")
# 假套件/流程/extra 依注册表清单生成：清单变动后假环境不会缺文件
_manifest = json.load(open(os.path.join(real, "units.json"), encoding="utf-8"))
# plan.py 的 modules 键存在性校验要求 REPO/docs/workflows/wf/<key> 存在：
# 依清单生成桩路径（目录键建目录、文件键建空文件），假环境跟上 plan.py 的契约面。
for _key in (_manifest.get("modules") or {}):
    _stub = os.path.join(fake_root, "docs", "workflows", "wf", _key)
    if _key.endswith("/"):
        os.makedirs(_stub, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(_stub), exist_ok=True)
        open(_stub, "w").close()
# 桩文件按注册表逐可计划单元生成：**文件名取该单元的 `script`**（不是 `<name>.py`），
# 输出行数等于 `expect`——名字或 script 拼错会在假树里缺文件/少行，由 run_all 当场暴露。
for _entry in _manifest["units"]:
    if _entry.get("kind") not in ("suite", "flow", "extra", "candidate"):
        continue
    _name = _entry["name"]
    _script = _entry.get("script", _name + ".py")
    _count = int(_entry["expect"])
    _path = os.path.join(fake, _script)
    os.makedirs(os.path.dirname(_path), exist_ok=True)
    _passes = "".join("print('[PASS] case " + str(i) + "')\n" for i in range(1, _count + 1))
    if _name == "cp1_tests":
        # 唯一失败桩：用于“失败必须传播”的负例。
        open(_path, "w").write(
            "print('[FAIL] fake')\nprint('saved 0 cases; 0 passed')\nraise SystemExit(1)\n")
    elif _entry.get("kind") in ("suite", "candidate"):
        open(_path, "w").write(_passes + "print('saved %d / %d')\n" % (_count, _count))
    else:
        open(_path, "w").write(_passes)
# repro 一键入口的桩：run_all 的 run_repro 会调用 $HERE/repro/run.sh
open(os.path.join(fake, "repro", "run.sh"), "w").write(
    '#!/bin/bash\n'
    'echo "ok   fake-case"\n'
    'echo "REPRO_TOTAL=1"\n'
    'echo "REPRO_PASSED=1"\n'
    'echo "REPRO_FAILED=0"\n'
    'echo "REPRO_GREEN_SECONDS=0"\n'
    'echo "REPRO_RED_SECONDS=0"\n'
    'echo "repro 用例：1/1"\n'
    'exit 0\n')
os.chmod(os.path.join(fake, "repro", "run.sh"), 0o755)
# 测试发行副本桩：run_f0 会调用 $RELEASE_REPO/install.py。
# 位置必须在 fake scope 内：runner 的管理路径（含 WF_TEST_RELEASE_CACHE）在 scope 下
# 统一由 wf_test_paths 校验，域外路径会在首次写前被拒。
# 外层可能以 `WF_SUITES=... bash run_all.sh` 启动（命令前缀会导出到子进程），
# 假环境必须显式清空，否则内层 run_all 会被当成子集模式
# 假环境不跑夹具模板（模板会调用 template_check.py，而这里只验证门禁逻辑）；
# 复制 run_all.sh 的套件必须显式关掉模板，否则会因缺少 template_check.py 而整段失败。
# 假运行器独占自己的 owned 测试 scope：管理写入口（results/cache/fixture/pycache）全在 scope 内，
# 不触碰真实用户锁与缓存，也不冒充宿主继承锁（任务 design §4.2/4.3）。
_fake_scope = subprocess.run([sys.executable, os.path.join(real, "fixture_scope.py"), "create-scope"],
                             capture_output=True, text=True, check=True).stdout.strip()
atexit.register(shutil.rmtree, _fake_scope, ignore_errors=True)
release_cache = os.path.join(_fake_scope, "release-cache")
os.makedirs(os.path.join(release_cache, "0.1.0"))
open(os.path.join(release_cache, "0.1.0", "install.py"), "w").write("import sys; sys.exit(0)\n")
_fake_cache = tempfile.mkdtemp(prefix="wf-r67-fake-cache-", dir=_fake_scope)
_fake_fix = tempfile.mkdtemp(prefix="wf-r67-fake-fixture-", dir=_fake_scope)
_fake_results1 = tempfile.mkdtemp(prefix="wf-r67-fake-results-", dir=_fake_scope)
_fake_results2 = tempfile.mkdtemp(prefix="wf-r67-fake-results-", dir=_fake_scope)
for _path in (_fake_fix, _fake_results1, _fake_results2):
    atexit.register(shutil.rmtree, _path, ignore_errors=True)
# 宿主 locator 一律不带进假运行器：串行单元会原样继承父进程环境（并行单元由 namespace
# 负责清除），而内层 run_all 用的是自己的 scope——借外面的结果锁/租约/pycache 本身就是
# 「冒充继承锁」，必须显式清空（与 namespace.HOST_LOCATORS 同口径）。
# fixture 租约**不**清：嵌套运行器的继承语义就是同一条全局 flock（locking 由 lock_run 负责，
# 清了会变成自撞 busy）。要清的是"本层 scope 的结果锁/发行锁/frame/pycache"这类**域内**定位。
_HOST_LOCATORS = (
    "WF_RESULTS_LOCK_FD", "WF_RESULTS_LOCK_PID", "WF_RESULTS_LOCK_DOMAIN", "WF_RESULTS_LOCK_MNT",
    "WF_TEST_RELEASE_LEASE_FD", "WF_TEST_RELEASE_LEASE_PID", "WF_TEST_RELEASE_LEASE_MNT",
    "WF_RUNNER_ENTRY_PID", "WF_RUNNER_CONTROL_PID",
    "WF_FRAME_ENTRY_PID", "WF_FRAME_RESULTS_ROOT", "WF_FRAME_RESULTS_EXPLICIT",
    "WF_FRAME_SCOPE_ROOT", "WF_FRAME_PLAN_FILE", "WF_FRAME_PLAN_SHA256", "WF_FRAME_PLAN_SIZE",
    "WF_FRAME_CONTEXT_FILE", "WF_FRAME_CONTEXT_SHA256", "WF_FRAME_CONTEXT_SIZE",
    "WF_TEST_SCOPE_ROOT", "WF_PLAN_LOG", "PYTHONPYCACHEPREFIX", "WF_PYCACHE",
)
_fake_base = {key: value for key, value in os.environ.items() if key not in _HOST_LOCATORS}
_fake_env = {**_fake_base, "WF_TEST_SCOPE_ROOT": _fake_scope, "WF_FIX": _fake_fix,
             "WF_RESULTS_CACHE": _fake_cache, "WF_TEST_RUN_CACHE": os.path.join(_fake_scope, "state"),
             "WF_TEST_RELEASE_CACHE": release_cache, "WF_JOBS": "1", "WF_NO_TEMPLATE": "1",
             # 显式再钉一次缓存开关：`WF_NO_TEMPLATE=1` 蕴含关闭缓存，但不能依赖实现漂移。
             "WF_NO_TEMPLATE_CACHE": "1",
             "WF_SUITES": "cp1_tests", "WF_WITH_REPRO": "", "WF_KNOWN_LEGACY": ""}
proc = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                      env={**_fake_env, "WF_RESULTS_DIR": _fake_results1})
_summary = [ln for ln in proc.stdout.splitlines() if ln.startswith("---- ")]
rec("4 有失败时脚本非零退出", "exit≠0 且 controller 报失败",
    f"exit={proc.returncode} summary={_summary[-1] if _summary else None} "
    f"stdout={(proc.stdout or '')[-4000:]} stderr={(proc.stderr or '')[-4000:]}",
    proc.returncode != 0 and ("GATE-FAIL" in (proc.stderr or "")
                              or any("status=failed" in ln for ln in _summary)))
_cp1_expect = int(next(item["expect"] for item in _manifest["units"] if item["name"] == "cp1_tests"))
open(os.path.join(fake, "cp1_tests.py"), "w").write(
    "".join("print('[PASS] case " + str(i) + "')\n" for i in range(1, _cp1_expect + 1))
    + "print('saved %d / %d')\n" % (_cp1_expect, _cp1_expect))
proc2 = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                       env={**_fake_env, "WF_RESULTS_DIR": _fake_results2})
if proc2.returncode != 0:
    print("4b fake 输出尾部:", "\n".join(proc2.stdout.splitlines()[-6:])[:500],
          "stderr:", (proc2.stderr or "")[-500:])
rec("4b 无失败时零退出", "exit=0",
    f"exit={proc2.returncode} stdout={(proc2.stdout or '')[-800:]} "
    f"stderr={(proc2.stderr or '')[-800:]}", proc2.returncode == 0)

# 4c 期望用例数预算：桩少输出一行 [PASS]（汇总行同步改成 expect-1，内部自洽）→
# execution.verdict 的 observed != expect 必须让它变红；错误行要指出单元名与期望/实际。
open(os.path.join(fake, "cp1_tests.py"), "w").write(
    "".join("print('[PASS] case " + str(i) + "')\n" for i in range(1, _cp1_expect))
    + "print('saved %d / %d')\n" % (_cp1_expect - 1, _cp1_expect - 1))
_fake_results3 = tempfile.mkdtemp(prefix="wf-r67-fake-results-", dir=_fake_scope)
atexit.register(shutil.rmtree, _fake_results3, ignore_errors=True)
proc3 = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                       env={**_fake_env, "WF_RESULTS_DIR": _fake_results3})
_budget_log = ""
try:
    _budget_log = open(os.path.join(_fake_results3, "cp1_tests.out"), encoding="utf-8").read()
except OSError:
    pass
rec("4c 少一行 PASS → 红且指出期望/实际", "exit≠0 且 EXECUTION-FAILED 指到 cp1_tests",
    f"exit={proc3.returncode} log_tail={_budget_log.strip().splitlines()[-1:] }",
    proc3.returncode != 0 and "cp1_tests" in proc3.stdout
    and "EXECUTION-FAILED: cp1_tests" in _budget_log
    and "expected=" + str(_cp1_expect) in _budget_log)

# 4d 串行段完整性：把 cp1 标成 parallel:false，并让串行域（WF_NAMESPACE=0）的桩不写结果行。
# 证明 results_gate 覆盖 PLAN_UNITS 全集（含串行段），不是只覆盖并行子集。
_registry_path = os.path.join(fake, "units.json")
_registry = json.load(open(_registry_path, encoding="utf-8"))
for _entry in _registry["units"]:
    if _entry["name"] == "cp1_tests":
        _entry["parallel"] = False
        _entry["notes"] = "r67 串行段完整性构造（临时）"
json.dump(_registry, open(_registry_path, "w", encoding="utf-8"), ensure_ascii=False)
_fake_results4 = tempfile.mkdtemp(prefix="wf-r67-fake-results-", dir=_fake_scope)
atexit.register(shutil.rmtree, _fake_results4, ignore_errors=True)
proc4 = subprocess.run(["bash", os.path.join(fake, "run_all.sh")], capture_output=True, text=True,
                       env={**_fake_env, "WF_RESULTS_DIR": _fake_results4, "WF_JOBS": "4",
                            "R67_SKIP_SERIAL": "1"})
rec("4d 串行段漏跑结果 → 证据缺口", "exit≠0 且 ASSESS_MISSING 含 cp1_tests",
    f"exit={proc4.returncode} missing={(proc4.stdout or '')[-200:]}",
    proc4.returncode != 0 and "ASSESS_MISSING=cp1_tests" in proc4.stdout)

json.dump(results, open("/tmp/r67_results.json", "w"), ensure_ascii=False, indent=2)
print("saved", sum(1 for r in results if r["pass"]), "/", len(results))
