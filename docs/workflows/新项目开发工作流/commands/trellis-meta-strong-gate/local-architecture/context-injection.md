<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Local Context Injection System

Trellis context injection aims to make AI read the right files at the right time instead of relying on model memory. In a user project with this workflow installed, injection is organized around the strong-gate stage model.

## Injected Context Types

| Type | Source | Purpose |
| --- | --- | --- |
| session context | `.trellis/scripts/get_context.py` | Developer, git status, active task, active tasks, journal, packages. |
| workflow context | `.trellis/workflow.md` + `workflow-state.py route` | Current strong-gate stage and allowed next action. |
| spec context | `.trellis/spec/` + task JSONL | Specs required during implementation/checking. |
| task context | `.trellis/tasks/<task>/prd.md`, `info.md`, `research/` | Current task requirements, design, and research. |
| platform context | Platform hooks/settings/agents | Lets each CLI read the files above through its own carrier. |

## Session-Start Versus Turn-Level Injection

Some platforms use a dedicated session-start carrier, while others mainly rely on per-turn hooks.

- Claude Code commonly uses `session-start` plus turn-level workflow-state injection.
- Codex commonly relies on `.codex/hooks.json -> inject-workflow-state.py` on each turn; `session-start.py` is an optional auxiliary surface only when the target project explicitly wires it.
- OpenCode may use plugin/session utilities depending on the installed carrier set.

If the user says "the AI forgot the current stage," first check the carrier the platform actually uses in that project, not an assumed universal `session-start` hook.

## workflow-state

workflow-state is the lightweight hint injected around each user turn. In strong-gate projects it should be derived from:

```text
active task -> workflow-state.py route -> stage template + route metadata header
```

Do not describe this as "matching the current task status" unless you are explicitly talking about a legacy non-strong-gate project.

Practical meaning:

- the breadcrumb body may still come from the current stage's `[workflow-state:STAGE]` block
- but the injected header should surface route-only fields such as `action`, `status`, `blockers`, `target`, and `reason`
- therefore `blocked`, `context_needed`, or `repair_needed` must not look identical to an ordinary `design` / `plan` / `implementation` re-entry

## compatibility carrier context

Retained agent carriers may still need task context, but in this installed
workflow they are not the normal execution path.

If the user is explicitly inspecting a retained compatibility carrier, Trellis
still has two loading modes for that carrier:

1. **hook push**: a platform hook injects `prd.md` and the files referenced by
   `implement.jsonl` / `check.jsonl`.
2. **agent pull**: the retained carrier definition reads the active task, PRD,
   and JSONL context after startup.

In both modes, JSONL files remain the key interface, but normal workflow-stage
routing for this installed workflow still comes from `workflow-state.py route`
plus main-session guidance.

## Local Customization Points

| Need | Edit location |
| --- | --- |
| Change session-start injected content | The platform's session-start carrier, if that project actually wires one. |
| Change per-turn workflow-state rules | `[workflow-state:STAGE]` blocks in `.trellis/workflow.md`, plus the carrier logic that decides which route metadata is surfaced in the injected header. |
| Change how a retained compatibility carrier reads context | Platform agent definitions, `inject-subagent-context`, or retained carrier preludes. |
| Change active task resolution | `.trellis/scripts/common/active_task.py`. |

When modifying context injection, verify two things: the correct active task resolves, and the correct strong-gate stage/breadcrumb is emitted.
