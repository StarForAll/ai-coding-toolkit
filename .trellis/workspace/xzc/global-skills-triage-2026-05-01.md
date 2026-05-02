# Global Skills Triage - 2026-05-01

## Conclusion

The current truncation warning is caused by too many loaded skills, not by a
single malformed skill description.

Evidence from `~/.codex/log/codex-tui.log`:

```text
total_skills=137
budget_limit=5440
truncated_skill_descriptions=130
```

For this triage, "global skills" means skills loaded from:

```text
/ops/data/ai/skills
```

Current loaded skill sources:

| Source | Count | Action in this triage |
|---|---:|---|
| `/ops/data/ai/skills` | 117 | Triage candidates |
| `/home/xzc/.codex/skills/.system` | 5 | Keep, system-managed |
| `.agents/skills` | 14 | Keep, project workflow |
| `.codex/skills` | 1 | Keep, project workflow |

## Evidence Method

Signals used:

1. Direct `SKILL.md` read traces in `~/.codex/log/codex-tui.log`.
2. Explicit user/assistant message mentions in Codex session JSONL, excluding
   injected skill-list context.
3. Current repository references, excluding archived tasks, workspace journals,
   skill definition files, and generated session context.

Current process environment exposes the global skill library via:

```text
SKILLS_DIR=/ops/data/ai/skills
```

Interpretation:

- High direct-read count means the skill has been used or inspected repeatedly.
- Message and repo references are weaker evidence because they may mention a
  domain without actually invoking the matching skill.
- `disable-candidate` below means zero evidence across all three signals, not
  merely zero direct reads.

## Keep Globally

These global skills have repeated usage evidence or are core review/debug
workflow primitives. Do not disable in the first pass.

| Skill | Read traces | Mark |
|---|---:|---|
| `multi-cli-review-action` | 69 | keep-global |
| `systematic-debugging` | 48 | keep-global |
| `verification-before-completion` | 43 | keep-global |
| `test-driven-development` | 40 | keep-global |
| `multi-cli-review` | 38 | keep-global |
| `receiving-code-review` | 26 | keep-global |
| `sharp-edges` | 11 | keep-global |
| `doc-coauthoring` | 11 | keep-global |
| `writing-skills` | 8 | keep-global |
| `writing-plans` | 7 | keep-global |
| `ui-ux-pro-max` | 6 | keep-global |
| `shell-scripting` | 5 | keep-global |
| `documentation-templates` | 5 | keep-global |
| `collaborating-with-claude` | 4 | keep-global |

## Move To On-Demand Or Project Scope

These show some evidence, but not enough to justify global always-loaded scope.
Keep available in the skills library, but remove from default global loading
unless there is a known upcoming use.

| Skill | Read traces | Mark |
|---|---:|---|
| `trellis-meta` | 3 | on-demand |
| `mindmap` | 3 | on-demand |
| `webapp-testing` | 2 | on-demand |
| `skill-creator` | 2 | on-demand |
| `requesting-code-review` | 2 | on-demand |
| `prompt-engineering-patterns` | 2 | on-demand |
| `prd` | 2 | on-demand |
| `planning-with-files` | 2 | on-demand |
| `find-skills` | 2 | on-demand |
| `agent-browser` | 2 | on-demand |
| `zread` | 1 | on-demand |
| `vitest` | 1 | on-demand |
| `vite` | 1 | on-demand |
| `python-testing-patterns` | 1 | on-demand |
| `product-analytics` | 1 | on-demand |
| `grill-me` | 1 | on-demand |
| `design-md` | 1 | on-demand |
| `demand-risk-assessment` | 1 | on-demand-keep-if-business-use |
| `copywriting` | 1 | on-demand |
| `code-review-router` | 1 | on-demand |

Additional positive-evidence skills should not be first-pass disabled, but they
also should not be assumed global-critical without a second pass:

```text
pdf, docx, xlsx, pptx, vue, remotion, stitch-loop, shadcn-ui,
changelog-generator, simplify, project-planner,
frontend-fullchain-optimization, collaborating-with-codex, coding-standards,
architecture-patterns, karpathy-guidelines, backend-patterns,
api-design-principles, postgresql-table-design, nuxt
```

## Disable Candidates

These current global skills have zero evidence across direct reads, explicit
message mentions, and current repo references. Mark them as first-pass
candidates to remove from global always-loaded scope.

| Skill | Evidence score | Mark |
|---|---:|---|
| `wechatpay-basic-payment` | 0 | disable-candidate |
| `wechat-article-writer` | 0 | disable-candidate |
| `web-design-guidelines` | 0 | disable-candidate |
| `vue-testing-best-practices` | 0 | disable-candidate |
| `vue-router-best-practices` | 0 | disable-candidate |
| `vue-best-practices` | 0 | disable-candidate |
| `vitepress` | 0 | disable-candidate |
| `viral-generator-builder` | 0 | disable-candidate |
| `variant-analysis` | 0 | disable-candidate |
| `using-git-worktrees` | 0 | disable-candidate |
| `unocss` | 0 | disable-candidate |
| `turborepo` | 0 | disable-candidate |
| `tsdown` | 0 | disable-candidate |
| `theme-factory` | 0 | disable-candidate |
| `tailwind-design-system` | 0 | disable-candidate |
| `tailored-resume-generator` | 0 | disable-candidate |
| `strategy-and-competitive-analysis` | 0 | disable-candidate |
| `sql-optimization-patterns` | 0 | disable-candidate |
| `springboot-verification` | 0 | disable-candidate |
| `springboot-tdd` | 0 | disable-candidate |
| `springboot-security` | 0 | disable-candidate |
| `springboot-patterns` | 0 | disable-candidate |
| `spring-boot-crud-patterns` | 0 | disable-candidate |
| `spec-to-code-compliance` | 0 | disable-candidate |
| `slidev` | 0 | disable-candidate |
| `slack-gif-creator` | 0 | disable-candidate |
| `product-marketing-context` | 0 | disable-candidate |
| `product-manager-toolkit` | 0 | disable-candidate |
| `product-manager` | 0 | disable-candidate |
| `pinia` | 0 | disable-candidate |
| `paid-ads` | 0 | disable-candidate |
| `mobile-ios-design` | 0 | disable-candidate |
| `mobile-android-design` | 0 | disable-candidate |
| `markitdown` | 0 | disable-candidate |
| `marketing-psychology` | 0 | disable-candidate |
| `llm-app-patterns` | 0 | disable-candidate |
| `langchain-architecture` | 0 | disable-candidate |
| `kpi-dashboard-design` | 0 | disable-candidate |
| `java-architect` | 0 | disable-candidate |
| `ios-application-dev` | 0 | disable-candidate |
| `internal-comms` | 0 | disable-candidate |
| `insecure-defaults` | 0 | disable-candidate |
| `humanizer-zh` | 0 | disable-candidate |
| `golang-pro` | 0 | disable-candidate |
| `flutter-expert` | 0 | disable-candidate |
| `flutter-dev` | 0 | disable-candidate |
| `file-organizer` | 0 | disable-candidate |
| `dispatching-parallel-agents` | 0 | disable-candidate |
| `differential-review` | 0 | disable-candidate |
| `deployment-pipeline-design` | 0 | disable-candidate |
| `dependency-updater` | 0 | disable-candidate |
| `csv-data-summarizer` | 0 | disable-candidate |
| `contract-review-pro` | 0 | disable-candidate |
| `content-strategy` | 0 | disable-candidate |
| `competitor-analysis` | 0 | disable-candidate |
| `changelog-automation` | 0 | disable-candidate |
| `audit-website` | 0 | disable-candidate |
| `audit-context-building` | 0 | disable-candidate |
| `ask-questions-if-underspecified` | 0 | disable-candidate |
| `android-native-dev` | 0 | disable-candidate |
| `algorithmic-art` | 0 | disable-candidate |
| `accessibility-a11y` | 0 | disable-candidate |
| `API Designer` (`api-designer`) | 0 | disable-candidate |

## Recommended Next Change

Do not edit `/home/xzc/.codex/skills/.system`, `.agents/skills`, or
`.codex/skills` for this issue.

Preferred next implementation:

1. Create a curated global skills directory containing only `keep-global` skills
   plus any explicitly approved `on-demand-keep-*` exceptions.
2. Point `SKILLS_DIR` at that curated directory instead of `/ops/data/ai/skills`.
3. Keep `/ops/data/ai/skills` as the full library for manual retrieval.
4. Restart Codex and verify the warning disappears from `codex_core_skills::render`.

Expected conservative reduction if only `disable-candidate` skills are removed:

```text
117 global skills -> 54 global skills
137 total loaded skills -> 74 total loaded skills
```

Expected aggressive reduction if only `keep-global` skills stay always-loaded:

```text
117 global skills -> about 14-20 always-loaded global skills
137 total loaded skills -> about 34-40 total loaded skills
```
