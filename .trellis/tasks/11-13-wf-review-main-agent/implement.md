# 实施清单：wf 审查判定与指引一致性修正

> 顺序：先审查核心（D1/D2），再旧口径（D4），再 §1.1（D5），最后文档/发行。
> 每个阶段结束跑对应测试；最后跑全量测试、设计校验、skill 校验与发行树校验。

## 0. 准备

- [ ] 确认工作树干净、基线 `5a55c398`；记录 `git status --short`。
- [ ] 跑基线：`/softwares/python/bin/python3 -m unittest discover -s scripts/tests/wf_review -t .`、`.../wf_runtime -t .`。
- [ ] 只改 `docs/workflows/wf/` 源树、`docs/workflows/wf-framework-*.md`、`scripts/tests/`、`docs/workflows/wf-release/`（生成物）；不改目标项目。

## 1. 主会话复核（D1）

### 1.1 `review.py`

- [ ] 新增 `MAIN_REVIEW_FIELDS`、`MAIN_REVIEW_AXES = REVIEW_AXES`。
- [ ] 新增 `validate_main_review(payload, *, task, round_no, imported, open_blocking)`：
  - 核 `task/round`、五轴、`conclusion`、`basis`、`sources`；
  - 核 `report_review` 覆盖每个已导入槽位、`reliance`、`notes`；
  - 核 `finding_review` 覆盖每条 finding（复用 `disposition_keys` 的歧义处理：同 id 多槽位需 `slot`）；
  - 核 `fail` 轴的 `finding_refs` 指向本轮未关闭 blocking；
  - 返回 `(record, problems)`，record 含 `file_digest`/`by`/`at`/`coverage`。
- [ ] 新增 `merged_coverage(main_axes, report_axes_by_slot)`：按 D1 公式返回 `{covered, uncovered, all_uncovered, sources}`。
- [ ] 新增 `main_review_draft(ctx, task, round_no)`：生成 D1 形状的待填骨架（`reliance: ""`、`check: ""`、`sources` 预填报告覆盖槽位）。
- [ ] `decide()`：
  - 产生 verdict 前要求 `main_review_path`；否则 `WF_SEMANTIC_DECISION`（给 `--main-review-draft` 出口）。
  - 校验复核；失败 → `WF_REVIEW_INVALID`（problems）。
  - 覆盖改用 `merged_coverage`；`all_uncovered` → `WF_REVIEW_INVALID`；部分缺口走现有 `gap_acceptance`。
  - 追加 `reviews.main_reviews[]`；同轮不同摘要 → `WF_REVIEW_INVALID`；同摘要幂等。
  - verdict/facts 增 `main_review`（五轴、report_review、file_digest）与 `coverage.sources`。
- [ ] `status_of_round()`：读 `main_reviews[]`，增 `main_review_ready` 与 `coverage.main_review/sources`。
- [ ] `derive_verdict()`：五轴全 `uncovered` → `unavailable`；更新 docstring。
- [ ] 删除 `review_report_problems` 的 `scope-exceptions` 循环与 `material-gaps/missing-materials` 失败分支。

### 1.2 `cli.py`

- [ ] `_review_command("decide")` 传 `--main-review` / `--main-review-draft`。
- [ ] `COMMAND_HELP["review-decide"]` 增参数、示例、`--gap-acceptance` 说明保持。
- [ ] `--main-review-draft` 分支：不产生 verdict，写骨架文件，返回 `WF_OK` + `next_`。

### 1.3 `wf-review-action` / `wf-review`

- [ ] `wf-review-action` 新增“主会话复核”步骤：逐份报告质疑、逐 finding 复核、五轴结论、`--main-review-draft` → 填写 → `review-decide --main-review`。
- [ ] 新增“pass 之后”段：纯建议取舍、准备 finish、不无限加轮。
- [ ] `wf-review`：说明报告是辅助，五轴未覆盖写 `uncovered`，主会话会补足；不要求补轮。

### 1.4 测试

- [ ] `scripts/tests/wf_review/test_main_review.py`：D1 验证清单的正反例。
- [ ] 更新 `test_review_coverage.py`：并集断言改为 `merged_coverage`；A 全 pass/B 全 uncovered/主会话 pass → pass 且 B none；主会话 uncovered + 报告覆盖 → 覆盖；两者都 uncovered → 缺口。
- [ ] 更新 `DecideHarness`：默认为测试生成合法主会话复核；支持覆盖。
- [ ] 更新 `scripts/tests/wf_runtime/*` 与 `full/repro` 夹具：在 `review-decide` 前写主会话复核（helper 统一生成）。
- [ ] 跑 `wf_review` + `wf_runtime`。

## 2. 报告边界（D2）

- [ ] `report_input_problems()` 新增 `read-scope-excluded` 检查（`match_path`/`subsumes` 双向）。
- [ ] `derive_verdict()` `unavailable` 兼容：`report_input_problems`/lint 的 declared-verdict 检查不误报。
- [ ] `review-report` 的 `read-scope`/`excluded-scope` 说明更新；删除 `scope-exceptions`/`material-gaps` 文档字段。
- [ ] `review.context()` facts 增 `submitted_scope`/`readable_scope`/`exclusions`。
- [ ] `default_launch_request()`：`readable_scope.business_code` 改项目内业务面，`focus_paths` 保留触碰面；`exclusions` 保持。
- [ ] `wf-review/SKILL.md`：diff 基准改任务基线；报告名 `review-<agent>.md`；材料不足 vs 授权不足分开。
- [ ] 测试：`test_report_input_single_source.py` 增 `read-scope-excluded`；`test_lint_report.py` 增矛盾用例；`test_launch_mechanized.py`/`test_material_baseline.py` 适配 `readable_scope`。
- [ ] 跑 `wf_review` + `wf_runtime`。

## 3. 旧口径与持续推进（D4）

### 3.1 身份/新任务

- [ ] `cmd_enable` facts 增 `binding`；`next_` 按绑定分支。
- [ ] `wf-start`：删 `bind --run`/issued 未交付；已绑定新任务出口；选对象后继续第一步。
- [ ] 部署表注释：`session_identity` 是声明、不是已安装适配层。

### 3.2 已交付能力

- [ ] `wf-start`、`wf-continue`、`instance-flow.md`、`wf/README.md`、`runs.py::next_`、`cli.py` 注释：清除 `bind --run`/`run create/advance/terminate/finish` 未交付说明；`upgrade` 保留第三轮。

### 3.3 执行器单源

- [ ] `session-flow.md` 增“运行约定（执行器）”完整段。
- [ ] 13 个 skill 替换长段为一句 + 指针；删除“审批拒绝后换解释器”表述。

### 3.4 持续推进

- [ ] `wf-continue` 首段增“在现有授权内推进至必要人判点”。
- [ ] `wf-review-action` “pass 之后”段。
- [ ] `wf-finish` 收尾：归档成功即释放；删除“按需 writer release”。

### 3.5 归档自动释放

- [ ] `cli.py` 提取 `_release_writer_locked(ctx, holder)`，`_writer_release` 复用。
- [ ] `tasks.py::cmd_archive` 持久化成功后调用；释放失败写 `write_release` facts，不把归档报成失败。
- [ ] `archive` 的 `next_` 更新；`wf-continue` 路由“归档后写权仍 held”改为“仅中断/释放失败”。
- [ ] 测试：`test_archive_writer_release.py`（成功释放、释放失败事实、中断不释放）。

### 3.6 信封缓存

- [ ] `remember_envelope` 用 `session_id`/`issued_id` 作键；缺标识不缓存。
- [ ] 测试：两个 wf 会话不共用缓存；host 会话按 session_id 隔离。

### 3.7 测试

- [ ] 跑 `wf_review` + `wf_runtime`。

## 4. §1.1 判据（D5）

- [ ] 设计稿 §1.1 “指令分工”写作规则改写。
- [ ] 设计稿 §1.1 “指引就地、不成层”判据句改写。
- [ ] 设计稿 §1.1 “固定流转程序化”语义分叉定义收窄。
- [ ] 机制稿/实现稿如有复述，改为指针或同步。
- [ ] `scripts/validate-wf-design.py` 通过。

## 5. 文档同步

- [ ] 设计稿 §6.5：主会话复核段、覆盖规则、外发范围澄清、报告字段删除。
- [ ] 机制稿 §9.1/§9.2：主会话复核记录、覆盖合并、read-scope 矛盾、删除 scope-exceptions/material-gaps；§0.1 输入摘要/变更说明。
- [ ] 实现稿 §2.2（generation）、§2.3.10（判定输入）、命令表（`--main-review`/`--main-review-draft`）。
- [ ] `docs/workflows/wf/README.md`：命令/版本说明；删除旧未交付。
- [ ] `scripts/validate-skills.sh` 通过。

## 6. 发行与收尾

- [ ] `python3 scripts/build-wf-release.py --version 0.1.2`。
- [ ] `python3 scripts/build-wf-release.py --verify`。
- [ ] `python3 scripts/validate-wf-design.py`。
- [ ] `./scripts/validate-skills.sh`。
- [ ] `/softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .` 全绿。
- [ ] `git diff` 复核：无目标项目改动、无无关重构、无凭据。
- [ ] 按 Trellis 3.3 更新 spec（如涉及交付纪律）；3.4 提交；3.5 收尾。

## 回滚点

- 1.4 后：若主会话复核引入大量夹具失败，先只回滚 D1 的 `decide` 必填，保留校验/草稿为可选，再修夹具。
- 3.5 后：若归档释放导致外部脚本失败，保留 `write_release` facts，回滚自动释放为显式 `writer release`，不回滚归档本身。
- 6 前：发行树可重新生成；不建 tag、不推送。
