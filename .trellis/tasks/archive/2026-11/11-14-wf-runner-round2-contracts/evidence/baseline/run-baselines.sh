#!/bin/bash
cd /home/xzc/projects/personal/ai-coding-toolkit || exit 1
E=/tmp/wf-evidence-baseline
run() {
  local name=$1; shift
  echo "=== $name start $(date +%T) ==="
  WF_RESULTS_DIR="$E/$name" bash scripts/tests/wf_runtime/full/run_all.sh "$@" > "$E/$name.console.log" 2>&1
  echo "=== $name rc=$? $(date +%T) ==="
}
run run1 --full --repro green
run run2 --full --repro green
WF_SUITES=cp2_tests run cp2
WF_SUITES=r67_tests run r67
run serial --full --repro green --serial
echo "=== baselines done $(date +%T) ==="
