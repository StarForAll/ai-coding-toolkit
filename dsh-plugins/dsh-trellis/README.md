# dsh-trellis

DeepSeek Harness (dsh) host 插件：把 [Trellis](https://github.com/mindfold-ai/Trellis) 工作流带进 dsh，并尽量沿用 DSH 原生能力补齐 Codex / Claude Code 级体验：

1. **每轮 workflow-state 面包屑注入** — 在每个 `agent/pre-step`，解析项目 `.trellis/workflow.md`（或任务/个人/团队选定的 workflow 变体）的 `[workflow-state:*]` 块 + 活跃任务状态（no_task / stale / task_error / planning / in_progress / completed / 团队自定义状态），把对应面包屑注入会话（与 `dsh-agent-instructions` 的注入管道相同）。未变化不重复注入；被压缩后自动重注入；提示词里出现独立单词 `no-trellis`（或项目 `prompt_injection.skip_keyword` 配置的词）可跳过当轮。
2. **隔离的原生会话上下文身份** — 从当前 agent 的 DSH 原生 session header 生成受管的 `DSH_TRELLIS_CONTEXT_ID`，让 `task.py start/create/current` 解析到会话级 active-task 指针，并在子代理身份不同于 shell 自身 session 时优先使用被转发的身份；插件命令启动的子进程也显式使用同一个 DSH 身份。
3. **原生子代理同步** — 安装插件后，Trellis 角色可用 DSH continuable 后台子代理；主会话先继续独立工作，耗尽后可调用事件驱动的 `trellis_wait`。它监听 DSH 的 `subagent/end`，利用 lifecycle 自带的 run/provider/output-block 元数据返回 `completed / failed / aborted / unknown` 的 fail-closed 结论。`error`、`max-tokens`、`refusal` 和未来未知失败原因都不会被误报成通过。rc.8 在父会话 idle 时也会用原生 settlement notice 唤醒，因此已经结束当前轮时无需额外调用 wait。
4. **子代理首步上下文 push** — 在子代理第一个 `agent/pre-step` 注入角色契约（目标项目 `.dsh/skills/trellis-agent-<role>/SKILL.md` 正文，去掉 frontmatter）与 curated task context。父会话指针缺失时回退到 dispatch prompt 的 `Active task:`；角色 skill 缺失时至少注入路径提示，不静默省略。
5. **`/trellis` 命令** — `/trellis-status`（活跃任务 + git 状态）、`/trellis-finish`（只读检查 + 安全收尾清单，不提前清 active-task 指针）。任务读取优先使用 `task.py current --json`；旧版 Trellis（0.6.10 之前没有该参数）自动回退到 `current --source` 的文档化输出。命令输出不进模型历史；真正的会话收尾走技能面 `/trellis-finish-work`，由技能先归档再写 journal。rc.8 下两条零输入命令使用 `recordInput: false`，并显式拒绝参数和图片附件，避免静默忽略输入。
6. **项目级模式引导** — 插件启用后，在首次解析某个 Trellis 项目的状态之前，自动确保
   `.trellis/config.yaml` 含 `dsh.dispatch_mode: inline`（缺省即内联）。只补缺失键，
   绝不覆盖显式 `auto`；保留注释、顺序与换行；文件缺失不凭空创建；写入是临时文件 +
   rename 的原子替换并带目录锁；拿到锁后会重读当前文件再合并，失败时回落到库默认
   `auto` 并只警告一次。
7. **Web 配置菜单** — DSH `0.1.7-rc.1` 的“插件 → dsh-trellis”详情页直接显示全部六个配置项；保留 `0.1.6-alpha.2` 详情页与旧版 RC 卡片。新版支持带修订号的原子保存、恢复 profile 继承值和冲突时保留草稿。配置里的 `enabled=false` 会停用工作流功能但保留表单；插件管理器的整包或组件开关则会连同表单一起卸载。

非 Trellis 项目不注入面包屑；命令只有被用户显式调用时才会检查并返回“未初始化 Trellis”。

这是 Trellis DSH 适配的**可选伴侣插件**，不是使用 `trellis init --dsh` 的前置条件。存在 `trellis_wait` 时可使用 continuable 后台派发和事件汇合。未安装插件时，只有工具 schema 明确支持 `run_in_background` 的旧宿主才设置 `run_in_background: false`；DSH `0.2.1-alpha.2` 已移除该参数，统一立即返回 child ID，应让父会话结束当前轮、由原生完成通知唤醒，或直接在主会话完成工作。收到 child ID 不代表依赖步骤通过；没有可用的事件汇合或可靠原生通知路径时不要派发。所有路径都禁止 sleep 或轮询，Trellis CLI 不会自动安装任何 DSH profile 插件。

## 本地分支：对齐 Codex 的三项 Trellis 接线

本副本基于上游 0.1.12；版本号已于 2026-10-21 重置，当前本地版本为 **0.1.1**
（重置前的 0.1.12–0.3.10 只保留在 `LOCAL_CHANGES.md` 与历史验证记录中）。
后续普通修改按 `0.1.0 → 0.1.1 → 0.1.2` 递增；只有运行时/配置契约破坏或大改才提升次版本/主版本。
三项主链路已经对齐，但 DSH 的事件形状仍带来下面的差异，因此本插件不宣称与 Codex
完全一致。**注意**：下文“Web 配置菜单”等上游章节描述的是上游版本；本副本的
配置入口已迁移到 **设置 → Trellis**，插件详情页不再显示表单。

| 能力 | Codex 的实际接线 | 本插件（DSH） |
| --- | --- | --- |
| 无任务 bootstrap | `UserPromptSubmit` 每轮附 `<trellis-bootstrap>` | 独立消息家族（`source.kind=dsh-trellis`、`source.form=bootstrap`）与独立 projection：新根会话每会话一次，与面包屑状态变化解耦，只有压缩移除后才重新提示；子代理永不注入。**首轮没有开始 Trellis 时，本会话后续不再重复催促是设计选择，不是缺陷**（见下文） |
| 路径级 spec 注入 | `PreToolUse` 匹配 Edit/Write；FULL 时 deny-once | `tools/pre-execute` deny-once（reason 携带 spec 正文）；ticket 通过 `tools/post-execute` 的 `additionalContexts` 在下一请求送达；去重记录持久化到 `.trellis/.runtime/spec-inject/` |
| 子代理上下文 push | `SubagentStart` 注入 developer context + agent TOML 角色指令 | 子代理首个 `agent/pre-step` 注入角色契约（`.dsh/skills/trellis-agent-*/SKILL.md` 正文）与 curated task context；父会话指针作为 `Active task:` 缺失时的回退 |

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
- 子代理是委托会话，不是新的根会话：没有自己绑定的任务时，插件不再向子代理注入
  `no_task` 面包屑或 bootstrap；它的任务上下文只来自 push，避免与 `Active task:`
  矛盾。子代理自己绑定任务后仍会收到对应状态的面包屑，但不会收到 bootstrap。
- 不含 `trellis-agent-*` 角色的 generic 子代理保持静默：Codex 的
  `inject-subagent-context.py` 对非 Trellis 子代理类型是 silent return，本插件同样
  不替它编造工作流状态；child-side 技能仍是它的 pull 路径。
- 子代理 push 先注入角色契约，再注入 curated task context：角色正文来自目标项目
  已安装的 `.dsh/skills/trellis-agent-<role>/SKILL.md`（去掉 YAML frontmatter），
  上限 16 KiB；推送副本会删除只属于 pull 路径的“自己加载上下文”段落，避免与
  “上下文已准备”矛盾。磁盘上的 skill 保持原样，child-pull 仍然有效。
- implement/check 继续复用 Trellis 自身的 `context_injection` 预算
  （`max_file_bytes` / `max_artifact_bytes` / `max_total_bytes`），读取
  `implement.jsonl` / `check.jsonl` 与 `prd.md` / `design.md` / `implement.md`。
  research 改为 Codex 同款的项目结构上下文：`.trellis/spec` 目录树 +
  `get_context.py --mode packages` + 搜索提示；可选的 `research.jsonl` 有真实条目时
  才内联，空清单不再产生“no curated entries”误导提示。角色技能缺失时至少注入
  路径提示，不静默省略。
- 项目根发现默认 `projectRootMarkers: [".trellis", ".git"]`：`.trellis` 优先，
  与 Codex 的 `find_trellis_root()` 一致，未 `git init` 的 Trellis 项目也能注入。
- 本地副本边界：本副本为个人使用的 Strategy A 就地维护版本，不发布 npm；旧 0.2.0
  会话升级后的重复 bootstrap 不在验收范围，验收以插件完成后的新会话为准；许可证
  说明见下文“License”。项目级策略和 vendored 自动同步脚本/补丁目录明确不需要；排他
  只做桌面通知警告。详见 [`../plugin-create.md`](../plugin-create.md) 的“范围排除”和
  [`docs/manual-verification.md`](docs/manual-verification.md)。

### 产品化增强（非 Codex parity）

- **`/trellis-doctor`**：纯 JS 诊断，不依赖项目 Python。输出项目根、插件/Trellis
  版本、workflow 块数量、活跃任务（含 `task_error`）、spec 注入配置与匹配数量、
  插件冲突检测状态。doctor 只报告本地状态，不发起网络检查（上游检查在设置页）。
- **派发守卫（默认开启）**：`trellis-agent-implement` / `trellis-agent-check` 派发
  时，父会话指针或 `Active task:` 前奏必须指向可读的 `task.json`，否则 deny；
  `research` 允许无任务派发，并在下一请求提示确认输出位置。这比 Codex 的
  “silent return + 子代理无上下文运行”更严格，属于 DSH 安全增强。
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
- **上游版本监控**：设置页内按来源分别监控——
  - **插件上游 fork 仓库**（`versionCheckPluginRepo`，可自定义）：监控 commit，
    用于吸收其优点到本插件；本插件有更新的 release 时同一行标出。
  - **Trellis 官方 npm 包**（`versionCheckTrellisPackage`，默认 `@mindfoldhq/trellis`）
    与 **DSH 官方 npm 包**（`versionCheckDshPackage`，默认 `@deepseek-ai/dsh`）：
    按 `dist-tags` 监控官方发布版本（等同 `npm view <pkg> dist-tags`），任一线道版本变化即算更新。
  - 关闭“版本监控”开关会隐藏间隔、通知、三个来源地址与整个检查面板；自动检查间隔为 0
    时只保留手动检查；手动检查用当前草稿值，自动检查用已保存配置。
  - 检查由 **Host 侧**执行并通过同源路由 `/dsh-trellis/version-check` 提供给设置页：
    GitHub 的 Atom feed（`commits.atom` / `releases.atom`）没有 CORS 头，而 REST API
    未认证配额（60 次/小时）正是浏览器端 403 的来源；Host 只访问由校验后的
    `owner/repo` 拼出的 Atom 地址，以及 npm registry 的 `dist-tags`，不接受任意 URL。
    新变化经 `Notification` 发桌面通知（未授权时只显示页内结果），手动检查另发一条本次汇总通知。

## 安装

### 本地源码替换已安装的 npm 版（本次使用的方式）

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

### 从 npm 安装（上游 0.1.12，不适用于本副本）

```powershell
# 装进实际使用的 profile（均在该 profile 下次启动时生效）
dsh plugin --profile web add dsh-trellis
dsh plugin --profile headless add dsh-trellis

# 如果你维护独立的 tui profile，也需要装进该 profile
dsh plugin --profile tui add dsh-trellis
```

`dsh plugin` 会把插件安装到指定 profile；每个实际使用的 profile 都需要单独安装。

DSH `0.2.0-rc.2` 的 macOS / Windows 桌面端可在菜单栏“Manage dsh command”中安装或管理内置 `dsh` 命令，无需单独安装 Node 或 pnpm。先用 `dsh --version` 确认 PATH 中实际调用的版本；旧的全局 CLI 可能与桌面端不同。桌面端默认使用 `desktop` profile，其他 profile 仍需分别安装。

新版本刚发布时，插件页预览的版本可能与安装器最终选择的版本不同。需要上游发布版 `0.1.12` 时，在插件页输入 `dsh-trellis@0.1.12`，或显式安装到实际使用的 profile：

```powershell
dsh plugin --profile desktop add dsh-trellis@0.1.12
# Web / headless 用户将 desktop 替换为对应 profile 名称。
```

DSH RC.2 内置 pnpm 11；其默认新版本等待期为 24 小时，裸包名可能暂时解析到较旧版本。显式版本安装会走安装器的相应确认流程，版本准入仍须通过；不需要关闭全局等待期或绕过兼容性检查。参见 [DSH RC.2 更新说明](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.2.0-rc.2) 与 [pnpm 11 发布说明](https://pnpm.io/blog/releases/11.0)。

日常升级命令：

```powershell
dsh plugin --profile web update dsh-trellis
dsh plugin --profile headless update dsh-trellis
```

对 `tui` profile 使用同样的 update。替换已加载的包版本后，需重启对应 DSH 进程；不要把新版插件管理器的实时开关误当作代码版本热更新。

DSH `0.1.6-alpha.2` 也可从 Web 侧栏“插件 → 添加插件”安装包。Web 安装后需要手动启用；CLI `add` 默认启用。安装命令仍是 `dsh plugin --profile <name> add <package>`，无需增加额外安装脚本。

如果要从源码开发或验证尚未发布的版本，可以改用本地 `file:` 安装：

```powershell
git clone https://github.com/SajoLuo/dsh-trellis.git
cd dsh-trellis
pnpm install --frozen-lockfile
pnpm run build:client
dsh plugin --profile headless add file:C:/path/to/dsh-trellis
```

`file:` 插件会作为 profile 内的 pnpm 快照安装；拉取源码更新后，尤其是版本新增文件时，需要先 remove 再 add 刷新该 profile。

配套要求：项目的 Trellis 平台需包含 dsh（`trellis init --dsh`，见 Trellis-DeepSeekHarness 适配分支），且 `.trellis/scripts` 需包含读取原生 `DSH_SESSION_ID` 的适配（已含在同一分支）。当前源码的 Host peer 范围显式包含 `^0.2.0-rc.1` 和 `^0.2.1-alpha.2`，保留既有版本范围；开发基线固定为 `0.2.0-rc.1`，隔离回归覆盖开发章节列出的七个宿主，不代表逐个重新验证所有历史版本。新版 DSH 的 peer 准入使用 `includePrerelease: true`，与 npm 默认匹配不同；通过准入不等于实际兼容，不应使用 `allow-version` 绕过缺失的 API。Web 配置只在具备对应 client surface 的 profile 中加载。

运行时需要 profile 提供 `sessionProjections` 服务；该依赖由插件的 `inject` 声明。自定义或精简 profile 若未组装此服务，需先加载 `@deepseek-ai/dsh-session-projection`，否则插件会等待依赖，不会退回直接扫描历史。

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
- **版本检查**：GitHub/npm 请求超时转为可读的局部结果；commit/release feed 独立
  结算，UI 显示“部分结果”而不是原始 `This operation was aborted`。
- **稳定性**：只读项目的 `dsh.dispatch_mode` 写入失败按进程缓存；`trellis_wait`
  支持可选 `timeout_ms`，超时返回 fail-closed 的 `timeout/unknown`。

版本：`0.1.0` → `0.1.1`；client bundle 已用 `pnpm run build:client` 重建。

### 0.1.11：DSH 0.2.0-rc.2 兼容验证

- 增加 `0.2.0-rc.2` 隔离回归与 Windows/Linux CI 目标；本地 RC.1 / RC.2 均为 130 项通过、无失败或跳过，RC.2 独立 Web profile 验收通过。
- 现有 `^0.2.0-rc.1` 已覆盖 RC.2，无需扩展 peer 或新增运行时补丁。开发基线仍为锁定的 RC.1。
- 补充桌面内置 CLI、profile 区别及显式版本安装说明。本版不包含 Trellis CLI 的归档与嵌套身份补丁，它们在独立适配分支中维护。范围与限制见[RC.2 验证记录](docs/validation-dsh-0.2.0-rc.2.md)；远端 CI 和发布状态以对应标签为准。

### 0.1.12：DSH 0.2.1-alpha.2 适配

- 面包屑和两条命令按每次调用读取 agent 作用域的 `workingDirectory.ensure()`，支持切换项目/worktree及目录恢复；仅旧宿主没有服务时才使用原始 `header.cwd`。目录验证失败不偷偷回退旧项目，原生 session ID 不随目录改变。
- `trellis_wait` 只证明匹配的执行结算；完成通知投递另由宿主负责。兼容字段 `settlementNoticeQueued=false` 表示未证明入队，**不表示确认未投递**。通过依赖门禁前仍需检查子代理报告或 transcript；inactive 快照保持 unknown。
- 为 DSH、Cordis 和 Schemastery 显式声明已验证 alpha peer 范围，保留 RC 开发基线及旧宿主范围；移除无直接用途的 `dsh-invariants` 开发依赖。新增 alpha.2 精确工具链隔离回归与 CI 目标，不升级本机 DSH。
- alpha 用户可显式安装 `dsh-trellis@0.1.12`。Trellis 模板在独立适配工作区同步，不包含在 npm 插件包中，也不是官方 Trellis npm 升级；现有项目的 workflow 不会被插件自动改写。测试结果及边界见 [alpha.2 验证记录](docs/validation-dsh-0.2.1-alpha.2.md)，远端 CI 与发布状态以对应标签为准。

### 0.1.10：DSH 0.2.0-rc.1 适配

- 七项 DSH peer 和 `engines.dsh` 新增 `^0.2.0-rc.1`；旧的 `^0.1.7-rc.1` 不接纳 0.2。开发依赖及锁文件升级到 0.2，Windows/Linux CI 配置继续覆盖四条旧宿主线。使用 0.2 宿主时请安装插件 0.1.10 或更新版本，0.1.9 不包含这项适配。
- 跟随宿主的失败工具历史恢复，新增真实 AgentLoop 回归：工具尚未启动时记录 `TOOL_NOT_STARTED`，已执行但结果未提交时记录 `TOOL_OUTCOME_UNKNOWN`；保留原始错误和已提交结果，继续会话不自动重试等待，也不重复注入面包屑。
- 已用隔离 DSH Web 验证正常版本准入、配置保存与读回、恢复继承值、整包/组件开关、冲突保留草稿以及页面重载。无需改变运行时代码、插件清单形态、安装命令或 Trellis 模板。完整范围见[验证记录](https://github.com/SajoLuo/dsh-trellis/blob/v0.1.10/docs/validation-dsh-0.2.0-rc.1.md)。

### 0.1.9：DSH 0.1.7-rc.2 兼容验证

- 新增 RC.2 隔离回归及 Windows/Linux CI 覆盖，修复兼容测试把非 RC.1 宿主错误归为旧版 Cordis 依赖的逻辑。
- 使用真实 AgentLoop、Loader 和 Session 验证动态工具增删、Settings 重挂、面包屑去重、恢复/分叉及压缩后的重新注入；补充等待目录失败与卸载清理回归。
- 本版不改变插件运行时代码、peer 范围、安装命令或 Trellis 生成模板；保留 RC.1 开发基线及两条旧宿主回归。验证范围与限制见[详细记录](https://github.com/SajoLuo/dsh-trellis/blob/v0.1.9/docs/validation-dsh-0.1.7-rc.2.md)。

### 0.1.8：DSH 0.1.7-rc.1 适配

- 按[新版 Settings 契约](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-rc.1/packages/settings/settings/README.md)声明六个 `.volatile()` 配置字段，读取 live Config，并由 Loader 的 `loader/volatile-update` 通知更新工作流注册。Settings 仅持有当前插件 fiber 的自定义页面策略；迟到、替换或卸载该服务不会重置配置。旧宿主保留原 helper/provider 路径。
- Web 改用 `configForms.get(entryId)`，保留旧 `settingsScope` 兼容分支。新版一次提交全部字段与编辑开始时的 revision，冲突或断连保留草稿；冲突后先放弃更改、读入新值，再重新编辑。旧宿主继续使用逐字段写入。
- 适配父会话 `subagentCatalog`：目录只证明直接归属和 continuable 模式，当前驻留状态另读 Session store，并校验创建时间和父会话，防止复用 id 串会话。查询期间捕获的 `subagent/end` 优先于 inactive 快照；冷子代理仍返回 unknown，不猜成功。旧目录格式继续支持。
- 保留单文件 `dsh.bundle.patch`、`manifestVersion: 1` 和 profile 安装命令；无需增加安装脚本。不改变 Trellis 生成模板及已有任务绑定。
- 本轮按本地工作区验证；不宣称支持新版 DSH 的 SSH 远程工作区文件访问。

### 0.1.7：DSH 0.1.6-alpha.2 适配

- 跟随[官方插件页 slot 契约](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.6-alpha.2/packages/client/ui-plugin-manager/README.md)，第三方包配置注册到 `plugins.bundle.config`，以 `dsh-trellis` 包名为 key；详情页直接渲染表单，不重复包装标题和折叠卡片。保留旧 `settings.plugin.item` keyed/list 两种形态，按实际存在的 slot 延迟注册并随 owner 卸载。
- 依照[官方插件管理器规范](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.6-alpha.2/packages/boot/plugin-manager/README.md)，保留 `dsh.bundle.patch` 安装入口，增加 `dsh.manifestVersion: 1` 与 `engines.dsh` 兼容性声明。`engines.dsh` 在该宿主版本中是声明信息，不是运行时兼容性检查器。
- 升级开发依赖和锁文件；测试依赖使用新名 `dsh-ptc-runtime`，RC 回归隔离副本继续使用 `dsh-code-runtime`。`dsh.client.inject` 保留旧宿主需要的依赖信息；新宿主实际运行时模块请求仍由编译产物决定，不额外安装一份 Web 壳。
- 加固实时卸载：取消所有正在等待的 `trellis_wait`、注销结算监听器、拒绝旧工具引用继续执行；清除尚未消费的 Trellis 面包屑，但保留用户输入。异步 pre-step continuation 在卸载后不再注入。Settings 保存遇到断连或拒绝时显示失败、保留草稿并允许重试。
- 本轮不改变 Trellis 的任务绑定、Python 脚本或生成模板；继续保留 0.1.6 的精确会话指针和 `task_error` 行为。

### 既有 DSH 0.1.5-rc.2 对齐

- 已迁移：面包屑使用 `sessionProjections` 的纯 fold，在恢复或分叉时重建状态、按已提交事件增量更新，不再调用 Session 的 `eventAt()` / `snapshotEvents()` / `ownEvents()` 或访问旧事件集合。当前 DSH 注册 Host-only projection；旧版 registry 通过 projection snapshot 兼容，仅包含序号和 payload 哈希，不传输工作流正文。
- 已修复：恢复会话、插件或 Settings 重载后的首轮也会去重；以最后一条仍可见的面包屑判断，避免 A → B → A 状态切换被旧记录误抑制。压缩移除后会重新注入，字节预算变化导致的正文变化也会重新注入。
- 前瞻适配：[上游同步历史读取弃用决策](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/architecture/2026-09-09-deprecate-synchronous-session-event-reads.md) 已进入主线，但 RC.2 仍提供这些方法；本次提前解除依赖，不代表 RC.2 已删除接口。插件不负责迁移磁盘会话格式。
- 已核对：插件不依赖 0.1.5 移除的 `ctx.agent` 或可构造 `Inbox`；pre-step 从事件载荷取得 agent，工具从 `exec.agent` 取得调用方，待处理消息只使用 `agent.inbox` 当前公开的 `nextStep`、`prepend`、`replace` 与 `remove`。
- 已采用：command lifecycle 的 `recordInput`、command attachment envelope 的 fail-closed 输入检查、`subagent/end` 的 run/provider/final-output 元数据，以及 report-before-settlement 与 idle-parent 原生唤醒语义。
- 已接入：Host `dsh-trellis` settings namespace 与 `dsh.client` 浏览器卡片。保存值写入 DSH 的 `settings.yaml` 用户层，并实时重挂插件 runtime；settings provider 单独重载时退回 loader 配置，插件自身卸载时则不会错误重挂 runtime。没有 settings 服务的 profile 继续使用原有 loader 配置。当前可选 Settings 生命周期由 `settings.installSection()` 承担；插件仍在运行时兼容旧版 helper。
- 已对齐：`dsh.client.inject` 指向的三个 DSH client 包与 React 都只作为浏览器构建输入保留在 `devDependencies`，发布安装不会重复解析 Web 壳已经提供的模块。
- 保持可选：`trellis_wait` 仍是“父会话还在当前轮里、需要明确同步点”时的工具；已经 yield 的父会话直接由 DSH 原生 settlement notice 唤醒。
- 保持直接归属：`trellis_wait` 继续使用 `listChildren(parent.id)` 验证 direct continuable child；这与 0.1.5 修正后的可继续子代理归属一致，不会把子代理误当作根会话参与调度。

## 配置

支持 Settings 的 DSH Web profile，在新版打开“插件 → dsh-trellis”，旧版 RC 打开“设置 → 插件 → 插件配置 → Trellis 工作流”。`0.1.7-rc.1` 起（含 `0.2.0-rc.1`）保存到当前 profile 的 `cordis.patch.yml`，全局 patch 和命令行覆盖仍优先，无法生效的表单写入会被拒绝；旧宿主仍保存到 `settings.yaml`。

升级前备份 `settings.yaml` 和各 profile 配置。新版宿主会把旧文件改名为 `settings.yaml.imported`，并向**首次启动的 profile** 按 entry id 一次性导入；拒绝的 section 只保留在备份文件，不会自动重试。插件不会自行重命名、删除或跨 profile 复制配置；应先安装兼容插件，再启动迁移，并核对其他 profile 的需要。

项目级执行模式不是插件配置，而是 `.trellis/config.yaml` 的 `dsh.dispatch_mode`。
插件启用后会在首次进入项目时自动补上 `dispatch_mode: inline`（只补缺失键，显式值不动，
注释与换行保持不变；详见下文）：

```yaml
dsh:
  dispatch_mode: inline   # inline = 主会话直接实现/检查（插件引导的默认）；auto = 派发角色子代理
  # 逃生口：inline 下若确实要显式委派 trellis-agent-implement / check，显式打开
  # inline_allow_dispatch: true
```

Codex 对应的 `codex.dispatch_mode` 不会被 DSH 读取；两个平台各用各的模式。

`inline` 的语义与边界（0.1.0 起）：

- **自动引导**：插件在首次解析项目状态前确保键存在，因此第一轮就已按 inline 注入；
  已有 `dispatch_mode: auto`、`dsh: {…}` 等显式写法不会被改写。只读项目或写入失败时
  本次回落到 `auto` 并记录一次警告。

- **模式横幅与状态块解耦**：只要 `dsh.dispatch_mode: inline`，每轮面包屑末尾都追加
  `<dsh-mode>` 横幅，覆盖全部状态（含 `no_task` / `completed` / `stale` / `task_error` /
  自定义状态），与 Codex 每轮输出 `<codex-mode>` 的行为对齐。`planning` / `in_progress`
  且 workflow 文件定义了 `*-inline` 块时额外选该块；**变体没有 `*-inline` 块时保留基础块，
  但横幅仍然输出**——否则裁剪过的 workflow 会把 auto 语义（curate jsonl、派发子代理）
  静默教给一个声明了 inline 的项目。
- **派发守卫会执行 inline 契约**：`inline` 下 `trellis-agent-implement` /
  `trellis-agent-check` 的派发被 fail-closed 拒绝（`trellis-agent-research` 仍放行）；
  错误信息给出两条出路：切 `dispatch_mode: auto`，或为本项目设置
  `inline_allow_dispatch: true`。Codex 只文档化 inline、不拦截，这是有意的 DSH 增强。
- **非法值回落 `auto`**：`dispatch_mode` 只接受 `auto` / `inline`（`sub-agent` 视为
  `auto`）；其他值（包括拼写错误）回落 `auto` 而不是 Codex 的 `inline`，避免一个笔误
  把项目静默变成“禁止派发”。`/trellis-doctor` 会显示实际生效的模式。
- **inline 下启动任务**：Trellis 的 `task.py start` 仍要求 `implement.jsonl` /
  `check.jsonl` 非空，而 inline 工作流明确跳过 jsonl 策展；首次启动请用
  `task.py start <task> --allow-empty-context`（Trellis CLI 契约，非插件行为）。
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
    versionCheck: true      # 设置页内的上游版本监控
    versionCheckIntervalMinutes: 1440  # 自动检查间隔；0 = 仅手动
    versionCheckNotify: true           # 新提交时发浏览器桌面通知
    versionCheckPluginRepo: "https://github.com/SajoLuo/dsh-trellis"
    versionCheckTrellisPackage: "@mindfoldhq/trellis"
    versionCheckDshPackage: "@deepseek-ai/dsh"
```

### 0.1.6：Trellis 会话隔离与任务错误兼容

- 跟随 [Trellis #608](https://github.com/mindfold-ai/Trellis/pull/608)：只读取当前 DSH 会话的精确指针。缺少身份或匹配指针时返回 `no_task`，不再借用唯一的其他会话；也不从派发提示词反向建立会话绑定。子代理继续通过明确的 `Active task:` 派发上下文读取任务。
- 对齐 [官方 `task_error` 工作流](https://github.com/mindfold-ai/marketplace/commit/62a77c9b57fb8bb081c110394bce08b6ebc6e09a)：已绑定任务的 `task.json` 缺失、不可读、JSON 损坏或状态为空时，保留任务路径，提示先修复记录，不把它当成“没有任务”。不修改或删除任何任务与指针。
- 旧项目没有 `[workflow-state:task_error]` 块时，插件提供保守的修复提示；恢复有效记录后，下一轮自动恢复正常状态。因此无需先更新 Trellis CLI 才能使用本插件的修复。
- 插件修复不替代 Trellis Python 脚本升级：旧版 `task.py current/finish` 的回退策略、归档恢复和上下文清单检查仍由项目中的 `.trellis/scripts` 实现。

## 工作原理

- **状态解析**（`lib/workflow.js`）：向上找项目根 → 按 Trellis 的优先级选择 workflow 文件（任务 `task.json workflow` → `.trellis/.developer` 的 `workflow=` → `config.yaml default_workflow` → 全局 `.trellis/workflow.md`）→ 解析状态块 → 只读当前会话指针 `.trellis/.runtime/sessions/dsh_<id>.json`，不枚举其他会话。指针缺失时返回 `no_task`；指针指向的目录已不存在时返回 `stale`；目录存在但任务记录不可读时返回 `task_error` 并保留路径。任务状态按原值匹配对应块（`completed`、团队自定义状态不会被改写成 `no_task`）。`codex.dispatch_mode` 是 Codex-only 设置，DSH 不读取；DSH 使用自己的 `.trellis/config.yaml` `dsh.dispatch_mode`（默认 `auto`）。`inline` 时每轮追加 `<dsh-mode>` 说明（主会话直接实现/检查、不派发 `trellis-agent-*`、无需 `trellis_wait`、用 `trellis-check` 技能验证），并在 `planning`/`in_progress` 且文件定义了对应 `*-inline` 块时选该块；块缺失只影响措辞，不影响模式声明。指针值按 Trellis 规则归一（`tasks/<slug>`、`./`、绝对路径），指向不存在或不是目录时降级为 `stale`。修复记录或重新绑定任务后会在下一轮重新解析。
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
pnpm test    # node --test test/*.test.js
pnpm run test:compat 0.1.5-rc.2  # 临时副本中安装旧宿主并运行同一套测试
pnpm run test:compat 0.1.7-rc.2  # RC.2 动态工具与面包屑集成回归
pnpm run test:compat 0.2.0-rc.2  # 最新 0.2 RC.2 隔离回归
pnpm run test:compat 0.2.1-alpha.2 # 新工作目录与统一 activation 契约
# 默认：0.1.5-rc.2、0.1.6-alpha.2、0.1.7-rc.1、0.1.7-rc.2、0.2.0-rc.1、0.2.0-rc.2、0.2.1-alpha.2
```

GitHub Actions 配置在 Windows / Linux 的 Node 24 环境执行锁定的 `0.2.0-rc.1` 安装、客户端构建、测试、四条旧宿主、`0.2.0-rc.2` 与 `0.2.1-alpha.2` 隔离回归及打包检查。测试覆盖真实 Session/projection 的恢复、分叉、压缩和 checkpoint，临时项目的精确绑定与任务错误恢复，以及新版真实 Loader 的 volatile 更新、子代理目录/查询/驻留状态；新版专属测试在旧宿主明确跳过。另有编译客户端 React 渲染、slot 生命周期、原子保存与拒绝写入测试。

RC.2 集成用例运行真实 AgentLoop、Loader、ToolRuntime 和 Session，以本地脚本化模型响应验证三种 `toolUpdate` 能力：不支持、`addition-only`、`in-history`。覆盖插件启停的工具增删消息、Settings 重挂不重复注入、混合历史的恢复/分叉投影，以及 surface 替换后重建工具基线并重新注入面包屑。等待工具另覆盖目录损坏/不存在及卸载期间查询失败的错误保留与监听器清理。该验证不调用外部模型，也不替代 Web 浏览器或真实子代理派发验收；详情见 [2026-09-28 验证记录](https://github.com/SajoLuo/dsh-trellis/blob/main/docs/validation-dsh-0.1.7-rc.2.md)。

0.2 集成用例另以真实 AgentLoop / ToolRuntime / Session 和实际 `trellis_wait` 验证失败工具历史的补齐顺序、错误分类、监听器清理及继续会话的消息配对。只注入 scheduler 故障和本地模型响应，不增加运行时补丁或自动重试；旧宿主按 `ToolCallRecovery` 能力明确跳过。还覆盖“目录查询期间收到成功结算、随后查询失败”的竞争，查询错误不能被伪装成成功。

`test:compat` 不改当前 checkout 的依赖，临时副本保留在系统临时目录并打印路径供检查。宿主工具链采用显式支持列表：0.1.7 RC.1/RC.2 和 0.2 RC.1/RC.2 使用 Cordis 4.0.4、Schemastery 3.18.4、Loader 1.0.5、Include 1.0.9；0.2.1-alpha.2 使用 Cordis 4.0.5-alpha.1、Schemastery 3.18.5-alpha.1、Loader 1.0.6-alpha.1、Include 1.0.10-alpha.1。两条旧线保留各自旧依赖组合，不按“非最新版本”猜测。发布前还应使用隔离 `DSH_HOME` 启动真实 Web profile，验证配置保存/读回、整包及组件开关、重新挂载和卸载；不复用个人凭据或会话。此前 0.2 RC.1 Windows 验收已覆盖正常安装、表单保存/重置、配置停用、整包/组件卸载重挂、冲突保护和浏览器重载，详见 [2026-09-29 验证记录](docs/validation-dsh-0.2.0-rc.1.md)；本轮 alpha.2 尚未重跑浏览器验收。

Host half 是直接由 `main` 加载的 ESM JavaScript；Web half 通过 tsdown 生成 DSH lazy-CJS factory 到 `lib/client.js`。`pnpm pack` 会在 prepack 阶段自动重建客户端 bundle。

## License

MIT（`package.json`）。本个人使用的 Strategy A 副本不包含 LICENSE 文件，这不是缺陷；
范围见 [`../plugin-create.md`](../plugin-create.md) 的“范围排除”，手工验收见
[`docs/manual-verification.md`](docs/manual-verification.md)。
