# 第四次审查裁定（2026-11-09）

| 审查条目 | 核实 | 处置 |
|---|---|---|
| **b-N1 `old_paths/new_paths` 第三处拼接仍崩** | ✅ 属实：`tasks.py:3720`（cmd_spec_update 的批准面校验）在 `spec.validate_changes` **之前**执行，字符串形态先炸 | **根因修**：新增 `paths.path_list()` 作为**唯一实现**，`spec.py::_path_list` 与 `tasks.py:3720` 都委托它；全仓 grep 确认再无裸拼接（仅剩内部状态拼接，不涉用户输入） |
| **b-N2 `task-abandon` 两种形态缺陷** | ✅ 属实：数组形态裸 `AttributeError`；空处置被当"没给处置"卡在预览态 | 先按形态归一（list → `{"changes": [...]}`，其它类型结构化拒绝）；`disposition is None and 需要处置` 才预览，空处置在无待处置项时放行 |
| **b-N3 cp2 A13 差一个 `threshold` 字段** | ✅ 事实相符，但**根因不是断言口径**：cp2 的采样调用缺 sid（我上一轮批量插入的漏网点），导致归档被 `task.sampled` 拦在前面，根本没走到 debug 分支 | ① 给 cp2/cp3/cp4/cp5_b345/r31r34 的采样调用补 sid；② 顺手在 debug 分支 facts 里补 `threshold`（AI 才知道"第几次算重复"） |
| **b-N3 r58 缺采样前置** | ✅ 属实（r58 不走 archive 子命令，我上轮 12 套件的补采样漏了它） | `run_final_gate()` 内先把 `task.sampling.picks` 备好（本套件测的是阈值裁定，不是抽样） |
| **b-N3 cp4 / cp5 / r17r24 红** | cp2 为假红（见上）；cp4/cp5/r17r24 未在本次修复范围内 | 保留登记，下一轮按"先打印 code+facts"逐条处理 |

## 本轮修复的性质

- **N1、N2 是产品缺陷**（违反 K10：裸异常 / 无出口），按根因修并加断言（`paths.path_list` 三态 + 禁止裸拼接的回归断言）。
- **cp2 是我自己的夹具污染**（缺 sid 让门禁先拦），不是产品问题；顺手补的 `threshold` 才是产品侧的可用性改进。
- **r58 是夹具漏迁移**，不是产品缺陷。

## 验证

290 条单测全绿；`--verify` 字节复现（70 assets）；设计门禁 / 文档引用 / 协议一致全绿。
实跑：`cp2` **15/15**、`r58` **10/10**。
