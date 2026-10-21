# Findings — 真实 DSH 会话端到端验证

判定基线：E1 = 本次实际运行取证；E2 = 静态推断；E3 = 文档/测试声明。

## 验证环境（真实进程）

- 临时 Trellis 项目：`/tmp/trellis-e2e`（`trellis init --dsh --codex --claude -y -u xzc`，
  CLI 0.7.0-beta.4；工作流模板含与仓库相同的第 123 行注释）。
- 临时 DSH profile：`~/.dsh/profiles/trellis-audit`（`dsh-base` + `dsh-headless` +
  `insert: dsh-trellis`；`node_modules/dsh-trellis` 符号链接到本仓库同一份插件代码）。
- LLM：本地 mock OpenAI-compatible 服务（`127.0.0.1:18931`），返回固定文本或指定
  tool_calls；不消耗真实额度，且能抓到**模型实际收到的完整 messages**。
- 真实 DSH 版本 0.2.1-rc.2；`dsh --profile trellis-audit --json "..."`。

> 说明：真实 web profile（`dsh --profile web`，即当前会话）也已用于取证，
> breadcrumb/bootstrap 的实际注入消息来自其 session transcript（见
> `state-breadcrumb.md` 第 1 节）。

## 1. no_task 端到端（E1）

全新项目、全新会话，`/tmp/mock-llm-requests.jsonl` 中模型请求的 messages 含：

- `user` 4065 字符：`<system-reminder>\nTrellis workflow state: no_task\n\n→ no active task; before Phase 1\n    [workflow-state:task_error] …`
  结尾被截断在 `…enter the planning ph`；真正的 `no_task` 指引（workflow.md:180–182）
  不可完整读到，正文前 57 行是注释内容。
- `user` 138 字符：`<trellis-bootstrap>…</trellis-bootstrap>`（正常）。

结论与探针 A 一致：缺陷在全新安装项目上同样复现，不是本仓库特有。

## 2. 状态切换端到端（E1）

同一会话（`session-1436ab53-…`）依次切换状态，transcript 中 `source.kind=dsh-trellis`
的消息（去重后）：

| 状态 | 是否注入新消息 | 消息长度 | 首行 |
| --- | --- | --- | --- |
| no_task | 是 | 4065 | `→ no active task; before Phase 1`（注释尾巴） |
| bootstrap | 是（仅一次） | 138 | `<trellis-bootstrap>` |
| planning | 是 | 567 | `Trellis workflow state: planning` + `Active task: …` |
| in_progress | 是 | 1756 | 正常真块正文 |
| task_error | 是 | 465 | 正常真块正文 |
| stale（指针指向已删除目录） | **否** | — | 插件按 task_error 处理，digest 不变，被去重；模型看不到"指针已失效"的提示 |

最后一行是本次审计确认的第二类问题：`stale` 在插件里不可达（见
`state-breadcrumb.md` 第 2 节），且因 digest 去重不会产生新消息。

## 3. spec 注入（deny-once / retry / ticket）（E1）

临时项目新增 `.trellis/spec/demo/demo-guidelines.md`（frontmatter `paths: ["src/**/*.ts"]`）。

- **deny-once**：mock 请求 `write src/a.ts` → 工具结果为
  `Error: Trellis injected governing specs. Review them, then retry this tool call.` +
  `<spec-context file="src/a.ts" spec=".trellis/spec/demo/demo-guidelines.md" sha256="a46cd3be4651">…`，
  文件未创建。
- **retry 放行**：同一调用重试 → `status=completed`，文件创建成功（`src/a.ts`）。
- **ticket 走 post-execute**：`tools: [read, edit, write]` 下用 `read src/a.ts`（无 deny 路径）
  → 工具结果 completed，下一次模型请求出现独立的 `user` 消息
  `<spec-context file="src/a.ts" …>`（252 字符）。
- **状态分片**：`.trellis/.runtime/spec-inject/session-*.json` 实际生成（每个会话一份）。

与 Codex 对照（E1）：同一输入跑 `.codex/hooks/inject-spec-context.py`，输出
`permissionDecision: "deny"`、`permissionDecisionReason` 与插件逐字相同，
`additionalContext` 中的 `<spec-context>` 与 `sha256="a46cd3be4651"` 完全一致。

## 4. 子代理上下文推送（E1）

mock 让父会话调用 `subagent`，prompt 以 `Active task: .trellis/tasks/10-21-e2e-planning`
开头并点名 `trellis-agent-implement`：

- 子代理首个模型请求里出现 5560 字符的 `user` 消息：
  `<!-- trellis-hook-injected -->\n# Trellis Native Implement Subagent …`
  含 `Active task:`、**项目真实 role skill 正文**（`.dsh/skills/trellis-agent-implement/SKILL.md`，
  不是 fallback），以及任务的 `prd.md` 内容。
- 父会话 tool_result 为 `started subagent <id>`。

## 5. dispatch 守卫（E1）

同一调用但 prompt 指向不存在的 `.trellis/tasks/10-21-missing`：

- `subagent` 调用被拒绝：
  `Error: Trellis dispatch guard: no readable active task for trellis-agent-implement. …`
- mock 日志中没有出现任何带推送上下文的子代理请求（子代理未启动）。

这是 DSH 侧比 Codex 更严格的行为（Codex 会放行且不注入），插件自己也文档化了这一点。
本次只确认"卫卫生效"，未评判该增强是否应保留——需用户决定。

## 6. 原生会话身份（E1）

mock 让模型执行 `bash` 打印环境变量，工具结果为：

```
CTX=dsh_session-de5d70ac-acd0-40e9-8fda-e640d705c52d
SID=session-de5d70ac-acd0-40e9-8fda-e640d705c52d
```

即 `DSH_TRELLIS_CONTEXT_ID` = `dsh_<native session id>`，与 `.trellis/.runtime/sessions/`
指针命名一致；`DSH_SESSION_ID` 也由宿主提供。

## 7. 工具面（E1）

headless 会话的工具列表（模型请求的 `tools`）包含插件注册的 `trellis_wait`，
同时含 `subagent` / `subagent_fork`（守卫覆盖的工具名与此一致）。

## 8. 未验证 / 局限

- `trellis_wait` 的实际等待语义未做端到端（需要真实子代理事件时序 + 长等待）。
- web 设置页 UI 未做浏览器级验证（仅验证了其后端路由与设置 schema）。
- mock LLM 不验证真实模型的指令遵循，只验证"模型实际收到什么"。
- 本次三个并行子代理曾因真实 LLM 额度不足（`QUOTA/402`）中断，未能产出其 findings；
  对应能力面已由主会话用上述 E1 手段补齐，未使用其未完成的结论。
