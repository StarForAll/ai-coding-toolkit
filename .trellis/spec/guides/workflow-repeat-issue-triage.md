# Workflow Repeat-Issue Triage Guide

> Repo-level triage guide for repeated `workflow-scan` findings and repeated
> temp-project workflow issue loops.

---

## Purpose

Use this guide when a temporary target project produces new findings after an
earlier `workflow-scan` / `workflow-repair` cycle, especially when the same
workflow/report lineage has already looped more than once.

This guide exists to prevent the common failure mode:

```text
scan -> repair -> scan -> repair -> incremental discovery loop
```

The goal is to decide:

- whether the new finding is truly new
- whether the issue belongs to the same lineage/family
- whether the next step should be `workflow-audit`, `workflow-repair`,
  `workflow-capability-audit`, or `trellis-break-loop`
- whether the temp project must be synchronized to current source before the
  next scan

---

## When To Use

Use this guide before choosing the next tool when any of the following is true:

- the same `/tmp` target project reports issues again after a recent repair
- the same source workflow keeps producing new findings on regenerated temp
  projects
- a scan result looks like "the same family again, but a slightly different
  symptom"
- you are unsure whether to continue with another ordinary `workflow-repair`
- you suspect closure converged only on marker/text presence rather than on
  actual runtime behavior

---

## Step 0: Freeze Evidence First

Before repairing anything:

- record the new `WORKFLOW_QUESTIONS.md` path
- record:
  - `temp-project-root`
  - `trellis-version`
  - `workflow-version`
  - `workflow-schema-version`
  - `scan-timestamp`
- preserve older reports, repair logs, and closure-round artifacts
- if the temp project already exists, snapshot the installed carrier files
  relevant to the new finding before running merge/repair commands

Do not overwrite the older evidence first and "reconstruct later" from chat
memory.

---

## Step 1: Classify The Finding

Answer these questions in order.

### 1. Is It The Same Lineage?

Treat the issue as the same lineage when the strongest available evidence still
points at the same workflow/report/temp-project chain, for example:

- same `source-report` path pattern
- same `temp-project-root` lineage, or the same regenerated target class for
  the same source workflow
- same `trellis-version`

### 2. Is It The Same Family?

Treat the issue as the same family when it shares the same:

- runtime carrier or contract surface
- category / origin / evidence-layer class
- root-cause class or blocked-path symptom family

### 3. Is It A New Family On The Same Lineage?

Treat it as a new family when the lineage is the same but the issue changes:

- contract surface
- root-cause class
- affected carrier or phase

### 4. Is It Actually Version Drift?

If the finding depends on Trellis version drift rather than same-version temp
project behavior, route to `workflow-capability-audit` instead of ordinary
repair.

---

## Step 2: Choose The Next Route

### A. Same Lineage + Same Family

Do **not** default to another routine `workflow-repair`.

Instead:

- re-open the last audit / break-loop evidence
- ask whether the earlier closure proved real runtime behavior or only
  marker/text presence
- if the family is runtime-carrier or runtime-patch related, require at least
  one behavior-level verification before calling it converged
- treat the problem as a closure-design or verification-gap issue first

Recommended route:

- `workflow-audit`
- then `trellis-break-loop` if the loop pattern is still unclear

### B. Same Lineage + New Family

- treat the finding as a fresh audit branch
- update the audit report before planning repair
- do not silently absorb the new family into the old repair family

Recommended route:

- `workflow-audit`
- then a focused `workflow-repair` only if the audit confirms a safe repair path

### C. New Temp Project Reproduces The Old Finding

- treat this as stronger proof of a source-workflow defect
- prioritize source-side repair over more lineage interpretation
- still require closure coverage updates so the same class is not missed again

Recommended route:

- `workflow-repair` only after the defect has been re-confirmed against the new
  temp project and the needed closure scenarios are known

### D. Version Drift / Different Trellis Baseline

- stop ordinary repair
- compare compatible anchor vs actual runtime version

Recommended route:

- `workflow-capability-audit`

---

## Step 3: Runtime-Patch Family Rules

If the finding touches any of these:

- hook parser behavior
- route-helper fallbacks
- blocked / deny / cancel semantics
- installed plugin / hook / agent runtime control flow

Then closure is **not** allowed to stop at source text or marker presence.

Require all of:

- source-side tests
- at least one behavior-level assertion against the affected installed carrier
  path
- installed target updated to the latest source (`upgrade-compat --merge` when
  the target already exists)
- post-merge `upgrade-compat --check`

The same-family issue is not converged until the installed carrier behavior is
also proven.

---

## Step 4: Sync The Temp Project Before Re-Scanning

If source files are already repaired and the question is whether the temp
project still reflects the old state:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
--merge \
--project-root <temp-project-root>
```

Then verify:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
--check \
--project-root <temp-project-root>
```

Only re-run `workflow-scan` after the installed state matches current source.

---

## Step 5: Decide Whether To Re-Scan

Re-scan only when at least one of these is true:

- source repair completed and verification passed
- the installed temp project has been merged to current source
- the new scan will answer a question that current evidence cannot answer

Do **not** re-scan just to "see what happens" after a partial or unverified
fix.

---

## Minimum Recording Template

Copy this block into the current task when triaging a repeated scan issue:

```markdown
## Repeat-Issue Triage

- Report: `<path>`
- Temp Project: `<path>`
- Trellis Version: `<version>`
- Workflow Version: `<version>`
- Same lineage: `yes | no`
- Same family: `yes | no`
- Runtime-patch family: `yes | no`
- Source already repaired: `yes | no`
- Temp project already merged to source: `yes | no`
- Next tool route: `workflow-audit | workflow-repair | workflow-capability-audit | trellis-break-loop`
- Why: `<one paragraph>`
```

---

## Fast Rules

- Same lineage + same runtime family + no behavior-level closure proof:
  do audit/break-loop first, not another blind repair loop.
- Same source fixed but temp project not merged:
  sync temp project first, then re-scan.
- New family:
  update audit scope before repair.
- Version drift:
  do capability audit, not ordinary repair.
