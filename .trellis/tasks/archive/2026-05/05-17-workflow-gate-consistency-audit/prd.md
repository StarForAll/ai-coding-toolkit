# 审计并修复新项目开发工作流强门禁一致性问题

## Goal

基于目标项目 `/tmp/trellis-0.5.16-2` 的真实嵌入结果，审计用户列出的 7 个候选问题是否真实存在。对确认存在的问题，在 `docs/workflows/新项目开发工作流` 内做最小、可验证修复，并同步检查同类残留，避免后续目标项目执行 `trellis init` + 工作流嵌入后继续产生相同问题。

## What I Already Know

- 当前任务维护的是工作流产品源资产，不是当前仓库正在使用的 Trellis 工作流。
- 正式修复范围限定为 `docs/workflows/新项目开发工作流`；不得修改其他产品源目录。
- 用户提供的判断样本是 `/tmp/trellis-0.5.16-2`，它是已经执行 `trellis init` 并嵌入本工作流的临时目标项目。
- `/tmp/trellis-0.5.16-2/.trellis/workflow-installed.json` 记录 `profile: outsourcing`、`trellis_version: 0.5.16`、`workflow_version: 0.1.28`。
- 工作流源文件 `docs/workflows/新项目开发工作流/commands/workflow_assets.py` 声明 `COMPATIBLE_TRELLIS_VERSION = "0.5.16"`，本机 `trellis -v` 输出 `0.5.16`，版本门禁已通过。
- 本次用户明确要求：先新建相关任务并补充完整任务信息，包含 `implement.jsonl` 和 `check.jsonl`，正式执行前停下来；整个过程不能使用 agents。

## Candidate Issues To Validate

1. 旧三阶段模型残留与 12 阶段强门禁模型冲突：目标项目 `.trellis/workflow.md` 仍保留旧 Phase 1/2/3，且 `trellis-start` 无任务入口仍指向 brainstorm/task create，可能绕过 feasibility。
2. Claude `SessionStart` 无任务提示仍引导 `trellis-brainstorm` + create task，可能绕过 AGENTS 中“首次立项必经 feasibility”的规则。
3. 首次入口 profile 判断错误：安装记录为 `outsourcing`，但 route 在无 `assessment.md` 时提示 `profile_hint=personal`。
4. 阶段切换文档 Quick Reference 中的 Step B 直接 `set --stage ...`，与脚本要求先 `awaiting_user_confirmation` 冲突。
5. `trellis-finish-work` 文档前后矛盾：开头仍要求 archive/add_session，后续补丁又说明 finish-work 不执行 archive/add_session。
6. `task.py start` 降级行为与文档不一致：文档称无 session identity 会失败，实际可能返回 0 并改 `status=in_progress`，导致 route 进入不可恢复状态。
7. 导入的 universal/scenario specs 不易发现：`library-lock` 导入 requirements foundation pack，但 `get_context --mode packages` 对 `scenarios` / `universal-domains` 缺少可发现 index 路径，导致 PRD、验收、需求文档规则普通注入缺失。

## Requirements

- 先证据后结论：每个候选问题必须从目标项目 `/tmp/trellis-0.5.16-2`、工作流源资产、运行命令输出中取得证据，不能按用户描述直接认定。
- 对确认存在的问题，只修改 `docs/workflows/新项目开发工作流` 内的源资产、安装器补丁、命令文档或测试。
- 如问题本质属于 Trellis 原生基线行为，必须在本工作流合适位置通过安装器/补丁/目标项目文档约束修复，不直接修改当前仓库 `.trellis/` 基线文件。
- 检查同类问题：凡涉及入口路由、阶段切换、profile 推断、finish-work 收尾、spec 注入发现能力的修复，必须在同类 CLI 和同类文档中搜索残留。
- 不使用 `spawn_agent`、`explorer`、`worker` 或任何平台 agent/sub-agent。
- 如果正式运行审计需要嵌入或重嵌 `/tmp` 项目，Codex 不能执行正式 embed 步骤；需按 `workflow-audit` Codex handoff 规则停下并要求主交互 Claude Code 或 OpenCode 接手。

## Out Of Scope

- 不修改当前仓库根工作流 `.trellis/workflow.md`、`.agents/skills/trellis-*` 等当前项目运行面，除非只是本任务目录内记录上下文。
- 不修改 `/tmp/trellis-0.5.16-2` 作为持久修复；它只作为验证样本。
- 不升级或替换 Trellis 版本，不把同 minor patch 兼容门禁扩大为跨版本兼容判断。
- 不处理未被证据关联到上述问题族的样式优化或低价值整理。

## Acceptance Criteria

- [ ] 7 个候选问题均在 `audit-report.md` 中得到结论：confirmed / false-alarm / blocked，并带 source-layer 标记与 validation action。
- [ ] 所有 confirmed 问题的修复只落在 `docs/workflows/新项目开发工作流` 下。
- [ ] 同类残留通过 `rg` 或脚本化检查完成，并在报告中记录检查范围。
- [ ] 目标项目 `/tmp/trellis-0.5.16-2` 的相关命令或静态证据能证明修复方向与真实嵌入结果一致。
- [ ] 相关文档、安装器补丁、测试或验证脚本保持一致，没有新增命令被脚本拒绝、入口绕过 feasibility、profile 提示误导、finish-work 收尾矛盾或 spec 注入缺失。
- [ ] 运行相关验证命令并记录实际结果；不能运行的验证必须记录原因和证据边界。

## Verification Plan

- `trellis -v`
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/test_workflow_installers.py` 或项目现有等价测试入口，按实际可用命令调整。
- `/ops/softwares/python/bin/python3 docs/workflows/新项目开发工作流/commands/shell/test_workflow_state.py`
- `/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings`
- 针对每个修复点运行定向 `rg`，确认同类残留消失或被解释为非缺陷。

## Formal Execution Status

Paused before formal audit/remediation execution per user request. Do not run `task.py start` yet.
