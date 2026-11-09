# repro/：修复的可证伪用例

每条已声明的修复配一个脚本，契约由 `_harness.py` 固定：

| 模式 | 做什么 | 期望 |
|---|---|---|
| `--expect green` | 在当前树上跑 check | 成立（退出 0） |
| `--expect red` | 把 payload 复制到临时目录，**注入"退回修复前"的那一处**，再跑同一 check | check 必须变红（退出 0 表示"如预期变红"） |

两者都过才说明：这条断言能区分"修好了"和"没修"——但只有 `TargetFailure` 能在 red 模式算通过，内部错误、前置失败、未归类字符串都不行（第十/十一轮复审）。只跑 green 的用例等于没有证据——
空断言、`expected == actual`、候选与规则不相交的空匹配、只记目录的快照，都会在 red 模式下原形毕露。

## 新增一条

1. 命名 `<批次>-<编号>-<短名>.py`，如 `f5-4-generation-bool.py`。
2. 用 `_harness.stage()` 拿临时 payload 副本；`WF_REPRO_INJECT=1` 时 `_harness.patch()` 注入缺陷。
3. `check()` 成立时返回 `None`；**目标断言被击中**时 `raise H.TargetFailure(原因)`；**夹具/环境/内部错误**时 `raise H.Precondition(原因)`。返回字符串已被视为未归类失败（两种模式都不通过）。
4. 跑 `--expect green` 与 `--expect red` 都要退出 0；`run_all.sh` 会自动汇总。

## 已知边界

- 只能证明"已声明的修复被验证过"，不能证明"没有未被发现的缺陷"。
- 注入点写死源码片段：实现改动后脚本会报 `repro stale`，必须同批更新，否则等于失效证据。
- 锁对象（`.wf-lock`）不属于写入产物，目录快照需显式排除。

## 一键运行（CI 可用）

```bash
bash scripts/tests/wf_runtime/full/repro/run.sh              # 重建发行后全跑
bash scripts/tests/wf_runtime/full/repro/run.sh --no-build   # 上层已重建时跳过
bash scripts/tests/wf_runtime/full/repro/run.sh --only bind  # 只跑名字含子串的
bash scripts/tests/wf_runtime/full/repro/run.sh --list       # 列出用例
```

退出码 0 才表示"每条用例的 green 与 red 都成立"；机器可读汇总为
`REPRO_TOTAL= / REPRO_PASSED= / REPRO_FAILED= / REPRO_FAILING:`，供上层脚本消费。
`run_all.sh` 已改为委托本脚本（不再另写一套循环）。

**必须先重建发行**：CLI 级用例通过 `install.py` 从 `docs/workflows/wf-release/` 部署，
直接跑单条脚本而不重建，会测到上一次的发行树。
