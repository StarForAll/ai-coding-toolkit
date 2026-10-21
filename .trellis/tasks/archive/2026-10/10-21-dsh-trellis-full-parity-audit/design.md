# Design — dsh-trellis 全链路对等性审计

## 1. 审计架构

### 1.1 环境分层

| 层 | 路径 | 用途 |
| --- | --- | --- |
| 审计任务 | `.trellis/tasks/10-21-dsh-trellis-full-parity-audit/` | 本轮唯一 Trellis 任务；PRD/设计/执行计划、findings、report |
| 临时目标项目 | `/tmp/trellis-dsh-parity-<ts>/` | 唯一 `trellis init --dsh --codex` 项目；所有状态/spec/子代理场景 |
| 隔离 DSH_HOME | `/tmp/dsh-parity-home-<ts>/` | `trellis-audit`（装插件）与 `trellis-control`（不装插件）两个 profile；不触碰用户 profile |
| mock LLM | `/tmp/trellis-dsh-parity-<ts>/harness/mock-llm.mjs` | 记录模型实际收到的 messages/tools；脚本化 root/child 响应 |
| 证据 | 任务目录 `findings/` + `/tmp/.../scenarios/` | E1 原始请求/事件/stderr；报告引用路径 |

### 1.2 隔离 headless profile

- 复制 shipped headless 模板结构：`package.json` bundles `@deepseek-ai/dsh-base`、`@deepseek-ai/dsh-headless`；`cordis.patch.yml` 配置 mock provider 并 `insert` 插件条目。
- `node_modules/dsh-trellis` 软链到 `dsh-plugins/dsh-trellis`，使安装态与源码一致；另建 `trellis-control` 不插插件。
- 每次 `dsh --profile trellis-audit --json ...` 都带 `DSH_HOME`、`MOCK_LLM_KEY=dummy`；mock 服务固定在 `/v1` 端口，按 plan 返回 SSE。
- 用 `--session-id` 续接同一 DSH session 做状态序列；独立场景可新会话。

### 1.3 mock LLM 协议

沿用已验证的脚本化协议：

- `plan.root[]`：root 每一步的 `content` 或 `tool_calls`；步骤按请求顺序消费。
- `plan.child`：子代理的固定回复；用 `CHILD-MARKER` 识别 child 请求。
- 辅助请求（无 tools，通常是标题）返回 `TITLE`，不推进 root 步骤。
- `dynamic: "wait_last_child"`：从最近工具结果文本 `started subagent <id>` 提取 child id 并调用 `trellis_wait`。
- 每个请求追加写入 `requests.jsonl`，包含完整 body；用 jq/node 断言，而不是信任模型自述。

## 2. 场景矩阵

### 2.1 安装态与静态对齐（R1/R6）

| ID | 场景 | 观测 |
| --- | --- | --- |
| S0 | profile 安装来源、版本、host/client/patch 哈希 | 与源码一致；peer/engines 覆盖 0.2.1-rc.2 |
| S0b | 插件测试基线 | `pnpm test` 计数、失败项 |
| S0c | DSH 类型/服务对齐 | 逐项核对插件使用的 API 在当前 DSH 中存在且形状一致（file:line） |

### 2.2 工作流状态（R2）

| ID | 场景 | 准备 | 期望 |
| --- | --- | --- | --- |
| S1 | no_task 首轮 | 全新项目、无任务 | breadcrumb(no_task)+bootstrap 一次；config 自动补 inline；含 `<dsh-mode>` |
| S2 | no_task 次轮 | 同一 session 再发 | 不再 bootstrap；breadcrumb 去重（无状态变化） |
| S3 | planning | `task.py create`/指针指向 planning | `planning-inline` + task 行 |
| S4 | in_progress | `task.py start --allow-empty-context` | `in_progress-inline` |
| S5 | completed | 手改 `task.json.status=completed` 保留指针 | `completed` 块 + 横幅，不误报 no_task |
| S6 | custom | status=`blocked` 或团队自定义 | 原值匹配；无块走 fallback，不误报 no_task |
| S7 | stale | 删除任务目录保留指针 | `stale`；不借用其它会话 |
| S8 | task_error | task.json 损坏/空 status | `task_error` + 修复提示 |
| S9 | workflow 变体 | task pin / `.developer` / `default_workflow` 三层 | 逐层生效；缺文件回落 |
| S10 | skip 关键字 | 项目 `prompt_injection.skip_keyword: skip-trellis` | 该轮 0 注入；插件级 `no-trellis` 兜底 |
| S11 | inline 自定义变体 | 变体只有基础块、无 `*-inline` | 基础块 + 横幅仍在 |
| S12 | auto 对照 | `dsh.dispatch_mode: auto` | 基础块、无横幅；角色派发放行 |
| S13 | 自动引导边界 | 显式 auto / 只读 config / 无 config | 不改显式值；不创建缺失文件；失败回落 auto 且只警告一次 |
| S14 | 非 Trellis 目录 | 无 `.trellis`/`.git` 的目录 | 0 注入 |

### 2.3 spec 注入（R3）

| ID | 场景 | 观测 |
| --- | --- | --- |
| S15 | deny-once | 首次 `write src/a.ts` → deny + `<spec-context>`；重试成功；分片文件存在 |
| S16 | ticket | 窗口内另一次 touch 静默；把分片 `ts` 推到窗口外 → ticket 经下一次请求出现 |
| S17 | disabled | `spec_injection.enabled: false` → 不 deny、不注入 |
| S18 | tools 配置 | 大写 `Edit/Write` 可匹配；`Read` 加入后只 post-execute、不阻断 |
| S19 | 损坏分片 | 写入坏 JSON → 重新 full，不静默放行 |
| S20 | Codex 同输入 | 真实 `.codex/hooks/inject-spec-context.py` 的 deny/ticket 文案与插件对照 |

### 2.4 子代理、等待、守卫（R4）

| ID | 场景 | 观测 |
| --- | --- | --- |
| S21 | implement push | child 首请求含角色契约 + curated context + prd；无 no_task 面包屑 |
| S22 | check push | 读取 `check.jsonl`，不读 implement 清单 |
| S23 | research push | 读取 `research.jsonl`/artifacts；与 Codex research 的 spec-tree context 对照 |
| S24 | generic child | 无 `trellis-agent-*` → 无 push、无面包屑 |
| S25 | 无 role skill | 删除 `.dsh/skills/trellis-agent-implement` → 至少路径提示 |
| S26 | 无任务 implement/check | dispatch 被 deny，child 不启动 |
| S27 | research 无任务 | 放行 + 输出位置提醒 |
| S28 | inline 守卫 | inline 下 implement/check deny、research 放行 |
| S29 | 逃生口 | `dsh.inline_allow_dispatch: true` → 放行 |
| S30 | wait 成功 | child 运行中调用 `trellis_wait` → completed |
| S31 | wait 先结束再等待 | root 先做一步独立工作，child 已结束但仍可能驻留，再 wait → 不挂死；返回 settled/inactive 或明确失败 |
| S32 | wait 失败/中止 | child stopReason=error/aborted → outcome 不误报 completed |
| S33 | 并发会话 | 两个 DSH session 各自任务指针，互不串任务 |

### 2.5 命令、身份、Web 面（R5）

| ID | 场景 | 观测 |
| --- | --- | --- |
| S34 | shell 身份 | bash 内 `DSH_SESSION_ID` / `DSH_TRELLIS_CONTEXT_ID` / `TRELLIS_CONTEXT_ID`；`task.py current --source` |
| S35 | status/finish/doctor | 真实 0.7.0-beta.4 项目：无任务/有任务输出、只读性、带参数拒绝 |
| S36 | Web 命令分发 | 当前 GUI 输入 `/trellis-doctor` 等；确认命令生命周期不进模型历史 |
| S37 | Web 设置页 | 设置 → Trellis 唯一入口、字段、开关；无重复 section |
| S38 | HTTP 路由 | `/dsh-trellis/conflicts` 200/checked；`/dsh-trellis/version-check` 的合法/非法请求 |
| S39 | 无插件对照 | control profile：无面包屑/bootstrap/spec/push/guard/wait，仅 Trellis 原生能力 |

### 2.6 Trellis 机制（R6）

| ID | 场景 | 观测 |
| --- | --- | --- |
| S40 | init 产物 | `.dsh/skills`、`.agents/skills`、`.codex`、AGENTS.md、`.trellis/.version` |
| S41 | `trellis update` | 自动补的 `dsh.dispatch_mode` 是否保留；config 是否被覆盖 |
| S42 | `task.py` 契约 | `create/start/current --json/finish/archive` 与插件的解析一致；start 的 jsonl 门禁 |
| S43 | Codex 同输入 | workflow-state 正文、bootstrap、research/implement context 逐项对照 |

## 3. 证据与判定

- **E1**：真实 DSH headless/web 进程、真实工具结果、真实文件/HTTP、真实 `task.py`。
- **E2**：源码/类型/契约静态核对（标注 file:line）。
- **E3**：插件单测、文档声明（仅作基线，不单独支撑结论）。
- 每个场景保存：
  - `requests.jsonl`（模型实际收到的完整 messages/tools）
  - `events.jsonl`（DSH 运行事件）
  - `stderr.log`
  - 关键文件快照/哈希（config、task.json、spec 分片）
  - 断言脚本输出 `assertions.txt`
- 判定词汇固定：`等价`、`DSH 增强`、`有意差异`、`退化/缺漏`、`未验证`。

## 4. 关键风险与处理

| 风险 | 处理 |
| --- | --- |
| mock LLM 与真实模型行为不同 | 只结论“模型收到什么”，不推断长期遵循率；真实遵循率列为未验证 |
| headless 与 Web 事件形状不同 | 核心消息链用 headless；命令/设置/压缩用当前 Web；差异标注 |
| `trellis_wait` 挂死 | 每个 wait 场景加 `timeout`；超时即作为 E1 缺陷证据，不重试掩盖 |
| 自动写 config 污染临时项目 | 每次场景前备份 config，场景后对比；临时项目可整体删除 |
| 当前 Web 会话被命令污染 | 只用只读命令；不执行 finish-work/归档；必要时新建会话 |
| 用户 profile 被改动 | 只用隔离 `DSH_HOME`；当前 Web 仅只读 HTTP/设置页 |
| 端口冲突 | mock 端口从 18941 起探测空闲；DSH web 用现有 3080 |

## 5. 交付物

- `findings/*.md`：按能力面归档的原始观察与断言。
- `report.md`：结论矩阵、P0–P3 问题清单、修复建议、未验证边界、最终三问回答。
- `check-report.md`：本轮自查（证据完整性、无源码改动、临时环境清理）。
- 可选：`findings/harness/` 保存可复现脚本（mock、run-scenario、codex compare）。

## 6. 回滚

- 删除 `/tmp/trellis-dsh-parity-*`、`/tmp/dsh-parity-home-*`；杀掉 mock/临时 DSH 进程。
- 本仓库只新增任务目录；若后续修复，单独提交并由用户确认。

---

## 7. 修复轮设计（2026-10-21）

### 7.1 配置解析（P2-4）

在 `lib/trellis-config.js` 增加 flow mapping 解析：

- 识别 `section: { key: value, ... }` 单行映射；
- 值与 flow list 复用现有 `unquote` / `parseFlowSequence`；
- `parseSection` 对 flow mapping 返回同一 `Map`，使 `dshDispatchMode` / `dshInlineDispatchAllowed` / `specInjectionSettings` / `promptInjectionSkipKeyword` / `contextInjectionLimits` 自动受益；
- 不迁移、不重写 flow-style；`project-defaults` 仍把 flow-style 视为用户权威。

### 7.2 workflow 状态（P2-3 / P3-1）

- 在 `resolveTrellisState` 中区分：
  - 找不到项目根 → null（非 Trellis，静默）；
  - 找到根但 workflow 缺失/不可读/零块 → 返回降级 state（status 取 active task 或 no_task，body=FALLBACK_BREADCRUMB）；
- 降级 state 仍走 inline 横幅与 digest；
- 新增 `normalizeDshCommandRefs(body)`：把注入正文中的 `/trellis:finish-work`、`/trellis:start`、`/trellis:continue` 映射为 DSH 技能名；`status`/`finish`/`doctor` 映射为插件命令。未知引用保持原样，避免猜测。
- digest 基于归一后的 body，避免同一状态重复注入。

### 7.3 角色契约推送（P3-2）

- 新增 `lib/role-contract.js`：`stripPullOnlyContext(body, role)`，只改 push 副本；
- implement/check：移除 `## Required: Load Trellis Context First` 到下一个 `## ` 的段落，移除 `dsh does not auto-inject...` 句；
- research：将 `### Step 1: Resolve Current Task` 替换为 `### Step 1: Prepare Output Directory`，保留 research 目录要求；
- 找不到匹配时保留原文（旧版兼容），不强行裁剪；
- `subagentContextMessage` 的前置说明改为不引用已被删除的章节。

### 7.4 research 上下文（P2-1）

- `buildSubagentContext` 对 research 走独立分支：
  - 先注入 Codex 同款 spec 目录树 / `get_context.py --mode packages` / search tips；
  - 再按总预算可选注入 task artifacts；
  - 不再读取不存在的 `research.jsonl` 作为主上下文（保留兼容读取，但空清单不再作为“主要上下文”提示）。
- implement/check 路径不变。

### 7.5 版本检查（P3-7）

- `fetchText` 捕获 AbortError → `UpstreamError("GitHub request timed out after ...", 504)`；
- `createVersionCheckHandler` 的 plugin 分支用 `Promise.allSettled`，返回 `{ok:true, commit, release, errors}` 局部结果；
- npm 分支保持单请求；超时同样友好化；
- 客户端 `runVersionCheck` 接受 partial：有 commit 正常；只有 release/无 commit 时显示 partial 行，不抛原始 abort；
- `VersionMonitor` 渲染 partial 提示与重试建议；新增 locale 文案；
- 增加测试：挂起 fetch + 短 timeout → 200 partial，UI result 含友好文案。

### 7.6 project-defaults / wait（P3-3 / P3-6）

- `createDshDefaultsEnsurer` 缓存每个 root 的写入失败结果，后续 step 跳过写尝试；保留一次 `logger.warn`；
- `trellis_wait` 新增可选 `timeout_ms`（0/缺省=不超时）；超时返回 `state:"timeout", outcome:"unknown"`，清理监听器，不抛原始 abort；
- 晚到 inactive 仍返回 unknown，文案明确“无法证明成功”。

### 7.7 版本与文档

- `package.json` / `README` / `LOCAL_CHANGES` / `docs/validation-0.1.1-local.md` 对齐 0.1.1；
- `pnpm run build:client` 重建 `lib/client.js` 与 map；
- 更新 `.trellis/spec/platforms/dsh-workflow-behavior.md` 的安装形态描述（git 依赖快照，而非软链），并在验证记录中说明。
