# Findings — `dsh.dispatch_mode: inline` 专项审查（E1）

## 1. 结论先行

| 问题 | 结论 |
| --- | --- |
| 是否实现 inline 模式 | **是**。项目级 `dsh.dispatch_mode` 已被真实读取并改变注入内容（T4/T5/T12/T13/T15） |
| 实现范围 | 仅 `planning` / `in_progress` 两个状态、且解析到的 workflow 文件存在对应 `*-inline` 块时生效 |
| 主链路是否正确 | **正确**：选块、追加 DSH 横幅、去重、切回 auto、非法值回落均符合设计；正文与 Codex 逐字相同（差异只是多出的横幅） |
| 是否存在实现问题 | **有 2 个边界缺陷 + 2 个一致性差异**（见 §4），均为 P2/P3，不影响主链路 |

## 2. 主链路证据

同一真实会话（`session-aaa548aa-…`）逐轮切换：

- T3 `dsh.dispatch_mode: auto` → `planning` 基础块（449 字符正文，与 Codex 相同）。
- T4 改 `inline` → `planning-inline`：Codex 块 439 字符 + DSH 横幅 333 字符。
- T5 任务转 `in_progress` → `in_progress-inline`：Codex 块 325 + 横幅 333。
- T12 改回 `auto` → `in_progress` 基础块（1635 字符，与 Codex 相同），说明切换会重新注入。
- T13 再改 `inline` → 重新注入 `in_progress-inline`。
- T14 `dispatch_mode: InLiNe   # 注释` → 仍解析为 inline（digest 未变，无新消息）。
- T15 `dispatch_mode: off` → 回落 auto（注入 1755 字符基础块）。
- 变体覆盖：V2 自定义 `planning-inline` 块被选中并追加横幅；V3 空 `planning-inline` 被丢弃后回到基础块。
- 作用域：S7 的子代理请求中无 `<dsh-mode>`；inline 只作用于根会话。

横幅原文（`lib/workflow.js:39-51`，333 字符）：

```
<dsh-mode>
inline: the main session implements and checks directly. Do not dispatch trellis-agent-implement / trellis-agent-check sub-agents; the trellis_wait tool is not needed in this mode. Verify with the trellis-check skill, update specs with trellis-update-spec, then commit (Phase 3.4) and run /trellis-finish-work.
</dsh-mode>
```

## 3. 与 Codex `codex.dispatch_mode: inline` 的逐项对照（E1）

| 维度 | Codex（真实 hook 输出） | DSH（真实会话注入） | 判定 |
| --- | --- | --- | --- |
| 默认值 | `auto` | `auto` | 一致 |
| 非法值 | 回落 **inline** | 回落 **auto** | 差异（DSH 更保守） |
| `sub-agent` 别名 | 视为 `auto` | 视为 `auto` | 一致 |
| inline 选块 | `planning-inline` / `in_progress-inline` | 同 | 一致 |
| 块缺失时 | 用基础块 **并仍输出 `<codex-mode>inline` 横幅** | 用基础块，**无任何 inline 提示** | **缺陷 I-1** |
| 模式横幅覆盖状态 | 每一轮、所有状态（含 no_task/completed/task_error） | 仅 planning/in_progress 且 inline 块存在时 | 差异 I-2（P3） |
| 技术门禁 | 无（仅指令） | 无（`dispatch guard` 不检查 inline，S7 放行） | 差异 I-3（设计缺口） |
| 关闭 inline 的方式 | 改 `codex.dispatch_mode` | 改 `dsh.dispatch_mode`（Codex 忽略 `dsh.*`，反之亦然） | 设计如此 |

## 4. 问题清单（inline 部分）

### I-1（P2）inline 块缺失时静默退化为 auto 语义

- 复现：`dsh.dispatch_mode: inline` + 任务 `workflow: alt`，`alt.md` 只有 `planning` 块 →
  DSH 注入 `Trellis workflow state: planning` + `ALT-PLANNING-BODY`，**无横幅**（V1/V3）。
- 同样输入下 Codex 输出 `ALT-PLANNING-BODY` **并附** `<codex-mode>inline: …</codex-mode>`。
- 影响：项目声明了 inline，模型却拿到 auto 语义的正文；若基础块含
  `Sub-agent mode: curate implement.jsonl…`（全局模板即如此），会与 inline 意图直接冲突，
  且模型无从得知应为 inline。
- 根因：`lib/workflow.js:423-427` 把“是否 inline”与“是否存在 `*-inline` 块”绑成一个布尔；
  `:433-435` 的横幅又只在 `inline && block !== undefined` 时追加。
- 建议修复：把模式判定与块选择解耦——`dsh.dispatch_mode=inline` 且状态属于
  `planning`/`in_progress` 时，即使 `*-inline` 块缺失也追加 `DSH_INLINE_NOTE`（并保持基础块）。
  回归用例：变体无 inline 块、空 inline 块、模板整体缺 inline 块。

### I-2（P3）横幅覆盖状态少于 Codex

- Codex 每轮对所有状态输出 `<codex-mode>`；DSH 在 `completed` / `stale` / `task_error` / 自定义状态 / `no_task` 下没有模式提示。
- 影响有限（这些状态下“是否派发”通常已由块正文决定），但与 Codex 行为不一致。
- 建议：若要严格对齐，可在所有状态追加一行模式提示；或明确记录为“仅阶段内提示”的设计。

### I-3（P2/P3，需用户决策）inline 无技术门禁，与派发守卫能力不一致

- S7 实测：inline 模式下派发 `trellis-agent-implement` **成功**，子代理照常收到 5472 字符推送。
- 插件已经实现了 fail-closed 的派发守卫（任务不可读即拒绝），却没有把 inline 纳入守卫条件；
  同一个插件里“该拦的拦、该提示的只提示”，行为不一致。
- Codex 侧同样只有提示，因此这不算“落后于 Codex”，但属于 DSH 侧可用而未用的约束。
- 选项：① 保持提示（与 Codex 一致，改动最小）；② 守卫在 inline 下拒绝 implement/check 派发，
  仅允许 research（风险：显式委派场景需要逃生口，可用配置开关）。

### I-4（P3）共享 workflow 模板里的 Codex 命令形态

- 复用的 `*-inline` 块文本含 `/trellis:finish-work`（Codex 斜杠命令）；DSH 实际命令是
  `/trellis-status` / `/trellis-finish` / `/trellis-doctor`，`trellis-finish-work` 是技能。
- DSH 横幅已用 `/trellis-finish-work` 补充，但基础块（非 inline）同样保留 Codex 形态；
  属模板层问题，插件横幅缓解了一部分。

## 5. 未覆盖

- `dsh.dispatch_mode` 放在多文档/锚点等 YAML 高级形态下的解析（本轮只测了简单标量、大小写、行内注释、非法值）。
- inline 模式下 `trellis_wait` 是否应被注销（当前仍注册、可用；横幅只说明“不需要”）。
