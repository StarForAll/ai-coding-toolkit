# Workflow Scan Repeat-Issue Checklist

## Purpose

Use this checklist when a temporary target project produces new findings after a
previous `workflow-scan` / `workflow-repair` cycle, especially when the same
lineage has already looped more than once.

This checklist is for **operational triage and routing**:

- preserve evidence first
- classify whether the finding is truly new
- choose the right next tool path
- avoid blindly re-entering `workflow-repair`

## Step 0: Freeze Evidence

- [ ] Save the new `WORKFLOW_QUESTIONS.md` path
- [ ] Record:
  - `temp-project-root`
  - `trellis-version`
  - `workflow-version`
  - `workflow-schema-version`
  - `scan-timestamp`
- [ ] Do not overwrite older reports or closure artifacts
- [ ] If the temp project already exists, snapshot the relevant installed
      carrier files before any merge/repair step

## Step 1: Classify The New Finding

Answer these questions in order:

1. Is this the **same lineage**?
   - Same `source-report` path pattern
   - Same `temp-project-root` lineage or same regenerated target for the same
     source workflow
   - Same `trellis-version`

2. Is this the **same family**?
   - Same runtime carrier / contract surface
   - Same category/origin/evidence-layer class
   - Same root-cause class or same blocked-path symptom

3. Is this a **new family** on the same lineage?
   - Different contract surface
   - Different root-cause class
   - Different affected carrier or phase

4. Is this only **version drift**?
   - If yes, route to `workflow-capability-audit`, not ordinary repair

## Step 2: Choose The Route

### A. Same Lineage + Same Family

Do **not** default to another routine `workflow-repair`.

Use this route when the same repair family has reappeared:

- [ ] Re-open the last audit / break-loop evidence
- [ ] Ask whether closure previously proved real runtime behavior or only
      marker/text presence
- [ ] If the family is runtime-carrier or runtime-patch related, require at
      least one behavior-level verification before calling it converged
- [ ] Treat this as a closure-design or verification-gap problem first

Recommended next tool:

- `workflow-audit`
- then `trellis-break-loop` if the loop pattern is still unclear

### B. Same Lineage + New Family

- [ ] Treat the new finding as a fresh audit branch
- [ ] Update the audit report before planning repair
- [ ] Do not silently absorb it into the old repair family

Recommended next tool:

- `workflow-audit`
- then a focused `workflow-repair` only if the audit confirms a safe repair path

### C. New Temp Project Reproduces Old Finding

- [ ] Treat this as stronger proof of a source-workflow defect
- [ ] Prioritize source-side repair over more lineage interpretation
- [ ] Still require closure coverage updates so the same class is not missed again

Recommended next tool:

- `workflow-repair` only after the defect has been re-confirmed against the new
  temp project and the needed closure scenarios are known

### D. Version Drift / Different Trellis Baseline

- [ ] Stop ordinary repair
- [ ] Compare compatible anchor vs actual runtime version

Recommended next tool:

- `workflow-capability-audit`

## Step 3: Runtime-Patch Family Rules

If the finding touches any of these:

- hook parser behavior
- route-helper fallbacks
- blocked / deny / cancel semantics
- installed plugin / hook / agent runtime control flow

Then closure is **not** allowed to stop at source text or marker presence.

Require all of:

- [ ] source-side tests
- [ ] at least one behavior-level assertion against the affected installed
      carrier path
- [ ] installed target updated to the latest source (`upgrade-compat --merge`
      if the target already exists)
- [ ] post-merge `upgrade-compat --check`

## Step 4: Sync The Temp Project Before Re-Scanning

If you already repaired source files and want to know whether the temp project
still reflects the old state:

- [ ] On the existing temp project, run:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
--merge \
--project-root <temp-project-root>
```

- [ ] Then verify:

```bash
/ops/softwares/python/bin/python3 \
docs/workflows/新项目开发工作流/commands/upgrade-compat.py \
--check \
--project-root <temp-project-root>
```

- [ ] Only re-run `workflow-scan` after the installed state matches current source

## Step 5: Decide Whether To Re-Scan

Re-scan only when one of these is true:

- [ ] source repair completed and verification passed
- [ ] installed temp project has been merged to current source
- [ ] the new scan will answer a question that current evidence cannot answer

Do **not** re-scan just to “see what happens” after a partial or unverified fix.

## Step 6: Minimum Recording Template

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

## Fast Rules

- Same lineage + same runtime family + no behavior-level closure proof:
  do audit/break-loop first, not another blind repair loop.
- Same source fixed but temp project not merged:
  sync temp project first, then re-scan.
- New family:
  update audit scope before repair.
- Version drift:
  do capability audit, not ordinary repair.
