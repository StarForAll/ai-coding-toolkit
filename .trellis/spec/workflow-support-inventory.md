# Workflow Support Inventory

> Inventory of templates, checklists, and examples under `.trellis/spec/` that support this repository's workflow assets.

---

## Purpose

This file makes the support layer explicit.

Use it when deciding whether a supporting asset should:

- stay as an active workflow dependency
- remain as adjacent support material
- be reviewed later for possible cleanup

This avoids treating every imported template, checklist, or example as equally
important.

---

## Direct Workflow Dependencies Today

These assets are explicitly referenced by live workflow documents in
`docs/workflows/**`.

| Asset | Path | Current Evidence |
|------|------|------------------|
| Acceptance criteria template | `.trellis/spec/templates/universal-domains/product-and-requirements/acceptance-criteria-template.md` | Referenced by `docs/workflows/自定义工作流制作规范.md` and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |
| Customer-facing PRD template | `.trellis/spec/templates/universal-domains/product-and-requirements/customer-facing-prd-template.md` | Referenced by `docs/workflows/自定义工作流制作规范.md`, `docs/workflows/新项目开发工作流/工作流总纲.md`, and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |
| Developer-facing PRD template | `.trellis/spec/templates/universal-domains/product-and-requirements/developer-facing-prd-template.md` | Referenced by `docs/workflows/自定义工作流制作规范.md`, `docs/workflows/新项目开发工作流/工作流总纲.md`, and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |
| Acceptance quality checklist | `.trellis/spec/checklists/universal-domains/product-and-requirements/acceptance-quality-checklist.md` | Referenced by `docs/workflows/自定义工作流制作规范.md` and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |
| Customer-facing PRD checklist | `.trellis/spec/checklists/universal-domains/product-and-requirements/customer-facing-prd-checklist.md` | Referenced by `docs/workflows/自定义工作流制作规范.md`, `docs/workflows/新项目开发工作流/工作流总纲.md`, and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |
| Developer-facing PRD checklist | `.trellis/spec/checklists/universal-domains/product-and-requirements/developer-facing-prd-checklist.md` | Referenced by `docs/workflows/自定义工作流制作规范.md`, `docs/workflows/新项目开发工作流/工作流总纲.md`, and `docs/workflows/新项目开发工作流/commands/start-patch-phase-router.md` |

---

## Indirect Support Assets

These assets are not currently referenced directly by `docs/workflows/**`, but
they support the direct dependency set above by giving maintainers concrete
artifact examples or linked companion material.

| Asset | Path | Why It Still Fits |
|------|------|-------------------|
| Customer-facing PRD example | `.trellis/spec/examples/universal-domains/product-and-requirements/customer-facing-prd-example.md` | Linked from the customer-facing PRD template and checklist |
| Developer-facing PRD example | `.trellis/spec/examples/universal-domains/product-and-requirements/developer-facing-prd-example.md` | Linked from the developer-facing PRD template and checklist |
| Product-and-requirements examples README | `.trellis/spec/examples/universal-domains/product-and-requirements/README.md` | Documents the example set as a coherent support package |

---

## Present but Not Yet Explicitly Routed by Current Workflows

These assets are reasonable for this repository's domain, but they do not
currently have explicit entry points in `docs/workflows/**`.

Keep them for now, but treat them as review candidates if future cleanup is
needed.

### Templates

- `.trellis/spec/templates/platforms/cli/command-contract-template.md`
- `.trellis/spec/templates/universal-domains/agent-collaboration/agent-handoff-template.md`
- `.trellis/spec/templates/universal-domains/verification/definition-of-done-template.md`

### Checklists

- `.trellis/spec/checklists/platforms/cli/command-interface-readiness-checklist.md`
- `.trellis/spec/checklists/universal-domains/agent-collaboration/delegation-readiness-checklist.md`
- `.trellis/spec/checklists/universal-domains/agent-collaboration/handoff-readiness-checklist.md`
- `.trellis/spec/checklists/universal-domains/context-engineering/context-health-checklist.md`
- `.trellis/spec/checklists/universal-domains/verification/definition-of-done-checklist.md`

---

## Conservative Ranking For Remaining Support Assets

This ranking is for review priority only. It does **not** mean everything in the
lower groups should be deleted automatically.

### Tier A: Keep As Near-Core Support

These assets are not explicitly routed by current workflow docs, but they remain
highly aligned with this repository's role.

#### CLI and command authoring

- `.trellis/spec/templates/platforms/cli/command-contract-template.md`
- `.trellis/spec/checklists/platforms/cli/command-interface-readiness-checklist.md`

Reason:

- this repository actively authors command and workflow command assets
- these assets are directly aligned with the retained CLI command-interface spec concern

#### Agent collaboration support

- `.trellis/spec/templates/universal-domains/agent-collaboration/agent-handoff-template.md`
- `.trellis/spec/checklists/universal-domains/agent-collaboration/delegation-readiness-checklist.md`
- `.trellis/spec/checklists/universal-domains/agent-collaboration/handoff-readiness-checklist.md`

Reason:

- this repository actively designs agent/subagent workflows
- these assets remain natural companions to the retained agent-collaboration spec set

#### Workflow execution discipline

- `.trellis/spec/checklists/universal-domains/context-engineering/context-health-checklist.md`
- `.trellis/spec/templates/universal-domains/verification/definition-of-done-template.md`
- `.trellis/spec/checklists/universal-domains/verification/definition-of-done-checklist.md`

Reason:

- these assets are tightly coupled to long-running AI workflow quality, context hygiene, and honest completion claims
- they remain central to the repository's actual workflow-tooling role

### Tier B: No Current Candidates

After the latest pruning sweep, there are no remaining support assets that are
both:

1. detached from current workflow entry points, and
2. detached from a retained core workflow-method concern

That means the support layer is now in a much cleaner state than before.

---

## Removed In The Latest Support-Layer Pruning Sweep

These support assets were removed because they had no current workflow entry
point and their parent live-spec concerns had already been pruned from this
project:

- `.trellis/spec/templates/universal-domains/project-governance/risk-assessment-template.md`
- `.trellis/spec/checklists/universal-domains/project-governance/risk-review-checklist.md`
- `.trellis/spec/templates/universal-domains/verification/release-readiness-template.md`
- `.trellis/spec/checklists/universal-domains/verification/release-readiness-checklist.md`
- `.trellis/spec/templates/universal-domains/project-governance/change-request-template.md`
- `.trellis/spec/checklists/universal-domains/project-governance/change-review-checklist.md`

---

## Review Rule

Before removing a support asset from `.trellis/spec/`, verify all of the
following:

1. It is not referenced by `docs/workflows/**`
2. It is not referenced by any neighboring template, checklist, or example that remains active
3. It is not part of a workflow package this repository intends to keep expanding

If any of those checks fail, prefer keeping the asset and clarifying its role
instead of deleting it.
