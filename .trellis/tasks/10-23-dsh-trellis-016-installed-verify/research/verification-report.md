# 已安装 dsh-trellis 0.1.6 全面验证报告

- 日期：2026-10-23
- 任务：`.trellis/tasks/10-23-dsh-trellis-016-installed-verify`
- 运行时：DSH `0.2.1-rc.2`；Trellis CLI `0.7.0-beta.4`（与只读上游 `~/projects/other/Trellis` 同版本）；Codex CLI `0.163.0`；Node `v24.20.0`
- 验证对象：**已安装** `~/.dsh/profiles/web/node_modules/dsh-trellis` = `0.1.6`；验证时与本仓库源码 `lib/` 逐字节一致（diff -rq 为空，两轮复核）。
  - 后续 0.1.7（F1/F2 文档轮）使源码 `lib/client.js` 的 `PLUGIN_VERSION` 变为 0.1.7，故现在源码↔已安装副本的 diff 仅剩该一行版本 stamp；无逻辑差异（见 §8）。
- 隔离环境：`/tmp/dsh-trellis-016-verify/`（DSH_HOME 隔离 home、测试 profile `trellis-headless` 以 file-link 挂载源码 0.1.6、`bare-headless` 无插件对照 profile；凭据经 env 注入不回显）
- 临时项目：`proj`（git + codex + dsh 面）、`proj-fresh`（C3 终检）、`proj-nogit`（无 git）、`plain`（非 Trellis）
- 证据目录：`/tmp/dsh-trellis-016-verify/evidence/`（s01–s40 会话 stdout/err + 隔离 home 会话日志 zstd + s2-*.mjs）

## 1. 结论摘要

1. **主链路全部达到 Codex 同等效果，未发现任何 P0/P1/P2 级插件缺陷**：0.1.5→0.1.6 的五项修复（C1/C2/C3/C6/C7）在已安装副本上全部实测通过；breadcrumb/bootstrap/spec 注入/子代理 push/守卫/命令/身份/升级链路真实会话（S1）全绿。
2. **补足评估：已补足 plain DSH 的全部主要缺口**（S1 对照实测）：无插件时 spec 被静默违反、无任何注入、无守卫、无 wait、无命令面；装插件后逐项补齐。
3. **新发现 2 项 P3 级观察 + 1 项环境事实**（见 §5，均有候选缓解，是否处理由用户决定）：
   - F1 headless 文本模式不路由 `/trellis-*` 命令（宿主限制），模型自行解释时出现过"插件未安装"的**错误声明**；
   - F2 dispatch_mode 切换后，会话历史中的过期 `<dsh-mode>` banner 会误导模型（本轮 s20 实际触发一次）；
   - F3 真实环境仅 web profile 装有 0.1.6，`~/.dsh/profiles/headless` 无插件（bare 行为）。
4. **已知上游边界（O 系列，按只读政策不计入问题）**：本轮再次观察到 Trellis 0.7.0-beta.4 的 `get_context.py --platform dsh` 仍输出 `run_in_background: false` 过期指引（O2）；U1 身份优先级边界未变。
5. 单测基线 **350 tests / 346 pass / 0 fail / 4 skip**（与 0.1.6 发布记录一致）。
6. 验证限制（诚实声明）：真实 compaction、Web GUI 交互、Codex exec 内 hook 自动触发（信任状态）三项未能本轮 S1 实测，以 S2/S4/上轮 S1 工件覆盖（见 §6）。

## 2. 证据等级

| 级别 | 手段 | 本轮用量 |
| --- | --- | --- |
| S1 | 真实 DSH 会话（真实 LLM + 真实工具调用，隔离 DSH_HOME，约 30 个场景 s01–s40） | 主结论 |
| S1 | 裸 DSH 对照（bare-headless profile） | 补足评估 |
| S2 | 直载**已安装 web 副本**模块（命令处理器 / upstream / conflicts）+ Codex 三 hook 真实 payload 直调 | 行为对照 |
| S3 | 源码 ↔ 安装副本逐字节 diff；上游 Trellis 模板/脚本只读比对 | 根因/边界 |
| S4 | `node --test`（350/346/0/4） | 回归 |

> 模型"自述"仅作线索；所有结论以会话日志（`source.kind=dsh-trellis` 消息、tool deny/result、runtime 指针/分片文件）为准。

## 3. 0.1.6 修复回归表（全部对已安装副本实测）

| 上轮编号 | 内容 | 本轮验证 | 证据 |
| --- | --- | --- | --- |
| C1 | 角色误判（generic/路径提及/话题型 description 不触发 push/守卫） | ✅ 4 变体全过：路径提及+`docs reader`→0 注入；首行 `trellis-agent-check:`→push role=check；description 严格前缀 `trellis-agent-check (audit round 3)`→push；话题型 `研究 trellis-agent-implement 插件的 README`→0 注入 | 子会话 6e8ae428 / acac3e3a / c587981f / 205bf01b 日志 |
| C2 | 子目录 cwd 相对路径 spec 漏注入 | ✅ cwd=`proj/src` + `d.js` → deny + spec 正文 + 重试合规 | s15-subdir + 分片 |
| C3 | 默认 inline + 不写 tracked config | ✅ `proj` 首会话与 `proj-fresh` 首会话后 `git status` 均干净、无 `dsh:` 段写入；banner 含 phase 覆盖与 `--allow-empty-context` 指引 | s01 / s40 |
| C6 | 安装版本一致性 | ✅ web=0.1.6=源码逐字节一致；新发现 F3（headless profile 无插件，见 §5） | diff -rq 双轮 |
| C7 | 文档/契约补充 | ✅ README 声明与实测一致（read 默认不在 tools、ticket 需显式配置 Read 后经 post-execute 送达、子代理不收 bootstrap 等） | 全轮对照 |

## 4. 逐维度实测结果

### 4.1 DSH 主链路（S1）

| 维度 | 结果 | 证据（evidence/ 与隔离 home 会话日志） |
| --- | --- | --- |
| 面包屑六状态 | no_task / planning-inline / in_progress-inline / stale / task_error / completed 全部按状态变化即时注入，未变不重复 | s01/s07/s08/s17/s18/s19 |
| stale 专用正文 | 指向不存在任务目录 → 专用诊断文案（"stale pointer, not a missing workflow-state block"） | s17（指针文件名须为 `dsh_session-<sid>.json`，首次误写无前缀属操作错误） |
| bootstrap | 新根会话一次；同会话 resume（新进程）不重复；stale 轮不重复（每会话一次设计）；子代理/generic 子代理零注入 | s01/s01b/s17/s22 |
| skip 关键词 | `no-trellis` 单独成词整轮跳过（含工具调用后的后续 step） | s01c |
| 非 Trellis 零注入 | plain 目录 0 条 dsh-trellis 消息（含命令会话） | smoke-plain / s34 |
| 无 git 项目 | 正常注入（projectRootMarkers `.trellis` 优先） | s36 |
| 身份 | 模型 shell 内 `DSH_SHELL=1` + `DSH_SESSION_ID` + `DSH_TRELLIS_CONTEXT_ID=dsh_<sid>`；`task.py create/start` 写会话指针；`/trellis-*` 子进程同身份 | s06 / s07 / s08 |
| spec deny-once | write `src/app.js` 首次 deny + `<spec-context sha256>`，读 spec 后重试成功 | s09 |
| spec 窗口静默 | 窗口内 `src/b.js` 0 deny | s10 |
| spec sha 变化 | spec 内容变更后 `src/c.js` 重新 FULL deny（新 sha 入分片） | s11 |
| read ticket | 默认 read 不触发（文档一致）；配置 `tools:[Read,…]` 后 read 不阻断、spec 经 post-execute 以 `form=spec-context` 消息送达；大写工具名规范化生效 | s12/s13/s14 |
| 子目录 spec（C2） | cwd=src + `d.js` → deny + 合规重试 | s15 |
| 并发分片 | 双会话并行写不同文件，各自独立分片无串扰（另见 implement 子代理自己也拿到 spec deny） | s37/s38 + spec-inject/ 目录 |
| 分片持久化 | `.trellis/.runtime/spec-inject/<session>.json` 原子写入；`.trellis/.gitignore` 覆盖 `.runtime/`，工作树零污染 | 分片文件 + git check-ignore |
| 升级后存活 | `trellis update --skip-all` 后面包屑/命令/守卫正常 | s35 |
| inline 守卫 | inline + 活跃任务 + 声明式 implement 派发 → 拒绝，文案含"Leaving inline mode is the user's decision"与两条出路（config 改 auto / `dsh.inline_allow_dispatch: true`） | s29 |
| 无任务守卫 | no_task + 声明式 implement 派发 → fail-closed 拒绝（"Codex would inject nothing here…this plugin fails closed"），子代理未启动 | s26 |
| research 放行 | no_task + `Role: trellis-agent-research` 派发 → 允许运行，父会话收到 `form=dispatch-guard role=research` 的输出位置提醒；子代理本身 0 push（无任务，与 Codex 静默一致） | s27 父/子日志 |
| implement push | 子代理首步 `form=subagent-context role=implement`：角色契约（"Trellis Native Implement Subagent"）+ 递归防护 + Curated Context（含 prd.md 正文） | 子会话 55662055 seq12 |
| 子代理 spec | 子代理 write `src/feature.js` 同样被 deny 并合规（`// demo-spec-applied` + `// spec-v2`） | 子会话 55662055 seq42 |
| trellis_wait | 真实汇合返回 `completed; settlement notice delivery is unverified; inspect its report…`（不冒充干净 settled）；不存在的 child id 直接拒绝（"can only wait for a direct continuable subagent"） | s21 / s28 |
| `.dsh` 闸门 | 空实施/检查 jsonl 的 `task.py start` 被拒并给出 curate/`--allow-empty-context` 指引；带参重试成功 | s08 |
| auto 模式 | `dsh: dispatch_mode: auto` 后面包屑状态名 `in_progress`（无 -inline）、无 banner、派发链路全通 | s20–s25 |

### 4.2 命令面（S2，已安装副本直载）

- `trellis-status` / `trellis-finish` / `trellis-doctor` 注册与执行正常；输出含任务指针、git 状态、模式、版本、workflow 块数、spec 计数。
- 带参数调用 → 显式拒绝 "This Trellis command does not accept arguments or image attachments."
- 非 Trellis 目录 → "No project root found from the configured markers."
- 详见 §5 F1：headless 文本模式不路由命令（宿主限制）。

### 4.3 Codex 对照（S2 直调真实 hook + payload；S1 见 §6 限制）

| hook | 直调结果 | 与插件对照 |
| --- | --- | --- |
| UserPromptSubmit（inject-workflow-state.py） | `<trellis-bootstrap>` + `<codex-mode>auto…` + `<workflow-state>Status: no_task…` | 插件：bootstrap 独立消息家族 + 面包屑 + （仅 inline 时）`<dsh-mode>`；内容对齐，默认模式 auto(Codex) vs inline(插件，用户已确认的设计选择 B) |
| PreToolUse（inject-spec-context.py） | Write `src/z.js` → `permissionDecision: deny` + `<spec-context sha256>` | 插件 deny-once 同构；实测两侧对同一 spec 输出一致 |
| SubagentStart（inject-subagent-context.py） | 父指针存在 → 注入与插件**同款** "Trellis Native Implement Subagent" 角色契约 + curated 上下文（空 jsonl 时同样警告）；父指针缺失 → 0 输出（静默） | 插件多了 prompt `Active task:` 回退路径（更稳健）与 dispatch-guard fail-closed（DSH 增强） |

### 4.4 补足评估（R5：plain DSH 差距 → 插件覆盖）

| plain DSH（bare-headless 实测） | 插件后 |
| --- | --- |
| 0 条注入（无 breadcrumb/bootstrap） | 六状态 breadcrumb + bootstrap |
| `write src/bare-test.js` 静默成功、**spec 被违反**（无 demo-spec-applied 首行） | deny-once → 合规（s09/s15/s37/s38，含子代理） |
| 无子代理上下文 push | 角色契约 + curated context（Active task 优先/父指针回退/双缺失静默） |
| 无 fail-closed 守卫 | 无任务/inline 守卫 + research 提醒 |
| 无事件驱动等待 | trellis_wait（含 fail-closed 结论） |
| 无命令面 | /trellis-status、/trellis-finish、/trellis-doctor（S2） |
| 无受管身份 | DSH_TRELLIS_CONTEXT_ID 全链一致 |
| 判定 | **已补足**（无"部分补足"项；宿主限制项见 §6） |

## 5. 新发现与候选方案（待用户确认；未确认前不修复）

### F1（P3·宿主限制+UX 缺口）headless 文本不路由 `/trellis-*` 命令，模型自行解释可产生错误声明

- 现象：prompt 恰为 `/trellis-status` 时（s30）命令并未经命令通道执行，输出实为模型自行跑 `get_context.py` 拼装（该会话 61 次 bash 调用）；带参数（s33）与 plain 目录（s34）同样不走命令通道。s33 中模型在**插件明明正在注入**（该会话有 bootstrap+breadcrumb）的情况下声称"本安装未装 dsh-trellis 插件"——事实性错误。
- 归属：DSH 宿主的命令路由只在 Web/TUI 输入面生效，headless 文本无命令通道（宿主限制）；错误声明是模型即兴产物。
- 影响：headless/管道用户以为在用命令，实际拿到模型仿制品（偶发事实错误）。
- 候选：① 维持现状 + 在插件 README「限制」节写明"headless 文本不路由 /trellis-*，请直接用等价 shell（task.py current / get_context.py）"（推荐，零代码）；② 注册同名兜底 skill（`trellis-status` skill 引导模型转述命令输出）——引入新维护面，不推荐；③ 无（纯宿主问题）。

### F2（P3·设计权衡）dispatch_mode 切换后，历史 `<dsh-mode>` banner 误导模型

- 现象：s20 中 config 已切 auto、当轮注入已无 banner，但模型引用会话历史里旧的 inline banner 拒绝派发；用户提示忽略过期 banner 后（s21）一切正常。
- 归属：投影去重设计下旧 banner 保留在历史（与 Codex 每轮重注新 banner 的做法不同）；状态变化会注入新 breadcrumb，但"模式已变"没有专门通告。
- 影响：低频（仅中途切换模式的会话），一次用户澄清即可恢复。
- 候选：① 维持现状（README 已写 banner 语义；推荐）；② 模式变化时随新 breadcrumb 附一行 "dispatch mode changed: inline → auto; earlier <dsh-mode> banners in this session are obsolete"（小改动 + 单测）；③ 无。

### F3（环境事实·非插件缺陷）真实环境安装覆盖不全

- 现象：`~/.dsh/profiles/` 仅 `web` 装有 0.1.6；`headless` 无插件（bare 行为，见 §4.4 左列）；上轮的 `trellis-headless` profile 已不存在。
- 候选：① 用户按需 `dsh plugin --profile headless add <本仓库 dsh-plugins/dsh-trellis>` 并重启；② 保持现状（只用 web profile 跑 Trellis）；③ 重建专用 profile。

### O 系列边界（上游只读，不计入问题、不修复）

- O2 复现：`get_context.py --mode phase --step 2.1 --platform dsh` 仍输出 "Without `trellis_wait`, dispatch that child with `run_in_background: false`"，而 DSH 0.2.1-rc.2 已移除该参数（上轮 headless-19 与本轮 request/header 工具 schema 均证实）。上游文件未变，按只读政策仅记录。
- U1（Codex-in-DSH 身份优先级）未重新触发，政策不变。

## 6. 验证限制（未覆盖项及补偿证据）

| 项 | 状态 | 补偿 |
| --- | --- | --- |
| 真实 compaction/end | 未触发（headless 无 /compact 入口；1M token 窗口下不可行） | `spec-policy` 的 compaction 重置有单测（S4）；`compaction/end` 处理源码（S3）；README 声明与实现一致 |
| Web GUI（设置页/版本监控 banner/冲突横幅） | 未进入（本地鉴权 URL 含 token，按凭据纪律不写入命令行/URL） | 设置卡/版本监控/冲突视图有 S4 单测（version-check/conflict-view/client-conflicts）；路由与决策函数 S2 直载正常 |
| Codex exec 内 hook 自动触发 | 本轮未复现（新旧项目 + `--dangerously-bypass-hook-trust` + `-c features.hooks=true` 均未注入；`[features] hooks=true` 在位；判定为 Codex hook 信任状态问题，需交互式 `/hooks` 审批，headless 无法完成） | 三 hook 以真实 payload S2 直调全过；上轮 S1 工件（codex-06-quote.jsonl，同版本同 hook 文件）经查验存在且证明 exec 内可触发 |
| Windows 路径/编码 | 未验证 | —（与本机无关） |

## 7. 安全与卫生

- 凭据仅经 env 注入子进程，未出现在任何输出/日志/命令行（本轮全部 evidence 复查无泄漏）。
- 隔离 DSH_HOME 完整复刻凭据文件（cp，未读取内容）；`~/.codex/config.toml` 的明文 bearer token 问题为上轮已知附带发现，本轮未触碰该文件、不复述值。
- 本任务验证阶段零仓库改动：`git status` 仅用户既有的两个未跟踪文件。后续 0.1.7 文档轮（F1/F2 处置）的工作区变更见 §8。

## 8. 执行方案（已确认并实施，2026-10-23）

> 任务状态：`in_progress` 为有意保留（用户要求后续其指示时再执行 finish-work 归档与提交）；验收项待提交后随收尾勾选。

| 项 | 用户决策（最终） | 实施 |
| --- | --- | --- |
| F1 | **补充文档说明** | 插件 README 新增「headless 文本限制」节（含等价 shell 命令）；仓库 spec `dsh-workflow-behavior.md` 新增 Command routing surface 节 |
| F2 | **补充文档说明**：同会话避免中途切换；必须切换时优先新开会话，或明确告知模型旧 banner 已过期并以当前配置为准 | 插件 README inline 语义列表新增「避免同会话中途切换模式」条；spec 新增 Mid-session mode switches 节 |
| F3 | **保持现状**（仅 web profile 使用 Trellis） | 无动作 |

实施为文档 + 版本号变更轮：插件版本 0.1.6 → 0.1.7（package.json/README/LOCAL_CHANGES/docs/validation-0.1.7-local.md 四处一致，client bundle 重印）；无 lib 逻辑/测试变更（`lib/` 中仅 `lib/client.js` 的 `PLUGIN_VERSION` 版本 stamp 随构建变化），单测回归 350/346/0/4 保持基线。已安装 web 副本仍为 0.1.6：本轮无运行时变化，仅为文档重装不必要；要让已安装用户看到新 README 需提交/推送后更新 profile。
