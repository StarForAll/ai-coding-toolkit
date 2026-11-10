# 机制测试映射（v42 §5.2 的"72 条"对照）

> 说明（如实）：本表是**族级映射**，不是 v42 那条 72 条清单的逐条 1:1 对照。族内每条用例的
> 断言与"它防的失败"写在用例 docstring 里。逐条 1:1 对照需要把 v42 第 331 行那段清单拆成
> 72 个可机检条目——那是下一轮的事，本表先把"哪一族有对应证据、哪一族没有"摆清楚。

## 覆盖总览（213 条用例）

| 机制族 | 用例数 | 落点 |
|---|---|---|
| 6 条不变量 + §7.1 回流守卫 | 7 | `wf_protocol/test_invariants.py` |
| K1 身份（四档→宿主优先/锚兜底、`/clear`、冲突钉住、部署表） | 12 | `wf_identity/test_identity_lease.py`、`test_deployment_table.py` |
| K2 租约（live/superseded/gone/unknown、接管 bump、旧代次失效） | 9 | `wf_identity/test_identity_lease.py`、`test_identity_store.py` |
| K3a/K3b 锚点（内容指纹、assertions_digest、实质字段、失配列差异） | 4 + 17 | `wf_review/test_assertions_digest.py`、`test_review_gates.py` |
| K4a/K4b/K4c 报告（不可覆盖、关闭不自证、规则不自证、broken-reference=声明+人复核） | 17 | `wf_review/test_review_gates.py` |
| S3 判定句 / lint 一次列全 / `d:` 只认 active | 5 | `wf_review/test_lint_report.py`、`test_review_status.py` |
| S6 收敛谓词（blocking 无处置、required 未核实） | 6 + 18 | `test_open_findings.py`、`test_projection.py` |
| S9 到位状态 | 8 | `test_review_status.py` |
| §5 判断清单（append-only、引用只认骨架 id、预览计数、`[补]`） | 9 | `test_judgments.py` |
| §0.2 抽样（可复算、预算、首任务、强化义务、漏报补写、期满） | 12 + 10 | `test_sampling.py`、`test_scale_and_backfill.py` |
| 4.6 规模事实托底 | 10 | `test_scale_and_backfill.py` |
| K5 vendor 边界 | 4 | `test_vendor_boundary.py` |
| K6/K7 授权、脱敏、三段提交 | 17 | `test_authorization.py` |
| K8 投影/缓存漂移、K9 提交三态/链头、S5b 未核实项 | 18 | `test_projection.py` |
| 打包工具（预检早于删树） | 2 | `test_build_wf_release.py` |

## 明确没有对应证据的（不许当成已覆盖）

| 项 | 缺什么 | 谁补 |
|---|---|---|
| §5.2 的 72 条逐条对照 | 清单未拆成可机检条目，族级映射不能替代 | 下一轮 |
| §5.4 的 **10 个场景演练** | 只做了「顺序两任务」与部分 `/clear`；其余 8 个未端到端跑 | 下一轮（临时夹具） |
| P3/P4 的端到端退出判据 | "复杂任务跑完零返工""归档后工作树干净"未实测 | 随场景演练一起 |
| `/clear` 的真实宿主证据 | 只有用户口述（codex 实测变化、dsh 无该命令） | 人 |
| 证据 tar.gz 入库 | 被全局 `*.tar.gz` ignore 挡住 | 人裁 |
