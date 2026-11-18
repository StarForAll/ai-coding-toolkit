# 收口 wf 测试运行器的候选身份、证明与终态

## 目标

让 `scripts/tests/wf_runtime/full/` 的全量、子集、候选和独立 repro 入口准确报告实际验证的发行提交、可复用的相位证明、业务断言及运行终态。对已确认问题和同一判定的其他调用者一起修正，每项都有能使旧实现失败的行为用例。任务处于 `planning`，方案经用户明确批准后进入实施。

## 背景

上一轮契约和集成回归已覆盖正常运行、部分监督故障和目录恢复。此次以当前源码、命令清单入口及内存探针定位相邻边界。证据基线为 `b84b1a56`，历史集成记录在 [validation.md](../archive/2026-11/11-16-wf-runner-lifecycle-contracts/validation.md#L15)。本轮规划期间的通过条件仅针对方案工件。

## 需求

| 编号 | 确认的问题与证据 | 必须交付的行为 |
| --- | --- | --- |
| R1 | 模板缓存键按内容主体，安装记录带 `source_commit`，克隆检查只比版本和 ref。候选结束校验依赖 repro。当前两个 dev 入口都在受监督链内独立取锁。见 [模板缓存](../../../scripts/tests/wf_runtime/full/template_cache.py#L56)、[模板检查](../../../scripts/tests/wf_runtime/full/template_check.py#L49)、[安装记录](../../../docs/workflows/wf-release/install.py#L1085)、[候选结束检查](../../../scripts/tests/wf_runtime/full/repro/repro_select.py#L547)、[full dev 取锁](../../../scripts/tests/wf_runtime/full/release_context.py#L182)、[独立 repro dev 取锁](../../../scripts/tests/wf_runtime/full/repro/run.sh#L196) | dev 和 candidate 的 full（含 `--repro none`）及独立 repro 由各自的外层 controller 持同根发行锁，从准备持续到收尾。dev 只准备一次。候选准备、夹具、报告和结束核验使用同一经验证的候选身份。候选 meta 的有效参数必须指向既有 sidecar。 |
| R2 | `local_cleanup=failed` 时相位可以保留目标 `rc=0`。现有 writer 仍可保存 red，下一次 `auto` 降为 `green`。见 [相位清理](../../../scripts/tests/wf_runtime/full/execution.py#L1321)、[相位结果验证](../../../scripts/tests/wf_runtime/full/repro/repro_select.py#L515)、[证明合并](../../../scripts/tests/wf_runtime/full/repro/repro_select.py#L585) | proof 只接收本代、相位证据齐全且清理已确认的用例。旧证明无法补足缺失的清理依据，重新验证后才能用于 `auto`。 |
| R3 | full trap 调用未定义函数，full 和 repro 内层各自删除取消文件，controller 收尾不消费已锁存的信号。见 [full trap](../../../scripts/tests/wf_runtime/full/run_all.sh#L291)、[repro 标记与 trap](../../../scripts/tests/wf_runtime/full/repro/run.sh#L256)、[controller](../../../scripts/tests/wf_runtime/full/execution.py#L1694) | C 指定本代唯一取消标记。内层只在收到信号时发布请求。取消到达成功提交边界前，后续调度停止、清理只收口一次、退出非零并保全真实清理事实。 |
| R4 | 独立 `--list --fixture-deploy candidate` 在无外来 WF 环境时实际退出 1。独立执行的摘要从外层环境与默认值取 `fixture_deploy` / `repro_mode`，候选 fallback 无提交。见 [列表](../../../scripts/tests/wf_runtime/full/repro/run.sh#L73)、[外层上下文](../../../scripts/tests/wf_runtime/full/execution.py#L1474)、[摘要](../../../scripts/tests/wf_runtime/full/results_summary.py#L392)、[独立发行身份](../../../scripts/tests/wf_runtime/full/repro/repro_select.py#L201) | 清单只做选择。发行准备、内层执行和摘要依同一已核执行计划。full 和独立 repro 的 `summary.json` 必须输出候选提交和 repro 相位统计，内嵌结果归入父摘要。原 CLI、输出列形状和子集约束继续受测。 |
| R5 | D1-3、R84 无绑定恢复、R67 恢复义务检查会在实际值不成立时输出 PASS。见 [D1](../../../scripts/tests/wf_runtime/full/d1_tests.py#L52)、[R84](../../../scripts/tests/wf_runtime/full/r84_tests.py#L118)、[R67](../../../scripts/tests/wf_runtime/full/r67_tests.py#L205) | 这三条及 full 注册用例中有同一缺陷的断言都核实际结果。调试展示或已有真断言的重复行不得计入独立断言覆盖。保持每条有效断言与注册数量相符。 |

## 验收

- [ ] **A1（R1）** 核对 dev 和 candidate 的整次运行锁持有链及发行身份。
  - **候选模板与终核**：A 和 B 使用同版本、同 tag、同内容及不同提交，共用同一空模板缓存。A 建立条目后，B 首次运行必须冷构建，B 的新装和复制夹具均带 B 的 `source_commit`。重跑 B 命中 B 的热模板。持久的提交变化阻断结束校验，覆盖无 repro、内嵌和独立入口。
  - **租约与准备**：dev full 和独立 repro 均完成冷构建、同输入复用与 `--no-build` 校验，每次整次运行只调用一次发行准备。内嵌 repro 复用父租约和 context。同一外层 controller 的 PID 与锁 inode 可从准备核到收尾。dev 和 candidate 各测真实同根竞争，独立 repro 覆盖相邻 case 间隔，整次正常结束后锁可重获。无有效租约或租约错根时，`--no-lock` 在任何发行写入前拒绝。
  - **候选 meta**：full 和独立入口中，有效 `--release-meta` 或 `WF_RELEASE_META` 指向其他文件都应非零退出且未启动 worker。CLI 显式 canonical 路径可覆盖冲突环境值并正常通过。
- [ ] **A2（R2）** 相位日志包含预期 PASS 但相位清理失败、收据缺失或来自旧代时，不为该相位更新证明，随后 `auto` 必须重做所需 red。显式 KEEP 场景保留真实路径，proof 和自动轮转均不放行。完成且清理的当前相位可保存；既有独立用例的部分通过语义有对照。已有 v4 状态按历史读取，不能直接命中。注入 state 读失败、落盘失败及 rename 失败，旧文件字节不变，原来无文件则仍不存在。下次 `auto` 按原有状态判定，若状态持续不可读则明确拒绝。
- [ ] **A3（R3）** 无信号的 full 和独立 repro 启动不创建取消标记。内嵌 repro 与主池重叠启动时保留已有标记的 inode 和内容，也不在自己的结果目录创建替代标记。向内层目标和外层 controller 发取消信号，并以确定性测试覆盖实际收尾、最终决策前后，核对停止调度、rc、`GATE-OK`、run-state、一次清理及无误复用。正常退出和既有监督故障回归。
- [ ] **A4（R4）** dev/candidate 的 `--list` 在干净环境按组、子串及候选资格返回稳定清单，全程零写入。对计划 token、代次、路径或文件内容不符做反向用例，验证 C 拒绝取发行锁，内层拒绝启动 worker，后续 evidence 不接受计划绑定错配。逐字段核对 `summary.json` 的 `fixture_deploy`、`repro_mode`、`candidate_commit`、`repro_phase_counts`，覆盖 CLI 覆盖环境、`both`、混合 `auto` 与无 repro。候选成功摘要的 commit 等于 validator 核实的 tag commit，dev 为 null。未报告的相位不能计为通过。
- [ ] **A5（R5）** 逐条核销硬编码通过清单。D1 给空结果或错误码、R84 恢复结果或对象身份错误、R67 义务为空时，各自变红，正常路径通过。影响审计证据的 suite 由生成器重跑；登记数量任何调整均对应真实行为变化。
- [ ] **A6（R1–R5）** 通过定向契约、通用回归、full 串并对拍、双相位及候选集成。按用例 ID 校验证据归属，保存首次失败、修复后通过及边界对照的验证记录。确认产品发行树和宿主管理路径符合既有写入边界。

## 范围

实现限定为作者侧运行器、其实际调用的发行与模板 helper、相关测试和相邻契约说明。运行性能维持合理现状，验收关注正确性。产品 payload、已发布发行树、产品业务判定、平台支持、广泛重写历史套件与旧缓存批量清理均在本任务范围外。
