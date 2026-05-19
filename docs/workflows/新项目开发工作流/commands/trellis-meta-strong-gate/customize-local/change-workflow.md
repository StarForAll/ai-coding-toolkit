<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Change Local Workflow

When the user wants to change Trellis stages, next-action hints, task-creation policy, or wrap-up flow in a project that has this workflow installed, edit the strong-gate workflow contract first.

## Read These Files First

1. `.trellis/workflow.md`
2. `.trellis/scripts/workflow/workflow-state.py`
3. The current platform entry files (continue/start skills or commands, hooks, agents)
4. The current task's `workflow-state.json`, `task.json`, and `prd.md`

## Common Needs And Edit Points

| Need | Edit point |
| --- | --- |
| Change stage names or stage order | `.trellis/workflow.md` and `workflow-state.py` together |
| Change whether to create a task when there is no task | `[workflow-state:no_task]` plus entry routing patches |
| Change the next step in a specific stage | The matching `[workflow-state:<stage>]` block and, if routing changes, `workflow-state.py route` |
| Change whether sub-agents are required | Stage instructions plus platform-specific entry files |
| Change close-out behavior | `finish-work`, `delivery`, `record-session`, and their validators together |

## Modification Steps

1. Find the relevant stage or entry point in `.trellis/workflow.md`.
2. If the meaning of a stage changes, update `workflow-state.py` gate validation and routing in the same change.
3. Synchronize the affected platform carrier files (continue/start commands or skills, hooks, agents).
4. Re-read `.trellis/workflow.md` after editing; do not keep using stale session assumptions.

## `/trellis:continue` Route Table

In strong-gate projects, `/trellis:continue` does not resume from a static `task.json.status + artifacts` table. The authoritative decision comes from `workflow-state.py route`, whose output includes:

- `action`
- `target`
- `stage`
- `stage_status`
- `blockers`

Examples:

| action | Meaning | Resume behavior |
| --- | --- | --- |
| `first_entry` | No active task and no resumable task | Use the skill/command matching `target` (`feasibility` for outsourcing, `brainstorm` for personal) |
| `reenter` | Re-enter the current confirmed stage | Use the carrier matching `target` |
| `context_needed` | Parent task cannot continue directly | Switch to the required child task before proceeding |
| `awaiting_confirmation_with_blockers` | Stage is at confirmation point but exit gate is incomplete | Fix blockers before asking for confirmation |
| `repair_needed` | State file missing or stale | Run `workflow-state.py repair` and confirm the inference; execution stages also need explicit confirmation fields such as `--execution-authorized true` and `--transition-from <previous-stage>` |

## Notes

- Do not add new behavior by writing custom `task.json.status` values alone; that is not the strong-gate routing source of truth.
- If you need a new breadcrumb key, make sure the routing layer can actually emit it and decide whether the change belongs in the template key, the injected header, or both.
- For finish-work changes, remember the active close-out chain is `finish-work -> delivery -> record-session`.
