#!/bin/bash
# 重建 D1 两个夹具到 $HOME/.cache/wf-fixtures（抗 /tmp 清空）
set -e
# 仓库根由脚本位置派生（脚本位于 <repo>/scripts/tests/wf_runtime/full/）
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd)
# 项目声明解释器（AGENTS.md §4 的回退链约定；shell 入口无 sys.executable）
PY=/softwares/python/bin/python3
if [ "${WF_RUNNER_ENTRY_PID:-}" != "$$" ] || [ -z "${WF_FIXTURE_LEASE_FD:-}" ] \
  || ! "$PY" "$ROOT/scripts/tests/wf_runtime/full/fixture_scope.py" check-lease >/dev/null 2>&1; then
  export WF_RUNNER_ENTRY_PID=$$
  exec "$PY" "$ROOT/scripts/tests/wf_runtime/full/fixture_scope.py" lease -- bash "$0" "$@"
fi
for name in d1host d1wf; do
  T="$HOME/.cache/wf-fixtures/$name"
  "$PY" "$ROOT/scripts/tests/wf_runtime/full/fixture_scope.py" reset "$T"
  mkdir -p "$T/src" "$T/tests"
  ( cd "$T" && git init -q && git config user.email t@example.com && git config user.name t \
    && printf '# demo\n' > README.md && printf 'x=1\n' > src/a.py && git add -A && git commit -qm init )
done
"$PY" "$ROOT/scripts/tests/wf_runtime/full/fixture_scope.py" reset /tmp/wf-fixtures/skills-d1
"$PY" "$ROOT/scripts/tests/wf_runtime/full/fixture_scope.py" reset /tmp/wf-fixtures/skills-d1w
"$PY" "$ROOT/scripts/wf-dev-deploy.py" --target "$HOME/.cache/wf-fixtures/d1host" \
  --platform dsh --confirm  --verified-version "dsh-session-2026-11-04" \
  >/dev/null
"$PY" "$ROOT/scripts/wf-dev-deploy.py" --target "$HOME/.cache/wf-fixtures/d1wf" \
  --provider wf --platform dsh --confirm  --verified-version "wf-issued-2026-11-04" >/dev/null
