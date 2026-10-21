# 命令、身份与 Web 面

## 结果

| ID | 场景 | 观察 | 判定 | 证据 |
| --- | --- | --- | --- | --- |
| S34 | shell 身份 | `ID=session-c622…`、`CTX=dsh_session-c622…`、`TRELLIS=` 空；`task.py current --source` 返回 impl-task | 通过 | `s34-shell-identity/events.jsonl` |
| S35 | `trellis-status` 有任务 | 返回 Current task/Status/Title/Source + git status + 技能提示 | 通过 | `s35-commands.txt` |
| S35 | `trellis-finish` 有任务 | 返回只读收尾清单；未清指针/未归档 | 通过 | `s35-commands.txt` |
| S35 | `trellis-doctor` | 项目根、插件 0.1.0、Trellis 0.7.0-beta.4、8 个 state 块、dispatch mode、active task、spec 1、冲突 unavailable（fake ctx） | 通过 | `s35-commands.txt` |
| S35b | 无任务 | status `Current task: (none)` success；finish 明确 “Nothing to archive” | 通过 | `s35b-commands-no-task.txt` |
| S35 | 带参数 | `status=error`：“does not accept arguments or image attachments” | 通过 | `s35-commands.txt` |
| S38 | `/dsh-trellis/conflicts` | HTTP 200；`{"status":"checked","conflicts":[]}` | 通过 | 本轮 curl 输出 |
| S38 | `/dsh-trellis/version-check` | npm source 200 返回 dist-tags；plugin source 200 返回 commit v0.1.13；非法 source 400；POST 405 | 通过 | `/tmp/vc*.json` |
| S36 | 真实 Web slash 分发 | **未验证**：DSH Web 需要启动时打印的认证 URL；独立 agent-browser 无凭据，根路径 401 | 未验证 | curl 401 |
| S37 | Web 设置页 UI | **未验证**：同上认证限制；只验证了路由与 client bundle/单测 | 未验证 | — |

## 身份细节

插件通过 `shellEnv` 注入 `DSH_TRELLIS_CONTEXT_ID=dsh_<session-id>`；DSH 原生同时提供 `DSH_SESSION_ID` 与 `DSH_SHELL=1`。实测 `task.py` 优先使用 `DSH_TRELLIS_CONTEXT_ID`，没有继承外层 `TRELLIS_CONTEXT_ID`。两个会话的指针互不覆盖（S33）。

## 命令只读性

`trellis-finish` 执行前后 active-task 指针文件内容一致；未触发 archive/journal。`trellis-status` 只运行 `task.py current --json` 与 `git status --short --branch`，无写操作。

## 未验证的 Web 面与原因

当前 Web 进程（PID 134621）对根路径要求启动时打印的认证 URL；浏览器新实例没有该凭据，`agent-browser` 打开根路径后无交互元素。直接读取该 URL 会把认证 token 带入命令行/日志，按凭据处理规则未做。

因此：

- 设置页“设置 → Trellis”唯一入口、五个能力开关、版本监控分组的浏览器级交互：**未验证**。
- 真实 `/trellis-status` / `/trellis-finish` 在 Web 客户端的 slash 分发与 `recordInput: false`：**未验证**；本轮只在 handler 级真实调用（S35）。
- 冲突横幅/桌面通知：只验证了 HTTP 路由和单测；未安装第二个插件到用户 profile。
- 压缩/clear 后 bootstrap/spec 重注入：**未验证**（需要可认证的 Web 会话）。

这些缺口不影响 headless 消息链的结论，但报告不把它们写成“通过”。
