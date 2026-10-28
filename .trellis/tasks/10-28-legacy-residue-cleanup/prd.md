# PRD：退役残留清理（A 级）+ 旧产品文档退役 + 临时项目脚本瘦身

## 1. 背景

旧模块与 1.2 已退役（`7fe5993`）。审计发现活跃文档仍有 5 处指向已删对象，另有两份旧产品文档整体建立在已删脚本之上。用户已裁决：

- 只清 **A 级残留**（不动根目录个人草稿）；
- 《自定义工作流制作规范》《完整流程演练模板》**随旧产品退役（删除）**；
- **补瘦身版**临时项目初始化脚本（只做 `trellis init` + `/tmp` 目录管理）。

## 2. 范围

### 2.1 A 级残留（活跃文档指向已删对象）

| 位置 | 处理 |
|---|---|
| `.trellis/spec/docs/index.md` `## Workflow Rule Propagation`（211–260） | 整节删除（传播清单 + 11 条历史规则全部指向已删文档/脚本/已退役 skill） |
| 同文件 `:34` Critical rule | 改述：删除"阶段门禁 / Phase Router / `阶段状态机与强门禁协议.md` / `工作流总纲.md`"这些旧产品指代 |
| 同文件 `:44` Workflow authoring spec 行 | 删除（该文档本任务删除） |
| 同文件 `:76` 目录树 `工作流总纲.md` | 删除该行 |
| 同文件 `:152` "Keep active version references aligned" | 删除（引用已删的 `commands/workflow_assets.py` 与 `工作流总纲.md`） |
| `.trellis/spec/scripts/index.md:70-75` | 删除 `docs/workflows/**/commands/` 目录树（`install-workflow.py` / `uninstall-workflow.py` / `upgrade-compat.py` / `shell/*.py`） |
| `docs/README.md:13-16` | 四条旧结构约定改为当前结构说明 |

### 2.2 旧产品文档退役（删除）

- `docs/workflows/自定义工作流制作规范.md`（473 行 / 25 处旧引用）
- `docs/workflows/完整流程演练模板.md`（1 处旧引用）

连带（必须同批）：

| 位置 | 处理 |
|---|---|
| `docs/workflows/中途接手项目工作流/工作流总纲.md:17` | 链接改成"原仓库级制作规范已随旧工作流模块退役" |
| `docs/workflows/旧项目重构工作流/工作流总纲.md:19` | 同上 |
| `.trellis/spec/workflow-support-inventory.md`（6 行） | "Referenced by 自定义规范" 改为"当前无引用方" |
| `docs/README.md` 相关行 | 随 2.1 一并处理 |

### 2.3 瘦身版临时项目初始化脚本

新增 `commands/shell/init-trellis-temp-project.sh`（bash，约 60–80 行），职责仅：

1. 探测 `trellis --version`（缺失即报错退出）；
2. 解析/创建目标目录（默认 `/tmp/trellis-<version>-<n>`，`--path` 可覆盖，`--force` 可重建）；
3. 透传平台参数给 `trellis init -y`（`--platform claude|codex|zcode|dsh|pi` 可重复，映射为 CLI flag）；
4. `--dry-run` 只打印将执行的命令；`--no-init` 只准备目录。

**不得**调用任何旧产品脚本，也不得写入目标项目的 `.trellis` 之外的仓库路径。

连带：`README.md` / `README.en.md` 的 `commands/shell/` 两行、`.trellis/spec/commands/index.md` 的对应说明恢复为"包含该脚本（职责见文件头）"。

## 3. 不做

- 不动根目录个人草稿（`todo.txt`、`trellis常用提示语句.txt`、`工作流升级.txt`）——用户已裁"只清 A 级"。
- 不动设计稿、依赖说明、`workflow-implementation.md`、`wf-variant.md`。
- 不重建 B3（`Trellis隐藏目录边界清单.md`），不启动 T2/T3。
- 不改 `scripts/validate-skills.sh`（已核对无残留）。

## 4. 验收

| ID | 判据 |
|---|---|
| B1 | 两份旧文档不存在；`git grep "自定义工作流制作规范\|完整流程演练模板" -- ':!tmp' ':!.trellis/tasks' ':!.trellis/workspace'` → 0 |
| B2 | 旧脚本名（`install-workflow.py`/`upgrade-compat.py`/`analyze-upgrade.py`/`plan-validate.py`）在活跃文档中 → 0（`workflow-implementation.md` 的裁决历史除外，若有则逐条说明） |
| B3 | `guide` 类旧文档名（`工作流总纲`/`命令映射`/`工作流嵌入执行规范`/`阶段状态机与强门禁协议`/`CLI原生适配边界矩阵`/`装后隐藏目录与托管边界核对清单`/`目标项目兼容升级方案指导`/`多CLI通用新项目完整流程演练`/`工作流全局流转说明`/`工作流思维导图`）在 `.trellis/spec/` 与 `docs/`（排除 tasks/workspace/tmp/个人草稿）→ 0 |
| B4 | 新脚本 `bash -n` 通过；`--dry-run` 输出包含 `trellis init -y` 与目标目录；真实执行一次到 `/tmp` 后清理成功 |
| B5 | `trellis-library validate --strict-warnings`、`validate-skills.sh`、`get_context.py` 全过 |
| B6 | README 双语同步（两处 `commands/shell/` 说明一致） |
