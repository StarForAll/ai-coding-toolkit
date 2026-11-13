# wf 控制流：两份分析报告核验与结构性修正

## Goal

对两个 agent 就 `docs/workflows/wf/` 控制流提出的 18 条主张逐条核验（以代码与 dogfood 会话事实为准，不采信报告结论本身），
对**成立的缺陷**按机制层面修正（不是逐处打补丁），对**不成立或属已声明边界**的主张给出带证据的拒绝理由，
并让修正后的 wf 在同类 dogfood 场景下不再静默失效、不再留下悬空引用。

## 背景事实（已核验）

- 上次 dogfood（`~/projects/personal/traffic_monitor`，会话 1–4）确实出现了：禁写 `.wf/` 时 `wf-start` 整体被旁路、
  外来未提交改动（`.unipi/`、`.gitignore`）两次逼停 Check、审查报告格式错误导致多轮返工、材料看不到已提交改动。
- 基线：`scripts/tests` 622 用例全绿；`docs/workflows/wf-release/` 由源树生成，当前对应已打 tag 的 `wf-v0.1.0`（tag 存在）。

## Requirements

逐条裁定（"采纳"= 本任务修；"拒绝"= 不改，只登记理由）：

| # | 报告主张 | 裁定 | 证据 / 落点 |
|---|---|---|---|
| A1 | `wf-review-action` 只登记建议、不承接修复与收敛 | 采纳（skill 口径） | skill 首行写"不改源码"且无 fail 后收敛路径；设计稿 §6.5 要求"就修→重跑 Check→下一轮"，skill 未承接 |
| A2 | `run advance` 整份写侧车抹掉 `writer_generation` | 采纳（代码） | `runs.py:1674`、`runs.py:1205`、`tasks.py:1490`、`cli.py:1216/1349` 用整份替换；`session.update_runtime` 的合并语义被绕过 |
| A3 | `uncovered` 可被机械推导成 pass；缺口处置引用 §4.8/4.9 不存在 | 采纳（代码+文档） | `derive_verdict` 只产 gaps；`review-decide` 直接置 `verdict="pass"`；机制稿无 §4.8/§4.9 |
| A4 / B1 | 外来未提交改动无条件阻断、无出口 | 部分采纳 | 阻断方向符合设计稿 §4.2（"先报告并交人处理"），但**只有提交类外部变更**有"已核对无影响"出口，未提交类没有；补一条摘要绑定的排除留痕出口 |
| A5 | 同进程新会话无顺序任务出口 | 拒绝（已声明边界） | 设计稿 §1.3 明文声明该限制、§8.3 已有候选行；不属缺陷，不删边界 |
| A6 | 外发/仓库规则授权只核类别、不核本次范围 | 采纳（代码） | `launch` 只 `authorize.require(...,"export")`；`archive` 的 `repo_rules` 只 `require`，而同处 `delete` 已用 `covers(paths)` |
| A7 | 脱敏黑名单，`quote`/嵌套字典敏感值可入库 | 采纳（代码） | `redact()` 按顶层键黑名单；协议 `redaction.json` 声明的是"保留项"口径（allowlist） |
| A8 | lint 与导入/判定两套校验，空 read-scope 等 lint 放行 | 采纳（代码） | `lint_report` 只核字段存在；`review_report_problems` 才核非空与 `exclusion_gaps` |
| A9 / B6 | 材料漏掉本任务已提交改动 | 采纳（代码） | `materialize_delivery` 对已跟踪路径只比 `HEAD`，任务中途提交后材料退化为"no textual change (metadata-only?)" |
| B2 | 禁写 `.wf/` 与 `enable` 硬前置冲突时无降级路径 | 部分采纳（skill 口径） | 会话 2 实录：用户禁改 `.wf/`，agent 自行跳过流程直接写码。**不采纳**"先写码后补流程"（与设计稿 §4.2 冲突）；改为"启用无法建立时显式报告 + 由人决定是否按普通开发继续" |
| B3 | `review-launch` 请求仍由模型手写 JSON | 采纳（代码） | 三类材料本可由入口从交付面/PRD/Check 记录机械生成；目前 `submitted_scope` 全手写 |
| B4 | `workflow_snapshot_digest=None` 且就地改 `.wf/lib` 会被重装覆盖 | 部分采纳 | "重装覆盖"**不成立**：`install.py` 与 `wf-dev-deploy.py` 对内容不同的既有文件都返回 `WF_ASSET_DECISION` 整批不写；成立的是锚点缺实例定义快照摘要 |
| B5 | 验证日志只持久化最后一行 summary | 采纳（代码） | `_run_argv` 只把 summary 写进 log |
| B7 | 报告修订无独立通道 | 拒绝（已声明边界） | 机制稿 §9.2 明确"旧轮次路径永不覆写"，属声明边界；骨架 + lint 前置已把格式类返工前移 |
| B8 | `docs/workflows/wf-variant.md` 标题仍是旧名 | 采纳（文档，标注历史） | 该文件属设计稿 §0/charter 明确排除的旧版文档族；改成历史标注，不改写其正文语义 |
| B9 | PRD 版本不符整体回 Plan，无格式豁免 | 拒绝主张，采纳可用性修正 | `task-approve` 的 `mechanical-revision` 通道就是该豁免；缺的是 `task-start` 报错不给这条路 |

## Constraints

- 不改 charter、不新增或放宽 charter 边界；设计稿只允许"澄清既有条款 + 补场景行"，不新增"唯一定义"条目。
- 新增判定字段/动作域必须按设计稿第 0 章登记：定义、写者、消费点、失败出口、正反例，并同步机制稿与索引。
- 修正不得引入新的事实源：排除/缺口/授权范围都必须绑定可核对摘要，内容变化即失效。
- 不改 `~/projects/personal/traffic_monitor`（目标项目）；只改本仓库 authoring 源树与其生成物。
- 代码只改 `docs/workflows/wf/payload/`，测试只加到 `scripts/tests/`；不新增运行时依赖。

## Acceptance Criteria

- [x] A2：所有侧车写入走合并语义；`run advance`/`bind`/`task.create` 后 `writer_generation` 仍在，缺代次时才报 `WF_GENERATION_STALE`。
- [x] A3：五轴全 `uncovered` 不产生 verdict（`WF_REVIEW_INVALID`）；部分 `uncovered` 且无人接受缺口时输出需人裁决档，接受后 verdict 只按已覆盖轴推导，缺口入 `facts`。
- [x] A4/B1：外来未提交路径可按"路径 + 当前内容摘要 + 来源"记录排除；摘要变化即失效；排除不进入交付、不构成提交授权。
- [x] A6：外发授权缺失或与本次材料类/目的地不符时 `launch` 拒绝；仓库规则提交按实际路径核对授权覆盖。
- [x] A7：`quote`、嵌套字典、未知字段中的敏感值不进 committed 副本；保留项与 `protocol/redaction.json` 一致。
- [x] A8：同一份报告在 lint 与导入/判定处的输入结论一致（空 read-scope、缺敏感面、状态头位置）。
- [x] A9/B6：任务中途提交后，材料包含该提交相对任务基线的差异；删除路径给出删除 hunk，不再出现"metadata-only"误导措辞。
- [x] B3：`review-launch` 可只给 `--implementation-cli` + 外发确认引用，材料三类由入口生成；缺项报明确原因。
- [x] B5：验证日志保留完整遮罩输出（含可见截断标记与丢弃字节数），记录内仍只存摘要。
- [x] B4：属于实例的任务，其 Check 锚点包含实例定义快照摘要；快照变化使旧锚点失效。
- [x] B2/A1/B9：三处 skill/UI 口径修正落地（启用受阻显式出口、审查 fail 后收敛路径、版本失配给机械修订出口）。
- [x] 文档：机制稿新增/修订段落与代码一致；设计稿只做澄清与场景行；`scripts/validate-wf-design.py` 通过；机制稿 §0.1 的输入摘要同步。
- [x] 测试：新增用例覆盖上述每项的正反例；`python3 -m unittest discover -s scripts/tests -t .` 全绿。
- [x] 发行树：`scripts/build-wf-release.py --verify` 通过（必要时重建为 `0.1.1`，tag 由人创建）。

## Notes

- 拒绝项（A5、B7、B4 的"覆盖"部分、B9 的"无豁免"部分）在机制稿/任务记录中留结论与证据，不进入实现。
- 排期：先代码与测试（A2/A3/A4/A6/A7/A8/A9/B3/B4/B5/B9），再 skill（A1/B2），最后文档与发行树重建。
