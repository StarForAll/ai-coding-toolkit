#!/usr/bin/env python3
"""results_summary.py — 运行摘要的唯一发布点（原子写 + 读回校验）。

为什么独立：`run_all.sh` 以前用内联 heredoc 直接 `open(w)` 写 summary，写失败仍然
继续到 `GATE-OK`。本模块把“成功”闭合为：冻结 plan/context 与已校验结果一致 →
同目录临时文件 → flush/fsync → replace → 读回必需字段与 payload 相等 → 才返回 0。

输入：

- `--plan-file`：lease 阶段冻结的 final plan（字节与 context 的 plan_sha256/size 绑定）；
- `--context-file`：controlled 阶段的 release-context（schema 2）；
- `--lines`：主池五列结果行（results_gate 已判过）；
- `--metrics`：shell 采集的计时/并发/repro 计数等**非判定事实**；
- `--results-dir`：summary.json 的发布目录。

计数从实际结果集 × 注册 kind 派生（不采信环境里的汇总数字）；任何缺行/重行/畸形行都
拒绝发布。repro 计数来自 repro 入口自己的机器汇总，只做非负有限性校验。
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

SCHEMA_VERSION = 2
INT_FIELDS = ("suite_ran", "flow_ran", "repro_ran", "units_total", "jobs", "requested_jobs",
              "effective_jobs", "repro_jobs", "fail", "legacy_debt", "build_seconds",
              "template_seconds", "init_millis", "suite_millis", "green_seconds",
              "red_seconds", "total_millis", "pool_seconds", "repro_seconds",
              "template_build_sequences")
FLOAT_FIELDS = ("total_seconds", "init_seconds", "suite_seconds", "startup_seconds")
REQUIRED_FIELDS = ("schema_version", "mode", "fixture_deploy", "suite_ran", "flow_ran",
                   "repro_ran", "units_total", "fail", "status", "gate", "cleanup_state")


class SummaryError(Exception):
    """可预期的拒绝（非零退出；调用方不得打印 GATE-OK）。"""


def _read_json(path, label):
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise SummaryError(f"{label} unreadable: {exc}") from exc
    try:
        value = json.loads(data)
    except ValueError as exc:
        raise SummaryError(f"{label} is not JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SummaryError(f"{label} must be a JSON object")
    return value, data


def _number(payload, key, integer=True, default=0):
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SummaryError(f"metric {key} must be a number, got {value!r}")
    if integer and value != int(value):
        raise SummaryError(f"metric {key} must be an integer, got {value!r}")
    if not math.isfinite(float(value)) or value < 0:
        raise SummaryError(f"metric {key} must be finite and non-negative, got {value!r}")
    return int(value) if integer else float(value)


def _plan_units(plan):
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


def _result_lines(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SummaryError(f"result lines unreadable: {exc}") from exc
    rows, malformed, seen = {}, [], set()
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 5 or not parts[1].removeprefix("-").isdigit() \
                or parts[3] not in ("ok", "bad"):
            malformed.append(line[:120])
            continue
        try:
            duration = float(parts[2])
        except ValueError:
            duration = float("nan")
        if not math.isfinite(duration) or duration < 0:
            malformed.append(line[:120])
            continue
        name = parts[0]
        if name in seen:
            malformed.append(f"duplicate result row: {name}")
            continue
        seen.add(name)
        status = parts[3] if int(parts[1]) == 0 and parts[4].strip() else "bad"
        rows[name] = {"rc": int(parts[1]), "seconds": duration, "status": status,
                      "tail": parts[4]}
    return rows, malformed


def build(results_dir, plan_path, context_path, lines_path, metrics_path):
    results_dir = Path(results_dir)
    if not results_dir.is_dir():
        raise SummaryError(f"results dir does not exist: {results_dir}")
    plan, plan_bytes = _read_json(plan_path, "frozen plan")
    context, _ = _read_json(context_path, "release context")
    digest = hashlib.sha256(plan_bytes).hexdigest()
    if context.get("plan_sha256") != digest:
        raise SummaryError("release context does not bind the frozen plan digest")
    if str(context.get("plan_size")) != str(len(plan_bytes)):
        raise SummaryError("release context does not bind the frozen plan size")
    names, kinds = _plan_units(plan)
    rows, malformed = _result_lines(lines_path)
    if malformed:
        raise SummaryError("malformed result rows: " + "; ".join(malformed[:5]))
    missing = [name for name in names if name not in rows]
    unexpected = sorted(name for name in rows if name not in names)
    if missing or unexpected:
        raise SummaryError("result rows do not match the frozen plan: missing="
                           + " ".join(missing[:10]) + " unexpected=" + " ".join(unexpected[:10]))
    metrics, _ = _read_json(metrics_path, "metrics")
    for key in INT_FIELDS:
        _number(metrics, key)
    for key in FLOAT_FIELDS:
        _number(metrics, key, integer=False)
    suite_ran = sum(1 for name in names if kinds.get(name) in ("suite", "candidate"))
    flow_ran = sum(1 for name in names if kinds.get(name) in ("flow", "extra"))
    bad = sum(1 for row in rows.values() if row["status"] != "ok")
    extra_failures = _number(metrics, "extra_failures")
    fail = bad + extra_failures
    groups = metrics.get("repro_groups") or []
    if not isinstance(groups, list) or any(not isinstance(item, str) for item in groups):
        raise SummaryError("metric repro_groups must be a list of strings")
    total_seconds = _number(metrics, "total_seconds", integer=False)
    pool_seconds = _number(metrics, "pool_seconds")
    repro_seconds = _number(metrics, "repro_seconds")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": metrics.get("mode") or plan.get("mode"),
        "full_mode": _number(metrics, "full_mode") if "full_mode" in metrics else int(plan.get("full_mode") or 0),
        "fixture_deploy": metrics.get("fixture_deploy") or plan.get("fixture_deploy"),
        "suite_ran": suite_ran,
        "flow_ran": flow_ran,
        "repro_ran": _number(metrics, "repro_ran"),
        "units_total": suite_ran + flow_ran + _number(metrics, "repro_ran"),
        "repro_mode": metrics.get("repro_mode"),
        "repro_groups": groups,
        "jobs": _number(metrics, "effective_jobs"),
        "requested_jobs": _number(metrics, "requested_jobs"),
        "effective_jobs": _number(metrics, "effective_jobs"),
        "execution_mode": metrics.get("execution_mode"),
        "fallback_reason": metrics.get("fallback_reason"),
        "repro_jobs": _number(metrics, "repro_jobs"),
        "timing_note": "init_seconds/suite_seconds 为全部执行单元累计；total_seconds 为墙钟",
        "fail": fail,
        "legacy_debt": _number(metrics, "legacy_debt"),
        "build_seconds": _number(metrics, "build_seconds"),
        "template_seconds": _number(metrics, "template_seconds"),
        "template_reused": bool(metrics.get("template_reused")),
        "template_source": metrics.get("template_source"),
        "template_cache_hit": bool(metrics.get("template_cache_hit")),
        "template_cache_key": metrics.get("template_cache_key") or None,
        "release_build": metrics.get("release_build"),
        "template_build_sequences": _number(metrics, "template_build_sequences"),
        "pycache_root": metrics.get("pycache_root"),
        "init_seconds": round(_number(metrics, "init_millis") / 1000, 2),
        "suite_seconds": round(_number(metrics, "suite_millis") / 1000, 2),
        "green_seconds": _number(metrics, "green_seconds"),
        "red_seconds": _number(metrics, "red_seconds"),
        "total_seconds": round(total_seconds, 3),
        "pool_seconds": pool_seconds,
        "repro_seconds": repro_seconds,
        "startup_seconds": max(0, round(total_seconds - pool_seconds - repro_seconds)),
        "repro_concurrent": bool(metrics.get("repro_concurrent")),
        "budget": {
            "full_seconds_target": 60,
            "full_seconds_hard": 65,
            "measured_seconds": round(total_seconds, 3),
            "over_target": total_seconds > 60,
            "over_hard": total_seconds > 65,
        },
        # 成功出口的必需事实（additive）：结构 gate、已拥有资源清理与摘要发布。
        "status": "failed" if fail else "ok",
        "gate": {
            "malformed": _number(metrics, "gate_malformed"),
            "missing": _number(metrics, "gate_missing"),
            "duplicate": _number(metrics, "gate_duplicate"),
            "unexpected": _number(metrics, "gate_unexpected"),
            "bad": bad,
            "repro_fail": _number(metrics, "repro_fail"),
            "extra_failures": extra_failures,
        },
        "cleanup_state": metrics.get("cleanup_state") or "unknown",
        "summary_publish": "pending",
    }
    path = publish(results_dir, payload)
    payload["summary_publish"] = "published"
    payload["summary_path"] = str(path)
    return payload


def publish(results_dir, payload):
    """同目录临时文件 → flush/fsync → replace → 读回校验，任一步失败即拒绝成功。"""
    path = Path(results_dir) / "summary.json"
    temporary = None
    try:
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
    for key in REQUIRED_FIELDS:
        if key not in readback:
            raise SummaryError(f"summary readback is missing {key}")
    if readback.get("units_total") != payload["units_total"]:
        raise SummaryError("summary readback does not match the published payload")
    if readback.get("status") != payload["status"]:
        raise SummaryError("summary readback status mismatch")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="运行摘要的原子发布与读回校验")
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--context-file", required=True)
    parser.add_argument("--lines", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = build(args.results_dir, args.plan_file, args.context_file, args.lines,
                        args.metrics)
    except (SummaryError, OSError) as exc:
        print(f"SUMMARY-FAILED: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({key: payload[key] for key in
                          ("schema_version", "status", "units_total", "fail", "cleanup_state",
                           "summary_path")}, ensure_ascii=False, sort_keys=True))
    else:
        print(f"SUMMARY-PUBLISHED: {payload['summary_path']} status={payload['status']} "
              f"units={payload['units_total']} fail={payload['fail']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
