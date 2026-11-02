# check-doc-refs 严格所有者模式（PRD）

## Goal

把 `scripts/check-doc-refs.py` 的「裸 `§x.y` 恰好命中本文件同号章节即通过」改为默认报错：新增文档一律要求每个 `§` 引用带所有者前缀（`本文 `/`机制稿 `/`设计稿 `/`依赖说明 `/`原 `，或按列举继承），只有显式登记的四份既有约定文档继续宽松。

## Background

- 来源：任务 `11-02-wf-implementation-plan` 的机制稿同批复审发现项 F5（见该任务 `review-mechanism-batch.md`）。实现方案文档中多处本应指向机制稿的裸 `§` 因本文存在同号章节而被脚本静默放过（评审时已逐个补前缀，但脚本判据仍会继续放过同类新写入）。
- 现状事实（实测）：`docs/workflows/wf-framework-implementation.md` 与 `wf-framework-mechanism.md` 的裸引用数均为 0；`wf-framework-design.md` 291 处、`wf-framework-design.index.md` 1399 处、`workflow-implementation.md` 240 处、`wf-framework-design.sources.md` 1 处——这四份文档以「裸 § = 本文件」为既有约定，其中 `workflow-implementation.md` 的约定登记在 `.trellis/spec/docs/workflow-implementation-constraints.md`（“Bare §x.y means this plan”）。
- 机检分工：`validate-wf-design.py` 只管四份设计族文档（含机制稿），`check-doc-refs.py` 是跨文档引用的补充检查，二者互不替代。

## Requirements

1. 默认严格：对未登记为宽松的文件，任何缺所有者前缀的 `§x.y` 一律报错——即使本文件存在同号章节；单级 `§n`（无点）仍跳过（与现状一致）。
2. 宽松名单显式且带理由：仅四份既有约定文档保持现有行为，名单写进脚本常量并在 docstring 说明每份的理由；名单外新增文件默认严格。
3. 报错文案区分两种成因：`§x.y 本地无此章节`（原有）与 `§x.y 缺所有者前缀`（新增）。
4. 输出与退出码不变：单文件输出两行与现状一致；多文件逐文件计数 + 总数；有任何问题退出码 1。
5. 不改判定语义、不改任何产品文档的既有引用内容；实现方案 §0 的引用约定同步为严格模式。

## Out of Scope

- 不把 `§` 引用解析成跨文档链接合法性检查（markdown 链接目标不在本脚本职责内）。
- 不新增回归测试框架；用 /tmp 夹具手测并在任务记录留证据。
- 不改 `validate-wf-design.py`。

## Acceptance Criteria

- [x] /tmp 夹具：本地有同号章节的裸引用（如 `见 §1.2`）报「缺所有者前缀」；带 `本文 `/`机制稿 `/`设计稿 ` 前缀通过；列举继承（`机制稿 §1.3、§8.1`、`机制稿 §6.2–§6.4`）通过；无前缀且本地无同号章节仍报错。
- [x] 三个 wf 文档实跑：`workflow-implementation.md` 0、`wf-framework-mechanism.md` 0、`wf-framework-implementation.md` 0。
- [x] 宽松名单四份文档实跑均为 0（行为未变）。
- [x] `validate-wf-design.py` 全绿且输入摘要 4/4；`unittest scripts.tests.test_validate_wf_design` 通过。
- [x] `docs/workflows/wf-framework-implementation.md` §0 的引用约定改写为严格模式措辞。
- [x] 未提交（本轮不提交）。

## Decisions（人裁，2026-11-02）

- F1 按已采纳的 ①（`task.retrospect` 为 `task.retrospective-done` 执行入口并写 completed 回执）；F2–F6 按复审建议处置——均已在 `11-02-wf-implementation-plan` 落地。
- F5 追加：把「本地同号章节 + 无前缀」改为报错，并**另立本任务**。

## 执行记录（2026-11-02）

实现落点：`scripts/check-doc-refs.py` 改为三种文件模式（`strict` 默认 / `local` / `cross`），名单与理由写进 docstring 与 `FILE_MODES` 常量：

| 文件 | 模式 | 理由 |
|---|---|---|
| `wf-framework-design.md` | local | 裸 § = 本文件 |
| `workflow-implementation.md` | local | 旧计划约定 bare § = this plan（spec/docs/workflow-implementation-constraints.md） |
| `wf-framework-design.index.md` | cross | 索引每格的 § 指设计稿章节（本文件无编号章节），由 validate-wf-design.py 校验 |
| `wf-framework-design.sources.md` | cross | 同上 |
| 其余（含 `wf-framework-implementation.md`、`wf-framework-mechanism.md`、`wf-framework-charter.md`） | strict | 缺所有者前缀即报错 |

判定细节：`本文 §x.y` 另核本文件章节（抓错号）；`机制稿 `/`设计稿 ` 前缀不核（上游各有校验）；列举继承含连接号（与 `validate-wf-design.py` 的所有者判据同集）。

实测（全绿）：七个文档 → 0 problem(s)。夹具：
- strict 文件内 `见 §1.2`（本地有同号章节）→ 报「缺所有者前缀」；`本文 §9.9` → 报「本文无此章节」；`机制稿 §9.9` → 通过；`机制稿 §1.3、§8.1`、`机制稿 §6.2–§6.4` → 通过。
- `docs/workflows/workflow-implementation.md` 路径下裸 `§9.9` → 报「本地无此章节」（local 模式）。
- `docs/workflows/wf-framework-design.index.md` 路径下裸 `§9.9` → 0（cross 模式）。

同步：实现方案 §0 的引用约定改写为严格模式措辞。`validate-wf-design.py` 全绿（引用 559；输入摘要 4/4）；`unittest` 19 tests OK。未提交。
