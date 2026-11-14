#!/bin/bash
# 单个执行单元的隔离执行：私有 /tmp（tmpfs）+ 只读挂共享发行仓库。
# 唯一入参是 plan.py 产出的五段记录 `name:kind:expect:fixture:script`；解析后一切路径与键只用 name，
# 脚本文件只从记录的 `script` 取（`f0` → `p5_f0.py`），不再按名字拼 `.py`。
# 部署来源与发行参数通过环境（WF_FIXTURE_DEPLOY / WF_RELEASE_* / WF_INSTALL_REF）传进来。
set -uo pipefail
record=${1:?}
IFS=':' read -r unit kind expect fixture script <<< "$record"
: "${FIX:?}" "${HERE:?}" "${PY:?}" "${SHARED_RELEASE:?}" "${RESULTS_DIR:?}"
# pyc 一律落在结果目录（run_all 已导出；独立调用时兜底），不落源树/夹具。
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-${WF_PYCACHE:-$RESULTS_DIR/pycache}}"
# 执行域：1 = 并行池（私有 /tmp + unshare）；0 = 串行域（宿主 /tmp，无 unshare）。
case "${WF_NAMESPACE:-1}" in 0) namespace=0 ;; *) namespace=1 ;; esac
if [ "$namespace" = "1" ] && [ "${WF_NAMESPACE_READY:-0}" != "1" ]; then
  FIX="${FIX}-${unit}-${BASHPID}"
  export FIX
  export NAMESPACE_ERROR_LOG="$RESULTS_DIR/$unit.namespace.log"
  exec "$PY" "$HERE/namespace.py" bash "$0" "$record"
fi
export WF_FIX="$FIX" WF_LEGACY_FIXTURE_ROOT="$FIX.legacy"
now_ms() { "$PY" -c 'import time; print(int(time.monotonic()*1000))'; }

out="$RESULTS_DIR/$unit.out"
: > "$out"
init_started=$(now_ms)
prep_rc=0

# 结果行唯一写入点：五列 name/rc/elapsed/status/tail（results_gate.py 只认五列）。
write_result() {
  printf '%s\t%s\t%s\t%s\t%s\n' "$unit" "$1" "$2" "$3" "$4" >> "$RESULTS_DIR/lines"
}

# 夹具/安装失败：保留日志、写自己的 timing、五列 bad 行后正常退出（失败由 gate 汇总）。
fail_prep() {
  local elapsed=$(( ($(now_ms) - init_started) / 1000 ))
  printf 'init_millis=%s\nsuite_millis=0\n' "$(( $(now_ms) - init_started ))" > "$RESULTS_DIR/$unit.timing"
  printf '%-18s %s\n' "$unit" "$1" >> "$out"
  write_result 1 "$elapsed" bad "$1"
  exit 0
}

case "$fixture" in
  install)
    # f0：从发行安装器装到空目录，再执行记录里的脚本（candidate 模式用候选安装器）。
    target="$WF_LEGACY_FIXTURE_ROOT/$unit"
    "$PY" "$HERE/fixture_scope.py" reset "$target" --forbid "$RESULTS_DIR" \
      --forbid "$SHARED_RELEASE" >>"$out" 2>&1 || fail_prep INSTALL-FAILED
    if ! "$PY" "$HERE/execution.py" --name "$unit-install" \
        --log "$RESULTS_DIR/$unit-install.log" -- \
        "$PY" "$SHARED_RELEASE/install.py" --target "$target" --release-ref "$WF_INSTALL_REF" \
        --source "$SHARED_RELEASE" --platform dsh --confirm >>"$out" 2>&1; then
      fail_prep INSTALL-FAILED
    fi
    FIX="$target"
    ;;
  template)
    if [ "${WF_TEMPLATE_READY:-0}" = "1" ]; then
      # 夹具模板只读：每单元复制独立一份，再核对空态（重锚定 + 无残留 + 至少改写 1 个）。
      check_args=(--quiet)
      if [ "$WF_FIXTURE_DEPLOY" = "candidate" ]; then
        check_args=(--quiet --version "$WF_RELEASE_VERSION" --ref "$WF_RELEASE_REF")
      fi
      "$PY" "$HERE/fixture_scope.py" clone "$WF_TEMPLATE" "$FIX" >>"$out" 2>&1 || prep_rc=3
      if [ "$prep_rc" -eq 0 ]; then
        check_out=$("$PY" "$HERE/template_check.py" "$FIX" \
          --repoint-from "${WF_TEMPLATE_SOURCE:-$WF_TEMPLATE}" --expect-repoint-min 1 \
          "${check_args[@]}" 2>&1) || {
          printf '%s\n' "$check_out" >>"$out"
          case "$check_out" in
            *"改写数"*) prep_rc=5 ;;
            *) prep_rc=4 ;;
          esac
        }
        printf '%s\n' "$check_out" >>"$out"
      fi
    else
      "$PY" "$HERE/execution.py" --name fixture --log "$out.fixture.log" -- \
        bash "$HERE/wf_fixture.sh" "$FIX" >>"$out" 2>&1 || prep_rc=1
      if [ "$prep_rc" -eq 0 ]; then
        WF_FIX="$FIX" "$PY" "$HERE/execution.py" --name init --log "$out.init.log" -- \
          "$PY" "$HERE/f1_init.py" >>"$out" 2>&1 || prep_rc=2
      fi
    fi
    ;;
  *)
    fail_prep FIXTURE-FAILED
    ;;
esac
if [ "$prep_rc" -ne 0 ]; then
  case "$prep_rc" in
    1) label=FIXTURE-FAILED ;;
    2) label=INIT-FAILED ;;
    3) label=TEMPLATE-COPY-FAILED ;;
    4) label=TEMPLATE-COPY-INVALID ;;
    5) label=TEMPLATE-REPOINT-MISMATCH ;;
    *) label=FIXTURE-FAILED ;;
  esac
  fail_prep "$label"
fi
if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
  fail_prep FIXTURE-INCOMPLETE
fi
init_millis=$(( $(now_ms) - init_started ))

# kind → execution.py 的枚举：executor 只有 raw/suite/flow/steps/repro；映射只存在这一处。
case "$kind" in
  suite|candidate) executor_kind=suite ;;
  flow|extra) executor_kind=flow ;;
  *) fail_prep KIND-INVALID ;;
esac
# isolated-user 成员判定与 run_all 同源（WF_ISOLATED_UNITS ← units.json isolated_user 字段）。
isolated_args() {
  case " ${WF_ISOLATED_UNITS:-} " in *" $unit "*) printf '%s\n' --isolated-user ;; esac
}
user_args=($(isolated_args))
started=$(now_ms)
WF_FIX="$FIX" "$PY" "$HERE/execution.py" --name "$unit" --kind "$executor_kind" \
  --expected "$expect" --log "$RESULTS_DIR/$unit.test.log" \
  --result "$RESULTS_DIR/$unit.test.log.json" ${user_args[@]+"${user_args[@]}"} \
  -- "$PY" "$HERE/$script" >>"$out" 2>&1
rc=$?
# 套件耗时唯一来源：execution.py 结果 JSON 的 seconds（time.monotonic）；缺失计 0，由 gate 兜底。
elapsed_ms=$("$PY" -c 'import json,sys
try: print(int(float(json.load(open(sys.argv[1]))["seconds"]) * 1000))
except (OSError, ValueError, KeyError): print(0)' "$RESULTS_DIR/$unit.test.log.json" 2>/dev/null) || elapsed_ms=$(( $(now_ms) - started ))
elapsed=$((elapsed_ms / 1000))
printf 'init_millis=%s\nsuite_millis=%s\n' "$init_millis" "$elapsed_ms" > "$RESULTS_DIR/$unit.timing"
line=$(tail -1 "$out")
status=ok
[ "$rc" -eq 0 ] || status=bad
write_result "$rc" "$elapsed" "$status" "$line"
