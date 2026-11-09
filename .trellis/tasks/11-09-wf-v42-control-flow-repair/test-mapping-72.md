# v42 §6 机制测试条目对照（逐条）

来源：`solution-review-v42.md` §6「机制测试」栏，按 `、`/`；` 拆得 **73** 条。

匹配方式：概念词 → **用例正文**（含 docstring）检索，命中即列出首个对上号的用例。
这是**线索表**：命中说明「有专门断言」，断言强度仍需人抽查；`—` 表示当前没有对应用例。

| # | v42 条目 | 对应用例 |
|---|---|---|
| 1 | K1–K10（含 K3b/K4b/K4c）各 1–2 条必须能红的用例：身份四档与冲突 | test_identity_store.py::test_unknown_when_bound_but_held_by_other_and_no_attachment |
| 2 | 写权接管 | test_identity_store.py::test_registered_multi_root_discloses |
| 3 | 内容锚点失配 | test_identity_store.py::test_registered_multi_root_discloses |
| 4 | 标准 digest 失配（含 refs 指向的验证定义变化） | test_validate_wf_design.py::test_malformed_baseline_digest_fails |
| 5 | 引用不存在/已停用/本轮新增规则 | test_validate_wf_design.py::test_three_level_reference_fails |
| 6 | 报告不可覆盖 | test_invariants.py::test_protocol_projections_are_equal |
| 7 | 提出者不得自证关闭 | test_review_gates.py::test_rule_changed_in_this_task_cannot_be_a_basis |
| 8 | 越界修改在确认前被拒 | test_vendor_boundary.py::test_classifier_has_a_vendor_bucket |
| 9 | 仓库级规则文件进入确认清单 | test_authorization.py::test_authorization_lands_in_task_dir_redacted |
| 10 | vendor 隔离 | test_vendor_boundary.py::test_wf_prefix_is_vendor |
| 11 | 授权绑定摘要 | — |
| 12 | 三段提交 | test_authorization.py::test_archive_reports_three_stages_and_guards |
| 13 | 投影等值 | test_identity_store.py::test_registered_multi_root_discloses |
| 14 | 审计三态 | test_projection.py::test_projections_are_pure_functions_of_records |
| 15 | 被驳回判断只能 resolved | test_invariants.py::test_protocol_projections_are_equal |
| 16 | waived 必须由人给出 | — |
| 17 | evidence_refs 不属骨架 id 时被拒 | — |
| 18 | `standard_drift` 报告无 judgment 时不能产出 pass | — |
| 19 | 判「沿用」未引用 `d:` 位置视为未判断 | test_validate_wf_design.py::test_three_level_reference_fails |
| 20 | `escalated` 判断阻断其依赖动作 | test_invariants.py::test_protocol_projections_are_equal |
| 21 | `ask_always` 强制升级 / `ai_decides` 越界升级须带 `why`（`pref_kind` 可选） | test_vendor_boundary.py::test_classifier_has_a_vendor_bucket |
| 22 | `d:` 位置存在于 drift_diffs 即合法（各种形态均接受） | — |
| 23 | digest 完整性（影响含义的字段变更必改 digest | test_validate_wf_design.py::test_malformed_baseline_digest_fails |
| 24 | 不影响的不变 | — |
| 25 | `clauses` 变更必改） | — |
| 26 | K4c 纠错豁免（broken-reference 不触发 | — |
| 27 | semantic 触发） | — |
| 28 | 纠错型漂移不得沿用（只能重发） | — |
| 29 | glob 展开为空视为 broken | — |
| 30 | `escalated` 不冻结中途动作 | — |
| 31 | 只挂起最终结论 | — |
| 32 | 偏好缺失仅在"历史有过"时提示 | — |
| 33 | 抽样样本由框架确定性选取（AI 不可挑选） | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 34 | `clauses` 原地改字被拒（只增不改） | — |
| 35 | 纠错型漂移只对锚点指向该 check 的报告强制重发 | test_identity_store.py::test_registered_multi_root_discloses |
| 36 | `unaddressed_findings` 缺理由时预览标注 | test_lint_report.py::test_all_problems_are_listed_in_one_pass |
| 37 | blocking 无处置 → `unaddressed_blocking` 阻断收工 | test_lint_report.py::test_all_problems_are_listed_in_one_pass |
| 38 | 抽样候选来自骨架（AI 增减 judgments 不改变样本池） | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 39 | 低频高危类出现时必被抽到 | — |
| 40 | 出现 blocking 时关闭类优先 | test_lint_report.py::test_all_problems_are_listed_in_one_pass |
| 41 | 抽到"无对应判断"→ 记漏报失败 + 补写路径保留原记录 | test_invariants.py::test_protocol_projections_are_equal |
| 42 | 回补两层（首次=该类强化抽样期 | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 43 | 二次=升内核） | — |
| 44 | 强化抽样期以"人声明看过预览"为结束前置（不声明则顺延 | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 45 | 框架不检测） | — |
| 46 | 冻结只锁事件集（补写不改骨架与选样结果） | — |
| 47 | 补写为两条且带 `backfill` | — |
| 48 | 不用 `supersedes` | — |
| 49 | 预览显示 `[补]` | — |
| 50 | 补写复核超 2 条按二次失败处理 | — |
| 51 | 抽样只在 archive 前执行 | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 52 | 冻结骨架 + 持久化种子可复算 | — |
| 53 | 第 2 条不排除同类 | — |
| 54 | 只要求事件不同 | — |
| 55 | 第 2 条优先履行未完成的强化义务 | — |
| 56 | deprecated_summary 缺失或超长 → lint 失败 | — |
| 57 | 已 resolved 的 blocking 不抢占第一位 | test_lint_report.py::test_all_problems_are_listed_in_one_pass |
| 58 | `d:` 引用 deprecated 条目被拒 | test_validate_wf_design.py::test_three_level_reference_fails |
| 59 | 抽样预算固定 2 条/任务（多类强化不叠加） | test_sampling.py::test_same_seed_and_pool_gives_same_picks |
| 60 | 二次失败不自动升内核（需 AI 写根因 + 人裁） | — |
| 61 | 首任务只抽 1 条关闭类 | — |
| 62 | 授权原件入 committed 后已脱敏且可复算 | test_invariants.py::test_doctrine_machine_facts_match_protocol |
| 63 | 脱敏规则放松须走改不变量（不可作为配置改） | test_invariants.py::test_doctrine_machine_facts_match_protocol |
| 64 | 首任务无关闭事件时改抽归属类 | — |
| 65 | 补写超限与二次失败同一处置（人裁，不自动升内核） | — |
| 66 | 强化类强制占 1 条（仅一次） | — |
| 67 | 遇 open blocking 时由第 2 条承接 | test_lint_report.py::test_all_problems_are_listed_in_one_pass |
| 68 | `by=human` 归入既有类（类别枚举仍为 9） | — |
| 69 | 种子写入任务记录可复算 | — |
| 70 | K6 五类确认原件入 committed（归档后仍可复算） | — |
| 71 | 执行器漂移以版本+路径身份判定（size/mtime 仅后备） | test_identity_store.py::test_unknown_when_bound_but_held_by_other_and_no_attachment |
| 72 | judgment 不可删除（append-only） | test_build_wf_release.py::test_preflight_runs_before_removing_release_tree |
| 73 | 出口完备 | test_invariants.py::test_every_gate_error_has_an_executable_exit |

**统计**：73 条命中 **37**，未命中 **36**。

## 未命中（当前无对应用例）

- 授权绑定摘要
- waived 必须由人给出
- evidence_refs 不属骨架 id 时被拒
- `standard_drift` 报告无 judgment 时不能产出 pass
- `d:` 位置存在于 drift_diffs 即合法（各种形态均接受）
- 不影响的不变
- `clauses` 变更必改）
- K4c 纠错豁免（broken-reference 不触发
- semantic 触发）
- 纠错型漂移不得沿用（只能重发）
- glob 展开为空视为 broken
- `escalated` 不冻结中途动作
- 只挂起最终结论
- 偏好缺失仅在"历史有过"时提示
- `clauses` 原地改字被拒（只增不改）
- 低频高危类出现时必被抽到
- 二次=升内核）
- 框架不检测）
- 冻结只锁事件集（补写不改骨架与选样结果）
- 补写为两条且带 `backfill`
- 不用 `supersedes`
- 预览显示 `[补]`
- 补写复核超 2 条按二次失败处理
- 冻结骨架 + 持久化种子可复算
- 第 2 条不排除同类
- 只要求事件不同
- 第 2 条优先履行未完成的强化义务
- deprecated_summary 缺失或超长 → lint 失败
- 二次失败不自动升内核（需 AI 写根因 + 人裁）
- 首任务只抽 1 条关闭类
- 首任务无关闭事件时改抽归属类
- 补写超限与二次失败同一处置（人裁，不自动升内核）
- 强化类强制占 1 条（仅一次）
- `by=human` 归入既有类（类别枚举仍为 9）
- 种子写入任务记录可复算
- K6 五类确认原件入 committed（归档后仍可复算）

## 说明

- 未命中 ≠ 失败不存在，只表示没有专用断言；逐条确认需人读（v42 §6 元规则）。
- 与 `test-mapping.md`（族级映射）互补：族级答「哪一族有证据」，本表答「哪一条对上了」。
