# dsh-trellis 安装态端到端对标验证与 inline 模式审查

## Goal

在真实 DSH 进程中验证**当前已安装**的 `dsh-trellis`（`~/.dsh/profiles/web` 以 `link:`
指向本仓库 `dsh-plugins/dsh-trellis`，版本 0.3.9）能否达到 Codex 使用 Trellis 的同等
效果、是否补足 DSH 平台使用 Trellis 的不足；专项判定 `dsh.dispatch_mode: inline`
是否真的实现、实现是否正确、边界是否完整。产出**问题清单 + 证据 + 修复方案**，等待
用户逐项确认后才进入修复。

## Background（已核实事实）

- 安装链（E1，`profiles/web/package.json`）：`dsh-trellis` →
  `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis`，包版本 0.3.9。
- 运行时版本：DSH `0.2.1-rc.2`、Trellis CLI `0.7.0-beta.4`、Codex CLI `0.163.0`、Node v24.20.0。
- Codex 侧真实接线（E1，本仓库 `.codex/`）：`hooks.json` 的 SessionStart /
  UserPromptSubmit / SubagentStart / PreToolUse 四个钩子，`.codex/agents/trellis-*.toml`，
  项目 `AGENTS.md` 的 `TRELLIS` 块，`.agents/skills/`。
- 插件 inline 实现（E1，`lib/workflow.js:414-437`）：只读 `.trellis/config.yaml`
  的 `dsh.dispatch_mode`；仅当状态为 `planning` / `in_progress` 且 workflow 文件存在
  `<status>-inline` 块时切块，并追加 `<dsh-mode>` 横幅；`auto` 为默认，未知值回落 `auto`。
- 本会话已实际收到 `Trellis workflow state: planning-inline` + `<dsh-mode>`（E1，本轮
  system-reminder），说明本仓库内 inline 至少对 `planning` 生效。
- 上一轮审计（`archive/2026-10/10-21-dsh-trellis-parity-audit`）确认过 0.3.7 的问题并修复到
  0.3.8/0.3.9；本轮不复用其结论，仅复用其**方法**，结论全部重新取证。

## Requirements

- **R1 证据等级**：只用真实执行（真实文件、真实进程、真实注入消息）下结论（E1）；
  静态推断标 E2，文档/单测声明标 E3，且不得单独作为结论依据。
- **R2 单一临时项目**：在 `/tmp` 新建一个 Trellis 项目（`trellis init --dsh --codex`），
  所有端到端场景在该项目内执行；不新建第二个。
- **R3 环境隔离**：使用独立 `DSH_HOME` + 独立 profile 装载同一份插件源码，不修改
  `~/.dsh/profiles/web`、`~/.dsh/profiles/headless`，不污染用户会话。
- **R4 抓取模型真实输入**：本地 mock OpenAI-compatible LLM 记录完整 `messages`/`tools`，
  不以模型自述替代。
- **R5 Codex 基线**：以真实 `.codex/hooks/*.py` 接收真实形态 payload 的输出为基线；
  条件允许时补充一次真实 `codex exec` 观察行为；差异必须逐条列出。
- **R6 能力矩阵**：覆盖 bootstrap、workflow-state 面包屑（全部状态 + 自定义状态）、
  workflow 变体选择、skip 关键字、spec 路径注入、子代理上下文推送、派发守卫、
  `trellis_wait`、会话身份、命令面、doctor、冲突检测、版本监控路由。
- **R7 inline 专项**：明确回答“是否实现 / 实现范围 / 是否正确 / 边界缺陷”，覆盖
  状态选择、块缺失回退、横幅内容、作用域（子代理/非 planning 状态）、与派发守卫和
  子代理协议的关系、与 Trellis 自有 `codex-inline` 契约的一致性。
- **R8 只取证不修复**：本轮不修改 `dsh-plugins/dsh-trellis` 源码、不改安装链；
  交付问题清单与修复方案，等用户确认。
- **R9 边界**：临时文件只落在 `/tmp` 与本任务目录；凭据不外泄到命令、日志与输出。

## Acceptance Criteria

- [x] AC1 每个结论附 E1/E2/E3 标记与可复现命令或文件路径。
- [x] AC2 能力矩阵逐项给出「通过 / 不通过 / 平台差异 / 无法验证」判定。
- [x] AC3 inline 专项给出四问结论（是否实现、范围、正确性、边界），并有真实会话注入取证。
- [x] AC4 问题清单逐条含：现象、最小复现、根因 `file:line`、影响面、严重级、建议修复与风险。
- [x] AC5 状态正文与 Codex hook 逐字/字节对照表。
- [x] AC6 明确回答“是否补足 DSH 使用 Trellis 的不足”，给出正面结论或缺口清单。
- [x] AC7 用户确认前 `dsh-plugins/` 无改动；`git status` 仅新增本任务目录及既有未提交文件。

## Out of Scope

- 任何插件源码修复或安装链变更（须用户确认后另行执行）。
- Web 设置页的浏览器级 UI 自动化（仅在后端路由成本低时验证）。
- 推送到上游仓库或 npm 发布。

## Open Questions

（无阻塞项。用户已明确：本轮只验证并出问题清单，修复需另行确认。）

## Scope Addendum（2026-10-21，用户追加授权）

审计交付后用户逐项确认并追加了修复与功能要求，原 R8/AC7 的“只取证、不改插件”仅
约束审计阶段：

1. P2/P3 一并处理（inline 边界、inline 派发门禁、横幅覆盖、文档）；bootstrap 每会话一次
   按用户要求保持不变。
2. 启用插件时自动向 Trellis 项目 `.trellis/config.yaml` 补 `dsh.dispatch_mode: inline`
   （只补缺失键，显式值优先，注释/换行保留，原子写入 + 锁内重读）。
3. 插件版本重置为 0.1.0；版本策略写入
   `.trellis/spec/platforms/dsh-workflow-behavior.md`（普通修改只递增 patch）。
4. 增加 pre-push 钩子：推送涉及插件的提交前重建 `lib/client.js`，未提交则中止推送。

这些追加项已纳入 `report.md` §8–§11 与 `docs/validation-0.1.0-local.md`。
