# Report — dsh-trellis 对标 Codex 的全面验证（已确认并修复）

> 状态：验证完成 → 用户已确认修复范围（P0 + P1 + P2，P2-6/P3-7 纳入）→ 已在
> 本任务内完成修复，版本 0.3.8，未提交。
> 证据等级：E1 = 本次实际运行；E2 = 静态推断；E3 = 文档/测试声明。结论只用 E1，
> E2/E3 均显式标注。

## 0. 一句话结论

探针 A **真实存在且可复现**：插件用真实 `.trellis/workflow.md` 解析出的 `no_task`
正文是 4,605 字符 / 66 行（正确值 421 字符 / 3 行），注入模型时被 4096 字节预算截成
4,063 字符，真正的"先分类、先征得建任务同意"指引完全丢失。同类解析/映射问题另有 4 项；
spec 注入、子代理推送、dispatch 守卫、命令与版本监控等其余能力面实测**与 Codex 等价或
更强**。

## 1. 验证方式（全部 E1）

- 真实装载链：`~/.dsh/profiles/web` → 符号链接 → 本仓库 `dsh-plugins/dsh-trellis` 0.3.7；
  `dsh --profile web --dump-config` 确认条目。
- 实时会话取证：当前 web 会话 transcript 中的 `source.kind=dsh-trellis` 消息。
- 全新项目：`/tmp/trellis-e2e`（`trellis init` 0.7.0-beta.4）。
- 独立 DSH profile + 本地 mock LLM：`/tmp/dsh-audit-*`、`~/.dsh/profiles/trellis-audit`，
  抓取模型实际收到的 `messages`（不依赖模型自述）。
- 对照基线：`.codex/hooks/*.py` 与 `.trellis/scripts/common/*`（Codex/Claude 实际使用的解析器）。
- 单元测试仅作基线：262 passed / 4 skipped / 0 failed（E1，不作为结论依据）。

## 2. 确认存在的问题

### P0-1 `no_task` 跨注释匹配 + 截断丢失真实指引（探针 A，确认）

- 根因：`lib/workflow.js:14-15` 的 `STATUS_RE` 开标签后无换行约束；`workflow.md:123`
  注释中的 `[workflow-state:no_task]` 被当成块首，body 一直吃到 189 行闭合标签。
- 实测：插件 4,605 字符 / 66 行；Codex/Claude hook 421 字符 / 3 行；其余 8 个状态两平台
  完全一致（该次匹配恰好吞掉了注释中其它标签的"提及"）。
- 截断：`maxBytes` 默认 4096 → 模型收到 4,063 字符 / 4,096 字节，尾被切断（`…and u`）；
  真实指引不可见。全新项目同样复现（4,091 字符 / 60 行，最后一行被切断）。
- 端到端：headless 真实会话 + mock LLM 的请求 messages 中确认同一文本。
- 影响面：所有使用 trellis 0.7 `workflow.md` 模板的项目；仅 `no_task` 状态受影响。
- 证据：`findings/state-breadcrumb.md` §1、`findings/e2e-session.md` §1–2。

### P1-2 状态映射丢状态：`completed` / 任意自定义状态 → `no_task`

`mapStatus` 只映射 planning / in_progress / task_error，其余一律 no_task。实测
`task.json.status = "completed"` 时插件报 `no_task` 并额外发 bootstrap（提示创建任务），
Codex 发 `[workflow-state:completed]` 正文；`blocked` 时 Codex 至少给出通用降级行。
证据：`findings/state-breadcrumb.md` §2。

### P1-3 指针失效（stale）不可达：被当成 `task_error`

Trellis 解析器对"指针存在但任务目录已删除"返回 `stale=True`，插件返回 `task_error`；
仓库 `workflow.md` 明确定义了 `[workflow-state:stale]`（459 字符）却永远读不到。
且因 digest 去重，stale 切换时**不会产生任何新提示**（E2E 实测）。
证据：`findings/state-breadcrumb.md` §2、`findings/e2e-session.md` §2。

### P1-4 忽略项目级工作流选择（per-task / personal / team）

Codex hook 通过 `common.workflow_selection` 依次支持：任务 `task.json.workflow` →
`.developer workflow=` → `config.yaml default_workflow` → 全局 `workflow.md`；
插件硬编码只读 `.trellis/workflow.md`。实测任务级变体 `alt.md` 被 Codex 选中、被插件忽略。
证据：`findings/state-breadcrumb.md` §3。

### P2-5 忽略项目级 `prompt_injection.skip_keyword`

项目 `.trellis/config.yaml` 设 `skip_keyword: skip-trellis` 时：Codex hook 正确跳过、
无输出；插件仍注入 breadcrumb + bootstrap（只用自身 profile 配置的 `no-trellis`）。
证据：`findings/state-breadcrumb.md` §3。

### P2-6 `*-inline` 状态不可达（影响待定）

插件不读 `codex.dispatch_mode`，`planning-inline` / `in_progress-inline` 永不产生。若
DSH 不需要 inline 模式，这是有意的平台差异；若项目把 `dispatch_mode: inline` 作为团队
契约，则两平台提示不同。需要用户判断是否算缺陷。

### P3-7 子代理首轮提示自相矛盾（E2，需行为级复核）

推送消息声明"上下文已准备"，但内联的 role skill 正文仍写 "This platform does NOT
auto-inject task context via hook … you MUST load context yourself"，并包含"两者都失败
就问用户"。可能诱导子代理重复 `task.py current`（无指针子代理会拿到空结果）。
未构造行为级证据，建议修复时一并评估。

## 3. 验证通过 / 与 Codex 等价的部分

| 能力面 | 结论 | 证据 |
| --- | --- | --- |
| spec 配置解析（引号、注释、flow list、非法值、负值） | 与 Codex hook 数值一致；默认 tools 有意收敛为 edit/write | spec findings §1 |
| deny-once → retry 放行 | E2E 实测，deny 文案与 Codex hook 逐字一致 | e2e §3 |
| spec ticket / 状态分片持久化 | post-execute 投递实测；`.trellis/.runtime/spec-inject/` 生成 | e2e §3 |
| 子代理上下文推送 | E2E：role skill 正文 + prd 内联，首轮一次 | e2e §4 |
| dispatch 守卫 fail-closed | E2E：无任务 dispatch 被拒，子代理未启动 | e2e §5 |
| 原生会话身份 `DSH_TRELLIS_CONTEXT_ID` | E2E：工具 shell 内 `dsh_<session-id>` | e2e §6 |
| bootstrap 去重、fork 判定、子代理静默 | E1 | state §4 |
| 命令 / doctor / 冲突检测 / 版本监控路由 | 真实执行与真实 HTTP 200 | command findings §1–3 |
| 插件自带单测 | 262 pass / 0 fail | 基线 |

## 4. 无法验证（明确保留）

- web 设置页 UI 的浏览器级交互（未做 browser automation）。
- `trellis_wait` 的真实等待/超时/结算语义（仅注册与单测）。
- compaction 后的 projection 重投递、spec 多命中预算降级、二进制 spec 截断。
- 真实 LLM 下的指令遵循效果（mock 只证明"模型收到什么"）。

## 5. 修复实施（0.3.8，用户确认后完成）

| 问题 | 修复 |
| --- | --- |
| P0-1 | `STATUS_RE` 增加"开标签必须在行尾"约束（与 Python hook 同语法） |
| P1-2 | 状态按原值匹配：`completed` / 自定义状态不再被改写成 `no_task`；无块时用通用降级行 |
| P1-3 | 指针指向已删除目录 → `stale`（有块用块，无块用通用降级行）；守卫与子代理 push 不再把 stale 当可读任务 |
| P1-4 | 实现 workflow 选择：任务 pin → `.developer` → `config.yaml default_workflow` → 全局 |
| P2-5 | 项目 `prompt_injection.skip_keyword` 优先，插件 `skipKeyword` 兜底 |
| P2-6 | 初版 inline 选择被 check 回退（Codex-only）；随后按用户选择新增 **`dsh.dispatch_mode`**（`auto`/`inline`）：`inline` 复用平台无关的 `*-inline` 阶段块并追加 `<dsh-mode>` DSH 说明，DSH 内联成为受支持的项目级模式 |
| P3-7 | 首步 push 明确声明角色 skill 的"先加载上下文"段落已满足，禁止重复 `task.py current` / 追问任务 |

验证：check 轮后 **291 tests / 287 pass / 0 fail / 4 skip**；真实 workflow.md 的
`no_task` 从 4,605 字符/66 行回到 421 字符/3 行（breadcrumb 491 字节）；全新项目 headless
会话的模型请求确认完整指引；项目 skip 关键字下注入为 0；任务级 workflow 变体生效；
本会话指针解析为 `in_progress`（1635 字节），未受 Codex-only inline 影响。
详见 `docs/validation-0.3.8-local.md` 与 `check-report.md`。

### `trellis-check` 复核结论（PASS WITH FIXES）

- D1（高影响）：inline 选择与 Trellis 契约冲突 → 已回退，DSH 保持基础块。
- D2：空/空白正文块被当模板 → 已修（丢弃空块，与 carrier `if body:` 一致）。
- D3：skip 关键字边界与 carrier 不一致（4/13 组相反）→ 已修（Unicode + 连字符边界）。
- D4：指针 ref 未归一 → 已修（`tasks/<slug>`、`./`、绝对路径、目录判定）。
- D5：doctor 不显示实际选中的 workflow 文件 → 已修（新增 `Workflow file:` 行）。
- D6/D7：零块静默与琐碎解析差异，记录为既有/低风险设计，未改。

### 后续：DSH 内联模式（0.3.9）

用户确认需要“DSH 主会话一直自己做”，已新增项目级 `dsh.dispatch_mode`（默认 `auto`）：
`inline` 时 breadcrumb 变为 `planning-inline` / `in_progress-inline`，并追加
`<dsh-mode>` 说明（不派发角色子代理、无需 `trellis_wait`、用 `trellis-check` 技能）。
本仓库 `.trellis/config.yaml` 已固定 `inline`；doctor 显示当前模式。
验证：295 tests / 291 pass / 0 fail / 4 skip；真实 headless 会话收到
`in_progress-inline`（788 字节，含 banner）。详见 `dsh-plugins/dsh-trellis/docs/validation-0.3.9-local.md`。

## 6. 后续决定

- 修复只落在本仓库本地改版（`dsh-plugins/dsh-trellis`），未提交、未同步上游。
- 是否需要向上游 `SajoLuo/dsh-trellis` 回馈同一批修复，需用户另行决定。
