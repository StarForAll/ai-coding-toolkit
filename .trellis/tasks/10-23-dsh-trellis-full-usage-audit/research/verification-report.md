# dsh-trellis 已安装版本使用效果验证报告

日期：2026-10-23。唯一工作任务：`10-23-dsh-trellis-full-usage-audit`。本报告保留修复前审计证据；外部会话完成 F1 测试修复后，本会话已独立复核，结果见 [修复后复核记录](post-fix-review.md)。插件运行时代码和真实 profile 未因本任务而修改。

## 结论

**在本次实际覆盖的核心集成机制上，已安装 `dsh-trellis 0.1.7` 能提供与 Codex 使用 Trellis 相当的效果，并补足 DSH 裸用时缺少的自动提示、spec 注入和子代理上下文 push。不能据此宣称完整使用体验或模型服从性百分之百相同。**

- 新建 `/tmp` 目标项目；当前 DSH CLI + 实际安装插件 + 本地确定性模型适配器完成 24 次主批次调用及补充实验。最终原始事件检查 **29/29 pass**。
- 真实 DSH 调用验证了：一次性 bootstrap、状态切换、整轮 skip、spec deny-once/重试/跨进程去重/内容变化/坏分片/过期 ticket/并发、角色 push、inline guard、原生子代理 wait 与父会话通知、身份绑定、命令注册表 handler、真实原生压缩和同版本 Trellis update 后存活。
- **F1（已修复，2026-10-23）**：当前 DSH 兼容测试两例使用旧式裸 user message，导致误失败；已补 `source` 并增加“至少一次模型请求”断言，`pnpm run test:compat 0.2.1-rc.2` 恢复 350 pass / 0 fail。没有据此发现插件运行时缺陷。**F2 已关闭（用户决定）**：`~/.dsh/profiles/headless` 是测试目录、后续删除，不用于跑 Trellis，因此不安装插件。
- 未发现本次已测主链路中的 P0/P1 运行时缺陷；Web 设置页实际交互、完整 Codex CLI 自动 hook 时序、真实模型服从性等仍有证据限制。
- 只读上游最终出现 `.gitignore` 的一行 `+.bce-tool/` 变化，疑似 BCE 检索副作用，未擅自恢复；见“只读边界事件”。

## 被测版本与证据边界

| 对象 | 本次实读事实 |
| --- | --- |
| DSH CLI | `dsh --version` → `0.2.1-rc.2` |
| Node | `v24.20.0` |
| Trellis CLI | `trellis -v` → `0.7.0-beta.4` |
| Codex CLI | `codex --version` → `codex-cli 0.163.0`；本轮实际对照是 fresh init 生成的 Python hooks，未启动完整 Codex 模型会话 |
| 插件安装态 | `/home/xzc/.dsh/profiles/web/node_modules/dsh-trellis` → `0.1.7`；真实 web profile 使用 ssh git 依赖快照，非源码 symlink |
| 插件源码 | `dsh-plugins/dsh-trellis` → `0.1.7`；开始和结束时安装态 `lib/` 与源码 `diff -rq` 均为空 |
| Trellis 上游 | `/home/xzc/projects/other/Trellis`，HEAD `be9e19b269c25cb2787489eb81062bf96619442c`；本地 reference 检出，并非据此声称网上最新版本 |
| DSH 宿主来源 | 当前全局安装包。`dsh-agent-loop/lib/index.js`、`dsh-settings/lib/index.js` 可见 `[dsh-purge]` 本地补丁标记，不能当作未经修改的 npm 官方原件；兼容矩阵另装精确 `0.2.1-rc.2` 包补证 |
| 临时证据根 | `/tmp/dsh-trellis-full-usage-audit-1023/`；最终批次使用 `evidence-final/` |

等级：**R1**=实际 DSH CLI/宿主和真实工具调用，本地脚本生成模型响应；**R2**=真实注册表/API 或 hook payload 直调；**R4**=源码/安装包/模板契约；**R5**=自动化测试。R1 不等于真实 LLM 行为评测。

隔离 profile 的依赖目录只读引用当前 web 安装的 `node_modules`，DSH 系统依赖由实际 CLI 安装解析；profile、运行状态、项目和输出写在 `/tmp`。这比计划中的复制快照更直接绑定实际安装对象，未改包文件，结束再次核对源码/安装态一致性。不复制凭据，不调用远端模型；DSH telemetry 显式关闭。测试只复用 `trellis init` 自动生成的临时 `00-bootstrap-guidelines` 记录，没有再创建工作任务或子任务。

## 当前机制的直接核验

1. Trellis 上游 `packages/cli/src/configurators/dsh.ts:1` 明确 DSH 是 class-2 pull 平台，生成 `.agents/skills`、`.dsh/skills` 和 `.dsh/DSH.md`，不安装 profile plugin 或 hooks。Codex 对照实现见 `packages/cli/src/configurators/codex.ts:132`。
2. fresh `trellis init --dsh --codex --user xzc --yes` 退出 0，生成 98 个托管模板。`.codex/hooks.json` 实际接线：`UserPromptSubmit`、`SubagentStart`、`PreToolUse(Edit|Write)`，以及 `SessionStart(clear|compact)`；存在 `session-start.py` 不代表启动时执行它。
3. fresh `.trellis/config.yaml` 的 spec 配置被注释，DSH 插件与 Codex hook 按自身缺省启用。脚手架 spec 初始没有实际 `paths` 规则，故本实验添加合成规则后再验证；没有误用本仓库关闭 spec 的配置作目标项目基准。
4. 当前 DSH `dsh-tools` 的 `tools/pre-execute`/`tools/post-execute` 确实支持 deny 与 additionalContexts；`dsh-subagent` 正式子会话创建包含 parentSession/origin/delegationDepth 和 descriptor。插件在第一模型请求前 push，不依赖不存在的 DSH `SubagentStart` hook。
5. Trellis `active_task.py:514` 的身份解析已能原生使用 `DSH_SHELL=1 + DSH_SESSION_ID`，插件额外贡献 `DSH_TRELLIS_CONTEXT_ID`。因此当前 Trellis 的基本会话身份能力**并非插件从无到有补齐**，插件补充托管身份和跨调用一致性；本轮裸 DSH env 直调也能排除外层 generic override。
6. 当前 DSH subagent 工具始终先返回 child id，原生发送完成通知；上游 fallback 文案中的 `run_in_background:false` 不在当前工具参数中。插件提供 `trellis_wait` 可走上游已有 wait 分支，裸用时应承认该上游文本的适用边界。上游只读，不提出上游补丁。

## 实测对照矩阵

| 能力 | Codex + fresh Trellis | DSH 裸用 | DSH + 当前已安装插件 | 判定 |
| --- | --- | --- | --- | --- |
| 无任务 bootstrap | hook 直调输出 bootstrap（R2） | R1 无插件消息 | R1 新根会话仅一次，resume 不重复 | 目的相当，频率为已接受差异 |
| workflow 状态 | 直调从 workflow 块生成（R2） | 只有主动 pull | R1 planning-inline / in_progress-inline / completed / reviewing / task_error / stale 正确 | 核心自动接线补足 |
| 整轮 skip | hook 直调使用 prompt escape hatch | 无注入可跳过 | R1 `no-trellis` 下两步请求均无插件消息 | 通过 |
| 首次 spec 写入 | hook 直调 FULL + deny；同 session 二次静默（R2） | R1 两次写入都成功，无注入 | R1 一次 deny 带完整正文，第二次成功 | 补足主要缺口 |
| spec 恢复/刷新 | reset/刷新由 hook 及脚本契约支持（R4） | 无策略 | R1 新进程不重复；内容变更/坏分片重新 FULL；人为老化 timestamp 后非阻断 ticket | 通过；ticket 时间用可控状态老化，不是假称等待 45 分钟 |
| 显式 Read 触发 | 默认 matcher 不含 Read | 无策略 | R1 显式启用 Read 后读取成功，下一模型请求含完整 spec | 支持，送达阶段有宿主差异 |
| 并发 | 本轮未跑 Codex 并发 CLI | 无策略 | R1 两个 session 各自 deny 一次，独立分片，均写成功 | 已测 DSH 通过 |
| 子代理角色/curated context | fresh hook/TOML 契约核验（R4） | Trellis 依赖 child-pull | R1 两个真实 child 首请求各有一个角色 push，含 role skill、spec、PRD | push 缺口补足 |
| inline guard | Codex 以指令声明 inline | 不拦截 | R1 派发前拒绝，child 未启动 | 插件增强；只是流程守卫 |
| 子代理 wait | Codex 原生机制，本轮未完整 CLI 对照 | DSH 当前已有完成通知，但无 `trellis_wait` | R1 child 完成后 wait 返回；下一父请求实际有 `subagent-settled` notice；无效 id 拒绝 | 补充同步屏障；不把 wait 单独误当“报告已读” |
| session identity | hook payload/session 解析（R2/R4） | Trellis 当前已有原生 env 支持（R2） | R1 Bash start/current 返回同一 dsh_session-* | 通过；补强已有基础能力 |
| 命令 handler | 本仓库 Codex 无同形项目命令 | 无插件命令 | R2 真实 commands.execute：status/finish/doctor 成功；参数拒绝；command/run/done 成对记录 | handler 通过；Web 输入路由未验证 |
| headless `/trellis-status` | 无相同入口 | 普通模型 prompt | R1 原文本送给模型，无 command/run | 宿主限制仍存在，有文档与 shell 等价路径 |
| 压缩恢复 | Codex reset hook 契约（R4） | 无插件恢复 | R1 原生 compactNow 成功，bootstrap/面包屑重注入；下次写入重新 FULL deny | 通过，无伪造 compaction 事件 |
| 安装/更新 | fresh 生成物契约（R4） | 不安装插件 | R1 插件加载；临时项目同版本 update 后启动仍注入 | 当前版本通过，不外推跨版本升级 |
| 配置/设置/版本监控/冲突 | 非本轮 parity 核心 | 无该插件能力 | R5 + R4 覆盖开关、live Config/Loader、设置视图、路由和冲突；Web 真实 UI 受认证限制 | 部分验证，不宣称 UI 全通过 |

**补足范围的实际含义**：插件自动接线补足了裸 DSH 的 bootstrap、workflow-state、spec policy 和 role push；`trellis_wait` 给 DSH 已有原生通知增加可调用的等待屏障，inline/no-task guard 及 doctor 为额外增强。Trellis 共享/入口/角色技能和基本 session identity 原本已可用，不重复算成插件成果。

## 验证明细（修复前原始审计）

- 主批次：`node /tmp/dsh-trellis-full-usage-audit-1023/run-suite.mjs`，最终 24 次调用均有 session/final，exit 0；记录 `evidence-final/suite-results.json`。脚本驱动工具并断言事件，模型回答 `AUDIT_LOCAL_DONE` 本身不作为通过依据。
- 事件复核：`node /tmp/dsh-trellis-full-usage-audit-1023/verify-evidence.mjs`，29 pass / 0 fail，见 `evidence-final/assertions.json`。
- 补充实验：`node /tmp/dsh-trellis-full-usage-audit-1023/supplement.mjs`。x01–x06 为 spec/损坏/refresh/并发；x07 为真实原生 compactNow，shadowedTokenCount=12318，正式 compaction/start/checkpoint/end；x08 update 退出 0 并显示 Already up to date；x09 后续启动通过；x10/x11 为命令与 Read。
- 根仓库 `pnpm test`：350 tests / 346 pass / 0 fail / 4 skip。其依赖锁定为 DSH 0.2.0-rc.1，不能代替当前宿主兼容性结论。
- `pnpm run test:compat 0.2.1-rc.2`：隔离安装精确版本后 **350 tests / 348 pass / 2 fail / 0 skip**；故原始兼容检查为失败，不能写成全绿。
- 原始两例在兼容副本直接执行再次复现（`compat-native-original.out`）；捕获 agent/error 后定位到 DSH AgentLoop 请求前访问 `message.source.kind`。首步 push 已成功，因 user fixture 缺少 source 导致适配器请求为空。
- 仅 `/tmp` 副本使用当前 `createUserMessage({content, source:{kind:'user'}})` 后，两例通过；正式权限下完整兼容副本 **350 pass / 0 fail / 0 skip**（`compat-diagnostic-adjusted.out`）。这只是根因验证，不是已修复仓库测试。
- fresh Codex hooks 实际直调：无任务 bootstrap、auto mode、in_progress 块、首触 spec deny、二次静默；spec 状态目录在 `/tmp/.../codex-spec-state`。未借用上轮完整 Codex CLI 结果冒充本轮 S1。
- 交付检查：持久化的 `research/verify-evidence.mjs` 仍为 29/29；`git diff --check` 退出 0。`task.py validate dsh-trellis-full-usage-audit` 退出 1，原因为 `implement.jsonl`/`check.jsonl` 各 0 curated entries；本项目 inline 流程按约定不消费这些 manifest，已用文档支持的 `start --allow-empty-context` 启动。保留空 manifest，未为通过检查制造子代理上下文，不把此已知流程差异列为插件问题。

## 问题与处理结果

### F1 — P2 / 测试基础设施：当前 DSH 兼容测试误失败

**证据**：`dsh-plugins/dsh-trellis/test/native-subagent-push.test.js:25` 直接构造没有 `source` 的对象；第 80/116 行送入 child，83/119 行读取空 adapter request。DSH 0.2.1-rc.2 `dsh-agent-loop/lib/index.js:1067` 在模型调用前读取 `message.source.kind`，因此先报 agent/error，再被外层测试掩盖成 `undefined.messages`。

**影响**：按仓库提供的精确版本兼容检查无法全绿，错误信号会掩盖真正的子代理兼容回归。此次实际 CLI push 和临时诊断证明不是“插件无法 push”的缺陷。

**推荐方案（已按最小方案执行）**：只改此测试文件：在共享 `user()` helper 中补 `source:{kind:'user'}`；同时先断言 adapter 至少收到一次请求，避免再次只见 undefined。保持两个业务断言和角色边界不变。未引入 `createUserMessage` import，以免给旧宿主版本的兼容矩阵新增依赖。

**验证**：原始两例、`pnpm test`、`pnpm run test:compat 0.2.1-rc.2`；要求当前 host 全部断言通过。**回滚**：仅还原该文件的本任务变更。**安装影响**：没有运行时代码变化，无需更新已安装包或重启 DSH。

**修复记录（2026-10-23）**：`pnpm test` → 350 tests / 346 pass / 4 skip；`pnpm run test:compat 0.2.1-rc.2` → 350 pass / 0 fail / 0 skip。仅测试文件变更。


### F2 — P3 / 条件性部署覆盖：真实 headless profile 没装插件

**证据**：`~/.dsh/profiles/headless/package.json` 只有 `dsh-base` 与 `dsh-headless`；当前 profile 目录枚举只找到 web 安装包。裸 profile 的 R1 对照无 bootstrap/面包屑/spec policy/push 等插件功能；Trellis init 本身不会安装它。

**影响**：若用户直接以这个 headless profile 跑 Trellis，无法获得已在隔离插件 profile 证明的自动接线。不是 web 插件安装错误，也不是插件实现缺陷。

**可选方案**：

- **F2-A（若确实使用 headless，推荐）**：明确授权后，为真实 headless profile 安装同一 `0.1.7` 插件并加入 bundles；先预览最小 package/patch 变化和备份范围，再测 bootstrap/spec/身份/push，保留原 profile 的其余配置；无需读取或迁移密钥。
- **F2-B**：只在已安装插件的 web profile 使用 Trellis，保留原 headless 用途，接受这个覆盖边界。

**回滚**：恢复本次安装前 profile manifest/lock/patch 的已确认改动和 bundle 声明；不删除用户其他依赖或状态。**兼容边界**：安装插件也不能使 headless 纯文本 slash 命令自动进入交互命令通道。

**后续决定（2026-10-23）**：用户确认 `~/.dsh/profiles/headless` 是测试目录、后续会删除，不会用于跑 Trellis；因此 F2 关闭，不安装插件。该边界已记入 `.trellis/spec/platforms/dsh-workflow-behavior.md` 的验证注意事项，避免后续再次把它作为问题上报。

### 可选缓解 M1 — headless 命令提示（非必修）

现有 README 已给 shell 等价命令，运行边界有 R1 证据。若用户希望尽量减少模型把普通 `/trellis-status` 文本当真命令，可在**确认后**评估对精确 `/trellis-status|finish|doctor` 输入添加一次可核验的提示/等价命令说明；不冒充宿主命令通道，不自动执行具有收尾副作用的操作。仅在插件可可靠识别输入入口时实现，不用猜测 headless。验证 mock prompt、真实 CLI 和既有命令注册表不互相遮蔽；回滚该提示相关文件。F1 已修复，M1 维持现状、不实施。

## 不立项的差异与未验证项

| 项 | 本次判断 |
| --- | --- |
| bootstrap 每会话一次 vs Codex 按轮提醒 | 明确已接受的降噪设计；真实 resume 和压缩恢复均验证，不要求改频率 |
| DSH 默认 inline、Codex 默认 auto | 独立配置设计；实际可显式 auto 并 push/wait，通过；不擅自改默认 |
| 旧 banner 在同会话切换模式后仍在历史 | README 已记录；本轮未做模式切换专项，不重复作为新问题 |
| wait 返回 notice delivery unverified | 插件不对 host 无法保证的信号作承诺。两次实测下一父请求有原生 notice；不因字符串保守就判缺陷，也不把 wait 返回当作模型已经阅读报告 |
| generic role/path 误识别、context budget、Loader 热更新、设置保存/路由/冲突 | 本轮 R5+R4 覆盖；不是全部真实 UI/CLI 场景。doctor 将本地适配器路径中的 trellis 命中为冲突符合其宽匹配约定，本轮排除测试命名造成的告警 |
| Web 设置页/版本监控/冲突桌面通知 | 已实际启动隔离 Web 并用 agent-browser 打开 root，页面要求认证；未读 token，未绕过登录，因此 UI 交互仍未验证。临时进程与浏览器已关闭 |
| 完整 Codex exec/自动 hook 时序、Codex child lifecycle | 本轮只执行 fresh hooks 和读取配置/角色契约，未启动完整 Codex 模型会话；不能给完整运行时等同保证 |
| 真实模型能否自觉遵守所有规划/验收/提交要求 | 不在确定性 adapter 能证明的范围；本轮没有真实 LLM API 调用或费用，不能冒称模型行为已评测 |
| 子目录 edit / workflow 变体 / windows / 跨版本升级 / 自然压力触发压缩 / clear | 子目录与变体以自动化测试和源码支持，未全部做 R1；Windows、跨版本升级和 clear 未测。压缩通过实际 compactNow 验证，未跑百万 token 自动压力场景 |

## 只读边界事件与执行限制

- 起始上游 `git status --short --branch` 干净；最终只出现 `.gitignore` 新增 `+.bce-tool/`，HEAD 未变，其他 tracked 文件无 diff。mtime 为 2026-10-23 16:54:41 +0800，与 BCE 检索阶段接近，**疑似**检索工具副作用，未完整归因。已停止向上游调用 BCE，未自行还原或修改任何上游文件；此处不能声称整个上游工作树从未变化。该行不改变核验中的脚本/模板内容。
- GitNexus 只列出无关 `loop-hive`，本仓库和上游没有可用图索引；调用关系用本地精确搜索、文件读取和实际事件补证，不作图完整性保证。
- 最初对真实 headless 的 `--help` 和 `--dump-default-config` 都会触发 DSH 重写 cordis.yml，被 EROFS 拒绝；两条失败不用于判定用户机器异常。后续真实 profile 未再执行 DSH 启动命令，所有启动都在隔离 DSH_HOME，并按正式审批处理监听、browser 和 package store 限制。
- Node runner 在沙箱下有过退出 0 却未返回 session/stdout 的记录；其本地日志显示仍有部分 /tmp 调用发生，故不能将空输出视为未执行或通过。最终 evidence-final 用受审批的完整子进程批次和显式事件断言；旧 evidence 的追加日志不用于最终计数。
- 用户既有 `docs/capability-inventory.md`、`dsh-plugins/plugin-create.md` 保留；不按其旧版指令追加开发任务或直接修复。只有本任务目录新增交付物；未提交、未推送、未归档。

## 执行闸门

- **F1**：已按用户授权修复并验证（仅测试文件变更；`pnpm test` 346 pass / 4 skip，`test:compat 0.2.1-rc.2` 350 pass / 0 fail；安装态无变化）。
- **F2**：用户已确认关闭（headless profile 是测试目录、后续删除，不用于 Trellis；不安装插件）。
- **M1**：接受现状（DSH 宿主限制，README 已给等价 shell 命令）。
- 其余未验证项边界继续保留；本任务没有其他待执行修复。

## 修复后复核与收尾

- 独立复跑 `pnpm test`：346 pass / 4 skip / 0 fail；`pnpm run test:compat 0.2.1-rc.2`：350 pass / 0 skip / 0 fail。
- `/tmp` 三组故障对照分别移除 `source`、停用 push、改变泛描述标签为精确角色标签，均按预期触发断言失败；现有测试仍能检出相关故障，未放宽原有业务断言。
- 已安装 web 插件 `lib/` 与源码比较退出 0；运行时代码和依赖声明无修改。未发现本次修改引入需要处理的新问题。
- F2 的关闭属于使用范围澄清，M1 保留为已接受限制；不把两者记为运行时修复，也不扩大已有对等性结论。
- 用户已要求完结当前唯一任务，并授权仅做本地提交、不推送、保留其他文件；按原生流程归档及记录日志。
- 详见 [修复后复核记录](post-fix-review.md) 和 [证据索引](evidence-index.md)。
