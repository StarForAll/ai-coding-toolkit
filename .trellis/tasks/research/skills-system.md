# Research: Trellis Skills System

- **Query**: Skill definitions, routing, skill-SKILL.md format, how skills are triggered and loaded
- **Scope**: internal
- **Date**: 2026-05-18

## Findings

### Files Found

| File Path | Description |
|---|---|
| `.claude/skills/trellis-brainstorm/SKILL.md` | Collaborative requirements discovery (549 lines) |
| `.claude/skills/trellis-before-dev/SKILL.md` | Pre-development spec discovery (35 lines) |
| `.claude/skills/trellis-check/SKILL.md` | Quality verification (93 lines) |
| `.claude/skills/trellis-update-spec/SKILL.md` | Spec capture and update (357 lines) |
| `.claude/skills/trellis-break-loop/SKILL.md` | Deep bug analysis (131 lines) |
| `.trellis/workflow.md` | Skill routing table (lines 253-305) |

### Skill Catalog

**trellis-brainstorm** (549 lines):
- Purpose: Collaborative requirements discovery
- 8 steps: Ensure Task Exists -> Auto-Context -> Classify Complexity -> Question Gate -> Research-first Mode -> Expansion Sweep -> Q&A Loop -> Final Confirmation
- Research delegation: dispatches `trellis-research` sub-agent (parallelized)
- Produces PRD structure template and ADR-lite format
- Triggers during Phase 1.2-1.3 when user intent is brainstorming/requirements

**trellis-before-dev** (35 lines):
- Purpose: Pre-development spec discovery and injection
- 6 steps: discover packages -> identify applicable specs -> read spec index -> read guideline files -> read shared guides -> understand standards
- Used in inline dispatch mode instead of spawning implement sub-agent
- Loads spec content directly into main session context

**trellis-check** (93 lines):
- Purpose: Quality verification against specs
- 6 steps: identify changes -> read specs -> run checks -> review checklist -> cross-layer dimensions -> report and fix
- Dimensions: spec compliance, lint, type-check, tests, cross-layer consistency
- Can auto-fix issues found during checking

**trellis-update-spec** (357 lines):
- Purpose: Capture executable contracts into spec documents
- Code-spec vs Guide: specs = "how to implement", guides = "what to consider"
- Mandatory 7-section template for infra/cross-layer work
- Update types: Design Decision, Project Convention, New Pattern, Forbidden Pattern, Common Mistake, Gotcha
- Triggers during Phase 3.1 (Update Specs)

**trellis-break-loop** (131 lines):
- Purpose: Deep bug analysis to break "fix-forget-repeat" cycle
- 5 dimensions: Root Cause Category (A-E), Why Fixes Failed, Prevention Mechanisms, Systematic Expansion, Knowledge Capture
- Triggers when user reports recurring issues or the AI detects a loop

### Skill Routing

From workflow.md lines 253-305:

| User Intent | Phase | Skill (sub-agent mode) | Skill (inline mode) |
|---|---|---|---|
| Brainstorm/Requirements | 1.2-1.3 | trellis-brainstorm | trellis-brainstorm |
| Implement | 2.1 | Dispatch trellis-implement | trellis-before-dev |
| Check | 2.2 | Dispatch trellis-check | trellis-check (inline) |
| Research | 1.3 | Dispatch trellis-research | Dispatch trellis-research |
| Update Spec | 3.1 | trellis-update-spec | trellis-update-spec |
| Break Loop | Any | trellis-break-loop | trellis-break-loop |

### Skill Loading Mechanism

- Skills are triggered by AI agents based on workflow step instructions in breadcrumbs
- The breadcrumb content includes skill routing recommendations
- On Claude Code, skills are loaded via the Skill tool invocation
- On other platforms, skills may be loaded differently (platform-specific mechanism)
- Skill files follow the `SKILL.md` convention within a named skill directory

### Connections

- Skills are the primary action mechanism within workflow phases
- `trellis-before-dev` bridges specs to the inline execution path
- `trellis-brainstorm` delegates research to the `trellis-research` sub-agent
- `trellis-update-spec` writes to the spec layer, creating new spec files
- `trellis-check` reads specs and compares against code, connecting spec layer to verification
- Skill routing is determined by dispatch mode (from config.yaml) and user intent

## Caveats / Not Found

- Other platform skill directories (`.cursor/skills/`, `.codex/skills/`, etc.) were not enumerated
- The `trellis-spec-bootstrap` skill (visible in git status as untracked) was not investigated
- How skills are registered/discovered by each AI platform was not traced in detail
