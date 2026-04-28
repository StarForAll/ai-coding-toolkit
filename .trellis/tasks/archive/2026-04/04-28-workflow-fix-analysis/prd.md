# brainstorm: 修复新项目开发工作流

## Goal

基于当前仓库中的 `docs/workflows/新项目开发工作流` 与 `/tmp` 下的干净 Trellis 初始化样本，判断用户提出的优化点是否真实存在，分析其影响范围，并给出遵循 Trellis 核心前提且原生适配 Claude Code / Codex / OpenCode 的修改方案；本轮只做分析，不执行 workflow 源文件修改。

## What I already know

* 分析范围限定在 `docs/workflows/新项目开发工作流/`
* 需要先在 `/tmp` 建临时项目，执行 `trellis init`，再嵌入当前 workflow 做实际验证
* 用户提出的 A 点聚焦 design 阶段 UI 设计链路，要求固定顺序为：`uiprompt.site` 风格词 -> 当前 CLI 整理 Prompt -> `stitch.withgoogle.com` 生成初稿 -> Figma 做现代视觉风格参考
* 用户提出的 B 点聚焦 `ownership_proof_required` 默认值与 `source-watermark-plan.md`
* 当前仓库的 `commands/design.md`、`工作流总纲.md`、`多CLI通用新项目完整流程演练.md` 已存在 `uiprompt.site -> STITCH-PROMPT -> Stitch` 主链，以及 Codex 不能作为 UI 原型主执行器的规则
* 当前仓库的 feasibility / design / plan / delivery 文档、校验脚本、演练文档中已存在 `ownership_proof_required`、`source_watermark_*`、`source-watermark-plan.md` 的规则链

## Assumptions (temporary)

* A 点更可能是“流程闭环不完整或约束不够严”，而不是“完全没有该流程”
* B 点更可能是“默认值策略、触发条件或文档表达存在歧义”，而不是完全缺少水印链路
* 若后续确认需要修改，影响面至少会覆盖命令文档、命令映射、演练文档、平台 README、helper 校验脚本和安装/升级契约说明

## Open Questions

* `/tmp` 干净 Trellis 项目在真实 `init + install-workflow` 后，Codex / Claude / OpenCode 的入口与文档实际落盘是否与当前源码描述一致
* `ownership_proof_required` 在当前 workflow 中到底是“默认 yes”还是“按 feasibility 明确填写，不预设默认值”
* design 阶段是否已经对 Figma 的角色做了明确约束，还是只覆盖到 Stitch 为止
* `STITCH-PROMPT.md` 是否需要在当前 workflow 中改名、别名化，还是只需明确“`DESIGN.md` 即 `STITCH-PROMPT.md`”的产物语义

## Requirements (evolving)

* 基于源码与 `/tmp` 实测给出结论，不凭记忆判断
* 明确区分：真实已存在的问题、用户反馈但当前仓库已覆盖的点、以及潜在可优化但并非缺陷的点
* 若提出修改方案，必须说明会影响哪些文档/脚本/测试，以及为什么
* 不在用户确认前修改 `docs/workflows/新项目开发工作流/` 中的任何源文件
* Stitch 执行 prompt 使用英文；生成的 UI 界面默认使用中文
* `ownership_proof_required` 继续保留为显式字段，但常规默认填写 `yes`，不区分外包或非外包项目

## Acceptance Criteria (evolving)

* [ ] 完成当前 workflow 中 design / ownership-proof 相关规则分布梳理
* [ ] 完成 `/tmp` 干净 Trellis 项目初始化与 workflow 嵌入验证
* [ ] 给出 A、B 两类优化点的“存在 / 不存在 / 部分存在”判断及证据
* [ ] 给出一组与 Trellis 核心及三 CLI 原生适配相兼容的修改方案
* [ ] 明确列出本轮不做的修改动作，等待用户确认

## Definition of Done (team quality bar)

* 结论可追溯到具体源码、脚本或 `/tmp` 实测结果
* 风险、未证实点、后续修改影响面已明确列出
* 不声称已修复任何问题

## Out of Scope (explicit)

* 本轮不直接修改 workflow 文档、脚本、测试或平台适配文件
* 本轮不生成最终设计稿、Figma 文件或 Stitch 页面原型
* 本轮不替目标项目定义具体水印策略内容，只判断 workflow 契约是否合理

## Technical Notes

* 已读约束：`.trellis/spec/scripts/workflow-command-doc-contracts.md`
* 已读约束：`.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
* 已读思考指南：`.trellis/spec/guides/cross-layer-thinking-guide.md`
* 已读思考指南：`.trellis/spec/guides/code-reuse-thinking-guide.md`
* 已定位关键文件：`commands/design.md`、`commands/feasibility.md`、`commands/plan.md`、`工作流总纲.md`、`命令映射.md`、`CLI原生适配边界矩阵.md`、`commands/*/README.md`

## Research Notes

### `/tmp` 实测基线

* 已在 `/tmp/trellis-workflow-analysis` 执行 `git init -b main`
* 已执行 `trellis init --claude --opencode --codex -y -u xzc`
* 已按 workflow 要求配置 `origin` 的 2 个 push URL
* 已执行 workflow 安装 dry-run 与正式安装
* 实测结论：
  * `trellis init` 后确实同时存在 `.agents/skills/` 与 `.codex/skills/parallel`
  * 正式安装时，当前执行环境若是 Codex，会先阻止首次嵌入，必须显式设置 `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1`
  * 安装完成后，shared workflow skills 落在 `.agents/skills/`，`.codex/skills/parallel` 被移除并备份
  * 安装记录 `.trellis/workflow-installed.json` 已写入，`profile = outsourcing`
  * 成功安装后 `.trellis/workflow-embed-attempt.json` 被清理

### A 点初步判断

* 当前 workflow **已经存在** `uiprompt.site -> STITCH-PROMPT -> Stitch` 的固定顺序和 Codex 禁止承担 UI 原型主执行器的边界
* 当前 workflow **已经存在** `STITCH-PROMPT.md` 的“去 AI 味”基线检查
* 当前 workflow **不存在**把“Stitch 初稿之后去 Figma 做现代视觉风格校正/风格参考”定义为正式步骤的强制契约
* 当前 workflow **不存在**“UI 文案默认中文、但给 Stitch 的执行 prompt 默认英文”的明确规则
* 当前 workflow 仍以 `design/STITCH-PROMPT.md` 为正式产物名，没有把 `DESIGN.md` 设为别名或等价产物

### B 点初步判断

* 当前 workflow **不是**默认 `ownership_proof_required = yes`
* 当前机制是：feasibility 阶段强制显式填写 `ownership_proof_required: yes/no`
* 只有当 `ownership_proof_required = yes` 时，design 才要求 `source-watermark-plan.md`
* 测试已覆盖 `ownership_proof_required = no` 时 design 跳过水印计划校验的行为
* 已确认：`ownership_proof_required` 保持显式字段，不改成隐式默认；调整为模板/文档/脚手架的常规默认值写 `yes`

### Potential Change Surface

* 阶段命令源文档：`commands/design.md`、`commands/feasibility.md`、`commands/plan.md`
* 总纲/演练/映射：`工作流总纲.md`、`多CLI通用新项目完整流程演练.md`、`完整流程演练.md`、`命令映射.md`、`工作流全局流转说明（通俗版）.md`、`工作流思维导图.html`
* 平台说明：`commands/claude/README.md`、`commands/opencode/README.md`、`commands/codex/README.md`、`CLI原生适配边界矩阵.md`
* helper / validator / tests：`commands/shell/design-export.py`、`commands/shell/workflow-state.py`、`commands/shell/ownership-proof-validate.py` 及相关测试
