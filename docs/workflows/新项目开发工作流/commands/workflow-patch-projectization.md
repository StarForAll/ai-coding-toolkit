## Development Process

<!-- workflow-projectization-patch -->

### Task Development Flow

```text
1. Create or select task
   --> python3 ./.trellis/scripts/task.py create "<title>" --slug <name> or list

2. Start task (mark as current)
   --> python3 ./.trellis/scripts/task.py start <name>
   --> Writes .trellis/.current-task; future sessions and hooks can re-enter the current task

3. Write code according to guidelines
   --> Read .trellis/spec/ docs relevant to your task
   --> For cross-layer: read .trellis/spec/guides/

4. Self-test
   --> Run the project's frozen verification commands when scaffold exists (see spec docs)
   --> Manual feature testing

5. Commit code
   --> git add <files>
   --> git commit -m "type(scope): description"
       Format: feat/fix/docs/refactor/test/chore

6. Final close-out
   --> python3 ./.trellis/scripts/workflow/record-session-helper.py --title "Title" --commit "hash"
   --> python3 ./.trellis/scripts/task.py archive <task-name>
   --> record-session runs first, then archive
```

`python3 ./.trellis/scripts/task.py finish` remains available when you intentionally need to clear `.trellis/.current-task` without archiving a completed task. Do not use it as a substitute for final close-out.

For workflows that split work into a parent coordination task plus child execution tasks:

- freeze the project test-first baseline once in design/spec docs
- select one concrete child task before entering test-first or implementation
- completing the current child task does not automatically authorize the next child task
- after a child task is completed or archived, update the parent coordinator records in the same round so the latest completed frontier, pending frontier, and next selectable child task stay synchronized
- the next child task may start only after the human explicitly names or approves that task in the current round
- create and verify the test gate for that child task only
- complete that child task's test gate before entering its concrete implementation work
- do not pre-write one-shot tests for the entire plan from the parent coordination task
- do not run sibling child tasks in parallel; finish the current child task before switching to the next one

### Code Quality Checklist

**Must pass before commit**:

- [OK] Lint checks pass (project-specific command)
- [OK] Type checks pass (if applicable)
- [OK] Manual feature testing passes

**Project-specific checks**:

- Run the project's frozen verification matrix when the scaffold exists (see `.trellis/spec/` quality guidelines)
- If a change is Trellis-related, sync all linked current-entry hidden directories instead of updating `.trellis/` alone:
  - `.trellis/`
  - `.claude/`
  - `.opencode/`
  - `.agents/skills/`
  - `.codex/`
- Keep each directory in its own format and command style.

---

## Session End

### One-Click Session Recording

After the human has tested and committed the code, run the workflow helper first and archive the current task second:

```bash
python3 ./.trellis/scripts/workflow/record-session-helper.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

python3 ./.trellis/scripts/task.py archive <task-name>
git status --short .trellis/tasks .trellis/.current-task
```

Expected metadata status output: empty.

Notes:

- `record-session` is the real close-out entry. It needs the current task context before archive clears `.trellis/.current-task`.
- If `record-session-helper.py` fails, do not archive yet.
- `archive` 预期会清除 `.trellis/.current-task`；真正需要关注的阻塞条件是 `.trellis/tasks` 元数据仍然 dirty。
- Detailed close-out gates still belong to the installed `/trellis:finish-work`, `/trellis:delivery`, and `/trellis:record-session` entries; this workflow guide only summarizes the default path.

### Pre-end Checklist

Close-out runs in two phases:

**Phase A — pre-commit (`/trellis:finish-work`)**

1. Frozen verification matrix executed or truthfully marked `deferred` / `not run`
2. Manual browser / app verification completed where required
3. `finish-work-checklist.md` records the current close-out evidence
4. Spec docs updated if needed

**Phase B — post-commit**

1. Human commit already exists
2. `record-session-helper.py` completed successfully for the current task
3. Current completed task archived; if it is a child task, the parent coordinator records are also synchronized to the new completed frontier
4. `.trellis/tasks` metadata clean
