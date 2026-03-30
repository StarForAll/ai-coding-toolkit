# Strengthen Feasibility Gate For New-Project Workflow

## Goal

Make `docs/workflows/新项目开发工作流/` treat feasibility and demand-risk assessment as a hard pre-brainstorm gate for new-project discovery, without changing this repository's live `.claude/`, `.opencode/`, or `.iflow` command deployments.

## Requirements

- Clarify in the workflow guide that new-project discovery must pass through feasibility before brainstorm.
- Define a stable `assessment.md` contract that captures go/no-go and negotiation outcomes.
- Align phase router and command mapping with the same gate and branch behavior.
- Upgrade the helper script so the generated assessment template matches the documented contract.
- Keep all changes inside workflow source assets and task metadata.

## Acceptance Criteria

- [ ] `工作流总纲.md` clearly states feasibility is the default gate before brainstorm for new projects.
- [ ] `命令映射.md` reflects pass / pause / reject branches and the brainstorm precondition.
- [ ] `feasibility.md` documents mandatory assessment output fields and downstream gate behavior.
- [ ] `start-patch-phase-router.md` routes missing-assessment new-project work back to feasibility.
- [ ] `feasibility-check.py` generates a structured assessment template matching the docs.

## Technical Notes

- Source-of-truth stays in `docs/workflows/新项目开发工作流/`.
- Do not modify live command deployment directories in this repo.
