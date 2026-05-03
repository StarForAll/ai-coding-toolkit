# 15 Source-layer Tag Compliance

## Purpose

Verify that `workflow-audit` preserves explicit source-layer tags on evidence and confirmed-issue evidence sources whenever it reports findings.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/` in a way that compares source files, installed target-project artifacts, and runtime command results.

## Expected Mode

Task-based runtime audit with multi-layer evidence.

## Expected Key Behaviors

- preserve explicit source-layer tags on evidence items
- use only the allowed tag values:
  - `source repo`
  - `generated target project`
  - `runtime command output`
- keep the same tags inside each confirmed issue's `evidence source` field

## Must Not

- must not output untagged evidence lines
- must not invent ad-hoc layer labels
- must not conflate source-repo evidence with generated target-project evidence
