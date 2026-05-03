# 17 Per-CLI Not-applicable Section

## Purpose

Verify that lightweight output keeps the `Per-CLI Adaptation Conclusions` section even when CLI adaptation is not in scope, using `not-applicable` entries with brief reasons.

## Input

User input:

> Do a lightweight document-only audit of `docs/workflows/新项目开发工作流/`. I only care about static rule-propagation drift right now, not CLI carrier mapping.

## Expected Mode

Lightweight static mode.

## Expected Key Behaviors

- output using the lightweight template
- keep the `Per-CLI Adaptation Conclusions` section
- mark Claude Code, OpenCode, and Codex as `not-applicable` when CLI adaptation was not examined
- include a brief reason for each `not-applicable` entry

## Must Not

- must not omit the per-CLI section entirely
- must not leave `not-applicable` entries unexplained
- must not fabricate CLI-specific conclusions when CLI adaptation was out of scope
