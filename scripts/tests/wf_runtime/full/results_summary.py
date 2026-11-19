#!/usr/bin/env python3
"""results_summary.py — 摘要输入的测量交接与唯一发布点。

本模块只消费已核验的**当前证据**（父任务 design §6/§6.1）：

- `write_metrics`：把内层采集的计时/并发/模板事实写成 schema1 交接对象，绑定本代
  run_id/canonical root/role 与当前 plan/context/lines/unit/repro 输入的 sha256+size；
  它只做测量交接，不携带 gate/cleanup/成功结论；
- `read_metrics`：controller 侧唯一读取点，用自己持有的预期 run_id/root/role 与冻结输入
  重算并逐项比对；旧代/缺失/截断/错类型/输入不符一律拒绝；
- `build`/`publish`：构造最终 schema4 对象一次原子发布（临时文件 → fsync → replace），
  读回完整对象与之相等才返回成功；返回对象、落盘对象与 `summary_path` 是同一份事实。

摘要的 gate/计数/债务来自 `results_gate.assess_run_results()`，cleanup 来自
`runner_cleanup` 的当前报告；本模块不再自己算另一份 fail。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
METRICS_SCHEMA = 1
SUMMARY_SCHEMA = 4
LEGACY_SUMMARY_SCHEMAS = (3,)
# 与 runner_cleanup.OUTCOMES 同一有限集：摘要只接受这些值，不从旧 bad 行反推类别。
UNIT_OUTCOMES = ("passed", "assertion_failed", "preparation_failed", "execution_failed",
                 "cancelled", "unverified")
MAX_INPUT_BYTES = 1 << 20

INT_MEASUREMENTS = ("full_mode", "jobs", "requested_jobs", "effective_jobs", "repro_jobs",
                    "template_build_sequences", "build_seconds", "template_seconds",
                    "init_millis", "suite_millis", "green_seconds", "red_seconds",
                    "total_millis", "pool_seconds", "repro_seconds")
STR_MEASUREMENTS = ("mode", "fixture_deploy", "execution_mode", "fallback_reason",
                    "repro_mode", "pycache_root", "template_source")
BOOL_MEASUREMENTS = ("repro_concurrent", "template_cache_hit", "template_reused")
LIST_MEASUREMENTS = ("repro_groups",)
NULLABLE_MEASUREMENTS = ("template_cache_key", "release_build")
REQUIRED_MEASUREMENTS = INT_MEASUREMENTS + STR_MEASUREMENTS + BOOL_MEASUREMENTS + \
    LIST_MEASUREMENTS + NULLABLE_MEASUREMENTS
RUN_ROLES = ("full", "repro")


class SummaryError(Exception):
    """可预期的拒绝（非零退出；调用方不得打印 GATE-OK）。"""


# ---- 输入快照 ---------------------------------------------------------------


def _read_bytes(path, label):
    path = Path(path)
    if path.is_symlink():
        raise SummaryError(f"{label} must not be a symlink: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SummaryError(f"{label} unreadable: {pad(path, exc)}") from exc
    if len(data) > MAX_INPUT_BYTES:
        raise SummaryError(f"{label} exceeds {MAX_INPUT_BYTES} bytes: {path}")
    return data


def pad(path, exc):
    return f"{path}: {exc}"


def _json_object(data, label):
    try:
        value = json.loads(data)
    except ValueError as exc:
        raise SummaryError(f"{label} is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SummaryError(f"{label} must be a JSON object")
    return value


def file_evidence(path, label):
    data = _read_bytes(path, label)
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def plan_units(plan):
    units = plan.get("units")
    if not isinstance(units, list) or not units:
        raise SummaryError("frozen plan has no units")
    names, kinds = [], {}
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("name"), str):
            raise SummaryError("frozen plan unit is malformed")
        if unit["name"] in kinds:
            raise SummaryError(f"frozen plan repeats unit {unit['name']}")
        names.append(unit["name"])
        kinds[unit["name"]] = unit.get("kind")
    return names, kinds


def canonical_root(root):
    path = str(root)
    if not os.path.isabs(path) or os.path.islink(path):
        raise SummaryError(f"results root must be an absolute real directory: {root!r}")
    return os.path.realpath(path)


def _unit_inputs(results_dir, names, run_id):
    """逐单元输入快照：缺记录/结构缺失是**事实**（state=incomplete），不阻断摘要；
    外来 run_id/单元名是矛盾输入，仍拒绝。"""
    evidence, problems = {}, []
    for name in names:
        path = Path(results_dir) / f"{name}.test.log.json"
        try:
            record = _json_object(_read_bytes(path, f"unit result {name}"), f"unit result {name}")
        except SummaryError as exc:
            evidence[name] = {"state": "incomplete", "reason": str(exc)}
            continue
        unit_execution = record.get("unit_execution")
        if not isinstance(unit_execution, dict):
            evidence[name] = {"state": "incomplete", "reason": "no unit_execution"}
            continue
        if unit_execution.get("run_id") != run_id:
            problems.append(f"unit result {name} belongs to another run_id")
            continue
        if unit_execution.get("unit") != name:
            problems.append(f"unit result {name} unit_execution names another unit")
            continue
        row = unit_execution.get("result_row")
        if not isinstance(row, list) or len(row) != 5 or row[0] != name:
            evidence[name] = {"state": "incomplete", "reason": "result_row is malformed"}
            continue
        evidence[name] = file_evidence(path, f"unit result {name}")
    return evidence, problems


def _repro_inputs(repro_results, bundle_sha=None, bundle_size=None):
    root = Path(repro_results)
    bundle = root / "inputs.json"
    data = _read_bytes(bundle, "repro bundle")
    sha = hashlib.sha256(data).hexdigest()
    if bundle_sha and sha != bundle_sha:
        raise SummaryError("repro bundle digest does not match the frozen bundle")
    if bundle_size is not None and str(len(data)) != str(bundle_size):
        raise SummaryError("repro bundle size does not match the frozen bundle")
    records = {}
    try:
        names = sorted(path.name for path in root.iterdir()
                       if path.is_file() and path.name.endswith(".json")
                       and path.name not in ("inputs.json", ".wf-results-owner.json"))
    except OSError as exc:
        raise SummaryError(f"repro results unreadable: {exc}") from exc
    for name in names:
        records[name] = file_evidence(root / name, f"repro record {name}")
    return {"state": "present", "bundle": {"sha256": sha, "size": len(data)},
            "records": records}


def collect_inputs(results_dir, run_id, role, plan_path, context_path=None, repro_results=None,
                   bundle_sha=None, bundle_size=None):
    results_dir = Path(results_dir)
    plan_data = _read_bytes(plan_path, "frozen plan")
    plan = _json_object(plan_data, "frozen plan")
    inputs = {"plan": {"sha256": hashlib.sha256(plan_data).hexdigest(), "size": len(plan_data)}}
    if role == "full":
        names, _kinds = plan_units(plan)
        if not context_path:
            raise SummaryError("full metrics require the verified release context")
        context_data = _read_bytes(context_path, "release context")
        context = _json_object(context_data, "release context")
        if context.get("plan_sha256") != inputs["plan"]["sha256"]:
            raise SummaryError("release context does not bind the frozen plan digest")
        if str(context.get("plan_size")) != str(inputs["plan"]["size"]):
            raise SummaryError("release context does not bind the frozen plan size")
        inputs["context"] = {"sha256": hashlib.sha256(context_data).hexdigest(),
                             "size": len(context_data)}
        inputs["lines"] = file_evidence(results_dir / "lines", "result lines")
        units, problems = _unit_inputs(results_dir, names, run_id)
        if problems:
            raise SummaryError("unit evidence is incomplete: " + "; ".join(problems[:5]))
        inputs["units"] = units
        if repro_results:
            inputs["repro"] = _repro_inputs(repro_results, bundle_sha, bundle_size)
        else:
            inputs["repro"] = {"state": "not-applicable"}
    else:
        # 独立 repro 的冻结计划不携带执行单元：它只用本代 bundle/records 作为输入证据。
        if not repro_results:
            raise SummaryError("repro role requires its own results root")
        inputs["repro"] = _repro_inputs(repro_results, bundle_sha, bundle_size)
        inputs["plan"] = {"state": "not-applicable"}
        inputs["units"] = {}
    return inputs


# ---- measurements -----------------------------------------------------------


def validate_measurements(measurements):
    if not isinstance(measurements, dict):
        raise SummaryError("measurements must be an object")
    missing = [key for key in REQUIRED_MEASUREMENTS if key not in measurements]
    if missing:
        raise SummaryError("measurements missing: " + " ".join(missing))
    unknown = sorted(set(measurements) - set(REQUIRED_MEASUREMENTS))
    if unknown:
        raise SummaryError("measurements carry unknown fields: " + " ".join(unknown))
    clean = {}
    for key in INT_MEASUREMENTS:
        value = measurements[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SummaryError(f"measurement {key} must be a non-negative integer")
        clean[key] = value
    for key in STR_MEASUREMENTS:
        value = measurements[key]
        if not isinstance(value, str):
            raise SummaryError(f"measurement {key} must be a string")
        clean[key] = value
    for key in BOOL_MEASUREMENTS:
        value = measurements[key]
        if not isinstance(value, bool):
            raise SummaryError(f"measurement {key} must be a boolean")
        clean[key] = value
    groups = measurements["repro_groups"]
    if not isinstance(groups, list) or any(not isinstance(item, str) for item in groups):
        raise SummaryError("measurement repro_groups must be a list of strings")
    clean["repro_groups"] = list(groups)
    if measurements["template_cache_key"] is not None and \
            not isinstance(measurements["template_cache_key"], str):
        raise SummaryError("measurement template_cache_key must be a string or null")
    if measurements["release_build"] not in (None, "built", "reused", "checked"):
        raise SummaryError("measurement release_build must be built|reused|checked or null")
    clean["template_cache_key"] = measurements["template_cache_key"]
    clean["release_build"] = measurements["release_build"]
    if clean["mode"] not in ("full", "subset", "representative"):
        raise SummaryError(f"measurement mode invalid: {clean['mode']!r}")
    if clean["fixture_deploy"] not in ("dev", "candidate"):
        raise SummaryError(f"measurement fixture_deploy invalid: {clean['fixture_deploy']!r}")
    if clean["repro_mode"] not in ("none", "green", "red", "both", "auto"):
        raise SummaryError(f"measurement repro_mode invalid: {clean['repro_mode']!r}")
    if clean["execution_mode"] not in ("serial", "unshare"):
        raise SummaryError(f"measurement execution_mode invalid: {clean['execution_mode']!r}")
    if clean["template_source"] not in ("none", "run-build", "cache"):
        raise SummaryError(f"measurement template_source invalid: {clean['template_source']!r}")
    if clean["jobs"] < 1 or clean["requested_jobs"] < 1 or clean["effective_jobs"] < 1 \
            or clean["repro_jobs"] < 1:
        raise SummaryError("measurement job counts must be positive")
    if clean["requested_jobs"] != clean["jobs"] and clean["effective_jobs"] != 1:
        raise SummaryError("measurement effective_jobs contradicts the requested/actual jobs")
    if clean["template_cache_hit"] and clean["template_source"] != "cache":
        raise SummaryError("measurement template_cache_hit contradicts template_source")
    if clean["template_cache_hit"] and clean["template_build_sequences"] != 0:
        raise SummaryError("measurement template_build_sequences contradicts a cache hit")
    if clean["repro_mode"] == "none":
        if clean["repro_groups"] or clean["green_seconds"] or clean["red_seconds"] \
                or clean["repro_seconds"]:
            raise SummaryError("measurement repro facts must be 0/empty when repro is disabled")
    return clean


# ---- write / read -----------------------------------------------------------


FAULT_SWITCH = "WF_TEST_FAULT_INJECTION"
METRICS_FAULTS = ("metrics-write-oserror", "metrics-missing", "metrics-truncated",
                  "metrics-old-run", "metrics-input-mismatch")


def validate_fault(fault):
    if not fault:
        return None
    if os.environ.get(FAULT_SWITCH) != "1":
        raise SummaryError(f"metrics fault requires {FAULT_SWITCH}=1")
    if fault not in METRICS_FAULTS:
        raise SummaryError(f"unknown metrics fault: {fault!r}")
    import fixture_scope
    if fixture_scope.current_scope() is None:
        raise SummaryError("metrics fault requires an owned test scope")
    return fault


def write_metrics(results_dir, run_id, role, plan_path, measurements, context_path=None,
                  repro_results=None, bundle_sha=None, bundle_size=None, metrics_path=None,
                  fault=None):
    """schema1 测量交接：原子写、绑定本代身份与当前输入快照。"""
    results_dir = Path(results_dir)
    root = canonical_root(results_dir)
    if role not in RUN_ROLES or not isinstance(run_id, str) or not run_id:
        raise SummaryError("metrics role/run_id is invalid")
    fault = validate_fault(fault)
    clean = validate_measurements(measurements)
    inputs = collect_inputs(results_dir, run_id, role, plan_path, context_path, repro_results,
                            bundle_sha, bundle_size)
    if clean["repro_mode"] == "none" and inputs["repro"].get("state") == "present":
        raise SummaryError("measurement repro_mode is none while repro inputs are present")
    payload = {"schema_version": METRICS_SCHEMA, "run_id": run_id, "results_root": root,
               "role": role, "state": "complete", "inputs": inputs,
               "measurements": clean}
    if fault == "metrics-write-oserror":
        raise SummaryError("injected metrics write failure")
    if fault == "metrics-missing":
        raise SummaryError("injected metrics missing")
    if fault == "metrics-old-run":
        payload["run_id"] = "0000000000000-0-injectedoldrun"
    if fault == "metrics-input-mismatch":
        if role == "full":
            payload["inputs"]["lines"] = {"sha256": "0" * 64, "size": payload["inputs"]["lines"]["size"]}
        else:
            payload["inputs"]["repro"]["bundle"]["sha256"] = "0" * 64
    path = Path(metrics_path) if metrics_path else results_dir / "summary-metrics.json"
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if fault == "metrics-truncated":
        data = data[:len(data) // 2]
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError as exc:
        raise SummaryError(f"metrics publish failed: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if fault == "metrics-truncated":
        raise SummaryError("injected truncated metrics bytes")
    return path


def read_metrics(path, expected_run_id, expected_root, expected_role, plan_path,
                 context_path=None, repro_results=None, bundle_sha=None, bundle_size=None):
    """唯一读取点：核本代身份与当前输入快照，返回 (measurements, input_evidence)。"""
    data = _read_bytes(path, "metrics")
    record = _json_object(data, "metrics")
    if record.get("schema_version") != METRICS_SCHEMA or isinstance(record.get("schema_version"), bool):
        raise SummaryError(f"metrics schema must be {METRICS_SCHEMA}; old metrics are display-only")
    if record.get("state") != "complete":
        raise SummaryError("metrics are not complete")
    if record.get("run_id") != expected_run_id:
        raise SummaryError("metrics run_id does not belong to this run")
    if record.get("results_root") != canonical_root(expected_root):
        raise SummaryError("metrics results_root mismatch")
    if record.get("role") != expected_role:
        raise SummaryError("metrics role mismatch")
    measurements = validate_measurements(record.get("measurements"))
    current = collect_inputs(expected_root, expected_run_id, expected_role, plan_path,
                             context_path, repro_results, bundle_sha, bundle_size)
    stored = record.get("inputs")
    if not isinstance(stored, dict) or stored != current:
        raise SummaryError("metrics inputs do not match the current evidence")
    input_evidence = {"metrics": {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)},
                      **current}
    return measurements, input_evidence


# ---- 发布 -------------------------------------------------------------------


def _number(metrics, key):
    value = metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SummaryError(f"measurement {key} is not a non-negative integer")
    return value


def repro_input_evidence(repro_root, bundle_sha=None, bundle_size=None):
    """独立 repro 的输入证据（不消费 full metrics/plan）。"""
    return {"repro": _repro_inputs(repro_root, bundle_sha, bundle_size)}


def _candidate_commit(plan, context):
    """候选提交的唯一投影：dev/未完成候选核验时为 null，候选成功时必须非空。"""
    if plan.get("fixture_deploy") != "candidate":
        return None
    if not isinstance(context, dict):
        return None
    commit = (context.get("candidate") or {}).get("commit")
    return commit if isinstance(commit, str) and commit else None


def _repro_phase_counts(plan, report):
    """repro 相位统计：禁用时全零；启用但本代没有合法 bundle 时为 null。"""
    if not plan.get("repro_enabled"):
        return {phase: {"planned": 0, "passed": 0, "failed": 0, "unverified": 0}
                for phase in ("green", "red")}
    counts = (report.get("repro") or {}).get("phase_counts")
    if counts is None:
        return None
    clean = {}
    for phase in ("green", "red"):
        entry = counts.get(phase)
        if not isinstance(entry, dict):
            raise SummaryError(f"repro phase counts missing {phase}")
        values = {}
        for key in ("planned", "passed", "failed", "unverified"):
            value = entry.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise SummaryError(f"repro phase count {phase}.{key} is invalid")
            values[key] = value
        if values["planned"] != values["passed"] + values["failed"] + values["unverified"]:
            raise SummaryError(f"repro phase counts for {phase} do not add up to planned")
        clean[phase] = values
    return clean


def _validate_unit_outcomes(value):
    """`unit_outcomes` 是 typed 分类（runner_cleanup 唯一产生）；结构非法即拒绝发布。"""
    if value is None:
        return None
    if not isinstance(value, list):
        raise SummaryError("summary unit_outcomes is not a list")
    clean, seen = [], set()
    for item in value:
        if not isinstance(item, dict):
            raise SummaryError("summary unit_outcomes entry is not an object")
        unit, outcome = item.get("unit"), item.get("outcome")
        if not isinstance(unit, str) or not unit:
            raise SummaryError("summary unit_outcomes entry has no unit")
        if unit in seen:
            raise SummaryError(f"summary unit_outcomes repeats unit {unit!r}")
        if outcome not in UNIT_OUTCOMES:
            raise SummaryError(f"summary unit outcome is invalid: {outcome!r}")
        seen.add(unit)
        clean.append({"unit": unit, "outcome": outcome})
    return clean


def _validate_outcome_counts(value, unit_outcomes):
    """typed 计数必须与逐单元 outcome 一致；缺失时按零计（历史/独立 repro 摘要）。"""
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise SummaryError("summary outcome counts are not an object")
    unknown = set(value) - set(UNIT_OUTCOMES)
    if unknown:
        raise SummaryError("summary outcome counts have unknown keys: " + " ".join(sorted(unknown)))
    counts = {}
    for name in UNIT_OUTCOMES:
        number = value.get(name, 0)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise SummaryError(f"summary outcome count {name} is invalid")
        counts[name] = number
    if unit_outcomes is not None:
        derived = {name: 0 for name in UNIT_OUTCOMES}
        for item in unit_outcomes:
            derived[item["outcome"]] += 1
        if counts != derived:
            raise SummaryError("summary outcome counts contradict unit_outcomes")
    return counts


def build(results_dir, report, metrics, input_evidence, plan, role, run_id, fault=None,
          context=None, commit=True):
    """一次构造最终 schema4；`commit=True` 立即原子发布，controller 用 `commit=False`
    先写诊断/生命周期记录，再把 `publish` 作为唯一正式提交点。"""
    if role not in RUN_ROLES:
        raise SummaryError(f"summary role invalid: {role!r}")
    if not isinstance(report, dict) or not isinstance(report.get("counts"), dict):
        raise SummaryError("summary report is malformed")
    counts = report["counts"]
    gate = report.get("gate")
    if not isinstance(gate, dict):
        raise SummaryError("summary gate report is missing")
    repro = report.get("repro") or {}
    cleanup_state = report.get("cleanup_state")
    if cleanup_state not in ("cleaned", "unknown", "failed"):
        raise SummaryError("summary cleanup_state is invalid")
    evidence_state = report.get("evidence_state")
    if evidence_state not in ("complete", "incomplete"):
        raise SummaryError("summary evidence_state is invalid")
    unit_outcomes = _validate_unit_outcomes(report.get("unit_outcomes"))
    outcome_counts = _validate_outcome_counts(report.get("outcome_counts"), unit_outcomes)
    if unit_outcomes is not None:
        planned = [item.get("name") for item in plan.get("units") or []
                   if isinstance(item, dict)]
        if planned and {item["unit"] for item in unit_outcomes} != set(planned):
            raise SummaryError("summary unit_outcomes must cover every planned unit")
    if (outcome_counts["unverified"] or (unit_outcomes is not None
                                        and any(item["outcome"] == "unverified"
                                                for item in unit_outcomes))) \
            and evidence_state == "complete":
        raise SummaryError("summary claims complete evidence while units are unverified")
    if not isinstance(input_evidence, dict):
        raise SummaryError("summary input_evidence is missing")
    candidate_commit = _candidate_commit(plan, context)
    repro_phase_counts = _repro_phase_counts(plan, report)
    ok = bool(report.get("ok")) and cleanup_state == "cleaned" and evidence_state == "complete"
    if plan.get("fixture_deploy") == "candidate" and not candidate_commit:
        ok = False
    status = "ok" if ok else "failed"
    failure_kind = None
    if not ok:
        requested = report.get("failure_kind")
        failure_kind = "cancelled" if requested == "cancelled" else "failed"
    payload = {
        "schema_version": SUMMARY_SCHEMA,
        "run_id": run_id,
        "role": role,
        "mode": metrics["mode"] if metrics else plan.get("mode"),
        "full_mode": _number(metrics, "full_mode") if metrics else int(plan.get("full_mode") or 0),
        "fixture_deploy": metrics["fixture_deploy"] if metrics else plan.get("fixture_deploy"),
        "suite_ran": counts["suite_ran"],
        "flow_ran": counts["flow_ran"],
        "repro_ran": counts["repro_ran"],
        "units_total": counts["units_total"],
        "repro_mode": metrics["repro_mode"] if metrics else (plan.get("repro_mode") or "none"),
        "repro_groups": metrics["repro_groups"] if metrics else list(plan.get("repro_groups") or []),
        "candidate_commit": candidate_commit,
        "repro_phase_counts": repro_phase_counts,
        "jobs": _number(metrics, "effective_jobs") if metrics else 1,
        "requested_jobs": _number(metrics, "requested_jobs") if metrics else 1,
        "effective_jobs": _number(metrics, "effective_jobs") if metrics else 1,
        "execution_mode": metrics["execution_mode"] if metrics else "serial",
        "fallback_reason": metrics["fallback_reason"] if metrics else "",
        "repro_jobs": _number(metrics, "repro_jobs") if metrics else 1,
        "timing_note": "init_seconds/suite_seconds 为全部执行单元累计；total_seconds 为墙钟",
        "fail": counts["fail"],
        "legacy_debt": counts["legacy_debt"],
        "failure_owner": {"unregistered": counts["unregistered_fail"],
                          "repro": counts["repro_fail"],
                          "rows": counts["bad"],
                          "structural": counts["extra_failures"],
                          "assertion": outcome_counts["assertion_failed"],
                          "preparation": outcome_counts["preparation_failed"],
                          "execution": outcome_counts["execution_failed"],
                          "cancelled": outcome_counts["cancelled"],
                          "unverified": outcome_counts["unverified"]},
        "build_seconds": _number(metrics, "build_seconds") if metrics else 0,
        "template_seconds": _number(metrics, "template_seconds") if metrics else 0,
        "template_reused": bool(metrics.get("template_reused")) if metrics else False,
        "template_source": metrics["template_source"] if metrics else "none",
        "template_cache_hit": bool(metrics.get("template_cache_hit")) if metrics else False,
        "template_cache_key": metrics.get("template_cache_key") if metrics else None,
        "release_build": metrics.get("release_build") if metrics else None,
        "template_build_sequences": _number(metrics, "template_build_sequences") if metrics else 0,
        "pycache_root": metrics.get("pycache_root") if metrics else None,
        "init_seconds": round(_number(metrics, "init_millis") / 1000, 2) if metrics else 0.0,
        "suite_seconds": round(_number(metrics, "suite_millis") / 1000, 2) if metrics else 0.0,
        "green_seconds": _number(metrics, "green_seconds") if metrics else 0,
        "red_seconds": _number(metrics, "red_seconds") if metrics else 0,
        "total_seconds": round(_number(metrics, "total_millis") / 1000, 3) if metrics else 0.0,
        "pool_seconds": _number(metrics, "pool_seconds") if metrics else 0,
        "repro_seconds": _number(metrics, "repro_seconds") if metrics else 0,
        "startup_seconds": max(0, round((_number(metrics, "total_millis") / 1000
                                         - _number(metrics, "pool_seconds")
                                         - _number(metrics, "repro_seconds")), 3)) if metrics else 0.0,
        "repro_concurrent": bool(metrics.get("repro_concurrent")) if metrics else False,
        "budget": {
            "full_seconds_target": 60,
            "full_seconds_hard": 65,
            "measured_seconds": round(_number(metrics, "total_millis") / 1000, 3) if metrics else 0.0,
            "over_target": (_number(metrics, "total_millis") / 1000 > 60) if metrics else False,
            "over_hard": (_number(metrics, "total_millis") / 1000 > 65) if metrics else False,
        },
        "status": status,
        "failure_kind": failure_kind,
        "gate": {
            "malformed": gate.get("malformed", 0),
            "missing": gate.get("missing") or [],
            "duplicate": gate.get("duplicate") or [],
            "unexpected": gate.get("unexpected") or [],
            "bad": gate.get("bad") or [],
            "repro_fail": counts["repro_fail"],
            "extra_failures": counts["extra_failures"],
        },
        "cleanup_state": cleanup_state,
        "cleanup_report": {
            "removed": report.get("cleanup_report", {}).get("removed", []),
            "failed": report.get("cleanup_report", {}).get("failed", []),
            "not_attempted": report.get("cleanup_report", {}).get("not_attempted", []),
            "retained_paths": report.get("cleanup_report", {}).get("retained_paths", []),
        },
        "evidence_state": evidence_state,
        "reasons": report.get("reasons") or [],
        "input_evidence": input_evidence,
        "summary_publish": "published",
    }
    if unit_outcomes is not None:
        # 可选字段：独立 repro 角色没有单元，保持旧读者看到的结构。
        payload["unit_outcomes"] = unit_outcomes
    if fault == "summary-exception":
        raise SummaryError("injected summary build/publish exception")
    payload["summary_path"] = str(Path(results_dir) / "summary.json")
    if commit:
        publish(results_dir, payload, fault=fault)
    return payload


def publish(results_dir, payload, fault=None):
    """同目录临时文件 → fsync → replace → 完整读回相等；任一步失败即拒绝。"""
    path = Path(results_dir) / "summary.json"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=results_dir,
                                         prefix=".summary-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except OSError as exc:
        raise SummaryError(f"summary publish failed: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    try:
        readback = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SummaryError(f"summary readback failed: {exc}") from exc
    if fault == "summary-malformed":
        # 受控故障：落一个不完整对象，读回比对必须拒绝，且调用方不得签成功。
        Path(path).write_text('{"schema_version": 3}\n', encoding="utf-8")
        raise SummaryError("injected malformed summary")
    if readback != payload:
        raise SummaryError("summary readback does not equal the published payload")
    return path


def historical_conclusion(results_dir):
    """历史/新版整次结论的**唯一**读取器（盘点与迁移核对用）。

    - 新版：summary schema 4 `status=ok` 必须同时有同代 owner/run-state（finished、
      cleanup=cleaned、evidence=complete）与同代控制记录的清理/证据事实；
    - 历史：summary schema 3 + 控制 schema 1（旧事实按原意读） 的 `success=true`/`summary.status=ok` + run-state
      schema 1 的 finished/cleaned/complete 一致才算通过；
    - 字段缺失、不可读或跨代不一致一律 `unknown`（不猜、不把旧成功当新版提交）。
    """
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import resource_lifecycle as lifecycle

    root = str(results_dir)
    try:
        owner = lifecycle.classify_owner(root)
        state = lifecycle.classify_run_state(root)
    except lifecycle.LifecycleError as exc:
        return {"status": "unknown", "reason": str(exc), "schema_version": None}
    try:
        summary = _json_object(_read_bytes(Path(root) / "summary.json", "summary"), "summary")
    except (SummaryError, OSError) as exc:
        return {"status": "unknown", "reason": f"summary unreadable: {exc}",
                "schema_version": None}
    schema = summary.get("schema_version")
    if isinstance(schema, bool) or schema not in (*LEGACY_SUMMARY_SCHEMAS, SUMMARY_SCHEMA):
        return {"status": "unknown", "reason": f"unknown summary schema: {schema!r}",
                "schema_version": schema}
    run_id = summary.get("run_id")
    if owner["kind"] != "schema2" or owner["payload"].get("intent") != "execution":
        return {"status": "unknown", "reason": "results root has no execution owner",
                "schema_version": schema}
    if state["kind"] != "finished" or state["payload"].get("run_id") != run_id:
        return {"status": "unknown", "reason": "run-state is not this generation's finish",
                "schema_version": schema}
    if owner["payload"].get("run_id") != run_id:
        return {"status": "unknown", "reason": "owner/summary run_id mismatch",
                "schema_version": schema}
    control = None
    receipt_path = Path(root) / ".runner.json"
    try:
        control = _json_object(_read_bytes(receipt_path, "control receipt"), "control receipt")
    except (SummaryError, OSError):
        control = None
    status = summary.get("status")
    if status == "failed":
        return {"status": "failed", "reason": "", "schema_version": schema,
                "failure_kind": summary.get("failure_kind")}
    if status != "ok":
        return {"status": "unknown", "reason": f"summary status invalid: {status!r}",
                "schema_version": schema}
    facts = {"cleanup_state": state["payload"].get("cleanup_state"),
             "evidence_state": state["payload"].get("evidence_state")}
    if facts != {"cleanup_state": "cleaned", "evidence_state": "complete"}:
        return {"status": "unknown", "reason": "run-state facts do not support success",
                "schema_version": schema}
    record = (control or {}).get("control") or {}
    record_schema = record.get("schema_version")
    if schema == SUMMARY_SCHEMA:
        if record_schema != 2:
            return {"status": "unknown", "reason": "control record does not match summary schema",
                    "schema_version": schema}
        cleanup_state = ((record.get("cleanup") or {}).get("cleanup_state"))
        evidence_state = ((record.get("assessment") or {}).get("evidence_state"))
        if cleanup_state != "cleaned" or evidence_state != "complete":
            return {"status": "unknown",
                    "reason": "control facts do not support success",
                    "schema_version": schema}
    else:
        if record_schema != 1 or record.get("success") is not True or \
                (record.get("summary") or {}).get("status") != "ok":
            return {"status": "unknown",
                    "reason": "historical control record does not confirm success",
                    "schema_version": schema}
    return {"status": "ok", "reason": "", "schema_version": schema}


# ---- CLI -------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description="测量交接（schema1）与摘要唯一发布（schema4）")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--role", choices=RUN_ROLES)
    parser.add_argument("--plan-file")
    parser.add_argument("--context-file")
    parser.add_argument("--repro-results")
    parser.add_argument("--bundle-sha256")
    parser.add_argument("--bundle-size")
    parser.add_argument("--measurements", help="测量 JSON（write-metrics 输入）")
    parser.add_argument("--write-metrics", action="store_true")
    parser.add_argument("--fault", default=None)
    args = parser.parse_args(argv)
    if not args.write_metrics:
        parser.error("only --write-metrics is supported; publication happens in the controller")
    if not args.run_id or not args.role or not args.plan_file or not args.measurements:
        parser.error("--write-metrics requires --run-id/--role/--plan-file/--measurements")
    try:
        measurements = _json_object(Path(args.measurements).read_bytes(), "measurements")
        path = write_metrics(args.results_dir, args.run_id, args.role, args.plan_file,
                             measurements, args.context_file, args.repro_results,
                             args.bundle_sha256, args.bundle_size, fault=args.fault)
    except (SummaryError, OSError) as exc:
        print(f"METRICS-FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"METRICS-WRITTEN: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())