# AGENTS.md

This file provides project-level instructions for AI assistants working in this repository.

## Repository Scope

This repository is a **meta-project** for authoring, validating, and distributing AI-assisted development workflow assets. It is not a runnable application.

Primary asset types:

- **Markdown** specs, templates, checklists, examples, and workflow docs
- **YAML/TOML** configuration and metadata
- **Python** and **Shell** automation
- **Skill**, **agent**, and **command** assets for multiple AI tools

## Current Repository Shape

- `trellis-library/`: reusable source library plus validation, assembly, and sync tooling
- `.trellis/`: project-local Trellis workflow runtime and maintenance layer: `workflow.md`, `spec/`, `tasks/`, `workspace/`, `scripts/`, runtime state, library sync metadata, and managed-file hash tracking
- `skills/`: skill source assets maintained in this repo
- `.agents/`: shared deployment layer scanned by compatible skill loaders; in this repository it is currently populated by shared Trellis skills under `.agents/skills/`
- `.claude/`, `.opencode/`, `.codex/`, `.kiro/`, `.qoder/`: current platform integration and deployment layer
- `agents/`: source agent asset layer with real repo-authored agent directories plus authoring templates; it is not the live source of truth for the managed Trellis native agent trio
- `commands/`: repo-root command/source-helper layer; currently still mostly scaffold docs, but it already includes shared shell helper assets and should not be confused with the workflow-local command product source
- current workflow product source tree: lives under `docs/workflows/新项目开发工作流/`; its command, installer, and CLI-adapter source assets live under `docs/workflows/新项目开发工作流/commands/`
- `.trellis/.template-hashes.json`: drift-tracking record for Trellis-managed deployment files across platform directories

## Common Commands

```bash
# Validate trellis-library manifest and asset sync
/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings

# Validate skills structure
./scripts/validate-skills.sh

# Run CLI unit tests
/ops/softwares/python/bin/python3 -m unittest trellis-library/tests/test_cli.py

# Get session context and active task inventory
/ops/softwares/python/bin/python3 ./.trellis/scripts/get_context.py
/ops/softwares/python/bin/python3 ./.trellis/scripts/task.py list
```

## Working Rules

- Read the relevant `.trellis/spec/` guidance before editing. For documentation and instruction changes, start with `.trellis/spec/docs/index.md` and `.trellis/spec/guides/index.md`.
- Treat this repository as the workflow authoring source project, not a target project that consumes installed workflow assets.
- Distinguish source assets, deployed tool copies, task-local runtime artifacts, and target-project outputs. Do not describe one layer as another.
- `AGENTS.md` carries long-lived project rules. Session/task context comes from `.trellis/` plus platform hooks/plugins, not from this file alone.
- For sub-agents, context may be pushed by platform-specific `inject-subagent-context` hooks/plugins or pulled by the agent definition itself, depending on the platform. When dispatching Trellis sub-agents from the main session, follow `.trellis/workflow.md`'s required `Active task: <task path>` prompt prelude so hookless or self-loading platforms resolve the correct task context.
- This repository authors workflow assets; consuming target projects receive extra install-time surfaces. One example is the installer-managed `workflow-nl-routing` AGENTS block, which belongs to installed target projects rather than this source authoring repository unless the authoring contract changes.
- If you edit the project root README, update `README.md` and `README.en.md` together.
- Keep `.trellis/workspace/` journal files under 2000 lines.
- Run the relevant validation commands before claiming completion.
- When this repository's Trellis workflow or platform-integration behavior changes, use the same change/review to manually re-check the guidance outside this file's `TRELLIS:START` / `TRELLIS:END` block against `.trellis/workflow.md`, `.codex/config.toml`, and the relevant `trellis-*` skills so local summary text does not drift from the managed workflow.

## Language Policy

- `trellis-library/` assets: **English** (enforced by manifest `default_language`)
- Project documentation: Chinese or English per context

## Platform Notes

- In this repository, project-local Trellis skills, agents, and command-like entrypoints are typically referenced with the `trellis-...` form, for example `trellis-check`, `trellis-before-dev`, and `trellis-continue`.
- Some workflow product docs may describe target-project CLI entrypoints such as `/trellis:...` or `trellis/...`; treat those as installed target-project surfaces, not the default invocation form for this repository.
- Trellis 0.5+ provides native `trellis-research`, `trellis-implement`, and `trellis-check` agents directly. The workflow no longer deploys or manages its own agent overlay; it only migrates legacy bare-name files (e.g. `research.md`) to the Trellis-native `trellis-*` naming convention during install/upgrade.
- Platform agent formats differ: Claude/OpenCode/Qoder use Markdown wrappers, Codex uses TOML, and Kiro uses JSON plus hook declarations.
- For workflow maintenance, compare rendered agent copies against the shared source plus renderer contract, not only by cross-platform string equality; small platform-localized wording or path examples may differ.
- Claude, OpenCode, and Kiro can push sub-agent context via `inject-subagent-context` hooks/plugins. Codex self-loads task context in agent files. In the current Qoder deployment, `trellis-implement` and `trellis-check` self-load `prd.md`, `info.md`, and JSONL context, while `trellis-research` resolves the active task/output path itself and there is no dedicated Qoder subagent-context hook in `.qoder/settings.json`.
- Codex relies on `AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json`, `.agents/skills/`, and `.codex/agents/`; do not assume a project-level `/trellis:...` command directory exists there. The `.codex/` project layer only becomes effective when the repo is trusted, the user-level hooks feature is enabled, and installed hooks pass Codex's one-time `/hooks` approval.
- When `.trellis/config.yaml` keeps `codex.dispatch_mode: inline` (the current default in this repository), the main Codex session must not use agents at all. This is an absolute rule: do not call generic platform agents such as `spawn_agent`, `explorer`, or `worker`, and do not manually invoke `.codex/agents/trellis-*`. Stay inline in the main session unless the project explicitly switches Codex to `sub-agent`.
- Use Trellis native `finish-work` as the normal close-out path in this repository after the workflow's required code-commit step. `add_session.py` is the underlying session-recording step used by that flow and a manual fallback when explicitly needed; do not introduce repo-local helper-based close-out flows unless the platform contract is explicitly changed.
- Kiro uses `.kiro/` hooks, agents, and skills to connect into the same `.trellis` state.
- Qoder uses `.qoder/` hooks, skills, and agents to connect into the same `.trellis` state.

<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
