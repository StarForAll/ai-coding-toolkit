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
collection, with the result written into the report. Six fixed scans (follow the current main document if its contract evolves):

1. every human-judgment point, checked for a "由人决定" marker (B1);
2. every reachable disposition of the project-layer task P, checked for an
   entry and an exit (A1);
3. the output state of every reconciliation repair type 1–5, checked against
   the ledger/archive combination table (B9);
4. overlapping rules over the same case, including load-bearing field axes;
5. closed assertions and the paths each assertion covers;
6. identification fields × roles × repair entrances, including the intersection
   of allowed writes and prohibitions.

Replay repeated actions on the same object, not just one instance of each
operation. Compare committed snapshots across recovery windows: identical
readable facts cannot select opposite automatic recoveries. A native task may
exist before mechanism metadata is committed; check how it is located and
excluded from ordinary routing without assuming a cross-system transaction.

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
5. **After a dedup, replay every consumer's exception.** Before deleting a
   copy, list the callers of the collapsed rule, collect the exceptions each
   caller relied on, and register them at the surviving source (§0 写作约定,
   added in v38).
6. **Enumerate the copies before editing, fill the sync result after.** For
   every changed judgment, write down the copy sites (source, summary table,
   handoff section, companion) in the fix notes and mark each one
   synced / demoted to a reference / intentionally different with a reason.
   A missing line is not done (§0 写作约定 + 口径 11, tightened in v39).

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
4. **One-sided edit.** A table or clause that is mirrored in the companion doc
   (组合自检表, the lifecycle rules, the ledger transition table) is changed in
   the main doc only. The companion is half the authority (§7.9: "机制细节冲突以
   配套文档为准"), so a missing mirror row makes a conforming implementation run
   into a hole. A version gate that only compares `design:` fields passes the
   whole time. When a touched line has a mirror, state the sync result (synced, or
   intentionally different with a reason); `rg` the changed line's characteristic
   words across both docs and require matching counts.
5. **Multi-step write with no mid-state.** A new or rewritten "sequential +
   recoverable" action (reconciliation repair type, replacement/abandon
   implementation, rework) written only to its end state. Every window needs a
   residual signature and a forward completion; the signature's marker must be
   written with the first step. §7.7's 类型 1 P branch shipped without this in
   v36: its crash residual (`archived + 异常 + no pointer + no reason`) was
   neither re-detected as type 1 (input is 无记录/挂起) nor as type 5 (needs a
   pointer or a reason), and the combination table called it legal (row 5).
   Endpoint-only scans (口径 10) and reference replay (口径 12) both pass such a
   path — 口径 13/14 exist for this class and its mirror (intra-document
   duplicate copies).
6. **A reference used as an exit.** "按 §6.5 执行" is written and counted as an
   exit, but the target section opens with "只适用于未归档任务" and the caller is
   an archived task. Naming an entry and an exit is not enough: walk every new
   "按 §N" into its target and check each precondition against the calling
   context; if it fails, add the exemption in the same version (type 5 carries
   the template: "不重跑实施前静态校验").
7. **角色换 ID 只补一面.** When a role's identity can change (P via
   replacement, 放弃-新建替代, or type-1 rebuild), six faces must be restated
   for the role: 规则面 (which disposition rules apply to the successor),
   身份面 (where the successor's identity is persisted), 入口面 (which routing
   row selects it), 验收面 (B9/A1 wording), 场景面 (§10 self-check), 镜像面
   (companion copies). v38 found three of these missing across v35–v37
   (F1/F2/F3) — one per version, because each round stopped after补了归属.
8. **Dedup creates orphan exceptions.** 口径 11 tells you to collapse copies
   into one surviving source. The surviving text must then carry every
   exception that any caller relied on; otherwise an exception living in a
   local clause becomes an orphan and collides with the collapsed source
   (v38 F1: §7.4 collapsed, the P exception stayed local in §7.7).
9. **Main-site-only fix.** A rule usually has summary copies: routing tables,
   the handoff section (接手), and the companion. Editing only the source
   leaves the summary stating the old disposition. v38 added the ready-task
   row to §9.1 but left §8.4's third stage restating "等前置" — the same
   rule, two versions. Before editing, list the copies; after editing, give
   each one a sync result. 口径 11 now requires that list in the report.
10. **Exception registered by source or role.** A limitation that enumerates its
   exceptions by provenance ("一般任务 / P 例外") goes stale the moment a new
   producer appears: v36–v38 patched the same §7.4 cell once per version, and
   v39 added a new disposition (改判放弃) the list did not cover, so the
   archived-old-task cell ended up with two conflicting dispositions (§7.4
   "只余删边" vs §7.7 类型 5 "补建"). Fix pattern: write the limitation as a
   **state / field predicate** (v40: "处分未完成 = 替换指向仍在 / 下游仍指向
   该任务 / 该任务未归档") and keep identification field-based — never a source
   list. A role property (P must always have a successor) may stay a separate
   sentence, written once.
11. **Action sequence defined twice, in different orders.** The same forward
   completion chain existed as an archive-first list (§6.5 / 配套 §6.4) and a
   build-first sentence (§7.7 类型 5). Order is load-bearing: archiving first
   makes the later 补建 look like "替换一个已归档任务", i.e. exactly the state
   the disposition rule forbids. Fix pattern: exactly one declared source per
   multi-step sequence (v40: §7.7 类型 5), mirrors stay same-order and
   reference-only, and §0 now bans a second sequence with a different order.
12. **Predicate rewritten without reachability accounting.** When a limitation
   is rewritten as a field predicate (v40 §7.4), the terminal shape must be
   evaluated on every producing path of the state it judges; v40 induced
   "pointer empty" from the 删边 variant alone while five paths keep the
   pointer, so the terminal was unreachable on daily success paths. The
   revision note claimed "一次覆盖四种形态" as an assertion, and every
   text-level gate (copy list, reference replay, window table, same-order
   mirror) passed — only a path-accounting table catches it. Fix pattern: the
   revision note must carry a path-accounting table (each producing path →
   predicate verdict); a coverage claim without the table is not done.
   Companion obligations: register a probe for the predicate's characteristic
   phrase and actually run the probes per revision — a registered probe with
   a stale expected value that nobody runs is how this class escapes (v41
   §0.1 口径 11③ added the run obligation).

13. **Historical records mask a new registration.** A cumulative rework set
    can be nonempty and fully archived while a second rework has not been
    created. Enumerate prepare/create/publish/cancel windows and the current
    intent that distinguishes them. A row or marker merely existing is not a
    recovery proof; check replay, cancellation from an already suspended state,
    and activation with old ambiguous data. The v42 source is 主稿 §6.4; mirrors
    reference it instead of defining another sequence.
14. **A reference calls a predicate outside its domain.** The v41 P parser
    applied the abnormal-disposition terminal predicate to a normally completed
    successor, whose legal downstream edges remain. Record input domain and
    downstream quantifier for each reused predicate; same words or one source
    do not imply the call is valid. Archived-but-unreconciled is distinct from
    normally completed. Source: 主稿 §6.5 / §7.4.
15. **Repair permission intersects a business prohibition.** A matrix saying
    “sole clear point” while type 4 permits clearing is still inconsistent in
    one table. Test allowed input/output tuples against every prohibition.
    Preserve recovery of legitimate empty values, a prewritten successor ID
    whose task does not exist yet, and archived rework-origin corruption, while
    forbidding creation of new relationships or rollback to an obsolete one.
    Source: 主稿 §7.8. Text-hit counts prove locations, not permission semantics.
16. **Creation-time writes bypass mechanism validation.** Task creation writes
    the prerequisite set directly and never passes §7.5's edge-change
    validation (which covers 建边 / 返工加边 / 重连 only). A rule that is wrong
    about creation-time sources survives every mechanism-path test because the
    mechanism never sees the write. Enumerate the 任务定义 path family
    （创建期写 deps / 收尾重定义 / 基线变更新建） as its own family in 口径 10⑤ —
    never fold it into 继承 or 建边 (v46: §4.4 三族表 is the sole source).
17. **“能跑通” ≠ “规则成立”.** A scenario passing only because no check runs
    on it is evidence of a blind spot, not of correctness. When enumerating
    paths for a closed assertion, verify the rule text against every
    producing family — not only the families the mechanism intercepts.
18. **A new permission must be scope-limited.** When an exception grants a new
    permission (for example, regenerating an occupied identifier as a carrier
    correction), state exactly which field and object it applies to; an
    unscoped permission leaks into adjacent invariants (v46: §7.8 类型 4
    恢复边界 now limits the regeneration license to 任务自身的依赖标识 and keeps
    P succession outside it).
19. **After editing one rule, search for the same-action opposite sentence.**
    A restriction tightened on one line (“不另生成 ID”) can coexist with its
    inverse permission elsewhere (“重新生成后重校验”); until the domains are
    split, the two sentences contradict on the same case (v46: §6.4 now
    separates 位置占用 from 标识占用). Grep the action's verbs across both
    documents before declaring consistency.
20. **A gate written stricter than the artifact it judges.** A new review
    gate or writing obligation worded at a different granularity than the
    existing artifact fails every conforming row when applied literally:
    v47 mandated the literal phrase 「此路径不变」 the matrix never used (R2),
    then per-cell producer references where the matrix's terminal-value cells
    write values, not producers (R3) — each time the executor's reconciling
    interpretation lived only in the task's fix-notes. Fix pattern: in the
    introducing version, either align the artifact cells to the gate verbatim
    or reword the gate to the artifact's actual granularity (write the
    terminal value, or an unchanged-reason, or a provenance note), and merge
    the reconciling口径 into the gate text itself. Source: 主稿 §0.1 口径 10⑥
    × §7.8 矩阵.
21. **Line numbers in records drift every round.** Editing a table above a
    cited line shifts every later reference (v47: four consecutive rounds of
    `:825 → :826` style drift). Locate edits by text anchors; cite line
    numbers as reference-only and correct them in the same pass the record is
    touched.
22. **轴内 0 被读成全域 0（验收轴镜像化）。** 每轮复核轴等于上一轮发现的原样镜像，轴跑完即报 0；下一轮换轴立刻出新发现（v47 四轮：镜像→闸口短语→闸口语义→措辞，末轮 0 条后仍有 3 条主发现存活）。修复规则：新规则同版必配验收位（场景或 probe），否则视为未落地；“0 条”只对已跑轴有效。
23. **例外只落在调用点，源规则仍在拒绝（调用点清单 ≠ 规则清单）。** 修一个判定时只列出被点名的动作位、漏掉统一校验源，例外写满五个调用位而源括号（一处括号同时管建边 / 加边 / 重连）仍在拒绝——同一动作在两条路径上判定相反（v48 复核：§7.5 的「目标不是异常」括号同时管重连，五处动作位例外 + 源未改 = F3 未闭合）。修复规则：改动判定先列「规则源 + 全部调用位」清单，例外必须写在源位、调用位只留引用；对借来谓词的域判断必须配 probe（凭“那是另一域”的口头判断无成本即出错）；none 验收位必须配机械兜底（改动行括号平衡、记录 § 标签与实际章节一致），否则被改坏的句子恰好就是没有验收位的那句。
24. **同义重复让条件有了两种读法，且主发现缺作者反驳。** 同一条件写成「不得建边」与「目标不是异常」两处时，读者会把前者泛读；只改一处等于留下可当场否掉例外的副本。反过来，主发现若依赖某指称，先查节内同词既有用法再判是否真缺定义——缺定义与“定义在上下文里”是两回事。修复规则：给重复条件加域（建边目标 / 重连目标）、指称在源位写死一次；每条主发现必写作者反驳并测试。

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
- [ ] All six acceptance scans done (口径 10), including field axes, closed assertions, and field/role/repair permissions?
- [ ] Every copy of a touched rule compared — intra-document and cross-doc (口径 11): synced, demoted to a reference, or divergence justified?
- [ ] Every new "按 §N" walked into its target section and its preconditions checked against the calling context (口径 12)?
- [ ] For every new or rewritten multi-step action: crash windows enumerated, each residual has a unique
      signature, and marker fields are written with the first step (口径 13)?
- [ ] Repeated-operation windows distinguishable by committed facts; native-created/unpublished tasks located and blocked; cancellation preserves earlier work?
- [ ] Referenced predicates applied within their role/state domain; allowed repairs disjoint from business prohibitions except explicit source-owned recovery exceptions?
- [ ] Each residual signature reachable from startup self-check, a table-row note, or a type-identification
      sentence — not only from «报告阻塞» (口径 14)?
- [ ] For any role/orphan gap: is the mirrored sibling role's clause present, and is P's succession covered?
- [ ] For any role whose identity can change: are all six faces restated (rule / identity / entry / acceptance / scenario / mirror)?
- [ ] For any collapsed duplicate: does the surviving source carry every caller's exception?
- [ ] Did you enumerate every copy site of the changed rule (source / summary / handoff / companion) and fill a sync result for each?
- [ ] Is every limitation a **state / field predicate** rather than a list of
      sources or roles (blind spot 10)?
- [ ] For every multi-step action: does exactly one place own the step order, and
      is each mirror same-order and reference-only (blind spot 11)?
- [ ] For any two rules that can hit the same case: is there exactly one disposition (情形矩阵, 口径 10 ④)?
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
