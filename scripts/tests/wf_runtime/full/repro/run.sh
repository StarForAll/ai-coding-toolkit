#!/usr/bin/env bash
# 修复的可证伪用例：一键（CI 可用）运行器。详细用法：repro/run.sh -h
set -uo pipefail
# 内部阶段：
#   --_wf-repro-lease  公开参数已解析成规范计划对象（随 frame 携带），租约内冻结 plan.json；
#   --_wf-repro-inner  只消费已冻结的 plan/context token（父 C 交接；内嵌时角色为 full）。
# 公开阶段在任何租约/layout/scope/cache/build 之前禁写 pyc；内部阶段继承父阶段的批准前缀。
INNER_STAGE=""
case "${1:-}" in
  --_wf-repro-lease) INNER_STAGE=lease ;;
  --_wf-repro-inner) INNER_STAGE=inner ;;
esac
if [ -z "$INNER_STAGE" ]; then
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

进程拓扑：R（本 shell）解析公开参数并把规范计划交给 lease frame；唯一 root controller
（execution.py --runner-control）持 fixture/results/release 租约，监督唯一的发行准备与
用例执行，在结束校验、清理与取消都有结论后提交 proof 并发布最终 repro 投影；worker 只写
自己的结果；gate 只读校验。
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
CLI="$HERE/cli.py"

# 内部 frame 先整体剥离/校验：用户参数里不允许出现保留选项，内层也不接受用户参数。
if [ -n "$INNER_STAGE" ]; then
  if ! frame=$("$PY" "$PROTOCOL" strip-repro -- "$@"); then
    exit 2
  fi
  eval "$frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
  case "$WF_STAGE" in
    repro-lease) [ "$INNER_STAGE" = "lease" ] || { echo "FRAME-STAGE-MISMATCH" >&2; exit 2; } ;;
    repro-inner) [ "$INNER_STAGE" = "inner" ] || { echo "FRAME-STAGE-MISMATCH" >&2; exit 2; } ;;
    *) echo "FRAME-STAGE-UNKNOWN: $WF_STAGE" >&2; exit 2 ;;
  esac
fi

# 取消请求只由 root controller 交接：内层不派生、不删除、不改写；收到信号才用排他创建发布。
publish_cancel() {   # publish_cancel <signum>
  local sig=$1 path="${WF_CANCEL_FILE:-}"
  if [ -z "$path" ]; then
    echo "CANCEL-PUBLISH-FAILED: WF_CANCEL_FILE 未交接（sig=$sig）" >&2
    return 0
  fi
  if ( set -o noclobber; printf 'cancelled by signal %s\n' "$sig" > "$path" ) 2>/dev/null; then
    echo "CANCEL-PUBLISHED: sig=$sig path=$path" >&2
  elif [ -f "$path" ]; then
    echo "CANCEL-KEPT: 本代取消请求已存在（sig=$sig）" >&2
  else
    echo "CANCEL-PUBLISH-FAILED: 无法创建取消标记 $path（sig=$sig）" >&2
  fi
}
install_cancel_traps() {
  trap 'publish_cancel TERM; exit 143' TERM
  trap 'publish_cancel INT; exit 130' INT
  trap 'publish_cancel HUP; exit 129' HUP
}

# ---- 公开阶段：唯一一次解析，零写入 ------------------------------------------------
if [ -z "$INNER_STAGE" ]; then
  if ! cli_out=$("$PY" "$CLI" "$@"); then
    exit 2
  fi
  eval "$cli_out" || { echo "CLI-EVAL-FAILED" >&2; exit 2; }
  if [ "$HELP" = "1" ]; then usage; exit 0; fi
  # 清单是纯选择面：只读组/用例登记，不计算 release subject，不读 proof/state/缓存。
  if [ "$LIST" = "1" ]; then
    list_args=(--fixture-deploy "$DEPLOY")
    for g in "${GROUP_NAMES[@]}"; do list_args+=(--group "$g"); done
    [ -n "$ONLY" ] && list_args+=(--only "$ONLY")
    exec "$PY" "$HERE/repro_select.py" list "${list_args[@]}"
  fi
  lease_frame=$("$PY" "$PROTOCOL" encode-repro --stage repro-lease \
    --entry-pid "$$" --plan-b64 "$PLAN_B64") || exit 2
  eval "$lease_frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
  exec "$PY" "$SCOPE" lease-results -- bash "$0" "${FRAME[@]}"
fi

# ---- lease 阶段：冻结唯一计划 → 交 root controller ---------------------------------
if [ "$INNER_STAGE" = "lease" ]; then
  "$PY" "$SCOPE" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
  "$PY" "$SCOPE" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
  if [ "${WF_FRAME_ENTRY_PID:-}" != "$$" ]; then
    echo "LEASE-ENTRY-MISMATCH: frame entry-pid=${WF_FRAME_ENTRY_PID:-} pid=$$" >&2
    exit 2
  fi
  plan_fields=$("$PY" "$CLI" plan-fields --plan-b64 "$WF_FRAME_PLAN_B64") || exit 2
  eval "$plan_fields" || { echo "PLAN-FIELDS-EVAL-FAILED" >&2; exit 2; }
  RESULTS="$PLAN_RESULTS_DIR"
  SCOPE_ROOT="$PLAN_SCOPE_ROOT"
  export WF_RESULTS_DIR="$RESULTS"
  export WF_COMMAND_EVIDENCE_ROOT="$RESULTS/commands"
  export WF_REPRO_RESULTS="$RESULTS"
  if ! layout_out=$("$PY" "$PATHS" layout --kind repro --pid "$$" --mode "$PLAN_REPRO_MODE" --format sh); then
    exit 2
  fi
  eval "$layout_out" || { echo "LAYOUT-EVAL-FAILED" >&2; exit 2; }
  export WF_TEST_RUN_CACHE="${WF_TEST_RUN_CACHE:-$LAYOUT_STATE}"
  export WF_TEST_RELEASE_CACHE="${WF_TEST_RELEASE_CACHE:-$LAYOUT_TEST_RELEASE_CACHE}"
  if [ -n "$SCOPE_ROOT" ]; then
    "$PY" "$SCOPE" check-scope "$SCOPE_ROOT" "$RESULTS" \
      ${WF_TEST_RUN_CACHE:+"$WF_TEST_RUN_CACHE"} ${WF_TEST_RELEASE_CACHE:+"$WF_TEST_RELEASE_CACHE"} \
      ${WF_RESULTS_CACHE:+"$WF_RESULTS_CACHE"} || exit 2
    RESULTS_CACHE="${WF_RESULTS_CACHE:-$SCOPE_ROOT/cache}"
  else
    RESULTS_CACHE="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}"
  fi
  # 结果缓存轮转：独立入口只回收本 scope（repro-*）的 finished+cleaned 条目。
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
  freeze=$("$PY" "$CLI" freeze-plan --plan-b64 "$WF_FRAME_PLAN_B64" \
    --results-root "$RESULTS" --run-id "$WF_RUN_ID") || exit 2
  eval "$freeze" || { echo "FREEZE-EVAL-FAILED" >&2; exit 2; }
  export WF_RUNNER_CONTROL_PID=$$
  exec "$PY" "$FULL/execution.py" --runner-control --name wf-repro-runner \
    --runner-role repro --results-root "$RESULTS" --run-id "$WF_RUN_ID" \
    --plan-file "$PLAN_FILE" --plan-sha256 "$PLAN_SHA256" --plan-size "$PLAN_SIZE" \
    --timeout "${WF_RUN_TIMEOUT:-1800}" --log "$RESULTS/.runner.log" \
    --result "$RESULTS/.runner.json" --pass-fds "${WF_FIXTURE_LEASE_FD},${WF_RESULTS_LOCK_FD}" -- \
    bash "$0"
fi

# ---- inner 阶段：只消费已核计划与 context ------------------------------------------
"$PY" "$SCOPE" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
"$PY" "$SCOPE" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
if ! plan_out=$("$PY" "$CLI" read-plan --plan-file "$WF_FRAME_PLAN_FILE" \
    --plan-sha256 "$WF_FRAME_PLAN_SHA256" --plan-size "$WF_FRAME_PLAN_SIZE" \
    --run-id "${WF_RUN_ID:?missing run id}" --results-root "$WF_FRAME_RESULTS_ROOT" \
    --scope-root "${WF_FRAME_SCOPE_ROOT:-}"); then
  exit 2
fi
eval "$plan_out" || { echo "PLAN-EVAL-FAILED" >&2; exit 2; }
PLAN_ROOT="$PLAN_RESULTS_DIR"
case "$PLAN_ROLE" in
  repro) RESULTS="$PLAN_ROOT" ;;
  full)
    # 内嵌 repro：父计划与父结果根；本层结果固定写在父根的 repro/ 子树。
    RESULTS="$WF_FRAME_RESULTS_ROOT/repro"
    ;;
  *) echo "PLAN-ROLE-INVALID: $PLAN_ROLE" >&2; exit 2 ;;
esac
CONTEXT_FILE="$WF_FRAME_CONTEXT_FILE"
[ -f "$CONTEXT_FILE" ] || { echo "RELEASE-CONTEXT-MISSING: $CONTEXT_FILE" >&2; exit 2; }
case "$CONTEXT_FILE" in /*) : ;; *) echo "RELEASE-CONTEXT-NOT-ABSOLUTE" >&2; exit 2 ;; esac
if ! "$PY" - "$CONTEXT_FILE" "$WF_FRAME_RESULTS_ROOT" <<'PY'
import os, sys
context, root = sys.argv[1:3]
expected = os.path.join(os.path.realpath(root), 'release-context.json')
raise SystemExit(0 if os.path.realpath(context) == expected else 1)
PY
then
  echo "RELEASE-CONTEXT-WRONG-ROOT: $CONTEXT_FILE" >&2
  exit 2
fi
ctx=$("$PY" - "$CONTEXT_FILE" "$WF_FRAME_CONTEXT_SHA256" "$WF_FRAME_CONTEXT_SIZE" \
  "$WF_FRAME_RESULTS_ROOT" <<'PY'
import hashlib, json, os, sys
path, sha, size, results_root = sys.argv[1:5]
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
for key in ('deploy', 'release_root', 'version', 'ref'):
    if not context.get(key):
        raise SystemExit('context missing ' + key)
if os.path.realpath(context.get('results_dir') or '') != os.path.realpath(results_root):
    raise SystemExit('context belongs to another results root')
candidate = context.get('candidate') or {}
if context['deploy'] == 'candidate' and not candidate.get('commit'):
    raise SystemExit('candidate context has no verified commit')
print(context['deploy']); print(context['release_root']); print(context['version']); print(context['ref'])
print(context.get('release_subject') or ''); print(context.get('tree_digest') or '')
print(context.get('plan_sha256') or ''); print(context.get('plan_size') or '')
print(candidate.get('commit') or '')
PY
) || { echo "RELEASE-CONTEXT-INVALID" >&2; exit 2; }
{ read -r CTX_DEPLOY; read -r CTX_ROOT; read -r CTX_VERSION; read -r CTX_REF; \
  read -r CTX_SUBJECT; read -r CTX_TREE; read -r CTX_PLAN_SHA; read -r CTX_PLAN_SIZE; \
  read -r CTX_COMMIT; } <<< "$ctx"
[ "$CTX_DEPLOY" = "$PLAN_DEPLOY" ] || { echo "RELEASE-CONTEXT-DEPLOY-MISMATCH" >&2; exit 2; }
[ "$CTX_PLAN_SHA" = "$WF_FRAME_PLAN_SHA256" ] || { echo "RELEASE-CONTEXT-PLAN-MISMATCH" >&2; exit 2; }
[ "$CTX_PLAN_SIZE" = "$WF_FRAME_PLAN_SIZE" ] || { echo "RELEASE-CONTEXT-PLAN-MISMATCH" >&2; exit 2; }
if [ "$PLAN_DEPLOY" = "candidate" ]; then
  [ "$CTX_ROOT" = "$PLAN_RELEASE_ROOT" ] || { echo "RELEASE-CONTEXT-ROOT-MISMATCH" >&2; exit 2; }
  [ "$CTX_VERSION" = "$PLAN_RELEASE_VERSION" ] || { echo "RELEASE-CONTEXT-VERSION-MISMATCH" >&2; exit 2; }
  [ "$CTX_REF" = "$PLAN_RELEASE_REF" ] || { echo "RELEASE-CONTEXT-REF-MISMATCH" >&2; exit 2; }
else
  [ "$CTX_ROOT" = "$PLAN_TEST_RELEASE_ROOT" ] || { echo "RELEASE-CONTEXT-ROOT-MISMATCH" >&2; exit 2; }
  [ "$CTX_VERSION" = "$PLAN_TEST_RELEASE_VERSION" ] || { echo "RELEASE-CONTEXT-VERSION-MISMATCH" >&2; exit 2; }
  [ "$CTX_REF" = "$PLAN_TEST_RELEASE_REF" ] || { echo "RELEASE-CONTEXT-REF-MISMATCH" >&2; exit 2; }
fi
"$PY" "$REPO/scripts/release_lock.py" --verify --root "$CTX_ROOT" >/dev/null \
  || { echo "RELEASE-LEASE-INVALID" >&2; exit 2; }
export WF_RELEASE_TREE="$CTX_ROOT" WF_RELEASE_REF="$CTX_REF" WF_RELEASE_VERSION="$CTX_VERSION"
export WF_RELEASE_CONTEXT="$CONTEXT_FILE" WF_FIXTURE_DEPLOY="$PLAN_DEPLOY"
export WF_TEST_LIB="$CTX_ROOT/wf-release/lib" WF_BUILD_SECONDS="${WF_BUILD_SECONDS:-0}"
if [ "$PLAN_DEPLOY" = "candidate" ]; then
  export WF_RELEASE_ROOT="$CTX_ROOT" WF_RELEASE_META="$CTX_ROOT.meta.json" \
    WF_RELEASE_COMMIT="$CTX_COMMIT"
fi
if [ "$PLAN_ROLE" = "repro" ]; then export WF_RESULTS_DIR="$PLAN_ROOT"; fi
export WF_REPRO_RESULTS="$RESULTS"

# ---- 结果/状态布局（纯派生）--------------------------------------------------------
if ! layout_out=$("$PY" "$PATHS" layout --kind repro --pid "$$" --mode "$PLAN_REPRO_MODE" --format sh); then
  exit 2
fi
eval "$layout_out" || { echo "LAYOUT-EVAL-FAILED" >&2; exit 2; }
export WF_TEST_RUN_CACHE="${WF_TEST_RUN_CACHE:-$LAYOUT_STATE}"
export WF_TEST_RELEASE_CACHE="${WF_TEST_RELEASE_CACHE:-$LAYOUT_TEST_RELEASE_CACHE}"
if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
  "$PY" "$SCOPE" check-scope "$RESULTS" || exit 2
fi
mkdir -p "$RESULTS/logs" "$RESULTS/commands" || exit 1
# 路径/scope 校验已通过：启用批准的 pycache 前缀（可恢复窗口，不得永久关闭字节码）。
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$RESULTS/pycache}"
unset PYTHONDONTWRITEBYTECODE
mkdir -p "$PYTHONPYCACHEPREFIX"
export WF_REPRO_RESULTS="$RESULTS" PY
install_cancel_traps

# ---- 冻结唯一 bundle（schema 3，原子写一次）----------------------------------------
group_args=()
for g in "${PLAN_REPRO_GROUPS[@]}"; do group_args+=(--group "$g"); done
selection=$("$PY" "$HERE/repro_select.py" plan --fixture-deploy "$PLAN_DEPLOY" \
  --mode "$PLAN_REPRO_MODE" --format sh --bundle "$RESULTS/inputs.json" \
  "${group_args[@]}" ${PLAN_ONLY:+--only "$PLAN_ONLY"})
rc=$?
if [ "$rc" -ne 0 ]; then
  exit "$rc"
fi
eval "$selection" || { echo "SELECT-EVAL-FAILED"; exit 2; }
[ -n "${REPRO_BUNDLE_SHA256:-}" ] || { echo "BUNDLE-NOT-FROZEN"; exit 1; }
export WF_REPRO_INPUTS_FILE="$RESULTS/inputs.json"
printf '%s' "$REPRO_CASES_TSV" > "$RESULTS/selection.tsv"
echo "repro: mode=$PLAN_REPRO_MODE deploy=$PLAN_DEPLOY cases=$REPRO_CASE_COUNT jobs=$PLAN_REPRO_JOBS"
if [ -n "${REPRO_SKIPPED_LIST:-}" ]; then
  echo "repro: skipped_non_candidate: $REPRO_SKIPPED_LIST"
fi

# ---- 执行（worker 只写自己的结果与日志）------------------------------------------
read -r started_uptime _ < /proc/uptime
started_ms=$((10#${started_uptime/./} * 10))
if [ "${PLAN_REPRO_JOBS:-1}" -le 1 ]; then
  while IFS=$'\t' read -r case mode; do
    [ -n "$case" ] || continue
    "$PY" "$HERE/_worker.py" "$case" "$mode"
  done <<< "$REPRO_CASES_TSV"
else
  awk -F'\t' 'NF>=2 {print $1" "$2}' "$RESULTS/selection.tsv" \
    | xargs -P "$PLAN_REPRO_JOBS" -n 2 "$PY" "$HERE/_worker.py"
fi
read -r ended_uptime _ < /proc/uptime
elapsed_ms=$((10#${ended_uptime/./} * 10 - started_ms))
elapsed=$(awk -v ms="$elapsed_ms" 'BEGIN { printf "%.2f", ms / 1000 }')

# ---- 只读 gate：报告结构，不写 state（唯一 writer 在 root controller）---------------
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
echo "repro 用例：$(printf '%s\n' "$summary" | sed -n 's/^REPRO_PASSED=//p')/$(printf '%s\n' "$summary" | sed -n 's/^REPRO_TOTAL=//p')（mode=$PLAN_REPRO_MODE，${elapsed}s）"
bundle_sha=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_BUNDLE_SHA256=//p' | head -1)
bundle_size=$(printf '%s\n' "$summary" | sed -n 's/^REPRO_BUNDLE_SIZE=//p' | head -1)
if [ -n "$bundle_sha" ] && [ -n "$bundle_size" ]; then
  printf '{"sha256":"%s","size":%s}\n' "$bundle_sha" "$bundle_size" \
    > "$RESULTS/repro.bundle.json" 2>/dev/null || true
fi

if ! [[ "${failed_count:-}" =~ ^[0-9]+$ ]]; then
  echo "repro: 汇总缺失（父进程统计失败）"
  exit 1
fi
if [ "$failed_count" -eq 0 ] && [ "$summary_rc" -eq 0 ] && [ "${structural:-0}" = "1" ] \
    && [ -n "${eligible:-}" ]; then
  echo "INNER-TARGET-OK: 用例证据交接完成；proof 与最终成功出口只在 root controller"
  exit 0
fi
echo "INNER-TARGET-FAILED: 用例证据未通过，交给 root controller 按真实证据收口"
exit 1