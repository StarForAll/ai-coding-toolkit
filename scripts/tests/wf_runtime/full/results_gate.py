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
    """**只读**结构校验：不写 state、不恢复缓存；输出结构报告与机器汇总。

    writer 是父 shell 启动的独立子进程；本函数报告的结构是否成立决定可否启动它。
    bundle 是唯一冻结来源，与 R 传入的初始 digest/长度比对。默认 bundle 与显式
    `--bundle` 走同一解析过程（不依赖环境变量才能工作）。
    """
    root = Path(root)
    bundle_file = Path(bundle_path or os.environ.get('WF_REPRO_INPUTS_FILE') or (root / 'inputs.json'))
    try:
        data = bundle_file.read_bytes()
    except OSError as exc:
        print(f'REPRO-RESULTS-INVALID: bundle unreadable: {exc}', file=sys.stderr)
        print(f'REPRO_STRUCTURAL_OK=0')
        return 1
    sha = hashlib.sha256(data).hexdigest()
    structural = True
    if expected_sha and sha != expected_sha:
        print('REPRO-BUNDLE-CHANGED: digest', file=sys.stderr)
        structural = False
    if expected_size is not None and str(len(data)) != str(expected_size):
        print('REPRO-BUNDLE-CHANGED: size', file=sys.stderr)
        structural = False
    try:
        bundle = json.loads(data)
        if not isinstance(bundle, dict):
            raise ValueError('bundle must be a JSON object')
        bundle['__sha256'] = sha
        report = repro_select.validate_repro(str(root), bundle)
    except (ValueError, TypeError, KeyError, repro_select.SelectError) as exc:
        print(f'REPRO-RESULTS-INVALID: {exc}', file=sys.stderr)
        print('REPRO_STRUCTURAL_OK=0')
        return 1
    expected = report['expected']
    passed = [case for case in expected if report['records'].get(case, {}).get('verified') is True]
    failed = len(expected) - len(passed) + len(report['malformed']) + len(report['missing'])
    if report['malformed'] or report['missing']:
        structural = False
    print(f'REPRO_TOTAL={len(expected)}')
    print(f'REPRO_PASSED={len(passed)}')
    print(f'REPRO_FAILED={failed}')
    for phase in ('green', 'red'):
        seconds = 0
        for record in report['records'].values():
            value = record.get(phase + '_seconds', 0)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                structural = False
                continue
            seconds += value
        print(f'REPRO_{phase.upper()}_SECONDS={int(seconds)}')
    print('REPRO_BUNDLE_SHA256=' + sha)
    print('REPRO_BUNDLE_SIZE=' + str(len(data)))
    if report['malformed']:
        print('REPRO_MALFORMED=' + ' '.join(report['malformed']))
    if report['missing']:
        print('REPRO_MISSING=' + ' '.join(report['missing']))
    print('REPRO_ELIGIBLE=' + ' '.join(passed))
    print(f'REPRO_STRUCTURAL_OK={1 if structural else 0}')
    return 0 if failed == 0 and structural else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="套件结果行完整性判定")
    parser.add_argument("--lines")
    parser.add_argument("--repro-results")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--bundle-sha256", default=None)
    parser.add_argument("--bundle-size", default=None)
    parser.add_argument("--expected", default="")
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    args = parser.parse_args(argv)
    if args.repro_results:
        try:
            return repro_gate(args.repro_results, args.bundle, args.bundle_sha256, args.bundle_size)
        except (OSError, ValueError) as exc:
            print(f'REPRO-RESULTS-INVALID: {exc}', file=sys.stderr)
            return 1
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
