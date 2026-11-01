# wf-framework-design 深度审查报告

初报基线：`d4b7a87`（2026-10-31）。以下保留初始取证供追溯；2026-11-01 的用户裁决与根因复核以 [decisions.md](./decisions.md) 为准，不把初报四项都当作当前缺陷。

## 结论

设计稿、charter、索引和机检器已经基本收敛，未发现偏离“单人、本机、单一共享工作区、顺序执行、本地完整路径”核心定位的重大问题。此前多轮审查中已经修复的候选不重复列出。

当前仅 F2、F4 经人确认进入修复规划。F1 已按用户指定命令核验本项目安装状态，不纳入本轮互斥检测扩展；F3 撤出当前缺陷，依既有设计在 wf 完成后适配。F2 的初报范围过宽，现已收窄为现有步骤内的动作/验证消费边界；具体纠正见 decisions.md。

## F1 初报：Trellis 互斥检测（现不纳入本轮修订）

**证据**

- `docs/workflows/wf-framework-design.md:149` 要求 `/wf-start` 在“检测到激活的 Trellis 上下文注入”时阻断；同段又声明检测只依据路径和 hook 配置等结构，不能证明宿主当前会话是否实际注入。
- `docs/workflows/wf-framework-design.md:594` 的验收行只描述“检测到激活 Trellis 注入”的结果，没有定义资产存在、hook 配置存在、当前会话实际注入三者的判定关系。

**实际场景**

目标项目存在 `.trellis/` 和 hooks 配置，但当前 CLI 没有启用注入；或者宿主确实注入了 Trellis，但结构文件不完整。两种情况下实现都无法从现行契约确定应阻断、提示人裁决还是继续。

**影响**

实现可能过度阻断所有共存项目，也可能在实际注入时放行，造成 wf 与 Trellis 同会话运行，违背独立会话流转边界。跨宿主实现还会出现不同结果。

**根因判断**

上位能力互斥规则和运行时可观测信号被写在同一条款中，但没有定义观测源优先级、未知状态的保守出口和 false negative/positive 处理。

**最低改进方向**

定义一个可实现的检测谓词和未知出口：至少区分“资产存在”“注入配置存在”“当前会话注入已证实”；明确检测能力不足时是否需人裁决或按风险阻断，并为无资产、仅资产、配置存在、实际注入、检测失败各给一条验收场景。

## F2 / P1：用户工作流步骤的执行边界（接受；根因与范围已收窄）

**证据**

- `docs/workflows/wf-framework-charter.md:43` 规定用户工作流只表达顺序工作和显式输入/产物引用，不支持任意代码、插件、开放式 DSL、循环、条件跳转或并发。
- `docs/workflows/wf-framework-design.md:330-340` 只规定定义包含步骤、产物、完成条件、验证和人判点，并允许验证来源来自项目命令或前序步骤建立的命令声明；具体字段编码和命令布局被推迟。
- `docs/workflows/wf-framework-design.md:541` 继续把实际格式和命令帮助留给机制设计/实现方案。

**实际场景**

实现者需要执行一个用户定义步骤时，当前契约没有说明步骤是封闭的操作类型、人工指令、AI 文字说明还是可执行命令引用，也没有规定验证命令的执行边界、输入绑定、输出捕获和未知步骤的拒绝行为。

**影响**

同一份定义可能被不同实现解释为 shell/插件/任意 AI 指令，从而绕过 charter 的能力上限；或者验证命令不可重放，导致实例恢复和验收结果不一致。这个缺口直接影响“同一格式/校验器/执行器”能否保持稳定语义。

**根因判断**

把可变的字段编码与不可变的安全执行边界一起延后到机制设计，导致 charter 的能力上限没有对应的实现级约束。

**最低改进方向**

在机制设计前先固定语义边界：定义允许的有限步骤类型、命令只能引用什么已登记来源、人工/AI/脚本动作的责任边界、输入输出绑定、未知类型和任意代码形态的拒绝规则，并在 §8.2 增加相应正反例。具体字段名和文件布局仍可留给机制设计。

## F3 初报：异种 CLI 审查适配（撤出当前缺陷；后续工作）

**证据**

- `docs/workflows/wf-framework-design.md:454` 要求 reviewer/action 两侧“须加性支持 `--task-id`”，并禁止从嵌套 `review/` 名推断任务身份；未适配前不宣称可用。
- `skills/multi-cli-review/SKILL.md:79-94` 的 task-level 输入只有 `--task-dir`、`--reviewer-id`、`--round`、可选 `--review-focus`，没有 `--task-id`。
- `skills/multi-cli-review-action/SKILL.md:73-80` 的 action-v2 输入只有 `--task-dir`、`--round`、`--force`、`--dry-run`，也没有 `--task-id`。
- reviewer skill 的规范路径是 `{task-dir}/review-round-{N}/{reviewer-id}.md`，而设计稿将 wf 调用路径设为 `{task-dir}/review/review-round-{N}/` 并把 `{task-dir}/review/` 作为参数值；这要求适配层明确“任务根”和“审查根”的关系。

**实际场景**

机制实现按 §6.5 生成命令时，若不从嵌套 `review/` 推断任务 id，就没有现有 CLI 参数可提供报告 frontmatter 的 `task-id`；若直接把 wf 任务目录传给 skill，又会改变设计稿约定的报告路径。

**影响**

在配对 skill 适配完成前，复杂任务审查不能被实现为可用门禁；不同实现可能自行推断任务 id 或改变 canonical path，导致 action-v2 拒收报告、轮次复用或审查结果无法绑定当前任务。

**根因判断**

设计协议先于配套 skill 的参数/路径契约收敛，任务身份来源和审查根目录没有单独建模。

**最低改进方向**

人工先决定任务根与审查根的唯一关系，再在 reviewer/action 两侧同批加入并校验 `--task-id`，或改为由 coordinator 显式提供不会依赖嵌套路径的任务身份来源；同步更新参数表、路径验收和报告元数据检查。适配完成前保留当前“不可用，复杂任务不得正常归档”的门禁。

## F4 / P2：设计期机检器的 authoring/runtime 执行器归属不清（接受）

**证据**

- `docs/workflows/wf-framework-design.md:46` 把“设计期机检”列入框架自有脚本，并要求统一按项目配置 → 全局配置 → 系统 Python 解析。
- `docs/workflows/wf-framework-design.md:539` 和 `.trellis/spec/docs/wf-design-revision-gate.md:24` 又以仓库相对路径 `scripts/validate-wf-design.py`、`python3` 直接运行设计期机检。
- `docs/workflows/wf-framework-charter.md:124` 与 `docs/workflows/wf-framework-design.md:479` 明确 charter/design 属 authoring 文档族，不进入安装清单、不投放目标项目。
- 本仓库 AGENTS 和常用命令使用 `/softwares/python/bin/python3` 运行该 checker；目标项目 `.wf/project-config.json` 的 `python_executable` 并不属于本 authoring checkout。

**实际场景**

authoring 仓库维护者执行 revision gate 时，无法使用目标项目的 `python_executable`；反过来，目标项目运行时也不应看到未安装的 authoring checker。当前文字没有明确这两个脚本集合是否同一套执行器契约。

**影响**

不同维护者可能用不同解释器或错误地读取目标项目配置，造成“统一执行器”声明与实际 gate 命令不一致，审查结果难以复现；实现者也可能把不应投放的设计 checker 当成运行时资产。

**根因判断**

authoring 侧设计/索引机检与目标项目运行时脚本被统称为“框架自有脚本”，没有在资产边界和执行器解析中分层。

**最低改进方向**

明确 `scripts/validate-wf-design.py` 是 authoring-only 工具，使用本仓库规定的解释器和 revision gate；目标项目执行器解析只约束安装、升级、日常入口与运行时 repair/uninstall。若坚持同一契约，则必须说明 checker 的配置来源、投放位置和版本边界，不能同时把它排除在发行资产外。

## 已验证但不构成问题的事项

- `/softwares/python/bin/python3 scripts/validate-wf-design.py` 通过：定义命中率 100%、消费点命中率 100%，引用残差 2 行为信息项。
- 现行 §8.2 三档断言表列数和空字段检查通过；此前的五列行问题已修复。
- charter T1-T7 均有设计稿指针和验收场景；候选/暂不采纳登记路径、Git 分支只读边界、嵌套仓库根例外、审查不可用不得借机降级等上一轮问题已在当前版本中明确。
- 未运行 wf 实现验收，因为当前仓库没有独立 wf 运行实现，且本任务只审查设计契约。
