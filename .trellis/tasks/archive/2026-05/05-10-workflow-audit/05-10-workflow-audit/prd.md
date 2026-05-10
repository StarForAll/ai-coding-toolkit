# workflow-audit: 新项目开发工作流性能差异

## Goal

验证“原生 Trellis 使用较快，而嵌入 `docs/workflows/新项目开发工作流/` 后较慢”这一历史体感在当前版本下是否仍然成立，并区分它属于 Trellis baseline 开销、workflow 增量开销，还是旧配置/旧文档路径导致的条件性问题。

## What I already know

* 审计目标固定为 `docs/workflows/新项目开发工作流/`。
* 当前 workflow 声明兼容版本为 `0.5.10`，本机 `trellis -v` 也是 `0.5.10`，同版本审计允许继续。
* 历史任务 `.trellis/tasks/archive/2026-04/04-02-analyze-new-project-workflow-init-overhead/prd.md` 曾明确指出“首次使用成本高，容易让使用者把严谨体验成进入太慢、上下文太厚”。
* 当前文档已把 OpenCode `instructions` 的推荐口径收敛为“只挂主入口与必要补充，不默认全量挂载所有阶段文档”。
* 当前 Codex/Claude 的 SessionStart hook 会主动注入 `get_context.py` 输出、workflow 目录索引、guides index、spec index 列表与 task status。

## Assumptions (temporary)

* “感觉变慢”不能只靠文件数量判断，必须区分：
  * 默认 SessionStart 注入成本
  * 每回合 breadcrumb 注入成本
  * workflow 安装后新增的入口/skills/patch 的增量成本
* 如果 current workflow 的增量上下文很小，而 baseline 已经很重，则“嵌入后更慢”更可能是 baseline 被误归因给 workflow。

## Open Questions

* 当前版本下，workflow 安装后是否还会明显增加默认启动上下文？
* 如果存在额外变慢，它来自哪个平台承载面？
* 旧问题里提到的 OpenCode `instructions` 过厚风险，现在是否仍属于当前合同的一部分？

## Requirements (evolving)

* 完成同版本 `workflow-audit` 静态与运行时验证。
* 对比 `trellis init` baseline 与 formal install 后状态。
* 给出“问题仍存在 / 不再成立 / 条件性存在”的明确结论。
* 指出慢的真实来源，而不是只给主观判断。

## Acceptance Criteria (evolving)

* [x] 验证 version gate、target binding、managed surface 合同
* [x] 采集 fresh `trellis init` baseline
* [x] 完成 `detect-embed-state.py`、`install-workflow.py --dry-run`、formal install、`upgrade-compat.py --check`
* [x] 对比 baseline 与 install 后的 SessionStart 注入规模
* [x] 输出是否仍存在性能问题及原因

## Definition of Done (team quality bar)

* 结论基于 source repo、generated target project、runtime command output 三层证据
* 不把 baseline 自带产物误归因给 workflow
* 明确区分“当前缺陷”和“历史风险点”

## Out of Scope (explicit)

* 不修改 workflow 源资产
* 不做跨版本兼容性审计
* 不做主观交互速度 benchmark 或网络 API 响应时间 benchmark

## Technical Notes

* Task dir: `.trellis/tasks/05-10-workflow-audit/`
* Runtime validation target project:
  * baseline/formal install: `/tmp/workflow-audit-perf-eGidHm`
  * SessionStart baseline size probe: `/tmp/workflow-audit-perf-pre-ctx-*`
* 关键命令：
  * `trellis -v`
  * `detect-embed-state.py --json`
  * `install-workflow.py --dry-run`
  * `install-workflow.py` with `WORKFLOW_EMBED_EXECUTOR_CONFIRMED=1`
  * `upgrade-compat.py --check`
* 关键探针：
  * Codex / Claude SessionStart `additionalContext` 字符数
  * baseline 与 install 后 hidden carrier 差异
  * OpenCode / Codex README 当前口径是否仍要求厚注入
