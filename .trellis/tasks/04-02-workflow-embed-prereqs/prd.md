# 修正新项目工作流的嵌入前提与低摩擦接入说明

## Goal

修正 `docs/workflows/新项目开发工作流/` 的说明与安装行为，明确目标项目的前置条件，并降低“把该工作流嵌入到目标项目”的理解成本。

## What I already know

- 当前目标文档已在多处明确：这套 workflow 是建立在 `trellis init` 之后的“嵌入 + 增强”，不是替代 Trellis 基线。
- `工作流总纲.md`、`命令映射.md`、`多CLI通用新项目完整流程演练.md`、`工作流全局流转说明（通俗版）.md`、`commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md` 已经存在一批前置条件说明。
- 安装脚本 `docs/workflows/新项目开发工作流/commands/install-workflow.py` 已实际校验：
  - 目标项目存在 `.git`
  - 目标项目存在 `.trellis/`
  - 目标项目存在 `.trellis/.version`
- `install-workflow.py --help` 的帮助文本已经写明：安装对象是 “Trellis Git 项目”。
- `workflow-e2e-issues.md` 中与本任务最相关的不是所有 issue，而是：
  - `ISSUE-001` / `ISSUE-010` / `ISSUE-011`：暴露“Git + trellis init` 前提未满足时，黑盒测试会把环境缺口误读为 workflow 缺陷”
  - `ISSUE-005` / `ISSUE-006`：暴露“首次嵌入后还需补哪些最低资产”这条低摩擦初始化路径解释不够集中
- 目前更像是“文档层口径分散、阅读成本高、部分读者会误解成给 AI CLI 一份目录即可直接使用”，不完全是实现缺失。

## Assumptions (temporary)

- 本轮优先修复“文档口径与安装说明不够集中”的问题，而不是大改 workflow 架构。
- 除非后续发现明确证据，否则暂不把 `ISSUE-002`、`ISSUE-007` 这类设计/技术栈约束问题纳入本任务范围。
- 安装脚本本身对前置条件的强校验已基本满足任务目标，若要改动，应该只做帮助文本或错误提示的补强。

## Open Questions

- 本轮要把“低摩擦接入”定义为哪一种口径：
  - A. 严格强调“必须先安装到目标项目后才算接入”
  - B. 同时保留“把 workflow 目录提供给 AI CLI 可先完成理解/预览，但不算正式安装”的双层表述
- `workflow-e2e-issues.md` 中哪些问题应被归类为“文档缺陷”，哪些应明确保留为“测试环境缺口”而不修到主文档里

## Scope Candidate

- 收敛新项目 workflow 文档里的“嵌入前提”“安装时序”“多 CLI 入口差异”“首次嵌入后的最低补齐动作”
- 明确区分：
  - 理解 / 预览 workflow
  - 正式嵌入并可运行
- 只在必要时补强安装脚本帮助文案或失败提示，不默认扩大到脚本流程重构

## Requirements

- 明确目标项目若要使用该 workflow，必须同时满足：
  - 本身是一个 Git 项目
  - 已执行 `trellis init`
- 统一说明这套 workflow 是在 Trellis 基线上做“嵌入 + 增强”，不是替代 Trellis 基线
- 明确低摩擦嵌入口径：
  - 将该 workflow 目录提供给对应 AI CLI 即可完成理解与接入
  - 平台差异只体现在原生入口协议和配置挂载方式，不要求用户重新理解整套主链
- 若安装脚本当前未强制校验 Git 仓库前提，则补齐脚本行为与帮助文本

## Acceptance Criteria

- [ ] `工作流总纲.md`、主入口 walkthrough、命令映射和必要的平台 README 对 Git + `trellis init` 前置条件表述一致
- [ ] 文档中明确“工作流目录可直接作为 AI CLI 的工作流入口 / 挂载源”的嵌入口径
- [ ] 安装脚本对非 Git 仓库给出明确失败提示
- [ ] 相关验证通过，至少覆盖脚本帮助或测试命令

## Technical Notes

- 优先保持现有“多 CLI 同装，但入口协议不同”的结构，不重写整体文档架构
- 只补最小必要改动，避免把平台私有细节重新堆回主文档
- 证据来源：
  - `workflow-e2e-issues.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  - `docs/workflows/新项目开发工作流/工作流全局流转说明（通俗版）.md`
  - `docs/workflows/新项目开发工作流/commands/claude/README.md`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - `docs/workflows/新项目开发工作流/commands/codex/README.md`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
