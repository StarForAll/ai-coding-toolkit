# brainstorm: 完善 trellis-library 目录内容

## Goal

在不破坏现有 `trellis-library/` 资产结构、manifest 注册机制和同步模型的前提下，补齐当前最有价值的目录内容缺口，使其更容易被使用、验证和维护。

## What I already know

* `trellis-library/` 已具备完整的顶层结构：`specs/`、`templates/`、`checklists/`、`examples/`、`schemas/`、`scripts/`、`manifest.yaml`、`README.md`、`taxonomy.md`。
* 根文档 [trellis-library/README.md](/ops/projects/personal/ai-coding-toolkit/trellis-library/README.md) 已定义库的用途、目录地图、pack 用法、同步模型和主脚本入口。
* 当前脚本能力已覆盖三类流程：`validation/`、`assembly/`、`sync/`，具体已有 7 个 Python 脚本。
* `validate-library-sync.py` 是当前核心验证入口；`.trellis/workflow.md` 也明确把它作为该仓库的项目级验证命令。
* `examples/assembled-packs/` 已存在多组 pack 示例，说明“内容资产”本身并不空，主要短板更偏向工程化支撑。
* 仓库内未发现 `trellis-library` 相关测试目录或测试函数，当前缺少直接验证脚本行为的测试层。
* 既有分析文档也已指出主要优化点集中在：统一 CLI 入口、测试、CI 或更清晰的使用入口。

## Assumptions (temporary)

* “进一步完善目录内容”优先指补齐高价值的工程化资产，而不是大规模新增整套 specs。
* 本次改动应尽量复用现有脚本，不重写已稳定的 `assembly/sync/validation` 逻辑。
* 最合理的 MVP 是补一层“统一入口 + 基础测试 + 文档对齐”，而不是扩张 taxonomy。

## Open Questions

* 无

## Requirements (evolving)

* 保持 `trellis-library/` 现有目录语义与资产命名稳定。
* 新增内容必须与现有 Python 脚本风格和 Trellis 文档风格一致。
* 优先补齐“使用入口清晰度”和“可验证性”相关缺口。
* 最终改动应落到具体文件，而不是只给建议。
* 本次范围确定为：统一 CLI + 基础测试 + 文档对齐。
* 统一 CLI 采用单层子命令形式：`validate`、`assemble`、`sync`。
* CLI 应作为薄包装层存在，尽量复用现有脚本，不重写其核心逻辑。

## Acceptance Criteria (evolving)

* [ ] 能明确说明 `trellis-library/` 当前结构和现有能力。
* [ ] 至少补齐一项当前明显缺失的高价值能力，并以代码/文件形式落地。
* [ ] 新增统一 CLI，能够调用现有核心能力且不改变既有行为语义。
* [ ] 新增基础测试，至少覆盖一个现有关键脚本流程和一个 CLI 入口行为。
* [ ] 文档与实现保持对齐。
* [ ] CLI 帮助信息和 README 使用示例一致。

## Definition of Done (team quality bar)

* Tests added/updated where appropriate
* Library validation run and results recorded truthfully
* Docs/notes updated if behavior changes
* No unregistered ad hoc asset bypassing `manifest.yaml`

## Out of Scope (explicit)

* 大规模重写 `manifest.yaml` 或重新设计 pack taxonomy
* 大批量新增与当前缺口无直接关系的 specs/templates/checklists
* 改造目标项目侧 `.trellis/` 工作流本身

## Technical Notes

* 任务目录：`.trellis/tasks/03-18-brainstorm-trellis-library-improvements/`
* 目录检查显示 `trellis-library/scripts/` 仅分为 `assembly/`、`sync/`、`validation/`，缺少统一 CLI 入口。
* 仓库检索未发现 `trellis-library` 相关测试文件，测试缺口是事实，不是推测。
* 现有验证命令：
  `/ops/softwares/python/bin/python3 trellis-library/scripts/validation/validate-library-sync.py --strict-warnings`
* CLI 决策：采用 `python trellis-library/cli.py <subcommand>` 形式，其中首批子命令为 `validate`、`assemble`、`sync`。

## Decision (ADR-lite)

**Context**: `trellis-library/scripts/` 已有稳定脚本，但入口分散、测试缺失，导致可用性和可维护性不足。

**Decision**: 本次采用单一入口 `trellis-library/cli.py`，暴露 `validate`、`assemble`、`sync` 三类一级子命令；同时补基础测试和 README 对齐，不重写底层脚本逻辑。

**Consequences**:

* 好处：入口统一、认知负担更低、后续扩展更自然。
* 代价：需要维护一层参数转发逻辑，并为 CLI 增加最小测试护栏。

## Research Notes

### What similar tools do

* 这类“脚本集合型仓库”通常会补一层统一 CLI，避免使用者记忆多个深路径脚本。
* 对已有稳定脚本做增量完善时，最常见的低风险策略是“薄包装入口 + 回归测试 + README 对齐”。
* 如果当前目录已经有主验证命令但没有测试，优先加最小测试比先做复杂 CI 更划算。

### Constraints from our repo/project

* 现有脚本均为 Python，可复用性高，适合通过统一入口转发。
* 项目工作流已经把 `validate-library-sync.py` 当作正式验证项，因此任何新增入口不应替代它的真实职责，只应提升易用性。
* 当前仓库偏文档/规范资产库，不应引入过重的工程框架。

### Feasible approaches here

**Approach A: 统一 CLI + 基础测试 + 文档对齐** (Selected)

* How it works:
  新增一个薄层 CLI 统一转发到 `validation/assembly/sync` 脚本；补最小测试验证 CLI 或关键脚本调用；同步更新 README。
* Pros:
  直接解决“难用”和“难验证”两个主要缺口，性价比最高。
* Cons:
  需要同时改动脚本、测试、文档三个面。

**Approach B: 只补测试与验证样例**

* How it works:
  保持现有脚本路径不变，只增加测试目录、测试用例和使用示例。
* Pros:
  风险最低，不碰现有调用方式。
* Cons:
  不能解决脚本入口分散的问题，用户体验提升有限。

**Approach C: 只补统一 CLI 和 README**

* How it works:
  新增一个统一入口脚本，把现有命令聚合起来，并更新使用文档。
* Pros:
  使用体验改善最直接。
* Cons:
  缺少测试护栏，后续维护风险仍偏高。
