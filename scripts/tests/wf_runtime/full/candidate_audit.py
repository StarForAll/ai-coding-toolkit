#!/usr/bin/env python3
"""candidate_audit.py — 生成 candidate 逐 suite 审计证据（可复现、可增量、可拒绝）。

`candidate-audit.json` 是 `candidate_clean` 提升/保留的**来源证据**，不能是一次性手工落盘。
本脚本是唯一生成入口：

1. 用 `prepare_candidate_repo.py` 准备候选根（或 `--candidate-root` 复用并 `check`）；
2. 在候选发行锁内冻结本次身份（候选/来源树、tag commit、runner/helper/解释器输入、
   单元注册表），并建一次 candidate 夹具模板（`wf_fixture.sh --deploy candidate` + `f1_init.py`）；
3. 对 `units.json` 中每个可计划单元用 `run_one.sh` 在独立夹具上真实执行，逐行记录脚本字节、
   kind/expect/fixture/隔离设置、模板来源与夹具的实际安装身份；
4. 结束前重算同一批输入摘要；任何漂移、缺行或证据异常都**放弃发布**并保全旧报告，
   只在全部登记 ID 都有本次实际运行记录时同目录原子发布。

`--only` 只做增量补录：必须提供可核验的旧报告（同 schema/同身份/全 ID/待保留行输入未变），
否则整组拒绝并在新路径执行完整审计；不传 `--only` 表示完整审计（不是空选择）。

审计结果是证据状态，不是门禁；已知 dev-only 单元的 `bad` 行是预期事实，CLI 仍以 0 退出，
由 `source_coverage` 决定 disposition。`AUDIT-STATUS` 明确区分完整（全部 ok）与含失败断言。

    python3 scripts/tests/wf_runtime/full/candidate_audit.py \
      --tree docs/workflows/wf-release --version 0.1.0 \
      --workdir <scope>/candidate-audit-work --out <scope>/candidate-audit.json
    # 核对全部 ID/身份/状态后再把 scope 输出复制到受跟踪的 candidate-audit.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(HERE))
import prepare_candidate_repo  # noqa: E402
import release_context  # noqa: E402
import release_lock  # noqa: E402
import source_coverage  # noqa: E402
import verify_install_identity  # noqa: E402

PY = os.environ.get("PY") or sys.executable
REPORT_SCHEMA = 3
FAILURE_PATTERNS = (
    re.compile(r"\[FAIL\]"),
    re.compile(r"^\[[^]]+\].*:\s*FAIL(?:\s|$)"),
    re.compile(r"^FAIL(?:\s|$)"),
)
PLANNABLE = ("suite", "candidate", "flow", "extra")
# helper 输入的单一注册点：任何会改变审计判定或夹具/发行身份的字节都必须列在这里。
AUDIT_HELPERS = (
    "candidate_audit.py", "run_one.sh", "fixture_scope.py", "wf_fixture.sh", "f2_setup.sh",
    "f1_init.py", "prepare_candidate_repo.py", "plan.py", "execution.py",
    "resource_lifecycle.py", "template_check.py", "namespace.py", "wfdrive.py",
    "results_gate.py", "source_coverage.py", "verify_install_identity.py",
)
REPO_HELPERS = (
    "scripts/wf_release_common.py", "scripts/release_lock.py", "scripts/wf_test_paths.py",
    "scripts/python_runtime_identity.py",
)
BAD_ROW_STATUSES = ("stale-evidence", "missing")


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


def _canonical_digest(payload):
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


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


def _registry(units_path=None):
    """可计划单元注册表：名字 → 条目（含默认 fixture）。"""
    path = units_path or (HERE / "units.json")
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = {}
    for entry in document.get("units") or []:
        if entry.get("kind") not in PLANNABLE:
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise AuditError("units.json 含无可计划名称的条目")
        entries[name] = dict(entry, fixture=entry.get("fixture", "template"))
    return entries


def _registry_digest(entries):
    projection = [{"name": name, "kind": entry["kind"], "expect": entry["expect"],
                   "fixture": entry["fixture"], "script": entry.get("script", name + ".py"),
                   "isolated_user": bool(entry.get("isolated_user"))}
                  for name, entry in sorted(entries.items())]
    return _canonical_digest(projection)


def helper_digests():
    digests = {}
    for name in AUDIT_HELPERS:
        digests["scripts/tests/wf_runtime/full/" + name] = _sha256(HERE / name)
    for relative in REPO_HELPERS:
        digests[relative] = _sha256(REPO / relative)
    return digests


def interpreter_identity():
    executable = os.path.realpath(sys.executable)
    return {"implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "binary_digest": _sha256(executable)}


def audit_identity(tree, candidate, meta, version, ref, entries):
    """本次审计的完整身份：任何一项变化都要求完整重跑，不能把旧行包在新报告头里。"""
    import release_context
    common = prepare_candidate_repo.common
    manifest = json.loads(Path(candidate, "wf-release.json").read_text(encoding="utf-8"))
    return {
        "version": version,
        "release_ref": ref,
        "candidate_commit": meta.get("commit"),
        "candidate_tree_digest": common.tree_digest(candidate),
        "source_tree_digest": common.tree_digest(tree),
        "release_subject": common.release_subject(tree, version, ref)["digest"],
        "manifest_digest": common.manifest_digest(manifest),
        "rules_digest": (manifest.get("compatibility") or {}).get("rules_digest"),
        "units_registry_digest": _registry_digest(entries),
        "helpers": helper_digests(),
        "runtime": release_context.runtime_identity(),
        "interpreter": interpreter_identity(),
    }


def _installation_check(target, release_root, version, ref):
    """安装记录 + `.wf/lib` 字节：唯一实现见 verify_install_identity.py。"""
    record, problems = verify_install_identity.verify(
        str(target), str(release_root), ref, version, check_lib=True)
    return record, problems


def _installation_projection(record):
    if not isinstance(record, dict):
        return None
    return {"version": record.get("version"), "release_ref": record.get("release_ref"),
            "source_commit": record.get("source_commit"),
            "rules_digest": record.get("rules_digest")}


def _template_identity(template, release_root, version, ref, source):
    """模板来源身份：外部模板必须内容+安装身份可核验才可增量复用。"""
    record, problems = _installation_check(template, release_root, version, ref)
    if problems:
        raise AuditError("模板安装身份与候选不一致：" + "; ".join(problems))
    return {"source": source,
            "tree_digest": prepare_candidate_repo.common.tree_digest(template),
            "install": _installation_projection(record)}


def _row_identity(entry, script_sha256, template, isolated_user):
    """行的可复核输入身份；run-build 模板的树摘要不参与（由候选身份与 helper 摘要覆盖）。"""
    source = template.get("source")
    identity = {
        "script_sha256": script_sha256,
        "kind": entry["kind"],
        "expect": entry["expect"],
        "fixture": entry["fixture"],
        "isolated_user": bool(isolated_user),
        "template": {"source": source, "install": template.get("install")},
    }
    if source == "external":
        identity["template"]["tree_digest"] = template.get("tree_digest")
    return identity


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


def record_suite(entry, results_dir, workdir=None, invocation_id=None, *,
                 kind=None, expect=None, fixture=None, isolated_user=False,
                 template=None, installation=None, installation_problem=None,
                 script_sha256=None, input_identity=None):
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
    if installation_problem:
        evidence_problem = ("installation identity: " + installation_problem
                            if not evidence_problem else
                            evidence_problem + "; installation identity: " + installation_problem)
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
    script = entry.get("script", name + ".py")
    record = {
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
        "script_sha256": script_sha256 or _sha256(HERE / script),
        "supervision_cleanup_state": supervision.get("cleanup_state"),
        "kind": kind if kind is not None else entry.get("kind"),
        "expect": expect if expect is not None else entry.get("expect"),
        "fixture": fixture if fixture is not None else entry.get("fixture", "template"),
        "isolated_user": bool(isolated_user),
        "template": template,
        "installation": installation,
    }
    identity = input_identity or _row_identity(
        {"kind": record["kind"], "expect": record["expect"], "fixture": record["fixture"]},
        record["script_sha256"], template or {}, record["isolated_user"])
    record["input_identity"] = identity
    record["input_digest"] = _canonical_digest(identity)
    # 脚本来源分类只做登记：候选资格仍由安装身份与实际断言决定。
    record["source_layer"] = source_coverage.script_evidence(
        HERE / script).get("source_layer")
    return record


def _audit_env(workdir, candidate, version, ref, template=None, commit=None):
    env = {
        **os.environ,
        "WF_FIXTURE_DEPLOY": "candidate",
        "WF_RELEASE_ROOT": candidate,
        "WF_RELEASE_REF": ref,
        "WF_RELEASE_VERSION": version,
        "WF_RELEASE_COMMIT": commit or "",
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


def build_template(workdir, candidate, version, ref, commit):
    template = os.path.join(workdir, "template")
    env = _audit_env(workdir, candidate, version, ref, commit=commit)
    subprocess.run([PY, str(HERE / "fixture_scope.py"), "reset", template], env=env, check=True)
    subprocess.run(["bash", str(HERE / "wf_fixture.sh"), template, "--deploy", "candidate",
                    "--release-root", candidate, "--release-ref", ref,
                    "--release-version", version], env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    subprocess.run([PY, str(HERE / "f1_init.py")], env={**env, "WF_FIX": template}, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return template


def normalize_only(values, entries):
    """`--only` 的唯一解析：缺席=完整审计；空值/纯空白/未知 ID 整组拒绝。"""
    if values is None:
        return None
    normalized = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise AuditError("--only 不接受空值或纯空白值；不传 --only 表示完整审计")
        name = value.strip()
        if name not in entries:
            raise AuditError(
                f"--only 含未登记或不可计划的 ID：{name!r}；"
                "可选值见 units.json 中 kind 属于 " + "/".join(PLANNABLE) + " 的条目")
        if name not in normalized:
            normalized.append(name)
    return normalized


def _load_previous(path):
    previous = _read_json(path)
    if not isinstance(previous, dict):
        raise AuditError(f"--only 需要可核验的旧审计报告：{path} 不存在或不可读")
    return previous


def _validate_incremental(previous, identity, entries, scripts, selected, template_identity):
    if previous.get("schema_version") != REPORT_SCHEMA:
        raise AuditError("旧审计报告 schema 不可验证：请在新路径执行完整审计")
    if previous.get("identity") != identity:
        raise AuditError("审计身份与旧报告不一致（候选/树/helper/运行时/解释器）："
                         "请在新路径执行完整审计")
    units = previous.get("units")
    if not isinstance(units, dict) or set(units) != set(entries):
        raise AuditError("旧审计报告未覆盖当前全部可计划 ID：请在新路径执行完整审计")
    for name, record in units.items():
        if not isinstance(record, dict):
            raise AuditError(f"旧审计报告的行 {name} 结构不可验证：请在新路径执行完整审计")
        if name in selected:
            continue
        if record.get("status") in BAD_ROW_STATUSES:
            raise AuditError(f"待保留行 {name} 的证据异常（{record.get('status')}）："
                             "请在新路径执行完整审计")
        expected = _row_identity(entries[name], scripts[name], template_identity,
                                 record.get("isolated_user"))
        if record.get("input_identity") != expected or \
                record.get("input_digest") != _canonical_digest(expected):
            raise AuditError(f"待保留行 {name} 的输入已变化（脚本/期望/夹具/模板）："
                             "请在新路径执行完整审计")
    return units


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".tmp-", delete=False)
    temporary = Path(handle.name)
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        if not handle.closed:
            handle.close()
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def generate(tree, version, ref, workdir, out, candidate_root=None, template=None,
             only=None):
    workdir = os.path.abspath(workdir)
    entries = _registry()
    selected = normalize_only(only, entries)
    if candidate_root:
        candidate = os.path.abspath(candidate_root)
        meta, _status = prepare_candidate_repo.check(tree, version, candidate)
    else:
        candidate = os.path.join(workdir, "candidate")
        if os.path.exists(candidate):
            meta, _status = prepare_candidate_repo.check(tree, version, candidate)
        else:
            candidate, meta, _status = prepare_candidate_repo.ensure(tree, version, candidate)
    commit = meta.get("commit")
    if not commit:
        raise AuditError("候选 meta 没有已核 tag commit，审计身份不成立")
    lock_fd = release_lock.acquire(candidate, exclusive=True)
    try:
        # 锁内重新冻结：候选树/输入在取锁前可能被协作写者替换。
        identity = audit_identity(tree, candidate, meta, version, ref, entries)
        scripts = {name: _sha256(HERE / entry.get("script", name + ".py"))
                   for name, entry in entries.items()}
        previous = _load_previous(out) if selected is not None else None
        os.makedirs(workdir, exist_ok=True)
        results = os.path.join(workdir, "results")
        os.makedirs(results, exist_ok=True)
        if template is None:
            template_path = build_template(workdir, candidate, version, ref, commit)
            template_identity = _template_identity(template_path, candidate, version, ref,
                                                   "run-build")
        else:
            template_path = os.path.abspath(template)
            template_identity = _template_identity(template_path, candidate, version, ref,
                                                   "external")
        retained = None
        if selected is not None:
            # 待保留行的输入身份校验（模板来源/树漂移也在内）必须在启动任何套件前完成。
            retained = _validate_incremental(previous, identity, entries, scripts,
                                             set(selected), template_identity)
        isolated = [name for name, entry in entries.items() if entry.get("isolated_user")]
        env = _audit_env(workdir, candidate, version, ref, template_path, commit)
        env["WF_ISOLATED_UNITS"] = " ".join(isolated)
        records = dict(retained) if retained else {}
        wanted = selected if selected is not None else sorted(entries)
        for name in wanted:
            entry = entries[name]
            fixture = entry["fixture"]
            fix = os.path.join(workdir, "fix-" + name)
            invocation = uuid.uuid4().hex
            run_env = {**env, "FIX": fix, "WF_UNIT_INVOCATION_ID": invocation}
            proc = subprocess.run(
                ["bash", str(HERE / "run_one.sh"),
                 f"{name}:{entry['kind']}:{entry['expect']}:{fixture}:"
                 f"{entry.get('script', name + '.py')}"],
                env=run_env, capture_output=True, text=True, timeout=400)
            installation = None
            installation_problem = None
            install_target = Path(str(fix) + ".legacy") / name if fixture == "install" else Path(fix)
            install_record, problems = _installation_check(install_target, candidate,
                                                           version, ref)
            installation = _installation_projection(install_record)
            if problems:
                installation_problem = "; ".join(problems)
            record = record_suite(
                entry, results, workdir, invocation,
                kind=entry["kind"], expect=entry["expect"], fixture=fixture,
                isolated_user=bool(entry.get("isolated_user")),
                template=template_identity, installation=installation,
                installation_problem=installation_problem,
                script_sha256=scripts[name],
                input_identity=_row_identity(entry, scripts[name], template_identity,
                                             bool(entry.get("isolated_user"))))
            record["runner_rc"] = proc.returncode
            record["runner_stderr_tail"] = sanitize((proc.stderr or "")[-400:], workdir)
            records[name] = record
            print(f"{name}\tstatus={record['status']}\tsuite_rc={record['suite_rc']}\t"
                  f"observed={record['observed']}\texpected={record['expected']}", flush=True)
        # 结束校验：身份与逐单元脚本字节必须与锁内冻结值一致。
        end_identity = audit_identity(tree, candidate, meta, version, ref, entries)
        end_scripts = {name: _sha256(HERE / entry.get("script", name + ".py"))
                       for name, entry in entries.items()}
        if end_identity != identity:
            raise AuditError("审计期间公共输入/身份发生变化：拒绝发布，旧报告保持不变")
        if end_scripts != scripts:
            raise AuditError("审计期间单元脚本字节发生变化：拒绝发布，旧报告保持不变")
        missing = sorted(set(entries) - set(records))
        invalid = sorted(name for name, record in records.items()
                         if record.get("status") in BAD_ROW_STATUSES)
        if missing:
            print("AUDIT-STATUS=partial", flush=True)
            raise AuditError("审计未完成，缺 %d 个登记 ID：%s；不发布部分报告"
                             % (len(missing), " ".join(missing[:10])))
        if invalid:
            raise AuditError("证据异常行（安装/收据不成立）：%s；不发布"
                             % " ".join(invalid))
        status = "complete" if all(record.get("status") == "ok"
                                   for record in records.values()) else "failed"
        payload = {
            "schema_version": REPORT_SCHEMA,
            "generated_by": "scripts/tests/wf_runtime/full/candidate_audit.py",
            "invocation": ["python3", "scripts/tests/wf_runtime/full/candidate_audit.py",
                           "--tree", "docs/workflows/wf-release", "--version", version],
            "audit": {"kind": "incremental" if selected is not None else "full",
                      "status": status,
                      "audited_at": datetime.date.today().isoformat()},
            "identity": identity,
            "units": records,
        }
        _atomic_write_json(out, payload)
        return payload, status
    finally:
        release_lock.release(lock_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", default=str(HERE.parents[3] / "docs" / "workflows" / "wf-release"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--ref", default=None)
    parser.add_argument("--workdir", default=None)
    parser.add_argument("--out", default=str(HERE / "candidate-audit.json"))
    parser.add_argument("--only", action="append", default=None,
                        help="只审计指定单元并把记录合并进已有 --out（需要可核验的旧报告）")
    parser.add_argument("--candidate-root", default=None)
    parser.add_argument("--template", default=None)
    args = parser.parse_args(argv)
    ref = args.ref or f"refs/tags/wf-v{args.version}"
    try:
        # 选择面在任何写入/套件启动前解析：空值、未知 ID 与不可计划 ID 整组拒绝。
        normalize_only(args.only, _registry())
        workdir = args.workdir or tempfile.mkdtemp(prefix="wf-candidate-audit-")
        payload, status = generate(args.tree, args.version, ref, workdir, args.out,
                                   args.candidate_root, args.template, only=args.only)
    except (AuditError, prepare_candidate_repo.CandidateError,
            prepare_candidate_repo.common.ReleaseError, release_context.ContextError,
            release_lock.LockError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, OSError, ValueError) as exc:
        print(f"AUDIT-REFUSED: {exc}", file=sys.stderr)
        return 1
    bad = [name for name, record in payload["units"].items() if record.get("status") != "ok"]
    print(f"AUDIT-WRITTEN: {args.out} units={len(payload['units'])} bad={len(bad)}")
    print(f"AUDIT-STATUS={status}")
    if bad:
        print("AUDIT-BAD: " + " ".join(sorted(bad)), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
