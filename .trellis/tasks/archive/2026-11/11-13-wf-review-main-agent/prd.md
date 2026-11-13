# wf 审查判定与指引一致性修正

## Goal

在不新增层级、不放宽既有门禁的前提下，修正 `docs/workflows/wf/` 中已由代码与 dogfood 事实核实的结构性问题：

1. **审查判定**：reviewer 报告是辅助证据，主会话必须完成自己的逐轴复核；本轮覆盖由“主会话复核 + 报告意见”共同构成，两者都未覆盖的轴才是缺口。报告未覆盖的轴由主会话补足，补不了才交人，不为此自动加轮。
2. **报告边界**：`read-scope` 与 `excluded-scope` 的矛盾必须被机械检出；删除 `scope-exceptions` / `material-gaps` 这类一义多用的自由文本通道，缺口只走 `axes: uncovered`。
3. **旧口径**：清除 `bind --run`、`run create/advance/terminate/finish`、自动模式 `inputs.generation` 必填、`diff.patch` 相对 HEAD、`report.md` 等已失效说明；执行器纪律只保留一处论述，修掉“审批拒绝后换解释器重试”的自相矛盾。
4. **收尾与身份**：正常归档成功后自动释放写权；`enable` 报告当前绑定，明确“开新任务需要新执行边界”；信封缓存不再共用 `unknown.json`。
5. **§1.1 判据**：把“按动词划分机制/指引”改为“按能否由明确输入稳定计算划分”，收窄“语义分叉”到改变目标/承诺/授权/无法消解的冲突，否定句规则改为“优先正面表述 + 精确边界可否定”。

## 背景事实（已核验）

- 基线提交 `5a55c398`，工作树干净；`scripts/tests` 当前 `wf_review` 251 用例、`wf_runtime` 343 用例全绿。
- 两份分析报告（`/tmp/wf-find-a.md`、`/tmp/wf-find-b.md`）与两份内联报告（a/b）的核心代码主张已逐条对照源码：
  - `scope-exceptions` 目前全部进入 `gaps_out`，不产生问题或失败；`read-scope` 只核非空，`read-scope: [".env"]` 与 `excluded-scope` 含 `.env` 可同时通过。
  - `coverage_state()` 按“任一报告覆盖”取并集；A 五轴 pass、B 五轴 uncovered 时仍视为全覆盖。
  - `authorize.export_scope()` 只绑定 `task + materials` 类别；`default_launch_request().readable_scope.business_code` 取自批准触碰面，窄于设计稿“允许只读业务代码/spec/PRD”。
  - `wf-review:36` 写“相对 HEAD”，实际材料取 `baseline_head`；`wf-review:89` 仍写 `report.md`。
  - `wf-start` 仍称 `bind --run` 未交付，但 `cmd_bind` 与 `_eligible_run_bind` 已实现；`run create/advance/pause/resume/locate/terminate/finish` 均已实现，`instance-flow.md` 与 `runs.py` 的 `next_` 仍写未交付。
  - 实现稿 §2.2 仍写自动模式 `inputs.generation` 必填；代码已支持从本会话运行态取代次。
  - 13 个 skill 复制了同一段执行器纪律，且“审批拒绝后改用另一个解释器”与“不要换路径重试同一效果”冲突。
  - `archive` 成功后 `next_` 仍要求另行释放写权；`wf-finish` 写“按需 writer release”。
  - `remember_envelope` 在无 `session_id` 时写 `unknown.json`，多个会话共用同一缓存。
- 分析报告中需纠正的两处：
  - 报告 (b) 把 `bind --run` 列入“未交付”；实际已交付（`cli.py::cmd_bind` 的 run 分支、`_eligible_run_bind`、`run_candidates`）。
  - 报告 (a) 称部署表“只说明 skill 投放位置”；表里确有 `session_identity` 元数据，但当前没有适配层把宿主会话标识映射进信封，故“没有可操作的逐宿主传递契约”成立，“只有投放位置”过强。
- 身份同进程新聊天无法区分是设计稿 §1.3 已声明的宿主边界；本轮不新增宿主 hook/adapter，只把出口说清楚，避免 `task-new` 试探。

## Requirements

### R1 主会话复核（核心）

- 新增 `review-decide --main-review <file>`；主会话在判定前必须提交本轮五轴复核。
- `main-review` 形状：`{task, round, axes{range,acceptance,contract,regression,testability: {conclusion, basis, sources[], finding_refs[]?}}, report_review[{slot, reliance, notes}], finding_review[{finding_id, slot?, check, basis}]}`。
- 校验：五轴齐全；`pass|fail|uncovered`；`pass/fail` 必须有非空 `basis` 与至少一个来源（`main` 或已导入槽位）；`report_review` 覆盖每份已导入报告；`finding_review` 覆盖本轮每条 finding；`fail` 轴必须指回本轮未关闭的 blocking finding。
- 覆盖：轴由主会话复核 `pass|fail` 或任一报告 `pass|fail` 覆盖；两者都未覆盖才进缺口。缺口仍由人 `--gap-acceptance` 接受；主会话能自行覆盖的轴不触发补轮。
- 主会话 `pass` 不能覆盖未关闭的 blocking finding；`fail` 无对应 finding 时输出需人裁决/修复出口，不写 pass。
- `review-decide --main-review-draft <path>` 生成待填骨架（含已导入报告槽位与 finding 清单），不产生结论。
- `review-status` 显示本轮主会话复核是否存在、五轴结论与报告信赖度。

### R2 报告边界

- `report_input_problems()` 新增 `read-scope` 与 `excluded-scope` 的矛盾检查：读声明命中排除面（或读声明包含排除面）即报问题；`lint`、`import`、`decide` 同源。
- 删除 `scope-exceptions` 的判定消费与文档字段；删除 `material-gaps` / `missing-materials` 的失败消费。缺材料/未覆盖统一写 `axes: uncovered`，由主会话复核补足或人接受缺口。
- `review-context` 返回 `submitted_scope`、`readable_scope`、`exclusions`；`wf-review` 说明只读范围与材料不足的区别。
- `default_launch_request().readable_scope` 改为设计稿口径：业务代码（项目树内、排除面之外）、spec、PRD；`focus_paths` 保留批准触碰面，作为审查重点而非读取上限。
- `derive_verdict()`：五轴全 `uncovered` 的报告自身结论改为 `unavailable`，不再自报 `pass`。

### R3 外发范围

- 保持 `scope_digest = H(task + materials)`；不新增路径绑定。
- 设计稿/机制稿把“本次范围”明确为“任务 + 材料类集合”；具体路径仍由批准触碰面、交付集合与排除面约束，不宣称摘要证明了具体路径。

### R4 旧口径与指引

- 清除 `bind --run`、`run create/advance/pause/resume/locate/terminate/finish` 的“未交付”说明；`upgrade --apply` 仍如实标第三轮。
- 修正实现稿自动模式 `inputs.generation` 必填；改为“运行态缺省、显式可覆盖”。
- 修正 `wf-review` 的 diff 基准与报告命名；修正 `cli.py` 的 `task-rework` 过时注释与 `runs.py` 的过时 `next_`。
- 执行器纪律：在 `payload/workflows/session-flow.md` 写唯一完整论述；13 个 skill 改为一句判断 + 指针；删除“审批拒绝后改用另一个解释器”的表述。
- 持续推进：`wf-start` 选对象后继续该对象第一步；`wf-continue` 增加“在现有授权内推进至必要人判点”；`wf-review-action` 增加 pass 后纯建议的取舍与主动收敛，明确不因建议无限加轮。
- 身份：`enable` 返回 `binding`；已绑定时 `next_` 明确“开新任务需新执行边界”；`wf-start` 不以 `task-new` 试探。
- 归档：正常归档持久化成功后自动释放写权；释放失败作为事实报告，不把归档报成失败。
- 信封缓存：按 `session_id` / `issued_id` 分文件，缺标识时不缓存。

### R5 §1.1 判据

- 机制 = 输入明确、结果可稳定计算的结构/状态/持久化；AI = 授权内的理解、诊断、方案、验证与收敛；人 = 改变目标/承诺/授权边界、不可逆操作、无法在授权内消解的冲突。
- “语义分叉”只保留上述人判情形；等价实现、测试选择、建议取舍不自动交人。
- 否定句改为“优先正面表述；精确权限边界可用否定句，须写明手段与对象并给正例”；“删掉后行为是否改变”作为编辑启发，不作逐句硬门禁。
- 保持“指引就地、不成层”“完整论述只写一处”。

## Constraints

- 不改 charter；不放宽复杂任务“两个异种 reviewer”的承诺；主会话复核是补足与质疑，不替代两位 reviewer。
- 不新增 skill/层级；不新增运行时依赖；不改 `~/projects/personal/traffic_monitor`。
- 新增字段/入口按设计稿第 0 章登记：定义、写者、消费点、失败出口、正反例，并同步设计稿/机制稿/实现稿/索引。
- 任何“人已接受/已放行”仍绑定可核对摘要；主会话复核不能自证关闭 blocking finding。
- 旧报告/旧记录的兼容：无 `main_review` 的旧轮次不追溯改写；新判定必须有主会话复核；旧 `scope-exceptions` 字段被忽略，不再产生缺口。

## Acceptance Criteria

- [ ] R1：`review-decide` 无 `--main-review` 时拒绝产生 verdict；有完整复核时可判；`report_review` 漏槽位、`finding_review` 漏 finding、`fail` 无 finding 引用、跨会话提交均被拒。
- [ ] R1：A 覆盖全部、B 全 uncovered、主会话复核覆盖五轴时，本轮可判且 facts 显示 B 的信赖度为 none；主会话未覆盖的轴才需 `--gap-acceptance`。
- [ ] R1：主会话复核不能覆盖未关闭 blocking；已关闭 finding 后同一轴可 pass。
- [ ] R1：`--main-review-draft` 生成的骨架可直接填写；`review-status` 显示复核状态。
- [ ] R2：`read-scope: [".env"]` + `excluded-scope` 含 `.env` 在 lint/import/decide 三处同报问题；合法补读不误伤。
- [ ] R2：`scope-exceptions` 不再产生缺口或失败；`material-gaps` 不再把材料不足记成 fail；`axes: uncovered` 仍走缺口。
- [ ] R2：`review-context` facts 含 `submitted_scope`/`readable_scope`/`exclusions`；`readable_scope` 不再只列触碰路径。
- [ ] R3：设计稿/机制稿“本次范围”表述与 `task+materials` 摘要一致，不再宣称绑定具体路径。
- [ ] R4：所有“未交付”旧口径清除，`bind --run` 与 run 子命令按已交付描述；`upgrade --apply` 仍标第三轮。
- [ ] R4：13 个 skill 的执行器段落收敛为一处论述 + 指针；无“审批拒绝后换解释器”表述。
- [ ] R4：正常归档成功后 `writer` 为空闲；归档中断不释放；`wf-finish`/`wf-continue` 口径同步。
- [ ] R4：`enable` 返回 binding；已绑定时新任务出口明确；信封缓存按会话隔离。
- [ ] R5：设计稿 §1.1 判据改写完成，机制稿/实现稿/索引无旧“按动词划分”残留。
- [ ] 测试：新增用例覆盖上述正反例；`python3 -m unittest discover -s scripts/tests -t .` 全绿。
- [ ] 文档：`scripts/validate-wf-design.py` 通过；`./scripts/validate-skills.sh` 通过。
- [ ] 发行：重建 `docs/workflows/wf-release/`（版本 `0.1.2`），`python3 scripts/build-wf-release.py --verify` 通过；不建 tag、不推送。

## Notes

- 本轮不交付：Codex 宿主 session id 适配层、`upgrade --apply`、`wf 签发 issued_id` 的显式命令、决定文件骨架生成（除主会话复核草稿外）。
- 分析报告中“平台表只有投放位置”“bind --run 未交付”两处按上述事实纠正，不作为修正依据。
- 设计决策：覆盖不取“交集/并集”的机械算法，而是“主会话复核为必要条件 + 报告补足”；两者都未覆盖才是缺口。
