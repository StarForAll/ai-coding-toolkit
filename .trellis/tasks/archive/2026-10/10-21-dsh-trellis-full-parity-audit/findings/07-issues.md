# 问题清单与验证结论

> 本轮只验证，未修改任何插件源码或用户 profile。严重度按“对 Trellis 工作流正确性/可恢复性的影响”分级，不按代码行数。

## 0. 总览

- **P0：无**
- **P1：无**
- **P2：4 项**
  1. research 子代理上下文与 Codex 不等价；
  2. inline 默认与 `task.py start` 的 jsonl 门禁摩擦；
  3. workflow.md 零状态块/缺失时完全静默（Codex 有 generic 降级）；
  4. flow-style `dsh: {dispatch_mode: inline}` 被忽略，inline 守卫被绕过。
- **P3：6 项**
  1. inline 块仍写 `/trellis:finish-work`（Codex 命令形态）；
  2. 角色 skill 正文与“上下文已准备”前置声明自相矛盾；
  3. 只读项目上每个 step 重新尝试写 config，且 headless 无可见警告；
  4. README/spec 说 profile 是软链，实际是 ssh git 依赖快照；
  5. `trellis_wait` 晚到 unknown、无内建超时（fail-closed 边界）；
  6. 版本检查手动校验出现 `上游 fork This operation was aborted`（UI 超时原始错误）。

---

## P2-1 research 子代理上下文不等价

**现象**：Codex research 的 `Curated Context` 是 `.trellis/spec` 目录树 + `get_context.py --mode packages` + Search Tips；插件给 research 推的是 `research.jsonl`（通常不存在）的“no curated entries”提示 + prd/design/implement。

**证据**：

- `findings/04-subagent.md`；`s23-research-push/requests.jsonl`
- `s43-codex-research.txt`
- 代码：`dsh-plugins/dsh-trellis/lib/subagent-context.js:30-34`、`:367-435`
- Codex：`.codex/hooks/inject-subagent-context.py:763-806`

**影响**：research 角色失去项目结构/搜索定向上下文，同时被无关任务 artifacts 占用预算；对“全仓发现”类研究任务效果弱于 Codex。角色 skill 仍含搜索指引，所以不是完全不可用。

**建议**：research 分支改为 Codex 同款 spec-tree + search tips；如需保留任务 artifacts，放在其后并受总预算约束。是否保留 `research.jsonl` 需先确认 Trellis 0.7 是否仍使用它。

**风险**：低；只影响 research 推送内容，不影响 guard/主链路。

---

## P2-2 inline 默认与 `task.py start` 门禁摩擦

**现象**：插件在首次进入项目时自动写 `dsh.dispatch_mode: inline`；inline 工作流明确“skip jsonl curation”，但 Trellis 0.7.0-beta.4 的 `task.py start` 仍要求 `implement.jsonl`/`check.jsonl` 非空，否则拒绝。

**证据**：

- `findings/02-state.md` S1/S13；`findings/06-trellis-codex.md` §2
- `s42-task-contract.txt`：`start` 无 `--allow-empty-context` 时错误 `implement.jsonl and check.jsonl have no curated entries`
- 插件 banner：`lib/workflow.js:47-54` 只写 “skip jsonl curation”，没有 `--allow-empty-context`
- Trellis inline 块：临时项目 `.trellis/workflow.md:216-221`

**影响**：每个新 inline 任务第一次 `task.py start` 都会失败一次；模型需自行从错误信息推断 `--allow-empty-context`。这是插件默认 inline 放大出的 Trellis CLI 契约摩擦，实际会打断 Phase 1→2 转换。

**建议**：在 `<dsh-mode>` 横幅中直接给出 `task.py start <task> --allow-empty-context`（或插件提供等价的 start 辅助）；同时保留 README 说明。不要把 `--allow-empty-context` 设成默认——它只应跳过“有意为空”的情形。

**风险**：低；文案/提示改动，无运行时语义变化。

---

## P2-3 workflow.md 零状态块/缺失时完全静默

**现象**：Trellis 项目存在，但 `workflow.md` 没有任何 `[workflow-state:*]` 块（或文件缺失/不可读）时，插件返回 `null`，既不注入 breadcrumb，也不注入 bootstrap。Codex 对同输入输出 generic 降级行：

```
<workflow-state>
Status: no_task
Refer to workflow.md for current step.
</workflow-state>
```

**证据**：

- `findings/02-state.md` S14b；`s14b-broken-workflow/requests.jsonl`（0/0）与 `s14b-codex-broken.json`
- 代码：`lib/workflow.js:416-419`、`lib/session-composer.js:112-113`

**影响**：workflow 文件损坏/被裁剪时，DSH 侧完全静默，用户看不到“该修 workflow.md”的提示；Codex 会让问题可见。违反 Trellis “缺块时给出 generic 行”的契约。

**建议**：`resolveTrellisState` 在“找到 Trellis 根但 workflow 不可读/零块”时返回一个 `status=no_task`/`error` 的降级 state，body 使用 `FALLBACK_BREADCRUMB`；bootstrap 仍按 no_task 规则发送。需要区分“非 Trellis 项目”（继续静默）与“Trellis 项目但 workflow 坏了”。

**风险**：低；只影响损坏项目，正常项目路径不变。

---

## P2-4 flow-style `dsh: {dispatch_mode: inline}` 被忽略，inline 守卫被绕过

**现象**：合法 YAML `dsh: {dispatch_mode: inline}` 下：

- 无 `<dsh-mode>` 横幅；
- `trellis-agent-implement` 派发 `status=completed`，child 启动（inline 守卫未生效）。

**证据**：

- `findings/02-state.md` S13e/S13f；`s13e-flow-inline/requests.jsonl`、`s13f-flow-guard/events.jsonl`
- 代码：`lib/trellis-config.js:16`（`SECTION_RE` 仅匹配 `dsh:` 独占行）、`lib/workflow.js:133-140`、`lib/project-defaults.js:64-72`（明确拒绝改写 flow-style，称“用户 mapping 保持权威”）

**影响**：用户明确声明 inline，但插件既不迁移也不读取；inline 守卫被静默绕过。对于把 `dsh.dispatch_mode` 作为团队契约的项目，这是配置语义失效。

**建议**：`dshDispatchMode` 支持 flow-style 单键映射（至少 `{dispatch_mode: ...}`）；或者在 `mergeDshDispatchMode` 检测到 flow-style 时明确警告“不会被读取/迁移”，不要让“用户权威”与“读取器忽略”同时成立。

**风险**：低；解析器小改，需补 flow-style 单测。

---

## P3-1 inline 块仍写 `/trellis:finish-work`

**现象**：`in_progress-inline`/`completed` 块来自 Trellis 模板，Flow 行是 `/trellis:finish-work`；DSH 实际技能名是 `trellis-finish-work`，命令族是 `/trellis-finish`。插件横幅追加了正确的 `/trellis-finish-work`，但块正文仍可能误导模型。

**证据**：`findings/02-state.md` S4/S5；临时项目 `.trellis/workflow.md:249-253`、`:681-683`；插件 `lib/workflow.js:47-54`。

**影响**：模型可能尝试不存在的 `/trellis:finish-work`。横幅在后，通常能纠正；属模板层残留。

**建议**：Trellis DSH 模板渲染时替换 `cmdRefPrefix`，或插件在 inline 块渲染后做一次 DSH 命令名归一。不要把这条算成插件主链路缺陷。

---

## P3-2 角色 skill 正文与前置声明矛盾

**现象**：推送消息先写 “The role skill's 'Required: Load Trellis Context First' section is fully satisfied… do NOT run task.py current”，紧接着内联的角色 skill 正文仍写 “This platform does NOT auto-inject task context via hook. Before doing anything else, you MUST load context yourself.”

**证据**：`findings/04-subagent.md`；`s21-implement-push/requests.jsonl`。

**影响**：弱模型可能重复 `task.py current` 或追问任务；强模型通常按前置声明执行。

**建议**：在推送时从角色 skill 中删除/替换 “Required: Load Trellis Context First” 段落，或把该段落改成条件句（“若上下文未随消息提供，才执行…”）。单纯在前面加声明只能缓解。

---

## P3-3 只读项目每个 step 重试写 config

**现象**：`createDshDefaultsEnsurer` 在每个 `agent/pre-step` 都重新计算 `merged.changed` 并尝试加锁/写入；`warned` 只抑制日志，不缓存“写入失败”。只读项目上一轮多 step 会重复尝试；headless 下没有可见警告（仅 logger.warn）。

**证据**：`lib/project-defaults.js:159-205`；`s13d-readonly/`（config 未改、stderr 无警告）。

**影响**：长会话中产生无意义 IO/锁竞争；用户不知道自动引导失败。

**建议**：在 ensurer 内缓存“本进程对该 root 的写入失败/不可写”结果；或至少在 DSH 可见通道输出一次警告。属效率/可观测性问题，不影响注入正确性。

---

## P3-4 README/spec 与安装形态不一致

**现象**：README 与 `.trellis/spec/platforms/dsh-workflow-behavior.md` 说 web profile 软链到源码；实际 profile 依赖是 ssh git 依赖，安装目录是 pnpm 快照。

**证据**：`findings/01-installed.md` §6；`~/.dsh/profiles/web/package.json`。

**影响**：编辑源码后误以为已生效；需要 remove/add 或更新 git 依赖后重启。属维护/文档漂移。

**建议**：把 README/spec 的“软链”改成“git 依赖快照；改源码后需重新安装并重启”，或实际改成 `link:` 安装（二者选一，与团队工作流一致）。

---

## P3-5 默认 inline（用户确认：不是问题）

2026-10-21 用户确认：插件默认 `inline` 是既定产品选择，后续不再作为缺陷报告。本节保留为历史审计记录，不再计入问题数。修复轮未改变该默认值。

## P3-6 `trellis_wait` 晚到等待与超时边界

**现象**：child 先结束、父会话稍后才调用 `trellis_wait` 时，返回 `already-inactive` / `unknown`，不猜测成功（正确 fail-closed）；但工具本身没有超时，只有调用方 AbortSignal。若 child 一直不结算且没有事件，调用会一直等待。

**证据**：`findings/04-subagent.md` S31；`lib/wait-tool.js:217-220`。

**影响**：模型可能把 `unknown` 误读为失败，或依赖 transcript；超时依赖宿主取消。不是 Codex 对等缺陷（Codex 有原生 wait），但 DSH 侧应文档化“晚到等待不证明成功”。

**建议**：保留 fail-closed；在工具描述/输出中明确“晚到等待返回 unknown 是预期”，并考虑可选超时参数（需产品确认）。

---

## P3-7 版本检查手动校验显示原始 abort（已修复）

**现象**：UI 设置页点击“手动校验”后，插件来源显示 `上游 fork This operation was aborted`。

**根因**：`lib/upstream.js` 的 GitHub Atom 请求使用 10 秒 AbortController；commit feed 超时后 `Promise.all` 整体 reject，handler 把原始 AbortError message 直接透传给客户端。release feed 的失败被 `fetchReleaseFeed` 静默吞掉，进一步掩盖了真实原因。

**修复**：`fetchText` 把 AbortError 转为明确的 `GitHub request timed out after N ms`；plugin 分支改用 `Promise.allSettled`，返回 200 的局部 `{commit, release, errors}`；客户端把无 commit 的响应渲染为“部分结果 + 可稍后重试”，不再显示原始 abort。真实 GitHub 请求和 10ms 挂起 feed 均已验证。

**证据**：`fix-report.md`；`test/upstream.test.js`、`test/version-check.test.js`。

## 6. 验证通过 / 与 Codex 等价的部分

| 能力面 | 结论 | 证据 |
| --- | --- | --- |
| 状态面包屑（7 类状态） | 通过；`in_progress` 正文与 Codex 逐字节相同 | `findings/02-state.md` |
| 工作流变体 3 层 | 通过 | S9 |
| skip 关键字（项目/插件） | 通过 | S10/S10b |
| inline/auto 与横幅 | 通过（block-style 配置） | S4/S11/S12 |
| 自动引导只写一次/不覆盖 auto | 通过 | S13 |
| spec deny-once/retry/ticket/损坏回退 | 通过；deny 文案与 Codex 等价 | `findings/03-spec.md` |
| spec 大写工具名/Read opt-in | 通过 | S18 |
| implement/check push | 通过；curated context 与 Codex 一致，额外角色契约 | `findings/04-subagent.md` |
| generic 子代理静默 | 通过 | S24 |
| 无 role skill fallback | 通过 | S25 |
| dispatch guard（无任务/inline/逃生口） | 通过，DSH 增强 | S26–S29 |
| `trellis_wait` 成功/失败/晚到 | 通过（晚到 unknown，fail-closed） | S30–S32 |
| 会话隔离 | 通过 | S33 |
| shell 身份 | 通过 | S34 |
| 三个命令（handler 级） | 通过 | S35 |
| 冲突/版本路由 | 通过 | S38 |
| 无插件对照 | 缺口确实存在（0 注入/0 工具） | S39 |
| Trellis init/update/task 契约 | 通过，update 保留 dsh 段 | S40–S42 |

## 7. 未验证边界

- 真实 Web 设置页 UI、真实 slash 命令分发、压缩/clear 后重注入：DSH Web 认证 URL 未在无凭据浏览器中可用；未把 token 带入命令。
- 真实第二个 Trellis 插件的桌面通知/横幅：未向用户 profile 安装第二插件。
- 真实模型对提示的长期遵循率：mock 只证明模型收到什么。
- 子代理 `send_message` 后续轮次、`trellis_wait` 超时/取消、fork 子代理的 push 去重。
- 多 spec 预算降级、超长 spec 截断、二进制 spec：单测覆盖，未做真实 E2E。
- 上游 0.1.13 行为。

## 8. 最终回答（摘要）

1. **能否达到 Codex 使用 Trellis 的同等效果？**
   主链路基本达到：状态注入、spec deny-once/ticket、implement/check context、skip、变体、命令与身份均通过；`in_progress` 正文与 Codex 逐字节一致。**但 research 子代理上下文不等价**，且零块 workflow、flow-style 配置两个边界会静默失效。因此不能笼统说“完全一致”；按能力面看是“核心等价 + research 退化 + 两个边界缺陷”。

2. **是否补足 DSH 使用 Trellis 的不足？**
   是，且是质变：无插件对照下没有 per-turn 状态、没有 spec 注入、没有子代理 push、没有 guard、没有 `trellis_wait`；插件把这些都补上了，并额外提供 fail-closed guard。inline 默认与 `task.py start` 的摩擦是补足过程中新暴露的集成问题。

3. **是否还有其它缺漏/不足？**
   有：P2-1..P2-4、P3-1..P3-4、P3-6、P3-7。P3-5 经用户确认撤销；其余已在 0.1.1 修复，见 `fix-report.md`。没有 P0/P1；没有发现数据破坏、权限越权或不可恢复错误。
