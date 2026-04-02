---
name: test-first
description: 任务拆好了？先写测试 — 实现前生成测试套件作为客观验收门禁。触发词：先写测试、TDD、测试先行、测试驱动、测试用例、验收测试
---

# /trellis:test-first — AI 测试驱动开发

> **Workflow Position**: §4.3 → 前: `/trellis:plan` → 后: `/trellis:start`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:test-first`） · ✅ OpenCode（TUI: `/trellis:test-first`；CLI: `trellis/test-first`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:test-first` 命令；见 `codex/README.md`）

---

## When to Use (自然触发)

- "先写测试吧"
- "用 TDD 方式开发"
- "测试先行"
- "先把验收标准写成测试用例"

> 若 `PRD` 已冻结后命中需求讨论，按 `§2.5` 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入需求变更管理，不直接改测试套件吸收新范围。

---

## 流程

进入 `/trellis:test-first` 前，必须已经满足这一前置：

- 目标项目技术架构已确认
- `test-first` 阶段所需的具体测试/验证命令，已在技术架构确认后由用户明确
- 测试文件目录、命名约定，以及是否需要评估集 / fixture / contract test 一类额外产物，已按项目实际情况确认

若以上内容仍未明确，先回到 `design` 阶段补齐，不在本阶段猜默认值。

### Step 1: TDD 循环

**调用 Skill**：`test-driven-development` — 按 Red → Green → Refactor 循环生成测试。降级：手动按“先写失败测试 → 最小实现通过 → 重构”流程执行。

**MCP 能力路由**

| 场景 | 调用能力 | 触发条件 | 说明 |
|------|---------|---------|------|
| 测试框架 API 查询 | `Context7` | 当需要查询测试框架官方 API 时 | 获取最新测试框架文档，确保 API 用法正确。无法获取时标记 `[Evidence Gap]`，只引用项目内既有模式 |
| 复杂测试逻辑推理 | `sequential-thinking` | 当测试场景涉及 ≥3 个边界条件组合或状态转换链 >3 步时 | 复杂测试场景 |

### Step 2: 测试用例生成

- 按项目已确认的语言、框架、目录和命名约定生成测试文件
  - 例如：`tests/<module>.test.ts`、`tests/test_<module>.py`、`<pkg>/<module>_test.go`
- 验收标准模板 → 功能/边界/异常
- 若项目确实需要评估集 / fixture / contract test，再按已确认格式生成
  - 不默认要求 `tests/evals/EVAL-<id>.yaml`
  - 不默认要求统一 YAML 格式、固定条数或固定对抗样本比例

### Step 3: 人工审核

- [ ] 核心路径覆盖
- [ ] 断言具体可验证
- [ ] 每个 Acceptance Criterion 有对应测试

### Step 4: 进入门禁

```bash
<user-confirmed test/verification command>
```

测试不通过 → 不允许提交代码

---

## 输出

```
$TASK_DIR/tests/ 或项目既有测试目录
├── <project-specific test files>
└── <optional evals / fixtures / contracts>
```

## 下一步推荐

**当前状态**: 测试套件已生成，门禁已就绪。

> 本节定义的是阶段完成后的推荐输出口径，用于帮助当前 CLI 或协作者说明下一步；它不是框架层自动跳转保证。

根据你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 开始实现代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | **默认推荐**。测试门禁就绪，进入实施 |
| 测试不够完善 | `/trellis:test-first` | 继续补测试，或显式触发 `test-first` skill | 补充测试用例 |
| 冻结后出现新增 / 修改 / 删除需求 | `§2.5 需求变更管理` | 同上 | 先完成评估与基线更新，再回到受影响的最早阶段重建测试门禁 |
| 仅测试策略需要调整，需求基线不变 | `/trellis:plan` | 回退任务拆解，或显式触发 `plan` skill | 回退到任务拆解调整验收标准或测试拆分方式 |
| 需要并行实现多个任务 | Git worktree 或 `/trellis:parallel` | Git worktree，或显式触发 `parallel` skill | 如当前项目已安装 `/trellis:parallel` 则优先使用，否则手工用 worktree 隔离 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
