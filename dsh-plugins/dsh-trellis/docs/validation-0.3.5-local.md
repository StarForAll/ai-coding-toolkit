GATE: GAP_FOUND

> 后续记录：第二次复验后，0.3.6 补了冲突视图 committed 测试、旧版 Trellis
> `--json` 回退和 generic 子代理确认；0.3.7 又补了子代理角色契约与 spec 去重状态
> 持久化。见 [validation-0.3.6-local.md](validation-0.3.6-local.md) 和
> [validation-0.3.7-local.md](validation-0.3.7-local.md)。

# Validation record — local dsh-trellis 0.3.5

- 日期：2026-10-20
- 复核对象：`tmp/dsh-trellis-verification-20261020.md`（独立验证会话留下的安装态报告）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 安装形态：`web` profile 依赖 `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis`
- 复核方式：不采信报告结论，直接运行插件导出的函数/命令处理器、真实项目 `task.py`、插件测试与构建，并核对 DSH 的 `agent/pre-step` 路径

## 结论

报告中的以下说法经独立复核成立，已在 0.3.5 修正：

1. 子代理首请求同时收到 `no_task` 面包屑 + bootstrap，与 push 的 `Active task:` 矛盾。
2. 无活跃任务时 `/trellis-status`（以及 `/trellis-finish`）把 Trellis 的 exit 1 当成脚本失败。
3. README 的“DSH 与 Codex 体验一致”与同文件列出的差异自相矛盾。
4. `docs/capability-inventory.md` 的 Gaps/Deferred 有过时、互相矛盾的条目。
5. 冲突路径不会主动请求通知权限；未授权时只有横幅，没有桌面通知。

以下说法未确认为可修正缺陷，不按缺口处理：

- “`docs/validation-0.3.4-local.md` 已过时”：运行中的 host 确实提供
  `/dsh-trellis/conflicts`（`200 {"ok":true,"status":"checked"}`）与
  `/dsh-trellis/version-check`（缺 source 时 `400 unknown source`），但无法从 host
  进程外确认已加载的包版本；不从“路由存在”推断版本，该条保留为未确认。
- “缺少 `USER_ACCEPTANCE` 记录”：见文末“流程证据”，本轮不伪造历史接受记录。

## 独立复核证据

### 1. 命令缺陷（真实项目）

在真实仓库 `/home/xzc/projects/personal/ai-coding-toolkit` 上直接调用插件的命令处理器：

修复前：

```text
trellis-status: error
Trellis script failed via python3: Command failed: ... task.py current --source
```

直接运行同一脚本：

```text
$ .trellis/scripts/task.py current --source
Current task: (none)
Source: none
EXIT:1
```

`task.py current --json` 返回同一状态的机器可读契约：

```text
{"current_task": null, "source": "none", "stale": false}
EXIT:1
```

Trellis `0.6.17` 与 `0.7.0-beta.4` 的 `cmd_current` 都实现了 `--json`，且都以
`return 0 if active.task_path else 1` 表达“有无活跃任务”。修复后，真实仓库上的输出：

```text
=== trellis-status (success) ===
Current task: (none)
Source: none

Git status:
## main...origin/main
?? docs/capability-inventory.md
?? dsh-plugins/

Session rituals: type /trellis-start (start), /trellis-continue (resume), /trellis-finish-work (skill wrap-up).

=== trellis-finish (success) ===
Current task: (none)
Source: none

No active task. Nothing to archive or record for a Trellis task.
...
```

### 2. 子代理缺陷（插件管线 + DSH 源码）

- DSH `dsh-subagent` 创建子会话时写入 `parentSession`、`origin: "subagent"`。
- DSH `dsh-agent-loop` 的 `preStep()` 对所有 agent 走同一个 `agent/pre-step`
  waterfall，子代理不会跳过。
- 插件 composer 用 `agent.session.header.id` 解析子会话自己的 pointer；子会话没有
  pointer，于是 `resolveTrellisState()` 得到 `no_task`。

用真实 session header 形状驱动插件管线，修复前：

```text
composer messages: [
  { breadcrumb: true,  firstLine: '<system-reminder>' },
  { breadcrumb: false, bootstrap: true, firstLine: '<trellis-bootstrap>' }
]
push added: 1
push first lines: [ '<!-- trellis-hook-injected -->', '# Trellis Native Implement Subagent', ... ]
```

修复后：

```text
composer messages: []
push added: 1
push first lines: [ '<!-- trellis-hook-injected -->', '# Trellis Native Implement Subagent', ... ]
```

判别条件是 `session.header.origin === "subagent"`，不是 `parentSession`：fork 也有
`parentSession`，但仍是根会话，必须保留面包屑/bootstrap。子代理自己绑定任务后仍会
收到该任务的面包屑，但不会收到 bootstrap。

### 3. 冲突通知

`notifyDesktop()` 在 `Notification.permission === "granted"` 时创建通知，否则返回
`false`；`requestNotificationPermission()` 只在 `"default"` 时发问。冲突横幅原先只
调用 `notifyDesktop()`，所以默认权限下既不会请求权限，也不会出现桌面通知。

修复后，横幅在 `permission === "default"` 时显示“启用桌面通知”按钮（点击即浏览器
要求的用户手势），授权成功后立即补发本次冲突通知；`denied` 时显示站点设置提示。
真实浏览器中的权限弹窗与通知展示仍未执行（见“未验证”）。

## 修正内容（按根因，不按症状）

| 文件 | 修正 |
| --- | --- |
| `lib/session-composer.js` | 识别 `origin: "subagent"`；无自有任务时不注入任何消息，有自有任务时只注入面包屑，永不注入 bootstrap。fork 保持根会话行为 |
| `lib/commands.js` | 改用 `task.py current --json`；`runTrellisScript` 在非零退出时保留 `stdout`/`stderr`/`exit code`；只有“exit 1 + 可解析且 `current_task: null`”才算无任务，裸 exit 1 仍报失败；`/trellis-finish` 无任务时不再打印归档清单 |
| `src/client/ConflictBanner.jsx`、`locales.js`、`styles.js` | 增加“启用桌面通知”按钮与拒绝提示，用点击满足用户手势要求 |
| `README.md` | 删除“体验一致”声明，改为“三项主链路已对齐，但仍存在下列差异” |
| `docs/capability-inventory.md` | 更新 Gaps/Deferred，关闭已实现的 doctor/排他/版本监控/Web 设置页条目 |
| `package.json`、`lib/client.js` | 版本 0.3.5；客户端 bundle 重新构建 |

## 测试与验证

```bash
cd dsh-plugins/dsh-trellis
node --test "test/*.test.js"
node_modules/.bin/tsdown
```

| 检查 | 结果 |
| --- | --- |
| 单元/集成测试 | 242 tests，238 pass，0 fail，4 skip |
| 子代理首步集成用例 | 无面包屑/bootstrap，只有 `subagent-context` push |
| 子代理自有任务用例 | 面包屑为 `planning`，无 bootstrap |
| fork/非 subagent 的 parentSession 用例 | 仍注入面包屑 + bootstrap |
| 无任务命令用例 | `/trellis-status`、`/trellis-finish` 均 success；裸 exit 1 仍 error |
| 客户端构建 | `lib/client.js` 61.85 kB（gzip 15.93 kB），`PLUGIN_VERSION = "0.3.5"` |
| 真实仓库命令探针 | 输出 `Current task: (none)`，不再是脚本失败 |

## 未验证 / 环境限制

- 真实浏览器中的通知权限弹窗、桌面通知展示、设置页保存：未执行（未取得运行中 Web
  GUI 的认证 token）。
- 真实 DSH 压缩流程：未触发；压缩相关行为仍只有投影/策略单测证据。
- 运行中 host 已加载的插件版本：无法从进程外确认；路由存在只证明路由已注册。
- GitHub Atom 版本检查：本环境网络结果不稳定；npm 路由此前已验证，本次未重跑。

## 流程证据

- 本文件第一行是 `GATE: GAP_FOUND`，对应本轮“发现缺口并修正”的结论。
- `USER_ACCEPTANCE: N/A`（历史）：本轮是缺陷复核与修正，不是首版“只补 bootstrap”的
  部分 parity 验收；不为满足历史流程而伪造当时的接受记录。当前（2026-10-20 晚）完整
  范围已无 partial-parity 缩减，记为 `USER_ACCEPTANCE: NOT_APPLICABLE`；固定排除项和
  手工验收见 `plugin-create.md` 与 `manual-verification.md`。
