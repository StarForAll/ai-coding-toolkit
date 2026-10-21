# Implement — dsh-trellis 平台能力对标验证与修复

## 准备

1. `python3 ./.trellis/scripts/task.py start .trellis/tasks/10-21-dsh-trellis-parity-audit`
2. 记录基线：`node -v`、`dsh --version`、插件 `package.json` 版本、`git status`。

## 阶段

| # | 阶段 | 关键动作 | 证据产物 |
| --- | --- | --- | --- |
| A | 状态与提示注入 | 逐状态跑 JS 解析器与 Python hook，测截断，读 live 会话 | `findings/state-breadcrumb.md` |
| E | 端到端会话 | 临时项目 + 独立 profile 跑 headless 多状态，抓模型请求 | `findings/e2e-session.md` |
| B | spec 注入 | 真实 spec 目录下跑注入决策与拒绝路径，对照 Codex hook | `findings/spec-injection.md` |
| C | 子代理与守卫 | 真实 subagent 调用的推送/拒绝路径 | `findings/subagent-guard.md` |
| D | 命令面 | 命令注册、doctor、上游路由、冲突检测 | `findings/command-surface.md` |
| F | 修复（用户确认后） | 0.3.8：正则、状态映射、stale、workflow 选择、skip keyword、inline、推送文案 | `report.md` §5 + `dsh-plugins/dsh-trellis/docs/validation-0.3.8-local.md` |

## 验证命令（最小可复现）

```bash
# 解析器实测（真实 workflow.md）
cd dsh-plugins/dsh-trellis && node --input-type=module -e '<import + parse + measure>'
# Python hook 基线
cd /home/xzc/projects/personal/ai-coding-toolkit && python3 .codex/hooks/<parser> ...
# 插件自带测试（辅助）
cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"
# 端到端（临时 profile + 本地 mock LLM）
dsh --profile trellis-audit --json "<prompt>"
```

## 验收门

- 每个结论至少一条 E1 证据。
- 探针 A 需要：可复现命令 + 实测行数/字节 + 与 Python hook 对照。
- 问题清单交付后停在"等待用户确认"；用户确认后才实施修复。
- 修复后跑完整测试与真实项目 E2E，更新本地验证记录。

## 回滚点

- 删除 `/tmp/trellis-e2e`、临时 DSH profile 与 mock 服务。
- 修复前状态：`dsh-plugins/dsh-trellis` 0.3.7（git 未提交目录）。
