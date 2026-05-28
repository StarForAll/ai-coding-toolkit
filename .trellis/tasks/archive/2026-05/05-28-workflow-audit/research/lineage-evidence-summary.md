# Lineage Evidence Summary

## Scope

This file captures the latest five repair-task artifacts on the currently
observed lineage:

- `source-report`: `/tmp/trellis-0.5.17-2/WORKFLOW_QUESTIONS.md`
- `trellis-version`: `0.5.17`

The broader lineage includes older same-lineage repair logs from 2026-05-20
through 2026-05-21. This file uses the latest five by timestamp as the initial
audit seed set and preserves the fact that one of those rounds was a skip-only
round under the older v2 protocol.

## Latest Five Rounds By Timestamp

### 1. 2026-05-27 21:48:42 +08:00

- Task: `.trellis/tasks/archive/2026-05/05-27-workflow-repair-2026-05-27-break-loop-doc-drift/`
- Log: `workflow-repair-log.md`
- Protocol: `workflow-scan-repair-v4`
- Base workflow version: `0.1.2802`
- Counts: attempted `3`, succeeded `3`, failed `0`, reverted `0`, skipped `0`
- Closure artifact:
  `closure-round-1.md` -> `round-outcome: clean`, `total-findings: 0`

### 2. 2026-05-27 19:32:25 +08:00

- Task: `.trellis/tasks/archive/2026-05/05-27-workflow-repair-2026-05-27-codex-start-routing/`
- Log: `workflow-repair-log.md`
- Protocol: `workflow-scan-repair-v4`
- Base workflow version: `0.1.2801`
- Counts: attempted `3`, succeeded `3`, failed `0`, reverted `0`, skipped `0`
- Closure artifact:
  `closure-round-1.md` -> `round-outcome: clean`, `total-findings: 0`

### 3. 2026-05-27 17:08:41 +08:00

- Task: `.trellis/tasks/archive/2026-05/05-27-workflow-repair-2026-05-27-create-pr-reference/`
- Log: `workflow-repair-log.md`
- Protocol: `workflow-scan-repair-v4`
- Base workflow version: `0.1.2800`
- Counts: attempted `4`, succeeded `4`, failed `0`, reverted `0`, skipped `0`
- Closure artifact:
  `closure-round-1.md` -> `round-outcome: clean`, `total-findings: 0`

### 4. 2026-05-27 15:17:55 +08:00

- Task: `.trellis/tasks/archive/2026-05/05-27-workflow-repair-2026-05-27-trellis-brainstorm-subagent-drift/`
- Log: `workflow-repair-log.md`
- Protocol: `workflow-scan-repair-v4`
- Base workflow version: `0.1.2800`
- Counts: attempted `1`, succeeded `1`, failed `0`, reverted `0`, skipped `0`
- Closure artifact:
  `closure-round-1.md` -> `round-outcome: clean`, `total-findings: 0`

### 5. 2026-05-21 20:24:59 +08:00

- Task: `.trellis/tasks/archive/2026-05/05-21-workflow-repair-2026-05-21-trellis-spec-bootstrap-typo/`
- Log: `workflow-repair-log.md`
- Protocol: `workflow-scan-repair-v2`
- Issue-history shadow: `tmp/workflow-issues/0012.md`
- Counts: attempted `0`, succeeded `0`, failed `0`, reverted `0`, skipped `8`
- Note: this is part of the latest-five chronology but is not a successful
  repair batch; it is retained because it still belongs to the same observed
  lineage trail.

## Broader Same-Lineage Context

Additional same-lineage repair logs exist earlier in the archive, including:

- `05-21-workflow-repair-2026-05-21-codex-hooks-json`
- `05-21-workflow-repair-2026-05-21-codex-sessionstart-hook`
- `05-21-workflow-repair-2026-05-21-phase-resolution`
- `05-21-workflow-repair-2026-05-21-carrier-boundaries`
- `05-21-workflow-repair-ws001-ws004-boundaries`
- `05-21-workflow-repair-trellis-library-full-path`
- `05-20-workflow-repair-missing-runtime-patches`
- `05-20-workflow-repair-2026-05-20-break-loop-update-spec-routing`
- `05-20-workflow-repair-2026-05-20-codex-skills-empty`
- `05-20-workflow-repair-2026-05-20-broken-carrier-links`
- `05-20-workflow-repair-agents-nl-routing-before-dev`

All of the above share the same currently observed `source-report` path and
`trellis-version`, so later audit work should not treat them as unrelated just
because the protocol version or workflow base version changed across time.

## Current Interpretation

- The currently observed lineage is broad enough that another ordinary
  `workflow-repair` batch would likely under-explain the repeat pattern.
- The four latest v4 repair rounds all recorded clean closure-round outcomes,
  which suggests the repeated-loop problem may live in a wider scan/repair
  selection boundary, contract boundary, or evidence-framing gap rather than in
  a single unresolved same-family closure finding inside those four rounds.
- The presence of an older skip-only v2 round in the latest-five chronology is
  itself useful lineage evidence: not every round produced real source edits,
  yet the same lineage continued to re-trigger.
