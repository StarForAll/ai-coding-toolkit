# brainstorm: 修正新项目开发工作流

## Goal

在 `docs/workflows/新项目开发工作流/` 范围内修正现有工作流文档与安装叙事，使其明确支持 Claude Code / Codex / OpenCode 的原生适配模型，并补齐前置校验、spec 导入方式、以及 workflow 安装后对 Trellis bootstrap/finish-work 基线的处理规则。

## What I already know

* 修改范围被明确限制在 `docs/workflows/新项目开发工作流/`
* 用户要求补充前置校验：目标项目必须是 Git 项目，且存在多个 remote 仓库
* 用户给出了多个 push remote 的参考命令：
  * `git remote set-url --add --push origin git@github.com:xxx/yyy.git`
  * `git remote set-url --add --push origin git@gitee.com:xxx/yyy.git`
* 用户要求把“初始阶段导入 spec”改为“通过对应脚本导入”，而不是让用户通过提示自行安装
* 用户要求在安装该 workflow 后删除 `trellis init` 创建的 `00-bootstrap-guidelines` 任务
* 用户要求移除 finish-work 中的 `pnpm` 校验占位，后续待技术架构明确后再补充具体内容
* 用户明确要求在实际修改前，先说明如何修正并与其确认
* 当前工作流文档已经声明原生适配范围为 Claude Code / OpenCode / Codex
* 现有文档已强调安装顺序为：先 `trellis init`，再执行 `docs/workflows/新项目开发工作流/commands/install-workflow.py`
* 仓库中存在 `.trellis/scripts/create_bootstrap.py`，其中明确会创建 `.trellis/tasks/00-bootstrap-guidelines/`
* `commands/install-workflow.py` 当前只校验：
  * 目标项目存在 `.git`
  * 已执行 `trellis init`
  * 存在 `.trellis/.version`
  * 尚未校验多 remote / 多 push URL
* `commands/install-workflow.py` 当前安装完成后的提示仍要求：
  * 先补 `pack.requirements-discovery-foundation`
  * 若未接入 `trellis-library` CLI，则手动复制最低资产集到目标项目 `.trellis/`
* `commands/start-patch-phase-router.md` 当前也保留“手动复制最低资产集”的降级路径
* `commands/design.md` 与 `完整流程演练.md` 已经使用 `trellis-library/cli.py assemble` 作为 spec 导入示例
* `工作流总纲.md` 的自动化检查矩阵模板仍含 `pnpm lint` / `pnpm type-check` / `pnpm test` 占位示例

## Assumptions (temporary)

* 本次修正主要落在 workflow 文档、命令说明、平台 README，可能还会补充安装/卸载脚本的行为描述
* “删除 00-bootstrap-guidelines” 应优先由 workflow 安装脚本在目标项目中自动处理，而不是只写文档提醒
* “spec 导入脚本” 应统一收敛为 `trellis-library/cli.py assemble` 或 workflow 自带脚本显式调用，不再保留“手动复制最低资产集”的正式叙事
* `finish-work` 的 `pnpm` 校验删除，优先表现为：
  * 去掉 workflow 文档里的 `pnpm` 示例占位
  * 若 workflow 目录内存在对 `finish-work` 基线的适配说明或补丁点，则同步改成“待架构确认后填写真实矩阵”

## Open Questions

* “多个 remote 仓库” 的判定口径，是：
  * A. `origin` 下存在至少两个 push URL（与用户给出的 `git remote set-url --add --push origin ...` 一致）
  * B. Git 中存在至少两个独立 remote 名称
* 对 `finish-work` 的处理，是否只收敛 workflow 目录中的文档/安装规则，还是需要在当前 workflow 中新增对 Trellis 原生命令 `finish-work` 的自动补丁？

## Requirements (evolving)

* 明确新项目 workflow 的前置校验要求
* 保持对 Claude Code / Codex / OpenCode 的原生适配叙事一致
* 在实际修改前形成一版可确认的修正方案
* 将“初始化后补 spec”的正式路径统一为脚本导入，而不是人工复制资产
* 在 workflow 安装后处理 `00-bootstrap-guidelines`
* 移除 workflow 目录中 `finish-work` 相关的 `pnpm` 占位叙事

## Acceptance Criteria (evolving)

* [ ] 能指出需要修改的文档/文件及其原因
* [ ] 能给出每项修正的落点与一致性处理方式
* [ ] 用户确认方案后再进入具体修改

## Definition of Done (team quality bar)

* Docs/notes updated if behavior changes
* Changes stay scoped to `docs/workflows/新项目开发工作流/` unless an explicitly approved exception is needed
* Validation/consistency checks run for touched assets where applicable

## Out of Scope (explicit)

* 当前不直接改动工作流目录外的通用 Trellis 基线，除非后续确认必须联动
* 当前不提前补充具体技术栈校验矩阵内容

## Technical Notes

* 已检索到的核心文件：
  * `docs/workflows/新项目开发工作流/工作流总纲.md`
  * `docs/workflows/新项目开发工作流/命令映射.md`
  * `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * `docs/workflows/新项目开发工作流/commands/claude/README.md`
  * `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
* 已确认相关现状：
  * 当前文档前置条件只写了“Git 项目 + 已执行 `trellis init`”，尚未体现“多个 remote 仓库”
  * `.trellis/scripts/create_bootstrap.py` 仍会创建 `00-bootstrap-guidelines`
  * `工作流总纲.md` 中仍包含 `pnpm lint` / `pnpm type-check` / `pnpm test` 之类占位示例

## Research Notes

### Relevant Files

* `docs/workflows/新项目开发工作流/工作流总纲.md`
  * 权威规则层，当前定义安装前提、`§3.7` spec 对齐门禁、自动化检查矩阵模板
* `docs/workflows/新项目开发工作流/多CLI通用新项目完整流程演练.md`
  * 第一入口 walkthrough，当前对安装顺序和三端入口协议有总说明
* `docs/workflows/新项目开发工作流/命令映射.md`
  * 阶段到命令/skill/CLI 的映射文档，需保持与总纲一致
* `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `start` 补丁说明，当前定义“首次嵌入后补 requirements 基线”的门禁逻辑
* `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * 当前 workflow 真正的安装入口；若要把“前置校验”“删除 bootstrap 任务”做成真实行为，应落在这里
* `docs/workflows/新项目开发工作流/commands/claude/README.md`
* `docs/workflows/新项目开发工作流/commands/opencode/README.md`
* `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * 三端原生适配说明，前置条件与安装时序必须同步更新

### Code Patterns Found

* spec 导入的脚本化正例：
  * `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/完整流程演练.md`
  * 均已使用 `python3 trellis-library/cli.py assemble ...`
* 原生命令补丁模式：
  * `commands/install-workflow.py` 目前只给 `start` / `record-session` 注入补丁，不处理 `finish-work`
* 多 CLI 一致叙事模式：
  * `工作流总纲.md` + `命令映射.md` 定义通用规则
  * `commands/{claude,opencode,codex}/README.md` 分别补平台私有承载方式

### Feasible Approaches Here

**Approach A: 文档收敛 + 安装器补最小行为** (Recommended)

* How it works:
  * 在总纲 / walkthrough / 映射 / 三端 README 中统一补上“Git + 多 remote”前置条件
  * 在 `install-workflow.py` 里新增真实前置校验，并在安装后自动删除目标项目中的 `00-bootstrap-guidelines`
  * 统一把 requirements/spec 初始化写成脚本导入，不再保留“手动复制最低资产集”作为正式路径
  * 去掉 workflow 目录里的 `pnpm` 占位矩阵与相关文案
* Pros:
  * 改动集中在 workflow 自己目录内
  * 文档与真实安装行为一致
  * 不需要越界改 Trellis 全局基线
* Cons:
  * 如果后续确实要改目标项目 `finish-work` 命令正文，还需下一轮补一个专门 patch

**Approach B: 文档收敛 + 安装器补行为 + 新增 finish-work patch**

* How it works:
  * 包含 Approach A
  * 再在 workflow 内新增 `finish-work` 的自动补丁文件，并由安装器在目标项目里修改 Trellis 原生命令
* Pros:
  * “删除 pnpm 校验”会直接落到目标项目命令行为，不只是文档
* Cons:
  * 影响面更大，需要同时定义 Claude/OpenCode/Codex 三端对 `finish-work` 的原生适配方式
  * 当前 workflow 之前没有 `finish-work` patch 机制，新增后需要额外测试与说明
