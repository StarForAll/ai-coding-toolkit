# Step 4 验证记录（2026-11-14 20:3x–20:4x）

## 调度合并

- `run_one.sh` 成为唯一单元执行器：入参五段记录，解析后一切路径/键只用 `name`；
  `script` 只从记录取（f0 → p5_f0.py）；`kind` 映射（suite|candidate→suite、flow|extra→flow）只此一处；
  `fixture` 分派 template/install；`WF_NAMESPACE=1/0` 决定执行域；结果行固定五列。
- `run_all.sh` 删除 run_suite/run_flow/run_f0/run_extra/expect_of 与所有计数递增；
  并行段 xargs 调用 worker、串行段以 `WF_NAMESPACE=0` 逐个调用同一 worker；
  `results_gate` 移到两段都结束后对 `PLAN_UNITS` 名字全集判一次；
  `suite_ran`/`flow_ran` 由 lines × 记录 kind 一次派生；计时在两段后统一读全部 `.timing`。
- 计数不变式（实测 s1/s2）：lines=64（59+5）；units_total=149（59+5+85）；repro_ran=85 == REPRO_TOTAL。

## 等价性对拍（并行 vs --serial）

- `--full --repro green`：49.87s / 49.65s（两次采样）；`--serial`：258.98s。
- `lines` 64 行（name/rc/status）逐项相等；`repro/*.json` 85 项（mode/green/red/verified）逐项相等；
  summary 的 suite_ran/flow_ran/repro_ran/units_total/fail 全部相等（脚本化对拍输出 EQUIVALENT）。
- 串行域实证（AC1 的对照面）：并行 cp1 运行后宿主 `/tmp` 新增 `cp1_*` 产物 0 个；串行运行后新增 23 个
  （宿主 `/tmp` + 无 unshare），证明两域确实不同且 `--serial` 保留宿主语义。
- f0 迁入 worker：representative（26.21s，62 单元 0 失败）与 full（49s，149 单元 0 失败）均绿；
  `lines` 中 `f0 0 2 ok saved 9`（安装 + 自举闭环在私有 tmpfs 内完成）。

## 完整性覆盖（串行段）

- r67 新增 4d：临时把 cp1 标 `parallel:false`，并让串行域（WF_NAMESPACE=0）的桩不写结果行 →
  run_all 非零退出且输出 `MISSING-RESULTS:cp1_tests`（gate 覆盖 PLAN_UNITS 全集，不是只覆盖并行子集）。
- r67 4c：桩少输出一行 `[PASS]`（汇总行同步为 expect-1）→ `EXECUTION-FAILED: cp1_tests … expected=20`，
  整次非零退出。

## repro

- 默认串行（决策 #3）：pool/repro 分段墙钟分别记录（s1: pool=30s, repro=19s, startup≈0）。
- `--repro-concurrent` 抽样：46.41s 绿，jobs=5 / repro_jobs=3，summary `repro_concurrent=true`；
  与默认路径对拍（lines/repro/summary 计数）EQUIVALENT。默认路径未改变。

## summary / 契约

- schema_version=2；新增 pool_seconds / repro_seconds / startup_seconds / repro_concurrent / budget
  （60s 目标、65s 硬阈值，只报告）；template_reused 口径放宽为“共享夹具源”（断言值不变）。
- `test_run_all_contract.py` 复核：flow_ran==2 / suite_ran==1 / flow_ran==0 / template_reused True 全部成立；
  新增 schema_version/units_total 不变式/budget 存在性断言。
- T0：873 tests OK（skipped=10）。`WF_SLOW_TESTS=1` 契约：9 tests OK（47.6s，含 candidate 代表集）。

## AC4 余量

- 8 并发下最慢单元：r17r24_tests 20.19s（WF_COMMAND_TIMEOUT=180s，≈8.9× 余量）。
- repro 最慢用例：bind-resume-under-lock 6.86s（WF_REPRO_TIMEOUT=120s，≈17× 余量）。
