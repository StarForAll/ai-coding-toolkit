# dsh-trellis 平台能力对标全面验证

## Goal

验证当前已安装的 `dsh-trellis`（0.3.7，装在 `~/.dsh/profiles/web`，符号链接到本仓库
`dsh-plugins/dsh-trellis`）能否达到 Codex 使用 Trellis 的同等效果、补足 DSH 平台使用
Trellis 的不足；实地复现并判定探针 A 报告的 workflow-state 解析缺陷是否真实、影响面多大；
输出经实际执行证据支撑的问题清单，等待用户确认后才进入修复。

## Requirements

1. 结论必须来自实际执行（读取真实文件、运行真实解析器、运行真实 DSH 会话、抓取真实注入
   消息），不以插件文档、测试通过或第三方转述作为唯一依据。
2. 覆盖插件对外声明的全部能力面：每轮 workflow-state 提示、bootstrap、spec 路径注入、
   子代理上下文推送、dispatch 守卫、命令面、doctor、设置页/上游监控、冲突检测、wait 工具。
3. 探针 A 判定必须给出：复现脚本与输出、真实字节/行数测量、与 Codex/Claude Python hook
   同文件解析结果对比、以及"哪些状态被污染、影响到哪些下游使用方"的影响面结论。
4. 端到端验证使用 `/tmp` 下临时 Trellis 项目 + 真实 DSH 进程；不以单元测试代替端到端。
5. 验证阶段只做取证，不修改插件源码；发现问题后先交付问题清单与证据，等待用户
   逐项确认。确认后在同一任务内实施修复并回归验证。
6. 验证与修复产生的文件只落在本任务目录、`dsh-plugins/dsh-trellis` 与 `/tmp` 临时目录。

## Constraints

- 不得为了"干净工作区"丢弃未提交内容（`dsh-plugins/` 与 `docs/capability-inventory.md`
  当前未提交）。
- 运行 DSH 真实会话时使用独立 `DSH_HOME`/临时 profile，避免污染用户现有 web profile。
- 凭据不出现在命令、日志与输出中。

## Acceptance Criteria

- [x] 探针 A 判定为真实，附复现命令与实测数据（`report.md` §2 P0-1）。
- [x] 逐状态给出插件与 Codex hook 的 body 行数/字符对照表（`findings/state-breadcrumb.md` §1）。
- [x] 给出真实 DSH 会话中模型收到的 breadcrumb/bootstrap/spec/子代理消息取证（`findings/e2e-session.md`）。
- [x] 列出确认存在、验证通过、无法验证三类条目（`report.md` §2–4）。
- [x] 用户确认修复范围后完成 0.3.8 修复与回归（`report.md` §5、`docs/validation-0.3.8-local.md`）。
