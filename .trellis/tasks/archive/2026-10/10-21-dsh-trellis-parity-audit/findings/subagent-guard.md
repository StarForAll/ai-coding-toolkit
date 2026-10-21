# Findings — 子代理上下文推送与 dispatch 守卫

判定基线：E1 = 实际运行；E2 = 静态推断；E3 = 文档/测试声明。

## 1. 首轮上下文推送（E1）

真实 DSH 会话（headless + 本地 mock LLM）中，父会话调用 `subagent`，prompt 以
`Active task:` 开头并点名 `trellis-agent-implement`：

- 子代理首个请求收到 5560 字符消息，标题 `# Trellis Native Implement Subagent`；
- `## Role Instructions` 段是 `.dsh/skills/trellis-agent-implement/SKILL.md` 的真实正文
  （去掉 frontmatter），不是 fallback；
- `## Curated Context` 含任务 `prd.md` 内容；
- 消息 source 为 `{kind:"dsh-trellis", form:"subagent-context", role:"implement", task:…}`。

模块级复核（E1）：

```
readRoleInstructions(root=/tmp/trellis-e2e, role=implement) -> 4297 字节
readRoleInstructions(root=/tmp/spec-cfg, role=implement)    -> null（无 .dsh/skills）
roleInstructionsFallback("check") -> "Load `.dsh/skills/trellis-agent-check/SKILL.md` once before acting."
buildSubagentContext(temp task, implement) -> 701 字节，含 prd.md
parentTaskPath(repo, live session id) -> .trellis/tasks/10-21-state-breadcrumb-audit
```

解析边界（E1）：`parseDispatchPrompt` 能从 `Active task: …` 提取路径（自动去掉句末
`.`），无 role 时保持静默；role 存在但无任务 prelude 时返回 `taskPath:null`，随后
由父会话指针兜底。

## 2. dispatch 守卫（E1）

- 有任务（`Active task:` 指向可读 task.json）：放行。
- 无任务 / 指向不存在的任务：拒绝 `trellis-agent-implement`，错误文案含
  `Trellis dispatch guard: no readable active task for trellis-agent-implement.`；
  mock 日志确认子代理未启动。
- 守卫在 Trellis 项目之外不生效（代码路径 `project === null` 直接放行，E2）。
- `research` 角色允许无任务并在 post-execute 附通知（代码路径 + 单测；未构造真实
  research 子代理，属 E2）。

## 3. 与 Codex/Claude 的行为差异（E2/E1）

- Codex/Claude 的 `SubagentStart` hook 在没有任务时**静默不注入**；DSH 插件选择
  fail-closed 拒绝 dispatch。代码注释与 README 均声明这是有意增强。是否保留需用户决定。
- role skill 正文仍写着 "This platform does NOT auto-inject task context via hook。
  Before doing anything else, you MUST load context yourself."，而插件在推送消息里声明
  "已经准备好上下文"。两段文案同时出现在子代理首轮提示里，可能让子代理重复执行
  `task.py current`（无指针的子代理会得到空结果，skill 又要求"问用户"）。
  这是**提示词自相矛盾**的观察，未构造行为级证据（E2），建议一并评估。

## 4. wait 工具（E1/E3）

- `trellis_wait` 已注册并出现在真实会话的工具列表中（E1）。
- 其等待语义（默认后台模式、每次依赖子代理一次、settlement 通知消费）未做端到端；
  单测通过（E3）。

## 5. 验证通过（无问题）

- 推送只发生在首轮（`payload.step !== 1` 直接返回），不会每轮重复（E2）。
- 推送只对 role 子代理生效，普通子代理消息静默（E2 + E1 的 no_task 抑制实测）。
- role 指令超长时按 `ROLE_INSTRUCTIONS_MAX_BYTES` 截断并追加提示（E2）。
- manifest（`implement.jsonl` / `check.jsonl`）无真实条目时，推送包含"未注入 spec 上下文"
  的显式说明，而不是假装有上下文（E1：临时任务无 jsonl 条目时消息含该说明）。

## 6. 未验证 / 无法验证

- `research` 无任务通知的真实投递（E2）。
- `trellis_wait` 的真实等待/超时/结算通知（E3）。
- 子代理内 `Active task:` 与父指针不一致时的优先级（代码为先 prelude 后父指针，E2）。
