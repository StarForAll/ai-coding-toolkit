# C3 验证记录：缓存恢复、材料盘点与退役

> 实施会话 2026-11-17；解释器 `/softwares/python/bin/python3 -B`。

## 激活记录（2026-11-17）

- 实际会话：DSH **inline**（`dsh.dispatch_mode: inline`，`in_progress-inline` 横幅；主会话直接
  实现/检查，不派发 implement/check 子agent）。本任务 `implement.jsonl`/`check.jsonl` 有意为空，
  按 activation.md 的 inline 分支以 `task.py start --allow-empty-context` 激活；分支 `main`。
- 未使用 ZCode/其他 dispatch 分支；若未来切到 `dispatch_mode: auto`，必须先为该子任务填写
  真实 spec/research 清单并 `task.py validate`，不能沿用本次 inline 记录。

## AC04–06（恢复与事务）

- 模板缓存：`publish` 真实 checkpoint `after-staging-before-journal|after-journal|after-old-moved|after-new-installed|after-meta|after-material-cleanup-before-journal-remove`（`WF_TEMPLATE_TXN_STOP_AFTER`，仅开关+owned scope），helper/进程 `os._exit(97)`；重入 `acquire` 分别得到 rolled-back / rolled-back / rolled-back / rolled-forward / rolled-forward，journal 清空、meta.root/tree digest 有效（`test_template_cache.CheckpointTest`）。
- 测试发行：同窗口通过 `ensure` 重入恢复；其 journal 在写入前已冻结新代摘要，W1–W3 前滚（与模板“repoint 后才确认摘要”的 W1–W3 回滚不同，不能复制同一断言），W4/F1 前滚（`test_release_maintenance.CheckpointTest`）。
- 首次发布（old absent）：`after-new-installed` → rolled-back-absent，随后真实入口重建；O1 staging 无 journal 时 inventory 标 owned、safe-legacy 可精确退役。
- F1：材料已删但 journal 在 → 重入前滚并清 journal；`_finish/_finish_transaction` 材料删除失败保留 journal（`test_template_cache.FinishFailureTest`）。
- 只读 `lookup` 遇未完成 journal 返回 recovery-required 且不写；测试发行 `--check` 同语义（`test_release_lock` 既有用例）。

## AC17–19（盘点/退役/observe）

- 统一选择格式与摘要：`resource_lifecycle.selection_entries/selection_digest/execute_retirement`；报告先建、逐项删除、部分失败停止、重试需重盘点（`test_resource_lifecycle.RetirementTest`）。
- safe-legacy 只接受可验证归属（严格旧 owner 结果、fixture marker、material-owner）；新协议结果/journal/unproven 拒绝。
- manual-retained：真实 TTY + 精确短语 `<domain> <root> <digest> abandon`（缓存 unproven 追加 `unproven-cache`）；非 TTY/错短语/摘要漂移/活引用/忙锁均零删除。
- 坏 journal key：inventory 标 journal blocked；manual `entry+journal` 同时选中后按材料→marker→journal 顺序删除，同 key 真实入口重建成功。
- observe：root controller 每次真实运行恰一次浅扫（结果缓存/模板/测试发行根去重；不存在根给 absent），记录 counts/capacity/inventory hint，不恢复、不取锁；计划/内嵌/per-case 零调用（`test_wf_runtime/test_run_all_contract.test_template_window...`、`test_template_cache.CheckpointTest.test_observe...`、`test_release_maintenance...test_observe...`、`test_fixture_scope.ResultsInventoryTest.test_observe...`）。

## 命令

```bash
/softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_template_cache \
  scripts.tests.wf_runtime.test_test_release scripts.tests.wf_runtime.test_release_lock \
  scripts.tests.wf_runtime.test_release_maintenance scripts.tests.wf_runtime.test_fixture_scope \
  scripts.tests.wf_runtime.test_resource_lifecycle
WF_SLOW_TESTS=1 /softwares/python/bin/python3 -B -m unittest scripts.tests.wf_runtime.test_run_all_contract
/softwares/python/bin/python3 -B -m unittest discover -s scripts/tests -t .      # 1223 OK
```

## 限制

- unproven 缓存的人工放弃风险由 R10 已确认范围承担；脚本不还原历史归属，也不把结果/fixture 扩进该许可。
- 活引用只覆盖同 UID 可见的 /proc；非本 UID/不可读进程按拒绝处理，不承诺发现全部外部写入。
- 容量上限重构不在本轮；observe 的 `capacity=not-measured` 如实标注。


## 复审补记

- 成功发布后 staging/backup 的 fixture marker 与 entry meta 的清理已补齐；坏 journal reset 需整组
  选中同 key 条目；safe-legacy 拒绝有效 entry；selection/report 在 scope 外拒绝。
- observe 改为真正浅层（不递归/不算树摘要/1 MiB 控制记录/observed_at/no-template-cache 跳过，
  无关根读取失败只诊断），并有定向反例测试。
- 测试发行 journal 内部材料路径在恢复前校验；F1 材料清理失败保留 journal 的定向测试补齐。
