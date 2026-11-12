# 设计：wf 第二轮 dogfood 缺陷修正

## 1. 边界与原则

- 只改 `docs/workflows/wf/payload/**`、`docs/workflows/wf/skills/**`、`docs/workflows/wf/README.md`、
  三份上位稿中与本轮结论直接冲突的句子、`AGENTS.md`、`scripts/` 内的构建/测试代码，以及重建的发行树。
- 每个判据只保留一处实现；调用点只消费（`.trellis/spec/docs/wf-delivery-discipline.md` §4）。
- 不改目标项目 `~/projects/personal/traffic_monitor`；不代跑人的终端确认；不动 B/C 两项。

## 2. 交付集合（R1）

### 2.1 契约

```python
# scope.delivery_set(root, task, *, receipts=None) -> dict
{
  "paths": [...],          # 排序后的交付集合（内容域）
  "buckets": {"e": [...], "f": [...], "covered_f": [...], "uncovered_f": [...], "v": [...]},
  "excluded": [...],       # vendor / 控制记录
}
```

构成：`e ∪ covered_f ∪ 未释放的策展路径 ∪ {.wf/baseline.md, .wf/project-config.json}`，再排除 vendor。
`covered_f` 由 `authorize.covers(task_dir, "expand", f, root=...)` 判定；`uncovered_f` 原样返回，
由 Check 继续按 `WF_SCOPE_VIOLATION` 阻断（本轮不改变阻断语义）。

### 2.2 消费者

| 消费者 | 现状 | 改后 |
|---|---|---|
| `check.object_paths` | 只取 e + 策展 + 固定两项 | 直接返回 `delivery_set()["paths"]` |
| `tasks.pending_delivery_paths` | e ∩ 未提交 | `delivery_set()["paths"]` ∩ 未提交（已批准扩面因此进提交/预检） |
| `review` 材料 | e ∪ f（另一套） | `delivery_set()["paths"]` |

`check.run_check_scope` 的 f 阻断分支改为消费 `uncovered_f`，不再自己再调 `covers()`；
展示用的 `buckets.e ∪ f` 事实保留（供人读），但不作为任何判定输入。

### 2.3 兼容性

`object_paths` 变大只在“存在已获批扩面路径”时发生；这类任务的 Check 锚点会变化一次，
需要重新 Check（既有机制本来就要求内容变化后重查）。无记录字段变化、无迁移步骤。

风险：`_spec_coverage` 也按 `object_paths` 匹配 spec，扩面路径会新增策展要求。
这是“碰到受管路径就要读规则”的既有语义，保留；若测试显示与既有断言冲突，先归因再决定是否
把 spec 匹配口径单独参数化（不在本轮静默放宽）。

## 3. 材料物化（R2）

### 3.1 契约

```python
# review.materialize_delivery(ctx, paths) -> {"text": str, "files": [...], "problems": [...], "empty": bool}
```

逐路径：

1. `git status --porcelain=v1 -z --untracked-files=all -- <path>` 取该路径状态；
2. 未跟踪（`??`）→ `git diff --no-index --no-color -- /dev/null <path>`（退出码 1 = 有差异，按成功）；
3. 已跟踪 → `git diff --no-color HEAD -- <path>`（同时覆盖已暂存与未暂存；删除路径给删除 hunk）；
4. 输出为空且路径存在 → 记 `files[].note = "metadata-only"`（如仅权限位变化），不伪造内容；
5. 含 `Binary files ... differ` → 追加显式标记行（路径 + 字节数 + 摘要），不让 reviewer 以为无内容；
6. 任何非 0/1 退出码、`OSError`、路径不可读 → `problems` 追加 `{path, reason, code}`，
   并在 `text` 里写 `# [wf-material-missing] <path>: <reason>`。

### 3.2 落盘

`review.context` 写 `materials/diff.patch` 与 `materials/status.json`：

- `paths` 为空 → `diff.patch = "# 本任务交付面为空（无已归属路径）"`，`status.empty = true`；
- `paths` 非空但某路径取片段失败 → `diff.patch` 含 missing 标记，`status.problems` 非空；
- 只有“路径为空”才允许出现“无差异”类文案；`# 无工作树差异` 这一句删除。

`facts` 增 `materials_status`（路径）与 `material_problems`（条数 + 前几条），reviewer 与 action 侧
无需读文件也能看到“材料是否完整”。

## 4. 代次由会话运行态携带（R3）

### 4.1 写入侧

`writer.save(root, record)` 是所有写权持久化的唯一出口（18 个调用点都经过它）。新增：

```python
if record.get("state") == "held" and (holder or {}).get("kind") == "session":
    session.update_runtime(root, holder["id"], writer_generation=holder["generation"])
```

`session.update_runtime()` 为新增的**合并写**（读现有侧车 → 覆盖给定字段 → 写回），避免覆盖
`runs.py` 存在同一侧车里的游标字段；写失败按机制稿只降级可见，不阻断。

### 4.2 读取侧

`cli.Context.require_held()`：

1. 显式 `inputs.generation` 存在 → 用它，且比较失败仍是 `WF_GENERATION_STALE`；
2. 缺失 → 读本会话侧车 `writer_generation`；存在则用，并在校验通过后调用一次
   `writer.sync_session_generation()`（幂等），解决“升级前已持权、侧车还没建立”的迁移；
3. 仍缺失 → `WF_GENERATION_STALE`，`facts.exits` 明确两条：显式携带一次 generation 后重试；
   重新 `writer release` + `writer acquire`。

**不读 writer 当前代次**：侧车记录的是调用者取得写权时拿到的值，侧车陈旧仍会被拦。

### 4.3 指引同步

`wf-start`/`wf-finish` 的“自动模式下不需要手写信封”改为“身份由执行边界派生；写命令的代次由
本会话运行态携带（不用手填）；显式信封仍可覆盖”。`task-approve` 帮助里“从 facts.generation 取”
的强制句改成“可显式覆盖；缺省取本会话运行态”。

## 5. 契约回显与骨架（R4）

- `tasks.cmd_task_check` 成功回显：
  `plan.complexity == "complex"` → “复杂任务：先 `review-launch` 发起审查（wf-review），再请人 finish”；
  否则 → 现文案。
- `review.context` 的占位文件改为完整骨架：状态行 + `<!-- wf-review-report:v1 -->` + ```json 块
  （`protocol`/`task-id`/`round`/`review-time`/`review-focus`/`check-anchor` 预填，
  `read-scope`/`excluded-scope`/`axes`/`findings`/`verdict` 留空位）+ 一行 lint 命令提示。
- `skills/wf-review/SKILL.md`：删 `scope-exceptions` 漂移；写明自动身份模式需要 `--as <cli>`；
  增加“导入前先 `wf lint report --file <report_path>`”的步骤。

## 6. 帮助取值域（R5）

`COMMAND_HELP` 里 `task-approve.inputs.decision[].choice` 由
`decisions.DOMAINS["plan_approval"] | DOMAINS["mechanical_revision"]` 生成（保持“规范值在首”的顺序），
不再手写字符串。新增断言：帮助文本里的每个取值都能通过 `decisions.accepts()` 对应域。

## 7. 文档与发行（R6）

| 文件 | 改动 |
|---|---|
| `AGENTS.md` | wf 源树现状描述（不再是空路径） |
| `docs/workflows/wf/README.md` | 11 → 13 个 skill（三处） |
| `docs/workflows/wf-framework-design.md` §301 | “会话绑定/项目写入权记录登记进 Git”改为运行态（gitignore），并说明理由与后果 |
| `docs/workflows/wf-framework-mechanism.md` §10.1 | 运行态表补齐忽略集合五项，声明清单 `gitignore_managed.lines` 为唯一枚举 |
| `docs/workflows/wf-framework-implementation.md` §目录注释 | 两处路径标注改为“运行态（gitignore）” |
| `payload/install.py` | `managed_segment` 缺 `gitignore_managed.lines` 时明确拒绝（`WF_ASSET_DECISION`），删除第二份常量 |

## 8. 风险与回退

| 风险 | 处理 |
|---|---|
| 已持权但侧车缺失的旧安装 | `require_held` 成功后自愈；失败出口给出显式携带一次的办法 |
| 交付集合变大影响锚点 | 只在扩面已获批时发生；重查一次，语义正确 |
| 材料变大/含二进制 | 二进制只给标记，不内联；文本仍按路径分块 |
| 帮助文本动态生成出错 | 单测直接断言“帮助值 ⊆ 登记域”，失败即阻断 |
| 文档修改越权 | 只改与代码直接冲突的句子，保留其余论证 |

回退：`git revert` 本轮实现提交 + `scripts/build-wf-release.py --version 0.1.0` 重建发行树；
侧车文件在 `.wf/.runtime/`（gitignore），删除即回退，无需数据迁移。
