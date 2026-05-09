---
name: record-session
description: "Legacy/manual fallback for recording completed work progress to .trellis/workspace/ journal files after human testing and commit. Prefer `trellis-finish-work` for the normal close-out path; use this only when you specifically need the helper flow or resume a previously interrupted metadata closure."
---

[!] **Legacy/manual fallback**: the normal `0.5` close-out path is `trellis-finish-work`.
Use this skill only when:

- you explicitly need `record-session-helper.py`
- you are resuming a previously interrupted metadata closure
- the user specifically asks to run `record-session` manually

[!] **Platform boundary**: in this repository, `record-session-helper.py` is a
Codex-specific helper / recovery path. Default non-Codex `finish-work`
entrypoints continue to use `add_session.py`; use the helper examples below
only when you explicitly need helper / resume semantics.

[!] **Prerequisite**: This skill should only be used AFTER the human has tested and committed the code.

**Do NOT run `git commit` directly** — the scripts below handle their own commits for `.trellis/` metadata. You only need to read git history (`git log`, `git status`, `git diff`) and run the Python scripts.

**Manual fallback order**: `record-session` first, then `archive`.

- `record-session` needs the current task context
- `archive` moves task metadata and clears the session-scoped active task pointer
- If you archive first, `record-session-helper.py` may be blocked by metadata closure pre-checks because `.trellis/tasks` is no longer clean

---

## Record Work Progress

### Step 1: Get Context & Check Tasks

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

[!] In this stage, first **judge** which tasks are actually done and should be archived, but do **not** archive before the helper runs:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

### Step 2: One-Click Add Session (helper / recovery path)

```bash
# Method 1: Simple parameters
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"

# Method 2: Pass detailed content via stdin
cat << 'EOF' | python3 ./.trellis/scripts/workflow/record-session-helper.py --stdin --title "Title" --commit "hash"
| Feature | Description |
|---------|-------------|
| New API | Added user authentication endpoint |
| Frontend | Updated login form |

**Updated Files**:
- `packages/api/modules/auth/router.ts`
- `apps/web/modules/auth/components/login-form.tsx`
EOF
```

**Auto-completes**:
- [OK] Appends session to journal-N.md
- [OK] Auto-detects line count, creates new file if >2000 lines
- [OK] Auto-detects Branch context (`--branch` override; otherwise Branch = task.json -> current git branch; missing values are omitted gracefully)
- [OK] Updates index.md (Total Sessions +1, Last Active, line stats, history)
- [OK] Runs metadata closure checks before and after session write
- [OK] Auto-commits .trellis/workspace and .trellis/tasks changes in helper commit-only mode
- [OK] If metadata commit fails in read-only/restricted env, prints `TRELLIS_AUTO_ESCALATE_COMMAND=...` plus a `--resume` command; if the current CLI supports privileged retry, rerun it with elevated permissions immediately

If you only need the generic non-Codex manual record path and do not need the
helper's recovery semantics, use:

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"
```

### Step 3: Archive Completed Task

Only after `record-session-helper.py` succeeds:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

Recommended post-check:

```bash
python3 ./.trellis/scripts/task.py current --source
```

Expected output: no active task for the current session. If the archived task still appears, the close-out is not complete yet.

---

## Script Command Reference

| Command | Purpose |
|---------|---------|
| `python3 ./.trellis/scripts/get_context.py --mode record` | Get context for record-session |
| `python3 ./.trellis/scripts/workflow/record-session-helper.py --title "..." --commit "..."` | **One-click add session (recommended, branch auto-complete, metadata closure aware)** |
| `python3 ./.trellis/scripts/add_session.py --title "..." --commit "..."` | Generic non-Codex manual session record path |
| `python3 ./.trellis/scripts/task.py archive <name>` | Archive completed task (**only after the helper succeeds**) |
| `python3 ./.trellis/scripts/task.py list` | List active tasks |
