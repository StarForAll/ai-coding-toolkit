#!/bin/bash
set -e
F=/tmp/wf-fixtures/f2
rm -rf "$F"; mkdir -p "$F/src" "$F/tests" "$F/.trellis"
cd "$F"
git init -q
git config user.email test@example.com; git config user.name tester
printf '# legacy project\n' > README.md
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
printf 'from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
printf '# Trellis 残留言据（非激活指令）\n' > .trellis/README.md
git add -A && git commit -qm "legacy import"
# 另一流程的外部提交（与本任务无交集）
printf 'external note\n' > NOTES.md
git add NOTES.md && git commit -qm "other process: add notes"
cd /home/xzc/projects/personal/ai-coding-toolkit
/softwares/python/bin/python3 scripts/wf-dev-deploy.py --target "$F" --platform dsh \
  --confirm --host-id dsh --verify-capability \
  --capability-evidence "kind=reentry;ref=夹具内同会话重入观察;by=test fixture" >/tmp/deploy_f2.log 2>&1
tail -2 /tmp/deploy_f2.log
