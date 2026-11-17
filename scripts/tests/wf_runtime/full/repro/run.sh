#!/usr/bin/env bash
# 修复的可证伪用例：一键（CI 可用）运行器。详细用法：repro/run.sh -h
set -uo pipefail
# 内部阶段标记：--_wf-repro-inner 只在 root controller 监督下重入；--_wf-inherited-release
# 是父 run 的内嵌交接。两者的 pyc 窗口都继承父阶段已批准的 pycache。
INNER=0
case "${1:-}" in --_wf-repro-inner) INNER=1; shift ;; esac
if [ "$INNER" != "1" ] && [ "${1:-}" != "--_wf-inherited-release" ]; then
  export PYTHONDONTWRITEBYTECODE=1
  unset PYTHONPYCACHEPREFIX
fi
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

进程拓扑：R（本 shell）编排；唯一 root controller（execution.py --runner-control）在同一 C 进程
监督发行准备/用例执行，并在 bundle/records/receipts 全部核验后发布最终 repro 投影；worker 只写
自己的结果；gate 只读校验；唯一 state writer 是本 shell 启动的一个 `commit-state` 子进程。
EOF
}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL="$(dirname "$HERE")"
REPO="$(cd "$FULL/../../../.." && pwd)"
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY="${PY:-/softwares/python/bin/python3}"
SCOPE="$FULL/fixture_scope.py"
PATHS="$REPO/scripts/wf_test_paths.py"
PROTOCOL="$FULL/runner_protocol.py"
LIFECYCLE="$FULL/resource_lifecycle.py"
# 测试专用注入点：默认取仓库内真实入口；契约测试指向计数 shim（只包一层 argv 记录）。
RELEASE_CLI="${WF_TEST_RELEASE_CLI:-$REPO/scripts/tests/wf_test_release.py}"
CANDIDATE_VALIDATOR="${WF_CANDIDATE_VALIDATOR:-$FULL/prepare_candidate_repo.py}"
CLI="$HERE/cli.py"

if [ "$INNER" = "1" ]; then
  INHERITED=""
else
  # 内部 frame 先整体剥离/校验：用户参数里不允许再出现保留选项。
  if ! frame=$("$PY" "$PROTOCOL" strip-inherited -- "$@"); then
    exit 2
  fi
  eval "$frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
  set -- "${USER_ARGV[@]}"
  INHERITED="${WF_STAGE:-}"
fi

# ---- 公开参数：唯一解析器是 cli.py；任何拒绝都发生在租约/layout/scope/cache/build 之前 ----
if ! cli_out=$("$PY" "$CLI" "$@"); then
  exit 2
fi
eval "$cli_out" || { echo "CLI-EVAL-FAILED" >&2; exit 2; }
if [ "$HELP" = "1" ]; then usage; exit 0; fi

group_args=()
for g in "${GROUP_NAMES[@]}"; do
  group_args+=(--group "$g")
done

# ---- 计划面：list 在租约/结果/pycache/state/runtime 之前纯选择退出 -----------------
if [ "$LIST" = "1" ]; then
  "$PY" "$HERE/repro_select.py" plan --fixture-deploy "$DEPLOY" --mode both --format json \
    "${group_args[@]}" ${ONLY:+--only "$ONLY"} \
    | "$PY" -c 'import json,sys; d=json.load(sys.stdin); [print(c + chr(9) + d["cases"][c]["mode"]) for c in d["cases"]]'
  exit $?
fi

# ---- 独立入口：租约 → layout → begin_run → root controller；内嵌/内层跳过前三步 --------
if [ "$INNER" != "1" ] && [ "$INHERITED" != "inherited" ]; then
  forward=(--fixture-deploy "$DEPLOY" --mode "$MODE" --jobs "$JOBS")
  [ "$BUILD" = "1" ] || forward+=(--no-build)
  [ -n "$ONLY" ] && forward+=(--only "$ONLY")
  [ -n "$RESULTS" ] && forward+=(--results-dir "$RESULTS")
  for g in "${GROUP_NAMES[@]}"; do forward+=(--group "$g"); done
  if [ "$DEPLOY" = "candidate" ]; then
    forward+=(--release-root "$RELEASE_ROOT" --release-ref "$RELEASE_REF"
              --release-version "$RELEASE_VERSION")
    [ -n "$RELEASE_META" ] && forward+=(--release-meta "$RELEASE_META")
  fi
  if [ -z "$RELEASE_ROOT$RELEASE_REF$RELEASE_VERSION" ] && [ "$DEPLOY" = "candidate" ]; then
    echo "repro: candidate 模式需要 --release-root/--release-ref/--release-version" >&2
    exit 2
  fi
  if [ "$DEPLOY" = "dev" ] && [ -n "$RELEASE_ROOT$RELEASE_REF$RELEASE_VERSION" ] \
      && [ "${WF_REPRO_LEASE_READY:-0}" != "1" ]; then
    echo "repro: dev 模式不接受 --release-*（候选请用 --fixture-deploy candidate）" >&2
    exit 2
  fi
  if [ "$DEPLOY" = "candidate" ] && { [ "$MODE" = "red" ] || [ "$MODE" = "both" ]; }; then
    echo "repro: candidate 模式只允许 --mode green|auto（red 注入针对源码，请在 dev 模式跑）" >&2
    exit 2
  fi
  # 独立入口：fixture → results 域锁（同 PID exec 持有）。
  if [ "${WF_REPRO_LEASE_READY:-0}" != "1" ]; then
    export WF_REPRO_LEASE_READY=1
    exec "$PY" "$SCOPE" lease-results -- bash "$0" "${forward[@]}"
  fi
  # 管理路径（纯派生，不写）：scope 下默认值从 scope 派生；显式域外值在首次写前拒绝。
  if ! layout_out=$("$PY" "$PATHS" layout --kind repro --pid "$$" --mode "$MODE" --format sh); then
    exit 2
  fi
  eval "$layout_out" || { echo "LAYOUT-EVAL-FAILED" >&2; exit 2; }
  RESULTS="${RESULTS:-$LAYOUT_RESULTS_DIR}"
  export WF_REPRO_RESULTS="$RESULTS"
  export WF_RESULTS_DIR="$RESULTS"
  export WF_TEST_RUN_CACHE="${WF_TEST_RUN_CACHE:-$LAYOUT_STATE}"
  export WF_TEST_RELEASE_CACHE="${WF_TEST_RELEASE_CACHE:-$LAYOUT_TEST_RELEASE_CACHE}"
  if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
    "$PY" "$SCOPE" check-scope "$WF_TEST_SCOPE_ROOT" "$RESULTS" "$WF_TEST_RUN_CACHE" \
      ${WF_TEST_RELEASE_CACHE:+"$WF_TEST_RELEASE_CACHE"} ${WF_RESULTS_CACHE:+"$WF_RESULTS_CACHE"} || exit 2
  fi
  # 结果缓存轮转：独立入口只回收本 scope（repro-*）的 finished+cleaned 条目。
  if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
    RESULTS_CACHE="${WF_RESULTS_CACHE:-$WF_TEST_SCOPE_ROOT/cache}"
  else
    RESULTS_CACHE="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}"
  fi
  WF_RESULTS_CACHE="$RESULTS_CACHE" "$PY" "$SCOPE" prune-results "$RESULTS_CACHE" \
    --scope repro --exclude "$RESULTS" || true
  # 唯一初始化：owner 意图 → active state → prepare（三个 checkpoint 只在 helper 内退出）。
  begin_out=$("$PY" "$LIFECYCLE" begin-run --results-root "$RESULTS" --role repro \
      --intent execution --format sh)
  begin_rc=$?
  if [ "$begin_rc" -ne 0 ]; then
    echo "RESULTS-INIT-FAILED: 初始化拒绝（rc=$begin_rc）；不启动 controller、不清理现场" >&2
    exit "$begin_rc"
  fi
  eval "$begin_out" || { echo "RUN-ID-EVAL-FAILED" >&2; exit 2; }
  export WF_RUN_ID="$RUN_ID"
  export WF_COMMAND_EVIDENCE_ROOT="$RESULTS/commands"
  exec "$PY" "$FULL/execution.py" --runner-control --name wf-repro-runner \
    --runner-role repro --results-root "$RESULTS" --run-id "$WF_RUN_ID" \
    --timeout "${WF_RUN_TIMEOUT:-1800}" --log "$RESULTS/.runner.log" \
    --result "$RESULTS/.runner.json" --pass-fds "${WF_FIXTURE_LEASE_FD},${WF_RESULTS_LOCK_FD}" -- \
    bash "$0" --_wf-repro-inner "${forward[@]}"
fi

# ---- 内层/内嵌：发行准备（受 root controller 或父 run 监督）---------------------
case "$DEPLOY" in
  dev)
    if [ "$INHERITED" = "inherited" ]; then
      CONTEXT_FILE="$WF_INHERITED_CONTEXT"
      [ -f "$CONTEXT_FILE" ] || { echo "inherited release context missing: $CONTEXT_FILE" >&2; exit 2; }
      ctx=$("$PY" - "$CONTEXT_FILE" "$WF_INHERITED_SHA256" "$WF_INHERITED_SIZE" <<'PY'
import hashlib, json, sys
path, sha, size = sys.argv[1:4]
data = open(path, 'rb').read()
if len(data) != int(size):
    raise SystemExit('context size mismatch')
if hashlib.sha256(data).hexdigest() != sha:
    raise SystemExit('context digest mismatch')
context = json.loads(data)
if context.get('schema_version') != 2:
    raise SystemExit('context schema mismatch (schema 2 required)')
runtime = context.get('runtime') or {}
for role in ('tool', 'sut'):
    projection = runtime.get(role) or {}
    if not projection.get('path_identity') or not projection.get('binary_digest'):
        raise SystemExit('context runtime identity incomplete: ' + role)
print(context['deploy']); print(context['release_root']); print(context['version']); print(context['ref'])
print(context.get('release_subject') or ''); print(context.get('tree_digest') or '')
PY
      ) || { echo "RELEASE-CONTEXT-INVALID" >&2; exit 2; }
      { read -r CTX_DEPLOY; read -r CTX_ROOT; read -r CTX_VERSION; read -r CTX_REF; \
        read -r CTX_SUBJECT; read -r CTX_TREE; } <<< "$ctx"
      [ "$CTX_DEPLOY" = "$DEPLOY" ] || { echo "RELEASE-CONTEXT-DEPLOY-MISMATCH" >&2; exit 2; }
      "$PY" "$SCOPE" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
      "$PY" "$SCOPE" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
      "$PY" "$REPO/scripts/release_lock.py" --verify --root "$CTX_ROOT" >/dev/null \
        || { echo "RELEASE-LEASE-INVALID" >&2; exit 2; }
      export WF_RELEASE_TREE="$CTX_ROOT" WF_RELEASE_REF="$CTX_REF" WF_RELEASE_VERSION="$CTX_VERSION"
      export WF_TEST_LIB="$CTX_ROOT/wf-release/lib"
      export WF_RELEASE_CONTEXT="$CONTEXT_FILE" WF_FIXTURE_DEPLOY="$DEPLOY"
      DEV_ROOT="$CTX_ROOT"; DEV_VERSION="$CTX_VERSION"; DEV_REF="$CTX_REF"
    else
      if [ -n "$RELEASE_ROOT" ] && [ -n "$RELEASE_VERSION" ] && [ -n "$RELEASE_REF" ]; then
        DEV_ROOT="$RELEASE_ROOT"; DEV_VERSION="$RELEASE_VERSION"; DEV_REF="$RELEASE_REF"
      else
        DEV_ROOT="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import wf_test_release as t; print(t.default_root(t.resolve_version(None)))' "$REPO/scripts/tests")"
        DEV_VERSION="$("$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import wf_test_release as t; print(t.resolve_version(None))' "$REPO/scripts/tests")"
        DEV_REF="refs/tags/wf-v$DEV_VERSION"
      fi
      if [ "${WF_REPRO_RELEASE_READY:-0}" != "1" ]; then
        export WF_REPRO_RELEASE_READY=1
        exec "$PY" "$REPO/scripts/release_lock.py" --lease --root "$DEV_ROOT" -- \
          bash "$0" --_wf-repro-inner --fixture-deploy "$DEPLOY" --mode "$MODE" --jobs "$JOBS" \
          $( [ "$BUILD" = "1" ] || printf '%s' --no-build ) \
          ${ONLY:+--only "$ONLY"} --results-dir "${WF_REPRO_RESULTS:-$RESULTS}" \
          $(for g in "${GROUP_NAMES[@]}"; do printf '%s %s ' --group "$g"; done) \
          --release-root "$DEV_ROOT" --release-ref "$DEV_REF" --release-version "$DEV_VERSION"
      fi
      "$PY" "$SCOPE" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
      "$PY" "$SCOPE" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
      "$PY" "$REPO/scripts/release_lock.py" --verify --root "$DEV_ROOT" >/dev/null \
        || { echo "RELEASE-LEASE-INVALID" >&2; exit 2; }
      if [ "$BUILD" = "1" ]; then
        "$PY" "$RELEASE_CLI" --ensure --no-lock --root "$DEV_ROOT" --version "$DEV_VERSION" \
          || { echo "BUILD-FAILED"; exit 1; }
      else
        "$PY" "$RELEASE_CLI" --check --no-lock --root "$DEV_ROOT" --version "$DEV_VERSION" \
          || { echo "TEST-RELEASE-STALE: 测试发行副本缺失或过期（重建或去掉 --no-build）"; exit 1; }
      fi
      export WF_RELEASE_TREE="$DEV_ROOT" WF_RELEASE_REF="$DEV_REF" WF_RELEASE_VERSION="$DEV_VERSION"
      export WF_TEST_LIB="$DEV_ROOT/wf-release/lib"
      export WF_FIXTURE_DEPLOY=dev
    fi
    ;;
  candidate)
    # 内嵌 repro 的候选身份由父 run 的起始/结束 barrier 已核验（design §3.3）。
    if [ "$INHERITED" != "inherited" ]; then
      "$PY" "$CANDIDATE_VALIDATOR" --check --out "$RELEASE_ROOT" --version "$RELEASE_VERSION" \
        || { echo "CANDIDATE-REPO-INVALID"; exit 1; }
    fi
    export WF_RELEASE_TREE="$RELEASE_ROOT" WF_RELEASE_REF="$RELEASE_REF" WF_RELEASE_VERSION="$RELEASE_VERSION"
    export WF_RELEASE_META="${RELEASE_META:-$RELEASE_ROOT.meta.json}"
    export WF_TEST_LIB="$RELEASE_ROOT/wf-release/lib"
    export WF_FIXTURE_DEPLOY=candidate
    ;;
esac

# ---- 结果目录（内层重算只用显式值；外层已派生） --------------------------------
if ! layout_out=$("$PY" "$PATHS" layout --kind repro --pid "$$" --mode "$MODE" --format sh); then
  exit 2
fi
eval "$layout_out" || { echo "LAYOUT-EVAL-FAILED" >&2; exit 2; }
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$LAYOUT_PYCACHE_BOOTSTRAP}"
unset PYTHONDONTWRITEBYTECODE
if [ -z "$RESULTS" ]; then
  RESULTS="${WF_REPRO_RESULTS_DIR:-$LAYOUT_RESULTS_DIR}"
fi
if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
  "$PY" "$SCOPE" check-scope "$RESULTS" || exit 2
fi
export WF_TEST_RUN_CACHE="${WF_TEST_RUN_CACHE:-$LAYOUT_STATE}"
export WF_TEST_RELEASE_CACHE="${WF_TEST_RELEASE_CACHE:-$LAYOUT_TEST_RELEASE_CACHE}"
mkdir -p "$RESULTS/logs" "$RESULTS/commands" || exit 1
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$RESULTS/pycache}"
mkdir -p "$PYTHONPYCACHEPREFIX"
export WF_REPRO_RESULTS="$RESULTS" PY
# 内嵌 repro 继承父 run 的 results root（owner/state/receipts 都在那里）；独立入口由外层显式导出。
if [ -z "${WF_RESULTS_DIR:-}" ]; then export WF_RESULTS_DIR="$RESULTS"; fi
# 取消：写一次性取消请求让每个 worker 的 C（execution.py）自行收口 G/S；内层不删现场。
export WF_CANCEL_FILE="${WF_CANCEL_FILE:-$RESULTS/cancel-request}"
rm -f "$WF_CANCEL_FILE" 2>/dev/null || true
trap 'trap "" INT TERM HUP; printf "cancelled by shell trap\n" > "$WF_CANCEL_FILE" 2>/dev/null || true; exit 143' TERM
trap 'trap "" INT TERM HUP; printf "cancelled by shell trap\n" > "$WF_CANCEL_FILE" 2>/dev/null || true; exit 130' INT

# ---- 冻结唯一 bundle（schema 2，原子写一次）----------------------------------------
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
bundle_sha=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_BUNDLE_SHA256=//p' | head -1)
bundle_size=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_BUNDLE_SIZE=//p' | head -1)
if [ -n "$bundle_sha" ] && [ -n "$bundle_size" ]; then
  printf '{"sha256":"%s","size":%s}\n' "$bundle_sha" "$bundle_size" \
    > "$RESULTS/repro.bundle.json" 2>/dev/null || true
fi

# ---- 唯一 state writer（R 串行启动并等待；gate rc 不等于写许可）--------------------
writer_rc=0
if [ "${structural:-0}" = "1" ] && [ -n "${eligible:-}" ]; then
  "$PY" "$HERE/repro_select.py" commit-state --results "$RESULTS" --bundle "$RESULTS/inputs.json" \
    --bundle-sha256 "$REPRO_BUNDLE_SHA256" --bundle-size "$REPRO_BUNDLE_SIZE" || writer_rc=$?
else
  echo "REPRO_STATE_SKIPPED: structural=${structural:-0} eligible=$(printf '%s' "${eligible:-}" | wc -w)"
fi

if ! [[ "${failed_count:-}" =~ ^[0-9]+$ ]]; then
  echo "repro: 汇总缺失（父进程统计失败）"
  exit 1
fi
[ "$writer_rc" -eq 0 ] || echo "WRITER-FAILED: $writer_rc"
if [ "$failed_count" -eq 0 ] && [ "$summary_rc" -eq 0 ] && [ "$writer_rc" -eq 0 ]; then
  echo "INNER-TARGET-OK: 用例证据与 state 交接完成；最终成功出口只在 root controller"
  exit 0
fi
echo "INNER-TARGET-FAILED: 用例证据未通过，交给 root controller 按真实证据收口"
exit 1