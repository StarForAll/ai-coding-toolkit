#!/usr/bin/env bash
# 修复的可证伪用例：一键（CI 可用）运行器。
#
# 每个用例有两个面：`--expect green`（当前树成立）与 `--expect red`（注入原缺陷后必须变红）。
# 只有 green 的"证据"无法区分"修好了"和"没修"，所以：
#   --mode both  两个面都跑（**默认**，保持兼容）；
#   --mode green 只跑当前树（T2 收口默认）；
#   --mode red   只跑注入面（断言变更/发行前的证伪检查）；
#   --mode auto  首次运行、新用例、helper/脚本/被测 payload 目标变化 → 该用例 both；未变化 → green
#                （candidate 模式遇到需要 both 会报错并提示先在 dev 模式跑 red）。
#
# 用法：
#   bash .../repro/run.sh --mode green --no-build
#   bash .../repro/run.sh --group review --mode red --no-build
#   bash .../repro/run.sh --mode auto --jobs 4
#   bash .../repro/run.sh --list
#   bash .../repro/run.sh --fixture-deploy candidate --release-root <候选仓库根> \
#        --release-ref refs/tags/wf-v0.1.2 --release-version 0.1.2 --mode green --no-build
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL="$(dirname "$HERE")"
REPO="$(cd "$FULL/../../../.." && pwd)"
PY="${PY:-/softwares/python/bin/python3}"

MODE="both"
GROUP_NAMES=()
ONLY=""
JOBS="${WF_REPRO_JOBS:-1}"
BUILD=1
DEPLOY="${WF_FIXTURE_DEPLOY:-dev}"
RELEASE_ROOT="${WF_RELEASE_ROOT:-}"
RELEASE_REF="${WF_RELEASE_REF:-}"
RELEASE_VERSION="${WF_RELEASE_VERSION:-}"
RELEASE_META="${WF_RELEASE_META:-}"
RESULTS="${WF_REPRO_RESULTS:-}"

usage() { sed -n '2,24p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --group) GROUP_NAMES+=("${2:-}"); shift 2 ;;
    --only) ONLY="${2:-}"; shift 2 ;;
    --jobs) JOBS="${2:-}"; shift 2 ;;
    --fixture-deploy) DEPLOY="${2:-}"; shift 2 ;;
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --release-ref) RELEASE_REF="${2:-}"; shift 2 ;;
    --release-version) RELEASE_VERSION="${2:-}"; shift 2 ;;
    --release-meta) RELEASE_META="${2:-}"; shift 2 ;;
    --results-dir) RESULTS="${2:-}"; shift 2 ;;
    --no-build) BUILD=0; shift ;;
    --list) MODE="__list__"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

case "$MODE" in
  green|red|both|auto|__list__) ;;
  *) echo "repro: --mode 只接受 green|red|both|auto（收到 '$MODE'）" >&2; exit 2 ;;
esac
case "$JOBS" in
  ''|*[!0-9]*) echo "repro: --jobs 必须是正整数（收到 '$JOBS'）" >&2; exit 2 ;;
esac
[ "$JOBS" -ge 1 ] || { echo "repro: --jobs 必须 >= 1" >&2; exit 2; }

group_args=()
for g in "${GROUP_NAMES[@]}"; do
  [ -n "$g" ] && group_args+=(--group "$g")
done

if [ "$MODE" = "__list__" ]; then
  "$PY" "$HERE/repro_select.py" plan --fixture-deploy "$DEPLOY" --mode both --format json \
    "${group_args[@]}" ${ONLY:+--only "$ONLY"} \
    | "$PY" -c 'import json,sys; d=json.load(sys.stdin); [print(c + chr(9) + d["modes"][c]) for c in d["cases"]]'
  exit $?
fi

# ---- 发行来源 --------------------------------------------------------------
case "$DEPLOY" in
  dev)
    if [ -n "$RELEASE_ROOT$RELEASE_REF$RELEASE_VERSION" ]; then
      echo "repro: dev 模式不接受 --release-*（候选请用 --fixture-deploy candidate）" >&2
      exit 2
    fi
    if [ "$BUILD" -eq 1 ]; then
      if ! "$PY" "$REPO/scripts/tests/wf_test_release.py" --ensure; then
        echo "BUILD-FAILED"; exit 1
      fi
    else
      if ! "$PY" "$REPO/scripts/tests/wf_test_release.py" --check; then
        echo "TEST-RELEASE-STALE: 测试发行副本缺失或过期（重建或去掉 --no-build）"
        exit 1
      fi
    fi
    read -r TEST_ROOT TEST_VERSION TEST_REF < <("$PY" "$REPO/scripts/tests/wf_test_release.py" --check --json \
      | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print(d["root"], d["version"], d["release_ref"])')
    if [ -z "${TEST_ROOT:-}" ] || [ -z "${TEST_REF:-}" ]; then
      echo "TEST-RELEASE-INVALID"; exit 1
    fi
    export WF_RELEASE_TREE="$TEST_ROOT"
    export WF_RELEASE_REF="$TEST_REF"
    export WF_RELEASE_VERSION="$TEST_VERSION"
    export WF_TEST_LIB="$TEST_ROOT/wf-release/lib"
    ;;
  candidate)
    if [ -z "$RELEASE_ROOT" ] || [ -z "$RELEASE_REF" ] || [ -z "$RELEASE_VERSION" ]; then
      echo "repro: candidate 模式需要 --release-root/--release-ref/--release-version" >&2
      exit 2
    fi
    if [ "$MODE" = "red" ] || [ "$MODE" = "both" ]; then
      echo "repro: candidate 模式只允许 --mode green|auto（red 注入针对源码，请在 dev 模式跑）" >&2
      exit 2
    fi
    if ! "$PY" "$FULL/prepare_candidate_repo.py" --check --out "$RELEASE_ROOT" \
        --version "$RELEASE_VERSION"; then
      echo "CANDIDATE-REPO-INVALID"; exit 1
    fi
    export WF_RELEASE_TREE="$RELEASE_ROOT"
    export WF_RELEASE_REF="$RELEASE_REF"
    export WF_RELEASE_VERSION="$RELEASE_VERSION"
    export WF_RELEASE_META="${RELEASE_META:-$RELEASE_ROOT.meta.json}"
    export WF_TEST_LIB="$RELEASE_ROOT/wf-release/lib"
    ;;
  *)
    echo "repro: --fixture-deploy 只接受 dev|candidate（收到 '$DEPLOY'）" >&2; exit 2 ;;
esac

# ---- 选择 ----------------------------------------------------------------
selection=$("$PY" "$HERE/repro_select.py" plan --fixture-deploy "$DEPLOY" --mode "$MODE" --format sh \
  "${group_args[@]}" ${ONLY:+--only "$ONLY"})
rc=$?
if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
eval "$selection" || { echo "SELECT-EVAL-FAILED"; exit 2; }

if [ -z "$RESULTS" ]; then
  RESULTS="${WF_REPRO_RESULTS_DIR:-$HOME/.cache/wf-test-run/repro-$MODE-$$}"
fi
mkdir -p "$RESULTS/logs"
rm -f "$RESULTS"/*.json
rm -rf "$RESULTS/logs"
mkdir -p "$RESULTS/logs"
export WF_REPRO_RESULTS="$RESULTS"
export PY

printf '%s' "$REPRO_CASES_TSV" > "$RESULTS/selection.tsv"
echo "repro: mode=$MODE deploy=$DEPLOY cases=$REPRO_CASE_COUNT jobs=$JOBS"
if [ -n "${REPRO_SKIPPED_LIST:-}" ]; then
  echo "repro: skipped_non_candidate: $REPRO_SKIPPED_LIST"
fi

# ---- 执行（worker 只写自己的结果与日志）--------------------------------------
started=$SECONDS
if [ "$JOBS" -le 1 ]; then
  while IFS=$'\t' read -r case mode; do
    [ -n "$case" ] || continue
    "$PY" "$HERE/_worker.py" "$case" "$mode"
  done <<< "$REPRO_CASES_TSV"
else
  awk -F'\t' 'NF>=2 {print $1" "$2}' "$RESULTS/selection.tsv" \
    | xargs -P "$JOBS" -n 2 "$PY" "$HERE/_worker.py"
fi
elapsed=$((SECONDS - started))

# ---- 汇总（父进程唯一写者；缺结果/重复/数字不一致都算失败）-------------------
summary=$("$PY" - "$RESULTS" "$HERE/repro_select.py" <<'PY'
import json
import os
import subprocess
import sys

results, select_py = sys.argv[1:3]
expected = []
with open(os.path.join(results, "selection.tsv"), encoding="utf-8") as handle:
    for line in handle:
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 2 and parts[0]:
            expected.append(parts[0])
records = {}
malformed = 0
for name in sorted(os.listdir(results)):
    if not name.endswith(".json"):
        continue
    path = os.path.join(results, name)
    try:
        with open(path, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        malformed += 1
        continue
    if not isinstance(record, dict) or not record.get("case"):
        malformed += 1
        continue
    records[record["case"]] = record
missing = [case for case in expected if case not in records]
extra = [case for case in records if case not in expected]
passed = [case for case in expected if case in records and records[case].get("verified")]
failed = [case for case in expected if case not in passed]
green_seconds = round(sum(float((records.get(c) or {}).get("green_seconds") or 0) for c in expected), 2)
red_seconds = round(sum(float((records.get(c) or {}).get("red_seconds") or 0) for c in expected), 2)
verified_only = [case for case in expected if case in passed]
if verified_only and not malformed and not missing and not extra:
    subprocess.run([sys.executable, select_py, "commit-state", "--results", results],
                   check=False, capture_output=True)
print(f"REPRO_TOTAL={len(expected)}")
print(f"REPRO_PASSED={len(passed)}")
print(f"REPRO_FAILED={len(failed) + malformed + len(missing) + len(extra)}")
print(f"REPRO_GREEN_SECONDS={int(green_seconds)}")
print(f"REPRO_RED_SECONDS={int(red_seconds)}")
if malformed:
    print(f"REPRO_MALFORMED={malformed}")
if missing:
    print("REPRO_MISSING=" + " ".join(missing))
if extra:
    print("REPRO_UNEXPECTED=" + " ".join(extra))
if failed:
    print("REPRO_FAILING:" + " ".join(failed))
PY
)
printf '%s\n' "$summary"
failed_count=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_FAILED=//p')
skipped_count=0
if [ -n "${REPRO_SKIPPED_LIST:-}" ]; then
  skipped_count=$(printf '%s' "$REPRO_SKIPPED_LIST" | wc -w)
fi
echo "REPRO_SKIPPED_COUNT=$skipped_count"
echo "repro 用例：$(printf '%s\n' "$summary" | sed -n 's/^REPRO_PASSED=//p')/$(printf '%s\n' "$summary" | sed -n 's/^REPRO_TOTAL=//p')（mode=$MODE，${elapsed}s）"

if ! [[ "${failed_count:-}" =~ ^[0-9]+$ ]]; then
  echo "repro: 汇总缺失（父进程统计失败）"; exit 1
fi
[ "$failed_count" -eq 0 ]
