# Workflow Spec Fit Assessment

> Strict review of which reusable spec concerns in `.trellis/spec/` are strongly aligned, weakly aligned, or currently poor-fit for this repository's actual role.

---

## Review Standard

This assessment uses three tests:

1. **Project-role fit**: does the concern directly support this repository's real work?
2. **Live-entry fit**: is it referenced by live workflow docs, commands, tasks, or clearly needed by those assets?
3. **Redundancy fit**: is it still needed here, or does a more specific concern already cover the same job?

This repository's current role includes:

- maintaining `trellis-library/`
- maintaining source assets such as `agents/`, `commands/`, `skills/`
- authoring workflow assets in `docs/workflows/**`

---

## Strong-Fit Spec Concerns

These are directly aligned with the repository's current role even when some of
them are not yet cited line-by-line in workflow docs.

### AI workflow core

- `.trellis/spec/universal-domains/ai-execution/`
- `.trellis/spec/universal-domains/context-engineering/`
- `.trellis/spec/universal-domains/agent-collaboration/`
- `.trellis/spec/universal-domains/verification/verification-gates`
- `.trellis/spec/universal-domains/verification/evidence-requirements`
- `.trellis/spec/universal-domains/verification/definition-of-done`

Reason:

- they map directly to AI-assisted workflow design, context injection, delegation, proof requirements, and verification discipline
- those concerns are central to this repository's workflow assets, even if some are currently enforced by prose rather than explicit spec citations

### Workflow-governance and repo-governance

- `.trellis/spec/universal-domains/project-governance/change-management`
- `.trellis/spec/universal-domains/project-governance/library-sync-governance`

Reason:

- this repository actively maintains downstream sync, lock-file behavior, and change-safe workflow guidance

### Requirement-discovery and PRD flow

- `.trellis/spec/universal-domains/product-and-requirements/problem-definition`
- `.trellis/spec/universal-domains/product-and-requirements/scope-boundary`
- `.trellis/spec/universal-domains/product-and-requirements/requirement-clarification`
- `.trellis/spec/universal-domains/product-and-requirements/acceptance-criteria`
- `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-customer-facing`
- `.trellis/spec/universal-domains/product-and-requirements/prd-documentation-developer-facing`

Reason:

- these are explicitly referenced by live workflow docs in `docs/workflows/**`
- they form the currently active PRD baseline for workflow installation and routing gates

### Platform-oriented workflow support

- `.trellis/spec/platforms/cli/command-interface/`

Reason:

- this repository authors workflow command assets and CLI-facing command contracts

---

## Removed In The Latest Pruning Sweep

The following previously weak-fit concerns were removed from the live project
spec workspace:

- `.trellis/spec/universal-domains/project-governance/risk-tiering`
- `.trellis/spec/universal-domains/project-governance/decision-record-policy`
- `.trellis/spec/universal-domains/verification/release-readiness`
- `.trellis/spec/universal-domains/agent-collaboration/parallel-work-rules`

Why they were removed:

- they had weak live-entry evidence in current workflow docs
- they were not part of the repository's current minimum active workflow baseline
- the project chose to optimize `.trellis/spec/` for active use over possible future expansion

Post-removal note:

- some retained support assets still discuss adjacent review/release topics, but
  the corresponding spec concerns are no longer treated as active live-spec
  requirements in this project

---

## Removed Redundancy Candidate

The generic PRD wrapper concern has now also been removed from the live project
spec workspace:

- `.trellis/spec/universal-domains/product-and-requirements/prd-documentation`

Why it was removed:

- live workflow docs already use the customer-facing and developer-facing PRD
  concerns directly
- the generic wrapper was acting as an extra indirection layer without a live
  workflow enforcement point in this repository
- customer-facing and developer-facing concerns can remain understandable after
  direct dependency tightening in `library-lock.yaml`

---

## Re-Scan Result

After removing the weak-fit concerns and the generic PRD wrapper concern, there
is no remaining workflow-method concern that currently stands out as an obvious
poor-fit candidate.

Future pruning should now focus on support-layer assets rather than the core
retained workflow-method spec concerns.

## Not Enough Evidence To Call Unrelated

The following should **not** currently be labeled unrelated just because they
lack direct citations in workflow docs:

- `ai-execution/*`
- `context-engineering/*`
- `agent-collaboration/*`
- `verification/evidence-requirements`
- `verification/definition-of-done`

Reason:

- their subject matter is tightly coupled to this repository's actual purpose
- the gap is explicit citation density, not semantic irrelevance

---

## Review Rule

Before marking any spec concern as unrelated to this repository, require all of
the following:

1. No direct workflow entry point
2. No strong semantic tie to AI workflow authoring, toolkit maintenance, or library sync
3. No active dependency from supporting templates, checklists, or examples
4. A more specific retained concern already covers the same practical job

If any condition fails, classify it as strong-fit or weak-fit instead of
unrelated.
