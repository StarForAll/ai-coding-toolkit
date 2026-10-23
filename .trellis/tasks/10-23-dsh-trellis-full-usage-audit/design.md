# 技术设计：dsh-trellis 对等性全面验证

## 验证边界

| 边界 | 权威对象 | 处理方式 |
| --- | --- | --- |
| DSH 插件运行时 | `/home/xzc/.dsh/profiles/*/node_modules/dsh-trellis` 中实际安装的包 | 先枚举 profile 和安装形态；隔离测试 profile 使用安装副本的精确快照，不以仓库源码替代被测对象 |
| 插件源码 | `dsh-plugins/dsh-trellis/` | 用于解释安装态结果、检查测试覆盖、验证源与安装包差异；不在审计阶段修改 |
| DSH 宿主 | 当前 `dsh` 可执行文件及其安装的 Cordis/命令/工具事件包 | 以当前版本的实际事件、payload 和 CLI 调用验证插件订阅契约 |
| Trellis | 当前 `trellis` CLI 以及 `/home/xzc/projects/other/Trellis` | 在 `/tmp` 新建项目；上游只读，记录版本、HEAD 和工作树状态 |
| Codex 基线 | 当前仓库/临时项目的 `.codex` hooks 与隔离 `CODEX_HOME` | 仅作为一条对照臂；用实际 hook 调用或可复核 payload，不把 Codex 行为当作 DSH 可行性的唯一依据 |
| 临时产物 | `/tmp/dsh-trellis-full-usage-audit-1023/` | 放置新 Trellis 项目、隔离 DSH/Codex 配置、事件日志和证据；不复制凭据 |
| 任务交付物 | `.trellis/tasks/10-23-dsh-trellis-full-usage-audit/` | 保存 PRD、设计、执行清单、报告和证据索引；仅任务文档允许在审计阶段写入 |

## 证据等级

- **R1：宿主运行证据**。通过当前 DSH 真实 CLI、实际安装插件和新建临时项目执行；优先用确定性本地模型驱动真实工具调用，日志保留事件、工具输入/结果与状态变化。不得把模型自然语言自述作为断言依据。
- **R2：宿主契约验证**。对当前已安装 DSH API/事件进行最小调用，验证 hook payload、deny/allow、追加上下文、session/subagent lifecycle 等实际形状。明确区分真实 DSH 事件与测试 harness。
- **R3：Codex 对照**。在隔离配置下调用真实 hook 或 Codex CLI；逐项记录是否运行真实模型。若 hook trust 或非交互入口阻止调用，说明限制并以 hook 本身和 payload 运行作补偿。
- **R4：静态机制核对**。对照 Trellis 当前上游模板/脚本/config、DSH 宿主当前 API、插件源码与安装包。只证明代码契约，不能单独证明运行效果。
- **R5：自动化测试**。运行插件测试及必要的兼容性测试；测试通过只证明其覆盖范围，不能替代 R1/R2。

## 执行架构

1. 在 `/tmp` 通过当前 Trellis CLI 创建一个新的 DSH+Codex 双接线目标项目，记录初始化命令和生成结果；先查 `trellis init --help`，不假设 flags 或默认值。
2. 从真实已安装插件副本构造隔离 DSH profile，并另建不加载该插件的 bare profile。测试前后核对版本、关键文件哈希和 profile 插件清单，避免安装态漂移。
3. 通过真实 DSH headless/Web 可用入口运行测试。首选本地确定性模型或请求夹具；由其发出实际工具调用，使 DSH 插件事件、Trellis 脚本和工具结果完整经过宿主。若当前环境不能提供这种驱动方式，不以直接调用插件函数冒充宿主验证。
4. 使用同一临时项目的数据状态比较 bare DSH、DSH+插件和 Codex：按会话隔离副本或重建 fixture，避免一条测试的 `.trellis/.runtime` 状态污染另一条。
5. 对关键场景至少重复一次，并在报告中保留原始事件/输出；并发、压缩、热更新等场景只在可安全、确定性复现时执行，否则明确给出降级证据等级。
6. 将差异归为：插件可修、DSH 宿主限制、Trellis 上游限制、部署/配置覆盖、双方共同边界、已接受设计差异或无问题。每一项必须说明用户影响，避免只依据实现不同判缺陷。

## 验证矩阵

| 领域 | 主要验证点 | 对照和判据 |
| --- | --- | --- |
| 安装与加载 | 实际 profile、安装形态、版本、插件开关、依赖宿主版本、安装副本与源码一致性 | 若版本/副本不同，所有结论绑定实际被测副本；不把源码测试结果外推到不同安装版本 |
| 初始化与 workflow 状态 | fresh `trellis init`、新会话 bootstrap、每轮状态、no_task/planning/in_progress/completed/stale/task_error/custom、无 Trellis 目录、skip keyword、状态去重和恢复 | 比较 Trellis 生成内容、bare DSH pull、插件注入及 Codex hook 输出；用文件与事件确认状态 |
| Spec policy | 默认配置、paths 匹配、read/edit/write 工具、deny-once 内容、重试、子目录、刷新/限制、坏状态、进程重启、并发、clear/compact | 同一临时 spec 和工具调用分别经过 DSH bare、插件 pre/post hooks、Codex hook；区分 DSH 事件能做的注入阶段差异 |
| 子代理 | role 识别、`Active task:` 优先级、角色 skill 与 curated context、child-pull 兼容、无任务 guard、generic child、background wait/invalid id/settlement notice | 用实际 parent/child lifecycle 及可读子代理请求验证，不以注册工具或单测代替 |
| 会话身份与生命周期 | `task.py current` 指针、嵌套 shell、不同会话隔离、resume、新进程恢复、compaction/clear 重教学 | 通过 CLI 输出和 `.trellis/.runtime` 状态核验；标明 projection 是否依赖 session event replay |
| 命令面 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 的真实交互入口、参数拒绝、非项目提示；headless 纯文本是否路由 | 交互命令处理器结果与普通模型 prompt 分开判定；无法启动 UI 时只把 handler 直调标为 R2 |
| 配置与运维 | 运行时开关、settings 保存/重载、版本检查、冲突检测、冲突提示、Trellis update 后存活 | 无 GUI 时不把代码/单测写成 UI 已验证；报告真实入口限制和替代证据 |
| 上游/宿主契约 | Trellis 任务、workflow、spec 注入、DSH skills/subagent 协议；DSH 当前 Cordis events、tool schemas、命令路由和 compaction 事件 | 发现上游文本过期只记录事实；不修改上游或其部署文档 |

## 修复闸门与回滚

- 第一阶段只读系统/源码，加上 `/tmp` fixture 与本任务报告写入；不得改插件、Codex/DSH/Trellis 源码或用户 profile。
- 向用户交付完整问题清单和逐项执行方案后停止。用户确认每个问题及方案后，才在本任务内修复已确认项；用户拒绝或要求调整时先更新计划，不执行未确认项。
- 候选方案注明修改文件、配置/安装影响、测试、回滚方式和是否需要重启 DSH。上游 Trellis 永远不改。

## 关键风险与限制

- DSH 交互式 Web/TUI、headless、mock model 入口可能有不同命令与事件路径；每类结论标明实际入口。
- 本地 mock model 能验证宿主集成和真实工具调用，但不能证明模型服从性；需要区分模型效果与插件事件效果。
- compaction、跨进程 resume、并发可能受测试入口能力限制；不可复现时给出明确的 R2/R4/R5 证据边界。
- 隔离 profile 不复制认证文件；不调用付费远端模型，不将私有代码传出本机。
- 当前发现的历史/未跟踪盘点文档版本与当前安装包不同；报告以本次重新读取的包、运行时和上游 commit 为准。
