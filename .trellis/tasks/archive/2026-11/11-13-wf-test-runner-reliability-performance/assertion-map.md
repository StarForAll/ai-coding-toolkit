# r68/r71 assertion map

Baseline: HEAD 1c58bce1. Each row tracks an original observable assertion.

| ID | Original assertion | Old source | Destination | Status |
|---|---|---|---|---|
| r68_tests:201 | 1 正常审查可 pass | scripts/tests/wf_runtime/full/r68_tests.py:201 | full r68_tests | retained |
| r68_tests:211 | 2 导入后锚点失效 → 判定拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:211 | full r68_tests | retained |
| r68_tests:214 | 3 带阻塞发现 → 判定拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:214 | wf_review/test_report_variants.py::test_r68_invalid_report_inputs_are_rejected_before_verdict | migrated |
| r68_tests:216 | 4 未声明的审查 CLI → 判定拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:216 | wf_review/test_report_variants.py::test_r68_invalid_report_inputs_are_rejected_before_verdict | migrated |
| r68_tests:218 | 5 缺读取范围声明 → 判定拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:218 | wf_review/test_report_variants.py::test_r68_invalid_report_inputs_are_rejected_before_verdict | migrated |
| r68_tests:223 | 6 审查轴 fail → 判定拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:223 | wf_review/test_report_variants.py::test_r68_invalid_report_inputs_are_rejected_before_verdict | migrated |
| r68_tests:227 | 7 声明未覆盖例外 → 按缺口留痕（不阻断） | scripts/tests/wf_runtime/full/r68_tests.py:227 | wf_review/test_report_variants.py::test_r68_legacy_scope_exceptions_do_not_block_valid_review | migrated |
| r68_tests:240 | 8 预览后无变化时可应用 | scripts/tests/wf_runtime/full/r68_tests.py:240 | full r68_tests | retained |
| r68_tests:243 | 8b 等待窗口内写者变化 → 预览失效 | scripts/tests/wf_runtime/full/r68_tests.py:243 | full r68_tests | retained |
| r68_tests:254 | 9 空锁文件不被 repair 认领 | scripts/tests/wf_runtime/full/r68_tests.py:254 | full r68_tests | retained |
| r68_tests:294 | 10d 绑定批准 + 前像齐全 → 通过 | scripts/tests/wf_runtime/full/r68_tests.py:294 | full r68_tests | retained |
| r68_tests:312 | 11 部分写入失败给结构化退出 | scripts/tests/wf_runtime/full/r68_tests.py:312 | full r68_tests | retained |
| r68_tests:318 | 11b 同提案重入续做（已写文件不挡） | scripts/tests/wf_runtime/full/r68_tests.py:318 | full r68_tests | retained |
| r68_tests:287 | 10 拒绝决定不得执行基线写入 | scripts/tests/wf_runtime/full/r68_tests.py:287 | full r68_tests | retained |
| r68_tests:289 | 10b 批准未绑定本提案 → 拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:289 | full r68_tests | retained |
| r68_tests:291 | 10c 缺前像指纹 → 拒绝 | scripts/tests/wf_runtime/full/r68_tests.py:291 | full r68_tests | retained |
| r71_tests:88 | 1 交接发起拒绝错误实例标识 | scripts/tests/wf_runtime/full/r71_tests.py:88 | full r71_tests | retained |
| r71_tests:91 | 1b 交接未进入 recovering | scripts/tests/wf_runtime/full/r71_tests.py:91 | full r71_tests | retained |
| r71_tests:94 | 1c 正常交接发起 | scripts/tests/wf_runtime/full/r71_tests.py:94 | full r71_tests | retained |
| r71_tests:145 | 2 计划被替换 → 预览失效 | scripts/tests/wf_runtime/full/r71_tests.py:145 | full r71_tests | retained |
| r71_tests:149 | 2b 未按被替换的计划写回 | scripts/tests/wf_runtime/full/r71_tests.py:149 | full r71_tests | retained |
| r71_tests:264 | 3 五轴齐全且通过 → pass | scripts/tests/wf_runtime/full/r71_tests.py:264 | full r71_tests | retained |
| r71_tests:266 | 3b axes 为空被拒 | scripts/tests/wf_runtime/full/r71_tests.py:266 | wf_review/test_report_variants.py::test_r71_invalid_axis_variants_never_write_a_verdict | migrated |
| r71_tests:268 | 3c 只报一轴被拒 | scripts/tests/wf_runtime/full/r71_tests.py:268 | wf_review/test_report_variants.py::test_r71_invalid_axis_variants_never_write_a_verdict | migrated |
| r71_tests:272 | 3d 缺可测性轴被拒 | scripts/tests/wf_runtime/full/r71_tests.py:272 | wf_review/test_report_variants.py::test_r71_invalid_axis_variants_never_write_a_verdict | migrated |
| r71_tests:276 | 3e 未知轴被拒且不写判定 | scripts/tests/wf_runtime/full/r71_tests.py:276 | wf_review/test_report_variants.py::test_r71_invalid_axis_variants_never_write_a_verdict | migrated |
| r71_tests:283 | 3f 单 reviewer 不产生判定结论 | scripts/tests/wf_runtime/full/r71_tests.py:283 | full r71_tests | retained |
| r71_tests:298 | 3h 有效审查 fail 落判定且历史可重建 | scripts/tests/wf_runtime/full/r71_tests.py:298 | full r71_tests | retained |
| r71_tests:308 | 3g 同 CLI 双槽位不产生判定结论 | scripts/tests/wf_runtime/full/r71_tests.py:308 | full r71_tests | retained |
| r71_tests:331 | 4 交接 begin 成功 | scripts/tests/wf_runtime/full/r71_tests.py:331 | full r71_tests | retained |
| r71_tests:333 | 4b begin 后进入 recovering 且旧代次失效 | scripts/tests/wf_runtime/full/r71_tests.py:333 | full r71_tests | retained |
| r71_tests:341 | 4c 交接中间态旧会话不可写 | scripts/tests/wf_runtime/full/r71_tests.py:341 | full r71_tests | retained |
| r71_tests:349 | 4c2 accept 前接收者不可推进 | scripts/tests/wf_runtime/full/r71_tests.py:349 | full r71_tests | retained |
| r71_tests:356 | 4d 接收者 accept 获得新代次 | scripts/tests/wf_runtime/full/r71_tests.py:356 | full r71_tests | retained |
| r71_tests:361 | 4e 接收者持新代次可推进 | scripts/tests/wf_runtime/full/r71_tests.py:361 | full r71_tests | retained |
| r71_tests:365 | 4f accept 后旧会话/旧代次失效 | scripts/tests/wf_runtime/full/r71_tests.py:365 | full r71_tests | retained |
