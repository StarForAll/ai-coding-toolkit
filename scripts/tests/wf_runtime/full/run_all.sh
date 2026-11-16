#!/bin/bash
# 全量/子集/代表集复现：每个套件都从干净夹具开始；任一环节失败都会让脚本以非零码退出。
# 选择与冲突判定在 `plan.py`（唯一 plan()）；本脚本只用它的计划执行，避免两份选择逻辑。
# 详细用法：run_all.sh --help
set -uo pipefail
# 路径/scope 校验完成之前一律禁写 pyc，并丢弃外部注入的 pycache 前缀：
# public/preflight/--list/--dry-run 不得在任何位置（含域外 WF_PYCACHE）产生写入。
# 内部 frame 重入（lease/controlled/execute）继承父阶段已批准的 pycache，不得清除。
if [ "${1:-}" != "--_wf-internal" ]; then
  export PYTHONDONTWRITEBYTECODE=1
  unset PYTHONPYCACHEPREFIX
fi
# usage 是唯一文本来源（heredoc），不按行号回头注释提取——头注释不再承载正文。
usage() { cat <<'EOF'
模式：
  --full            59 套件 + 4 流程 + r72 + repro（默认）
  --subset          只跑 WF_SUITES 选中的套件（repro 需 WF_WITH_REPRO=1）
  --representative  代表集 + f0/p5_spec + 代表 repro 组（T3 候选模式的入口）
  WF_SUITES=a,b    未显式模式时隐含 --subset
  WF_TAGS=review   按 tag 选套件（同样隐含 --subset；与 WF_SUITES 取交集）
  --list --changed 按改动文件给出建议套件/repro 组（只建议，不执行）

常用：
  WF_SUITES="r70_tests" bash run_all.sh                  # 真子集（1 个执行单元）
  bash run_all.sh --full --repro green                   # T2 阶段收口
  bash run_all.sh --full --repro both                     # T3-1
  bash run_all.sh --representative --fixture-deploy candidate \
    --release-root ~/.cache/wf-candidate-repo/0.1.2 \
    --release-ref refs/tags/wf-v0.1.2 --release-version 0.1.2
  bash run_all.sh --serial                                # 套件层串行（确定性/排障）
  bash run_all.sh --list | --dry-run                      # 只输出计划

环境：WF_JOBS（套件层并行，默认 min(8,cpu)；--serial 或 WF_JOBS=1 退回串行）、
      WF_REPRO_JOBS（repro 用例层并行，默认 min(8,cpu)）、
      WF_WITH_REPRO=1（子集模式开 repro）、WF_RESULTS_DIR、WF_RESULTS_CACHE（缓存轮转根，
      默认 ~/.cache/wf-test-run）、WF_FIX、WF_NO_RUN=1（计划后即退出）、
      WF_NO_TEMPLATE=1（逐套件重建夹具；默认在 run 内构建一次夹具模板后逐套件 cp -a）
EOF
}
HERE=$(cd "$(dirname "$0")" && pwd)
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY=/softwares/python/bin/python3
REPO_ROOT=$(cd "$HERE/../../../.." && pwd)
SCOPE_HELPER="$HERE/fixture_scope.py"
# 管理路径/scope 的唯一所有者（作者侧）；shell 只消费它派生并校验过的值。
PATH_HELPER="$REPO_ROOT/scripts/wf_test_paths.py"

# ---- 内部 frame：先整体剥离/校验，再处理用户 argv（非法不 fallback）------------
# public 没有前缀；lease/controlled/execute 是同一脚本的三次重入，只有两次计划。
if ! frame_out=$("$PY" "$HERE/runner_protocol.py" strip -- "$@"); then
  exit 2
fi
eval "$frame_out" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
set -- "${USER_ARGV[@]}"
STAGE="${WF_STAGE:-public}"

apply_frame_env() {
  export WF_RESULTS_DIR="$WF_FRAME_RESULTS_ROOT"
  export WF_RUNNER_ENTRY_PID="$WF_FRAME_ENTRY_PID"
  if [ "$WF_FRAME_SCOPE_ROOT" != "-" ]; then export WF_TEST_SCOPE_ROOT="$WF_FRAME_SCOPE_ROOT"; fi
}
# 阶段日志（design §5.2 的计数证据）：public 阶段在 claim 之前不能写结果目录，
# 因此由 lease 阶段在 claim/prepare 之后补记 public，再记自己。
note_stage() {
  [ -n "${WF_RESULTS_DIR:-}" ] && [ -d "$WF_RESULTS_DIR" ] || return 0
  printf '%s\n' "$1" >> "$WF_RESULTS_DIR/stages" 2>/dev/null || true
}
verify_inherited_locks() {
  "$PY" "$SCOPE_HELPER" check-lease >/dev/null || { echo "FIXTURE-LEASE-INVALID" >&2; exit 2; }
  "$PY" "$SCOPE_HELPER" check-results-lease >/dev/null || { echo "RESULTS-LEASE-INVALID" >&2; exit 2; }
}

case "$STAGE" in
  public)
    case "${1:-}" in -h|--help) usage; exit 0 ;; esac
    # pycache 只在 layout/scope 校验通过后启用；此前的 helper/preflight/list 全程禁写。
    # 显式性在此刻按原始环境记录一次，内部 frame 原样传递，重入不重新猜。
    if [ -n "${WF_RESULTS_DIR:-}" ]; then RESULTS_EXPLICIT=1; else RESULTS_EXPLICIT=0; fi
    # 管理路径的唯一规则（wf_test_paths）：scope 下默认值从 scope 派生，显式域外值在
    # 首次写前拒绝；无 scope 时保持历史默认。layout 只派生/校验，不写任何文件。
    if ! layout_out=$("$PY" "$PATH_HELPER" layout --kind run --pid "$$" --format sh); then
      exit 2
    fi
    eval "$layout_out" || { echo "LAYOUT-EVAL-FAILED" >&2; exit 2; }
    WF_RESULTS_DIR=${WF_RESULTS_DIR:-$LAYOUT_RESULTS_DIR}
    export WF_FIX="${WF_FIX:-$LAYOUT_FIX}"
    export WF_RESULTS_CACHE="${WF_RESULTS_CACHE:-$LAYOUT_RESULTS_CACHE}"
    export WF_TEST_RUN_CACHE="${WF_TEST_RUN_CACHE:-$LAYOUT_STATE}"
    export WF_TEST_RELEASE_CACHE="${WF_TEST_RELEASE_CACHE:-$LAYOUT_TEST_RELEASE_CACHE}"
    WF_RESULTS_DIR=$("$PY" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$WF_RESULTS_DIR")
    export WF_RESULTS_DIR
    # 唯一一次 preflight：禁写 pyc、不给 WF_RESULTS_DIR（list/dry-run 全程零写入）。
    # 计划调用计数不落任何文件：preflight 的阶段行在内存里暂存，claim 之后与 final plan
    # 一起写入结果目录（不再创建再删除 bootstrap 文件来冒充零写入）。
    unset WF_PLAN_LOG
    preflight_out=$(PYTHONDONTWRITEBYTECODE=1 WF_RESULTS_DIR= "$PY" "$HERE/plan.py" --format sh -- "$@")
    plan_rc=$?
    if [ "$plan_rc" -ne 0 ]; then
      exit "$plan_rc"
    fi
    if ! eval "$preflight_out"; then
      echo "PLAN-EVAL-FAILED" >&2
      exit 2
    fi
    export WF_PREFLIGHT_PLAN_LINE="${PLAN_MODE:-} ${PLAN_LIST_ONLY:-}"
    if [ "${PLAN_LIST_ONLY:-0}" = "1" ] || [ "${WF_NO_RUN:-0}" = "1" ]; then
      # 显式结果目录：只写 plan.json 与必要 owner marker，并在当前域固定结果锁下短期完成。
      if [ "$RESULTS_EXPLICIT" = "1" ] && [ "${PLAN_LIST_ONLY:-0}" = "1" ]; then
        exec "$PY" "$SCOPE_HELPER" lease-domain -- bash -c '
          "$1" "$2" claim-results "$3" || exit 1
          "$1" "$4" --format json -- "${@:5}" >/dev/null || exit 2' \
          lease-mirror "$PY" "$SCOPE_HELPER" "$WF_RESULTS_DIR" "$HERE/plan.py" -- "$@"
      fi
      exit 0
    fi
    # 测试域：runner 管理的写入口必须落在 owned scope 内（越界写前拒绝）。
    if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
      "$PY" "$SCOPE_HELPER" check-scope "$WF_TEST_SCOPE_ROOT" "$WF_RESULTS_DIR" \
        ${WF_RESULTS_CACHE:+"$WF_RESULTS_CACHE"} ${WF_TEST_RUN_CACHE:+"$WF_TEST_RUN_CACHE"} \
        ${WF_TEST_RELEASE_CACHE:+"$WF_TEST_RELEASE_CACHE"} \
        ${WF_PYCACHE:+"$WF_PYCACHE"} ${WF_FIX:+"$WF_FIX"} || exit 2
      SCOPE_FIELD="$WF_TEST_SCOPE_ROOT"
    else
      SCOPE_FIELD="-"
    fi
    # 路径验证已通过：启用批准的 pycache 前缀（scope 下为 scope 内 bootstrap）。
    export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$LAYOUT_PYCACHE_BOOTSTRAP}"
    unset PYTHONDONTWRITEBYTECODE
    FRAME=()
    lease_frame=$("$PY" "$HERE/runner_protocol.py" encode --stage lease -- \
      --entry-pid "$$" --results-root "$WF_RESULTS_DIR" \
      --results-explicit "$RESULTS_EXPLICIT" --scope-root "$SCOPE_FIELD" -- "$@") || exit 2
    eval "$lease_frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
    export WF_RUNNER_CONTROL_PID=$$
    exec "$PY" "$SCOPE_HELPER" lease-results -- bash "$0" "${FRAME[@]}"
    ;;
  lease)
    apply_frame_env
    verify_inherited_locks
    # claim 必须在任何结果目录写入之前（pycache 目录也算“非空”）。
    "$PY" "$SCOPE_HELPER" claim-results "$WF_RESULTS_DIR" || exit 1
    "$PY" "$SCOPE_HELPER" prepare-results "$WF_RESULTS_DIR" || exit 1
    note_stage public
    note_stage lease
    # 计划调用计数：preflight 的一行来自内存（public 阶段不落任何文件），final plan 由
    # plan.py 自己追加到同一文件；复用结果目录时这两个文件都已在 prepare-results 清空。
    if [ -n "${WF_PREFLIGHT_PLAN_LINE:-}" ]; then
      printf '%s\n' "$WF_PREFLIGHT_PLAN_LINE" >> "$WF_RESULTS_DIR/plan-calls"
    fi
    export WF_PLAN_LOG="$WF_RESULTS_DIR/plan-calls"
    export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$WF_RESULTS_DIR/pycache}"
    mkdir -p "$PYTHONPYCACHEPREFIX"
    # 结果缓存轮转：只回收本 scope（run-*）的带 marker 目录，保留最近 20；root 可经
    # WF_RESULTS_CACHE 注入（契约测试指向临时根，不触碰真实用户缓存）。
    if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
      RESULTS_CACHE="${WF_RESULTS_CACHE:-$WF_TEST_SCOPE_ROOT/cache}"
    else
      RESULTS_CACHE="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}"
    fi
    WF_RESULTS_CACHE="$RESULTS_CACHE" "$PY" "$SCOPE_HELPER" prune-results "$RESULTS_CACHE" \
      --scope run --exclude "$WF_RESULTS_DIR" || true
    # ---- 计划（唯一权威）：lease 内唯一一次 final plan，落盘后冻结字节 -------------
    "$PY" "$HERE/plan.py" --format json -- "$@" > "$WF_RESULTS_DIR/plan.json" \
      2>"$WF_RESULTS_DIR/plan.err" || {
      cat "$WF_RESULTS_DIR/plan.err" >&2
      exit 2
    }
    PLAN_FILE="$WF_RESULTS_DIR/plan.json"
    export PLAN_FILE
    token_out=$("$PY" "$HERE/runner_protocol.py" token --file "$PLAN_FILE") || exit 2
    eval "$token_out" || { echo "TOKEN-EVAL-FAILED" >&2; exit 2; }
    eval "$("$PY" "$HERE/plan.py" --plan-file "$PLAN_FILE")" || { echo "PLAN-EVAL-FAILED" >&2; exit 2; }
    FIX="$PLAN_FIX"
    RESULTS_DIR="$PLAN_RESULTS_DIR"
    export WF_FIX="$FIX" WF_ISOLATED_UNITS="${PLAN_ISOLATED_UNITS:-}"
    LEGACY_FIXTURE_ROOT="$FIX.legacy"
    WF_LEGACY_FIXTURE_ROOT="$LEGACY_FIXTURE_ROOT"
    export WF_LEGACY_FIXTURE_ROOT
    "$PY" "$SCOPE_HELPER" validate "$FIX" --forbid "$RESULTS_DIR" \
      --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
    mkdir -p "$RESULTS_DIR"
    "$PY" "$SCOPE_HELPER" reset "$LEGACY_FIXTURE_ROOT" --forbid "$RESULTS_DIR" \
      --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
    # controlled frame 由同一 encoder 组装（父字段原样搬运，只换 stage）。
    FRAME=()
    controlled_frame=$("$PY" "$HERE/runner_protocol.py" encode --stage controlled -- \
      --entry-pid "$WF_FRAME_ENTRY_PID" --results-root "$WF_FRAME_RESULTS_ROOT" \
      --results-explicit "$WF_FRAME_RESULTS_EXPLICIT" --scope-root "$WF_FRAME_SCOPE_ROOT" \
      --plan-file "$PLAN_FILE" --plan-sha256 "$TOKEN_SHA256" --plan-size "$TOKEN_SIZE" -- "$@") || exit 2
    eval "$controlled_frame" || { echo "FRAME-EVAL-FAILED" >&2; exit 2; }
    # controller 显式白名单继承 fixture/result FD：不依赖 Popen 默认，也不传其他 FD。
    pass_fds="${WF_FIXTURE_LEASE_FD},${WF_RESULTS_LOCK_FD}"
    export WF_RUNNER_CONTROL_PID=$$
    exec "$PY" "$HERE/execution.py" --runner-control --name wf-runner \
      --timeout "${WF_RUN_TIMEOUT:-1800}" --log "$RESULTS_DIR/.runner.log" \
      --result "$RESULTS_DIR/.runner.json" --pass-fds "$pass_fds" -- \
      bash "$0" "${FRAME[@]}"
    ;;
  controlled)
    apply_frame_env
    verify_inherited_locks
    note_stage controlled
    RESULTS_DIR="$WF_RESULTS_DIR"
    eval "$("$PY" "$HERE/plan.py" --plan-file "$WF_FRAME_PLAN_FILE")" || { echo "PLAN-EVAL-FAILED" >&2; exit 2; }
    release_args=(--deploy "$PLAN_FIXTURE_DEPLOY" --results-dir "$WF_RESULTS_DIR"
      --entry-pid "$WF_FRAME_ENTRY_PID" --results-root "$WF_FRAME_RESULTS_ROOT"
      --results-explicit "$WF_FRAME_RESULTS_EXPLICIT" --scope-root "$WF_FRAME_SCOPE_ROOT"
      --plan-file "$WF_FRAME_PLAN_FILE" --plan-sha256 "$WF_FRAME_PLAN_SHA256"
      --plan-size "$WF_FRAME_PLAN_SIZE")
    if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
      release_args+=(--release-root "$PLAN_RELEASE_ROOT" --release-ref "$PLAN_RELEASE_REF"
                     --release-version "$PLAN_RELEASE_VERSION")
    else
      release_args+=(--release-root "$PLAN_TEST_RELEASE_ROOT" --release-ref "$PLAN_TEST_RELEASE_REF"
                     --release-version "$PLAN_TEST_RELEASE_VERSION")
      if [ "$PLAN_NO_BUILD" = "1" ]; then release_args+=(--no-build); fi
    fi
    exec "$PY" "$HERE/release_context.py" "${release_args[@]}" -- bash "$0" -- "$@"
    ;;
  execute)
    apply_frame_env
    note_stage execute
    RESULTS_DIR="$WF_RESULTS_DIR"
    if ! gate_out=$("$PY" "$HERE/execute_gate.py" \
        --entry-pid "$WF_FRAME_ENTRY_PID" --plan-file "$WF_FRAME_PLAN_FILE" \
        --plan-sha256 "$WF_FRAME_PLAN_SHA256" --plan-size "$WF_FRAME_PLAN_SIZE" \
        --context-file "$WF_FRAME_CONTEXT_FILE" --context-sha256 "$WF_FRAME_CONTEXT_SHA256" \
        --context-size "$WF_FRAME_CONTEXT_SIZE"); then
      exit 2
    fi
    eval "$gate_out" || exit 2
    RELEASE_SUBJECT=""
    eval "$("$PY" "$HERE/plan.py" --plan-file "$WF_FRAME_PLAN_FILE")" || { echo "PLAN-EVAL-FAILED" >&2; exit 2; }
    FIX="$PLAN_FIX"
    RESULTS_DIR="$PLAN_RESULTS_DIR"
    export WF_FIX="$FIX" WF_ISOLATED_UNITS="${PLAN_ISOLATED_UNITS:-}"
    LEGACY_FIXTURE_ROOT="$FIX.legacy"
    WF_LEGACY_FIXTURE_ROOT="$LEGACY_FIXTURE_ROOT"
    export WF_LEGACY_FIXTURE_ROOT
    ;;
  *)
    echo "FRAME-STAGE-UNKNOWN: $STAGE" >&2
    exit 2
    ;;
esac

now_ms() {
  local uptime rest
  read -r uptime rest < /proc/uptime || return 1
  uptime=${uptime/./}
  printf '%s\n' "$((10#$uptime * 10))"
}
# isolated-user 的唯一来源：units.json isolated_user 字段（plan.py → PLAN_ISOLATED_UNITS）；
# 这里只做成员判定，套件特判不进 bash 分支。
isolated_args() {
  case " ${WF_ISOLATED_UNITS:-} " in *" $1 "*) printf '%s\n' --isolated-user ;; esac
}
run_command() {
  local phase=$1 log=$2 kind=$3 expected=""; shift 3
  local expected_args=()
  local user_args=()
  user_args=($(isolated_args "$phase"))
  if [ "${1:-}" = "--expected" ]; then expected=$2; shift 2; expected_args=(--expected "$expected"); fi
  "$PY" "$HERE/execution.py" --name "$phase" --kind "$kind" --log "$log" --result "$log.json" \
    "${expected_args[@]}" "${user_args[@]}" -- "$@"
}
export WF_RESULTS_DIR="$RESULTS_DIR" WF_FIX="$FIX"
WF_TEMPLATE=""
WF_TEMPLATE_READY=0
# run 内模板（结果目录里）由本 run 拥有、结束即删；跨 run 缓存条目绝不在此删除。
RUN_TEMPLATE=""
# 取消协议：shell 不再递归强杀监督进程（那会绕过 G 的最终核验）；它只写一次性取消请求，
# 每个 owned `execution.py` 调用（C）在自己的事件循环里读到后经私有通道取消 G/S，
# 并等到 G 的最终 DONE+退出才返回。run_one 在启动新单元前检查同一请求，停止调度。
CANCEL_REQUEST="$RESULTS_DIR/cancel-request"
rm -f "$CANCEL_REQUEST" 2>/dev/null || true
export WF_CANCEL_FILE="$CANCEL_REQUEST"
CLEANUP_DONE=0
CLEANUP_FAILED=0
cleanup_fixtures() {
  local rc=0
  for fixture_path in "$FIX" "$LEGACY_FIXTURE_ROOT" ${RUN_TEMPLATE:+"$RUN_TEMPLATE"}; do
    [ -n "$fixture_path" ] || continue
    [ -e "$fixture_path" ] || continue
    "$PY" "$SCOPE_HELPER" remove "$fixture_path" >/dev/null 2>>"$RESULTS_DIR/cleanup.err" || rc=1
  done
  return "$rc"
}
on_exit_cleanup() {
  if [ "$CLEANUP_DONE" != "1" ]; then
    cleanup_fixtures >/dev/null 2>&1 || true
  fi
}
trap on_exit_cleanup EXIT
# 早期阶段（public/lease/controlled 被直接 TERM）不需要递归清理；ctrl 阶段由 C 收口。
request_cancel() {
  trap '' INT TERM HUP
  printf 'cancelled by shell trap\n' > "$CANCEL_REQUEST" 2>/dev/null || true
}
trap 'request_cancel; exit 143' TERM
trap 'request_cancel; exit 130' INT
trap 'request_cancel; exit 129' HUP

# ---- 源树卫生：运行前快照（唯一实现 source_hygiene.py）----------------------
# 只对**新增**失败（本地存量以警告 + 清理命令呈现）；AC3 的绝对判据另行用 find 复核。
HYGIENE_SNAPSHOT="$RESULTS_DIR/source-hygiene.before.json"
"$PY" "$HERE/source_hygiene.py" snapshot "$REPO_ROOT" "$HYGIENE_SNAPSHOT" || exit 1

TOTAL_STARTED=$(now_ms)
build_seconds=0
init_millis=0
suite_millis=0
green_seconds=0
red_seconds=0
fail=0
suite_ran=0
flow_ran=0
repro_ran=0

SOURCE_HOME="$HOME"
export SOURCE_HOME

# ---- 发行来源 --------------------------------------------------------------
product_digest() {
  "$PY" - "$REPO_ROOT" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import wf_release_common as common
print(common.tree_digest(common.REPO_ROOT + "/docs/workflows/wf-release"))
PY
}

PRODUCT_BEFORE=$(product_digest)

# 发行准备已在 controlled 阶段完成（release_context.py）：execute 只消费已核 env。
build_seconds=${WF_BUILD_SECONDS:-0}
BUILD_OK=1
RELEASE_REPO="$WF_RELEASE_REPO"
RELEASE_REF="$WF_INSTALL_REF"
SHARED_RELEASE="$RELEASE_REPO"
if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
  RELEASE_VERSION="$PLAN_RELEASE_VERSION"
else
  RELEASE_VERSION="$PLAN_TEST_RELEASE_VERSION"
fi
export WF_FIXTURE_DEPLOY="$PLAN_FIXTURE_DEPLOY" WF_RELEASE_REPO

fixture_args() {
  FIXTURE_ARGS=(--deploy "$PLAN_FIXTURE_DEPLOY")
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    FIXTURE_ARGS+=(--release-root "$PLAN_RELEASE_ROOT" --release-ref "$PLAN_RELEASE_REF"
                   --release-version "$PLAN_RELEASE_VERSION")
  fi
}

# ---- 夹具模板（run 内构建 + 跨 run 缓存；一处策略两个载体）-------------------
# 每单元都跑 wf_fixture.sh + f1_init.py 约 1.95s，而 cp -a 约 5ms：模板只构建一次、
# 只读，每单元复制独立一份。复制不会搬走记录里的绝对路径与外部暂存目录，所以克隆后
# 必须 repoint + 残留检查（template_check.py 是唯一判定点，bash 只传参与读退出码）。
# run-owned 模板（无跨 run 缓存）：与 template_cache._build 同序（reset → wf_fixture → f1_init）。
build_template_tree() {   # build_template_tree <root> <log>
  local root=$1 log=$2 rc=0
  local args=(--deploy "$PLAN_FIXTURE_DEPLOY")
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    args+=(--release-root "$PLAN_RELEASE_ROOT" --release-ref "$PLAN_RELEASE_REF"
           --release-version "$PLAN_RELEASE_VERSION")
  fi
  {
    "$PY" "$HERE/fixture_scope.py" reset "$root" || exit 1
    WF_FIX="$root" bash "$HERE/wf_fixture.sh" "$root" "${args[@]}" || exit 1
    WF_FIX="$root" "$PY" "$HERE/f1_init.py" || exit 1
  } >>"$log" 2>&1 || rc=$?
  return "$rc"
}

template_check() {   # template_check <root> [extra args...]
  local root=$1; shift
  local args=(--version "$PLAN_RELEASE_VERSION" --ref "$PLAN_RELEASE_REF")
  if [ "$PLAN_FIXTURE_DEPLOY" != "candidate" ]; then args=(); fi
  "$PY" "$HERE/template_check.py" "$root" "${args[@]}" --quiet "$@"
}

# 模板缓存的身份/槽位/发布都在 template_cache.py（唯一实现）；bash 只传参与读退出码。
release_subject_digest() {
  "$PY" - "$REPO_ROOT" "$PLAN_RELEASE_ROOT" "$PLAN_RELEASE_VERSION" "$PLAN_RELEASE_REF" <<'PY'
import sys
repo, root, version, ref = sys.argv[1:5]
sys.path.insert(0, repo + "/scripts")
import wf_release_common as common
print(common.release_subject(root, version, ref)["digest"])
PY
}

template_cache_cli() {  # template_cache_cli <subcommand> [extra args...]
  local sub=$1; shift
  local args=(--cache-root "$TEMPLATE_CACHE_ROOT" --deploy "$PLAN_FIXTURE_DEPLOY"
              --results-dir "$RESULTS_DIR")
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    args+=(--version "$PLAN_RELEASE_VERSION" --ref "$PLAN_RELEASE_REF"
           --release-root "$PLAN_RELEASE_ROOT" --subject "$RELEASE_SUBJECT")
  fi
  "$PY" "$HERE/template_cache.py" "$sub" "${args[@]}" "$@"
}

cleanup_template_cache_stale() {  # 只收本工具自己的历史残留（staging/backup/旧版 stale）
  local path
  for path in "$TEMPLATE_CACHE_ROOT"/*.staging-* "$TEMPLATE_CACHE_ROOT"/*.backup-* \
              "$TEMPLATE_CACHE_ROOT"/*.stale-* "$TEMPLATE_CACHE_ROOT"/*.build; do
    [ -e "$path" ] || continue
    "$PY" "$HERE/fixture_scope.py" remove "$path" >/dev/null 2>&1 \
      || echo "（无法回收陈旧模板缓存条目：$path）"
  done
}

TEMPLATE_SECONDS=0
WF_TEMPLATE_READY=0
WF_TEMPLATE=""
WF_TEMPLATE_SOURCE=""
TEMPLATE_SOURCE=run-build
TEMPLATE_CACHE_HIT=0
TEMPLATE_CACHE_KEY=""
if [ -n "${WF_TEST_SCOPE_ROOT:-}" ]; then
  TEMPLATE_CACHE_ROOT="${WF_RESULTS_CACHE:-$WF_TEST_SCOPE_ROOT/cache}/template"
else
  TEMPLATE_CACHE_ROOT="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}/template"
fi
# dev HEAD 是安装记录身份的一部分；读不到时固定退回 run-owned 模板（不读写跨 run 缓存，
# 也不签发 unknown）。该判断只在构建模板前算，preflight 不探测 HEAD。
HEAD_READABLE=1
if [ "$PLAN_FIXTURE_DEPLOY" = "dev" ]; then
  if [ -z "$("$PY" - "$REPO_ROOT" <<'PY'
import sys
sys.path.insert(0, sys.argv[1] + "/scripts")
import wf_release_common as common
print(common.git_head() or "")
PY
)" ]; then
    HEAD_READABLE=0
    echo "（dev HEAD 不可读：固定使用 run-owned 模板，不读写跨 run 缓存）"
  fi
fi
if [ "$PLAN_NO_TEMPLATE" = "1" ]; then
  TEMPLATE_SOURCE=none
  echo "（模板机制关闭（--no-template/WF_NO_TEMPLATE=1）：逐单元重建夹具）"
else
  template_started=$(now_ms)
  if [ "$PLAN_NO_TEMPLATE_CACHE" = "1" ] || [ "$HEAD_READABLE" = "0" ]; then
    WF_TEMPLATE="$RESULTS_DIR/template"
    RUN_TEMPLATE="$WF_TEMPLATE"
    if ! build_template_tree "$WF_TEMPLATE" "$RESULTS_DIR/template.out"; then
      echo "TEMPLATE-BUILD-FAILED（见 $RESULTS_DIR/template.out）"
      tail -5 "$RESULTS_DIR/template.out" || true
      exit 1
    fi
    if ! template_check "$WF_TEMPLATE"; then
      echo "TEMPLATE-BUILD-INVALID（见 $RESULTS_DIR/template.out）"
      exit 1
    fi
    TEMPLATE_SOURCE=run-build
    WF_TEMPLATE_SOURCE="$WF_TEMPLATE"
    WF_TEMPLATE_READY=1
  else
    mkdir -p "$TEMPLATE_CACHE_ROOT"
    cleanup_template_cache_stale "$TEMPLATE_CACHE_ROOT"
    if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ] && [ -z "$RELEASE_SUBJECT" ]; then
      RELEASE_SUBJECT=$(release_subject_digest) || { echo "RELEASE-SUBJECT-FAILED"; exit 1; }
    fi
    # 发布前先迁移可确认同槽位的 legacy key（只改 key 名，不改内容身份）。
    TEMPLATE_CACHE_KEY=$(template_cache_cli migrate) || { echo "TEMPLATE-CACHE-MIGRATE-FAILED"; exit 1; }
    if hit=$(template_cache_cli lookup); then
      TEMPLATE_CACHE_KEY=$(printf '%s\n' "$hit" | sed -n '2p')
      TEMPLATE_ENTRY="$TEMPLATE_CACHE_ROOT/$TEMPLATE_CACHE_KEY"
      WF_TEMPLATE="$TEMPLATE_ENTRY"
      WF_TEMPLATE_SOURCE=$(printf '%s\n' "$hit" | sed -n '1p')
      WF_TEMPLATE_READY=1
      TEMPLATE_SOURCE=cache
      TEMPLATE_CACHE_HIT=1
      echo "（模板缓存命中：$TEMPLATE_ENTRY）"
    else
      if ! published=$(template_cache_cli publish); then
        echo "TEMPLATE-CACHE-PUBLISH-FAILED"
        exit 1
      fi
      TEMPLATE_CACHE_KEY=$(printf '%s\n' "$published" | sed -n '2p')
      TEMPLATE_ENTRY="$TEMPLATE_CACHE_ROOT/$TEMPLATE_CACHE_KEY"
      WF_TEMPLATE="$TEMPLATE_ENTRY"
      WF_TEMPLATE_SOURCE=$(printf '%s\n' "$published" | sed -n '1p')
      WF_TEMPLATE_READY=1
      TEMPLATE_SOURCE=cache
      TEMPLATE_CACHE_HIT=0
      echo "（模板缓存已发布：$TEMPLATE_ENTRY）"
    fi
  fi
  TEMPLATE_SECONDS=$(( ($(now_ms) - template_started) / 1000 ))
  echo "（夹具来源：$TEMPLATE_SOURCE（hit=$TEMPLATE_CACHE_HIT），${TEMPLATE_SECONDS}s；逐单元 cp -a 复用）"
fi
export WF_TEMPLATE WF_TEMPLATE_READY
export WF_TEMPLATE_SOURCE

can_unshare() {
  unshare -Urm bash -c 'mount -t tmpfs tmpfs /proc/self/fd >/dev/null 2>&1 || mount -t tmpfs tmpfs /tmp' >/dev/null 2>&1
}

add_init_millis() {
  local timing="$RESULTS_DIR/$1.timing"
  if [ -f "$timing" ]; then
    local value
    value=$(sed -n 's/^init_millis=//p' "$timing" | head -1)
    case "$value" in ''|*[!0-9]*) value=0 ;; esac
    init_millis=$((init_millis + value))
    value=$(sed -n 's/^suite_millis=//p' "$timing" | head -1)
    case "$value" in ''|*[!0-9]*) value=0 ;; esac
    suite_millis=$((suite_millis + value))
  fi
}

run_repro() {
  # 只有一条实现：repro/run.sh（也可单独/CI 运行）。这里只消费它的机器可读汇总。
  # 失败计数写进 repro_fail（不直接改 fail）：并发开关下它跑在子 shell 里，父进程按计数器合并。
  local args=(--mode "$PLAN_REPRO_MODE" --jobs "$PLAN_REPRO_JOBS"
              --fixture-deploy "$PLAN_FIXTURE_DEPLOY" --results-dir "$RESULTS_DIR/repro")
  local g
  for g in $PLAN_REPRO_GROUPS; do args+=(--group "$g"); done
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    args+=(--release-root "$PLAN_RELEASE_ROOT" --release-ref "$PLAN_RELEASE_REF"
           --release-version "$PLAN_RELEASE_VERSION")
  fi
  if [ "$PLAN_NO_BUILD" = "1" ]; then args+=(--no-build); fi
  # 内嵌 repro 一律走 inherited release frame（默认构建与 --no-build 都一样），
  # 不靠 --no-build 让内层再 ensure/check 一次。
  FRAME=()
  inherited_frame=$("$PY" "$HERE/runner_protocol.py" encode-inherited \
    --context "$WF_FRAME_CONTEXT_FILE" --sha256 "$WF_FRAME_CONTEXT_SHA256" \
    --size "$WF_FRAME_CONTEXT_SIZE" -- "${args[@]}") || { echo "REPRO-FRAME-FAILED"; repro_fail=$((repro_fail + 1)); repro_rc=1; return; }
  eval "$inherited_frame" || { echo "REPRO-FRAME-EVAL-FAILED"; repro_fail=$((repro_fail + 1)); repro_rc=1; return; }
  local out rc
  out=$(bash "$HERE/repro/run.sh" "${FRAME[@]}" 2>&1); rc=$?
  printf '%s\n' "$out" > "$RESULTS_DIR/repro.raw"
  printf '%s\n' "$out" | grep -E '^(ok|FAIL|repro|SKIP|SELECT-ERROR|WRITER-FAILED|REPRO-STATE)' || true
  local total passed failed gsec rsec skipped
  total=$(printf '%s\n' "$out" | sed -n 's/^REPRO_TOTAL=//p')
  passed=$(printf '%s\n' "$out" | sed -n 's/^REPRO_PASSED=//p')
  failed=$(printf '%s\n' "$out" | sed -n 's/^REPRO_FAILED=//p')
  gsec=$(printf '%s\n' "$out" | sed -n 's/^REPRO_GREEN_SECONDS=//p')
  rsec=$(printf '%s\n' "$out" | sed -n 's/^REPRO_RED_SECONDS=//p')
  skipped=$(printf '%s\n' "$out" | sed -n 's/^REPRO_SKIPPED_COUNT=//p')
  if ! [[ "${total:-}" =~ ^[0-9]+$ ]] || ! [[ "${passed:-}" =~ ^[0-9]+$ ]] || ! [[ "${failed:-}" =~ ^[0-9]+$ ]]; then
    echo "repro 汇总缺失（子进程退出 $rc）"
    repro_fail=$((repro_fail + 1)); repro_rc=1
    return
  fi
  if [ "${skipped:-0}" != "0" ]; then
    echo "SKIPPED-NON-CANDIDATE: $skipped 个用例（candidate 模式不计通过）"
  fi
  repro_ran=$((repro_ran + total))
  repro_fail=$((repro_fail + failed))
  case "${gsec:-}" in ''|*[!0-9]*) gsec=0 ;; esac
  case "${rsec:-}" in ''|*[!0-9]*) rsec=0 ;; esac
  green_seconds=$((green_seconds + gsec))
  red_seconds=$((red_seconds + rsec))
  if [ "$rc" -ne 0 ] && [ "${failed:-0}" -eq 0 ]; then
    echo "repro 退出码 $rc 与汇总不一致"
    repro_fail=$((repro_fail + 1))
  fi
  [ "$rc" -eq 0 ] || repro_rc=1
}

# 执行记录解析：`name:kind:expect:fixture:script` 五段固定顺序（plan.py 是唯一产出点）。
record_name() { printf '%s' "${1%%:*}"; }
record_field() {
  local record=$1 index=$2
  printf '%s' "$record" | cut -d: -f"$index"
}
record_script() { printf '%s' "${1##*:}"; }

# ---- 已知技术债清单（必过门的唯一豁免来源）---------------------------------
# 这些套件当前是红的、且原因已登记；它们**不阻塞**必过门，但会被单独列出。
# 一旦它们转绿，本脚本会失败并提示从清单里移除 —— 清单不允许腐烂。
# 2026-11-10：cp3/r67/r68/r69/r70/r71 已全部修绿，清单清空——现在**没有豁免**。
# 以后要加条目，必须同时在 task 记录里写明"为什么现在修不了、谁来修"，否则不许进清单。
KNOWN_LEGACY="${WF_KNOWN_LEGACY-}"

JOBS=$PLAN_JOBS
EXECUTION_MODE=serial
FALLBACK_REASON=""
RESULTS_MARK="$RESULTS_DIR/lines"

# 单元记录只由 plan.py 产出；一切按名字消费的点（lines/.timing/gate/计数）都取记录第一段。
UNIT_RECORDS=($PLAN_UNITS)
UNIT_NAMES=()
for rec in "${UNIT_RECORDS[@]}"; do UNIT_NAMES+=("$(record_name "$rec")"); done
ALL_NAMES="${UNIT_NAMES[*]}"
if [ "${#UNIT_RECORDS[@]}" -eq 0 ]; then
  echo "PLAN-EMPTY: 没有可执行单元"
  fail=$((fail+1))
fi

: > "$RESULTS_MARK"
repro_fail=0
repro_rc=0
repro_seconds=0
REPRO_PID=""
REPRO_STARTED=0
if [ "$PLAN_REPRO_ENABLED" = "1" ] && [ "$PLAN_REPRO_CONCURRENT" = "1" ]; then
  echo "（repro 与主池并发：显式开关 --repro-concurrent）"
  REPRO_STARTED=$(now_ms)
  (
    run_repro
    printf 'REPRO_RAN=%s\nREPRO_FAIL=%s\nREPRO_GREEN=%s\nREPRO_RED=%s\nREPRO_RC=%s\n' \
      "$repro_ran" "$repro_fail" "$green_seconds" "$red_seconds" "$repro_rc" \
      > "$RESULTS_DIR/repro.counters"
  ) &
  REPRO_PID=$!
fi

# 仓库副本位于 /tmp 时，unshare 里挂的 tmpfs 会把 /tmp 遮住，子进程看不到输入与结果文件。
if [ "$JOBS" -gt 1 ]; then
  case "$HERE" in
    /tmp/*) echo "（套件目录在 /tmp 下：unshare 会遮住输入路径，改用串行）"; JOBS=1; FALLBACK_REASON="repository-under-tmp" ;;
  esac
fi

# ---- 执行：一个池 + 一个 worker（WF_NAMESPACE 决定执行域）------------------
# worker 是子进程：执行所需的路径变量必须先导出（两段共用同一份）。
export FIX HERE PY SHARED_RELEASE RESULTS_DIR SOURCE_HOME WF_INSTALL_REF
export WF_FIXTURE_DEPLOY WF_ISOLATED_UNITS
POOL_STARTED=$(now_ms)
if [ "$JOBS" -gt 1 ] && [ -n "$PLAN_UNITS_PARALLEL" ] && can_unshare; then
  EXECUTION_MODE=unshare
  echo "（并行：$JOBS worker（unshare 隔离）；串行段 $(printf '%s' "$PLAN_UNITS_SERIAL" | wc -w) 个单元）"
  xargs_rc=0
  printf '%s\n' $PLAN_UNITS_PARALLEL | xargs -P "$JOBS" -I{} unshare -Urm bash "$HERE/run_one.sh" {} || xargs_rc=$?
  for rec in $PLAN_UNITS_SERIAL; do
    WF_NAMESPACE=0 bash "$HERE/run_one.sh" "$rec"
  done
  if [ "$xargs_rc" -ne 0 ]; then
    echo "XARGS-EXIT: $xargs_rc"; fail=$((fail+1))
  fi
else
  if [ "$JOBS" -gt 1 ]; then
    if ! can_unshare; then FALLBACK_REASON="unshare-unavailable"
    elif [ -z "$PLAN_UNITS_PARALLEL" ]; then FALLBACK_REASON="all-units-require-serial"
    else FALLBACK_REASON="parallel-worker-capability-unavailable"
    fi
    echo "（$FALLBACK_REASON：退回串行）"
  else
    echo "（串行：逐单元执行）"
  fi
  JOBS=1
  # 串行域 = 宿主 /tmp + 无 unshare（与今天 --serial 的可观测语义一致，是 AC1 的对拍面）。
  for rec in "${UNIT_RECORDS[@]}"; do
    if [ -f "$CANCEL_REQUEST" ]; then
      echo "CANCEL-REQUESTED: 停止调度剩余单元"
      break
    fi
    WF_NAMESPACE=0 bash "$HERE/run_one.sh" "$rec"
  done
fi
POOL_SECONDS=$(( ($(now_ms) - POOL_STARTED) / 1000 ))
if [ "$BUILD_OK" = 0 ]; then
  fail=$((fail + 1))
fi

# ---- 完整性判定（唯一实现 results_gate.py）：两段都结束后对名字全集判一次 ---
sort -t$'\t' -k1 "$RESULTS_MARK" | awk -F'\t' '{printf "%-18s rc=%s %ss %s | %s\n", $1, $2, $3, $4, $5}'
gate_rc=0
gate_out=$("$PY" "$HERE/results_gate.py" --lines "$RESULTS_MARK" --expected "$ALL_NAMES") || gate_rc=$?
if [ -z "$gate_out" ]; then
  # gate helper 崩溃/无输出：按“未验证”失败，不留下未绑定变量把脚本打断。
  echo "RESULTS-GATE-FAILED: rc=$gate_rc（结果行未判定）"
  gate_out="GATE_MALFORMED=0
GATE_UNIQUE=0
GATE_MISSING=
GATE_DUPLICATE=
GATE_UNEXPECTED=
GATE_BAD="
  fail=$((fail + 1))
fi
eval "$gate_out" || { echo "GATE-EVAL-FAILED"; fail=$((fail + 1)); }
GATE_MALFORMED=${GATE_MALFORMED:-0}
GATE_MISSING=${GATE_MISSING:-}
GATE_DUPLICATE=${GATE_DUPLICATE:-}
GATE_UNEXPECTED=${GATE_UNEXPECTED:-}
GATE_BAD=${GATE_BAD:-}
if [ "$GATE_MALFORMED" -ne 0 ]; then
  echo "MALFORMED-RESULTS: $GATE_MALFORMED 行"
fi
if [ -n "$GATE_MISSING" ]; then
  echo "MISSING-RESULTS:$GATE_MISSING（子进程未产出结果行）"
fi
if [ -n "$GATE_DUPLICATE" ]; then
  echo "DUPLICATE-RESULTS: $GATE_DUPLICATE"
fi
if [ -n "$GATE_UNEXPECTED" ]; then
  echo "UNEXPECTED-RESULTS:$GATE_UNEXPECTED"
fi
fail=$((fail + GATE_MALFORMED + $(printf '%s' "$GATE_MISSING" | wc -w)
         + $(printf '%s' "$GATE_DUPLICATE" | wc -w) + $(printf '%s' "$GATE_UNEXPECTED" | wc -w)
         + $(printf '%s' "$GATE_BAD" | wc -w)))

# ---- 计数一次派生：lines（唯一结果集）× 注册表 kind（记录第二段）-----------
counts=$("$PY" - "$RESULTS_MARK" "$PLAN_UNITS" <<'PY'
import sys

kinds = {}
for record in sys.argv[2].split():
    parts = record.split(":")
    if len(parts) >= 2:
        kinds[parts[0]] = parts[1]
suite = flow = 0
seen = set()
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
except OSError:
    lines = []
for line in lines:
    parts = line.split("\t")
    if len(parts) != 5 or parts[0] in seen:
        continue
    seen.add(parts[0])
    kind = kinds.get(parts[0])
    if kind in ("suite", "candidate"):
        suite += 1
    elif kind in ("flow", "extra"):
        flow += 1
print(suite, flow)
PY
) || { echo "COUNTS-DERIVATION-FAILED"; fail=$((fail+1)); counts="0 0"; }
read -r suite_ran flow_ran <<< "$counts"

# 计时：全部单元的 .timing 在两段结束后一次累加（worker 只写自己的文件）。
init_millis=0
suite_millis=0
for name in "${UNIT_NAMES[@]}"; do add_init_millis "$name"; done

# ---- repro（默认在主池之后串行；--repro-concurrent 走上面的后台通道）------
if [ "$PLAN_REPRO_ENABLED" = "1" ]; then
  if [ -n "$REPRO_PID" ]; then
    wait "$REPRO_PID" || true
    if [ -f "$RESULTS_DIR/repro.counters" ]; then
      # shellcheck disable=SC1091
      . "$RESULTS_DIR/repro.counters"
      repro_ran=${REPRO_RAN:-0}
      repro_fail=${REPRO_FAIL:-0}
      green_seconds=${REPRO_GREEN:-0}
      red_seconds=${REPRO_RED:-0}
      repro_rc=${REPRO_RC:-1}
    else
      echo "REPRO-COUNTERS-MISSING"
      repro_fail=$((repro_fail + 1))
    fi
    repro_seconds=$(( ($(now_ms) - REPRO_STARTED) / 1000 ))
  else
    REPRO_STARTED=$(now_ms)
    run_repro
    repro_seconds=$(( ($(now_ms) - REPRO_STARTED) / 1000 ))
  fi
  fail=$((fail + repro_fail))
fi

# ---- 必过门核算：区分"未登记的红"与"已登记的债" ------------------------------
legacy_failed=""
legacy_fixed=""
legacy_missing=""
if [ -f "$RESULTS_MARK" ]; then
  for suite in $KNOWN_LEGACY; do
    # 子集模式（WF_SUITES）下没有参与的套件不算"清单过期"：那是没跑，不是没结果
    case " ${UNIT_NAMES[*]} " in *" $suite "*) ;; *) continue ;; esac
    state=$(awk -F'\t' -v s="$suite" 'NF==5 && $1==s {print $4}' "$RESULTS_MARK" | head -1)
    case "$state" in
      bad)  legacy_failed="$legacy_failed $suite" ;;
      ok)   legacy_fixed="$legacy_fixed $suite" ;;
      "")   legacy_missing="$legacy_missing $suite" ;;
    esac
  done
fi
if [ -n "$legacy_failed" ]; then
  echo "LEGACY-DEBT:$legacy_failed（已登记的技术债，不阻塞必过门；修好后请从 KNOWN_LEGACY 移除）"
fi
if [ -n "$legacy_fixed" ]; then
  echo "LEGACY-FIXED:$legacy_fixed（已转绿，请从 KNOWN_LEGACY 移除，使其成为必过项）"
fi
if [ -n "$legacy_missing" ]; then
  echo "LEGACY-MISSING:$legacy_missing（清单里的套件没有结果行；清单过期或套件被删除）"
fi

debt=$(printf '%s' "$legacy_failed" | wc -w)
stale=$(( $(printf '%s' "$legacy_fixed" | wc -w) + $(printf '%s' "$legacy_missing" | wc -w) ))
unknown_fail=$(( fail - debt ))
total_millis=$(( $(now_ms) - TOTAL_STARTED )); total_seconds=$((total_millis / 1000))
units_total=$((suite_ran + flow_ran + repro_ran))

# ---- 产品发行树必须没被测试改写 ---------------------------------------------
PRODUCT_AFTER=$(product_digest)
if [ "$PRODUCT_BEFORE" != "$PRODUCT_AFTER" ]; then
  echo "PRODUCT-TREE-CHANGED: docs/workflows/wf-release 在运行期间被改写（测试不得写产品发行树）"
  echo "  before=$PRODUCT_BEFORE"
  echo "  after =$PRODUCT_AFTER"
  unknown_fail=$((unknown_fail + 1))
fi

# ---- 源树卫生：运行后 delta 判定（新增 → 失败标签；存量只警告）---------------
hygiene_rc=0
"$PY" "$HERE/source_hygiene.py" check "$REPO_ROOT" --expect "$HYGIENE_SNAPSHOT" || hygiene_rc=$?
if [ "$hygiene_rc" -ne 0 ]; then
  echo "SOURCE-TREE-POLLUTED: 运行期在源树新增了字节码产物（明细见上）"
  unknown_fail=$((unknown_fail + 1))
fi

# 模板缓存构建序列次数（design §3.3）：命中=0，发布一次=1；模板机制关闭=0。
TEMPLATE_BUILD_SEQUENCES=0
if [ "$PLAN_NO_TEMPLATE" != "1" ] && [ "$HEAD_READABLE" = "1" ] && [ "$TEMPLATE_CACHE_HIT" = "0" ]; then
  TEMPLATE_BUILD_SEQUENCES=1
fi

# ---- 取消请求在收口前出现：不得签成功 -----------------------------------------
if [ -f "$CANCEL_REQUEST" ]; then
  echo "CANCEL-REQUESTED: 运行被取消，跳过成功出口"
  unknown_fail=$((unknown_fail + 1))
fi

# ---- 已拥有资源清理：必须在发布摘要与成功出口之前确认 ---------------------------
# 先聚合每个命令的 cleanup 结论：命令级 unknown/failed 时保留现场，不删除夹具。
cleanup_unknown_out=$("$PY" "$HERE/runner_cleanup.py" --results-dir "$RESULTS_DIR" --format sh) || true
eval "$cleanup_unknown_out" || { echo "CLEANUP-STATE-EVAL-FAILED"; unknown_fail=$((unknown_fail + 1)); }
if [ "${CLEANUP_UNKNOWN_COUNT:-0}" -gt 0 ]; then
  echo "CLEANUP-UNKNOWN: 命令级清理未确认（${CLEANUP_UNKNOWN:-unknown}）；保留夹具/现场，不重试"
  echo "恢复步骤：核对 EXECUTION-FAILED 里的 command/guardian/supervisor/target 身份，确认无存活持有者后再人工回收。"
  unknown_fail=$((unknown_fail + 1))
  CLEANUP_STATE=unknown
  CLEANUP_DONE=1
else
  cleanup_rc=0
  cleanup_fixtures || cleanup_rc=$?
  if [ "$cleanup_rc" -ne 0 ]; then
    echo "CLEANUP-FAILED: 本 run 拥有的夹具/模板未能回收（见 $RESULTS_DIR/cleanup.err）"
    unknown_fail=$((unknown_fail + 1))
  fi
  CLEANUP_DONE=1
  if [ "$cleanup_rc" -ne 0 ]; then CLEANUP_STATE=failed; else CLEANUP_STATE=cleaned; fi
fi

# ---- 失败计数拆分：lines 的 bad 行由 summary 从实际结果集派生 ------------------
bad_lines=$(printf '%s' "$GATE_BAD" | wc -w)
extra_failures=$(( unknown_fail - bad_lines ))
[ "$extra_failures" -lt 0 ] && extra_failures=0

# ---- 摘要：计数从实际结果集 × 注册 kind 派生，原子发布 + 读回，失败即非零 --------
METRICS_JSON="$RESULTS_DIR/summary-metrics.json"
WF_METRICS_JSON="$METRICS_JSON" \
WF_METRICS_MODE="$PLAN_MODE" WF_METRICS_FULL_MODE="$PLAN_FULL_MODE" \
WF_METRICS_DEPLOY="$PLAN_FIXTURE_DEPLOY" \
WF_METRICS_REPRO_RAN="$repro_ran" WF_METRICS_REPRO_FAIL="$repro_fail" \
WF_METRICS_DEBT="$debt" WF_METRICS_BUILD="$build_seconds" WF_METRICS_TEMPLATE="$TEMPLATE_SECONDS" \
WF_METRICS_INIT_MS="$init_millis" WF_METRICS_SUITE_MS="$suite_millis" \
WF_METRICS_GREEN="$green_seconds" WF_METRICS_RED="$red_seconds" \
WF_METRICS_TOTAL_MS="$total_millis" WF_METRICS_EFFECTIVE_JOBS="$JOBS" \
WF_METRICS_EXECUTION_MODE="$EXECUTION_MODE" WF_METRICS_FALLBACK="$FALLBACK_REASON" \
WF_METRICS_REPRO_MODE="$PLAN_REPRO_MODE" WF_METRICS_REPRO_GROUPS="$PLAN_REPRO_GROUPS" \
WF_METRICS_POOL_SECONDS="$POOL_SECONDS" WF_METRICS_REPRO_SECONDS="$repro_seconds" \
WF_METRICS_REPRO_CONCURRENT="$PLAN_REPRO_CONCURRENT" \
WF_METRICS_PYCACHE_ROOT="${PYTHONPYCACHEPREFIX:-}" \
WF_METRICS_TEMPLATE_SOURCE="$TEMPLATE_SOURCE" \
WF_METRICS_TEMPLATE_CACHE_HIT="$TEMPLATE_CACHE_HIT" \
WF_METRICS_TEMPLATE_CACHE_KEY="$TEMPLATE_CACHE_KEY" \
WF_METRICS_TEMPLATE_SEQUENCES="$TEMPLATE_BUILD_SEQUENCES" \
WF_METRICS_JOBS="$PLAN_JOBS" WF_METRICS_REPRO_JOBS="$PLAN_REPRO_JOBS" \
WF_METRICS_GATE_MALFORMED="$GATE_MALFORMED" WF_METRICS_GATE_MISSING="$(printf '%s' "$GATE_MISSING" | wc -w)" \
WF_METRICS_GATE_DUPLICATE="$(printf '%s' "$GATE_DUPLICATE" | wc -w)" \
WF_METRICS_GATE_UNEXPECTED="$(printf '%s' "$GATE_UNEXPECTED" | wc -w)" \
WF_METRICS_EXTRA_FAILURES="$extra_failures" \
WF_METRICS_CLEANUP_STATE="$CLEANUP_STATE" \
"$PY" - <<'PY'
import json, os


def release_build():
    """从 controlled 阶段的 release-context 搬运构建状态（built/reused/checked）。"""
    path = os.environ.get("WF_RELEASE_CONTEXT")
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return (json.load(handle) or {}).get("release_build")
    except (OSError, ValueError):
        return None


def number(name, default=0):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


metrics = {
    "mode": os.environ.get("WF_METRICS_MODE"),
    "full_mode": number("WF_METRICS_FULL_MODE"),
    "fixture_deploy": os.environ.get("WF_METRICS_DEPLOY"),
    "repro_ran": number("WF_METRICS_REPRO_RAN"),
    "repro_fail": number("WF_METRICS_REPRO_FAIL"),
    "legacy_debt": number("WF_METRICS_DEBT"),
    "build_seconds": number("WF_METRICS_BUILD"),
    "template_seconds": number("WF_METRICS_TEMPLATE"),
    "init_millis": number("WF_METRICS_INIT_MS"),
    "suite_millis": number("WF_METRICS_SUITE_MS"),
    "green_seconds": number("WF_METRICS_GREEN"),
    "red_seconds": number("WF_METRICS_RED"),
    "total_seconds": round(number("WF_METRICS_TOTAL_MS") / 1000, 3),
    "effective_jobs": number("WF_METRICS_EFFECTIVE_JOBS"),
    "execution_mode": os.environ.get("WF_METRICS_EXECUTION_MODE"),
    "fallback_reason": os.environ.get("WF_METRICS_FALLBACK"),
    "repro_mode": os.environ.get("WF_METRICS_REPRO_MODE"),
    "repro_groups": (os.environ.get("WF_METRICS_REPRO_GROUPS") or "").split(),
    "pool_seconds": number("WF_METRICS_POOL_SECONDS"),
    "repro_seconds": number("WF_METRICS_REPRO_SECONDS"),
    "repro_concurrent": os.environ.get("WF_METRICS_REPRO_CONCURRENT") == "1",
    "pycache_root": os.environ.get("WF_METRICS_PYCACHE_ROOT"),
    "template_source": os.environ.get("WF_METRICS_TEMPLATE_SOURCE"),
    "template_cache_hit": os.environ.get("WF_METRICS_TEMPLATE_CACHE_HIT") == "1",
    "template_cache_key": os.environ.get("WF_METRICS_TEMPLATE_CACHE_KEY") or None,
    "template_reused": os.environ.get("WF_TEMPLATE_READY") == "1",
    "template_build_sequences": number("WF_METRICS_TEMPLATE_SEQUENCES"),
    "jobs": number("WF_METRICS_JOBS"),
    "requested_jobs": number("WF_METRICS_JOBS"),
    "repro_jobs": number("WF_METRICS_REPRO_JOBS"),
    "release_build": release_build(),
    "gate_malformed": number("WF_METRICS_GATE_MALFORMED"),
    "gate_missing": number("WF_METRICS_GATE_MISSING"),
    "gate_duplicate": number("WF_METRICS_GATE_DUPLICATE"),
    "gate_unexpected": number("WF_METRICS_GATE_UNEXPECTED"),
    "extra_failures": number("WF_METRICS_EXTRA_FAILURES"),
    "cleanup_state": os.environ.get("WF_METRICS_CLEANUP_STATE") or "unknown",
}
path = os.environ["WF_METRICS_JSON"]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(metrics, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
PY
if [ $? -ne 0 ]; then
  echo "SUMMARY-METRICS-FAILED: 无法采集摘要输入"
  unknown_fail=$((unknown_fail + 1))
fi

summary_rc=0
if [ -f "$RESULTS_DIR/plan.json" ] && [ -n "${WF_FRAME_CONTEXT_FILE:-}" ] && [ -f "$METRICS_JSON" ]; then
  "$PY" "$HERE/results_summary.py" --results-dir "$RESULTS_DIR" \
    --plan-file "$RESULTS_DIR/plan.json" --context-file "$WF_FRAME_CONTEXT_FILE" \
    --lines "$RESULTS_MARK" --metrics "$METRICS_JSON" || summary_rc=$?
else
  echo "SUMMARY-INPUTS-MISSING: 缺少冻结 plan/context 或 metrics"
  summary_rc=1
fi
if [ "$summary_rc" -ne 0 ]; then
  echo "SUMMARY-FAILED: 摘要未成功发布（非零 $summary_rc）；不输出 GATE-OK"
  unknown_fail=$((unknown_fail + 1))
fi

echo "---- 运行 $units_total 项（套件 $suite_ran，流程/extra $flow_ran，repro $repro_ran），失败 $fail 项（其中已登记债 $debt 项）----"
echo "---- 计时 build=${build_seconds}s template=${TEMPLATE_SECONDS}s init=$((init_millis/1000))s suite=$((suite_millis/1000))s green=${green_seconds}s red=${red_seconds}s total=${total_seconds}s ----"
if [ "$unknown_fail" -ne 0 ] || [ "$stale" -ne 0 ]; then
  [ "$unknown_fail" -ne 0 ] && echo "GATE-FAIL: 未登记的失败 $unknown_fail 项（必过门未通过）"
  [ "$stale" -ne 0 ] && echo "GATE-BOOKKEEPING: 豁免清单有 $stale 项需要销账（转绿或已不存在）"
  exit 1
fi
echo "GATE-OK: 必过门通过（豁免中的债：$(printf '%s' "$legacy_failed" | wc -w) 项）"
exit 0
