---
name: wf-continue
description: 推进 当前绑定对象（继续/开工/Check/暂停/收工）：批准规划、开工、Check、暂停/恢复、收工、策展、知识处置、复盘、归属裁决、审查记录。
disable-model-invocation: false
---

# wf-continue

> **判断指引**：需要写 judgment 或被人挑战依据时读 `wf-judging`（十条：交付面/关闭/影响面/扩面/标准变更/规模/报告有效性/标准缺失/未核实/冲突）。

已启用会话内的推进入口。先确认本会话已 `wf-start` 启用且绑定一致，再按当前状态路由。
门禁规则在 `.wf/workflows/task-flow.md` 与 `session-flow.md`，本 skill 只做路由。

## 路由

| 当前状态 | 动作 |
|---|---|
| 未开工 / plan，未批准 | 呈现 PRD 机读块、复杂度与 TDD，请人批准 → `task-approve --task <id> --decision <path>` |
| 已批准，未开工 | `task-start --task <id>` |
| in_progress/execute | 在批准触碰面内实施；读规则用 `spec --file <path>`；需要时 `task-curate` |
| in_progress/check | `task-check --task <id> [--decision …] [--review-notes …]` |
| in_progress/finish | **先读修复态**（见下节），再请人核对结果后由人调用 `wf-finish` |
| 人**明确要求**改方案 | 先取人签的 `choice=replan` 决定文件 → `task-replan --decision <文件>` → 重新 `task-approve` → `task-start`（缺决定即 `WF_SEMANTIC_DECISION`） |
| 暂停 / 恢复 | `task-pause --task <id> [--reason]` / `task-resume --task <id>` |
| 收工 | `stop --decision <path>`（一个去向：commit/keep/reverse/transfer） |
| 放弃 | `task-abandon --task <id> --decision <path> [--disposition <path>]` |
| `status=archived` 但记录仍在活动区（归档中断：终态已写、目录未移） | **重入 `archive --task <id> --decision <同一决定>` 续做**；该入口会补做目录移动，不另开恢复命令 |
| 归档成功后写权仍 held | `writer release`（对象已终态，`ensure_releasable` 放行）；完成后再结束会话 |

## 修复态先读什么（⑥）

进入 finish、或收到 `fail` / `unavailable` / 报告损坏 / 换实施宿主的信号时，先读事实再动作：

```bash
<python> <项目根>/.wf/bin/wf.py status --short --json    # 四条件 + exits + 确定阻断
<python> <项目根>/.wf/bin/wf.py gate --due before_archive --json   # 步骤面缺口
```

- `repair_scope` 的四组事实与 `exits` 怎么读：见 `wf-repair-loop`。
- **不要用 `archive` 试归档探路**：归档会先做业务提交（现在有提交前只读预检，但它通过不代表
  可以归档——步骤面、escalated、required、依赖、debug 各有自己的门禁）。
- 要人裁放行不可核实证据时，用 `wf-review-accept-unknown`（先按 `wf-review-accept-unknown`
  skill 呈现事实与采集 quote）。

## 复杂任务审查

Check pass 后：`review-launch --task <id> --launch-request <path>` → 人按回显文本在 reviewer CLI 里调用 `wf-review`
→ `review-import`（每个槽位一次） → `review-decide`。


## 证据文件纪律（2026-11-07 起）

真实 dogfood 发现：把"入口该生成的结构"写成文件，会让任务目录膨胀、并迫使模型读源码猜字段。因此：

- **可以人/模型写的只有四类**：决定文件（批准/收工/知识处置的选择）、`--review-notes`（双轴结论）、`--changes`（spec 变更）、基线提案（**推荐** `baseline-apply --files a,b,c --decision <批准文件>`，由入口生成提案）。
- **不要自建**：验证结果（`task-check` 会记）、门禁预览（`gate --due before_archive`）、提交清单与摘要（`archive` 记录）、`plan-approval`/`finish-commit-manifest` 之类"自述性"文件。
- 需要知道某命令的输入结构：`<python> <项目根>/.wf/bin/wf.py help <命令>`（有最小示例，不必读源码）。

## 不做

- 不调用 `wf-finish`、不归档、不提交（提交只在拿到精确路径授权时由归档动作执行）。
- 不替人回答 `plan-q`、不伪造 review 结论。

## 工作习惯（2026-11-08 起）

- **同一终端同时只推进一个任务**；并行请另开终端/窗口。
  同一终端里的第二个 agent 会被 `WF_IDENTITY_UNRESOLVED(concurrent_unregistered_caller)` 阻断，
  须人显式 `wf.py enable` 登记后才放行，且此后与前者共享同一执行会话。
- **自动模式下不需要手写信封**：直接跑 `wf.py <子命令>`；身份由执行边界派生。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令形如 `<python> <项目根>/.wf/bin/wf.py <子命令>`。`<python>` 按此顺序取，**取到能跑的就整会话固定复用**：
  ① `.wf/project-config.json` 的 `python_executable`（未设置再读 `~/.wf/config.json` 同名键，可直接读文件取值，不必先执行）；
  ② 你自身运行时的 Python 可执行文件；
  ③ 系统 `python3`。
  若宿主执行策略要求审批或不在白名单（`WF_EXECUTOR_UNCONFIRMED` / 审批拒绝），改用策略允许的已核实 Python 绝对路径并固定下来；
  **不要每条命令换解释器**，也不要因为被拒就改成手写信封或换路径重试同一效果。不装 PATH、不做 shell shim。
