#!/usr/bin/env python3
"""_worker.py — 单个 repro 用例的执行单元（由 `repro/run.sh` 调度）。

职责边界：
- 只写自己的 `results/<case>.json` 与 `logs/<case>.<mode>.log`，**不碰 `repro-state.json`**
  （状态只由父进程在汇总校验通过后原子更新）；
- 单用例超时结束整个进程组，并记失败（不留下挂起进程）；
- red 面只有“目标断言变红”才算通过：前置失败、注入后仍绿都记失败并把原因写进结果。

用法：`python3 _worker.py <case> <green|both|red>`
"""
from __future__ import annotations

import json
import os
import sys
import re
import shutil
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import execution
import repro_select

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.environ.get("PY") or sys.executable
TIMEOUT = int(os.environ.get("WF_REPRO_TIMEOUT") or 120)


def results_dir():
    root = os.environ.get("WF_REPRO_RESULTS")
    if not root:
        raise SystemExit("WF_REPRO_RESULTS is not set")
    return root


def run_phase(case, phase):
    """跑一个面（green/red），返回 dict(passed, seconds, detail, rc)。"""
    log_dir = os.path.join(results_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{case}.{phase}.log")
    temporary = tempfile.mkdtemp(prefix=f'{case}-{phase}-', dir=log_dir)
    try:
        execution_result = execution.run([PY, os.path.join(HERE, case + ".py"), "--expect", phase],
                                         log_path, timeout=TIMEOUT,
                                         env={**os.environ, 'TMPDIR': temporary})
    finally:
        if os.environ.get('WF_REPRO_KEEP') != '1':
            shutil.rmtree(temporary)
    check = execution.verdict(log_path, execution_result["rc"], "repro")
    return {"passed": check["ok"], "seconds": execution_result["seconds"],
            "rc": execution_result["rc"], "detail": execution_result["reason"] or check["tail"],
            "execution": execution_result}


def main(argv):
    if len(argv) != 2:
        print("usage: _worker.py <case> <green|both|red>", file=sys.stderr)
        return 2
    case, mode = argv
    if mode not in ("green", "red", "both") or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", case):
        return 2
    current = repro_select.input_fingerprint(case)
    frozen = json.loads(os.environ.get("REPRO_INPUTS_JSON", "{}"))
    fingerprint = frozen.get(case, current)
    if fingerprint != current:
        print(f"FAIL {case}: inputs changed before execution")
        return 1
    os.makedirs(results_dir(), exist_ok=True)
    record = {"case": case, "mode": mode, "green": "skip", "red": "skip",
              "green_seconds": 0.0, "red_seconds": 0.0, "detail": "", "verified": False}
    record["fingerprint"] = fingerprint
    record["phases"] = {}
    details = []
    ok = True
    if mode in ("green", "both"):
        green = run_phase(case, "green")
        record["phases"]["green"] = green["execution"]
        record["green"] = "pass" if green["passed"] else "fail"
        record["green_seconds"] = green["seconds"]
        ok = ok and green["passed"]
        details.append(f"green: {green['detail']}")
    if mode in ("red", "both"):
        red = run_phase(case, "red")
        record["phases"]["red"] = red["execution"]
        record["red"] = "pass" if red["passed"] else "fail"
        record["red_seconds"] = red["seconds"]
        ok = ok and red["passed"]
        details.append(f"red: {red['detail']}")
    if repro_select.input_fingerprint(case) != fingerprint:
        ok = False
        details.append("inputs changed during execution; evidence rejected")
    record["verified"] = bool(ok)
    record["duration"] = round(record["green_seconds"] + record["red_seconds"], 2)
    record["detail"] = "; ".join(details)
    path = os.path.join(results_dir(), case + ".json")
    execution.write_json(path, record)
    if ok:
        print(f"ok   {case} [{mode}]")
        return 0
    print(f"FAIL {case} [{mode}] {record['detail'][:200]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
