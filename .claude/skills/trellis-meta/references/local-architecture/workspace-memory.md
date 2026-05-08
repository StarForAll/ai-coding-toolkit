# Local Workspace Memory System

`.trellis/workspace/` stores cross-session memory. Its purpose is to let AI and humans understand what happened before across different windows and different days.

## Directory Structure

```text
.trellis/workspace/
├── index.md
└── <developer>/
    ├── index.md
    ├── journal-1.md
    └── journal-2.md
```

| File | Purpose |
| --- | --- |
| `.trellis/.developer` | Current developer identity. |
| `.trellis/workspace/index.md` | Global workspace overview. |
| `.trellis/workspace/<developer>/index.md` | Session index for a developer. |
| `.trellis/workspace/<developer>/journal-N.md` | Session journal. |

## Developer Identity

Run this the first time:

```bash
python3 ./.trellis/scripts/init_developer.py <name>
```

This creates `.trellis/.developer` and the corresponding workspace directory. The AI should not change developer identity casually; if the identity is wrong, first confirm who is using the current project.

## Journal

`journal-N.md` records completed or partially completed work from each session. By default, each journal holds about 2000 lines; after that it rotates to the next file.

Common workflow for recording a session:

```bash
# Step 1: Archive the completed task
python3 ./.trellis/scripts/task.py archive <task-name>

# Step 2: Record the session journal
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session title" \
  --summary "What changed" \
  --commit "abc1234"
```

`record-session-helper.py` performs metadata closure pre-checks, calls `add_session.py` internally, and auto-commits `.trellis/workspace` and `.trellis/tasks` metadata changes. If it reports a failure in a read-only environment, follow the `TRELLIS_AUTO_ESCALATE_COMMAND` guidance it prints.

## Relationship Between Workspace Memory And Tasks

| System | What it stores |
| --- | --- |
| `.trellis/tasks/` | Requirements, design, research, and state for a specific task. |
| `.trellis/workspace/` | Work records across tasks and sessions. |
| `.trellis/spec/` | Engineering knowledge preserved as long-term conventions. |

If information is only useful for the current task, put it in the task directory.  
If information describes what happened in the current session, put it in the workspace journal.  
If information should be followed every time code is written in the future, put it in spec.

## Local Customization Points

| Need | Edit location |
| --- | --- |
| Change maximum journal lines | `max_journal_lines` in `.trellis/config.yaml`. |
| Change session auto-commit message | `session_commit_message` in `.trellis/config.yaml`. |
| Change session content format | `.trellis/scripts/add_session.py`. |
| Change how workspace is displayed in context | `.trellis/scripts/common/session_context.py`. |

## AI Usage Rules

The AI should not treat workspace as the only source of truth. When resuming a task, read the current task first, then use workspace for background. After a task is complete, record important process notes in workspace; if long-term rules emerged, update spec.
