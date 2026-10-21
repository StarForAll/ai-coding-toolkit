# Implement — 验证执行清单

> 只读验证：不修改 `dsh-plugins/dsh-trellis`，不改用户 profile；临时状态全部落在
> `/tmp`。每步完成后把原始输出归档到本任务 `findings/`。

## 0. 准备

- [x] 0.1 记录版本与安装链：`dsh --version`、`--dump-config` 中 dsh-trellis 条目、
      插件 `package.json` 版本、Trellis/Codex CLI 版本 → `findings/environment.md`
- [x] 0.2 新建唯一临时项目 `/tmp/trellis-verify-<ts>`：
      `git init` + `trellis init --dsh --codex -y -u xzc`
- [x] 0.3 建独立 `DSH_HOME=/tmp/dsh-verify-home-<ts>`，复制 headless profile 为
      `trellis-verify`，软链插件并写 insert 条目；`--dump-config` 验证
- [x] 0.4 启动 mock LLM（记录 messages/tools，按脚本返回 tool_calls），配置
      `llm-pi-ai` + `agent-default-model` 指向 mock
- [x] 0.5 冒烟：一次 `dsh --profile trellis-verify --json "hi"`，确认会话可建立、
      mock 收到含系统提示的请求

## 1. 静态基线（E2 假设，供后续验证）

- [x] 1.1 通读 `lib/index.js`、`workflow.js`、`dispatch-guard.js`、`subagent-context.js`、
      `spec-inject.js`、`bootstrap.js`、`wait-tool.js`，列出待验证断言
- [x] 1.2 对照 `.codex/hooks/*.py` 与 `.trellis/scripts/common/*`，列出逐项差异假设
- [x] 1.3 记录插件自带单测基线（`node --test`）——仅基线，不作结论

## 2. 端到端场景（E1）

- [x] 2.1 B1/B2/B3 bootstrap 首轮一次、次轮不重复、子代理静默
- [x] 2.2 C1 逐状态注入：no_task / stale / task_error / planning / in_progress /
      completed / 自定义 / blocked；同输入跑 Codex hook 做字节对照
- [x] 2.3 C2 去重与 compaction 重投
- [x] 2.4 C3 项目 `prompt_injection.skip_keyword`
- [x] 2.5 C4 任务级 / developer / default_workflow 变体选择
- [x] 2.6 D1–D5 spec 注入四类行为 + 配置变体 + 持久化/损坏恢复
- [x] 2.7 E1/E2 子代理上下文推送与通用子代理静默
- [x] 2.8 E3 派发守卫（缺失任务 / stale / 不可读 task.json）
- [x] 2.9 F1 `trellis_wait` 成功/失败/中止语义
- [x] 2.10 G1 会话身份与 `task.py current` 解析
- [x] 2.11 H1–H3 doctor / 冲突检测 / 版本监控路由
- [x] 2.12 J1 非 Trellis 项目 0 注入

## 3. inline 专项（E1）

- [x] 3.1 I1–I5：实现存在性、状态覆盖、块缺失回退、配置解析、横幅内容
- [x] 3.2 I6–I9：作用域、去重、与派发守卫/子代理协议关系、与 Trellis 契约冲突
- [x] 3.3 I10：Codex `codex.dispatch_mode: inline` 真实 hook 输出 vs DSH 注入正文
- [x] 3.4 I11–I12：缺省/缺段默认 auto、正文体积与截断

## 4. 收尾

- [x] 4.1 汇总 `report.md`：结论、问题清单（P0–P3，含复现/根因/影响/建议修复）、
      无法验证项
- [x] 4.2 复核 `git status`：`dsh-plugins/` 无改动，仅本任务目录新增
- [x] 4.3 向用户提交问题清单与执行方案，**等待确认后**再修复

## 验证命令（固定）

```bash
# 端到端单场景
DSH_HOME=/tmp/dsh-verify-home-<ts> dsh --profile trellis-verify --json "..."

# Codex 基线
python3 -X utf8 .codex/hooks/inject-workflow-state.py < payload.json

# 单测基线
cd dsh-plugins/dsh-trellis && node --test "test/*.test.js"
```

## 回滚点

- 删除 `/tmp/trellis-verify-<ts>`、`/tmp/dsh-verify-home-<ts>`、mock 日志即可完全回滚。
- 任何需要临时改配置的故障注入只改 `/tmp` 项目内文件，改前备份同名 `.bak`。


## 执行结果

全部项目已完成，证据与结论见 `report.md` 与 `findings/`。本轮未修改插件源码。
