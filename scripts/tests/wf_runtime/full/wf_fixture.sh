#!/bin/bash
# 重建夹具（仓库外临时目录）。详细用法：wf_fixture.sh --help
set -e
# usage 是唯一文本来源（heredoc），不按行号回头注释提取——头注释不再承载正文。
usage() { cat <<'EOF'
用法：
  wf_fixture.sh <F> [nocap] [--deploy dev|candidate]
                [--release-root DIR --release-ref REF --release-version X.Y.Z] [--profile install]

部署来源：
  dev       源码树 → `scripts/wf-dev-deploy.py`（安装记录 0.0.0-dev），T1/T2 用；
  candidate 候选仓库根的 `install.py --source <候选根>`，安装后核对 installation.json
            的 version / release_ref / source_commit / rules_digest 与 `.wf/lib` 内容，
            不符即失败（不回退 dev）。
EOF
}
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY=/softwares/python/bin/python3
case "${1:-}" in -h|--help) usage; exit 0 ;; esac
if [ "${WF_RUNNER_ENTRY_PID:-}" != "$$" ] || [ -z "${WF_FIXTURE_LEASE_FD:-}" ] \
  || ! "$PY" "$HERE/fixture_scope.py" check-lease >/dev/null 2>&1; then
  export WF_RUNNER_ENTRY_PID=$$
  exec "$PY" "$HERE/fixture_scope.py" lease -- bash "$0" "$@"
fi

F=""
MODE="verified"
DEPLOY=""
RELEASE_ROOT=""
RELEASE_REF=""
RELEASE_VERSION=""
PROFILE="install"
while [ $# -gt 0 ]; do
  case "$1" in
    --deploy) DEPLOY="${2:-}"; shift 2 ;;
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --release-ref) RELEASE_REF="${2:-}"; shift 2 ;;
    --release-version) RELEASE_VERSION="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) if [ -z "$F" ]; then F="$1"; else MODE="$1"; fi; shift ;;
  esac
done
F=${F:-${WF_LEGACY_FIXTURE_ROOT:-${TMPDIR:-/tmp}/wf-fixtures}/f1}
DEPLOY=${DEPLOY:-${WF_FIXTURE_DEPLOY:-dev}}
RELEASE_ROOT=${RELEASE_ROOT:-${WF_RELEASE_ROOT:-}}
RELEASE_REF=${RELEASE_REF:-${WF_RELEASE_REF:-}}
RELEASE_VERSION=${RELEASE_VERSION:-${WF_RELEASE_VERSION:-}}

if [ "$PROFILE" != "install" ]; then
  echo "wf_fixture: 未知 profile '$PROFILE'（Phase 1 只实现 install）" >&2
  exit 2
fi

"$PY" "$HERE/fixture_scope.py" reset "$F"
mkdir -p "$F/src" "$F/tests"
DEPLOY_LOG=$(mktemp "$F/.deploy.XXXXXX")
trap 'rm -f "$DEPLOY_LOG"' EXIT
cd "$F"
git init -q
mkdir -p .git/info
printf '/.wf/tasks/**/check-logs/\n' >> .git/info/exclude
git config user.email test@example.com; git config user.name tester
printf '# demo project\n' > README.md
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
printf 'from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
git add README.md src/calc.py tests/test_calc.py && git commit -qm "initial import"
cd "$REPO"

case "$DEPLOY" in
  dev)
    if [ -n "$RELEASE_ROOT$RELEASE_REF$RELEASE_VERSION" ]; then
      echo "wf_fixture: dev 模式不接受 --release-root/--release-ref/--release-version" >&2
      exit 2
    fi
    "$PY" "$REPO/scripts/wf-dev-deploy.py" --target "$F" --platform dsh --confirm >"$DEPLOY_LOG" 2>&1
    ;;
  candidate)
    if [ -z "$RELEASE_ROOT" ] || [ -z "$RELEASE_REF" ] || [ -z "$RELEASE_VERSION" ]; then
      echo "wf_fixture: candidate 模式需要 --release-root/--release-ref/--release-version" >&2
      exit 2
    fi
    if [ ! -f "$RELEASE_ROOT/install.py" ]; then
      echo "wf_fixture: 候选仓库根缺少 install.py：$RELEASE_ROOT" >&2
      exit 2
    fi
    "$PY" "$RELEASE_ROOT/install.py" --target "$F" --release-ref "$RELEASE_REF" \
      --source "$RELEASE_ROOT" --platform dsh --confirm >"$DEPLOY_LOG" 2>&1 || {
      echo "wf_fixture: 候选安装失败（见 $DEPLOY_LOG）" >&2; tail -5 "$DEPLOY_LOG" >&2; exit 1; }
    "$PY" "$HERE/verify_install_identity.py" --target "$F" --release-root "$RELEASE_ROOT" \
      --ref "$RELEASE_REF" --version "$RELEASE_VERSION" || {
      echo "wf_fixture: 候选安装记录与候选身份不一致（不回退 dev）" >&2; exit 1; }
    ;;
  *)
    echo "wf_fixture: --deploy 只接受 dev|candidate（收到 '$DEPLOY'）" >&2; exit 2 ;;
esac
tail -2 "$DEPLOY_LOG"
