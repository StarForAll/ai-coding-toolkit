# Verification Report：dsh-trellis 0.1.2 缺陷修复

日期：2026-10-22　环境：DSH `0.2.1-rc.2`（安装态）、Node `v24.20.0`、pnpm `12.14.0`、
隔离 profile `trellis-fix-verify`（`file:` 指向工作树）。

## 1. 自动化测试

```bash
cd dsh-plugins/dsh-trellis
node --test "test/*.test.js"
```

结果：**356 tests / 352 pass / 0 fail / 4 skipped**（第二轮修复后；首轮为 351/347）。
跳过项为 alpha-only 集成用例
（`@deepseek-ai/dsh-working-directory` 未安装），与本次改动无关。

新增/更新用例：

| 文件 | 覆盖点 |
| --- | --- |
| `test/subagent-identity.test.js` | descriptor label 折叠、fork 继承忽略、迟到注册重放、legacy registry、无注册表降级 |
| `test/native-subagent-push.test.js` | 真实 AgentLoop + Session + `subagent/descriptor`：label-only 角色收到 push |
| `test/dispatch-guard.test.js` | description 兜底、prompt 优先、description-only 的 inline 拒绝与无任务拒绝、拒绝文案约束 |
| `test/subagent-context.test.js` | label 兜底、skill 已推送/缺失两种文案、prepared 语句唯一 |
| `test/index.test.js` | 新投影随 runtime 注册/卸载 |

`test/client-bundle.test.js`：通过（bundle 与源码一致，版本 0.1.2）。

## 2. 真实 DSH 会话调用（无外部模型，真实工具/子代理运行时）

脚本化适配器（`/tmp/dsh-scripted-model`）只负责发出一次真实的 `subagent` 工具调用，
其余链路全部是宿主真实实现：`tools` 守卫 → `dsh-tool-subagent` → `subagent` runtime →
真实子会话 + `subagent/descriptor` → 插件 push。临时项目由 `trellis init --dsh` 生成。

### 2.1 description-only 角色 + 有任务前奏（`dsh.dispatch_mode: auto`）

- 工具参数：`description = "trellis-agent-implement"`，prompt 仅含
  `Active task: .trellis/tasks/10-22-push-verify`（**不含角色名**）。
- 父会话 `session-f35ebb81…`：`tool/call subagent` → `tool/result isError=false`
  `started subagent d14ff346…`。
- 子会话 `d14ff346…`：`subagent/descriptor.label = "trellis-agent-implement"`；
  首轮请求前收到 push（4,232 字节）：
  - `# Trellis Native Implement Subagent`、`Active task: …`；
  - `prepared by dsh-trellis` 出现 **1** 次，`## Task Context` **1** 次；
  - 含“Do not load `.dsh/skills/trellis-agent-implement/SKILL.md` again …”；
  - 含角色 skill 正文（`## Recursion Guard` 等）与 curated context。
- 结论：P2-1 的 push 假阴性在真实宿主上消失；P3-1 重复消失；P2-2 的互相排斥指令被
  单向权威说明取代。

### 2.2 generic 子代理（无角色）

- `description = "summarise the log"`，prompt 无角色。
- 子会话 `e2489674…`：**没有** push。
- 结论：静默契约保留，未因 label 兜底误判。

### 2.3 research（无任务）

- `description = "trellis-agent-research"`，prompt 无 `Active task:`。
- 父会话收到 `<trellis-dispatch-guard>` 的 research notice（post-execute
  additionalContexts），工具成功。
- 子会话无 push：该会话没有任务路径（无指针、无前奏），按现有设计跳过 push。
- 结论：守卫侧的 description 识别生效；research 允许无任务派发的行为未变。

### 2.4 implement 无任务（`auto`）

- `description = "trellis-agent-implement"`，prompt 无 `Active task:`。
- `tool/result isError=true`：`Trellis dispatch guard: no readable active task …`。
- 结论：fail-closed 行为不变，且 description-only 不再绕过。

### 2.5 inline 模式（插件自动写入 `dsh: dispatch_mode: inline`）

- 同一 description-only implement 派发。
- 父会话 `session-1b52afd2…`：`tool/result isError=true`，正文为新的拒绝信息：
  “Leaving inline mode is the user's decision, not yours … Do not edit
  `.trellis/config.yaml` to get past this guard … not a security boundary.”
- 没有创建任何子会话。
- 结论：P1-1 的自我绕过路径在文案层被明确关闭；守卫仍可被有写权限的模型绕过（设计已
  在 README/spec 中如实声明）。

证据来源：`~/.dsh/sessions/--tmp-dsh-trellis-fix-auto-proj--/`、
`~/.dsh/sessions/--tmp-dsh-trellis-fix-inline-proj--/`（本次验证创建，可删除）。

## 3. 构建与 bundle

- `pnpm run build:client` 成功；`lib/client.js` 仅版本常量变化（0.1.1 → 0.1.2）。
- `client-bundle.test.js` 通过。

## 4. 未覆盖 / 边界

- 未用真实大模型跑派发：模型是否遵守“不要再次加载 skill”属于模型合规，不是插件行为；
  本次验证的是插件在真实宿主中实际产生的消息与守卫结果。
- `test:compat` 旧宿主矩阵未重跑（本机只安装 `0.2.1-rc.2`）；dev 基线 `0.2.0-rc.1`
  的全量测试已通过，legacy projection 分支有单元覆盖。
- 版本监控的“来源仓库”能力仍在代码与设置页中（`versionCheckPluginRepo`，默认值在
  代码/设置页，README 不再给出该地址）；README 已删除来源、版本历史、npm 安装叙述，
  `grep -n "SajoLuo\|上游" README.md` 无结果。

## 5. 0.1.2 追补：话题型 description 误判（2026-10-22 第二轮）

### 问题真实性

已确认：0.1.2 首版对 `description` / descriptor label 用子串匹配，`description` 只要
出现 `trellis-agent-*` 就被当成角色。对话题型描述：

- `研究 trellis-agent-implement 插件的 README` → 守卫判定 implement → 无任务时
  `no readable active task` 拒绝（0.1.1 放行，属用户可见回归）；
- `about trellis-agent-check plugin docs` → 有任务时 generic 子代理被推送 Check 角色契约。

代码级复现（改前）：`parseDispatchRequest("Do it", topical)` 返回
`{role:"implement"}`，`parseDispatchPrompt` 同样返回 check/implement。

### 修复

`roleFromLabel`（`lib/role-contract.js`）要求**整个 label** 等于
`trellis-agent-<role>` / `trellis-<role>`（忽略大小写与包裹引号、尾部标点）。
守卫与 push 的 label 兜底都改用它；prompt 仍用原有子串匹配（prompt 是指令通道，
`Load the trellis-agent-check role skill` 必须继续识别）。

### 真实会话验证（同一隔离 profile / 真实 subagent 工具）

- auto 项目，`description = "研究 trellis-agent-implement 插件的 README"`，
  无任务前奏 → `tool/result isError=false`、子会话 label 为原话题文本、**无 push**；
  有任务前奏 → 同样放行、**无 push**（未错推 Implement 契约）。
- inline 项目，`description = "about trellis-agent-check plugin docs"` → **放行**，
  子会话 generic、**无 push**（修复前会被 inline 守卫拒绝/推送 Check 契约）。
- 回归对照：`` `Trellis-Agent-Check` ``（带反引号、大小写混合）→ 子会话收到
  Check push，`prepared by dsh-trellis` 1 次。

### 自动化

- 新增 `test/role-contract.test.js`（整段匹配与话题型反例）、guard 话题型放行用例、
  push 话题型安静用例、真实 Session 的 topic-child 用例。
- 全量：**356 tests / 352 pass / 0 fail / 4 skipped**。

### P3 簿记

`LOCAL_CHANGES.md` 补齐 `0.1.2` 小节（Added/Changed，含本轮话题型修复）。

## 6. 已安装插件实测（2026-10-22 11:00）

### 安装态

- `~/.dsh/profiles/web/node_modules/dsh-trellis` 版本 **0.1.2**，`lib/` 与本仓库已提交
  版本逐字节一致（`diff -rq` 为空），新模块 `lib/subagent-identity.js` 存在。
- 安装时间 10:51:45；运行中的 `dsh web` 进程 PID 5538 启动于 08:14:50，**早于**安装，
  因此该进程内存里仍是更新前的模块实例；HMR 只覆盖 profile 的 `file:` 模块，web 的
  `dsh-trellis` 是 ssh git 依赖，不会热更新。要让界面实际使用 0.1.2/0.1.3 需重启。

### 用安装产物跑真实链路

复制一个临时 profile，用 `file:` 指向 **已安装目录**（不是工作树），真实 `subagent`
工具 + subagent runtime + 子会话，仅模型响应脚本化：

| 场景 | 结果 |
| --- | --- |
| exact `description = trellis-agent-implement` + `Active task:` | 派发成功；子会话 implement push；prepared ×1；不重载 skill 提示存在 |
| `description = 研究 trellis-agent-implement 插件的 README` + 前奏 | 放行；generic，无 push |
| 同上，无前奏 | 放行（不再 “no readable active task”） |
| inline + exact implement | 拒绝；新文案含“user's decision”“not a security boundary” |
| inline + `about trellis-agent-check plugin docs` | 放行；generic，无 push |

安装态对报告的问题全部符合预期；但发现带标注的角色 label（用户 r3 会话中的
`trellis-agent-implement (audit round 3)`）被整段规则判为 generic，push 缺失。

### 0.1.3 补强

`roleFromLabel` 改为“角色名开头 + 可选标注”（空白后的 `:`/`：`、`(`/`（`、`[`/`【`、
`-`、`–`、`—`）；话题型描述与“角色名后接普通词语”仍为 generic。版本 0.1.3，
bundle 重建，新增 `docs/validation-0.1.3-local.md`。全量 356/352/0/4。
