# Findings — 命令面、doctor、冲突检测、版本监控与测试基线

## 1. 命令面（部分无法在 headless 做 E1）

- 插件注册三个命令（E2，源码锚点）：
  - `trellis-status`、`trellis-finish`：`lib/commands.js:342,385`
  - `trellis-doctor`：`lib/doctor.js:133-147`
- headless 应用没有斜杠命令派发：把 `/trellis-doctor` 当普通 prompt 送给模型
  （V8：事件流只有 `session/status/text/final`，mock 收到一次模型请求，无 command 事件）。
  因此**命令的实际 UI 行为本轮无法 E1 验证**，需要 web profile 手工或浏览器自动化验证。
- 命令实现只依赖 Python CLI + git（`lib/commands.js`），无网络副作用。

## 2. doctor / 设置页 / 冲突 / 版本监控

| 能力 | 本轮判定 | 依据 |
| --- | --- | --- |
| `/trellis-doctor` | 无法 E1（headless 无命令派发）；单测覆盖 | `lib/doctor.js`、`test/doctor.test.js` |
| Web 设置页（设置 → Trellis） | 无法 E1（未做浏览器自动化） | `settings.section` 注册于 `lib/index.js` |
| 冲突检测 | 无法 E1（结果经 `/dsh-trellis/conflicts` 与 shell overlay 暴露，headless 无 UI） | `lib/conflicts.js`、`lib/index.js:137` |
| 版本监控路由 | 无法 E1（同源路由 `/dsh-trellis/version-check`，headless 不启动 web host） | `lib/index.js`、`lib/client.js` |

以上能力均为“产品化增强”，不参与 Codex 对标判定；本轮不以文档或单测当作通过证据。

## 3. 插件自带测试基线（E3，仅基线）

```
node --test "test/*.test.js"
tests 295 | pass 291 | fail 0 | cancelled 0 | skipped 4
```

与 `docs/validation-0.3.9-local.md` 的声明一致；本轮结论不依赖该结果。

## 4. 真实 Codex 侧接线现状

- 用户级 `~/.codex/config.toml` 已开 `features.hooks = true`，本仓库 hooks 已审批；
  **临时项目**未审批，因此 `codex exec` 真实运行没有任何 Trellis 注入（见 `environment.md`）。
- 这反证：Codex 的 Trellis 体验依赖“用户级开启 + 每项目 hook 审批 + 项目可信”三道人工门；
  DSH 插件安装后即生效（本轮所有 E1 场景均无审批步骤）。这是 DSH 侧的实际优势。
