GATE: PASS

# Validation record — local dsh-trellis 0.1.4

- 日期：2026-10-22
- 范围：`no-trellis` / 项目 `prompt_injection.skip_keyword` 从“按 step”改为“按 turn”生效（缺陷 D1），
  以及子代理 push 任务来源优先级的文档更正（观察项 O2）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）；未提交
- 端到端环境：隔离的 `DSH_HOME=/tmp/skip-e2e/home` + 临时 profile（`skip-verify` = 本源码 lib，
  `skip-verify-old` = 0.1.3 lib）+ 临时 Trellis 项目 `/tmp/skip-e2e/proj`，真实 LLM
  （`deepseek-official`，凭据经环境变量注入，未写入任何文件或输出）

## 问题复核：D1 与 O2 是否真实

### D1 —— 真实缺陷，已修复

`agent/pre-step` 的 `messages` 是 inbox claim 到的新消息批次
（`dsh-agent-loop` `preStep`：`this.inbox.claim(target, turn)`），模型调用工具后的 step 2
批次里只有工具结果和运行时上下文，不再含带 `no-trellis` 的用户 prompt；因此
`hasSkipKeyword(messages)` 在 step 2 不命中，同一轮继续注入面包屑 + bootstrap。
Codex 侧是 `UserPromptSubmit`（每轮一次，见 `.codex/hooks/inject-workflow-state.py:504`
“this turn”），所以按轮判定。README 第 1 条、设置页文案
（`src/client/locales.js` `skipKeywordHint`“跳过本轮面包屑”）都承诺按轮生效，代码只做到按 step。

复现（真实会话，0.1.3，`session-20bf2c90`）：

```
[7]  seq=6  step/start turn=1 step=1
[23] seq=22 tool/result
[25] seq=24 step/start turn=1 step=2
[26] seq=25 trellis:breadcrumb      <- 同一轮、跳过词已在 step 1 生效后仍注入
[27] seq=26 trellis:bootstrap
```

### O2 —— 设计权衡，行为正确；只更正了写反的文档

- 代码事实：push 需要子代理 header 的 `parentSession`，任务路径优先取 dispatch prompt 的
  `Active task:`，其次才是父会话指针（`subagent-context.js`：`parsed.taskPath ?? await
  parentTaskPath(...)`）。两者都取不到时静默不 push —— 与 Codex 在 task_dir 缺失时 return 一致；
  无任务时本来就没有任务上下文可 push，research 另有 dispatch-guard 的落盘位置提醒。
- 因此“research push 依赖父会话指针存在”这一表述不准确（prompt prelude 才是首选来源），但
  “父会话从未绑定任务时没有 push”是真实且符合设计的。本轮不改行为。
- 真实文档缺陷：README 第 4 条写成“父会话指针缺失时回退到 dispatch prompt 的 `Active task:`”，
  优先级写反；已更正，并补上“两者都取不到时不 push”。

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `lib/session-composer.js` | 新增 `position.turn` 参数与 `skippedTurns`（`WeakMap`，按 agent）；命中关键词记住该 turn，后续 step 直接返回 `[]`。无 `turn` 的宿主退化为原来的按 step 判定。项目引导（`dsh.dispatch_mode`）仍在跳过期间执行。 |
| `lib/index.js` | `agent/pre-step` 把 payload 的 `turn` 传给 composer。 |
| `lib/config.js` | `skipKeyword` 描述从“one breadcrumb injection”改为“whole turn（every step）”。 |
| `README.md` | 跳过词语义改为按轮（含工具调用后的 step）；子代理任务来源优先级更正 + 无任务不 push 的边界；版本 0.1.4。 |
| `.trellis/spec/platforms/dsh-workflow-behavior.md` | 跳过词按 turn 的契约、push 任务来源顺序。 |
| `package.json`、`lib/client.js` | 版本 `0.1.4`；`pnpm run build:client` 重建，diff 仅 `PLUGIN_VERSION`，sourcemap 逐字节相同。 |
| 测试 | `test/breadcrumb-skip-turn.test.js`（真实 AgentLoop）、`test/session-composer.test.js`（+3）、`test/index.test.js`（+1）。 |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | **362 tests / 358 pass / 0 fail / 4 skip**（skip 均为 alpha 宿主 API 门槛用例，与 10-21/10-22 记录一致） |
| 真实 AgentLoop 回归（`test/breadcrumb-skip-turn.test.js`） | 修复前该用例在“同一 turn 的 step 2”断言失败（实际注入 `breadcrumb`+`bootstrap`）；修复后通过：turn 内多 step 全程静默、下一 turn 恢复注入、项目 `skip_keyword` 同样按轮、跳过期间 `dsh.dispatch_mode` 引导仍写入、注入后后续 step 不重复 |
| S1 真实会话（0.1.4，跳过词，`session-e970b321`） | turn 1 共 4 个 step（3 次工具调用 + 最终回答），`dsh-trellis` 用户消息 **0 条**；同一轮内 `.trellis/config.yaml` 仍补上了 `dsh: dispatch_mode: inline`（跳过不影响项目引导） |
| S1 真实会话（0.1.4，`--session-id` 续同会话第二问） | turn 2 step 1 注入 1 条 `breadcrumb` + 1 条 `bootstrap`（seq 51/52）；跳过不粘滞，bootstrap 只在真正未被跳过的那轮补一次 |
| S1 真实会话对照（0.1.4，无跳过词，`session-cdb7334c`） | turn 1 共 **13 个 step**，全程仅 1 条 `breadcrumb` + 1 条 `bootstrap`（step 1 注入，后续 step 不重复；projection 去重未被本轮改动破坏） |
| S1 真实会话回归对照（0.1.3，同样提示词，`session-20bf2c90`） | 同一提示词下 4 个 step，step 2 注入 `breadcrumb`+`bootstrap` —— 修复前行为复现 |
| 会话日志 | `/tmp/skip-e2e/home/sessions/--tmp-skip-e2e-proj--/`（三个 session 目录，`zstd -dc .../session.v4.jsonl.zstd`） |

## 已知边界与未覆盖

- 端到端临时 profile 里 DSH 的 bash 工具多数调用在子进程 bootstrap 阶段失败
  （`subprocess scope exited before its bootstrap consumed the launch request`）。同一临时
  profile 搭建方式下 0.1.3 会话出现**完全相同**的失败（3/3），控制组 19 次调用里另有 1 次成功，
  因此这是临时 `DSH_HOME`/profile 的宿主环境现象，不是本轮改动引入的；失败的调用仍产生 tool/result
  并推进 step，正好构成多 step 回合，不影响注入取证。宿主真实 profile 与当前 GUI 会话下 bash 正常。
- 临时 profile 端到端未验证“同一轮内后到消息带跳过词”的转向场景；该路径由 composer/index 单测
  覆盖（turn 内任意 step 命中即从此静默）。
- 设置页重挂载（`mountRuntime`）会重建 composer，跳过记忆随之清空：同一轮内改配置这一极端场景下，
  已跳过 turn 的后续 step 可能重新注入一次。未修复，按边界记录。
- Web GUI（`~/.dsh/profiles/web`）仍安装 git 快照 0.1.3；本轮改动未提交，因此 GUI 需在提交/
  重装插件并重启 DSH 后才会生效。
- `test:compat` 未重跑（需要为每个历史宿主版本临时安装依赖）。新增代码只使用
  `agent/pre-step` payload 的既有 `turn` 字段：已用
  `npm pack @deepseek-ai/dsh-agent@0.1.5-rc.2` 核对最低支持宿主的
  `runtime-types.d.ts`（payload 含 `turn: number`，`messages` 同为“removed from the inbox
  for this step”），当前宿主 `0.2.1-rc.2` 同字段已在本仓库 `node_modules` 中核对；“宿主不
  提供 `turn`”的退化路径只对不受支持的宿主生效。
