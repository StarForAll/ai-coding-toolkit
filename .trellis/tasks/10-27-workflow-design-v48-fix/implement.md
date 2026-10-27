# Implement：v48 修复执行清单

## 前置

- [x] 基线记录：HEAD `aea771d`、工作区 clean、两文档 v47、矩阵 14 / 组合表 12 / 表 4-2 7 / §6.4 窗口 9。
- [x] `research/fix-manifest.tsv` 写入并冻结（含两处偏差登记）。

## 执行（顺序不可颠倒）

- [x] 1. 源：M2d（矩阵 14 行）→ M3b（类型 5 补建）→ M3c（类型 5 守卫）→ M4a（§0 尾句）→ M6（类型 1 分支）→ M1（自检场景）。
- [x] 2. 引用 / 镜像：M3d（窗口④）→ M3e/M3f（配套 §6.4 / §8）→ M3g（表 B9）→ M4b/c/d（口径 10⑥ / 类迁移 / 自检括注）→ M7a/M7b（配套发起清单）→ M2a/b/c（正文与窗口行）。
- [x] 3. 验证：写 `research/verify.py` 并运行；全量 probe（含 M9 新增 8 条）；计数不符只修到通过，不改期望（期望写错才改并记原因）。
- [x] 4. 记录：M8（版本与附录 C v48，行号取自脚本输出）→ M9（spec probe 基准与注册表行）→ M10（guide 盲点 22）→ fix-notes.md（A1–A8 + 70 格 ⑥ 复核表 + probe 全量 + 声称-正文清单）→ residuals.md。
- [x] 5. `git diff --check`；`git diff -U0` 逐 hunk 核对只碰清单内位置。

## 收尾

- [x] 报告：git diff 摘要、待独立复核列表（none 验收位 + residuals「留」项 + NEW 项）、结论 ready for independent review。
- [x] 未经授权不 commit / finish-work / archive。
