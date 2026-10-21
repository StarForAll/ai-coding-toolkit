# Findings — workflow-state 解析与每轮提示注入

判定基线：E1 = 本次实际运行取证；E2 = 仅静态推断；E3 = 文档/测试声明。
审计对象：`~/.dsh/profiles/web/node_modules/dsh-trellis` → 符号链接 →
`dsh-plugins/dsh-trellis`（0.3.7，git 未提交目录）。真实装载链已核实：
`~/.dsh/profiles/web/cordis.patch.yml` 含 `- id: dsh-trellis`，
`dsh --profile web --dump-config` 第 1303–1307 行出现该条目。

## 1. 探针 A：`no_task` 跨注释匹配 —— 真实存在（E1）

### 复现命令

```bash
cd dsh-plugins/dsh-trellis
node --input-type=module -e '
import {readFileSync} from "node:fs";
import {parseWorkflowStateBlocks} from "./lib/workflow.js";
const b=parseWorkflowStateBlocks(readFileSync("/home/xzc/projects/personal/ai-coding-toolkit/.trellis/workflow.md","utf8"));
for (const [s,body] of b) console.log(s, body.length, body.split("\n").length);
'
```

### 实测数据（本仓库 `.trellis/workflow.md`，773 行）

| 状态 | 插件 JS 解析 | Codex/Claude Python hook 解析 | 差异 |
| --- | --- | --- | --- |
| `no_task` | **4605 字符 / 66 行**，首行 `→ no active task; before Phase 1` | **421 字符 / 3 行**，首行 `No active task. First classify…` | 污染 |
| `stale` | 459 / 3 | 459 / 3 | 相同 |
| `task_error` | 345 / 3 | 345 / 3 | 相同 |
| `planning` | 449 / 4 | 449 / 4 | 相同 |
| `planning-inline` | 439 / 4 | 439 / 4 | 相同 |
| `in_progress` | 1635 / 5 | 1635 / 5 | 相同 |
| `in_progress-inline` | 325 / 3 | 325 / 3 | 相同 |
| `completed` | 80 / 1 | 80 / 1 | 相同 |
| `my-status`（文档示例块） | 25 / 1 | 25 / 1 | 相同 |

Python 侧实测命令：

```bash
python3 - <<'EOF'
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("h",".codex/hooks/inject-workflow-state.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print({k:(len(v),len(v.splitlines())) for k,v in m.load_breadcrumbs(Path("."),{}).items()})
EOF
```

### 根因（E1）

`lib/workflow.js:14-15`：

```js
const STATUS_RE =
  /\[workflow-state:([A-Za-z0-9_-]+)\]([\s\S]*?)\[\/workflow-state:\1\]/g;
```

开标签后**没有"必须紧跟换行"的约束**。`.trellis/workflow.md:123` 的 HTML 注释里有：

```
    [workflow-state:no_task]      → no active task; before Phase 1
```

于是 `matchAll` 从第 123 行起匹配，一路吃到第 189 行真正的闭合标签
（`[/workflow-state:no_task]`），body = 第 123 行标签后的全部注释正文 + 第 186–188 行
真正指引。Codex/Claude hook 的正则带约束：

```python
r"\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n(.*?)\n\s*\[/workflow-state:\1\]"
```

`]` 后是空格 + `→`，`\s*\n` 不成立，所以跳过注释，匹配第 185 行真块。

其余状态未被污染的原因：`no_task` 的这次匹配吞掉了 123–189 行，正好覆盖注释里
`task_error/planning/in_progress/completed` 等标签的"提及"，它们真正的块在 189 行之后
才被扫描到，因此干净。`stale` 真块正好在 189 行之后，同样干净。

### 截断放大后果（E1）

`lib/breadcrumb.js` + `lib/text.js` 以 `maxBytes`（`lib/config.js` 默认 4096）做 UTF-8 截断：

| 场景 | 模型实际收到的 `no_task` breadcrumb | 真正指引是否可见 |
| --- | --- | --- |
| 本仓库（body 4605） | **4096 字节 / 4063 字符**，开头 `→ no active task; before Phase 1`，结尾 `…add-subtask <parent> <child>\`, and u` | **完全不可见**（尾被截断） |
| 全新 `trellis init` 项目（body 4091，60 行） | 4096 字节 / 4065 字符，开头同样是注释尾巴，结尾 `…enter the planning ph` | 只剩 2.5 行，且最后一行被切断 |
| 无预算（`maxBytes=0`） | 4675 字符，开头仍是注释尾巴 | 可见，但被 60+ 行注释噪声淹没 |

本会话的实时证据（web profile 真实运行）：`~/.dsh/sessions/--home-xzc-projects-personal-ai-coding-toolkit--/session-b91f0b24-d68b-4826-823d-a192c535f752/session.v4.jsonl.zstd`
解压后，`source.kind=dsh-trellis, form=breadcrumb, status=no_task` 的消息为
**4063 字符 / 4096 字节**，与上表一致；`source.form=bootstrap` 的消息 138 字符正常。
这正是用户侧观察到的"4,063 字符 breadcrumb"。

端到端复核（见 `e2e-session.md`）：全新项目 + 独立 profile + 本地
mock LLM，模型请求里的该消息 4065 字符，开头 `→ no active task; before Phase 1`，
`[workflow-state:task_error]`、`[workflow-state:planning]` 等注释行被当成正文注入。

### 影响面（E1）

- 受影响的只有 `no_task` 一个状态的**正文内容**；但 `no_task` 是"没有活动任务"时的
  唯一每轮频道，恰是决定"先分类、先征得建任务同意"的那一段。
- 影响所有使用 trellis 0.7.0-beta.4 `workflow.md` 模板的项目：全新 `trellis init`
  生成的第 123 行注释与仓库内一致（实测 `/tmp/trellis-e2e/.trellis/workflow.md:123`）。
- `maxBytes` 调大不能修复缺陷：只是把注释噪声完整注入，真正指引仍排在 60+ 行之后。
- 与本缺陷无关但同处解析层：`my-status` 这类文档示例块也会被解析进 Map（两平台一致，
  仅当任务状态恰为 `my-status` 才会用到，无实际影响）。

## 2. 状态映射与 Codex 的差异（E1）

`lib/workflow.js:157-162` 的 `mapStatus` 只认 `planning` / `in_progress` / `task_error`，
其余一律 `no_task`。实测（临时项目真实 task.json + 真实 `resolveTrellisState`）：

| task.json status | 插件输出 | Codex hook 输出 |
| --- | --- | --- |
| `completed` | **no_task**（并触发 bootstrap，提示"创建任务"） | `[workflow-state:completed]` 正文 80 字符 |
| `blocked`（任意未知状态） | **no_task** | `Refer to workflow.md for current step.` |
| 指针指向已删除目录（stale） | **task_error**（"Inspect the active task directory…"） | Trellis 解析器 `stale=True` → `[workflow-state:stale]` |
| `planning-inline` / `in_progress-inline` | 永不产生（不读 `codex.dispatch_mode`） | 按 `codex.dispatch_mode: inline` 产出 |

补充证据：Trellis 自带解析器对同一份损坏指针返回
`task_path=.trellis/tasks/10-21-does-not-exist stale=True source=session`，
而插件返回 `task_error`；本仓库 `workflow.md` 明明定义了 `stale` 块（459 字符），
插件却永远读不到它。

## 3. 项目级工作流选择与跳过关键字（E1）

| 能力 | Codex/Claude hook | dsh-trellis |
| --- | --- | --- |
| 任务级 workflow（`task.json.workflow` → `.trellis/workflows/<id>.md`） | 支持（`common.workflow_selection.resolve_workflow_md`） | **忽略**，永远读 `.trellis/workflow.md` |
| 个人/团队默认 workflow（`.developer workflow=`、config `default_workflow`） | 支持（同一优先级链） | **忽略**（同上） |
| `prompt_injection.skip_keyword`（项目 `.trellis/config.yaml`） | 支持（`_resolve_skip_keyword`） | **忽略**；只用插件自身配置 `skipKeyword`（默认 `no-trellis`） |

实测：

```bash
# 插件：忽略任务级 workflow
node --input-type=module -e '... resolveTrellisState({contextKey:"dsh_probe"}) ...'
# -> status: planning, body: "Load \`trellis-brainstorm\`..."，不含 ALT_WORKFLOW_MARKER

# Trellis 解析器：正确选中变体
python3 -c 'from common.workflow_selection import workflow_md_for_task; ...'
# -> /tmp/trellis-e2e/.trellis/workflows/alt.md（含 2 个 ALT_WORKFLOW_MARKER）
```

```bash
# 项目 config 设 prompt_injection.skip_keyword: skip-trellis 后
echo '{"cwd":"/tmp/trellis-e2e","prompt":"please skip-trellis this turn"}' \
  | python3 .codex/hooks/inject-workflow-state.py     # 无输出（正确跳过）
# 插件 compose("please skip-trellis this turn") -> 2 条消息（breadcrumb + bootstrap，未跳过）
```

## 4. 验证通过（无问题）

- 真实 web 会话中 breadcrumb / bootstrap 的注入位置、去重、消息 source 字段（E1）。
- `no_task` 下 bootstrap 只发一次；`planning/in_progress/task_error` 切换时不重发（E1，会话
  transcript 只出现一次 bootstrap）。
- fork 会话带 `parentSession` 但仍按根会话处理（不会被误判为子代理）（E1）。
- 子代理会话无自身任务时静默，不注入矛盾 breadcrumb（E1）。
- 插件配置默认 `skipKeyword: "no-trellis"` 生效（`no-trellis` 提示词 → 0 条消息）（E1）。
- `maxBytes=0` 关闭注入；`truncateUtf8` 不切断 UTF-8 码点（E1：4096 字节截断点为完整字符）。
- 单元测试：`node --test test/*.test.js` → 262 pass / 4 skipped / 0 fail（E1，仅作基线）。

## 5. 无法验证

- 压缩（compaction）后 projection 重新投递：需要真实长会话压缩，未构造。
- `my-status` 等文档示例标签对真实任务状态的影响：需任务状态恰好等于示例值，未构造。
