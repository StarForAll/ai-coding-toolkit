#!/bin/bash
# 重建夹具（仓库外临时目录）。第二个参数可为 "nocap" 表示不声明能力已核实。
set -e
F=${1:-/tmp/wf-fixtures/f1}
MODE=${2:-verified}
rm -rf "$F"; mkdir -p "$F/src" "$F/tests"
cd "$F"
git init -q
git config user.email test@example.com; git config user.name tester
printf '# demo project\n' > README.md
printf 'def add(a, b):\n    return a + b\n' > src/calc.py
printf 'from src.calc import add\n\ndef test_add():\n    assert add(1, 2) == 3\n' > tests/test_calc.py
git add README.md src/calc.py tests/test_calc.py && git commit -qm "initial import"
cd /home/xzc/projects/personal/ai-coding-toolkit
if [ "$MODE" = "nocap" ]; then
  /softwares/python/bin/python3 scripts/wf-dev-deploy.py --target "$F" \
    --platform dsh --confirm >/tmp/deploy.log 2>&1
else
  /softwares/python/bin/python3 scripts/wf-dev-deploy.py --target "$F" \
    --platform dsh --confirm    >/tmp/deploy.log 2>&1
fi
tail -2 /tmp/deploy.log
