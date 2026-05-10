## Development Process

<!-- workflow-projectization-patch -->

### Task Development Flow

```text
1. Create or select task
   --> python3 ./.trellis/scripts/task.py create "<title>" --slug <name> or list

2. Start task (mark as current)
   --> python3 ./.trellis/scripts/task.py start <name>
   --> Writes session-scoped active task runtime state; future sessions and hooks can re-enter the current task

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
   --> python3 ./.trellis/scripts/task.py archive <task-name>
   --> python3 ./.trellis/scripts/add_session.py --title "Title" --commit "hash"
   --> archive runs first, then add_session
```

`python3 ./.trellis/scripts/task.py finish` remains available when you intentionally need to clear the current session's active task without archiving a completed task. Do not use it as a substitute for final close-out.

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

After the human has tested and committed the code, archive the current task first and record the session second:

```bash
python3 ./.trellis/scripts/task.py archive <task-name>

python3 ./.trellis/scripts/add_session.py \
  --title "Session Title" \
  --commit "abc1234" \
  --summary "Brief summary"

git status --short .trellis/workspace .trellis/tasks
```

Expected metadata status output: empty.

Notes:

- Close-out follows Trellis native `finish-work` behavior: archive first, then `add_session.py`.
- `archive` 预期会清除当前 session 的 active-task runtime；真正需要关注的阻塞条件是 `.trellis/workspace` / `.trellis/tasks` 元数据仍然 dirty。
- Detailed close-out gates still belong to the installed `/trellis:finish-work` / `trellis-finish-work` and `/trellis:delivery` entries; legacy `/trellis:record-session` is old-target compatibility only. This workflow guide only summarizes the default path.

### Pre-end Checklist

Close-out runs in two phases:

**Phase A — pre-commit (`/trellis:finish-work`)**

1. Frozen verification matrix executed or truthfully marked `deferred` / `not run`
2. Manual browser / app verification completed where required
3. `finish-work-checklist.md` records the current close-out evidence
4. Spec docs updated if needed

**Phase B — post-commit**

1. Human commit already exists
2. Current completed task archived; if it is a child task, the parent coordinator records are also synchronized to the new completed frontier
3. `add_session.py` completed successfully for the current session record
4. `.trellis/workspace` and `.trellis/tasks` metadata clean
