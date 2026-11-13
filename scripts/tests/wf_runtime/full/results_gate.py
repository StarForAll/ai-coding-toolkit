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
import json
import math
import shlex
from pathlib import Path
import sys


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


def repro_gate(root):
    """Validate one result per selected identity/mode before publishing evidence."""
    sys.path.insert(0, str(Path(__file__).parent / 'repro'))
    import repro_select
    root = Path(root)
    expected = {}
    for line in (root / 'selection.tsv').read_text().splitlines():
        case, mode = line.split('\t')
        if case in expected or mode not in ('green', 'red', 'both'):
            raise ValueError('duplicate identity or invalid mode in repro selection')
        expected[case] = mode
    if not expected:
        raise ValueError('empty repro selection')
    fingerprints = json.loads((root / 'inputs.json').read_text())
    if not isinstance(fingerprints, dict) or set(fingerprints) != set(expected):
        raise ValueError('repro input fingerprints do not match the selected cases')
    records, malformed = {}, []
    for path in sorted(root.glob('*.json')):
        if path.name in ('inputs.json', '.wf-results-owner.json'):
            continue
        try:
            record = json.loads(path.read_text())
            case = record['case']
            mode = record['mode']
            phases = ('green', 'red') if mode == 'both' else (mode,)
            if (not isinstance(case, str) or not isinstance(mode, str) or path.stem != case
                    or case in records or case not in expected or mode != expected[case]
                    or type(record.get('verified')) is not bool
                    or record.get('fingerprint') != fingerprints[case]
                    or any(record.get(p) not in ('pass', 'fail') for p in phases)
                    or record['verified'] != all(record.get(p) == 'pass' for p in phases)):
                raise ValueError('contradictory case/mode/phase result')
            for phase in ('green', 'red'):
                seconds = record.get(phase + '_seconds', 0)
                if not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds < 0:
                    raise ValueError('invalid duration')
            if record['verified']:
                sys.path.insert(0, str(Path(__file__).parent))
                import execution
                for phase in phases:
                    actual = (record.get('phases') or {}).get(phase) or {}
                    log = root / 'logs' / f'{case}.{phase}.log'
                    if (actual.get('rc') != 0 or actual.get('status') != 'passed'
                            or not execution.verdict(log, actual['rc'], 'repro')['ok']):
                        raise ValueError('phase evidence contradicts execution or log')
            records[case] = record
        except (OSError, ValueError, TypeError, KeyError):
            malformed.append(path.name)
    passed = [case for case in expected if records.get(case, {}).get('verified') is True]
    failed = len(expected) - len(passed) + len(malformed)
    if passed and not malformed:
        try:
            repro_select.commit_state(str(root))
        except (repro_select.SelectError, OSError, ValueError) as exc:
            print(f'REPRO_STATE_FAILED: {exc}')
            failed += 1
    print(f'REPRO_TOTAL={len(expected)}')
    print(f'REPRO_PASSED={len(passed)}')
    print(f'REPRO_FAILED={failed}')
    for phase in ('green', 'red'):
        seconds = sum(record.get(phase + '_seconds', 0) for record in records.values())
        print(f'REPRO_{phase.upper()}_SECONDS={int(seconds)}')
    if malformed:
        print('REPRO_MALFORMED=' + ' '.join(malformed))
    return 0 if failed == 0 else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="套件结果行完整性判定")
    parser.add_argument("--lines")
    parser.add_argument("--repro-results")
    parser.add_argument("--expected", default="")
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    args = parser.parse_args(argv)
    if args.repro_results:
        try:
            return repro_gate(args.repro_results)
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
