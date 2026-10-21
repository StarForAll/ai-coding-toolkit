# Findings — 子代理上下文推送、派发守卫、trellis_wait、会话身份（E1）

## S1 角色子代理上下文推送

- 父会话 `subagent` 调用返回 `started subagent 129f5fb4-…`。
- 子代理**首个**请求（6 条消息）中出现 5472 字符的推送消息：
  - 首行 `<!-- trellis-hook-injected -->`
  - 含**项目真实角色 skill 正文**（`.dsh/skills/trellis-agent-implement/SKILL.md` 去 frontmatter 后逐字命中）
  - 含 `Active task: .trellis/tasks/10-21-verify-task`
  - 含任务 `prd.md` 正文（`PRD-BODY-MARKER`）
- 子代理请求中 **无** bootstrap、**无** workflow-state 面包屑、**无** `<dsh-mode>` 横幅。
- S3 通用子代理（无 trellis 角色）：只收到 516 字符原始 prompt，无任何 Trellis 推送（与 Codex hook 的 silent return 对齐）。

## S2/S8/S9/S10 派发守卫

| 用例 | 输入 | 结果 |
| --- | --- | --- |
| S2 指针指向不存在任务 | pointer → `.trellis/tasks/10-21-missing` | 派发被拒：`Error: Trellis dispatch guard: no readable active task for trellis-agent-implement.`；mock 日志无 child 请求（子代理未启动） |
| S9 任务目录存在但 task.json 损坏 | 同上 + `{bad` | 同样被拒（fail-closed） |
| S8 仅 `Active task:` 前奏、无指针 | 前奏指向可读任务 | 放行，子代理启动并收到推送 |
| S10 `trellis-agent-research` 无任务 | 无指针 | 放行（research 例外），子代理启动 |

Codex 没有等价守卫（会放行并静默不注入），这是 DSH 侧更严格的增强。

## S4/S5/S11 `trellis_wait`

| 用例 | 子代理结局 | 工具返回 |
| --- | --- | --- |
| S4 | 正常完成 | `subagent <id> completed; settlement notice delivery is unverified; inspect its report or transcript before passing a dependent gate` |
| S5 | 子代理上游 500（重试 6 次后失败） | `subagent <id> settled with failed (error); do not treat this gate as passed; settlement notice delivery is unverified` |
| S11 | 不存在的 id | `Error: trellis_wait can only wait for a direct continuable subagent of this session: does-not-exist` |

- 失败/未知不会被误报为通过（fail-closed，E1）。
- “settlement notice delivery is unverified”是 DSH `subagent/end` 只证明执行结算、不证明父通知投递的如实表述
  （`lib/wait-tool.js:1-10`、`settlementNoticeQueued: false`）；成功路径也带这句，可能诱导模型重复核对，属噪声而非错误。
- 未验证：等待中超时/取消、rc.8 原生 settlement notice 唤醒时序（本轮子代理均快速结算）。

## S6 会话身份

真实 bash 工具内：

```
CTX=dsh_session-a1114fc3-e00c-4742-b4f1-7160293c1abe
SID=session-a1114fc3-e00c-4742-b4f1-7160293c1abe
```

- `DSH_TRELLIS_CONTEXT_ID` = `dsh_<原生 session id>`，与 `.trellis/.runtime/sessions/dsh_<id>.json` 命名一致。
- 该会话尚未绑定任务时 `task.py current --json` 返回 `{"current_task": null, "source": "none"}`，符合预期。
- 状态实验复用的会话（`session-aaa548aa-…`）在指针存在时能正确解析出任务并注入 `Active task:`。

## S7 inline 模式下的派发

在 `dsh.dispatch_mode: inline` + 可读任务下派发 `trellis-agent-implement`：**放行**，子代理启动并收到完整推送。
即 inline 模式目前只是提示，不是技术门禁（详见 `inline-mode.md`）。
