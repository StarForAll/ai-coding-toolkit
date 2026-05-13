# workflow-capability-audit: 新项目开发工作流

## Goal

Audit whether a newer Trellis version changed baseline capabilities or mechanics in ways that require compatibility adaptation for `docs/workflows/新项目开发工作流/`.

## What I already know

* Current Trellis version is `0.5.14`.
* Current compatibility anchor is `0.5.12`.
* This audit is limited to `docs/workflows/新项目开发工作流/`.
* Current Codex hook carrier in both the authoring repo and fresh A/B is `.codex/hooks.json` -> `UserPromptSubmit` -> `.codex/hooks/inject-workflow-state.py`.
* `.codex/hooks/session-start.py` still exists in the repo as a legacy / auxiliary hook file, but it is not the current primary hook referenced by `hooks.json`.
* `commands/codex/README.md` still has two wording drifts:
  * overview line says `.codex/hooks.json + .codex/hooks/*.py` inject context "at session start"
  * smoke-test prompt says `If you received a <ready> block from session-start hook`, even though the current workflow carrier is `inject-workflow-state.py`
* `commands/codex/README.md` line 198-202 is not itself a defect: it describes the fact that `session-start.py` still exists in the repo, not that it is the current primary hook contract.

## Requirements

* Create fresh `A` and `B` fixtures after the version gate passes.
* Discover current Trellis baseline capabilities dynamically.
* Compare workflow-managed and workflow-dependent Trellis-native surfaces.
* Produce `capability-report.md` and stop for user confirmation.
* When fixing Codex hook wording, distinguish "repo still contains session-start.py" from "current hooks.json primary carrier uses inject-workflow-state.py".
* Prefer minimal wording corrections over deleting or redefining legacy hook files without evidence.
