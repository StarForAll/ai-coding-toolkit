# 执行计划：v31 修订

## 顺序

1. [ ] 记录基线：`git status --short docs/workflows`。
2. [ ] 主设计 frontmatter（v31 + version_note）、卷首引文。
3. [ ] §0 事实边界补“边只表达尚未满足的顺序”。
4. [ ] §0.1 口径 3 取舍清单补同款；A1/A4/B1/B6 验收列对齐正文。
5. [ ] §3 补 SOP、建边；返工任务条目标注简称 R。
6. [ ] §4.2 写入者补启动评估；§4.4 补归档前置仅来自继承。
7. [ ] §5.5 与 §6.6 补替代任务继承口径。
8. [ ] §7.3 与 §7.7 保留理由改写。
9. [ ] §7.5 建边段落整段重写。
10. [ ] §7.7 组合表（规划中行 + 等待判定）、类型 2 限定、类型 4 例子收敛。
11. [ ] §8.4 三段重构。
12. [ ] §9.1 三段重构。
13. [ ] §9.2 表 9-2 对齐 §7.5。
14. [ ] §10 补 SOP/迁移、自检三条、版本表述。
15. [ ] 附录 B 的 F → R；附录 C 新增 v31 条（置于 v30 之前）。
16. [ ] 配套文档：frontmatter、§2、§3、§6.7、§8（组合表与类型 1–5）、§12、§13、§19 修订条。
17. [ ] 结构验证与交叉对读（见 design.md 验证节）。
18. [ ] 七条路径走查，记结论；不一致回改。
19. [ ] `git diff` 通读，确认无补丁痕迹。

## 验证命令

```bash
rg -n '新前置必须为正常' docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
rg -n '归档区' docs/workflows/workflow-design.md
rg -n '挂起阶段|非挂起阶段' docs/workflows/workflow-design.md
rg -n '^### v31|^## 19\.' docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md
rg -n '\bF\b' docs/workflows/workflow-design.md | tail -20
```

## 复核门

- 门 1（步骤 10 后）：组合表每行都有唯一出口，且“等待”与“不一致”两类不再混用。
- 门 2（步骤 12 后）：挂起子表 4 行互斥、含指针为空；非挂起阶段无挂起重叠行。
- 门 3（步骤 16 后）：主设计与配套的组合表、类型措辞逐条对应。
- 门 4（步骤 19 后）：diff 通读，无“另外/补充说明”式的追加句。

## 回滚点

每完成一个段落后 diff 该段；整轮失败则 `git checkout -- docs/workflows/workflow-design.md docs/workflows/依赖机制设计说明.md`。
