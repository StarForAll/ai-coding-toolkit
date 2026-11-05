#!/bin/bash
# 单个套件的隔离执行：私有 /tmp（tmpfs）+ 只读挂共享发行仓库。
# 由 run_all.sh 以 unshare -Urm 调用；套件里写死的 /tmp 路径因此天然互不干扰。
set -uo pipefail
suite=$1
: "${FIX:?}" "${HERE:?}" "${PY:?}" "${SHARED_RELEASE:?}" "${RESULTS_DIR:?}"

mount -t tmpfs tmpfs /tmp || { echo "$suite tmpfs-failed" >> "$RESULTS_DIR/lines"; exit 0; }
mkdir -p /tmp/wf-fixtures/release-repo /tmp/wf-fixtures
if [ -d "$SHARED_RELEASE" ]; then
  mount --bind "$SHARED_RELEASE" /tmp/wf-fixtures/release-repo 2>/dev/null || true
fi

out="$RESULTS_DIR/$suite.out"
if ! bash "$HERE/wf_fixture.sh" "$FIX" >"$out" 2>&1; then
  echo "$suite FIXTURE-FAILED" >> "$RESULTS_DIR/lines"; exit 0
fi
if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
  echo "$suite FIXTURE-INCOMPLETE" >> "$RESULTS_DIR/lines"; exit 0
fi
if ! WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >>"$out" 2>&1; then
  echo "$suite INIT-FAILED" >> "$RESULTS_DIR/lines"; exit 0
fi

started=$SECONDS
WF_FIX="$FIX" "$PY" "$HERE/$suite.py" >>"$out" 2>&1
rc=$?
elapsed=$((SECONDS - started))
bad=$(grep -c '\[FAIL\]' "$out" || true)
line=$(tail -1 "$out")
status=ok
if [ "$rc" -ne 0 ] || [ "$bad" -ne 0 ] || printf '%s' "$line" | grep -qE 'FAIL|(saved|total) 0'; then
  status=bad
fi
printf '%s\t%s\t%s\t%s\t%s\n' "$suite" "$rc" "$elapsed" "$status" "$line" >> "$RESULTS_DIR/lines"
