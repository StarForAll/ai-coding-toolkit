# brainstorm: 分析新项目开发工作流初始化负担

## Goal

分析 `docs/workflows/新项目开发工作流/` 这套面向“新项目使用方”的工作流设计，判断它在初始化阶段是否偏重、是否会过早占用大量上下文，并给出基于实际文档内容的结论与优化方向。

## What I already know

* 用户关注的是 `./docs/workflows/新项目开发工作流/` 对应工作流本身，而不是当前仓库作为设计者/维护者的实现细节。
* 目标问题聚焦在“初始化是否过重”“是否在开始阶段就消耗大量上下文”。
* 该目录当前包含 `工作流总纲.md`、`命令映射.md`、两份流程演练文档、`commands/`、`learn/` 等内容。

## Assumptions (temporary)

* 需要先区分“文档很大”与“实际运行时必须注入的上下文很大”这两个层面。
* 需要识别初始化路径中的强制步骤、可选步骤、以及仅供参考的长文档。

## Open Questions

* 该工作流初始化阶段的最小必读集合是什么？
* 初始化阶段哪些步骤会真实扩大 AI 上下文，而哪些只是文档体量大但不必一次读完？
* 若偏重，主要重在文档组织、命令编排，还是上下文注入策略？

## Requirements (evolving)

* 基于实际文档内容分析初始化路径。
* 区分“工作流设计负担”和“当前项目实现负担”。
* 给出结论时同时说明证据、边界、以及可操作的减重建议。
* 区分“文档阅读负担”“默认上下文注入负担”“流程门禁动作负担”。

## Acceptance Criteria (evolving)

* [ ] 明确列出初始化主路径及其上下文来源
* [ ] 判断该工作流是否存在初始化过重问题，并说明程度
* [ ] 给出至少 2 条针对性的优化建议

## Definition of Done (team quality bar)

* 结论基于已读取的工作流文档与命令定义
* 说明哪些内容属于强制、哪些属于参考或后置
* 风险与结论边界表达清楚

## Out of Scope (explicit)

* 不分析当前仓库整体是否臃肿
* 不直接修改工作流文档或命令资产
* 不把“设计工作流的维护成本”混同为“使用工作流的初始化成本”

## Technical Notes

* 任务目录：`.trellis/tasks/04-02-analyze-new-project-workflow-init-overhead/`
* 待重点阅读：`docs/workflows/新项目开发工作流/工作流总纲.md`
* 待辅助阅读：`docs/workflows/新项目开发工作流/命令映射.md`、`docs/workflows/新项目开发工作流/完整流程演练.md`、`docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
* 文档规模：
  * `工作流总纲.md` 2875 行
  * `命令映射.md` 534 行
  * `多CLI通用新项目完整流程演练.md` 486 行
  * `完整流程演练.md` 460 行
  * 各阶段命令文档约 82-266 行
* 已确认的关键证据：
  * `工作流总纲.md` 与 `命令映射.md` 明确声明“渐进性披露”，并要求避免把平台细节塞进默认主上下文。
  * `多CLI通用新项目完整流程演练.md` 被定义为“首次接触的第一入口”，`工作流总纲.md` 与 `命令映射.md` 是后续按需阅读层。
  * `start-patch-phase-router.md` 为“首次嵌入后的初始化门禁”增加了 `pack.requirements-discovery-foundation` 检查与补齐要求。
  * `install-workflow.py` 会注入 AGENTS 自然语言路由表、阶段命令、辅助脚本，并在 Claude/OpenCode 的 `start.md` 上注入 Phase Router。
  * `commands/opencode/README.md` 的 `opencode.json.instructions` 示例一次性挂载 `工作流总纲.md` 与多个阶段命令文档，存在默认上下文偏重风险。
  * `commands/codex/README.md` 推荐在 SessionStart 注入 `.trellis/workflow.md`、`.trellis/spec/` 索引、当前任务状态、`start` skill 指令；相对没有把整套 workflow 文档全量塞进默认上下文。

## Research Notes

### Initialization Path

* 首次阅读入口：`多CLI通用新项目完整流程演练.md`
* 会话兜底入口：`/trellis:start` 或等价 skill，由 `Phase Router` 判断当前应进入的阶段
* 首次嵌入门禁：若检测到 `.trellis/workflow-installed.json` 存在且 `.trellis/library-lock.yaml` 缺少最低资产集，则先补 `requirements-discovery-foundation`

### Feasible Assessment

**结论草案**：这套 workflow 在“原则设计”上并不主张默认重上下文，但在“首次嵌入后的启动门禁”和“个别 CLI 的默认挂载方式”上确实存在初始化偏重问题。

### Candidate Improvement Directions

**方向 A：保留门禁，但拆成 minimal / extended 两级**（倾向推荐）

* 把 `problem-definition` / `scope-boundary` / `requirement-clarification` / `acceptance-criteria` 作为最小必需资产
* 将 customer/developer-facing PRD spec、template、checklist 改为进入 brainstorm/design 后按阶段补齐

**方向 B：保持资产门禁不变，但压缩默认注入层**

* 保持流程门禁
* 但默认只把主入口文档与当前阶段命令挂进 CLI instructions / hooks，不全量挂载多份规则与阶段文档

**方向 C：维持现状**

* 优点：流程完整、门禁前置
* 缺点：首次使用成本高，容易让使用者把“严谨”体验成“进入太慢、上下文太厚”。
