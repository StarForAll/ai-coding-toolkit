#!/bin/bash
# 全量/子集/代表集复现：每个套件都从干净夹具开始；任一环节失败都会让脚本以非零码退出。
# 选择与冲突判定在 `plan.py`（唯一 plan()）；本脚本只用它的计划执行，避免两份选择逻辑。
# 详细用法：run_all.sh --help
set -uo pipefail
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

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

# 字节码缓存策略（D3.1）：pyc 一律落在仓库与夹具之外。计划前用 bootstrap 前缀——
# 结果目录尚未 claim，先写 pyc 会让“非空无主目录”被 fixture_scope 拒绝；claim/prepare
# 之后改指结果目录（随 run 轮转，可经 WF_PYCACHE 注入）。
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-${TMPDIR:-/tmp}/wf-pycache-bootstrap}"
unset PYTHONDONTWRITEBYTECODE
REPO_ROOT=$(cd "$HERE/../../../.." && pwd)
WF_RESULTS_DIR=${WF_RESULTS_DIR:-$HOME/.cache/wf-test-run/run-$$}
export WF_RESULTS_DIR

if [ "${WF_RUNNER_ENTRY_PID:-}" != "$$" ] || [ -z "${WF_FIXTURE_LEASE_FD:-}" ] \
  || ! "$PY" "$HERE/fixture_scope.py" check-lease >/dev/null 2>&1; then
  export WF_RUNNER_ENTRY_PID=$$
  exec "$PY" "$HERE/fixture_scope.py" lease -- bash "$0" "$@"
fi
"$PY" "$HERE/fixture_scope.py" claim-results "$WF_RESULTS_DIR" || exit 1
if [ -z "${WF_RUNNER_CONTROL_PID:-}" ]; then
  export WF_RUNNER_CONTROL_PID=$$
  exec "$PY" "$HERE/execution.py" --runner-control --name wf-runner \
    --timeout "${WF_RUN_TIMEOUT:-1800}" --log "$WF_RESULTS_DIR/.runner.log" \
    --result "$WF_RESULTS_DIR/.runner.json" -- bash "$0" "$@"
fi
"$PY" "$HERE/fixture_scope.py" prepare-results "$WF_RESULTS_DIR" || exit 1
export PYTHONPYCACHEPREFIX="${WF_PYCACHE:-$WF_RESULTS_DIR/pycache}"
mkdir -p "$PYTHONPYCACHEPREFIX"
# 结果缓存轮转：只回收本 scope（run-*）的带 marker 目录，保留最近 20；root 可经
# WF_RESULTS_CACHE 注入（r67 假环境/契约测试指向临时根，不触碰真实用户缓存）。
# bootstrap 不在此接入——那是无自动调用点的一次性存量清理（任务 design D5.3）。
RESULTS_CACHE="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}"
WF_RESULTS_CACHE="$RESULTS_CACHE" "$PY" "$HERE/fixture_scope.py" prune-results "$RESULTS_CACHE" \
  --scope run --exclude "$WF_RESULTS_DIR" || true

# ---- 计划（唯一权威）--------------------------------------------------------
plan_out=$("$PY" "$HERE/plan.py" --format sh -- "$@")
plan_rc=$?
if [ "$plan_rc" -ne 0 ]; then
  exit "$plan_rc"
fi
if ! eval "$plan_out"; then
  echo "PLAN-EVAL-FAILED" >&2
  exit 2
fi
if [ "${PLAN_LIST_ONLY:-0}" = "1" ]; then
  exit 0
fi
if [ "${WF_NO_RUN:-0}" = "1" ]; then
  exit 0
fi

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
FIX="$PLAN_FIX"
RESULTS_DIR="$PLAN_RESULTS_DIR"
export WF_RESULTS_DIR="$RESULTS_DIR" WF_FIX="$FIX"
export WF_ISOLATED_UNITS="${PLAN_ISOLATED_UNITS:-}"
LEGACY_FIXTURE_ROOT="$FIX.legacy"
WF_LEGACY_FIXTURE_ROOT="$LEGACY_FIXTURE_ROOT"
export WF_LEGACY_FIXTURE_ROOT
"$PY" "$HERE/fixture_scope.py" validate "$FIX" --forbid "$RESULTS_DIR" \
  --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
mkdir -p "$RESULTS_DIR"
"$PY" "$HERE/fixture_scope.py" reset "$LEGACY_FIXTURE_ROOT" --forbid "$RESULTS_DIR" \
  --forbid "$PLAN_TEST_RELEASE_ROOT" --forbid "$PLAN_RELEASE_ROOT" || exit 1
WF_TEMPLATE=""
WF_TEMPLATE_READY=0
# run 内模板（结果目录里）由本 run 拥有、结束即删；跨 run 缓存条目绝不在此删除。
RUN_TEMPLATE=""
cleanup_fixtures() {
  for fixture_path in "$FIX" "$LEGACY_FIXTURE_ROOT" ${RUN_TEMPLATE:+"$RUN_TEMPLATE"}; do
    [ -n "$fixture_path" ] || continue
    "$PY" "$HERE/fixture_scope.py" remove "$fixture_path" >/dev/null 2>&1 || true
  done
}
trap cleanup_fixtures EXIT
trap 'trap "" INT TERM; "$PY" "$HERE/execution.py" --cancel-parent-children; exit 143' TERM
trap 'trap "" INT TERM; "$PY" "$HERE/execution.py" --cancel-parent-children; exit 130' INT
"$PY" "$HERE/plan.py" --format json -- "$@" > "$RESULTS_DIR/plan.json" 2>"$RESULTS_DIR/plan.err" || {
  cat "$RESULTS_DIR/plan.err" >&2
  exit 2
}

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

build_started=$(now_ms)
BUILD_OK=1
if [ "$PLAN_FIXTURE_DEPLOY" = "dev" ]; then
  if [ "$PLAN_NO_BUILD" = "1" ]; then
    if ! "$PY" "$REPO_ROOT/scripts/tests/wf_test_release.py" --check \
        --root "$PLAN_TEST_RELEASE_ROOT" --version "$PLAN_TEST_RELEASE_VERSION"; then
      echo "TEST-RELEASE-STALE: 测试发行副本缺失或过期（重建或去掉 --no-build）"
      BUILD_OK=0
    fi
  else
    if ! "$PY" "$REPO_ROOT/scripts/tests/wf_test_release.py" --ensure \
        --root "$PLAN_TEST_RELEASE_ROOT" --version "$PLAN_TEST_RELEASE_VERSION"; then
      echo "TEST-RELEASE-BUILD-FAILED"
      BUILD_OK=0
    fi
  fi
  RELEASE_REPO="$PLAN_TEST_RELEASE_ROOT"
  RELEASE_REF="$PLAN_TEST_RELEASE_REF"
  RELEASE_VERSION="$PLAN_TEST_RELEASE_VERSION"
else
  # candidate 模式只校验候选仓库，不构建测试发行副本
  if ! "$PY" "$HERE/prepare_candidate_repo.py" --check --out "$PLAN_RELEASE_ROOT" \
      --version "$PLAN_RELEASE_VERSION"; then
    echo "CANDIDATE-REPO-INVALID"
    BUILD_OK=0
  fi
  RELEASE_REPO="$PLAN_RELEASE_ROOT"
  RELEASE_REF="$PLAN_RELEASE_REF"
  RELEASE_VERSION="$PLAN_RELEASE_VERSION"
fi
build_seconds=$(( ($(now_ms) - build_started) / 1000 ))

export WF_FIXTURE_DEPLOY="$PLAN_FIXTURE_DEPLOY"
export WF_RELEASE_REPO="$RELEASE_REPO"
if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
  # dev 模式不导出候选身份：否则任何读环境的下游都会以为自己在候选模式
  export WF_RELEASE_ROOT="$RELEASE_REPO"
  export WF_RELEASE_REF="$RELEASE_REF"
  export WF_RELEASE_VERSION="$RELEASE_VERSION"
  export WF_RELEASE_META="$PLAN_RELEASE_META"
fi
if [ "$PLAN_FIXTURE_DEPLOY" = "dev" ]; then
  # 断言侧只读发行副本的 lib，不读源码 payload/lib
  export WF_TEST_LIB="$PLAN_TEST_RELEASE_ROOT/wf-release/lib"
  # f1_candidate_smoke 之外的 dev 路径不需要候选身份
  export WF_RELEASE_TREE="$RELEASE_REPO"
else
  export WF_TEST_LIB="$PLAN_RELEASE_ROOT/wf-release/lib"
  export WF_RELEASE_TREE="$RELEASE_REPO"
fi
SHARED_RELEASE="$RELEASE_REPO"

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
template_check() {   # template_check <root> [extra args...]
  local root=$1; shift
  local args=(--version "$PLAN_RELEASE_VERSION" --ref "$PLAN_RELEASE_REF")
  if [ "$PLAN_FIXTURE_DEPLOY" != "candidate" ]; then args=(); fi
  "$PY" "$HERE/template_check.py" "$root" "${args[@]}" --quiet "$@"
}

template_repoint() {  # template_repoint <root> <from> [extra args...]
  local root=$1 from=$2; shift 2
  local args=(--version "$PLAN_RELEASE_VERSION" --ref "$PLAN_RELEASE_REF")
  if [ "$PLAN_FIXTURE_DEPLOY" != "candidate" ]; then args=(); fi
  "$PY" "$HERE/template_check.py" "$root" --repoint-from "$from" "${args[@]}" --quiet "$@"
}

# key = <payload_digest12>-<py_maj.min>-<deploy>[-<version>-<ref>]
# digest 是内容摘要（相对路径序 + 逐文件 sha256，跳过 .git/__pycache__/*.pyc，不看 mtime）：
# 改内容才失效，只 touch 不失效。非 [A-Za-z0-9._-] 字符统一折叠为 '-'（ref 含 '/'）。
compute_template_key() {
  local version="$PLAN_TEST_RELEASE_VERSION" ref="$PLAN_TEST_RELEASE_REF"
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    version="$PLAN_RELEASE_VERSION"; ref="$PLAN_RELEASE_REF"
  fi
  "$PY" - "$REPO_ROOT" "$PLAN_FIXTURE_DEPLOY" "$version" "$ref" <<'PY'
import os, re, sys
repo, deploy, version, ref = sys.argv[1:5]
sys.path.insert(0, os.path.join(repo, "scripts"))
import wf_release_common as common

digest = common.tree_digest(os.path.join(repo, "docs/workflows/wf/payload")).split(":", 1)[-1][:12]
pyver = "%d.%d" % sys.version_info[:2]

def sanitize(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "x"

parts = [digest, pyver, deploy]
if deploy == "candidate" and version and ref:
    parts += [version, ref]
print("-".join(sanitize(part) for part in parts))
PY
}

build_template_tree() {  # build_template_tree <root> <out-file>
  local root=$1 out=$2
  "$PY" "$HERE/fixture_scope.py" reset "$root" || return 1
  fixture_args
  if ! run_command template-fixture "$RESULTS_DIR/template-fixture.log" raw \
      bash "$HERE/wf_fixture.sh" "$root" "${FIXTURE_ARGS[@]}" >"$out" 2>&1; then
    return 1
  fi
  if ! WF_FIX="$root" run_command template-init "$RESULTS_DIR/template-init.log" raw \
      "$PY" "$HERE/f1_init.py" >>"$out" 2>&1; then
    return 1
  fi
  return 0
}

cleanup_template_cache_stale() {  # 陈旧条目/半成品：flock 保证无并发运行器，直接按所有权回收
  local root=$1 path
  for path in "$root"/*.stale-* "$root"/*.build; do
    [ -e "$path" ] || continue
    "$PY" "$HERE/fixture_scope.py" remove "$path" >/dev/null 2>&1 \
      || echo "（无法回收陈旧模板缓存条目：$path）"
  done
}

cache_entry_root() {  # 有效条目打印 meta.root；无效返回非零（诊断走 stderr）
  local entry=$1 meta="$1.meta.json" root
  if [ ! -f "$meta" ]; then
    echo "TEMPLATE-CACHE-INVALID: 缺少 meta（没有 meta 的条目一律无效）" >&2
    return 1
  fi
  root=$("$PY" - "$entry" "$meta" <<'PY'
import json, os, sys
entry, meta = os.path.abspath(sys.argv[1]), sys.argv[2]
try:
    record = json.load(open(meta, encoding="utf-8"))
except (OSError, ValueError):
    raise SystemExit(1)
root = record.get("root")
if not isinstance(root, str) or not root or root != os.path.realpath(entry):
    raise SystemExit(1)
print(root)
PY
  ) || {
    echo "TEMPLATE-CACHE-MOVED: meta.root 与条目 realpath 不一致（缓存根被移动/条目被拷贝）" >&2
    return 1
  }
  template_check "$entry" >&2 || {
    echo "TEMPLATE-CACHE-INVALID: 空态/安装身份校验失败" >&2; return 1; }
  "$PY" "$HERE/source_hygiene.py" check --strict "$entry" >&2 || {
    echo "TEMPLATE-CACHE-INVALID: 条目内含字节码产物（strict 判脏）" >&2; return 1; }
  printf '%s\n' "$root"
  return 0
}

publish_template_cache() {  # 发布序列：build → 校验 → 挪旧 → 改名 → repoint → 最后写 meta
  local entry=$1 build="$1.build"
  if [ -e "$build" ]; then
    "$PY" "$HERE/fixture_scope.py" remove "$build" >/dev/null 2>&1 || return 1
  fi
  if ! build_template_tree "$build" "$RESULTS_DIR/template.out"; then
    echo "TEMPLATE-BUILD-FAILED（见 $RESULTS_DIR/template.out）" >&2
    tail -5 "$RESULTS_DIR/template.out" >&2 || true
    return 1
  fi
  if ! template_check "$build"; then
    echo "TEMPLATE-BUILD-INVALID（见 $RESULTS_DIR/template.out）" >&2
    return 1
  fi
  if [ -e "$entry" ]; then
    "$PY" "$HERE/fixture_scope.py" move "$entry" "$entry.stale-$$" || return 1
  fi
  "$PY" "$HERE/fixture_scope.py" move "$build" "$entry" || return 1
  if ! template_repoint "$entry" "$build" --expect-repoint-min 1; then
    echo "TEMPLATE-REPOINT-MISMATCH: 发布时改写数 < 1（记录未指向构建路径）" >&2
    return 1
  fi
  "$PY" - "$entry" "$TEMPLATE_CACHE_KEY" <<'PY'
import datetime, json, os, sys
entry, key = sys.argv[1], sys.argv[2]
meta = entry + ".meta.json"
record = {
    "key": key,
    "digest": key.split("-", 1)[0],
    "pyver": "%d.%d" % sys.version_info[:2],
    "deploy": os.environ.get("PLAN_FIXTURE_DEPLOY", ""),
    "version": os.environ.get("PLAN_RELEASE_VERSION", ""),
    "ref": os.environ.get("PLAN_RELEASE_REF", ""),
    "root": os.path.realpath(entry),
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
}
temporary = meta + ".tmp"
with open(temporary, "w", encoding="utf-8") as handle:
    json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
os.replace(temporary, meta)
PY
  return 0
}

TEMPLATE_SECONDS=0
WF_TEMPLATE_READY=0
WF_TEMPLATE=""
WF_TEMPLATE_SOURCE=""
TEMPLATE_SOURCE=run-build
TEMPLATE_CACHE_HIT=0
TEMPLATE_CACHE_KEY=""
TEMPLATE_CACHE_ROOT="${WF_RESULTS_CACHE:-$HOME/.cache/wf-test-run}/template"
if [ "$PLAN_NO_TEMPLATE" = "1" ]; then
  TEMPLATE_SOURCE=none
  echo "（模板机制关闭（--no-template/WF_NO_TEMPLATE=1）：逐单元重建夹具）"
else
  template_started=$(now_ms)
  if [ "$PLAN_NO_TEMPLATE_CACHE" = "1" ]; then
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
    TEMPLATE_CACHE_KEY=$(compute_template_key) || {
      echo "TEMPLATE-CACHE-KEY-FAILED"; exit 1; }
    TEMPLATE_ENTRY="$TEMPLATE_CACHE_ROOT/$TEMPLATE_CACHE_KEY"
    if entry_root=$(cache_entry_root "$TEMPLATE_ENTRY"); then
      WF_TEMPLATE="$TEMPLATE_ENTRY"
      WF_TEMPLATE_SOURCE="$entry_root"
      WF_TEMPLATE_READY=1
      TEMPLATE_SOURCE=cache
      TEMPLATE_CACHE_HIT=1
      echo "（模板缓存命中：$TEMPLATE_ENTRY）"
    else
      if [ -e "$TEMPLATE_ENTRY" ]; then
        "$PY" "$HERE/fixture_scope.py" move "$TEMPLATE_ENTRY" "$TEMPLATE_ENTRY.stale-$$" \
          || { echo "TEMPLATE-CACHE-STALE-FAILED"; exit 1; }
      fi
      if ! publish_template_cache "$TEMPLATE_ENTRY"; then
        echo "TEMPLATE-CACHE-PUBLISH-FAILED: $TEMPLATE_ENTRY"
        exit 1
      fi
      WF_TEMPLATE="$TEMPLATE_ENTRY"
      WF_TEMPLATE_SOURCE="$TEMPLATE_ENTRY"
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

# 准备一个套件的夹具：模板可用时只做 cp -a + 空态校验，否则重建夹具并初始化。
# 返回码：0 成功；1 夹具失败；2 初始化失败；3 复制失败；4 复制后校验失败
prepare_fixture() {
  local log=$1
  if [ "$WF_TEMPLATE_READY" = "1" ]; then
    if ! "$PY" "$HERE/fixture_scope.py" clone "$WF_TEMPLATE" "$FIX" >>"$log" 2>&1; then
      return 3
    fi
    if ! template_repoint "$FIX" "${WF_TEMPLATE_SOURCE:-$WF_TEMPLATE}" --expect-repoint-min 1 >>"$log" 2>&1; then
      return 4
    fi
    return 0
  fi
  fixture_args
  "$PY" "$HERE/fixture_scope.py" reset "$FIX" >>"$log" 2>&1 || return 1
  if ! run_command fixture "$log.fixture.log" raw bash "$HERE/wf_fixture.sh" "$FIX" "${FIXTURE_ARGS[@]}" >>"$log" 2>&1; then
    return 1
  fi
  if ! WF_FIX="$FIX" run_command init "$log.init.log" raw "$PY" "$HERE/f1_init.py" >>"$log" 2>&1; then
    return 2
  fi
  return 0
}

fixture_failure_label() {
  case "$1" in
    1) echo FIXTURE-FAILED ;;
    2) echo INIT-FAILED ;;
    3) echo TEMPLATE-COPY-FAILED ;;
    4) echo TEMPLATE-COPY-INVALID ;;
    *) echo FIXTURE-FAILED ;;
  esac
}

JOBS=$PLAN_JOBS
EXECUTION_MODE=serial
FALLBACK_REASON=""
RESULTS_MARK="$RESULTS_DIR/lines"

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

run_suites_parallel() {
  # 并行汇总不能只统计「已写出的结果行」——子进程异常、结果不可写都会让结果行缺失，
  # 而旧的计数方式仍会把计划里的套件当成已运行并给出绿灯。
  local -a records=("$@")
  local rec
  mkdir -p "$RESULTS_DIR"
  : > "$RESULTS_MARK"
  export FIX HERE PY SHARED_RELEASE RESULTS_DIR SOURCE_HOME
  local xargs_rc=0
  if [ "$#" -gt 0 ]; then
    printf '%s\n' "${records[@]}" | xargs -P "$JOBS" -I{} unshare -Urm bash "$HERE/run_one.sh" {} || xargs_rc=$?
  fi
  # Missing worker results are infrastructure failures, not permission to rerun
  # a partly executed test against different state. Preserve logs and fail closed.
  sort -t$'\t' -k1 "$RESULTS_MARK" | awk -F'\t' '{printf "%-18s rc=%s %ss %s | %s\n", $1, $2, $3, $4, $5}'
  for rec in "${records[@]}"; do add_init_millis "${rec%%:*}"; done
  # 完整性判定只有一处实现（results_gate.py）：缺行/重行/畸形/计划外/坏结果都必须计失败，
  # 不能只统计「已写出的结果行」。--expected 只取记录第一段（名字），不传执行记录。
  local -a names=()
  for rec in "${records[@]}"; do names+=("${rec%%:*}"); done
  local gate_out
  gate_out=$("$PY" "$HERE/results_gate.py" --lines "$RESULTS_MARK" --expected "${names[*]}")
  eval "$gate_out"
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
  local xargs_fail=0
  if [ "$xargs_rc" -ne 0 ]; then
    echo "XARGS-EXIT: $xargs_rc"; xargs_fail=1
  fi
  fail=$((fail + GATE_MALFORMED + $(printf '%s' "$GATE_MISSING" | wc -w)
           + $(printf '%s' "$GATE_DUPLICATE" | wc -w) + $(printf '%s' "$GATE_UNEXPECTED" | wc -w)
           + $(printf '%s' "$GATE_BAD" | wc -w) + xargs_fail))
  suite_ran=$((suite_ran + GATE_UNIQUE))
}

run_repro() {
  # 只有一条实现：repro/run.sh（也可单独/CI 运行）。这里只消费它的机器可读汇总。
  local args=(--mode "$PLAN_REPRO_MODE" --jobs "$PLAN_REPRO_JOBS"
              --fixture-deploy "$PLAN_FIXTURE_DEPLOY" --results-dir "$RESULTS_DIR/repro")
  local g
  for g in $PLAN_REPRO_GROUPS; do args+=(--group "$g"); done
  if [ "$PLAN_FIXTURE_DEPLOY" = "candidate" ]; then
    args+=(--release-root "$PLAN_RELEASE_ROOT" --release-ref "$PLAN_RELEASE_REF"
           --release-version "$PLAN_RELEASE_VERSION")
  fi
  if [ "$PLAN_NO_BUILD" = "1" ]; then args+=(--no-build); fi
  local out rc
  out=$(bash "$HERE/repro/run.sh" "${args[@]}" 2>&1); rc=$?
  printf '%s\n' "$out" | grep -E '^(ok|FAIL|repro|SKIP)' || true
  local total passed failed gsec rsec skipped
  total=$(printf '%s\n' "$out" | sed -n 's/^REPRO_TOTAL=//p')
  passed=$(printf '%s\n' "$out" | sed -n 's/^REPRO_PASSED=//p')
  failed=$(printf '%s\n' "$out" | sed -n 's/^REPRO_FAILED=//p')
  gsec=$(printf '%s\n' "$out" | sed -n 's/^REPRO_GREEN_SECONDS=//p')
  rsec=$(printf '%s\n' "$out" | sed -n 's/^REPRO_RED_SECONDS=//p')
  skipped=$(printf '%s\n' "$out" | sed -n 's/^REPRO_SKIPPED_COUNT=//p')
  if ! [[ "${total:-}" =~ ^[0-9]+$ ]] || ! [[ "${passed:-}" =~ ^[0-9]+$ ]] || ! [[ "${failed:-}" =~ ^[0-9]+$ ]]; then
    echo "repro 汇总缺失（子进程退出 $rc）"
    fail=$((fail + 1))
    return
  fi
  if [ "${skipped:-0}" != "0" ]; then
    echo "SKIPPED-NON-CANDIDATE: $skipped 个用例（candidate 模式不计通过）"
  fi
  repro_ran=$((repro_ran + total))
  fail=$((fail + failed))
  case "${gsec:-}" in ''|*[!0-9]*) gsec=0 ;; esac
  case "${rsec:-}" in ''|*[!0-9]*) rsec=0 ;; esac
  green_seconds=$((green_seconds + gsec))
  red_seconds=$((red_seconds + rsec))
  if [ "$rc" -ne 0 ] && [ "${failed:-0}" -eq 0 ]; then
    echo "repro 退出码 $rc 与汇总不一致"
    fail=$((fail + 1))
  fi
}

# 记录解析：`name:kind:expect:fixture:script` 五段固定顺序（plan.py 是唯一产出点）。
record_name() { printf '%s' "${1%%:*}"; }
record_field() {
  local record=$1 index=$2
  printf '%s' "$record" | cut -d: -f"$index"
}
record_script() { printf '%s' "${1##*:}"; }

run_suite() {
  local record=$1
  local suite expect script
  suite=$(record_name "$record"); expect=$(record_field "$record" 3); script=$(record_script "$record")
  mkdir -p "$RESULTS_DIR"
  local log="$RESULTS_DIR/$suite.out"
  local init_started=$(now_ms)
  : > "$log"
  local prep_rc=0
  prepare_fixture "$log" || prep_rc=$?
  if [ "$prep_rc" -ne 0 ]; then
    printf '%-18s %s\n' "$suite" "$(fixture_failure_label "$prep_rc")"
    fail=$((fail+1)); return
  fi
  if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
    printf '%-18s FIXTURE-INCOMPLETE\n' "$suite"; fail=$((fail+1)); return
  fi
  local init_millis_local=$(( $(now_ms) - init_started ))
  init_millis=$((init_millis + init_millis_local))
  local out rc line started elapsed elapsed_ms
  started=$(now_ms)
  out=$(WF_FIX="$FIX" run_command "$suite" "$RESULTS_DIR/$suite.test.log" suite \
        --expected "$expect" "$PY" "$HERE/$script" 2>&1); rc=$?
  printf '%s\n' "$out" >> "$log"
  elapsed_ms=$(( $(now_ms) - started )); elapsed=$((elapsed_ms / 1000))
  suite_millis=$((suite_millis + elapsed_ms))
  printf 'init_millis=%s\nsuite_millis=%s\n' "$init_millis_local" "$((elapsed_ms))" > "$RESULTS_DIR/$suite.timing"
  line=$(printf '%s\n' "$out" | tail -1)
  printf '%-18s rc=%s %ss %s\n' "$suite" "$rc" "$elapsed" "$line"
  suite_ran=$((suite_ran+1))
  # 判定：退出码、汇总行里的失败数、FAIL 行都由 execution.py 统一解释（含 expect 预算）
  local status=ok
  if [ "$rc" -ne 0 ]; then fail=$((fail+1)); status=bad; fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "$rc" "$elapsed" "$status" "$line" >> "$RESULTS_MARK"
}

# ---- 已知技术债清单（必过门的唯一豁免来源）---------------------------------
# 这些套件当前是红的、且原因已登记；它们**不阻塞**必过门，但会被单独列出。
# 一旦它们转绿，本脚本会失败并提示从清单里移除 —— 清单不允许腐烂。
# 2026-11-10：cp3/r67/r68/r69/r70/r71 已全部修绿，清单清空——现在**没有豁免**。
# 以后要加条目，必须同时在 task 记录里写明"为什么现在修不了、谁来修"，否则不许进清单。
KNOWN_LEGACY="${WF_KNOWN_LEGACY-}"

: > "$RESULTS_MARK"

# 单元派发（Step 2 过渡态）：kind 决定既有三段执行形状；调度合并在 Step 4。
# 记录只由 plan.py 产出，bash 不重算 kind/expect/script。
SUITE_PARALLEL_RECORDS=()
SUITE_SERIAL_RECORDS=()
FLOW_RECORDS=()
EXTRA_RECORDS=()
UNIT_NAMES=()
for rec in $PLAN_UNITS; do
  UNIT_NAMES+=("$(record_name "$rec")")
  kind=$(record_field "$rec" 2)
  case "$kind" in
    suite|candidate)
      case " $PLAN_UNITS_SERIAL " in
        *" $rec "*) SUITE_SERIAL_RECORDS+=("$rec") ;;
        *) SUITE_PARALLEL_RECORDS+=("$rec") ;;
      esac
      ;;
    flow) FLOW_RECORDS+=("$rec") ;;
    extra) EXTRA_RECORDS+=("$rec") ;;
    *) echo "PLAN-RECORD-INVALID: 未知 kind ${kind}（$rec）"; fail=$((fail+1)) ;;
  esac
done

# 仓库副本位于 /tmp 时，unshare 里挂的 tmpfs 会把 /tmp 遮住，子进程看不到套件与结果文件。
if [ "$JOBS" -gt 1 ]; then
  case "$HERE" in
    /tmp/*) echo "（套件目录在 /tmp 下：unshare 会遮住输入路径，改用串行）"; JOBS=1; FALLBACK_REASON="repository-under-tmp" ;;
  esac
fi
if [ "${#SUITE_PARALLEL_RECORDS[@]}" -gt 0 ] || [ "${#SUITE_SERIAL_RECORDS[@]}" -gt 0 ]; then
  if [ "$JOBS" -gt 1 ] && [ "${#SUITE_PARALLEL_RECORDS[@]}" -gt 0 ] && can_unshare; then
    echo "（并行：$JOBS worker（unshare 隔离）；串行段 ${#SUITE_SERIAL_RECORDS[@]} 个套件）"
    EXECUTION_MODE=unshare
    run_suites_parallel ${SUITE_PARALLEL_RECORDS[@]+"${SUITE_PARALLEL_RECORDS[@]}"}
    for rec in ${SUITE_SERIAL_RECORDS[@]+"${SUITE_SERIAL_RECORDS[@]}"}; do run_suite "$rec"; done
  else
    if [ "$JOBS" -gt 1 ] && [ -z "$FALLBACK_REASON" ]; then
      if ! can_unshare; then FALLBACK_REASON="unshare-unavailable"
      elif [ "${#SUITE_PARALLEL_RECORDS[@]}" -eq 0 ]; then FALLBACK_REASON="all-suites-require-serial"
      else FALLBACK_REASON="parallel-worker-capability-unavailable"
      fi
      echo "（$FALLBACK_REASON：退回串行）"
    else
      echo "（串行：逐套件执行）"
    fi
    JOBS=1
    # 串行模式共享 /tmp：某些套件会伪造 release-repo 软链，逐套件重建以隔离这种干扰
    for rec in ${SUITE_PARALLEL_RECORDS[@]+"${SUITE_PARALLEL_RECORDS[@]}"} ${SUITE_SERIAL_RECORDS[@]+"${SUITE_SERIAL_RECORDS[@]}"}; do
      WF_RELEASE_REPO="$RELEASE_REPO" run_suite "$rec"
    done
  fi
fi
if [ "$BUILD_OK" = 0 ]; then
  fail=$((fail + 1))
fi

# ---- 流程 / extra（同一份 PLAN_UNITS 记录驱动；Step 4 并入统一 worker）------
run_flow() {
  local record=$1
  local name expect script
  name=$(record_name "$record"); expect=$(record_field "$record" 3); script=$(record_script "$record")
  mkdir -p "$RESULTS_DIR"
  local log="$RESULTS_DIR/$name.out"
  local init_started=$(now_ms)
  : > "$log"
  local prep_rc=0
  prepare_fixture "$log" || prep_rc=$?
  if [ "$prep_rc" -ne 0 ]; then
    printf '%-18s %s\n' "$name" "$(fixture_failure_label "$prep_rc")"
    fail=$((fail+1)); flow_ran=$((flow_ran+1)); return
  fi
  init_millis=$((init_millis + ($(now_ms) - init_started)))
  local out rc got started elapsed elapsed_ms
  started=$(now_ms)
  out=$(WF_FIX="$FIX" run_command "$name" "$RESULTS_DIR/$name.test.log" flow \
        --expected "$expect" "$PY" "$HERE/$script" 2>&1); rc=$?
  elapsed_ms=$(( $(now_ms) - started )); elapsed=$((elapsed_ms / 1000))
  suite_millis=$((suite_millis + elapsed_ms))
  printf '%s\n' "$out" >> "$log"
  # PASS 计数唯一来源：execution.py 结果 JSON（verdict 的 observed 字段）——
  # shell 不再本地复制行文法判定；解析失败计基础设施失败（不静默）。
  got=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["assertion_result"]["observed"])' "$RESULTS_DIR/$name.test.log.json") || {
    printf '%-18s RESULT-JSON-INVALID\n' "$name"; fail=$((fail+1)); flow_ran=$((flow_ran+1)); return; }
  printf '%-18s rc=%s PASS=%s\n' "$name" "$rc" "$got"
  flow_ran=$((flow_ran+1))
  if [ "$rc" -ne 0 ] || [ "$got" -ne "$expect" ]; then fail=$((fail+1)); fi
}

# F0：从发行安装器装到一个空目录，再跑自举闭环（candidate 模式下用候选安装器）
run_f0() {
  local record=$1
  local name expect script
  name=$(record_name "$record"); expect=$(record_field "$record" 3); script=$(record_script "$record")
  local target="$LEGACY_FIXTURE_ROOT/$name"
  "$PY" "$HERE/fixture_scope.py" reset "$target" --forbid "$RESULTS_DIR" \
    --forbid "$RELEASE_REPO" || { fail=$((fail+1)); return; }
  if ! run_command "$name-install" "$RESULTS_DIR/$name-install.log" raw "$PY" "$RELEASE_REPO/install.py" --target "$target" --release-ref "$RELEASE_REF" \
      --source "$RELEASE_REPO" --platform dsh \
      --confirm >"$RESULTS_DIR/$name-install.out" 2>&1; then
    printf '%-18s INSTALL-FAILED\n' "$name"; fail=$((fail+1)); flow_ran=$((flow_ran+1)); return
  fi
  local out got passed
  out=$(WF_FIX="$target" run_command "$name" "$RESULTS_DIR/$name.test.log" flow --expected "$expect" "$PY" "$HERE/$script" 2>&1); got=$?
  passed=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["assertion_result"]["observed"])' "$RESULTS_DIR/$name.test.log.json") || passed=RESULT-JSON-INVALID
  printf '%-18s rc=%s PASS=%s\n' "$name" "$got" "$passed"
  flow_ran=$((flow_ran+1))
  if [ "$got" -ne 0 ] || [ "$passed" != "$expect" ]; then fail=$((fail+1)); fi
}

run_extra() {
  # 直接调用的专项脚本体：计入 flow_ran，判据为退出码与 PASS 计数（唯一来源：
  # execution.py 结果 JSON；解析失败计基础设施失败，不静默）
  local record=$1
  local name expect script
  name=$(record_name "$record"); expect=$(record_field "$record" 3); script=$(record_script "$record")
  local out rc got log="$RESULTS_DIR/$name.out"
  out=$(WF_FIX="$FIX" run_command "$name" "$RESULTS_DIR/$name.test.log" flow --expected "$expect" "$PY" "$HERE/$script" 2>&1); rc=$?
  printf '%s\n' "$out" >> "$log"
  got=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["assertion_result"]["observed"])' "$RESULTS_DIR/$name.test.log.json") || {
    printf '%-18s RESULT-JSON-INVALID\n' "$name"; fail=$((fail+1)); flow_ran=$((flow_ran+1)); return; }
  printf '%-18s rc=%s PASS=%s\n' "$name" "$rc" "$got"
  flow_ran=$((flow_ran+1))
  if [ "$rc" -ne 0 ] || [ "$got" -ne "$expect" ]; then fail=$((fail+1)); fi
}

for rec in ${FLOW_RECORDS[@]+"${FLOW_RECORDS[@]}"}; do
  case "$(record_name "$rec")" in
    f0) run_f0 "$rec" ;;
    *) run_flow "$rec" ;;
  esac
done
for rec in ${EXTRA_RECORDS[@]+"${EXTRA_RECORDS[@]}"}; do
  run_extra "$rec"
done

if [ "$PLAN_REPRO_ENABLED" = "1" ]; then
  run_repro
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

SUMMARY_JSON="$RESULTS_DIR/summary.json"
WF_SUMMARY_JSON="$SUMMARY_JSON" \
WF_SUMMARY_MODE="$PLAN_MODE" WF_SUMMARY_FULL_MODE="$PLAN_FULL_MODE" \
WF_SUMMARY_DEPLOY="$PLAN_FIXTURE_DEPLOY" \
WF_SUMMARY_SUITE_RAN="$suite_ran" WF_SUMMARY_FLOW_RAN="$flow_ran" WF_SUMMARY_UNITS="$units_total" \
WF_SUMMARY_REPRO_RAN="$repro_ran" WF_SUMMARY_FAIL="$unknown_fail" \
WF_SUMMARY_DEBT="$debt" WF_SUMMARY_BUILD="$build_seconds" WF_SUMMARY_TEMPLATE="$TEMPLATE_SECONDS" \
WF_SUMMARY_INIT_MS="$init_millis" WF_SUMMARY_SUITE_MS="$suite_millis" \
WF_SUMMARY_GREEN="$green_seconds" WF_SUMMARY_RED="$red_seconds" \
WF_SUMMARY_TOTAL="$total_seconds" WF_SUMMARY_TOTAL_MS="$total_millis" WF_SUMMARY_EFFECTIVE_JOBS="$JOBS" WF_SUMMARY_EXECUTION_MODE="$EXECUTION_MODE" WF_SUMMARY_FALLBACK="$FALLBACK_REASON" WF_SUMMARY_REPRO_MODE="$PLAN_REPRO_MODE" \
WF_SUMMARY_REPRO_GROUPS="$PLAN_REPRO_GROUPS" \
WF_SUMMARY_PYCACHE_ROOT="$PYTHONPYCACHEPREFIX" \
WF_SUMMARY_TEMPLATE_SOURCE="$TEMPLATE_SOURCE" \
WF_SUMMARY_TEMPLATE_CACHE_HIT="$TEMPLATE_CACHE_HIT" \
WF_SUMMARY_TEMPLATE_CACHE_KEY="$TEMPLATE_CACHE_KEY" \
WF_SUMMARY_JOBS="$PLAN_JOBS" WF_SUMMARY_REPRO_JOBS="$PLAN_REPRO_JOBS" \
"$PY" - <<'PY'
import json, os
groups = (os.environ.get("WF_SUMMARY_REPRO_GROUPS") or "").split()
payload = {
    "schema_version": 1,
    "mode": os.environ.get("WF_SUMMARY_MODE"),
    "full_mode": int(os.environ.get("WF_SUMMARY_FULL_MODE") or 0),
    "fixture_deploy": os.environ.get("WF_SUMMARY_DEPLOY"),
    "suite_ran": int(os.environ.get("WF_SUMMARY_SUITE_RAN") or 0),
    "flow_ran": int(os.environ.get("WF_SUMMARY_FLOW_RAN") or 0),
    "repro_ran": int(os.environ.get("WF_SUMMARY_REPRO_RAN") or 0),
    "units_total": int(os.environ.get("WF_SUMMARY_UNITS") or 0),
    "repro_mode": os.environ.get("WF_SUMMARY_REPRO_MODE"),
    "repro_groups": groups,
    "jobs": int(os.environ.get("WF_SUMMARY_EFFECTIVE_JOBS") or 0),
    "requested_jobs": int(os.environ.get("WF_SUMMARY_JOBS") or 0),
    "effective_jobs": int(os.environ.get("WF_SUMMARY_EFFECTIVE_JOBS") or 0),
    "execution_mode": os.environ.get("WF_SUMMARY_EXECUTION_MODE"),
    "fallback_reason": os.environ.get("WF_SUMMARY_FALLBACK"),
    "repro_jobs": int(os.environ.get("WF_SUMMARY_REPRO_JOBS") or 0),
    # init/suite 是各套件累计（并行下总和可大于 total_seconds），totals 才是墙钟
    "timing_note": "init_seconds/suite_seconds 为跨套件累计；total_seconds 为墙钟",
    "fail": int(os.environ.get("WF_SUMMARY_FAIL") or 0),
    "legacy_debt": int(os.environ.get("WF_SUMMARY_DEBT") or 0),
    "build_seconds": int(os.environ.get("WF_SUMMARY_BUILD") or 0),
    "template_seconds": int(os.environ.get("WF_SUMMARY_TEMPLATE") or 0),
    "template_reused": bool(os.environ.get("WF_TEMPLATE_READY") == "1"),
    "template_source": os.environ.get("WF_SUMMARY_TEMPLATE_SOURCE"),
    "template_cache_hit": os.environ.get("WF_SUMMARY_TEMPLATE_CACHE_HIT") == "1",
    "template_cache_key": os.environ.get("WF_SUMMARY_TEMPLATE_CACHE_KEY") or None,
    "pycache_root": os.environ.get("WF_SUMMARY_PYCACHE_ROOT"),
    "init_seconds": round(int(os.environ.get("WF_SUMMARY_INIT_MS") or 0) / 1000, 2),
    "suite_seconds": round(int(os.environ.get("WF_SUMMARY_SUITE_MS") or 0) / 1000, 2),
    "green_seconds": int(os.environ.get("WF_SUMMARY_GREEN") or 0),
    "red_seconds": int(os.environ.get("WF_SUMMARY_RED") or 0),
    "total_seconds": round(int(os.environ["WF_SUMMARY_TOTAL_MS"]) / 1000, 3),
}
path = os.environ["WF_SUMMARY_JSON"]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
print("summary: " + path)
PY

echo "---- 运行 $units_total 项（套件 $suite_ran，流程/extra $flow_ran，repro $repro_ran），失败 $fail 项（其中已登记债 $debt 项）----"
echo "---- 计时 build=${build_seconds}s template=${TEMPLATE_SECONDS}s init=$((init_millis/1000))s suite=$((suite_millis/1000))s green=${green_seconds}s red=${red_seconds}s total=${total_seconds}s ----"
if [ "$unknown_fail" -ne 0 ] || [ "$stale" -ne 0 ]; then
  [ "$unknown_fail" -ne 0 ] && echo "GATE-FAIL: 未登记的失败 $unknown_fail 项（必过门未通过）"
  [ "$stale" -ne 0 ] && echo "GATE-BOOKKEEPING: 豁免清单有 $stale 项需要销账（转绿或已不存在）"
  exit 1
fi
echo "GATE-OK: 必过门通过（豁免中的债：$(printf '%s' "$legacy_failed" | wc -w) 项）"
exit 0
