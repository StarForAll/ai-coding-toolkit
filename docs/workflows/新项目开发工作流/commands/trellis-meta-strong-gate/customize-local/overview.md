<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Local Customization Overview

This workflow keeps the generic Trellis customization topics, but under the
strong-gate policy some topics move to different first-choice edit surfaces.

## First Determine The Real Target

| User wording | Read first in this installed workflow |
| --- | --- |
| "Change the Trellis flow / phases / next prompt" | `change-workflow.md` |
| "Change task creation, status, archive, or hooks" | `change-task-lifecycle.md` |
| "AI did not read context / change injected content" | `change-context-loading.md` |
| "A platform hook is not behaving as expected" | `change-hooks.md` |
| "Change implement/check/research execution behavior" | `change-workflow.md` first; `change-agents.md` only if the request is explicitly about retained compatibility carriers |
| "Add a skill/command/workflow/prompt" | `change-skills-or-commands.md` |
| "Adjust the project spec structure" | `change-spec-structure.md` |
| "Add team conventions and local notes" | `add-project-local-conventions.md` |

## Important Boundary

In this installed workflow, "change implement/check/research behavior" is
usually a workflow-policy or live-carrier question, not a platform-agent-file
question.

Start from:

1. `.trellis/workflow.md`
2. workflow-state routing
3. live hooks/skills/commands

Only go to `change-agents.md` when the user explicitly wants to modify the
compatibility-retained agent carrier files themselves.
