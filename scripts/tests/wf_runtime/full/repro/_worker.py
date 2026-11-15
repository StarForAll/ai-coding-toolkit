#!/usr/bin/env python3
"""_worker.py — 单个 repro 用例的执行单元（由 `repro/run.sh` 调度）。

职责边界（design §5.2 / AC8）：
- 只读父进程冻结的**唯一** `inputs.json` bundle（env 只给路径），不读第二份 JSON，不回退 current；
- 只写自己的 `results/<case>.json` 与 `logs/<case>.<mode>.log`，**不碰 `repro-state.json`**
  （全局状态只由父进程启动的唯一 writer 子进程提交）；
- 结果记 bundle digest、相位与 execution fingerprint；case 缺失/模式不符/输入变化均拒绝；
- red 面只有“目标断言变红”才算通过：前置失败、注入后仍绿都记失败并写原因。

用法：`python3 _worker.py <case> <green|both|red>`
"""
from __future__ import annotations

import hashlib
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


def load_bundle():
    path = os.environ.get("WF_REPRO_INPUTS_FILE")
    if not path:
        raise SystemExit("WF_REPRO_INPUTS_FILE is not set（bundle 是唯一冻结来源）")
    with open(path, "rb") as handle:
        data = handle.read()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def run_phase(case, phase):
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
    bundle, bundle_sha = load_bundle()
    frozen = (bundle.get("cases") or {}).get(case)
    if not frozen:
        print(f"FAIL {case}: case missing from frozen bundle")
        return 1
    if frozen.get("mode") != mode:
        print(f"FAIL {case}: mode {mode} != frozen {frozen.get('mode')}")
        return 1
    if bundle.get("execution_context") != repro_select.execution_context():
        print(f"FAIL {case}: execution context changed before execution")
        return 1
    fingerprint = frozen["execution_fingerprint"]
    current = repro_select.input_fingerprint(case, repro_select.load_groups())
    if fingerprint != current:
        print(f"FAIL {case}: inputs changed before execution")
        return 1
    os.makedirs(results_dir(), exist_ok=True)
    record = {"case": case, "mode": mode, "green": "skip", "red": "skip",
              "green_seconds": 0.0, "red_seconds": 0.0, "detail": "", "verified": False,
              "execution_fingerprint": fingerprint, "bundle_sha256": bundle_sha, "phases": {}}
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
    if repro_select.input_fingerprint(case, repro_select.load_groups()) != fingerprint:
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
