# 第三十五轮外部评审的复核与修正（3 项）

- 处置编号 R71；实跑见 `validation.md` §61

## 0. 结论

| # | 原判 | 复核 | 处置 |
|---|---|---|---|
| 1 | 写权交接两端都漏实例标识核验 | **成立** | `begin`/`accept` 均接入 `_require_instance_match` |
| 2 | `repair --dispose` 锁内不重核预览，可应用未经确认的计划 | **成立** | 锁内 `dispose_preview` 重算并比摘要 |
| 3 | 审查不要求五轴齐全，空 axes 也算 pass | **成立** | 固定五轴齐全 + 结论合法 + 拒绝未知轴 |

## 1. 交接的实例核验

获取与释放写权已接 `_require_instance_match`，交接两段却漏了：

- `begin`：`require_held()` 之后补实例与能力核对——错误的 `instance_id` 现在 `WF_BINDING_MISMATCH`，写者保持 `held`，不会把原代次作废。
- `accept`：拿到绑定后同样调用统一校验，再核对象一致性。

用同一个函数而不是各入口手写，是这一条的要害——上一轮修 acquire/release 时就是漏掉了"另一条改写权的路"。

## 2. `repair --dispose` 的锁内重核

普通 `repair` 已有锁内重核，`dispose_flow` 却在校验令牌后直接 `dispose_plan()`，而后者**重新读文件**——于是"预览的是回执 A、应用的是回执 B"能成立。

现在锁内先 `dispose_preview(root, plan_path)` 重算并比摘要，不一致即 `WF_PREVIEW_STALE`，`dispose_plan` 不会被调用（实测：计划被替换时 disposition 仍为空）。

## 3. 审查五轴

原实现只遍历"报告里出现的轴"，于是 `axes: {}` 与"只报一轴"都算通过——等于把"没覆盖必要检查面"解释成通过。

现在按协议（`wf-review` skill、机制稿 §9.2）核：
- **五轴齐全**：`range / acceptance / contract / regression / testability` 缺一即 `WF_REVIEW_INVALID`（输入不成立）；
- **结论合法**：每轴取 `pass|fail|uncovered`，非法值拒绝；
- **拒绝未知轴**：出现五轴之外的键即拒绝，防止用自造轴充数；
- 轴结论非 `pass` 仍按上一轮口径记 `fail` 并留痕（有效审查判否）。

顺带纠正口径混用：此前用例拿 Check 内部自审的 `standard/requirement` 当外部审查轴，现全部改为外部五轴。

## 4. 用例

`r71_tests.py` 10 条：交接错误实例被拒且写者不变、正常交接、dispose 计划被替换时预览失效且不写回、五轴齐全通过、空 axes / 单轴 / 缺轴 / 未知轴四种拒绝。
