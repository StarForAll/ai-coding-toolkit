# 执行计划

## 前置事实

- HEAD：`8ad836d`；`docs/workflows/` 下产品文档无未提交改动（工作树仅有未跟踪 `.agents/skills/grill-me/`、`.unipi/`）。
- 机检基线：`python3 scripts/validate-wf-design.py` → OK（设计 695 行 / charter 129 行；定义位点 51+7；索引 141 行；定义/消费命中 100%；引用残差 2 行）。

## 步骤

- [x] 1. 读设计稿全文、charter、索引、sources、旧模块文档（workflow-design / workflow-implementation / wf-variant / 依赖机制设计说明）、机检器实现、`.trellis/spec/docs/wf-design-revision-gate.md`、`.trellis/spec/docs/index.md`。
- [x] 2. 运行设计期机检，记录真实输出（作为"结构绿"基线，不作语义结论）。
- [x] 3. 轴 A 可实现性：逐条核对正文承诺 vs §8.1 交付清单 vs §8.2 场景，找"必须自造规则"的点。
- [x] 4. 轴 B 一致性：对同一门禁做跨节回扫（写权/挂起复评、repair 令牌、安装落点、审查链路）。
- [x] 5. 轴 C 覆盖性：用脚本比对 141 条索引定义与 §8.2 场景行的可核对映射；核对夹具是否给出可观测判定物。
- [x] 6. 轴 D 机检可信度：逐检查项复核 `validate-wf-design.py` 的实际覆盖与盲区。
- [x] 7. 汇总根因聚类与建议修复顺序，写 `review-report.md`。
- [x] 8. 停止：交人工审查（第一轮：只出报告，不修复、不提交、不归档）。
- [x] 9. 按人工指示执行第一批修复：A2、B1–B4、C1–C3、C6、D1–D2、D4、W1–W4 落到设计稿/索引/机检器；C4/C5 改为交付义务；D3 补回归测试；R1–R6 写进 revision gate。明细见 `review-report.md` 第十二节。
- [x] 10. 人工审核通过（2026-11-01），继续执行：复核机检两处漏洞、补齐知识删除路径、更新机检自述。
- [x] 11. 最终验证：`validate-wf-design.py` 通过；`unittest` 7 条通过；`check-doc-refs.py` 0 问题；`git diff --check` 无空白问题；改动范围复核（仅设计稿、索引、机检器、回归测试、revision gate）。
- [ ] 12. 待人工下令收尾：提交 + 归档 + finish-work（未执行）。

## 验证方式

- 每条问题可用 `文件:行号` 复核原文。
- 机检结论以实际命令输出为准，不用历史任务的结论替代。
- 修复批次的实际验证：`python3 scripts/validate-wf-design.py`（结构 + 覆盖率）、`python3 -m unittest scripts.tests.test_validate_wf_design`（机检回归）、`python3 scripts/check-doc-refs.py`（跨文档引用），并以 `git diff` 复核每条改动只落在声明范围。

## 回滚点

本任务只新增任务目录内文件；如需回退，删除本任务目录或 `task.py archive` 即可，不触及产品资产。
