# Design：退役收口的编辑策略与落点

## 0. 原则

1. **只改证据已消失的地方**：凡是文本声称"旧资产在 X"的，改述或删除；凡是文本记录"当年为什么这么裁决"的，保留结论、去掉指向已删文档的节号。
2. **不重写历史结论**：§9.5 裁决记录一字不改（只追加新行）；§9.1–§9.4 的结论表保留，只把 `1.2 §x` 换成不带节号的"旧实现方案"。
3. **不引用 `tmp/`**（R7）：受版本库管理的文档里出现 gitignored 路径 = 新克隆死链。
4. **每一步都能单独验证**：删文件后立即跑 `validate-skills.sh` / `trellis-library validate`。

## 1. 编辑策略（方案文档）

| ID | 对象 | 处理 |
|---|---|---|
| P-a | 正文 `〔1.2 §x〕` 标注（**34 行**） | 删除标注，保留句义。理由：文义自足，出处已不可读 |
| P-b | `1.2 §x` / `1.2 Dx` 的**叙述性引用**（86 行，含附录 C 与 §9） | 改为"旧实现方案"（不带节号）；附录 C 的 35 行映射整节删除（P-c） |
| P-c | 附录 C 整节（**1416–1458**，标题"来源映射表（1.2 → 本文件）"） | 整节删除；§0.2 的指向同步去掉 |
| P-d | §0.2"与 1.2 文档的关系"（含 8 行继承表） | 改写为一段：旧实现方案已删除；本文件正文自足，不再提供逐条出处 |
| P-e | `tmp/新项目开发工作流`（**8 行**）、`旧模块`（12 行） | 按 §2 的逐节改法处理，最终 A3 判据为 0 |

## 2. 方案文档逐节改法

| 节 | 改法 |
|---|---|
| §0.2 | 见 P-d |
| §2.1 模块源 | 标题改为"模块源（本仓库）"；删除步骤表、四维护 skill 处置表、`grep` 核验命令、"归属说明"段；改为一句事实："旧模块已退役并移出仓库（不入库）；`docs/workflows/新项目开发工作流/` 空出，由本模块新建"；布局代码块删除 `tmp/新项目开发工作流/` 行 |
| §2.2 目标项目布局 | 无 `tmp/` 行，只需确认（当前无） |
| §2.5 上游参考 | 删除"`tmp/新项目开发工作流/`（旧模块…实现参考）"行；在表前加一句"实现参考仅限 Trellis 源码与五平台规范" |
| 附录 B.1 | 保留路径（R4 沿用）；把"P0 位置交接后归属本模块"改为"旧模块退役后由本模块新建" |
| §8.2 P0 ① | 改为"旧模块退役（删除）+ 建模块源骨架"；删"同批处置四个维护 skill 的目标根（§2.1）" |
| §8.2 P0 ⑤/⑥/⑩/⑫ 与 P1 | 按 M1–M3（见 §3） |
| §9.1–§9.4 | P-b 处理；§9.4 标题改为"已判定不采纳的旧实现方案内容" |
| §9.5 | **只追加**一行 2026-10-28 的裁决 |
| §9.6 G3 | 改判（见 §3.3） |
| §9.7 | M1/M2 由"修正提案"改"已裁决"；新增 M3 行；T2 行删除位置交接与四 skill |

## 3. M1–M3 的落地（R5 已裁：全部采纳）

### 3.1 §8.2 P0 行

- ⑤ 追加括注："（只读命令依赖**账本读取**：解析 `ledger.json`，键缺失按'无记录'；账本**写入**仍属 P1）"
- ⑥ 不变（`wf start` 的账本前置由 M1 提供）
- ⑩ 探针清单改为：`W1–W6、W9–W11、W12、W15–W17、W21–W23`（移出 W18；补入 W12）
- ⑫ 改为："往返验收（§7.6 两条），收尾走**最小 `wf close`**"

### 3.2 §8.2 P1 行

改为："**账本写入**；`wf dag` 派生视图；任务图解析与 `wf task new --from-graph`；`wf edge add/rm` 与 W18；`wf baseline --light`；`wf repair` 类型 1 / 3；投放 `wf-repair` skill"（`wf close` 从 P1 移除）。

### 3.3 §9.5 追加行（措辞按既有格式）

| 日期 | 条目 | 结论 |
|---|---|---|
| 2026-10-28 | M1 / M2 / M3 | 采纳建议项 ①：账本只读与最小 `wf close` 并入 P0 机制面（同任务）；W18 随 `wf edge` 归 P1、W12 归 P0；§8.2 两行与探针归属同步改写 |
| 2026-10-28 | G3（模块源位置） | **改判**：旧模块已退役并移出仓库（不入库、文档不引用）；模块源沿用 `docs/workflows/新项目开发工作流/` 新建 |
| 2026-10-28 | 四个维护 skill | 退役删除（audit / capability-audit / repair / scan 及其契约 spec）；等价能力由 `wf doctor` / `wf upgrade` / `embed-state` / W 探针承载；删前摘录通用误报守卫 |

### 3.4 §9.7 表改写

- T1 行：追加"G5 正文已产出"（现状即真）。
- T2 行：删除"位置交接（含四个维护 skill …）"；改为"建模块源骨架 + 变体迁入 + 旧路径零残留"；验收改为"`docs/workflows/新项目开发工作流/` 只有新模块源且无任何旧路径引用"。
- T3 行：M1 / M2 已裁决，直接写进边界；新增 M3 行（W18/W12 归属）。
- 传递项：删 N4、D5（随四个 skill 退役消失）；保留"G5 落点"。

## 4. 四个 skill 退役（R3 已裁：删除 + 摘录守卫）

### 4.1 删除清单（222 文件）

| 路径 | 文件数 |
|---|---|
| `.claude/skills/workflow-audit/` | 42 |
| `.claude/skills/workflow-capability-audit/` | 23 |
| `.agents/skills/workflow-audit/` | 42 |
| `.agents/skills/workflow-capability-audit/` | 23 |
| `skills/workflow-repair/` | 71 |
| `skills/workflow-scan/` | 21 |

连带 spec：

| 路径 | 动作 |
|---|---|
| `.trellis/spec/skills/{workflow-audit,workflow-capability-audit,workflow-scan,workflow-repair}.md` | 删除 |
| `.trellis/spec/skills/index.md` | 删 25–28 行清单、46–93 行"Coupled Skill Contracts (CRITICAL)"整节、98–111 行 pair 描述 |
| `.trellis/spec/scripts/workflow-{command-doc,installer-upgrade}-contracts.md` | **删除**（契约绑旧产品脚本）；`spec/scripts/index.md` 删对应两行 |
| `.trellis/spec/workflow-support-inventory.md` | 删"被旧模块引用"的表述，保留 `自定义工作流制作规范.md` 的引用 |
| `.trellis/spec/{docs,agents}/index.md`、`guides/workflow-repeat-issue-triage.md` | 改述旧模块指向 |

### 4.2 删前摘录（新文件）

`.trellis/spec/docs/workflow-asset-audit-guards.md`：从 scan/repair 的 Version History 中摘 **3–5 条与路径无关**的通用误报守卫。候选（已核有出处）：

1. 已安装的共享模板 vs 任务期生成的同名文件（`finish-work-checklist-template.md` vs 生成的 `finish-work-checklist.md`）不可混为缺陷。
2. 共享 skill 载体 vs 平台二级载体（`.agents/skills/` 与 `.claude/skills/` 同名 ≠ 重复资产）。
3. 大写 `SKILL.md` 是该生态的约定，不是命名错误。
4. "被禁用/退役的命令在活跃面缺失"是预期状态，不是缺陷。
5. 只按文件名/路径形状判断的引用类发现，必须先做内容级复核再采纳。

该文档不含任何已退役路径，供将来 wf 模块的作者侧审计复用。

## 5. 其余载体处置

| 对象 | 动作 |
|---|---|
| `AGENTS.md:25` | 改述：模块源路径保留；删除"its command, installer, and CLI-adapter source assets live under …"（这些旧资产已退役） |
| `docs/workflows/自定义工作流制作规范.md:469-470` | 两行改为"（旧模块已退役）"或删除该两行 |
| `docs/Trellis隐藏目录边界清单.md`（134 行） | **整篇 `git rm`**（B3 待重写，不保留半真半假版本） |
| `commands/shell/init-trellis-temp-project.sh:111` | 先查它是否还调用旧产品的安装器：若只写死路径 → 改为按仓库根解析并指向 `docs/workflows/新项目开发工作流/`；若依赖旧产品脚本 → 整个脚本随旧产品退役（删除）并在 §9.5 记录 |

## 6. 风险与回滚

| 风险 | 处置 |
|---|---|
| 批量删除误删 | 全部走 `git rm`（保留历史）；执行前把 `git status` 列表与 §4.1 清单逐条比对 |
| 改 §9 导致历史不可读 | 只替换节号、只删附录 C；§9.5 原文不改 |
| spec 删除后校验失败 | 每删一步立即跑 `validate-skills.sh` + `trellis-library validate` |
| 死链残留 | A2/A3/A4/A5 四条 grep 判据 + `grep -rn` 已删文件名（`workflow-audit.md` 等）为 0 |
| 回滚 | 本任务全部改动可由 `git revert` 单提交撤销；`tmp/` 未被触碰 |

## 7. 验证设计

见 implement.md §3：静态 grep（A2–A6）、两条项目校验（A7）、context 冒烟（A8），外加"已删文件名零引用"与"docs 内相对链接存在性"两项。
