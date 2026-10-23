# 已安装 dsh-trellis 对等性与补足独立复验报告

- 日期：2026-10-23
- 任务：`.trellis/tasks/10-23-dsh-trellis-installed-parity-reverify`
- 运行时：DSH `0.2.1-rc.2`；Trellis CLI/上游 `0.7.0-beta.4`；Codex CLI `0.163.0`；Node `v24.20.0`
- 验证对象：初测 **0.1.6**（2026-10-23 上午）；用户手动更新后复验 **0.1.7**（§11）
- 源码对照：`dsh-plugins/dsh-trellis` = **0.1.7**（更新后 `lib/` 与安装副本逐字节一致）
- 证据根：`/tmp/dsh-trellis-reverify-1023/`；索引见 `research/evidence-index.md`
- 修复闸门：**本报告只交付结论与候选方案；用户确认前未修改任何插件/仓库代码。**

## 1. 结论摘要

1. **主链路达到 Codex 使用 Trellis 的同等效果**（S1 实测）：bootstrap、每轮 workflow-state 面包屑、六种任务状态、路径级 spec deny-once/静默窗口/刷新、子代理上下文 push、角色识别、命令处理器（S2）、会话身份、升级后存活均通过；未发现 P0/P1/P2 级缺陷。
2. **补足了 DSH 裸用 Trellis 的主要缺口**（S1 对照实测）：无插件时 spec 可被静默违反、无自动注入、无子代理 push、无 fail-closed 守卫、无 `trellis_wait`、无托管身份、无 `/trellis-*` 命令；装插件后逐项补齐。插件的 `trellis_wait` 还使上游 workflow 中"无 wait 时传 `run_in_background: false`"的 DSH 指引不再被触发（该参数在 DSH 0.2.1 已移除）。
3. **更新到 0.1.7 后：文档滞后项已关闭，仅剩 1 项环境缺口 + 宿主限制观察**（§11）：
   - **F1a（已关闭）**：已安装 0.1.7 README 已含"headless 文本不路由 `/trellis-*`"说明；
   - **F1b（仍存在，宿主限制）**：headless 纯文本仍不走命令通道；本轮复测模型改为"命令未注册，我直接读 Trellis 状态"，未再声称"插件未安装"，但宿主层无法保证模型不自造输出；
   - **F2（仍存在，环境）**：`~/.dsh/profiles/headless` 仍未安装插件；
   - **F3 文档部分已关闭**：0.1.7 README 已含"避免同会话中途切换模式"；运行时投影设计未变；
   - **边界观察**：上游 O2、极端小上下文 compaction 反复、Codex hook 信任前提、bootstrap 频率设计差异；均不需修复插件。
4. **安装态与源码现在完全一致**：更新后已安装 0.1.7 与源码 0.1.7 `lib/` 逐字节一致（diff 为空），README 两项文档齐全；初测 S1 使用 0.1.6，更新后 S1 复验使用 0.1.7。
5. **单测回归**：350 tests / 346 pass / 0 fail / 4 skip（S4）。
6. **验证限制**：Web GUI（设置页/版本监控/冲突横幅）因本地鉴权未进入，降级 S2+S4；TUI/Web 命令路由未做真实 UI 调用；tdd 模板 registry 网络不可达；Windows 未验证；本轮末尾真实 LLM 余额耗尽，未再补充 S1。

## 2. 三臂对照矩阵

| 维度 | Codex + Trellis（S1） | DSH 裸用（S1） | DSH + 已安装插件（S1/S2） | 判定 |
| --- | --- | --- | --- | --- |
| 新会话 bootstrap | `UserPromptSubmit` 附 `<trellis-bootstrap>`（本轮实测一轮；每轮频率来自 hook 契约/前轮证据） | 无 | 每根会话一次，独立消息家族 | 达到同等（频率为设计差异） |
| 工作流状态 | `UserPromptSubmit` 注入 `workflow-state`（hook 契约；本轮实测一轮） | 无 | `agent/pre-step` 面包屑，未变不重复 | 达到同等 |
| 任务状态 | no_task/stale 等 | 依赖模型自查 | no_task/planning/in_progress/completed/stale/task_error/自定义状态全部正确 | 达到同等（stale 正文为增强） |
| 路径级 spec | PreToolUse `apply_patch` deny-once + `<spec-context>` | 无，spec 可被违反 | `tools/pre-execute` deny-once，`edit/write` 均生效；窗口/刷新/Read ticket/损坏回退均实测 | 达到同等（DSH 多持久化分片） |
| 子代理上下文 | `SubagentStart` 注入角色契约（agent TOML） | child 自行 pull，无 push | 首步 push 角色 skill 正文 + curated context | 达到同等（DSH 还能 fail-closed 守卫） |
| 子代理守卫 | 无（无任务时 child 仍可跑） | 无 | auto 无任务 implement/check 拒绝；inline 拒绝；research 放行 + 提醒 | **DSH 增强** |
| 角色识别 | 由 Codex agent 类型决定 | 无 | 声明式识别；话题型 description/路径提及不误判 | 达到同等 |
| 命令面 | 无项目级 `/trellis-*` 命令 | 无 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor`（交互输入面） | **DSH 增强**（headless 文本受宿主限制） |
| 会话身份 | Codex thread/session | 仅 `DSH_SESSION_ID` | `DSH_TRELLIS_CONTEXT_ID=dsh_<sid>`，task.py 解析一致 | **DSH 增强** |
| 模式配置 | `codex.dispatch_mode` | 无 | `dsh.dispatch_mode` 只读；默认 inline；不写 tracked config | 达到同等（默认值不同是已确认设计） |
| 子代理同步 | Codex 原生 wait/通知 | 无事件汇合；workflow 指引已过期 | `trellis_wait` 真实汇合；无效 id fail-closed | **DSH 增强** |
| 安装/升级 | hooks + agents | `trellis init --dsh` | git path 安装 + `trellis update --skip-all` 后存活 | 达到同等 |
| 运维面 | 无 | 无 | doctor/版本路由/冲突检测/设置页逻辑 | **DSH 增强**（GUI 未实测） |

## 3. 主链路实测结果

### 3.1 上下文注入与状态

- **S01**：no_task 首轮注入 breadcrumb + bootstrap；`<dsh-mode>` inline 说明完整。
- **S01b**：同 session `--session-id` 新进程续跑，**未重复**注入 bootstrap/面包屑。README 0.1.6 的"headless resume 可能再注入一次"是保守表述，实测未发生（更优方向）。
- **S02**：`task.py create` → `planning-inline`；`start --allow-empty-context` → `in_progress-inline`；status=completed → `completed`；损坏 task.json → `task_error`；不存在目录 → `stale` 专用文案。状态未变不重复。
- **S08**：plain 目录 0 条插件消息；无 `.git` 的 Trellis 项目正常注入；`no-trellis` 独立词整轮跳过。
- **S09**：显式 auto 下面包屑为 `in_progress`、无 `<dsh-mode>` banner；全轮后 `.trellis/config.yaml` sha256 不变，无 `dsh:` 段写入。
- **S15**：自定义 `[workflow-state:reviewing]` 块正确渲染（自定义状态透传）。tdd 模板因 registry 网络不可达未切换，记录为限制。

### 3.2 路径级 spec 注入

| 场景 | 结果 |
| --- | --- |
| 根目录 `write src/app.js` | 首次 deny，reason 含完整 spec 正文 + sha256；重试成功 |
| 窗口内 `write src/b.js` | 不 deny（静默） |
| spec 内容变更后 `write src/c.js` | 重新 FULL deny，sha 更新 |
| 子目录 cwd=`src` + `write d.js` | 正确并集匹配并 deny |
| `edit src/app.js` | deny（默认 edit/write 均生效） |
| `tools:[Read]` + `read src/app.js` | read 不阻断；post-execute 以 `form=spec-context` 送达正文 |
| 损坏分片（非法 JSON） | 下一次触碰重新 FULL deny（安全回退） |
| 两会话并发写不同文件 | 各自一次 deny 后合规；分片互不串扰 |
| compaction 后 | 真实 24k 窗口触发 2 次 compaction；结束后 breadcrumb + bootstrap 重新注入 |

**行为边界（非缺陷）**：当用户 prompt 明确指定精确内容（如"content 'export const demoSpec = 1;'"）时，模型会优先服从用户而忽略 spec 的第一行/尾注。deny 与 spec 正文均已送达；这是模型优先级问题，Codex 侧同样可能发生。

### 3.3 子代理

- **S04**：auto 下派发 `trellis-agent-implement`，子会话首步收到 `form=subagent-context role=implement`，含：
  - "Trellis Native Implement Subagent" 角色契约；
  - 递归防护；
  - 指向 `.trellis/tasks/10-23-auto-push` 的 curated context（空 jsonl 时给出明确提示）；
  - 子会话无 breadcrumb/bootstrap（设计正确）。
- **S05**：inline + 活跃任务 → deny，文案给出"改 config 或 `inline_allow_dispatch`"两条出路；auto + 无任务 → fail-closed deny，子代理未启动。
- **S06**：无任务 research 放行，父会话收到位置提醒；话题型 description 不触发 push/守卫；generic child 无 push。
- **S07 无效 wait**：不存在的 child id 被明确拒绝。
- **S06 wait 成功**：`trellis_wait` 返回 `completed; settlement notice delivery is unverified; inspect its report…`，未冒充干净 settled。

### 3.4 身份

- 模型 shell 内：`CTX=dsh_session-<sid>`、`SID=session-<sid>`、`SHELL=1`。
- 绑定任务后 `task.py current --json` 返回该 session 的任务，`source=session:dsh_session-<sid>`。
- 命令处理器子进程使用同一 key（S2：`runTrellisScript` 注入 `TRELLIS_CONTEXT_ID`/`DSH_TRELLIS_CONTEXT_ID`）。

### 3.5 命令/运维（S2）

- 注册：`trellis-status`、`trellis-finish`、`trellis-doctor`。
- `trellis-status`：输出当前任务、来源、git status、session rituals 提示。
- `trellis-finish`：只读检查 + 安全收尾清单，不提前清指针。
- `trellis-doctor`：项目根、插件 0.1.6、Trellis 0.7.0-beta.4、workflow 块数、dispatch mode、活跃任务、spec 配置、冲突状态。
- 带参数调用 → 明确拒绝；非 Trellis 目录 → "No project root found…"。
- 冲突决策：no loader=`unavailable`；仅自身=`checked` 无冲突；重复插件=`checked` + `dsh-trellis-fork`。
- 版本路由：`source=npm` 返回 dist-tags；`source=plugin` 走 Atom/REST（stub 下 feed 解析失败但错误路径正确返回）。

### 3.6 升级

- `trellis update --skip-all`：项目已是最新，更新后 breadcrumb/bootstrap 正常。
- 插件安装形态：web profile 通过 git path 安装；已安装副本与源码 `lib/` 仅版本 stamp 差异。

## 4. 补足评估（DSH 裸用 → 插件）

| DSH 裸用实测缺口 | 证据 | 插件后 | 判定 |
| --- | --- | --- | --- |
| 无 bootstrap/面包屑 | `b02-spec-bare`、`b04` 无插件消息 | 六状态面包屑 + 每会话 bootstrap | **已补足** |
| spec 可被静默违反 | `b02` 写 `src/bare.js` 成功且无 `// demo-spec-applied` | deny-once + 正文 + 重试；窗口/刷新/子目录/Read ticket | **已补足** |
| 无子代理 push | `b03` child 无任何注入 | 角色契约 + curated context | **已补足** |
| 无 guard | `b03` 无任务 implement 照常启动 | inline/no_task fail-closed；research 提醒 | **已补足（增强）** |
| 无 `trellis_wait` | 无 | 事件驱动 wait；无效 id 拒绝 | **已补足（增强）** |
| 无托管身份 | `b04` `DSH_TRELLIS_CONTEXT_ID` 为空 | `dsh_<sid>` 全链一致 | **已补足** |
| 无命令面 | 无 | status/finish/doctor（交互面） | **已补足（headless 受宿主限制）** |
| workflow 的 `run_in_background:false` 指引在 DSH 无效 | 上游 O2 | `trellis_wait` 存在 → 上游走 wait 分支，不再需要该参数 | **已补足（条件性）** |

**结论**：没有发现"部分补足/未补足"的主链路项；唯一未补的是宿主不允许的 headless 命令路由，以及 headless profile 未装插件的环境覆盖。

## 5. 安装态与源码对比

### 5.1 更新前（初测）：已安装 0.1.6 ↔ 源码 0.1.7

| 项 | 结果 |
| --- | --- |
| `lib/` 逐字节对比 | 仅 `lib/client.js` 的 `PLUGIN_VERSION` 不同（0.1.6 vs 0.1.7） |
| 运行时逻辑 | 无差异；S1 全部在隔离 profile 的**已安装副本**上执行，运行前 `diff -rq` 证明一致 |
| README | 0.1.7 多出"headless 文本限制"与"避免同会话中途切换模式"两节；已安装 0.1.6 **没有** |
| 影响 | 运行时不受影响；headless 用户缺少边界文档，模型可能自行编造命令输出/错误声明（见 F1a） |

### 5.2 更新后（2026-10-23 16:30）：已安装 0.1.7 ↔ 源码 0.1.7

| 项 | 结果 |
| --- | --- |
| 版本 | web profile `package.json` = 0.1.7；`client.js` 版本 stamp = 0.1.7 |
| `lib/` 逐字节对比 | **diff 为空**（完全一致） |
| README | "headless 文本限制"与"避免同会话中途切换模式"两节均存在（grep 各 1 处） |
| 影响 | F1a/F3a 的"安装态文档滞后"关闭；运行时行为与 0.1.6 相同（lib 一致） |

## 6. 问题清单（待确认；未修复）

### F1（P3）headless 文本不路由 `/trellis-*`

#### F1a（更新后已关闭）安装态文档滞后

- 初测已安装 0.1.6 README 没有 0.1.7 的 headless 限制说明；更新后 0.1.7 README 已包含该节（§5.2），**该项关闭**。

#### F1b（仍存在，宿主限制）headless 纯文本没有命令通道

- **现象**：`s16-headless-command`（0.1.6）中 prompt 为 `/trellis-status`，命令通道未触发；模型自行跑 `get_context.py`/`task.py` 拼装，并称"当前未安装"——而同会话已有 bootstrap + 面包屑注入。
- **更新后复测**：`u05-headless-command`（0.1.7）中模型改为表述"`/trellis-status` isn't registered as a command handler in this session (it ships with the optional dsh-trellis plugin)，所以我直接从 Trellis 状态生成报告"，并输出基于 `get_context.py`/任务目录的状态；**本轮未再声称"插件未安装"**，但仍是模型仿制而非命令输出。
- **归属**：DSH 宿主的命令路由只在交互输入面生效（headless 纯文本无命令通道）；插件无法在 headless 注册命令处理器。
- **影响**：headless/管道用户以为在执行命令，实际拿到模型拼装结果；模型偶发事实错误的风险仍在（不可由文档完全消除）。
- **候选方案**：
  - **A（已执行）**：更新到 0.1.7，README 带上 headless 限制与等价 shell 命令；已完成。
  - **B（可选，小改动+测试）**：在 headless 场景的 bootstrap/面包屑追加一行"`/trellis-*` 在 headless 文本不路由，请用 `.trellis/scripts/...` 等价命令"，直接降低模型误判概率。
  - **C**：维持现状（文档已说明）。
- **建议**：A 已完成；若你希望进一步降低误判率，再做 B；否则接受宿主限制。

### F2（P3·环境覆盖）`~/.dsh/profiles/headless` 未安装 dsh-trellis

- **现象**：真实环境 web profile 已更新到 0.1.7；`~/.dsh/profiles/headless` 仍未安装 dsh-trellis（隔离 `bare-headless` 证明无插件时无注入/无守卫/无 spec 强制）。
- **归属**：环境部署选择，不是插件缺陷。
- **影响**：若用 headless profile 跑 Trellis，行为等同裸 DSH（且命令文本不可用）。
- **候选**：① 在 headless profile 安装本插件（注入/守卫/spec 生效，命令仍受 headless 限制）；② 明确只用 web profile 跑 Trellis；③ 维持现状并文档说明。
- **建议**：按实际使用面选择；若 headless 会跑 Trellis，选 ①。

### F3（P3·文档/设计边界）同会话切换 `dsh.dispatch_mode` 后旧 `<dsh-mode>` banner 留在历史

- **状态**：本轮未复现（未做切换场景）；上一轮归档任务有 S1 证据。源码 0.1.7 README 已加"避免同会话中途切换/优先新开会话"；更新后已安装 0.1.7 README 已包含（F3a 文档部分关闭）。运行时投影设计仍未变。
- **归属**：投影去重设计下旧 banner 不会随配置变化撤回；状态变化会注入新面包屑，但"模式已变"没有专门通告。
- **影响**：低频；一次用户澄清即可恢复。
- **候选**：A（已执行）更新到 0.1.7 带文档；B 模式变化时随新面包屑附一行"旧 banner 已过期"（小改动+单测）；C 维持现状。
- **建议**：A 已完成；B 可选（仅在确实频繁切换模式时）。

> 说明：本轮**未发现 P0/P1/P2**。更新后 F1a/F3a（文档滞后）已关闭；F1b 是宿主限制，F2 是环境部署选择；均不构成插件运行时缺陷。

## 7. 边界观察（不进入修复清单）

### O1 上游 Trellis 的 DSH 指引仍含已移除参数（只读政策）

- `get_context.py --mode phase --step 2.1 --platform dsh` 仍输出："Without `trellis_wait`, dispatch that child with `run_in_background: false`"；DSH 0.2.1-rc.2 已移除该参数。
- 装插件后 `trellis_wait` 存在，上游走 wait 分支，该指引**不会被触发**；裸 DSH 才会踩到。按上游只读政策，仅记录，不提上游补丁。

### O2 极端小上下文 + spec 重教学的自激循环

- 在 24k context window、40KB `read`、spec deny 的组合下，`compaction/end` 清除 spec 状态→重试再次 deny→再次 compaction，首轮 420s 超时未完成（`s13b-*`）。
- 正常 1M 窗口下 compaction 阈值约 800k，实际触发频率低；该现象属于人工极端配置的边界，不作为插件缺陷。若未来要处理，可考虑"同一工具调用链内 compaction 后不重复 FULL deny"或限制重教学频率，但会削弱"压缩后必须重新教学"的正确性。

### O3 Codex hook 信任前提

- 真实 `codex exec` 触发 hook 需要：隔离 `CODEX_HOME` 中项目 `trust_level = "trusted"` + `--dangerously-bypass-hook-trust`（或交互式 `/hooks` 审批）。这是 Codex 侧安全机制，不是插件缺陷；本轮已在隔离 home 中真实触发三个 hook。

### O4 bootstrap 频率差异

- 插件侧本轮 S1 复现"每根会话一次"；Codex 侧"每轮"来自其 `UserPromptSubmit` hook 契约与前轮证据（本轮只跑了一轮 Codex）。插件 README 已说明这是避免噪音的设计选择；用户此前已确认，未视为缺陷。

### O5 resume 行为与 README 保守表述

- README 0.1.6 称 headless `--session-id` 新进程可能再注入一次 bootstrap；实测未重复（`s01b`）。这是更优方向，建议未来文档改为"实测不重复，投影状态随会话日志重放"。

## 8. 验证限制与补偿

| 未覆盖项 | 原因 | 补偿 |
| --- | --- | --- |
| Web GUI 设置页/版本监控/冲突横幅 | 本地鉴权，凭证纪律不允许把 token 写入 URL/命令行 | S2 路由/决策 + S4 `client-*`/`version-check`/`conflict-view` 单测 |
| TUI/Web 命令输入面真实路由 | 无交互式会话；headless 文本不路由 | S2 命令处理器全量执行；S16 记录 headless 限制 |
| tdd 工作流模板 | registry 网络不可达 | 自定义 `[workflow-state:reviewing]` 已实测；tdd 仅记录限制 |
| Windows 路径/编码 | 本机 Linux | 不适用 |
| 真实 LLM 剩余场景 | 末尾 `QUOTA: Insufficient Balance` | 所有关键断言已有 S1 观测；未测项明确列出 |
| 应用内真实 compaction 的 1M 场景 | 需要接近 800k token，成本不可行 | 用 24k 窗口真实触发 compaction（S1），验证重注入；spec 重置由 S4 单测 + 本报告 O2 边界覆盖 |
| 隔离 profile 初期 bash 工具不可用 | 复制的旧隔离骨架缺 `@deepseek-ai/dsh-bash-local`/`dsh-subprocess` 等包（`subprocess scope exited…`） | 从宿主补齐缺失包后 bash 正常；这是测试环境搭建问题，不是插件缺陷；补齐后所有需要 bash 的场景均通过 |

## 9. 待用户确认的执行方案

> 以下只是候选，**确认前不修改任何代码/文档/安装态**。

| 编号 | 问题 | 当前状态 | 剩余可选动作 |
| --- | --- | --- | --- |
| F1a | 安装态文档滞后 | **已关闭**（用户已手动更新到 0.1.7，README 已含 headless 说明） | 无 |
| F1b | headless 文本无命令通道（宿主限制） | 仍存在；u05 复测未再出现"插件未安装"错误声明，但仍为模型拼装 | 可选 B：bootstrap 增加 headless 提示（代码+测试）；或接受现状 |
| F2 | headless profile 无插件 | 仍存在（`~/.dsh/profiles/headless` 无 dsh-trellis） | 若 headless 会跑 Trellis，安装插件；否则维持 |
| F3a | 模式切换旧 banner 文档 | **已关闭**（0.1.7 README 已含"避免同会话中途切换"） | 无 |
| F3b | 模式切换旧 banner 运行时通告 | 设计未变；本轮未复现 | 可选 B：模式变化附"旧 banner 已过期"一行；或接受现状 |
| O1–O5 | 上游/设计边界 | 不处理，仅记录 | 无 |

**下一步**：A 类（F1a/F3a）已由你手动完成。若还要处理 F1b/F2/F3b，请指定；否则本任务可进入收尾（更新报告结论后按流程归档）。

## 10. 证据位置

- 主索引：`research/evidence-index.md`
- 关键 S1：`/tmp/dsh-trellis-reverify-1023/evidence/{s01,s02*,s03*,s04,s05*,s06*,s07*,s08*,s09,s10*,s12*,s13*,s14,s15*,s16,b0*,c0*,u0*}.jsonl`
- 会话日志：`/tmp/dsh-trellis-reverify-1023/home/sessions/**/session.v4.jsonl.zstd`
- Codex rollout：`/tmp/dsh-trellis-reverify-1023/codex-home/sessions/2026/10/23/`
- S2/S4/契约：`evidence/s2-modules.out`、`evidence/s4-unit.out`、`evidence/h04-host-upstream.out`
- 隔离环境：`home/profiles/{trellis-headless,bare-headless}`；`proj`、`auto`、`nogit`、`ticket`、`update`、`custom`、`compact`、`plain`


## 11. 更新后复验（0.1.7，2026-10-23 16:30 起）

### 11.1 安装态

- 已安装 web profile：`dsh-trellis` **0.1.7**（`package.json`、`lib/client.js` 版本 stamp 均为 0.1.7）。
- `diff -rq` 已安装 `lib/` ↔ 源码 `lib/`：**空**（逐字节一致）。
- README：`headless 文本限制` 与 `避免同会话中途切换` 各 1 处。
- 隔离测试 profile 已替换为同一 0.1.7 副本，复验前 `diff -rq` 一致。

### 11.2 S1/S2 复验结果

| 场景 | 结果 | 证据 |
| --- | --- | --- |
| u01 no_task bootstrap + 面包屑 | 正常，注入文本与 0.1.6 一致 | `evidence/u01-smoke.jsonl` |
| u02 spec deny-once | 写 `src/u02.js` 首次 deny（count=1），随后重试 | `evidence/u02-spec.jsonl` |
| u03 inline 守卫 | 任务绑定 session 中派发 implement → inline deny，文案与 0.1.6 一致 | `evidence/u03-guard.jsonl` |
| u04 auto 子代理 push | 真实 child 收到 `form=subagent-context role=implement` + 角色契约 + curated context | `evidence/u04-push.jsonl`；child `1b07c131…` seq12 |
| u05 headless `/trellis-status` | 命令仍未路由；模型改为"命令未注册，我直接读 Trellis 状态"，**未再声称插件未安装**；输出为模型拼装 | `evidence/u05-headless-command.jsonl` final |
| S2 doctor/命令/冲突/版本 | 已安装 0.1.7 直载：命令注册、doctor 版本 0.1.7、冲突 duplicate、版本路由 200 | `evidence/u02-s2-modules.out` |
| 单测 | 350 tests / 346 pass / 0 fail / 4 skip（源码 = 安装态 lib） | `evidence/s4-unit.out` |

### 11.3 更新后判定

- **F1a 已关闭**：安装态 README 不再缺 headless 边界文档。
- **F1b 仍存在（宿主限制）**：headless 纯文本没有命令通道；插件无法注册命令处理器。u05 显示模型不再错误声称插件未安装，但仍是模型拼装结果，不能当作命令输出。
- **F2 仍存在（环境）**：headless profile 仍未安装插件。
- **F3a 已关闭**：模式切换文档已随 0.1.7 安装。
- **F3b 未变**：运行时投影不撤回旧 banner；本轮未复现，保留为上轮 S1 证据 + 文档已覆盖。
- **无回归**：0.1.7 与 0.1.6 `lib/` 完全一致；复验的 bootstrap/spec/guard/push 均通过；未发现 P0/P1/P2。

### 11.4 最终结论（基于最新安装态）

1. 当前已安装 **0.1.7** 与源码一致，主链路对等性与补足结论不变。
2. **唯一仍实际存在的缺口是 F2（headless profile 未装插件）**；F1b/F3b 是宿主/设计边界，文档已覆盖，是否进一步用代码缓解由你决定。
3. 若不再处理 F2/F1b/F3b，本任务验证部分可以收尾；修复/安装动作仍需你明确授权。
