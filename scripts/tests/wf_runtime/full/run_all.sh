#!/bin/bash
# 全量复现：每个套件都从干净夹具开始；任一环节失败都会让脚本以非零码退出。
# 用法：bash run_all.sh [--wf_fix <dir>]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/softwares/python/bin/python3
FIX=${WF_FIX:-/tmp/wf-fixtures/rerun}
SUITES="cp1_tests cp2_tests cp3_tests cp4_tests cp5_b345 r1r2_tests r7r15_tests r17r24_tests r25r30_tests r31r34_tests r35r37_tests r38r39_tests r40r42_tests r43r45_tests r46_tests r47r48_tests r49_tests r50_tests r51r52_tests r53_tests r54_tests r55_tests r56_tests r57_tests r58_tests r59_tests r60_tests r61_tests r62_tests r63_tests r64_tests r65_tests r66_tests r67_tests r68_tests r69_tests r70_tests r71_tests r74_tests r75_tests r76_tests r77_tests r79_tests r80_tests r81_tests r82_tests r83_tests r84_tests r85_tests r86_tests r87_tests r88_tests r89_tests r90_tests"

REPO_ROOT=$(cd "$HERE/../../../.." && pwd)
RELEASE_REPO=${WF_RELEASE_REPO:-/tmp/wf-fixtures/release-repo}
SHARED_RELEASE="$RELEASE_REPO"
SOURCE_HOME="$HOME"

REBUILD_RELEASE=${WF_REBUILD_RELEASE:-1}

# 这些套件用"改成不可写目录"来模拟写入失败；在 user namespace 里我们是 root，chmod 不起作用，
# 所以它们必须在宿主 /tmp 的串行阶段跑（改造方案：改用"父路径是普通文件"触发 ENOTDIR，见 validation §87）。
PARALLEL_SERIAL="cp3_tests r1r2_tests r7r15_tests r67_tests r68_tests r69_tests r70_tests r71_tests r89_tests r90_tests"

prepare_release_repo() {
  # 依赖发行树的套件（f0 / d1 / r69 / r72）需要一份带 tag 的发行仓库。
  # 默认每次从源码重建（与"从零重建"的声明一致）；WF_REBUILD_RELEASE=0 时复用已有仓库。
  if [ "$REBUILD_RELEASE" = "0" ] && [ -f "$RELEASE_REPO/wf-release.json" ]; then
    return 0
  fi
  "$PY" "$REPO_ROOT/scripts/build-wf-release.py" --version 0.1.0 >/dev/null 2>&1 || return 1
  rm -rf "$RELEASE_REPO"
  mkdir -p "$RELEASE_REPO"
  cp -a "$REPO_ROOT/docs/workflows/wf-release/." "$RELEASE_REPO/" || return 1
  git -C "$RELEASE_REPO" init -q || return 1
  git -C "$RELEASE_REPO" config user.email tests@example.com
  git -C "$RELEASE_REPO" config user.name tests
  git -C "$RELEASE_REPO" add -A || return 1
  git -C "$RELEASE_REPO" commit -qm "wf release 0.1.0" >/dev/null || return 1
  git -C "$RELEASE_REPO" tag wf-v0.1.0 || return 1
}

prepare_release_repo || echo "release repo unavailable: 依赖发行树的套件将失败"

# ---- 并行执行（默认开启；WF_JOBS=1 退回串行） ----
JOBS=${WF_JOBS:-4}
RESULTS_DIR="${WF_RESULTS_DIR:-$HOME/.cache/wf-test-run/run-$$}"

can_unshare() {
  unshare -Urm bash -c 'mount -t tmpfs tmpfs /proc/self/fd >/dev/null 2>&1 || mount -t tmpfs tmpfs /tmp' >/dev/null 2>&1
}

run_suites_parallel() {
  local list="$1"
  mkdir -p "$RESULTS_DIR"
  : > "$RESULTS_DIR/lines"
  export FIX HERE PY SHARED_RELEASE="$RELEASE_REPO" RESULTS_DIR SOURCE_HOME="$HOME"
  printf '%s\n' $list | xargs -P "$JOBS" -I{} unshare -Urm bash "$HERE/run_one.sh" {}
  sort -t$'\t' -k1 "$RESULTS_DIR/lines" | awk -F'\t' '{printf "%-18s rc=%s %ss %s | %s\n", $1, $2, $3, $4, $5}'
  local bad
  bad=$(awk -F'\t' '$4!="ok"' "$RESULTS_DIR/lines" | wc -l)
  ran=$((ran + $(printf '%s\n' $list | wc -w)))
  fail=$((fail + bad))
}

fail=0
ran=0

run_suite() {
  local suite=$1
  mkdir -p "$RESULTS_DIR"
  local log="$RESULTS_DIR/$suite.out"
  if ! bash "$HERE/wf_fixture.sh" "$FIX" >"$log" 2>&1; then
    printf '%-18s FIXTURE-FAILED\n' "$suite"; fail=$((fail+1)); return
  fi
  if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
    printf '%-18s FIXTURE-INCOMPLETE\n' "$suite"; fail=$((fail+1)); return
  fi
  if ! WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >>"$log" 2>&1; then
    printf '%-18s INIT-FAILED\n' "$suite"; fail=$((fail+1)); return
  fi
  local out rc line started elapsed
  started=$SECONDS
  out=$(WF_FIX="$FIX" "$PY" "$HERE/$suite.py" 2>&1); rc=$?
  printf '%s\n' "$out" >> "$log"
  elapsed=$((SECONDS - started))
  line=$(printf '%s\n' "$out" | tail -1)
  printf '%-18s rc=%s %ss %s\n' "$suite" "$rc" "$elapsed" "$line"
  ran=$((ran+1))
  # 判定：退出码、汇总行里的失败数、输出中的 FAIL 都算失败
  local bad
  bad=$(printf '%s\n' "$out" | grep -c '\[FAIL\]')
  if [ "$rc" -ne 0 ] || [ "$bad" -ne 0 ] || printf '%s' "$line" | grep -qE 'FAIL|(saved|total) 0'; then
    fail=$((fail+1))
  fi
}

# 迭代期只跑相关套件：WF_SUITES="r88_tests r89_tests r90_tests" bash run_all.sh
SELECTED="${WF_SUITES:-}"
if [ -n "$SELECTED" ]; then
  SUITES="$SELECTED"
  SKIP_FLOWS=1
else
  SKIP_FLOWS=0
fi
PARALLEL_LIST=""
SERIAL_LIST=""
for suite in $SUITES; do
  case " $PARALLEL_SERIAL " in
    *" $suite "*) SERIAL_LIST="$SERIAL_LIST $suite" ;;
    *) PARALLEL_LIST="$PARALLEL_LIST $suite" ;;
  esac
done

if [ "$JOBS" -gt 1 ] && can_unshare; then
  run_suites_parallel "$PARALLEL_LIST"
  for suite in $SERIAL_LIST; do run_suite "$suite"; done
else
  [ "$JOBS" -gt 1 ] && echo "（unshare 不可用：退回串行）"
  for suite in $SUITES; do run_suite "$suite"; done
fi

# 专项流程：同样要求退出码与 PASS 计数
run_flow() {
  local name=$1 script=$2 expect=$3
  mkdir -p "$RESULTS_DIR"
  local log="$RESULTS_DIR/$name.out"
  if ! bash "$HERE/wf_fixture.sh" "$FIX" >"$log" 2>&1; then
    printf '%-18s FIXTURE-FAILED\n' "$name"; fail=$((fail+1)); return
  fi
  if ! WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >>"$log" 2>&1; then
    printf '%-18s INIT-FAILED\n' "$name"; fail=$((fail+1)); return
  fi
  local out rc got
  out=$(WF_FIX="$FIX" "$PY" "$HERE/$script.py" 2>&1); rc=$?
  got=$(printf '%s\n' "$out" | grep -c 'PASS')
  printf '%-18s rc=%s PASS=%s\n' "$name" "$rc" "$got"
  ran=$((ran+1))
  if [ "$rc" -ne 0 ] || [ "$got" -ne "$expect" ]; then fail=$((fail+1)); fi
}
run_extra() {
  # 直接调用的专项脚本体：计入 ran，判据为退出码与 PASS 计数
  local name=$1 script=$2 expect=$3 out rc got
  out=$(WF_FIX="${WF_FIX:-/tmp/wf-fixtures/f1}" "$PY" "$HERE/$script" 2>&1); rc=$?
  got=$(printf '%s\n' "$out" | grep -c 'PASS')
  printf '%-18s rc=%s PASS=%s\n' "$name" "$rc" "$got"
  ran=$((ran+1))
  if [ "$rc" -ne 0 ] || [ "$got" -lt "$expect" ]; then fail=$((fail+1)); fi
}
run_extra r72_tests r72_tests.py 7
# F0：从发行安装器装到一个空目录，再跑自举闭环
run_f0() {
  local target=/tmp/wf-fixtures/f0
  rm -rf "$target"; mkdir -p "$target"
  if ! "$PY" "$RELEASE_REPO/install.py" --target "$target" --release-ref refs/tags/wf-v0.1.0 \
      --source "$RELEASE_REPO" --platform dsh \
      --confirm      >/dev/null 2>&1; then
    printf '%-18s INSTALL-FAILED\n' f0; fail=$((fail+1)); return
  fi
  local out got
  out=$(WF_FIX="$target" "$PY" "$HERE/p5_f0.py" 2>&1); got=$?
  local passed
  passed=$(printf '%s\n' "$out" | grep -c 'PASS')
  printf '%-18s rc=%s PASS=%s\n' f0 "$got" "$passed"
  ran=$((ran+1))
  if [ "$got" -ne 0 ] || [ "$passed" -ne 9 ]; then fail=$((fail+1)); fi
}
if [ "$SKIP_FLOWS" = "0" ]; then
  # 流程只有 4 项（~10s），串行跑：它们都依赖共享 /tmp 里的发行仓库与 f0 目录
  run_f0
  run_flow p5_spec p5_spec 13
  run_flow p5_v2v3 p5_v2v3 12
  run_flow p5_v5 p5_v5 12
else
  echo "（WF_SUITES 子集模式：跳过 f0 与 p5 流程）"
fi

echo "---- 运行 $ran 项，失败 $fail 项 ----"
[ "$fail" -eq 0 ] || exit 1
exit 0
