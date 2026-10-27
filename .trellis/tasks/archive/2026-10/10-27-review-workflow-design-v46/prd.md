# 深度审查 workflow-design.md 设计稿（对照 0.1 自身约束）

## Goal

按 0.1 设计稿自身的约束对 docs/workflows/workflow-design.md 最新内容做深度审查，产出问题清单后中断等待人工审查，修复前先判定根因，修复后不收尾

## Background

`docs/workflows/workflow-design.md` 当前为 v46。按该文件内部「0.1 设计稿自身的
约束」对文档当前内容做深度审查，判断是否有可以改善的地方，避免后续实现中途
修改。

## Requirements

- 审查对象：`docs/workflows/workflow-design.md`（当前文档）。
- 交叉证据：`docs/workflows/依赖机制设计说明.md`（配套文档，用于口径 11 镜像
  核对与 probe 运行，但不作为独立审查对象）。
- 忽略：`docs/workflows/1.2-零补丁嵌入方案.md`（用户明确指定本轮忽略）。
- 遵循 `.trellis/spec/guides/design-review-thinking-guide.md` 与
  `.trellis/spec/docs/index.md`（predicate registry、probe 清单、v46 probe 表）。
- 按 guide 的证据门槛执行：§0.1 口径 10 六个验收面扫描必须做并写入报告；
  运行 spec 登记的 predicate probes（v46 期望值）作为文本证据。
- 实事求是：低于证据门槛的候选放入「Excluded (not reported as defects)」，
  不吹毛求疵。
- 发现问题后中断等待人工审查；修复前先判定每个问题的根因（避免同一问题
  反复修复）；修复完成后也**不执行收尾动作**，须人工审查通过并明确要求后
  才收尾。
- 本轮只读审查，不修改 `docs/workflows/` 下任何文件。（人工审查已完成，
  v47 修复轮按下方「本轮修复范围」执行，改动仅限主稿、配套与本任务文件，
  覆盖本条只读约束。）

## Acceptance Criteria

- [ ] 报告含全部六项验收面扫描结论与 probe 运行结果
- [ ] 每条主发现有确切 §/表/行引用、触发场景、期望 vs 实际，且通过作者反驳测试
- [ ] 报告落盘到本任务 `research/review-report-v46.md`，并在会话内给出结论
- [ ] 审查已完成，本轮进入修复；修复后不收尾
- [ ] fix-notes 落 `research/` 并在会话内给出未收口结论

## Notes

- Review-only task: PRD-only is sufficient; no design.md / implement.md.

## 本轮修复范围（v47，人工审查确认后追加）

唯一依据：用户修复提示词 + `research/review-report-v46.md`。产出版本 v47。

1. **F1（内部矛盾）**：§7.8 识别字段写入矩阵第 14 行（依赖标识写入）整行
   重写（按提示词给定文本，五格逐格对齐表头）；§6.4 第 2 步补冲突改写
   生效与发布取值句；§6.4 逐窗口表补「标记内容已改写、R 未建」行；
   类迁移 grep `不入说明|记任务记录` 并补「登记期间除外」。
2. **F2（同一情形双出口）**：§7.7 组合表「待重定义」行条件格改字段谓词
   「尾端处分已到终态（§7.4）」；分类前置守卫补类型 5 前置句；尾行注记
   同步；配套 §8 对应行、注记、守卫同版镜像；§10 自检补「先按类型 5
   补建（不重定义）」；情形矩阵两格推演落 fix-notes；A3 四例重跑。
3. **闸口 ⑥ 换代**：口径 10⑥「须在矩阵有行」改「有一行且逐格回指产生者
   /标明此路径不变」；§0 写作约定加写作侧义务；§10 类迁移义务与自检括注
   同步；本版自执行 14 行 × 5 格逐格表落 fix-notes，不合格格同版改掉。
4. **§3 图内任务成员**：补「基线变更新建任务」；配套 §3 术语行同版镜像；
   §7.6 C5 登记句经核对无口径差则不改（决策记 fix-notes）。
5. **记录面**：主稿与配套 version → v47；配套 `design: workflow-design.md
   v47`；主稿抬头、frontmatter status、§10 版本可追溯、附录 C 新增 v47、
   配套新增 §35；探针全量重跑，期望需要变的同版改注释。
6. 流程约束：先 fix-plan 后执行；顺序 源→引用→探针→记录；fix-notes 落
   `research/`；结论只能写「未收口，待人工复核」；不执行收尾（finish/
   archive/commit 禁止）。
