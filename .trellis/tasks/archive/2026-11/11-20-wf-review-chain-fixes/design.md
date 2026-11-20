# 技术设计：wf 审查链路与发行身份修正

## 1. 边界与目标

本设计只修当前 HEAD 已核实的实现缺陷、版本身份与文档口径，不新增 skill、不新增流程层、不实现第三轮的 `upgrade --apply`。核心边界：

- 机制只做可稳定计算的事实：Check 有效性、覆盖合并、未关闭 blocking、材料集合、版本身份。
- 主会话保留：五轴结论、逐报告 `reliance`、逐 finding `verified/disputed/unable`、误报/重分类的处置理由。
- 人保留：覆盖缺口接受、审查不可用、任务降级、残余风险承担；错误码与回显不得把 AI 可补齐的输入伪装成人判。

## 2. 审查链路契约

### 2.1 Check 有效性单一实现

`gates.check_validity(ctx, task)`（`gates.py:584`）已经是 Check 有效性的唯一判据，包含规则版本、锚点漂移、失效登记、`result != pass`、结构复核。修改：

- `review.launch` 在锁内重读任务后调用 `check_validity`，非 `valid` 时以 `code/facts/blockers` 抛出 `ReviewError`，不再只核 `check.result`。
- `review.context` 从 `task.reviews.launches` 取本轮 launch 的 `anchor.check_anchor`，与 `_current_anchor` 计算的当前锚点比较；不一致时抛 `WF_CHECK_STALE`，不创建骨架、不重写材料。
- 两处不复制判据；`review.context` 的 launch 查找沿用现有 `round_no` 逻辑。

失败出口：

- launch：`WF_CHECK_STALE` / `WF_CHECK_FAILED` / `WF_APPROVAL_MISSING`，facts 保留 `check_id`、`saved`、`current`、`blockers`。
- context：`WF_CHECK_STALE`，facts 保留 `round`、`launch_anchor`、`current_anchor`，exit 指向 `task-check` 后重新 `review-launch`。

### 2.2 覆盖合并消费主会话采信

`merged_coverage` 改为接收完整主会话复核记录：

```python
merged_coverage(main_review, axis_reports) -> {
  "covered": [...], "uncovered": [...], "all_uncovered": bool,
  "sources": {axis: ["main"|slot...]}, "adopted": {...}
}
```

规则：

1. 主会话轴 `pass/fail` 直接覆盖，来源记 `main`。
2. 对每个报告槽位，从 `main_review.report_review` 取 `reliance`：
   - `none`：不贡献；
   - `primary`：该报告所有 `pass/fail` 轴贡献；
   - `partial`：仅当主会话该轴 `sources` 包含该槽位时贡献。
3. 主会话缺失时（`review-status` 投影、判定前的状态页）：报告原始 `pass/fail` 仍用于展示，`adopted=false`，`main_review_ready=false`；判定入口要求主会话复核必填，因此不会用这个降级口径产生 verdict。
4. `all_uncovered` 仍表示两源都没有真正覆盖任何轴；判定入口按输入不成立拒绝。

调用点：

- `validate_main_review` 的 `record.coverage` 用完整记录重算。
- `status_of_round` 用最近一份 main review（若存在）重算；无 main review 时走第 3 条展示口径。
- `decide` 用 `main_record` 重算；不再把 `main_axes` 与裸报告轴直接合并。

兼容性：旧 `main_reviews[]` 已含 `report_review[].reliance` 和 `axes[].sources`，可直接消费；缺字段的旧记录由 `validate_main_review` 的现有必填校验拒绝，不猜测。

### 2.3 本轮 verdict 只由未关闭 blocking 触发

新增单一派生函数（放在 `review.py`，与 `open_findings` 同源）：

```python
round_open_blocking(ctx, task, round_no, extra_dispositions=()) -> [items]
```

实现：构造一个浅拷贝任务，`reviews.dispositions = 既有 + 本次`，调用 `open_findings`，按 `round` 过滤 `blocking`。不另写关闭匹配逻辑。

`decide` 顺序调整：

1. 校验报告输入、人数/异种、主会话复核、覆盖与缺口接受。
2. 校验 dispositions 结构与 `recheck_by`。
3. 用 `round_open_blocking` 计算本轮未关闭 blocking；非空才把 `verdict` 设为 `fail`，facts 记 `open_blocking` 与报告原始 `report_failures`（保留可追溯性）。
4. 写入 `reviews.dispositions` 与 `rounds[]`。

语义：

- 误报/重分类且未改内容：`accepted` 关闭 finding，锚点不变，同一轮可重判 `pass`。
- 已修复：内容变化 → 当前锚点变化 → 旧报告导入/判定锚点失配，必须新 Check + 新轮；同一轮不会因关闭而绕过锚点。
- 旧轮未关闭 blocking 仍由归档门禁 C2 与 `repair_scope` 阻断；本轮 verdict 只消费本轮 imports 的开放项。

### 2.4 判定回显与错误码

- 缺 `--main-review`：`WF_REVIEW_INVALID`，facts 保留 `round`，exits 为 `--main-review-draft` 与 `--main-review`。
- 主会话 `fail` 无 finding：`WF_REVIEW_INVALID`，exits 为「修复后重跑 task-check」「登记 judgment 后重核」「无法覆盖改判 uncovered 交人接受缺口」。
- `review-decide` 的 `next`：
  - `pass` → `verdict=pass 后由人调用 finish`；
  - `fail` → `有未关闭 blocking：在批准范围内修复→重跑 task-check→重新发起；误报/重分类经复核登记 accepted 后可重判`；
  - `unavailable` → `按异常退出处置：暂停，或经人重新分级后按轻量完成`。
- 不改 `codes.py` 的码值语义；只改本路径的 code 选择。

### 2.5 外发声明与材料物化绑定

新增单一校验函数：

```python
scope_binding_problems(ctx, task, launch, delivery) -> [problems]
```

检查：

- `submitted_scope.diff.paths` 每项是 `delivery_set.paths` 的子集；
- `submitted_scope.requirement` 等于本任务 PRD 的相对路径；
- `submitted_scope.test_results.check` 等于当前 `task.check.id`；
- `submitted_scope.diff.diff_base` 若给出，等于 `task.baseline_head`（或为 `None` 时按基线）。

`write_materials(ctx, task, round_no, anchor, materials_dir, paths=None)`：

- `paths` 缺省取 `delivery_set`（兼容旧 launch / 旧任务）；
- `context` 从 launch 取 `submitted_scope.diff.paths` 传入；若缺失，回退 `delivery_set` 并在 facts 标 `legacy_scope=true`；
- `materialize_delivery` 仍用同一实现，base 仍取 `task.baseline_head`。

报告输入面：

- `report_input_problems(payload, task=None, text=None, launch=None)` 增加可选 `launch`；
- 当 `launch` 存在时，报告 `read-scope` 的每个模式若命中 `launch.exclusions`，追加 `read-scope-outside-launch` 问题；
- `lint_report` 不传 launch（保持只读、无任务上下文时仍可用）；导入与判定传入 launch，三处共享实现不分裂。

### 2.6 版本与发行

- `docs/workflows/wf/README.md` 目标版本改为 `0.1.3`，删除失实的 tag 句，改为「本轮重建后由人创建 `wf-v0.1.3`；此前 `0.1.0` 曾对应不同内容，不再复用」。
- `scripts/build-wf-release.py`：
  - `--version` 前读 README 的「目标版本」行，解析首个反引号版本，要求等于 `--version`；解析失败即 `BuildError`，不静默。
  - `--version` 前执行 `git tag --list wf-v<version>`；存在即拒绝（除非新增显式 `--allow-existing-tag`，默认不提供）。
  - `--verify` 仍按现有清单版本重建；不触发 tag 守卫。
- 重建 `docs/workflows/wf-release/` 为 `0.1.3`；不建 tag、不提交。
- `dev-manifest.json` 保持 `0.0.0-dev` 占位，版本源唯一在 `--version` 与 README。

### 2.7 设计稿 §1.1 判据补全

在「判据句」段末补两句（不新增定义、不新增层级）：

> 可计算只是进入机制的条件，不等于设成硬门禁；是否阻断取决于它保护哪条明确承诺，结构事实可以只作 `facts`/`next` 输出。需要人承担的明确残余风险（覆盖缺口、审查不可用、任务降级）也属交人，而不只是改变目标、承诺或授权边界。

同步：

- §8.2「审查覆盖缺口」行的待决事实改为「未被主会话复核或未被主会话采信的报告覆盖」；
- 索引 #109「固定流转程序化」的语义消费点补「§6.5（覆盖判定与硬门禁边界）」并说明理由；
- 机制稿 §0.1 追加 2026-11-20 修订摘要；
- 运行 `scripts/validate-wf-design.py`。

## 3. 数据流与兼容

```
task.check ──check_validity──> launch (valid? -> record anchor)
                                  │
                                  ├─ review-context: launch.anchor == current? -> materials(submitted_scope)
                                  │
review-import ──report digest + anchor──> imported
                                  │
main review (_main-review) ──reliance/sources──> merged_coverage
                                  │
dispositions (_plan) ──open_findings──> round_open_blocking ──> verdict
```

- 旧 launch 缺 `submitted_scope`：`context` 回退 `delivery_set`，facts 标 `legacy_scope=true`；不拒绝在途轮次。
- 旧主会话复核缺 `reliance`/`sources`：现有校验已拒绝；不新增兼容分支。
- 旧 `reviews.result` 的 `verdict` 不重写；新判定按新规则产生新 `result`。
- `review-status` 在无主会话复核时展示报告原始覆盖，并明确 `main_review_ready=false`；有主会话复核时展示采信后的覆盖。

## 4. 权衡

- **严格 reliance 可能让某些轮变成全未覆盖**：这是有意的——主会话不能一边说「不采信」一边用报告过关。出口是主会话补轴、改 reliance 为 primary/partial 并写依据，或人接受缺口；不是新增轮次上限。
- **同一轮误报关闭后可 pass**：依赖「无内容变化 → 锚点不变」；一旦内容变化，旧报告锚点失配，必须新 Check/新轮，不能借关闭绕过重查。
- **不实现 upgrade**：第三轮能力，涉及三方合并、本地偏离、维护写者与提交令牌；本轮只保证新版发行身份可重建，避免把半成品 upgrade 伪装成可用。
- **不改 `task-attribute`**：批准面内未提交路径已由 touch_paths 归入交付；面外路径的正确出口是回 Plan 扩范围，不是归属命令。

## 5. 回滚

- 代码/文档修改可按文件回滚；无数据迁移。
- 发行树重建是生成物，可回退到 `0.1.0` 的已提交字节。
- 不创建 tag，回滚不涉及远端引用。
- 若严格 reliance 在测试中暴露设计冲突，回退到「只拒绝主会话全未覆盖 + 全部报告 reliance=none」的窄口径，并记录冲突事实，不静默放宽。