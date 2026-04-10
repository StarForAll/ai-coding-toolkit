# brainstorm: 分析新项目开发工作流对 browser_bookmark_cleaner_rchiver 的兼容升级方案

## Goal

基于 `docs/workflows/新项目开发工作流` 现有的目标项目兼容升级机制，分析
`/ops/projects/personal/browser_bookmark_cleaner_rchiver` 是否适合走普通兼容升级主链，
并给出一份可执行但暂不落地的操作方案，等待用户确认后再实施。

## What I already know

* 用户明确要求当前阶段只做分析和方案，不执行实际兼容升级。
* 用户补充了关键语义映射：
  * 目标项目中的 `self-review` = 当前工作流中的 `check`
  * 目标项目中的 `check` = 当前工作流中的 `review-gate`
* 当前仓库已提供目标项目兼容升级分析文档：`docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`。
* 当前仓库已提供三类核心脚本：
  * `commands/install-workflow.py`：生成 `B` 期望状态
  * `commands/analyze-upgrade.py`：执行 `A/B/C` 三态分析
  * `commands/upgrade-compat.py`：仅处理低风险漂移修复
* 目标项目存在已安装工作流痕迹：
  * `.trellis/workflow-installed.json`
  * `.trellis/scripts/workflow/`
  * `.claude/commands/trellis/`
  * `.opencode/commands/trellis/`
  * `.agents/skills/` 与 `.codex/skills/`
* 目标项目当前 `.trellis/.version` 为 `0.4.0-beta.8`，Git 工作区当前干净。
* 目标项目当前安装记录中缺少 `workflow_version` / `workflow_schema_version`。
* 目标项目安装记录仍使用旧资产集合：
  * commands: `feasibility, brainstorm, design, plan, test-first, self-review, check, delivery`
  * scripts: `feasibility-check.py, design-export.py, plan-validate.py, self-review-check.py, delivery-control-validate.py, metadata-autocommit-guard.py, record-session-helper.py`
* 当前 workflow 源资产已经切换到新集合：
  * commands: `feasibility, brainstorm, design, plan, test-first, check, review-gate, delivery`
  * scripts: `feasibility-check.py, design-export.py, plan-validate.py, check-quality.py, delivery-control-validate.py, metadata-autocommit-guard.py, record-session-helper.py`

## Assumptions (temporary)

* 当前仓库中的 workflow 源资产兼容升级已经完成，可作为最新期望状态来源。
* 目标项目已经做过 Trellis 官方升级，或至少当前将以“先验证是否满足该前置”作为方案第一步。
* 目标项目中可能存在对 workflow 托管文件的私有改动，需要在正式执行前做三态分析确认。

## Open Questions

* 目标项目是否已经完成“仅处理 Trellis 官方基线冲突”的官方升级前置？
* 针对 `self-review -> check`、`check -> review-gate` 与 `self-review-check.py -> check-quality.py` 的变化，本次能否仍落在普通兼容升级，还是已经触发结构性迁移？
* 目标项目的 workflow 托管文件中是否存在较重的私有改写，导致 `merge` 项占主导？

## Requirements (evolving)

* 给出面向当前目标项目的具体兼容升级操作方案。
* 明确区分“分析阶段可执行动作”和“用户确认后才能执行的修改动作”。
* 标出必须满足的前置条件、推荐执行顺序、风险点和回退点。
* 判断本次更偏向普通兼容升级还是需要先做结构性迁移判断。

## Acceptance Criteria (evolving)

* [ ] 明确列出本次方案依赖的前置条件
* [ ] 明确列出建议执行顺序和每一步对应的命令/输入/产出
* [ ] 明确列出普通兼容升级与结构性迁移的分叉判定条件
* [ ] 明确列出当前阶段不执行的内容，等待用户确认

## Definition of Done (team quality bar)

* 方案覆盖分析、执行、验证、回退四个方面
* 结论基于已读文档和目标项目现状，不凭记忆猜测
* 明确哪些步骤只读、哪些步骤会修改目标项目

## Out of Scope (explicit)

* 现在不运行 `install-workflow.py`、`analyze-upgrade.py`、`upgrade-compat.py`
* 现在不改动目标项目任何文件
* 现在不执行真实的 `/tmp` 基线构造与三态分析

## Technical Notes

* Workflow upgrade guidance: `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
* Structural migration boundary: `docs/workflows/新项目开发工作流/结构性迁移设计.md`
* Managed asset definitions: `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
* Target project install record: `/ops/projects/personal/browser_bookmark_cleaner_rchiver/.trellis/workflow-installed.json`
* Target project AGENTS route table still references `self-review`

## Research Notes

### What similar tooling in this repo already supports

* `目标项目兼容升级方案指导.md` 已经把升级主链定义为：先完成 workflow 源资产兼容升级，再让目标项目完成 Trellis 官方升级，然后执行 `A/B/C` 三态分析，最后仅对低风险漂移使用 `upgrade-compat.py`。
* `analyze-upgrade.py` 已支持读取目标项目当前 `workflow-installed.json` 中的旧命令/脚本清单，把“当前 workflow 不再托管但目标项目仍存在”的旧资产识别为 `delete`。
* `upgrade-compat.py` 目前只会重部署当前 `DISTRIBUTED_COMMANDS` 和 `HELPER_SCRIPTS`，以及恢复 `start/finish-work/record-session` 补丁，不会主动删除安装记录里的旧遗留资产。

### Constraints from our repo/project

* 目标项目当前确实仍带有旧版 `self-review` 语义和 `self-review-check.py` helper。
* 当前 workflow 源资产已经切换到：
  * `check` = 实现后质量检查
  * `review-gate` = 任务级多 CLI 补充审查门禁
  * `check-quality.py` = `check` 阶段 helper
* 目标项目缺失 `workflow_version` / `workflow_schema_version`，需要按 `legacy/unknown` 处理，但这本身不构成升级阻塞。
* 只读执行 `upgrade-compat.py --check` 后，目标项目共检出 `26` 个冲突，覆盖三类 CLI 与 shared scripts，说明当前项目与最新 workflow 期望状态存在系统性漂移，而不是单点补丁丢失。
* 目标项目旧版命令与新版命令不是简单“删除旧命令、新增新命令”，而是存在语义迁移关系：
  * 旧 `self-review` 的职责与当前 `check` 对齐
  * 旧 `check` 的职责与当前 `review-gate` 对齐
  * 旧 `self-review-check.py` 的职责与当前 `check-quality.py` 对齐

### Feasible approaches here

**Approach A: 带语义映射表的 `A/B/C` 三态分析，再按动作清单执行** (Recommended)

* How it works:
  * 先在 `/tmp` 构造纯净基线 `A` 和当前 workflow 期望状态 `B`
  * 将目标项目官方升级后的真实状态作为 `C`
  * 用 `analyze-upgrade.py` 产出 `add / replace / merge / delete`
  * 在解释报告时额外套用“旧 `self-review` → 新 `check`、旧 `check` → 新 `review-gate`、旧 `self-review-check.py` → 新 `check-quality.py`”的语义映射表
  * 只把低风险 `replace/add` 交给 `upgrade-compat.py`
  * 对 rename 对应项、`delete` 和 `merge` 做人工核对与定向处理
* Pros:
  * 与仓库文档定义的主链一致
  * 能显式发现“语义迁移但文件名不同”的旧资产
  * 更适合当前“旧资产集合 -> 新资产集合”的变更
* Cons:
  * 前期准备较多
  * 真正执行时仍需人工判断 rename 项上的私有漂移、`merge` 和结构性 break

**Approach B: 直接运行 `upgrade-compat.py --check/--merge`**

* How it works:
  * 跳过 `A/B/C`，直接以当前源资产和目标项目现状做低风险修复
* Pros:
  * 执行最快
* Cons:
  * 会直接把目标项目当前的 `check.md` 覆盖成新版“质量检查”，但不会先判断其中是否存在旧 gate 语义上的私有改写
  * 无法系统识别和清理 `self-review` / `self-review-check.py` 这类语义已迁移的旧资产
  * 可能把新旧路由、新旧命令和新旧 helper 同时留在项目里
  * 不符合当前文档对 rename / retired asset 升级的建议主链

**Approach C: 先按结构性迁移处理**

* How it works:
  * 直接把本次升级视为普通兼容升级已不足以解释，先产出迁移方案，再做迁移
* Pros:
  * 对潜在 breaking change 最保守
* Cons:
  * 当前证据还不足以证明必须走这条路
  * 容易把原本可按文件级动作解决的问题过度升级
