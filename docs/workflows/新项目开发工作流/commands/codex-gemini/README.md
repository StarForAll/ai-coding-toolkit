# Codex CLI / Gemini CLI 适配

这些 CLI 目前没有统一的命令扩展机制，但仍可通过脚本、上下文注入或预置能力配置使用部分工作流命令。

## 使用方式

### 方式 1: Python 脚本直接调用

```bash
# 可行性评估
python3 docs/workflows/新项目开发工作流/commands/shell/feasibility-check.py --step compliance

# 设计文档验证
python3 docs/workflows/新项目开发工作流/commands/shell/design-export.py --validate

# 任务拆解验证
python3 docs/workflows/新项目开发工作流/commands/shell/plan-validate.py

# 自审检查
python3 docs/workflows/新项目开发工作流/commands/shell/self-review-check.py
```

> 所有脚本仅依赖 Python 3 标准库，无需安装任何第三方包。

### 方式 2: Markdown 上下文注入

在对话开始时，将命令文件内容作为上下文：

```
请先阅读以下工作流指引：
@docs/workflows/新项目开发工作流/commands/feasibility.md

然后按照指引执行可行性评估。
```

任务级补充审查场景可改为：

```text
请先阅读以下工作流指引：
@docs/workflows/新项目开发工作流/commands/check.md

然后按照指引判断是否需要任务级多 CLI 补充审查。
```

> 对于 `§5.1.x` 的任务级多 CLI 补充审查，**不建议**仅靠一次性 Markdown 上下文注入临时模拟 reviewer / action 协议。
> 若目标 CLI 尚未具备 `multi-cli-review` 或 `multi-cli-review-action` 对应能力，应先补齐对应 skill，再参与该审查层。

### 方式 3: AGENTS.md / CONTEXT.md

将命令摘要写入各 CLI 的全局配置文件：

- Codex: `~/.codex/AGENTS.md` 或项目 `.codex/AGENTS.md`
- Gemini: 通过 prompt 模板

## 兼容性矩阵

| 功能 | Codex | Gemini | 说明 |
|------|-------|--------|------|
| Python 脚本 | ✅ | ✅ | 完全兼容（需 Python 3） |
| Markdown 指引 | ✅ | ✅ | 通过上下文注入 |
| 自然语言触发 | ✅ | ✅ | AI 自行理解 |
| Hook 自动注入 | ❌ | ❌ | 不支持 |
| Slash 命令 | ❌ | ❌ | 不支持 |
| 任务级补充审查能力 | ⚠️ | ⚠️ | 需预先补齐 `multi-cli-review` / `multi-cli-review-action` 对应 skill，再参与该机制 |
