# 02 Nontrivial Full Audit

## Purpose

Verify that `workflow-audit` correctly enters the non-trivial audit path when `/tmp + trellis init + embed/post-install validation` are required.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/`. Create a temporary project under `/tmp`, run `trellis init`, and validate post-install state and per-CLI adaptation conclusions.

## Expected Mode

Non-trivial audit mode.

## Expected Key Behaviors

- create an audit task
- enter the `brainstorm` mainline
- maintain `prd.md` in the task through the `brainstorm` path
- maintain `audit-report.md` when required
- gather static evidence first, then runtime evidence
- when formal install is actually delegated or executed in a valid non-Codex path, require a post-install `upgrade-compat.py --check`
- output per-CLI adaptation conclusions
- stop with a controlled next-step recommendation instead of auto-executing follow-up work

## Must Not

- must not remain in lightweight mode
- must not skip `/tmp` temporary-project validation
- must not produce certain issue conclusions without evidence
- must not auto-advance into remediation after the audit stop point
