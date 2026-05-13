# Design Product Price Estimator Agent

## Goal

Create a reusable source-layer agent at
`agents/software-pricing-estimation-expert/` for software pricing and estimate
work. The agent must be adaptable to Claude Code, Codex, and OpenCode, must not
be installed into platform runtime directories in this repository, and must
enforce live verification for time-sensitive pricing facts.

## What I already know

- The user wants a generic "software product pricing estimation expert" agent.
- The asset must live under the current repository's `agents/` directory.
- The deliverable is a source asset, not an installed platform wrapper.
- The design must be usable in Claude Code, Codex, and OpenCode.
- The agent must analyze with the latest live-valid information when current
  facts matter.
- This repository expects `README.md`, `SYSTEM.md`, `TOOLS.md`,
  `DEPLOYMENT.md`, and optional `EXAMPLES/` in each source agent directory.
- Existing source agents already establish the expected structure and tone for
  cross-platform agent assets.

## Assumptions (temporary)

- The agent should cover both custom software quote estimation and software
  product / SaaS pricing estimation, as long as the work stays centered on
  pricing and estimate decisions.
- The agent should optimize for evidence-backed estimate ranges rather than
  false precision or single-number commitments.
- Example outputs should demonstrate process and structure without hardcoding
  stale third-party market numbers into long-lived source files.

## Open Questions

- None blocking. The current request is specific enough to implement a first
  reusable source asset directly.

## Requirements (evolving)

- Add a new agent source directory:
  `agents/software-pricing-estimation-expert/`
- Include:
  - `README.md`
  - `SYSTEM.md`
  - `TOOLS.md`
  - `DEPLOYMENT.md`
  - `EXAMPLES/` with representative input/output examples
- Keep `SYSTEM.md` tool-agnostic.
- Make the agent explicitly require live verification for:
  - vendor/API/cloud pricing
  - market benchmark pricing
  - labor rate benchmarks
  - exchange rates
  - app store / platform fees
  - time-sensitive policy or compliance cost drivers
- Require `[Evidence Gap]` output when live verification is unavailable.
- Document current platform mapping for Claude Code, OpenCode, and Codex using
  official documentation checked on 2026-05-13.
- Update `agents/README.md` so the new source asset appears in the directory
  index.

## Acceptance Criteria (evolving)

- [ ] `agents/software-pricing-estimation-expert/README.md` explains purpose,
      usage, I/O, source/deploy boundary, and wrapper targets
- [ ] `SYSTEM.md` defines role, responsibilities, boundaries, workflow, and
      output format without platform-specific syntax
- [ ] `TOOLS.md` encodes the live-evidence requirement through permission needs
      and forbidden operations
- [ ] `DEPLOYMENT.md` documents current Claude Code / OpenCode / Codex wrapper
      guidance with 2026-05-13 verification baseline
- [ ] `EXAMPLES/` demonstrates at least one custom software quote scenario and
      one SaaS / AI pricing scenario
- [ ] `agents/README.md` includes the new agent in the source asset list

## Definition of Done (team quality bar)

- Files are added in the source asset layer only
- Relevant documentation is consistent with current repository conventions
- Validation commands are run and results are reported truthfully

## Out of Scope (explicit)

- Installing wrappers into `.claude/agents/`, `.opencode/agents/`, or
  `.codex/agents/`
- Building automation that syncs source assets to platform deployment files
- Maintaining live market numbers inside long-lived example files

## Technical Notes

- Reuse style and structure from:
  - `agents/self-media-content-expert/`
  - `agents/software-solution-delivery-expert/`
- Official platform evidence is captured in:
  - `research/platform-and-evidence-baseline.md`

## Research References

- [`research/platform-and-evidence-baseline.md`](research/platform-and-evidence-baseline.md)
  — current platform file-format and live-evidence design baseline
