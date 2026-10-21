# Findings — spec 注入机制对等验证

判定基线：E1 = 实际运行；E2 = 静态推断；E3 = 文档/测试声明。
审计对象：`dsh-plugins/dsh-trellis/lib/spec-*.js`、`lib/trellis-config.js`；
对照：`.codex/hooks/inject-spec-context.py` + `.trellis/scripts/common/*`。

## 1. 配置解析对等（E1）

真实 Trellis 项目 `/tmp/trellis-e2e` 上写同一份 `.trellis/config.yaml`，分别调用
插件 `specInjectionSettings` 与 Codex hook `get_spec_injection_settings`：

| 用例 | 插件 | Codex hook | 结论 |
| --- | --- | --- | --- |
| `enabled: "false"` 带行尾注释、`max_*` 混合引号、`tools: [Edit, Write, Read]` | `enabled:false, 1234, 2345, 60, ["edit","write","read"]` | `(False, 1234, 2345, 60, ('Edit','Write','Read'))` | 等价（大小写归一） |
| `tools: []` | `tools: []` | `tools: ()` | 等价（显式"永不触发"） |
| `enabled: maybe` | 静默按默认 true | 默认 true + stderr 警告 | 结果等价，提示方式不同 |
| `tools: nope` | 回退默认 `["edit","write"]` | 回退默认 `('Read','Edit','Write','MultiEdit')` + 警告 | **默认集不同（有意）** |
| `refresh_window_seconds: -5` | 回退 2700 | 回退 2700 + 警告 | 等价 |

默认工具集差异来自插件注释：对齐 Codex 实际 `PreToolUse` matcher `Edit|Write`，
`Read` 作为显式 opt-in；DSH 无 `MultiEdit` 工具。属有意差异，不是缺陷。

## 2. deny-once / retry / ticket 对等（E1）

- 插件端到端见 `e2e-session.md` 第 3 节：deny 一次 → retry 放行 →
  read 工具走 post-execute ticket；状态分片写入 `.trellis/.runtime/spec-inject/`。
- Codex hook 同输入输出：`permissionDecision:"deny"`、
  `permissionDecisionReason:"Trellis injected governing specs. Review them, then retry this tool call."`、
  `additionalContext` 的 `<spec-context>` 与 `sha256="a46cd3be4651"` 与插件逐字一致（E1）。
- 同一 spec + 窗口内再次触碰走 `silent`（`decide()` 第 66 行），与 Codex 的
  `.trellis/scripts/common/spec_match.py` 决策语义一致；这是实测到的"无消息"而非缺陷。

## 3. spec 索引与匹配（E1）

- `matchSpecsForFile` 对 `src/**/*.ts` 命中 `.trellis/spec/demo/demo-guidelines.md`；
  文件无 `paths:` frontmatter 时（trellis 0.7 模板默认）不命中，行为与 Trellis 一致。
- 未验证：specificity 排序在多重命中时的顺序（需要多份带 glob 的 spec，未构造）。

## 4. 状态持久化与 compaction（E1 / E2）

- 持久化：`.trellis/.runtime/spec-inject/session-<id>.json` 实际生成；同一会话跨轮次
  "已教过"状态生效（第二次触碰不再 deny，实测）。
- 重启持久化、损坏分片恢复、只读目录降级：未构造真实进程重启（E2，仅有单测覆盖）。
- `compaction/end` 清除：未构造压缩事件（E2）。

## 5. 未验证 / 无法验证

- 多 spec 同时命中时的 `max_total_chars` 降级为索引行：未构造多份 spec（E2）。
- 二进制/超长 spec 的截断提示：未构造（E2）。
- 由于三个并行子代理遭遇真实 LLM `QUOTA/402` 中断，其原定 findings 未产出；
  本文件结论全部由主会话 E1 命令重新取得，未引用未验证的转述。
