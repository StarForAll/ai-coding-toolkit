# brainstorm: 新项目工作流补充自动化检查要求

## Goal

补充 `docs/workflows/新项目开发工作流/工作流总纲.md`，把“技术框架确定后需要明确自动化检查内容”写成强约束，避免继续使用模糊的默认 `Lint` 表述，并给出按项目/框架补充或替换检查项的要求，例如可纳入 SonarQube。

## What I already know

* 目标文档当前在多个位置使用了默认化表述，如 `Lint / Type Check / Unit Test / Security Scan`。
* 文档已有“技术架构确认后的项目 Spec 对齐”门禁，适合补充“检查矩阵”绑定要求。
* `task_plan.md` 模板中的验收标准仍写为“Lint检查通过”，不够项目化。
* 仓库内暂未出现现成的 `SonarQube` 相关表述，可以作为示例新增。

## Assumptions (temporary)

* 本次修改范围限定为工作流文档，不新增脚本或校验程序。
* 用户希望强调“框架确认后必须显式定义检查项”，而不是强行要求所有项目都必须接入 SonarQube。

## Open Questions

* 当前无阻塞性问题。

## Requirements (evolving)

* 在技术架构确认后的门禁中，新增“自动化检查矩阵/清单”要求。
* 明确不得只写默认 `Lint`，而要根据技术栈、框架、语言、部署方式定义具体检查项与命令。
* 允许并鼓励补充项目特定检查，如 SonarQube、构建校验、依赖漏洞扫描、DB migration 校验等。
* 将这一要求同步到 `task_plan.md` 模板与实施阶段门禁表述，保持前后一致。

## Acceptance Criteria (evolving)

* [ ] 技术架构确认后的门禁新增“自动化检查清单”定义要求。
* [ ] `task_plan.md` 模板不再只写“Lint检查通过”，而是要求填写项目实际检查项。
* [ ] 实施阶段自动门禁说明体现“按项目定义并执行”的原则，并含 SonarQube 示例。

## Definition of Done (team quality bar)

* Docs updated with clear, executable wording
* Internal wording remains consistent across affected sections
* Relevant examples and verification expectations are explicit

## Out of Scope (explicit)

* 新增真实 CI 流水线配置
* 编写 SonarQube 集成脚本
* 修改其他工作流文档

## Technical Notes

* 主要修改文件：`docs/workflows/新项目开发工作流/工作流总纲.md`
* 相关段落：`3.7 技术架构确认后的项目 Spec 对齐`、`task_plan.md 模板验收标准`、`5.1 单个需求开发流程`、`单次对话任务闭环规范`
* 相关仓库规范：`.trellis/spec/docs/index.md`、`.trellis/spec/guides/index.md`
