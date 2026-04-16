## Record-Session Metadata Closure `[AI]`

Use `/trellis:record-session` here only for the **final close-out of the current completed task**.

**Close-out order: record-session first, then archive.** The session record needs the current task context; archive clears `.current-task`, so it must come after.

### Step 1: Record the session

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"
```

This helper runs the metadata closure checks before and after `add_session.py`.
If the helper returns non-zero, do NOT proceed to archive — fix the failure first.

### Step 2: Archive the completed task

```bash
python3 ./.trellis/scripts/task.py archive <current-task>
```

> 注意：这里的 `archive` 仍直接调用目标项目 Trellis 基线 `task.py`。若目标项目不是当前最新 Trellis 基线，可能还会继承旧基线中的 archive metadata auto-commit 问题；此时应先升级 Trellis，再继续使用当前 workflow 的 close-out 链路。

### Step 3: Verify clean state

```bash
git status --short .trellis/tasks .trellis/.current-task
```

Expected output: empty. If still dirty, fix the metadata issues before considering the close-out complete.
