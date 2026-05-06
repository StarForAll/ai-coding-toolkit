# 自动提交恢复链当前实现摘要

## 目标文档

- `docs/Trellis自动提交失败恢复与提权修复指南.md`
- 当前内容整体机制方向正确，但部分“当前项目实际使用情况”已落后于仓库现状。

## 当前脚本实现

### archive 链

- `.trellis/scripts/common/task_store.py`
  - 存在 `READONLY_HINTS`
  - `_print_archive_commit_resume_guidance()` 会输出：
    - `python3 ./.trellis/scripts/task.py archive-commit-only <task>`
    - `TRELLIS_AUTO_ESCALATE_COMMAND=...`
- `.trellis/scripts/task.py`
  - usage 已公开 `archive-commit-only`

### record-session / finish-work 链

- `.trellis/scripts/add_session.py`
  - `git add` / `git commit` 失败时会检测只读/权限错误
  - 会创建 `.trellis/.pending-record-session/<slug>.pending.json`
  - 会打印 `record-session-helper.py --resume ...` 和 `TRELLIS_AUTO_ESCALATE_COMMAND=...`
- `.trellis/scripts/workflow/record-session-helper.py`
  - 正常链路：pre-check → `add_session.py --no-commit` → `metadata-autocommit-guard.py` commit-only → post-check
  - 失败时会创建 pending state 并打印 `--resume` / `TRELLIS_AUTO_ESCALATE_COMMAND=...`
- `.trellis/scripts/workflow/metadata-autocommit-guard.py`
  - 仅负责 `record-session` 模式的 pre/post check 与 metadata commit-only
  - 不参与 archive 链

## 当前入口面

- 活跃 `finish-work` 入口：
  - `.agents/skills/trellis-finish-work/SKILL.md`
  - `.claude/commands/trellis/finish-work.md`
  - `.opencode/commands/trellis/finish-work.md`
  - `.qoder/commands/trellis-finish-work.md`
- 需要单独审计的漂移/遗留入口：
  - `.qoder/skills/trellis-finish-work/SKILL.md` 仍存在，但 frontmatter 为 `name: finish-work`，正文其实是旧的 pre-commit checklist；不能作为当前 `finish-work` 收尾入口
  - `.agents/skills/record-session/SKILL.md` 已明确标成 legacy/manual fallback，语义已对齐 helper / resume / `TRELLIS_AUTO_ESCALATE_COMMAND`
  - `.qoder/skills/record-session/SKILL.md` 仍存在，且仍描述旧的“record-session 先于 archive”顺序，只提 `--resume` 命令，未对齐当前主链文案

## 与目标文档相关的主要同步点

1. 当前项目平台面不只 `.claude` / `.opencode`，还包含 `.qoder`。
2. Qoder 当前可直接证实的主入口是 `.qoder/commands/trellis-finish-work.md`；`.qoder/skills/trellis-finish-work/SKILL.md` 是漂移旧副本，文档不能继续把它列成当前推荐主路径。
3. `record-session` 不是仓库当前主路径，但仓库里同时保留了两类不同状态的残留入口：`.agents/skills/record-session/SKILL.md` 是已标注的 legacy/manual fallback，`.qoder/skills/record-session/SKILL.md` 则仍保留旧 close-out 顺序。
4. `metadata-autocommit-guard.py` 是 record-session helper 子链的一部分，不应让读者误以为 archive 链也依赖它。
5. 验证命令应与当前仓库命令形式一致，优先使用具体脚本路径。
