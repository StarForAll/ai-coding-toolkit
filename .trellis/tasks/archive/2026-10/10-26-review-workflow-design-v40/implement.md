# implement.md — v41 修复执行计划（F1/F2 + 防复发闸口）

来源：本任务 `review-report.md`（主发现 F1/F2、自审 N1–N4、根因 R1–R5）。
原则：**非补丁式**——每处修复都落在根因对应位点；**不引入新问题**——只改下列清单内的字符串，禁止顺手改其他措辞；**不遗留**——清单覆盖报告列出的全部同步位点（含 N1/N2 扩展面）。

## 总纪律（执行者必读）

1. 所有编辑用精确字符串替换（本清单的 old_string 逐字复制自当前文件，含全角引号 “ ” 与破折号 ——）。若某条 old_string 在文件中找不到或多处命中，**停下报告，不得临场改写措辞**。
2. 行号仅供定位参考，编辑后行号会漂移，以字符串为准。
3. 不修改 `1.2-零补丁嵌入方案.md`（用户指示忽略）。
4. 不执行 git commit（收尾与提交由人工审查后决定）。
5. W1 已复核为误报（原文格式正确），不修。W3 不修（§3 已封逻辑，避免无谓扰动）。

## 文件 A：docs/workflows/workflow-design.md

### A1 版本字段
- old: `version: v40`
- new: `version: v41`

### A2 frontmatter status 追加 v41 摘要
- old: `自证清单入版本库与收敛声明边界（口径 11 / §10 / §0.1）`
- new: `自证清单入版本库与收敛声明边界（口径 11 / §10 / §0.1）；v41 审查修复：处分终态谓词改继任者枝（§7.4 四处同版）、类型 5 窗口⑤同口径、替换指向生命周期与 P 链式解析（§7.8 / §6.5）、放弃-新建替代补继承（§6.6 发起 / 配套 §6.5 发起与实施第 2 步）、§10 自检补完成后重启两场景、口径 10④ 补字段轴、口径 11③ 探针改必查`

### A3 标题
- old: `# 工作流整体设计（v40 · 修订）`
- new: `# 工作流整体设计（v41 · 修订）`

### A4 §7.4 表行——终态谓词（F1 核心）
- old: `**处分未完成**（替换指向仍在、下游仍指向该任务、该任务未归档——三者任一）→ 按 §7.7 类型 5 向前完成，下游或改依赖继任者、或随删边继续；**处分已到终态**（已归档 + 替换指向为空 + 下游已不指向它）→ 无需动作。`
- new: `**处分未完成**（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）→ 按 §7.7 类型 5 向前完成，下游或改依赖继任者、或随删边继续；**处分已到终态**（已归档，且下游已不指向它，且（无替换指向 或 继任者已建））→ 无需动作。`

### A5 §7.4 口径句——同款谓词（含生命周期锚点）
- old: `处分未完成（替换指向仍在、下游仍指向该任务、该任务未归档）→ 按 §7.7 类型 5 向前完成；处分已到终态（已归档 + 替换指向为空 + 下游已不指向它）→ 无需动作；`
- new: `处分未完成（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）→ 按 §7.7 类型 5 向前完成；处分已到终态（已归档，且下游已不指向它，且（无替换指向 或 继任者已建）——替换指向不清空，有指向时以继任者已建为完成，见 §7.8）→ 无需动作；`

### A6 §7.7 类型 5 窗口⑤收紧（N2，与 A4/A5 同口径）
- old: `⑤ 已归档且继任者已建或下游已删边 → 组合表“已归档 + 异常”合法，收敛；`
- new: `⑤ 已归档、下游已不指向它，且继任者已建或无替换指向（与 §7.4 终态谓词同口径）→ 组合表“已归档 + 异常”合法，收敛；`

### A7 §7.8 新增替换指向生命周期条款（治根因 R2）
- old: `改判为放弃时替换指向按 §7.7 类型 5 处置（一般任务置空、P 沿用预写标识且不置空）；`
- new: `改判为放弃时替换指向按 §7.7 类型 5 处置（一般任务置空、P 沿用预写标识且不置空）；
- **替换指向的双重用途与生命周期**：它既是向前完成的补建识别标记，又是继任关系的持久身份记录（P 的角色解析沿它逐任进行，§6.5）；两个用途都不要求用后清空——终态判定不依赖指向为空（§7.4：有指向时以继任者已建为完成），继任者以“指向可解析到已存在任务”判定；已归档“异常”任务的账本不再改写（表 4-2 无“异常 →”转移），指向随账本长期保留；`

### A8 §6.5 P 条款补链式解析（N3）
- old: `基线产物（项目文档、任务图）由继任者续写。`
- new: `基线产物（项目文档、任务图）由继任者续写。P 按角色解析沿替换指向链逐任进行：链上已归档且处分已到终态（§7.4）的中间继任者不再作为判定对象，解析到链尾未归档的继任者为止。`

### A9 §6.6 发起静态校验补继承项（N1，与 §6.5 发起对称）
- old: `机制做实施前静态校验（旧任务未归档、旧任务账本为“无记录”或“挂起”、下游边删除/替代后不成环），新建替代变体同时预生成替代任务的依赖标识`
- new: `机制做实施前静态校验（旧任务未归档、旧任务账本为“无记录”或“挂起”、新任务继承的前置集合 = 旧任务当前前置集合、下游边删除/替代后不成环），新建替代变体同时预生成替代任务的依赖标识`

### A10 §0.1 口径 10④ 情形矩阵补字段轴（闸口 2）
- old: `④枚举同一情形被两条规则分别管辖的组合（情形矩阵），逐条核对是否已有唯一口径`
- new: `④枚举同一情形被两条规则分别管辖的组合（情形矩阵，轴须含承重字段——如替换指向有/无 × 继任者已建/未建 × 归档前后，只按继任形态扫描会漏字段谓词冲突），逐条核对是否已有唯一口径`

### A11 §0.1 口径 11③ 探针项改必查（闸口 1 文档侧 + W2）
- old: `③本项目自有的探针清单中标记为它的条目（探针本身由实现方案承载，见口径 4；本项目未维护清单时本项不适用）。`
- new: `③本项目自有的探针清单中标记为它的条目（探针本身由实现方案承载，见口径 4；维护了清单时本项为必查——须实际执行探针并逐条核对期望值，期望值随判定改动同版更新；未维护清单时本项不适用）。`

### A12 §10 自检补两场景（闸口 3）
- old: `（一般任务：替换指向置空、下游删边、旧任务归档；项目层任务 P：新建替代、沿用预写指向不置空）→ 一次对前置不全正常的`
- new: `（一般任务：替换指向置空、下游删边、旧任务归档；项目层任务 P：新建替代、沿用预写指向不置空）→ 一次替换**正常完成**后重启（§7.4 判处分已到终态、不重入类型 5）→ 一次放弃-新建替代**正常完成**后重启（同上）→ 一次对前置不全正常的`

### A13 §10 自检情形矩阵标注补轴
- old: `情形矩阵（**继任形态 × 归档前后逐格**）`
- new: `情形矩阵（**继任形态 × 归档前后 × 替换指向有/无，逐格**）`

### A14 §10 版本可追溯
- old: `必须等于本文件版本（v40）；配套文档的 \`design\` 字段必须写明本文件版本（\`workflow-design.md v40\`）。`
- new: `必须等于本文件版本（v41）；配套文档的 \`design\` 字段必须写明本文件版本（\`workflow-design.md v41\`）。`

### A15 附录 C 新增 v41 条目（含路径核算表，不写无核算的覆盖断言）
- old: `## 附录 C：本版修订

### v40`
- new: `## 附录 C：本版修订

### v41

- **处分终态谓词改继任者枝（源在 §7.4）**：处分已到终态由「已归档 + 替换指向为空 + 下游已不指向它」改为「已归档，且下游已不指向它，且（无替换指向 或 继任者已建）」；处分未完成改为「有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一」。旧谓词把删边变体独有的终态形状升格为全部异常任务的终态，而替换、放弃-新建替代、类型 1 的 P 分支、类型 5 补建、改判放弃（P）五条路径保留指向，正常完成后被反复判为未完成。**路径核算**（八条产生路径全覆盖）：指向为空族三路径（删边变体、类型 1 一般任务、类型 5 无指向分支/改判-一般）入「无替换指向」枝；有指向族五路径入「继任者已建」枝；崩溃残留「有指向 + 继任者不存在」入未完成，与窗口①一致；启动识别句（§7.7 绕过兜底）与新谓词逐字段一致。四处同版：§7.4 表行与口径句、配套 §5 状态表行与表后段；§7.7 类型 5 窗口⑤同步收紧为同口径。
- **替换指向生命周期与 P 链式解析（源在 §7.8、§6.5）**：§7.8 新增双重用途条款（补建识别标记 + 继任关系持久身份记录，终态判定不依赖指向为空）；§6.5 补「P 按角色解析沿替换指向链逐任进行」。此前该字段同时承担两个对终态要求相反的用途却从未定义生命周期，是谓词反复漂移的根因。
- **放弃-新建替代补继承（源在 §6.6、配套 §6.5）**：主稿 §6.6 发起静态校验与配套 §6.5 发起补「新任务继承的前置集合 = 旧任务当前前置集合」（与 §6.5 / 配套 §6.4 发起对称）；配套 §6.5 实施第 2 步补「继承旧任务当前的前置集合」——此前配套缺句，照配套实现会让替代任务空前置直接就绪、跳过旧任务未满足的前置。
- **审查面补强**：§0.1 口径 10④ 情形矩阵补字段轴；口径 11③ 探针项由「未维护不适用」改为「维护了必查、须实际执行并核对期望值」；§10 自检补「替换 / 放弃-新建替代正常完成后重启」两场景，情形矩阵标注补字段轴。
- **版本**：本文件 v41；配套 v41；\`implements_design\` 必须 pin v41。

### v40`

## 文件 B：docs/workflows/依赖机制设计说明.md

### B1 版本字段
- old: `version: v40`
- new: `version: v41`

### B2 design 字段
- old: `design: workflow-design.md v40`
- new: `design: workflow-design.md v41`

### B3 抬头同步版本
- old: `随主设计 [workflow-design.md](./workflow-design.md) v40 同步`
- new: `随主设计 [workflow-design.md](./workflow-design.md) v41 同步`

### B4 §5 状态表行——终态谓词镜像（F1）
- old: `处分未完成（替换指向仍在、下游仍指向该任务、该任务未归档）→ 按主设计 §7.7 类型 5 向前完成；处分已到终态（已归档 + 替换指向为空 + 下游已不指向它）→ 无需动作；`
- new: `处分未完成（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）→ 按主设计 §7.7 类型 5 向前完成；处分已到终态（已归档，且下游已不指向它，且（无替换指向 或 继任者已建））→ 无需动作；`

### B5 §5 表后段——同款镜像（F1）
- old: `处分未完成（替换指向仍在、下游仍指向该任务、该任务未归档）按主设计 §7.7 类型 5 向前完成，处分已到终态（已归档 + 替换指向为空 + 下游已不指向它）无需动作；`
- new: `处分未完成（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）按主设计 §7.7 类型 5 向前完成，处分已到终态（已归档，且下游已不指向它，且（无替换指向 或 继任者已建））无需动作；`

### B6 §6.5 发起静态校验补继承项（N1）
- old: `机制做实施前静态校验（旧任务未归档、旧任务账本为“无记录”或“挂起”、下游边删除/替代后不成环），新建替代变体同时预生成替代任务的依赖标识`
- new: `机制做实施前静态校验（旧任务未归档、旧任务账本为“无记录”或“挂起”、新任务继承的前置集合 = 旧任务当前前置集合、下游边删除/替代后不成环），新建替代变体同时预生成替代任务的依赖标识`

### B7 §6.5 实施第 2 步补继承（F2 核心）
- old: `   - **新建替代**：用第 1 步预写的标识创建替代任务，再按 §6.4 的重连规则把下游改依赖替代任务。`
- new: `   - **新建替代**：用第 1 步预写的标识创建替代任务，**继承旧任务当前的前置集合**（与 §6.4 实施第 2 步同款），再按 §6.4 的重连规则把下游改依赖替代任务。`

### B8 §9 生命周期镜像（R2）
- old: `改判为放弃时替换指向按主设计 §7.7 类型 5 处置（一般任务置空、P 沿用预写标识且不置空）。`
- new: `改判为放弃时替换指向按主设计 §7.7 类型 5 处置（一般任务置空、P 沿用预写标识且不置空）。
- **替换指向不清空**：终态判定不依赖指向为空（主设计 §7.4：有指向时以继任者已建为完成），补建识别与继任身份（P 的角色解析，主设计 §6.5）共用该字段；已归档“异常”任务的账本不再改写（主设计表 4-2 无“异常 →”转移）。`

### B9 新增 §29 修订记录
- old: `- **版本**：v40；\`design: workflow-design.md v40\`；与主设计 v40 同版。`
- new: `- **版本**：v40；\`design: workflow-design.md v40\`；与主设计 v40 同版。

## 29. 本版修订（v41）

- **§5 终态谓词镜像（镜像主设计 §7.4）**：处分未完成 / 已到终态改为与主设计 v41 相同的字段谓词（有指向时以继任者已建为完成，不再要求指向为空）；状态表行与表后段两处同版。
- **§6.5 放弃补继承（镜像主设计 §6.6 / §6.4）**：发起静态校验补「新任务继承的前置集合 = 旧任务当前前置集合」；实施第 2 步新建替代补「继承旧任务当前的前置集合」，与 §6.4（替换）对称——此前缺句，照本文实现会让替代任务空前置直接就绪。
- **§9 替换指向生命周期镜像**：补「替换指向不清空、终态判定不依赖指向为空」一句（主设计 §7.8 为源）。
- 版本 v41；\`design: workflow-design.md v41\`；与主设计 v41 同版。`

## 文件 C：.trellis/spec/docs/index.md

### C1 探针块抬头改 v41 + 执行义务（闸口 1）
- old: `Probes — run after any \`workflow-design.md\` revision, against both documents
(expected values as of v40):`
- new: `Probes — run after any \`workflow-design.md\` revision, against both documents
(expected values as of v41). The run is mandatory, not optional: update expected
values in the same pass as any predicate change — a registered probe with a
stale expected value that nobody runs is exactly how v40's disposition-terminal
defect escaped (see blind spot 12 in the design-review guide):`

### C2 注册表补终态谓词行（插在 “Disposition of an abnormal task's downstream” 行之后）
- old: `| Successor identity（放弃-新建替代） |`
- new: `| Disposition-terminal predicate | 主设计 §7.4 | “处分已到终态（已归档，且下游已不指向它，且（无替换指向 或 继任者已建））”“处分未完成（有替换指向而继任者不存在、下游仍指向该任务、该任务未归档——三者任一）”；配套 §5 行 + 表后段为同句镜像 | The v40 shape “已归档 + 替换指向为空 + 下游已不指向它” — the 补建 / 新建替代 / 类型 1 paths never clear the pointer, so the old terminal is unreachable on five of eight producing paths |
| Successor identity（放弃-新建替代） |`

### C3 探针 P12 注释更新
- old: `rg -n "下游仍指向该任务、该任务未归档" docs/workflows               # 6 hits as of v40: 4 normative (main §7.4 row + 口径句, companion §5 row + 表后段) + 2 revision records`
- new: `rg -n "下游仍指向该任务、该任务未归档" docs/workflows               # 4 normative (main §7.4 row + 口径句, companion §5 row + 表后段) + revision records (count drifts per version; the phrase must stay contiguous in all four predicate sites)`

### C4 探针 P15 注释更新
- old: `rg -n "替换指向为空" docs/workflows                                  # only 删边-variant lines: main §6.6 step 1 + companion §6.5 step 1`
- new: `rg -n "替换指向为空" docs/workflows                                  # 删边-variant step lines only (main §6.6 step 1 + companion §6.5 step 1) + revision records; the v41 terminal predicate deliberately uses 「无替换指向 / 继任者已建」 — a new normative hit here means the v40 terminal shape returned`

### C5 新增两条探针（追加在探针代码块末尾，`rg -n "无当前任务时按 §9.1"` 行之后）
- old: `rg -n "无当前任务时按 §9.1" docs/workflows                            # 2 hits: §8.4 第三段 (normative) + v31 appendix record
````
- new: `rg -n "无当前任务时按 §9.1" docs/workflows                            # 2 hits: §8.4 第三段 (normative) + v31 appendix record
rg -n "继任者已建" docs/workflows                                      # 6 hits as of v41: 4 predicate sites (main §7.4 row + 口径句, companion §5 row + 表后段) + main §7.7 窗口⑤ + v41 record; a predicate site missing this phrase means the old v40 shape returned
rg -n "新建替代" docs/workflows/依赖机制设计说明.md                      # 发起 / 实施第1步 / 实施第2步 / §9；实施第2步必须含「继承旧任务当前的前置集合」（v41），缺句即 F2 回归
``` ``

（注意：C5 的 old/new 中代码块结尾反引号按文件实际内容处理——先读取该区域确认围栏形态再编辑；若围栏形态与上述不符，停下报告。）

## 文件 D：.trellis/spec/guides/design-review-thinking-guide.md

### D1 盲点清单补第 12 条（插在盲点 11 之后）
- old: `11. **Action sequence defined twice, in different orders.** The same forward
   completion chain existed as an archive-first list (§6.5 / 配套 §6.4) and a
   build-first sentence (§7.7 类型 5). Order is load-bearing: archiving first
   makes the later 补建 look like "替换一个已归档任务", i.e. exactly the state
   the disposition rule forbids. Fix pattern: exactly one declared source per
   multi-step sequence (v40: §7.7 类型 5), mirrors stay same-order and
   reference-only, and §0 now bans a second sequence with a different order.`
- new: 同上原文 + 新增：
`
12. **Predicate rewritten without reachability accounting.** When a limitation
   is rewritten as a field predicate (v40 §7.4), the terminal shape must be
   evaluated on every producing path of the state it judges; v40 induced
   "pointer empty" from the 删边 variant alone while five paths keep the
   pointer, so the terminal was unreachable on daily success paths. The
   revision note claimed "一次覆盖四种形态" as an assertion, and every
   text-level gate (copy list, reference replay, window table, same-order
   mirror) passed — only a path-accounting table catches it. Fix pattern: the
   revision note must carry a path-accounting table (each producing path →
   predicate verdict); a coverage claim without the table is not done.
   Companion obligations: register a probe for the predicate's characteristic
   phrase and actually run the probes per revision — a registered probe with
   a stale expected value that nobody runs is how this class escapes (v41
   §0.1 口径 11③ added the run obligation).`

## 验证（执行完成后必跑，结果写入报告）

1. `rg -n "替换指向为空" docs/workflows` — 规范位应只剩主稿 §6.6 第 1 步 + 配套 §6.5 第 1 步两处删边步骤句。
2. `rg -n "继任者已建" docs/workflows` — 应含主稿 §7.4 两处 + 配套 §5 两处 + §7.7 窗口⑤。
3. `rg -n "下游仍指向该任务、该任务未归档" docs/workflows` — 四处谓词位保持该连续子串。
4. 重跑 index.md 探针清单全部条目（对照 v41 预期值），逐条记录实际命中数。
5. `python3 .trellis/scripts/task.py validate .trellis/tasks/10-26-review-workflow-design-v40`
6. 复核最终 diff：`git diff --stat` + 逐文件 `git diff`，确认无清单外改动。

## 回滚点

单次会话内完成全部编辑；任一 old_string 失配即停（不产生半应用状态之外的新风险——已应用编辑保持原样并报告进度，等待指示）。
