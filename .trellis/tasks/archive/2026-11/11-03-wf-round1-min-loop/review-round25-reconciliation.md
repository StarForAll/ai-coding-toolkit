# 第二十五轮外部评审的复核与修正（P1 4 项 / P2 7 项 / P3 建议）

- 处置编号 R62（P1-1…P1-4、P2-1…P2-5 实施）；P2-6、P2-7 与 P3 登记为待修（见 §4）
- 实施与实跑见 `validation.md` §48

## 0. 结论

P1 四条与 P2 前五条**全部成立**，已修；P2-6、P2-7 成立但需设计，登记待修；P3 十余条按约定只登记。逐条判定：P1-1 成立、P1-2 成立、P1-3 成立、P1-4 成立（属未声明裁剪）、P2-1 成立、P2-2 成立、P2-3 成立、P2-4 成立、P2-5 成立、P2-6 成立、P2-7 成立。

## 1. P1 处置（收口前必修，已修）

- **P1-1 审查失败事实丢失**：`review.decide` 现在把本轮结论写回所在尝试的 `outcome`（机制稿 §9.2 的字段终于是活的），round-2 pass 后 round-1 的 fail 仍能重建 `review_fail` 触发。
- **P1-2 调查任务免检**：`work_satisfied_fact` 对空 `touch_paths` 要求可观察成果（人判决定 / 复盘 / 策展 / 已通过 Check），否则 `WF_CHECK_FAILED`。
- **P1-3 spec-update 越权写 knowledge**：改写到 `execution.spec_changes`，`knowledge` 只由 `task-knowledge` 写，`task.knowledge-disposed` 恢复「人处置」语义。
- **P1-4 启动校验无落点**：新增 `tasks.startup_check()`，按机制稿 §5.2 的四段（绑定写者 → 记录可解释 → 对象与依赖 → 工作区）给出 ok/unknown/blocked，**未知优先**；`status` 输出 `startup` 事实。①–⑩ 中实例相关的两步仍按首轮无实例登记，其余落到这一处。

## 2. P2 处置（已修 5 条）

- **P2-1 证据核验**：声明必须带 `evidence_refs`，逐条核可定位（任务内文件、check id、`check:`/`handoff:` 具名引用），`dedupe_refs` 的 `check_id` 必须存在；缺失分别 `WF_SEMANTIC_DECISION`/`WF_HISTORY_UNRESOLVED`。
- **P2-2 Trellis 档位**：「当前宿主配置存在」只是线索，默认 `WF_SEMANTIC_DECISION`；仅当输入声明 `trellis_loaded`（本会话确实加载）才 `WF_FLOW_CONFLICT`。
- **P2-3 run 绑定**：`gate` 对 run 对象改抛 `WF_CAPABILITY_UNAVAILABLE`（tier=round 2），不再落内部错误 70。
- **P2-4 哈希域**：降级条目在 `compute_plan_version` 之后追加，`current_plan_version` 与机械修订重算都剔除 `downgrade` 条目——与机制稿 §1.1 的哈希域一致。同时把 `task.review-passed` 的适用条件从 `complex` 放宽为 `all`，否则轻量任务的降级齐全性没有任何门禁。
- **P2-5 归档后写入**：`task-knowledge`/`task-curate`/`task-retrospect` 补 `status == archived` 拒绝。

## 3. 期间新发现

- **N-R39**：`plan.complexity_reasons` 手改后 `plan-approved` 重算差异掩盖了降级复核（P2-4 让两者一致，反而暴露 review-passed 不被 light 任务适用）→ 修法见 P2-4 末句。

## 4. 待修登记（不视为已完成）

| 项 | 内容 | 出口 |
|---|---|---|
| P2-6 | 检查日志与 `facts` 无秘密边界脱敏（机制稿 §3.5） | 按 `\$\{...\}`/`*_TOKEN` 等已知形态做可见遮罩，并给「不可判定则整段保留」的边界说明 |
| P2-7 | 原语/审查副本缺来源、许可、基线、差异登记（设计稿 §7.4、§7.5） | 在各 SKILL.md 与源树 README 补登记段 |
| P3 | 源树 `__pycache__`、`cmd_spec` 双份正文、`_sync_curation_paths` 不 bump 包络、`stop` 无 WIP 强制 subject、`cmd_bind` 死代码、skill description 写法、`evaluate` 静默 KeyError、启动侧复评触发、`rules_digest` 三份实现缺一致性检查 | 逐条排期；`rules_digest` 建议仿 `--verify-token-parity` 加一致性检查 |
