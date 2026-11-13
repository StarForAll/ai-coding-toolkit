#!/bin/bash
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../../.." && pwd)
F=${WF_LEGACY_FIXTURE_ROOT:-/tmp/wf-fixtures}/f2
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
"$PY" scripts/wf-dev-deploy.py --target "$F" --platform dsh --confirm >"$deploy_log" 2>&1
tail -2 "$deploy_log"
