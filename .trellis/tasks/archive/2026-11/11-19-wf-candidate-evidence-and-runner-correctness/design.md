# 技术设计

## 1. 候选发行来源（R1）

以 `release_context.py` 下发的发行根和 `WF_INSTALL_REF` 为输入，候选版本和提交来自已核上下文。从同一发行根取得安装器和 source。正向安装复用 `wf_fixture.sh` 的安装记录校验，补核安装记录的 `source_commit`。负向用例保留显式错误参数及受控副本。准备失败在该处带日志退出，后续断言不从半成品取证。作者源码工具检查与候选产品检查分别保留在现有执行分母，不把源码验证伪装成候选运行。

| 调用链 | 处理 |
| --- | --- |
| f0、候选模板及无模板重建 | 保留真实候选入口，共用已安装身份核验。 |
| R69、R70、R89 | 托管发行路径使用当前发行的安装器、ref 和版本，移除固定旧目录回退。R89 的合成输入保持能表达安装器参数解析，不因替换版本源改变其测试意图。 |
| R72 | 现有调用本来就是作者源码安装器和固定旧 ref，覆盖 dev 源码安装。保留在 dev 路径和候选排除，不将其改造成候选行为测试。 |
| CP5 B12 的 F2 | `f2_setup.sh` 按部署模式选择作者 dev 部署器或候选安装器。候选分支安装后核 F2 的 `installation.json` version/ref/source_commit，并确认 `.wf/lib` 内容来自本次候选。分别从相同 legacy scaffold 执行 dev 部署和候选安装，比较 CP5 依赖的状态，不比较预期不同的发行元数据。必须保留原始 `.trellis/README.md`、`NOTES.md`、初始及无交集外部 commit；candidate `f1_init.py` 与 CP5 B1/B2 在该 fixture 继续通过。候选安装破坏这些产品数据或前置时保留 candidate failure，不静默降级资格或弱化断言。仅对明确检查作者工具的断言单独标记来源和分母，dev 验收继续保留。 |
| CP4 A8、R35 的次级项目 | `wf_fixture.sh` 已读取 `WF_FIXTURE_DEPLOY`，候选时走发行安装器。保留各自夹具结构、残留、提交和基线，补测试断言实际安装身份。 |
| CP3、R83、R85、R86 | CP3/R83 在候选模式下导入本次发行安装器，而不是 payload 同名模块。R85/R86 对发行内安装器/资产的静态读取在候选模式指向 release root。R86 对仅存在于作者仓库的开发部署器/构建器断言明确标为作者侧，保留 dev 覆盖；按 assertion 归属核候选资格，不能让这些作者侧断言替代已安装行为证据。迁移错分层断言时逐项对照分母。 |

按注册表检查所有可计划单元的发行调用以及候选 install repro。候选审计逐单元保留脚本来源分类和候选 fixture 的安装记录身份。候选合格的安装行为断言必须能连到已核 candidate version/ref/commit；只使用任意本地 `.wf/lib` 不能证明候选来源。混合套件的源码断言单独标出断言对象和对应分母。合成版本、扰动副本及作者工具断言按其实际作用核对，保留源码和候选的原有场景边界，且不得用跳过或降级消除候选失败。

## 2. 候选审计增量（R2）

`candidate_audit.py` 持有审计的写入和复用判定。报告级身份记录真实 version、ref、commit、候选树摘要、来源发行树摘要、仓库内运行器/helper 输入摘要和解释器身份。helper 集合由单一注册点产生并进入身份，包括审计实际调用的 `run_one.sh`、fixture/template 建立与来源解析代码。逐行记录脚本字节摘要、kind、expect、fixture、隔离设置和该行模板来源身份。模板由当前候选确定性构建时记录其摘要；外部模板只有在内容及候选安装身份可核验时才可增量复用。报告不写绝对临时路径。

- 完整审计只消费本次实际运行的行。完成所有登记 ID 后，在同目录原子发布。任一运行或发布前校验异常都保全旧报告。结果中明确区分完整、部分和含失败断言的审计，不把“报告写成”当成“审计通过”。
- 不传 `--only` 表示完整审计，不是空选择。显式 `--only ""` 或纯空白值拒绝；未提供 option 值由 argparse 直接拒绝，不另造状态。每个非空 ID 必须是登记的可计划单元。混入未知或不可计划 ID 时整组选项在启动套件前拒绝，不忽略合法部分。重复的已知 ID 归一为一个。
- `--only` 核对旧报告 schema、报告级完整身份、登记 ID 集合及每个待保留行的输入摘要，通过后才运行并替换指定行。跨身份、旧格式、待保留行过期或当前报告已有缺行时发布前拒绝，保全原字节，并提示在新路径执行完整审计。不得用新报告头包装旧执行事实。
- 审计持有与 runner 相同的候选发行锁，锁内执行起始和结束校验并涵盖全部 suite，避免协作写者在审计期间替换候选。审计开始前冻结公共输入摘要，结束后重算；suite 或 helper 在审计期间改变即拒绝发布。锁忙或输入漂移时明确失败，输出工件不变。候选根的显式复用并不等于 stale input。由调用者明确传入并经树摘要/tag/commit 校验的候选仓库或正式发行缓存继续按现有方式复用并保持只读，绝不由普通 runner 回收。测试域将候选准备输出放入 owned scope。完整审计先写独立 scope 输出，核对所有 ID、身份和状态后再更新受跟踪的审计工件。

## 3. 临时材料（R3）

复用执行收据与本地资源清理规则，参照 repro 相位的私有临时根。保留现有 `local_dirs` API 语义，新增命令级 `--local-tmp-root`。执行器先写 pending receipt，再在该父目录下用本命令唯一 ID 创建专用根，将实际路径记录在同一收据并把目标进程的 `TMPDIR` 指向该根。创建失败时收据说明目录未创建，不能伪报 retained path。根置于本次结果的 logs 子目录内，以便并行 user namespace 绑定结果卷后仍可见；不把它放在会被 namespace tmpfs 遮蔽的宿主临时目录。fixture、init、suite 各自登记独占根；同一命令内的嵌套步骤继承该 `TMPDIR`。显式串行、自动回退、并行及候选审计使用同一 runner/worker 实现。回收仍只在监督允许时进行。

套件生成的 JSON 决定、审批材料、说明文件、报告、测试输出及临时项目都使用本次根。诸如 `/tmp/wf_external_ack.json` 是测试自造的伪确认，并非宿主或人类证据，必须按次生成。产品通过 `tempfile.gettempdir()` 派生的暂存由继承的 `TMPDIR` 定域，测试中的发现/glob 改用同一个解析根。绝对路径测试先问被断言的究竟是“项目外/越界/固定文件名”还是字面目录；前者选本次根下、仍在项目外的唯一目标，保留边界断言，不复用固定全局名。只有产品接口明确把精确字面路径作为行为契约时才保留字面值，并在独立 namespace 或其它现有受支持隔离域中验证，不能以单元通过为由覆盖宿主旧文件。受监督 local-tmp 根即使位于绝对 `/tmp` 字符串下，也按真实 `TMPDIR` 解析，不能把该字面前缀当成私有隔离的证据。

迁移已发现的 `/tmp/cp5_a.json`、`*_results.json`、伪外部确认与 notes、审批/main-review JSON、`tempfile.gettempdir()` review staging、R47 的外部目标，以及 R69/R70/R72/R35/R89 对 `/tmp/wf-fixtures/release-repo` 的 fallback。托管 runner 必须使用传入的 `WF_RELEASE_REPO`；缺失时明确失败，不回退到固定旧目录。手工 D1 工具与产品自身固定锁/路径契约不随这次迁移。

增加静态回归守卫，扫描 `units.json` 里所有可计划脚本及本轮登记的 fixture/init helpers。源码中的绝对 `/tmp` literal 必须迁到 `TMPDIR`/unit path helper，或登记为精确路径契约并连到对应测试。未分类的新 literal 使守卫失败。动态 `tempfile.gettempdir()` 路径由实际执行 `TMPDIR` 的对照覆盖。执行器确认、Git 身份、isolated-user、产品授权路径、公开结果与审计出口维持现有口径。

## 4. 结果归因（R4）

`unit_execution.state=passed` 表示该单元完成了执行记录写入，不代表 suite 断言通过。`bad` 仍是兼容聚合门禁，不能作为断言失败证据。唯一分类器消费冻结计划、五列 row、`unit_execution`、test result JSON 的 `assertion_result` 与本代 receipts。

| 单元事实 | 分类 |
| --- | --- |
| `unit_execution.state=prep-failed`，failure_reason/阶段记录匹配，且已启动的 prep commands 有同代 finished receipt | preparation_failure，不是 assertion failure。标记为已启动但 receipt 缺失/错代/矛盾则 unverified。合法 `preflight_failed` 可无 command receipt，因为执行尚未启动。 |
| suite/flow 的 test target_rc 为 0，`assertion_result` 有显式 FAIL，PASS+FAIL 数或正式 summary 总数完整且等于 expect，且结果、unit row、receipt 同代一致 | assertion_failed。 |
| suite/flow target_rc 非零且本代 result/receipt 明确记录退出码 | execution_failed，不得单凭 bad 行称为 assertion failure。若 receipt/终态缺失则 unverified。 |
| 本代命令 receipt 明确为 cancelled/timeout，且结果/终态记录一致 | cancelled 或 execution_failed，不得归为 assertion failure。 |
| PASS 数不足但无显式 FAIL、汇总数不等于 expect、结果/断言记录缺失，或 row 与 test JSON/receipt 矛盾 | unverified，不得归为 assertion failure。 |
| 全部预期断言结构齐全、目标退出为零、结果和 receipt 同代一致且通过 | passed。 |

`execution.verdict` 是 PASS/FAIL 解析的唯一来源，扩充 `assertion_result` 暴露 failure count 与完整计数判据；shell 不复制正则分类。`runner_cleanup` 唯一地产生每个计划单元的 typed outcome，并将结果行、`unit_execution` 状态、test result 和 receipt 交叉校验。outcome 限定为 `passed|assertion_failed|preparation_failed|execution_failed|cancelled|unverified`。`summary.json` 的既有 schema4 中新增可选 `unit_outcomes=[{unit,outcome}]` 和 `failure_owner` 的 assertion/preparation/execution/cancelled/unverified 计数；既有 `gate.bad` 与 `failure_owner.rows` 继续表示原聚合值。每个单元身份均在 `unit_outcomes` 里，不靠可能截断的 reasons 复原。旧 schema4 摘要没有该字段时仍按原历史规则读取，不从旧 bad 行反推类别。`evidence_state` 仅在每个计划单元都有合法、同代且可分类的结果及必要 receipts 时为 complete。结构完整的 prep/execution/cancelled failure 可以 evidence complete，但类别明确且绝不计为断言失败。缺记录、错误分类或错代为 incomplete。`cleanup_state` 独立来自监督与本地资源事实。任何组合均不得签发成功。

repro 只有在本代 receipt、结果状态、命令身份、监督终态和本地回收都已核验后，才判日志断言。完整可核的失败断言相位计 `failed`；失败日志但 receipt/cleanup 未确认时保留诊断并记 `unverified`，不得写 proof。

| 事实 | 正式结果 |
| --- | --- |
| 已通过且证据和清理已确认 | 现有 schema 4 出口签发通过。 |
| 明确断言失败、计数完整、同代执行可核 | 非零、`failure_owner.assertion > 0`；清理状态另行记录。 |
| 准备失败或 target_rc 非零，unit/phase 及必要 receipts 可核 | 非零，分别记 preparation/execution failure，不增加 assertion failure；可为 `evidence_state=complete`。 |
| PASS 不足但无明确 FAIL、计数不完整或执行记录缺失/错代/矛盾 | 有 unverified 分类，`evidence_state=incomplete`，非零。 |
| 明确断言失败且监督/本地清理失败或未知 | 保留 assertion 分类，cleanup 维持真实 failed/unknown，不成功。repro 回收未确认则 phase 为 unverified，不能签 proof。 |
| 早期发行准备失败，尚无合法 plan/context 或执行收据 | 用非零退出、准备日志和已有生命周期事实诊断。不得伪造断言结果、摘要通过或可退役状态。 |

failure `summary` 保留分类和清理状态。schema4 增加可选归因字段但保持旧聚合字段语义；历史摘要及 reader 保持原样，缺少新分类时不回推历史 assertion 类型。

保留 summary、run-state 与 proof 格式和早期准备失败的非零及日志出口。检查历史读取、`classify_result` 和 `prune-results` 的影响。失败运行可以有完整证据，处置仍须原有授权。

## 5. 兼容与回退

临时候选用现有构建函数和测试域 validator 注入点，保持正式发行字节。按四项行为分别核对及回退，审计生成件随同套件和核验规则更新或回退。旧记录与失败现场保留原样。

## 6. 实施注记（2026-11-19）

- 审计报告 schema 3 的 `identity` 冻结候选/来源树、tag commit、release subject、注册表与 helper/runtime/解释器身份；逐行 `input_identity` 里 run-build 模板只记录来源与安装身份，模板树摘要作诊断字段保留（fixture/init 构建含时间性字节，不能作为跨次复用判据）；`external` 模板的树摘要参与复用校验。
- 命令私有 TMPDIR 与既有 fixture 归属校验通过 `WF_HOST_TMPDIR` 衔接：execution 在改写 TMPDIR 前记录宿主/运行器临时存储根，`fixture_scope.validate` 同时接受该根与命令私有根，夹具仍不得落在受保护路径或共享 hub。
- 候选审计只有在全部登记 ID 都有本次运行、无证据异常行（安装/收据不成立）时才发布；行级 `bad` 属合法审计事实，以 `audit.status=complete|failed` 区分“全绿”与“含预期 dev-only 失败断言”。
- `unit_outcomes` 在独立 repro 角色（无单元）下省略；`failure_owner` 的 typed 计数始终存在（缺省为 0），旧 schema4 摘要读取路径不变。
