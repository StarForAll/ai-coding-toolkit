# dsh-trellis 0.1.3 Codex parity 全量复核与缺口验证

## Goal

以真实调用、多角度取证验证：当前已安装的 dsh-trellis 0.1.3 插件在 dsh 0.2.1-rc.2 +
Trellis CLI 0.7.0-beta.4 环境下，是否达到 Codex 使用 Trellis 的同等效果；是否（尽可能）
补足 DSH 原生使用 Trellis 的不足；是否仍存在其他缺漏。

**硬约束**：
- 只开这一个 Trellis 任务，不为子项另建任务。
- 所有结论必须来自实际调用与可复核证据（真实 dsh 会话事件日志、真实代码执行、源码比对），
  不接受插件 README / 文档自述作为通过依据（"不能依靠一面之词"）。
- 验证发现的问题与修复方案全部先交付给用户确认；**用户确认之后才允许动手修复**。
  若未发现问题，则给出具体验证结果而非模糊结论。
- 验证场所在 /tmp 下的临时项目，不污染本仓库以外的内容；本仓库的改动（若有）限于
  dsh-plugins/dsh-trellis/ 及其文档/spec 记录。

## 背景

- 2026-10-21 任务 `10-21-dsh-trellis-live-parity-verification` 对 0.1.1 做过 C1–C10
  全链路验证，结论为三项主链路对齐 Codex，并留下 P1-1（守卫拒绝文案教模型绕过）、
  P2-1（角色识别只解析 prompt）等问题。
- 2026-10-22 任务 `10-22-dsh-trellis-defect-fix` 发布 0.1.3，修复了上述问题（角色识别
  支持 description/descriptor label、push 文案去矛盾、守卫表述降级为提示性闸门、
  README 清除上游 fork 内容）。**0.1.3 修复后尚未做过同等强度的真实会话复核**。
- 基准 A（Codex parity）：本仓库 `.codex/` 部署契约 + Trellis 上游（~/projects/other/Trellis）
  Codex 平台 hooks/agents 机制。
- 基准 B（补足 DSH 不足）：无插件的 plain dsh 在同项目下的行为对比。
- 验证须同时结合 dsh 宿主机制（插件事件模型、sessionProjections、subagent lifecycle）
  与 Trellis 源码机制（init 产物、task.py / active_task.py 契约、workflow.md 派发协议），
  不能只看 Codex 侧。

## Requirements

### R1 0.1.3 修复项真实回归（针对 defect-fix 的 R1–R3）
- 真实 dsh 会话中派发 `description` 以角色名开头（prompt 无角色）的子代理：
  子代理首步收到 `subagent-context` push（角色契约 + 任务上下文）；inline 模式下
  description-only 的 implement/check 派发被守卫拒绝。
- 话题型 description（如"研究 trellis-agent-implement 的 README"）保持 generic：
  不误推、不误拦。
- push 文本：`was prepared by dsh-trellis` 恰好一次；skill 已推送时含"不要再次加载"
  权威说明；skill 缺失时退化为路径提示且无矛盾表述。

### R2 主链路 Codex parity 复核（0.1.3 上的全量重跑）
沿用并刷新 C1–C10：面包屑状态映射与去重、会话身份隔离（DSH_TRELLIS_CONTEXT_ID）、
子代理 + trellis_wait、子代理上下文 push、/trellis-* 命令面、dispatch_mode 引导、
spec 注入（deny-once/ticket/持久化/compaction 重置）、bootstrap 一次性、非 Trellis
项目零干扰、init 产物与插件读取路径双向一致。
新增对照点：Codex 侧每条链路以 .codex/ 实际部署 + Trellis 源码为准逐条比对，记录
"对齐 / 有意差异（README 已声明）/ 未声明差异（疑似缺陷）"三档。

### R3 补足 DSH 原生不足的程度评估
- 无插件对照（plain headless profile，同项目）：列出 DSH 裸用 Trellis 缺失的能力清单。
- 装插件后逐项确认已补足；**仍未能补足或只能部分补足的项单独列出**（例如 DSH 事件
  形状导致的 read 不能先阻断、bootstrap 频率差异等），并评估是否还有可改进空间。
- 超出 Codex parity 的增强（doctor、守卫、冲突检测、版本监控）验证其实际可用性。

### R4 其他缺漏扫描（此前未覆盖的角度）
- 多会话/多项目并发：同一 profile 多项目、多会话的 spec-inject 分片与 session 指针隔离。
- 异常路径：task.json 损坏、config.yaml 损坏/并发写、.trellis 中途被删、磁盘只读等
  fail-closed 行为。
- 长会话行为：compaction 后 bootstrap/spec 重注入、会话 resume（--session-id）。
- research 角色链路（此前重点在 implement/check）。
- 插件冲突检测与版本监控的真实触发（如可安全模拟）。
- 与本仓库现行 workflow.md 派发协议（Active task 前奏、trellis_wait 或
  run_in_background:false 二选一）的一致性。
- dsh-trellis 与 Trellis 0.7.0-beta.4 的契约对齐（task.py current --json、
  DSH_TRELLIS_CONTEXT_ID 解析优先级）。

### R5 交付与修复闸门
- 产出 verification-report.md：每项结论附证据等级（真实会话 / 真实代码执行 /
  源码比对 / 单元测试）与取证位置（session 事件日志路径、命令、diff）。
- 产出问题清单：每个问题给出定性（缺陷 / 设计权衡 / 上游限制）、影响面、
  可选修复方案与推荐项。
- **修复闸门**：问题清单与方案经用户逐条确认后，才进入修复；用户拒绝的项不修。
- 未发现问题时，报告须给出逐项通过的具体证据，不接受"看起来没问题"。

## Acceptance Criteria

- [ ] R1 三项修复在真实 dsh 会话（headless profile + /tmp 临时项目）中复测通过，
      事件日志可复核。
- [ ] R2 C1–C10 全量重跑完成，每项有结论与证据等级；与 Codex 的每处差异归入三档之一。
- [ ] R3 给出"无插件缺失清单 → 插件补足情况 → 残余不足"三段式结论。
- [ ] R4 各角度有实测或明确的"无法安全实测"说明（说明阻塞原因与替代证据）。
- [ ] R5 verification-report.md + 问题清单交付，且未在用户确认前修改任何插件代码。
- [ ] 本仓库既有未提交工作（docs/capability-inventory.md、dsh-plugins/plugin-create.md）
      不被破坏；任务 diff 仅限本任务范围。
