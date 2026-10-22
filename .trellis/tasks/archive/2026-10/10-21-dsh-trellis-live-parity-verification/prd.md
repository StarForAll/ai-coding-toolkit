# PRD：dsh-trellis 0.1.1 全链路实际调用验证

## 背景

- 上游 `dsh-trellis` 0.1.12 在本仓库被本地化改造为 `0.1.1`（版本号 2026-10-21 重置），
  声称对齐了 Codex 使用 Trellis 的三条主链路（无任务 bootstrap、路径级 spec 注入、
  子代理上下文 push），并自带大量单元测试（约 242 个）与多轮 validation 文档。
- 插件已安装在 dsh `web` profile（dsh 版本 0.2.1-rc.2），`headless` profile 未安装。
- 此前已有任务 `10-21-dsh-trellis-full-parity-audit`（已归档）做过一轮审计；本任务
  不复用其结论，独立重新验证。
- 用户要求：**不能依靠一面之词**（即不能只信 README / LOCAL_CHANGES / 单元测试 /
  既有 validation 文档的自述），需要**实际全方位多角度调用验证，实事求是**。

## 目标（用户需求原文拆解）

1. 验证 dsh 已安装的 `dsh-trellis` 插件是否能达到 **Codex 使用 Trellis 一样的效果**。
2. 验证它是否**补足了 dsh 在使用 Trellis 上的不足**（需尽可能弥补）。
3. 排查**其他缺漏或不足**。
4. **约束**：问题修复必须在用户确认完所有问题和执行方案之后才能进行 —— 本任务
   范围 = 发现与报告问题 + 提出修复方案，**不执行修复**；若没有发现问题则说明具体
   验证结果。
5. 验证方式：在 `/tmp` 新建临时项目实际调用；**必须结合当前 dsh 与 Trellis
   （~/projects/other/Trellis）的机制判断**，不能仅依据 Codex 侧的使用推断。

## 验证范围（capability matrix）

对照 README/LOCAL_CHANGES 声称的能力，逐项设计实际调用证据：

| # | 能力 | 验证方式 |
|---|------|---------|
| C1 | 每轮 workflow-state 面包屑注入（状态映射、去重、压缩重注入、`no-trellis` 跳过） | headless `--json` 跑多轮会话，检查注入消息事件；变更任务状态后观察新面包屑 |
| C2 | 隔离会话上下文身份（DSH_TRELLIS_CONTEXT_ID → task.py start/create/current 会话级指针） | 临时项目中两个并行会话各自 create/start 任务，检查指针互不串扰 |
| C3 | 原生子代理同步（trellis_wait 事件驱动、fail-closed 结论映射） | 实际派发 trellis-agent 子代理 + trellis_wait；构造失败子代理验证不误报通过 |
| C4 | 子代理首步上下文 push（角色契约 + curated task context + Active task 回退） | 派发子代理，检查其首步收到的注入内容是否含 SKILL.md 正文与任务上下文 |
| C5 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 命令 | 实际调用，校验输出与旧版 Trellis 兼容回退 |
| C6 | 项目级 `dsh.dispatch_mode: inline` 自动引导（只补缺、不覆盖、保注释、原子写） | 各 config 形态（缺失/显式 auto/带注释）下挂载项目，diff 检查 |
| C7 | spec 注入 deny-once / ticket / 持久化 / 压缩重置（tools: edit/write/read） | headless 会话中实际触发编辑，观察 pre-execute deny 与 post-execute ticket |
| C8 | bootstrap 每会话一次、与面包屑解耦、子代理不注入 | 新会话首轮 no_task 观察 bootstrap；后续轮确认不重复；子代理确认无 bootstrap |
| C9 | 非 Trellis 项目静默、未初始化项目的命令行为 | 在无 .trellis 目录跑会话与命令 |
| C10 | Trellis CLI 侧：`trellis init --dsh` 产物与插件 expectations 的双向一致性 | 用 ~/projects/other/Trellis 的 CLI 在 /tmp 项目 init，检查 `.dsh/skills/trellis-agent-*`、config 键、与插件读取逻辑互洽 |

## 判定基准（何为"与 Codex 一样效果"）

- 基准 A（对齐）：README 中"Codex 的实际接线 vs 本插件"表所列三条主链路，
  且差异仅为 README 已声明的 DSH 事件形状差异（bootstrap 频率、read 不能 deny 等）。
- 基准 B（补足 DSH 不足）：不装插件时 dsh 使用 Trellis 缺什么（无面包屑、无
  spec 注入、无子代理 push、无会话身份、无命令面），装插件后是否补上。
- 基准 C（机制正确性）：插件行为与 Trellis 本体（~/projects/other/Trellis 的
  hooks/脚本/config 契约）一致，例如 `task.py current --json` 退出码契约、
  `.trellis/.runtime/spec-inject/` 状态分片、config.yaml 键名。
- 发现的问题分级：P0 功能性缺陷（行为与声称不符且影响使用）/ P1 声称与实现
  不符（文档性偏差）/ P2 已知差异的边界确认 / P3 建议改进。

## 验收标准

1. `verification-report.md`（任务目录内）逐项给出 C1–C10 的证据（命令、输出摘录、
   判定），不允许只引用插件自述文档作为通过证据；自述只能作为"声称"清单来源。
2. 每一项验证结论只有三种：通过（附实际证据）/ 不通过（附实际证据与复现路径）/
   无法验证（说明被什么阻塞，如需要 GUI 交互）。
3. 问题清单按 P0–P3 分级，每个问题附修复方案（但**不执行修复**）。
4. 最终答复用户：逐项验证结果 + 问题清单 + 修复方案，等待用户确认后才进入修复
   （修复是否属于本任务范围由用户届时决定）。
5. 临时项目在 /tmp 下，验证结束保留路径供用户复查（用户确认后可清理）。

## 非目标（Out of Scope）

- 不修复任何发现的问题（用户确认方案前）。
- 不重新审计 Web 设置表单的 UI 交互细节（仅验证注册与关键路由可用性）。
- 不对比未安装插件的其他宿主（Codex 本身）的运行时行为做侵入式验证；
  Codex 侧行为以本仓库 `.codex/` 已部署的 hooks 契约与 Trellis 上游源码为准。
