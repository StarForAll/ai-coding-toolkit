# 执行计划

顺序按"先机制、后指引、最后文档"，每一步都能独立验证与回退。收口前不提交（等用户同意）。

## 1. 材料原子发布（F1a）

- [x] 1.1 `review.prepare_context` 的 `unmaterialized` 分支改 staging → manifest → `os.replace`；
      起手清理残留 `materials.staging-*`；失败删 staging。
- [x] 1.2 新增 `scripts/tests/wf_review/test_materials_atomic.py`：① 正常物化后无 `materials.staging-*`
      残留、`materials/` 完整且 manifest 在包内；② 在 `write_materials` 中注入异常后接口失败、
      `materials/` 不存在、重跑可完整出版；③ 只在 `unmaterialized` 发布（`fixed` 重入不改 `generated_at`）。
- 验证：`-m unittest scripts.tests.wf_review.test_materials_atomic`。

## 2. 材料身份（F1b/F1c/F2c）

- [x] 2.1 `review.materials_identity(manifest)`（唯一实现）。
- [x] 2.2 `report_skeleton` 预填 `materials.identity`；`facts.materials_check` 改为真实 `state`/`fixed`/`identity`。
- [x] 2.3 `report_input_problems(..., materials_identity=None)` 增校验（可选字段，给值即须匹配）。
- [x] 2.4 `import_report`：校验后写 `entry_record["materials"]`；无值时补记当前身份 + `materials_unbound`；
      `--restore` 保留 `previous["materials"]`。
- [x] 2.5 `decide`：本轮 imported 的身份集合必须齐一且等于当前身份，否则 `WF_REVIEW_INVALID`；
      `result.materials` 用绑定身份 + `current` 对账。
- [x] 2.6 两处 drift 出口与 `wf-review` 材料纪律按设计 §1.4 改三段。
- [x] 2.7 测试 `scripts/tests/wf_review/test_materials_identity.py`：身份排除时间戳；骨架带值；
      导入失配拒绝；判定失配拒绝；同内容重出仍放行；`--restore` 保留；老报告 `materials_unbound` 不阻断。
- [x] 2.8 `review-status` 投影 `materials_state`。
- 验证：上述两套 + `test_report_boundary.py` + `test_report_input_single_source.py`。

## 3. 启用前置（F2a/F2b）

- [x] 3.1 抽 `_enable_guards(ctx, host_id)`（Trellis 两段 + `check_platforms`，只读）。
- [x] 3.2 `cmd_enable` 在 `_establish_auto_session` 之前调用；`_rotate_session` 在写前调用并补身份警告事实。
- [x] 3.3 测试 `scripts/tests/test_cli_enable_guards.py`（或就近既有会话测试）：① Trellis 有效 +
      `--new-session` → `WF_FLOW_CONFLICT` 且无新附件/路由；② 平台集合为空 → 两入口都 `WF_IDENTITY_UNRESOLVED`；
      ③ 首次启用被拒后 `task-new` 仍 `WF_NOT_ENABLED`。
- 验证：该套 + `scripts/tests/test_identity_store.py`、`wflib_session` 相关。

## 4. 批准摘要（F3）

- [x] 4.1 `cmd_task_approve` 摘要改必填 + 分开两条错误；同步 `_load_decision` 注释与帮助。
- [x] 4.2 补测试（空摘要拒、错误摘要拒、`--draft` 结果可直接批准）。
- [x] 4.3 机械补齐 12 处 subject-only 夹具的 `object_digest`（用夹具自己的 PRD 摘要）。
- 验证：`scripts/tests/wf_review`、`wf_runtime` 相关；夹具改动逐套跑过。

## 5. 指引（F5a/F5b/F6）

- [x] 5.1 `wf-review-action` 导入示例加 `--round`；`review-import` 错误 facts 加 `undecided_rounds`、`next_` 带轮次。
- [x] 5.2 `wf-bootstrap` 删五类清单留指针。
- [x] 5.3 `wf-continue` 的 `preexisting_in_scope` 行改"先核后问"。
- 验证：`python3 scripts/check-doc-refs.py`、`./scripts/validate-skills.sh`、`test_help_contract.py`
  （`undecided_rounds` 不是旗标，只需帮助文案一致）。

## 6. §1.1 与登记

- [x] 6.1 设计稿 §1.1 两句改写（消费点 / 交人触发点）。
- [x] 6.2 机制稿 §9.2 字段表增 `materials`（报告字段 + 导入记录）、§1.1 只读信息字段补 `reviews.imported[].materials`；
      §9.2「轮次材料固定」段补"报告绑定材料身份、判定比对"。
- [x] 6.3 `COMMAND_HELP` 的 `review-import`/`review-decide` 增 `materials` 与 `undecided_rounds` 口径。
- [x] 6.4 双向回扫登记（无新 § 引用）+ `python3 scripts/validate-wf-design.py` 全绿。

## 7. 收口验证（不提交）

```bash
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
WF_TAGS=review bash scripts/tests/wf_runtime/full/run_all.sh
bash scripts/tests/wf_runtime/full/repro/run.sh --group review --mode green --no-build
python3 scripts/build-wf-release.py --verify --verify-token-parity
python3 scripts/validate-wf-design.py && python3 scripts/check-doc-refs.py && ./scripts/validate-skills.sh
```

全量（`--full --repro green`）在收口前跑一次并如实报告结果；回退注入至少一次（材料身份 +
启用前置各一条），确认断言变红再恢复。`git status` 核对只有本任务路径，`wf-release/` 不变。
提交与收尾等用户同意后再做。

## 风险点 / 回退点

| 点 | 回退方式 |
|---|---|
| 材料 staging 改动（1.1） | 单文件还原 `review.py` 该分支 |
| 报告字段与判定比对（2.x） | 删字段校验 + 删 decide 比对（记录里多出的 `materials` 可留） |
| 启用前置（3.x） | 还原 `cli.py` 两处调用顺序 |
| 批准必填（4.x） | 恢复"非空才比"，夹具补摘要可留 |

## 实际偏差（收口记录）

- 4.3 夹具补齐：绝大多数夹具的 `approve()` 已带摘要；真正空的只有 proposal 类（不属 `task-approve`）。
  r70 的 2b 原本就红（存量：次轮不关上一轮 blocking，pass 的任务级校验过不去），本轮同批修好：
  次轮 `--plan` 关闭 F1。
- 新增的两处小红一并处理：`test_review_material_fixed` 的 mock 改为写 `write_materials` 的目录参数；
  `test_decide_all_blocking` 的 `manifest_digest` 断言改为绑定身份语义。
- `scripts/tests/wf_runtime/full/candidate-audit.json` 的 r70 脚本摘要按当前字节更新（否则
  `test_source_coverage` 的 candidate-verified 计数会掉）。
- `docs/workflows/wf-release/` 按 0.1.8 重建（`build-wf-release.py --version 0.1.8` 生成）；`--verify
  --verify-token-parity` 通过。不建 tag、不提交。
- 节文件 `wf-framework-mechanism.md` §0.1 的设计稿输入摘要按新字节更新并追加本轮说明。

## 第二轮复核（两份外部报告）的处置

- a-P1：`--identity` 参数校验与锚点冲突前移到写盘前（冲突只在续用/显式形态判，建立形态本就接管路由）；
  `_establish_auto_session` 接受预算身份；新增两条"拒绝后零附件"断言。
- a-P2 / b-P2：恢复 `subject` 必须含任务 id（摘要只绑内容，相同字节的两份 PRD 会互相顶用）；
  设计稿 §4.2 早已要求"批准只对当前任务有效"，此前实现比稿松。夹具 subject 统一补任务 id。
- a-P3：`--restore` 同时豁免 drift 拒绝（还原的是历史证据，漂移留给判定如实报）。
- a-P4 / b-P1：`materials` 在导入时**必填**（`--restore` 例外），判定侧保留旧报告的 unbound 容忍；
  `unbound` 进 stale 事实成为有消费点的强度标注；wf-review 补"重抄后要重核受影响结论"。
- a-P5：三处出口改"有备份时放回原字节"（manifest 只有摘要，不放字节）。
- a-P6：核过——首次启用分支会 return，未重复跑；`_rotate_session` 的身份改取附件，顺带解除
  `activation_stale` 死锁（b-P3）：stale 由 enable 续期，两入口都补 `activation_renewed` 事实。
- a-次要：材料身份说明从源码注释移进 `review-decide` 的 `purpose`；`subject` 帮助改成"必须含任务 id"。
- b-P4：`review-status` 的 stale 判据改为"锚点不同"，与导入/判定同源（同锚点换 check_id 仍到位）。
- b-P5：`wf-continue` 补一句——调试裁定由 AI 在授权内判，不是转录人答。
- a-P7：交付纪律登记"材料字节必须可确定性重产"，改 `write_materials` 必须跑同内容重出测试。
- b-P2 的"design/implement 变化仍通过"经核实不成立：`plan.version` 已含三份规划产物的摘要，
  产物一改批准即失效（`compute_plan_version` → `artifact_digests`）。

## 第二轮修正的验证与遗留

- T0 1871 项全绿（43 skip）；全量 `--full --repro green` 59 套件 + 5 流程 + 80 repro 全过（GATE-OK）；
  review repro 组单独复跑 12/12；`build-wf-release --verify --verify-token-parity` 通过。
- 夹具清扫：`subject` 绑定恢复后，全仓 approve 夹具补任务 id（约 40 处 helper/调用点），
  `candidate-audit.json` 的脚本摘要按当前字节刷新（否则 candidate 计数掉）。
- 已知取舍：`materials` 导入必填 + 摘要锁 ⇒ 材料重出后同轮报告作废，出口是"有备份就放回原字节，
  否则重写报告开新一轮"。这是 11-21 人裁 + 本轮 R1 的组合结果，未再放宽。
- 仍未核：跨会话身份适配层；候选审计的**完整重审**要等提交后按 T3 重跑（本轮只刷新了脚本摘要）。

## 第三轮复核（两份外部报告）的处置

- a-1：批准补 `artifacts`（草稿按当时 prd/design/implement 预填，批准与机械修订都核当前值；
  旧决定不带此键按 PRD 兼容）。修掉"人答复后产物再变、旧答复照样批准新方案"。
- a-2 / b-P1：`_rotate_session` 的续期移到终态/写权核对之后——被拒的轮换不再顺手改启用状态；
  新增"拒绝后不续期"断言。轮换的首次启用子分支补 identity/trellis facts 与同一份警告。
- a-3：`lint` 与导入共用 `materials` 必填判据；`review-context` 对 done 报告的回显带
  `materials_check.identity`，旧报告知道往哪补。
- a-4：`review-status` 与 `check_next_hint` 都识别"材料身份已变"：不再让 AI 等同轮重交，
  直接给"放回原字节 / 换一轮"。
- a-5：裁定改**覆盖**语义——一条裁定覆盖它之前的所有倍数（待决项给 `covers` 区间），
  计数与精确 subject 留痕不变；机制稿 §1.3/§11.2 与 wf-diagnosing-bugs 同步。
- b-P2：`restored` 标记进导入记录；drift 对"本轮报告全部来自 restore"的轮次降级为事实
  （结论按记录身份成立），其余仍是硬拒。
- b-P3：状态页区分 `stale_cause`（report / anchor / materials / restored-historical），
  restore 保留旧身份不再与"材料真被换"混为一谈。
- b-次要2：交付纪律登记 0.1.8 的一次性迁移成本（旧报告首次导入需按身份补一行）。
- b-次要1：`cmd_enable` pending 分支的死赋值已去；establish 子分支的结果与自述面已补齐。

验证：T0 1880 全绿；全量 144 单元（59 套件 + 5 流程 + 80 repro）全过 GATE-OK；review repro 组 12/12；
`--verify --verify-token-parity` 通过；设计闸门 100%/100%、skills、doc-refs 全绿；
r79 的 D04 按新语义改写并刷新其审计摘要。

## 第四轮复核（两份外部报告）的处置

- a-P1 / b-P2：`artifact_drift` 由"只核声明路径"改为**双向**——声明后产物被改/被删/新出现
  都算漂移（新增项 `declared: null`），help 与机制稿同步；新增"草稿后补写产物被拒"用例。
  复杂任务不再能用"草稿时没有、批准时才有"的方案开工。
- a-P2 / b-P1：restored 条目的身份来自记录，`review_report_problems` 不再拿它与现场比；
  判定侧 drift 容忍面从"全部 restored"扩到"restored 或纯旧记录（无身份）"；status 文案去掉
  "仍可判/不可判"的分叉，review-status 与 check_next_hint 对 restored 一律给"可直接判定"。
- b-次要1：旧记录无身份的轮次同样豁免 drift（`history_round`），事实走 `materials_state`。
- b-次要2：`check_next_hint` 的兜底改为追加"材料身份没核成，先看 review-status"，不再静默当作未失配。

验证：T0 1883 全绿；全量 144 单元全过 GATE-OK；review repro 组 12/12；`--verify` 通过；
设计闸门 100%/100%、skills、doc-refs 全绿。

## 第五轮复核（两份外部报告）的处置

- a-P1 / b-次要1：`artifacts` 由"可选"改**必填且非空**（正式批准与机械修订都拒缺），
  `artifact_drift` 双侧核对早已在，空 dict 不再等于"没声明"；新的失败 exit 直接给 expected_artifacts。
  夹具统一走 `wfdrive.plan_artifacts` / 在 `dec()` 里补，约为 40 处；`f1_*`/`p5_*`/`r87` 改用它算全量产物。
- b-P1：restored 豁免由"条目级"改"整轮级"——存在非还原条目并存且身份不同时，`materials_stale`
  照旧阻断并给"把它也 restore / 开新一轮"出口；全还原轮才降为事实。新增混合轮用例。
  判定侧 drift 容忍面同批扩到"restored 或纯旧记录"。
- b-P2：`check_next_hint` 改读 `materials_identity_state`：drift 时不再指引先去 `review-context`，
  直接给"还原记录可直接判定 / 要可核身份先放回原字节"。
- b-次要2：drift 的 `materials_note` 改"按记录给出的身份成立（纯旧记录无身份见 unbound）"。

验证：T0 1883 全绿；全量 144 单元全过 GATE-OK；review repro 组 12/12；`--verify` 通过；
r87 增加开工/批准两条断言（expect 11→13）并刷新审计摘要；设计闸门 100%/100%、skills、doc-refs 全绿。

## 第六轮复核（两份外部报告）的处置

- a-P1：机械修订草稿条目补 `artifacts`（与 approve 条目同源），通道不再自我锁死；补"草稿→填写→执行"贯通用例。
- a-P2：三处口径统一为"必填（0.1.8 起）"：help 的 inputs、机制稿 Decision 契约都写明旧决定会被拒、按
  `expected_artifacts` 补即可；`_load_decision` 的 field_notes 同步。
- b-P1：`report_input_problems` 增 `materials_restored`（import 按 `--restore`、判定按 entry 标记逐条传）：
  还原报告自报的旧身份不再被输入校验当 `report_invalid` 挡掉；跨条目的一致性仍由混合基线判据管。
- a-次要2：两条 hint（review-status / check_next_hint）都识别混合轮，给"把正常条目也 restore 或开新一轮"。
- a-次要1 经核不成立：`_mechanical_revision` 里 digest → artifacts → parse 的顺序本来就是 artifacts 先于模板解析。

验证：T0 1884 全绿；全量 144 单元全过 GATE-OK；review repro 组 12/12；`--verify` 通过；
设计闸门 100%/100%、skills、doc-refs 全绿；新增用例：机械修订贯通、还原报告带旧身份仍可判。

## 第七轮复核（两份外部报告）的处置

- a-P1：写入时核裁定倍数不得超过已跨过倍数（同一决定文件里的声明先计入再核）——未来倍数不再
  提前覆盖尚未发生的失败；机制稿 §1.3 补该条，新增"倍数 99 被拒"用例。
- b-P1：混合基线判据收敛为 `review.round_materials_basis` 单一实现——decide 阻断、
  `check_next_hint`、`review-status` 三处都读它；hint 的分歧场景（restored + 未失配的正常条目）
  现在与阻断一致。
- b-P2：补混合场景贯通用例（decide 阻断 + hint 文案），两份实现分叉时会变红。
- b-次要1：`_load_decision` 的 field_notes 补 `artifacts` 说明。
- b-次要2：restore 不再整体过滤 materials check（格式问题照报），身份相等由 `materials_restored` 放宽。
- 修正随动的 `test_debug_declaration_idempotent` 夹具（裁定倍数按新的"已跨过"校验调整）。

验证：T0 1887 全绿；全量 144 单元全过 GATE-OK；review repro 组 12/12；`--verify`；
设计闸门 100%/100%、skills、doc-refs 全绿。

## 版本号回退到 0.0.1 与“只由人推进”规则

- `docs/workflows/wf/README.md` 的目标版本改 `0.0.1`，并写明版本号从 0.1.x 回退、只有人主动要求才改；
  升级通道示例改 `wf-v0.0.1`（tag 由人建）。
- 机制稿、help、review.py 注释里“0.1.8 起/之前”的表述改为“0.0.1 起 / 此前版本”，避免版本号回退后
  出现倒挂表述。
- `AGENTS.md` 增长期规则：wf 版本号只由人推进，提交/轮次/复核都不自动加号。
- 发行树按 `--version 0.0.1` 重建；`--verify` 通过；`verify-wf-release.py` 显示 `tag_exists` 待人工建 tag
  （预期，不代建）。
