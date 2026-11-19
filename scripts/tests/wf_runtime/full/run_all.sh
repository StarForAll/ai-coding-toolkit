#!/bin/bash
# 全量/子集/代表集复现：每个套件都从干净夹具开始；任一环节失败都会让脚本以非零码退出。
# 选择与冲突判定在 `plan.py`（唯一 plan()）；本脚本只用它的计划执行，避免两份选择逻辑。
# 详细用法：run_all.sh --help
set -uo pipefail
# 路径/scope 校验完成之前一律禁写 pyc，并丢弃外部注入的 pycache 前缀：
# public/preflight/--list/--dry-run 不得在任何位置（含域外 WF_PYCACHE）产生写入。
# 内部 frame 重入（lease/execute）继承父阶段已批准的 pycache，不得清除。
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
  bash run_all.sh --template-cache                        # 显式申请跨 run 模板复用（默认只用本次模板）
  bash run_all.sh --list | --dry-run                      # 只输出计划

环境：WF_JOBS（套件层并行，默认 min(8,cpu)；--serial 或 WF_JOBS=1 退回串行）、
      WF_REPRO_JOBS（repro 用例层并行，默认 min(8,cpu)）、
      WF_WITH_REPRO=1（子集模式开 repro）、WF_RESULTS_DIR、WF_RESULTS_CACHE（退役候选
      报告根，默认 ~/.cache/wf-test-run）、WF_FIX、WF_NO_RUN=1（计划后即退出）、
      WF_NO_TEMPLATE=1（逐套件重建夹具；默认在 run 内构建一次夹具模板后逐套件 cp -a）
默认只写本次结果/夹具/私有测试发行；跨 run 模板复用用 --template-cache 显式申请，
历史结果轮转只由 prune-results 报告，删除走 inventory-results + retire-results。
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
# public 没有前缀；lease/execute 是同一脚本的两次重入，只有两次计划。
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
    # 真实执行在冻结计划前只分配一次执行身份：隐式路径与 owner 共用它，PID 重用不会同名。
    # public 每次调用都新建（不继承外层进程可能泄漏的旧身份）。
    WF_RUN_IDENTITY=$("$PY" "$HERE/resource_lifecycle.py" new-id) || exit 2
    export WF_RUN_IDENTITY
    # 管理路径的唯一规则（wf_test_paths）：scope 下默认值从 scope 派生，显式域外值在
    # 首次写前拒绝；无 scope 时保持历史默认。layout 只派生/校验，不写任何文件。
    if ! layout_out=$("$PY" "$PATH_HELPER" layout --kind run --pid "$$" \
        --identity "$WF_RUN_IDENTITY" --format sh); then
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
          "$1" "$2" claim-plan "$3" || exit 1
          "$1" "$4" --format json -- "${@:5}" >/dev/null || exit 2' \
          lease-mirror "$PY" "$HERE/resource_lifecycle.py" "$WF_RESULTS_DIR" "$HERE/plan.py" -- "$@"
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
    # 初始化只有一次：owner 意图 → active state → 按旧代许可 prepare（helper 内三个 checkpoint）。
    begin_out=$("$PY" "$HERE/resource_lifecycle.py" begin-run \
        --results-root "$WF_RESULTS_DIR" --role full --intent execution \
        --run-id "$WF_RUN_IDENTITY" --format sh)
    begin_rc=$?
    if [ "$begin_rc" -ne 0 ]; then
      echo "RESULTS-INIT-FAILED: 初始化拒绝（rc=$begin_rc）；不启动 controller、不清理现场" >&2
      exit "$begin_rc"
    fi
    eval "$begin_out" || { echo "RUN-ID-EVAL-FAILED" >&2; exit 2; }
    export WF_RUN_ID="$RUN_ID"
    export WF_COMMAND_EVIDENCE_ROOT="$WF_RESULTS_DIR/commands"
    note_stage public
    note_stage lease
    # 计划调用计数：preflight 的一行来自内存（public 阶段不落任何文件），final plan 由
    # plan.py 自己追加到同一文件；复用结果目录时这两个文件都已在 begin-run 的 prepare 清空。
    if [ -n "${WF_PREFLIGHT_PLAN_LINE:-}" ]; then
      printf '%s\n' "$WF_PREFLIGHT_PLAN_LINE" >> "$WF_RESULTS_DIR/plan-calls"
    fi
    export WF_PLAN_LOG="$WF_RESULTS_DIR/plan-calls"
    export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$WF_RESULTS_DIR/pycache}"
    mkdir -p "$PYTHONPYCACHEPREFIX"
    # 默认执行不盘点/不轮转/不观察历史材料：这些只在显式维护入口发生。
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
    if [ -n "${PLAN_EXCLUDED_UNITS:-}" ]; then
      echo "（候选资格排除：$PLAN_EXCLUDED_UNITS）"
    fi
    export WF_FIX="$FIX" WF_ISOLATED_UNITS="${PLAN_ISOLATED_UNITS:-}"
    LEGACY_FIXTURE_ROOT="$FIX.legacy"
    WF_LEGACY_FIXTURE_ROOT="$LEGACY_FIXTURE_ROOT"
    export WF_LEGACY_FIXTURE_ROOT
    "$PY" "$SCOPE_HELPER" validate "$FIX" --forbid "$RESULTS_DIR" \
      --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
    mkdir -p "$RESULTS_DIR"
    "$PY" "$SCOPE_HELPER" reset "$LEGACY_FIXTURE_ROOT" --forbid "$RESULTS_DIR" \
      --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
    # controller 显式白名单继承 fixture/result FD：不依赖 Popen 默认，也不传其他 FD。
    # 发行消费锁由 controller 自己取得并贯穿整次运行（不在受监督子链里再次取锁）。
    pass_fds="${WF_FIXTURE_LEASE_FD},${WF_RESULTS_LOCK_FD}"
    export WF_RUNNER_CONTROL_PID=$$
    exec "$PY" "$HERE/execution.py" --runner-control --name wf-runner \
      --runner-role full --results-root "$WF_RESULTS_DIR" --run-id "$WF_RUN_ID" \
      --plan-file "$PLAN_FILE" --plan-sha256 "$TOKEN_SHA256" --plan-size "$TOKEN_SIZE" \
      --timeout "${WF_RUN_TIMEOUT:-1800}" --log "$RESULTS_DIR/.runner.log" \
      --result "$RESULTS_DIR/.runner.json" --pass-fds "$pass_fds" -- \
      bash "$0"
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
    if [ -n "${PLAN_EXCLUDED_UNITS:-}" ]; then
      echo "（候选资格排除：$PLAN_EXCLUDED_UNITS）"
    fi
    export WF_FIX="$FIX" WF_ISOLATED_UNITS="${PLAN_ISOLATED_UNITS:-}"
    export WF_RUN_ID="${WF_RUN_ID:?missing run id from lease begin_run}"
    export WF_COMMAND_EVIDENCE_ROOT="$RESULTS_DIR/commands"
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
# 取消协议：本代唯一标记由 root controller 指定并交接（WF_CANCEL_FILE），shell 既不派生也不
# 删除它。收到 INT/TERM/HUP 时只用排他创建发布请求并保留信号退出码；已有标记视为已发布。
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
# 本 shell 不再拥有资源删除或取消标记重置：root controller 在同一 C 进程收口。
trap 'publish_cancel TERM; exit 143' TERM
trap 'publish_cancel INT; exit 130' INT
trap 'publish_cancel HUP; exit 129' HUP

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
STRUCTURAL_FAIL=0
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

# 发行准备已由 root controller 完成并交接 release-context：execute 只消费已核 env。
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
  local args=()
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    # 候选模板身份还包含已核 tag commit：缺它就不能复用/接受已消费模板。
    args=(--version "$PLAN_RELEASE_VERSION" --ref "$PLAN_RELEASE_REF"
          --commit "${WF_RELEASE_COMMIT:?candidate template requires the verified commit}")
  fi
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
           --release-root "$PLAN_RELEASE_ROOT" --subject "$RELEASE_SUBJECT"
           --commit "${WF_RELEASE_COMMIT:?candidate template requires the verified commit}")
  fi
  "$PY" "$HERE/template_cache.py" "$sub" "${args[@]}" "$@"
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
    if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ] && [ -z "$RELEASE_SUBJECT" ]; then
      RELEASE_SUBJECT=$(release_subject_digest) || { echo "RELEASE-SUBJECT-FAILED"; exit 1; }
    fi
    # 唯一修改型入口：恢复 → 迁移 → 命中 → 必要时发布（顺序只在 template_cache.acquire）。
    if ! acquired=$(template_cache_cli acquire); then
      echo "TEMPLATE-CACHE-FAILED"
      exit 1
    fi
    unset WF_TEMPLATE_TXN_REBUILD
    TEMPLATE_CACHE_KEY=$(printf '%s\n' "$acquired" | sed -n '2p')
    TEMPLATE_ENTRY="$TEMPLATE_CACHE_ROOT/$TEMPLATE_CACHE_KEY"
    WF_TEMPLATE="$TEMPLATE_ENTRY"
    WF_TEMPLATE_SOURCE=$(printf '%s\n' "$acquired" | sed -n '1p')
    WF_TEMPLATE_READY=1
    TEMPLATE_SOURCE=cache
    if [ "$(printf '%s\n' "$acquired" | sed -n '4p')" = "TEMPLATE-CACHE-HIT=1" ]; then
      TEMPLATE_CACHE_HIT=1
      echo "（模板缓存命中：$TEMPLATE_ENTRY）"
    else
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
  # 内嵌 repro 复用父 C 的租约与 context：参数全部来自父冻结计划，不再重传公开 argv。
  # 失败计数写进 repro_fail（不直接改 STRUCTURAL_FAIL）：并发开关下它跑在子 shell 里，父进程按计数器合并。
  FRAME=()
  repro_frame=$("$PY" "$HERE/runner_protocol.py" encode-repro --stage repro-inner \
    --entry-pid "${WF_RUNNER_CONTROL_PID:?missing controller pid}" \
    --results-root "$WF_RESULTS_DIR" --results-explicit "${WF_FRAME_RESULTS_EXPLICIT:-0}" \
    --scope-root "${WF_FRAME_SCOPE_ROOT:--}" \
    --plan-file "$WF_FRAME_PLAN_FILE" --plan-sha256 "$WF_FRAME_PLAN_SHA256" \
    --plan-size "$WF_FRAME_PLAN_SIZE" \
    --context-file "$WF_FRAME_CONTEXT_FILE" --context-sha256 "$WF_FRAME_CONTEXT_SHA256" \
    --context-size "$WF_FRAME_CONTEXT_SIZE") \
    || { echo "REPRO-FRAME-FAILED"; repro_fail=$((repro_fail + 1)); repro_rc=1; return; }
  eval "$repro_frame" || { echo "REPRO-FRAME-EVAL-FAILED"; repro_fail=$((repro_fail + 1)); repro_rc=1; return; }
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
  bundle_sha=$(printf '%s\n' "$out" | sed -n 's/^REPRO_BUNDLE_SHA256=//p' | head -1)
  bundle_size=$(printf '%s\n' "$out" | sed -n 's/^REPRO_BUNDLE_SIZE=//p' | head -1)
  case "$bundle_sha" in
    *[!0-9a-f]*|'') : ;;
    *) case "$bundle_size" in
         ''|*[!0-9]*) : ;;
         *) printf '{"sha256":"%s","size":%s}\n' "$bundle_sha" "$bundle_size" \
              > "$RESULTS_DIR/repro/repro.bundle.json" ;;
       esac ;;
  esac
}

# 执行记录解析：`name:kind:expect:fixture:script` 五段固定顺序（plan.py 是唯一产出点）。
record_name() { printf '%s' "${1%%:*}"; }
record_field() {
  local record=$1 index=$2
  printf '%s' "$record" | cut -d: -f"$index"
}
record_script() { printf '%s' "${1##*:}"; }

# 已知技术债清单只由 root controller 从 WF_KNOWN_LEGACY 快照并交给 assess_run_results；
# 本 shell 不再单独计算 debt/stale，也不再拥有成功/失败出口。

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
  STRUCTURAL_FAIL=$((STRUCTURAL_FAIL+1))
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
    echo "XARGS-EXIT: $xargs_rc"; STRUCTURAL_FAIL=$((STRUCTURAL_FAIL+1))
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
    if [ -n "${WF_CANCEL_FILE:-}" ] && [ -f "$WF_CANCEL_FILE" ]; then
      echo "CANCEL-REQUESTED: 停止调度剩余单元"
      break
    fi
    WF_NAMESPACE=0 bash "$HERE/run_one.sh" "$rec"
  done
fi
POOL_SECONDS=$(( ($(now_ms) - POOL_STARTED) / 1000 ))
if [ "$BUILD_OK" = 0 ]; then
  STRUCTURAL_FAIL=$((STRUCTURAL_FAIL + 1))
fi

# ---- 结果行诊断：逐行打印（完整性判定只在 assess_run_results 一处）------------
sort -t$'\t' -k1 "$RESULTS_MARK" | awk -F'\t' '{printf "%-18s rc=%s %ss %s | %s\n", $1, $2, $3, $4, $5}'

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
      repro_rc=1
    fi
    repro_seconds=$(( ($(now_ms) - REPRO_STARTED) / 1000 ))
  else
    REPRO_STARTED=$(now_ms)
    run_repro
    repro_seconds=$(( ($(now_ms) - REPRO_STARTED) / 1000 ))
  fi
fi
# repro 入口自身的非零（含唯一 state writer 失败）必须阻断内层成功出口；
# 只依赖 records 结构无法证明本代 repro 证明已提交，因此不能只看 assess 诊断。
if [ "${repro_rc:-0}" -ne 0 ]; then
  echo "REPRO-INNER-FAILED: rc=$repro_rc（state writer/证据汇总未闭合）"
  STRUCTURAL_FAIL=$((STRUCTURAL_FAIL + 1))
fi

# 本段只做两件事：把测量交给 schema1 交接对象，并输出非最终诊断。
# gate/cleanup/成功结论由同 C 进程的 root controller 从当前证据派生（本 shell 不再有成功出口）。
total_millis=$(( $(now_ms) - TOTAL_STARTED )); total_seconds=$((total_millis / 1000))
suite_ran=0; flow_ran=0
for rec in "${UNIT_RECORDS[@]}"; do
  case "$(record_field "$rec" 2)" in
    suite|candidate) suite_ran=$((suite_ran + 1)) ;;
    flow|extra) flow_ran=$((flow_ran + 1)) ;;
  esac
done
units_total=$((suite_ran + flow_ran + repro_ran))
INNER_FAIL=0

# ---- 产品发行树必须没被测试改写 ---------------------------------------------
PRODUCT_AFTER=$(product_digest)
if [ "$PRODUCT_BEFORE" != "$PRODUCT_AFTER" ]; then
  echo "PRODUCT-TREE-CHANGED: docs/workflows/wf-release 在运行期间被改写（测试不得写产品发行树）"
  echo "  before=$PRODUCT_BEFORE"
  echo "  after =$PRODUCT_AFTER"
  INNER_FAIL=1
fi

# ---- 源树卫生：运行后 delta 判定（新增 → 失败标签；存量只警告）---------------
hygiene_rc=0
"$PY" "$HERE/source_hygiene.py" check "$REPO_ROOT" --expect "$HYGIENE_SNAPSHOT" || hygiene_rc=$?
if [ "$hygiene_rc" -ne 0 ]; then
  echo "SOURCE-TREE-POLLUTED: 运行期在源树新增了字节码产物（明细见上）"
  INNER_FAIL=1
fi

# 模板缓存构建序列次数（design §3.3）：命中=0，发布一次=1；模板机制关闭=0。
TEMPLATE_BUILD_SEQUENCES=0
if [ "$PLAN_NO_TEMPLATE" != "1" ] && [ "$PLAN_NO_TEMPLATE_CACHE" = "0" ] \
    && [ "$HEAD_READABLE" = "1" ] && [ "$TEMPLATE_CACHE_HIT" = "0" ]; then
  TEMPLATE_BUILD_SEQUENCES=1
fi

# ---- 取消请求在收口前出现：内层只报告，不删除、不签成功 ------------------------
if [ -n "${WF_CANCEL_FILE:-}" ] && [ -f "$WF_CANCEL_FILE" ]; then
  echo "CANCEL-REQUESTED: 运行被取消，root controller 继续按真实终态收口"
  INNER_FAIL=1
fi

# ---- 测量交接（schema1）：只含计时/并发/模板事实，不含 gate/cleanup/成功结论 ----
MEASUREMENTS_JSON="$RESULTS_DIR/summary-measurements.json"
WF_METRICS_MODE="$PLAN_MODE" WF_METRICS_FULL_MODE="$PLAN_FULL_MODE" \
WF_METRICS_DEPLOY="$PLAN_FIXTURE_DEPLOY" \
WF_METRICS_BUILD="$build_seconds" WF_METRICS_TEMPLATE="$TEMPLATE_SECONDS" \
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
WF_MEASUREMENTS_JSON="$MEASUREMENTS_JSON" "$PY" - <<'MEASUREMENTS'
import json, os


def release_build():
    """从 controller 写的 release-context 搬运构建状态（built/reused/checked）。"""
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


measurements = {
    "mode": os.environ.get("WF_METRICS_MODE"),
    "full_mode": number("WF_METRICS_FULL_MODE"),
    "fixture_deploy": os.environ.get("WF_METRICS_DEPLOY"),
    "execution_mode": os.environ.get("WF_METRICS_EXECUTION_MODE"),
    "fallback_reason": os.environ.get("WF_METRICS_FALLBACK") or "",
    "repro_mode": os.environ.get("WF_METRICS_REPRO_MODE"),
    "repro_groups": (os.environ.get("WF_METRICS_REPRO_GROUPS") or "").split(),
    "repro_concurrent": os.environ.get("WF_METRICS_REPRO_CONCURRENT") == "1",
    "jobs": number("WF_METRICS_JOBS"),
    "requested_jobs": number("WF_METRICS_JOBS"),
    "effective_jobs": number("WF_METRICS_EFFECTIVE_JOBS"),
    "repro_jobs": number("WF_METRICS_REPRO_JOBS"),
    "pycache_root": os.environ.get("WF_METRICS_PYCACHE_ROOT") or "",
    "template_source": os.environ.get("WF_METRICS_TEMPLATE_SOURCE"),
    "template_cache_hit": os.environ.get("WF_METRICS_TEMPLATE_CACHE_HIT") == "1",
    "template_cache_key": os.environ.get("WF_METRICS_TEMPLATE_CACHE_KEY") or None,
    "template_reused": os.environ.get("WF_TEMPLATE_READY") == "1",
    "template_build_sequences": number("WF_METRICS_TEMPLATE_SEQUENCES"),
    "release_build": release_build(),
    "build_seconds": number("WF_METRICS_BUILD"),
    "template_seconds": number("WF_METRICS_TEMPLATE"),
    "init_millis": number("WF_METRICS_INIT_MS"),
    "suite_millis": number("WF_METRICS_SUITE_MS"),
    "green_seconds": number("WF_METRICS_GREEN"),
    "red_seconds": number("WF_METRICS_RED"),
    "total_millis": number("WF_METRICS_TOTAL_MS"),
    "pool_seconds": number("WF_METRICS_POOL_SECONDS"),
    "repro_seconds": number("WF_METRICS_REPRO_SECONDS"),
}
with open(os.environ["WF_MEASUREMENTS_JSON"], "w", encoding="utf-8") as handle:
    json.dump(measurements, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
MEASUREMENTS
if [ $? -ne 0 ]; then
  echo "MEASUREMENTS-FAILED: 无法采集测量输入"
  INNER_FAIL=1
fi

# ---- 非最终诊断：与 controller 共用 assess_run_results（不构成成功出口）--------
REPRO_DIR=""
BUNDLE_SHA=""
BUNDLE_SIZE=""
if [ "$PLAN_REPRO_ENABLED" = "1" ]; then
  REPRO_DIR="$RESULTS_DIR/repro"
  if [ -f "$REPRO_DIR/repro.bundle.json" ]; then
    BUNDLE_SHA=$(sed -n 's/.*"sha256": *"\([0-9a-f]*\)".*/\1/p' "$REPRO_DIR/repro.bundle.json" | head -1)
    BUNDLE_SIZE=$(sed -n 's/.*"size": *\([0-9]*\).*/\1/p' "$REPRO_DIR/repro.bundle.json" | head -1)
  fi
fi
diag_rc=0
"$PY" "$HERE/results_gate.py" --assess-run --plan-file "$RESULTS_DIR/plan.json" \
  --lines "$RESULTS_DIR/lines" ${REPRO_DIR:+--repro-results "$REPRO_DIR"} \
  ${BUNDLE_SHA:+--bundle-sha256 "$BUNDLE_SHA"} ${BUNDLE_SIZE:+--bundle-size "$BUNDLE_SIZE"} \
  --format sh || diag_rc=$?

# ---- 测量交接（schema1，原子写）：失败让本层非零并由 controller 拒绝 --------------
METRICS_FAULT="${WF_METRICS_FAULT:-}"
unset WF_METRICS_FAULT
metrics_ok=1
if [ -f "$MEASUREMENTS_JSON" ]; then
  "$PY" "$HERE/results_summary.py" --write-metrics --results-dir "$RESULTS_DIR" \
    --run-id "$WF_RUN_ID" --role full --plan-file "$RESULTS_DIR/plan.json" \
    --context-file "$WF_FRAME_CONTEXT_FILE" \
    ${REPRO_DIR:+--repro-results "$REPRO_DIR"} \
    ${BUNDLE_SHA:+--bundle-sha256 "$BUNDLE_SHA"} ${BUNDLE_SIZE:+--bundle-size "$BUNDLE_SIZE"} \
    --measurements "$MEASUREMENTS_JSON" ${METRICS_FAULT:+--fault "$METRICS_FAULT"} || metrics_ok=0
else
  echo "METRICS-INPUTS-MISSING"
  metrics_ok=0
fi
[ "$metrics_ok" = "1" ] || INNER_FAIL=1

echo "---- 执行单元 $units_total（套件 $suite_ran，流程/extra $flow_ran，repro $repro_ran）exit=$INNER_FAIL diag=$diag_rc ----"
echo "---- 计时 build=${build_seconds}s template=${TEMPLATE_SECONDS}s init=$((init_millis/1000))s suite=$((suite_millis/1000))s green=${green_seconds}s red=${red_seconds}s total=${total_seconds}s ----"
if [ "$INNER_FAIL" -ne 0 ] || [ "$diag_rc" -ne 0 ] || [ "$STRUCTURAL_FAIL" -ne 0 ]; then
  echo "INNER-TARGET-FAILED: 目标/测量未通过，交给 root controller 按真实证据收口"
  exit 1
fi
echo "INNER-TARGET-OK: 目标结果与测量交接完成；最终成功出口只在 root controller"
exit 0