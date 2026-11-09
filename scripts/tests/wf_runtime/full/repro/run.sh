#!/usr/bin/env bash
# 修复的可证伪用例：一键（CI 可用）运行器。
#
# 每条用例跑两次：`--expect green`（当前树成立）与 `--expect red`（注入原缺陷后必须变红）。
# 两种都过才算通过——只有 green 的"证据"无法区分"修好了"和"没修"。
#
# 用法：
#   bash .../repro/run.sh              # 重建发行后全跑（CLI 级用例从发行树部署，必须先重建）
#   bash .../repro/run.sh --no-build   # 跳过重建（已被上层脚本重建过时用）
#   bash .../repro/run.sh --only bind  # 只跑名字含子串的用例
#   bash .../repro/run.sh --list       # 列出用例
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL="$(dirname "$HERE")"
REPO="$(cd "$FULL/../../../.." && pwd)"
PY="${PY:-/softwares/python/bin/python3}"

BUILD=1
ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-build) BUILD=0 ;;
    --only) shift; ONLY="${1:-}" ;;
    --list) ls "$HERE"/[a-z0-9]*.py 2>/dev/null | xargs -r -n1 basename | sed 's/\.py$//'; exit 0 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$BUILD" -eq 1 ]; then
  echo "重建发行树（CLI 级用例从发行树部署）"
  if ! "$PY" "$REPO/scripts/build-wf-release.py" --version 0.1.0 >/dev/null; then
    echo "BUILD-FAILED"; exit 1
  fi
  if ! "$PY" "$REPO/scripts/build-wf-release.py" --verify >/dev/null; then
    echo "VERIFY-FAILED"; exit 1
  fi
fi

total=0; passed=0; failed=0; failures=""
for script in "$HERE"/[a-z0-9]*.py; do
  [ -f "$script" ] || continue
  name="$(basename "$script" .py)"
  case "$name" in *"$ONLY"*) ;; *) continue ;; esac
  total=$((total + 1))
  ok=1
  for mode in green red; do
    if ! out="$("$PY" "$script" --expect "$mode" 2>&1)"; then
      ok=0
      echo "FAIL $name [$mode] $(printf '%s' "$out" | tail -1)"
    fi
  done
  if [ "$ok" -eq 1 ]; then
    passed=$((passed + 1)); echo "ok   $name"
  else
    failed=$((failed + 1)); failures="$failures $name"
  fi
done

if [ "$total" -eq 0 ]; then
  echo "REPRO_TOTAL=0"
  echo "REPRO_PASSED=0"
  echo "REPRO_FAILED=1"
  echo "REPRO_FAILING: no-case-matched(only=${ONLY})"
  echo "repro 用例：0/0（--only 未匹配任何用例，按失败处理）"
  exit 1
fi

echo "REPRO_TOTAL=$total"
echo "REPRO_PASSED=$passed"
echo "REPRO_FAILED=$failed"
[ -n "$failures" ] && echo "REPRO_FAILING:$failures"
echo "repro 用例：$passed/$total（每条同时过 green 与 red）"
[ "$failed" -eq 0 ]
