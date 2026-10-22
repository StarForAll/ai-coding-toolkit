# Design：dsh-trellis 缺陷修复

## 1. 角色识别的两条来源（P2-1）

角色目前只有一条证据：dispatch prompt 文本。DSH 在两条链路上各有一份可得证据：

### 1.1 父会话 / 守卫（同步可得）

`subagent` 与 `subagent_fork` 的工具参数都含 `description`，DSH 用它作为子代理的显示
`label`（`@deepseek-ai/dsh-tool-subagent`：`label: args.description`）。`tools/pre-execute`
的 `exec.arguments` 已经包含它，无需新增服务。

改动：`parseDispatchRequest(prompt, description)` 先匹配 prompt，未命中再用
`roleFromLabel(description)`。label 是展示文本，只有**以角色名开头**（后接结尾或
括号/冒号/破折号标注，忽略大小写与包裹引号）才算角色，例如
`trellis-agent-implement (audit round 3)`；“研究 trellis-agent-implement 插件的
README”之类话题描述保持 generic。保持
“`Active task:` 只从 prompt 读取”不变（它是任务证据，不是角色标签）。

### 1.2 子代理首步（push 侧）

子代理首步的消息里没有 description，只有 dispatch prompt。但 DSH 在创建子代理时把
`subagent/descriptor`（`{version, mode, provider, label, …}`）写入子会话日志，位于首轮
消息之前。读取它的正确方式是 `sessionProjections` 注册表（插件已经 `inject` 该服务），
而不是已弃用的 `eventAt` / `snapshotEvents` / `ownEvents`。

新增 `lib/subagent-identity.js`：

- key `dsh-trellis.subagent-identity`，`stateVersion: 1`；
- `init: (header, inherited) => ({ inherited })`；`apply(state, event)`：只处理
  `subagent/descriptor`，`event.seq < inherited` 的继承事件忽略，其余把合法 `label`
  存入 `{ inherited, label? }`，其它事件原样返回（引用不变时注册表不会重复驱动）；
- 与 `message-projection.js` 相同的宿主能力探测：有 `stateOf` 用 host-only 单元，
  否则补 `schema` + `view` 走旧快照路径；
- `registerSubagentIdentity(ctx)` 返回 disposer 和 `labelOf(session)`；注册表缺失时
  `labelOf` 返回 `null`，整个特性安全降级为“只按 prompt 识别角色”。

`parseDispatchPrompt(messages, label)` 增加可选 label 参数：prompt 未命中时用
`roleFromLabel(label)`。push 侧调用 `labelOf(agent.session)`；`registerSubagentContext`
测试用 harness 没有注册表，label 为 `null`，行为与现在一致。

## 2. push 文案收敛（P2-2 / P3-1）

现状三处重复/冲突：

1. `subagentContextMessage` 前导：`Do not run task.py current … do not re-read task artifacts`；
2. `roleInstructionsFallback`：`The task context below is already prepared by dsh-trellis.`；
3. `role-contract.js` 的 `TASK_CONTEXT_SECTION`：同一句 prepared 说明。

改为：

- **前导**是唯一权威说明：任务上下文已随消息送达，不要运行 `task.py current`、不要向用户
  要任务路径、不要为了“发现任务”重读任务工件；
- **skill 已推送时**追加一句：`## Role Instructions` 是完整的角色 skill 正文，不要再加载
  `.dsh/skills/trellis-agent-<role>/SKILL.md`，也不要执行其中“自己加载上下文”的段落；
- **skill 缺失时**：提示加载路径一次，不再声明“已准备”，避免与 fallback 自相矛盾；
- `TASK_CONTEXT_SECTION` 只保留 `## Task Context` 标题 + 一句指向 `## Curated Context` 的
  指引，删除重复的 prepared 段落；
- `roleInstructionsFallback` 只保留“加载一次 skill”的提示。

结果：一条 push 中 `was prepared by dsh-trellis` 恰好出现一次；子代理收到的
“不要重读”和“加载 skill”不再互斥，因为 push 已明确 skill 正文就在消息里。

## 3. 守卫表述（P1-1）

- `inlineDenyReason`：保留两条出路（切 `dispatch_mode: auto` / `inline_allow_dispatch: true`），
  但改为“如果用户明确要求派发，请让用户决定”，并明确 `Do not edit .trellis/config.yaml
  to get past this guard`。
- README：`派发守卫会执行 inline 契约` → `派发守卫会拦截 inline 下的默认派发（提示性闸门，
  不是安全边界）`，并说明配置开关属于用户决定。

## 4. README 上游内容清除（R4）

删除清单（按标题/位置）：

- “本地分支”章节里“本副本基于上游 0.1.12 / 版本号重置”的叙述，改为只描述本插件与
  Codex 接线的对齐；保留三项对齐表与边界说明。
- `### 从 npm 安装（上游 0.1.12，不适用于本副本）` 整节（含 npm/desktop 安装、pnpm 11
  等待期、升级命令、file: 上游克隆流程）。
- 上游版本历史小节：`0.1.6`、`0.1.7`、`0.1.8`、`0.1.9`、`0.1.10`、`0.1.11`、`0.1.12`、
  `既有 DSH 0.1.5-rc.2 对齐`。
- 开发章节里指向上游仓库的验证记录链接、旧宿主 CI 叙述；只保留本地可执行命令。
- 保留 `0.1.1` 本地发布记录，并新增 `0.1.2` 本轮修复记录（不引用上游）。

## 5. 版本与 bundle

`package.json` 0.1.1 → 0.1.2；`pnpm run build:client` 重写 `lib/client.js`（版本常量由
tsdown 注入）。`test/client-bundle.test.js` 校验 bundle 与源码一致。

## 6. 验证策略

1. 单元：新增/更新 `dispatch-guard.test.js`、`subagent-context.test.js`、
   `subagent-identity.test.js`、`role-contract.test.js`；覆盖整段角色匹配、话题型描述
   放行、inline 拒绝、文本唯一性、descriptor label 折叠、注册表缺失降级。
2. 集成：真实 `AgentLoop` + `Session`（`native-subagent-push.test.js`）写入
   `subagent/descriptor` 后跑首轮，断言 label-only 角色收到 push、话题型 label 保持静默。
3. 全量：`pnpm test`（全部 test/*.test.js）。
4. 真实会话：用隔离 profile（`file:` 指向工作树）+ 临时 Trellis 项目跑 headless 会话，
   实际派发并检查子会话事件与工具结果；验证后清理临时 profile/项目，恢复用户配置。
5. 构建：`pnpm run build:client` + `git diff --stat` 复核。

## 7. 风险与回退

- descriptor 投影只读 `label`，不含任何任务数据；注册失败时降级，不影响面包屑/其它投影。
- label 兜底接受“角色名开头 + 标注”，覆盖真实出现的
  `trellis-agent-implement (audit round 3)`；话题型描述与“角色名后接普通词语”
  （`trellis-agent-check plugin docs`）仍保持 generic。prompt 仍是主通道。
- prompt 仍用子串匹配：它是指令通道，`Load the trellis-agent-check role skill` 必须继续
  识别；prompt 里“谈论角色名”仍是调用方的表达问题，不在本轮收紧。
- push 文案改动是纯文本，不影响任务解析与预算逻辑；旧 Trellis 项目 skill 布局缺失时走
  fallback 路径。
