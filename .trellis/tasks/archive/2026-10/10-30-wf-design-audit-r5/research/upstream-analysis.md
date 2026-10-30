# 四个参考项目第五轮分析（r5）

取证日期：2026-10-30。四个上游仓库 HEAD 已逐一核对与 wf-framework-design.sources.md 登记的固定提交一致（skills `59db609`、Trellis `be9e19b`、stop-that-shit `17ffc9f`、mcode-stack `d987793`）；stop-that-shit 5 个发行/贡献文件本地有原改、Trellis `.gitignore` 有原改，均不作为固定提交事实。全部为本地快照静态研究，未运行上游测试/安装/评测，不声明远端最新状态。

分析由四路只读子代理执行，本文件为汇总转记；原始结论存子代理输出，行号均指固定提交下的文件。

## 一、四项目快评（使用场景 / 优点 / 缺点）

| 项目 | 使用场景 | 核心优点 | 核心缺点 |
|---|---|---|---|
| skills | 单人日常真实工程的纪律原语库（grilling/tdd/调试/双轴审查/复盘） | 原语极薄、按名互引复用；完成信号可检验；知识载体（glossary/ADR/out-of-scope）惰性创建 | 无跨会话任务状态机（依赖外部 tracker）；子代理并发是默认路径；审查依据是字面引用而非结构化 spec 路由 |
| Trellis | 多平台多开发者的团队工作流框架 | 故障驱动设计（边界处事故注释密度极高）；幂等重试/原子写/失败恢复建模成熟；safe_commit 等小机制解决真实问题 | 会话身份解析是持续维护负担（12 个捏造环境变量名的逐平台审计）；状态机扁平（completed 面包屑死代码）；无用户数据 schema 版本化；uninstall 默认删用户数据 |
| stop-that-shit | 防过度工程/范围膨胀的停止纪律工具（skill + Guard 双层） | 诚实边界声明贯穿始终（deny≠未执行、hostEffect 恒 unobserved）；防误报设计成熟；成对案例与三臂评测归因分离 | 7 宿主适配约 900 行特例契约，维护税极重；实测效果证据为空（多次 pilot null-effect）；并发/锁/恢复机制远超单人需要 |
| mcode-stack | 团队成员按"时刻"取用的日常 skill 合集，每 stack 即插件包 | skill/清单/笔记三形态同源；清单双源反查使清单漂移机器可检；贡献门槛绑定真实使用 | stack 纯纪律无持久化（无任务状态/跨会话账本）；check 只核结构不核语义；lifting-loops 依赖私有数据与定时任务 |

## 二、第五轮新识别的未吸收点（按项目）

### skills（10 项，均低成本纪律形状）

| # | 来源 | 机制 | 增益初衷 | 成本 |
|---|---|---|---|---|
| S1 | `SKILL-MECHANICS.md:9-14` | user-invoked skill 的 description 降为人面向一行摘要、剥离触发词 | 单任务可控 | 一句纪律 |
| S2 | 同上 + `writing-for-agents:12-18` | model-invoked description 按一分支一触发词、首词前置修剪（永驻上下文负载） | 单人长期 | 一句 |
| S3 | `diagnosing-bugs:57-66` | 完成信号属性化（可红/确定/快/可无人跑）+ 已实际跑过一次并出示输出 | 单任务可控 | 低 |
| S4 | `grilling:13-24` | 每题编号+标题+推荐答案，问题措辞使"yes"即接受推荐 | 单任务可控 | 两行 |
| S5 | `wayfinder:75` | HITL 边界句：模型不得代人作答人判侧 | 单任务可控 | 一句 |
| S6 | `retro:19` | 复盘"能机械化的造确定性检查、不写散文 spec"分流 | spec 沉淀 | 一句 |
| S7 | `GLOSSARY.md` 全文 | 术语表作为知识类型（`_Avoid_` 别名、只收本项目概念） | 长期+沉淀 | 较高（新资产类，须按第 0 章登记；可先作 spec 的一个约定族起步） |
| S8 | `handoff:10-12` | 交接记录含"下一会话入口"字段与不复制已有产物的去重义务 | 跨 CLI 接续 | 两字段 |
| S9 | `triage/OUT-OF-SCOPE.md:68,81-84` | 拒绝项区分"真拒绝 vs 搁置"（durable 判据）；重提追加进旧文件 Prior requests | spec 沉淀 | 两行 |
| S10 | `writing-for-agents:74` | 否定句失效纪律：禁令句把被禁行为拖入上下文，应正面表述 | 单任务可控 | 中（正文句式修订；至少进 skill 编写纪律） |

### Trellis（高性价比 6 项 + 验收 1 项 + 表述风险 1 项）

| # | 来源 | 机制 | 增益 | 成本 |
|---|---|---|---|---|
| T1 | `task_store.py:1322-1337` | 归档/跨任务动作**先查全部目标碰撞再开始突变**（Trellis 教训：先改状态后发现冲突需手工撤销） | 单任务可控/恢复 | 低：一条前置检查排序规则 |
| T2 | `add_session.py:16-31,481-520` | 记录级幂等指纹标记（输入派生指纹，重入按四态分类只补缺口） | 长期/恢复 | 中：机制设计补一节 |
| T3 | `spec_inject.py:82-85` | **截断的读取不算已读**：被截断的 FULL 记录不得发"已看过" ticket——侧车哈希相同不代表内容完整装入 | spec 沉淀 | 低：留痕字段加 complete 标志 |
| T4 | `types.py:19-22` | **写回必须用原始 dict 保留未知字段**（TypedDict 仅作读注解）——wf §5.3 只规定了读语义，写路径未约束 | 长期/schema 演进 | 一句写者纪律 |
| T5 | `spec_match.py:17,156,174-180` | frontmatter 容错细节：头部读取上限（16KiB/200 行）、BOM 容忍、`---` 后无已知键视为水平线（散文不算畸形） | 新建/存量皆可 | 低 |
| T6 | `safe_commit.py:20-30` | 警告输出内嵌负面示例（"DO NOT use git add -f"）——防 AI 从日志重造事故 | 单任务可控 | 极低 |
| T7 | `workflow.md:108-127` | required 步骤 enforcement 不变量测试（每个 `[required·once]` 步骤须有对应 enforcement 行；Trellis 两个真实跳步事故源于此缺口） | 验收 | 低-中：一条验收断言 |
| T8 | `spec_match.py:255-262` | **表述风险**：wf §6.1"拒绝无法识别形状"若被实现者读成 allow-list 会拒真实路径；Trellis 是 deny-list（仅拒绝对路径/`..`/反斜杠/控制字符） | 存量可用 | 低：改为枚举拒绝条件 |

### stop-that-shit（8 项）

| # | 来源 | 机制 | 增益 | 成本 |
|---|---|---|---|---|
| ST1 | `decision.cjs:12-14,104-141` | 四级判定结果：allow / deny_and_explain / **report_and_defer** / **require_user_approval**——机器不能定夺时输出"需人批准"而非硬拒 | 强度如实/防噪音 | 低：门禁输出加两档 |
| ST2 | `decision.cjs:80-224` | 判定固定优先级短路 + 唯一主因码（一次输出一个 reasonCode） | 可测试/不刷屏 | 低：定义检查顺序表 |
| ST3 | `SKILL.md:88-90` | 调查任务"零交付"Check 时点断言（空 touch_paths 任务未改业务文件）——经核 §4.2 Check 逐路径比对已覆盖语义，**场景表已含**"越界继续执行"反例，此项判为已覆盖 | — | — |
| ST4 | `evals/proof-stop/case.json:8-28` | proof=focused 结构化验证停止条件（定向测试 ≤2 次、项目级套件 0 次） | 防任务打转 | 中：复杂任务 PRD 可选字段 |
| ST5 | `ARCHITECTURE.md:200-203` | 审计/留痕写失败不改变门禁判定（audit fail-open，控制面 fail-closed 分离） | 一致性 | 一行 |
| ST6 | `HOST-ADAPTER-CONTRACT.md:69-81` | "通过=不加约束而非授权"措辞契约（不改全局设置使任务通过） | 授权边界 | 低 |
| ST7 | `EVIDENCE.md:25-30,443-465` | 验收材料按 defensible claim 组织 + 空结果照记 | 验收诚实 | 低：报告模板约定 |
| ST8 | `evals/codex-paired/README.md:31-40` | dogfood 三臂归因分离（含 instruction-only 对照臂，防把人的纪律归功于框架） | 真实使用观察 | 中：入候选清单 |

### mcode-stack（7 项）

| # | 来源 | 机制 | 增益 | 成本 |
|---|---|---|---|---|
| M1 | `independent-review/SKILL.md:15-31,66-74` | 三输入极简审查输入集（reviewer 只拿 diff+需求+测试结果，不继承作者会话/自评）+ 拒绝发现留痕（"下次不再重提"） | spec 沉淀/单任务可控 | 低：§6.5 增两三句 |
| M2 | `jiachen/WORKFLOW.md:12-16`（标注 Draft） | 计划开放决策"编号+推荐项+一遍批量答"；可逆细节 agent 自决并终报列出 | 降人工介入轮次 | 低 |
| M3 | `jiachen/WORKFLOW.md:18-23`（Draft） | 结论带 verified/inferred 标记 + 会推翻自己的证伪检查（非自判检查优先） | 诊断质量/spec 沉淀 | 中 |
| M4 | `lifting-loops/SKILL.md:105-113` | 人工介入"角色→出口阶梯"（删过时规则 > 改既有 artifact > 机械检查 > 新 skill > …；加一行先删一行） | spec 沉淀（与 §4.4 最低成本修复同构，提供可操作排序） | 低 |
| M5 | `lifting-loops/SKILL.md:76,103` | 干预计数必须配对独立结果信号（防"用户放弃"冒充改善） | 长期 | 低 |
| M6 | `engineering-emergency-changes/SKILL.md:14-31,44` | 紧急变更资格闸门（"什么不算紧急"反清单）+ 事后立即立案防丢 | 防紧迫感通胀绕门禁 | 低 |
| M7 | `scripts/check.mjs:146-155` | 清单双源一致性反查（汇总层 description 与组件定义强制一致，禁止两处写） | 发行管理 | 低：validate 脚本加一条 |

### 已声明"不吸收"项的理由核验结论

- Trellis hooks/会话身份/团队 workspace/平台矩阵/分发 CLI/双存储账本、spec-bootstrap MCP 依赖：**全部站得住**（`active_task.py:37-127` 的环境变量审计即会话身份维护税的直接证据；spec-bootstrap 正文"direct source reads"本就是并列主路径）。
- STS Guard/宿主拦截：**站得住且获其自身证据反向支持**（deny≠未执行、拦截需 4 个宿主前置、7 适配器税、pilot null-effect）。
- mcode 缓存/压缩/后台进程/定时采集：**全部站得住**（context-tax 针对 prompt 组装者、long-command-check 开篇"For people building agents"）。
- skills 子代理并发、tracker 状态机、HTML 报告、wizard 生成器：合理未吸收。

## 三、与 r3/r4 已吸收清单的去重

r4 报告 §4 与 r3 报告 C 节已裁决/登记的项（STS 显式文件范围思想、mcode 版本递增思想、入口速查表、update.ts 三方升级形状、spec_match 特异性排序、spec_inject sha/截断语义、manifest-prune、userDeletedFiles 尊重删除、rename-dir 方向判定、脱敏、提交消息形状、截断标注 incomplete、writer-for-agents 写作纪律、to-tickets 垂直切片/expand-contract、ADR 三条件、六角色 dogfood 候选等）在本轮不重复列为新发现。本文件第二节的项均为 r3/r4 未点名或未充分展开的增量。
