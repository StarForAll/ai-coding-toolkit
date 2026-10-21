# 修复报告 — dsh-trellis 0.1.1

> 用户确认：P3-5 默认 inline 是正常产品选择，不再报错；P3-7 的实际问题是 UI 手动校验显示 `上游 fork This operation was aborted`。其余 P2/P3 均按真实问题修复。
> 本轮按机制修复，不做调用点补丁。用户已提交 `5baa8d7` 与 `bca5a15` 并更新 web profile。

## 1. 修复矩阵

| 项 | 修复 | 关键文件 | 验证 |
| --- | --- | --- | --- |
| P2-1 research 上下文 | research 改为 spec 目录树 + `get_context.py --mode packages` + Search Tips；`research.jsonl` 仅在真实条目时内联 | `lib/subagent-context.js` | 单测 + `s23b-research-spec-tree` |
| P2-2 inline 启动门禁 | `<dsh-mode>` 增加 `task.py start ... --allow-empty-context` 指引 | `lib/workflow.js` | `s13e2-flow-inline` |
| P2-3 workflow 零块/缺失 | Trellis 项目返回 generic fallback + bootstrap；普通 Git 仓库仍静默 | `lib/workflow.js` | 单测 + `s14b2`/`s14c` |
| P2-4 flow-style 配置 | `parseSection` 支持 `section: {k: v}`，覆盖 dsh/spec/prompt/context | `lib/trellis-config.js` | 单测 + `s13e2`/`s13f2` |
| P3-1 命令形态 | 注入正文把 `/trellis:<name>` 归一为 DSH 技能/命令 | `lib/workflow.js` | 单测 + `s13e2` |
| P3-2 角色契约矛盾 | 推送副本删除 pull-only 段落；research Step 1 改写；磁盘 skill 不变 | `lib/role-contract.js`、`lib/subagent-context.js` | 单测 + `s21b`/`s23b` |
| P3-3 只读重试 | 按 root 缓存不可写结果，只警告一次 | `lib/project-defaults.js` | 单测 |
| P3-4 安装文档 | README/spec 改为“ssh git 依赖快照”，说明改源码需重装/重启 | `README.md`、`.trellis/spec/platforms/dsh-workflow-behavior.md` | 文档复核 |
| P3-6 wait 边界 | 新增可选 `timeout_ms`，超时返回 `timeout/unknown`，清理监听器 | `lib/wait-tool.js` | 单测 + `s30b-wait-timeout` |
| P3-7 版本检查 abort | AbortError → 友好超时；Atom 失败回退 GitHub REST；commit/release 用 `allSettled` 返回局部结果；UI 显示 partial | `lib/upstream.js`、`src/client/version-check.js`、`VersionMonitor.jsx`、`locales.js` | 单测 + 真实 GitHub 200 + 10ms 挂起测试 |
| P3-5 默认 inline | 用户确认保留，未改默认值 | — | — |

## 2. 版本检查修复细节

旧路径：

```text
commits.atom 超时 → AbortError("This operation was aborted")
  → Promise.all reject
  → handler 500 {error: message}
  → UI 行显示 “上游 fork This operation was aborted”
```

新路径：

```text
fetchText AbortError → UpstreamError("GitHub request timed out after 10000 ms", 504)
  → Promise.allSettled
  → Atom 失败时回退 GitHub REST（commits?per_page=1 / releases?per_page=1）
  → 200 {ok:true, commit, release, errors:[...]}（可用数据优先）
  → client: row.ok=true, row.partial=true, row.error=友好文本
  → UI: “部分结果” + release（若有）+ “可稍后重试”
```

- commit feed 失败不再丢弃 release feed；
- Atom feed 不可达时回退到 GitHub REST（`commits?per_page=1` / `releases?per_page=1`）；
- release feed 失败不再被静默吞掉，作为 `errors` 返回；
- 只有 commit 成功时才更新 seen baseline，partial 不覆盖旧基线；
- npm 分支同样把超时/网络错误转为可读 `UpstreamError`。

## 3. 验证

### 单测

```text
pnpm test
tests 340 / pass 336 / fail 0 / skipped 4
```

新增覆盖：flow-style 配置、零块/缺失 workflow、普通 Git 静默、命令归一、角色契约裁剪、research spec-tree、版本检查 partial/timeout、只读失败缓存、wait 超时。

### 真实 DSH E2E

隔离 `DSH_HOME` + 本地 mock LLM；用户 `web` profile 未改动。

| 场景 | 结果 |
| --- | --- |
| 零块 workflow | breadcrumb + bootstrap 均出现；generic fallback |
| 普通 Git 仓库 | 0 注入 |
| flow-style inline | inline 块 + banner；implement 派发被拒 |
| inline 启动提示 | `--allow-empty-context` 出现在 banner |
| 命令归一 | `/trellis-finish-work` 出现，`/trellis:finish-work` 消失 |
| research push | spec tree + Search Tips；无 PRD/无空清单提示 |
| implement push | 无 `MUST load context yourself` / `does NOT auto-inject` |
| wait 超时 | `state=timeout`, `outcome=unknown`，无误报成功 |

证据目录：`/tmp/trellis-dsh-parity-20261021/scenarios/`。

### 版本检查

- 真实 GitHub Atom：200，commit `5108b7f`，release `v0.1.13`，`errors=[]`。
- 10ms 挂起 feed：200，`commit=null`、`release=null`，错误文本 `GitHub request timed out after 10 ms`；不含 `This operation was aborted`。

## 4. 变更与提交

- 版本：`0.1.0` → `0.1.1`；`lib/client.js` 重建，`PLUGIN_VERSION = "0.1.1"`。
- 文档：README、LOCAL_CHANGES、`docs/validation-0.1.1-local.md`、DSH 平台 spec。
- 用户已提交 `5baa8d7`（0.1.1 主修复）与 `bca5a15`（check 轮修复），并更新 web profile；当前 Web 进程启动于安装文件之后，已加载新 bundle。

## 5. 仍不在本轮范围

- 真实 Web 设置页/真实 slash 命令（认证 URL 未带入命令行）。
- `/compact`/clear 后的真实重注入与桌面通知。
- 第二个 Trellis 插件的真实冲突告警。
- 真实模型长期遵循率。

## 6. 安装态 0.1.1 复验（2026-10-21）

- 第二次提交 `bca5a15` 已包含 check 轮改动；安装目录 `~/.dsh/profiles/web/node_modules/dsh-trellis` 与源码哈希一致。
- 安装目录 mtime `22:58:53`，当前 Web 进程启动于 `22:58:59`，进程已加载新 bundle。
- 安装态 E2E：零块 fallback + 精确 inline 提示 + bootstrap；flow-style inline + 命令归一；inline 守卫；research spec tree；implement 契约无矛盾句；wait 超时全部通过。
- 当前 DSH 进程的版本检查路由返回 200 commit/release（Atom 超时后 REST 回退，约 11s），无原始 abort。
- 单测 `340 / 336 pass / 0 fail / 4 skip`。
- 未自动化浏览器点击“手动校验”按钮；认证 URL 未带入命令行。Host 路由与 client bundle 已分别验证。
