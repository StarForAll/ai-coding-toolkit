# Cross-Layer Thinking Guide

> **Purpose**: Think through repository boundary changes before implementing.

---

## The Problem

**In this repository, many bugs happen at boundary handoffs**, not inside a
single file.

Common boundary bugs here:
- `trellis-library` source assets change but target-project imports or lock data do not
- a command changes behavior but the matching docs, skill text, or config shape do not
- a spec directory moves but assembly, sync, or validation tooling still assumes the old path
- multiple project layers describe the same workflow differently and drift over time

---

## Use This Guide When

Use this guide when a change crosses two or more of these repository layers:

- source library assets in `trellis-library/`
- imported project-local specs in `.trellis/spec/`
- target-project state in `.trellis/library-lock.yaml`
- commands and automation scripts
- agent or skill instructions
- config or metadata files that shape behavior

If a change stays fully inside one file or one isolated directory, this guide is
usually unnecessary.

---

## Before Implementing Boundary-Crossing Changes

### Step 1: Map the Repository Flow

Write the actual handoff path for the change:

```text
Source of truth → copied/imported form → metadata/lock state → command/tooling behavior → verification
```

Examples in this repo:

```text
trellis-library spec -> .trellis/spec import -> .trellis/library-lock.yaml -> sync/propose/apply flow
```

```text
command spec -> command implementation -> README / skill instructions -> verification checklist
```

For each arrow, ask:
- What path or identifier is being relied on?
- What file records the state of this handoff?
- What breaks if only one side changes?

### Step 2: Identify the Boundaries

| Boundary | Common Issues In This Repo |
|----------|----------------------------|
| `trellis-library` ↔ `.trellis/spec` | imported spec drift, wrong target path, stale copied directories |
| asset content ↔ `.trellis/library-lock.yaml` | lock metadata no longer matches actual imports |
| command/script ↔ docs/skills | behavior changes but instructions stay outdated |
| config ↔ agent/command behavior | allowed paths, flags, or conventions drift |
| spec ↔ validation flow | rules say one thing, tooling enforces another |

### Step 3: Define the Contract

For each boundary, make the contract explicit:
- Which file is the source of truth?
- Which paths or IDs must stay aligned?
- Which command proves the boundary still works?
- Which changes require updating more than one layer?

---

## Common Boundary Mistakes

### Mistake 1: Hidden Source of Truth

**Bad**: Editing imported project files and forgetting whether source of truth is
the local copy or `trellis-library`

**Good**: State clearly whether the change belongs in project-local spec,
`trellis-library`, or both

### Mistake 2: Metadata Drift

**Bad**: Moving or remapping files without checking `.trellis/library-lock.yaml`
or script path assumptions

**Good**: Update path mapping, lock metadata, and tests together

### Mistake 3: Instruction / Tooling Mismatch

**Bad**: Changing command behavior while README, AGENTS instructions, or skill
text still describe the old workflow

**Good**: Treat docs and instructions as part of the change surface

---

## Checklist for Boundary-Crossing Changes

Before implementation:
- [ ] Mapped the full repository handoff path
- [ ] Identified source-of-truth files and derived files
- [ ] Identified path, ID, or metadata fields that must stay aligned
- [ ] Chosen the commands or tests that verify the boundary

After implementation:
- [ ] Verified copied/imported paths match the intended layout
- [ ] Verified lock/config/metadata reflects the actual state on disk
- [ ] Verified related docs/instructions were updated if behavior changed
- [ ] Verified the relevant command/test path still passes end to end

---

## When to Write Extra Flow Notes

Write explicit boundary notes when:
- a change touches `trellis-library` and the project-local `.trellis/` tree
- a path remapping or import rule changes
- a command behavior change affects docs, skills, or config
- a bug was caused by drift between source assets and derived state
