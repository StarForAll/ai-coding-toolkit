# 实施计划与验证销账

> 实施状态（2026-11-16）：本计划已执行；实际验证见 [validation.md](./validation.md)。
> 需求：[prd.md](./prd.md)；技术契约：[design.md](./design.md)。
> 性能偏差（52.8s → 66.11s，+25.2%）已在 PRD 的“实施结果与已登记偏差”登记并按审查口径接受；
> 复选框保留为计划清单，不代表未执行。

## 0. 启动前

- [ ] 用户明确批准最新三份规划材料；如有实质改动，重新交审。
- [ ] 再次检查工作区，记录相对基线的所有未提交/暂存/未跟踪路径，保护其他工作。
- [ ] 加载 `trellis-before-dev`，读取 scripts/docs 对应 spec；安全/协议改动先有针对性失败行为断言。
- [ ] Codex inline；空 JSONL 不供子 agent 使用。批准后才执行 `task.py start --allow-empty-context`。
- [ ] 公共新 helper 的 fake-tree、输入身份、独立 CLI 路径一起列入影响表；不动态跳过依赖。

## 1. P1：管理路径的唯一规则（R1）

- [ ] 新建作者侧 `scripts/wf_test_paths.py`，抽取并委托现有 scope 读取/解析规则；不复制第二套 marker 身份。
- [ ] 统一完整 layout，覆盖结果/缓存/state/发行/template/candidate/fixture/pycache/所有 sidecar；无 scope 保持既有默认。
- [ ] public bootstrap 禁止 pyc，完成 scope 检查后再启用写入；移除 list/dry-run 短暂落地的计数文件。
- [ ] 全部独立 CLI 与内部 consumer 在首次写前消费同一规则，保持锁域和所有权规则。
- [ ] 增加不存在 `..`、父链接、坏链、相似前缀、域外 release cache/pycache、派生 sidecar、零写计划的反例；验证 outside sentinel 未变。
- [ ] 先定向再跑 r67 fake-tree 冒烟；路径 helper 缺失必须明确失败。

## 2. P2：证据协议与校验链同批切换（R2/R3/R6）

- [ ] `execution.verdict` 显式 phase；worker、validate_repro、gate、writer 同批消费。
- [ ] green 清除继承注入变量；red 显式注入，保留多行合法 detail。
- [ ] runtime 复用 Resolver 的完整 role 身份摘要；实际 tool/SUT 调用来源可核对。
- [ ] 升级 bundle/state/context，旧证明只作 legacy；覆盖 dev auto both、candidate auto 拒绝/匹配复用、显式 green 不续签 red。
- [ ] 模块导入和 typed 错误归因覆盖读取/JSON/结构错误，输出不得再次异常；检查所有复核入口。
- [ ] 对 wrong-phase 日志同时断言 gate 非零与 writer 未调用；同路径替换二进制/SUT 版本使旧 proof 失效。
- [ ] 用 3/30 case 扫描计数确保公共身份只在 barrier 计算；不靠 wall-clock 断言替代计数。

## 3. P3：进程归属与结果成功出口（R8/R4）

- [ ] 先用受控进程建立父先退出 + 子 setsid 的真实反例；记录前序静态推断成立或撤回的证据。
- [ ] `execution.run` 固定为 C→G→S→W；专用 G 在派生 S 前核验 subreaper，S 启动 W 前同样核验，C 不改全局 subreaper。正常 S 回收与 G 故障接管复用算法，不新增无人监督的清理旁路。
- [ ] 建 C↔G、G↔S 两条匿名 socketpair，协议共用有界帧/版本/command_id；READY→START→STARTED、CANCEL→ACK→清理→DONE 全链路含部分传输与 EOF。最终 DONE 只由 G 核验后发 C，W 不继承控制 FD，S 不持 C↔G 端点。
- [ ] 在每次 spawn 前保护 INT/TERM/HUP 窗口，C 锁存取消并恢复 mask；G/S 的忽略设置与 subreaper 核验完成才 READY。独立 exec 路径恢复 W 的正常信号策略/mask，不依赖 restore_signals 或 preexec_fn 代替。
- [ ] 握手失败无 W 也可能已有 S，仍由 G 收已派生子进程；C 不直接强杀 G 假定清理完成。覆盖 START 已发但 STARTED 未回的 S 死亡，避免 PID 消息竞态留下 W。
- [ ] 覆盖正常退出、业务失败、异常、超时、双 fork、嵌套 controller、独立 session、pass_fds 与日志两路；不遗留进程/FD/锁。
- [ ] 取消测试使用自建 PTY/PID/进程组：Ctrl-C、定向 TERM/HUP、进程组信号、各启动/清理窗口、重复取消、C EOF、坏帧/失联，W 信号/mask/FD 不泄漏；不得向真实宿主终端发信号。
- [ ] 设施故障单独注入 S 的未捕获异常、os._exit、SIGKILL、卡住；W 含独立 session、双 fork、真实测试锁/FD，必须验证 G wait S 后实际接管、无残留/锁可重取，最终仍为 infrastructure failure。另测嵌套强制接管无误杀 sibling，以及 G 可捕获异常的最外层清理。
- [ ] 最后监督责任方丢失的故障仅在外层可靠测试收容中注入：断言 cleanup=unknown、归属诊断/恢复提示/无成功，随后由测试外层回收；不能用这条边界替代 G 存活时 S 失败的回收验收。
- [ ] G/S 能力/通道/信号初始化失败不启动 SUT，不冒充普通失败或 skip；C 接完整最终 DONE 并 wait G 才结束，G wait S 且真实后代清空才签 cleaned。取消或设施失败先于最终确认时，目标 rc=0 不得取绿。
- [ ] `results_summary.py` 从冻结输入和已校验结果生成摘要；原子发布、读回和 shell rc 强绑定。
- [ ] 故障注入覆盖创建/写/fsync/replace/readback/清理；无 GATE-OK、非零、原始日志保留，不能读取旧摘要取绿。
- [ ] 同批替换 run_all/repro trap 的 `--cancel-parent-children` 旁路，停止调度并经 owned 调用等待 G 的收口。正常路径不提前杀内层监督方；强制接管由存活祖先 G 明确承担整个真实 owned 子树的暂停派生/终止/wait，不再期待已终止 S 代清理。cleanup 未知时保留夹具/锁现场，不自动删除或重试。

## 4. P4：候选身份、宿主保护与来源覆盖（R5/R7/R9）

- [ ] 候选完整验证统一，命中必须输入=实际候选=meta 且 tag/HEAD 对应；无主目录拒绝。
- [ ] 候选重建先验证新代，锁内发布并保留旧代恢复能力；复用不得改 meta 或虚报 REUSED。
- [ ] 修宿主快照：类前后只读内容/类型/权限/链接清单；读取未知失败；负向自证仅改合成 scope 树。
- [ ] 依 [inventory.md](./inventory.md) 从完整注册表和 `all_cases()` 实际产出建立逐 ID 来源清单（基线 67 单元、85 repro；分组覆盖 54、未分组 31），同时记录分组/元数据缺失，不能只清点 groups 或仅按 candidate_clean 推断来源。
- [ ] 统一库 resolver，candidate 无源码回退；迁移可迁移的行为套件并实跑；源码白盒项逐个登记理由/安装行为对应项。
- [ ] 来源清单与基线/当前全集核对 ID 差集，新增/删除/改名逐项说明，数量相同不能代替集合相同；执行覆盖统计从真实计划和结果派生，排除/人工不算 passed；所有可迁移但未验证项必须清零。

## 5. P5：产品技能根边界闭环（R10，依赖 P1/P2/P4）

- [ ] `payload/install.py` / `payload/bin/uninstall.py` 保持自包含，分别集中同构边界；明确修改 `scripts/wf-dev-deploy.py` 的完整部署计划判定，使首装和追加平台只消费同一组已校验根/落点。
- [ ] 三方首装、追加平台/已有重装升级入口、卸载预览与锁内 apply 先核项目→技能根→资产；不新造 dev-deploy 升级入口或跨进程预览令牌。
- [ ] dev-deploy 的 resolve_skill_roots/plan_deployment 在预览前验证全批，deploy 首装在 mkdir .wf/writer/skills 前锁内重算；add_platforms 在冲突内容读取、pending 筛选、维护写者保存前重算，禁止原直接 join 绕过规范计划。root_record 仅处理已验证根，旧外部 roots 不能当合法绝对根登记。
- [ ] 旧外部 root_ref 拒绝且不删外部对象；项目内合法绝对 root_ref/正常目录继续工作。
- [ ] 预览/本次预检到锁内 apply 根身份漂移须拒绝，先于业务资产/数据/回执写入，既有锁对象语义单列；三方同矩阵对拍，合法 no-op、来源/代次/内容冲突和 nested-repo 原守卫不退化。
- [ ] known-gap 测试转正式拒绝断言；保留候选安装产物级正反用例，并直接测试 dev-deploy preview、首次 confirm、追加 confirm、no-op（每项含适用的合法/域外根/祖先链接/根下资产越界/坏链/锁前后漂移）。外部哨兵均在测试 scope 内，校验域外与项目业务状态未变。
- [ ] 同步 dev-manifest 中已有资产摘要的生成链；如新增产品文件则登记 asset，不手填生成摘要。
- [ ] 使用现有构建器重建当前正式发行版本，验证字节复现/token parity；不手改 generated release、不自动提版本。

## 6. P6：文档和最终集成

- [ ] README/spec 中 scope、证据相位、身份迁移、清理和成功语义与实现同批更新；撤销已修 known-gap 的当前声明，保留归档原文。
- [ ] 若触及 wf 上位稿，仅同步已有边界的实现状态；按相关 revision gate 校验索引/引用，不顺手改产品政策。
- [ ] 建 `validation.md`：每个 AC 对应代码、测试名、实测结果和证据路径；未跑/skip/无法测量单列，不改写为通过。
- [ ] 复查每个公共 helper 的所有调用方、导入路径、假树副本、缓存/proof 依赖登记、协议 consumer 与清理责任。
- [ ] review 全部 diff、暂存与 untracked；确认无临时脚本/夹具/pyc 落源树，无用户缓存改写。

## 7. 验证命令与隔离约束

全部实现级命令待批准后执行；解释器固定项目声明的 `/softwares/python/bin/python3`。T0 用仓库外 pycache；需要真实 runner 的测试独占 fixture，禁止与其他 runner 并发根调用。

```bash
# 定向模块：新增模块按实现落点补入，不创建重复测试入口
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest \
  scripts.tests.wf_runtime.test_fixture_scope \
  scripts.tests.wf_runtime.test_execution \
  scripts.tests.wf_runtime.test_results_gate \
  scripts.tests.wf_runtime.test_repro_selection \
  scripts.tests.wf_runtime.test_prepare_candidate_repo \
  scripts.tests.wf_runtime.test_test_release

# 快速回归与慢契约分别运行，避免先全量再定位
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .
PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache WF_SLOW_TESTS=1 /softwares/python/bin/python3 -m unittest scripts.tests.wf_runtime.test_run_all_contract
```

全量执行前，通过修正后的 scope API 建 owned 临时域，并显式/默认派生所有管理路径；命令的 scope、发行/cache/state/fixture/pycache/result 归属写入证据。不得复制旧方案中只隔离 results 的命令。安装/卸载故障用外部兄弟目录，但整个合成项目仍在 owned scope 内；不操作真实项目或宿主确认记录。

随后按顺序：相关子集 + repro green → full green 并行 → full green `--serial` → 名称/rc/status/phase/verified 逐项对拍 → full both（本任务修改 repro 断言/协议）→ 候选安装回归及 R10 边界正反用例。候选最终 green 证明要使用重建后的同一版本/ref/内容，不能借修复前 dev red；dev red/both 先建立对应新证明。

```bash
/softwares/python/bin/python3 scripts/build-wf-release.py --verify --verify-token-parity
/softwares/python/bin/python3 scripts/validate-wf-design.py
/softwares/python/bin/python3 scripts/check-doc-refs.py
./scripts/validate-skills.sh
/softwares/python/bin/python3 trellis-library/cli.py validate --strict-warnings
```

仅在确认无失败、无新增改动时结束验证；失败先诊断，不盲目重复整套。记录 cold/warm、有效并发、实际测试数与跳过原因，对照既有约 53s full green 和约 136s 契约的证据判断是否出现新的重复工作，不新增与机器性能绑定的硬失败门槛。

## 8. 逐项证据矩阵

| AC | 必需行为反例 | 正常/幂等/反向守护 | 测试责任面 |
|---|---|---|---|
| AC01 | 不存在的 `..` / 父链接落点被拒，域外零新建 | scope 内未建目录合法、相似前缀拒绝 | test_fixture_scope、新 path helper 测试 |
| AC02 | 域外 release cache/sidecar/pycache 在首次写前拒绝 | 仅设 scope 所有默认管理路径入域；list 零写 | test_test_release、test_run_all_contract、协议入口 |
| AC03 | red 日志只有 PASS green、反向/混相位都拒绝 | 正常多行 detail 正确相位通过 | test_evidence_protocol::VerdictTest；gate/writer 由 test_results_gate、test_repro_selection 覆盖 |
| AC04 | gate 与 writer 均拒绝 wrong-phase，不提交 state | green 不续签 red；green 清注入 env | test_repro_selection、worker/harness 测试 |
| AC05 | 同路径 binary/SUT 版本变化使 proof/context 失效 | 同内容身份稳定，路径重定位按既有域规则 | test_python_runtime_identity、test_repro_selection |
| AC06 | 旧/坏 proof 不可复用，candidate auto 不借旧 red | 新同主体 dev red → candidate auto green | test_repro_selection、慢契约 |
| AC07 | summary 任一发布/读回步骤失败，最终非零且无 GATE-OK | 成功摘要完整/可读回；重用结果目录无旧证据 | summary 测试、test_run_all_contract |
| AC08 | 清理 unknown/失败/残留不报成功，不删锁强接管 | 正常取消与 G 接管 S 故障后，owned 后代/FD 释放且 fixture/results/release 锁可重取，日志保留 | test_execution、慢契约 |
| AC09 | 输入 A/候选 B、tag/HEAD/meta 漂移不可 REUSED | 同输入真正复用且不写；check 只读 | test_prepare_candidate_repo |
| AC10 | 候选发布失败不丢有效旧代，无主拒绝 | 首建/重复/受控重建恢复一致 | 候选事务与 scope 测试 |
| AC11 | 默认 bundle、坏 JSON/非对象/缺字段/读失败稳定非零 | 默认路径与显式路径在成功/失败两种场景均等价 | test_results_gate |
| AC12 | 畸形 phase/计数/非有限值不进入成功汇总 | 合法失败结果归因正确，无二次异常 | test_results_gate、test_repro_selection |
| AC13 | 深层内容变化且顶层 mtime 不变仍被检测 | 缺失/空树区分、合法只读不误报 | 快照自证测试、慢契约 |
| AC14 | 链接换目标/权限变化/读取未知能检测 | 不跟随外部链接、不记录敏感原文 | 同上 |
| AC15 | 父退出 + setsid/双 fork 后代仍被清理 | 正常 rc/日志/pass_fds 保真，sibling 不被回收 | test_execution 真实 scope 进程 |
| AC16 | S 在 STARTED 前/持锁/清理时崩溃、os._exit、SIGKILL、卡住均不得只报错留后代；G 失去最终核验时不伪报 cleaned | 自建 PTY/信号/EOF/部分帧与握手 barrier；G 接管真实后代并 wait，C 等 G 最终 DONE+退出；嵌套取消/接管、原 rc/日志/FD 保真；可靠外层故障收容 | test_execution、test_run_all_contract、run_all/repro trap 集成 |
| AC17 | 只按 groups 清点、遗漏未分组/无元数据 ID、candidate 缺库回退源码或误标均不得通过 | 逐 ID 来源表覆盖完整发现集合；基线 67 单元、85 repro，含 54 分组成员及 31 未分组成员；可迁移套件 candidate 实跑 | 来源 resolver/注册表测试、candidate 套件 |
| AC18 | 同数量但换 ID 必须报差集；排除或 manual 不计 passed，未验证项不销账 | 新增/删除/改名有处置，既有用例和 expect 守恒，新增预算明确 | test_test_runner_plan、最终覆盖表 |
| AC19 | install/uninstall/dev-deploy 任一技能根/祖先/资产落点越界均整批拒绝；dev 追加平台不能绕过 | dev preview/首次 confirm/追加 confirm/no-op 直接验证，域外和项目业务状态不变；合法路径通过，既有锁语义单列 | 三方参数化边界测试、dev-deploy 直接集成、candidate 负路径 |
| AC20 | 预览/单进程预检到锁内根漂移失效；旧外部 root_ref 不删除/合法化 | 正常幂等、原确认机制不变，dev 不新增跨进程令牌，原保护不退化 | install/uninstall/dev-deploy 对拍与漂移注入 |
| AC21 | 任一缺结果/协议混读/输入漂移继续阻断 | 串并对拍、全量 both、新候选证明 | 原有全量与新协议集成 |
| AC22 | 生成树手改、旧 known-gap 声明或输入漏登记不得收口 | 构建器字节复现、文档与实现一致 | 发行/文档校验、最终逐项 diff |

## 9. 交付边界

本任务不通过 commit/push/archive 自动收尾。向用户交付全部 AC 的实际证据及剩余外部验证项；未经另行授权不提交、不改历史、不清除其他人的工作。任一脚本可解决的范围内缺口未闭环时，报告未完成，不能把它改名为“已知限制”来销账。
