# 28 Trellis Init Partial Baseline Failure

## Purpose

Verify that `workflow-audit` handles a Step D failure correctly when `trellis
init` fails after creating some files but before a reliable clean baseline
snapshot can be confirmed.

## Input

User input:

> Audit the embed flow of `docs/workflows/新项目开发工作流/` in full runtime mode.
> If `trellis init` fails after creating some files, report what remains
> unverified instead of treating those partial files as a valid baseline.

## Expected Mode

Task-based runtime mode blocked during Step D.

## Expected Key Behaviors

- begin Step D and attempt `/tmp` project setup plus `trellis init`
- if `trellis init` fails before the clean baseline snapshot is successfully
  captured, classify the audit as `Blocked / Runtime Execution Failure`
- record the failing command, exit status, partial file-system evidence, and
  explicitly state that no reliable clean baseline snapshot was established
- keep any partially created files as incomplete runtime evidence only, not as
  baseline or workflow-installed state

## Must Not

- must not treat partially created `trellis init` files as a confirmed clean
  baseline
- must not continue to install or post-install checks after the blocking
  `trellis init` failure
- must not attribute partial `trellis init` output to the workflow
