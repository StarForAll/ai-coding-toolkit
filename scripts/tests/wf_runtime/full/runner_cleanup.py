#!/usr/bin/env python3
"""runner_cleanup.py — 聚合每个命令结果的 cleanup 结论（run_all 的唯一判定点）。

命令级监督失败（G/S 丢失）时，`execution.py` 会把 `supervision.cleanup_state` 写成
`unknown`/`failed` 并以非零返回。shell 不能只看自己的夹具删除结果：**命令级未知**
必须保留现场、不得删除仍可能被使用的夹具。本模块扫描结果 JSON（单元 `*.test.log.json`
与外层 `.runner.json`），输出可归因的未知清单；读取失败按“未知”计，不折成已清理。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shlex
import sys


def unknown_units(results_dir):
    findings = []
    paths = sorted(glob.glob(os.path.join(results_dir, "*.test.log.json")))
    outer = os.path.join(results_dir, ".runner.json")
    if os.path.isfile(outer):
        paths.append(outer)
    for path in paths:
        name = os.path.basename(path)
        if name == ".runner.json":
            label = "wf-runner"
        else:
            label = name[:-len(".test.log.json")]
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as exc:
            findings.append({"unit": label, "state": "unreadable", "detail": str(exc)})
            continue
        supervision = (payload or {}).get("supervision") or {}
        state = supervision.get("cleanup_state")
        if state and state != "cleaned":
            findings.append({"unit": label, "state": state,
                             "reason": supervision.get("termination_reason")
                             or payload.get("reason") or ""})
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--format", default="sh", choices=("sh", "json"))
    args = parser.parse_args(argv)
    findings = unknown_units(args.results_dir)
    if args.format == "json":
        print(json.dumps({"unknown": findings, "count": len(findings)},
                         ensure_ascii=False, sort_keys=True))
    else:
        print("CLEANUP_UNKNOWN_COUNT=" + str(len(findings)))
        print("CLEANUP_UNKNOWN=" + shlex.quote(" ".join(
            f"{item['unit']}:{item['state']}" for item in findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
