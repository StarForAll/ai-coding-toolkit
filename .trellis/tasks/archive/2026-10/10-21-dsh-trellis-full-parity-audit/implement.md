# Implement — dsh-trellis 全链路对等性审计

> 本计划只执行验证与取证；任何源码/profile 修复都不在本轮范围内。

## 0. 准备与护栏

- [ ] 记录基线：`git status --short --branch`、`dsh --version`、`trellis --version`、`codex --version`。
- [ ] 生成唯一时间戳 `TS`；建立 `/tmp/trellis-dsh-parity-$TS` 与 `/tmp/dsh-parity-home-$TS`。
- [ ] 复制/编写 harness：`mock-llm.mjs`、`run-scenario.sh`、`codex_compare.py`、断言脚本。
- [ ] 建立隔离 `DSH_HOME`：
  - [ ] `trellis-audit` profile（headless + mock provider + 插件软链）
  - [ ] `trellis-control` profile（同配置，不插插件）
- [ ] 确认 mock LLM 可被 DSH 调用（空场景 smoke：root 返回固定文本）。

## 1. 安装态与静态对齐（S0/S0b/S0c）

- [ ] 记录 profile package.json 中 dsh-trellis 来源、版本、启用状态。
- [ ] 对比安装目录与源码的 `lib/index.js`、`lib/client.js`、`cordis.patch.yml` sha256。
- [ ] 用 Node/semver 核对 peer/engines 对 `0.2.1-rc.2` 的覆盖；记录客户端版本标记。
- [ ] 运行 `pnpm test`，记录 pass/fail/skip；与历史基线对比。
- [ ] 逐项核对 DSH 0.2.1-rc.2 类型/服务（agent/pre-step、tools/pre-execute、tools/post-execute、subagent/end、session/event、workingDirectory、sessionProjections、shellEnv、commands）与插件用法，记录 file:line。

## 2. 临时项目与 Trellis 机制（S40/S42）

- [ ] `mkdir` 临时项目；`git init`；`trellis init --dsh --codex -y -u xzc`。
- [ ] 记录生成文件树、`.trellis/.version`、`.dsh/skills`、`.agents/skills`、AGENTS.md 的 Trellis 块。
- [ ] 真实执行 `task.py create/start/current --json/finish/archive`，记录输出与 jsonl 门禁行为。
- [ ] 记录 `dsh.dispatch_mode` 初始缺失状态；准备后续场景所需任务/变体/spec。

## 3. 工作流状态 E2E（S1–S14）

- [ ] S1/S2：新会话首轮/次轮；断言 bootstrap 一次、breadcrumb、`<dsh-mode>`、config 自动补键。
- [ ] S3/S4：planning / in_progress；断言 `*-inline` 与 task 行。
- [ ] S5/S6：completed / custom；断言不误报 no_task。
- [ ] S7/S8：stale / task_error；断言路径保留与修复提示。
- [ ] S9：三层 workflow 变体；逐层断言正文变化。
- [ ] S10：skip 关键字（项目级 + 插件级兜底）；断言 0 注入。
- [ ] S11/S12：inline 变体无块、auto 对照；断言横幅与基础块。
- [ ] S13：显式 auto / 只读 config / 无 config；断言不覆盖、不创建、失败降级。
- [ ] S14：非 Trellis 目录；断言 0 注入。
- [ ] 每个场景保存 `requests.jsonl`/`events.jsonl`/`stderr`/断言结果。

## 4. spec 注入 E2E（S15–S20）

- [ ] 准备 `.trellis/spec/demo/index.md`（frontmatter paths + 唯一 marker）与 `src/` 文件。
- [ ] S15：首次 write deny + spec 正文；重试成功；检查分片 JSON。
- [ ] S16：窗口内静默；把分片 ts 推旧后 ticket 出现。
- [ ] S17：`enabled: false` 无注入。
- [ ] S18：大写工具名、Read opt-in 的行为。
- [ ] S19：损坏分片重新 full。
- [ ] S20：Codex hook 同输入输出对照（含 deny/ticket 文案、预算）。

## 5. 子代理 / wait / 守卫 E2E（S21–S33）

- [ ] 准备任务 artifacts 与 `implement.jsonl`/`check.jsonl` 条目。
- [ ] S21/S22/S23：三种角色首步 push；断言角色契约、清单、artifacts、无 no_task。
- [ ] S23b：与 Codex research spec-tree context 对照。
- [ ] S24：generic child 静默。
- [ ] S25：删除 role skill 后的 fallback。
- [ ] S26/S27：无任务 implement/check deny、research 放行提醒。
- [ ] S28/S29：inline 守卫与逃生口。
- [ ] S30：child 运行中 wait → completed。
- [ ] S31：child 先结束再 wait；带 timeout，记录是否挂死/返回 inactive。
- [ ] S32：error/aborted 结算不误报。
- [ ] S33：两个 session 并发任务指针隔离。
- [ ] 保存 child 请求 messages、tool 结果、wait 输出。

## 6. 命令、身份、Web 面（S34–S39）

- [ ] S34：bash 打印三个身份变量；`task.py current --source` 对照。
- [ ] S35：用真实项目调用命令 handler（status/finish/doctor），记录输出与指针未变。
- [ ] S36：当前 Web GUI 输入只读命令，确认分发与 `recordInput: false`；不执行 finish-work。
- [ ] S37：浏览器打开 设置 → Trellis，核对唯一入口、字段、开关；不保存敏感/破坏性修改。
- [ ] S38：curl 冲突路由（same-origin）与版本检查合法/非法请求。
- [ ] S39：control profile 同场景对照，记录缺失的能力面。

## 7. Trellis/Codex 对照与更新（S20/S41/S43）

- [ ] 用真实 hook payload 跑 `.codex/hooks/inject-workflow-state.py`，对照各状态正文。
- [ ] 对照 bootstrap、implement/check/research 子代理 context。
- [ ] 在临时项目执行 `trellis update`（如可用），确认自动补的 `dsh.dispatch_mode` 保留、config 未被覆盖。
- [ ] 记录 `trellis platforms` / `.dsh/DSH.md` 与插件声明的差异。

## 8. 汇总与报告

- [ ] 将 E1 证据整理到 `findings/installed.md`、`state.md`、`spec.md`、`subagent.md`、`commands-web.md`、`codex.md`、`trellis.md`。
- [ ] 建立结论矩阵（Codex / DSH+插件 / 判定 / 证据）。
- [ ] 问题按 P0–P3 分级；每项含现象、复现、根因 file:line、影响、证据等级、建议方案/风险。
- [ ] 写明未验证边界与原因。
- [ ] 写 `report.md`，明确回答三个问题；没有问题时给出具体验证结果。
- [ ] 运行 `trellis-check` 自查；确认 `git status` 只新增任务产物、无源码/profile 改动。
- [ ] 清理 mock/临时 DSH 进程；保留临时目录供复核（或按用户要求删除）。

## 验证命令

```bash
git status --short --branch
dsh --version
trellis --version
codex --version
sha256sum dsh-plugins/dsh-trellis/lib/index.js ~/.dsh/profiles/web/node_modules/dsh-trellis/lib/index.js
cd dsh-plugins/dsh-trellis && pnpm test
# 每个场景：
DSH_HOME=/tmp/dsh-parity-home-$TS MOCK_LLM_KEY=dummy timeout 180 \
  dsh --profile trellis-audit --json "<prompt>"
# 断言示例：
jq -r 'select(.kind=="root#0") | .body.messages[]?.content[]?.text' requests.jsonl
```

## 风险文件 / 回滚点

| 风险文件 | 风险 | 回滚 |
| --- | --- | --- |
| 本任务 `report.md`/`findings/*` | 结论无证据 | 删除重写；不修改源码 |
| `/tmp/.../.trellis/config.yaml` | 自动写 inline | 临时项目整体删除 |
| 用户 `~/.dsh` | 误用 web profile | 只用 `DSH_HOME` 隔离；当前 Web 只读 |
| mock 端口/进程 | 残留 | `pkill -f mock-llm.mjs`；记录 PID |

## 完成门槛

- [ ] 场景矩阵全部有 E1 证据或明确“未验证”理由。
- [ ] 报告明确区分等价/增强/差异/退化，不把未验证写成通过。
- [ ] 用户确认问题清单后，才另起修复任务。

---

## 9. 修复轮执行清单（2026-10-21）

- [ ] 更新 `lib/trellis-config.js` flow mapping + 测试。
- [ ] 更新 `lib/workflow.js` 零块 fallback + 命令引用归一 + 测试。
- [ ] 更新 `lib/session-composer.js`（如需要）让降级 state 仍发 bootstrap。
- [ ] 新增 `lib/role-contract.js`，接入 `lib/subagent-context.js`，更新测试。
- [ ] research 分支 spec-tree 上下文 + 测试/真实 E2E。
- [ ] `lib/upstream.js` 超时/局部结果 + 测试。
- [ ] `src/client/version-check.js` partial 处理 + `VersionMonitor.jsx`/locale/styles + 测试。
- [ ] `lib/project-defaults.js` 失败缓存 + 测试。
- [ ] `lib/wait-tool.js` 可选超时 + 测试。
- [ ] 版本 0.1.1、README/LOCAL_CHANGES/validation 记录、build:client。
- [ ] `pnpm test`、关键 E2E（S1/S15/S21/S23/S30/S31/S43）回归。
- [ ] `trellis-check` 自查；更新 report/check-report。
