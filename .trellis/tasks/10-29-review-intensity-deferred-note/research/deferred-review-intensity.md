# 待决分析：任务级审查强度分流（下一任务的输入）

> 状态：**未采纳，留待下一任务裁决**。本文件只保存本轮分析，不构成规范。
> 相关登记：`docs/workflows/workflow-implementation.md` §9.6 G7。

## 1. 用户原始要求

> 在具体的单个任务中，如果判断是简单任务就按照 Trellis 的机制执行即可；如果是复杂的任务就在对应 check 阶段引入多方 agent 辅助审查。

## 2. 与既有条款的冲突（下一任务不得放宽的边界）

| # | 冲突 | 依据 |
|---|---|---|
| 1 | "复杂/简单"是自述判断，写成门即不可验证 | 方案 §3.6（门禁只看状态不看触发者）；设计稿 §1.3（不防对抗，只防意外） |
| 2 | 目标项目侧依赖多方 agent ⇒ 依赖平台子代理能力 | 设计稿不变量 9；constraints「required capabilities never depend on hooks」 |
| 3 | 审查结论若成为完成判据 ⇒ 等于恢复证据链 | 设计稿不变量 6；方案 §6.2；C1 裁决 |
| 4 | 与"本模块不派 Trellis 子代理"的立论冲突 | 方案 §3.5 / constraints：`wf start` 固定 `--allow-empty-context` 的理由是 manifests 天然为空 |
| 5 | 若在目标项目可执行 ⇒ 需第三个 skill 面 | C11 裁决：skill 面固定 `wf` / `wf-repair` |

## 3. 方案 A：`multi-cli-review` + `-action`（文件契约）

- reviewer 只产出一份结构化报告文件，天然不碰源码；报告随任务归档、可离线复现、可被 action 侧汇总。
- 支持任意可运行的 CLI（含 zcode / pi / dsh）。
- 缺点：一次性，无法追问；编排靠人/主会话逐条发命令。

## 4. 方案 B：`trellis channel` 编排（本地实测，2026-10-29，0.7.0-beta.4）

| 事实 | 证据 |
|---|---|
| 官方有并行 reviewer 模式 | `references/workflows.md` Pattern C：一个 channel + `--agent check`（claude）+ `--provider codex --as check-cx` + `wait --kind done --from a,b --all` |
| worker provider **仅 claude / codex** | `--provider <claude\|codex>` 经 adapter registry 校验；zcode/pi/dsh 不能当 worker |
| 一次性形态 | `channel run`：建临时 channel → spawn → send → wait done → 打印最终答案 → 清理；失败保留 channel、exit 1 |
| 资源护栏 | `--timeout` / `--idle-timeout`（默认 5m）/ `--max-live-workers`（默认 6）；配置有 OOM guard 段 |
| 输出形态 | 事件/消息流，操作台视图会截断，需 `--raw`；日志在 `~/.trellis/channels/`（仓外） |
| 官方边界 | channel skill 明写 **Not For**: one static review where a markdown file and prompt are enough |
| 本机可用性 | claude/codex/zcode/pi/dsh 五个 CLI 均在 PATH；当前无 channel |

**结论**：channel 强在编排与交互（并行、`--all`、`interrupt` 追问、`spawned` 事件审计），弱在报告契约、仓外留痕、provider 覆盖（2/5）与写风险（worker 有 cwd 与文件访问）。

## 5. 建议形态（待下一任务裁决）

编排用 channel、报告仍用 multi-cli-review 的 schema：

```
触发：可观察信号（不是主观复杂度）
第 1 档 自检：trellis-check + 项目校验
第 2 档 单方复核：channel run（另一家 provider）或 code-review-expert
第 3 档 多方审查：channel Pattern C 编排 claude + codex；报告按 multi-cli-review schema 落成文件；用 multi-cli-review-action 汇总
```

四条纪律（无论最终选哪种编排）：

1. **只读**：审查前后 `git status --porcelain` 必须为空，否则结果作废；
2. **降级**：可用 provider < 2 时降为"单方复核 + 人判"，不得声称"多方"；
3. **非门禁**：审查产物不改任务状态、不写账本、不构成完成判据；
4. **失败≠通过**：timeout / killed / error / 报告缺失，均视为未升档完成。

## 6. 待裁决清单（下一任务）

| ID | 问题 |
|---|---|
| R-1 | 是否用"可观察信号"替代"复杂/简单"判断，信号集合如何定（契约面条数 / 账本 schema / 探针路径 / diff 规模 / 跨平台） |
| R-2 | 审查强度是否允许成为门（建议不允许） |
| R-3 | reviewer 是否强制"不同 CLI/模型"（建议强制） |
| R-4 | 第 3 档用 channel 编排 + 报告仍按 multi-cli-review schema（建议采纳） |
| R-5 | provider < 2 时的降级规则 |
| R-6 | "自动"的范围：仅主会话按信号发起，不含流程自行触发或自行判通过 |
| R-7 | 落点：constraints（作者侧硬约束）+ 方案 §8 引用；不进变体、不进设计稿 |
