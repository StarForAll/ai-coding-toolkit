# Findings — 命令面 / doctor / 设置页 / 上游监控 / 冲突检测

判定基线：E1 = 实际运行；E2 = 静态推断；E3 = 文档/测试声明。

## 1. 命令注册与执行（E1）

以真实 `registerCommands` / `registerDoctorCommand` 捕获注册结果并直接调用 handler：

| 命令 | 注册 | 真实执行结果 |
| --- | --- | --- |
| `trellis-status` | 是 | 本仓库 cwd + 假会话 id → `kind: success`，输出 `Current task: (none)`、git status、session ritual 提示 |
| `trellis-finish` | 是 | `kind: success`，只打印 wrap-up 清单，不清理/归档任务（只读语义成立） |
| `trellis-doctor` | 是 | `kind: success`，输出 Project root / Plugin dsh-trellis 0.3.7 / Trellis 0.7.0-beta.4 / Workflow 9 blocks / Spec injection / Version monitoring 等字段 |
| 参数拒绝 | — | `rawInput="extra arg"` → `kind: error`，"does not accept arguments" |
| 非项目目录 | — | cwd=/tmp → `kind: error`，"No project root found" |

doctor 的 `Spec injection: disabled by .trellis/config.yaml` 与仓库真实配置一致
（`.trellis/config.yaml:213-214` 明确 `spec_injection.enabled: false`），不是误报。

## 2. 上游版本监控（E1）

真实 web 会话（`http://127.0.0.1:3080`）自带路由：

```
GET /dsh-trellis/version-check?source=plugin&url=https://github.com/SajoLuo/dsh-trellis
-> 200 {"ok":true,"commit":{"shortSha":"5108b7f",…},"release":{"tag":"v0.1.13",…}}
GET /dsh-trellis/version-check?source=npm&name=dsh-trellis
-> 200 {"ok":true,"tags":{"latest":"0.1.13"}}
```

错误路径（E1）：非法 repo URL → 400 `unrecognized GitHub repository URL`；
`source=x` → 400 `unknown source`；跨站 `sec-fetch-site: cross-site` → 403；
POST → 405。本地 handler 注入 mock fetch 时同样返回这些状态码。

观察：本地版本号 0.3.7 高于上游 0.1.13（LOCAL_CHANGES 说明这是刻意抬高以避免安装器
跳过）。版本监控以 commit/release 为准，本审计未判定"版本号比较"是否会在 UI 上产生
误导徽标（属 E3/未验证）。

## 3. 冲突检测（E1）

真实 web 路由：`GET /dsh-trellis/conflicts` → `200 {"ok":true,"status":"checked","conflicts":[]}`。

模块级注入 loader 形状的 fake ctx（E1）：

- 仅有自身条目 → `{"status":"checked","conflicts":[]}`；
- 自身 + `dsh-trellis-next` → `{"status":"checked","conflicts":[{id:"x",name:"dsh-trellis-next"}]}`；
- 竞争条目 `disabled:true` → 被忽略；
- loader 不可达 → `{"status":"unavailable"}`；无法排除自身 → `{"status":"unverified"}`。

与文档声明一致：宁报不确定，不伪造"无冲突"。

## 4. 设置页 / 客户端（E1/E3）

- `package.json#exports["./client"] -> ./lib/client.js` 存在；`dsh.client.inject` 声明的
  `@deepseek-ai/dsh-client-locale`、`-ui-settings`、`-ui-settings-plugins` 均存在于
  profile `node_modules`（E1）。
- `node --test test/client-*.test.js` 全部通过（E1，属单元级）。
- **未做浏览器级验证**：没有打开设置页确认字段渲染、maxBytes 编辑、doctor 卡片和
  版本监控 UI 的真实交互。该项标记"未验证"，不能用单元测试替代。

## 5. 验证通过（无问题）

- 三个命令的名称、参数拒绝、非项目降级、只读语义（E1）。
- doctor 报告字段完整，且对真实配置给出正确判断（E1）。
- 上游路由的输入校验、方法限制、跨站拒绝、错误状态码（E1）。
- 冲突检测的四种状态与实际 loader 形状一致（E1）。

## 6. 未验证 / 无法验证

- web 设置页 UI 与版本监控徽标的浏览器级行为（未做 browser automation）。
- 上游 feed 异常/超时（`UpstreamError` 502）在真实网络下的表现（仅本地 mock 注入）。
- doctor 对损坏 task.json / 只读运行时目录的真实报告（未在临时项目构造；单测覆盖）。
