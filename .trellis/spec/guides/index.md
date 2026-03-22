# Thinking Guides

> **Purpose**: Provide project-local thinking prompts for maintaining this asset repository safely.

---

## What This Directory Is For

This directory keeps lightweight checklists for mistakes that are common in this
repository but do not belong in a deeper implementation spec.

The focus here is repo maintenance:

- source-of-truth versus deployed copies
- path, ID, and metadata drift
- keeping `.trellis/spec/library-assets/` aligned with live `trellis-library/` authoring rules
- repeated patterns across agents, commands, skills, and docs
- keeping tooling and instructions aligned

## Why These Guides Matter

**Many bugs and tech debt still come from "didn't think of that"** in places
where this repository has unusual handoffs:

- Didn't think about source-to-deployment sync → tool instances behave differently
- Didn't think about cross-tool consistency → agents or commands diverge across `.claude/`, `.opencode/`, `.iflow/`
- Didn't think about manifest-asset alignment → validation fails or sync drifts
- Didn't think about future maintainers → docs and instructions stop matching the repo

These guides help you **ask the right project-specific questions before making changes**.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through repo boundary changes | Features spanning multiple layers |

## Boundary

Before adding a new guide here, check whether it should instead live as a
deeper repo spec or as a reusable library asset in `trellis-library`.

Keep guides here only when they are:

- clearly project-specific
- lightweight supplements rather than full authoring specs
- not better expressed inside `library-assets/`, `scripts/`, `agents/`, `commands/`, `skills/`, or `docs/`

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Change touches 2+ repository layers (see list below)
- [ ] Asset ID or path rename (affects manifest, tool deployments, docs, or scripts)
- [ ] Agent/command content changed but not synced across all tool directories
- [ ] Validation rule change affects multiple scripts or CI
- [ ] You're not sure which layer owns the source of truth

**Repository layers to consider:**
- `trellis-library/` source assets (specs, templates, checklists)
- `.trellis/spec/library-assets/` authoring guidance for those assets
- `manifest.yaml` registry
- `.trellis/spec/` project-local maintenance specs
- `agents/` source → `.claude/agents/` → `.opencode/agents/` → `.iflow/agents/`
- `commands/` source → `.claude/commands/` → `.opencode/commands/` → `.iflow/commands/`
- `scripts/` validation and sync tooling

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar logic to something that exists in another tool's deployment
- [ ] You see the same pattern repeated across `.claude/`, `.opencode/`, `.iflow/`
- [ ] You're adding a new field to `manifest.yaml` entries
- [ ] **You're modifying any constant, path, or config that appears in multiple layers**
- [ ] **You're creating a new validation or sync script** ← Search existing scripts first!

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

---

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
# Search for the value you're about to change
rg -n "value_to_change" .
```

This single habit prevents most "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before making changes**: Skim the relevant thinking guide
2. **When touching multiple layers**: Run through the cross-layer checklist
3. **When modifying existing values**: Search across all tool directories first
4. **After bugs**: Add new insights to the relevant guide

---

## Contributing

Found a new "didn't think of that" moment? Add it to the relevant guide.

---

**Core Principle**: A short repo-boundary review prevents most drift bugs.
