# v49 修复记录

基于第二轮扫描及已批准的 M1–M15 清单。old/new 落点与 `已同步` 后的行号由本脚本按唯一文本锚点生成；修改后若行号变化，重新运行本脚本。

## 根因与范围

- F1 根因：成员全集没有同一动作全集交叉表；“建边”收窄后，没有复核返工加边写者，调用位/probe 只保证短语存在。M1/M2/M3/M4修源与两处枚举；Guide 25要求先出全集矩阵。
- F2 根因：以引用章节名代替命中类型/行的前提检查；“按§7.7对账”在挂起合法等待态没有任何类型输入可匹配，并与“命中即停止”说明冲突。M5–M9补具体下沉动作、同状态镜像与验收。
- P2/P3/P4 根因及处理：类型5借用归档动作未写归档态幂等性；局部两出口表述使用全局“只有”；配套场景投影遗漏移交守卫。分别由M10、M11、M12限定。

## 修复清单及脚本行号

| ID | 源 / 镜像 | § / 锚点 | 脚本位置 | 处理 |
|---|---|---|---|---|
| M1 | docs/workflows/workflow-design.md | §4.4 族2 | docs/workflows/workflow-design.md:314 | 已同步 |
| M2 | docs/workflows/workflow-design.md | §4.4 族注记 | docs/workflows/workflow-design.md:318 | 已同步 |
| M3 | docs/workflows/workflow-design.md | §0.1 口径10⑤ | docs/workflows/workflow-design.md:66 | 已同步 |
| M4 | docs/workflows/workflow-design.md | §0.1 口径尾段 | docs/workflows/workflow-design.md:72 | 已同步 |
| M5 | docs/workflows/workflow-design.md | §9.1 挂起表第3行 | docs/workflows/workflow-design.md:802 | 已同步 |
| M6 | docs/workflows/workflow-design.md | §8.4 挂起第3条 | docs/workflows/workflow-design.md:775 | 已同步 |
| M7a | docs/workflows/workflow-design.md | §7.7 组合表挂起行出口 | docs/workflows/workflow-design.md:660 | 已同步 |
| M7b | docs/workflows/依赖机制设计说明.md | §8 组合表挂起行出口 | docs/workflows/依赖机制设计说明.md:253 | 已同步 |
| M8 | docs/workflows/workflow-design.md | §9.1 说明区 | docs/workflows/workflow-design.md:832 | 已同步 |
| M9 | docs/workflows/workflow-design.md | §10 自检场景唯一锚点 | docs/workflows/workflow-design.md:911 | 已同步 |
| M10a | docs/workflows/workflow-design.md | §7.7 类型5补建 | docs/workflows/workflow-design.md:682 | 已同步 |
| M10b | docs/workflows/workflow-design.md | §7.7 类型5无指向 | docs/workflows/workflow-design.md:684 | 已同步 |
| M11 | docs/workflows/workflow-design.md | §5.5 轻量用法 | docs/workflows/workflow-design.md:389 | 已同步 |
| M12 | docs/workflows/依赖机制设计说明.md | §12 返工完成场景行 | docs/workflows/依赖机制设计说明.md:317 | 已同步 |
| M14 | .trellis/spec/docs/index.md | Predicate Registry and Probes 的探针块 | .trellis/spec/docs/index.md:389 | 已同步 |
| M15 | .trellis/spec/guides/design-review-thinking-guide.md | blind spots末尾 | .trellis/spec/guides/design-review-thinking-guide.md:375 | 已同步 |
| M14b | .trellis/spec/docs/index.md | Predicate Registry：Archived-prerequisite source list | .trellis/spec/docs/index.md:305 | 已同步 |
| M13a | docs/workflows/workflow-design.md | frontmatter version | docs/workflows/workflow-design.md:3 | 已同步 |
| M13b | docs/workflows/workflow-design.md | title | docs/workflows/workflow-design.md:13 | 已同步 |
| M13c | docs/workflows/workflow-design.md | §10 implements_design pin | docs/workflows/workflow-design.md:906 | 已同步 |
| M13d | docs/workflows/workflow-design.md | §10 companion design pin | docs/workflows/workflow-design.md:906 | 已同步 |
| M13f | docs/workflows/依赖机制设计说明.md | frontmatter version | docs/workflows/依赖机制设计说明.md:3 | 已同步 |
| M13g | docs/workflows/依赖机制设计说明.md | frontmatter design field | docs/workflows/依赖机制设计说明.md:4 | 已同步 |
| M13h | docs/workflows/依赖机制设计说明.md | header sync version | docs/workflows/依赖机制设计说明.md:13 | 已同步 |
| M13e | docs/workflows/workflow-design.md | frontmatter status | docs/workflows/workflow-design.md:5 | 已同步 |

## 验收位

- M1/M2：族2 source cell 与唯一注记；M3/M4：两份路径族枚举；M14/M14b：注册探针及来源注册表。
- M5/M6/M7a/M7b/M9：状态入口、接手摘要、组合表、配套镜像和连续自检；新增场景在正文 §10。
- M10a/M10b：两处类型5动作的幂等限定和 probe；M11：probe；M12：配套场景行及probe。
- M15：guide盲点25/26；本报告D1–D5和实际运行probe为方法执行记录。
- M13：版本三元一致性；附录C与配套§37的逐项引用行号由 `version_records_v49.py` 生成。

## 未同步项

无。所有“已同步”位点均有上述唯一锚点及脚本产出行号；附录C / 配套§37使用相同生成脚本。
