<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Platform Files Overview

The current embedded workflow still uses the same broad Trellis file categories,
but the live execution path is narrowed by the strong-gate main-session-only
policy.

## Two Categories Still Matter

- **Shared files**: `.trellis/workflow.md`, `.trellis/tasks/`, `.trellis/spec/`,
  `.trellis/scripts/`
- **Platform files**: `.claude/`, `.codex/`, `.opencode/`, and related adapter
  directories

Platform files still connect the AI tool to Trellis, but not every generated
carrier is an active workflow path.

## Platform File Categories Under Strong-Gate

| Category | Common paths | Current meaning |
| --- | --- | --- |
| settings/config | `.claude/settings.json`, `.codex/hooks.json`, `.opencode/package.json` | Active wiring surface |
| hooks/plugins/extensions | `.claude/hooks/`, `.opencode/plugins/`, `.codex/hooks/` | Active workflow-state / session / blocked-route carriers |
| agents | `.claude/agents/`, `.codex/agents/`, `.opencode/agents/` | Baseline or compatibility-retained carriers; not the normal execution path |
| skills | `.claude/skills/`, `.agents/skills/`, `.opencode/skills/` | Active guidance surface when the workflow installs or patches them |
| commands/prompts/workflows | command/workflow entry files | Active user-facing entry surfaces where applicable |

## Integration Modes In This Workflow

### 1. Hook / Extension Driven

These carriers are active and should be checked first when the user asks "what
is the AI actually reading now?"

- workflow-state injection
- session-start where wired
- blocked subagent routing or denial behavior
- shell/session identity propagation

### 2. Compatibility Agent Carriers

Platform agent files may still exist, but this workflow does not currently use
them as the normal execution path for implementation/checking.

Treat them as:

- baseline Trellis carriers
- compatibility-retained surfaces
- possible future re-enable targets only after policy changes

### 3. Main-Session Workflow

This installed workflow expects normal research / implement / check work to stay
in the main session, guided by workflow-state routing plus the relevant
skills/commands/hooks.

## Modification Order

When the user asks to change current behavior:

1. Read `.trellis/workflow.md`
2. Read the platform settings/config that register live carriers
3. Read the actual active hooks/skills/commands
4. Touch compatibility agent files only if the request is explicitly about
   those retained carriers

Do not assume that a generated agent file is active just because it exists.
