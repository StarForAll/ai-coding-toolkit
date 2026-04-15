---
name: test-first
description: 需要显式先测或补验证证据？进入手动测试驱动模式。触发词：先写测试、TDD、测试先行、测试驱动、测试用例、验收测试
---

# /trellis:test-first — 手动测试驱动入口

> **Workflow Position**: §4.3 → 默认前: `/trellis:start` 前的显式手动入口 → 后: `/trellis:start`
> **Cross-CLI**: ✅ Claude Code（项目命令：`/trellis:test-first`） · ✅ OpenCode（TUI: `/trellis:test-first`；CLI: `trellis/test-first`；见 `opencode/README.md`） · ⚠️ Codex（通过 AGENTS.md NL 路由触发，不提供项目级 `/trellis:test-first` 命令；见 `codex/README.md`）

> **Strong Gate**: 本阶段受 [阶段状态机与强门禁协议](../阶段状态机与强门禁协议.md) 约束。测试先行完成后，必须等待用户确认，不能自动推进到实现或 check。

---

## 核心定位

`/trellis:test-first` **不再是默认主链阶段**。

默认主链中：

- 进入某个具体 task 实现前，由 `/trellis:start` 自动执行 `before-dev`
- task 级测试门禁自动补到：

```text
$TASK_DIR/before-dev.md
```

只有在以下场景，才需要显式进入 `/trellis:test-first`：

- 用户明确要求 TDD / 先写测试
- 需要先把某个 task 的验收标准转成测试
- `before-dev.md` 已给出 task 门禁，但验证证据仍不足
- `check` 明确指出“先补测试再回来”

## When to Use (自然触发)

- "先写测试吧"
- "用 TDD 方式开发"
- "测试先行"
- "先把验收标准写成测试用例"
- "这个 task 先把验证证据补齐"

> 若 `PRD` 已冻结后命中需求讨论，按 [需求变更管理执行卡](../需求变更管理执行卡.md) 分流：纯澄清留在当前阶段；新增 / 修改 / 删除进入变更管理，不直接改测试套件吸收新范围。

---

## 前置条件

进入 `/trellis:test-first` 前，至少应满足：

- 当前要处理的具体 task 已明确
- 项目级全局测试基线已在上游阶段定义
- 当前 task 的 `before-dev.md` 已存在，或能明确当前 task 的实现边界与门禁

若以上内容仍未明确，先回到：

- `/trellis:start`：自动执行 before-dev 并补齐 task 级门禁
- 或 `/trellis:design`：补齐项目级全局测试基线

推荐进入顺序：

1. 先通过 `/trellis:start` 进入一次主链，让当前 task 自动生成 `before-dev.md`
2. 如果仍需显式先测，再进入 `/trellis:test-first` 补测试或补验证证据

边界说明：

- 当前 workflow 里，`before-dev.md` 由 `/trellis:start` 主链自动 before-dev 步骤保证生成
- 手动单独调用 `/trellis:before-dev` 仍按 Trellis 基线语义理解为“读规范 / 注入项目知识”，不默认承诺一定会单独生成 `before-dev.md`

## 流程

### Step 1: 读取当前 task 的门禁快照

至少读取：

- `$TASK_DIR/prd.md`
- `$TASK_DIR/before-dev.md`
- 当前项目既有测试目录与测试约定

优先把 `before-dev.md` 中的当前 task 门禁转成可执行测试，而不是重新发明另一套标准。

### Step 2: TDD / 验证证据补充

**调用 Skill**：`test-driven-development`

可做的事：

- 先写失败测试
- 把验收标准转成测试用例
- 为当前 task 补边界/异常/回归测试
- 在无法自动化时，补最小手工验证步骤与证据口径

### Step 3: 同步门禁状态

补完测试后，应更新当前 task 的门禁结论：

- 若测试门禁已齐：在 `before-dev.md` 中同步标记当前验证要求已具备执行条件
- 若仍不足：明确缺口，不要假装可以直接实现

### Step 4: 回到实现主链

测试就绪后，回到 `/trellis:start` 进入实现。

---

## 输出

```text
$TASK_DIR/
├── before-dev.md                        # 当前 task 门禁快照（同步当前测试门禁状态）
└── <project-specific test files>        # 当前 task 对应测试产物
```

## 下一步推荐

**当前状态**: 当前 task 的测试证据已显式补充或已发现门禁缺口；在用户明确确认前，仍停留在 test-first 阶段。

根据你的意图：

| 你的意图 | Claude / OpenCode 推荐入口 | Codex 推荐入口 | 说明 |
|---------|---------------------------|----------------|------|
| 开始实现代码 | `/trellis:start` | 直接进入实施，或显式触发 `start` skill | **默认推荐**。仅在用户明确确认后才允许回到主链进入实现 |
| 继续补测试 | `/trellis:test-first` | 继续补测试，或显式触发 `test-first` skill | 测试证据仍不足 |
| 发现任务边界不对，需要重拆 | `/trellis:plan` | 回退任务拆解，或显式触发 `plan` skill | 重新调整 task 图与门禁摘要 |
| 冻结后出现新增 / 修改 / 删除需求 | [需求变更管理执行卡](../../需求变更管理执行卡.md) | 同上 | 先完成评估与基线更新，再回到受影响的最早阶段 |
| 不确定下一步 | `/trellis:start` | 描述当前意图，或显式触发 `start` skill | 用 Phase Router / skill 路由做阶段检测 |
