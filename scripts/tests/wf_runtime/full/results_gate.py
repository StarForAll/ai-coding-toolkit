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
        if len(parts) != 5 or not parts[1].lstrip("-").isdigit() or parts[3] not in ("ok", "bad"):
            malformed += 1
            continue
        rows.setdefault(parts[0], []).append(parts[3])
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="套件结果行完整性判定")
    parser.add_argument("--lines", required=True)
    parser.add_argument("--expected", default="")
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    args = parser.parse_args(argv)
    result = gate(args.lines, args.expected)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["ok"] else 1
    print(f"GATE_OK={1 if result['ok'] else 0}")
    print(f"GATE_MALFORMED={result['malformed']}")
    print(f"GATE_UNIQUE={result['unique']}")
    print("GATE_MISSING=" + " ".join(result["missing"]))
    print("GATE_DUPLICATE=" + " ".join(result["duplicate"]))
    print("GATE_UNEXPECTED=" + " ".join(result["unexpected"]))
    print("GATE_BAD=" + " ".join(result["bad"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
