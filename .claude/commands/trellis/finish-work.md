# Finish Work - Pre-Commit Checklist

Before submitting or committing, use this checklist to ensure work completeness.

**Timing**: After code is written and tested, before commit

---

## Checklist

### 1. Code Quality

```bash
# Must pass
pnpm lint
pnpm type-check
pnpm test
```

- [ ] `pnpm lint` passes with 0 errors?
- [ ] `pnpm type-check` passes with no type errors?
- [ ] Tests pass?
- [ ] No `console.log` statements (use logger)?
- [ ] No non-null assertions (the `x!` operator)?
- [ ] No `any` types?

### 1.5. Test Coverage

Check if your change needs new or updated tests (see `.trellis/spec/unit-test/conventions.md`):

- [ ] New pure function → unit test added?
- [ ] Bug fix → regression test added in `test/regression.test.ts`?
- [ ] Changed init/update behavior → integration test added/updated?
- [ ] No logic change (text/data only) → no test needed

### 2. Code-Spec Sync

**Code-Spec Docs**:
- [ ] Does `.trellis/spec/backend/` need updates?
  - New patterns, new modules, new conventions
- [ ] Does `.trellis/spec/frontend/` need updates?
  - New components, new hooks, new patterns
- [ ] Does `.trellis/spec/guides/` need updates?
  - New cross-layer flows, lessons from bugs

**Key Question**: 
> "If I fixed a bug or discovered something non-obvious, should I document it so future me (or others) won't hit the same issue?"

If YES -> Update the relevant code-spec doc.

### 2.5. Code-Spec Hard Block (Infra/Cross-Layer)

If this change touches infra or cross-layer contracts, this is a blocking checklist:

- [ ] Spec content is executable (real signatures/contracts), not principle-only text
- [ ] Includes file path + command/API name + payload field names
- [ ] Includes validation and error matrix
- [ ] Includes Good/Base/Bad cases
- [ ] Includes required tests and assertion points

**Block Rule**:
In pipeline mode, the finish agent will automatically detect and execute spec updates when gaps are found.
If running this checklist manually, ensure spec sync is complete before committing — run `/trellis:update-spec` if needed.

### 3. API Changes

If you modified API endpoints:

- [ ] Input schema updated?
- [ ] Output schema updated?
- [ ] API documentation updated?
- [ ] Client code updated to match?

### 4. Database Changes

If you modified database schema:

- [ ] Migration file created?
- [ ] Schema file updated?
- [ ] Related queries updated?
- [ ] Seed data updated (if applicable)?

### 5. Cross-Layer Verification

If the change spans multiple layers:

- [ ] Data flows correctly through all layers?
- [ ] Error handling works at each boundary?
- [ ] Types are consistent across layers?
- [ ] Loading states handled?

### 6. Manual Testing

- [ ] Feature works in browser/app?
- [ ] Edge cases tested?
- [ ] Error states tested?
- [ ] Works after page refresh?

### 7. trellis-library 校验（如果修改了 trellis-library/ 目录）

**触发条件**: 任何对 `trellis-library/` 目录的修改

```bash
# 1. 运行官方验证脚本（必须通过）
python3 trellis-library/scripts/validation/validate-library-sync.py --strict-warnings

# 2. 运行单元测试（必须通过）
python3 -m unittest trellis-library/tests/test_cli.py

# 3. 验证 CLI 基本功能
python3 trellis-library/cli.py --help
python3 trellis-library/cli.py validate --help
python3 trellis-library/cli.py assemble --help
python3 trellis-library/cli.py sync --help
```

#### 7.1 manifest.yaml 必填字段检查

- [ ] `library` 部分包含: `id`, `title`, `description`, `status`, `owners`
- [ ] `policies` 部分存在且包含关键策略:
  - `require_manifest_registration: true`
  - `require_unique_ids: true`
  - `allow_unregistered_files: false`
  - `deletion_policy: block-if-referenced`
- [ ] `enums` 部分定义所有枚举值
- [ ] `assets` 列表中每个资产包含必填字段:
  - `id`: 唯一标识符 (格式: `type.domain.concern`)
  - `type`: `spec|template|checklist|example|schema|script`
  - `format`: `file|directory`
  - `path`: 相对于库根目录的路径
  - `title`: 人类可读标题
  - `summary`: 简短描述
  - `status`: `draft|active|deprecated|archived`
  - `version`: 语义化版本 (如 `1.0.0`)

#### 7.2 资产路径校验（必须匹配类型）

| 资产类型 | 路径前缀 | 文件格式 |
|----------|----------|----------|
| spec | `specs/` | `.md` 目录或文件 |
| template | `templates/` | `.md` 目录或文件 |
| checklist | `checklists/` | `.md` 目录或文件 |
| example | `examples/` | `.md` 目录或文件 |
| schema | `schemas/` | `.json/.yaml/.yml` |
| script | `scripts/` | `.py/.sh` |

- [ ] 所有 `format: directory` 的资产路径必须指向实际存在的目录
- [ ] 所有 `format: file` 的资产路径必须指向实际存在的文件

#### 7.3 依赖完整性校验

- [ ] `dependencies` 中的每个资产 ID 都必须在 manifest 中存在
- [ ] `optional_dependencies` 中的每个资产 ID 都必须在 manifest 中存在
- [ ] `relations` 中的 `from` 和 `to` 必须引用已注册的资产

#### 7.4 Pack 校验

- [ ] 每个 pack 的 `selection.assets` 列表中的资产 ID 都必须已注册
- [ ] Pack ID 必须唯一且格式为 `pack.<name>`
- [ ] README 中列出的 pack 必须在 manifest 中存在

#### 7.5 注册漂移校验

- [ ] 不存在未在 manifest.yaml 中注册的资产（除非 `allow_unregistered_files: true`）
- [ ] manifest 中注册的资产在文件系统中必须存在

#### 7.6 SPEC 文件内容校验

**目录结构校验**:

每个 spec 目录必须包含以下文件之一：
- `overview.md` (必须有 `# Purpose` 和 `# Applicability`)
- `normative-rules.md` (必须有具体规则)
- `scope-boundary.md` (必须有 `This concern covers...` 和 `It does not...`)
- `verification.md` (必须有 `# Verification` 和检查项)

**overview.md 内容校验**:

- [ ] 必须包含 `# Purpose` 章节
- [ ] 必须包含 `# Applicability` 章节
- [ ] `# Purpose` 必须说明"这是什么规范"和"解决什么问题"
- [ ] `# Applicability` 必须说明"什么时候使用"和"什么时候不使用"

**normative-rules.md 内容校验**:

- [ ] 必须包含具体的规范条目（以 `*` 或 `-` 开头）
- [ ] 规范不能是宽泛的原则，必须是可执行的规则
- [ ] 规范应包含具体的约束词：必须 (must)、禁止 (must not)、应该 (should)、不应该 (should not)
- [ ] 不能包含：
  - 宽泛的陈述如 "Be good" 或 "Do the right thing"
  - 模糊的指导如 "Consider using..." 而不说明在什么情况下
  - 占位符文本如 `(to be filled)` 或 `[placeholder]`

**scope-boundary.md 内容校验**:

- [ ] 必须包含 "This concern covers..." 语句
- [ ] 必须包含 "It does not..." 语句
- [ ] 边界必须具体，不能模糊如 "其他相关事项"

**verification.md 内容校验**:

- [ ] 必须包含 `# Verification` 标题
- [ ] 必须包含具体的验证检查项
- [ ] 检查项必须说明如何验证规范是否被遵守

**内容质量校验**:

- [ ] 不能有过多的 "should consider" 而没有具体指导
- [ ] 不能有自相矛盾的内容
- [ ] 不能有与其他 spec 重复的通用内容（应引用而非重复）
- [ ] 特定技术的 spec（如 Go/Java/Python）必须包含该技术的具体示例或规则
- [ ] 不能全是抽象原则而无可执行的具体指导

#### 7.7 CHECKLIST 文件内容校验

- [ ] 必须包含 `#` 开头的标题
- [ ] 必须包含具体的检查项（以 `*` 或 `-` 开头）
- [ ] 检查项必须描述可验证的行为或状态
- [ ] 不能包含模糊的检查项如 "检查是否正确" 而不说明什么是正确

#### 7.8 TEMPLATE 文件内容校验

- [ ] 必须包含模板变量标记（如 `{{variable}}` 或 `<variable>`）
- [ ] 必须包含使用说明或示例
- [ ] 必须说明输入和输出的格式要求

#### 7.9 pack 组装校验

```bash
# 验证 pack 可正常组装
python3 trellis-library/cli.py assemble --target /tmp/test --pack pack.go-service-foundation --dry-run
```

---

## Quick Check Flow

```bash
# 1. Code checks
pnpm lint && pnpm type-check

# 2. View changes
git status
git diff --name-only

# 3. Based on changed files, check relevant items above
```

---

## Common Oversights

| Oversight | Consequence | Check |
|-----------|-------------|-------|
| Code-spec docs not updated | Others don't know the change | Check .trellis/spec/ |
| Spec text is abstract only | Easy regressions in infra/cross-layer changes | Require signature/contract/matrix/cases/tests |
| Migration not created | Schema out of sync | Check db/migrations/ |
| Types not synced | Runtime errors | Check shared types |
| Tests not updated | False confidence | Run full test suite |
| Console.log left in | Noisy production logs | Search for console.log |
| trellis-library: 资产未注册 | 验证脚本失败 | 运行 validate-library-sync.py |
| trellis-library: 依赖引用不存在 | 组装脚本失败 | 检查 dependencies/relations |
| trellis-library: Pack 引用的资产不存在 | 无法组装 pack | 运行 assemble --dry-run |
| trellis-library: 路径与类型不匹配 | 验证脚本报错 | 检查 path 前缀 |
| trellis-library: spec 内容宽泛空洞 | AI 产出不符合预期 | 检查 normative-rules 是否有具体规则 |
| trellis-library: overview 缺少适用性说明 | 不知何时使用 | 检查 Applicability 章节 |
| trellis-library: scope-boundary 模糊 | 规范边界不清 | 检查 covers/does not 表述 |
| trellis-library: 缺少 verification 说明 | 无法验证合规性 | 检查验证检查项 |

---

## Relationship to Other Commands

```
Development Flow:
  Write code -> Test -> /trellis:finish-work -> git commit -> /trellis:record-session
                          |                              |
                   Ensure completeness              Record progress
                   
Debug Flow:
  Hit bug -> Fix -> /trellis:break-loop -> Knowledge capture
                       |
                  Deep analysis
```

- `/trellis:finish-work` - Check work completeness (this command)
- `/trellis:record-session` - Record session and commits
- `/trellis:break-loop` - Deep analysis after debugging

---

## Core Principle

> **Delivery includes not just code, but also documentation, verification, and knowledge capture.**

Complete work = Code + Docs + Tests + Verification
