# browser_bookmark_cleaner_rchiver 轻量结构性迁移实施蓝图

> 状态：只读分析完成，尚未进入目标项目实现。
> 目的：把本次升级按《目标项目兼容升级方案指导》与《结构性迁移设计》整理成可执行蓝图，供用户确认后实施。

---

## 1. 规范符合性

本次分析链已满足以下规范前置：

1. 当前仓库 workflow 源资产已完成本轮兼容升级。
2. 目标项目已升级到当前最新 Trellis 版本：
   - 目标项目 `.trellis/.version` = `0.4.0-beta.9`
   - 本机 `trellis -v` = `0.4.0-beta.9`
3. 已按 `A/B/C` 三态执行只读分析，而不是直接对目标项目做兼容升级。

本次分析输入：

- `A_ROOT`: `/tmp/workflow-upgrade-a-HCCz6w`
- `B_ROOT`: `/tmp/workflow-upgrade-b-HCCz6w`
- `C_ROOT`: `/ops/projects/personal/browser_bookmark_cleaner_rchiver`
- 分析报告：`/tmp/workflow-upgrade-report-browser-bookmark-cleaner-rchiver.md`

---

## 2. 迁移结论

本次升级应按“轻量结构性迁移”处理，不应继续视为普通兼容升级。

原因：

1. `A/B/C` 结果为：
   - `keep`: 8
   - `add`: 4
   - `replace`: 0
   - `merge`: 26
   - `delete`: 4
2. `merge` 明显占主导，已符合“目标项目私有漂移过重”的结构性迁移触发条件。
3. 当前目标项目存在阶段命令语义迁移，而不是简单的旧文件退役：
   - 旧 `self-review` -> 新 `check`
   - 旧 `check` -> 新 `review-gate`
   - 旧 `self-review-check.py` -> 新 `check-quality.py`
   - 以上映射描述的是**目标项目内部的旧结构 -> 新结构**，不是源仓库内部仍保留这些旧文件
4. 安装记录仍停留在旧结构：
   - `trellis_version` 仍记录为 `0.4.0-beta.8`
   - `commands` 仍包含 `self-review`
   - `scripts` 仍包含 `self-review-check.py`

因此，后续实现必须把“语义迁移 + 私有漂移保留 + 路由清理”作为一个整体处理。

---

## 3. 迁移范围

只处理 workflow 托管层，不处理业务代码。

### 3.1 主迁移范围

- Claude 命令目录：`.claude/commands/trellis/`
- OpenCode 命令目录：`.opencode/commands/trellis/`
- Codex skills 目录：`.agents/skills/`
- Shared helper scripts：`.trellis/scripts/workflow/`
- 安装记录：`.trellis/workflow-installed.json`

### 3.2 附加必查范围

- 目标项目 `AGENTS.md` 中由安装器写入的 `workflow-nl-routing` 路由块
- 目标项目 `start.md` 中仍引用旧 `self-review` / `check` 阶段链的路由片段
- reviewer CLI 能力前置：
  - `multi-cli-review`
  - `multi-cli-review-action`

说明：

- 上述 reviewer / 协调者能力只验证“实际执行环境是否已具备”，不把它们当作本轮目标项目 workflow-managed 资产清单的一部分。
- 也就是说，本轮蓝图可以要求“先确认能力可用”，但不把 `multi-cli-review` / `multi-cli-review-action` 写进目标项目的 `workflow-installed.json`。
- 这里的 `AGENTS.md` / `start.md` 都指**目标项目安装态文件**，不是当前源仓库根目录下用于维护本仓库的规则文件或已部署副本。

### 3.3 本次不处理

- 业务代码
- Trellis 非 workflow 托管的原生命令
- `.codex/hooks.json` / `.codex/hooks/session-start.py`
- 非 workflow 直接依赖的 `.trellis/spec/` 业务规范资产

---

## 4. 迁移动作矩阵

补充说明：

- 本表中的“当前源”统一指当前仓库的 workflow source-of-truth，即 `docs/workflows/新项目开发工作流/commands/*.md` 与 `docs/workflows/新项目开发工作流/commands/shell/*.py`，不是本仓库当前 `.claude/` / `.opencode/` / `.agents/` 下的部署副本。
- `A/B/C` 报告里的同名 `merge` 是**文件级动作分类**；本表里的 `旧 check -> 新 review-gate`、`旧 self-review -> 新 check` 是**目标项目内部的语义迁移映射**。实施时必须先抽取旧语义里的私有规则，再回填到新结构，而不是把 `merge` 误读成“只改同名文件即可”。

| 旧资产 / 现状 | 目标资产 / 目标语义 | 动作 | 说明 |
|---|---|---|---|
| `self-review`（三端） | `check`（三端） | `extract + replace + cleanup` | 先从目标项目旧 `self-review` 提取仍需保留的私有规则，再以源仓库新 `check` 为主内容回写到目标项目 `check`，最后清理旧 `self-review` |
| `check`（三端） | `review-gate`（三端） | `extract + add + cleanup` | 先从目标项目旧 `check` 提取门禁私有规则，再新建/补齐 `review-gate`；同时保留一条独立动作：把目标项目当前同名 `check` 回归为源仓库新 `check` 语义。也就是说，`A/B/C` 中 `check=merge` 与这里的 `旧 check -> 新 review-gate` 是重叠但不等价的两层动作 |
| `self-review-check.py` | `check-quality.py` | `inspect + add + cleanup` | 源仓库已有 `check-quality.py`；目标项目需人工检查旧脚本私有逻辑是否要并入，再部署 `check-quality.py`，最后删除旧 `self-review-check.py` |
| 缺失的 `review-gate` 三端资产 | 当前 workflow source-of-truth `review-gate` | `add` | 正式新增目标入口；源内容以 `docs/workflows/新项目开发工作流/commands/review-gate.md` 及对应 skill/source 为准 |
| `brainstorm` | 当前源 `brainstorm` | `merge` | 目标项目已有私有改动 |
| `design` | 当前源 `design` | `merge` | 目标项目已有私有改动 |
| `plan` | 当前源 `plan` | `merge` | 目标项目已有私有改动 |
| `test-first` | 当前源 `test-first` | `merge` | 目标项目已有私有改动 |
| `delivery` | 当前源 `delivery` | `merge` | 目标项目已有私有改动 |
| `start` | 当前补丁型 `start` | `merge` | 目标项目保留了项目私有阶段路由调整 |
| `finish-work` | 当前补丁型 `finish-work` | `merge` | 当前 `--check` 已检测到补丁缺失，但目标内容本身并非可直接覆盖 |
| `record-session` | 当前补丁型 `record-session` | `merge` | marker 正常，但内容已偏离最新期望状态 |
| `metadata-autocommit-guard.py` | 当前源同名脚本 | `merge` | 当前脚本存在目标项目私有漂移 |
| `.trellis/workflow-installed.json` | 新安装记录 | `rewrite` | 只能在迁移完成后回写，不能提前“补记录” |

---

## 5. 目标文件清单

### 5.1 语义迁移核心文件

Claude:

- `.claude/commands/trellis/self-review.md`
- `.claude/commands/trellis/check.md`
- `.claude/commands/trellis/review-gate.md`

OpenCode:

- `.opencode/commands/trellis/self-review.md`
- `.opencode/commands/trellis/check.md`
- `.opencode/commands/trellis/review-gate.md`

Codex:

- `.agents/skills/self-review/SKILL.md`
- `.agents/skills/check/SKILL.md`
- `.agents/skills/review-gate/SKILL.md`

说明：

- 目标项目当前 Codex workflow 实际生效路径是 `.agents/skills/`
- 本次迁移不使用 `.codex/skills/` 作为主写入路径
- 如目标项目同时存在 `.codex/skills/`，只检查其中是否残留与 workflow 阶段技能重名的旧副本；无关资产不纳入本轮清理

Shared helper:

- `.trellis/scripts/workflow/self-review-check.py`
- `.trellis/scripts/workflow/check-quality.py`

### 5.2 路由与阶段链文件

- `AGENTS.md`
- `.claude/commands/trellis/start.md`
- `.opencode/commands/trellis/start.md`

说明：

- `AGENTS.md` 的核对重点是安装器生成的 `<!-- workflow-nl-routing-start --> ... <!-- workflow-nl-routing-end -->` 区块
- `start.md` 的核对重点是目标项目当前仍保留旧 `self-review` / `check` 引用的阶段路由与触发词片段
- 不以当前源仓库根 `AGENTS.md` 或当前仓库 `.claude/.opencode` 已部署副本的精简程度，反推目标项目是否需要迁移这些旧引用

### 5.3 仍需人工 merge 的同名资产

- `.claude/commands/trellis/brainstorm.md`
- `.claude/commands/trellis/design.md`
- `.claude/commands/trellis/plan.md`
- `.claude/commands/trellis/test-first.md`
- `.claude/commands/trellis/delivery.md`
- `.opencode/commands/trellis/brainstorm.md`
- `.opencode/commands/trellis/design.md`
- `.opencode/commands/trellis/plan.md`
- `.opencode/commands/trellis/test-first.md`
- `.opencode/commands/trellis/delivery.md`
- `.agents/skills/brainstorm/SKILL.md`
- `.agents/skills/design/SKILL.md`
- `.agents/skills/plan/SKILL.md`
- `.agents/skills/test-first/SKILL.md`
- `.agents/skills/delivery/SKILL.md`
- `.claude/commands/trellis/finish-work.md`
- `.opencode/commands/trellis/finish-work.md`
- `.agents/skills/finish-work/SKILL.md`
- `.claude/commands/trellis/record-session.md`
- `.opencode/commands/trellis/record-session.md`
- `.trellis/scripts/workflow/metadata-autocommit-guard.py`

### 5.4 迁移完成后再清理的旧资产

- `.claude/commands/trellis/self-review.md`
- `.opencode/commands/trellis/self-review.md`
- `.agents/skills/self-review/`
- `.trellis/scripts/workflow/self-review-check.py`

---

## 6. 建议实施顺序

### Phase 0: 冻结与备份

1. 为目标项目创建独立升级分支。
2. 备份以下目录：
   - `.claude/commands/trellis/`
   - `.opencode/commands/trellis/`
   - `.agents/skills/`
   - `.trellis/scripts/workflow/`
   - `.trellis/workflow-installed.json`
3. 记录当前 `git status --short` 与关键文件 diff。
4. 在任何删除或覆盖前，先做一次只读盘点并保存结果，供 Phase 2 路由迁移与 Phase 4 清理复核：

```bash
rg -n "self-review|self-review-check\\.py|review-gate|/trellis:self-review|/trellis:check" \
  AGENTS.md \
  .claude/commands/trellis \
  .opencode/commands/trellis \
  .agents/skills \
  .trellis/scripts/workflow
```

### Phase 1: 语义迁移主轴

1. 明确源仓库 source-of-truth：
   - `docs/workflows/新项目开发工作流/commands/check.md`
   - `docs/workflows/新项目开发工作流/commands/review-gate.md`
   - `docs/workflows/新项目开发工作流/commands/shell/check-quality.py`
   - 上述文件定义的是**正文语义与共享契约**；目标项目 `.claude/.opencode/.agents` 的安装态文件仍需保持各自平台要求的 frontmatter / SKILL 包装格式
   - 对 `review-gate` 这类目标项目当前尚缺失的资产，不要直接把 `docs/workflows/.../*.md` 原样复制到 `.claude/commands/trellis/` 或 `.agents/skills/`；应沿用目标项目现有同平台文件格式包装 source body
2. 从目标项目旧 `self-review` 中提取仍需保留的私有规则，落到临时对照文档。
3. 从目标项目旧 `check` 中提取仍需保留的门禁规则，落到临时对照文档。
4. 对第 2-3 步的提取结果先做一次 diff / 去重：
   - 若同一条目标项目私有规则同时出现在旧 `self-review` 与旧 `check`，只能迁移一次，避免重复吸收到新结构
   - 归属原则：实现偏差自检类规则优先归入新 `check`；多 CLI 审查门禁类规则优先归入新 `review-gate`
   - 去重结果要回写到临时对照文档，至少保留：规则名 / 来源文件 / 归入 `check` 或 `review-gate` / 原因
5. 以源仓库 `check.md` 为蓝本，合并第 2 步确认保留、且经第 4 步去重后的私有规则，形成目标项目新 `check`。
6. 以源仓库 `review-gate.md` 为蓝本，合并第 3 步确认保留、且经第 4 步去重后的私有规则，形成目标项目新 `review-gate`。
7. 以源仓库 `check-quality.py` 为蓝本，人工审查旧 `self-review-check.py` 中是否有必须保留的目标项目逻辑；若有则并入，否则直接部署新脚本。
8. 路径模式适配：
   - 源仓库命令文案中的 helper 源路径需要落到目标项目 `.trellis/scripts/workflow/`
   - 当前安装器 / 兼容升级脚本的既有改写契约是：`<WORKFLOW_DIR>/commands/shell/` → `.trellis/scripts/workflow/`
   - 至少显式核对：`check.md` 中 `python3 <WORKFLOW_DIR>/commands/shell/check-quality.py` 在目标项目落地后应改写为 `python3 .trellis/scripts/workflow/check-quality.py`
   - 不允许把 `<WORKFLOW_DIR>/commands/shell/...` 直接原样写入目标项目命令文案

### Phase 2: 路由更新

1. 先盘点所有旧引用，再更新 `AGENTS.md` 自然语言路由：
   - 先执行：

```bash
rg -n "self-review|review-gate|/trellis:check|/trellis:self-review" \
  AGENTS.md \
  .claude/commands/trellis/start.md \
  .opencode/commands/trellis/start.md
```

   - 再按清单逐项迁移：
     - “自审/自检” 路由从 `self-review` 改到 `check`
     - “补充审查/多人审查” 路由从 `check` 改到 `review-gate`
     - 为 `review-gate` 增加独立触发词行
2. 更新 `.claude/commands/trellis/start.md`
3. 更新 `.opencode/commands/trellis/start.md`
4. 同步调整前后阶段描述：
   - `start -> check -> review-gate -> finish-work`
5. 显式核对下列旧引用点：
   - `AGENTS.md` 中所有 `/trellis:self-review` 与 `/trellis:check` 的路由描述
   - `start.md` 中“代码实现完成 + 无 self-review.md”分支
   - `start.md` 中“自审完成 -> `/trellis:check`”分支
   - `start.md` 自然语言触发词表中的“自检”“补充审查”“多人审查”等条目

### Phase 3: 其余 merge 资产

按文件逐个比较当前源资产与目标项目私有漂移，决定：

- 哪些内容应上收为共享规则
- 哪些内容只属于该目标项目
- 哪些内容已无价值，应丢弃

### Phase 4: 清理与记录回写

1. 删除已被迁移吸收的旧 `self-review` 资产。
2. 删除旧 `self-review-check.py`。
3. 回写 `.trellis/workflow-installed.json`：
   - `trellis_version`
   - `cli_types`
   - `commands`
   - `overlay_commands`
   - `added_commands`
   - `scripts`
   - 保留或按实更新已有 lifecycle 字段（如 `installed` / `updated` / `previous_version` / `initial_pack` / `bootstrap_task_removed`），不凭空伪造
   - `commands` / `overlay_commands` / `added_commands` / `scripts` 的目标值应以当前 workflow 共享定义为准，即 `workflow_assets.py` 中的 `DISTRIBUTED_COMMANDS`、`OVERLAY_BASELINE_COMMANDS`、`ADDED_COMMANDS`、`HELPER_SCRIPTS`
   - 本轮语义迁移下的最低更新规则：从 `commands` 中移除 `self-review`；保留 `check` 作为 overlay 命令；新增 `review-gate` 到 `commands` 与 `added_commands`；`scripts` 以 `check-quality.py` 替换 `self-review-check.py`
4. 目标安装记录示例：

```json
{
  "trellis_version": "0.4.0-beta.9",
  "cli_types": [
    "claude",
    "opencode",
    "codex"
  ],
  "commands": [
    "feasibility",
    "brainstorm",
    "design",
    "plan",
    "test-first",
    "check",
    "review-gate",
    "delivery"
  ],
  "overlay_commands": [
    "brainstorm",
    "check"
  ],
  "added_commands": [
    "feasibility",
    "design",
    "plan",
    "test-first",
    "review-gate",
    "delivery"
  ],
  "scripts": [
    "feasibility-check.py",
    "design-export.py",
    "plan-validate.py",
    "check-quality.py",
    "delivery-control-validate.py",
    "metadata-autocommit-guard.py",
    "record-session-helper.py"
  ]
}
```

5. `workflow_version` / `workflow_schema_version`：
   - 若本轮能确认其值，则一并补齐
   - 若当前没有可靠来源，允许暂时保持缺失，但必须在迁移记录中显式注明“仍为 legacy/unknown”
6. 不把 `multi-cli-review` / `multi-cli-review-action` 写进 `workflow-installed.json`：
   - 它们是 reviewer / 协调者能力前置，不属于当前 workflow 已托管的命令/脚本清单

---

## 7. 回滚方案

本次迁移如要实施，不应把 `upgrade-compat.py --force` 当作主回滚手段。

推荐回滚方式：

1. 恢复迁移前 Git 分支或工作区快照。
2. 若只回滚 workflow 托管层，则按以下顺序恢复：
   - 先恢复命令文件、skills 与 helper scripts
   - 再恢复 `AGENTS.md` 与 `start.md` 路由
   - 最后恢复 `.trellis/workflow-installed.json`
3. 需要恢复的快照目录：
   - `.claude/commands/trellis/`
   - `.opencode/commands/trellis/`
   - `.agents/skills/`
   - `.trellis/scripts/workflow/`
   - `.trellis/workflow-installed.json`
4. 再次跑 `upgrade-compat.py --check`，确认已回到迁移前状态。

---

## 8. 验证方案

### 8.1 结构验证

- `AGENTS.md` 路由是否已切换为：
  - 自审 -> `check`
  - 补充审查 -> `review-gate`
- `start.md` 是否已切换为：
  - 实现完成 -> `check`
  - `check` 完成 -> `review-gate`

### 8.2 语义验证

- `check` 是否以 `check.md` 为输出产物，并调用 `check-quality.py`
- `review-gate` 是否读取 `$TASK_DIR/check.md`
- 旧 `self-review.md` / `self-review-check.py` 是否不再出现在主链路
- archived task 中历史 `self-review.md` 产物默认保留，不纳入清理范围

### 8.3 收口验证

1. 重新跑 `analyze-upgrade.py`
2. 重新跑 `upgrade-compat.py --check`
3. 旧引用清理检查，至少执行：

```bash
rg -n "self-review|self-review-check\\.py" AGENTS.md .claude/commands/trellis .opencode/commands/trellis .agents/skills .trellis/scripts/workflow
```

4. 路由与阶段检查，至少人工核对：
   - `AGENTS.md`
   - `.claude/commands/trellis/start.md`
   - `.opencode/commands/trellis/start.md`

5. 目标应至少达到：
   - 不再出现旧 `self-review` / `self-review-check.py` 的 `delete`
   - `review-gate` / `check-quality.py` 不再是缺失的 `add`
   - `merge` 项显著下降，只剩明确保留的目标项目私有漂移

---

## 9. 仍待用户最终确认的实现边界

在真正动手前，还需用户确认这三类取舍：

1. `brainstorm/design/plan/test-first/delivery` 中哪些目标项目私有改写必须保留。
2. `finish-work/record-session/metadata-autocommit-guard.py` 中哪些项目化约束优先于当前源资产。
3. `.trellis/workflow-installed.json` 是否在本轮同时补写 `workflow_version / workflow_schema_version`。
4. reviewer CLI 的 `multi-cli-review` / `multi-cli-review-action` 能力是否已在实际执行环境中可用；若不可用，需要先补齐能力，再执行 `review-gate` 链路。

---

## 10. 当前结论

下一步若进入实现，应按本蓝图执行，不建议直接运行：

- `upgrade-compat.py --merge`
- `upgrade-compat.py --force`

因为这两条路径都不能正确表达本次“命令语义迁移 + 大量 merge 私有漂移”的真实结构。
