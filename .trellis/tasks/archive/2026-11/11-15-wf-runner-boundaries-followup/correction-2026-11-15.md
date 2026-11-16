# 更正记录：上轮「无逐 case 重扫」的失实声明（2026-11-15）

## 被更正的原声明（不改写原文）

`.trellis/tasks/archive/2026-11/11-14-wf-runner-correctness-boundaries/validation-2026-11-15.md`
「边界与未覆盖」一节最后一条写道：

> 新增身份核验成本实测：单次 build inputs ~0.04s、模板身份 ~0.10s，均只发生在两个 barrier 级，
> 不在 per-case 循环内；full 未出现逐 case 重扫。

前半句（单次成本量级）成立；**后半句不成立**。旧记录按原文保留，这里只做更正与证据登记。

## 当时真实代码事实

- `repro/repro_select.py::select()` 逐 case 调 `_case_inputs()`，其中每次都要跑
  `source_digest()`（`wf_release_common.source_tree_digest()` ≈4.5 ms 实测）与 `helpers_digest()`
  （7 个 helper 文件各读一次）；一个 88 用例的 full repro 选择阶段因此重复扫了 88 次公共输入。
- `red_subject()` / `input_fingerprint()` 每次调用都再算一遍 `_case_inputs()`，同一 case 内被调 2 次。
- `repro/_worker.py` 每个 case 进程调 `execution_context()` 一次、`input_fingerprint()` 两次，
  每次 `input_fingerprint` 又各算一遍 source/helpers（单次 fingerprint ≈66 ms 实测）。
- 唯一 writer `commit_state()` 逐 case 再算 `red_subject()`（同样包含 source/helpers 重扫）。
- 只读 gate 经 `validate_repro()` 不重算摘要，这一条当时成立。

## 本轮更正与证据

- 公共输入（source/helpers/executor/runner）收敛为唯一产生点 `public_inputs()`，在 freeze 算一次并
  冻结进 bundle schema 2；worker 只重算 case 局部输入（script/targets/case_meta）与 context 比对；
  gate 不重算；writer 在最终 barrier 各重算一次 public/context 并与冻结值比对。
- 断言（新增，可复跑）：
  - `scripts/tests/wf_runtime/test_repro_selection.py::ScanCountTest::test_public_scans_are_constant_in_case_count`
    —— 3 与 30 个 case 的 select+commit 流程中公共扫描计数相同（`source/release/helpers` 各 1）。
  - 同文件 `ScanCountTest::test_worker_consumes_frozen_public_inputs` —— worker 直跑后
    `source`/`helpers` 计数为 0，只有一次 context 比对。
  - `test_results_gate.py::GateTest::test_gate_does_not_rescan_public_inputs` —— 只读 gate 的三项计数为 0。
  - `test_repro_selection.py::BundleSchemaTest::test_tampered_public_inputs_are_refused_at_the_writer_barrier`
    —— 篡改冻结公共输入会在 writer barrier 被拒。
- 旧 schema 1 bundle 现在**明确拒绝**（`validate_bundle` 只接受 schema 2），不做兼容层：
  bundle 是每 run 产物，迁移会让「冻结来源唯一」变成两个来源。

## 剩余边界（如实登记）

- 本更正只覆盖 authoring 运行器（`scripts/tests/**`）的公共摘要扫描；产品发行树与产品 payload
  未改，产品侧是否存在同类逐 case 重扫不在本任务范围。
- `execution_context()` 仍按每个 worker 进程各算一次（含一次 `release_context()`）；它属于
  「每个执行单元的身份事实」而不是逐 case 的公共扫描，故保留，并由上面的计数断言锁定其上限。
