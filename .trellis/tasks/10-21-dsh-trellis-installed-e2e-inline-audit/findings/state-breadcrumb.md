# Findings — workflow-state 面包屑与 bootstrap（E1）

## 1. 单会话逐状态注入（真实 headless 会话 `session-aaa548aa-…`）

每轮以 mock 服务捕获模型请求，按“与上一轮消息列表的最长公共前缀”取新增消息，剔除自身 prompt。

| 轮次 | 项目状态 | 新增注入 | 消息长度 | 状态头 | 正文与 Codex hook |
| --- | --- | --- | --- | --- | --- |
| T1 | 无任务 | breadcrumb + bootstrap | 491 + 138 | `no_task` | 正文一致（见下） |
| T2 | 无任务（同会话再来一轮） | 无 | — | — | 去重生效（跨进程 resume 也去重） |
| T3 | planning / auto | 是 | 566 | `planning` | **449 字节正文与 Codex 完全相同** |
| T4 | planning / inline | 是 | 898 | `planning-inline` | Codex 正文 439 + DSH 横幅 333 |
| T5 | in_progress / inline | 是 | 787 | `in_progress-inline` | Codex 正文 325 + DSH 横幅 333 |
| T6 | completed | 是 | 198 | `completed` | **80 字节正文完全一致** |
| T7 | blocked（模板无块） | 是 | 221 | `blocked` | 通用降级行（Codex 同类） |
| T8 | reviewing（自定义） | 是 | 223 | `reviewing` | 通用降级行（Codex 同类） |
| T9 | 指针指向已删除目录 | 是 | 219 | `stale` | 通用降级行（该模板无 `stale` 块） |
| T10 | task.json 损坏 | 是 | 464 | `task_error` | **345 字节正文完全一致** |
| T11 | 命中项目 `skip_keyword` | **无** | — | — | 与 Codex 一样静默 |
| T12 | 切回 auto / in_progress | 是 | 1755 | `in_progress` | **1635 字节正文完全一致** |
| T13 | 再切回 inline | 是 | 787 | `in_progress-inline` | 切换后重新注入 |
| T14 | `dispatch_mode: InLiNe   # 注释` | 无新增 | — | （沿用 inline 正文） | 大小写与行内注释解析正确 → digest 未变 |
| T15 | `dispatch_mode: off`（非法） | 是 | 1755 | `in_progress`（auto） | 非法值回落 auto |

证据目录：`/tmp/dsh-verify-20261021-1547/state-seq/t01…t15/`（`requests.jsonl` 为模型真实请求）。

### 逐字对照（Codex hook vs DSH 注入正文）

| 状态 | Codex 正文 | DSH 正文 | 结果 |
| --- | --- | --- | --- |
| planning（auto） | 449 | 449 | 完全相同 |
| in_progress（auto） | 1635 | 1635 | 完全相同 |
| completed | 80 | 80 | 完全相同 |
| task_error | 345 | 345 | 完全相同 |
| planning inline | 439 | 439 + 333 banner | 块相同，DSH 追加 DSH 专属说明 |
| in_progress inline | 325 | 325 + 333 banner | 同上 |

## 2. bootstrap

- 新会话首轮 `no_task`：独立消息 `<trellis-bootstrap>…</trellis-bootstrap>`（138 字符），与 Codex 文案逐字相同。
- 同会话第二轮、以及后续任意状态切换：**不再注入**（T2/T3+ 新增消息中无 bootstrap）。
  Codex 则在每个无任务轮次随 breadcrumb 重复输出。这是插件文档声明的有意差异，不是缺陷。
- 子代理：S1/S7 的 child 请求中 `bootstrap=False`、`workflow-state=False`，只收到角色推送（见 `subagent.md`）。

## 3. 状态与变体选择

- 任务级 `task.workflow`（V1）、`.trellis/.developer workflow=`（V5）、`config.yaml default_workflow`（V4）
  都能正确选中 `.trellis/workflows/alt.md`；变体文件缺失（V6）回落到全局 `.trellis/workflow.md`。
- 变体中的空 `planning-inline` 块被丢弃（V3 回到 `planning` 基础块），与 Trellis `if body:` 语义一致。
- stale 时任务目录已删除，`task.workflow` 不可读，两个平台都回落到全局 workflow.md；
  DSH 状态名 `stale`，Codex 为 `stale_<source>`（`stale_session`）。若全局模板含 `stale` 块，两者都会命中该块。
- 非 Trellis 目录（`/tmp/notrellis-verify`）：0 注入（V7）。

## 4. 相关代码

- `lib/workflow.js:14-21`（`STATUS_RE` 行尾约束）、`:423-437`（inline 选择与 digest）、
  `:389-405`（`mapStatus` 原值透传）、`:355-380`（`stale`/`task_error` 区分）。
- `lib/workflow.js:414` 注释明确忽略 `codex.dispatch_mode`，DSH 读自己的 `dsh.dispatch_mode`。
