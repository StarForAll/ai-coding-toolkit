GATE: PASS

# Validation record — local dsh-trellis 0.1.5

- 日期：2026-10-22
- 范围：活动任务指针指向已消失目录（`stale`）时的面包屑正文与 bootstrap（缺陷 D1）
- 运行时：DSH `0.2.1-rc.2`；Node `v24.20.0`
- 源码：`dsh-plugins/dsh-trellis`（Strategy A，就地修改）；未提交
- 端到端环境：隔离 `DSH_HOME=/tmp/dsh-cap-verify/home`（profile 以 `link:` 挂载本源码）+
  临时 Trellis 项目 `/tmp/dsh-cap-verify/{proj,proj2}`；真实 LLM（`deepseek-official`，
  凭据经环境变量注入，未写入任何文件或输出）

## 问题复核：D1 是否真实

真实 DSH 会话 `session-202baae0`（`proj2`，指针指向不存在的
`.trellis/tasks/10-22-does-not-exist`）：

```
INJECT breadcrumb stale
<system-reminder>
Trellis workflow state: stale
Active task: .trellis/tasks/10-22-does-not-exist

Refer to `.trellis/workflow.md` for the current workflow step
(no matching [workflow-state] block found).
</system-reminder>
```

- 正文把“指针失效”误报成“workflow 缺块”，没有修复路径；
- `stale` 不等于 `no_task`，composer 不追加 bootstrap；
- Codex 同场景（真实 payload 直调 `.codex/hooks/inject-workflow-state.py`，清除继承的
  `DSH_*` 环境变量）输出 `Task: 10-22-gone (stale_session)` + 通用兜底行，且不附
  bootstrap（源码：bootstrap 仅在完全没有任务指针时追加）—— DSH 的旧文案确实更差，
  但两边并非 no_task/bootstrap 的差异。

> **勘误（2026-10-22）**：本记录最初把 Codex 输出写成 `Status: no_task` + bootstrap。
> 那是直调时的假阳性：`common/active_task.py#resolve_context_key` 会优先使用继承的 DSH
> 身份——`DSH_TRELLIS_CONTEXT_ID`（第 1 优先）或 `DSH_SHELL=1` + `DSH_SESSION_ID`
> （第 2 优先）——并用**环境变量的值**构造 key（`dsh_session-3b709400…`），先于 payload 的
> `session_id`；该 key 在临时项目中没有指针，于是落到 no_task + bootstrap。
> `_detect_platform` 并不识别 DSH，payload 的 `session_id` 也没有被构造成 `dsh_<id>`；
> 早期勘误写的 `dsh_staletest` 是虚构的重建，无法核实。清除 `DSH_*` 后复现真实输出。
> 该错误不影响 D1 的 DSH 侧结论，但把“与 Codex 的差异”写反了：Codex 保留
> `stale_session`、不补 bootstrap，DSH 的专用正文与 bootstrap 是增强。

## 实现变更

| 文件 | 变更 |
| --- | --- |
| `lib/workflow.js` | 新增 `STALE_BREADCRUMB`；`stale` 时优先项目 `[workflow-state:stale]` 块，否则用专用正文（即使 workflow.md 没有任何状态块）。 |
| `lib/session-composer.js` | `stale` 与 `no_task` 一样追加一次性 bootstrap；子代理仍不注入。 |
| `test/workflow.test.js` | 原“stale 降级为通用 fallback”用例改为断言 `STALE_BREADCRUMB`；新增“workflow 无状态块时仍显式诊断”用例。 |
| `test/session-composer.test.js` | 新增 stale 指针 → 面包屑 + bootstrap 用例。 |
| `README.md`、`.trellis/spec/platforms/dsh-workflow-behavior.md` | 记录 stale 语义与默认 `inline`/Codex `auto` 差异。 |

## 验证结果

| 检查 | 结果 |
| --- | --- |
| `node --test "test/*.test.js"` | 364 tests / 360 pass / 0 fail / 4 skip（新增 2 项，skip 仍为 alpha 宿主门槛用例） |
| 真实会话复测（修复后，`proj2`） | 面包屑正文为 `This is a stale pointer, not a missing [workflow-state] block...`，并追加 `<trellis-bootstrap>`；状态仍为 `stale` |
| 真实会话对照（0.1.4） | `session-202baae0` 复现旧文案，无 bootstrap |
| 项目自定义 `[workflow-state:stale]` 块 | 单测：项目文案优先，不被内置正文覆盖 |
| 子代理 | 单测：子代理 stale 不追加 bootstrap |

## 版本

`0.1.4` → `0.1.5`；`pnpm run build:client` 重建 client bundle（仅 `PLUGIN_VERSION` 变更）。
编写本记录时已安装 profile 仍为 0.1.4。2026-10-22 23:15 用户已将 `web` profile 更新到
0.1.5 并重启 DSH（进程启动时间 23:15:18 晚于安装 23:15:12）；`trellis-headless` profile
仍为 0.1.4，使用该 profile 时需要单独更新。

## 安装后复核（web profile 0.1.5，2026-10-22）

- 复测当时，安装目录 `~/.dsh/profiles/web/node_modules/dsh-trellis` 的 `lib/**` 与仓库源码
  逐文件 sha256 一致；`PLUGIN_VERSION` 为 `0.1.5`。之后的勘误只改注释/文档，安装目录与仓库
  存在文本差异（运行逻辑不变），重装可同步。
- 用安装目录（非源码 link）搭建隔离 profile 复测：
  - no_task：breadcrumb + bootstrap；write 触发 deny-once 并重试成功；
  - stale 指针：正文为 0.1.5 专用诊断（`stale pointer, not a missing [workflow-state] block`）；
    安装版 composer 对 root stale 返回 breadcrumb + bootstrap，对子代理不注入 bootstrap；
  - in_progress / `in_progress-inline` / `task_error` 面包屑正常；
  - 子代理 implement push + `trellis_wait`；inline 守卫拒绝；
  - `no-trellis` 仅跳过 breadcrumb/bootstrap，spec-context 仍送达；
  - 非 Trellis 目录零注入；`/trellis-status`、`/trellis-doctor` 正常。
- 回归：`node --test "test/*.test.js"` → 364 / 360 pass / 0 fail / 4 skip；无新增问题。
