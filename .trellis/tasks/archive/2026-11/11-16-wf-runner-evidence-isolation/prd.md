# wf 测试证据、隔离与发行边界修正

> 状态：实施完成（2026-11-16），待最终人工审查；未提交。
> 基线：`b74d60101bf874f7940af1e20dd1aa73eb8a6ee3`；创建任务前工作区干净。
> 实施与验证证据见 [validation.md](./validation.md)。

## Goal

修正 wf 测试运行器及关联脚本中可由脚本解决的隔离、证据、缓存、结果交付和进程清理问题，使成功结论对应本次实际执行，并保留此前提速成果。以公共契约及其所有调用方一起修正，避免只处理某个入口或增加绕过分支。

## 实施结果与已登记偏差（2026-11-16）

- R1–R10 已按本 PRD 与 [design.md](./design.md) 实施；AC01–AC22 的逐项证据见
  [validation.md](./validation.md)。candidate 逐 suite 审计见
  `scripts/tests/wf_runtime/full/candidate-audit.json`（由 `candidate_audit.py` 可复现生成）：
  59 suite 中 56 个通过并提升 `candidate_clean=true`；r67 为 fake-tree runner 技术审计，
  r90/p5_v1 保留 dev-only 并记录具体失败断言。
- **Goal 偏差（已登记，不再作为完成阻断）**：Goal 的“保留此前提速成果”未完全保住。本轮
  保留证据的 cold full green 并行为 ext4 **72.74s**，相对上一任务存档 cold **52.8s**（
  `.trellis/tasks/archive/2026-11/11-15-wf-runner-boundaries-followup/validation-2026-11-15.md:77`，
  `verification-2026-11-16.json:30`）回退 **+37.8%**；历史 tmpfs 66.28s 也有留存，但存储/负载未做
  同轮 A/B，只作量级参考。本轮串行 ext4 417.25s 是全新冷 scope，不能与存档 reused release/template
  的 268.2s 直接比较。该偏差来自新增 C→G→S→W 命令监督、公共 helper 身份、命令级 cleanup 聚合与
  审计测试；没有硬失败门槛，按本轮审查口径接受为交付偏差。
  若后续要求恢复原速，应另立优化项，不在本任务内用跳过校验或降低覆盖换取。

## Background / 已确认事实

前序只读分析通过内存反例确认：scope 可接受尚不存在的越界路径、测试发行缓存未完整纳入 scope；red 可凭错误相位日志签发证明；解释器变化可能不改变 red 身份；摘要命令失败未必影响最终 rc；候选内容不符可能误报 REUSED；结果校验有 NameError/UnboundLocalError。内存反例只证明这些路径的逻辑缺陷，不替代真实回归，也不说明历史运行已经发生错误。

另有三类覆盖限制：宿主快照仅顶层元数据不足以证明子树终态不变；脱离 session 后代的清理目前仅有静态风险推断；candidate 声明范围小于源码回归范围。产品安装器技能根链接写穿是仓库已有 known-gap，当前请求将其纳入脚本修正范围。

## 用户约束与范围

- 本轮只创建 Trellis 任务和规划材料，不修改实现、产品发行树或配置，不执行实现级测试。
- `prd.md`、`design.md`、`implement.md` 完成后交用户审查；收到对最终方案的明确批准才可启动实施。
- 所有 R1–R10 都在本任务内处理；不能将脚本可解决的缺口改名为“外部条件”而遗留。
- 不提交、不推送、不创建 PR；不改官方 Trellis 上游；Codex inline，不派发子 agent。

实现范围：`scripts/tests/wf_runtime/**`、`scripts/tests/wf_test_release.py`、`scripts/wf-dev-deploy.py` 及相关作者侧路径/身份/锁 helper、`docs/workflows/wf/payload/install.py`、`docs/workflows/wf/payload/bin/uninstall.py`、必要测试和直接相关 README/spec。正式发行树只能由构建器生成。安装行为修正遵守既有产品边界，不顺手变更产品政策或工作流。

## Requirements / 问题与归属

表中 `FULL` = `scripts/tests/wf_runtime/full/`，`REPRO` = `FULL/repro/`，其余作者测试在 `scripts/tests/wf_runtime/`；锚点基于上面的固定基线。

| ID / 判断 | 要求 | 证据与事实边界 | 验收 |
|---|---|---|---|
| R1 / 高，成立 | 一个公共规则负责管理路径解析、scope 默认值及首次写入前校验，包含发行/candidate/pycache 和 sidecar | `FULL/fixture_scope.py:383`、`FULL/run_all.sh:110`、`FULL/plan.py:550`；不存在目标的内存反例已确认 | AC01–02 |
| R2 / 高，成立 | 请求相位、日志证据、worker/gate/writer 采用同一判定 | `FULL/execution.py:172`、`REPRO/repro_select.py:454`；错误 red 日志的 gate 与模拟 writer 均通过 | AC03–04 |
| R3 / 高，成立 | tool/SUT 的完整运行身份进入 context/red subject，旧证明不得冒充新证明 | `REPRO/repro_select.py:137`、`scripts/python_runtime_identity.py::resolve`；二进制/SUT 版本变化仍复用 red 的内存反例成立 | AC05–06 |
| R4 / 中，成立 | 成功包括清理与摘要交付；原子发布/读回失败必须非零，无 GATE-OK | `FULL/run_all.sh:852`；原收口段模拟前命令失败后最终 rc=0 | AC07–08 |
| R5 / 中，成立 | ensure/check/发布后共用完整候选身份校验，安全复用/重建 | `FULL/prepare_candidate_repo.py:154`；输入 A/候选 B 返回 REUSED；现有下游 check 会拒绝，不夸大为完整运行假绿 | AC09–10 |
| R6 / 中，成立 | 输入读取/解析/结构错误稳定非零归因，异常处理不再次异常 | `FULL/results_gate.py:75`；默认 bundle 与坏 JSON 的两类内存异常已确认 | AC11–12 |
| R7 / 覆盖不足，成立 | 宿主子树终态对拍和检测器自证，不能只比较顶层 inode/mtime | `test_run_all_contract.py:52`；快照不声称覆盖“中途写后恢复” | AC13–14 |
| R8 / 原遗留风险为推断，监督故障契约缺口成立 | 启动/取消/失联与 S 死亡接管共用命令归属协议；S 崩溃或 SIGKILL 且 G 存活时必须回收其后代与 FD/锁 | `FULL/execution.py:42,99–125`、`FULL/run_all.sh:268`、`REPRO/run.sh:239`；前版方案只有 S 存活时的清理，没有 S 死亡后的责任方，现明确专用 G；本轮不宣称已实跑未来监督器故障 | AC15–16 |
| R9 / 证明范围不足，成立 | 核实实际测试来源、迁移可迁移行为项，candidate 禁止源码回退，补安装行为断言 | 规划基线：`FULL/units.json` 共 67 单元，其中显式 candidate_clean=false 为 62（59 suite、1 extra、2 manual），true 为 1，4 flow 未声明（实施后分布见 [清点依据](./inventory.md) §2.1）；`REPRO/repro_select.py:60,253` 定义可发现全集及选择，基线 85，分组仅覆盖其中 54；`REPRO/groups.json` 声明 3 个候选 repro；完整来源见 [清点依据](./inventory.md)；`FULL/wfdrive.py:18` 已支持发行库优先，`FULL/f1_candidate_smoke.py:2` 为候选兜底说明，不能据 metadata 断言全部硬编码源码 | AC17–18 |
| R10 / 既有产品及开发部署缺陷，成立 | install、uninstall、dev-deploy 三方明确修正项目→基址→资产判定；覆盖首装/追加平台/重装升级（已有入口）/卸载，拒绝域外链接 | `FULL/README.md:277`；`docs/workflows/wf/payload/install.py:668,1165`、`docs/workflows/wf/payload/bin/uninstall.py:254`、`scripts/wf-dev-deploy.py:94,108,249,323,431,496`；dev-deploy 首装只按 base 校验，追加平台直接 join；既有产品规则见 `docs/workflows/wf-framework-mechanism.md:269` | AC19–20 |

## Acceptance Criteria

> 规划时点（实施前）：所有条目均未实施/未验证。下方复选框保留为原始计划清单，**不表示当前完成状态**；
> 实施后的逐项状态与证据见 [validation.md](./validation.md)，具体反例/正常对照/测试责任面见
> [实施验证矩阵](./implement.md#8-逐项证据矩阵)。R9 的规划基线以 [清点依据](./inventory.md) 为准，
> 实施后的 candidate 分布更新见该文件 §2.1。

- [ ] AC01：尚不存在的 `..`、父链接、相似前缀或坏链不能通过 scope 越界校验；合法域内未建路径可用。
- [ ] AC02：仅设置 scope 后全部管理默认路径入域；显式域外缓存/pycache/sidecar 在首次写前拒绝；普通 list/dry-run 无临时写入。
- [ ] AC03：相位不符、矛盾或缺失的 repro 日志拒绝；合法对应相位的多行日志通过。
- [ ] AC04：worker、gate、writer 同样拒绝错误相位且不签发证明；green 不受继承注入变量污染、不续签 red。
- [ ] AC05：解释器路径不变但 binary 或 SUT 版本变化时运行身份和证明变化；相同输入身份稳定。
- [ ] AC06：旧证明无条件失去新协议资格；dev auto 重证、candidate auto 缺证明拒绝，新同主体跨部署复用正常。
- [ ] AC07：摘要创建/写/fsync/replace/读回任一步失败，根运行器非零且不输出 GATE-OK；成功摘要可读回且无旧轮次证据。
- [ ] AC08：owned 资源清理失败/未知/残留阻断成功；正常取消及 G 存活时的 S 死亡接管后日志保留、fixture/results/release 锁及 FD 正确释放；未知时保留现场、不得删锁取绿。
- [ ] AC09：输入树/候选/meta/tag/HEAD 任一不符不能误报 REUSED；同输入实际复用只读且稳定。
- [ ] AC10：候选构建/发布失败不丢有效旧代；无主输出不覆盖；首次/重复/重建与恢复一致。
- [ ] AC11：默认 bundle 与显式路径同样可用；缺失、不可读、坏 JSON、非对象、坏 schema 稳定非零，不抛二次异常。
- [ ] AC12：畸形字段/相位/非有限值在校验层归因，不能进入成功汇总或错误 state。
- [ ] AC13：宿主合成缓存深层已有文件改变，即使顶层 mtime 不变也能检测；缺失与空树区分。
- [ ] AC14：内容/权限/链接变化与读取未知均有反向自证；快照不跟随树外链接、不记录敏感原文。
- [ ] AC15：真实父先退出、setsid/双 fork 等反例中，命令后代均被回收且不误杀 sibling；原始 rc/日志/pass_fds 保真。
- [ ] AC16：BOOT/READY/START/STARTED 前/清理窗口的信号、重复取消、C 失联均经同一协议收口；S 普通崩溃/os._exit/SIGKILL/卡住由 G 接管，在独立 session/双 fork/持锁用例中确认无后代与 FD/锁遗留且仍报设施失败；目标不继承保护信号/mask/控制 FD。G 可捕获异常也须收口，最终监督边界失效则报告 cleanup=unknown 和恢复步骤而不签成功；正常与嵌套行为、原 rc/日志保真。
- [ ] AC17：按清点依据对注册全集和运行器可发现 repro 全集逐 ID 销账（基线 67 与 85，其中 repro 分组覆盖 54、未分组 31）；显式元数据缺失不能作为漏核理由；candidate 缺失安装库不能退回源码；可迁移行为项完成候选实跑。
- [ ] AC18：覆盖表核对集合身份及新增/删除/改名差集，不能只核总数或以分组成员代替全集；排除/manual/不适用不计 passed；保留源码白盒项有技术理由和对应安装行为保障；旧用例预算不降低取绿。
- [ ] AC19：install/uninstall/dev-deploy 三方均完成边界修正，首装/追加平台/已有升级入口/卸载对技能根及其祖先域外链接整批拒绝；域外对象与项目业务文件/记录不变（既有互斥锁语义单列），正常项目内路径不误拒。dev-deploy 的 preview/首次 confirm/追加 confirm/no-op 各有直接证据。
- [ ] AC20：已有预览确认链及单进程预检到锁内 apply 间的根漂移被拒；旧项目外 root_ref 不删除外部对象、不序列化为合法新根，项目内记录与合法 no-op 保持可用；dev-deploy 不新增跨进程预览令牌。
- [ ] AC21：T0、定向、慢契约、full green 串并等价、full both 与新候选证明通过；缺结果、协议混读、输入漂移等原守卫继续有效。
- [ ] AC22：新 helper/用例的注册与输入身份链齐全；产品发行由构建器生成并通过字节复现/token parity，相关文档与代码一致。

## Key Decisions / 兼容约束

- 优先抽取作者侧公共契约并改全调用链，不在 bash/worker/gate 各补一套条件。
- 产品 installer/uninstaller 继续单文件标准库自包含；其同构边界采用共享参数化反例对拍，不强迫依赖安装前不可用的 wflib。
- bundle/state/context 成组升级；旧证明保留可追溯信息但不继承资格，不静默清空或回写归档证据。
- 进程监督采用固定 C→G→S→W 两级专用责任方：G/S 均为独立 session 的 subreaper，G 是 S 故障时的存活接管边界；两跳匿名通道共用协议，终止/回收共用算法，不更改调用方全局 subreaper。目标信号和 pass_fds/锁语义保留，不要求额外权限。
- install/uninstall 保持自包含；dev-deploy 明确修改完整计划与锁内复核，现有 base 级 safe_write_target 不能代替项目→base 的第一层边界。
- candidate 声明必须经真实来源和行为证明核实，不能机械把 59 项都标 clean；需操作作者源码的白盒测试保留原层。
- 真实 HOME 与 SUT 异解释器不变，不借伪造执行器确认换取测试通过。无 scope 默认路径兼容；scope 下收紧是边界修复。

## 本轮排除

- 自动制造真实宿主压缩/恢复事件来替代 `d1_tests`、`d1_wf_tests` 的人工验收。
- 改变宿主 HOME 的产品语义、伪造执行器确认，或修改宿主已有确认凭据。
- 同 UID 恶意竞争、任意 syscall 沙箱、整个 G/S 边界最后有效回收方不可用/宿主断电/内核不可回收对象的自动回收保证、断电级持久性及跨系统重写；C 退出且 G 存活、S 普通崩溃/SIGKILL 且 G 存活均在本任务内。残余边界必须报告未知和恢复步骤，不等于“可安全重跑”。
- 无关重构、改变现有 green/red 的业务含义、降低期望用例数以取绿。

## Risks / 规划状态

主要风险是公共路径 helper 影响 bootstrap/fake-tree、身份协议改变影响旧证明、G/S 两级监督影响锁祖先/信号/FD，以及三方资产安全修正影响旧 root_ref。G 增加固定监督成本，必须保持最小接管职责并记录真实开销，不能通过移除故障回收来达标。设计逐项指定兼容出口与完整回滚单元，实施不能用忽略错误或跳过验证化解风险。

没有待用户补充的事实问题；技术方案、范围、兼容变化和上述外部能力边界一并提交本次审查。当前仅完成任务与三份规划材料；完整性自查见 [review.md](./review.md)。本轮不得执行 `task.py start`、实现修改或实现级测试。仅用户在看到本版材料后明确批准，才进入实施。
