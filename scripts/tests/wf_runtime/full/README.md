# wf 运行期全流程用例（手动运行）

这些脚本是 2026-11-03 各轮复核期间的三夹具验证资产，已固化进仓库以免随会话丢失。
它们**不在** `unittest discover` 的默认范围内，需要显式运行。运行器会写测试发行缓存、
结果目录和临时夹具；`cp3/r1r2` 的用户配置写入使用独立测试目录，结束后清理。

## 前置

1. 解释器：`/softwares/python/bin/python3`（authoring 侧）。
2. 夹具：`bash wf_fixture.sh [夹具目录] [nocap]` 会从 `docs/workflows/wf/payload`
   部署开发态运行时（调用 `scripts/wf-dev-deploy.py --confirm`）。夹具必须是新目录或带本工具所有权标记的目录；拒绝非空无主目录和符号链接。
3. `run_all.sh` 自动分配临时夹具；`WF_FIX` 可指定安全临时路径。直接使用 `wf_fixture.sh` 时默认 `/tmp/wf-fixtures/f1`。

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

使用运行器单跑，确保夹具部署、初始化和模板复制顺序一致。旧夹具没有所有权标记时，换一个新临时路径；不要让运行器接管已有内容。

**套件自带夹具（2026-11-06 W1）**：`cp4_a8` / `cp5_b12` / `r35_tests` 曾因写死 `/tmp/wf-fixtures/{fu,f5,f3,f2}`
且无人创建而脱离 `run_all.sh`（cp5_b12 当时已红 4 条而无人知晓）。现在它们在脚本内自己调用
`wf_fixture.sh` / `f2_setup.sh`（cp5_b12 另跑 `f1_init.py` 补初始化任务），不依赖兄弟套件或调用方的 `FIX`。
新增套件若需要非 F1 夹具，按同一方式自带，不要假设某个固定 `/tmp` 目录已存在。

## 并行与子集

- 默认 `min(8, cpu_count)` 并发（`WF_JOBS` 可覆盖；`--serial`/`WF_JOBS=1` 退回串行）：每个 worker 用 user namespace 私有 `/tmp`，只读挂共享发行仓库；`unshare` 不可用时自动退回串行。
- 迭代期只跑相关套件：`WF_SUITES="r88_tests r89_tests" bash run_all.sh`（约 4.5s，跳过 f0/p5 流程）。
- **串行集合已清空**（2026-11-14）：原 13 个强制串行套件全部转入并行池——chmod 写入失败
  注入改由 `wfdrive.deny_writes` 的三探针等价契约承担（chmod 层 + ro bind mount 层按探针
  结果选择，user namespace 内同样成立）；其余 11 个保守遗留项经五项审计（夹具来源/共享
  路径/用户状态/pty·sleep/嵌套运行器）确认并行安全。今后确需串行的套件：`suites.json`
  置 `"parallel": false` 并在 `notes` 登记理由（`plan.py::load_suites` 校验 notes 非空）。
- `cp3/r1r2` 的 `--isolated-user` 由 `suites.json` 的 `isolated_user` 字段下发
  （`plan.py` → `PLAN_ISOLATED_SUITES` → run_all/run_one 同一成员判定）。
- 复用发行缓存：`--no-build`；会核对源摘要，过期即拒绝。
- `summary.json` 分开记录 `requested_jobs/effective_jobs`、`execution_mode/fallback_reason`，累计耗时与墙钟分开。
- `WF_COMMAND_TIMEOUT` 是单个运行器命令的秒数上界（默认 180）；repro 用 `WF_REPRO_TIMEOUT`（默认 120）；整次 run 用 `WF_RUN_TIMEOUT`（默认 1800）。超时结束子进程并计失败，日志与结果保留。
- 全局 `flock` 拒绝重叠运行；worker 的私有 `/tmp` 不挂回宿主夹具目录，仅共享结果与只读发行/模板。缺结果直接计基础设施失败，不静默重跑。
- 运行结束清理夹具和模板，保留结果/日志。结果目录也要求为空或由本工具创建。

## 结果缓存轮转

- run_all（`--scope run`）与独立 repro 入口（`--scope repro`）在 `prepare-results` 之后
  各自回收**本前缀**的带 marker 结果目录，保留最近 20（`--keep`）；root 经 `WF_RESULTS_CACHE`
  注入（默认 `~/.cache/wf-test-run`）——r67 假环境与契约测试指向临时根，不触碰真实用户缓存。
- `--bootstrap`（仅手工执行，无自动调用点）额外回收"无主但顶层内容全部为运行器已知产物"
  的历史目录；未知顶层内容跳过并列出。prune 的 liveness 保障隐式依赖全局 flock 单运行器。
- 直接 `plan.py --list` 不再创建结果目录（旧逻辑每次泄漏一个无主 `run-<pid>` 目录）；
  显式给出 `WF_RESULTS_DIR` 时 plan.json 仍镜像写入。

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

`r68/r71` 的 9 个字段变体在 `scripts/tests/wf_review/test_report_variants.py` 测试；两个历史 suite 名称保留集成和恢复场景。完整覆盖由单元层与全流程层一起证明。

## 性能

- `tasks._committed_fingerprint` 按提交缓存树、按 blob 缓存摘要：单次 `task-check` 约 0.38s（改前 1.87s）。
- 不要缓存祖先判定/提交列表：同进程调用方可能改 HEAD，会给出陈旧事实。
- 2026-11-14（任务 11-13-wf-runner-speed-quality）：串行集合清空 + 默认并发 min(8,cpu)；
  full green 并行墙钟见该任务的 validation 记录（基线 204s @4 jobs / 上一任务 174.99s）。
