## Record-Session Metadata Closure `[AI]`

Use `/trellis:record-session` here only for the **final close-out of the current completed task**.

Before continuing:

- Archive the current completed task explicitly:

```bash
python3 ./.trellis/scripts/task.py archive <current-task>
```

- Verify task metadata is already closed out:

```bash
git status --short .trellis/tasks .trellis/.current-task
```

Expected output: empty.

If `.trellis/tasks` or `.trellis/.current-task` is still dirty, stop here and fix archive / metadata issues before recording the session.

For the final session record, use the workflow helper instead of calling `add_session.py` directly:

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"
```

This helper runs the metadata closure checks before and after `add_session.py`.
