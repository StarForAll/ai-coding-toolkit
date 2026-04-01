---
name: test-first
description: 任务拆好了？先写测试 — 实现前生成测试套件作为客观验收门禁。触发词：先写测试、TDD、测试先行、测试驱动
---

# /trellis:test-first — AI 测试驱动开发

> **Workflow Position**: §4.3 → 前: `/trellis:plan` → 后: `/trellis:start`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:test-first`） · ✅ Cursor（命令名: test-first） · ✅ OpenCode（TUI: `/trellis:test-first`；CLI: `trellis/test-first`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:test-first` 命令；见 `codex/README.md`） · ⚠️ Gemini（兼容层；见 `gemini/README.md`）

---

## When to Use (自然触发)

- "先写测试吧"
- "用 TDD 方式开发"
- "测试先行"
- "先把验收标准写成测试用例"

> 若 `PRD` 已冻结后命中需求讨论，按 `§2.5` 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入需求变更管理，不直接改测试套件吸收新范围。

---

## 流程

### Step 1: TDD 循环

**调用 Skill**：使用 Skill 工具执行 `test-driven-development`，按 Red → Green → Refactor 循环生成测试。若该 skill 不可用，手动按"先写失败测试 → 最小实现通过 → 重构"流程执行，至少先写手工验证步骤与证据口径。

**MCP 能力路由**

| 场景 | 调用能力 | 调用级别 | 说明 |
|------|---------|---------|------|
| 测试框架 API 查询 | `Context7` | 默认 | 获取最新测试框架文档，确保 API 用法正确。无法获取时标记 `[Evidence Gap]`，只引用项目内既有模式 |
| 复杂测试逻辑推理 | `sequential-thinking` | 按需 | 当测试场景涉及 ≥3 个边界条件组合或状态转换链 >3 步时触发 |

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

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 开始实现代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | **默认推荐**。测试门禁就绪，进入实施 |
| 测试不够完善 | `/trellis:test-first` | 继续补测试，或显式触发 `test-first` skill | 补充测试用例 |
| 冻结后出现新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 同上 | 先完成评估与基线更新，再回到受影响的最早阶段重建测试门禁 |
| 仅测试策略需要调整，需求基线不变 | `/trellis:plan` | 回退任务拆解，或显式触发 `plan` skill | 回退到任务拆解调整验收标准或测试拆分方式 |
| 需要并行实现多个任务 | Git worktree 或 `/trellis:parallel` | Git worktree，或显式触发 `parallel` skill | 如当前项目已安装 `/trellis:parallel` 则优先使用，否则手工用 worktree 隔离 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由自动检测 |
