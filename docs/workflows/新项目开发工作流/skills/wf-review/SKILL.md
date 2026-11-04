---
name: wf-review
description: reviewer 侧：读取本次暂存请求，只读项目并按固定检查轴产出协议化报告。
disable-model-invocation: true
user-invoked: true
---

# wf-review

由人打开的顺序独立 review CLI 会话调用。**只写暂存目录**，不写项目树、不改源码、不提交。

## 输入

必备参数：`--task-id`、`--round`、`--reviewer-id`（= 槽位 id）、`--review-focus`、`--request <staging>/request.json`。

## 步骤

1. 只读 `request.json`：`check-anchor`、`submitted_scope`（diff/需求/测试结果）、`readable_scope`（业务代码、spec、PRD）、`exclusions`。
2. 按固定检查轴逐项检查并按需只读仓库：范围、验收、契约/spec、跨层回归、可测性。
3. 材料不足以覆盖某个轴时**停止并回报**，不自行扩大读取范围；越界与缺材料写进 `scope-exceptions`。
4. 报告写到同目录 `report.md`：Markdown 正文 + 唯一协议块：

```
<!-- wf-review-report:v1 -->
```json
{"protocol":"wf-review-v1","task-id":"…","round":1,"reviewer-id":"r1","source-cli":"claude",
 "review-time":"…","review-focus":"…","check-anchor":{"check_id":"…","check_anchor":"sha256:…"},
 "read-scope":[…],"excluded-scope":[…],"scope-exceptions":[],
 "axes":{"range":"…","acceptance":"…","contract":"…","regression":"…","testability":"…"},
 "findings":[{"id":"f1","location":"…","evidence":"…","impact":"…","severity":"blocking|suggestion"}],
 "verdict":"pass|fail|unavailable"}
```
```

5. `verdict` 只写本报告的事实结论；不得声称“已通过项目门禁”。

## 不做

- 不读凭据、私密配置、项目外路径与其他任务目录。
- 不改项目内任何文件；不做提交；不代替主会话做处置决定。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 改造成 `<!-- wf-review-report:v1 -->` 协议 + 项目树外暂存、只写自己报告；锚点字段按 §6.5 |
| 最近正例 | reviewer 写报告到暂存目录、锚点与当前 Check 一致，导入成功 |
| 最近反例 | 报告写进项目树、缺锚点；缺失时审查报告无法核对新鲜度 |
