# 26 Ambiguous Natural-language Target

## Purpose

Verify that repo-level natural-language wording still binds the audit target to the fixed workflow root instead of widening the audit target to the whole repository or current project.

## Input

User input:

> Audit the workflow in this repo and tell me whether the current project's workflow packaging looks inconsistent, but do not run `/tmp` validation yet.

## Expected Mode

Lightweight mode.

## Expected Key Behaviors

- resolve the natural-language target to `docs/workflows/新项目开发工作流/`
- keep the audit target scoped to that workflow root even if later evidence references repo-local carrier directories
- report the supported workflow root explicitly in the output
- stay in static A/B/C mode when no runtime-validation trigger is found

## Must Not

- must not reinterpret "this repo" or "current project" as the primary workflow target
- must not expand the audit target to the whole repository
- must not ask for a different workflow root when no alternate path was named
