# 执行计划：已安装 dsh-trellis 对等性与补足独立复验

> 状态（2026-10-23）：**验证已完成，等待用户确认问题与修复方案**。
> 报告：`research/verification-report.md`；证据索引：`research/evidence-index.md`。
> 结论（0.1.7 最新）：主链路达到 Codex 同等效果、补足裸 DSH 主要缺口；无 P0/P1/P2。F1a/F3a 文档滞后已随手动更新关闭；仍存在 F1b（headless 无命令通道，宿主限制）与 F2（headless profile 无插件，环境选择）；F3b 未变。
> 已执行：0（基线）、1（隔离环境）、2（临时项目/夹具）、3（S1 主链路）、4（裸用对照）、5（Codex 真实 exec/hook）、6（S2 模块）、7（S3 宿主/上游契约）、8.1–8.3（报告/索引/自检）。
> 未完成：8.4 之后的修复动作（按闸门等待用户确认）；Web GUI/TUI 实机、tdd 模板（网络）、Windows 未覆盖。
> 闸门：验证阶段零仓库修改（`git status` 仅本任务目录 + 用户既有两个未跟踪文件）；修复须另经用户逐项确认。
>
> **2026-10-23 用户决定**：不做自动修复；用户已**手动更新已安装插件到 0.1.7**。更新后复验已完成（§11 of verification-report）。复验覆盖：
> 1. web profile 已安装版本号、`lib/` 与源码 diff、README 是否含 headless/模式切换文档；
> 2. S1 回归：bootstrap/面包屑、spec deny-once/窗口、子代理 push/guard、auto 模式、身份；
> 3. S16 类 headless `/trellis-status` 是否仍产生“插件未安装”错误声明；
> 4. 将更新前后差异写入本任务报告，并据此重判 F1/F3。
> 复验结果：u01–u05 + S2 全通过；F1a/F3a 关闭，F1b（宿主限制）与 F2（headless profile 无插件）仍存在；无回归。

## 0. 基线与闸门（S3，约 15 分钟）

- [ ] 0.1 记录版本：`dsh --version`、`trellis --version`、`codex --version`、`node --version`。
- [ ] 0.2 安装态取证：
  ```bash
  diff -rq dsh-plugins/dsh-trellis/lib ~/.dsh/profiles/web/node_modules/dsh-trellis/lib
  diff -rq dsh-plugins/dsh-trellis ~/.dsh/profiles/web/node_modules/dsh-trellis --exclude=node_modules
  node -p "require('/home/xzc/.dsh/profiles/web/node_modules/dsh-trellis/package.json').version"
  ```
  记录 0.1.6↔0.1.7 的逐文件差异（预期：`client.js` 版本 stamp、README/package.json）。
- [ ] 0.3 `git status --porcelain` 记基线（预期仅用户既有两个未跟踪文件）。
- [ ] 0.4 明确被测实体：隔离 profile 中 `dsh-trellis` = 复制自 web 已安装副本，运行前 diff 一致性。

## 1. 隔离环境与 harness（约 30 分钟）

- [ ] 1.1 建 `/tmp/dsh-trellis-reverify-1023/{home,evidence,harness,proj}`。
- [ ] 1.2 复用已证明可用的隔离 profile 骨架（`/tmp/dsh-trellis-audit-1023/home-final/profiles/trellis-headless`，含 base/headless/插件依赖的完整 node_modules），复制到新 home；把 `node_modules/dsh-trellis` 替换为**真实 web 安装副本**并 diff 证明一致。
- [ ] 1.3 建 `bare-headless`：同一 profile 去掉 `dsh-trellis` bundle 与 `node_modules/dsh-trellis`，用于裸用对照。
- [ ] 1.4 写 `harness/run.sh`：
  - `DSH_HOME=/tmp/dsh-trellis-reverify-1023/home`；
  - `DEEPSEEK_API_KEY` 仅从 `~/.dsh/.credentials.yaml` 的 `refs` 取名注入环境，不 echo、不进 argv；
  - `dsh --profile <p> --json [--session-id <sid>] "<prompt>"`，stdout/err 分文件，`timeout 300`。
- [ ] 1.5 冒烟：`bare-headless` 与 `trellis-headless` 各跑一次极短任务，确认 LLM 可答、插件消息出现。

## 2. 临时项目与夹具（约 30 分钟）

- [ ] 2.1 `proj`：`git init` + `trellis init --codex --dsh -y -u xzc`；确认 `.agents/skills`、`.dsh/skills`、`.dsh/DSH.md`、`.trellis/` 齐全。
- [ ] 2.2 建 spec 夹具：在 `.trellis/spec/` 写入带路径匹配的测试规范（要求目标文件首行含 `// demo-spec-applied`），验证插件 spec 索引能命中。
- [ ] 2.3 建任务夹具：`task.py create` + 空 jsonl + `task.py start --allow-empty-context`；记录任务目录与指针。
- [ ] 2.4 派生项目：`plain`（非 Trellis）、`nogit`（无 .git 的 Trellis）、`subdir`（子目录会话）、`auto`（config 显式 auto）、`tdd`（`--workflow tdd`）、`update`（升级用）、`conflict`（duplicate 插件）。
- [ ] 2.5 记录每个项目的 `.trellis/config.yaml` 关键项（`dsh.dispatch_mode`、`spec_injection`、`context_injection`）作为断言输入。

## 3. S1 主链路（约 2–3 小时，按场景批跑）

> 每个场景保存 `evidence/<id>.jsonl` + `.err`；断言以 `--json` 事件流（`source.kind=dsh-trellis`、tool deny/result、subagent 事件）、`.trellis/.runtime/**` 文件、`git status` 为准；模型自述只作线索。

- [ ] S01 bootstrap/no_task：新会话首轮出现 bootstrap + no_task 面包屑；第二轮不重复；`no-trellis` 轮跳过。
- [ ] S02 状态链：create → planning；start → in_progress（inline 状态名）；finish → completed；无状态变化不重复。
- [ ] S03 spec deny-once：写 `src/app.js` 首次 deny（reason 含 spec 正文 + sha）→ 读 spec → 重试成功；窗口内 `src/b.js` 不 deny；改 spec 后 `src/c.js` 重新 FULL deny。
- [ ] S04 子代理 push + 子代理 spec：真实派发 `trellis-agent-implement`（首行 `Active task:`），子代理首步收到角色契约 + curated context；子代理写文件被 deny 后按 spec 重试。
- [ ] S05 守卫：no_task 下 implement/check 被拒且子代理未启动；inline 下声明式派发被拒并给出出路；research 放行 + 父会话位置提醒。
- [ ] S06 角色识别：首行前缀、`Role:` 行、严格 description 前缀、话题型 description、路径提及 5 变体。
- [ ] S07 spec 变体：子目录 cwd、`tools: [Read]`、大写工具名、`refresh_window_seconds`/`max_spec_chars`、损坏分片回退。
- [ ] S08 零干扰：plain 目录 0 条插件消息；nogit Trellis 正常注入。
- [ ] S09 模式：fresh 项目首会话后 `git status` 干净；默认 banner；auto 下无 banner、状态名无 `-inline`、派发链路通。
- [ ] S10 身份：会话内 `echo $DSH_TRELLIS_CONTEXT_ID` 与 `task.py current` 指针一致；命令子进程同身份；子代理转发身份。
- [ ] S11 resume：`--session-id` 恢复后 bootstrap/projection 行为、spec 分片持久化、去重与 README 声明一致性。
- [ ] S12 并发：两会话并行写不同文件，`.runtime/spec-inject/*.json` 分片互不串扰。
- [ ] S13 compaction：优先尝试真实 compaction；不可行则 S2 直载 `compaction/end` 处理器验证内存+磁盘重置，S4 单测补偿，明确记录限制。
- [ ] S14 升级：`trellis update --skip-all` 后主链路复测；managed-file 漂移/冲突记录。
- [ ] S15 工作流变体与自定义状态：`--workflow tdd` 或任务级 workflow 的块选择；自定义 `[workflow-state:*]` 渲染。

## 4. 裸用对照（S1 抽样，约 40 分钟）

- [ ] B01 no_task：无 bootstrap/面包屑。
- [ ] B02 spec：写文件静默成功、违反 spec（无 deny）。
- [ ] B03 子代理：无 push/守卫，子代理自行 pull 或空跑。
- [ ] B04 身份/命令：无托管身份、无 `/trellis-*` 命令。

## 5. Codex 对照（约 60 分钟）

- [ ] C01 隔离 `CODEX_HOME`（复制 `~/.codex`，不读取内容）+ 项目 trust + `[features] hooks=true`，`codex exec` 试触发 UserPromptSubmit / PreToolUse / SubagentStart；成功则逐项对照。
- [ ] C02 若自动触发仍失败：用真实 hook payload 直调三脚本（S2），记录已尝试配置与限制，不伪造 S1。
- [ ] C03 对照 Codex 的 bootstrap 频率、spec deny reason、SubagentStart 注入内容、stale 行为与插件差异。

## 6. 命令/运维/模块（S2+S4，约 60 分钟）

- [ ] M01 直载已安装副本：`/trellis-status`、`/trellis-finish`、`/trellis-doctor` 注册与输出、拒参数、非 Trellis 提示。
- [ ] M02 设置页/版本监控/冲突：直载 host 路由与 client 决策函数；`conflict` profile 下 doctor/冲突路由输出；duplicate 挂载不自动禁用。
- [ ] M03 单测：`cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"`；如可行对安装副本跑同套测试；必要时 `node scripts/test-compat.mjs`。
- [ ] M04 headless 命令面限制复测：纯文本 `/trellis-status` 是否被当任务解释、是否产生失实声明（对照 README 0.1.6/0.1.7 文档差异）。

## 7. 宿主/上游契约（S3，约 45 分钟）

- [ ] H01 在 DSH 0.2.1-rc.2 中核对插件使用的服务/事件（`agent/pre-step`、`tools/pre-execute|post-execute`、`compaction/end`、`subagent/end`、`commands`、`settings.section`、`webServer`、`loader`）仍存在且语义未变；peerDependencies 满足。
- [ ] H02 检查宿主新增能力是否有插件未利用且影响体验的（列观察，不轻易立项）。
- [ ] H03 核对 Trellis 0.7.0-beta.4 的 DSH 契约：`get_context.py --platform dsh`、`task.py current --json`、`workflow.md` 状态块、`.dsh/` 模板、`trellis update` 读取逻辑；O2（`run_in_background` 过期指引）按只读政策仅记录。
- [ ] H04 安装/升级形态：git path 安装、`lib/client.js` bundle 存在且版本一致、headless profile 无插件的现实覆盖与影响。

## 8. 汇总、证据索引与闸门（约 45 分钟）

- [ ] 8.1 写 `research/evidence-index.md`：场景 → 命令 → 证据文件 → 断言 → 等级。
- [ ] 8.2 写 `research/verification-report.md`：结论摘要、三臂矩阵、补足评估、问题清单（P/X/H/O）、未覆盖项与补偿。
- [ ] 8.3 逐条自检 R1–R11 与验收标准；`git status --porcelain` 证明仓库零改动。
- [ ] 8.4 向用户提交问题清单 + 执行方案（含推荐项与取舍），**停止等待确认**；确认后才进入修复。

## 验证命令速查

```bash
# S1 会话（示例）
DSH_HOME=/tmp/dsh-trellis-reverify-1023/home \
  dsh --profile trellis-headless --json --session-id <sid> "<prompt>" > evidence/<id>.jsonl 2> evidence/<id>.err

# 裸用对照
DSH_HOME=/tmp/dsh-trellis-reverify-1023/home dsh --profile bare-headless --json "<prompt>"

# Codex 对照
CODEX_HOME=/tmp/dsh-trellis-reverify-1023/codex-home codex exec --json --cd /tmp/dsh-trellis-reverify-1023/proj "<prompt>"

# 单测
cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"

# 安装态一致性
diff -rq dsh-plugins/dsh-trellis/lib ~/.dsh/profiles/web/node_modules/dsh-trellis/lib
```

## 回滚点

- 验证阶段无仓库改动，无需回滚；`/tmp/dsh-trellis-reverify-1023/` 可整体删除。
- 若进入修复：每项独立 commit/可 revert；提交与推送另行请示。

## 风险与停点

- 真实会话单次 30–300 秒，若 LLM/网络异常，记录失败并重试一次；不无限重试。
- spec 夹具必须能被插件索引命中，否则先修夹具（属实验区，不算产品修复）。
- 若发现 P0/P1，立即在报告中置顶并暂停其余低优先级场景，先向用户报告。
