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
bash scripts/tests/wf_runtime/full/repro/run.sh              # 默认 both、单并发，构建/复用测试发行缓存
bash scripts/tests/wf_runtime/full/repro/run.sh --no-build   # 已有新鲜缓存时校验并复用
bash scripts/tests/wf_runtime/full/repro/run.sh --only bind  # 只跑名字含子串的
bash scripts/tests/wf_runtime/full/repro/run.sh --list       # 列出用例
```

默认 both 模式退出码 0 才表示"每条用例的 green 与 red 都成立"；机器可读汇总为
`REPRO_TOTAL= / REPRO_PASSED= / REPRO_FAILED= / REPRO_FAILING:`，供上层脚本消费。
`run_all.sh` 已改为委托本脚本（不再另写一套循环）。

CLI 级用例由运行器传入测试发行缓存或候选仓库；T1/T2 不重建产品发行树。通过本入口运行，避免直接执行单条脚本时借用旧发行。

`--mode auto` 使用 schema 2 的逐用例 green/red 输入摘要。green 不会刷新 red 证据，helper 改动后局部运行不会刷新其他用例。未知目标与旧 schema 1 缓存要求 both；损坏/未知 schema 缓存明确拒绝覆盖。运行前冻结输入，运行后及状态提交前重核。结果目录无主或符号链接时拒绝清理；日志、模式、退出状态和计划不一致时计失败。
