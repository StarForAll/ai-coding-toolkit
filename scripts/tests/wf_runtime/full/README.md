# wf 运行期全流程用例（手动运行）

这些脚本是 2026-11-03 各轮复核期间的三夹具验证资产，已固化进仓库以免随会话丢失。
它们**不在** `unittest discover` 的默认范围内，需要显式运行。运行器会写测试发行缓存、
结果目录和临时夹具；`cp3/r1r2` 的用户配置写入使用独立测试目录，结束后清理。

## 前置

1. 解释器：`/softwares/python/bin/python3`（authoring 侧）。
2. 夹具：`bash wf_fixture.sh [夹具目录] [nocap]` 会从 `docs/workflows/wf/payload`
   部署开发态运行时（调用 `scripts/wf-dev-deploy.py --confirm`）。夹具必须是新目录或带本工具所有权标记的目录；拒绝非空无主目录和符号链接。
3. `run_all.sh` 自动分配临时夹具；`WF_FIX` 可指定安全临时路径。直接使用 `wf_fixture.sh` 时默认 `/tmp/wf-fixtures/f1`。

### 宿主前置条件（HOME 由宿主提供，运行器不隔离）

被测 SUT 把用户级环境当作执行事实的一部分，因此下列宿主条件必须就绪，**否则套件会在
`task-new`/`task-check` 阶段被 SUT 拒绝**（不是运行器缺陷，也不得用假 HOME 绕过）：

1. **执行器确认**：`~/.wf/interpreters.json` 里有与当前解释器匹配的确认元组。
   缺失时 `task-new` 返回 `WF_EXECUTOR_UNCONFIRMED`（`facts.reason="no matching confirmation tuple"`）。
   恢复方式是在终端里对夹具实际使用的解释器执行一次
   `python3 <项目>/.wf/bin/wf.py confirm-executor --scope system`（非 TTY 会被拒绝，这是产品规则）。
2. **git 身份**：夹具内的 `git commit`（首个 HEAD、归档提交）需要 `user.name`/`user.email`
   （全局 `~/.gitconfig` 或仓库级配置皆可）。

契约测试据此**不隔离 HOME**：`WF_TEST_SCOPE_ROOT` 只约束 runner 管理的写入口
（results/cache/state/fixture/pycache/release 缓存），HOME 保持宿主值；用户 cache 与生产结果锁
只用"存在性 + inode/mtime 快照"证明未被触碰。A/B 实测（同一 HEAD 代码、同一 scope、只改 HOME）：
scope 内 HOME 会让候选流程 f0 的 `task-check` 变成 `WF_CHECK_STALE`（9 项里 3 项 FAIL），
宿主 HOME 则全绿——换 HOME 等于改被测语义。

## 用例

| 脚本 | 覆盖 |
|---|---|
| `f1_init.py` | 初始化任务闭环（baseline-apply → Check → 知识处置 → 归档） |
| `f1_ordinary.py` | 普通任务闭环（含 `enable`） |
| `cp1_tests.py` … `cp5_b345.py` | 第一轮复核的 A 类修复回归 |
| `r1r2_tests.py` | R1 成组写入与接续、R2 `confirm-executor` 交互闸门（pty） |
| `r35_tests.py` | R5 `install.py` 记录下的卸载、R3 锁的人工出口 |
| `r7r15_tests.py` | 第三轮 R7–R15（写入边界、续做、双轴、finish 验证、人判绑定、spec 兜底、归档持久化、锁） |
| `r17r24_tests.py` | 第四轮 R17–R24（spec 授权、核实并集与到期、整批冲突、归档引用、结束前重算、TDD 结构、归档续做、放弃处置） |
| `r25r30_tests.py` | 第五轮 R25–R30（核实周期配置与 spec_review、冲突判定时机；R25/R27/R29 的用例在 `r17r24_tests.py` 内） |
| `r31r34_tests.py` | 第六轮 R31–R34（归档/放弃的步骤恢复、写权锁内重核、保留 WIP 判据、规则版本门禁） |
| `r35r37_tests.py` | 第七轮 R35–R37（异常归档按步骤恢复并在锁内、锁内完整写权核验、真实 `stop keep` WIP 判据） |
| `r38r39_tests.py` | 第八轮 R38–R39（授予写权的统一前置、保留 WIP 随实际处置解除） |
| `r40r42_tests.py` | 第九轮 R40–R42（未登记脏改动计入前置、同对象接续放行并交回 WIP、恢复前指纹核对） |
| `r43r45_tests.py` | 第十轮 R43–R45（命中规则进入检查锚点、显式归属优先于 glob 重叠、已持久化删除的恢复） |
| `r47r48_tests.py` | 第十二轮 R47–R48（spec 读取的真实落点、写入拒绝嵌套仓库）；`r46_tests.py` 为第十一轮（单条非法路径只失效该条） |
| `r49_tests.py` | 第十三轮 R49（链接把目标带进项目内嵌套仓库时，读/写两侧都拒绝） |
| `r50_tests.py` | 第十四轮 R50（baseline-apply 与 spec 写入对同一嵌套仓库目标作出一致拒绝） |
| `r51r52_tests.py` | 第十五轮 R51–R52（复杂产物门禁、disable 后 frontmatter 复验） |
| `r53_tests.py` | 第十六轮 R53（空产物拒绝、连字符字段标记识别与登记） |
| `r54_tests.py` | 第十七轮 R54（四项条件汇总后才分级、降级须理由与证据） |
| `r55_tests.py` | 第十八轮 R55（批准决定类型/对象必须被消费，拒绝不得放行） |
| `r56_tests.py` | 第十九轮 R56（核实周期非法值阻断、键缺失走缺省） |
| `r57_tests.py` | 第二十轮 R57（统一配置取值器：非法/整体不可读一律阻断，键缺失走缺省） |
| `r58_tests.py` | 第二十一轮 R58（结构/字段两级问题分类、调试阈值非法阻断归档门禁） |
| `r59_tests.py` | 第二十二轮 R59（维护回执可达提交查证接入统一读取，已提交即派生 persisted） |
| `r60_tests.py` | 第二十三轮 R60（查证核提交树终态、按路径稳定排序、待核回执进入门禁） |
| `r61_tests.py` | 第二十四轮 R61（按提交树重建完整指纹核验、探测异常仍可定位路径） |
| `r62_tests.py` | 第二十五轮 R62（审查 outcome、调查成果、knowledge 写者、启动核验落点、降级哈希域、归档写入） |
| `r63_tests.py` | 第二十六轮 R63（日志与 facts 秘密边界脱敏、副本来源登记） |
| `r64_tests.py` | 第二十七轮 R64（P3：spec facts 收缩、generation 校验、未知 step 留痕、源树卫生等） |
| `r65_tests.py` | 第二十八轮 R65（review-passed 恢复 complex、降级核验入 final_gate、outcome 单调、调查判据收紧） |
| `d1_tests.py` | D1 实跑（真实 `$DSH_SESSION_ID` 绑定/重入/压缩边界/新会话/wf 身份拒绝面）；**手动执行，需真实宿主压缩，不计入 `run_all.sh` 分母** |
| `d1_wf_tests.py` | D1 的 wf 签发路径（`provider=wf` 携带/恢复/复制到新会话/丢失）；**同上，手动执行、不计入分母** |
| `r66_tests.py` | 第二十九轮 R66（实例标识、写者结构、终态、义务来源、重复记录） |
| `r67_tests.py` | 第三十轮 R67（写权入口实例/能力、baseline 状态与提案、清单声明、聚合脚本退出码） |
| `r90_tests.py` | 第五十八轮 R93（平台清单即身份事实：未装宿主只读放行/写阻断、多 agent 交替不覆盖、追加平台） |
| `r89_tests.py` | 第五十七轮 R92（`--platform` 平台表、项目内技能目录、安装产物归入控制面） |
| `r88_tests.py` | 第五十五/五十六轮 R90–R91（第十一轮复审 D1–D4：早期中断可恢复、实例固定、伪造 done 被拒、旧动作出口） |
| `r87_tests.py` | 第五十四轮 R89（裁决 A：writer 单一父动作、Finish→Check 受控迁移） |
| `r86_tests.py` | 第五十一～五十三轮 R86–R88（第八至十轮复审：删除归属崩溃、证据引用分类、d 桶、异常归档、预览一致、复现校验、活冲突语义） |
| `r85_tests.py` | 第五十轮 R85（第七轮独立复审：创建/绑定意图协议、索引去重、复盘证据、安装预览、P2 四项） |
| `r84_tests.py` | 第四十九轮 R84（第六轮独立复审：改名/停用后像与索引、JSON 归一、恢复期身份核验、bind 意图先行） |
| `r83_tests.py` | 第四十八轮 R83（第五轮独立复审：自造词表收回、transport 收窄、自证证据拒绝、续做三态全覆盖、task-new 恢复可达） |
| `r82_tests.py` | 第四十七轮 R82（第四轮独立复审 + 其他 agent 反例：解除依赖写入、巡检误报、报告重核、续做三态、能力结构） |
| `r81_tests.py` | 第四十六轮 R81（第三轮独立复审 + 其他 agent 反例：install 边界、manual 证据、归档恢复、脱敏、规则指纹、能力结构） |
| `r80_tests.py` | 第四十五轮 R80（第二轮独立复审反例：Check 结构、处置事实、裁定标识、脱敏、计数） |
| `r79_tests.py` | 第四十四轮 R79（E 复审缺陷：哈希公式、Check 结构、处置事实、裁定精确匹配、脱敏） |
| `r77_tests.py` | 第四十一/四十二/四十三轮 R77–R78（未知压制候选、非法配置阻断、改名映射、畸形条目、活动任务依赖保护、归档事实完整性） |
| `r76_tests.py` | 第四十轮 R76（回收候选语义、周期触发基数、存活探测的恢复闭环） |
| `r75_tests.py` | 第三十九轮 R75（bind 实例一致性、报告重哈希、槽位完整性、巡检治理面、锁存活探测） |
| `r74_tests.py` | 第三十八轮 R74（写入白名单统一、activation 覆盖 start 路由、工作树枚举同源） |
| `r72_tests.py` | 第三十六轮 R72（卸载入口的清单一致性与资产边界） |
| `r71_tests.py` | 第三十五轮 R71（交接实例核验、dispose 锁内重核、审查固定五轴） |
| `r70_tests.py` | 第三十四轮 R70（卸载预览指纹 vs 发行摘要、审查判否必须落盘） |
| `r69_tests.py` | 第三十三轮 R69（前像结构、整批预检、导入冲突与门禁引用、卸载内容重核） |
| `r68_tests.py` | 第三十一/三十二轮 R68（审查判定六核、repair 锁内重核与预览指纹、基线批准绑定与前像、续做三分类） |

全量复现：`bash run_all.sh`——**每个套件使用独立夹具副本**，因此与跑序无关；不需要中间手工 pause/release。
脚本会校验夹具建成、初始化退出码、套件退出码、`[FAIL]` 行数与汇总通过数，任一不符即计失败并以 `exit 1` 结束。
| `p5_v1.py` / `p5_v2v3.py` / `p5_v5.py` / `p5_spec.py` / `p5_f0.py` | V1–V5 与 F0 |

## 用法示例

```bash
WF_SUITES="r68_tests r71_tests" bash scripts/tests/wf_runtime/full/run_all.sh
WF_TAGS=review bash scripts/tests/wf_runtime/full/run_all.sh
bash scripts/tests/wf_runtime/full/repro/run.sh --group review --mode green --jobs 4
```

`repro/run.sh` 的公开参数只有一处解析：`repro/cli.py`（argparse，shell 只消费其 shlex 引用输出）。
有值选项缺值/空值/后继选项冒充取值、未知选项、`--list` 与 `--mode` 同时出现等非法调用都在租约、
layout、scope、cache、build 之前以 rc=2 退出，不产生任何写入；`--list`/`--help` 仍是纯选择面。
内部 `--_wf-*` frame 仍先由 `runner_protocol.py` 整体剥离，公开 parser 看不到保留选项。

使用运行器单跑，确保夹具部署、初始化和模板复制顺序一致。旧夹具没有所有权标记时，换一个新临时路径；不要让运行器接管已有内容。

**套件自带夹具（2026-11-06 W1）**：`cp4_a8` / `cp5_b12` / `r35_tests` 曾因写死 `/tmp/wf-fixtures/{fu,f5,f3,f2}`
且无人创建而脱离 `run_all.sh`（cp5_b12 当时已红 4 条而无人知晓）。现在它们在脚本内自己调用
`wf_fixture.sh` / `f2_setup.sh`（cp5_b12 另跑 `f1_init.py` 补初始化任务），不依赖兄弟套件或调用方的 `FIX`。
新增套件若需要非 F1 夹具，按同一方式自带，不要假设某个固定 `/tmp` 目录已存在。

## 并行与子集

- 默认 `min(8, cpu_count)` 并发（`WF_TOTAL_JOBS` 可覆盖，兼容 `WF_JOBS`；`--serial`/`WF_JOBS=1` 退回串行）：每个 worker 用 user namespace 私有 `/tmp`，只读挂共享发行仓库；`unshare` 不可用时自动退回串行。**flows/extra 与 suites 同池**（每个单元仍有私有夹具与私有 `/tmp`），`--serial` 时全部单元走宿主 `/tmp`、无 `unshare` 的串行域（AC1 的对拍面）。
- 迭代期只跑相关单元：`WF_SUITES="r88_tests r89_tests" bash run_all.sh`（约 4.5s，跳过 f0/p5 流程）。
- **注册表是 `units.json`（顶层 `units`）**：每个可计划单元声明 `expect`（期望用例数）/`fixture`/`script`；
  `plan.py` 下发五段记录 `name:kind:expect:fixture:script`，worker 只按记录执行（`f0` 的脚本是
  `p5_f0.py`，不按名字拼 `.py`）。少跑用例 → `execution.verdict` 的 observed≠expect → 整次红。
- **串行集合已清空**（2026-11-14）：原 13 个强制串行套件全部转入并行池——chmod 写入失败
  注入改由 `wfdrive.deny_writes` 的三探针等价契约承担（chmod 层 + ro bind mount 层按探针
  结果选择，user namespace 内同样成立）；其余 11 个保守遗留项经五项审计（夹具来源/共享
  路径/用户状态/pty·sleep/嵌套运行器）确认并行安全。今后确需串行的单元：`units.json`
  置 `"parallel": false` 并在 `notes` 登记理由（`plan.py::load_units` 校验 notes 非空）。
- `cp3/r1r2` 的 `--isolated-user` 由 `units.json` 的 `isolated_user` 字段下发
  （`plan.py` → `PLAN_ISOLATED_UNITS` → `WF_ISOLATED_UNITS`，run_all/run_one 同一成员判定）。
- 复用发行缓存：`--no-build`；会核对 build inputs 与实际发行树摘要，过期即拒绝。
- **repro 默认在主池之后串行**（决策：并发编排只值 3–6s 且引入抖动）；显式开关 `--repro-concurrent`
  才让 repro 与主池并发，预算按 5/3 分配（`plan.py` 一处推导）。两条路径都记录 `pool_seconds`/`repro_seconds`。
- `summary.json` 采用 **schema 3**：`run_id/role` 与同代 `run-state`/`.runner.json` 一致，
  `input_evidence` 记录实际消费的 metrics/plan/context/lines/unit/repro 快照（sha256+size），
  `cleanup_state/cleanup_report/evidence_state` 只来自当前 controller 证据；`gate` 与计数来自
  `results_gate.assess_run_results()` 这一处实现。`status=ok` 同时要求门禁、`cleanup=cleaned` 与
  证据完整。计时/并发/模板事实经 **schema 1 `summary-metrics.json`** 交接（绑定本代 run_id/root/role
  与输入摘要），controller 侧 `read_metrics` 重算并逐项比对；旧无 ID metrics 只作历史展示。
  模板来源三键、`pycache_root` 与 60s/65s `budget` 仍只报告不硬失败。
  成本账目另有两个只读字段：`release_build`（controlled 阶段从 `release-context.json` 搬运的
  `built|reused|checked`）与 `template_build_sequences`（模板缓存命中=0、本次发布一次=1、模板机制关闭=0）。
- `WF_COMMAND_TIMEOUT` 是单个运行器命令的秒数上界（默认 180）；repro 用 `WF_REPRO_TIMEOUT`（默认 120）；整次 run 用 `WF_RUN_TIMEOUT`（默认 1800）。超时结束子进程并计失败，日志与结果保留。
- 全局 `flock` 拒绝重叠运行；worker 的私有 `/tmp` 不挂回宿主夹具目录，仅共享结果与只读发行/模板。缺结果直接计基础设施失败，不静默重跑。
- **阶段与 frame**：入口先是 `public`（记原始 results 显式性、一次禁写 pyc 的 preflight；list/dry-run 在此结束），
  然后 `exec` 进 `lease`（fixture→当前域结果锁、**一次 `resource_lifecycle.begin-run`** 写 schema2 owner →
  active run-state → 按旧代许可 prepare、唯一一次 final plan 并写 `plan.json` 字节 + token），
  controller 起 `controlled`（取并保持 release 独占锁、ensure/核验、原子写 `release-context.json`），
  最后 `exec` 成 `execute`（第三次脚本重入、最终 consumer：核祖先/三把锁/两处冻结字节后才执行，不再 plan/ensure；
  内层只写目标结果与 schema1 metrics，没有成功出口）。
  内部 frame 由 `runner_protocol.py` 唯一编解码，语法 `--_wf-internal <lease|controlled|execute> <固定键> -- <用户参数>`；
  用户 argv 出现保留 `--_wf-*` 即拒绝。异常和取消由 controller 统一等后代退出后清理。
- **结果锁域**：生产域固定 `/tmp/wf-test-results-<uid>.lock`（一个 UID 一把，不为每个 run/目录建 sidecar，
  prune 不回收）。显式镜像只短期持结果锁写 plan/owner marker；普通无显式结果的 list/dry-run 不取锁。
  锁序固定 fixture → results → release。
- **测试域 `WF_TEST_SCOPE_ROOT`**：`fixture_scope.py create-scope` 建 owned scope，结果/cache/meta/state/夹具根/pycache/HOME
  等 runner 管理写入口必须落在 scope 内（越界写前拒绝）；它**不是**任意 syscall 沙箱——suite 自己的固定 `/tmp` scratch
  仍按既有并行私有 tmpfs / 宿主串行语义。测试结果锁为 `<scope>/locks/results-<uid>.lock`；真实 full fixture 慢测的
  既有独占前提不取消。
- **namespace 边界**：覆盖 `/tmp` 前记录宿主 mount 域，覆盖后关闭本 worker 继承的宿主结果/release FD 副本（不 unlock），
  清 locator 并标 `WF_UNIT_DOMAIN=unit`；生产锁 helper 在域不符时拒绝，不把私有 `/tmp` 同名 inode 当宿主锁。
  显式 scope 的 fake runner 可在自己 scope 内建测试锁，但不能声称继承宿主锁。
- run 级删除只由同 C 进程的 root controller 在 `runner_cleanup.finalize` 执行（固定角色序
  FIX → LEGACY_FIXTURE_ROOT → RUN_TEMPLATE，首次失败即停并报告 removed/failed/not-attempted）；
  `execute` 的 EXIT trap 不再提前删除。结果目录必须为空或由本工具按协议创建；
  上一代 `active`/证据不完整/有 KEEP 的现场不会自动复用，需用

  `fixture_scope.py inventory-results` → `retire-results` 明确处置。
- **测试发行消费期**：`<root>.lock` 是根外固定 inode，ensure/恢复/发布独占、check 共享只读；runner 在同一 PID
  保持独占到全部 worker/repro 结束，外部 ensure/check 得到明确 busy（退出 75）。`--check` 遇到未完成 journal
  返回 recovery-required（只读，不恢复）；恢复入口是 ensure。

## 结果缓存轮转

- run_all（`--scope run`）与独立 repro 入口（`--scope repro`）在 `begin-run` 之后各自回收
  **本前缀且 `finished+cleaned+evidence=complete`** 的结果目录，保留最近 20（`--keep`）；
  `active`/unknown/KEEP/无主/旧格式一律不自动轮转。root 经 `WF_RESULTS_CACHE` 注入
  （默认 `~/.cache/wf-test-run`）——契约测试指向临时根，不触碰真实用户缓存。
- `--bootstrap`（仅手工）不再凭“顶层看起来已知”删除无主目录：只报告
  `needs-retirement-review` 并以非零退出，处置走 `retire-results`。prune 的 liveness 保障隐式依赖全局 flock 单运行器。
- **模板跨 run 缓存**（`<WF_RESULTS_CACHE>/template/<key>/` + 同级 `<key>.meta.json`，实现见
  `template_cache.py`）。身份 = `sha256` 规范 JSON：登记资产、dev-manifest、build/测试/runtime
  helper 字节、tool 与 SUT **路径字符串身份 + binary 字节**、full 受控子树、协议 schema、
  dev 完整 HEAD 或候选 release subject；`key = <inputs_digest12>-<slot>`，slot 是
  `py<major.minor>-<deploy>[-<version>-<ref>]` 的 urlsafe-base64 编码（可逆、无分隔符碰撞）。
  纯 `touch` 不变，dirty 字节即 miss；**dev HEAD 不可读时固定退回 run-owned 模板**，不读写跨 run 槽。
  发布走有界 journal（staging → journal → backup/安装 → repoint → 摘要/meta → 验证 → 提交）：
  repoint 会改写记录路径，摘要只能在 repoint 之后算；带摘要且验证通过的新代才前滚，否则按冻结旧代回滚，
  两代都不可验证时 fail closed 保留现场。meta 是 schema 1，命中要求 `meta.root`、`meta.key`、
  `inputs_digest`、实际 tree digest 全 match，并过空态/身份校验与 `source_hygiene --strict`；
  缺 meta / 旧无版本 meta 只算 miss。只迁移同 Python/deploy/release 槽位且 owner/root/身份完整的
  legacy key（<digest12>-<pyver>-<deploy>[-<version>-<ref>]）；其他版本、无主与归属不明目录不自动清理。
  修改型入口只有 `template_cache acquire`（恢复→迁移/命中→必要时发布）；只读 `lookup` 遇到未完成
  journal 返回 recovery-required（不写）。发布失败/中断后的恢复材料由 `inventory` 标明，
  无主 staging/backup 只在带 fixture marker 时算 owned，其余归 unproven。
  「同槽位单条」意味着：共用 cache 的 dev 双 checkout/worktree 在不同 HEAD/dirty 输入下交替使用会反复
  miss/重建（candidate 同 version/ref 异内容同样），槽数量仍随版本/deploy 组合增长，没有全 cache 上限。
  克隆后 `--repoint-from <meta.root> --expect-repoint-min 1`，**0 改写 = 该单元失败**
  （`TEMPLATE-REPOINT-MISMATCH`）。开关：`--no-template`（整套模板机制，含缓存）与
  `--no-template-cache`（只关跨 run 缓存）。
- **pyc 策略**：运行器统一下发 `PYTHONPYCACHEPREFIX`（默认 `$RESULTS_DIR/pycache`，`WF_PYCACHE` 可注入），
  不再使用 `PYTHONDONTWRITEBYTECODE`。pyc 不落源树、不落夹具；`source_hygiene.py` 在 run 前后做
  delta 对拍（新增即 `SOURCE-TREE-POLLUTED`），模板缓存条目用 strict 绝对判据。
- 直接 `plan.py --list` 不再创建结果目录；`run_all.sh --list/--dry-run` 默认零写入（无 lease/结果/日志/pycache/prune）。
  只有**显式** `WF_RESULTS_DIR` 才写 plan.json + owner marker，并在当前域结果锁下短期完成。

## 隔离 scope、成本账目与证据计数（2026-11-15）

- **宿主保护的终态证据**：类入口/出口对 `~/.cache/wf-test-release`、`~/.cache/wf-test-run`、
  `~/.cache/wf-candidate-repo` 与生产结果锁做只读树清单（相对路径/类型/权限/regular 文件字节摘要/
  链接目标；不跟随树外链接、不记录内容），缺失、空目录与正常目录区分。每次调用仍保留轻量
  inode/mtime 定位证据，但不再是终态证明（`host_snapshot.py`，含深层改写/改权限/换链接/增删/
  不可读的自证用例）。
- **契约测试的单 scope 口径**（`scripts/tests/wf_runtime/test_run_all_contract.py`，`WF_SLOW_TESTS=1`）：
  整个 class 只建一个 owned scope（`fixture_scope.py create-scope`）+ 空 pool 布局
  `pool/results-cache`、`pool/test-release`；每个逻辑 case 有自己的 `state`（同一 case 的多次调用
  共用 state），每次 runner 调用有自己的 `results`/`fixture`/`pycache`。helper 注入缺一即失败：
  `WF_TEST_SCOPE_ROOT`、`WF_TEST_RELEASE_CACHE`、`WF_RESULTS_CACHE`、`WF_TEST_RUN_CACHE`、
  `WF_PYCACHE`、`WF_RESULTS_DIR`、`WF_FIX`。**HOME 保持宿主值**：被测 SUT 的 check/归档判据依赖
  用户级环境（git 身份、执行器确认），A/B 实测把 HOME 指到 scope 内会让候选流程的 `task-check`
  退化成 `WF_CHECK_STALE`——假 HOME 会改变被测语义，所以隔离只施加在 runner 管理的写入口上。生产结果锁与 `~/.cache/wf-test-release|wf-test-run|wf-candidate-repo`
  只做快照比对（存在性 + inode/mtime），运行前后必须一致；scope 内 create/delete 另行断言。
- **成本与 deadline**：一个逻辑 case 共享一个 900 秒单调 deadline，子进程超时取 `min(剩余, 既有上限)`，
  剩余为 0 直接失败并归因 `case deadline exhausted`（不重置、不加时）。class/case 墙钟、cold/warm、
  `release_build`、`template_build_sequences`、取消窗口等待（15 秒窗口）与清理时间（5 秒窗口）、
  teardown 与剩余 deadline 写进 `<scope>/evidence/class-cost.json`；`WF_CONTRACT_KEEP_SCOPE=1` 保留现场。
- **阶段与计划计数文件**（证据，不是门禁）：`run_all` 在每个阶段入口向 `$WF_RESULTS_DIR/stages` 追加名字；
  `public` 阶段在 begin-run 之前不能写结果目录，由 `lease` 阶段在 owner/state/prepare 之后补记，因此一次真实 run
  是 `public,lease,controlled,execute` 四行。计划计数不再创建 bootstrap 文件：preflight 的阶段行只留在
  内存里，`lease` begin-run 之后与 final plan 一起写 `$WF_RESULTS_DIR/plan-calls`，一次真实 run
  合计 2 行；`--list`/`--dry-run` 全程零写入。
- **调用计数注入点**（默认值不变，仅测试使用；不劫持 PATH）：`WF_TEST_RELEASE_CLI`（测试发行 CLI，
  `release_context.py` 与 `repro/run.sh` 都消费）、`WF_CANDIDATE_VALIDATOR`（候选校验，
  `release_context.py`、`repro/run.sh`、repro 最终 writer barrier 都消费）、`WF_GIT_BIN`
  （`wf_release_common.git_head/git_describe`）。契约用计数 shim（记录 argv 后 exec 真实入口）断言：
  内嵌 repro 不再 ensure/check（一次 run 只剩 controlled 阶段那一次）、独立 repro 入口 1 次、
  候选 validator 起始与结束 barrier 各 1 次、坏候选只有起始 1 次且不启动 worker。
- **release/模板构建次数**：测试发行 meta（schema 2）与模板条目 meta（schema 1）都有一个 additive
  诊断字段 `builds`（首建=1，同输入复用不增）；`wf_test_release.py --ensure --json` 的 `status` 为
  `built|reused`、`--check --json` 为 `checked`，供 summary 与契约账目读取。
- **恢复状态机**（两处 cache 同形，判定只用 journal 冻结的摘要与归属，不比 mtime）：
  1) 新代可验证（已装到根或仍在 staging）→ 前滚；2) 旧代仍在原位且字节等于冻结摘要 → 只清
  staging/journal（**不要求 backup**）；3) 旧代已移走但 backup 可验证 → 按冻结 meta/owner 原文回滚；
  4) 首次发布（old-absent）→ 只撤销本事务的不完整新代；5) 其余 → fail closed、保留现场、非零。
  窗口断言覆盖「journal 后未移旧 / 移旧未装新 / 装新未写 meta / 写 meta 未清 journal / staging 半移动 /
  首次发布半安装」，见 `test_release_lock.py` 与 `test_template_cache.py` 的 `RecoveryTest`。

## 存量盘点与精确退役（唯一入口）

结果/夹具、模板缓存、测试发行缓存各自有 inventory/retire CLI；不再提供手工 `rm -rf` 示例。
三个入口共享同一选择格式（`schema_version/domain/root/entries[]`，见 `resource_lifecycle.py`）、
集合摘要与外部报告写序，但各自重新扫描/核验归属与锁。

```bash
# A) 结果/独立夹具：默认缓存模式或显式精确模式（二者互斥）
python3 scripts/tests/wf_runtime/full/fixture_scope.py inventory-results \
  --cache-root ~/.cache/wf-test-run --format json
python3 scripts/tests/wf_runtime/full/fixture_scope.py inventory-results \
  --results-root /tmp/run-x --fixture /tmp/fix-y --format json

# B) 模板缓存
python3 scripts/tests/wf_runtime/full/template_cache.py inventory \
  --cache-root ~/.cache/wf-test-run/template --format json

# C) 测试发行缓存
python3 scripts/tests/wf_test_release.py --inventory --cache-root ~/.cache/wf-test-release --json
```

把 inventory 输出中实际选中的 `entries` 写成 selection（不要手推删除集合），再按归属等级选择模式：

- `safe-legacy`：只接受严格旧格式 owner 的结果、可验证 fixture/marker 孤儿或空壳；journal/
  新协议保留现场/有效模板或发行代/unproven 材料一律拒绝（有效条目走正常替换或 manual-retained）。
- `manual-retained`：必须真实 TTY + 完整集合摘要短语（`<domain> <root> <digest> abandon`；缓存
  unproven 材料再加 `unproven-cache`）+ 外部 `--report`。非 TTY/EOF/摘要漂移/忙锁/活引用/
  非本 UID/越界均零删除；报告先建，删除/报告 I/O 中途失败即停并保留现场，重试须重盘点。
  坏 journal 的 cache-key reset 必须把同 key 的 entry、全部可识别材料与 journal 一起选中，
  不能只删 journal 留下仍可命中的残代；条目的正式 meta 与材料 marker 随所属树确认不存在的
  同一路径删除，marker 不先于树消失。

```bash
python3 scripts/tests/wf_runtime/full/fixture_scope.py retire-results \
  --selection /tmp/selection.json --retirement-mode safe-legacy \
  --confirm-retirement --report /tmp/retire-report.json

python3 scripts/tests/wf_runtime/full/template_cache.py retire --cache-root <cache> \
  --selection /tmp/selection.json --retirement-mode manual-retained \
  --confirm-retirement --report /tmp/retire-report.json

python3 scripts/tests/wf_test_release.py --retire --cache-root <cache> \
  --selection /tmp/selection.json --retirement-mode manual-retained \
  --confirm-retirement --report /tmp/retire-report.json
```

root 每次真实运行只做一次**浅层** observe（`observe_roots`）：只枚举配置根的直接子项、读取
owner/state/meta/journal 控制记录（单文件上限 1 MiB、不跟随链接），不递归模板树/发行树、不算
字节摘要、不恢复不取锁；输出 `observed_at`/counts/`complete|partial|absent|unverified`/
`capacity=not-measured` 与 shlex 正确的 inventory 命令。深层字节与确认摘要只由显式 inventory 产生。

模板/测试发行事务另提供确定性窗口（仅 `WF_TEST_FAULT_INJECTION=1` + owned scope）：
`WF_TEMPLATE_TXN_STOP_AFTER` / `WF_TEST_RELEASE_TXN_STOP_AFTER` 取
`after-staging-before-journal|after-journal|after-old-moved|after-new-installed|after-meta|
after-material-cleanup-before-journal-remove`；重入真实入口（acquire / ensure）先恢复。
命中会掩盖窗口时用受限的 `WF_TEMPLATE_TXN_REBUILD=1` / `WF_TEST_RELEASE_TXN_REBUILD=1`
（只跳过本次命中，仍走真实 build/journal/move，用完即清）。未开总开关时这些变量全部忽略；
非法点名/越界在首次写前拒绝。

## 产品技能根边界（项目 → 基址 → 资产）

三个入口（`payload/install.py`、`payload/bin/uninstall.py`、`scripts/wf-dev-deploy.py`）用同一判据：
登记基址的实际位置必须在真实项目根内，资产实际落点还必须同时在该基址与项目根内；尚不存在路径
按最近现有祖先解析 `..` 与符号链接，坏链直接拒绝。

- 资产落点本身是指向项目外的符号链接 → `WF_ASSET_DECISION`，整批零写入；
- 技能根目录（如 `proj/.claude/skills`）或其它祖先指向项目外 → 同样整批拒绝；产品修复后
  `test_asset_boundaries.py` 与 `test_run_all_contract.py::test_install_refuses_a_symlinked_skill_root_outside_the_project`
  是正式负断言，不再是 known-gap；
- uninstall 的历史绝对 root_ref 若仍在项目内允许，项目外记录拒绝且不删除外部对象；确认后 apply
  在同一锁内重新解析根并整批复核选中集合；
- dev-deploy 的首装、追加平台、预览与锁内重算共用 `plan_deployment` 的完整计划，`root_record`
  只序列化通过校验的项目内根。

## 证据相位、运行身份与成功出口

- **相位**：`execution.verdict(kind='repro')` 必须显式给 `green|red`；日志里只有相反相位的
  `PASS <phase>:`、空日志、矛盾 PASS/FAIL 或非零退出都不能签发证明。worker、gate、writer 用同一判定。
- **运行身份**：`repro_select._runtime_identity()` 与 `release_context.py` 都用
  `python_runtime_identity.Resolver` 的完整投影（路径身份 + 调用文件字节 + 解释器二进制字节 +
  实现/版本）；同路径二进制或 SUT 版本变化会改变 red subject，旧证明失去资格。
  bundle/state/release-context 成组升级（bundle 3、state 4、execution context 2、release context 2）；
  schema 1/2/3 的 state 只作 legacy 保留，不作新协议证明。
- **公共 helper 身份**：`repro_select.HELPERS` 同时登记 repro 目录内的 8 个 helper（含公开参数
  解析器 `cli.py`）和 `library_source.py`、`prepare_candidate_repo.py`、`release_context.py`、
  `resource_lifecycle.py`、
  `results_gate.py`、`results_summary.py`、`fixture_scope.py`、`execute_gate.py`、`run_all.sh`、
  `wf_test_paths.py`；`public_inputs.helper_set=core-v2`，旧集合的 bundle 在 gate/writer 被拒绝。
  修改这些文件会让 red subject/fingerprint 变化，旧证明必须重新跑。
- **零写入**：`public` 在 layout/scope 校验前统一禁写 pyc（`PYTHONDONTWRITEBYTECODE=1`）并丢弃
  外部注入的 pycache 前缀；`--list`/`--dry-run` 全程不启用 pycache、不写结果目录（显式 dry-run
  仅 plan.json + owner marker）。显式域外 `WF_PYCACHE` 在首次写前被拒，实测域外目录保持不存在。
- **成功出口（唯一）**：root controller 在同一 C 进程内聚合当前证据：`assess_execution/assess_run`
  把进程与本地资源事实和 unit/gate 证据完整性分开归因；`finalize` 只在 `cleanup=cleaned` 时按
  FIX→LEGACY_FIXTURE_ROOT→RUN_TEMPLATE 删除，首次失败即停并报告 removed/failed/not-attempted；
  `summary.json`（schema 3）由 controller 一次原子发布并全对象读回，`status=ok` 同时要求门禁、
  清理与证据完整。任何发布/读回失败都非零且不打印 `GATE-OK`；`execute` shell 只写 schema1 metrics，
  不是成功出口。
- **候选来源审计**：`candidate-audit.json` 由 `candidate_audit.py` 可复现生成，记录 59 个
  suite 在 candidate 0.1.0 上的真实运行（逐 ID 的 `rc` 命令退出、`suite_rc` 目标进程退出、
  `expected/observed`、失败断言、脚本摘要）。56 个通过的 suite 已把 `candidate_clean` 置为 true；
  `r67_tests` 是 fake-tree runner 技术审计（模拟环境中的 candidate plan/scope 错误，不作为断言失败）；
  `r90_tests`（R93 追加平台资产不一致）与 `p5_v1`（`[V1] 追加平台…: FAIL — False`）保留 dev-only，
  覆盖表引用其具体失败断言。
  `source_coverage.py` 的逐 ID 行同时记录脚本摘要、真实来源层、可安装执行性、不可迁移理由/
  已安装断言；集合差集由 `coverage-baseline.json` 守护。

## 命令监督（C → G → S → W）与取消

`execution.py run()` 为每个命令建立固定拓扑：调用方 C → 专用 guardian G → 执行 supervisor S →
目标 W。G/S 都是 subreaper；S 正常退出后由 G 接管其真实残留后代，任何 S 故障（普通异常、`os._exit`、
SIGKILL、卡住）都判为设施失败而不是成功。控制面是两条匿名 socketpair 上的有界长度帧
（READY/START/STARTED/CANCEL/CANCELLED_ACK/DONE），W 不继承控制 FD。

- shell trap 不再递归强杀监督进程：它只写一次 `WF_CANCEL_FILE`（`$RESULTS_DIR/cancel-request`），
  每个 owned `execution.py` 调用在事件循环里读到后经私有通道取消，`run_one.sh` 在启动新单元前检查
  同一请求并停止调度；
- 正常取消由 S 清理，S 卡住时 G 在有界宽限后终止 S 并接管；G 猝死时 S 看到 EOF 仍须清理，但
  C 只报告 `cleanup=unknown` 与设施失败，不声称已释放锁；
- 最后有效监督方丢失/宿主断电仍是明确的能力边界：保留现场、报告最后观测身份与恢复步骤，
  不自动删锁或重跑。
- 确定性 G/S 故障：`WF_EXECUTION_FAULT_TARGET`（`root|unit:<name>|repro:<case>:<phase>`）+
  `WF_EXECUTION_FAULT_POINT`（`supervisor-before-ready|supervisor-after-started|guardian-after-started`）+
  `WF_EXECUTION_FAULT_ACTION`（`exception|exit|kill|hang`），只在总开关 + owned scope 下由各 C 按
  自己的身份解析；故障 spec 随 G/S 启动参数先行传递，目标 W 环境不继承选择器。after-started 点可用
  测试 ready 管道（`WF_EXECUTION_FAULT_READY_FD`）确认目标已初始化。旧 `WF_SUPERVISOR_FAULT`/
  `WF_GUARDIAN_FAULT`/`WF_UNIT_FAULT` 仍是低层测试注入点，同样受开关约束。
- 每个 `execution.run` 在启动前写命令 receipt（managed `commands/<command_id>.json` /
  standalone 隐藏同目录 sibling / root 的 `.runner.json`），阶段与 unit_execution 只用显式引用，
  不按文件名猜全集。隔离 HOME 与 repro 相位 TMPDIR 在 supervision=cleaned 后才回收，unknown/failed
  保留并在 receipt `retained_paths` 报告；harness 的 `_STAGED` 在托管 worker 下 defer 给相位目录统一回收。
- candidate `check` 的 git 调用带 `GIT_OPTIONAL_LOCKS=0`，不刷新 `.git/index`；测试直接断言 index 不变。

## 解释器契约

- SUT 驱动解释器（启动被测 `wf.py`）：`wfdrive.PYTHON` / `_harness.WF_PYTHON` 两处单点默认
  （**保持异解释器**——`wflib/session.py::l2_anchor` 跳过同解释器祖先，统一会把锚点推出
  harness 之外，探针证据见任务 11-13-wf-runner-speed-quality），`WF_TEST_PYTHON` 可覆盖；
  full/repro/单元层/manual 四层驱动点一律引该常量。
- 工具侧（启动 `install.py`/`wf-dev-deploy.py`）：`wfdrive.TOOL_PYTHON = sys.executable`
  （与运行器一致；安装器自检走 `sys.executable`，不受锚点耦合影响）。
- 数据侧 `/usr/bin/python3` 断言字面量（argv 验证命令、双解释器并存断言等）不动；
  白名单与守恒校验见任务 11-13-wf-runner-speed-quality 的 evidence/。
- 路径字面量已全部改 `wfdrive.REPO`/`wfdrive.LIB` 派生（`WF_TEST_LIB` 优先=发行副本）。
- 单元层手工运行时也要带 pyc 前缀，否则 `unittest discover` 会把 pyc 写进源树：
  `PYTHONPYCACHEPREFIX=/tmp/wf-unit-pycache /softwares/python/bin/python3 -m unittest discover -s scripts/tests -t .`。

`r68/r71` 的 9 个字段变体在 `scripts/tests/wf_review/test_report_variants.py` 测试；两个历史 suite 名称保留集成和恢复场景。完整覆盖由单元层与全流程层一起证明。

## 性能

- `tasks._committed_fingerprint` 按提交缓存树、按 blob 缓存摘要：单次 `task-check` 约 0.38s（改前 1.87s）。
- 不要缓存祖先判定/提交列表：同进程调用方可能改 HEAD，会给出陈旧事实。
- 2026-11-14（任务 11-13-wf-runner-speed-quality）：串行集合清空 + 默认并发 min(8,cpu)；
  full green 并行墙钟见该任务的 validation 记录（基线 204s @4 jobs / 上一任务 174.99s）。
- 2026-11-14（任务 11-14-wf-runner-round2-contracts）：pyc 缓存 −35%/单元、模板跨 run 缓存
  （单套件 13.4→6.1s）、flows/extra 入池；full 并行 **90.3/88.8s → 49.9/49.7s**，串行 267→259s。
- 2026-11-16（本任务）：保留证据的 cold 并行 full green **72.74s**（ext4）vs 上一任务存档 cold
  **52.8s**（`11-15-wf-runner-boundaries-followup/validation-2026-11-15.md`），+37.8%；历史 tmpfs
  66.28s 留存作量级参考（存储/负载未做同轮 A/B）。ext4 串行 417.25s 是全新冷 scope，不能与存档
  reused 的 268.2s 直接比较。新增命令监督（C→G→S→W）、公共 helper 身份、cleanup 聚合与审计测试
  是主要成本。无硬失败门槛，按审查口径接受偏差。
  热路径守护：`test_runner_budgets.py` 断言 `wf.py status` 5 次中位数 < 500ms（`WF_PERF_GUARD=0` 可关）。
