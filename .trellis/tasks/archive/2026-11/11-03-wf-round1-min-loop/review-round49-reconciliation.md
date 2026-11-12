# 第四十九轮：第六轮独立复审（A3-9/A3-11、B2-1、B4-1）+ 其他 agent（1/2/3/4）

- 处置编号 R84；实跑见 `validation.md` §76
- 结论：**6 条成立并已修**（复审 3 条 + 其他 agent 3 条，其中 2 条重叠）；A2/A4/A5 判通过；B3/B5 判通过、B4 一条按"登记边界"处置。

## 0. 复审已判通过的部分

A2（观察证据判据）、A4（只核结构的解除依赖）、A5（归档恢复三态）、B3（gate 步骤集合）、B5（双入口判据）本轮实机复核通过，未再改动——这几条正好是前四轮反复出问题的地方，说明它们这一版站住了。

## 1. A3-9 改名后索引补不进去（中）

`_sync_index(rename=(source,target))` 只做"把旧路径字符串替换成新路径"。索引里本来就没有旧条目时（初始化骨架、被手工改乱、上次同步失败），**替换无从发生，新路径永远不会出现**——skip 与 apply 两支同构，都受影响。

处置：替换未命中时退回 `add`，把新路径追加进去。所以「跳过正文」与「补索引」现在是两件独立核实的事，符合机制稿 §8.4「索引与 metadata 同步是后置，不单靠文件写成功判完成」。

## 2. A3-11 / #2 disable 的"已是后像"识别不出（中）

`_resume_decision_removal` 对 disable 用摘要比对判后像，但 disable 的后像就是**改写后的新内容**，与 `before_digests` 必不相等 → 框架自己的合法修改被误判为外部冲突，索引补不上。

处置：disable 分支改为「摘要等于前像 → 执行」「解析 frontmatter 得到 `status=disabled` → 跳过（并补索引）」「其余 → 冲突」。

## 3. #1 改名后目标内容被改仍判成功（中）

`source 不在 && target 存在 → skip` 少核了目标内容。处置：有前像时要求 `target_now == before`；没有前像（旧登记未带摘要）只能按"已完成"处理——这一条在 R9 用例（旧形态 rename 不带 `before_digests`）上验证过，不能因为收紧就把合法续做挡死。

## 4. B2-1 损坏 JSON 泄漏成内部错误（中）

`records.loads()` 只把自身的 `RecordInvalid` 归一，语法损坏的 `json.JSONDecodeError`（`ValueError` 子类）直接穿透三个消费点（PRD 机读块、审查报告、请求信封）→ exit 70。

处置：`loads()` 里 `except ValueError → RecordInvalid`，一处修复覆盖三处消费点；`load_json` 的既有兜底保持不变。

## 5. #3 恢复入口绕过实例一致性（中）

`_resume_task_create` 有绑定时直接用绑定里的 `instance_id`，不比请求携带值——同一请求走普通入口 `WF_BINDING_MISMATCH`、走恢复入口却放行。处置：恢复路径复用 `_require_instance_match(ctx, existing)`，身份核验与普通入口同源。

## 6. #4 bind 的跨记录中断窗口（中）

`cmd_bind` 仍按「取写权 → 写绑定 → 登记 `session.bind` 动作」的顺序，绑定写失败就留下"held + 无绑定 + 无动作"的死局，重试只得 `WF_WRITER_BUSY`。

处置：把绑定与运行态的写入搬进 `_atomic_writer_action` 的 mutate 回调——动作意图先落 writer 主记录，再做跨记录写入；并新增 `_resume_bind()`：本会话有未完成的 `session.bind` 时续做并结案，不报 `WF_WRITER_BUSY`。

## 7. B4-1 d 桶恒为空（按"登记边界"处置）

`classify_candidates` 的 d 桶（归属语义存疑 → `WF_SCOPE_UNRESOLVED`）在布尔归属模型下不可达：未归属且未提交落 c、已归属落 e/f。真实存疑判定需要「同一路径被多处认领 / 归属不可解析」，属第二轮能力。

处置：在实现稿 §2.3.11 登记为**首轮已知边界**并写明方向偏保守（存疑的已提交路径仍落 f 阻断，不会放行）、两个出口首轮不可区分、第二轮实现后删除该条。不假装"已经实现"，也不留一个永远为空的桶在文档里冒充出口。

## 8. 期间新发现（都是我改出来的）

- **N-R86**：`_resume_task_create` 里 `instance_id` 在 else 分支引用了未赋值的局部变量 → 恢复路径 exit 70。改为从 session 取。
- **N-R87**：`_resume_decision_removal` 用了不存在的 `_frontmatter_meta` 包装（parse_frontmatter 本身就是 `(metadata, problems)`），删掉包装。
- **N-R88**：r84 的 disable 用例把 frontmatter 写成 `status: disabled`（不带引号），而项目约定是 JSON 值 → 判据正确、用例错；改为 `"disabled"`。

## 9. 口径

六轮独立复审 + 其他 agent 累计处置 50 条。本轮首次出现"复审判通过的面比缺陷多"，且通过面集中在之前反复出错的四处——可以认为这几处的收敛是真的，但**任务创建/绑定这类跨记录写入**仍是薄弱带（本轮又出了两条），下一轮应继续压这里。
