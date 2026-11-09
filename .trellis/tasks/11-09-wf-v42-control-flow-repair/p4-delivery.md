# P4 交付记录（第一片：K5 vendor 边界）

## 1. 本轮改动

| 文件 | 动机 | 编号 |
|---|---|---|
| `payload/lib/wflib/scope.py` | 新增 `VENDOR_PREFIX = ".wf/"` / `is_vendor` / `vendor_paths`；`classify_candidates` 增 **`v` 桶**（vendor 先于一切归属判定被摘出，既不算交付也不算越界），并在结果里给 `vendor_dirty` | K5 |
| `payload/lib/wflib/check.py::object_paths` | 检查对象显式排除 vendor（改动框架不再污染业务交付的指纹与结论） | K5 |
| `payload/lib/wflib/judgments.py` | 骨架增 `vendor_dirty`；预览增 `[vendor] N 项框架自有改动（不计入交付、不进审查、不进业务提交）` 一行 | K5、S5.1 |
| `scripts/tests/wf_review/test_vendor_boundary.py` | 4 条：前缀判定、vendor 分离、分类器有 v 桶与 `vendor_dirty`、检查对象排除 vendor | K5 |

**为什么这条重要**：dogfood E1/E2——`.wf/lib/wflib/*.py` 曾直接进任务批准触碰面，"修框架"与"做需求"混在同一份交付里，检查与提交都无法分开。现在 vendor 在分类的第一顺位被摘走，只留事实。

## 2. 验证

| 命令 | 结果 |
|---|---|
| `unittest discover` | **173 tests OK**（169 → 173） |
| `build-wf-release.py --verify` | **OK** byte reproduction（66 assets） |

## 2.5 第二片：K6 五类动作的确认、脱敏入库与两道提交守卫

| 位点 | 改动 |
|---|---|
| `payload/protocol/repo_rules.json`（新） | K6 第 5 类**仓库级规则文件集合**（34 条模式：`.gitignore`、依赖清单、锁文件、CI、工具链），带 `source` 与 `why`；集合只此一处声明 |
| `protocol.py::repo_rules` | 加载 + 校验（缺 patterns 即 `ProtocolError`） |
| `payload/lib/wflib/authorize.py`（新） | `ACTIONS` 五类（commit/delete/export/expand/repo_rules）；`redact` 按 `protocol/redaction.json` 口径产出**可入库副本**（丢掉外发全文/删除明细/凭据类，保留动作/路径/取值/时间/人/quote）并给 `original_digest`；`record_authorization` 把脱敏副本写**任务目录（committed）**、敏感原文只留 runtime；`require` 读回；`is_repo_rule`/`repo_rule_paths` 用注册表判定 |
| `tasks.py::cmd_archive` | 两道守卫：**含 vendor 的提交 → `WF_SCOPE_VIOLATION`**；**含仓库级规则文件但缺 `repo_rules` 确认 → `WF_COMMIT_NOT_AUTHORIZED`**（facts 指明缺哪一类动作 + 两条出口） |
| `dev-manifest.json` | 登记 `authorize.py` 与 `repo_rules.json`（68 assets） |
| `scripts/tests/wf_review/test_authorization.py` | 7 条：runtime_only 字段被丢、保留下发摘要与脱敏记录、摘要可复算、脱敏件进任务目录而原文留 runtime、未知动作被拒、集合来自 protocol、注册表匹配（含 glob） |

验证：`unittest discover` **180 tests OK**；`build-wf-release.py --verify` **OK**（68 assets）。

## 2.6 第三片：K6 第 2/4 类接入 + K7 三段回报

| 位点 | 改动 |
|---|---|
| `authorize.py::covers` | 已入库确认是否覆盖给定路径（glob 匹配；没确认就整批未覆盖，不猜"大概是这个意思"）；`(covered, uncovered)` 两值返回 |
| `check.py` 范围核对 | **K6 第 4 类（越界修改）**：f 桶路径被 `expand` 确认覆盖时按"已批准扩面"处理（仍留 `approved_expansion` 事实、并入 e 桶），否则 `WF_SCOPE_VIOLATION` 并列出未覆盖路径与两条出口（回 Plan 重批 / 先确认后改） |
| `tasks.py::cmd_archive` | **K6 第 2 类（删除数据）**：提交范围内的删除路径缺 `delete` 确认 → `WF_COMMIT_NOT_AUTHORIZED`（facts 列出未覆盖路径）；**K7**：结果里给 `stages` 三段（业务 / 记录 / 运行态），每段带 `paths`、`result` 与**恢复点**；运行态按 S10 不入库只报告 |
| `tasks.py::_deleted_paths` | 提交范围内的删除路径识别（工作树不存在即删除） |
| `scripts/tests/wf_review/test_authorization.py` | +5 条：无确认即未覆盖、glob 覆盖、部分覆盖报剩余、别的动作不算、归档合同（三段 + 三道守卫存在） |

验证：`unittest discover` **185 tests OK**（180 → 185）；`build-wf-release.py --verify` **OK**（68 assets）。

## 2.7 第四片：人执行入口 + 外发触发点（P4 收口）

| 位点 | 改动 |
|---|---|
| `cli.py::cmd_authorize` | **K6 五类动作的人执行入口**：`authorize record --task --file`（决定文件每条含 `choice∈五类` + 必填 `quote`）→ 每类落 `authorization-<action>.json`（**脱敏进任务目录=committed**，原文留 `.wf/.runtime/decisions/`）；`authorize show --task` 只读查看已确认的类别与摘要。走 `task.authorize` 动作（锁内重核 + 写标记 + 证据引用） |
| `review.py::launch` | **K6 第 3 类（外发）触发点**：材料要外发时，`export_decision` 只是声明，必须另有 `authorization-export.json` 才放行；否则 `WF_COMMIT_NOT_AUTHORIZED`（缺 `missing_action=export`）+ 两条出口 |
| `scripts/tests/wf_review/test_authorization.py` | +3 条：命令已注册且 help 提到 record、一条文件可落五类确认且各自成文件、launch 已接 export 守卫 |

**这一步解掉的正是上一轮我自己提出的风险**：守卫有了，但"永远没有确认文件"会让它们一律阻断——现在有了人执行入口。

验证：`unittest discover` **188 tests OK**（185 → 188）；`build-wf-release.py --verify` **OK**（68 assets）；协议一致性 / 设计门禁 / 文档引用全绿。

## 3. P4 收口状态

| K6 五类 | 守卫位点 |
|---|---|
| ① 提交/推送 | `cmd_archive`（`WF_COMMIT_NOT_AUTHORIZED`） |
| ② 删除数据 | `cmd_archive`（`authorize.covers(delete)`） |
| ③ 外发内容 | `review.launch`（`authorize.require(export)`） |
| ④ 越界修改 | `check` 范围核对（`authorize.covers(expand)`） |
| ⑤ 仓库级规则文件 | `cmd_archive`（`protocol/repo_rules.json` 注册表 + `require(repo_rules)`） |
| 人执行入口 | `wf authorize record/show`（脱敏入库、原文留 runtime） |
| K7 三段回报 | `cmd_archive` 的 `stages`（业务/记录/运行态 + 恢复点） |
| K5 vendor | 分类 `v` 桶 + 提交守卫 + 检查对象排除 |

**仍缺一条正文**：机制稿没有"仓库级规则文件集合由 protocol 声明"的句子（v42 K6 要求），当前靠 `protocol/repo_rules.json` 自述；补一句正文需你授权（属机制稿语义）。

两件都落在 `archive` / `stop` 那一段，建议下一轮一起做（同一段代码，避免两次翻）。
