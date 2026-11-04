# 第五十轮：第七轮独立复审（R50-01..11）+ 其他 agent（P1-1/P1-3、P2-1..P2-5）

- 处置编号 R85；实跑见 `validation.md` §77
- 结论：**复审 8 条已修、3 条按"登记边界"处置；其他 agent 5 条已修、2 条登记**。
- 这一轮暴露的是**同一类问题的第 N 次复发**：跨记录写入的意图/恢复协议，我连着两轮"修好"，两轮都被注入测试推翻。

## 一、跨记录写入（R50-01～07）

| 编号 | 问题 | 处置 |
|---|---|---|
| R50-01（高） | 先建目录、再存无动作的记录，两步之间退出就留下空目录或无意图记录 | 改为**暂存目录一次发布**：模板产物写进 `.staging-<id>` 再 `rename`，记录首次落盘即带 `task.create` 意图（步骤含 done 状态） |
| R50-02（高） | 别人的 `task.create` 意图未完成时，另一个会话仍能取写权建新对象 | 写权获取前 `_any_pending_task_create()` 全仓扫描（不限会话），命中即 `WF_WRITER_BUSY` 并指向续做 |
| R50-03（高） | `bind` 先保存写权授予，再登记 `session.bind` 动作 | 写权与动作意图**同一次写入**：`acquire` 后立刻把 prepared 动作塞进同一记录再 save |
| R50-04（高） | 绑定已写但动作未结案时，已有绑定分支提前返回成功，动作永不结案 | 已有绑定分支先取 live writer 记录、先 `_resume_bind()` 续做结案，再返回 |
| R50-05（高） | bind 恢复用**本次请求**的目标，却结案原动作 | 目标一律取自意图（`action.targets` 里的 task/run），请求目标不符即 `WF_SEMANTIC_DECISION` |
| R50-06（高） | task.create 恢复不核后置：删掉 prd.md 也能结案 | 恢复前逐项核：目录在、模板产物在、绑定对象与意图一致、运行态缺失则重建并留痕 |
| R50-07（中） | 结案保存成功但响应丢失，重试只报 `WF_BINDING_MISMATCH` | 绑定对象对应的动作已 done 时，重核后返回原结果（`already_completed`） |

## 二、其余复审条目

| 编号 | 处置 |
|---|---|
| R50-08（中）索引重复/损坏 | 同一目标去重；索引存在未闭合 ``` 围栏时拒绝同步并给修复出口，不再把"字符串存在"当同步完成 |
| R50-09（中）任意 disabled 当后像 | disable 的后像是改写后的新内容，无法从前后像推定 → 改为**明确交人核对**（`looks_already_disabled`），不静默认作本动作成果 |
| R50-10（中）复盘门禁不核证据 | 新增 `retrospective_evidence_problems()`：裁定引用的调试证据须可核对（check 条目在 / 提交可达 / 路径存在）；`handoff`、`check:<id>` 这类符号引用不按文件判 |
| R50-11（中）安装预览不显示身份 | 预览新增「会话身份（session_profile）」段与 `facts.session_profile`，含 provider / transport / capability.status / evidence_refs |

## 三、其他 agent 的 7 条

| # | 处置 |
|---|---|
| P1-1 外部变更无待决出口 | **登记边界**：`scope_facts.external_pending` 已把数量带进 Check facts，但不新增阻断判定——原因见下节 |
| P1-2 Finish 期规范变更无通路 | **未修，登记**：需要一条 `finish→check` 的受控迁移，属机制面改动，留给人裁决 |
| P1-3 巡检缺归档引用类 | 补 `archive_references.dangling`（prerequisites/rework_of/successor_id 悬空）与终态持久化检查 |
| P2-1 `.wf/out-of-scope/` 未实现 | **登记**：schema 在机制稿里，代码与 skill 零引用，首轮不做 |
| P2-2 纯删除/改名不算交付 | 触碰路径上存在本任务归属的删除/改名事实即算交付成立（`_removal_attributed`） |
| P2-3 initialize 开工不核候选唯一 | 候选唯一性检查移出 `kind == "ordinary"` 分支，对全部 kind 生效 |
| P2-4 门禁把"审查不可用"报成"不合格" | `verdict=unavailable` → `WF_REVIEW_UNAVAILABLE`，与 `WF_REVIEW_INVALID` 分流 |
| P2-5 提示键配置了但永不出现 | `task-approve` 的 facts 带 `complexity_hints`（提醒复评，不自动分类） |

## 四、为什么 P1-1 只登记不实现（诚实说明）

我按建议实现了 Check 阻断，结果**全部 53 项回归有 7 项立刻变红**：夹具里的 `git commit` 没有任务 trailer，于是每个正常流程的 Check 都把"自己刚提交的业务文件"判成外部变更。这不是夹具"不规范"，而是暴露了一个机制面事实——**提交归属靠 trailer，而 trailer 只由框架的提交路径写**；一旦有人在框架外提交（包括测试、包括人手 `git commit`），系统无法把它与"外部变更"区分开。

我先试着给夹具提交补 trailer，随即出现镜像问题：`git commit -A` 把 `.wf/project-config.json` 也带进本任务的提交，落进 f 桶变成越界。

结论：把"外部变更"做成 Check 阻断，需要先补齐**提交归属的判定面**（谁能证明某提交属于本任务），那是机制稿级别的改动，不该在实现轮里顺手加。因此本轮：保留事实字段（`external_pending`），把这条登记为已知边界，并写明它需要什么前置。

## 五、期间新发现（都是我改出来的）

- **N-R89**：给夹具提交补 trailer 后，`.wf/project-config.json` 被带进业务提交 → f 桶越界；已回滚该改动，夹具恢复原样。
- **N-R90**：复盘证据核验最初把 `handoff` 当文件路径 → 合法流程被判缺证据；改为只核"形如路径"的引用。
- **N-R91**：`_pending_task_create` 派生定位用 `or` 兜底 `base_revision`，`0` 被吞成上级 revision（上一轮 N-R82 的同型错误在别处复发）——已改成显式判断。
- **N-R92**：r82/r75/r84 三个用例需要跟随新契约调整（归档持久化只在有 action 时判、治理面新增 `archive_references`、disable 后像改交人核对）。

## 六、口径

七轮独立复审 + 其他 agent 累计处置 55 条、登记 4 条。**跨记录写入连修三轮仍有新洞**，说明这块不是"漏写一行"，而是协议本身需要一次正面设计（意图、后置、恢复、身份四件事的统一定义），下一轮应专门压这里，并接受"审出来的比修掉的多"这个现实。
