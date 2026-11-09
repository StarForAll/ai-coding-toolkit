# P6 交付记录（命名解耦 / S11）

## 1. 本轮改动

| 位点 | 改动 |
|---|---|
| `docs/workflows/新项目开发工作流/` → `docs/workflows/wf/` | 源树目录改英文（`git mv`，245 文件随迁） |
| 显示名与技术标识 | **不动**：显示名仍是中文「新项目开发工作流」；`wf`、`.wf/`、`wf-*`、`.agents/skills/wf-*` 全部不变 |
| `scripts/wf_release_common.py` | `SOURCE_ROOT` 指向新目录（仍是**唯一常量**） |
| `scripts/wf-protocol-docs.py`、`wf-evidence-snapshot.py` | 不再各自硬编码中文路径，改为 `Path(_common.SOURCE_ROOT)`（S11「脚本从清单取路径」） |
| 82 个 tracked 引用者 + 3 个 untracked（含 `.claude/settings.local.json`） | 路径形态统一改为 `docs/workflows/wf`；**判断规则**：只改路径形态（`workflows/<名>/`、`"workflows", "<名>"`、`./<名>/` 链接），散文里的中文显示名保留 |
| 历史记录 | **不改写**：`.trellis/workspace/**`、`.trellis/tasks/archive/**` 保持原样（S11 只要求脚本与测试从清单取路径） |
| `.trellis/spec/**` 指引 | 路径形态改为新目录；`spec/docs/index.md` 的目录树同步 |

## 2. 一次自我纠正（记下来，避免下次踩）

第一轮批量替换把 `.trellis/**`（含工作日志与归档任务记录）也改了 568 处，属"改写历史"。已按相反规则逐类还原（`workflows/wf/`、`"workflows", "wf"`、无斜杠形态、以及 `.trellis/workflows/wf.md` 这个**同名但不同物**的变体文件），最终 `.trellis` 只剩既有在途改动。教训：批量改写必须排除记录层，且要区别"目录名"与"同名文件名"。

## 3. 验证

| 命令 | 结果 |
|---|---|
| `unittest discover`（工作树） | **203 tests OK** |
| `build-wf-release.py --verify` | **OK** byte reproduction（69 assets） |
| `validate-wf-design.py` | **OK** 定义 100% / 消费 100% / 输入摘要 4/4 |
| `check-doc-refs.py` | **0 problem(s)** |
| `wf-protocol-docs.py --check` | **OK** 36 码 / 16 配置键 / 11 转移 |
| **干净 clone** → `--verify` | **OK**（69 assets） |
| **干净 clone** → `unittest discover` | **203 tests OK** |
| **干净 clone** → `wf-protocol-docs.py --check` | **OK** |

## 4. 提交

- `db29acd refactor(wf): 源树目录改英文 wf，显示名与技术标识不动（P6 / S11）`
- `04a3d6b docs(spec): 指引里的源树路径改为 docs/workflows/wf（P6 同批）`

## 5. 未完成 / 观察

1. `AGENTS.md` 里"the path is empty until the new module source is built"这句是**旧状态描述**（源树早已不为空），属既有文案漂移，未改（不在本任务范围，且改它要同步 README.en）。
2. `.trellis/workspace/**` 与归档任务里的旧路径按 S11 **保持原样**；后续如需检索可按 `workflows/wf` 与 `workflows/新项目开发工作流` 两式同时 grep。
