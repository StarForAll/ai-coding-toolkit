# 提案（v3）：改用 `fixing` 持久阶段（撤回 v2 的"派生事实"路线）

> 状态：**待审 v3**。v1、v2 被两轮审查否掉，本版不是打补丁，而是**换掉方案本身**：
> 结论是「派生可见性事实」这条路走不通，改回 v42 的 `fixing` 阶段。
> 本文件是决策提案，实现未开始。

---

## 0. 为什么撤回 v2（不修补的判据）

两轮审查合起来证明了一件事：**只要"修复中"是"从记录派生"，它就必须复制门禁的判定逻辑**，于是每轮都被抓出新的分叉：

| v2 的定义 | 审查抓到的反例 | 本质 |
|---|---|---|
| check 五态（no_check/not_pass/invalidated/anchor_mismatch/rule_version_mismatch） | 还漏两类：**锚点重算失败**（`tasks.py:1018` 返回 error 三元组）、**结构复核不过**（`gates.py:651` 的 `check_result_problems`） | 派生态要复制 `gates.py:631-654` 的全部分支，且**没有错误通道** |
| review = open_blocking + unavailable 报告 + verdict=unavailable | 还有：**材料缺口导致的正式 fail**（`review.py:1356`，可无 blocking）、**复杂任务审查未绑定当前 check**（`gates.py:682` 的 `result.check_id != check.id`） | 同上 |
| 「不可结案原因集合」 | `final_gate` 还拦 escalated 待答、required 未核实、依赖未满足、debug 未裁、action 未完成… | 名字承诺了一个它做不到的问题 |
| 退出条件只看"无 unavailable 报告" | `--unavailable` 可在**没有导入报告**时写结论（`review.py:1248`），`open_findings` 不读它 → 同一记录 §1 判 true、§3 判 false | **自相矛盾** |
| "任务级结果总带 repairing" | `task-check` 失败时 `raise TaskError`（`tasks.py:2465`），根本不走结果构造器 → 最该带的时候没有 | 注入面覆盖不到异常链路 |
| "误报 disposition 掉后 → false" | `open_findings` 的 closed **只认 `decision=="accepted"`**（`review.py:173`）；rejected/amended 不闭环 | 我的反例表写错了事实 |
| no_check → true | 新建任务、刚进 execute 就恒显示"修复中"，`next` 指向"重跑 check" | 矫枉过正 |

**判断：这条路线要么持续复制门禁（第二真相），要么持续不完备。** 两轮修正都没能收敛，按"不引入新问题、不遗留问题"的要求，应换方案而不是继续补。

---

## 1. v3 方案：`fixing` 作为**持久阶段**（v42 K10/S4/S5 原样）

`phase` 枚举变五档：`plan → execute → fixing → finish`。

**关键区别**：`fixing` 不是"派生出来的事实"，而是**在事件发生的那一刻由知道结果的代码写下的状态**：

| 事件 | 谁写 | 写入内容 |
|---|---|---|
| `task-check` 产生 fail 结果 | check 写入路径（已知道 fail） | `phase = fixing` |
| `review-decide` 判 fail | decide 写入路径（已知道 fail） | `phase = fixing` |
| `task-check` 产生 pass 结果 | check 写入路径 | `phase = check`（退出修复） |
| 修复中决定重做工作 | `replan`/显式动作（现有 `check` 迁移第三去向） | `phase = execute` |
| 异常归档 | `task-abandon` | `status = archived` |

**因此它不需要**：枚举 check 状态、复制门禁判定、注入每个结果、定义"不可结案原因集合"。**门禁一律不改**（归档口仍看 `check.result`、审查门仍看 `verdict` 与 `check_id` 绑定）——`fixing` 不是"能否结案"的镜像，是"当前处在修复"这一状态。

### 1.1 直接消掉的审查反例

| 审查反例 | 在 v3 下 |
|---|---|
| 无报告时 `--unavailable` 造成的 true/false 矛盾 | 不存在："是否在修"由 `phase` 一个字段回答，不做派生 |
| check fail 返回不带状态（A2） | `position.phase` **本来就有**，无需注入 |
| 命令硬编码 next 提示 finish（A3） | `phase=fixing` 后 `next_by_position["in_progress/fixing"]` 生效；`task-check` 的提示文案改为读 phase |
| 归档终态被重新标成修复中（A4） | `next_for` 的**终态优先**不变（`protocol.py:134` 先判 terminal），且归档不改 phase 但 `status=archived` 优先展示 |
| check 五态装不下（A5） | 不需要枚举：状态是"发生过 fail"，不是"现在是否可用" |
| review fail 无 blocking（A6） | decide 一旦判 fail 就写 `fixing`，与 blocking 无关 |
| 新任务恒显示修复中（B1） | 新任务 `phase=execute`，不是 fixing |
| 复杂任务"审查未绑定当前 check"（B2） | 仍由既有门禁拦（`gates.py:682`），`fixing` **不声称**能替代它 |

---

## 2. 需要动的地方（实测，比 v1/v2 说的少）

> 勘误：v1 说"`phase` 引用 102 行"容易误读——那 102 行包含**传递 phase 参数**的代码；
> 真正**按 phase 值分支**的只有 6 处 + 2 个元组常量。

| 类别 | 实测位置 | 改法 |
|---|---|---|
| 按 phase 值分支 | `tasks.py:449`（`PHASES_STARTED`）、`1568`、`1956`、`3167`、`3371`、`3508`、`3728` | 把 `fixing` 加进该进的白名单（`PHASES_STARTED` 与两处 `("execute","check","finish")` 元组）；`== "finish"` 的两处（3167/3371）需判断"修复中能否归档"——按 §3 结论：**不能**，保持只认 finish |
| 常量 | `tasks.py:374 PHASES_STARTED` | 加 `fixing` |
| 协议 | `protocol/states.json` 的 `phase.enum`、`phase_model`、`next_by_position` 增 `in_progress/fixing`、迁移表 | 见 §3 |
| 展示 | `states.json` 的 `phase.display`；`wf status`/预览读 phase 即可 | 加 `fixing: Fixing` |
| position | **不动**（`codes.position` 已经带 phase） | —— |

---

## 3. 状态机设计（唯一权威：`states.json`）

新增/修改的迁移（`from → to`，均 `status=in_progress`）：

| id | from | to | when |
|---|---|---|---|
| `check`（改） | `execute` / `check` | `finish`（pass）/ **`fixing`（fail）** / `execute`（修复完成回做） | 现有三去向里"fail 留在 check"改为"fail 进 fixing" |
| `review-fail`（新增） | `execute` / `check` / `finish` | `fixing` | 审查判 fail（含 fail 由材料缺口产生、或复杂任务审查未绑定当前 check 的重发要求） |
| `recheck`（新增） | `fixing` | `check` | 修复后重跑 `task-check` 产生新结果（pass 或 fail 都由 check 迁移处理） |
| `repair-rework`（新增） | `fixing` | `execute` | 修复需要重做工作（等价于现有"修复完成回 execute"） |
| `repair-replan`（新增） | `fixing` | `plan` | 人决定重新规划 |
| `archive-abnormal`（现有） | 任意 | 归档 | 不变：异常路径不看 phase |

**归档仍只允许 `phase=finish`**（`tasks.py:3167` 的 `!= "finish"` 不改）——修复中不能正常归档，这正是 v42 S5 的语义。

---

## 4. 与 2026-11-09 人裁的关系（必须显式推翻）

那次人裁是「保留四阶段、`fixing` 不落盘」。v3 与之相反，理由必须写进裁定文件而不是悄悄改：

1. 人裁的动机是"`fixing` 会增加机械复杂度、`check` 已能满足 fail→修复的语义"；
2. 两轮审查证明替代方案（派生事实）**复杂度更高、且无法自洽**（§0）；
3. `fixing` 的实际代码成本只有 **6 处条件 + 2 个常量 + 迁移表**（§2），不是当初估计的"处处加一支"。

→ 建议新增 `analysis/ruling-fixing-phase.md`：记录"推翻 2026-11-09 人裁、采用 v42 K10/S4/S5"，附上述三条理由与两轮审查的反例清单。**v42 原文一字不改**（逐字节冻结，sha256 `d06c57e7…cadd`）；K10/S4/S5 与实现从此一致，不再需要"差异表"。

---

## 5. 在途任务与兼容

| 情形 | 处理 |
|---|---|
| 现在处于 `check` 且 `check.result=fail` 的任务 | **不迁移**：保持 phase=check（行为与今天一致）；下次 `review-decide fail` 或新的 `task-check fail` 才进入 fixing。理由是迁移会改写历史记录 |
| 现在处于 `finish` 且审查 fail 的任务 | 同上：下一次 decide 才进 fixing |
| 工具读取 | 任何只认四阶段的旧读取方（若有）需同时接受第五值；本仓库内没有此类外部读取方 |
| 未来要多 agent 并行 | `fixing` 是"当前在做修复"的状态；"多份报告陆续到达"由 `reviews.imported/launches` 表达，两者不冲突（与 v2 主张不同，这里不再声称正交优势） |

---

## 6. 验收标准（每条对应一个真实失败）

| # | 断言 | 防的失败 |
|---|---|---|
| 1 | `task-check` 产生 fail → `task.phase == "fixing"`，且返回 `position.phase == "fixing"` | check fail 后无状态（v2 的 A2） |
| 2 | 修复后重跑 `task-check` pass → `phase == "check"` | 修完不退出修复 |
| 3 | `review-decide` 判 fail（含**材料缺口产生的 fail**、**无 blocking finding**）→ `phase == "fixing"` | 审查失败不进修复态（v2 的 A6） |
| 4 | `phase=fixing` 时 `archive` 被拒（只认 finish），`next` 指向修复出口 | 修复中能直接归档 |
| 5 | `status=archived` 时展示与 `next` 仍以终态优先 | 归档后仍显示修复中（v2 的 A4） |
| 6 | 新模式任务（`phase=execute`，从未 check）不显示修复中 | 新任务恒"修复中"（v2 的 B1） |
| 7 | `--unavailable` 判定的任务**不进入** fixing（出口是补审查/异常归档） | 不可用被当成待修复（v2 的 A1 矛盾） |

---

## 7. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 推翻人裁 | 用 §4 的裁定文件显式记录，不静默改 |
| 第五阶段被写成"修复期准入规则"（禁扩面等） | 明确不做：`fixing` 只表示状态，准入仍由既有门禁承担 |
| 旧记录（四阶段）与新代码混存 | 读取方一律"白名单式"接受（未知 phase 按 check 处理并提示），不因历史值报错 |
| 与 v42 §7.1（把 check 当"已删除机制"）的对立 | 采用 v42 后这条自然成立，无需改 v42 |

---

## 8. 留给审查者的问题

1. §3 的 `review-fail` 允许从 **finish** 进入 fixing：这是否会让"已 pass 的任务"退回修复态，与"finish 只差归档"的直觉冲突？
2. §5 决定**不迁移**在途任务，会不会造成"同类任务处于两种 phase"的长期并存？
3. §2 只改 6 处条件，是否还有按 phase 语义隐式分支的地方（例如模板/预览文案里写死"Check 阶段"）？
4. 推翻人裁的门槛：是否应由你重新确认一次（而不是由这份提案自行改口径）？
