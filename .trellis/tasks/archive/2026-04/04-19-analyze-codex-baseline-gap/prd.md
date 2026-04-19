# brainstorm: analyze codex baseline gap in workflow

## Goal

在不立即修改实现的前提下，先针对 `docs/workflows/新项目开发工作流/` 中与 Codex 安装、`.codex/skills` 基线、`finish-work` 项目化补丁、`start` Phase Router 补丁相关的逻辑做证据化分析；同时通过 `/tmp` 下真实 `trellis init` 初始化后的临时项目复现安装行为，判断用户提出的错误点 A 是否真实存在、是否会导致能力缺失、以及后续应该如何修正。所有结论都必须优先服从 Trellis 核心工作机制，并分别满足 Claude Code / Codex / OpenCode 的原生适配边界。

## What I already know

* 用户要求先分析、后给方案，得到确认后才允许具体修改。
* 分析对象限定为 `docs/workflows/新项目开发工作流/` 目录内的工作流资产。
* `docs/workflows/新项目开发工作流/commands/install-workflow.py` 已存在 Codex 分支：
  * 对所有 Codex skills 目录遍历 `finish-work` 基线并条件注入项目化补丁。
  * 对所有 Codex skills 目录遍历 `start` 基线并条件注入 Phase Router 补丁。
  * 若某个目录缺失基线，只输出 info 日志并跳过该目录；若所有目录都缺失，则记为错误。
* `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md` 与 `commands/codex/README.md` 当前文档口径都写明：
  * Codex 可能同时存在 `.agents/skills/` 与 `.codex/skills/` 两个目录。
  * 阶段 skills 会同步写入所有目录。
  * `finish-work` 补丁是“有基线就打补丁，没有就跳过”。
* 现有日志文本与用户提到的问题一致：
  * `[Codex] .codex/skills 缺少 finish-work 基线，跳过该项目化补丁`
  * `[Codex] .codex/skills 缺少 start 基线，跳过该 Phase Router 补丁`

## Assumptions (temporary)

* `trellis init` 在某些版本或某些项目状态下，可能只在 `.agents/skills/` 写入 `start` / `finish-work`，而没有在 `.codex/skills/` 写入同名基线。
* 如果 `.agents/skills/` 中已经有对应基线并成功注入，那么 `.codex/skills/` 缺少基线未必等于实际能力缺失，可能只是多目录同步策略与日志呈现不够清晰。
* 如果 Codex 在真实加载链路中会命中 `.codex/skills/`，而 `.agents/skills/` 只是共享目录，则“跳过”可能确实造成能力缺失。

## Open Questions

* 当前更值得澄清的问题不是“日志会不会出现”，而是是否需要把“预期跳过”继续保留为当前这种容易误解的提示。
* 如果要修，应该优先修“日志/文档口径”，还是直接收紧安装器对 baseline patch 的目录选择逻辑？

## Requirements (evolving)

* 先在 `/tmp` 新建临时项目并执行 `trellis init`，基于真实落盘状态做分析。
* 分析必须覆盖 `docs/workflows/新项目开发工作流/` 中与 Codex skills、安装器、升级兼容、CLI 适配矩阵相关的源文件。
* 判断错误点 A 是否真实存在时，必须区分“日志存在”与“能力缺失存在”两个层面。
* 如果问题成立，需要给出符合 Trellis 核心机制且原生适配 Claude Code / Codex / OpenCode 的修正方案。
* 在用户确认修正方向前，不进行具体代码修改。

## Acceptance Criteria (evolving)

* [x] 通过真实 `trellis init` 初始化结果说明 `.agents/skills/` 与 `.codex/skills/` 的基线分布。
* [x] 明确指出 `install-workflow.py` 当前对 Codex `start` / `finish-work` 的处理逻辑与触发条件。
* [x] 判断 A 点属于：仅日志噪声 / 文档不一致 / 真实能力缺失 / 多项并存 中的哪一种。
* [x] 至少给出 2 个可行修正方向，并说明推荐项、影响范围、兼容性与风险。
* [ ] 在任何修改前先向用户给出结构化结论并等待确认。

## Definition of Done (team quality bar)

* 结论只基于真实文件、真实初始化结果和可定位的实现逻辑。
* 方案能解释与 Claude Code / Codex / OpenCode 三端原生承载边界的关系。
* 后续若进入实现，能明确要改哪些文件、为什么改、如何验证。

## Out of Scope (explicit)

* 本轮不直接修改 workflow 源文件。
* 本轮不同时处理用户尚未提出的其他错误点。
* 本轮不把 Codex 强行改写为项目级 `/trellis:*` slash command 模型。

## Technical Notes

* 关键实现：
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/start-skill-patch-phase-router.md`
  * `docs/workflows/新项目开发工作流/commands/finish-work-patch-projectization.md`
* 关键文档：
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `docs/workflows/新项目开发工作流/目标项目兼容升级方案指导.md`
* 后续需要补充：
  * 用户确认后的最终修正方向

## Research Notes

### `/tmp` 真实复现

在 `/tmp/trellis-codex-baseline-66w9bX` 中执行：

```bash
git init -b main
trellis init --claude --opencode --codex -y -u xzc
```

得到的真实基线分布：

* `.agents/skills/` 中存在 `start`、`finish-work`、`brainstorm`、`check` 等共享 Trellis skills。
* `.codex/skills/` 中默认只有 `parallel/SKILL.md`，没有 `start/SKILL.md`，也没有 `finish-work/SKILL.md`。
* `.codex/config.toml`、`.codex/hooks.json`、`.codex/hooks/session-start.py` 会被创建。
* 初始化后的 `AGENTS.md` 明确把 Codex 的项目级 skill 提示写成 `.agents/skills/`，没有把 `.codex/skills/` 当成主入口。

### workflow 安装真实结果

在同一临时项目中补齐 workflow 前置 Git 远端后执行：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/install-workflow.py \
--project-root /tmp/trellis-codex-baseline-66w9bX \
--cli codex
```

真实安装行为：

* 分发型阶段 skills 会同步写入 `.agents/skills/` 与 `.codex/skills/`。
* `.agents/skills/start/SKILL.md` 成功注入 Phase Router 补丁。
* `.agents/skills/finish-work/SKILL.md` 成功注入项目化补丁。
* `.codex/skills/parallel/SKILL.md` 成功被禁用覆盖。
* 安装日志会出现：
  * `[Codex] .codex/skills 缺少 finish-work 基线，跳过该项目化补丁`
  * `[Codex] .codex/skills 缺少 start 基线，跳过该 Phase Router 补丁`

### 升级检查结果

对已安装好的临时项目执行：

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
--check \
--project-root /tmp/trellis-codex-baseline-66w9bX \
--cli codex
```

结果为 `总冲突: 0`，并且只要求：

* `.agents/skills/start` 上的 Phase Router 补丁正常
* `.agents/skills/finish-work` 上的项目化补丁正常
* `.codex/skills/parallel` 上的禁用覆盖正常

也就是说，当前 workflow 自己的升级检测逻辑并**不**把 `.codex/skills` 缺少 `start/finish-work` 视为异常。

### 根因判断

错误点 A 的现状应拆成两层：

1. **日志层面：属实**
   * 当前安装器确实会对 `.codex/skills` 输出“缺少 start / finish-work 基线，跳过补丁”的信息。
2. **能力缺失层面：默认场景下不属实**
   * `trellis init` 的真实主承载链是 `.agents/skills/` + `AGENTS.md` + `.codex/hooks*`。
   * 安装器已经在 `.agents/skills/start` / `.agents/skills/finish-work` 成功注入补丁。
   * `upgrade-compat.py --check` 也确认当前状态是完整的健康状态。

因此，A 点更准确的定性是：

* **“日志噪声 / 语义误导”真实存在**
* **“默认安装后 Codex 缺少 start / finish-work workflow 增强能力”证据不足，且当前复现结果不支持这一说法**

## Feasible Approaches Here

**Approach A: 只修口径，不改安装行为**（最小改动）

* How it works:
  * 保留当前多目录遍历逻辑。
  * 调整安装日志、边界矩阵、Codex README 的表述，明确 `.agents/skills/` 是当前 `trellis init` 产出的主承载面，`.codex/skills/` 默认只需要承载存在的 Codex 本地 skill（当前最典型的是 `parallel`）。
* Pros:
  * 最安全，不改变安装器真实行为。
  * 能直接消除“看起来像缺能力”的误导。
* Cons:
  * 代码里仍会遍历 `.codex/skills` 的 baseline patch 检查，逻辑层面不够收敛。

**Approach B: 收紧 baseline patch 目标目录，分发 skill 与 baseline patch 分开处理**（Recommended）

* How it works:
  * 对 `start` / `finish-work` 这类“基线增强型 skill”，优先只针对 `resolve_codex_skills_dir(root)` 返回的主目录做补丁注入与成功日志。
  * 继续对 `list_all_codex_skills_dirs(root)` 做“阶段分发型 skill”同步和 `parallel` 禁用覆盖。
  * 同步更新文档与测试，明确：分发 skill 是多目录同步；baseline patch 只打到真实存在且被 Trellis 当作主 skills 目录的那一侧。
* Pros:
  * 逻辑与 `trellis init` 真实基线更一致。
  * 能消除误导日志，同时保留多目录同步的必要部分。
  * 与当前 `resolve_codex_skills_dir` 的“`.agents/skills` 优先”规则一致。
* Cons:
  * 需要同步修改安装器、升级检查文档和测试，改动面比 A 大。

**Approach C: 主动在 `.codex/skills/` 补建 `start` / `finish-work` 基线再打补丁**（Not recommended）

* How it works:
  * 安装器在发现 `.codex/skills` 缺少基线时，直接复制或生成 `start` / `finish-work` baseline skill 到 `.codex/skills/`，再追加补丁。
* Pros:
  * 表面上能让两个目录都“完整”。
* Cons:
  * 偏离当前 `trellis init` 真实基线。
  * 容易把 `.codex/skills/` 变成第二套共享技能副本，增加升级和漂移风险。
  * 缺乏当前证据支持其必要性。
