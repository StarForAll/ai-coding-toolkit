# 本次验证证据索引

临时根：`/tmp/dsh-trellis-full-usage-audit-1023/`。**最终断言只使用 `evidence-final/`，不把早期 `evidence/` 的追加记录计数合入。** 每个 `.jsonl` 为本地模型请求和 DSH session event；`.stdout/.stderr` 为对应 CLI 调用原始输出。临时目录可能日后清理，任务目录另保存精简结果和核心复核脚本。

## 实验与证据

| 场景 | 文件（相对 evidence-final） | 断言与等级 |
| --- | --- | --- |
| 首会话/新进程恢复 | `r01-bootstrap.{jsonl,stdout}`、`r02-resume.{jsonl,stdout}` | 新会话 bootstrap/breadcrumb 各 1 次；恢复无重复 emitted message（R1） |
| skip 整轮 | `r03-skip.{jsonl,stdout}` | read 前后两个模型请求无插件消息（R1） |
| spec 首触与重试 | `r04-spec.*`、`r05-spec-repeat.*` | deny 携带正文后写入成功（R1） |
| spec 跨进程去重 | `r06-spec-resume.*` | 与 r05 同 session 的新进程写入无重复 FULL deny（R1） |
| inline guard/无效 wait | `r07-inline-guard.*`、`r08-invalid-wait.*` | 派发被拒且 child 未启动；未知 id fail-closed（R1） |
| 裸 profile | `r09-bare-smoke.*`、`r10-bare-write.*` | 无插件消息、工具目录无 trellis_wait、写入不经过 spec deny（R1） |
| headless 命令文本 | `r11-headless-text.*` | `/trellis-status` 原文进入模型，无 command/run（R1） |
| auto 子代理 push/wait | `r12-auto-child.*`、`r13-auto-child-repeat.*` | 两个 child 首请求各含唯一 push、role/spec/PRD；最后父请求含 subagent-settled notice（R1） |
| 状态变化 | `r14-state-initial.*`、`r15-state-{planning,in_progress,completed,reviewing}.*`、`r16-state-error.*`、`r17-state-stale.*` | 每次对应新 breadcrumb 的 status 正确，task_error/stale 不变成 no_task（R1） |
| 身份 | `r18-identity.*` | 实际 Bash start/current 共用同一 dsh_session-*（R1） |
| 非项目 | `r19-no-project.*` | 无插件消息（R1） |
| 默认 read | `r20-read-spec.*` | 不声明 Read 触发器时没有 spec-context（R1） |
| 最早命令 probe 夹具 | `r21-command-registry.*` | helper 未声明 inject commands，probe 报错；**不作产品结果**，由 x10 替代 |
| 显式 read 触发 | `r22-read-enabled.jsonl`、`x11-read-enabled.*` | 第二模型请求出现 spec-context，读取前没有（R1） |
| 真实命令注册表 | `r23-commands.jsonl`、`x10-command-registry.*` | 四次 command/run + command/done；前三 success、参数调用 error（R2），不冒称 UI 路由 |
| spec 变化/坏分片 | `x01-spec-seed.*`、`x02-spec-changed.*`、`x03-corrupt-shard.*` | 同 session 内容变更、新 hash、损坏后均重新 FULL（R1） |
| ticket | `x04-ticket-aged.*` | 人为将分片 ts 调旧，写入不阻断，下一请求含 spec-ticket（R1） |
| 并发 | `x05-concurrent-a.*`、`x06-concurrent-b.*` | 两个 CLI 同时运行，各自 FULL deny 后写入成功（R1） |
| 原生压缩 | `x07-native-compaction.*`、`compact-result.json` | DSH compactNow 实际替换选定 surface，12318 估算 token；后续 bootstrap/面包屑和 FULL spec 重教学（R1） |
| Trellis 更新 | `x08-trellis-update.*`、`x09-after-update.*` | 同版本 update Already up to date，更新后注入正常（R1），不代表跨版本升级 |
| Codex hook payload | `c01-bootstrap.*`、`c02-spec-first.*`、`c03-spec-repeat.*`、`c04-skip.*`、`codex-hook-results.json` | fresh hooks 输出 bootstrap、FULL deny、重复静默、skip 静默（R2）；清除了 DSH/generic 覆盖变量 |
| 最终事件断言 | `assertions.json` | 29 pass / 0 fail；检查的输入是原始事件而非模型自述 |
| 原始兼容失败复现 | `compat-native-original.out` | 原始两个用例 0 pass / 2 fail（R5） |
| 临时诊断后兼容集 | `compat-diagnostic-adjusted.out` | 正式权限执行：350 pass / 0 fail / 0 skip（R5）；仓库未应用修复 |

## 对应驱动与环境

- `project/`：fresh `trellis init --dsh --codex --user xzc --yes` 生成物；临时 `00-bootstrap-guidelines` 是 init 自带记录，非新开的开发任务。
- `auto-project-final/`：显式 `dsh.dispatch_mode:auto`，填入一个合成 curated spec manifest，用于 child push。
- `read-project/`：显式 `spec_injection.tools:[Read, Edit, Write]`，验证只读触发。
- `command-project/`：命令 handler 测试项目；真实 Web 输入路由未通过认证页，不纳入成功项。
- `dsh-home/profiles/{trellis-audit,bare-audit,web-audit}/`：只写 `/tmp` profile 配置，依赖只读指向当前安装包。未复制真实凭据或用户 patch。
- `local-adapter.mjs`：本地确定性 LlmAdapter；保存真实模型请求和 DSH session event，按场景发出真实 write/read/bash/subagent/trellis_wait 调用，不联网生成回答。
- `run-suite.mjs`：最终 24 个 DSH CLI 调用；`supplement.mjs`：spec/并发/压缩/更新/命令补充实验。
- `compact-driver.mjs` + `compact-overlay.yml`：使用当前宿主正式 API 创建合成 Agent 并调用 compactNow，写回正式 checkpoint；没有手工伪造 compaction/end。
- `verify-evidence.mjs`：29 项实际事件断言；`run-codex-hooks.py`：fresh Codex payload 直调和四项断言。
- `/tmp/dsh-trellis-compat-0.2.1-rc.2-YOjjL4/`：兼容脚本安装的精确 host fixture；其中 `test/native-subagent-push.test.js` 有临时诊断日志和 user factory/source 调整，仅用于根因证明，不是产品修复。

## 本任务目录持久化摘要

- `evidence-summary.json`：安装包核心哈希、最终主批次/补充实验退出结果、29 项断言摘要及压缩结果。
- `verify-evidence.mjs`：实际使用的事件断言脚本副本，仅读取临时证据，不修改源码。
- `compat-native-original.out`、`compat-diagnostic-adjusted-tail.out`：原始两例失败与调整后完整集的计数。
- `upstream-boundary.diff`：最终上游 `.gitignore` 意外变化；未还原，不能宣称上游工作树全程不变。
- `post-fix-review.md`：修复后独立审查结论、复跑结果、故障对照和最终关闭边界。
- `post-fix-default.out`、`post-fix-compat.out`：本轮独立执行默认测试与精确 `0.2.1-rc.2` 兼容测试的完整输出。
- `post-fix-controls.json`、`post-fix-control-*.out`：三组临时故障对照的摘要与断言输出；退出 1 是预期故障被检出的结果。

## 解释限制

1. R1 使用确定性本地适配器，证明宿主集成、消息/工具顺序和状态，不证明真实 LLM 会主动遵守 Trellis。
2. 原始兼容失败和临时诊断证据仍保留为历史记录；F1 随后由外部会话修复，已用 `post-fix-*` 的独立复跑关闭，不能把临时诊断通过冒充正式修复验证。
3. Web root 实际显示 `dsh web authentication required; reopen the URL printed by dsh web.`；未读 token、未绕过认证，UI 未验收。
4. 最早 Node 子进程批次有空 stdout，但本地日志有实际执行记录；最终批次与计数通过 session/final/事件断言单独确定。
