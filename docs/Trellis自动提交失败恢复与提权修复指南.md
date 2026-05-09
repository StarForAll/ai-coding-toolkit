# Trellis 自动提交失败恢复与提权修复指南

> 适用场景：某个项目已经在使用 Trellis，本地 `finish-work` / `task.py archive` 会在最后一步尝试自动提交 `.trellis/` 元数据，但因为只读文件系统、沙箱、权限限制、`.git/index.lock` 无法创建等原因失败。

这份文档不是当前仓库专用 spec，而是一份**可迁移到其他 Trellis 项目的独立修复指南**。  
如果其他项目出现同样问题，可以直接按本文对应步骤修改它自己的 `.trellis/` 运行时脚本和命令入口。

下文里凡是提到“当前仓库实际使用情况”，均以本仓库 **2026-05-09** 时的入口面为准：

- 主入口链：`.agents/skills/trellis-finish-work/SKILL.md`
- Claude / OpenCode 命令入口：`.claude/commands/trellis/finish-work.md`、`.opencode/commands/trellis/finish-work.md`
- Qoder 当前命令入口：`.qoder/commands/trellis-finish-work.md`
- Codex 特例：`record-session-helper.py` 是当前仓库为 Codex 补充的 close-out helper，不应被描述成其他 CLI 的默认收尾路径
- Qoder 兼容副本：`.qoder/skills/trellis-finish-work/SKILL.md` 仍存在，且当前仓库中已经对齐到共享 `trellis-finish-work` 主链语义；后续不能再漂回旧的 pre-commit checklist
- 遗留 / fallback 入口：`.agents/skills/record-session/SKILL.md` 仍然存在，但已经明确标成 legacy/manual fallback
- 平台遗留入口：`.qoder/skills/record-session/SKILL.md` 仍然存在，但它不是当前推荐主路径；当前仓库中已对齐到共享 fallback 语义，后续若继续保留也必须保持一致

---

## 1. 问题定义

典型现象：

- `python3 ./.trellis/scripts/task.py archive <task>` 已执行归档，但自动提交失败
- `python3 ./.trellis/scripts/add_session.py ...` 已写 journal / index，但自动提交失败
- `record-session-helper.py` 或 Codex 特化的 close-out helper 链在最后一步停住（其他 CLI 的默认 `finish-work` 入口仍以 `add_session.py` 为主；个别平台仍可能保留遗留 `record-session` 入口）
- stderr 中出现类似：
  - `Read-only file system`
  - `Permission denied`
  - `Operation not permitted`
  - `.git/index.lock`
  - `不能创建`

如果系统只是打印：

- `[WARN] git add failed ...`
- `[WARN] Auto-commit failed ...`
- `Please commit .trellis manually`

那么说明这个项目的 Trellis 运行时只具备“失败提示”，**没有可恢复 / 可提权重试协议**。

---

## 2. 修复目标

把当前项目的 Trellis 自动提交链路改成下面的行为：

1. 自动提交正常时：照常完成闭环
2. 自动提交因只读/权限失败时：
   - 明确识别“这是只读/受限写入”
   - 生成**机器可读**的恢复命令
   - 优先建议当前 CLI 用提权方式立即重试
   - 仅当当前环境确实不支持提权时，才退回手工提交

换句话说，目标不是“避免所有失败”，而是把失败从：

- 模糊 warning

提升为：

- **结构化恢复协议**

---

## 3. 需要修改的文件

### 3.1 归档自动提交链

- `.trellis/scripts/common/task_store.py`
- `.trellis/scripts/task.py`

### 3.2 会话记录自动提交链

- `.trellis/scripts/add_session.py`
- `.trellis/scripts/workflow/record-session-helper.py`
- `.trellis/scripts/workflow/metadata-autocommit-guard.py`

### 3.3 用户入口文档 / 技能入口

当前仓库实际维护的主入口面是：

- `.agents/skills/trellis-finish-work/SKILL.md`
- `.claude/commands/trellis/finish-work.md`
- `.opencode/commands/trellis/finish-work.md`
- `.qoder/commands/trellis-finish-work.md`

另外，当前仓库还存在一个需要单独审计的 Qoder 同名兼容副本：

- `.qoder/skills/trellis-finish-work/SKILL.md`（当前仓库中已收口为与 `trellis-finish-work` 主链一致的兼容副本）

如果项目里还保留遗留 `record-session` 入口，也要一起评估；当前仓库的例子是：

- `.agents/skills/record-session/SKILL.md`（已明确标成 legacy/manual fallback，文案已切到 helper / resume / `TRELLIS_AUTO_ESCALATE_COMMAND` 语义）
- `.qoder/skills/record-session/SKILL.md`（平台遗留兼容入口，不是当前主路径；当前仓库中已同步成当前 fallback 语义）

不要把平台路径写死成单一模式。
例如 Claude / OpenCode 当前是 `commands/trellis/finish-work.md`，但 Qoder 当前实际是 `commands/trellis-finish-work.md`。

---

## 4. 修复原则

### 4.1 不要让失败只停留在 warning

错误示例：

- 只输出 `git add failed`
- 只提示“请手工提交”
- 没有恢复命令

正确做法：

- 输出一条**可直接执行**的恢复命令
- 同时输出机器可读键值：

```text
TRELLIS_AUTO_ESCALATE_COMMAND=<command>
```

这样上层执行器（Codex / Claude Code / 其他 AI CLI）才能识别并自动决定是否提权重跑。

### 4.2 区分两条链路

自动提交失败不只出现在一个地方：

1. **archive 链**
   - `task.py archive`
   - 自动提交 `.trellis/tasks`

2. **record-session / Codex helper 链**（Codex 特化 helper / fallback 路径；某些平台也可能保留遗留入口）
   - `record-session-helper.py`（当前仓库中的 Codex 特化 helper / fallback 路径）
   - `add_session.py`
   - 自动提交 `.trellis/workspace` + `.trellis/tasks`

当前仓库的实际例子是：`record-session` 已不再是主入口，但仍保留了两类残留面：

- `.agents/skills/record-session/SKILL.md`：已明确标成 legacy/manual fallback
- `.qoder/skills/record-session/SKILL.md`：属于平台遗留兼容入口，若保留则必须与共享 fallback 语义保持一致

这两条链都要有恢复方案，不能只修一边。

### 4.3 Codex helper 链优先于直接 add_session

在当前仓库里，`record-session-helper.py` 是 Codex 特化 close-out helper。
当问题发生在这条 Codex helper / fallback 链上时，推荐入口应改成：

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py ...
```

因为 helper 本身负责：

- pre-check
- 调用 `add_session.py --no-commit`
- metadata commit-only
- post-check
- resume 恢复

---

## 5. 脚本层具体修法

## 5.1 归档链：给 `task.py archive` 增加 commit-only 恢复入口

### 需要新增的行为

在 `.trellis/scripts/common/task_store.py` 中：

1. 定义只读/权限失败关键词，例如：

```python
READONLY_HINTS = (
    "Read-only file system",
    "只读文件系统",
    "Permission denied",
    "Operation not permitted",
    ".git/index.lock",
    "cannot create",
    "不能创建",
)
```

2. 在 `_auto_commit_archive(...)` 里判断 `git add` / `git commit` 的 stderr
3. 若是只读失败，则打印：

```text
python3 ./.trellis/scripts/task.py archive-commit-only <task-name>
TRELLIS_AUTO_ESCALATE_COMMAND=python3 ./.trellis/scripts/task.py archive-commit-only <task-name>
```

4. `_auto_commit_archive(...)` 不再只打印 warning，应返回成功/失败布尔值
5. `cmd_archive(...)` 根据布尔值决定返回码，推荐：
   - 成功：`0`
   - 归档成功但自动提交失败：`2`

### 为什么要有 `archive-commit-only`

因为 archive 已经发生后，再次调用完整 `archive` 不是幂等的。  
恢复路径应只重跑“元数据提交”这一步，不重复归档。

### `task.py` 需要同步修改

在 `.trellis/scripts/task.py` 中新增子命令：

```text
archive-commit-only
```

并在 help/usage 中暴露它。

---

## 5.2 会话记录链：让 `add_session.py` 在失败时自动生成 resume 状态

### 需要新增的行为

在 `.trellis/scripts/add_session.py` 中：

1. 检测 `git add` / `git commit` 的只读失败
2. 自动创建 pending state，例如：

```text
.trellis/.pending-record-session/<slug>.pending.json
```

3. 打印恢复命令：

```text
python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
TRELLIS_AUTO_ESCALATE_COMMAND=python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
```

4. 自动提交失败时，应返回非零 exit code，让调用方知道这次没有完成闭环

### 为什么不能只提示 “请手工提交”

因为手工提交会丢失：

- helper 的统一恢复路径
- 机器可读的提权重试协议
- 后续自动化/AI CLI 的可恢复性

---

## 5.3 helper 层：`record-session-helper.py` 必须输出机器可读恢复命令

在 `.trellis/scripts/workflow/record-session-helper.py` 中：

原本就有 `--resume` 能力时，还需要补上：

```text
TRELLIS_AUTO_ESCALATE_COMMAND=<resume-command>
```

推荐输出格式：

```text
⚠️  record-session metadata auto-commit 失败，检测到可能的只读/受限写入环境。
如果当前 CLI 支持提权重试，请立即用提权方式执行：
python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
TRELLIS_AUTO_ESCALATE_COMMAND=python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <pending-file>
```

这一步非常关键，因为真正的收尾默认应该经过 helper。

补充一点：`metadata-autocommit-guard.py` 当前只服务于 `record-session-helper.py` 这条链，用来做 pre-check / commit-only / post-check。
archive 链当前并不经过这个 guard，而是由 `.trellis/scripts/common/task_store.py` 自己完成 `git add` / `git commit` 和 `archive-commit-only` 恢复提示。

---

## 6. 命令/技能入口层如何改

## 6.1 `finish-work` 与 Codex helper 边界

如果你维护的是当前仓库中的 Codex 特化 close-out helper 链，推荐的 session journal 步骤是：

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary"
```

不要把上面的 Codex helper 路径误写成所有 CLI 的统一默认 `finish-work` 路径。

当前仓库的边界应明确为：

- Claude / OpenCode / Qoder / Kiro 的默认 `finish-work` 入口仍以 `add_session.py` 为主
- Codex 特化 helper / fallback 链才以 `record-session-helper.py` 为主

并在文案里明确写：

- 如果 helper 输出了 `TRELLIS_AUTO_ESCALATE_COMMAND=...`
- 当前 CLI 支持提权
- 那么**应立即提权重跑打印出的命令**

不要把“手工提交 `.trellis`”写成默认建议。

如果你维护的是当前仓库这一套入口面，至少要同时同步当前主入口：

- `.agents/skills/trellis-finish-work/SKILL.md`
- `.claude/commands/trellis/finish-work.md`
- `.opencode/commands/trellis/finish-work.md`
- `.qoder/commands/trellis-finish-work.md`

如果平台目录里还残留同名 skill 镜像或旧副本，也要一起审计或删除。当前仓库的例子是：

- `.qoder/skills/trellis-finish-work/SKILL.md`：当前仓库中已收口为与共享 `trellis-finish-work` 主链一致；如果继续保留，就必须维持这种一致性

## 6.2 `record-session` fallback（遗留入口，不是主路径）

`record-session` 已不再是当前推荐主入口。当前仓库中，它更适合被视为 legacy / fallback 入口；若走 Codex 特化 helper 链，可通过 `record-session-helper.py` 获得额外恢复能力。

但“已退役”不等于“仓库里一定已经没有残留入口”。当前仓库就还保留着：

- `.agents/skills/record-session/SKILL.md`
- `.qoder/skills/record-session/SKILL.md`

其中：

- `.agents/skills/record-session/SKILL.md` 已经明确标成 legacy/manual fallback
- `.qoder/skills/record-session/SKILL.md` 当前仓库中已明确标成 legacy/fallback，并与共享 `record-session` fallback 语义保持一致；后续不得再回漂

因此，如果你的项目仍保留独立 `record-session` 入口，至少要二选一：

1. 删除它，并统一引导到 `finish-work`
2. 保留它，但明确标成 legacy / fallback，并把文案同步成当前真实语义

---

## 7. 其他项目可以直接照抄的最小改动包

如果你只是想把这套机制移植到另一个 Trellis 项目，最小必改项是：

1. `.trellis/scripts/common/task_store.py`
2. `.trellis/scripts/task.py`
3. `.trellis/scripts/add_session.py`
4. `.trellis/scripts/workflow/record-session-helper.py`
5. `.trellis/scripts/workflow/metadata-autocommit-guard.py`（如果你采用 helper 的 pre/post check + commit-only 链）
6. 一份收尾入口的源文案，例如 `.agents/skills/trellis-finish-work/SKILL.md`
7. 你正在使用的平台命令 / 技能入口：
   - `.claude/commands/trellis/finish-work.md`
   - `.opencode/commands/trellis/finish-work.md`
   - `.qoder/commands/trellis-finish-work.md`

如果项目里还存在平台私有 skill 镜像或历史副本，也把它们列入这次迁移范围并逐个核实是否漂移：

- 例如 `.qoder/skills/trellis-finish-work/SKILL.md`

如果项目里还残留独立 `record-session` 入口，也把它列入这次迁移范围：

- 例如 `.agents/skills/record-session/SKILL.md`
- 例如 `.qoder/skills/record-session/SKILL.md`

如果项目没有：

- `record-session-helper.py`
- `metadata-autocommit-guard.py`

那就不能只照搬入口文案，必须连 helper 链一起移植。

---

## 8. 推荐验证步骤

### 8.1 脚本语法

```bash
python3 -m py_compile \
  .trellis/scripts/add_session.py \
  .trellis/scripts/workflow/record-session-helper.py \
  .trellis/scripts/workflow/metadata-autocommit-guard.py \
  .trellis/scripts/common/task_store.py \
  .trellis/scripts/task.py
```

### 8.2 归档自动提交测试

如果项目已有 `task_store` 单测，补一个只读失败用例；没有的话至少要覆盖：

- archive 正常自动提交
- 无变更时跳过自动提交
- 只读失败时输出：
  - `archive-commit-only`
  - `TRELLIS_AUTO_ESCALATE_COMMAND=...`

### 8.3 record-session helper 恢复链（Codex 特化 helper / fallback）

人工演练至少验证：

1. `record-session-helper.py` 正常闭环
2. 伪造 `git add` / `git commit` 失败时：
   - 会生成 pending state
   - 会打印 `--resume`
   - 会打印 `TRELLIS_AUTO_ESCALATE_COMMAND=...`

### 8.4 文案一致性

检查下面这些入口不再直接鼓励手工 commit：

```bash
rg -n "Please commit \\.trellis|手工提交|record-session-helper.py --resume|archive-commit-only|TRELLIS_AUTO_ESCALATE_COMMAND" \
  .agents/skills .claude/commands .opencode/commands .qoder/commands .qoder/skills .trellis/scripts
```

### 8.5 遗留入口审计

如果项目里还保留独立 `record-session` 入口，至少确认以下两件事：

1. 它是否被明确标成 legacy / fallback，而不是继续伪装成主路径
2. 它描述的 close-out 顺序是否仍然与当前主流程冲突
3. 是否还存在同名 `finish-work` skill 副本，但内容早已漂移成别的语义

---

## 9. Good / Base / Bad

### Good

- 自动提交成功时静默闭环
- 自动提交失败时打印机器可读恢复命令
- Codex 特化 helper / fallback 路径走 helper
- archive 与 record-session / Codex helper 两条链都有恢复路径
- 如果保留遗留 `record-session` 入口，会明确标记为 legacy / fallback

### Base

- 失败时至少能打印 `--resume` 命令
- 有 helper，但没有 `TRELLIS_AUTO_ESCALATE_COMMAND`

这能人工恢复，但不利于上层 CLI 自动提权。

### Bad

- 只打印 warning，不给恢复命令
- 把 Codex 特化 helper 路径误写成所有 CLI 的统一 `finish-work` 默认入口
- 只有 record-session / Codex helper 链有恢复路径，archive 没有
- 强制要求用户手工 `git add .trellis && git commit`
- 口头上说 `record-session` 已退役，但仓库里仍保留未标注的旧入口

---

## 10. Wrong vs Correct

### Wrong

```python
if add_result.returncode != 0:
    print("[WARN] git add failed")
    print("[WARN] Please commit .trellis/ changes manually")
    return
```

问题：

- 不能区分是否为只读/权限失败
- 没有恢复命令
- 上层 CLI 无法自动提权重跑

### Correct

```python
if add_result.returncode != 0:
    combined = (add_result.stdout or "") + "\n" + (add_result.stderr or "")
    if detect_readonly_failure(combined):
        state_file = ensure_resume_artifacts(...)
        print_resume_guidance(repo_root, state_file)
    return False
```

并且 `print_resume_guidance(...)` 必须输出：

```text
TRELLIS_AUTO_ESCALATE_COMMAND=python3 ./.trellis/scripts/workflow/record-session-helper.py --resume <file>
```

---

## 11. 最终建议

如果其他项目也遇到“`finish-work` 已经执行到最后，但 `.trellis` 元数据自动提交在只读环境下失败”的情况，不要只修一行 warning。

正确修法是同时覆盖：

- `archive` 自动提交链
- `record-session` / Codex helper 自动提交链
- helper 恢复链
- `finish-work` 默认入口文案
- 仍然留在仓库里的遗留 `record-session` 入口

只有把这些层一起改完，才算真正解决问题。
