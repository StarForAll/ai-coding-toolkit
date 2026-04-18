# brainstorm: absorb workflow strengths from browser_bookmark_cleaner_rchiver

## Goal

分析并吸收目标项目 `/ops/projects/personal/browser_bookmark_cleaner_rchiver` 隐藏目录中的实际工作流优点，映射到当前仓库 `docs/workflows/新项目开发工作流/` 的源工作流中。在任何具体修改前，先基于真实嵌入结果做对比分析，输出优点清单、修改方案、受影响文件面和防漂移修正策略，并等待用户确认。

## What I already know

- 用户要求只在 `docs/workflows/新项目开发工作流/` 范围内规划修改，不直接改目标项目。
- 目标项目的工作流位于目标项目根目录下的隐藏目录。
- 需要先在 `/tmp` 创建临时项目，执行 `trellis init`，再将当前 workflow 嵌入该临时项目，以便和目标项目的实际落地工作流对比。
- 当前 workflow 的核心源文件集中在 `docs/workflows/新项目开发工作流/`，其中包括：
  - `工作流总纲.md`
  - `命令映射.md`
  - `CLI原生适配边界矩阵.md`
  - `多CLI通用新项目完整流程演练.md`
  - `完整流程演练.md`
  - `工作流全局流转说明（通俗版）.md`
  - `阶段状态机与强门禁协议.md`
  - `commands/install-workflow.py`
  - `commands/workflow_assets.py`
  - `commands/test_workflow_installers.py`
- 当前 workflow 已明确主适配范围是 Claude Code / OpenCode / Codex，且强调原生载体差异：
  - Claude / OpenCode 以项目命令目录为主
  - Codex 以 `AGENTS.md + hooks + skills + subagents` 为主
- 当前仓库已有传播要求与防漂移要求，特别是阶段门禁和 workflow 规则修改需要同步检查 walkthrough、命令映射、CLI README、shell helper、测试和思维导图等文件。

## Assumptions (temporary)

- 目标项目隐藏目录中的工作流是长期真实使用产物，包含比当前源工作流更成熟或更实战的部分约束、入口设计或运行习惯。
- 目标项目中可通过读取隐藏目录结构与文件内容直接提炼优点，无需运行其完整业务项目。
- 本次先做分析与方案，不进入具体文件修改。

## Open Questions

- 暂无阻塞性用户问题；先通过对比分析提炼优点与修改方案，再向用户确认是否进入修改。

## Requirements (evolving)

- 分析目标项目隐藏目录中的 workflow 资产与实际承载方式。
- 在 `/tmp` 创建纯净临时项目，执行 `trellis init`，再安装当前仓库 `docs/workflows/新项目开发工作流/` 进行对比。
- 站在实际开发实践角度提炼“值得吸收”的优点，而不是机械复制。
- 给出适配 Claude Code / Codex / OpenCode 官方原生格式的改造方案。
- 明确所有拟修改文件都限制在 `docs/workflows/新项目开发工作流/` 内，并说明如何避免传播遗漏与数据漂移。
- 在具体修改前，必须先向用户汇报优点分析、修改方案、影响面和修正方法，并等待确认。

## Acceptance Criteria (evolving)

- [ ] 给出目标项目 workflow 的优势点分析，包含来源依据。
- [ ] 给出基于 `/tmp` 临时项目嵌入结果的差异分析。
- [ ] 给出当前 workflow 可吸收的修改方案，明确推荐项与不建议项。
- [ ] 给出受影响文件面与防漂移同步策略。
- [ ] 在未获确认前不实施具体修改。

## Definition of Done (team quality bar)

- 分析结论基于实际文件与落地产物，不靠记忆猜测。
- 涉及 CLI 适配的建议能映射到 Claude Code / OpenCode / Codex 原生承载方式。
- 影响面和验证思路明确，可直接作为后续修改输入。

## Out of Scope (explicit)

- 直接修改目标项目中的任何文件。
- 在未确认前修改 `docs/workflows/新项目开发工作流/`。
- 扩散到 `docs/workflows/新项目开发工作流/` 以外的当前仓库其他目录。

## Technical Notes

- 初步关键文件：
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/命令映射.md`
  - `docs/workflows/新项目开发工作流/CLI原生适配边界矩阵.md`
  - `docs/workflows/新项目开发工作流/阶段状态机与强门禁协议.md`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py`
  - `docs/workflows/新项目开发工作流/commands/workflow_assets.py`
  - `docs/workflows/新项目开发工作流/commands/test_workflow_installers.py`
- 需要补充读取：
  - 目标项目隐藏目录中的 workflow 命令、skills、AGENTS、hooks、任务状态载体
  - `/tmp` 临时项目经过 `trellis init` 与 workflow 嵌入后的实际文件布局
- 需要重点比对：
  - 阶段入口与日常开发摩擦点
  - 命令/skills/AGENTS 的官方原生承载边界
  - 状态机、恢复、升级、验证、最小可执行路径
  - 文档传播面与安装器/测试是否足够约束防漂移

## Research Notes

### `/tmp` 纯净基线 + 当前 workflow 嵌入结果

- 已在 `/tmp/trellis-workflow-compare.05ajFr` 执行：
  - `git init -b main`
  - 配置双 push URL 的 `origin`
  - `trellis init --claude --opencode --codex -y -u xzc`
  - `docs/workflows/新项目开发工作流/commands/install-workflow.py --project-root /tmp/trellis-workflow-compare.05ajFr`
- 当前 source workflow 成功落地到：
  - `.claude/commands/trellis/*.md`
  - `.opencode/commands/trellis/*.md`
  - `.agents/skills/*/SKILL.md`
  - `.codex/skills/*/SKILL.md`
  - `.trellis/scripts/workflow/*.py`
  - `AGENTS.md` 的 NL 路由块
- 但安装后 `.trellis/workflow.md` 仍保持 Trellis 基线式写法，未被当前 source workflow 项目化增强。

### 目标项目隐藏目录中确认到的“实战化优点”

1. **关闭前验证矩阵被真正冻结并落盘**
   - 目标项目的 `finish-work` 已把“frozen verification matrix”作为第一性概念，而不是只提醒“自行定义真实命令”。
   - 真实任务产物 `finish-work-checklist.md` 以表格记录命令、方法、结果和备注，且允许如实写 `pass / fail / not run / deferred`。

2. **close-out 产物契约比当前 source workflow 更具体**
   - 目标项目中，`finish-work-checklist.md`、`delivery/acceptance.md`、`delivery/deliverables.md`、`delivery/transfer-checklist.md`、`delivery/retrospective.md` 形成稳定的收尾产物包。
   - `acceptance.md` 还会显式写明 acceptance gate、阻塞项和离进入 record-session 还差什么。

3. **父子任务同步要求在真实工作流入口文档里更清楚**
   - 目标项目 `.trellis/workflow.md` 明确规定：完成当前 child task 不代表自动授权下一个 child task，归档/完成 child task 后要同步 parent 的 frontier、notes、task_plan 摘要。
   - 当前 source workflow 在命令/总纲里提到过 child task，但没有把这些实战规则传播到安装后目标项目一定会读的 `.trellis/workflow.md`。

4. **Trellis 相关变更的“隐藏目录联动同步”被显式提醒**
   - 目标项目 `.trellis/workflow.md` 和 `finish-work` 都明确提醒：Trellis 相关变更不能只改 `.trellis/`，还要同步 `.claude/`、`.opencode/`、`.agents/skills/`、`.codex/` 等当前入口目录。
   - 这对避免“源文件改了，实际入口没跟上”的数据漂移很有价值。

5. **收尾分为 commit 前 / commit 后两段，职责更清楚**
   - 目标项目 `.trellis/workflow.md` 把 `finish-work` 和 `archive + record-session-helper` 明确分成两个阶段，实践上降低了“以为 finish-work 做完就算收尾完成”的误解。

### 不应直接吸收的目标项目差异

- 目标项目当前安装记录是 `workflow_version = 1.1.19`，反而比当前 source workflow `0.1.24` 的安装契约更旧，缺少 `project-audit`、`workflow-state.py`、`ownership-proof-validate.py` 等新资产；这些不是优点，不应回退。
- 目标项目真实任务里存在部分旧布局，如某些 `review-gate` 记录落在 `check/` 下；当前 source workflow 已标准化为 `$TASK_DIR/review-gate/`，不应倒退回混合布局。
- 目标项目的 close-out 顺序采用“archive 后 record-session-helper”的项目化做法，但当前 source workflow 已在 `delivery.md`、测试和 learn 文档中明确固化为“先 record-session，再 archive”；若要改这条链路，属于更高风险的契约调整，不建议在本次吸收中顺手改动。

### Spec 内容筛选结论

#### 已读取且有代表性的目标项目 spec

- `.trellis/spec/frontend/quality-guidelines.md`
- `.trellis/spec/universal-domains/verification/evidence-requirements/normative-rules.md`
- `.trellis/spec/universal-domains/product-and-requirements/prd-documentation/normative-rules.md`
- `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-developer-facing/normative-rules.md`
- `.trellis/spec/scenarios/discovery-and-planning/solution-comparison/normative-rules.md`
- `.trellis/spec/universal-domains/architecture/system-boundaries/normative-rules.md`

#### 已被当前 workflow 等价覆盖，原则上不单独再吸收

1. **证据先于断言**
   - 目标项目 `evidence-requirements` 的规则，与当前 workflow 已有的 `pass / fail / not run`、`[Evidence Gap]`、不得伪造验证结论基本等价。
   - 当前 source workflow 在 `工作流总纲.md`、`check.md`、`delivery.md`、walkthrough 中已明确覆盖。

2. **双 PRD / 需求基线分层**
   - 目标项目关于 `customer-facing` / `developer-facing` PRD 的 shared facts、scope、assumptions、open questions 规则，当前 workflow 已通过 `brainstorm/design/总纲/状态机` 的正式文档边界表达覆盖，而且当前 source workflow更细。

3. **项目级粗估、需求澄清、边界条件**
   - 目标项目 universal-domains 的 requirement / scope 规则，当前 workflow 已落到 `customer-facing-prd.md`、`task_dir/prd.md`、`developer-facing-prd.md` 的阶段门禁里。

4. **“冻结验证矩阵 + child task 串行 + parent record sync” 作为理念**
   - 当前 source workflow 的命令、总纲、walkthrough 已有，但目标项目 `.trellis/workflow.md` 的表达更接地气；这里更适合通过 workflow 文档增强来补，不需要直接复制 spec 文件。

#### 可以少量吸收的通用有效点

1. **方案对比的“无可信备选时也要显式说明”**
   - 目标项目 `solution-comparison` 里有一条很实用：若没有可信替代方案，不要伪造比较，而要明确写“当前无可比方案”。
   - 当前 source workflow 的 `design` 已要求给多个候选，但对“确实只有一个可信方向”的合法情况表达不够硬，适合补到 `design.md` 与 `brainstorm.md`。

2. **设计阶段显式声明系统边界 / 外部依赖 / 责任边界**
   - 目标项目 `system-boundaries` 里的几条规则是跨项目通用的：
     - 识别外部依赖与主要边界穿越
     - 在责任变更处标注 ownership
     - 不默认把外部系统当成可靠/可控
   - 当前 source workflow 在 `工作流总纲.md` 已有“系统边界”概念，但在 `design.md` 的明确输出要求里不够硬，可补成设计检查项或设计文档最小必选字段。

3. **开发向 PRD 的最小章节要求中，可借鉴“依赖与约束 / 接口与集成 / 错误处理与边界情况”的显式列名**
   - 当前 workflow 已要求技术架构确认后生成 `developer-facing-prd.md`，但可以更明确规定这些章节必须可定位，而不是只在总纲里高层提到。
   - 这适合补到 `design.md` / walkthrough / 命令映射，不需要搬运目标项目整个 developer-facing PRD 规范正文。

### Candidate Approaches

**Approach A: 文档/命令契约增强，不触碰安装到目标项目的 `.trellis/workflow.md`**  
(风险低，收益中等)

- 强化 `commands/finish-work-patch-projectization.md`、`commands/delivery.md`、`工作流总纲.md`、walkthrough 文档
- 明确 `finish-work-checklist.md` / `delivery/*` 产物契约
- 保持安装器行为不变

Pros:
- 不新增安装器 patch 点，兼容风险低
- 主要是 source docs 与命令契约补强

Cons:
- 新装目标项目仍看不到 `.trellis/workflow.md` 里的实战化提醒
- 一线使用者还是更可能先读到旧 baseline workflow 文档

**Approach B: 在 A 的基础上，引入 `.trellis/workflow.md` 的项目化补丁源资产**  
(推荐)

- 除了强化现有源文档，还新增/扩展安装器，使其把“冻结验证矩阵 / 父子任务同步 / Trellis 隐藏目录联动 / close-out 双阶段说明”补进目标项目 `.trellis/workflow.md`
- 同步补齐 `install-workflow.py`、`upgrade-compat.py`、`uninstall-workflow.py`、`workflow_assets.py`、安装器测试

Pros:
- `/tmp` 新装项目也能直接继承实战化 workflow 说明
- 解决“源文档很强，但目标项目第一入口还是弱 baseline”的落差

Cons:
- 需要新增一个 baseline patch 类资产，安装/升级/卸载/测试链都要改
- 需要谨慎设计 patch marker，避免 Trellis 升级后 anchor 脆弱

**Approach C: 只提炼为 learn/经验文档，不改正式契约**  
(不推荐)

Pros:
- 变更面最小

Cons:
- 无法真正减少新项目安装后的使用摩擦
- 优点继续停留在“知道的人会用”的隐性经验
