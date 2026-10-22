# dsh-trellis 全量能力复核：DSH vs Codex 的 Trellis 使用效果与缺口验证

## 背景

- 被验证对象：本仓库 `dsh-plugins/dsh-trellis`（Strategy A 本地副本，版本 `0.1.4`），
  以及 `~/.dsh/profiles/{web,trellis-headless}` 中已安装的同源包。
- 运行时：DSH `0.2.1-rc.2`；Trellis CLI `0.7.0-beta.4`；Codex CLI `0.163.0`；Node `v24.20.0`。
- 2026-10-21 / 10-22 已有多轮验证（`10-21-dsh-trellis-full-parity-audit`、
  `10-21-dsh-trellis-live-parity-verification`、`10-22-dsh-trellis-defect-fix`、
  `10-22-dsh-trellis-full-parity-reverify`），结论为“主链路对齐、未发现新问题”。
- 本轮是**独立复核**：不复用旧结论作为通过依据，重新取证；同时补上新角度
  （真实 Codex 会话对照、Trellis `init/update` 产物全量 diff、多会话并发、异常路径）。

## Goal

在 `/tmp` 临时项目中，以真实 Codex 会话与真实 DSH 会话为核心证据，回答三件事：

1. **Codex parity**：dsh-trellis 0.1.4 能否达到 Codex 使用 Trellis 的同等效果？
   逐条给出「对齐 / 有意差异（已声明）/ 未声明差异」三档结论。
2. **补足 DSH 原生不足**：无插件 plain DSH 使用 Trellis 的缺口清单，以及装插件后
   哪些已补足、哪些只能部分补足、剩余可改进空间。
3. **其他缺漏**：超出 parity 的增强（doctor、版本监控、冲突检测、设置页）与异常/并发/
   升级路径上仍存在的问题或不足。

## 硬约束

- 只开这一个 Trellis 任务，不按子项另建任务。
- 结论必须来自：真实 LLM 会话事件日志（Codex rollout、DSH session jsonl）、真实代码执行、
  真实 CLI/脚本输出、源码逐行比对；**插件 README、旧验证报告、单元测试自述不作为通过依据**。
- 必须同时结合 DSH 宿主机制与 Trellis 机制判断，不能只拿 Codex 侧当唯一标尺。
- 修复闸门：问题清单与执行方案必须先交付用户逐条确认；**确认之前不改任何插件/仓库代码**。
  若未发现问题，报告须给出逐项通过的具体证据，不接受模糊结论。
- 临时项目与隔离 profile 放 `/tmp`，不污染仓库外既有内容；仓库内仅新增本任务产物。
- 凭据只经环境变量或既有配置引用，不写入文件、不输出明文。

## 基准定义

- **基准 A（Codex 侧）**：Trellis 0.7.0-beta.4 `packages/cli/src/templates/codex/`
  （`hooks.json` 四类事件 + `agents/*.toml` + `config.toml`）与本仓库 `.codex/` 实际部署
  （`inject-workflow-state.py`、`inject-spec-context.py`、`inject-subagent-context.py`、
  三个 agent toml、`config.toml`、`hooks.json`）+ `.agents/skills/`。
- **基准 B（DSH 原生）**：Trellis `templates/dsh/`（`.dsh/skills/` 角色与入口技能、
  `DSH.md`、`.agents/skills/` 共享技能）+ 无插件 plain DSH 的真实行为。
- **基准 C（插件）**：`dsh-plugins/dsh-trellis/lib/` 全部模块的实际行为。

## Requirements

### R1 接口面清单对照

- 在同一个临时项目上分别 `trellis init --codex` 与 `--dsh`，列出两边产物：
  skills（共享/入口/角色）、agents、hooks、config、指南文件、命令面。
- 逐项标注：**对齐** / **有意差异（README 或 DSH.md 已声明）** / **未声明差异（疑似缺口）**。
- 核对 DSH 运行时实际能发现的技能集合与 Trellis 写入位置是否一致（`.agents/skills` 与
  `.dsh/skills` 的加载来源需实测，不靠文档推断）。

### R2 真实会话对照

同一临时项目、同一任务场景，分别跑真实 Codex 与真实 DSH：

- workflow breadcrumb / no-task bootstrap 的注入时机与去重；
- spec 路径级注入（deny-once、重试放行、read ticket、compaction 后重注入）；
- 子代理上下文 push（角色识别、任务来源、内容完整性、非 Trellis 项目静默）；
- 任务状态流转（planning → in_progress → completed）与会话身份隔离；
- `/trellis-status`、`/trellis-finish`、`trellis_wait` 等命令/工具面的实际可用性；
- finish-work 流程（commit → archive → journal）在 DSH 侧的可执行性。

### R3 补足程度评估

- 无插件 plain DSH 同项目同提示对照；列出缺失能力清单。
- 插件逐项补足情况；仍缺或部分补足的项单列，并评估是否还有可实现空间（结合 DSH 事件模型）。

### R4 新角度缺口扫描

- 多会话 / 多项目并发：同 profile 下 spec-inject 分片、session 指针、active task 隔离。
- 异常路径：task.json 损坏、config.yaml 损坏、`.trellis` 中途删除、只读目录的 fail-closed 行为。
- 长会话：compaction、`--session-id` resume、子代理生命周期。
- 升级路径：`trellis update` 后 DSH 产物与插件读取路径是否仍一致；插件版本/上游监控。
- 增强项：doctor、版本监控、冲突检测、Web 设置页的真实触发与边界。

### R5 交付与修复闸门

- `verification-report.md`：每项结论带证据等级（S1 真实会话 / S2 真实代码执行 / S3 源码比对 /
  S4 单元测试）与取证位置（会话日志路径、命令、diff）。
- 问题清单：定性（缺陷 / 设计权衡 / 上游限制 / 宿主限制）、影响面、可选方案、推荐项、优先级。
- 用户逐条确认后才进入修复；未确认项不动代码。

## Acceptance Criteria

- [ ] R1 产物清单与三档对照完成，证据可复核。
- [ ] R2 每个链路至少有一条真实会话或真实代码执行证据；Codex 侧尽量真实会话，受限处说明原因。
- [ ] R3 有 plain DSH 对照数据与补足矩阵。
- [ ] R4 至少覆盖并发、异常、长会话、升级四类，每类有实测或明确不可测原因。
- [ ] `verification-report.md` 与问题清单完成，交付用户确认。
- [ ] 修复前无任何插件/仓库代码改动（仅任务产物与 `/tmp` 实验物）。
