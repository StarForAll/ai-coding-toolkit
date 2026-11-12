# 第二十轮外部评审的复核与修正（1 项，4 个残留分支）

- 复核对象：外部评审第 20 轮 1 条（只读复验）
- 处置编号 R57；实施与实跑见 `validation.md` §43

## 0. 结论

| # | 原判 | 复核 | 契约依据 | 处置 |
|---|---|---|---|---|
| 1 | 「配置已判非法、消费者仍继续使用」尚未整体闭合 | **成立** | 设计稿 §3「非法项阻断依赖该判断，不能放宽门禁」 | R57 |

上一轮 `spec_verify_days` 已修，本轮复验通过；但同一根因在其余键上仍在。

## 1. 复核（4 个分支逐个成立）

| 配置情况 | 校验结果 | 消费者实际行为 |
|---|---|---|
| 整配置为 `[]` | `project config is not a JSON object` | Check 仍按 90 天 pass |
| `debug_repeat_threshold: "bad"` | 非法正整数 | 静默取 3 |
| `spec_output_codepoints: 0` | 非法正整数 | spec 读取 `WF_OK`，按 0 预算并记完整读取 |
| `tdd_default: "false"` | 非法布尔 | 批准 `WF_OK`，`bool("false")` 变成 `True`（静默取反） |

根因是**取值靠各消费者手写 `isinstance` 兜底**：兜底不等于阻断，且 `bool()` 会把非空字符串转成 `True`。

## 2. 处置（R57）

- `config.value_of(config, problems, key)` 作为唯一的取值入口：返回 `(值, None)` 或 `(None, problem)`——
  - 键缺失且配置可用 → 发行缺省（**不阻断**）；
  - 键存在但非法、或配置整体不可读 → `(None, problem)`（调用方必须阻断）。
- 回扫全部消费者并改用该入口：`check._spec_coverage`（周期）、`cli.Ctx.debug_threshold`、`cli.cmd_spec`（输出预算）、`tasks.cmd_task_approve`（`tdd_default`，非法即 `WF_SEMANTIC_DECISION` 并提示可显式传 `inputs.tdd`，不再 `bool()` 静默取反）。
- 周期不可用时仍按缺省值算出候选，但 `period_problems` 让 Check 阻断（不至于连候选都列不出）。

## 3. 边界

- 不新增原因码：预算/配置不可用走 `WF_CAPABILITY_UNAVAILABLE`，TDD 默认非法走 `WF_SEMANTIC_DECISION`。
- 不整体阻断项目：只有依赖该键的判断被阻断，无关键仍局部。
- 不改缺省值、不改键名、不加新键。

## 4. 对收口状态的影响

属「校验与执行脱节」的系统性残留，收口前必修。落地后需重跑 Check 相关（CP1/CP3/CP5、R13/R18/R21/R34/R43/R56）与三夹具全流程、F0。
