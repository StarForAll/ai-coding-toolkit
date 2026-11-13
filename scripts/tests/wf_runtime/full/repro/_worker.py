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
import signal
import subprocess
import sys
import time

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
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log:
        proc = subprocess.Popen([PY, os.path.join(HERE, case + ".py"), "--expect", phase],
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            rc = proc.wait(timeout=TIMEOUT)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            rc = proc.wait()
    seconds = round(time.time() - started, 2)
    try:
        with open(log_path, encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]
    except OSError:
        lines = []
    tail = lines[-1] if lines else ""
    if timed_out:
        return {"passed": False, "seconds": seconds, "rc": rc,
                "detail": f"TIMEOUT after {TIMEOUT}s", "timed_out": True}
    passed = rc == 0 and tail.startswith("PASS")
    return {"passed": passed, "seconds": seconds, "rc": rc, "detail": tail, "timed_out": False}


def main(argv):
    if len(argv) != 2:
        print("usage: _worker.py <case> <green|both|red>", file=sys.stderr)
        return 2
    case, mode = argv
    os.makedirs(results_dir(), exist_ok=True)
    record = {"case": case, "mode": mode, "green": "skip", "red": "skip",
              "green_seconds": 0.0, "red_seconds": 0.0, "detail": "", "verified": False}
    details = []
    ok = True
    if mode in ("green", "both"):
        green = run_phase(case, "green")
        record["green"] = "pass" if green["passed"] else "fail"
        record["green_seconds"] = green["seconds"]
        ok = ok and green["passed"]
        details.append(f"green: {green['detail']}")
    if mode in ("red", "both"):
        red = run_phase(case, "red")
        record["red"] = "pass" if red["passed"] else "fail"
        record["red_seconds"] = red["seconds"]
        ok = ok and red["passed"]
        details.append(f"red: {red['detail']}")
    record["verified"] = bool(ok)
    record["duration"] = round(record["green_seconds"] + record["red_seconds"], 2)
    record["detail"] = "; ".join(details)
    path = os.path.join(results_dir(), case + ".json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)
    if ok:
        print(f"ok   {case} [{mode}]")
        return 0
    print(f"FAIL {case} [{mode}] {record['detail'][:200]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
