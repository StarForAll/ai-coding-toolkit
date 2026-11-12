# 第三十八轮外部评审的复核与修正

- 处置编号 R74；实跑见 `validation.md` §64
- 逐条判定：1 成立、2 成立（文档缺漏）、3 成立、4 不成立（体验项，不改）、5 成立（改进）、6 成立（文档漂移）、7 撤回、8 非缺陷、9–12 登记

## 1. 写入目标白名单统一（成立）

`baseline-apply` 有显式白名单，`spec-update` 只判 `.wf/spec/` 前缀——两处判据分开写，正是实现稿自己反对的形态。

处置：`paths.write_target_allowed()` / `write_target_allowed_list()` 作为**单一实现**，两入口都调用它。控制记录（`.wf/writer.json` 等）在两边都 `WF_SCOPE_UNRESOLVED`。

## 2. 归档中断的恢复出口没写进路由（成立，文档缺漏）

「终态已写、目录未移」时只有重入 `archive` 才补做移动，但 skill 路由表没有这一行，人会以为要靠 `repair`。

处置：`wf-continue` 路由表增两行——`status=archived` 但记录仍在活动区 → **重入 `archive` 续做**；归档后写权仍 held → `writer release`。实现稿 §2.3.11 同步登记。

## 3. start 路由缺 activation 核验（成立）

`bind`/`task-new` 不在 `ACTIVATION_REQUIRED`，`writer acquire` 也不在（只有 `release` 在）。按设计稿 §1.3「model-invoked 入口先确认已启用」，这些建立绑定/写权的入口应由脚本核，不靠 skill 纪律。

处置：新增 `ACTIVATION_REQUIRED_ROUTING = {bind, task-new}`，并把 `writer acquire` 纳入子动作判定。实测三者未启用均 `WF_NOT_ENABLED`。

## 4. 归档后不自动释放写权（不成立为缺陷）

`archive` 输出已提示「写权释放后可结束会话」，`ensure_releasable` 对终态对象放行，链路通。属多一步手工，本轮只在路由表补一行提示，不改行为——自动释放会让"人还没看到结果就先丢写权"，反而更差。

## 5. 治理面全树 walk（成立，改进）

改为优先 `git ls-files -z --cached --others --exclude-standard`（与 Git 同源、快），非仓库或失败时退回原 `os.walk`；两边都排除 `.git/.wf/__pycache__/node_modules`。

## 6. D08/D32 的函数名漂移（成立，文档修正）

- D08 实际是 `actions.py::action_id/targets_digest/new_action/pending/step_done/complete`；没有 `begin`/`apply_steps`/`reenter`，也没有 `tasks.py::preflight_collisions`（碰撞预检在各入口就地判定）。
- D32 实际是 `lock.py::acquire/LockHandle/LockBusy/LockUnavailable`；**没有 `verify_holder`/`proc_start`**。

处置：两行按实际函数名改写；**存活探测作为已登记缺口**写入新增的 §2.3.11（当前以人确认旧写者停止替代），不再暗示已实现。

## 7/8. 撤回与非缺陷

模块数一致（23/23）——评审已自行撤回。`parse_frontmatter` 逻辑正确，只是缩进易误读，不改。

## 9–12. 登记

- `_task_command` 的命名约定映射与 `gates.CONTROL_STEP_COMMANDS` 需人工同步：登记，暂不重构。
- `stop` 的 transfer 只核承接任务存在：登记，承接任务后续开工会被门禁拦。
- `review-launch` 允许同 CLI 双槽位、fail 推到 decide：有意设计（`validation.md` §19 双槽位实跑），保留。
- `config.value_of` 不覆盖 `python_executable`/`project_id`，`wf.py` 引导层另写一份：属引导层不导入 `wflib` 的**正当例外**，已在 §2.3.11 明示。
