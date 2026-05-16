# 补齐 Context7 spec 复核与 plan 粒度判断合同

## Goal

补齐 `docs/workflows/新项目开发工作流/` 在 design → plan 承接链上的两个流程合同缺口：
1. 在技术架构确认后、导入目标项目 `.trellis/spec/` 之后，强制执行一次基于 `Context7` 的 spec 错漏复核，并在 `plan` 前置条件中明确承接该门禁。
2. 将 `plan` 阶段“是否还应继续细分任务、以达到合适任务粒度”的判断写成固定结构，同时保留必要的人工判断空间；`plan-validate.py` 只校验结构存在与非占位，不机械裁决拆分是否正确。

## What I already know

- 当前 `design` 文档把技术架构确认后的工程化联动定义为：导入 spec、分析完善 `.trellis/spec/`、明确自动化检查矩阵、适配 `finish-work`/close-out 等。
- 当前 `plan` 文档要求进入前已完成 spec 导入与分析完善，但没有明确“Context7 复核已有 spec”这一步，也没有明确复核的通过/阻断规则。
- 当前 `brainstorm` / `plan` / `工作流总纲` 已经有“继续拆分”“超出单上下文预算”等原则，但用户已明确不要再以“单上下文”为主判据，而应改为“当前事项是否还应继续细分、以达到合适任务粒度”。
- 用户已经确认以下合同方向：
  - `Context7` 复核发生在对应目标项目中；
  - 检查对象是“所有与已确认技术架构直接相关的全部 spec”；
  - `design` 阶段必须明确触发该操作；
  - `plan` 前置条件需要补承接说明；
  - `Context7` 复核通过/阻断规则按此前建议执行；
  - `plan` 中任务粒度判断写成固定结构，但避免过度程序化，保留人工判断空间；
  - `plan-validate.py` 只检查结构存在、字段非空、不是占位内容。

## Assumptions (temporary)

- 本次修改应同步至少以下层面：`design.md`、`plan.md`、`工作流总纲.md`、`plan-validate.py`。
- 如果命令文档或主定义发生行为变化，需要同步相关测试与可能引用该规则的 companion 文档。
- 当前没有必要引入运行时 `/tmp` 验证；本轮属于静态流程合同收敛。

## Open Questions

- 无阻塞性未决问题。若在编辑过程中发现规则传播面超出当前预期，再在任务内补充。

## Requirements

- 在 `design` 的技术架构确认后工程化联动步骤中，新增强制 `Context7` spec 复核步骤。
- 明确 `Context7` 复核边界：
  - 检查目标项目中与已确认技术架构直接相关的全部 spec；
  - 能被第三方官方文档约束的 spec 必须经过 `Context7`；
  - 纯内部流程/团队约定/项目私有规范不强行要求 `Context7`，但仍要做人类可复核的本地分析。
- 明确 `Context7` 复核维度至少包括：
  - API / 配置过时
  - 能力假设错误
  - 缺少必要约束
  - 遗漏关键边界或失败路径
  - 与官方文档冲突
- 明确 `Context7` 不可用时的规则：
  - 对直接相关的第三方 spec，标记 `[Evidence Gap]` 并阻断进入 `plan`
- 在 `plan` 前置条件中新增该门禁承接说明，并避免重写主定义。
- 将 `plan` 阶段的任务拆分判断收敛为“是否还应继续细分以达到合适任务粒度”，并写成固定结构。
- 固定结构应保留人工判断空间，不使用机械评分表。
- `plan-validate.py` 新增对该固定结构的存在性/非占位校验，但不判断拆分结论本身是否正确。
- 同步更新受影响测试，避免文档与校验脚本漂移。

## Acceptance Criteria

- [ ] `design.md` 明确要求在技术架构确认后的工程化联动中执行 `Context7` spec 复核，且写明边界与阻断规则。
- [ ] `plan.md` 前置条件明确承接该门禁，并新增任务粒度判断固定结构说明。
- [ ] `工作流总纲.md` 与命令文档保持一致，不出现主定义/承接摘要冲突。
- [ ] `plan-validate.py` 校验新增的任务粒度结构存在且非占位，但不机械裁决拆分对错。
- [ ] 相关测试或示例同步更新，能够覆盖新合同。

## Definition of Done

- 文档主定义、命令文档、校验脚本、测试保持一致
- 相关验证命令已执行并如实记录结果
- 不引入新的行为漂移或重复定义

## Out of Scope

- `/tmp` 运行时安装链验证
- workflow 其他无关阶段的大规模重写
- 新增与本次合同无关的优化项

## Technical Notes

- 重点影响面：
  - `docs/workflows/新项目开发工作流/commands/design.md`
  - `docs/workflows/新项目开发工作流/commands/plan.md`
  - `docs/workflows/新项目开发工作流/工作流总纲.md`
  - `docs/workflows/新项目开发工作流/commands/shell/plan-validate.py`
  - 相关持久化测试
- 需要遵守 repo-local 文档/命令/脚本规范，并检查跨文档规则传播。
