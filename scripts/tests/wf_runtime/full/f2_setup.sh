#!/bin/bash
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
F=${WF_LEGACY_FIXTURE_ROOT:-${TMPDIR:-/tmp}/wf-fixtures}/f2
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY=/softwares/python/bin/python3
if [ "${WF_RUNNER_ENTRY_PID:-}" != "$$" ] || [ -z "${WF_FIXTURE_LEASE_FD:-}" ] \
  || ! "$PY" "$HERE/fixture_scope.py" check-lease >/dev/null 2>&1; then
  export WF_RUNNER_ENTRY_PID=$$
  exec "$PY" "$HERE/fixture_scope.py" lease -- bash "$0" "$@"
fi
"$PY" "$HERE/fixture_scope.py" reset "$F"
mkdir -p "$F/src" "$F/tests" "$F/.trellis"
cd "$F"
git init -q
mkdir -p .git/info
printf '/.wf/tasks/**/check-logs/\n' >> .git/info/exclude
git config user.email test@example.com; git config user.name tester
printf '# legacy project\n' > README.md
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
printf 'from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
printf '# Trellis 残留言据（非激活指令）\n' > .trellis/README.md
git add -A && git commit -qm "legacy import"
# 另一流程的外部提交（与本任务无交集）
printf 'external note\n' > NOTES.md
git add NOTES.md && git commit -qm "other process: add notes"
cd "$REPO"
deploy_log=$(mktemp "$F/.deploy.XXXXXX")
trap 'rm -f "$deploy_log"' EXIT
case "${WF_FIXTURE_DEPLOY:-dev}" in
  dev)
    "$PY" scripts/wf-dev-deploy.py --target "$F" --platform dsh --confirm >"$deploy_log" 2>&1
    ;;
  candidate)
    # 候选模式：用本次已核发行的安装器（缺失即失败，不回退 dev 部署器）。
    : "${WF_RELEASE_ROOT:?f2_setup: candidate 模式需要 WF_RELEASE_ROOT}"
    : "${WF_RELEASE_REF:?f2_setup: candidate 模式需要 WF_RELEASE_REF}"
    : "${WF_RELEASE_VERSION:?f2_setup: candidate 模式需要 WF_RELEASE_VERSION}"
    [ -f "$WF_RELEASE_ROOT/install.py" ] || {
      echo "f2_setup: 候选根缺少 install.py：$WF_RELEASE_ROOT" >&2; exit 2; }
    "$PY" "$WF_RELEASE_ROOT/install.py" --target "$F" --release-ref "$WF_RELEASE_REF" \
      --source "$WF_RELEASE_ROOT" --platform dsh --confirm >"$deploy_log" 2>&1 || {
      echo "f2_setup: 候选安装失败（见 $deploy_log）" >&2; tail -5 "$deploy_log" >&2; exit 1; }
    "$PY" "$HERE/verify_install_identity.py" --target "$F" --release-root "$WF_RELEASE_ROOT" \
      --ref "$WF_RELEASE_REF" --version "$WF_RELEASE_VERSION" || {
      echo "f2_setup: F2 安装身份不是本次候选（不回退 dev）" >&2; exit 1; }
    ;;
  *)
    echo "f2_setup: WF_FIXTURE_DEPLOY 只接受 dev|candidate（收到 '${WF_FIXTURE_DEPLOY:-}'）" >&2
    exit 2 ;;
esac
tail -2 "$deploy_log"
