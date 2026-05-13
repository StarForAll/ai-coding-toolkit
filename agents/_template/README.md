# Agent Template

这是 `agents/` 源资产层的作者脚手架，不是一个真实可调用的 agent。

用途：

- 作为创建新跨平台 agent 时的起点
- 避免遗漏 `README.md`、`SYSTEM.md`、`TOOLS.md`、`DEPLOYMENT.md`、`EXAMPLES/`
- 帮助作者保持 source/deploy 边界一致

## How To Use

1. 复制整个 `_template/` 目录
2. 重命名为新的 `kebab-case` agent 名
3. 替换所有占位符
4. 根据角色边界删掉不需要的段落
5. 再补该 agent 的真实示例
6. 如果示例不是实际运行产物，明确标注“期望输出格式示例”

## Not A Real Agent

以下目录以 `_` 开头，是为了明确表示它是作者辅助资产，不应当作真实 agent 部署：

- `_template/`

## Files

- `README.md`
- `SYSTEM.md`
- `TOOLS.md`
- `DEPLOYMENT.md`
- `EXAMPLES/`

## Authoring Reminder

- `README.md` 只保留用途、输入输出、边界和对 `DEPLOYMENT.md` 的明确指针
- 平台字段表与 wrapper 模板优先放在 `DEPLOYMENT.md`
- 示例若不是实际运行结果，必须显式说明
