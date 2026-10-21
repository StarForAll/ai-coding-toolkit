# 子代理上下文、派发守卫与 wait

任务：`.trellis/tasks/10-21-impl-task`，含 `prd.md`/`design.md`/`implement.md`、`implement.jsonl`（指向 demo spec）、`check.jsonl`。

## 结果矩阵

| ID | 场景 | 观察 | 判定 | 证据 |
| --- | --- | --- | --- | --- |
| S21 | implement 首步 | child 收到 5498 字符推送：角色契约 + `PRD-MARKER-123` + spec + design/implement；无 `no_task` 面包屑 | 通过 | `s21-implement-push/requests.jsonl` |
| S22 | check 首步 | 5362 字符；读取 `check.jsonl` 指向的 spec + prd；不读 implement 清单 | 通过 | `s22-check-push/requests.jsonl` |
| S23 | research 首步 | 4854 字符；`research.jsonl` 为空 → “no curated entries” + prd/design/implement | **与 Codex 不等价** | `s23-research-push/requests.jsonl`、`s43-codex-research.txt` |
| S24 | generic child | 无 push、无 breadcrumb、无 bootstrap | 通过 | `s24-generic-child/requests.jsonl` |
| S25 | 删除 implement role skill | 推送回退为 `Load .dsh/skills/trellis-agent-implement/SKILL.md once…` | 通过 | `s25-missing-role-skill/requests.jsonl` |
| S26 | 无任务 implement | `status=error`，guard 文案；child 未启动（0 个 child 请求） | 通过（DSH 增强） | `s26-guard-no-task/` |
| S27 | 无任务 research | 放行；child 启动；下一次请求出现 `<trellis-dispatch-guard>` 输出位置提醒 | 通过 | `s27-research-no-task/` |
| S28 | inline implement | `status=error`，inline 守卫拒绝；child 未启动 | 通过（DSH 增强） | `s28-inline-guard/` |
| S29 | inline + `inline_allow_dispatch: true` | tool completed，child 启动并收到 push | 通过 | `s29-inline-escape/` |
| S30 | child 运行中 wait | `trellis_wait` 返回 `completed`，文案含 “settlement notice delivery is unverified” | 通过 | `s30-wait-success/events.jsonl` |
| S31 | child 先结束再 wait | 返回 `already-inactive` / `unknown`，未挂死 | 通过（fail-closed） | `s31-wait-after-end/events.jsonl` |
| S32 | child 失败 | 返回 `settled with failed (error)`，不误报 completed | 通过 | `s32-wait-failure/events.jsonl` |
| S33 | 两个会话 | A 显示 impl-task，B 显示 session-b-task；互不串 | 通过 | `s33b/`、`s33c/` |

## 关键差异：research 上下文（P2）

Codex `SubagentStart` 对 research 的 `Curated Context` 是 **项目 spec 目录树 + 搜索提示**：

```text
## Project Spec Directory Structure
.trellis/spec/
├── backend/
├── demo/
├── frontend/
└── guides/
...
## Search Tips
```

插件 `lib/subagent-context.js:30-34` 把 research 也当作 implement/check 一样读取 `research.jsonl` + `prd.md`/`design.md`/`implement.md`：

```text
[Trellis] .trellis/tasks/.../research.jsonl has no curated entries...
=== .../prd.md (Requirements) ===
```

Trellis 0.7.0-beta.4 的任务创建只 seed `implement.jsonl` / `check.jsonl`，`research.jsonl` 是旧/可选清单；因此默认情况下 research 子代理几乎总是收到“无 curated entries”提示，并被塞入任务 artifacts，而不是 Codex 的项目结构概览。角色 skill 里仍有搜索指引，但推送内容与 Codex 不等价。

影响：research 角色做全仓发现时少了“spec 各包/层目录 + get_context --mode packages + 搜索工具”的定向上下文；同时多了与发现任务无关的 PRD/design/implement 文本，可能挤占上下文预算。建议：research 分支改为 Codex 同款 spec-tree + search tips（或两者并存），再决定是否保留 `research.jsonl`。

## 残余文案矛盾（P3）

推送消息先声明：

```
The role skill's "Required: Load Trellis Context First" section is fully satisfied...
do NOT run `task.py current`...
```

紧接着内联的角色 skill 正文仍写着：

```
This platform does NOT auto-inject task context via hook. Before doing anything else, you MUST load context yourself.
```

虽然前置声明覆盖了后者，但同一消息内自相矛盾，弱模型可能仍执行 `task.py current` 或追问任务。证据：`s21-implement-push/requests.jsonl` 的完整推送。

## wait 的边界（非缺陷）

- child 运行中：可靠返回 `completed` / `failed` / `aborted`。
- child 已结束后再 wait：返回 `already-inactive` / `unknown`，而不是猜测成功；模型需查看 transcript 或已到的结算通知。
- 未验证：父会话原生 settlement notice 的实际唤醒时序、子代理 `send_message` 后续轮次、超时（工具本身无超时，只有调用方 AbortSignal）。

## 工具注册

当前会话与隔离 headless 都只注册一份 `trellis_wait`；无插件 control profile 的工具列表中不存在任何 `trellis*` 工具。
