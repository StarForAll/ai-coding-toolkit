# 验证 dsh-trellis 插件与 codex 使用 trellis 的效果对等性

## Goal

对已安装的 `dsh-trellis`（源码对应本仓库 `dsh-plugins/dsh-trellis`）做一次独立、可复现的多角度实测：它是否达到 Codex 使用 Trellis 的同等效果、是否补足 DSH 直接使用 Trellis 的不足，以及还存在哪些缺漏。先交付问题清单与执行方案；**用户确认之前不修改任何插件代码**。

## Background

- 本机 DSH `0.2.1-rc.2`、Trellis `0.7.0-beta.4`、Codex CLI `0.163.0`、Node `v24.20.0`。
- 已安装插件：`~/.dsh/profiles/web/node_modules/dsh-trellis` = `0.1.5`；`~/.dsh/profiles/trellis-headless/node_modules/dsh-trellis` = `0.1.4`。
- 本仓库源码 `dsh-plugins/dsh-trellis` 为 `0.1.5`；与 web 安装副本仅有两个文件的注释差异（`session-composer.js`、`workflow.js`），运行逻辑一致。
- Trellis 0.7.0-beta.4 原生支持 DSH 的 class-2 pull 模式（`.agents/skills` + `.dsh/skills` + `.dsh/DSH.md`），插件是可选伴侣。
- 已有一个历史任务 `10-22-dsh-trellis-capability-verify-0-1-4` 的结论；本轮不复用其结论，只把其中的证据点作为待复核清单。

## Requirements

- **R1 机制对照**：逐项对照 Codex 与 DSH 在 Trellis 中的接入面：会话/每轮上下文注入、任务状态、路径级 spec 注入、子代理上下文、角色定义、命令面、会话身份、项目级配置、升级/安装形态。
- **R2 真实运行验证**：在 `/tmp` 临时 Trellis 项目中使用真实 DSH 会话（真实 LLM、真实工具调用）验证；Codex 侧同样用真实 `codex exec`/hook 实际执行，不能只读文档。
- **R3 双机制判断**：结合 DSH 宿主机制（事件、工具、投影、子代理、命令、shellEnv）与 Trellis 0.7.0-beta.4 的脚本/模板/hook 契约判断，不把 Codex 行为当作唯一标准。
- **R4 不足清单**：列出可复现的缺漏/行为差异，附严重级别、证据、影响与可选修复方案；区分“插件缺陷”“上游 Trellis 缺陷”“宿主限制/设计选择”。
- **R5 单任务约束**：只创建本任务；不并行创建其他 Trellis 任务。
- **R6 修复闸门**：在用户确认问题清单与执行方案之前，不做任何插件代码修改；临时项目与证据目录不受此限。

## Non-Goals

- 本阶段不实现修复、不提交、不推送、不改写历史。
- 不验证与 Trellis 无关的插件、GUI 样式或网络服务。
- 不绕过 DSH Web 的本地鉴权去“验证 UI”（若无法在不泄露凭据的前提下进入，记录为限制）。
- 不把模拟/单测结论冒充真实会话结论。

## Acceptance Criteria

- [ ] 一份基于 S1（真实会话）/S2（真实模块或 hook 执行）/S3（源码契约）/S4（单测）分级证据的验证报告。
- [ ] Codex 与 DSH 的逐项对照矩阵，明确“达到同等效果 / DSH 增强 / DSH 不及 / 双方共同缺陷 / 宿主限制”。
- [ ] 至少覆盖：breadcrumb、bootstrap、spec deny-once/ticket、子代理 push、inline/auto 模式、身份解析、命令面、升级与安装状态。
- [ ] 每个问题有唯一编号、严重级别、复现步骤、证据位置、影响面与候选修复方案。
- [ ] 给出待用户选择的执行方案（含推荐项与取舍），并明确“未确认前不修复”。
- [ ] 不修改本仓库中用户已有的未提交改动；不泄露任何凭据值。

## Decisions (2026-10-23, user-confirmed)

- **Mode target: B** — 默认 `inline`，但不再自动改写被跟踪的 `.trellis/config.yaml`；补强 inline 契约（banner/文档），因为上游没有 DSH-inline phase 变体。
- **Fix scope**：C1 角色误判、C2 子目录 spec、C3 模式/config、C6 trellis-headless 更新、C7 文档补充。
- **Not in scope**：U1（Codex-in-DSH 上游身份）、U2（上游 Trellis 模板/DSH.md）按“上游只读”政策忽略，不作为问题或修复项。
- **Config write**：不写任何 tracked config。
- **Role detection**：专用 Role/首行标记 + description 严格匹配，忽略普通叙述与路径提及。
- **Spec path**：按 agent cwd 解析，同时尝试根相对路径并取并集。
- **Upstream policy**：Trellis 官方上游（如 `~/projects/other/Trellis`）是**只读参考**，当前无修改权限；插件/工作流的设计与修复只在本仓库资产内完成。上游行为差异（U1 identity 优先级、U2 DSH workflow/DSH.md 过期）只作为观察/边界，不进入问题清单、修复计划或待办，不提上游补丁。
