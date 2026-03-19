# Thinking Guides

> **Purpose**: Provide project-local supplemental thinking prompts that sit beside imported governance specs.

---

## What This Directory Is For

Imported governance specs under `.trellis/spec/universal-domains/` now cover the
primary rules for:

- requirement clarification
- scope control
- change management
- risk tiering
- evidence and verification gates

This directory should only keep **project-specific supplemental guides** that
add value beyond those shared governance concerns.

## Why Supplemental Guides Still Matter?

**Many bugs and tech debt still come from "didn't think of that"** in places
where project-local habits matter:

- Didn't think about source-to-deployment sync → tools behave differently
- Didn't think about cross-tool consistency → agents diverge across .claude/ .opencode/ .iflow/
- Didn't think about manifest-asset alignment → validation failures
- Didn't think about future maintainers → undocumented conventions

These guides help you **ask the right project-specific questions before making changes**.

---

## Available Guides

| Guide | Purpose | When to Use |
|-------|---------|-------------|
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | Identify patterns and reduce duplication | When you notice repeated patterns |
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Think through data flow across layers | Features spanning multiple layers |

## Boundary

Before adding a new guide here, check whether it should instead live as a
reusable concern in `trellis-library`.

Keep guides here only when they are:

- clearly project-specific
- lightweight supplements rather than primary governance rules
- not better expressed as shared reusable specs

---

## Quick Reference: Thinking Triggers

### When to Think About Cross-Layer Issues

- [ ] Change touches 2+ repository layers (see list below)
- [ ] Asset ID or path rename (affects manifest + library-lock + tool deployments)
- [ ] Agent/command content changed but not synced across all tool directories
- [ ] Validation rule change affects multiple scripts or CI
- [ ] You're not sure which layer owns the source of truth

**Repository layers to consider:**
- `trellis-library/` source assets (specs, templates, checklists)
- `manifest.yaml` registry
- `.trellis/spec/universal-domains/` imported governance
- `agents/` source → `.claude/agents/` → `.opencode/agents/` → `.iflow/agents/`
- `commands/` source → `.claude/commands/` → `.opencode/commands/` → `.iflow/commands/`
- `scripts/` validation and sync tooling

→ Read [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md)

### When to Think About Code Reuse

- [ ] You're writing similar logic to something that exists in another tool's deployment
- [ ] You see the same pattern repeated across .claude/ .opencode/ .iflow/
- [ ] You're adding a new field to manifest.yaml entries
- [ ] **You're modifying any constant, path, or config that appears in multiple layers**
- [ ] **You're creating a new validation or sync script** ← Search existing scripts first!

→ Read [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md)

---

## Pre-Modification Rule (CRITICAL)

> **Before changing ANY value, ALWAYS search first!**

```bash
# Search for the value you're about to change
grep -r "value_to_change" .
```

This single habit prevents most "forgot to update X" bugs.

---

## How to Use This Directory

1. **Before making changes**: Skim the relevant thinking guide
2. **When touching multiple layers**: Run through cross-layer checklist
3. **When modifying existing values**: Search across all tool directories first
4. **After bugs**: Add new insights to the relevant guide (learn from mistakes)

---

## Contributing

Found a new "didn't think of that" moment? Add it to the relevant guide.

---

**Core Principle**: 30 minutes of thinking saves 3 hours of debugging.
