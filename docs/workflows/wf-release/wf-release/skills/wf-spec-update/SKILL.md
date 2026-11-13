---
name: wf-spec-update
description: 更新 spec：准入、新增/更新/拆分/合并/改名/删除、索引与 metadata 同步、依赖解除与处置留痕。
disable-model-invocation: false
---

# wf-spec-update

已启用会话内的知识变更入口，只能在当前任务批准范围内执行。默认路径不依赖 MCP、索引服务或知识图谱。

## 步骤

1. 读现有索引、相关 spec 与本地证据（真实失败、已验证契约、人的长期约定、明确边界）。
2. 判断准入：有可追溯依据、有消费者、与既有条目不冲突；给正反例，不写空泛建议。
3. 起草变更数组（每项 `{operation, old_paths, new_paths, before_digests, after_digests, reference_dispositions}`，`add/update` 带 `content`）。
4. `spec-update --task <id> --changes <path>` 成组应用；删除/停用前逐个解除活动任务依赖，未解除时按出口先解除/推迟/指定替代。
5. 变更后重新 `task-check`（spec 属检查输入，旧 pass 失效）。

## 改的是"尺子"还是"判断"（标准变更）

改验收标准或 spec 规则本身，与修正自己对任务的理解，是两件事：

- 你要判断：改的是哪一类；受影响的**未关闭项**如何处理（哪些因此失效、哪些仍成立）。
- 留下依据：新旧差异摘要 + 受影响未关闭项清单；人的挑战：「这次是标准写错了，还是你在绕开它？」
- 机制只核结构（frontmatter、id 唯一、只增不改、引用存在）与锚点失效；**语义是否冲突、该不该改，由人判**。

## 知识拒绝项（`.wf/out-of-scope/`）

人明确裁定「这个概念我们不做」时，把它写成**持久拒绝项**（一概念一文件），这样下次有人重提时能对上账：

```markdown
---
concept: "parallel-scheduler"
reason: "并行调度不属本框架目标（charter T3 不做清单）"
reconsider_when: "出现真实的多任务并行需求并愿意承担一致性代价时重议"
status: "active"
---

# parallel-scheduler

## 既往请求
- 2026-11-12 ｜ 想要并行跑两个任务 ｜ 人裁：不做，理由见 reason
```

- **写法**：`changes` 的 `add`（首建）或 `update`（重提追加）。机制会拒的：三字段任一为空、
  文件名与 `concept` 不一致、缺 `## 既往请求` 段、**改写既往内容**（只增不改）、追加行不是
  `- <YYYY-MM-DD> ｜ <摘要> ｜ <裁决引用>` 形状、同 concept 已有文件却用 `add` 新建。
- **重提不新建文件**：在同 concept 的 `## 既往请求` 追加一行即可；同 concept 出现多个文件会被
  `inspect` 报重复登记，由人合并。
- **这是"持久拒绝"，不是"这次做不了"**：临时困难、待补依赖、做了一半的活写 `task.handoff.pending`
  （随任务走、任务结束即失效）。判据是**概念层面是否永久不做**——这一个判断由人做，机制只保证写下来的东西可被检索与核对。
- 机制**不判**某次重提是否值得重议，也不判拒绝理由是否成立；它只保证 schema、只增不改与重复登记可见。

## 不做

- 不借知识变更扩大触碰面或改其他任务的目标/批准/check 结论。
- 不自动停用或删除无法核实的条目；交人裁决。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 解释器按 `.wf/workflows/session-flow.md`「运行约定」选择并整会话固定；`WF_EXECUTOR_UNCONFIRMED` 或审批拒绝时停下报告，不换解释器重试。
