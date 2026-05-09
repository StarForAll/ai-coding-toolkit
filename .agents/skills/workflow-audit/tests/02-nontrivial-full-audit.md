# 02 Task-based Runtime Audit

## Purpose

Verify that `workflow-audit` correctly enters the task-based runtime audit path when `/tmp + trellis init + embed/post-install validation` are required.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/`. Create a temporary project under `/tmp`, run `trellis init`, and validate post-install state and per-CLI adaptation conclusions.

## Expected Mode

Task-based runtime mode.

## Expected Key Behaviors

- run the version preflight first (`workflow_assets.py` compatible version vs `trellis -v`) and proceed only when they match
- execute evidence mainline steps A (understand mechanics), B (static evidence), and C (gap analysis) first
- based on A/B/C findings, determine step D is required
- before creating task context, explain why task-based runtime mode was chosen
- create an audit task and enter the `trellis-brainstorm` mainline as the control container
- maintain `prd.md` in the task through the `trellis-brainstorm` path
- maintain `audit-report.md`, seeded with step A/B/C evidence tagged with source layers
- verify referenced script paths and check whether documented exit-code/output contracts remain machine-parseable when later workflow steps depend on them
- execute step D: `/tmp` project creation, `trellis init`, embed chain, post-install verification
- treat files immediately after `trellis init` as clean baseline evidence, then compare post-install state against that baseline before attributing artifacts to the workflow
- compare documented install artifacts against actual files, including hidden directories under `.trellis/`, `.claude/`, `.opencode/`, `.agents/`, and `.codex/`
- when evaluating shared carriers, treat `.agents/skills/` presence alone as non-defective and `.codex/skills/` as a conditional secondary carrier rather than a default required artifact
- when formal install is executed in a valid non-Codex path, require post-install `upgrade-compat.py --check`
- classify CLI adaptation gaps in step E as `present-but-incompatible` or `missing-but-valuable` when applicable
- stop with a controlled next-step recommendation instead of auto-executing follow-up work
- candidate_issues, if supplied, are referenced within each step without changing the execution path

## Must Not

- must not remain in lightweight mode
- must not pre-decide mode before step A/B/C
- must not skip the version preflight
- must not switch into task-based runtime mode without explaining why runtime validation is necessary
- must not skip gap analysis before runtime validation
- must not skip `/tmp` temporary-project validation
- must not produce certain issue conclusions without evidence
- must not attribute clean-baseline Trellis artifacts to the workflow merely because they still exist after install
- must not classify the absence of `.codex/skills/` alone as a defect without contract evidence that the secondary carrier is required
- must not use vague unlabeled CLI-gap wording when one of the required adaptation labels applies
- must not treat candidate_issues as a path-switching condition
- must not auto-advance into remediation after the audit stop point
