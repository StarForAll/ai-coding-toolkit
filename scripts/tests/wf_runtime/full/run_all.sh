#!/bin/bash
# 全量复现：每个套件都从干净夹具开始；任一环节失败都会让脚本以非零码退出。
# 用法：bash run_all.sh [--wf_fix <dir>]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PY=/softwares/python/bin/python3
FIX=${WF_FIX:-/tmp/wf-fixtures/rerun}
SUITES="cp1_tests cp2_tests cp3_tests cp4_tests cp5_b345 r1r2_tests r7r15_tests r17r24_tests r25r30_tests r31r34_tests r35r37_tests r38r39_tests r40r42_tests r43r45_tests r46_tests r47r48_tests r49_tests r50_tests r51r52_tests r53_tests r54_tests r55_tests r56_tests r57_tests r58_tests r59_tests r60_tests r61_tests r62_tests r63_tests r64_tests r65_tests r66_tests r67_tests r68_tests r69_tests r70_tests r71_tests r74_tests r75_tests r76_tests r77_tests r79_tests r80_tests r81_tests r82_tests r83_tests r84_tests r85_tests r86_tests r87_tests r88_tests"

REPO_ROOT=$(cd "$HERE/../../../.." && pwd)
RELEASE_REPO=${WF_RELEASE_REPO:-/tmp/wf-fixtures/release-repo}

REBUILD_RELEASE=${WF_REBUILD_RELEASE:-1}

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

fail=0
ran=0

run_suite() {
  local suite=$1
  if ! bash "$HERE/wf_fixture.sh" "$FIX" >/dev/null 2>&1; then
    printf '%-18s FIXTURE-FAILED\n' "$suite"; fail=$((fail+1)); return
  fi
  if [ ! -f "$FIX/.wf/bin/wf.py" ]; then
    printf '%-18s FIXTURE-INCOMPLETE\n' "$suite"; fail=$((fail+1)); return
  fi
  if ! WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >/dev/null 2>&1; then
    printf '%-18s INIT-FAILED\n' "$suite"; fail=$((fail+1)); return
  fi
  local out rc line
  out=$(WF_FIX="$FIX" "$PY" "$HERE/$suite.py" 2>&1); rc=$?
  line=$(printf '%s\n' "$out" | tail -1)
  printf '%-18s rc=%s %s\n' "$suite" "$rc" "$line"
  ran=$((ran+1))
  # 判定：退出码、汇总行里的失败数、输出中的 FAIL 都算失败
  local bad
  bad=$(printf '%s\n' "$out" | grep -c '\[FAIL\]')
  if [ "$rc" -ne 0 ] || [ "$bad" -ne 0 ] || printf '%s' "$line" | grep -qE 'FAIL|(saved|total) 0'; then
    fail=$((fail+1))
  fi
}

for suite in $SUITES; do run_suite "$suite"; done

# 专项流程：同样要求退出码与 PASS 计数
run_flow() {
  local name=$1 script=$2 expect=$3
  if ! bash "$HERE/wf_fixture.sh" "$FIX" >/dev/null 2>&1; then
    printf '%-18s FIXTURE-FAILED\n' "$name"; fail=$((fail+1)); return
  fi
  if ! WF_FIX="$FIX" "$PY" "$HERE/f1_init.py" >/dev/null 2>&1; then
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
      --source "$RELEASE_REPO" --skill-root /tmp/wf-fixtures/skills-f0 \
      --confirm --host-id dsh --verify-capability \
      --capability-evidence "kind=reentry;ref=夹具内同会话重入观察;by=test fixture" >/dev/null 2>&1; then
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
run_f0

run_flow p5_spec p5_spec 13
run_flow p5_v2v3 p5_v2v3 12
run_flow p5_v5 p5_v5 12

echo "---- 运行 $ran 项，失败 $fail 项 ----"
[ "$fail" -eq 0 ] || exit 1
exit 0
