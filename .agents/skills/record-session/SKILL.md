---
name: record-session
description: "Legacy/manual fallback for recording completed work progress to .trellis/workspace/ journal files after human testing and commit. Prefer `trellis-finish-work` for the normal close-out path; use this only when you specifically need to run `add_session.py` manually."
---

[!] **Legacy/manual fallback**: the normal `0.5` close-out path is `trellis-finish-work`.
Use this skill only when:

- the user specifically asks to run `record-session` manually
- you intentionally want a manual `add_session.py` path outside the normal `finish-work`

[!] **Platform boundary**: this repository now treats `finish-work` as the
standard close-out path. Direct `add_session.py` use remains the underlying
session-recording step in that flow and a manual fallback when explicitly
needed. Do not reintroduce helper-specific recovery semantics here.

[!] **Prerequisite**: This skill should only be used AFTER the human has tested and committed the code.

**Do NOT run `git commit` directly** — the scripts below handle their own commits for `.trellis/` metadata. You only need to read git history (`git log`, `git status`, `git diff`) and run the Python scripts.

**Manual fallback order**: archive first, then `add_session.py`, matching Trellis native finish-work behavior.

---

## Record Work Progress

### Step 1: Get Context & Check Tasks

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

[!] In this stage, first **judge** which tasks are actually done and should be archived:
- Code committed? → Archive it (don't wait for PR)
- All acceptance criteria met? → Archive it
- Don't skip archiving just because `status` still says `planning` or `in_progress`

### Step 2: Archive Completed Task

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

Recommended post-check:

```bash
python3 ./.trellis/scripts/task.py current --source
```

Expected output: no active task for the current session. If the archived task still appears, the close-out is not complete yet.

### Step 3: Record Session Journal

```bash
python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "hash1,hash2" \
  --summary "Brief summary of what was done"
```

---

## Script Command Reference

| Command | Purpose |
|---------|---------|
| `python3 ./.trellis/scripts/get_context.py --mode record` | Get context for record-session |
| `python3 ./.trellis/scripts/task.py archive <name>` | Archive completed task first |
| `python3 ./.trellis/scripts/add_session.py --title "..." --commit "..."` | Manual session record path |
| `python3 ./.trellis/scripts/task.py list` | List active tasks |
