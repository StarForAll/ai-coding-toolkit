# 29 Native CLI Doc And Practical Evidence

## Purpose

Verify that `workflow-audit` does not judge Claude Code / OpenCode / Codex
native adaptation from memory or repo inspection alone; it must combine the
latest official CLI docs with repo-local evidence and practical
development-use evidence.

## Input

User input:

> Audit whether `docs/workflows/新项目开发工作流/` is really natively adapted to
> Claude Code, OpenCode, and Codex. Use the latest official docs and tell me
> whether the current carrier setup still matches how these CLIs are actually
> used in development.

## Expected Mode

Mode is determined by Step 2 findings. Lightweight static mode is acceptable if
the question can be answered conclusively through doc + repo evidence without
runtime validation. Task-based mode is required if runtime gating or embed
behavior must be verified to resolve the conclusion.

## Expected Key Behaviors

- for each CLI, check the latest official documentation available at audit time
- for each CLI, check repo-local evidence such as the boundary matrix, platform
  READMEs, and live carrier files
- for each CLI, record practical development-use evidence such as the primary
  carrier path, conditional carrier path, and runtime gating behavior
- if these evidence sources disagree, report the discrepancy conservatively
  instead of guessing
- do not equate directory presence/absence with real native compatibility

## Must Not

- must not conclude native adaptation from memory alone
- must not conclude native adaptation from carrier-file presence alone
- must not skip the practical development-use angle when carrier behavior is
  conditional or runtime-gated
- must not collapse official docs, repo-local evidence, and practical-use
  evidence into one unlabeled statement
