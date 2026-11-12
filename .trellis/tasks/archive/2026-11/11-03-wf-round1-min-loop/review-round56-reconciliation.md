# 第五十六轮：第十二轮独立复审（复验轮）——A1 判成立

- 处置编号 R91；实跑见 `validation.md` §83
- 结论：**A1「成立 / 修复可接受」**；本轮只处理了复审与其他 agent 提出的 2 条小项 + 1 处口径张力。

## 1. A1 复验结果（复审原文要点）

| 项 | 结果 |
|---|---|
| 7 个注入点（create_dir 前/后、write_record 后、acquire 后、bind 后、结案前、结案后响应前） | **全部通过**：续做同一 task_id、按需重建缺失产物、步骤状态与后置一致 |
| D1 早期中断 | 通过（1–3 点均 WF_OK，无 `WF_PERSISTENCE_FAILED`） |
| D2 实例固定 | 通过（删绑定 + 新 instance 重入 → `WF_BINDING_MISMATCH`） |
| D3 伪造 done | 通过（仍重建真实后置） |
| D4 旧 `task.action` | 通过（`WF_RECORD_INVALID` + repair 出口） |
| 篡改 targets 的 task id | 通过（已有绑定时 `WF_BINDING_MISMATCH`，未放行） |
| r87 / r88 实跑 | 11/11、7/7，退出 0 |
| Finish→Check 独立链 | 通过（回 check、旧检查登记 invalidation、门禁 stale、再次 Check 生成新 id） |

未覆盖：真实断电、并发竞争、`repair` 接管路径——已写入实现稿状态行的未覆盖轴。

## 2. 本轮实际改动

### P1-1 `repair --dispose` 的锁忙出口（真实问题，已修）

dispose 的设计是"不要求写权空闲、只需互斥"，但它复用了 `WF_WRITER_BUSY`，而该码的 `prohibited_repairs` 写的是"不超时抢占；不删除锁或写权记录"——把人引向"处理写权"，方向与 dispose 的实际需要相反。

修法（最小）：锁忙分支的文案与 facts 明确写出"该动作不要求写权空闲、只需互斥，稍后重试即可（无需交接/抢占写权）"，并给 `guidance` 字段。不改码表（码表属机制稿）。

### P3 死分支（已删）

`gates.py` 里 `if not task.get("prerequisites"): pass` 是占位残留，删除后 57 项回归无变化。

### 口径张力（已消解）

复审指出：状态行自称"按已覆盖轴定稿（两轮独立 CLI 复审）"，而 R85–R90 的修订按收口计划是"独立复审按人决定暂不执行"，两者有张力。

处理：状态行重写为**如实披露**——12 轮逐轮定向复审、哪一轮审了哪块、第十二轮复验判成立，并列出未覆盖轴（真实断电/并发/repair 接管、D1 绑定轴、dogfood 观察）。不再用"定稿"覆盖未复审的事实。

## 3. 登记（不阻塞）

`pending-decisions.md` §4 新增：`status` 维护态观测（P1-2，复审建议维持）、`probe_version` 冗余解析、`uninstall` 预览近似计数、skill 纪律段重复（裁量）、**dogfood 建议尽快启动**、E 轨道的口径已消解。

复审自己撤回的一条（"Check 执行期间锁未持有"）已核实不成立：`cmd_task_check` 的锁覆盖整个 `run_check` 生命周期。

## 4. 口径

十二轮独立复审 + 其他 agent 累计：**80 条已处置、9 条登记**（其中 0 条阻塞）。

按复审的措辞：**A1 的修复可接受**；实现稿状态行已按"覆盖范围 + 未覆盖轴"如实表述，不再与收口计划冲突。
