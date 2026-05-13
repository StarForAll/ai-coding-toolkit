# Research: current-trellis-runtime-and-upgrade-residue

- **Query**: 分析当前仓库真实生效的 Trellis runtime，以及 0.5.12 → 0.5.14 相关 minor upgrade 残留是否正确保留、错误回退、或仍有遗漏
- **Scope**: internal
- **Date**: 2026-05-13

## Runtime mechanism summary

### Live runtime surfaces

本仓库当前真正生效的 Trellis runtime 在以下路径，不应把 `docs/workflows/新项目开发工作流/` 当成这次任务的 runtime 真源：

| Path | Role |
| --- | --- |
| `.trellis/workflow.md` | 唯一有效的 Phase / workflow-state 合同 |
| `.trellis/scripts/common/active_task.py` | 会话级 active task 解析与 runtime session 文件定位 |
| `.trellis/scripts/common/session_context.py` | `get_context.py` 的 Git/任务/工作区上下文拼装 |
| `.trellis/scripts/common/task_store.py` | task create/start/archive 生命周期 |
| `.trellis/scripts/common/safe_commit.py` | `.trellis` 受控路径的安全 stage/auto-commit 边界 |
| `.trellis/scripts/add_session.py` | 会话日志写入与 journal commit |
| `.claude/`, `.qoder/`, `.opencode/`, `.codex/`, `.kiro/` | 平台侧 hooks / agents / skills / settings |
| `.agents/skills/trellis-*` | 共享 Trellis skills，在多个平台部署层复用 |
| `.trellis/.template-hashes.json` | Trellis 模板落盘哈希记录 |
| `.trellis/.version` | 当前 live Trellis 版本 |

### Developer / session bootstrap

- `python3 ./.trellis/scripts/get_context.py` 是主入口；当前输出显示本仓库处于 Git worktree，当前无 active task，但存在 `05-13-analyze-current-trellis-runtime-and-minor-upgrade-residue/` 等 planning 任务。
- `.trellis/workflow.md` 仍定义原 live Phase 编号：Phase 1/2/3，对应关键步骤 `1.3`、`1.4`、`2.1`、`2.2`、`3.1`、`3.3`、`3.4`、`3.5`，这仍是所有升级判断的编号真源。

### Active-task resolution

- `active_task.py` 把 active task 存在 `.trellis/.runtime/sessions/*.json`，是“按 AI session/window 隔离”的模型，不是全局单例。
- 解析顺序来自 hook 输入和环境变量；支持 `CLAUDE_*`、`CODEX_*`、`OPENCODE_*`、`QODER_*` 等平台变量，必要时会生成标准化 context key。
- `normalize_task_ref()` / `resolve_task_ref()` 允许 `.trellis/tasks/...`、`tasks/...`、绝对路径三种表达。
- 历史 session 文件确实存在，说明 live runtime 一直依赖 `.trellis/.runtime/sessions/`，不是文档层描述。

### Task lifecycle

- `task.py create` 创建 task 目录并在有 sub-agent 平台时 seed `implement.jsonl` / `check.jsonl`。
- `task.py start` 负责把 task 状态切到 `in_progress` 并写 session pointer。
- `task.py finish` 清 session pointer，但不改 task status。
- `task.py archive` 先写 `status=completed`，再 move 到 `archive/`，并清理仍指向该 task 的 session 文件。

### Context injection / platform split

- Claude / Kiro 走 Python hook 注入；`inject-subagent-context.py` 直接调用 `active_task.resolve_active_task(...)`。
- Qoder 当前只有 `session-start` 和 `inject-workflow-state` 配置，研究/实现/检查 agent 依赖 agent 文件自身说明与 `task.py current --source` 兜底，不存在专门的 subagent-context hook。
- Codex 当前 live 配置是“有 sub-agent carrier 文件，但主流程是否 inline/sub-agent 由 `.trellis/workflow.md` 和 `.trellis/config.yaml` 决定”；本地 `.codex/hooks.json` 只挂 `inject-workflow-state.py`。
- OpenCode 是独立 JS runtime：`lib/trellis-context.js` 负责 session/task 解析，`plugins/inject-subagent-context.js` 负责 task tool prompt 注入，`plugins/session-start.js` / `inject-workflow-state.js` 负责主会话 breadcrumb。

### Workspace / journal recording

- `.trellis/workspace/xzc/journal-5.md` 仍是 live journal；`get_context.py` 读它的行数，`add_session.py` 负责写 session，并由 `session_commit_message` 控制 journal commit message。
- 现有 workspace 历史已多次记录 `.new` 和 minor-upgrade 审计结论，因此这次判断必须与历史已定规则一致。

## Upgrade diff classification

### A. 正常且应保留的 live 0.5.14 级增强

1. `.trellis/.version`：`0.5.12 -> 0.5.14` 是正常版本前移。
2. `session_context.py`：新增 `_collect_root_git_info()`、polyrepo child repo fallback、root-is-not-git 的防误报逻辑。这类增强与 live repo/runtime 兼容，且当前仓库确实是 root Git repo，行为合理。
3. OpenCode runtime：
   - `lib/trellis-context.js` 新增 `isTrellisSubagent()`、single-session fallback、session 文件解析增强。
   - `plugins/session-start.js` / `inject-workflow-state.js` 跳过 trellis sub-agent turn，避免主会话 breadcrumb 覆盖子代理上下文。
   - `plugins/inject-subagent-context.js` 增强 `Active task: <path>` hint 解析、Windows shell 前缀判断、相对/绝对 task 路径统一解析。
4. Claude / Qoder / Codex hook timeout 上调：
   - `.claude/settings.json`：session-start `10 -> 30` 秒，workflow-state `5 -> 15` 秒。
   - `.qoder/settings.json`：同类 timeout 上调。
   - `.codex/hooks.json`：workflow-state `5 -> 15` 秒。
   这些改动只放宽 hook 超时，不改变合同方向，属于低风险保留项。
5. `task_store.py` + `safe_commit.py` 的“archive commit 缩域”方向本身正确：目标是避免 archive 自动提交把其他 active tasks 的脏变更一起打包，符合历史“scope creep”收敛原则。

### B. 当前 worktree 中最可疑、且与既有 live 合同冲突的回退

#### B1. trellis-research 在多平台被再次错误简化

以下 live 文件都被改成“只剩 Glob/Grep + Exa”的弱化版：

- `.claude/agents/trellis-research.md`
- `.qoder/agents/trellis-research.md`
- `.opencode/agents/trellis-research.md`
- `.codex/agents/trellis-research.toml`

证据：

- 当前 diff 明确删除了 `ace.search_context`、`Context7`、`deepwiki`、`grok-search` 的工具/路由说明。
- 这与仓库历史结论直接冲突：`journal-5.md` Session 189 已记录“Restore research agent MCP tools + 3-step fallback”，并且 `05-08-trellis-0-5-7-new/prd.md` 明确把“trellis-research 工具列表被错误简化”定性为必须拒收的升级候选。
- 本仓库顶层 AGENTS 也规定：代码定位优先 `ace.search_context`，三方库必须 `Context7`，最新信息必须 live web，不允许降成仅凭 Exa/grep。

结论：这不是“正常 0.5.14 更新”，而是把已验证正确的 live 合同再次回退成过去曾明确拒收的弱化版。

#### B2. Codex “inline 主流程限制”说明被删，但 live workflow 仍保留 inline 分支

被删位置：

- `.codex/agents/trellis-check.toml`
- `.codex/agents/trellis-implement.toml`
- `.codex/agents/trellis-research.toml`
- `.codex/config.toml`

问题不在于注释被删本身，而在于：

- `.trellis/config.yaml` 仍说明 Codex 默认 `dispatch_mode: inline`。
- `.trellis/workflow.md` 仍保留 `[workflow-state:planning-inline]` 和 `[workflow-state:in_progress-inline]`。
- 但当前会话实际又已经使用了 `trellis-research` sub-agent，说明“Codex 是否 inline”在 live repo 中本来就处于过渡/双轨状态。

结论：这里不是立即的功能性 bug，但属于合同表述漂移。删除说明后，live repo 对“Codex 主会话何时必须 inline、何时允许 Trellis sub-agent”变得更模糊。

### C. 方向正确但仍需进一步核对的 live 改动

#### C1. `task_store.py` / `safe_commit.py` 的 archive 修复

保留理由：

- 新逻辑通过 `modified_children` 缩小 stage 范围，避免把其他并行窗口下的 active task 一起自动提交。
- 额外 `git rm --cached --ignore-unmatch` 是为了解决 moved-away source task 的 delete staging 问题，注释与代码意图一致。

残留风险：

- `safe_archive_paths_to_add()` 的 docstring 仍写“source task directory”属于返回范围，但新实现实际在 `task_name is not None` 分支里不返回 source path，而是由 `_auto_commit_archive()` 额外补 `git rm --cached`。代码行为本身可以成立，但文档与函数返回值语义不再完全一致。
- `safe_git_add()` 现在统一不用 `-A`，完全依赖调用方手动补删路径；这要求所有 archive/journal 调用点都已经同步完成调用侧修补。当前仅检查到 archive 链路做了这个补丁。

结论：这组改动更像“有意识的 selective merge”，应保留，但需要靠回归验证确认没有新的漏删/漏提交流程。

### D. 派生文件更新

- `.trellis/.template-hashes.json` 只是追踪当前 live 文件内容的派生记录。
- 由于当前 worktree 里存在疑似错误回退（特别是 research agent 弱化），所以这次 hash 更新不能被当作正确性证据，只能视为“当前工作树的快照”。

## `.new` handling recommendations

### 当前状态

- 当前仓库里 **没有任何待处理的 `*.new` 文件**。`find . -name '*.new' -o -name '*.new.*'` 返回空。
- 因此这次任务里所谓 “`.new`-style upgrade decision” 不是指还有实体 `.new` 文件没删，而是指：之前由 `.new` 候选触发的 merge / reject 决策，是否在本轮 0.5.14 live diff 中被错误改回去。

### 对本轮 diff 的 `.new` 式裁决

1. `trellis-research` 简化版改动：**discard / revert**
   - 理由：它等价于再次采纳历史上已明确拒收的 `.new` 候选内容。
2. OpenCode 上下文注入增强：**already settled / keep**
   - 理由：这是 live runtime 健壮性修复，不是历史拒收项。
3. hook timeout 上调：**already settled / keep**
   - 理由：与历史规则不冲突，也没有功能回退迹象。
4. `task_store.py` / `safe_commit.py` selective-merge：**merge already in progress, keep but verify**
   - 理由：方向与历史“缩域 + 不吞并其他 dirty tasks”一致，但要靠验证确认没有新回归。
5. `.codex/*` carrier 注释删除：**merge decision unclear**
   - 理由：不是显式 bug，但会削弱 live repo 对 inline/sub-agent 双轨行为的自描述，应视为“需人工确认是否保留”的文档级残留。

## Suspected omissions / regressions

### 1. `trellis-research` 合同回退是本轮最严重回归

影响：

- 与仓库和全局 AGENTS 的证据优先策略冲突。
- 直接降低 research agent 的能力边界，尤其是代码定位、官方文档检索、最新信息核实。
- 这不是抽象风格问题，而是会让后续研究任务失去必须使用的证据通道。

### 2. 当前 worktree 没有把“0.5.12 已修复结论”延续到 0.5.14

历史已知结论：

- `journal-5.md` Session 189 已确认：research agent MCP 工具要恢复；`.new` 不是自动可信真源；template hashes 要在 live 内容稳定后再同步。

而当前 worktree：

- 又把 research agent 改回弱化版。
- 同步刷新了 `.template-hashes.json`。

这说明本轮 minor upgrade residue 处理没有完整继承前一次审计结论。

### 3. Codex runtime 合同出现“行为仍双轨、说明却被删”的漂移

证据：

- live workflow 仍含 inline / sub-agent 两套分支。
- `.codex/config.toml` 中针对 inline 模式的说明被删。
- `.codex/agents/trellis-research.toml` 同时又失去了“dispatch prompt 第一行 `Active task:` fallback”的说明。

这会增加维护者误判：以为 Codex 现在只有单一路径，但 live workflow 与当前实际操作并非如此。

### 4. `change-workflow.md` 的 Phase 表述有改善，但仍是压缩式改写

这次从 `Phase 3.1 -> 3.3 -> 3.4` 改成 `Phase 3.1 (verify quality + spec update)`，方向是减少错误链式表述；但它把 Phase 3.3 吞进一句话里，不再直观反映 workflow.md 中 `3.1 / 3.3 / 3.4 / 3.5` 的分离关系。

这不是阻塞性 bug，但属于文档精度下降。

## Confidence / evidence gaps

### Confidence

- **High**：active-task / workflow / session runtime 机制图
- **High**：当前不存在待处理实体 `.new` 文件
- **High**：research agent 弱化是对历史已拒收升级内容的回退
- **Medium**：`task_store.py` / `safe_commit.py` 新 archive 逻辑是否完全无回归
- **Medium**：Codex inline/sub-agent 双轨合同在 0.5.14 的最终意图

### Evidence gaps

- 这次只做静态审计，没有实际执行 `task.py archive` 或 `add_session.py` 来验证 archive/journal auto-commit 行为。
- 未比对 `trellis 0.5.14` 上游模板原文；本结论只基于本仓库 live 合同、当前 diff、以及仓库内既有升级审计记录判断“是否适合本仓库继续保留”。

### Recommended verification

若后续要把这份审计转成修复，优先验证：

```bash
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/get_context.py --mode record
python3 ./.trellis/scripts/task.py current --source
python3 -m unittest trellis-library/tests/test_cli.py
```

另建议补一轮针对 archive auto-commit 的脚本级回归验证，覆盖：

- archive 单任务但存在其他 active task 脏变更时，不应误带提交
- moved-away source task 的删除能否稳定进入 `chore(task): archive ...` 提交
- `session_auto_commit: false` 下 archive / add_session 都不应触发 git stage/commit
