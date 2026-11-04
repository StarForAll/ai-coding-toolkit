---
name: wf-continue
description: 推进 当前绑定对象（继续/开工/Check/暂停/收工）：批准规划、开工、Check、暂停/恢复、收工、策展、知识处置、复盘、归属裁决、审查记录。
disable-model-invocation: false
---

# wf-continue

已启用会话内的推进入口。先确认本会话已 `wf-start` 启用且绑定一致，再按当前状态路由。
门禁规则在 `.wf/workflows/task-flow.md` 与 `session-flow.md`，本 skill 只做路由。

## 路由

| 当前状态 | 动作 |
|---|---|
| 未开工 / plan，未批准 | 呈现 PRD 机读块、复杂度与 TDD，请人批准 → `task-approve --task <id> --decision <path>` |
| 已批准，未开工 | `task-start --task <id>` |
| in_progress/execute | 在批准触碰面内实施；读规则用 `spec --file <path>`；需要时 `task-curate` |
| in_progress/check | `task-check --task <id> [--decision …] [--review-notes …]` |
| in_progress/finish | 请人核对结果后由人调用 `wf-finish` |
| 需要改方案 | `task-replan` → 重新 `task-approve` → `task-start` |
| 暂停 / 恢复 | `task-pause --task <id> [--reason]` / `task-resume --task <id>` |
| 收工 | `stop --decision <path>`（一个去向：commit/keep/reverse/transfer） |
| 放弃 | `task-abandon --task <id> --decision <path> [--disposition <path>]` |
| `status=archived` 但记录仍在活动区（归档中断：终态已写、目录未移） | **重入 `archive --task <id> --decision <同一决定>` 续做**；该入口会补做目录移动，不另开恢复命令 |
| 归档成功后写权仍 held | `writer release`（对象已终态，`ensure_releasable` 放行）；完成后再结束会话 |

## 复杂任务审查

Check pass 后：`review-launch --task <id> --launch-request <path>` → 人按回显文本在 reviewer CLI 里调用 `wf-review`
→ `review-import`（每个槽位一次） → `review-decide`。

## 不做

- 不调用 `wf-finish`、不归档、不提交（提交只在拿到精确路径授权时由归档动作执行）。
- 不替人回答 `plan-q`、不伪造 review 结论。

## 纪律

- 身份只在请求信封里：不读环境变量、不从命令行或文件猜身份；信封缺失就报 `WF_IDENTITY_UNRESOLVED`。
- 不代人作答、不代跑终端确认与令牌；人的决定只经 `--decision` / `--plan` / `--disposition` 文件承载。
- 入口输出的 `tier` / `code` / `facts` / `next` 是唯一判定源；不自行改写状态或补写门禁结论。
- 命令一律形如 `python3 <项目根>/.wf/bin/wf.py <子命令>`；不装 PATH、不做 shell shim。
