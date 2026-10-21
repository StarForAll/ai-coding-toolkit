GATE: PASS

# Validation record — local dsh-trellis 0.3.8

- 日期：2026-10-21
- 范围：修复 0.3.7 审计发现的对标缺陷（P0/P1/P2 + 待定项）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`
- 来源：`.trellis/tasks/10-21-dsh-trellis-parity-audit/`（report.md + 子任务 findings）
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 临时项目：`/tmp/trellis-e2e`（`trellis init -u xzc --dsh --codex --claude -y`）
- 端到端方式：独立 profile（`dsh-base` + `dsh-headless` + `insert: dsh-trellis`）+ 本地
  OpenAI-compatible mock LLM，抓取模型实际收到的 `messages`

## 结论

审计确认的缺陷全部修复，未发现回归；插件自带测试从 262 pass 增至 278 pass。

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `lib/workflow.js` | `STATUS_RE` 增加“开标签必须在行尾”约束（与 Python hook 同语法）；`completed`/自定义状态按原值匹配；指针指向已删除目录 → `stale`；按任务/个人/团队/全局优先级选择 workflow 文件；`codex.dispatch_mode: inline` 选择 `*-inline` 块 |
| `lib/trellis-config.js` | 新增 `topLevelScalar`（`default_workflow`）与 `promptInjectionSkipKeyword` |
| `lib/session-composer.js` | 项目 `prompt_injection.skip_keyword` 优先，插件 `skipKeyword` 兜底 |
| `lib/subagent-context.js` | 首步 push 明确声明角色 skill 的“先加载上下文”段落已被满足并禁止重复探测；`stale` 父指针不再提供 push 路径 |
| `lib/dispatch-guard.js` | `stale` 指针不再被视为可读任务 |
| `test/workflow.test.js` | 注释内标签、行内标签、completed/自定义/stale、workflow 选择优先级、inline 变体、非法 id |
| `test/session-composer.test.js` | 项目 skip 关键字优先、空值禁用、插件兜底、子代理静默 |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | 282 tests / 278 pass / 0 fail / 4 skip |
| 真实 `.trellis/workflow.md` 解析 | `no_task` 4605→**421** 字符 / 66→3 行；breadcrumb 491 字节，真实指引完整可见 |
| 全新 `trellis init` 项目解析 | 同上（421 / 3 行），与 Codex/Claude hook 一致 |
| headless 真实 DSH 会话（mock LLM） | 模型请求中的 breadcrumb 为 491 字节，首行 `No active task. First classify…`；bootstrap 138 字节不变 |
| 项目 `prompt_injection.skip_keyword: skip-me` | 含 `skip-me` 的提示词下，模型请求中 trellis 消息数为 **0** |
| 任务级 workflow 变体（真实临时项目） | `task.json workflow: alt` → 解析到 `ALT_WORKFLOW_MARKER`（修复前忽略） |
| stale（真实 Trellis 解析器对照） | 插件 `stale` 与 `common.active_task stale=True` 一致；无 stale 块时降级为通用行 |
| `completed` / `blocked`（真实 task.json） | `completed` 使用 completed 块；`blocked` 使用通用降级行，不再报 `no_task` |

## 已知边界

- `stale` 需要 workflow.md 定义该块；0.7.0-beta.4 全新模板尚未包含，此时使用通用降级行
  （与 Codex hook 的 fallback 相同）。
- `codex.dispatch_mode` 是 Codex-only 设置：Trellis carrier 只在 `platform == "codex"` 时选 `*-inline`；DSH 保持基础块（检查轮已回退此前的 inline 选择）。
- 未重新跑浏览器级设置页验证（与 0.3.7 相同的未验证边界）。

## 检查补充（`trellis-check`，2026-10-21 同日）

对上一轮修复做对抗复核，用同一输入分别跑插件与 Python carrier 后确认两处偏差并修复：

| 文件 | 修复 | 依据 |
| --- | --- | --- |
| `lib/workflow.js` | 正文为空/仅空白的 `[workflow-state:*]` 块不再计入模板 | `load_breadcrumbs` 保留标签的前置条件是正文非空（`if body:`），否则降级为通用行；此前空块会让"空正文面包屑"或空的 `*-inline` 顶掉有内容的基块 |
| `lib/breadcrumb.js` | 跳过关键词边界改为 `(?<![\w-])keyword(?![\w-])`（含 Unicode 词字符），不再用 ASCII `\b` | 项目 `prompt_injection.skip_keyword` 与 Codex/Claude 共用，必须给出相同跳过判定；ASCII `\b` 在两个方向上都会改变判定（`foo-no-trellis` 误命中、`skip.`/`#skip` 漏命中） |

补充用例：`stale` 指针在 dispatch 守卫中不可读（`test/dispatch-guard.test.js`）、
`stale` 父指针不提供 push 路径（`test/subagent-context.test.js`）、push 对角色 skill
"自行加载上下文"段的覆盖文案（`test/subagent-context.test.js`）。

同一轮复核还推翻并回退了一项 0.3.8 变更，并补齐两项缺口：

| 文件 | 处理 | 依据 |
| --- | --- | --- |
| `lib/workflow.js` | DSH 不再选择 `*-inline` 块；`codex.dispatch_mode` 视为 Codex-only | `workflow.md` 明确标注 "Codex-only opt-in"，carrier 的 `resolve_breadcrumb_key` 仅在 `platform == "codex"` 时选 inline。本仓库默认 `dispatch_mode: inline`，此前会把 1635 字节的 `in_progress`（含 DSH 派发协议）换成 325 字节的"不要派发子代理" |
| `lib/workflow.js`、`lib/node-fs.js` | 会话指针按 `common/active_task.py` 归一（`tasks/<slug>`、`./`、绝对路径），并要求目标为目录；文件同名或越界 → `stale` | 修复前 `tasks/x` 假 stale、绝对路径被当相对路径、同名文件误报 `task_error` |
| `lib/doctor.js` | 报告实际选中的 workflow 文件（`Workflow file:`），不再固定 `.trellis/workflow.md` | 变体生效后，块数可能描述的是另一个文件 |
| `test/workflow.test.js` | +4 用例：DSH 忽略 inline、legacy/绝对指针、文件非目录 stale、越界 stale | 回归覆盖 |

复核后：`node --test "test/*.test.js"` → **291 tests / 287 pass / 0 fail / 4 skip**；
真实 `.trellis/workflow.md` 解析仍为 9 块（与 Python 侧逐块一致，无空块）；
本会话指针实测解析为 `in_progress`（1635 字节），不再是 `in_progress-inline`。

