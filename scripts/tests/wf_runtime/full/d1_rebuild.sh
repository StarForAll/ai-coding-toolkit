#!/bin/bash
# 重建 D1 两个夹具到 $HOME/.cache/wf-fixtures（抗 /tmp 清空）
set -e
ROOT=/home/xzc/projects/personal/ai-coding-toolkit
for name in d1host d1wf; do
  T="$HOME/.cache/wf-fixtures/$name"
  rm -rf "$T"; mkdir -p "$T/src" "$T/tests"
  ( cd "$T" && git init -q && git config user.email t@example.com && git config user.name t \
    && printf '# demo\n' > README.md && printf 'x=1\n' > src/a.py && git add -A && git commit -qm init )
done
rm -rf /tmp/wf-fixtures/skills-d1 /tmp/wf-fixtures/skills-d1w
/softwares/python/bin/python3 "$ROOT/scripts/wf-dev-deploy.py" --target "$HOME/.cache/wf-fixtures/d1host" \
  --platform dsh --confirm --host-id dsh --verify-capability \
  --capability-evidence "kind=reentry;ref=夹具内同会话重入观察;by=test fixture" \
  --verified-version "dsh-session-2026-11-04" \
  --capability-evidence "kind=compaction;ref=2026-11-04 真实压缩后 \$DSH_SESSION_ID 仍为 session-826cbd83;by=human" >/dev/null
/softwares/python/bin/python3 "$ROOT/scripts/wf-dev-deploy.py" --target "$HOME/.cache/wf-fixtures/d1wf" \
  --provider wf --platform dsh --confirm --host-id dsh --verify-capability \
  --capability-evidence "kind=reentry;ref=夹具内同会话重入观察;by=test fixture" \
  --verified-version "wf-issued-2026-11-04" >/dev/null
