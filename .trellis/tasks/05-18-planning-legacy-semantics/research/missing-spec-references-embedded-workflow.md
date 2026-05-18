# Research: Missing Spec File References in Embedded Workflow

- **Query**: Investigate missing spec file references in /tmp/trellis-0.5.17-2
- **Scope**: Internal
- **Date**: 2026-05-18

## Findings

### Summary of Broken References

There are **3 distinct categories** of broken file references in the embedded workflow project at `/tmp/trellis-0.5.17-2/`.

---

### Category 1: `.trellis/spec/cli/backend/workflow-state-contract.md` -- DOES NOT EXIST

This is the originally reported missing file. It is referenced in 3 carrier directories (`.agents/skills/`, `.claude/skills/`, `.opencode/skills/`).

| Source Location | Referenced Path | Exists? |
|---|---|---|
| `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76` | `.trellis/spec/cli/backend/workflow-state-contract.md` | NO |
| `.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76` | `.trellis/spec/cli/backend/workflow-state-contract.md` | NO |
| `.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76` | `.trellis/spec/cli/backend/workflow-state-contract.md` | NO |

**Source file content** (line 76 of change-task-lifecycle.md in all 3 carriers):
> "If you fork `task.py` to add a new creation path (e.g. an external import that bypasses `cmd_create`), audit whether your path also calls `set_active_task`. Without that call, your created tasks will not surface as active. The full status writer table is in `.trellis/spec/cli/backend/workflow-state-contract.md`."

**Status**: The entire `.trellis/spec/cli/` directory does NOT exist in the embedded project. The embedded project has `.trellis/spec/backend/`, `.trellis/spec/frontend/`, `.trellis/spec/guides/`, `.trellis/spec/scenarios/`, and `.trellis/spec/universal-domains/` -- no `cli/` subdirectory.

---

### Category 2: `.trellis/spec/cli/backend/index.md` and `.trellis/spec/cli/unit-test/conventions.md` -- DO NOT EXIST

These are **example JSONL entries** inside the `trellis-meta` skill reference files. They appear in `spec-system.md` and `task-system.md` as illustrative JSONL format examples.

| Source Location | Referenced Path | Exists? |
|---|---|---|
| `.agents/skills/trellis-meta/references/local-architecture/spec-system.md:71` | `.trellis/spec/cli/backend/index.md` | NO |
| `.agents/skills/trellis-meta/references/local-architecture/spec-system.md:72` | `.trellis/spec/cli/unit-test/conventions.md` | NO |
| `.agents/skills/trellis-meta/references/local-architecture/task-system.md:66` | `.trellis/spec/cli/backend/index.md` | NO |
| `.claude/skills/trellis-meta/references/local-architecture/spec-system.md:71` | `.trellis/spec/cli/backend/index.md` | NO |
| `.claude/skills/trellis-meta/references/local-architecture/spec-system.md:72` | `.trellis/spec/cli/unit-test/conventions.md` | NO |
| `.claude/skills/trellis-meta/references/local-architecture/task-system.md:66` | `.trellis/spec/cli/backend/index.md` | NO |
| `.opencode/skills/trellis-meta/references/local-architecture/spec-system.md:71` | `.trellis/spec/cli/backend/index.md` | NO |
| `.opencode/skills/trellis-meta/references/local-architecture/spec-system.md:72` | `.trellis/spec/cli/unit-test/conventions.md` | NO |
| `.opencode/skills/trellis-meta/references/local-architecture/task-system.md:66` | `.trellis/spec/cli/backend/index.md` | NO |

**Source file content** (spec-system.md line 71-72, all carriers):
```jsonl
{"file": ".trellis/spec/cli/backend/index.md", "reason": "CLI backend conventions"}
{"file": ".trellis/spec/cli/unit-test/conventions.md", "reason": "Test expectations"}
```

**Source file content** (task-system.md line 66, all carriers):
```jsonl
{"file": ".trellis/spec/cli/backend/index.md", "reason": "Backend conventions"}
```

**Status**: These are example JSONL entries demonstrating format. They reference a monorepo `cli` package spec structure that does not exist in the embedded project (which is a single-repo with `backend/` and `frontend/` layers, not a `cli/` package). The examples are potentially misleading because they suggest a structure that doesn't match the target project.

---

### Category 3: `.trellis/spec/cli/backend/auth.md` -- DOES NOT EXIST

Referenced as a usage example in `task.py` help text.

| Source Location | Referenced Path | Exists? |
|---|---|---|
| `.trellis/scripts/task.py:374` | `.trellis/spec/cli/backend/auth.md` | NO |

**Source file content** (task.py line 374):
```
python3 task.py add-context <dir> implement .trellis/spec/cli/backend/auth.md "Auth guidelines"
```

**Status**: Same issue as Category 2 -- the example uses a `cli/backend/` spec path that does not exist in this project. The script's help text shows a monorepo example regardless of whether the target project is a monorepo.

---

### What Spec Structure DOES Exist in the Embedded Project

The embedded project `/tmp/trellis-0.5.17-2/.trellis/spec/` contains:

```
.trellis/spec/
├── backend/
│   ├── index.md
│   ├── database-guidelines.md
│   ├── directory-structure.md
│   ├── error-handling.md
│   ├── logging-guidelines.md
│   └── quality-guidelines.md
├── frontend/
│   ├── index.md
│   ├── component-guidelines.md
│   ├── directory-structure.md
│   ├── hook-guidelines.md
│   ├── quality-guidelines.md
│   ├── state-management.md
│   └── type-safety.md
├── guides/
│   ├── index.md
│   ├── code-reuse-thinking-guide.md
│   └── cross-layer-thinking-guide.md
├── scenarios/discovery-and-planning/solution-comparison/
│   ├── normative-rules.md
│   ├── overview.md
│   ├── scope-boundary.md
│   └── verification.md
└── universal-domains/
    ├── architecture/system-boundaries/
    ├── product-and-requirements/acceptance-criteria/
    ├── product-and-requirements/prd-documentation/
    ├── product-and-requirements/prd-documentation-customer-facing/
    ├── product-and-requirements/prd-documentation-developer-facing/
    ├── product-and-requirements/problem-definition/
    ├── product-and-requirements/requirement-clarification/
    ├── product-and-requirements/scope-boundary/
    ├── project-governance/readme-governance/
    └── verification/evidence-requirements/
```

No `cli/` subdirectory exists.

---

### Source Project Analysis

In the source project `/ops/projects/personal/ai-coding-toolkit/`:

1. **`.trellis/spec/cli/` does NOT exist either.** The source project has `.trellis/spec/platforms/cli/` (which contains `command-interface/` spec docs), but NOT `.trellis/spec/cli/backend/`.

2. **`workflow-state-contract.md` does NOT exist anywhere** in the source project's spec tree. Previous research tasks (archived under `.trellis/tasks/archive/`) have confirmed this file was never checked in. The reference is a stale residual from an earlier version.

3. **The same broken references exist in the source project** -- the `trellis-meta` reference files in `.agents/skills/`, `.claude/skills/`, `.opencode/skills/` all contain the same stale references to `.trellis/spec/cli/backend/workflow-state-contract.md` and `.trellis/spec/cli/backend/index.md`.

4. **The install-workflow.py script** at `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py` copies these reference files verbatim from the workflow assets into the target project, without sanitizing spec path references. The script does not check whether referenced spec files actually exist in the target.

---

### Other Reference Integrity Check: workflow-docs Files

The two `.trellis/workflow-docs/` files referenced by multiple skill SKILL.md files DO exist:

| Referenced Path | Exists? |
|---|---|
| `.trellis/workflow-docs/需求变更管理执行卡.md` | YES |
| `.trellis/workflow-docs/源码水印与归属证据链执行卡.md` | YES |

---

### Other Reference Integrity Check: `assessment.md` and `risk-analysis-guide.md`

These are referenced in the `feasibility` SKILL.md as task-level output files (written to `$TASK_DIR/assessment.md` and `$TASK_DIR/risk-analysis-guide.md`). These are **not pre-existing files** -- they are generated by the workflow during execution. Not broken references.

---

### Other Reference Integrity Check: `inject-workflow-state.py` in workflow.md

Previous archived tasks reported that the source project's `workflow.md` referenced `inject-workflow-state.py` at a wrong path. In the current embedded project at `/tmp/trellis-0.5.17-2/`, the `workflow.md` (410 lines) does NOT contain any reference to `workflow-state-contract.md` or `inject-workflow-state.py` as a file path. This suggests the embedded workflow.md was already patched to remove those stale references.

---

### Complete Inventory of All `.trellis/spec/cli/` References in Embedded Project

| # | Source File | Line | Referenced Path | Nature | Broken? |
|---|---|---|---|---|---|
| 1 | `.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 76 | `.trellis/spec/cli/backend/workflow-state-contract.md` | Authoritative doc reference | YES |
| 2 | `.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 76 | `.trellis/spec/cli/backend/workflow-state-contract.md` | Authoritative doc reference | YES |
| 3 | `.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | 76 | `.trellis/spec/cli/backend/workflow-state-contract.md` | Authoritative doc reference | YES |
| 4 | `.agents/skills/trellis-meta/references/local-architecture/spec-system.md` | 71 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 5 | `.agents/skills/trellis-meta/references/local-architecture/spec-system.md` | 72 | `.trellis/spec/cli/unit-test/conventions.md` | JSONL example | YES |
| 6 | `.agents/skills/trellis-meta/references/local-architecture/task-system.md` | 66 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 7 | `.claude/skills/trellis-meta/references/local-architecture/spec-system.md` | 71 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 8 | `.claude/skills/trellis-meta/references/local-architecture/spec-system.md` | 72 | `.trellis/spec/cli/unit-test/conventions.md` | JSONL example | YES |
| 9 | `.claude/skills/trellis-meta/references/local-architecture/task-system.md` | 66 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 10 | `.opencode/skills/trellis-meta/references/local-architecture/spec-system.md` | 71 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 11 | `.opencode/skills/trellis-meta/references/local-architecture/spec-system.md` | 72 | `.trellis/spec/cli/unit-test/conventions.md` | JSONL example | YES |
| 12 | `.opencode/skills/trellis-meta/references/local-architecture/task-system.md` | 66 | `.trellis/spec/cli/backend/index.md` | JSONL example | YES |
| 13 | `.trellis/scripts/task.py` | 374 | `.trellis/spec/cli/backend/auth.md` | Help text example | YES |

**Total: 13 broken references, all pointing under `.trellis/spec/cli/` which does not exist.**

---

### Severity Assessment

| Category | Severity | Impact |
|---|---|---|
| `workflow-state-contract.md` (entries 1-3) | **Medium** | Direct authoritative doc reference. An AI reading the `change-task-lifecycle.md` reference would be told to consult a file that does not exist, losing the "full status writer table" information. |
| JSONL `cli/backend/index.md` examples (entries 4-12) | **Low** | These are illustrative format examples in documentation. They don't directly cause runtime failures, but they mislead by showing a monorepo structure that doesn't match the target project type. |
| `task.py` help text example (entry 13) | **Low** | Help text example. Same misleading-structure issue. |

---

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | Contains line 76 stale reference to `workflow-state-contract.md` |
| `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/local-architecture/spec-system.md` | Contains lines 71-72 JSONL examples with `cli/` paths |
| `/tmp/trellis-0.5.17-2/.agents/skills/trellis-meta/references/local-architecture/task-system.md` | Contains line 66 JSONL example with `cli/` path |
| `/tmp/trellis-0.5.17-2/.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.claude/skills/trellis-meta/references/local-architecture/spec-system.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.claude/skills/trellis-meta/references/local-architecture/task-system.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-meta/references/local-architecture/spec-system.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.opencode/skills/trellis-meta/references/local-architecture/task-system.md` | Same as .agents version |
| `/tmp/trellis-0.5.17-2/.trellis/scripts/task.py` | Contains line 374 help text with `cli/` path example |
| `/ops/projects/personal/ai-coding-toolkit/.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md` | Source version -- has SAME stale reference |
| `/ops/projects/personal/ai-coding-toolkit/.agents/skills/trellis-meta/references/local-architecture/spec-system.md` | Source version -- has SAME stale reference |
| `/ops/projects/personal/ai-coding-toolkit/.agents/skills/trellis-meta/references/local-architecture/task-system.md` | Source version -- has SAME stale reference |
| `/ops/projects/personal/ai-coding-toolkit/docs/workflows/新项目开发工作流/commands/install-workflow.py` | Install script -- copies references verbatim without validation |

### Related Specs

- `.trellis/spec/platforms/cli/command-interface/` -- the only `cli/` spec that DOES exist in the source project (under `platforms/`, not under `spec/` directly)
- Archived task `.trellis/tasks/archive/2026-05/05-16-workflow-source-analysis/research/issue-9-maintenance-reference-residues.md` -- previous research documenting the same issue

## Caveats / Not Found

- The `workflow-state-contract.md` file has never existed in the source project at the referenced path. Previous archived tasks confirm it was likely a design artifact that was never checked in, or was from an earlier version.
- The source project also has these same broken references -- this is not an embed-specific problem. The fix needs to happen in the source workflow assets first.
- I did not verify the install-workflow.py script in detail (line-by-line) to confirm whether it has any spec-path sanitization logic; a quick search showed it copies trellis-meta references verbatim.
- The `trellis-meta` skill reference files are duplicated across 3 carrier directories (`.agents/skills/`, `.claude/skills/`, `.opencode/skills/`), which means any fix must be applied to all 3 in the source, and the install script will propagate all 3.
