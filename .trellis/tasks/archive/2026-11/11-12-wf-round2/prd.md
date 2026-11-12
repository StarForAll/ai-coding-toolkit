# PRD：wf 第二轮：能力交付与收口遗留

> 建立于 2026-11-12。承接：`11-05-wf-implementation-gap-audit`（审计与 identity 重构记录）、
> `11-03-wf-round1-min-loop`（首轮实现，已归档）、`docs/workflows/wf/analysis/`（v42 与 ⑥ 两份方案）。
> 轮次口径以实现稿 §6.4 为准。

## 1. 目标

1. 交付 **wf 第二轮能力**（实现稿 §6.4:795 的清单）：定义准备与静态校验、实例创建/推进/暂停/终止、步骤人判与略过、自动建任务与顺序边、返工/替换/建删边、挂起复评；以及 **`inspect` 的两项治理输出**（「需人工比对」清单、`author` 复核顺序）。
2. 同批交付 **`.wf/out-of-scope/` 知识拒绝项机制**（2026-11-12 人裁 A：与第 1 项同批，不单独留到第三轮）。
3. 承接 **⑥/backlog 的收尾遗留与文档漂移**，让"已落地但无任务台账"的 112 个提交有正式归属。

## 2. 范围

### 2.1 第二轮能力（实现稿 §6.4 清单）

| # | 能力 | 现状 |
|---|---|---|
| 1 | 定义准备与静态校验（`definition.prepare`） | `WF_CAPABILITY_UNAVAILABLE` 桩 |
| 2 | 实例创建/推进/暂停/终止（`run.*`） | 桩 |
| 3 | 步骤人判与略过 | 桩 |
| 4 | 自动建任务与顺序边（`dependency.change`） | 桩 |
| 5 | 返工/替换/建删边（`task-rework`/`task-replace`） | 桩 |
| 6 | 挂起复评（`task-reassess`） | 桩 |
| 7 | `inspect` 治理输出：「需人工比对」清单 + `author` 复核顺序 | `governance_omitted` 声明未输出（`tasks.py:4266-4269`） |

> **已核实（2026-11-12，见 [prework.md](prework.md) §1）**：D14 的「wf 自签发身份路径」随 2026-11-08 自动身份模式交付，**不属第二轮**；机制稿 §1.4、实现稿 §6.4/D14 行已同批订正。剩余的实现级文案缺陷（无锚点时出口提示「显式信封」但 `provider=wf` 的显式信封会被拒）登记在 P2。

### 2.2 `.wf/out-of-scope/` 知识拒绝项（与 2.1 的第 7 项同批）

四项启用前置必须同批打勾（设计稿 §6.3、实现稿 §2.3.11 P2-1）：

1. **写入者**：`spec-update` 按机制稿 §8.4 的 schema 建 `<concept>.md`（`concept`/`reason`/`reconsider_when` 非空、文件名与 concept 一致）；
2. **重提追加**：同 concept 已存在则追加 `## 既往请求` 行，不新建文件；同 concept 多文件由巡检报重复登记；
3. **路径放行**：`.wf/out-of-scope/**` 进 `paths.py::WRITE_TARGET_PREFIXES` 与 `protocol.project_data()`（写入者唯一）；
4. **消费者**：`inspect` 的 `_governance_summary` 增加"重复登记核对"，知识处置入口能引用拒绝项。

同批必须改一处声明：`governance_omitted` 里现在只声明 2 类未输出，需增加 `out_of_scope_duplicates`（交付后移除），避免读者把 governance 当全量。

### 2.3 收尾遗留（只登记不实现的部分要写清）

- backlog 已裁不动的三项：`D2`（归档提交顺序，暂不动）、`F1`（复用 `WF_CHECK_FAILED`，码表维持 36）、`E3`（维持现状，复杂任务仍需一次 pass）→ 本轮**只核对登记是否一致**，不实现。
- **文档漂移**：`analysis/backlog-excluded-from-item6.md` 的状态表仍写"只记录，不实现"；`analysis/proposal-repairing-state.md` 顶部写"已实施 v67"而 §6 标"工作树未提交"；实现稿 §6.4:795 的 D14 行待核实（见 2.1）。
- **dogfood 复跑**：v42/⑥ 之后的机制尚未再 dogfood（首轮那次在 2026-11-09～10）。本轮交付完成后按 `11-05-…/dogfood-plan.md` 跑一轮，作为第二轮串行门禁的前置。
- **记录债（已按人裁 ① 处理，2026-11-12）**：`denominator.md` 采取「冻结 + 局部重判」——修 2 处计数与 1 处轮次归属（691 → 等第二轮），逐行复核首轮 14 行（13 保持、1 改判），现为 `66/98`（断言口径 `66/79 = 83.5%`）；门禁①证据改为引用当前版本的 `run_all` 132 项与三夹具。详见 [prework.md](prework.md) §2。

## 3. 非目标

- 第三轮：`upgrade --apply`／`uninstall --purge`／运行期升级侧清单解析（D22）／完整发行生命周期（D31）／资产修复验收（D09）／落点表全部适用分支（D33）。
- 不改 charter／设计稿／机制稿的判定语义；发现冲突按 charter T1 出「需人裁决」。
- 不重新设计首轮已定稿的部分（准入、门禁顺序、状态值、原因码）。

## 4. 验收

| 项 | 判据 |
|---|---|
| 第二轮能力 | 实现稿 §6.4 逐项从 `WF_CAPABILITY_UNAVAILABLE` 变为可跑；每项至少一条 repro（green/red 双模） |
| `inspect` 治理输出 | `governance` 里出现两类输出；`governance_omitted` 相应条目移除，且无"未声明未输出"的类别 |
| `.wf/out-of-scope/` | 四项前置各有可核对用例：建文件、重提追加、空 `reason` 拒、concept 与文件名不符拒、多文件被巡检报重复 |
| 机检/回归 | `validate-wf-design.py` 输入摘要 4/4、`check-doc-refs.py` 0 problem、单测全绿、`run_all.sh` 全量与 repro 全绿、发行字节复现通过 |
| 文档同步 | 实现稿 §6.4 轮次表、§2.3.11 P2-1 状态、`governance_omitted` 同批更新；`analysis/` 两处漂移订正 |
| dogfood | 至少一轮真实项目闭环记录（或明确写"未运行 + 原因分类"） |

## 5. 依赖与输入

- 判据源（只读）：`docs/workflows/wf-framework-{charter,design,mechanism,implementation}.md`。
- 记录：`11-05-…/{gap-inventory,closeout-inventory,denominator,open-decisions,dogfood-plan}.md`；
  `11-03`（已归档）的 `validation.md` §97 收口口径；`docs/workflows/wf/analysis/{solution-review-v42,proposal-repairing-state,backlog-excluded-from-item6}.md`。
- 当前实现：`docs/workflows/wf/payload/**`（`spec.py` 854 行、`tasks.py` 4540 行、`paths.py`、`protocol.py`）。
- 开工程序：本任务属复杂任务，`task.py start` 前须补 `design.md` + `implement.md`。
