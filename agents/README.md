# Agents

这里存放自定义 agent（或 agent 相关资产），用于复用固定的工作流、约束与提示词。

当前目录在本仓库里是 **source asset 层**，不是三方 CLI 的直接运行目录。面向 Claude Code、OpenCode、Codex 的真实部署文件当前仍分别位于 `.claude/agents/`、`.opencode/agents/`、`.codex/agents/`。

## 推荐目录结构（可按需调整）

```text
agents/
  <agent-id>/
    README.md        # 该 agent 的用途、适用场景、示例
    SYSTEM.md        # 系统提示词（System Prompt）
    TOOLS.md         # 工具/权限/边界约束（可选）
    EXAMPLES/        # 输入输出示例（可选）
```

## 当前已落地的源资产示例

- `self-media-content-expert/`
  - 通用“现代自媒体内容设计实现专家”
  - 重点能力：实时趋势核验、内容结构设计、多平台内容改写、交付规范化
  - 适配目标平台：Claude Code / OpenCode / Codex
- `software-solution-delivery-expert/`
  - 通用“软件项目接单与交付专家”
  - 重点能力：需求澄清、MVP 收敛、风险识别、实施与验收路径设计
  - 适配目标平台：Claude Code / OpenCode / Codex

## 作者辅助资产

- `_template/`
  - 新建跨平台 agent 时的目录脚手架
  - 不是实际 agent，不用于部署
- `NAMING-AND-VERSIONING.md`
  - 命名、范围切分、版本演进建议

## Source / Deploy Boundary

- 源资产层：`agents/<agent-id>/`
- Claude Code 部署层：`.claude/agents/*.md`
- OpenCode 部署层：`.opencode/agents/*.md`
- Codex 部署层：`.codex/agents/*.toml`

如果修改了 `agents/<agent-id>/SYSTEM.md` 或 `TOOLS.md`，后续可在目标项目中据此生成或同步对应平台 wrapper；本仓库当前不要求为每个 source agent 同步提交运行副本。

以 `_` 开头的目录保留给作者辅助资产，不视为真实 agent。

## 命名建议

- `agent-id` 用短横线风格：`feature-planner`、`bug-fixer`、`release-helper`。
- 以“任务/角色”为中心命名，避免跟具体项目强绑定（否则建议放到 `docs/` 并标注项目背景）。
