# Platform Integration Specifications

> Project-level rules for platform-specific behavior in this repository.

---

## Overview

This layer captures constraints that are specific to how a particular AI tool
or carrier behaves in this repository.

Use this layer when a rule is:

- specific to one platform runtime or carrier surface
- not a generic workflow rule that should live under `universal-domains/`
- not merely a source-asset formatting rule for `agents/`, `commands/`, or
  `skills/`

Typical examples:

- platform-specific context injection constraints
- platform-specific delegation limits
- project-level operating rules tied to one CLI's execution model

---

## Current Concerns

| Concern | Path | Purpose |
|--------|------|---------|
| CLI command interface | `platforms/cli/command-interface/` | Generic CLI invocation and output contracts |
| Codex workflow behavior | `platforms/codex-workflow-behavior.md` | Project rules for Codex execution behavior in this repository |
| DSH workflow behavior | `platforms/dsh-workflow-behavior.md` | Project rules for DSH execution behavior and the local dsh-trellis carrier |
| ZCode workflow behavior | `platforms/zcode-workflow-behavior.md` | Project rules for ZCode behavior: dual-directory skill discovery, shadowing, and command naming |

---

## Pre-Development Checklist

Before changing platform-specific behavior:

1. [ ] Identify whether the rule is truly platform-specific
2. [ ] Check whether an existing universal-domain rule already covers it
3. [ ] If the rule affects Codex behavior, read `codex-workflow-behavior.md`
4. [ ] If the rule affects DSH behavior or the `dsh-trellis` carrier, read `dsh-workflow-behavior.md`
5. [ ] If the rule affects ZCode behavior, read `zcode-workflow-behavior.md`
6. [ ] If the rule affects command-line interface semantics, read `platforms/cli/command-interface/*`
7. [ ] Update nearby indexes when adding a new platform concern

---

## Boundary

Keep this layer focused on project-local platform behavior.

Do not put the following here:

- generic delegation policy that applies to every platform
- workflow product runtime rules for target projects
- tool-directory source/deploy formatting guidance for `agents/` or `commands/`

When a rule is “Codex in this repository must behave this way,” this is the
right layer.

---

**Language**: English
