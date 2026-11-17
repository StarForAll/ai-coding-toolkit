# 激活前的平台与上下文门控

> 这是父子任务共用的操作前置条件，未执行激活。平台必须在**实际实施会话**重新核验，不从任务创建记录、外部审查者平台或持久化“当前平台”句子推断。

## 1. 核验和读取范围

1. 确认用户批准的是最新父design、子工件和交付范围；本轮审查/文档修正不是实施授权。
2. 依据运行时加载的平台/模式说明和项目配置读取对应 `.trellis/workflow.md` 分支；配置只能约束它对应的平台，例如codex.dispatch_mode不能证明当前是Codex，外部文本说ZCode也不能切换本会话平台。
3. 确认启动的是有责任范围的子任务及其依赖已通过；C1独立，C2依赖C1，C3依赖C2。父任务只协调与集成，不直接激活改全包。
4. 先读该子目录的prd/design/implement（C1轻量PRD+实施清单即可），再按其“必读输入”读父共享协议与spec。共享设计是引用依赖，不代表不读取；不得凭父清单或记忆替代子上下文。

不枚举环境变量、不输出凭据/原始会话日志；只需读取平台说明和公开配置键。身份不明、运行时要求与所选分支冲突时停在planning，不能通过 --allow-empty-context 试着激活。

## 2. 匹配分支

| 实际模式 | 启动前条件 | 用户批准后才可执行的命令 |
|---|---|---|
| Codex inline | 运行时和该平台配置都指定inline；主会话不派发agent；JSONL有意为空；trellis-before-dev在主会话读子工件/spec | `/softwares/python/bin/python3 .trellis/scripts/task.py start --allow-empty-context <child-task-path>` |
| DSH inline（本仓库 `dsh.dispatch_mode: inline`） | DSH 运行时加载 `in_progress-inline`/`planning-inline` 横幅；主会话直接实现/检查、不派发子agent；implement/check JSONL 有意为空；以主会话读取子工件/spec 代替 JSONL 注入 | `/softwares/python/bin/python3 .trellis/scripts/task.py start --allow-empty-context <child-task-path>` |
| ZCode/其他 dispatch 平台，或 DSH `dispatch_mode: auto` | 按该平台workflow的1.3，将**该子任务**实现/检查所需spec/research写入implement.jsonl/check.jsonl并验证；父/兄弟清单不能替代；遵守该平台dispatch协议 | `/softwares/python/bin/python3 .trellis/scripts/task.py validate <child-task-path>` 通过后，再 `/softwares/python/bin/python3 .trellis/scripts/task.py start <child-task-path>` |

--allow-empty-context仅确认没有子agent会消费清单，不是绕过必需的dispatch上下文门禁。本任务不改平台配置，也不因审查者平台而派发agent。该门控适用于C1第一次启动和每次后续交接，不只适用于“未来可能换平台”。

## 3. 状态与验证

本仓库当前 DSH 配置为 `dsh.dispatch_mode: inline`（见 `.trellis/config.yaml`），实际 DSH 会话加载 `in_progress-inline` 横幅；四任务的 implement/check 清单（共 8 份 JSONL）仍空是 inline 分支的事实，不是以后 dispatch 会话的启动依据。实施前按上表重新裁定；dispatch session 必须填真实条目，inline session 按约定直接加载，不为跨平台兼容提前改变当前执行模式。

父任务本身在开始最终集成/AC 总账前也必须按同一分支 `task.py start`；planning 状态下产出的集成结果只能作预检，不能作为 AC16 的最终证据。工件校验须确认所有可操作的激活指令只引用本文分支，不留无条件“当前Codex/DSH inline→带豁免启动”的命令；DSH 若被显式配置为 `dispatch_mode: auto`，按 dispatch 行执行，不能沿用 inline 豁免。读入工件的技能、hooks或CLI规则变化时，按实际版本再核分支并记录到相应子validation，不能把这份计划写成未来平台的事实证明。
