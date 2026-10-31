# wf Framework Design — Revision Gate

> Distilled from the 2026-10-30 review/revise rounds on `docs/workflows/wf-framework-design.md`
> (r4: six batched judgments, ~35 accepted items; r5: three revision rounds, 6 core gaps +
> 17 absorptions + follow-up corrections). The recurring failure mode is not "we don't know
> what to check" but "we must check it in several places at once and human bandwidth cannot keep
> up" — the fix is a machine gate plus mechanical enumeration steps, not more discipline text.

---

## Scope

Applies to every future revision of:

- `docs/workflows/wf-framework-design.md` — the wf framework design document (how to build and how to accept)
- `docs/workflows/wf-framework-charter.md` — the charter (whether to build, where the boundary is, when to stop)
- `docs/workflows/wf-framework-design.index.md` — the shared unique-definition index table for both documents
- `scripts/validate-wf-design.py` — the design-stage machine checker itself

---

## The gate

1. **Every revision ends with a green checker run** (`python3 scripts/validate-wf-design.py`).
   "Green" means: all seven checks pass **and** coverage metrics meet thresholds —
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

8. **Back-scan by enumeration, not by vigilance (r5).** At the end of every revision, list
   each new cross-section `§` reference added to the body (and each new consumer claimed in
   the index) and confirm the corresponding index rows are back-written — both the lexical
   candidate column and the semantic-consumer column of the *consumed* entry. The checker
   cannot catch semantic back-scans (the matched key does not appear in the consuming
   section). r5 evidence: three consecutive rounds each found missed back-scans (4 rows,
   then 2, then 1) *after* the sync protocol was already written; the enumeration list in
   the revision record is what actually catches them.

9. **A retained rule's judgment input needs a reconstructible source (r5).** When a rule
   keeps a counting or trigger input, define source, ordering, and reset semantics so the
   input is fully reconstructible from durable records; never park trigger state in runtime
   markers. r5 evidence: "连续正常归档任务数" admitted three implementations with different
   long-run behavior; fixed as "cumulative count reaching integer multiples of N, ordered by
   archive time, abnormal archives neither count nor reset, manual runs don't change the
   count — reconstructible from archive records, no runtime marker".

10. **Imported constraints must be checked against co-located rules (r5).** When importing
    a constraint from an upstream project (e.g., a reviewer's "exactly three inputs"), check
    it against every rule in the same paragraph or contract before landing it (e.g., fixed
    check axes that require spec text the input list doesn't carry). Upstream exactness does
    not survive transplantation onto a different check surface; either widen the imported
    rule or narrow the co-located one in the same change.

11. **The acceptance matrix tracks the output model (r5).** When the gate output model gains
    a tier (通过/阻断/需人裁决), the acceptance matrix gains that tier's assertion form in the
    same change (tier + pending fact + exit, not folded into allow/deny columns); every new
    judgment criterion added to the body gets its scenario row in the same change. Gates with
    semantic boundaries get at least one third-tier assertion each, carried in a dedicated
    table (tier, pending fact, exit) rather than folded into the binary rows; the checker
    validates that table's header and per-row completeness.

12. **Absorption is closed until a named gap reopens it (r5).** The four reference projects'
    mechanism surface is covered; remaining differences are tradeoffs, not omissions. Do not
    use "absorb from upstream" as a reason to expand text — a new absorption must first name
    the current gap and the lowest-cost fix (product §8.3 closing rule, enforced at the
    authoring level too).

13. **A new judgment criterion lands in exactly one owner (charter split).** Before writing a rule,
    decide whether it answers "whether/where/until when" (charter `Tn`) or "how/how to verify"
    (design `§x.y`). The owner holds the definition; the other document holds a pointer plus the
    action that consumes it. Moving a rule means deleting the definition sentence but keeping every
    action, gate, and assertion that used it. A charter clause without a design consumer or an
    acceptance row is a dead clause — delete it instead of keeping a principle that changes nothing.
    The checker enforces this mechanically: charter chapters, `charter Tn` pointers, dangling
    consumers, migration residue keywords, one registration row per definition site, and a §8.2
    table row tagged `charter Tn` for every charter item — an index cell alone is not an assertion.

---

## Why these and not others

Real failures from those rounds, each caught by (or catchable by) the gate: a bare external
section reference (`§8.5.3` with no owning document named on the line), 21 missing consumer
sections in the index (consume-hit rate 44%), an unclosed bold marker, a registration table
whose own structure contradicted the rule it carries. They were all mechanical misses under
human-only rescan of a 630-line document.

r5 failures of the same family: an imported reviewer-input boundary that contradicted the
fixed check axes in the same sentence (gate 10); a binary acceptance matrix left behind by
a three-tier output model, plus two new judgment criteria with no scenario rows (gate 11);
a trigger rule whose counting input had no source or reset definition (gate 9); seven index
rows whose new consumers were added to the body but never back-written across three rounds
(gate 8). The r5 rounds also confirmed the positive case: the enumeration list (gate 8)
caught two back-scan misses the same day the rule was written.
