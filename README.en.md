# AI Coding Toolkit (ai-coding-toolkit)

> Default version: [简体中文](./README.md) | English

Reusable assets accumulated from AI-assisted programming work: specs, templates, agents, commands, skills, multi-tool configurations, and workflows.

## Repository Structure

### Core Assets

| Directory | Description |
|------|------|
| `trellis-library/` | **Core asset library**: specs, templates, checklists, examples, schemas, and scripts managed through `manifest.yaml` |
| `.trellis/spec/` | **Live project spec workspace**: defines how assets in this repository are authored and maintained, with 11 spec layers (agents, checklists, commands, docs, examples, guides, library-assets, platforms, scripts, skills, templates) |
| `skills/` | Skills discoverable and installable through **Skills CLI** (`npx skills`) (4 skills) |

### Source Asset Layer

> ⚠️ These directories currently contain README skeletons only. Real assets are still maintained directly in the corresponding tool deployment layer.

| Directory | Description |
|------|------|
| `agents/` | Agent source assets (tool-agnostic system prompts, permission boundaries, workflow definitions); currently README-only and waiting to be populated |
| `commands/claude/` | Claude Code command source assets; currently README-only and waiting to be populated |
| `commands/codex/` | Codex CLI command source assets; currently README-only and waiting to be populated |
| `commands/shell/` | Shared shell scripts; currently README-only and waiting to be populated |

### Tool Deployments

| Directory | Description |
|------|------|
| `.claude/` | Claude Code config: agents (6), commands (13), hooks (3), settings |
| `.opencode/` | OpenCode config: agents (6), commands (15), plugin (2), lib, settings |
| `.iflow/` | iFlow config: agents (6), commands (13), hooks (3), settings |
| `.codex/` | Codex CLI config: agents (3, TOML format), hooks (1) |
| `.agents/` | Tool-side skills deployment (13 trellis workflow skills) |
| `.kiro/` | Tool-side skills deployment (12 trellis workflow skills) |

### Other Directories

| Directory | Description |
|------|------|
| `scripts/` | Repository maintenance scripts (`validate-skills.sh`) |
| `docs/` | Notes and design documents, including 3 workflows under `docs/workflows/**` |
| `reference-data/` | Empty directory reserved for future use |
| `tmp/` | Temporary workflow data, ignored by `.gitignore` |
| `.trellis/` | Trellis workspace: workflow, tasks, workspace, scripts, spec, library-lock |
| `.github/` | GitHub Actions CI config (`trellis-library-ci.yml`) |
| `.ace-tool/` | Tool cache, ignored by `.gitignore` |

## Architecture: Source Assets -> Tool Deployments

```text
Source asset layer (source of truth)   Tool deployment layer (derived instances)
────────────────────────────────────   ─────────────────────────────────────────
agents/<id>/SYSTEM.md            ──→   .claude/agents/<role>.md
                                ──→   .opencode/agents/<role>.md
                                ──→   .iflow/agents/<role>.md

commands/<tool>/                 ──→   .<tool>/commands/<ns>/<name>.md
```

> **Current status**: the `agents/` and `commands/` source layers have not been built yet and currently contain README skeletons only.
> Agent and command assets are still maintained directly in tool deployment directories (`.claude/`, `.opencode/`, `.iflow/`, while `commands/` is waiting to be populated).
> See `.trellis/spec/agents/index.md` and `.trellis/spec/commands/index.md` for details.

### Notes on Automated Workflows

**This project does not use fully automated AI development workflows.** Reference examples:

- [ralph-claude-code](https://github.com/frankbria/ralph-claude-code) - overnight automated workflow
- [loki-mode](https://github.com/asklokesh/loki-mode) - fully automated workflow

**Why this project does not adopt that approach:**

1. **Uncertainty introduced by automation**
   - It may stall when permissions are insufficient
   - A large blast radius may cause accidental deletion of unrelated files

2. **Current model limitations**
   - Fully automated workflows continue to accumulate technical debt
   - Human intervention is still required to ensure quality

If these problems can be solved, the complexity of work for junior and mid-level developers could be significantly reduced.

## Skills (for `npx skills add`)

The `skills/` directory in this repository follows the discoverable structure required by Skills CLI and can be installed directly from a git repository.

### Quick Install

```bash
# Install all skills from a git repository
npx skills add <owner>/<repo>

# Or use the full URL
npx skills add https://github.com/<owner>/<repo>
```

### Local Testing

```bash
# List discoverable skills only (without installing)
npx skills add . --list

# Install from a local path
npx skills add . -g -y
```

### Current Skills

| Skill ID | Description |
|----------|------|
| `collaborating-with-claude` | Collaborate through the Claude Code CLI for prototyping, debugging, and code review, with multi-turn session support |
| `demand-risk-assessment` | Requirement risk assessment for outsourcing, projects, or requests, including structured scoring and risk matrices |
| `multi-cli-review` | Multi-CLI review workflow that outputs structured defect reports, supporting both single-reviewer and multi-reviewer protocols |
| `multi-cli-review-action` | Multi-CLI review aggregation that reads multiple reviewer reports, deduplicates findings, detects conflicts, and applies a unified fix plan |

### Skill Directory Conventions

```text
skills/
  <skill-id>/
    SKILL.md       # required, with YAML frontmatter (name, description)
    scripts/       # optional
    references/    # optional
```

### Add a New Skill

1. Create a new directory: `skills/<new-skill-id>/`
2. Add `SKILL.md` with YAML frontmatter containing at least `name` and `description`
3. Optionally add `scripts/` and/or `references/`
4. Run validation:

```bash
./scripts/validate-skills.sh
```

## Trellis Library

The core asset library lives in `trellis-library/` and contains all reusable assets registered through `manifest.yaml`.

### Validation

```bash
python3 trellis-library/cli.py validate --strict-warnings
```

### Documentation

See `trellis-library/README.md`, `trellis-library/taxonomy.md`, and `.trellis/spec/library-assets/`.

## Development Specs

All development specs live under `.trellis/spec/`:

```bash
# View the full spec index
cat .trellis/spec/index.md

# Browse by task type
cat .trellis/spec/library-assets/spec-authoring.md   # author a spec
cat .trellis/spec/scripts/python-conventions.md      # write Python scripts
cat .trellis/spec/agents/index.md                    # define an agent
cat .trellis/spec/commands/index.md                  # define a command
cat .trellis/spec/skills/index.md                    # define a skill
```
