# Code Reuse Thinking Guide

> **Purpose**: Stop and think before creating new code or content. Does it already exist?

---

## The Problem

**Duplicated logic is a major source of drift in this repository.**

When you copy-paste or rewrite existing rules:
- bug fixes do not propagate
- tool-specific files diverge over time
- the repo becomes harder to audit and maintain

---

## Before Writing New Code

### Step 1: Search First

```bash
# Search for similar function names
rg -n "functionName" .

# Search for similar logic or wording
rg -n "keyword" .
```

### Step 2: Ask These Questions

| Question | If Yes... |
|----------|-----------|
| Does a similar function or rule exist? | Reuse or extend it |
| Is this pattern used elsewhere? | Follow the existing pattern |
| Could this be a shared utility or source asset? | Put it in the right shared location |
| Am I copying code or prose from another file? | **STOP** and decide whether it should be centralized |

---

## Common Duplication Patterns

### Pattern 1: Copy-Paste Functions

**Bad**: Copying a validation function to another script

**Good**: Extract to shared utilities and import it where needed

### Pattern 2: Parallel Asset Definitions

**Bad**: Rewriting the same instruction, README block, or metadata shape in
multiple agent, command, or skill files

**Good**: Factor out the shared rule, or at least align on one existing pattern
before adding another copy

### Pattern 3: Repeated Constants and Paths

**Bad**: Defining the same path, asset ID fragment, or command string in multiple files

**Good**: Single source of truth, import or reference it everywhere

---

## When to Abstract

**Abstract when**:
- the same logic or wording appears 3+ times
- the rule is important enough that drift would be risky
- multiple tools or workflows must stay aligned

**Don't abstract when**:
- it is only used once
- the abstraction would be harder to understand than the duplication
- the files intentionally differ by tool behavior

---

## After Batch Modifications

When you've made similar changes to multiple files:

1. **Review**: Did you catch all instances?
2. **Search**: Run `rg -n` to find any missed
3. **Consider**: Should this be abstracted?

---

## Gotcha: Asymmetric Mechanisms Producing Same Output

**Problem**: When two different mechanisms must produce the same file set, structural changes (renaming, moving, adding subdirectories) only propagate through the automatic mechanism. The manual one silently drifts.

**Symptom**: One path updates correctly, but another path creates files at wrong locations or misses files entirely.

**Prevention checklist**:
- [ ] When migrating directory structures, search for ALL code paths that reference the old structure
- [ ] If one path is auto-derived and another is manually listed, the manual one needs updating
- [ ] Add or update a regression test that compares both outputs

---

## Checklist Before Commit

- [ ] Searched for existing similar code or wording
- [ ] No copy-pasted logic that should be shared
- [ ] Constants and path fragments are defined in one place when possible
- [ ] Similar patterns follow the same structure across source assets, docs, and tooling
