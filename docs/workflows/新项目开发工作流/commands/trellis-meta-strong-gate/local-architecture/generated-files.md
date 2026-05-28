<!-- workflow-embed-patch:trellis-meta-strong-gate -->

# Local Files Generated After Init

`trellis init` still generates the baseline Trellis runtime, but this installed
workflow distinguishes between active carriers and compatibility-retained
carriers.

## Platform Directories

Common categories still include hooks, settings, agents, skills, and explicit
command/workflow entry files.

| Category | Example paths | Current meaning in this workflow |
| --- | --- | --- |
| hooks | `.claude/hooks/`, `.codex/hooks/`, `.opencode/plugins/` | Active integration layer |
| settings | `.claude/settings.json`, `.codex/hooks.json`, `.opencode/package.json` | Active wiring layer |
| agents | `.claude/agents/`, `.codex/agents/`, `.opencode/agents/` | Baseline/compatibility-retained carriers; not the normal execution path |
| skills | `.claude/skills/`, `.agents/skills/`, `.opencode/skills/` | Active guidance surface when installed/patched by this workflow |
| commands/prompts/workflows | platform-specific entry files | Active user-facing entry surfaces where applicable |

## Practical Boundary

Do not assume that every generated carrier is active just because it exists on
disk.

For this workflow:

- workflow-state carriers, hooks/plugins, and installed stage guidance are the
  active path
- agent carrier files may remain for compatibility, baseline preservation, or
  future re-enable planning

If the user asks to change the current execution model, start from the active
workflow and hook/skill/command surfaces first.
