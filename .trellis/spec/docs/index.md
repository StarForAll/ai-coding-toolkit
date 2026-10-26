# Project Documentation Guidelines

> Project-local rules for writing and organizing documentation in this repository.

---

## Overview

This directory is the **repo-local documentation layer** for `ai-coding-toolkit`.

Use this document for:
- README and directory-level structure in this repo
- workflow docs and maintenance notes that describe real repository behavior
- workflow-asset documentation under `docs/workflows/**`
- formatting, linking, and update habits for asset-library documentation

---

## Project Identity

This project is a **workflow authoring toolkit** — it creates, maintains, and distributes AI-assisted development workflows. It is not a target project that uses those workflows.

Key distinction:

| | This project (ai-coding-toolkit) | Target projects (other repos) |
|--|----------------------------------|-------------------------------|
| Role | **Author and distribute** workflow assets | **Install and use** workflow assets |
| `docs/workflows/*/` | Product source assets to maintain | Does not exist (installed as tool commands) |
| `docs/workflows/**/commands/*.md` | Source files to edit with authoring specs | Deployed copies managed by installer |
| `docs/workflows/**/commands/*.py` | Installer/upgrade scripts to develop | Scripts run once during embed |
| Workflow at runtime | Trellis native workflow (no Phase Router, no `workflow-installed.json`) | Workflow-enhanced Trellis (Phase Router, strong gates, `workflow-state.json`) |
| Dev process | `/trellis:start` → Trellis native brainstorm/check/finish-work | `/trellis:start` → Phase Router → feasibility/brainstorm/design/plan/... |

**Critical rule**: When modifying files under `docs/workflows/`, you are editing **product assets** — the stage gates, Phase Router, `workflow-state.json` state machine, outsourcing controls, and delivery protocols defined in those files are features of the product, not rules for how to develop in this project. The specs that govern your editing behavior are in `.trellis/spec/scripts/` (installer/upgrade contracts, command-doc authoring contracts), not in the workflow's own `阶段状态机与强门禁协议.md` or `工作流总纲.md`.

---


| Type | Location | Purpose |
|------|----------|---------|
| Repository README | `README.md`, `README.en.md` | Explain what this repo contains and how the asset layers relate; maintain the Chinese default plus aligned English companion |
| Asset README | `agents/README.md`, `commands/*/README.md`, `docs/README.md` | Clarify scope and structure of one asset area |
| Workflow docs | `docs/workflows/**` | Human-facing workflow notes and command references |
| Workflow authoring spec | `docs/workflows/自定义工作流制作规范.md` | Cross-workflow authoring rules, including Trellis upgrade-compat baseline requirements |
| Trellis spec docs | `.trellis/spec/**` | Repo-local maintenance guidance plus workflow-authoring rules used by this repo |
| Library docs | `trellis-library/README.md`, `trellis-library/taxonomy.md` | Source-library architecture and taxonomy |

---

## Boundary

Do not add generic application README templates, frontend/backend doc advice, or
API-reference scaffolds here. This repository is an asset library and workflow
tooling repo, not a runnable app.

Do not treat `docs/workflows/*/` content as development rules for this project.
Those are product assets — see [Project Identity](#project-identity) above.

This directory should stay focused on repository-specific documentation
conventions and examples.

---

## Directory Structure

```text
docs/
  README.md
  workflows/
    新项目开发工作流/
      工作流总纲.md
      工作流思维导图.html    ← generated per workflow-mindmap-spec.md
      commands/
    旧项目重构工作流/
      工作流总纲.md
```

---

## Mindmap Generation

When a workflow document needs a visual companion mindmap, follow
[workflow-mindmap-spec.md](./workflow-mindmap-spec.md).

Key contracts:
- Output: self-contained `.html` file, no external deps
- Layout: right-expanding tree, parent centered on children block
- Data: inline JS `const tree = [...]` array with typed node classes

---

## Reviewing Design/Contract Docs

When the task is to **review** (not edit) a design or contract document under
`docs/workflows/` — especially `workflow-design.md` — read
[Design-Doc Review Thinking Guide](../guides/design-review-thinking-guide.md)
first. It defines the evidence bar, the four filters, the required "excluded
candidates" section, and the known false-positive patterns. Its structural
blind-spot list covers one-sided edits (口径 11, now intra-document as well
as cross-doc), references used as exits (口径 12, walk the referenced
preconditions), multi-step writes with no mid-state (口径 13/14: enumerate
windows, give every residual a unique signature), exceptions registered by
source/role instead of by state (blind spot 10; v40 replaced §7.4's list with a
field predicate), and one action sequence defined twice in different orders
(blind spot 11; sole source is now §7.7 类型 5).

Version drift in derived docs (for example a flow diagram still labeled v24) is
a report item, not a design defect.

---

## README Standards

### Project Root README

Must include:
- **Project title**: Clear, searchable name
- **One-line description**: What reusable assets this repo contains
- **Repository map**: Core directories and what each one owns
- **Source-of-truth explanation**: Which directories are source assets versus derived tool deployments
- **Validation commands**: How to run repo checks that matter
- **Links**: To workflow docs, `trellis-library`, and relevant spec indexes

Additional contract for this repository:
- The project root README is a **paired bilingual asset**: `README.md` is the default Simplified Chinese entry, and `README.en.md` is the aligned English companion
- **Any modification** to the project root README content, structure, commands, paths, links, or status descriptions must update **both** `README.md` and `README.en.md` in the same change
- The two files must keep visible cross-links near the top so readers can switch languages directly

### Directory README

For subdirectories:
- **Purpose**: What this directory contains
- **Structure**: Overview of files or subdirectories
- **Source/deploy boundary**: If this directory feeds other tool-specific copies
- **Usage**: How to modify or validate these files

---

## Writing Guidelines

### Language

- **Default**: Match the directory's established language
- **Consistency**: Keep one document internally consistent
- **Commands / identifiers**: Preserve exact paths, filenames, and command names

### Formatting

- **Markdown**: Use standard MD syntax
- **Code blocks**: Language-specific syntax highlighting where useful
- **Links**: Relative paths for internal links
- **Headings**: Use ATX-style (`#`, `##`, `###`)

### Content

- **Concise**: Get to the point
- **Actionable**: Tell reader what to do
- **Complete**: Include prerequisites, steps, and verification when behavior is procedural
- **Current**: Keep up to date with code

### Workflow Boundary

- **Separate ownership layers**: Distinguish source-repo authoring files, task-local runtime artifacts, and target-project outputs
- **Name the target explicitly**: If a workflow creates or updates files in the consuming project, say "target project" and give the target path
- **Do not conflate artifacts**: Explain different roles when both task-local working files and project-level formal docs exist
- **Preserve deploy semantics**: When source docs are installed into other tool/runtime locations, state whether the rule applies to the source copy, deployed copy, or target project filesystem
- **Do not describe target architecture as current repo state**: For repo-level docs such as the root `AGENTS.md` and README files, distinguish placeholder/scaffold directories from the workflow-local source or live deployed copies that actually drive behavior today
- **Keep source-repo AGENTS separate from install-time target-project AGENTS blocks**: Installer-managed target-project sections such as `workflow-nl-routing` should be described as target-project outputs, not mirrored into this source repository's own `AGENTS.md`, unless the authoring contract explicitly requires the source repo to carry the same block
- **Use a clean Trellis baseline for source-workflow compatibility maintenance**: When documenting how this repository updates Trellis-based workflow source content after a Trellis upgrade, reference the `/tmp` fixture created by `trellis init`, not this repository's already customized `.trellis/` or CLI directories; do not present that rule as the target project's own upgrade-compat standard
- **Keep pre-release workflow versions below 1.0**: For workflow source assets under `docs/workflows/**` that are not yet officially declared production-ready, the active version must use `0.x.y`; reserve `1.0.0+` for workflows explicitly declared formally available
- **Keep active version references aligned**: When the current workflow version changes, update the single-source version in code plus every active-source reference together, including `commands/workflow_assets.py`, the workflow's `工作流总纲.md` title and current version-history row, `命令映射.md`, walkthrough docs, mindmap HTML title/root label, and installer tests that assert `workflow_version`

---

## Template: Directory README.md

```markdown
# Directory Name

Brief description of what this directory owns.

## Purpose

What belongs here and what does not.

## Structure

- `path-a/` - explanation
- `path-b/` - explanation

## Update Notes

- How to modify safely
- How to validate changes
- Related source-of-truth or deployment paths
```

---

## Quality Standards

### Must Have

- [ ] Clear title and purpose
- [ ] Logical structure with headings
- [ ] Exact repo paths and commands where applicable
- [ ] Links to related docs

### Should Have

- [ ] Small examples for non-obvious workflows
- [ ] Validation note for change-heavy docs
- [ ] Table of contents for long docs

### Anti-Patterns

- **Outdated docs**: Docs that contradict code
- **Incomplete steps**: "Do X" without explaining how
- **No context**: "Run this command" without explaining why
- **Broken links**: Internal links that don't work
- **App-centric boilerplate**: Installation or runtime sections for software this repo does not ship
- **Inconsistent formatting**: Mixed styles in same doc
- **Split bilingual README maintenance**: Updating `README.md` or `README.en.md` alone when the root README contract requires both files to stay aligned
- **Target-project ambiguity**: Referencing paths like `docs/...` without saying whether they live in this repo, a task directory, or the installed target project
- **Artifact conflation**: Treating task-local files such as `$TASK_DIR/prd.md` as equivalent to long-lived project requirement documents
- **Version drift across workflow source files**: Updating `WORKFLOW_VERSION` or a workflow title without synchronizing the other active references, installer assertions, or generated companion docs

---

## Workflow Rule Propagation

When a workflow rule changes in a canonical command file (e.g., `commands/brainstorm.md`),
the change must be verified across **all documents that reference the rule**. A rule change
is not complete until every referencing document has been updated.

### Propagation Checklist

After changing a workflow rule in any command file:

1. `grep` the entire `docs/workflows/<workflow-name>/` directory for the old wording
2. Check these categories of referencing documents:
   - Other command files (`commands/*.md`)
   - `工作流总纲.md` (the authority layer)
   - `工作流嵌入执行规范.md` (the embed-contract layer, when the workflow defines one)
   - `命令映射.md` (the routing layer)
   - `多CLI通用新项目完整流程演练.md` and `完整流程演练.md` (the walkthrough layer)
   - `工作流全局流转说明（通俗版）.md` (the overview layer)
   - Maintainer-facing boundary docs such as `装后隐藏目录与托管边界核对清单.md`, `CLI原生适配边界矩阵.md`, and `目标项目兼容升级方案指导.md`
   - Platform README files (`commands/opencode/README.md`, `commands/codex/README.md`)
   - Command-derived skill entrypoints (`.agents/skills/*/SKILL.md`, `.qoder/skills/*/SKILL.md`) when the workflow is consumed through skills
   - `learn/README.md` (examples and gotchas)
   - Test files (`test_workflow_installers.py`)
   - Validation scripts (`shell/plan-validate.py`)
   - HTML mindmap (`工作流思维导图.html`)
3. Verify: no residual references to the old rule remain

### Known Propagation-Prone Rules

These rules have historically required cross-document propagation:

- **sonar-scanner conditionalization**: "必须有明确质量平台门禁；采用 Sonar 的项目写真实命令，未采用时写替代门禁和原因" — appears in 总纲, design, plan, finish-work, brainstorm, 命令映射, walkthrough, test
- **L0/Lite dual-PRD relaxation**: "L0 不强制双 PRD" — appears in brainstorm, 命令映射, walkthrough
- **review-gate conditional trigger**: "check 默认进 finish-work，条件触发 review-gate" — appears in check, review-gate, start phase router, 总纲, walkthrough, 通俗版
- **workflow close-out order**: for the installed target-project workflow, fresh-baseline close-out enters through Trellis native `finish-work`, using `task.py archive` plus `add_session.py`. This is a product/runtime contract for workflow-installed target projects.
- **project-audit conditional generation**: "不是所有项目都强制" — appears in brainstorm, plan, project-audit, plan-validate.py
- **ownership-proof workflow gate**: "`ownership_proof_required` 启用后，`source_watermark_channels` 决定实际验证范围，且 `visible` 是最低必选通道；若 design 声明了 `Protected Watermark Snippets`，后续改动还必须通过 `source-watermark-guard.py` 保持/修复检查" — appears in feasibility, design, plan, check, delivery, 总纲, 命令映射, walkthrough, 通俗版, platform README, validator tests
- **first-entry feasibility gate**: "所有新实现任务首次入口都必须先经过 feasibility；只有仍有效且明确允许进入 brainstorm 的 assessment 才能被复用到 brainstorm，任何 profile 都不存在首次入口跳过 feasibility 的例外" — appears in feasibility, brainstorm, workflow phase router docs, workflow.md patch source, 总纲, 命令映射, walkthrough, AGENTS/NL routing text, installer-generated skill/session-start text, and validator tests
- **execution authorization semantics**: "`checkpoints.execution_authorized` 表示用户已明确批准当前叶子任务进入真实 implementation/执行边界；未获批准前必须保持 false，离开执行态后自动重置" — appears in 阶段状态机与强门禁协议, workflow.md patch source, implementation/plan guidance, workflow-state validators, repair output, and tests
- **repair confirmation output contract**: "`workflow-state.py repair` 在 `manual_confirmation_required` 时必须同时输出结构化的 `required_confirmation_args` 与 `missing_confirmation_items`，不能只把缺项埋在自然语言 message 里" — appears in workflow-state.py, start/continue phase-router guidance, workflow.md patch source, and tests
- **embed-integrity semantic patch check**: "`embed_integrity.py` 对关键 runtime Python patches 不能只看 marker；至少要校验稳定的补丁语义片段，避免 marker 保留但补丁语义已漂移" — appears in embed_integrity.py, install/upgrade validation expectations, 装后核对清单, and tests
- **breadcrumb status charset contract**: "workflow breadcrumb tag keys must stay within the parser-allowed status alphabet unless the workflow patch source, installed carrier regexes, and regression tests are widened together" — appears in workflow patch source, inject-workflow-state patch helpers, installed carrier parsers, and workflow-state tests
- **OpenCode strong-gate hard-stop contract**: "当嵌入 workflow 声明 main-session-only 时，OpenCode 的 blocked subagent path 必须真正终止 Task 执行；仅改 prompt 或仅打印 blocked 提示不算有效强门禁" — appears in OpenCode subagent patch helper, embed_integrity.py, upgrade-compat.py, CLI 边界文档, workflow-audit evidence, and regression tests
- **multi-cli reviewer command pairing**: "需要调用 `multi-cli-review` 时，按当前模式生成匹配的 reviewer 命令：`lite` 默认 1 条，`full` 默认至少 2 条且只在 `--reviewer-id` 上不同；需要进入汇总修复时，同时生成匹配的 `multi-cli-review-action` 聚合命令；task-level `reviewer-id` 默认使用 `a/b/c/d` 这类字母槽位，真实 CLI 身份记录在 `source-cli`" — appears in review-gate, project-audit, 总纲, walkthrough, platform instructions, and any reviewer command pack templates
- **workflow embed execution contract**: "只有纯净初始态目标项目才允许执行首次嵌入；只要嵌入前置条件、初始态判定、非初始态阻断、完整/有效嵌入判定、托管资产范围、`install-workflow.py` / `upgrade-compat.py --check` 行为、`workflow-embed-attempt.json` / `workflow-installed.json` 语义、或 CLI 原生入口承载方式发生变化，就必须同步评估 `工作流嵌入执行规范.md` 是否需要更新" — appears in 嵌入执行规范, 总纲, 命令映射, walkthrough, CLI 边界矩阵, 装后核对清单, platform README, installer / checker scripts, and installer regression tests
- **command-source vs maintainer-doc boundary**: "阶段命令源文档只保留产品/runtime 语义；维护者专用说明不得混入 `commands/*.md`，而应同步落到 `装后隐藏目录与托管边界核对清单.md`、`CLI原生适配边界矩阵.md`、`目标项目兼容升级方案指导.md` 与必要的平台 README" — appears in command-doc authoring spec, maintenance docs, platform README, and any tests/assertions that verify deployed command content
- **ordinary-use defect boundary**: "当前 workflow 的缺陷判定默认面向个人正常使用 / 诚实使用路径；只有通过刻意篡改文件、伪造状态、主动绕过命令约束等恶意方式才会触发，而正常使用链路下不会出现的问题，不按默认漏洞/缺陷口径处理" — appears in 总纲, 通俗版, 目标项目兼容升级方案指导, 结构性迁移设计, and `workflow-audit` spec

### workflow-design.md Predicate Registry and Probes

`docs/workflows/workflow-design.md` (v34+) defines each load-bearing
predicate in exactly one place; every other occurrence must be a reference,
not a restated condition (main doc §0 写作约定, added in v34). Registry —
update the row when a source moves:

| Predicate | Sole source | Sanctioned reference forms | Banned (defining restatement) |
|---|---|---|---|
| Current-task pointer validity | 主设计 §3 「当前任务」 | “按 §3 判定”“按 §3 有效（且非挂起）”“按 §3 无效”“视为无当前任务”；companion doc: “按主设计 §3 判定” | Any parenthetical restatement posing as “按 §3 有效（…）”; enumerating the invalid list anywhere outside 主设计 §3 (companion doc included) |
| Dependency satisfied / ready | 主设计 §4.3 依赖满足 (§3 就绪 references §4.3) | Action sequences may reuse “前置全部为正常” verbatim | A second “依赖满足 = …” / “就绪 = …” definition or any competing satisfaction semantics |
| Start-work legality | 主设计 §7.5 开工 | “按 §7.5 校验”; summary tables cite §4.5 / §7.5 (表 4-1 form) | Re-writing the full condition in a summary table |
| Finish legality | 主设计 §7.5 完成 + §5.3 可见性顺序 | “按 §5.3 / §6.3 执行” | Same |
| Project-layer role succession | 主设计 §6.5「替换 / 放弃项目层任务 P」 | “继任者即新的 P”（§6.6 放弃变体、§9.1 说明、配套 §6.0，均指向 §6.5）；§6.6 放弃-新建替代与 §7.7 类型 1 补建亦以 §6.5 为归属源 | Re-deciding who succeeds P elsewhere, or leaving a P disposition without a successor |
| Type-1 P succession markers | 主设计 §7.7 类型 1 | “替换指向随「异常」同次预写”“逐窗口”“P 改为放弃沿用预写标识、不置空”（配套 §8 类型 1 镜像，细则不重述） | Writing “回填替换指向” as the only timing, or a P successor path without per-window residual identification |
| Replacement-pointer write matrix | 主设计 §7.8 写入矩阵（唯一源，9 行：8 条机制写入路径 + 类型 4 记录修复行及其校验——指向为空或可解析到已存在任务、不得借修复新建继任关系） | “按 §7.8 写入矩阵（<行名>）写入 / 置空 / 不新增写入”；各动作步与全部镜像（主稿 §6.5/§6.6/§7.7、配套 §5/§6.4/§6.5/§8/§9）只许引用、不得复述终值 | A pointer write/clear rule or terminal value stated outside the matrix (v41 first pass: companion §9 “不清空” without exception; v41 second pass: terminal values still restated at 6+ action-step sites, and the closed assertion 「已归档后不再有任何指向写入」 blocked matrix row 4); a second clearing point appearing without matrix registration |
| Disposition of an abnormal task’s downstream | 主设计 §7.4 | “按 §7.4 处置”（§9.1 两表、§8.4 第三段、§7.7 启动段、组合表行 10）；字段谓词本身见下一行（Disposition-terminal predicate）——引用时不得复述旧形「替换指向仍在 / 已归档 + 无指向 + 下游已不指向」；P 的继任是角色条款（§6.5 / §7.7 类型 1） | 按来源 / 角色逐格追加例外（如 v38 的「一般任务 / P 例外」）；把「已归档时不可替换」写成无字段限定的绝对句；或把该处分写进 §6.5 的失败与修复 |
| Forward-completion action sequence | 主设计 §7.7 类型 5 | “按 §7.7 类型 5 向前完成”“序列 / 顺序 / 窗口以主设计 §7.7 类型 5 为唯一源”（§6.5、§6.6、§7.9、配套 §6.4、配套 §8） | A second step list that changes the order (notably 归档 before 补建 / 重连 — v39's 「旧任务未归档 → 归档旧任务」), or restating the sequence anywhere other than a same-order mirror |
| Disposition-terminal predicate | 主设计 §7.4 表行（唯一源） | “处分已到终态（已归档，且下游已不指向它，且（无替换指向 或 继任者已建））”“处分未完成（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）”；§7.7 窗口⑤ 为标注同口径的引用；主 §7.4 口径句、配套 §5 行 + 表后段、配套 §9 为**引用式**（“以主设计 §7.4 表行为唯一源，本处不复述”） | The v40 shape “已归档 + 替换指向为空 + 下游已不指向它”; restating the predicate at any of the reference sites (the v41-first-pass “four synchronized copies” — 口径 11 says a demoted-to-reference copy is the sanctioned sync form, a restated copy recreates the drift surface) |
| Successor identity（放弃-新建替代） | 主设计 §6.6 实施第 1 步 + §7.8 | “替换指向 = 发起时预生成的替代标识”“沿替换指向解析”（§9.1 说明、配套 §9） | Writing the pointer only after the successor task exists, or leaving 放弃-新建替代 with an empty pointer |
| Selection when no current task | 主设计 §9.1 第三段两张表 | “按 §9.1 第三段两张表选择”“按 §9.1 选择”；§7.6、§8.4 第三段、配套 §7 均为引用 | Restating the branch conditions (等前置 / 最早就绪) outside §9.1 — v38's §8.4 miss |

Key distinction: **defining restatements are banned; action-condition
references are allowed** — once the source definition fixes the semantics, a
verbatim condition inside an action sequence inherits it and does not create a
second predicate.

Probes — run after any `workflow-design.md` revision, against both documents
(expected values as of v41). The run is mandatory, not optional: update expected
values in the same pass as any predicate change — a registered probe with a
stale expected value that nobody runs is exactly how v40's disposition-terminal
defect escaped (see blind spot 12 in the design-review guide):

```bash
rg -n "按 §3 有效（" docs/workflows/workflow-design.md                 # 0 hits
rg -n "有当前任务，且该任务未归档、账本为|有当前任务，但该任务未归档、账本为|有当前任务，但该任务已归档" docs/workflows/workflow-design.md   # 0 hits (old condition-style rows gone)
rg -n "按 §3 有效|按 §3 无效" docs/workflows/workflow-design.md        # 9 lines as of v34: 6 normative (§8.4 ×1, §9.1 rows 1/2 ×4, §9.1 说明 ×1) + 3 record mentions (frontmatter status, version blockquote, appendix C entry — they name the form, they do not define it)
rg -n "依赖满足 =|就绪.*前置集合全部为" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md   # 3 lines as of v34: 主设计 §3 就绪 + §4.3 依赖满足 + 配套 §3 就绪 (all others must be references)
rg -n "满足判定按 §4.3|按主设计 §4.3" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md   # 5 lines: 主设计 §3 就绪；配套 §3 就绪、§5 判定规则、§6.7 建边（“该态按主设计 §4.3 视为未满足”）、§22 revision record (stable since v34; 主设计 §4.3's own bullet states the rule, not a reference, so it does not match this probe)
rg -n "指向已归档、规划中且前置未满足" docs/workflows/依赖机制设计说明.md   # 0 hits (companion references 主设计 §3 instead)
rg -n "或为“正常但未归档”的任务|前置未完工（或为" docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md   # 0 hits (satisfaction exception folded into 未完工 enumeration)
rg -n "视为无当前任务" docs/workflows/workflow-design.md               # diff vs registry snapshot; new hits must be reference-form (historical appendix entries stay)
rg -n "继任者即新的 P" docs/workflows/workflow-design.md                 # 2 hits: the §6.5 source + the v35 appendix record; every other place must point at §6.5, not restate it
rg -n "异常前置走替换|前置为异常时按删边或替换" docs/workflows                  # 0 hits as of v36 (all point at §7.4)
rg -n "按 §7.4 处置|按主设计 §7.4" docs/workflows                            # references only (9 main + 4 companion as of v40); the §7.4 table row is the sole definition
rg -n "或删边后不再等待$" docs/workflows                                     # 0 hits: no un-narrowed copy of the abnormal-downstream sentence
rg -n "预生成.{0,4}新 P" docs/workflows                                     # 2 hits as of v41 third pass: main §7.8 写入矩阵行 (the sole rule site — the §7.7 action step was demoted to a matrix reference) + v37 appendix record; a hit anywhere else means a terminal-value restatement returned
rg -n "修复的写入纪律" docs/workflows                                        # 4 hits: main §7.7 + appendix v37/v38 records + companion §8 (demoted to a reference)
rg -n "两种处置由人决定" docs/workflows                                  # 0 hits (variant is decided at 发起 since v38)
rg -n "只余删边" docs/workflows                                       # 7 hits as of v40, all in version-收口 blockquotes / revision records (judge by context, not line numbers — they shift每版); 0 normative hits — the disposition is now a field sentence
rg -n "下游仍指向该任务、该任务未归档" docs/workflows               # 4 hits as of v41 second pass: 1 normative (main §7.4 表行, the predicate's sole defining site) + 3 historical revision records (main v41 + v40 appendix, companion §28 v40); a hit at main §7.4 口径句 or companion §5 表行/表后段 means the predicate got restated (the v41-first-pass four-copy shape)
rg -n "旧任务未归档 → 归档旧任务|边已重连但旧任务未归档" docs/workflows   # 0 hits — the forward-completion order lives only in §7.7 类型 5
rg -n "先补建 / 重连、后归档" docs/workflows/workflow-design.md      # 2 hits: §7.7 类型 5 (sole source) + v40 record; the sequence wording must not appear in §6.5 / 配套 §6.4 / 配套 §8
rg -n "替换指向为空" docs/workflows                                  # ALLOWED: revision records only (v41/v40 appendix entries quoting the old shape); BANNED: any normative hit — the v41 terminal predicate uses 「无替换指向 / 继任者已建」 and the 删边-variant step lines now reference the §7.8 matrix instead of stating 「替换指向为空」; a normative hit here means the v40 terminal shape (or a step-level terminal-value restatement) returned
rg -n "新建替代" docs/workflows                                     # every normative line names 预生成 / 第 1 步 or points at §6.6; revision records are historical
rg -n "继任任务" docs/workflows                                     # 3 hits: §3 term + §9.1 note + v38 appendix record
rg -n "无当前任务时：T 进行中或规划中但前置含非正常" docs/workflows    # 0 hits (the §8.4 summary copy is now a reference, v39)
rg -n "无当前任务时按 §9.1" docs/workflows                            # 2 hits: §8.4 第三段 (normative) + v31 appendix record
rg -n "继任者已建" docs/workflows                                      # ALLOWED: main §7.4 表行 (sole predicate definition) + §7.7 窗口⑤ (marked 同口径引用) + 口径 10④ 轴名 + action-branch conditions inside the forward-completion sequence (§7.7 补建「继任者已建时只补齐重连」— verbatim condition inside an action sequence inherits the source, registry principle) + revision records / companion §29; BANNED: any sentence outside these sites restating the terminal/incomplete field combination as a standalone judgment (esp. main §7.4 口径句, main §7.8, companion §5, companion §9)
rg -n "唯一清空点" docs/workflows                                     # 2 hits as of v41 third pass: main §7.8 写入矩阵行 + v41 appendix record; companion carries no terminal values anymore (demoted to references) — any normative hit outside the matrix row means an unregistered clearing rule appeared
rg -n "写入矩阵" docs/workflows                                        # 27 hits as of v41 sixth pass: main 17 (§7.8 唯一源句 + 矩阵引导句 + action-step references: §6.4 返工来源、§6.5/§6.6 step 1 ×2、类型 1 一般/P、类型 5 改判 ×2、类型 4、识别句双缺失出口 + §7.4 口径句指引 + 口径 10⑥ + frontmatter status + v41 record) + companion 10; ALLOWED: exactly one full matrix (main §7.8 识别字段写入矩阵, 10 rows × 3 field columns: 指向 + 说明 + 返工来源), every other hit must be a reference, not a restated terminal value; BANNED: a second full matrix, or a pointer/说明/返工来源 write/clear rule stated outside a reference
rg -n "P 的指向不得置空" docs/workflows                            # 4 hits: main §7.8 矩阵行 9 (P guard, sole rule site) + v41 record + companion §9 / §29 references; the type-4 repair entrance must never strand P's successor chain (§6.6 role invariant) — losing this guard reopens the v35/v36 project-layer-object loss via a new entrance
rg -n "唯一 / 不再 / 一律 / 只」" docs/workflows                     # GATE-EXISTENCE CHECK ONLY (not a sweep): this literal string only matches the gate's own wording in §0 写作约定 + 口径 10⑤ — it proves the closed-assertion gate exists, it cannot detect newly written closed assertions. The actual assertion × path enumeration is a human/LLM judgment done under 口径 10⑤ and recorded in the review report; do not treat this probe passing as that check having run
rg -n "新建替代" docs/workflows/依赖机制设计说明.md                      # 发起 / 实施第1步 / 实施第2步 / §9；实施第2步必须含「继承旧任务当前的前置集合」（v41），缺句即 F2 回归
```

---

## Code Examples

### Good

```bash
# Validate skill structure
./scripts/validate-skills.sh
```

### Bad

```text
Run the validator
```

---

## Links

### Internal Links

```markdown
[Workflow](../../../docs/workflows/新项目开发工作流/工作流总纲.md)
[Spec Index](../index.md)
```

### External Links

```markdown
[Skills CLI](https://www.npmjs.com/package/skills)
```

---

## Maintenance

- Review docs when code changes
- Remove obsolete information
- Check sample commands still work
- Re-test links when moving files

---

## Tools

- Markdown linters: `markdownlint`
- Link checkers: `lychee`
- Spell checkers: `cspell`

---

**Language**: Match the document's existing language and audience
