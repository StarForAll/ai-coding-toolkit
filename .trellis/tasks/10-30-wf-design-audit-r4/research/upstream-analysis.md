# 四个参考项目的机制分析与 wf 吸收评估

审阅日期：2026-10-30。任务：`10-30-wf-design-audit-r4`。这是本地快照的静态研究，不是上游最新版本调查，也不是安装实测或效果评测。参考项目内的 skill 内容仅作研究数据，未执行其中的派发、提交、安装、调度或清理指令。

## 1. 基线与证据范围

| 对象 | 本地 HEAD | 工作区 | 版本/边界 |
|---|---|---|---|
| skills | `59db609eb1e18aaf59b63284d0e52255aff0c63c` | 干净 | 以提交为基线，不推断远端状态 |
| Trellis | `be9e19b269c25cb2787489eb81062bf96619442c` | `.gitignore` 有修改 | CLI 清单标 `0.7.0-beta.4`；上游只读 |
| stop-that-shit | `17ffc9f5108381916f4f9b019d61b759626c4a71` | 5 文件有修改 | HEAD 的 package.json 标 `0.2.5`；本地修改涉及 marketplace、CONTRIBUTING、两个 package.json、release-files.json |
| mcode-stack | `d987793c2945e3455782180989322f6ce37b8363` | 干净 | 以提交为基线，不推断远端状态 |
| 本仓库设计稿 | `925654b1c35a5e3b03c5310a6b72362933c5560f` | 被审三份设计文档无本轮修改 | 初始另有 `.agents/skills/grill-me/`、`skills-lock.json` 未跟踪，保持不动 |

取证方式为 `git rev-parse HEAD`、`git status --short`、文件清单、精确搜索和直接阅读。未拉取远端，未运行四仓库的测试/构建/安装器。MCP 检索工具虽有暴露，但其数据流未确认，依 `mcp-routing` 的数据边界采用本地读取；不向外部服务发送内部路径或仓库内容。没有 AST/图遍历或全仓逐行审计保证。

研究覆盖入口与编排、任务状态、spec、知识治理、验证、长会话和资产生命周期。具体引用均指本轮读到的文件；README 的定位声明与源码可支持的机制分开判断。

## 2. skills：可组合纪律，适合做原语库

**定位与场景。** [README](/home/xzc/projects/other/skills/README.md:17) 明确选择小、可改、可组合的 skills，而不接管整套开发过程。适合人主导的需求澄清、设计、实现、调试与复盘；可用本地 Markdown，也可用 issue tracker。它的 spec 常指待实现的工作规格，不能直接等同 wf 的长期 Code-Spec。

**值得吸收的优点。**

- [setup](/home/xzc/projects/other/skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:19) 先探测已有文件再提问，按真正存在的分支配置；入口已存在就原地更新。对存量项目有用，但其 AGENTS/CLAUDE 写入与 tracker 接入不应照搬。
- [implement](/home/xzc/projects/other/skills/skills/engineering/implement/SKILL.md:7) 很短，把工作纪律交给原语；[code-review](/home/xzc/projects/other/skills/skills/engineering/code-review/SKILL.md:9) 把“符合项目标准”和“实现需求”分开给结论，避免一轴掩盖另一轴。
- [tdd](/home/xzc/projects/other/skills/skills/engineering/tdd/SKILL.md:13) 要求行为测试和逐个垂直切片，明确反对按实现重算期望值的伪测试；[diagnosing-bugs](/home/xzc/projects/other/skills/skills/engineering/diagnosing-bugs/SKILL.md:19) 先建立能暴露本次症状的反馈，再最小化、假设、定向探测和回归。
- [domain-modeling](/home/xzc/projects/other/skills/skills/engineering/domain-modeling/SKILL.md:40) 按需创建术语与决策文档，ADR 只有在难逆转、无背景会意外、确有取舍三个条件同时成立时才建议创建。
- [writing-for-agents](/home/xzc/projects/other/skills/skills/productivity/writing-for-agents/SKILL.md:10) 区分常驻上下文成本与人的认知成本，通过有触发条件的指针渐进加载；强调环境本身也是事实源，不要把可查询配置缓存成第二份规则。
- [retro](/home/xzc/projects/other/skills/skills/engineering/retro/SKILL.md:17) 优先修复真正失效或未接线的自动检查，机械问题交给机械检查，避免每次失败都往说明文档加一句。

**限制与代价。** 文件纪律不能提供持久任务状态机或强门禁；部分入口依赖 tracker、用户配置和其他 skills。`implement` 原文包含提交，code-review 原文派发两个子代理；这些行为不自动得到 wf 的许可。`diagnosing-bugs` 的严格反馈前置对难复现问题成本较高，需保留其“无法建立反馈则明确报告”的出口。in-progress 中的 [chief-of-staff](/home/xzc/projects/other/skills/skills/in-progress/chief-of-staff/SKILL.md:18) 依赖调度与子代理，不应整套吸收；只借其知识 lint。其历史 wiki 保留旧断言的策略也不宜替代 wf 的当前规范与 Git 历史。

**对 wf 的判断。** §1.3、§4.2、§7.4 已吸收调用权、短编排、双轴检查和四原语；§8 已列 setup 问答、ADR、fog of war、知识 lint 等候选。新增价值主要是纠正一次跨层误用：[SCOPE](/home/xzc/projects/other/skills/SCOPE.md:7) 的“真实失败”是上游贡献准入门槛，不适合成为目标项目所有知识的唯一准入条件；详见报告 F5。

## 3. Trellis：长期项目骨架，适合借机制契约

**定位与场景。** [README](/home/xzc/projects/other/Trellis/README.md:43) 与 [workflow](/home/xzc/projects/other/Trellis/packages/cli/src/templates/trellis/workflow.md:7) 围绕持久 specs、task 产物、workspace 记录和跨会话上下文展开，适合新项目建立规范、存量项目补齐规范并长期迭代。多平台、团队与代理协作是其额外产品面，并非 wf 必须具备的能力。

**值得吸收的优点。**

- [brainstorm](/home/xzc/projects/other/Trellis/packages/cli/src/templates/common/skills/brainstorm.md:3) 明确区分建任务与批准最新规划，事实问题先查证；产物写完后先交人审，后续明确批准才允许开工。这比“文件齐了”多一个必要的人判条件。
- [workflow](/home/xzc/projects/other/Trellis/packages/cli/src/templates/trellis/workflow.md:31) 的 index 是加载指针；任务保存 PRD、设计、计划与研究；任务树明确不是依赖系统。wf 已正确把依赖语义归于本仓库两份设计，而没有冒称来自 Trellis。
- [spec_match.py](/home/xzc/projects/other/Trellis/packages/cli/src/templates/trellis/scripts/common/spec_match.py:12) 有界读取 frontmatter、校验相对路径、非法 glob 按条处理；[spec_inject.py](/home/xzc/projects/other/Trellis/packages/cli/src/templates/trellis/scripts/common/spec_inject.py:79) 区分完整内容、提醒与静默，内容改变或上下文重置时重新提供内容。wf 应借纯函数契约，自己写无 hook 的拉取实现。
- [update-spec](/home/xzc/projects/other/Trellis/packages/cli/src/templates/common/skills/update-spec.md:35) 不只记录事故，也记录已实现功能、设计决策、新模式和明确约定。非常契合新项目正向积累。
- [update.ts 的 analyzeChanges](/home/xzc/projects/other/Trellis/packages/cli/src/commands/update.ts:973) 区分新文件、已是新模板、未本地修改但模板更新、本地修改冲突、用户删除；其中 `storedHash`、当前内容、新模板三者各有职责。这是 wf 当前升级三态还没完整表达的部分。
- [manifest-prune](/home/xzc/projects/other/Trellis/packages/cli/src/utils/manifest-prune.ts:1) 纠正旧清单错误吞入用户文件的问题；[对应测试](/home/xzc/projects/other/Trellis/packages/cli/test/utils/manifest-prune.test.ts:43) 有用户自有路径不应被托管的反例。只读确认了测试存在，没有运行它。

**限制与代价。** 平台 hooks、渲染器、会话身份、channel、任务树、分发与迁移链条维护面大。流程纪律与脚本校验不是同一强度：[task.py start](/home/xzc/projects/other/Trellis/packages/cli/src/templates/trellis/scripts/task.py:174) 的实现不能被当作自动证明“人已批准规划”。[uninstall](/home/xzc/projects/other/Trellis/packages/cli/src/commands/uninstall.ts:1) 明确删除整个 `.trellis/`，与 wf 保留用户知识的数据策略不同，不应继承。以上是本地版本观察，不评价其对团队产品是否合理。

**对 wf 的判断。** 可继续吸收的主要是规划许可的明确消费（F2）与升级的三方判据（F6）。持久记录、纯匹配、损坏恢复、用户删除态均已覆盖。没有必要为 wf 引入其平台矩阵、开发者身份或 channel。

**用户补充要求后的专项核实（2026-10-30）。** [spec-bootstrap](/home/xzc/projects/other/Trellis/packages/cli/src/templates/common/bundled-skills/trellis-spec-bootstrap/SKILL.md:11) 的分析步骤列出 GitNexus、ABCoder、语言工具和直接读源码；[repository-analysis](/home/xzc/projects/other/Trellis/packages/cli/src/templates/common/bundled-skills/trellis-spec-bootstrap/references/repository-analysis.md:5) 具体编排图分析与结构分析。[mcp-setup](/home/xzc/projects/other/Trellis/packages/cli/src/templates/common/bundled-skills/trellis-spec-bootstrap/references/mcp-setup.md:3) 自称工具选择、非平台要求，但其 Verification 又要求配置后确认服务可见并查询再写 spec。这可解释用户对工作流依赖工具的顾虑；不构成“所有 spec 更新必须 GitNexus”的证据，常规 update-spec 本身没有该前置。本次只读核对文档，未测试 Trellis 在 MCP 全关时的整体表现。wf 的所有 spec 变更必须走本地完整路径，原语吸收时删除必需的外部 MCP、图服务及建索引前置；具体契约与验收见审查报告 §2.1。

## 4. stop-that-shit：任务边界与停止判断，适合借反例和验收方法

**定位与场景。** [README_EN](/home/xzc/projects/other/stop-that-shit/README_EN.md:34) 针对范围膨胀、无消费者的防御、只审却改、反复验证；产品由建议性的 skill 与依赖宿主集成的 Guard 构成。适合校准一次任务的动作边界，不能替代项目任务和 spec 生命周期。

**值得吸收的优点。**

- [Stop Ladder](/home/xzc/projects/other/stop-that-shit/skills/stop-that-shit/SKILL.md:21) 从当前责任、直接方案、具体缺口、防御实际作用，走到最终证据支持的完成；必要调用方、迁移、兼容和校验仍须做完，绝非“少改文件就好”。
- [任务模式](/home/xzc/projects/other/stop-that-shit/skills/stop-that-shit/SKILL.md:94) 区分 review/answer/monitor 与 change。[decision.cjs](/home/xzc/projects/other/stop-that-shit/src/decision.cjs:106) 对只读模式的写操作返回明确原因和出口；这与 wf 的阻断三要素相容，但 wf 没有 Guard，不能宣称等价拦截。
- [cases](/home/xzc/projects/other/stop-that-shit/cases/README.md:26) 强调最近的正反例只改变决定性事实。[case 模板](/home/xzc/projects/other/stop-that-shit/cases/_template.md:17) 要区分预期判断、决定性证据、下一步和是否真实复现。
- [paired-eval](/home/xzc/projects/other/stop-that-shit/evals/codex-paired/README.md:3) 分开评测指令、加载路由与宿主拦截，授权 Good Case 同样必须通过；框架不能靠“拒绝更多”证明更好，也不能把模型未尝试写入当作机制挡住了写入。

**限制与证据上限。** Guard 有动作分类、宿主适配和存储状态成本；unknown 写操作可能保守拒绝，支持路径以外没有完整保证。[EVIDENCE](/home/xzc/projects/other/stop-that-shit/EVIDENCE.md:467) 仍登记未完成的完整实时矩阵，历史存在 null-effect 和基础设施失效；这份上游自述不构成本轮复测，也不支持“已证明普遍改善模型行为”。

**对 wf 的判断。** 四问、显式停止、最终状态有效证据、诚实分级与正反例已吸收。§8 的 evidence_level、反例三元组和 case-first 均已有候选，不能重报为遗漏。可补的低成本点是把“合法工作必须放行”的成对用例真正放进三个夹具，尤其是共存提交和返工切换；不必引入 Guard、观察态或全平台评测系统。

## 5. mcode-stack：工作习惯与 harness 审计，适合借长期使用成本视角

**定位与场景。** [README](/home/xzc/projects/other/mcode-stack/README.md:16) 按作者 stack 分发日常 skills 与 checklist，覆盖工具、上下文、长会话、审查与实验。适合已经有 agent/开发流程的使用者选择性补纪律；它不是统一项目状态机。

**值得吸收的优点。**

- [handoff-doc](/home/xzc/projects/other/mcode-stack/stacks/ronny/skills/handoff-doc/SKILL.md:15) 先查真实 Git 与测试结果，再写目标、决策理由、当前状态、排除项和下一步；同一交接文档持续更新。
- [long-session-check](/home/xzc/projects/other/mcode-stack/stacks/ronny/skills/long-session-check/SKILL.md:8) 将上下文视为工作台，能重新获取的丢掉、会话过程概括、不能丢的写盘；反复压缩仍漂移时换新会话。wf §4.4 已有完整对应。
- [context-tax-audit](/home/xzc/projects/other/mcode-stack/stacks/ronny/skills/context-tax-audit/SKILL.md:15) 测一条真实请求，问每部分删除会失去什么，并核对频率、精度和加载位置；比单看文档行数更能评价 wf 日常开销。
- [long-command-check](/home/xzc/projects/other/mcode-stack/stacks/ronny/skills/long-command-check/SKILL.md:27) 检查是否重复启动、输出是否截断、完成结果是否读取；wf 只应吸收“命令未结束不能当通过、截断不能当完整证据”，不接管宿主进程运行时。
- [harness-experiment](/home/xzc/projects/other/mcode-stack/stacks/ronny/skills/harness-experiment/SKILL.md:13) 单变量、固定其余输入、看翻转用例与请求/时间/成本，模型升级后复查原有脚手架是否仍有用。
- [lifting-loops](/home/xzc/projects/other/mcode-stack/stacks/jiachen/skills/lifting-loops/SKILL.md:97) 先找真实目标和外部判断信号，优先删除过时规则或修改既有产物，最后才新建 skill；介入减少需和任务结果一起观察，不能把人放弃当改善。

**限制与代价。** 多数审计对象是 agent harness，wf 不控制工具集、缓存、压缩或进程生命期，不能原样变成 wf 必做步骤。lifting-loops 的日志采集、私有 ledger、跨项目数据与定时任务不符合当前框架范围；六角色可作人工评估词汇，无需搬它的系统。另有 [NOTICE](/home/xzc/projects/other/mcode-stack/stacks/ronny/NOTICE.md:3) 说明 engineering 系列材料有 CC-BY 3.0 来源，不能仅凭根 LICENSE 的 MIT 概括所有文件；这里仅记录来源文本，不作法律结论。

**对 wf 的判断。** 交接、三分桶和漂移换会话已经覆盖。§8 已有人工介入分类、脱敏、截断标注等候选。尚可增加的是 authoring/dogfood 的小型成本比较：同一类轻任务用了多少人工确认、多少 wf 命令，是否确实降低接续错误；不是目标项目新门禁。

## 6. 吸收裁决建议（不自动并入正文）

| 候选 | 当前覆盖 | 建议与成本 |
|---|---|---|
| Trellis：批准最新规划才可开工 | 只保留了口号，开工消费条件缺失 | 优先补 F2；沿既有人判留痕，不引入身份系统 |
| Trellis：正向知识也是 spec | 被“真实失败”唯一门槛排除 | 修 F5；更换准入定义，不增加存储体系 |
| Trellis：GitNexus/ABCoder 分析与配置路径 | 不属于 wf 的必需能力；用户明确禁止 spec 操作依赖外部 MCP | 不吸收其必需工具/索引前置；本地读源码、Git 与普通脚本须覆盖完整 spec 变更路径 |
| Trellis：旧基线/本地/新版三方升级 | 三态中没有正常模板更新分支 | 补 F6 的动作表，保留小脚本 |
| skills：小原语、双轴检查、setup 原地更新 | 正文已有 | 保留；不另建同名路由或第二份规范 |
| skills：问答形状、fog、ADR、知识 lint | §8 ①③④⑤已有候选 | 按需要裁决；不再作为新增发现 |
| STS：最近正反例、Good Case 不回归 | 已有反例纪律与三夹具，尚无本轮具体场景 | 把 F1–F4 场景加入现有验收夹具；低成本，无新运行时 |
| STS：证据四级和 case-first | §8 ⑥⑦⑧已有候选 | 可选；先用报告中的“静态证据/推演/实测”说明，不急于加字段 |
| mcode：真实证据交接、长会话三分桶 | §4.4 已有 | 保留，不再加交接产物类 |
| mcode：介入次数与结果配对、单变量试验 | §4.1 有预期介入点；§8 ⑨只有分类，未给比较方法 | 候选 A1：仅在 authoring dogfood 记少量成本与结果，验证轻量任务是否过重 |
| skills + mcode：按实际任务测加载量并剪枝 | 有份额纪律与 spec 预算，无端到端成本样本 | 候选 A2：测 start/continue/check 三个实际样本再剪枝；不因行数直接判坏 |
| Trellis：清单修剪 | §8 ⑰已有 | 实现资产升级时再裁决，不搬平台注册表 |
| hooks、后台定时、团队 tracker、子代理调度 | 明确在边界外 | 不吸收；这些项目拥有它们不构成 wf 需要它们的理由 |

本轮真正应优先做的是修正几条已有规则的组合语义，而非继续增加机制。具体问题、优先级与验证场景见 [审查报告](../review-report.md)。
