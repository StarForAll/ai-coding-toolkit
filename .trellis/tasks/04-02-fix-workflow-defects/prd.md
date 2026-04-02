# 修复工作流脚本3个真实缺陷

## Goal

修复 `docs/workflows/新项目开发工作流/commands/shell/` 下的3个确认缺陷，确保工作流脚本在实际开发使用中行为正确。

## 缺陷清单

### 缺陷 1（高）：plan-validate.py — 等待原因验证逻辑反转

**位置**：`commands/shell/plan-validate.py:202-203`

**现状代码**：
```python
if status != "等待中" and not wait_reason.strip():
    start_wait_ok = False
```

**问题**：非等待状态（"可开始"、"进行中"、"已完成"）的任务，如果等待原因为空，就会被判定为验证失败。这在语义上是反的——只有"等待中"的任务才需要填写等待原因，非等待任务没有等待原因是正常的。

**实际影响**：用户按规范创建 `task_plan.md`，把"可开始"任务的等待原因留空（合理行为），`plan-validate.py` 报错，导致验证无法通过。

**修复方向**：删除 202-203 行（该逻辑无意义），或改为检查非等待任务不应有等待原因（互斥校验）。

---

### 缺陷 2（中）：plan-validate.py — 占位符标记子字符串匹配导致误判

**位置**：`commands/shell/plan-validate.py:38, 64`

**现状代码**：
```python
PLACEHOLDER_MARKERS = ("[", "待补充", "TBD")

def has_meaningful_text(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    return not any(marker in stripped for marker in PLACEHOLDER_MARKERS)
```

**问题**：`"["` 作为占位符标记使用 `in` 子字符串匹配，导致任何包含 `[` 的合法内容都被误判为占位符。在任务执行矩阵中，开始条件写成 `[T1] 完成后开始`（引用任务 ID）是自然用法，但会被 `has_meaningful_text` 判定为无意义文本，触发验证失败。

**实际影响**：用户在开始条件、等待原因、冲突说明等字段中使用方括号引用（`[T1]`、`[Phase 2]`），验证误报失败。

**修复方向**：将 `"["` 改为更精确的占位符模式匹配，例如检查整个值是否匹配 `[xxx]` 格式（全值被方括号包裹），而非包含 `[` 即判定。或者从 PLACEHOLDER_MARKERS 中移除 `"["`，仅保留 `"待补充"` 和 `"TBD"`。

---

### 缺陷 3（中）：self-review-check.py — 硬编码 pnpm 包管理器

**位置**：`commands/shell/self-review-check.py:39, 46, 50`

**现状代码**：
```python
run_check("pnpm test --reporter=dot 2>/dev/null", "测试状态")
run_check("pnpm lint 2>/dev/null", "Lint 状态")
run_check("pnpm type-check 2>/dev/null", "Type Check 状态")
```

**问题**：自审检查脚本硬编码 `pnpm` 作为包管理器。该工作流系统设计上支持多 CLI、多项目部署，但自审脚本假设所有项目都用 pnpm。对于使用 npm/yarn/bun 的项目，这些检查命令会失败或产生误导性结果。

**实际影响**：非 pnpm 项目执行自审时，测试/lint/type-check 三项检查全部失败或报"命令不存在"，用户无法获得有效的自审反馈。

**修复方向**：检测项目实际使用的包管理器（通过 lockfile 类型判断：`pnpm-lock.yaml` → pnpm，`yarn.lock` → yarn，`package-lock.json` → npm，`bun.lockb` → bun），然后使用对应的命令。

## 修复范围

### 涉及文件

| 文件 | 修改内容 |
|------|----------|
| `docs/workflows/新项目开发工作流/commands/shell/plan-validate.py` | 修复缺陷1、缺陷2 |
| `docs/workflows/新项目开发工作流/commands/shell/self-review-check.py` | 修复缺陷3 |

### 不涉及文件

- 命令文档（`.md` 文件）中的 `<WORKFLOW_DIR>` 占位符 —— 部署时由 `install-workflow.py` 自动替换
- `feasibility-check.py` 的反引号 regex —— 匹配模板预期格式，非缺陷
- `record-session-helper.py` 的 `raise SystemExit` —— 合法 Python 退出模式
- §3.7 跨文档循环引用 —— 文档组织改进，不影响脚本执行

## Acceptance Criteria

- [ ] plan-validate.py: 删除或修复 202-203 行的逻辑反转问题
- [ ] plan-validate.py: 修复占位符标记误判问题（方括号合法使用不被误判）
- [ ] self-review-check.py: 自动检测包管理器（pnpm/yarn/npm/bun）并执行对应命令
- [ ] 所有修复保持向后兼容，不破坏现有功能
- [ ] 修复后脚本在 Python 3.8+ 环境下可正常运行

## Definition of Done

- 修复代码已提交
- 修复后的脚本通过基本功能测试
- 相关文档无需更新（纯缺陷修复，无行为变更需说明）

## Out of Scope

- 新增功能或增强
- 重构或代码风格优化
- 文档内容改进
- 其他未确认的"潜在问题"

## Technical Notes

- 包管理器检测优先级：`pnpm-lock.yaml` > `yarn.lock` > `package-lock.json` > `bun.lockb`
- 如果未检测到 lockfile，默认使用 `npm`（最通用）
- 修复应保持脚本无外部依赖（Python stdlib only）
