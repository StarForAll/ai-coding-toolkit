# 证据索引：已安装 dsh-trellis 对等性复验（2026-10-23）

- 证据根：`/tmp/dsh-trellis-reverify-1023/`
  - `home/`：隔离 DSH_HOME（`trellis-headless` 装已安装副本 0.1.6；`bare-headless` 无插件）
  - `evidence/`：本索引引用的 stdout/err/会话导出/脚本
  - `proj/`、`auto/`、`nogit/`、`ticket/`、`update/`、`custom/`、`compact/`、`plain/`：临时 Trellis 项目及其变体
- 会话日志：`/tmp/dsh-trellis-reverify-1023/home/sessions/<project-key>/<session-id>/session.v4.jsonl.zstd`
- 查看工具：`python3 harness/sessions.py --evidence evidence/<name>.jsonl [--tools|--all]`（需 `DSH_HOME=/tmp/dsh-trellis-reverify-1023/home`）

## 证据等级

| 级别 | 含义 | 本轮代表 |
| --- | --- | --- |
| S1 | 真实 DSH/Codex 会话（真实 LLM + 真实工具调用） | 绝大多数场景 |
| S2 | 直载已安装副本模块/路由/命令处理器 | `s2-modules.mjs` |
| S3 | 源码/模板/脚本/宿主 API 契约比对 | `h04-host-upstream.out`、diff |
| S4 | 单测 | `s4-unit.out` |

## 场景 → 证据

| 场景 | 断言/结果 | 证据 | 等级 |
| --- | --- | --- | --- |
| S01 no_task | 新会话注入 bootstrap + no_task 面包屑（含 `<dsh-mode>` inline） | `evidence/s01-notask.jsonl`；session `session-ba690d54…` seq10/11 | S1 |
| S01b resume | 同 session 新进程续跑，bootstrap/面包屑不重复 | `evidence/s01b-resume.jsonl`；同一 session 仅 seq10/11 两条插件消息 | S1 |
| S02 planning | `task.py create` 绑定 `dsh_<sid>` 后注入 `planning-inline` | `evidence/s02b-planning.jsonl` seq52 | S1 |
| S02 in_progress | `task.py start --allow-empty-context` 后注入 `in_progress-inline` | `evidence/s02c-inprogress.jsonl` seq64 | S1 |
| S02 completed | task.json status=completed 时注入 `completed` + banner | `evidence/s02d-completed.jsonl` seq76 | S1 |
| S02 task_error | task.json 损坏时注入 task_error 专用修复文案 | `evidence/s02-error.jsonl` seq30 | S1 |
| S02 stale | 指针指向不存在目录时注入 stale 专用文案 | `evidence/s02-stale.jsonl` seq30（该轮模型调用遇 QUOTA，注入仍发生） | S1 |
| S03 spec deny-once | 写 `src/app.js` 首次 deny，reason 含 spec 正文 + sha256；重试成功 | `evidence/s03-spec.jsonl`；shard `session-e8496151…json` | S1 |
| S03b 静默窗口 | 同 session 再写 `src/b.js` 不再 deny | `evidence/s03b-window.jsonl`（3 次 write 仅 1 次 deny） | S1 |
| S03c spec 刷新 | 修改 spec 后写 `src/c.js` 重新 FULL deny（新 sha `fecd16b5…`） | `evidence/s03c-refresh.jsonl` | S1 |
| S04 子代理 push | auto 模式下 `trellis-agent-implement` 首个 pre-step 收到角色契约 + curated context；子会话无 breadcrumb/bootstrap | `evidence/s04-push.jsonl` 父；子 session `ab43213c…` seq12 form=subagent-context role=implement | S1 |
| S05 inline 守卫 | inline + 活跃任务派发 implement → deny，提示用户改配置/`inline_allow_dispatch` | `evidence/s05-guard-inline.jsonl` | S1 |
| S05 auto 无任务守卫 | auto + 无任务派发 implement → fail-closed deny，子代理未启动 | `evidence/s05-guard-auto-notask.jsonl` | S1 |
| S06 research 放行 | 无任务 research 可派发，父会话收到位置提醒；`trellis_wait` 正常返回 completed + unverified 提醒 | `evidence/s06-research.jsonl`；child `d7e6d124…` | S1 |
| S06 话题型不误判 | description 仅提及角色名 → 不推送、不守卫 | `evidence/s06-generic.jsonl`；child `adf3a4a6…` 无 push | S1 |
| S07 子目录 | cwd=`proj/src` + `d.js` → 命中 spec 并 deny；合规重试 | `evidence/s07-subdir.jsonl` | S1 |
| S07 Read ticket | `tools:[Read]` 时 read 不阻断，post-execute 送达 `form=spec-context` | `evidence/s07-read-ticket.jsonl` seq28 | S1 |
| S07 edit | `edit` 工具同样被 deny 并携带 spec | `evidence/s07-edit.jsonl` | S1 |
| S07 损坏分片 | 分片写成非法 JSON 后下一次触碰重新 FULL deny（安全回退） | `evidence/s07-corrupt.jsonl` + `s07-corrupt2.jsonl`（deny 计数 2） | S1 |
| S07 无效 wait | 不存在的 child id → 明确拒绝 | `evidence/s07-wait-invalid.jsonl` | S1 |
| S08 plain | 非 Trellis 目录 0 条 dsh-trellis 消息 | `evidence/s08-plain.jsonl` | S1 |
| S08 no-git | 无 `.git` 的 Trellis 项目仍注入 | `evidence/s08-nogit.jsonl` | S1 |
| S08 skip | `no-trellis` 独立词整轮跳过 | `evidence/s08-skip.jsonl`（0 条插件消息） | S1 |
| S09 auto | 显式 auto：面包屑为 `in_progress`（无 `-inline`）、无 `<dsh-mode>` banner | `evidence/s09-auto.jsonl`、`s04-push.jsonl` seq30 | S1 |
| S09 不写配置 | 全轮会话后 `.trellis/config.yaml` sha256 不变，无 `dsh:` 段 | `evidence/config-before.sha` 与 `h04-host-upstream.out` | S1/S3 |
| S10 身份 | 模型 shell 内 `CTX=dsh_session-<sid>`、`SID=session-<sid>`、`DSH_SHELL=1` | `evidence/s10-identity2.jsonl` | S1 |
| S10b 身份→任务 | 绑定后 `task.py current --json` 返回该 session 的任务（source=`session:dsh_session-…`） | `evidence/s10b-identity.jsonl` | S1 |
| S12 并发 | 两会话并行写不同文件，各自一次 deny 后合规；4 个独立分片 | `evidence/s12-conc-a/b.jsonl`；`proj/.trellis/.runtime/spec-inject/` | S1 |
| S13 compaction | 24k 窗口真实触发 2 次 compaction；压缩后 breadcrumb + bootstrap 重新注入 | `evidence/s13-compact.jsonl`（`compaction/start/end`；seq39/40 重注入） | S1 |
| S13b 极端边界 | 24k 窗口 + 40KB read + spec deny 反复 compaction/deny，首轮 420s 超时未完成 | `evidence/s13b-spec-reset.jsonl`（132KB，无 final）、`s13b-write2.jsonl`；见报告边界观察 | S1（边界） |
| S14 升级 | `trellis update --skip-all` 后（已是最新）面包屑/bootstrap 正常 | `evidence/s14-update.jsonl` | S1 |
| S15 自定义状态 | 自定义 `[workflow-state:reviewing]` 块被渲染 | `evidence/s15-custom2.jsonl` seq29 | S1 |
| S15 tdd 模板 | registry 不可达，无法切换 tdd 模板（记录限制） | `evidence/s15-tdd.jsonl` + 命令 stderr | S1（失败） |
| S16 headless 命令 | 文本 `/trellis-status` 未走命令通道；模型自行拼装并错误声称“插件未安装” | `evidence/s16-headless-command.jsonl` final + 命令历史 | S1 |
| B02 裸用 spec | 无插件时 write 静默成功，文件违反 spec（无 `// demo-spec-applied`） | `evidence/b02-spec-bare.jsonl`；`proj/src/bare.js` | S1 |
| B03 裸用子代理 | 无插件时 implement 子代理可启动，无 push/无守卫 | `evidence/b03-subagent-bare.jsonl`；child `6a36136a…` | S1 |
| B04 裸用身份 | 无插件时 `DSH_TRELLIS_CONTEXT_ID` 为空；`task.py current` 无会话任务 | `evidence/b04-identity-bare.jsonl` | S1 |
| C01 Codex bootstrap | 隔离 CODEX_HOME + 项目 trust + hook trust bypass 后，`codex exec` 真实注入 bootstrap/codex-mode/workflow-state | `evidence/c01-codex2.jsonl`；rollout `codex-home/sessions/2026/10/23/rollout-2026-10-23T16-16-13-…jsonl` | S1 |
| C02 Codex spec | 真实 `apply_patch` 被 PreToolUse 阻断，注入 `<spec-context sha256>` 后重试成功 | `evidence/c02-codex.jsonl`；rollout `…16-16-34-…jsonl` ord53/54 | S1 |
| C03 Codex 子代理 | 真实 `spawn_agent` 子代理收到 SubagentStart 注入的角色契约 | `evidence/c03-codex-subagent.jsonl`；rollout `…16-19-59-01a167d8…jsonl` | S1 |
| M01 命令 | 已安装副本注册 `/trellis-status`、`/trellis-finish`、`/trellis-doctor`；带参数拒绝；非 Trellis 目录报错；doctor 输出完整 | `evidence/s2-modules.out` | S2 |
| M02 冲突/版本 | 冲突决策 checked/unavailable/duplicate 正确；doctor 显示重复插件；版本路由 200（repo feed stub、npm dist-tags） | `evidence/s2-modules.out` | S2 |
| M04 安装态文档 | 已安装 0.1.6 README 无“headless 文本限制”“避免同会话中途切换”（源码 0.1.7 有） | `evidence/h04-host-upstream.out` | S3 |
| S4 单测 | 350 tests / 346 pass / 0 fail / 4 skip | `evidence/s4-unit.out` | S4 |
| S3 宿主契约 | 插件使用的 5 个事件在 DSH 0.2.1-rc.2 均存在；peer range 覆盖 0.2.1-rc.2 | `evidence/h04-host-upstream.out` | S3 |
| O2 上游契约 | `get_context.py --step 2.1 --platform dsh` 仍输出“without trellis_wait … run_in_background: false”（DSH 已移除该参数） | `evidence/h04-host-upstream.out` | S3 |

## 更新后复验（0.1.7）

| 场景 | 结果 | 证据 | 等级 |
| --- | --- | --- | --- |
| u01 no_task | 0.1.7 安装副本仍注入 bootstrap + no_task 面包屑 | `evidence/u01-smoke.jsonl` | S1 |
| u02 spec | 写 `src/u02.js` 首次 deny（count=1） | `evidence/u02-spec.jsonl` | S1 |
| u03 inline 守卫 | 任务 session 派发 implement → inline deny | `evidence/u03-guard.jsonl` | S1 |
| u04 auto push | child 首步 `form=subagent-context role=implement` + 角色契约 + curated context | `evidence/u04-push.jsonl`；child `1b07c131…` | S1 |
| u05 headless 命令 | `/trellis-status` 未路由；模型称"命令未注册"并直接读状态，未再称"插件未安装" | `evidence/u05-headless-command.jsonl` | S1 |
| u02 S2 | 已安装 0.1.7 直载：doctor 版本 0.1.7、命令注册、冲突 duplicate、版本路由 200 | `evidence/u02-s2-modules.out` | S2 |

## 未产出/失败证据

- `evidence/s02-planning.jsonl`、`s10-identity.jsonl`、`s05-guard-notask.jsonl`：早期夹具/命令问题（错误 context key、缺 `dsh-bash-local`、inline 优先于 no_task 守卫）导致无效或部分无效，已由后续场景替代，不作为结论依据。
- `s15-tdd`：registry 网络不可达，模板未切换。
- `s13b-*`：极端 24k 窗口实验，会话未完成；只作为边界观察。
- 本轮最后一条真实会话（s02-stale）模型调用遇 `QUOTA: Insufficient Balance`，但注入发生在模型调用前，故该条 S1 注入证据仍有效；后续未再消耗 LLM。
