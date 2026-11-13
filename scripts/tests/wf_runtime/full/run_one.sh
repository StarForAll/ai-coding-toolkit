#!/bin/bash
# 单个套件的隔离执行：私有 /tmp（tmpfs）+ 只读挂共享发行仓库。
# 由 run_all.sh 以 unshare -Urm 调用；套件里写死的 /tmp 路径因此天然互不干扰。
# 部署来源与发行参数通过环境（WF_FIXTURE_DEPLOY / WF_RELEASE_*）传进来。
set -uo pipefail
suite=$1
: "${FIX:?}" "${HERE:?}" "${PY:?}" "${SHARED_RELEASE:?}" "${RESULTS_DIR:?}"

mount -t tmpfs tmpfs /tmp || { echo "$suite tmpfs-failed" >> "$RESULTS_DIR/lines"; exit 0; }
mkdir -p /tmp/wf-fixtures/release-repo /tmp/wf-fixtures
if [ -d "$SHARED_RELEASE" ]; then
  mount --bind "$SHARED_RELEASE" /tmp/wf-fixtures/release-repo 2>/dev/null || true
fi

out="$RESULTS_DIR/$suite.out"
: > "$out"
init_started=$SECONDS
prep_rc=0
if [ "${WF_TEMPLATE_READY:-0}" = "1" ]; then
  # 夹具模板只读：每套件复制独立一份，再核对空态（绝对路径残留/安装身份）
  rm -rf "$FIX"
  cp -a "$WF_TEMPLATE" "$FIX" >>"$out" 2>&1 || prep_rc=3
  if [ "$prep_rc" -eq 0 ]; then
    check_args=(--quiet)
    if [ "$WF_FIXTURE_DEPLOY" = "candidate" ]; then
      check_args=(--quiet --version "$WF_RELEASE_VERSION" --ref "$WF_RELEASE_REF")
    fi
    "$PY" "$HERE/template_check.py" "$FIX" --repoint-from "$WF_TEMPLATE" "${check_args[@]}" >>"$out" 2>&1 || prep_rc=4
  fi
else
  bash "$HERE/wf_fixture.sh" "$FIX" >>"$out" 2>&1 || prep_rc=1
  if [ "$prep_rc" -eq 0 ]; then
    WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >>"$out" 2>&1 || prep_rc=2
  fi
fi
if [ "$prep_rc" -ne 0 ]; then
  printf 'init_millis=%s\nsuite_millis=0\n' "$(( (SECONDS - init_started) * 1000 ))" > "$RESULTS_DIR/$suite.timing"
  case "$prep_rc" in
    1) label=FIXTURE-FAILED ;;
    2) label=INIT-FAILED ;;
    3) label=TEMPLATE-COPY-FAILED ;;
    4) label=TEMPLATE-COPY-INVALID ;;
    *) label=FIXTURE-FAILED ;;
  esac
  echo "$suite $label" >> "$RESULTS_DIR/lines"; exit 0
fi
if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
  printf 'init_millis=%s\nsuite_millis=0\n' "$(( (SECONDS - init_started) * 1000 ))" > "$RESULTS_DIR/$suite.timing"
  echo "$suite FIXTURE-INCOMPLETE" >> "$RESULTS_DIR/lines"; exit 0
fi
init_millis=$(( (SECONDS - init_started) * 1000 ))

started=$SECONDS
WF_FIX="$FIX" "$PY" "$HERE/$suite.py" >>"$out" 2>&1
rc=$?
elapsed=$((SECONDS - started))
printf 'init_millis=%s\nsuite_millis=%s\n' "$init_millis" "$((elapsed * 1000))" > "$RESULTS_DIR/$suite.timing"
bad=$(grep -c '\[FAIL\]' "$out" || true)
line=$(tail -1 "$out")
status=ok
if [ "$rc" -ne 0 ] || [ "$bad" -ne 0 ] || printf '%s' "$line" | grep -qE 'FAIL|(saved|total) 0'; then
  status=bad
fi
printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "$rc" "$elapsed" "$status" "$line" >> "$RESULTS_DIR/lines"
