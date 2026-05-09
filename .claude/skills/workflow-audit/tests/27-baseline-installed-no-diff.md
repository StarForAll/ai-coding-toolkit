# 27 Baseline Installed No Diff

## Purpose

Verify that `workflow-audit` does not invent workflow-managed changes when the
clean `trellis init` baseline and the post-install state are materially the
same for a reviewed path.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/`. Create a temporary
> project under `/tmp`, run `trellis init`, install the workflow, and verify
> whether any hidden-directory artifacts are truly workflow-added rather than
> just baseline Trellis output.

## Expected Mode

Task-based runtime mode.

## Expected Key Behaviors

- capture a clean baseline snapshot immediately after `trellis init`
- compare post-install files against that snapshot before attributing any path
  to the workflow
- if a reviewed path is materially unchanged between baseline and post-install
  state, classify it as baseline/non-workflow evidence rather than a confirmed
  issue or workflow-managed delta
- preserve the distinction between baseline evidence, workflow-installed
  evidence, and runtime command output in the report

## Must Not

- must not attribute a no-diff baseline path to the workflow merely because the
  path exists after install
- must not escalate a no-diff path into a confirmed issue without contradictory
  evidence
- must not collapse baseline and workflow-installed state into a single bucket
