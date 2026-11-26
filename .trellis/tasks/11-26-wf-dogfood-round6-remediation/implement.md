# 执行计划：wf 六轮 dogfood 修正

> 设计见 [design.md](./design.md)，验收见 [prd.md](./prd.md)。簇与簇之间除 F1→F2 的顺序外相互独立，可按簇回退。
> 解释器统一 `/softwares/python/bin/python3`；用例默认带 `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache`（避免 pyc 写进源树）。

## 0. 前置核对（只读，不写业务）

- [ ] 0.1 `git status --porcelain` 为空（或记录既有未提交改动并保留）；`python3 ./.trellis/scripts/get_context.py` 确认无其它活动任务抢写。
- [ ] 0.2 记录基线：`PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t . 2>&1 | tail -20`（记录 failures/errors 是否全为存量）。
- [ ] 0.3 记录基线 repro：`bash scripts/tests/wf_runtime/full/run_all.sh --representative`（失败项与原因在 `implement.md` 末尾「基线偏差」登记，不与本轮改动混淆）。

## 1. 簇 F1：任务写入口归属唯一化（P0，design §3-F1）

- [ ] 1.1 `tasks.write_scope(ctx, task_id)` 新增（唯一实现）；`_require_binding` 改为它的薄壳并保留原错误码与事实形状。
- [ ] 1.2 `tasks.require_held_for(ctx, task_id)` 新增：锁内 `ctx.require_held()` + holder scope 复核（task 面须等于该任务；run 面须 `run_id`+未终态+游标指向）。
- [ ] 1.3 接入 17 处写入口（`tasks.py` 的 approve/start/replan/pause/resume/curate/check/knowledge/retrospect/attribute/abandon/dep/archive/baseline-apply/spec-update/rework` + `check` 的两段锁）。
- [ ] 1.4 `bind_task_for_write` 改为 `write_scope` + `require_held()` 组合，保持返回三元组形状（决策类入口与 review 不破）。
- [ ] 1.5 `_release_after_archive` 在 run scope 不释放写权；`archive` 的 `next_` 按 scope 分叉；`stop_work` 对 run scope 给「用 task-pause / run pause」出口。
- [ ] 1.6 用例：`scripts/tests/wf_runtime/test_instance_task_write.py`（新）——
  - 正例：run create → advance 建任务 → approve → start → check(pass) → archive → advance 记 satisfied；
  - 负例：错任务、游标不指向、实例已终态、他人持权、task 绑定任务但实例在途（保持原拒绝）。
- [ ] 1.7 更新既有用例期望：`test_run_advance.py::*`、`full/repro/run-advance-creates-task.py` 追加「建出的任务可被批准」的正向断言。
- [ ] 1.8 验证：`python3 -m unittest scripts.tests.wf_runtime.test_instance_task_write scripts.tests.wf_runtime.test_run_advance scripts.tests.wf_runtime.test_binding_matrix -v`（后者若不存在以 `test_enable_guards_source`/`test_ready_runs` 替代）+ repro `run-advance-creates-task`。
- **回退点 R1**：1.1–1.5 全部在 `tasks.py`/`check.py` 的调用面，出问题按簇回退，其他簇不受影响。

## 2. 簇 F2：游标按步骤事实推进（P0，design §3-F2）

- [ ] 2.1 `runs.advance` ①段分支重写（task 映射存在 / 无映射但有 satisfied|skipped 结果 / 其余仍 `WF_HISTORY_UNRESOLVED`）。
- [ ] 2.2 异常归档出口改实例层动作 + `facts.exits`。
- [ ] 2.3 `_next_step`：跳过 `step_results` 已有步骤、删除 `creation` 形参、docstring 对齐；调用点同步。
- [ ] 2.4 用例：`scripts/tests/wf_runtime/full/repro/run-advance-after-human-step.py`（新）——
  - 人判步骤记录后 advance 推进到下一步（不报 HISTORY_UNRESOLVED）；
  - 略过步骤记录后 advance 推进；
  - 注入「游标 step 无映射且无结果」→ 仍 `WF_HISTORY_UNRESOLVED`；
  - 异常归档任务后再 advance → `WF_SEMANTIC_DECISION` 且出口含 `run terminate`。
- [ ] 2.5 验证：`bash scripts/tests/wf_runtime/full/run_all.sh --subset`（`WF_SUITES=run_core`，名以 `plan.py --list` 为准）+ 新 repro 单独跑。
- **回退点 R2**：仅 `runs.py::advance/_next_step`。

## 3. 簇 F8：实例快照单读（P1，design §3-F8）

- [ ] 3.1 `runs._fixed_snapshot(ctx, run)` 新增（存在性 + digest + 解析一次），`advance` 改为消费它（行为不变）。
- [ ] 3.2 `finish` / `_terminate_preview` / `terminate` 改为消费它；`terminate` 的第二次 `open` 删除。
- [ ] 3.3 用例：`scripts/tests/wf_runtime/test_run_snapshot_missing.py`（新）——删快照后 finish/preview/terminate 均 `WF_HISTORY_UNRESOLVED`，且 terminate 不产生任何任务处置写入。
- [ ] 3.4 验证：`python3 -m unittest scripts.tests.wf_runtime.test_run_snapshot_missing scripts.tests.wf_runtime.test_run_locate -v`。
- **回退点 R3**：`runs.py` 的四处快照读取。

## 4. 簇 F3：Check 定稿合并（P1，design §3-F3）

- [ ] 4.1 `check` 准备段输出可重放的调试声明输入（`decisions` 已在 state 里，重放即可）。
- [ ] 4.2 `cmd_task_check` ③段：重读记录 → 重放 debug 输入 → 身份比对（status/phase/paused/suspended/plan_version/entry digest/acceptance digest/上一版 check id）→ 不一致 `WF_CHECK_STALE`。
- [ ] 4.3 用例：`scripts/tests/wf_runtime/test_check_lock_window.py` 扩展——「Check 锁外期间同会话 task-pause」→ 结果不覆盖 paused，返 `WF_CHECK_STALE` 且记录仍 paused；「锁外无变化」→ 正常 pass。
- [ ] 4.4 验证：`python3 -m unittest scripts.tests.wf_runtime.test_check_lock_window scripts.tests.wf_runtime.test_check_next_route -v`。
- **回退点 R4**：`tasks.py::cmd_task_check` ③段 + `check.py` 的 state 形状。

## 5. 簇 F5：TDD 证据身份与适用性（P1，design §3-F5）

- [ ] 5.1 `check.tdd_evidence_problem` 增加同验证项判定；错误事实给 `verification_id` 与可用红/绿引用。
- [ ] 5.2 `tasks.validate_plan_block` 接受可选 `tdd_applicability ∈ {code,docs,investigation}`；`task-approve --draft` 与正式批准 facts 回显。
- [ ] 5.3 `run_check_finish`：`tdd_applicability != "code"` 时不要求红绿，写 `check.tdd_applicability`，并按验收证据判 pass；`gates.verify_step("task.tdd-verified")` 按批准声明放行并给事实。
- [ ] 5.4 用例：`scripts/tests/wf_runtime/full/repro/tdd-evidence-identity.py`（新）+ `test_task_check_draft.py` 扩展——
  - 跨验证项拼凑被拒；同验证项红→绿通过；
  - `tdd_applicability=docs` + 命令验收证据 → pass；未声明（缺省 code）→ 仍要求红绿。
- [ ] 5.5 同步 `payload/workflows/task-flow.md` 的 `task.tdd-verified` 动作句与 `skills/wf-tdd/SKILL.md` 的判据位（适用性怎么选、谁签）。
- **回退点 R5**：`check.py::tdd_evidence_problem/run_check_finish`、`gates.py:782` 区段、plan 块校验。

## 6. 簇 F4：复杂度条件事实化（P1，design §3-F4）

- [ ] 6.1 `scope.expansion_condition` 改 `subsumes` 判据（含 facts）。
- [ ] 6.2 `tasks._complexity_proposal` 的 acceptance 条件改用 `acceptance_digest` 比较（保留 id 集合差异作为 facts）。
- [ ] 6.3 `scope.contract_surface_condition` 的 `AGENTS.md` 分支改托管块内容比较（`git show HEAD:` + 当前文件截块；缺一端保守 true）。
- [ ] 6.4 用例：`scripts/tests/wf_runtime/test_complexity_conditions.py`（新）——`a.py→**` 判扩面、`**→a.py` 判内部、同 id 改判据判验收变化、AGENTS.md 块外改动不判契约面、块内改动判契约面。
- [ ] 6.5 验证：`python3 -m unittest scripts.tests.wf_runtime.test_complexity_conditions scripts.tests.wf_runtime.full.repro.complexity-human-carrier -v`（或对应 repro）。
- **回退点 R6**：`scope.py` 两函数 + `tasks._complexity_proposal`。

## 7. 簇 F6 + F7（P1，design §3-F6/F7）

- [ ] 7.1 `work_satisfied_fact` 零触碰面分支改「已批准验收项即成立」，出口去自循环。
- [ ] 7.2 `decisions` 域新增 `prepare_definition` 取值；`runs.prepare` 接受 `--authorization`（六键 + scope 覆盖）与 `--authorization-draft`；准备记录写 `source=decision` + `scope_digest`；同范围复用。
- [ ] 7.3 `_preparation_problems` 增授权核验；`run create --creation-draft --id` 生成骨架。
- [ ] 7.4 同步 `payload/workflows/instance-flow.md` 的 `control.definition.prepare` 动作/出口句、`skills/wf-start/SKILL.md` 的定义准备顺序、`wf-*` 相关命令 help。
- [ ] 7.5 用例：`scripts/tests/wf_runtime/test_prepare_authorization.py`（新）+ `test_run_create.py` 扩展——无授权拒、授权覆盖不足拒、同范围复跑复用、`create` 核到授权、creation 骨架四字段齐全且 digest 与 validate 一致。
- **回退点 R7**：`runs.prepare/create` + `tasks.work_satisfied_fact`。

## 8. 簇 F9 + F10 + F11（P1/P2，design §3-F9/F10/F11）

- [ ] 8.1 `cmd_gate` 接受 `after_archive`。
- [ ] 8.2 `validate_usage` 未注册 flag 不再吞值。
- [ ] 8.3 `_human_answer` 整词匹配。
- [ ] 8.4 `projection._adjudicated` 精确提交号（记录时 `git rev-parse --verify` 归一）。
- [ ] 8.5 `session.state_of_root` sid 分支复用 l1 判定。
- [ ] 8.6 `_publish_materials` 幂等复用；`_main_review_revision_problems` 抽公共实现供两处消费。
- [ ] 8.7 死代码清理（`if True:`、`and False`、`vendor_assets` 重复、`judgments` 重复导入、`check.run_check` 删除）。
- [ ] 8.8 用例：`test_help_contract.py`（gate due）、`test_decision_domains.py` 或新增 `test_usage_flags.py`、`test_run_advance.py`（human answer 整词）、`test_read_attribution.py`（projection）、`test_w3_session_identity.py`（sid 死亡）、`test_review_readiness.py`（并发物化）、`test_register_close.py`（复核保留规则一致）。
- [ ] 8.9 验证：上述单测 + `python3 -m unittest discover -s scripts/tests -t . `（全量单测）。
- **回退点 R8**：逐小项独立，按需单独回退。

## 9. 簇 F12：出口、指引与文档（design §3-F12）

- [ ] 9.1 `runs.pause` 回显 + docstring；异常归档出口（已含在 2.2）。
- [ ] 9.2 用户可见文案 5 处 authoring 引用改可达出口。
- [ ] 9.3 发行 skills 13 处 authoring 指针改可达指针/删除；`wf-continue` 路由表加「命令形态以 `wf help` 为准」一句。
- [ ] 9.4 设计稿 §1.1：默认规则、人签封闭清单、指令分工（入口用法单一来源）三处更新；同批复查 `.index.md` 与 `sources.md` 的登记（`scripts/validate-wf-design.py` 必须通过）。
- [ ] 9.5 验证：`./scripts/validate-skills.sh`、`/softwares/python/bin/python3 scripts/validate-wf-design.py`、`/softwares/python/bin/python3 scripts/check-doc-refs.py`（若适用）。
- **回退点 R9**：文档与 skill 文本层，独立回退。

## 10. 收尾（人审后执行）

- [ ] 10.1 全量验证：`PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .` + `bash scripts/tests/wf_runtime/full/run_all.sh --representative --repro green`（或按 `plan.py --changed` 建议的本轮相关套件）。
- [ ] 10.2 复核 diff：`git diff --stat` 与本计划逐条对齐，无顺手重构、无无关文档改动。
- [ ] 10.3 登记 `analysis/round-history.md` 一轮叙述（只在人同意后提交批次内做）。
- [ ] 10.4 **等人口头同意**后提交（`task.py` Phase 3.4），再执行 finish-work；此前不提交、不推送。

## 基线与偏差登记

- 基线单测（改动前）：`python3 -m unittest discover -s scripts/tests -t .` → **2084 用例 OK**（43 skipped，exit 0）。
- 基线 representative repro（改动前）：`run_all.sh --representative` → **57 执行单元 / repro 49/49 green**，exit 0。
- 完成后单测：**2086 用例 OK**（43 skipped；净 +2 个用例：复杂度条件 12 条 + 新 repro 覆盖在 full 侧）。
- 完成后全量运行期：`run_all.sh --full` → **152 执行单元（套件 59 / 流程 5 / repro 88）**，repro 88/88 green。

### 偏差与登记（逐条，不并入结论）

1. **`r17r24_tests` / `r62_tests` / `r65_tests` 的字节改动**：三条既有套件按新契约改写（R22 红绿证据、
   调查成果口径）。`candidate-audit.json` 仍绑定它们的旧字节，本机无法重跑增量审计（`--only` 要求同身份旧报告；
   全量审计被 `r72/r86/r87` 与安装收据拒发），故在 `test_source_coverage.py` 显式登记为
   `DECLARED_UNVERIFIED`（`declared-candidate-unverified`），**发行批次必须重跑候选审计**。
   不伪造审计摘要、不改写旧报告。
2. **`--full` 下 `p5_v1`/`r90_tests` 的偶发 FAIL**：单独运行与两两组合均绿；机制是并行套件导入
   `payload/lib` 时生成 `__pycache__`，使 `wf-dev-deploy` 的「落点内容与本发行一致」核验看到额外文件。
   清理源树 pyc 后复跑 `--full` 为绿（见上方结论）。这是既有的环境性抖动，不是本轮改动引入。
3. **`docs/workflows/wf-release` 未重建**：发行树是生成物，随发行批次重建（版本推进由人发起，本轮不改版本）。
4. **二轮外部审查（同日）的修正与验证**：
   - 修回回归 A1（`--workspace-exclusion` 声明在定稿段重放）；新增 repro `check-exclusion-persists`（green+red）。
   - 机械修订等价域纳入验证声明与 `tdd_applicability`，验证声明摘要收敛为 `fingerprint.verifications_digest`
     单实现（批准入口与门禁投影共用）；新增 repro `mechanical-revision-equivalence`（red 注入点落在共享摘要实现，
     单点关闭两处比较才能证伪）。
   - 实例创建补人签（`run create --authorization` + `--authorization-draft`）；准备通道限未绑定会话；
     创建时重算准备范围摘要；`r71_tests` 的 fail 断言改 `WF_REVIEW_FAILED`。
   - TDD 红绿要求同 `verification_digest`；`review-decide` 的"A 未到齐先于人数"守卫覆盖两种导入形态；
     草稿旗标与真实输入同给即拒（`DRAFT_CONFLICTS` + dispatch 一处核）；`_open_lock` 删除
     （`support_report`/`verify_holder` 经核有调用方，属误判，保留）。
   - 新增单测 `test_sixth_round_guards.py`（草稿冲突 + TDD 关联）；help 契约新增两条自检
     （登记表重复键、帮助旗标必须被用法校验放行——后者正是本轮重复键事故的来源）。
   - 验证：单测 **2096 OK**（43 skipped）；`run_all.sh --full` **155 单元 fail=0 / GATE-OK**（repro 91）；
     设计稿机检、skills 校验、`build_required_steps`（41 步，无问题）全绿。
   - 候选审计待重跑集合扩到 `r71_tests`（同前三条套件，`DECLARED_UNVERIFIED` 显式登记）。
   - 三轮外部审查（同日）的修正：① 准备通道补上**限定准备写权**（`scope.object=preparation`）与收口
     （`definition prepare --end` 处置未提交编辑后释放；`run create` 作为天然收口自动释放；已结束记录仍可用于创建）；
     ② TDD 红绿在历史红运行缺 `verification_digest` 时 fail-closed；③ `wf-start` 路由顺序与详细步骤统一；
     ④ skill 的人工验收/直接验收说明改为「判断 + 指针」（形状只在 `wf help`）；⑤ `task-knowledge` 的草稿互斥
     对象改回真实配对并支持布尔冲突项；⑥ `stop --preview` 实例出口同口径；⑦ repro 直跑守卫（缺
     `WF_RELEASE_TREE` 直接前置失败，避免用旧发行树产出空洞 green）。用例 `prepare-authorization` 扩到
     8 段（含准备写权、未处置编辑拒结束、结束释放、结束记录仍可创建），`test_sixth_round_guards` 增
     `task-knowledge` 配对与历史红运行两条。⑧ **red 面全量复核**：`--full` 只跑 green，单独跑
     `run.sh --mode red` 发现三条注入已 stale（`review-count-reject` 的 `eligibility["problems"]`、
     `auto-identity-zero-input` 的 `if key is None:`、`reinstall-preserves-data` 的 install.py 两行被注释隔断）
     与一条目标判定错位（`complexity-bootstrap-exempt` 把 `WF_SEMANTIC_DECISION` 当前置失败）；四处已修，
     现 **91/91 red 全绿**（此前这几条的 red 结论不成立，等于修复没有可证伪覆盖）。
   - 四轮外部审查（同日）的修正：① 授权解析前移到取写权之前（缺授权不再先占住写权）；
     ② `prepare --end` 的释放条件改按事实核（范围内未提交路径必须已提交或已移走，`--disposition`
     只是留痕且必须与事实一致）；③ 结束某定义只释放该定义的 preparation 写权（跨定义不误释放，
     新增单测 `test_preparation_lifecycle`）；④ TDD 断代升级成本写进 round-history（在途任务首次 Check
     会报「红运行早于验证身份」，按当前定义重跑红即恢复）；⑤ `wf-continue` 的定义编辑路由区分
     已绑定/未绑定会话；⑥ 两个环境相关用例改为可诊断（异解释器不变量在单解释器机器上 skip 并说明；
     模板缓存取键改为带目录快照的可读失败，替掉裸 `StopIteration`）。
     验证：单测 **2101 OK**；`--full` 155 单元 fail=0 GATE-OK；`run.sh --mode red` **91/91**。
   - 五轮外部审查（同日）的修正：① `prepare --end` 改「先释放写权、后写 ended_at」，已结束分支自愈补释放
     （终态标记先落会让重试提前返回、写权永久留在无 task/run 绑定的会话里）；② 补**保留草稿**出路
     （`action=retain` + risk + pending，记范围/路径/内容摘要/暂存事实后释放）；③ "提交定义"归属到人
     （准备通道不授权提交），出口/skill/instance-flow 同批；④ `test_template_cache` 槽位按实现现算，
     替掉硬编码 py3.14 base64 槽位（3.13 机器上 9 个失败的真因）。
   - 六轮外部审查（同日）的修正：① `run advance` 末步结案/创建下一步两处写回 `step_results`（`instance-task-phases`
     扩了落盘断言与 `run finish`→`persist_pending`→补授权续做→再次拒绝的完整链路）；② `run finish`/`run terminate`
     的 `persist_pending` 重入续做（`_pending_persist` 单实现）；③ 准备通道拒绝 `recovering` 写权态；`retained_wip`
     补消费侧（`retained_preparation_wip` + `wip_blockers` 指名归属 + 重新准备关闭保留并记 drift）；④ 复杂度条件②
     的 `AGENTS.md` 判定与触碰面顺序无关、给 `basis` 与 `contract_changes` 声明入口。新增单测
     `test_contract_surface_order`（4 条）与 `test_preparation_lifecycle` 扩到 10 条。
   - 同日**自审查**（不依赖外部报告，按"写了不核 / 形状不一 / 顺序相关 / 恒真自报 / 出口不通"五类逐项核）：
     ① `run terminate` 完成动作时把 `steps` 从步骤名改写成 `{"id","state"}`（同一字段两种形状）——已停；
     ② 反过来统一步骤形状为 `{"id","state"}`：`actions.new_action` 直接产出、`complete()` 把步骤一起标 done，
     删除 `run.create`/`run.bind`/`task.create`/`run.terminate` 四处手工改写；`step_done` 按 id 推进；
     ③ `run terminate` 的 `persist_pending` 重入按主路径归一 `decision_ref`（数组形态此前取不到授权）；
     ④ 末步结案只写 `step_results`，不再顺手清空 `cursor.task_id`（写权释放前置与 current-task 投影都读它）；
     ⑤ 去掉 `end_disposition.verified` 恒真自报；`retention_closed` 补消费点（prepare facts 报 drifted）；
     ⑥ `--end` 的 `retain` 声明若路径没有未提交改动 → 按声明与事实不符拒绝（新增单测）。
     ⑦ 步骤形状不变量加单测 `test_action_steps_shape`（5 条：new_action 产出形态、按 id 推进、
     未知步骤拒、complete 全部标 done、旧记录（纯名字）仍可推进）。
     验证：单测 **2119 OK**；`--full` 155 单元 fail=0 GATE-OK；red **91/91**；设计与 skills 机检通过。
   - 追加修正（审查收尾时新发现的两处同源问题）：① `review-decide` 的"材料未到齐"守卫会挡住
     "槽位确实不可用"的合法降级——现在**人已签单 reviewer 残余风险接受**时不阻断（缺的槽位按不可用处理，
     走同一降级分支，`result.degraded` 也如实记 `single-provider`，此前只有 facts 里有、result 里没有）；
     ② 机械修订的验证声明摘要在批准入口与门禁投影各写了一套 `H("wf-plan-verifications-v1", …)`/
     `H("wf-verifications-v1", …)`，收敛为 `fingerprint.verifications_digest` 单实现。