# dsh-trellis 插件全链路对等性审计与 DSH 缺口验证

## Goal

在 **一个** 新建 Trellis 任务内，用一个 `/tmp` 临时 Trellis 项目对已安装的 `dsh-trellis`（源码 `dsh-plugins/dsh-trellis`）做全链路实测，回答三个问题：

1. 它能否达到 Codex 使用 Trellis 的同等效果；
2. 它是否补足了 DSH 原生使用 Trellis 的缺口，补足到什么程度；
3. 是否仍有其它缺漏、退化或未覆盖边界。

本轮只做验证并产出证据化问题清单；**任何修复都必须等用户确认后再执行**。

## Background / Confirmed Facts

- 已安装 DSH `0.2.1-rc.2`，web profile 中 `dsh-trellis@0.1.0` 已启用；已安装的 `lib/index.js`、`lib/client.js`、`cordis.patch.yml` 与 `dsh-plugins/dsh-trellis` 工作树对应文件哈希一致。
- Trellis CLI/模板版本为 `0.7.0-beta.4`；上游 DSH 适配为 class-2 pull-based，角色提示以 `.dsh/skills/trellis-agent-*` 交付，可选伴侣插件由本仓库维护。
- Codex CLI `0.163.0` 可用；本仓库 `.codex/hooks/*.py` 是 Codex 侧实际接线基线。
- 插件自带测试基线（本轮实跑）：`321 tests / 317 pass / 0 fail / 4 skip`。
- 前两个已归档审计任务分别覆盖过 0.3.8 修复与 0.3.9/0.3.10 安装态 E2E；本轮必须在**当前 0.1.0 + DSH 0.2.1-rc.2 + Trellis 0.7.0-beta.4** 上重新取证，不能复用旧结论。
- 当前 web GUI `http://127.0.0.1:3080` 的 `/dsh-trellis/conflicts` 实测返回 `200`、`status=checked`、无冲突。

## Requirements

### R1. 安装态与接线保真

- 核对 profile 安装来源、版本、host/client bundle/patch 与源码一致性。
- 核对插件声明的 peer/engines 是否覆盖当前 DSH，并确认实际加载（面包屑已出现在当前会话即一项证据）。
- 确认插件只在 Trellis 项目注入；非 Trellis 目录静默。

### R2. 工作流状态注入 E2E

- 新会话 bootstrap 行为与频率；子代理不注入 bootstrap。
- `no_task` / `planning` / `in_progress` / `completed` / 自定义状态 / `stale` / `task_error` 的注入正文与任务行。
- 工作流变体优先级：任务 pin → `.developer` → `default_workflow` → 全局。
- 项目 `prompt_injection.skip_keyword` 与插件级 skip 的回退关系。
- `dsh.dispatch_mode: inline` 的 `*-inline` 块选择、`<dsh-mode>` 横幅、全部状态覆盖；`auto` 的对照。
- 项目级 `dsh.dispatch_mode` 自动引导：只补缺失键、显式 `auto` 不被覆盖、不创建缺失 config、并发/只读降级。

### R3. 路径级 spec 注入 E2E

- `edit` / `write` 首次命中：deny-once，reason 含 spec 正文；重试放行。
- 已教过的 spec 在刷新窗口内保持静默；窗口外产生 ticket；ticket 经 post-execute 送达下一次请求。
- `spec_injection.enabled: false`、预算/工具名配置的实际效果；与 Codex hook 输出做同输入对照。
- 状态分片持久化与损坏/缺失时的安全回退。

### R4. 子代理上下文、等待与派发守卫 E2E

- `trellis-agent-implement` / `check` / `research` 子代理首步收到角色契约 + curated context；generic 子代理保持静默。
- 无 `Active task:` 时父会话指针回退；无角色 skill 时至少注入路径提示；无任务时不注入 `no_task` 面包屑。
- 有任务时 implement/check 派发放行；无任务时 fail-closed；research 无任务放行并提醒输出位置。
- `inline` 下 implement/check 派发被拒、research 放行、`inline_allow_dispatch: true` 逃生口生效。
- `trellis_wait` 的真实结算：成功、失败/中止、未知、冷 child、**等待调用前已结束但可能仍驻留的 child**。

### R5. 命令、身份与 Web 面

- `/trellis-status`、`/trellis-finish`、`/trellis-doctor` 的真实 Trellis 0.7.0-beta.4 项目输出；零输入/带参数行为；只读性。
- `DSH_SESSION_ID` / `DSH_TRELLIS_CONTEXT_ID` / `TRELLIS_CONTEXT_ID` 在真实 shell 中的取值与任务指针隔离；两个并发会话不串任务。
- Web 设置页“Trellis”入口与字段渲染；冲突路由、版本检查路由；当前安装态下无重复命令/工具/设置页。

### R6. 机制对齐与残余缺口

- 以 Trellis 0.7.0-beta.4 源码为准，核对插件对 workflow 选择、状态、spec、context injection、DSH 身份、`task.py current --json` 等契约的实现。
- 以 DSH 0.2.1-rc.2 类型/服务为准，核对插件使用的 `agent/pre-step`、`tools/pre-execute`、`tools/post-execute`、`subagent/end`、`session/event`、`workingDirectory`、`sessionProjections`、`shellEnv`、命令 API。
- 明确区分：与 Codex 等价、DSH 增强、平台差异（有意设计）、真实退化/缺漏、未验证项。

## Acceptance Criteria

- [ ] 全程只使用 **一个** 本轮新建的 Trellis 任务；临时验证项目位于 `/tmp`，不修改用户 `web`/`headless` profile。
- [ ] 建立一个隔离 `DSH_HOME`（headless 审计 profile + 无插件对照 profile + 本地 mock LLM），可重复运行；不依赖真实模型自述。
- [ ] 每类结论至少有 E1 证据（真实进程/真实工具结果/真实文件或 HTTP），并保存原始 `requests.jsonl`、`events.jsonl`、`stderr`、状态文件或哈希；E2/E3 证据显式标注。
- [ ] 覆盖 R2–R5 的场景矩阵，至少包含：bootstrap 一次、7 类状态、3 层 workflow 变体、skip 关键字、inline/auto、spec deny+retry+ticket、implement 子代理 push、research push、generic 静默、dispatch guard 三种角色、inline 守卫+逃生口、`trellis_wait` 成功与“先结束再等待”、shell 身份隔离、三个命令、Web 设置/路由。
- [ ] 与 Codex 的同输入对照至少覆盖：workflow-state 正文、spec deny/ticket 文案、子代理 context 组成；差异给出原因与影响。
- [ ] 与 DSH 原生（不装插件）对照，说明补足了哪些缺口；不能只拿 Codex 当基线。
- [ ] 结论矩阵逐项给出：能力面、Codex 行为、DSH+插件行为、判定（等价/增强/差异/退化/未验证）、证据位置。
- [ ] 问题清单按 P0–P3 分级，每项含：现象、复现、根因（file:line）、影响面、证据等级、建议方案与风险；**本轮不实施修复**。
- [ ] 最终报告明确回答“是否达到 Codex 同等效果”“是否补足 DSH 缺口”“是否仍有缺漏”；没有发现问题时也必须给出具体验证结果与覆盖边界。
- [ ] 临时环境可整体删除；交付前 `git status` 证明本任务只新增任务目录与必要的任务产物，未改插件源码或用户 profile。

## Out of Scope

- 本轮不修改 `dsh-plugins/dsh-trellis`、Trellis 上游、DSH 安装或用户 profile；修复另起执行并需用户确认。
- 不安装第二个 Trellis 插件到用户 profile；冲突检测以现有路由/单测/隔离环境验证，不制造真实插件冲突。
- 不验证与 Trellis 无关的 DSH 功能；不评估真实模型对提示的长期遵循率（mock 只证明模型收到什么）。
- 不承诺覆盖所有历史 DSH/Trellis 版本；以当前安装版本为准，兼容矩阵只在声明范围内抽查。

## Constraints

- 临时项目只用于验证；其 `.trellis` 任务不是本轮 Trellis 任务。
- 不把凭据写入日志/报告；不打印 `~/.codex/config.toml` 或 profile 中的密钥值。
- 不修改当前会话的活跃任务指针；Web 命令测试避免触发归档/清理。
- 所有后台进程（mock LLM、临时 DSH）在结束前清理。

## Open Questions

无阻塞项。若执行中发现需要修改用户 profile 或安装第二个插件才能验证的项，先停下向用户申请，不擅自扩大范围。

---

## 修复轮补充（用户 2026-10-21 确认）

用户确认：

- **P3-5（默认 inline）不是问题**：插件默认 inline 是既定产品选择，后续不再作为缺陷报告。
- **P3-7 重新定义**：实际问题是 UI 设置页点击“手动校验”后出现 `上游 fork This operation was aborted`。需要修复的是版本检查的超时/中断处理，而不是把“上游已到 0.1.13”当作缺陷。
- 其余 P2/P3 均真实存在，需在本任务内修复；要求从机制上修正，避免只在调用点打补丁。

### 修复范围

- P2-1：research 子代理上下文对齐 Codex 的 spec 目录树 + 搜索提示，同时保留任务上下文预算控制。
- P2-2：inline 默认下 `task.py start` 的 jsonl 门禁摩擦；在 DSH 模式横幅中给出 `--allow-empty-context` 指引。
- P2-3：Trellis 项目 workflow.md 零状态块/缺失时给出可见 generic 降级 + bootstrap，而不是完全静默。
- P2-4：支持 flow-style `dsh: {dispatch_mode: inline}`；同一解析器覆盖 `spec_injection` / `prompt_injection` / `context_injection` 的 flow-style。
- P3-1：注入正文中的 `/trellis:finish-work` 等 Codex 命令引用归一为 DSH 命令/技能形态。
- P3-2：推送的角色契约去除 pull-only 上下文加载段，避免与“上下文已准备”矛盾；保留 pull 路径的原始 skill。
- P3-3：只读项目缓存写入失败，避免每个 step 重复尝试；保留一次可见警告。
- P3-4：README/spec 的安装形态与真实 git 依赖快照一致。
- P3-6：`trellis_wait` 增加可选超时；晚到 unknown 保持 fail-closed 并明确文案。
- P3-7：版本检查 Host 侧把 AbortError 转为明确超时；commit/release feed 使用 allSettled 返回局部结果；UI 展示 partial，不再显示原始 `This operation was aborted`。

### 修复验收

- [ ] 上述各项有单元测试或 E2E 证据；旧行为不再复现。
- [ ] 不改变 pull 路径技能文件；只改 push 副本。
- [ ] 版本 bump 到 0.1.1（patch），client bundle 重建并提交。
- [ ] README/LOCAL_CHANGES/验证记录与行为一致。
- [ ] 不把默认 inline 当作缺陷，不改变其默认值。
