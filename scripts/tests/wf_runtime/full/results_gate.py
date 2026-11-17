#!/usr/bin/env python3
"""results_gate.py — 套件结果行的完整性判定（`run_all.sh` 的唯一实现）。

规则（延续第四轮复审 R4-3 的口径，不因重构放宽）：
- 每行必须正好 5 段：`suite<TAB>rc<TAB>seconds<TAB>ok|bad<TAB>末行`；
- `rc` 必须是整数；状态只允许 `ok`/`bad`；
- 计划内的套件必须**恰好一行**：缺行、重复行都算失败；
- 计划外的行（unexpected）也算失败——否则“跑错套件”会被静默吞掉。

用法（bash 侧把输出 eval 成变量）：
    results_gate.py --lines <file> --expected "<suite> <suite> ..." [--format sh|json]
输出变量：GATE_OK / GATE_MALFORMED / GATE_MISSING / GATE_DUPLICATE / GATE_UNEXPECTED / GATE_BAD / GATE_UNIQUE
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
from pathlib import Path
import sys

# 模块级导入依赖：坏 bundle/不可读路径也必须给出**稳定归因**，不能在 except 子句里
# NameError 二次崩溃（正常路径与显式路径共用同一解析过程）。
sys.path.insert(0, str(Path(__file__).resolve().parent / "repro"))
import repro_select  # noqa: E402


def gate(path, expected):
    expected_list = [item for item in expected.split() if item]
    malformed = 0
    rows = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        lines = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 5 or not parts[1].removeprefix("-").isdigit() or parts[3] not in ("ok", "bad"):
            malformed += 1
            continue
        try:
            duration = float(parts[2])
        except ValueError:
            duration = float("nan")
        if not math.isfinite(duration) or duration < 0:
            malformed += 1
            continue
        status = parts[3]
        if int(parts[1]) != 0 or not parts[4].strip():
            status = "bad"
        rows.setdefault(parts[0], []).append(status)
    missing = [name for name in expected_list if name not in rows]
    duplicate = sorted(name for name, values in rows.items() if len(values) > 1)
    unexpected = sorted(name for name in rows if name not in expected_list)
    bad = sorted(name for name, values in rows.items() if "bad" in values)
    unique = len([name for name in rows if name in expected_list])
    ok = not (malformed or missing or duplicate or unexpected or bad)
    return {
        "ok": ok,
        "malformed": malformed,
        "missing": missing,
        "duplicate": duplicate,
        "unexpected": unexpected,
        "bad": bad,
        "unique": unique,
    }


def repro_gate(root, bundle_path=None, expected_sha=None, expected_size=None):
    """**只读**结构校验的 CLI 投影：不写 state、不恢复缓存；报告来自 `repro_report`。"""
    report = repro_report(root, bundle_path, expected_sha, expected_size)
    if not report.get("bundle_sha256"):
        print(f'REPRO-RESULTS-INVALID: {report.get("reason")}', file=sys.stderr)
        print('REPRO_STRUCTURAL_OK=0')
        return 1
    if report.get("reason"):
        print(f'REPRO-RESULTS-INVALID: {report["reason"]}', file=sys.stderr)
    expected = report.get("passed") or []
    failed = int(report.get("failed") or 0)
    print(f'REPRO_TOTAL={int(report.get("total") or 0)}')
    print(f'REPRO_PASSED={len(expected) if report.get("total") else 0}')
    print(f'REPRO_FAILED={failed}')
    print(f'REPRO_GREEN_SECONDS={int(report.get("green_seconds") or 0)}')
    print(f'REPRO_RED_SECONDS={int(report.get("red_seconds") or 0)}')
    print('REPRO_BUNDLE_SHA256=' + report["bundle_sha256"])
    print('REPRO_BUNDLE_SIZE=' + str(report.get("bundle_size") or 0))
    if report.get("malformed"):
        print('REPRO_MALFORMED=' + ' '.join(report["malformed"]))
    if report.get("missing"):
        print('REPRO_MISSING=' + ' '.join(report["missing"]))
    print('REPRO_ELIGIBLE=' + ' '.join(expected))
    print(f'REPRO_STRUCTURAL_OK={1 if report.get("structural") else 0}')
    return 0 if report.get("ok") else 1


def repro_report(root, bundle_path=None, bundle_sha=None, bundle_size=None):
    """结构化 repro 结构报告：唯一校验点（gate/writer/controller 共用）。"""
    root = Path(root)
    bundle_file = Path(bundle_path or os.environ.get('WF_REPRO_INPUTS_FILE') or (root / 'inputs.json'))
    try:
        data = bundle_file.read_bytes()
    except OSError as exc:
        return {"enabled": True, "ok": False, "reason": f"bundle unreadable: {exc}"}
    sha = hashlib.sha256(data).hexdigest()
    structural = True
    reasons = []
    if bundle_sha and sha != bundle_sha:
        structural = False
        reasons.append("bundle digest changed")
    if bundle_size is not None and str(len(data)) != str(bundle_size):
        structural = False
        reasons.append("bundle size changed")
    try:
        bundle = json.loads(data)
        if not isinstance(bundle, dict):
            raise ValueError('bundle must be a JSON object')
        bundle['__sha256'] = sha
        report = repro_select.validate_repro(str(root), bundle)
    except (ValueError, TypeError, KeyError, repro_select.SelectError) as exc:
        return {"enabled": True, "ok": False, "reason": str(exc),
                "bundle_sha256": sha, "bundle_size": len(data)}
    expected = report['expected']
    passed = [case for case in expected if report['records'].get(case, {}).get('verified') is True]
    failed = len(expected) - len(passed) + len(report['malformed']) + len(report['missing'])
    if report['malformed'] or report['missing']:
        structural = False
    seconds = {}
    for phase in ('green', 'red'):
        total = 0
        for record in report['records'].values():
            value = record.get(phase + '_seconds', 0)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or \
                    not math.isfinite(value) or value < 0:
                structural = False
                reasons.append(f"{phase} seconds invalid")
                continue
            total += value
        seconds[phase] = int(total)
    ok = failed == 0 and structural
    return {"enabled": True, "ok": ok, "structural": structural,
            "total": len(expected), "passed": passed, "failed": failed,
            "malformed": report['malformed'], "missing": report['missing'],
            "green_seconds": seconds['green'], "red_seconds": seconds['red'],
            "bundle_sha256": sha, "bundle_size": len(data),
            "bundle_path": str(bundle_file), "reasons": reasons}


def assess_run_results(plan_path, lines_path, repro_results=None, bundle_sha=None,
                       bundle_size=None, known_legacy=""):
    """纯判定：冻结 plan × 五列 lines × 本代 repro 报告 → 最终计数/门禁/债务。

    controller 与内层诊断共用这一份实现；不采信 shell 的 fail/extra 数字，也不从 metrics
    读取 gate/cleanup/成功结论。
    """
    with open(plan_path, encoding="utf-8") as handle:
        plan = json.load(handle)
    if not isinstance(plan, dict):
        raise ValueError("frozen plan must be a JSON object")
    units = plan.get("units")
    if not isinstance(units, list) or not units:
        raise ValueError("frozen plan has no units")
    names, kinds = [], {}
    for unit in units:
        if not isinstance(unit, dict) or not isinstance(unit.get("name"), str):
            raise ValueError("frozen plan unit is malformed")
        if unit["name"] in kinds:
            raise ValueError(f"frozen plan repeats unit {unit['name']}")
        names.append(unit["name"])
        kinds[unit["name"]] = unit.get("kind")
    gate_result = gate(lines_path, " ".join(names))
    repro = (repro_report(repro_results, bundle_sha=bundle_sha, bundle_size=bundle_size)
             if repro_results else {"enabled": False, "ok": True, "total": 0, "failed": 0,
                                    "green_seconds": 0, "red_seconds": 0})
    suite_ran = sum(1 for name in names if kinds.get(name) in ("suite", "candidate"))
    flow_ran = sum(1 for name in names if kinds.get(name) in ("flow", "extra"))
    repro_ran = int(repro.get("total") or 0) if repro.get("enabled") else 0
    bad = len(gate_result["bad"])
    extra = (gate_result["malformed"] + len(gate_result["missing"])
             + len(gate_result["duplicate"]) + len(gate_result["unexpected"]))
    repro_fail = int(repro.get("failed") or 0) if repro.get("enabled") else 0
    # 已知技术债：清单只在参与本次计划的单元上判定；转绿/缺失都是必须销账的账目问题。
    rows = {}
    try:
        with open(lines_path, encoding="utf-8", errors="replace") as handle:
            for line in handle.read().splitlines():
                parts = line.split("\t")
                if len(parts) == 5:
                    rows.setdefault(parts[0], parts[3])
    except OSError:
        pass
    legacy = [name for name in known_legacy.split() if name]
    debt_failed = [name for name in legacy if name in names and rows.get(name) == "bad"]
    debt_fixed = [name for name in legacy if name in names and rows.get(name) == "ok"]
    debt_missing = [name for name in legacy if name in names and name not in rows]
    fail = bad + extra + repro_fail
    debt = len(debt_failed)
    unregistered_fail = fail - debt
    reasons = []
    if not gate_result["ok"]:
        reasons.append("result rows do not match the frozen plan")
    if repro.get("enabled") and not repro.get("ok"):
        reasons.append("repro report is not complete: " + (repro.get("reason") or "failed"))
    if debt_fixed or debt_missing:
        reasons.append("legacy bookkeeping needs reconciliation: fixed=" + " ".join(debt_fixed)
                       + " missing=" + " ".join(debt_missing))
    return {
        "ok": bool(gate_result["ok"] and repro.get("ok") and unregistered_fail == 0
                   and not debt_fixed and not debt_missing),
        "gate": gate_result,
        "repro": repro,
        "counts": {
            "suite_ran": suite_ran, "flow_ran": flow_ran, "repro_ran": repro_ran,
            "units_total": suite_ran + flow_ran + repro_ran, "fail": fail,
            "bad": bad, "extra_failures": extra, "repro_fail": repro_fail,
            "legacy_debt": debt, "unregistered_fail": unregistered_fail,
            "debt_failed": debt_failed, "debt_fixed": debt_fixed, "debt_missing": debt_missing,
        },
        "reasons": reasons,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="套件结果行完整性判定")
    parser.add_argument("--lines")
    parser.add_argument("--repro-results")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--bundle-sha256", default=None)
    parser.add_argument("--bundle-size", default=None)
    parser.add_argument("--expected", default="")
    parser.add_argument("--assess-run", action="store_true",
                        help="冻结 plan × lines × repro 的最终计数/门禁（controller 与诊断共用）")
    parser.add_argument("--plan-file", default=None)
    parser.add_argument("--known-legacy", default="")
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    args = parser.parse_args(argv)
    if args.repro_results:
        try:
            return repro_gate(args.repro_results, args.bundle, args.bundle_sha256, args.bundle_size)
        except (OSError, ValueError) as exc:
            print(f'REPRO-RESULTS-INVALID: {exc}', file=sys.stderr)
            return 1
    if args.assess_run:
        if not args.plan_file or not args.lines:
            parser.error('--assess-run requires --plan-file and --lines')
        try:
            report = assess_run_results(args.plan_file, args.lines,
                                        args.repro_results, args.bundle_sha256,
                                        args.bundle_size, args.known_legacy)
        except (OSError, ValueError) as exc:
            print(f"ASSESS-RUN-FAILED: {exc}", file=sys.stderr)
            return 1
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            counts = report["counts"]
            print(f"ASSESS_OK={1 if report['ok'] else 0}")
            print(f"ASSESS_UNITS_TOTAL={counts['units_total']}")
            print(f"ASSESS_FAIL={counts['fail']}")
            print(f"ASSESS_LEGACY_DEBT={counts['legacy_debt']}")
            print("ASSESS_REASONS=" + shlex.quote("; ".join(report["reasons"])))
            print("ASSESS_MISSING=" + shlex.quote(" ".join(report["gate"].get("missing") or [])))
            print("ASSESS_BAD=" + shlex.quote(" ".join(report["gate"].get("bad") or [])))
            print(f"ASSESS_SUITE={counts['suite_ran']} ASSESS_FLOW={counts['flow_ran']} "
                  f"ASSESS_REPRO={counts['repro_ran']}")
        return 0 if report["ok"] else 1
    if not args.lines:
        parser.error('--lines or --repro-results is required')
    result = gate(args.lines, args.expected)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["ok"] else 1
    print(f"GATE_OK={1 if result['ok'] else 0}")
    print(f"GATE_MALFORMED={result['malformed']}")
    print(f"GATE_UNIQUE={result['unique']}")
    for name in ("missing", "duplicate", "unexpected", "bad"):
        print("GATE_" + name.upper() + "=" + shlex.quote(" ".join(result[name])))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
