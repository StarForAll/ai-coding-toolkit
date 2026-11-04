# 任务流程（task-flow）

> 单个任务的四阶段：Plan → Execute → Check → Finish。步骤标 `[required · once|repeatable]`，
> required 不允许附理由跳过；once 只在产物仍有效且完成判据满足时复用。
> 本文件是发行资产（随升级覆盖，本地修改按偏离保护）；enforcement 行登记每步的执行/检查面。

## 一、任务级 required 步骤

### task.plan-approved [required · once]

- 时点：Plan 末（before_execute）
- enforcement: `wflib/tasks.py::cmd_task_approve`（处理器）＋ `wflib/gates.py::verify_step`（核验）
- 动作：人批准当前规划的机读块、复杂度与 TDD 取值；入口提取 PRD 的 `plan-q-<n>` 问题全集并核批答覆盖。
- 出口：版本不符、批准缺失或问题未答 → `WF_APPROVAL_MISSING` / `WF_SEMANTIC_DECISION`，回 Plan 重批。

### task.spec-loaded [required · repeatable]

- 时点：开工与 Check、Finish 前（before_execute）
- enforcement: `wflib/cli.py::cmd_spec`（写本会话读取侧车）＋ `wflib/tasks.py::spec_loaded_fact`（核验全文与版本）
- 动作：按策展清单逐文件读取正文；日志/摘要不算完整读取。
- 出口：正文未完整读取或哈希不符 → `WF_SPEC_INCOMPLETE`，分批读全后重试；换会话必须重读。

### task.work-satisfied [required · once]

- 时点：进入 Check 前（before_check）
- enforcement: `wflib/tasks.py::work_satisfied_fact`（核验）＋ `cmd_task_check` 在同一 action 内写 completed 回执
- 动作：批准范围要求的产物与必需用户动作已实际完成；纯调查须有可观察成果。
- 出口：交付物缺失或用户动作未答 → `WF_CHECK_FAILED` / `WF_SEMANTIC_DECISION`。

### task.check-passed [required · repeatable]

- 时点：归档前（before_archive）
- enforcement: `wflib/check.py::run_check`（执行）＋ `wflib/gates.py::verify_step`（锚点核验）
- 动作：固定五步：范围核对 → 验证就绪 → 实际执行 → 双轴内部审查 → 写结果与指纹。
- 出口：范围越界 `WF_SCOPE_VIOLATION`；检查失败 `WF_CHECK_FAILED`；对象变化 `WF_CHECK_STALE`。

### task.tdd-verified [required · repeatable]

- 时点：归档前（before_archive，仅 TDD 开启时适用）
- enforcement: `wflib/check.py::run_check` 的 `tdd_evidence` 核验
- 动作：对同一真实行为有红→绿证据；文档类对象以已批准的适用性与独立可观察验证代替。
- 出口：开关开启而缺证据 → `WF_CHECK_FAILED`，不得以其余检查通过顶替。

### task.review-passed [required · repeatable]

- 时点：归档前（before_archive，仅复杂任务适用）
- enforcement: `wflib/review.py::decide`（判定）＋ `wflib/gates.py::verify_step`（核验结果与当前 check 绑定）
- 动作：当前对象由两个与实施 CLI 不同、彼此也不同的审查 CLI 实际审查通过；锚点与当前 Check 一致。
- 出口：报告缺失/身份或人数不合格/锚点失配 → `WF_REVIEW_INVALID`；环境不足 → `WF_REVIEW_UNAVAILABLE`。

### task.knowledge-disposed [required · once]

- 时点：归档前（before_archive）
- enforcement: `wflib/tasks.py::cmd_task_knowledge`（写入）＋ `wflib/gates.py::verify_step`（核验）
- 动作：知识处置留痕：`no-update` 或 `updated`；curation 显式存在（允许为空数组）。
- 出口：缺处置记录 → `WF_SEMANTIC_DECISION`；字段缺失 → `WF_RECORD_INVALID`。

### task.retrospective-done [required · once]

- 时点：归档前（before_archive，仅存在触发事实时适用）
- enforcement: `wflib/tasks.py::cmd_task_retrospect`（写入）＋ `wflib/gates.py::retrospective_triggers`（触发集合重建）
- 动作：复盘结论覆盖当前触发集合（返工、审查失败、已确认的重复调试）。
- 出口：触发事实未被覆盖 → `WF_SEMANTIC_DECISION`；复盘后新增事实形成新期次。

### task.changes-persisted [required · repeatable]

- 时点：归档前（before_archive）
- enforcement: `wflib/tasks.py::changes_persisted_fact`（核验）＋ `cmd_archive` 的授权提交
- 动作：本任务交付按授权提交，工作区无本任务未处理改动；外来改动未被捎带。
- 出口：无授权 `WF_COMMIT_NOT_AUTHORIZED`；提交失败 `WF_PERSISTENCE_FAILED`；WIP 未处置 `WF_WIP_UNRESOLVED`。

### task.archived [required · once]

- 时点：归档后（after_archive）
- enforcement: `wflib/tasks.py::cmd_archive` 的提交后只读后置派生
- 动作：归档终态、目录移动与归档提交可核；不要求也不追加回执行记录。
- 出口：不可核 → `WF_PERSISTENCE_FAILED`；只报告事实，不重启已归档任务。

## 二、控制步骤（scope=control，due=operation_end）

### control.task.create [required · repeatable]

- 时点：task-new 动作结束
- enforcement: `wflib/tasks.py::cmd_task_new`（writer 主记录单一父 action）
- 动作：创建任务规划记录：目录防撞、写记录、首次绑定与写权获取成组完成。
- 出口：目标占用 → `WF_TARGET_COLLISION`；记录不可解析 → `WF_RECORD_INVALID`。

### control.task.transition [required · repeatable]

- 时点：每次状态/阶段迁移结束
- enforcement: `wflib/tasks.py::cmd_task_start` / `cmd_task_replan` / `cmd_task_resume`
- 动作：迁移到 Execute 或 Plan；首次开工写 `entry_snapshot` 与 `baseline_head`，再入保留原基线。
- 出口：批准缺失 `WF_APPROVAL_MISSING`；门禁缺项按其码返回；越界 `WF_SCOPE_VIOLATION`。

### control.task.attribute [required · repeatable]

- 时点：归属裁决动作结束
- enforcement: `wflib/tasks.py::cmd_task_attribute`
- 动作：人把未归属提交裁决给本任务；一个提交至多归属一个任务。
- 出口：提交不存在 → `WF_HISTORY_UNRESOLVED`；trailer 冲突 → `WF_SEMANTIC_DECISION`。

### control.baseline.apply [required · repeatable]

- 时点：基线/配置成组应用结束
- enforcement: `wflib/tasks.py::cmd_baseline_apply`
- 动作：按人审提案成组写活文件与配置；应用后重新核验检查有效性。
- 出口：提案缺项 → `WF_SEMANTIC_DECISION`；路径越界 → `WF_PATH_INVALID` / `WF_SCOPE_UNRESOLVED`。

### control.task.retrospect [required · repeatable]

- 时点：复盘记录结束
- enforcement: `wflib/tasks.py::cmd_task_retrospect`（同一 action 写 `task.retrospective` 与 completed 回执）
- 动作：记录触发事实引用、结论与是否必需；可选复盘记 `required=false`，不进入门禁。
- 出口：结论缺失 → `WF_SEMANTIC_DECISION`。

### control.task.check [required · repeatable]

- 时点：Check 动作结束
- enforcement: `wflib/tasks.py::cmd_task_check`（五步由 `wflib/check.py::run_check` 执行）
- 动作：写检查记录、指纹与回执；pass 时阶段进入 Finish。
- 出口：五步任一失败按其码返回，不写可 pass 的结果。

### control.task.pause [required · repeatable]

- 时点：暂停动作结束
- enforcement: `wflib/tasks.py::cmd_task_pause`
- 动作：记暂停与待处理原因；不改变绑定、不释放写权。
- 出口：未持写权 → `WF_WRITER_BUSY`；代次不符 → `WF_GENERATION_STALE`。

### control.session.stop [required · repeatable]

- 时点：收工动作结束
- enforcement: `wflib/tasks.py::stop_work`
- 动作：人给一个去向（commit/keep/reverse/transfer）后记录真实 WIP、暂停并释放写权。
- 出口：去向未落实 → `WF_WORKSPACE_UNRESOLVED`；无提交授权 → `WF_COMMIT_NOT_AUTHORIZED`。

### control.task.archive [required · repeatable]

- 时点：归档动作结束（含提交步骤）
- enforcement: `wflib/tasks.py::cmd_archive`
- 动作：预检 → 写终态 → 移动目录 → 授权提交 → 只读核对；`persist_pending` 表示提交尚未完成。
- 出口：门禁未过按其码返回；碰撞 `WF_TARGET_COLLISION`；提交失败 `WF_PERSISTENCE_FAILED`。

### control.task.abandon [required · repeatable]

- 时点：单任务放弃动作结束
- enforcement: `wflib/tasks.py::cmd_task_abandon`
- 动作：保存停止决定与逐项去向后异常归档；未落实去向不结案。
- 出口：去向未落实 → `WF_WORKSPACE_UNRESOLVED`；只报告退出完成，不报告验收通过。
