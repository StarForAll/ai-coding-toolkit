# Findings — spec 路径注入（E1）

实验 spec：`.trellis/spec/demo/demo-guidelines.md`，frontmatter `paths: ["src/**/*.ts"]`。

| 用例 | 配置 | 结果 | 证据 |
| --- | --- | --- | --- |
| D1 deny-once | 默认（`edit`/`write`） | 第一次 `write src/a.ts` 被拒绝：`Error: Trellis injected governing specs. Review them, then retry this tool call.` + `<spec-context file="src/a.ts" spec=".trellis/spec/demo/demo-guidelines.md" sha256="b31dd704c1f3">`；文件未落盘 | `spec/d1-deny-retry/` |
| D1 retry | 同上 | 重试同调用 `status=completed`，文件内容更新为 `a = 2` | 同上 |
| D2 ticket | `tools: [read, edit, write]` | `read src/a.ts` 不被拦截；**下一次模型请求**出现独立 user 消息 `<spec-context …>`（206 字符） | `spec/d2-ticket-read/` |
| D3 关闭 | `enabled: false` | 无 deny、无 `<spec-context>`，写入直接成功 | `spec/d3-disabled/` |
| D4 预算 | `max_spec_chars: 40` | 正文截断并附 `[Trellis: truncated at 40 characters — read … for the full content]` | `spec/d4-budget/` |
| D5 大写工具名 | `tools: [Write]` | 规范化后仍触发 deny，reason 与 Codex 逐字相同 | `spec/d5-upper-tools/` |
| 状态分片 | 默认 | `.trellis/.runtime/spec-inject/session-*.json` 生成，含 `version: 1`、`records[{v:2, spec, sha256, …}]` | D1 输出 |

## 与 Codex hook 的逐字对照（E1）

同一 spec、同一文件、`tools: [Write]`：

- DSH 工具结果：`Error: Trellis injected governing specs. Review them, then retry this tool call.` +
  `<spec-context file="src/a.ts" spec=".trellis/spec/demo/demo-guidelines.md" sha256="b31dd704c1f3">…</spec-context>`
- Codex hook 输出：`permissionDecision: "deny"`，`permissionDecisionReason` 与 DSH 相同，
  `additionalContext` 中的 `<spec-context>` 正文与 sha256 前缀完全一致。
- 截断文案、ticket 形态、`refresh_window` 语义来自同一契约；本轮未单独重跑 refresh window 的静默/刷新分支。

## 配置可移植性（P3，跨平台共享配置）

- DSH 把工具名规范化为小写（`lib/trellis-config.js:225-232`），因此 `tools: [Write]` 与 `tools: [write]` 在 DSH 都生效。
- Codex hook 只认识 `Read|Edit|Write|MultiEdit`：写 `tools: [write]` 时真实运行输出
  `[inject-spec-context] WARN: unknown spec_injection.tools entries ['write'] — they will never match`，
  该配置在 Codex 侧等于关闭注入。
- 结论：共享项目配置应使用 Trellis 原生大写工具名，两个平台都能工作；插件文档若建议小写，会诱导出 Codex 侧静默失效。
