# 20 Script Behavior Mismatch

## Purpose

Verify that `workflow-audit` properly detects, classifies, and reports a mismatch between a workflow script's documented behavior and its actual behavior, including documented output-value contracts (e.g., `detect-embed-state.py` status values) and required environment-variable contracts (e.g., `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` for `install-workflow.py`).

## Input

User input:

> Audit `docs/workflows/新项目开发工作流/`. Pay special attention to whether `install-workflow.py` still refuses formal install when `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` is unset, and whether `detect-embed-state.py` exit codes still match what the embed flow documentation promises.

Interpreted as:
```yaml
workflow_path: docs/workflows/新项目开发工作流/
candidate_issues:
  - Whether install-workflow.py still enforces WORKFLOW_EMBED_EXECUTOR_CONFIRMED for formal install
  - Whether detect-embed-state.py output status values still match documented contract
need_runtime_validation: auto
force_full_brainstorm: no
```

## Expected Mode

Mode is determined by Step 2 findings. If static analysis can conclusively confirm or refute the mismatch (script source clearly shows or omits the env-var check, output status values are inspectable), the audit may stay in lightweight static mode and report it. If static analysis cannot conclusively decide and runtime behavior is required, escalate to task-based runtime mode (or output a Needs Confirmation block when the user pinned `need_runtime_validation: no`).

## Expected Key Behaviors

- execute evidence mainline A/B/C with the candidate issues as supplementary focus, not as confirmed defects
- in Step 2B, locate `install-workflow.py` and `detect-embed-state.py`, then read the relevant code paths (env-var enforcement, output status-value mapping, required output shape)
- in Step 2C, compare the documented contract (from workflow docs and from `references/codex-handoff-template.md`) against actual script behavior; note that `detect-embed-state.py` always exits with code 0 and reports status via stdout (both human-readable and JSON), not via exit codes — the documented contract references status values (`INITIAL_BASELINE_READY`, `ALREADY_VALID_EMBEDDED`, `BLOCKED_NON_INITIAL_STATE`) which appear in the output, not in exit codes
- if the script no longer enforces `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1` for formal install, classify it as a `P0` confirmed issue (security/boundary contract broken) per the priority rubric
- if output status values diverge in a way that breaks downstream parsing but a manual workaround exists, classify it as `P1`
- if the divergence is only in wording (e.g., a help-text typo) with no behavior impact, classify it as `P2`
- every confirmed issue includes the full minimum schema, with `validation action` describing exactly how the mismatch was detected (e.g., "Read `install-workflow.py:114` and confirmed the env-var check has been removed; documentation in `codex-handoff-template.md` still implies enforcement")
- evidence sources keep their source-layer tags (`source repo` for static reads, `runtime command output` if D was executed)
- if the audit cannot conclusively determine severity from static evidence, record it as `Blocked / Evidence Gap` with a runtime-validation follow-up note; do NOT guess a P-level

## Must Not

- must not silently downgrade a broken `WORKFLOW_EMBED_EXECUTOR_CONFIRMED` enforcement to `P1` or `P2` — boundary-contract breakage is `P0`
- must not treat the candidate issues as confirmed defects before evidence is gathered
- must not report a confirmed issue without `validation action` or without a source-layer tag
- must not claim the env-var contract is intact based only on documentation; the audit must read the script itself
- must not treat `detect-embed-state.py` status values as exit codes; the script always returns exit code 0 and reports status through its stdout output (human-readable or JSON), not through the process exit code
- must not skip the comparison against `codex-handoff-template.md` and the spec, since those are the documented contracts the script is being measured against
