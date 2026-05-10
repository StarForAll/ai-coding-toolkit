# Trellis 元数据自动提交失败恢复指南

> 适用场景：某个项目已经在使用 Trellis，`finish-work`、`task.py archive` 或 `add_session.py` 在最后一步尝试自动提交 `.trellis/` 元数据，但因为只读文件系统、沙箱、权限限制、`.git/index.lock` 无法创建等原因失败。

这份文档是一份**可迁移到其他 Trellis 项目的独立修复指南**。  
如果其他项目出现同类问题，可以按本文思路修改它自己的 `.trellis/` 运行时脚本与收尾入口。

下文里提到“当前仓库实际使用情况”时，均以本仓库 **2026-05-09** 的真实状态为准：

- 主入口链：`.agents/skills/trellis-finish-work/SKILL.md`
- Claude / OpenCode 命令入口：`.claude/commands/trellis/finish-work.md`、`.opencode/commands/trellis/finish-work.md`
- Qoder 当前命令入口：`.qoder/commands/trellis-finish-work.md`
- 当前仓库的 close-out 已统一回到 **Trellis 原生 `task.py archive` + `add_session.py`**
- `.agents/skills/record-session/SKILL.md` 与 `.qoder/skills/record-session/SKILL.md` 仍保留，但已明确标成 legacy/manual fallback

---

## 1. 问题定义

典型现象：

- `python3 ./.trellis/scripts/task.py archive <task>` 已执行归档，但自动提交失败
- `python3 ./.trellis/scripts/add_session.py ...` 已写 journal / index，但自动提交失败
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

那么说明这个项目的 Trellis 运行时只具备“失败提示”，**没有结构化恢复协议**。

---

## 2. 修复目标

把当前项目的 Trellis 自动提交链路改成下面的行为：

1. 自动提交正常时：照常完成闭环
2. 自动提交因只读/权限失败时：
   - 明确识别“这是只读/受限写入”
   - 生成**机器可读**的恢复命令
   - 优先建议当前 CLI 用提权方式立即重试
   - 仅当当前环境确实不支持提权时，才退回手工提交

目标不是“避免所有失败”，而是把失败从模糊 warning 提升为可恢复协议。

---

## 3. 当前真实收尾模型

当前仓库与目标项目的收尾顺序应是：

1. `python3 ./.trellis/scripts/task.py archive <task>`
2. `python3 ./.trellis/scripts/add_session.py --title ... --commit ... --summary ...`

也就是说：

- **先 archive**
- **再 add_session**

不要再把任何 helper 脚本当作默认收尾入口。

---

## 4. 需要修改的文件

### 4.1 归档自动提交链

- `.trellis/scripts/common/task_store.py`
- `.trellis/scripts/task.py`

### 4.2 会话记录自动提交链

- `.trellis/scripts/add_session.py`

### 4.3 用户入口文档 / 技能入口

当前仓库实际维护的主入口面：

- `.agents/skills/trellis-finish-work/SKILL.md`
- `.claude/commands/trellis/finish-work.md`
- `.opencode/commands/trellis/finish-work.md`
- `.qoder/commands/trellis-finish-work.md`
- `.qoder/skills/trellis-finish-work/SKILL.md`
- `.kiro/skills/trellis-finish-work/SKILL.md`

如果项目里还保留独立 `record-session` 入口，也要一起评估：

- `.agents/skills/record-session/SKILL.md`
- `.qoder/skills/record-session/SKILL.md`

它们应被明确标成 **legacy/manual fallback**，不能再伪装成主路径。

---

## 5. 修复原则

### 5.1 不要让失败只停留在 warning

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

这样上层执行器（Codex / Claude Code / 其他 AI CLI）才能识别并决定是否提权重跑。

### 5.2 只保留两条恢复链

自动提交失败现在只需要覆盖两条链：

1. **archive 链**
   - `task.py archive`
   - 自动提交 `.trellis/tasks`

2. **session 记录链**
   - `add_session.py`
   - 自动提交 `.trellis/workspace` + `.trellis/tasks`

不要再为 session 记录额外发明第三条 helper-based close-out 主链。

---

## 6. 脚本层具体修法

### 6.1 归档链：给 `task.py archive` 保留 commit-only 恢复入口

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

4. `_auto_commit_archive(...)` 返回成功/失败布尔值
5. `cmd_archive(...)` 根据布尔值决定返回码

### 6.2 为什么要有 `archive-commit-only`

因为 archive 已经发生后，再次调用完整 `archive` 不是幂等的。  
恢复路径应只重跑“元数据提交”这一步，不重复归档。

### 6.3 `task.py` 需要同步修改

在 `.trellis/scripts/task.py` 中保留或新增子命令：

```text
archive-commit-only
```

并在 help/usage 中暴露它。

---

## 7. 会话记录链：让 `add_session.py` 在失败时具备结构化恢复

在 `.trellis/scripts/add_session.py` 中：

1. 检测 `git add` / `git commit` 的只读失败
2. 如果有 resume / pending 机制，就输出机器可读恢复命令
3. 自动提交失败时返回非零 exit code，让调用方知道这次没有完成闭环

推荐输出格式：

```text
⚠️  session metadata auto-commit 失败，检测到可能的只读/受限写入环境。
如果当前 CLI 支持提权重试，请立即用提权方式执行：
python3 ./.trellis/scripts/add_session.py ...
TRELLIS_AUTO_ESCALATE_COMMAND=<command>
```

如果项目实现里没有 `add_session.py` 级别的 resume / pending 机制，也至少要做到：

- 明确区分这是只读/权限失败
- 输出下一步建议
- 不要只剩“请手工提交”

---

## 8. 命令/技能入口层怎么改

### 8.1 `finish-work` 入口

当前真实入口应描述为：

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
python3 ./.trellis/scripts/add_session.py --title "..." --commit "..." --summary "..."
```

不要再写：

```bash
<custom-helper-based-close-out-command>
```

### 8.2 `record-session` 入口

`record-session` 已不再是当前推荐主入口。  
如果保留它，至少要二选一：

1. 删除它，并统一引导到 `finish-work`
2. 保留它，但明确标成 legacy / fallback，并把文案同步成当前真实语义

当前仓库的正确语义是：

- `record-session` = 手动 fallback
- 默认路径 = `finish-work`

---

## 9. 可迁移的最小改动包

如果你只是想把这套机制移植到另一个 Trellis 项目，最小必改项是：

1. `.trellis/scripts/common/task_store.py`
2. `.trellis/scripts/task.py`
3. `.trellis/scripts/add_session.py`
4. 一份收尾入口源文案，例如 `.agents/skills/trellis-finish-work/SKILL.md`
5. 你正在使用的平台命令 / 技能入口

如果项目里仍保留独立 `record-session` 入口，也把它列入迁移范围：

- `.agents/skills/record-session/SKILL.md`
- `.qoder/skills/record-session/SKILL.md`

---

## 10. 推荐验证步骤

### 10.1 脚本语法

```bash
python3 -m py_compile \
  .trellis/scripts/add_session.py \
  .trellis/scripts/common/task_store.py \
  .trellis/scripts/task.py
```

### 10.2 归档自动提交测试

至少覆盖：

- archive 正常自动提交
- 无变更时跳过自动提交
- 只读失败时输出：
  - `archive-commit-only`
  - `TRELLIS_AUTO_ESCALATE_COMMAND=...`

### 10.3 会话记录测试

至少验证：

1. `add_session.py` 正常闭环
2. 伪造 `git add` / `git commit` 失败时：
   - 返回非零
   - 输出明确的恢复/提权指引

### 10.4 文案一致性

检查下面这些入口不再鼓励手工 commit，也不再指向已删除 helper：

```bash
rg -n "Please commit \\.trellis|手工提交|TRELLIS_AUTO_ESCALATE_COMMAND" \
  .agents/skills .claude/commands .opencode/commands .qoder/commands .qoder/skills .trellis/scripts
```

---

## 11. Good / Base / Bad

### Good

- 自动提交成功时静默闭环
- 自动提交失败时打印机器可读恢复命令
- `finish-work` 明确使用 Trellis 原生 `archive + add_session.py`
- archive 与 session 记录两条链都有恢复策略
- 遗留 `record-session` 入口被明确标记为 legacy / fallback

### Base

- 失败时至少能打印提权或恢复命令
- 即使没有完整 resume 机制，也不会只剩一句“请手工提交”

### Bad

- 只打印 warning，不给恢复命令
- 把已删除 helper 路径继续写成主入口
- 只有 archive 链有恢复路径，`add_session.py` 没有
- 强制要求用户手工 `git add .trellis && git commit`
- 口头上说 `record-session` 已退役，但仓库里仍保留未标注的旧入口

---

## 12. 最终建议

如果其他项目也遇到“`finish-work` 已经执行到最后，但 `.trellis` 元数据自动提交在只读环境下失败”的情况，不要只修一行 warning。

正确修法是同时覆盖：

- `archive` 自动提交链
- `add_session.py` 会话记录链
- `finish-work` 默认入口文案
- 仍然留在仓库里的遗留 `record-session` 入口

只有把这些层一起改完，才算真正解决问题。
