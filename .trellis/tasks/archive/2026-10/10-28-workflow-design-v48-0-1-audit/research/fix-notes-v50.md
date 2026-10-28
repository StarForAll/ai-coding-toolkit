# v50 修复记录

根因、类别扫描与修正判定见 `review-report-v50.md`。清单行号由 `finalize_v50_records.py` 按锚点生成；每个旧/新字符串以 `verify_v50.py` 核验。

| ID | 文件 | 落点锚点 | 脚本行号 | 验收位 | 结果 |
|---|---|---|---|---|---|
| V50-01 | docs/workflows/workflow-design.md | §4.4 族2标题 | docs/workflows/workflow-design.md:314 | probe新标题=1、旧标题=0；v50族表枚举回查 | 已同步 |
| V50-02 | docs/workflows/workflow-design.md | §7.7 类型5改判放弃-一般 | docs/workflows/workflow-design.md:683 | 类型5四分支归档守卫矩阵=4/4 | 已同步 |
| V50-03 | docs/workflows/workflow-design.md | §7.7 类型5改判放弃-P | docs/workflows/workflow-design.md:683 | 类型5四分支归档守卫矩阵=4/4 | 已同步 |
| V50-04 | docs/workflows/workflow-design.md | §7.7 类型1一般任务 | docs/workflows/workflow-design.md:675 | probe统一归档守卫=5个规范位 | 已同步 |
| V50-05 | docs/workflows/workflow-design.md | §9.1 第二段挂起行第三行 | docs/workflows/workflow-design.md:802 | probe挂起下沉递归=1；D3递归状态表；自检 | 已同步 |
| V50-06 | docs/workflows/workflow-design.md | §9.1 第二段挂起行第一行 | docs/workflows/workflow-design.md:800 | probe返工任务递归挂起=1；D3递归状态表 | 已同步 |
| V50-07 | docs/workflows/workflow-design.md | §9.1 说明区下沉范围 | docs/workflows/workflow-design.md:833 | probe新说明=1、旧说明=0；引用命中D2 | 已同步 |
| V50-08 | docs/workflows/workflow-design.md | §8.4 第二段挂起摘要 | docs/workflows/workflow-design.md:775 | probe8.4递归引用=1；引用命中D2 | 已同步 |
| V50-09 | docs/workflows/workflow-design.md | §10 挂起递归自检 | docs/workflows/workflow-design.md:911 | probeQ挂起用例=1；D3 recursive state case | 已同步 |
| V50-10 | docs/workflows/workflow-design.md | §9.1 第二段上下文定义 | docs/workflows/workflow-design.md:796 | D3递归状态表；probe上下文=1；指针边界不变 | 已同步 |
| V50-11 | docs/workflows/workflow-design.md | §8.4 第二段返工引用 | docs/workflows/workflow-design.md:773 | D2命中§9.1第二段行1；probe引用=1 | 已同步 |
| V50-12 | docs/workflows/workflow-design.md | frontmatter version | docs/workflows/workflow-design.md:3 | 两文档版本同为v50 | 已同步 |
| V50-13 | docs/workflows/workflow-design.md | main title | docs/workflows/workflow-design.md:13 | 标题与frontmatter同版 | 已同步 |
| V50-14 | docs/workflows/workflow-design.md | status suffix | docs/workflows/workflow-design.md:5 | status含v50修订摘要 | 已同步 |
| V50-15 | docs/workflows/workflow-design.md | §10 implements_design pin | docs/workflows/workflow-design.md:906 | 版本引用探针；§标签范围核验 | 已同步 |
| V50-16 | docs/workflows/workflow-design.md | §10 companion design pin | docs/workflows/workflow-design.md:906 | 版本引用探针；§标签范围核验 | 已同步 |
| V50-17 | docs/workflows/依赖机制设计说明.md | companion frontmatter version | docs/workflows/依赖机制设计说明.md:3 | 两文档版本同为v50 | 已同步 |
| V50-18 | docs/workflows/依赖机制设计说明.md | companion design pin | docs/workflows/依赖机制设计说明.md:4 | 两文档design pin一致 | 已同步 |
| V50-19 | docs/workflows/依赖机制设计说明.md | companion sync header | docs/workflows/依赖机制设计说明.md:13 | 抬头与frontmatter同版 | 已同步 |
| V50-20 | docs/workflows/workflow-design.md | Appendix C v49 source classification | docs/workflows/workflow-design.md:977 | D4源/副本登记回查；旧源短语=0 | 已同步 |
| V50-21 | docs/workflows/workflow-design.md | Appendix C v49 copy classification | docs/workflows/workflow-design.md:978 | D4源/副本登记回查；§8.4引用式=1 | 已同步 |
| V50-22 | docs/workflows/workflow-design.md | §7.7 hanging combination row | docs/workflows/workflow-design.md:660 | 主稿挂起组合表镜像引用probe=1 | 已同步 |
| V50-23 | docs/workflows/依赖机制设计说明.md | companion §8 hanging combination row | docs/workflows/依赖机制设计说明.md:253 | 配套挂起组合表镜像引用probe=1 | 已同步 |
| V50-24 | .trellis/spec/docs/index.md | probe baseline annotation | .trellis/spec/docs/index.md:315 | 全文版本基准注= v50 | 已同步 |
| V50-25 | .trellis/spec/docs/index.md | v49 launch probe expected count | .trellis/spec/docs/index.md:393 | v50全量探针实际=1 | 已同步 |
| V50-26 | .trellis/spec/docs/index.md | v50 regression probes | .trellis/spec/docs/index.md:398 | 每条probe逐项全量比对注释 | 已同步 |
| V50-27 | .trellis/spec/guides/design-review-thinking-guide.md | guide blind spot 25 paired check | .trellis/spec/guides/design-review-thinking-guide.md:375 | guide probe + verifier四分支断言 | 已同步 |
| V50-28 | docs/workflows/workflow-design.md | Appendix C v50 insertion | docs/workflows/workflow-design.md:946 | D4 record/body grep + generated line references | 已同步 |
| V50-29 | docs/workflows/依赖机制设计说明.md | companion §38 v50 insertion | docs/workflows/依赖机制设计说明.md:517 | D4 record/body grep + generated line references | 已同步 |
| V50-30 | .trellis/spec/docs/index.md | archive guard probe expectation | .trellis/spec/docs/index.md:394 | rg -n=4 lines; rg -o=5 occurrences; four named type-5 branches | 已同步 |

## 脚本生成的版本记录行号

附录 C v50 与配套 §38 的所有“已同步”路径和行号由 `finalize_v50_records.py` 生成；`verify_v50.py` 逐条确认目标行内容及章节范围。

## 根因 / 修复面

- P1/P6：类型5终归档动作全集只有四处，补建与无指向分支有守卫、两个改判分支漏守卫；统一四处分支文案，并以动作调用位而非全篇词频验收。
- P2：前置状态表没有递归展开所下沉对象自身的依赖状态；挂起的前置回到同一第二段表按已有行1–4匹配，阻塞只在递归处理后判定。
- P3：下沉位置由一个扩展到第二段第3行，说明句同步列出两个调用位。
- P4：族2标题同步扩展为建边与返工加边。
- P5：v49记录中的§8.4是被改的接手摘要副本，不是规则源；更正源/副本字段，不改规则正文。
