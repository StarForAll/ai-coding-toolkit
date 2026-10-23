# 执行计划：已安装 dsh-trellis 0.1.6 全面验证

> **进度（2026-10-23）**：A/B/C/D 全部执行完毕，E1/E2 已完成（见 `research/verification-report.md`）；**E3 闸门生效——等待用户确认 F1/F2/F3 处置方案**。验证阶段零仓库改动。

## A. 准备（S3 基线）✅

- [ ] A1 复查安装态：web profile 版本与 lib 一致性 diff；headless/tui 等 profile 插件清点；记录 DSH/Trellis/Codex 版本。
- [ ] A2 建立隔离环境：`/tmp/dsh-trellis-016-verify/{home,evidence,proj}`；隔离 DSH_HOME 下创建测试 profile 并从 `dsh-plugins/dsh-trellis`（0.1.6）安装；安装后 diff 证明与真实 web 副本一致。
- [ ] A3 建临时 Trellis 项目：`trellis init --codex --dsh`（含派生：fresh-no-config、nogit、subdir 会话用例、mode-auto 用例、update 用例）。
- [ ] A4 通读上游 Trellis 0.7.0-beta.4 的 DSH 面（`packages/` 内模板/脚本/get_context.py --platform dsh）与 Codex hook 源，形成对照检查单（只读）。

## B. 真实会话验证（S1，DSH 侧）

- [ ] B1 V2 面包屑：no_task → 建任务(planning) → start(in_progress) → finish(completed) 全状态；未变不重复；`no-trellis` skip turn 级；非 Trellis 目录零注入。
- [ ] B2 V3 bootstrap：新会话首次 no_task 提醒一次；同会话后续不重复；子代理不收 bootstrap。
- [ ] B3 V4 身份：会话内 `task.py current` 解析到指针；命令子进程同身份；子代理转发身份优先。
- [ ] B4 V5/V6 子代理：implement/check/research 各一次成功 push（角色契约 + curated context，`Active task:` 首行）；C1 回归——generic 子代理（prompt 提及角色路径/话题型 description）不触发 push/守卫；无任务 implement/check 被守卫拒绝；research 收到位置提醒。
- [ ] B5 V7 trellis_wait：后台派发 → 主会话独立工作 → wait 汇合成功；再跑一次故意失败子代理验证 fail-closed 结论。
- [ ] B6 V8 spec 注入：根目录 edit deny-once → ticket → refresh 窗口；子目录 cwd 相对路径（C2 回归）；read 不阻断只补正文；分片持久化 + 损坏回退（S2 辅助）；compaction 重置。
- [ ] B7 V9 模式：fresh 项目首次会话后 `git status` 证明 config 未被写（C3 回归）；inline banner 出现；显式 auto 配置下派发链路通；`.dsh` 单独存在时 `task.py start` 闸门提示。
- [ ] B8 V10 命令：`/trellis-status`、`/trellis-finish` 真实调用（零输入、带参数拒绝）；非 Trellis 项目调用提示。
- [ ] B9 V12 升级：`trellis update --skip-all` 后面包屑/命令/守卫仍工作。
- [ ] B10 V15 并发/resume：两会话并发 spec 分片互不串扰；`--session-id` resume 后注入去重行为。
- [ ] B11 V16 裸用对照：同一隔离 home 下无插件 profile 跑 2–3 个关键场景（no_task 引导缺失、子代理无 push、spec 无注入），取证差距清单。

## C. 对照基线（S1，Codex 侧 + Trellis 原生）

- [ ] C1 V13 Codex：同项目 `codex exec`——无任务轮 bootstrap、状态面包屑、edit 的 PreToolUse deny-once、SubagentStart push（父有/无任务）、stale；hook 日志留证。
- [ ] C2 V14 原生 pull：`.agents/skills`、`.dsh/skills`、`.dsh/DSH.md` 资产齐全性；`get_context.py --mode phase --platform dsh` 输出；child-pull 路径在插件 push 后仍不冲突（B4 中子代理同时验证）。

## D. 模块与单测（S2/S4）

- [ ] D1 直载已安装 web 副本模块：`/trellis-status`、`/trellis-finish`、`/trellis-doctor` 注册与输出；upstream/version-check 路由；conflicts 决策。
- [ ] D2 spec 决策函数：子目录并集、tools 大小写规范化、预算/降级。
- [ ] D3 单测：源码 `node --test "test/*.test.js"`（对照基线 350/346/0/4）；如可行对安装副本跑同套测试。

## E. 汇总与闸门

- [x] E1 写 `research/verification-report.md`：V1–V16 逐维度结果 + 证据等级 + 证据路径；对照矩阵；0.1.6 修复回归表（C1/C2/C3/C6/C7）；补足评估表（R5）。
- [x] E2 问题清单（F1/F2/F3 + O 系列边界）；无问题维度写具体结果（R10）。
- [x] E3 向用户提交问题清单 + 执行方案；用户已确认（F1/F2 补充文档说明、F3 保持现状）。
- [x] E4 实施确认的修复：文档 + 版本号变更（插件 README 两处 + 仓库 spec 两节 + 版本 0.1.6→0.1.7 + `docs/validation-0.1.7-local.md` + client bundle 版本 stamp 重印）；无 lib 逻辑/测试变更（`lib/` 仅 `client.js` 的 `PLUGIN_VERSION` 一行随构建变化）；单测回归 350/346/0/4。任务工件与插件变更的提交另行请示。

## 验证命令速查

```bash
# 隔离真实会话（示例）
DSH_HOME=/tmp/dsh-trellis-016-verify/home dsh --profile <test> --json --session-id <sid> "<task>"
# Codex 对照
codex exec --json --cd /tmp/dsh-trellis-016-verify/proj "<task>"
# 单测
cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"
# 一致性
diff -rq dsh-plugins/dsh-trellis/lib ~/.dsh/profiles/web/node_modules/dsh-trellis/lib
```

## 回滚点

- 验证阶段无仓库改动，无需回滚；`/tmp` 目录可整体删除。
- 修复阶段每项修复独立 commit/可 revert（获准提交后）。

## 当前闸门

**E3 之前禁止任何仓库代码/文档修改。**
