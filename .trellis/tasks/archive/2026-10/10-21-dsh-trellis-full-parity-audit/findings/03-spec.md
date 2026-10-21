# 路径级 spec 注入 E2E

测试 spec：`.trellis/spec/demo/index.md`，frontmatter `paths: [src/**]`，正文 marker `SPEC-BODY-MARKER-ONLY`。

## 结果

| ID | 场景 | 观察 | 判定 | 证据 |
| --- | --- | --- | --- | --- |
| S15 | 首次 `write src/a.ts` | `tool_result status=error`；reason = RETRY_NOTICE + `<spec-context>` 正文；重试 `status=completed` | 通过 | `s15-spec-deny/events.jsonl` |
| S15 | 状态分片 | `.trellis/.runtime/spec-inject/session-b683….json` 生成，记录 `mode=full` | 通过 | 同上 + 文件 |
| S16a | 窗口内再次 touch `src/b.ts` | 无新 deny；tool completed | 通过 | `s16a-window-silent/events.jsonl` |
| S16b | 分片 `ts` 推旧后 touch `src/c.ts` | tool completed；下一次请求出现 `<spec-ticket>` | 通过 | `s16b-ticket/requests.jsonl` |
| S17 | `spec_injection.enabled: false` | 无 deny、无 ticket | 通过 | `s17-spec-disabled/events.jsonl` |
| S18a | `tools: [Edit, Write, Read]` 大写 | `write` 仍 deny（规范化为小写） | 通过 | `s18a-uppercase-tools/events.jsonl` |
| S18b | `tools: [Read]` | `read` 不阻断；下一次请求出现 `<spec-context>` | 通过 | `s18b-read-optin/requests.jsonl` |
| S19 | 损坏分片 | 重新 full deny，不静默放行 | 通过 | `s19-corrupt-shard/events.jsonl` |
| S20 | Codex 同输入 | `permissionDecision=deny`，reason 与插件 RETRY_NOTICE 相同；`additionalContext` 与插件 payload 相同（203 字符） | 等价 | `codex-spec-out.json` |

## 关键细节

- 插件 deny reason 把 RETRY_NOTICE 与 payload 合并在 `reason`；Codex 把两者拆到 `permissionDecisionReason` 与 `additionalContext`。模型最终看到的文本等价。
- 分片在 5 秒窗口内静默；把 `ts` 改 0 后 ticket 出现在 **tool 执行后的下一次请求**，符合 DSH `additionalContexts` 语义。
- `read` 只走 post-execute；不会阻断读取。这是插件 README 已声明的平台形状差异。
- 损坏分片按“无历史”处理，重新 full；安全侧正确。

## 未覆盖

- 真实 `/compact` 后的分片删除与重新教学（需要 Web 压缩；本轮未完成）。
- 多 spec 同时命中时的预算降级与 index 行（单测覆盖，未做真实 E2E）。
- 超长 spec 的字符预算截断（单测覆盖）。
