# dsh-trellis 对等性全面验证

## Goal

独立判断当前已安装的 `dsh-trellis` 能否提供与 Codex 使用 Trellis 相当的工作效果、能否补足 DSH 原生使用 Trellis 的主要不足，以及是否存在值得处理的其他缺口。交付可复核的验证报告和候选执行方案；问题与方案由用户确认后才进入修复。

## Background

- 当前观察到的运行时为 DSH `0.2.1-rc.2`、Trellis `0.7.0-beta.4`、Node `v24.20.0`。
- 当前 web profile 的已安装包与仓库源码包均为 `dsh-trellis 0.1.7`；两边 `lib/` 的 `diff -rq` 结果为空。
- 只读上游 Trellis 检出位于 `/home/xzc/projects/other/Trellis`，当前 HEAD 为 `be9e19b269c25cb2787489eb81062bf96619442c`，工作树干净。
- 工作区有两个既存未跟踪文件：`docs/capability-inventory.md`、`dsh-plugins/plugin-create.md`。其版本描述与当前实际包不一致，本任务以运行时、实际安装包、当前源码和只读上游为事实依据，不修改这两个文件。

## Requirements

- 以一个新建的 Trellis 任务完成本次审计，不创建子任务或其他任务。
- 至少比较三种情况：DSH 裸用 Trellis、DSH 加载当前已安装插件、Codex 使用 Trellis；同时直接检查 Trellis 上游和 DSH 宿主契约，不能只从 Codex 行为推导结论。
- 在 `/tmp` 建立新初始化的 Trellis 临时项目和隔离运行环境。验证对象必须是当前安装包的精确副本；不把仓库单测、文档声明或模型自述单独当作运行行为证据。
- 覆盖主要用户流程和边界：会话启动与任务状态、workflow 面包屑和 bootstrap、路径级 spec 注入、子代理角色/上下文/守卫/wait、会话身份与恢复、压缩后的状态恢复、命令入口、配置开关和热更新、安装/更新/冲突诊断，以及 DSH/Trellis 版本契约。
- 每个有影响的候选问题要有复现或核验证据、影响、严重级别、归属（插件/宿主/Trellis/部署/共同限制）、可行性和推荐方案；排除纯措辞或低影响差异。
- 验证报告写清实际执行的命令/调用、预期与实际、证据路径、未运行项及原因。若没有实质问题，给出具体验证结果，不为凑问题而立项。
- 审计与修复分开：在用户确认全部问题清单及对应执行方案前，不改插件源码、Codex/DSH/Trellis 工作流源码、用户 profile 或安装态；上游 Trellis 始终只读。
- 不复制或记录凭据，不把用户私有源码发往外部服务；优先用实际 DSH runtime 配合确定性本地模型/调用夹具。若必要验证只能通过会产生外部模型调用或费用的方式完成，先列为阻塞项，不擅自改用该方式。

## Acceptance Criteria

- [x] 记录实际 DSH、Trellis、插件安装包及源码版本；确认 profile 覆盖范围，并复核安装副本与源码的差异。
- [x] 以新建 `/tmp` Trellis 项目完成 DSH 裸用、安装插件、Codex 基准的分层验证；把真实宿主调用、直接模块测试和源码/文档检查分开标级。
- [x] 依据当前 DSH 宿主事件/API 和上游 Trellis 当前脚本、模板、配置、workflow 机制核验插件的兼容性及遗漏能力。
- [x] 交付对照矩阵、问题/限制清单、证据索引、未覆盖边界，以及逐项候选修复方案和验证/回滚办法。
- [x] 在用户确认全部问题及执行方案前，源码与安装态保持不变；后续经确认的修复仍在本任务内进行，不另建任务。
- [x] 若无值得修复的问题，报告给出每个核心维度的实际调用结果及剩余证据限制。

验收依据：`research/verification-report.md`、`research/evidence-index.md` 和
`research/post-fix-review.md`。F1 的外部修复已独立复核，F2 按实际用途关闭，
M1 接受现状；未验证项及上游只读边界事件继续保留。用户已要求完结任务，
并授权仅做本地提交、不推送、保留其他文件。

## Out of Scope

- 未经用户确认的任何缺陷修复、版本升级、profile 安装/卸载或外部发布。
- 修改 `/home/xzc/projects/other/Trellis` 上游检出。
- 与 Trellis 使用体验无关的代码整理、文档润色或历史版本文档统一。
