# Workflow Command Document Authoring Contracts

> Executable contracts for authoring and maintaining workflow command source documents under `docs/workflows/**/commands/*.md`.

**Reminder**: This project is a workflow authoring toolkit. The command `.md` files are **product assets** distributed to target projects — not development rules for this project. See `docs/index.md` → Project Identity.

---

## Scenario: Workflow Command Document Structure

### 1. Scope / Trigger

- Trigger: creating a new `docs/workflows/**/commands/<command>.md`
- Trigger: modifying the section structure of an existing command document
- Trigger: adding a new mandatory section pattern across multiple command documents

### 2. Required Sections

Every workflow command document must include these sections in order:

| Section | Heading Pattern | Required | Purpose |
|---------|----------------|----------|---------|
| Natural-language trigger | `## When to Use (自然触发)` | Yes | Lists user phrases and scenarios that route to this command |
| Pre-conditions | `## 前置条件` or `## 前置条件与边界` or `### 前置条件与出口约束` | Yes | Entry requirements; may reference `workflow-state.py validate` |
| Gate validation block | `### 门禁校验` | Yes (for gated stages) | Standard block invoking `workflow-state.py validate` |
| Steps | `### Step N: <name>` | Yes | Numbered execution steps |
| Next-step recommendation | `## 下一步推荐` | Yes | Multi-path recommendation table |

### 3. Contracts

#### 3.1 Gate Validation Block

For stages that have programmatic validation, use this standard block instead of restating validation rules in prose:

```markdown
### 门禁校验

\`\`\`bash
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
\`\`\`

校验通过后继续当前阶段；失败时按输出的错误项逐项修复后重试。
```

**Rule**: Do not restate in prose what `workflow-state.py validate` already enforces programmatically. If a validation check exists in the Python script, the command document must reference the script output, not duplicate the field-level logic.

Rationale: During the 2026-04 refactoring, ~150 lines of duplicated validation prose were removed from 5 command documents. The prose restated checks for `project_engagement_type`, `kickoff_payment_*`, `customer-facing-prd.md` existence, and project-estimate markers — all already enforced by `validate_external_project_controls` and `validate_project_doc_boundary` in `workflow-state.py`.

#### 3.2 Next-Step Recommendation Table

Every command document must end with a standard recommendation table:

```markdown
## 下一步推荐

**当前状态**: <one-line summary>

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| <default intent> | `/trellis:<command>` | <natural language or skill> | **默认推荐**。<explanation> |
| <alternative> | `/trellis:<command>` | <natural language or skill> | <explanation> |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | Phase Router 阶段检测 |
```

Requirements:
- Must include at least one **默认推荐** row
- Must include a `/trellis:start` fallback row
- Must have separate Claude/OpenCode and Codex columns (Codex does not support `/trellis:xxx` commands)

#### 3.3 Step Numbering

- Steps use `### Step N:` format (not `####`)
- Step 0 is reserved for initialization/validation
- Steps that only apply conditionally use `(如适用)` suffix: `### Step 4: 外部项目交付控制门禁（如适用）`

---

## Scenario: Conditional Content Markers

### 1. Scope / Trigger

- Trigger: adding outsourcing-specific content to a command document
- Trigger: adding any profile-conditional content

### 2. Marker Syntax

```markdown
<!-- if:outsourcing -->
(content only included when profile=outsourcing)
<!-- endif:outsourcing -->
```

### 3. Contracts

| Rule | Detail |
|------|--------|
| Markers on own line | No other content on the marker line |
| Always paired | Every `<!-- if:outsourcing -->` must have a matching `<!-- endif:outsourcing -->` |
| No nesting | `<!-- if:outsourcing -->` inside another `<!-- if:outsourcing -->` is not supported |
| No inline | `<!-- if:outsourcing -->content<!-- endif:outsourcing -->` on one line will not be stripped |

### 4. Stripping Behavior

Implemented in `workflow_assets.py` → `prepare_command_content(source_path, *, profile)`:

| Profile | Behavior |
|---------|----------|
| `personal` | Remove markers AND wrapped content |
| `outsourcing` (default) | Remove markers only, keep wrapped content |

### 5. What to Wrap

Wrap content that is **exclusively relevant** to external outsourcing / contract delivery:

- Kickoff payment gates and delivery control tracks
- Trial authorization terms
- Source watermark and ownership proof sections
- External project delivery event checklists
- Outsourcing-specific task splitting in plan stage

Do **not** wrap content that applies to all projects even if it mentions "外包" as one example among several.

### 6. Wrong vs Correct

#### Wrong
```markdown
<!-- if:outsourcing -->some content on same line<!-- endif:outsourcing -->
```

#### Correct
```markdown
<!-- if:outsourcing -->
some content on its own line(s)
<!-- endif:outsourcing -->
```

---

## Scenario: Source-to-Deploy Path Rewriting

### 1. Scope / Trigger

- Trigger: referencing helper scripts, execution cards, or other files with paths that differ between source and target project

### 2. Contracts

Command source files use **source-repo paths**. `prepare_command_content()` in `workflow_assets.py` rewrites them at deploy time.

Current rewrite rules:

| Source form (what you write) | Deployed form (what target project sees) |
|-----------------------------|------------------------------------------|
| `<WORKFLOW_DIR>/commands/shell/` | `.trellis/scripts/workflow/` |
| `docs/workflows/新项目开发工作流/commands/shell/` | `.trellis/scripts/workflow/` |
| `[需求变更管理执行卡](../需求变更管理执行卡.md)` | `[需求变更管理执行卡](.trellis/workflow-docs/需求变更管理执行卡.md)` |
| `[源码水印与归属证据链执行卡](../源码水印与归属证据链执行卡.md)` | `[源码水印与归属证据链执行卡](.trellis/workflow-docs/源码水印与归属证据链执行卡.md)` |
| `[阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md)` | `阶段状态机与强门禁协议` (plain text, not a link) |

### 3. Rules

- Use `<WORKFLOW_DIR>/commands/shell/` as the canonical source-form prefix for helper scripts
- Use `(../需求变更管理执行卡.md)` as the canonical source-form link for execution cards
- Do not use absolute paths or target-project paths in source files
- If a new rewrite rule is needed, add it to `prepare_command_content()` in `workflow_assets.py` first, then use the source form in command docs

### 4. Wrong vs Correct

#### Wrong (target-project path in source file)
```markdown
python3 .trellis/scripts/workflow/workflow-state.py validate <task-dir>
```

#### Correct (source-repo path, will be rewritten at deploy)
```markdown
python3 <WORKFLOW_DIR>/commands/shell/workflow-state.py validate <task-dir>
```

---

## Scenario: Referencing Product Runtime Rules

### 1. Scope / Trigger

- Trigger: modifying a command document and needing to describe the product's runtime behavior

### 2. Contracts

Command documents define what the **product does when installed in a target project**. They are not rules for this project's own development process.

When editing command docs, the authoring specs to follow are:

| Need | Read this spec |
|------|---------------|
| Installer/upgrade behavior | `scripts/workflow-installer-upgrade-contracts.md` |
| Command document format | This file (`scripts/workflow-command-doc-contracts.md`) |
| Python script conventions | `scripts/python-conventions.md` |
| Rule propagation checklist | `docs/index.md` → Workflow Rule Propagation |

Do **not** follow these product documents as your development rules:

| Product document | What it defines | For whom |
|-----------------|-----------------|----------|
| `阶段状态机与强门禁协议.md` | Stage transition rules | Target project AI |
| `工作流总纲.md` | Full workflow lifecycle | Target project AI/human |
| `命令映射.md` | Stage→command routing | Target project AI |

You may read them to understand the product's design intent, but they do not constrain your editing behavior in this project.

---

## Scenario: Maintainer-Only Guidance Boundary

### 1. Scope / Trigger

- Trigger: adding usage examples that differ between workflow source maintenance and target-project runtime
- Trigger: explaining how maintainers should validate deployed assets from this repository
- Trigger: modifying path examples, helper entrypoints, execution-card links, or Phase Router invocation examples in command documents

### 2. Contracts

Workflow command source documents are **product assets**. They should describe the workflow's runtime behavior for an installed target project, not mix in maintainer playbooks for this repository.

#### 2.1 Single-Semantics Rule

- Command source documents must keep a **single product/runtime semantics**
- Do **not** mix these two audiences inside the same command source file:
  - target-project runtime user/AI
  - source-repo maintainer validating or debugging workflow assets
- Source files may still use **source-form paths** such as `<WORKFLOW_DIR>/commands/shell/...`; this is a deployment authoring convention, not a second audience

#### 2.2 Where Maintainer Guidance Belongs

Maintainer-only instructions must live in dedicated maintenance documents, for example:

- `装后隐藏目录与托管边界核对清单.md`
- `CLI原生适配边界矩阵.md`
- `目标项目兼容升级方案指导.md`
- platform adapter READMEs under `commands/claude/README.md`, `commands/opencode/README.md`, `commands/codex/README.md` when the change is CLI-specific

#### 2.3 When Sync Is Mandatory

If a command-doc change affects any of the following, you must explicitly review the maintainer-facing docs above and update the affected ones in the same change:

- source-to-deploy path rewrite rules
- helper script invocation forms
- execution-card distribution or link targets
- Phase Router invocation examples or route/repair semantics
- what is installer-managed vs target-project-managed vs manually maintained
- which deployed files are expected in target projects after install/upgrade

#### 2.4 Wrong vs Correct

#### Wrong

- Inserting text like “若在当前源仓库维护 workflow 内容时，可直接使用 ...” into a phase command document
- Showing both `docs/workflows/.../commands/shell/...` and `.trellis/scripts/workflow/...` as parallel operator choices inside one command source doc

#### Correct

- Keep the command source doc focused on installed-workflow runtime behavior
- Put maintainer validation or source-repo execution guidance in dedicated maintenance docs
- Keep source-form paths in command docs only when they are meant to be rewritten by `prepare_command_content()`

---

## Related Files

- `docs/workflows/**/commands/*.md` — command source documents governed by this spec
- `docs/workflows/**/commands/workflow_assets.py` — `prepare_command_content()` rewrite logic
- `docs/workflows/自定义工作流制作规范.md` — cross-workflow authoring rules
- `.trellis/spec/scripts/workflow-installer-upgrade-contracts.md` — installer/upgrade code-spec
- `docs/workflows/**/装后隐藏目录与托管边界核对清单.md` — maintainer-facing deployed-state verification guidance
- `docs/workflows/**/CLI原生适配边界矩阵.md` — maintainer-facing CLI boundary guidance
- `docs/workflows/**/目标项目兼容升级方案指导.md` — target-project upgrade analysis guidance
- `.trellis/spec/docs/index.md` → Project Identity — project boundary declaration
