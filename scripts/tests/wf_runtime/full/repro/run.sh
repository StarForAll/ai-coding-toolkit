#!/usr/bin/env bash
# 修复的可证伪用例：一键（CI 可用）运行器。详细用法：repro/run.sh -h
set -uo pipefail
# usage 是唯一文本来源（heredoc），不按行号回头注释提取——头注释不再承载正文。
usage() { cat <<'EOF'
每个用例有两个面：`--expect green`（当前树成立）与 `--expect red`（注入原缺陷后必须变红）。
只有 green 的"证据"无法区分"修好了"和"没修"，所以：
  --mode both  两个面都跑（**默认**，保持兼容）；
  --mode green 只跑当前树（T2 收口默认）；
  --mode red   只跑注入面（断言变更/发行前的证伪检查）；
  --mode auto  首次运行、新用例、helper/脚本/被测 payload 目标变化 → 该用例 both；未变化 → green
               （candidate 模式遇到需要 both 会报错并提示先在 dev 模式跑 red）。

用法：
  bash .../repro/run.sh --mode green --no-build
  bash .../repro/run.sh --group review --mode red --no-build
  bash .../repro/run.sh --mode auto --jobs 4
  bash .../repro/run.sh --list
  bash .../repro/run.sh --fixture-deploy candidate --release-root <候选仓库根> \
       --release-ref refs/tags/wf-v0.1.2 --release-version 0.1.2 --mode green --no-build

进程拓扑：R（本 shell）编排；worker 只写自己的结果；gate 只读校验；唯一 state writer 是本 shell
启动的一个 `commit-state` 子进程。冻结来源只有一个 `inputs.json` bundle。
EOF
}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL="$(dirname "$HERE")"
REPO="$(cd "$FULL/../../../.." && pwd)"
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY="${PY:-/softwares/python/bin/python3}"
SCOPE="$FULL/fixture_scope.py"
PROTOCOL="$FULL/runner_protocol.py"
case "${1:-}" in -h|--help) usage; exit 0 ;; esac

# 内部 frame 先整体剥离/校验：用户参数里不允许再出现保留选项。
if ! frame=$("$PY" "$PROTOCOL" strip-inherited -- "$@"); then
  exit 2
fi
eval "$frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
set -- "${USER_ARGV[@]}"
INHERITED="${WF_STAGE:-}"

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

# ---- 计划面：list 在租约/结果/pycache/state/runtime 之前纯选择退出 -----------------
if [ "$MODE" = "__list__" ]; then
  "$PY" "$HERE/repro_select.py" plan --fixture-deploy "$DEPLOY" --mode both --format json \
    "${group_args[@]}" ${ONLY:+--only "$ONLY"} \
    | "$PY" -c 'import json,sys; d=json.load(sys.stdin); [print(c + chr(9) + d["cases"][c]["mode"]) for c in d["cases"]]'
  exit $?
fi

# ---- 租约与发行：继承入口零 ensure/check；独立入口持锁初始化一次 --------------------
if [ "$INHERITED" = "inherited" ]; then
  CONTEXT_FILE="$WF_INHERITED_CONTEXT"
  [ -f "$CONTEXT_FILE" ] || { echo "inherited release context missing: $CONTEXT_FILE" >&2; exit 2; }
  ctx=$("$PY" - "$CONTEXT_FILE" "$WF_INHERITED_SHA256" "$WF_INHERITED_SIZE" <<'PY'
import hashlib, json, os, sys
path, sha, size = sys.argv[1:4]
data = open(path, 'rb').read()
if len(data) != int(size):
    raise SystemExit('context size mismatch')
if hashlib.sha256(data).hexdigest() != sha:
    raise SystemExit('context digest mismatch')
context = json.loads(data)
if context.get('schema_version') != 1:
    raise SystemExit('context schema mismatch')
print(context['deploy']); print(context['release_root']); print(context['version']); print(context['ref'])
print(context.get('release_subject') or ''); print(context.get('tree_digest') or '')
PY
  ) || { echo "RELEASE-CONTEXT-INVALID" >&2; exit 2; }
  { read -r CTX_DEPLOY; read -r CTX_ROOT; read -r CTX_VERSION; read -r CTX_REF; \
    read -r CTX_SUBJECT; read -r CTX_TREE; } <<< "$ctx"
  [ "$CTX_DEPLOY" = "$DEPLOY" ] || { echo "RELEASE-CONTEXT-DEPLOY-MISMATCH" >&2; exit 2; }
  "$PY" "$SCOPE" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
  "$PY" "$SCOPE" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
  if [ "$DEPLOY" = "dev" ]; then
    # dev 继承：父 context 是身份唯一来源，不要求内层重复传 --release-*。
    "$PY" "$REPO/scripts/release_lock.py" --verify --root "$CTX_ROOT" >/dev/null \
      || { echo "RELEASE-LEASE-INVALID" >&2; exit 2; }
    export WF_RELEASE_TREE="$CTX_ROOT" WF_RELEASE_REF="$CTX_REF" WF_RELEASE_VERSION="$CTX_VERSION"
    export WF_TEST_LIB="$CTX_ROOT/wf-release/lib"
  else
    [ "$CTX_ROOT" = "$RELEASE_ROOT" ] || { echo "RELEASE-CONTEXT-ROOT-MISMATCH" >&2; exit 2; }
    export WF_RELEASE_TREE="$CTX_ROOT" WF_RELEASE_REF="$CTX_REF" WF_RELEASE_VERSION="$CTX_VERSION"
    export WF_RELEASE_META="${RELEASE_META:-$CTX_ROOT.meta.json}"
    export WF_TEST_LIB="$CTX_ROOT/wf-release/lib"
  fi
  export WF_RELEASE_CONTEXT="$CONTEXT_FILE" WF_FIXTURE_DEPLOY="$DEPLOY"
else
  export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-${TMPDIR:-/tmp}/wf-pycache-repro-bootstrap}"
  unset PYTHONDONTWRITEBYTECODE
  case "$DEPLOY" in
    dev)
      if [ "${WF_REPRO_LEASE_READY:-0}" = "1" ] && [ -n "$RELEASE_ROOT" ]; then
        # 持锁重入：父进程已解析好身份，原样沿用（不重算、不重新猜）。
        DEV_ROOT="$RELEASE_ROOT"; DEV_VERSION="$RELEASE_VERSION"; DEV_REF="$RELEASE_REF"
        [ -n "$DEV_ROOT" ] && [ -n "$DEV_VERSION" ] && [ -n "$DEV_REF" ] \
          || { echo "repro: 持锁重入缺 dev 发行身份" >&2; exit 2; }
      else
        if [ -n "$RELEASE_ROOT$RELEASE_REF$RELEASE_VERSION" ]; then
          echo "repro: dev 模式不接受 --release-*（候选请用 --fixture-deploy candidate）" >&2
          exit 2
        fi
        DEV_ROOT="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import wf_test_release as t; print(t.default_root(t.resolve_version(None)))' "$REPO/scripts/tests")"
        DEV_VERSION="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import wf_test_release as t; print(t.resolve_version(None))' "$REPO/scripts/tests")"
        DEV_REF="refs/tags/wf-v$DEV_VERSION"
      fi
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
      ;;
    *)
      echo "repro: --fixture-deploy 只接受 dev|candidate（收到 '$DEPLOY'）" >&2; exit 2 ;;
  esac
  # 重入要用的 argv 只在这里组装一次（数组，不拼字符串）。
  forward=(--fixture-deploy "$DEPLOY" --mode "$MODE" --jobs "$JOBS")
  if [ "$BUILD" = "0" ]; then forward+=(--no-build); fi
  if [ -n "$ONLY" ]; then forward+=(--only "$ONLY"); fi
  if [ -n "$RESULTS" ]; then forward+=(--results-dir "$RESULTS"); fi
  for g in "${GROUP_NAMES[@]}"; do forward+=(--group "$g"); done
  if [ "$DEPLOY" = "dev" ]; then
    forward+=(--release-root "$DEV_ROOT" --release-ref "$DEV_REF" --release-version "$DEV_VERSION")
  else
    forward+=(--release-root "$RELEASE_ROOT" --release-ref "$RELEASE_REF" --release-version "$RELEASE_VERSION")
  fi
  if [ "${WF_REPRO_LEASE_READY:-0}" != "1" ]; then
    # fixture → 当前域结果锁（同 PID exec 持有）。
    export WF_REPRO_LEASE_READY=1
    exec "$PY" "$SCOPE" lease-results -- bash "$0" "${forward[@]}"
  fi
  if [ "$DEPLOY" = "dev" ]; then
    # release 独占锁必须由**本 shell 进程**持有：先把 FD 交给一个 python 进程取锁，
    # 再 exec 回本脚本（FD 真实存活，env 只是定位事实）。
    if [ "${WF_REPRO_RELEASE_READY:-0}" != "1" ]; then
      export WF_REPRO_RELEASE_READY=1
      exec "$PY" "$REPO/scripts/release_lock.py" --lease --root "$DEV_ROOT" -- bash "$0" "${forward[@]}"
    fi
    if [ "$BUILD" -eq 1 ]; then
      "$PY" "$REPO/scripts/tests/wf_test_release.py" --ensure --no-lock --root "$DEV_ROOT" --version "$DEV_VERSION" \
        || { echo "BUILD-FAILED"; exit 1; }
    else
      "$PY" "$REPO/scripts/tests/wf_test_release.py" --check --no-lock --root "$DEV_ROOT" --version "$DEV_VERSION" \
        || { echo "TEST-RELEASE-STALE: 测试发行副本缺失或过期（重建或去掉 --no-build）"; exit 1; }
    fi
    export WF_RELEASE_TREE="$DEV_ROOT" WF_RELEASE_REF="$DEV_REF" WF_RELEASE_VERSION="$DEV_VERSION"
    export WF_TEST_LIB="$DEV_ROOT/wf-release/lib"
    export WF_FIXTURE_DEPLOY=dev
  else
    "$PY" "$FULL/prepare_candidate_repo.py" --check --out "$RELEASE_ROOT" --version "$RELEASE_VERSION" \
      || { echo "CANDIDATE-REPO-INVALID"; exit 1; }
    export WF_RELEASE_TREE="$RELEASE_ROOT" WF_RELEASE_REF="$RELEASE_REF" WF_RELEASE_VERSION="$RELEASE_VERSION"
    export WF_RELEASE_META="${RELEASE_META:-$RELEASE_ROOT.meta.json}"
    export WF_TEST_LIB="$RELEASE_ROOT/wf-release/lib"
    export WF_FIXTURE_DEPLOY=candidate
  fi
fi

# ---- 结果目录与选择 ----------------------------------------------------------------
if [ -z "$RESULTS" ]; then
  if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
    RESULTS="$WF_TEST_SCOPE_ROOT/repro-$MODE-$$"
  else
    RESULTS="${WF_REPRO_RESULTS_DIR:-$HOME/.cache/wf-test-run/repro-$MODE-$$}"
  fi
fi
if [ -n "${WF_TEST_SCOPE_ROOT:-}" ] && [ "$INHERITED" != "inherited" ]; then
  "$PY" "$SCOPE" check-scope "$WF_TEST_SCOPE_ROOT" "$RESULTS" || exit 2
fi
# 结果缓存轮转：独立 repro 入口只回收本 scope（repro-*）的带 marker 目录；root 可经
# WF_RESULTS_CACHE 注入（契约测试指向临时根，不触碰真实用户缓存）。
RESULTS_CACHE="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}"
WF_RESULTS_CACHE="$RESULTS_CACHE" "$PY" "$SCOPE" prune-results "$RESULTS_CACHE" \
  --scope repro --exclude "$RESULTS" || true
"$PY" "$SCOPE" prepare-results "$RESULTS" || exit 1
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$RESULTS/pycache}"
mkdir -p "$PYTHONPYCACHEPREFIX" "$RESULTS/logs"
export WF_REPRO_RESULTS="$RESULTS" PY
trap 'trap "" INT TERM; "$PY" "$FULL/execution.py" --cancel-parent-children; exit 143' TERM
trap 'trap "" INT TERM; "$PY" "$FULL/execution.py" --cancel-parent-children; exit 130' INT

# ---- 冻结唯一 bundle（schema 1，原子写一次）----------------------------------------
selection=$("$PY" "$HERE/repro_select.py" plan --fixture-deploy "$DEPLOY" --mode "$MODE" --format sh \
  --bundle "$RESULTS/inputs.json" "${group_args[@]}" ${ONLY:+--only "$ONLY"})
rc=$?
if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
eval "$selection" || { echo "SELECT-EVAL-FAILED"; exit 2; }
[ -n "${REPRO_BUNDLE_SHA256:-}" ] || { echo "BUNDLE-NOT-FROZEN"; exit 1; }
export WF_REPRO_INPUTS_FILE="$RESULTS/inputs.json"
printf '%s' "$REPRO_CASES_TSV" > "$RESULTS/selection.tsv"
echo "repro: mode=$MODE deploy=$DEPLOY cases=$REPRO_CASE_COUNT jobs=$JOBS"
if [ -n "${REPRO_SKIPPED_LIST:-}" ]; then
  echo "repro: skipped_non_candidate: $REPRO_SKIPPED_LIST"
fi

# ---- 执行（worker 只写自己的结果与日志）------------------------------------------
read -r started_uptime _ < /proc/uptime
started_ms=$((10#${started_uptime/./} * 10))
if [ "$JOBS" -le 1 ]; then
  while IFS=$'\t' read -r case mode; do
    [ -n "$case" ] || continue
    "$PY" "$HERE/_worker.py" "$case" "$mode"
  done <<< "$REPRO_CASES_TSV"
else
  awk -F'\t' 'NF>=2 {print $1" "$2}' "$RESULTS/selection.tsv" \
    | xargs -P "$JOBS" -n 2 "$PY" "$HERE/_worker.py"
fi
read -r ended_uptime _ < /proc/uptime
elapsed_ms=$((10#${ended_uptime/./} * 10 - started_ms))
elapsed=$(awk -v ms="$elapsed_ms" 'BEGIN { printf "%.2f", ms / 1000 }')

# ---- 只读 gate：报告结构，不该 gate 写 state --------------------------------------
summary=$("$PY" "$FULL/results_gate.py" --repro-results "$RESULTS" --bundle "$RESULTS/inputs.json" \
  --bundle-sha256 "$REPRO_BUNDLE_SHA256" --bundle-size "$REPRO_BUNDLE_SIZE")
summary_rc=$?
printf '%s\n' "$summary"
failed_count=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_FAILED=//p')
structural=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_STRUCTURAL_OK=//p')
eligible=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_ELIGIBLE=//p')
skipped_count=0
if [ -n "${REPRO_SKIPPED_LIST:-}" ]; then
  skipped_count=$(printf '%s' "$REPRO_SKIPPED_LIST" | wc -w)
fi
echo "REPRO_SKIPPED_COUNT=$skipped_count"
echo "repro 用例：$(printf '%s\n' "$summary" | sed -n 's/^REPRO_PASSED=//p')/$(printf '%s\n' "$summary" | sed -n 's/^REPRO_TOTAL=//p')（mode=$MODE，${elapsed}s）"

# ---- 唯一 state writer（R 串行启动并等待；gate rc 不等于写许可）--------------------
writer_rc=0
if [ "${structural:-0}" = "1" ] && [ -n "${eligible:-}" ]; then
  "$PY" "$HERE/repro_select.py" commit-state --results "$RESULTS" --bundle "$RESULTS/inputs.json" \
    --bundle-sha256 "$REPRO_BUNDLE_SHA256" --bundle-size "$REPRO_BUNDLE_SIZE" || writer_rc=$?
else
  echo "REPRO_STATE_SKIPPED: structural=${structural:-0} eligible=$(printf '%s' "${eligible:-}" | wc -w)"
fi

if ! [[ "${failed_count:-}" =~ ^[0-9]+$ ]]; then
  echo "repro: 汇总缺失（父进程统计失败）"; exit 1
fi
[ "$writer_rc" -eq 0 ] || echo "WRITER-FAILED: $writer_rc"
[ "$failed_count" -eq 0 ] && [ "$summary_rc" -eq 0 ] && [ "$writer_rc" -eq 0 ]
