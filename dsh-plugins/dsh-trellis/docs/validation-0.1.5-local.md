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
- Codex 同场景（真实 payload 直调 `.codex/hooks/inject-workflow-state.py`）输出
  `Status: no_task` + bootstrap —— 行为不一致。

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
已安装 profile 仍为 0.1.4，需要重装/重启后生效。
