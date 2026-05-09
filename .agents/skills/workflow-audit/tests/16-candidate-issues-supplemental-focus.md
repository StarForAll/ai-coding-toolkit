# 16 Candidate Issues Supplemental Focus

## Purpose

Verify that `candidate_issues` act only as supplementary focus points inside the normal evidence mainline and do not switch execution paths.

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/` and pay special attention to whether Codex handoff wording drifted and whether post-install verification guidance still matches the installer. Keep it static unless the evidence truly requires more.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - Whether Codex handoff wording drifted
  - Whether post-install verification guidance still matches installer behavior
need_runtime_validation: auto
force_full_brainstorm: no
```

## Expected Mode

Mode determined by the normal evidence mainline, not by `candidate_issues` alone.

## Expected Key Behaviors

- execute the same A/B/C mainline that would run without `candidate_issues`
- reference the supplied `candidate_issues` as supplementary focus points within the evidence steps
- if the focused evidence reaches generated target-project material, keep the baseline-vs-installed comparison model intact instead of collapsing them into one bucket
- keep mode selection based on actual findings rather than the mere presence of `candidate_issues`

## Must Not

- must not treat `candidate_issues` as confirmed defects
- must not let `candidate_issues` switch directly into task-based or runtime mode by themselves
- must not skip non-mentioned branches of the normal evidence mainline
