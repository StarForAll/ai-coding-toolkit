# Design：v48 修复的执行方式

## 方法

修复指令已给出逐字旧文 / 新文与验收位，本任务不做机制设计，执行方式为 **manifest 驱动的逐字替换 + 机械验证**：

1. `research/fix-manifest.tsv`：7 列 `ID	文件	锚点	旧文	新文	验收位	说明`，冻结后不再改语义；每行用 Python `str.replace(old, new, 1)`，执行前后计数必须恰为 1，不符即停。
2. 执行顺序固定（源 → 引用/镜像 → 验证 → 记录），顺序不可颠倒。
3. `research/verify.py`：对 manifest 逐行断言 `count(old)==0 && count(new)==1` 并输出新文行号；对 fix-notes 的反引号短语逐条 `grep -F`；断言不变量与全量 probe 期望。

## 记录目录

任务 `research/` 目录（`.trellis/tasks/10-27-workflow-design-v48-fix/research/`）：fix-manifest.tsv、verify.py、fix-notes.md、residuals.md。

## 已知的两处清单内偏差（冻结前登记）

1. M1 新文中「守卫转类型 5 补建」调整为「守卫先按类型 5 补建」：M1 自身验收位与 M9 期望要求 `rg "先按类型 5 补建"`=2（自检 + 记录），指令给出的新文逐字不含该短语，自检位将无法命中；最小调整即在原句插入「先按」二字，语义不变（守卫转去先按类型 5 补建）。
2. M8 status 追加文本中「改写改写即提交」按 M2 语义写为「改写即提交」（指令文本疑有重复字）。

## 验证面

- 不变量：矩阵 14 数据行、组合表 12 数据行、表 4-2 7 数据行、§6.4 窗口 9 数据行、既有 11 行组合表 diff 为空、矩阵无裸 `| — |`。
- 全量 probe：spec 既有探针 + M9 新增 8 条，逐条与期望比对。
- probe 范围：主稿 + 配套 + 记录目录（fix-notes）；spec 自身不入计数范围。
