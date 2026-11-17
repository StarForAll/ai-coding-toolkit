# 规划自查、外部意见判定与验收映射

> 更新：2026-11-17；本文是实施前的规划审查记录，当前实施/验证状态见 [validation.md](./validation.md)。基线c0c3a167；本轮仅修任务Markdown，未启动任务或运行实现测试。
> 方法：trellis-brainstorm、receiving-code-review及项目方案自查规则；意见按本仓库事实判定，不把外部审查会话的平台当当前运行时。

## 1. 历次意见与统一裁定

序号1–29保留历次问题的证据摘要，30–34为本轮五条意见；处置规则以当前共享design、activation、verification-plan及子任务切片为准，早期方案不是另一套可执行规则。AC仍为01–20，不因重复审查增号。

| 意见 | 判定/已查证依据 | 当前统一处置 |
|---|---|---|
| 1：无journal orphan与stale/build无出口 | 核心成立。template_cache.py:367–374、wf_test_release.py:516–539可吞删除错误后删journal；发行另有_cleanup_stale，run_all glob并非所有缓存唯一回收路径。所查full Python/Shell和发行helper中未见stale/build当前生产者 | finish最后删索引；材料所属inventory分类，合法材料精确清单退役，历史命名不自动授删除权 |
| 2：legacy-owned旧结果永久跳过 | 成立。fixture_scope.remove:136–166只认兄弟fixture marker，README:274–276的结果owner说法不符 | 专用inventory-results/retire-results验结果owner；严格旧格式走safe-legacy，不补历史cleaned；新协议处置见16 |
| 3：五窗口真入口无确定机制 | 成立。现发布器无checkpoint，直调recover不足以证明真实入口顺序 | 有限checkpoint、总开关+scope、精确退出、日志/磁盘/真实入口三证据 |
| 4：空JSONL与ZCode冲突 | 对本会话平台判断不成立；运行时与项目配置指定Codex inline。原启动命令漏空清单确认是实际缺口 | 不修改配置；每次实施按activation重新核平台，不能长期固定空清单豁免 |
| 5：bootstrap不认新增产物 | 部分成立。.json分支已认run-state，commands目录未认；名称识别也不证明可删 | 唯一产物登记供prepare/prune/bootstrap/inventory/retire消费；无主新协议不被bootstrap绕过 |
| 6：初始化早死被认成legacy | 成立。旧claim/prepare先于controller/state，旧代重用/计划转执行也有身份空窗 | schema2 owner原子绑定协议/意图/run_id；先意图→state→prepare，新缺坏state不降级legacy |
| 7：AC17提示无生产者 | 成立；但真实root可以在计划退出分支之后观察，无须放宽计划零扫描 | controller维护前一次observe_roots；按本次使用根浅扫，计数/容量未测/准确inventory命令 |
| 8：controller无实现落点 | 成立。已有execution C侧--runner-control；旧shell收尾实在execute，非controlled | 同C扩runner_control与CancellationScope，直接assess/finalize/publish，保持拓扑/FD/rc |
| 9：root异常/G/S故障无确定机制 | 核心成立；已有G/S fault但部分靠delay，聚合/publish缺注入。新直接调用不再有CLI空stdout边界 | design第5.2节枚举异常/非法返回/删除发布失败，G/S按真实事件和metadata selector注入 |
| 10：无collector时对账全集不成立 | 成立。direct API与candidate_audit/run_one确有无collector路径 | root/managed/standalone三域；所有启动先登记，坏managed拒绝不fallback，独立receipt不冒充完整run |
| 11：五窗口/六点数目混乱 | 成立，且finish尾窗也需销账 | W1–W5/O1/F1七场景六点；模板/发行摘要时机不同，恢复断言分别核 |
| 12：单任务规模风险 | 成立；建议不等于数量硬阈值，R5与controller不能表面拆开 | C1 CLI、C2生命周期/controller/summary、C3缓存/维护；父做协议与最后集成，固定依赖 |
| 13：审查平台已是ZCode | 对当前执行者不成立；外部reviewer平台不是本会话平台证据 | 现在不派发agent；后续实际会话重新过activation，dispatch填真实JSONL |
| 14：父P2与P1缺陷不一致 | 不必天然一致，但原默认P2缺理由 | 父/C2/C3 P1、C1 P2，已在元数据和交付图统一 |
| 15：standalone侧写/枚举兼容漏盘点 | 成立。log邻近文件可被复用/枚举/audit看到，hidden命名不替代调用身份 | 唯一hidden sibling，API/evidence_path与CLI result显式引用；C2逐调用方盘点可写/拒绝及reader/prepare/audit |
| 16（上一轮）：新协议保守状态没有真实处置出口 | 核心成立，原design的拒绝清单只适合自动清理，不能同时作为所有维护的永久禁令。plan-only本可首次执行，故“也不能复用”不准确；但不需要计划时的放弃出口确实缺失。应由自查第2/6项捕获 | 统一自动保留/safe-legacy/manual-retained：仅owner可验schema2结果与逐项owned fixture可在必要检查通过后TTY精确放弃，覆盖plan-only/早死/死active/cleanup unknown或failed/KEEP；不补cleaned，不让确认覆盖活锁/活持有者/权限能力不足 |
| 17（上一轮）：父切片丢章节与执行命令 | 成立。C2/C3所指父implement旧章节已不存在；职责表不能替代操作顺序，AC16也不能只留文字要求。应由自查第10项捕获 | 三子独立有序implement，父只协调最终组合；共享verification-plan保存隔离/T0/定向/真实契约/full/candidate/发行/资产文档命令，按V编号引用并机械核可达 |
| 18（上一轮）：C1激活指令与父不一致 | 不一致成立；“本执行者已ZCode”仍不成立。持久化“当前inline”的操作指令会形成未来激活陷阱，应由自查第3/10项捕获 | 所有父子入口统一引用activation：实际会话核运行时与配置，inline或dispatch分别加载上下文/启动；本次空清单只是记录，不是未来授权 |
| 19（前轮P1）：standalone的scope前提自相矛盾 | 成立。test_execution:18和test_supervision:52以普通TemporaryDirectory直接run，无WF scope；execution.run:750会mkdir父链，路径OSError现直接抛出。故“全部合法调用必在scope”不成立，但有scope越界保护应保留；自查第3/8项漏检 | 有scope按scope、无scope固定显式log真实父目录输出锚点；安全创建缺失链，库异常保持，坏scope/managed不得降级。普通无scope绿路径与scope故障用例分开，不以迁全测试掩盖兼容 |
| 20（前轮P1）：metrics未绑定本run | 设计缺口成立。run_all:850–935无ID直写，summary builder:125–146未核身份；但fixture_scope.prepare:91–111会删旧JSON，早死还受rc/缺结果门禁，不能据此宣称已复现旧metrics必然签成功。自查第1/3/5/8项应沿输入链捕获 | schema1 metrics原子交接，本ID/root/role+当前输入摘要，由唯一reader核验；summary3记input_evidence，controller按当前gate/control/receipts派生结论，不信shell cleanup/extra_failures。旧/缺/半写/错摘要与真实入口故障矩阵，债务/卫生规则保留 |
| 21（前轮P2）：结果行引用与五列冲突 | 成立为载体歧义，不是已决定扩列。run_one:31、results_gate:44、results_summary:100均五列；audit:111的len>=5不构成其他reader兼容。自查第3/9项漏列协议承载 | lines五列不变；原unit JSON附unit_execution schema1与逐阶段receipt引用，prep失败也有终态；audit显式接本invocation并核runner_rc/行投影。execution与unit writer串行，JSON读取/fake-tree/产物登记成组 |
| 22（前轮P2）：begin_run归属矛盾 | 成立；设计写序和checkpoint本来都在lease，3.2表的“只读”与之相反，不能交给实施者二选一。自查第1/4项应发现 | lease持锁一次调用Python begin_run写owner/state/prepare，成功返回后shell编排并exec C；controller只接管，三个初始化点在同helper，失败不重演许可 |
| 23（前轮P3）：内层诊断误读root started | 核心成立。runner_cleanup:19–31当前会追加.runner.json；旧实现对无state未必报unknown，但新严格reader若继承该路径就会产生因果错误/噪声。自查第1/5/7项应同时查正反消费者 | 移除内层run cleanup聚合，lifecycle唯一child集合只含commands，必要诊断children-only/nonfinal；外层显式给root终态，缺root仍拒绝。离线CLI不得因排除root而签完整成功 |
| 24（本轮P1）：无journal材料的资格缺失 | 核心成立，事实需纠正：template_cache._build:223调用fixture_scope.reset(staging)已建兄弟marker，publish:410/411的move也重锚定marker，故“模板staging没有marker”不成立；发行_publish_locked:554–591在build前确无材料owner。stale/build检查范围未见生产者，不能由命名补证据。应由自查1/3/6/9捕获 | 4.2按材料列机械判据：模板验既有fixture marker，不要求staging meta；新发行材料用独立typed material-owner先marker后build/rename；旧无证据标unproven，不走safe/自动删；用户2026-11-17已确认额外TTY精确放弃分支，不能伪owned |
| 25（本轮P1）：坏journal无最终出口 | 成立；“先恢复可信元数据”无法处理原字节不可恢复的损坏，人工修改历史journal也非既定出口。应由自查2/6/7捕获 | 缓存manual-retained做单key完整reset，按固定路径集合/快照而非坏字段，材料+marker成功后journal最后删；无需修journal，重建验证同key解除阻断，sibling不动。归属未证实项另含unproven-cache确认，策略取舍已于2026-11-17确定，每次实际材料仍须确认 |
| 26（本轮P1）：初始化死亡机制不定 | 成立；但“raise一定无法留下该现场”过强，异常实现可能保留，仍不能代替真实死亡反例。helper死后shell仍持FD副本，也不能马上断言锁已释放。应由自查1/4/7捕获 | helper日志flush后os._exit(97)，shell非零原样退出、不eval部分ID/启动controller/EXIT删现场；首次/plan-only/重用×3点，从最外public等退出并探真实锁释放，核新入口拒绝降级；不计AC19缓存七场景 |
| 27（本轮P2）：finalize部分删除无确定点 | 成立。delete-oserror只有首删前场景，不能证明删首项后失败的报告/后续停止。应由自查4/5/6捕获 | 固定角色序delete-after-first，用真实root产生至少两项资源，核第一项与marker消失、第二项/后项及报告一致，失败停/rc不改/无成功；单根rmtree内部部分失败另做定向反例，不重建已删内容 |
| 28（本轮P2）：隔离文字与可复制片段不同步 | 成立；进一步核CaseWorkspace.env主要显式覆盖路径，run_runner仍合并os.environ，不能把“CaseWorkspace模式”当已存在的全面净化器。应由自查8/10捕获 | Bash片段定义wf_clean按变量名逐调用净化WF_*及已知定位，不输出值；create后设active scope跑check-scope验marker，每次root重验路径，T0/定向/build/candidate也净化，显式env参数后加；坏marker/label/路径失败不启动child |
| 29（本轮P2）：19–23行断表 | 成立。18与19之间空行结束GFM表，后五行没有新header/delimiter，先前引用校验不检查此类渲染结构。应由自查10捕获 | 移除该空行，24–29连续接同一表；纯文档结构检查要求每个pipe表块有header/delimiter、列数一致，核意见1–29都属于同一表，不再以链接通过代表排版通过 |
| 30（决策已解决）：unproven-cache授权曾先进入AC | 审查指出的悬置在当时成立。用户于2026-11-17明确允许历史wf归属无法证实的缓存材料，在路径/UID/锁/活引用等硬检查通过后，额外TTY与摘要确认显式放弃；该策略取舍现已确定 | R10、AC17/AC18、design4.2及C3切片统一采用已确认分支；每次仍须额外真实TTY+集合摘要确认，归属保留unproven，自动/safe-legacy拒绝，不扩大无主结果/fixture权限。规划确认不等于实施启动或真实材料已获本次删除授权；AC仍待实施验证 |
| 31（登记缺口）：standalone hidden receipt不在4.1唯一登记表 | 成立。2.2和C2文字有路径/枚举规则，但AC20要求唯一producer/consumer/缺失/处置登记，表缺行会让prepare顶层JSON行为无权威依据 | 4.1新增standalone receipt行，登记生产者、scope域、prepare条件、repro/summary/audit排除、inventory/retire与缺失/坏终态规则；C2按表成组更新，不按前缀扫删、不把receipt当结果owner |
| 32（交接缺口）：C2/C3 observe调用位行为未定义 | 成立。父序列写调用位，C2说后续接口、C3才接线；C2真实root期望不能从“没实现”推断。应由自查2/7捕获 | C2阶段显式`disabled/not-enabled`且observe=0、不读根、不输出残留计数；C3接线后`enabled`，实际配置根各一次；计划/per-case/内嵌始终0，父分别验两态，禁止no-op伪造 |
| 33（同类漏网）：慢契约teardown证据写失败静默吞掉 | 成立。test_run_all_contract:177–182 pass OSError，且约199–201先rmtree再做leftover/FD/host断言；与R9证据缺失不得静默同类，应由自查5/7/8捕获 | C2同批改为证据写失败非零/明确归因；先完成进程、FD、宿主保护断言，证据失败/leftover/host变化保留scope并报告，不能先rmtree或空报告掩盖 |
| 34（低）：delivery-map与C2 PRD R编号不一致 | 成立为文档引用精度问题，虽不改变AC行为，但违反自查10并会误导责任边界 | C2 PRD同步列R1/R3/R5/R6/R7/R8，delivery-map、review、AC映射保持同一责任集合；结构校验机械比对 |

## 2. 十项自查与本轮关联修正

| # / 检查 | 本方案最终约束与核法 |
|---|---|
| 1 唯一产生函数 | execution写三域receipt，lease中唯一begin_run写意图/state/prepare；write_metrics/read_metrics单一交接，results_gate.assess_run_results唯一目标投影，C唯一收口；lifecycle统一child集合/产物，unit JSON按command完成后串行附加 |
| 2 反向规则 | 另开results只允许继续工作，不解除旧现场；retired-manual不是cleaned；认识名称不是删除许可；核R10、AC18、处置表的两种语义 |
| 3 身份域 | schema2 owner协议/意图/本代ID原子绑定；standalone调用与run全集分域，有scope/无scope输出锚点各定义；unit invocation与本run分开绑定，metrics输入全链核ID/摘要；选择绑定域/根/路径/摘要；平台以实际会话核验，不能从文档旧现在时推断 |
| 4 首次/幂等/显式重做 | 首次/计划转执行/cleaned重用×三初始化点真死亡、shell退出与实际锁释放；事务重入与新material-owner先写/marker-only壳；跨资源和单根内部部分删除；退役已删项幂等，变动项重盘点，人工重试用新报告不覆盖旧证据 |
| 5 事实归属 | process/local分别记账，内层root started不归child unknown；metrics仅测量，gate/cleanup/目标事实来自当前证据；prep失败不伪test；浅扫/人工处置报告不冒充cleaned |
| 6 真解除出口 | 有效journal优先恢复；可验marker孤儿safe-legacy；坏key完整manual reset后真重建；旧缓存unproven按已确认R10逐次精确TTY+摘要授权，不要求修出不存在的历史证据；结果/fixture仍验owner，能力不足/活引用先解除硬阻断，不绕确认 |
| 7 阻断作用域 | 坏key只阻当前维护；自动拒绝不阻新路径；维护整批预检失败零删除，删除期I/O可能部分完成；C1/C2不被未来C3用例阻塞，父未集成不能宣称整体完成 |
| 8 读取归因 | 缺失/损坏/不可读/漂移分别报告；metrics必需项不默认0，单次快照验证/消费不重开；路径安全不吞既有OSError，不删除正常父链创建能力；选择不信任输入；必要liveness核锁协议、PID启动身份和本UID/proc路径引用，不读取环境/argv，不因无关跨UID不可见对象无条件拒绝 |
| 9 旧记录兼容 | 旧metrics/unit JSON无身份只读展示不补ID，lines五列不升级；旧summary只读，严格旧owner无新痕迹才legacy；新owner缺state不降级；不回写历史/伪cleaned；维护工具不自动迁移真实用户存量 |
| 10 数字/引用/命令 | 20 AC、七缓存场景六点（初始化3点不混计）、父三子、8 JSONL；意见1–34同一连续GFM表，所有表header/列数与Bash片段语法/marker及净化结构核验；C2/C3 R编号和observe两态可达；子输入/共享章节/Markdown文件链接/V编号可达，命令完整与隔离前置保留；重排不准删除引用目标 |

上一轮三条意见关联的四组修订继续有效：

1. 精确输入：只给cache根不能直接处置缓存外显式结果，且selection结构未定；增加--results-root/逐项--fixture，盘点给可直接选取的selection projection，文档给完整示例。
2. 报告失败：预检不能预知后续I/O；首删前创建外部报告，后续报告/删除失败停止并报告部分，重盘点确认，不许假原子保证。
3. 能力范围：不能把所有不可见跨UID进程当作本UID对象的永久阻断；限定必需检查的协议/本UID范围，相关权限或平台能力不足仍拒绝，TTY不能代替机器核验。
4. local现场：结果之外的standalone HOME/direct harness stage不能没有归属/处置入口；沿用既有fixture marker与lease，先归属后内容、唯一HOME不reset旧保留根，fixture-only模式可盘点/明确放弃。C2生产证据，C3消费，不另建资源框架。


前轮沿producer→载体→reader→最终结论补的四组覆盖继续有效：

1. 输出兼容：不能只解除无scope前提，却丢掉run()原有mkdir父链和OSError语义；固定调用者cwd、dirfd/O_NOFOLLOW与有/无scope矩阵，公开CLI单独归因。
2. JSON交接：prep失败没有test JSON，不能只说“加引用”而留空；定义unit_execution失败态、逐阶段引用和串行写序，audit同时核runner_rc、旧行/旧invocation。
3. 指标可信度：只给metrics加ID仍会采信shell cleanup/gate/extra_failures及缺字段默认0；改为唯一gate报告与必需测量登记，输入摘要联到unit/repro，保留债务/卫生现有语义。
4. 验收可达性：metrics新反例不能只手改文件直调builder；给真实write_metrics固定有限故障spec，作用域/本代校验及子进程隔离同步登记，reader定向与真实root两层验收。


本轮自查另补四个相邻约束，分别进入统一生产/处置/验证路径：

1. 新material-owner先写会产生marker-only壳，且旧journal没有该新证据；明确壳盘点/处置、新路径碰撞拒绝而非rmtree、有效旧journal兼容而不追认无journal旧材料。
2. 缓存reset不能仅删坏journal，必须完整列entry/owner/meta/材料/marker，journal最后删；部分失败继续阻断，真重建证解除，不动sibling。引用检查排除仅本维护登记的遍历FD，不能因自有FD永久拒绝或排除其他进程。
3. 跨资源部分完成不等于单个rmtree内部失败；补删除一个自建后代后失败的定向反例，保留marker/剩余字节，不靠ignore_errors报removed。
4. 环境净化须每次重算变量名，且不能只净化scoped_run而让T0/构建仍继承故障；所有命令复用wf_clean、显式参数后注入，marker设active scope实读，片段结构和后续行为验证分层。

本轮又补四组跨层覆盖：standalone receipt的4.1权威登记与实际prepare/枚举/retire统一；observe交接用disabled/enabled两态和调用次数契约；teardown证据写失败与scope回收排序进入同一错误出口；C2 R编号从delivery-map反向核PRD，意见表/AC/子切片机械比对。

既有信号/FD、local pending、未来.runner.json因果环、双fork就绪、standalone枚举隔离、无关key、完整summary读回及取消边界仍按共享design验收；unproven-cache分支已由用户于2026-11-17确认进入最终AC；策略已确定；审查时 AC 仍未实施/未验证，不把决策确认记为实现通过（后续实施/验证见 validation.md）。

## 3. AC到入口/证据映射（实施期全部待验证）

| AC | 归属/定向测试 | 必需真实入口/正常对照 |
|---|---|---|
| 01–03 | C2；runner_cleanup/execution/lifecycle/supervision | root异常/非法返回/缺receipt；三域先登记，有/无scope/父链/库异常兼容、坏managed拒绝；五列不变、unit JSON逐阶段/失败/旧invocation与audit引用隔离 |
| 04–06 | C3；template_cache/test_release/release_lock | W1–W5/F1真实入口重入，两缓存分别核摘要时机；命中+journal/坏journal/finish失败，sibling不变 |
| 07–10 | C2生命周期、C3维护消费者 | full/独立/内嵌repro；owner/state初始化各边界、错ID、pycache时机；lease helper初始化点与C不重做；children-only/root终态分域，正常started不误报、最终缺root拒绝；helper os._exit97后shell/锁释放，finalize跨资源/单根内部部分失败；取消/G/S/local失败/轮转/teardown，新保留现场处置须C3完成 |
| 11–12 | C1公开parser、C2内部frame | 全部有值选项缺参零副作用，正常group/空格路径/dev/candidate/继承frame |
| 13–14 | C2 summary/controller | publisher OS错误与root seam分验；metrics本ID/root/role/当前输入摘要、旧/缺/半写/错类型与write故障，正常复用/repro开关/债务卫生对照；full/repro投影一致，不只改pending |
| 15–16 | 分片+父最终V-T0/V-CONTRACT/V-FULL/V-CANDIDATE/V-RELEASE/V-DOC | 身份/fake-tree/source coverage与candidate当前证据；全量串并/both、发行只读复现/token parity及全部资产/文档命令 |
| 17–18 | C3维护CLI、PTY/observer、真实root | 计划零观察/实际根一次/根外sentinel/容量未测；inventory零写，safe-legacy与manual-retained分验；plan-only/早死/死active/unknown/failed/KEEP的明确出口，非TTY/活持有者/忙锁/能力不足硬拒绝；模板现有marker/新发行material-owner与壳，坏journal完整key reset→真重建、unproven额外TTY，缓存外精确选择；报告/删除部分失败保留journal、幂等、宿主缓存不动 |
| 19 | C3 checkpoint/真实root | W1–W5/O1/F1七场景六点；开关关闭/坏点/越界拒绝，每行到达+磁盘+重入；初始化/G/S归各自AC |
| 20 | C2产物登记、C3维护消费者、父核对 | run-state/commands/metrics/unit JSON及发行material-owner所有消费者与不变五列lines；wf_clean/marker前置语义，无主不绕bootstrap；activation实际平台分支、JSONL上下文与子切片一致 |

具体命令及运行顺序只在[verification-plan.md](./verification-plan.md)维护，各子implement选择相应V编号；本文件不是执行命令的第二副本。每个AC记录实际pass/fail/not-run和证据，规划文字不算通过。

## 4. 限制与审查状态

历史/新保留材料在明确处置前占空间；新发行material-owner先于内容使新增材料可追溯，旧证据损坏不伪恢复。用户于2026-11-17已确认缓存manual-retained的unproven精确放弃范围；实现必须展示历史归属缺口、额外TTY短语/集合摘要及同一硬门禁；该策略确认不代替每次处置授权，也不证明历史归属或本任务已实施。结果/fixture仍需wf owner，活锁/活持有者/非本UID/能力不足/越界不能确认覆盖。本UID引用检查不能证明不守锁外部消费者或恶意同UID竞争不存在。

宿主断电/内核不可回收对象/全部监督方同时消失/恶意同UID篡改/真实交互压缩不承诺脚本证明；unknown和保留出口仍在验收范围。审查时未实施，不能以此方案保证零新缺陷；后续实施结果见 validation.md。

审查时四任务仍planning，8份JSONL按inline模式有意为空；截至本文记录的时点未运行start、未改实现、未跑单测/repro/build、未提交或归档（后续实施与验证见 validation.md）。等待用户审查的是最新方案，实际启动须重新按[activation.md](./activation.md)核验；当前不要求用户作第二次平台确认。
