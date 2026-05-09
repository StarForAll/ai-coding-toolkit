---
name: trellis-finish-work
description: "Wrap up the current session in the Codex repo-local close-out path: record the session via `record-session-helper.py`, then archive the active task (and any other completed-but-unarchived tasks the user wants to clean up). Use when done coding and ready to end the session."
---

# Finish Work

Wrap up the current session: archive the active task (and any other completed-but-unarchived tasks the user wants to clean up) and record the session journal. Code commits are NOT done here — those happen in workflow Phase 3.4 before you invoke this command.

## Step 1: Survey current state

```bash
python3 ./.trellis/scripts/get_context.py --mode record
```

This prints:

- **My active tasks** — review whether any besides the current one are actually done (code merged, AC met) and should be archived this round.
- **Git status** — quick visual on what's dirty.
- **Recent commits** — you'll need their hashes in Step 4 for `--commit`.

If `--mode record` surfaces other completed tasks not tied to the current session, surface them to the user with a one-shot confirmation: "These N tasks look done — archive them too in this round? [y/N]". Default is no; the current active task is always archived in Step 4 regardless.

## Step 2: Sanity check — classify dirty paths

Run:

```bash
git status --porcelain
```

Filter out paths under `.trellis/workspace/` and `.trellis/tasks/` — those are managed by `record-session-helper.py` and `task.py archive` metadata commits and will appear dirty as part of this skill's own work.

For each remaining dirty path, decide whether it belongs to **the current task** or to **other parallel work** (e.g., another terminal window editing the same repo). Heuristics:

- Paths referenced in the current task's `prd.md` / `implement.jsonl` / `check.jsonl` → current task
- Paths in code areas matching the task's stated scope, or that you remember editing this session → current task
- Paths in unrelated areas you have no recollection of touching this session → other parallel work

Then route:

- **Any remaining path looks like current-task work** — bail out with:
  > "Working tree has uncommitted code changes from this task: `<list>`. Return to workflow Phase 3.4 to commit them before running ``finish-work` (Trellis command)`."

  Do NOT run `git commit` here. Do NOT prompt the user to commit. The user goes back to Phase 3.4 and the AI drives the batched commit there.
- **All remaining paths look unrelated** (other parallel-window work) — report them once and continue to Step 3:
  > "FYI, dirty files outside this task's scope — leaving them for the other window: `<list>`."
- **Genuinely unsure** — ask the user once: "Are `<list>` this task's work I forgot to commit, or another window's? (commit / ignore)" — then route per their answer.

## Step 3: Record session journal via helper

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
    --title "Session Title" \
    --commit "hash1,hash2" \
    --summary "Brief summary"
```

Use the work-commit hashes produced in Phase 3.4 (visible in Step 1's Recent commits list, or via git log --oneline) for --commit.

  The helper:

  - appends the session to the current journal
  - updates workspace index metadata
  - performs Codex-aware metadata closure checks
  - attempts the metadata commit in helper commit-only mode
  - prints TRELLIS_AUTO_ESCALATE_COMMAND=... if the metadata commit needs privileged retry

  If the helper fails, do NOT archive yet.

## Step 4: Archive task(s)

```bash
python3 ./.trellis/scripts/task.py archive <task-name>
```

Only after record-session-helper.py succeeds. At minimum: the current active task (if any). Plus any extra tasks the user confirmed in Step
  1. Each archive produces a chore(task): archive ... commit via the script's auto-commit.

  If there is no active task and the user did not confirm any cleanup archives, skip this step.

  Final git log order: <work commits from 3.4> → chore: record journal → chore(task): archive ... (one or more).
