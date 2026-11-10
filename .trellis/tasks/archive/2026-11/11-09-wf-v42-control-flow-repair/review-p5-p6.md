# 自查审查记录（P5–P6 改动集）

审查方式：逐条读实现 + 在有真实 Git 历史的仓库里跑投影做交叉验证（不只看断言）。
结论：**修正方向正确，但有 5 处必须修**（已修）+ 3 处需你裁定/知情。

## 必修（已修，均带回归断言）

| # | 缺陷 | 为什么错 | 修法 | 断言 |
|---|---|---|---|---|
| R1 | `assertion_index` 的"是否改过"只比单一摘要形态 | 策展记录存的是**整文件摘要**，而 `spec_versions` 现在给**规则实质摘要** → 所有已策划规则都会被判成"本任务改过"，K4c 变成一律阻断 | 抽 `curation_changed(before, rule_digest, file_digest)`：与当前任一形态相等即"没改过" | `CurationDigestTest` 4 条 |
| R2 | 骨架 `findings` 只取**未处置** | v42 §5.1 要求 `findings[]` 列全部、`closures[]` 单列已关闭；原实现让"已关闭的缺陷从清单消失"，且 `findings` 与 `unaddressed_findings` 变成同一份 | 新增 `review.all_findings`（含 `closed` 标记），骨架用它；未处置仍是子集 | `AllFindingsTest` |
| R3 | `_deleted_paths` 按"工作树不存在"判删除 | 从未存在过的路径（glob 展开、拼错）也被算成删除 → 每次归档都被要求补 `delete` 确认（假阻断，且会训练人乱点确认） | 只认「HEAD 里有、工作树里没有」 | `DeletedPathTest` 2 条 |
| R4 | `projection.attribution` 用 `%x00%x00` 切记录 | 与 git 输出不对齐：实测 6 条提交只解析出 1 条且判成 external（**投影静默出错**） | 改 `%x1f/%x1e` 并抽 `classify_commits(raw, ...)` 纯函数 | `CommitClassificationTest` 3 条 |
| R5 | `projection.open_items` 的死条件 `conclusion in ("passed", None) and == "passed"` | 恒等于 `== "passed"`，读起来像"None 也算通过"；`None`（未完成）本该算未核实 | 简化为 `== "passed"` | 既有 `ProjectionTest` 覆盖 |

## 知情/待裁

1. **`schema_version` 同时受类型校验**（P0 的 D6）：非法值会多报一条 field 级问题，行为更严，非缺陷。
2. **`assertions_digest` 依赖 `spec_versions` → 依赖 `scope.classify_candidates`**（读 Git）。分类失败时骨架标 `scope_available=false`，但锚点侧仍会抛——这是有意的 fail-closed；若你希望"非 git 环境也能 Check"，需要单独定口径。
3. **`_identity_facts` 每次 `enable` 都探 `/proc`**：codex/dsh 两档事实已在部署表声明；未声明标识的宿主仍是 `unknown` 且不猜（符合 S12）。

## 抽查过但确认无问题的点

- `authorize.redact` 只丢 `RUNTIME_ONLY_KEYS`，保留路径/取值/人/quote/digest —— 与 S7 的保留项一致；
- `check.object_paths` 的 vendor 过滤只作用于 e 桶，`.wf/baseline.md`/`project-config.json` 仍在规则输入里；
- `tasks.cmd_archive` 的三道守卫都在 `final_gate` **之前**，失败会把 action 标 fail（不留半成功）；
- `judgments`/`projection`/`sampling` 之间的 import 都是函数内惰性导入，无环。
