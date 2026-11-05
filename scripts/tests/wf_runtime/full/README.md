# wf 运行期全流程用例（手动运行）

这些脚本是 2026-11-03 各轮复核期间的三夹具验证资产，已固化进仓库以免随会话丢失。
它们**不在** `unittest discover` 的默认范围内：会写 `~/.wf/`（解释器确认集合）与 `/tmp/wf-fixtures/`，
需要显式运行。

## 前置

1. 解释器：`/softwares/python/bin/python3`（authoring 侧）。
2. 夹具：`bash wf_fixture.sh [夹具目录] [nocap]` 会从 `docs/workflows/新项目开发工作流/payload`
   部署开发态运行时（调用 `scripts/wf-dev-deploy.py --confirm --verify-capability`，会写 `~/.wf/`）。
3. 环境变量 `WF_FIX`：夹具根（默认 `/tmp/wf-fixtures/f1`）。

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
| `d1_tests.py` | D1 实跑（真实 `$DSH_SESSION_ID` 绑定/重入/压缩边界/新会话/wf 身份拒绝面） |
| `d1_wf_tests.py` | D1 的 wf 签发路径（`provider=wf` 携带/恢复/复制到新会话/丢失） |
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
| `r68_tests.py` | 第三十一/三十二轮 R68（审查判定六核、repair 锁内重核与随机令牌、基线批准绑定与前像、续做三分类） |

全量复现：`bash run_all.sh`——**每个套件前重建夹具**，因此与跑序无关；不需要中间手工 pause/release。
脚本会校验夹具建成、初始化退出码、套件退出码、`[FAIL]` 行数与汇总通过数，任一不符即计失败并以 `exit 1` 结束。
| `p5_v1.py` / `p5_v2v3.py` / `p5_v5.py` / `p5_spec.py` / `p5_f0.py` | V1–V5 与 F0 |

## 用法示例

```bash
cd scripts/tests/wf_runtime/full
bash wf_fixture.sh                                   # 建 F1
WF_FIX=/tmp/wf-fixtures/f1 /softwares/python/bin/python3 f1_init.py
WF_FIX=/tmp/wf-fixtures/f1 /softwares/python/bin/python3 f1_ordinary.py
WF_FIX=/tmp/wf-fixtures/f1 /softwares/python/bin/python3 r7r15_tests.py
```

注意：这些脚本假定 `/tmp/wf-fixtures/` 下的夹具可重建；`r35_tests.py` 需要先用仓库外的发行树
（`docs/workflows/wf-release/` 打 tag 后 `install.py`）准备 `/tmp/wf-fixtures/f5`。

## 并行与子集

- 默认 4 并发（`WF_JOBS`）：每个 worker 用 user namespace 私有 `/tmp`，只读挂共享发行仓库；`unshare` 不可用时自动退回串行。
- 迭代期只跑相关套件：`WF_SUITES="r88_tests r89_tests" bash run_all.sh`（约 4.5s，跳过 f0/p5 流程）。
- 8 个套件固定串行（权限失败注入、写全局配置、依赖宿主 `/tmp` 状态）：见 `run_all.sh` 的 `PARALLEL_SERIAL`。
- 复用发行仓库：`WF_REBUILD_RELEASE=0`。

## 性能

- `tasks._committed_fingerprint` 按提交缓存树、按 blob 缓存摘要：单次 `task-check` 约 0.38s（改前 1.87s）。
- 不要缓存祖先判定/提交列表：同进程调用方可能改 HEAD，会给出陈旧事实。
