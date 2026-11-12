# 第十九轮外部评审的复核与修正（1 项）

- 复核对象：外部评审第 19 轮 1 条（单变量配置对照）
- 处置编号 R56；实施与实跑见 `validation.md` §42

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | `spec_verify_days` 非法时 Check 静默回退 90 天继续判断 | **成立** | 设计稿 §3「非法项阻断依赖该项的判断，不能放宽门禁」 | R56 |

上一轮批准决定的单变量正反例本轮复验通过。

## 1. 复核

`load_project_config` 已经把非法值记进 `problems`（`spec_verify_days must be a positive integer`），`_spec_coverage` 也接住了 `problems`，**但拿到之后只在 `try/except` 里回退 90 天，从不据此阻断**。探针：同一份两天前核实的 spec，配置 `1` 时正确要求处置到期条目；配置 `"invalid-period"` 时 Check 直接通过——而检查记录里同时存着那条 problem。检测到了、却没约束门禁。

## 2. 处置（R56）

- 把「键缺失」与「键存在但非法」分开：键缺失 → 用发行缺省（`config.DEFAULTS`，不阻断）；键存在但非法 → 记 `period_problems` 并**阻断**。
- 配置整体不可读（非对象等）时同样按非法处理。
- `coverage.period_problems` 与 `missing_curation`/`unresolved` 同列，一并触发 `WF_SPEC_INCOMPLETE`；`period_days` 与 `period_problems` 都进入 `check.spec_review`，事后可核对。
- 不牵连无关配置错误：其他键的问题仍按既有局部阻断规则处理，不扩大为整体阻断。

## 3. 边界

- 不新增原因码：仍用 `WF_SPEC_INCOMPLETE`（缺项类），不升级为配置整体不可用。
- 不改变合法值的语义（`1` 就是 1 天）。
- 不在 Check 里改写配置：只报告。

## 4. 对收口状态的影响

属「检测到但不约束门禁」，正是设计稿 §3 要防的放宽门禁；收口前必修。落地后需重跑 Check 相关（CP1/CP3/CP5、R13/R18/R21/R34/R43）与三夹具全流程、F0。
