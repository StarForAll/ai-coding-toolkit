# Check Report — dsh-trellis 0.3.8 对标修复复核

> 角色：`trellis-check`（子代理）｜对象：`dsh-plugins/dsh-trellis` 0.3.8（未提交）
> 证据等级：E1 = 本次实际运行；E2 = 静态推断；E3 = 文档/测试声明。结论只用 E1，E2/E3 显式标注。
> 改动范围：仅 `dsh-plugins/dsh-trellis` 与本任务目录；未提交、未 push、未 stash，未触碰其他仓库文件。

## 0. 结论

**PASS WITH FIXES。**

- 0.3.8 声称的 P0/P1/P2/P3 修复**方向正确、效果可复现**：真实 `.trellis/workflow.md`
  与全新 `trellis init` 项目上，插件的 9/8 个状态块正文与 Python carrier **逐块完全一致**；
  workflow 选择优先级、`stale`、`completed`、项目 skip keyword 均按声明生效。
- 确认 **3 项缺陷**：2 项（D2、D3）已在插件内修复并回归；1 项（D1）是平台契约冲突，
  影响用户当前所有 DSH 会话，已提前上报主代理，**未擅自回退**（见 D1 的做法与理由）。
- 另有 4 项低严重度差异/缺口（D4–D7）记录在案，未改代码。
- 测试：复核前 282 tests / 278 pass / 0 fail / 4 skip（与其记录一致）；修复后
  **287 tests / 283 pass / 0 fail / 4 skip**。

## 1. 复核方法（全部 E1）

| 手段 | 说明 |
| --- | --- |
| 真文件对照 | 同一份 `.trellis/workflow.md`（本仓库 773 行、8 个真块）与 `/tmp/trellis-e2e`（`trellis init` 0.7.0-beta.4 模板）分别跑 `lib/workflow.js` 与 `.codex/hooks/inject-workflow-state.py` 的 `load_breadcrumbs` |
| 真配置对照 | `.trellis/config.yaml` 的 `codex.dispatch_mode` / `default_workflow` / `skip_keyword` 分别用插件解析器与 `.trellis/scripts/common/{config,trellis_config,workflow_selection,active_task}.py` 解析 |
| 旧行为模拟 | 把插件复制到 `/tmp/old-plugin`，将 `STATUS_RE`/`mapStatus`/`resolveWorkflowPath`/`breadcrumbStatus`/composer skip 关键字回退到 0.3.7 语义后跑**新测试文件**，验证测试是否真的能抓住旧行为 |
| 真文件系统端到端 | 临时项目 `/tmp/skipcheck`、`/tmp/ptrtest` 上用 `nodeFs` 跑 `createSessionComposer().compose()` 与 `hasReadableTask`/`parentTaskPath` |

关键对照结果：

| 对照项 | 插件（0.3.8） | Python carrier | 结论 |
| --- | --- | --- | --- |
| 本仓库 workflow.md 全部块 | 9 块，`no_task` 421/3 行…`my-status` 25/1 | 同（9 项逐一字符数一致） | 一致 |
| 全新项目 workflow.md | 8 块（无 `stale` 块），`no_task` 421/3 | 同 | 一致 |
| `codex.dispatch_mode` 8 种写法（缺省/空节/flow map/带引号/非法/空值/sub-agent/无文件） | auto/auto/auto/inline/inline/inline/auto/auto | 完全同（flow map 两侧都退回 auto，Trellis 会 stderr 警告） | 一致 |
| `default_workflow` 8 种写法 | 7 项一致；仅"根键缩进"一处 Python 视为有效、插件跳过 | — | 可忽略 |
| skip keyword 13 组输入 | 修复前 4 组不一致；**修复后 13/13 一致** | — | 见 D3 |

## 2. 确认的缺陷

### D1（未修复，待用户决策）`*-inline` 块被应用到 DSH，与 Trellis 自身契约冲突

**现象（E1）**：本会话指针 `dsh_session-b91f0b24-…` 指向
`.trellis/tasks/10-21-dsh-trellis-parity-audit`（`status: in_progress`），
`resolveTrellisState` 现返回 `status: in_progress-inline`、body 325 字符；0.3.7 返回
`in_progress`、body 1635 字符。

**契约证据（E1/E2）**：

1. `.trellis/workflow.md:223-228`、`:257-261` 明确标注这两个块是 **"Codex-only opt-in alternate"**；
2. `.codex/hooks/inject-workflow-state.py:365-382`（`.claude` 同）
   `resolve_breadcrumb_key()` 只在 `platform == "codex"` 时返回 `f"{status}-inline"`；
   实测同一 `status=in_progress` + 同一 config：`platform=None → in_progress`（1635 字符）、
   `platform="codex" → in_progress-inline`（325 字符）。
   同一函数对 `completed` 也会返回 `completed-inline`（插件只对 planning/in_progress 生效，见 D5）；
3. `docs/workflows/新项目开发工作流/commands/shell/patch-inject-workflow-state.py:38-51`
   的补丁同样是 `if platform == "codex"`；
4. DSH 侧没有 carrier 可依赖：`_detect_platform` 的 env 表与脚本路径表都没有 DSH 项，
   因此"DSH 平台"在 Trellis 自己的实现里就是 `platform=None`（不选 inline）。

**影响（E1）**：本仓库 `.trellis/config.yaml:150-151` 默认就是
`codex: dispatch_mode: inline`，因此**所有 DSH 会话的每轮面包屑**从
`in_progress`（含 "On DeepSeek Harness, role instructions ship as … `trellis_wait` …"、
"Main-session default: dispatch implement/check sub-agents"）变成
`in_progress-inline`（"Do not dispatch implement/check sub-agents in inline mode."）。
这与同仓库 AGENTS.md、`.dsh/skills/trellis-agent-*`、插件自身的 dispatch-guard /
subagent push / `trellis_wait` 直接矛盾——本次复核本身就是主会话派发的
`trellis-check` 子代理，即该矛盾的现场实例。

**处理**：已提前把证据与建议发给主代理（`session-b91f0b24…`），**未改代码**，因为
P2-6"纳入 inline"是用户明确确认过的范围，检查角色不应单方面反转。两条可选路径：

- 推荐：DSH 侧不应用 `codex.dispatch_mode`（恢复 `planning`/`in_progress`，把 P2-6 记作
  有意的平台差异），与 Python carrier 的 `platform == "codex"` 判定完全一致；
- 若坚持保留：必须在 `README.md` / `LOCAL_CHANGES.md` 写明"该块在 workflow.md 中标注为
  Codex-only，DSH 选择它是本地扩展，会覆盖 DSH 专属的派发指引"，并接受与 dispatch-guard
  等机制的语义冲突（E2：未见任何自动化能检出该冲突）。

### D2（已修复）空/空白正文的状态块被当成可用模板

**证据（E1）**：同一份含 `[workflow-state:in_progress-inline]\n   \n[/…]` 的 workflow 内容：

| 实现 | 结果 |
| --- | --- |
| Python `load_breadcrumbs` | `{'planning': 'REAL', 'in_progress': 'REAL2'}`——空正文块被丢弃（`if body: result[status] = body`，`.codex/hooks/inject-workflow-state.py:253-256`），inline 键查不到时回落到 `in_progress` 正文 |
| 插件 0.3.8 | `in_progress-inline → ""`，`blocks.get()` 返回 `""`（非 nullish），inline 分支把**有内容的基块顶掉**，最终注入 body 为空的面包屑 |

`task_error` 因 `||` 兜底不受影响，`planning-inline`/`in_progress-inline` 与任何"空块降级"
场景受影响。这是 0.3.8 新增 inline 选择后才可触达的路径（复核时用"inline 选择 + 旧解析器"
构造，测试失败，见 §4）。

**修复**：`lib/workflow.js:58-68` `parseWorkflowStateBlocks()` 只保存非空正文
（与 carrier 的 `if body:` 同义）。修复后同一输入 JS 返回 `[planning, in_progress]`，
与 Python 完全一致。测试：`test/workflow.test.js` 新增
"parseWorkflowStateBlocks drops empty and whitespace-only bodies"、
"an empty inline block does not shadow the base block"。

### D3（已修复）跳过关键字的边界判定与 carrier 不一致

项目级 `prompt_injection.skip_keyword` 是跨平台输入，判定必须与
`prompt_has_skip_keyword`（`inject-workflow-state.py:296-309`，
`(?<![\w-])keyword(?![\w-])`，大小写不敏感，`inject-workflow-state.py:299-309`）一致。原实现用 ASCII `\b`，13 组对照中 4 组相反：

| keyword | prompt | 修复前插件 | carrier |
| --- | --- | --- | --- |
| `no-trellis` | `foo-no-trellis this turn` | **true（误跳过）** | false |
| `skip-trellis` | `foo-skip-trellis` | **true（误跳过）** | false |
| `skip.` | `please skip. then` | **false（该跳过没跳）** | true |
| `#skip` | `please #skip then` | **false（该跳过没跳）** | true |

多词、下划线、大小写、`(no-trellis)`、`no-trellisx` 等 9 组原本就一致。

**修复**：`lib/breadcrumb.js:72-79` 改为
`(?<![\p{L}\p{N}_-])<escaped>(?![\p{L}\p{N}_-])` + `iu`（`\p{L}\p{N}_` = Python 的
Unicode `\w`）。修复后 13/13 与 carrier 一致，含中文关键字
（`跳过abc` → false、`请 跳过 这次` → true、`请跳过这次` → false，两侧同）。
测试：`test/breadcrumb.test.js` 新增 "skip keyword boundaries mirror Trellis's
prompt_has_skip_keyword"。

### D4（记录，未改）会话指针 ref 未按 Trellis 归一 → 假 `stale` / 误 `task_error`

`lib/workflow.js:257-263` 直接用 `join(root, data.current_task)` 判存在，
而 `common/active_task.py` 的 `resolve_task_ref` 会先 `normalize_task_ref`
（`tasks/x` → `.trellis/tasks/x`；绝对路径原样；越界拒绝），再用 `not is_dir()` 判 stale。
实测（E1，`/tmp/ptrtest`）：

| 指针值 | Trellis | 插件 0.3.8 |
| --- | --- | --- |
| `.trellis/tasks/ofile`（同名**文件**而非目录） | `stale=True` | `task_error`（提示修 task.json，指向错误） |
| `tasks/real`（省略 `.trellis/` 的旧式 ref） | `planning`（正常解析） | `stale`（假失效） |
| `/abs/.trellis/tasks/real`（绝对路径） | `planning` | `stale`（`join` 把绝对段当相对段拼接） |

可达性低：Trellis 写入指针时一律用 `_canonical_task_ref` 的 `.trellis/tasks/<slug>` 形式，
只有手写指针或手写 `Active task:` prelude 才会命中；且这是 0.3.7 就存在的归一缺口，
0.3.8 只是把结果从 `task_error` 变成 `stale`。建议下一轮把
`normalize_task_ref` + `is_dir` 判定补进 `resolveActiveTask`（需给 `nodeFs.stat` 增
`isDirectory`），并在 dispatch-guard / push 路径复用同一归一函数。

### D5（记录，未改）inline 只对 `planning`/`in_progress`；doctor 不反映选中的变体

- `lib/workflow.js:171-180` 只对两个状态尝试 `*-inline`，carrier 对任意状态都尝试
  （`completed-inline` 等）。0.7 模板只有这两个变体，故实际等价；团队自定义 `*-inline`
  会导致两平台提示不同。`docs/validation-0.3.8-local.md` "已知边界"已声明该收敛。
- `lib/doctor.js:90-109` 仍固定读 `.trellis/workflow.md`，不读
  `resolveWorkflowPath` 选中的变体：任务 pin 了 `alt.md` 时，doctor 的
  "Workflow: N blocks" 描述的文件并不是当轮在用的文件。属新增特性带来的诊断缺口（E1：
  代码路径 + 临时项目报告实测），不影响注入行为。

### D6（记录，未改）零块/工作流文件缺失时静默（carrier 会给通用行）

`lib/workflow.js:362-364`：`content === null` 或 `blocks.size === 0` → 返回 `null`（不注入），
carrier 则输出 "Refer to workflow.md for current step."。这是插件既有且被测试固化的设计
（"zero workflow-state blocks → silent"）；但有了 workflow 变体后，"pin 的变体没有块"
这一新可达状态会让两平台从"降级提示"变成"完全静默"，偏差被放大。

### D7（记录，未改）琐碎差异

- 任务 pin：插件 `task.workflow.trim()`，Trellis 不 trim（`" alt "` 在插件生效、在 Trellis 被判非法后回落）；
- `skip_keyword: 123`：YAML 是 int，carrier 因 `isinstance(raw, str)` 不成立回落 `no-trellis`，插件字面取 `"123"`（E2：读码推断 + 解析器实测）；
- `prompt_injection:` 用 flow map 写法时两侧都回落默认（Trellis 会警告），无偏差。

## 3. 已应用的修复（3 个文件 + 测试，均在 `dsh-plugins/dsh-trellis` 内）

| 文件:行 | 改动 |
| --- | --- |
| `lib/workflow.js:60-68` | `parseWorkflowStateBlocks` 丢弃空/仅空白正文块（D2） |
| `lib/breadcrumb.js:72-79` | `hasSkipKeyword` 边界改为 Unicode + 连字符同级于 carrier（D3） |
| `test/workflow.test.js` | +2 用例（空块丢弃；空 inline 不顶掉基块） |
| `test/breadcrumb.test.js` | +1 用例（13 组边界，含中文） |
| `test/dispatch-guard.test.js` | +1 用例：`stale` 指针（目录已删）在守卫中不可读 |
| `test/subagent-context.test.js` | +1 用例：`stale` 父指针不提供 push 路径；并断言 P3-7 的覆盖文案 |
| `LOCAL_CHANGES.md` | 新增 "Check round 0.3.8" 段（两处修复 + 依据 + 新增覆盖 + 测试数） |
| `docs/validation-0.3.8-local.md` | 新增 "检查补充（trellis-check）" 段，不改原 GATE 与结论 |

## 4. 测试结果（E1）

| 阶段 | 命令 | 结果 |
| --- | --- | --- |
| 复核前基线 | `node --test "test/*.test.js"` | 282 tests / 278 pass / 0 fail / 4 skip（与其记录逐项一致） |
| 旧行为模拟 | `/tmp/old-plugin`（回退到 0.3.7 语义）跑 `test/workflow.test.js test/session-composer.test.js` | 49 tests / 36 pass / **13 fail** |
| 我新增用例是否有效 | 同上跑更新后的两个测试文件 | 50 tests / 37 pass / **13 fail**：新增"空块丢弃""边界 13 组""push 覆盖文案"均失败；"空 inline 顶掉基块"在"inline 选择 + 旧解析器"组合下失败 |
| 修复后 | `node --test "test/*.test.js"` | **287 tests / 283 pass / 0 fail / 4 skip** |
| 真文件系统端到端 | `/tmp/skipcheck` 上 `compose()` | 项目 `skip_keyword: skip-me` → 0 条；`foo-skip-me` → 1 条；`no-trellis` → 1 条（项目值优先）；stale 指针 → 仅 1 条 stale 面包屑（带 digest，无 bootstrap） |

13 个在旧行为上失败的用例：`mapStatus` 透传、注释内标签、行内标签、`completed` 块、
自定义状态回落、`stale`（有块/无块）、workflow pin / personal / team 三个优先级、
inline 选择、项目 skip 关键字（2 个）。**这 13 个是真回归测试**；仅
"dispatch_mode=auto 保持普通块""非法变体 id 被忽略""插件 skipKeyword 兜底"三个是护栏
（旧代码也通过）。

## 5. 测试质量评估

- 0.3.8 新增测试**没有**编码实现细节，证据是上面 13 个在旧语义下确实失败；断言语义
  （"completed 用 completed 块""空块降级"）而非内部结构。
- 遗漏已补：`stale` 在 dispatch-guard（`lib/dispatch-guard.js:70-74`）与
  `parentTaskPath`（`lib/subagent-context.js:489-499`）的行为无任何用例；P3-7 文案无用例。
- 仍缺（本轮不补，需真实进程）：inline 选择在真实 DSH 会话中的行为（D1 的最终判定）、
  `trellis_wait` 结算、compaction 后重投递、doctor 变体展示。

## 6. 文档/代码一致性

- `README.md:277`（状态解析段）、`README.md:5`、`README.md:254`（skip keyword 优先级）与实际
  行为一致；`LOCAL_CHANGES.md` 的 0.3.8 表逐条可复现。
- `docs/validation-0.3.8-local.md` 的量化声明抽检通过：真实 workflow `no_task` 421 字符 /
  3 行、面包屑 491 字符（=491 字节）、全新项目模板确实**无** `stale` 块（`grep -c` = 0）。
- 唯一实质漂移：`LOCAL_CHANGES.md` 0.3.8 表 inline 行的理由"A project that opted into inline mode must see
  the same step contract on DSH"与 `.trellis/workflow.md:223-227` 的 "Codex-only" 注释、
  carrier 的 `platform == "codex"` 判定冲突（见 D1）。若保留现状，这句话需要改写并补注。
- 我改动的两处行为已同步进 `LOCAL_CHANGES.md` 与验证记录，避免新的文档漂移。

## 7. 残余风险 / 无法验证

1. **D1 未决**：在用户决定前，本仓库所有 DSH 会话继续收到 `*-inline` 面包屑，
   与 DSH 派发指引冲突（本轮无法用真实 LLM 验证影响程度，只有文本级 E1）。
2. D4 的归一缺口只做了手工构造验证；真实项目里指针均由 `task.py` 写入，属理论可达。
3. 未跑真实 DSH 进程（headless + 真 LLM）；本轮结论是"模型收到的文本"级别，不是指令遵循级别。
4. `trellis_wait` 结算、compaction 重投递、web 设置页 UI 仍为未验证边界（与上一轮相同）。
5. 客户端 bundle 未重建：本次未触碰 `src/client/**`，`test/client-bundle.test.js` 通过，
   故 `lib/client.js` 无需重打包。

## 8. D1 处置（主代理，check 轮之后）

- **决定：回退 inline 选择。** 复核给出的契约证据（`workflow.md:223-228/257-261`
  "Codex-only opt-in"、carrier `resolve_breadcrumb_key` 的 `platform == "codex"`、
  `docs/workflows/.../patch-inject-workflow-state.py` 同判定）优先于此前"P2-6 纳入修复"
  的假设；继续在 DSH 选 inline 会让每轮提示与 dispatch-guard / sub-agent push /
  `trellis_wait` 互相矛盾。
- 代码：`lib/workflow.js` 已删除 `breadcrumbStatus` / `codexDispatchMode` 及 inline 选择，
  并在原处留下契约注释；`test/workflow.test.js` 的 inline 用例改为断言 DSH 取基础块。
- 实测：本会话指针解析为 `in_progress`，body 1635 字节（回退前为 `in_progress-inline`，
  325 字节）。
- 同轮另行修复 D4（指针归一 + 目录判定）与 D5（doctor 显示实际 workflow 文件）；
  D6/D7 保留为已记录的低风险差异。
- 回归：`node --test "test/*.test.js"` → **291 tests / 287 pass / 0 fail / 4 skip**。

## 9. 后续：DSH 自己的内联模式（0.3.9）

D1 的处置不是“只能派发”。用户确认需要主会话常驻内联后，0.3.9 增加了
`dsh.dispatch_mode`（`.trellis/config.yaml`，默认 `auto`）：

- `inline` → 选中平台无关的 `planning-inline` / `in_progress-inline` 块，并追加
  `<dsh-mode>` 说明（不派发 `trellis-agent-*`、无需 `trellis_wait`、用
  `trellis-check` 技能验证）；
- `auto` / 非法值 / 无 inline 块 → 基础块（与 0.3.8 行为一致）；
- `codex.dispatch_mode` 仍被 DSH 忽略。

验证：295 tests / 291 pass / 0 fail / 4 skip；headless 真实会话收到
`Trellis workflow state: in_progress-inline`（788 字节，含 banner）。详见
`dsh-plugins/dsh-trellis/docs/validation-0.3.9-local.md`。
