# Report — dsh-trellis 安装态端到端对标验证与 inline 模式审查

> 证据等级：E1 = 本轮真实执行（真实 DSH 进程 / 真实 hook 进程 / 真实文件与 HTTP）；E2 = 静态推断；
> E3 = 文档与单测声明。结论只用 E1，E2/E3 均显式标注。
> 本轮**未修改** `dsh-plugins/dsh-trellis` 任何源码，也未改动用户 profile。

## 0. 一句话结论

已安装的 dsh-trellis 0.3.9（web profile 软链到本仓库源码）在真实 DSH 0.2.1-rc.2 中**能补足 DSH 使用
Trellis 的核心缺口**：每轮状态面包屑、bootstrap、路径级 spec 注入、子代理上下文推送、fail-closed
派发守卫、事件驱动 `trellis_wait`、会话身份，全部 E1 实测通过，且 4 个核心状态的注入正文与 Codex hook
**逐字节相同**。**inline 模式确实已实现**，主链路正确；但存在 1 个边界缺陷（inline 块缺失时静默退化成
auto 语义且无任何横幅）和 1 个设计缺口（inline 只是提示，派发守卫并不拦截）。未发现 P0/P1 级问题。

## 1. 验证方式（全部 E1）

- 唯一临时项目：`/tmp/trellis-verify-20261021-1547`（`trellis init --dsh --codex -y -u xzc`，Trellis 0.7.0-beta.4）。
- 独立 `DSH_HOME=/tmp/dsh-verify-home-20261021-1547`，headless 模板 + 软链插件源码；用户 `web`/`headless` profile 未改动。
- 本地 mock LLM 记录模型**实际收到的完整 messages/tools**；每场景保留 `requests.jsonl` / `events.jsonl`。
- Codex 基线：真实 `.codex/hooks/*.py` + 真实 payload 的逐字输出；另跑一次真实 `codex exec`（见 §6）。
- 单会话逐状态切换（`--session-id` 续接）+ 独立会话执行工具类场景。
- 详见 `findings/environment.md`、`findings/state-breadcrumb.md`、`findings/spec-injection.md`、
  `findings/subagent.md`、`findings/inline-mode.md`、`findings/commands-limits.md`。

## 2. 能力对照（Codex 实际接线 vs DSH 安装态）

| 能力面 | Codex | DSH（本轮实测） | 判定 |
| --- | --- | --- | --- |
| 无任务 bootstrap | 每轮无任务时附 `<trellis-bootstrap>` | 新会话一次，独立消息；子代理不注入 | 通过（频率差异为有意设计） |
| 每轮 workflow-state | UserPromptSubmit hook | `agent/pre-step` 注入，状态切换即更新 | **通过**（4 状态正文逐字相同） |
| 状态覆盖 | no_task/stale/task_error/planning/in_progress/completed/自定义 | 全部可达，`completed`/自定义不再被改写 | **通过**（DSH 的 stale 命名更准确） |
| workflow 变体选择 | task → `.developer` → `default_workflow` → 全局 | 同优先级，实测 3 层生效 | **通过** |
| skip 关键字 | 项目 `prompt_injection.skip_keyword` | 实测命中即 0 注入 | **通过** |
| 路径级 spec 注入 | PreToolUse(Edit/Write) deny-once + ticket | tools/pre-execute deny-once + post-execute ticket | **通过**（deny 文案与 spec-context 逐字相同） |
| 子代理上下文 push | SubagentStart + agent TOML | 子代理首步推送角色 skill 正文 + 任务上下文 | **通过**（5472 字符，含真实 skill 与 prd） |
| 派发守卫 | 无 | 缺失/损坏任务 fail-closed 拒绝，research 例外 | **DSH 增强** |
| 等待原语 | 平台原生 wait | `trellis_wait` 事件驱动；失败/中止不误报通过 | **DSH 增强**（超时/取消未覆盖） |
| 会话身份 | 平台 session | `DSH_TRELLIS_CONTEXT_ID=dsh_<session>` | **通过** |
| inline 模式 | `codex.dispatch_mode` | `dsh.dispatch_mode`，选 `*-inline` + DSH 横幅 | **已实现，有边界缺陷**（§3） |
| 开箱可用性 | 需用户级 hooks + 每项目 `/hooks` 审批 + 项目可信 | 安装即生效 | **DSH 明显更好** |
| 命令/设置页/doctor/版本监控 | skills/命令 | headless 无法 E1，源码与单测存在 | 无法验证（非对标核心） |

结论：**“达到 Codex 同等效果”在主链路上成立**；差异集中在模式提示与几个平台约定上，见 §3、§4。

## 3. 问题清单（按严重度）

### P2-1 inline 块缺失时静默退化为 auto 语义（inline 专项）

- 现象：`dsh.dispatch_mode: inline` + 变体 workflow 只有 `planning` 块时，DSH 注入基础块正文，
  **不追加 `<dsh-mode>` 横幅**；同输入下 Codex 仍输出 `<codex-mode>inline: …</codex-mode>`。
  若基础块含 “Sub-agent mode: curate implement.jsonl…”（全局模板即如此），模型会得到与项目声明相反的指引。
- 复现：`/tmp/dsh-verify-20261021-1547/variant/v1-task-variant`、`v3-variant-empty-inline`；
  对照 Codex：`codex_compare.py` 同输入输出含 inline 横幅。
- 根因：`dsh-plugins/dsh-trellis/lib/workflow.js:423-427`（inline 判定与 `blocks.has()` 绑定）、
  `:433-435`（横幅只在 `inline && block !== undefined` 时追加）。
- 影响：使用自定义 workflow 变体或裁剪过模板的项目，inline 声明会被静默丢弃；主模板（含 `*-inline`）不受影响。
- 建议：模式判定与块选择解耦——inline 且状态为 planning/in_progress 时始终追加横幅，块缺失时保留基础块。

### P2-2 inline 只是提示，派发守卫不拦截（需用户决策）

- 现象：inline 下派发 `trellis-agent-implement` 成功，子代理照常收到完整推送（S7）。
- 影响：模型若不遵守横幅，inline 项目仍会产生子代理；与插件已有 fail-closed 守卫的能力不一致。
- 与 Codex 对照：Codex 同样只有提示，故不算落后，但 DSH 有条件做得更严。
- 选项：① 保持提示（最小改动，与 Codex 一致）；② 守卫在 inline 下拒绝 implement/check 派发，仅放行 research，
  并加配置开关作为逃生口。

### P3-3 模式横幅覆盖状态少于 Codex

Codex 每轮所有状态都输出 `<codex-mode>`；DSH 只在 planning/in_progress 且 inline 块存在时输出。
`completed`/`stale`/`task_error`/自定义/`no_task` 下模型拿不到模式声明。建议明确记录为设计差异，或补齐。

### P3-4 非法 `dsh.dispatch_mode` 的回落方向与 Codex 相反

DSH 非法值 → `auto`（`lib/workflow.js:119-137`）；Codex 非法值 → `inline`。DSH 更保守，但与 Codex 不一致；
需确认是否要按 Codex 对齐（可能让错误配置变成“禁止派发”的意外行为）。

### P3-5 spec 工具名跨平台可移植性

DSH 把小写/大写都规范化为小写（`lib/trellis-config.js:225-232`），Codex 只认 `Read|Edit|Write|MultiEdit`。
共享配置若按插件文档写 `tools: [write]`，Codex 侧实测输出
`WARN: unknown spec_injection.tools entries ['write'] — they will never match` 并静默失效。
建议：文档改为“共享配置用 Trellis 原生大写名”，或由插件在写入/生成配置时统一。

### P3-6 bootstrap 频率差异（有意设计，记录）

DSH 每会话一次，Codex 每个无任务轮次重复。长会话中模型可能更早“忘记”Trellis 上下文；
但面包屑仍在，属可接受取舍；插件 README 已声明。

### P3-7 复用块中的 Codex 命令形态

`*-inline`（以及基础 in_progress）块含 `/trellis:finish-work`，DSH 实际是技能 `trellis-finish-work`
与命令 `/trellis-finish`。DSH 横幅用 `/trellis-finish-work` 缓解，但基础块仍有歧义；属模板层。

### P3-8 inline 工作流与 `task.py start` 的 jsonl 门禁冲突

DSH inline 面包屑写明 “skip jsonl curation”，但 `task.py start` 要求 jsonl 非空，实际必须
`--allow-empty-context`（本轮真实遇到）。属 Trellis CLI 与 inline 工作流的契约摩擦，非插件缺陷，
但会打断 inline 第一跳。

### P3-9 `trellis_wait` 成功文案带 “settlement notice delivery is unverified”

DSH 只证明执行结算、不证明通知投递，文案如实但每次成功都出现，可能诱导模型重复核对。
属噪声级；是否降级为结构化字段需产品决策。

## 4. 修复执行方案（待确认，未实施）

| 项 | 方案 | 文件/范围 | 风险 | 回归 |
| --- | --- | --- | --- | --- |
| P2-1 | inline 判定与 `*-inline` 块存在性解耦，块缺失时仍追加横幅 | `lib/workflow.js`（~10 行）+ 单测 | 低；只影响 inline 且块缺失的组合 | state-seq V1/V2/V3 重跑 + `node --test` |
| P2-2 | 二选一：① 文档化为提示；② 守卫识别 inline 并拒绝 implement/check | `lib/dispatch-guard.js`、README | ② 会改变派发语义，需逃生口 | S1/S2/S7 + 守卫单测 |
| P3-3 | 可选：所有状态输出一行模式提示 | `lib/workflow.js` | 每轮多 ~40 字符 | 状态表重跑 |
| P3-4 | 可选：非法值改回落 inline（对齐 Codex）或维持 auto | `lib/workflow.js` | 改变错误配置行为 | 单测 + T15 |
| P3-5 | 文档改为大写工具名，或在 doctor 里提示 | README / `lib/doctor.js` | 无运行时风险 | 文档核对 |
| P3-8 | 在 inline 文档/技能里写明 `--allow-empty-context` | 工作流文档 / 技能（非插件） | 无 | 手工走查 |

建议顺序：先做 P2-1（明确缺陷、改动小、可测），P2-2 由用户选型后再动；P3 系列可合并进同一次文档/行为调整。

## 5. 是否补足 DSH 使用 Trellis 的不足

**是，且是质变**。DSH 原生没有 hook 体系：没有每轮工作流状态、没有子代理首步推送、没有工具边界 spec 注入、
没有会话到任务的绑定。安装 dsh-trellis 后这些全部由插件在宿主事件上补齐，且比 Codex 少三道人工门
（用户级开关、项目 hook 审批、项目可信）。额外的派发守卫与 `trellis_wait` 是 Codex 侧没有的能力。

## 6. 无法验证 / 明确保留

- Web 设置页、`/trellis-*` 命令的真实 UI 行为、冲突检测横幅、版本监控路由（headless 无命令派发与 web host）。
- `trellis_wait` 的超时/取消、rc.8 原生 settlement notice 唤醒时序。
- compaction 后的重投递、spec refresh window 的静默/刷新分支、二进制 spec 截断。
- 真实模型对 inline 横幅的遵循率（mock 只证明“模型收到什么”）。
- 真实 `codex exec` 在临时项目未注入（hooks 未审批）；Codex 基线取自真实 hook 进程输出。

## 7. 变更与回滚

- 本任务只新增 `.trellis/tasks/10-21-dsh-trellis-installed-e2e-inline-audit/`；
  `dsh-plugins/` 与用户 profile 无改动（`git status` 可复核）。
- 临时环境可整体删除：`rm -rf /tmp/trellis-verify-20261021-1547 /tmp/dsh-verify-home-20261021-1547 /tmp/dsh-verify-harness`。

## 8. 修复记录（0.3.10，用户确认后实施）

用户确认：P2/P3 一并处理；**bootstrap 每会话一次属于正常设计，不修改**。

| 项 | 处理 | 文件 |
| --- | --- | --- |
| P2-1 inline 块缺失静默退化 | 模式横幅与块选择解耦：inline 时所有状态都输出 `<dsh-mode>`，块缺失只影响措辞 | `lib/workflow.js` |
| P2-2 inline 无技术门禁 | 采用方案 ②：守卫在 inline 下拒绝 implement/check 派发，research 放行；新增 `dsh.inline_allow_dispatch: true` 逃生口 | `lib/dispatch-guard.js`、`lib/trellis-config.js` |
| P3-3 横幅覆盖状态 | 随 P2-1 一并覆盖全部状态 | `lib/workflow.js` |
| P3-4 非法值回落方向 | 保留回落 `auto`（避免笔误变成禁止派发），在 README 明确记录差异与理由 | `README.md` |
| P3-5 spec 工具名可移植性 | README 明确共享配置用 Trellis 大写名，并说明 Codex 侧静默失效现象 | `README.md` |
| P3-6 bootstrap 频率 | 按用户要求**不修改**，保留每会话一次 | — |
| P3-7 模板命令形态 | 横幅已含 DSH 技能名；README 记录模板层差异 | `README.md` |
| P3-8 inline 启动 jsonl 门禁 | README 给出 `task.py start --allow-empty-context` 指引（Trellis CLI 行为） | `README.md` |
| P3-9 wait 文案 | 保留如实表述，理由写入验证记录 | `docs/validation-0.1.0-local.md` |

验证：

- 单测 `301 tests / 297 pass / 0 fail / 4 skip`（新增 6 个用例）。
- 真实 DSH 会话：变体无/空 `*-inline` 块均输出横幅；`completed` 输出横幅；
  inline 派发被拒、逃生口放行、auto 回归放行。
- 详见 `dsh-plugins/dsh-trellis/docs/validation-0.1.0-local.md`。


## 9. 后续修正（0.1.0，用户追加要求）

### 9.1 项目级 `dsh.dispatch_mode` 自动引导

- 插件启用后，首次解析某个 Trellis 项目状态之前，自动在 `.trellis/config.yaml`
  补 `dsh.dispatch_mode: inline`。
- 只补缺失键；显式 `auto`、注释、顺序、换行一律保留；缺失的 config 不创建；
  非块写法（`dsh: {…}`）不迁移；原子替换 + 目录锁；失败回落 `auto` 并只警告一次。
- 实现：`lib/project-defaults.js`（纯文本合并 + IO 策略）、`lib/session-composer.js`
  （状态解析前引导、复用同一 root）、`lib/project.js` / `lib/workflow.js`（复用 cwd/root）。
- E1：首轮面包屑 826 字符含 `<dsh-mode>`；第二轮文件 sha256 与 mtime 不变；
  显式 `auto` 文件逐字不变且无横幅。

### 9.2 版本重置与版本策略

- `package.json` 0.3.10 → **0.1.0**；`lib/client.js` 的 `PLUGIN_VERSION` 由
  `pnpm run build:client` 重新盖为 `0.1.0`。
- 版本策略写入 `.trellis/spec/platforms/dsh-workflow-behavior.md`：普通修改只递增
  patch（0.1.0 → 0.1.1），次版本/主版本仅用于重大变化。
- `README.md`、`LOCAL_CHANGES.md`、`docs/validation-0.1.0-local.md`、
  `docs/manual-verification.md` 与包版本对齐。

## 10. 推送前自动构建（0.1.0）

- 新增 `scripts/git-hooks/pre-push`：仅当推送提交涉及 `dsh-plugins/dsh-trellis` 时执行
  `pnpm run build:client`；重建后若 `lib/client.js`/`lib/client.js.map` 与 HEAD 不一致，
  中止推送并输出提交命令（推送对象是已提交对象，钩子无法把构建结果塞进已有提交）。
- 新增 `scripts/install-git-hooks.sh`：安装到 `.git/hooks/pre-push`，不替换
  `core.hooksPath`；本机 Sonar 的 `core.hooksPath` pre-push 会链式调用它，两者共存。
- 验证（本地克隆）：普通推送路径 exit 0；版本号改动触发重建且未提交时 exit 1；
  无插件改动的推送直接跳过；`--no-verify` 为显式逃生口。
- 注意：当前仓库 HEAD 仍是 0.3.9 的 bundle，工作树是 0.1.0 构建；在提交重建产物前，
  推送涉及插件的提交会被钩子按预期拦截。

## 11. check 轮（2026-10-21）

按 `trellis-check` 复核本次全部改动，发现并修复 3 个实质问题：

| 问题 | 证据 | 修复 |
| --- | --- | --- |
| “读 → 等锁 → 写”竞态：旧快照可能重复追加 `dsh:` 或覆盖并发编辑 | 锁释放后第二个会话仍用写前快照合并 | 拿到锁后重读当前文件再合并；新增 2 个回归用例 |
| `maxBytes: 0` 时跳过项目配置引导，与“启用插件即引导”不符 | 引导位于预算早退之后 | 引导移到预算判断之前；新增 composer 用例 |
| `dsh:` 段后的列首注释被吞进段内，新键插入破坏注释归属 | 段结束条件把 `^\s*#` 当段内 | 段在列首注释处结束；新增用例 |

| 锁与临时文件位于 `.trellis/`，崩溃残留会污染工作树 | `.trellis/.gitignore` 未覆盖该锁名 | 迁移到 `.trellis/.runtime/`；8 路并发写入只生成一段配置 |

另按仓库 Shell 规范统一两个钩子脚本的 shebang、`set -eu`、`fail()` 与
`ERROR:/WARN:/OK:` 前缀。复核结果：`321 tests / 317 pass / 0 fail / 4 skip`；
client 构建可复现（前后 sha256 一致）；`git diff --check` 通过；无调试输出残留。
