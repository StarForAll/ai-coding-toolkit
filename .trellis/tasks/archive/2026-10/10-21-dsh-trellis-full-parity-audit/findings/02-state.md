# 工作流状态注入 E2E

临时项目：`/tmp/trellis-dsh-parity-20261021/project`。隔离 profile：`trellis-audit`（装插件）与 `trellis-control`（不装）。所有场景使用 mock LLM，直接检查模型请求 `messages`。

## 结果矩阵

| ID | 状态/场景 | 观察 | 判定 | 证据 |
| --- | --- | --- | --- | --- |
| S1 | 新会话 no_task | breadcrumb(no_task) + bootstrap 各 1；正文 421 字符；含 `<dsh-mode>`；config 自动补 `dsh.dispatch_mode: inline` | 通过 | `smoke/requests.jsonl` |
| S2 | 同一会话第二轮 no_task | 新消息只有用户 prompt；bootstrap/breadcrumb 未重复 | 通过 | `s2-second/requests.jsonl` |
| S3 | planning | `planning-inline` + `Active task: .trellis/tasks/10-21-state-probe2` | 通过 | `s3-planning/requests.jsonl` |
| S4 | in_progress | `in_progress-inline` + 任务行 | 通过 | `s4-inprogress/requests.jsonl` |
| S5 | completed | `completed` 块 + 任务行，不误报 no_task | 通过 | `s5-completed/requests.jsonl` |
| S6 | 自定义 `blocked` | 原值 `blocked`；无块走 `FALLBACK_BREADCRUMB`，不误报 no_task | 通过 | `s6-blocked/requests.jsonl` |
| S7 | stale | `stale` + 路径；无块走 fallback；不借用其它会话 | 通过 | `s7-stale/requests.jsonl` |
| S8 | task_error | `task_error` + 修复提示 | 通过 | `s8-task-error/requests.jsonl` |
| S9 | 任务 pin | `ALT-BODY-TASK-PIN` | 通过 | `s9a-task-pin/requests.jsonl` |
| S9 | `.developer` | `ALT-BODY-TASK-PIN` | 通过 | `s9b-developer/requests.jsonl` |
| S9 | `default_workflow` | `ALT-BODY-TASK-PIN` | 通过 | `s9c-default/requests.jsonl` |
| S10 | 项目 skip 关键字 | 注入数 before=8 / after=8 | 通过 | `s10-skip/requests.jsonl` |
| S10b | 插件级 `no-trellis` 兜底 | breadcrumbs=0，bootstraps=0 | 通过 | `s10b-plugin-skip/requests.jsonl` |
| S11 | inline 变体无 `*-inline` 块 | 基础块 `ALT-BODY-TASK-PIN` + `<dsh-mode>` 仍在 | 通过 | `s11-inline-missing-block/requests.jsonl` |
| S12 | 显式 auto | 基础块，无 `<dsh-mode>` | 通过 | `s12-auto/requests.jsonl` |
| S13 | 自动引导首轮 | config hash 变化一次；首轮含 banner；第二轮 hash 不变 | 通过 | `s13a-bootstrap/`、`s13b-bootstrap-second/` |
| S13c | 显式 auto | config hash 前后相同；无 banner | 通过 | `s13c-explicit-auto/` |
| S13d | 只读 `.trellis` | config 未被修改；breadcrumb 为 no_task、无 banner；无可见警告 | 通过（降级） | `s13d-readonly/` |
| S13e/S13f | flow-style `dsh: {dispatch_mode: inline}` | 无 banner；implement 派发放行 | **差异/缺陷** | `s13e-flow-inline/`、`s13f-flow-guard/` |
| S14 | 非 Trellis 目录 | breadcrumbs=0，bootstraps=0 | 通过 | `s14-non-trellis/requests.jsonl` |
| S14b | Trellis 目录、workflow.md 零状态块 | 插件 0 注入、0 bootstrap；Codex 输出 generic `Refer to workflow.md for current step.` | **差异/缺陷** | `s14b-broken-workflow/`、`s14b-codex-broken.json` |

## 关键观察

### 1. 正文与 Codex 等价

- `no_task` 正文与 Codex 完全一致（差异仅为抽取时尾部换行）。
- `in_progress` 正文与 Codex **逐字节相同（1635 字符）**。
- 任务行、状态名、fallback 文案均符合 Trellis 0.7.0-beta.4 的 tag 块。

### 2. inline 横幅与状态解耦

`planning`/`in_progress` 有/无 `*-inline` 块都输出 `<dsh-mode>`；`completed`/`blocked`/`stale`/`task_error` 也输出。与 README 的“全状态横幅”一致。

### 3. 自动引导只写一次

- 移除 `dsh:` 段后首轮写入；第二轮 `sha256` 不变。
- 显式 `auto` 前后 `sha256` 不变。
- 只读项目不创建/不修改 config，回落到 `auto` 语义。

### 4. flow-style 配置被静默忽略（缺陷）

`dsh: {dispatch_mode: inline}` 是合法 YAML，但：

- `lib/trellis-config.js:16` 的 `SECTION_RE` 只接受 `dsh:` 独占一行；
- `lib/workflow.js:133-140` 的 `dshDispatchMode()` 因此返回 `auto`；
- `lib/project-defaults.js:64-72` 又明确拒绝改写 flow-style，注释称“用户的 mapping 保持权威”。

结果：用户明确声明 inline，插件既不迁移也不读取，**inline 守卫被绕过**。`s13f-flow-guard/events.jsonl` 显示 implement 派发 `status=completed` 且 child 启动。

### 5. 零状态块/缺失 workflow 时静默（缺陷）

`lib/workflow.js:416-419` 在 `blocks.size === 0` 时返回 `null`；`lib/session-composer.js:112-113` 直接返回 `[]`，连 bootstrap 也不发。Codex 对同一输入输出：

```
<workflow-state>
Status: no_task
Refer to workflow.md for current step.
</workflow-state>
```

这违反 Trellis “缺块时给出可见 generic 行，让用户修 workflow.md”的契约；对损坏/裁剪掉全部 tag 的项目，DSH 侧完全静默，比 Codex 更隐蔽。

## 结论

状态注入主链路（状态覆盖、变体、skip、inline/auto、自动引导）通过；发现 2 个真实差异：flow-style 配置忽略、零块 workflow 静默。两者都不是 P0/P1。
