---
name: wf-review
description: reviewer 侧：运行 review-context 取材料与报告骨架（授权范围以 facts 为准），只读项目并按固定检查轴产出协议化报告。
disable-model-invocation: true
user-invoked: true
---

# wf-review

> **判断指引**：关闭证据必须指回那个问题（见 `wf-repair-loop`「这条 blocking 真的修了吗」）；"沿用"必须点名 `d:` 位置（见 `wf-review-action`「报告还能不能沿用」）；标准本身该不该改见 `wf-spec-update`「改的是"尺子"还是"判断"」。

由人打开的顺序独立 review CLI 会话调用。**只写暂存目录**，不写项目树、不改源码、不提交。

**适用面**：只在**复杂任务**的 Check pass 之后、人判之前使用（设计稿 §4.3、§6.5）。复杂任务默认要求两个与实施 CLI 不同、彼此也不同的审查 CLI；只有一个 reviewer 时，判定需人签残余风险接受记录（`review-decide --single-reviewer-acceptance`，留痕降级、不默认）——这是判定入口的事，reviewer 侧照常产出报告。轻量任务的完成条件是 Check 的内部双轴审查；需要额外意见时可以自发外部审查（可选，不改变分级、也不是轻量完成条件）。任务仍属复杂而审查环境不足时，按设计稿 §6.5 暂停或异常归档。

## 输入（任务 id 与轮次）

**任务 id** 与 **轮次**，其余信息由入口给出。身份按你的会话模式补一项：

```bash
# 自动身份模式（身份由执行边界派生，没有宿主 host_id）：署名必须自报
<python> <项目根>/.wf/bin/wf.py review-context --task <任务 id> --round <轮次> --as <你的 CLI> --json

# 显式信封模式：信封携带 session.identity.host_id 时 --as 可省
<python> <项目根>/.wf/bin/wf.py review-context --task <任务 id> --round <轮次> \
  --envelope <本会话信封> --json
```

返回的 `facts` 里给全了你需要的：`report_path`（报告要写到哪）、`materials`（材料目录，文件名以 facts 返回为准）、`submitted_scope` / `readable_scope` / `exclusions`（本次授权边界）、`anchor`（`check_anchor`）、以及 `agent`（你的署名，取自本会话宿主身份）。若 `narrowed` 为真，材料只是交付集合的子集（`submitted_paths` / `delivery_path_count`）：按声明范围审，不把未选路径当作已覆盖；需要更多材料时停止回报，不自行扩大。

**同一 agent 在同一轮只能审查一次**：`review-context` 会先占位；`status=in-progress` 是你自己的草稿，重入会返回同一 `materials`/`report_path` 让你续写；只有 `status=done` 才拒绝并指向 `review-import`。不要绕过去重跑。

## 步骤

1. 运行上面的 `review-context`，拿到 `report_path` 与 `materials`。
2. 只读 `materials` 里的材料（`diff.patch` 是相对**任务基线**的差异；`prd.md` 是本次批准的需求；`check.json` 是 Check 锚点；`tests.json` 是已执行的验证命令，其 `logs[]` 只含**通过证据身份核对**的脱敏验证日志（每条带 `verified: true` 与 `recorded_digest`）；Check 引用了但字节不符或读不到的日志**不进包**，改在 `status.json.problems` 列出原因——按"证据不可核实"处理，**必须作为 finding 报出**）。材料包不足时，可只在 `readable_scope` 内只读仓库补充（业务代码、spec、PRD），把实际读取面写进 `read-scope`；不得越过 `exclusions`。只读材料包、未做仓库补读时 `read-scope` 写 `materials`；本轮 `readable_scope` 显式为空时，空数组表示未补读，不要写仓库路径。**`read-scope` 不得与 `excluded-scope` 或本次 `exclusions` 交叠**：如果某路径已声明排除，就不要把它写进读取面；确实读过就如实写，导入/判定会按越界处理。`.wf/` 运行态与 `.git/` 私有配置不是业务代码，未在 spec/PRD 显式放行时不要申报。
3. 报告写到 `report_path`（文件名 `review-<agent>.md` **就是身份**，正文不必再写 `reviewer-id`/`source-cli`）。写完后把文件头部的 `status=in-progress` 改成 `status=done`——`review-import` 只认 `done`。**状态行的唯一位置约定**：骨架写在第一行，判定只读报告**开头前 400 字符**；把标题/长前言写在状态行之前并超过这个窗口，等价于没有状态行。
   **报告已存在时先看状态行**：`status=in-progress` 是你自己这次的占位（`review-context` 写的骨架），正常续写；**已是 `status=done`** 说明该槽位本轮已完成一份报告、只是还没导入——**停止并回报给人，不要覆盖**。
4. 按固定检查轴逐项检查：范围、验收、契约/spec、跨层回归、可测性。
5. 区分两种不足：
   - **材料包不足**（例如缺测试记录）：先按 `readable_scope` 在仓库内补读并记 `read-scope`；补不到就把该轴记 `uncovered`，在正文写明缺什么。
   - **授权范围不足**（需要读排除面、项目外或其他任务目录）：**停止并回报**，不自行扩大；该轴记 `uncovered`，不要写自造字段。
   报告是辅助证据，主会话会逐轴复核并补足；你按事实写 `uncovered` 比猜测更有用。
6. 材料目录**只读不改**：`review-context` 物化后即落身份记录（`materials-manifest.json`），
   并把该身份预填进报告 `materials.identity`；导入与判定都按它核对——手改材料会让入口拒，
   重取也不会重写已有字节（新增文件同样算改了）。缺材料就补读到仓库、写 `read-scope`。
   主会话若在你写报告前后重出了材料，`materials.identity` 会与当前不符：按新 facts 重抄该值，
   然后**重核受影响的结论**（材料换了，你引用的行号、证据、覆盖判断都可能变——重抄不等于重审）；
   或由主会话开新一轮。若只是材料目录被清/重建（Check 未重跑、交付面与规格未变），
   重建会逐字节复现同一身份，报告继续有效；只有 Check 换 id 或字节变化才需重写/开新一轮。
7. 材料是**脱敏副本**：`diff.patch` / `prd.md` 在生成时按协议 `secret-mask` 遮罩过（`status.json` 里 `redacted: true`），看到 `***` 是预期，不要据此判「材料缺失」；报告 = 头部状态行 + Markdown 正文 + 唯一协议块（`review-context` 已把整套骨架写到
   `report_path`，含预填的 `task-id`/`round`/`check-anchor`；照它填，不自己另写字段）：

```
<!-- wf-review-agent:v1 status=done -->
```

报告协议**以 `review-context` 生成的骨架为权威版本**（字段、必填、枚举一次给全，不在此复制）：
骨架已预填 `excluded-scope`（必排敏感面）与 `read-scope=["materials"]`，按需自行申报仍受同一套导入校验约束。

同一份报告内 `findings[].id` 必须唯一；不同报告之间可以复用同名 id（身份由 round+slot+id 组成）。

8. `verdict` 只写本报告的事实结论；不得声称“已通过项目门禁”。
9. **先在 `status=in-progress` 下跑一遍
   `<python> <项目根>/.wf/bin/wf.py lint report --file <report_path> --task <任务 id> --json`**，
   按 `problems` 一次改全。草稿阶段的 `in-progress` 不是格式错误（lint 只在 `notes` 里提示
   “导入前须改 done”，`ok` 仍为 true）；`import`/`decide` 才要求 `status=done`。
10. 结束时回显三项事实：`round`、`agent`（= 你的文件名 token）、实际输出路径。回显后停止，不宣称流程已推进、不标记修复已完成、不宣称已验证。

## 不做

- 不读凭据、私密配置、项目外路径与其他任务目录。
- 不改项目内任何文件；不做提交；不代替主会话做处置决定。
  这不算违反：只读仓库补充材料、把报告写到入口给的暂存路径；改项目文件或提交才是越界。

## 纪律

- 运行纪律见 `.wf/workflows/session-flow.md`「运行约定」：身份只经信封或宿主映射通道；不代人作答；入口输出是唯一判定源；解释器整会话固定、失效即停。

## 来源与差异

| 项 | 值 |
|---|---|
| 来源 | 本仓库全局 `skills/multi-cli-review`（一次性适配源） |
| 许可 | 跟随本仓库（内部私有源，无第三方 NOTICE 义务；上游为同作者资产） |
| 基线 | 适配基线＝本仓库上述源文件；本副本为唯一发行件，上游改动不自动流入 |
| 差异 | 改造成 `<!-- wf-review-report:v1 -->` 协议 + 项目树外暂存、只写自己报告；锚点字段按 §6.5 |
| 最近正例 | 任务记录 `validation.md` §19：codex 与 pi（glm-5.3-flash）两异种 reviewer 各写 `review-<agent>.md` 到本轮暂存路径、锚点与当前 Check 一致，`review-import` 导入成功 |
| 最近反例 | 实现稿 §7.1 V4：改一个交付文件后重导旧报告 → `WF_REVIEW_INVALID`（锚点失配）；报告缺 `check-anchor` 时无法核对新鲜度 |
