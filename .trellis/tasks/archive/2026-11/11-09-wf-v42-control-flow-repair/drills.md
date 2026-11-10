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

> 更正：v42 全文**没有**提到 `task-rework`（0 次）。我当时以为"v42 §4 要求删除"，属**误判出处**；
> 该命令是 `wf-framework-implementation.md` 的**第二轮交付项**。详见 `rework-conflict.md`。

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


## 第三轮：完整链路（Check pass → 4 轮审查 → 归档守卫）

搭出了能真正跑通的复杂任务：`task-start` 后改一个范围内的文件、`task-check --review-notes` 给内部
审查两轴 → **Check = WF_OK**（`acceptance_results[0].conclusion=passed`，跑的是真验证命令）。

| # | 场景 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| 4 | **审查失败后继续修**：launch 第 1 轮报告不合规（缺四类敏感面 + 无 status=done）→ 拒 → 第 2/3 轮仍有输入问题 → 第 4 轮补齐后通过 | 不被"两轮用尽"驳回，能在新轮次修好后通过 | 第 1–3 轮 `WF_REVIEW_INVALID`/`WF_PATH_INVALID`，第 4 轮 `review-decide = WF_OK` | ✅ **额度已删属实** |
| 4b | 审查输入合规性 | 缺 `excluded-scope` 四类敏感面即拒 | 拒并列出 `missing: [credentials, private-config, outside-project, other-task-dirs]` | ✅ |
| 7 | **标准变更/锚点**：每轮 launch 都核对 `check_anchor` | 锚点不一致即拒 | 4 轮 launch 的 `check_anchor` 恒为同一摘要 | ✅（同锚点） |
| 9 | **vendor 提交守卫**：`archive` 的 commit 面里放 `.wf/lib/wflib/scope.py` | `WF_SCOPE_VIOLATION` + 出口两条 | `WF_SCOPE_VIOLATION`，`vendor_paths=[".wf/lib/wflib/scope.py"]` | ✅ |

### 第三轮发现（已修）：vendor 判定把**项目数据**也当成框架资产

第一次用 `.wf/tasks/**`、`.wf/baseline.md`、`.wf/project-config.json` 做提交面时，归档仍报
`WF_SCOPE_VIOLATION`——因为 `is_vendor` 只看 `.wf/` 前缀，把任务记录/基线/项目配置一起算成 vendor。
后果：**归档提交永远过不去**（记录本身就在 `.wf/tasks/**` 下）。

修法：
- 分类器里**控制记录（b 桶）先于 vendor 判定**（顺序错了会把记录打成 vendor）；
- 新增 `scope.vendor_assets(root, task, paths)`：排除 `.wf/tasks/**`、`.wf/install/**`、
  `.wf/baseline.md`、`.wf/project-config.json`、`.wf/writer.json` 与已识别控制记录；
  `cmd_archive` 改用它。
- 回归断言：`test_vendor_boundary.py` 增 2 条（记录不算 vendor、分类顺序）。

### 仍未演练

`archive` 的**成功**路径（"归档后工作树干净"）与"归档编排失败"故障注入：本轮归档被 vendor 守卫
正确拦下后就收尾了；成功路径需要一份不含 `.wf/**` 的 commit 面（记录由归档自己分三段提交），
可在下一轮补。


## 第四轮：归档三段（故障注入 → 恢复 → 收工）

同一夹具内推进到 `task-check = WF_OK`（真验证命令）、审查 `decide = WF_OK`、`task-knowledge = WF_OK`。

| # | 场景 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| 10 | **归档编排失败**（`.git/index.lock` 占位，让 `git add` 失败） | 失败**带恢复点**，不产生半成功 | `WF_PERSISTENCE_FAILED`（`git add` + stderr 原文）；动作结果里记 `failure`，重入被允许 | ✅ |
| 10b | 恢复后重入 | 清掉故障即可重试，门槛只看未完成的步骤 | 清 lock → 重入 → 只报未完成步骤（`task.review-passed`/`task.knowledge-disposed`） | ✅ |
| 10c | 三段回报（`changes-persisted`） | 三段 receipt 满足 | `task.changes-persisted = satisfied`（业务/记录两段都跑过） | ✅ |
| 1 | **归档成功路径** | `WF_OK` + 工作树干净 | 未达成：最终卡在 `complex 分级须由人在批准决定中确认（decision.plan.complexity）` | ⏭ |

### 第四轮发现（未修，待确认）：`complexity` 决定与归档门禁的口径不一致

批准时我用 `{"choice": "complexity", "value": "complex"}`，`task-approve` **回执 `complexity: "complex"`**（即它认了这个值）；
但归档门禁 `WF_SEMANTIC_DECISION` 仍要求 `decision.plan.complexity` 由人确认，`confirmed_source=inputs`、`human_inputs={}`。

两种可能，需一次定位：
1. 决定文件的形状不对（应写成 `{"choice":"plan","plan":{"complexity":"complex"}}` 之类），批准侧宽松、归档侧严格；
2. `task-approve` 收下了 complexity 却没落进 `decision.plan`，属**记录漏写**（若是这种，就是缺陷）。

**定位结果（不需要夹具，读码即可定性）：是决定形状问题，不是记录漏写。**

- `tasks.py:1625`：`plan_decision = approval.get("plan")` —— 分级只从**批准决定里的 `plan` 对象**读；
- `tasks.py:1643`：`confirmed_source = "decision" if "complexity" in plan_decision else "inputs"`；
- `gates.py:880`：complex 且 `confirmed_source != "decision"` → 阻断。

我写的是独立条目 `{"choice":"complexity","value":"complex"}`，既不在 `plan` 里，也不在 `APPROVE_CHOICES`
里，于是**被静默忽略**；批准时 `complexity` 回执来自"提案值"而非人工确认，归档才炸。

正确形状：`{"choice":"approve", "plan": {"complexity": "complex"}, ...}`。

**顺带修掉的缺陷**：未知 `choice` 原本被静默丢弃（同一类"不许静默通过"）。现在 `task-approve` 遇到
未知 choice 直接 `WF_SEMANTIC_DECISION`，并在 hint 里写明分级该写在哪。回归断言 2 条。

仍未兑现："归档成功路径 / 归档后工作树干净"——需要按正确形状重新批准一次（下一轮第一步），
本条不是代码缺陷。


## 第五轮：归档成功路径（P4 判据兑现）

按正确形状 `{"choice":"approve","plan":{"complexity":"complex"}}` 重新批准，全链路一次跑通：

`enable → task-new → approve(plan.complexity) → start → 改 src/calc.py → check = WF_OK
→ task-knowledge = WF_OK → authorize export = WF_OK → review-launch → 两份报告 import
→ review-decide = WF_OK → archive = WF_OK`

| 判据 | 实测 | 判定 |
|---|---|---|
| 三段回报 | `business`（committed, head=141c52b）/ `record`（committed，含归档后全部记录）/ `runtime`（不入库，S10） | ✅ |
| 归档后工作树干净 | **不干净**：`D .wf/tasks/<旧目录>/{prd,design,implement}.md`、`task.json` 残留未暂存 | ❌ → 已修 |

### 第五轮发现（已修）：记录段没带上"旧位置的删除"

`archive` 的记录段只提交了新路径（`.wf/tasks/archive/...`），没有把旧任务目录的删除加入同一提交，
于是 `git status` 留下 4 条 `D`——"归档后工作树干净"这条判据不成立。

修法：记录段的 `commit_paths` 追加 `old_rel`（旧目录的相对路径），让移动的"删+增"落在同一个提交里。
回归断言 1 条（`ArchiveStagesContractTest`）。

**复测结果（同日补跑）**：`archive = WF_OK`，`git status --porcelain` **为空**（干净）；
日志为 `wf: archive … | feat: 支持负数 | install`，三段回报齐全。→ P4 判据"归档后工作树干净"**兑现**。
