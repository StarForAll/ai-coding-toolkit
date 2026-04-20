# Reviewer Commands - Round 1

## Task

- Task ID: `04-20-workflow-brainstorm-drift-closure`
- Review root: `tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure`
- Review round: `1`
- Target path: `docs/workflows/新项目开发工作流`

## Task Summary

Current changes focus on documenting and closing workflow drift around post-install verification and cross-CLI hidden-directory ownership:

- Added a single post-install verification checklist
- Updated canonical docs to require `trellis init -> install-workflow.py -> post-install verification -> use`
- Corrected Codex wording so `.agents/skills/` and `.codex/skills/` are both treated as review impact surface, while keeping `.codex/skills/` as a Trellis-init-era extra impact surface rather than claiming it as Codex's sole official path
- Propagated the post-install verification step into walkthrough docs and the HTML mindmap

## Review Goal

Identify remaining defects in the current documentation repair, especially:

- residual data drift across canonical docs, walkthrough docs, and the HTML mindmap
- places where the workflow claims a closed loop but still omits the actual post-install verification step
- wording that still mismatches `install-workflow.py` / `upgrade-compat.py` real behavior
- incorrect or incomplete statements about `.agents/skills/`, `.codex/skills/`, `AGENTS.md`, `workflow-installed.json`, `library-lock.yaml`, and hand-maintained CLI assets

Reviewer output must be a structured defect report only. Reviewers must not modify files and must not create directories.

## Reviewer Commands

Run these in other CLIs from the project root. The two commands are intentionally identical except for `--reviewer-id`.

```text
/multi-cli-review "Review the current documentation repair for docs/workflows/新项目开发工作流. Identify any remaining documentation drift, missing post-install verification closure, mismatches with install-workflow.py or upgrade-compat.py behavior, and incorrect boundary statements about .agents/skills, .codex/skills, AGENTS.md managed blocks, workflow-installed.json, library-lock.yaml, or hand-maintained CLI assets. Output a structured defect report only; do not modify files." "docs/workflows/新项目开发工作流" --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --reviewer-id "claude-reviewer" --round 1 --review-focus "documentation drift, post-install verification closure, Codex skills boundary, installer/upgrade behavior consistency"
```

```text
/multi-cli-review "Review the current documentation repair for docs/workflows/新项目开发工作流. Identify any remaining documentation drift, missing post-install verification closure, mismatches with install-workflow.py or upgrade-compat.py behavior, and incorrect boundary statements about .agents/skills, .codex/skills, AGENTS.md managed blocks, workflow-installed.json, library-lock.yaml, or hand-maintained CLI assets. Output a structured defect report only; do not modify files." "docs/workflows/新项目开发工作流" --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --reviewer-id "opencode-reviewer" --round 1 --review-focus "documentation drift, post-install verification closure, Codex skills boundary, installer/upgrade behavior consistency"
```

## Aggregation Command

After both reviewer reports are present under:

```text
tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure/review-round-1/
```

run this in the current CLI:

```text
/multi-cli-review-action --task-dir "tmp/multi-cli-review/04-20-workflow-brainstorm-drift-closure" --round 1
```
