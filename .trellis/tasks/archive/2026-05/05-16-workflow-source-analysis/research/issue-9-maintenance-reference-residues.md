# Research: Issue 9 - Maintenance reference residues

- **Query**: Does workflow.md point to non-existent files like workflow-state-contract.md and inject-workflow-state.py?
- **Scope**: Internal
- **Date**: 2026-05-16

## Findings

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.16-2/.trellis/workflow.md` (line 105, 696-697) | Contains stale references |
| `/tmp/trellis-0.5.16-2/.agents/skills/trellis-meta/references/.../change-task-lifecycle.md` (line 76) | Contains stale reference |
| `/tmp/trellis-0.5.16-2/.claude/skills/trellis-meta/references/.../change-task-lifecycle.md` (line 76) | Duplicate stale reference |
| `/tmp/trellis-0.5.16-2/.opencode/skills/trellis-meta/references/.../change-task-lifecycle.md` (line 76) | Duplicate stale reference |

### Analysis

#### Reference 1: `inject-workflow-state.py` in workflow.md

**workflow.md line 105 (breadcrumb contract comment):**
```
inject-workflow-state.py (Python platforms) and
inject-workflow-state.js (OpenCode plugin) only parse them
```

This is inside an HTML comment block (lines 99-140) that explains the breadcrumb contract. It references `inject-workflow-state.py` as a generic name for the hook scripts.

**workflow.md lines 696-697 (full contract section):**
```
- `.claude/hooks/inject-workflow-state.py` — Python parser implementation
- `.codex/hooks/inject-workflow-state.py` — Codex parser implementation
- `.opencode/plugins/inject-workflow-state.js` — OpenCode parser implementation
```

**Actual locations:**
- `.claude/hooks/inject-workflow-state.py` -- EXISTS (correct)
- `.codex/hooks/inject-workflow-state.py` -- EXISTS (correct)
- `.opencode/plugins/inject-workflow-state.js` -- Not checked but assumed to exist

**Verdict on this reference:** The workflow.md references are CORRECT. The hooks actually exist at `.claude/hooks/` and `.codex/hooks/`. The path `.trellis/scripts/inject-workflow-state.py` does NOT exist and is NOT referenced anywhere in the embedded project.

#### Reference 2: `workflow-state-contract.md` in trellis-meta skills

**Found in 3 locations** (all copies of the same file):
```
.agents/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76
.claude/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76
.opencode/skills/trellis-meta/references/customize-local/change-task-lifecycle.md:76
```

Each contains:
```
The full status writer table is in `.trellis/spec/cli/backend/workflow-state-contract.md`.
```

**Actual status:**
```
.trellis/spec/cli/backend/workflow-state-contract.md -- DOES NOT EXIST
```

**Verdict on this reference:** This is a REAL stale reference. The file does not exist. The status writer information may have been moved to `阶段状态机与强门禁协议.md` or to `workflow-state.py` itself, but the reference was never updated.

### Verdict: PARTIAL

**What's REAL:**
1. The `trellis-meta` skill reference files (change-task-lifecycle.md) in all 3 carrier directories point to `.trellis/spec/cli/backend/workflow-state-contract.md` which does NOT exist. This is a stale reference.

**What's NOT REAL:**
1. The workflow.md references to `inject-workflowflow-state.py` are correct -- the hooks exist at the documented paths (`.claude/hooks/` and `.codex/hooks/`).
2. There is NO reference to `.trellis/scripts/inject-workflow-state.py` anywhere in the embedded project. The issue description's claim that workflow.md points to this path is not confirmed.

### Source files involved

- `trellis-meta` skill source (in the trellis-library or workflow assets) -- contains the stale `workflow-state-contract.md` reference
- The workflow.md template's full contract section (lines 694-699) -- these references are actually correct, no fix needed

### Proposed fix scope

1. **trellis-meta skill**: Update `change-task-lifecycle.md` to point to the actual location of status writer information (likely `阶段状态机与强门禁协议.md` or inline in the workflow docs)
2. **workflow.md**: No fix needed -- the existing references to hook paths are correct

## Caveats / Not Found

- The `workflow-state-contract.md` may have existed in an earlier version and been removed without updating references
- The actual status writer table content needs to be located (likely in `阶段状态机与强门禁协议.md` section 2-3) before the reference can be corrected
- The `trellis-meta` skill is distributed via the workflow installer, so the fix needs to be in the source assets before re-embedding
