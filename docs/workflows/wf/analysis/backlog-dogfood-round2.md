# backlog：dogfood 二轮修正（11-21）遗留跟进项

> **状态更新（2026-11-21 收口）**：本文件 §1–§7 全部条目已在本任务内完成处理
>（用户裁决"不留 backlog"）：§1 help 48/48+注册表断言、§2 未知参数校验+WF_USAGE_INVALID
>（37 码）、§3 现场出口（stop preview 免决定/enable 终态/摘要锁定 exits 已存在核验）、
> §4 usage 码迁移（cli 29 处+tasks 20 处）、§5 vendor_dirty 消费点（check/archive
> facts+wf-continue 确认指引）、§6 死指针改写/repo_rules 前置确认指引/五轴 basis 粒度/
> §1.1 归位标注/curation.py 删除、§7 t:<触碰面路径> 判据扩展（K4c 登记）。
> 本文件保留作为处置记录；"已裁决不做"两维持原判（同轮重导入、upgrade 桩）。
> 六轮审查补强（同日收口）：t: 引用绑定 finding 实际位置；repo_rules/delete 确认按内容摘要绑定
>（确认后再改即失效，旧无档确认保持路径级语义不追溯）；归档门禁 exits 指向 authorize record
> 真实通道；expand 单点轻量通道进指引；review-import 摘要冲突补出口；help 补 10 个缺失 flag
> 并加双向断言；task-resume 去掉未消费的 --decision；草稿 at 占位改全匹配 ISO；
> request.json 经 review-context materials 暴露给 reviewer；部分导入聚合各槽位 facts。

# backlog：dogfood 二轮修正（11-21）遗留跟进项

> 来源：2026-11-21 任务 `11-21-wf-dogfood-fixes-round2` 收口前的第三轮外部审查
> （两份报告）。本轮已修项见该任务 implement.md「第三轮审查补充」；
> 本文件只登记**裁决延后**的项。处理时机：下一轮 wf 任务（建议与 0.1.5 同批）。

## 1. help 覆盖 21/48（P0，下一轮优先）

- 现状：`COMMAND_HELP` 21 条 vs `COMMANDS` 48 个；`wf help writer` 等仍报
  `WF_PATH_INVALID unknown command for help`（cli.py 的 help 分支）。
- dogfood 对应失败：AI 现场读源码才知道怎么调入口（最贵的"发现路径"成本）。
- 处置建议：补齐 27 条缺失条目（writer/writer-handover/status/gate/task-rework/
  task-attribute/task-replan/review-accept-unknown/run/dep/spec/enable/verify/version），
  并加注册表断言（`COMMANDS - set(COMMAND_HELP)` 为空），防回潮。

## 2. vendor_dirty 消费点（P1）

- 现状：`.wf/**` vendor 边界正确（不进交付/材料/指纹），`vendor_dirty` 只在
  status/judgments 展示，无门禁、无人确认消费点——dogfood"业务任务里修框架"
  路径仍可静默重演（4/5 时间耗在此）。
- 处置建议：task-check/archive 的 facts 出 `vendor_dirty` + 一次人确认记录
  （不新增命令/skill、**不做硬阻断**——"该不该回源仓库"仍是人判）。
  登记链走机制稿 §1.1（写者/消费点/失败出口）。

## 3. 主会话五轴复核粒度（P1，设计变更）

- 现状：`validate_main_review` 要求五轴全填 + 每轴 basis，草稿只给 blocking 占位
  （review.py）。复杂任务 3 轮 = 40 条 basis 的"满足格式"空转。
- 处置建议：保留"主会话判 pass 必须自己给依据"，允许与采信报告一致的轴用
  `sources` 表达、basis 一句指向；劳动集中到有分歧的轴。需改机制稿 §9.2 与
  `review.py` 校验（含夹具）。

## 4. §1.1 内容归位（P2）

- "执行器解析（唯一定义）/命令启动/分支边界"三段属机制契约，放在 §1.1
  核心原则表后冲淡 AI 指导要点；建议移至 §1.3 或机制稿（同步索引与引用方）。

## 6. 第四轮审查延后项（2026-11-21 收口前登记）

- **未知参数静默忽略**（P0 级风险）：`Args.used`/`rest()` 定义但未消费，`stop --prevew`
  拼错会静默走真实处置。处置建议：`main()` 对各命令注册的合法 flag 集做残留校验，
  未知 flag 报错并给"最近似拼写"提示；需逐命令登记合法参数表（中等工作量，涉及
  全部命令与既有夹具调用面）。
- **缺 usage 类原因码**：`WF_PATH_INVALID` 兼作"缺参数/未知子命令/help 不存在"
  （lib 内 126 处中约 55 处），码级 exit/prohibited_repairs 指向"路径 glob"话术，
  误导 AI 去改触碰面。码表闭集只增不改——新增 `WF_USAGE_INVALID` 类码并迁移
  用法类错误；需机制稿码表登记 + 消费方迁移。
- **现场出口大面积缺失**：check/review/spec/tasks 合计 387/588 处错误无 next_/exits。
  最痛实例：review-import"摘要已锁定"缺"开新一轮 review-launch、旧报告保留原轮"出口。
  处置建议：按"阻断三要素"逐码补齐高频路径（可按 dogfood 触碰频率排序分批）。
- **curation.py 死模块**：全树无 import，实际逻辑在 tasks.py/spec.py 内联；发行清单
  仍投放。处置：删除 + dev-manifest 去登记 + 重建发行。
- **发行件引用未发行上位稿**：skills/workflows 内 16 处"机制稿/设计稿 §x"动作型指针
  在目标项目不可达（且设计稿无 §4.9）。处置：改为就地可执行文字或指向 `.wf/workflows/`
  本地文档；涉及 wf-continue 异常归档行、maintenance-flow 锁异常行等。
- **repo_rules 确认时点**：确认只在归档提交发生，"环境级规则变更确认"保护不到
  变更生效前。属设计变更（改前确认/写入前置阻断需回机制稿 K6 定义），本轮不改授权模型。
- **范围内缺陷的 blocking 引用死路**：wf-review-action 要求"批准判据外但仍在批准
  触碰面内的缺陷继续修、不降级"，但 blocking finding 必须 cite 已批准集合的
  assertion_ref（review.py assertion_index/K4c）——无对应判据时缺陷无法进入审查
  记录。处置建议：扩展 assertion_index 增加"批准触碰面内路径"类引用（如
  `t:<path>`，与既有 `p:` 证据引用同族），机制稿 K4c 同批修订；属机制变更，需人裁。

## 7. 已裁决不做（勿重复提议）

- 同轮报告条件重导入（未被引用且未判定时允许 supersedes）：用户 11-21 裁决
  **维持"导入后不可覆盖"声明边界**，本 backlog 不重开。
- `upgrade --apply`：第三轮能力桩，属已知交付计划；0.1.3→0.1.4 已按
  "卸载重装/整树手工投放"如实声明。
> 七轮审查补强（同日）：K6 确认通道补齐定义位（机制稿登记段 + 设计稿 §6.5 指针 + 索引 140）；
> covers glob 通用展开（requirements-*.txt 类清单原样授权可用）；内容核验任一端读不到即未覆盖；
> t: 引用强制携带 location；码级出口补 expand/--workspace-exclusion 轻量通道；
> record 时序定死为"改动后落档"；草稿占位照抄被全匹配 ISO 拒绝（含断言）。
> 八轮审查补强（同日）：删除类确认补齐可满足口径——record 在删除前落档（绑定被删内容），
> 守卫按"确认时存在、当前已删 ⇒ 覆盖"判定；模式匹配不到已删文件不再算确认不可用。
> 机制稿 K6 段与 wf-continue 指引同步删除例外顺序；删除流正反断言入库。
> （P2-3 草稿占位、b-2 t: 缺 location 为旧树主张——批K 已修且有断言在库。）
> 九轮审查补强（同日）：收工决策面补不可逆确认投影（stop --preview / archive --draft 的
> irreversible facts + wf-finish K6 项 + judgments 删除渲染行）；预存脏文件归属改为
> preexisting_in_scope 事实+指引（不阻断——硬路由会把"在途工作补进任务"的合法主流程拦死）；
> expand 单点确认闭合（classify 判 in_scope + t: 判据面含 expand + delivery 语义升级）；
> 用法校验支持 --flag=value 与 run 子命令级参数收窄；排除声明 help 两入口形状统一。
> 十轮审查补强（同日）：irreversible 投影与归档门禁同源（拟提交路径∪已登记授权，同一
> repo_rule_paths/_deleted_paths 实现）+ 降级 unavailable 可见；草稿占位统一 TODO 前缀、
> 六字段等拒（不再半可过）；check facts 上抛 preexisting_in_scope（断链修复）+ 排除声明
> 接受 preexisting 路径且排除后移出交付（e→x）；布尔旗标注册表 + 缺值旗标拒绝
> （--reason --json 不再吞值、--short stray 不再静默）。
> 十一轮审查补强（11-22）：BOOL_FLAGS 改按命令注册表（--check 在 project 布尔、task-curate 取值；
> upgrade --apply 按 help 登记布尔——帮助示例全部可过用法校验，example 断言入库）；
> 布尔旗标拒绝赋值形态（--preview=true 不再绕过只读分支）；同动作重复授权按累计合并
>（路径并集+摘要并入，quote 取最新）——重复单点扩面不再丢失先前授权（机制稿登记）。
> 十二轮审查补强（11-22）：授权合并三缺口收口——export 落档带 materials 清单、
> 合并材料类并集后**重算 scope_digest**（追加材料类再确认从永远无效变为即时生效；
> legacy 无 materials 记录按新范围整体替换，与 content_digests 兼容口径一致）；
> 路径类键归一列表并集（字符串/列表混用不再碎成单字符、不再静默丢新路径）；
> record_log 按序保留每次 {quote,by,at,source,paths,materials}（原话留痕，
> 顶层凭证字段取最新）——三断言入库；旧 materials 不入库断言迁移为新口径。
> 十三轮审查补强（11-22）：record_log 三缺口收口——条目改取 redact() 后的值（quote 与顶层
> 同遮罩截断，committed 不再落第二条明文原话，含断言）；上限 20 条折叠计数标记；
> 消费点接 authorize show（审计视图输出 record_log，不再只写不读）；legacy 无 materials
> 键的 export 记录按新范围整体替换（注释与实现对齐，出口不再指向无效动作，含断言）。
> 十四轮审查补强（11-22）：legacy 无 content_digests 键时新确认照档（确认后改内容即失效，断言入库）；
> 截断改顶层 record_log_truncated 累计（20 真实条目、标记不占窗口、计数不重复累积，断言入库）；
> 超限逐条原话不再保留记为声明边界（机制稿登记，authorize show 计数可见）。
> 十五轮审查补强（11-22）：covers 的 legacy 并行语义——缺摘要键的路径按 legacy 路径级确认保留
> （追加新确认不溯及旧路径失效；delete 例外：不可逆性最高，legacy 删除须重新确认，断言入库）；
> authorize show 投影补 record_log_truncated/materials/scope_digest（机制稿"计数可见"的声明边界落地，断言入库）。
> 十六轮审查补强（11-22，第 14 次外部审查）：covers 缺摘要三档（content_bound_patterns 区分
> “确认后新增匹配文件须重 record”与 legacy 路径级；repo_rules 确认后删除与 delete 同型例外，
> 断言入库）；reassess 未持权“待复评”分支可达（写权要求后移）；当前 Check 完整脱敏日志
> 物化进材料包（materials/check-logs/ + tests.json 清单，reviewer 不再只能看摘要）；
> 指引五处漂移收敛（扩面通道/采纳建议锚点规则/首轮返工过时句/围栏闭合）；机械修订路由、
> review-notes 位置、__all__ 卫生、writer.json 口径收口；task-approve/replan/rework/stop
> --draft 只读草稿（object_digest/路径预填，TODO 占位预检拒，断言入库）；
> §1.1 两处收窄（客观事实直接核实、残余风险并入判据句主句）。


# 下一任务待办（第 15 次外部审查，2026-11-22 收口时登记——已核验成立、未实施）

用户裁决：先提交 0.1.4 当前已验证状态；以下项在紧随的下一个任务逐批处置，按优先级排。

> **处置标注（2026-11-22，任务 `11-22-wf-dogfood-fixes-round3` 收口）**：
> 下列全部条目已在本任务处置完毕；标注形态＝`已处置（本任务 W<x>）`＋处置摘要。
> 用户裁决"不做顺延"后，登记为"可并入下一轮"的骨架尾项（--plan/judgments --draft）同批完成。

## P0（a 组，上一轮实现的真实缺陷）

- **a-3 验证日志物化未生效**：`write_materials` 读了 `check.started`，实际 Check 字段是
  `started_at`——**分支在真实数据上从不执行，reviewer 看不到完整日志的问题实际未解决**。
  修复：字段对齐 + 用真实 Check 记录的端到端断言。
  **已处置（本任务 W1-a3）**：`started`→`started_at` 对齐；后续审查再补"按命令记录
  证据身份核对"（`logs[].verified`）与 wf-review 判读指引——日志被改写标 verified=false、
  缺失进 status.json.problems，端到端断言落 `test_check_logs_materialization.py`。
- **a-1 content_bound_patterns 合并遗漏**：追加授权只合并 paths/digests 不合并该字段——
  先确认 `.gitignore` 再确认 `requirements-*.txt` 后，新增的 `requirements-prod.txt`
  仍按 legacy 路径级放行。修复：并入合并白名单 + 组合场景断言。
  **已处置（本任务 W1-a1）**：合并段并入 `content_bound_patterns` 并集（与 digests 同型），
  组合场景断言（先 .gitignore 后 requirements-*.txt 再新增 prod.txt ⇒ 未覆盖）入库并做过回退注入。
- **a-2 机械修订路由指错入口**：`wf-continue` 与 `task-replan --draft` 都指向
  `choice=机械修订`，但该命令正式执行只认 replan；机械修订实际在 `task-approve`
  （等价链）。修复：路由句改 `task-approve`（choice=机械修订、PRD 只改排版/转义时不
  重复人批）；草稿入口同步；顺带审视"仍需新的人签决定"与"不重复问人"的口径。
  **已处置（本任务 W1-a2）**：路由句改 `task-approve`；`task-approve --draft` 补机械修订
  骨架（占位写明"仅已有批准后使用"）、`task-replan --draft` 删该骨架；replan 拒绝给
  task-approve 出口。口径审视结论（设计稿记录）：人签保留（散文等价性签认），"不重复问人"
  由"不重复批准"承载。
- **a-4 OSError≠删除**：covers 把权限/IO 错误折成 current=None 后按"确认后已删除"放行。
  修复：改用 `records.file_digest_state` 三态归因，missing 才走删除例外、unreadable 判未覆盖。
  **已处置（本任务 W1-a4）**：covers 与 record 侧同批统一 `file_digest_state`；删除例外
  收紧为 `cause=="missing"`（目录替换不再冒充已删除）；三态断言 + 回退注入入库。

## P1/P2（b 组，需裁决或指引补强）

- b-P1-3：审查序列开头补"authorize record export → 再 review-launch"一句（指引）。
  **已处置（本任务 W2-4）**：wf-continue/wf-review-action/wf-finish 三处补外发确认步；
  后续审查修正口径为"同任务同材料类集合持续有效，不每轮重签"，且 task-check 的 next_
  与门禁同判据前置提示（export_scope_problems）。
- b-P1-4：K6 commit 双轨（authorize record commit 无消费方，实际走 finish 的 commit_grants）——
  **需人裁**：删 commit 类并声明 finish 决定唯一，或让归档守卫消费它。
  **已处置（本任务 W2-1，人裁②）**：删 commit 类（ACTIONS 四类）；提交授权唯一通道＝
  finish 决定 commit_grants；机制稿/设计稿/帮助同批。后续审查补 K6 分码
  （delete/repo_rules/export 各有专属码，不再共用提交码）。
- b-P1-5：control_plane_digest 非交付维度事实（vendor 改动不进锚点、旧 pass 可静默复用）——
  设计变更，**需人裁**。
  **已处置（本任务 W2-2，人裁③）**：常开第 11 键进 Check 锚点（一次性全量失效）；
  呈现伴随键 control_plane_paths 使 drift 可归因"改了哪个框架文件"；
  分类失败归因不改写契约码。
- b-P1-6：review-notes help 示例路径 `<id>/notes.json` 与真实目录 `<id>-<slug>` 不符——
  改为指 `status` 回显的 directory 或加 --review-notes-draft（机械）。
  **已处置（本任务 W2-5）**：帮助改指 `status` 回显的 `<id>-<slug>` 真实目录。
- b-P1-7：单 reviewer 无正常降级路径——**需人裁**：单 reviewer+人接受残余风险留痕，或
  把双 CLI 写进安装前置声明。
  **已处置（本任务 W2-3，人裁④）**：`review-decide --single-reviewer-acceptance`（人签
  残余风险留痕降级，不默认）；接受只降人数，其余门槛照旧；双 reviewer 仍是默认要求；
  收工预览（irreversible.review_degraded）单列降级事实供人判。
- b-P2-8：repo_rules 逐文件硬确认粒度——**需人裁**：任务级合并或降 facts+人判。
  **维持现状（本任务 W2-8，理由留档）**：K6 ⑤ 确认对象恰是"环境级规则变更对后续任务的
  影响"——逐次内容变化逐次确认正是该承诺本体；dogfood 摩擦实例是门禁正确工作。任务级
  合并引入"确认后内容再变仍放行"窗口，与内容绑定不变量冲突，不降档。
- b-P2-9/10/11：重复句收敛、§1.1 边界补充（本地完整路径补异种 CLI 依赖；固定流转清单的
  "三方升级匹配"标第三轮未交付）、两处小文案（archived 绑定 next 提"继续当前对象"无效、
  vendor_dirty 确认无记录载体）。
  **已处置（本任务 W2-9/W2-6/W2-7）**：工作习惯唯一完整定义位收敛＋正面授权与"需人签
  封闭清单"进设计稿 §1.1；三方升级匹配已交付（W4-1）并在固定清单标注交付状态；
  archived 绑定 next 按 enable 终态出口同口径分档；vendor_dirty 确认载体＝judgments
  kind=框架改动（经 --file 条目、task-check/归档 facts 投影 vendor_judgments）。

## 维持已声明边界（勿重复提议）

- 会话身份轮换（P0-1）与 upgrade/回传闭环（P0-2）：既有声明边界，待第三轮交付计划。
  **已处置（本任务 W3/W4）**：P0-1＝`enable --new-session` + Codex SessionStart hook
  适配层（host_hook 资产类、per-asset platform、hooks.json 合并/卸载对称）+ 四态解析
  （在途会话续用优先，不夺走在途任务）；P0-2＝`install.py --upgrade` 三方匹配 +
  预览令牌（三方同源 parity）+ `--export-deviations` 偏离导出回源闭环；0.1.4→0.1.5
  自举升级实跑验证通过（30 路径变更、applied_pending_commit、自检绿）。
  **登记为"可并入下一轮"的骨架尾项（五轮审查 b5）按用户"不做顺延"裁决同批完成**：
  `review-decide --plan-draft`、`judgments add --draft`——至此全部"AI 必须手写的
  结构化文件"均有只读骨架入口。
