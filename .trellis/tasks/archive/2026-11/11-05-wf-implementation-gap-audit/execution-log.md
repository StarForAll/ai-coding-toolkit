# 执行记录：R1-1 与全局旧 skill 清理（2026-11-05）

> 人已裁决：① `multi-cli-review*` 仓库层删 + 12 处引用同批改 + 用户全局层也删；② `workflow-scan` / `workflow-repair` 用户全局层删。
> 执行前置：先做归因（`root-cause.md`），再动手。**未提交、未收尾。**

## 1. 删除

| 层 | 路径 | 文件数 | 可恢复性 |
|---|---|---|---|
| 仓库源资产 | `skills/multi-cli-review/`、`skills/multi-cli-review-action/` | 2（395 + 382 行） | Git 历史可恢复（本次未提交，diff 仍可见） |
| 用户全局库 | `/home/xzc/ops/data/ai/skills/agents-skills/{multi-cli-review,multi-cli-review-action,workflow-scan,workflow-repair}` | 1 + 1 + 21 + 71 | 仓库两个可由 Git 恢复；`workflow-scan`/`workflow-repair` 对应 `7fe5993` 退役提交前的历史 |
| 符号链接 | `~/.claude/skills/` 下同名 4 条 | 4 条链接 | 随库删除一并移除，避免悬空链接 |

删除后会话技能目录已刷新：这 4 个 skill 不再可用。

## 2. 引用同批更新（12 处 / 6 文件）

| 文件 | 改动 |
|---|---|
| `README.md` | 删「当前 skills」表两行 |
| `README.en.md` | 删「Current Skills」表两行（双语同批） |
| `.trellis/spec/skills/index.md` | 「Coupled Skill Contracts (CRITICAL)」整节改为「Retired Coupled Skill Pair」（指向 wf 模块自有副本 + 禁再添加通用副本）；删 Common Mistakes 里同名条目 |
| `.trellis/spec/commands/index.md` | 两处去掉具体 skill 名，改为通用表述（外部 reviewer CLI / aggregator command） |
| `.trellis/spec/guides/cross-layer-thinking-guide.md` | 示例链、Mistake 3.5、收尾清单三项改指 wf 模块副本 |
| `.trellis/spec/docs/workflow-implementation-constraints.md` | 「Once it lands…」改为已完成事实（含两层删除与日期） |

**刻意保留、不属待清引用**：`docs/workflows/wf-framework-design.md` §2.2/§6.5/§7.4（判据正文）、`wf-framework-implementation.md` §1.1（命名理由）、`docs/workflows/新项目开发工作流/README.md` §6 与两副本 SKILL.md 的「来源」行（设计稿 §7.4 要求的来源登记）、`docs/workflows/workflow-implementation.md`（已退役模块的历史文档）。

## 3. 验证（实跑）

| 检查 | 结果 |
|---|---|
| `grep -rn "multi-cli-review" README.md README.en.md skills/ .trellis/spec/` | 3 处命中，**全部是退役登记本身**（"were a mandatory…" / "Do not re-add…" / "was removed from…"），非活跃引用 |
| `./scripts/validate-skills.sh` | OK：24 个 skill（原 26） |
| `trellis-library/cli.py validate --strict-warnings` | exit 0，仅 5 条既有 mtime-info |
| 用户全局库 | 4 个目录均不存在；`~/.claude/skills/` 无对应链接 |
| 会话技能目录 | 已刷新，4 个 skill 消失 |

## 4. 未做

- 未提交、未 add、未收尾（按人要求等人工审查）。
- 未动 `tmp/新项目开发工作流/`（旧模块副本，见下一条待裁）。
- 未改设计稿/机制稿/实现稿正文。

---

# 第二批执行记录（2026-11-05，14 项裁决落地）

前置：归因见 `root-cause.md`；裁决见 `gap-inventory.md` §8。**未提交、未收尾。**

## 1. 文档批

| 项 | 裁决 | 落点 |
|---|---|---|
| R1-2 | A | 实现稿 D14 轮次改为「跨轮（身份判定与持久绑定）+ 第二轮（wf 自签发身份路径）」；§6.4 第二轮行补该能力与首轮出口（`provider=wf` → `WF_IDENTITY_UNRESOLVED`，人换宿主或等第二轮，模型不自行签发） |
| R1-3 | A | 设计稿 §1.2 收窄为「只投放目标项目内的根」+ 设计稿 §8.2「资产落点」拒绝列改为「把投放根落到目标项目之外」；机制稿 §10.1（roots 一律项目内相对路径）、机制稿 §3.1 符号链接段同步；机制稿 §0.1 输入摘要随设计稿变更更新 |
| R1-4 | B | 实现稿 D24 标注「拒绝项延至第三轮」；§2.3.11 改明「延迟至第三轮」并列出 4 条启用前置；设计稿 §6.3 与机制稿 §8.4 各加「启用前置」句 |
| R1-5 | B | D24 标注「巡检两类治理输出延至第二轮」；§2.3.11 改为「首轮口径：不阻断门禁，但 `inspect` 报告须显式列出未输出的治理类别」 |
| R1-6 | B | 机制稿 §3.5 加「首轮实现覆盖」说明（d 档不产生、存疑并入 f、两出口经不同入口区分；a–f 契约不变）；实现稿 §2.3.11 同批记录人裁 |
| R1-10 | A | §5.1 明写 `--request` 属实现级增补、不改设计稿 §6.5 的契约枚举 |
| R1-15 | A | §6.1、§6.4 第三轮行、D37、§8.2 速查四处承认 `install.py` 首轮已交付；第三轮收敛为 upgrade/purge/资产修复/落点全分支 |
| R1-16 | A | README §3 补「开发态占位符 `0.0.0-dev`」例外，并写明机检位置 `_assert_version_consistency` |

## 2. 技能批

| 项 | 裁决 | 落点 |
|---|---|---|
| R1-9 | A + 明确适用面 | `wf-review`：`--review-focus` 改「可选，wf 侧总会给出」；正文加「只在复杂任务的 Check pass 之后、人判之前使用」 |
| R1-11 | A | `wf-review` 步骤新增：报告固定 `report.md`、已存在则停止并回报、不自建目录；末尾回显四项事实 |
| R1-12 | A | 两副本「最近正反例」改为指向实跑证据（`validation.md` §19 / 实现稿 §7.1 V4） |

## 3. 代码批

| 项 | 裁决 | 落点 |
|---|---|---|
| R1-7 | A | 删除 `templates.py::check_markers`（无消费点）；D30 登记改为实际函数 + 删除说明 |
| R1-8 | B | `gates.py` 新增 `STEP_DELIVERY_ROUND`/`CURRENT_DELIVERY_ROUND`，`required_step_specs()` 带 `delivery_round`；`support_report()` 增「已声明交付却仍是能力桩」判定；`cli._unavailable` 打 `wf_delivery_round` 标记；`wf-release.json` 增顶层 `delivery_round` 与每步 `delivery_round`；`install.py` 自检同步（runtime_support 输出 `stub_rounds`） |
| 测试 | 随 R1-8 更新 | `cp3_tests.py` A16 用例改为按 `required_step_specs()` 构造清单，新增「已交付步骤不得是能力桩」「缺交付轮次被拒」两例 |

## 4. 验收夹具登记面（R1-13 A）

新增 `docs/workflows/新项目开发工作流/acceptance-fixtures.md`：场景行 → 夹具 → 初态/触发/预期输出 → 证据；§3 列夹具特有覆盖对照，§4 单列未覆盖项（F0 的「准备定义与自举/验证分时解析」属第二轮、spec 拆分未单独断言、真实压缩增量观察待触发）。实现稿 §7.3 加指针。

## 5. 验证结果（实跑）

| 检查 | 结果 |
|---|---|
| `validate-wf-design.py` | OK：七项检查 + 覆盖率断言通过；机制稿引用 562、场景 91/91、三档 13/13、输入摘要 4/4 |
| `check-doc-refs.py` 三稿 | 0 problem |
| `validate-skills.sh` | OK：24 skill |
| `build-wf-release.py --verify` | OK：字节复现（0.1.0，55 资产） |
| 全量套件 `run_all.sh` | **59 项，失败 0** |

## 6. 文档新绑定（供复审使用）

| 文档 | sha256 | 行数 |
|---|---|---|
| 设计稿 | `53b0834aec043832a556214418fc543f8076260f0fdd1364b5fe40268b3db496` | 719 |
| 机制稿 | `4cc3a9fe1c333f8615e4f319730c4cf132613f6309994688d5a9eb567877ef9e` | 1143 |
| 实现稿 | `60f7df944e04bfefea5815399f9099907456e2541b4a7234c852ece5de464787` | 900 |

**复审义务未履行**：设计稿/机制稿均属已审稿，按机制稿 §0.1 与设计稿 §0 的维护协议，须由**未参与本轮修订的会话**按轴复审后才可称定稿；本记录只声明"已改并自检通过"。

---

# 第三批执行记录（2026-11-05，第二轮复核提出的 5 项）

分类结论：**3 项属第一轮遗漏（已补完）**；**2 项不是实现遗漏**（见 §5）。

## 1. 项 3：README 残留已删除能力的描述 —— 属遗漏，已修

- 事实：模块 README §2 仍写「`--host-id` / `--verify-capability` 是人确认宿主身份的承载；目标已安装时只允许更新 `installation.json` 的 `session_profile`」，而 R93（commit `20e3ae8`）已删除这两个参数与 `session_profile`。
- **同类范围比一处更大**（逐处 grep 后确认）：
  - 实现稿 §1.6 installation 字段表仍列 `session_profile`、漏 `platforms`；
  - 实现稿 §2.3.7 仍写 `--provider/--verified-version/--capability-evidence` 与"声明式 verified"口径；
  - 实现稿 §2.3.8 仍有 `session_profile.capability.status != verified` 判定句；
  - 实现稿 §4.1.1 仍描述 `--host-id`/`--capability-evidence` 参数；
  - 实现稿 §7.1 V1 初态仍写 `session_profile.capability=unknown`；
  - 代码 `wflib/cli.py::Context.profile()` 仍读 `session_profile`，且**零调用点**（死代码）。
- 处置：README §2 按现工具重写（`--platform` 可重复、`platforms`/`roots` 落点、同引用只追加平台、不覆盖资产）；实现稿五处按 R93 事实归一；删除 `profile()` 死代码。

## 2. 项 4：spec 拆分「旧文件停用/保留」分支 + 登记面矛盾 —— 属遗漏，已补跑

- 补跑：`p5_spec` 新增 5 条用例（建待拆分条目 / 停用+新建两条 applied=3 / 旧文件保留且 `status=disabled` / 索引同步 / 停用条目不再被 `match` 加载），`p5_spec` 13 → 18 例。
- 首次实跑发现断言写错（实现把 status 写成 `status: "disabled"` 带引号，我按裸字符串断言）→ 改为解析 frontmatter 后比对，未改实现。
- 登记面归一：`validation.md` §2.1 末段（原"拆分未单独跑"）改为"移除分支见 §16.1、停用分支见 §16.2"；§11 表该行由"未运行"改为"已补跑（2026-11-05）"；§16 新增 16.2 记录 5/5；`acceptance-fixtures.md` §2/§3/§4 同步（拆分两支均覆盖，从未覆盖清单移除）。

## 3. 项 5：回归项数 55 → 59 —— 属遗漏，已改

- 按 `SUITES` 54 + 专项 5（`r72`/`f0`/`p5_spec`/`p5_v2v3`/`p5_v5`）重算，实现稿 §7.3 改为 59 并注明"R93 批次新增 `r90_tests` 等套件后未回写"。

## 4. 随批修正的测试基建（否则套件会假绿/假红）

| 问题 | 处置 |
|---|---|
| `run_all.sh` 的 `p5_spec` 期望计数写死 13 | 改为 18 |
| `r67_tests` 的假环境把 `p5_spec` 假件写死 13 | 改为从 `run_all.sh` 的 `run_flow` 行解析期望计数（与既有"依实际清单造假套件"同源） |
| `r67_tests` case 4b 未隔离 `WF_RESULTS_DIR`，内层 run_all 会覆盖外层结果行 | 两个 case 各用独立结果目录 |
| `r67_tests` case 4 断言只报 `exit` | 追加汇总行信息，便于定位 |

## 5. 项 1 / 项 2：不是实现遗漏

| 项 | 判断 | 依据 |
|---|---|---|
| 三稿独立复审未履行 | **不是实现遗漏，是流程义务**；且**不可由修订者本人完成** | 设计稿 §0 维护协议、机制稿 §0.1：须由未参与本次修订的会话按轴复审。已交付复审输入 `review-packet.md`（绑定哈希、逐文档改动、五条建议轴、结论模板），不含结论 |
| 全部改动未提交、两任务未收尾 | **不是遗漏**，且与你先前指示一致 | "后续操作执行之后也不能执行收尾动作，需要人工审查通过之后人工要求收尾才能进行" |

## 6. 验证（实跑）

| 检查 | 结果 |
|---|---|
| `run_all.sh` 全量 | **59 项，失败 0**（`r67` 15/15、`r71` 10/10、`p5_spec` 18/18） |
| `validate-wf-design.py` | OK：七项 + 覆盖率断言；输入摘要 4/4 |
| `check-doc-refs.py` 三稿 | 0 problem |
| `validate-skills.sh` | OK：24 skill |
| `build-wf-release.py --verify` | OK：字节复现（0.1.0，55 资产） |

## 7. 文档新绑定（第三次）

| 文档 | sha256 | 行数 |
|---|---|---|
| 设计稿 | `53b0834aec043832a556214418fc543f8076260f0fdd1364b5fe40268b3db496` | 719 |
| 机制稿 | `4cc3a9fe1c333f8615e4f319730c4cf132613f6309994688d5a9eb567877ef9e` | 1143 |
| 实现稿 | `ec2162a9c2d67aeea92e3a48dc413f08c962ca0bbf2bf1dfd83d53387b4e1a08` | 900 |

---

# 第四批（2026-11-05，人裁新增轮次串行门禁）

## 1. 新增契约

设计稿 §8.2 新增「**轮次串行门禁**」：第二轮实现不得在第一轮验收完成前开始；不得以「先搭骨架/并行推进/另立任务」绕开。第一轮「完成」= ①三夹具及专属场景与五条最小验证有实跑记录（**依赖后续轮次才能覆盖的场景行按 §8.1 排除并登记为「等该轮交付」**）；②审查链路可用，或已按 §6.5 留痕不可用并按其出口处置；③**dogfood 至少完成轻量任务闭环与一次中断恢复**并留观察事实。缺任一项时第二轮实现动作一律不得开始。判定与留痕由人执行；「人尚未安排 dogfood」不是豁免理由。

同步落点：实现稿 §6.1 增执行口径（第二轮命令保持 `WF_CAPABILITY_UNAVAILABLE`，不因骨架存在提前解封）；`dogfood-plan.md` 前置为 §0 硬门禁；`review-packet.md` 与 `review-prompt.md` 列为复审重点。

## 2. 自检时发现并修掉的死锁

初稿写「三夹具及其专属场景…均有实跑记录」，但 `acceptance-fixtures.md` §3 记录 F0 的「准备定义与自举/验证分时解析」依赖第二轮能力——按初稿字面，第一轮永远不可能完成、第二轮永远不得开始。已加排除条款（按 §8.1 轮次归属排除 + 逐行登记「等该轮交付」），并同步到实现稿与 dogfood 计划。

## 3. 机检

| 检查 | 结果 |
|---|---|
| `validate-wf-design.py` | OK：七项 + 覆盖率断言；输入摘要 4/4；索引消费点缺项 0 |
| `check-doc-refs.py` 三稿 | 0 problem |
| 索引 | §6.5「不可用处置」的词面候选列与语义列各补 §8.2（新门禁引用本节留痕） |

## 4. 文档最终绑定（第四次）

| 文档 | sha256 | 行数 |
|---|---|---|
| 设计稿 | `b8a0f2880c1ed6f9e218e48baae6f1b037ffa555ed816f7a2301b3050567a6e6` | 721 |
| 机制稿 | `c6864d5259df97e6c95eaf7e7f09fb6908e5ed3a188a4a4cd1daecae573d689e` | 1143 |
| 实现稿 | `35bb8e85bb873b793c1e951ad0c6ad53260ca879de51677c92758b14da8bd26b` | 901 |
| 索引 | `efd9724ddfeb23472c417b4233e66e711acdc8a810dc76e191ae2e59fc152e73` | 143 |

仍未提交、未收尾；独立复审提示词见 `review-prompt.md`。

---

# 第五批（2026-11-05，吸收第 1 次独立复审 F1–F7 + 外部 A1–A3/B1–B3）

## 1. 判定

| 来源 | 判定 | 处置 |
|---|---|---|
| F1 d 桶说明与代码不符 | 成立（阻塞） | 撤回错误断言，按 `scope.py` 事实重写（d 档会产生） |
| F2 轮次归属未贯通 | 成立（阻塞） | 机制稿 §12.1 D14/D24 补子项；实现稿 §6.4 两行、D22 行同步 |
| F3 `delivery_round` 未登记 | 成立（阻塞） | 机制稿 §10.2/§11.2 + 实现稿 §4.2 键表登记 |
| F4 门禁「有记录」歧义 | 成立（建议） | 改为「达到预期结果；仅有失败记录不算完成」 |
| F5 夹具登记强于断言 | 成立（阻塞） | 收窄 F0 行、身份行改 `platforms` 模型 |
| F6 §7.3 过期摘要 + 重复 §16.2 + 4/5 计数 | 成立（建议） | 删过期句、重编 §16.6、计数改 5 |
| F7 复审包绑定过期 | 成立（建议） | 更新四份哈希与真实行数 |
| A1 add_platforms 三处叠加缺陷 | 成立（功能级） | 重写：锁 + 维护回执 + 资产登记 + 冲突整批不写 |
| A2 安装器锁判据与 wflib 不一致 | 成立 | 改为「不存在才创建；已存在须以标记开头」 |
| A3 单 reviewer 参考性执行 | **需人裁** | 不改代码；实现稿 §2.3.11 登记两种口径与当前行为 |
| B1 被遮蔽的重复函数 | 成立 | 删除死函数（81 行，未动 `cmd_task_new`） |
| B2 安装期分支来源核对无运行点 | 成立但**未实现** | 实现稿 §2.3.11 登记为首轮欠项 + 出口 |
| B3 Trellis 宿主扫描面不全 | 成立 | `TRELLIS_HOST_CONFIGS` 对齐 6 平台 |

## 2. 过程中一次自伤并已修正（如实记录）

删除 B1 死函数时首次按行号区间整段删除，误删了 `cmd_task_new` 等后续函数，全量套件出现 58 项 INIT-FAILED。按 `git checkout` 还原该文件后改为「精确删到下一个顶层 def 之前」，复跑通过。教训：按行号区间删除前必须先核对边界函数名。

## 3. 验证

| 检查 | 结果 |
|---|---|
| `run_all.sh` 全量 | **59 项，失败 0** |
| `validate-wf-design.py` | OK（七项 + 覆盖率断言；输入摘要 4/4） |
| `check-doc-refs.py` 三稿 | 0 problem |
| `validate-skills.sh` | OK：24 skill |
| `build-wf-release.py --verify` | OK：字节复现（0.1.0，55 资产） |

## 4. 文档最终绑定（第五次）

| 文档 | sha256 | 行数 |
|---|---|---|
| 设计稿 | `a36b63aab071ebca321b8a5b3b6d90370f6b25e4336e7084a1804e6ece4bcdd8` | 721 |
| 机制稿 | `1e74ef80d3563394bf1d23332ef8ed829254122be7894c22a85747ab44ad339b` | 1143 |
| 实现稿 | `d12bddbe17d993b5db2d4f93d3a37725a669a807fcb23ebedc2871c7107f009b` | 905 |
| 索引 | `efd9724ddfeb23472c417b4233e66e711acdc8a810dc76e191ae2e59fc152e73` | 157（登记行 143） |

第 2 次复审提示词见 `review-prompt-2.md`。仍未提交、未收尾。

---

# 第六批（2026-11-05，A3 人裁 B 落地）

| 落点 | 改动 |
|---|---|
| 设计稿 §6.5 | 「只能凑一个时…」改为「发起与报告导入照常留档供参考；该轮**不产生判定结论**（`review-decide` 拒绝，出口是补第二家 CLI 或按不可用处置留痕），也不满足复杂完成条件」 |
| 机制稿 §9.2 | 同口径重写，并写明拒绝时给出已导入报告与两个出口 |
| 实现稿 §2.3.11 | 原「需人裁，已登记」改为「已裁 B」+ 行为说明（不存在 degraded 结论，单 reviewer 报告不得当作审查 pass） |
| `review.py::decide` | 槽位<2 的拒绝 facts 增加 `degraded`、`imported_reports`、`exits`（两条合法出口） |
| `r71_tests` | `review_case` 支持单槽位；新增「3f 单 reviewer 不产生判定结论」用例（断言 code/verdict/degraded/exits/imported_reports） |

验证：`run_all.sh` **59 项，失败 0**（`r71` 11/11）；`validate-wf-design` OK（4/4）；`check-doc-refs` 0 problem；`build --verify` 字节复现。

新绑定：设计稿 `3ab18df9…`(721)、机制稿 `a6c30e8a…`(1143)、实现稿 `aecd1951…`(905)。仍未提交、未收尾。

---

# 第七批（2026-11-05，B2 交付）

人裁："B2 如果没有多个选择那么直接做"。核对后确认设计稿 §7.1/机制稿 §10.4 已把行为写死（只读核对 → 列分支与出口 → 人确认再继续），无备选方案，故直接实现。

| 落点 | 改动 |
|---|---|
| `install.py` | 新增 `needs_decision()`（tier/exit 2）与 `branch_source_findings()`（自含 Git 核对，语义同 `assets.branch_source_check`；安装时尚无 `.wf/lib`，不导入运行时）；补顶层 `import subprocess` |
| 预览 | 命中「当前分支缺失、其他本地分支存在」时列出路径与分支、给出两条出口，返回 `WF_ASSET_DECISION`（needs_decision），**不写任何文件** |
| `--confirm` | 人在预览中确认后继续投放，并把该决定写入 `installation.decisions`（`kind=branch-source`）；追加平台路径同样记录 |
| 文档 | 实现稿 §2.3.11 的 B2 条目由「首轮欠项」改为「已交付」并写明行为边界（只读、不保存 branch 字段、不切换分支） |
| 测试 | `r83` 新增 4 条：前置（回默认分支且文件缺失）、命中报分支、工作树已存在不算、任何分支都没有不算 |

过程中一次自伤并修正：`install.py` 未在顶层 `import subprocess`（原文件在 main 内局部导入），导致 f0 INSTALL-FAILED 与 r83 NameError；补导入后复跑通过。

验证：`run_all.sh` **59 项，失败 0**（`r83` **23/23**）；`validate-wf-design` OK（4/4）；`check-doc-refs` 0 problem；`validate-skills` 24；`build --verify` 字节复现。

新绑定：设计稿 `3ab18df9…`、机制稿 `a6c30e8a…`、实现稿 `b689aa63…`。仍未提交、未收尾。

---

# 第八批（2026-11-05，吸收第 2 次独立复审 13 项 + 外部 R1–R3）

| 来源 | 判定 | 处置 |
|---|---|---|
| #1 F1 说明仍不符代码 | 成立（P1） | 按候选集构造重写：候选 = 未提交 ∪ 本任务归属 ⇒ 未归属必然未提交 ⇒ 落 c，**d 不可达**；外部提交不进候选集；「命中 glob 但归属存疑」无专用出口列已知偏差 |
| #2 追加平台锁外读、无锁内重核 | 成立（P1） | `add_platforms` 全部读取/计划/冲突复算移入锁内 |
| #3 回执 changes 用绝对路径 | 成立（P1） | 首装与追加两处均改项目相对路径 |
| #4 writer 只查 idle | 成立（P1） | 新增 `_writer_problem()`，与运行期同判据（schema/状态/holder/代次） |
| #5 锁不核真实落点/普通文件 | 成立（P1） | `Lock` 增加普通文件 + realpath 在项目根内 + inode 复查 |
| #6 锁异常未结构化 | 成立（P2） | 两个入口的 `with lock` 均包 try/except → `WF_ASSET_DECISION`/`WF_WRITER_BUSY` |
| #7 释放代次未递增 | 成立（P2） | 持有 +1、释放再 +1（2→4） |
| #8 共享根追加产生空回执 | 成立（P2） | 元数据变更计入回执；无变化走幂等返回 |
| #9 单 reviewer 相反判据残留 | 成立（P2） | 设计稿 §6.5 与机制稿 §9.2 改为「输入不成立先拒绝、不产生 verdict」 |
| #10 r71 断言错绑 | 成立（P2） | 3e/3f 各自独立变量并先断言 3e |
| #11 绑定夹具行写反 | 成立（P2） | 改为「实例标识不符→拒；释放后新会话 bind 成功」并标注真实断言位置 |
| #12 D22/D37 归属冲突 | 成立（P2） | 机制稿两行拆「安装侧（首轮）/运行期升级侧（第三轮）」；实现稿 §4.6 同步 |
| #13 复审包导读过期 | 成立（P3） | 更新 F1 说明与 §16.6 指向 |
| R1 dev-deploy 同型未修 | 成立（P2） | 按 install.py 同语义重写（锁内、资产登记、维护回执、冲突整批、幂等） |
| R2 r90 固化旧口径 | 成立（P2） | 改为「共享根：平台增加、assets 不变、回执含 installation.json」 |
| R3 A1/A2 无实跑 | 成立（P2） | r83 新增 6 条 add_platforms 用例 + r90 修正；`validation.md` 新增 §90 记录 |

过程中两次自伤并修正（如实记录）：
1. 替换 `Lock` 时按行区间删除，误删 `write_bytes`/`self_check`/`_flatten_platforms` 等 7 个函数 → 恢复到 HEAD 版本后发现同时回退了 R1-8 的 `delivery_round` 自检 → 重新施加该补丁；f0 与 r83 复跑通过。
2. r83 测试脚手架先用了与已装平台相同的根，导致「新根」为空、三条用例假失败 → 改为独立新根 `.cursor/skills`。

验证：`run_all.sh` **59 项，失败 0**（r83 30/30、r90 9/9、r71 11/11、f0 9/9）；三校验器通过；发行字节复现。

新绑定：设计稿 `926fd621…`(721)、机制稿 `18e8254d…`(1143)、实现稿 `171b9230…`(906)。仍未提交、未收尾。

---

# 第九批（2026-11-05，吸收第 3 次独立复审 N1–N8 + 外部 5 项）

| 来源 | 处置 |
|---|---|
| N1 | `wf-dev-deploy.py::add_platforms` 记录真实 `head_before`（`git rev-parse HEAD`）并写入回执，持久化派生可成立 |
| N2 | `review.py::decide` 把「人数不足 / 与实施 CLI 重叠」改为**输入不成立先拒绝**（`WF_REVIEW_INVALID`，不写 result、不落 fail 历史、不触发复盘）；实现稿 §5.3 与验收登记同步；历史记录按版本语境保留 |
| N3 | `run_all.sh` 并行汇总改为逐套件核对：缺行/重行/多余/子进程异常都计失败；套件目录在 `/tmp` 时自动退回串行 |
| N4 | dev-deploy 的 writer 校验异常转结构化输出（`WF_RECORD_INVALID` 等），不再 traceback |
| N5 | 实现稿 §6.1 与 D22 轮次列拆为「安装侧首轮 / 运行期升级侧第三轮」 |
| N6 | `p5_spec` 的 match 候选改规则真实值 `src/calc.py`，并加「拆分前 active 命中」正对照；顺带发现测试夹具的 frontmatter 用裸值（非 JSON）导致 spec 一直不可路由，已改为合法 JSON 值 |
| N7 | `p5_f0` 的 HEAD 断言改为核 `rev-parse` 退出码 + `HEAD^{commit}` 可解析 |
| N8 | `r83` 捕获 JSON 代码断言原因码、冲突用双目标验整批零写入、幂等比较完整记录、非法 schema 核记录未变；`r90` expected/actual 列纠正 |
| 外部1 | 4 个改编 skill（grilling/tdd/diagnosing-bugs/code-review）的来源改为「同作者通用 skill + 内容摘要 sha256」，不再以机器本地路径作基线 |
| 外部2 | `task-flow.md` 的 `task.spec-loaded` 时点改为「before_execute 一期；Check/Finish 是重核」 |
| 外部3 | 模块 README 重复的「## 6」改为「## 7」 |
| 外部4 | 清理源树 23 个陈旧 pyc（gitignore 已有该目录规则） |
| 外部5 | 骨架与 `config.skeleton()` 都不再给 `project_id` 值（机制稿 §8.1「不在骨架给值」） |

过程中的自伤：移动 `wf_spec` 导入时切错行区间，导致 p5_spec 语法/缩进破损，已按整段重排修复；另因测试夹具 frontmatter 非法，新增的 match 正对照先暴露「spec 一直不可路由」这一既有测试缺陷（非实现缺陷）。

验证：`run_all.sh` **59 项，失败 0**（p5_spec 19/19、r83 30/30、r90 9/9、r71 11/11、f0 9/9）；`validate-wf-design` OK（4/4）；`check-doc-refs` 0 problem；`validate-skills` 24；`build --verify` 字节复现。

新绑定：设计稿 `926fd621…`(721)、机制稿 `18e8254d…`(1143)、实现稿 `0bc33ecf…`(906)。仍未提交、未收尾。

---

# 第十批（2026-11-05，吸收第 4 次独立复审 R4-1–R4-6 + 外部补记）

| 来源 | 处置 |
|---|---|
| R4-1（P1） | `wf-dev-deploy.py::add_platforms` 锁内核验开发态来源（`dev:<describe>` + HEAD）：不一致即 `WF_ASSET_DECISION`、整批不写；与 install.py 同口径 |
| R4-2 | 取维护权前校验 `generation` 为整数，非整数 → `WF_RECORD_INVALID`，不再 traceback |
| R4-3 | `run_all.sh` 并行汇总先校验每行 5 段、rc 为整数、状态仅 ok/bad；畸形行单独计失败，「存在性」只认合法行 |
| R4-4 | `r90 rec()` 的 expected 字段改为形参（此前误写为 actual） |
| R4-5 | `validation.md` §16.6 回填当前版本（6 条用例、matched 不再是空、p5_spec 19）；`p5_spec` 补「删除未解除依赖给三个出口」断言（`facts.exits` 三条），使登记与断言一致 |
| R4-6 | 实现稿 §6.1 分轮摘要补齐 D14/D24 的延期子项，并注明「以 §6.2/§6.4 为准」 |
| 外部补记 | `validation.md` 新增 §91，登记第三/四轮修正批的实跑（含资产/文档改动由机检覆盖的说明）；`run_all.sh` 设 `PYTHONDONTWRITEBYTECODE=1` 并清理源树 pyc |

验证：`run_all.sh` **59 项，失败 0**（r90 11/11、p5_spec 19/19、r83 30/30、r71 11/11、f0 9/9）；三稿 0 problem；`validate-wf-design` OK（4/4）；`validate-skills` 24；`build --verify` 字节复现；源树 pyc 0。

新绑定：设计稿 `926fd621…`(721)、机制稿 `18e8254d…`(1143)、实现稿 `8b903fd8…`(906)。仍未提交、未收尾。

---

# 第十一批（2026-11-05，吸收第 5 次独立复审 F5-1–F5-7 + 外部 A1–A6 及低优先项）

| 来源 | 处置 |
|---|---|
| F5-1（P1） | dev-deploy 追加平台以 `rules_digest` 判同源（覆盖同一 HEAD 下的 dirty 内容变化），不一致整批拒 |
| F5-2 | 目录创建移出预检路径：拒绝分支不再创建 `.claude/` 等新根；首装写入阶段才建 |
| F5-3 | r90 的 R4-1 断言改为「篡改后快照 = 拒绝后逐字节 + 目录树相等」并解析 JSON 原因码 |
| F5-4 | `generation` 校验排除 JSON 布尔（dev-deploy 与 install.py 两处） |
| F5-5 | r71 的 3e/3f 增补「result 为空 + attempts 无 fail」断言，新增 3g（同 CLI 双槽位）；`validation` §91 的过度归属已改正 |
| F5-6 | `wf-review-action` 的最近反例改为「拒绝、不产生 verdict」并标注旧口径已被替代 |
| F5-7 | 夹具与实现稿的「5 条用例」改 6 条并点明正对照 |
| A1 | `spec-update` / `baseline-apply` 的批准范围改取 `entry_snapshot.touch_paths`（未开工回退 plan） |
| A2 | `cmd_bind` 的绑定恢复路径纳入同一把 `.wf-lock`（锁外快检 + 锁内重核） |
| A3 | `stop` 的 transfer 要求承接任务未归档、已批准、且触碰面覆盖待承接路径，否则保留待决并给三出口 |
| A4 | `task-replan` 缺 Decision —— 登记为未实现（命令面改动需机制稿同批，未擅自加参） |
| A5 | `inspect` facts 增 `governance_omitted`，显式声明未输出的两类治理输出 |
| A6 | 启动校验只覆盖机制稿 §5.2 四步子集 —— 登记为已知缩减，禁止据此宣称完整启动校验 |
| 低优先 | `import_report` 非对象 anchor → `WF_REVIEW_INVALID`；其余一致性偏差（Decision 词表、python_version 未比对、project_key_approved 只扫活动区、debug 声明非幂等、预算降级不可达、start 验证未入 action）逐条登记在实现稿 §2.3.11 |

验证：`run_all.sh` **59 项，失败 0**（r71 12/12、r90 13/13、r83 30/30、p5_spec 19/19、f0 9/9）；三稿 0 problem；`validate-wf-design` OK（4/4）；`validate-skills` 24；`build --verify` 字节复现；`validation` 新增 §92。

新绑定：设计稿 `926fd621…`(721)、机制稿 `18e8254d…`(1143)、实现稿 `6dfee7cb…`(909)。仍未提交、未收尾。

---

# 第十二批（2026-11-05，吸收第 6 次独立复审 F6-1–F6-6 + 外部 5 项）

| 来源 | 处置 |
|---|---|
| F6-1（P1） | 新增 `approved_touch_paths()`：已开工且快照带 `touch_paths` 时**空数组照用**；快照缺键 → `WF_RECORD_INVALID`，不回退可变 plan。`spec-update`/`baseline-apply` 与 `scope.classify_candidates` 统一走它 |
| F6-2 | dev-deploy 同源判据改为「HEAD + `rules_digest`」；`dev:<describe>[-dirty]` 只作描述（无关文件变脏不再阻断，技能内容变化仍拒绝） |
| F6-3 | r90 的目录快照纳入**文件路径**；拒绝用例改用尚不存在的新根（claudecode），可捕获「预建目录」回归 |
| F6-4 | transfer 的归档/终止分支补齐三个适用出口 |
| F6-5 | 新增 r71 3h（有效审查 fail 落判定 + attempts.outcome=fail）；`validation` §91 撤下错绑的 3b 指针、把 3g 归属移到 §92 |
| F6-6 | 六项低优先偏差逐项补「当前处置 / 禁用场景 / 承接轮次」 |
| 外部1 | `validation` §10 的复现命令改 `--platform`；头部宿主描述改平台清单口径；历史命令保留并在文首标注版本语境 |
| 外部2 | 执行器确认的集合语义与失效传播负例 —— 登记为**未运行**（`validation` §93），并写入夹具登记面 §4 |
| 外部3 | 补**两段显式交接 E2E**（r71 第 4 组：begin → 旧代次不可写 → accept 新代次 → 可推进）；并记录 `begin --to` 必须是 session-key |
| 外部4 | dogfood 记录表新增「宿主身份稳定性」观察轴 |
| 外部5 | `round1-closure-plan` 的进度行与实现稿绑定同步到当前状态 |

验证：`run_all.sh` **59 项，失败 0**（r71 **18/18**、r90 13/13、r83 30/30、p5_spec 19/19、f0 9/9）；三稿 0 problem；`validate-wf-design` OK（4/4）；`validate-skills` 24；`build --verify` 字节复现。

新绑定：设计稿 `926fd621…`(721)、机制稿 `18e8254d…`(1143)、实现稿 `74e41c23…`(916)。仍未提交、未收尾。

---

# 第十三批（2026-11-05，吸收第 7 次独立复审 F7-1–F7-6 + 外部清单）

| 来源 | 处置 |
|---|---|
| F7-1（P1） | `approved_touch_paths()` 改为按**是否已开工**分流：仅「快照为 null 且未开工」回退 plan；已开工的 null/非对象/缺键/非列表一律 `WF_RECORD_INVALID` |
| F7-2（P1） | transfer 的承接面判定改走同一函数，空批准面不再回退 plan |
| F7-3 | `scope.classify_candidates` 改调同一 helper（此前另写一套回退）；`validation` §94 记录统一 |
| F7-4 | r71 补 4c2（accept 前接收者不可推进）与 4f（accept 后旧会话/旧代次失效） |
| F7-5 | 审查人数行改引 §92/§93 与 r71 3f/3g，并注明 §19 是旧口径历史；`validation` 文首补版本语境说明 |
| F7-6 | `round1-closure-plan` 进度行改为「七轮外部复审 + 对应修正批全部落地」，指向 §90–§94 与执行记录 |
| 外部-夹具登记面 | 补 5 行高价值 §2（机械修订/机读触碰面/执行器三级解析/日常收工/暂停后换会话）与 4 项 §4 未覆盖（spec 多文件预算、读取留痕负例、历史锚点不可达、未提交记录存在性负例） |
| 外部-spec 预算降级 | 夹具 §4 登记归属待裁；未宣称覆盖 |
| 外部-Git 就绪 | p5_f0 增加 `git ls-tree` 断言（`.wf/` 与 `.gitignore` 之外无路径；用 `core.quotepath=false` 避免中文路径被加引号） |
| 外部-其余 | `support_report` 对 repair/uninstall 报「bootstrap-layer entry (expected)」；README 模块计数改 24 个 .py |

验证：`run_all.sh` **59 项，失败 0**（r71 **20/20**、r90 13/13、cp3 19/19、f0 9/9、p5_spec 19/19）；三稿 0 problem；`validate-wf-design` OK（4/4）；`validate-skills` 24；`build --verify` 字节复现；`validation` §94 已记录。

---

# 第十四批（2026-11-05，方案 A：把"已修复"变成可证伪用例）

动机：七轮复审里"证据通过但不具区分力"是主要失败形态（空断言、expected==actual、只记目录的快照、`!=` 比较）。文字条款无法约束它，改成可执行产物。

落地：
- `scripts/tests/wf_runtime/full/repro/_harness.py`：固定契约——`--expect green` 在当前树必须成立；`--expect red` 把 payload 复制到临时目录、注入"退回修复前"的那一处、同一 check 必须变红。
- 首批 4 条：`f7-1-touch-paths`、`f7-3-scope-single-source`、`f5-4-generation-bool`、`r4-1-source-mismatch`。
- `run_all.sh` 增 `run_repro()`，两模式都过才计入通过；汇总输出"repro 用例 N/M"。
- `repro/README.md` 写明增量约定与边界（`repro stale`、锁对象排除、只证明已声明项）。

未做的：其余 finding 的复现用例（按同一契约逐步补齐）；B（闭合做成门禁产物）、C（单源化）仍待排。

验证：`run_all.sh` **63 项、失败 0**；`validation` §95 记录。
未提交、未收尾。

---

# 第十五批（2026-11-05，方案 A 铺开：4 → 7 条 repro）

新增 3 条（另把 harness 抽出 `install_fixture()` 复用，避免每条脚本各写一套安装夹具）：

| 用例 | 证明的断言 | 注入点 |
|---|---|---|
| `install-lock-foreign-object` | 锁对象只复用"存在且带 wf 标记 + 普通文件 + realpath 在项目根内"的对象 | 去掉标记前缀核验、去掉真实落点核验 |
| `install-generation-and-receipt` | 追加成功：代次 2→4、`installation.json` 进回执、`changes[].path` 项目相对 | 释放不增代次、元数据不计入变更、回执写绝对路径 |
| `inspect-declares-omitted` | `inspect` 明确声明两类未输出的治理输出（及其说明） | 把 `governance_omitted` 键改名 |

过程中修掉两处脚本自身缺陷（如实记录）：`Lock` 的判据在 `__enter__` 而非构造器，原先"直接构造"测不到；回执/代次注入模式写的是臆测代码片段，实际片段不同，改为从源码取值。

验证：`run_all.sh` **66 项、失败 0**（59 既有 + 7 repro，两模式均过）。

仍未覆盖（下一批，需完整 CLI 夹具）：review-decide 拒绝路径、bind 恢复进锁、transfer 承接三条件、writer-handover 两段 E2E。未提交、未收尾。

---

# 第十六批（2026-11-05，repro 铺到 CLI 级：7 → 9 条）

新增 CLI 级基础设施（`repro/_harness.py`）：`deploy()` 用**真实发行树**部署临时项目、`cli()` 用真实 envelope 调项目内 `wf.py` 并自动携带绑定实例标识、`ensure_project_config()` 造最小项目配置与带治理块的活基线；`repro/_review_flow.py` 固化「建任务→写 PRD 计划块→批准→开工→Check→launch→import→decide」。

| 新用例 | 证明的断言 | 注入点 |
|---|---|---|
| `review-count-reject` | 同 CLI 双槽位 → `WF_REVIEW_INVALID`、`result` 为空、attempts 无 fail、facts 给出口 | 去掉提前拒绝 + 把人数不足退回写 `verdict=fail` |
| `bind-instance-mismatch` | 实例标识不符 → `WF_BINDING_MISMATCH`，写权代次不变 | `_require_instance_match` 直接 return |

搭这套夹具时踩到的真实约束（记下来，后续 CLI 级用例直接复用）：`install.py --target` 要求目录已存在；普通任务开工要求 `.wf/project-config.json` 与带 `wf-governance` 块的 `.wf/baseline.md`；Check 之前只能提交 `.wf/`（业务文件须留作任务自己的未提交改动）；`review-launch` 的逐槽位暂存目录在 `facts.temp_paths`；报告必须带 `<!-- wf-review-report:v1 -->` 标记。

验证：`run_all.sh` **68 项、失败 0**（59 既有 + 9 repro）。

仍未覆盖（下一批）：`cmd_bind` 恢复分支进锁、`stop` 的 transfer 承接三条件、`writer-handover` 两段 E2E、`scope` d 档不可达。未提交、未收尾。

---

# 第十七批（2026-11-05，repro 9 → 10；transfer 用例因阻塞撤回）

新增 `handover-two-stage`（CLI 级）：begin 进 recovering → 中间态旧会话与接收者都不可写 → accept 后**以 begin 后为基线**递增代次 → 旧会话失效。注入 `handover_accept` 不递增代次即变红。

写这条用例时踩到并修正了两处自身错误（如实记录）：
1. 注入模式 `generation = ... + 1` 在 `acquire` 与 `handover_accept` 各有一处，`patch()` 命中了前者 → 注入看似成功实则无效。改为连 `receiver_session_key` 前置判断一起替换保证唯一。
2. 断言基线取错：拿"最初代次"比"accept 后代次"，而 `begin` 本身已递增一次，导致注入后仍通过。改为比较 `begin 后` 与 `accept 后`。

`stop` 的 transfer 用例：先写后撤。实测表明 subject 首项放 id 会随 WIP 路径一起进 `fingerprint.item()`，只给 id 则被"未覆盖 WIP"拒；给 `[id, 路径]` 落到"须给出存在的具名承接任务 id"（该 id 确实存在）。怀疑是实现问题或 subject 另有约定，**未确认前不写 repro**，已在 `validation` §95 记为阻塞项。

验证：`run_all.sh` **69 项、失败 0**（59 既有 + 10 repro）。未提交、未收尾。

---

# 第十八批（2026-11-05，查证并修正 transfer 语义；repro 10 → 11）

查证结论：文档（机制稿 §5.6「具名对象与实际承接」、设计稿 §4.4）要求承接是**具名对象**；实现却从 `subject` 首项取 id，而同一命令又要求 subject 覆盖全部未提交路径——id 与路径混在一张清单里被逐项 `fingerprint.item()`，导致「存在/未归档/已批准/覆盖」四项承接核验实际不可达。判定为**实现偏差**，不是 subject 约定缺失。

修正：
- `stop` 的 transfer 分支改为读取 `Decision.target_task`（与 repair 的 disposition 同一约定），subject 只列待承接路径；保留「subject 首项是 id」的兼容回退。
- 该分支（目标缺失/不存在/自承接）补三个可执行出口。

用例：`transfer-target-task-field`（CLI 级）——`target_task` 为不存在的 id 与自身 id 两种都被拒、回显 target 且给出口；注入回「subject 首项即 id」即变红。

过程中发现并修正的一处验证环境陷阱：`_harness.deploy()` 装的是**发行树**，所以 repro 必须在 `build-wf-release` 之后跑；直接跑单条脚本会测到旧发行。`run_all.sh` 本来就先重建发行，故整套跑不受影响——已在脚本注释与本批记录中写明。

验证：`run_all.sh` **70 项、失败 0**（59 既有 + 11 repro）。未提交、未收尾。

---

# 第十九批（2026-11-05，repro 11 → 12：bind 恢复分支进锁）

`bind-resume-under-lock`（CLI 级）：先在夹具里把 writer 动作伪造成「同一会话的 `session.bind` 未结案」，再让**另一个进程**持有 `.wf-lock`，然后调用 `bind`。

- 修复后：取锁失败 → `WF_WRITER_BUSY`，writer 逐字节不变；锁释放后同一意图能结案（`resumed=true`、`action.state=done`）——同时证明"拒绝"和"路径可用"两件事。
- 注入（把恢复分支的 `_lock` 换成 `nullcontext`）：持锁期间仍写成功 → 变红。

夹具要点：`build_task` 之后 writer.action 已是 `task.create`，必须复用同形状动作记录改写 `kind/state/targets` 才能进入恢复分支；锁持有者用独立进程 flock + 就绪握手，避免竞态。

验证：`run_all.sh` **71 项、失败 0**（59 既有 + 12 repro）。

至此 `validation` §95 里列的"待补 repro"只剩 `scope` 的 d 档不可达（定义性断言，无注入点）。未提交、未收尾。

---

# 第二十批（2026-11-05，repro 一键入口）

- 新增 `scripts/tests/wf_runtime/full/repro/run.sh`：一键/CI 入口，默认先 `build-wf-release --version 0.1.0` + `--verify` 再跑；支持 `--no-build`、`--only <子串>`、`--list`；退出码 0 表示每条用例的 green 与 red 都成立。
- 机器可读汇总：`REPRO_TOTAL=` / `REPRO_PASSED=` / `REPRO_FAILED=` / `REPRO_FAILING:`，供上层消费。
- `run_all.sh` 的 `run_repro()` 改为**委托**该脚本（单一实现，不再并行维护两套循环）。
- `repro/README.md` 补「一键运行」小节，并写明"CLI 级用例从发行树部署，必须先重建"这一陷阱。

验证：`repro/run.sh` 12/12；`repro/run.sh --only handover --no-build` 1/1；`run_all.sh` **71 项、失败 0**。未提交、未收尾。

---

# 第二十一批（2026-11-05，吸收第 8 次独立复审 F8-1–F8-7 + 外部清单；repro 12 → 15）

| 来源 | 处置 |
|---|---|
| F8-1（P1） | 删掉 transfer 的「subject 首项即 id」兼容回退——真实 WIP 路径可能与任务 id 同形，回退会把它从核验面静默移走；现只认 `Decision.target_task` |
| F8-2（P1） | 承接批准必须是**有效批准对象**（dict + `decision`/`choice` + `plan.version`），`true`/字符串一律不算 |
| F8-3（P1） | repair 的承接探针与 stop 同判据：真实批准存的是 Decision 本身（无 `decision` 字段），且批准面取 `entry_snapshot`、拒绝已归档/终止的目标 |
| F8-4（P1） | 正式安装追加平台在比 `source_commit` 之外再比 `rules_digest`（首装把该值写进安装记录），同 tag 重建后的内容差异不再混装 |
| F8-5（P1） | `repro/run.sh` 在 `--only` 无匹配时按失败退出；`run_all` 不再吞退出码（汇总缺失/退出码与数字不一致都计失败） |
| F8-6（P2） | 把复合用例 `install-generation-and-receipt` 拆成三条单点注入用例，各自独立可证伪 |
| F8-7（P2） | 回填四处陈旧登记：夹具行的提交树断言、README 23 个 .py、实现稿 74 项口径、收口计划"二十批" |
| 外部 P1 | 核对 `stop_work`：`require_held` 已在 `lock.acquire` 内（3070–3071），未复现所述窗口；仍补 `stop-under-lock` 用例把"锁内核验+释放"固化为可证伪断言 |
| 外部 P2 | 登记两处未实现（spec 索引只同步一段、`stop` 无预览分支，各带出口与承接轮次）；修正 §9.1 陈旧行与 §7.3 的 `capability=verified` 旧口径 |
| 外部 P3 | 七条低优先观察逐条登记（Check 锚点偏宽、Trellis 托管块不分宿主、纯删除绕行、ensure_releasable 更严、blocking_receipts 死代码、staging_root 退化、_sync_index 子串匹配） |

另修一处夹具联动：`run_all` 改成委托 `repro/run.sh` 后，`r67` 的假环境缺 `repro/` 目录会被判"汇总缺失"，已在假环境生成 stub。

验证：`run_all.sh` **74 项、失败 0**（59 既有 + 15 repro）。未提交、未收尾。

---

# 第二十二批（2026-11-05，吸收第 9 次独立复审 N9-1–N9-5 + 外部 4 项；repro 15 → 16）

| 来源 | 处置 |
|---|---|
| N9-1（P1） | 旧安装缺 `rules_digest` 时从**已装清单**取；两者都取不到即拒绝追加（不再"缺证据就放行"） |
| N9-2（P1） | 新增 `_is_approved_plan()`：批准必须是入口认可的批准语义（`choice ∈ APPROVE_CHOICES` 或包装形态内层如此 + `plan.version`），stop 与 repair 探针共用；`{"choice":"reject"}`、`{"decision":true}` 不再被当作已批准 |
| N9-3（P2） | 拆分/收敛双注入点：锁用例拆出 `install-lock-realpath`；`review-count-reject` 删掉被提前拒绝遮蔽的第二注入点 |
| N9-4（P2） | harness 新增 `Precondition`：夹具/运行前置失败在 green 与 red 都算失败，red 只接受"目标断言被击中" |
| N9-5（P2） | 回填当前计数：实现稿 79→75 项、§9.1、收口计划"九轮/二十二批"；`validation` §95 删掉复合行、补 4 条单点用例 |
| 外部-1 | `task-start` 写快照时从**批准版本的 PRD 重提取** `touch_paths`（不再抄 `plan`），失败即 `WF_TEMPLATE_INCOMPLETE` |
| 外部-2 | `check.py::_external_touches_task` 改用 `approved_touch_paths(task)`，与分类器同源 |
| 外部-3 | `scope.governance_condition` 去掉行为相同的冗余分支 |
| 外部-4 | 清理源树 `__pycache__`（gitignore 已覆盖） |

过程中三次自伤并修正（如实记录）：
1. 变量名 `_prd_text` 遮蔽同名函数 → `task-start` 抛 UnboundLocalError（exit 70），全量 108 项失败；改名 `_prd_source` 修复。
2. 安装夹具没有 `rules_digest`，被 N9-1 新判据拒 → 3 条 repro + r83 的 5 条用例假失败；补夹具（含 manifest）后恢复。
3. `r4-1` 传空 manifest 被新判据兜住，red 变成"注入后仍被拒"而失效 → 传入匹配摘要。

验证：`run_all.sh` **75 项、失败 0**（59 既有 + 16 repro）。未提交、未收尾。

---

# 第二十三批（2026-11-05，吸收第 10 次独立复审 N10-1–N10-6 + 外部清单）

| 来源 | 处置 |
|---|---|
| N10-1（P1） | `_is_approved_plan(task, root)` 增加「当前 PRD 重算版本命中批准版本或等价链」的复核，stop 与 repair 共用；PRD 缺失的记录不做版本复核（留给记录完整性） |
| N10-2（P2） | harness 引入 `TargetFailure`：只有它能在 red 模式算通过；未归类字符串、`Precondition`、内部错误码在两种模式都失败；六个 CLI 用例加 `require_business_code` 守卫 |
| N10-3（P2） | 版本重算侧也做 `validate_glob` 规范化（`pkg//**` 不再永久失配）；快照按 PRD 顺序去重 |
| N10-4（P2） | 幂等（无新增平台/无待投放/无缺登记）判定前移到摘要校验之前，无变化重装不再被拒 |
| N10-5（P2） | `validation` §95 的注入描述改为与脚本一致，删掉已拆分的复合行 |
| N10-6（P2） | `r87` 按会话标识选绑定（不再 `listdir[0]`），并修正其 `rec()` 的 expected 字段 |
| 外部 P1-1 | 登记 D18 降级阶梯 / D21 集合负例的「跨轮」标签漂移，写明须在第二轮开工前由人裁定 |
| 外部 P1-2 | `wf-continue` 路由行改为「人明确要求改方案」才调用 `task-replan`，并说明纪律前置原因 |
| 外部 P2 | `review-flow.md` 的「fail」改为「拒绝输入、不产生判定结论」；`task-flow.md` 的「第二阶段」改「第二轮」 |
| 外部 P3 | 四条低优先观察登记在实现稿 §2.3.11 |

过程自伤与修正：`TargetFailure` 批量改造时正则把守卫插进了多行调用中间（3 条用例语法错误），按"语句闭合后再插入"重写修复；`_is_approved_plan` 加版本复核后 `r80` 的人造任务记录（无 PRD）被判未批准，补 PRD 缺失时的回退。

验证：`run_all.sh` **75 项、失败 0**（59 既有 + 16 repro）；三稿 0 problem；机检 4/4；`validate-skills` 24；字节复现。未提交、未收尾。

---

# 第二十四批（2026-11-05，吸收第 11 次独立复审 N11-1–N11-5 + 外部清单）

| 来源 | 处置 |
|---|---|
| N11-1（P1） | `_is_approved_plan` 改用既有 `normalized_plan_version()`（按 `old_version → new_version` 多跳归一），合法机械修订链不再被误拒 |
| N11-2（P1） | 读不到 PRD 不再默认放行：按未批准处理；`r80` 夹具改为写真实 PRD 并用 `compute_plan_version` 回填版本 |
| N11-3（P2） | `require_business_code` 收紧为「必须返回码表内的 `WF_*`」；`f7-3` 只把 `WF_RECORD_INVALID` 当目标、非业务异常归前置；handover 三处拒绝检查、bind-resume 正对照、lock-realpath 正对照都加了守卫；README 契约同步 |
| N11-4（P2） | 快照先 `validate_glob` 规范化再去重（`pkg//**` 开工后能正常 Check） |
| N11-5（P3） | `repro/README.md` 改为 `TargetFailure`/`Precondition` 契约 |
| 外部-1 | `review-import` 前移字段完备性核验（缺 `excluded-scope` 等即拒）；decide 的出口补「用 review-launch 开新轮」 |
| 外部-3/5 | 实现稿 §1.3 落点表加"不等于已启用"说明；速查 §8.3 前补「安装维护组处置」两条出口；`wf-start` 的 `--run` 改为"首轮不可用" |

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检 4/4。未提交、未收尾。

---

# 第二十五批（2026-11-05，吸收第 12 次独立复审 N12-1–N12-3 + 外部 M-1/M-2 与低优先项）

| 来源 | 处置 |
|---|---|
| N12-1（P2） | 五条用例的"非目标失败"分流加固：`f7-1` 只认 `WF_RECORD_INVALID`、非业务异常归前置；`f7-3` 内部码/非 `WF_*` 归前置；`inspect` 先核 `WF_OK`；`f5-4`/`r4-1` 对异常退出与无业务码判前置。实测注入 `RuntimeError` → red 非零退出 |
| N12-2（P3） | 收口计划轮数改为"十二轮" |
| N12-3（P3） | `§8.2` 的身份错误出口改为"核实或改用受支持宿主（wf 签发属第二轮）" |
| M-1 | `work_satisfied_fact` 与 `stop` 的 keep 分支统一走 `approved_touch_paths`；损坏快照显式拒绝，不再折叠成空批准面 |
| M-2 | `_harness.cli()` 解析失败时抛 `Precondition` 并带回 stderr 尾部，red 可归因 |
| 低优先 | `support_report` 排除 bool 轮次、清单级问题键名统一为 `required_step`；`bind` 的死 else 分支删除；`repro` 的临时目录退出清理（`WF_REPRO_KEEP=1` 可保留）；`_review_flow` 的 `SystemExit` 改为 `Precondition` |

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16。未提交、未收尾。

---

# 第二十六批（2026-11-05，吸收第 13 次独立复审 F13-1–F13-4 + 外部 P1/P2/P3）

| 来源 | 处置 |
|---|---|
| F13-1（P1） | `scope.cross_task_conflicts` 把 `handoff.wip.paths` 的**指纹对象**归一为路径字符串（`_wip_path_strings`），不再对 dict 做集合判断（此前跨任务 keep 后 Check 直接崩在 unhashable type） |
| F13-2（P2） | `require_success` / `code_problem` 两个结构化归类进入 harness；`f7-1`/`f7-3`/`inspect`/`f5-4`/`r4-1` 改为「期望码 → 目标失败；内部码/未知码/非成功 → 前置失败」 |
| F13-3 | `delivery_round` 在 **gates 与 install 自检两处**都排除 bool（上一轮替换未断言、实际未生效，本轮以 assert 校验写入） |
| F13-4 | 清单级问题键名统一为 `required_step`（同上，两处） |
| 外部 P1 | `_commit_paths` 支持 `moved_from`：目录移动的**旧路径删除进同一提交**（`git add -A`，paths 不匹配时剔除未跟踪项重试）；`stop`/`archive`/`abandon` 五个提交点接入；`_moved_from()` 在源已被恢复时返回 None，避免续做场景误提交 |
| 外部 P2 | `scope.cross_task_conflicts`、`scope.external_changes`、`tasks._block_overlapping_maintenance` 三处旧式快照读取统一走 `approved_touch_paths` |
| P3 | 锁「持锁者事实行」措辞债登记在实现稿 §2.3.11（需回机制稿同批补） |
| P4/P5 | `spec.parse_frontmatter` 的「未闭合」诊断移到循环内（原先不可达）；`review.launch` 的锚点改在**锁内重读后**计算 |

过程自伤（如实记录）：`moved_from` 首次接入时把 `old_rel` 只定义在"需要移动"的分支里，续做分支触发 `NameError` → archive 重入返回 70；另因 `git add -A -- <已消失路径>` 报 pathspec 不匹配导致归档失败。两处均按"分支内初始化 + 未跟踪项剔除重试"修复。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。未提交、未收尾。

---

# 第二十七批（2026-11-06，吸收第 14 次独立复审 F14-1–F14-3 + 外部 5 项）

| 来源 | 处置 |
|---|---|
| F14-1（P1） | `_moved_from` 不再用「目录是否存在」判断：改为看 `git status --porcelain` 是否仍报删除；新增 `_stale_task_deletions()`，续做分支据此把旧任务目录的残留删除一并提交 |
| F14-2（P2） | 新增 `only_two_outcomes()`：用例只承认「命中期望码」或「成功（缺陷复现）」，其它原因码（内部码/未知码/无关业务码）一律前置失败；`f5-4`/`r4-1`/`f7-1`/`f7-3` 与五条 CLI 用例全部接入 |
| F14-3（P2） | `review.launch` 的 Check 读取与通过核验移入锁内，锁内重读后用同一份记录生成检查 ID 与锚点 |
| 外部 1 | 机制稿 §12.1 的 D18、D21 行加「待裁」批注（实现侧为子集/未运行，第二轮开工前由人裁定） |
| 外部 2 | task-replan 无 Decision：维持 §2.3.11 提级登记（命令面加参需同批改契约） |
| 外部 3 | 实现稿 §7.1 的 V5 行改掉「dedupe 双扣未运行」的陈旧表述 |
| 外部 4 | 新增原因码 `WF_TARGET_MISSING`（机制稿码表 + `codes.py`），bind 的「对象不存在」不再复用 `WF_TARGET_COLLISION` |
| 外部 5 | 夹具 §4 的「历史锚点不可达」「未提交记录存在性负例」标注轮次归属（首轮适用） |

过程自伤：批量插入 `only_two_outcomes` 时未沿用原语句缩进，三条 CLI 用例语法破损；按"以 `require_business_code` 的缩进为基准重排调用块"修复。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `8432c06d`(1144)、implementation `cd961ef3`(929)。未提交、未收尾。

---

# 第二十八批（2026-11-06，吸收第 15 次独立复审 F15-1–F15-5 + 外部 5 项；交付 task-replan 的 Decision）

| 来源 | 处置 |
|---|---|
| F15-1（P1） | 移动时把来源路径写进记录（`task["moved_from"]`），续做据此定位删除；删除按目录名子串扫描的 `_stale_task_deletions`；abandon 续做也接入 |
| F15-2（P1） | `_commit_paths` 只并入**确切的删除文件**（`_deleted_paths()` 逐文件），不再对目录 `git add -A`，避免把别的任务的未授权改动带进提交 |
| F15-3（P2） | `WF_TARGET_MISSING` 真正登记进 `codes.CODES`（上一批插到了错误位置、未生效） |
| F15-4（P2） | `locate_task_dirs` 忽略没有 `task.json` 的空目录（移动中断留下的壳不再被当成重复记录） |
| F15-5（P3） | 机制稿 D18/D21 的「待裁」移到**交付归属单元格**内（此前落在第 5 格，表格渲染时被丢弃） |
| 外部 P1 | **`task-replan` 现在要求 `--decision`（choice=replan）**，缺证据即 `WF_SEMANTIC_DECISION` 并给三个出口；`wf-continue` 路由与实现稿登记同步为"已交付" |
| 外部 P2/P3 | D18 预算阶梯、stop 预览、执行器证据强度、启动四步、spec 三段、同义词白名单等维持既有登记（本轮不重复） |

过程自伤：`_move_task(task=…)` 记录后，`artifact_digests` 在"记录未落盘"时崩在 `join(None)` → 加空路径回退；`r80` 夹具改为先落 `task.json` 再算版本。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `ba9e47c3`(1144)、implementation `0018dfa5`(929)。未提交、未收尾。

---

# 第二十九批（2026-11-06，吸收第 16 次独立复审 F16-1–F16-7 + 外部 3 项）

| 来源 | 处置 |
|---|---|
| F16-2/F16-3（P1） | `task-replan` 生效时**旧批准失效**（`approval/approved_version` 清空、旧值进 `plan.approval_history`）；决定必须指向本任务（subject 含 id 或 object_digest=当前规划版本），并写入 `execution.human_decisions` 与动作 `decision_refs` |
| F16-1（P1） | `_commit_paths` 区分"已暂存删除"（索引里就是 D）与工作树待删除，前者不再重复 `git add`；其余路径逐条容错 |
| F16-4（P2） | `bind-resume` 的正对照改为**必须成功**；`handover` 的三处失效检查改为二元判据（期望码 or 成功） |
| F16-5（P2） | porcelain 改用 `-z`（NUL 分隔），引号/制表符路径不再被错误解析 |
| F16-6（P2） | 缺 `task.json` 的目录分两类：空壳忽略；非空**记为 `broken_task_dirs`** 并由 `inspect` 报告，不在定位阶段抛错 |
| F16-7（P2） | 实现稿合并重复的 replan 条目、命令表/调用形态/速查都补 `--decision` |
| 外部 P1 | **`baseline-apply` 写 `project-config.json` 时生成 `project_id`**（此前全库无生成者）；D21 在实现稿与机制稿降级为「部分交付」 |
| 外部 P2 | Check 的范围核对把「任务基线不可达」映射为 `WF_HISTORY_UNRESOLVED`（只读核对出口），不再静默通过 |
| 外部 P2 | 清单 `executable: true` 与事实对齐：三个投放点 chmod 改 `0o755` |
| P3 | 码表计数更正；`parse_frontmatter` 只剩一处「未闭合」诊断；`writer-handover accept` 补 `require_activation` |

过程自伤：F16-6 首版把"非空缺记录目录"当致命错误抛 `RecordInvalid`，导致 `r7r15` 的合成归档目录让整套失败；改为记录事实并交由 `inspect` 报告。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `57ecb7ac`(1144)、implementation `eef24e9e`(928)。未提交、未收尾。

---

# 第三十批（2026-11-06，吸收第 17 次独立复审 N17-1–N17-8）

| 来源 | 处置 |
|---|---|
| N17-1（P1） | replan 改为**同时**核对象与版本：subject 必须含任务 id，且 `object_digest` ∈ {当前 plan.version, 当前 PRD 摘要}，二者缺一即拒 |
| N17-2（P1） | `project_id` 改为在**提案内容**阶段定稿（`_finalize_project_config`）：缺则生成、有则保留，写盘后内容与提案一致，重入可判"已完成" |
| N17-3（P1） | 已有 `project_id` 永不被入口重建；仅在提案与磁盘都没有时生成（重建须走 repair） |
| N17-4（P2） | 提交回读改 `git show --name-only -z`，引号路径不再误报授权外 |
| N17-5（P2） | `broken_task_dirs(root)` 改为**现扫**，不再用模块级缓存（避免跨项目串味、新会话漏报） |
| N17-6（P2） | 实现稿 D21 的「部分交付」说明移进「轮次」单元格（原第 6 格渲染即丢） |
| N17-7（P3） | `_deleted_paths` 按 `-z` 记录结构消费改名/复制的第二个字段 |
| N17-8（P3） | 执行记录里的行数口径与实物对齐（928） |
| 外部 B1 | 码表计数文案改为「首版 34 + `WF_TARGET_MISSING` = 35」（机制稿 §12.1.1 与实现稿 D29） |

过程自伤：N17-1 收紧后 `r17r24` 的两处 replan 决定仍用占位摘要 → 4 条用例失败；改为传当次 PRD 摘要（`d21b`/`d22b`）后恢复 30/30。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `6d221a02`(928)。未提交、未收尾。

---

# 第三十一批（2026-11-06，吸收第 18 次独立复审 N18-1–N18-5 + 外部 `bind --run`）

| 来源 | 处置 |
|---|---|
| N18-1（P1） | replan 的摘要候选**排除空值**；PRD 解析失败直接 `WF_TEMPLATE_INCOMPLETE`（不再以空摘要放行） |
| N18-2（P1） | `project_id` 生成改为 `uuid5(任务 id + 项目根)`：同一任务重入得到同一值，动作输入摘要稳定，首次写入失败后可原样续做 |
| N18-3（P2） | `broken_task_dirs` 只扫**任务目录层级**（活动区一级、归档区 `archive/<月>/` 二级），排除容器与任务内部子目录，避免重复遍历 |
| N18-4（P1） | `scope.commit_paths` 改 `-z`：引号/制表符/换行路径不再被转义，归属与外部变更不再漏核 |
| N18-5（P3） | `_deleted_paths` 任一状态列出现 R/C 都消费源路径字段 |
| 外部 | `bind --run` 的**死分支**改为按参数选 kind，并以 `WF_CAPABILITY_UNAVAILABLE`（第二轮）拒绝；`wf-start` skill 与实现稿命令表同步 |

说明：`bind --run` 此前永远走 task 分支（返回 `WF_TARGET_MISSING`），skill 却宣称返回 `WF_TARGET_COLLISION`——文档与行为双侧不符，本轮同时修正为「未交付能力按轮次桩拒绝」。

验证：`run_all.sh` **75 项、失败 0**；`repro/run.sh` 16/16；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `9a807cb5`(928)。未提交、未收尾。

---

# 第三十二批（2026-11-06，吸收第 19 次独立复审 N19-1–N19-3 + 外部 N-1/N-2/N-3）

| 来源 | 处置 |
|---|---|
| N19-1（P1） | replan 显式消费 `current_plan_version` 的错误对象：PRD 机读块不可解析即 `WF_TEMPLATE_INCOMPLETE`，不再"空摘要被拒、文件摘要却放行" |
| N19-2（P2） | `project_id` 恢复为 **uuid4 随机生成**，但首次生成值写入任务记录（`project_config_project_id`）并在重入时复用——同一身份可续做，重建走 repair |
| N19-3（P1） | `bind --run` 的能力拒绝**提前到任何绑定/恢复分支之前**，已绑定会话也不能以 WF_OK 续做并写出错误对象类型的运行态 |
| 外部 N-1 | `wf.py` 转交 `repair`/`uninstall` 时把已解析 root 通过 `WF_PROJECT_ROOT` + `execve` 传给目标脚本；实测项目根与外部 cwd 两种形态都可用 |
| 外部 N-2 | `task-approve` 的决定必须有最低对象绑定：subject 含任务 id 或 `object_digest` 精确等于当前 PRD 摘要，二者都空即 `WF_APPROVAL_MISSING` |
| 外部 N-3 | `spec-update` 首跑不核前像——登记为偏差（Check 锚点兜底），承接第二轮 |

新增用例 `wf-repair-handoff`（双模）：验证两条调用形态都能走到 repair；注入"不传 root"即变红。全量随之变为 **76 项**（59 既有 + 17 repro）。

过程自伤：新用例首版直接 `return` 字符串，未按契约抛 `TargetFailure`，red 报"未归类失败"；补齐后 17/17。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `7f105fbc`(929)。未提交、未收尾。

---

# 第三十三批（2026-11-06，吸收第 20 次独立复审 N20-1–N20-3 + 外部 F1/F2）

| 来源 | 处置 |
|---|---|
| N20-1（P2） | `project_id` 生成值改为**整批校验通过后**才写入任务记录（此前在预校验循环里就 save，被拒路径也会留下 memo） |
| N20-2（P2） | `wf-repair-handoff` 改为结构化归类：只有「`WF_PATH_INVALID` 且 facts.project 为空」算目标失败，内部错误/未知码/其它业务失败一律 `Precondition` |
| N20-3（P3） | `validation` §95 同步为 17 条 / 76 项，并补 `wf-repair-handoff` 的断言与注入点 |
| 外部 F1 | 两条「首轮适用」未覆盖场景：在夹具 §4 写明**构造方案与期望行为**，并如实标注「仍未补」；本轮**没有**新造夹具（尝试加进 r17r24 时因写权状态冲突失败，已撤回，不提交半成品） |
| 外部 F2 | D18/D21 的裁定请求写入 `root-cause.md`（补实现 / 按 D24 先例显式延期），等待人裁；D 表标签保持「待裁 / 部分交付」，不擅自改口径 |

说明：F1 的两行是**首轮标为适用、目前仍未运行**的场景。按设计稿 §8.2 第①项，严格读它们构成首轮收口的真实缺口；本轮只做到"如实登记 + 给出构造方案"，未完成夹具补跑。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `7f105fbc`(929)。未提交、未收尾。

---

# 第三十四批（2026-11-06，吸收第 21 次独立复审 N21-1–N21-3 + 外部 P1-1/P1-2/P1-3）

| 来源 | 处置 |
|---|---|
| N21-1（P1） | `baseline-apply` 重排为：内存算计划 → 与未结案意图比对（不同提案即 `WF_ACTION_INCOMPLETE`）→ **整批前像预检** → 才登记动作；生成值随意图同次持久化，重入从意图取回 |
| N21-2（P2） | `wf-repair-handoff` 增加 `preview.target_root == 项目` 断言；`WF_CAPABILITY_UNAVAILABLE` 归前置失败 |
| N21-3（P2） | `task-check` 在记录缺失时给 `WF_RECORD_INVALID` + 三个恢复出口，不再拼 `None` 路径崩溃 |
| 外部 P1-1 | `codes.py` docstring 的「36 枚」改为「35 枚（34 + WF_TARGET_MISSING）」 |
| 外部 P1-2 | `task-reassess` 的空集合直通前检查 `suspended` 残留，有则 `WF_HISTORY_UNRESOLVED` |
| 外部 P1-3 | 机制稿 D21 行补「待裁」，与 D18 对齐 |

过程自伤：本轮先按 N21-1 把预检整体挪到意图比对之前，导致 `r1` 的「不同提案不得覆盖未完成动作」拿到 `WF_WORKSPACE_UNRESOLVED` 而非 `WF_ACTION_INCOMPLETE`；重排为「意图比对 → 前像预检 → 登记动作」后恢复 76/0。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `7f105fbc`(929)。未提交、未收尾。

---

# 第三十五批（2026-11-06，吸收第 22 次独立复审 N22-1–N22-3 + 外部 A–D）

| 来源 | 处置 |
|---|---|
| N22-1（P2） | 身份值改为**必然进动作 inputs**，重入先按「记录字段 → 未结案 inputs」复原再比摘要，"从意图恢复"才真正可达 |
| N22-2（P2） | 身份优先级改为 **意图值 > 现场配置 > 新生成**：现场被外部改 id 不再让同一提案被判"不同提案"，差异留给前像冲突 |
| N22-3（P3） | 实现稿 §7.3 计数改 76 项 / 17 repro |
| 外部 A | `unanswered_plan_questions` 改**整词/编号边界**匹配（`plan-q-1` 不被 `plan-q-10` 覆盖，且允许 `plan-q-1：说明` 后缀） |
| 外部 B | `install.py::_dump_json` 改 tmp + fsync + `os.replace` 原子写，与 `uninstall.py` 同标准 |
| 外部 C | 实现稿 §1.3 标注 `templates/task/task-record.json` 是**参考文档、无代码消费** |
| 外部 D | 首轮 PRD/implement 的「19 tests」改为「全部通过（数量以实跑为准）」，并注明 2026-11-06 增补 |

过程自伤：外部 A 首版按空白分词，导致 `plan-q-1：初始化…` 这种带后缀写法不再被识别，init 全流程 101 项失败；改为按编号边界正则后恢复 76/0。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `ef64aa96`(931)。未提交、未收尾。

---

# 第三十六批（2026-11-06，吸收第 23 次复审 N23-1–N23-4 + 外部 P2-NEW）

本轮按"不变式而非点修补"处理，四类各落一条：

| 不变式 | 落地 |
|---|---|
| 身份：发布身份 == 可恢复意图身份；所有来源保存同值；重入不重选；跨任务不绕过 repair | `actions.new_action` 保存 `inputs` 本体；身份优先级「记录 → 未结案 inputs → 现场 → 新生成」；提案自带 id 与已知身份不一致即拒；现场缺 id 而历史有身份痕迹时 `WF_HISTORY_UNRESOLVED`（要求 repair） |
| 移动：成功必须同时证明目标后像、源删除与授权外内容终态 | 源删除路径无法规范化时**整批拒绝**（`WF_PATH_INVALID`），不再静默跳过（N23-2） |
| 证据：宣称幂等/零副作用必须断言受保护状态后置条件 | `r83` A5d 从"不抛异常"改为"文件仍不存在"；变异注入可打红（N23-3） |
| 批准面：所有消费点同一状态判定，未覆盖格逐一登记 | 新增 `validation` §96「状态矩阵登记面」：四组矩阵逐格标已测/未测/HUMAN（N23-4） |

外部 P2-NEW：`task-check` 的验证命令在 OS 锁内执行——**已做** `verification_timeout_seconds`（项目配置，正整数）给上界，超时按 `WF_CHECK_FAILED` 报；**未做**把步骤③移出锁（结构改动），已在实现稿 §2.3.11 登记并要求第二轮承接。

过程自伤：`check.py` 的 `subprocess.run` 实参名是 `workdir` 而非 `cwd`，首次替换失效；按实际签名重写后生效。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `0498a807`(932)。未提交、未收尾。

---

# 第三十七批（2026-11-06，吸收第 24 次复审 N24-1–N24-4 + 外部 10 项）

| 来源 | 处置 |
|---|---|
| N24-3（P2，实测） | `verification_timeout_seconds` 此前是**死键**（不在 DEFAULTS → `value_of` 抛错被吞）。已加入 DEFAULTS（默认 0=不设界）；配置非法时 `WF_RECORD_INVALID`，不再静默取无超时。实测 1s 配置可解析 |
| N24-1（P1） | **现场来源**的身份也写入任务记录与动作 inputs：同一身份不再因来源不同而在重入时被重选 |
| N24-2（P1） | 历史身份扫描扩展到「未结案动作 inputs 里的身份」，不再只认 memo |
| N24-4（P1） | §96 矩阵补 5 个漏列消费点（维护处置承接、`work_satisfied_fact`、`cross_task_conflicts`、外部变更再判定、两个写入口）与移动的**调用点轴**（4 条 `_commit_paths` 路径）；修正「未开工 × 维护重叠」为已测（`r60`/`r61`） |
| 外部 3 | `writer-handover accept` 补 `assert_no_foreign_wip`（与 acquire 同款边界） |
| 外部 2 | `baseline-apply` 的「历史有身份、现场缺失」出口改为「从 Git 恢复 / 等 repair（第二轮）」，不再指向不存在的能力 |
| 外部 4/6/7/8/9/10 | 逐条登记在实现稿 §2.3.11（卸载不登记维护写者、spec 预算键无效果、skill 否定句与 §1.1 冲突待裁、复杂度②③④无机械核对、enable 停用分支不可达、巡检只算不触发） |
| 外部 5 | 收口计划内部陈旧段落修正 |

回归：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `931bb006`(1144)、implementation `c683c285`(939)。未提交、未收尾。

---

# 第三十八批（2026-11-06，吸收第 25 次复审 N25-1–N25-3 + 外部 8 项）

| 来源 | 处置 |
|---|---|
| N25-1（P1） | 身份解析顺序改为「**先本任务可恢复身份（记录 → 未结案 inputs → 现场）→ 再查跨任务历史**」；只有本任务无身份且现场缺失才要求 repair。此前"仅 pending 身份"会被自己的历史检查挡住 |
| N25-2（P1） | `value_of` 的 **problem 必须被消费**：非法超时值在启动验证命令前返回 `WF_RECORD_INVALID`，不再静默退成无界 |
| N25-3（P2） | §96 按证据强度三档（拒绝已验证 / 局部后置 / 完整零写入）修正 4 处登记；身份表改为 10 态 |
| 外部 1 | `verification_timeout_seconds` 同步进骨架 JSON 与机制稿 §8.1 键表；新增 `ZERO_ALLOWED_KEYS`，0=不设上界的语义显式登记 |
| 外部 2 | `cmd_stop` 空决定数组 → `WF_SEMANTIC_DECISION`（此前 IndexError / 退出 70） |
| 外部 3 | 实现稿命令表与速查补 `writer-handover begin --decision <文件>` |
| 外部 4 | `WF_REVIEW_UNAVAILABLE` 的归属改正为仅 `review-decide --unavailable` |
| 外部 5/6/7 | 登记精确化：两段 checklist 无承载结构；`spec` 身份不可核时严于字面；引导层缺 Python 版本自检——**并已实现**引导层启动版本检查 |
| 外部 8 | `spec` 配置非法由 `WF_CAPABILITY_UNAVAILABLE` 改为 `WF_RECORD_INVALID`（码义不改），`r57` 期望同步 |

过程自伤 2 次：①`verification_timeout_seconds` 默认 0 与"正整数键"校验冲突，导致 `task-check` 全链 `WF_RECORD_INVALID`、init 103 项失败——加 `ZERO_ALLOWED_KEYS` 后恢复；②`r57` 仍断言旧码。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `6610c5ab`(1145)、implementation `263f8694`(942)。未提交、未收尾。

---

# 第三十九批（2026-11-06，吸收第 26 次复审 N26-1/N26-2 + 外部 7 项）

| 来源 | 处置 |
|---|---|
| N26-1（P2） | §96 的 `baseline-apply` 行按格拆档：两格 ②、两格 ①，并写明**没有任何一格达到 ③**（不再合并声称） |
| N26-2（P3） | 机制稿 §8.1 的超时键**并入三列表格**；非法域改为「负数/布尔/非整数」，0 合法 |
| 外部 1 | 安装器新增 `--strict-source`：核发行子树与提交一致，脏即 `WF_RELEASE_CONFLICT`；默认只记 `source_dirty`（作者仓库的发行树在开发循环里天然为脏）。真正按 tag 提交取字节承接第三轮 |
| 外部 2 | 登记：复杂度/TDD 的人判没有可核载体（`plan.approval` 不含这两项），承接第二轮 |
| 外部 3 | 登记：卸载不登记维护写者，并注明 `maintenance-flow.md` 未声明该偏离 |
| 外部 4 | 登记：无就绪视图/建议；实现稿 V1 措辞改为「直接 bind --task」，不再冒充「按就绪选择」 |
| 外部 5 | 登记：安装自检不核 skill frontmatter |
| 外部 6 | repair 轮次口径统一为**第三轮**（与 D09 一致），改掉报错文案里的「第二轮」 |
| 外部 7 | 归档回显新增 `inspection_hint`：正常归档整数倍时提示巡检到点（不再只靠人主动跑 inspect） |

过程自伤 1 次：干净检出检查最初对**整仓库**执行 `git status`，导致 7 条 repro 在作者仓库里前置失败；改为只核发行子树、并设为 `--strict-source` 选项后恢复 17/17。

验证：`run_all.sh` **76 项、失败 0**；`repro/run.sh` 17/17；三稿 0 problem；机检通过；`validate-skills` 25；字节复现。
绑定：design `926fd621`(721)、mechanism `30012ff9`(1145)、implementation `61620127`(947)。未提交、未收尾。

---

# 第四十批（2026-11-06，W1 分母修复；承接第 27 轮复审的 x/N 计数）

| 项 | 处置 |
|---|---|
| 孤儿套件回接 | `cp4_a8` `cp5_b12` `r35_tests` `f1_ordinary` `p5_v1` 进 `SUITES`；`d1_tests`/`d1_wf_tests` 在 README 标「手动、需真实宿主压缩、不计入分母」 |
| 崩溃修复 | `cp4_a8.py`、`r35_tests.py` 写死 `/tmp/wf-fixtures/{fu,f5,f3}` 且无人创建 → 改为脚本内自带夹具（`wf_fixture.sh`）；技能根改从 `F/.agents/skills` 取，不再假设外部 skills 根 |
| `cp5_b12` 红 4 条 | B2 三条未跟 P1-1 外部变更人判规则 → task-check 补 `--decision`（`choice=checked`，subject 含 OID）；夹具补 `f2_setup.sh` + `f1_init.py`（此前无初始化任务、无基线，故 `task-start` 报能力不可用）；B1 经实测是 `WF_OK`+warning，原本断言正确，**未**改期望 |
| 计数 | `run_all.sh` 76 → **81 项**；`validation` §95 同步并记回接实测（`cp5_b12` 5/9 红、两个套件崩溃、两个本绿） |
| 观察 | 回接后首次全量出现一次 4 项 `INIT-FAILED`（r7r15/r67/r68/r69）；隔离与配对复跑均绿，连续两次全量 81/0，暂记偶发未定位 |

过程自伤 1 次：先把 `cp5_b12` 的 B1 期望改成 `WF_SEMANTIC_DECISION`（依据 §2.3.11「停用分支不可达」），实测纯残留场景返回 `WF_OK`+warning，回退原断言并保留对 `enable` 停用分支的登记。

验证：`run_all.sh` **81 项、失败 0**（连续两次）；回接三套件分别 9/9、9/9、10/10。
未提交、未收尾。

---

# 第四十一批（2026-11-06，W4 裁定落地；承接第 27 轮审查后的四项人裁）

裁定记录：`pending-decisions.md` §6（2026-11-06 人裁）；`root-cause.md` 待裁表逐行标「已裁」。

| 项 | 处置 |
|---|---|
| W4-5 裁定落盘 | `pending-decisions.md` 新增「## 6. 2026-11-06 人裁（第 27 轮审查后）」五列表（项/裁定/依据/时间/范围/出口），覆盖 D18、D21、两条首轮夹具、dogfood 前置共 5 行；`root-cause.md` 待裁表 3 行逐行标「已裁，见 pending-decisions.md §6」 |
| W4-1 D18 延期 | 机制稿 §12.1 D18 行改「该轮交付·第三轮（2026-11-06 人裁延期）」；实现稿 §6.2 D18 轮次列、§7.3 第十轮登记条、`spec_output_codepoints` 条同步；夹具 §4 两行（预算降级、截断标记）改「延至第三轮，该轮交付后核」。grep「待裁」不再命中 D18 |
| W4-2 D21 集合负例 | 新增 `repro/d21-executor-set-{multi-clone,move,venv-rebuild,purge-reconfirm}.py`（后两条为可构造的追加项：venv 重建按设计稿 §1.1「元数据变化才失配」双方向断言；purge 用 project_id 重建等价构造，真实 `uninstall --purge` 链路第三轮）。确认集合隔离到夹具临时 `HOME`；确认动作用伪终端进程内驱动（与第 27 轮探针同法，不证明真人确认）。四条均双模 0 退出；机制稿 §12.1 D21 行与实现稿 D21 行的「待裁／确认集合负例未交付」标签同步为「已补 repro，repair 重建留第三轮」（grep「待裁」在 D 表不再命中） |
| W4-3 首轮两夹具 | 新增 `repro/history-anchor-unreachable.py`（amend → `WF_HISTORY_UNRESOLVED` 带三出口；`git reset --soft` 恢复可达后重检通过）、`repro/record-missing-in-worktree.py`（删 task.json → `WF_RECORD_INVALID` JSON 带 exit、`inspect` 列 `broken_task_dirs`；恢复后正常）。双模 0 退出 |
| W4-4 dogfood 前置 | 设计稿 §8.2 ③ 补「门禁①成立后即可开跑，不必等待收口全绿」（仅此一句，W4-4 已授权）；`dogfood-plan.md` 前置第 1 条同步、顶部加「实跑放最后一个批次，第 27 轮不执行」 |
| 连带 | 机制稿 §0.1 输入摘要随设计稿改动重绑（design `926fd621…` → `d5d25d4f…`）并补变更叙述；机制稿 D18 行的「pending-decisions §4」按机检要求改写为「pending-decisions.md 第 4 节」（裸 §4 缺所有者前缀） |

过程自伤 2 次：① `d21-executor-set-purge-reconfirm.py` 初版漏 `import os`，双模均崩，补 import 后恢复；② 两条首轮夹具的正例最初用 `git reset --hard` 恢复可达性，会把 writer.json 重置回安装态导致 `WF_WRITER_BUSY`，改 `reset --soft`（不动工作树）后正例通过。

并行会话说明：本批与另一 CLI 会话（W1 分母修复，见第四十批）在同一工作树并行施工；两批产物无重叠（它动 SUITES/三套件/README/§95 的 W1 段，我动裁定记录/三稿标签/6 条 repro/§95 的 W4 段），合并后 `run_all` 末态 87 项。

验证：`run_all.sh` **87 项、失败 0**（64 既有 + 23 repro）；6 条新 repro 单独双模全绿；`validate-wf-design.py` 通过（引用 567、三率 100%、输入摘要 4/4）；`check-doc-refs.py` 三稿 0 problem；`build-wf-release.py --verify` 通过；`validate-skills.sh` 通过。
绑定：design `d5d25d4f`(721)、mechanism `185294e5`(1145)、implementation `9fe2f3ef`(947)。未提交、未收尾。

---

# 第四十二批（2026-11-06，第 28 轮的记录级修复：分母入库 + 引用去歧义）

本批不动产品代码，只修第 28 轮留下的四处记录缺陷——它们本身不难，但留到下轮就会变成"新发现"。

| 项 | 处置 |
|---|---|
| ① `pending-decisions.md` 三个 `## 4.` | 新人裁节改编号 **`## 6.`**（文件顶部加「编号提示」说明历史重复编号）；W4 批次新增的 **17 处**引用改指 §6（实现稿 4、机制稿 2、夹具 3、root-cause 3、dogfood-plan 1、执行记录 2、validation 2）；历史 §3/§4 引用保持原意未动 |
| ② D18 标签两侧不一致 | 机制稿与实现稿统一为「跨轮基础项（单文件读取与不截断自首轮成立）；多文件预算降级链与截断标记延至第三轮」；650/643 随之从首轮分母移出 |
| ③ 分母只在 `/var/tmp` | `denominator.md` + `denominator.json` 入库到本任务目录；4 行升级（623/624/671/674 → 已断言）、2 行顺延（650/643 → 等第三轮）写回；**正式口径 x/N = 23/84（27.4%）**，并给延期前口径 23/86 备查 |
| ④ dogfood 头部过期 | 「第 27 轮不执行」→「门禁①成立后的最后一个批次，本轮（第 28 轮末）不执行」 |
| 连带 | `review-packet.md` 顶部标注第 1 节三稿哈希已失效并给现行绑定；`validation` §95 增「分母入库」段并写明「87 项绿灯是套件层，不能替代场景行覆盖」 |

验证：`run_all.sh` **87 项、失败 0**（本批不改代码，复跑确认）；`validate-wf-design.py` 通过（引用 567、三率 100%、输入摘要 4/4）；三稿 `check-doc-refs.py` 各 0 problem；`build-wf-release.py --verify` 字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `83d3fc11`(947)。未提交、未收尾。

未做（如实记）：W3 的「前 4 行」未开工。逐行核对后确认每行都是**整行义务**（如 629 覆盖 4 状态 × 11 消费点），一条 repro 只能填一格，不足以把行从「仅有原因码」升到「已断言」；按「断言不被检验就等于没有」的纪律，宁可不写也不写半条。W3 需按行拆批，见下一步计划。

---

# 第四十三批（2026-11-06，W3 批 A：执行器批准链与配置可信；粗行拆子行）

| 项 | 处置 |
|---|---|
| 668 执行器配置可信（升档） | 新增 `repro/executor-tuple-mismatch.py`：project 作用域确认绑定解释器 size/mtime；同路径替换（只改指纹）后 `executor_ready=False` 且 `wf.py status` 返 `WF_EXECUTOR_UNCONFIRMED`。注入 = `matches()` 不核 size/mtime → 红（两条断言同时打红） |
| 673 执行器首次写入（升档） | 新增 `repro/executor-approval-chain.py`：键未进基线/已批准 PRD 时 `confirm-executor --scope project` 返 `WF_APPROVAL_MISSING` 且**零写入**；把键与值补进基线后同一确认成立。注入 = 跳过 `project_key_approved` → 红 |
| 粗行拆子行（人裁） | 设计行 629（机读触碰面）按 §96 ① 拆为 4 状态 × 11 消费点 = 44 个子行 `629.s*.c*`，原单行不再计入；`validation` §96 ① 补「与分母的对应」映射段 |
| 分母 | `denominator.md`/`.json` 更新：668、673 → 已断言；**x/N = 27/127（21.3%）**（拆行使分母 84→127、分子 25→27；比例下降是计价结果） |
| 残余缺口（不随升档关闭） | 668 仍不比对 `python_version`；673 的 `project_key_approved` 只扫活动区（归档 PRD 不扫）——两条仍按实现稿 §2.3.11 ③ 登记，第三轮承接 |

验证：两条新用例各自 green/red 双 0 退出；`repro/run.sh` **25/25**；`run_all.sh` **89 项、失败 0**；`validation` §95 计数 23→25、87→89 同步。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `83d3fc11`(947)。未提交、未收尾。

过程自伤 1 次：`executor-approval-chain.py` 首版正例写成 `confirm_raw(project and module, project)`（笔误但能跑），已改为 `confirm_raw(module, project)` 并复跑双模。

---

# 第四十四批（2026-11-06，629 s1 可达性判定 + `verify_holder` 假宣称登记）

| 项 | 处置 |
|---|---|
| `verify_holder` 零运行时消费（新登记，归因待定） | 实现稿 §2.3.11 新增条目：`payload/` 全树对 `verify_holder` 只有 1 处引用（`lock.py:215` 定义本身），零调用点；`repair.py`/`uninstall.py` 各自含 `_live_holder`，不导入运行时。因此本节开头「运行时与 repair/uninstall 都在锁内消费该判定」只有后半成立——运行期既不读持锁者事实行、也不会因持有者存活而返 `WF_WRITER_BUSY`。按机制稿 §12.4 先判实现缺陷或文档错，归入 688 批；判定前不得把「存活探测」描述为运行期已生效 |
| 629 s1 可达性判定 | 逐格读代码：`c1/c2/c3/c4/c6/c7/c11` 可达（stop 只要求绑定+写权；`task-start` 即调分类器；baseline/spec 写入口只需批准面），`c5/c8/c9/c10` 不可达（外部变更与两种 check 期判定只在 Check，`work_satisfied_fact` 只在 finish，`cross_task_conflicts` 无开工期调用点） |
| 分母 | 不可达 4 格标「不适用」并移出：**N 127 → 123、x 27**，`x/N = 22.0%`；`denominator.md` 增加「s1 可达性判定」表（格/入口/判定/依据行） |
| 结论 | s1 的真实工作面是 **6 格待补**（`c6` 已有断言），不是 11 格 |

验证：`denominator.md`/`.json` 与 `validation` §95/§96 同步；三稿 `check-doc-refs.py` 各 0 problem；`validate-wf-design.py` 通过；`build-wf-release.py --verify` 字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation 因本批新增一条登记而变化（`0f66a8bf`(949)）。未提交、未收尾。

---

# 第四十五批（2026-11-06，629.s1 批 B：c1 收工归属边界；c2/c3 归第二轮）

| 格 | 处置 |
|---|---|
| **s1.c1（已断言）** | 新增 `repro/stop-unstarted-surface.py`：已批准未开工任务收工时，keep 的边界来自 `plan.touch_paths`——①声明漏项 → `WF_WORKSPACE_UNRESOLVED`；②两条都声明时越界项**只点名** `notes.txt`（`facts.out_of_scope`）；③批准面内 keep 成立。注入 = 未开工不回退 plan（批准面变空）→ 越界项变成两条、正例被拒，双模都红 |
| **s1.c2/s1.c3（改判等第二轮）** | 正例需**第二个任务**承接，但首轮 `task-new` 对同一项目只产出一个任务（重复调用返回同一 id 并 `WF_WRITER_BUSY`，与 denominator 行 600「单任务与多任务流程＝等第二轮」一致）；拒绝分支已由 `repro/transfer-target-task-field.py` 覆盖（不存在/自承接 → `WF_SEMANTIC_DECISION`）。故两格从首轮分母移出，标「等第二轮（多任务未交付）」 |
| 分母 | **N 121、x 28，x/N = 23.1%**（c1 升档 +1；c2/c3 移出 -2）；`denominator.md` 更新结论句与逐行表 |
| 计数 | `validation` §95：25→26 条 repro、89→90 项；§96 ① 的 s1 结论同步 |

验证：新用例 green/red 双 0 退出；`repro/run.sh` **26/26**；`run_all.sh` **90 项、失败 0**。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `0f66a8bf`(949)。未提交、未收尾。

过程自伤 2 次：①先按「一个夹具多任务」设计，实测第二次 `task-new` 返回同一任务 id（并 `WF_WRITER_BUSY`），流程跑不通——这恰好是 c2/c3 该判第二轮的证据；②`stop` 的「漏列」检查先于「越界」检查，首版只声明 `notes.txt` 得到的是漏列拒绝，不是越界拒绝，改成同时声明两条才命中 `out_of_scope`。

---

# 第四十六批（2026-11-06，629.s1 批 C：c4 断言 + c11 改判；688 归因出结论）

| 项 | 处置 |
|---|---|
| **s1.c4（已断言）** | 新增 `repro/task-start-surface.py`：开工期分类器按未开工回退面分桶——面外未归属改动 → `WF_WORKSPACE_UNRESOLVED` 且 `other_tasks` 只点名 `notes.txt`；清掉后，面内未提交改动可开工。注入 = 未开工不回退 plan → 阻断项变成两条、合法开工被拒（双模红） |
| **s1.c11（改判不适用）** | 查证：`baseline-apply`（`tasks.py:3170`）与 `spec-update`（`tasks.py:3378`）都要求 `phase ∈ execute/check/finish`；未开工时该写入口不存在 → 该格在 s1 属**不适用**，移出分母 |
| **688 归因（结论：文档错，非实现缺陷）** | 依据设计稿 §8.2「互斥与锁生命周期」应拒绝列：「**PID 消失即当空闲**」被明令禁止，出口是「持锁标记 / 存活探测 / 人确认恢复」；§4.4 对「未知旧写者是否仍活动」要求**阻断相关写入**并交人按 §5.5 恢复，不是自动接管。运行期一律阻断（fail-closed）符合该要求；判定死活由 `repair`/`uninstall` 各自自含的 `_live_holder` 承担。故实现稿「运行时也在消费该判定」为**失实表述**，已就地更正；`verify_holder` 记为**无调用方死代码**（清理/复用属维护项，不影响首轮行为）。若日后要让运行期区分死活持有者，须先改设计稿 |
| 分母 | **N 120、x 29，x/N = 24.2%**（c4 升档 +1；c11 移出 -1）；s1 现余 **1 格**（`c7` 收工回执核对） |
| 计数 | `validation` §95：26→27 条 repro、90→91 项；§96 ① 的 s1 结论同步 |

验证：新用例 green/red 双 0；`repro/run.sh` **27/27**；`run_all.sh` **91 项、失败 0**；三稿 `check-doc-refs` 各 0 problem、`build-wf-release.py --verify` 字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `17f26045`(949)。未提交、未收尾。

本批自伤 1 次（已修）：新写的归因段里 `§4.4`/`§5.5` 漏了所有者前缀，`check-doc-refs.py` 报 2 problem；补成「设计稿 §4.4」「设计稿 §5.5」后归零，实现稿绑定随之更新为 `17f26045`(949)。

---

# 第四十七批（2026-11-06，629.s1 批 D：c7 收工回执核对 —— s1 整行收口）

| 项 | 处置 |
|---|---|
| **s1.c7（已断言）** | 新增 `repro/maintenance-disposition-s1.py`：①与请求范围重叠的未结维护组 → `WF_WIP_UNRESOLVED` 且 `overlapping_receipts` 点名 `pkg/b.py`；②处置字段齐但**事实不可核**（claim `commit`、实际未提交）→ `WF_HISTORY_UNRESOLVED`（`pending_check`），不得当已结案；③真正提交后回执派生 `persisted` → 开工成立。注入 = `maintenance_disposition_probe` 恒 True（字段齐即结案） |
| 连带发现（已登记思路） | `writer.blocking_receipts` 与 `verify_holder` 同类：**定义无调用方**（`writer.py:307`）；`WF_WIP_UNRESOLVED` 实际由 `_block_overlapping_maintenance`（`tasks.py:1681`）与 `changes_persisted_fact`（`:937`）产生。不影响本格判定，但与 688 的「死代码」条同批清理时一并处理 |
| s1 收口 | 11 格全部定论：**已断言** c1/c4/c6/c7；**等第二轮** c2/c3；**不适用** c5/c8/c9/c10/c11。`validation` §96 ① 的对应段同步 |
| 分母 | **N 120、x 30，x/N = 25.0%** |
| 计数 | §95：27→28 条 repro、91→92 项 |

验证：新用例 green/red 双 0；`repro/run.sh` **28/28**；`run_all.sh` **92 项、失败 0**。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `12e2fcbe`(951)（本批新增「运行时死代码」条，把 `verify_holder` 与 `blocking_receipts` 两处一起登记）。未提交、未收尾。

过程自伤 2 次：①处置对象的形状先按 `{kind, evidence}` 写，实测 `_disposition_complete` 还要求 `decision.choice == kind`，补上后才走到「事实不可核」分支；②red 模式下第③步会因注入提前 disposed 而另报 `WF_SEMANTIC_DECISION`——属同一注入的连带效应，目标断言（第②步被放行）已正确判红，未据此放宽判据。

---

# 第四十八批（2026-11-06，629.s3：快照缺键 11 格判定 + 3 条 repro）

s3 的义务只有一条：**已开工任务的批准面缺键即拒，不得回退可变的 `plan.touch_paths`**——否则手改 `task.json` 的 plan 就能扩大批准面，收工归属与 Check 范围全部失效。

| 入口 | 用例 | 断言 |
|---|---|---|
| 收工（c1 及同路径 c2/c3/c7） | `repro/snapshot-missing-stop.py` | keep/transfer 均 `WF_RECORD_INVALID` |
| Check（c4/c5/c9/c10） | `repro/snapshot-missing-check.py` | `task-check` 返 `WF_RECORD_INVALID`，且原因指向缺键；任何其它业务码都判目标失败（`code_problem`） |
| 写入口（c11） | `repro/snapshot-missing-write.py` | `spec-update` 返 `WF_RECORD_INVALID`；`baseline-apply` 共用同一批准面判定 |

注入统一为「缺键时回退 plan」：red 下 Check 变 `WF_CHECK_FAILED`、spec-update 变 `WF_DEFINITION_INVALID`、stop 直接放行——三条都被判红。

| s3 判定 | 格 |
|---|---|
| 已断言（6） | c1、c4（此前由 f7-3 覆盖，本批补齐入口级）、c5、c9、c10、c11 |
| 仅有原因码（3） | c2、c3、c7 —— 同一批准面守卫先行拒绝，各自的承接核验/回执探针未走到 |
| 不适用（2） | c6（开工期门禁，s3 已开工）、c8（finish 需 Check 通过，链式不可达） |

分母：**N 118、x 35，x/N = 29.7%**。计数：§95 的 repro 28→31、全量 92→95。

验证：三条用例 green/red 双 0；`repro/run.sh` **31/31**；`run_all.sh` **95 项、失败 0**。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `12e2fcbe`(951)。未提交、未收尾。

过程自伤 1 次：`snapshot-missing-stop.py` 首版在 keep 分支放行后继续跑 transfer，拿到的不是目标码而是 `WF_WRITER_BUSY`（放行已暂停任务并释放写权），`only_two_outcomes` 判前置失败；改为命中即 `break`。

---

# 第四十九批（2026-11-06，629.s2：空批准面 11 格判定 + 2 条 repro）

s2 的要害：`entry_snapshot.touch_paths == []` 是**合法状态**，不是损坏——空就该按空判定（任何路径都越界），
绝不能因为空就回退 `plan.touch_paths`（那等于把"批准面为空"读成"没批准过"）。

| 入口 | 用例 | 断言 |
|---|---|---|
| 收工（c1） | `repro/snapshot-empty-stop.py` | 空面下 keep 任意路径 → `WF_WORKSPACE_UNRESOLVED` 且 `out_of_scope` 点名 `pkg/b.py` |
| 写入口（c11） | `repro/snapshot-empty-write.py` | `spec-update` → `WF_SCOPE_UNRESOLVED` 且 `facts.touch_paths == []`（回显空面即证明用的是快照而非 plan） |

注入统一为「空数组回退 plan」：red 下 stop 变 `WF_OK`、spec-update 变 `WF_DEFINITION_INVALID`，两条都判红。

| s2 判定 | 格 |
|---|---|
| 已断言（2） | c1、c11 |
| 仅有原因码（2） | c2、c3（需第二任务承接；拒绝分支由 `transfer-target-task-field.py` 覆盖） |
| 未测（4） | c4、c5、c9、c10 —— 单任务夹具跑 `task-check` 会**先被 `task.work-satisfied` 拦下**，没隔离到范围核对；如实登记，不假装已断言 |
| 不适用（3） | c6（开工期门禁）、c7（请求面为空，回执路径不可能重叠，该消费点无义务对象）、c8（finish 链式不可达） |

分母：**N 115、x 37，x/N = 32.2%**。计数：§95 的 repro 31→33、全量 95→97。

验证：两条用例 green/red 双 0；`repro/run.sh` **33/33**；`run_all.sh` **97 项、失败 0**。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `12e2fcbe`(951)。未提交、未收尾。

未做的部分说清楚：c4/c5/c9/c10 要断言，得先把 Check 的 `task.work-satisfied` 前置补上（给任务一个可观察成果），属下一批夹具工作，不是本轮偷懒。

---

# 第五十批（2026-11-06，s2 补 c4 与 s4 判定 —— §96 ① 的 44 格全部定论）

| 项 | 处置 |
|---|---|
| **s2.c4（升档）** | 新增 `repro/snapshot-empty-check.py`：空批准面下 `task-check` 把本任务文件归 **c 桶**并阻断，`e` 桶必须为空；注入=空数组回退 plan 时该文件变 e、拒绝码也变 → 判红。前置处理：`task.work-satisfied` 对纯调查任务要求可观察成果，用 `task-retrospect` 补上（这正是上一批登记的那个前置） |
| **s2 其余格** | `c9` 改「仅有原因码」（跨任务冲突需另一任务 WIP＝第二轮）；`c5`/`c10` 仍为**未测**——空面下无可判对象，没隔离出来，如实登记 |
| **s4（已断言 6 格）** | 新增 `repro/snapshot-broken-type.py`：`touch_paths` 为字符串时，收工 / Check / spec-update 三入口均 `WF_RECORD_INVALID`；注入=类型不符当单条路径收下，收工变 `WF_OK` → 判红。s4 判定：已断言 c1/c4/c5/c9/c10/c11；仅有原因码 c2/c3/c7；不适用 c6/c8 |
| 分母 | **N 113、x 44，x/N = 38.9%**；§96 ① 的 **4 状态 × 11 消费点共 44 格，至此全部有定论**（27 已断言 / 9 仅有原因码 / 8 不适用 等，逐格见 `denominator.md`） |
| 计数 | §95：33→35 条 repro、97→99 项 |

验证（最终、单跑）：`repro/run.sh` **35/35**；`run_all.sh` **99 项、失败 0**；字节复现通过。

**关于并发踩踏（第二次观测，已定位）**：本批中途我同时跑了两份 `run_all.sh`，两份都出现 8 项 `INIT-FAILED`（cp3/cp4_a8/cp5_b12/r1r2/r35/r67/r68/r69），而单独清 `/tmp/wf-fixtures` 后单跑 99/0。原因确认：`run_all.sh` 的 `prepare_release_repo` 会 `rm -rf` 再 `cp -a` 共享发行仓库，并在串行阶段共享宿主 `/tmp`；两个实例并发时互相拆台。第四十批登记的那次「4 项 INIT-FAILED 未定位」应属同一原因——**这不是产品缺陷，但跑测试时必须保证单实例**。已在 `repro/README` 与本记录留痕；建议后续给 `run_all.sh` 加一把运行期互斥锁（未做，登记）。

---

# 第五十一批（2026-11-06，688 升档 + 668/673 两条残余缺口关闭；首批产品代码改动）

| 项 | 处置 |
|---|---|
| **688（升「已断言」）** | 新增 `repro/stale-writer-facts.py`：写权记录仍 `held`、而 `.wf-lock` 的持锁者 pid 不存在时，收工与写入口都 `WF_WRITER_BUSY`、`facts.reason == "held by another session"`、出口指向交接/恢复；**不自动接管**（设计稿 §8.2 明列「PID 消失即当空闲」为禁止行为）。注入 = 不再核他人持有 → 收工变 `WF_OK`，判红 |
| **668 残余缺口关闭（产品改动①）** | `wf.py::executor_ready` 增加 `python_version` 比对：解释器版本变了而 size/mtime 未变（打包镜像、保留元数据）时，旧确认失效 → `WF_EXECUTOR_UNCONFIRMED`。用例 `repro/executor-version-change.py`（注入=去掉版本比对） |
| **673 残余缺口关闭（产品改动②）** | `wf.py::project_key_approved` 的候选集扩为「基线 + 活动任务已批准 PRD + `.wf/tasks/archive/**` 已批准 PRD」（摘要须仍等于批准摘要）。用例 `repro/project-key-archived-evidence.py`（注入=把 archive 指向不存在的目录） |
| 文档 | 实现稿 §2.3.11 ③ 的两条由「未比对/只扫活动区」改为「已关闭」，并写明仍未做的部分（语义级键值解析留第二轮） |
| 分母 | **N 113、x 45，x/N = 39.8%** |
| 计数 | §95：35→38 条 repro、99→102 项 |

验证（单跑、清 `/tmp/wf-fixtures` 后）：`repro/run.sh` **38/38**；`run_all.sh` **102 项、失败 0**；`build-wf-release.py --verify` 字节复现通过；`validate-wf-design.py` 与三稿 `check-doc-refs` 通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `cf9a0d9e`(951)。未提交、未收尾。

过程自伤 3 次：①688 首版把「repair 预览应报告持有者已停止」也写成断言——实测 repair 预览不输出该事实（不违规，规格只要求阻断+出口），删掉该断言并把它记为低优先观察；②同一用例先按 `verify_holder(root)` 的真值注入，实际返回 `(alive, facts)` 二元组，改为取 `[0]`；③`project-key-archived-evidence` 的合成归档记录起初 `object_digest` 是假值，`_task_prd_is_approved` 按「摘要须等于当前 PRD」判否，改为先算 PRD 摘要再写记录。

---

# 第五十二批（2026-11-06，654 受控修复升档 + 令牌闸门口径不一致登记）

| 项 | 处置 |
|---|---|
| **654（升「已断言」）** | 新增 `repro/repair-controlled-apply.py`：旧写者**仍存活**时 `repair --apply` 必须被拒（`WF_WRITER_BUSY`）且**零写入**——人工确认不能替代存活事实；旧写者停止后应用成功，留下**代次 +1** 与**维护回执**。注入 = 去掉存活判定（人工确认替代存活事实）→ 存活时也应用，判红 |
| 新登记（待裁，未改行为） | `repair` / `uninstall` 的 `--apply` 令牌闸门**没有 TTY 校验**，且 `--nonce` 由调用方自定令牌（`repair.py:380`、`uninstall.py:405` 把它传给 `Token.issue`），脚本可完整走完预览→应用；而 `wf.py::cmd_confirm_executor` 明确拒绝管道/代填。设计稿 §1.5 声明不防伪、机制稿 §10.3 是过程约束，所以不是安全边界破损，但**同一发行里四个入口口径不一**，须人裁：统一加 `isatty`，还是把 §10.3 收窄为过程约束并在此登记 |
| 分母 | **N 113、x 46，x/N = 40.7%** |
| 计数 | §95：38→39 条 repro、102→103 项 |

验证（清 `/tmp/wf-fixtures` 后单跑）：`repro/run.sh` **39/39**；`run_all.sh` **103 项、失败 0**；`build-wf-release.py --verify` 字节复现通过；`validate-wf-design.py` 与三稿 `check-doc-refs` 通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `fb64c92f`(953)。未提交、未收尾。

**未做并说明原因**：`692 审查不可用` 未开工。它的义务是「复杂任务的审查链路不可用时：留痕 + 不得正常归档」，要驱动它得先建**复杂任务 + review-launch 两个槽位 + 报告导入**；`review-launch` 需要可用的 reviewer CLI 槽位，单测夹具里只能用伪 CLI 名，等于把「不可用」这一前置证成/证伪都揉进同一个夹具，容易变成自证。计划：先写一个 `_review_flow` 级别的 launch 夹具（伪槽位 + 报告占位），让 `review-decide --unavailable` 的留痕与归档阻断各成一条断言，再动手。

过程自伤 2 次：①654 首版把「令牌错必须拒绝」当断言——实测 `--nonce` 是**跨进程携带预览令牌**的机制（`Token.issue(preview, nonce=args.nonce)`），因此任何 nonce 都能走通，这个断言本身是错的；顺带查出上面的 TTY 口径问题。②第二次把 `.wf-lock` 的 `start=0` 当作「存活」，`_live_holder` 按「start 不符＝pid 复用」判否；改用 `/proc/self/stat` 第 22 列的真实启动时刻后才成立。

---

# 第五十三批（2026-11-06，剩余 67 行施工分类：A/B/C/DEFER）

只读分析，不改代码、不改分母。产出 `remaining-classification.md`。

| 类 | 行数 | 含义 |
|---|---|---|
| **A 补断言即可** | 19 | 行为已成立，缺的是可证伪用例（630、632、637、648、660、666、692 等） |
| **B 必须先改实现** | 16 | 对应实现稿 §2.3.11 已登记缺口（651 启动子集、619 卸载写者、631 enable 停用分支、622 就绪视图、669 复杂度核对、672 AI 载体、675 repair 重建、652 发行身份、644/639 spec 索引…） |
| **C 人判／人跑／依赖环境** | 19 | charter 层判断 10 行（586–595、682–685）、真实压缩 612、dogfood 656、外发审计 659、读取范围 665、等效替换 655、待裁 684 |
| **DEFER 建议改判** | 13 | 需第二个任务的格（629.s2.c2/c3/c9、635、640）+ 损坏面下守卫先行、消费点无可观察义务的格（629.s3/s4 的 c2/c3/c7）+ 空面下无可判对象的 629.s2.c5/c10 |

结论与建议：
1. A 类先做门禁相关且有现成证据的 6 条：630、632、637、648、660、692。
2. B 类按「改一处关多行」排序：651（牵 I:466/473）→ 619 → 631。
3. C 类统一挂 `pending-decisions.md`，与 dogfood 一并等人。
4. DEFER 若要落盘，需人确认：N 会从 113 降到 100、x 仍 46（比例 46.0%）。**这是口径修正，不是进度**，必须与「移出理由」一并登记；未确认前不动分母。

未提交、未收尾。

---

# 第五十四批（2026-11-06，DEFER 落盘 + C 类挂队 + A 类首条 660）

| 项 | 处置 |
|---|---|
| **DEFER 落盘（13 行）** | `629.s2.c2/c3/c9`、`635`、`640` → 「等第二轮（多任务未交付）」；`629.s2.c5/c10` 与 `629.s3/s4` 的 `c2/c3/c7` → 「不适用」（守卫先行，消费点无可观察义务）。**N 113→100、x 46 不变**——口径修正，非进度，已在 `denominator.md` 单列一节说明 |
| **C 类 19 行挂队** | 写入 `pending-decisions.md` 新增 §7：charter 层判断 10 行、612 真实压缩、655 等效替换、656 dogfood、659/665 审查审计、684 待裁等，逐行给「为什么断言替代不了 + 需要你做什么」 |
| **A 类首条：660（升「已断言」）** | 新增 `repro/reason-code-table.py`：35 枚码逐枚核档位/出口/禁止修复；注入 = 把 `WF_OK` 的档位改成非法值 `"ok"` → 判红 |
| 分母 | **N 100、x 47，x/N = 47.0%** |
| 计数 | §95：39→40 条 repro、103→104 项 |

验证（清 `/tmp/wf-fixtures` 后单跑）：`repro/run.sh` **40/40**；`run_all.sh` **104 项、失败 0**。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `fb64c92f`(953)。未提交、未收尾。

**未完成并说明**：A 类原计划 6 条（630/632/637/648/660/692），本批只交付 660。
- `648 Python 执行器`：写了一半的用例（`executor-resolution-priority`）在注入下不变红——因为 `resolve_candidate(root, scope=None)` 会先把 scope 归一成 `project/global/system`，我注入的「项目→全局」顺序分支**不在默认路径上**；已删除该半成品，避免留下无效断言。下一版应按「项目键存在但不可用」这个真实分支入手。
- `630/632/637`：都需要 F2 三夹具（共存/外部提交/异常归档）的完整链，属夹具工程，不宜与断言混批。
- `692`：仍需先搭 launch 夹具（伪槽位+占位报告）。

---

# 第五十五批（2026-11-06，A 类：632 外部变更边界；决策队列加导航）

| 项 | 处置 |
|---|---|
| **632 紧急变更边界（升「已断言」）** | 新增 `repro/external-change-boundary.py`：①**面外**外部提交（`docs/x.md`）只记事实、Check 通过；②**面内**外部提交（改了 `pkg/a.py`）→ `WF_SEMANTIC_DECISION`，不得静默放行；③补一条 `choice=checked`、subject 含该提交 OID 的人判后放行。注入 = 「是否触及批准面」判成恒假 → 面内被静默放行，判红 |
| 决策队列 | `pending-decisions.md` 顶部加**导航**：二级标题历史重号，按标题文字定位（并列出十个标题），不重编号以免破坏既有 § 引用 |
| 分母 | **N 100、x 48，x/N = 48.0%** |
| 计数 | §95：40→41 条 repro、104→105 项 |

验证（清 `/tmp/wf-fixtures` 后单跑）：`repro/run.sh` **41/41**；`run_all.sh` **105 项、失败 0**；`build-wf-release.py --verify` 字节复现通过。
绑定未变（本批未改三稿）：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `fb64c92f`(953)。未提交、未收尾。

**本批只完成 1 行，原因逐条记**：
- `630 共存与重装`：核心是「无关外部提交不阻断 + 相关路径变化使旧检查失效 + 重装保留数据」。前两项已被 632 的①②覆盖，第三项要驱动 `install.py`/`add_platforms` 的重装链（`H.install_fixture` 级），属夹具工程，未与断言混批。
- `637 异常归档边界`：实测 `task-abandon` 缺 `--disposition` 时返回 `WF_SEMANTIC_DECISION` 且**零写入**（预览只读），受理据是 `need: ["--disposition 覆盖 preview.uncommitted 的每一项"]`；要断言「补齐后异常归档成立且 terminal 不是 normal」，需先按 `preview.uncommitted` 造 disposition 覆盖项，属下一批。
- `648 Python 执行器`：上一批记录的注入失效原因已查明——`resolve_candidate` 会先把 `scope` 归一，默认路径不走我注入的顺序分支；正确入口是「项目键存在但不可用」分支。
- `692 审查不可用`：仍需 launch 夹具。

---

# 第五十六批（2026-11-06，A 类：648 执行器解析 + 637 异常归档边界）

| 行 | 用例 | 断言 |
|---|---|---|
| **648（升「已断言」）** | `repro/executor-project-key-unusable.py` | 项目键指向不存在的解释器时：`resolve_candidate` 仍返回 **project 作用域 + 该键值**，`wf.py status` 返 `WF_EXECUTOR_UNCONFIRMED`，且报错对象就是配置的项目键。注入 =「不可用即降级到全局」→ 解析变 global，判红 |
| **637（升「已断言」）** | `repro/abandon-boundary.py` | ①无 `--disposition` 只回预览、**记录零写入**；②去向缺项 → `WF_WORKSPACE_UNRESOLVED` 且 `uncovered == ["pkg/a.py"]`；③覆盖 + 提交授权后成立，`terminal == "abnormal"`（不得记为正常完成）。注入 = 不核去向覆盖，判红 |

分母：**N 100、x 50，x/N = 50.0%**。计数：§95 的 repro 41→43、全量 105→107。
验证：`repro/run.sh` **43/43**；`run_all.sh` **107 项、失败 0**。未提交、未收尾。

**本批未完成并说明**：
- `630 共存与重装`：写了两版都失败，**已删除不留半成品**。原因有二：①`install.py` 不在项目内，注入点天然在**发行源**；而 `--release-ref` 需要带 tag 的发行仓库，注入得先复制整份发行仓库（含 `.git` 与 tag）到临时目录，属夹具成本，不是断言问题；②首版把快照取在 `stop` 之前，导致「空闲重装改动了任务记录」是**我的夹具误判**，不是实现问题。
- `692 审查不可用`：仍需 launch 夹具（伪槽位 + 占位报告）。本轮把预算放在 648/637 两条可完整闭环的用例上，没有硬凑。

---

# 第五十七批（2026-11-06，发行源副本夹具 `_release.py` + 630 升档）

| 项 | 处置 |
|---|---|
| **夹具 `_release.py`（新）** | 把 `docs/workflows/wf-release/` 复制到临时目录并初始化为**带同样 tag** 的仓库，供需要「注入安装器」的用例使用；`patch_asset()` 改文件后**同步清单摘要并重算 `rules_digest`**（安装器会核「声明 vs 重算」，只改文件不改清单会被当场拒绝——这是本批踩到的第一个坑） |
| **630 共存与重装（升「已断言」）** | `repro/reinstall-preserves-data.py`：①写权被会话持有时重装**必须被拒**且任务记录逐字节不变；②收工释放写权后重装**幂等**（输出「无任何变化」）且任务记录逐字节保留。注入 = 写者持有时也允许重装 → 判红 |
| 分母 | **N 100、x 51，x/N = 51.0%** |
| 计数 | §95：43→44 条 repro、107→108 项 |

验证：`repro/run.sh` **44/44**；`run_all.sh` **108 项、失败 0**。绑定未变。未提交、未收尾。

**692 未开工，但把前置查清了（下一批可直接施工）**：`review.launch` 要求——`implementation_clis` 非空；`slots` 每项含 `slot` 与 `reviewer_cli`，且 reviewer 不得与实施 CLI 相同；必须带 `export_decision`；`submitted_scope` 必须同时含 diff / requirement / test_results 三类材料；**且任务当前 Check 必须 `pass`**，锚点取锁内重读后的任务。因此 692 的夹具链是：先跑一次完整 Check → 造 launch 请求（双伪槽位）→ `review-decide --unavailable` 留痕 → 再断言复杂任务 `archive` 被阻断。这条链比 648/637 长一倍，本轮预算已用在 `_release.py` 与 630 上。

---

# 第五十八批（2026-11-06，651 启动校验扩交付：③⑧⑨ 落地，两条显式不在启动面）

**产品改动**（`tasks.py::startup_check`）：按机制稿 §5.2 的固定顺序，启动校验从「四步」扩到「七步」：

| 步 | 内容 | 状态 |
|---|---|---|
| ① binding | 绑定与写者 | 原有 |
| ⑤ record | 记录可解释性 | 原有 |
| **③ candidates（新）** | 执行候选唯一性；多候选 → `WF_RECORD_INVALID`（记录集不变量，不是写权占用）；活动记录不可读 → 「未知优先」`WF_HISTORY_UNRESOLVED` |
| ⑦ graph | 对象与依赖 | 原有 |
| **⑧ marker（新）** | 持有/恢复态核 `.wf-lock` 的 `wf-lock-v1` 标记行；缺失/未知 → `WF_HISTORY_UNRESOLVED` |
| **⑨ assets（新）** | 必需资产（`.wf/bin/{wf,repair,uninstall}.py`、`.wf/lib/wflib/module_main.py`）缺失 → `WF_CAPABILITY_UNAVAILABLE` 并点名 |
| ⑩ workspace | 工作区边界 | 原有 |

另新增 `STARTUP_OUT_OF_SCOPE` 常量，把 **④ 维护写者与预览范围对应**（只有维护入口有预览上下文）与 **⑥ 未结束实例**（第二轮）**显式列为不在启动面**——不再靠文档口头解释「四步 ok ≠ 完整校验」。

| 项 | 处置 |
|---|---|
| **651 固定流转程序化（升「已断言」）** | `repro/startup-checks-anchor-assets.py`：启动校验必须含 candidates/marker/assets 三步；标记行改成未知内容 → `WF_HISTORY_UNRESOLVED`；删 `.wf/bin/repair.py` → `WF_CAPABILITY_UNAVAILABLE` 且点名该资产。注入 = 资产缺失也报 ok → 判红 |
| 文档 | 实现稿 §2.3.11 的「四步子集」条目改写为「覆盖七步 + 两项显式不在启动面」，原条目关闭 |
| 分母 | **N 100、x 52，x/N = 52.0%** |
| 计数 | §95：44→45 条 repro、108→109 项 |

验证：`repro/run.sh` **45/45**；`run_all.sh` **109 项、失败 0**；三稿 `check-doc-refs` 0 problem、`validate-wf-design` 通过、字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `9c7b4d40`(953)。未提交、未收尾。

过程自伤 1 次：首版 `status` 探针用空 stdin（`{}`）调用，`startup` 根本不出现（该分支需要会话信封），误判为「新步骤没生效」；改用 `H.cli` 带信封后正常。

---

# 第五十九批（2026-11-06，631 enable 停用分支接通；619 未做并说明原因）

**产品改动**（`cli.py::cmd_enable`）：新增输入 `trellis_disabled_confirmed`——
- 未声明：仍是 `WF_SEMANTIC_DECISION`（不擅自放行，行为不变）；
- 人显式声明：放行，并把 `trellis_files_present_but_disabled_confirmed` 写入 `warnings`、`facts.trellis_disabled_confirmed=true` 留痕。
这样设计稿 §3 的「已停用」分支从「只能物理删文件」变成可达且有留痕。

| 项 | 处置 |
|---|---|
| **631 Trellis 互斥（升「已断言」）** | `repro/enable-disabled-branch.py`：默认拒绝 → 声明后放行 + 留痕；注入 = 停用分支不可达（声明后仍拒）→ 判红 |
| 文档 | 实现稿 §2.3.11 的「enable 停用分支不可达」条目改为已接通，并写明仍未做的一项：`trellis_loaded` 与 `disabled_confirmed` 同时给出时的优先级（当前按冲突处理） |
| 分母 | **N 100、x 53，x/N = 53.0%** |
| 计数 | §95：45→46 条 repro、109→110 项 |

验证：`repro/run.sh` **46/46**；`run_all.sh` **110 项、失败 0**；字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `6a19a151`(1145)、implementation `e618f1b4`(953)。未提交、未收尾。

**619 卸载不登记维护写者：未做，原因是契约问题不是代码问题。** 卸载要「登记维护持有 + 递增代次 + 维护回执」，
但回执一旦写进 `writer.maintenance_results`，就会参与 `receipt_state` 派生：无 disposition → `applied_pending_commit`（会挡住后续任务）、
`disposition.kind=reverse` → 被删资产已不存在、事实核不过 → `pending_check`（同样挡住）。
也就是说：**回执的「处置形态」必须先定义**（例如卸载回执一律记 `disposed` 且以「资产已不存在」为可核事实，或引入专门的 `kind=uninstall`），
否则仓促实现会给每个目标项目留下一条永久待核回执——比不登记更糟。这属设计稿 §4.5/§10.5 的口径问题，需要先定再改，未擅自实施。

---

# 第六十批（2026-11-06，人裁：C 类以人判为验收出口）

| 项 | 处置 |
|---|---|
| 分母口径 | 19 行（586–595、612、655、656、659、665、682–685）标 `mode=human`、覆盖判定「人判（待体检）」；**仍留在首轮分母**，不计入断言分子 |
| 门禁① 判据拆分 | ①断言口径 81 行全绿（当前 53/81 = 65.4%）②人判口径 19 行逐行有登记（当前 0/19）。两段都满足才算「三夹具适用项达到预期」——100% 从此可达，且不靠挪分母 |
| 记录 | `pending-decisions.md` §8 记裁定与「需要逐行给结论的 19 行 + 交付形式」；`validation` 与 `denominator.md` 同步 |
| 619 | 未动手：先把「卸载回执的处置形态」讲清楚交人裁，再改代码（理由见回答） |

未提交、未收尾。

---

# 第六十一批（2026-11-06，人裁 B：卸载登记维护写者 + `disposition.kind=uninstall`）

**先说清删除语义（人已确认保持现状）**：默认卸载**真删**「发行清单登记的框架资产」（`uninstall.py:495/502` 的 `os.remove`），
**保留**项目数据（`.wf/tasks`、`.wf/install`、`writer.json`、`.wf-lock`）与本地偏离；`--purge` 仍是第三轮的桩（`uninstall.py:320-323`），当前不会删任何数据。

**产品改动**
| 处 | 改动 |
|---|---|
| `writer.py` | `DISPOSED_KINDS` 增加 `uninstall` |
| `tasks.py::maintenance_disposition_probe` | 新增 `uninstall` 分支：登记的每个路径当前**都不存在**即成立（不依赖 Git 提交） |
| `uninstall.py --apply` | 先取维护持有（`state=held`、`holder.kind=maintenance`、代次 +1）→ 删资产/托管段 → 释放为 `idle`（代次再 +1、holder 清空）→ 追加回执：`operation=uninstall`、`changes` **只列真被删的路径**、`disposition.kind=uninstall`、`evidence={removed, assets_absent}` |
| 机制稿 §4.5 | 增补「处置类型与各自核验事实」：commit/reverse/transfer/uninstall 四类，字段齐但事实核不过一律 `pending_check` |
| 实现稿 §2.3.11 | 「卸载不登记维护写者」条目改为已交付，并写明**为什么不用 commit/reverse**（会落 `pending_check` 挡住后续任务） |

| 项 | 结果 |
|---|---|
| **619 维护写者（升「已断言」）** | `repro/uninstall-records-maintenance.py`：卸载后 `state=idle`、`holder=None`、代次 +2、回执派生 `disposed`。注入 = 把 `kind` 写成 `commit` → 回执落 `applied_pending_commit`，判红 |
| 分母 | **x = 54**；断言口径分母 81 行内 **54/81 = 66.7%**（总分母 100 含 19 行人判） |
| 计数 | §95：46→47 条 repro、110→111 项 |

验证：`repro/run.sh` **47/47**；`run_all.sh` **111 项、失败 0**；字节复现通过；三稿 `check-doc-refs` 0 problem、`validate-wf-design` 通过。
绑定：design `d5d25d4f`(721)、mechanism `cc9e89fa`、implementation `6c43c631`。未提交、未收尾。

过程自伤 2 次：①回执 `changes` 字段一开始把 `before/after` 写反，靠打印实测纠正；②用例里 `from wflib import tasks` 被**项目内 lib 的缓存**抢走（卸载已删掉那些文件），改用「清 `sys.modules` + 暂存 payload 路径」才导入成功。

---

# 第六十二批（2026-11-06，审查链路夹具 `_review_launch.py` + 692 升档）

| 项 | 处置 |
|---|---|
| **新夹具 `_review_launch.py`** | 封装 `review.launch` 的全部前置（`implementation_clis`、双槽位且异于实施 CLI、`export_decision`、`submitted_scope` 三类材料、**任务 Check 必须 pass**）。踩到一条：复杂任务的 `design.md`/`implement.md` 空 body 会被 `WF_TEMPLATE_INCOMPLETE` 拦（`empty body`），夹具必须写实质正文 |
| **692 审查不可用（升「已断言」）** | `repro/review-unavailable.py`：①`--unavailable` 无 `evidence` → `WF_SEMANTIC_DECISION`；②带证据 → `WF_REVIEW_UNAVAILABLE`，且 `reviews.result.verdict` 与尝试级 `outcome` 均为 `unavailable`（留痕，不是 pass）；③复杂任务随后 `archive` 被拒、`status` 未变。注入 = 把不可用当 pass → 三处断言同时红 |
| 分母 | **x 55/81 = 67.9%**（总分母 100 含 19 行人判） |
| 计数 | §95：47→48 条 repro、111→112 项 |

验证：`repro/run.sh` **48/48**；`run_all.sh` **112 项、失败 0**。未提交、未收尾。

过程自伤 2 次：①复杂任务批准时 `design.md`/`implement.md` 只写标题，被 `empty body` 拦下；补实质正文后通过。②断言 `reviews.history` 字段并不存在——实现写的是 `reviews.result.verdict` 与 `attempts[].outcome`，按实际结构改写断言（这也说明"照文档猜字段"必错）。

---

# 第六十三批（2026-11-06，666 报告写权升档）

| 项 | 处置 |
|---|---|
| **666 审查报告写权（升「已断言」）** | `repro/review-report-boundary.py`：①`review-launch` 给出的暂存目录**必须在项目树之外**；②报告从该槽位暂存目录导入成功；③导入期间**写权不转移**（state/holder 不变）。注入 = 把暂存根改到 `.wf/review`（写进项目树）→ 判红 |
| 分母 | **x 56/81 = 69.1%**（总分母 100 含 19 行人判） |
| 计数 | §95：48→49 条 repro、112→113 项 |

验证：`repro/run.sh` **49/49**；`run_all.sh` **113 项、失败 0**。未提交、未收尾。

过程自伤 3 次（都是"照文档猜字段"）：①报告缺 `check-anchor/read-scope/excluded-scope/scope-exceptions/axes` 五字段被拒；②`protocol` 值写成 `wf-review-report:v1`，实际常量是 `wf-review-v1`；③注入里用 `root` 但 `staging_root(ctx, …)` 只有 `ctx`，抛出 `internal error: name 'root' is not defined`（被 rc=70 暴露）。三次都靠实跑输出纠正，没有一次是靠读文档猜对的。

---

# 第六十四批（2026-11-06，622 就绪视图交付：新增只读子命令 `ready`）

**产品改动**：`cli.py` 新增只读子命令 `ready`
- 列出活动/暂停任务的 `id/title/status/phase/created_at/eligible/ready/blockers`，按 `created_at` 排序；
- `suggested` = ready 中创建时间最早的一个（设计稿 §5.6 的「最早就绪建议」）；
- 就绪判定 = 独立接续资格通过 ∧ 已批准 ∧ **非「进行中未暂停」** ∧ **写权未被其他会话持有**；
- 命令**只读**：不写任何判定字段（用例逐字节比对任务记录）。

| 项 | 处置 |
|---|---|
| **622 绑定历史按需读取/就绪视图（升「已断言」）** | `repro/ready-view.py`：已批准未开工 → `ready:true` 且被建议、记录逐字节不变；开工后（进行中未暂停）→ 不再 ready、不再被建议。注入 = 忽略全部阻断项 → 后者失真，判红 |
| 文档 | 实现稿 §2.3.11「无就绪视图/建议」条目改为已交付，并写明仍未做的（不按实例归组、无耗时类建议）；V1 场景措辞恢复为「先看 `ready` 再 `bind --task`」 |
| 分母 | **x 57/81 = 70.4%**（总分母 100 含 19 行人判） |
| 计数 | §95：49→50 条 repro、113→114 项 |

验证：`repro/run.sh` **50/50**；`run_all.sh` **114 项、失败 0**；`check-doc-refs` 0 problem。
绑定：design `d5d25d4f`(721)、mechanism `cc9e89fa`、implementation `12f74710`。未提交、未收尾。

过程自伤 1 次：就绪判定首版没考虑「进行中未暂停」与「写权被他人持有」，导致**刚开工的任务仍被判 ready 并被建议**——断言自己抓出来的（green 阶段失败），补上两条阻断项后通过。

---

# 第六十五批（2026-11-06，652 发行身份：改为按 tag 提交树核内容）

**产品改动**：`install.py::verify_assets(source, manifest, commit=None)`
- 给出 `commit` 时**按该提交的树取字节**（`git show <commit>:<path>`）核摘要；工作树仅作 `source_dirty` 事实；
- `--strict-source` 保留（要求子树干净），作者链路仍可跑；
- 「同版异内容」从此相对**提交**成立，脏检出无法冒充同一发行。

**连带夹具修复（重要）**：本改动改变了一个前提——发行源必须是「包含这些路径的**仓库根**」。
1. `_harness.deploy` 改为先把发行树复制成**自带 tag 的独立仓库**再安装（新增 `release_source()`）；否则用仓库内子目录的当前工作树当源，会因提交树里没有这些路径而全线失败（本轮一度 39 项红）。
2. `_release.patch_asset` 在改文件+同步清单后**提交并移动 tag**；否则「工作树改了、提交没改」会先被发行身份校验挡住，测不到目标行为。

| 项 | 结果 |
|---|---|
| **652 发行身份（升「已断言」）** | `repro/release-identity-commit.py`：篡改工作树资产并把清单摘要同步成自洽 → 仍必须 `WF_RELEASE_CONFLICT`（证明按提交核内容）；注入=退回工作树核摘要 → 放行，判红 |
| 文档 | 实现稿 §2.3.11 该条改为已交付，并写明仍未做的（清单签名/来源证明、逐资产 `git show` 的性能） |
| 分母 | **x 58/81 = 71.6%**（总分母 100 含 19 行人判） |
| 计数 | §95：50→51 条 repro、114→115 项 |

验证：`repro/run.sh` **51/51**；`run_all.sh` **115 项、失败 0**；字节复现通过；三稿引用检查 0 problem。
绑定：design `d5d25d4f`(721)、mechanism `cc9e89fa`、implementation（见下批记录行）。未提交、未收尾。

过程自伤 1 次（代价大、但值得记）：改完 `verify_assets` 直接跑，**39 项 repro 变红**——原因不是产品错，而是所有用例都拿「仓库内发行子目录的当前工作树」当源；提交树里没有这些路径 → 全判缺失。修法是让夹具造自带 tag 的独立发行仓库，这也更接近真实投放方式。

---

# 第六十六批（2026-11-06，按实测证据重排后的三处处置：627 升档、670 改判、614 降档）

| 行 | 处置 | 依据 |
|---|---|---|
| **627 Git 就绪（升「已断言」）** | `repro/git-readiness-no-head.py`：删掉 HEAD 后 `task-start` 必须 `WF_CAPABILITY_UNAVAILABLE`；注入=无 HEAD 也放行 → 返回 `WF_WORKSPACE_UNRESOLVED`，判红 | 正例已由 `p5_f0` 覆盖，缺的就是负例 |
| **670 锁删除与人工清理（改判「等第三轮」）** | 从首轮分母移出（N 100→99） | 证据原文即「完整 uninstall/**purge** 后续」，而 `purge` 是第三轮桩（`uninstall.py:320`）；继续放首轮只会每轮被当成"待补" |
| **614 单工作区串行写入（降回「仅有原因码」）** | 不加用例，并在 denominator 写明卡点 | 实测：另一会话先报 `WF_BINDING_MISMATCH`（未绑定），要隔离出「他人持有写权」得先让 B 会话**持有绑定但不持写权**——当前命令面没有这种形态，硬写只能造出自证夹具。已删除写了一半的 `single-writer-serial.py` |

分母：**x 59；断言口径 59/80 = 73.8%**（总分母 99，含 19 行人判）。计数：§95 的 repro 51→52、全量 115→116。
验证：`repro/run.sh` **52/52**；`run_all.sh` **116 项、失败 0**。未提交、未收尾。

过程自伤 1 次：重写 `git-readiness-no-head.py` 的注入常量时，用正则替换把 `\n` 写成了真实换行，文件两度 `SyntaxError`；改为整段重写文件头（用 `chr(92)+"n"` 构造转义）才修好。教训：**在生成器里改生成器的转义，等于自己给自己下绊子**——这类改动应该直接重写整段，而不是正则打补丁。

---

# 第六十七批（2026-11-06，A 类扫尾：662 审查副本 + 687 分支来源）

| 行 | 用例 | 断言 |
|---|---|---|
| **662 审查适配副本（升「已断言」）** | `repro/review-copies-installed.py` | 两份副本（`wf-review`/`wf-review-action`）随发行投放、进 `installation.assets`、卸载后随资产移除。注入=造一个「清单与树都不含副本」的发行（未交付），判红 |
| **687 分支来源未确认（升「已断言」）** | `repro/branch-source-preview.py` | 目标资产当前分支缺失、`feature` 分支存在时：预览报 `WF_ASSET_DECISION`、**点名 feature 分支**、且 `.wf` **零写入**。注入=跳过分支来源核对 → 继续投放并写入，判红 |

分母：**x 61；断言口径 61/80 = 76.2%**（总分母 99，含 19 行人判）。计数：§95 的 repro 52→54、全量 116→118。
验证：`repro/run.sh` **54/54**；`run_all.sh` **118 项、失败 0**。未提交、未收尾。

过程自伤 2 次：①662 首版注入是「跳过写副本」，结果被安装器**自检**（digest mismatch after deploy）当场拦住——说明这条防线本来就在；改为「清单与树同时不含副本」才测到目标；②687 注入锚点猜成 `findings = …`，实际是 `branch_findings = branch_source_findings(args.target, project_paths)`，靠 `repro stale` 报错纠正。

---

# 第六十八批（2026-11-06，616 stop 只读预览交付 + 待决策清单成文）

| 项 | 处置 |
|---|---|
| **616 日常收工（升「已断言」）** | 产品改动：`stop --decision <f> --preview` 增加**只读预览**分支——返回 `facts.buckets`（逐路径归属）、`facts.uncommitted`、「预览只读；本次未写入任何记录」，**不写任何记录**；去掉 `--preview` 才执行。用例 `repro/stop-preview-readonly.py`（注入=预览落到执行分支 → 任务记录与写权记录被改写，判红） |
| **639/644 未做，改列决策** | 查证：两份 checklist 模板是**静态通用条目，没有 per-spec 指针区**——"三段同步"缺的是承载结构，不是同步代码。凭空造指针格式等于发明契约，已写入 `open-decisions.md` §3（三个选项） |
| **待决策清单** | 新增 `open-decisions.md`：C 类 19 行人判、669+672 契约、639/644 指针区、614 形态取舍、dogfood、编号重整，每项带选项与代价 |
| 文档 | 实现稿 §2.3.11「stop 没有预览分支」条目改为已交付，并写明仍未做的（不预估提交后残留、不覆盖 task-abandon） |
| 分母 | **x 62；断言口径 62/80 = 77.5%**（总分母 99，含 19 行人判） |
| 计数 | §95：54→55 条 repro、118→119 项 |

验证：`repro/run.sh` **55/55**；`run_all.sh` **119 项、失败 0**；三稿引用检查 0 problem。
未提交、未收尾。

---

# 第六十九批（2026-11-06，639/644 spec 三段索引交付；614 按人裁锁定覆盖）

**产品改动**（`spec.py` + 模板）
- 两份 checklist 模板新增固定段 `## spec 指针`（含维护说明），解决"没有承载结构"这个更根本的问题；
- 新增 `_sync_checklists` / `_sync_all`：`spec-update` 的 add/rename/delete **同批**更新 `index.md` 与两份 checklist；改名同时重写标签与路径，删除移除该行；
- 旧的 6 处 `_sync_index(...)` 调用统一改为 `_sync_all(...)`（三段同步的唯一入口）。

| 项 | 结果 |
|---|---|
| **639 spec 正向积累 + 644 无 MCP 全流程（升「已断言」）** | `repro/spec-three-part-index.py`：add/rename/delete 后逐段断言；注入=只同步索引表 → 两份 checklist 缺条目、旧条目残留，判红 |
| **614（人裁方案 A：锁定覆盖）** | 登记为「他人持有时 `bind` 被 `WF_WRITER_BUSY` 拒绝 + 只读视图放行」；「已绑定但无写权」的会话形态**不存在**，不再追 |
| 文档 | 实现稿 §2.3.11 两条（第八轮「只同步一段」、第二十五轮「无承载结构」）同批改为已交付 |
| 分母 | **x 64；断言口径 64/80 = 80.0%**（总分母 99，含 19 行人判） |
| 计数 | §95：55→56 条 repro、119→120 项 |

验证：`repro/run.sh` **56/56**；`run_all.sh` **120 项、失败 0**；三稿引用检查 0 problem、字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `cc9e89fa`、implementation `43ad9164`(953)。未提交、未收尾。

过程自伤 4 次（都在夹具/断言口径上，值得记）：
1. checklist 指针段是我新造的契约边界——先按 `pkg/**` 的 spec 路径写，实际 spec 只接受 `.wf/spec/**`（`WF_SCOPE_UNRESOLVED`）；
2. 任务的批准触碰面必须覆盖 `.wf/spec/**`，否则 `spec-update` 直接判越界；
3. `missing()` 返回 **list** 却与 **tuple** 比较，`list != tuple` 恒真 → 误报"旧条目仍在"；
4. 把索引条目改成 `- [新文件名](新路径)` 后，`r7r15` 的 R9 断言按文件名计数变成 2 → 改为按**路径**计数（这属测试口径修正，不是放水）。

---

# 第七十批（2026-11-07，人裁 A：复杂度②③④事实核对 + 人工载体可扩展）

## 人裁口径（2026-11-07）

- ② 契约面 = `.wf/bin/**`、`.wf/lib/**`、`.wf/templates/**`、`.wf/workflows/**` + `AGENTS.md` 托管块（含 `TRELLIS:START`）；
- ③ 验收口径边界归 ③，但**只收载体**（`.wf/baseline.md`、`.wf/project-config.json`）+ 再次批准时 acceptance id 集合变化；改 spec 正文不算（设计稿说的是「变化」不是「触碰」）；
- ④ 范围扩张：再次批准时触碰面覆盖上一版批准面之外；
- 人工载体：决定文件 `plan` 块承载 `complexity`/`tdd`/`downgrade`，**要求可扩展**。

## 产品改动

| 处 | 改动 |
|---|---|
| `scope.py` | 新增 `contract_surface_condition` / `acceptance_surface_condition` / `expansion_condition`（与①同构，返回 true/false/unknown） |
| `tasks.py::_complexity_proposal` | 四项全部事实核对；取不到证据 → unknown → 仍按复杂（宁高不低） |
| `tasks.py::cmd_task_approve` | 读决定文件 `plan` 块；`HUMAN_PLAN_KEYS` 注册表校验；`inputs` 降为提议；记录 `confirmed_source` / `human_inputs` / `unconfirmed_keys` / `acceptance_ids` |
| `tasks.HUMAN_PLAN_KEYS` | **可扩展点**：新增人判项 = 加一条键+校验；**未登记的键不丢弃**，原样进 `human_inputs` 并列入 `unconfirmed_keys`（这条约束就是可扩展性的保证） |
| `gates.py::final_gate` | 复杂分级必须 `confirmed_source == "decision"`，否则 `WF_SEMANTIC_DECISION` |

| 项 | 结果 |
|---|---|
| **669 复杂度分级一致性（升「已断言」）** | ②命中 `.wf/lib/**` 即按复杂、要求三件套，条件入库 `condition=contract` |
| **672 TDD 开关（升「已断言」）** | `plan.complexity` 确认才记 `confirmed_source=decision`；无理由降级被拒、有理由降级留痕；未登记项 `review_depth` 留痕且不阻断 |
| 分母 | **x 66；断言口径 66/80 = 82.5%**（总分母 99） |
| 计数 | §95：56→57 条 repro、120→121 项 |

## 夹具/环境修复（同一批，必须记）

1. **`run_all.sh` 的发行仓库搬出 `/tmp`**（默认 `$HOME/.cache/wf-release-repo`）：`run_one.sh` 会把 `/tmp` 换成 tmpfs，源仓库随即不可见 → 并行模式全线 INIT-FAILED；
2. **串行模式逐套件重建 `/tmp/wf-fixtures/release-repo` 软链**（含 `run_flow`）：`r67` 会把它指向伪造仓库，污染 `r69/r70/r89/r72`；
3. **`install.py` 的 git 调用统一加 `-c safe.directory=*`**：在 user namespace 里仓库属主与当前 uid 不同，git 会拒绝，导致误判「资产缺失」；
4. **本机并行模式不可用**：`unshare` 里 `mount -t tmpfs /proc/self/fd` 失败、回退挂 `/tmp` 会遮住结果目录。**串行 `WF_JOBS=1` 为权威验证路径**。

验证：`WF_JOBS=1 run_all.sh` **121 项、失败 0**；三稿引用检查 0 problem、`validate-wf-design` 通过；字节复现通过。
绑定：design `d5d25d4f`(721)、mechanism `cc9e89fa`、implementation `e30a5f45`。未提交、未收尾。

过程自伤 3 次：①改 `tasks.py` 时漏掉一行 guard，`unexpected indent` → 全线 INIT-FAILED（`/usr/bin/python3` 直接跑才看到 traceback）；②③两次改测试口径时把 `complexity_conditions` 的旧语义当成新语义，靠跑出来才发现；④误把 spec 正文算作③，导致 `p5_spec` 19 项里 18 项变复杂而失败——这条最终改的是**实现**（口径收窄），不是测试。

---

# 第七十一批（2026-11-07，C 类人判落盘 + 595 三处同批义务补正）

人（用户）给出 19 行中 18 行的结论，并**纠正了我两处**：

| 我原先 | 人裁/更正 | 处理 |
|---|---|---|
| 590 拟「不成立 — 第二轮起两次无新事实复开」 | **成立**：查遍 11-03 的 55 份 review-round 记录、11-05 的 70 个批次、28 次复审，**没有**"无新事实复开"的记录；两次最可能被指为复开的事件各自产出新事实；第 15 次复审外部项明确拒绝重复（execution-log.md:678） | 撤回我的拟判，改记「成立」，并把「结论须能反向定位证据」写进落盘依据 |
| 595「文案字段名错」 | **同批义务未完成**（登记面漏掉新命令形态/新 schema 字段），并给出三处指认 + 一处候选 | 按此表述落盘，并**同批补正** |

## 595 的补正（同一变更内完成）

| # | 缺口 | 位置 | 补正 |
|---|---|---|---|
| 1 | 命令表缺 `ready` | 实现稿 :225–260 | 新增 `ready` 行（只读、设计稿 §5.6 / 机制稿 §6.1） |
| 2 | `stop` 行缺 `--preview` | 实现稿 :234 | 改为 `--decision <path> [--preview]` 并注明只读 |
| 3 | 机制稿 schema 缺新字段 | 机制稿 `Decision` / `plan` 两行 | 补 `Decision.plan` 块与 `plan.confirmed_source/human_inputs/unconfirmed_keys/acceptance_ids` |
| 4 | 机制稿无 checklist 指针段登记 | `spec-update` 操作行 | 补「三段同批同步」 |

## 其余结论落盘

- `pending-decisions.md` §9：19 行逐行结论 + 依据 + 计数（成立 13 / 不成立 1 / 宣告不审 1 / 待 3 / 未给 1）；
- `denominator.md`：`mode=human` 行的覆盖判定改为 `人判（成立/不成立/宣告不审/待补/待裁）`，逐行写依据；
- `validation.md` §95：人判口径计数写入，并写明「595 记未履行、已补正、待下一轮复核，**不计入达成**」。

## 仍需人给的两句

1. **655 用哪档标准**：A charter T4 字面（有最近正反例 → 成立）；B 方案 A 双模可证伪（R93 缺注入反例 → 不成立）。建议 A + 登记 R93 缺口。
2. **665 审查读取范围**：审计，或宣告不审。

验证：三稿 `check-doc-refs` 0 problem、`validate-wf-design` 通过（机制稿 `cd4fa8a7`、实现稿 `50fbd2b7`）。未提交、未收尾。

---

# 第七十二批（2026-11-07，665 审计 + 排除范围覆盖检查）

**审计结论**（人裁：审计，不宣告不审）

| 面 | 结论 |
|---|---|
| 已保证 | `read-scope`/`excluded-scope` 非空、`scope-exceptions` 非空即拒、`source-cli`/锚点核对（`review.py:455/459/462/469`） |
| **发现缺口** | `excluded-scope` **只核非空**：写 `["node_modules/**"]` 即可通过，四类敏感面一个都没覆盖。历史夹具（r68–r71、r75、`_review_flow`）都是这个值 → 不是理论缺口，是当时的实际声明形态 |
| 无法核 | reviewer 实际读了什么（无遥测）；审计只证明「声明被约束」，不证明「没有越界」 |

**产品改动**
- `review.exclusion_gaps()`：要求 `excluded-scope` 覆盖凭据（`.env`/`id_rsa`/`.npmrc`…）、私密配置（`.codex/config.toml`…）、项目外路径（`..`/`/` 开头）、其他任务目录（`.wf/tasks/**`）；
- `decide`：缺任一类 → `WF_REVIEW_INVALID` 并点名缺失类别；
- **拒绝补三档出口**：输入不成立时也返回 `exits`（补齐重导 / 转 `--unavailable` 留痕 / 按异常退出）。这条是被 `review-count-reject` 的 red 反向暴露出来的——原来输入不成立的拒绝不给出口。

| 项 | 结果 |
|---|---|
| **665 审查读取范围（人判：成立）** | `repro/review-excluded-scope-covers.py`：窄排除被判通过即为缺陷（注入=不核覆盖时正好复现），有覆盖才放行 |
| 夹具同步 | r68–r71、r75、`_review_flow`、`review-report-boundary` 的 `excluded-scope` 补齐四类 |
| 计数 | repro 57→58、全量 121→122；人判口径 **成立 15 / 不成立 1 / 宣告不审 1 / 待 2** |
| 分母 | x 仍 66（665 是人判行）；断言口径 66/80 = 82.5% |

验证：`WF_JOBS=1 run_all.sh` **122 项、失败 0**；三稿引用检查 0 problem、`validate-wf-design` 通过。
绑定：mechanism `818d6b4c`、implementation `c64b4e8d`。未提交、未收尾。

过程自伤 2 次：①首版用例把 `source-cli` 写成槽位 id，被"声明 CLI 不符"先拒，red 断言不干净——改为取槽位声明的 CLI；②`review-count-reject` 的 red 因新缺口不再被触发，暴露出"输入不成立拒绝不给出口"的老问题，遂补 `exits` 并同步其夹具。

---

# 第七十三批（2026-11-07，dogfood 可执行步骤成文）

按"全部修正落地后给可执行步骤"的要求，把 `dogfood-plan.md` 的 §3 抽象步骤落成 **§8 可执行步骤（当前版本）**：

- 对齐本轮四处变更：复杂分级须人确认（`decision.plan.complexity`）、新增 `ready`、审查报告 `excluded-scope` 覆盖四类、发行按 tag 提交树核内容；
- 逐条给命令形态（含会话信封示例）、预期输出与**该留什么证据**；
- 补 §8.8「656 闭环四条件的判定表」与 §8.9「已实测到的六个坑」（TTY、plan 块、排除声明、target 存在性、发行仓库形态、脏工作区）；
- 明确边界：`confirm-executor` 与所有令牌必须人执行，模型只做记录与判读辅助。

未提交、未收尾。

---

# 第七十四批（2026-11-07，B1 落地 + B2 后端落地）

人裁（2026-11-07）：review 改为「reviewer 只给 task id + 轮次；报告文件名 `review-<agent>.md` 承载身份；同一 agent 同一轮不得二次审查」；initialize/bootstrap 豁免①③④；其余按默认。

## B1：initialize/bootstrap 豁免机械条件（已完成，123 项绿）

- `_complexity_proposal`：`kind ∈ {initialize, bootstrap}` → ①基线缺失导致的 unknown 记 `bootstrap-not-applicable`、③④ 不参与；**②（契约面）仍参与**；
- 用例 `repro/complexity-bootstrap-exempt.py`：initialize 不判复杂；**同路径 ordinary 仍判复杂**（豁免不外溢）；注入=取消豁免 → 判红。

## B2（后端部分）：审查身份改由文件名承载（已完成，123 项绿）

| 改动 | 说明 |
|---|---|
| 新增 `wf.py review-context --task <id> [--round n]` | reviewer 侧唯一入口：按本会话 `host_id` 归一身份、创建 `review-<agent>.md` 占位（`status=in-progress`）、物化材料（`diff.patch`/`prd.md`/`check.json`/`tests.json`）、回显锚点与报告路径 |
| **不做平台校验** | 审查 CLI（pi/zcode…）不必是项目已安装平台，它只是署名人；写权限仍在主会话（已写入实现注释） |
| 占位即闸门 | 同一 agent 同一轮已有 `in-progress`/`done` → 直接拒，**审查不开始**（满足"阻止后续实际审查操作"） |
| `review-import --task <id>` | `--round/--slot/--report` 全部可省：轮次取最新已发起轮、身份取本会话、路径取 `round-N/review-<agent>.md`；要求 `status=done` |
| `review-decide --task <id>` | `--round` 可省；人数与异种按**导入记录里的 agent token** 判；实施 CLI 取 action 会话 `host_id` 并回写 `reviews.launches[].implementation_cli` |
| 报告字段 | `reviewer-id`/`source-cli` 不再必需；若正文写了且与文件名不一致 → `WF_REVIEW_INVALID`（两个事实源不许打架） |
| 兼容 | 显式 `--report` 的槽位制路径**保持旧语义**（r75 的"声明三槽位只导入两份"仍被拒） |

验证：`WF_JOBS=1 run_all.sh` **123 项、失败 0**；`complexity-bootstrap-exempt.py` 双模绿。

过程自伤 3 次：①生成代码时 `\n` 被 heredoc 吃掉，`review.py` 一度 `unterminated string`；②把"人数"直接改成按导入记录判，**打掉了旧槽位制的"声明了却没导入"检查**（r75 判红），改成"发现模式/槽位模式"双分支；③`/tmp/wf-fixtures/release-repo` 被 r67 换成伪造仓库，导致 r89 在批量跑里失败而单跑通过——已把 r35/r69/r70/r72/r89 改为 `WF_RELEASE_REPO` 环境优先，并在 `run_all.sh` 导出该变量（不再依赖固定 /tmp 路径）。

**仍未做（下一批）**：`review-context --reset`（占位清理出口）、692/666/count-reject 三个 repro 改用新形态、`wf-review`/`wf-review-action` 技能文本、设计稿 §6.5 与机制稿 §9.2 同步。

## B2b：审查链路收口（2026-11-07，124 项绿）

| 项 | 结果 |
|---|---|
| `review-context --reset` | 占位清理出口（审查中途放弃后，人可清掉该 agent 的本轮记录） |
| `review-launch` | `slots`/`implementation_clis` 均可省；不给则默认"要两份审查"；不再要求事先声明审查 CLI |
| `review-import --task` | 扫描本轮目录里所有 `status=done` 的 `review-<agent>.md` 批量导入；**不再用调用方身份定位报告**（导入由持写权主会话执行） |
| `review-decide --task` | 人数与异种按文件名 token；`facts.reviewer_clis` 与 `result.reviewer_clis` 都回显；实施 CLI 取 action 会话身份并回写 |
| 技能 | `wf-review` 输入改为「任务 id + 轮次」，步骤改为 `review-context` → 写报告 → `status=done`；`wf-review-action` 改为 `review-import`/`review-decide` **零参数**（免路径免轮次） |
| 文档 | 设计稿 §6.5 改写为「事后核验」并明确"不宣称更强身份保证"；机制稿 §9.2 补身份/人数规则；实现稿命令表补 `review-context`、放宽 import/decide 参数 |
| 新用例 | `repro/review-filename-identity.py`：只给 task id+轮次 → 占位/材料齐 → 同 agent 二次审查被拒 → 两 agent 判定 pass 且身份取文件名；注入=不拦二次审查 → 判红 |

验证：`WF_JOBS=1 run_all.sh` **124 项 0 失败**；三稿校验通过（机制稿输入摘要已随设计稿更新为 `57d940e7`）；字节复现 OK。

自伤 4 次（都记）：`lock` 局部导入被大段替换吃掉 → `internal error: name 'lock' is not defined`；`distinct` 在 unavailable 分支未定义；discovery 递归把 `discovered` 标志搞混（`slot not declared in launch`）；r75 的"声明三槽位只导入两份"因只按导入记录判人数而失效 → 改为发现/槽位双分支。

## B4：`wf.py help <命令>`（2026-11-07，125 项绿）

- 新增只读命令 `help [<命令>]`：无参列出可查命令；带参返回该命令的**参数表、输入结构、最小示例与常见出口**；
- 覆盖 13 条写命令（task-new/approve/start/check/knowledge、stop、archive、spec-update、baseline-apply、review-launch/context/import/decide）；
- 重点把"人不写就卡住"的字段显式写进示例：`task-approve` 的 `plan{complexity,tdd,downgrade}`、`task-check` 的 `--review-notes` 双轴结构；
- 未知命令 → `WF_PATH_INVALID` 并列出可查命令。
- 用例 `repro/help-covers-write-commands.py`（注入=注册表为空 → 判红）。

**过程自伤 2 次**：①`help` 首次探测跑的是**旧发行副本**（未重建），误判成"命令没注册"；②`Args` 的 `argv` 不含子命令名，我的位置参数解析从 `[1:]` 开始 → 永远走"无参"分支，改为 `[0:]`。

验证：`WF_JOBS=1 run_all.sh` **125 项 0 失败**；三稿校验通过；实现稿命令表已补 `help` 行。

## B5：证据输入命令化（2026-11-07，126 项绿）

针对 dogfood 实测的**19 次直连 `from wflib import …` / 37 次手写 JSON**：

| 改动 | 说明 |
|---|---|
| `baseline-apply --files a,b,c --decision <人批准> [--preview]` | 提案（文件集、前像、内容摘要）由入口从工作树生成；人只看 `proposal_digest` 批准，`object_digest` 绑定提案内容。`--proposal` 保留兼容 |
| `task-knowledge --no-update` | 常用情形不必再写决定文件 |
| `wf.py help <cmd>` | 每条写命令的输入结构与最小示例（B4 已交付，B5 把新参数写进去） |
| 技能纪律（wf-continue / wf-finish / wf-bootstrap） | 新增「证据文件纪律」：可写的只有决定文件、`--review-notes`、`--changes`、基线提案；验证结果、门禁预览、提交清单与摘要**一律由入口生成，不自建** |

用例：`repro/baseline-apply-generated.py`（预览取摘要 → 人批准 → 应用；注入=只认 `--proposal` → 判红）。

验证：`WF_JOBS=1 run_all.sh` **126 项 0 失败**；三稿校验 0 problem；字节复现 OK（55 assets）。

**过程自伤 3 次**：①生成的提案没把 `object_digest` 带进 `approval`，导致 `WF_APPROVAL_MISSING`；②前像取成 HEAD 内容，应用时与工作树不符（`WF_WORKSPACE_UNRESOLVED`）→ 改为取当前工作树内容；③用例任务触碰面是 `pkg/**`，应用 `.wf/**` 直接判越界 → 改成基线范围的触碰面，并发现"内容与现状一致时走 `skipped`"这一语义（已在用例里按 `written ∪ skipped` 断言）。

**语义澄清（重要）**：`--files` 的语义是「工作树里已是目标内容，入口核批准覆盖并登记」；内容未变时记为 `skipped` 而非 `written`。这不是 bug——baseline-apply 的产物本来就是"人批准的基线正文"，正文由任务交付产生，入口负责**批准绑定与登记**。

## B6：任务目录收口（2026-11-07，127 项绿）

调查发现：那次 dogfood 的 52 个文件里，**入口自己只写 1 类**（导入的审查报告）；
其余 40 余个是 agent 自建的"证据/协议"文件（B5 的纪律已在源头禁止）。因此本批做两件事：

1. **规范文件集 + 只读盘点**：新增 `wflib/taskfiles.py`，`status` 在绑定时回 `facts.task.files {count, unexpected}`；
   规范集＝`task.json`/`prd.md`/`design.md`/`implement.md` + `review/`。自建证据文件第一次绑定就会被点名（不阻断）。
2. **命名统一**：导入目录 `review/review-round-N/<slot>.md` → `review/round-N/review-<agent>.md`（与暂存目录同构），旧名仍可读。

用例 `repro/task-dir-canonical.py`（注入=盘点恒空 → 判红）。`dev-manifest.json` 补登新文件后字节复现 **56 assets**。

验证：`WF_JOBS=1 run_all.sh` **127 项 0 失败**；三稿校验通过；字节复现 OK。

自伤 1 次：新增 `lib` 文件没进 `dev-manifest.json` → 构建直接报 `source tree has unlisted files`（这道门很值：新文件必须显式登记）。

## B7：信封缓存 + 状态短视图（2026-11-07，128 项绿）

| 改动 | 针对的实测代价 |
|---|---|
| 成功命令把「身份+activation+instance_id+generation」写进 `.wf/.runtime/last-envelope.json`（gitignore 托管段内，不提交） | dogfood 里 **51 次**反复拼 `/tmp/wf-env.json` |
| `--envelope-last` | 上述缓存缺失时给明确出口，不静默挂起 |
| `status --short` 只回 `{id,title,status,phase,complexity,tdd,check}` | **13 次**整份 `cat task.json` |

用例 `repro/envelope-cache-and-short.py`：启动任务后缓存存在且身份正确；`--envelope-last` 在**不给信封**时跑通 `status --short`，且摘要不含 `plan/reviews/execution/check_history`。注入=不缓存 → 判红。

验证：`WF_JOBS=1 run_all.sh` **128 项 0 失败**；三稿校验通过；字节复现 OK。

自伤 1 次：`dispatch` 的回写钩子那一段因前一个脚本断言失败而**没写进去**（脚本中途退出），导致缓存永远不产生——靠"缓存文件不存在"的断言才发现。

## B8：目录 ASCII 化 + 收口（2026-11-07，129 项绿）

| 项 | 结果 |
|---|---|
| `slugify` 只保留 ASCII | 目录名 `<id>-<ascii-slug>`；标题仍存记录。用例 `repro/task-dir-ascii.py`（注入=退回旧正则 → 判红） |
| 收口验证 | `WF_JOBS=1 run_all.sh` **129 项 0 失败**；三稿校验 0 problem；字节复现 OK（56 assets） |
| 交付物 | `dogfood-plan.md` §10：重跑清单（重置→安装→首跑→四指标→三条定位→停止条件） |

**关键发现（ASCII 化的连带效应）**：`p5_v2v3` 的"writer 未被任务提交捎带"原本靠**中文路径被 git 引号化**而"意外通过"——
ASCII 化后路径不再加引号，用例自己的 `git add .wf` 把 `.wf/tasks/**` 与 `.wf/writer.json` 扫进了同一个"维护组提交"，断言立刻判红。
这是**夹具缺陷**（提交范围太宽），已改为 `git add .wf ':!.wf/tasks'`：维护组提交覆盖整组排除任务目录。
先只补 `.wf/writer.json` 会漏掉 `.wf/bin|lib|templates|workflows`，导致回执核不过（`WF_HISTORY_UNRESOLVED`）——两种错法都试过，最终用 pathspec 排除。

## B8 后审计（2026-11-07，重跑前的独立复核）

对 B1–B8 逐项复核"是否真的解决"，并**实测**发现两处必须修的问题（已修）：

| # | 审计发现 | 证据 | 处置 |
|---|---|---|---|
| A1 | **信封缓存跨会话串身份**：缓存是单文件"最后写入者赢"。同一项目里主会话 + 两个 reviewer 会话并存时，主会话用 `--envelope-last` 会拿到 reviewer 的身份（实测：B 会话 enable 后，`enable --envelope-last` 返回 A 的 session_key 不变只是因 B 被平台校验拒；reviewer 的 `review-context` 成功则会写入缓存） | `/tmp/audit2` 实测 | 改为**按会话分文件** `.wf/.runtime/envelopes/<session_id>.json`；`--envelope-last [--session <id>]`，多会话且未指定 → `WF_IDENTITY_UNRESOLVED` 并列候选；`review-context` **不写缓存** |
| A2 | **B6 的规范文件盘点把入口自己的 `check-logs/` 误报为非规范**（`task-check` 会写验证输出） | 端到端探针：`files: {count:1, unexpected:['check-logs/']}` | `CANONICAL_DIRS` 补 `check-logs`；用例仍绿 |

其余复核结论（全部实测）：

| 声明 | 复核方式 | 结果 |
|---|---|---|
| reviewer 只给 task id + 轮次 | 真实 CLI：`review-context --task <id> --round 1`，host_id=pi（**未安装平台**） | `WF_OK`，返回 `review-pi.md` 与四份材料 |
| 同 agent 同轮二次审查被拦 | 连调两次 | 第二次 `WF_REVIEW_INVALID`（审查未开始） |
| 免路径导入 + 免轮次判定 | 两个 reviewer 写报告后 `review-import --task` / `review-decide --task` | `imported_agents=['pi','zcode']`、`reviewer_clis=['pi','zcode']`、`WF_OK` |
| `status --short` 精简 | 同项目实测 | 只回 7 个字段（无 plan/reviews/execution） |
| `help` 覆盖新参数 | `help baseline-apply` | 含 `--files` |
| 发行树含新技能文本 | grep release 副本 | wf-review 3 处、wf-review-action 1 处、三份技能各 1 处"证据文件纪律" |

验证：`WF_JOBS=1 run_all.sh` **129 项 0 失败**；三稿 0 problem；字节复现 56 assets。

**仍未验证（只能在真实会话里验）**：①Codex 会不会主动按技能用 `review-context`（而不是敲裸命令）；②模型会不会主动用 `help` / `--short`；③文件纪律是否真的抑制住自建证据文件。这三条正是 §10.3 要测的。

## 审计后设计定稿（2026-11-07，待外审）

人裁：`provider=wf` 提前到首轮；`generation` **保持必填**；**Linux 必选**，macOS/Windows 可选。

综合两份外部评审（/tmp/a.md、/tmp/b.md）后产出独立评审稿 `.trellis/tasks/11-05-wf-implementation-gap-audit/identity-redesign.md`：
身份＝wf 在人调 start 时签发的 `session_id`；锚点（tty 优先 → 进程锚）只做路由；附着只在 start；歧义一律 fail loud；
`activation` 落 runtime、`instance_id` 与**独立本机附件**比对、`generation` 必填；平台清单降为安装事实；`--envelope-last` 退役。

采纳 A 的两条硬修正（`generation` 不可自动补、`instance_id` 不可同源比对）与 B 的两条增益（tty 锚给重启连续性、同锚歧义阻断），
并明确不借 Trellis 的宿主环境变量表与单会话回退。§9 列了 7 个给外审的攻击点。

## identity-redesign v2（2026-11-07，据两份评审 + 实测复核）

**实测复核（决定性）**：`/proc/<pid>/stat` 第 6 字段是 `session`、**第 7 才是 tty_nr**（我 v1 写错）；
连续两次 `openpty` 得到同样的 `/dev/pts/7`、`136:7`、**inode=10**（**评审 B 说 inode 每次不同，实测不成立**；A 的观察正确）；
`getsid(0)` 在同一终端多次调用稳定、`setsid` 每条命令新 sid、新 shell 新 sid —— 故**会话锚定为 L1**，tty 降为审计。

**采纳的修正**：①同锚≠可见阻断（改为"同一执行会话"并如实披露同对象合并）；②新增 start 处**轮换**（解决终态后无法开新对象）；③`last_root_pid` 定消费者（旧根已死 ⇒ activation 降级，堵住跳过 §5.5）；④pid1 不可解析、解释器只按 pid 精确跳过；⑤两模式互斥（显式/自动），显式模式**保留 host_id 检查**与旧语义（因此 129 项不必改写）；⑥`generation` 闭环（响应回显 + STALE 出口）；⑦`checkout_id` 移出 MVP；⑧`host_id` 消费者清单（含 `cmd_enable` 的 Trellis 互斥）。

**质疑并反驳的**：B#1 的 inode 主张（实测不成立）；B#10 的"必须大规模改夹具"（双模式隔离后旧用例免改）。

## identity-redesign v3（2026-11-07，第二轮评审后）

**实测复核（新增）**：`exec /usr/bin/python3` 前后 **pid 与 starttime 都不变**（5096225→5096225）⇒ 评审 B#6"exec ⇒ 新 starttime ⇒ 新锚点键"**不成立**，该行从矩阵移除。
其余采纳：L1 需 R0 前置验证门（8 种环境，不满足即列不支持）；`resolve_anchor` 改为**返回候选列表**（L1→L2 回查，二者皆 miss 才 fail）；`root_ref` 定义为 L2 的 agent 祖先并**每次成功调用后刷新**；新增 `facts.concurrent_callers`（同锚并存）；L2 候选加三条硬判据（非 pid1、**非 init 直接子进程**、starttime 早于调用者）；activation 强度拆分两面；`WF_ATTACHMENT_MISSING` 增量原因码；轮换提交顺序与失败语义；显式模式定位与退役条件；Windows 只支持显式模式。

## R0 首轮实测 + 同锚策略定案（2026-11-07）

探针 `r0-anchor-probe.py`（8 场景）已跑 4 个：
- 普通终端：L1/L2 均稳定；
- **`setsid` 新会话：L1 变、L2 不变（同 node pid）→ 实测证明 L2 会静默合并 L1 能区分的边界**；
- `systemd-run --user --scope`：继承发起终端 sid（同一执行会话，记为可接受）；
- `docker run … python3`（容器 pid 1）：**L1/L2 全无** ⇒ 按设计阻断。

由实测新增 **L2 独占性检查**：L2 独用时若该根已属另一个 session ⇒ 阻断（防静默合并）。
人裁：**共享宿主（同锚）取"披露"**——合并发生且 `facts` 标记，不阻断；矩阵与 §10 已按此更新。

## 方案 v3.1：R0 升格为强制门（2026-11-07 人裁）

人裁：**R0 必要**，不接受"仅保证普通终端"的口径；**后续在实现前执行 R0**。
文档已改：§2.4 重写为强制门（四条判据 R0-A/B/C/D + 11 类环境清单 + 执行时机/产出/回归要求 + 处置规则）；
新增 §2.5 `r0-results.md` 记录模板；§8 R0 行改为"未完成不得进 R1"；§9 加验收第 15 条（支持环境逐行有 R0 证据）；§10 第 1 条划掉（已裁）。
探针 `r0-anchor-probe.py` 已在 4 个环境跑出初步数据（普通终端 / setsid / systemd-run / docker run），**不构成 R0 通过**。

## 方案 v3.2：根进程改集合（2026-11-07，自审后修）

**缺陷（我上一轮自己预判的第 4 条）**：`last_root_ref` 是单字段，两个并存调用者会互相覆盖 → 并存检测失效、"旧根已死"判定也会被覆盖成伪值。

**修法**：§3.4 整段重写为 `roots[]` 有序集合：
- 每条 `{pid,start,exe,first_seen,last_seen}`；常量 `ROOT_TTL=12h`、`ROOTS_MAX=8`；
- 每次成功认证后在**项目锁内**做 upsert → 剪枝（进程死/超 TTL）→ 超额淘汰最旧；
- 三种关系：**同一调用者**（正常）/ **并存**（`facts.concurrent_callers` 披露）/ **同锚新调用者**（旧根全死 ⇒ `WF_NOT_ENABLED` 要求重新 start）；
- **TTL 清空 ⇒ `activation_stale=true`**：长时间空闲后回来不当作首调用者继承激活，宁可让人重新 start；
- 数据结构、建立/轮换字段、L2 独占性检查引用、验收（新增 8b/8c）全部同步；§10 第 4 条标为已修。

## 方案 v3.3（2026-11-07，第三轮评审后）

采纳（11 条，全部落文档）：
1. **roots 判定顺序**：`snapshot → 判定 → 维护`（原"先 upsert 再剪枝"让 TTL 分支永不可达、"当前根在集合"恒真）；
2. **降级持久化**：`!known ∧ snapshot 非空 ∧ 无其它存活根` ⇒ 写 `activation_stale=true`，`WF_NOT_ENABLED` 判据 = 附件无效 **或** stale；**只有 start 清除**；**只读命令不参与 roots**（顺带堵死"用只读调用洗掉降级"）；
3. **回查决策表**（§2.2b，7 行）：明确 L1 命中/L2 命中/L1 漂移/L2 独用/双 miss 的动作；`start` **同时登记 L1+L2**；
4. **L2 归属按可达性裁决**：对方 session 可达 ⇒ 阻断；不可达（锚点全失效、只剩本根重叠）⇒ **迁移附着**（`facts.anchor_migrated`）——修掉"leader 先死、同一 agent 继续"被误杀；
5. **删掉 ROOT_TTL**：Linux 上存活可证，TTL 只会把活着的 agent 隔夜剪掉造成强制重新启用；`ROOTS_MAX` 只淘汰死条目，全活超限记 `facts.roots_capped`；
6. **轮换前置**：旧会话仍持写权时**不轮换**，先走 §5.4 释放；
7. **附件显式恢复流程**（start 内 5 步：核对象/写权 → 重建 `instance_id_expected := binding.instance_id` → 按真实 start 写 activation → 留痕）；"存在但不符"先呈现差异再人确认重建；
8. **R0 完成条件**：可选类不可达记"未验证⇒阻断"、不算未完成；**必须经 agent 命令路径**跑（终端直跑仅对照）；
9. **矩阵修正**：共享宿主同一 root ⇒"合并且**不可检测**"（`concurrent_callers` 只对**不同 root** 生效）；leader 先死补迁移分支；每命令新 L1 补降级分支；
10. **R2 交付物**：新增"roots 行为用例"（判据 4/7/7b/7c/7d/7e/8/8b/8c）；
11. **§6 收窄**："跨会话冒充被堵死"**仅自动模式**；显式模式仍完整接受请求身份（既定选择，不作全局保证）。

文档 421 行；§10 新增 2b（共享守护进程是否强制只允许显式模式）待裁。

## 方案 v3.4 + R0 执行件（2026-11-07，第四轮评审后）

采纳（9 条）：
1. **路由与状态分离**（a#1/a#2、b#2）：`anchors.json` **单文件**（整文件 rename ⇒ 轮换时该会话全部键一起改指，不再留分叉别名）；`roots/activation/activation_stale/instance_expected` 移到 **会话级** `attachments/<session_key>`（单份，跨键不再漂移）；重复 start **合并**已有存活根，不重置。
2. **R0 改为按支持路径验证**（a#3）：P1（L1 稳定，完整支持）/ P2（L1 每命令变 + L2 单根，**受限支持·仅单聊天假设**）/ P3（仅 L1，完整支持）；两者皆不稳 ⇒ 不支持。删除"L1+L2 都必须稳定"的旧判据。
3. **首次建立**（a#3）：候选集非空即可 start（不再把"L1 可用但未登记、L2 不可用"判成无锚）。
4. **失败形态三分法**（a#4）：机械可识别 / 部署前提（无运行时信号，靠文档声明）/ 仅 R0 证据（发布范围）。并写死"工具表与 init 直子判据**只约束 L2**，L1 不做名字过滤"。
5. **空 roots fail-safe**（b#1）：删 TTL 后，空集/损坏**不得落到正常推进** ⇒ `activation_stale` + `WF_NOT_ENABLED`；判据 8b 相应改写（原写"TTL 清空"已无此机制）。
6. **附件恢复三态**（a#5）：未绑定 / 在途 / 终态待清理；终态待清理只恢复"补释放所需"的启用与附件，不得推进业务。
7. **命令三分类**（b#6）：只读（不参与 roots）/ **写侧车但需 activation**（`spec --file`）/ 写业务；并声明显式模式不参与 roots。
8. **矩阵补两条不可检测通道**（b#3）：决策表 #4 的 L1 漂移降级、迁移附着，都只在**单聊天假设**下安全；容器内 reparent 到 init 会让 L2 不成立（b#4），矩阵已限定。
9. 统一：建立/**轮换/迁移/附件恢复** 四种 start 动作都清 `activation_stale`；`root_ref={sid}` 形态下"agent 重启降级"不适用（判据 4 已注例外）。

质疑/反驳 1 条：b#5 称 `WF_HISTORY_UNRESOLVED` 是"悄悄引入的新码"——核 `codes.py:91` **该码已存在**（`needs_decision`），无需登记；真正需要增量登记的是 `WF_ATTACHMENT_MISSING`（现不存在）。

**R0 执行件就绪**（按人裁，等最终审查结论后再跑）：
- `r0-run.sh`：本机可自动化的 8 类（bash/zsh/嵌套/setsid×2/systemd-run/docker run/docker exec -t/leader 先死），输出 `r0-results.json` + 汇总表；
- `r0-manual-steps.md`：tmux / VS Code·JetBrains / CI / ssh·sudo·script 的人工步骤，并明确"**经 agent 命令路径**的那次才作判定依据"。

## 方案 v3.5（2026-11-07，第五轮评审后）

采纳（7 条，全部落文档）：
1. **伪码与新 schema 同步**（a#1）：§3.1/§3.3 改为"`anchors.json` 只存 key→session_key；状态只写 `attachments[session_key]` 一份"，轮换 = 写新附件 → 把该会话**全部路由键**改指 → 单次 rename；
2. **标识链写死**（a#2，新增 §2.6）：`issued_id → {provider:"wf",identity} → session_key`；路由/绑定/附件/writer.holder 一律用 `session_key`，日志用 `issued_id` 前 8 位；
3. **迁移确定性表 M1–M5**（a#3，新增 §3.4c）：定义"可达"= 任一登记键命中当前候选 **或** 有除本根外 alive 的 root；并规定迁移**同批** upsert 新 root + 清 stale（否则迁移后第一条命令立刻被打回，b#2）；
4. **存活三态 alive/dead/unknown + 锁分离**（a#4/b#1，新增 §3.4b）：`/proc` 不可读 ⇒ unknown ⇒ **不剪枝、不据此降级**、报 `facts.roots_unknown`；`attachments` 用**自己的锁**，不再抢 `.wf-lock`（否则两会话场景常态化等锁超时）；
5. **P2 是部署事实、默认关闭**（a#5，新增 §2.4d）：`.wf/project-config.json` 的 `identity.path`；P2 需 `--accept-single-chat` 显式启用并在 facts 长期显示假设；
6. **命令四分类**（a#6/b#4）：`repair/install/upgrade/uninstall` 归**维护类**（不读信封、不需 activation、不参与 roots，与 `bin/repair.py` 实现和机制稿 §2.1 一致）；`start` 单列；`spec --file` 身份失败时"只读断言可做、不给完整读取回执"；
7. **附件恢复三支互斥**（a#7）：未绑定 / 在途 / 终态待清理 各自独立步骤，不再落入统一绑定对账。

另补：矩阵加 **`{sid}` 退化根**行（先后两个 agent ⇒ 同一会话、无降级、不可检测）；`WF_NOT_ENABLED` 的 `facts.reason` 分 `activation_missing` / `activation_stale`；验收补 15b–15e。

**质疑/反驳 2 条**：
- a#8「验收 8b 仍写 TTL」——**该文本已在此前修正**（现为"roots 为空或条目损坏"，见 §9:456）；评审读到的是旧副本。
- a#8/b#4.5「`WF_HISTORY_UNRESOLVED` 未按增量码登记」——**已登记**：`codes.py:91`（needs_decision）与机制稿 §11.1 码表（:855）都有。本轮第三次同一主张，附证据不再采纳。

文档 585 行 / v3.5。

## 方案 v3.6（2026-11-07，第六轮评审后）

本轮全部是**我上一版"半截修改"留下的内部矛盾**，评审判断正确：

| # | 矛盾 | 处理 |
|---|---|---|
| a#1 | `task-start` 被归入"start 自身"（activation 非前置）⇒ 未启用会话可绕过 activation 开工 | `enable` 单列为"会话建立/启用"；**`task-start` 归业务类**，必须有效 activation |
| a#2/b#1 | §3.4 并发段说 roots 在项目锁、§3.4b 说用附件锁；判据 8c 也写项目锁 | 统一：附件用**附件锁**，anchors/writer/bindings 用**项目锁**；**锁顺序固定"先项目锁后附件锁"，禁止持附件锁再取项目锁**；判据 8c 改为附件锁并断言"与写权持锁互不阻塞" |
| b#2 | §3.5 恢复表同时存在新的 0/0a/0b/0c 与旧的 1a/1b/1c/2–5 两套流程 | 整表重写为**三支互斥**，每支自含步骤/是否核写权/输出 `restored_mode` |
| b#3 | §2.6 立了"落盘用 session_key"，§3.3/§7 仍写 session_id | 机械统一（现全文仅剩 §2.6 的解释句） |
| a#3 | 决策表 #7 把"L1 可用但未登记 + L2 不可用"判成无锚 ⇒ P3 首次使用无路径 | 拆 **7a（候选为空）/ 7b（候选存在未登记 ⇒ start 可新建）** |
| b#4 | `enable --identity-path P2` 自身被"P2 未启用"阻断（引导悖论） | 增**引导例外**：该命令是唯一允许在 P2 未启用时做一次性引导认证的入口（L2 命中 + 单根 + 人显式发起），记 `facts.identity_path_bootstrapped` |
| b#5 | §2.2b 与 §3.4c 都自称实现依据且守卫不一致 | 边界写死：#2.2b 管**每次调用路由**，M 表只管**候选全 miss 后 start 的处置**，且 **先查 M3–M5 再新建**；M2 拆 **M2a（L1 不可用，无守卫）/ M2b（L1 可漂移，需单根 + P2 已启用）** |
| b#6 | `identity.path` 与 `p2_enabled` 双字段冗余、未登记配置契约 | 改**单字段 `identity.path ∈ {P1,P2,P3}`，缺省 P1**；按配置键契约登记（随发行骨架、schema_version、非法值 `WF_RECORD_INVALID`） |
| 小项 | 孤儿附件无 GC；`{sid}` 混合形态未写 | 补 GC 三条件（无路由指向 + 对象终态 + 非 holder）；补 `{sid}` 条目按 unknown 处理 |

**再次反驳（第四次）**：`WF_HISTORY_UNRESOLVED` **已在码表**——`codes.py:91`（needs_decision）与机制稿 §11.1:855。本轮附证据，不再修改。

文档 612 行 / v3.6。R0 执行件不变，等最终判定后执行。

## 方案 v3.7（2026-11-07，第七轮评审后）

采纳 2 个实质问题 + 5 个清理项：

**实质 1（a#1，真漏洞）**：§3.4c 的"可达"只看 alive ⇒ 旧根为 **unknown** 时被判"不可达" ⇒ M4 迁移接管，"证据不明即自动接管"。
→ 新增 **M3u**：S 不可达但 roots 含 unknown ⇒ **阻断**（`WF_HISTORY_UNRESOLVED`，`reason="old caller liveness unknown"`，出口＝人核实或 §5.5 受控恢复），**禁止迁移**；M4 条件收紧为"既无 alive 也**无 unknown** 的其他根"。

**实质 2（b#2，治理漏洞）**：`enable --identity-path` 直接写 Git 跟踪的 `project-config.json`，绕过设计稿 §3 的基线通道。
→ 改为：安装参数写入 + 之后走**维护类命令** `wf.py identity-path --set P2 --accept-single-chat --decision <f> [--preview]`，复用 `baseline-apply --files` 的**提案/批准/摘要**通道；维护类不读信封 ⇒ **引导悖论同时消失**（删除 v3.6 的"引导例外"）。

**清理**：①M 表收缩为 M3/M3u/M4/M5，命中场景明确归还 §2.2b（并给 #4 补 P2 前提）；②§4.2b 业务行去掉 `start`、维护类加 `identity-path --set`；③§3.4b 删除重复锁段，指回 §3.4；④§3.5 ② 的 `WRITER_BUSY` 收窄为"holder 非本会话且非中断态 ⇒ 仅报告，不处置"；⑤§3.3 旧名 `entry.session` → `route.session_key`。

**第五次反驳**：`WF_HISTORY_UNRESOLVED` 已登记三处——`codes.py:91`、机制稿 §11.1:855、实现方案 :374/:469/:673 均有消费与定义。不再修改，请评审方指出其认为缺失的**具体码表位置**。

## 方案 v3.8（2026-11-07，第八轮评审后）—— 三个"会静默失效"的问题

**a1 共享 L2 让新终端建不了会话**（真缺陷）：v3.3 的"L1+L2 无条件双登记"把 L2 变成全局别名——
A 登记 (L1=a,L2=c)，B 在另一终端得到 (L1=b,L2=c)，L1 已区分两者却被 L2 覆盖。
→ 登记键按支持路径决定：**P1/P3 只登记 L1**（L1 有决定权，L1 不同=不同边界），只有 P2 才 L1+L2；决策表 #4 在 P1 下**不复用**、按新边界处理。

**a2 迁移没有正向关联**（真缺陷）：旧根已死只证明"停止了"，不证明"当前调用者是其后继"。
→ 新增**迁移候选集** `{S : S.roots 含当前 root（同 kind 同标识）}`；**空集不得迁移**（新建会话），恰一个才按 M3/M3u/M4 处置，多个 ⇒ M5 阻断。

**a3 issued_id 首次绑定前无处保存**（真缺陷）：只存哈希 key，"只启用未绑定"后重启无法构造 `binding.identity`。
→ `attachments` 里存 **`identity` 原文 + session_key**，启动时核 `SHA256(C(identity)) == session_key`。

其余：a4/b3 **`identity-path` 授权链归维护类**（复用提案格式与摘要校验，但不借用任务批准/会话写权，按维护命令契约走预览+互斥+留痕）；a5 **恢复五态 S0–S4**（补"终态已清理"与"绑定原本应有却缺失"）；a6/b2 **根两型（pid/sid）+ unknown 单一语义**（放行前提一律阻断/stale，仅披露场合不阻断，sid 永不 unknown）；b1 L2 归属检查改扫 `attachments`；b4 命令清单补全；b5 **消费码表列清**（仅 `WF_ATTACHMENT_MISSING` 需新增）；b6 矩阵补 M3u 行。

文档 664 行 / v3.8。

## 方案 v3.9（2026-11-07，第九轮评审后）

**a1/b1 合并经 M4 复发 + P1 续接被切断**（同一根因，真缺陷）：v3.8 的"P1 只登记 L1"既让 L1 后死无法经 L2 续接（#5 不可达），又没挡住 M4 按 root 把新边界并进旧会话。
→ **登记两键 + `attached_l1` 守卫**：决策表 #4/#5 只要发现「S.attached_l1 现在仍可解析」⇒ 判定"那是另一个边界"⇒ 不得复用/不得降级；M4 额外要求「当前 L1 不可用」。两处同时修好。

**a2 identity 结构与哈希输入不一致**：`{provider:"wf", identity:{issued_id}}` vs `{provider:"wf", issued_id}`。
→ 附件里 `provider` 与 `identity:{issued_id}` **分开存**（与哈希输入同构），轮换/恢复用同一构造；核 `SHA256(C({provider,identity})) == session_key`。

**a3 身份不可恢复**：S0 且附件已丢、从未绑定 ⇒ 不得沿用旧 key ⇒ 走新会话建立，报 `facts.stale_routes` 并清理路由。

**a4 迁移候选集含轮换残留** ⇒ M5 假冲突：候选集加**有效性**（`superseded_by == null` 且 有 roots 或有路由键），轮换时旧附件打 `superseded_by`。

**a5 路径切换后旧键无规则** ⇒ 路由键记 `via`/`path_at_attach`，**只使用当前路径兼容的键**判定，旧键保留但不参与（`facts.routes_shadowed`）。

**b2 S0/S1 无机械判据** ⇒ S0 ⇔ 无 binding 文件**且**该路径在 Git 历史中从未出现（`git log --diff-filter=D`）；否则 S1。

**b3 五态与三支执行表脱节** ⇒ 执行表重写为 S0–S4 五行，含 identity 来源列。

**b4 判定顺序未定** ⇒ 写死：①解析与决策表 → ②五态 → ③roots/并发 → ④迁移。

文档 705 行 / v3.9。

## 方案 v3.10（2026-11-07，第十轮评审后）

**实测复核（a3 成立）**：`git log --diff-filter=D -- <绑定路径>` 在"提交过、仅工作树删除"时为 **0 条**（实测：任意历史 1 条、`--diff-filter=D` 0 条）。我 v3.9 的 S0 公式会把"绑定被删"误判成"从未绑定"，进而签发新身份。

修正（6 条）：
1. **键资格改按 `path_at_attach`**（b1，我 v3.9 自相矛盾：§2.2 说两键都登记、§2.2c 又把 P1 的 proc 键排除 ⇒ #5 不可达、`attached_l1` 守卫成死代码）。现在"路径切换"只排除**别的路径时代**的键；P1 自己的 proc 键照样参与，防合并全靠 `attached_l1` 守卫。
2. **#4 补 else 格 + P2 豁免**（b2/small）：当前 L1 可用 ⇒ P1/P3 一律不复用（`attached_l1` 死活不改变结论）；P2 不做该守卫（L1 本就不是边界依据）；`attached_l1=null` ⇒ 守卫放行但报 `facts.single_chat_assumption`。
3. **守卫覆盖 M4**（a1）：迁移除了"当前 L1 不可用 + root 相同 + 无其他存活根"，还要求 `S.attached_l1` 已死或 null——否则 P1 下共享 root 的另一调用者会被迁移并进去。
4. **有效性以"已提交路由"为准**（a2）：`superseded_by`/`roots 非空` 都不作数（前者崩在提交前不会写，后者对候选恒真）。孤儿附件与轮换残留**天然无路由** ⇒ 自动无效。轮换顺序写死：①写新附件（此时是孤儿）②commit 路由（组原子）③成功后写 `superseded_by`（仅审计）。②失败 ⇒ 旧会话仍有效、无孤儿参与迁移。
5. **S0/S1 判据重写**（a3）：不再用 `--diff-filter=D`。S0 只在「attachments 存在且无绑定」或「本次 start 刚签发」时成立；attachments 丢失且非本次签发 ⇒ **S1 待核实**（`WF_HISTORY_UNRESOLVED`，人确认后才可走 S0）。
6. **顺序改分支表述**（b4）：hit 分支 ①→②→③；miss 分支 ①→④（②③不执行）。**S0 新身份覆盖路由**（b3）：`start` 在五态判 S0/待核实且 identity 不可恢复时，同锁内把路由改指新 key，而不是"复用后再清理"。

文档 724 行 / v3.10。

## 方案 v3.11（2026-11-07，第十一轮评审后）—— 结构重写，不再打补丁

**根因**：前四版反复在"登记哪些键"上打补丁，因为我把"登记"当成**单一映射**。真实情况是：
**L1 是单主（一个终端只属一个会话）、L2 可多主（一个 agent 进程可被多个边界共享）**。
承认这一点后，一串历史问题一起消失。

| 改动 | 解决的历史问题 |
|---|---|
| `anchors.json` 的 value 改 **`owners: [...]`**；L1 登记要求单主（否则 `WF_HISTORY_UNRESOLVED`），**L2 追加不覆盖** | a1/b1（两终端共享 L2 时路由互相覆盖、合法建立第二个会话却报"历史冲突"） |
| **取消 v3.10 的 #2「键冲突」**：L1 命中即以 L1 为准，L2 多主仅 `facts.l2_shared` 披露 | 同上：L2 多主是常态，不是损坏 |
| **#5 唯一裁决**：owners 中 `attached_l1` 已死或 null 的**恰一个** ⇒ 续接；多个 ⇒ `ambiguous shared root` 阻断；零个 ⇒ 阻断 | 把"独占性阻断"（与多主矛盾）收敛成一个裁决点 |
| **删除 §2.3b 独占性阻断**，R0-C 判据同步改为"能否唯一裁决" | 旧规则会把正常双终端判成"占用 ⇒ 阻断" |
| **S0 改为最严格一档**：必须**无任何曾绑定痕迹**（`instance_expected` 有值 / writer 引用 / Git 任意历史 / 绑定文件存在，任一成立即"曾绑定"） | a2（"附件存在"被误当"从未绑定"——已绑定会话的附件一直在） |
| **§3.1 伪码落地 S1 闸门**：S1 ⇒ `WF_HISTORY_UNRESOLVED` 终止本次 start，不签发 | b2（伪码会替待核实会话自动签发新身份，违反"证据不足不判 S0"） |
| 路径切换后果写明（P2→P1 ⇒ 旧键失格 ⇒ 路由重置 ⇒ 若持写权走 §5.5）+ `facts.orphan_sessions` | 小项：避免被当成"切路径后 wf 坏了" |
| 删 §3.3 重复旧注释；§7 schema 标注 `superseded_by` 为可选/仅审计 | 小项 |

**一致性自检（机械）**：全文检索已废弃表述，`P1/P3：L1；P2`=0、`--diff-filter=D`=0、`roots 非空 或 存在路由键`=0、`独占性检查`=0、`superseded_by == null`=0；
新语义关键词均在位（`owners` 11 处、`L1 单主` 4 处、`ambiguous shared root`、`orphan_sessions`）。

文档 ~740 行 / v3.11。

## 方案 v3.12（2026-11-07，第十二轮评审后）

v3.11 的结构改写只改到一半（`owners` 只进了 §2.2a/§2.2b），其余章节仍按单值语义，本轮全部回扫：

| # | 问题 | 处理 |
|---|---|---|
| a1 | 轮换仍按 `value.session_key == S` 改指 ⇒ 共享 L2 时把 B 一起改指、或把 A 留在 owners | **`replace_owner(S→N)`**：遍历所有路由，owners 中 S→N、**保留其它 owner**；给出"A 的 L1 {A}→{N} / 共享 L2 {A,B}→{N,B} / B 的 L1 不动"的对照表；轮换即 L1 单主的受控替换路径 |
| b2 | §7 anchors schema 仍是单值 | 同步为 `owners + path_at_attach`，注明 L1 单主 / L2 多主 |
| b1 | M3「可达」在 owners 模型下失效（miss 分支键不可能命中；"除本根外 alive root" 又是多主常态）⇒ M3 几乎不触发、M4 几乎总触发，**双终端共享 root 会在 leader 死后被迁移合并** | 迁移整体**并入 #5 同一判据**：`U = {S : attached_l1 不可解析或 null}`，X1 unknown ⇒ 阻断、X2 恰一个 ⇒ 追加 owners + 续接、X3 多个 ⇒ ambiguous 阻断、X4 零个 ⇒ 阻断、X5 候选空 ⇒ 新建。**M3/M3u/M4/M5 编号作废** |
| b3 | #5 用「attached_l1 已死」而 sid 型根按 §3.4b 不做存活判定 ⇒ P3 续接卡在未定义 | 改为「**不可解析**（leader 不存在或 sid 不符）」= 存在性检查，并在 §3.4b 注明不走存活三态 |
| a2 | 把 writer 引用一律当"曾绑定"证据 ⇒ 堵死合法的**未绑定准备流程**（preparation scope） | 证据只看 **scope 是任务/实例** 的写权与提交类维护结果；preparation 引用**不算**；并补"附件完整 + 无绑定 ⇒ 可直接 S0，不要求本次签发" |
| 小项 | `l2_shared` 常态噪声；R0-C 名称/描述未跟上 | 改 `l2_owners_changed`（仅数量变化时）；R0-C 更名「**唯一裁决**」，P2 行与模板表头同步；矩阵 M3u 行改称 X1 |

**一致性自检**：`可达（任一登记键命中候选` = 0、`value.session_key == S` 仅存于 changelog 说明、M 表编号引用已全改为 X1–X5。
文档 ~800 行 / v3.12。

## 方案 v3.13（2026-11-07，第十三轮评审后）

**a1（真缺陷）**：`attached_l1` 不可解析只证明「L1 边界没了」，**不证明「旧会话的 agent 进程停了」**。
场景：A 的终端 leader 死了但 agent 仍活；B 是共享同一 L2 root 的另一边界 ⇒ 旧规则把 B 接进 A 的会话，继承其 activation/绑定，而 A 的进程还在跑。
→ #5 与 X2 都改为**双重条件**：`attached_l1 不可解析或 null` **且** 该会话**除当前 root 外无 alive 根**、且**无 liveness-unknown 根**。任一不满足 ⇒ 阻断。

**b1（真缺陷）**：X2 原写"把当前候选键追加进 owners"，但
①若该 L2 键已在 owners 里，追加是 no-op ⇒ **迁移什么也没做**，只是打了个"已迁移"标记；
②`|U|==1` 没排除**其它 owner 仍活着**，于是新边界会被"加入现存共享"而非"接管孤儿"。
→ X 表引入 `O = C \ U` 与 `alive_other(S)`，**X2 收紧为 `C==U` 且 `¬alive_other(S)`**（接管孤儿），
`O` 非空或其它根仍活 ⇒ X4 阻断。X5 明确标为 else 分支。

**b2/b3 残骸**：`resolve()` 可执行伪码仍按单值 `anchors[k].session_key` 取会话（owners 模型在 resolve 层不存在）、
§2.6 用途表仍写"value = session_key"、§2.3b 裁决伪码仍用已废除的"已死"措辞 → 三处机械同步为 owners / "不可解析"。

**小项**：矩阵"leader 先死"行与判据 7b 去掉"可达"（改 X1–X5 语义）；轮换前置补"别人的 recovering 交接 ⇒ 阻断"；
"可达"定义整段替换为"已废除"说明 + 现用两个判据；R2 交付物改为"X1–X5 五分支 + 接管孤儿/加入共享的区分"。

文档 778 行 / v3.13。

## 方案 v3.14（2026-11-07，第十四轮评审后）—— 判据收敛为唯一函数

**a#14 成立**：v3.13 把新判据写进 #5 与 X 表，但 §2.3b 的旧伪码、矩阵的 L2 裁决行、R0-C 描述仍只写
「owners + attached_l1」，**漏掉 `alive_other` 与 liveness-unknown 两个条件** ⇒ 按那些地方实现会重新允许
"旧 agent 仍有其它存活根"时接管。这不是文字重复，是**行为分叉**。

**做法（不修补，收敛）**：新增 **§2.3d `adjudicate(C, current_root)`** 作为**全文唯一实现依据**：

```
unknown_any / U = {attached_l1 不可解析或 null} / alive_other
BLOCK(evidence_unknown) → NEW(C为空) → USE(C==U 且 |C|==1 且 ¬alive_other)
→ BLOCK(ambiguous_shared_root) → BLOCK(other_boundary_alive) → BLOCK(other_root_alive) → 兜底 BLOCK
```

- **#5**（hit）与 **§3.4c X 表**（miss）都只调用它，各自只解释结果（续接 vs 接管孤儿）；
- **§2.3b** 删掉自带判据与伪码，改为「没有独立规则，一律调用 `adjudicate()`」；
- **失效矩阵**两行、**R0-C** 描述、**§3.4b** 的放行前提行、**§3.4c** 额外前提段 全部改为引用；
- **X1–X5 编号作废**（评审 b#14 指出的 M4 残骸一并清掉）。

文档 796 行 / v3.14。自检：`M4`/`M5`/`X1–X5` 仅存于 changelog 的历史说明，正文零残留。

## 方案 v3.15（2026-11-07，第十五轮评审后）

**a1（真缺陷）**：`adjudicate()` 把「attached_l1 读不到」与「attached_l1 确认不存在」都归入 `U` ⇒ **权限/IO/namespace 读取失败被当成"旧边界已消失"**，可导致另一边界续接旧会话。
→ 证据**三值化**：`l1_state ∈ {match, gone, unverified}`、`root_state ∈ {alive, dead, unverified}`；**unverified 一律 `BLOCK(evidence_unknown)`**，只有 `gone` 才能作为孤儿接管依据。同步修验收 15d（原写"不据此降级"，与 §3.4b 冲突）。

**a2（结构冲突）**：`path_at_attach` 是**条目级**字段，但 L2 可多主且各 owner 来自不同路径时代 ⇒ 无论更新还是保留条目都会错一半。
→ **删除该字段，改「路径切换 = 路由重置」**：`identity-path --set` 在维护事务内把 `anchors.json` 存档并清空；旧会话成为 orphan（`facts.orphan_sessions`），绑定/附件/历史全保留，接续走 §5.5。

**a3（正常路径缺口）**：首次 `bind` 生成 `instance_id` 后，**没有任何步骤把它写进附件** ⇒ "启用未绑定 → 首次绑定 → 下一条命令"会因附件 null 失败。
→ 新增 **§3.6**：写入链（项目锁 → 附件锁）＋三种残态（binding 已写/附件 null ⇒ 幂等补齐；附件非空且不符 ⇒ 保留差异，只允许人确认后重建；附件已写/binding 未写 ⇒ 回退 S0）。

**a4（证据越界）**：验收 15/15b 要求运行时区分"未验证环境""P2 未启用"——超出可识别能力。
→ 收窄为：**机械可识别的不合格必须阻断**；**未通过 R0 的不得声明为支持**（发布纪律）；不可识别的部署前提按"部署前提"类声明。

**b1（归因错误）**：矩阵 leader 行与判据 7b 说该场景产出 `anchor_migrated`，但 v3.9 起双键登记后 L2 路由存在 ⇒ 走 **#5 续接 `l2-only`**，根本不进 miss。
→ 拆 **子场景 A（L2 在 ⇒ l2-only）/ 子场景 B（L2 缺失失格 ⇒ 接管孤儿）**，判据分别断言。

**b2/b3/小项**：清理 X 表与 X1–X5 引用（含 R2 批次门措辞）；**#5 收紧**（`|C|>1 ∧ |U|==1` 不再放行）在 §2.3d 明示为有意行为变化并列入 dogfood 观察；owners 空数组 ⇒ `WF_HISTORY_UNRESOLVED`（不走裁决）；#4-P2 改为调用 `adjudicate()`。

文档 839 行 / v3.15。

## 方案 v3.16（2026-11-07，第十六轮评审后）

**a1/b1（同一处，真缺陷）**：§3.6 的"binding 已写、附件 null ⇒ 普通调用幂等补齐"与 §3.5"普通调用不补齐"冲突，
且"附件有值 + binding 缺失 ⇒ 清空 `instance_expected` 按首次绑定重来"会**抹掉"绑定被删"的证据**（那本该是 S1）。
→ 删掉普通调用补齐（只在 `start` 内按 S2 补，且要求 `writer.action` 证明是同一动作的中断意图）；
"附件有值 + binding 缺失"**保留证据、归 S1**，确属未完成首次绑定的走既有动作恢复协议补 binding，**不清空**。

**a2（算法与说明不一致）**：`adjudicate()` 只在 `unverified` 检查里排除了当前 root，`USE` 与 `other_root_alive` 分支漏了
⇒ 按字面实现会把"候选只剩 S、S 的根就是当前 agent"这种**文档承诺支持**的续接判成阻断。
→ 定义 `other_roots(S) = S.roots − {current_root}`，**所有根证据一律基于它**。

**a3（违反单一裁决）**：#4 把 `adjudicate({S})` 传成单元素集合 ⇒ `|C|==1` 恒真、歧义丢了；#5 又写"P2 不做该守卫"。
→ 函数签名加 `path`：**P2 的放宽写在函数内**（`G = C`），但 `|C|` 仍是真实 owners 集合，多候选照样 ambiguous 阻断；
调用处不得筛集合、不得跳守卫。

**a4（三值只落在裁决函数）**：§3.4 业务根维护仍是"没有 alive 就当全死"⇒ 全部 unverified 时误置 `activation_stale`。
→ 改为三值：`others_unk` 非空 ⇒ 报 `evidence_unknown`、**不置 stale、不剪枝**；只有 `others_dead` 覆盖全部旧根才降级。

**b2/b3/小项**：判据 7b 拆 A/B（A 断言 `l2-only` 且无 `anchor_migrated`；B 断言 `anchor_migrated`）；
§2.2a schema 示例删 `path_at_attach`；§2.4b 与新验收统一（未验证环境归"发布声明"，不要求运行时识别）；
路由条目加 `boot` 字段（键是哈希、无法反推 boot，GC 需要）；`anchors.invalidated-*.json` 仅留最近 3 份；
删 `routes_shadowed`；§3.4c 历史叙述压缩。

文档 861 行 / v3.16。

## 方案 v3.17（2026-11-07，第十七轮评审后）—— 本轮最多实质项

**算法/状态机（4 项）**
1. **a1**：`others_unk` 非空时阻断后**不得 upsert 当前 root**——否则新调用者被登记成"已知"，旧根转 dead 后就不再降级，等于绕过"须人重新 start"。改为**立即返回、状态原样保留**。
2. **b1**：`boot` 只进了 `anchors`，没进 `roots[]` 与 `attached_l1`；`starttime` 是"自本次 boot 起的 tick"，跨重启撞车 ⇒ 合法续接被误判"别一边界活着"。改为**条目带 `boot`，判定前先比 boot**（不同 ⇒ 视为 dead，可剪枝）。
3. **b2**：`state(null)` 与损坏条目的映射未定义（null 可导向 USE/BLOCK/evidence_unknown 三种行为）。补映射表：**null=gone**（§2.4a 允许只凭 L2 建立）、**损坏=unverified**（阻断）。
4. **a2**：`adjudicate()` 已统一，但"读法"仍无条件说"只有 gone 才能接管"，与 P2 的 `G=C` 冲突 ⇒ 读法限定 P1/P3，P2 单列为例外。

**可实现性（4 项）**
5. **b3**：§3.1 的 S1 出口写"人确认后重跑 start 走 S0"，但 S1 判据是"证据存在"——人确认不删证据，出口不可达。改为 **repair 出口**。
6. **b4**：S3/S4 判据"曾正常释放 vs 未释放"在 `writer.json` 里不可区分 ⇒ 改为可核对的 **`holder`/`recovering` 是否指向该 key**。
7. **b5**：`SHELLS_OR_UTILS` 匹配口径未定义 ⇒ `basename(exe)` **全等**匹配常量、不读配置、变更需重跑 R0。
8. **b10**：`root_exe → host_id` 在自动模式**无消费点**（机制稿已取消逐宿主声明）⇒ **删除该路径与 `host-map.json`**，`root_exe` 仅审计。

**契约与验证（5 项，最重）**
9. **b6**：新增 **§3.7 契约修订清单 C1–C5**——设计稿 §1.3 两条语义（"新会话不同"→"新边界不同"；"复制不接管"→"同边界即接管"）、机制稿 activation 落盘位置、D14 轮次、适配层注入。逐条列"原文/新语义/必须同步的位置"，R5 按此改文并更新索引。
10. **b8**：新增 **§3.7b 适配层退场**——否则存量注入让自动模式成死代码；给三阶段迁移与"两种 activation 来源"的一致性规则。
11. **b12**：新增 **§3.7c 轮次归属**——D14 原规定 provider=wf 属第二轮，本轮**人裁提前**；给批次与首轮通道映射。
12. **b9**：**§2.4e R0 环境清单按 agent 宿主重排**（A1 单聊天 / A2 同守护进程多聊天 / A3 逐命令新会话 为必测，终端形态降为对照），并补 macOS 行。
13. **b11**：新增 **§8b 组合穷举维度 + 7 条不变量**（I1 无 gone 不 USE、I2 有 unverified 不 USE、I4 失败不留痕…）。

**次要**：`status --issued` 只读查看旧对象（b13）；**§9b 使用观察项** O1–O4（runtime 误清理成本、路径切换成本、#5 收紧代价、A2 覆盖率）。

文档 975 行 / v3.17。

## 方案 v3.18（2026-11-07，第十八轮评审后）

**a1/b1（我上轮判断错误，已核实并纠正）**：v3.17 以"没有消费点"为由删掉自动模式 `host_id`，但
`review.py:281`（`review-context` 取 reviewer 身份）与 `:601`（`review-decide` 取实施 CLI）都在读它，设计稿 §6.5 也要求"实施 CLI 与两名 reviewer 不同"。
→ **审查参与者身份与会话路由身份分离**：reviewer 由 `review-context --as <cli>` 显式声明；实施 CLI 由 `start` 人声明写入 `reviews.launches[].implementation_cli`；**任一缺失 ⇒ 拒绝产生 pass**（不得用空集合放行）。新增契约项 **C6**。

**b2/a2（会摧毁主场景）**：`state()` 表缺"确认不存在"一行 ⇒ leader 死亡（`/proc/<sid>` ENOENT）会落进"不可读 ⇒ unverified" ⇒ 永久阻断，
而"leader 先死续接"正是本方案主推路径。→ 补三行：**ENOENT ⇒ gone/dead**、**start 不符（pid 复用）/ zombie ⇒ dead**，并写死 `ENOENT` vs `EACCES` 的区分。

**b1(毒丸)**：v3.17 让 `any_unverified` **无条件**前置阻断 ⇒ 一个无关旧根持续不可读（hidepid/异用户/跨 namespace）就把**已知且存活**的
当前调用者永久挡住，且"人核实"没有落点。→ ①`unverified` 降为 **USE 守卫**（只在判定依赖旧根证据时阻断）；②新增
`wf.py repair --mark-root-gone`（人确认后标 gone 并留痕），让"人核实"有落点。

**a3/b7**：不变量挂到具体入口——I1 仅 P1/P3 孤儿裁决、I2 仅 `USE` 候选、I3 收窄为"经 L1 可区分的边界"、I4 仅 `adjudicate()` 的 BLOCK（stale 分支是显式例外）。

**b3**：适配层标记语义二分——`identity.path` **键存在** ⇒ 切路径且停注入；**键缺省** ⇒ 解析兜底 P1 但**注入继续**（升级当天行为不变）；新装未验证宿主附显式调用模板。
**b4**：C4 补裁决记录 **OD-7**（写入 `open-decisions.md`，引 2026-11-07 原话）并补"设计稿 §8.1 首轮闭环清单"为同步位置。
**b5**：删 macOS 的"ps 后端"幻影（本方案未实现）；**b6**：unverified 固定输出 `WF_HISTORY_UNRESOLVED(facts.reason="evidence_unknown")`。
**小项 a–f**：`basename(readlink(exe))` 口径统一（readlink 失败 ⇒ 候选不成立）；删 `host-map`（§10.5 与条目 11）；`status --issued` 进命令表；
根相等条件含 `boot`；`attachment.activation` 结构写明与显式模式同构；删不可触发的"混用"规则。

文档 1016 行 / v3.18。

## 方案 v3.19（2026-11-08，第十八批第二轮评审后）

| # | 问题 | 处理 |
|---|---|---|
| a1/b2 | `repair --mark-root-gone` 有入口但**结果没接入判定**（只留痕不改 /proc 事实 ⇒ 下次仍 unverified） | 定稿为**删除 `roots` 条目**（不是加状态字段）：删除后 `others_dead` 自然覆盖 `others`，`state()` 无需新增"人裁"行；原像 + 决策摘要写 `maintenance_results`；参数面**只收 pid 型**（sid 型永不 unverified）；给最小验证链 |
| b1 | §2.3d **伪码仍是无条件 `evidence_unknown` 前置**，与同节正文"只是 USE 守卫"互斥；§3.4b 的表也是无条件口径 | 伪码改为 `USE` 条件里带 `∧ ¬any_unverified`，另起一行 `USE 条件成立 ∧ any_unverified → BLOCK(evidence_unknown)`；§3.4b 表拆成"依赖旧根证据 ⇒ 阻断 / 不依赖 ⇒ 只披露" |
| a2/b6 | 实施 CLI"start 时声明、写入 task 级 reviews.launches"——start 与 review-launch 是不同层，数据流断裂 | **声明时点改到 `review-launch`**（写入该轮记录）；会话级默认值只作预填；补录出口＝重跑 `review-launch --implementation-cli` 或 repair 补写；`--as` 约束写死（非空 + `normalize_agent`） |
| a3 | `review-context` 仍归业务类 ⇒ 未 start 的 reviewer 会被前置拒绝，到不了 `--as` | **单列 reviewer 入口**：不要求 activation、不参与 roots、不解析路由身份（与 `cli.py:1677` 现有实现一致） |
| b3 | §3.4 条件里"或已知 root 已非 alive"不可达 | 删除（当前 root 由定义恒 alive） |
| b4 | §8b 不变量表**双表头 + 缺列** | 重建为三列表，I1–I7 全填"适用入口" |
| b5 | 安装器"读本机 R0 结论"——发行集里没有该文件，且框架不做宿主探测 | 改为"展示结论表（发行内副本）+ 无条件附显式模板"，不假装能判定 |
| 小项 | §0.2 仍列 host-map；矩阵缺"无关旧根 unverified 只披露"行；命令表 `task-start` 重复 | 全部清理/补齐 |

文档 1035 行 / v3.19。

## 方案 v3.20（2026-11-08，第十九轮评审后）

| # | 问题 | 处理 |
|---|---|---|
| a1 | `mark-root-gone` 只按 `pid:start`，跨重启可能删错根 | 参数改为 **`pid:<boot>:<pid>:<start>`**；匹配 0 条或多条 ⇒ **阻断**并列候选 |
| a2 | 审查身份新协议没贯穿实现接口 | 新增 **§3.7a 实现修改点清单**：`cli.py` 参数（`--as` / `--implementation-cli`）、`review.py:281`（context 身份）、`:140`（launch 记录）、`:601`（decide 消费）、launch schema、import 署名、help 命令表；列明"缺失 ⇒ 拒绝出 pass"的验收 |
| a3 | 删根 + 写回执跨两个文件，无中断协议 | 定义 action 意图 + 固定顺序（意图 → 删条目 → 回执 → 清意图）+ **四种中断点的重入判定**；无意图但条目消失 ⇒ `WF_HISTORY_UNRESOLVED`（不猜） |
| b1 | `attached_l1` 的 unverified 没被"只披露"条款覆盖 | §3.4b 补一行：**#1/#2/#3 不调用 `adjudicate()`**（动作列直接"用 S"），故 `attached_l1` 的 unverified 在这些场景无效果——与 `js cli` 现状一致，避免落进 `other_boundary_alive` 的误导原因码 |
| b2 | `review-launch` 写 task 记录的写权链缺失 | 补引机制稿 §5.3：`reviews.*` 属**判定字段**，由入口脚本在 `writer.json` 代次内写；三命令仍是写业务类，**不因声明制免除写权** |
| b3 | 会话级默认值 `declared_implementation_cli` 无写者/清除/轮换语义 | 写者=`review-launch --implementation-cli`（附件锁内顺带写）；缺省时预填、归一不符则忽略并要显式；**随轮换复制** |
| 小项 | `status --issued` 无输出语义；§3.7b 表格断裂；矩阵两行谓词重叠 | 空结果 + `facts.found=false`；表格补齐"过渡期"行并闭合；矩阵列改"L1 命中（hit）"vs"候选全 miss（无 L1 命中）" |

文档 1050 行 / v3.20。

## 方案 v3.21（2026-11-08，第二十轮评审后）

| # | 问题 | 处理 |
|---|---|---|
| a1 | `--as` 未贯穿实现（报告文件名、import token、校验、help 都缺） | §3.7a 清单补 4 行；新增 **§3.7d 三点一致性**：`context --as X` 写占位 → 文件名 `review-X.md` → `import` 的 token 与 `--as` 都必须等于占位 X，否则 `WF_REVIEW_INVALID`（实测可构造的绕过：`context --as codex` + 文件名 `review-claude.md`） |
| a2 | `declared_implementation_cli` 有消费规则但**不在 schema** | 进 §7 schema；兼容缺省 null（不得解释成任意 CLI）；写者＝review-launch（附件锁内）；轮换/恢复/repair 保留 |
| a3 | `review-launch` 跨三处写，无事务协议 | 新增 **§3.7e**：复用 `mark-root-gone` 那套 action 意图/前像/后像 + 四种重入；明确"launch 记录是本轮事实、附件默认值只是下次预填"，故两者不同不算不一致 |
| b2 | 预填值可能过期（换对象后实施 CLI 可能变） | 写明：预填值**不可作为异种判定依据**；不符 ⇒ 重跑 launch 覆盖或 repair |
| b3 | 新装/升级两条路径混在一格 | 拆成两行：升级项首次仍注入；**新装项不注入**（干净路径），未验证宿主由安装输出兜底 |
| b4 | `state()` 缺 sid 型根的行 | 补两行：`sid_start` 相符 ⇒ match；**不符（sid 被新 leader 复用）⇒ gone**（视为不同边界） |

文档 1085 行 / v3.21。

## 方案 v3.22（2026-11-08，第二十一轮评审后）

**a1/a2 是事实指控，我接受并写进文档**：`--as` / `--implementation-cli` 只存在于清单，代码与机制稿/实现稿都还没改。
→ 新增 **§8c 交付状态表**：逐项列"未实现 / 未同步 / 未跑"，并写明"本方案目前**没有一行实现代码**；C6 是待办不是已完成"。
这条同时防止后续把 C6 当已闭合。

**a3**：`review-launch` 的 action 伪码字段太薄 ⇒ 补 **action schema 映射**：幂等键 `SHA256(C({kind,task,round,impl_cli,decision_digest}))`（**含 impl_cli**，补录即新 id）、`base_revision/head_before/targets/before/after`、**generation 变化 ⇒ 拒绝旧 launch 重入**（`WF_GENERATION_STALE`）。

**b1（v3.21 自造的矛盾）**：重入表说"round 已存在 ⇒ 只补 ②"，而 §6 的补录出口恰恰要求"更新 ① 的 implementation_cli" ⇒ **补录永不可达**。
→ 重入判定改为比较 **意图值 vs 落盘值**：相同 ⇒ 只补 ②；不同 ⇒ **按意图值更新 ①**（写新 `declared_at/by`）。同时把"同轮次幂等"的两种含义统一成一句。

**b2/b3**：sid 根两行补 `root_state`（相符 ⇒ alive；不符 ⇒ dead）；§3.4b 的"同 sid 即同根"改为 **`(boot, sid, sid_start)` 全等**（否则与 state() 新行相反）。

**b4**：`review-context` 要写占位与 materials（项目树）却没授权链 ⇒ 声明为**固定职责授权**（同 §4.2 机读触碰面），
并把占位记录移到运行态 `.wf/.runtime/review-claims/`；materials 落任务树但**不随记录提交**。

**小项**：§3.7a 第二张表补表头；§3.7b 计数改为"前两行互斥 + 过渡期正交"；§3.7d 补"占位不存在 ⇒ 同样阻断"。

文档 1131 行 / v3.22。

## 方案 v3.23（2026-11-08，第二十二轮评审后）

**三个高优先级，全部采纳**

1. **a1/b9：reviewer 不该写项目树**。v3.22 用"固定职责授权"让它写 `materials/` 与占位——但设计稿 §4.4 的写者互斥**不因此豁免**，且 reviewer 无 session_key，**附件锁无从谈起**（自相矛盾）。
   → 重写：**主会话在 `review-launch` 一次性物化材料**；reviewer 只在运行态写（占位 `.wf/.runtime/review-claims/`、报告 `.wf/.runtime/review-reports/`，`O_EXCL` 原子创建，无需会话锁）；`review-import` 由主会话校验后**复制**进任务树。
2. **a2：补录实施 CLI 会让既有 pass 失去依据**。`final_gate` 只核 verdict/check id/摘要，不重核实施 CLI。
   → 值实质变化 ⇒ **同批失效 `reviews.result` 与完成回执**，要求重跑 `review-decide`（报告可复用，资格重判）。
3. **a3：轮换会把旧会话的其他活跃调用者带进新对象**（B 未结束却自动解析到 N，且已是 known root，不触发重新启用）。
   → 轮换前置加 **`other_roots(S)` 中无 alive、无 unverified**；不满足则阻断，要求那些调用者先结束或先 start。

**其余 8 项**：a4 一致性只核未完成 action（默认值事后独立变化不算损坏）；a5 S0/S1 收敛（仅"有路由键"不构成曾绑定证据；S0 可复用完整旧附件的 identity）；b1 7c 与矩阵行补"仅 P2 启用时"；b2 §3.4 守卫收窄为 `!known ∧ others_alive==∅`（有存活兄弟根时 unverified 与判定无关）；b3 bind 链补 ⓪意图/④清意图；b4 reason 归因（`|G|==0 ∧ l1 unverified ⇒ evidence_unknown`，不再误报 `other_boundary_alive`）；b5 P2 下 `any_unverified` 排除 l1 维度；b7 R0 必测不可达 ⇒ 该形态按"仅显式模式"发布，不阻塞；b8 `{sid}` 断言收紧；b10 `mark-root-gone` 幂等重跑（有回执即"已处理"）；b11 `state()` 补"附件整体缺失 ⇒ unverified"。

**新增 §3.7f 待裁与回扫补充**：C2（安全承诺弱化）**待裁**；补设计稿 §5.3 新记录类登记、§1.3 活动指针与附件两套运行态文件的关系、O1 的解释性放宽。

文档 1213 行 / v3.23。

## 方案 v3.24（2026-11-08，人裁 C2 = C）

人裁：**C2「复制不构成接管许可」取 C（分级）**。已落账 6 处：

1. **§3.7 C2 行**：改写为分级语义 + 裁决引用（OD-8）；
2. **§2.3d 新增分级规则表**：
   - 当前 root ∈ `S.roots` ⇒ 正常推进（另有存活 root 时披露）；
   - 当前 root ∉ `S.roots` 且无其他存活 root ⇒ 视为重启/续接，走既有降级；
   - **当前 root ∉ `S.roots` 且有其他存活 root ⇒ `BLOCK(concurrent_unregistered_caller)`**，出口＝人调 `start` 显式登记，或结束另一调用者；
   - 同 root 多聊天 ⇒ 合并 + `facts.single_root_multi_chat`；
3. **§5 矩阵行**：「同终端并存两个 agent」由"合并（披露）"改为**阻断（可检测）**；
4. **§9 判据 7** 拆三档（未登记⇒阻断 / 已登记多 root⇒披露 / 同 root⇒合并不可检测），并新增 **7a'** 死锁检查（人登记后两个调用者都必须能正常推进）；
5. **§6 强度④**：明确这是唯一被弱化的部分，且可检测侧已收紧；
6. **`open-decisions.md` OD-8**：原文、冲突、三选项、裁决与连带影响。

**关键理由**：登记只能由**人调 `start`** 产生——这既保住了"复制标识不构成接管"的实质（拷文件无效），又不假装能区分同一进程内的多个聊天。

文档 1216 行 / v3.24。

## 方案 v3.25（2026-11-08，第二十三轮评审后）

**核心（a1/b1 同一处）：C2 规则落在了不会执行的地方**
- C2 表写在 §2.3d（`adjudicate()` 一节），但"同终端未登记第二调用者"走的是**决策表 #1（L1 命中 ⇒ 用 S）**，全程不进 `adjudicate()`；
- 唯一能拦的地方是 §3.4 的 roots 维护，而那里 **v3.24 一个字没改**，伪码在 `!known ∧ others_alive ≠ ∅` 时**直接 upsert** 未登记调用者，然后"披露不阻断"；
- 后果：B 的第一条业务命令就把自己登记进 roots ⇒ 从第二条起 `known` 恒真 ⇒ **阻断永远只在第一条命令前有机会，而伪码恰好放行**。判据 7① 不可实现。

→ §3.4 步骤 3 新增分支（**在 unverified 守卫之后、降级分支之前**）：`!known ∧ others_alive ≠ ∅ ⇒ BLOCK(concurrent_unregistered_caller)`，**不 upsert、不剪枝、立即结束**；并在节首写明"C2 检查必须先于任何 upsert"。
→ 同时把"已登记"改成可机械核对的定义（`当前 root ∈ S.roots`，两处写入来源都可核对），不再声称"人类经 start 认可过"。

**其余**：
- **a2**：reviewer 的占位与报告从 `.wf/.runtime/`（**仍在项目树内**）移到**项目树外暂存目录** `${TMPDIR:-/tmp}/wf-review/<project-hash>/<task>-<round>-<as>/`；项目内只留一行定位；导入时文件不在 ⇒ 拒绝并提示重跑 context。
- **a3**：附件整体缺失会让 `adjudicate()` 先 BLOCK，`start` 进不到 §3.5 重建（**恢复入口要求附件先完整**）⇒ 明确区分"识别待恢复候选"（start，需人确认+核 binding+核写权）与"批准推进"（业务命令仍阻断）。
- **a4**：审查失效改为**改现有状态**（`reviews.result.verdict = invalidated` + `status`），`final_gate` 只认 `verdict=="pass" ∧ status=="valid"`；action 前像/后像覆盖四处；重入核验后像完整性。
- **b 小项**：删掉 `facts.single_root_multi_chat`（不可检测 ⇒ 无产生机制，假披露面）；判据 4 的 `{sid}` 断言改条件式并交 R0-A2 声明；判据 8 与 7① 对齐；矩阵 l1-drift 补"仅 P2"；`mark-root-gone` 排除附件缺失并指向 §3.5；materials 明确不提交；**C1 升为待裁**（与 C2 同属身份契约本体）。

文档 1240 行 / v3.25。

## 方案 v3.26（2026-11-08，第二十四轮评审后）

| # | 问题 | 处理 |
|---|---|---|
| a1/b1 | **staging 改名 `report.md` 却仍按文件名取身份** ⇒ 两条规则互斥；占位记录还留着树内旧路径 | 统一为 **`<staging>/…/review-<as>.md` + `.claim-<as>.json`**（身份仍由文件名承载，归档后同名）；§3.7d 三点表与 §3.7a 的 import token 行同步 |
| a2/b2 | 新门禁 `verdict=="pass" ∧ status=="valid"` 引入**没人产生的 `status`**，且与"改 verdict 为 invalidated"两处编码不一致；存量记录无该字段会导致**历史 pass 全失效** | **只保留 `verdict`**（`pass\|fail\|invalidated`），`final_gate` 只认 `pass`；**无需迁移**（旧记录本就只有 pass/fail） |
| a3/a4/b3/b4 | start 越过 `evidence_unknown` 的规则**没把限定写进规则本体**：多候选（共享 L2）时不知该恢复哪个；hidepid 类 unverified 也会被这条通道放开，架空 I2 | 规则本体加三条前置：**候选唯一** + **确由候选附件整体缺失引起** + binding/写权核对；**多候选不越过**（人指认）；**附件完好但根不可读 ⇒ 不越过**（走 `mark-root-gone`）；**S0 不在本规则范围**（无 binding 可校） |
| b5 | 判据 8c（"两并发调用后集合含两根"）与 C2 阻断冲突 | 改为"**两个已登记的调用者**并发"；未登记者按 C2 阻断、不产生 upsert |
| 小项 | 两条新门禁无验收行；`concurrent_unregistered_caller` 未登记；矩阵 leader 行未注 C2；§8c 缺四项；I4 范围不含 §3.4 阻断；暂存清理归因不准 | 补 15f–15h；reason 表加行（既有码下的新 reason 值）；矩阵行补注；§8c 加四行；I4 扩到 §3.4 两个阻断；`no_claim` / `staging_evicted` 两因 |

文档 1275 行 / v3.26。

## 方案 v3.27（2026-11-08，人裁 C1 = ①）

人裁 **C1 取 ①（执行边界粒度）**。已落账：

1. **§3.7 C1 行**：改为"已裁 ①"，并写明使用约定（**一个终端同时只干一个任务**）；
2. **新增 §3.7g**：给出 R5 的**逐字改写文本**——
   - 设计稿 §1.3 身份句新文（含"同一进程多聊天无法区分"的显式声明与 C2 分级引用）；
   - environment 行新文（"多执行边界分别绑定；同一边界内只有单一绑定"）；
   - 三份 skills 的"工作习惯"加句（并行请另开终端）；
   - **4 类 8 项连带核对清单**（设计稿 §1.3/environment/§8.2/索引、机制稿 §1.4、实现稿命令表、三份 skills）；
3. **§3.7f 待裁清单**：C1 划掉（OD-9），现存三条裁决记录（OD-7/8/9）；
4. **`open-decisions.md` OD-9**：三选项（边界/进程/聊天）+ 代价对照 + 裁决理由。

副作用说明（写进文档）：同终端第二个 agent 在 C2 下被阻断，人 `start` 后放行，**此后与第一个共享同一会话**——这是 ① 的必然结果，不是缺陷。

待裁项现在只剩：**C3 / C5 / C6 的落账确认**（方向明确，R5 同批改文）。R0 仍是实现前的硬门。

## 方案 v3.28（2026-11-08，第二十五轮评审后）

**a1/b1 同一处，第 4 次回扫遗漏**：v3.26 把暂存布局改成"文件名承载身份"（`review-<as>.md` + `.claim-<as>.json`），
但**同一节的写入边界表**仍是 v3.25 的"目录承载身份"（`<as>/claim.json` + `report.md`）——两种布局的 `O_EXCL` 作用对象都不同（文件 vs 目录），R3 无法同时满足。
→ 写入边界表两行改为新布局；并做了一次**全文路径扫描**（`review-claims|review-reports|claim.json|report.md|<as>/`），确认无第三处残留。

**a2**：`verdict` 新枚举把**既有的 `unavailable`** 吞掉了。核实机制稿 :734 与 `review.py:592`：`result` 保存 `pass/fail/unavailable`，`gates.py:676` 据此区分"审查不可用"与"审查不合格"。
→ 枚举改为 **`pass | fail | unavailable | invalidated`**，`final_gate` 仍只认 `pass`；兼容缺省说明改为"存量本就只有 pass/fail/unavailable，无需迁移"。

**b2**：§3.7g 清单只覆盖 frontmatter 的 `environment:`，漏了设计稿 **§3 正文「使用环境」句**（同一事实的第二份表述，:131）。
→ 两处**逐字新文**都写出，核对清单加一项。

**小项**：`status` 残留清干净（result 只写 `verdict`）；`concurrent_unregistered_caller` 的登记位置改指向本节（§4.2c）而非错指 §4.2b 的 `WF_NOT_ENABLED` 表；§8c 两处验收错引（15g/15f）改正；暂存清理双因给出判别规则（**目录整体消失 ⇒ 只能报 `no_claim`；报告在而 claim 不在 ⇒ `staging_evicted`**）；矩阵 leader 行注明该路径 reason 是 `other_root_alive`（`concurrent_unregistered_caller` 只来自 hit #1 分支）；15g 补注 S3/S4 同属该规则、由 R2 用例覆盖。

文档 1298 行 / v3.28。

## 方案 v3.29（2026-11-08，第二十六轮评审后）

评审指出 §3.7g ①"逐字改写"本身不可执行——**这条本来是给 R5 机械执行的**，所以三处都成立：

| # | 问题 | 修法 |
|---|---|---|
| a | 引用里用"……"省略了「宿主不能提供时，使用 wf 显式签发……」⇒ R5 无法判断省略部分保留还是删除 | 给出**完整原文（无省略）**，并写明**替换范围**：只替换前两句，其后「绑定记录同时保存……」与「能力、传递与恢复方式……」**原样保留** |
| b | 新文只写自动模式 ⇒ 显式 legacy 模式的身份定义会随整句替换而**消失**（它只在机制稿 §1.4 有落点，而设计稿才是唯一定义处） | 新文补**显式模式分支**：仍采用宿主提供/请求携带的标识，语义见机制稿 §1.4，退役条件见 §4.1 |
| c | 原文「后者是**路由标识而非凭据或人批准证明**」在新文里没有对应物 | 新文补回该限定，并明确它同时适用于两种模式——这也正是 C2「复制不构成接管」的论证地基（OD-8 的前提） |

核对清单同步加一项：「§1.3 后两句保持不变」。

文档 1310 行 / v3.29。

## S1 执行：拆文档（2026-11-08，v3.30）

按终局评估的建议，把**审查子系统**三节从身份方案拆出：

| 内容 | 去向 |
|---|---|
| C6 实现修改点清单（`review.py:281/:140/:601`、CLI 参数、launch schema、import 署名、help） | `review-identity-protocol.md` §1 |
| `--as` 三点一致性（context 占位 → 文件名 → import 校验） | 同文 §2 |
| `review-launch` 跨文件事务（action 意图/前像/后像/四种重入） | 同文 §3 |
| 契约 C6 行、§8c 两行交付状态、判据 15f | 身份方案保留**引用**，细节指向新文 |

结果：身份方案 **1215 行**（原 1310，−95），回归单一议题；新文 **128 行**，自带议题边界表（"属于本文/不属于本文"）。

## S2 执行：R0 本机部分（2026-11-08）

`r0-run.sh` 实跑 9 个场景，结论表见 `r0-results.md`：

| 环境 | 结果 |
|---|---|
| **A1 单聊天 agent 宿主** | L1 `a78cac38…` 稳定 ⇒ **支持（P1）** |
| B1 bash/zsh/嵌套 | 同一 L1 ⇒ 支持 |
| **A3 setsid 每命令** | L1 每次变、L2 同一 ⇒ **仅 P2** |
| B6 systemd-run --scope | 继承发起终端 ⇒ 同一执行会话（须声明） |
| B5 docker run（容器 pid1） | 无锚 ⇒ 不支持 |
| **B4 docker exec -t ×2** | `sid=7`→`sid=13`、L2 无 ⇒ **不支持**（实测修正：之前用 stub 误报"稳定"） |
| B7 leader 先死 | reparent 到 systemd、`parent==init` 被拒 ⇒ 无锚 ⇒ 不支持 |

**R0 未完成**：A2（同守护进程多聊天，必测）、B2（tmux）、B3（IDE 终端）无数据 ⇒ 按 §2.4b 不得写入"支持环境"表。

**自伤记录**：第一版 `r0-run.sh` 的 docker-exec 场景用了手写 stub（恒定 `l1_stable=true`），
掩盖了"两次 exec 得到不同 sid"这一关键事实；改用真实两次 `docker exec -t` 后修正。

## S2 续：人工结果回收（2026-11-08）

| 环境 | L1 | L2 | 结论 |
|---|---|---|---|
| **B2 tmux 两 pane** | `9c96747e…` / `772e9e04…`（不同，各自稳定） | **None** | **支持（P3：只有 L1）**——`tmux` 在工具表内、其后直达 pid1 ⇒ 无 L2 兜底 |
| **B3a IDEA 终端** | `d2b27994…` 稳定 | `2b5b4bdd…`（`idea` 进程） | 支持（P1） |
| **B3b Zed 终端** | `1c1c6661…` 稳定 | `307caba3…`（`zed-editor`） | 支持（P1） |
| 两个 IDE 之间 | 不同 ✓ | 各自 IDE 进程 | 不同边界可区分 |

**新读数**：IDE 的 L2 就是 IDE 进程本身 ⇒ **同一 IDE 实例的所有终端共享同一 L2**；IDE 内必须靠 L1 区分终端，L1 一旦不可用，L2 会把整实例的终端混成一个（正是 owners + attached_l1 要裁决的形态）。两个 IDE 的 `tty_nr` 相同（`/dev/pts/7` 复用）⇒ 再次印证 tty 不能作身份。

**A2 仍未测**：用户给的是"终端标签里手跑"（B3），不是"同一进程内两个聊天由 agent 执行"（A2）。已在 `r0-results.md` §三 与 `r0-manual-steps.md` §0 写明判据与方法。

**ssh -t 说明**：探针是单文件纯标准库、只读 `/proc`，**不需要拷项目代码**；给了三种跑法（stdin 管道 / scp 单文件 / 远端 python3 探测）与观测判据（同连接两次同键、两条连接不同键）。CI runner 用户没有 ⇒ 按 §2.4b 记"未验证"，不阻塞。

## R0 完成（2026-11-08）

**A2（zcode 两个会话）**：
- 会话 1：L1 `3d4cb3fc…`（sid 3026948, leader zsh）、L2 `9387fc94…`（zcode pid 1023974）
- 会话 2：L1 `a6683247…`（sid 3027029）、L2 **同一** `9387fc94…`
⇒ **L1 不同（R0-B 通过）**；**L2 相同（同一宿主进程多主）**——正是 owners + attached_l1 覆盖的形态。
**部署前提**：宿主须为每聊天派生独立 shell/pty；若宿主直接用自身 session 执行命令，两聊天会同 sid ⇒ 合并（§2.4c "部署前提"类）。

**ssh -t**：单连接内 L1 `38219b5a…` 稳定、L2 = `sshd`（每连接一进程）。跨连接对比属可选，未做。

**R0 判定：完成**（必测 A1/A2/A3/B1/B7 全部有结论）。
**支持环境清单**（写进 `r0-results.md` §九）：
- 完整 P1：终端单聊天、zcode 多聊天（前提同上）、IDEA/Zed 集成终端
- 受限 P3（只有 L1）：tmux 多 pane
- 仅 P2（默认关闭）：逐命令新会话的执行服务
- 同一执行会话：systemd-run --scope
- 不支持（显式模式）：docker exec -t、docker run、leader 先死/后台化
- 未验证：CI runner、Windows/macOS

**§10 待裁项 2b 关闭**：R0 证明 zcode 两聊天 L1 可分 ⇒ 不需要"共享宿主一律显式模式"。

**S3 分叉结论**：A1 成立（且 A2 亦成立）⇒ **自动模式继续，进 R1**。

## R1 完成：`session.py` 锚点与唯一裁决（2026-11-08）

**实现**（`payload/lib/wflib/session.py` 追加，396 行 → 约 640 行）：

| 组成 | 内容 |
|---|---|
| `SHELLS_OR_UTILS` | 工具分类常量（`basename(readlink(exe))` 全等匹配，§2.2c 口径） |
| `Probe` | 读取 `/proc` 的唯一入口（`stat_of`/`exe_of`/`name_of`/`boot`），**测试可注入** |
| `l1_anchor()` | `getsid(0)` 会话 leader + `sid_start`；不用 tty（R0 实测 pty 复用） |
| `l2_anchor()` | 最近长命非工具祖先；跳过**同一解释器可执行文件**的祖先（不按名字前缀，避免跳过 python 系 agent）；排除 pid1/内核线程/init 直子 |
| `candidates()` / `anchor_key()` | 键 = `SHA256(C({boot,…}))`；sid/pid 两型 |
| `state_of_l1()` / `state_of_root()` | **三值证据**：null/ENOENT/start 不符/zombie/boot 不同 ⇒ gone|dead；读不到 ⇒ unverified；sid 型按 `(boot,sid,sid_start)` 全等 |
| `other_roots()` | 唯一根集合定义 |
| `adjudicate()` | 唯一裁决：`USE/NEW/BLOCK(evidence_unknown|ambiguous_shared_root|other_boundary_alive|other_root_alive)`；P2 在函数内放宽 `G=C` 并排除 l1 维度 |

**单测**：`scripts/tests/test_wflib_session.py`，**31 项全绿**（Keys 3 / L1State 8 / RootState 4 / OtherRoots 2 / Adjudicate 12 / RealProc 3）。
注入 `FakeProbe` 覆盖每个 verdict 分支，含 R0 实测形态：zcode 双聊天（L1 不同、L2 同）⇒ 不 USE。

**回归**：`WF_JOBS=1 run_all.sh` **129 项 0 失败**；三稿校验通过；字节复现 OK（56 assets）。

### 过程中发现并修复的一个真缺陷（与 R1 无关）

回归先报 `R92b 技能副本不被算作任务交付物: b=59 c=1`。定位：
**全新安装会新建 `.gitignore`（未跟踪）**，而 `_is_control_record` 不含它 ⇒ 判成"未归属改动"，
意味着**任何新项目第一次 Check 都会把它报成外部变更**。

修法（`scope.py`）：新增 `_gitignore_is_framework_only(root)`——**只在 `.gitignore` 除托管段外没有其它行时**才归框架控制面
（用户自己加过内容则不隐藏），并给 `_is_control_record` 增 `root` 参数。修后 129 项全绿。

**自伤记录**：我在定位时先怀疑 R1，用"把 session.py 回退到 HEAD 再跑"排除了它；随后又先写了一个引用未定义 helper 的草案（已废弃），才落到内容判定这个正确口径。

## R2 完成：路由/状态存储与 roots 维护（2026-11-08）

**新增模块** `payload/lib/wflib/identity_store.py`（已登记 dev-manifest，release 56→57 assets）：

| 组成 | 内容 |
|---|---|
| 路由 | `load_routes/save_routes`（`.wf/.runtime/anchors.json`，结构破损 ⇒ `StoreError`） |
| 所有权 | `register()`：**L1 单主**（已有其它 owner ⇒ `StoreError`）、**L2 追加不覆盖**；`owners_of`、`routes_of_session` |
| 轮换 | `replace_owner(old,new)`：遍历全部条目只换该 owner、保留其它（§3.3） |
| 状态 | `attachments/<session_key>.json` 单份；`new_attachment` 同时存 `provider + identity + session_key`；`verify_attachment_identity()` 校验 `SHA256(C({provider,identity}))==session_key`（I5） |
| roots 维护 | `maintain_roots()`：**snapshot → 判定 → 维护**；`unverified` 需旧根证据 ⇒ 阻断且**不 upsert**；`!known ∧ 有存活兄弟根` ⇒ **C2 阻断且不 upsert**；旧根全 dead ⇒ 置 `activation_stale` 后 upsert；只剪 confirmed dead（unverified 保留） |
| 五态 | `five_state()`：S0/S1（`instance_expected` 有值或历史）／S2/S3/S4（按 `object_terminal` 与 `holder`/`recovering` 是否指向本会话） |
| 恢复前置 | `can_override_evidence_unknown()`：**候选唯一 + 确由附件缺失引起**才允许 `start` 越过 |
| 迁移 | `valid_sessions`（以**已提交路由**为准）、`migration_candidates`（含当前 root 且 root 存活、排除 `superseded_by`） |

**单测** `scripts/tests/test_identity_store.py`：**19 项全绿**，关键断言：
- C2 阻断后 **roots 里没有新 root**（防止"拒一次却登记了"的绕过）；
- `unverified` 阻断后 roots 原样；
- 死根被剪、unverified 保留、已登记多 root ⇒ 披露不阻断；
- 轮换后 `{A,B}→{N,B}`；
- 无效会话（无路由）不进迁移候选。

**回归**：129 项 0 失败；三稿通过；字节复现 OK（**57 assets**）。

**自伤 1 处**：`maintain_roots` 的 known 分支起初只替换当前 root、**没有剪死根**，被单测
`test_known_root_with_dead_sibling_is_normal` 抓住；改为统一"按快照逐条判死、只保留 alive/unverified"。

## R3 完成：CLI 自动身份模式接线（2026-11-08）

**目标**：`/wf-start` 之后不再需要手写信封；**显式模式完整保留**（存量项目与 129 项夹具不受影响）。

| 改动 | 内容 |
|---|---|
| `Context.explicit_session()` | 信封里**有 session 对象**才算显式模式；否则返回 None |
| `Context._auto_resolve()` | 锚点解析：L1 单主命中即用；否则按 L2 的 owners 调 `adjudicate()`；未命中返回 (None,None) |
| `Context.auto_session()` | 由附件合成 `{provider:"wf", identity, instance_id, activation, source:"auto"}`；`activation_stale` ⇒ `WF_NOT_ENABLED` |
| `Context.session()` | 显式优先 → 自动 → 都没有则 `WF_IDENTITY_UNRESOLVED`（给"重跑 /wf-start / 用显式信封"两个出口） |
| `_establish_auto_session()` | 首次 `enable`：签发 `issued_id`、写附件、登记 L1 单主 + L2 追加；**先写附件、后提交路由** |
| `session.check_platforms()` | `source=="auto"` 放行（本地已自校验）；**显式 wf 信封仍拒绝**（保住 r81 A6d） |
| `cmd_enable` | 自动模式且无路由 ⇒ 本次即建立会话；响应新增 `identity_mode: auto|explicit` |

**端到端实测**（`/tmp/amode`，全新安装）：
- 自动 `enable`（**空 stdin**）⇒ `WF_OK`、`identity_mode=auto`、生成 1 份附件与 2 条路由（L1+L2）；
- 连续三次 `enable` ⇒ **同一 session_key、附件数仍为 1**（L2 owners 复用生效）；
- `{"inputs":{"generation":2}}` + `task-new` ⇒ `WF_OK`（业务命令在自动模式下可用，`generation` 仍必填）；
- 显式信封 `enable` ⇒ `WF_OK`、`identity_mode=explicit`（旧通道未破）。

**回归**：129 项 0 失败；字节复现 OK（57 assets）；三稿通过。

### 三处自伤（都被测试/实测抓住，已修）

1. **`join(root, *parts)` 参数错**：`identity_store.routes_path` 用了 `join(root, *rel.split("/"))`，而 `paths.join` 只收 `(root, rel)` ⇒ `enable` 直接 internal error。
2. **锚点 kind 过滤写错**：`_auto_resolve` 用 `item["kind"] == "proc"` 找 L2，但锚点 kind 是 **`pid`**（`proc` 只是路由 `via`）⇒ L2 owners 永远查不到，每次 `enable` 都新建会话（附件数 2 而不是 1）。
3. **`ENOENT` 被当成"读不到"**：`Probe.stat_of` 让 `FileNotFoundError` 冒泡成 OSError ⇒ `state_of_l1` 判 `unverified` ⇒ 死掉的 leader 变成"证据未知"、续接被阻断（正是文档 §2.3d 三值要防的那件事）。改为 `ENOENT/ProcessLookupError → None`，并补回归用例 `test_missing_pid_is_none_not_error`。

**契约变更一处（已在测试里如实改口径）**：`r86` 的"stdin 无管道时明确报错"原断言 `must be piped on stdin`；
自动模式后改为断言"**解析失败即 `WF_IDENTITY_UNRESOLVED` 并给出口**"（不再静默挂起），注释记录了变更依据。

## R4 完成：自动模式的运行级用例（2026-11-08）

新增两条 repro（repro 用例 65 → **67**，131 项全量）：

| 用例 | 断言 |
|---|---|
| `repro/auto-identity-zero-input.py` | **零输入** `enable`（无 session 对象、空 stdin）⇒ `WF_OK` + `identity_mode=auto`；生成 1 份附件与 `anchors.json`；**重复 enable 同 session_key、附件数仍为 1**；随后 `task-new`（只带 `inputs.generation`）可跑通 |
| `repro/auto-identity-gates.py` | 自动模式下两道闸门仍生效：①`activation_stale` ⇒ `WF_NOT_ENABLED(activation_stale)`；②未登记的第二调用者（同会话另有存活根）⇒ `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)`（C2/OD-8） |

**R4 暴露并修掉的实现缺口（重要）**：R3 只接了"身份解析"，**`maintain_roots` 从未被 CLI 调用** ⇒
`activation_stale` 不会被业务命令置位、C2 在 hit 路径上永不触发（闸门 2 的用例一开始直接 `WF_OK` 通过）。
→ 在 `Context.session()` 里对**写业务命令**（`ROOTS_COMMANDS`，按 §4.2b 四分类）执行 §3.4 roots 维护：
`block` ⇒ 结构化 `WF_IDENTITY_UNRESOLVED`（C2 / evidence_unknown，各自带出口）；`stale` ⇒ `WF_NOT_ENABLED`；并把维护结果写回附件。

**另两处自伤**：
1. `_needs_roots` 起初读 `self.args.argv[0]`——而 `Args` 收的是**去掉子命令之后**的参数 ⇒ 永远匹配不上；改由 `dispatch` 把 `ctx.command` 记下来。
2. 闸门 2 的夹具原用"本测试进程"当存活根；在 `/softwares/python` 下它恰好可能成为 CLI 的 L2 锚 ⇒ `known=True`、C2 不触发（用例假绿/假红）。改为起一个 `sleep` 子进程当"另一个存活根"。

**验证**：repro **67/67**（每条同时过 green 与 red）；全量 **131 项 0 失败**；字节复现 OK。

## R5 完成：三稿与 skills 落账（2026-11-08）

按 `identity-redesign.md` §3.7g 的**逐字文本**改文：

| 文档 | 改动 |
|---|---|
| 设计稿 frontmatter `environment` | `多会话分别绑定` → **`多执行边界分别绑定（同一边界内只有单一绑定）`** |
| 设计稿 **§1.3 会话身份** | **只替换前两句**：自动模式（执行边界粒度）+ 显式 legacy 模式（保留宿主/携带语义）+ **「路由标识而非凭据」限定**；后两句（绑定实例标识、能力/恢复出口）原样保留 |
| 设计稿 **§3 正文「使用环境」句** | 同步为"多执行边界…同一边界内只有单一绑定（一个终端同时只干一个任务，并行另开终端/窗口）" |
| 设计稿**索引** #112 | 消费点列补"§1.3 粒度=执行边界（自动模式锚点派生／显式模式保留）" |
| 机制稿 **§1.4 activation** | 拆两种模式：显式模式仍由宿主携带；**自动模式由入口写入 `attachments/<session_key>`（运行态、gitignore）** |
| 机制稿 **D14** | 「wf 自签发属第二轮」→ **「已提前到第一轮（OD-7）」**，旧口径作废 |
| 机制稿 **§0.1 输入摘要** | 更新 design / index 两份摘要 + 记录本轮修订说明（改设计稿 §1.3、environment、§3 使用环境） |
| 实现稿 **§2.2** | 标题与内容改为"两种模式互斥"：显式 vs 自动（来源、`generation` 仍必填、roots 维护的三种返回码、首次 enable 建立会话） |
| skills `wf-start` | 第 5 步改为"自动模式不需要手写信封"；显式模式步骤顺延；新增 **「工作习惯」**（一个终端一个任务、第二个 agent 须人 enable 后共享会话） |
| skills `wf-continue` / `wf-finish` | 同款「工作习惯」段 |

**校验**：`validate-wf-design.py` 通过（定义位点 51+7、索引 143 行、三率 100%、输入摘要 4/4）；
字节复现 OK（57 assets）；全量 **131 项 0 失败**、repro **67/67**。

**两次校验打回（已修）**：①机制稿新增句里裸写 `§3`/`§3.7`/`§2.2` 被"引用缺所有者"规则拦下——
机制稿只能以「本文/设计稿」作所有者，最终改为不带 `§` 的措辞；②改索引后 `wf-framework-design.index.md` 摘要不符，同批更新基线。

## R6 完成：收口（2026-11-08）

**1. dogfood 清单更新（步骤 3 正式移除）**
- `dogfood-plan.md` §10.2 改为"**不需要任何手写信封**"，说明自动模式的三件事（锚点派生、运行态附件、`generation` 仍需携带）；
- 新增 **§10.2b 失败出口**：按错误码处置（无锚点 / C2 未登记调用者 / 证据未知 / activation_stale / activation_missing），**都不要求手写信封**；
- 新增 **§10.2c 支持的宿主形态**（引 R0 结论表）。

**2. §8c 交付状态改为实测**
| 项 | 状态 |
|---|---|
| `session.py`（锚点 + `adjudicate`） | 已实现（单测 32） |
| `identity_store.py`（routes/attachments/roots/五态/迁移） | 已实现（单测 19） |
| CLI 自动模式 + roots 维护 | 已实现（2 条 repro） |
| 三稿 + skills 落账 | 已同步（validate 通过） |
| `repair --mark-root-gone` / `identity-path --set` / C6 审查身份 | **未实现**（协议与验收已定，不阻塞 dogfood） |
| R0 结论 | 已完成 |

**3. 最终验证门（全部通过）**
| 门 | 结果 |
|---|---|
| R1 单测 | 32 项 OK |
| R2 单测 | 19 项 OK |
| 全量 `WF_JOBS=1 run_all.sh` | **131 项 0 失败** |
| repro | **67/67**（每条同时过 green/red） |
| 字节复现 | OK（57 assets） |
| 三稿校验 | 通过（定义位点 51+7 / 索引 143 行 / 三率 100% / 输入摘要 4/4） |

**R1–R6 全部交付完成。** 交付物：`session.py`（锚点+裁决）、`identity_store.py`（记录层）、CLI 自动模式接线、
2 条运行级 repro、2 个单测文件（41 项）、三稿与三份 skills 的文本落账、`r0-results.md`、`final-assessment.md`。

## dogfood 预演（2026-11-08，/tmp/smoke 全链路）

按 dogfood-plan §10.2 在全新项目里走了一遍真实链路（安装 → confirm-executor → `wf-start` → `task-new` → PRD → `task-approve` → `task-start` → `task-check`）。

**抓到并修掉一个真 bug（R3 遗漏）**：`task-new` 写绑定时**没有把首次绑定的 `instance_id` 写回附件**（§3.6 的二段写回从未接线）
⇒ 下一条命令 `session.instance_id` 仍为 null ⇒ `task-approve` 报 `WF_IDENTITY_UNRESOLVED(instance_id not carried by request)`。
修法：`identity_store.sync_attachment_instance()`（不自造 ctx 依赖），`tasks.py:1410`（task-new 首次绑定）与 `cli.py:992`（bind）两处调用。
修后：`task-new → approve → start → check` 在自动模式下全部可达。

**结论：链路可用，但完整 dogfood 仍有一处硬阻塞**：
`review-context` 在自动模式下返回 `WF_IDENTITY_UNRESOLVED(reviewer session lacks host identity)`——
C6（审查参与者身份：`--as` / `--implementation-cli` / verdict 失效）尚未实现，属 `review-identity-protocol.md` 的 R3 交付。
另：`dogfood-plan §10.2b` 里写的 `repair --mark-root-gone` 尚未实现（文档与代码不一致，需标注为"未接线"）。

**验证**：全量 131 项 0 失败、repro 67/67、R2 单测 19 项 OK。

## C6 交付（2026-11-08，原"完整 dogfood 的硬阻塞"）

**产品改动（`review.py` 为主）**

| 项 | 做法 |
|---|---|
| 参与者身份 | 新增 `review_cli()`（归一 + 校验 `[a-z][a-z0-9-]*`）与 `participant_cli(ctx, --as)`：**`--as` 优先**，显式模式回退信封 `host_id`（存量兼容），都没有 ⇒ `WF_IDENTITY_UNRESOLVED` 并给出两个出口 |
| 报告路径 | `review-context --as pi` ⇒ `review-<pi>.md`（文件名即身份），不再依赖 host_id |
| 实施 CLI | `review-launch --implementation-cli <cli>` **必填**；旧 `implementation_clis` 数组仅兼容读，与单值冲突即阻断；记录 `implementation_cli` + `declared_at` + `declared_by` |
| 判定 | `review-decide` **只读 launch 记录**；缺失 ⇒ 拒绝给 pass；**删掉**了判定期从会话猜并回写记录的旧逻辑（补丁式行为的根源） |
| 失效链 | 换实施 CLI ⇒ 既有 `reviews.result.verdict` 同批改 `invalidated`（`invalidated_reason`/`invalidated_at`）；`final_gate` 本就只认 `pass`，无需改门禁 |
| 导入三点一致性 | `--as` 与文件名/`--slot` 冲突 ⇒ 阻断；从未调过 context ⇒ `no_claim`；占位在但未 done ⇒ `staging_evicted` |

**一处实现层面的对齐（写进协议文档）**：占位不是独立 `.claim-<X>.json`，而是 `review-context` 写下的**报告骨架本身**（`status=in-progress`）。
协议文档已改为事实描述，避免"文档要求一个不存在的文件"。

**新 repro**：`repro/review-identity-c6.py`（green/red 双过）——覆盖：未声明实施 CLI 被拒、`--as` 优先于信封 host_id、无占位报 `no_claim`、
判定给出 pass、换实施 CLI 后 verdict 变 `invalidated`、且**不得出现第二状态字段 `status`**。

**实测链路（`/tmp/smoke2`，自动模式）**：enable → task-new → approve(complex) → start → task-check(`--review-notes`) →
`review-launch --implementation-cli codex` → `review-context --as pi` / `--as zcode` → 写报告 → `review-import` → `review-decide` ⇒ **pass**；
再以 `--implementation-cli pi` 重发 ⇒ **verdict=invalidated**。

### 自伤 3 处（都记下来）
1. 新函数取名 `declared_cli`，**与既有局部变量同名** ⇒ 函数体内该名被判定为局部变量，5 条 review repro 全崩（`cannot access local variable`）。
   改为 `review_cli` 并只替换模块级调用点，未改既有局部变量。
2. `review-filename-identity` 夹具靠旧的 host_id 推断实施 CLI ⇒ 现在必须声明，已在该夹具补 `--implementation-cli dsh`（契约变更，非放宽）。
3. 首版 repro 把 `context` 失败写成 `Precondition`，注入后变成"夹具坏了"而不是"缺陷被抓到" ⇒ red 判定失真；改为计入目标断言。

**验证**：全量 **132 项 0 失败**、repro **68/68**、三稿校验通过、字节复现 OK（57 assets）。

## 执行器形态修正（2026-11-08，非补丁：接上已有机制）

**触发**：dogfood 在 Codex 里第一步就撞墙——`python3 .wf/bin/wf.py enable` 被宿主的 execpolicy 拒绝
（`~/.codex/rules/hardened.rules` 第 0 条：裸 `python3` = `prompt`，`/softwares/python/bin/python3` = `allow`；
审批策略 `Never` ⇒ 直接拒）。**这不是 wf 缺执行器机制**：`wf.py` 早已有
「项目 `python_executable` → 全局 `~/.wf/config.json` → 系统 `python3`」的解析、`~/.wf/interpreters.json` 确认记录、
以及 `os.execve(candidate, …)` 移交（`payload/bin/wf.py:173/515/542`），设计稿 §1.1 也写全了。

**真正缺陷有两处，都是"文档/提示把入口解释器写死成 `python3`"，绕过了已有机制**：

| 位置 | 改法 |
|---|---|
| **11 个 SKILL.md** 的纪律行「命令一律形如 `python3 …`」 | 改为 **`<python>`** 并按序取值：① 项目 `python_executable`（未设置读全局键，**可直接读文件取值，不必先执行**）② 调用方自身运行时的 Python ③ 系统 `python3`；**取到能跑的就整会话固定复用**；被策略拒绝时改用策略允许的已核实绝对路径，**不要每条命令换解释器**、不要因被拒就改写信封 |
| `payload/bin/wf.py` 的出口提示 `"人执行：python3 .wf/bin/wf.py confirm-executor …"` | 改为拼接 **`sys.executable`**（刚跑通 wf.py 的那个解释器必然在本环境可用）；版本不足的提示也不再指向 `python3` |
| `payload/install.py` 的 `recovery.md` 模板（`python3 <abs>/wf.py status`、`python3 repair.py`） | 改为 `<python>` + 一句取值说明 |
| 实现稿 §2.3 的入口命令表 5 行 | 同步为 `<python>` |
| 设计稿 §1.1「命令启动」 | `python3 .wf/bin/wf.py <操作>` → **`<解释器> .wf/bin/wf.py <操作>`**，并写明缺省系统 `python3`、可为已配置执行器或人给的已核实绝对路径、**调用形态不构成身份或权限来源**；机制稿 §0.1 输入摘要同批更新 |

**为什么这不是补丁**：执行器解析/确认/移交本来就有；此前只是**入口形态在技能里被写死**，导致机制被绕过。
现在技能、运行时提示、恢复说明、三稿统一到「`<python>` 由配置/确认状态决定」这一条口径，没有新增概念、没有新增回退档。

**验证**：全量 **132 项 0 失败**；repro **68/68**；三稿校验通过；字节复现 OK（57 assets）。
发行内 `skills/wf-start/SKILL.md` 已含新口径（已核对产物）。
