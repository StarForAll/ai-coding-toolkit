# wf 两路 dogfood 缺陷复核与机制化修正

## Goal

对两份独立 agent 对 `docs/workflows/wf` 当前源码的问题分析（下文 a/b）与六轮 dogfood 会话证据做**质疑式复核**：把每条主张核成「真实缺陷 / 误判 / 已修复 / 设计候选」四态之一，再按设计稿 §1.1「判据句＋后置条件」把**能稳定计算且有消费点**的部分转成机制，其余落成就地指引或明确不做的设计观察。修正须结构性一次到位：不允许补丁式叠加、不允许引入新层级或新 skill、不允许留下半修状态。

## 背景（本任务的事实基线）

- 目标：`docs/workflows/wf`（当前目标版本 `0.0.17`）。源码 `payload/lib/wflib` 约 2.9 万行。
- 输入证据：
  1. 报告 a（P0/P1 七条 + 日常场景 + §1.1 判断）；
  2. 报告 b（机制/指引分工评估 + 交互时序缺陷 + 新问题清单 + §1.1 判断）。
  3. 六轮 dogfood 会话（`/tmp/traffic_monitor_{1..4}.md` 可读）。
- **证据缺口（如实登记）**：`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`（上一轮 dogfood 分析报告）与本机 `~/.zcode/cli/log/zcode-2026-11-08.jsonl` 在本机均**不存在**（`/tmp` 已无该两文件；zcode 日志目录只有 11-20 起的文件）。因此本轮复核以**当前源码 + 仓库内既有分析记录**（`analysis/dogfood-round5-dispositions.md`、`analysis/round-history.md`、`analysis/backlog-dogfood-round2.md`）+ 两份新报告为事实源，不引用缺失报告的任何结论。

## Requirements

### R1 复核纪律

- 每条主张必须落到**可复核的代码位置或已读记录**；不得以报告原文为准直接修正。
- 主张被证伪的，在 `design.md` 记「误判 + 依据」，不改代码。
- 主张属于设计契约变更（改变人的授权边界/承诺）而非缺陷的，记为待裁项，交人决定，不在本轮自行改契约。

### R2 机制/指引分工（承接设计稿 §1.1）

- 能把语义无歧义的事实按明确输入稳定算出的（归属、游标、引用身份、退出码、集合包含关系、提交存在性）→ 进机制，且必须写清消费点。
- 需要理解语境的（红绿是否验证同一行为、扩面是否实质、调查结论是否成立、审查结论）→ 留在**使用它的那一步**的 skill 判据位；机制只给事实与可执行出口。
- 不得为收束新增层级/新 skill；不得把判断指引集中到新文档。

### R3 结构性修正要求

- 同一判定只允许一处实现：本轮涉及的归属解析、外发/准备授权、复核保留规则、快照读取，若已有多处实现，收敛为一处并让所有入口消费它。
- 修正后的出口文案必须给出**当前事实下可执行**的下一步（不得指向已不存在的入口、不得指回循环、不得指向目标项目不可达的 authoring 文档）。
- 每处修正都要有能证伪它的用例（正向断言 + 至少一个注入式红模，沿用 `scripts/tests/wf_runtime` 既有风格）。

### R4 文档与指引同步

- 设计稿 §1.1 的表述须与修正后的机制一致（默认规则的授权分层、人签封闭清单的完整性、指令分工中"命令用法单一来源"的纪律）。
- 发行 skill 正文不得指向目标项目不可达的 authoring 文档；用户可见的机制出口文案同理。
- 改动若涉及行为契约，须同批更新 `payload/workflows/*.md` 与 README/round-history 的对应行，不留反向漂移。

### R5 交付边界

- 不提交、不推送、不建 PR：提交与收尾只在人明确同意后执行（本任务的人审点）。
- 不修改 charter 的不可削减项；不引入外部服务依赖；脚本仍只用标准库。

## Acceptance Criteria

- [ ] AC1 实例内任务（`run advance` 建出的任务）可从批准一路走到归档：`task-approve/start/pause/resume/replan/check/curate/knowledge/retrospect/attribute/archive/baseline-apply/spec-update/dep` 在 run 绑定下按「实例归属 + 游标指向」核验，非本实例或游标不指向时仍拒；实例内任务归档后实例写权与游标不被破坏，`run advance` 仍可继续记 satisfied。
- [ ] AC2 人判步骤记录答复、可略步骤记录 skipped 之后，下一次 `run advance` 推进到下一步而不是报 `WF_HISTORY_UNRESOLVED`；真正的游标损坏（任务步骤无映射、无结果）仍报该码。
- [ ] AC3 `task-check` 定稿段以锁内重读的记录为准：锁外执行期间同一会话写入的暂停/挂起、阶段或规划身份变化不会被覆盖，命中时报 `WF_CHECK_STALE` 并给出可执行出口。
- [ ] AC4 复杂度四项条件只报可证事实：把 `src/a.py` 扩成 `src/**` 判为扩面；同一批验收 id 但判据文本变化判为验收变化；`AGENTS.md` 托管块内容未变时不因路径命中判为契约面变化。
- [ ] AC5 TDD 证据绑定同一验证项：红运行须是同 `verification_id` 的历史失败运行、绿运行须是同 `verification_id` 的本次通过运行，跨验证项拼凑被拒；文档/调查类对象按**已批准**的适用性声明走独立可观察验证，缺声明仍要求红绿。
- [ ] AC6 零触碰面的纯调查任务不再被 `before_check` 循环卡住：已批准规划声明了验收项即可进入 Check，缺验收项时给出「回 Plan 补验收项重新批准」的出口。
- [ ] AC7 `definition prepare` 消费人的准备授权（决定文件）并记录授权来源与该授权绑定的范围；无授权时拒并给 `--authorization-draft` 骨架；同一范围重复 prepare 复用既有授权；`run create` 核到的准备记录带可核授权，不再自报 `source=human`。
- [ ] AC8 `gate --due after_archive` 可用且与 help 一致；`run finish/terminate/preview` 在快照缺失时报 `WF_HISTORY_UNRESOLVED`（不抛裸异常），`run terminate` 只读一次快照且在任何业务写入之前。
- [ ] AC9 参数解析不再把未注册 flag 当作前一个 flag 的值；人判答复的步骤 id 按整词匹配；`projection` 的归属决定按完整提交号匹配；sid 型身份的存活判定查真实进程事实（同 boot 内死亡可检出）。
- [ ] AC10 review 侧：并发 `review-context` 不再产生假失败（后到者复用已物化材料）；register-only 与正式判定共用同一份「复核不得静默丢 finding/降级」规则。
- [ ] AC11 死代码与 docstring 谎言清理完毕（`if True:`、`and False`、无调用方的兼容入口、重复赋值/导入、`_next_step` 行为说明），且清理不改变任何判定。
- [ ] AC12 出口文案与指引：异常归档任务的 advance 出口指向实例层可执行动作（`run terminate`/替换），不再让 AI 对已归档任务重跑 `task-abandon`；`run pause` 回显指向 `run resume`；用户可见文案不引用目标项目不可达的 authoring 文档；发行 skills 正文的 13 处 authoring 指针改为可达指针或删除。
- [ ] AC13 设计稿 §1.1 更新：默认规则写明「已授权调查与可逆准备」与「批准后受控写入」的分界；人签封闭清单补入 §4.2 基线/项目配置提案、`task-replan`、工作流定义准备授权与实例创建授权；指令分工补「入口用法只有一个描述面（`wf help` + 登记表）」的纪律。
- [ ] AC14 全量验证：相关 `scripts/tests/wf_runtime` 套件与新增/更新用例通过；`scripts/tests/wf_runtime/full/run_all.sh` 相关子集（含 `repro`）通过；`scripts/validate-wf-design.py` 与 `scripts/validate-skills.sh` 通过（文档改动时）。
- [ ] AC15 交付前不产生任何提交；工作树改动清单与本任务 `implement.md` 一致，无顺手重构。

## Notes / 人审点

- 人审点 1：本 prd/design/implement 起草完毕后由人确认范围（特别是 `design.md` §5 列出的「不在本轮」项）。
- 人审点 2：所有修改完成、验证通过后，提交与收尾须另行获得人的同意。