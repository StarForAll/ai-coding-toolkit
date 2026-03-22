# Cross-Layer Thinking Guide

> **Purpose**: Think through repository boundary changes before implementing.

---

## The Problem

**In this repository, many bugs happen at boundary handoffs**, not inside a
single file.

Common boundary bugs here:
- `trellis-library` source assets change but `manifest.yaml`, examples, or validation logic do not
- `trellis-library` asset structures evolve but `.trellis/spec/library-assets/` still describes the old authoring model
- a command changes behavior but the matching docs, skill text, or config shape do not
- an agent or command source changes but deployed tool copies drift
- multiple project layers describe the same workflow differently over time

---

## Use This Guide When

Use this guide when a change crosses two or more of these repository layers:

- source library assets in `trellis-library/`
- project-local maintenance specs in `.trellis/spec/`
- registry or metadata state in `trellis-library/manifest.yaml`
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
Source of truth → derived copy or metadata → command/tooling behavior → verification
```

Examples in this repo:

```text
trellis-library asset -> manifest.yaml -> cli/validation/sync flow
```

```text
trellis-library authoring pattern -> .trellis/spec/library-assets guidance -> contributor behavior
```

```text
source asset -> tool deployment copy -> README / skill instructions -> verification checklist
```

For each arrow, ask:
- What path or identifier is being relied on?
- What file records the state of this handoff?
- What breaks if only one side changes?

### Step 2: Identify the Boundaries

| Boundary | Common Issues In This Repo |
|----------|----------------------------|
| `trellis-library` ↔ `manifest.yaml` | source asset added or moved but registry not updated |
| `trellis-library` ↔ `.trellis/spec/library-assets/` | source library structure or authoring rules change but local guidance still teaches the old workflow |
| source asset ↔ tool deployment copy | content diverges across `.claude/`, `.opencode/`, `.iflow/` |
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

**Bad**: Editing a deployed tool file and forgetting whether the real source of
truth lives in a source asset directory, a repo script, or a spec doc

**Good**: State clearly whether the change belongs in a source asset directory,
tool deployment copy, repo-local spec, or `trellis-library`

### Mistake 2: Metadata Drift

**Bad**: Moving or remapping files without checking `manifest.yaml`, README
examples, or script path assumptions

**Good**: Update path mapping, metadata, and tests together

### Mistake 2.5: Authoring Guide Drift

**Bad**: Changing `trellis-library` asset layout or conventions while leaving
`.trellis/spec/library-assets/` on the old model

**Good**: When source-library authoring rules change, update the local
authoring spec in the same change or explicitly record why it remains different

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
- [ ] Verified copied/deployed paths match the intended layout
- [ ] Verified config/metadata reflects the actual state on disk
- [ ] Verified related docs/instructions were updated if behavior changed
- [ ] Verified the relevant command/test path still passes end to end

---

## When to Write Extra Flow Notes

Write explicit boundary notes when:
- a change touches `trellis-library` and project-local specs or tooling
- a change updates source-library authoring rules that contributors read via `.trellis/spec/library-assets/`
- a path remapping or deployment rule changes
- a command behavior change affects docs, skills, or config
- a bug was caused by drift between source assets and derived state
