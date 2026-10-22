# Implement — dsh-trellis 全量能力复核

> 本任务是**验证任务**：步骤只产出证据与报告；修复阶段在用户确认问题清单后另起步骤。

## 0. 准备

- [ ] 0.1 建任务工作区：`/tmp/dsh-cap-verify/{proj,home,codex-home,sessions,evidence}`
- [ ] 0.2 记录环境事实：`dsh/trellis/codex/node` 版本；插件在 web/trellis-headless 的安装版本与来源。
- [ ] 0.3 快照仓库状态（`git status`、插件 `git diff --stat`），确保验证期间不改代码。

## 1. R1 产物清单与三档对照

- [ ] 1.1 `git init` 临时项目；`trellis init -u xzc --codex --dsh -y`。
- [ ] 1.2 `find .codex .dsh .agents .trellis -maxdepth 3 -type f` 全量清单 + 文件 hash。
- [ ] 1.3 读 Codex 模板/本仓库 `.codex` 与 Trellis `templates/dsh`，逐项映射。
- [ ] 1.4 实测 DSH 技能发现：会话内 skill 目录 vs `.agents/skills` vs `.dsh/skills`。
- [ ] 1.5 输出对照表（对齐 / 有意差异 / 未声明差异）。

## 2. R2 真实会话对照

### 2.1 Codex

- [ ] 2.1.1 隔离 `CODEX_HOME`（provider 引用 env；不含明文密钥）；项目 trust。
- [ ] 2.1.2 启用 hooks（user-level `features.hooks`）；确认 `/hooks` 审批在 exec 模式的行为。
- [ ] 2.1.3 真实回合：首轮注入（workflow-state / bootstrap）、edit 触发 spec deny、
      二次 edit 放行、子代理（若可用）上下文。
- [ ] 2.1.4 若 hooks 不可用：用真实 Codex hook payload 直调 `inject-*.py`（S2），标注限制。

### 2.2 DSH（插件）

- [ ] 2.2.1 隔离 `DSH_HOME` + 新 profile（本地插件 `link:`），真实 LLM 会话：
      首轮 breadcrumb+bootstrap、同轮多 step 不重复、状态变化再注入。
- [ ] 2.2.2 spec 注入：write 触碰 paths → deny-once → 重试放行；read ticket；持久化分片。
- [ ] 2.2.3 子代理 push：`Active task:` 前奏派发 → 子会话首步 push 内容；无任务 implement/check
      守卫拒绝；generic 静默。
- [ ] 2.2.4 命令/工具：`/trellis-status`、`/trellis-finish`、`trellis_wait`（直调 + 会话）。
- [ ] 2.2.5 会话身份：`DSH_TRELLIS_CONTEXT_ID`、任务指针、resume。
- [ ] 2.2.6 finish 流程：commit → archive → journal 在 DSH 侧可执行性。

### 2.3 plain DSH 对照

- [ ] 2.3.1 无插件 profile、同项目同提示，记录注入/守卫/spec/子代理差异。

## 3. R3 补足矩阵

- [ ] 3.1 汇总 plain DSH 缺口清单 → 插件逐项状态 → 剩余空间。

## 4. R4 新角度

- [ ] 4.1 并发：双项目双会话 spec 分片与 active task 隔离。
- [ ] 4.2 异常：损坏 task.json / config.yaml、删除 .trellis、只读目录。
- [ ] 4.3 长会话：compaction、resume。
- [ ] 4.4 升级：`trellis update` 前后 DSH 产物与插件读取契约；上游版本监控。
- [ ] 4.5 增强项：doctor、冲突告警、版本监控、设置页字段实测/边界。

## 5. 报告与闸门

- [ ] 5.1 写 `verification-report.md`（证据等级 + 取证位置）。
- [ ] 5.2 问题清单（定性/影响/方案/推荐/优先级）→ 交付用户确认。
- [ ] 5.3 用户确认后才进入修复（另立步骤，修复范围按确认结果）。

## 验证命令

```bash
# 单元测试（回归参考）
cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"
# DSH 会话
DSH_HOME=/tmp/dsh-cap-verify/home dsh --profile capverify "…" # 具体参数按宿主 CLI 实测调整
# 会话日志
zstd -dc "$DSH_HOME"/sessions/*/*/session.v4.jsonl.zstd | jq -c 'select(.type|test("message"))'
```

## 回退点

- 所有实验在 `/tmp/dsh-cap-verify`；删除该目录即回退，不影响 `~/.dsh`、`~/.codex` 与仓库。
- 仓库侧只新增本任务目录；若误改，`git status` 核对后按原样恢复（不使用破坏性命令）。
