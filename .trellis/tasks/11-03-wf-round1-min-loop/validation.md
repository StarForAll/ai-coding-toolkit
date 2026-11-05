# 首轮实现验证记录（P5）

- 运行日期：2026-11-03（Asia/Shanghai）
- 宿主：单人本机；本会话宿主标识 `host_id=dsh`（wf 会话身份路径按机制稿 §1.4 由人声明 capability=verified）
- 解释器：目标项目解析到系统 `/usr/bin/python3`（Python 3.13.5）；authoring 工具用 `/softwares/python/bin/python3`（Python 3.14.7）
- git：git version 2.47.3
- 发行：`dev:a35ae34`（开发态部署）/ 打包发行 `0.1.0`，`rules_digest` 见下
- 夹具：/tmp 下临时目录（仓库外），F0=`/tmp/wf-fixtures/f0`、F1=`/tmp/wf-fixtures/f1`、F2=`/tmp/wf-fixtures/f2`；每个夹具均由脚本从零重建

## 0. 环境探测（审查 CLI）

| CLI | 版本 | 非交互调用 | 结果 |
|---|---|---|---|
| claude | 2.1.288 (Claude Code) | `claude -p` | **不可用**：`[claude-code:unrecognized_model] {"model":"step-5-preview[1M]"}` |
| codex | codex-cli 0.166.0 | `codex exec` | **可用**：产出 round-1 r2 协议报告（30,819 tokens） |
| dsh | 0.2.1-rc.2 | `dsh headless` | **不可用**：`MISSING_CREDENTIAL: llm-deepseek`（无可用 API key，未代配凭据） |

结论：本机只有 1 个可用的非交互 reviewer CLI，**不满足复杂任务「两个异种 reviewer」**；按机制稿 §6.4 记录，不降审查。

## 1. F0 全新项目（无 Git / 无基线）

夹具：`install.py` 从打包发行树安装（`refs/tags/wf-v0.1.0` → 提交、清单与资产哈希均校验通过；投放 54 个文件含 11 个 skill 副本），随后人执行 `confirm-executor --scope system`。

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 安装后启用（无 Git/无基线） | pass | WF_OK | PASS |
| 无 Git 时仍可创建规划 | pass（创建任务/起草规划不被阻断） | task-new ok | PASS |
| 批准初始化规划 | pass | WF_OK | PASS |
| 无 HEAD 时开工 | blocked WF_CAPABILITY_UNAVAILABLE | WF_CAPABILITY_UNAVAILABLE exit=1 | PASS |
| 人授权建立首个 HEAD | HEAD 存在且只含骨架 | 7c55b8fc | PASS |
| Git 就绪后开工 | pass | WF_OK | PASS |
| 初始化落盘骨架 | pass | WF_OK | PASS |
| Check pass | pass | WF_OK | PASS |
| 归档 | pass | WF_OK | PASS |

F0 汇总：9/9。归因：首轮实现缺陷已在这轮前修正（自检处理器探针、提交幂等）；无机制回修。

## 2. F1 存量无流程（初始化 → 普通任务）

- 初始化任务：`task-new(kind=initialize) → task-approve（light + 降级理由）→ task-start（consume_at=start 的 v0 实际执行）→ baseline-apply（基线/配置/spec 骨架）→ task-check（固定五步，v1 通过）→ task-knowledge(no-update) → 人 finish → archive`，全程 `WF_OK`；归档产生两个提交（业务组 + 归档组），归档记录保持 `persist_pending`，持久化由可达提交派生。
- 普通任务（新会话）：`task-new → approve → start → 实施 src/calc.py+tests → check → knowledge → finish → archive → writer release`，全程 `WF_OK`；`check.anchor` 固定、`task.check-passed`/`work-satisfied`/`knowledge-disposed` 回执齐全。

### 2.1 spec 生命周期（本地、无 MCP）

| case | expected | actual | pass |
|---|---|---|---|
| 批准 | pass | WF_OK | True |
| 开工 | pass | WF_OK | True |
| 新增（extracted） | pass | WF_OK | True |
| 策展引用 | pass | WF_OK | True |
| 读取正文并留痕 | complete=true 且写入本会话侧车 | complete=True codepoints=188 | True |
| 更新为 active（人核实日期） | pass | WF_OK | True |
| 改名（索引同步） | pass 且 index 指向新路径 | WF_OK | True |
| 删除未解除依赖 | needs_decision WF_SEMANTIC_DECISION（给三个出口） | WF_SEMANTIC_DECISION exit=2 | True |
| 解除依赖后删除 | pass 且文件移除、索引同步 | WF_OK removed=True | True |
| 合并写入目标文件 | pass | WF_OK | True |
| Check pass（spec 变更已入检查对象） | pass | WF_OK | True |
| 知识处置 updated | pass | WF_OK | True |
| 归档 | pass | WF_OK | True |

汇总：13/13。覆盖新增（extracted）/更新为 active/改名（索引与活动策展同步）/合并写入/删除未解除依赖被拒（`WF_SEMANTIC_DECISION`，给出三个出口）/解除依赖后删除（`spec.update` 的 `reference_dispositions`）。
未运行：拆分（split）未单独跑——本轮实现把拆分与合并都落成 `reference_dispositions` + 旧文件处置，合并已实跑；拆分的旧文件保留/停用分支未单独断言（原因分类：尚未安排）。

## 3. V1 宿主会话身份能力（F1v，capability 初值 unknown）

| case | expected | actual | pass |
|---|---|---|---|
| capability=unknown 时 enable | needs_decision WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED exit=2 | True |
| 维护预览更新 session_profile | 只更新安装记录（资产与数据未变） | True | True |
| verified 后 enable | pass WF_OK | WF_OK | True |
| task-new 一次完成写权获取+首次绑定+创建 | pass 且回显 generation 与 instance_id | task=2026-984cedb95b7d4d51880f82933ac4997d gen=3 inst=945403c35c72497998dce1cbc6545a2e | True |
| 重复调用 enable | pass（不重复绑定、不新建绑定） | WF_OK | True |
| 同一身份+同一实例标识（压缩后恢复） | position.task_id 指向原任务 | task_id=2026-984cedb95b7d4d51880f82933ac4997d | True |
| 实例标识不符（标识丢失/复制） | needs_decision WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED exit=2 | True |
| 暂停当前任务 | pass | WF_OK | True |
| 释放写权（合法终态/暂停后） | pass | WF_OK | True |
| 新会话按就绪对象 bind 接续 | pass 并回显新代次 | WF_OK gen=5 | True |
| 已绑定会话不能再建对象 | blocked WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | True |

汇总：11/11。归因：首次绑定/压缩后恢复/新会话接续/实例标识不符四条均按实现事实判定，无机制回修。未覆盖：真实压缩（宿主压缩事件未发生，以「同身份同实例标识重入」等价观察）与「身份能力未知时改用 wf 签发路径」的实跑（原因：本宿主未提供稳定 issued_id 携带通道，属环境未验证）。

## 4. V2 恢复协议跨记录组合（F1）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 归档后另一合法动作改写公共字段再独立进程重入 `archive` | 报告「归档已持久化」，不重复归档/提交 | `WF_OK`，`archive_persisted.persisted=true`（下界=动作 `head_before`，命中含归档记录的可达提交） | PASS |
| 归档提交不重复 | 同一任务仅一条 archive 提交 | `count=1` | PASS |

未覆盖：「归档提交成功但进程未报告」的崩溃点由人工构造（把动作留在 `persist_pending` 后重入）观察等价事实，未做真实进程 kill；原因分类：尚未安排。

## 5. V3 维护组与后续任务共存（F1）

| case | expected | actual | pass |
|---|---|---|---|
| 维护组未提交时创建并批准不重叠任务 | pass（reject: WF_ASSET_DECISION） | WF_OK | True |
| 不重叠任务开工（不带入维护组） | pass | WF_OK | True |
| Check pass（V2 准备） | pass | WF_OK | True |
| 不重叠任务归档（维护组仍待提交） | pass 且提交成功（reject: 捎带维护组） | WF_OK commit=True | True |
| 归档后释放写权（另一合法动作改写公共字段） | pass | WF_OK | True |
| 独立进程重入 archive | 报告「归档已持久化」，不重复归档/提交 | WF_OK persisted=True | True |
| 归档提交不重复 | 同一任务仅一条 archive 提交 | count=1 | True |
| 创建并批准重叠任务 | pass | WF_OK | True |
| 重叠任务开工 | blocked WF_WIP_UNRESOLVED | WF_WIP_UNRESOLVED exit=1 | True |
| 人处置维护组并回写 disposition | repair --dispose 写回回执 | OK  WF_OK | True |
| 处置后重叠任务恢复推进 | pass | WF_OK facts={"baseline_head": "b2b144444528aef68131e7c4edb8d189152e15d2", "control_assertion": {"anchor": "sha256:843e3f813c08ab664c | True |
| writer 整文件未被任务提交捎带 | 任务提交中不出现 .wf/writer.json（维护组提交另计） | task_commits_with_writer=0 | True |

汇总：12/12（含 V2 两行）。维护组回执由 dev-deploy 写入 `writer.maintenance_results`（`applied_pending_commit`）；重叠任务被 `WF_WIP_UNRESOLVED` 挡；人按「独立提交」处置后 `repair.py --dispose` 回写 disposition，读取侧派生 `disposed`，重叠任务恢复推进；任务提交中未出现 `.wf/writer.json`。

## 6. V4 复杂任务审查链路（F2）

| 步骤 | 实际 | 结果 |
|---|---|---|
| 复杂任务（改 `add` 对外契约，`complexity=complex`）Check pass | `WF_OK` | PASS |
| `review-launch`（槽位 r1=claude、r2=codex；实施 CLI=dsh；声明材料范围与外发授权） | `WF_OK`，输出两个暂存目录与可粘贴调用文本 | PASS |
| codex 作为 r2 产出协议报告并写入暂存目录 | 报告含唯一协议块、锚点、五轴结论，`verdict=fail`（真实发现：`add` 未提供默认参数，与验收 a1 不符） | PASS（真实审查生效） |
| claude 作为 r1 | `[claude-code:unrecognized_model]`，未产出报告 | **环境不足** |
| `review-import`（r2） | `WF_OK`，锚点核对通过并原子发布到任务目录 | PASS |
| 修改交付文件后重导同一报告 | `WF_REVIEW_INVALID`（`check-anchor mismatch`） | PASS |
| 依 finding 修复后重检、`review-launch` round 2 | `WF_OK` | PASS |
| `review-decide --unavailable`（人声明 + 证据：claude 模型错误、dsh 无凭据） | `WF_REVIEW_UNAVAILABLE`，`reviews.result.verdict=unavailable` | PASS（按 §6.4 留痕） |
| 复杂任务尝试正常归档 | `WF_REVIEW_INVALID`（`task.review-passed` 未满足） | PASS（不降审查） |
| 按 §6.4 异常退出（`task-abandon` + 逐项去向「保留现状」） | `WF_OK`，`terminal=abnormal` | PASS |

未运行：单 reviewer「人数不合格」派生分支（需要两份已导入报告，本机只有 1 个可用 reviewer，无法在不伪造报告的前提下构造）。原因分类：外部阻塞（审查环境）。

## 7. V5 调试计数与复盘（F1）

| case | expected | actual | pass |
|---|---|---|---|
| 准备：批准 | pass | WF_OK | True |
| 准备：开工 | pass | WF_OK | True |
| 首次 Check（验证失败） | blocked WF_CHECK_FAILED | WF_CHECK_FAILED exit=1 | True |
| 修复后重检 | pass | WF_OK | True |
| 单次 Check 内重试形态 | 每次 Check 每声明仅一条最终结果，重试不产生多条 failed 条目 | checks=2 failed_history=1 commands_in_pass=1 | True |
| 声明 Execute 期失败（合并累计 1+2=3） | pass 且记录 debug_declarations | WF_OK | True |
| 双源合并累计 | check_history failed(1) + counted(2) = 3 | [{"counted": 2, "dedupe_refs": [], "evidence_refs": ["handoff"], "verification_id": "v1"}] | True |
| 未裁定倍数阻断归档 | needs_decision WF_SEMANTIC_DECISION 且列 unruled_debug_multiples | WF_SEMANTIC_DECISION unruled=1 | [{'merged': 3, 'multiple': 1, 'threshold': 3, 'verification_id': 'v1'}] |
| 裁定「同一问题」留痕 | pass 且写入 human_decisions | WF_OK | True |
| 裁定后触发复盘要求 | blocked，缺 task.retrospective-done | WF_SEMANTIC_DECISION missing=['task.retrospective-done'] | True |
| 复盘记录覆盖触发集合 | pass | WF_OK | True |
| 复盘后归档 | pass | WF_OK | True |

汇总：12/12。判定口径：双源合并 = `check_history` failed 条目数 + 声明 `counted` 之和 − `dedupe_refs` 条目数；跨过阈值的每个整数倍须有 `debug-ruling-<vid>-<n>` 裁定，未裁定即阻断归档（`WF_SEMANTIC_DECISION`）；裁定「同一问题」转正为 `debug_repeat` 触发事实，复盘证据须覆盖当前全集。
未运行：`dedupe_refs` 双扣冲突与「同一失败事件已入 check_history 又被声明计入」的构造用例（原因分类：尚未安排；实现已按 `WF_SEMANTIC_DECISION` 拒绝双扣）。

## 8. 归因汇总

- 首轮实跑中发现的缺陷全部落在**实现层**并已修正：目录/路径 join、代理参数解析、模板标记未拦截、治理面空 `paths` 误判不可用、git 路径引号化导致可达提交查证失配、提交不幂等、spec 改名未同步策展引用、归档重入需写权、`review_fail` 触发源错置。
- 没有出现「实现正确但事实不足以判定」的条目，因此本轮**未回修机制稿**。
- 环境层事实：claude 与 dsh 的非交互能力不可用，已按 §6.4 记录，不构成机制回修依据。

## 9. 实现稿按实跑结果的更新与重绑

按任务要求，实现稿 §7.1 的「未运行」表述已按本轮实跑结果更新（同时更新 §0 的验证纪律、§7.3 的实跑状态、§9.1 的未做项状态与 §9.2 的冻结行）：

- 修订前绑定：`sha256 051aade51681f9b33ba7fbf2e21c44f20045c273772f796caa72c4f1e7e4d952`（738 行）
- 修订后：`sha256 0505cb8d37374da0f2662d6ec362dd19eda9186d0f0354b1715c7680fcb08b52`（742 行）
- 属实现稿内容变更：**须由未参与本次运行的会话复审后才可称定稿**；本文本次未改动 charter、设计稿、索引、来源说明与机制稿。

## 10. 版本与环境复现

```
python3 scripts/build-wf-release.py --version 0.1.0     # 产物见 docs/workflows/wf-release/
python3 scripts/build-wf-release.py --verify           # OK: byte reproduction (0.1.0, 55 assets)
python3 scripts/build-wf-release.py --verify-token-parity  # OK
python3 install.py --target <abs> --release-ref refs/tags/wf-v0.1.0 \
    --source <已检出发行目录> --skill-root <abs> --confirm --host-id dsh --verify-capability
```

最终发行标识（本次生成，凡源树改动须重建）：`rules_digest = sha256:c6239b9b685cec29c3514a4dfbf816ee5f49d01e3473686784249c58ad293502`。

## 11. 评审复核后的未运行 / 部分交付登记（2026-11-03）

外部评审复核（见同目录 `review-reconciliation.md`）确认：以下能力**已交付命令面但未接线或未验证**，此前未在本记录登记，违反「未运行必须写原因分类」判据。逐条补记：

| 项 | 状态 | 实际事实 | 原因分类 | 归属轮次 |
|---|---|---|---|---|
| `plan.equivalences` 等价链归一（机械修订不重复批准） | **未实现** | 字段只在任务创建时初始化（`tasks.py:143`），`compute_plan_version`/`check_anchor`/回执 P 均不归一；PRD 改错字会强制重批 | 尚未安排 | 首轮收口前补（机制稿 §12.3「机械修订不重复批准」场景） |
| activation 核验 / `WF_NOT_ENABLED` | **未实现** | `WF_NOT_ENABLED` 仅存在于码表；会话类子命令不核 activation | 尚未安排 | 首轮收口前补（机制稿 §1.4/§2.1） |
| `debug_repeat_threshold` 项目配置 | **已接线（§44 更新）** | 由 `config.value_of` 读取并阻断非法值，归档门禁的调试分支按该值判定（R58 用例覆盖） | 已完成 | — |
| F2 专属：Trellis「有效指令」与「纯残留」两分支 | **未运行** | 当前实现对任何 `TRELLIS:START` 一律 `WF_FLOW_CONFLICT`，未构造两分支 | 尚未安排（且实现缺「适用性未知」档，见复核 A14） | 首轮收口前补跑 + 修档位 |
| F2 专属：与其他流程共存 + 外部提交处置 | **未运行** | F2 只跑了 V4 审查链路；未验证「无交集外部提交不阻断、影响检查对象时失效重检」 | 尚未安排 | 首轮收口前补跑（机制稿 §12.3 F2 绑定场景） |
| `spec_verify_days` / `spec_reclaim_tasks` / `inspection_every_tasks` | **已接线（§64 更新）** | `spec_verify_days` 由 Check 消费；`spec_reclaim_tasks` / `inspection_every_tasks` 由 `inspect` 的治理面消费（spec 复用回收候选、按归档任务数的周期触发，R75 用例覆盖）；`inspect` 另含归档终态与记录 id 一致性断言 | 已完成 | — |
| `task-abandon` 异常归档后的持久化查证 | **已交付（§64 更新）** | 放弃路径用 `_record_committed` 核「记录目录已入提交且无未提交差异」，失败即 `WF_PERSISTENCE_FAILED` 并提示持权重入续做（R31 实跑覆盖）；`archive_persisted` 是 normal 归档的可达提交查证，两者判据不同、各自适用 | 已完成 | — |
| 交接 `transfer` / 反向修正 `reverse` 的承接与完成核验 | **部分交付** | `stop` 只核 decision 存在与条数 | 尚未安排 | 第二轮（依赖建边/替换入口） |
| 治理面见证枚举排除 `.wf` 等前缀 | **已知偏差（不修）** | 只会让条件①偏保守取 complex，不会放行 | 场景不适用 | 不修，仅登记 |
| 单 reviewer「人数不合格」派生分支 | 未运行 | 本机只有 1 个可用非交互 reviewer（codex）；claude `unrecognized_model`、dsh 缺凭据 | 外部阻塞 | 待审查环境具备后补 |
| 真实压缩事件 / wf 签发路径 | 未运行 | 以「同身份同实例标识重入」等价观察 | 宿主能力未验证 | 待宿主核实 |
| 真实进程崩溃点（归档提交后未报告） | 未运行 | 以动作停留 `persist_pending` 后重入的等价事实观察 | 尚未安排 | 首轮收口前补故障注入 |
| `dedupe_refs` 双扣冲突构造 | 未运行 | 实现已按 `WF_SEMANTIC_DECISION` 拒绝，未构造用例 | 尚未安排 | 首轮收口前补 |
| spec 拆分（split）的旧文件停用/保留分支 | 未运行 | 合并已实跑；拆分沿用同一 `reference_dispositions` 面 | 尚未安排 | 首轮收口前补 |

## 12. CP1（结构核验与交接/收工/放弃前置）实跑记录（2026-11-03）

环境同上（`/usr/bin/python3 3.13.5`；夹具 `/tmp/wf-fixtures/f1` 由脚本重建；发行 `0.1.0` 重新打包，`rules_digest=sha256:085d568a…`）。

### 12.1 CP1 新增用例（20/20）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A5 开工回执不含非法 reused | 无 reused∧completed_ref=null | reused_null=0 | PASS |
| A5 spec-loaded 写 completed | result=completed | completed | PASS |
| A15 批准（含答复） | pass | WF_OK | PASS |
| A15 开工核 plan-q 覆盖 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A10 无 Decision 的 manual | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| A10 choice 非枚举不得通过 | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| A10 显式 passed 通过 | pass | WF_OK | PASS |
| A10 记录绑定锚点与 plan.version | command/acceptance 均带锚点 | bound=True | PASS |
| A11 检查期间对象变化 | WF_CHECK_STALE | WF_CHECK_STALE | PASS |
| A12 Check 通过（finish 项延后） | pass | WF_OK | PASS |
| A12 归档前核 finish 就绪 | WF_VERIFICATION_UNREADY | WF_VERIFICATION_UNREADY | PASS |
| A18 批准 | pass | WF_OK | PASS |
| A18 降级缺证据阻断 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A21 未保存进度即交接 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A22 keep 含范围外路径 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| A22 commit 授权未覆盖 | WF_COMMIT_NOT_AUTHORIZED | WF_COMMIT_NOT_AUTHORIZED | PASS |
| A22 transfer 承接对象不存在 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A23 无 disposition 出预览 | WF_SEMANTIC_DECISION 且含 preview.uncommitted | WF_SEMANTIC_DECISION uncommitted=2 | PASS |
| A23 去向未覆盖全部未提交路径 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| A23 覆盖全部后异常归档 | pass | WF_OK | PASS |

### 12.2 回归（改动后重跑）

| 套件 | 结果 |
|---|---|
| 初始化任务闭环（`f1_init`） | 8/8 `WF_OK` |
| 普通任务闭环（`f1_ordinary`） | 8/8 `WF_OK` |
| V1 身份与绑定 | 11/11 |
| V2 归档持久化派生 | 2/2 |
| V3 维护组共存 | 8/8 |
| V5 调试计数与复盘 | 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0 自举与 Git 就绪（`install.py` 从打包发行树安装） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 12.3 CP1 期间新发现并一并修正的缺陷

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-CP1-1 | 问题提取把临时键写进任务记录 | `cmd_task_approve` 用 `_attach_questions` 返回的副本直接 `save_task`，导致 `task.json` 出现 `_prd_text`（整份 PRD）与 `_questions`；夹具里已可见 | 改为纯函数 `plan_questions(root, task)` / `unanswered_plan_questions(root, task, decisions)`，不再产生临时键（A15 范围内） |
| N-CP1-2 | 收工自授权 | `stop_work` 把 `decisions` 中所有 `choice=commit` 计入授权，包含收工选择本身 ⇒ 提交授权恒成立 | 授权改取 `decisions[1:]`；收工选择只表示选择（A22 范围内） |
| N-CP1-3 | 门禁回执短路 | `gates.evaluate` 一旦找到 completed 回执就不再 `verify_step`，plan-q 覆盖等活事实被跳过 | 门禁一律先 `verify_step` 再采信回执；回执只作证据（A15 范围内） |

以上三条都属「实现漏判」，不需要回修机制稿；`N-CP1-3` 的改法依据机制稿 §11.2「gate.evaluate 重核实际产物、版本与完成判据」。

## 13. CP2（接线：等价链 / activation / 阈值 / Trellis 档位）实跑记录（2026-11-03）

环境同上；发行重新打包后 `rules_digest=sha256:adbcb4e8…`。

### 13.1 CP2 新增用例（14/14）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A3 缺 activation 的开工 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| A3 带 activation 的开工 | pass | WF_OK | PASS |
| A3 只读查询无需 activation | pass | WF_OK | PASS |
| A2 改错字后未接链即重批 | WF_APPROVAL_MISSING 或语义变化提示 | WF_SEMANTIC_DECISION | PASS |
| A2 机械修订接链 | pass 且 normalized=approved | WF_OK norm=True | PASS |
| A2 等价链已记录 | equivalences 长度 1 | 1 | PASS |
| A2 机械修订不改变锚点 | anchor 前后相同且重检通过 | same=True rc=0 | PASS |
| A2 语义变化拒绝机械修订 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A13 首次重检通过（历史 1 次失败） | pass | WF_OK | PASS |
| A13 阈值 2 时合并累计 2 触发待决 | WF_SEMANTIC_DECISION 且 threshold=2 | WF_SEMANTIC_DECISION threshold=2 | PASS |
| A14 仅数据线索 | pass（附警告） | WF_OK warnings=1 | PASS |
| A14 托管块适用性未知 | needs_decision WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION exit=2 | PASS |
| A14 当前宿主可适用的 hook 配置 | blocked WF_FLOW_CONFLICT | WF_FLOW_CONFLICT exit=1 | PASS |
| A14 他宿主配置的适用性未知 | needs_decision WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION exit=2 | PASS |

### 13.2 回归（CP2 改动后重跑）

| 套件 | 结果 |
|---|---|
| CP1 结构核验套件 | 20/20 |
| 初始化任务闭环 | 8/8 `WF_OK` |
| 普通任务闭环 | 8/8 `WF_OK` |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0 自举与 Git 就绪（新发行树安装） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 13.3 CP2 期间新发现并一并修正的缺陷

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-CP2-1 | 机械修订被「仅 plan 阶段可批准」挡住 | `cmd_task_approve` 在识别机械修订之前先判阶段；任务进入 execute/check/finish 后无法为「改错字」接等价链，实际场景（开工后修 PRD 错字）不可达 | 机械修订判定提前到阶段检查之前；机械修订只改 `plan.version`+`equivalences`，不改阶段、不写批准（A2 范围内） |
| N-CP2-2 | 阈值读不到项目配置 | `debug_pending` 硬编码 3（A13 本体） | 由 `Context.debug_threshold()` 读 `debug_repeat_threshold`，读不到用发行缺省（A13） |

### 13.4 等价链的实际语义（实现口径，便于复审）

- 批准时写入 `plan.approved_version`；机械修订把新版本接到链上、把 `plan.version` 前移，`approved_version` 不变。
- 归一：沿 `equivalences` 的 `new_version → old_version` 回溯到 `approved_version`；链断裂、缺 Decision、Decision 的 `choice` 不是 `机械修订`、出现环，都返回当前版本（即不归一）。
- 消费点：`check_anchor` 的 `plan_version`、回执 P 的 `plan_version`、门禁的版本比对；`acceptance_digest` 仍取批准值。
- 进入机械修订前核两端同义：规范化 `touch_paths` 集合相等且验收摘要相等；不等即 `WF_SEMANTIC_DECISION`（回 Plan 重新批准）。

## 14. CP3（提交范围 / 审查 attempt / 执行器 / 分派表 / rules_digest 单源）实跑记录（2026-11-03）

环境同上；发行重新打包后 `rules_digest=sha256:29a052bf…`。

### 14.1 CP3 新增用例（17/17）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A6 准备：Check 通过 | pass | WF_OK | PASS |
| A6 归档成功（subject 为数组） | pass | WF_OK | PASS |
| A6 业务提交不含预暂存文件 | notes.txt 不在业务提交中 | in_business=False | PASS |
| A6 归档提交不含预暂存文件 | notes.txt 不在归档提交中 | in_archive=False | PASS |
| A6 预暂存内容保持原状 | notes.txt 仍处于暂存区 | ['M'] | PASS |
| A6 未覆盖交付的授权被门禁挡住 | WF_WIP_UNRESOLVED 或 WF_COMMIT_NOT_AUTHORIZED | WF_WIP_UNRESOLVED | PASS |
| A7 round 1 发起 | pass | WF_OK | PASS |
| A7 round 2 发起 | pass | WF_OK | PASS |
| A7 两轮落在同一 attempt | attempts=[{number:1,round_ids:[1,2]}] | [{"number": 1, "outcome": null, "rework_ref": null, "round_ids": [1, 2]}] | PASS |
| A7 第三轮被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A9 全局键须为绝对路径 | WF_EXECUTOR_UNCONFIRMED | WF_EXECUTOR_UNCONFIRMED exit=1 | PASS |
| A9 项目键不得越出项目根 | WF_PATH_INVALID | WF_PATH_INVALID exit=1 | PASS |
| A9 项目配置损坏不静默回退 | WF_EXECUTOR_UNCONFIRMED | WF_EXECUTOR_UNCONFIRMED exit=1 | PASS |
| A16 分派表与命令面一致 | 无问题 | 0 problems | PASS |
| A16 未登记步骤被拒 | 报 no fixed handler | [{'required_step': 'control.repair.apply', 'reason': 'handler entry missing: repair'}, {'required_step': 'control.uninstall.apply', 'reason': 'handler entry missing: uninstall'}, {'required_step': 'task.unknown-step', 'reason': 'no fixed handler'}] | PASS |
| A16 未声明处理器被拒 | 报 handler not declared | 3 | PASS |
| A17 两处 rules_digest 一致（含非 ASCII 路径） | 相同摘要 | same=True | PASS |

### 14.2 回归（CP3 改动后重跑）

| 套件 | 结果 |
|---|---|
| CP1 / CP2 套件 | 20/20 / 14/14 |
| 初始化任务闭环 / 普通任务闭环 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0（新发行树安装 + 自举） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 14.3 CP3 期间新发现并一并修正的缺陷

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-CP3-1 | 提交后回读受路径引号干扰 | `git show --name-only` 对非 ASCII 路径加引号转义，`extra` 判定把正常的归档提交判成「授权外内容」 | 所有提交相关 git 调用加 `-c core.quotePath=false`（与 `scope.py` 同口径） |
| N-CP3-2 | 归档记录提交重复带入业务授权 | 记录组提交把 grant 路径再带一遍；业务提交后 glob 已无匹配 → `WF_PATH_INVALID`，归档半途停下（目录已移动、记录未提交） | 记录组提交只含记录目录本身；提交后按 glob 覆盖核对残留差异 |
| N-CP3-3 | 部署自检 `join()` 参数错误 | `join(target, ".wf/bin", name)` 用了两参版本 → 部署自检抛异常，夹具停在维护持有态 | 改为单段相对路径 |
| N-CP3-4 | 授权 glob 语义缺失 | 人写 `.wf/spec/**` 时无法提交（与「按精确路径提交」冲突） | 授权可写 glob，提交前按当前未提交集合展开为精确路径；无匹配不报错，残留由归档/收工后的差异核对兜底 |

### 14.4 CP3 后的提交语义（实现口径，便于复审）

- 业务组与记录组分开提交：业务组 = 授权 Decision 的 `subject`（数组或 `,;/换行` 分隔），记录组 = 归档目录本身。
- `git commit -m … -- <paths>`：路径限定提交，索引中的其他内容不进入本次提交；提交后回读 `git show --name-only` 并要求 ⊆ 授权集合。
- 提交后核对：归档要求授权组与记录目录无残留差异（有则 `WF_PERSISTENCE_FAILED`）；收工要求授权路径无残留差异。
- 非 ASCII 路径全程 `core.quotePath=false`。

## 15. CP4（前置核验 / spec 模板 / 卸载偏离 / spec 输出）实跑记录（2026-11-03）

环境同上；卸载用例使用独立夹具 `/tmp/wf-fixtures/fu`（skill 根 `/tmp/wf-fixtures/skills-u`），restore 后由部署脚本重建。发行重新打包后 `rules_digest=sha256:cc57239a…`。

### 15.1 CP4 新增用例（15/15）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A1 准备：被放弃的前置任务 | pass | WF_OK | PASS |
| A1 开工核前置（异常归档） | WF_DEPENDENCY_UNMET | WF_DEPENDENCY_UNMET | PASS |
| A1 归档门禁核前置 | WF_DEPENDENCY_UNMET | WF_DEPENDENCY_UNMET | PASS |
| A4 模板 frontmatter 可解析 | problems 为空且 metadata 含 status/author | problems=[] errors=[] | PASS |
| A19 非 JSON 模式只输出正文 | stdout 为文件正文，无结果头 | header=False stderr_lines=1 | PASS |
| A19 --json 输出结构 | tier=pass 且 facts.content 存在 | pass has_content=True | PASS |
| A8 预览列出本地偏离 | 列 2 项偏离 | count=2 | PASS |
| A8 预览给出令牌 | 32 位十六进制 | 8749e7bb | PASS |
| A8 卸载应用成功 | WF_OK | wf 卸载预览（未写入任何文件） | PASS |
| A8 偏离的 skill 未被删除 | 文件仍存在且含本地修改 | True | PASS |
| A8 偏离的项目资产未被删除 | 文件仍存在 | True | PASS |
| A8 未修改的资产被移除 | .wf/bin/wf.py 已移除 | True | PASS |
| A8 保留项写入报告 | preserved 含 2 项 | 2 | PASS |
| A8 数据与安装记录保留 | .wf/install/installation.json 与 writer.json 仍在 | True | PASS |
| A8 托管段移除且保留 /.wf-lock 裸行 | .gitignore 无标记串但含 /wf-lock 行 | ['/.wf-lock'] | PASS |

### 15.2 回归（CP4 改动后重跑）

| 套件 | 结果 |
|---|---|
| CP1 / CP2 / CP3 套件 | 20/20 / 14/14 / 17/17 |
| 初始化任务闭环 / 普通任务闭环 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0（新发行树安装 + 自举） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 15.3 CP4 期间新发现并一并修正的缺陷

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-CP4-1 | 预览令牌跨进程必然失效 | `repair.py` / `uninstall.py` 的 `--apply` 分支先 `issue(preview)` 生成新 nonce，再拿它校验人给的令牌 ⇒ 永远 `WF_PREVIEW_STALE`；机制稿 §10.3 本就要求「令牌只在同一交互进程内有效」 | 预览与确认合并为同一进程：先打印预览与令牌，再读终端输入；`--nonce` 仅测试形态注入。`repair --apply` 与 `uninstall --apply` 均已实测通过 |
| N-CP4-2 | 卸载默认会删掉用户改过的资产 | 原实现按清单 `os.remove`，仅记录 `expected` 不比对 | 逐项比对发行摘要：偏离项默认保留并列入报告；同目录未知文件只列不删；报告给出「保留本地偏离 N 项」 |

### 15.4 卸载的默认语义（实现口径）

- 只移除「与发行摘要一致」的登记资产；偏离项保留并在预览/结果里逐项列出（含原因）。
- 同目录未知文件不认领、不改名、不删除，只在预览里列出。
- 项目数据、`.wf/install/`、`.wf-lock` 与 `.gitignore` 中的 `/.wf-lock` 裸行保留；托管段整段移除。
- 清理顺序仍由人执行：确认无 wf 进程 → 删 `.wf-lock` → 删 `/.wf-lock` 行。

## 16. CP5（B 组补跑：F2 分支、崩溃点、dedupe、拆分）实跑记录（2026-11-03）

环境同上。F2 夹具由 `f2_setup.sh` 重建（含 `.trellis/` 残留言据与一条无任务标记的外部提交）；F1 用于 B3/B4/B5。

### 16.1 CP5 新增用例（16/16）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| B1 纯残留数据可启用 | pass + 警告 | WF_OK warnings=1 | PASS |
| B1 托管指令块（适用性未知） | needs_decision WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION exit=2 | PASS |
| B1 当前宿主可适用配置（有效指令） | blocked WF_FLOW_CONFLICT | WF_FLOW_CONFLICT exit=1 | PASS |
| B2 批准 | pass | WF_OK | PASS |
| B2 开工（含外部提交历史） | pass | WF_OK | PASS |
| B2 外部提交（触碰面内）不阻断 Check | pass | WF_OK | PASS |
| B2 外部提交被列入检查事实 | 列出该提交 | ['d81c2c6e'] | PASS |
| B2 无交集的外部提交不入列 | 只列与触碰面相交的提交 | count=1 | PASS |
| B4 重检通过（历史 1 次失败） | pass | WF_OK | PASS |
| B4 同一失败事件重复计入被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| B4 双扣后合并累计=2（1+2-1） | WF_SEMANTIC_DECISION 且 merged=2 | WF_SEMANTIC_DECISION merged=2 | PASS |
| B5 建被拆分条目 | pass | WF_OK | PASS |
| B5 拆分应用 | 3 条变更且原文件移除 | WF_OK applied=3 old_gone=True | PASS |
| B5 索引同步新条目、移除旧条目 | index 含 pure/effects、不含 combined | pure=True effects=True combined=False | PASS |
| B3 归档提交后被强杀 | 进程被 SIGKILL（提交已落地、结果未报告） | killed=True rc=-9 | PASS |
| B3 独立进程重入报告已持久化 | WF_OK 且 persisted=true、不重复归档 | WF_OK persisted=True commits=1 | PASS |

### 16.2 回归（CP5 后全量重跑）

| 套件 | 结果 |
|---|---|
| CP1 / CP2 / CP3 / CP4 | 20/20 / 14/14 / 17/17 / 6/6 (+卸载 9/9) |
| 初始化任务闭环 / 普通任务闭环 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F2（Trellis 分支 + 共存/外部提交） | 8/8 |
| F0（新发行树安装 + 自举） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过（`rules_digest=sha256:cc57239a…`） |

### 16.3 B3 崩溃点的实测事实

归档以子进程运行；父进程轮询 `git log`，在归档提交出现后立即 `SIGKILL`。实测进程被强杀（`rc=-9`），随后**新进程**重入同一归档动作：`WF_OK` 且 `archive_persisted.persisted=true`、同一任务只有一条 `wf: archive` 提交 —— 即「提交已落地、结果未报告」的恢复路径成立。

### 16.4 实现稿重绑（E 组）

- 修订前：`sha256 0505cb8d…`（742 行）
- 本次修订：§7.3 的未运行清单与处置状态（A/B 完成、C 待裁、复审待安排）
- 修订后：`sha256 2923a82a649ba17018d7a235f9790319ca618665ac9a710d80251cea2f02d8c9`（744 行）
- 独立复审：**待安排**（须由未参与本轮修订的会话执行；未复审前只作实现阶段记录）

### 16.5 仍未闭合的项

| 组 | 项 | 状态 |
|---|---|---|
| C | `repair --dispose` 是否取令牌（N8） | 待人工裁定；复核建议纳入令牌（理由见 `review-reconciliation.md` §5） |
| C | 归档提交顺序的表述（F6） | 待人工确认「维持设计稿 §4.2」；代码不再变更，仅补文档依据 |
| D | 真实压缩事件 / wf 签发路径 | 等宿主能力核实（不阻塞收口，按「未运行 + 原因」保留） |
| D | 单 reviewer「人数不合格」派生分支 | 等第二个可用非交互 reviewer（外部阻塞） |
| E | 独立复审 | 待未参与修订的会话执行 |

## 17. N8 裁定落地：`repair --dispose` 纳入令牌（2026-11-03）

按人裁定「N8 按建议执行」，`repair --dispose` 改为与 `--apply` 同一套「预览 → 终端令牌 → 同进程应用」流程。

### 17.1 实测

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| `--dispose` 只预览 | 列出目标回执、当前写权状态与处置内容，给出摘要与令牌，不写文件 | 预览输出含 `回执/写权状态/处置/摘要/令牌`；`writer.json` 未变 | PASS |
| `--apply` 给错误令牌 | `WF_PREVIEW_STALE`，不写文件 | `BLOCKED WF_PREVIEW_STALE`，回执 disposition 仍为 null | PASS |
| `--apply` 给正确令牌（测试形态注入 nonce） | `WF_OK`，只写 `disposition` 字段 | `OK WF_OK`；回执 disposition 有值，`holder/generation` 未变 | PASS |
| 写权仍被持有时回写 | 允许（互斥由同一最小锁保证，只改 disposition） | V3 场景中重叠任务持有写权仍能处置并恢复推进 | PASS |

### 17.2 回归

V2/V3 12/12（含改用令牌的处置步骤）；CP1 20/20；CP2 14/14；CP3 17/17；CP4 6/6；普通任务 8/8；V5 12/12；F1 spec 13/13；V1 11/11；F0 9/9；`--verify` 与 `--verify-token-parity` 通过（`rules_digest=sha256:67d89ad3…`）。

### 17.3 口径说明

- 处置回写只改该回执的 `disposition` 字段，不改 `holder`/`generation`/资产，因此不要求写权空闲；互斥由 `.wf-lock` 的最小锁保证。
- 令牌仍只在同一交互进程内有效；`--nonce` 仅为测试形态注入。
- 实现稿 §4.6 的对应表述待与 F6 一并改一次并重绑（见 `pending-decisions.md`）。

## 18. 人裁落地与 D2 探测（2026-11-03）

### 18.1 F6（按建议执行：维持设计稿 §4.2 顺序）

实现稿新增 §2.3.1「归档动作的提交顺序」，写明：业务组提交 → 最终门禁 → 终态/移动 → 记录组单独提交；依据设计稿 §4.2；门禁失败中间态可恢复（续做、幂等、不重复归档）；并注明不按机制稿 §5.3 字面重排的理由（否则门禁失败也先提交业务，与设计稿相反）。代码零改动。

### 18.2 N8 的文档表述

实现稿 §4.5.1 补一条：`repair.py --dispose` 与 `--apply` 走同一套预览与令牌，只改 `disposition` 字段，不要求写权空闲（实测见 §17）。

### 18.3 重绑

- 修订前：`sha256 2923a82a…`（744 行）
- 第一次修订（§2.3.1 + §4.5.1）：`sha256 daf341a6…`（753 行）
- 最终修订（§7.3 的处置状态改为终态）：`sha256 54e2a58a7ad82ebeeca4c89af5a79c6957aa498d3b4b5c1a114049a767151d20`（753 行）
- 独立复审：按人决定「暂不执行」；实现稿状态保持「实现阶段记录，未定稿（复审待安排）」。

### 18.4 D1（按建议：保持未运行）

真实压缩事件与 wf 签发路径仍按「未运行 + 宿主能力未验证」登记（§16.5），本轮不注入伪造状态。

### 18.5 D2 探测结果：pi / zcode 不可用于非交互审查

| 探测 | 结果 |
|---|---|
| `pi --print --model glm-5.3-flash` | `401 Invalid token`（上游拒绝） |
| `pi --print --provider xzc-1 --model glm-5.3-flash` | 同上 `401 Invalid token` |
| `pi --print --provider xzc-1 --model glm-5.3` / `qwen3.8-max` | 同 provider 下其他模型同样 `401` |
| `pi auth check --provider xzc-1 --json` | `{"status":"ready","authType":"api_key"}`——本地认为就绪，**上游判为无效**，属凭据失效 |
| `zcode --help` / `--version` | 启动 Electron 桌面应用（输出为启动日志），无 print/headless 子命令；`~/.zcode/cli` 是数据目录（agents/artifacts/exec/log/rollout），不是 CLI 入口 |

结论：D2 的「第二个可用非交互 reviewer CLI」在本机仍不成立；`glm-5.3-flash` 的访问凭据被上游判为无效（本地状态显示就绪），需由人刷新该凭据后才可补跑。zcode 为桌面应用，无脚本化审查入口。
补跑条件（凭据就绪后）：用同一 `f2_setup.sh` 建夹具 → 初始化 → 复杂任务 Check pass → `review-launch`（slots: codex + pi/glm-5.3-flash）→ 两方各出报告 → 双导入 → `review-decide` 预期 pass；另建一个复杂任务，两个槽位都用 codex 出报告 → `review-decide` 预期 fail（人数不合格）。

### 18.6 E（按人决定暂不执行）

独立复审未执行；实现稿保持「实现阶段记录」，复审主体与覆盖轴留待人安排。

## 19. D2 复验：pi / glm-5.3-flash 与两处审查分支（2026-11-03）

### 19.1 凭据刷新后探测

`pi --print --provider xzc-1 --model glm-5.3-flash "Reply with exactly: WF_PROBE_OK"` → `WF_PROBE_OK`（此前同一调用返回 `401 Invalid token`）。pi 可作为第二个非交互 reviewer CLI。

### 19.2 两异种 reviewer 全链路 pass（F2，任务 `2026-5218e6b8…`）

| 步骤 | 实际 |
|---|---|
| 复杂任务（改 `add` 对外契约，`complexity=complex`）Check pass | `WF_OK`，锚点 `0192c087…` |
| round 1：codex（r1）+ pi（r2）各出报告 | codex 报告 `verdict=fail`，**真实阻断发现**：`add(a,b,*rest)` 在空 `rest` 时多算 `+0`，两参数的字符串/列表调用被破坏；pi 首次运行因工作目录未锚定项目根，按 SKILL 纪律停止并回报 `verdict=unavailable`（材料不足即停止，符合预期） |
| 按发现修复 + 重检 | 改为逐项累加并补字符串/多参数测试；新锚点 `df08d0f7…` |
| round 2：codex（r1）+ pi（r2）重新审查 | 两份报告均 `verdict=pass`，`source-cli` 分别为 `codex`/`pi`，锚点与当前 Check 一致 |
| 双导入 + `review-decide --round 2` | `WF_OK`，`verdict=pass`，`reviewer_clis=['codex','pi']` |
| 人 finish + 归档 | `WF_OK`，`terminal=normal`，业务组与记录组提交成功 |

同一实施尝试两轮（`attempt=1`，`round_ids=[1,2]`），与 A7 的两轮上限一致。

### 19.3 同一 CLI 双槽位 → 人数不合格（F2，任务 `2026-cdd60797…`）

| 步骤 | 实际 |
|---|---|
| `review-launch`（slots 都为 codex） | `WF_OK`（launch 只核「不与实施 CLI 重叠」） |
| 两个 codex 槽位各出报告 | 两份均为合法协议报告，`source-cli=codex`；因该任务已无可审 diff，两份报告自报 `verdict=unavailable`（测试构造，非框架问题） |
| 双导入 + `review-decide` | `WF_REVIEW_INVALID`，`verdict=fail`，`reason=人数不合格：需要两个彼此不同的审查 CLI`，`reviewer_clis=['codex']` |

### 19.4 过程中观察到的两条事实

1. **reviewer 写项目树**：pi 在项目根运行时由其扩展写出了 `.unipi/config/settings-version.json`，随后下一任务的 `task-start` 以 `WF_WORKSPACE_UNRESOLVED` 挡住并列出该路径——工作区边界核验按设计生效；该产物已移除。审查 skill 要求「不写项目树」，说明 pi 侧需禁用该扩展或改在项目外运行，属环境注记，不改框架。
2. **材料不足即停止**：pi 在无法锚定审查对象时回报 `BLOCKED` 并在报告里逐轴写 `unavailable`，没有扩大读取范围——与 V4「reviewer 在材料不足时停止回报而非 pass」的预期一致。

### 19.5 复验后的状态

- D2 关闭：两异种 reviewer 全链路 pass 与「人数不合格」分支均有实跑结果。
- 仍未运行只剩 D1（真实压缩/签发路径，按人决定保留）。
- 实现稿 §7.1 的 V4 行与 §7.3 的 D 组表述按本节更新，绑定见 §19.6。

### 19.6 重绑

- 修订前：`sha256 54e2a58a…`（753 行）
- 修订后：`sha256 bbdcef62f22b02d2607762e9ecb561c74e2ab35d8f1909ec57d5bcd90b877b1b`（753 行）

## 20. 第二轮评审的登记（2026-11-03，复核见 `review-round2-reconciliation.md`）

复核结论：R1（跨文件写入与接续）、R2（`confirm-executor` 交互闸门）、R5（正式记录形态下的卸载）成立；R3（锁标记）部分成立（空文件自愈，部分标记只有人工出口，未验证）；R4/R6 部分成立且以文档/登记为主（P1–P5 是阶段不是轮次；`dedupe_refs` 已在 §16.4 运行）。

以下为**尚未闭合**的条目，补做前不得宣称首轮完整性闭合：

| 项 | 类型 | 当前状态 | 出口 |
|---|---|---|---|
| R1 先校验后写入 + 未完成动作接续 | 代码 | **已修复（§21）** | 「第 2 条非法 → 零落盘」与「第 2 条写失败 → 重入完成且幂等」两条用例通过 |
| R2 `confirm-executor` 交互闸门 | 代码 | **已修复（§21）** | pty 正例写入；非 TTY 反例不写并返回 `WF_SEMANTIC_DECISION` |
| R3 锁部分标记的恢复出口 | 验证/文档 | **已验证（§21）** | 用例证明人工出口；`recovery.md` 写明清理顺序 |
| R5 `install.py` 记录形态下的卸载 | 测试 | **已验证（§21）** | install → 偏离 → uninstall：偏离保留、其余移除、数据保留 |
| R4 `implement.md` 口径说明 | 文档 | **已补（§21）** | 开头说明「阶段 ≠ 轮次」与三态分记 |
| R6 未运行项核对 | 登记 | **已核（§21）** | 清单更新；压缩/签发保持「未运行 + 原因」 |

补齐后的回归范围：受影响套件（CP1/CP3/CP4、V2/V3、A8、F0）+ 三条机检 + `build --verify`/`--verify-token-parity`，并在此追加实跑记录。

## 21. R1–R6 实施与实跑（2026-11-03）

复核文与处置依据见 `review-round2-reconciliation.md`；本节记录实施结果。

### 21.1 用例（24/24）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R1 非法条目整批拒绝 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R1 拒绝时零写入 | first.md 不存在 | False | PASS |
| R1 中途写入失败映射为结构化退出码 | WF_PERSISTENCE_FAILED | WF_PERSISTENCE_FAILED | PASS |
| R1 失败后动作留在未完成态 | kind=baseline.apply 且 state!=done | kind=baseline.apply state=prepared | PASS |
| R1 不同提案不得覆盖未完成动作 | WF_ACTION_INCOMPLETE | WF_ACTION_INCOMPLETE | PASS |
| R1 同提案重入续做成功 | WF_OK 且两份文件都在 | WF_OK first=True second=True | PASS |
| R1 接续复用同一动作 | action.id 与失败时一致且 state=done | same=True state=done | PASS |
| R1 spec 整批校验拦截 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R1 spec 拦截时零写入 | new-one.md 不存在 | False | PASS |
| R1 spec 拦截时索引不变 | index 不含 new-one.md | False | PASS |
| R2 非 TTY 拒绝写确认记录 | exit=2 且 WF_SEMANTIC_DECISION | rc=2 code=True | PASS |
| R2 非 TTY 未写记录 | 记录条数仍为 1 | 1 | PASS |
| R2 TTY 下拒绝确认词不写记录 | 非零退出且未写 | rc=2 count=1 | PASS |
| R2 TTY 下确认词写入记录 | 退出 0 且记录 +1 | rc=0 count=2 | PASS |
| R5 正式记录下预览可运行 | 输出预览且列出 2 项偏离 | deviations=2 | PASS |
| R5 正式记录下卸载应用 | WF_OK | ['已保留 .gitignore 中的 /.wf-lock 裸行（段外）', '已列出但未认领：同目录未知文件（不删除、不改名）', '人工清理顺序：确认无 wf 进程 → 删除  | PASS |
| R5 偏离默认保留 | 两处本地修改仍在 | True | PASS |
| R5 未改资产被移除 | .wf/bin/wf.py 已移除 | True | PASS |
| R5 数据与安装记录保留 | 安装记录仍在 | True | PASS |
| R5 托管段移除但保留 /.wf-lock 行 | 无托管标记且含 /.wf-lock | marker=False lock_line=True | PASS |
| R3 部分标记被识别为资产待决 | WF_ASSET_DECISION | code=True rc=2 | PASS |
| R3 修复入口在锁不可识别时拒绝应用 | WF_ASSET_DECISION | rc=1 code=True | PASS |
| R3 清理顺序写入维护流程文档 | 含锁人工清理顺序与空锁自愈说明 | order=True self_heal=True | PASS |
| R3 人工清理后恢复正常 | status 正常输出 | rc=0 | PASS |

### 21.2 逐项结果

| 项 | 实施 | 证据 |
|---|---|---|
| **R1** 先校验后写入 + 接续 | `baseline-apply`：整批预校验（路径/前缀/内容）后写入，输入含「路径 + 内容摘要」；失败映射 `WF_PERSISTENCE_FAILED`；同提案重入复用原动作续做，不同提案 → `WF_ACTION_INCOMPLETE`。`spec-update`：`validate_changes()` 在建立动作前做语义校验（含「活动依赖是否已解除」，并扣除本批已声明的解除），应用阶段逐条写、OSError → `WF_PERSISTENCE_FAILED` | 「非法条目 → 零写入」「中途写失败 → `WF_PERSISTENCE_FAILED` + 动作留存」「同提案续做复用同一动作」「不同提案被拒」「spec 拦截时零写入且索引不变」 |
| **R2** 交互闸门 | `confirm-executor` 非 TTY → `WF_SEMANTIC_DECISION`（exit 2）且不写；TTY 下先打印完整元组，输入 `yes` 才写；确认词不符不写 | 四条用例（pipe 拒绝、pty 拒绝词、pty 确认、记录条数核对） |
| **R3** 锁部分标记 | 运行期由 `WF_WRITER_BUSY` 改为 `WF_ASSET_DECISION`（机制稿 §4.1：不覆盖、不接管）；`repair --apply` 的锁异常映射为 `WF_ASSET_DECISION` 并给出锁路径；`maintenance-flow.md` 增补人工清理顺序与「空锁自愈」说明 | 「部分标记 → `WF_ASSET_DECISION`」「repair 应用被拒」「清理顺序入文档」「人工恢复后正常」 |
| **R5** 正式记录形态下的卸载 | 无需改代码：`install.py` 写出的记录形态下，`uninstall` 预览/应用行为与 dev-deploy 一致 | 偏离保留、未改资产移除、数据与安装记录保留、`/.wf-lock` 行保留 |
| **R4** 口径说明 | `implement.md` 开头补「P1–P5 是阶段不是轮次；能力/验证/验收三态分记」 | 文档 |
| **R6** 未运行清单 | `dedupe_refs` 已从「未运行」移除（§16.4 已跑）；压缩/签发保持未运行 | §16.5/§18.4 一致 |

### 21.3 回归（R1–R3 改动后全量重跑）

| 套件 | 结果 |
|---|---|
| R1/R2 新用例 / R3+R5 新用例 | 14/14 / 10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0（发行树安装 + 自举） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过（`rules_digest=sha256:25d01944…`） |

### 21.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R1 | 写入失败以异常外泄 | 目标不可写时命令以退出码 70 崩溃、无结构化结果 | 两个入口都映射为 `WF_PERSISTENCE_FAILED`（facts 带已写路径） |
| N-R2 | 语义校验晚于建立动作 | 「依赖未解除」的 spec 删除会先建动作再报错，留下未完成动作挡住修正重试 | 语义校验前移到建立动作之前；依赖校验扣除本批声明的解除 |
| N-R3 | 锁不可识别被报成写权占用 | 运行期把 `LockMismatch` 归到 `WF_WRITER_BUSY`；`repair --apply` 遇锁异常直接以 traceback 退出 | 前者改为 `WF_ASSET_DECISION`；后者捕获并给人工出口（附锁路径） |
| N-R4 | `confirm-executor` 无交互闸门 | 非交互调用可直接写确认记录（本轮实测即如此） | 非 TTY 拒绝 + 终端确认词 + 打印待写元组 |

### 21.5 重绑

- 修订前：`sha256 bbdcef62…`（753 行）
- 修订后：`sha256 f6768af29cafc3be91162737e591bba6aa480b640dbf771b39d71e88dd90f176`（760 行）
- 新增：§3 第 3 步的交互闸门说明、§2.3.2「成组写入与接续」
- 独立复审仍按此前决定暂不执行；实现稿保持「实现阶段记录」。

### 21.6 收口状态

R1–R6 全部落地；`review-round2-reconciliation.md` §4 所述「补齐前不宜宣称首轮完整性闭合」的条件已满足（余下未运行项仅 D1 的压缩/签发路径）。

## 22. 第三轮评审的登记（2026-11-03，复核见 `review-round3-reconciliation.md`）

8 条全部成立，其中第 8 条推翻 §21 对锁的结论（「空锁自愈」与机制稿 §4.1 的排他创建/不自动认领冲突；错误码应为 `WF_CAPABILITY_UNAVAILABLE` 而非 `WF_ASSET_DECISION`）。**§21 的 R3 结论作废，需按 R15 重做。**

以下为未闭合项，落地前「首轮完整性闭合」的表述不成立：

| 项 | 类型 | 当前状态 | 出口 |
|---|---|---|---|
| R7 `baseline-apply` 的阶段/批准/触碰面/目标类别/真实落点 | 代码 | **已修（§23）** | 五种非法提案全部零写入 |
| R8 `spec-update` 目标类别 | 代码 | **已修（§23）** | `.wf/spec/**` 之外 → `WF_SCOPE_UNRESOLVED` |
| R9 改名/删除续做 | 代码 | **已修（§23）** | 「改名成功 + 索引失败 → 重入完成」 |
| R10 双轴必须通过 | 代码 | **已修（§23）** | 任一轴非 pass → check 不 pass |
| R11 finish 必需验证 | 代码 | **已修（§23）** | 未执行 → 不 pass |
| R12 人判绑定对象与版本 | 代码 | **已修（§23）** | `v1` 不接受 `v10`/旧版本决定 |
| R13 Check 期 spec 重新匹配与到期/extracted 处置 | 代码 | **已修（§23）** | 漏策展命中 → 阻断 |
| R14 归档持久化只认任务记录 | 代码 | **已修（§23）** | 仅提交 `review/notes.md` → `persisted=false` |
| R15 锁按 §4.1 重做 | 代码+文档 | **已修（§23）** | 空/不完整 → `WF_CAPABILITY_UNAVAILABLE`，不认领 |
| R16 运行期用例固化进仓库 | 工程 | **已完成（§23）** | `scripts/tests/wf_runtime/` 可复跑 |

落地后需重跑：初始化、普通任务、V2/V3、spec 生命周期、F0、R1/R2/R3/R5 用例，并在此追加实跑记录。

## 23. R7–R16 实施与实跑（2026-11-03）

复核文见 `review-round3-reconciliation.md`；本节记录实施与验证结果。

### 23.1 第三轮用例（37/37）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R7 未开工不得应用 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R7 未开工零写入 | 未写 ok.md | False | PASS |
| R7 准备：开工 | WF_OK | WF_OK | PASS |
| R7 控制记录不得作目标 | WF_SCOPE_UNRESOLVED | WF_SCOPE_UNRESOLVED | PASS |
| R7 业务路径不得经基线写入 | WF_SCOPE_UNRESOLVED | WF_SCOPE_UNRESOLVED | PASS |
| R7 合法提案可应用 | WF_OK | WF_OK | PASS |
| R7 符号链接逃逸被拒 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R7 逃逸时未写项目外文件 | outside 未生成 x.md | False | PASS |
| R7b 准备：开工 | WF_OK | WF_OK | PASS |
| R7 目标须在批准触碰面内 | WF_SCOPE_UNRESOLVED | WF_SCOPE_UNRESOLVED | PASS |
| R8 准备：开工 | WF_OK | WF_OK | PASS |
| R8 spec 不得写控制记录 | WF_SCOPE_UNRESOLVED | WF_SCOPE_UNRESOLVED | PASS |
| R10 准备：开工 | WF_OK | WF_OK | PASS |
| R10 双轴 fail 不得 pass | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R10 双轴 pass 可继续 | WF_OK | WF_OK | PASS |
| R11 准备：开工 | WF_OK | WF_OK | PASS |
| R11 finish 项在 Check 被执行 | commands 含 v2 且 Check 未 pass | ids=['v1', 'v2'] code=WF_CHECK_FAILED | PASS |
| R9 准备：开工 | WF_OK | WF_OK | PASS |
| R9 准备：建条目 | WF_OK | WF_OK | PASS |
| R9 改名后索引写失败 | WF_PERSISTENCE_FAILED | WF_PERSISTENCE_FAILED | PASS |
| R9 改名本身已落盘 | r9b.md 存在且 r9.md 不存在 | new=True old=False | PASS |
| R9 同变更集重入完成剩余步骤 | WF_OK 且索引含 r9b.md | WF_OK index=True | PASS |
| R12 准备：开工 | WF_OK | WF_OK | PASS |
| R12 旧 id/旧对象不得通过 | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R12 未绑定批准对象的决定不得通过 | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R12 绑定对象与版本的决定通过 | WF_OK | WF_OK | PASS |
| R13 准备：开工 | WF_OK | WF_OK | PASS |
| R13 漏策展的命中被阻断 | WF_SPEC_INCOMPLETE | WF_SPEC_INCOMPLETE | PASS |
| R13 未核实条目阻断 | WF_SPEC_INCOMPLETE | WF_SPEC_INCOMPLETE | PASS |
| R13 人判覆盖后可继续 | WF_OK | WF_OK spec=null | PASS |
| R14 只提交 review/notes.md 不算已持久化 | persisted=False | False | PASS |
| R14 记录进入提交才算已持久化 | persisted=True | True | PASS |
| R15 空锁不被认领 | WF_CAPABILITY_UNAVAILABLE | rc=1 has=True | PASS |
| R15 空锁未被补写 | 仍为空 | <empty> | PASS |
| R15 部分标记返回 WF_CAPABILITY_UNAVAILABLE | WF_CAPABILITY_UNAVAILABLE | rc=1 has=True | PASS |
| R15 不覆写未知内容 | 标记仍为 wf-lock | wf-lock | PASS |
| R15 合法标记恢复正常 | rc=0 | 0 | PASS |

### 23.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R7** 基线写入边界 | `baseline-apply` 写入前增加：阶段须为 `execute`/`check`/`finish`、规划须有效批准（复用 `gates.verify_step("task.plan-approved")`）、目标类别限「基线文件 / 项目配置 / `.wf/spec/**`」、目标须被批准 `touch_paths` 匹配、`realpath` 仍在项目根内；控制记录一律 `WF_SCOPE_UNRESOLVED` | 未开工 → `WF_SEMANTIC_DECISION`；控制记录/业务路径/越触碰面 → `WF_SCOPE_UNRESOLVED`；符号链接逃逸 → `WF_PATH_INVALID` 且项目外无文件 |
| **R8** spec 写入目标 | `spec.validate_changes` 限定 `.wf/spec/**` + `realpath` 核对 | 目标为 `.wf/writer.json` → `WF_SCOPE_UNRESOLVED` |
| **R9** 改名/删除续做 | `validate_changes(..., resume=True)` 按已落盘事实识别已完成步骤；`apply_changes(..., resume=...)` 透传；改名/删除应用幂等 | 「改名成功、索引写失败 → `WF_PERSISTENCE_FAILED`」→ 同变更集重入完成且索引只出现一次 |
| **R10** 双轴 | 两轴 `conclusion` 必须均为 `pass`；解析层只接受 `pass/fail/undecided` | 双轴 fail → `WF_CHECK_FAILED`；双轴 pass → 通过 |
| **R11** finish 验证 | Check 执行全部必需验证（去掉 `consume_at=finish` 跳过）；归档前只做重核 | 失败 finish 项出现在 `check.commands` 且 Check fail |
| **R12** 人判绑定 | `subject` 按整词匹配 + 绑定当前规划（显式 `plan_version` 或批准对象摘要） | `v10` 与旧对象决定均不通过；正确绑定通过 |
| **R13** spec 兜底 | Check 按实际触碰路径重匹配：漏策展 → 阻断；未核实（`extracted`/空）无人判 → 阻断 | 三态用例均符合 |
| **R14** 归档持久化 | 只认「提交包含 `task.json` 且其中终态为 `normal`」 | 只提交 `review/notes.md` → false；记录提交 → true；异常终态 → false |
| **R15** 锁 | `O_CREAT|O_EXCL` 创建；已存在须普通文件 + 真实落点 + 完整标记；空/部分标记 → `LockUnavailable` → `WF_CAPABILITY_UNAVAILABLE`；两份自含实现同步；`maintenance-flow.md` 撤回「自愈」 | 空锁与部分标记均拒绝且不覆写；合法标记可用；符号链接锁拒绝 |
| **R16** 用例固化 | 新增 `scripts/tests/wf_runtime/`：`test_lock.py`（5）、`test_archive_persisted.py`（3）随 `unittest discover` 默认运行；`full/` 保存三夹具全流程脚本与 README（手动运行，会写 `~/.wf/`） | 8 项新单测通过；全流程脚本已入库 |

### 23.3 回归（第三轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第三轮 R7–R15 用例 | 37/37 |
| `scripts/tests/wf_runtime` 新单测 | 8/8 |
| R1/R2 套件 / R3+R5 套件 | 14/14（A12 期望已按 R11 更新）/ 10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0（发行树安装 + 自举） | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过（`rules_digest=sha256:167b75fe…`） |

### 23.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R7 | 续做标志未透传 | `apply_changes` 内部又调了一次 `validate_changes`（默认 `resume=False`），导致改名续做仍报「source missing」 | `apply_changes(..., resume=...)` 透传 |
| N-R8 | 人判主题按 `/` 切分 | spec 路径含 `/`，整词匹配永远失败 | 分隔符去掉 `/` |
| N-R9 | 实现稿重复小节 | 追加 §2.3.2 时与既有同名小节重复 | 删除旧节，保留合并版 |
| N-R10 | 旧用例固化在错误前提上 | `cp1 A12` 断言「finish 项在 Check 延后」、`r1r2 R1` 提案触碰面不足——都是被本轮修正的旧行为 | 更新期望（R11 语义 / 触碰面） |

### 23.5 重绑

- 修订前：`sha256 f6768af2…`（760 行）
- 修订后：`sha256 daec04e706b08e71e665bd0f1548cb98bd06627822c9c192506436b86f2beea7`（767 行）
- 新增：锁对象行的排他创建与不认领、双轴必须 pass、§2.3.2 写入边界与续做、§2.3.3 Check 的必需验证与知识兜底。

### 23.6 收口状态

R7–R16 全部落地。第三轮复核提出的 8 条 + 评审附注 1 条均已闭环；此前 §22 登记的未闭合项全部关闭。
仍未运行项仅剩 D1（真实压缩/签发路径，按人决定保持未运行）；E 的独立复审按人决定暂不执行。

## 24. 第四轮评审的登记（2026-11-03，复核见 `review-round4-reconciliation.md`）

7 条全部成立（第 1 条「触碰面」口径已改写：spec 目标不要求落在业务 `touch_paths`，越界判定改为「阶段 + 批准 + 未暂停 + 目标类别 + 真实落点」）。以下为未闭合项：

| 项 | 类型 | 当前状态 | 出口 |
|---|---|---|---|
| R17 `spec-update` 动作授权 | 代码 | **已修（§25）** | 拒绝且零写入 |
| R18 核实集合并集与到期 | 代码 | **已修（§25）** | 过期与策展未命中项均判定 |
| R19 同批改名目标碰撞 | 代码 | **已修（§25）** | `WF_TARGET_COLLISION` 零写入 |
| R20 改名改写归档引用 | 代码 | **已修（§25）** | 归档 `task.json` 不被改写 |
| R21 Check 结束前重算范围 | 代码 | **已修（§25）** | 新增范围外文件 → `WF_CHECK_STALE` |
| R22 TDD 证据结构 | 代码 | **已修（§25）** | 结构不符 → 不 pass |
| R23 归档提交失败续做 | 代码 | **已修（§25）** | 有授权则续做提交 |
| R24 放弃的真实处置 | 代码 | **已修（§25）** | 残留 → `WF_WORKSPACE_UNRESOLVED` |

落地前「首轮完整性闭合」的表述不成立；落地后需重跑 spec 生命周期、初始化、普通任务、V2/V3、F0、R7–R15 用例与 `wf_runtime` 单测。

## 25. R17–R24 实施与实跑（2026-11-03）

复核文见 `review-round4-reconciliation.md`。

### 25.1 第四轮用例（24/24）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R19 同批同目标被拒 | WF_TARGET_COLLISION | WF_TARGET_COLLISION | PASS |
| R19 拒绝时零写入 | a.md 与 c.md 都还在 | a=True c=True | PASS |
| R17 未开工不得写 spec | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R17 暂停任务不得写 spec | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R17 拒绝时零写入 | early.md 不存在 | False | PASS |
| R17 恢复后可写 | WF_OK | WF_OK | PASS |
| R20 准备：Check | WF_OK | WF_OK | PASS |
| R20 准备：归档任务 | WF_OK | WF_OK facts={"archived_at": "2026-11-03T07:42:23.184719Z", "commit": { | PASS |
| R20 改名成功 | WF_OK | WF_OK | PASS |
| R20 归档任务记录未被改写 | task.json 内容不变 | True | PASS |
| R20 归档仍引用旧路径 | .wf/spec/old.md 仍在归档策展里 | True | PASS |
| R18 到期条目阻断 | WF_SPEC_INCOMPLETE 且 needs 含 expired | code=WF_SPEC_INCOMPLETE needs=['expired'] | PASS |
| R18 策展未命中条目也参与判定 | curated 含 nomatch 且仍阻断 | curated=['.wf/spec/expired.md', '.wf/spec/nomatch.md'] code=WF_SPEC_IN | PASS |
| R18 人判覆盖后通过 | WF_OK | WF_OK spec=null | PASS |
| R21 验证期间新增范围外文件 | WF_CHECK_STALE 或 WF_WORKSPACE_UNRESOLVED | WF_CHECK_STALE | PASS |
| R22 准备：开工 | WF_OK | WF_OK | PASS |
| R22 非结构化证据不得通过 | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R22 结构化证据通过 | WF_OK | WF_OK | PASS |
| R23 准备：正常归档 | WF_OK | WF_OK | PASS |
| R23 未持久化状态已构造 | persisted=False | False | PASS |
| R23 重入按既有授权续做提交 | WF_OK 且 persisted=true 且标记续做 | WF_OK persisted=True resumed=True | PASS |
| R24 无授权且未处置不得结案 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R24 未结案时不写异常终态 | terminal 为空且仍未归档 | terminal=None status=in_progress | PASS |
| R24 有授权时实际提交并结案 | WF_OK 且改动已提交 | WF_OK committed=True | PASS |

### 25.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R19** 整批冲突 | `validate_changes` 增加整批预检：源唯一、目标唯一、目标不得是另一变更的源 | `a→b` + `c→b` → `WF_TARGET_COLLISION` 且 a/c 均在 |
| **R17** spec 授权 | `spec-update` 复用基线的三项授权：阶段 ∈ execute/check、有效批准、未暂停/挂起；不给 spec 目标加 `touch_paths` 要求（口径见复核文 §1） | 未开工/暂停 → 拒绝且零写入；恢复后可写 |
| **R20** 归档引用 | `_sync_curation_paths` 跳过已归档/终止任务；关联活动任务有未完成动作 → `WF_ACTION_INCOMPLETE`；当前任务仍同步自身策展（只跳过 pending 检查） | 归档 `task.json` 字节不变、仍引用旧路径 |
| **R18** 核实并集与到期 | 判定集合改为「命中 ∪ 策展」；`extracted`/空/超过 `spec_verify_days`（缺省 90）/日期不可解析 都进入 needs；人判覆盖后写 `check.spec_review` 证据 | 到期条目与策展未命中条目都阻断；双覆盖后通过 |
| **R21** 结束前重算 | 写结果前重跑完整范围核对（分类/外部变更/治理面）并与初值比对 | 验证期间新增 `rogue.txt` → 阻断 |
| **R22** TDD 结构 | 新增 `tdd_evidence_problem()`：五段非空 + 红/绿引用可解析到本次 `check.commands`；Check 与门禁共用 | `{"note": …}` → `WF_CHECK_FAILED`；结构化证据通过 |
| **R23** 归档续做 | 已归档未持久化且记录含 `finish_decision` → 续做记录组提交并重算持久化 | 回退记录组提交后重入 → `WF_OK`、`persisted=true`、`resumed_commit=true` |
| **R24** 放弃处置 | 有 `commit` 授权的改动实际提交，其余须已不在工作树差异；残留 → `WF_WORKSPACE_UNRESOLVED`，不写终态不移目录 | 无授权残留被拒且未结案；有授权则提交并结案 |

### 25.3 回归（第四轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第四轮 R17–R24 用例 | 24/24 |
| 第三轮 R7–R15 用例 | 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0（发行树安装 + 自举） | 9/9 |
| `scripts/tests` / `wf_runtime` 单测 | OK / 8/8 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过（`rules_digest=sha256:9870cbf8…`） |

### 25.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R11 | 自身策展未同步 | R20 初版把当前任务整体跳过，改名后自身策展仍指旧路径，spec 套件从 13 掉到 9 | 只对当前任务跳过「未完成动作」检查，仍同步路径/哈希 |
| N-R12 | 归档续做条件写错 | 人的 `commit` 授权只覆盖业务路径，不覆盖归档目录，按「授权覆盖记录目录」判续做永远不成立 | 改为按记录中的 `finish_decision`（归档已授权）判定 |
| N-R13 | TDD 标志来源 | `plan.tdd` 来自批准信封的 `tdd` 输入，不在 PRD 块内；用例构造错误会误判为「不校验」 | 用例改为在 approve 信封传 `tdd=true` |
| N-R14 | 用例间 spec 互相命中 | 同一夹具里 `src/**` 规则会命中后续任务，导致误判为框架缺陷 | 各用例改用独立触碰根（`area21/**` 等） |

### 25.5 重绑

- 修订前：`sha256 daec04e7…`（767 行）
- 修订后：`sha256 e3a0b8381d1cbf427e3f1d1f383d66fe01eac78c5ea573b9ccdb1db33324b22b`（773 行）
- 新增：§2.3.2 的 spec 授权/整批冲突/改名与归档引用、§2.3.3 的核实并集与到期/结束前重算/TDD 结构、§2.3.1 的归档续做与放弃处置。

### 25.6 收口状态

R17–R24 全部落地；第四轮 7 条（含第 1 条口径改写）闭环，§24 登记项全部关闭。
仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 26. R25–R30 实施与实跑（2026-11-03）

复核文见 `review-round5-reconciliation.md`。第五轮 6 条：1/2/3/4/5/6 分别对应下表；R25/R27/R29 的用例落在第四轮套件（R23/R22/R24 条目），R28/R30 单独成组。

### 26.1 用例

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R28 准备：开工 | WF_OK | WF_OK | PASS |
| R28 配置周期生效（1 天） | needs 含 expired 且 period_days=1 | needs=['future-date', 'expired'] period=1 | PASS |
| R28 未来日期进入待核对 | needs 含 future-date | ['future-date', 'expired'] | PASS |
| R28 覆盖后可继续 | WF_OK | WF_OK | PASS |
| R28 spec_review 写入检查记录 | 记录含 needs/period/evidence | needs=2 evidence=1 | PASS |
| R30 准备：开工 | WF_OK | WF_OK | PASS |
| R30 准备：留下未完成动作 | WF_PERSISTENCE_FAILED | WF_PERSISTENCE_FAILED | PASS |
| R30 被引用的路径在写入前阻断 | WF_ACTION_INCOMPLETE | WF_ACTION_INCOMPLETE | PASS |
| R30 未被引用的路径不阻断 | 不抛错 | no-raise | PASS |
| R30 判定只读不写文件 | ref.md 仍在 | True | PASS |

第四轮套件在本次修复后为 30/30（含 R23 的「无写权不得续做」、R22 的真实红→绿与「红绿同一条不得通过」、R24 的记录持久化）。

### 26.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R25** 归档续做须核当前写权 | 续做记录组提交前先 `ctx.require_held(task=...)`；写权/代次不满足即停，返回对应码而不提交 | 释放写权后重入 → `WF_WRITER_BUSY`；持写权重入 → 续做成功 |
| **R26** spec 触碰面口径 | 删除上一轮「spec 免触碰面」的豁免：按设计稿 §4.2，spec 目标必须被批准 `touch_paths` 匹配，与 Check 的分类一致 | 触碰面仅 `src/**` 时新增 `.wf/spec/outside-face.md` → `WF_SCOPE_UNRESOLVED` 且零写入 |
| **R27** TDD 红/绿语义 | 绿引用须是本次通过的命令；红引用须是历史检查中失败的命令；两者不同 | 真实红→绿通过；红绿同为一条 → 不通过 |
| **R28** 核实配置与证据 | `load_project_config` 返回 `(config, problems)` 正确解包（不再静默回退）；未来日期进入 `future-date`；成功 Check 的 `check.spec_review` 保存 needs/period/evidence | 周期 1 天 + 2 天前 → `expired`；未来日期 → `future-date`；记录含 `spec_review` |
| **R29** 放弃的记录持久化 | 移入归档后提交记录组并核对（`git ls-files` + 目录无未提交差异）；未成功 → `WF_PERSISTENCE_FAILED` 停在待持久化 | 结案后记录已提交；`record_persisted=true` |
| **R30** 冲突判定前移 | `validate_changes` 在写入前检查真正引用旧路径的活动任务是否有未完成动作；无关任务不阻断；本次任务自身在途动作不算冲突 | 被引用路径 → `WF_ACTION_INCOMPLETE`；未引用路径 → 不抛错；拆分用例恢复通过 |

### 26.3 回归（第五轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第四轮（R17–R24） | 30/30 |
| 第五轮（R25–R30） | 10/10 |
| 第三轮（R7–R15） | 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 | 13/13 |
| F0 | 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 26.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R15 | 冲突判定误伤本次任务 | 改名/删除的冲突检查在 `apply_changes` 二次校验时把**本次任务自己的在途动作**当成冲突，B5 拆分用例失败 | `validate_changes/apply_changes` 传入 `current_task_id` 并跳过自身 |
| N-R16 | spec 触碰面口径前后矛盾 | 上一轮「spec 免触碰面」的说明与设计稿 §4.2 及 Check 分类相反（入口允许写、门禁判 c 类） | 统一为「spec 目标须在批准触碰面内」，实现稿同步改写 |
| N-R17 | 归档续做沿用历史授权不核写权 | R23 用例先释放写权再验证成功，固化了错误前提 | 续做前 `require_held`；用例改为「释放后拒绝、持权后续做」 |
| N-R18 | 放弃只处置业务改动 | 记录未提交即报告退出完成 | 提交记录组并核对；失败停待持久化 |

### 26.5 重绑

- 修订前：`sha256 e3a0b838…`（773 行）
- 修订后：`sha256 04bc919c42c4c3834115028bce901b412f6d998e452de2a767559fa10f8f22f4`（773 行）
- 改写：§2.3.1 的归档续做/放弃、§2.3.2 的 spec 触碰面与冲突判定、§2.3.3 的 TDD 红绿语义。

### 26.6 收口状态

第五轮 6 条闭环；R25–R30 全部落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 27. 第六轮评审的登记（2026-11-03，复核见 `review-round6-reconciliation.md`）

4 条全部成立。以下未闭合项在落地前不成立「首轮完整性闭合」：

| 项 | 类型 | 当前状态 | 出口 |
|---|---|---|---|
| R31 归档/放弃按已落盘步骤恢复 | 代码 | **已修（§28）** | 「未移动→先移动」「未提交→续做」「放弃失败→可续做」 |
| R32 写权释放/交接锁内重核 | 代码 | **已修（§28）** | 锁内属 B 时 A 的调用被拒 |
| R33 获取/释放/交接/恢复消费保留 WIP | 代码 | **已修（§28）** | 他任务未处置 WIP 时获取被拒 |
| R34 规则版本参与门禁 | 代码 | **已修（§28）** | 旧规则 Check 不满足门禁 |

落地后回归范围：CP1 A23、CP5 B3、R23/R24/R29、CP2、R1R2、CP1/CP3/CP5 门禁用例与三夹具全流程。

## 28. R31–R34 实施与实跑（2026-11-04）

复核文见 `review-round6-reconciliation.md`。

### 28.1 第六轮用例（13/13）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R31 准备：正常归档 | WF_OK | WF_OK | PASS |
| R31 准备：目录回到活动位置 | 活动目录存在、归档目录不存在 | active=True archived=False | PASS |
| R31 重入先完成移动 | 记录回到归档根下 | dir=.wf/tasks/archive/2026-11/2026-90c1c736cc764d7c9a6119dd5ed1a20a-R3 | PASS |
| R31 重入报告已持久化 | WF_OK 且 persisted=true | WF_OK persisted=True | PASS |
| R31 准备：放弃结案 | WF_OK | WF_OK | PASS |
| R31 准备：记录未提交 | 任务仍归档、记录未入库 | tracked=False | PASS |
| R31 放弃重入续做记录提交 | WF_OK 且记录已入库 | WF_OK tracked=True | PASS |
| R32 锁内持有者变更时拒绝释放 | WF_WRITER_BUSY | WF_WRITER_BUSY | PASS |
| R33 他任务未处置 WIP 被识别 | 列出该任务与其 pending | blocked=[{"task": "2026-16d83ee434cb4fd082c9c1b18d8f87a7", "pending":  | PASS |
| R33 排除自身后不阻断 | 空列表 | [] | PASS |
| R33 准备：重新获取写权 | WF_OK | WF_OK | PASS |
| R33 自身 pending 阻断释放 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R34 旧规则 Check 不满足门禁 | WF_CHECK_STALE | ok=False code=WF_CHECK_STALE | PASS |

### 28.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R31** 按已落盘步骤恢复 | 归档重入：先核目录位置，未移动则持写权完成移动（幂等）再核提交；`archive_persisted` 追加「记录必须在归档根下」。放弃重入：对「已归档 abnormal、记录未提交」放行，持写权补提交并核对 | 「目录回到活动位置」后重入 → 记录移回归档根且 `persisted=true`；放弃记录失败后重入 → 记录入库、`WF_OK` |
| **R32** 锁内重核 | `writer release` / `writer-handover begin` 取锁后重读 writer，重核持有者与代次；不匹配 `WF_WRITER_BUSY` | 伪造「锁外属于 A、锁内属于 B」→ 释放被拒 |
| **R33** 保留 WIP 共享判据 | 抽出 `wip_blockers()`：获取前扫其他活动任务的 `disposition.pending`；释放/交接对自身 pending 同判 | 他任务 pending → 被列出且不排除自身时为空；自身 pending → 释放 `WF_WORKSPACE_UNRESOLVED` |
| **R34** 规则版本参与门禁 | `task.check-passed` 比较 `anchor.rule_version`；`evaluate` 对规则类回执的版本失配不再归 `satisfied` | 旧规则 Check → `WF_CHECK_STALE` |

### 28.3 回归（第六轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第六轮 R31–R34 | 13/13 |
| 第五轮 / 第四轮 / 第三轮 | 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 28.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R19 | 冲突检查需要可单测的判据 | WIP 拦截内联在 `_writer_acquire` 里，无法单测也无法在释放/交接复用 | 抽出 `cli.wip_blockers()`，三处共用 |
| N-R20 | 归档位置缺失导致误报 | `archive_persisted` 只核「记录进提交」，不看位置，符合探针的误报 | 追加「记录必须在 `.wf/tasks/archive/` 下」 |

### 28.5 重绑

- 修订前：`sha256 04bc919c…`（773 行）
- 修订后：`sha256 61c5d7130ad711f7a1b88a232f7b983b4ccde1d8d0b1ede58f8fea772593fd5d`（781 行）
- 新增：§2.3.1 的「按已落盘步骤恢复」、§2.3.4「写权与保留 WIP 的共享判据」、§2.3.3 的「规则版本参与门禁」。

### 28.6 收口状态

第六轮 4 条闭环；R31–R34 全部落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 29. R35–R37 实施与实跑（2026-11-04）

复核文见 `review-round7-reconciliation.md`。

### 29.1 第七轮用例（15/15）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R35 准备：放弃结案 | WF_OK | WF_OK | PASS |
| R35 准备：目录回到活动位置 | 活动在、归档不在 | active=True archived=False | PASS |
| R35 重入先完成移动 | 记录回到归档根 | dir=.wf/tasks/archive/2026-11/2026-2a930a476d064280888fe0c303f3e667-R3 | PASS |
| R35 重入报告已持久化 | WF_OK 且 record_persisted | WF_OK persisted=True | PASS |
| R36 准备：开工 | WF_OK | WF_OK | PASS |
| R36 准备：释放第 1 代 | WF_OK | WF_OK | PASS |
| R36 准备：重新取得新代次 | WF_OK 且代次前进 | WF_OK gen=9 | PASS |
| R36 旧代次不得释放新写权 | WF_GENERATION_STALE | WF_GENERATION_STALE | PASS |
| R36 当前代次可释放 | WF_OK | WF_OK | PASS |
| R37 准备：开工 | WF_OK | WF_OK | PASS |
| R37 准备：收工保留 WIP | WF_OK 且记录 handoff.wip | WF_OK paths=[{'digest': 'sha256:19732980d68fbd00358a0a4d98246c960400b8 | PASS |
| R37 真实 WIP 被识别 | 列出该任务与路径 | blocked=[{"task": "2026-72ced72549a04d9e834272783853da5d", "paths": [" | PASS |
| R37 保留 WIP 阻断空闲释放 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R37 准备：恢复前取得写权 | WF_OK | WF_OK | PASS |
| R37 保留路径变化时恢复被拒 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |

### 29.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R35** 异常归档按步骤恢复 | 放弃续做与归档共用三步判定（位置 → 提交 → 事实），并整体移入 `lock.acquire`，先 `require_held` 再恢复 | 目录移回活动位置后重入 → 先移回归档根、再补提交、`record_persisted=true` |
| **R36** 锁内完整重核 | 释放/交接在锁内直接调用 `ctx.require_held()`（含 generation 与 scope） | 「锁外通过、锁内被换期」→ `WF_WRITER_BUSY` 且核验调用两次；旧代次释放 → `WF_GENERATION_STALE` |
| **R37** 真实 WIP 判据 | 新增 `tasks.wip_paths()` 读取 `handoff.wip.paths`（支持指纹条目）；`wip_blockers` 判据改为 `wip_paths ∪ disposition.pending`；`ensure_releasable(task, root)` 核工作树；`task-resume` 核保留路径现状 | 真实 `stop keep` → 被识别；空闲释放被拒；保留路径消失后恢复被拒 |

### 29.3 回归（第七轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第七轮 R35–R37 | 15/15 |
| 第六轮 / 第五轮 / 第四轮 / 第三轮 | 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 29.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R21 | 保留 WIP 的路径是指纹条目 | `handoff.wip.paths` 存 `{path,digest,…}`，按字符串过滤后恒为空，R37 用例首轮全部落空 | 抽出 `tasks.wip_paths()` 统一取值 |
| N-R22 | R32 用例只证明了锁外核验 | 假 ctx 在第一次 `require_held` 就抛错，锁内复核从未被执行 | 用例改为「第 1 次通过、第 2 次失败」并断言核验调用两次 |

### 29.5 重绑

- 修订前：`sha256 61c5d713…`（781 行）
- 修订后：`sha256 52918e6767d630fb1b2ab48d5b00674e6a7204b89f361dfe9259090a74125ac3`（781 行）
- 改写：§2.3.1 的步骤恢复（含互斥）、§2.3.4 的锁内完整重核与真实 WIP 判据。

### 29.6 收口状态

第七轮 3 条闭环；R35–R37 全部落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 30. 第八轮评审的登记（2026-11-04，复核见 `review-round8-reconciliation.md`）

2 条全部成立：

| 项 | 类型 | 当前状态 | 出口 |
|---|---|---|---|
| R38 授予写权的入口统一前置 | 代码 | **已修（§31）** | 三个入口在同一状态下都返回 `WF_WORKSPACE_UNRESOLVED` |
| R39 保留 WIP 随实际处置解除 | 代码 | **已修（§31）** | 真实 `stop commit` 后不再阻断；`stop keep` 仍阻断 |

落地前「首轮完整性闭合」的表述不成立；落地后重跑授予相关（CP2、R1R2、R32、R37）、收工/恢复相关（CP1 A23、R24、R29）与三夹具全流程、F0。

## 31. R38–R39 实施与实跑（2026-11-04）

复核文见 `review-round8-reconciliation.md`。

### 31.1 第八轮用例（12/12）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R38 准备：开工 | WF_OK | WF_OK facts={"baseline_head": "c8de60249f6bb5171dc3c5a62e872c4df38c701 | PASS |
| R38 准备：保留 WIP | WF_OK | WF_OK facts={"commit": null, "control_assertion": {"anchor": "sha256:2 | PASS |
| R38 准备：WIP 已被识别 | 列出该任务 | True | PASS |
| R38 task-new 被同一前置拦住 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R38 bind 被同一前置拦住 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R38 统一前置对 writer acquire 同判 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R39 keep 记录 resolved 为空 | resolved=None | None | PASS |
| R39 准备：恢复前取得写权 | WF_OK | WF_OK writer_state=idle facts={"control_assertion": {"anchor": "sha256 | PASS |
| R39 路径仍脏时 resume 不写解除 | resolved 仍为 None | None | PASS |
| R39 收工提交成功 | WF_OK | WF_OK | PASS |
| R39 提交后写解除结论 | resolved.choice=commit | {"at": "2026-11-03T08:20:32.625269Z", "choice": "commit", "evidence":  | PASS |
| R39 已提交不再阻断他对象 | 空列表 | [] | PASS |

### 31.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R38** 授予写权的统一前置 | 新增 `cli.assert_no_foreign_wip(ctx, exclude_id)`；`writer acquire`（排除本对象）、`bind`（不排除）、`task-new`（无可排除）三处在各自 `lock` 内调用 | 保留 WIP 存在时：`task-new`/`bind`/`writer acquire`（另一对象）均 `WF_WORKSPACE_UNRESOLVED`；同一对象重新取得写权仍允许 |
| **R39** 处置后解除 | `stop` 按选择写 `handoff.wip.resolved`（commit/reverse/transfer 带证据，keep 留空）；`wip_blockers` 改为**状态事实**判据（保留路径仍在工作树差异中才算阻断）；`task-resume` 在路径已干净时补写解除依据 | `keep` → 仍阻断；真实 `stop commit` → `resolved.choice=commit` 且不再阻断；恢复前路径仍脏时不写解除 |

### 31.3 回归（第八轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第八轮 R38–R39 | 12/12 |
| 第七 / 第六 / 第五 / 第四 / 第三轮 | 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 31.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R23 | `bind` 的排除写反了 | 初版 `bind` 排除目标对象，导致「把新会话绑到带保留 WIP 的任务」仍被允许（等于绕过） | `bind` 不排除，任何保留 WIP 都阻断新绑定 |
| N-R24 | WIP 判据只认登记不认状态 | 旧 `wip_blockers` 只看 `paths` 是否存在，`stop commit` 后仍长期阻断 | 改为与工作树差异求交，已处置即放行 |

### 31.5 重绑

- 修订前：`sha256 52918e67…`（781 行）
- 修订后：`sha256 a6ed1b8cec681aec65cefb6386b16a7ef6aba8de83a2ea2d9ed51110e82324df`（783 行）
- 改写：§2.3.4 的「保留 WIP 共同消费」「授予写权的统一前置」「解除结论写回」。

### 31.6 收口状态

第八轮 2 条闭环；R38–R39 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 32. R40–R42 实施与实跑（2026-11-04）

复核文见 `review-round9-reconciliation.md`。

### 32.1 第九轮用例（10/10）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R40 准备：开工 | WF_OK | WF_OK | PASS |
| R40 释放写权（改动仍归属该任务） | WF_OK | WF_OK | PASS |
| R40 未登记改动被识别 | 列出 a40/x.txt | [{"task": "2026-d89f61ecec6147f78591888995e82081", "paths": ["a40/x.tx | PASS |
| R40 其他对象 task-new 被拒 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R41 同对象接续被允许 | WF_OK | WF_OK | PASS |
| R41 接续响应带出保留 WIP | inherited_wip 含 a40/x.txt | {"paths": ["a40/x.txt"], "registered": false, "task": "2026-d89f61ecec | PASS |
| R42 准备：接续取得写权 | WF_OK | WF_OK | PASS |
| R42 内容变化时恢复被拒 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| R42 报告变化路径与指纹 | changed 含 a40/x.txt | [{"current": {"digest": "sha256:e2208f01e42b2cab0fef975b55dc70d39579dd | PASS |
| R42 指纹一致时恢复通过 | WF_OK | WF_OK | PASS |

### 32.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R40** 未登记脏改动 | `wip_blockers` 并入「该任务可见的未提交交付路径」（`classify_candidates` e 桶 ∩ 差异），与登记路径取并集，facts 标 `registered` | 暂停+脏改动 → 其他对象 `task-new` 被拒；`wip_blockers` 列出 `a40/x.txt` |
| **R41** 同对象接续 | `bind` 排除目标对象、放行同对象接续，响应交回 `inherited_wip`（含未登记脏改动与原始 WIP 记录） | 同对象 `bind` → `WF_OK` 且带 `inherited_wip` |
| **R42** 恢复指纹 | 恢复前逐条比较保存的 `{path,exists,kind,executable,digest}` 与当前指纹，不一致即拒绝并给 `changed` | 内容替换 → 拒绝并列出变化；恢复原值 → 通过 |

### 32.3 回归（第九轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第九轮 R40–R42 | 10/10 |
| 第八 / 第七 / 第六 / 第五 / 第四 / 第三轮 | 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 32.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R25 | 用例未在两例之间提交 | CP1 的 A22 用例留下归属该任务的脏文件，触发新的授予前置，导致后续用例 `task-new` 被拒 | 两例之间补 `clean()`（把残留提交后再进入下一例），不改框架行为 |
| N-R26 | R38 用例断言过时 | R41 允许同对象接续后，「bind 被拦」不再成立 | 该断言换成 R40–R42 套件的同对象/换对象两条 |

### 32.5 重绑

- 修订前：`sha256 a6ed1b8c…`（783 行）
- 修订后：`sha256 cb82928efb99a791dc2e1df342489c0be9c4ed78fbe1ab5899e16aee40f47f9f`（785 行）
- 改写：§2.3.4 的「保留 WIP 共同消费」（并入未登记脏改动）、授予前置（bind 同对象放行 + `inherited_wip`）、恢复前的指纹核对。

### 32.6 收口状态

第九轮 3 条闭环；R40–R42 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 33. R43–R45 实施与实跑（2026-11-04）

复核文见 `review-round10-reconciliation.md`。

### 33.1 第十轮用例（16/16）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R43 准备：开工 | WF_OK | WF_OK | PASS |
| R43 准备：Check 通过 | WF_OK | WF_OK | PASS |
| R43 新增命中规则后旧 Check 失效 | WF_CHECK_STALE | ok=False code=WF_CHECK_STALE | PASS |
| R43 报告新旧锚点差异 | facts 含 saved/current | {"saved": "sha256:4c5db94bc7fdb5097385174606c4bb4d4553f935dc0e88e81134 | PASS |
| R44 准备：B 创建 | 创建成功 | 2026-4475d1734 | PASS |
| R44 准备：A 开工 | WF_OK | WF_OK facts={"baseline_head": "c35ac8cb2b7195b75b08a866f01feeb74880480 | PASS |
| R44 准备：A 保存 WIP 归属 | WF_OK | WF_OK | PASS |
| R44 A 的接续条件不把文件算给 B | B 不在列或 B 无该路径 | [] | PASS |
| R44 显式归属仍计入 A | A 被列为 WIP 持有者 | [{"task": "2026-eeb95d05e89d45afbcda02d8a7942547", "paths": ["src/a.py | PASS |
| R45 准备：开工 | WF_OK | WF_OK | PASS |
| R45 准备：删除态保留 WIP | WF_OK | WF_OK | PASS |
| R45 准备：接续取得写权 | WF_OK | WF_OK | PASS |
| R45 未提交删除可恢复 | WF_OK | WF_OK | PASS |
| R45 准备：写权仍在接续会话 | held | held | PASS |
| R45 删除已提交后仍可恢复 | WF_OK | WF_OK | PASS |
| R45 写回解除结论 | resolved.choice=resume-after-disposal | {"at": "2026-11-03T08:39:30.458953Z", "choice": "resume-after-disposal | PASS |

### 33.2 逐项实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R43** 命中集合进入锚点 | `check.spec_versions()` 改为「策展 ∪ 交付路径实际命中的 spec」（复用 `spec.match`） | 新增命中规则后旧 Check → `WF_CHECK_STALE`，facts 给新旧锚点 |
| **R44** 归属优先 | `wip_blockers` 先建「显式归属表」（`handoff.wip.paths` → task id），未登记脏改动排除已被他任务显式记录的路径 | A 保存归属后 B 不再认领 `src/a.py`；A 仍被列为持有者 |
| **R45** 已持久化删除 | 区分「记录即删除」（`exists: false`）与「记录为存在」，前者在当前仍不存在且已不在差异中即放行并写回 `resolved` | 删除提交后恢复通过，`resolved.choice=resume-after-disposal` |

### 33.3 回归（第十轮改动后全量重跑）

| 套件 | 结果 |
|---|---|
| 第十轮 R43–R45 | 16/16 |
| 第九 / 第八 / 第七 / 第六 / 第五 / 第四 / 第三轮 | 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 33.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R27 | 用例构造触碰新前置 | R44 的「重叠任务 B」若在 A 产生 WIP 之后创建，会被 R40 的前置直接拦住；R43 的用例也需先释放写权 | 用例改为「先建 B 并提交、再让 A 产生 WIP」「R43 结束时暂停并释放」，不改框架行为 |

### 33.5 重绑

- 修订前：`sha256 cb82928e…`（785 行）
- 修订后：`sha256 5f5b543d1bfdaccfc58c2770cd5ea2af7716a3b56face8e1314d3995bd463484`（788 行）

### 33.6 收口状态

第十轮 3 条闭环；R43–R45 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 34. R46 实施与实跑（2026-11-04）

复核文见 `review-round11-reconciliation.md`。

### 34.1 用例（5/5，含只改一个事实的对照）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R46 准备：开工 | WF_OK | WF_OK | PASS |
| R46 对照：合法条目命中即阻断 | WF_SPEC_INCOMPLETE | WF_SPEC_INCOMPLETE | PASS |
| R46 单条非法不放过合法条目 | WF_SPEC_INCOMPLETE 且 matched 含该规则 | WF_SPEC_INCOMPLETE matched=['.wf/spec/rules/with-bad-entry.md'] | PASS |
| R46 非法条目作为可见报告 | path_problems 列出该条 | [{"kind": "path", "path": ".wf/spec/rules/with-bad-entry.md", "problem | PASS |
| R46 元数据不可靠时整文件不可路由 | 不进入 matched、列入 unparsed | matched=[] unparsed=['.wf/spec/index.md', '.wf/spec/pre-dev-checklist. | PASS |

### 34.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R46** 单条非法只失效该条 | `validate_metadata` 返回 `(problems, valid_paths, path_problems)`；`load_spec` 加 `routable`（仅元数据级错误/解析失败为假）；`match` 只在不可路由时整份跳过，否则用合法条目匹配并把路径问题作为 `kind: path` 报告；`_spec_coverage` 单列 `path_problems` | 「`["pkg/**","../invalid/**"]`」仍阻断且 `matched` 含该规则、`path_problems` 列出非法条目；改为 `status: bogus` 后整文件不可路由 |

### 34.3 回归

| 套件 | 结果 |
|---|---|
| 第十一轮 R46 | 5/5 |
| 第十 / 九 / 八 / 七 / 六 / 五 / 四 / 三轮 | 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 34.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 本轮改动未引出新的实现缺陷；`cp4_tests` 的 A4 用例随 `validate_metadata` 返回值扩为三元组同步更新 | — |

### 34.5 收口状态

第十一轮 1 条闭环；R46 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 35. R47–R48 实施与实跑（2026-11-04）

复核文见 `review-round12-reconciliation.md`。

### 35.1 用例（8/8）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R47 准备：开工 | WF_OK | WF_OK | PASS |
| R47 越界链接被拒绝 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R47 未写入完整读取侧车 | 侧车无该路径记录 | [] | PASS |
| R47 外部正文未进入结果 | 正文缺失 | True | PASS |
| R48 准备：开工 | WF_OK | WF_OK | PASS |
| R48 嵌套仓库目标被拒 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R48 拒绝时零写入 | new.md 未生成 | False | PASS |
| R48 报告嵌套根位置 | facts 含 nested repository root | {"path": ".wf/spec/child/new.md", "reason": "target crosses a nested r | PASS |

### 35.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R47** 读取真实落点 | 新增 `spec.path_violation()`（realpath 越界 / 嵌套仓库根）；`load_spec` 命中即返回 `routable:false` + `violation`，不返回正文；`cmd_spec` 转 `WF_PATH_INVALID` | 越界链接 → `WF_PATH_INVALID`，无侧车记录、无正文 |
| **R48** 写入嵌套仓库 | `validate_changes` 追加 `paths.nested_repo_boundary()` 判定 | 嵌套根内目标 → `WF_PATH_INVALID`、零写入、facts 带嵌套根路径 |

### 35.3 回归

| 套件 | 结果 |
|---|---|
| 第十二轮 R47–R48 | 8/8 |
| 第十一 / 十 / 九 / 八 / 七 / 六 / 五 / 四 / 三轮 | 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 35.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 读取与写入共用同一个 `path_violation` 判据，未引出新缺陷 | — |

### 35.5 收口状态

第十二轮 2 条闭环；R47–R48 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 36. R49 实施与实跑（2026-11-04）

复核文见 `review-round13-reconciliation.md`。

### 36.1 用例（7/7）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R49 准备：开工 | WF_OK | WF_OK | PASS |
| R49 文件链接进嵌套仓库被拒 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R49 未返回正文字段 | facts.content 缺失 | True | PASS |
| R49 未写完整读取侧车 | 侧车无记录 | [] | PASS |
| R49 目录链接进嵌套仓库被拒 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R49 拒绝时零写入 | 嵌套仓库内 new.md 未生成 | False | PASS |
| R49 正例：普通 spec 可写 | WF_OK | WF_OK | PASS |

### 36.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R49** 真实祖先边界 | 新增 `paths.nested_repo_boundary_real()`（按真实路径逐段核 `.git`）；`spec.path_violation` 与 `validate_changes` 都改为「字面判定 或 真实判定」 | 文件链接读嵌套仓库 → `WF_PATH_INVALID`、无侧车、无正文；目录链接写嵌套仓库 → `WF_PATH_INVALID`、零写入；普通 spec 读写照常 |

### 36.3 回归

| 套件 | 结果 |
|---|---|
| 第十三轮 R49 | 7/7 |
| 第十二 / 十一 / 十 / 九 / 八 / 七 / 六 / 五 / 四 / 三轮 | 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 36.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R28 | 用例夹具用了目录形态的 `.git` | 目录形态的嵌套仓库无法被 `git add` 收进夹具，导致 `task-start` 因未归属改动被拒；改用 gitfile 形态（同为契约认可的嵌套根标记） | 用例夹具改用 `.git` 文件 |

### 36.5 收口状态

第十三轮 1 条闭环；R49 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 37. R50 实施与实跑（2026-11-04）

复核文见 `review-round14-reconciliation.md`。

### 37.1 用例（7/7）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R50 准备：开工 | WF_OK | WF_OK | PASS |
| R50 baseline-apply 拒绝嵌套仓库目标 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R50 baseline-apply 零写入 | 嵌套仓库内未生成 | False | PASS |
| R50 报告嵌套根原因 | facts 含 nested repository root | {"path": ".wf/spec/alias/baseline-created.md", "reason": "nested repos | PASS |
| R50 spec 写入对同一目标一致拒绝 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R50 两入口原因一致 | 同为 nested repository root | baseline={"path": ".wf/spec/alias/baseline-created.md", "reason": "nes | PASS |
| R50 正例：普通骨架可写 | WF_OK | WF_OK | PASS |

### 37.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R50** 统一边界判据 | 新增 `paths.boundary_violation()`（项目包含性 + 字面祖先 + 真实祖先）；`spec.path_violation`、`spec.validate_changes`、`cmd_baseline_apply` 三处改为调用它 | 同一目标经两个入口都 `WF_PATH_INVALID` 且 reason 一致；普通骨架仍可写 |

### 37.3 回归

| 套件 | 结果 |
|---|---|
| 第十四轮 R50 | 7/7 |
| 第十三 … 第三轮 | 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 | 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 37.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R29 | 判据重复实现 | 边界逻辑在 spec 与 baseline 各写一份，第三个入口漏接 | 抽成 `paths.boundary_violation()` 单一来源 |

### 37.5 收口状态

第十四轮 1 条闭环；R50 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 38. R51–R52 实施与实跑（2026-11-04）

复核文见 `review-round15-reconciliation.md`。

### 38.1 用例（9/9）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R51 缺 design/implement 不得批准 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R51 报告缺失产物 | 列出 design.md 与 implement.md | [{"artifact": "design.md", "fields": ["contract", "title", "tradeoffs" | PASS |
| R51 保留占位不得批准 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R51 报告未填占位 | reason=unfilled placeholders | ['unfilled placeholders'] | PASS |
| R51 补齐后批准通过 | WF_OK | WF_OK | PASS |
| R51 开工复核通过 | WF_OK | WF_OK | PASS |
| R52 disable 成功 | WF_OK | WF_OK | PASS |
| R52 结果仍可解析 | 无 problems 且 status=disabled | problems=[] status=disabled | PASS |
| R52 结束分隔符保留 | 第二个 --- 存在 | True | PASS |

### 38.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R51** 复杂产物门禁 | 新增 `complex_artifact_problems()`（缺失/未填占位）；`task-approve` 与 `task-start` 复核处调用，`WF_TEMPLATE_INCOMPLETE` | 缺文件、留占位均被拒并报告产物的 reason；补齐后批准与开工均通过 |
| **R52** disable 结构 | `_rewrite_frontmatter` 补回结束 `---`；写盘后重新解析并核 `status=disabled`，失败即 `WF_RECORD_INVALID` | disable 后 `problems=[]`、`status=disabled`、分隔符计数 ≥2 |

### 38.3 回归

| 套件 | 结果 |
|---|---|
| 第十五轮 R51–R52 | 9/9 |
| 第十四 … 第三轮 | 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 38.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R30 | 用例断言不可序列化 | `set` 与 `assertEqual` 之类进入 `actual` 会中断落盘 | 断言值改为 `sorted(...)` 列表 |

### 38.5 收口状态

第十五轮 2 条闭环；R51–R52 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 39. R53 实施与实跑（2026-11-04）

复核文见 `review-round16-reconciliation.md`。

### 39.1 用例（9/9）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R53 连字符字段可识别 | ['data-flow', 'non-goals'] | ['data-flow', 'non-goals'] | PASS |
| R53 普通字符串不误判 | 不报值占位 | True | PASS |
| R53 两个空文件不得批准 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R53 报告空产物 | reason=empty | ['empty'] | PASS |
| R53 只有标题算空正文 | WF_TEMPLATE_INCOMPLETE 且 reason=empty body | WF_TEMPLATE_INCOMPLETE ['empty body'] | PASS |
| R53 连字符占位不得批准 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R53 报告具体连字符字段 | ['data-flow'] | ['data-flow'] | PASS |
| R53 补齐后批准通过 | WF_OK | WF_OK | PASS |
| R53 补齐后开工通过 | WF_OK | WF_OK | PASS |

### 39.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R53** 空产物与连字符标记 | `MARKER_PATTERN` 扩为 `[A-Za-z0-9_-]+`（成品校验、`double_check`、`template_markers` 登记同时生效）；`complex_artifact_problems` 增加 `empty` / `empty body` 两层空判定 | 空文件、只有标题、连字符占位均被拒并逐份报告 reason/fields；补齐后批准与开工通过；`data-flow`/`non-goals` 可识别且普通字符串不误判 |

### 39.3 回归

| 套件 | 结果 |
|---|---|
| 第十六轮 R53 | 9/9 |
| 第十五 … 第三轮（13 套） | 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 39.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R31 | 发行清单登记的标记数偏少 | 收紧前的正则使 5 个连字符占位（`data-flow`/`non-goals`/`verification-commands`/`example-good`/`example-bad`）从未登记，`double_check` 的「漏登记」方向因此形同虚设 | 放宽正则后登记 19 个标记，全部可双向核对 |

### 39.5 收口状态

第十六轮 1 条闭环；R53 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 40. R54 实施与实跑（2026-11-04）

复核文见 `review-round17-reconciliation.md`。

### 40.1 用例（10/10）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R54 contract=true 未指定分级 → 要求复杂产物 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R54 报告按 complex 要求 | facts.complexity=complex | complex | PASS |
| R54 补齐后通过 | WF_OK | WF_OK | PASS |
| R54 分级落为 complex | plan.complexity=complex | complex | PASS |
| R54 条件事实入库 | reasons 含 contract | ['contract'] | PASS |
| R54 scope=unknown 同样要求产物 | WF_TEMPLATE_INCOMPLETE | WF_TEMPLATE_INCOMPLETE | PASS |
| R54 有理由可降级为 light | WF_OK | WF_OK | PASS |
| R54 降级留痕 | reasons 含 downgrade | True | PASS |
| R54 无理由降级被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R54 无条件为 light 且通过 | WF_OK 且 complex=light | WF_OK light | PASS |

### 40.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R54** 四项条件先汇总 | `_complexity_proposal(..., extra_conditions)`；顺序改为「汇总 → 提议 → 定级（人工只能降级）→ 降级须理由证据 → 产物检查」；删掉用旧 `plan.complexity` 的前置产物检查 | `contract=true` 不给级 → 按 complex 要求产物、补齐后落 `complex`；`scope=unknown` 同判；显式 light 无理由被拒、有理由通过并留痕；无条件仍 light |

### 40.3 回归

| 套件 | 结果 |
|---|---|
| 第十七轮 R54 | 10/10 |
| 第十六 … 第三轮（14 套） | 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 40.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R32 | 产物检查判了两遍且首遍用旧值 | 第一次用 `task.plan.complexity`（新任务恒为 None），等价于白判 | 合并为一次，放在分级定稿之后 |

### 40.5 收口状态

第十七轮 1 条闭环；R54 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 41. R55 实施与实跑（2026-11-04）

复核文见 `review-round18-reconciliation.md`。

### 41.1 用例（8/8，单变量对照）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R55 approve 决定被接受 | WF_OK | WF_OK | PASS |
| R55 approval.choice 落库为 approve | approve | approve | PASS |
| R55 approve 后可开工 | WF_OK | WF_OK | PASS |
| R55 阶段进入 execute | execute | execute | PASS |
| R55 reject 决定不得批准 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R55 reject 后不得开工 | WF_APPROVAL_MISSING 或 WF_SEMANTIC_DECISION | WF_APPROVAL_MISSING | PASS |
| R55 门禁复核 approval.choice | WF_APPROVAL_MISSING | WF_APPROVAL_MISSING | PASS |
| R55 对象摘要不符被拒 | WF_APPROVAL_MISSING | WF_APPROVAL_MISSING | PASS |

### 41.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R55** 消费批准决定 | `APPROVE_CHOICES` + 从决定集筛出批准决定；无批准即 `WF_SEMANTIC_DECISION`；`object_digest` 必须等于当前 PRD 摘要（`subject` 含任务 id 时兜底）；门禁复核 `approval.choice` | `reject` 决定被拒且不能开工；批准后把 `approval.choice` 改成 `reject` → 开工 `WF_APPROVAL_MISSING`；摘要不符被拒；正常路径 `approve` 落库并进 execute |

### 41.3 回归

| 套件 | 结果 |
|---|---|
| 第十八轮 R55 | 8/8 |
| 第十七 … 第三轮（15 套） | 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 41.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 现有用例的决定本就写 `approve`，因此加严后无回归 | — |

### 41.5 收口状态

第十八轮 1 条闭环；R55 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 42. R56 实施与实跑（2026-11-04）

复核文见 `review-round19-reconciliation.md`。

### 42.1 用例（4/4，单变量配置对照）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R56 准备：开工 | WF_OK | WF_OK | PASS |
| R56 合法周期 1 天 → 到期阻断 | WF_SPEC_INCOMPLETE | WF_SPEC_INCOMPLETE period=1 | PASS |
| R56 非法值阻断（不按 90 天放行） | WF_SPEC_INCOMPLETE 且 period_problems 非空 | WF_SPEC_INCOMPLETE problems=['spec_verify_days must be a positive inte | PASS |
| R56 键缺失按缺省且不阻断周期 | WF_OK 且记录 period_days=90、无 period_problems | WF_OK period=90 problems=[] | PASS |

### 42.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R56** 非法周期阻断 | 区分键缺失（缺省、不阻断）与键存在但非法（`period_problems` + 阻断）；`period_problems` 与既有缺项同列触发 `WF_SPEC_INCOMPLETE`；`period_days`/`period_problems` 进入 `check.spec_review` | 合法 `1` → 到期阻断；非法 `"invalid-period"` → 同样阻断并给问题；键缺失 → `WF_OK` 且记录 `period_days=90`、无问题 |

### 42.3 回归

| 套件 | 结果 |
|---|---|
| 第十九轮 R56 | 4/4 |
| 第十八 … 第三轮（16 套） | 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 42.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R33 | 通过分支不返回 `facts.spec` | 无阻断时调用方看不到 `period_days`，用例只能改从记录读 | 用例改为读 `check.spec_review`；实现侧 `spec_review` 已随记录保存，无需改返回结构 |

### 42.5 收口状态

第十九轮 1 条闭环；R56 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 43. R57 实施与实跑（2026-11-04）

复核文见 `review-round20-reconciliation.md`。

### 43.1 用例（7/7）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R57 键缺失取缺省 | 90 | 90 | PASS |
| R57 非法正整数报问题 | must be a positive integer | spec_verify_days must be a positive integer | PASS |
| R57 0 也是非法 | None | None | PASS |
| R57 字符串布尔非法 | None | None | PASS |
| R57 配置整体非对象→依赖键非法 | None | None | PASS |
| R57 配置为数组→入口被拒 | 非 WF_OK | WF_EXECUTOR_UNCONFIRMED facts={"detail": "project config is not a JSON | PASS |
| R57 预算 0 → spec 读取被拒 | WF_CAPABILITY_UNAVAILABLE | WF_CAPABILITY_UNAVAILABLE | PASS |

### 43.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R57** 统一取值器 | `config.value_of()`：键缺失→缺省（不阻断）；非法/整体不可读→`(None, problem)`；回扫四个消费者全部改用它，TDD 默认非法不再 `bool()` 取反 | 单元 5 条覆盖缺失/非法/0/字符串布尔/整体非对象；入口层：配置为数组被拒、预算 0 → spec 读取 `WF_CAPABILITY_UNAVAILABLE` |

### 43.3 回归

| 套件 | 结果 |
|---|---|
| 第二十轮 R57 / 第十九轮 R56 | 7/7 / 4/4 |
| 第十八 … 第三轮（16 套） | 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 43.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R34 | 周期为 None 时比较抛错 | `value_of` 返回 `None` 后仍执行 `days > None` → `TypeError`，R56 用例先失败 | 周期不可用时先落缺省值再参与计算，阻断仍由 `period_problems` 负责 |

### 43.5 收口状态

第二十轮 1 条闭环；R57 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 44. R58 实施与实跑（2026-11-04）

复核文见 `review-round21-reconciliation.md`。

### 44.1 用例（10/10）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R58 无关字段错误不扩散到缺失键 | 90 | 90 | PASS |
| R58 结构级错误阻断缺失键 | None | None | PASS |
| R58 结构级错误阻断已给的合法键 | None | None | PASS |
| R58 无关字段错误不影响自身合法键 | 5 | 5 | PASS |
| R58 准备：开工 | WF_OK | WF_OK | PASS |
| R58 准备：一次失败留下 | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R58 准备：第二次失败（历史留痕） | WF_CHECK_FAILED | WF_CHECK_FAILED | PASS |
| R58 准备：第三次通过 | WF_OK | WF_OK | PASS |
| R58 阈值=1 时要求裁定 | WF_SEMANTIC_DECISION 且 pending 非空 | ok=False code=WF_SEMANTIC_DECISION facts={"unruled_debug_multiples": [ | PASS |
| R58 阈值非法时同样阻断（不再按 3 放行） | WF_CAPABILITY_UNAVAILABLE 且指出该键 | code=WF_CAPABILITY_UNAVAILABLE facts={"reason": "debug_repeat_threshol | PASS |

### 44.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R58-a** 阈值消费 | `debug_threshold()` 有 problem 即抛 `WF_CAPABILITY_UNAVAILABLE` | 阈值 `1` → 归档门禁要求裁定；阈值 `"bad"` → 同样阻断并指出该键 |
| **R58-b** 分类 | problems 结构化 `{level,key,message}`；`value_of` 按 level 判定，无关字段错误不扩散，结构错误约束全部键；配置缺失且允许缺失走缺省 | 无关字段错误 + 缺失键 → 仍取缺省；结构错误 → 缺失键与已给合法键都阻断；无关字段错误 + 自身合法值 → 通过 |

### 44.3 回归

| 套件 | 结果 |
|---|---|
| 第二十一轮 R58 / 第二十轮 R57 / 第十九轮 R56 | 10/10 / 7/7 / 4/4 |
| 第十八 … 第三轮（16 套） | 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 44.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R35 | 配置缺失被误判非法 | 初始化任务在写入配置前批准，`value_of` 把「缺 config」当不可读而阻断 | 配置为 None 且无 problems 时返回缺省 |
| N-R36 | R57 单测仍用字符串 problems | 结构化为 dict 后旧断言报 `'str' object has no attribute 'get'` | 单测改用结构化 problem |

### 44.5 收口状态

第二十一轮 2 条闭环；R58 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 45. R59 实施与实跑（2026-11-04）

复核文见 `review-round22-reconciliation.md`。

### 45.1 用例（8/8）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R59 未提交时为待提交 | applied_pending_commit | applied_pending_commit | PASS |
| R59 待提交计入重叠阻断 | 非空 | 1 | PASS |
| R59 完整提交后派生 persisted | persisted | persisted | PASS |
| R59 不再计入门禁重叠 | 空 | 0 | PASS |
| R59 工作区干净 |  |  | PASS |
| R59 回执本身未被改写（不写 writer） | result 仍是 applied_pending_commit | applied_pending_commit | PASS |
| R59 重叠任务创建 | 创建成功 | 2026-fa6ab84 | PASS |
| R59 重叠任务可开工（不再 WF_WIP_UNRESOLVED） | WF_OK | WF_OK | PASS |

### 45.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R59** 可达提交查证接入 | 新增 `maintenance_persisted_probe()`；`task_receipts()` 统一带 probe；开工重叠检查与 `inspect` 改调统一读取 | 未提交 → `applied_pending_commit` 并阻断；完整提交后 → `persisted`、不再阻断、重叠任务可开工；回执 `result` 未被改写 |

### 45.3 回归

| 套件 | 结果 |
|---|---|
| 第二十二轮 R59 | 8/8 |
| 第二十一 … 第三轮（18 套） | 10/10 / 7/7 / 4/4 / 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 45.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R37 | 用例时序把「提交回执」当成「未提交」 | 首轮在写回执后立刻提交，第一步就已是 persisted | 用例改为「写回执不提交 → 断言待提交 → 再提交 → 断言 persisted」 |

### 45.5 收口状态

第二十二轮 1 条闭环；R59 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 46. R60 实施与实跑（2026-11-04）

复核文见 `review-round23-reconciliation.md`。

### 46.1 用例（6/6）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R60 多文件回执不抛排序异常 | applied_pending_commit | applied_pending_commit | PASS |
| R60 仅提交文件、回执未提交时为待提交 | applied_pending_commit | applied_pending_commit | PASS |
| R60 提交树内容与登记不符→仍待提交 | applied_pending_commit | applied_pending_commit | PASS |
| R60 后续提交树已含完整结果→persisted | persisted | persisted | PASS |
| R60 不可核回执为 pending_check | pending_check | pending_check | PASS |
| R60 待核回执进入门禁（不再被忽略） | WF_HISTORY_UNRESOLVED | WF_HISTORY_UNRESOLVED | PASS |

### 46.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R60-a** 核树终态 | `_committed_digest()` 读候选提交树内容；probe 逐项比较登记 `after`，不再要求同一次 diff | 内容与登记不符 → 仍待提交；后续提交树已含完整结果 → persisted |
| **R60-b** 稳定排序 | `_changes_by_path()` 按 path 排序（两处比较都用它） | 两文件回执不再抛 `'<' not supported` |
| **R60-c** 待核进门禁 | `pending_check` 的 facts 带 `paths`；门禁把待核判 `WF_HISTORY_UNRESOLVED` | 不可核回执 → 开工会被 `WF_HISTORY_UNRESOLVED` 挡住 |

### 46.3 回归

| 套件 | 结果 |
|---|---|
| 第二十三轮 R60 / 第二十二轮 R59 | 6/6 / 8/8 |
| 第二十一 … 第三轮（18 套） | 10/10 / 7/7 / 4/4 / 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 46.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R38 | 待核回执不带路径 | `pending_check` 的 facts 只有 `result`，门禁无从匹配 → 首轮用例仍放行 | 两个 pending_check 分支都补 `paths` |

### 46.5 收口状态

第二十三轮 1 条闭环；R60 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 47. R61 实施与实跑（2026-11-04）

复核文见 `review-round24-reconciliation.md`。

### 47.1 用例（6/6）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R61 可执行位不符→仍待提交 | applied_pending_commit | applied_pending_commit | PASS |
| R61 完整状态一致→persisted | persisted | persisted | PASS |
| R61 登记删除且确实删除→persisted | persisted | persisted | PASS |
| R61 历史摘要登记兼容 | persisted | persisted | PASS |
| R61 探测异常→pending_check 且带路径 | pending_check 且 paths 非空 | pending_check paths=['pkg/g.txt'] | PASS |
| R61 探测异常→门禁待核出口 | WF_HISTORY_UNRESOLVED | WF_HISTORY_UNRESOLVED | PASS |

### 47.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **R61-a** 完整指纹 | `_committed_fingerprint()` 按提交树重建存在/类型/可执行位/摘要，`_fp_matches()` 按字段比；历史纯摘要仍兼容；dev-deploy 登记改为完整指纹 | 可执行位不符 → 仍待提交；一致 → persisted；登记删除且确实删除 → persisted；历史摘要仍可判 |
| **R61-b** 待核带路径 | `probe failed` 分支补 `paths`，与另两个待核分支一致 | 探测抛异常 → `pending_check` 且带路径、门禁 `WF_HISTORY_UNRESOLVED` |

### 47.3 回归

| 套件 | 结果 |
|---|---|
| 第二十四轮 R61 / 第二十三轮 R60 / 第二十二轮 R59 | 6/6 / 6/6 / 8/8 |
| 第二十一 … 第三轮（18 套） | 10/10 / 7/7 / 4/4 / 8/8 / 10/10 / 9/9 / 9/9 / 7/7 / 7/7 / 8/8 / 5/5 / 16/16 / 10/10 / 11/11 / 15/15 / 13/13 / 10/10 / 30/30 / 37/37 |
| R1/R2、R3+R5 | 14/14、10/10 |
| CP1 / CP2 / CP3 / CP4 / CP5 | 20/20 / 14/14 / 17/17 / 6/6 / 8/8 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 8/8 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 47.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 三个待核分支补齐后再无漏路径；历史摘要兼容用例证明格式升级不破坏旧记录 | — |

### 47.5 收口状态

第二十四轮 2 条闭环；R61 落地。仍未运行项仅剩 D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行。

## 48. R62 实施与实跑（2026-11-04）

复核文见 `review-round25-reconciliation.md`。P1 四条 + P2 前五条已修；P2-6/P2-7/P3 登记待修。

### 48.1 用例（10/10）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| P1-1 pass 时历史 fail 仍可重建 | 存在 review_fail 触发 | [] | PASS |
| P1-1 outcome=fail 重建触发 | 含 review_fail | ['review_fail'] | PASS |
| P1-2 无成果的调查任务不满足 | WF_CHECK_FAILED | False WF_CHECK_FAILED | PASS |
| P1-2 有人判即可满足 | 满足 | True | PASS |
| P1-3 门禁按 plan 事实而非入口写入 | work_satisfied 不写 knowledge | True | PASS |
| P1-4 status 报告启动核验事实 | 含 startup 面 | True | PASS |
| P2-4 降级批准通过 | WF_OK | WF_OK | PASS |
| P2-4 版本只按条件条目计算 | 重算等于保存值 | True | PASS |
| P2-4 降级条目仍留痕 | reasons 含 downgrade | [None, True] | PASS |
| P2-5 task-knowledge 对归档任务拒绝 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |

### 48.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **P1-1** | `review.decide` 写 `attempts[].outcome` | `outcome=fail` 可重建 `review_fail` 触发 |
| **P1-2** | 调查任务须有可观察成果 | 空成果 → `WF_CHECK_FAILED`；有人判 → 通过 |
| **P1-3** | knowledge 改写 `execution.spec_changes` | 门禁不再被入口旁路 |
| **P1-4** | 新增 `startup_check()` 并挂 `status` | `status` 输出按序 `startup` 事实 |
| **P2-1** | 证据存在性与 dedupe 目标核验 | 缺证据/悬空 dedupe 分别给码 |
| **P2-2** | Trellis 三档需 `trellis_loaded` 才 blocked | 未声明 → 待核；声明 → 冲突 |
| **P2-3** | run 走 `WF_CAPABILITY_UNAVAILABLE` | 不再 70 |
| **P2-4** | 降级不进哈希域；review-passed 适用 all | 重算等于保存值、降级仍留痕 |
| **P2-5** | 归档任务拒绝 knowledge 写入 | `WF_BINDING_MISMATCH` |

### 48.3 回归

| 套件 | 结果 |
|---|---|
| 第二十五轮 R62 | 10/10 |
| CP1 / CP2 | 20/20 / 15/15（A14 与 B1 期望按新档位更新） |
| 其余 17 套（CP3–CP5、R1–R61） | 全通过 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 9/9 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 48.4 待修登记

P2-6（日志脱敏）、P2-7（副本来源登记）、P3 若干条——见复核文 §4，未计入本轮完成。

## 49. R63 实施与实跑（P2-6、P2-7，2026-11-04）

复核文见 `review-round26-reconciliation.md`。

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 脱敏 key=value | api_key=*** | api_key=*** | PASS |
| 脱敏 sk- 形态 | Bearer *** | Bearer *** | PASS |
| 不误伤普通输出 | tests passed | tests passed | PASS |
| 日志遮罩秘密 | 含 *** 且不含明文 | masked=True plain=True | PASS |
| facts 摘要素遮罩 | summary 含 *** | token=*** | PASS |
| P2-7 wf-grilling 来源登记齐全 | 六项齐全 | ok | PASS |
| P2-7 wf-tdd 来源登记齐全 | 六项齐全 | ok | PASS |
| P2-7 wf-diagnosing-bugs 来源登记齐全 | 六项齐全 | ok | PASS |
| P2-7 wf-code-review 来源登记齐全 | 六项齐全 | ok | PASS |
| P2-7 wf-review 来源登记齐全 | 六项齐全 | ok | PASS |
| P2-7 wf-review-action 来源登记齐全 | 六项齐全 | ok | PASS |

实施：`check.redact_secrets()` 应用于摘要与 argv，日志/facts 同步脱敏；六个改编副本补「来源与差异」段，README 增 §6。

## 50. R64 实施与实跑（P3 九条，2026-11-04）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| P3-2 json 模式不带正文 | content 为 None | None | PASS |
| P3-2 非 json 模式仍有正文 | stdout 非空 | # spec 索引

> | PASS |
| P3-6 非法 generation 报可解释错误 | WF_HISTORY_UNRESOLVED | WF_HISTORY_UNRESOLVED | PASS |
| P3-8 未知 step 留痕 | 有 __unknown_steps__ 条目 | True | PASS |
| P3-1 源树无 __pycache__ | 空 | [] | PASS |
| P3-3 同步与释放 bump 包络 | 源码含 revision bump | True | PASS |

实施见复核文 §3。新增 `scripts/tests/wf_runtime/test_rules_digest_parity.py`（2 条）。

## 51. 回归（R63 + R64）

| 项 | 结果 |
|---|---|
| 全部 31 套（CP1–CP5、R1–R64） | 全通过 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 9/9 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `unittest` scripts/tests、wf_runtime | OK（10 条，新增 2 条） |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

期间新发现：无（P3 均为既有实现细节，改后无回归）。

## 52. R65 实施与实跑（2026-11-04）

复核文见 `review-round27-reconciliation.md`。

### 52.1 用例（6/6）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R3 review-passed 适用条件为 complex | complex | complex | PASS |
| R3 轻量任务缺证据的降级仍被归档门禁挡住 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R4 前轮 fail 不被后轮 pass 覆盖 | 含 review_fail | ['review_fail'] | PASS |
| R5 execution 未引入未登记字段 | 无 spec_changes | [] | PASS |
| R6 只有人判记录不算调查成果 | WF_CHECK_FAILED | False WF_CHECK_FAILED | PASS |
| R6 有复盘即满足 | 满足 | True | PASS |

### 52.2 套件同步（R1/R2）

| 项 | 事实 | 处置 |
|---|---|---|
| 树内旧版 | `cp1_tests`、`cp2_tests`、`cp4_tests`、`cp5_b345`、`r17r24_tests`、`r31r34_tests`、`r38r39_tests`、`r57_tests` 与实跑版本不一致；`r46_tests.py` 缺失 | 全部同步 `scripts/tests/wf_runtime/full/`，补回 `r46_tests.py` |
| 复核方式 | 同一夹具先 CP2 后 CP1 | CP2 15/15 → CP1 20/20（与记录一致） |
| 防复发 | 每轮结束做全量 `diff /tmp/<suite> 树内` | 本轮为零差异 |

### 52.3 实施（R3–R6）

| 项 | 实施 | 证据 |
|---|---|---|
| **R3** | `review-passed` 恢复 `complex`；降级齐全性移入 `final_gate` | 轻量任务归档仍被 `WF_SEMANTIC_DECISION` 挡住 |
| **R4** | `outcome` 单调保留 `fail` | 同尝试 round1 fail + round2 pass 仍重建 `review_fail` |
| **R5** | 删除 `execution.spec_changes` | `execution` 字段集合与机制稿 §1.3 一致 |
| **R6** | 调查成果收紧为复盘 / 策展 / Check 通过 | 仅人判记录不再满足 |

### 52.4 回归

| 项 | 结果 |
|---|---|
| 全部 32 套（CP1–CP5、R1–R65） | 全通过 |
| 初始化 / 普通任务 / F2 | 8/8 / 8/8 / 9/9 |
| V1 / V2 / V3 / V5 | 11/11 / 2/2 / 8/8 / 12/12 |
| F1 spec 生命周期 / F0 | 13/13 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 52.5 期间新发现

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R40 | 登记与实际脱节 | 记录的全绿来自 `/tmp` 版本，树内是旧版 | 全量同步 + 每轮末 diff 核对 |
| N-R41 | `r62` 用例依赖旧判据 | R6 收紧后「仅人判即可满足」不再成立 | 用例改为断言不满足 + 补复盘满足的正例 |

### 52.6 收口状态

R1–R7 全部闭环。仍未运行项：D1（真实压缩/签发路径，按决定保持未运行）；E 的独立复审按决定暂不执行——本轮外部审查已作为一次独立复审记入 R7 的边界。

## 53. D1 实跑（2026-11-04）：宿主身份 / 压缩边界 / wf 签发路径

目标项目 `/tmp/wf-fixtures/d1`（真实 Git 仓库）用 `wf-dev-deploy.py --host-id dsh --verify-capability` 投放；
请求信封里的 `session_id` 取**运行时真实标识** `$DSH_SESSION_ID`（`session-826cbd83-…`，44 字符），不再用 `sess-*` 人造值。

### 53.1 用例（12/12）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D1-1 真实 session_id 可绑定 | WF_OK | WF_OK | PASS |
| D1-2 同身份重入保持绑定 | object.id 等于任务 | 2026-022194d9e7314c93baa2bc6490b9a52f | PASS |
| D1-3 压缩未携带 activation → 需重新 start | WF_NOT_ENABLED 或 WF_OK(只读) | WF_OK | PASS |
| D1-3b 无 activation 推进业务被拒 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| D1-4 重新 enable（= /wf-start）恢复原对象 | WF_OK 或已绑定提示 | WF_OK | PASS |
| D1-4b 仍是同一对象、未改绑 | object.id 不变 | 2026-022194d9e7314c93baa2bc6490b9a52f | PASS |
| D1-5 新会话看不到原绑定 | binding 缺失或对象不同 | None | PASS |
| D1-5b 新会话直接推进被拒 | 非 WF_OK | WF_BINDING_MISMATCH | PASS |
| D1-6 wf 身份在 host profile 下推进业务被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| D1-6b 只读诊断不因 provider 不匹配而停 | WF_OK | WF_OK | PASS |
| D1-7 wf 身份的 issued_id 校验通过 | 接受 32 位 uuid4 hex | True | PASS |
| D1-7b 非法 issued_id 被拒 | 拒绝 | True | PASS |

### 53.2 覆盖到的契约点

| 契约 | 证据 |
|---|---|
| 真实宿主身份首次绑定（机制稿 §1.4） | `task-new` 用真实 `session_id` 成功建立绑定 |
| 同身份重入保持绑定 | `status` 回读 `binding.object.id` 与任务一致 |
| **压缩未携带 activation**（机制稿 §1.4 末段） | 无 activation 时只读诊断放行，`task-start` 被 `WF_NOT_ENABLED` 拒 |
| 重新 start 只恢复原对象、不产生改绑许可 | `enable` 后仍是同一 `object.id` |
| 新会话区别 | 换 `session_id` 后看不到原绑定；直接推进被 `WF_BINDING_MISMATCH` 拒 |
| wf 身份不得绕过既有 profile | host profile 下用 `provider=wf` 推进业务被 `WF_IDENTITY_UNRESOLVED`；只读 `status` 不受影响 |
| wf 身份的字段核验 | 32 位 uuid4 hex 通过，非法值被拒 |

### 53.3 仍未覆盖（如实登记）

| 项 | 原因 | 出口 |
|---|---|---|
| 宿主是否在**真实压缩**后保持同一 `session_id` | 压缩由宿主触发，不可按需制造；本会话虽发生过一次上下文压缩，但压缩前没有留下同标识的绑定记录，无法回溯证明增量事实 | 需在宿主暴露压缩事件（或另一次压缩前后各取一次绑定读回）后补跑 |
| wf 签发路径的**端到端**绑定 | `session_profile.provider` 当前为 `host`，切换 provider 属「人在安装/维护预览里选 wf 路径」的动作，不是脚本能自行改的 | 人确认后把 profile 置 `provider=wf`（并核实携带方式），再跑同一套用例；本轮已证明切换前后的拒绝面正确 |

### 53.4 附带发现

- `capability.status=verified` 的 `evidence_refs` 目前只有 `declared_by: installer preview`，**没有压缩/重入/新会话的实际观察依据**，与机制稿 §1.4「evidence_refs 指向实际观察依据」不符。本轮 §53.2 的重入与新会话观察可直接补作证据；压缩一条仍缺，故按机制稿口径这份 `verified` 属**声明式**，不应据此宣称压缩稳定性已核实。

## 54. D1 收尾：B（证据补齐）+ C（wf 签发路径端到端，2026-11-04）

### 54.1 B：能力证据按实际观察补齐

`wf-dev-deploy.py` 与 `install.py` 的预览新增三个输入：`--provider host|wf`、`--verified-version`、`--capability-evidence kind=<种类>;ref=<观察>;by=<声明人>`（可重复）。
按机制稿 §1.4「声明由安装/维护预览的人确认后写入」，证据只能经这条路径进入，不手改运行时记录。

`/tmp/wf-fixtures/d1host` 的 `session_profile.capability.evidence_refs` 现为：

| 项 | 内容 |
|---|---|
| 声明 | `declared_by=installer preview` |
| 重入 | `kind=reentry`：同 `session_id` 连续两次 `status` 绑定一致 |
| 新会话 | `kind=new-session`：换 `session_id` 后绑定不可见、推进被 `WF_BINDING_MISMATCH` 拒 |

按 B 的口径：`status` 维持 `verified`，但**压缩一条仍未核实**，报告须写「声明式 verified，压缩未核实」，不得说成压缩稳定性已证明。

### 54.2 C：wf 签发路径端到端（8/8）

`/tmp/wf-fixtures/d1` 以 `--provider wf --host-id dsh --verify-capability` 投放。

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| C-1 wf 签发身份首次绑定 | WF_OK | WF_OK | PASS |
| C-2 同 issued_id 重入保持绑定 | object.id 一致 | 2026-3a20557d84004ae8ab334f28ed4863db | PASS |
| C-3 压缩未携带 activation → 业务动作被拒 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| C-4 重新 enable 恢复原对象 | WF_OK | WF_OK | PASS |
| C-4b 未产生改绑 | object.id 不变 | 2026-3a20557d84004ae8ab334f28ed4863db | PASS |
| C-5 复制到新会话不可见原绑定 | 无绑定 | {} | PASS |
| C-5b 新会话推进被拒 | 非 WF_OK | WF_BINDING_MISMATCH | PASS |
| C-6 丢失 issued_id → 身份未决 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |

### 54.3 累计覆盖

| 路径 | 用例 | 结果 |
|---|---|---|
| host 身份（`$DSH_SESSION_ID` 真实值） | §53 的 12 条 | 12/12 |
| wf 签发身份 | 本节 8 条 | 8/8 |

两条路径都实测了同一组边界：首次绑定、同标识重入、压缩未携带 activation、重新 start 不改绑、新会话看不到原绑定且推进被拒、身份丢失/不匹配走 `WF_IDENTITY_UNRESOLVED`。

### 54.4 仍未覆盖（一条）

真实压缩事件本身。处置见 `d1-compaction-checkpoint.md`：压缩摘要无法注入，改为在磁盘留检查点（压缩前快照 + 压缩后核对步骤 + 判定口径），一旦发生压缩即可补证；`capability` 的口径按 §54.1 标注。

## 55. R66 实施与实跑（2026-11-04）

复核文见 `review-round29-reconciliation.md`。

### 55.1 用例（12/12）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 实例标识被篡改 → 拒绝 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 1b 正常携带实例标识 → 通过 | WF_OK | WF_OK | PASS |
| 1c 实例标识缺失 → 需人裁决 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| 2 未知 writer schema 被拒 | WF_RECORD_INVALID | WF_RECORD_INVALID | PASS |
| 2b 顶层与 holder 代次矛盾被拒 | WF_RECORD_INVALID | WF_RECORD_INVALID | PASS |
| 3 正常任务暂停通过（准备） | WF_OK 或已暂停 | WF_OK | PASS |
| 3b 已归档任务拒绝暂停 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 3c 已归档任务拒绝恢复 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 4 清单缺声明 → 拒绝计算义务 | WF_ASSET_DECISION | WF_ASSET_DECISION | PASS |
| 4b 正常时义务由清单给出 | 含 task.plan-approved | True | PASS |
| 5 重复记录被拒并给诊断 | RecordInvalid | RecordInvalid | PASS |
| 5b 去重后可正常定位 | 返回路径 | True | PASS |

### 55.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 实例标识 | `_require_binding` 增 `_require_instance_match`；`wfdrive` 扮演适配层从绑定携带 | 篡改→`WF_BINDING_MISMATCH`、缺失→`WF_IDENTITY_UNRESOLVED`、正常→通过 |
| **2** 写者结构 | `writer.require_supported()`：schema=1、状态枚举、idle/holder 组合、顶层与 holder 代次一致 | schema 999 → `WF_RECORD_INVALID`；代次矛盾 → `WF_RECORD_INVALID` |
| **3** 终态 | pause/resume 拒绝 archived/terminal | 两条均 `WF_BINDING_MISMATCH` |
| **4** 义务来源 | `declared_step_specs()` 读已校验清单，缺失/未知/矛盾 → `WF_ASSET_DECISION` | 删掉清单里一条声明即被拒；正常时义务来自清单 |
| **5** 重复记录 | `locate_task_dirs()` + `task_dir()` 拒绝重复、`load_task()` 核记录 id | 复制目录即抛 `RecordInvalid` 并列出双方；去重后可定位 |

### 55.3 复现性（N1）

新增 `scripts/tests/wf_runtime/full/run_all.sh`（每套件前重建夹具）。实测 32 套 + 3 专项全绿、失败 0；不再需要任何跑序或中间清理动作。

### 55.4 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（32 套） | 全通过，失败 0 |
| 专项 p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 | 11/11 / 9/9 |
| F0 | 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 55.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R42 | 测试驱动器不携带 `instance_id` | 收紧后所有后续请求被 `WF_IDENTITY_UNRESOLVED` 挡住——此前「未携带也放行」正是缺陷本身 | `wfdrive` 从持久绑定取值携带，等价于真实适配层 |
| N-R43 | r64 的未知步骤用例依赖注入 `TASK_STEP_SPECS` | 义务来源改为清单后注入不再生效 | 改为让 `compute_P` 抛 `KeyError` 验证不静默跳过 |
| N-R44 | cp5 B3 手写信封不带实例标识 | 归档在崩溃点之前就失败 | 信封携带绑定中的 `instance_id` |

### 55.6 收口状态

第二十九轮 5 条 + N1/N2 闭环；R66 落地。D1 维持「两路径已实跑、压缩待触发」。

## 56. R67 实施与实跑（2026-11-04）

复核文见 `review-round30-reconciliation.md`。

### 56.1 用例（15/15）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 writer acquire 拒绝错误实例标识 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 1b 正常获取成功或已由本会话持有 | WF_OK 或已持有时 WF_WRITER_BUSY | WF_WRITER_BUSY held_by_self=True | PASS |
| 1c 能力未核实 → 日常入口拒绝 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| 2 正常执行态可写 | WF_OK | WF_OK | PASS |
| 2 paused 时拒绝基线写入 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 2 suspended 时拒绝基线写入 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 2b 无批准引用的提案被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 2c 前像不符被拒 | WF_WORKSPACE_UNRESOLVED | WF_WORKSPACE_UNRESOLVED | PASS |
| 2d 已归档对象拒绝基线写入 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 3 scope 改动不得移出门禁 | WF_ASSET_DECISION | WF_ASSET_DECISION | PASS |
| 3b 缺 mode 被拒 | WF_ASSET_DECISION | WF_ASSET_DECISION | PASS |
| 3c 重复声明被拒 | WF_ASSET_DECISION | WF_ASSET_DECISION | PASS |
| 3d 恢复后可用 | 有义务 | True | PASS |
| 4 有失败时脚本非零退出 | exit≠0 且汇总报失败 | exit=1 | PASS |
| 4b 无失败时零退出 | exit=0 | exit=0 | PASS |

### 56.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 写权入口 | `_require_instance_match` 上移 `cli`，acquire 锁前、release 核验后调用；内加 `capability.status != verified` → `WF_IDENTITY_UNRESOLVED` | acquire 带错实例 → `WF_BINDING_MISMATCH`；能力置 unknown → 日常入口 `WF_IDENTITY_UNRESOLVED` |
| **2** baseline-apply | archived/terminal → `WF_BINDING_MISMATCH`；paused/suspended → `WF_SEMANTIC_DECISION`；提案须带批准引用；`before` 指纹核对 | 四类状态各自命中；无批准引用被拒；前像不符 `WF_WORKSPACE_UNRESOLVED` |
| **3** 清单声明 | 先完整校验（非对象/缺 id/未知/重复/缺 mode·due），再判 scope 与处理器矛盾 | 改 scope、删 mode、重复 id 三种都被 `WF_ASSET_DECISION` 拒；恢复后可用 |
| **4** 聚合脚本 | 校验夹具、初始化退出码、套件退出码、`[FAIL]` 数、汇总 0 通过；末尾按失败数 `exit 1` | 假套件失败 → `exit=1` 且报"失败 1 项"；改回通过 → `exit=0` |

### 56.3 回归（新脚本，37 项）

| 项 | 结果 |
|---|---|
| `run_all.sh` 37 项 | 失败 0，脚本 `exit 0` |
| 专项 p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 56.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R45 | 旧聚合脚本掩盖真失败 | 换用严格脚本后立刻暴露 4 套失败（r1r2 9/14、r7r15 32/37、r31r34 12/13、r50 3/7）+ F0 基线步骤 | 全部由本轮收紧引起，且都是用例输入缺新要求：基线提案补批准引用、`FakeCtx` 补 `session/profile`、B3 信封带实例标识、r64 改用 `compute_P` 注入、F0 提案补批准 |

### 56.5 未处理（按评审建议不越过本轮范围）

审查判定的四类可放行、`repair` 预览后清空新写者、`repair`/`uninstall` 接管已有空锁——三项登记待专项处理，本轮未动。

## 57. R68 实施与实跑（2026-11-04）

复核文见 `review-round31-reconciliation.md`。

### 57.1 用例（9/9）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 正常审查可 pass | WF_OK | WF_OK | PASS |
| 2 导入后锚点失效 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3 带阻塞发现 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 4 未声明的审查 CLI → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 5 缺读取范围声明 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 6 预览给出令牌 | 有令牌 | True | PASS |
| 6b 预览后写者变化 → 令牌失效 | WF_PREVIEW_STALE | rc=1 out=令牌不匹配或预览已失效（需在同一进程重新预览） | PASS |
| 6c 未变化时同一令牌可应用 | WF_OK | rc=0 | PASS |
| 7 空锁文件不被 repair 认领 | 非 WF_OK 且报锁问题 | rc=1 tail=令牌不匹配或预览已失效（需在同一进程重新预览） | PASS |

### 57.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 审查判定输入 | `review.decide` 核锚点一致性、阻塞发现、声明来源、材料声明，命中即 `WF_REVIEW_INVALID` | 导入后重跑 Check → 拒绝；带 blocker → 拒绝；未声明 CLI → 拒绝；空 `read-scope` → 拒绝；两份合格报告 → 通过 |
| **2** 令牌派生 | `PreviewToken.derive()`；预览打印派生令牌，应用只认 `confirm_derived()` | 预览后改写者代次 → `WF_PREVIEW_STALE`；未变化 → 可应用 |
| **3** 独立入口锁 | 排他创建才写标记；已有文件标记不全即拒 | 空锁文件下 `repair --apply` 被拒 |

### 57.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（38 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 57.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R46 | 应用路径把人为指定的 nonce 当令牌 | `issue(nonce=…)` 覆盖派生值，使漂移检测失效 | 应用改用 `confirm_derived()`，`issue(nonce=…)` 只服务一致性比对 |

### 57.5 收口状态

第三十一轮 3 条闭环；R68 落地。R1–R68 全部闭环。仍未运行项：D1 的真实压缩事件（检查点已就位）。

## 58. R68b 修订实跑（2026-11-04）

复核文见 `review-round32-reconciliation.md`。

### 58.1 用例（16/16）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 正常审查可 pass | WF_OK | WF_OK | PASS |
| 2 导入后锚点失效 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3 带阻塞发现 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 4 未声明的审查 CLI → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 5 缺读取范围声明 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 6 审查轴 fail → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 7 声明未覆盖例外 → 判定拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 8 预览后无变化时可应用 | WF_OK | rc=0 token=yes | PASS |
| 8b 等待窗口内写者变化 → 预览失效 | WF_PREVIEW_STALE | rc=1 tail=事实: {"current_digest": "sha256:5129a1f45ee3bfe23 | PASS |
| 9 空锁文件不被 repair 认领 | 报锁问题 | rc=1 tail=事实: {"lock": "/tmp/wf-fixtures/rerun/.wf-lock",  | PASS |
| 10 拒绝决定不得执行基线写入 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 10b 批准未绑定本提案 → 拒绝 | WF_APPROVAL_MISSING | WF_APPROVAL_MISSING | PASS |
| 10c 缺前像指纹 → 拒绝 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 10d 绑定批准 + 前像齐全 → 通过 | WF_OK | WF_OK | PASS |
| 11 部分写入失败给结构化退出 | WF_PERSISTENCE_FAILED | WF_PERSISTENCE_FAILED | PASS |
| 11b 同提案重入续做（已写文件不挡） | WF_OK 且 skipped 含已写文件 | WF_OK skipped=['.wf/spec/rules/r68c.md'] | PASS |

### 58.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 批准语义 | `choice ∈ APPROVE_CHOICES`；`object_digest` 必须等于本次提案摘要；`before` 必填 | `reject` → `WF_SEMANTIC_DECISION`；无关批准 → `WF_APPROVAL_MISSING`；缺前像 → `WF_SEMANTIC_DECISION`；齐全 → `WF_OK` |
| **2** 续做分类 | 先识别未完成动作，再分「已应用/待写/外来变化」 | 部分失败后同提案重入 → `WF_OK` 且 `skipped` 只含已写文件 |
| **3** 令牌与窗口 | 恢复随机 nonce；锁内重算预览比摘要 | 等待窗口内改代次 → `WF_PREVIEW_STALE`；无变化 → `WF_OK` |
| **4** 审查判定 | 补 `scope-exceptions`、逐轴结论、材料缺口 | 轴 fail / 未覆盖例外 → `WF_REVIEW_INVALID` |
| **5** 锁验证口径 | 用例改为先过令牌再进锁 | 空锁文件 → 锁分支拒绝并给锁事实 |

### 58.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（38 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 58.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R47 | 确定性令牌与 §10.3 冲突且挡不住锁内竞态 | 摘要派生让"重新预览"不再失效，且应用只比摘要不比锁内状态 | 恢复随机 nonce + 锁内重算预览 |
| N-R48 | R68 空锁用例未走到锁 | 断言只看"非零退出"，令牌不匹配即满足 | 改为先通过令牌再验锁，断言锁事实 |
| N-R49 | 用例输入跟不上收紧 | r1r2/r7r15/r50/F0 提案缺 `before`/绑定批准 | 输入补字段；写失败改用只读目录触发 |

### 58.5 收口状态

第三十二轮 4 条 + 口径纠正闭环；R68b 落地。

## 59. R69 实施与实跑（2026-11-04）

复核文见 `review-round33-reconciliation.md`。

### 59.1 用例（9/9）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 空对象前像被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| 1b exists=false 前像可用 | WF_OK | WF_OK | PASS |
| 2 整批冲突在写入前拦下 | WF_WORKSPACE_UNRESOLVED 且列冲突 | WF_WORKSPACE_UNRESOLVED conflicts=True | PASS |
| 2b 前一件未产生写入 | d.md 不存在 | False | PASS |
| 3 准备：审查 pass | WF_OK | WF_OK | PASS |
| 3b 同槽位不同摘要 → 导入冲突 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3c 旧 pass 引用的就是当前导入 → 门禁通过 | 满足 | True None | PASS |
| 3d 结论引用的报告已变 → 门禁不通过 | WF_REVIEW_INVALID | False WF_REVIEW_INVALID | PASS |
| 4 确认期间资产被改 → 预览失效且不删除 | WF_PREVIEW_STALE 且文件仍在 | rc=1 survived=True | PASS |

### 59.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 前像结构 | dict 必须含 `digest` 或 `exists:false` | `{}` → `WF_SEMANTIC_DECISION`；`exists:false` → 通过 |
| **1b** 整批预检 | 先分类全部条目，冲突即整体拒绝 | 两件提案中后件冲突 → `WF_WORKSPACE_UNRESOLVED` 且前件未写入 |
| **2** 导入冲突 | 同摘要幂等、不同摘要拒绝 | 重导入不同报告 → `WF_REVIEW_INVALID` |
| **2b** 门禁引用 | 核 `result.imported[]` 摘要与当前导入一致 | 引用不变 → 通过；摘要被改 → `WF_REVIEW_INVALID` |
| **3** 卸载内容重核 | 锁内比对待删资产内容与 `.gitignore` 全文 | 确认期间改动资产 → `WF_PREVIEW_STALE` 且文件仍在 |

### 59.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（39 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 59.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R50 | 轻量任务的审查门禁不涉及报告 | 首版 3c/3d 用 light 任务，`review-passed` 只核降级条目，报告引用无从验证 | 用例改用复杂任务，真正走到报告引用核验 |

### 59.5 收口状态

第三十三轮 3 条闭环；R69 落地。

## 60. R70 实施与实跑（2026-11-04）

复核文见 `review-round34-reconciliation.md`。

### 60.1 用例（5/5）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 干净资产可卸载 | WF_OK | rc=0 | PASS |
| 1b 既有偏离不被误判为预览失效 | 卸载成功且偏离文件保留 | rc=0 survived=True | PASS |
| 1c 确认期间改动 → 预览失效且保留 | WF_PREVIEW_STALE 且文件仍在 | rc=1 survived=True | PASS |
| 2 首轮真失败被记录 | result.verdict=fail 且 outcome=fail | code=WF_REVIEW_INVALID verdict=fail outcome=fail | PASS |
| 2b 次轮通过仍保留历史失败 | outcome=fail 且触发含 review_fail | verdict=pass outcome=fail triggers=['review_fail'] | PASS |

### 60.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 卸载两比较分开 | `preview_digests` 记预览时指纹；锁内用它判"是否变过"，发行摘要只用于删/留 | 干净→成功；既有偏离→成功且保留；确认期改动→`WF_PREVIEW_STALE` 且保留 |
| **2** 审查失败落盘 | 拆 `problems`（输入不合法）与 `failures`（判否）；后者写 `verdict=fail` 与 `outcome=fail` | 首轮阻塞发现 → `result.verdict=fail`、`outcome=fail`；次轮 pass 后 `outcome` 仍 `fail`、触发含 `review_fail` |

### 60.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（40 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 60.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R51 | 用例取暂存目录的方式不稳 | 用正则从 launch payload 抠路径，取不到就落到 `unknown/` | 改 glob 按 `task_id` 定位 |

### 60.5 收口状态

第三十四轮 2 条闭环；R70 落地。

## 61. R71 实施与实跑（2026-11-04）

复核文见 `review-round35-reconciliation.md`。

### 61.1 用例（10/10）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 交接发起拒绝错误实例标识 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 1b 交接未进入 recovering | held | held | PASS |
| 1c 正常交接发起 | WF_OK | WF_OK | PASS |
| 2 计划被替换 → 预览失效 | WF_PREVIEW_STALE | rc=1 | PASS |
| 2b 未按被替换的计划写回 | disposition 仍为空 | None | PASS |
| 3 五轴齐全且通过 → pass | WF_OK/pass | WF_OK/pass | PASS |
| 3b axes 为空被拒 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3c 只报一轴被拒 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3d 缺可测性轴被拒 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 3e 未知轴被拒 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |

### 61.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 交接实例核验 | `begin`/`accept` 接入 `_require_instance_match` | 错误实例 → `WF_BINDING_MISMATCH` 且写者仍 `held`；正常 → `WF_OK` |
| **2** dispose 锁内重核 | 锁内 `dispose_preview` 重算比摘要 | 计划被替换 → `WF_PREVIEW_STALE`，disposition 未写回 |
| **3** 审查五轴 | 固定五轴齐全、结论合法、拒绝未知轴 | 五轴通过→pass；空 axes／单轴／缺轴／未知轴→`WF_REVIEW_INVALID` |

### 61.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（41 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 61.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R52 | 用例混用内部两轴与外部五轴 | r68/r69/r70 的正例用 `standard/requirement` | 全部改为外部五轴，并按五轴补"缺轴"反例 |
| N-R53 | dispose 用例的回执挡住后续任务开工 | 残留 `maintenance_results` 使 `task-start` 报 `WF_WIP_UNRESOLVED` | 用例在进入审查段前清空该回执 |

### 61.5 收口状态

第三十五轮 3 条闭环；R71 落地。

## 62. R72 实施与实跑（2026-11-04）

复核文见 `review-round36-reconciliation.md`。

### 62.1 用例（5/5）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 正常项目可卸载 | WF_OK | rc=0 | PASS |
| 2 越界条目整批拒绝 | WF_ASSET_DECISION | rc=1 | PASS |
| 2b 目标外文件未被删 | 仍在 | True | PASS |
| 3 清单摘要不符即拒绝 | WF_ASSET_DECISION | rc=1 | PASS |
| 4 未知资产类别被拒 | WF_ASSET_DECISION | rc=1 | PASS |

### 62.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **清单一致性** | 比对 `installation.manifest_digest` 与清单实际摘要 | 清单被改动 → `WF_ASSET_DECISION` |
| **路径合法性** | 拒绝绝对路径、`..`/`.`/空段/反斜杠/盘符 | `../outside-user.txt` → 整批拒绝 |
| **真实落点** | `realpath` 必须仍在项目根 / skill 根内 | 越界条目不会进入删除 |
| **类别白名单** | 只认 `project_wf`/`skill_root`；`release_only` 显式跳过 | 未知类别被拒；正常项目仍可卸载 |

### 62.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（41 项，含 r72） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 62.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R54 | `release_only` 被误判为未知类别 | 发行清单每项都带该类资产（installer 自身），首版白名单只列两类 → 正常项目也被拒 | 显式跳过发行侧类别 |
| N-R55 | 聚合脚本直接 `bash` 执行 Python 脚本体 | `run_all.sh` 里 r72 用 `bash` 跑 → 语法错误 | 改用 `$PY` 执行 |
| N-R56 | r67 的假套件环境缺 r72 桩 | 清单变动后假环境少文件、并误用 bash | 补桩并按 `$PY` 运行 |

### 62.5 收口状态

第三十六轮 1 条闭环；R72 落地。

## 63. R73 实施与实跑（2026-11-04）

复核文见 `review-round37-reconciliation.md`。

### 63.1 用例（7/7）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 正常项目可卸载 | WF_OK | rc=0 | PASS |
| 2 越界条目整批拒绝 | WF_ASSET_DECISION | rc=1 | PASS |
| 2b 目标外文件未被删 | 仍在 | True | PASS |
| 3 清单摘要不符即拒绝 | WF_ASSET_DECISION | rc=1 | PASS |
| 4 未知资产类别被拒 | WF_ASSET_DECISION | rc=1 | PASS |
| 5 安装记录摘要missing → 拒绝且不删 | WF_ASSET_DECISION 且资产仍在 | rc=1 removed=False | PASS |
| 5 安装记录摘要empty → 拒绝且不删 | WF_ASSET_DECISION 且资产仍在 | rc=1 removed=False | PASS |

### 63.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **清单摘要必填** | `manifest_digest` 缺失或为空 → `WF_ASSET_DECISION`，不进删除 | 缺摘要、空摘要两种情况均拒绝且资产仍在 |

### 63.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（41 项，含 r72） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 63.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R57 | 用例与实现的日界时钟不同源 | `r56`/`r25r30` 用本地 `date.today()`，实现用 UTC；本地跨日后"两天前+周期1天"被判未到期 | 用例改用 `records.utc_now().date()`，与实现同源 |

### 63.5 收口状态

第三十七轮 1 条闭环；R73 落地。

## 64. R74 实施与实跑（2026-11-04）

复核文见 `review-round38-reconciliation.md`。

### 64.1 用例（9/9）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 基线/配置在允许集合 | 允许 | True | PASS |
| 1b spec 目录在允许集合 | 允许 | True | PASS |
| 1c 控制记录被拒 | 拒绝 | True | PASS |
| 1d spec-update 拒绝控制记录目标 | WF_SCOPE_UNRESOLVED | WF_SCOPE_UNRESOLVED | PASS |
| 2 bind 未启用被拒 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| 2 task-new 未启用被拒 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| 2c writer acquire 未启用被拒 | WF_NOT_ENABLED | WF_NOT_ENABLED | PASS |
| 3 枚举包含全部 Git 跟踪文件 | 无遗漏 | [] | PASS |
| 3b 枚举不含控制目录 | 无 .wf/ 前缀 | [] | PASS |

### 64.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 白名单统一 | `paths.write_target_allowed()` 单一实现，两入口共用 | 控制记录在两边都被拒（`spec-update` → `WF_SCOPE_UNRESOLVED`） |
| **3** activation 覆盖 start 路由 | `bind`/`task-new` 与 `writer acquire` 纳入核验 | 三者未启用均 `WF_NOT_ENABLED` |
| **5** 工作树枚举 | 优先 `git ls-files`，失败退回 `os.walk` | 枚举含全部 Git 跟踪文件且不含 `.wf/` |
| **2** 归档中断出口 | `wf-continue` 路由增两行 | 文档 |
| **6** D08/D32 | 按实际函数名改写，存活探测登记为缺口 | 文档 |

### 64.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（42 项，含 r74） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 64.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R58 | `/tmp` 被清后发行仓库不存在 | r69/r72/f0/d1 依赖 `/tmp/wf-fixtures/release-repo`，全量跑直接失败 | `run_all.sh` 增加 `prepare_release_repo()`：缺失时用 `build-wf-release.py` 重建并打 tag |
| N-R59 | 夹具技能副本过期导致投放中止 | skills 目录内容变化时 `wf-dev-deploy` 拒绝覆盖，`wf.py` 未投放 | 重建前删除该副本目录（测试侧操作） |
| N-R60 | r74 触碰面过宽触发维护回执重叠 | `.wf/**` 覆盖 `dev-deploy` 回执路径 → `task-start` 报 `WF_WIP_UNRESOLVED` | 收窄为 `.wf/spec/**`；白名单判定本在前，不影响该用例的判据 |

## 65. R75 实施与实跑（2026-11-04）

复核文见 `review-round39-reconciliation.md`。

### 65.1 用例（12/12）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 bind 缺实例标识被拒 | WF_IDENTITY_UNRESOLVED 或 WF_RECORD_INVALID | WF_IDENTITY_UNRESOLVED | PASS |
| 1b bind 实例不符被拒 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| 1c bind 正常携带可接续 | WF_OK | WF_OK | PASS |
| 2 声明三槽位只导入两份 → 拒绝 | WF_REVIEW_INVALID | WF_REVIEW_INVALID | PASS |
| 2b 三槽位齐全 → pass | WF_OK | WF_OK | PASS |
| 2c 报告文件被改写 → 门禁不通过 | WF_REVIEW_INVALID | False WF_REVIEW_INVALID | PASS |
| 3 巡检输出治理面 | 含 archive_terminals/spec_usage/inspection | ['archive_terminals', 'inspection', 'spec_usage'] | PASS |
| 3b 消费 inspection_every_tasks | every_tasks=10 | 10 | PASS |
| 3c 消费 spec_reclaim_tasks | reclaim_threshold=5 | 5 | PASS |
| 4 无持锁时不误报存活 | 存活判定有明确事实 | alive=False mark=False | PASS |
| 4b 持锁期间探测到存活进程 | alive=True 且 pid 匹配 | alive=True pid=450181 | PASS |
| 4c 探测不改动锁文件 | 标记仍在 | False | PASS |

### 65.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **P1-1** D23/D24 | `inspect` 增治理面（归档终态、spec 回收候选、周期触发），消费两个配置键 | 治理面三项齐全；`every_tasks=10`、`reclaim_threshold=5` |
| **P1-2** 锁存活探测 | 标记后记 `holder pid/start`；`verify_holder`/`proc_start` 只读探测；获取刷新、释放清除 | 持锁期间 `alive=True` 且 pid 匹配；释放后不误报 |
| **P1-3** bind 实例 | 已有绑定走同一 `_require_instance_match` | 缺失 → `WF_IDENTITY_UNRESOLVED`；不符 → `WF_BINDING_MISMATCH` |
| **P1-4** 报告重哈希 | 门禁三重核对（结论/记录/文件实际摘要） | 改写报告文件 → `WF_REVIEW_INVALID` |
| **P1-5** 槽位完整性 | 声明 ≥2 槽位且每槽位都要有报告 | 三槽位只导入两份 → 拒绝；补齐 → pass |
| **P1-6** 日期 | 未来日期全部改为实际日期 | `validation.md` 仅剩 11-03/11-04 |
| **P2** | `wf-start` 写清 activation/instance 重放；`review-launch` 核三类材料；旧登记按代码改写；清 `__pycache__` | 文档 + `launch` 校验 |
| **残留** | `verify_anchor` → 实际函数名；frontmatter/§7.3 同步 | 文档 |

### 65.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（43 项，含 r75） | 失败 0，`exit 0`（含从零重建发行仓库） |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` scripts/tests、wf_runtime | OK（30 条 / 11 条，新增锁探测两条） |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 65.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R61 | 锁标记追加持锁者行后，独立入口判"标记完全相等" | `repair`/`uninstall` 把正常锁判成未知标记，r68/r71 失败 | 两处改为前缀判定，与运行时一致 |
| N-R62 | 既存锁文件不刷新持锁者事实 | 复用旧标记会让探测看到上一任 pid | 获取时一律刷新、释放时清除 |
| N-R63 | 验证记录写入未来日期 | §53–§64 出现 2026-11-05…11-13，本次会话实为 11-04 | 全部改为实际日期并复核 |

### 65.5 口径

按评审结论，当前称**首轮实现候选**；独立复审（E）未执行，由人决定。

## 66. R76 实施与实跑（2026-11-04）

复核文见 `review-round40-reconciliation.md`。

### 66.1 用例（11/11）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 1 长期被引用的 spec 不作候选 | 不含 used.md | ['.wf/spec/index.md', '.wf/spec/pre-dev-checklist.md | PASS |
| 1b 近期未被引用的 spec 成为候选 | 含 idle.md | True | PASS |
| 1c 异常归档不计入窗口样本 | 窗口不含异常归档 | ['2026-00000000000000000000000000000002', '2026-0000 | PASS |
| 1d 窗口样本按归档时间取最近 N 个 | 样本数=5 | 5 | PASS |
| 1e 活动任务引用则不作候选 | 不含 idle.md | False | PASS |
| 1f 窗口内样本不足不静默当零 | unknown 非空或样本足够 | [] | PASS |
| 2 周期触发按正常归档计数 | normal_archived=7、abnormal=1 | 7/1 | PASS |
| 2b 异常归档不计入触发基数 | due=False（7%5≠0） | False | PASS |
| 2c 达到整数倍即触发 | normal=10 due=True | 10 due=True | PASS |
| 3 锁被活进程持有时 repair 拒绝 | 非成功且指出锁/写权 | rc=1 blocked=True | PASS |
| 3b 探测与运行时同一事实源 | 返回 (bool, dict) | False ['pid', 'reason', 'start'] | PASS |

### 66.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 回收候选语义 | 改为「最近连续 N 个正常归档样本全未引用 + 无活动任务引用」，异常归档不作样本，样本不足/缺清单报 `unknown` | 长期引用的 spec 不入候选；未被引用者入选；异常归档不入窗口 |
| **2** 周期触发基数 | 只数正常归档（按 `archived_at,id`），异常不计不重置 | 7 正常 + 1 异常 → `due=False`；补到 10 → `due=True` |
| **3** 存活探测闭环 | `repair`/`uninstall` 锁内探测，持有者仍存活即 `WF_WRITER_BUSY` | 子进程持锁时 `repair --apply` 被拒 |
| **4** 文档同步 | 40 轮 / §21–§66 / 44 项；新增「巡检治理面」段 | 文档 |

### 66.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（44 项，含 r76） | 失败 0，`exit 0`（含从零重建发行仓库） |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` scripts/tests、wf_runtime | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 66.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R64 | 治理面把夹具自带的初始化归档算漏 | 用例按 6 个样本断言，实际正常归档 7 个 | 用例按真实计数断言，并补"达整数倍即触发"正例 |

### 66.5 口径与状态

首轮实现候选；独立复审（E）仍未执行，由人决定是否安排未参与修订的会话。R1–R76 闭环。

## 67. R77 实施与实跑（2026-11-04）

复核文见 `review-round41-reconciliation.md`。

### 67.1 用例（8/8）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 0 基线：样本完整才给候选 | statistic_complete=True 且候选非空 | complete=True candidates=3 | PASS |
| 1 样本不足不给候选 | 候选为空且 unknown 含样本不足 | candidates=0 unknown=1 | PASS |
| 2 样本缺清单不给候选 | 候选为空且 unknown 指出缺清单 | candidates=0 | PASS |
| 3 畸形策展条目不致异常 | 正常返回并报 unknown | candidates=0 | PASS |
| 4 改名/合并无法映射报 unknown | unknown 指明路径已不存在 | ['curation path no longer exists; rename/m'] | PASS |
| 5 非法配置不给候选 | 候选为空且 unknown 指出配置非法 | candidates=0 unknown=2 | PASS |
| 5b 非法配置不给触发结论 | due=None | None | PASS |
| 6 inspect 输出治理面事实 | 含 spec_usage.unknown | ['problem', 'reclaim_candidates', 'reclaim_threshold | PASS |

### 67.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **1** 未知压制候选 | 任一 unknown → 候选为空、`statistic_complete=false` | 样本不足/缺清单 → `candidates=0` |
| **2** 非法配置阻断 | 非法 `spec_reclaim_tasks` 不产候选；非法 `inspection_every_tasks` → `due=null` | 两键置非法后候选 0、`due=None` |
| **3** 改名/合并映射 | 样本引用过但当前不存在的路径 → unknown | `unknown` 含 `no longer exists` |
| **4** 畸形条目 | 先判类型再取字段，非对象记 unknown 不抛异常 | 字符串条目下巡检正常返回 |
| **5** 文档 | §2.3.11 改为「已知边界与实现说明」，新增「巡检治理面的未知纪律」 | 文档 |

### 67.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（45 项，含 r77） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 67.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 四条缺口同源，一次重写覆盖 | — |

### 67.5 口径与状态

首轮实现候选；独立复审（E）未执行。R1–R77 闭环。

## 68. R77b 实施与实跑（2026-11-04）

复核文见 `review-round42-reconciliation.md`。

### 68.1 用例（13/13）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 0 基线：样本完整才给候选 | statistic_complete=True 且候选非空 | complete=True candidates=3 | PASS |
| 1 样本不足不给候选 | 候选为空且 unknown 含样本不足 | candidates=0 unknown=1 | PASS |
| 2 样本缺清单不给候选 | 候选为空且 unknown 指出缺清单 | candidates=0 | PASS |
| 3 畸形策展条目不致异常 | 正常返回并报 unknown | candidates=0 | PASS |
| 4 改名/合并无法映射报 unknown | unknown 指明路径已不存在 | ['curation path no longer exists; rename/m'] | PASS |
| 5 非法配置不给候选 | 候选为空且 unknown 指出配置非法 | candidates=0 unknown=2 | PASS |
| 5b 非法配置不给触发结论 | due=None | None | PASS |
| 6 inspect 输出治理面事实 | 含 spec_usage.unknown | ['problem', 'reclaim_candidates', 'reclaim_thresho | PASS |
| 7 无活动任务时样本完整可给候选 | statistic_complete=True | True | PASS |
| 7 缺 curation 字段 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 curation 非列表 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 条目非对象 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 活动任务引用已消失 spec → unknown | 无候选且含 no longer exists | candidates=0 | PASS |

### 68.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| 活动任务纳入未知 | 缺 `curation`/非列表/条目非对象/引用已消失路径，均记 unknown 并压制候选 | 四种情形候选均为 0 且带对应未知 |
| 消失路径判定扩面 | `referenced_recently ∪ active_refs` | 活动任务引用消失 spec → 无候选 |
| 正例保持 | 活动任务正常时仍计入 `active_refs` | 样本完整且无活动任务 → `statistic_complete=True`、给候选 |

### 68.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（45 项） | 失败 0，`exit 0` |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 68.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R65 | 改完代码未重建发行树 | `--verify` 报 `tasks.py` 与 `wf-release.json` 不一致 | 重跑 `build-wf-release.py --version 0.1.0` 后 `--verify` 通过（每次改运行时模块都必须重建，已按此执行） |

### 68.5 口径与状态

首轮实现候选；独立复审（E）未执行。

## 69. R78 实施与实跑（2026-11-04）

复核文见 `review-round43-reconciliation.md`。

### 69.1 用例（17/17，r77 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 0 基线：样本完整才给候选 | statistic_complete=True 且候选非空 | complete=True candidates=3 | PASS |
| 1 样本不足不给候选 | 候选为空且 unknown 含样本不足 | candidates=0 unknown=1 | PASS |
| 2 样本缺清单不给候选 | 候选为空且 unknown 指出缺清单 | candidates=0 | PASS |
| 3 畸形策展条目不致异常 | 正常返回并报 unknown | candidates=0 | PASS |
| 4 改名/合并无法映射报 unknown | unknown 指明路径已不存在 | ['curation path no longer exists; rename/m'] | PASS |
| 5 非法配置不给候选 | 候选为空且 unknown 指出配置非法 | candidates=0 unknown=2 | PASS |
| 5b 非法配置不给触发结论 | due=None | None | PASS |
| 6 inspect 输出治理面事实 | 含 spec_usage.unknown | ['problem', 'reclaim_candidates', 'reclaim_thres | PASS |
| 7 无活动任务时样本完整可给候选 | statistic_complete=True | True | PASS |
| 7 缺 curation 字段 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 curation 非列表 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 条目非对象 → unknown 压制候选 | 无候选且含对应未知 | candidates=0 hit=True | PASS |
| 7 活动任务引用已消失 spec → unknown | 无候选且含 no longer exists | candidates=0 | PASS |
| 8 完整归档记录可统计 | complete=True 且 due 有结论 | complete=True due=False | PASS |
| 8 缺 archived_at → unknown 压制 | 候选 0 且 due=None | candidates=0 due=None | PASS |
| 8 目录在归档区但 status 非 archived → unknown | 候选 0 且给状态未知 | candidates=0 | PASS |
| 8 terminal 非法 → unknown | 候选 0 且给 terminal 未知 | candidates=0 | PASS |

### 69.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| 归档事实完整性 | `status=archived` + `terminal∈{normal,abnormal}` + `archived_at` 可解析，缺一即 unknown | 缺 `archived_at`、状态不符、terminal 非法三种都压制候选 |
| 时间可排序 | 新增 `_parse_stamp()`，窗口按 `datetime` 排序 | 完整记录时 `statistic_complete=True` |
| 未知时不给触发 | `due` 在存在 unknown 时置 `null` | 记录不完整 → `due=None`；完整 → 有结论 |
| 文档同步 | 43 轮 / §65–§69；未知纪律补「归档记录不完整」与 `due=null` | 文档 |

### 69.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh`（45 项） | 失败 0，`exit 0`（含从零重建发行仓库） |
| p5_spec / p5_v2v3 / p5_v5 | 13 / 12 / 12 |
| V1 / F2 / F0 | 11/11 / 9/9 / 9/9 |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |

### 69.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| — | 无新增 | 改动集中在同一函数内，一次重写覆盖 | — |

### 69.5 口径与状态

首轮实现候选；独立复审（E）未执行。

## 70. E 独立复审的处置与实跑（2026-11-04）

复核文见 `review-round44-reconciliation.md`。复审主体：`codex exec`（未参与修订的异构 CLI，只读）。

### 70.1 用例（18/18，r79 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D01 内容类锚点不额外包一层 | sha256:52eb5955f79a4242aca7aaa0c05a67513 | sha256:52eb5955f79a4242aca7aaa0c05a675133584a0 | PASS |
| D01b 与旧形状不同 | different | False | PASS |
| D01c 规则类仍含 rule_version | sha256:01b66939e19d12a5a4b3b490df53b3f73 | sha256:01b66939e19d12a5a4b3b490df53b3f7324544b | PASS |
| D02 结构齐全时无问题 | [] | [] | PASS |
| D02 缺 rule_version → 阻断 | 问题非空 | ['anchor.rule_version'] | PASS |
| D02 缺 commands → 阻断 | 问题非空 | ['commands'] | PASS |
| D02 命令未通过 → 阻断 | 问题非空 | ['commands'] | PASS |
| D02 缺验收结果 → 阻断 | 问题非空 | ['acceptance_results'] | PASS |
| D02 内部双轴缺一 → 阻断 | 问题非空 | ['internal_review.requirement'] | PASS |
| D02 声明验证未执行 → 阻断 | commands | ['commands'] | PASS |
| D03 无探测时不得结案 | pending_check | pending_check | PASS |
| D03 事实不成立不得结案 | pending_check | pending_check | PASS |
| D03 事实成立才结案 | disposed | disposed | PASS |
| D03 承接任务不存在 → 不结案 | False | False | PASS |
| D04 第 1 倍不被第 10 倍覆盖 | 1 在待裁定列表 | [1, 2, 3] | PASS |
| D04b 已裁定的第 10 倍不重复 | 10 不在待裁定列表 | False | PASS |
| D07 标准 Bearer 被遮罩 | 不含明文 | Authorization: *** | PASS |
| D07b 分离参数被遮罩 | 不含明文 | ['/usr/bin/python3', 'tool', '--token', '***', | PASS |

### 70.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **D01** | 内容类锚点多包一层 `{"P": …}` | 改为 `H(domain, C(P))` | 与机制稿公式逐字节相等；与旧形状不同 |
| **D02** | Check 门禁只核 pass + 锚点 | 新增 `gates.check_result_problems()`：result、`anchor.rule_version`、命令覆盖与状态、验收结果、内部双轴 | 五种缺项各自阻断；齐全时无问题 |
| **D03** | 维护回执「字段齐就结案」 | `receipt_state` 增 `disposition_probe`；`disposed` 需事实可核；新增 `tasks.maintenance_disposition_probe()`（提交可达/反向到位/承接已批准且覆盖路径） | 无探测、事实不成立均 `pending_check`；承接任务不存在不结案 |
| **D04** | 裁定前缀误配（第 1 倍被第 10 倍覆盖） | `parse_debug_ruling()` 精确解析，`rulings` 键改 `(verification_id, multiple)`；写入口校验结构 | 累计 30/阈值 3 时待裁定含 1、不含 10 |
| **D05** | 覆盖声明超出实际执行 | `run_all.sh` 默认从源码重建发行仓库并把 `f0` 接入入口 | 实际执行 **47 项**（43 套件 + r72 + f0 + 3 专项），`exit 0` |
| **D06** | §6.2/G11/G22 落点函数不存在 | 按真实定义改写 8 组符号，并加 AST 校验 | 全稿 `wflib/<mod>.py::sym` 核对 **missing: none** |
| **D07** | Bearer 与分离参数未脱敏 | 补 `Authorization: Bearer <值>` 与 `--token <值>`；新增 `redact_argv()` | 虚构哨兵值在日志/facts/命令记录里均被遮罩 |
| **D08** | 无消费者的 `_decision_index` | 删除 | 全仓检索 0 命中 |

### 70.3 未覆盖轴（如实登记，不追认）

1. 上位文件历次语义修改的**授权批准链**——本轮只能证明摘要匹配与相对 HEAD 无差异。
2. **历史实跑声明的原始记录**（强杀恢复、宿主身份、异种 reviewer）——不以本轮回归通过追认。

### 70.4 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | 47 项，失败 0，`exit 0`；`f0 rc=0 PASS=9` |
| `unittest` scripts/tests、wf_runtime | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 70.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R66 | 删除死函数时连带删掉 `SECRET_PATTERNS` | `task-check` 抛内部错误 exit 70 | 恢复常量并复验脱敏；按 AST 边界删函数 |
| N-R67 | 处置事实核验过严 | dev-deploy 回执含 `.gitignore`，证据提交只覆盖安装组 → V3 误判 | 允许「提交内匹配 或 当前态匹配且无未提交差异」 |
| N-R68 | r67 假环境未跟上新入口 | 缺 `p5_f0.py` 与发行仓库桩 | 补桩 |
| N-R69 | r79 的裁定用例外形不符 | `check_history` 缺 `result=fail`，基数算成 0 | 补字段后 18/18 |

### 70.6 状态

实现稿 frontmatter 改为「**按已覆盖轴定稿**」，并列出未覆盖轴；R1–R79 闭环。

## 71. D1「真实压缩事件」实跑（2026-11-04）

复核记录见 `d1-compaction-checkpoint.md`。

### 71.1 本次观察到的事实

| 项 | 值 |
|---|---|
| 快照写入（2026-11-03T12:58:34Z） | `$DSH_SESSION_ID = session-826cbd83-3b6e-4185-830e-2d87287e7c77` |
| 压缩后读取（2026-11-04，本会话已发生两次真实压缩） | `$DSH_SESSION_ID = session-826cbd83-3b6e-4185-830e-2d87287e7c77` |
| 判定 | **同一标识**：运行时没有因压缩换身份 |
| 绑定键复核 | 用当前标识重算 `session.session_key()` → `7eeebb62…ddf7`，与磁盘绑定文件名逐字符一致 |

绑定键只由「身份来源 + 标识」派生，不含任何随压缩失效的上下文令牌——这是「压缩不影响绑定可达性」的结构性依据；**观察性**依据仍需下一次压缩后的读回，快照已就位（见检查点 §1）。

### 71.2 两条路径重跑（夹具已移出 `/tmp`）

| 路径 | 夹具 | 结果 |
|---|---|---|
| host（真实 `$DSH_SESSION_ID`） | `~/.cache/wf-fixtures/d1host` | **12/12** |
| wf 签发（`issued_id`） | `~/.cache/wf-fixtures/d1wf` | **8/8** |

夹具重建脚本：`scripts/tests/wf_runtime/full/d1_rebuild.sh`（移出 `/tmp` 是因为上一次 `/tmp` 被清空把 d1 夹具丢了）。

### 71.3 能力依据的落账方式

`capability.evidence_refs` 通过部署预览写入（未手改运行时记录）：

```
--capability-evidence "kind=compaction;ref=2026-11-04 真实压缩后 $DSH_SESSION_ID 仍为 session-826cbd83;by=human"
```

`d1host/.wf/install/installation.json` 的 `session_profile.capability` 现为
`status=verified`、`verified_version=dsh-session-2026-11-04`、`evidence_refs` 含上述 `kind=compaction` 一条。

### 71.4 D1 矩阵现状

| 项 | 状态 |
|---|---|
| 宿主真实身份可绑定 | 已运行（12/12） |
| 压缩边界：activation 丢失 → 业务被拒、重新 enable 恢复原对象 | 已运行（D1-3/3b/4/4b） |
| 换会话不得接管 | 已运行（D1-5/5b） |
| wf 签发路径（携带/恢复/丢失/复制到新会话） | 已运行（8/8） |
| **真实压缩后标识不变** | **本次已运行** |
| **真实压缩后绑定仍可读** | 待下一次压缩，快照与判据已写入检查点 |

### 71.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R70 | D1 夹具在 `/tmp`，被系统清空后整套证据消失 | 上次重启后 `/tmp/wf-fixtures/d1*` 不存在 | 迁到 `~/.cache/wf-fixtures/` 并加 `d1_rebuild.sh` 重建脚本 |
| N-R71 | wf 签发路径夹具需 `--provider wf` 部署，与 host 夹具不能共用 | 同一夹具跑 wf 路径直接 `WF_IDENTITY_UNRESOLVED` | 分成 `d1host` / `d1wf` 两个夹具，分别部署 |
| N-R72 | 检查点里写了 `instance_id` 明文 | 它是定位会话的凭据，写进仓库等于共享值 | 改为「不记录，从上下文取；取不到按 `WF_IDENTITY_UNRESOLVED` 处理」 |

### 71.6 口径

D1 从「未运行」变为「**已运行（身份轴）；绑定轴待下一次压缩**」。不称「宿主身份稳定性已完全核实」——同一进程内的标识稳定性不覆盖进程重启与跨设备场景。

## 72. R80 实施与实跑（2026-11-04）

复核文见 `review-round45-reconciliation.md`。第二轮独立复审：`codex exec` 全新会话（未参与修订）。

### 72.1 用例（22/22，r80 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D02 齐全时通过 | [] | [] | PASS |
| D02 验收未通过被拒 | 非空 | ['acceptance_results[a1]'] | PASS |
| D02 调用被替换被拒 | invocation | ['commands[v1].invocation'] | PASS |
| D02 非零退出被拒 | exit_code | ['commands[v1].exit_code'] | PASS |
| D02 缺结束时间被拒 | ended_at | ['commands[v1].ended_at'] | PASS |
| D02 重复结果被拒 | duplicate | ['duplicate verification_id'] | PASS |
| D02 未知 verification 被拒 | unknown | ['unknown verification_id'] | PASS |
| D02 可选验证未执行不阻断 | [] | [] | PASS |
| D02 必要验证未执行被拒 | required verification | ['missing or empty', 'required verification  | PASS |
| D02 未知验收 id 被拒 | unknown acceptance | ['acceptance item has no result', 'unknown a | PASS |
| D03 reverse 缺 before → 不结案 | False | False | PASS |
| D03 before 为空对象 → 不结案 | False | False | PASS |
| D03 承接任务不存在 → 不结案 | False | False | PASS |
| D03 承接路径不覆盖 → 不结案 | False | False | PASS |
| D03 承接已批准且覆盖 → 结案 | True | True | PASS |
| D03 承接批准为空对象 → 不结案 | False | False | PASS |
| D03 reject 不能当 commit 结案 | 不得为 disposed | applied_pending_commit | PASS |
| D04 上标数字不被当倍数 | None | None | PASS |
| D04 写入路径不给内部异常 | TaskError/WF_RECORD_INVALID | ['TaskError', 'WF_RECORD_INVALID'] | PASS |
| D07 文本级脱敏全覆盖 | 无泄漏 | [] | PASS |
| D07 facts 摘要不泄漏 | 无哨兵 | --token *** | PASS |
| D07b 日志不泄漏 | 无哨兵 | True | PASS |

### 72.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **R80-a** | D01 兼容说明与实现不符 | 文档改为事实描述：旧回执按 occurrence 选中、不失配 | 文档 |
| **R80-b** | Check 结构复核不全 | 生成端 `check.validate_check_result()` 单一实现，门禁端直接调用 | 失败验收、替换调用、非零退出、缺结束时间、重复、未知 id 六种均被拒；可选验证不阻断 |
| **R80-c** | 处置事实可被空值绕过 | reverse 要求 `before` 键存在；`_fp_matches` 拒绝空对象；transfer 要求有效批准；writer 要求 choice 等于 kind | 六种构造下只有事实成立才结案 |
| **R80-d** | `²` 触发内部异常 | `tail.isascii() and tail.isdigit()` | 解析返回 None；写入路径 `WF_RECORD_INVALID` |
| **R80-e** | 实际 48 项报 47 | `run_extra` 统一计数 | 现为 49 项、失败 0 |
| **R80-f** | facts/日志仍泄漏 | `redact_text()` 单一实现（Bearer 去长度门槛、补分隔与别名写法） | 四种写法文本级全遮罩；真实失败命令的 facts 与日志无哨兵 |

### 72.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **49 项，失败 0，`exit 0`**；`r72 rc=0 PASS=7`、`f0 rc=0 PASS=9` |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 72.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R73 | r79 的「结构齐全」样本缺 `plan.acceptance` | 新校验把 `a1` 判为未知验收 id | 补齐 plan 的 verification/acceptance 后 18/18 |
| N-R74 | r67 假环境的 r72 桩不输出 PASS 行 | 新的 `run_extra` 按 PASS 计数，桩只有一行 `saved` | 桩改为输出 7 行 PASS |

### 72.5 口径

两轮独立复审的缺陷已全部处置；未覆盖轴仍是「上位文件历次授权的批准链」与「历史实跑声明的原始记录」。实现稿状态保持「按已覆盖轴定稿」。

## 73. R81 实施与实跑（2026-11-04）

复核文见 `review-round46-reconciliation.md`。第三轮独立复审（`codex` 新会话）+ 其他 agent 的 7 条反例。

### 73.1 用例（25/25，r81 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D-B4-1 清单含 ../ 即整批拒绝 | problems 非空且写入为空 | problems=1 writes=0 | PASS |
| D-B4-1b 未知 target_class 被拒 | problems 非空 | 1 | PASS |
| D-B4-1c release_only 跳过且不报错 | 无写入无问题 | writes=0 problems=0 | PASS |
| D-B4-1d 符号链接逃逸被拒 | problems 非空 | 1 | PASS |
| D-A1-5 有可核人判 → 通过 | [] | [] | PASS |
| D-A1-5 无 decision → 阻断 | 非空 | ['manual verification without a decision'] | PASS |
| D-A1-5 choice=reject → 阻断 | 非空 | ["manual decision is not 'passed'"] | PASS |
| D-A1-5 subject 不覆盖 → 阻断 | 非空 | ['manual decision does not cover this verifi | PASS |
| D-B1-1 空决定被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| D-B1-1b 缺理由被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| D-B1-1c 有效决定放行 | None | None | PASS |
| A1 json 模式带正文 | content 非空 | # spec 索引
 | PASS |
| A1b json 模式 complete 与正文一致 | complete=True 且 content 非空 | True/True | PASS |
| A2 task.create 动作与步骤齐备 | kind=task.create 且步骤含 bind | task.create/4 | PASS |
| A3 两个 skill 根各一项 | 2 | 2 | PASS |
| A3b 第二个根改动反映到指纹 | 指纹变化 | True | PASS |
| A6 无证据的 verified 被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED/['capability.evidence | PASS |
| A6b 结构齐全放行 | None | None | PASS |
| A6c 缺 transport 被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| A5 草稿 PRD 不作批准证据 | None | None | PASS |
| A5b 已批准 PRD 作为证据 | 非空 | True | PASS |
| A4 相对候选按项目根解析 | 项目内相对路径 | venv/bin/python | PASS |
| A5c 有效项目配置优先于损坏全局配置 | project | project/None | PASS |
| A5d 非字符串项目值给结构化出口 | WF_EXECUTOR_UNCONFIRMED | WF_EXECUTOR_UNCONFIRMED | PASS |
| A7 wf-start 写明 activation 与 instance_id 重放 | 含两者 | True | PASS |

### 73.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **R81-a** | install 投放不核路径（高） | `safe_relative/inside/plan_writes`，与 uninstall 同判据，整批拒绝 | `../`、未知类别、符号链接逃逸三种被拒；`release_only` 跳过 |
| **R81-b** | manual 验证无证据也过（高） | `validate_check_result` 核 decision、choice、`_decision_covers` | 无 decision / reject / subject 不覆盖 三种均阻断 |
| **R81-c** | 归档恢复假阴性（中） | `archive_persisted(lower_override=…)` + 恢复分支补业务提交 | 提交成功即报 persisted；业务 WIP 一并提交 |
| **R81-d** | 解除依赖可空决定（中） | `_require_release_decision()` 两处调用 | 空决定、缺理由均 `WF_SEMANTIC_DECISION` |
| **R81-e** | JSON 内嵌凭据漏遮（中） | 引号键值规则 + 键名边界 | 4 种 JSON 形态被遮；`tokenizer`/`max_tokens` 不误伤 |
| **#1** | spec json 无正文却记完整读取 | `content` 两路都交付 | json 模式带正文，`complete=true` 与交付一致 |
| **#2** | task-new 意图晚于跨记录变更 | 先落 `task.create` 动作再取写权/绑定 | 动作 kind 与四步齐备 |
| **#3** | 规则指纹只取一个 skill 根 | 每个根各一项 | 两根 → 两项；第二根改动 → 指纹变 |
| **#4** | 解释器身份按 cwd 解析 | 先拼项目根 | 相对候选解析为项目内路径 |
| **#5** | 草稿 PRD 当批准证据 | 要求 `plan.approval` 或正常归档 | 草稿被拒、已批准通过 |
| **#5b** | 损坏全局配置阻断有效项目配置 | 有效项目配置优先 | 项目配置生效、无错误 |
| **#5c** | 非字符串配置值抛 TypeError | 类型校验 | `WF_EXECUTOR_UNCONFIRMED` |
| **#6** | `verified` 缺结构也通过 | 核 host_id/provider/transport/evidence | 无证据、缺 transport 均被拒 |
| **§三** | 检查对象错位 | `check-doc-refs.py` 默认改当前三稿 | 三稿 0 problem |

### 73.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **50 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs`（默认） / `validate-wf-design` | 0 problem / 全绿 |

### 73.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R75 | 重写脱敏时删掉 `SEPARATED_FLAGS` | `task-check` 内部错误 exit 70 | 恢复常量并复验 |
| N-R76 | 恢复分支把 `commit_grants` 当字典 | `'list' object has no attribute 'get'` | 按 Decision 数组摊平 subject |
| N-R77 | `cp5_b345`/`p5_spec` 用 `released: True` + 字符串决定 | 与 Decision 对象判据冲突 | fixture 改 Decision 对象（判据不变） |
| N-R78 | `r64` 断言 json 不带正文 | 与「读取留痕要真实」冲突 | 改为断言 json 也交付正文 |

### 73.5 口径

三轮独立复审 + 其他 agent 反例共处置 20 条行为缺陷。未覆盖轴不变（上位文件授权链、历史实跑原始记录）；`issued_id` 显式签发命令登记为第二轮对象。

## 74. R82 实施与实跑（2026-11-04）

复核文见 `review-round47-reconciliation.md`。第四轮独立复审（`codex` 新会话）+ 其他 agent 的 7 条反例。

### 74.1 用例（25/25，r82 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D-1 写入端保存人判决定 | decision 非空 | {'at': '2026-11-04T14:30:00.000000Z', 'c | PASS |
| D-1b 写入端保存替代路径 | replacement 非空 | .wf/spec/rules/h.md | PASS |
| D-1c 保留旧摘要 | old_digest 非空 | sha256:111111111111111111111111111111111 | PASS |
| D-1d reject 不能当作解除 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| D-2 正常归档不误报目录名 | problems 为空 | [] | PASS |
| D-2b 真不符仍被报出 | problems 非空 | 1 | PASS |
| D-6 非对象条目给结构化问题 | problems 非空 | [{'reason': 'asset entry is not an objec | PASS |
| D-6b 摘要计算拒绝非对象条目 | ValueError | asset entry is not an object | PASS |
| D-4 多词密码 被遮罩 | 不含明文 | {"password":***} | PASS |
| D-4 多词 token 被遮罩 | 不含明文 | {"token":***} | PASS |
| D-4 单引号多词 被遮罩 | 不含明文 | {'secret': ***} | PASS |
| D-5 token_type_ids 不误伤 | 原样 | token_type_ids: [1,2,3] | PASS |
| D-5 max_tokens 不误伤 | 原样 | max_tokens: 4096 | PASS |
| D-5 tokenizer 不误伤 | 原样 | tokenizer: vocab | PASS |
| A1 续做时发现被改动 → 冲突 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A1b 冲突时保留现场 | 内容未被覆盖 | someone else
 | PASS |
| A1c 已是本动作后像 → 跳过 | 内容仍为 mine | mine
 | PASS |
| A1d 符合前像 → 应用 | 内容变为 mine | mine
 | PASS |
| A7 结构齐全放行 | None | None | PASS |
| A7b 不支持的 transport 被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| A7c 只有声明人没有观察 → 被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED | PASS |
| A6 多路径授权正确拆分 | 2 条 | ['pkg/a.py', 'pkg/b.py'] | PASS |
| D-3 报告被改写可被摘要核出 | 摘要不等 | True | PASS |
| D-3b decide 内确有摘要重核 | 含 report file changed after impo | True | PASS |
| D-7 repair 拒绝多回执歧义 | 含多重回执的拒绝 | True | PASS |

### 74.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **D-1/#3** | 解除依赖写入端丢人判（高） | 写回取 `released.decision/replacement`，`choice` 须属 `RELEASE_CHOICES` | 写入后 decision/replacement/old_digest 齐全；reject 被拒 |
| **D-2** | 归档终态巡检全量误报 | `basename(path)` | 正常归档 0 误报；真不符仍报出 |
| **D-3** | 报告可被事后改写 | `decide` 先核 `file_digest` | 改写后摘要不符即入 problems |
| **D-4/D-5** | 脱敏多词漏遮 / `token_type_ids` 误遮 | 两条值规则 + 豁免集合 | 多词被遮；计数键不误伤 |
| **D-6** | install 非对象资产抛裸异常 | 三处结构化拒绝，摘要短路 | 返回 `asset entry is not an object` |
| **D-7** | repair 预览/写入面不一致 | 多回执拒绝 | 同 operation 多回执被拒 |
| **#1** | spec 续做覆盖新内容 | `_resume_decision()` 三态 | 冲突时不覆盖；后像跳过；前像应用 |
| **#2** | task-new 无恢复路径 | `_pending_task_create`/`_resume_task_create` | 重入续做同一任务 |
| **#4** | 批准证据不绑当前 PRD | 比对 `approval.object_digest` 与 PRD 摘要 | 改 PRD 后证据失效 |
| **#5** | skill 误称 wf 签发可用 | 写明未交付；`enable` 给缓存模板 | 文档 + `activation_source/cache_hint` |
| **#6** | 恢复分支不拆多路径授权 | 复用 `_subject_paths()` | `pkg/a.py, pkg/b.py` → 两条 |
| **#7** | transport/证据结构不核 | 白名单 + `kind/ref` 必填 | `unsupported`、仅声明人均被拒 |

### 74.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **51 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs`（默认三稿） / `validate-wf-design` | 0 problem / 全绿 |

### 74.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R79 | preview 证据缺 `kind/ref` | 能力结构收紧后所有夹具 task-new 被拒 | deploy 与 install 两处补 `declared-verification` + `ref` |
| N-R80 | `verify_assets` 非对象检查插错位置（静默未生效） | r82 用例暴露 AttributeError | 按函数体插入并短路摘要计算 |
| N-R81 | r81 的 A5 给的是摘要不匹配的批准 | 判据收紧后必然失败 | 改为摘要匹配 + 新增"改 PRD 即失效"正例 |

### 74.5 口径

四轮独立复审 + 其他 agent 累计处置 34 条；未覆盖轴不变；`issued_id` 仍是第二轮事项。

## 75. R83 实施与实跑（2026-11-04）

复核文见 `review-round48-reconciliation.md`。第五轮独立复审 + 其他 agent 的 3 条反例。

### 75.1 用例（24/24，r83 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A1 任意非空 choice 只做结构核验 | 放行 | None | PASS |
| A1b 无理由仍被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A2 request_json 放行 | None | None | PASS |
| A2b stdio_json 不被宣称支持 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED/['request_json'] | PASS |
| A2b mcp_tool 不被宣称支持 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED/['request_json'] | PASS |
| A2b unsupported 不被宣称支持 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED/['request_json'] | PASS |
| A2c 支持集合只有 request_json | 1 项 | ['request_json'] | PASS |
| A3 自证证据被拒 | WF_IDENTITY_UNRESOLVED | WF_IDENTITY_UNRESOLVED/capability is dec | PASS |
| A3b 观察类别清单来自机制稿 | 4 类 | ['compaction', 'reentry', 'new-session', | PASS |
| A3c 安装器只在有观察时给 verified | 含 _has_observation | True | PASS |
| A5 delete 续做遇外部改动被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A5b 冲突时保留现场 | 内容仍在 | restored by someone
 | PASS |
| A5c 符合前像才删除 | 文件不存在 | False | PASS |
| A5d 已删除再次续做跳过 | 不抛异常 | True | PASS |
| A5e disable 续做遇外部改动被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A5f rename 续做遇外部改动被拒 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A3-agent 跳过正文时补索引 | 索引含该文件 | True | PASS |
| B1 外层 decision 被可见拒绝 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| B2 按派生 id 找到本会话遗留意图 | 命中 | True | PASS |
| B2b 别的会话不认领 | None | None | PASS |
| B2c 同会话重入续做同一任务 | resumed=True 且 task_id 不变 | True/True | PASS |
| B2d 不再新建第二个任务 | 目录唯一 | 1 | PASS |
| B3 decide 对缺失 report_path 有出口 | 含 imported entry lacks report_ | True | PASS |
| B3b decide 对不可读报告有出口 | 含 report file unreadable | True | PASS |

### 75.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **A1** | 自造 choice 词表 | 删词表，退回结构核验 | 任意非空 choice 放行；缺 reason 仍拒 |
| **A2** | 宣称三条 transport | 只留 `request_json` | `stdio_json`/`mcp_tool` 被拒，`supported` 只 1 项 |
| **A3** | 声明式证据自证 | `OBSERVATION_KINDS` + 安装器只在有观察时给 verified | 自证证据被拒；安装器含 `_has_observation` |
| **A5** | 续做保护只覆盖 add/modify | 新增 delete/disable/rename 三态判据 | 四类操作的"外部改动"都被拒且保留现场 |
| **B1** | 外层 decision 静默跳过 | 可见拒绝 | `WF_SEMANTIC_DECISION` |
| **B2** | 恢复逻辑死代码 | 按 action.id 派生定位 + 顺序前置 | 同会话重入 `resumed=True` 且 task_id 不变；异会话不认领 |
| **B3** | 报告缺失炸内部错误 | 两处结构化出口 | 缺失/不可读均 `WF_REVIEW_INVALID` |
| **#3** | skip 时漏补索引 | skip 也执行 `_sync_index` | 索引含该文件 |

### 75.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **52 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs`（默认三稿） / `validate-wf-design` | 0 problem / 全绿 |

### 75.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R82 | `base_revision` 用 `or` 兜底吞掉 0 | 派生 id 用 1 重算，恢复永不匹配 | 显式 `is not None` |
| N-R83 | `holder_hint` 缺 scope | action.id 的 owner_ref 与恢复端推导不同源 | 补 scope |
| N-R84 | install 未解析 `kind=…;ref=…` | 观察证据永不被识别，f0 全挂 | 与 dev-deploy 同一解析 |
| N-R85 | 所有夹具只有 `--verify-capability` | A3 收紧后一律 unknown | 补 `kind=reentry` 真实观察 |

### 75.5 口径

五轮独立复审 + 其他 agent 累计处置 44 条。新增纪律（写入实现稿 §2.3.11）：规范未登记取值域时只核结构、不自造白名单；规范登记了的观察类别必须真被消费。

## 76. R84 实施与实跑（2026-11-04）

复核文见 `review-round49-reconciliation.md`。第六轮独立复审 + 其他 agent 的 4 条反例。

### 76.1 用例（13/13，r84 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A3-9 apply 支索引含新路径 | 含 renamed.md | True | PASS |
| A3-9b skip 支索引也含新路径 | 含 renamed.md | True | PASS |
| A1 rename 目标被改 → 冲突 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| A3-11 disable 合法后像被识别为 skip | 不抛异常 | None | PASS |
| A3-11b disable skip 后索引已同步 | 索引无 d.md（已移除） | False | PASS |
| B2-1 截断 JSON 归一为 RecordInvalid | RecordInvalid | RecordInvalid | PASS |
| B2-1 非法 JSON 归一为 RecordInvalid | RecordInvalid | RecordInvalid | PASS |
| B2-1 常量 JSON 归一为 RecordInvalid | RecordInvalid | RecordInvalid | PASS |
| B4-1 d 桶在实现稿登记 | 含归属语义存疑的边界说明 | True | PASS |
| A3-agent 恢复在有绑定时拦实例不符 | WF_BINDING_MISMATCH 或 WF_OK（无绑定可 | WF_OK | PASS |
| A3-agent2 恢复路径核实例标识 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| A4 bind 有恢复入口 | 含 _resume_bind | True | PASS |
| A4b bind 意图先于绑定写入 | mutate 里写绑定 | True | PASS |

### 76.2 缺陷处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **A3-9** | 改名 skip/apply 都不补索引 | 替换未命中时退回 add | 两支索引都含新路径 |
| **A3-11/#2** | disable 合法后像被误判冲突 | 解析 frontmatter `status=disabled` 即跳过 | 续做不抛异常且索引已同步 |
| **#1** | 改名目标被改仍判成功 | 有前像须目标内容相符 | 目标被改 → `WF_SEMANTIC_DECISION` |
| **B2-1** | 损坏 JSON 泄漏 exit 70 | `loads()` 归一为 `RecordInvalid` | 截断/非法/NaN 三种均归一 |
| **#3** | 恢复入口绕过实例核验 | 复用 `_require_instance_match` | 实例不符 → `WF_BINDING_MISMATCH` |
| **#4** | bind 先写绑定后登记动作 | 绑定写入搬进动作 mutate + `_resume_bind` | 恢复入口存在、意图先于绑定 |
| **B4-1** | d 桶恒为空 | 登记为首轮已知边界 | 实现稿 §2.3.11 |

### 76.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **53 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs`（默认三稿） / `validate-wf-design` | 0 problem / 全绿 |

### 76.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R86 | 恢复路径引用未赋值的 `instance_id` | 恢复入口 exit 70 | 从 session 取 |
| N-R87 | 调用了不存在的 `_frontmatter_meta` | disable 分支报错 | 直接用 `parse_frontmatter` |
| N-R88 | r84 用例 frontmatter 未用 JSON 值 | 判据正确、用例错 | 改为 `"disabled"` |

### 76.5 口径

六轮独立复审 + 其他 agent 累计处置 50 条。通过面集中在历史反复出错的四处；跨记录写入（task-new / bind）仍是薄弱带。

## 77. R85 实施与实跑（2026-11-04）

复核文见 `review-round50-reconciliation.md`。第七轮独立复审 + 其他 agent 的 7 条。

### 77.1 用例（16/16，r85 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R50-01 创建走暂存目录后原子发布 | 含 .staging- | True | PASS |
| R50-01b 意图随记录一次写入 | 记录先带 task.create 再保存 | True | PASS |
| R50-02 有未完成意图时阻断其他会话 | 含 _any_pending_task_create | True | PASS |
| R50-07 已完成动作可重试返回原结果 | 含 already_completed | True | PASS |
| R50-08 同一目标不重复 | 只有一条 | 1 | PASS |
| R50-08b 未闭合围栏拒绝同步 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R50-09 已 disabled 但不可推定 → 交人核对 | WF_SEMANTIC_DECISION | WF_SEMANTIC_DECISION | PASS |
| R50-10 证据缺失被识破 | problems 非空 | [{'subject': 'debug-ruling-v1-1', 'r | PASS |
| R50-10b 符号引用不误判 | [] | [] | PASS |
| R50-11 预览含会话身份 | 含 session_profile 段 | True | PASS |
| P1-1 外部变更数量进入 facts | 含 external_pending | True | PASS |
| P1-3 巡检含归档引用 | archive_references | ['archive_references', 'archive_term | PASS |
| P2-2 删除事实可作交付 | 含 _removal_attributed | True | PASS |
| P2-3 候选唯一性不在 ordinary 分支内 | if others 出现在 ordinary 分支之后且同级 | ordinary=True others=True | PASS |
| P2-4 门禁区分 REVIEW_UNAVAILABLE | 含 WF_REVIEW_UNAVAILABLE | True | PASS |
| P2-5 复杂度提示键带出 | 含 complexity_hints | True | PASS |

### 77.2 处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **R50-01** | 创建留下无意图中间态 | 暂存目录 + 记录带意图一次发布 | 代码含 `.staging-`；意图随记录落盘 |
| **R50-02** | 别会话可越过未完成意图 | 全仓 `_any_pending_task_create()` 阻断 | 命中即 `WF_WRITER_BUSY` |
| **R50-03** | bind 写权先于意图 | 写权与意图同一次写入 | 无"已取写权无动作"窗口 |
| **R50-04** | 绑定后重入提前成功 | 已有绑定先续做结案 | 动作不再永久 prepared |
| **R50-05** | 恢复可改绑目标 | 目标取自 `action.targets` | 请求不符即拒绝 |
| **R50-06** | 恢复不核后置 | 核目录/产物/绑定/运行态 | 删 prd.md 后恢复被拒 |
| **R50-07** | 重试报 BINDING_MISMATCH | 已结案动作返回原结果 | `already_completed` |
| **R50-08** | 索引重复/损坏 | 去重 + 未闭合围栏拒绝 | 同目标仅一条；损坏即拒 |
| **R50-09** | 任意 disabled 当后像 | 交人核对出口 | `WF_SEMANTIC_DECISION` |
| **R50-10** | 复盘不核调试证据 | `retrospective_evidence_problems()` | 缺失即阻断；符号引用不误判 |
| **R50-11** | 预览不显示身份 | 预览 + facts 带 session_profile | 段落与字段齐全 |
| **P2-2/3/4/5** | 四类语义缺口 | 删除算交付、候选唯一、审查分流、提示键浮现 | 各自用例通过 |

### 77.3 登记边界（未实现，写明理由）

| 条目 | 状态 |
|---|---|
| P1-1 外部变更阻断 | 只把 `external_pending` 带进 facts。做成阻断会让全部正常流程变红——提交归属依赖 trailer、而 trailer 只由框架提交路径写入；需要先补"提交归属判定面"（机制级） |
| P1-2 finish→check 迁移 | 需机制面新增受控迁移，留人裁决 |
| P2-1 `.wf/out-of-scope/` | 首轮不做，schema 留在机制稿 |
| 实现稿 §2.3.11 d 桶 | 上一轮已登记（首轮不产生） |

### 77.4 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **54 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 77.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R89 | 夹具提交补 trailer 后 `.wf/project-config.json` 进业务提交 | 落 f 桶越界，53 项里 7 项变红 | 回滚该改动，恢复夹具原样 |
| N-R90 | 复盘证据把 `handoff` 当路径 | 合法流程被判缺证据 | 只核形如路径的引用 |
| N-R91 | `base_revision` 用 `or` 兜底吞 0 | 派生定位错位（N-R82 同型复发） | 显式判断 |
| N-R92 | 三个用例需跟随新契约 | r75/r82/r84 期望过时 | 按新契约调整 |

## 78. R86 实施与实跑（2026-11-04）

复核文见 `review-round51-reconciliation.md`。第八轮独立复审（pi/kimi）：18 条缺陷 + 1 处崩溃。

### 78.1 用例（17/17，r86 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 崩溃：删除归属判定不再抛异常 | 返回布尔 | False crash=None | PASS |
| D-11 符号引用不误判 | 不含 handoff | True | PASS |
| D-12 目录证据被拒 | 含 evidence | True | PASS |
| D-12b 缺失文件被拒 | 含 missing.txt | True | PASS |
| D-12c check 条目内证据缺失被拒 | 含 check:v1 | True | PASS |
| D-04 d 桶进入范围事实 | 含 ambiguous_ownership | True | PASS |
| D-04b 跨任务冲突检测存在 | 含 cross_task_conflicts | True | PASS |
| D-01 未接线的外部变更 helper 已删 | 无 _external_touches_task | True | PASS |
| D-02 spec-update 与 baseline-apply 阶段口径一致 | 两处都含 finish | True | PASS |
| D-02b finish 期变更要求重检 | 含 requires_recheck | True | PASS |
| D-13 无异常归档误报 | 不含 abnormal 未提交 | [] | PASS |
| D-14 引用检查带 unknown 分类 | 含 unknown/status | ['dangling', 'status', 'unknown'] | PASS |
| D-15 install 预览与落盘共用证据构造 | 含 _profile_evidence | True | PASS |
| D-16 开发态预览含 session_profile | 含 session_profile | True | PASS |
| D-17 复现比对用 sha256 | 含 file_digest | True | PASS |
| D-18 版本一致性有断言 | 含 _assert_version_consistency | True | PASS |
| stdin 无管道时明确报错 | 含 must be piped on stdin | True | PASS |

### 78.2 处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **崩溃** | `_removal_attributed` 把列表当字典 → exit 70 | 按列表语义判成员 | 真删除场景返回布尔、不抛异常 |
| **D-01** | 外部变更静默 pass + 死 helper | 删 helper，保留 `external_pending` 事实 | 源码无 `_external_touches_task` |
| **D-02** | 两入口阶段口径不一 | 统一 `execute/check/finish`，finish 期 `requires_recheck` | 两处元组一致 |
| **D-04** | d 桶静默 pass、跨任务双认领 | d 桶进 facts 并阻断；新增活冲突检测 | `ambiguous_ownership` / `cross_task_conflicts` |
| **D-11/D-12** | 证据引用分类错误 | 符号/check:<id>/目录/文件分流 | 四类各自判定正确 |
| **D-13** | 异常归档误报 | 改用 `_record_committed` | 无误报 |
| **D-14** | 引用检查覆盖不足 | 活动+归档全扫，实例字段 unknown | `dangling/unknown/status` 三档 |
| **D-15/D-16** | 预览与落盘不一致 | `_profile_evidence()` 单一构造；dev 预览补身份 | 两处含同一构造 |
| **D-17** | 字节复现可绕过 | 逐文件 sha256 | `--verify` 通过 |
| **D-18** | 版本无机械校验 | `_assert_version_consistency` | 占位符放行、真分叉报错 |
| **D-10** | inspect 不报孤儿/治理问题 | 进 warnings | — |
| 收尾 | stdin 静默挂起 | `isatty()` 直接报错 | — |

### 78.3 登记（待人裁）

`pending-decisions.md` §3：①主记录/意图归属合并为 writer 单一父动作（含 `action` 字段登记）；②外部变更是否启用阻断（需先有提交归属判定面）；③Finish→Check 受控迁移。另登记 `.wf/out-of-scope/`、`assets.branch_source_check`。

### 78.4 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **55 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |
| 源树 `__pycache__`/`.pyc` | 0 |

### 78.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R93 | d 桶阻断后立刻 `WF_CHECK_STALE` | 结束前重算的快照键集合未含 d | after 快照补键 |
| N-R94 | 冲突检测把历史归属算成冲突 | r46/r56 等正常流程被挡 | 只认活冲突（未提交 + 活动任务） |
| N-R95 | finish 期 `next_` 未明说要重检 | 方向不明 | 返回 `requires_recheck` |
| N-R96 | 删 helper 用文本切片有连带风险 | 已用编译 + 全量回归复核 | 无连带删除 |

## 79. R87 实施与实跑（2026-11-04）

复核文见 `review-round52-reconciliation.md`。第九轮独立复审：3 条裁决建议 + 2 条缺陷 + 3 条观察。

### 79.1 用例（19/19，r86 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 崩溃：删除归属判定不再抛异常 | 返回布尔 | False crash=None | PASS |
| D-11 符号引用不误判 | 不含 handoff | True | PASS |
| D-12 目录证据被拒 | 含 evidence | True | PASS |
| D-12b 缺失文件被拒 | 含 missing.txt | True | PASS |
| D-12c check 条目内证据缺失被拒 | 含 check:v1 | True | PASS |
| D-04 d 桶已进范围事实（当前分类下不可达，仅结构存在） | 含 ambiguous_ownership | True | PASS |
| D-04b 跨任务冲突检测存在 | 含 cross_task_conflicts | True | PASS |
| D-01 未接线的外部变更 helper 已删 | 无 _external_touches_task | True | PASS |
| D-02 spec-update 与 baseline-apply 阶段口径一致 | 两处都含 finish | True | PASS |
| D-02b finish 期变更要求重检 | 含 requires_recheck | True | PASS |
| D-13 无异常归档误报 | 不含 abnormal 未提交 | [] | PASS |
| D-14 引用检查带 unknown 分类 | 含 unknown/status | ['dangling', 'status', 'unknown' | PASS |
| D-15 install 预览与落盘共用证据构造 | 含 _profile_evidence | True | PASS |
| D-16 开发态预览含 session_profile | 含 session_profile | True | PASS |
| D-17 复现比对用 sha256 | 含 file_digest | True | PASS |
| D-18 版本一致性有断言 | 含 _assert_version_consistenc | True | PASS |
| stdin 无管道时明确报错 | 含 must be piped on stdin | True | PASS |
| N52-01 冲突判定以保存的 WIP 为准 | 含 handoff.wip.paths 语义 | True | PASS |
| N52-01b 不再用历史归属路径求交 | 不含 attributed_paths 直接求交 | True | PASS |

### 79.2 处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **N52-01**（P1） | 历史归属被当永久所有权 | 活冲突只认另一任务未处置的 `handoff.wip.paths` | 暂停任务的历史提交不再误挡；WIP 声明仍能挡 |
| **N52-02**（P2） | 阶段行为与实现稿相反 | 文档改为与代码一致，单列未交付的回迁动作 | `check-doc-refs` 0 problem |
| 观察 1 | d 桶不可达被误当已判定 | 用例改名注明"结构存在、当前不可达" | — |
| 观察 2 | `baseline-apply` 缺对称提示 | finish 期同样返回 `requires_recheck` | 两入口对称 |
| 观察 3 | 巡检两类未登记 | 写入 §2.3.11 并注明排期 | — |

### 79.3 三条裁决建议

全部**采纳为方案**并写入 `pending-decisions.md` §3，其中两条（意图归属、外部变更阻断）仍需人裁后才能动代码；第三条（Finish→Check 迁移）同样是机制面新增。

### 79.4 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **55 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 79.5 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R97 | 两入口 finish 期提示不对称 | 只改了 spec-update | 补齐 baseline-apply |
| N-R98 | §2.3.11 插入点影响相邻条目 | 需确认章节顺序 | 文档检查通过 |

## 80. R88 实施与实跑（2026-11-04）

复核文见 `review-round53-reconciliation.md`。第十轮独立复审（收口判断轮）+ 其他 agent 3 条。

### 80.1 用例（19/19，r86 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| 崩溃：删除归属判定不再抛异常 | 返回布尔 | False crash=None | PASS |
| D-11 符号引用不误判 | 不含 handoff | True | PASS |
| D-12 目录证据被拒 | 含 evidence | True | PASS |
| D-12b 缺失文件被拒 | 含 missing.txt | True | PASS |
| D-12c check 条目内证据缺失被拒 | 含 check:v1 | True | PASS |
| D-04 d 桶已进范围事实（当前分类下不可达，仅结构存在） | 含 ambiguous_ownership | True | PASS |
| D-04b 跨任务冲突检测存在 | 含 cross_task_conflicts | True | PASS |
| D-01 外部变更 helper 已接线（未决即阻断） | 含 _external_touches_task 且被消 | True | PASS |
| D-02 spec-update 与 baseline-apply 阶段口径一致 | 两处都含 finish | True | PASS |
| D-02b finish 期变更要求重检 | 含 requires_recheck | True | PASS |
| D-13 无异常归档误报 | 不含 abnormal 未提交 | [] | PASS |
| D-14 引用检查带 unknown 分类 | 含 unknown/status | ['dangling', 'status', 'unknown' | PASS |
| D-15 install 预览与落盘共用证据构造 | 含 _profile_evidence | True | PASS |
| D-16 开发态预览含 session_profile | 含 session_profile | True | PASS |
| D-17 复现比对用 sha256 | 含 file_digest | True | PASS |
| D-18 版本一致性有断言 | 含 _assert_version_consistenc | True | PASS |
| stdin 无管道时明确报错 | 含 must be piped on stdin | True | PASS |
| N52-01 冲突判定以保存的 WIP 为准 | 含 handoff.wip.paths 语义 | True | PASS |
| N52-01b 不再用历史归属路径求交 | 不含 attributed_paths 直接求交 | True | PASS |

### 80.2 处置

| 项 | 处置 | 证据 |
|---|---|---|
| 外部变更（阻塞项 2，建议 A） | 未归属且触及触碰面的提交必须有「已核对无影响」人判，否则 `WF_SEMANTIC_DECISION` | 8 个套件以人判声明通过；无声明时阻断 |
| 意图归属（阻塞项 1） | 维持人裁，选项收敛 A/B | `pending-decisions.md` §3 |
| Finish→Check（阻塞项 3） | 维持人裁 | 同上 |
| D24/D30/G03 | 按真实函数落点改写，注明无消费点 | `check-doc-refs` 0 problem |
| 归档 PRD 证据 | 比对 `plan.approval.object_digest` | 归档任务 PRD 被改后不再作批准依据 |
| `.wf/out-of-scope/`、巡检两类 | 维持登记 | 实现稿 §2.3.11 |

### 80.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **55 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |
| 源树 `__pycache__`/`.pyc` | 0 |

### 80.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R99 | 阻断启用后 8 个套件全红 | 夹具提交无 trailer | 补人判声明，不退判定 |
| N-R100 | "helper 已删"的断言在接线后变假 | 约束断言应写"被消费" | 改为检查 `pending_external` 消费点 |

### 80.5 收口判断

三条阻塞项：一条已落地、两条待裁。当前可称 **首轮实现候选**，不称首轮闭环完成。

## 81. R89 实施与实跑（2026-11-04）：人裁 A 落地

复核文见 `review-round54-reconciliation.md`。

### 81.1 用例（11/11，r87 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| A1 主记录为 writer 的 task.create | task.create | task.create | PASS |
| A2 四步全部结案 | ['create_dir', 'write_record | ['create_dir', 'write_record', 'ac | PASS |
| A3 目标固定（writer/task/binding/runtime） | ['binding', 'runtime', 'task | ['binding', 'runtime', 'task', 'wr | PASS |
| A4 任务记录不再承载创建动作 | None | None | PASS |
| A5 绑定与运行态齐备 | True | True | PASS |
| A6 重入按原意图续做同一任务 | True/True | True/True | PASS |
| A7 续做后动作结案 | done | done | PASS |
| B0 检查已通过 | pass | pass | PASS |
| B1 finish 期变更回 check | True/check | True/check | PASS |
| B2 旧检查保留并登记失效 | ['action_id', 'at', 'by', 'r | ['action_id', 'at', 'by', 'reason' | PASS |
| B3 失效的旧检查不再通过门禁 | WF_CHECK_STALE | WF_CHECK_STALE | PASS |

### 81.2 实施

| 项 | 实施 | 证据 |
|---|---|---|
| **主记录** | `task.create` 写在 writer 的 `action`，`task.action` 为空 | A1/A4 |
| **目标固定** | `targets` 含 writer/task/binding/runtime | A3 |
| **步骤推进** | 四步逐个 done 后结案；未完成拒结案 | A2 |
| **身份固定** | `instance_id` 在意图里一次写定 | A5/A6 |
| **恢复** | 任务 id 取自 `action.targets`，实例不符即拒 | A6 |
| **Finish→Check** | 回 check、旧检查登记 `invalidated`、门禁 `WF_CHECK_STALE` | B1/B2/B3 |

### 81.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **56 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |
| 源树 `.pyc` | 0 |

### 81.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R101 | 重写时删掉 `APPROVE_CHOICES`/`COMPLEXITY_CONDITIONS` | 运行期 NameError；后者原本两处都未定义（潜伏死路径） | 补回并键名对齐 |
| N-R102 | 恢复排在"已绑定"之后 | 绑定已写时提前返回成功 | 恢复提到绑定分支之前 |
| N-R103 | 三个用例仍按旧结构注入 | 与新协议不符 | 改为退回 writer 父动作状态 |

### 81.5 口径

第十轮三条阻塞项全部处置；剩余登记项均不阻塞首轮。

### 81.6 复审前的收尾清理（同轮）

| # | 事项 | 事实 | 处置 |
|---|---|---|---|
| N-R104 | 三个 helper 在合并后成为死代码 | `_pending_task_create`/`_any_pending_task_create`/`task_owner_scope` 已无调用方 | 删除；r83/r85 里依赖它们的断言改为按 writer 意图判定 |

## 82. R90 实施与实跑（2026-11-04）

复核文见 `review-round55-reconciliation.md`。第十一轮定向复审（A 改动）判 A1 不成立，给 D1–D5。

### 82.1 用例（7/7，r88 套件；另 r87 11/11）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| D1 早期中断可续做同一任务 | True/True | True/True | PASS |
| D1b 目录与产物被重建 | True/True | True/True | PASS |
| D1c 绑定与运行态被重建 | [True, False] | [True, False] | PASS |
| D2 意图固定 instance 目标 | True | True | PASS |
| D2b 重入只接受意图里的实例 | WF_BINDING_MISMATCH | WF_BINDING_MISMATCH | PASS |
| D3 伪造 done 仍会补做真实后置 | WF_OK/True | WF_OK/True | PASS |
| D4 旧 task.create 动作给出明确出口 | WF_RECORD_INVALID | WF_RECORD_INVALID | PASS |

### 82.2 处置

| 编号 | 缺陷 | 实施 | 证据 |
|---|---|---|---|
| **D1** | 早期中断不可恢复 | 逐步推进器 + 幂等补步；模板/标题/kind 进 targets | 删目录/绑定后重入仍续做同一任务并重建产物 |
| **D2** | 实例未固定 | instance 进 targets；请求值不符即拒 | 新实例重入被 `WF_BINDING_MISMATCH` 拒 |
| **D3** | 伪造 done 可绕过 | 结案前重核每步真实后置 | 手工标 done 仍补做真实后置 |
| **D4** | 旧 task.action 永久阻塞 | 识别遗留形态并给 repair 出口 | `WF_RECORD_INVALID` + remedy |
| **D5** | 文档与实测不符 | 随 D1–D3 修复成立 | 文档逐句对应实现 |

### 82.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **57 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 82.4 期间新发现并修正

| # | 缺陷 | 事实 | 修正 |
|---|---|---|---|
| N-R105 | 意图 inputs 只存摘要 | 早期恢复拿不到模板 | 模板/标题/kind 写进 targets |
| N-R106 | r84 用例期望过窄 | 实例不符也可能先撞 WRITER_BUSY | 断言改为"不得放行"+保留精确断言 |
| N-R107 | r87/r88 依赖夹具配置 | 缺 project-config 时 start 直接失败 | 用例内自带创建 |

## 83. R91 实施与实跑（2026-11-05）

复核文见 `review-round56-reconciliation.md`。第十二轮独立复审：复验 A1 的修复。

### 83.1 复审结论（原文要点）

| 项 | 结果 |
|---|---|
| 7 个注入点 | 全部通过：同一 task_id、按需重建产物、状态与后置一致 |
| D1 早期中断 / D2 实例固定 / D3 伪造 done / D4 旧动作 | 四项均通过 |
| targets 篡改 | `WF_BINDING_MISMATCH`，未放行 |
| r87 / r88 | 11/11、7/7，退出 0 |
| Finish→Check 独立链 | 通过（回 check、invalidation、门禁 stale、再次 Check 生成新 id） |
| **A1 判定** | **成立 / 修复可接受** |

### 83.2 本轮改动

| 项 | 级别 | 处置 |
|---|---|---|
| `repair --dispose` 锁忙沿用写权语义 | P1-1 | 文案与 facts 明确"不要求写权空闲、只需互斥，稍后重试"，加 `guidance` |
| `gates.py` 死分支 `if not task.get("prerequisites"): pass` | P3 | 删除 |
| 状态行"定稿"与收口计划的口径张力 | 文档 | 重写为"12 轮逐轮定向 + 未覆盖轴"，不再用定稿覆盖未复审事实 |

### 83.3 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **57 项，失败 0，`exit 0`** |
| `unittest` 两组 | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` / `validate-wf-design` | 0 problem / 全绿 |

### 83.4 登记

`pending-decisions.md` §4：`status` 维护态观测（维持，第二轮）、`probe_version` 冗余、`uninstall` 预览近似、skill 纪律段重复（裁量）、**dogfood 建议尽快启动**、E 轨道口径已消解。

### 83.5 口径

十二轮独立复审 + 其他 agent：**80 条已处置、9 条登记、0 条阻塞**。A1 修复可接受；未覆盖轴已如实列入实现稿状态行。

## 84. R92 实施与实跑（2026-11-05）：`--skill-root` → `--platform`

人裁：技能必须装在**目标项目内**；要区分 agent 发现层就按平台解析，不接受任意投放根。

### 84.1 平台表（依据均为官方文档，见实现稿 §2.3.10.1）

| 平台 | 自有目录 | 读共享层 | 落地 |
|---|---|---|---|
| `dsh` / `codex` / `cursor` / `geminicli` / `copilot` | 见文档表 | 是 | `.agents/skills/` |
| `claudecode` | `.claude/skills/` | 否 | `.claude/skills/` |

规则：能读共享层就用共享层，否则用自有目录；多平台取并集；未知名直接拒绝并列支持项，**不按目录存在性猜**。

### 84.2 用例（9/9，r89 套件）

| 用例 | 预期 | 实际 | 结果 |
|---|---|---|---|
| R92 dsh 装在项目内 .agents/skills | WF_OK | WF_OK | PASS |
| R92b 记录里 roots 为相对路径、platforms 已写入 | ['.agents/skills'] / ['dsh'] | ['.agents/skills'] / ['dsh'] | PASS |
| R92 claudecode 只落在 .claude/skills | 0/False | 0/False | PASS |
| R92 多平台取并集 | True/True | True/True | PASS |
| R92 未知平台被拒 | WF_PATH_INVALID/False | WF_PATH_INVALID/False | PASS |
| R92 省略平台被拒 | WF_PATH_INVALID | WF_PATH_INVALID | PASS |
| R92 --skill-root 已移除 | True | True | PASS |
| R92 安装产物登记为项目内路径 | ['.agents/skills/wf-bootstrap/SKIL | ['.agents/skills/wf-bootstrap/SKIL | PASS |
| R92b 技能副本不被算作任务交付物 | b=58 c=0 | b=58 c=0 | PASS |

### 84.3 连带修正（都是这次改动暴露出来的）

| # | 问题 | 事实 | 修正 |
|---|---|---|---|
| N-R108 | 技能副本进了项目后，Check 把它们当"未归属改动"挡住 | F0 的 Check 返回 `WF_WORKSPACE_UNRESOLVED`；fixture 里 5 个套件掉 PASS | `scope.installed_asset_paths()` 读 `installation.json` 的投放清单（含 `root_ref` 换算），把安装产物归入 b 桶（控制面），不按目录名猜 |
| N-R109 | 维护组回执现在含 `.agents/skills/**`，夹具只提交 `.wf`+`.gitignore` | p5_v2v3 处置后仍 `WF_HISTORY_UNRESOLVED` | 夹具提交覆盖回执登记的全部路径（`.wf`、`.gitignore`、`.agents`） |
| N-R110 | `installation.json.roots` 之前对项目内根记相对、对外部根记绝对 | 平台化后一律项目内 | 统一记相对路径，并新增 `platforms` 字段记录人声明的平台 |

### 84.4 契约层影响

设计稿 §1.2 原本要求"人声明 CLI 与其可读根，缺省候选 `.agents/skills/`"——`--platform` 正是这条的落地形态：人声明 CLI，根由平台表解析。机制稿 §10.1 提到的"项目外宿主 skill 根"因此**首轮不支持**（入口不再能表达），已在实现稿 §2.3.10.1 与 `pending-decisions.md` §4 登记为边界。

### 84.5 回归

| 项 | 结果 |
|---|---|
| `run_all.sh` | **58 项，失败 0，`exit 0`** |
| `unittest` | OK |
| `build --verify` / `--verify-token-parity` | 通过 / 通过 |
| `check-doc-refs` | 0 problem |

## 85. D1 绑定轴：压缩后复核（2026-11-05，第三次真实压缩之后）

### 85.1 观察

| 项 | 值 |
|---|---|
| 压缩后 `$DSH_SESSION_ID` | `session-826cbd83-3b6e-4185-830e-2d87287e7c77`（与 §0 快照一致） |
| 重算 `session_key()` | `7eeebb62…3d8ff7`，与磁盘绑定文件名一致 |
| `status`（**不带** instance_id） | `WF_OK`；`facts.binding.object.id = 2026-1e1b84fdcff74a00bfc1b498b7215d78`、`facts.binding.instance_id = 48b3b8d9…521f7a`、`generation=3` |
| `status`（带 instance_id） | 同上，结果一致 |
| startup 自查 | `binding/record/graph/workspace` 四步均 `ok` |

**判定：绑定轴成立**——压缩后标识未变，绑定键由标识确定性重算并命中同一对象，读写路径（startup 四项）无一项因压缩失败。

### 85.2 口径（不夸大）

- 成立的断言：**压缩不改变宿主身份标识，也不使绑定失效**。
- 不成立的推论：不证明"模型记住了 instance_id"——本次 instance_id 是从会话侧车
  （`~/.cache/wf-fixtures/d1host/.wf/session-bindings/*.json`）读的，不是从上下文回忆的；
  也不证明进程重启/跨设备场景的稳定性（`$DSH_SESSION_ID` 在同一进程内本就稳定）。
- 因此 `capability.status=verified` 的证据保持 `kind=compaction`，但不升级为"宿主身份稳定性已完全核实"。

### 85.3 由此关闭的登记项

`pending-decisions.md` 与实现稿状态行里的"未覆盖轴：D1 绑定轴"→ 本轮已覆盖，剩余未覆盖轴为：
真实断电/并发竞争、`repair` 接管路径、dogfood 真实使用观察。

## 86. 回归耗时剖析与迭代方式（2026-11-05）

全量 `run_all.sh` 实测 **4 分 10 秒**（58 项）。逐项计时（`run_all.sh` 现在会打印每项耗时）：

| 项 | 耗时 | 说明 |
|---|---|---|
| r68_tests | 42s | 83 次 CLI 调用（cProfile：38.8s 全在 `subprocess.run`） |
| r17r24_tests | 39s | 同类 |
| r7r15_tests | 21s | 同类 |
| cp1_tests | 19s | 同类 |
| 其余 49 项 | 87s | 平均 ~1.8s |

单次 CLI 调用实测 60–70ms（裸解释器 9ms、导入 wflib 31ms、`status` 60ms），说明**耗时是"调用次数 × 每次进程启动 + 少量 git/子进程"**，不是框架算法慢。

优化已做与可做：

| 措施 | 状态 | 效果 |
|---|---|---|
| 逐项耗时打印 | 已加 | 慢项一眼可见 |
| `WF_SUITES="r88_tests r89_tests"` 子集模式 | 已加 | 子集 4.5s，迭代期替代全量 |
| `WF_REBUILD_RELEASE=0` 复用发行仓库 | 已有 | 省发行重建 |
| 套件并行（每 worker 一个夹具目录） | 待办 | 预计全量 4min → ~1.5min（本机 4 核+） |
| 合并 r68/r17r24 里的重复 git 提交与重复 CLI 调用 | 待办 | 可省 ~40s |

## 87. 并行执行（2026-11-05）

### 87.1 做法

`run_all.sh` 默认 4 并发（`WF_JOBS`），每个 worker 用 **user namespace 私有 /tmp**（`unshare -Urm` + `mount -t tmpfs tmpfs /tmp`），
再把共享发行仓库**只读 bind 挂**进 `/tmp/wf-fixtures/release-repo`。这样套件里写死的 `/tmp/...` 路径天然互不干扰，
不需要改 67 个文件里的 431 处字面量。

`unshare` 不可用时自动退回串行（有提示）。

### 87.2 实测

| 模式 | 用时 | 结果 |
|---|---|---|
| 串行（改前） | **4 分 10 秒** | 58 项全绿 |
| 并行 `WF_JOBS=4` | **2 分 19 秒** | 58 项全绿（连续 3 次） |
| 并行 `WF_JOBS=6` | 2 分 23 秒 | 58 项全绿（另一份串行尾段，提升不再明显） |
| 子集 `WF_SUITES="r88_tests r89_tests"` | **4.5 秒** | 迭代期用这个 |

### 87.3 必须在串行段跑的 8 个套件（已登记原因）

| 套件 | 原因 |
|---|---|
| `cp3_tests` | 会写 `~/.wf/config.json`（故意写非法值再删），并行窗口内其他 worker 会读到它 → `WF_EXECUTOR_UNCONFIRMED` |
| `r1r2_tests`、`r68_tests` | 用"把目录改成不可写"模拟写入失败；在 user namespace 里我们是 root，chmod 不生效 → 断言失效 |
| `r69_tests`、`r70_tests`、`r89_tests`、`r67_tests`、`r7r15_tests` | 依赖宿主 `/tmp` 的跨套件状态或全局/系统级解释器记录 |

**下一步（可选）**：把这几个的"权限失败注入"改成"父路径是普通文件 → ENOTDIR"（与 root 无关），即可并入并行池，
预计全量再降到 ~60–70 秒。这是纯测试改造，判据不变。

### 87.4 期间修的问题

| # | 问题 | 修正 |
|---|---|---|
| N-R111 | `run_one.sh` 初版漏了 `unshare`，mount 报"必须以超级用户身份" | 由 `run_all.sh` 以 `unshare -Urm` 调用 |
| N-R112 | 隔离后 6 个套件失败（root 使 chmod 失效、跨套件 `/tmp` 状态） | 独立出 `PARALLEL_SERIAL` 串行段 |
| N-R113 | 曾试图用 per-worker `HOME` 隔离全局记录 → 全部 INIT-FAILED（`confirm-executor` 要求人在终端，不能脚本代填） | 回退；改由串行段处理 |
| N-R114 | 批量把 `>/dev/null` 换成 `>>"$log"` 时误改 `run_flow`（`log` 未定义）→ 流程 INIT-FAILED | `run_flow` 自带 log |
| N-R115 | `r67` 的假 `run_all.sh` 环境缺 `run_one.sh`，并行段无结果行 → 失败不传播 | 假环境补 `run_one.sh` 与 `wf_fixture.sh` |

### 87.5 口径

并行不改变判据：`run_one.sh` 与 `run_suite` 用同一套失败判定（rc、`[FAIL]` 计数、汇总行 0/FAIL）。
串行模式仍可用 `WF_JOBS=1` 完整复现。

## 88. 性能：一次 Check 里的 git 子进程（2026-11-05）

### 88.1 发现

给 `r68` 做耗时剖析时发现：**一次 `task-check` 会起 635 个子进程**，其中
`git ls-tree` 264 次、`git show` 286 次——因为 `tasks._committed_fingerprint()` 是"每 (提交, 路径) 起两次 git"。
这不是测试问题，是**最常用命令**的实现问题。

### 88.2 修法

提交对象不可变，所以按对象缓存是安全的：

| 缓存 | 键 | 取代 |
|---|---|---|
| `_tree_entries(root, sha)` | `(root, sha)` | 每路径一次 `git ls-tree` → 每提交一次 `git ls-tree -r -z` |
| `_blob_digest(root, sha, blob)` | `(root, sha, blob)` | 每路径一次 `git show` → 每 blob 一次 `git cat-file blob` |

**没有**缓存祖先判定与提交列表：同进程调用方（多个套件直接 `import wflib` 后自行提交）会改 HEAD，
缓存会给出陈旧事实——试过一版，`r59/r60/r31r34/r17r24` 立刻红，已回退并写进注释。

### 88.3 实测

| 指标 | 改前 | 改后 |
|---|---|---|
| 单次 `task-check` | 1.87s | **0.38s**（4.9×） |
| `r68_tests`（83 次 CLI） | 33.5s | **12.4s** |
| `r17r24_tests` | 43s | 15s |
| 全量并行 `WF_JOBS=4` | 140s | **88s** |
| 全量串行（旧） | 250s | 约 150s（同比例下降） |

### 88.4 口径

- 判定条件未变，58 项并行全绿（`exit 0`）；串行模式另跑一次确认。
- 缓存只按**不可变提交对象**建键，进程结束即释放；不落盘、不跨进程。
- 仍未做：`merge-base` 35 次与 `rev-list` 24 次（需要"HEAD 变化即失效"的机制，本轮不引入）。
