GATE: PASS

# Validation record — local dsh-trellis 0.3.7

- 日期：2026-10-20
- 范围：把上一轮对照中的 #1（子代理角色契约）与 #5（spec 去重状态）落为实现；#2 bootstrap 频率保持不变，只统一文档口径
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 安装形态：`web` profile 依赖 `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis`
- 临时项目：`/tmp/trellis-parity-20261020/project`（`trellis init -u xzc --dsh --codex -y`）

## 结论

`USER_ACCEPTANCE: NOT_APPLICABLE`（当前完整范围没有 partial-parity 缩减；历史 M1 的
`N/A` 仅作历史记录，不伪造 `ACCEPTED/PENDING`）。

本轮不是补丁式修补，两个结构性缺口的归属都移到正确层：

1. 子代理角色契约由目标项目已安装的 `.dsh/skills/trellis-agent-<role>/SKILL.md`
   提供，插件只负责读取、去 frontmatter、按 16 KiB 上限截断并放进首步 push；
   不在插件里复制第二份角色正文。
2. spec 去重状态由 `lib/spec-state.js` 持久化到目标项目
   `.trellis/.runtime/spec-inject/<session>.json`；`spec-inject.js` 的决策逻辑不变，
   `spec-policy.js` 只替换状态所有者；压缩/clear 同时删除内存与磁盘分片。

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `lib/subagent-context.js` | 新增 `readRoleInstructions` / `stripYamlFrontmatter` / `roleInstructionsFallback`；首步 push 先角色契约、后 curated task context；缺失 skill 时注入路径提示，不静默省略 |
| `lib/spec-state.js` | 新增 per-project/per-session JSON 分片；原子 temp+rename；损坏、版本不匹配、只读或写入失败时安全回退为“无历史”并重新教学 |
| `lib/spec-policy.js` | 按 root + session 加载/保存；同一 session 的写入串行化；`compaction/end` 删除内存与磁盘分片；无稳定 session identity 时不写共享状态 |
| `test/subagent-context.test.js` | 角色正文提取、frontmatter 剥离、缺失 skill 兜底、首步 push 包含角色契约 |
| `test/spec-state.test.js` | round-trip、损坏/版本回退、非法记录过滤、clear、路径 containment、纯 JSON 格式 |
| `test/spec-policy.test.js` | 重启保留、压缩删除磁盘分片后重启重新 deny、重试放行 |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `pnpm test` | **266 tests，262 pass，0 fail，4 skip** |
| `pnpm run build:client` | 通过；`lib/client.js` 63.97 kB（gzip 16.57 kB）；`PLUGIN_VERSION = "0.3.7"` |
| 真实 headless：spec 首触 | 第一次 `write` 返回 `Trellis injected governing specs` + `<spec-context ... SPEC-MARKER-12345>`；重试成功 |
| 真实 headless：重启后 | 同一 session 在新进程中继续编辑另一个 `src/` 文件，**不再 deny**；状态分片在 `.trellis/.runtime/spec-inject/session-16ecb4eb-...json` |
| 真实 headless：子代理首步 | 子请求包含 `## Role Instructions`、角色 skill 正文（含 `This platform does NOT auto-inject...`）、`prepared by dsh-trellis` 说明、`Active task` 与 PRD curated context |
| 缺失 skill 兜底 | 单测覆盖：至少注入 `.dsh/skills/trellis-agent-<role>/SKILL.md` 路径提示 |

真实 headless 证据：

- `evidence/dsh-state-write1.events.jsonl`（首触 deny + retry）
- `evidence/dsh-state-write2.events.jsonl`（重启后不 deny）
- `evidence/dsh-subagent-role.requests.jsonl`（角色契约 + curated context）
- 临时项目状态分片：`.trellis/.runtime/spec-inject/session-16ecb4eb-85db-4cb4-94ef-ade6bbaae757.json`

## Bootstrap 口径（不是代码变更）

保持“每会话一次”不变：

- 新根会话第一次 `no_task` 注入一次 `<trellis-bootstrap>`。
- 如果这一轮没有开始 Trellis，同一会话后续普通轮次**不再重复催促**；workflow
  面包屑仍会随任务状态出现。
- 需要重新提示时，手动加载 `trellis-start`，或通过压缩/clear 移除后再次注入；
  新会话会重新注入。
- 这是有意的降噪设计，不是 `dsh-trellis` 的缺陷；本插件不复制 Codex 的每轮提醒频率。

关联文档已同步：`README.md`、`LOCAL_CHANGES.md`、
`../../docs/capability-inventory.md`、`docs/manual-verification.md`。

## 未验证/边界

- 真实 Web `/compact`、clear 仍未触发；本轮用单元/集成测试覆盖“删除内存 + 磁盘分片后重新教学”，并在 manual-verification M1b 保留手工验收步骤。
- 状态分片是 project-local advisory state：同一 session 被多个进程同时编辑时是 last-write-wins；DSH Web 单进程场景不受影响。
- 角色契约来自目标项目已安装的 Trellis skill；如果目标项目没有 `.dsh/skills/trellis-agent-*/SKILL.md`，只注入路径提示，不伪造角色正文。
- 未在当前仓库创建 Trellis 任务；临时项目复用旧验证任务作为夹具。
