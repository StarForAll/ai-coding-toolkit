# dogfood（真实使用观察）建议步骤

实跑放在门禁①成立后的最后一个批次，本轮（第 28 轮末）不执行（2026-11-06 人裁，见 `pending-decisions.md` §6）。

> 位置说明：R1-14 的裁决是"**在全部修正落地后**，按最新内容给出可执行的建议步骤，交人执行"。本文件就是该交付物，不包含已执行的动作。
> 判据来源：设计稿 §8.2（分轮验收 + 真实使用观察）、charter T5（成本不构成新增/删减承诺的理由）、T6.5（停止条件）。

## 0. 硬门禁（2026-11-05 人裁，先读这段）

**人工没有完成 dogfood，就不能进入第二轮实现。** 这条门禁写进设计稿 §8.2「轮次串行门禁」与实现稿 §6.1，不是本文件的建议：

- 第一轮「完成」= ①三夹具与五条最小验证有实跑记录（依赖后续轮次才能覆盖的场景行按设计稿 §8.1 排除并登记为「等该轮交付」）；②复杂任务审查链路可用，或已按设计稿 §6.5 留痕「不可用」并按其出口处置；③**真实项目 dogfood 至少完成轻量任务闭环与一次中断恢复**，并留有观察记录。
- 三项缺任一项时，第二轮的任何实现动作（代码、脚本、清单、测试）不得开始，只允许文档、设计与计划活动。
- 不得以「先搭骨架」「并行推进」「另立任务」绕开；不得把「人还没安排 dogfood」当作降级或豁免理由。
- 判定与留痕由人执行；脚本只核记录存在，不核语义。

若第 3 轮（复杂任务 dogfood）因缺少第二个异种 CLI 无法执行，按设计稿 §6.5 的不可用处置留痕即可，**不作**进入第二轮的额外门槛；但第 1、3 节里的轻量闭环与中断恢复两轮是硬前置。

## 1. 为什么必须在真实项目里跑一次

现有证据全部是夹具级：F0/F1/F2 由脚本构造、断言可复现，但**四类事实只有真实使用才能观察**：

| 事实 | 夹具为什么测不到 |
|---|---|
| 宿主会话身份在真实压缩后仍可恢复 | 压缩不可按需触发；夹具只能模拟"同标识重入" |
| 人判环节的真实成本（批准、`plan-q` 作答、审查发起） | 夹具里的人答是脚本写死的 Decision |
| 审查 CLI 的实际可用率与等待时长 | 夹具只覆盖"能起/起不来"两态，测不到等待与重试成本 |
| 换对象/换会话的摩擦 | 夹具不模拟人连续做多个短任务的心理与时间成本 |

## 2. 前置条件（缺一不开始）

1. 门禁①成立（§96 首轮适用行的适用项达到各自预期）即可开始，不要求收口全绿。
2. 选定一个**真实小项目**（几十到几百行、有真实测试命令、最好有自己的 README）。不要用工作流本身的仓库当 dogfood 对象，避免自指。
3. 按发行方式安装：从打包发行树 `install.py --release-ref refs/tags/wf-vX.Y.Z` 投放（不要用 `wf-dev-deploy.py`，否则测不到发行入口）。
4. 预备 CLI：1 个实施 CLI；若要做复杂任务，另备 **2 个与实施 CLI 不同、彼此也不同**的审查 CLI（设计稿 §6.5）。
5. 建一个记录文件（建议 `.trellis/tasks/<task>/dogfood-log.md`，只记事实，不写结论）。

## 3. 建议执行顺序（三轮，可停在任何一轮）

### 第 1 轮：轻量任务闭环（半天内，必须先做）

- **对象**：一个真实小改动，例如"给现有函数补一个边界用例并修一个已发现的小缺陷"。
- **步骤**：`/wf-start` → `task-new --kind ordinary` → 起草 PRD（`touch_paths` 写实际路径）→ `task-approve`（复杂度应为 light）→ `task-start` → 实施 → `task-check` → 知识处置（允许"无更新"）→ `wf-finish` → `archive`。
- **要观察并计数**：
  - 人被判了几次（批准 1 次 + finish 1 次，超出即记录原因）
  - 每条命令的实际次数与耗时（尤其 `task-check`）
  - 是否出现"为了推进而临时绕过门禁"的冲动，以及触发它的具体输出
- **通过判据**：全程无阻断，或每次阻断都有明确原因码且人知道下一步做什么。

### 第 2 轮：复杂任务 + 双 reviewer 审查（验证审查契约）

- **对象**：触碰治理面或改变对外契约的改动（例如给一个既有脚本加参数并改它的输出契约）。
- **步骤**：同第 1 轮，但 `complex` 分级 → Check pass 后 `review-launch` → 人打开两个异种 CLI 会话各跑 `/wf-review`（拿 `--request`）→ 回主会话 `review-import` → `review-decide` → `finish`。
- **要观察并计数**：
  - 两个 reviewer CLI 的实际可用性（起了几次、失败原因、等待多久）
  - 报告是否真的覆盖五个轴；有没有"空转的 pass"
  - 驳回的 finding 能否本地核实（这是审查质量的核心）
  - 锚点失配是否被真实触发过一次（故意改一个交付文件再重导旧报告）
- **通过判据**：两异种报告 + 锚点核对 + 判定三者都成立；不可用时按设计稿 §6.5 暂停或异常归档，不降级完成。

### 第 3 轮：中断与恢复（最有价值的一轮）

- **对象**：第 1/2 轮任务做到一半时，**故意**制造三种中断：
  1. 未收工直接关闭会话（写权仍被持有）；
  2. 暂停后保留 WIP 并释放写权，换新会话恢复；
  3. 归档提交后立刻 kill 进程（本项已有夹具覆盖，真实环境再确认一次更稳）。
- **要观察**：新会话能否只凭项目记录接续（不要求人重述）；`repair.py` 的预览是否说清了旧写者状态；WIP 同对象恢复是否要求重批。
- **通过判据**：不丢任务、不重复动作、不误判空闲；每次恢复都有可核对的记录锚点。

## 4. 记录表（照抄进 dogfood-log.md）

| 项 | 口径 | 本轮值 |
|---|---|---|
| 对象类型 | 轻量 / 复杂 | |
| 人判次数 | 计数 + 每次原因 | |
| 命令调用次数 / 总耗时 | 按子命令分列 | |
| 阻断次数 | 原因码 + 人是否知道出口 | |
| 跨会话次数（换对象） | 新会话 → `wf-start` → 选对象 → 重载上下文 | |
| 审查 CLI 可用率 | 成功/尝试 + 等待时长 | |
| 身份不可用次数 | 原因 + 时长 | |
| 宿主身份稳定性 | 新会话是否丢失绑定；`provider=wf` 签发路径未交付（第二轮）时该宿主是否直接卡死 | |
| 未收工关闭/恢复次数 | 人核对动作数 + 耗时 | |
| 主观摩擦点 | 一句话 + 触发它的具体输出 | |

## 5. "缺漏不足"怎么验证（不是看绿灯）

按下列顺序判定，每一步都要指向**具体对象**，不能凭整体感觉：

1. **门禁是否真的会拒绝**：每轮至少人为构造一条应拒绝事实（越界路径、缺批准、旧锚点报告），看是否得到预期原因码。只有"该拒的被拒"才算门禁有效。
2. **记录是否足够自恢复**：新会话不提供任何口头背景，看能否复述目标/批准范围/位置/下一步。说不出来就是记录缺口。
3. **人判是否可追溯**：任取一个 Decision，能否从记录反查到它对应哪个问题、哪版规划。反查不到就是人判留痕缺口。
4. **降级是否可见**：刻意制造一次不可用（把某个 review CLI 的凭据临时去掉），看是否输出"不可用 + 影响 + 出口"，而不是静默继续。
5. **成本是否可接受**：用 §4 的计数对照设计稿 §8.2 的观察项；若某项成本高到人会放弃使用，按 charter T5 记"场景无法长期维持"的证据，**不得据此删承诺**（T4 仍成立）。
6. **不许用夹具结论替代**：夹具绿灯只能说明"结构对"，不能说明"人愿意用"；反过来，主观觉得麻烦也不能推翻已承诺的门禁。

## 6. 停止条件

- 轻量轮跑通 + 复杂轮跑通 + 一次恢复成立 → 可认为首轮达到"最小可运行候选"，按设计稿 §8.2 进入第二轮（定义与实例编排）验收。
- 任一轮出现**阻断且人不知出口**、或**记录不足以自恢复**、或**门禁该拒未拒** → 停止 dogfood，回到缺陷登记，不在真实项目里继续试。
- 不因为 dogfood 结果顺手扩范围（charter T6.5）；观察结论只用于候选重议与缺口判断。

## 7. 本轮明确不做

- 不把 dogfood 结论写成"框架生产可用"（设计稿 §8.2：未完成全部验收前只能称设计/实现候选）。
- 不采集跨项目私有日志；只记本次任务的记录与本地观察。
- 不在 dogfood 中改框架代码；发现缺陷先登记，另行授权修复。

---

## 8. 可执行步骤（2026-11-07 当前版本，与本轮交付对齐）

> 与上面 §3 的差别：这一节写**当前实际能跑的命令形态**。本轮新增/变更的四处必须体现在 dogfood 里，否则测的就不是当前版本：
> ① 复杂度 ②③④ 已改为事实核对，复杂任务的**分级必须由人在决定文件里确认**（`decision.plan.complexity`）；
> ② 新增只读子命令 `ready`（无绑定新会话的就绪建议）；
> ③ 审查报告 `excluded-scope` 必须覆盖四类敏感面（凭据/私密配置/项目外/其他任务目录），否则 `review-decide` 直接拒；
> ④ 发行安装按 **tag 提交树**核内容（工作树脏不影响，但源必须是带 tag 的仓库根）。

### 8.1 选对象（缺一不开始）

| 条件 | 检查方式 |
|---|---|
| 几十到几百行、有真实测试命令 | `ls`、`cat README.md`、跑一次它自己的测试命令 |
| **不是**本仓库（避免自指） | `pwd` 对比 |
| 有 Git 且至少一个提交 | `git log --oneline -1`（无 HEAD 时 `task-start` 会 `WF_CAPABILITY_UNAVAILABLE`） |
| 工作区相对干净 | `git status --porcelain` |

准备一个记录文件（只记事实）：`dogfood-log.md`，表格照抄 §4。

### 8.2 安装（发行入口，必须人执行）

```bash
# 0) 造一份带 tag 的发行源（若已有打包好的发行树与 tag，跳到 1）
python3 scripts/build-wf-release.py --version 0.1.0
# 在发行源目录里：git init && git add -A && git commit -m release && git tag wf-v0.1.0

# 1) 安装（target 必须是**已存在**的绝对目录）
python3 <release-src>/install.py --target /abs/path/to/project \
  --release-ref refs/tags/wf-v0.1.0 --source <release-src> --platform dsh --confirm

# 2) 确认执行器（**必须 TTY**；非 TTY 会返回 WF_SEMANTIC_DECISION）
python3 /abs/path/to/project/.wf/bin/wf.py confirm-executor --scope system
```

预期：安装输出"投放 N 个文件 / 清单摘要 / 规则摘要 / 托管段 appended"；若报 `WF_RELEASE_CONFLICT`，说明 tag 提交树与清单不符——**先修发行，不要绕过**。

### 8.3 会话信封（所有业务命令都要带）

```bash
# 每个命令都从 stdin 收同构信封；sid 是本次会话标识
payload='{"session":{"provider":"host","identity":{"host_id":"dsh","session_id":"dogfood-1"},
  "instance_id":null,"activation":{"enabled":true,"start_source":"human:dogfood",
  "enabled_at":"2026-11-07T00:00:00.000000Z"}},"inputs":{}}'
echo "$payload" | python3 .wf/bin/wf.py enable --json
echo "$payload" | python3 .wf/bin/wf.py ready --json      # 列出候选与 suggested
```

### 8.4 第 1 轮：轻量闭环（半天内）

```bash
W="python3 .wf/bin/wf.py"
# 1) 建任务（kind=ordinary），拿到 task_id 与目录
echo "$payload" | $W task-new --kind ordinary --title "补边界用例并修小缺陷" --template .wf/templates/task --json
# 2) 起草 PRD：填 wf-plan:v1 机读块（touch_paths=真实路径；acceptance；verifications 里的命令必须真能跑）
# 3) 批准（轻量：决定文件不需要 plan 块；若被判复杂，必须走 8.5）
cat > approve.json <<'J'
[{"source":"human:dogfood","at":"2026-11-07T00:00:00.000000Z","subject":"approve <task-id>",
  "object_digest":"sha256:<prd 摘要>","choice":"approve","reason":"范围清楚"}]
J
echo "$payload" | $W task-approve --task <id> --decision approve.json --json
# 4) 开工 → 实施 → 检查（--review-notes 给双轴结论）
echo "$payload" | $W task-start --task <id> --json
echo "$payload" | $W task-check --task <id> --review-notes notes.json --json
# 5) 知识处置（允许"无更新"）→ 收工 → 归档
echo "$payload" | $W task-knowledge --task <id> --decision knowledge.json --json
echo "$payload" | $W stop --decision stop.json --preview --json   # 先看逐路径归属（只读）
echo "$payload" | $W stop --decision stop.json --json
echo "$payload" | $W archive --task <id> --decision finish.json --json
```

**要记的数**：人被判了几次（批准 + finish 各 1 次为基线）、每条命令耗时（尤其 `task-check`）、阻断次数与原因码、有无"想绕过门禁"的冲动及触发它的输出。

### 8.5 第 2 轮：复杂任务 + 双 reviewer

```bash
# 批准必须人在决定文件里确认分级（新要求）
cat > approve-complex.json <<'J'
[{"source":"human:dogfood","at":"2026-11-07T00:00:00.000000Z","subject":"approve <id>",
  "object_digest":"sha256:<prd>","choice":"approve","reason":"改对外输出契约",
  "plan":{"complexity":"complex","tdd":false}}]
J
echo "$payload" | $W task-approve --task <id> --decision approve-complex.json --json
# Check pass 后发起审查（请求里给实施 CLI + 两个**异种且彼此不同**的审查 CLI）
echo "$payload" | $W review-launch --task <id> --launch-request launch.json --json
# 人在两个审查 CLI 会话里各跑一轮，把报告放回 launch 给出的暂存目录
echo "$payload" | $W review-import --task <id> --round 1 --slot s1 --report /abs/report.md --json
echo "$payload" | $W review-decide --task <id> --round 1 --json
```

**报告必填**（当前版本）：`protocol=wf-review-v1`、`task-id`、`round`、`reviewer-id`、`source-cli`、`review-time`、`review-focus`、`check-anchor`（取 launch 回显）、`read-scope`、**`excluded-scope` 必须覆盖四类敏感面**、`scope-exceptions: []`、五轴 `axes`、`findings`、`verdict`。
**故意做一次反例**：改一个交付文件后再导入旧报告 → 必须报锚点失配（`WF_REVIEW_INVALID`）。

### 8.6 第 3 轮：中断与恢复（三种）

| 中断 | 怎么造 | 看什么 |
|---|---|---|
| 未收工关会话 | 开工后直接关终端（写权仍 held） | 新会话 `status`/`ready` 是否报"写权被他人持有"；`python3 .wf/bin/repair.py --project <abs>` 预览是否说清旧写者 |
| 暂停 + 保留 WIP 换会话 | `task-pause` → `writer release` → 新会话 `ready` → `bind` → 恢复 | 是否要求重批；WIP 是否按同对象例外恢复 |
| 归档后立刻 kill | 归档命令执行后立即终止进程 | 重入是否幂等、不重复提交 |

### 8.7 证据清单（跑完必须留）

1. `dogfood-log.md` 填好的 §4 表格；
2. 每轮的首末 `status --json` 输出（时间戳可核）；
3. 每次阻断的完整原因码与出口文本；
4. 决定文件原文（批准 / finish / 知识处置）——用于反查"人判可追溯"；
5. 复杂轮两份审查报告原文 + `review-decide` 输出；
6. 恢复轮的 `repair.py` 预览输出。

### 8.8 656「闭环四条件」判定表（跑完逐项打勾）

| 条件 | 判据 | 证据 |
|---|---|---|
| 正常执行 | 轻量轮全程无阻断，或每次阻断都有原因码 + 出口 | §8.7-2/3 |
| 异常退出 | 至少一次真实异常（中断/拒绝）有可见输出与恢复路径 | §8.7-3/6 |
| 恢复 | 三种中断至少各成功一次 | §8.7-6 |
| 知识回流 | `task-knowledge` 有结论（含"无更新"），且能反查 | §8.7-4 |

### 8.9 已知坑（本轮实测过的）

| 坑 | 现象 | 处置 |
|---|---|---|
| `confirm-executor` 非 TTY | `WF_SEMANTIC_DECISION` | 必须人在终端跑 |
| 决定文件缺 `plan.complexity` 而任务是复杂 | 补三件套后仍被拒（`WF_SEMANTIC_DECISION`） | 人在决定里写 `plan.complexity` |
| 报告 `excluded-scope` 只写 `node_modules/**` | `review-decide` 报 "does not cover sensitive surfaces" | 补凭据/私密配置/项目外/任务目录四类 |
| `target` 目录不存在 | `WF_PATH_INVALID` | 先建目录 |
| 源不是带 tag 的仓库根 | `WF_RELEASE_CONFLICT` | 用 `build-wf-release.py` 造的发行仓库 |
| 开工前工作区有他人改动 | `WF_WORKSPACE_UNRESOLVED` | 先处置或提交，不要 stash 后不管 |

### 8.10 停止条件（沿用 §6）

任一轮出现「阻断且人不知出口」/「记录不足以自恢复」/「门禁该拒未拒」→ 停止 dogfood，登记缺陷，**不在真实项目里继续试**，也不顺手扩范围。

---

## 9. 首次 dogfood 尝试记录（2026-11-07，traffic_monitor）

**触发**：人在 `traffic_monitor` 新开 agent 会话，输入 `/wf-start`。安装已完成（`git status` 显示 `?? .agents/`、`?? .wf/`，未提交）。

**agent 实际做了什么**：读 `wf-start` 技能 → `cat AGENTS.md`（无输出）→ `git status --short` → 尝试 `python3 .wf/bin/wf.py enable` → **被宿主拒绝**（"操作需要审批，但当前审批策略为 Never"）→ 明确停止并声明不绕过限制。

**观察到的三条事实**

| # | 事实 | 性质 |
|---|---|---|
| **F1** | 宿主执行授权为 Never，agent 无法运行任何 `wf.py` 命令 | **环境**（非产品缺陷）；agent 的"停止且不绕过"是**期望行为**，记正面观察 |
| **F2** | `wf-start` 只写「跑 `wf.py enable`」，**没给信封的构造与传法**；直接敲会得 `WF_PATH_INVALID: request envelope must be piped on stdin` | **产品缺陷（skill 指导缺口）**：真实可行性验证的第一处失败点 |
| **F3** | `AGENTS.md` 不存在，安装器未生成路由块（只在文件存在时核对）；本次靠人显式 `/wf-start` 才发现技能 | **待判**：是否应生成 AGENTS 路由块（影响"模型是否知道 wf 存在"） |

**处置**

- F1：由人放开该项目的命令执行授权（或 allowlist `python3 .wf/bin/wf.py`），再重跑 `/wf-start`；
- F2：**先登记不改**（dogfood 期间不改框架代码）；修法是给 `wf-start` 补最小信封示例与 `--envelope <file>` 写法，并把"宿主拒绝执行"列为可识别前置；
- F3：登记候选，等 dogfood 结论再决定是否补生成逻辑。

**补一条被这次暴露出来的 runbook 缺口**：安装后应把 `.wf/`、`.agents/` 与 `.gitignore` 托管段**提交成一个基线提交**，否则 `task-start` 会因"他人未提交改动"报 `WF_WORKSPACE_UNRESOLVED`（夹具里踩过同样的问题）。

### 9.1 F1 根因定位（2026-11-07 追加）

- 框架侧**已确认正常**：`enable --envelope /tmp/wf-env.json` 返回 `WF_OK`，`activation` 已形成，`platforms=["codex","dsh"]`。
- 宿主侧根因：该 Codex 会话以 **`-a never`（从不询问审批）** 启动，且沙箱为只读；因此 `git status`（只读）能跑，而 `python3 .wf/bin/wf.py enable`（要写 `.wf/`）直接拒绝，连审批机会都没有。
- `~/.codex/config.toml` 里该项目已是 `trust_level = "trusted"`，**所以不是信任问题**。
- 修法（宿主启动参数，非框架）：`codex -a on-request -s workspace-write -C <项目>`；或 `--approve-for-me`；`--dangerously-bypass-approvals-and-sandbox` 不推荐（等于放弃观察"人审批成本"这一项 dogfood 指标）。

### 9.2 第二次尝试（2026-11-07，Codex + `-a on-request -s workspace-write`）

| 项 | 结果 |
|---|---|
| **F1 关闭** | 重开宿主后，agent 在会话内成功执行 `wf.py enable --envelope …` → `WF_OK` |
| **F2 复现（且被人工指令绕过）** | agent 是在人额外贴了「每次调用都带 `--envelope /tmp/wf-env.json`」之后才走通的；**仅凭技能文本它没有完成第一步**。F2 应视为确证缺口，非偶发 |
| **新发现 F4（轻）** | `wf-start` 第 6 步写「`generation` → 信封 `inputs.generation`」，但没说 `enable` **不返回** generation、它只在 `task-new`/`bind` 后出现；agent 如实报「本次响应没有 generation，因此不补造该值」——行为正确，但暴露技能表述不够精确 |
| **正面观察 1** | agent 在多目录搜 `AGENTS.md`，`traffic_monitor` 下确实没有 → F3（无路由块）再次确认 |
| **正面观察 2** | 不伪造事实：缺 `generation` 就不编，符合 `wf-start` 纪律「入口输出的 code/facts 是唯一判定源」 |
| **正面观察 3** | 用绝对解释器路径 `/softwares/python/bin/python3` 调用，符合技能「不装 PATH、不做 shell 别名」 |

**待办**：F2 修技能（补最小信封示例 + `--envelope` 用法 + 宿主拒绝执行时的出口）；F4 与 F2 同批改一句话（generation 何时出现）。

### 9.3 深度分析结论（2026-11-07，未执行任何修复）

**闭环结果（更正此前的猜测）**：`initialize` 任务 `archived`，`complexity=complex`（`reasons=[governance, acceptance]`），`attempts=[(1,'pass',[1,2])]` —— **两次审查轮后通过并归档**。

**量化**：93 条命令；`wf.py` 仅 7 次；`python3 <<PY` 41 次（19 次直连 `from wflib import`）；写任务目录 37 次；读 `.wf/lib` 源码 33 次；`cat wf-continue/SKILL.md` 11 次；触碰 `/tmp/wf-env.json` 51 次；**14.88M input tokens**；任务目录 **52 个文件 / 400K**。

**三处自我纠错**
1. 此前判断"跑不通"错误——实际跑通，问题在成本。
2. 667 那批把 `.wf/baseline.md`、`project-config.json` 划进③ → **initialize 必然 complex**（reasons 里就是 governance+acceptance），是我引入的回归，违反设计稿「新任务首次定义验收不算变化」。
3. `review-launch` 输出的 `commands` 字符串本身极长（`/wf-review --task-id … --round … --reviewer-id … --review-focus … --request <path>`），且 `submitted_scope` 只有三个布尔——**材料从未被物化**，reviewer 实际拿不到，只能靠人贴路径。

**新 review 契约（待实施，2026-11-07 人裁方向）**：reviewer 侧只声明 task id，其余由 `wf.py review-context` 提供；action 侧免路径免轮次；`source-cli` 事后核（≥2 且互异且 ≠ 实施 CLI）。

---

## 10. 重跑 dogfood 的对照清单（2026-11-07，B1–B8 交付后）

> 你先按 §10.1 重置项目；再按 §10.2 跑；把 §10.3 的四个指标填出来，就能判断这批修正是否真的把成本降下来。
> **若这次与上次不同，按 §10.4 的三条定位**。

### 10.1 重置（你已定，照做即可）

```bash
cd /home/xzc/projects/personal/traffic_monitor
ls                 # 只保留 README.md
rm -rf .wf .agents .dsh .codex .claude .gitignore    # 除 README 外清空
git init -q && git add README.md && git commit -qm "chore: 重新开始"
```

### 10.2 安装与首跑（人执行）

```bash
TOOLKIT=/home/xzc/projects/personal/ai-coding-toolkit
RELEASE=/home/xzc/projects/personal/wf-release-0.1.0
PROJECT=/home/xzc/projects/personal/traffic_monitor

cd "$TOOLKIT" && /softwares/python/bin/python3 scripts/build-wf-release.py --version 0.1.0
rm -rf "$RELEASE" && cp -a "$TOOLKIT/docs/workflows/wf-release" "$RELEASE"
cd "$RELEASE" && git init -q && git add -A && git commit -qm "wf release 0.1.0" && git tag wf-v0.1.0

/softwares/python/bin/python3 "$RELEASE/install.py" --target "$PROJECT" \
  --release-ref refs/tags/wf-v0.1.0 --source "$RELEASE" --platform codex --confirm
cd "$PROJECT" && /softwares/python/bin/python3 .wf/bin/wf.py confirm-executor --scope system
git add .wf .agents .gitignore && git commit -qm "chore(wf): 安装 wf 0.1.0 基线"
```

然后开 Codex（`-a on-request -s workspace-write`），在会话里跑 `/wf-start`。

**2026-11-08 起：不需要任何手写信封（步骤 3 已消失）。** 自动身份模式已交付（R1–R5）：

- 身份由执行边界派生（`/proc` 会话 leader + 进程链），项目内落 `.wf/.runtime/anchors.json` 与
  `.wf/.runtime/attachments/<session_key>.json`；
- `activation` / `instance_id` 由入口写运行态并由后续命令自动读取；
- `generation` **仍需携带**（业务并发参数，不是身份）——技能会自己带；
- 只有**拿不到执行边界**时才回退显式信封（见下面"失败出口"）。

### 10.2b 失败出口（按错误码处置，不要手写信封）

| 现象 | 含义 | 处置 |
|---|---|---|
| `WF_IDENTITY_UNRESOLVED`（`reason=no execution boundary resolved`） | 当前形态无锚点（容器逐命令、跨 namespace、Windows/macOS） | 用显式信封（`--envelope <file>` 或 stdin），或换到"保留终端/shell"的形态 |
| `WF_IDENTITY_UNRESOLVED`（`reason=concurrent_unregistered_caller`） | 同一终端里有**未登记**的第二个调用者（C2 分级） | **人**跑一次 `wf.py enable` 显式登记；登记后两者共享同一会话 |
| `WF_IDENTITY_UNRESOLVED`（`reason=evidence_unknown`） | 旧调用者状态读不到（`/proc` 不可读） | 人核实后 `wf.py repair --mark-root-gone --session <key> --root pid:<boot>:<pid>:<start>`（R6 待接线），或换显式模式 |
| `WF_NOT_ENABLED`（`reason=activation_stale`） | 旧根全部确认已死 ⇒ 新调用者须重新启用 | **人**重新 `/wf-start` |
| `WF_NOT_ENABLED`（`reason=activation_missing`） | 附件里没有启用事实 | 人重新 `/wf-start` |
| `WF_REVIEW_INVALID`（`reason=implementation CLI must be declared`） | 发起审查时没声明实施 CLI | 重发 `review-launch --implementation-cli <本会话 CLI>` |
| `WF_REVIEW_INVALID`（`reason=no_claim`） | reviewer 用的 `--as X` 从未跑过 `review-context --as X` | 该 reviewer 先跑 context 再写报告 |
| `WF_REVIEW_INVALID`（`reason=implementation CLI changed`） | 换实施 CLI 后，既有审查结论被标记 `invalidated` | 重跑 `review-decide`（报告可复用） |

### 10.2c 支持的宿主形态（R0 结论，`r0-results.md`）

| 形态 | 支持 |
|---|---|
| 终端单聊天 agent、**zcode 多聊天**（宿主为每聊天派生独立 shell/pty）、IDEA/Zed 集成终端 | ✅ 完整（P1） |
| tmux 多 pane | ✅ 受限（只有 L1） |
| 逐命令新会话的执行服务 | ⚠️ 需显式启用 P2（默认关闭） |
| `docker exec -t` / `docker run` / leader 先死/后台化 | ❌ 不支持（用显式信封） |
| CI runner / Windows / macOS | 未验证 / 首轮不声明 |

### 10.3 四个指标（对比 2026-11-07 首次）

| 指标 | 首次实测 | 目标 | 本次 |
|---|---|---|---|
| `wf.py` 调用占全部命令比例 | 7 / 93 | ≥ 70% | |
| 手写脚本（`python3 <<PY`） | 41（19 次直连 wflib） | ≤5，直连 **0** | |
| 任务目录文件数 | 52 | ≤12 | |
| 单任务 token | 14.88M | ≤5M | |

辅助观察（记进 `dogfood-log.md`）：
- 人被判次数（首次 15 次消息）：目标 ≤8；
- 审查环节是否**只给任务 id + 轮次**，且报告文件名自动是 `review-<agent>.md`；
- `status --short` 是否被用来代替 `cat task.json`；
- 是否出现"自建证据文件"（`finish-commit-manifest` / `verification-v1` / `review-*.json`）——`status` 的 `facts.task.files.unexpected` 会点名。

### 10.4 若表现与上次不同，按这三条定位

1. **它仍在敲裸 `wf.py`** → B3 技能未生效或被旧副本覆盖：`grep -c "review-context" .agents/skills/wf-review/SKILL.md` 应为 1。
2. **它仍在手写证据 JSON** → 命中 `wf.py help <cmd>` 没被使用：看会话里有没有 `help` 调用；没有则说明技能没引导，记缺陷。
3. **复杂任务被判成 light（或反之）** → `status --short` 的 `complexity` 与 `wf.py help task-approve` 的 `plan` 块对不上：先看 `facts.task.complexity`，再看决定文件里有没有 `plan`。

### 10.5 停止条件（同 §6）

出现「阻断且人不知出口」「记录不足以自恢复」「门禁该拒未拒」→ 停止，登记缺陷，不在真实项目里继续试。

---

## 11. 审计：为什么会存在"手写会话信封"这一步（2026-11-07）

### 11.1 文档说谁负责

| 文档 | 原文 | 归属 |
|---|---|---|
| 机制稿 §1.4 | 「**宿主/skill 适配层**把实际上下文中的身份按此映射放入请求 JSON，由入口从标准输入解析；**具体 CLI 外壳交实现方案，不另接受环境变量或命令行覆写身份**」 | 适配层产出信封；入口只从 **stdin** 读 |
| 机制稿 §1.4 | 「activation 是**当前会话由宿主/skill 携带的可丢弃缓存**……缓存保存在**宿主当前会话上下文**，经请求信封传给独立 CLI 进程，**不写进项目 Git、本机解释器确认记录或他人会话文件**」 | 会话级缓存，不入项目 |
| 机制稿 §1.4 | 「宿主无法保证稳定来源时由人选择 wf 签发路径；……已经确认当前实现不支持该传递能力且无可用路径时用 `WF_CAPABILITY_UNAVAILABLE`（**阻断**）」 | 拿不到身份时**阻断**，而不是让人手写 |
| 设计稿 §1.2「最小宿主适配」 | 只列三件事：skill 投放 / 调用权声明 / 会话启用 | **没有"身份注入"这一项** |

### 11.2 发行里有什么

```
assets: lib 24 / template 11 / skill 11 / workflow 6 / bin 3 / installer 1
```

**没有任何 hook / adapter / wrapper 资产**。也就是说：机制稿假定的"宿主/skill 适配层"**在 round 1 没有交付**，而设计稿 §1.2 又没有把它列进"最小宿主适配"——两稿之间的边界上，这块**没有责任人**。

### 11.3 结论（定性）

1. **不是实现违背设计稿**：设计稿 §1.2 从未要求适配层注入身份，实现照做不误；
2. **确实违背机制稿 §1.4 的身份纪律**：人手写 JSON 文件不是被承认的身份来源（机制稿只承认"适配层放入请求、入口从 stdin 读"），且它把 activation 从"会话上下文"降级为"静态文件"；
3. **根因是设计稿漏项**：`§1.2 最小宿主适配` 少了"身份/activation 注入"这一条，导致交付边界无人认领；
4. **次生偏离（我引入）**：B7 的 `--envelope-last` 把activation 缓存落到项目内 `.wf/.runtime/`（虽 gitignored），与"不写进项目"的精神有距离，应登记；
5. 因此"步骤 3"不是设计要求的步骤，而是**缺口的具体表现**——用户"莫名其妙"的感受是准确的。

### 11.4 三个修法（未实施）

| 方案 | 做法 | 代价 / 风险 |
|---|---|---|
| **A（建议）补最小适配层** | 交付两个资产：①Codex `SessionStart`/`UserPromptSubmit` hook：把 `{provider:host, identity:{host_id:<platform>, session_id:<hook 提供的 session_id>}}` 写到**会话级临时文件**（项目外）；②`.wf/bin/wf-run` 外壳：读该文件 + 上一次的 activation/instance_id，拼信封后**管道**给 `wf.py`（入口仍只从 stdin 读，不违反"不另接受环境变量/命令行覆写"） | 需为每个宿主写一次 hook；Codex 已验证可在 hook 里拿到 `session_id`（本仓库 `.codex/hooks/*` 在用） |
| B 提前 wf 签发路径 | 把第二轮的 `provider=wf` 签发提前：`wf.py session issue` 由人显式签发一次性凭证 | 机制稿已定义校验要点（不能因 provider=wf 就视为 verified），实现量中等，但"凭证携带"仍要解决 |
| C 显式降级 | 承认 round 1 用"人写一次性会话文件"，写进设计稿 §1.2 并把适配层列为第二轮 | 最小改动，但等于把人手写文件合法化，与 §1.4 纪律冲突需同步放宽 |

### 11.5 验收判据（修好后应满足）

- 安装完成后，**人不写任何 JSON**；在 Codex 会话里 `/wf-start` 直接可跑；
- `activation` 与身份只存在于会话级载体（项目外或 gitignored 的会话目录），**不出现"人手工维护的信封文件"**；
- 拿不到稳定身份时，入口按机制稿输出 `WF_CAPABILITY_UNAVAILABLE`（阻断）并给出口，而不是让人拼 JSON。

---

## 12. 新方案 P：进程身份（provider=proc），取消信封输入（2026-11-07，待裁）

用户两条硬约束：**①不得为特定 agent 适配；②信封必须最小完整（不占上下文、不破坏判定）**。
方案 A（Codex hook）因此**撤回**——它违反①。

### 12.1 原理

任何 agent 执行命令，都是**它自己的子进程**。所以"哪个会话在调用"可以不问宿主、不问模型，
直接从**进程祖先链**取：取最近一个"非 shell / 非工具"祖先，用 `(boot_id, exe, pid, starttime)` 作为身份。
`starttime` 与锁原语里已用的"存活探测"同一来源（`/proc/<pid>/stat` 第 22 列），能区分 pid 复用。

**本机实测**（两次独立调用）：

```
root: node(pid 5538, start 16466)  → key 0f160e4f42a24898
root: node(pid 5538, start 16466)  → key 0f160e4f42a24898   # 中间多一层 bash 也不影响
```

### 12.2 信封字段的去向（最小完整性）

| 现字段 | 新来源 | 说明 |
|---|---|---|
| `provider` | 固定 `proc`（`host`/`wf` 保留为显式覆盖） | 不再需要人给 |
| `identity{host_id, session_id}` | `(boot_id, root_exe, root_pid, root_start)` | `SessionKey` 仍用同一哈希域 |
| `instance_id` | 从 `.wf/session-bindings/<key>.json` 读 | 绑定本来就有 |
| `activation` | `.wf/.runtime/sessions/<key>.json`（`start` 写、`continue` 读） | 会话级缓存，不随请求传 |
| `inputs.generation` | 从 `.wf/writer.json` 读 | 本来就有 |

→ **调用方零输入**：`wf.py <子命令>` 直接可用，没有信封文件、没有上下文占用。

### 12.3 判定逻辑是否被破坏（逐条）

| 判定 | 是否仍成立 | 备注 |
|---|---|---|
| 写权互斥（holder.id == session key） | ✅ | 仍是同一 key 比对 |
| 跨会话区分 | ✅ | 不同进程 → 不同 key |
| 子代理与父会话 | ⚠️ 同一 key | 视为同一会话（需写明；首轮无实例/子代理语义） |
| **agent 重启 = 新会话** | ⚠️ **实质退化** | 今天靠手写稳定 `session_id` 可跨重启；进程身份不行 → 出口：`ready` + `bind` 一次确认接续 |
| 共享守护进程型 agent（所有会话共用一个服务进程） | ❌ 会话塌陷 | 出口：`--session-token <opaque>` 显式覆盖；或输出 `WF_CAPABILITY_UNAVAILABLE` 给出口 |
| 平台成员判定（host_id ∈ platforms） | 改为 | 改判"共享技能根存在"（`.agents/skills/wf-start`），`root_exe` 仅作审计记录 |

### 12.4 风险与出口

1. **重启即新会话**（唯一实质退化）：`ready` 会给候选，人一次 `bind` 接续；或后续引入"会话令牌文件"（模型不在每条命令带它，只在重启时用一次）。
2. **共享守护进程**：无法从进程树区分 → 必须给显式覆盖或阻断。
3. **跨平台**：Linux 用 `/proc`；macOS 用 `ps -o ppid=,lstart=,comm=`；Windows 需 powershell（慢）。round 1 建议 Linux 优先，其余走 `--session-token`。
4. **伪造面**：模型能算同一 key、也能写 runtime 文件——与今天"能随手写信封"**同级**，不宣称增强（设计稿 §1.5 已声明不建立验证证据链）。

### 12.5 需要的文档改动（大改，但一次到位）

- 设计稿 §1.2 增"身份自取（进程身份）"；§1.4 会话身份定义改写；§1.5 补一条伪造边界；
- 机制稿 §1.4 请求协议改写：`provider=proc` 为默认，`host`/`wf` 保留为显式覆盖；activation 落 `.wf/.runtime/sessions/<key>.json`；
- 实现稿：`cli.Context.envelope()` 改为"自取 + 可选覆盖"；`start` 写 activation 到 runtime；
- 夹具：129 项里凡传信封的都要改（`--envelope` 保留为覆盖/测试通道）。

### 12.6 验收判据（步骤 3 消失的判据）

- 安装后**人不写任何 JSON**，`/wf-start` 直接跑通；
- `wf.py status` 不再要求信封；`status` 不提示"缺信封"；
- reviewer 会话（pi/zcode 等）同样零输入可跑 `review-context`；
- 重启 agent 后 `wf.py ready` 能列出可接续对象并 `bind` 成功。

---

## 13. 综合两份外部评审后的最终方案（2026-11-07，待你裁）

两份评审（/tmp/a.md、/tmp/b.md）交集：**在"禁止宿主适配 + 禁止调用方携带标识"下，任意 agent 的聊天会话不可能被自动识别**；
分歧在"用什么补"：A 主张**显式启动器登记锚点 + 重定义执行会话**，B 主张**锚点只做路由、身份用 wf 签发的逻辑 id，tty 锚免费解决重启连续性**。

### 13.1 采纳要点

| 来源 | 采纳 |
|---|---|
| A | ①`session` 重定义为**wf 执行会话**，不再声称等于宿主聊天会话；②**`generation` 必须保留为请求携带的期望值**（自动读最新 writer 会让延迟请求拿到新代次，破坏旧代次失效）；③`instance_id` 必须与**独立本机附件记录**比对，不能两边都读同一绑定；④平台清单与运行期身份校验**解耦** |
| B | ⑤**tty 锚优先级高于进程锚**（同终端重启可免费续接）；⑥同锚多候选**阻断并列出候选**，绝不静默合并；⑦身份用**`provider=wf` 签发 id**（机制稿已定义、原属第二轮，提前到首轮）；⑧侧车/读取留痕按 session_key 隔离（这也否掉了 D 世系案） |

### 13.2 最终方案（三层）

1. **身份**：`session_id` 由 wf 在**人调 `/wf-start`** 时签发（`provider=wf`），绑定/写权/侧车全按它算 SessionKey（哈希域不变）。
2. **锚点（只做路由）**：`tty(boot_id, tty_nr)` 优先 → `进程锚(boot_id, 最近长命非 shell 祖先 pid+starttime)` → 都没有则 `WF_IDENTITY_UNRESOLVED` **fail loud**。
   映射存 `.wf/.runtime/anchors/<anchor-key>.json`（gitignore、可丢弃）。
3. **附着与校验**：只在人调 start 时建立/复用映射；**同锚多候选 → 阻断列候选**；写权互斥按 session_key 不变；
   `activation` 由入口写 runtime（不从输入读）；`instance_id` 与本机附件记录比对；`generation` 仍按请求携带（可选，省略则 facts 标 `generation_not_pinned`）。

### 13.3 边界（如实写进文档）
- 共享执行服务/无 tty 的 IDE/CI：锚点不可解析 → **阻断并给出口**（后续"领养码"兜底属第二轮）；
- 同终端先后两个 agent：以"start 时报告续接来源 + 人确认"处理；
- 伪造面：同用户可伪造 tty/直写 runtime，与手写信封同级，不宣称认证；
- 平台清单：只作安装事实；运行期不再要求"自动证明来自已安装宿主"。

### 13.4 实施批次（R1–R6，替代原 B 系列中未做的部分）
R1 `session.py` 锚点解析（tty+进程锚，Linux）→ R2 `anchors` 注册表 + start 附着 + `provider=wf` 签发 → R3 `cli` 解析顺序与 instance/activation/generation 归位 → R4 129 项夹具改造 + 5 条新用例 → R5 三稿与技能同步 → R6 收口验证 + 重跑清单。

**验收判据**：安装后人不写任何 JSON；双终端两会话可区分；同一会话多次调用同 key；同终端重启经 tty 续接；同锚多会话阻断；无锚 fail loud；释放再获取后旧代次请求仍失败。
