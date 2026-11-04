# 第二十六 / 二十七轮：P2-6、P2-7 与 P3 的收尾

- 处置编号 R63（P2-6、P2-7）、R64（P3 九条）
- 实跑见 `validation.md` §49、§50

## 0. 结论

上一轮登记的待修项全部落地，无新增契约缺口。P2-6/P2-7 为机制义务补实现；P3 九条为改进项，逐条给出处置。

## 1. P2-6 日志与 facts 的秘密边界（R63）

- `check.redact_secrets()`：按 `key=value`/`token:`/`Bearer`、`sk-`、`gh*_`、`AKIA` 形态把值换成 `***`。
- `_run_argv` 对**摘要与 argv** 都过一遍，日志文件与 `evidence` facts 写的都是脱敏结果。
- 边界：只认形态，不判定「什么算秘密」；不可识别就原样保留——比漏遮更安全的只有「整段丢」，那会毁掉排障价值，故保留原文并在此写明。

## 2. P2-7 副本来源登记（R63）

- 六个改编副本（grilling/tdd/diagnosing-bugs/code-review/review/review-action）各自 `SKILL.md` 末尾新增「来源与差异」段，登记来源、许可、基线、差异、最近正例、最近反例（设计稿 §7.4）。
- 模块 README 增 §6：列出改编件与原创件，写明审查两副本的适配源是一次性的、上游不自动流入（设计稿 §7.5）。

## 3. P3 九条（R64）

| 项 | 处置 |
|---|---|
| 源树 `__pycache__` | 清空并在 `.gitignore` 加 `docs/workflows/新项目开发工作流/**/__pycache__/` |
| `cmd_spec` 正文重复 | json 模式 `facts.content` 置 `None`，非 json 模式仍渲染正文（§2.4 输出契约） |
| 窄写入不 bump | `_sync_curation_paths`、`_release_dependencies` 均 bump `revision`/`updated_at` |
| `stop` 强制 subject 列路径 | 无未提交差异时允许空 subject；有差异仍要求列路径 |
| `transfer` 取 `paths[0]` | 首项必须匹配任务 id 形态，否则 `WF_SEMANTIC_DECISION` |
| `cmd_bind` 死代码 | 改为显式 `isinstance(generation, int)` 且非负，`startup_check` 的记录面同样修正 |
| skill description 写法 | `wf-continue` 改为触发词前置并列出子动作 |
| `evaluate` 静默 KeyError | 未知 step 汇总成 `__unknown_steps__` unknown 条目 |
| 启动侧复评触发 | `startup_check` 在 graph 面附 `_reassess_empty_set` 事实（首轮空集合合法，第二轮接触发） |
| `rules_digest` 多份实现 | 新增 `scripts/tests/wf_runtime/test_rules_digest_parity.py`，比对 install 与运行时两份独立实现 |

## 4. 影响

无状态值/原因码/字段/哈希域变更；`cmd_spec` 的 facts 收缩属输出契约对齐。回归含全部 31 套与三夹具、F0、两组 `unittest`（新增 2 条）。
