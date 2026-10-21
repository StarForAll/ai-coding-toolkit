GATE: GAP_FOUND

> 历史记录：0.3.7 已将子代理角色契约与 spec 去重状态持久化改为实现，并统一 bootstrap 文档口径。见 [validation-0.3.7-local.md](validation-0.3.7-local.md)。

# Validation record — local dsh-trellis 0.3.6

- 日期：2026-10-20
- 复核对象：`tmp/dsh-trellis-reverification-0.3.5-20261020.md`（第二次会话的复验报告）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`；Trellis `0.7.0-beta.4`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）
- 安装形态：`web` profile 依赖 `link:/home/xzc/projects/personal/ai-coding-toolkit/dsh-plugins/dsh-trellis`

## 结论

第二次复验报告的以下结论经独立复核成立：

1. 子代理首请求不再出现 `no_task` 面包屑/bootstrap，只保留 push 的任务上下文。
2. 无活跃任务时 `/trellis-status` / `/trellis-finish` 返回 success。
3. 冲突权限按钮确实存在，但 `test/` 中没有任何 committed 断言。
4. 命令修复依赖 `task.py current --json`；更旧的 Trellis 没有该参数。
5. generic 子代理现在完全静默。
6. 0.3.4 验证记录仍写旧结论（本轮确认第一轮已加“历史记录”横幅，正文保留历史）。

本轮按根因处理其中三项，不改变 0.3.5 已修复的行为：

| 残留项 | 处理 |
| --- | --- |
| generic 子代理静默 | 用 Codex 源码确认这是 parity：`inject-subagent-context.py` 对非 `trellis-*` 子代理类型直接 `sys.exit(0)`。新增 explicit 测试并写入 README，避免把“静默”误当回归 |
| 冲突权限 UI 无 committed 测试 | 拆出 JSX-free 的 `src/client/conflict-view.js`（视图 + 权限请求 action），新增 `test/conflict-view.test.js`，覆盖 `default` / `denied` / `granted` / `unsupported`、请求权限后仅 `granted` 才通知、双语 copy |
| `--json` 兼容边界 | `lib/commands.js` 在 argparse 明确拒绝 `--json` 时回退到 `current --source`；只接受其文档化的 `Current task:` 行，真实失败仍报错。用真实 Trellis 0.6.5 项目验证通过 |

## 当前范围定稿（2026-10-20 晚）

- 当前范围：除固定排除项外全部实现；固定排除项为**项目级策略**和**vendored 自动同步脚本/补丁目录**（不需要）。
- 排他只要求**桌面通知警告**；通知权限不可用时页内横幅兜底；不自动禁用其他插件。
- spec 注入、子代理 push、doctor、版本监控、Web 设置页、冲突告警不再列为“后续阶段”。
- `USER_ACCEPTANCE: NOT_APPLICABLE`：当前完整范围没有 partial-parity 缩减；历史 M1 的 `N/A` 仅作历史记录，不伪造 `ACCEPTED/PENDING`。
- 仍需用户手工确认的项目见 [manual-verification.md](manual-verification.md)。

未处理项：

- 真实 DSH 压缩/clear：仍未触发，作为“未验证项 / 手工验收”，不再称为 Deferred。
- 历史 M1 的 `USER_ACCEPTANCE: ACCEPTED/PENDING`：原始记录不可重建，保持 `N/A`，不伪造。
- 运行中的 host 在第二次复验时是 0.3.5；本轮的 0.3.6 代码需要重启 DSH 才会加载。

## 独立复核证据

### 1. generic 子代理静默是 Codex parity

Codex hook `.codex/hooks/inject-subagent-context.py` 在解析出 `subagent_type` 后：

```python
# Only handle subagent types we care about
if subagent_type not in AGENTS_ALL:
    sys.exit(0)
```

`AGENTS_ALL` 只包含 `trellis-implement` / `trellis-check` / `trellis-research`。因此
generic 子代理在 Codex 侧同样没有 SubagentStart 上下文。插件不替它编造
`no_task` 或 bootstrap 是正确行为；Trellis 角色子代理仍走 push，child-side 技能仍是
pull 路径。

新增用例：`test/index.test.js` 的
“a generic sub-agent stays silent, matching Codex's non-Trellis SubagentStart path”，
断言 generic 派发经过所有 `agent/pre-step` 监听器后消息列表不变。

### 2. 冲突权限 UI 已有 committed 测试

修复前 `grep` 确认 `test/` 中没有 `enableNotifications` /
`requestNotificationPermission` / `notificationsBlocked` 断言。本轮拆出
`src/client/conflict-view.js`，`ConflictBanner.jsx` 只保留 fetch/去重/事件状态；
`test/conflict-view.test.js` 的 5 个用例覆盖：

- `default`：渲染“启用桌面通知”按钮 + 关闭；
- `denied`：渲染站点设置提示 + 关闭，不渲染启用按钮；
- `granted` / `unsupported`：只渲染关闭；
- 权限请求后：仅 `granted` 调用 `notifyDesktop`，`denied`/`unsupported` 不通知；
- zh/en 两份 `conflict.enableNotifications` / `conflict.notificationsBlocked` copy 存在。

这是对生产路径的测试：`ConflictBanner` 调用的正是同一个 view 和
`enableConflictNotifications()`。

### 3. 旧版 Trellis 的 `--json` 兼容已实测

检查 npm 包内的 `task.py`：

| Trellis | `current --json` |
| --- | --- |
| 0.5.0 | 无 |
| 0.6.0 | 无 |
| 0.6.5 | 无；真实运行 `task.py current --json` 退出 2，stderr 为 `unrecognized arguments: --json` |
| 0.6.10 / 0.6.15 / 0.6.16 / 0.6.17 / 0.7.0-beta.4 | 有 |

用真实 0.6.5 项目（`.trellis/scripts/task.py` 来自该版本）验证插件：

```text
无任务：{ kind: "success", noTask: true,  text: "Current task: (none)\nSource: none" }
有任务：{ kind: "success", noTask: false, task: { dir: ".trellis/tasks/demo" },
          text: "Current task: .trellis/tasks/demo\nSource: session:..." }
```

插件先执行 `current --json`，捕获 exit 2 + `unrecognized arguments: --json` 后回退到
`current --source`。裸失败（无该标记）不触发回退；测试覆盖了“真实失败不被吞掉”和
“无关 exit 2 不触发回退”。

### 4. 0.3.4 历史记录

`docs/validation-0.3.4-local.md` 文首已有：

> 历史记录：本文件记录 0.3.4 当时的状态。0.3.5 的独立复核与修正见
> validation-0.3.5-local.md。第 5 节……保留为当时记录……

第二次报告说“可加历史标记”，本轮确认标记已存在；正文保留历史原文，不再改写。

## 测试与构建

```bash
cd dsh-plugins/dsh-trellis
node --test "test/*.test.js"
node_modules/.bin/tsdown
pnpm run test:compat 0.2.1-rc.2
```

| 检查 | 结果 |
| --- | --- |
| 单元/集成测试 | 254 tests，250 pass，0 fail，4 skip |
| 兼容矩阵 | `0.2.1-rc.2` 通过：254 tests，254 pass，0 fail，0 skip |
| 冲突视图测试 | 5/5 通过 |
| 旧版命令兼容测试 | 真实 Trellis 0.6.5 项目；无任务/有任务均 success |
| 客户端构建 | `lib/client.js` 63.97 kB（gzip 16.57 kB），`PLUGIN_VERSION = "0.3.6"` |
| 真实仓库命令探针 | `/trellis-status`、`/trellis-finish` 均 success，输出 `Current task: (none)` |
| host 路由 | `/dsh-trellis/conflicts` 200；`/dsh-trellis/version-check` 缺 source 时 400（路由存在） |

## 未验证 / 环境限制

- 本轮没有重跑完整 headless 会话；第二次复验已做过真实 headless 派发与请求体检查。
  本轮独立证据是代码路径、真实 Trellis 0.5/0.6.5/0.6.10+ 包检查、真实 0.6.5 项目
  命令运行、插件测试与构建。
- 真实浏览器中的权限弹窗/桌面通知展示：本轮（2026-10-20 晚）已用真实 Chrome 页面 +
  `Notification` stub 捕获冲突通知调用；操作系统通知横幅未肉眼确认。
- 真实 DSH 压缩/clear：未触发；列入手工验收。
- 运行中 host 已加载的版本：第二次复验记录为 0.3.5；本轮 0.3.6 需要重启后确认。
- 兼容矩阵：`SUPPORTED_HOSTS` 已加入 `0.2.1-rc.2`；见 `docs/capability-inventory.md`。

## 流程证据

- 本文件第一行是 `GATE: GAP_FOUND`，对应本轮“复验确认 + 残留修正”的结论。
- 历史 `USER_ACCEPTANCE: N/A`：历史 M1 的 partial-parity 接受记录不可重建；不伪造
  `ACCEPTED/PENDING`。当前完整范围已无 partial-parity 缩减，故当前记为
  `USER_ACCEPTANCE: NOT_APPLICABLE`；剩余差异在 README 与 capability inventory 中列出。
