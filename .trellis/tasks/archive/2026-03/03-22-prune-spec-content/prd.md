# Prune irrelevant .trellis spec content

## Goal
Align `.trellis/spec/` with the actual role of this repository and remove spec content that does not help maintain the project's real assets.

## Requirements
- Identify the repository's actual asset types and maintenance workflows from repo docs, scripts, and workflow files.
- Review `.trellis/spec/` and remove sections or files that do not map to those asset types or workflows.
- Keep spec coverage for repository-relevant areas such as library assets, scripts, agents, commands, skills, docs, and shared thinking guides when still applicable.
- Update affected index files so the remaining structure is navigable and truthful.

## Acceptance Criteria
- [ ] `.trellis/spec/` only contains content justified by the repository's current purpose.
- [ ] Any removed content is reflected in relevant index files or workflow references.
- [ ] Remaining spec indexes describe the repository scope accurately.
- [ ] Verification commands run successfully or any verification gap is stated explicitly.

## Technical Notes
- This is a spec-maintenance task, not an application feature change.
- Deletions must be based on repository evidence, not personal preference.
