# 15 Native CLI Adaptation Evidence Contract

## Purpose

Verify that `workflow-capability-audit` does not judge Claude Code / OpenCode /
Codex native adaptation from memory or repo inspection alone; it must combine
the latest official CLI docs with repo-local validated evidence.

## Input

User input:

> Audit whether the latest Trellis version is still compatible with `docs/workflows/新项目开发工作流/`, and tell me whether Claude Code, OpenCode, and Codex native adaptation still holds.

## Expected Mode

Task-based full compatibility audit with explicit native CLI evidence collection.

## Expected Key Behaviors

- check the latest official documentation for Claude Code, OpenCode, and Codex before finalizing native-adaptation conclusions
- check repo-local evidence such as `CLI原生适配边界矩阵.md`, the relevant platform README, and the live carrier files behind the claim
- keep both evidence tracks visible in `capability-report.md`
- if official docs and repo-local evidence disagree, record the discrepancy explicitly and use a conservative evidence-backed classification
- ensure `## Native CLI Adaptation Evidence` exists in `capability-report.md`
- if `capability-report.md` is missing that section, add it during Step B before finalizing the audit conclusion

## Must Not

- must not rely on memory alone for Claude Code / OpenCode / Codex capability claims
- must not treat repo-local carrier presence as sufficient proof when the official docs define a different runtime boundary
- must not silently flatten official-doc and repo-local contradictions into one unqualified conclusion
