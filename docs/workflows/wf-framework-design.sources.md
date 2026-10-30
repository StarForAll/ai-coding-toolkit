# wf 框架设计的来源与证据边界

本文件保存独立框架设计引用的稳定定位。正文中的规则由 `wf-framework-design.md` 定义，本文件只说明借鉴依据。任务研究、报告与修订史保留在 Trellis 任务/Git 中；归档移动任务目录不应影响产品文档。

取证日期：2026-10-30。全部基于本地 checkout 的固定提交与文件直接阅读；未拉取远端、未运行上游测试/安装或模型效果评测，不声明最新官方版本。下列 `仓库@提交:路径` 可在对应 checkout 用 `git show <提交>:<路径>` 重取；不把本机绝对路径作为长期引用。

## 参考版本

| 来源 | 固定提交 | 版本与读取边界 |
|---|---|---|
| skills | `59db609eb1e18aaf59b63284d0e52255aff0c63c` | 工作区当时干净；按提交定位 |
| Trellis | `be9e19b269c25cb2787489eb81062bf96619442c` | CLI 标 `0.7.0-beta.4`；本地 `.gitignore` 有原有改动，未用于设计结论 |
| stop-that-shit | `17ffc9f5108381916f4f9b019d61b759626c4a71` | HEAD 标 `0.2.5`；5 个本地发行/贡献文件有原有修改，不将其内容当固定提交事实 |
| mcode-stack | `d987793c2945e3455782180989322f6ce37b8363` | 工作区当时干净；按提交定位 |
| 本仓库旧 wf 设计 | `925654b1c35a5e3b03c5310a6b72362933c5560f` | 早期内嵌模块两份设计；本框架保持独立，不继承其存储实现 |
| 本仓库旧统计规则 | `902e8943ad6edf5862c59cdd4be6b614ee58a354` | 仅用于核对重写曾丢失的输入约束，不作为现行运行规则 |

## 借鉴内容与原文件

| 概念 | 固定版本下的文件 | 支持的判断与限制 |
|---|---|---|
| 小原语、工程纪律与调用权 | skills 的 `README.md`、`skills/engineering/implement/SKILL.md`、`skills/engineering/code-review/SKILL.md` | 原语小型组合；原版双轴使用子代理，wf 改为顺序执行，不能引用其独立上下文理由自证 |
| 需求澄清与当前规划批准 | Trellis 的 `packages/cli/src/templates/common/skills/brainstorm.md` | 建任务与批准实施分开，不把文件存在当许可 |
| 可执行知识与正向沉淀 | Trellis 的 `packages/cli/src/templates/common/skills/update-spec.md`；skills 的 `SCOPE.md` | 前者包括成功实现/长期约定；后者“真实失败”是上游贡献门槛，不泛化为项目知识准入 |
| 纯本地路径匹配 | Trellis 的 `packages/cli/src/templates/trellis/scripts/common/spec_match.py`、`spec_inject.py` | 借 frontmatter、glob、预算的形状，自建标准库实现，不复制宿主 hooks |
| MCP 依赖的事实范围 | Trellis 的 `packages/cli/src/templates/common/bundled-skills/trellis-spec-bootstrap/` 中 `SKILL.md`、`references/repository-analysis.md`、`references/mcp-setup.md` | bootstrap 推荐并编排 GitNexus/ABCoder，配置文档称工具选择；常规 update-spec 未列其必需前置。未测试 MCP 全关时整个 Trellis 的行为；wf 明确不依赖它们 |
| 三方升级与清单所有权 | Trellis 的 `packages/cli/src/commands/update.ts`、`src/utils/manifest-prune.ts`、`src/commands/uninstall.ts` | 对比旧哈希/本地/新版，区分删除与碰撞；不照搬其卸载项目数据策略 |
| 任务边界与最近反例 | stop-that-shit 的 `skills/stop-that-shit/SKILL.md`、`cases/README.md`、`EVIDENCE.md` | 保持必要工作、尊重只读/改动模式、允许/拒绝成对验证；效果声明不能由单元测试或拒绝次数推出 |
| 显式文件范围 | stop-that-shit 的 `skills/stop-that-shit/SKILL.md` 中 `lock change files=...` | 原版是完整边界已知时的硬文件名单，未定义 PRD glob。wf 的 glob 与越界回 Plan 是本框架自建契约及用户明确裁决，不声称来自其实现 |
| 持久交接与长会话 | mcode-stack 的 `stacks/ronny/skills/handoff-doc/SKILL.md`、`long-session-check/SKILL.md` | 先查真实项目事实再写简报，上下文三分桶；不接管宿主压缩和记忆 |
| 版本递增 | mcode-stack 的 `scripts/check.mjs` | `CHECK_BASE` 已设置时核对变动 stack 的 plugin 版本递增，未设则跳过；因其 marketplace 分发需要。wf 借发行前检查思想，不引入 marketplace，也不声称一次源码编辑就必须 bump |
| 人视角入口速查 | mcode-stack 的 `stacks/ronny/WORKFLOW.md` | “时刻→技能”表用于使用说明；wf 后续使用文档据自己的调用权与实际命令生成 |
| 依赖顺序语义 | 本仓库固定版本 `docs/workflows/workflow-design.md` 与 `workflow-implementation.md` | 满足需正常归档、五条件挂起清除、替换/放弃只前向；不搬双事实源和平台分支 |
| 回收统计输入 | 本仓库 `902e894:docs/workflows/wf-framework-design.md` 的回收治理段 | 旧版以各任务（含归档）的策展条目承载统计；现行稿明确命名为“引用”，不冒称实际加载 |

## 不作为本框架依赖的能力

不吸收 STS Guard/宿主拦截、Trellis 平台矩阵/团队 workspace/channel、skills 并行实现或 mcode 定时采集。观察期会增加时间态，仍为未批准候选，不能靠它遮住当前规则的错误拒绝。

许可按实际借用文件及其 NOTICE 核对。上游宣传、README 安装示例与本地测试文件只证明其文本/文件存在，不等同本轮运行验证；存在来源争议时保留证据边界，不推断最新状态。
