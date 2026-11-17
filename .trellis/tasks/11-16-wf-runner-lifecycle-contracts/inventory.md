# 调用链与删除出口清单（规划基线）

> 基线 `c0c3a167`。只读取证；行号用于定位，实施后按函数与行为复核。
> 搜索范围：full/ 的 shell/执行/缓存/路径 helper、repro/ 的 worker/选择/脚手架、wf_test_release.py、直接相关单测；不是整个仓库安全审计。

## 调用结构

```text
run_all public → fixture/results lease → outer execution C→G→S→W
  W: controlled → release_context → execute shell
    ├ template_cache / run-owned build
    ├ run_one → install 或 fixture/init → test execution
    └ repro/run（继承 context）→ _worker → execution.run → case
  当前 W: cleanup helper → 删除 → summary → GATE-OK
  当前 C: 等 G/S 完成 → .runner.json；取消时另删夹具

独立 repro/run → fixture/results/release lease → worker → gate → state writer
候选审计 candidate_audit → run_one（同一 execution 路径）
慢契约 class → run_all / repro → scope 检查 → teardown
```

内层 summary 在外层监督结束前产生；不能要求内层等待 `.runner.json`，那是因果环。方案将最终发布交给外层收口者。

## 资源责任表

| 出口/资源 | 当前来源/消费者 | 证据与缺口 | 方案归属 |
|---|---|---|---|
| run fixture / legacy / run-owned template | run_all cleanup_fixtures / EXIT / execution.cleanup_cancelled_run | run_all:280,289,825；正常收尾与 EXIT/取消三路删除，helper 失效默认 0 | R1/R3：外层单一 finalize；内层只请求取消 |
| root controller落点 | execution.main --runner-control / run_all lease exec | execution:1128,1147,1165；run_all:194–197 已有外层C，旧shell成功收尾实际在execute而非controlled分支 | R3/R5：扩execution.runner_control，CancellationScope贯穿，直接调runner_cleanup.finalize/publisher；同C进程，不新建controller，不bash收口 |
| 单元 prep/install/test 命令 | run_one:52,81,84,125 | 只有 test 有显式结果 JSON；prep 监督返回未纳入 runner_cleanup glob | R1：execution.run 启动/终态 receipt 覆盖所有调用，不靠文件名猜全集 |
| isolated HOME | execution.isolated_user / main finally | execution:1143–1152；unknown 仍删，删除异常会遮住原失败 | R3：同一 cleanup assessment，清理失败附加归因并先保留执行事实 |
| repro 相位 TMPDIR | _worker.run_phase | _worker:47–67；finally 不看执行结论；phases 内有真实 execution 结果 | R3：清理依赖明确 cleaned；失败或异常保留路径 |
| 独立 repro 全局资源/锁 | repro/run:180–263 / worker / writer | shell 无与 run_all 等价的根 controller；trap 退出后需完整收口 | R3：复用 execution controller；内嵌不新增根 controller |
| 命令结果汇总 | runner_cleanup.unknown_units | :19–43；glob 不证明预期集合，空字段放行，非对象崩溃；内层不能读未来外层结果 | R1：run_id+managed/root/standalone证据域；assess_run直接结构化返回，非法/异常保守拒绝，不重建CLI空输出边界 |
| 显式结果目录初始化/复用 | fixture_scope.claim_results/prepare_results；run_all lease | fixture_scope:72–113、run_all:140–152 当前先 claim/prepare 再 controller；原方案会在 state 首写前留下与 legacy 相同 owner | R3/R7：schema2 owner 原子绑定协议/意图/run_id；begin_run 先意图→state→prepare；死亡后 incomplete-new，不降级历史退役 |
| 自动结果轮转 / bootstrap | fixture_scope.prune_results | :210,233–307；.json 后缀已认 run-state.json，_KEEP_DIRS 不含 commands；认识名称也不证明 cleanup | R3/R10：自动仅终态 cleaned；共用产物登记；无主 bootstrap 报处置路径，不凭已知形状删除 |
| 慢契约 scope teardown | test_run_all_contract.tearDownClass | :160–204；发现 leftovers 后仍 rmtree；unknown case 也会被整类删 | R3：检测/证据失败保留 scope，正常完成才删；测试 owned 进程由测试外边界回收 |
| harness 自有 _STAGED | repro/_harness.main finally/_cleanup | :167–185；在目标进程内部，无法自行证明外部后代终态 | R3：托管 worker 设置本地 defer-cleanup；由 worker 在监督后统一回收相位目录，KEEP 显式保留 |
| template journal/backup/staging | run_all cleanup_template_cache_stale / template_cache publish/recover/_finish | run_all:405,464；template_cache:343,367,382；先删后恢复、lookup 可绕过，_finish 吞删除失败 | R2：维护入口单一所有者、先恢复、再验证命中、最后有据清理 |
| test-release journal/backup/staging | wf_test_release.ensure_release_locked / recover_locked / _finish_transaction | :644 先恢复后清理已正确；:532 finish 用 ignore_errors 后删 journal | R2：保留已有算法，核事务终结与删除失败行为，无必要不改恢复判据 |
| candidate 发布 | prepare_candidate_repo._publish_staged | 同步发布与异常回滚，不属模板 journal；由已有锁/验证保护 | R6：回归核原保护，不新造 candidate journal/替换算法 |
| summary.json | results_summary.build/publish | :210–214 先写 pending 后改内存；readback 只核少数字段 | R5：构造最终对象一次发布，完整读回相等；外层 finalize 后发布 |
| 控制结果 / 日志 / receipts / run-state | execution + 生命周期 helper（拟） | 需区分进程证明、资源删除与发布结果，避免循环写/成功自证 | R1/R3/R5：各字段唯一写者、失败保留 started/active，不补签 cleaned |
| 无 journal staging/backup 与历史 stale/build | 模板 run_all:405–411；发行 _cleanup_stale:629–641 | finish 忽略删除错误后删索引可造 orphan；stale/build 在本次检查范围只见删除引用，未见生产者 | R2/R10：归属/引用/容量盘点与精确清单退役；新 finish 保留失败索引，journal 前中断也可发现 |
| 历史有主无 run-state 结果 | fixture_scope.prune_results / README:270–276 | 新规则会永久跳过；现有 remove:136 只验 sibling fixture marker，与 README 声称支持结果内部 marker 不符；仅缺 state 不能证明旧格式 | R7/R10：严格旧 owner 且无新痕迹才可确认退役；schema2 缺坏 state/错 run_id 一律 unknown；批量确认、锁内复验、失败/幂等；旧记录不回写 |
| 事务 checkpoint 与继承污染 | template_cache.publish / wf_test_release._publish_locked；候选审计/namespace/r67 环境 | 两发布器无精确 checkpoint；RecoveryTest 直调恢复不能证明真实入口顺序 | R2/R9：显式开关+owned scope+枚举点确定退出，逐点真实恢复；非测试环境不生效，不依赖外部 kill |
| 平台上下文清单 | workflow.md:407–462,474–505；config.yaml 的 codex.dispatch_mode；activation.md | 本次Codex inline不等于未来实施平台，外部审查者平台也不能代替运行时证据；硬编码进入命令会误用空清单豁免 | 统一共享activation门控，每次实际启动前裁定；inline直接加载，dispatch先补真实spec/research JSONL并校验；不更改平台配置 |
| root 自动残留观察 | root execution controller → runner_cleanup.observe_roots → fixture_scope/template_cache/wf_test_release.observe（拟） | 前方案只有 AC17 提示要求，无调用生产者；run_all:153–161 的结果 prune 与 :464 模板维护分散，单 key acquire 不会代替全根观察 | R10：控制器接管后/维护前一次 shallow 只读编排；按使用根去重、排当前 run，stderr 分类快照+容量未测+准确 inventory 命令；计划/内嵌/per-case 零调用 |
| 新 owner/状态部分写入窗口 | lifecycle.begin_run（拟）、fixture_scope owner writers/readers | 当前 owner schema 缺失为 owner/root 精确对象；新方案要避免“旧 owner + state 还未写” | R7：正式 owner 首写 schema2、执行意图先于破坏性 prepare；第一代/plan-only 转执行/cleaned 复用逐点中断；所有权域变化只限结果 marker |
| 无run collector/scope的execution调用 | execution.run:745–766、main:1118；test_execution:18、test_supervision:52；candidate_audit→run_one | 直接测试用普通TemporaryDirectory无scope；run现会mkdir日志父链且路径错误抛OSError，不应以新增receipt要求全部迁scope | R1/R6：有scope核scope、无scope固定显式log父dirfd锚点并安全创建所需父链；库异常语义保持、坏managed/scope不fallback；receipt唯一hidden sibling，不授目录删除权 |
| standalone receipt 的结果枚举 | repro_select.validate_repro 根目录 `*.json`、fixture_scope.prepare_results 顶层JSON清理、candidate_audit record_suite 精确结果读取 | hidden sibling 不命中repro case glob；prepare只会在owner/lifecycle允许复用后清理；audit必须按本次返回引用读取，不能搜同名历史receipt | C2：证明隐藏receipt不被repro reader误报为case、不影响plan/results_summary/coverage；prepare拒绝路径不发生sidecar删除；candidate audit行绑定本次command_id |
| standalone receipt 生命周期/留存 | execution.run/CLI 的唯一隐藏JSON sibling | test_temp目录由测试owner清理；candidate_audit workdir可能跨次复用并保留旧receipt；没有统一prune owner | C2：record精确保存本invocation receipt路径；其留存只作audit证据，不纳入run汇总；盘点调用者是否已存在可控生命周期，绝不按隐藏命名自动glob删除 |
| controller/监督确定故障 | execution.runner_control、runner_cleanup.assess_run/finalize、execution G/S固定事件（拟） | 现有S/G有fault env但部分靠delay；聚合/publisher真实root边界无注入定义 | AC02/08/14：总开关+scope+有限enum注入异常/非法返回/删除发布失败；G/S按metadata selector和真实状态点故障，无任意脚本/路径 |
| 新协议保留现场的终止出口 | lifecycle分类；fixture_scope inventory-results/retire-results；README（拟） | 旧方案只自动拒绝unknown/KEEP并换新路径，未解除旧现场占用；plan-only虽可首次执行仍缺显式放弃出口 | R8/R10、AC18：自动拒绝不变；可验schema2结果/逐项owned fixture经TTY路径+digest明确放弃，必要检查硬门禁；外部报告先建、晚期I/O停下报部分，不伪cleaned |
| 缓存外显式结果/fixture的选择面 | inventory-results --results-root / --fixture；selection.entries（拟） | 只给cache根扫描无法直接处置任意命名显式结果；未定义清单结构会使维护入口不可照做 | 互斥cache/精确结果模式，fixture逐项marker核验；盘点与selection共用entries结构，README给完整命令/schema，禁止从plan自动推删除集合 |
| 父子执行与命令可达性 | 父implement、子implement、verification-plan（拟） | 父切片后C2/C3曾引用不存在章节，具体校验命令丢失；职责表不能替代操作顺序 | C1/C2/C3独立执行切片，只引用共享design与V编号；验证目录保存owned scope、T0/定向/真实契约/全量/candidate/发行/文档命令，父最终组合不可跳过 |
| local保留资源的归属/重用/处置 | isolated_user:1079、worker.run_phase:47、harness.stage:51（基线） | HOME现按同log固定路径reset，stage/相位TMPDIR现无独立owner；只保留会产生后续重用抹证据或无主死路 | C2：HOME每command_id唯一，direct stage先既有marker后内容，结果内后代给owner锚点；沿用fixture lease并保证锁序。C3：fixture-only精确选择与同一manual-retained，不伪run_id/结果owner |
| metrics本代交接/最终事实 | run_all:850–935写summary-metrics；results_summary:125–146读输入；fixture_scope.prepare:91–111 | 原metrics无ID且open(w)直写；prepare现会删旧JSON，旧文件必然冒充成功并未证实，但新外层publisher若只核summary身份仍缺输入契约 | C2/AC13–14：write_metrics/read_metrics单点schema1与run_id/root/role/输入摘要、原子提交/受限一次读取；旧/缺/截断/错ID定向及真实入口，controller只用当前gate/control/receipts签结论 |
| lines与结构化receipt引用 | run_one.write_result:31–34；results_gate.gate:44；results_summary._result_lines:100；candidate_audit.record_suite:92–135 | lines严格五列；audit仅len>=5不能代表所有消费者都支持扩列；prep当前无test JSON | 保留五列，unit_execution schema1附原unit JSON（含prep失败/本invocation阶段引用）；audit接预期ID与runner_rc，writer串行；JSON扩展与fake-tree/reader/prepare成组 |
| 初始化执行归属 | run_all lease:136–152；lifecycle.begin_run（拟）；design3.2旧只读措辞 | lease实际上写claim/prepare，原新方案写序放lease而职责又称只读；三个checkpoint要求helper在controller前完成 | C2/AC08–09：lease持锁一次调Python begin_run写owner/state/prepare，成功返ID后exec C；controller不重做，三个初始化点归同一helper |
| 内层诊断对root started的处理 | runner_cleanup.unknown_units:19–31；run_all:825–841 | 当前glob会追加.runner.json；新root started在W退出前天然无终态，若原分支遗留会常驻unknown污染rc/metrics | C2/AC08：移除内层run cleanup聚合，仅同一child reader供nonfinal诊断；终态root由C显式传assess，真正缺root仍拒绝，不按文件名各加一套过滤 |
| root残留观察的交接状态 | runner_control拟固定调用位；C2/C3子implement | controller序列有observe但C2未实现适配器，原文未说明C2真实root期望；C3接线前若隐式no-op会把0计数误读为空根 | C2阶段显式disabled/零调用且诊断标记not-enabled；C3完成后enabled，仅实际配置根各一次浅扫；父最终分别核0与启用次数/根集合，计划/内嵌/per-case始终0 |
| 无journal材料的真实归属 | template_cache._build:223/reset、publish:410/411/move；wf_test_release._publish_locked:554–591 | 模板staging已有fixture兄弟marker，意见称无marker不符；发行staging先build后journal，材料专用marker确实缺失；stale/build在检查范围未见生产者 | C3：模板复用现有marker；发行新typed material-owner先于内容/rename，marker-only壳/碰撞拒绝/旧有效journal兼容；safe-legacy逐类机械判据，旧无证据unproven不伪迁移 |
| 坏journal/无证据历史缓存出口 | 缓存inventory/retire（拟）与既有acquire/ensure | 原方案要求恢复可信元数据，原字节损坏时不可达；只删坏journal又会留残代 | C3：完整key reset→材料/marker→journal最后删→真实入口重建；用户于2026-11-17确认unproven缓存在路径/UID/锁/活引用等硬检查后，经额外TTY+集合摘要逐次确认放弃；不伪归属、不扩大自动清理权限 |
| 初始化真死亡和锁副本 | lease shell→begin_run helper（拟）；fixture_scope.lease_results | 三checkpoint原未定退出方式；helper死不等于持锁shell结束，raise不足证明死亡窗口 | C2：日志flush后helper os._exit97，shell非零原样退出不清理；public整体退出后核现场和真实锁释放，首次/计划/重用×3点，不计入七缓存场景 |
| finalize自动删除部分完成 | runner_cleanup.finalize（拟）；fixture_scope.remove:136–166 | delete-oserror原只有首删前，没有跨资源/单根内部部分完成证据 | C2：delete-after-first至少两实际owned资源，唯一角色序报告removed/failed/not-attempted，错误即停；单根部分rmtree失败保留marker/剩余内容，不ignore/retry |
| 验证片段隔离和审查表 | verification-plan第1节；review意见19–23 | 片段原无marker读取/净化；CaseWorkspace合并os.environ并非全面净化；空行切断GFM表，引用脚本不核此语义 | wf_clean逐调用只按变量名剥离定位/故障，check-scope设active scope验marker；所有验证命令同用，片段语法/结构与实施行为分层；GFM表块头/列数/1–29连续行纯文档校验 |
| 慢契约teardown证据写失败 | test_run_all_contract.tearDownClass:177–182、199–201（基线） | class-cost写入OSError被pass吞掉，且scope回收先于leftover/宿主保护断言；失败时无证据且可能抹现场 | C2/AC10：证据写失败显式teardown-evidence-failed并非零；先记录进程/FD/宿主保护，再按保留条件回收；证据失败或leftover/host变化保留scope，不能先rmtree再断言 |

## 影响登记

- 新公共 helper 必须进入 `repro_select.HELPERS`、`plan.FAKE_TREE_COPY` 与对应完整性测试；模板输入已有 full subtree 枚举，核验而不重复维护。
- r67 fake tree 必须产出新协议的真实最小合法记录；不得通过“fake 模式忽略清理”绕过。
- 如 r67 等 suite 脚本字节变化，按现有生成器更新 candidate-audit，核 source_coverage 基线；不手写通过记录，不改 candidate_clean 以绕失败。
- run_all/repro 所有 trap、早退、re-entry、pending receipt、unknown、资源删除异常与发布异常逐项回查；不只正常 exit。
- 低层 fixture_scope.remove/reset 继续负责路径/owner 校验；业务自动调用方负责生命周期许可。显式人工清理不被推导为自动可删许可。
- 产物登记还要覆盖 prepare/prune/bootstrap/盘点/退役，不只 fake-tree 与 coverage。run-state.json 的既有 .json 识别须保留而收紧语义，commands/ 新登记但不豁免 pending/KEEP。
- 正常运行提示由 root 的 observe_roots 明确生产：实际维护前一次 shallow 快照、容量未测、精确 inventory 命令；显式完整 inventory 才算大小/摘要。计划/内嵌/每用例不额外扫描，观察坏无关材料不扩为当前 key 错误。固定 .lock 永不作为清单对象。
- 删除失败不保证原子回滚：整批预检后逐项报告并停止，过时清单重盘点；普通/safe路径对未知归属拒绝。缓存unproven的额外TTY放弃拟授权单列，不伪owner/cleaned，不扩大结果/fixture权限。维护自身登记的遍历FD不误当消费者，其他进程/cwd仍检查。
- owner schema2读写同步claim/plan/prepare/prune/bootstrap/retire/controller/fake-tree/tests；既有fixture与正式test-release owner不升级。发行新material-owner是独立tag/字段/消费者，不能当正式发行owner或靠宽松字段兼容坏结构；先内容前建证据、树删后才清marker。
- 事务验收集合：W1–W5五恢复场景+O1 journal前孤儿+F1索引最后删除，共七行/六点；同点首次/重建分别证明。模板和发行新摘要确认时机不同，不能复制相同回滚断言。
- 本目录为父协调任务，CLI(C1)、controller/证据/摘要(C2)、缓存/盘点/观察(C3)分批所有权与依赖见 [delivery-map.md](./delivery-map.md)；实施不得直接start父来一次性改全包。
- 终止出口独立核验：换新路径不等于旧现场已处置；自动保留/safe-legacy/manual-retained分别有允许/拒绝矩阵。权限或liveness能力不足不能靠TTY越过；所有新状态/报告都有生产者、消费者与中断重盘点规则。
- 子项验证只要求该时点已实现契约；未来C3功能不得阻塞C1/C2或被记已通过。共享命令的V编号、文件链接和章节引用作为方案文档校验项，避免父重排再次造成引用与命令丢失。
- 本轮新增身份链登记：metrics schema1、unit_execution schema1及prep result属C2兼容批次；summary3/owner2/receipts1原计划不变，lines五列不变。C3维护消费者复用同一产物登记，不能再发明名称豁免。故障spec/fake-tree/输入来源/README与引用边同批核对。
- 保留现有绿路径的机械对照含无scope库/CLI、可安全创建父目录、既有OSError、prep失败与无test、候选复用workdir；不许“全部迁scope”或“只用最终test receipt”把影响面掩掉。内层卫生/产品树检查、债务语义通过实际非零控制事实保留，metrics不覆盖。
