# DSH 平台 Trellis 全链路冒烟测试 — 子代理实测证据

- 记录者角色：`trellis-agent-implement` 子代理（由主会话派发，本会话未再派发任何子代理）
- 工作目录：`/home/xzc/projects/personal/ai-coding-toolkit`
- 记录方式：第 1–7 节全部内容来自记录者**自己实际执行**的命令输出，逐条原样粘贴；未转述主会话结论，未补写未运行的命令。（第 8 节为评审代理独立追加，作者边界见该节开头。）
- 日期标注：命令输出中的时间戳（如 `10月15日 22:42`）来自本机 `ls`，未额外执行 `date`。

---

## 1. 执行环境

### 1.1 `env | grep -i '^DSH' | sort`

```
DSH_HOME=/home/xzc/.dsh
DSH_PROFILE_DIR=/home/xzc/.dsh/profiles/web
DSH_PROFILE=web
DSH_SESSION_ID=ca2bfafa-338c-430c-8139-1862748fa918
DSH_SHELL=1
DSH_WEB_URL=http://127.0.0.1:3080
--- exit: 0 ---
```

### 1.2 `env | grep -i '^TRELLIS' | sort`

无输出（无任何 `TRELLIS*` 环境变量）。补充计数命令：

```
=== env|grep -c '^TRELLIS' (match count) ===
0
--- exit: 1 ---
```

（`grep -c` 无匹配时输出 `0` 且退出码为 1；此处退出码 1 表示"无匹配"，不是命令失败。）

另查三个候选变量是否显式存在：

```
DSH_TRELLIS_CONTEXT_ID=<unset>
TRELLIS_CONTEXT_ID=<unset>
TRELLIS_CONTEXT=<unset>
```

### 1.3 `python3 -V` 与 `pwd`

```
=== python3 -V ===
Python 3.13.5
--- exit: 0 ---

=== pwd ===
/home/xzc/projects/personal/ai-coding-toolkit
--- exit: 0 ---
```

---

## 2. 任务指针解析

```
=== python3 ./.trellis/scripts/task.py current --source ===
Current task: (none)
Source: none
--- exit: 1 ---
```

**明确回答：解析结果不等于 `Active task:` 前导行给出的路径。**

- 派发提示的前导行为 `Active task: .trellis/tasks/10-15-dsh-trellis-smoke-test`；
- `task.py current --source` 在本子会话返回 `Current task: (none)` / `Source: none`，退出码 1；
- 二者不一致。本子会话无法通过 `task.py current` 解析出活动任务，只能依赖前导行（这与 `.dsh/DSH.md` 第 74–75 行"前导行是子代理主要上下文来源"的设计一致）。

### 2.1 为什么返回 `(none)`（记录者自行追加的机制核实）

在同一 shell 中调用脚本内部函数：

```
=== introspect resolve_context_key() in this shell ===
resolve_context_key(None, None) = 'dsh_ca2bfafa-338c-430c-8139-1862748fa918'
_lookup_env_context_key('dsh') = 'dsh_ca2bfafa-338c-430c-8139-1862748fa918'
_lookup_env_context_key(None) = 'dsh_ca2bfafa-338c-430c-8139-1862748fa918'
--- exit: 1 ---
[stderr]
Traceback (most recent call last):
  File "<stdin>", line 9, in <module>
AttributeError: 'ActiveTask' object has no attribute 'task_ref'
```

（该 `exit: 1` 由我探针脚本自身的 `AttributeError` 引起——我猜错了 `ActiveTask` 的字段名；`resolve_context_key` 的三行输出在该异常之前已打印，取值可用。异常之后的"期望文件是否存在"检查未执行。）

据此 + 源码阅读：本 shell 解析出的 context key 为 `dsh_ca2bfafa-...`，对应 `.trellis/.runtime/sessions/dsh_ca2bfafa-....json`，该文件不存在，故 `current` 为 `(none)`。

---

## 3. 子会话身份对照

本会话自身的 session id（提取自第 1 节 `DSH_SESSION_ID`）：

```
ca2bfafa-338c-430c-8139-1862748fa918
```

```
=== ls .trellis/.runtime/sessions/ | grep -i dsh ===
dsh_session-9a0daef3-1e03-4f14-9514-000d26e31030.json
dsh_session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2.json
--- exit: 0 ---
```

目录全貌（含非 dsh 平台）：

```
总计 92
drwxr-xr-x 2 xzc xzc  4096 10月15日 22:42 .
drwxr-xr-x 3 xzc xzc 61440 10月15日 22:37 ..
-rw-r--r-- 1 xzc xzc   136  6月 3日 09:24 claude_0f2c8c47-8176-4e98-b5f3-1d4413c29b5c.json
-rw-r--r-- 1 xzc xzc   168  6月 3日 09:24 claude_13802c75-83bb-4bf8-978a-d3828c1394fc.json
-rw-r--r-- 1 xzc xzc   168  6月 3日 09:24 claude_c955ff1d-af0a-4d3d-8f48-41a05f4a7ebf.json
-rw-r--r-- 1 xzc xzc   178  6月 3日 09:24 codex_019e52f6-eafa-70c0-b8d7-850e6c3985b0.json
-rw------- 1 xzc xzc   168 10月14日 22:15 dsh_session-9a0daef3-1e03-4f14-9514-000d26e31030.json
-rw------- 1 xzc xzc   153 10月15日 22:42 dsh_session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2.json
-rw------- 1 xzc xzc   151 10月15日 22:42 pi_01a13fff-375e-737c-8836-8bcdca011c2a.json
```

**明确回答：我自己的 session id 没有出现在这些指针文件名中。**

```
=== my own session id pointer exists? ===
0
--- exit: 1 ---
```

（`grep -c` 输出 `0`，退出码 1＝无匹配。）

读到的父会话指针内容（该文件在 `.trellis/.runtime/sessions/` 内，只读读取）：

```
=== parent pointer content: dsh_session-ebf0d88c....json ===
{
  "platform": "dsh",
  "last_seen_at": "2026-10-15T14:42:00Z",
  "current_task": ".trellis/tasks/10-15-dsh-trellis-smoke-test",
  "current_run": null
}
--- exit: 0 ---
```

### 3.1 这意味着什么（结论 + 证据边界）

- **结论（有证据）**：父会话（`DSH_SESSION_ID=session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2`）确实写入了指向本任务的会话指针；而我（`ca2bfafa-338c-430c-8139-1862748fa918`）是**独立的 DSH 会话**，`resolve_context_key()` 只按 `DSH_SHELL=1` + `DSH_SESSION_ID` 解析出 `dsh_ca2bfafa-...`，该指针文件不存在，因此**子会话读不到父会话设置的活动任务指针**，`task.py current --source` 返回 `(none)`。
- **子会话无法读到父指针，是当前实现的既定行为**：解析器不做"单会话兜底"（源码 `_resolve_single_session_fallback` 的注释明确说明 pull-based 子调用者须显式选择兼容兜底，且只在**恰好存在 1 个** session 文件时才生效）；本仓库当前有 2 个 dsh 会话指针 + 5 个 claude/codex/pi 指针（3 个 `claude_*`、1 个 `codex_*`、1 个 `pi_*`，与第 3 节 `ls` 全貌一致），即便启用兜底也不会命中。
- **记录者补充观察（原因已定位到 DSH 侧，非 Trellis 侧）**：本工作区 DSH 会话目录同时存在两种 id 形态——`session-<uuid>`（父会话、10-15 08:38/08:54/22:33 等）与裸 `<uuid>`（`b5ce567d...` 22:37、`ca2bfafa...` 22:42）。Trellis 的 context key 由 `"dsh" + "_" + session_id` 拼接，因此父会话得 `dsh_session-ebf0d88c-...`，我得 `dsh_<裸uuid>`，两者落在不同文件名上。

  ```
  === session dir mtimes (this workspace) ===
  drwx------ 2 xzc xzc 4096 2026-10-15 22:42 .../ca2bfafa-338c-430c-8139-1862748fa918/
  drwx------ 2 xzc xzc 4096 2026-10-15 22:37 .../b5ce567d-2ad8-4431-8fd6-87047a942668/
  drwx------ 2 xzc xzc 4096 2026-10-15 22:33 .../session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2/
  ```
  裸 uuid 形态来自 DSH 的子代理驱动（`grep` 命中 `node_modules/@deepseek-ai/dsh-subagent-in-process-driver/lib/index.js:166: const childId = brandString(randomUUID());`，而 `dsh-headless` / `dsh-api-session-controller` 使用 `session-${randomUUID()}`）。**这是对 DSH 源码的静态检索结论，不是我在本任务中动态验证的结果，标注为推断。**

---

## 4. Skill 加载面

加载 `trellis-agent-implement` 时，由 `skill` 工具返回的 base directory：

```
Base directory for this skill: /home/xzc/projects/personal/ai-coding-toolkit/.dsh/skills/trellis-agent-implement
```

```
=== ls .dsh/skills/ .agents/skills/ ===
.agents/skills/:
trellis-before-dev
trellis-brainstorm
trellis-break-loop
trellis-channel
trellis-check
trellis-continue
trellis-finish-work
trellis-meta
trellis-session-insight
trellis-spec-bootstrap
trellis-start
trellis-update-spec
workflow-audit
workflow-capability-audit

.dsh/skills/:
trellis-agent-check
trellis-agent-implement
trellis-agent-research
trellis-continue
trellis-finish-work
trellis-start
--- exit: 0 ---
```

实体文件确认：

```
=== .dsh/skills/trellis-agent-implement contents ===
总计 16
drwxrwxr-x 2 xzc xzc 4096 10月15日 22:30 .
drwxrwxr-x 2 xzc xzc 4096 10月15日 22:30 ..
-rw-rw-r-- 1 xzc xzc 4572 10月15日 22:30 SKILL.md
```

**DSH 从哪里发现 skill**：本次加载的 `trellis-agent-implement` 来自项目内 **`.dsh/skills/`**（DSH 私有层，与 `.dsh/DSH.md` 第 63–66 行"`.dsh/skills/trellis-agent-{research,implement,check}/` 为 child-only 角色 skill"一致）；它**不在** `.agents/skills/` 中（后者只含 14 个共享/入口 skill，无 `trellis-agent-*` 角色 skill）。即：DSH 从项目级 `.dsh/skills/` 发现了它，而不是从 `.agents/skills/`。

---

## 5. 脚本可用性

### 5.1 `python3 ./.trellis/scripts/get_context.py --mode phase --platform dsh`（前 5 行）

````
## Phase Index

```
Phase 1: Plan    → classify, get task-creation consent, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
--- exit: 0 ---
--- total output lines: 87 ---
````

（原始输出第 3 行本身就是一对 Markdown 代码围栏，故此处用四反引号包裹以避免歧义；围栏内容未改动。退出码 0，实际输出 87 行，此处按任务要求只贴前 5 行。）

### 5.2 `python3 ./.trellis/scripts/get_context.py --mode packages`

```
Single-repo project (no packages configured)

Spec layers: agents, checklists, commands, docs, examples, library-assets, platforms, scenarios, scripts, skills, templates, universal-domains
--- exit: 0 ---
```

### 5.3 `python3 ./.trellis/scripts/task.py list`

原始输出含 ANSI 颜色转义（`\x1b[0;34m`、`\x1b[0;36m`），可见文本为：

```
All active tasks:

  - 10-15-dsh-trellis-smoke-test/ (in_progress) [xzc]
  - 10-15-pi-trellis-smoke-test/ (planning) [xzc]

Total: 2 task(s)
--- exit: 0 ---
```

---

## 6. 结论清单

| # | 检查项 | 通过/失败 | 证据引用 |
|---|---|---|---|
| 1a | DSH 环境变量在子会话 shell 中可见（含 `DSH_SHELL=1`、`DSH_SESSION_ID`） | 通过 | 1.1 输出列出 6 个 `DSH_*`，其中 `DSH_SHELL=1`、`DSH_SESSION_ID=ca2bfafa-...` |
| 1b | 存在 `TRELLIS*` 环境变量 | 失败（不存在，非报错） | 1.2 "无输出" + `env\|grep -c '^TRELLIS'` = `0`；三变量均为 `<unset>` |
| 1c | Python 解释器可用、工作目录正确 | 通过 | 1.3 `Python 3.13.5`、`pwd` = `/home/xzc/projects/personal/ai-coding-toolkit` |
| 2a | 子代理提示前导行给出的任务路径可由 `task.py current --source` 解析出来 | **失败** | 第 2 节原始输出：`Current task: (none)` / `Source: none` / `exit: 1`，与前导行 `.trellis/tasks/10-15-dsh-trellis-smoke-test` 不一致 |
| 2b | `(none)` 的原因可归因到确定的 context key，而非随机失败 | 通过 | 2.1 输出 `resolve_context_key(None, None) = 'dsh_ca2bfafa-338c-430c-8139-1862748fa918'`；第 3 节证明同名指针文件不存在 |
| 3a | 本子会话 session id 出现在 dsh 指针文件名中 | **失败** | 第 3 节 `ls ... \| grep -i dsh` 只列出 `9a0daef3...`、`ebf0d88c...` 两个；`grep -c ca2bfafa...` = `0` |
| 3b | 父会话已写入指向本任务的活动任务指针 | 通过 | 3 节父指针 JSON：`"current_task": ".trellis/tasks/10-15-dsh-trellis-smoke-test"`，`"platform": "dsh"` |
| 3c | 子会话能读到父会话设置的活动任务指针 | **失败（已固化的已知限制）** | 3a 失败 + 2a 失败：context key 不同（`dsh_ca2bfafa-*` vs `dsh_session-ebf0d88c-*`），且无单会话兜底（本仓库有 2 个 dsh 指针） |
| 4a | `trellis-agent-implement` skill 可被加载并给出 base directory | 通过 | 第 4 节 base directory = `<repo>/.dsh/skills/trellis-agent-implement`；对应实体 `SKILL.md`（4572 字节）存在 |
| 4b | 该 skill 由项目内 `.dsh/skills/` 提供，而非 `.agents/skills/` | 通过 | 第 4 节 `ls` 输出：`.dsh/skills/` 含 `trellis-agent-implement`，`.agents/skills/` 14 项中无任何 `trellis-agent-*` |
| 4c | skill 加载只发生一次、未再派发子代理 | 通过 | 本会话仅在开始时调用 `skill` 一次；全过程未调用 `subagent` / `subagent_fork` / `workflow` |
| 5a | `get_context.py --mode phase --platform dsh` 可用 | 通过 | 5.1 `exit: 0`，输出 87 行，前 5 行见上 |
| 5b | `get_context.py --mode packages` 可用 | 通过 | 5.2 `exit: 0`，列出 12 个 spec layer |
| 5c | `task.py list` 可用且能列出本任务为 `in_progress` | 通过 | 5.3 `exit: 0`，`10-15-dsh-trellis-smoke-test/ (in_progress) [xzc]` |

### 6.1 交付范围自证

```
=== git rev-parse --abbrev-ref HEAD ===
main
--- exit: 0 ---

=== git status --porcelain (before writing deliverable) ===
?? .trellis/tasks/10-15-dsh-trellis-smoke-test/
?? .trellis/tasks/10-15-pi-trellis-smoke-test/
--- exit: 0 ---
```

说明：写本文件前工作区只有两个未跟踪任务目录，无已跟踪文件被修改；本次交付只新增本任务目录下的 `smoke-evidence.md`。未执行 `git add` / `git commit` / `git push`（任务明确禁止）。

---

## 7. 未验证事项

以下能力我**知道其存在**，但**本任务中没有实际执行过**，因此不给任何通过/失败结论。标注均为「未验证」。

| 事项 | 位置/入口 | 状态 | 说明 |
|---|---|---|---|
| 任务归档 | `task.py archive`、`.trellis/tasks/archive/` | 未验证 | 未运行；PRD AC5（main 上先拒绝、`--skip-branch-validation` 后成功、归档后 `current` 返回 `(none)`）本次未测 |
| 会话 journal 记录 | `add_session.py` / `trellis-finish-work` | 未验证 | 未运行；AC6 的"自动提交只暂存任务路径 + journal 路径"未测 |
| `trellis_wait` 工具 | 依赖 `dsh-trellis` 伴生插件 | 未验证（本运行时未暴露该工具） | 本会话工具清单中无 `trellis_wait`；按 `.dsh/DSH.md` 兜底契约本应改用 `run_in_background: false` 派发子代理——该契约由主会话执行，我作为子代理无法验证 |
| 伴生插件模式（`DSH_TRELLIS_CONTEXT_ID`、`/trellis-status`、`/trellis-finish`） | `dsh-trellis` 插件 | 未验证（未安装） | 第 1.2 节实测 `DSH_TRELLIS_CONTEXT_ID=<unset>`；`~/.dsh/hooks.json` 三个钩子数组均为空、`~/.dsh/profiles/web/` 无 trellis 插件包，故本环境为"无插件"模式，插件能力未被触发 |
| 每轮 workflow 面包屑注入 | 插件提供 | 未验证 | 本会话未观察到面包屑注入，但未做针对性实验 |
| 主会话内的 `task.py current --source` 解析（AC1） | 主会话 shell | 未验证（**我无法验证**） | 我只能在子会话内运行命令；主会话的解析结果不在我的观测范围内。我只能证明：父指针文件内容正确（3b） |
| 评审代理（`trellis-agent-check`）独立复核 | `check.jsonl` | 未验证 | 按递归守卫，我不派发 check 子代理；AC4 由主会话后续处理 |
| 跨会话/重启后的指针持久性 | — | 未验证 | 只观测到当前时刻的两个 dsh 指针文件 |

---

**证据边界声明**：第 1–7 节所有原始输出均由记录者在 `/home/xzc/projects/personal/ai-coding-toolkit` 内实际执行命令获得；Fenced code block 中原样保留输出文本（ANSI 颜色转义已在 5.3 显式说明），未做内容改写。凡属推断或来自源码静态检索的结论，已在相应小节标注为推断。第 8 节由评审代理在独立会话中执行并追加，作者边界见该节开头。

---

## 8. 评审代理独立复核追加（`trellis-agent-check`）

> 本节由**评审代理**（而非第 1–7 节的记录者）在**独立会话**中追加，用于 AC4。评审代理自身
> `DSH_SESSION_ID=ed5d911c-9179-4901-bbde-80cbfc1616af`（与记录者的 `ca2bfafa-...` 不同）。
> 以下命令均由评审代理在其会话内亲自重跑，输出为评审代理自己的输出。

### 8.1 关键命令复跑比对

| 命令 | 与第 1–5 节所贴输出 | 说明 |
|---|---|---|
| `python3 ./.trellis/scripts/task.py current --source` | 一致 | 同样 `Current task: (none)` / `Source: none` / `exit: 1` |
| `env \| grep -i '^DSH' \| sort` | 结构一致（仅 `DSH_SESSION_ID` 一行不同） | 6 个变量、排序、其余 5 项取值逐字相同 |
| `python3 ./.trellis/scripts/get_context.py --mode phase --platform dsh` | 一致 | `exit: 0`、共 87 行，前 5 行逐字相同（含第 3 行的代码围栏行） |
| `python3 ./.trellis/scripts/get_context.py --mode packages` | 一致 | 逐字相同，12 个 spec layer |
| `ls .dsh/skills/ .agents/skills/` | 一致 | 逐行相同；`.agents/skills/` 14 项、`.dsh/skills/` 6 项、`trellis-agent-*` 计 0 |
| `ls -l .dsh/skills/trellis-agent-implement/` | 一致 | `SKILL.md` = 4572 字节 |
| `env \| grep -c '^TRELLIS'` | 一致 | 输出 `0`、`exit: 1` |
| `~/.dsh/hooks.json` | 一致 | 恰为 `PreToolUse` / `SessionStart` / `UserPromptSubmit` 三个数组且均为空 |
| `python3 ./.trellis/scripts/task.py list` | **不一致（环境漂移）** | 现为 `Total: 1 task(s)`，不再是 2——并发 pi 任务已被其会话归档；本任务行仍为 `10-15-dsh-trellis-smoke-test/ (in_progress) [xzc]` |
| `.trellis/.runtime/sessions/` 目录全貌 | **不一致（环境漂移）** | `pi_01a13fff-...json` 现已不存在（评审时仅剩 6 个文件）；其余 6 行文件名与字节大小逐字相同 |

### 8.2 新增独立复核结论（原文件未覆盖的观察）

**（1）`session-<uuid>` / 裸 `<uuid>` 两种 id 形态已获动态证实，不再只是静态推断。**
评审代理自身 `DSH_SESSION_ID=ed5d911c-9179-4901-bbde-80cbfc1616af`，而
`/home/xzc/.dsh/sessions/--home-xzc-projects-personal-ai-coding-toolkit--/` 下同名目录恰为**裸**
`ed5d911c-9179-4901-bbde-80cbfc1616af`（无 `session-` 前缀）。该目录 7 个会话目录的形态为：
`session-*` 4 个（`9a0daef3` 10-14 18:42、`a796e795` 10-15 08:38、`c30c28c0` 10-15 08:54、`ebf0d88c` 10-15 22:33），
裸 uuid 3 个（`b5ce567d` 22:37、`ca2bfafa` 22:42、`ed5d911c` 22:46）。
即：**会话目录名 == 该会话的 `DSH_SESSION_ID`**，且**子代理会话为裸 uuid**——与 3.1 节判断一致。
第 158–159 行的 `ls` 只贴了 3 行；评审代理另行确认 08:38 / 08:54 两个 `session-*` 目录确实存在，
故第 152 行"10-15 08:38/08:54"的说法成立。

**（2）AC1 的机制已被独立验证（但主会话实际执行仍不可观测）。**
评审代理用父会话身份重跑：

```
=== simulate PARENT identity (session-ebf0d88c) ===
Current task: .trellis/tasks/10-15-dsh-trellis-smoke-test
Source: session:dsh_session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2
--- exit: 0 ---
```

这证明"父指针可被解析 + Source 命名空间正确"成立；但**主会话是否真的执行过该命令、其 stdout 是否如此，
本文件仍无法判定**。另注：PRD AC1 写作 `session:dsh_session-ebe...`，而实际 id 前缀为 `ebf0d88c`
（`ebe` 与 `ebf` 不符），AC1 的字面串按实际值应为 `session:dsh_session-ebf0d88c-3fb9-4517-b522-ee72ff93abc2`。

**（3）`randomUUID()` 归因的边界需要收窄。**
第 160 行引用的 `dsh-subagent-in-process-driver/lib/index.js:166`
（`const childId = brandString(randomUUID());`；同文件第 1 行 `import { randomUUID } from "node:crypto";`）
经复核**逐字准确**，且该 `childId` 正是随后 `agents.create({ sessionId: childId, ... })` 的 `sessionId`——
这是"子代理会话 id 为裸 uuid"的直接源码依据（`dsh-subagent-spawn-in-process` 与
`dsh-subagent-fork-in-process` 两个包内均无 `randomUUID`，说明二者共用该驱动，故结论对 spawn / fork 都适用）。
**但 `session-` 前缀并非主会话专属**：`dsh-api-session-controller/lib/index.js:806` 的会话 fork 路径
同样以 ``childId = brandString(`session-${randomUUID()}`)`` 创建**子**会话。因此准确表述是
"**前缀取决于创建路径**（`dsh-headless`、`dsh-api-session-controller` 主会话与 api 会话 fork 带前缀；
in-process 子代理为裸 uuid）"，而不是"主 / 子会话二分"。

**（4）结论表 4c 的"通过"属自证，无法由本文件复核。**
4c 描述的是记录者会话自身的工具调用序列（"skill 只加载一次、未再派发子代理"），
文件中未附任何工具调用日志，评审侧只能将其记为**未附证据的自述**，不宜计作可复核的"通过"。

**（5）AC6 相关：评审时 git 索引中已存在与本任务无关的已暂存文件。**
评审代理执行 `git status --porcelain` 与 `git diff --cached --name-only` 得到：索引中已有 4 个
`.trellis/tasks/archive/2026-10/10-15-pi-trellis-smoke-test/*` 处于已暂存（`A `）状态，
另有 `.trellis/workspace/xzc/index.md`、`.trellis/workspace/xzc/journal-7.md` 为未暂存修改；
`HEAD` 仍为 `10e239f trellis补充zcode/pi/dsh`（无自动提交产生的新提交）。
这是**并发会话造成的环境状态，不属于本任务**，但它直接影响 AC6 的判定条件
（"最终 `git status` 除任务归档外的无关文件保持未暂存"在当前索引状态下不成立），
且 AC5 / AC6 执行时若直接 `git commit`，会把上述无关文件一并提交。
