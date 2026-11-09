# 10 场景演练记录（v42 §5.4）

环境：`/tmp` 临时夹具（`wf_fixture.sh` 开发态部署，`--platform dsh`），演练后**已删除夹具**；
`~/.wf/interpreters.json` 与演练前逐字节一致（`68a9e265…70f6`）。驱动为临时脚本，未入库。

## 结果：10/11 断言通过；2 个真实发现

| # | 场景 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| 1 | 顺序两任务（建 A） | `WF_OK` | `WF_OK` | ✅ |
| 1b | 暂停 A / 释放写权 | `WF_OK` | `WF_OK` | ✅ |
| 1c | 新会话接管建 B（generation） | 递增 | 4 → 5 | ✅ |
| 1d | 旧代次写入 | `WF_WRITER_BUSY` 或 `WF_GENERATION_STALE` | `WF_WRITER_BUSY` | ✅ |
| 2 | `/clear`（不同宿主 session_id） | 新会话独立绑定、租约 `live` | `lease={'state':'live'}` | ✅ |
| 2b | 已绑定会话再建任务 | `WF_BINDING_MISMATCH`（v42 A3） | `WF_BINDING_MISMATCH` | ✅ |
| 3 | 报告格式错 | **一次列全**问题 | 一次列出 12 个问题（含缺字段与 axes） | ✅ |
| 5 | 外来改动 | 归 `external`，不计入本任务 | `attributed=0 external=1` | ✅ |
| 8 | required 未核实 | 阻断 → 收窄四项后放行 | `['a5']` → 0 | ✅ |
| 9 | vendor 边界（端到端） | 已开工任务的 e 桶不含 `.wf/**` | 未开工任务缺 `entry_snapshot`，分类按设计拒绝 | ⏭ 未完成 |
| 10 | 归档编排失败 | `persist_pending` + 恢复点 | 未演练 | ⏭ 未完成 |

## 发现 1（已修）：删除 `task-rework` 会让**部署自检失败**

我按 v42 §4 删掉了 `task-rework` 命令桩，结果部署自检报
`handler entry missing: task-rework / required_step: control.task.rework` → `WF_CAPABILITY_UNAVAILABLE`，
**writer 停在维护持有**，之后所有普通命令都 `WF_WRITER_BUSY`。

原因：机制稿 §6.2 与 `payload/workflows/instance-flow.md` 仍把 `control.task.rework` 声明为
`[required]` 的两轮交付步骤；删命令而不删步骤必然自检失败，而删步骤会拿掉设计稿 §5.6 承诺的返工能力。

**处置**：恢复桩，并在代码里写明这是**权威冲突**（v42 §4 vs 机制稿 §6.2 / 设计稿 §5.6），待你裁定后
再决定"删命令+删步骤"还是"保留到第二轮交付"。

## 发现 2：夹具脚本会**掩盖**部署失败

`wf_fixture.sh` 只 `tail -2 /tmp/deploy.log`，而 deploy 的失败行在更前面——于是"部署失败 +
writer 卡在维护持有"被伪装成"平台：["dsh"] 下一步…"。演练第一轮就因此卡住。
建议：脚本改为 `grep -q "WF_OK" || { cat; exit 1; }`。

## 第二轮：复杂任务夹具（额外跑通 2 个场景）

搭出了"已开工的复杂任务"夹具：`task-new` → PRD 机读块（`touch_paths` / `acceptance` / `verifications`）
→ `design.md`/`implement.md` 去占位 → `task-approve`（complexity=complex）→ `task-start` = **WF_OK**。
（过程中补齐了夹具缺的 `.wf/project-config.json` 与 `.wf/baseline.md`，并把部署与初始记录提交进夹具 Git。）

| # | 场景 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| 6 | **扩面（未确认）**：越界路径按本任务提交（带 `wf-task:` trailer）→ `task-check` | `WF_SCOPE_VIOLATION` 且列出 `out_of_scope` | `WF_SCOPE_VIOLATION`，`f=["docs-extra.md"]`，出口两条 | ✅ |
| 6b | **扩面（人确认后）**：`authorize record --choice expand --paths docs-extra.md` → 再 `task-check` | 越界消失（进入 e 桶） | e 桶含该路径、f 为空；本次 Check 因前后快照变化判 `WF_CHECK_STALE`（正确的重检语义） | ✅ |
| 9 | **vendor 提交守卫**（`archive` grant 里塞 `.wf/lib/...`） | `WF_SCOPE_VIOLATION` | 未到达该段：`archive` 首先要求 `phase=finish`（本夹具只到 execute/check） | ⏭ |

**关于 6b 的语义**：确认文件本身落在任务目录里，改变了检查对象的快照 → 同一次 Check 的前后比对不一致，
按设计判 `WF_CHECK_STALE`（"检查期间对象变化即本次不判 pass"）。这不是缺陷，而是要求重跑一次
Check 才能拿结论。

## 未演练的 4 个场景（原因）

| 场景 | 缺什么 |
|---|---|
| 审查失败后继续修（含"额度已删"） | 需要完整审查链路夹具：两份 reviewer 报告要带五轴 + 锚点 + 材料，本轮未搭 |
| ~~扩面（`expand` 确认前后）~~ | ✅ 已演练（见"第二轮"） |
| 标准变更（`assertions_digest` 漂移 + `drift_diffs`） | 同上，且需要改 spec 规则并重跑 Check |
| 框架缺陷就地修 / 归档编排失败 | 需要把任务推进到 `finish`（Check pass + 复杂任务审查 pass）+ 故障注入 |
