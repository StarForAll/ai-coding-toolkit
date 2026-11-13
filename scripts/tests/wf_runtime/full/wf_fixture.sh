#!/bin/bash
# 重建夹具（仓库外临时目录）。
#
# 用法：
#   wf_fixture.sh <F> [nocap] [--deploy dev|candidate]
#                 [--release-root DIR --release-ref REF --release-version X.Y.Z] [--profile install]
#
# 部署来源：
#   dev       源码树 → `scripts/wf-dev-deploy.py`（安装记录 0.0.0-dev），T1/T2 用；
#   candidate 候选仓库根的 `install.py --source <候选根>`，安装后核对 installation.json
#             的 version / release_ref / rules_digest，不符即失败（不回退 dev）。
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
PY=/softwares/python/bin/python3
case "${1:-}" in -h|--help) sed -n '2,14p' "$0"; exit 0 ;; esac
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
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) if [ -z "$F" ]; then F="$1"; else MODE="$1"; fi; shift ;;
  esac
done
F=${F:-/tmp/wf-fixtures/f1}
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
    "$PY" - "$F" "$RELEASE_ROOT" "$RELEASE_REF" "$RELEASE_VERSION" <<'PY'
import json, os, sys

target, release_root, expected_ref, expected_version = sys.argv[1:5]
install = os.path.join(target, ".wf", "install", "installation.json")
try:
    with open(install, encoding="utf-8") as handle:
        record = json.load(handle)
except (OSError, ValueError) as exc:
    raise SystemExit(f"wf_fixture: 读取安装记录失败：{exc}")
with open(os.path.join(release_root, "wf-release.json"), encoding="utf-8") as handle:
    manifest = json.load(handle)
problems = []
if record.get("version") != expected_version:
    problems.append(f"version={record.get('version')!r} expected={expected_version!r}")
if record.get("release_ref") != expected_ref:
    problems.append(f"release_ref={record.get('release_ref')!r} expected={expected_ref!r}")
expected_digest = (manifest.get("compatibility") or {}).get("rules_digest")
if record.get("rules_digest") != expected_digest:
    problems.append(f"rules_digest={record.get('rules_digest')!r} expected={expected_digest!r}")
if record.get("version") == "0.0.0-dev":
    problems.append("安装记录仍是 dev 占位版本 0.0.0-dev")
if problems:
    raise SystemExit("wf_fixture: 候选安装记录与候选身份不一致：" + "; ".join(problems))
print(f"candidate install ok: version={expected_version} ref={expected_ref}")
PY
    ;;
  *)
    echo "wf_fixture: --deploy 只接受 dev|candidate（收到 '$DEPLOY'）" >&2; exit 2 ;;
esac
tail -2 "$DEPLOY_LOG"
