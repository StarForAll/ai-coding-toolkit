# 验证报告：dsh-trellis 0.1.3 全量 parity 复核与缺口验证

- 日期：2026-10-22
- 任务：`.trellis/tasks/10-22-dsh-trellis-full-parity-reverify`
- 环境：dsh 0.2.1-rc.2（全局 npm）+ Trellis CLI 0.7.0-beta.4 + 插件 dsh-trellis **0.1.3**
  （新 profile `trellis-headless`，git 快照安装，与 web profile 同源）
- 临时项目：`/tmp/dsh-parity-reverify/{proj-basic, proj-nogit, proj-plain}`
- 会话取证：`~/.dsh/sessions/--tmp-dsh-parity-reverify-proj-*--/<session>/session.v4.jsonl.zstd`
  （会话清单见附录 A）

## 证据等级说明

- **S1 真实会话**：真实 LLM（deepseek-flash / deepseek-official）headless 会话，事件日志逐条可复核。
- **S2 真实代码执行**：node 直载已安装插件的 lib 模块，对真实临时项目执行。
- **S3 源码比对**：插件 lib 与 Trellis 源码（`~/projects/other/Trellis` @ 0.7.0-beta.4）及本仓库
  `.codex/` 部署契约逐点比对。
- **S4 单元测试**：插件自带 `node --test test/*.test.js`（356 tests / 352 pass / 0 fail / 4 skip——
  skip 均为 alpha 宿主 API 门槛测试，与 10-21 记录一致）。
- 本报告所有"通过"结论均以 S1/S2 为准；S3/S4 仅作补充。README 自述不作为通过依据。

## G1 = R1 修复回归（0.1.3 三项修复的真实会话复测）

| # | 用例 | 结论 | 证据 |
|---|------|------|------|
| G1.1 | inline 模式 + 无任务，`description="trellis-agent-implement (parity test)"`（prompt 无角色名）派发 | **通过（deny）** | S1 `session-a0de6d58`：tool/result 错误 "Trellis inline mode: the main session implements and checks directly, so trellis-agent-implement dispatch is refused."；文案为 0.1.3 新版（明确"leaving inline mode is the user's decision, not yours"），未再教模型自行改配置 |
| G1.2 | 任务 in_progress + `dispatch_mode: auto`，description-only 派发 | **通过（push）** | S1 子会话 `cf41efc5`：首步收到 `kind=dsh-trellis form=subagent-context role=implement`；`was prepared by dsh-trellis` **恰好 1 次**；含 "The complete `trellis-agent-implement` role skill is included immediately below. Do not load ... again, and ignore any 'load the task context yourself' step"；Curated Context 含 prd.md 内联与空 manifest 降级提示 |
| G1.3 | 话题型 description `研究 trellis-agent-implement 插件的行为` | **通过（generic 静默）** | S1 子会话 `9cbe3087`：descriptor label 正确记录为话题文本；无 subagent-context push、无 deny，子代理正常运行 |
| G1.4 | skill 文件缺失时的退化 push | **通过（S2）** | 临时移除 `.dsh/skills/trellis-agent-implement/` 后（已恢复），直载 `subagentContextMessage({roleInstructions:null})`：push 退化为 "Load `.dsh/skills/trellis-agent-implement/SKILL.md` once before acting."；`was prepared` 1 次；无 "Do not load again" 矛盾表述。（S1 路径受阻：headless 每次调用是新会话、指针不延续，派发被守卫拦；降级为 S2 并确认守卫行为本身符合 fail-closed 设计） |

**G1 结论：0.1.2→0.1.3 的三项修复（R1 角色识别、R2 push 文案、R3 守卫表述）在真实会话中全部复测通过，无回归。**

## G2 = R2 主链路复核（C1–C10 重跑 + Codex 三档对照）

| # | 能力 | 结论 | 证据 |
|---|------|------|------|
| C1 | 面包屑状态映射 | **通过** | S1+S2：no_task（`session-947753ba`/`1682559e` 首轮注入）、planning/in_progress/completed（S2 `resolveTrellisState` 实测三态，completed 面包屑文案 "Code committed. Run `/trellis-finish-work`..."）、task_error（S1+S2：故意损坏 task.json → `resolveTrellisState` 返回 task_error，面包屑 "The active task record could not be read..."）、stale（S2：指针指向已归档任务 → resolveActiveTask null → no_task） |
| C1-去重 | 同状态不重复注入 | **通过** | S1 `session-2ce12a29`（4 轮 resume）：breadcrumb 与 bootstrap 各仅 1 条事件（首轮） |
| C1-skip | `no-trellis` 跳过词 | **部分通过，发现 D1** | S1 `session-a0d43e8e`：step1 无任何 dsh-trellis 注入（skip 生效）；但同一 turn 内模型调用 bash 后的 step2 注入了 breadcrumb+bootstrap。见问题清单 D1 |
| C2 | 会话身份隔离 | **通过** | S1 `session-80b35cc0`：真实会话 shell 内 `env` 输出 `DSH_TRELLIS_CONTEXT_ID=dsh_session-80b35cc0-...`（与该会话 id 一致）；S2：两份指针文件（g14-static/g14-other）指向不同任务，`task.py current --json` 各自解析正确、互不串扰；pi 会话与 dsh 会话指针并存（`.trellis/.runtime/sessions/` 三个分片） |
| C3 | trellis_wait | **通过** | S1 `session-80b35cc0`：request/header 工具表含 `trellis_wait`（真实注册）；research 子代理派发后父会话收到 "completed; settlement notice delivery is unverified; inspect its report..."（诚实措辞）；失败映射由 S4 覆盖（wait-tool.test.js 全过） |
| C4 | 子代理 push 内容 | **通过** | 同 G1.2；research 角色见 G4.4 |
| C5 | /trellis 命令面 | **通过** | S2：`registerCommands` 实际注册 `trellis-status`/`trellis-finish`，`registerDoctorCommand` 注册 `trellis-doctor`；`readCurrentTask` 对 proj-basic 实跑返回 "Current task: (none) / Source: none"，对 proj-plain 返回明确错误；doctor 报告实跑输出完整 9 项（root/版本/workflow 8 blocks/dispatch mode/spec 1 项/conflicts unavailable）；非 Trellis 项目 withProject 正确拒绝。注：headless 无交互命令面，命令 handler 由 S2 直调验证 |
| C6 | dispatch_mode 引导 | **通过** | S1 `session-1682559e`（proj-nogit，无 .git 无 dsh 段）：会话后 config.yaml 自动追加 `dsh: dispatch_mode: inline`（带注释块）；显式值不被覆盖（S2 `mergeDshDispatchMode` reason:"present"）；config 缺失不创建（S2 reason:"no-config"）；flow-style `dsh: {...}` 不改写（源码 reason:"dsh-not-block"） |
| C7 | spec 注入 | **通过** | S1 `session-6ae02eab`：write 触碰 `src/spec-test.js` → tool result isError，deny reason 携带 `<spec-context file="src/spec-test.js" spec=".trellis/spec/mylayer/index.md" sha256=...>` 完整 spec 正文 → 重试放行；同会话第二次 write 不再 deny（去重）；持久化分片 `.trellis/.runtime/spec-inject/session-6ae02eab....json` 记录 mode:full + sha256；read ticket：`session-6bca475c` read 触碰后下一请求收到 `form=spec-context` 消息（`tools: [Read, Edit, Write, MultiEdit]` 配置生效） |
| C8 | bootstrap 一次性 | **通过** | S1 `session-6ae02eab`（resume 4 轮）：bootstrap 事件仅首轮 1 条；子代理会话（`cf41efc5`/`ad8e3c7a`）永不注入（事件日志核对） |
| C9 | 非 Trellis 项目零干扰 | **通过** | S1 `session-068ef22b`（proj-plain）：0 条 dsh-trellis 消息 |
| C10 | init 双向一致 + Trellis 契约 | **通过** | S3：`trellis init --dsh` 产物 `.dsh/skills/trellis-agent-{implement,check,research}`、`trellis-start/continue/finish-work`、`DSH.md` 与插件 `ROLE_SKILLS` 路径逐一对齐；S1+S2：`task.py current --json` exit 0 带 payload / exit 1 无任务；S3：Trellis 源码 `active_task.py` L532 确认 `DSH_TRELLIS_CONTEXT_ID` 优先于 `TRELLIS_CONTEXT_ID`，与插件 session-env 注入契约一致 |

### Codex 逐点对照（三档）

| 链路 | Codex 实际接线（本仓库 .codex/ + Trellis 源码） | dsh-trellis 0.1.3 | 档位 |
|---|---|---|---|
| workflow-state | `UserPromptSubmit` 每轮注入（`inject-workflow-state.py`） | 每 `agent/pre-step` 注入，状态变化去重 | **有意差异（README 已声明）**：DSH 每会话一次 vs Codex 每轮；频率差异已文档化。新发现"step 语义"偏差见 D1 |
| no-task bootstrap | 每轮 UserPromptSubmit 附 `<trellis-bootstrap>`（`CODEX_NO_TASK_BOOTSTRAP_NOTICE`） | 每会话一次 + compaction 重注入 | **有意差异（已声明）** |
| spec 注入 | `PreToolUse` matcher "Edit\|Write" deny-once（`permissionDecision: deny`）；Claude 侧 PostToolUse "Read\|..." | `tools/pre-execute` deny-once + post-execute ticket；默认 tools `[edit, write]`，可配 Read（实测 ticket） | **对齐**。差异：read 不能先阻断（DSH 事件形状决定，README 已声明） |
| subagent context | `SubagentStart` matcher `^(trellis-implement\|trellis-check\|trellis-research)$`，非 Trellis 子代理 silent return（源码 L915-965：subagent_type 不匹配直接 return） | 子代理首步 push；角色识别 prompt → description/label；generic 静默（G1.3 实测） | **对齐**。DSH 增强：description 识别（Codex 由 agent type 名直接匹配） |
| research 无任务 | Codex hook：task_dir 取不到 → return（静默） | 允许派发，下一请求注入 `dispatch-guard` notice 提示确认输出位置（S1 `session-c3500f42` seq29 实测） | **有意差异（增强，README 已声明）** |
| 无任务 implement/check | Codex：hook 静默 return，子代理无上下文运行 | fail-closed deny（G1.1 + `session-2d7d7226` 实测 "no readable active task"） | **有意差异（增强，README 已声明"提示性闸门"）** |
| 平台标识 | `platform == "codex"`，读 `codex.dispatch_mode` | 读 `dsh.dispatch_mode`，绝不读 codex 键（源码注释明确） | **对齐**（DSH 拥有独立配置键） |

## G3 = R3 补足 DSH 原生不足（三段式结论）

**1) 无插件缺失清单**（S1 对照：`headless` profile 在 proj-basic，`session-f3807c04`/`session-392c75e8`）：
- 模型确认"没有 Trellis workflow state 注入块，没有 trellis-bootstrap"（0 条 dsh-trellis 消息）
- write 触碰受 spec paths 覆盖的文件**无任何 deny/注入**（一次成功，0 工具错误）
- 无 DSH_TRELLIS_CONTEXT_ID 会话身份、无 trellis_wait、无 /trellis-* 命令、无派发守卫、无 dispatch_mode 引导

**2) 插件补足情况**：上述全部补齐（对应 G1/G2 各项实测通过）。

**3) 残余不足**：
- D1（skip 词的 step 语义，见下）
- read 不能先阻断（上游宿主事件形状限制，README 已声明，无可改进空间——DSH 无 read 前置 hook）
- bootstrap 频率（每会话一次 vs Codex 每轮）为有意设计，README 已声明
- research push 依赖父会话指针存在：父会话从未 start 任务时 push 静默省略（S1 `session-c3500f42` 实测：父指针缺失 → 子代理无 push；补指针后 S1 `session-80b35cc0`→子代理 `ad8e3c7a` push 完整）。守卫对 research 放行但不强制任务，push 静默与 notice 之间的落差见观察项 O2

**超出 parity 的增强（实测可用）**：/trellis-doctor（S2 全项输出）、派发守卫 fail-closed（S1）、
冲突检测诚实降级（S2：无 loader → `unavailable` 不伪造"无冲突"；模拟双插件 → `checked`+冲突列表）、
dispatch_mode 自动引导（S1）、read ticket（S1）。

## G4 = R4 缺漏扫描

| # | 角度 | 结论 | 证据 |
|---|------|------|------|
| G4.1 | 多会话并发隔离 | **通过** | S2：两份 session 指针分片并存且指向不同任务、`task.py current --json` 各自正确；S1：pi 会话与 2 个 dsh 会话指针并存互不串扰 |
| G4.2 | 异常路径 fail-closed | **通过** | S2：task.json 损坏 → task_error 面包屑（不静默吞掉）；workflow.md 损坏/缺失 → fallback 面包屑（"no matching [workflow-state] block" / "missing or unreadable"）；config.yaml 损坏时 merge 不改写原文件；写失败 → `write-failed` + 进程内负缓存（第二次调用零 IO，实测）；config 缺失 → `no-config` 不创建 |
| G4.3 | 长会话/resume | **通过** | S1：`--session-id` resume 4 轮，bootstrap 仍只 1 条（projection 状态跨轮保持）；compaction 重注入行为由 projection 设计（surface 可见性判定）+ S4 覆盖——headless 单轮会话无法安全触发真实 compaction，此子项证据等级为 S3+S4 |
| G4.4 | research 链路 | **通过（附 O2）** | S1 `session-80b35cc0`→子代理 `ad8e3c7a`：首步 push `form=subagent-context role=research`，含 `## Project Spec Directory Structure`（backend/frontend/guides/mylayer 树）+ Search Tips + Active task 行；无任务派发 → dispatch-guard notice（S1 `session-c3500f42`） |
| G4.5 | 冲突检测/版本监控 | **部分实测** | S2：冲突检测 headless 降级 `unavailable` + 模拟双插件检出冲突（不伪造）；版本监控/设置页/桌面通知为 web UI 专属，headless 无法真实验证，证据等级 S3（源码审查：upstream.js/conflicts.js 路由）+ S4 |
| G4.6 | workflow.md 派发协议一致性 | **通过** | S3：本仓库 workflow.md 的 DSH 派发协议（trellis_wait 优先 / 无则 run_in_background:false）与插件实际能力一致：trellis_wait 真实注册（S1），dsh rc.2 subagent 默认 continuable 后台模式（S1 派发返回 child id + settlement 通知路径实测） |
| G4.7 | Trellis 0.7.0-beta.4 契约 | **通过** | S2：`task.py current --json` 双态退出码；S3：active_task.py 源码 L532 确认 DSH_TRELLIS_CONTEXT_ID 最高优先级（高于 TRELLIS_CONTEXT_ID，且 DSH_SHELL 哨兵防外层继承） |

## 问题清单（等待用户逐条确认，未做任何修复）

### D1 skip 词只在触发它的那一步生效（turn 内后续 step 仍注入）【缺陷（文档与行为不符）】
- **现象**（S1 `session-a0d43e8e`）：prompt 含 `no-trellis` 的会话，step1 无任何注入；模型调用
  bash 后进入 step2，breadcrumb+bootstrap 在 step2 注入（事件 seq26/27）。
- **根因**（S3）：`agent/pre-step` 的 `messages` 是 inbox claim 的**新消息批次**
  （dsh-agent-loop `Inbox.claim`），step2 的批次只含工具结果，不再含带 `no-trellis` 的用户
  prompt，`hasSkipKeyword` 自然不命中。Codex 侧按"轮"（UserPromptSubmit）判定，无此问题。
- **影响面**：想用 skip 词跳过某轮注入的用户，在该轮模型有工具调用的多 step 场景下仍会被
  注入。README 说"可跳过当轮"，实际是"跳过触发的那一步"。
- **可选方案**：
  - a) **推荐**：让 composer 在 turn 维度记住 skip 判定（同一 turn 内后续 step 延续 skip），
    语义对齐 Codex 的"每轮"并使 README 文案成立；
  - b) 改 README/帮助文案为"跳过当前 step"，不改行为（成本最低但体验不变）。

### O2 research push 依赖父会话指针，静默省略【设计权衡（建议文档化或加提示）】
- **现象**（S1 `session-c3500f42`）：父会话从未 `task.py start` 时派发 research，子代理无
  push（守卫只对 implement/check 拦，research 放行且 notice 只提示输出位置）；补上父指针后
  同样派发 push 完整（`session-80b35cc0`→`ad8e3c7a`）。
- **定性**：与 Codex 行为一致（Codex task_dir 取不到也 return），不算 parity 缺陷；但 DSH
  headless 每次调用是新会话、指针天然不延续，此场景在 DSH 上更常见。
- **可选方案**：a) research 派发无指针时 notice 里补一句"子代理未获得项目结构上下文（无活动任务）"；
  b) 保持现状，README 记录该边界。

### O3 headless 每次调用即新会话【上游限制，非插件问题】
- G1.2 的守卫拦下发现在 headless 无状态使用模式下，"父会话指针"几乎总是缺失，派发守卫会
  拒绝 implement/check 直到用户在同一会话内 start 任务。这是 DSH headless 形态 + fail-closed
  守卫共同作用，交互式（TUI/web）会话不受影响。仅记录，不建议改插件。

### 已核实非问题（期间排查过）
- `/trellis-doctor` "Plugin: dsh-trellis <函数源码>"——为 S2 直调漏 await `version()` 所致，
  真实路径 `registerDoctorCommand` 已 await（S2 复测输出 `0.1.3` 正常）。
- 守卫拒绝文案（G1.1）为 0.1.3 新版，不再教模型绕过（P1-1 已闭环）。

## 总体结论

1. **Codex parity**：三项主链路（workflow-state、spec 注入、子代理 context push）在 0.1.3 上
   全部实测对齐；与 Codex 的每处差异都能归入"有意差异且 README 已声明"或"DSH 增强"档。
   唯一新发现的行为偏差是 D1（skip 词的 step 语义）。
2. **补足 DSH 不足**：无插件时缺失的 7 类能力全部补齐并实测可用；残余不足仅限宿主事件形状
   决定的 read 时序与有意设计的 bootstrap 频率。
3. **0.1.3 修复回归**：三项修复全部通过真实会话复测，无回归。
4. 插件测试套件 356 项 0 失败，与本轮实测互相印证。

## 附录 A：会话取证清单

| session | 用途 |
|---|---|
| session-947753ba | 首次冒烟（面包屑+bootstrap 首注入） |
| session-a0de6d58 | G1.1 inline deny |
| session-1953fa15 + cf41efc5 | G1.2 push（父+子） |
| 9cbe3087 | G1.3 话题型 generic |
| session-2d7d7226 | G1.4 派发被守卫拦（headless 无指针） |
| session-2ce12a29 | C1 去重 / C8 / 多轮 resume |
| session-6ae02eab | C7 deny-once + C8 resume 4 轮 |
| session-6bca475c | C7 read ticket |
| session-58578f8f | C5 命令面（headless 限制确认） |
| session-c3500f42 + 2b6baa25 | G4.4 research 无指针（父+子） |
| session-80b35cc0 + ad8e3c7a | G4.4 research push + C3 trellis_wait + C2 env |
| session-f3807c04 / session-392c75e8 | G3 无插件对照 |
| session-a0d43e8e | C1-skip（D1 证据） |
| session-068ef22b（proj-plain） | C9 |
| session-1682559e（proj-nogit） | C6 dispatch_mode 引导 |

---

# 修复审查（0.1.4，commit 29965e0）——独立真实性复核

- 审查日期：2026-10-22（修复由其他任务执行，本审查独立复测）
- 审查方式：**真实 dsh 会话复测为主**（trellis-headless profile 升级安装 0.1.4 后跑真实 LLM 会话，
  事件日志取证），辅以宿主源码核实（dsh-agent-loop turn 单调性、WeakMap 生命周期）。
  不依赖修复方自带的端到端记录（该记录用了独立 DSH_HOME + 源码直挂 profile；本审查用
  pnpm 安装的同源 git 快照，路径独立）。
- 审查环境：源码/安装版本均为 0.1.4（`profile node_modules/dsh-trellis` 与仓库 diff 一致，
  `PLUGIN_VERSION="0.1.4"`，client bundle 测试通过）。

## D1（skip 词按 turn 生效）——**真实修复，已验证**

| 用例 | 场景 | 结论 | 证据 |
|---|---|---|---|
| V1 | `no-trellis` 轮内 read 工具调用（2 steps） | **通过**：breadcrumb 0、bootstrap 0（0.1.3 时 step2 注入）；对照组同 prompt 无词 → 各 1 条 | S1 `session-1be4dc71`（skip）/ `session-6945580d` turn1（对照） |
| V2 | 同会话 turn2 无 skip 词、状态未变 | **通过**：无注入（状态去重，非 skip 残留——由 V3/V6 区分证明） | S1 `session-6945580d` turn2 |
| V3 | turn3 无词、状态 no_task→in_progress | **通过**：注入 in_progress 面包屑（seq56），skip 记忆未过度抑制 | S1 `session-6945580d` turn3 |
| V4 | turn4 `no-trellis` + 工具调用 | **通过**：整轮（含 step2）零注入 | S1 `session-6945580d` turn4 |
| V5 | turn5 无词、状态未变 | 无注入（去重语义，与 0.1.3 相同设计） | S1 `session-6945580d` turn5 |
| V6 | turn6 无词、状态 → planning | **通过**：注入 planning 面包屑（seq96）→ **skip 记忆未跨 turn 泄漏** | S1 `session-6945580d` turn6 |
| 退化 | 宿主不提供 `turn` | `Number.isInteger(turn)` 双闸门：不记忆、退化为原按 step 行为（单测 "without a turn position the skip stays step-scoped"） | S4 |

边界核实（S3，宿主源码）：
- turn 单调性：`dsh-agent-loop` `turn = phase.turn + 1`，per-agent 单调递增，无回退 → WeakMap
  只存"最新 skip turn + 相等判定"不会误命中；
- 生命周期：WeakMap 键为 agent（每会话一个），resume/fork 产生新 agent 对象，旧记忆可回收，
  无跨会话泄漏；
- skip 记忆 return [] 只吞 breadcrumb/bootstrap 家族，不影响项目引导（ensureProjectDefaults 在
  判定前执行）与 spec-inject（独立模块 + 独立事件），V1 中 spec-context read ticket 照常送达。

## O2（research push 依赖父指针）——**文档化路线已落实，行为与文档一致**

- `subagent-context.js` 0.1.3→0.1.4 **未改动**（git diff 为空）——修复选择的是更正文档而非改行为，与用户确认的路线一致。
- README 新表述三点全部实测吻合（S1）：
  1. 任务路径 `Active task:` 前奏优先（`session-4b0cc4e8`：无父指针、带前奏派发 → push `role=research task=.trellis/tasks/10-22-sess-b-test`）；
  2. 前奏与指针都缺失 → 不 push（`session-9938c970`：子代理 `0ab70357` push 次数 0，回复"否"）；
  3. research 无任务派发 → 父会话收到 `dispatch-guard` notice（seq37，输出位置提醒）。
- 原 README 把优先级写反（"父会话指针缺失时回退到 Active task"）；实际代码一直是 prompt 优先。文档更正属实。

## 新问题排查——**未发现**

| 回归面 | 检查 | 结论 |
|---|---|---|
| 正常注入（V7a） | 新会话无 skip 词 | breadcrumb 1 + bootstrap 1（`session-5b3ad2f3`）✓ |
| spec 注入（V7b） | write 触碰 paths 覆盖文件 | deny-once 后放行（`session-3a5c2f52`：write×2、deny×1）✓ |
| 非 Trellis 项目（V7c） | proj-plain | 0 条 dsh-trellis 消息（`session-4d8ac8db`）✓ |
| 子代理 push / 守卫 | O2 用例附带 | Active-task 前缀派发 push 正常；无任务 research notice 正常 ✓ |
| 测试套件 | `node --test test/*.test.js` | 362 tests / 358 pass / 0 fail / 4 skip（skip 仍为 alpha 宿主门槛项）✓ |
| 版本契约四件套 | package.json / README / LOCAL_CHANGES / docs/validation-0.1.4-local.md | 全部 0.1.4 且同步；client bundle 重建（PLUGIN_VERSION=0.1.4，bundle 测试过）✓ |
| 设置页文案 | `src/client/locales.js` skipKeywordHint | "跳过本轮面包屑"在修复后与行为一致（修复让代码追上了文案，文案本身无需改）✓ |

## 审查结论

1. **D1 已真实修复**：turn 级 skip 在真实会话（含工具调用的多 step 轮、跨 turn 状态变化、
   退化路径）全部按 README/设置页新文案行为执行；未发现跨 turn 泄漏或过度抑制。
2. **O2 按确认路线落实**：行为未改（与 Codex 一致），文档错误（优先级写反）已更正，
   三点新表述实测吻合。
3. **未发现新问题**：主链路（正常注入、spec deny-once、零干扰、子代理 push、守卫）回归
   全部通过；turn 单调性与 WeakMap 生命周期的宿主源码核实无隐患。
4. 版本与验证记录（validation-0.1.4-local.md）与实际改动一致，无声称与实际不符项
   （其引用的 `skipKeywordHint` 文案是"原本就承诺按轮"的佐证，非待改项，已核实）。
