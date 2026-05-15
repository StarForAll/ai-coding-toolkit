# Trellis 隐藏目录边界清单

> 适用对象：**当前仓库 `ai-coding-toolkit` 自身**。  
> 这份清单用于判断本仓库里 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.qoder/`、`.kiro/`、`.agents/` 等隐藏目录的归属边界，避免把 repo-local overlay、手工维护文件和 ignored runtime residue 混成同一种“漂移”。

## 先分清边界

这份文档描述的是 **source repo 当前真实状态**，不是“目标项目安装 workflow 之后”的检查表。

- 当前 source repo 的装后/升级对照文档：`docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`
- 当前文档：只回答 **本仓库自身** 的隐藏目录文件应该如何归类、如何判断问题

## 三类文件

```text
managed hidden assets
  -> 当前仓库中由 Trellis baseline 或其后续 managed deployment 面承载的文件
manual project-owned hidden assets
  -> 当前仓库自己维护、但不应由 .template-hashes 充当真相源的隐藏文件
ignored runtime residue
  -> 运行时状态、备份、缓存、临时产物；不属于长期 source-of-truth
```

## 一、Managed Hidden Assets

这类文件的特点：

- 是当前仓库 Trellis 运行机制的一部分
- 多数会出现在 `.trellis/.template-hashes.json` 中
- 可以和 fresh `trellis init` baseline 不同，因为本仓库允许 repo-local overlay
- 判断是否异常时，不能只看“和 `/tmp/trellis-0.5.15` 不同”，还要看该差异是否被当前 repo 明确保留

常见路径：

| 路径 | 说明 |
|------|------|
| `.trellis/workflow.md` | 当前仓库 Trellis 主流程 source-of-truth |
| `.trellis/config.yaml` | 当前仓库 Trellis 配置入口 |
| `.trellis/scripts/*.py` `common/*.py` | 任务、runtime、journal、validation 等脚本 |
| `.agents/skills/trellis-*` | 共享 Trellis skills 主承载面 |
| `.claude/agents/trellis-*` `.codex/agents/trellis-*` `.opencode/agents/trellis-*` `.qoder/agents/trellis-*` `.kiro/agents/trellis-*` | 各 CLI 的 Trellis agent carrier |
| `.codex/hooks.json` `.codex/hooks/*.py` | Codex 的 Trellis hook carrier |
| `.qoder/hooks/*.py` `.qoder/settings.json` | Qoder 的 Trellis hook/config carrier |
| `.opencode/plugins/*.js` `.opencode/package.json` | OpenCode 的 Trellis plugin/config carrier |
| `.trellis/.template-hashes.json` | managed deployment drift detector，本身不是“所有隐藏文件”的总表 |

判断规则：

1. 先看文件是否属于当前 repo 的 live carrier，而不是 `.trellis/.backup-*` 或 runtime 目录。
2. 若文件在 `.template-hashes.json` 中：
   - hash 不同不自动等于缺陷
   - 先检查是否属于 repo-local overlay，或是否被测试明确要求“保持可检测差异”
3. 若文件是当前 repo 明确保留的 overlay，应看行为和文档是否自洽，而不是强行回退到 stock baseline。

## 二、Manual Project-Owned Hidden Assets

这类文件的特点：

- 会影响当前仓库行为
- 可能被 git 跟踪
- 但不应由 `.template-hashes.json` 作为真相源
- 更接近“本仓库手工维护的本地/平台配置面”

当前仓库里的典型例子：

| 路径 | 说明 |
|------|------|
| `.claude/settings.local.json` | 本机权限/MCP allowlist 扩展；当前仓库已跟踪，但不属于 Trellis managed hash 集 |
| `.claude/hooks/statusline.py` | 当前仓库自加的 Claude statusline helper，不在 fresh 0.5.15 baseline 中 |
| `.opencode/bun.lock` `.opencode/package-lock.json` | OpenCode 本地依赖锁文件；由当前仓库自行维护 |
| `.qoder/skills/record-session/SKILL.md` | legacy/manual fallback 入口；不应误判为当前主路径 |

判断规则：

1. 这类文件和 stock baseline 不同，通常不是“原生 Trellis 出错”，而是当前仓库自有配置。
2. 这类文件的漂移检查应看：
   - 是否仍符合当前 repo 文档
   - 是否与相关主路径冲突
   - 是否错误地伪装成 managed baseline
3. 不要试图把它们补进 `.template-hashes.json` 来“消灭差异”。

## 三、Ignored Runtime Residue

这类文件的特点：

- 不属于长期 source-of-truth
- 主要用于运行时状态、恢复、缓存、备份
- 应作为“当前状态”检查，而不是“代码/配置漂移”检查

常见路径：

| 路径 | 说明 |
|------|------|
| `.trellis/.runtime/sessions/*.json` | session-scoped active task runtime state |
| `.trellis/.runtime/degraded-active-task.json` | degraded active task fallback |
| `.trellis/.runtime/update-check-*.marker` | 版本检查/运行时 marker |
| `.trellis/.backup-*` | 历史备份目录 |
| `.opencode/node_modules/` | 本地依赖缓存 |
| `**/__pycache__/` `**/*.pyc` | Python cache |

判断规则：

1. 这类文件不进入正常 source review。
2. 若 runtime 指向的 task 已不存在，应清理状态文件，而不是把问题归因到 workflow baseline。
3. 备份和 marker 变多通常是运维噪音，不应直接记成“实现漂移”。

## 当前仓库的判断口径

### 1. `.template-hashes.json` 的边界

`.trellis/.template-hashes.json` 只回答：

- 当前仓库哪些 **managed deployment files** 在受监控
- 这些 managed 文件与其记录 hash 是否一致

它**不回答**：

- 所有隐藏目录文件是否都被管理
- 所有和 stock baseline 的差异是否都是缺陷
- `.claude/settings.local.json`、`.opencode/package-lock.json` 这类 manual 文件的状态

### 2. runtime stale state 的边界

当 `.trellis/.runtime/sessions/*.json` 或 `.trellis/.runtime/degraded-active-task.json` 指向已不存在的 task 时，优先按“runtime residue”处理：

- 删除 stale 指针
- 保留仍指向 live task 的 session
- 不把它直接升级为“当前 Trellis 实现仍然坏着”，除非能用 fresh baseline 复现

### 3. source repo 与 target project 不要混用清单

如果要检查 **目标项目安装 workflow 后** 的隐藏目录边界，使用：

- `docs/workflows/新项目开发工作流/装后隐藏目录与托管边界核对清单.md`

如果要检查 **当前仓库自身** 的隐藏目录状态，使用本文。

## 建议检查顺序

1. 先看目标对象是不是 live carrier、manual config，还是 ignored runtime。
2. 如果是 managed file，再看：
   - 是否在 `.template-hashes.json`
   - 是否有 repo-local overlay 理由
   - 是否有测试或文档显式保留该差异
3. 如果是 manual file，看它是否仍符合 repo 当前主路径。
4. 如果是 ignored runtime residue，优先做清理或降噪，不要直接上升为实现缺陷。

## 本轮已处理的 runtime 修复

当前仓库已清理 `.trellis/.runtime/sessions/` 中指向不存在 task 的 stale session 文件，只保留仍指向 live task 的 session 记录。

后续若再次出现同类问题，按本文的 “Ignored Runtime Residue” 口径处理。
