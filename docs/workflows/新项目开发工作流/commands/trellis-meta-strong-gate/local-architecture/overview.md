<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Local Trellis Architecture Overview

`trellis-meta` still explains how a Trellis project is structured locally, but
for this installed workflow the execution policy is narrower than the generic
Trellis baseline.

## Local Layers

1. **Workflow layer**: `.trellis/workflow.md`
2. **Persistence layer**: `.trellis/tasks/`, `.trellis/spec/`,
   `.trellis/workspace/`
3. **Platform integration layer**: hooks, settings, skills, commands, and
   compatibility-retained agent carriers

All of these still live inside the user project.

## Strong-Gate Policy Overlay

The important difference in this installed workflow is:

- live routing comes from workflow-state plus main-session execution
- generated agent/subagent carrier files may remain on disk
- those retained carriers do **not** automatically count as the current
  supported path

Therefore, when the user asks "where should I change the workflow now?", start
from the workflow and active hook/skill/command surfaces first, not from the
retained agent carrier files.

## Read Order For Current Behavior

1. `.trellis/workflow.md`
2. `.trellis/scripts/workflow/workflow-state.py`
3. current platform settings/config
4. live workflow-state / command / skill carriers

Only inspect platform agent files first when the request is explicitly about
the compatibility carrier itself.
