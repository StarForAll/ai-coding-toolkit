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

3. **Keep lexical candidates and semantic consumers separate.** The index has six columns:
   ID, definition, lexical candidates, redefinition sites, semantic consumers with reasons,
   and review state. The checker consumes the third column; regenerate only that column
   from literal matches, preserving the fifth and sixth columns. A 100% lexical hit rate
   does not establish semantic coverage. Same-name-different-sense candidates use
   `排除：§X=reason`; never silently remove a match or hand-fill candidates from memory.

   Review state distinguishes `未核对`, `已核对·有消费`, and `已核对·仅定义节`.
   No literal match is not evidence of no semantic consumer. For gates, states, pointers,
   records, and assets, trace each claimed consumer back to an actual clause/action in
   the current body. An intended action absent from the body is a gap, not a verified
   consumer. Record the missing action or withdraw the claim; do not certify intent.

4. **Optional improvements go to the candidate list** (design doc §8.3) unless the user
   explicitly authorizes the concrete revision. User-authorized P2/P3 fixes are not blocked
   by the default candidate rule. Keep dispositions in task records rather than appending
   round histories to product rules.

5. **Rewrites must preserve each retained rule's inputs and ownership.** For a statistic,
   check which durable record supplies it and how missing data differs from zero. For a
   managed document or project configuration, record the target path, writer, upgrade policy,
   and consumers. Runtime caches must not silently become historical evidence. Compare
   dependent clauses after changing these contracts; one locally correct sentence is insufficient.

6. **Product evidence links must survive task archival.** Use the stable
   `docs/workflows/wf-framework-design.sources.md` plus immutable commit/file identifiers;
   do not point product docs at an active task directory that `task.py archive` will move.
   Task-local reports may retain historical line anchors if they explicitly name the baseline.

7. **Separate design acceptance from implementation validation.** Record the user's actual
   review decision without inventing independent-session or runtime evidence. Run the checker
   and review the changed contracts, then stop expanding text review when the agreed scope
   is resolved. The next implementation stage owns executable fixtures and runtime claims.

---

## Why these and not others

Real failures from those rounds, each caught by (or catchable by) the gate: a bare external
section reference (`§8.5.3` with no owning document named on the line), 21 missing consumer
sections in the index (consume-hit rate 44%), an unclosed bold marker, a registration table
whose own structure contradicted the rule it carries. They were all mechanical misses under
human-only rescan of a 630-line document.
