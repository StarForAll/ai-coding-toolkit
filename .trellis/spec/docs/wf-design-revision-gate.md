# wf Framework Design — Revision Gate

> Distilled from the 2026-10-30 review/revise rounds on `docs/workflows/wf-framework-design.md`
> (six batched judgments, ~35 accepted items). The recurring failure mode was not "we don't know
> what to check" but "we must check it in several places at once and human bandwidth cannot keep
> up" — the fix is a machine gate, not more discipline text.

---

## Scope

Applies to every future revision of:

- `docs/workflows/wf-framework-design.md` — the wf framework design document
- `docs/workflows/wf-framework-design.index.md` — its unique-definition index table
- `scripts/validate-wf-design.py` — the design-stage machine checker itself

---

## The gate

1. **Every revision ends with a green checker run** (`python3 scripts/validate-wf-design.py`).
   "Green" means: all four checks pass **and** coverage metrics meet thresholds —
   definition-hit rate and consume-hit rate ≥ 90%, reference-check residual reported
   (informational, no threshold). A checker run that merely executes is not a pass; coverage
   is part of the pass criteria.

2. **The checker must assert its own coverage.** Its blind spots have no upper layer to catch
   them ("a net with the mesh on the silent side is no net" applies to the checker itself).
   When extending the checker, extend its coverage output in the same change.

3. **Index-table consumer column = machine-generated candidates + human confirmation.**
   The checker diffs "sections where the key literally appears" against the column; gaps FAIL.
   Same-name-different-sense candidates are rejected via **exclusion annotations**
   (`排除：§X=reason`) recorded inside the cell — the section number stays in the line so the
   checker counts it as human-adjudicated. Never hand-fill the column from memory.

4. **Non-P1 revision requests go to the candidate list** (design doc §8 item 7), not directly
   into the document. When a candidate class is empty, the list must state where the previous
   round's leftovers were disposed of (empty-table self-check).

---

## Why these and not others

Real failures from those rounds, each caught by (or catchable by) the gate: a bare external
section reference (`§8.5.3` with no owning document named on the line), 21 missing consumer
sections in the index (consume-hit rate 44%), an unclosed bold marker, a registration table
whose own structure contradicted the rule it carries. They were all mechanical misses under
human-only rescan of a 630-line document.
