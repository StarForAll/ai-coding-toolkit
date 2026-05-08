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
- `agents/`: currently a placeholder scaffold with README-only guidance; it is not yet the live source of truth for the managed Trellis agent trio
- `commands/`: repo-root scaffold docs; do not confuse this directory with the workflow-local agent source
- workflow-local shared-agents source: lives under `docs/workflows/新项目开发工作流/commands/` for the current workflow product
- `.trellis/.template-hashes.json`: drift-tracking record for Trellis-managed deployment files across platform directories

## Common Commands

```bash
# Validate trellis-library manifest and asset sync
python3 trellis-library/cli.py validate --strict-warnings

# Validate skills structure
./scripts/validate-skills.sh

# Run CLI unit tests
python3 -m unittest trellis-library/tests/test_cli.py

# Get session context and active task inventory
python3 ./.trellis/scripts/get_context.py
python3 ./.trellis/scripts/task.py list
```

## Working Rules

- Read the relevant `.trellis/spec/` guidance before editing. For documentation and instruction changes, start with `.trellis/spec/docs/index.md` and `.trellis/spec/guides/index.md`.
- Treat this repository as the workflow authoring source project, not a target project that consumes installed workflow assets.
- Distinguish source assets, deployed tool copies, task-local runtime artifacts, and target-project outputs. Do not describe one layer as another.
- `AGENTS.md` carries long-lived project rules. Session/task context comes from `.trellis/` plus platform hooks/plugins, not from this file alone.
- For sub-agents, context may be pushed by platform-specific `inject-subagent-context` hooks/plugins or pulled by the agent definition itself, depending on the platform.
- This repository authors workflow assets; consuming target projects receive extra install-time surfaces. One example is the installer-managed `workflow-nl-routing` AGENTS block, which belongs to installed target projects rather than this source authoring repository unless the authoring contract changes.
- If you edit the project root README, update `README.md` and `README.en.md` together.
- Do not execute `git commit`.
- Keep `.trellis/workspace/` journal files under 2000 lines.
- Run the relevant validation commands before claiming completion.

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
- Codex relies on `AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json`, `.agents/skills/`, and `.codex/agents/`; do not assume a project-level `/trellis:...` command directory exists there.
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

## Subagents

- ALWAYS wait for every spawned subagent to reach a terminal status before yielding, acting on partial results, or spawning followups.
  - On Codex, this means calling the `wait` tool with the subagent's thread id (requires `multi_agent_v2`). Do NOT infer completion from elapsed time.
  - On Claude Code / OpenCode, this means awaiting the Task/agent tool result before continuing.
- NEVER cancel or re-spawn a subagent that hasn't finished. If a subagent appears stuck, raise the wait timeout (Codex default 30s, max 1h) before judging it broken.
- Spawn subagents automatically when:
  - Parallelizable work (e.g., install + verify, npm test + typecheck, multiple tasks from plan)
  - Long-running or blocking tasks where a worker can run independently
  - Isolation for risky changes or checks

### Codex-only — `spawn_agent` parameters

When calling `spawn_agent`, ALWAYS pass `fork_turns="none"`. Without it the child inherits the parent transcript and sees your prior `spawn_agent(...)` records, then applies the "wait for spawned subagents" rule to itself — causing `wait_agent` self-deadlock.

```text
spawn_agent(agent_type="trellis-implement", message="...", fork_turns="none")
```

### Codex-only — multi-subagent close-loop

When `wait` returns a `completed` notification, treat it as an event signal — not as "all done". Run this loop:

1. Maintain an `expected_agents` set of dispatched sub-agent thread IDs.
2. After each `wait` update:
   1. Call `list_agents` to inspect ALL live agents' status.
   2. For each agent now in a terminal state:
      - Verify its promised deliverable exists (e.g. `{task_dir}/research/*.md`).
      - Read or summarize as needed.
      - `close_agent` to release the slot.
      - Remove from `expected_agents`.
   3. If `expected_agents` still contains running agents → keep waiting.
   4. If `expected_agents` is empty → continue main flow.
3. Never `wait` on an agent that has already reported `completed`.
4. If a `completed` agent is missing its deliverable, treat it as failed — surface that in your report instead of re-waiting.

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->
