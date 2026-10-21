# Report — dsh-trellis 全链路对等性审计与 DSH 缺口验证

> 唯一任务：`.trellis/tasks/10-21-dsh-trellis-full-parity-audit`
> 唯一临时项目：`/tmp/trellis-dsh-parity-20261021/project`
> 环境：DSH `0.2.1-rc.2` / Trellis `0.7.0-beta.4` / Codex CLI `0.163.0` / 插件 `0.1.0`
> 证据等级：E1 = 本轮真实进程、真实工具结果、真实文件/HTTP；E2 = 源码/类型静态核对；E3 = 文档/单测声明。结论只以 E1 为主，E2/E3 显式标注。
> 审计轮**未修改** `dsh-plugins/dsh-trellis`、Trellis 上游、DSH 安装或用户 profile；修复轮结果见 §9/§10，代码由用户提交为 `5baa8d7` 与 `bca5a15`。

## 0. 一句话结论

主链路**基本达到 Codex 使用 Trellis 的同等效果**：7 类状态、3 层 workflow 变体、skip、inline/auto、spec deny-once/ticket、implement/check 子代理上下文、dispatch guard、`trellis_wait`、会话身份均实测通过；`in_progress` 正文与 Codex hook **逐字节相同**。  
但**不能宣称完全一致**：research 子代理上下文与 Codex 不等价（P2），workflow 零状态块时插件完全静默（P2），flow-style `dsh.dispatch_mode` 被忽略并绕过 inline 守卫（P2），inline 默认与 `task.py start` 的 jsonl 门禁存在摩擦（P2）。无 P0/P1。

## 1. 验证方式

- 真实安装态核对：web profile 的 `lib/index.js`、`lib/client.js`、`cordis.patch.yml` 与源码 sha256 一致；`pnpm test` = 321 tests / 317 pass / 0 fail / 4 skip。
- 隔离环境：`DSH_HOME=/tmp/dsh-parity-home-20261021`，两个 headless profile：
  - `trellis-audit`：装插件 + mock LLM；
  - `trellis-control`：同配置不装插件，作为 DSH 原生对照。
- 临时项目：`trellis init --dsh --codex -y -u xzc`；所有状态、spec、子代理场景都在此项目。
- mock LLM：脚本化 root/child 响应，记录模型**实际收到的完整 messages/tools**；不依赖模型自述。
- Codex 对照：用真实 `.codex/hooks/*.py` + 真实 payload（干净环境，去掉外层 DSH_*），逐字对比；未运行 `codex exec`（hooks 审批/信任门未在本轮重新走）。
- 证据：`findings/01..07`，原始文件在 `/tmp/trellis-dsh-parity-20261021/scenarios/`。

## 2. 能力对照矩阵

| 能力面 | Codex 实际行为 | DSH + dsh-trellis（本轮） | 判定 |
| --- | --- | --- | --- |
| no_task bootstrap | 每个无任务轮次都附 `<trellis-bootstrap>` | 新根会话一次，子代理不注入；压缩后才可能再提示 | 有意差异（降噪） |
| 每轮 workflow-state | UserPromptSubmit hook | `agent/pre-step` 注入；状态变化即更新 | 等价 |
| 状态覆盖 | no_task/planning/in_progress/completed/自定义/stale/task_error | 全部可达；`completed`/自定义不被改写；stale 独立 | 等价（DSH 更准确） |
| workflow 变体 | task → `.developer` → `default_workflow` → 全局 | 同优先级，三层实测 | 等价 |
| skip 关键字 | 项目 `prompt_injection.skip_keyword` | 项目优先、插件级兜底；边界一致 | 等价 |
| inline/auto | `codex.dispatch_mode` + `<codex-mode>` | `dsh.dispatch_mode` + `<dsh-mode>`；块缺失仍出横幅 | 等价（平台差异） |
| spec deny-once | PreToolUse(Edit/Write) deny + additionalContext | tools/pre-execute deny + post-execute ticket | 等价 |
| spec 工具名 | 只认大写 Edit/Write/Read | 大小写规范化；Read 只 post-execute | 有意差异 |
| implement/check push | SubagentStart + agent TOML | 子代理首步 push：角色 skill 正文 + curated context | 等价（插件多角色契约） |
| research push | spec 目录树 + Search Tips | `research.jsonl` 空提示 + prd/design/implement | **不等价（P2）** |
| generic 子代理 | 静默 | 静默 | 等价 |
| dispatch guard | 无 | 无任务 fail-closed；inline 拒绝 implement/check；research 放行 | DSH 增强 |
| `trellis_wait` | 平台原生 wait | 事件驱动；成功/失败/中止 fail-closed；晚到 unknown | DSH 增强（有边界） |
| 会话身份 | 平台 session | `DSH_TRELLIS_CONTEXT_ID=dsh_<session>`；并发不串 | 等价 |
| 命令 | skills/命令 | `/trellis-status`、`/trellis-finish`、`/trellis-doctor` | 通过（handler 级） |
| 开箱可用性 | 需用户级 hooks + 项目审批/信任 | 安装即生效 | DSH 明显更好 |
| Web 设置/真实 slash/压缩 | — | 认证限制，未验证 | 未验证 |

## 3. 关键实测结果

### 3.1 状态注入

- `no_task`：421 字符正文 + banner + bootstrap 一次；第二轮无重复。
- `planning`/`in_progress`：`*-inline` + 任务行；`completed`/`blocked`/`stale`/`task_error` 均正确。
- 三层变体：task pin / `.developer` / `default_workflow` 全部生效。
- skip：项目级命中时注入数不变；插件级 `no-trellis` 兜底为 0。
- 自动引导：首轮写一次 `dsh.dispatch_mode: inline`；第二轮 hash 不变；显式 `auto` 前后 hash 不变。
- 只读项目：config 不被修改，回落 auto 语义。

### 3.2 spec

- 首次 `write`：deny reason 含 `RETRY_NOTICE + <spec-context>`；重试成功；分片 `mode=full`。
- 窗口内静默；`ts` 推旧后下一次请求出现 `<spec-ticket>`。
- 禁用、大写工具名、Read opt-in、损坏分片回退均通过。
- Codex 同输入：`deny` + 203 字符 `<spec-context>`，文本与插件一致。

### 3.3 子代理

- implement：5498 字符，角色契约 + spec + prd/design/implement；check：5362 字符。
- generic：无 push/无 breadcrumb/无 bootstrap。
- 删除 role skill：回退到路径提示，不静默。
- 无任务 implement/check：deny，child 0 启动；research：放行 + 输出位置提醒。
- inline：implement/check deny；`inline_allow_dispatch: true` 放行。
- wait：运行中 `completed`；失败 `failed (error)`；先结束再 wait 返回 `already-inactive/unknown`（未挂死）。
- 两个会话：A/B 任务指针互不串。

### 3.4 Codex 对照

- `in_progress` 正文：1635 字符，**逐字节相同**。
- `no_task` 正文：内容相同（仅抽取尾部换行差异）。
- spec：deny 文案与 payload 等价。
- implement curated context：一致；插件额外注入角色契约。
- research：Codex spec-tree vs 插件 task artifacts，**不等价**。
- bootstrap 频率：Codex 每轮 1 次，插件每会话 1 次（有意差异）。

## 4. 问题清单（摘要）

完整复现、file:line、建议见 `findings/07-issues.md`。

| 级别 | 问题 | 影响 |
| --- | --- | --- |
| P2-1 | research 子代理上下文与 Codex 不等价 | research 角色失去 spec 目录树/搜索提示，被无关 artifacts 占预算 |
| P2-2 | inline 默认 + `task.py start` jsonl 门禁 | 每个新 inline 任务第一次 start 失败，需自行发现 `--allow-empty-context` |
| P2-3 | workflow 零状态块/缺失时完全静默 | 损坏 workflow 不可见；Codex 有 generic 降级 |
| P2-4 | flow-style `dsh: {dispatch_mode: inline}` 被忽略 | inline 横幅缺失、inline 守卫被绕过 |
| P3-1 | inline 块仍写 `/trellis:finish-work` | 模型可能尝试不存在的命令形态 |
| P3-2 | 角色 skill 正文与“上下文已准备”声明矛盾 | 弱模型可能重复 `task.py current`/追问 |
| P3-3 | 只读项目每 step 重试写 config，警告不可见 | 无意义 IO/锁竞争；用户不知道失败 |
| P3-4 | README/spec 说软链，实际是 git 依赖快照 | 改源码不生效的认知偏差 |
| P3-5 | 默认 inline（用户确认不是问题） | 保留既定产品选择，不计入缺陷 |
| P3-6 | `trellis_wait` 晚到 unknown、无内建超时 | 模型可能误读；依赖 transcript/宿主取消 |
| P3-7 | 手动版本校验显示 `This operation was aborted` | 已修复：超时友好化 + 局部结果 + UI partial |

## 5. 是否补足 DSH 使用 Trellis 的不足

**是，且是质变**。无插件 control profile 实测：

- 0 个 `Trellis workflow state`；
- 0 个 `<trellis-bootstrap>`；
- 工具列表无 `trellis*`；
- spec 文件写入不被 deny；
- 子代理首步无 push。

插件把这些全部补上，并额外提供 fail-closed 派发守卫与事件驱动 wait。inline 默认是 DSH 侧的产品选择，不是 Codex 的默认，也不是 Trellis 官方 DSH 文档的默认叙事；需要用户确认。

## 6. 未验证边界

- 真实 Web 设置页 UI、真实 slash 命令分发、压缩/clear 后 bootstrap/spec 重注入：DSH Web 需要启动时打印的认证 URL；未把 token 带入命令行/日志。
- 真实第二个 Trellis 插件的桌面通知/横幅：未向用户 profile 安装第二插件。
- 真实模型对提示的长期遵循率：mock 只证明模型收到什么。
- `trellis_wait` 的父会话原生 settlement notice 唤醒时序、`send_message` 后续轮次、fork 子代理 push 去重。
- 多 spec 预算降级、超长/二进制 spec：单测覆盖，未做真实 E2E。
- 上游 0.1.13 的行为。

## 7. 变更与回滚

- 本仓库只新增本任务目录；`git status` 显示未跟踪的本任务目录与用户既有的 `docs/capability-inventory.md`、`dsh-plugins/plugin-create.md`，未改动其它文件。
- 临时环境可整体删除：

```bash
rm -rf /tmp/trellis-dsh-parity-20261021 /tmp/dsh-parity-home-20261021
pkill -f mock-llm.mjs
```

- 修复不在本轮范围；用户确认问题清单后另起任务执行。

## 8. 最终回答

1. **能否达到 Codex 使用 Trellis 的同等效果？**  
   核心主链路达到，`in_progress` 正文逐字节一致；但 research 子代理上下文不等价，且零块 workflow / flow-style 配置两个边界会静默失效。准确表述是“核心等价 + research 退化 + 两个边界缺陷”，不是“完全一致”。

2. **是否补足 DSH 使用 Trellis 的不足？**  
   是，且是质变；无插件对照确认了状态、spec、子代理、guard、wait 的缺口全部由插件补齐。inline 默认与 `task.py start` 的摩擦是补足过程中暴露的集成问题。

3. **是否还有其它缺漏/不足？**  
   有：4 个 P2、6 个 P3（P3-5 经用户确认撤销；P3-7 已修复）。没有 P0/P1，没有发现数据破坏、权限越权或不可恢复错误。修复已在 0.1.1 完成，见 `fix-report.md`。

---

## 9. 修复轮结果（0.1.1，2026-10-21）

用户确认 P3-5 默认 inline 为正常设计，撤销该问题；P3-7 重新定义为 UI 手动校验的 `This operation was aborted`。其余 P2/P3 已按机制修复，详见 [`fix-report.md`](fix-report.md)。

- 版本：`0.1.0` → `0.1.1`；client bundle 已重建。
- 单测：340 tests / 336 pass / 0 fail / 4 skip。
- 真实 DSH E2E：零块 fallback、普通 Git 静默、flow-style inline + 守卫、inline 启动提示、命令归一、research spec-tree、角色契约去拉取化、wait 超时均通过。
- 版本检查：真实 GitHub 200；10ms 挂起 feed 返回 partial，不再出现原始 abort。
- 当前 web profile 是 ssh git 依赖快照；运行中的 UI 需重装/更新并重启后才能看到 0.1.1 的 UI 变化。
- 插件代码由用户提交为 `5baa8d7` 与 `bca5a15`；任务目录本身未归档。

---

## 10. 安装态复验与 check 轮（2026-10-21）

- 已安装 `dsh-trellis@0.1.1`（web profile ssh git 依赖快照）；host/client/workflow/upstream/wait-tool/subagent/role-contract 哈希与源码一致。
- 第二次提交 `bca5a15` 已包含 check 轮改动；安装目录 mtime `22:58:53`，当前 Web 进程启动于 `22:58:59`，进程在安装之后，已加载新 bundle。
- 安装态 E2E：零块 fallback + 精确 inline 提示 + bootstrap；flow-style inline + 命令归一；inline 守卫拒绝 implement；research spec tree（无 PRD/空清单提示）；implement 契约无 `MUST load context yourself`；wait 10ms 超时返回 unknown；全部通过。
- 当前 DSH 进程的 `/dsh-trellis/version-check` 实测 200，返回 commit/release；耗时约 11s（Atom 超时后 REST 回退），无原始 abort。
- check 轮发现并修复 4 个细节：HTTP status 未传递导致 release 404 回退失效；wait 超时未覆盖目录查询；inline 提示未写仓库内 `task.py` 路径；缺失 workflow 与零块共用 fallback 文案。修后单测 `340 / 336 pass / 0 fail / 4 skip`。
- 仍未自动点击浏览器 UI 的“手动校验”按钮（DSH Web 认证 URL 未带入命令行）；但当前进程的 Host 路由、client bundle、partial 渲染代码均已验证/构建。
