# Mobile Game Player Reviewer

通用型“大众玩家手机游戏分析员”源资产。用于把一款手机游戏 APP 的体验信息，
转成普通玩家视角的优劣分析、流失风险判断和可落地改进建议，再按平台格式适配到
Claude Code、OpenCode、Codex。

## Purpose

这个 agent 解决的是“从大众手游玩家视角看，这款游戏哪里好、哪里劝退、应该优先
怎么改”的稳定问题，特别适合：

- 手游立项、Demo、内测、公测或已上线版本的体验复盘
- 分析用户评论、测试反馈、试玩记录或运营复盘中的共性问题
- 判断新手期、成长中期、中后期、付费点、日常压力和移动端体验风险
- 把“玩家觉得不爽”翻译成策划、客户端、数值、运营可以行动的优化建议
- 在竞品参考、付费公平性、抽卡/开箱、FOMO、发热耗电等问题上给出明确风险提示

它不是专业媒体评测、不是开发者自嗨报告，也不是泛泛的游戏聊天助手。它要像一个
真实普通玩家说话，但输出必须服务于游戏改进。

## Source Prompt Assessment

`tmp/大众玩家游戏评论Agent-SystemPrompt.md` 的方向是合适的：

- 角色口吻清楚，能避免“咨询报告腔”
- 覆盖了手游常见体验维度和手机端专项
- 已经把付费公平性、抽卡/开箱和敏感内容作为重点
- 输出结构能直接服务于改进讨论

但作为长期复用的跨 CLI agent，原提示词需要优化：

- 增加证据状态，区分实际游玩、用户提供、公开资料、竞品核验和推测
- 增加信息不足时的降级路径，避免把“初步印象”写成完整评测
- 把平台 wrapper 和工具权限从系统提示词中剥离，放到 `DEPLOYMENT.md` / `TOOLS.md`
- 强化竞品引用规则，避免凭印象乱引用竞品做法
- 强化改进建议格式，要求“改什么、怎么改、成本、影响、优先级”
- 增加跨 CLI 部署说明和字段刷新策略

## When To Use

- 你有一款手机游戏，想知道普通玩家会夸什么、骂什么、哪里最容易流失
- 你有试玩反馈或评论摘录，想整理成产品改进清单
- 你想评估付费设计是否像 Pay-to-Win、Pay-to-Progress 或 Cosmetic-only
- 你想分析抽卡、开箱、保底、限时活动是否制造过强焦虑
- 你想把竞品做法转成适合自己游戏的优化参考
- 你想检查移动端体验：发热、耗电、弱网、推送、单手操作、横竖屏适配

## Input

正式分析建议提供：

- 游戏名称
- 游戏类型
- 游玩平台：iOS / Android / 双端
- 已游玩时长或测试范围
- 当前版本号
- 付费模式
- 重点关注问题
- 可选材料：试玩记录、用户评论、商店链接、竞品名、截图描述、版本更新说明

缺少关键输入时，agent 应输出“初步印象”或“证据缺口清单”，不能假装自己已经玩过。

## Output

根据任务需要，agent 可以输出：

- 总体玩家感受
- 亮点 TOP 5
- 痛点 TOP 5
- 付费公平性判断
- 手机端专项体验判断
- 主要流失风险
- 针对痛点的优化建议
- 优先改进三件事
- 竞品参考和适配判断
- 证据缺口与下一步验证建议

## Evidence Boundary

这个 agent 可以使用用户提供的试玩材料做体验判断；如果要引用当前外部事实，例如
最新版本、商店评分、竞品活动、概率公示、公开评论趋势或平台政策，必须先核验当前
资料。无法核验时标记 `[Evidence Gap]`。

## Source / Deploy Boundary

这里的文件是**源资产层**，不是三平台的直接运行文件。

本仓库中的这个 agent 当前只保留在 `agents/` 目录中，作为跨平台共享设计，
不在当前项目内实际安装到任何平台运行目录。

- 源资产：`agents/mobile-game-player-reviewer/`
- Claude Code 部署目标：`.claude/agents/mobile-game-player-reviewer.md`
- OpenCode 部署目标：`.opencode/agents/mobile-game-player-reviewer.md`
- Codex 部署目标：`.codex/agents/mobile-game-player-reviewer.toml`

部署细节、平台字段、wrapper 模板与刷新策略见 `DEPLOYMENT.md`。

## Files

- `SYSTEM.md`：跨平台共享的核心角色定义
- `TOOLS.md`：抽象权限与禁用操作
- `DEPLOYMENT.md`：跨平台 wrapper 生成与验证指南
- `EXAMPLES/`：调用示例

## Example Coverage

当前示例覆盖：

- `EXAMPLES/input-1.md` / `output-1.md`：基于用户提供的虚构手游试玩信息，输出
  大众玩家视角的体验诊断与改进建议

说明：

- 当前 `EXAMPLES/output-*.md` 是**期望输出格式示例**，用于展示这个 agent 的
  目标报告形态，不代表本仓库内已经真实执行过 live verification。

## Validation Notes

如需把它真正部署到目标项目中的三平台，应至少检查：

- frontmatter / TOML 字段是否与当前平台版本兼容
- 目标平台是否具备 web search / web fetch 或等价能力
- 如果目标任务要分析商店评分、竞品现状、概率公示或最新评论，是否允许实时核验
- 若只做用户提供材料的离线分析，是否接受 `[Evidence Gap]` 覆盖外部事实
- Codex wrapper 是否只使用当前官方支持的自定义 agent 字段
