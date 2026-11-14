#!/bin/bash
# 单个套件的隔离执行：私有 /tmp（tmpfs）+ 只读挂共享发行仓库。
# 由 run_all.sh 以 unshare -Urm 调用；套件里写死的 /tmp 路径因此天然互不干扰。
# 部署来源与发行参数通过环境（WF_FIXTURE_DEPLOY / WF_RELEASE_*）传进来。
set -uo pipefail
record=$1
suite=${record%%:*}
expect=$(printf '%s' "$record" | cut -d: -f3)
script=${record##*:}
: "${FIX:?}" "${HERE:?}" "${PY:?}" "${SHARED_RELEASE:?}" "${RESULTS_DIR:?}"
# pyc 一律落在结果目录（run_all 已导出；独立调用时兜底），不落源树/夹具。
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-${WF_PYCACHE:-$RESULTS_DIR/pycache}}"
# Every worker owns a separate fixture path. The old shared path was hidden by
# tmpfs but still raced during setup and cleanup before the namespace was ready.
if [ "${WF_NAMESPACE_READY:-0}" != "1" ]; then
  FIX="${FIX}-${suite}-${BASHPID}"
  export FIX
  export NAMESPACE_ERROR_LOG="$RESULTS_DIR/$suite.namespace.log"
  exec "$PY" "$HERE/namespace.py" bash "$0" "$record"
fi
export WF_FIX="$FIX" WF_LEGACY_FIXTURE_ROOT="$FIX.legacy"
now_ms() { "$PY" -c 'import time; print(int(time.monotonic()*1000))'; }

out="$RESULTS_DIR/$suite.out"
: > "$out"
init_started=$(now_ms)
prep_rc=0
if [ "${WF_TEMPLATE_READY:-0}" = "1" ]; then
  # 夹具模板只读：每套件复制独立一份，再核对空态（绝对路径残留/安装身份）
  "$PY" "$HERE/fixture_scope.py" clone "$WF_TEMPLATE" "$FIX" >>"$out" 2>&1 || prep_rc=3
  if [ "$prep_rc" -eq 0 ]; then
    check_args=(--quiet)
    if [ "$WF_FIXTURE_DEPLOY" = "candidate" ]; then
      check_args=(--quiet --version "$WF_RELEASE_VERSION" --ref "$WF_RELEASE_REF")
    fi
    # 克隆后一次判三件事：重锚定、无残留、至少改写 1 个（0 改写 = 记录与模板源不一致）。
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
  "$PY" "$HERE/execution.py" --name fixture --log "$out.fixture.log" -- bash "$HERE/wf_fixture.sh" "$FIX" >>"$out" 2>&1 || prep_rc=1
  if [ "$prep_rc" -eq 0 ]; then
    WF_FIX="$FIX" "$PY" "$HERE/execution.py" --name init --log "$out.init.log" -- "$PY" "$HERE/f1_init.py" >>"$out" 2>&1 || prep_rc=2
  fi
fi
if [ "$prep_rc" -ne 0 ]; then
  printf 'init_millis=%s\nsuite_millis=0\n' "$(( $(now_ms) - init_started ))" > "$RESULTS_DIR/$suite.timing"
  case "$prep_rc" in
    1) label=FIXTURE-FAILED ;;
    2) label=INIT-FAILED ;;
    3) label=TEMPLATE-COPY-FAILED ;;
    4) label=TEMPLATE-COPY-INVALID ;;
    5) label=TEMPLATE-REPOINT-MISMATCH ;;
    *) label=FIXTURE-FAILED ;;
  esac
  printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "1" "$(( ($(now_ms) - init_started) / 1000 ))" "bad" "$label" >> "$RESULTS_DIR/lines"
  exit 0
fi
if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
  printf 'init_millis=%s\nsuite_millis=0\n' "$(( $(now_ms) - init_started ))" > "$RESULTS_DIR/$suite.timing"
  printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "1" "$(( ($(now_ms) - init_started) / 1000 ))" "bad" "FIXTURE-INCOMPLETE" >> "$RESULTS_DIR/lines"
  exit 0
fi
init_millis=$(( $(now_ms) - init_started ))

# isolated-user 成员判定与 run_all.sh 同源（WF_ISOLATED_UNITS ← units.json isolated_user
# 字段经 plan.py 下发）。修复：并行路径此前缺失 --isolated-user，套件会写真用户配置。
isolated_args() {
  case " ${WF_ISOLATED_UNITS:-} " in *" $1 "*) printf '%s\n' --isolated-user ;; esac
}
user_args=($(isolated_args "$suite"))
started=$(now_ms)
WF_FIX="$FIX" "$PY" "$HERE/execution.py" --name "$suite" --kind suite --expected "$expect" --log "$RESULTS_DIR/$suite.test.log" --result "$RESULTS_DIR/$suite.test.log.json" ${user_args[@]+"${user_args[@]}"} -- "$PY" "$HERE/$script" >>"$out" 2>&1
rc=$?
# 套件耗时的唯一来源：execution.py 结果 JSON 的 seconds（time.monotonic，精度优于
# /proc/uptime 的 10ms）——run_one 不再自算套件段计时；init 段不经 execution.py，
# 保留本地 now_ms。结果 JSON 缺失（如进程被杀）计 0，由 results_gate 兜底判失败。
elapsed_ms=$("$PY" -c 'import json,sys
try: print(int(float(json.load(open(sys.argv[1]))["seconds"]) * 1000))
except (OSError, ValueError, KeyError): print(0)' "$RESULTS_DIR/$suite.test.log.json" 2>/dev/null) || elapsed_ms=$(( $(now_ms) - started ))
elapsed=$((elapsed_ms / 1000))
printf 'init_millis=%s\nsuite_millis=%s\n' "$init_millis" "$elapsed_ms" > "$RESULTS_DIR/$suite.timing"
line=$(tail -1 "$out")
status=ok
[ "$rc" -eq 0 ] || status=bad
printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "$rc" "$elapsed" "$status" "$line" >> "$RESULTS_DIR/lines"
