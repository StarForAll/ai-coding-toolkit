# 修正 workflow.md 错漏

## Goal

修正 `.trellis/workflow.md` 中已确认的 8 项错漏，使文档内部一致、与实际机制对齐、覆盖完整。

## What I already know

* workflow.md 共 531 行，是 trellis workflow 的核心操作文档
* 文档被 session-start.py hook 注入每次会话，Phase Index 和 [workflow-state:STATUS] 标签块是运行时关键内容
* 已通过深度分析确认 8 项错漏，并排除了 4 项误判

## Requirements

### P1 — 必须修正

1. **Best Practices "AI should not commit" 矛盾**（L392）
   - 当前：`Don't execute git commit - AI should not commit code`
   - 实际：Phase Index `[workflow-state:in_progress]` 明确写 `the main agent drives the commit`
   - 修正：Best Practices 应改为 "AI 主会话驱动 commit，sub-agent 禁止 commit" 的一致表述

2. **Development Process 线性流程与 Phase Index 脱节**（L210-231）
   - 当前：5 步线性流程（Create → Write → Test → Commit → Close-out）
   - 实际：Phase Index 定义三阶段状态机（Plan → Execute → Finish）+ sub-agent 分发
   - 修正：重写 Development Process 为 Phase Index 的摘要引用，不重复定义流程

3. **spec/ 树遗漏 5 个用户面向子目录**
   - 遗漏：`universal-domains/`、`checklists/`、`templates/`、`examples/`、`platforms/`
   - 修正：补充到 File System 树（L129-153）和 File Descriptions spec 段落（L304-333）

### P2 — 应当修正

4. **Phase 编号跳跃**
   - Plan：1.1 → 1.3 → 1.4 → 修正为 1.1, 1.2, 1.3
   - Finish：3.1 → 3.4 → 修正为 3.1, 3.2

5. **agents/ 注释 "OpenCode agent definitions"**（L322, L142）
   - 修正为 `# Agent source asset definitions (multi-tool deployment)`

6. **config.yaml 未在 File System 树列出**
   - 在树中 `.developer` 和 `.runtime/` 之间补充 `config.yaml  # Project-level configuration`

7. **ToC 缺少 Phase Index**
   - 补充 `8. [Phase Index](#phase-index)`

### P3 — 建议修正

8. **Quick Start 与 Session Start 内容重复**
   - Session Start Process 标注为 "See Quick Start steps above" + 补充差异部分

## Acceptance Criteria

- [ ] Best Practices 的 commit 规则与 Phase Index 一致，无矛盾
- [ ] Development Process 引用 Phase Index 而非定义独立线性流程
- [ ] spec/ 树包含全部 12 个子目录
- [ ] Phase 编号连续（1.1-1.3, 2.1-2.3, 3.1-3.2）
- [ ] agents/ 注释反映跨平台架构
- [ ] config.yaml 出现在 File System 树
- [ ] ToC 包含 Phase Index
- [ ] Session Start 与 Quick Start 重复减少
- [ ] 修改后 workflow.md 通过 `inject-workflow-state.py` 和 `workflow_phase.py` 解析验证

## Definition of Done

- 上述 8 项全部修正
- 无新矛盾引入
- Phase Index 标签块 `[workflow-state:...]` 格式不变（hook 依赖此格式）
- `workflow_phase.py` 能正确提取修正后的 Phase Index

## Out of Scope

- hook/JSONL/multi-platform 机制的详细说明（非本文档职责）
- python3 路径规范化（非本文档职责）
- scripts/ 树补全（省略 sync/validation 脚本合理）
- Summary 段落位置调整（非错误）
- [workflow-state:my-status] 用途说明（待后续任务处理）

### Phase 编号重映射

| 旧编号 | 内容 | 新编号 |
|--------|------|--------|
| 1.1 | Brainstorm / PRD | 1.1（不变）|
| 1.3 | Curate JSONL Context | **1.2** |
| 1.4 | Enter Execute Phase | **1.3** |
| 2.1 | Implement | 2.1（不变）|
| 2.2 | Check | 2.2（不变）|
| 2.3 | Update Spec | 2.3（不变）|
| 3.1 | Commit Gate | 3.1（不变）|
| 3.4 | Close-Out | **3.2** |

注意：`change-workflow.md` 引用 Phase 3.5（finish-work archive），但 workflow.md 当前无 3.5 步骤。3.4 Close-Out 本身包含 archive + record session。3.5 在 meta references 中是对 `/finish-work` 的语义引用，修正后应为 3.2（Close-Out）。

## Technical Notes

- 文件：`.trellis/workflow.md`（531 行）
- 关键约束：`[workflow-state:STATUS]...[/workflow-state:STATUS]` 标签格式被 `inject-workflow-state.py` 和 `workflow_phase.py` 解析，不可改变此格式
- `workflow_phase.py` 通过标题层级提取 Phase Index 步骤，编号连续性不影响解析
- Phase 编号重编后，其他文件中引用 "Phase 1.3" 的地方需同步检查（如 session-start hook 输出、spec 文件引用）
