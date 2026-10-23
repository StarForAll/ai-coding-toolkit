# Validation record — local dsh-trellis 0.1.6

- 日期：2026-10-23
- 范围：默认 inline 改为只读（不写 `.trellis/config.yaml`）；角色识别改为声明式；
  子目录相对路径的 spec 匹配；trellis-headless profile 安装 0.1.6；文档补充
- 运行时：DSH `0.2.1-rc.2`；Trellis `0.7.0-beta.4`；Node `v24.20.0`
- 源码：`dsh-plugins/dsh-trellis`（0.1.5 → 0.1.6）
- 端到端环境：
  - 隔离 `DSH_HOME=/tmp/dsh-trellis-parity-verify/home-src`，profile 的
    `dsh-trellis` 指向本仓库源码（symlink）；
  - 真实 `~/.dsh/profiles/trellis-headless` 已更新到 0.1.6（旧 0.1.4 备份在
    `/tmp/dsh-trellis-parity-verify/headless-dsh-trellis-0.1.4`）；
  - 临时项目 `/tmp/dsh-trellis-parity-verify/proj-016`（`trellis init --dsh`）。
- 真实 LLM：`deepseek-official`（凭据经环境变量注入，未写入文件或输出）。

## 变更

| 文件 | 变更 |
| --- | --- |
| `lib/project-defaults.js`（删除）、`test/project-defaults.test.js`（删除） | 不再向项目 config 写 `dsh.dispatch_mode` |
| `lib/workflow.js` | 缺省/非法 `dsh.dispatch_mode` → `inline`；`DSH_INLINE_NOTE` 增加 phase-detail 覆盖与 `.dsh` jsonl 闸门说明 |
| `lib/session-composer.js` | 移除 defaults ensurer；项目解析保持只读 |
| `lib/role-contract.js` | 新增 `roleFromPrompt`：首行角色前缀 / `Role:`/`Agent:` 行 / `You are the <role> sub-agent/role` |
| `lib/subagent-context.js`、`lib/dispatch-guard.js` | 角色识别改用声明式；路径/普通叙述不再触发 push/guard |
| `lib/spec-glob.js`、`lib/spec-policy.js` | 相对 `file_path` 按 agent cwd 解析，并 union 根相对候选 |
| `test/*` | 更新 mode/skip/role/guard/push/spec 用例；新增子目录 spec 与 role 声明用例 |
| `README.md`、`LOCAL_CHANGES.md`、`.trellis/spec/platforms/dsh-workflow-behavior.md`、`docs/manual-verification.md` | 0.1.6 行为与边界 |
| `package.json`、`lib/client.js` | 0.1.6；client bundle 重建（`PLUGIN_VERSION=0.1.6`） |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | **350 tests / 346 pass / 0 fail / 4 skip** |
| 新项目首会话（无 `dsh:` 段） | 面包屑带 `<dsh-mode>`；`git status` 无 `.trellis/config.yaml` 改动（`proj-016` 会话 `session-2b64c4c5…`） |
| generic 子代理（prompt 只读 role skill 路径） | 子会话 0 条 `dsh-trellis` 消息（child `eef038cf…`），未被 push/拒绝 |
| 声明式角色（prompt `Role: trellis-agent-implement`） | 子会话收到 `form=subagent-context role=implement`，含 Active task 与 prd（child `52ab6a48…`） |
| 子目录 spec（cwd=`src`，`file_path=d.js`） | 首次 deny，`<spec-context file="src/d.js" spec=".trellis/spec/demo/api.md">`；重试成功（session `session-67f8651d…`） |
| 已安装 trellis-headless 0.1.6 stale | 专用正文 “This is a stale pointer, not a missing [workflow-state] block…”（session `session-78559178…`） |
| 版本一致性 | `package.json` / `README` / `LOCAL_CHANGES` / 本记录均为 0.1.6；`lib/client.js` 的 `PLUGIN_VERSION=0.1.6` |

## 边界

- **Web profile 仍是 0.1.5**：本轮只更新了 `trellis-headless`；当前运行中的 Web 会话不会看到
  0.1.6 的修复，需另行重装/更新 web profile 并重启 DSH。
- **上游未改**：`~/projects/other/Trellis` 的 DSH workflow/DSH.md 过期指令、Codex-in-DSH
  身份优先级仍按任务报告记录，未在本轮修改。
- **未实测**：真实 compaction、Web GUI（鉴权 URL 未在不泄露凭据的前提下取得）、Windows。
- **Trellis CLI 闸门**：`.dsh` 仍被 `task.py start` 视为 sub-agent-capable；inline 启动仍需
  `--allow-empty-context`（banner 已提示），插件不修改 Trellis 脚本。
