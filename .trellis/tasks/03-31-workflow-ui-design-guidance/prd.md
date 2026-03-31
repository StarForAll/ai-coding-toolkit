# brainstorm: 补充新项目工作流中的外部UI设计指引

## Goal

在 `docs/workflows/新项目开发工作流/` 的设计阶段文档中，补充一条可执行的外部 UI 设计引导：当进入 UI 设计阶段时，先提示用户去 `https://www.uiprompt.site/zh/styles` 获取 UI 提示词，再去 `https://stitch.withgoogle.com/` 生成 UI 原型，使工作流不仅说明“内部如何设计”，也明确“用户需要去哪些外部站点完成原型设计”。

## What I already know

* 用户希望补充的是“新项目开发工作流”中的 UI 设计阶段说明。
* 直接命中入口文件是 `docs/workflows/新项目开发工作流/commands/design.md`。
* `design.md` 当前 Step 1 只写了 `ui-ux-pro-max` 粗稿生成，没有写外部站点操作链路。
* `docs/workflows/新项目开发工作流/工作流总纲.md` 的 `3.1 UI/UX设计` 已提到 Stitch、Figma、Sketch 等工具，但没有明确写出先去 `uiprompt.site` 获取提示词、再去 Stitch 生成原型的具体步骤。
* 文档规范要求内容简洁、可执行、路径和命令精确，并保持与现有目录语言风格一致。

## Assumptions (temporary)

* 本次改动以文档补充为主，不涉及脚本逻辑修改。
* 至少需要更新 `design.md`；是否同步更新 `工作流总纲.md` 与 `命令映射.md` 取决于范围选择。
* 外部站点仅作为操作指引，不要求在仓库内新增自动化集成。

## Open Questions

* 无。范围已确认：同步更新命令级设计说明与总纲级设计说明。

## Requirements (evolving)

* 在 UI 设计阶段明确提示用户去 `https://www.uiprompt.site/zh/styles` 获取 UI 提示词。
* 明确提示用户去 `https://stitch.withgoogle.com/` 生成 UI 原型。
* 说明这是一条“外部操作链路”，用于帮助用户完成 UI 设计，而不是仓库内自动执行步骤。
* 文档语气需保持当前工作流文档风格，强调可执行步骤。
* 提醒必须落在“进入需要外部 UI 设计的阶段时”，而不是只埋在补充说明或附录里。
* 命令层与总纲层都要出现该提醒，避免阶段说明漂移。

## Acceptance Criteria (evolving)

* [ ] 设计阶段文档中出现 `uiprompt.site` 与 `stitch.withgoogle.com` 的明确指引。
* [ ] 文档能让读者理解推荐顺序：先取 UI 提示词，再生成 UI 原型。
* [ ] 改动后的内容与现有工作流表述风格一致，不引入无关实现细节。
* [ ] 读者一进入设计阶段，就能看到“需要去外部做 UI 设计”的明确提醒。
* [ ] `design.md` 与 `工作流总纲.md` 的阶段说明保持一致。

## Definition of Done (team quality bar)

* 文档改动与实际工作流位置对齐
* 相关引用路径与站点地址准确
* 必要的关联文档已同步，避免同一阶段说明冲突

## Out of Scope (explicit)

* 自动化调用外部网站
* 为 Stitch 或 UI Prompt Site 编写脚本、插件或集成
* 改写整个设计阶段流程

## Technical Notes

* 已定位文件：
  * `docs/workflows/新项目开发工作流/commands/design.md`
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
* `工作流总纲.md` 的 `3.1.2 外部工具精细化设计` 已包含 Stitch，但还缺少面向用户的外部站点使用步骤。
