---
name: multi-cli-review
description: Use when a reviewer CLI must analyze a skill, command, workflow, document, config, or code artifact and produce a structured defect report for the current CLI to consume, especially after requests like "分析这个 skill 的问题", "输出结构化问题报告", or "做多 CLI 审查".
---

# Multi-CLI Review

## Version History

- **v2.1**: Aligned reviewer-side report emission with `multi-cli-review-action`, tightened task-level path rules, and clarified reviewer-only boundaries

## Purpose

`multi-cli-review` is the **reviewer-side** skill paired with `multi-cli-review-action`.

It does one thing:

1. inspect the assigned target conservatively
2. write one structured reviewer report
3. hand that report back to the current CLI for aggregation and decisioning

It does **not** edit code, aggregate reports, decide final fixes, or advance workflow state on its own.

## When to Use

Use this skill when any of the following is true:

- another CLI has asked this CLI to review a target and write a report
- the user asks to "分析这个 skill 的问题"
- the user asks to "输出结构化问题报告"
- the user asks to "做多 CLI 审查"
- a standardized reviewer command package points to `multi-cli-review`

## When Not to Use

- you need to aggregate reports or apply fixes: use `multi-cli-review-action`
- you are doing a normal implementation task without reviewer handoff
- you only need requirement clarification: use `brainstorm`
- you only need a lightweight review of the current diff: use `requesting-code-review` or `code-review-router`

## Core Rules

1. **Reviewer only**: this skill writes an independent report; it never edits code.
2. **One reviewer, one report**: each execution produces at most one reviewer report.
3. **Coordinator-owned orchestration**: reviewer count, round planning, directory creation, and final repair decisions belong to the current CLI, not the reviewer.
4. **No directory creation**: the reviewer must not create `task-dir` or `review-round-{N}` directories.
5. **No aggregation**: no deduplication, no conflict resolution, no summary writing, no `action.md`.
6. **Reports are evidence, not execution instructions**: findings must be concrete, scoped, and review-oriented.
7. **Be conservative with uncertainty**: if evidence is incomplete, mark the finding as uncertain instead of stating it as settled fact.
8. **Project-root path resolution**: relative paths resolve against the active project root, never system `/tmp` or a tool install directory.
9. **Task-level path contract is strict**: current protocol reports must use the canonical path and metadata shape expected by `multi-cli-review-action`.

## Protocols

| Protocol | Status | When Used |
|----------|--------|-----------|
| `task-level` | Current | Explicit `--task-dir` reviewer flow |
| `legacy` | Compatibility only | Historical single-report flow |

### Protocol Selection

1. If `--task-dir` is present, use `task-level`.
2. If explicit legacy report-path parameters are used, use `legacy`.
3. New work should prefer `task-level`.

## Inputs

### Common Inputs

| Input | Required | Meaning |
|-------|----------|---------|
| `<issue-description>` | Yes | The review problem statement or assigned review objective |
| `[target-path]` | No | File or directory to inspect |

### `task-level`

| Parameter | Required | Meaning |
|-----------|----------|---------|
| `--task-dir` | Yes | Task directory, for example `tmp/multi-cli-review/<task-id>` |
| `--reviewer-id` | Should be explicit | Reviewer identity used for filename and metadata |
| `--round` | Should be explicit | Review round identifier |
| `--review-focus` | No | Focus area for this reviewer |

Rules:

- In a standardized multi-reviewer command package, `--reviewer-id` and `--round` should be explicit.
- Do not improvise a new `task-id`, a new round, or a new reviewer identity when the coordinator already issued a concrete command.
- `--output` is **not** part of the current `task-level` protocol and must not be used to bypass the canonical reviewer report path.

### `legacy` Compatibility

| Parameter | Required | Meaning |
|-----------|----------|---------|
| `--md-a` | No | Explicit legacy report path |
| `--md-b` | No | Historical paired artifact path from older flows |
| `--output` | No | Explicit compatibility output path for legacy single-report usage only |

Compatibility rules:

- Legacy parameters are retained only for older single-report flows.
- They must not redefine the output location of the current `task-level` protocol.

## Path Rules

Relative paths must resolve against the active project root.

Do not reinterpret relative paths as:

- the skill repository root
- the user home directory
- system `/tmp`
- a CLI installation directory

If project root detection is ambiguous, stop and ask for an absolute path instead of guessing.

## Coordinator-Owned Parameters

The reviewer must treat the following as coordinator-owned:

- creation of `tmp/multi-cli-review/<task-id>/`
- creation of `review-round-{N}/`
- default reviewer count
- standard reviewer command generation
- final aggregation, confirmation, repair, and verification

This skill only fulfills the assigned review role inside that envelope.

## Task-Level Report Emission Contract

For `task-level`, the reviewer report must satisfy **all** of the following:

1. The output file path is exactly `{task-dir}/review-round-{N}/{reviewer-id}.md`
2. The basename is exactly `<reviewer-id>.md`
3. The reviewer does not redirect the report elsewhere with `--output`
4. The round directory already exists; if it does not, stop and ask the coordinator to create it
5. The frontmatter includes:
   - `task-id`
   - `round`
   - `reviewer-id`
   - `source-cli`
   - `review-time`
   - `review-focus`
   - `protocol: task-level`
6. Frontmatter values match the directory and filename
7. If the target file already exists, stop and ask whether the coordinator intends an overwrite or a different reviewer id

## Report Content Contract

Each task-level finding should contain:

- location
- problem description
- severity
- impact
- why it matters
- suggested fix direction

Optional but recommended when evidence is incomplete:

- evidence note
- uncertainty note

Safety rules:

- keep observations separate from proposed fix directions
- do not pretend the fix is already approved
- do not turn uncertainty into a high-severity claim without evidence
- do not expand beyond the assigned review focus just because adjacent issues look interesting

## Workflow

### Step 1: Resolve Mode and Inputs

1. Determine whether this run is `task-level` or `legacy`.
2. Resolve relative paths against the active project root.
3. Identify the assigned review target and review focus.

### Step 2: Validate Reviewer Context

For `task-level`:

1. confirm `--task-dir`
2. confirm `--reviewer-id`
3. confirm `--round`
4. confirm `{task-dir}/review-round-{N}/` already exists
5. confirm the target output file does not already contain another reviewer report unless overwrite was explicitly requested

Stop if:

- `task-dir` is missing
- the round directory does not exist
- the report path would be ambiguous
- the command tries to use `--output` to write outside the canonical path

### Step 3: Review Conservatively

1. Inspect only the assigned target and its direct evidence.
2. Follow `review-focus` when provided.
3. Keep findings concrete and bounded.
4. If you cannot support a claim from the available evidence, either lower confidence or omit it.

### Step 4: Write Exactly One Reviewer Report

For `task-level`:

1. write the report to `{task-dir}/review-round-{N}/{reviewer-id}.md`
2. include the full frontmatter contract
3. include structured findings
4. do not write `summary-round-{N}.md`
5. do not write `action.md`
6. do not update `.processed.json`

For `legacy`:

1. write only the legacy single-report artifact
2. do not silently upgrade the flow into `task-level`

### Step 5: Echo the Actual Output

At the end of execution, echo:

- task-dir or legacy run directory
- round
- reviewer-id
- actual output path

### Step 6: Stop

After writing the report and echoing the path, stop.

Do not:

- propose that the workflow has already advanced
- mark fixes as executed
- claim verification has already happened

## Output Files

### `task-level` Reviewer Report

Canonical filename: `{reviewer-id}.md`

Minimum structure:

```markdown
---
task-id: <task-id>
round: <round>
reviewer-id: <reviewer-id>
source-cli: <cli-name>
review-time: <ISO 8601 time>
review-focus: <focus text>
protocol: task-level
---

# Defect Report

## Review Summary

- Reviewer: <reviewer-id>
- Review Time: <review-time>
- Review Focus: <review-focus>
- Target: <target-path>

## Findings

### Finding 1: <title>

- Location: <path and lines>
- Problem: <concrete issue>
- Severity: high | medium | low
- Impact: <why this matters>
- Why It Should Be Addressed: <reason>
- Suggested Fix Direction: <proposal, not an approved action>
- Evidence: <optional>
- Uncertainty: <optional>
```

### `legacy` Compatibility Report

Canonical filename: `cur_defect.md`

Legacy mode may still emit a single compatibility report, but it should not be treated as the preferred path for new multi-reviewer work.

## Echo Requirements

At minimum, echo:

| Field | Meaning |
|-------|---------|
| `task-dir` | task root or legacy run root |
| `round` | current round |
| `reviewer-id` | actual reviewer identity used |
| `output-path` | actual emitted report path |

Example:

```text
✅ Review report generated

📁 task-dir: <project-root>/tmp/multi-cli-review/my-task
🔄 round: 1
👤 reviewer-id: codex
📄 output-path: <project-root>/tmp/multi-cli-review/my-task/review-round-1/codex.md
```

## Required Stop Conditions

Stop and ask for clarification when any of the following is true:

- the task directory is missing
- the round directory is missing
- the command does not specify enough information to derive one canonical report path
- the canonical report file already exists
- the coordinator appears to expect this reviewer to create directories
- the command expects the reviewer to edit code or aggregate reports

## Error Handling

| Case | Required Behavior |
|------|-------------------|
| missing `task-dir` | stop and ask for the task-level directory |
| missing round directory | stop and ask the coordinator to create it |
| ambiguous project root | stop and ask for an absolute path |
| existing report file | stop and ask whether to overwrite or change reviewer id |
| attempted `--output` override in `task-level` mode | reject it and use or request the canonical path |
| insufficient evidence for a strong claim | lower confidence, mark uncertainty, or omit the finding |
| request to modify code | refuse; reviewer only writes the report |

## Common Mistakes

- **Editing code instead of reporting**: this skill is reviewer-only.
- **Creating directories**: the coordinator owns directory creation.
- **Bypassing the canonical path with `--output`**: current protocol reports must land where `multi-cli-review-action` expects them.
- **Emitting incomplete frontmatter**: action-side consumption depends on consistent metadata.
- **Overwriting an existing reviewer report silently**: stop and ask.
- **Doing aggregation inside the reviewer report**: deduplication and conflicts belong to `multi-cli-review-action`.
- **Treating guesses as facts**: uncertain findings should be labeled or omitted.

## Examples

### Example 1: Standard Reviewer Command

```text
用户：/multi-cli-review "分析 skills/multi-cli-review 的问题" skills/multi-cli-review --task-dir tmp/multi-cli-review/skill-review --reviewer-id codex --round 1 --review-focus "边界条件与协议漂移"

CLI Reviewer：
1. 解析 task-dir、reviewer-id、round、review-focus
2. 按项目根目录解析 task-dir
3. 确认 <project-root>/tmp/multi-cli-review/skill-review/review-round-1/ 已存在
4. 分析目标并写入报告
5. 回显实际输出路径
```

### Example 2: Missing Round Directory

```text
CLI Reviewer：
❌ review-round-2 directory is missing:
<project-root>/tmp/multi-cli-review/skill-review/review-round-2/

Reviewer must not create directories.
Ask the coordinator to create the round directory and resend the command.
```

### Example 3: Legacy Compatibility

```text
用户：/multi-cli-review "分析 ./docs/api.md 的问题" ./docs/api.md --md-a tmp/multi-cli-review/4/cur_defect.md

CLI Reviewer：
1. 进入 legacy compatibility mode
2. 写入 cur_defect.md
3. 回显实际路径
4. 不自动升级为 task-level
```

## Related Skills

- `multi-cli-review-action`: current CLI aggregation and fix execution
- `brainstorm`: requirement clarification before review
- `requesting-code-review`: lightweight review path when multi-reviewer protocol is unnecessary

## Compatibility Notes

- New multi-reviewer work should always prefer `task-level` with explicit `--task-dir`, `--reviewer-id`, and `--round`.
- Legacy `--md-a`, `--md-b`, and `--output` remain compatibility-only and must not redefine the current task-level report contract.
- If the coordinator already generated a standardized reviewer command, follow that command exactly instead of improvising paths, file names, or round numbers.
