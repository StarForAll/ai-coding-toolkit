# 校准 wf 候选发行证据与回归结果

## 目标

发行验收能回答实际测试了哪份候选，日常回归能在干净的输入下复跑，失败结果能区分已验证的断言失败和证据缺失。四项修正按可观察反例验收，方案获用户批准后进入实施。

## 需求与证据

| 编号 | 当前行为与影响 | 要求 |
| --- | --- | --- |
| R1 | [R70](../../../scripts/tests/wf_runtime/full/r70_tests.py#L59) 属于 T3 候选代表集，却使用作者安装器和固定 `wf-v0.1.0`。R69 同类，R89 使用候选安装器但固定 ref。[CP5 B12](../../../scripts/tests/wf_runtime/full/cp5_b12.py#L5) 的 F2 次级夹具通过 `f2_setup.sh` 开发态部署，并被标为候选合格，可能让候选审计实际测试作者库。 | 以发行产物为断言对象的路径统一消费本次已核发行，并核次级 fixture 的实际安装记录。作者侧行为保留相应验证。已有代表集和全量覆盖意图不变，实质断言逐条有去向。 |
| R2 | [增量审计](../../../scripts/tests/wf_runtime/full/candidate_audit.py#L253) 横跨发行保留旧行的条件未核验，[现有检查](../../../scripts/tests/wf_runtime/test_source_coverage.py#L142) 分别核对报告头和脚本。当前记录无跨发行混用证据。 | 旧行只在发行身份和相关测试输入均可核验且一致时复用。未知或不可审计的 ID 整次拒绝，指出应改用的已登记选择。身份或旧证据不符时保全原报告，并给出完整重跑出口。 |
| R3 | [串行及回退](../../../scripts/tests/wf_runtime/full/run_all.sh#L599) 使用宿主 `/tmp`。[R70 决策文件](../../../scripts/tests/wf_runtime/full/r70_tests.py#L10) 等套件自造材料存在固定路径及旧输入复用。 | 托管套件和初始化步骤按次创建测试材料。并行、串行、回退及审计使用相同归属策略。显式选用并已核验的发行、缓存及合法宿主配置继续按既有契约消费。 |
| R4 | [单元结果行](../../../scripts/tests/wf_runtime/full/run_one.sh#L64) 的 `bad` 同时表示夹具准备失败和测试进程失败，[gate](../../../scripts/tests/wf_runtime/full/results_gate.py#L54) 还会把非零退出或空尾行标为 bad。`runner_cleanup` 当前仅以 `gate.ok` 区分证据完整性。 | 分别归类已核断言失败、准备失败、测试进程失败和无法判定。任何 `bad` 行都不能单独证明断言失败。结果结构完整性与监督/本地清理独立表达。repro 的断言结论也须先核本代执行证据。 |

## 验收

- [x] A1（R1）非 `0.1.0` 候选通过真实 T3 代表入口和候选全量，核对 f0、R70 次级安装、CP5 的 F2 次级 fixture、install repro 及全量其他发行相关断言的实际安装身份。CP5 候选安装前后须验证其 legacy 数据、Git 历史和初始化前置仍满足 B1/B2。候选合格用例的实际 release 来源有运行证据，不能仅凭 suite 退出 0 或脚本文本判断。用当前发行跑候选代表入口并显式跑 dev full。覆盖缺身份、错 ref 或错来源拒绝。
- [x] A2（R2）同身份增量成功。脚本相同而候选内容、helper/runtime/tree 输入或待保留行摘要变化，旧格式不可验证时，拒绝合并并保全原字节。未传 `--only` 表示完整审计。覆盖 `--only ""`、未知 ID、已知与未知混合 ID，拒绝均发生在启动套件前。当前发行完整审计逐 ID 核对登记和实跑结果。candidate-clean ID 必须实跑 ok；non-candidate ID 的 bad 必须有具体断言并保持候选排除。
- [x] A3（R3）首次和第二次串行运行均不得消费伪确认、旧审批/notes/init JSON、CP5 的 `/tmp/cp5_a.json`、旧报告、旧测试输出或固定 release-repo 回退内容。并行、显式串行按 ID、断言数和结论对拍。以仓库位于 `/tmp` 的现有自动回退分支确定性验证 `repository-under-tmp`，不靠打印文本单独验收。固定路径扫描结果全部分类，并由回归守卫覆盖。显式候选或缓存仍经原身份校验和锁，runner 不改写或回收。
- [x] A4（R4）准备失败、目标测试退出非零、明确断言失败、断言数量不完整/无断言输出、结果结构缺失，分别有真实结果与分类对照；每类再覆盖清理成功和未知/失败。明确断言失败仅当目标正常退出、完整断言计数和失败记录一致时成立。summary 增加可选 `unit_outcomes`，为每个计划单元保存 typed outcome，同时保留现有 bad/rows 聚合值和 status/failure_kind 语义。repro 缺本代收据或清理未确认时记 `unverified` 且不可写 proof。准备失败可被分类为 preparation failure，但不得记成 assertion failure。通过、旧摘要读取和退役授权继续回归。

R4 outcome 的有限值为 `passed|assertion_failed|preparation_failed|execution_failed|cancelled|unverified`。断言失败判据和 execution/preparation failure 判据不得只依赖 summary 的 aggregate `bad`。

## 范围

作者侧运行器、相关用例、审计记录及必要用法。临时候选在受控目录构建，产品实现和生成发行树保持原样。性能优化、缓存与监督协议重构、扩大候选覆盖和历史材料批量清理属于独立工作。按 A1–A4 收口，新发现仅在会改变本轮结论、来源证明、清理安全或损害既有调用方时纳入。
