# workflow-audit: embedded workflow issue validation

## Goal

基于 `docs/workflows/新项目开发工作流/` 的 source assets，以及 `/tmp/trellis-0.5.17-2` 这个已执行 `trellis init` + workflow 嵌入的目标项目，判断候选问题哪些是真实 defect、哪些是 false alarm，并在得到用户确认后只修改 `docs/workflows/新项目开发工作流/` 完成修复。

## Scope

- 审计目标固定为 `docs/workflows/新项目开发工作流/`
- 证据层包括：
  - source repo 下的 workflow docs / scripts / tests
  - `/tmp/trellis-0.5.17-2` 的 installed target state
  - 只读 runtime command output
- 本轮先完成真实性判断、影响面分析、修正方案
- 未获用户确认前不修改 workflow source

## Candidate Issues

1. 新 leaf task / project-audit owner 的阶段初始化指引是否不可执行
2. Codex 启动 quick reference 是否仍路由到旧 `trellis-brainstorm`
3. `plan-validate.py` 是否漏拦截“声明 PROJECT-AUDIT 但未落结构化 task 行”
4. Codex 侧 agent/subagent 禁用是否只有软约束，没有结构性硬禁用
5. `delivery` 后的 `finish-work` 入口命名是否不一致
6. 安装完整性 / 升级检查是否覆盖不到关键语义漂移
7. 是否真的缺少状态机与门禁脚本测试

## Constraints

- 只允许修改 `docs/workflows/新项目开发工作流/`
- 可以创建和保留当前 task 文件
- 不能把 repo 其他目录作为修复目标
- 若问题属于 Trellis 原生而非 workflow 自身，需要在 workflow 合适位置以 patch/contract 方式修正

## Acceptance

- 每个候选问题都有明确结论：confirmed / false alarm / evidence gap
- confirmed 问题都有 source repo + installed target + runtime 证据
- 给出最小且成组的一致性修复方案
- 等待用户确认后再进入实际修改
