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

### Step 3: Verify clean state

```bash
git status --short .trellis/tasks .trellis/.current-task
```

Expected output: empty. If still dirty, fix the metadata issues before considering the close-out complete.
