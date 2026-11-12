---
name: wf-review
description: reviewer 侧：读取本次暂存请求，只读项目并按固定检查轴产出协议化报告。
disable-model-invocation: true
user-invoked: true
---

# wf-review

> **判断指引**：关 finding、判"报告是否还沿用"、处理标准漂移前先读 `wf-judging` 的 4.2 / 4.5 / 4.7：关闭证据必须指回那个问题，"沿用"必须点名 `d:` 位置。

由人打开的顺序独立 review CLI 会话调用。**只写暂存目录**，不写项目树、不改源码、不提交。

**适用面**：只在**复杂任务**的 Check pass 之后、人判之前使用（设计稿 §4.3、§6.5）。轻量任务不发起审查；任务仍属复杂而审查环境不足时，按设计稿 §6.5 暂停或异常归档。

## 输入（只有两项）

**任务 id** 与 **轮次**。其余信息由入口给出，不需要人再准备。

```bash
<python> <项目根>/.wf/bin/wf.py review-context --task <任务 id> --round <轮次> \
  --envelope <本会话信封> --json
```

返回的 `facts` 里给全了你需要的：`report_path`（报告要写到哪）、`materials`（`diff.patch` / `prd.md` / `check.json` / `tests.json`）、`anchor`（`check_anchor`）、以及 `agent`（你的署名，取自本会话宿主身份）。

**同一 agent 在同一轮只能审查一次**：`review-context` 会先占位；若本轮已有你的记录，它会直接拒绝并给出口——不要绕过去重跑。

## 步骤

1. 运行上面的 `review-context`，拿到 `report_path` 与 `materials`。
2. 只读 `materials` 里的材料（`diff.patch` 是相对 HEAD 的差异；`prd.md` 是本次批准的需求；`check.json` 是 Check 锚点；`tests.json` 是已执行的验证命令）。需要时可只读仓库补充，但不越出排除面。
3. 报告写到 `report_path`（文件名 `review-<agent>.md` **就是身份**，正文不必再写 `reviewer-id`/`source-cli`）。写完后把文件头部的 `status=in-progress` 改成 `status=done`——`review-import` 只认 `done`。
   **报告已存在时先看状态行**：`status=in-progress` 是你自己这次的占位（`review-context` 写的骨架），正常续写；**已是 `status=done`** 说明该槽位本轮已完成一份报告、只是还没导入——**停止并回报给人，不要覆盖**。
4. 按固定检查轴逐项检查：范围、验收、契约/spec、跨层回归、可测性。
5. 材料不足以覆盖某个轴时**停止并回报**，不自行扩大读取范围；越界与缺材料写进 `scope-exceptions`。
6. 报告 = 头部状态行 + Markdown 正文 + 唯一协议块：

```
<!-- wf-review-agent:v1 status=done -->
<!-- wf-review-report:v1 -->
```json
{"protocol":"wf-review-v1","task-id":"…","round":1,
 "review-time":"…","review-focus":"…","check-anchor":{"check_id":"…","check_anchor":"sha256:…"},
 "read-scope":[…],"excluded-scope":[…],"scope-exceptions":[],
 "axes":{"range":"…","acceptance":"…","contract":"…","regression":"…","testability":"…"},
 "findings":[{"id":"f1","location":"…","evidence":"…","impact":"…","severity":"blocking|suggestion"}],
 "verdict":"pass|fail|unavailable"}
```
```

7. `verdict` 只写本报告的事实结论；不得声称“已通过项目门禁”。
8. 结束时回显三项事实：`round`、`agent`（= 你的文件名 token）、实际输出路径。回显后停止，不宣称流程已推进、不标记修复已完成、不宣称已验证。

## 不做

- 不读凭据、私密配置、项目外路径与其他任务目录。
- 不改项目内任何文件；不做提交；不代替主会话做处置决定。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 改造成 `<!-- wf-review-report:v1 -->` 协议 + 项目树外暂存、只写自己报告；锚点字段按 §6.5 |
| 最近正例 | 任务记录 `validation.md` §19：codex 与 pi（glm-5.3-flash）两异种 reviewer 各写 `report.md` 到自己的暂存槽位、锚点与当前 Check 一致，`review-import` 导入成功 |
| 最近反例 | 实现稿 §7.1 V4：改一个交付文件后重导旧报告 → `WF_REVIEW_INVALID`（锚点失配）；报告缺 `check-anchor` 时无法核对新鲜度 |
