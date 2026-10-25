# Design-Doc Review Thinking Guide

> Repo-local review protocol for design/contract documents. It exists because
> "deep review" without an evidence bar produces false defects, unnecessary
> revisions, and noise that hides the real findings.

---

## The Failure Mode

In the 2026-10 review of `docs/workflows/workflow-design.md` v27, the first pass
reported 7 main findings and 5 minor items. After checking the document's own
decision log, worked examples, and the simplest conforming implementation:

- main findings: 1 retained, 2 downgraded to wording/optional, 4 withdrawn
- minor items: 2 retained, 3 withdrawn

The expensive part was not the retraction; it was that false and true findings
were presented with the same confidence. A review that cannot exclude its own
false positives is not a review, it is a candidate list.

## When To Use

- reviewing `docs/workflows/workflow-design.md` or its companion
  `依赖机制设计说明.md`
- any "find gaps / contradictions / risks" review of a design, contract, or
  protocol document
- before turning review notes into a document revision

Do not use this guide for ordinary code review or bug diagnosis.

## Core Rule

A candidate is a **design defect** only if at least one is true:

1. two written rules conflict on the same case;
2. a written rule has no permitted exit for a reachable, honest-use scenario;
3. every conforming implementation/execution violates a written rule or an
   invariant;
4. a written rule contradicts a normal real-world usage scenario.

Everything else is not a defect: unspecified values (blanks), implementation
freedom, tooling choices, intentional tradeoffs, external tampering or
against-doc bypass, and "it would be nicer if".

## Step 0: Build The Decision Log Before Judging

Read these first and treat them as constraints, not targets:

- the document's own review contract and intentional-tradeoff list (for
  `workflow-design.md`: §0.1 fact boundary and the A/B acceptance table);
- the revision-history appendix (v25-v27 record deliberate decisions);
- the companion document's implementation-choices section (for
  `依赖机制设计说明.md`: §13);
- version fields: design version must equal the companion `design` field;
  derived docs are cross-check only — report version drift, do not review them
  as if they were the design.

If a finding asks to undo a recorded decision, it is not a finding. Record the
decision and move on.

## Step 0.5: Acceptance-Surface Sweep Before Candidates

`workflow-design.md` §0.1 口径 10 requires the sweep **before** candidate
collection, with the result written into the report. Three fixed scans:

1. every human-judgment point, checked for a "由人决定" marker (B1);
2. every reachable disposition of the project-layer task P, checked for an
   entry and an exit (A1);
3. the output state of every reconciliation repair type 1–5, checked against
   the ledger/archive combination table (B9).

A gap found by the sweep is fixed in the same version as anything else; it is
not deferred. The sweep also stops the known blind spot where all three
findings are "one unmirrored role", "one unmarked judgment", "one unguarded
repair" and get found one version apart.

## Step 1: Collect Candidates Without Verdicts

For each candidate, record:

- exact `§` / table / line;
- the rule you believe is violated;
- the triggering scenario;
- expected vs actual behavior.

Do not write "impact" yet. Impact is where speculation enters.

## Step 2: Four Filters (Apply In Order)

### F1. Layer filter: design vs implementation vs target project

Ask: "What is the cheapest implementation/usage that follows the document and
still works?" If one exists, it is implementation freedom, not a design defect.

Examples that pass this filter (i.e. are **not** design defects):

- when the mechanism allocates its snowflake ID;
- how a failed commit is rolled back or retried;
- how the single work line switches between tasks.

### F2. Decision-log filter: intentional tradeoff?

Check the §0.1 tradeoff list. Examples: human judgment without extra records,
no evidence chain, no anti-adversarial defense, uninstall-only recovery, no
ledger cleanup, archived tasks immutable, forward-only replacement/abandon,
single work line. Drop the candidate unless the tradeoff violates its own
stated boundary.

### F3. Blank vs conflict

"Not specified" is a blank; it is not a defect. Only "two rules disagree" or
"a rule has no exit" counts. If the document leaves a value open, do not invent
a requirement for it.

### F4. Failure-model filter

Does the scenario come from normal/honest use, or from manual deletion,
tampering, or against-doc bypass? This repository's ordinary-use defect boundary
(see `.trellis/spec/docs/index.md`) excludes the latter from the default defect
model. At most, report it as "outside the model".

## Step 3: Adversarial Validation (Required Before Publishing)

### Rebuttal search

Search the document and companion for the concept before claiming absence:
`rg` the term, check nearby clauses, worked examples, and appendices. If a
clause resolves the apparent problem, downgrade it to "wording".

### End-to-end simulation

Walk the scenario to the document's stated exit. If a permitted path exists
(create/continue a current task, reconciliation type 1, forward completion,
uninstall, etc.), drop the finding.

### Conforming-implementation test

Describe the simplest implementation an honest developer would write from the
document alone. If it satisfies the document without changing it, drop.

### Author's rebuttal

Write the one sentence the author would use to reject the finding, with a `§`.
If you can write it, drop or downgrade. If you cannot, the finding survives.

## When A Finding Survives: How To Fix Without A Patch Layer

- Prefer making the two overlapping rules **mutually exclusive by condition**
  (for example: split a flat table into ordered stages, and scope each stage's
  rows) over declaring "rows are matched top-down". Row order is a cover; the
  overlap stays underneath it.
- When a boundary is narrowed on one side (a target must be active), also check
  the mirror case (may an archived task still serve as the prerequisite?) and
  state both in the same paragraph; leaving one implicit re-creates the defect.
- Change the main document and its companion in the same pass, including both
  version fields; a rule edit with a stale `design:` field is not done.
- Enumerate and update the **same-condition copies** in the same pass: a
  routing row's condition usually has a summary paragraph that restates it
  (§8.4 in workflow-design.md), a mirror table (the other project-state
  table), and related rule sections that reference the same state. Fixing
  one copy and leaving the others re-creates the "same rule, two places"
  defect one occurrence at a time — the v33 fix history hit this three
  times (§9.1 row fix missed §6.8; first-row condition fix missed the
  second row and the §8.4 summary; an archive-state swallow fix missed the
  mirror table). Before declaring a routing fix done, grep the old
  condition's keywords across the document.

## Revision Protocol (For workflow-design.md Fixes)

The v31→v33 history shows one defect family recurring: a predicate defined in
one place, then restated with drifting conditions elsewhere. Fix order and
record-keeping are therefore part of the fix:

1. **Source first, projections second, probes third, revision note last.**
   Edit the single definition (§3, §4.3, §7.5 …), then update every
   referencing location **as a reference** — never as a restated condition —
   then run the predicate probes (see the registry in
   `.trellis/spec/docs/index.md`), then write the appendix revision entry.
   Adding a routing row before its source condition exists is exactly how v33
   reintroduced a restatement v32 had deleted.
2. **Appendix revision entries record; they do not define.** Each entry may
   only state: which source/cell changed, which references and mirrors
   followed, and why. Restating conditions in the revision note creates the
   next drift copy.
3. **Main doc and companion doc change in the same commit**, and the probes
   run against both.
4. **When a fix adds a role or repair rule, write the mirror in the same
   pass** — the sibling role clause, the summary-table row, and the companion
   mirror — then add a probe for the new source phrase so the rule cannot
   disappear silently.

## Step 4: Calibrate The Output

- Main findings: only the four accepted sources, with a concrete impact (which
  phase is forced to change) and a minimal fix (add a judgment / remove
  duplication / change wording; no new mechanism unless separately decided).
- Keep wording/precision items in a separate section; never inflate severity
  with speculative implementation cost.
- Include an **"Excluded (not reported as defects)"** section with the reason
  for each below-threshold candidate. This is required, not optional.
- Report version checks separately. A derived-doc version mismatch is a report
  item, not a design defect.

## Known Structural Blind Spots In This Repo

1. **Unmirrored role.** Every special role needs its exit written where the
   role lives. 收尾任务 has "由人重新定义" (§6.7) and 返工任务 inherits its
   marker (§6.5); P needs its own succession clause (§6.5). When one role's
   clause exists and a sibling role's does not, that is a finding, not a blank.
2. **Repair that breaks what it repairs.** Every 对账修复 type must be checked
   against the combination table for its *output* state. Type 1 carries a
   "前置须全正常" guard; type 3 re-archive must carry the same one.
3. **Unmarked judgment fork.** A fork whose two branches have asymmetric
   irreversibility needs an explicit "由人决定", even when the surrounding
   section is human-led by tone.

## Known False-Positive Patterns In This Repo

1. **Literal-phrase anchoring.** "Archived artifacts are handled by rework" was
   read as "rework the archived task"; the worked example mounts rework on the
   active task, and the same paragraph says the old task's ledger is unchanged.
2. **Section-local scope.** "Iteration-phase edge creation" was read as the only
   authorized edge creation; the baseline-change section already authorizes it.
3. **Implementation-as-design.** Commit-failure handling and ID allocation
   timing are implementation choices, not design gaps.
4. **External error as failure model.** A dangling edge caused by manually
   deleting a task directory is not "any step failed".
5. **Awkward sentence as contradiction.** "Startup reconciliation handles type 5"
   next to "does not change task state" reads badly, but the adjacent clause and
   the handoff section resolve the intent; downgrade to wording.
6. **Format-driven inflation.** The required "impact" field invites speculative
   cost. Require a concrete, unavoidable failure or drop the item.

## Candidate Checklist

- [ ] Exact violated rule cited with `§` / table / line?
- [ ] Rebuttal search done (document + companion + examples + appendix)?
- [ ] Cheapest conforming implementation described and tested?
- [ ] Scenario is honest-use, not external tampering/bypass?
- [ ] Is the state in question produced by an entry action the document itself
      allows? A legal entry action whose result another rule calls illegal is an
      internal contradiction (core rule 1), not a blank.
- [ ] For a routing-row change: is the row's shading recorded — which earlier
      stage/row pre-empts it? A row that can never be reached must be widened
      or removed (dead row).
- [ ] Does the state the row covers have exactly one exit in its table? Two
      exits for one cell means one of them is a stray copy.
- [ ] Not a stated tradeoff?
- [ ] Not merely a blank?
- [ ] Author's rebuttal attempted and failed?
- [ ] Impact concrete and unavoidable, not speculative?
- [ ] Wording-only items moved to the precision section?
- [ ] Acceptance-surface sweep done (口径 10): human-judgment markers, all P dispositions, repair output legality?
- [ ] For any role/orphan gap: is the mirrored sibling role's clause present, and is P's succession covered?
- [ ] Does every touched 对账修复 type still produce a legal archive/ledger combination?

## Output Template

Use this shape so a reader can see the evidence bar, not just the conclusions:

```markdown
## Review conclusion
- Main findings: N
- Wording/precision: N
- Excluded candidates: N
- Version check: ...

## Main findings
### F1 ... (constraint / evidence / source type / impact / minimal fix)

## Wording and precision
...

## Excluded (not defects)
| Candidate | Why excluded |
|---|---|
...

## Version drift (report only)
...
```

## Bottom Line

> A review is not judged by how many problems it finds, but by whether the
> problems it reports can survive the author's rebuttal.
