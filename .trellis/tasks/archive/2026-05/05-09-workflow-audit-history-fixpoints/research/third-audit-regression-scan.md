# Research: Workflow Third Audit - Regression Scan

- **Query**: Third regression scan of 25 fixpoints after fresh install at /tmp/trellis-0.5.9-2
- **Scope**: internal
- **Date**: 2026-05-09

## Findings

### upgrade-compat Self-Check Result

`upgrade-compat.py --check` against /tmp/trellis-0.5.9-2: **0 conflicts**. All checks passed:

- workflow-installed.json schema complete
- Claude continue.md: Phase Router OK
- Claude all distributed commands content consistent
- Claude finish-work.md: projectization patch OK
- OpenCode continue.md: Phase Router OK
- OpenCode all distributed commands content consistent
- OpenCode finish-work.md: projectization patch OK
- Codex .agents/skills distributed skills content consistent
- Codex trellis-finish-work skill: projectization patch OK
- Codex trellis-continue skill: Phase Router patch OK
- Codex hooks.json exists
- Codex session-start.py exists
- All shared helper scripts content consistent
- No obsolete shared script residue
- All execution cards content consistent
- .trellis/workflow.md: projectization patch OK
- AGENTS.md: NL routing table OK

### Files Found

| File Path | Description |
|---|---|
| `/tmp/trellis-0.5.9-2/.trellis/workflow-installed.json` | Install manifest - trellis_version=0.5.9, workflow_version=0.1.26, schema=2 |
| `/tmp/trellis-0.5.9-2/.trellis/workflow.md` | Workflow doc with projectization patch and 4 [workflow-state:STATUS] blocks |
| `/tmp/trellis-0.5.9-2/.claude/commands/trellis/` | 11 command files (brainstorm, check, continue, delivery, design, feasibility, finish-work, plan, project-audit, review-gate, test-first) |
| `/tmp/trellis-0.5.9-2/.claude/agents/` | 3 agents (trellis-check, trellis-implement, trellis-research) |
| `/tmp/trellis-0.5.9-2/.claude/skills/` | 5 skills (trellis-before-dev, trellis-brainstorm, trellis-break-loop, trellis-check, trellis-meta, trellis-update-spec) |
| `/tmp/trellis-0.5.9-2/.claude/hooks/` | 3 hooks (inject-subagent-context, inject-workflow-state, session-start) |
| `/tmp/trellis-0.5.9-2/.opencode/` | Full OpenCode adaptation layer (commands, agents, skills, plugins, lib) |
| `/tmp/trellis-0.5.9-2/.codex/` | Codex adaptation layer (agents, hooks, hooks.json) |
| `/tmp/trellis-0.5.9-2/.agents/skills/` | 19 shared Codex skills including trellis-continue, trellis-finish-work, trellis-start |
| `/tmp/trellis-0.5.9-2/.qoder/` | Qoder adaptation layer (agents, commands, hooks, settings, skills) |
| `/tmp/trellis-0.5.9-2/.trellis/scripts/workflow/` | 7 helper scripts (feasibility-check, design-export, workflow-state, plan-validate, check-quality, delivery-control-validate, ownership-proof-validate) |
| `/tmp/trellis-0.5.9-2/.trellis/workflow-docs/` | 2 execution cards |
| `/tmp/trellis-0.5.9-2/.trellis/spec/` | 60 spec files across 21 directories |

### Regression Detection Results

#### ISSUE-1: Qoder research agent severely downgraded (severe)

**Source repo** (.qoder/agents/trellis-research.md) has:
- Tools: ace.search_context, exa (web_search, web_fetch, get_code_context, web_search_advanced), Context7 (resolve-library-id, query-docs), deepwiki (read_wiki_structure, read_wiki_contents, ask_question), grok-search (web_search, web_fetch), Skill, chrome-devtools
- Full search routing table (6 search types with primary/fallback columns)
- Multi-step task resolution: (1) dispatch prompt "Active task:" line, (2) task.py current --source, (3) ask user

**Installed version** (.qoder/agents/trellis-research.md) has:
- Tools: only exa (web_search, get_code_context), Skill, chrome-devtools -- missing ace, Context7, deepwiki, grok-search, web_fetch, web_search_advanced
- No search routing table -- just "Run independent searches in parallel (Glob + Grep + web) for efficiency"
- Single-step task resolution: just "Run task.py current --source"

**Root cause**: workflow_assets.py CLI_DIRS only defines {claude, opencode, codex}. The `_deploy_enhanced_research_agent` function only deploys to these three platforms. Qoder is NOT covered by the workflow installer's managed enhanced agent deployment. Qoder agents come from the Trellis baseline, which has not been updated with the enhanced research agent.

**Impact**: Fixpoint #21 (search routing table sync) is satisfied for Claude/OpenCode/Codex but NOT for Qoder. Qoder users get a basic research agent lacking ace.search_context, Context7, deepwiki, grok-search, and the routing table.

#### ISSUE-2: Codex implement/check agents missing carrier comment block (low)

**Source repo** (.codex/agents/trellis-implement.toml, trellis-check.toml) starts with:
```
# This agent definition is a carrier for explicit delegated/non-inline Codex
# paths. When `.trellis/config.yaml` keeps `codex.dispatch_mode = "inline"`,
# the main Codex session must not manually spawn this agent ad hoc.
```

**Installed version** does not have these 4 comment lines.

**Root cause**: These agents come from the Trellis baseline (deployed by `trellis init`), not from the workflow installer. The source repo has been manually updated but the Trellis baseline has not been synced.

**Impact**: Low -- purely informational comments. No functional impact.

#### ISSUE-3: Claude settings.json missing statusLine config (low)

**Source repo** (.claude/settings.json) has at the end:
```json
"statusLine": {
  "type": "command",
  "command": "python3 .claude/hooks/statusline.py"
}
```

**Installed version** ends with:
```json
"enabledPlugins": {}
```

**Root cause**: statusline.py hook does not exist in the installed project. The source repo's statusline is an authoring-repo-only enhancement not distributed by the workflow.

**Impact**: Low -- authoring-repo-specific feature. Not a regression.

### Sampling Verification of Previously Satisfied Items

| # | Fixpoint | Status | Evidence |
|---|---|---|---|
| 1 | Multi-remote prerequisite | PASS | workflow-installed.json records cli_types=[claude,opencode,codex] |
| 2 | Spec imported via script | PASS | library-lock.yaml exists; 60 spec files across 21 dirs; requirements-discovery-foundation pack auto-imported |
| 3 | Bootstrap task removed | PASS | .trellis/tasks/00-bootstrap-guidelines does NOT exist; workflow-installed.json: bootstrap_task_removed=true, bootstrap_cleanup_status=removed |
| 4 | Customer-facing PRD in brainstorm exit | PASS | workflow-state.py CUSTOMER_ESTIMATE_MARKERS present; feasibility/brainstorm not in PROJECT_ESTIMATE_DOC_STAGES |
| 5 | Task dependency enforcement | PASS | workflow.md documents "completing the current child task does not automatically authorize the next child task" |
| 6 | Main branch + quality gates | PASS | install-workflow.py enforce_initial_main_branch_policy() exists; plan.md "明确自动化检查矩阵" requirement present |
| 7 | Task not squeezed into task_plan.md | PASS | plan.md "以 Trellis task 为主执行单元做任务图规划，task_plan.md 只保留摘要" |
| 8 | Design UI as reference only | PASS | design stage instructions present in commands |
| 9 | Strong gate user confirmation | PASS | workflow.md [workflow-state:in_progress] "Inline override" requires explicit user phrases; all stage commands have "Strong Gate" headers |
| 10 | Plan stage no implementation | PASS | plan.md "只允许重入当前已确认的 plan 阶段，不允许顺手自动进入实现" |
| 11 | UI reference vs actual tech stack | PASS | design.md separates UI prototype from implementation tech |
| 12 | Task explanation before start | PASS | workflow.md Phase 2.1 dispatch protocol includes "Active task: <path>" |
| 13 | Feasibility not skippable | PASS | feasibility.md "首次立项必经" gate rule; workflow-state:no_task block enforces task creation |
| 14 | Legal risk analysis | PASS | feasibility-check.py --step compliance; VALID_ENGAGEMENT_TYPES present |
| 15 | Source watermark | PASS | workflow-state.py VALID_SOURCE_WATERMARK_LEVELS, OWNERSHIP_POLICY_FIELDS; ownership-proof-validate.py exists |
| 16 | Effort estimation | PASS | PROJECT_ESTIMATE_REQUIRED_STAGES, TASK_ESTIMATE_MARKERS in workflow-state.py |
| 17 | Outsourcing payment safeguard | PASS | MIN_KICKOFF_PAYMENT_RATIO=30.0 in both feasibility-check.py and delivery-control-validate.py |
| 18 | Research -> implement -> check sub-agent chain | PASS | workflow.md Phase 2.1/2.2 dispatch trellis-implement/trellis-check; trellis-research in Phase 1.2 |
| 19 | .current-task cleanup after install | PASS | install-workflow.py clear_bootstrap_current_task_if_needed(); workflow-installed.json: bootstrap_cleanup_status=removed |
| 20 | Research agent search routing (Fixpoint #21) | PARTIAL | Claude/OpenCode/Codex: PASS (all 3 identical to source); Qoder: FAIL (downgraded basic version) |
| 21 | Workflow embed spec doc | PASS | commands/ directory has full set |
| 22 | Dual-language README | PASS | plan.md mentions README.md + README.en.md requirements |
| 23 | Performance optimization sub-task | PASS | plan.md "若项目包含前端视觉落地链路" and other sub-task requirements |
| 24 | Native trellis agents | PASS | Claude: 3 agents; OpenCode: 3 agents; Codex: 3 agents (all trellis-prefixed) |
| 25 | Parallel disabled | PASS | parallel.md does NOT exist; .agents/skills/parallel does NOT exist; backup preserved |

### Cross-Platform Consistency

| Platform | Research Agent | Implement Agent | Check Agent | Commands | Skills | Hooks |
|---|---|---|---|---|---|---|
| Claude | PASS (identical to source) | PASS | PASS | 11 commands | 5 skills | 3 hooks |
| OpenCode | PASS (identical to source) | PASS | PASS | 11 commands | 5 skills + plugins + lib | 3 hooks (JS) |
| Codex | PASS (identical to source) | Missing carrier comments | Missing carrier comments | Via .agents/skills (19) | Phase Router + finish-work patches | hooks.json + 2 py hooks |
| Qoder | FAIL (downgraded) | PASS | PASS | 2 commands only | 5 skills | 2 py hooks |

### Source Repo Uncommitted Changes Impact

| Changed File | Regression? | Detail |
|---|---|---|
| .codex/agents/trellis-research.toml | No | Carrier comment + search routing + multi-step task resolution; properly deployed to temp project |
| commands/delivery.md | No | Properly deployed with prepare_command_content rewrites |
| commands/feasibility.md | No | Properly deployed with gate rules and compliance checks |
| commands/plan.md | No | Properly deployed with strong gate and task decomposition |
| commands/shell/workflow-state.py | No | Identical between source and installed |
| commands/shell/delivery-control-validate.py | No | Identical between source and installed |
| commands/shell/feasibility-check.py | No | Identical between source and installed |
| commands/install-workflow.py | No | Self-check (upgrade-compat) passes with 0 conflicts |
| commands/workflow_assets.py | No | CLI_DIRS={claude,opencode,codex}; qoder not covered (pre-existing gap) |
| commands/upgrade-compat.py | No | Runs successfully against temp project |

## Caveats / Not Found

1. **Qoder platform not covered by workflow installer**: CLI_DIRS only has {claude, opencode, codex}. Qoder agents/skills come from Trellis baseline, which is not updated by the workflow installer. This is the root cause of ISSUE-1 and represents a structural gap that affects fixpoint #21 for the Qoder platform specifically.

2. **Codex implement/check carrier comments**: These are authoring-repo-only additions not yet synced to Trellis baseline. Functional impact is zero since these are purely informational comments.

3. **All three core platforms (Claude, OpenCode, Codex)**: Fully consistent with source. No regressions detected.

4. **The upgrade-compat self-check validates only CLI_DIRS-covered platforms**: It does not check Qoder, so ISSUE-1 is invisible to the automated self-check.
