# 第四十六轮：第三轮独立复审 + 其他 agent 反例的复核与修正

- 处置编号 R81；实跑见 `validation.md` §73
- 结论：**13 条行为缺陷成立并已修**（复审 6 条 + 其他 agent 7 条）；4 条通过/观察项按原判定登记；1 条验证材料问题（检查对象错位）已修。
- 这一轮最重的两条都在**我上一轮自认为已经补好的地方**：install 的资产边界、Check 的 manual 证据。

## 一、第三轮独立复审（codex 新会话）

| 编号 | 复审结论 | 复核 | 处置 |
|---|---|---|---|
| D-B4-1 | install 投放不核 `target_relative`（高） | **成立** | R81-a |
| D-A1-5 | 门禁侧 manual 验证不核人判证据（高） | **成立** | R81-b |
| D-B2-1 | 归档恢复假阴性（中） | **成立** | R81-c |
| D-B1-1 | spec 删除解除依赖不核决定内容（中） | **成立** | R81-d |
| D-A3-1 | 脱敏漏 JSON 内嵌（中） | **成立** | R81-e |
| D-B2-2 | 恢复分支不续做业务提交（低-中） | **成立** | R81-c |
| B3 治理面枚举 | 通过（附观察） | 同意 | 登记差异：`witnessed` 在 `.gitignore` 忽略面上漏检，但 `prefix-unexcluded` 兜底使条件①结果一致 |
| B5 写者交接 | 通过 | 同意 | 无旧代次可写路径 |

**R81-a install 资产边界**：`install.py` 的投放循环原来只 `os.path.join(base, *relative.split("/"))`，没有路径合法性、真实落点与类别白名单——清单里一条 `../escape.txt` 就能写到目标目录外，而 `uninstall.py` 对同一份清单整批拒绝。新增 `safe_relative()/inside()/plan_writes()` 与 uninstall 同判据，**任一不合规即在写任何文件之前整批拒绝**（`plan_writes` 有问题时直接返回空写入计划）。实测：`../`、未知类别、符号链接逃逸三种都被拒；`release_only` 正常跳过。

**R81-b manual 证据**：`validate_check_result` 只核 `status`，`kind=manual` 的命令没有 decision 也能过。补上：decision 必须是非空对象、`choice == "passed"`、且 `_decision_covers()` 覆盖本项（与生成端 `_manual_command` 同判据）。这样「生成端与门禁端共用同一实现」才真的成立。

**R81-c 归档恢复**：恢复分支提交成功后调 `archive_persisted()`，而它的第一道判定是 `action.kind != "task.archive"` 就返回 `no archive action`——于是**提交成功却报 `WF_PERSISTENCE_FAILED`**。改法：`archive_persisted(root, task, lower_override=…)` 支持「以刚做的记录组提交的父提交为下界」，下界来源写进 facts（`lower_bound_source`）；恢复分支同时按 `commit_grants` 补做业务提交（授权事实已在记录里），并把业务提交结果放进 facts。

**R81-d 解除依赖**：`released.decision` 可空，空决定也能解除活动依赖。新增 `_require_release_decision()`：必须是对象、`choice` 非空、`reason` 非空，`validate_changes` 与 `_release_dependencies` 两处都调用。

**R81-e 脱敏**：JSON 内嵌（`{"token":"x"}` 等 6 种）全漏。补一条带引号的键值规则，并加键名边界（`tokenizer`/`max_tokens`/`token_type` 这类不遮，修掉 `tokenizer → ***` 的误伤）。

## 二、其他 agent 的 7 条

| # | 问题 | 复核 | 处置 |
|---|---|---|---|
| 1 | `spec --json` 记 `complete=true` 但 `content=null` | **成立** | 两路都交付正文；`content` 就是 `loaded["text"]` |
| 2 | `task-new` 先写绑定后建 `task.create` 动作 | **成立** | 改为**先落恢复意图**（动作与四步写进主记录）再取写权、写绑定 |
| 3 | 规则指纹只取一个 skill 根；相对根按 cwd 解析 | **成立** | 每个已登记根各算一项；相对根按项目根解析（`join(root, item)` 本就如此，问题在"只取第一个存在副本的根"） |
| 4 | `path_identity` 相对候选按 cwd 解析 | **成立** | 先拼目标项目根再 realpath，与执行候选同源 |
| 5 | `project_key_approved` 只做文本匹配；损坏全局配置阻断有效项目配置；非字符串值抛 TypeError | **成立** | 批准证据要求任务 `plan.approval` 非空或已正常归档；有效项目配置优先、不再读全局层；类型校验给结构化出口 |
| 6 | `capability.status=verified` 缺结构与证据也通过 | **成立** | 补结构核验：`host_id`/`provider`/`transport`/`evidence_refs` 缺一即 `WF_IDENTITY_UNRESOLVED`（核声明结构，不核人的真实性） |
| 7 | `wf-start` 的 activation 缓存与 wf 签发路径没讲完整 | 部分成立 | 文档已在上一轮写明重放要求；本轮补验（用例 A7）。`issued_id` 的显式签发命令属第二轮对象，明确登记不做 |

## 三、验证材料收口

`check-doc-refs.py` 默认检查 `docs/workflows/workflow-implementation.md`（旧计划的宽松文档），不带参数跑它并不能证明当前实现方案通过——复审这条判断成立。已把默认目标改为当前 wf 三稿（机制稿由 `validate-wf-design.py` 核），并修掉实现稿里 8 处缺所有者前缀/指向不存在章节的引用，现为 **0 problem**。

## 四、期间新发现（都是我自己改出来的）

- **N-R75**：重写脱敏函数时把 `SEPARATED_FLAGS` 一起删掉，`task-check` 直接内部错误 exit 70。与上一轮 N-R66 同类——批量替换必须按符号边界核对。
- **N-R76**：恢复分支读 `commit_grants` 当作 `{"paths": [...]}`，实际是 Decision 数组 → `'list' object has no attribute 'get'`。
- **N-R77**：`cp5_b345`/`p5_spec` 的解除依赖输入用 `released: True` + 字符串 `decision`，与"人判必须是 Decision 对象"冲突。fixture 改为 Decision 对象（判据不变，测的是同一件事）。
- **N-R78**：`r64` 断言「json 模式不带正文」，与"读取留痕要真实"冲突。改为断言 json 也交付正文。
