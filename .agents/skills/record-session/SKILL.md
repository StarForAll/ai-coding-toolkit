---
name: record-session
description: "Record work progress after human has tested and committed code"
---

[!] **Prerequisite**: This skill should only be used AFTER the human has tested and committed the code.

**Do NOT run `git commit` directly** — the scripts below handle their own commits for `.trellis/` metadata. You only need to read git history (`git log`, `git status`, `git diff`) and run the Python scripts.

**Postcondition is mandatory**: if `task.py archive` or `add_session.py` modified `.trellis/tasks` or `.trellis/workspace`, those metadata changes must be auto-committed by the scripts. Do not stop at “session added successfully” or “task archived” — verify the `.trellis/` metadata is actually committed.

---

## Record Work Progress

### Step 1: Get Context & Check Tasks

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

[!] Archive tasks whose work is **actually done** — judge by work status, not the `status` field in task.json:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

After archive:

```bash
git status --short .trellis/tasks
```

- Expected: clean output
- If `.trellis/tasks` is still dirty, treat archive auto-commit as failed and resolve it before continuing

### Step 2: One-Click Add Session

```bash
# Method 1: Simple parameters
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"

# Method 2: Pass detailed content via stdin
cat << 'EOF' | python3 ./.trellis/scripts/add_session.py --stdin --title "Title" --commit "hash"
| Feature | Description |
|---------|-------------|
| New API | Added user authentication endpoint |
| Frontend | Updated login form |

**Updated Files**:
- `packages/api/modules/auth/router.ts`
- `apps/web/modules/auth/components/login-form.tsx`
EOF
```

After session recording:

```bash
git status --short .trellis/workspace .trellis/tasks
```

- Expected: clean output
- If `.trellis/workspace` or `.trellis/tasks` is still dirty, treat record-session as incomplete
- Do not claim “recorded” until the metadata auto-commit has actually happened

**Auto-completes**:
- [OK] Appends session to journal-N.md
- [OK] Auto-detects line count, creates new file if >2000 lines
- [OK] Updates index.md (Total Sessions +1, Last Active, line stats, history)
- [OK] Auto-commits `.trellis/workspace` and `.trellis/tasks` changes; command should be treated as failed if this step does not actually happen

---

## Script Command Reference

| Command | Purpose |
|---------|---------|
| `python3 ./.trellis/scripts/get_context.py --mode record` | Get context for record-session |
| `python3 ./.trellis/scripts/add_session.py --title "..." --commit "..."` | **One-click add session (recommended)** |
| `python3 ./.trellis/scripts/task.py archive <name>` | Archive completed task (auto-commits) |
| `python3 ./.trellis/scripts/task.py list` | List active tasks |
