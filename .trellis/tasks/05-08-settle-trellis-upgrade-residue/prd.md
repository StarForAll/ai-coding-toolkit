# 收敛 trellis 升级残留并清理 `.new` 候选

## Goal

按当前仓库实际使用的 Trellis live 合同收敛升级残留：

1. 修正 Kiro live 改动中的错误部分
2. 清理不应保留的 `.new` 候选文件
3. 保留当前仓库需要的 live 增强
4. 让 `.trellis/.template-hashes.json` 与最终 live 文件一致

## Scope

本次只处理当前仓库实际使用的 Trellis runtime / platform deployment 层，不处理
`docs/workflows/新项目开发工作流` 的目标项目升级产物。

## Required Actions

### R1: 修正 Kiro live 改动

- 保留 `.kiro/agents/trellis-{check,implement,research}.json` 中将 hook 命令落为可执行命令的修正
- 修正 `.kiro/hooks/inject-subagent-context.py`：
  - 将错误的 `Phase 1.3` 引用恢复为当前仓库 live 合同的 `Phase 1.2`
  - 将 research search tool 提示恢复为与 Kiro agent 实际可用工具一致的口径

### R2: 清理不应采用的 `.new` 候选

- 删除所有引入 `Phase 1.3 / 1.4 / 3.4 / 3.5` 漂移的 `.new`
- 删除所有会弱化 `trellis-research` 工具能力的 `.new`
- 删除其他已经确认不应并回 live 的 `.new`

### R3: 保留 live 合同

- 保留当前 `.trellis/workflow.md` 的 phase 编号和 close-out 语义
- 保留当前 Claude / Codex / Qoder / OpenCode / shared skill 的 live 合同，不被 `.new` 回退
- 保留 `record-session-helper.py` 作为当前 close-out 链的一部分

### R4: 同步模板哈希

- 在最终 live 文件确定后，同步 `.trellis/.template-hashes.json`
- 不让 template hash 继续为错误的 Kiro hook 内容背书

## Acceptance Criteria

- [ ] `.kiro/hooks/inject-subagent-context.py` 的 Phase 口径和工具提示与当前仓库 live 合同一致
- [ ] 不应采用的 `.new` 文件全部清理
- [ ] `trellis-research` 的 live 工具能力未被回退
- [ ] `.trellis/.template-hashes.json` 与最终保留的 live 文件一致
- [ ] 相关验证命令通过

## Validation

```bash
/ops/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings
./scripts/validate-skills.sh
/ops/softwares/python/bin/python3 -m unittest trellis-library/tests/test_cli.py
git status --short
```
