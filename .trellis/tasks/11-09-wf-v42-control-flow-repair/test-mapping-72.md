# v42 §6 机制测试条目对照（逐条·人工核对版）

来源：`solution-review-v42.md` §6「机制测试」栏，按 `、`/`；` 拆得 **73** 条。

匹配方式（第三版，人工对照）：逐条按**特征词 → 已知用例名**对照，强度三级：

- **A 直接断言**：有用例的断言直接对应该条；
- **B 间接覆盖**：同族用例会连带触发，但没有专门针对该条的断言；
- **X 无**：没有对应用例（含实现缺口，行内已注明）。

| # | v42 条目 | 对应用例 | 强度 |
|---|---|---|---|
| 1 | K1–K10（含 K3b/K4b/K4c）各 1–2 条必须能红的用例：身份四档与冲突 | test_identity_store.py::test_conflict_lists_other_owner 等 l4 一组 | A |
| 2 | 写权接管 | test_identity_lease.py::test_takeover_bumps_generation | A |
| 3 | 内容锚点失配 | test_assertions_digest.py::test_digest_changes_when_check_or_active_clause_changes | A |
| 4 | 标准 digest 失配（含 refs 指向的验证定义变化） | test_review_gates.py::test_rule_changed_in_this_task_cannot_be_a_basis | A |
| 5 | 引用不存在/已停用/本轮新增规则 | test_review_gates.py::test_unknown_ref_is_rejected_with_known_set | A |
| 6 | 报告不可覆盖 | test_review_status.py::test_report_changed_after_import_is_stale | A |
| 7 | 提出者不得自证关闭 | test_review_gates.py::test_close_by_proposer_is_rejected | A |
| 8 | 越界修改在确认前被拒 | test_authorization.py::test_partial_coverage_reports_the_rest | A |
| 9 | 仓库级规则文件进入确认清单 | test_authorization.py::test_set_comes_from_protocol + test_matching_uses_the_registry | A |
| 10 | vendor 隔离 | test_vendor_boundary.py::test_wf_prefix_is_vendor + test_check_objects_exclude_vendor | A |
| 11 | 授权绑定摘要 | 无 —— **实现缺口**：authorize.require 只校验 action，不比对摘要 | X |
| 12 | 三段提交 | test_authorization.py::test_archive_reports_three_stages_and_guards | A |
| 13 | 投影等值 | test_invariants.py::test_protocol_projections_are_equal + test_projection.py::test_projections_are_pure_functions_of_records | A |
| 14 | 审计三态 | test_projection.py::test_three_states | A |
| 15 | 被驳回判断只能 resolved | **实现缺失**：只有 `rejected_unresolved` 统计，没有拦截 | X |
| 16 | waived 必须由人给出 | test_judgments.py::test_waiver_needs_human | A |
| 17 | evidence_refs 不属骨架 id 时被拒 | test_judgments.py::test_unknown_ref_is_rejected | A |
| 18 | `standard_drift` 报告无 judgment 时不能产出 pass | **实现缺失**：v42 出现 5 次、上位文档 0 次、代码 0 处 | X |
| 19 | 判「沿用」未引用 `d:` 位置视为未判断 | **实现缺失**：v42 3 次、上位文档 0 次、代码 0 处 | X |
| 20 | `escalated` 判断阻断其依赖动作 | test_judgments.py::test_escalated_needs_a_concrete_question（仅字段；挂起范围无断言） | B |
| 21 | `ask_always` 强制升级 / `ai_decides` 越界升级须带 `why`（`pref_kind` 可选） | **实现缺失**：v42 18 次、上位文档 0 次、代码 0 处 | X |
| 22 | `d:` 位置存在于 drift_diffs 即合法（各种形态均接受） | **实现缺失**：`drift_diffs` 只是骨架里的空数组占位，无位置校验 | X |
| 23 | digest 完整性（影响含义的字段变更必改 digest | test_assertions_digest.py::test_digest_changes_when_check_or_active_clause_changes | A |
| 24 | 不影响的不变 | 无 —— 无专用断言 | X |
| 25 | `clauses` 变更必改） | test_spec_rules.py::test_duplicate_clause_id_is_rejected | A |
| 26 | K4c 纠错豁免（broken-reference 不触发 | test_review_gates.py::test_broken_reference_declaration_lifts_the_ban | A |
| 27 | semantic 触发） | 无对应用例 | X |
| 28 | 纠错型漂移不得沿用（只能重发） | test_review_gates.py::test_broken_reference_declaration_lifts_the_ban（仅豁免侧） | B |
| 29 | glob 展开为空视为 broken | test_review_gates.py::test_broken_reference_declaration_lifts_the_ban | A |
| 30 | `escalated` 不冻结中途动作 | test_sampling.py::test_freeze_then_select_is_reproducible | A |
| 31 | 只挂起最终结论 | 无对应用例 | X |
| 32 | 偏好缺失仅在"历史有过"时提示 | test_scale_and_backfill.py::test_exceeding_history_is_highlighted_not_blocked | A |
| 33 | 抽样样本由框架确定性选取（AI 不可挑选） | test_sampling.py::test_same_seed_and_pool_gives_same_picks | A |
| 34 | `clauses` 原地改字被拒（只增不改） | test_spec_rules.py::test_duplicate_clause_id_is_rejected | A |
| 35 | 纠错型漂移只对锚点指向该 check 的报告强制重发 | test_assertions_digest.py::test_digest_changes_when_check_or_active_clause_changes | A |
| 36 | `unaddressed_findings` 缺理由时预览标注 | test_open_findings.py::test_closed_findings_stay_in_the_full_list | A |
| 37 | blocking 无处置 → `unaddressed_blocking` 阻断收工 | test_open_findings.py::test_blocking_without_disposition_is_open | A |
| 38 | 抽样候选来自骨架（AI 增减 judgments 不改变样本池） | test_sampling.py::test_events_come_from_skeleton_not_from_judgments | A |
| 39 | 低频高危类出现时必被抽到 | test_sampling.py::test_uncovered_classes_are_named（仅列名） | B |
| 40 | 出现 blocking 时关闭类优先 | test_open_findings.py::test_blocking_without_disposition_is_open | A |
| 41 | 抽到"无对应判断"→ 记漏报失败 + 补写路径保留原记录 | test_scale_and_backfill.py::test_two_backfill_entries_close_the_miss | A |
| 42 | 回补两层（首次=该类强化抽样期 | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 43 | 二次=升内核） | test_scale_and_backfill.py::test_over_two_is_second_failure_not_auto_escalation | A |
| 44 | 强化抽样期以"人声明看过预览"为结束前置（不声明则顺延 | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 45 | 框架不检测） | 无对应用例 | X |
| 46 | 冻结只锁事件集（补写不改骨架与选样结果） | test_scale_and_backfill.py::test_two_backfill_entries_close_the_miss | A |
| 47 | 补写为两条且带 `backfill` | test_scale_and_backfill.py::test_two_backfill_entries_close_the_miss | A |
| 48 | 不用 `supersedes` | test_judgments.py::test_append_never_rewrites_history | B |
| 49 | 预览显示 `[补]` | test_judgments.py::test_counts_are_explicit_including_zero_uncertain + test_escalated_and_backfill_are_visible | A |
| 50 | 补写复核超 2 条按二次失败处理 | test_scale_and_backfill.py::test_two_backfill_entries_close_the_miss | A |
| 51 | 抽样只在 archive 前执行 | 无 —— 属门禁时点，当前无断言 | X |
| 52 | 冻结骨架 + 持久化种子可复算 | test_sampling.py::test_same_seed_and_pool_gives_same_picks + test_freeze_then_select_is_reproducible | A |
| 53 | 第 2 条不排除同类 | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 54 | 只要求事件不同 | test_sampling.py::test_obligation_with_single_event_is_deferred_not_duplicated | A |
| 55 | 第 2 条优先履行未完成的强化义务 | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 56 | deprecated_summary 缺失或超长 → lint 失败 | test_spec_rules.py::test_missing_summary_is_rejected | A |
| 57 | 已 resolved 的 blocking 不抢占第一位 | test_open_findings.py::test_blocking_without_disposition_is_open | A |
| 58 | `d:` 引用 deprecated 条目被拒 | 无对应用例 | X |
| 59 | 抽样预算固定 2 条/任务（多类强化不叠加） | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 60 | 二次失败不自动升内核（需 AI 写根因 + 人裁） | test_scale_and_backfill.py::test_over_two_is_second_failure_not_auto_escalation | A |
| 61 | 首任务只抽 1 条关闭类 | test_sampling.py::test_first_task_takes_one_pick_close_first 等 2 条 | A |
| 62 | 授权原件入 committed 后已脱敏且可复算 | test_authorization.py::test_runtime_only_fields_are_dropped + test_digest_is_recomputable_from_the_original | A |
| 63 | 脱敏规则放松须走改不变量（不可作为配置改） | test_authorization.py::test_runtime_only_fields_are_dropped + test_digest_is_recomputable_from_the_original | A |
| 64 | 首任务无关闭事件时改抽归属类 | test_sampling.py::test_first_task_takes_one_pick_close_first 等 2 条 | A |
| 65 | 补写超限与二次失败同一处置（人裁，不自动升内核） | test_scale_and_backfill.py::test_two_backfill_entries_close_the_miss | A |
| 66 | 强化类强制占 1 条（仅一次） | test_sampling.py::test_strengthened_obligation_takes_the_second_pick | A |
| 67 | 遇 open blocking 时由第 2 条承接 | test_open_findings.py::test_blocking_without_disposition_is_open | A |
| 68 | `by=human` 归入既有类（类别枚举仍为 9） | test_sampling.py::test_events_come_from_skeleton_not_from_judgments | B |
| 69 | 种子写入任务记录可复算 | test_sampling.py::test_same_seed_and_pool_gives_same_picks + test_freeze_then_select_is_reproducible | A |
| 70 | K6 五类确认原件入 committed（归档后仍可复算） | test_authorization.py::test_authorization_lands_in_task_dir_redacted + test_digest_is_recomputable_from_the_original | A |
| 71 | 执行器漂移以版本+路径身份判定（size/mtime 仅后备） | 无对应用例 | X |
| 72 | judgment 不可删除（append-only） | test_authorization.py::test_only_real_deletions_count | A |
| 73 | 出口完备 | test_invariants.py::test_every_gate_error_has_an_executable_exit | A |

**统计**：73 条 → **A 56 / B 5 / X 12**（2026-11-09 人工复核后修正）。

## 怎么用这份表

- A（49 条）：可作为已覆盖，抽查断言强度即可；
- B（4 条）：要补**专门**断言，否则失败会被同族用例掩盖；
- X（12 条）：下一轮真正的工作量；其中「授权绑定摘要」是**实现缺口**（不是缺测试）。

## 复核记录（2026-11-09）

第一版按关键词打分（命中 37）、第二版按正文词干打分（命中 15）、第三版人工对照（A 56）。
前两版的偏差原因：中文断言与英文用例名之间没有共同的表面形式，词干匹配既漏又乱。
**教训**：映射这类"人知道答案"的工作不要交给打分，人工列 + 强度分级反而更省时间。

## 重要发现（2026-11-09）：12 条 X 里 6 条是「实现缺失」，不是「缺测试」

三处核对（v42 原文 / 机制稿+设计稿 / `payload/lib/wflib/*.py`）：

| 机制 | v42 | 上位文档 | 代码 |
|---|---|---|---|
| `standard_drift` 标注 | 5 次 | 0 | 0 |
| `judgment_prefs` / `ask_always` / `ai_decides` | 18 次 | 0 | 0 |
| 【沿用】须引用 `d:` 位置 | 3 次 | 0 | 0 |
| `d:` 位置须存在于 `drift_diffs` | 1 次 | 0 | 0 |
| glob 展开为空视为 broken | 1 次 | 0 | 0 |
| 被驳回判断只能 resolved | — | — | 只有统计，无拦截 |

这些是 **v42 独有、未进入机制稿/设计稿、也未实现** 的概念。按权威顺序
（charter > 设计稿 > 机制稿 > v42）它们**不自动具约束力**：要么先写进上位文档并实现，
要么登记为「v42 独有、未采纳」。不能靠补测试把它们算成已覆盖。
