# dsh-trellis

DeepSeek Harness (dsh) host 插件：把 [Trellis](https://github.com/mindfold-ai/Trellis) 工作流带进 dsh，并尽量沿用 DSH 原生能力补齐 Codex / Claude Code 级体验：

1. **每轮 workflow-state 面包屑注入** — 在每个 `agent/pre-step`，解析项目 `.trellis/workflow.md`（或任务/个人/团队选定的 workflow 变体）的 `[workflow-state:*]` 块 + 活跃任务状态（no_task / stale / task_error / planning / in_progress / completed / 团队自定义状态），把对应面包屑注入会话（与 `dsh-agent-instructions` 的注入管道相同）。未变化不重复注入；被压缩后自动重注入；提示词里出现独立单词 `no-trellis`（或项目 `prompt_injection.skip_keyword` 配置的词）可跳过该轮（turn）的全部请求，包括工具调用之后的后续 step（与 Codex 的 `UserPromptSubmit` 按轮判定一致）。
2. **隔离的原生会话上下文身份** — 从当前 agent 的 DSH 原生 session header 生成受管的 `DSH_TRELLIS_CONTEXT_ID`，让 `task.py start/create/current` 解析到会话级 active-task 指针，并在子代理身份不同于 shell 自身 session 时优先使用被转发的身份；插件命令启动的子进程也显式使用同一个 DSH 身份。
3. **原生子代理同步** — 安装插件后，Trellis 角色可用 DSH continuable 后台子代理；主会话先继续独立工作，耗尽后可调用事件驱动的 `trellis_wait`。它监听 DSH 的 `subagent/end`，利用 lifecycle 自带的 run/provider/output-block 元数据返回 `completed / failed / aborted / unknown` 的 fail-closed 结论。`error`、`max-tokens`、`refusal` 和未来未知失败原因都不会被误报成通过。rc.8 在父会话 idle 时也会用原生 settlement notice 唤醒，因此已经结束当前轮时无需额外调用 wait。
4. **子代理首步上下文 push** — 在子代理第一个 `agent/pre-step` 注入角色契约（目标项目 `.dsh/skills/trellis-agent-<role>/SKILL.md` 正文，去掉 frontmatter）与 curated task context。任务路径优先取 dispatch prompt 的 `Active task:`，其次才是父会话指针；两者都取不到（父会话从未绑定任务）时不 push —— 与 Codex 在 task_dir 缺失时静默返回一致，research 另外会收到 dispatch-guard 的输出位置提醒。角色 skill 缺失时至少注入路径提示，不静默省略。**角色识别是声明式的**：dispatch prompt 的首行角色前缀（`trellis-agent-implement: …` / `trellis-implement (round 3)`）、独立标记行（`Role: trellis-agent-implement` / `Agent: trellis-check`）、或 Trellis 派发语（`You are the trellis-implement sub-agent/role`），以及 dispatch `description` 的严格角色前缀；只提到 `.dsh/skills/trellis-agent-*/SKILL.md` 路径或普通叙述（如「跑 trellis-check 技能」）不再触发 push/守卫。未命中时子代理走 child-pull 路径。
5. **`/trellis` 命令** — `/trellis-status`（活跃任务 + git 状态）、`/trellis-finish`（只读检查 + 安全收尾清单，不提前清 active-task 指针）。任务读取优先使用 `task.py current --json`；旧版 Trellis（0.6.10 之前没有该参数）自动回退到 `current --source` 的文档化输出。命令输出不进模型历史；真正的会话收尾走技能面 `/trellis-finish-work`，由技能先归档再写 journal。rc.8 下两条零输入命令使用 `recordInput: false`，并显式拒绝参数和图片附件，避免静默忽略输入。
6. **项目级模式（只读）** — `.trellis/config.yaml` 的 `dsh.dispatch_mode` 缺省为
   `inline`（主会话直接实现/检查），显式 `auto` / `sub-agent` 才派发角色子代理。
   插件**不写**项目配置：不追加键、不改注释/换行、不创建缺失的 config，也不再提供
   “首次进入自动补 inline”的迁移；模式只从现有配置读取。
7. **Web 配置菜单** — DSH `0.1.7-rc.1` 的“插件 → dsh-trellis”详情页直接显示全部六个配置项；保留 `0.1.6-alpha.2` 详情页与旧版 RC 卡片。新版支持带修订号的原子保存、恢复 profile 继承值和冲突时保留草稿。配置里的 `enabled=false` 会停用工作流功能但保留表单；插件管理器的整包或组件开关则会连同表单一起卸载。

非 Trellis 项目不注入面包屑；命令只有被用户显式调用时才会检查并返回“未初始化 Trellis”。

这是 Trellis DSH 适配的**可选伴侣插件**，不是使用 `trellis init --dsh` 的前置条件。存在 `trellis_wait` 时可使用 continuable 后台派发和事件汇合。未安装插件时，只有工具 schema 明确支持 `run_in_background` 的旧宿主才设置 `run_in_background: false`；DSH `0.2.1-alpha.2` 已移除该参数，统一立即返回 child ID，应让父会话结束当前轮、由原生完成通知唤醒，或直接在主会话完成工作。收到 child ID 不代表依赖步骤通过；没有可用的事件汇合或可靠原生通知路径时不要派发。所有路径都禁止 sleep 或轮询，Trellis CLI 不会自动安装任何 DSH profile 插件。

## 对齐 Codex 的三项 Trellis 接线

当前版本 **0.1.6**。普通修改按 `0.1.0 → 0.1.1 → 0.1.2 → 0.1.3 → 0.1.4 → 0.1.5 → 0.1.6` 递增；只有运行时/配置契约
破坏或大改才提升次版本/主版本。三项主链路已经对齐，但 DSH 的事件形状仍带来下面的
差异，因此本插件不宣称与 Codex 完全一致。

配置入口是 **设置 → Trellis**，插件详情页不显示表单。

| 能力 | Codex 的实际接线 | 本插件（DSH） |
| --- | --- | --- |
| 无任务 bootstrap | `UserPromptSubmit` 每轮附 `<trellis-bootstrap>` | 独立消息家族（`source.kind=dsh-trellis`、`source.form=bootstrap`）与独立 projection：新根会话每会话一次，与面包屑状态变化解耦，只有压缩移除后才重新提示；子代理永不注入。**首轮没有开始 Trellis 时，本会话后续不再重复催促是设计选择，不是缺陷**（见下文） |
| 路径级 spec 注入 | `PreToolUse` 匹配 Edit/Write；FULL 时 deny-once | `tools/pre-execute` deny-once（reason 携带 spec 正文）；ticket 通过 `tools/post-execute` 的 `additionalContexts` 在下一请求送达；去重记录持久化到 `.trellis/.runtime/spec-inject/` |
| 子代理上下文 push | `SubagentStart` 注入 developer context + agent TOML 角色指令 | 子代理首个 `agent/pre-step` 注入角色契约（`.dsh/skills/trellis-agent-*/SKILL.md` 正文）与 curated task context；角色取自 dispatch prompt，prompt 不含角色时回退到 dispatch `description`（DSH 记录为子代理 descriptor label，以角色名开头、可带括号/冒号/破折号说明时才生效）；父会话指针作为 `Active task:` 缺失时的回退 |

实现细节与边界：

- 配置权威仍是目标项目的 `.trellis/config.yaml`：`spec_injection.enabled`
  显式为 `false` 时关闭，缺省按 Codex 默认启用；支持
  `max_spec_chars` / `max_total_chars` / `refresh_window_seconds` / `tools`。
  插件内部使用 DSH 原生小写工具名，默认 `[edit, write]`，与 Codex 的
  `Edit|Write` matcher 对齐；只读工具可显式加入（如 `tools: [Read]`），它永远不会被 deny。
  **跨平台共享配置请写 Trellis 原生大写名**（`Edit` / `Write` / `Read` /
  `MultiEdit`）：DSH 会把大写规范化为小写后匹配，Codex hook 则只认大写；
  反过来在共享文件里写 `tools: [write]` 会让 Codex 侧输出
  `unknown spec_injection.tools entries ['write']` 并静默停止注入。
- `read` 触发时正文只能经 post-execute 送达，因此**不会**像 Codex 那样先阻断
  读取；这是 DSH 事件形状决定的差异，不是配置问题。Codex 0.163 当前也没有可
  匹配的 `Read` 工具，读文件走 `Bash`/shell，因此这条不是 DSH 独有的退步。
- spec 去重记录持久化在目标项目的 `.trellis/.runtime/spec-inject/<session>.json`
  （该目录被 Trellis 的 `.gitignore` 忽略）。写入是 temp + rename 的原子替换；
  文件损坏、版本不匹配、目录只读或写入失败时，插件安全回退到“没有历史”，下一次
  触碰会重新完整注入。`compaction/end` 会同时删除内存记录和磁盘分片，保证压缩后
  重新教学；插件重启不再无条件重复 deny。
- bootstrap 的“每会话一次”是**有意设计**：新根会话第一次处于 `no_task` 时提醒一次
  “如果还没加载 Trellis 上下文，读一次 `trellis-start`”。如果这一轮没有开始
  Trellis，同一会话后续普通轮次不再重复提醒——这不是 `dsh-trellis` 的缺陷，而是
  避免每轮噪音；workflow 面包屑仍会随任务状态变化出现。需要重新提示时，可手动
  加载 `trellis-start`，或通过压缩/clear 让消息被移除后再次注入；新会话会重新注入。
  headless 用 `--session-id` 在新进程 resume 时，projection 状态不跨进程恢复，可能再注入
  一次；Web 同一进程内不会重复。Codex 在每个无任务轮次重复提醒，本插件不复制该频率。

- **stale 指针**：指针指向已不存在的任务目录时，面包屑使用专用正文说明“这是失效指针，
  不是缺少 workflow 状态块”，并提示检查 `.trellis/.runtime/sessions/` 或用
  `python3 .trellis/scripts/task.py finish` 清理；同时像 `no_task` 一样补一次 bootstrap。
  项目若定义了 `[workflow-state:stale]` 块，则优先使用项目文案。Codex 在该场景保留
  `stale_session` 标签并输出通用兜底行，且不附 bootstrap；DSH 的专用正文与 bootstrap
  是增强，不是 parity 对齐（0.1.5）。
- 子代理是委托会话，不是新的根会话：没有自己绑定的任务时，插件不再向子代理注入
  `no_task` 面包屑或 bootstrap；它的任务上下文只来自 push，避免与 `Active task:`
  矛盾。子代理自己绑定任务后仍会收到对应状态的面包屑，但不会收到 bootstrap。
- 不含 `trellis-agent-*` 角色的 generic 子代理保持静默：Codex 的
  `inject-subagent-context.py` 对非 Trellis 子代理类型是 silent return，本插件同样
  不替它编造工作流状态；child-side 技能仍是它的 pull 路径。角色识别同时接受 dispatch
  prompt 与 dispatch `description`（prompt 优先），因此“把角色名写在 `description`
  里”的派发不会被误判为 generic。`description` 必须以**角色名开头**（忽略大小写与
  包裹的引号；可以带 `(audit round 3)`、`: task`、`— round 3` 这类标注）才算角色：
  像 `研究 trellis-agent-implement 插件的 README`、`about trellis-agent-check plugin
  docs` 这种只是谈论角色名的“话题型”描述仍按 generic 处理，不会误触守卫或推送错角色契约。
- 子代理 push 先注入角色契约，再注入 curated task context：角色正文来自目标项目
  已安装的 `.dsh/skills/trellis-agent-<role>/SKILL.md`（去掉 YAML frontmatter），
  上限 16 KiB；推送副本会删除只属于 pull 路径的“自己加载上下文”段落，并明确告诉
  子代理“角色 skill 正文已随消息送达、不要再次加载、忽略其中‘自己加载上下文’的步骤”。
  磁盘上的 skill 保持原样，child-pull 仍然有效。只有 skill 缺失时才退回“加载一次
  skill 路径”的提示，不会同时声称上下文已准备。
- implement/check 继续复用 Trellis 自身的 `context_injection` 预算
  （`max_file_bytes` / `max_artifact_bytes` / `max_total_bytes`），读取
  `implement.jsonl` / `check.jsonl` 与 `prd.md` / `design.md` / `implement.md`。
  research 改为 Codex 同款的项目结构上下文：`.trellis/spec` 目录树 +
  `get_context.py --mode packages` + 搜索提示；可选的 `research.jsonl` 有真实条目时
  才内联，空清单不再产生“no curated entries”误导提示。角色技能缺失时至少注入
  路径提示，不静默省略。
- 项目根发现默认 `projectRootMarkers: [".trellis", ".git"]`：`.trellis` 优先，
  与 Codex 的 `find_trellis_root()` 一致，未 `git init` 的 Trellis 项目也能注入。
- 本地副本边界：本副本为个人使用的 Strategy A 就地维护版本，不发布 npm；旧版本
  会话升级后的重复 bootstrap 不在验收范围，验收以插件完成后的新会话为准；许可证
  说明见下文“License”。项目级策略和 vendored 自动同步脚本/补丁目录明确不需要；排他
  只做桌面通知警告。详见 [`../plugin-create.md`](../plugin-create.md) 的“范围排除”和
  [`docs/manual-verification.md`](docs/manual-verification.md)。

### 产品化增强（非 Codex parity）

- **`/trellis-doctor`**：纯 JS 诊断，不依赖项目 Python。输出项目根、插件/Trellis
  版本、workflow 块数量、活跃任务（含 `task_error`）、spec 注入配置与匹配数量、
  插件冲突检测状态。doctor 只报告本地状态，不发起网络检查（版本检查在设置页）。
- **派发守卫（默认开启）**：`trellis-agent-implement` / `trellis-agent-check` 派发
  时，父会话指针或 `Active task:` 前奏必须指向可读的 `task.json`，否则 deny；
  角色从 prompt 的**声明**（首行角色前缀 / `Role:` 行 / `You are the <role>
  sub-agent/role`）或 dispatch `description` 的严格角色前缀识别；只提到 role skill
  路径或普通叙述不触发守卫。把角色名写进 `description` 不会绕过守卫，话题型
  `description` 也不会被误拦。
  `research` 允许无任务派发，并在下一请求提示确认输出位置。这比 Codex 的
  “silent return + 子代理无上下文运行”更严格，属于 DSH 增强；它是**提示性闸门**，
  不是安全边界（见下文 inline 语义）。
- **插件冲突检测**：通过 loader 条目（`loader.locate(fiber)`、fiber 身份）识别同 profile 内**任何包名或
  loader id 含 `trellis` 的插件**（大小写不敏感，不限于 `dsh-trellis*`）；确认冲突时**不再只写日志**——Host 通过
  `/dsh-trellis/conflicts` 暴露结果，页面加载时尝试发**桌面通知**，同时在
  `shell.overlay` 显示一条可关闭的告警横幅。浏览器尚未授权时，横幅提供
  **启用桌面通知** 按钮（点击即用户手势，满足浏览器的权限提示要求）；权限被拒绝时
  横幅保留并提示到站点设置中重新允许。不自动禁用。
  loader 不可用或无法排除自身时报告 `unavailable` / `unverified`，不伪造“无冲突”。
- **Web 设置页**：配置入口改到 **设置 → Trellis**（`settings.section`），与插件详情页解耦；
  页面顶部是能力开关（启用插件、`/trellis` 命令、派发守卫、子代理上下文 push、spec 注入），
  其下是面包屑/命令行为，最后是版本监控。插件页不再渲染表单。
- **版本监控**：设置页内按来源分别监控——
  - **来源仓库**（`versionCheckPluginRepo`，可自定义）：按 `owner/repo` 监控其 commit，
    用于吸收改进；本插件有更新的 release 时同一行标出。
  - **Trellis 官方 npm 包**（`versionCheckTrellisPackage`，默认 `@mindfoldhq/trellis`）
    与 **DSH 官方 npm 包**（`versionCheckDshPackage`，默认 `@deepseek-ai/dsh`）：
    按 `dist-tags` 监控官方发布版本（等同 `npm view <pkg> dist-tags`），任一线道版本变化即算更新。
  - 关闭“版本监控”开关会隐藏间隔、通知、三个来源地址与整个检查面板；自动检查间隔为 0
    时只保留手动检查；手动检查用当前草稿值，自动检查用已保存配置。
  - 检查由 **Host 侧**执行并通过同源路由 `/dsh-trellis/version-check` 提供给设置页：
    GitHub 的 Atom feed（`commits.atom` / `releases.atom`）没有 CORS 头；Host 优先读
    Atom，失败后才回退到 GitHub REST（未认证配额 60 次/小时），避免每次检查消耗配额。
    Host 只访问由校验后的 `owner/repo` 拼出的地址，以及 npm registry 的 `dist-tags`，
    不接受任意 URL。
    新变化经 `Notification` 发桌面通知（未授权时只显示页内结果），手动检查另发一条本次汇总通知。

## 安装

### 本地源码替换已安装的 git 快照（本次使用的方式）

当前 `web` profile 使用的是 **ssh git 依赖快照**，不是软链：

```text
# 当前 profile package.json 结果
"dsh-trellis": "ssh://git@forgejo.xzc.com/xzc/ai-coding-toolkit.git#path:dsh-plugins/dsh-trellis"
```

因此直接编辑 `dsh-plugins/dsh-trellis` 的源码不会热更新已安装插件；需要重新执行
安装/更新并重启 DSH。下面的 `link:` 流程只用于本地开发，不是当前安装态。

安装步骤（DSH 内置插件管理器；已安装同名包时必须先移除）：

1. `plugin_manager(action: "remove_bundle", target: "dsh-trellis")`
2. `plugin_manager(action: "install_bundle", target: "<仓库绝对路径>/dsh-plugins/dsh-trellis")`

返回 `application: "applied"` 即已生效；Host 半会随 runtime 重挂载，新增的
`<trellis-bootstrap>` 独立消息在下一轮即可观察到。`link:` 依赖直接指向源码目录：
移动或删除该目录会使 profile 失效；只想固定快照时改用 `file:` 或 git 依赖。

推送到远程仓库后，可将同一 package 作为 git 依赖安装（预期形态，未在本轮验证）：

```powershell
dsh plugin --profile web remove dsh-trellis
dsh plugin --profile web add github:<owner>/<repo>
```

git 依赖不会执行 `prepack`（`pnpm pack`/`publish` 才会），因此 `lib/client.js` 必须保持已构建并
随仓库提交。源码仓库提供了一个跟踪的 pre-push 钩子：推送涉及本插件的提交前会自动执行
`pnpm run build:client`，如果重建后 bundle 仍未提交则中止推送并给出提交命令。启用方式：

```bash
./scripts/install-git-hooks.sh
```

钩子被安装到 `.git/hooks/pre-push`（Sonar 等 `core.hooksPath` 管理器会链式调用它），
不会替换现有的 hook 管理器；`git push --no-verify` 可显式绕过。

配套要求：项目的 Trellis 平台需包含 dsh（`trellis init --dsh`，见 Trellis-DeepSeekHarness 适配分支），且 `.trellis/scripts` 需包含读取原生 `DSH_SESSION_ID` 的适配（已含在同一分支）。当前源码的 Host peer 范围显式包含 `^0.2.0-rc.1` 和 `^0.2.1-alpha.2`，保留既有版本范围；开发基线固定为 `0.2.0-rc.1`；其它宿主版本用 `test:compat` 在临时副本中单独验证，不代表逐个重新验证所有历史版本。新版 DSH 的 peer 准入使用 `includePrerelease: true`，与 npm 默认匹配不同；通过准入不等于实际兼容，不应使用 `allow-version` 绕过缺失的 API。Web 配置只在具备对应 client surface 的 profile 中加载。

运行时需要 profile 提供 `sessionProjections` 服务；该依赖由插件的 `inject` 声明。自定义或精简 profile 若未组装此服务，需先加载 `@deepseek-ai/dsh-session-projection`，否则插件会等待依赖，不会退回直接扫描历史。

### 0.1.6：只读默认、严格角色识别、子目录 spec

- **模式不再写项目文件**：移除首次进入项目自动补 `dsh.dispatch_mode: inline` 的迁移；
  缺省即 inline，显式 `auto`/`sub-agent` 才派发，非法值回落 inline。插件不再修改
  被跟踪的 `.trellis/config.yaml`，也不再让 `trellis update` 反复把 config 标为
  “用户修改”。inline banner 明确覆盖 phase detail 中的派发指令，并说明 `.dsh` 仍会
  触发 `task.py start` 的 jsonl 闸门（保留 `--allow-empty-context` 提示）。
- **角色识别改为声明式**：只接受 dispatch prompt 首行角色前缀、独立 `Role:`/`Agent:`
  行、`You are the <role> sub-agent/role` 语句，以及 dispatch `description` 的严格
  角色前缀。只读 `.dsh/skills/trellis-agent-<role>/SKILL.md` 或普通叙述不再触发
  subagent push / dispatch guard，修复 generic 子代理被误判的问题。
- **子目录 spec 路径**：`edit`/`write` 的相对 `file_path` 按 agent 当前工作目录解析，
  同时尝试项目根相对路径并取并集；session cwd 为子目录时不再漏掉
  `src/**/*.js` 这类 spec 的 deny-once。
- 版本：`0.1.5` → `0.1.6`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.5：stale 指针诊断与 bootstrap 补齐

- **缺陷**：活动任务指针指向已删除/不存在的任务目录时，面包屑正文退化为
  `no matching [workflow-state] block found.`，把“指针失效”误报成“workflow 缺块”，
  且不再注入 bootstrap。Codex 同场景保留 `stale_session` 标签与通用兜底行，且不附
  bootstrap；DSH 的专用正文与 bootstrap 是增强，不是与 Codex 对齐。
- **修复**：`resolveTrellisState` 为 `stale` 提供专用正文（项目自定义
  `[workflow-state:stale]` 块仍然优先），明确这是失效指针并给出修复/清理路径；
  composer 对 `stale` 与 `no_task` 一样追加一次性 bootstrap。`stale` 状态本身保留，
  不静默改写成 `no_task`。
- **文档**：补充默认 dispatch mode（`inline`）与 Codex（`auto`）的差异说明。
- 版本：`0.1.4` → `0.1.5`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.4：skip 词改为按 turn 生效

- **缺陷**：`no-trellis`（或项目 `prompt_injection.skip_keyword`）原先只在触发它的那个
  step 生效。DSH 的 `agent/pre-step` 只把 inbox claim 到的新消息批次交给监听器，模型
  调用工具后的 step 2 批次里没有带关键词的用户 prompt，于是同一轮仍然注入面包屑与
  bootstrap；README 与 Codex 的按轮语义都要求跳过整轮。
- **修复**：composer 在命中关键词时记住该 `turn`（`WeakMap` 以 agent 为键，随会话
  回收），同一 turn 的后续 step 直接静默；下一个 turn 重新判定。跳过只影响消息
  渲染，插件始终只读项目配置。宿主若不提供 `turn`，退化为原来的按 step 判定，
  不会记忆无法归属的决定。
- **文档更正**：子代理 push 的任务来源优先级是 dispatch prompt 的 `Active task:` 优先、
  父会话指针兜底（原 README 写反了）；两者都没有时不 push，这一点现在明说。
- 版本：`0.1.3` → `0.1.4`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.3：角色 label 补强

- **角色 label**：`description` / descriptor label 不再要求与角色名完全相等。label
  以角色名开头、后面是结尾或独立标注（空白 + `:`/`：`、`(`/`（`、`[`/`【`、`-`、
  `–`、`—`）时即识别为角色，例如 `trellis-agent-implement (audit round 3)`。
- **话题型保持 generic**：`研究 trellis-agent-implement 插件的 README`、
  `about trellis-agent-check plugin docs`、以及角色名后接普通词语的
  `trellis-agent-check plugin docs` 都不选角色。
- 版本：`0.1.2` → `0.1.3`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.2：缺陷修复轮

- **角色识别**：派发守卫与子代理 push 除 dispatch prompt 外，还接受 dispatch
  `description`（DSH 记录为子代理 `subagent/descriptor` 的 label）；prompt 优先，
  description/label 兜底。首版要求 label 整体等于角色名；0.1.3 放宽为“角色名开头 +
  可选标注”（见下）。把角色名写进 `description` 不再让 push 静默失效、也不再绕过
  inline 守卫，而 `研究 trellis-agent-implement 插件的 README` 这类话题型描述仍按
  generic 处理。label 经 `sessionProjections` 折叠读取，不使用已弃用的同步事件读取。
- **push 文案**：明确“角色 skill 正文已随消息送达、不要再次加载、忽略其中‘自己加载
  上下文’的步骤”；只有 skill 缺失时才提示加载路径。同一条 push 中“上下文已准备”
  只出现一次（`## Task Context` 段不再重复）。
- **守卫表述**：拒绝信息与 README 将守卫明确为提示性闸门而非安全边界；退出 inline
  改为用户决定项，并要求模型不要自行修改 `.trellis/config.yaml`。
- **README**：只描述本插件，删除来源、版本历史与 npm 安装说明。

版本：`0.1.1` → `0.1.2`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.1：对等性修复轮

- **research 子代理上下文**：改为 Codex 同款 `.trellis/spec` 目录树 +
  `get_context.py --mode packages` + 搜索提示；`research.jsonl` 仅在存在真实条目时
  内联，空清单不再产生误导性提示。
- **角色契约**：推送副本删除 pull-only 的“自己加载上下文”段落，磁盘 skill 保持
  不变；research 的 Step 1 改为使用 dispatch 中的 `Active task:`。
- **workflow 降级**：Trellis 项目 workflow 缺失/不可读/零状态块时输出可见 generic
  面包屑与 bootstrap；普通 Git 仓库仍保持静默。
- **命令引用**：注入正文中的 `/trellis:finish-work` 等 Codex 形态归一为 DSH
  技能/命令名。
- **配置解析**：支持 `dsh: {dispatch_mode: inline}` 等 flow-style section；
  `spec_injection` / `prompt_injection` / `context_injection` 同步支持。
- **inline 启动**：`<dsh-mode>` 横幅补充 `task.py start --allow-empty-context`
  提示。
- **版本检查**：GitHub/npm 请求超时转为可读的局部结果；Atom feed 不可达时
  回退到 GitHub REST，commit/release feed 独立结算，UI 显示“部分结果”而不是
  原始 `This operation was aborted`。
- **稳定性**：只读项目的 `dsh.dispatch_mode` 写入失败按进程缓存；`trellis_wait`
  支持可选 `timeout_ms`，超时返回 fail-closed 的 `timeout/unknown`。

版本：`0.1.0` → `0.1.1`；client bundle 已用 `pnpm run build:client` 重建。

## 配置

支持 Settings 的 DSH Web profile，在新版打开“插件 → dsh-trellis”，旧版 RC 打开“设置 → 插件 → 插件配置 → Trellis 工作流”。`0.1.7-rc.1` 起（含 `0.2.0-rc.1`）保存到当前 profile 的 `cordis.patch.yml`，全局 patch 和命令行覆盖仍优先，无法生效的表单写入会被拒绝；旧宿主仍保存到 `settings.yaml`。

升级前备份 `settings.yaml` 和各 profile 配置。新版宿主会把旧文件改名为 `settings.yaml.imported`，并向**首次启动的 profile** 按 entry id 一次性导入；拒绝的 section 只保留在备份文件，不会自动重试。插件不会自行重命名、删除或跨 profile 复制配置；应先安装兼容插件，再启动迁移，并核对其他 profile 的需要。

项目级执行模式不是插件配置，而是 `.trellis/config.yaml` 的 `dsh.dispatch_mode`。
插件**只读**该键，不写项目文件；缺省（没有 `dsh` section 或没有该键）即 `inline`：

```yaml
dsh:
  dispatch_mode: inline   # 缺省值；inline = 主会话直接实现/检查
  # dispatch_mode: auto    # 显式开启角色子代理派发
  # 逃生口：inline 下若确实要显式委派 trellis-agent-implement / check
  # inline_allow_dispatch: true
```

Codex 对应的 `codex.dispatch_mode` 不会被 DSH 读取；两个平台各用各的模式。Trellis 脚本
（`task.py start` 的 jsonl 闸门、`get_context.py` 的 phase 文本）仍只认识
`codex.dispatch_mode`；插件不修改这些脚本，只通过面包屑/banner 提供 DSH 语义。

**与 Codex 默认值的差异**：Trellis 的 Codex 侧默认 `auto`（派发角色子代理），本插件的
DSH 默认是 `inline`（主会话直接实现/检查）。`auto` 在 DSH 上已实测可用；切换由用户显式
设置，插件不覆盖、也不写入显式值。

`inline` 的语义与边界（0.1.0 起）：

- **只读默认**：缺省即 inline；插件不追加键、不修改注释/换行，也不创建缺失的
  `.trellis/config.yaml`。显式 `auto` / `sub-agent` 才派发角色子代理。

- **模式横幅与状态块解耦**：只要 `dsh.dispatch_mode: inline`，每轮面包屑末尾都追加
  `<dsh-mode>` 横幅，覆盖全部状态（含 `no_task` / `completed` / `stale` / `task_error` /
  自定义状态），与 Codex 每轮输出 `<codex-mode>` 的行为对齐。`planning` / `in_progress`
  且 workflow 文件定义了 `*-inline` 块时额外选该块；**变体没有 `*-inline` 块时保留基础块，
  但横幅仍然输出**——否则裁剪过的 workflow 会把 auto 语义（curate jsonl、派发子代理）
  静默教给一个声明了 inline 的项目。
- **派发守卫会拦截 inline 下的默认派发（提示性闸门，不是安全边界）**：`inline` 下
  `trellis-agent-implement` / `trellis-agent-check` 的派发被拒绝
  （`trellis-agent-research` 仍放行）。拒绝信息说明退出 inline 是**用户决定**：只有
  用户明确要求派发时，才由用户把项目切到 `dispatch_mode: auto`，或由用户设置
  `inline_allow_dispatch: true`；模型不应自行修改 `.trellis/config.yaml` 绕过守卫。
  因为模型对项目配置有写权限，守卫只能阻止“顺手派发”，不能强制一个可写配置的项目。
  Codex 只文档化 inline、不拦截，这里的拦截是 DSH 增强。
- **非法值回落 `inline`（fail-safe）**：`dispatch_mode` 只接受 `auto` / `inline`
  （`sub-agent` 视为 `auto`）；其他值（包括拼写错误）回落 `inline`，避免一个笔误把
  项目静默变成“自动派发”。`/trellis-doctor` 会显示实际生效的模式。
- **inline 下启动任务**：Trellis 的 `task.py start` 把 `.dsh` 目录无条件视为
  sub-agent-capable（`_SUBAGENT_CONFIG_DIRS` 含 `.dsh`），因此即使
  `dsh.dispatch_mode: inline` 仍要求 `implement.jsonl` / `check.jsonl` 非空；inline
  工作流跳过 jsonl 策展，首次启动请用
  `task.py start <task> --allow-empty-context`（Trellis CLI 契约，非插件行为）。
- **phase detail 覆盖**：Trellis 0.7.0-beta.4 的 `get_context.py --platform dsh` 没有
  DSH-inline 变体，phase detail 仍会写 “Spawn the implement sub-agent…”；`<dsh-mode>`
  banner 明确覆盖这类派发指令，inline 下应以 banner 为准。
- **迁移提示**：从 `auto` 切到 `inline`（或反向）会改变面包屑正文的 digest，下一轮自动
  重新注入；同模式同状态不会重复注入。子代理不接收 `<dsh-mode>`。

Headless、rc.6 或需要声明部署默认值时，仍可在 profile 的 `cordis.patch.yml` 里覆盖（整行替换）；Web 卡片的“恢复配置文件值”会清除用户层字段并重新继承这里的值：

```yaml
- id: dsh-trellis
  config:
    maxBytes: 4096          # 面包屑注入的字节预算（0 = 关闭注入）
    skipKeyword: no-trellis # 无项目配置时的回退跳过词；项目 prompt_injection.skip_keyword 优先（空 = 禁用）
    pythonCmd: ""           # 空 = 自动选择：Windows 先 py -3 再 python；其他系统先 python3 再 python
    commandsEnabled: true
    specInjection: true     # 路径级 spec 注入；项目 .trellis/config.yaml 仍是逐项目权威
    subagentContext: true   # Trellis 角色子代理首步任务上下文 push
    dispatchGuard: true     # implement/check 派发无可读任务时 fail-closed
    versionCheck: true      # 设置页内的来源版本监控
    versionCheckIntervalMinutes: 1440  # 自动检查间隔；0 = 仅手动
    versionCheckNotify: true           # 新提交时发浏览器桌面通知
    versionCheckTrellisPackage: "@mindfoldhq/trellis"
    versionCheckDshPackage: "@deepseek-ai/dsh"
```

## 工作原理

- **状态解析**（`lib/workflow.js`）：向上找项目根 → 按 Trellis 的优先级选择 workflow 文件（任务 `task.json workflow` → `.trellis/.developer` 的 `workflow=` → `config.yaml default_workflow` → 全局 `.trellis/workflow.md`）→ 解析状态块 → 只读当前会话指针 `.trellis/.runtime/sessions/dsh_<id>.json`，不枚举其他会话。指针缺失时返回 `no_task`；指针指向的目录已不存在时返回 `stale`；目录存在但任务记录不可读时返回 `task_error` 并保留路径。任务状态按原值匹配对应块（`completed`、团队自定义状态不会被改写成 `no_task`）。`codex.dispatch_mode` 是 Codex-only 设置，DSH 不读取；DSH 使用自己的 `.trellis/config.yaml` `dsh.dispatch_mode`（缺省 `inline`，显式 `auto`/`sub-agent` 才派发；非法值回落 `inline`；插件不写该键）。`inline` 时每轮追加 `<dsh-mode>` 说明（主会话直接实现/检查、不派发 `trellis-agent-*`、无需 `trellis_wait`、用 `trellis-check` 技能验证），并在 `planning`/`in_progress` 且文件定义了对应 `*-inline` 块时选该块；块缺失只影响措辞，不影响模式声明。指针值按 Trellis 规则归一（`tasks/<slug>`、`./`、绝对路径），指向不存在或不是目录时降级为 `stale`。修复记录或重新绑定任务后会在下一轮重新解析。
- **注入去重**（`lib/breadcrumb-projection.js`）：投影仅保存面包屑的事件序号和 source/content 指纹，与 DSH 已维护的 `session.surface.nodes` 一起确定最后可见面包屑。恢复、分叉和重载均从 projection 重建；不缓存“本进程最后注入”的临时判断，也不扫描完整事件历史。
- **会话身份**：DSH 原生提供 `DSH_SESSION_ID = agent.session.header.id`，并先丢弃环境中已有的 `DSH_*` 再重建受管命名空间。Trellis beta 因此会在同时看到 `DSH_SHELL=1` 与 `DSH_SESSION_ID` 时优先解析当前 DSH 身份，即使没有插件也不会被外层 host 继承的 `TRELLIS_CONTEXT_ID` 串任务。插件通过 `shellEnv` 为每次执行额外生成 `DSH_TRELLIS_CONTEXT_ID = dsh_<session-id>`，用于转发可能不同于 shell 自身 session 的子代理身份；主会话与子代理仍各自保留 DSH 身份，子代理通过派发 prompt 首行的 `Active task:` 和角色 prelude 取得父任务上下文。
- **Headless 会话**：默认每次 `dsh --profile headless` 调用都会创建新 DSH session。需要跨轮保留 active-task 指针时，应保持同一会话，或在支持的宿主上用 `--session-id` 明确继续已有会话；不能把多个未指定身份的独立调用当成同一 session。
- **工作目录**：优先读取当前 agent 的可选 `workingDirectory` 服务，跟随宿主提交的目录切换/恢复；仅服务不存在时回退 session header。服务故障不会触发旧目录操作。切换目录不会替换会话身份，不会复制任务指针；新目录按同一身份查找自己的指针。
- **取消与生命周期**：命令和 `trellis_wait` 都继承 DSH invocation 的 `AbortSignal`；取消后命令不会继续尝试另一个 Python 启动器，等待工具也会立即注销临时事件监听器。结算事件不能单独证明父会话通知入队，因此 `settlementNoticeQueued` 保守返回 false（未验证）；仅从 catalog 看到 inactive 时保持 `unknown`，不猜任务通过。插件卸载或 Settings 重挂时，还会取消自己的活跃等待和待消费面包屑，不删除用户消息或任务记录。
- **子代理并发**：主会话先做独立工作，需要汇合时用 `trellis_wait` 等待直接 continuable 子代理的结算。无插件时根据实际工具 schema 选择旧宿主前台参数，或 alpha.2 的父会话 yield/原生通知路径；不存在可靠事件路径时主会话直接做工作。SDK 的 `session/wait` 不是可以假定存在的模型工具。所有路径都必须检查结果后才能推进依赖步骤。

## 开发

```powershell
pnpm install
pnpm run build:client
pnpm test    # node --test "test/*.test.js"
```

测试用本地脚本化模型响应运行真实 AgentLoop、Loader、ToolRuntime、Session 与
`sessionProjections`，覆盖面包屑去重/恢复/分叉/压缩、路径级 spec 注入、命令与
`trellis_wait` 生命周期、子代理上下文 push（含 description-only 角色识别）与派发守卫、
客户端 bundle 和设置页逻辑；不调用外部模型。`test:compat` 可在临时副本中安装其它
宿主版本后运行同一套测试，不改变当前 checkout 的依赖。

Host half 是直接由 `main` 加载的 ESM JavaScript；Web half 通过 tsdown 生成 DSH lazy-CJS factory 到 `lib/client.js`。`pnpm pack` 会在 prepack 阶段自动重建客户端 bundle。

## License

MIT（`package.json`）。本个人使用的 Strategy A 副本不包含 LICENSE 文件，这不是缺陷；
范围见 [`../plugin-create.md`](../plugin-create.md) 的“范围排除”，手工验收见
[`docs/manual-verification.md`](docs/manual-verification.md)。
