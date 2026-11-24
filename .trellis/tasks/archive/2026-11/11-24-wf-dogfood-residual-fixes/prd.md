# wf dogfood 残缺口修正（材料身份 / 启用前置 / 批准摘要）

## Goal

以 2026-11-08 traffic_monitor 四会话 dogfood（真实使用）为证据，修正 `docs/workflows/wf/` 当前版本里
**仍然存在**的机制缺口与指引漂移；同时按"可稳定计算且改变实际动作的进机制、其余留指引"的既定分工
复核设计稿 §1.1 的 AI 指导要点，只改不准的表述，不加层级、不加 skill。

## Background

### 证据

- 四份会话全文：`/tmp/traffic_monitor_1.md`（bootstrap + 代次/决定返工）、`_2.md`（禁写 `.wf/`）、
  `_3.md`（新会话仍命中旧绑定）、`_4.md`（两轮上限死锁、格式返工链、`pass` 后修建议失锚、
  用户两次催"为什么只登记不修"、`.unipi`/`.gitignore` 工作区门禁、8 轮 16 份报告后 pass）。
- 两位 agent 的当前版本分析：报告 a（结论"10 项全部解决"）、报告 b（4 条 P1/P2 残缺口）。
  **按质疑口径逐条复核**，不采信结论。
- **缺失输入（如实声明）**：`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`、`~/.zcode/cli/log/zcode-2026-11-08.jsonl`
  在本机已不存在（`ls` 确认；日志目录最早为 11-17）。上一轮对它们的采信只能经
  `docs/workflows/wf/analysis/dogfood-round5-dispositions.md` 转述，本任务不复核原件。

### 复核结论（对两份报告的判定）

**报告 a 的可靠面**：下述均已独立核实成立——`report_input_problems()` 是 lint/import/decide 的唯一
实现（`payload/lib/wflib/review.py:319`、`3988`）；轮次不设上限（`review.py:2627` 注释 + `round_ids` 只作观察）；
`review-restart` / `review-reauthorize` / `reopen-reviewed` 已不存在（`grep` 零命中）；`task-rework` 已真实现
（`tasks.py:5184`）；`resolve_generation` 缺省取会话运行态代次（`cli.py:27`）；`materialize_delivery` 对未跟踪
文件用 `git diff --no-index`（`review.py:2746`）；`workspace_exclusions` + `--workspace-exclusion` 存在
（`cli.py:3848`）；`task-approve --draft` 存在（`cli.py:2751`）。

**报告 a 的失真面**：① a 称 `review-restart` 等"不再需要存在"，方向对但漏了**新会话/启用侧**仍留缺口
（见 F2、F3）；② a 未发现任何新问题，与"当前版本零 dogfood 实证"自评矛盾——它承认没实证，却把
"机制与指引落点已闭合"当成"AI 发挥已改善"；③ a 对 `scope-exceptions` 的判断正确，但把
"骨架预填 excluded-scope"当成格式链已彻底解决，漏了 F1 的材料身份面。

**报告 b 的可靠面**：F2（`enable --new-session` 跳过互斥核对）、F3（空 `object_digest` 仍可批准）、
F5（导入示例不给 `--round`、bootstrap 五类清单漂移）均复核成立。

**报告 b 的失真/不足**：① b 说"报告骨架和导入记录只绑定任务、轮次与 Check 锚点"，准确；但它给的出口
"恢复原包或产生真实的新审查"没考虑 manifest 的 `generated_at` 会让**内容相同**的重物化也算失配
（见 D3 的身份取法）；② b 只说 `--new-session` 跳过 Trellis 核对，漏了同一入口还跳过 `check_platforms`
与身份警告，也漏了普通启用"先写附件/路由、后查冲突"会让失败启用留下 `enabled=true`（见 F2 的后半）；
③ b 的两条 §1.1 收紧建议方向对，但它把"消费点"问题归到判据句改写即可，没发现同一病灶在
`wf-continue` 已产生**互相矛盾的两句**（F5b 与 F6）。

### 本次自行发现（两份报告均未提）

- **F1c**：两处文档出口"删 `materials/` 下内容文件后重跑 `review-context`"按现有判据**执行不了**：
  只删内容不删 manifest ⇒ `materials_identity_state` 返回 `drift` ⇒ 入口直接拒绝（`review.py:2975`）。
- **F2c**：`review-context` 的 `facts.materials_check.fixed` 恒为 `true`（`review.py:3346`），legacy/采纳态也说"fixed"。
- **F6**：`workflows/*` 之外，`wf-continue` 用"先向人确认"描述 `preexisting_in_scope`，同一 skill 后文
  又要求 AI 先按快照/提交/WIP 判断归属——前者制造停点，后者才是 §1.1 的口径。

## Findings（含处置）

| 编号 | 事实（决定性证据） | 处置 |
|---|---|---|
| F1a | 首轮物化逐文件写入 `materials/`、manifest 最后写：中断留下的半包按 `legacy` **被采纳**（`review.py:3305` 先 `makedirs`、`write_materials` 后写 manifest） | 机制：改为 staging 目录写完（含 manifest）后一次性发布 |
| F1b | 报告与材料身份**无绑定**：导入记录只有 `anchor` + `report_digest`（`review.py:3740` 附近），判定却读**当前** manifest 并把它的摘要写进结论（`review.py:5261`）——同轮重物化后旧报告仍过锚点校验，结论却能记新 manifest | 机制：材料身份进报告协议（骨架预填）、导入校验并登记、判定比对；身份取 manifest 的 `check_id`+`files`（不含 `generated_at`） |
| F1c | 文档出口"删内容文件后重跑"实际被 drift 挡住 | 指引：出口改成"连 manifest 一起删"并说明身份后果 |
| F2a | `cmd_enable` 在 `--new-session` 分支**先返回**轮换（`cli.py:1389`），Trellis 互斥（`cli.py:1425`）与 `check_platforms`（`cli.py:1450`）都不跑 | 机制：抽一套启用前置，两个入口共用且在写盘前跑 |
| F2b | 普通启用先 `_establish_auto_session`（写附件 + 路由）再查冲突；冲突时命令失败但 `activation.enabled=true` 已落盘，后续命令的 `require_activation` 会放行 | 机制：同上（前置前移） |
| F2c | `materials_check.fixed` 恒 `true` | 机制：按 `materials_identity_state` 如实给 `state`/`fixed` |
| F3 | 正式批准只在摘要非空时比对（`tasks.py:1822`），随后"subject 含任务 id 或摘要相等"即放行——空摘要 + subject 带 id 的旧决定能批准已变的 PRD | 机制：`plan_approval` 决定必须精确匹配当前 PRD 摘要；`subject` 退回次级绑定 |
| F5a | `wf-review-action` 导入示例不给 `--round`（`skills/wf-review-action/SKILL.md:13`），默认取最大发起轮；`next_` 也不带轮次 | 指引 + 机制事实：示例与 `next_` 带轮次，导入报错时列出待处理轮次 |
| F5b | `wf-bootstrap` 的"证据文件纪律"仍是五类清单（`skills/wf-bootstrap/SKILL.md:20`），与 `wf-continue` 已改的"按谁生成分类 + 以 `wf help` 为准"冲突，且是重复的完整论述 | 指引：删清单，只留一句判断 + 指针 |
| F6 | `wf-continue` 执行行"先向人确认……不默认归属、也不阻断"与后文"先判"矛盾 | 指引：改为"先核证据 → 只有冲突/要决定接管·排除·提交时才问人" |
| F7 | §1.1 判据句把"消费点"列成"判定、门禁、留痕、`next` 或交接"，`facts`/`next` 本身也是程序输出 ⇒ 近乎自证 | 设计稿：把后置条件写成"改变哪个实际动作、保护哪项已承诺的结果"，并写明"只被打印不算消费点" |
| F8 | §1.1 的"交人"当前只在冲突处收口，但 skill 侧仍有"先确认"型停点（F6 是同族） | 设计稿：把交人触发点钉在真实决定上（证据冲突 / 接管·排除·提交他人改动 / 改承诺） |

## Requirements

- **R1**（F1a–F1c）轮次材料是一个原子的、可核的身份：半包不再产生；报告绑定它读到的材料身份；判定按报告绑定的身份核对，不一致即拒并给可执行出口。
- **R2**（F2a–F2c）启用只有一套前置：`enable` 与 `enable --new-session` 在写任何记录前共用同一套核对（Trellis 互斥、平台、身份警告）；失败不留下 `enabled=true`。`materials_check` 如实报状态。
- **R3**（F3）正式批准必须精确覆盖当前 PRD 摘要；空摘要不再能靠 subject 过关。
- **R4**（F5a/F5b/F6）四处指引按各自判据位改到"先核证据、给收敛动作"，重复论述只留一处。
- **R5**（F7/F8）§1.1 两处表述改准；转写后按设计稿维护协议做双向回扫并跑设计校验器。
- **R6** 全部改动只走现有入口与判据位，不新增 skill、不新增层级；机制项都有消费点与失败出口。

## Acceptance Criteria

- [ ] A1 首轮物化中断（在 `write_materials` 返回前杀掉）不产生可采纳的半包：重跑 `review-context` 得到完整包，`materials_identity_state` 不为 `legacy`。
- [ ] A2 报告协议带 `materials`（骨架预填）；导入时与当前身份不符即 `WF_REVIEW_INVALID`，facts 给"恢复原字节 / 换一轮"出口。
- [ ] A3 导入后重物化（内容变化）再 `review-decide` 被拒，错误给出口；内容相同（只有时间戳变）仍放行。
- [ ] A4 `review-decide` 的结论记的是**报告绑定**的身份；与当前不一致时两者都可见。
- [ ] A5 已导入报告 + 材料 drift + "删 manifest 采纳"路径的行为被断言（不再把弱身份洗成 fixed）。
- [ ] A6 Trellis 有效指令存在时，`enable` 与 `enable --new-session` 都返回 `WF_FLOW_CONFLICT` 且**都不写**附件/路由；`check_platforms` 失败同样两入口都拒。
- [ ] A7 普通启用被前置拒绝后，同会话后续写命令仍按 `WF_NOT_ENABLED` 处理（不因遗留 `enabled=true` 放行）。
- [ ] A8 空 `object_digest` 的 approve 决定被拒（错误含 `expected_prd_digest`）；`--draft` 生成的草稿仍可直接批准。
- [ ] A9 `materials_check` 在 legacy/采纳态报 `fixed=false` 与真实 `state`。
- [ ] A10 `wf-review-action` 导入示例带 `--round`；`review-import` 无报告时的 facts 列出待处理轮次。
- [ ] A11 `wf-bootstrap` 不再持有独立清单；`wf-continue` 的 `preexisting_in_scope` 行与新口径一致。
- [ ] A12 §1.1 两处表述改准，`python3 scripts/validate-wf-design.py` 全绿（含覆盖率阈值），索引回扫逐行登记。
- [ ] A13 T0 单测全绿；受影响套件 + `WF_TAGS=review` 与 review repro 组绿；全量在收口前跑一次并如实报告。
- [ ] A14 `git diff` 只含本任务范围；行为变更都有能区分的断言（含回退注入至少一次）。

## Out of Scope

- 不新建/删除 skill、不新增层级、不引入新的判断步骤。
- 不改范围：升级通道端到端实跑、tag、`candidate-audit` 存量红灯、摘要锁裁决本身（见下）、审查强度模型。
- 不发布、不打 tag（但按交付纪律同步重建 `wf-release/` 生成树，只由脚本生成）；不改 `traffic_monitor` 目标项目。
- 不改工作流定义/实例（`definition`/`run`)语义。

## Pending decision（需人裁）

**同轮报告可否在"只是材料被重出、内容确实变了"时覆盖重导？** 现状是 11-21 人裁的"导入后不可覆盖"，
重开须人显式提出；上一轮台账 §21 已按"维持"登记。本轮 R1 让该成本更可见（重物化后同轮报告失效）。
三个选项见最终计划摘要。

## Review verdict on §1.1

判据句主干、两条护栏、指引就地、人签清单性质、清单外不停点的自查句**准确且与实现互证**（本轮核到的
F1/F2/F3 全部落在"可算 + 有消费点 + 有已观察失败"一侧）。两处不准：F7（消费点口径把程序输出算进去）、
F8（交人触发点没钉在真实决定上）。改法只动这两句，不动其余要点与四段机制契约的位置。
