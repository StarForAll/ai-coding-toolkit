# 分析 Codex 工作流嵌入失败原因与修正方案

## Goal

基于 `docs/workflows/新项目开发工作流` 的实际安装协议、安装器实现、`trellis init` 初始化产物和 `/tmp` 临时目标项目复现实验，判断 Codex 嵌入失败的分析结论是否成立；若问题确实存在，则仅提出符合 Claude Code / Codex / OpenCode 原生承载边界且以 Trellis 核心机制为前提的修正方案，待用户确认后再实施修改。

## What I already know

* 用户限定分析范围为 `docs/workflows/新项目开发工作流/`，后续修改也只能发生在该目录内。
* 用户要求先在 `/tmp` 新建临时项目，并使用 `trellis init` 初始化后再判断分析。
* 当前 workflow 的嵌入协议要求先跑 `detect-embed-state.py`，只有 `INITIAL_BASELINE_READY` 才允许安装。
* 当前 workflow 对 Codex 的原生承载边界是 `AGENTS.md + hooks + skills + subagents`，不是项目级 slash commands。
* `install-workflow.py` 的 Codex 部署逻辑会枚举所有已存在的 skills 目录，并对阶段 skill 进行同步写入。
* `install-workflow.py` 对 Codex baseline patch skill（`start` / `finish-work`）会优先写 `.backup-original/.../SKILL.md` 备份，再覆盖活动 skills 目录。
* `工作流嵌入执行规范.md` 规定：正式安装开始后会先写 `.trellis/workflow-embed-attempt.json`；若安装中途失败，目标项目即进入非初始态，不能继续覆盖安装。
* 当前已通过代码阅读确认：若 Codex 安装阶段发生写入失败，安装器应保留失败的 attempt record，后续状态检测应返回阻断状态。

## Assumptions (temporary)

* 用户提供的失败分析来自真实目标项目，但其环境约束不一定与当前会话完全一致。
* Codex 安装失败可能由多种原因触发：目录只读、技能目录枚举策略不稳、备份策略过于激进、基线/影子目录同步边界不合理，或几者叠加。
* 若 `/tmp` 复现环境无法复现只读错误，也仍可能说明当前结论“环境只读是唯一根因”并不充分，需要回到工作流设计本身评估稳健性。

## Open Questions

* A 点中的“当前环境对 `.agents/skills` / `.codex/skills` 只读”是否能在本会话的 `/tmp` 复现环境中稳定复现？
* 即使存在环境只读限制，当前安装器对 Codex skills 目录“多目录同步 + 先备份后写入”的策略是否过于脆弱，需要 workflow 级修正？
* 如需修正，应该落在“文档澄清”、“状态/报错改进”、“部署策略调整”、“目录探测/备份策略调整”中的哪一层？

## Requirements (evolving)

* 先在 `/tmp` 新建临时目标项目并执行 `trellis init`，以真实初始化产物为依据分析。
* 先分析、不直接修改；只有用户确认修正方案后才实施代码或文档变更。
* 所有分析和方案必须以 Trellis 核心机制为前提，同时满足 Claude Code / Codex / OpenCode 的原生承载边界。
* 对用户给出的错误点，只有在证据支持“确实存在”时才提出修改建议。
* 若发现问题不完全等同于用户给出的结论，需要明确区分“已证实事实”“推断”“尚未证实”。

## Acceptance Criteria (evolving)

* [ ] 已完成对 `工作流嵌入执行规范.md`、`CLI原生适配边界矩阵.md`、`commands/install-workflow.py`、`commands/workflow_assets.py`、`commands/detect-embed-state.py` 的证据链阅读。
* [ ] 已在 `/tmp` 创建临时目标项目，并执行 `trellis init` 观察 Codex 相关初始化产物。
* [ ] 已在临时目标项目中执行该 workflow 的状态检测、预演和至少一次正式安装尝试或等价复现实验。
* [ ] 已明确区分 A 点结论中的“直接证据”“实验复现结果”“基于实现的推断”。
* [ ] 若确认问题存在，已提出 2–3 个可选修正方向并给出推荐方案与 trade-off。
* [ ] 在用户确认前，不对 `docs/workflows/新项目开发工作流` 下文件做实际修改。

## Definition of Done (team quality bar)

* 结论与证据可回溯到具体文件、脚本行为和复现实验
* 明确说明哪些内容已验证、哪些未验证
* 若后续进入修改阶段，需补齐测试/校验与文档传播面分析

## Out of Scope (explicit)

* 在本轮未经确认直接修改 workflow 源文件
* 修改 `docs/workflows/新项目开发工作流` 之外的仓库结构或 Trellis 核心实现
* 把单一目标项目的环境问题直接等同为 workflow 设计缺陷，除非证据充分

## Technical Notes

* 已读：
  * `docs/workflows/新项目开发工作流/工作流嵌入执行规范.md`
  * `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  * `docs/workflows/新项目开发工作流/commands/codex/README.md`
  * `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  * `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  * `docs/workflows/新项目开发工作流/commands/detect-embed-state.py`
  * `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md`
* 当前观察到的关键实现：
  * `list_all_codex_skills_dirs(root)` 会返回 `.agents/skills` 与 `.codex/skills` 中所有已存在目录。
  * `resolve_codex_skills_dir(root)` 优先把 `.agents/skills` 视为活动目录，其次才是 `.codex/skills`。
  * `deploy_codex()` 会在 baseline patch skill 覆盖前写 `.backup-original`，阶段 skill 则向所有 skills 目录直接同步写入。
  * `detect-embed-state.py` 在存在 attempt record 时会把项目判定为阻断态并输出失败细节。
* 待补充：
  * 若用户确认修改，需补充传播面清单与修改后验证矩阵

## Research Notes

### `/tmp` 真实复现结果

* 在 `/tmp/trellis-codex-embed-repro` 中执行 `trellis init --codex --claude --opencode -y -u xzc` 后，真实产物同时包含：
  * `.agents/skills/`：承载 `start`、`brainstorm`、`finish-work` 等基线/共享 skills
  * `.codex/skills/parallel/`：额外存在的 Codex 侧 skill 目录
  * `.codex/agents/*.toml`、`.codex/hooks.json`、`.codex/hooks/session-start.py`
* 在该标准初始化项目上，按协议顺序执行：
  * `detect-embed-state.py --project-root ... --cli codex`
  * `install-workflow.py --project-root ... --cli codex --dry-run`
  * `install-workflow.py --project-root ... --cli codex`
* 结果均通过，说明当前 workflow 在标准 `trellis init` 基线上可以成功嵌入 Codex。

### 对 A 点结论的拆分判断

* **已证实**：
  * 如果 `.agents/skills` / `.codex/skills` 不可写，安装会在 Codex 部署阶段创建 `.backup-original` 时失败。
  * 失败后安装器会保留 `.trellis/workflow-embed-attempt.json`，并将目标项目判定为 `BLOCKED_NON_INITIAL_STATE`。
* **未证实**：
  * “当前 workflow 本身无法嵌入 Codex”这一更强结论不成立，因为标准初始化项目中已成功安装。
* **合理推断**：
  * 用户提供案例中的直接根因更像是“目标项目/执行环境对 Codex skills 目录写入受限”，不是 workflow 对 Codex 的承载模型本身错误。

### 额外发现

* 当前安装器对这类权限异常会：
  * 先写 attempt record
  * 在 `except Exception` 中将状态记为 `failed`，`last_step=unexpected-exception`
  * 然后直接重新抛出 traceback
* 这意味着：
  * 状态记录契约是成立的
  * 但用户侧报错体验偏底层，不能清楚区分“环境写权限问题”与“workflow 设计问题”

### Feasible approaches here

**Approach A: 只增强安装器的权限预检与错误表达**（Recommended）

* How it works:
  * 在正式安装前，对 Codex 目标目录做可写性预检
  * 若 `.agents/skills` / `.codex/skills` 中任一 workflow 计划写入的目录不可写，则在进入正式写入前给出结构化失败信息并退出
  * 把当前 `unexpected-exception` 权限错误改为面向用户的明确报错，同时保留 attempt record 语义
* Pros:
  * 不改变当前 Trellis/Codex 承载边界
  * 不破坏现有多目录同步策略
  * 能显著降低误判为“workflow 设计坏掉”的概率
* Cons:
  * 不能绕过只读环境本身
  * 只改善诊断，不改变部署策略

**Approach B: 对 Codex skills 部署增加“逐目录预检 + 分类别失败说明”**

* How it works:
  * 安装器先枚举所有 skills 目录
  * 分别检查 backup 目标、分发 skill 目标、baseline patch 目标的可写性
  * 输出“哪个目录、哪个资产类别、为什么需要写、为什么失败”
* Pros:
  * 比 A 更精细，适合 `.agents/skills` 与 `.codex/skills` 权限不一致的场景
  * 与当前多目录同步模型天然匹配
* Cons:
  * 实现和测试传播面更大
  * 仍不改变“必须可写才能安装”的本质

**Approach C: 调整 Codex 部署策略，减少对非活动目录的强写入依赖**

* How it works:
  * 重新评估是否所有阶段 skill 都必须同步写入全部 skills 目录
  * 可能收缩到“活动目录优先，影子目录仅校验或条件同步”
* Pros:
  * 理论上可降低某些目录受限时的失败概率
* Cons:
  * 这会触碰当前 workflow 对多目录同步的一致性设计
  * 需要同步更新文档、校验器、测试和兼容边界，风险明显更高
  * 当前证据不足以证明必须走这一步

## Decision (ADR-lite)

**Context**: 用户提供的失败分析把问题指向 Codex 技能目录只读，并怀疑 workflow 嵌入逻辑本身存在问题。  
**Decision**: 当前阶段建议优先采用 Approach A，必要时补充 Approach B；暂不建议直接改成 Approach C。  
**Consequences**:
* 可以保留现有 Trellis 核心与多 CLI 原生承载边界
* 可以把“环境权限失败”与“workflow 设计失败”清楚区分
* 若后续仍频繁遇到目录不一致问题，再评估是否需要升级为部署策略调整
