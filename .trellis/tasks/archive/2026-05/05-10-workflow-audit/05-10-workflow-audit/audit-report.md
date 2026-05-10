# workflow-audit: 新项目开发工作流

## Audit Target and Boundary
- Workflow Root: `docs/workflows/新项目开发工作流/`
- Resolved Workflow Root Rule: always `docs/workflows/新项目开发工作流/`
- Audit Scope: `task-based runtime`
- Current CLI: `codex`
- Candidate Issues:
  - “原生 Trellis 比较快，嵌入 workflow 之后比较慢”的历史问题是否仍存在
- Generated Target Project Root: `/tmp/workflow-audit-perf-eGidHm`
- Comparison Model: `source repo` vs `generated target project` baseline (`trellis init`) vs `generated target project` workflow-installed state (`install-workflow.py`) vs `runtime command output`

## Evidence-Gathering Actions Executed in This Round
- 读取 `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 并确认 `COMPATIBLE_TRELLIS_VERSION = 0.5.10` — Layer: `source repo`
- 执行 `trellis -v` 并确认本机版本为 `0.5.10` — Layer: `runtime command output`
- 阅读 `工作流嵌入执行规范.md`、`CLI原生适配边界矩阵.md`、`装后隐藏目录与托管边界核对清单.md`、三平台 README、`install-workflow.py`、`detect-embed-state.py`、`upgrade-compat.py` — Layer: `source repo`
- 复核历史性能负担结论：`.trellis/tasks/archive/2026-04/04-02-analyze-new-project-workflow-init-overhead/prd.md` 明确记录过“进入太慢、上下文太厚”风险，其中重点点名旧版 OpenCode `instructions` 挂载过厚 — Layer: `source repo`
- 在 `/tmp/workflow-audit-perf-eGidHm` 创建 fresh target project，并执行 `trellis init --claude --opencode --codex -u audit-dev -y` — Layer: `generated target project` — Stage: `baseline after trellis init`
- 记录 baseline 落盘事实：
  - `.agents/skills/` 已有 9 个 Trellis baseline skills
  - `.claude/commands/trellis/` 与 `.opencode/commands/trellis/` 各有 2 个 baseline commands
  - `.codex/skills/` 不存在
  - `AGENTS.md` 中不存在 `workflow-nl-routing` 区段
  - `.trellis/workflow.md` 中不存在 `workflow-projectization-patch`
  — Layer: `generated target project` — Stage: `baseline after trellis init`
- 执行 `detect-embed-state.py --project-root /tmp/workflow-audit-perf-eGidHm --json`，返回 `INITIAL_BASELINE_READY`，`traces=[]`，`blockers=[]` — Layer: `runtime command output`
- 执行 `install-workflow.py --project-root /tmp/workflow-audit-perf-eGidHm --dry-run`，确认将新增 9 个阶段入口、2 个 Codex baseline skill patch、1 个增强版 research agent、8 个 helper scripts、2 个 execution cards、`workflow.md` patch、`AGENTS.md` NL routing 与 install record — Layer: `runtime command output`
- 通过非 Codex 执行器完成 formal install：
  - `install-workflow.py --project-root /tmp/workflow-audit-perf-eGidHm` with `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` 返回 `0`
  - `upgrade-compat.py --project-root /tmp/workflow-audit-perf-eGidHm --check` 返回 `0`
  — Layer: `runtime command output`
- 记录 workflow-installed state：
  - `.trellis/workflow-installed.json` 存在
  - `.trellis/workflow-embed-attempt.json` 不存在
  - `AGENTS.md` 已出现 `workflow-nl-routing`
  - `.trellis/workflow.md` 已出现 `workflow-projectization-patch`
  - `.trellis/scripts/workflow/` 中共有 8 个 helper scripts
  - `.agents/skills/` 中新增 9 个 workflow 阶段 skills
  — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- 直接测量 SessionStart 注入长度：
  - fresh baseline：Codex `26576` chars，Claude `26603` chars
  - formal install 后：Codex `26607` chars，Claude `26634` chars
  - 增量分别仅为 `+31` chars / `+31` chars
  — Layer: `runtime command output`
- 复核当前 OpenCode README：已明确要求 `instructions` “只挂主入口与必要补充，不默认全量挂载所有阶段文档”；旧版“全量挂多份长文档”的风险不再是当前推荐合同 — Layer: `source repo`
- 读取历史慢项目 `/ops/projects/work/file_flow` 的现场状态：
  - `.trellis/.version = 0.4.0`
  - `.trellis/workflow-installed.json` 记录 `workflow_version = 0.1.24`
  - 仍采用 legacy carrier：`start` / `record-session` patched baseline、custom agent overlay、`.codex/agents/{research,implement,check}.toml` 旧命名、`.claude/commands/trellis/start.md`
  - `.agents/skills/` 共 21 个 skills，`.codex/skills/` 仍有 1 个目录
  — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`
- 在 `/ops/projects/work/file_flow` 直接测量当前落盘 hooks 的 SessionStart 注入长度：
  - Codex `7106` chars
  - Claude `7106` chars
  - `guidelines` 段分别约 `5229` chars，且内容为 `backend/frontend/guides` 三个 `index.md`，不是整套 `spec/**/*.md`
  — Layer: `runtime command output`
- 在 `/ops/projects/work/file_flow` 直接测量当前执行链耗时：
  - `python3 .trellis/scripts/get_context.py` 均值约 `45.4ms`
  - `python3 .trellis/scripts/get_context.py --mode packages --json` 均值约 `37.1ms`
  - `python3 .codex/hooks/session-start.py` 均值约 `66.4ms`
  - `python3 .claude/hooks/session-start.py` 均值约 `69.0ms`
  - `python3 .claude/hooks/statusline.py` 均值约 `22.8ms`
  - `python3 .claude/hooks/inject-subagent-context.py`（PreToolUse: Task/Agent）均值约 `19-20ms`
  — Layer: `runtime command output`
- 在 `/ops/projects/work/file_flow` 复盘 OpenCode 首消息执行链：
  - `chat.message` 首轮注入总耗时约 `88.9ms`
  - 同步步骤包含：
    1. `await hasPersistedInjectedContext(client, sessionID)` → `client.session.messages(...)`
    2. `loadTrellisConfig()` → `execFileSync(get_context.py --mode packages --json)`
    3. `ctx.runScript(get_context.py)`
    4. 读取 `.trellis/workflow.md`
    5. 遍历 `.trellis/spec/*/index.md`
    6. 拼接 injected context 回写到 `output.parts`
  - 其中 fake client 下 `client.session.messages` 近乎 0ms，但真实 OpenCode runtime 下这一步仍是同步 await 边界
  — Layer: `runtime command output`
- 复核 OpenCode 插件加载边界：
  - `.opencode/plugins/session-start.js` 模块导入均值约 `1.4ms`
  - `.opencode/package.json` 未声明 `"type": "module"`，Node 会触发 `MODULE_TYPELESS_PACKAGE_JSON` 警告并重新按 ESM 解析
  - 说明慢点不在模块导入本身，而在首消息同步执行链
  — Layer: `runtime command output`
- 用同一离线基准对比 legacy project 与 current workflow 的 OpenCode 首消息链：
  - `file_flow` (`0.4.0 + 0.1.24`) `chat.message` 均值约 `87.9ms`
  - fresh current workflow target (`0.5.10 + 0.1.27`) `chat.message` 均值约 `88.0ms`
  - 在同一 fake client 条件下，两者几乎相同
  — Layer: `runtime command output`
- 对比 legacy project 与 current workflow 的 Codex / Claude 路径：
  - legacy `file_flow`
    - Claude SessionStart total `7106`
    - Codex SessionStart total `7106`
    - Codex per-turn breadcrumb hook `~8.4ms`
  - current fresh workflow target
    - Claude SessionStart total `26634`
    - Codex SessionStart total `26607`
    - Codex per-turn breadcrumb hook `~34.7ms`
  - 说明当前版本在 Codex / Claude 路径上引入了明显更重的默认上下文与 per-turn hook 成本
  — Layer: `runtime command output`
- 对比当前 workflow 的 carrier wiring：
  - current `.opencode/plugins/session-start.js` 仍采用：
    1. `await hasPersistedInjectedContext(...)`
    2. `buildSessionContext(...)`
    3. `loadTrellisConfig()` → `get_context.py --mode packages --json`
    4. `ctx.runScript(get_context.py)`
    5. 读取 `workflow.md`
    6. 读取 / 构造 spec index 内容
  - current `.codex/hooks.json` 已不再用 SessionStart，改为 `UserPromptSubmit -> inject-workflow-state.py`
  - current `.claude/settings.json` 同时保留 `SessionStart` 与 `UserPromptSubmit`
  — Layer: `source repo`
- 读取 `/ops/projects/work/file_flow/CLAUDE.md`，确认该项目还额外挂载约 `9.2k` chars 的 Claude 项目说明；这属于项目侧额外说明面，不属于 workflow SessionStart hook 本体 — Layer: `generated target project` — Stage: `workflow-installed state after install-workflow.py`

## Confirmed Issues

### [P1] “嵌入 workflow 后明显更慢”作为当前版本的默认 workflow 性能回归，不成立
- Conclusion: 在 `Trellis 0.5.10 + workflow 0.1.27` 当前合同下，没有证据表明 formal install 会给 Codex/Claude 默认 SessionStart 注入带来显著增量；历史“变慢”不再是当前 workflow 的默认回归问题。
- Evidence Source:
  - Layer: `runtime command output`
  - Stage: `n/a`
  - baseline SessionStart size:
    - Codex `26576`
    - Claude `26603`
  - workflow-installed SessionStart size:
    - Codex `26607`
    - Claude `26634`
  - 增量仅 `+31` / `+31`
  - Layer: `source repo`
  - Stage: `n/a`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md` 当前已明确禁止默认全量挂载所有阶段文档
- Validation Action:
  - 在 fresh `trellis init` baseline 与 formal install 后分别直接执行 `.codex/hooks/session-start.py` 与 `.claude/hooks/session-start.py`
  - 解析 `hookSpecificOutput.additionalContext` 长度
  - 对照当前 README 合同，确认旧版 OpenCode 厚注入建议已被移除
- Impact Scope:
  - 对“当前 workflow 默认安装就会导致明显变慢”的判断
  - Codex / Claude 的默认首轮上下文成本归因
- Suggested Fix Direction:
  - 不要把当前体感慢直接归因给 workflow 增量
  - 若要继续优化，应先从 Trellis baseline SessionStart 注入本身入手

### [P1] 当前仍然存在的主要慢点在 Trellis baseline SessionStart 注入，而不是 workflow 安装增量
- Conclusion: 当前默认启动上下文的主要成本已经在 fresh `trellis init` baseline 中存在；workflow 安装只是在这个重 baseline 上叠加很小的启动增量。
- Evidence Source:
  - Layer: `runtime command output`
  - Stage: `baseline after trellis init`
  - fresh baseline SessionStart size 约 `26.6k` chars（Codex / Claude）
  - Layer: `source repo`
  - Stage: `n/a`
  - `.codex/hooks/session-start.py`、`.claude/hooks/session-start.py` 都会注入：
    - `get_context.py` 的 current-state 输出
    - `workflow.md` 的 Phase Index / TOC
    - `guides/index.md` 全文
    - spec index 路径列表
    - task-status / ready 指引
- Validation Action:
  - 阅读两套 SessionStart hook 实现
  - 在 baseline 状态执行 hook，并统计 `additionalContext` 字符数
  - 对照 install 后再测一次，分离 baseline 与 workflow 增量
- Impact Scope:
  - Codex / Claude 首轮会话启动
  - 用户对“原生 Trellis 就已经偏重”的体感
- Suggested Fix Direction:
  - 如果要降首轮开销，优先精简 baseline SessionStart 注入内容，而不是优先删 workflow 阶段资产

### [P2] OpenCode 的历史慢路径仍可条件性复现，但它已不属于当前推荐合同
- Conclusion: 如果目标项目仍沿用旧的 `opencode.json.instructions` 厚挂载方式，OpenCode 侧仍可能出现“嵌入后更慢”；但这是旧配置/手工配置漂移问题，不是当前 workflow 文档的默认推荐行为。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - 历史证据：`.trellis/tasks/archive/2026-04/04-02-analyze-new-project-workflow-init-overhead/prd.md` 明确记录旧版 OpenCode 示例存在“默认上下文偏重风险”
  - 当前证据：`docs/workflows/新项目开发工作流/commands/opencode/README.md` 已明确写出
    - `instructions` 只挂主入口与必要补充
    - 不默认全量挂载 `工作流总纲.md` 与全部阶段命令
- Validation Action:
  - 对比历史任务结论与当前 README
  - 核对当前 source repo 合同已修改风险口径
- Impact Scope:
  - OpenCode 目标项目的手工配置面
  - 老项目未更新 `opencode.json.instructions` 时的体感风险
- Suggested Fix Direction:
  - 排查慢项目是否仍保留旧版 `opencode.json.instructions`
  - 将其收敛到当前 README 推荐的最小挂载模型

### [P1] `file_flow` 当前最明显的执行流程缺点在 OpenCode 首消息同步链过长
- Conclusion: 这个项目真正暴露出的慢点不是“文件多”，而是 OpenCode 把 Trellis 上下文注入挂在首条 `chat.message` 的同步链上，而且链内串了两次 Python 子进程与一次 session-history 去重查询。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `.opencode/plugins/session-start.js`
  - `.opencode/lib/trellis-context.js`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - `chat.message` 首轮注入总耗时约 `88.9ms`
  - `get_context.py --mode packages --json` 约 `37.1ms`
  - `get_context.py` 约 `45.4ms`
  - OpenCode 首消息总耗时与这两次 Python 调用之和高度吻合
- Validation Action:
  - 阅读 OpenCode `session-start.js` 与 `trellis-context.js`
  - 通过 Node 直接调用插件 `server(...).chat.message(...)`
  - 分离模块导入、dedupe 查询、Python 子进程、context 拼接的时序
- Impact Scope:
  - OpenCode 首轮用户消息
  - 每个新 session / compact 后重新注入时的首条消息体验
- Suggested Fix Direction:
  - 把 `loadTrellisConfig()` 与 `ctx.runScript(get_context.py)` 合并或缓存，避免首消息内双 Python 子进程
  - 若 session history dedupe 无法避免，至少不要把其他重计算也放在同一同步链里

### [P1] 当前 workflow 仍然保留了 `file_flow` 的 OpenCode 同类慢路径
- Conclusion: `file_flow` 暴露出的 OpenCode 首消息同步慢链，在当前 workflow 里仍然存在；这不是历史遗留项目独有问题，而是当前 OpenCode adapter 的现行执行模型。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - current `.opencode/plugins/session-start.js`
  - current `.opencode/lib/session-utils.js`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - legacy `chat.message` mean `87.9ms`
  - current `chat.message` mean `88.0ms`
  - 两者都包含同类同步链：session history dedupe + 双 Python 子进程 + workflow/spec 拼接
- Validation Action:
  - 在 legacy project 与 fresh current workflow target 上，用同一 fake client 与同一 Node benchmark 调用 `chat.message`
  - 对照 source plugin 代码路径，确认执行链结构一致
- Impact Scope:
  - 当前 workflow 的 OpenCode fresh install
  - 所有基于 `.opencode/plugins/session-start.js` 的首轮消息体验
- Suggested Fix Direction:
  - 把当前 OpenCode adapter 视为真实性能问题，而不是旧项目偶发现象
  - 优先优化其同步链，而不是只修文档口径

### [P1] 当前 workflow 在 Codex / Claude 路径上没有继承 `file_flow` 的同类慢点，但引入了另一类更重的默认上下文成本
- Conclusion: `file_flow` 的主慢点是 OpenCode 首消息同步链；当前 workflow 在 Codex / Claude 上的主要问题不是这一类，而是 SessionStart / per-turn 注入内容显著增重。
- Evidence Source:
  - Layer: `runtime command output`
  - Stage: `n/a`
  - legacy:
    - Claude SessionStart `7106`
    - Codex SessionStart `7106`
    - Codex per-turn `~8.4ms`
  - current:
    - Claude SessionStart `26634`
    - Codex SessionStart `26607`
    - Codex per-turn `~34.7ms`
  - Layer: `source repo`
  - Stage: `n/a`
  - current `.codex/hooks.json` 改为 `UserPromptSubmit`
  - current `.claude/settings.json` 同时挂 `SessionStart` + `UserPromptSubmit`
- Validation Action:
  - 在 legacy 与 current target 上分别测 SessionStart 注入长度和 Codex per-turn hook
  - 读取 current hooks wiring 进行对照
- Impact Scope:
  - 当前 fresh workflow 的 Codex / Claude 使用体验
  - 与 `file_flow` 不同类型的性能负担
- Suggested Fix Direction:
  - 对 Codex / Claude 路径单独建账，不要混到 OpenCode 首消息慢链里
  - 若目标是整体降延迟，OpenCode 与 Codex/Claude 需要分别优化

### [P2] `file_flow` 的 Claude / Codex 路径当前不是主要慢点，但流程上仍有次级缺点
- Conclusion: Claude / Codex 当前流程没有 OpenCode 那么重，但它们仍把 SessionStart 设计成同步阻塞流程，只是当前项目上的代价约在 `66-69ms` 量级。
- Evidence Source:
  - Layer: `source repo`
  - Stage: `n/a`
  - `.codex/hooks.json` 仅配置 `SessionStart`
  - `.claude/settings.json` 配置 `SessionStart` + `PreToolUse` + `SubagentStop`
  - Layer: `runtime command output`
  - Stage: `n/a`
  - Codex `session-start.py` 均值约 `66.4ms`
  - Claude `session-start.py` 均值约 `69.0ms`
  - Claude `inject-subagent-context.py` 在分派子代理前仍会额外同步阻塞约 `19-20ms`
- Validation Action:
  - 读取 `.codex/hooks.json`、`.claude/settings.json`
  - 分别基准执行对应 hook 脚本
- Impact Scope:
  - Codex / Claude 的新会话启动
  - Claude 的 Task/Agent 子代理分派前置链
- Suggested Fix Direction:
  - 若优化启动体验，可继续精简 SessionStart 生成逻辑
  - Claude 的 PreToolUse 可考虑对无 active task / 无匹配 agent 的情况更早退出

### [P1] `file_flow` 属于旧版嵌入谱系，不能作为当前 `0.5.10 + 0.1.27` 默认慢回归的直接证据
- Conclusion: `/ops/projects/work/file_flow` 的 workflow 落盘状态来自 `2026-04-21` 的旧版组合（`Trellis 0.4.0` + `workflow 0.1.24`），其 carrier surface 明显早于当前审计对象，不能直接代表当前版本默认行为。
- Evidence Source:
  - Layer: `generated target project`
  - Stage: `workflow-installed state after install-workflow.py`
  - `.trellis/.version = 0.4.0`
  - `.trellis/workflow-installed.json`:
    - `workflow_version = 0.1.24`
    - `patched_baseline_commands = ["start","finish-work","record-session"]`
    - `patched_codex_skills = ["start","finish-work"]`
    - `scripts` 仍含 `metadata-autocommit-guard.py`、`record-session-helper.py`
  - `.claude/commands/trellis/start.md`、`.opencode/commands/trellis/start.md`、旧命名 custom agents 仍存在
- Validation Action:
  - 读取 target project 的 `.trellis/.version` 与 `.trellis/workflow-installed.json`
  - 对比当前 source repo 的 `0.5.10 + 0.1.27` 合同与 fresh baseline 审计结果
- Impact Scope:
  - 任何试图用这个项目直接代表“当前 workflow 默认很慢”的判断
  - 历史项目排障时的归因口径
- Suggested Fix Direction:
  - 把它当成 legacy embedded project 单独分析
  - 不要把它与当前 fresh install 审计结果混为一谈

## Unconfirmed Items / False Alarms
- “formal install 后 Codex 会把大量 workflow 正文再次塞进 SessionStart” -> false alarm
  - runtime size probe 显示增量只有 `+31` chars
- “当前 workflow 仍默认要求 OpenCode 在 `instructions` 里加载整套长文档” -> false alarm
  - 当前 README 已明确禁止这种默认用法
- “`.codex/skills/` 缺失会导致当前 baseline 路径更慢或不完整” -> false alarm
  - fresh baseline 实测 `.codex/skills/` 默认不存在，且不影响 detect/install/check 主链
- “`file_flow` 现在的 SessionStart hook 本体本身就重到足以单独解释‘非常慢’” -> false alarm
  - 该项目当前 Codex / Claude hook 注入长度都约 `7106` chars，主要是 `current-state + workflow toc + backend/frontend/guides index`
- “OpenCode 的主要慢点是插件模块导入或 node_modules 体积本身” -> false alarm
  - 模块导入均值仅约 `1.4ms`；主要耗时发生在首消息同步链内部
- “`file_flow` 的慢点只是历史项目问题，当前 workflow fresh install 不再有同类 OpenCode 问题” -> false alarm
  - 同一离线基准下，legacy / current 的 OpenCode `chat.message` 链耗时几乎相同

## Blocked Items (Blocked / Evidence Gap / Needs Clarification)
- `file_flow` 当时为什么“非常慢”的精确端到端根因
  - Type: `Evidence Gap`
  - Cause:
    - 目前已测到当前落盘执行链，但未重放 2026-04-21 当时的真实 CLI 版本、模型端性能、OpenCode runtime 内部 `client.session.messages` 实际成本与用户级配置
    - OpenCode 若当时使用了额外用户级 `instructions`、旧 plugin runtime 或更慢的 session-history 查询链，其历史开销无法仅凭当前落盘文件完全复现
  - What is needed to continue:
    - 获取当时实际使用的 CLI（Claude / OpenCode / Codex）与版本
    - 若是 OpenCode，补当时的用户级 `opencode.json.instructions` / provider 配置
    - 做该项目上的真实 OpenCode runtime 首轮响应 benchmark，而不是仅测离线插件脚本

## Per-CLI Adaptation Conclusions

### Claude Code
- Expected carrier model: `.claude/commands/trellis/*.md` + Trellis baseline SessionStart / hooks + Trellis native agents
- Does the current implementation match: `confirmed`
- If not, what is wrong: 无当前适配漂移；慢点主要在 baseline SessionStart 注入体积，而非 workflow 增量

### OpenCode
- Expected carrier model: `.opencode/commands/trellis/*.md` 为正式入口，`instructions` 只挂主入口与必要补充
- Does the current implementation match: `confirmed`
- If not, what is wrong: 当前 source contract 已修正旧版厚注入建议；仅老项目手工配置漂移时仍可能变慢

### Codex
- Expected carrier model: `.agents/skills/` 共享 skills 主承载面 + `.codex/hooks.json` / hooks + `.codex/agents/*.toml`
- Does the current implementation match: `confirmed`
- If not, what is wrong: 当前默认慢点同样主要来自 baseline SessionStart，而不是 formal install 增量

## Suggested Fix Directions
- 如果目标是解决“现在仍觉得慢”，先优化 Trellis baseline SessionStart 注入，而不是先裁剪 workflow 阶段资产
- 如果目标是解决 OpenCode 的个别慢项目，先检查其 `opencode.json.instructions` 是否仍保留旧版厚挂载
- 若后续要做真正的性能治理，增加 hook 上下文字数与首轮 latency 的自动 benchmark，把 baseline 与 workflow 增量分开统计

## Flow-Friction Comparison

### Comparison Rule
- This section compares **workflow-step flow friction**, not raw script speed.
- Focus dimensions:
  - how many mandatory stage gates exist before implementation can start
  - whether stage completion always requires explicit user confirmation
  - whether the workflow auto-advances or forces re-entry
  - whether extra fixed tasks / audits / proof chains are mandatory
  - whether a finished mainline still requires extra post-mainline loops

### `file_flow` Embedded Workflow (`Trellis 0.4.0 + workflow 0.1.24`)
- Inherited strong-gate flow already existed:
  - every stage ends at `awaiting_user_confirmation`
  - `/trellis:start` only re-entered the current confirmed stage
  - no automatic cross-stage progression
  - no automatic next-task continuation after a task closes
- Planning-to-implementation friction already existed:
  - `brainstorm` required project-level estimate output before leaving the stage
  - `plan` required explicit task split and re-entry through `/trellis:start`
  - task-level `before-dev.md` was deferred until entering implementation
- Review-loop friction already existed:
  - `check` could conditionally branch into `review-gate`
  - all code-related tasks could later require `project-audit`
  - both `review-gate` and `project-audit` required explicit confirmation before leaving
- Ownership-proof friction already existed when enabled:
  - `design` had to freeze watermark / ownership-proof baseline
  - `plan` had to split watermark / verification / ownership-proof tasks
  - delivery had to verify ownership artifacts

### Current Workflow (`Trellis 0.5.10 + workflow 0.1.27`)
- All of the above strong-gate flow is still present:
  - per-stage explicit confirmation
  - no auto-advance
  - no auto-continue to the next task
  - `continue` only re-enters the current confirmed stage
- New or strengthened planning friction added on top:
  - `task_creation_checklist.md` must be completed before real task creation
  - `implement.jsonl` / `check.jsonl` curation is mandatory before `task.py start`
  - fresh flow now requires `task create -> brainstorm -> jsonl curation -> task start`
- New fixed task obligations added on top:
  - mandatory post-mainline `性能回归与优化任务`
  - early `walking skeleton / smoke`
  - early `packaging skeleton`
  - early `performance probe`
  - mandatory `UI -> 首版代码界面` task when a frontend-visual lane exists
- Existing proof-chain friction kept and expanded:
  - ownership-proof / watermark chain still applies
  - plan now explicitly requires those task splits plus post-mainline performance work
- Finish-path friction remains long:
  - implementation internal chain
  - formal `check`
  - conditional `review-gate`
  - `finish-work`
  - `delivery`
  - optional but often required `project-audit`

### Flow-Friction Verdict
- `file_flow` was already a high-friction workflow in terms of stage transitions and required confirmations.
- The current workflow does **not** remove that class of friction.
- The current workflow adds **additional mandatory planning gates and post-mainline tasks**, so the overall flow friction is **higher**, not lower.
- Therefore, if the question is whether the **current real workflow still has the kind of “workflow-step transition causes slowness” problem** seen in `file_flow`, the answer is **yes**, and the current version is **heavier** at the workflow-flow level.

### Flow-Friction Delta Table
- `Per-stage explicit confirmation`
  - `file_flow`: present
  - `current workflow`: present
  - verdict: retained
- `No automatic cross-stage advancement`
  - `file_flow`: present
  - `current workflow`: present
  - verdict: retained
- `Need explicit re-entry to continue work`
  - `file_flow`: `/trellis:start`
  - `current workflow`: `/trellis:continue`
  - verdict: retained with renamed primary entry
- `Conditional task-level extra review loop`
  - `file_flow`: `review-gate`
  - `current workflow`: `review-gate`
  - verdict: retained
- `Project-level final audit loop`
  - `file_flow`: `project-audit`
  - `current workflow`: `project-audit`
  - verdict: retained
- `Ownership-proof / watermark task chain`
  - `file_flow`: present when enabled
  - `current workflow`: present when enabled
  - verdict: retained
- `Task creation must wait for human checklist confirmation`
  - `file_flow`: not evidenced as a separate mandatory artifact
  - `current workflow`: mandatory `task_creation_checklist.md`
  - verdict: added / heavier
- `Sub-agent context curation before execution`
  - `file_flow`: not evidenced as a required once-only planning step in the active flow
  - `current workflow`: mandatory `implement.jsonl` / `check.jsonl` curation
  - verdict: added / heavier
- `Fixed post-mainline performance task`
  - `file_flow`: not evidenced as mandatory
  - `current workflow`: mandatory
  - verdict: added / heavier
- `Fixed early probe / skeleton tasks`
  - `file_flow`: not evidenced as mandatory trio
  - `current workflow`: mandatory when applicable
  - verdict: added / heavier
- `UI first-code task boundary`
  - `file_flow`: not evidenced as a dedicated mandatory lane task in the embedded flow contract
  - `current workflow`: mandatory when frontend-visual lane exists
  - verdict: added / heavier

### Decision Matrix

| 流转摩擦点 | `file_flow` | 当前 workflow | 判断 |
|---|---|---|---|
| 每阶段结束都要用户明确确认 | 有 | 有 | 保留 |
| 不能自动跨阶段推进 | 有 | 有 | 保留 |
| 前一 task 完成后不能自动续跑下一 task | 有 | 有 | 保留 |
| 需要重新进入主入口才能继续 | 有，`/trellis:start` | 有，`/trellis:continue` | 保留 |
| `check` 后可能再走任务级补充审查 | 有，`review-gate` | 有，`review-gate` | 保留 |
| 全部代码任务后可能再走项目级总审查 | 有，`project-audit` | 有，`project-audit` | 保留 |
| ownership proof / watermark 任务链 | 启用时存在 | 启用时存在 | 保留 |
| 真建 task 前必须先走单独的人类确认清单 | 未见独立硬门 | 有，`task_creation_checklist.md` | 新增 |
| 开工前必须补 sub-agent 上下文配置 | 未见作为独立必经阶段 | 有，`implement.jsonl` / `check.jsonl` | 新增 |
| 主干完成后强制追加性能回归后置任务 | 未见强制固定后置任务 | 有，`性能回归与优化任务` | 新增 |
| 开始主干前强制前置 skeleton / probe | 未见固定三件套 | 有，`walking skeleton / packaging skeleton / performance probe` | 新增 |
| 前端视觉落地必须额外拆专属 task | 未见固定 lane task | 有，`UI -> 首版代码界面` | 新增 |

### Final Comparative Verdict
- If the benchmark is **"Will the workflow's stage transitions and mandatory flow discipline slow down end-to-end progress?"**, then:
  - `file_flow`: yes
  - `current workflow`: yes, and more strongly
- Therefore the current workflow **still has the same class of flow-friction problem**, and the total friction is **higher** because it keeps the old gate structure and adds new mandatory pre-start / post-mainline steps.

### Practical Readout
- `file_flow` 的慢，更像是“强门禁 + 多次确认 + 审查回路 + proof 链”。
- 当前 workflow 的慢，则是“保留上述全部摩擦，再额外加 task 创建确认、jsonl 配置、固定性能后置任务、固定早期探针、前端专属 lane task”。
- 所以如果你的目标是削掉**流转导致的慢**，优先目标不该是单个 hook，而应该是：
  1. `task_creation_checklist.md`
  2. `implement.jsonl` / `check.jsonl` 必经门
  3. `性能回归与优化任务` 固定后置要求
  4. `walking skeleton / packaging skeleton / performance probe` 固定前置要求
  5. `review-gate` / `project-audit` 的默认进入条件是否过宽

## Flow-Reduction Recommendations

### P0 — First Cuts (highest impact on flow speed)

#### 1. Stop requiring explicit confirmation at every stage boundary
- Current state:
  - `file_flow`: every stage stops for explicit confirmation
  - current workflow: same rule retained
- Why it slows end-to-end flow:
  - adds a mandatory human checkpoint even when the stage output is obvious and low-risk
  - creates repeated “stop → confirm → re-enter” loops
- Recommendation:
  - keep explicit confirmation only for irreversible or high-cost transitions:
    - `feasibility -> brainstorm`
    - `plan -> implementation`
    - `check -> review-gate`
    - `finish-work -> delivery`
  - allow low-risk intra-mainline transitions to continue in the same round

#### 2. Remove `task_creation_checklist.md` as a universal hard gate
- Current state:
  - `file_flow`: not evidenced as a separate mandatory pre-task artifact
  - current workflow: mandatory before real task creation
- Why it slows flow:
  - inserts an extra human approval artifact before any real execution can start
  - duplicates information that already exists in `prd.md` / `task_plan.md`
- Recommendation:
  - make it conditional only for:
    - `L2`
    - external outsourcing / payment-gated projects
    - high blast radius / release-sensitive work
  - skip it entirely for `L0` and most `L1`

#### 3. Remove the unconditional post-mainline `性能回归与优化任务`
- Current state:
  - `file_flow`: not evidenced as mandatory
  - current workflow: mandatory for all projects
- Why it slows flow:
  - guarantees every mainline ends with one extra required loop
  - turns “performance-sensitive projects” into “all projects”
- Recommendation:
  - trigger only when at least one condition holds:
    - performance probe shows regression risk
    - product has explicit performance SLO / startup / memory targets
    - the changed surface is performance-sensitive
  - otherwise keep performance validation inside normal `check` / `delivery`

#### 4. Stop default-enabling the full ownership-proof / watermark chain for all projects
- Current state:
  - `file_flow`: ownership-proof chain existed when enabled
  - current workflow: same chain retained and described as default-on in current docs
- Why it slows flow:
  - adds design artifacts, extra tasks, validation steps, and delivery proof work
  - changes a specialized control path into the default path
- Recommendation:
  - switch to opt-in or scenario-gated default:
    - external outsourcing
    - source-transfer-sensitive work
    - explicit author-rights protection need
  - do not make it the default for ordinary internal work

### P1 — Conditionalize, don’t delete

#### 5. Downgrade `implement.jsonl` / `check.jsonl` from universal planning gate to dispatch-mode gate
- Current state:
  - current workflow requires JSONL curation before `task.py start` in sub-agent flows
- Why it slows flow:
  - adds an extra preparation step before implementation begins
  - creates friction even when the main session will implement directly
- Recommendation:
  - keep mandatory only when:
    - dispatch mode = sub-agent
    - task complexity justifies remote context injection
  - skip for:
    - inline mode
    - `L0`
    - single-file / low-risk tasks

#### 6. Downgrade `walking skeleton / packaging skeleton / performance probe` from near-default trio to applicability-based triggers
- Current state:
  - current workflow strongly front-loads these probes
- Why it slows flow:
  - forces side tasks before the user sees mainline progress
  - moves uncertainty handling into mandatory pre-work even when risk is low
- Recommendation:
  - `walking skeleton` only for architecture-risk / integration-risk work
  - `packaging skeleton` only for packaging-sensitive desktop / native-shell paths
  - `performance probe` only when measurable performance targets actually matter

#### 7. Narrow `project-audit` to true project-wide risk
- Current state:
  - `file_flow`: project-audit already existed
  - current workflow retains it and also places it after the fixed performance task
- Why it slows flow:
  - adds a project-level re-review loop after task-level work is already complete
- Recommendation:
  - trigger only for:
    - multi-task / multi-module accumulation risk
    - release-candidate / pre-ship review
    - external delivery / high blast radius
  - do not normalize it for ordinary small sequences of tasks

#### 8. Keep `review-gate`, but make its trigger narrower and more objective
- Current state:
  - both legacy and current workflow retain `review-gate`
- Why it slows flow:
  - if the trigger is broad, normal tasks are pushed into multi-CLI review loops
- Recommendation:
  - require a concrete trigger:
    - security / permissions / migration
    - unresolved cross-layer blast radius
    - test evidence clearly insufficient
    - explicit user request
  - avoid subjective triggers like “maybe risky”

#### 9. Keep `UI -> 首版代码界面` only for true prototype-to-code handoff projects
- Current state:
  - current workflow introduces it as a dedicated lane task when a frontend-visual lane exists
- Why it slows flow:
  - creates a special-case lane and CLI restriction even for ordinary frontend iteration
- Recommendation:
  - trigger only when:
    - there is an external prototype / Stitch / visual handoff
    - visual-system convergence is itself a project milestone
  - do not require it for routine frontend feature work

### P2 — Keep, but smooth the operator experience

#### 10. Preserve “no blind auto-advance,” but stop forcing explicit re-entry for obvious next moves
- Current state:
  - both legacy and current workflow require re-entry (`start` / `continue`)
- Why it slows flow:
  - introduces repeated entry command friction even when the next step is mechanically obvious
- Recommendation:
  - keep anti-auto-jump semantics
  - but allow:
    - same-round continuation after user confirmation
    - direct stage transition inside the same active session without forcing a new route entry

#### 11. Preserve task-local `before-dev.md`, but avoid using it as a hidden extra gate
- Current state:
  - both flows rely on `before-dev` / `before-dev.md`
- Why it slows flow:
  - can become another invisible mandatory step the user did not explicitly ask for
- Recommendation:
  - keep it as auto-generated context support
  - do not let it become an additional human-facing approval gate

### Prioritized Trim Order
- First trim:
  1. per-stage explicit confirmation everywhere
  2. universal `task_creation_checklist.md`
  3. unconditional `性能回归与优化任务`
  4. default-on ownership-proof chain
- Second trim:
  1. universal JSONL curation
  2. fixed early probe trio
  3. broad `project-audit` usage
  4. broad `review-gate` usage
- Third trim:
  1. `UI -> 首版代码界面` overuse
  2. forced route re-entry for obvious same-session continuation

## Propagation Scope and Synchronized Update Range
- 受影响判断层：
  - `.codex/hooks/session-start.py`
  - `.claude/hooks/session-start.py`
  - `.opencode/lib/session-utils.js`
  - `docs/workflows/新项目开发工作流/commands/opencode/README.md`
  - 历史 target project 的 `opencode.json.instructions`
- 风险说明：
  - 若继续把 baseline 重注入误判成 workflow 增量，会导致错误裁剪 source workflow
  - 若忽略老项目手工配置漂移，又会误以为所有“变慢”都已消失

## Recommended Next Step
- Recommended action: `plain-language action`
- Trigger condition: 已完成事实审计，但是否继续做性能优化需要先决定优化对象是 baseline 还是 workflow
- Recommendation reason: 现在最需要的是先选方向：
  - 要么去查具体慢项目的 OpenCode/Codex 本地配置漂移
  - 要么新开一个 baseline 性能优化任务，专门压缩 SessionStart 注入
- Stronger alternatives not selected: 不直接 `start` 改 workflow 源资产，因为当前没有证据证明 workflow 安装增量本身是主要根因

## Stop Point and Pending Confirmations
- Auto-continue allowed: `No`
- User confirmation required for:
  - 是否继续追某个具体 CLI/项目的真实慢路径
  - 是否新开任务专门优化 Trellis baseline SessionStart 注入

## Refined Rule 8

### Scope
- Accepted optimization target: `review-gate`
- Rejected / ignored in this round:
  - `1`
  - `5`
  - `6`
  - `7`
  - `9`

### Final Hard Conditions
The following remain hard triggers for `review-gate`:

1. 认证 / 授权 / 权限边界 / 敏感信息处理
2. 数据迁移 / schema 变化 / 删除 / 回填
3. 公共 API / 跨层 contract / 外部系统集成
4. 支付 / 消息队列 / 缓存一致性 / 并发状态
5. 共享核心模块且 blast radius 明显
6. 用户显式要求使用 `review-gate`

### Anti-patterns (not sufficient by themselves)
The following must not trigger `review-gate` on their own:

- “看起来复杂”
- “改动文件稍多”
- “CLI 想更稳一点”

### Clarified `blast radius 明显高`
Only treat condition `5` as hit when at least one of the following is true:

- 改动落在多个 feature / module / package 共用的核心模块，且当前代码搜索已知下游消费者不少于 3 处
- 改动改变多个层之间共享的数据 contract / serialization / validation 语义
- 改动影响全局启动 / 构建 / runtime 初始化 / 全局状态一致性
- 一旦出错，影响不是局部功能退化，而是跨功能、跨任务或跨模块系统性失效

If these cannot be shown from code / context evidence, do not upgrade the task to hard condition `5`.

### Clarified `测试或验证证据明显不足`
This stays a soft condition, not a hard one.

Treat it as “明显不足” when at least one of the following is true:

- 变更了行为或修复了 bug，但没有对应自动化测试，也没有明确的手工验证记录
- 变更了失败路径 / 异常分支 / 回退逻辑，但没有负向验证证据
- 变更了跨层 contract / serialization / integration 行为，但没有对应集成或边界验证
- 跳过了当前任务本应执行的关键验证命令，且没有等价替代证据

Do not treat the following as “明显不足” by default:

- 一般性的覆盖率不够理想，但当前改动路径已有合理自动化或手工验证
- 纯文档 / 纯重构 / 无行为变化改动
- 仅因为“还可以补更多测试”

### Soft-Condition Decision Rule
- Hard condition hit → `required`
- No hard condition hit, but the confidence layer alone reaches medium because evidence is clearly insufficient → `recommended`
- No hard condition hit, but multiple soft layers together reach the existing medium threshold → `recommended`
- Otherwise → `skip`

### Explicit User Trigger Boundary
Separate the two user-driven cases:

1. User explicitly asks for `review-gate`
   - Must enter the `review-gate` stage
   - The result inside the stage may still be `skip` / `recommended` / `required`
   - AI must not refuse stage entry just because it judges the task low-risk

2. User explicitly asks for “多 CLI 审查 / 让其他 CLI 再看一轮 / multi-cli-review”
   - Treat external reviewer execution as required unless tooling is unavailable
   - If tooling is unavailable, stop as blocked with dependency reason; do not silently downgrade

### Final Policy
- Default trigger becomes narrower and more evidence-based
- Domain-specific high-risk areas (支付 / MQ / 缓存 / 并发) remain explicitly listed
- “验证证据明显不足” remains soft, but stronger than before
- User-explicit `review-gate` request always forces stage entry
