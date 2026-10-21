# Validation record — local dsh-trellis 0.3.4

> 历史记录：本文件记录 0.3.4 当时的状态。0.3.5 的独立复核与修正见
> [validation-0.3.5-local.md](validation-0.3.5-local.md)。第 5 节“0.3.4 尚未在运行中的
> host 里重新导入”保留为当时记录；后续只能从 host 外侧探测到路由存在，无法确认已加载
> 的包版本，因此该条不作为已证实结论。

- 日期：2026-10-20
- 运行时：DSH `0.2.1-rc.2`（`dsh --version`），Node `v24.20.0`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A 就地修改）
- 安装形态：`web` profile 依赖 `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis`

本记录只记录**实际运行过**的检查；未运行项单列在最后一节。

## 1. 仓库内自动化

```bash
cd dsh-plugins/dsh-trellis
npm test            # node --test "test/*.test.js"
npm run build:client
```

结果（2026-10-20 本轮）：

| 命令 | 结果 |
| --- | --- |
| `npm test` | 231 tests，227 pass，0 fail，4 skip |
| `npm run build:client` | 通过；`lib/client.js` 60.26 kB（gzip 15.69 kB） |

4 个 skip 是既有的 native-activation 用例：没有真实激活宿主时按设计跳过。

> 基线安装说明：本机 `pnpm install` 因 `~/.local/share/pnpm` 只读而失败
> （`ERR_PNPM_STORE_DIR_OPEN_OPERATION_LOCK`），本轮沿用 `npm install
> --legacy-peer-deps` 建立的 `node_modules`，并补装了传递 peer
> `@deepseek-ai/dsh-session-title@0.2.0-rc.1`。`package-lock.json` 已删除，
> `pnpm-lock.yaml` 未改动。

## 2. 设置页结构

| 检查 | 期望 | 实际 |
| --- | --- | --- |
| 唯一入口 | 仅 `settings.section:trellis` | 两种 settings 服务下都只有一条注册 |
| 顶部能力组 | 启用插件 → `/trellis` 命令 → 派发守卫 → 子代理 push → spec 注入 | 静态渲染断言顺序通过 |
| 行为组 | 面包屑字节、项目根标记、跳过关键词、Python 命令 | 渲染在能力组之后 |
| 版本监控关闭 | 间隔、通知、三个来源地址与检查面板全部隐藏 | `versionCheck=false` 渲染结果不含这些 id |
| 版本监控开启 | 全部 15 个配置项 + 面板 | 渲染断言通过 |
| 版本戳 | 客户端显示构建版本 | `PLUGIN_VERSION = "0.3.4"` |

## 3. 版本监控

| 检查 | 期望 | 实际 |
| --- | --- | --- |
| 插件上游 fork | Host 读 `commits.atom` + `releases.atom`，设置页只看结果 | 真实 HTTP 路由探针：commit `32706f7`（2026-10-12），release `v0.1.12` |
| Trellis 官方版本 | Host 读 `@mindfoldhq/trellis` 的 dist-tags | 真实路由探针：`rc 0.6.0-rc.0 · beta 0.7.0-beta.4 · latest 0.6.17` |
| DSH 官方版本 | Host 读 `@deepseek-ai/dsh` 的 dist-tags | 真实路由探针：`latest 0.2.1-rc.2 · alpha 0.2.1-alpha.5 · next 0.2.1-rc.2` |
| 同源路由 | `/dsh-trellis/version-check` 返回 JSON；非法 URL 400；跨站 403；非 GET 405 | `node:http` + 真实 `fetch` 探针通过 |
| 403 成因 | REST API 未认证配额用尽 | 实测 API 响应带 `x-ratelimit-limit: 60`；Atom feed 无配额但无 CORS 头 |
| 基线不误报 | 首次只记录、不通知 | 单测：`firstSeen=true, isNew=false, notified=[]` |
| commit 变化 | 通知一次 | 单测 |
| 版本变化 | 任一 dist-tag 变化即通知一次 | 单测：`latest 0.6.17 → 0.6.18` 触发 1 条 |
| 上游 release 对比 | 本地 0.2.2 + 上游 v0.3.0 → 标更新 | 单测 |
| 空值/坏值 | 空 = 跳过；坏包名/坏 URL = 该来源失败，其他来源不受影响 | 单测 |

网络端点（2026-10-20 实测）：`github.com/<owner>/<repo>/commits.atom` 与 `releases.atom`
可访问且无 API 配额，但**没有** `access-control-allow-origin`（浏览器不可直读）；
`registry.npmjs.org` 带 `access-control-allow-origin: *`。因此检查统一由 Host 执行。

## 3.1 插件冲突告警

| 检查 | 期望 | 实际 |
| --- | --- | --- |
| 检测结果作为数据返回 | `/dsh-trellis/conflicts` 返回 `{ok,status,conflicts}` | 真实 `node:http` + `fetchConflicts` 探针：`checked` + `dsh-trellis-plus` |
| 匹配范围 | 包名或 loader id 含 `trellis`（大小写不敏感）都算 | 单测：`trellis-helper`、`@scope/my-trellis`、`SomeTrellisWrapper`、id 为 `trellis-alt` 的条目都上报；`dsh-example` 不报 |
| 只读与同源 | POST 405；跨站 403 | 单测 |
| 桌面通知 | 页面加载时若确认冲突，发一次 `Notification` | 由 `ConflictBanner` 触发；静态渲染不执行 effect，通知逻辑未在真实浏览器验证 |
| 兜底可见 | 通知权限被拒时仍显示 `shell.overlay` 横幅 | 注册断言通过；横幅样式/关闭按钮未在浏览器验证 |
| 不再写日志 | Host 不再输出冲突 warning | 代码中已移除 `warnOnConflicts`，doctor 与横幅使用同一检测结果 |

## 4. 既有能力回归（真实运行时探针）

| 检查 | 实际 |
| --- | --- |
| 两个消息投影注册 | `dsh-trellis.breadcrumbs`、`dsh-trellis.bootstrap` 均可读 |
| spec deny-once | edit 首次 deny 且 reason 含正文；重试放行 |
| read 上下文 | 首次 1 条、窗口内第二次 0 条 |
| 派发守卫 | 无任务 implement deny；有指针放行；无任务 research 放行并附提示 |
| 压缩事件 | 根上下文收到 `compaction/end` |

## 5. 已安装形态

- `~/.dsh/profiles/web/package.json`：`"dsh-trellis": "link:.../dsh-plugins/dsh-trellis"`。
- 0.2.1 已由真实 Web 会话验证：注入内容变成“面包屑 + 独立 bootstrap 消息”两段。
- **0.3.4 尚未在运行中的 host 里重新导入**：源码是 link，但模块已加载，Cordis loader
  用普通 `import()`（同一路径命中 Node ESM 缓存），需要重启 DSH 才会加载 0.3.4（包括 `/dsh-trellis/version-check` 与 `/dsh-trellis/conflicts` 路由）。

> 后续记录：0.3.4 之后 host 已重启到 0.3.5，并由第二次复验确认两个缺陷修复；本条
> 保留为 0.3.4 当时的历史记录，不再代表当前安装态。

## 6. 手工验收清单（未运行，需重启后执行）

1. 重启 DSH，打开 设置 → Trellis：顶部应为“启用插件 / 启用 /trellis 命令 / 派发守卫 /
   子代理任务上下文 push / 路径级 spec 注入”。
2. 版本监控开启时显示间隔、通知、`插件上游 fork 仓库`、Trellis/DSH 官方 npm 包与检查面板。
3. 关闭“版本监控”：上述内容立即隐藏；重新开启后恢复（未保存前只影响草稿视图）。
4. 点“立即检查”：插件上游 fork 显示 Atom feed 里的最新 commit 与 release，
   Trellis/DSH 显示官方 `dist-tags`；对应行链接可跳转；授权通知后弹出本次检查汇总通知；
   若仍出现 403/“route returned 404”，说明 host 尚未重启或路由未注册。
5. 断网后检查：每个来源独立报错，其他来源不受影响。
6. `/trellis-doctor` 仍报告本地版本、任务、spec 注入与冲突检测状态。
7. 同装另一个 `dsh-trellis*` 插件：应出现桌面通知（已授权时）与右下角告警横幅；
   关闭横幅后本页面不再提示；移除冲突插件并刷新后不再出现。

## 7. 未实现/未验证

- 真实浏览器中的通知权限弹窗、桌面通知、自动计时器（只有静态渲染 + 单测）。
- 本地 Trellis/DSH 版本展示：它们是项目/宿主级，页面只展示官方发布版本；
  本地信息由 `/trellis-doctor` 报告。
- npm 版本变化的“落后/领先”判断：页面只显示官方当前 tag 与是否变化，不判断本机是否落后。
- 网络检查的失败重试/退避：当前每次检查独立失败、不重试。
- DSH 若以 Electron/IPC 方式加载（非 `webServer` 路由），设置页的检查会报
  “version-check route returned 404”；该形态未验证。
