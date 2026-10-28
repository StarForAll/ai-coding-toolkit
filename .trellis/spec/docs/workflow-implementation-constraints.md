# Workflow Implementation Constraints

> Compact guardrail set for implementing `docs/workflows/workflow-implementation.md`.
> The plan is the single source of truth; this file only restates the rules a future
> session must not re-derive or quietly relax. If this file and the plan disagree,
> the plan wins and this file is the defect.

---

## Authority order

| Layer | Document | Rule |
|---|---|---|
| Design | `docs/workflows/workflow-design.md` (+ `依赖机制设计说明.md`) | Judgments and transitions; never overridden by implementation detail |
| Implementation | `docs/workflows/workflow-implementation.md` | Paths, commands, gates, platform matrix, upgrade/uninstall |

A conflict between the two must be registered in the plan's §9 register and decided
by the operator. Never silently pick the more convenient side. `1.2-零补丁嵌入方案.md`
is a superseded historical source that the operator plans to delete; it is not authority.

---

## State and records

- Task status: **only** `planning` / `in_progress` / `completed`. Never write `wf-*` or any
  private value into `task.json.status`.
- Dependency state lives **only** in `.trellis/dependencies/ledger.json`. Never hand-edit it;
  `wf repair` is the only repair entry.
- Per-task mechanism facts live in `task.json` `meta.wf.deps` — one key, serialized JSON,
  written through `task.py set-meta`.
- `meta.wf.deps.in_graph` is the **only** in-graph / out-of-graph discriminator. Do not infer
  it from "does `meta.wf.deps` exist" or "does it have `prereqs`".
- **No evidence chain.** Completion = human judgment + archive. Do not add verification
  records, `impl_sha`, or `self-hash` trust roots.

---

## Mechanism entries

- In-graph start/close go through the module CLI only. Direct `task.py` calls are **reported**
  by `wf doctor`, not blocked.
- `wf start` must pass `--allow-empty-context`: the module dispatches no Trellis sub-agents,
  so the context-manifest gate protects nothing here.
- `wf close` must pass `--skip-branch-validation` **and** assert `pr_url is None` first.
  A single work line is by definition never PR-backed; the upstream gate assumes PR metadata.
- `wf task new --from-graph <key>` is the only way to materialize tasks from P's graph, and
  must run in topological order (a node's prerequisites must already exist).
- `wf task new --role project` is the **only** entry that does not require an archived P —
  otherwise the first P could never be created. Every other entry requires an archived,
  ledger-normal P. Keep this exception in the parameterized-entry table, not in a footnote.
- Graph roots get `prereqs = { P's dependency id }`; non-root nodes list only in-graph keys.

---

## Writes and commits

- **Write-time clean check first**: if the target file already carries uncommitted changes
  unrelated to this mechanism write, refuse and report. Do not "commit everything" to get past it.
- The mechanism commits its **own single path** immediately; do not rely on
  `session_auto_commit` for mechanism facts.
- The ledger commit always follows the archive commit — that ordering is what makes
  "downstream sees normal" imply "already archived".

## Uninstall restore basis

Managed-file restore (the `default_workflow` line and the four ZCode hook commands) resolves its
baseline in three tiers:

1. local snapshot under `.trellis/.runtime/wf/pre-install/`;
2. **git history** — first commit that introduced our text, take that commit's parent version;
3. neither available → fail-closed: print a preview, modify nothing, ask the operator.

A fresh clone has no tier-1 snapshot because `.runtime/` is gitignored. That is the normal case:
fall through to tier 2, do not treat it as an error and never skip the restore.

---

## Versions and evidence

- Read versions from the repo (`.trellis/.version`, `trellis --version`, upstream `git log -1`).
  **Never write a version from memory** — this exact mistake happened once and is recorded as
  plan §9-C10.
- Every claim about upstream behavior must be tagged `实测` / `读码` / `文档` / `推断`.
  Line numbers are not citable; use function name + canonical path.
- `T_min = 0.7.0-beta.0`, `T_max = 0.7.0-beta.4` (closed range, only measured versions).

---

## Platforms

- **Required capabilities must never depend on hooks.** Every gate is state-based.
- Platform differences appear only in the plan's platform matrix and the frontmatter renderer;
  skill bodies stay platform-neutral.
- Supported platforms: Claude Code, Codex, ZCode, Pi, DSH. Anything else gets generic L1/L2
  support only — never claim "supports all agents".
- ZCode: `.zcode/config.json` is the **single** managed-file exception (T1c). Hook commands must
  keep the git-root fallback and `exit 0`. After every `trellis update`, diff it against the
  upstream template and re-run checks Z1–Z5.

---

## Before implementation

Move the existing old module (`docs/workflows/新项目开发工作流/`) into
`tmp/新项目开发工作流/` (gitignored, read-only reference), then build the new module source at
`docs/workflows/新项目开发工作流/`. See plan §2.1; without this step the paths in the plan point
at the old assets.

---

## Variant rendering (measured, 0.7.0-beta.4)

These four facts come from `trellis/scripts/common/workflow_phase.py` and were re-checked in a
throwaway fixture on 2026-10-28. Do not re-derive them from the docs.

- **Index boundaries are literal.** `get_phase_index` starts at a line exactly `## Phase Index`
  and stops at a line exactly `## Phase 1: Plan`. With no such terminator the whole rest of the
  file (step bodies included) is injected as the index. A variant must contain that literal line.
- **`--mode phase` never returns the state blocks.** Both `[workflow-state:*]` blocks and HTML
  comments are stripped before output. Assert the sentinel through the phase output; assert the
  three state blocks with a file-level regex (the platform channel is probe W7).
- **Steps are `#### X.Y`.** A step body ends at the next `####`, the next `## `, or a column-0
  `---`. No column-0 horizontal rules inside a variant.
- **Marker-shaped lines are swallowed.** `filter_platform` treats any standalone line matching
  `^\[<letter>…\]$` as a platform marker and drops it plus its block when the platform does not
  match. Keep template lines out of that shape; the sentinel must be plain text.

---

## Known traps

| Trap | Why it bites | Rule |
|---|---|---|
| `task.py archive` branch gate | `branch == base_branch` is a **hard refusal** (`return False`); only a missing local branch is a warning | Always pass `--skip-branch-validation` from `wf close`, after asserting `pr_url is None` |
| `task.py create` dates | Directory is `{today MM-DD}-{slug}`; a `--slug` carrying another date is rejected | Locators must be **slug-only**; never store a date-prefixed path in the ledger |
| Slug collisions | `create` refuses an existing directory but happily creates the same slug under a different date | The module must enforce slug uniqueness across active + archive areas |
| P creates tasks too early | `wf task new` requires an archived P, so nothing can be created during P | The tail task is defined in P's graph block, not as a pre-created directory |
| Derived DAG file | A persisted `dag.md` would drift and add noise | There is no `dag.md`; use `wf dag` output |
| P0 read-only commands need the ledger | §8.2 puts `route`/`state`/`dag`/`check` in P0 but "ledger read/write" in P1, while §3.7 and §3.8 both read the ledger | Plan §9.7 M1 (pending): ledger **read** moves into the first mechanism task; ledger **write** stays in P1 |
| P0 roundtrip needs `wf close` | §8.2's P0 exit criterion is the §7.6 roundtrip "start through close", but `wf close` is P1 | Plan §9.7 M2 (pending): the minimal `wf close` belongs to the same task, or P0 ships a state where in-graph tasks can only be closed natively |

---

## Where to read more

- Plan: `docs/workflows/workflow-implementation.md` — §3 (state / ledger / entries), §4 (platforms),
  §5 (ZCode hardening), §7 (upgrade / uninstall), §9 (conflicts and decisions).
- Design: `docs/workflows/workflow-design.md` — §2 invariants, §4 states, §7 dependency mechanism.
