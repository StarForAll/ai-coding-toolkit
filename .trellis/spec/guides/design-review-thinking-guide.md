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
- [ ] Not a stated tradeoff?
- [ ] Not merely a blank?
- [ ] Author's rebuttal attempted and failed?
- [ ] Impact concrete and unavoidable, not speculative?
- [ ] Wording-only items moved to the precision section?

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
