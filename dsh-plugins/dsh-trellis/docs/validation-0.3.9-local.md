GATE: PASS

# Validation record — local dsh-trellis 0.3.9

- 日期：2026-10-21
- 范围：新增 DSH 自己的 Trellis 执行模式 `dsh.dispatch_mode`（`auto` / `inline`）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 临时项目：`/tmp/trellis-e2e`；端到端使用独立 profile + 本地 mock LLM

## 背景

0.3.8 的 check 轮确认 `*-inline` 块是 Codex-only（`workflow.md:223-228/257-261`，
carrier 的 `resolve_breadcrumb_key` 仅在 `platform == "codex"` 时选择），因此 DSH
不应复用 `codex.dispatch_mode`。但 DSH 也没有自己的内联开关：基础
`[workflow-state:in_progress]` 写的是 "Main-session default: dispatch … sub-agents"，
主会话想一直自己做时没有受支持的配置。

本版增加 DSH 自己的模式，而不是复用 Codex 的键：

```yaml
dsh:
  dispatch_mode: inline   # auto（默认，派发角色子代理）/ inline（主会话直接做）
```

- `auto` / 缺省 / 非法值 → 基础块，行为与 0.3.8 相同。
- `inline` 且存在 `*-inline` 块 → 选中 `<status>-inline` 阶段块，并追加
  `<dsh-mode>` 说明：主会话直接实现/检查、不派发 `trellis-agent-*`、无需
  `trellis_wait`、用 `trellis-check` 技能验证、Phase 3.4 提交后走
  `/trellis-finish-work`。
- 没有对应 `*-inline` 块时保持基础块，不追加 banner（不伪造内联指引）。
- `codex.dispatch_mode` 仍然完全忽略。

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `lib/workflow.js` | 新增 `dshDispatchMode` 与 `DSH_INLINE_NOTE`；`resolveTrellisState` 按 `dsh.dispatch_mode` 选择块并追加 banner |
| `lib/doctor.js` | 报告新增 `Dispatch mode: <auto|inline> (dsh.dispatch_mode)` |
| `test/workflow.test.js` | +4 用例：inline 选中块 + banner、auto 保持基础块、非法值回落、无 inline 块不加 banner |
| `.trellis/config.yaml` | 本仓库固定 `dsh.dispatch_mode: inline`（与 Codex 侧的 inline 规则对齐） |
| `README.md`、`LOCAL_CHANGES.md` | 记录项目级模式与 banner |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | **295 tests / 291 pass / 0 fail / 4 skip** |
| 本仓库真实指针 + 真实配置 | `resolveTrellisState` → `in_progress-inline`，body 660 字节，含 `<dsh-mode>` |
| headless 真实 DSH 会话（`dsh.dispatch_mode: inline` + planning 任务） | 模型请求中的 breadcrumb 为 `Trellis workflow state: in_progress-inline`，788 字节，结尾为 `<dsh-mode>…</dsh-mode>` |
| 无活动任务的会话 | 仍为 `no_task` 491 字节，无 banner |
| `auto` / 非法值 / 无 inline 块 | 保持基础块，无 banner |

## 已知边界

- Mode 只影响 `planning` / `in_progress`（与现有 `*-inline` 块一致）；`completed`
  与自定义状态不受影响。
- `dsh.dispatch_mode` 是本地插件扩展，Trellis CLI 不读取该键；`trellis update`
  会保留 `config.yaml` 的用户键，但不会校验它。
- 未做真实 LLM 行为验证（只验证模型实际收到的文本）；设置页 UI、`trellis_wait`
  结算等边界与 0.3.8 相同。
