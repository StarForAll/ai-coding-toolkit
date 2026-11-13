# 技术设计：wf 审查判定与指引一致性修正

本设计覆盖 PRD R1–R5。每节写：要消除的失败模式、机制契约、落点、失效/兼容、验证。
设计原则：不新增层级；新增记录/字段必须绑定可核对摘要；主会话复核是 AI 判断，机制只核结构与记录。

## D1 主会话复核（R1）

### 失败模式

- 当前 `review-decide` 的结论只来自 reviewer 报告；主会话的 `wf-review-action` 只汇总/处置，不记录自己的逐轴结论。
- 覆盖按报告并集计算：A 覆盖全部、B 全 uncovered 仍算全覆盖；主会话没有补足通道，报告未覆盖的轴只能补轮或人接受。
- 结果：要么“名义两位、实质一位”，要么为补轴反复 `review-launch`，迭代次数不可控。

### 契约

1. **主会话复核是本轮判定的必要输入**。`review-decide` 产生 verdict 时必须带 `--main-review <file>`；`--register-only` 与 `--unavailable` 不产生 verdict，不要求主会话复核。
2. **复核文件形状**：

```json
{
  "task": "t1",
  "round": 1,
  "axes": {
    "range":       {"conclusion": "pass|fail|uncovered", "basis": "…", "sources": ["main", "s1"], "finding_refs": []},
    "acceptance":  {"conclusion": "…", "basis": "…", "sources": ["…"]},
    "contract":    {"conclusion": "…", "basis": "…", "sources": ["…"]},
    "regression":  {"conclusion": "…", "basis": "…", "sources": ["…"]},
    "testability": {"conclusion": "…", "basis": "…", "sources": ["…"]}
  },
  "report_review": [
    {"slot": "s1", "reliance": "primary|partial|none", "notes": "这份报告的覆盖/证据/矛盾点"}
  ],
  "finding_review": [
    {"finding_id": "f1", "slot": "s1", "check": "verified|disputed|unable", "basis": "…"}
  ]
}
```

3. **校验（机制）**：
   - `task`/`round` 必须等于当前判定对象；`round` 必填。
   - `axes` 恰好五轴；`conclusion ∈ {pass,fail,uncovered}`；`basis` 非空；`sources` 是 `main` 与已导入槽位的子集，`pass/fail` 至少一个来源。
   - `report_review` 覆盖本轮每个已导入槽位，`reliance ∈ {primary,partial,none}`，`notes` 非空；不得含未导入槽位或重复槽位。
   - `finding_review` 覆盖本轮每条 finding（按 `(round, slot, finding_id)` 精确匹配；同 id 多槽位时必须带 `slot`），`check ∈ {verified,disputed,unable}`，`basis` 非空。
   - `fail` 轴的 `finding_refs` 非空，且每项指向本轮**未关闭**的 blocking finding；否则 `WF_SEMANTIC_DECISION`（先修复重查，或把问题登记为判断；不得无据判 fail）。
   - 复核记录由入口盖 `by = 当前会话 key` 与 `at`；文件里的 `by` 若存在必须与当前会话一致（reviewer 不能代写）。
4. **覆盖（机制）**：

```text
axis_covered = main_review.axes[axis].conclusion ∈ {pass, fail}
            OR any report.axes[axis].conclusion ∈ {pass, fail}
uncovered = [axis | not axis_covered]
all_uncovered = not any(axis_covered)
```

   - `all_uncovered` → `WF_REVIEW_INVALID`（本轮没有任何来源真正覆盖；不产生 verdict）。
   - 部分 `uncovered` → 人接受缺口（现有 `--gap-acceptance`，按轴集合与 round 绑定）。
   - 主会话复核 `uncovered` 但报告覆盖的轴：该轴算覆盖；`report_review` 记录主会话为何没有独立复核（例如依赖报告并核对了其证据）。主会话复核不应机械复制报告；它必须给出自己的判断依据。
5. **判定（机制）**：
   - 现有 report failures（blocking findings、轴 fail 无 finding）不变。
   - 主会话 `pass` 不覆盖未关闭 blocking：失败集合仍由未关闭 finding 决定。
   - 主会话 `fail` 轴必须对应未关闭 blocking finding，因此失败集合已被包含；不新增“主会话 fail 但没有 finding 就记 fail”的通道。
   - 纯建议不阻塞；主会话复核的 `pass` 与 `report_review.reliance=none` 可同时成立（报告是辅助）。
6. **记录**：`task.reviews.main_reviews[]` 追加 `{round, at, by, file_digest, axes, report_review, finding_review, coverage}`。同一轮已有复核且摘要不同时拒绝（“主会话复核在判定后不可替换；要改结论请开新一轮”）；同摘要重入幂等。
7. **草稿**：`review-decide --main-review-draft <path>` 按当前轮已导入报告生成待填骨架：
   - `report_review` 预填每个已导入槽位（`reliance: ""`）；
   - `finding_review` 预填每条 finding（`check: ""`）；
   - `axes` 五轴占位，`sources` 预填覆盖该轴的报告槽位（主会话可加 `main` 或改）；
   - 不写 `task.reviews`，不产生 verdict；返回 `WF_OK` 与 `next_`。
8. **状态**：`review-status` 的 `coverage` 增加 `main_review`（是否存在/五轴结论/文件摘要）与 `sources`（每轴覆盖来源）；`material_ready` 之外单列 `main_review_ready`，不承诺“可判”。

### 落点

- `review.py`：`MAIN_REVIEW_FIELDS`、`validate_main_review()`、`merged_coverage()`、`main_review_draft()`；`decide()` 在报告输入核验后校验复核并合并覆盖；`status_of_round()` 读取 `main_reviews[]`。
- `cli.py`：`_review_command("decide")` 传 `--main-review` / `--main-review-draft`；`COMMAND_HELP["review-decide"]` 增参数与示例。
- 任务记录模板/机制稿：`reviews.main_reviews[]`；`review-decide` 的 `inputs` 增 `main_review_digest`。
- `wf-review-action`：新增“主会话复核”步骤与判据；`wf-review`：不要求每位 reviewer 覆盖全部轴，未覆盖写 `uncovered`，主会话会补足。

### 失效与兼容

- 旧轮次无 `main_reviews[]`：`review-status` 如实显示“无主会话复核”，不追溯改写旧 verdict；新的 `review-decide` 必须提供。
- 旧报告无 `scope-exceptions` 不影响；新报告不再要求该字段。
- 复核文件是临时输入，记录只存摘要与结构化字段；文件可丢弃，记录可重建。
- 主会话复核不是人批准，不解除任何门禁；blocking 仍须 disposition，finish 仍由人调用。

### 验证

- 无 `--main-review` → `WF_SEMANTIC_DECISION`（给 `--main-review-draft` 出口）。
- 五轴齐全、bases 非空、report/finding 覆盖齐全 → 可判 pass。
- A 全 pass、B 全 uncovered、主会话复核五轴 pass 且 `report_review[s2].reliance=none` → pass，facts 显示 B 为 none。
- 主会话复核某轴 `uncovered` 且所有报告也未覆盖 → 缺口；带 `--gap-acceptance` 后可判。
- 主会话复核 `fail` 无 finding 引用 → `WF_SEMANTIC_DECISION`。
- 主会话复核 `pass` 但 blocking finding 未关闭 → fail（不被覆盖）。
- 同一轮换一份不同摘要的复核重判 → 拒绝。

## D2 报告边界与缺口通道（R2）

### 失败模式

- `read-scope` 只核非空；`scope-exceptions` 全部降为 `gaps_out`；报告自述“读取了排除面”仍可 pass。
- `material-gaps`/`missing-materials` 被记成有效审查 fail，把“材料不足”误记成“代码不通过”。
- 报告字段一义多用：未覆盖、越界、缺材料混在同一个自由文本字段里。

### 契约

1. `report_input_problems()` 增 `read-scope-excluded` 检查：
   - 对每个 `read-scope` 模式 r 与 `excluded-scope` 模式 e：
     - `match_path(e, r)`（e 把 r 当路径匹配）→ 矛盾；
     - `paths.subsumes(r, e)`（r ⊆ e，读取完全落在排除面内）→ 矛盾；
     - `paths.subsumes(e, r)`（e ⊆ r，读取面包含排除面）→ 矛盾。
   - 输出 `{reason: "read-scope intersects excluded-scope", read, excluded, exits: [...]}`。
   - 该检查在 `lint`/`import`/`decide` 三处同源；不解析自然语言，只核可比较的路径模式。
2. 删除 `scope-exceptions`：
   - `REPORT_FIELDS` 已不含它；`report_input_problems` 不再读；`review_report_problems` 删除对应循环；机制稿 §9.1 字段表删除该行；实现稿“六核”删除第⑤项。
   - 报告含该字段时按未知字段忽略（不报错、不产生缺口）；`wf-review` 不再提示写它。
3. 删除 `material-gaps`/`missing-materials` 的失败消费；材料不足写进对应轴的 `uncovered`，由主会话复核补足或人接受缺口。
4. `derive_verdict()`：五轴全 `uncovered` 时返回 `unavailable`（不再 `pass`）；`report_input_problems` 的 declared-verdict 检查据此核对。
5. `review-context` facts 增 `submitted_scope`、`readable_scope`、`exclusions`（取自本轮 launch 记录）；`wf-review` 说明这些是本次授权边界，材料包不足时先在该边界内补读并记 `read-scope`，越界才停止。
6. `default_launch_request()`：
   - `readable_scope.business_code = ["<项目根>/**"]` 语义（项目内业务代码，排除面之外），`focus_paths = approved_touch_paths`（审查重点）；
   - `readable_scope.spec = curation paths`；`readable_scope.prd = prd path`；
   - 文档说明：`focus_paths` 不是读取上限；排除面仍是硬边界。

### 落点

- `review.py`：`report_input_problems`、`derive_verdict`、`review_report_problems`、`default_launch_request`、`context`。
- `wf-review/SKILL.md`：输入说明、步骤 2/5、报告骨架字段。
- 机制稿 §9.1/§9.2；实现稿 §2.3.10；设计稿 §6.5 的“允许自主读取”表述（澄清，不改承诺）。

### 验证

- `read-scope=[".env"]` + `excluded-scope` 含 `.env` → lint/import/decide 同报。
- `read-scope=["pkg/**"]` + 排除面含 `.env`/`node_modules/**` → 通过。
- 五轴全 uncovered 的报告自报 `verdict=pass` → declared-verdict 不一致；自报 `unavailable` → 一致。
- `scope-exceptions` 非空 → 不影响 verdict，不产生 gaps。
- `material-gaps` 非空 → 不再记 fail；对应轴 `uncovered` 时才走缺口。

## D3 外发范围表述（R3）

### 契约

- `scope_digest` 保持 `H("wf-export-scope-v1", {task, materials})`。
- 设计稿 §6.5/§8.2 与机制稿 §9.1 的“本次范围”统一为“任务 + 材料类集合”；补一句“具体路径由批准触碰面、交付集合与排除面约束，摘要不证明具体路径”。
- 不新增 `paths` 字段、不改授权文件形状；`readable_scope` 的放宽只影响 reviewer 本地读取，不影响外发材料类。

### 验证

- 换任务或新增材料类 → `WF_COMMIT_NOT_AUTHORIZED`；同任务同类 → 可复用。
- 文档无“已绑定具体路径”的表述。

## D4 旧口径与持续推进（R4）

### D4.1 身份与新任务出口

- `cmd_enable` facts 增 `binding` `{object, instance_id}`（无绑定为 `null`）。
- `next_`：
  - 已绑定：`"已绑定对象 <id>：继续当前对象；要开新任务请在新执行边界/新会话里选择（同进程内无法区分时开新终端）"`。
  - 未绑定：`"人显式选择对象：task-new、bind --task，或 run create"`。
- `wf-start`：
  - 删除 `bind --run` 未交付说明；实例接续写 `bind --run <id>` 已可用。
  - 步骤 2 改为：已绑定只恢复；人想开新任务时停止并说明需要新执行边界，不以 `task-new` 试探。
  - 步骤 1 的 `host_identity_absent` 警告与出口对应。
- 部署表注释：`session_identity` 是来源声明，wf 不安装宿主 hook；无适配层时按 `unknown` 处理，不猜。

### D4.2 已交付能力口径

- `wf-start`、`wf-continue`、`instance-flow.md`、`wf/README.md`、`runs.py` 的 `next_`、`cli.py` 的 `task-rework` 注释：删除“未交付/尚在交付/桩”的过时说明；`upgrade --apply` 保留第三轮。
- `wf-continue` 路由：`run terminate/finish` 按已交付描述；归档后写权释放改为自动，保留“归档中断/释放失败”恢复路由。

### D4.3 执行器纪律单源

- `payload/workflows/session-flow.md` 新增 `## 运行约定（执行器）`：
  - 解析顺序：项目 `python_executable` → 本运行时 Python → 系统 `python3`；取到能跑的就整会话固定复用。
  - `WF_EXECUTOR_UNCONFIRMED` / 审批拒绝：停下报告事实，由人确认执行器或调整策略后重跑；不换解释器重试同一命令，不改写信封/路径绕过；不装 PATH、不做 shell shim。
  - 卸载/repair 的独立入口例外按设计稿 §1.1。
- 13 个 skill 的“纪律”段替换为一句：`解释器按 .wf/workflows/session-flow.md「运行约定」选择并整会话固定；WF_EXECUTOR_UNCONFIRMED 或审批拒绝时停下报告，不换解释器重试。`
- 删除“审批拒绝后改用策略允许的 Python 绝对路径并固定下来”的表述。

### D4.4 持续推进

- `wf-start` 首句：`启用 + 选对象 + 取得写权；选定后继续该对象的第一步（新任务→PRD/规划；实例→run advance），不把“已启用”当终点。`
- `wf-continue` 首段新增：`在现有授权与批准目标内持续推进调查、实现、必要修复、验证与下一步准备，直到完成条件满足或需要人新增授权/改变承诺/明确人判；不因一个 skill 段落结束或一条命令返回而停下。`
- `wf-review-action` 新增“pass 之后”：
  - 纯建议逐条判断本轮是否采纳；采纳需改代码时按新锚点重查/重审，不采纳留档说明理由；
  - 没有未关闭 blocking、缺口已接受或无需缺口 → 准备收工材料，交人调用 `wf-finish`；
  - 不为了“把所有建议做完”无限加轮。
- `wf-finish`：归档成功即释放写权；删除“按需 writer release”；保留“归档中断/释放失败”的核对出口。

### D4.5 归档自动释放

- `cmd_archive` 在 `archive_persisted` 为真后，于同一锁内调用 `cli._release_writer_locked(ctx, holder)`：
  - 重读 writer，确认 holder 仍是本会话；调用 `writer_mod.release` + `_atomic_writer_action("writer.release")`。
  - 释放失败不把归档报成失败：`facts.write_release = {released: false, reason}`，`next_` 给 `writer release` 恢复出口。
- `archive` 的 `next_`：成功释放 → `"归档已完成，写权已释放；下一对象需在新会话选择"`；未释放 → 保留恢复说明。
- `wf-finish` 步骤 4 改为“归档成功时入口已释放；若回显 `write_release.released=false`，按提示重跑 `writer release`”。

### D4.6 信封缓存

- `remember_envelope` 缓存键：`identity.session_id` → `identity.issued_id` → 不缓存。
- `--envelope-last --session <id>` 的 `<id>` 接受这两种值；缓存文件同名规则不变。
- 缺标识时不写 `unknown.json`，避免多会话共用。

## D5 §1.1 判据（R5）

改写设计稿 §1.1 的两段：

1. **判据分工**：用“能否由明确输入稳定计算”替代动词清单；机制/AI/人三分的定义按 PRD R5；明确“同一步骤可同时包含三者”。
2. **指引就地、不成层**：保留；判据句改为“需要 AI 在授权内理解/判断/择优/表述 → 指引且就地；能由明确输入稳定计算并产生同一结果 → 机制且进代码；只有改变承诺/授权/目标或无法消解的冲突 → 交人”。
3. **语义分叉**：保留术语，定义收窄；固定流转程序化段的“语义分叉点”举例保留（范围语义存疑、规划语义变更、知识准入冲突），并补一句“等价实现、测试选择、建议取舍不属此列”。
4. **写作规则**：否定句改为“优先正面表述；精确权限边界可用否定句，须写明手段与对象并给正例”；“删掉后行为是否改变”作为编辑启发。
5. 机制稿/实现稿如复述同一判据，改为指针或同步改写；索引中对“语义分叉”的引用仍有效（术语保留、定义收窄）。

## 回滚与风险

- 主会话复核是新增必要输入：旧任务的新判定会被要求补复核；这是预期收紧，不追溯旧 verdict。
- 删除 `scope-exceptions`/`material-gaps` 会让旧报告中的这些字段失效；旧轮次已判结果不改写，新轮次按新字段。
- 归档自动释放改变 writer 终态；若外部脚本依赖“归档后 writer 仍 held”，会在 `writer release` 处得到“已空闲”的事实。按设计稿 §4.4，归档后释放是正常收尾，保留绑定。
- 覆盖合并仍是“主会话 + 报告”的两源事实，不承诺机械防止主会话敷衍；强度声明按设计稿 §1.5 如实写，不宣称防对抗。
- 发行版本递增到 `0.1.2`，不建 tag、不推送。
