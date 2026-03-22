---
name: test-first
description: 任务拆好了？先写测试 — 实现前生成测试套件作为客观验收门禁。触发词：先写测试、TDD、测试先行、测试驱动
---

# /trellis:test-first — AI 测试驱动开发

> **Workflow Position**: §4.3 → 前: `/trellis:plan` → 后: `/trellis:start`
> **Cross-CLI**: ✅ Claude Code · ✅ Cursor (命令名: test-first) · ⚠️ OpenCode · ⚠️ Codex/Gemini

---

## When to Use (自然触发)

- "先写测试吧"
- "用 TDD 方式开发"
- "测试先行"
- "先把验收标准写成测试用例"

---

## 流程

### Step 1: TDD 循环

**Skill**: `test-driven-development` — Red → Green → Refactor

### Step 2: 测试用例生成

- 单元测试 → `tests/<module>.test.ts`
- 验收标准模板 → 功能/边界/异常
- 评估集 → `tests/evals/EVAL-<id>.yaml`（≥50 条，对抗用例 ≥15%）

### Step 3: 人工审核

- [ ] 核心路径覆盖
- [ ] 断言具体可验证
- [ ] 每个 Acceptance Criterion 有对应测试

### Step 4: 进入门禁

```bash
pnpm test
```

测试不通过 → 不允许提交代码

---

## 输出

```
$TASK_DIR/tests/
├── <module>.test.ts
└── evals/EVAL-<id>.yaml
```

## 下一步推荐

**当前状态**: 测试套件已生成，门禁已就绪。

根据你的意图：

| 你的意图 | 推荐命令 | 说明 |
|---------|---------|------|
| 开始实现代码 | `/trellis:start` | **默认推荐**。测试门禁就绪，进入实施 |
| 测试不够完善 | `/trellis:test-first` | 补充测试用例 |
| 测试策略需要调整 | `/trellis:plan` | 回退到任务拆解调整验收标准 |
| 需要并行实现多个任务 | Git worktree 或 `/trellis:parallel` | 如当前项目已安装 `/trellis:parallel` 则优先使用，否则手工用 worktree 隔离 |
| 不确定下一步 | `/trellis:start` | 用 Phase Router 自动检测 |
