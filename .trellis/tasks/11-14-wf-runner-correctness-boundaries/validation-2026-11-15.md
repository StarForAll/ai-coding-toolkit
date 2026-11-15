# 2026-11-15 实施验证记录

本轮按 implement.md 顺序实现（身份/输入 → 发行 cache → 模板 cache → 帧与阶段 → 结果域/namespace → repro 双身份与 writer），未派子代理，未改产品 payload、正式发行树与用户 cache 内容。以下**只记实际跑过的命令与结果**；未跑的边界单列。

## 通过证据（按 AC 归并）

| AC | 证据（命令 → 结果） |
|---|---|
| AC1 | `test_python_runtime_identity` 9/9；`test_test_release::InputIdentityTest`（资产/manifest/工具/dirty/HEAD 各改身份、纯 touch 不变、缺失拒绝、slot 单射）；`test_template_cache::KeyTest` |
| AC2 | `test_release_lock::JournalTest`（pending journal 只读拒绝、前滚、旧字节回滚、首次发布撤销、两代不可验证 fail closed、越界 journal）；`test_template_cache::RecoveryTest` |
| AC3 | `test_release_lock::BusyTest`（ensure×ensure、消费期×check 均 busy 退出 75、两个共享 check 共存、释放后重试、恢复也要独占） |
| AC4 | `test_release_lock::SchemaTest`（旧 meta 只算 miss）；`test_template_cache::MigrateTest`（只迁同槽位且身份完整；其他 python/deploy/version、无主不动；目标已存在不迁）；README/spec 已写抖动与清理边界 |
| AC5 | `test_run_all_contract::test_default_list_creates_no_lease_results_or_cache`、`test_dry_run_only_prints_plan`（显式目录只有 plan.json + marker）、`test_conflicting_modes_exit_nonzero` |
| AC6 | 上述 dry-run + `test_subset_runs_exactly_one_unit`（一次 preflight、lease 内一次 final plan；controller/execute 从冻结节执行） |
| AC7 | `test_repro_selection` 25/25（green 不签 red、helper/source/target 变化失效、candidate auto 同主体同 release 才 green、无证明/异 release 拒绝）；`test_run_all_contract::test_candidate_auto_requires_and_then_uses_matching_dev_red`（先拒绝，补 dev red 后 3/3 candidate green） |
| AC8 | `test_results_gate` 12/12（bundle token 不符、结构矛盾、verified 与相位冲突）；`test_repro_selection::CommitTest`（token 变化、context 变化、缺失/畸形结果阻断 writer） |
| AC9 | `test_repro_selection`（schema 1/2 legacy 保留且不复用、损坏不覆盖、green 不刷 red 的相位独立性） |
| AC10 | T0 961 tests OK（skip 13 慢测）；定向 r67 17/17、r70 5/5；`--full --repro green` 149 项 0 失败（并行 57s / 串行 281s，两次均 GATE-OK）；并行/串行 `lines`（名称/rc/status）与 85 个 repro 结果的 case/mode/verified/green/red 逐项无差异 |
| AC11 | 真实嵌套 repro（`--repro green --repro-group writer` 7/7、candidate install 3/3）在默认构建与 `--no-build` 下都只走 inherited frame；`execute_gate` 单测覆盖 context 缺失/篡改/root/version/ref 不符、坏 plan、伪造租约 |
| AC12 | `test_fixture_scope::TestScopeTest`（scope marker/结果锁域/继承/伪造拒绝/越界拒绝）；镜像零写与显式镜像最小写测试；`execute_gate::test_tampered_or_truncated_plan_is_refused` |
| AC13 | 同上 scope 用例 + 单测里的生产路径桩（真实 full fixture 慢测仍走既有独占前提，contract 套件整体通过） |
| AC14 | 并行 full 跑含 r67（unit domain + 自建 scope）；`namespace.py` 关闭继承宿主 FD、清 locator、标 unit 域；生产 helper 域不符拒绝 |
| AC15 | `test_results_gate` 证明 gate 不写 state；R→G→S 真实子进程链在 repro 运行中提交（state updated，见 AC7 运行）；writer 无/伪造租约拒绝单测；candidate 起始 dirty 工作树 `test_candidate_dirty_worktree_fails_the_start_barrier` |
| AC16 | `test_runner_protocol` 13/13（round-trip/空格中文/未知/重复/漏字段/缺分隔符/保留注入/CLI eval）；真实链上三次重入只两次 plan |
| AC17 | 冷/暖账目：full 计时行 template=2s、build 命中 0s；类内 scope/repro 每调用独立 results；cancellation 契约用例仍绿 |
| AC18 | `test_fixture_scope` 新增"scope 内项目外兄弟目录合法 / scope 外拒绝"；既有 r7r15 escape 套件在 full 中通过；README/spec 写明 scope 不是 syscall 沙箱 |

## 文档与发行校验

- `scripts/build-wf-release.py --verify --verify-token-parity` → rc 0（0.1.2，74 assets，字节复现；产品树未被测试改写）
- `scripts/validate-wf-design.py` → rc 0；`scripts/check-doc-refs.py` → 0 problems；`./scripts/validate-skills.sh` → rc 0

## 未覆盖 / 明确边界

- D1 真实宿主压缩仍手动，不计入自动分母；`WF_SLOW_TESTS` 之外不跑 slow/契约。
- 生产域 busy 用桩而非真实另一 UID 进程（同机单用户环境）；mount namespace 行为由并行 full 的真实 unshare 覆盖，未另造外部独立 `unshare` 域。
- 断电级 durability 与同 UID 恶意 TOCTOU 不在威胁模型（PRD Out of Scope）。
- 新增身份核验成本实测：单次 build inputs ~0.04s、模板身份 ~0.10s，均只发生在两个 barrier 级，不在 per-case 循环内；full 未出现逐 case 重扫。
