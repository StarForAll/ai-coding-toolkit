# Market Signal Framework

日期：2026-05-13

## Refresh Trigger

以下任一情况出现时，应重新核验或调整本研究：

1. 距离本次核验超过 90 天
2. 目标 agent 的主要判断场景发生明显变化，例如从“个人产品前景”扩展到
   受监管行业或强线下渠道市场
3. 主要信号源的产品形态或可用性发生变化
4. 实际使用中反复发现某类信号权重明显失真，需要修正判断框架

## Purpose

为“个人产品市场前景调研 agent”定义一个默认的实时证据采集框架，确保它在分析
“当前市场是否有前景”时，不会只靠静态印象下结论。

## Source Baseline

### Official references checked

- Google Trends home: `https://trends.google.com/home`
- Google Trends help:
  `https://support.google.com/trends/answer/6248105?hl=en`
- Google Trends related searches help:
  `https://support.google.com/trends/answer/4355000?hl=en`

### Scope Boundary

本研究当前只正式核验了“需求趋势信号”中的 Google Trends 官方能力说明。

正文提到的 Reddit、Hacker News、独立开发者社区、竞品目录与评论站点，
在本文件里目前属于**方法框架建议**，还不是逐一验证过的可用性基线。

如果后续要把它们升级为“默认强依赖来源”，应补一轮来源可用性与覆盖范围核验。

### What these official pages confirm

- 可以按地区查看热门搜索与趋势
- 可以在 Explore 中比较多个词
- 可以查看 related searches
- “Rising searches” 代表增长最快的相关搜索

这意味着：

- Google Trends 适合作为**需求变化信号**的一部分
- 但它不是单独的“市场前景定论工具”，必须与竞争、变现、分发、用户反馈一起看

## Recommended Live Evidence Buckets

对于“这个产品在当前时间是否有市场前景”，默认至少检查以下 5 类信号：

### 1. Demand Signals

- 搜索热度是否存在明显需求或增长
- 相关关键词是否出现 rising / breakout
- 用户是否在社区、论坛、社媒中持续表达相似问题
- 用户表达的是“想法兴趣”还是“明确痛点”

优先来源：

- Google Trends
- 搜索结果页
- 目标用户社区（如 Reddit、Hacker News、独立开发者社区、垂直论坛）
- 用户公开问答与讨论串

### 2. Competition Signals

- 是否已经有足够多的直接竞品
- 竞品最近是否仍在更新、发布、获客
- 竞品是“很多但弱”，还是“少但很强”
- 竞品是否已经把核心价值主张教育完市场

优先来源：

- 竞品官网
- 定价页
- 更新日志 / 发布日志
- 产品目录 / 发布平台
- 评测与案例文章

### 3. Monetization Signals

- 用户是否已经习惯为该类问题付费
- 市场里是否存在可比付费方案
- 定价带是否有空间
- 免费工具是否强到足以压缩付费空间

优先来源：

- 竞品 pricing pages
- 用户评论中的付费抱怨 / 价值感反馈
- 购买页、套餐页、退款/限制说明

### 4. Distribution Signals

- 这个产品能否在当前渠道低成本触达目标用户
- 获取流量是否高度依赖单一平台
- SEO / 社媒 / 社区 / 商店等渠道是否已明显拥挤
- 是否存在自然的传播机制或复利渠道

优先来源：

- 搜索结果竞争态势
- 社媒与社区讨论活跃度
- 产品发布目录
- 内容生态密度

### 5. Timing / Constraint Signals

- 是否受到平台政策、监管、API 变动、AI 成本变化影响
- 当前时间点是否因为宏观变化而放大或削弱需求
- 目标市场是否已经被新一轮基础设施或平台能力改写

优先来源：

- 官方政策页
- 官方产品更新
- 平台公告
- 当前价格 / 费率 / 限额说明

## Evidence Hierarchy

当多个来源同时存在时，优先级建议如下：

1. 第一方、当前、可归因来源
2. 第一方之外但当前、强相关、可复核来源
3. 高质量二手分析
4. 泛化观点或历史印象

执行含义：

- 不要只因为某人在社媒上说“最近很火”就直接下结论
- 不要把老文章、老榜单、老评论当作“当前市场事实”
- 能看价格页、更新日志、官方公告时，优先看这些

## Output Implications For The Agent

该 agent 的 `SYSTEM.md` 应强制要求：

- 凡是“当前市场”“最近增长”“现在有前景”“竞争是否激烈”“是否还能做”
  这类判断，都必须先走 live evidence 路线
- 若没有 live evidence 能力，只能输出 `[Evidence Gap]` + 保守分析框架
- 结论应使用：
  - `promising now`
  - `conditional`
  - `weak now`
  - `[Evidence Gap]`
  这类有边界的判断，而不是绝对化“能做 / 不能做”

## Suggested Minimum Analysis Structure

一个完整的市场前景判断，至少应包含：

- 当前结论
- 证据状态
- 需求信号
- 竞争信号
- 变现信号
- 分发信号
- 时间窗口判断
- 主要不确定项
- 下一步验证动作
