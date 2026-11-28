# wf 控制流修复与跨会话接续验收

## Goal

在 `0.0.22` 基线上复核历史 dogfood 故障与本轮两份外审意见，修复影响
「正常入口推进 / 受阻后可执行出口 / 换会话按持久事实恢复 / 完成结论可信」的根因，
并用可复算的断言与隔离目标项目验收证明修复前后的差别。规划产物先行；本次不提交、
不归档、不推进版本、不发布、不改真实 dogfood 项目。

## 基线事实（2026-11-28 20:49 采样）

| 项 | 值 | 说明 |
|---|---|---|
| 仓库 / 分支 | `ai-coding-toolkit` / `main` | 工作区干净（`git status --porcelain` 为空） |
| HEAD | `1f60bb25b4892b61c887999ae3947139692bbf86` | `chore(wf): release 0.0.22` |
| README 目标版本 | `0.0.22` | `docs/workflows/wf/README.md` 目标版本单元 |
| 模块源树 | `docs/workflows/wf/`（`dev-manifest.json` = `0.0.0-dev`） | 本轮候选的实现来源 |
| 发行树 | `docs/workflows/wf-release/`（`wf-release.json` = `0.0.22`） | 生成物，不手改；本轮不改版本，故不重建 |
| 系统命令包 | `docs/workflows/wf-cli/` | 维护面入口，不投放目标项目 |
| 真实 dogfood 项目 | `/home/xzc/projects/personal/traffic_monitor`（安装记录 `0.0.7`，工作区有未跟踪 `.wf/` 等） | 本轮只读；不修改 |

证据来源分层：

- **实际被验证的资产**：`docs/workflows/wf/payload/` 源码树（candidate），以及隔离目标项目
  上的 dev 部署副本；发行树 `0.0.22` 不是本轮候选，升级/发布相关结论不冒充候选验证。
- **历史会话**：`/tmp/traffic_monitor_1..4.md`（四份 11-08 Codex 会话导出）可读；
  `~/.codex/sessions/2026/11/08/` 下对应四份 `rollout-*.jsonl` 原始日志可读。
  `/tmp/wf-find-a.md`、`/tmp/wf-find-b.md` 缺失；ZCode 原始会话存储为 Electron/LevelDB，
  本轮未取得可直接引用的文本。只依赖转述的判断在 `design.md` 中标注。
- **本轮外审**：两份 reviewer 报告（agent1/agent2）随任务指令提供，按条裁定见 `design.md`。

## 范围（本轮承诺的场景）

- **S1 正常入口推进**：全新隔离项目经真实安装/部署入口安装候选后，
  `enable → task-new → PRD → task-approve → task-start → task-check → archive` 可走通；
  实例内任务可走完 `run create → run advance → 四阶段 → run finish`。
- **S2 受阻后可执行出口**：required 验收未核实、双轴依据缺失、收工无业务 WIP、
  `verify resolve` 不改变门禁等受阻点，入口给出的下一步必须真实改变状态或明确交人，
  不得停在「照做后仍撞同一拒绝」。
- **S3 换会话按持久事实恢复**：旧对象终态后新会话 `enable --new-session` 可开始下一对象；
  暂停/交接后新会话能按绑定、写权、WIP 指纹与任务记录接续；无宿主标识时有受支持出口。
- **S4 完成结论可信**：实例步骤契约把定义声明的验证来源/消费时点、步骤级与动作级人判点、
  `waived` 资格全部纳入 Check；Check 发布 `pass` 的条件与 Finish 门禁消费条件一致。

## 需求

- **R1 实例步骤契约完整消费**：`runs.step_contract` 保留 `source/established_by/stored_in/consume_at`；
  Check 核对 `stored_in.verification_id`、`consume_at` 与已批准 plan 一致；动作级人判点必须有
  命中选项的答复；`required` 且未声明可略的动作不得以 `waived` 结案。
- **R2 验收处置出口可执行**：`verify resolve` 校验验收 id 存在、`narrow` 只用于未核实
  （不是已失败）；其 `next_` 与 Finish 门禁出口指向真正改变门禁的入口（规划变更/重批/重检，
  或异常归档），不再宣称「resolve 后重入即可」。
- **R3 Check 发布与消费同条件**：双轴 notes 在验证执行前解析并校验 `basis`；执行后文件变化按
  `WF_CHECK_STALE`；组装 `pass` 前复用 `check.validate_check_result`，不得发布一个会被后续门禁
  判为缺证据的 `pass`。
- **R4 实例暂停与释放的 WIP 事实一致**：`writer release` 释放暂停实例前，除已登记
  `handoff.wip` 外还核对当前任务 e 桶未提交路径；未登记即拒绝并给「保持写权/处置后重试/
  writer-handover」出口，防止交接记录丢失。
- **R5 收工空 subject 死路**：空 subject 守卫只看本任务业务 WIP（e 桶 ∩ 未提交），
  不被自身控制记录（b 桶）或本任务回执路径（a 桶）误触；`keep`/`commit` 的归属核接受
  本任务 a∪e，仍拒绝 b/c/d。
- **R6 契约表述与实现一致**：修正 C2「仅人调启用入口可登记」的机制表述（与 §1.1
  「机制不核调用者身份」一致）、`_commit_gate_problems`「所有提交入口」的越界声明、
  `states.json` 迁移登记与真实入口/出口的漂移。
- **R7 历史故障复核**：逐项复核 11-08 四份会话中与 S1–S4 相关的故障；已由现有实现/用例
  修复的给出证据，未闭合的纳入本轮或登记边界。
- **R8 维护接续**：把候选身份、逐条裁定、已跑验证与结果、未覆盖项、下一步写入本任务产物；
  只读任务目录与 Git 可重建本轮状态。
- **R9 产品接续**：隔离目标项目部署可识别候选，验证同会话续用、旧对象终态后新会话、
  暂停/交接接续、无宿主标识出口；夹具模拟、真实宿主、升级预览/实际升级分别记录结果。

## 验收标准

- **AC1** `test_step_contract` 新增断言在基线上红、修复后绿：`waived` 无 `skip` 被拒；
  人判点未声明选项被拒；动作级人判未答被拒；`consume_at`/`stored_in.verification_id`
  失配被拒；旧契约（无 `stored_in`）仍可按 id 消费。
- **AC2** `verify resolve` 对不存在 id、已 `failed` 的 `narrow` 拒绝；成功记录不回写 Check；
  Finish 门禁与 `verify resolve` 的 `next_` 指向 `task-replan`/重批/重检或异常归档。
- **AC3** 双轴 `pass` 缺 `basis` 在 `run_check_scope` 阶段即被拒（不执行验证命令）；
  执行后 notes 文件变化报 `WF_CHECK_STALE`；`run_check_finish` 不能产出会被
  `validate_check_result` 拒绝的 `pass`。
- **AC4** 暂停实例的当前任务有未登记未提交路径时，`writer release` 拒绝并列出路径；
  无未提交路径时仍可释放；已登记 `handoff.wip` 的既有行为不变。
- **AC5** 空 subject 且只有自身控制记录/回执路径时，`stop` 不再被「工作区有未提交差异」
  误拒；`keep`/`commit` 接受本任务 a∪e 路径，仍拒绝他人路径。
- **AC6** `states.json` 的 `check.from` 含 `finish`，`finish-invalidate` 同时登记
  `baseline-apply` 与 `spec-update`；C2/commit gate 的文本不再声称机制做不到的事实。
- **AC7** 历史故障逐项有「当前基线复现/反证 + 现有防线」；未覆盖项在台账中如实标注。
- **AC8** 隔离目标项目上完成 S1/S2/S3 的可执行验收；同会话、新会话、暂停/交接、
  无宿主标识四类分别有结果；发布/升级未跑的原因与影响如实记录。
- **AC9** 仓库要求的验证（定向单测、受影响 full runner 子集/全量、文档闸门、
  skills/doc-refs、pyc 清理）通过；最终 diff 与声明范围一致。

## 非目标

- 不推进 `wf` 版本、不重建发行树、不建 tag、不发布/推送、不改真实 `traffic_monitor`。
- 不新增 skill、命令、原因码或层级；不做与 S1–S4 无关的重构。
- 不实现复杂度路径 glob 交集判定、单 reviewer 跨轮复签、reviewer 报告状态自动翻转、
  长验证异步承载、`run` 记录组提交门禁接线等未影响本轮承诺的改进（登记边界/backlog）。
- 不替代人作规划批准、Check 结论、收工/提交、外发或残余风险接受。

## 需人裁 / 残余风险

- **C2 表述**：按 §1.1 既有口径，机制不能辨别人调/模型调；本轮选择**纠正 §1.3 与实现的
  「仅人调」表述**，不新增人证闸门（新增闸门会改变新终端并行的既有出口，属另一变更）。
- **升级预览 / 实际升级**：候选不是发行版；本轮不推进版本/发布，故无法在候选上验证真实升级。
  以隔离项目上的现有发行路径结果 + 明确「未跑候选升级」记录，不冒充。
- **单 reviewer 跨轮复签**：现行契约按轮绑定；本轮不改，登记为摩擦项。