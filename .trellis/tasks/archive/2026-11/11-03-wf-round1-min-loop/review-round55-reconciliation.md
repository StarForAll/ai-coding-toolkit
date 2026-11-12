# 第五十五轮：第十一轮独立复审（A 改动的定向复审）——4 条缺陷已修

- 处置编号 R90；实跑见 `validation.md` §82
- 结论：复审裁定 **A1「不成立」**，给出 D1–D5 五条；其中 4 条已修、1 条（D5 文档）随修复同步。**D2 是这一轮最实的一条**。

## 1. 四条缺陷

| 编号 | 缺陷 | 修法 |
|---|---|---|
| **D1**（高） | 早期中断不可恢复：`create_dir` 与 `write_record` 一次发布、同时置 done，重入却要求目录与 `prd.md` 已存在 → `WF_PERSISTENCE_FAILED` | 拆成**逐步推进器** `_run_creation_steps()`：每步先看真实后置，缺什么补什么（`_ensure_creation_step` 幂等重放），再置 done。模板路径/标题/kind 作为不可变目标写进 `targets`，早期中断也能重建目录与产物 |
| **D2**（高） | `instance_id` 没写进意图；重入回退到请求值或新生成值 → 删绑定后用新实例可接管 | 实例作为 `targets` 里的 `{"kind":"instance"}` 固定；重入**先**比对请求携带值与该固定值，不同即 `WF_BINDING_MISMATCH`，不再 fallback 生成 |
| **D3**（高） | 只信步骤字段：手工把四步标 done 即可结案 | 结案前 `_finish_writer_action` 对每个步骤**重核真实后置**（目录/记录/写权 scope/绑定+运行态），不符即 `WF_PERSISTENCE_FAILED`；步骤字段降级为游标 |
| **D4**（中） | 旧任务的 `task.action(kind=task.create)` 在 `task-start` 处永久阻塞 | 识别为**遗留形态**并给明确出口：`WF_RECORD_INVALID` + `remedy` 指向 repair；不再输出"按原意图恢复"这种无法执行的指引 |
| **D5**（中） | 实现稿声称"实例固定、四步可恢复"与实测不符 | 随 D1–D3 修复成立；文档表述保留，但改为逐句对应实现（目标固定清单、逐步后置、结案重核） |

## 2. 复审判"有条件成立"的 Finish→Check

它的直接调用验证全部通过（旧检查保留、不伪造回执、门禁判 stale、两轮 invalidation 独立、迁移后 archive 被拦）。唯一"未覆盖"是 **r87 的 B 段实跑失败**——原因不是实现，而是**测试夹具缺 `.wf/project-config.json`**，`task-start` 直接 `WF_CAPABILITY_UNAVAILABLE`。已在该用例里补上配置创建。

## 3. 期间新发现

- **N-R105**：意图里的 `inputs` 只存摘要、不存原值，早期恢复拿不到模板路径 → 改为写进 `targets`（不可变目标）而不是新增顶层字段。
- **N-R106**：`r84` 的"A3-agent2"用例期望过窄：实例不符时也可能先撞 `WF_WRITER_BUSY`；断言改为"不得放行"，同时保留 D2b 的精确断言。
- **N-R107**：`r87`/`r88` 都依赖夹具的项目配置；已在用例内自带创建，避免依赖夹具顺序。

## 4. 口径

十一轮独立复审 + 其他 agent 累计：**78 条已处置、8 条登记**。A1 从"不成立"回到"四项缺陷已修、注入点待复审确认"。剩余登记项仍不阻塞：`.wf/out-of-scope/`、巡检知识治理两类、`branch_source_check` 消费点、`enable` 残留通道、`review-launch` 不核 invalidated（新登记，门禁可兜底）、若干 P3 工程项。
