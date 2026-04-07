---
name: finish-work
description: "Pre-commit checklist for this meta-project. Focuses on trellis-library validation, asset integrity, code-spec sync, and cross-layer executable-spec checks before human commit."
---

# Finish Work - Pre-Commit Checklist

Before submitting or committing, use this checklist to ensure work completeness.

**Timing**: After code is written and tested, before commit
**Project**: ai-coding-toolkit（元项目，非应用）

---

## Checklist

### 1. trellis-library 校验（修改 trellis-library/ 目录时必须通过）

```bash
# 1. 运行官方验证脚本（必须通过）
python3 trellis-library/cli.py validate --strict-warnings

# 2. 运行单元测试（必须通过）
python3 -m unittest trellis-library/tests/test_cli.py

# 3. 验证 CLI 基本功能
python3 trellis-library/cli.py --help
python3 trellis-library/cli.py validate --help
python3 trellis-library/cli.py assemble --help
python3 trellis-library/cli.py sync --help
```

#### 1.1 manifest.yaml 必填字段检查

- [ ] `library` 部分包含: `id`, `title`, `description`, `status`, `owners`
- [ ] `policies` 部分存在且包含关键策略
- [ ] `enums` 部分定义所有枚举值
- [ ] `assets` 列表中每个资产包含必填字段: `id`, `type`, `format`, `path`, `title`, `summary`, `status`, `version`

#### 1.2 资产路径校验（必须匹配类型）

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

#### 1.3 依赖完整性校验

- [ ] `dependencies` 中的每个资产 ID 都必须在 manifest 中存在
- [ ] `optional_dependencies` 中的每个资产 ID 都必须在 manifest 中存在
- [ ] `relations` 中的 `from` 和 `to` 必须引用已注册的资产

#### 1.4 SPEC 文件内容校验

**目录结构校验**:
- [ ] spec 目录必须有 `overview.md` (含 `# Purpose` 和 `# Applicability`) 或 `normative-rules.md` 或 `scope-boundary.md` 或 `verification.md`

**overview.md 内容校验**:
- [ ] 必须包含 `# Purpose` 章节
- [ ] 必须包含 `# Applicability` 章节

**normative-rules.md 内容校验**:
- [ ] 必须包含具体的规范条目（不能是宽泛原则）
- [ ] 不能包含占位符文本如 `(to be filled)`

**scope-boundary.md 内容校验**:
- [ ] 必须包含 "This concern covers..." 语句
- [ ] 必须包含 "It does not..." 语句

**verification.md 内容校验**:
- [ ] 必须包含 `# Verification` 标题
- [ ] 必须包含具体的验证检查项

#### 1.5 CHECKLIST 文件内容校验

- [ ] 必须包含具体检查项（以 `*` 或 `-` 开头）
- [ ] 检查项必须描述可验证的行为或状态

#### 1.6 TEMPLATE 文件内容校验

- [ ] 必须包含模板变量标记（如 `{{variable}}`）
- [ ] 必须包含使用说明或示例

---

### 2. Code-Spec Sync

**Code-Spec Docs**:
- [ ] `.trellis/spec/scripts/` 需要更新?
- [ ] `.trellis/spec/agents/` 需要更新?
- [ ] `.trellis/spec/commands/` 需要更新?
- [ ] `.trellis/spec/guides/` 需要更新?

**Key Question**: 
> "如果我修复了一个 bug 或发现了显而易见的问题，是否应该记录下来?"

如果是 → 更新相关的 code-spec doc。

### 2.1 Code-Spec Hard Block (Infra/Cross-Layer)

如果变更涉及基础架构或跨层合约:

- [ ] Spec 内容可执行（真实签名/合约）
- [ ] 包含文件路径 + 命令/API 名称
- [ ] 包含验证矩阵和错误矩阵
- [ ] 包含 Good/Base/Bad 案例
- [ ] 包含必需的测试和断言点

**阻塞规则**:
如果相关 spec 仍然是抽象的，不要完成。先运行 `$update-spec`。

---

## Quick Check Flow

```bash
# 1. 验证 trellis-library
python3 trellis-library/cli.py validate --strict-warnings
python3 -m unittest trellis-library/tests/test_cli.py

# 2. 查看变更
git status
git diff --name-only
```

---

## Common Oversights

| Oversight | Consequence | Check |
|-----------|-------------|-------|
| trellis-library 校验未运行 | 资产校验或组装失败 | 运行 `validate --strict-warnings` 和 CLI 基本帮助命令 |
| manifest / relations 引用失配 | 资产注册与依赖漂移 | 检查 `manifest.yaml`、`dependencies`、`relations` |
| 相关 code-spec 未更新 | 后续维护者不知道规则已变 | 检查 `.trellis/spec/scripts/`、`.trellis/spec/agents/`、`.trellis/spec/commands/`、`.trellis/spec/guides/` |
| spec 仍停留在抽象原则 | 基础设施或跨层改动容易回归 | 补齐真实签名/字段/矩阵/案例/断言点 |

---

## Relationship to Other Commands

```
Development Flow:
  Write code -> Test -> $finish-work -> git commit -> $record-session
                          |                              |
                   Ensure completeness              Record progress
                   
Debug Flow:
  Hit bug -> Fix -> $break-loop -> Knowledge capture
                       |
                  Deep analysis
```

- `$finish-work` - Check work completeness (this skill)
- `$record-session` - Record session and commits
- `$break-loop` - Deep analysis after debugging

---

## Core Principle

> **交付不仅包括代码，还包括文档、验证和知识捕获。**

Complete work = Code + Docs + Tests + Verification
