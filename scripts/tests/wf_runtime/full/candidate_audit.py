#!/usr/bin/env python3
"""candidate_audit.py — 生成 candidate 逐 suite 审计证据（可复现、可重放）。

为什么必须有生成器：`candidate-audit.json` 是 `candidate_clean` 提升/保留的**来源证据**，
不能是一次性手工落盘。本脚本按固定步骤生成：

1. 用 `prepare_candidate_repo.py` 准备候选根（或 `--candidate-root` 复用并 `check`）；
2. 建一个 candidate 夹具模板（`wf_fixture.sh --deploy candidate` + `f1_init.py`）；
3. 对 `units.json` 的每个 suite 用 `run_one.sh` 在独立夹具上真实执行；
4. 从 `run_one` 结果行、`execution.py` 结果 JSON（suite rc / assertion observed/expected）
   和输出日志的 `[FAIL]` / `[<label>] ...: FAIL` 行生成记录。

输出是审计证据，不是门禁：失败 suite 仍写入记录（`status=bad`），由覆盖表/测试决定 disposition。
命令示例（validation 中引用同一条）：

    python3 scripts/tests/wf_runtime/full/candidate_audit.py \
      --tree docs/workflows/wf-release --version 0.1.0 \
      --workdir /tmp/wf-candidate-audit --out scripts/tests/wf_runtime/full/candidate-audit.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(HERE))
import prepare_candidate_repo  # noqa: E402

PY = os.environ.get("PY") or sys.executable
FAILURE_PATTERNS = (
    re.compile(r"\[FAIL\]"),
    re.compile(r"^\[[^]]+\].*:\s*FAIL(?:\s|$)"),
    re.compile(r"^FAIL(?:\s|$)"),
)


class AuditError(Exception):
    pass


def parse_failures(text):
    """提取所有失败断言行（兼容 `[FAIL]`、`[V1] ...: FAIL — ...` 与 `FAIL ...`）。"""
    found = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[PASS]"):
            continue
        if any(pattern.search(stripped) for pattern in FAILURE_PATTERNS):
            found.append(stripped)
    return found


def _sha256(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def sanitize(text, workdir=None):
    """去掉本次 workdir/临时 scope 的绝对路径，保持审计证据可移植、可复核。"""
    text = text or ""
    if workdir:
        text = text.replace(os.path.abspath(workdir), "<workdir>")
    return re.sub(r"/tmp/wf-test-scope-[A-Za-z0-9_]+", "<scope>", text)


def _last_line(path):
    try:
        lines = [line for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
                 if line.strip()]
    except OSError:
        return ""
    return lines[-1] if lines else ""


def _verify_unit_evidence(result, invocation_id):
    """本次 invocation 的精确 unit_execution/阶段引用；旧 JSON 或旧绿行不得冒充。"""
    unit_execution = result.get("unit_execution")
    if not isinstance(unit_execution, dict):
        return "no unit_execution（旧结果/未按新协议写入）"
    if unit_execution.get("invocation_id") != invocation_id:
        return f"invocation mismatch: {unit_execution.get('invocation_id')!r}"
    if unit_execution.get("run_id") is not None:
        return f"standalone audit received a managed run_id: {unit_execution.get('run_id')!r}"
    evidence = unit_execution.get("command_evidence")
    if not isinstance(evidence, list) or not evidence:
        return "no command_evidence"
    for item in evidence:
        if not isinstance(item, dict):
            return "malformed command_evidence"
        try:
            receipt = json.loads(Path(item["evidence_path"]).read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            return f"receipt unreadable: {item.get('evidence_path')}"
        if receipt.get("command_id") != item.get("command_id"):
            return "receipt command_id mismatch"
        if receipt.get("state") != "finished":
            return "receipt is not finished"
    return None


def record_suite(entry, results_dir, workdir=None, invocation_id=None):
    name = entry["name"]
    out_path = Path(results_dir) / f"{name}.out"
    result_path = Path(results_dir) / f"{name}.test.log.json"
    try:
        output = out_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        output = ""
    result = _read_json(result_path) or {}
    assertion = result.get("assertion_result") or {}
    evidence_problem = (_verify_unit_evidence(result, invocation_id)
                        if invocation_id is not None else None)
    unit_execution = result.get("unit_execution") or {}
    line = ""
    try:
        for candidate in reversed(Path(results_dir, "lines").read_text(encoding="utf-8").splitlines()):
            if candidate.startswith(name + "\t"):
                line = candidate
                break
    except OSError:
        pass
    parts = line.split("\t")
    command_rc = int(parts[1]) if len(parts) >= 5 and parts[1].lstrip("-").isdigit() else None
    command_status = parts[3] if len(parts) >= 5 else "missing"
    supervision = result.get("supervision") or {}
    # command rc 是 execution.py 的最终退出码（断言失败会覆盖 target rc）；suite_rc 必须取
    # 目标进程自身的退出码，避免把“断言观察数不符”误读成 suite 进程失败。
    suite_rc = supervision.get("target_rc", result.get("rc"))
    failures = [sanitize(item, workdir) for item in parse_failures(output)]
    reason = assertion.get("reason") or ""
    if reason and reason not in failures:
        failures.append(sanitize(reason, workdir))
    status = command_status
    if evidence_problem:
        status = "stale-evidence"
    return {
        "rc": command_rc,
        "status": status,
        "invocation_id": invocation_id,
        "unit_execution_state": unit_execution.get("state"),
        "unit_execution_run_id": unit_execution.get("run_id"),
        "command_evidence": len(unit_execution.get("command_evidence") or []),
        "evidence_problem": evidence_problem,
        "suite_rc": suite_rc,
        "execution_status": result.get("status"),
        "expected": assertion.get("expected", entry.get("expect")),
        "observed": assertion.get("observed"),
        "assertion_ok": assertion.get("ok"),
        "failures": failures[:20],
        "tail": sanitize((parts[4] if len(parts) >= 5 else "") or _last_line(out_path), workdir),
        "script_sha256": _sha256(HERE / entry.get("script", name + ".py")),
        "supervision_cleanup_state": supervision.get("cleanup_state"),
    }


def _audit_env(workdir, candidate, version, ref, template=None):
    env = {
        **os.environ,
        "WF_FIXTURE_DEPLOY": "candidate",
        "WF_RELEASE_ROOT": candidate,
        "WF_RELEASE_REF": ref,
        "WF_RELEASE_VERSION": version,
        "WF_RELEASE_REPO": candidate,
        "WF_RELEASE_TREE": candidate,
        "SHARED_RELEASE": candidate,
        "WF_INSTALL_REF": ref,
        "WF_TEST_LIB": os.path.join(candidate, "wf-release", "lib"),
        "RESULTS_DIR": os.path.join(workdir, "results"),
        "HERE": str(HERE),
        "PY": PY,
        "WF_NAMESPACE": "0",
        "WF_COMMAND_TIMEOUT": "240",
        "PYTHONPYCACHEPREFIX": os.path.join(workdir, "pycache"),
    }
    for name in ("WF_CANCEL_FILE", "WF_UNIT_FAULT", "WF_TEST_FAULT_INJECTION",
                 "WF_TEMPLATE_TXN_STOP_AFTER", "WF_TEMPLATE_TXN_REBUILD",
                 "WF_TEST_RELEASE_TXN_STOP_AFTER", "WF_TEST_RELEASE_TXN_REBUILD",
                 "WF_RESULTS_INIT_STOP_AFTER", "WF_EXECUTION_FAULT_TARGET",
                 "WF_EXECUTION_FAULT_POINT", "WF_EXECUTION_FAULT_ACTION",
                 "WF_EXECUTION_FAULT_READY_FD", "WF_RUNNER_FINALIZE_FAULT",
                 "WF_SUMMARY_FAULT", "WF_METRICS_FAULT", "WF_GUARDIAN_FAULT",
                 "WF_SUPERVISOR_FAULT"):
        env.pop(name, None)
    if template:
        env.update({"WF_TEMPLATE_READY": "1", "WF_TEMPLATE": template,
                    "WF_TEMPLATE_SOURCE": template})
    return env


def build_template(workdir, candidate, version, ref):
    template = os.path.join(workdir, "template")
    env = _audit_env(workdir, candidate, version, ref)
    subprocess.run([PY, str(HERE / "fixture_scope.py"), "reset", template], env=env, check=True)
    subprocess.run(["bash", str(HERE / "wf_fixture.sh"), template, "--deploy", "candidate",
                    "--release-root", candidate, "--release-ref", ref,
                    "--release-version", version], env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    subprocess.run([PY, str(HERE / "f1_init.py")], env={**env, "WF_FIX": template}, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return template


def generate(tree, version, ref, workdir, out, candidate_root=None, template=None):
    workdir = os.path.abspath(workdir)
    os.makedirs(workdir, exist_ok=True)
    results = os.path.join(workdir, "results")
    os.makedirs(results, exist_ok=True)
    if candidate_root:
        candidate = os.path.abspath(candidate_root)
        prepare_candidate_repo.check(tree, version, candidate)
    else:
        candidate = os.path.join(workdir, "candidate")
        if os.path.exists(candidate):
            prepare_candidate_repo.check(tree, version, candidate)
        else:
            prepare_candidate_repo.ensure(tree, version, candidate)
    if template is None:
        template = build_template(workdir, candidate, version, ref)
    else:
        template = os.path.abspath(template)
    units = json.loads((HERE / "units.json").read_text(encoding="utf-8"))["units"]
    isolated = [entry["name"] for entry in units if entry.get("isolated_user")]
    env = _audit_env(workdir, candidate, version, ref, template)
    env["WF_ISOLATED_UNITS"] = " ".join(isolated)
    records = {}
    for entry in units:
        if entry.get("kind") != "suite":
            continue
        name = entry["name"]
        fix = os.path.join(workdir, "fix-" + name)
        invocation = uuid.uuid4().hex
        run_env = {**env, "FIX": fix, "WF_UNIT_INVOCATION_ID": invocation}
        record = None
        proc = subprocess.run(
            ["bash", str(HERE / "run_one.sh"),
             f"{name}:suite:{entry['expect']}:template:{entry.get('script', name + '.py')}"],
            env=run_env, capture_output=True, text=True, timeout=400)
        record = record_suite(entry, results, workdir, invocation)
        record["runner_rc"] = proc.returncode
        record["runner_stderr_tail"] = sanitize((proc.stderr or "")[-400:], workdir)
        records[name] = record
        print(f"{name}\tstatus={record['status']}\tsuite_rc={record['suite_rc']}\t"
              f"observed={record['observed']}\texpected={record['expected']}", flush=True)
    payload = {
        "schema_version": 2,
        "generated_by": "scripts/tests/wf_runtime/full/candidate_audit.py",
        "invocation": ["python3", "scripts/tests/wf_runtime/full/candidate_audit.py",
                       "--tree", "docs/workflows/wf-release", "--version", version],
        "version": version,
        "release_ref": ref,
        "candidate_tree_digest": prepare_candidate_repo.common.tree_digest(candidate),
        "audited_at": datetime.date.today().isoformat(),
        "units": records,
    }
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", default=str(HERE.parents[3] / "docs" / "workflows" / "wf-release"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--out", default=str(HERE / "candidate-audit.json"))
    parser.add_argument("--candidate-root", default=None)
    parser.add_argument("--template", default=None)
    args = parser.parse_args(argv)
    ref = args.ref or f"refs/tags/wf-v{args.version}"
    workdir = args.workdir or tempfile.mkdtemp(prefix="wf-candidate-audit-")
    try:
        payload = generate(args.tree, args.version, ref, workdir, args.out,
                           args.candidate_root, args.template)
    except (AuditError, prepare_candidate_repo.CandidateError, subprocess.CalledProcessError) as exc:
        print(f"AUDIT-FAILED: {exc}", file=sys.stderr)
        return 1
    bad = [name for name, record in payload["units"].items() if record.get("status") != "ok"]
    print(f"AUDIT-WRITTEN: {args.out} suites={len(payload['units'])} bad={len(bad)} workdir={workdir}")
    if bad:
        print("AUDIT-BAD: " + " ".join(sorted(bad)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
