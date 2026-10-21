# Trellis 机制、Codex 对照与更新

## 1. 临时项目初始化（E1）

```bash
git init -q
trellis init --dsh --codex -y -u xzc
```

生成：

- `.dsh/skills/trellis-{start,continue,finish-work}/SKILL.md`
- `.dsh/skills/trellis-agent-{implement,check,research}/SKILL.md`
- `.agents/skills/trellis-{before-dev,brainstorm,check,update-spec,...}/SKILL.md`
- `.dsh/DSH.md`、`.codex/hooks/*.py`、`AGENTS.md` 的 `TRELLIS` 块
- `.trellis/.version = 0.7.0-beta.4`

与 Trellis 0.7.0-beta.4 上游 `packages/cli/src/configurators/dsh.ts` 的 class-2 pull-based 设计一致：不写 project hooks/settings，角色提示作为 `.dsh/skills` 交付。

## 2. `task.py` 契约（E1）

`s42-task-contract.txt`：

- `create` 生成任务目录；有 DSH 身份时自动写 `.trellis/.runtime/sessions/dsh_<id>.json`。
- `start` 在 `implement.jsonl`/`check.jsonl` 为空时拒绝，提示 `--allow-empty-context`（Trellis 0.7.0-beta.4 行为）。
- `current --json` 返回 `{current_task:{dir,id,title,status,...},source,stale}`，插件解析字段一致。
- `finish` 删除当前会话指针，不改 task status。
- `archive` 在 `branch == base_branch == main` 时拒绝，要求 `set-branch` 或 `--skip-branch-validation`。这是 Trellis 的 PR 元数据门禁，不是插件行为。

## 3. Codex 对照（E1）

### 3.1 workflow-state 正文

- `in_progress`：Codex hook 正文 **1635 字符**，插件 `in_progress` 正文 **1635 字符，逐字节相同**。
- `no_task`：正文 421 字符，内容相同（仅抽取尾部换行差异）。
- Codex 每轮 no-task 都发 `<trellis-bootstrap>`（两次连续 hook 均为 1）；插件设计为每会话一次（S2 第二轮无重复）。这是**有意差异**，不是缺陷。

证据：`s43-codex-inprogress.txt`、`s43-codex-no-task.json`、`s43-codex-bootstrap-{1,2}.json`。

### 3.2 spec 注入

同一 spec/config/文件：

- Codex：`permissionDecision=deny`，reason=`Trellis injected governing specs...`，`additionalContext` 203 字符的 `<spec-context>`。
- 插件：deny reason 合并 RETRY_NOTICE + 同一 `<spec-context>`。

文本等价；投递形状不同（DSH 把 payload 放进 deny reason）。

### 3.3 implement/check 子代理

- Codex `SubagentStart` 的 `Curated Context`：spec 文件 + prd + design + implement（共 756 字符）。
- 插件推送：同一 curated context，外加角色 skill 正文（完整 implement 契约）与“上下文已准备”前置声明（共 5498 字符）。

curated 部分一致；插件多出角色契约，属于 DSH 侧补足（Codex 的角色契约在 agent TOML 中另行注入）。

### 3.4 research 子代理

- Codex：spec 目录树 + `get_context.py --mode packages` + Search Tips（705 字符）。
- 插件：`research.jsonl` 空提示 + prd/design/implement（4854 字符，含角色契约）。

**不等价**，详见 `04-subagent.md` P2。

### 3.5 skip 关键字

项目 `prompt_injection.skip_keyword: skip-trellis` 下：

- Codex hook 输出 0 字节。
- 插件 S10 注入数 before=8 / after=8（未新增）。

两者一致。

## 4. `trellis update`（E1）

`trellis update --dry-run` 将 `.trellis/config.yaml` 归为 “Modified by you”，不自动覆盖；`trellis update -s` 跳过该文件，`dsh.dispatch_mode` 保留，config hash 前后相同（`6b7934a4…b058`）。说明插件写入的 `dsh` 段不会被 Trellis 更新擦除；但每次 update 会把它当作用户修改提示一次。这是可接受的混合所有权行为。

## 5. 版本/平台对照（E2）

- Trellis `AI_TOOLS.dsh` 声明：`hasPythonHooks: false`、`agentCapable: true`、skills 从 `.agents/skills` + `.dsh/skills` 读取。
- 插件 role push 硬编码 `.dsh/skills/trellis-agent-<role>/SKILL.md`，与当前 Trellis 生成路径一致；若目标项目只初始化了旧版/其他平台目录，则只能走 fallback 路径提示。
- Trellis `DSH.md` 的官方能力表明确：无插件时没有 per-turn breadcrumb / 事件驱动 wait / utility commands；插件补齐了这些。这与本轮 control profile 的 0 注入、0 trellis 工具结果一致。
