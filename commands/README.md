# Commands

这里存放可复用的命令集合（scripts / snippets / workflows），用于把常用操作标准化、可版本化。

## 推荐目录结构（可按需调整）

```text
commands/
  codex/            # Codex CLI 相关的自定义命令/工作流（如有）
  claude/           # Claude Code / Claude CLI 相关（如有）
  shell/            # 通用 shell 脚本、Makefile 片段等
  README.md
```

## 建议约定

- 每个命令（或一组强相关命令）放一个目录，附带 `README.md` 说明：
  - 解决什么问题
  - 依赖什么环境（Node/Python/CLI）
  - 如何运行与常见参数
  - 输出/副作用（是否会写文件、是否会改 git 状态等）

