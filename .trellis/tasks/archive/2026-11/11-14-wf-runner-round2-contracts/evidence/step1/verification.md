# Step 1 验证记录（2026-11-14 20:05:06）

## 机械检查
```
$ grep -rn 'sys.path.insert(0, "/tmp")' scripts/tests | wc -l
0
$ find docs/workflows/wf scripts/tests \\( -name "*.pyc" -o -name "__pycache__" \\) | wc -l
0
$ git check-ignore -v scripts/tests/wf_runtime/__pycache__/x.pyc
.gitignore:12:__pycache__/	scripts/tests/wf_runtime/__pycache__/x.pyc
$ git check-ignore -v docs/workflows/wf/payload/lib/wflib/__pycache__/x.pyc
.gitignore:12:__pycache__/	docs/workflows/wf/payload/lib/wflib/__pycache__/x.pyc
```

## T0
858 tests, OK (skipped=10), 4.968s（PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache）

## r67 冒烟
rc=0, saved 15 / 15, GATE-OK；HYGIENE-OK pyc=0

## G9 缺根容错
空目录 snapshot/check 均退出 0，输出 HYGIENE-ABSENT ×2

## 可证伪性（植入 pyc）
植入 docs/workflows/wf/payload/lib/wflib/__pycache__/x.pyc → check 退出 1 并列出该路径；删除后恢复 0。

## r64 用例数
P3-1 删除后 saved 5 / 5（原 6）。
