# PRD: 修正 Trellis 0.5.4 升级后的 workflow 契约漂移与模板状态

## 背景

当前仓库在一次 Trellis 0.5.4 小版本升级后，工作区同时存在：

- 已修改的 live 文件
- 多个未合并的 `.new` 候选文件
- 已被刷新过的 `.trellis/.template-hashes.json`

审计结果显示，这轮升级把另一套 workflow phase 契约混入了当前仓库，导致多个 live 技能、命令、hook、agent 与 `.trellis/workflow.md` 的真实阶段编号不一致。

## 问题

需要把这轮升级修正回当前仓库真实生效的 Trellis 契约，并清理错误吸收的模板内容，避免后续：

- `continue` 路由到不存在的 phase
- `finish-work` 走错 close-out 流程
- `trellis-research` 丢失关键证据工具
- `.template-hashes.json` 隐藏本地用户修改

## 目标

1. 恢复当前仓库真实 workflow phase 语义：
   - Plan: `1.1 / 1.2 / 1.3`
   - Execute: `2.1 / 2.2 / 2.3`
   - Finish: `3.1 / 3.2`
2. 保留本轮升级里合理的注释增强，但不引入新的 runtime 契约。
3. 不接收 `iflow` / `pi` 相关平台扩展。
4. 恢复 `trellis-research` 的证据优先工具链。
5. 修正 `.trellis/.template-hashes.json` 的错误刷新，使其重新代表模板基线而非当前本地改动内容。
6. 处理本轮不应保留的 `.new` 文件，避免后续继续误合并。

## 非目标

- 不把当前仓库整体迁移到另一套 `1.3 / 1.4 / 3.4 / 3.5` phase 模型
- 不引入 `iflow` / `pi` 平台支持
- 不重构 `record-session-helper.py` / `add_session.py` 总体设计
- 不实现 `agents/` 源资产层

## 约束

- 本任务全程不使用 subagents。
- 以当前仓库 live `.trellis/workflow.md` 为 workflow source of truth。
- 对 `.new` 文件采取按需吸收、拒收或删除，不做盲目覆盖。
- 保留当前仓库已有的 metadata closure / resume 恢复链路。

## 验收标准

1. 当前仓库所有受影响的 live 技能、命令、hook、agent 与 `.trellis/workflow.md` 的 phase 编号重新一致。
2. `finish-work` 重新指向当前 live close-out 契约，而不是错误的 `3.4 + add_session.py` 变体。
3. `trellis-research` 重新具备内部代码定位和第三方文档检索所需的核心工具与说明。
4. `.trellis/.template-hashes.json` 不再把当前本地修改内容当作模板基线。
5. 本轮明确拒收的 `.new` 文件不再留在工作区误导后续合并。
